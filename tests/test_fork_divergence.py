"""Contract tests for the divergence registry check.

`docs/DIVERGENCE.md` is only trustworthy if it is exactly the set of upstream-owned
files this fork has actually changed -- not a superset (stale rows nobody removed) and
not a subset (a silent edit nobody wrote down). These tests pin the parsing, the
comparison in both directions, rename handling and group (directory / glob) rows (and
why an ordinary added file does *not* count), and the two ways this can legitimately not run
at all: a missing/unreachable base commit (shallow clone) degrades to a warning and
exit 0, never a false pass or a false failure.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import check_divergence as checker  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run(args: list[str], cwd: Path) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8"
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


@pytest.fixture
def tiny_repo(tmp_path: Path) -> tuple[Path, str]:
    """A throwaway git repo shaped like a fork point: one base commit, then a fork
    commit that modifies one upstream file, deletes another, and adds a new one."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _run(["init", "--initial-branch=main"], repo)
    _run(["config", "user.email", "test@example.invalid"], repo)
    _run(["config", "user.name", "Test"], repo)
    (repo / "UPSTREAM.md").write_text("original\n", encoding="utf-8")
    (repo / "KEEP.md").write_text("keep\n", encoding="utf-8")
    _run(["add", "."], repo)
    _run(["commit", "-m", "base"], repo)
    base_sha = _run(["rev-parse", "HEAD"], repo).strip()

    (repo / "UPSTREAM.md").write_text("forked\n", encoding="utf-8")
    (repo / "KEEP.md").unlink()
    (repo / "NEW.md").write_text("new\n", encoding="utf-8")
    _run(["add", "-A"], repo)
    _run(["commit", "-m", "fork changes"], repo)

    return repo, base_sha


def test_owned_files_at_base_lists_only_what_existed_at_that_commit(
    tiny_repo: tuple[Path, str],
) -> None:
    repo, base_sha = tiny_repo
    assert checker.owned_files_at_base(base_sha, repo) == {"UPSTREAM.md", "KEEP.md"}


def test_changed_since_base_reports_modify_delete_and_add(
    tiny_repo: tuple[Path, str],
) -> None:
    repo, base_sha = tiny_repo
    statuses = dict((path, status) for status, path in checker.changed_since_base(base_sha, repo))
    assert statuses == {"UPSTREAM.md": "M", "KEEP.md": "D", "NEW.md": "A"}


def test_compute_divergent_files_excludes_a_newly_added_file(
    tiny_repo: tuple[Path, str],
) -> None:
    repo, base_sha = tiny_repo
    owned = checker.owned_files_at_base(base_sha, repo)
    pairs = checker.changed_since_base(base_sha, repo)
    divergent = checker.compute_divergent_files(pairs, owned)
    assert divergent == {"UPSTREAM.md", "KEEP.md"}
    assert "NEW.md" not in divergent


def test_base_commit_available_distinguishes_real_from_bogus_sha(
    tiny_repo: tuple[Path, str],
) -> None:
    repo, base_sha = tiny_repo
    assert checker.base_commit_available(base_sha, repo) is True
    assert checker.base_commit_available("f" * 40, repo) is False


def test_fetch_base_commit_pulls_a_missing_baseline_from_upstream(
    tiny_repo: tuple[Path, str], tmp_path: Path
) -> None:
    """A single-root-commit fork has no upstream ancestor; the checker fetches it."""
    upstream, base_sha = tiny_repo
    fork = tmp_path / "fork"
    fork.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=fork, check=True)
    assert checker.base_commit_available(base_sha, fork) is False
    assert checker.fetch_base_commit(str(upstream), base_sha, fork) is True
    assert checker.base_commit_available(base_sha, fork) is True


def test_an_alias_counts_as_divergent_for_the_upstream_file_it_stands_in_for(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """git cannot pair a modified file with an added one, so aliases are explicit."""
    monkeypatch.setattr(checker, "RENAME_ALIASES", {"README.old.md": "README.md"})
    owned = {"README.md"}
    pairs = [("M", "README.md"), ("A", "README.old.md")]
    assert checker.compute_divergent_files(pairs, owned) == {"README.md", "README.old.md"}


def test_a_renamed_upstream_file_is_reported_as_deleted(tmp_path: Path) -> None:
    """git's diff.renames defaults on; without --no-renames a `git mv` of an upstream
    file came back as one R line and the upstream path escaped the registry."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _run(["init", "--initial-branch=main"], repo)
    _run(["config", "user.email", "test@example.invalid"], repo)
    _run(["config", "user.name", "Test"], repo)
    (repo / "old.xml").write_text("<a/>\n" * 20, encoding="utf-8")
    _run(["add", "."], repo)
    _run(["commit", "-m", "base"], repo)
    base_sha = _run(["rev-parse", "HEAD"], repo).strip()
    _run(["mv", "old.xml", "new.xml"], repo)
    _run(["commit", "-m", "rename"], repo)

    owned = checker.owned_files_at_base(base_sha, repo)
    pairs = checker.changed_since_base(base_sha, repo)
    assert checker.compute_divergent_files(pairs, owned) == {"old.xml"}


def test_directory_and_glob_rows_cover_every_matching_file() -> None:
    divergent = {"site/index.html", "site/assets/og.png", "docs/images/wechat-1.png", "README.md"}
    registered = {"site/", "docs/images/wechat-*.png", "README.md"}
    assert checker.compare(divergent, registered) == (set(), set())


def test_a_group_row_that_matches_nothing_is_stale() -> None:
    assert checker.compare({"README.md"}, {"README.md", "site/"}) == (set(), {"site/"})


def test_a_directory_row_does_not_cover_a_sibling_with_the_same_prefix() -> None:
    unregistered, _ = checker.compare({"site2/x.html"}, {"site/"})
    assert unregistered == {"site2/x.html"}


def test_an_added_file_without_a_registered_alias_is_not_a_divergence() -> None:
    owned = {"README.md"}
    pairs = [("A", "NOTICE.md")]
    assert checker.compute_divergent_files(pairs, owned) == set()


def test_parse_registered_paths_skips_header_and_separator_rows() -> None:
    text = (
        "| 上游檔案 | 上游原狀 |\n"
        "|---|---|\n"
        "| `README.md` | something |\n"
        "| `requirements-dev.txt` | something else |\n"
    )
    assert checker.parse_registered_paths(text) == {"README.md", "requirements-dev.txt"}


def test_the_repos_own_divergence_doc_registers_exactly_the_documented_files() -> None:
    text = (REPO_ROOT / "docs" / "DIVERGENCE.md").read_text(encoding="utf-8")
    assert checker.parse_registered_paths(text) == {
        "README.md",
        "CLAUDE.md",
        "CHANGELOG.md",
        "CONTRIBUTORS.md",
        "PRIVACY.md",
        ".gitignore",
        "apk/",
        "site/",
        "docs/acceptance.md",
        "docs/probe_spec.md",
        "docs/v1.3-*.md",
        "docs/images/wechat-*.png",
        "docs/images/donate/",
        "docs/images/mascot/",
        "docs/images/logo.png",
        "docs/images/overlay.png",
        "docs/images/settings.png",
        "docs/images/sponsors/",
        "app/src/main/res/drawable/ic_launcher_foreground.xml",
        "tools/jev/TASK.md",
        "app/build.gradle.kts",
        "build.gradle.kts",
        "gradle/wrapper/gradle-wrapper.properties",
        "gradle/wrapper/gradle-wrapper.jar",
        "gradlew",
        "gradlew.bat",
        "app/src/main/AndroidManifest.xml",
        "app/src/main/java/com/google/android/accessibility/selecttospeak/SelectToSpeakService.kt",
        "app/src/main/res/xml/config_disguised.xml",
        "app/src/main/res/values/strings.xml",
        "app/src/main/java/com/jev/probe/capture/ChatCaptureService.kt",
        "app/src/main/java/com/jev/probe/capture/ChatAppAdapter.kt",
        "app/src/main/java/com/jev/probe/MainActivity.kt",
        "app/src/main/java/com/jev/probe/SettingsActivity.kt",
        "app/src/main/java/com/jev/probe/KnowledgeActivity.kt",
        "app/src/main/java/com/jev/probe/core/Prefs.kt",
        "app/src/main/java/com/jev/probe/core/ChatModels.kt",
        "app/src/main/java/com/jev/probe/core/kb/KbModels.kt",
        "app/src/main/java/com/jev/probe/overlay/OverlayController.kt",
        "app/src/main/java/com/jev/probe/jev/VisionClient.kt",
        "app/src/main/java/com/jev/probe/capture/ocr/OcrEngine.kt",
        "app/src/main/java/com/jev/probe/jev/ReplyClient.kt",
        "app/src/main/java/com/jev/probe/capture/KeepAliveService.kt",
        "app/src/main/java/com/jev/probe/jev/JevQuestions.kt",
        "app/src/main/java/com/jev/probe/capture/ocr/ScreenCapture.kt",
        "app/src/main/java/com/jev/probe/core/kb/KbSelfCheck.kt",
        "app/src/main/java/com/jev/probe/core/kb/KbStore.kt",
        "app/src/main/java/com/jev/probe/jev/HttpJson.kt",
        "app/src/main/java/com/jev/probe/jev/JudgeClient.kt",
    }


def test_compare_reports_both_mismatch_directions() -> None:
    changed_not_registered, registered_not_changed = checker.compare({"a", "b"}, {"b", "c"})
    assert changed_not_registered == {"a"}
    assert registered_not_changed == {"c"}


def test_render_report_says_ok_when_everything_matches() -> None:
    report = checker.render_report("a" * 40, {"x"}, {"x"}, set(), set())
    assert "OK" in report


def test_render_report_lists_both_mismatch_directions() -> None:
    report = checker.render_report("a" * 40, {"x"}, {"y"}, {"x"}, {"y"})
    assert "NOT registered" in report
    assert "NOT actually changed" in report


def test_render_json_round_trips() -> None:
    payload = json.loads(checker.render_json("a" * 40, {"x"}, {"x"}, set(), set()))
    assert payload["base_commit"] == "a" * 40
    assert payload["changed_upstream_files"] == ["x"]
    assert payload["warning"] is None


def test_load_baseline_rejects_a_missing_file(tmp_path: Path) -> None:
    with pytest.raises(checker.DivergenceCheckError):
        checker.load_baseline(tmp_path / "nope.json")


def test_load_baseline_rejects_a_short_reviewed_through(tmp_path: Path) -> None:
    path = tmp_path / "baseline.json"
    path.write_text(json.dumps({"reviewed_through": "abc"}), encoding="utf-8")
    with pytest.raises(checker.DivergenceCheckError):
        checker.load_baseline(path)


def test_the_repos_own_baseline_is_readable_by_this_checker() -> None:
    baseline = checker.load_baseline()
    assert len(baseline["reviewed_through"]) == 40


def test_main_degrades_to_a_warning_and_exit_zero_when_the_base_commit_is_unreachable(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Simulates a shallow clone: the baseline names a commit this local repo does
    not have. There is no way to compute a real answer, so this must not fail the
    check -- it must say so and exit 0."""
    monkeypatch.setattr(checker, "load_baseline", lambda: {"reviewed_through": "f" * 40})
    monkeypatch.setattr(sys, "argv", ["check_divergence.py", "--repo-dir", str(REPO_ROOT)])

    exit_code = checker.main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "WARNING" in captured.out


def test_main_reports_ok_when_the_registry_matches_real_changes(
    tiny_repo: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, base_sha = tiny_repo
    monkeypatch.setattr(checker, "load_baseline", lambda: {"reviewed_through": base_sha})
    doc = repo / "DIVERGENCE.md"
    doc.write_text(
        "| 上游檔案 | 說明 |\n|---|---|\n| `UPSTREAM.md` | modified |\n| `KEEP.md` | deleted |\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys, "argv", ["check_divergence.py", "--repo-dir", str(repo), "--divergence-doc", str(doc)]
    )

    exit_code = checker.main()

    assert exit_code == 0
    assert "OK" in capsys.readouterr().out


def test_main_returns_one_when_a_real_change_is_not_registered(
    tiny_repo: tuple[Path, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, base_sha = tiny_repo
    monkeypatch.setattr(checker, "load_baseline", lambda: {"reviewed_through": base_sha})
    doc = repo / "DIVERGENCE.md"
    # KEEP.md's deletion is real but not registered here: this must go red.
    doc.write_text(
        "| 上游檔案 | 說明 |\n|---|---|\n| `UPSTREAM.md` | modified |\n", encoding="utf-8"
    )
    monkeypatch.setattr(
        sys, "argv", ["check_divergence.py", "--repo-dir", str(repo), "--divergence-doc", str(doc)]
    )

    assert checker.main() == 1


def test_main_returns_one_when_a_registered_row_was_not_actually_changed(
    tiny_repo: tuple[Path, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, base_sha = tiny_repo
    monkeypatch.setattr(checker, "load_baseline", lambda: {"reviewed_through": base_sha})
    doc = repo / "DIVERGENCE.md"
    # UNTOUCHED.md is not a real change; registering it anyway must go red too.
    doc.write_text(
        "| 上游檔案 | 說明 |\n|---|---|\n"
        "| `UPSTREAM.md` | modified |\n| `KEEP.md` | deleted |\n| `UNTOUCHED.md` | not real |\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys, "argv", ["check_divergence.py", "--repo-dir", str(repo), "--divergence-doc", str(doc)]
    )

    assert checker.main() == 1
