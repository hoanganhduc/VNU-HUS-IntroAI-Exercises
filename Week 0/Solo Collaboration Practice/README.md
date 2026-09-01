# Solo Collaboration Practice

This guided lesson uses one GitHub account to practise the mechanics of repository collaboration in your own template-derived exercise repository.

This lesson uses GitHub's graphical Issues and Pull Requests together with CLI commands. It
does not itself create a Classroom50 assignment. The shared
[Classroom50 graphical workflow](../../Classroom50/shared/CLASSROOM50-WEB-UI.md) explains
browser-based assignment acceptance, collaborator management, and result inspection.

It follows the same cycle as the personal lesson:

```text
Explain → Predict → Perform → Observe → Check → Repair
```

Complete [Personal Git Practice](../Personal%20Git%20Practice/) first. Begin this lesson with `main` clean and synchronized with `origin/main`. The shared [illustrated Classroom50 web and CLI guide](../../Classroom50/shared/CLASSROOM50-WEB-UI.md) covers assignment acceptance, group collaborators, submission, and feedback; this lesson focuses on GitHub Issues and pull requests.

## What this lesson can and cannot simulate

A one-person repository can authentically practise:

- issues and assignees;
- feature branches;
- draft pull requests;
- pull-request diffs and automated checks;
- review comments and corrective commits;
- merge commits and branch synchronization;
- a controlled merge conflict.

It cannot reproduce:

- inviting and authorizing a collaborator;
- an independent reviewer identity;
- a shared group score;
- genuine approval by another person.

GitHub does not allow a pull-request author to approve their own pull request. Therefore this lesson requires a visible **self-review comment and correction**, not a fake self-approval. The Classroom50 group-onboarding assignment accepts one to five members. A singleton repeats the GitHub workflow; a multi-person group adds peer review and shared work.

Do not put a university student ID or legal name in the member profile. The GitHub username is sufficient for this public practice artifact.

## Files used by the lesson

| File | Purpose |
|---|---|
| [`team.json`](team.json) | Final one-person-team record |
| [`workbook.md`](workbook.md) | URLs, predictions, observations, and limitations |
| [`members/TEMPLATE.md`](members/TEMPLATE.md) | Template for your profile contribution |
| [`shared/merge-practice.txt`](shared/merge-practice.txt) | The line changed by the controlled-conflict branches |
| [`issue-body-profile.md`](issue-body-profile.md) | Source for the profile issue body |
| [`issue-body-conflict.md`](issue-body-conflict.md) | Source for the conflict issue bodies |
| [`pr-body-profile.md`](pr-body-profile.md) | Source for the profile pull-request body |
| [`pr-body-conflict.md`](pr-body-conflict.md) | Source for the conflict pull-request bodies |
| [`check.sh`](check.sh) | Local and GitHub-metadata checkpoints |

The repository also contains a pull-request workflow at [`.github/workflows/week0-solo-collaboration.yml`](../../.github/workflows/week0-solo-collaboration.yml).

## Preparation

### Concept

GitHub CLI can create and inspect issues and pull requests without leaving the terminal. The commands still act on the same GitHub objects visible in the web interface.

### Perform

From the repository root or this lesson directory:

```bash
gh auth status
USERNAME="$(gh api user --jq .login)"
printf 'GitHub username: %s\n' "$USERNAME"
git switch main
git pull --ff-only
git status
```

Record the username in `GITHUB_USERNAME` only during the final documentation phase; do not edit `workbook.md` directly on `main` now.

## Module 1 - Create and assign a profile issue

### Concept

An **issue** describes work before the implementation begins. A useful issue identifies the intended result, assigns responsibility, and gives acceptance criteria that can later be checked.

### Predict

Answer `WHY_ISSUE_FIRST` in the workbook draft you will complete later: why is it useful to state the expected result before changing files?

### Perform

Create a temporary issue-body file without modifying the repository template:

```bash
sed "s/REPLACE_WITH_GITHUB_USERNAME/$USERNAME/g" \
  issue-body-profile.md > /tmp/week0-profile-issue.md
```

Create and self-assign the issue:

```bash
PROFILE_ISSUE_URL="$(gh issue create \
  --title "Week 0 solo profile: $USERNAME" \
  --body-file /tmp/week0-profile-issue.md \
  --assignee @me)"
printf '%s\n' "$PROFILE_ISSUE_URL"
```

Keep the URL. It will be recorded in `workbook.md` later.

### Observe

Open the issue and identify its title, body, assignee, and checklist.

## Module 2 - Isolate work on a feature branch

### Concept

A branch gives a change its own line of history. It lets the default branch remain stable while work is prepared and checked.

Useful commands:

| Command | Purpose |
|---|---|
| `git switch main` | Move to the default branch. |
| `git pull --ff-only` | Synchronize the local default branch without an unexpected merge. |
| `git switch -c <branch>` | Create and enter a new branch. |
| `git branch --show-current` | Print the active branch. |

### Predict

The new branch points to the same starting commit as `main` until its first commit is created. Record this idea in `WHY_BRANCH` later.

### Perform

```bash
git switch main
git pull --ff-only
git switch -c "solo/profile-$USERNAME"
cp members/TEMPLATE.md "members/$USERNAME.md"
```

Edit `members/$USERNAME.md`:

- replace the student ID and username placeholders;
- explain one useful Git command;
- **leave the literal `TODO_REVIEW` in the final section for now**.

Commit and push:

```bash
git add "members/$USERNAME.md"
git commit -m "Add solo profile for $USERNAME"
git push -u origin "solo/profile-$USERNAME"
```

## Module 3 - Open a draft pull request and inspect a failed check

### Concept

A pull request proposes merging a **head branch** into a **base branch**. A draft pull request indicates that the proposal is not ready to merge. Its **Files changed** tab shows the diff; its **Checks** tab shows automated validation.

Pushing a branch does not merge it. Opening a pull request also does not merge it.

### Perform

Extract the issue number and prepare the PR body:

```bash
PROFILE_ISSUE_NUMBER="${PROFILE_ISSUE_URL##*/}"
sed \
  -e "s/REPLACE_WITH_ISSUE_NUMBER/$PROFILE_ISSUE_NUMBER/g" \
  -e "s/REPLACE_WITH_GITHUB_USERNAME/$USERNAME/g" \
  pr-body-profile.md > /tmp/week0-profile-pr.md
```

Open a draft PR:

```bash
PROFILE_PR_URL="$(gh pr create \
  --base main \
  --head "solo/profile-$USERNAME" \
  --title "Add solo profile for $USERNAME" \
  --body-file /tmp/week0-profile-pr.md \
  --draft)"
printf '%s\n' "$PROFILE_PR_URL"
```

Inspect the PR:

```bash
gh pr view "$PROFILE_PR_URL" --web
```

The public check should fail because `TODO_REVIEW` remains in the profile. Record later:

```text
PROFILE_CHECK_FIRST_RESULT: fail
```

### Repair by self-review

A real reviewer would identify the problem. In this solo simulation, leave a specific self-review comment instead:

```bash
gh pr comment "$PROFILE_PR_URL" \
  --body "Self-review: the profile still contains TODO_REVIEW. Replace it with a concrete observation before merging."
```

Edit the profile, remove `TODO_REVIEW`, and write a concrete observation about inspecting the pull-request diff. Then:

```bash
git add "members/$USERNAME.md"
git commit -m "Address solo profile self-review"
git push
```

Mark the PR ready:

```bash
gh pr ready "$PROFILE_PR_URL"
```

Wait for the public check to pass and record later:

```text
PROFILE_CHECK_AFTER_REPAIR: pass
```

Do **not** try to approve your own PR. Record:

```text
SELF_APPROVAL: impossible
```

## Module 4 - Merge and synchronize

### Concept

A merge incorporates the proposed commits into the base branch. The remote `main` changes immediately, but your local `main` remains unchanged until you fetch or pull it.

For this lesson use a **merge commit** so the branch history remains visible.

### Perform

```bash
gh pr merge "$PROFILE_PR_URL" --merge --delete-branch
git switch main
git pull --ff-only
git branch -d "solo/profile-$USERNAME"
```

Confirm that `members/$USERNAME.md` is now present on local `main`.

Record later:

- `PR_VS_MERGE`: the difference between proposing and incorporating a change;
- `WHY_LOCAL_MAIN_NEEDED_PULL`: why the local branch did not change at the instant GitHub merged the PR.

The linked issue should close automatically because the PR body contains `Closes #...`.

## Module 5 - Prepare two branches that will conflict

### Concept

A merge conflict occurs when Git cannot safely combine competing changes. To make the process reproducible, both conflict branches must start from the same version of `main` and change the same line differently.

### Create two issues

```bash
sed \
  -e "s/REPLACE_WITH_GITHUB_USERNAME/$USERNAME/g" \
  -e "s/REPLACE_WITH_CONFLICT_ROLE/alpha/g" \
  issue-body-conflict.md > /tmp/week0-conflict-alpha-issue.md

ALPHA_ISSUE_URL="$(gh issue create \
  --title "Week 0 controlled conflict: alpha" \
  --body-file /tmp/week0-conflict-alpha-issue.md \
  --assignee @me)"

sed \
  -e "s/REPLACE_WITH_GITHUB_USERNAME/$USERNAME/g" \
  -e "s/REPLACE_WITH_CONFLICT_ROLE/beta/g" \
  issue-body-conflict.md > /tmp/week0-conflict-beta-issue.md

BETA_ISSUE_URL="$(gh issue create \
  --title "Week 0 controlled conflict: beta" \
  --body-file /tmp/week0-conflict-beta-issue.md \
  --assignee @me)"
```

### Create alpha from the common base

```bash
git switch main
git pull --ff-only
git switch -c "solo/conflict-alpha-$USERNAME"
printf '%s\n' 'decision = proposal-alpha' > shared/merge-practice.txt
git add shared/merge-practice.txt
git commit -m "Add alpha conflict proposal"
git push -u origin "solo/conflict-alpha-$USERNAME"
```

### Create beta from the same common base

Return to the still-unchanged local `main` **before merging alpha**:

```bash
git switch main
git switch -c "solo/conflict-beta-$USERNAME"
printf '%s\n' 'decision = proposal-beta' > shared/merge-practice.txt
git add shared/merge-practice.txt
git commit -m "Add beta conflict proposal"
git push -u origin "solo/conflict-beta-$USERNAME"
```

## Module 6 - Open and merge the alpha PR

Prepare bodies and open both PRs:

```bash
ALPHA_ISSUE_NUMBER="${ALPHA_ISSUE_URL##*/}"
BETA_ISSUE_NUMBER="${BETA_ISSUE_URL##*/}"

sed \
  -e "s/REPLACE_WITH_ISSUE_NUMBER/$ALPHA_ISSUE_NUMBER/g" \
  -e "s/REPLACE_WITH_CONFLICT_ROLE/alpha/g" \
  pr-body-conflict.md > /tmp/week0-conflict-alpha-pr.md

sed \
  -e "s/REPLACE_WITH_ISSUE_NUMBER/$BETA_ISSUE_NUMBER/g" \
  -e "s/REPLACE_WITH_CONFLICT_ROLE/beta/g" \
  pr-body-conflict.md > /tmp/week0-conflict-beta-pr.md

ALPHA_PR_URL="$(gh pr create \
  --base main \
  --head "solo/conflict-alpha-$USERNAME" \
  --title "Add alpha conflict proposal" \
  --body-file /tmp/week0-conflict-alpha-pr.md)"

BETA_PR_URL="$(gh pr create \
  --base main \
  --head "solo/conflict-beta-$USERNAME" \
  --title "Add beta conflict proposal" \
  --body-file /tmp/week0-conflict-beta-pr.md)"
```

Wait for the alpha check, then merge alpha:

```bash
gh pr checks "$ALPHA_PR_URL" --watch
gh pr merge "$ALPHA_PR_URL" --merge --delete-branch
```

Do not merge beta yet.

## Module 7 - Resolve the beta conflict locally

### Concept

When you merge updated `origin/main` into beta, Git should display conflict markers:

```text
  <<<<<<< HEAD
  decision = proposal-beta
  =======
  decision = proposal-alpha
  >>>>>>> origin/main
```

`HEAD` denotes the current beta branch. The other block comes from the branch being merged. Resolving a conflict means constructing the intended final content and removing all markers; it does not mean arbitrarily keeping one side.

### Perform

```bash
git switch "solo/conflict-beta-$USERNAME"
git fetch origin
git merge origin/main
```

The merge command is expected to stop with a conflict. Inspect:

```bash
git status
git diff -- shared/merge-practice.txt
```

Replace the entire file with exactly:

```text
decision = proposal-alpha + proposal-beta
```

Then commit and push the resolution:

```bash
git add shared/merge-practice.txt
git commit -m "Resolve solo merge conflict"
git push
```

Wait for the corrected PR check and merge beta:

```bash
gh pr checks "$BETA_PR_URL" --watch
gh pr merge "$BETA_PR_URL" --merge --delete-branch
git switch main
git pull --ff-only
git branch -d "solo/conflict-beta-$USERNAME"
```

The final file must contain both proposals.

## Module 8 - Record the workflow through one final PR

### Concept

The repository should contain enough structured evidence to reproduce what happened. Record URLs rather than screenshots whenever possible; URLs are searchable and auditable.

### Perform

Create a final documentation branch:

```bash
git switch main
git pull --ff-only
git switch -c "solo/finalize-$USERNAME"
```

Edit [`team.json`](team.json) to contain exactly one member:

```json
{
  "team_name": "solo-YOUR_GITHUB_USERNAME",
  "members": ["YOUR_GITHUB_USERNAME"]
}
```

Complete every field in [`workbook.md`](workbook.md), including:

- the profile issue and PR URLs;
- the alpha and beta issue and PR URLs;
- the observations and conceptual explanations;
- the exact limitation that self-approval is impossible;
- the final repository URL.

Commit and push:

```bash
git add team.json workbook.md
git commit -m "Complete solo collaboration workbook"
git push -u origin "solo/finalize-$USERNAME"
```

Open a final PR:

```bash
FINAL_PR_URL="$(gh pr create \
  --base main \
  --head "solo/finalize-$USERNAME" \
  --title "Complete solo collaboration practice" \
  --body "Records the completed one-person collaboration simulation and its limitations.")"
```

Add `FINAL_PR_URL` to `workbook.md`, commit, and push the update:

```bash
git add workbook.md
git commit -m "Record final solo collaboration PR"
git push
```

Leave one self-review comment that names a concrete file or field you inspected:

```bash
gh pr comment "$FINAL_PR_URL" \
  --body "Self-review: I checked the team.json member against the profile filename and verified the final conflict result."
```

Wait for checks, then merge and synchronize:

```bash
gh pr checks "$FINAL_PR_URL" --watch
gh pr merge "$FINAL_PR_URL" --merge --delete-branch
git switch main
git pull --ff-only
git branch -d "solo/finalize-$USERNAME"
```

## Module 9 - Final checks

Run local history and file checks:

```bash
bash check.sh local
```

Then verify GitHub issues, PRs, comments, commits, and merged states:

```bash
bash check.sh github
```

Run both:

```bash
bash check.sh final
```

## What the final checks establish

The checks establish that the published workflow and repository states are present. They do not establish that self-review has the same value as peer review. In the Classroom50 group assignment, those additional outcomes occur only when the group has two or more members:

- collaborator invitations and shared access;
- contributions from distinct accounts;
- review by someone other than the author;
- a shared Classroom50 submission and score.
