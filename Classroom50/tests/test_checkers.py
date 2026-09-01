from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CLASSROOM50 = REPOSITORY_ROOT / "Classroom50"
PACKAGE_SLUGS = (
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
MARKER_TARGETS = {
    "ch01-introduction": ("submission.md", "RESPONSE"),
    "ch03-first-order-logic": ("comparison.md", "PART_A"),
    "ch04-limitations-of-logic": ("analysis.md", "TWEETY1_ANALYSIS"),
    "ch05-prolog": ("answers.md", "EXERCISE_5_3_ANSWERS"),
}
READY_FIXED_SYMLINK_TARGETS = {
    "w00-individual-onboarding": "profile.md",
    "w00-group-collaboration": "team.json",
    "ch01-introduction": "submission.md",
    "ch03-first-order-logic": "highjump.lop",
    "ch04-limitations-of-logic": "tweety1.lop",
    "ch05-prolog": "plan2.pl",
}


@contextmanager
def copied_package(slug: str) -> Iterator[Path]:
    with tempfile.TemporaryDirectory() as temporary_directory:
        destination = Path(temporary_directory) / slug
        shutil.copytree(CLASSROOM50 / slug, destination)
        yield destination


def run_checker(package: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", "check_submission.py"],
        cwd=package,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
        check=False,
    )


def run_teacher_command(
    package: Path, command: str
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=package,
        shell=True,
        executable="/bin/sh",
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
        check=False,
    )


def run_fixture_git(package: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=package,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
        check=True,
    )


def initialize_fixture_git(package: Path) -> None:
    run_fixture_git(package, "init", "-q", "-b", "main")
    run_fixture_git(package, "config", "user.name", "Template Test")
    run_fixture_git(package, "config", "user.email", "template-test@example.invalid")
    run_fixture_git(package, "add", ".")
    run_fixture_git(package, "commit", "-q", "-m", "Initial starter")


def trusted_teacher_run(package: Path) -> subprocess.CompletedProcess[str]:
    tests = json.loads(
        (package / "classroom50-tests.json").read_text(encoding="utf-8")
    )
    return run_teacher_command(package, tests[0]["run"])


def combined_output(result: subprocess.CompletedProcess[str]) -> str:
    return result.stdout + result.stderr


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def fill_ch06_explanation(package: Path, value: str = "A written explanation.") -> None:
    (package / "explanation.md").write_text(
        "# Exercise 6.6 response scaffold\n\n"
        "<!-- BEGIN:EXERCISE_6_6_DFS_EXPLANATION -->\n"
        f"{value}\n"
        "<!-- END:EXERCISE_6_6_DFS_EXPLANATION -->\n",
        encoding="utf-8",
    )


def prepare_complete_ch06(package: Path) -> dict[str, list[str]]:
    (package / "solution" / "search.py").write_text(
        "print('student search implementation')\n", encoding="utf-8"
    )
    manifest = {
        "exercise_6_6_files": ["search.py"],
        "exercise_6_12_files": ["search.py"],
    }
    write_json(package / "submission.json", manifest)
    fill_ch06_explanation(package)
    return manifest


class CompletionCheckerTests(unittest.TestCase):
    def assert_clean_failure(self, result: subprocess.CompletedProcess[str]) -> None:
        output = combined_output(result)
        self.assertEqual(result.returncode, 1, output)
        self.assertNotIn("Traceback", output)
        self.assertIn("FAIL", output)

    def test_all_untouched_starters_are_incomplete(self) -> None:
        for slug in PACKAGE_SLUGS:
            with self.subTest(slug=slug), copied_package(slug) as package:
                self.assert_clean_failure(run_checker(package))

    def test_reversed_markers_fail_cleanly(self) -> None:
        for slug, (filename, field) in MARKER_TARGETS.items():
            with self.subTest(slug=slug), copied_package(slug) as package:
                (package / filename).write_text(
                    f"<!-- END:{field} -->\nanswer\n<!-- BEGIN:{field} -->\n",
                    encoding="utf-8",
                )
                result = run_checker(package)
                self.assert_clean_failure(result)
                self.assertIn("must occur before", combined_output(result))

    def test_invalid_utf8_marker_files_fail_cleanly(self) -> None:
        for slug, (filename, _) in MARKER_TARGETS.items():
            with self.subTest(slug=slug), copied_package(slug) as package:
                (package / filename).write_bytes(b"\xff")
                result = run_checker(package)
                self.assert_clean_failure(result)
                self.assertIn("utf-8", combined_output(result).casefold())

    def test_week_zero_invalid_utf8_fails_cleanly(self) -> None:
        for slug, filename in (
            ("w00-individual-onboarding", "profile.md"),
            ("w00-group-collaboration", "team.json"),
        ):
            with self.subTest(slug=slug), copied_package(slug) as package:
                (package / filename).write_bytes(b"\xff")
                result = run_checker(package)
                self.assert_clean_failure(result)
                self.assertIn("utf-8", combined_output(result).casefold())

    def test_ch02_rejects_symlinked_student_file(self) -> None:
        with copied_package("ch02-propositional-logic") as package:
            (package / "outside.py").write_text("print('outside')\n", encoding="utf-8")
            os.symlink("../outside.py", package / "solution" / "answer.py")
            self.assert_clean_failure(run_checker(package))

    def test_ch02_control_char_filename_cannot_forge_output(self) -> None:
        with copied_package("ch02-propositional-logic") as package:
            forged = package / "solution" / "answer\n::error::forged.py"
            forged.write_text("print('student work')\n", encoding="utf-8")
            result = run_checker(package)
            self.assert_clean_failure(result)
            self.assertNotIn("::error::forged", combined_output(result))

    def test_ready_fixed_targets_reject_symbolic_links(self) -> None:
        for slug, filename in READY_FIXED_SYMLINK_TARGETS.items():
            with self.subTest(slug=slug), copied_package(slug) as package:
                target = package / filename
                payload = target.read_bytes()
                linked = package / "linked-starter-payload"
                linked.write_bytes(payload)
                target.unlink()
                target.symlink_to(linked.name)
                result = run_checker(package)
                self.assert_clean_failure(result)
                self.assertIn("symbolic link", combined_output(result))

    def test_ch05_rejects_solution_targets_linked_to_supplied_support(self) -> None:
        with copied_package("ch05-prolog") as package:
            for filename in ("plan2.pl", "ones.pl", "fib.pl", "fib01.pl"):
                target = package / filename
                target.unlink()
                target.symlink_to("support/plan.pl")
            answers = package / "answers.md"
            answers.write_text(
                answers.read_text(encoding="utf-8").replace(
                    "REPLACE_THIS_TEXT", "A completed written answer."
                ),
                encoding="utf-8",
            )
            result = run_checker(package)
            self.assert_clean_failure(result)
            self.assertIn("symbolic link", combined_output(result))

    def test_ch06_accepts_separate_declarations_that_share_one_file(self) -> None:
        with copied_package("ch06-search") as package:
            prepare_complete_ch06(package)
            result = run_checker(package)
            output = combined_output(result)
            self.assertEqual(result.returncode, 0, output)
            self.assertIn("100/100 complete submission", output)

    def test_ch06_rejects_supplied_readme_as_both_submissions(self) -> None:
        with copied_package("ch06-search") as package:
            write_json(
                package / "submission.json",
                {
                    "exercise_6_6_files": ["README.md"],
                    "exercise_6_12_files": ["README.md"],
                },
            )
            fill_ch06_explanation(package)
            result = run_checker(package)
            self.assert_clean_failure(result)
            self.assertIn("not supplied solution/README.md", combined_output(result))

    def test_ch06_control_and_bidi_paths_cannot_forge_output(self) -> None:
        for label, filename in (
            ("newline", "answer\n::error::forged.py"),
            ("bidi", "answer\u202eforged.py"),
        ):
            with self.subTest(case=label), copied_package("ch06-search") as package:
                prepare_complete_ch06(package)
                (package / "solution" / filename).write_text(
                    "print('student work')\n", encoding="utf-8"
                )
                write_json(
                    package / "submission.json",
                    {
                        "exercise_6_6_files": [filename],
                        "exercise_6_12_files": [filename],
                    },
                )
                result = run_checker(package)
                self.assert_clean_failure(result)
                self.assertNotIn("::error::forged", combined_output(result))

    def test_ch06_rejects_malformed_manifest(self) -> None:
        with copied_package("ch06-search") as package:
            prepare_complete_ch06(package)
            (package / "submission.json").write_text("{", encoding="utf-8")
            self.assert_clean_failure(run_checker(package))

    def test_ch06_rejects_invalid_manifest_entries(self) -> None:
        cases: tuple[tuple[str, Any], ...] = (
            ("top-level array", []),
            (
                "empty declaration",
                {
                    "exercise_6_6_files": [],
                    "exercise_6_12_files": ["search.py"],
                },
            ),
            (
                "wrong field type",
                {
                    "exercise_6_6_files": "search.py",
                    "exercise_6_12_files": ["search.py"],
                },
            ),
            (
                "wrong entry type",
                {
                    "exercise_6_6_files": [7],
                    "exercise_6_12_files": ["search.py"],
                },
            ),
            (
                "path traversal",
                {
                    "exercise_6_6_files": ["../outside.py"],
                    "exercise_6_12_files": ["search.py"],
                },
            ),
            (
                "directory",
                {
                    "exercise_6_6_files": ["directory"],
                    "exercise_6_12_files": ["search.py"],
                },
            ),
            (
                "empty file",
                {
                    "exercise_6_6_files": ["empty.py"],
                    "exercise_6_12_files": ["search.py"],
                },
            ),
            (
                "extra field",
                {
                    "exercise_6_6_files": ["search.py"],
                    "exercise_6_12_files": ["search.py"],
                    "unexpected": [],
                },
            ),
        )

        for label, manifest in cases:
            with self.subTest(case=label), copied_package("ch06-search") as package:
                prepare_complete_ch06(package)
                (package / "solution" / "directory").mkdir()
                (package / "solution" / "empty.py").write_bytes(b"")
                (package / "outside.py").write_text(
                    "print('outside')\n", encoding="utf-8"
                )
                write_json(package / "submission.json", manifest)
                self.assert_clean_failure(run_checker(package))

    def test_ch06_rejects_symlinked_declared_file(self) -> None:
        with copied_package("ch06-search") as package:
            manifest = prepare_complete_ch06(package)
            (package / "outside.py").write_text("print('outside')\n", encoding="utf-8")
            os.symlink("../outside.py", package / "solution" / "linked.py")
            manifest["exercise_6_6_files"] = ["linked.py"]
            write_json(package / "submission.json", manifest)
            result = run_checker(package)
            self.assert_clean_failure(result)
            self.assertIn("symbolic link", combined_output(result))

    def test_ch06_reversed_explanation_markers_fail_cleanly(self) -> None:
        with copied_package("ch06-search") as package:
            prepare_complete_ch06(package)
            (package / "explanation.md").write_text(
                "<!-- END:EXERCISE_6_6_DFS_EXPLANATION -->\n"
                "answer\n"
                "<!-- BEGIN:EXERCISE_6_6_DFS_EXPLANATION -->\n",
                encoding="utf-8",
            )
            result = run_checker(package)
            self.assert_clean_failure(result)
            self.assertIn("must occur before", combined_output(result))

    def test_ch06_rejects_empty_or_placeholder_explanation(self) -> None:
        for label, value in (
            ("empty", ""),
            ("placeholder", "REPLACE_THIS_TEXT"),
        ):
            with self.subTest(case=label), copied_package("ch06-search") as package:
                prepare_complete_ch06(package)
                fill_ch06_explanation(package, value)
                self.assert_clean_failure(run_checker(package))


class TeacherRunIntegrityTests(unittest.TestCase):
    def load_test(self, slug: str) -> tuple[Path, dict[str, Any]]:
        package = CLASSROOM50 / slug
        tests = json.loads(
            (package / "classroom50-tests.json").read_text(encoding="utf-8")
        )
        self.assertEqual(len(tests), 1)
        return package, tests[0]

    def test_every_teacher_run_authenticates_and_executes_same_bytes(self) -> None:
        required_fragments = (
            "python3 -I -c",
            "os.O_RDONLY|os.O_NOFOLLOW",
            "stat.S_ISREG(os.fstat(fd).st_mode)",
            "b=f.read()",
            "hashlib.sha256(b).hexdigest()",
            'exec(compile(b,p,"exec")',
        )
        for slug in PACKAGE_SLUGS:
            with self.subTest(slug=slug):
                package, test = self.load_test(slug)
                digest = hashlib.sha256(
                    (package / "check_submission.py").read_bytes()
                ).hexdigest()
                self.assertEqual(test["type"], "run")
                self.assertEqual(test["timeout"], 30)
                self.assertEqual(test["points"], 100)
                command = test["run"]
                self.assertIn(f'expected="{digest}"', command)
                for fragment in required_fragments:
                    self.assertIn(fragment, command)

    def test_trusted_teacher_run_executes_checker(self) -> None:
        _, test = self.load_test("ch06-search")
        with copied_package("ch06-search") as package:
            result = run_teacher_command(package, test["run"])
            output = combined_output(result)
            self.assertEqual(result.returncode, 1, output)
            self.assertIn("0/100 incomplete submission", output)
            self.assertNotIn("untrusted check_submission.py", output)

    def test_teacher_run_rejects_tampered_checker_without_executing_it(self) -> None:
        _, test = self.load_test("ch06-search")
        with copied_package("ch06-search") as package:
            (package / "check_submission.py").write_text(
                'print("MALICIOUS_EXECUTED")\n', encoding="utf-8"
            )
            result = run_teacher_command(package, test["run"])
            output = combined_output(result)
            self.assertNotEqual(result.returncode, 0, output)
            self.assertIn("FAIL untrusted check_submission.py", output)
            self.assertNotIn("MALICIOUS_EXECUTED", output)

    def test_teacher_run_rejects_symlinked_checker(self) -> None:
        _, test = self.load_test("ch06-search")
        with copied_package("ch06-search") as package:
            checker = package / "check_submission.py"
            trusted_copy = package / "trusted-checker.py"
            checker.rename(trusted_copy)
            checker.symlink_to(trusted_copy.name)
            result = run_teacher_command(package, test["run"])
            output = combined_output(result)
            self.assertNotEqual(result.returncode, 0, output)
            self.assertNotIn("0/100 incomplete submission", output)


class PositiveSubmissionTests(unittest.TestCase):
    def assert_teacher_accepts(self, package: Path) -> None:
        result = trusted_teacher_run(package)
        output = combined_output(result)
        self.assertEqual(result.returncode, 0, output)
        self.assertIn("100/100 complete submission", output)

    def test_week_zero_individual_prescribed_history_passes(self) -> None:
        with copied_package("w00-individual-onboarding") as package:
            initialize_fixture_git(package)
            profile = package / "profile.md"
            profile.write_text(
                profile.read_text(encoding="utf-8")
                .replace("REPLACE_THIS_TEXT", "studentname", 1)
                .replace("REPLACE_THIS_TEXT", "Learn introductory AI methods.", 1),
                encoding="utf-8",
            )
            run_fixture_git(package, "add", "profile.md")
            run_fixture_git(package, "commit", "-q", "-m", "Complete profile")
            (package / "message.txt").write_text(
                "Hello, Classroom50!\n", encoding="utf-8"
            )
            run_fixture_git(package, "add", "message.txt")
            run_fixture_git(package, "commit", "-q", "-m", "Complete message")
            self.assert_teacher_accepts(package)

    def test_week_zero_group_prescribed_history_passes(self) -> None:
        with copied_package("w00-group-collaboration") as package:
            initialize_fixture_git(package)
            write_json(
                package / "team.json",
                {"team_name": "Test team", "members": ["alice"]},
            )
            run_fixture_git(package, "add", "team.json")
            run_fixture_git(package, "commit", "-q", "-m", "Set team members")

            run_fixture_git(package, "checkout", "-q", "-b", "profile-alice")
            template = (package / "members" / "TEMPLATE.md").read_text(
                encoding="utf-8"
            )
            profile = (
                template.replace("REPLACE_THIS_TEXT", "alice", 1)
                .replace("REPLACE_THIS_TEXT", "git status", 1)
                .replace(
                    "REPLACE_THIS_TEXT",
                    "It shows the current repository state.",
                    1,
                )
            )
            (package / "members" / "alice.md").write_text(profile, encoding="utf-8")
            run_fixture_git(package, "add", "members/alice.md")
            run_fixture_git(package, "commit", "-q", "-m", "Add profile for alice")

            run_fixture_git(package, "checkout", "-q", "main")
            run_fixture_git(
                package,
                "merge",
                "--no-ff",
                "-q",
                "profile-alice",
                "-m",
                "Merge profile for alice",
            )
            summary = package / "summary.md"
            summary.write_text(
                summary.read_text(encoding="utf-8").replace(
                    "REPLACE_THIS_TEXT", "A sufficiently detailed explanation."
                ),
                encoding="utf-8",
            )
            run_fixture_git(package, "add", "summary.md")
            run_fixture_git(
                package, "commit", "-q", "-m", "Complete group submission"
            )
            self.assert_teacher_accepts(package)

    def test_ready_chapter_submissions_pass(self) -> None:
        for slug in (
            "ch01-introduction",
            "ch02-propositional-logic",
            "ch03-first-order-logic",
            "ch04-limitations-of-logic",
            "ch05-prolog",
            "ch06-search",
        ):
            with self.subTest(slug=slug), copied_package(slug) as package:
                if slug == "ch01-introduction":
                    submission = package / "submission.md"
                    submission.write_text(
                        submission.read_text(encoding="utf-8")
                        .replace("REPLACE_THIS_TEXT", "A completed response."),
                        encoding="utf-8",
                    )
                elif slug == "ch02-propositional-logic":
                    (package / "solution" / "answer.py").write_text(
                        "print('student solution')\n", encoding="utf-8"
                    )
                elif slug == "ch03-first-order-logic":
                    for filename in ("highjump.lop", "russell.lop", "semigroup.lop"):
                        (package / filename).write_text("student_fact.\n", encoding="utf-8")
                    comparison = package / "comparison.md"
                    comparison.write_text(
                        comparison.read_text(encoding="utf-8").replace(
                            "REPLACE_THIS_TEXT", "A completed comparison."
                        ),
                        encoding="utf-8",
                    )
                elif slug == "ch04-limitations-of-logic":
                    for index in range(1, 6):
                        (package / f"tweety{index}.lop").write_text(
                            "student_fact.\n", encoding="utf-8"
                        )
                    analysis = package / "analysis.md"
                    analysis.write_text(
                        analysis.read_text(encoding="utf-8").replace(
                            "REPLACE_THIS_TEXT", "A completed analysis."
                        ),
                        encoding="utf-8",
                    )
                elif slug == "ch05-prolog":
                    for filename in ("plan2.pl", "ones.pl", "fib.pl", "fib01.pl"):
                        (package / filename).write_text(
                            "student_fact.\n", encoding="utf-8"
                        )
                    answers = package / "answers.md"
                    answers.write_text(
                        answers.read_text(encoding="utf-8").replace(
                            "REPLACE_THIS_TEXT", "A completed written answer."
                        ),
                        encoding="utf-8",
                    )
                else:
                    prepare_complete_ch06(package)
                self.assert_teacher_accepts(package)


if __name__ == "__main__":
    unittest.main()
