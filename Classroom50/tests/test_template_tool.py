from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


sys.dont_write_bytecode = True
REPO_ROOT = Path(__file__).resolve().parents[2]
TOOL_PATH = REPO_ROOT / "Classroom50/tools/template_tool.py"
SPEC = importlib.util.spec_from_file_location("classroom50_public_template_tool", TOOL_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import {TOOL_PATH}")
template_tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(template_tool)


def _git_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_AUTHOR_NAME": "Template Test",
            "GIT_AUTHOR_EMAIL": "template-test@example.invalid",
            "GIT_COMMITTER_NAME": "Template Test",
            "GIT_COMMITTER_EMAIL": "template-test@example.invalid",
            "GIT_AUTHOR_DATE": "2000-01-01T00:00:00+0000",
            "GIT_COMMITTER_DATE": "2000-01-01T00:00:00+0000",
        }
    )
    return environment


def _run_git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        env=_git_environment(),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _git_output(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        env=_git_environment(),
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()


def _fixture_repo(parent: Path) -> Path:
    repo = parent / "source"
    shutil.copytree(
        REPO_ROOT,
        repo,
        ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
    )
    _run_git(repo, "init", "-q", "-b", "main")
    _run_git(repo, "add", ".")
    _run_git(repo, "commit", "-q", "-m", "fixture")
    _run_git(
        repo,
        "remote",
        "add",
        "origin",
        "git@github.com:hoanganhduc/VNU-HUS-IntroAI-Exercises.git",
    )
    _run_git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    return repo


def _file_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def _manifest(repo: Path) -> dict[str, object]:
    return json.loads((repo / "PUBLIC-CONTENT.json").read_text(encoding="utf-8"))


def _write_manifest(repo: Path, manifest: dict[str, object]) -> None:
    (repo / "PUBLIC-CONTENT.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _add_manifest_file(
    repo: Path,
    relative: str,
    *,
    classification: str = "instructional-prose",
    license_id: str = "CC-BY-4.0",
) -> None:
    manifest = _manifest(repo)
    files = manifest["files"]
    assert isinstance(files, list)
    files.append(
        {
            "path": relative,
            "classification": classification,
            "license": license_id,
            "origin": "course-authored",
        }
    )
    files.sort(key=lambda entry: entry["path"])
    _write_manifest(repo, manifest)


def _mock_live_source(
    repo: Path,
    *,
    repository_id: int | None = None,
    live_commit: str | None = None,
):
    if repository_id is None:
        repository_id = int(
            template_tool.load_catalog(repo)["source_repository_id"]
        )
    if live_commit is None:
        live_commit = _git_output(repo, "rev-parse", "HEAD")
    return mock.patch.multiple(
        template_tool,
        _github_repository_id=mock.Mock(return_value=repository_id),
        _github_branch_commit=mock.Mock(return_value=live_commit),
    )


class CatalogAndBoundaryTests(unittest.TestCase):
    def test_nonisolated_cli_refuses_before_sibling_import_shadow(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            tool = directory / "template_tool.py"
            shutil.copyfile(TOOL_PATH, tool)
            (directory / "hashlib.py").write_text(
                "print('IMPORT_SHADOW_EXECUTED')\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(tool), "validate"],
                cwd=directory,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=10,
                check=False,
            )
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("run this tool in isolated mode", result.stderr)
            self.assertNotIn(
                "IMPORT_SHADOW_EXECUTED",
                result.stdout + result.stderr,
            )

    def test_live_public_source_validates(self) -> None:
        summary = template_tool.validate_repository(REPO_ROOT)
        manifest = _manifest(REPO_ROOT)
        self.assertEqual(summary["assignments"], 9)
        self.assertEqual(summary["ready"], 8)
        self.assertEqual(summary["blocked"], 1)
        self.assertEqual(summary["references"], 12)
        self.assertEqual(summary["public_files"], len(manifest["files"]))
        self.assertEqual(
            template_tool.load_catalog(REPO_ROOT)["source_repository_id"],
            template_tool.EXPECTED_SOURCE_REPOSITORY_ID,
        )

    def test_catalog_has_only_structured_references_not_deployment_targets(self) -> None:
        catalog = template_tool.load_catalog(REPO_ROOT)
        self.assertEqual(catalog["schema_version"], 2)
        self.assertEqual(catalog["repository_role"], "public-reusable-source")
        self.assertEqual(
            tuple(item["slug"] for item in catalog["assignments"]),
            template_tool.EXPECTED_SLUGS,
        )
        for assignment in catalog["assignments"]:
            self.assertNotIn("template", assignment)
            self.assertNotIn("canonical_files", assignment)
            for reference in assignment["references"]:
                self.assertEqual(
                    set(reference) - {"pages", "note"},
                    {"work", "exercise"},
                )
                self.assertNotIn("statement", reference)

    def test_validator_ignores_commented_devcontainer_decoys(self) -> None:
        for property_name, replacement, expected_error in (
            (
                "image",
                "ubuntu:latest",
                "devcontainer image does not match the catalog digest",
            ),
            (
                "postCreateCommand",
                "printf unpinned",
                "devcontainer postCreateCommand does not match",
            ),
        ):
            with self.subTest(property_name=property_name), tempfile.TemporaryDirectory() as temporary:
                repo = _fixture_repo(Path(temporary))
                devcontainer = repo / ".devcontainer/devcontainer.json"
                document = devcontainer.read_text(encoding="utf-8")
                environment = template_tool.load_catalog(repo)["environment"]
                expected = (
                    environment["devcontainer_image"]
                    if property_name == "image"
                    else "gh extension install foundation50/gh-student "
                    f'--pin {environment["student_cli_version"]} --force'
                )
                document = document.replace(
                    f'"{property_name}": {json.dumps(expected)}',
                    f'"{property_name}": {json.dumps(replacement)}',
                    1,
                ).replace(
                    "{\n",
                    f'{{\n\t// "{property_name}": {json.dumps(expected)},\n',
                    1,
                )
                devcontainer.write_text(document, encoding="utf-8")
                with self.assertRaisesRegex(
                    template_tool.TemplateError,
                    expected_error,
                ):
                    template_tool.validate_repository(repo)

    def test_validator_rejects_duplicate_devcontainer_properties(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = _fixture_repo(Path(temporary))
            devcontainer = repo / ".devcontainer/devcontainer.json"
            document = devcontainer.read_text(encoding="utf-8")
            expected = template_tool.load_catalog(repo)["environment"][
                "devcontainer_image"
            ]
            document = document.replace(
                f'"image": {json.dumps(expected)},',
                f'"image": {json.dumps(expected)},\n\t"image": "ubuntu:latest",',
                1,
            )
            devcontainer.write_text(document, encoding="utf-8")
            with self.assertRaisesRegex(
                template_tool.TemplateError,
                "duplicate property.*image",
            ):
                template_tool.validate_repository(repo)

    def test_unsafe_relative_paths_are_rejected(self) -> None:
        for value in (
            "/absolute",
            "../escape",
            "nested/../escape",
            "nested//file",
            "a\\b",
            "bad\npath",
            "bad\x00path",
            "bad\u202epath",
        ):
            with self.subTest(value=value), self.assertRaises(
                template_tool.TemplateError
            ):
                template_tool._safe_relative_path(value, "test path")

    def test_unclassified_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = _fixture_repo(Path(temporary))
            (repo / "unexpected.md").write_text("unexpected\n", encoding="utf-8")
            with self.assertRaisesRegex(
                template_tool.TemplateError,
                "unclassified files.*unexpected.md",
            ):
                template_tool.validate_repository(repo)

    def test_root_dockerfile_requires_configuration_classification(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = _fixture_repo(Path(temporary))
            manifest = _manifest(repo)
            entries = manifest["files"]
            assert isinstance(entries, list)
            dockerfile = next(entry for entry in entries if entry["path"] == "Dockerfile")
            dockerfile["classification"] = "instructional-prose"
            dockerfile["license"] = "CC-BY-4.0"
            _write_manifest(repo, manifest)
            with self.assertRaisesRegex(
                template_tool.TemplateError,
                "classification must be 'configuration'.*Dockerfile",
            ):
                template_tool.validate_repository(repo)

    def test_dockerfile_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = _fixture_repo(Path(temporary))
            dockerfile = repo / "Dockerfile"
            dockerfile.write_text(
                dockerfile.read_text(encoding="utf-8") + "\n# drift\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                template_tool.TemplateError,
                "approved Dockerfile differs from reviewed bytes",
            ):
                template_tool.validate_repository(repo)

    def test_catalog_rejects_a_different_ghcr_package(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = _fixture_repo(Path(temporary))
            catalog_path = repo / "Classroom50/catalog.json"
            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
            old_image = catalog["environment"]["devcontainer_image"]
            new_image = old_image.replace(
                "ghcr.io/hoanganhduc/vnu-hus-introai-exercises",
                "ghcr.io/hoanganhduc/different-image",
            )
            catalog["environment"]["devcontainer_image"] = new_image
            catalog_path.write_text(
                json.dumps(catalog, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            devcontainer = repo / ".devcontainer/devcontainer.json"
            devcontainer.write_text(
                devcontainer.read_text(encoding="utf-8").replace(old_image, new_image),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                template_tool.TemplateError,
                "must pin the approved GHCR repository",
            ):
                template_tool.validate_repository(repo)

    def test_casefolded_and_unicode_chapter_paths_are_rejected(self) -> None:
        for relative in ("CHAPTER 1/notes.md", "Ｃｈａｐｔｅｒ ２/notes.md"):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as temporary:
                repo = _fixture_repo(Path(temporary))
                target = repo / relative
                target.parent.mkdir(parents=True)
                target.write_text("course note\n", encoding="utf-8")
                _add_manifest_file(repo, relative)
                with self.assertRaisesRegex(
                    template_tool.TemplateError,
                    "prohibited Chapter directory",
                ):
                    template_tool.validate_repository(repo)

    def test_statement_directories_and_denied_extensions_are_rejected(self) -> None:
        for relative in (
            "Classroom50/x/Statements/note.md",
            "notes/scan.PDF",
            "notes/scan.ＰＤＦ",
            "notes/source.ＴＥＸ",
        ):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as temporary:
                repo = _fixture_repo(Path(temporary))
                target = repo / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("course note\n", encoding="utf-8")
                _add_manifest_file(repo, relative)
                with self.assertRaisesRegex(
                    template_tool.TemplateError,
                    "prohibited statement directory|prohibited extension",
                ):
                    template_tool.validate_repository(repo)

    def test_gitlinks_and_gitmodules_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = _fixture_repo(Path(temporary))
            commit = _git_output(repo, "rev-parse", "HEAD")
            _run_git(
                repo,
                "update-index",
                "--add",
                "--cacheinfo",
                f"160000,{commit},vendor/submodule",
            )
            with self.assertRaisesRegex(
                template_tool.TemplateError,
                "non-file entry.*160000.*vendor/submodule",
            ):
                template_tool.validate_repository(repo)

        with tempfile.TemporaryDirectory() as temporary:
            repo = _fixture_repo(Path(temporary))
            (repo / ".gitmodules").write_text(
                "[submodule \"vendor\"]\n\tpath = vendor\n\turl = ../vendor\n",
                encoding="utf-8",
            )
            _add_manifest_file(
                repo,
                ".gitmodules",
                classification="configuration",
                license_id="MIT",
            )
            with self.assertRaisesRegex(
                template_tool.TemplateError,
                "prohibited submodule metadata",
            ):
                template_tool.validate_repository(repo)

    def test_lfs_pointer_archive_symlink_and_private_name_are_rejected(self) -> None:
        cases = (
            (
                "pointer.md",
                "version https://git-lfs.github.com/spec/v1\noid sha256:"
                + "0" * 64
                + "\nsize 1\n",
                "Git LFS pointer",
            ),
            ("bundle.zip", "not really an archive\n", "prohibited extension"),
            (
                "private.md",
                "VNU-HUS-IntroAI-Exercises-" + "Internal\n",
                "private source repository",
            ),
        )
        for relative, payload, expected in cases:
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as temporary:
                repo = _fixture_repo(Path(temporary))
                (repo / relative).write_text(payload, encoding="utf-8")
                _add_manifest_file(repo, relative)
                with self.assertRaisesRegex(template_tool.TemplateError, expected):
                    template_tool.validate_repository(repo)

        with tempfile.TemporaryDirectory() as temporary:
            repo = _fixture_repo(Path(temporary))
            relative = "renamed-archive.md"
            (repo / relative).write_bytes(b"PK\x05\x06" + b"\x00" * 18)
            _add_manifest_file(repo, relative)
            with self.assertRaisesRegex(
                template_tool.TemplateError,
                "prohibited ZIP payload",
            ):
                template_tool.validate_repository(repo)

        with tempfile.TemporaryDirectory() as temporary:
            repo = _fixture_repo(Path(temporary))
            (repo / "outside.md").write_text("outside\n", encoding="utf-8")
            (repo / "linked.md").symlink_to("outside.md")
            _add_manifest_file(repo, "outside.md")
            _add_manifest_file(repo, "linked.md")
            with self.assertRaisesRegex(
                template_tool.TemplateError,
                "symbolic-link path component",
            ):
                template_tool.validate_repository(repo)

    def test_hash_and_similarity_denylist_mechanisms_reject_content(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = _fixture_repo(Path(temporary))
            target = repo / "Classroom50/ch05-prolog/copied.pl"
            target.write_text("copied_example.\n", encoding="utf-8")
            _add_manifest_file(
                repo,
                "Classroom50/ch05-prolog/copied.pl",
                classification="code",
                license_id="MIT",
            )
            digest = __import__("hashlib").sha256(target.read_bytes()).hexdigest()
            with mock.patch.object(
                template_tool,
                "DENIED_CONTENT_SHA256",
                {*template_tool.DENIED_CONTENT_SHA256, digest},
            ):
                with self.assertRaisesRegex(
                    template_tool.TemplateError,
                    "matches excluded support code",
                ):
                    template_tool.validate_repository(repo)

        with tempfile.TemporaryDirectory() as temporary:
            repo = _fixture_repo(Path(temporary))
            target = repo / "Classroom50/ch05-prolog/similar.pl"
            target.write_text(
                "\n".join(f"predicate_{index}(value_{index})." for index in range(80))
                + "\n",
                encoding="utf-8",
            )
            _add_manifest_file(
                repo,
                "Classroom50/ch05-prolog/similar.pl",
                classification="code",
                license_id="MIT",
            )
            fingerprint, _ = template_tool._simhash(
                target.read_text(encoding="utf-8")
            )
            with mock.patch.object(
                template_tool,
                "DENIED_PROLOG_SIMHASHES",
                {*template_tool.DENIED_PROLOG_SIMHASHES, fingerprint},
            ):
                with self.assertRaisesRegex(
                    template_tool.TemplateError,
                    "too similar to excluded support code",
                ):
                    template_tool.validate_repository(repo)

    def test_license_misclassification_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = _fixture_repo(Path(temporary))
            manifest = _manifest(repo)
            entry = next(
                item for item in manifest["files"] if item["path"] == "README.md"
            )
            entry["license"] = "MIT"
            _write_manifest(repo, manifest)
            with self.assertRaisesRegex(
                template_tool.TemplateError,
                "does not match classification",
            ):
                template_tool.validate_repository(repo)

        with tempfile.TemporaryDirectory() as temporary:
            repo = _fixture_repo(Path(temporary))
            manifest = _manifest(repo)
            entry = next(
                item for item in manifest["files"] if item["path"] == "README.md"
            )
            entry["classification"] = "code"
            entry["license"] = "MIT"
            _write_manifest(repo, manifest)
            with self.assertRaisesRegex(
                template_tool.TemplateError,
                "classification must be 'instructional-prose'",
            ):
                template_tool.validate_repository(repo)

        with tempfile.TemporaryDirectory() as temporary:
            repo = _fixture_repo(Path(temporary))
            manifest = _manifest(repo)
            entry = next(
                item
                for item in manifest["files"]
                if item["path"] == "Classroom50/tools/template_tool.py"
            )
            entry["classification"] = "instructional-prose"
            entry["license"] = "CC-BY-4.0"
            _write_manifest(repo, manifest)
            with self.assertRaisesRegex(
                template_tool.TemplateError,
                "classification must be 'code'",
            ):
                template_tool.validate_repository(repo)

    def test_bibliography_cannot_carry_statement_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = _fixture_repo(Path(temporary))
            catalog_path = repo / "Classroom50/catalog.json"
            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
            catalog["bibliography"][0]["statement"] = "not permitted"
            catalog_path.write_text(
                json.dumps(catalog, indent=2) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                template_tool.TemplateError,
                "approved structured book record",
            ):
                template_tool.validate_repository(repo)

    def test_shared_guide_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = _fixture_repo(Path(temporary))
            guide = (
                repo
                / "Classroom50/ch04-limitations-of-logic/docs/CLASSROOM50-WEB-UI.md"
            )
            guide.write_text(
                guide.read_text(encoding="utf-8") + "\nDrift.\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                template_tool.TemplateError,
                "guide copy differs",
            ):
                template_tool.validate_repository(repo)

    def test_trusted_runner_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = _fixture_repo(Path(temporary))
            tests_path = (
                repo / "Classroom50/ch01-introduction/classroom50-tests.json"
            )
            tests = json.loads(tests_path.read_text(encoding="utf-8"))
            tests[0]["run"] = tests[0]["run"].replace(
                "actual==expected",
                "actual==actual",
            )
            tests_path.write_text(
                json.dumps(tests, indent=2) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                template_tool.TemplateError,
                "exactly match the trusted",
            ):
                template_tool.validate_repository(repo)

    def test_approved_workflow_drift_is_rejected(self) -> None:
        for relative in template_tool.EXPECTED_WORKFLOW_SHA256:
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as temporary:
                repo = _fixture_repo(Path(temporary))
                workflow = repo / relative
                workflow.write_text(
                    workflow.read_text(encoding="utf-8") + "\n# drift\n",
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(
                    template_tool.TemplateError,
                    "approved workflow differs from reviewed bytes",
                ):
                    template_tool.validate_repository(repo)

    def test_manifest_listed_extra_workflow_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = _fixture_repo(Path(temporary))
            relative = ".github/workflows/extra.yml"
            (repo / relative).write_text("name: Extra\n", encoding="utf-8")
            _add_manifest_file(
                repo,
                relative,
                classification="configuration",
                license_id="MIT",
            )
            with self.assertRaisesRegex(
                template_tool.TemplateError,
                "public source has unapproved workflows.*extra.yml",
            ):
                template_tool.validate_repository(repo)

    def test_image_publisher_is_manual_and_repository_bound(self) -> None:
        workflow = (REPO_ROOT / ".github/workflows/build-docker.yml").read_text(
            encoding="utf-8"
        )
        expected_start = (
            "name: Publish IntroAI development image\n\n"
            "on:\n"
            "  workflow_dispatch:\n"
            "    inputs:\n"
        )
        self.assertTrue(workflow.startswith(expected_start))
        self.assertIn("github.ref == 'refs/heads/main'", workflow)
        self.assertIn(
            "IMAGE: ghcr.io/hoanganhduc/vnu-hus-introai-exercises",
            workflow,
        )
        self.assertIn("contents: read", workflow)
        self.assertIn("packages: write", workflow)
        self.assertIn("--platform linux/amd64", workflow)
        self.assertIn("candidate-${{ github.run_id }}-${{ github.run_attempt }}", workflow)
        self.assertIn("inputs.operation == 'promote'", workflow)
        self.assertIn('test "$latest_digest" = "$PROMOTE_DIGEST"', workflow)
        self.assertEqual(workflow.count("docker build \\"), 1)
        self.assertNotIn(
            "VNU-HUS-IntroAI-Exercises-" + "Internal",
            workflow,
        )


class ExportTests(unittest.TestCase):
    def test_all_ready_assignments_export_exact_allowlists_and_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = _fixture_repo(root)
            catalog = template_tool.load_catalog(repo)
            commit = _git_output(repo, "rev-parse", "HEAD")
            tree = _git_output(repo, "rev-parse", "HEAD^{tree}")
            with _mock_live_source(repo):
                for assignment in catalog["assignments"]:
                    if assignment["status"] != "ready":
                        continue
                    slug = assignment["slug"]
                    with self.subTest(slug=slug):
                        destination = root / f"export-{slug}"
                        result = template_tool.export_assignment(
                            repo,
                            slug,
                            destination,
                        )
                        expected = {
                            *assignment["student_files"],
                            *(
                                item["target"]
                                for item in catalog["shared_files"]
                            ),
                            "SOURCE-INVENTORY.md",
                        }
                        self.assertEqual(set(_file_bytes(destination)), expected)
                        self.assertEqual(result["source_commit"], commit)
                        self.assertEqual(result["source_tree"], tree)
                        self.assertEqual(
                            result["source_repository_id"],
                            catalog["source_repository_id"],
                        )
                        self.assertFalse(
                            (destination / "classroom50-tests.json").exists()
                        )
                        self.assertFalse(
                            (destination / "PUBLIC-CONTENT.json").exists()
                        )
                        self.assertFalse((destination / "Dockerfile").exists())
                        self.assertFalse(
                            (destination / ".github/workflows/build-docker.yml").exists()
                        )
                        readme = (destination / "README.md").read_text(
                            encoding="utf-8"
                        )
                        self.assertIn(
                            f"Source repository ID: `{catalog['source_repository_id']}`",
                            readme,
                        )
                        self.assertIn(f"Source tree: `{tree}`", readme)

    def test_same_commit_exports_deterministically(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = _fixture_repo(root)
            with _mock_live_source(repo):
                first = root / "first"
                second = root / "second"
                template_tool.export_assignment(repo, "ch05-prolog", first)
                template_tool.export_assignment(repo, "ch05-prolog", second)
            self.assertEqual(_file_bytes(first), _file_bytes(second))

    def test_blocked_assignment_cannot_be_exported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = _fixture_repo(root)
            destination = root / "blocked"
            with self.assertRaisesRegex(
                template_tool.TemplateError,
                "ch07-uncertainty is blocked",
            ):
                template_tool.export_assignment(
                    repo,
                    "ch07-uncertainty",
                    destination,
                )
            self.assertFalse(destination.exists())

    def test_export_rejects_wrong_origin_or_repository_id(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = _fixture_repo(root)
            destination = root / "wrong-origin"
            _run_git(
                repo,
                "remote",
                "set-url",
                "origin",
                "https://github.com/example/not-canonical.git",
            )
            with self.assertRaisesRegex(
                template_tool.TemplateError,
                "origin must identify canonical",
            ):
                template_tool.export_assignment(
                    repo,
                    "w00-individual-onboarding",
                    destination,
                )

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = _fixture_repo(root)
            source_id = template_tool.load_catalog(repo)["source_repository_id"]
            with mock.patch.object(
                template_tool,
                "_github_repository_id",
                return_value=source_id + 1,
            ):
                with self.assertRaisesRegex(
                    template_tool.TemplateError,
                    "canonical GitHub repository ID must be",
                ):
                    template_tool.export_assignment(
                        repo,
                        "w00-individual-onboarding",
                        root / "wrong-id",
                    )

    def test_export_rejects_noncanonical_head_and_dirty_validated_input(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = _fixture_repo(root)
            _run_git(repo, "commit", "--allow-empty", "-q", "-m", "ahead")
            with _mock_live_source(repo):
                with self.assertRaisesRegex(
                    template_tool.TemplateError,
                    "must equal canonical",
                ):
                    template_tool.export_assignment(
                        repo,
                        "w00-individual-onboarding",
                        root / "ahead",
                    )

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = _fixture_repo(root)
            readme = repo / "README.md"
            readme.write_text(
                readme.read_text(encoding="utf-8") + "\nLocal change.\n",
                encoding="utf-8",
            )
            with _mock_live_source(repo):
                with self.assertRaisesRegex(
                    template_tool.TemplateError,
                    "uncommitted changes",
                ):
                    template_tool.export_assignment(
                        repo,
                        "w00-individual-onboarding",
                        root / "dirty",
                    )

    def test_spoofed_local_origin_ref_cannot_replace_live_branch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = _fixture_repo(root)
            live_commit = _git_output(repo, "rev-parse", "HEAD")
            _run_git(repo, "commit", "--allow-empty", "-q", "-m", "spoof")
            _run_git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
            with _mock_live_source(repo, live_commit=live_commit):
                with self.assertRaisesRegex(
                    template_tool.TemplateError,
                    "must equal live GitHub",
                ):
                    template_tool.export_assignment(
                        repo,
                        "w00-individual-onboarding",
                        root / "spoofed",
                    )
            self.assertFalse((root / "spoofed").exists())

    def test_existing_destination_is_preserved_and_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = _fixture_repo(root)
            destination = root / "occupied"
            destination.mkdir()
            marker = destination / "keep.txt"
            marker.write_text("keep\n", encoding="utf-8")
            with _mock_live_source(repo):
                with self.assertRaisesRegex(
                    template_tool.TemplateError,
                    "already exists",
                ):
                    template_tool.export_assignment(
                        repo,
                        "w00-individual-onboarding",
                        destination,
                    )
            self.assertEqual(marker.read_text(encoding="utf-8"), "keep\n")

    def test_github_repository_id_uses_explicit_read_only_request(self) -> None:
        completed = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="123\n",
            stderr="",
        )
        with mock.patch.object(
            template_tool.subprocess,
            "run",
            return_value=completed,
        ) as run:
            self.assertEqual(
                template_tool._github_repository_id("owner/repository"),
                123,
            )
        command = run.call_args.args[0]
        self.assertEqual(
            command,
            [
                "gh",
                "api",
                "--method",
                "GET",
                "--hostname",
                "github.com",
                "repos/owner/repository",
                "--jq",
                ".id",
            ],
        )

    def test_github_branch_commit_uses_explicit_read_only_request(self) -> None:
        commit = "a" * 40
        completed = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=commit + "\n",
            stderr="",
        )
        with mock.patch.object(
            template_tool.subprocess,
            "run",
            return_value=completed,
        ) as run:
            self.assertEqual(
                template_tool._github_branch_commit("owner/repository", "main"),
                commit,
            )
        command = run.call_args.args[0]
        self.assertEqual(
            command,
            [
                "gh",
                "api",
                "--method",
                "GET",
                "--hostname",
                "github.com",
                "repos/owner/repository/git/ref/heads/main",
                "--jq",
                ".object.sha",
            ],
        )


if __name__ == "__main__":
    unittest.main()
