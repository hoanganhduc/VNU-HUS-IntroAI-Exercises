#!/usr/bin/env python3
"""Completion-only checker for Week 0A.

The checker inspects the final files and Git history. It does not assess the
quality of the student's answers.
"""

from __future__ import annotations

import re
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

ASSIGNMENT_DIR = Path(__file__).resolve().parent
PLACEHOLDERS = ("REPLACE_THIS_TEXT", "TODO", "YOUR_ANSWER_HERE")
EXPECTED_MESSAGE = "Hello, Classroom50!"
USERNAME_RE = re.compile(r"[A-Za-z0-9](?:-?[A-Za-z0-9])*")


class CheckError(RuntimeError):
    """A completion requirement is missing."""


@dataclass(frozen=True)
class Commit:
    sha: str
    subject: str


def run_git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(ASSIGNMENT_DIR), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise CheckError(f"git {' '.join(args)} failed: {detail}")
    return result


def repository_root() -> Path:
    result = run_git("rev-parse", "--show-toplevel")
    return Path(result.stdout.strip()).resolve()


def relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(repository_root()).as_posix()
    except ValueError as exc:
        raise CheckError(f"{path} is outside the Git repository") from exc


def contains_placeholder(text: str) -> bool:
    upper = text.upper()
    return any(token in upper for token in PLACEHOLDERS)


def is_regular_file(path: Path) -> bool:
    try:
        return stat.S_ISREG(path.lstat().st_mode)
    except OSError:
        return False


def extract_section(text: str, heading: str) -> str:
    pattern = re.compile(
        rf"^## {re.escape(heading)}\s*$\n+(.*?)(?=^## |\Z)",
        flags=re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        raise CheckError(f"profile.md is missing the section '## {heading}'")
    return match.group(1).strip()


def check_files() -> None:
    profile = ASSIGNMENT_DIR / "profile.md"
    message = ASSIGNMENT_DIR / "message.txt"
    if not is_regular_file(profile):
        raise CheckError("profile.md must be a regular file, not a symbolic link")
    if not is_regular_file(message):
        raise CheckError("message.txt must be a regular file, not a symbolic link")

    try:
        profile_text = profile.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise CheckError(f"profile.md is not readable UTF-8 text: {exc}") from exc
    username = extract_section(profile_text, "GitHub username")
    goal = extract_section(profile_text, "One goal for this course")

    if not username or contains_placeholder(username):
        raise CheckError("the GitHub username in profile.md is not filled")
    if len(username) > 39 or USERNAME_RE.fullmatch(username) is None:
        raise CheckError("the GitHub username in profile.md has an invalid format")
    if len(goal) < 5 or contains_placeholder(goal):
        raise CheckError("the course goal in profile.md is not filled")

    try:
        message_lines = message.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise CheckError(f"message.txt is not readable UTF-8 text: {exc}") from exc
    if message_lines != [EXPECTED_MESSAGE]:
        raise CheckError(
            f"message.txt must contain exactly one line: {EXPECTED_MESSAGE!r}"
        )


def commits_at_head() -> list[Commit]:
    result = run_git("log", "--format=%H%x00%s", "HEAD")
    commits: list[Commit] = []
    for line in result.stdout.splitlines():
        if "\x00" not in line:
            continue
        sha, subject = line.split("\x00", 1)
        commits.append(Commit(sha=sha, subject=subject))
    if not commits:
        raise CheckError("the repository has no readable Git history")
    return commits


def changed_paths(commit: str) -> set[str]:
    result = run_git(
        "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", commit
    )
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def is_ancestor(older: str, newer: str) -> bool:
    return (
        run_git("merge-base", "--is-ancestor", older, newer, check=False).returncode
        == 0
    )


def matching_commits(subject: str, required_path: str) -> list[Commit]:
    return [
        commit
        for commit in commits_at_head()
        if commit.subject == subject and required_path in changed_paths(commit.sha)
    ]


def check_history() -> None:
    profile_path = relative_path(ASSIGNMENT_DIR / "profile.md")
    message_path = relative_path(ASSIGNMENT_DIR / "message.txt")

    profile_commits = matching_commits("Complete profile", profile_path)
    if not profile_commits:
        raise CheckError(
            'no commit named exactly "Complete profile" changes profile.md'
        )

    message_commits = matching_commits("Complete message", message_path)
    if not message_commits:
        raise CheckError(
            'no commit named exactly "Complete message" changes message.txt'
        )

    if not any(
        is_ancestor(profile_commit.sha, message_commit.sha)
        for profile_commit in profile_commits
        for message_commit in message_commits
    ):
        raise CheckError(
            'the "Complete profile" commit must occur before the '
            '"Complete message" commit'
        )


def report(label: str, check: Callable[[], None]) -> bool:
    try:
        check()
    except CheckError as exc:
        print(f"FAIL {label}: {exc}")
        return False
    print(f"PASS {label}")
    return True


def main() -> int:
    results = [
        report("required files and final content", check_files),
        report("prescribed Git commit history", check_history),
    ]
    if all(results):
        print("100/100 complete submission")
        print(
            "This is a completion score only; it does not assess academic correctness."
        )
        return 0
    print("0/100 incomplete submission")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
