# Personal Git Practice

This guided lesson teaches the Git and GitHub workflow used throughout the course. Work in **your own repository created from the course template**.

This repository-native lesson does not create a Classroom50 assignment. For the browser
steps used when accepting and inspecting real course assignments, read the shared
[Classroom50 graphical workflow](../../Classroom50/shared/CLASSROOM50-WEB-UI.md).

Do not rush through the commands. For each module:

```text
Explain → Predict → Perform → Observe → Check → Repair
```

Open this file in VS Code before opening a terminal. The course Codespace normally starts the terminal in the directory of the active file. Confirm the location with:

```bash
pwd
git rev-parse --show-toplevel
```

You can run each checkpoint from this folder:

```bash
bash check.sh <checkpoint>
```

Available checkpoints are:

```text
environment
content
committed
pushed
final
```

## Module 1 - Distinguish the systems and interfaces

### Concept

The names below are related, but they are not interchangeable.

| System | What it does |
|---|---|
| **Git** | Records local versions of files as commits and supports branches and merges. |
| **GitHub** | Hosts Git repositories and supplies issues, pull requests, reviews, checks, and collaborators. |
| **GitHub Codespaces** | Runs the configured development environment in a browser. |
| **Classroom50 web app** | Lets students find and accept assignments, manage group collaborators, and open submission or grade information. |
| **Classroom50 CLI** | Provides exact terminal commands such as `gh student accept`, `gh student invite`, and `gh student submit`. |

A Git repository can exist without GitHub. A GitHub repository uses Git, but GitHub also supplies collaboration services that are not part of Git itself.

### Predict

Before running any command, fill the five `*_ROLE` fields in [`workbook.md`](workbook.md) using these exact values:

```text
local-history
hosted-collaboration
development-environment
assignment-browser-workflow
assignment-command-line-workflow
```

### Perform

First open the shared [illustrated Classroom50 guide](../../Classroom50/shared/CLASSROOM50-WEB-UI.md) and identify one browser action and one CLI action. Then verify the installed tools and authentication:

```bash
git --version
gh --version
python3 --version
gh auth status
```

### Check

```bash
bash check.sh environment
```

### Repair

- When `gh` is unavailable in a Codespace created before the repository configuration changed, pull the latest changes and run **Codespaces: Rebuild Container**.
- For a local installation, install GitHub CLI, run `gh extension install foundation50/gh-student --pin v1.40.0`, and then run `gh auth login`.
- If `origin` points to `hoanganhduc/VNU-HUS-IntroAI-Exercises`, you cloned the canonical repository rather than creating your own repository from the template. Stop before pushing and create your own repository.

## Module 2 - Repository, working tree, branch, and remote

### Concept

A **repository** stores project history. The files you currently see form the **working tree**. A **branch** names a line of commits. A **remote** is a named connection to another repository, usually the copy hosted on GitHub.

Useful commands:

| Command | Purpose |
|---|---|
| `pwd` | Print the current working directory. |
| `ls` | List files in the current directory. |
| `git rev-parse --show-toplevel` | Print the repository root. |
| `git status` | Show the current branch and uncommitted changes. |
| `git branch --show-current` | Print the current branch name. |
| `git remote -v` | Show remote names and URLs. |

### Predict

A new repository generated from a template should initially have no changes in its working tree. Record your prediction in `STATUS_BEFORE_EDIT`.

### Perform

```bash
pwd
ls
git rev-parse --show-toplevel
git status
git branch --show-current
git remote -v
```

Record the repository root, branch, origin URL, and observed status in [`workbook.md`](workbook.md).

### Observe

Compare the path printed by `pwd` with the repository root. They may differ: a command can run from a subdirectory while still belonging to the same repository.

## Module 3 - Edit and inspect a change

### Concept

Editing a file changes the working tree, but it does not create a commit. `git status` summarizes changed files; `git diff` shows the changed lines that are not staged.

### Predict

Before editing, set:

```text
PREDICT_AFTER_EDIT: modified-not-staged
```

### Perform

1. Replace every `REPLACE_THIS_TEXT` field in [`profile.md`](profile.md). Use only your GitHub username and a non-sensitive course goal; do not add a university student ID or legal name.
2. Replace the content of [`message.txt`](message.txt) with exactly:

   ```text
   Hello, Git and GitHub!
   ```

3. Inspect the result:

   ```bash
   git status
   git diff -- profile.md message.txt
   ```

4. Run the content checkpoint:

   ```bash
   bash check.sh content
   ```

The starter files are intentionally incomplete, so running `bash check.sh content` **before** editing should fail. Read the diagnostic, make the requested changes, and rerun it until it passes.

### Observe

In `DIFF_OBSERVATION`, describe one concrete line shown by `git diff`.

### Repair

To discard an accidental, unstaged change to one file:

```bash
git restore <file>
```

Do not run `git restore` on work you intend to keep.

## Module 4 - Stage and commit

### Concept

The relevant states are:

```text
working tree --git add--> staging area --git commit--> local history
```

`git add` selects the current file content for the next commit. `git diff --staged` shows that selection. `git commit` records it in local history.

| Command | Purpose |
|---|---|
| `git add <file>` | Stage a file for the next commit. |
| `git diff --staged` | Inspect staged changes. |
| `git commit -m "..."` | Create a commit with a message. |
| `git log --oneline` | Show compact commit history. |
| `git restore --staged <file>` | Remove a file from the staging area without discarding its working-tree content. |

### Predict

Set:

```text
PREDICT_AFTER_ADD: staged
```

### Perform

Stage only the two edited content files:

```bash
git add profile.md message.txt
git status
git diff --staged -- profile.md message.txt
```

As a safe recovery exercise, unstage and restage `message.txt`:

```bash
git restore --staged message.txt
git status
git add message.txt
```

Commit:

```bash
git commit -m "Complete personal Git practice content"
git log --oneline -5
```

Record the short ID of this commit in `CONTENT_COMMIT_ID` and describe the staging recovery in `UNSTAGE_OBSERVATION`.

### Check

```bash
bash check.sh committed
```

This checkpoint verifies that `profile.md` and `message.txt` contain the required content, are committed, and have no remaining unstaged or staged changes.

## Module 5 - Push and pull

### Concept

A commit is initially local. `git push` sends commits to GitHub. `git pull --ff-only` downloads remote commits and advances the local branch only when no local merge is required.

Committing and pushing are therefore different actions:

```text
commit = record local history
push   = send local commits to a remote repository
```

### Predict

Before pushing, answer `COMMIT_VS_PUSH` and predict whether the new commit is visible on the GitHub web page.

### Perform

```bash
git push -u origin "$(git branch --show-current)"
```

Open the repository on GitHub and verify the commit. Then run:

```bash
git pull --ff-only
```

Record what you observed in `PUSH_OBSERVATION`.

### Check

```bash
bash check.sh pushed
```

The checkpoint requires an upstream branch and verifies that the local branch is neither ahead of nor behind it.

## Module 6 - Deliberate failure and safe restoration

### Concept

A failing check is useful information. Read its output, locate the violated requirement, repair the smallest relevant part, and run the check again.

### Perform

Temporarily change `message.txt` to an incorrect value. Do **not** commit it.

```bash
printf '%s\n' 'This value is intentionally wrong.' > message.txt
bash check.sh content
```

The check should fail. Inspect the difference:

```bash
git diff -- message.txt
```

Restore the committed version:

```bash
git restore message.txt
bash check.sh content
```

Record:

```text
FIRST_CHECK_RESULT: fail
RESTORE_RESULT: restored-committed-version
```

and explain what `git restore message.txt` did in `RESTORE_OBSERVATION`.

## Module 7 - Complete the workbook and verify the result

### Concept

A good repository records both the completed work and enough explanation to reproduce the workflow. The final checkpoint does not grade the quality of open prose; it checks required structure and observable Git state.

### Perform

1. Complete every remaining field in [`workbook.md`](workbook.md).
2. Record your GitHub repository URL in `FINAL_GITHUB_URL`.
3. Commit and push the workbook:

   ```bash
   git add workbook.md
   git commit -m "Complete personal Git practice workbook"
   git push
   ```

4. Run:

   ```bash
   bash check.sh final
   ```

5. Inspect the final repository and commit history on GitHub.

### Final reflection

Make sure the workbook explains, in your own words:

- the difference between the working tree, staging area, and committed history;
- the difference between committing and pushing;
- why `git pull --ff-only` is safer than silently creating an unexpected merge in this simple workflow;
- what the failed check taught you;
- what `git restore` and `git restore --staged` changed.

## What this lesson does not cover

This personal lesson does not use issues, pull requests, reviews, or merges. Continue with [Solo Collaboration Practice](../Solo%20Collaboration%20Practice/) after the final checkpoint passes.
