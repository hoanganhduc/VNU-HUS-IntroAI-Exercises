# Week 3 — First-Order Predicate Logic: Exercise 3.9 scaffold

**Bibliographic reference:** Wolfgang Ertel, *Introduction to Artificial
Intelligence*, 3rd ed. (2025), Exercise 3.9, p. 66. The course interprets the
book's cross-reference in part (c) as Exercise 3.8.

This public package does not include or restate the exercise. Obtain an
authorized copy before editing the blank targets.

## Required submission

Complete:

```text
highjump.lop
russell.lop
semigroup.lop
comparison.md
```

The generic `proof.sh` helper can invoke E, but the completion checker does not
run it.

```bash
python3 check_submission.py
git add highjump.lop russell.lop semigroup.lop comparison.md
git commit -m "Complete Exercise 3.9"
git push
gh student submit
```

Read the shared [Classroom50 workflow](docs/CLASSROOM50-WEB-UI.md). The checker
verifies safe regular files, noncomment content in each target, and completed
response blocks. It does not assess any formalization, proof, or comparison.

```text
100/100  complete submission
0/100    incomplete submission
```
