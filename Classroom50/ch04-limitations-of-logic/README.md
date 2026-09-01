# Week 4 — Limitations of Logic: Exercise 4.3 scaffold

**Bibliographic reference:** Wolfgang Ertel, *Introduction to Artificial
Intelligence*, 3rd ed. (2025), p. 75. The source repeats an earlier exercise
number; the course citation for this item is Exercise 4.3.

This public package does not include or restate the exercise. Obtain an
authorized copy before editing the five blank targets.

## Required submission

```text
tweety1.lop
tweety2.lop
tweety3.lop
tweety4.lop
tweety5.lop
analysis.md
```

The generic `proof.sh` helper can invoke E; the completion checker does not.

```bash
python3 check_submission.py
git add tweety1.lop tweety2.lop tweety3.lop tweety4.lop tweety5.lop analysis.md
git commit -m "Complete Exercise 4.3"
git push
gh student submit
```

Read the shared [Classroom50 workflow](docs/CLASSROOM50-WEB-UI.md). The checker
verifies safe regular files, noncomment target content, and completed response
blocks. It does not assess the submitted logic or analysis.

```text
100/100  complete submission
0/100    incomplete submission
```
