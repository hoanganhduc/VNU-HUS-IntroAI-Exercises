#!/usr/bin/env python3
"""Validate and export the public Classroom50 scaffold packages."""

from __future__ import annotations

import sys

if not sys.flags.isolated:
    sys.stderr.write(
        "ERROR: run this tool in isolated mode: "
        "python3 -I Classroom50/tools/template_tool.py ...\n"
    )
    raise SystemExit(2)

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tempfile
import unicodedata
from typing import Any, Iterable


CATALOG_PATH = PurePosixPath("Classroom50/catalog.json")
PROVENANCE_BEGIN = "<!-- SOURCE-PROVENANCE:BEGIN -->"
PROVENANCE_END = "<!-- SOURCE-PROVENANCE:END -->"
EXPECTED_SOURCE_REPOSITORY = "hoanganhduc/VNU-HUS-IntroAI-Exercises"
EXPECTED_SOURCE_REPOSITORY_ID = 1353117837
EXPECTED_SLUGS = (
    "w00-individual-onboarding",
    "w00-group-collaboration",
    "ch01-introduction",
    "ch02-propositional-logic",
    "ch03-first-order-logic",
    "ch04-limitations-of-logic",
    "ch05-prolog",
    "ch06-search",
    "ch07-uncertainty",
)
EXPECTED_REFERENCES = {
    "w00-individual-onboarding": (),
    "w00-group-collaboration": (),
    "ch01-introduction": ("1.1",),
    "ch02-propositional-logic": ("2.5",),
    "ch03-first-order-logic": ("3.9",),
    "ch04-limitations-of-logic": ("4.3",),
    "ch05-prolog": ("5.2", "5.3", "5.5", "5.8"),
    "ch06-search": ("6.6", "6.12"),
    "ch07-uncertainty": ("7.9", "7.10"),
}
EXPECTED_SHARED_FILES = {
    (".devcontainer/devcontainer-lock.json", ".devcontainer/devcontainer-lock.json"),
    (".devcontainer/devcontainer.json", ".devcontainer/devcontainer.json"),
    ("LICENSE", "LICENSE"),
    ("LICENSES/CC-BY-4.0.md", "LICENSES/CC-BY-4.0.md"),
    ("LICENSES/MIT.txt", "LICENSES/MIT.txt"),
    ("THIRD-PARTY-MATERIALS.md", "THIRD-PARTY-MATERIALS.md"),
}
EXPECTED_ASSIGNMENT_KEYS = {
    "slug",
    "title",
    "status",
    "package",
    "classroom50",
    "student_files",
    "teacher_files",
    "references",
}
EXPECTED_LICENSE_POLICY = {
    "code_and_configuration": "MIT",
    "original_instructional_prose": "CC-BY-4.0",
    "third_party_materials": "excluded",
}
EXPECTED_WORKFLOW_SHA256 = {
    ".github/workflows/classroom50-templates.yml": (
        "a9fff4a147dab4767ad5928be1e9283ac6f58640a225015aa85803ea295eab6c"
    ),
    ".github/workflows/week0-solo-collaboration.yml": (
        "5deb14a92c4031cfdf4d740d98a8e97fbea6e6c7eb5a757b68f332e1b9658476"
    ),
}
LICENSE_BY_CLASSIFICATION = {
    "code": "MIT",
    "configuration": "MIT",
    "instructional-prose": "CC-BY-4.0",
    "cc-license-notice": "CC-BY-4.0",
    "mit-license-text": "MIT",
}
ALLOWED_ORIGINS = {"course-authored", "standard-license-text"}
DENIED_EXTENSIONS = {
    ".7z",
    ".bz2",
    ".gz",
    ".jar",
    ".pdf",
    ".rar",
    ".tar",
    ".tex",
    ".tgz",
    ".xz",
    ".zip",
}
DENIED_CONTENT_SHA256 = {
    "152164797cd727dfe445895cfdb6434e6de548d938c8cb57d0ebfe24d4e2c203",
    "d173b56fe7c90c4c04d4db2ca59e8d547cd70f03b8cd5e24b28d2495d1134a6c",
}
DENIED_PROLOG_SIMHASHES = {
    0x1E5680EDC7F4E378,
    0xFAC648652BE531E6,
}
TOKEN_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|[0-9]+|[^\s]")
SECRET_PATTERNS = (
    re.compile(rb"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(rb"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(rb"AKIA[0-9A-Z]{16}"),
    re.compile(rb"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
)


class TemplateError(RuntimeError):
    """A catalog, boundary, validation, or export error safe to show."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_json(path: Path) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise TemplateError(f"cannot read valid JSON from {path}: {exc}") from exc


def _safe_relative_path(value: Any, context: str) -> PurePosixPath:
    if not isinstance(value, str) or not value:
        raise TemplateError(f"{context} must be a nonempty relative POSIX path")
    if "\\" in value:
        raise TemplateError(f"{context} must use POSIX '/' separators: {value!r}")
    if any(unicodedata.category(character) in {"Cc", "Cf"} for character in value):
        raise TemplateError(
            f"{context} must not contain control or formatting characters: {value!r}"
        )
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or str(path) != value
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise TemplateError(
            f"{context} is not a normalized safe relative path: {value!r}"
        )
    return path


def _first_symlink_component(path: Path, boundary: Path | None = None) -> Path | None:
    if boundary is None:
        path = Path(os.path.abspath(path))
        current = Path(path.anchor)
        parts = path.parts[1:]
    else:
        try:
            relative = path.relative_to(boundary)
        except ValueError:
            return path
        current = boundary
        parts = relative.parts
    for part in parts:
        current /= part
        if current.is_symlink():
            return current
    return None


def _regular_file(
    path: Path,
    context: str,
    errors: list[str],
    boundary: Path | None = None,
) -> bool:
    symlink = _first_symlink_component(path, boundary)
    if symlink is not None:
        errors.append(f"{context} has a symbolic-link path component: {symlink}")
        return False
    if not path.is_file():
        errors.append(f"{context} is missing or is not a regular file: {path}")
        return False
    return True


def _tree_files(directory: Path) -> set[str]:
    if not directory.is_dir() or directory.is_symlink():
        return set()
    files: set[str] = set()
    for path in directory.rglob("*"):
        relative = path.relative_to(directory)
        if not relative.parts:
            continue
        if relative.parts[0] == ".git":
            continue
        if "__pycache__" in relative.parts or path.suffix == ".pyc":
            continue
        if path.is_file() or path.is_symlink():
            files.add(relative.as_posix())
    return files


def _validate_git_index(repo_root: Path, errors: list[str]) -> None:
    """Reject committed symlinks, gitlinks, and other non-file entries."""

    if not (repo_root / ".git").exists():
        return
    try:
        reported_root = Path(
            _git(repo_root, ["rev-parse", "--show-toplevel"])
            .stdout.decode("utf-8")
            .strip()
        ).resolve()
        if reported_root != repo_root.resolve():
            errors.append(
                f"public source is inside another Git worktree: {reported_root}"
            )
            return
        output = _git(repo_root, ["ls-files", "--stage", "-z"]).stdout
    except (TemplateError, UnicodeDecodeError) as exc:
        errors.append(f"cannot validate public Git index: {exc}")
        return
    for record in output.split(b"\0"):
        if not record:
            continue
        try:
            header, encoded_path = record.split(b"\t", 1)
            mode, _object_id, stage = header.split()
            relative = encoded_path.decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            errors.append("public Git index contains an unreadable entry")
            continue
        if stage != b"0" or mode not in {b"100644", b"100755"}:
            errors.append(
                "public Git index contains a non-file entry "
                f"(mode {mode.decode('ascii', errors='replace')}, "
                f"stage {stage.decode('ascii', errors='replace')}): {relative}"
            )


def _validate_workflows(repo_root: Path, errors: list[str]) -> None:
    """Require the two explicitly reviewed, credential-minimized workflows."""

    for relative, expected_digest in EXPECTED_WORKFLOW_SHA256.items():
        path = repo_root / PurePosixPath(relative)
        if not _regular_file(path, f"approved workflow {relative}", errors, repo_root):
            continue
        actual_digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual_digest != expected_digest:
            errors.append(f"approved workflow differs from reviewed bytes: {relative}")


def _expect_exact_keys(
    value: Any,
    required: set[str],
    optional: set[str],
    context: str,
    errors: list[str],
) -> bool:
    if not isinstance(value, dict):
        errors.append(f"{context} must be an object")
        return False
    keys = set(value)
    missing = required - keys
    unknown = keys - required - optional
    if missing:
        errors.append(f"{context} is missing keys: {', '.join(sorted(missing))}")
    if unknown:
        errors.append(f"{context} has unknown keys: {', '.join(sorted(unknown))}")
    return not missing and not unknown


def load_catalog(repo_root: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    catalog_path = repo_root / CATALOG_PATH
    symlink = _first_symlink_component(catalog_path, repo_root)
    if symlink is not None:
        raise TemplateError(f"catalog has a symbolic-link path component: {symlink}")
    catalog = _load_json(catalog_path)
    if not isinstance(catalog, dict):
        raise TemplateError("Classroom50/catalog.json must contain a JSON object")
    return catalog


def _strip_jsonc_comments(text: str) -> str:
    output: list[str] = []
    index = 0
    in_string = False
    escaped = False
    while index < len(text):
        character = text[index]
        if in_string:
            output.append(character)
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            index += 1
            continue
        if character == '"':
            in_string = True
            output.append(character)
            index += 1
            continue
        if character == "/" and index + 1 < len(text):
            marker = text[index + 1]
            if marker == "/":
                output.extend("  ")
                index += 2
                while index < len(text) and text[index] not in "\r\n":
                    output.append(" ")
                    index += 1
                continue
            if marker == "*":
                output.extend("  ")
                index += 2
                while index + 1 < len(text) and text[index : index + 2] != "*/":
                    output.append(text[index] if text[index] in "\r\n" else " ")
                    index += 1
                if index + 1 >= len(text):
                    raise ValueError("unterminated block comment")
                output.extend("  ")
                index += 2
                continue
        output.append(character)
        index += 1
    return "".join(output)


def _strip_jsonc_trailing_commas(text: str) -> str:
    output: list[str] = []
    index = 0
    in_string = False
    escaped = False
    while index < len(text):
        character = text[index]
        if in_string:
            output.append(character)
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            index += 1
            continue
        if character == '"':
            in_string = True
            output.append(character)
            index += 1
            continue
        if character == ",":
            following = index + 1
            while following < len(text) and text[following].isspace():
                following += 1
            if following < len(text) and text[following] in "}]":
                output.append(" ")
                index += 1
                continue
        output.append(character)
        index += 1
    return "".join(output)


def _reject_duplicate_jsonc_properties(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate property: {key}")
        result[key] = value
    return result


def _load_jsonc(text: str, context: str) -> Any:
    try:
        uncommented = _strip_jsonc_comments(text)
        normalized = _strip_jsonc_trailing_commas(uncommented)
        return json.loads(
            normalized,
            object_pairs_hook=_reject_duplicate_jsonc_properties,
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise TemplateError(f"cannot read valid JSONC from {context}: {exc}") from exc


def _trusted_run_command(checker_digest: str) -> str:
    return (
        "python3 -I -c 'import hashlib,os,stat; p=\"check_submission.py\"; "
        "fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW); "
        "stat.S_ISREG(os.fstat(fd).st_mode) or (_ for _ in ()).throw("
        "SystemExit(\"FAIL check_submission.py is not a regular file\")); "
        "f=os.fdopen(fd,\"rb\"); b=f.read(); f.close(); "
        "actual=hashlib.sha256(b).hexdigest(); "
        f"expected=\"{checker_digest}\"; "
        "actual==expected or (_ for _ in ()).throw("
        "SystemExit(\"FAIL untrusted check_submission.py\")); "
        "exec(compile(b,p,\"exec\"),{\"__name__\":\"__main__\",\"__file__\":p})'"
    )


def _validate_test_contract(
    repo_root: Path,
    package_dir: Path,
    slug: str,
    errors: list[str],
) -> None:
    checker = package_dir / "check_submission.py"
    tests_path = package_dir / "classroom50-tests.json"
    if not (
        _regular_file(checker, f"{slug} public checker", errors, repo_root)
        and _regular_file(
            tests_path,
            f"{slug} teacher test definition",
            errors,
            repo_root,
        )
    ):
        return
    try:
        tests = _load_json(tests_path)
    except TemplateError as exc:
        errors.append(str(exc))
        return
    if (
        not isinstance(tests, list)
        or len(tests) != 1
        or not isinstance(tests[0], dict)
    ):
        errors.append(
            f"{slug} test definition must contain exactly one declarative test"
        )
        return
    test = tests[0]
    if (
        test.get("type") != "run"
        or test.get("timeout") != 30
        or test.get("points") != 100
    ):
        errors.append(
            f"{slug} test must be one 100-point run test with a 30-second timeout"
        )
    if set(test) != {"name", "type", "run", "timeout", "points"}:
        errors.append(f"{slug} test has unexpected or missing fields")
    if not isinstance(test.get("name"), str) or not test["name"].strip():
        errors.append(f"{slug} test name must be nonempty")
    command = test.get("run")
    if not isinstance(command, str):
        errors.append(f"{slug} run command must be a string")
        return
    expected_digest = hashlib.sha256(checker.read_bytes()).hexdigest()
    if command != _trusted_run_command(expected_digest):
        errors.append(
            f"{slug} run command must exactly match the trusted checker runner for "
            f"SHA-256 {expected_digest}"
        )


def _simhash(text: str) -> tuple[int, int]:
    tokens = TOKEN_PATTERN.findall(text.casefold())
    if len(tokens) < 4:
        return 0, len(tokens)
    shingles = ["\0".join(tokens[index : index + 4]) for index in range(len(tokens) - 3)]
    weights = [0] * 64
    for shingle in shingles:
        value = int.from_bytes(
            hashlib.sha256(shingle.encode("utf-8")).digest()[:8],
            "big",
        )
        for bit in range(64):
            weights[bit] += 1 if value & (1 << bit) else -1
    fingerprint = sum(
        (1 << bit) for bit, weight in enumerate(weights) if weight >= 0
    )
    return fingerprint, len(tokens)


def _expected_public_classification(relative: str) -> str | None:
    if relative == "LICENSES/MIT.txt":
        return "mit-license-text"
    if relative == "LICENSES/CC-BY-4.0.md":
        return "cc-license-notice"
    name = PurePosixPath(relative).name
    suffix = unicodedata.normalize(
        "NFKC", PurePosixPath(relative).suffix
    ).casefold()
    if suffix in {".py", ".sh", ".pl", ".lop"}:
        return "code"
    if suffix in {".json", ".jsonc", ".yml", ".yaml"} or name == ".gitignore":
        return "configuration"
    if suffix in {".md", ".txt"} or relative == "LICENSE":
        return "instructional-prose"
    return None


def _prohibited_payload_format(payload: bytes) -> str | None:
    signatures = (
        (b"%PDF-", "PDF"),
        (b"PK\x03\x04", "ZIP"),
        (b"PK\x05\x06", "ZIP"),
        (b"PK\x07\x08", "ZIP"),
        (b"\x1f\x8b", "gzip"),
        (b"BZh", "bzip2"),
        (b"\xfd7zXZ\x00", "xz"),
        (b"7z\xbc\xaf\x27\x1c", "7z"),
        (b"Rar!\x1a\x07", "RAR"),
    )
    for signature, label in signatures:
        if payload.startswith(signature):
            return label
    if len(payload) >= 262 and payload[257:262] == b"ustar":
        return "tar"
    return None


def _validate_public_file(
    repo_root: Path,
    relative: str,
    classification: str,
    errors: list[str],
) -> None:
    path = repo_root / PurePosixPath(relative)
    if not _regular_file(path, f"public manifest file {relative}", errors, repo_root):
        return
    normalized_parts = tuple(
        unicodedata.normalize("NFKC", part).casefold()
        for part in PurePosixPath(relative).parts
    )
    if any(re.fullmatch(r"chapter [1-7]", part) for part in normalized_parts):
        errors.append(f"public file uses a prohibited Chapter directory: {relative}")
    if any(part in {"statement", "statements"} for part in normalized_parts):
        errors.append(f"public file uses a prohibited statement directory: {relative}")
    if ".gitmodules" in normalized_parts:
        errors.append(f"public file uses prohibited submodule metadata: {relative}")
    normalized_suffix = unicodedata.normalize(
        "NFKC", PurePosixPath(relative).suffix
    ).casefold()
    if normalized_suffix in DENIED_EXTENSIONS:
        errors.append(f"public file has a prohibited extension: {relative}")
    joined = "/".join(normalized_parts)
    if joined.endswith("ch05-prolog/support/plan.pl") or joined.endswith(
        "ch05-prolog/support/dynamic_rel.pl"
    ):
        errors.append(f"public file uses a prohibited support-code path: {relative}")
    try:
        payload = path.read_bytes()
    except OSError as exc:
        errors.append(f"cannot read public file {relative}: {exc}")
        return
    if len(payload) > 2_000_000:
        errors.append(f"public file exceeds the 2 MB source limit: {relative}")
    prohibited_format = _prohibited_payload_format(payload)
    if prohibited_format is not None:
        errors.append(
            f"public file contains prohibited {prohibited_format} payload: {relative}"
        )
    digest = hashlib.sha256(payload).hexdigest()
    if digest in DENIED_CONTENT_SHA256:
        errors.append(f"public file matches excluded support code: {relative}")
    if payload.startswith(b"version https://git-lfs.github.com/spec/v1\n"):
        errors.append(f"public file is a Git LFS pointer: {relative}")
    for pattern in SECRET_PATTERNS:
        if pattern.search(payload):
            errors.append(f"public file contains a high-confidence secret pattern: {relative}")
            break
    if classification in {
        "code",
        "configuration",
        "instructional-prose",
        "cc-license-notice",
        "mit-license-text",
    }:
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError:
            errors.append(f"public text file is not UTF-8: {relative}")
            return
        private_name = "VNU-HUS-IntroAI-Exercises-" + "Internal"
        if private_name.casefold() in text.casefold():
            errors.append(f"public file names the private source repository: {relative}")
        if normalized_suffix == ".pl":
            fingerprint, token_count = _simhash(text)
            if token_count >= 50 and any(
                (fingerprint ^ denied).bit_count() <= 8
                for denied in DENIED_PROLOG_SIMHASHES
            ):
                errors.append(
                    f"public Prolog file is too similar to excluded support code: {relative}"
                )


def _validate_public_manifest(
    repo_root: Path,
    catalog: dict[str, Any],
    errors: list[str],
) -> int:
    try:
        manifest_rel = _safe_relative_path(
            catalog.get("public_content_manifest"),
            "catalog public_content_manifest",
        )
    except TemplateError as exc:
        errors.append(str(exc))
        return 0
    manifest_path = repo_root / manifest_rel
    if not _regular_file(
        manifest_path,
        "public content manifest",
        errors,
        repo_root,
    ):
        return 0
    try:
        manifest = _load_json(manifest_path)
    except TemplateError as exc:
        errors.append(str(exc))
        return 0
    if not _expect_exact_keys(
        manifest,
        {
            "schema_version",
            "repository_role",
            "source_repository",
            "source_repository_id",
            "licenses",
            "files",
        },
        set(),
        "public content manifest",
        errors,
    ):
        return 0
    if manifest["schema_version"] != 1:
        errors.append("public content manifest schema_version must be 1")
    if manifest["repository_role"] != "public-reusable-source":
        errors.append("public content manifest repository_role is invalid")
    if manifest["source_repository"] != catalog.get("source_repository"):
        errors.append("public content manifest source_repository differs from catalog")
    if manifest["source_repository_id"] != catalog.get("source_repository_id"):
        errors.append("public content manifest source_repository_id differs from catalog")
    if manifest["licenses"] != {"MIT": "LICENSES/MIT.txt", "CC-BY-4.0": "LICENSES/CC-BY-4.0.md"}:
        errors.append("public content manifest licenses mapping is invalid")
    entries = manifest["files"]
    if not isinstance(entries, list):
        errors.append("public content manifest files must be a list")
        return 0
    declared: list[str] = []
    normalized_seen: set[str] = set()
    for index, entry in enumerate(entries):
        context = f"public content manifest files[{index}]"
        if not _expect_exact_keys(
            entry,
            {"path", "classification", "license", "origin"},
            set(),
            context,
            errors,
        ):
            continue
        try:
            relative = _safe_relative_path(entry["path"], f"{context}.path")
        except TemplateError as exc:
            errors.append(str(exc))
            continue
        relative_text = str(relative)
        declared.append(relative_text)
        normalized = unicodedata.normalize("NFKC", relative_text).casefold()
        if normalized in normalized_seen:
            errors.append(
                f"public content manifest has a normalized duplicate path: {relative_text}"
            )
        normalized_seen.add(normalized)
        classification = entry["classification"]
        license_id = entry["license"]
        origin = entry["origin"]
        if classification not in LICENSE_BY_CLASSIFICATION:
            errors.append(f"{context}.classification is invalid")
        elif license_id != LICENSE_BY_CLASSIFICATION[classification]:
            errors.append(
                f"{context} license {license_id!r} does not match classification "
                f"{classification!r}"
            )
        expected_classification = _expected_public_classification(relative_text)
        if expected_classification is None:
            errors.append(
                f"{context}.path has no approved file-class rule: {relative_text}"
            )
        elif classification != expected_classification:
            errors.append(
                f"{context}.classification must be {expected_classification!r} "
                f"for {relative_text}"
            )
        if origin not in ALLOWED_ORIGINS:
            errors.append(f"{context}.origin is invalid")
        if classification == "mit-license-text" and relative_text != "LICENSES/MIT.txt":
            errors.append("mit-license-text classification is limited to LICENSES/MIT.txt")
        if classification == "cc-license-notice" and relative_text != "LICENSES/CC-BY-4.0.md":
            errors.append(
                "cc-license-notice classification is limited to LICENSES/CC-BY-4.0.md"
            )
        _validate_public_file(repo_root, relative_text, classification, errors)
    if declared != sorted(declared):
        errors.append("public content manifest files must be sorted by path")
    if len(declared) != len(set(declared)):
        errors.append("public content manifest contains duplicate paths")
    actual = _tree_files(repo_root)
    if actual != set(declared):
        unexpected = sorted(actual - set(declared))
        absent = sorted(set(declared) - actual)
        if unexpected:
            errors.append(
                "public source has unclassified files: " + ", ".join(unexpected)
            )
        if absent:
            errors.append(
                "public manifest names absent files: " + ", ".join(absent)
            )
    return len(declared)


def validate_repository(repo_root: Path) -> dict[str, int]:
    """Validate the public catalog, packages, licenses, and content boundary."""

    repo_root = repo_root.resolve()
    catalog = load_catalog(repo_root)
    errors: list[str] = []

    top_keys = {
        "schema_version",
        "repository_role",
        "source_repository",
        "source_repository_id",
        "source_default_branch",
        "public_content_manifest",
        "license_policy",
        "bibliography",
        "environment",
        "shared_guide",
        "shared_files",
        "assignments",
    }
    _expect_exact_keys(catalog, top_keys, set(), "catalog", errors)
    if catalog.get("schema_version") != 2:
        errors.append("catalog schema_version must be 2")
    if catalog.get("repository_role") != "public-reusable-source":
        errors.append("catalog repository_role must be public-reusable-source")
    if catalog.get("source_repository") != EXPECTED_SOURCE_REPOSITORY:
        errors.append(
            f"catalog source_repository must be {EXPECTED_SOURCE_REPOSITORY}"
        )
    source_repository_id = catalog.get("source_repository_id")
    if (
        type(source_repository_id) is not int
        or source_repository_id != EXPECTED_SOURCE_REPOSITORY_ID
    ):
        errors.append(
            "catalog source_repository_id must be immutable GitHub repository ID "
            f"{EXPECTED_SOURCE_REPOSITORY_ID}"
        )
    if catalog.get("source_default_branch") != "main":
        errors.append("catalog source_default_branch must be main")
    if catalog.get("license_policy") != EXPECTED_LICENSE_POLICY:
        errors.append("catalog license_policy does not match the public license boundary")

    bibliography = catalog.get("bibliography")
    expected_bibliography = [
        {
            "id": "ertel-introai-3e-2025",
            "type": "book",
            "author": "Wolfgang Ertel",
            "title": "Introduction to Artificial Intelligence",
            "edition": 3,
            "year": 2025,
            "publisher": "Springer",
            "doi": "10.1007/978-3-658-43102-0",
            "url": "https://doi.org/10.1007/978-3-658-43102-0",
        }
    ]
    if bibliography != expected_bibliography:
        errors.append(
            "catalog bibliography must contain only the approved structured book record"
        )

    environment = catalog.get("environment")
    environment_valid = _expect_exact_keys(
        environment,
        {"student_cli_version", "devcontainer_image"},
        set(),
        "catalog environment",
        errors,
    )
    if environment_valid:
        cli_version = environment["student_cli_version"]
        image = environment["devcontainer_image"]
        if (
            not isinstance(cli_version, str)
            or re.fullmatch(r"v\d+\.\d+\.\d+", cli_version) is None
        ):
            errors.append(
                "environment student_cli_version must be a pinned vMAJOR.MINOR.PATCH"
            )
        if (
            not isinstance(image, str)
            or re.fullmatch(
                r"ghcr\.io/[a-z0-9_.-]+/[a-z0-9_.-]+@sha256:[0-9a-f]{64}",
                image,
            )
            is None
        ):
            errors.append(
                "environment devcontainer_image must be an immutable GHCR digest"
            )
        devcontainer = repo_root / ".devcontainer/devcontainer.json"
        if _regular_file(
            devcontainer,
            "shared devcontainer definition",
            errors,
            repo_root,
        ):
            try:
                devcontainer_data = _load_jsonc(
                    devcontainer.read_text(encoding="utf-8"),
                    "shared devcontainer definition",
                )
            except (OSError, UnicodeError, TemplateError) as exc:
                errors.append(f"cannot read shared devcontainer definition: {exc}")
            else:
                if not isinstance(devcontainer_data, dict):
                    errors.append(
                        "shared devcontainer definition must contain an object"
                    )
                else:
                    if devcontainer_data.get("image") != image:
                        errors.append(
                            "devcontainer image does not match the catalog digest"
                        )
                    expected_install = (
                        "gh extension install foundation50/gh-student "
                        f"--pin {cli_version} --force"
                    )
                    if devcontainer_data.get("postCreateCommand") != expected_install:
                        errors.append(
                            "devcontainer postCreateCommand does not match "
                            "the catalog student CLI pin"
                        )

    try:
        guide_rel = _safe_relative_path(
            catalog.get("shared_guide"),
            "catalog shared_guide",
        )
    except TemplateError as exc:
        errors.append(str(exc))
        guide_rel = None
    guide_bytes: bytes | None = None
    if guide_rel is not None:
        guide = repo_root / guide_rel
        if _regular_file(guide, "shared Classroom50 guide", errors, repo_root):
            guide_bytes = guide.read_bytes()

    shared_files = catalog.get("shared_files")
    shared_pairs: list[tuple[str, str]] = []
    if not isinstance(shared_files, list):
        errors.append("catalog shared_files must be a list")
    else:
        for index, item in enumerate(shared_files):
            context = f"shared_files[{index}]"
            if not _expect_exact_keys(
                item,
                {"source", "target"},
                set(),
                context,
                errors,
            ):
                continue
            try:
                source = _safe_relative_path(
                    item["source"],
                    f"{context}.source",
                )
                target = _safe_relative_path(
                    item["target"],
                    f"{context}.target",
                )
            except TemplateError as exc:
                errors.append(str(exc))
                continue
            shared_pairs.append((str(source), str(target)))
            _regular_file(
                repo_root / source,
                f"{context} source",
                errors,
                repo_root,
            )
        if shared_pairs != sorted(shared_pairs, key=lambda pair: pair[1]):
            errors.append("shared_files must be sorted by target path")
        if len({target for _, target in shared_pairs}) != len(shared_pairs):
            errors.append("shared_files target paths must be unique")
        if set(shared_pairs) != EXPECTED_SHARED_FILES:
            errors.append("shared_files does not match the pinned public export set")

    assignments = catalog.get("assignments")
    if not isinstance(assignments, list):
        errors.append("catalog assignments must be a list")
        assignments = []
    slugs = [
        item.get("slug")
        for item in assignments
        if isinstance(item, dict)
    ]
    if tuple(slugs) != EXPECTED_SLUGS:
        errors.append("catalog must list the nine expected assignments in course order")
    if all(isinstance(slug, str) for slug in slugs) and len(set(slugs)) != len(slugs):
        errors.append("assignment slugs must be unique")

    ready_count = 0
    blocked_count = 0
    reference_count = 0
    for index, assignment in enumerate(assignments):
        context = f"assignments[{index}]"
        if not isinstance(assignment, dict):
            errors.append(f"{context} must be an object")
            continue
        status = assignment.get("status")
        optional_keys = {"blocked_reason"} if status == "blocked" else set()
        if not _expect_exact_keys(
            assignment,
            EXPECTED_ASSIGNMENT_KEYS,
            optional_keys,
            context,
            errors,
        ):
            continue
        slug = assignment["slug"]
        if (
            not isinstance(slug, str)
            or re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug) is None
        ):
            errors.append(f"{context}.slug is invalid")
            continue
        if not isinstance(assignment["title"], str) or not assignment["title"].strip():
            errors.append(f"{slug} title must be nonempty")
        if status == "ready":
            ready_count += 1
        elif status == "blocked":
            blocked_count += 1
            if (
                not isinstance(assignment.get("blocked_reason"), str)
                or not assignment["blocked_reason"].strip()
            ):
                errors.append(f"{slug} blocked assignment must give a reason")
        else:
            errors.append(f"{slug} status must be ready or blocked")
        if slug == "ch07-uncertainty" and status != "blocked":
            errors.append("ch07-uncertainty must remain blocked")
        if slug != "ch07-uncertainty" and status != "ready":
            errors.append(f"{slug} must be marked ready")

        expected_package = f"Classroom50/{slug}"
        if assignment["package"] != expected_package:
            errors.append(f"{slug} package must be {expected_package}")
        try:
            package_rel = _safe_relative_path(
                assignment["package"],
                f"{slug} package",
            )
        except TemplateError as exc:
            errors.append(str(exc))
            continue
        package_dir = repo_root / package_rel
        if (
            not package_dir.is_dir()
            or _first_symlink_component(package_dir, repo_root) is not None
        ):
            errors.append(
                f"{slug} package directory is missing or unsafe: {package_dir}"
            )
            continue

        settings = assignment["classroom50"]
        settings_optional = (
            {"max_group_size"}
            if isinstance(settings, dict) and settings.get("mode") == "group"
            else set()
        )
        if _expect_exact_keys(
            settings,
            {"mode", "submission_mode", "feedback_pr", "pass_threshold"},
            settings_optional,
            f"{slug} classroom50 settings",
            errors,
        ):
            expected_mode = (
                "group" if slug == "w00-group-collaboration" else "individual"
            )
            if settings["mode"] != expected_mode:
                errors.append(f"{slug} mode must be {expected_mode}")
            if settings["mode"] == "group" and settings.get("max_group_size") != 5:
                errors.append(f"{slug} group mode must have max_group_size 5")
            if settings["submission_mode"] != "tag":
                errors.append(f"{slug} submission_mode must be tag")
            if settings["feedback_pr"] is not True:
                errors.append(f"{slug} feedback_pr must be true")
            if settings["pass_threshold"] != 100:
                errors.append(f"{slug} pass_threshold must be 100")

        path_lists: dict[str, list[str]] = {}
        for field in ("student_files", "teacher_files"):
            values = assignment[field]
            if not isinstance(values, list):
                errors.append(f"{slug} {field} must be a list")
                path_lists[field] = []
                continue
            safe_values: list[str] = []
            for file_index, value in enumerate(values):
                try:
                    safe = _safe_relative_path(
                        value,
                        f"{slug} {field}[{file_index}]",
                    )
                except TemplateError as exc:
                    errors.append(str(exc))
                    continue
                safe_values.append(str(safe))
                _regular_file(
                    package_dir / safe,
                    f"{slug} {field} entry",
                    errors,
                    repo_root,
                )
            if safe_values != sorted(safe_values):
                errors.append(f"{slug} {field} must be sorted")
            if len(set(safe_values)) != len(safe_values):
                errors.append(f"{slug} {field} contains duplicate paths")
            path_lists[field] = safe_values

        student_files = path_lists.get("student_files", [])
        teacher_files = path_lists.get("teacher_files", [])
        if set(teacher_files) != {"classroom50-tests.json"}:
            errors.append(
                f"{slug} teacher_files must contain only classroom50-tests.json"
            )
        if set(student_files) & set(teacher_files):
            errors.append(f"{slug} student_files and teacher_files overlap")
        required_public = {
            "README.md",
            "check_submission.py",
            "docs/CLASSROOM50-WEB-UI.md",
        }
        if not required_public.issubset(student_files):
            errors.append(f"{slug} student_files omits a required public starter file")
        forbidden_export = {
            "classroom50-tests.json",
            ".github/workflows/autograde.yaml",
            ".classroom50.yaml",
        }
        leaked = forbidden_export & set(student_files)
        if leaked:
            errors.append(
                f"{slug} student_files leaks teacher/platform files: {sorted(leaked)}"
            )

        actual_package_files = _tree_files(package_dir)
        classified_files = set(student_files) | set(teacher_files)
        if actual_package_files != classified_files:
            unclassified = sorted(actual_package_files - classified_files)
            absent = sorted(classified_files - actual_package_files)
            if unclassified:
                errors.append(
                    f"{slug} package has unclassified files: "
                    + ", ".join(unclassified)
                )
            if absent:
                errors.append(
                    f"{slug} catalog names absent files: " + ", ".join(absent)
                )

        readme = package_dir / "README.md"
        if readme.is_file() and _first_symlink_component(readme, repo_root) is None:
            try:
                readme_text = readme.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                errors.append(f"{slug} README cannot be read as UTF-8: {exc}")
            else:
                if PROVENANCE_BEGIN in readme_text or PROVENANCE_END in readme_text:
                    errors.append(
                        f"{slug} source README already contains generated provenance"
                    )

        guide_copy = package_dir / "docs/CLASSROOM50-WEB-UI.md"
        if (
            guide_bytes is not None
            and guide_copy.is_file()
            and _first_symlink_component(guide_copy, repo_root) is None
            and guide_copy.read_bytes() != guide_bytes
        ):
            errors.append(f"{slug} guide copy differs from Classroom50/shared")

        references = assignment["references"]
        actual_exercises: list[str] = []
        if not isinstance(references, list):
            errors.append(f"{slug} references must be a list")
            references = []
        for reference_index, reference in enumerate(references):
            reference_context = f"{slug} references[{reference_index}]"
            if not _expect_exact_keys(
                reference,
                {"work", "exercise"},
                {"pages", "note"},
                reference_context,
                errors,
            ):
                continue
            if reference["work"] != "ertel-introai-3e-2025":
                errors.append(f"{reference_context}.work is not approved")
            exercise = reference["exercise"]
            if (
                not isinstance(exercise, str)
                or re.fullmatch(r"[1-9]\d*\.[1-9]\d*", exercise) is None
            ):
                errors.append(f"{reference_context}.exercise is invalid")
            else:
                actual_exercises.append(exercise)
            if "pages" in reference:
                pages = reference["pages"]
                if (
                    not isinstance(pages, list)
                    or not pages
                    or any(
                        not isinstance(page, int)
                        or isinstance(page, bool)
                        or page <= 0
                        for page in pages
                    )
                ):
                    errors.append(f"{reference_context}.pages is invalid")
            if "note" in reference and (
                not isinstance(reference["note"], str)
                or not reference["note"].strip()
                or len(reference["note"]) > 160
            ):
                errors.append(f"{reference_context}.note is invalid")
        if tuple(actual_exercises) != EXPECTED_REFERENCES.get(slug):
            errors.append(f"{slug} bibliographic exercise references are incorrect")
        reference_count += len(references)

        _validate_test_contract(repo_root, package_dir, slug, errors)

    _validate_git_index(repo_root, errors)
    _validate_workflows(repo_root, errors)
    public_file_count = _validate_public_manifest(repo_root, catalog, errors)
    if ready_count != 8 or blocked_count != 1:
        errors.append(
            "catalog readiness must be exactly eight ready and one blocked assignment"
        )
    if reference_count != 12:
        errors.append(
            f"catalog must declare 12 bibliographic references, found {reference_count}"
        )
    if errors:
        raise TemplateError("public source validation failed:\n- " + "\n- ".join(errors))
    return {
        "assignments": len(assignments),
        "ready": ready_count,
        "blocked": blocked_count,
        "references": reference_count,
        "public_files": public_file_count,
    }


def _git(repo_root: Path, args: list[str]) -> subprocess.CompletedProcess[bytes]:
    try:
        result = subprocess.run(
            ["git", "--no-replace-objects", *args],
            cwd=repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as exc:
        raise TemplateError(f"cannot run git: {exc}") from exc
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise TemplateError(
            f"git {' '.join(args)} failed: {detail or 'unknown error'}"
        )
    return result


def _github_repository_id(source_repository: str) -> int:
    try:
        result = subprocess.run(
            [
                "gh",
                "api",
                "--method",
                "GET",
                "--hostname",
                "github.com",
                f"repos/{source_repository}",
                "--jq",
                ".id",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            text=True,
        )
    except OSError as exc:
        raise TemplateError(f"cannot run gh to verify repository identity: {exc}") from exc
    if result.returncode != 0:
        detail = result.stderr.strip()
        raise TemplateError(
            "cannot resolve the canonical GitHub repository ID: "
            + (detail or "unknown gh error")
        )
    try:
        repository_id = int(result.stdout.strip())
    except ValueError as exc:
        raise TemplateError("gh returned an invalid GitHub repository ID") from exc
    if repository_id <= 0:
        raise TemplateError("gh returned a nonpositive GitHub repository ID")
    return repository_id


def _github_branch_commit(source_repository: str, branch: str) -> str:
    try:
        result = subprocess.run(
            [
                "gh",
                "api",
                "--method",
                "GET",
                "--hostname",
                "github.com",
                f"repos/{source_repository}/git/ref/heads/{branch}",
                "--jq",
                ".object.sha",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            text=True,
        )
    except OSError as exc:
        raise TemplateError(f"cannot run gh to verify live branch identity: {exc}") from exc
    if result.returncode != 0:
        detail = result.stderr.strip()
        raise TemplateError(
            "cannot resolve the live canonical GitHub branch: "
            + (detail or "unknown gh error")
        )
    commit = result.stdout.strip()
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise TemplateError("gh returned an invalid live GitHub branch commit")
    return commit


def _normalize_github_repository(remote_url: str) -> str | None:
    prefixes = (
        "git@github.com:",
        "ssh://git@github.com/",
        "https://github.com/",
    )
    repository: str | None = None
    for prefix in prefixes:
        if remote_url.casefold().startswith(prefix.casefold()):
            repository = remote_url[len(prefix) :].rstrip("/")
            break
    if repository is None:
        return None
    if repository.endswith(".git"):
        repository = repository[:-4]
    parts = repository.split("/")
    if (
        len(parts) != 2
        or any(not part for part in parts)
        or any(
            character.isspace()
            or unicodedata.category(character) in {"Cc", "Cf"}
            for character in repository
        )
    ):
        return None
    return repository


def _git_blob(repo_root: Path, commit: str, relative: str) -> bytes:
    return _git(repo_root, ["show", f"{commit}:{relative}"]).stdout


def _git_file_mode(repo_root: Path, commit: str, relative: str) -> int:
    output = _git(repo_root, ["ls-tree", "-z", commit, "--", relative]).stdout
    entries = [entry for entry in output.split(b"\0") if entry]
    if len(entries) != 1 or b"\t" not in entries[0]:
        raise TemplateError(f"cannot resolve one Git tree entry for {relative}")
    header, recorded_path = entries[0].split(b"\t", 1)
    fields = header.split()
    if len(fields) != 3 or fields[1] != b"blob":
        raise TemplateError(f"Git tree entry is not a file blob: {relative}")
    try:
        decoded_path = recorded_path.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TemplateError(f"Git returned a non-UTF-8 path for {relative}") from exc
    if decoded_path != relative:
        raise TemplateError(f"Git resolved an unexpected tree path for {relative}")
    if fields[0] == b"100644":
        return 0o644
    if fields[0] == b"100755":
        return 0o755
    raise TemplateError(f"Git tree entry is not a regular file: {relative}")


def _verified_source_commit(
    repo_root: Path,
    relevant_paths: Iterable[str],
    source_repository: str,
    source_repository_id: int,
    source_default_branch: str,
) -> tuple[str, str]:
    reported_root = Path(
        _git(repo_root, ["rev-parse", "--show-toplevel"])
        .stdout.decode("utf-8")
        .strip()
    ).resolve()
    if reported_root != repo_root.resolve():
        raise TemplateError(
            f"repo root {repo_root} is inside another Git worktree: {reported_root}"
        )
    try:
        origin_url = (
            _git(repo_root, ["config", "--get", "remote.origin.url"])
            .stdout.decode("utf-8")
            .strip()
        )
    except (TemplateError, UnicodeDecodeError) as exc:
        raise TemplateError("export requires a readable canonical origin remote") from exc
    normalized_origin = _normalize_github_repository(origin_url)
    if (
        normalized_origin is None
        or normalized_origin.casefold() != source_repository.casefold()
    ):
        raise TemplateError(
            f"origin must identify canonical GitHub repository {source_repository}; "
            f"found {origin_url!r}"
        )
    live_repository_id = _github_repository_id(source_repository)
    if live_repository_id != source_repository_id:
        raise TemplateError(
            f"canonical GitHub repository ID must be {source_repository_id}; "
            f"resolved {live_repository_id}"
        )
    live_commit = _github_branch_commit(source_repository, source_default_branch)
    branch = (
        _git(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"])
        .stdout.decode("utf-8", errors="replace")
        .strip()
    )
    if branch != source_default_branch:
        raise TemplateError(
            f"export requires checked-out branch {source_default_branch}; found {branch}"
        )
    commit = (
        _git(repo_root, ["rev-parse", "HEAD^{commit}"])
        .stdout.decode("ascii")
        .strip()
    )
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise TemplateError(f"git returned an invalid source commit: {commit!r}")
    tree = (
        _git(repo_root, ["rev-parse", f"{commit}^{{tree}}"])
        .stdout.decode("ascii")
        .strip()
    )
    if re.fullmatch(r"[0-9a-f]{40}", tree) is None:
        raise TemplateError(f"git returned an invalid source tree: {tree!r}")
    remote_ref = f"refs/remotes/origin/{source_default_branch}"
    try:
        remote_commit = (
            _git(repo_root, ["rev-parse", f"{remote_ref}^{{commit}}"])
            .stdout.decode("ascii")
            .strip()
        )
    except (TemplateError, UnicodeDecodeError) as exc:
        raise TemplateError(
            f"export requires the locally available canonical ref {remote_ref}; "
            "fetch origin before exporting"
        ) from exc
    if commit != remote_commit:
        raise TemplateError(
            f"HEAD {commit} must equal canonical {remote_ref} {remote_commit}; "
            "publish or check out the canonical default-branch commit first"
        )
    if commit != live_commit:
        raise TemplateError(
            f"HEAD {commit} must equal live GitHub "
            f"{source_repository}@{source_default_branch} {live_commit}; "
            "publish or check out the live canonical default-branch commit first"
        )
    paths = sorted(set(relevant_paths))
    tracked_output = _git(repo_root, ["ls-files", "-z", "--", *paths]).stdout
    tracked = {
        entry.decode("utf-8")
        for entry in tracked_output.split(b"\0")
        if entry
    }
    untracked = sorted(set(paths) - tracked)
    if untracked:
        raise TemplateError(
            "export inputs are not committed to Git: " + ", ".join(untracked)
        )
    status = (
        _git(
            repo_root,
            ["status", "--porcelain=v1", "--untracked-files=all", "--", *paths],
        )
        .stdout.decode("utf-8", errors="replace")
    )
    if status.strip():
        raise TemplateError(
            "export inputs have uncommitted changes:\n" + status.rstrip()
        )
    for relative in paths:
        source = repo_root / PurePosixPath(relative)
        try:
            working_bytes = source.read_bytes()
        except OSError as exc:
            raise TemplateError(f"cannot read export input {relative}: {exc}") from exc
        if working_bytes != _git_blob(repo_root, commit, relative):
            raise TemplateError(
                f"export input differs from HEAD despite Git status: {relative}"
            )
        git_mode = _git_file_mode(repo_root, commit, relative)
        if source.stat().st_mode & 0o111 != git_mode & 0o111:
            raise TemplateError(
                f"export input mode differs from HEAD despite Git status: {relative}"
            )
    return commit, tree


def _assignment(catalog: dict[str, Any], slug: str) -> dict[str, Any]:
    for assignment in catalog["assignments"]:
        if assignment["slug"] == slug:
            return assignment
    raise TemplateError(f"unknown assignment slug: {slug}")


def _validated_state_paths(repo_root: Path, catalog: dict[str, Any]) -> set[str]:
    manifest_path = repo_root / catalog["public_content_manifest"]
    manifest = _load_json(manifest_path)
    return {entry["path"] for entry in manifest["files"]}


def _provenance_block(
    source_repository: str,
    source_repository_id: int,
    commit: str,
    tree: str,
    source_slug: str,
) -> str:
    return (
        f"{PROVENANCE_BEGIN}\n"
        "## Source provenance\n\n"
        f"- Source repository: `{source_repository}`\n"
        f"- Source repository ID: `{source_repository_id}`\n"
        f"- Source commit: `{commit}`\n"
        f"- Source tree: `{tree}`\n"
        f"- Source slug: `{source_slug}`\n"
        "- Complete file inventory: [`SOURCE-INVENTORY.md`](SOURCE-INVENTORY.md)\n"
        f"{PROVENANCE_END}\n"
    )


def _append_provenance(readme: bytes, block: str) -> bytes:
    try:
        text = readme.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TemplateError(f"source README is not valid UTF-8: {exc}") from exc
    if PROVENANCE_BEGIN in text or PROVENANCE_END in text:
        raise TemplateError("source README already contains generated provenance")
    separator = "\n" if text.endswith("\n") else "\n\n"
    return (text + separator + block).encode("utf-8")


def _inventory(
    source_repository: str,
    source_repository_id: int,
    commit: str,
    tree: str,
    source_slug: str,
    exported_files: Iterable[str],
) -> bytes:
    lines = "\n".join(sorted(exported_files))
    return (
        "# Source inventory\n\n"
        f"- Source repository: `{source_repository}`\n"
        f"- Source repository ID: `{source_repository_id}`\n"
        f"- Source commit: `{commit}`\n"
        f"- Source tree: `{tree}`\n"
        f"- Source slug: `{source_slug}`\n\n"
        "```text\n"
        f"{lines}\n"
        "```\n"
    ).encode("utf-8")


def _write_git_file(
    repo_root: Path,
    commit: str,
    source: PurePosixPath,
    target: Path,
) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    relative = str(source)
    target.write_bytes(_git_blob(repo_root, commit, relative))
    os.chmod(target, _git_file_mode(repo_root, commit, relative))


def export_assignment(
    repo_root: Path,
    slug: str,
    destination: Path,
) -> dict[str, Any]:
    """Export one ready public scaffold to a new standalone directory."""

    repo_root = repo_root.resolve()
    summary = validate_repository(repo_root)
    catalog = load_catalog(repo_root)
    assignment = _assignment(catalog, slug)
    if assignment["status"] != "ready":
        raise TemplateError(f"{slug} is blocked: {assignment['blocked_reason']}")

    package_rel = PurePosixPath(assignment["package"])
    source_slug = str(package_rel)
    copy_plan: list[tuple[PurePosixPath, PurePosixPath]] = []
    for relative in assignment["student_files"]:
        target = PurePosixPath(relative)
        copy_plan.append((package_rel / target, target))
    for shared in catalog["shared_files"]:
        copy_plan.append(
            (PurePosixPath(shared["source"]), PurePosixPath(shared["target"]))
        )
    targets = [str(target) for _, target in copy_plan]
    if len(set(targets)) != len(targets):
        raise TemplateError(f"{slug} export has colliding target paths")
    forbidden = {
        "classroom50-tests.json",
        ".github/workflows/autograde.yaml",
        ".classroom50.yaml",
        "PUBLIC-CONTENT.json",
    }
    if forbidden & set(targets):
        raise TemplateError(f"{slug} export plan contains a source or platform file")

    relevant = _validated_state_paths(repo_root, catalog)
    commit, tree = _verified_source_commit(
        repo_root,
        relevant,
        catalog["source_repository"],
        catalog["source_repository_id"],
        catalog["source_default_branch"],
    )

    lexical_destination = Path(os.path.abspath(destination.expanduser()))
    destination_symlink = _first_symlink_component(lexical_destination)
    if destination_symlink is not None:
        raise TemplateError(
            f"export destination has a symbolic-link path component: {destination_symlink}"
        )
    destination = lexical_destination.resolve(strict=False)
    try:
        destination.relative_to(repo_root)
    except ValueError:
        pass
    else:
        raise TemplateError(
            "export destination must be outside the canonical source repository"
        )
    if destination.exists():
        raise TemplateError(f"export destination already exists: {destination}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(
            prefix=f".{destination.name}.export-",
            dir=destination.parent,
        )
    )
    try:
        for source, target in copy_plan:
            _write_git_file(repo_root, commit, source, temporary / target)

        readme = temporary / "README.md"
        readme.write_bytes(
            _append_provenance(
                readme.read_bytes(),
                _provenance_block(
                    catalog["source_repository"],
                    catalog["source_repository_id"],
                    commit,
                    tree,
                    source_slug,
                ),
            )
        )
        exported_files = sorted({*targets, "SOURCE-INVENTORY.md"})
        (temporary / "SOURCE-INVENTORY.md").write_bytes(
            _inventory(
                catalog["source_repository"],
                catalog["source_repository_id"],
                commit,
                tree,
                source_slug,
                exported_files,
            )
        )
        actual_files = _tree_files(temporary)
        if actual_files != set(exported_files):
            raise TemplateError(
                "internal error: exported tree differs from its inventory"
            )
        temporary.replace(destination)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise

    return {
        **summary,
        "slug": slug,
        "source_repository_id": catalog["source_repository_id"],
        "source_commit": commit,
        "source_tree": tree,
        "destination": str(destination),
        "files": len(exported_files),
    }


def _default_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate and export public VNU-HUS IntroAI Classroom50 scaffolds."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=_default_repo_root(),
        help="public source repository root (defaults to this checkout)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "validate",
        help="validate the catalog, packages, and public-content boundary",
    )
    export_parser = subparsers.add_parser(
        "export",
        help="export one ready package to a clean standalone directory",
    )
    export_parser.add_argument("slug", choices=EXPECTED_SLUGS)
    export_parser.add_argument("destination", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "validate":
            summary = validate_repository(args.repo_root)
            print(
                "OK: validated "
                f"{summary['assignments']} assignments "
                f"({summary['ready']} ready, {summary['blocked']} blocked), "
                f"{summary['references']} bibliographic references, and "
                f"{summary['public_files']} classified public files"
            )
        else:
            result = export_assignment(
                args.repo_root,
                args.slug,
                args.destination,
            )
            print(
                f"OK: exported {result['slug']} from repository "
                f"{result['source_repository_id']} at {result['source_commit']} "
                f"(tree {result['source_tree']}) to {result['destination']} "
                f"({result['files']} files)"
            )
    except TemplateError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
