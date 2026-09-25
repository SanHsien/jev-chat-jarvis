"""Enforce that `docs/DIVERGENCE.md` lists exactly the upstream files this fork has

changed or deleted since the reviewed baseline -- no more, no less.

This fork's stated policy (see docs/DIVERGENCE.md and docs/DECISIONS.md) is: track
upstream directly, accept divergence as the expected outcome, and write every
divergence down clearly enough that a future sync does not need to re-derive the
judgment call. A registry nobody checks drifts the moment
someone edits an upstream-owned file without adding a row, or deletes a row without
reverting the edit; this script is the machine check that keeps the two in sync.

It compares two sets:

- Every upstream-owned file (present in the repo at the reviewed baseline commit,
  `reviewed_through` in `tools/upstream_baseline.json`) that is modified or deleted
  between that commit and the current working tree (`git diff --name-status
  <base>`, which folds in both committed and uncommitted changes).
- Every file path registered in `docs/DIVERGENCE.md`'s table.

A file this fork only *adds* (never existed upstream) is not a divergence and is not
expected to be registered -- there is no upstream version to diverge from.

A registry row may name a whole group instead of one file: a path ending in `/`
covers everything under that directory, and a path with `*` / `?` is a glob
(`fnmatch`). That keeps a bulk deletion -- an upstream directory this fork does not
ship -- to one row. A group row that matches no divergent file is reported as
"registered but not changed", the same as a stale single-file row.

`RENAME_ALIASES` maps an *added* path that stands in for an upstream-owned file
(for example a moved README) to that file, because git's rename detection only
pairs a deleted path with an added one. It is empty today.

Git history has to actually contain the baseline commit for any of this to work. A
shallow clone (the default for many CI checkouts) or a machine that has never fetched
that commit cannot answer "what changed since then", so this degrades gracefully: it
prints a warning and exits 0 rather than failing a check that has no way to succeed.

    python tools/check_divergence.py [--json] [--repo-dir PATH] [--divergence-doc PATH]
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = REPO_ROOT / "tools" / "upstream_baseline.json"
DIVERGENCE_DOC_PATH = REPO_ROOT / "docs" / "DIVERGENCE.md"

# Added path -> the upstream-owned path it stands in for (see the module docstring).
RENAME_ALIASES: dict[str, str] = {}

_TABLE_ROW_RE = re.compile(r"^\|\s*`([^`]+)`")


class DivergenceCheckError(RuntimeError):
    """Raised when the baseline or the divergence document cannot be read."""


def load_baseline(path: Path = BASELINE_PATH) -> dict:
    if not path.is_file():
        raise DivergenceCheckError(f"missing baseline file: {path}")
    try:
        baseline = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DivergenceCheckError(f"invalid baseline file: {path}: {exc}") from exc
    reviewed_through = baseline.get("reviewed_through")
    if not reviewed_through or len(reviewed_through) != 40:
        raise DivergenceCheckError(f"{path} is missing a full 40-character reviewed_through")
    return baseline


def run_git(args: list[str], repo_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def base_commit_available(base_sha: str, repo_dir: Path) -> bool:
    """Is the base commit object present in this local repository?

    A shallow clone (common in CI) or a fresh checkout that never fetched the
    fork point will not have it; there is no way to answer "what changed since
    then" without it, so callers must treat a False result as "skip, do not fail".
    """
    result = run_git(["cat-file", "-e", f"{base_sha}^{{commit}}"], repo_dir)
    return result.returncode == 0


def fetch_base_commit(repo_url: str, base_sha: str, repo_dir: Path) -> bool:
    """Fetch just the baseline commit from upstream when it is not local.

    This fork's history is a single root commit (upstream history is not an
    ancestor), so a clone never carries the baseline by itself. GitHub serves a
    commit by its full SHA; a failure (offline, rewritten upstream) just leaves
    the caller's "not available" path in charge.
    """
    result = run_git(["fetch", "--quiet", "--no-tags", repo_url, base_sha], repo_dir)
    return result.returncode == 0 and base_commit_available(base_sha, repo_dir)


def owned_files_at_base(base_sha: str, repo_dir: Path) -> set[str]:
    """Every path that existed in the repo at the reviewed baseline commit.

    A file outside this set was added by this fork; it has no upstream version to
    diverge from, so a later change to it is not a divergence.
    """
    result = run_git(["ls-tree", "-r", "--name-only", base_sha], repo_dir)
    if result.returncode != 0:
        raise DivergenceCheckError(f"git ls-tree failed: {result.stderr.strip()}")
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def changed_since_base(base_sha: str, repo_dir: Path) -> list[tuple[str, str]]:
    """`(status, path)` pairs for every difference between the base commit and now.

    `git diff <commit>` (one ref, no second one) compares the base commit against
    the working tree -- index and unstaged changes both -- so an uncommitted edit
    is caught here too, not only a committed one. `--no-renames` is explicit:
    git's `diff.renames` defaults to on, and a renamed upstream file would then
    come back as one `R` line that is neither a modification nor a deletion --
    the upstream path would silently escape the registry.
    """
    result = run_git(["diff", "--no-renames", "--name-status", base_sha, "--"], repo_dir)
    if result.returncode != 0:
        raise DivergenceCheckError(f"git diff failed: {result.stderr.strip()}")
    pairs = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status, path = parts[0][0], parts[-1]
        pairs.append((status, path))
    return pairs


def compute_divergent_files(pairs: list[tuple[str, str]], owned: set[str]) -> set[str]:
    """Which of `pairs` count as a fork divergence from an upstream-owned file.

    Modified or deleted upstream-owned paths always count. An *added* path counts
    only through `RENAME_ALIASES`, when it stands in for an upstream-owned path that
    was itself changed -- an ordinary new file this
    fork introduced is not a divergence, because there is no upstream file it
    diverges from.
    """
    divergent: set[str] = set()
    for status, path in pairs:
        modified_or_deleted_upstream_file = status in ("M", "D") and path in owned
        aliased_addition_for_a_changed_upstream_file = (
            status == "A" and path in RENAME_ALIASES and RENAME_ALIASES[path] in owned
        )
        if modified_or_deleted_upstream_file or aliased_addition_for_a_changed_upstream_file:
            divergent.add(path)
    return divergent


def parse_registered_paths(text: str) -> set[str]:
    """Every backtick-quoted path in the first column of `docs/DIVERGENCE.md`'s table.

    The header row (`| 上游檔案 | ...`) and the separator row (`| --- | ... |`) do not
    start their first cell with a backtick, so both are skipped without special-casing.
    """
    paths: set[str] = set()
    for line in text.splitlines():
        match = _TABLE_ROW_RE.match(line.strip())
        if match:
            paths.add(match.group(1).strip())
    return paths


def _is_group(entry: str) -> bool:
    return entry.endswith("/") or any(ch in entry for ch in "*?[")


def _covers(entry: str, path: str) -> bool:
    if entry.endswith("/"):
        return path.startswith(entry)
    if _is_group(entry):
        return fnmatch.fnmatchcase(path, entry)
    return path == entry


def compare(divergent: set[str], registered: set[str]) -> tuple[set[str], set[str]]:
    """`(changed_but_not_registered, registered_but_not_changed)`.

    A group row (directory or glob) covers every divergent path it matches; it is
    stale only when it matches none of them.
    """
    unregistered = {p for p in divergent if not any(_covers(e, p) for e in registered)}
    stale = {e for e in registered if not any(_covers(e, p) for p in divergent)}
    return unregistered, stale


def render_report(
    base_sha: str,
    divergent: set[str],
    registered: set[str],
    changed_not_registered: set[str],
    registered_not_changed: set[str],
) -> str:
    lines = [
        f"Base commit: {base_sha[:7]}",
        f"{len(divergent)} upstream file(s) diverge from the baseline; "
        f"{len(registered)} registered in docs/DIVERGENCE.md.",
    ]
    if changed_not_registered:
        lines.append("")
        lines.append("Changed but NOT registered in docs/DIVERGENCE.md:")
        lines.extend(f"  - {path}" for path in sorted(changed_not_registered))
    if registered_not_changed:
        lines.append("")
        lines.append("Registered in docs/DIVERGENCE.md but NOT actually changed:")
        lines.extend(f"  - {path}" for path in sorted(registered_not_changed))
    if not changed_not_registered and not registered_not_changed:
        lines.append("OK: the divergence registry matches the actual changes.")
    return "\n".join(lines)


def render_json(
    base_sha: str,
    divergent: set[str],
    registered: set[str],
    changed_not_registered: set[str],
    registered_not_changed: set[str],
    warning: str | None = None,
) -> str:
    payload = {
        "base_commit": base_sha,
        "changed_upstream_files": sorted(divergent),
        "registered_files": sorted(registered),
        "changed_but_not_registered": sorted(changed_not_registered),
        "registered_but_not_changed": sorted(registered_not_changed),
        "warning": warning,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-dir", type=Path, default=REPO_ROOT)
    parser.add_argument("--divergence-doc", type=Path, default=DIVERGENCE_DOC_PATH)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print a machine-readable JSON report instead of plain text.",
    )
    args = parser.parse_args()

    try:
        baseline = load_baseline()
    except DivergenceCheckError as exc:
        print(f"ERROR: {exc}")
        return 2
    base_sha = baseline["reviewed_through"]

    if not base_commit_available(base_sha, args.repo_dir) and baseline.get("repo"):
        fetch_base_commit(baseline["repo"], base_sha, args.repo_dir)
    if not base_commit_available(base_sha, args.repo_dir):
        warning = (
            f"WARNING: base commit {base_sha[:7]} is not available in this local "
            "repository (shallow clone, or history never fetched). Cannot compute "
            "divergence against it; skipping the check rather than failing one that "
            "has no way to succeed. Run `git fetch --unshallow` (or fetch the full "
            "history) to get a real answer."
        )
        print(warning)
        if args.json:
            print(render_json(base_sha, set(), set(), set(), set(), warning=warning))
        return 0

    try:
        owned = owned_files_at_base(base_sha, args.repo_dir)
        pairs = changed_since_base(base_sha, args.repo_dir)
        if not args.divergence_doc.is_file():
            raise DivergenceCheckError(f"missing divergence document: {args.divergence_doc}")
        doc_text = args.divergence_doc.read_text(encoding="utf-8")
    except DivergenceCheckError as exc:
        print(f"ERROR: {exc}")
        return 2

    divergent = compute_divergent_files(pairs, owned)
    registered = parse_registered_paths(doc_text)
    changed_not_registered, registered_not_changed = compare(divergent, registered)

    if args.json:
        print(
            render_json(
                base_sha, divergent, registered, changed_not_registered, registered_not_changed
            )
        )
    else:
        print(
            render_report(
                base_sha, divergent, registered, changed_not_registered, registered_not_changed
            )
        )

    return 1 if (changed_not_registered or registered_not_changed) else 0


if __name__ == "__main__":
    raise SystemExit(main())
