# Week 0A — Individual Git and Classroom50 Practice

This is a short guided exercise. It teaches the basic workflow used by later course
assignments:

```text
accept → inspect → edit → commit → push → submit → read feedback → fix → resubmit
```

The automatic score checks only the final repository and its Git history. It does not
assess the quality of your course goal or prove that you typed every inspection command.

See [`docs/CLASSROOM50-WEB-UI.md`](docs/CLASSROOM50-WEB-UI.md) for the browser interface and CLI equivalents.

## 1. Accept and open the assignment

**Graphical path:** open the assignment link, sign in to Classroom50 with GitHub, open the organization marked **Student**, and choose **Accept assignment**. Follow the repository link shown after acceptance, then choose **Code → Codespaces** or clone it locally.

**CLI alternative:**

```bash
gh student accept VNU-HUS <classroom> w00-individual-onboarding
```

Classroom50 creates or locates the assignment repository; GitHub hosts the **remote** repository; the folder open on your computer or in Codespaces is your **working copy**.

## 2. Inspect the repository

Run:

```bash
pwd
git status
git branch --show-current
git remote -v
```

These commands show:

- `pwd`: your current directory;
- `git status`: the current branch and uncommitted changes;
- `git branch --show-current`: the current branch name;
- `git remote -v`: the GitHub repository connected as `origin`.

## 3. Complete and commit `profile.md`

Fill both answer sections in `profile.md`. Use your GitHub username and a non-sensitive
course goal. Do not add passwords, tokens, a university student ID, or other unnecessary
personal information.

Inspect the change and commit it:

```bash
git diff -- profile.md
git add profile.md
git status
git commit -m "Complete profile"
```

`git add` selects file content for the next commit. `git commit` records that selected
content in Git history.

## 4. Push and make an intentionally incomplete submission

This assignment uses tag-only grading. `git push` saves the commit; `gh student submit` records the official Classroom50 submission.

```bash
git push
gh student submit
```

This first submission should fail because `message.txt` still contains its starter placeholder. In Classroom50, open the assignment and choose **My submission**, then **View score**. Open the GitHub Feedback PR and read the reported missing requirement.

## 5. Complete and commit `message.txt`

Replace the entire content of `message.txt` with exactly:

```text
Hello, Classroom50!
```

Then run:

```bash
git diff -- message.txt
git add message.txt
git commit -m "Complete message"
git log --oneline -5
git push
python3 check_submission.py
gh student submit
```

## 6. Confirm completion

Return to Classroom50, open **My submission**, and confirm that the newest submission is shown. Open **View score** and the GitHub Feedback PR, and confirm that the final completion check passes.

The checker verifies only that:

- `profile.md` and `message.txt` are regular files with the required final content;
- a commit named exactly `Complete profile` changes `profile.md`;
- a later commit named exactly `Complete message` changes `message.txt`;
- both commits are in the submitted history and occur in that order.

The expected final result is:

```text
100/100  complete submission
```

> This is a completion score only. It does not assess whether the submitted work is
> mathematically, logically, algorithmically, or factually correct.
