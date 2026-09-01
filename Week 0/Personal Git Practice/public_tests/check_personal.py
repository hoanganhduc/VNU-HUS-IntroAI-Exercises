#!/usr/bin/env python3
"""Public checkpoints for Week 0 Personal Git Practice.

The checks are deterministic and inspect only the published file contract and
observable Git state. They do not use an LLM or grade the quality of open prose.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

LESSON_DIR = Path(__file__).resolve().parents[1]
PLACEHOLDERS = (
    "REPLACE_THIS_TEXT",
    "TODO",
    "YOUR_ANSWER_HERE",
)
EXPECTED_MESSAGE = "Hello, Git and GitHub!"
EXPECTED_FIELDS = {
    "GIT_ROLE": "local-history",
    "GITHUB_ROLE": "hosted-collaboration",
    "CODESPACES_ROLE": "development-environment",
    "CLASSROOM50_WEB_ROLE": "assignment-browser-workflow",
    "CLASSROOM50_CLI_ROLE": "assignment-command-line-workflow",
    "PREDICT_AFTER_EDIT": "modified-not-staged",
    "PREDICT_AFTER_ADD": "staged",
    "FIRST_CHECK_RESULT": "fail",
    "RESTORE_RESULT": "restored-committed-version",
}
NARRATIVE_FIELDS = (
    "STATUS_BEFORE_EDIT",
    "REPOSITORY_ROOT",
    "CURRENT_BRANCH",
    "ORIGIN_URL",
    "STATUS_OBSERVATION",
    "DIFF_OBSERVATION",
    "UNSTAGE_OBSERVATION",
    "WORKING_TREE_STAGING_COMMIT",
    "COMMIT_VS_PUSH",
    "PUSH_OBSERVATION",
    "PULL_FF_ONLY",
    "RESTORE_OBSERVATION",
    "LESSON_LEARNED",
    "FINAL_GITHUB_URL",
)


class CheckFailure(RuntimeError):
    """Raised when a checkpoint requirement is not satisfied."""


def run(
    args: Sequence[str],
    *,
    cwd: Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        list(args),
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and result.returncode != 0:
        command = " ".join(args)
        detail = (result.stderr or result.stdout).strip()
        raise CheckFailure(f"command failed: {command}\n{detail}")
    return result


def git(*args: str, check: bool = True) -> str:
    result = run(("git", *args), cwd=LESSON_DIR, check=check)
    return result.stdout.strip()


def repository_root() -> Path:
    try:
        return Path(git("rev-parse", "--show-toplevel")).resolve()
    except CheckFailure as exc:
        raise CheckFailure("this lesson must be run inside a Git repository") from exc


def relative_lesson_path() -> Path:
    root = repository_root()
    try:
        return LESSON_DIR.relative_to(root)
    except ValueError as exc:
        raise CheckFailure("the lesson directory is outside the detected repository") from exc


def contains_placeholder(value: str) -> bool:
    upper = value.upper()
    return any(token in upper for token in PLACEHOLDERS)


def require_nonplaceholder(label: str, value: str, *, minimum: int = 1) -> None:
    cleaned = value.strip()
    if not cleaned or contains_placeholder(cleaned) or len(cleaned) < minimum:
        raise CheckFailure(f"{label} is empty, too short, or still contains a placeholder")


def parse_workbook() -> Dict[str, str]:
    path = LESSON_DIR / "workbook.md"
    if not path.is_file():
        raise CheckFailure("workbook.md is missing")
    fields: Dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^([A-Z][A-Z0-9_]+):\s*(.*)$", line)
        if match:
            key, value = match.groups()
            if key in fields:
                raise CheckFailure(f"workbook field {key} appears more than once")
            fields[key] = value.strip()
    return fields


def require_fields(fields: Dict[str, str], names: Iterable[str]) -> None:
    for name in names:
        if name not in fields:
            raise CheckFailure(f"workbook field {name} is missing")


def check_exact_fields(fields: Dict[str, str], names: Iterable[str]) -> None:
    for name in names:
        expected = EXPECTED_FIELDS[name]
        actual = fields.get(name, "")
        if actual != expected:
            raise CheckFailure(f"{name} must be exactly {expected!r}; found {actual!r}")


def normalize_github_url(url: str) -> str:
    value = url.strip()
    if value.startswith("git@github.com:"):
        value = "https://github.com/" + value[len("git@github.com:") :]
    elif value.startswith("ssh://git@github.com/"):
        value = "https://github.com/" + value[len("ssh://git@github.com/") :]
    if value.endswith(".git"):
        value = value[:-4]
    return value.rstrip("/")


def check_environment(fields: Dict[str, str]) -> None:
    if shutil.which("git") is None:
        raise CheckFailure("git is not installed")
    if shutil.which("gh") is None:
        raise CheckFailure(
            "GitHub CLI (gh) is not installed; rebuild the Codespace or install it locally"
        )
    if shutil.which("python3") is None:
        raise CheckFailure("python3 is not installed")

    root = repository_root()
    if not (root / ".git").exists():
        # Worktrees may use a .git file; rev-parse remains the source of truth.
        git_dir = Path(git("rev-parse", "--git-dir"))
        if not git_dir.exists() and not (root / git_dir).exists():
            raise CheckFailure("Git metadata could not be located")

    branch = git("branch", "--show-current")
    if not branch:
        raise CheckFailure("the repository is in detached-HEAD state; use a branch")

    origin_result = run(
        ("git", "remote", "get-url", "origin"), cwd=LESSON_DIR, check=False
    )
    if origin_result.returncode != 0:
        raise CheckFailure("the repository has no origin remote")
    origin = origin_result.stdout.strip()
    normalized = normalize_github_url(origin).lower()
    if normalized == "https://github.com/hoanganhduc/vnu-hus-introai-exercises":
        raise CheckFailure(
            "origin is the canonical course repository; create your own repository from the template"
        )

    require_fields(fields, EXPECTED_FIELDS.keys())
    check_exact_fields(
        fields,
        (
            "GIT_ROLE",
            "GITHUB_ROLE",
            "CODESPACES_ROLE",
            "CLASSROOM50_WEB_ROLE",
            "CLASSROOM50_CLI_ROLE",
        ),
    )


def extract_markdown_section(text: str, heading: str) -> str:
    pattern = re.compile(
        rf"^## {re.escape(heading)}\s*$\n+(.*?)(?=^## |\Z)",
        flags=re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        raise CheckFailure(f"profile.md is missing the heading '## {heading}'")
    return match.group(1).strip()


def check_profile() -> str:
    path = LESSON_DIR / "profile.md"
    if not path.is_file():
        raise CheckFailure("profile.md is missing")
    text = path.read_text(encoding="utf-8")
    username = extract_markdown_section(text, "GitHub username")
    goal = extract_markdown_section(text, "One goal for this course")
    require_nonplaceholder("profile GitHub username", username, minimum=1)
    require_nonplaceholder("profile course goal", goal, minimum=8)
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})", username):
        raise CheckFailure("profile GitHub username has an invalid format")
    return username


def check_content(fields: Dict[str, str]) -> None:
    check_environment(fields)
    check_profile()
    message_path = LESSON_DIR / "message.txt"
    if not message_path.is_file():
        raise CheckFailure("message.txt is missing")
    lines = message_path.read_text(encoding="utf-8").splitlines()
    if lines != [EXPECTED_MESSAGE]:
        raise CheckFailure(
            f"message.txt must contain exactly one line: {EXPECTED_MESSAGE!r}"
        )
    require_fields(fields, ("PREDICT_AFTER_EDIT",))
    check_exact_fields(fields, ("PREDICT_AFTER_EDIT",))


def relevant_paths(names: Iterable[str]) -> List[str]:
    rel = relative_lesson_path()
    return [str(rel / name) for name in names]


def require_clean_and_committed(names: Iterable[str]) -> None:
    paths = relevant_paths(names)
    status = git("status", "--porcelain", "--", *paths)
    if status:
        raise CheckFailure(
            "the following lesson files still have staged, unstaged, or untracked changes:\n"
            + status
        )
    for path in paths:
        tracked = run(
            ("git", "ls-files", "--error-unmatch", "--", path),
            cwd=LESSON_DIR,
            check=False,
        )
        if tracked.returncode != 0:
            raise CheckFailure(f"{path} is not tracked by Git")
        commits = git("log", "--format=%H", "--", path).splitlines()
        if len(commits) < 2:
            raise CheckFailure(
                f"{path} must have a student commit in addition to the template baseline"
            )


def check_committed(fields: Dict[str, str]) -> None:
    check_content(fields)
    require_fields(fields, ("PREDICT_AFTER_ADD",))
    check_exact_fields(fields, ("PREDICT_AFTER_ADD",))
    require_clean_and_committed(("profile.md", "message.txt"))


def require_upstream_sync() -> None:
    upstream = run(
        ("git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"),
        cwd=LESSON_DIR,
        check=False,
    )
    if upstream.returncode != 0 or not upstream.stdout.strip():
        raise CheckFailure(
            "the current branch has no upstream; push with git push -u origin <branch>"
        )
    counts = git("rev-list", "--left-right", "--count", "HEAD...@{upstream}")
    try:
        ahead, behind = (int(value) for value in counts.split())
    except Exception as exc:  # pragma: no cover - defensive parsing
        raise CheckFailure(f"could not parse ahead/behind counts: {counts!r}") from exc
    if ahead or behind:
        raise CheckFailure(
            f"local and upstream branches differ: ahead={ahead}, behind={behind}"
        )


def check_pushed(fields: Dict[str, str]) -> None:
    check_committed(fields)
    require_upstream_sync()


def check_final(fields: Dict[str, str]) -> None:
    check_pushed(fields)
    require_fields(fields, (*EXPECTED_FIELDS.keys(), *NARRATIVE_FIELDS, "CONTENT_COMMIT_ID"))
    check_exact_fields(fields, EXPECTED_FIELDS.keys())

    for name in NARRATIVE_FIELDS:
        minimum = 8 if name not in {"CURRENT_BRANCH", "REPOSITORY_ROOT", "ORIGIN_URL"} else 1
        require_nonplaceholder(f"workbook field {name}", fields[name], minimum=minimum)

    commit_id = fields["CONTENT_COMMIT_ID"]
    if not re.fullmatch(r"[0-9a-fA-F]{7,40}", commit_id):
        raise CheckFailure("CONTENT_COMMIT_ID must be a 7-40 character hexadecimal commit ID")
    commit_exists = run(
        ("git", "cat-file", "-e", f"{commit_id}^{{commit}}"),
        cwd=LESSON_DIR,
        check=False,
    )
    if commit_exists.returncode != 0:
        raise CheckFailure("CONTENT_COMMIT_ID does not identify a commit in this repository")

    root = str(repository_root())
    branch = git("branch", "--show-current")
    origin = git("remote", "get-url", "origin")
    if fields["REPOSITORY_ROOT"] != root:
        raise CheckFailure(f"REPOSITORY_ROOT must be exactly {root!r}")
    if fields["CURRENT_BRANCH"] != branch:
        raise CheckFailure(f"CURRENT_BRANCH must be exactly {branch!r}")
    if fields["ORIGIN_URL"] != origin:
        raise CheckFailure("ORIGIN_URL must exactly match 'git remote get-url origin'")
    if normalize_github_url(fields["FINAL_GITHUB_URL"]) != normalize_github_url(origin):
        raise CheckFailure("FINAL_GITHUB_URL must identify the origin GitHub repository")

    require_clean_and_committed(("profile.md", "message.txt", "workbook.md"))
    require_upstream_sync()


CHECKS = {
    "environment": check_environment,
    "content": check_content,
    "committed": check_committed,
    "pushed": check_pushed,
    "final": check_final,
}


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in CHECKS:
        choices = ", ".join(CHECKS)
        print(f"usage: {Path(sys.argv[0]).name} <{choices}>", file=sys.stderr)
        return 2
    checkpoint = sys.argv[1]
    try:
        fields = parse_workbook()
        CHECKS[checkpoint](fields)
    except CheckFailure as exc:
        print(f"[FAIL] {checkpoint}: {exc}", file=sys.stderr)
        return 1
    print(f"[PASS] {checkpoint}: all published checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
