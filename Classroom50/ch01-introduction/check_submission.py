#!/usr/bin/env python3
"""Check only the observable completeness of the Week 1 submission."""

from __future__ import annotations

import stat
import sys
from pathlib import Path


SUBMISSION = Path("submission.md")
PROSE_FIELDS = ("RESPONSE",)
PLACEHOLDERS = (
    "REPLACE_THIS_TEXT",
    "TODO",
)


def is_regular_file(path: Path) -> bool:
    try:
        return stat.S_ISREG(path.lstat().st_mode)
    except OSError:
        return False


def field_value(text: str, name: str) -> tuple[str | None, list[str]]:
    """Return one marked field and diagnostics about missing/duplicate markers."""

    begin = f"<!-- BEGIN:{name} -->"
    end = f"<!-- END:{name} -->"
    errors: list[str] = []

    begin_count = text.count(begin)
    end_count = text.count(end)
    if begin_count != 1:
        errors.append(f'{begin} must occur exactly once (found {begin_count})')
    if end_count != 1:
        errors.append(f'{end} must occur exactly once (found {end_count})')
    if errors:
        return None, errors

    start = text.index(begin) + len(begin)
    stop = text.index(end)
    if stop < start:
        errors.append(f"{begin} must occur before {end}")
        return None, errors
    return text[start:stop].strip(), []


def main() -> int:
    failures: list[str] = []
    passes: list[str] = []

    if not is_regular_file(SUBMISSION):
        print(
            f"FAIL required file {SUBMISSION} must be a regular file, "
            "not a symbolic link"
        )
        print("\n0/100 incomplete submission")
        return 1

    try:
        text = SUBMISSION.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        print(f"FAIL cannot read {SUBMISSION} as UTF-8 text: {error}")
        print("\n0/100 incomplete submission")
        return 1
    passes.append(f"required file {SUBMISSION} exists")

    values: dict[str, str] = {}
    for name in PROSE_FIELDS:
        value, errors = field_value(text, name)
        failures.extend(errors)
        if value is not None:
            values[name] = value
            passes.append(f"field markers for {name} occur exactly once")

    for name in PROSE_FIELDS:
        value = values.get(name)
        if value is None:
            continue
        if not value:
            failures.append(f"field {name} is empty")
        elif any(token in value for token in PLACEHOLDERS):
            failures.append(f"field {name} still contains a starter placeholder")
        else:
            passes.append(f"field {name} is filled")

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
