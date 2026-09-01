#!/usr/bin/env python3
"""Completion-only checker for Week 0B.

The checker accepts one to five members and inspects only the final files and Git
history. It does not call the GitHub API or assess the quality of collaboration.
"""

from __future__ import annotations

import json
import re
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

ASSIGNMENT_DIR = Path(__file__).resolve().parent
PLACEHOLDERS = ("REPLACE_THIS_TEXT", "TODO", "YOUR_ANSWER_HERE")
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
    """Reject a file if it or a path component below the package is a symlink."""

    try:
        relative = path.relative_to(ASSIGNMENT_DIR)
    except ValueError:
        return False

    current = ASSIGNMENT_DIR
    try:
        for part in relative.parts[:-1]:
            current /= part
            mode = current.lstat().st_mode
            if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
                return False
        return stat.S_ISREG(path.lstat().st_mode)
    except OSError:
        return False


def require_answer(label: str, value: str, minimum: int = 1) -> None:
    cleaned = value.strip()
    if len(cleaned) < minimum or contains_placeholder(cleaned):
        raise CheckError(f"{label} is empty, too short, or still contains a placeholder")


def extract_section(text: str, heading: str, source: str) -> str:
    pattern = re.compile(
        rf"^## {re.escape(heading)}\s*$\n+(.*?)(?=^## |\Z)",
        flags=re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        raise CheckError(f"{source} is missing the section '## {heading}'")
    return match.group(1).strip()


def load_team() -> tuple[str, list[str]]:
    path = ASSIGNMENT_DIR / "team.json"
    if not is_regular_file(path):
        raise CheckError("team.json must be a regular file, not a symbolic link")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CheckError(f"team.json is not valid JSON: {exc}") from exc

    if not isinstance(data, dict) or set(data) != {"team_name", "members"}:
        raise CheckError("team.json must contain exactly team_name and members")

    team_name = data["team_name"]
    members = data["members"]
    if not isinstance(team_name, str):
        raise CheckError("team_name must be a string")
    require_answer("team_name", team_name, minimum=2)

    if not isinstance(members, list):
        raise CheckError("members must be a JSON array")
    if not 1 <= len(members) <= 5:
        raise CheckError("members must contain one to five GitHub usernames")
    if any(not isinstance(member, str) for member in members):
        raise CheckError("every members entry must be a string")
    if len({member.casefold() for member in members}) != len(members):
        raise CheckError("members contains a duplicate GitHub username")
    for member in members:
        if len(member) > 39 or USERNAME_RE.fullmatch(member) is None:
            raise CheckError(f"invalid GitHub username in members: {member!r}")
    return team_name, members


def check_profile(member: str) -> None:
    path = ASSIGNMENT_DIR / "members" / f"{member}.md"
    if not is_regular_file(path):
        raise CheckError(
            f"members/{member}.md must be a regular file, not a symbolic link"
        )
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise CheckError(
            f"members/{member}.md is not readable UTF-8 text: {exc}"
        ) from exc
    username = extract_section(text, "GitHub username", path.name)
    command = extract_section(text, "One Git command I used", path.name)
    explanation = extract_section(text, "What the command does", path.name)
    if username != member:
        raise CheckError(
            f"the username inside members/{member}.md must be exactly {member!r}"
        )
    require_answer(f"command in members/{member}.md", command, minimum=2)
    require_answer(
        f"command explanation in members/{member}.md", explanation, minimum=5
    )


def check_summary() -> None:
    path = ASSIGNMENT_DIR / "summary.md"
    if not is_regular_file(path):
        raise CheckError("summary.md must be a regular file, not a symbolic link")
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise CheckError(f"summary.md is not readable UTF-8 text: {exc}") from exc
    for heading in (
        "What a branch is for",
        "What a pull request is for",
        "What merging does",
    ):
        value = extract_section(text, heading, "summary.md")
        require_answer(f"summary section {heading!r}", value, minimum=5)


def check_files() -> list[str]:
    _, members = load_team()
    for member in members:
        check_profile(member)
    check_summary()
    return members


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


def parents(commit: str) -> list[str]:
    result = run_git("rev-list", "--parents", "-n", "1", commit)
    fields = result.stdout.strip().split()
    return fields[1:]


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


def contribution_merge(contribution: str) -> str | None:
    """Return a merge that introduced contribution from a non-first parent."""
    result = run_git("rev-list", "--merges", "HEAD")
    for merge in result.stdout.splitlines():
        merge_parents = parents(merge)
        if len(merge_parents) < 2:
            continue
        if is_ancestor(contribution, merge_parents[0]):
            continue
        if any(is_ancestor(contribution, parent) for parent in merge_parents[1:]):
            return merge
    return None


def check_history_for_team(members: list[str]) -> None:
    team_path = relative_path(ASSIGNMENT_DIR / "team.json")
    summary_path = relative_path(ASSIGNMENT_DIR / "summary.md")
    team_commits = matching_commits("Set team members", team_path)
    if not team_commits:
        raise CheckError('no commit named exactly "Set team members" changes team.json')

    failures: list[str] = []
    for team_commit in team_commits:
        selected_merges: list[str] = []
        attempt_error: str | None = None

        for member in members:
            profile_path = relative_path(
                ASSIGNMENT_DIR / "members" / f"{member}.md"
            )
            candidates = matching_commits(f"Add profile for {member}", profile_path)
            candidates = [
                candidate
                for candidate in candidates
                if is_ancestor(team_commit.sha, candidate.sha)
            ]
            if not candidates:
                attempt_error = (
                    f'no commit named exactly "Add profile for {member}" changes '
                    f"members/{member}.md after the team commit"
                )
                break

            merge = None
            for candidate in candidates:
                merge = contribution_merge(candidate.sha)
                if merge is not None:
                    break
            if merge is None:
                attempt_error = (
                    f"the profile contribution for {member} is not introduced through "
                    "a merge commit"
                )
                break
            selected_merges.append(merge)

        if attempt_error is not None:
            failures.append(attempt_error)
            continue

        final_commits = matching_commits("Complete group submission", summary_path)
        valid_final = next(
            (
                commit
                for commit in final_commits
                if all(is_ancestor(merge, commit.sha) for merge in selected_merges)
            ),
            None,
        )
        if valid_final is None:
            failures.append(
                'no commit named exactly "Complete group submission" changes '
                "summary.md after all profile merges"
            )
            continue

        return

    detail = failures[0] if failures else "the prescribed Git history is incomplete"
    raise CheckError(detail)


def report(label: str, check: Callable[[], object]) -> tuple[bool, object | None]:
    try:
        value = check()
    except CheckError as exc:
        print(f"FAIL {label}: {exc}")
        return False, None
    print(f"PASS {label}")
    return True, value


def main() -> int:
    files_ok, members_value = report("required files and final content", check_files)
    history_ok = False
    if files_ok and isinstance(members_value, list):
        history_ok, _ = report(
            "prescribed Git branch-and-merge history",
            lambda: check_history_for_team(members_value),
        )
    else:
        print("FAIL prescribed Git branch-and-merge history: file checks must pass first")

    if files_ok and history_ok:
        print("100/100 complete submission")
        print(
            "This is a completion score only; it does not assess academic correctness "
            "or the quality of collaboration."
        )
        return 0
    print("0/100 incomplete submission")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
