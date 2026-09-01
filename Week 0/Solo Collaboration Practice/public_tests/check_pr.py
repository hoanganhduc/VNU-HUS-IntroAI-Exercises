#!/usr/bin/env python3
"""Validate changed files in Solo Collaboration Practice pull requests."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Sequence

LESSON_REL = Path("Week 0/Solo Collaboration Practice")
PLACEHOLDERS = ("REPLACE_THIS_TEXT", "TODO_REVIEW", "YOUR_ANSWER_HERE")
ALLOWED_EXACT = {
    LESSON_REL / "team.json",
    LESSON_REL / "workbook.md",
    LESSON_REL / "shared/merge-practice.txt",
}
ALLOWED_DECISIONS = {
    "decision = base",
    "decision = proposal-alpha",
    "decision = proposal-beta",
    "decision = proposal-alpha + proposal-beta",
}
EXACT_WORKBOOK_FIELDS = {
    "TEAM_MODEL": "one-person-simulation",
    "SELF_APPROVAL": "impossible",
    "PROFILE_CHECK_FIRST_RESULT": "fail",
    "PROFILE_CHECK_AFTER_REPAIR": "pass",
    "CONFLICT_RESOLUTION": "proposal-alpha + proposal-beta",
}
REQUIRED_WORKBOOK_FIELDS = {
    "GITHUB_USERNAME",
    "TEAM_MODEL",
    "SELF_APPROVAL",
    "SELF_REVIEW_LIMITATION",
    "PROFILE_ISSUE_URL",
    "PROFILE_PR_URL",
    "CONFLICT_ALPHA_ISSUE_URL",
    "CONFLICT_ALPHA_PR_URL",
    "CONFLICT_BETA_ISSUE_URL",
    "CONFLICT_BETA_PR_URL",
    "FINAL_PR_URL",
    "FINAL_REPOSITORY_URL",
    "WHY_ISSUE_FIRST",
    "WHY_BRANCH",
    "PROFILE_CHECK_FIRST_RESULT",
    "PROFILE_CHECK_AFTER_REPAIR",
    "PR_VS_MERGE",
    "WHY_LOCAL_MAIN_NEEDED_PULL",
    "SELF_REVIEW_OBSERVATION",
    "CONFLICT_MARKERS_EXPLANATION",
    "CONFLICT_RESOLUTION",
    "SOLO_VS_REAL_GROUP",
}
URL_FIELDS = {
    "PROFILE_ISSUE_URL",
    "PROFILE_PR_URL",
    "CONFLICT_ALPHA_ISSUE_URL",
    "CONFLICT_ALPHA_PR_URL",
    "CONFLICT_BETA_ISSUE_URL",
    "CONFLICT_BETA_PR_URL",
    "FINAL_PR_URL",
    "FINAL_REPOSITORY_URL",
}


class Failure(RuntimeError):
    pass


def run(args: Sequence[str]) -> str:
    result = subprocess.run(
        list(args), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
    )
    if result.returncode != 0:
        raise Failure((result.stderr or result.stdout).strip())
    return result.stdout.strip()


def repository_root() -> Path:
    return Path(run(("git", "rev-parse", "--show-toplevel"))).resolve()


def contains_placeholder(text: str) -> bool:
    upper = text.upper()
    return any(token in upper for token in PLACEHOLDERS)


def section(text: str, heading: str) -> str:
    match = re.search(
        rf"^## {re.escape(heading)}\s*$\n+(.*?)(?=^## |\Z)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    if not match:
        raise Failure(f"missing heading '## {heading}'")
    return match.group(1).strip()


def validate_profile(path: Path) -> None:
    username = path.stem
    if path.name == "TEMPLATE.md":
        raise Failure("members/TEMPLATE.md must not be edited")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}", username):
        raise Failure(f"profile filename does not contain a valid GitHub username: {path.name}")
    text = path.read_text(encoding="utf-8")
    if contains_placeholder(text):
        raise Failure(f"{path} still contains a starter or review placeholder")
    required = (
        "GitHub username",
        "One useful Git command",
        "What the command does",
        "Pull-request self-review observation",
    )
    values = {name: section(text, name) for name in required}
    for name, value in values.items():
        if not value or len(value) < 2:
            raise Failure(f"{path}: section {name!r} is empty or too short")
    if values["GitHub username"] != username:
        raise Failure(
            f"{path}: GitHub username must exactly match the filename ({username})"
        )


def validate_team(path: Path) -> None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise Failure(f"team.json is invalid JSON: {exc}") from exc
    if set(data) != {"team_name", "members"}:
        raise Failure("team.json must have exactly the keys team_name and members")
    members = data["members"]
    if not isinstance(members, list) or len(members) != 1 or not isinstance(members[0], str):
        raise Failure("team.json members must contain exactly one GitHub username")
    username = members[0]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}", username):
        raise Failure("team.json contains an invalid GitHub username")
    if data["team_name"] != f"solo-{username}":
        raise Failure(f"team_name must be exactly 'solo-{username}'")


def parse_workbook(path: Path) -> Dict[str, str]:
    fields: Dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^([A-Z][A-Z0-9_]+):\s*(.*)$", line)
        if match:
            key, value = match.groups()
            if key in fields:
                raise Failure(f"workbook field {key} appears more than once")
            fields[key] = value.strip()
    return fields


def validate_workbook(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if contains_placeholder(text):
        raise Failure("workbook.md still contains a starter placeholder")
    fields = parse_workbook(path)
    missing = sorted(REQUIRED_WORKBOOK_FIELDS - fields.keys())
    if missing:
        raise Failure("workbook.md is missing fields: " + ", ".join(missing))
    for key, expected in EXACT_WORKBOOK_FIELDS.items():
        if fields[key] != expected:
            raise Failure(f"{key} must be exactly {expected!r}")
    for key in REQUIRED_WORKBOOK_FIELDS - set(EXACT_WORKBOOK_FIELDS):
        value = fields[key]
        if not value or len(value) < 4:
            raise Failure(f"workbook field {key} is empty or too short")
    for key in URL_FIELDS:
        if not re.fullmatch(r"https://github\.com/[^/\s]+/[^/\s]+(?:/(?:issues|pull)/\d+)?/?", fields[key]):
            raise Failure(f"workbook field {key} is not a supported GitHub URL")


def validate_merge_file(path: Path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) != 1 or lines[0] not in ALLOWED_DECISIONS:
        allowed = ", ".join(sorted(ALLOWED_DECISIONS))
        raise Failure(f"merge-practice.txt must contain one allowed line: {allowed}")


def reject_conflict_markers(path: Path) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return
    markers = ("<<<<<<<", "=======", ">>>>>>>")
    if any(marker in text for marker in markers):
        raise Failure(f"{path} contains unresolved Git conflict markers")


def changed_paths(base: str, head: str) -> List[Path]:
    output = run(("git", "diff", "--name-only", f"{base}...{head}"))
    return [Path(line) for line in output.splitlines() if line.strip()]


def main() -> int:
    if len(sys.argv) != 3:
        print(f"usage: {Path(sys.argv[0]).name} <base-sha> <head-sha>", file=sys.stderr)
        return 2
    base, head = sys.argv[1:]
    try:
        root = repository_root()
        paths = changed_paths(base, head)
        lesson_paths = [path for path in paths if path == LESSON_REL or LESSON_REL in path.parents]
        if not lesson_paths:
            raise Failure("the pull request does not change Solo Collaboration Practice files")

        for relative in lesson_paths:
            allowed_member = (
                relative.parent == LESSON_REL / "members"
                and relative.suffix == ".md"
                and relative.name != "TEMPLATE.md"
            )
            if relative not in ALLOWED_EXACT and not allowed_member:
                raise Failure(f"this lesson does not permit changing {relative}")
            path = root / relative
            if not path.exists():
                raise Failure(f"deleting {relative} is not permitted")
            reject_conflict_markers(path)
            if allowed_member:
                validate_profile(path)
            elif relative == LESSON_REL / "team.json":
                validate_team(path)
            elif relative == LESSON_REL / "workbook.md":
                validate_workbook(path)
            elif relative == LESSON_REL / "shared/merge-practice.txt":
                validate_merge_file(path)
    except Failure as exc:
        print(f"[FAIL] pull-request check: {exc}", file=sys.stderr)
        return 1
    print("[PASS] pull-request check: changed files satisfy the published contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
