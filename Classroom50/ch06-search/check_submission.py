#!/usr/bin/env python3
"""Check only the observable completeness of the Week 6 submission."""

from __future__ import annotations

import json
import stat
import sys
import unicodedata
from pathlib import Path, PurePosixPath
from typing import Any


SOLUTION = Path("solution")
MANIFEST = Path("submission.json")
EXPLANATION = Path("explanation.md")
MANIFEST_FIELDS = (
    "exercise_6_6_files",
    "exercise_6_12_files",
)
EXPLANATION_FIELD = "EXERCISE_6_6_DFS_EXPLANATION"
PLACEHOLDERS = (
    "REPLACE_THIS_TEXT",
    "TODO",
    "YOUR_SOLUTION_GOES_HERE",
)
PLACEHOLDER_ONLY = {token.encode("utf-8") for token in PLACEHOLDERS}
SUPPLIED_NON_SUBMISSIONS = {PurePosixPath("README.md")}


def marked_value(text: str, name: str) -> tuple[str | None, list[str]]:
    begin = f"<!-- BEGIN:{name} -->"
    end = f"<!-- END:{name} -->"
    errors: list[str] = []
    if text.count(begin) != 1:
        errors.append(f"{begin} must occur exactly once (found {text.count(begin)})")
    if text.count(end) != 1:
        errors.append(f"{end} must occur exactly once (found {text.count(end)})")
    if errors:
        return None, errors

    start = text.index(begin) + len(begin)
    stop = text.index(end)
    if stop < start:
        errors.append(f"{begin} must occur before {end}")
        return None, errors
    return text[start:stop].strip(), []


def declared_paths(
    data: dict[str, Any], field: str, failures: list[str]
) -> list[PurePosixPath]:
    value = data[field]
    if not isinstance(value, list):
        failures.append(f"{field} must be a JSON array")
        return []
    if not value:
        failures.append(f"{field} must list at least one file under solution/")
        return []

    paths: list[PurePosixPath] = []
    for index, raw_path in enumerate(value):
        label = f"{field}[{index}]"
        if not isinstance(raw_path, str):
            failures.append(f"{label} must be a string")
            continue
        if (
            not raw_path
            or "\\" in raw_path
            or any(
                unicodedata.category(character) in {"Cc", "Cf"}
                for character in raw_path
            )
        ):
            failures.append(
                f"{label} must be a nonempty forward-slash path relative to solution/"
            )
            continue

        relative = PurePosixPath(raw_path)
        if (
            relative.is_absolute()
            or not relative.parts
            or any(part in {".", ".."} for part in relative.parts)
            or relative.as_posix() != raw_path
        ):
            failures.append(f"{label} must be a safe path relative to solution/")
            continue
        if relative in SUPPLIED_NON_SUBMISSIONS:
            failures.append(
                f"{label} must name student work, not supplied solution/{relative}"
            )
            continue
        paths.append(relative)
    return paths


def check_declared_file(
    field: str, relative: PurePosixPath, failures: list[str], passes: list[str]
) -> None:
    candidate = SOLUTION
    for part in relative.parts:
        candidate /= part
        if candidate.is_symlink():
            failures.append(f"{field} references symbolic link solution/{relative}")
            return

    try:
        mode = candidate.lstat().st_mode
    except (OSError, ValueError) as error:
        failures.append(f"{field} references missing file solution/{relative}: {error}")
        return
    if not stat.S_ISREG(mode):
        failures.append(f"{field} must reference a regular file: solution/{relative}")
        return

    try:
        content = candidate.read_bytes().strip()
    except OSError as error:
        failures.append(f"cannot read solution/{relative}: {error}")
        return
    if not content:
        failures.append(f"{field} references empty file solution/{relative}")
    elif content in PLACEHOLDER_ONLY:
        failures.append(f"{field} references placeholder-only file solution/{relative}")
    else:
        passes.append(f"{field} declares nonempty regular file solution/{relative}")


def main() -> int:
    failures: list[str] = []
    passes: list[str] = []

    solution_is_directory = SOLUTION.is_dir() and not SOLUTION.is_symlink()
    if not solution_is_directory:
        failures.append("solution/ must be a real directory, not a symbolic link")
    else:
        passes.append("required directory solution/ exists")

    data: Any = None
    manifest_loaded = False
    if MANIFEST.is_symlink() or not MANIFEST.is_file():
        failures.append(f"{MANIFEST} must be a regular file, not a symbolic link")
    else:
        try:
            data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            failures.append(f"cannot read {MANIFEST} as UTF-8 JSON: {error}")
        else:
            manifest_loaded = True
            passes.append(f"{MANIFEST} is valid JSON")

    if manifest_loaded:
        if not isinstance(data, dict):
            failures.append(f"{MANIFEST} must contain a JSON object at its top level")
        elif set(data) != set(MANIFEST_FIELDS):
            failures.append(
                f"{MANIFEST} must contain exactly " + " and ".join(MANIFEST_FIELDS)
            )
        else:
            for field in MANIFEST_FIELDS:
                for relative in declared_paths(data, field, failures):
                    if solution_is_directory:
                        check_declared_file(field, relative, failures, passes)

    if EXPLANATION.is_symlink() or not EXPLANATION.is_file():
        failures.append(f"{EXPLANATION} must be a regular file, not a symbolic link")
    else:
        try:
            text = EXPLANATION.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            failures.append(f"cannot read {EXPLANATION} as UTF-8 text: {error}")
        else:
            value, errors = marked_value(text, EXPLANATION_FIELD)
            failures.extend(errors)
            if value is not None:
                if not value:
                    failures.append(f"explanation field {EXPLANATION_FIELD} is empty")
                elif any(token in value for token in PLACEHOLDERS):
                    failures.append(
                        f"explanation field {EXPLANATION_FIELD} still contains "
                        "a starter placeholder"
                    )
                else:
                    passes.append(f"explanation field {EXPLANATION_FIELD} is filled")

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
