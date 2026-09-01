# Week 6 — Search, Games and Problem Solving scaffolds

**Bibliographic references:** Wolfgang Ertel, *Introduction to Artificial
Intelligence*, 3rd ed. (2025), Exercises 6.6 and 6.12, pp. 125–126.

This public package does not include or restate the exercises. Obtain authorized
statements before writing the implementations. The reusable scaffold does not
prescribe a programming language or common input/output protocol.

## Required submission

Place implementation files under `solution/`. In `submission.json`, list at
least one safe path for each cited exercise. The same path may appear in both
lists when appropriate. Complete the marked response block in `explanation.md`
according to the authorized statement.

```json
{
  "exercise_6_6_files": ["answer.py"],
  "exercise_6_12_files": ["answer.py"]
}
```

```bash
python3 check_submission.py
git add solution submission.json explanation.md
git commit -m "Submit the Week 6 search code"
git push
gh student submit
```

Read the shared [Classroom50 workflow](docs/CLASSROOM50-WEB-UI.md). The checker
verifies path safety, nonempty declared files, and a completed response block.
It neither runs the code nor assesses the explanation.

```text
100/100  complete submission
0/100    incomplete submission
```
