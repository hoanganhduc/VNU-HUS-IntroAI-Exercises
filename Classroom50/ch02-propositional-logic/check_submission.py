#!/usr/bin/env python3
"""Check only that Week 2 contains a nonempty student code submission."""

from __future__ import annotations

import stat
import sys
import unicodedata
from pathlib import Path


SOLUTION = Path("solution")
IGNORED_NAMES = {
    ".gitkeep",
    "README.md",
    "README.txt",
}
PLACEHOLDER_ONLY = {
    b"REPLACE_THIS_TEXT",
    b"TODO",
    b"YOUR_SOLUTION_GOES_HERE",
}


def is_student_file(path: Path) -> bool:
    try:
        relative = path.relative_to(SOLUTION)
    except ValueError:
        return False

    if any(
        unicodedata.category(character) in {"Cc", "Cf"}
        for part in relative.parts
        for character in part
    ):
        return False

    current = SOLUTION
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            return False

    try:
        mode = path.lstat().st_mode
    except OSError:
        return False
    if not stat.S_ISREG(mode) or path.name in IGNORED_NAMES:
        return False
    if "__pycache__" in path.parts or path.suffix == ".pyc":
        return False
    try:
        content = path.read_bytes().strip()
    except OSError:
        return False
    if not content or content in PLACEHOLDER_ONLY:
        return False
    return True


def main() -> int:
    if not SOLUTION.exists() and not SOLUTION.is_symlink():
        print("FAIL required directory solution/ does not exist")
        print("\n0/100 incomplete submission")
        return 1
    if SOLUTION.is_symlink() or not SOLUTION.is_dir():
        print("FAIL solution/ must be a real directory, not a symbolic link")
        print("\n0/100 incomplete submission")
        return 1

    files = sorted(
        path.relative_to(SOLUTION)
        for path in SOLUTION.rglob("*")
        if is_student_file(path)
    )

    if not files:
        print(
            "FAIL solution/ contains no nonempty student file other than "
            "README or placeholder files"
        )
        print("\n0/100 incomplete submission")
        return 1

    print("PASS required directory solution/ exists")
    for path in files:
        print(f"PASS student file solution/{path} is nonempty")

    print("\n100/100 complete submission")
    print(
        "This is a completion score only. It does not assess whether the "
        "submitted work is mathematically, logically, algorithmically, or "
        "factually correct."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
