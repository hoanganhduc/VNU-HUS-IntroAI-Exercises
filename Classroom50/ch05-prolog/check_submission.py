#!/usr/bin/env python3
"""Check only the observable completeness of the Week 5 submission."""

from __future__ import annotations

import stat
import sys
from pathlib import Path


PROLOG_FILES = (
    Path("plan2.pl"),
    Path("ones.pl"),
    Path("fib.pl"),
    Path("fib01.pl"),
)
ANSWERS = Path("answers.md")
FIELDS = (
    "EXERCISE_5_3_ANSWERS",
    "EXERCISE_5_8_ANSWERS",
)
PLACEHOLDERS = ("REPLACE_THIS_TEXT", "TODO")


def marked_value(text: str, name: str) -> tuple[str | None, list[str]]:
    begin = f"<!-- BEGIN:{name} -->"
    end = f"<!-- END:{name} -->"
    errors: list[str] = []
    if text.count(begin) != 1:
        errors.append(f'{begin} must occur exactly once (found {text.count(begin)})')
    if text.count(end) != 1:
        errors.append(f'{end} must occur exactly once (found {text.count(end)})')
    if errors:
        return None, errors
    start = text.index(begin) + len(begin)
    stop = text.index(end)
    if stop < start:
        errors.append(f"{begin} must occur before {end}")
        return None, errors
    return text[start:stop].strip(), []


def has_substantive_prolog_line(path: Path) -> bool:
    """Return whether a target has a nonblank line other than a `%` comment."""

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("%"):
            return True
    return False


def is_regular_file(path: Path) -> bool:
    """Return whether a required target is a real regular file."""

    try:
        return stat.S_ISREG(path.lstat().st_mode)
    except OSError:
        return False


def main() -> int:
    failures: list[str] = []
    passes: list[str] = []

    for path in PROLOG_FILES:
        if not is_regular_file(path):
            failures.append(
                f"required file {path} must be a regular file, not a symbolic link"
            )
        else:
            try:
                substantive = has_substantive_prolog_line(path)
            except (OSError, UnicodeError) as error:
                failures.append(f"cannot read {path} as UTF-8 text: {error}")
            else:
                if not substantive:
                    failures.append(
                        f"{path} contains no nonblank, noncomment student content"
                    )
                else:
                    passes.append(f"{path} contains noncomment content")

    if not is_regular_file(ANSWERS):
        failures.append(
            f"required file {ANSWERS} must be a regular file, not a symbolic link"
        )
    else:
        try:
            text = ANSWERS.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            failures.append(f"cannot read {ANSWERS} as UTF-8 text: {error}")
        else:
            for name in FIELDS:
                value, errors = marked_value(text, name)
                failures.extend(errors)
                if value is None:
                    continue
                if not value:
                    failures.append(f"written-answer field {name} is empty")
                elif any(token in value for token in PLACEHOLDERS):
                    failures.append(
                        "written-answer field "
                        f"{name} still contains a starter placeholder"
                    )
                else:
                    passes.append(f"written-answer field {name} is filled")

    for message in passes:
        print(f"PASS {message}")
    for message in failures:
        print(f"FAIL {message}")

    if failures:
        print("\n0/100 incomplete submission")
        return 1

    print("\n100/100 complete submission")
    print(
        "This is a completion score only. It does not assess whether the "
        "submitted work is mathematically, logically, algorithmically, or "
        "factually correct."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
