#!/usr/bin/env python3
"""Final public checks for Week 0 Solo Collaboration Practice."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

LESSON_DIR = Path(__file__).resolve().parents[1]
PLACEHOLDERS = ("REPLACE_THIS_TEXT", "TODO_REVIEW", "YOUR_ANSWER_HERE")
EXACT_FIELDS = {
    "TEAM_MODEL": "one-person-simulation",
    "SELF_APPROVAL": "impossible",
    "PROFILE_CHECK_FIRST_RESULT": "fail",
    "PROFILE_CHECK_AFTER_REPAIR": "pass",
    "CONFLICT_RESOLUTION": "proposal-alpha + proposal-beta",
}
URL_FIELDS = (
    "PROFILE_ISSUE_URL",
    "PROFILE_PR_URL",
    "CONFLICT_ALPHA_ISSUE_URL",
    "CONFLICT_ALPHA_PR_URL",
    "CONFLICT_BETA_ISSUE_URL",
    "CONFLICT_BETA_PR_URL",
    "FINAL_PR_URL",
    "FINAL_REPOSITORY_URL",
)
NARRATIVE_FIELDS = (
    "SELF_REVIEW_LIMITATION",
    "WHY_ISSUE_FIRST",
    "WHY_BRANCH",
    "PR_VS_MERGE",
    "WHY_LOCAL_MAIN_NEEDED_PULL",
    "SELF_REVIEW_OBSERVATION",
    "CONFLICT_MARKERS_EXPLANATION",
    "SOLO_VS_REAL_GROUP",
)
FINAL_DECISION = "decision = proposal-alpha + proposal-beta"


class CheckFailure(RuntimeError):
    pass


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
        detail = (result.stderr or result.stdout).strip()
        raise CheckFailure(f"command failed: {' '.join(args)}\n{detail}")
    return result


def git(*args: str, check: bool = True) -> str:
    return run(("git", *args), cwd=LESSON_DIR, check=check).stdout.strip()


def repository_root() -> Path:
    try:
        return Path(git("rev-parse", "--show-toplevel")).resolve()
    except CheckFailure as exc:
        raise CheckFailure("run this checker inside the Git repository") from exc


def lesson_relative() -> Path:
    root = repository_root()
    try:
        return LESSON_DIR.relative_to(root)
    except ValueError as exc:
        raise CheckFailure("lesson directory is outside the detected repository") from exc


def contains_placeholder(text: str) -> bool:
    upper = text.upper()
    return any(token in upper for token in PLACEHOLDERS)


def normalize_github_url(url: str) -> str:
    value = url.strip()
    if value.startswith("git@github.com:"):
        value = "https://github.com/" + value[len("git@github.com:") :]
    elif value.startswith("ssh://git@github.com/"):
        value = "https://github.com/" + value[len("ssh://git@github.com/") :]
    if value.endswith(".git"):
        value = value[:-4]
    return value.rstrip("/")


def github_repository(url: str) -> Tuple[str, str]:
    normalized = normalize_github_url(url)
    match = re.fullmatch(r"https://github\.com/([^/]+)/([^/]+)", normalized)
    if not match:
        raise CheckFailure(f"not a supported GitHub repository URL: {url!r}")
    return match.group(1), match.group(2)


def parse_team() -> Tuple[str, str]:
    path = LESSON_DIR / "team.json"
    if not path.is_file():
        raise CheckFailure("team.json is missing")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CheckFailure(f"team.json is invalid JSON: {exc}") from exc
    if set(data) != {"team_name", "members"}:
        raise CheckFailure("team.json must have exactly team_name and members")
    members = data["members"]
    if not isinstance(members, list) or len(members) != 1 or not isinstance(members[0], str):
        raise CheckFailure("team.json must list exactly one member")
    username = members[0]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}", username):
        raise CheckFailure("team.json contains an invalid GitHub username")
    expected_name = f"solo-{username}"
    if data["team_name"] != expected_name:
        raise CheckFailure(f"team_name must be exactly {expected_name!r}")
    return username, data["team_name"]


def parse_workbook() -> Dict[str, str]:
    path = LESSON_DIR / "workbook.md"
    if not path.is_file():
        raise CheckFailure("workbook.md is missing")
    text = path.read_text(encoding="utf-8")
    if contains_placeholder(text):
        raise CheckFailure("workbook.md still contains a starter placeholder")
    fields: Dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^([A-Z][A-Z0-9_]+):\s*(.*)$", line)
        if match:
            key, value = match.groups()
            if key in fields:
                raise CheckFailure(f"workbook field {key} appears more than once")
            fields[key] = value.strip()
    required = {
        "GITHUB_USERNAME",
        *EXACT_FIELDS.keys(),
        *URL_FIELDS,
        *NARRATIVE_FIELDS,
    }
    missing = sorted(required - fields.keys())
    if missing:
        raise CheckFailure("workbook.md is missing fields: " + ", ".join(missing))
    for key, expected in EXACT_FIELDS.items():
        if fields[key] != expected:
            raise CheckFailure(f"{key} must be exactly {expected!r}")
    for key in NARRATIVE_FIELDS:
        if len(fields[key]) < 12:
            raise CheckFailure(f"workbook field {key} is empty or too short")
    return fields


def markdown_section(text: str, heading: str) -> str:
    match = re.search(
        rf"^## {re.escape(heading)}\s*$\n+(.*?)(?=^## |\Z)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    if not match:
        raise CheckFailure(f"profile is missing the heading '## {heading}'")
    return match.group(1).strip()


def check_profile(username: str) -> Path:
    path = LESSON_DIR / "members" / f"{username}.md"
    if not path.is_file():
        raise CheckFailure(f"missing member profile: members/{username}.md")
    text = path.read_text(encoding="utf-8")
    if contains_placeholder(text):
        raise CheckFailure("member profile still contains a starter or review placeholder")
    headings = (
        "GitHub username",
        "One useful Git command",
        "What the command does",
        "Pull-request self-review observation",
    )
    values = {heading: markdown_section(text, heading) for heading in headings}
    if values["GitHub username"] != username:
        raise CheckFailure("profile GitHub username does not match team.json")
    for heading, value in values.items():
        if len(value) < 2:
            raise CheckFailure(f"profile section {heading!r} is empty or too short")
    return path


def require_clean(paths: Iterable[Path]) -> None:
    root = repository_root()
    relative = [str(path.resolve().relative_to(root)) for path in paths]
    status = git("status", "--porcelain", "--", *relative)
    if status:
        raise CheckFailure("lesson files are not clean:\n" + status)
    for path in relative:
        tracked = run(
            ("git", "ls-files", "--error-unmatch", "--", path),
            cwd=LESSON_DIR,
            check=False,
        )
        if tracked.returncode != 0:
            raise CheckFailure(f"{path} is not tracked")
        if len(git("log", "--format=%H", "--", path).splitlines()) < 2:
            raise CheckFailure(f"{path} has no student commit beyond the template baseline")


def require_upstream_sync() -> None:
    upstream = run(
        ("git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"),
        cwd=LESSON_DIR,
        check=False,
    )
    if upstream.returncode != 0:
        raise CheckFailure("current branch has no upstream")
    counts = git("rev-list", "--left-right", "--count", "HEAD...@{upstream}")
    ahead, behind = (int(value) for value in counts.split())
    if ahead or behind:
        raise CheckFailure(f"local/upstream mismatch: ahead={ahead}, behind={behind}")


def find_resolution_commit(merge_path: Path) -> str:
    root = repository_root()
    relative = str(merge_path.resolve().relative_to(root))
    output = git("log", "--all", "--format=%H%x09%s", "--", relative)
    matches = []
    for line in output.splitlines():
        commit, _, subject = line.partition("\t")
        if subject == "Resolve solo merge conflict":
            matches.append(commit)
    if not matches:
        raise CheckFailure("could not find the commit 'Resolve solo merge conflict'")
    for commit in matches:
        parents = git("rev-list", "--parents", "-n", "1", commit).split()
        if len(parents) >= 3:
            ancestor = run(
                ("git", "merge-base", "--is-ancestor", commit, "HEAD"),
                cwd=LESSON_DIR,
                check=False,
            )
            if ancestor.returncode == 0:
                return commit
    raise CheckFailure(
        "the resolution commit must have two parents and be incorporated into the current branch"
    )


def check_local() -> Tuple[str, Dict[str, str]]:
    username, _ = parse_team()
    fields = parse_workbook()
    if fields["GITHUB_USERNAME"] != username:
        raise CheckFailure("GITHUB_USERNAME must match the sole team.json member")

    profile = check_profile(username)
    merge_path = LESSON_DIR / "shared" / "merge-practice.txt"
    if merge_path.read_text(encoding="utf-8").splitlines() != [FINAL_DECISION]:
        raise CheckFailure(f"merge-practice.txt must contain exactly {FINAL_DECISION!r}")
    find_resolution_commit(merge_path)

    origin = git("remote", "get-url", "origin")
    normalized = normalize_github_url(origin)
    if normalized.lower() == "https://github.com/hoanganhduc/vnu-hus-introai-exercises":
        raise CheckFailure("origin is the canonical repository, not a student repository")
    if normalize_github_url(fields["FINAL_REPOSITORY_URL"]) != normalized:
        raise CheckFailure("FINAL_REPOSITORY_URL must identify origin")
    for key in URL_FIELDS[:-1]:
        if not re.fullmatch(
            r"https://github\.com/[^/\s]+/[^/\s]+/(?:issues|pull)/\d+/?",
            fields[key],
        ):
            raise CheckFailure(f"{key} is not an issue or pull-request URL")

    require_clean(
        (
            LESSON_DIR / "team.json",
            LESSON_DIR / "workbook.md",
            profile,
            merge_path,
        )
    )
    require_upstream_sync()
    return username, fields


def gh_json(kind: str, url: str, fields: str) -> Dict[str, object]:
    result = run(("gh", kind, "view", url, "--json", fields), cwd=LESSON_DIR)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise CheckFailure(f"could not parse gh {kind} output for {url}") from exc


def login_of(value: object) -> str:
    if isinstance(value, dict):
        login = value.get("login")
        if isinstance(login, str):
            return login
    return ""


def ensure_same_repository(url: str, expected: Tuple[str, str]) -> None:
    match = re.match(r"https://github\.com/([^/]+)/([^/]+)/(?:issues|pull)/\d+/?$", url)
    if not match or (match.group(1), match.group(2)) != expected:
        raise CheckFailure(f"URL does not belong to the origin repository: {url}")


def check_issue(url: str, username: str, expected_repo: Tuple[str, str]) -> None:
    ensure_same_repository(url, expected_repo)
    data = gh_json("issue", url, "state,author,assignees,url")
    if data.get("state") != "CLOSED":
        raise CheckFailure(f"issue is not closed: {url}")
    if login_of(data.get("author")) != username:
        raise CheckFailure(f"issue author is not {username}: {url}")
    assignees = data.get("assignees")
    logins = {login_of(item) for item in assignees} if isinstance(assignees, list) else set()
    if username not in logins:
        raise CheckFailure(f"issue is not assigned to {username}: {url}")


def check_pr(
    url: str,
    username: str,
    expected_repo: Tuple[str, str],
    *,
    require_comment: bool = False,
    require_two_commits: bool = False,
    require_resolution_commit: bool = False,
) -> None:
    ensure_same_repository(url, expected_repo)
    data = gh_json(
        "pr",
        url,
        "state,isDraft,author,baseRefName,headRefName,mergedAt,mergeCommit,commits,comments,url",
    )
    if data.get("state") != "MERGED" or not data.get("mergedAt"):
        raise CheckFailure(f"pull request is not merged: {url}")
    if data.get("isDraft"):
        raise CheckFailure(f"pull request is still a draft: {url}")
    if login_of(data.get("author")) != username:
        raise CheckFailure(f"pull-request author is not {username}: {url}")
    if data.get("baseRefName") != "main":
        raise CheckFailure(f"pull request base must be main: {url}")
    if not data.get("mergeCommit"):
        raise CheckFailure(f"pull request has no merge commit: {url}")

    commits = data.get("commits")
    commit_list = commits if isinstance(commits, list) else []
    if require_two_commits and len(commit_list) < 2:
        raise CheckFailure(f"pull request must contain at least two commits: {url}")
    if require_resolution_commit:
        headlines = {
            item.get("messageHeadline")
            for item in commit_list
            if isinstance(item, dict)
        }
        if "Resolve solo merge conflict" not in headlines:
            raise CheckFailure(f"beta PR lacks the resolution commit: {url}")

    if require_comment:
        comments = data.get("comments")
        comment_list = comments if isinstance(comments, list) else []
        own_specific = [
            item
            for item in comment_list
            if isinstance(item, dict)
            and login_of(item.get("author")) == username
            and len(str(item.get("body", "")).strip()) >= 20
        ]
        if not own_specific:
            raise CheckFailure(f"pull request lacks the required specific self-review comment: {url}")


def check_github() -> None:
    if shutil.which("gh") is None:
        raise CheckFailure("GitHub CLI (gh) is not installed")
    auth = run(("gh", "auth", "status"), cwd=LESSON_DIR, check=False)
    if auth.returncode != 0:
        raise CheckFailure("GitHub CLI is not authenticated; run gh auth login")

    username, fields = check_local()
    current = run(("gh", "api", "user", "--jq", ".login"), cwd=LESSON_DIR).stdout.strip()
    if current != username:
        raise CheckFailure(f"authenticated GitHub account is {current!r}, expected {username!r}")

    origin = git("remote", "get-url", "origin")
    expected_repo = github_repository(origin)

    check_issue(fields["PROFILE_ISSUE_URL"], username, expected_repo)
    check_issue(fields["CONFLICT_ALPHA_ISSUE_URL"], username, expected_repo)
    check_issue(fields["CONFLICT_BETA_ISSUE_URL"], username, expected_repo)

    check_pr(
        fields["PROFILE_PR_URL"],
        username,
        expected_repo,
        require_comment=True,
        require_two_commits=True,
    )
    check_pr(fields["CONFLICT_ALPHA_PR_URL"], username, expected_repo)
    check_pr(
        fields["CONFLICT_BETA_PR_URL"],
        username,
        expected_repo,
        require_two_commits=True,
        require_resolution_commit=True,
    )
    check_pr(
        fields["FINAL_PR_URL"],
        username,
        expected_repo,
        require_comment=True,
        require_two_commits=True,
    )


CHECKS = {
    "local": lambda: check_local(),
    "github": check_github,
    "final": lambda: (check_local(), check_github()),
}


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in CHECKS:
        print("usage: check_solo.py <local|github|final>", file=sys.stderr)
        return 2
    mode = sys.argv[1]
    try:
        CHECKS[mode]()
    except CheckFailure as exc:
        print(f"[FAIL] {mode}: {exc}", file=sys.stderr)
        return 1
    print(f"[PASS] {mode}: all published checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
