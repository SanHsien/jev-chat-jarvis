from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import check_upstream_updates as checker  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_baseline_file_is_valid_and_complete() -> None:
    baseline = checker.load_baseline()

    assert baseline["repo"].endswith("jev-chat/jev-chat-jarvis.git")
    assert baseline["branch"] == "main"
    assert len(baseline["reviewed_through"]) == 40
    assert baseline["reviewed_date"]
    assert baseline["track"] == "release"


def test_baseline_reads_pr_and_issue_watermarks() -> None:
    baseline = checker.load_baseline()

    assert isinstance(baseline["reviewed_pr_through"], int)
    assert isinstance(baseline["reviewed_issue_through"], int)
    assert baseline["reviewed_pr_through"] > 0


def test_two_part_upstream_tags_are_parsed() -> None:
    """Upstream tags v1.3 / v1.4 (no patch); a three-part-only regex saw no releases."""
    raw = "\n".join(
        [
            "aaa\trefs/tags/v1.3",
            "bbb\trefs/tags/v1.4",
            "ccc\trefs/tags/v1.4^{}",
            "ddd\trefs/tags/v1.10.2",
            "eee\trefs/tags/nightly",
        ]
    )
    tags = checker.parse_tag_refs(raw)

    assert [name for _, name, _ in tags] == ["v1.3", "v1.4", "v1.10.2"]
    # The peeled ^{} line carries the commit for an annotated tag.
    assert dict((name, sha) for _, name, sha in tags)["v1.4"] == "ccc"


def test_missing_patch_sorts_before_patch_releases() -> None:
    tags = checker.parse_tag_refs("a\trefs/tags/v1.4.1\nb\trefs/tags/v1.4\n")

    assert [name for _, name, _ in tags] == ["v1.4", "v1.4.1"]


def test_workflow_is_scheduled_and_fails_on_unreviewed_work() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "upstream-check.yml").read_text(
        encoding="utf-8"
    )

    assert "schedule:" in workflow
    assert "--strict" in workflow
    assert "GH_TOKEN" in workflow
    assert "check_divergence.py" in workflow


def test_decision_log_mentions_the_reviewed_release() -> None:
    baseline = checker.load_baseline()
    decisions = (REPO_ROOT / baseline["decision_log"]).read_text(encoding="utf-8")

    assert baseline["reviewed_release"] in decisions
    assert baseline["reviewed_through"][:7] in decisions
