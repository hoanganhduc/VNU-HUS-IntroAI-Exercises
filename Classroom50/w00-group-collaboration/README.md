# Week 0B — GitHub Collaboration Practice

This guided exercise teaches the branch–pull-request–merge workflow used for shared
repositories.

The assignment accepts **one to five members**:

- a one-person group practises the GitHub tools using one account;
- a group with two to five students additionally practises invitations, shared access,
  and peer review.

The automatic score checks only the final repository and its Git history. It does not use
the GitHub API and does not claim that a one-person group performed peer collaboration.

See [`docs/CLASSROOM50-WEB-UI.md`](docs/CLASSROOM50-WEB-UI.md) for browser acceptance, **Manage collaborators**, submission, and grade viewing.

## 1. Create one assignment repository

Only the designated founder accepts the Classroom50 assignment.

**Graphical path:** the founder opens the assignment link, chooses **Accept assignment**, then opens **Assignment settings** and **Manage collaborators**. A singleton adds nobody. For two to five students, the founder adds the other enrolled members.

**CLI alternative:**

```bash
gh student accept VNU-HUS <classroom> w00-group-collaboration
gh student invite VNU-HUS/<shared-repository> <github-username>
```

The other members join that repository instead of accepting separately. Every member opens or clones the same shared repository.

## 2. Record the members

Edit `team.json` so that it contains a non-placeholder team name and the GitHub usernames
of all actual members. The list may contain one to five distinct usernames.

Commit it on `main`:

```bash
git add team.json
git commit -m "Set team members"
git push
```

## 3. Create one contribution branch per member

Every member replaces `<username>` with their own GitHub username:

```bash
git switch main
git pull --ff-only
git switch -c member/<username>
cp members/TEMPLATE.md members/<username>.md
```

Fill `members/<username>.md`, then commit and push:

```bash
git add members/<username>.md
git commit -m "Add profile for <username>"
git push -u origin member/<username>
```

A branch keeps unfinished work separate from `main`. Pushing the branch makes it
available on GitHub but does not merge it.

## 4. Open and merge the pull request

Open a pull request from `member/<username>` to `main` and inspect **Files changed** and
the public check.

- **One-person group:** inspect the pull request yourself. Do not call this peer review,
  and do not try to approve your own pull request.
- **Two to five students:** ask another member to inspect the change and leave a short
  review comment or approval.

Merge using **Create a merge commit**. The automatic checker uses that merge commit as
final-repository evidence that the branch workflow was performed.

The course repository is configured so that an approving review is not mandatory for
this onboarding assignment. If GitHub refuses a singleton merge because another approval
is required, report the repository-setting problem to the instructor.

After the merge, the contribution author synchronizes their local `main`:

```bash
git switch main
git pull --ff-only
```

Repeat until every listed member has one merged profile contribution.

## 5. Complete and submit the summary

This assignment uses tag-only grading. `git push` saves the final commit; `gh student submit` records the official shared submission.

After all member pull requests are merged, fill every section in `summary.md` and commit
it on `main`:

```bash
git add summary.md
git commit -m "Complete group submission"
git push
python3 check_submission.py
gh student submit
```

Every member opens the assignment in Classroom50, chooses **My submission**, then opens **View score** and the shared GitHub Feedback PR. Everyone confirms that the same newest submission and result are visible.

## What the completion checker verifies

The checker verifies only that:

- `team.json`, member profiles, and `summary.md` are regular files rather than
  symbolic links;
- `team.json` contains one to five distinct GitHub usernames;
- every listed member has a filled `members/<username>.md`;
- `summary.md` is filled;
- commit `Set team members` changes `team.json`;
- each member has a commit `Add profile for <username>` changing the matching file;
- every profile commit entered the submitted history through a merge commit;
- commit `Complete group submission` changes `summary.md` after all profile merges.

It does not verify branch names, collaborator invitations, reviewer identity, review text,
or approval events. Those actions are part of the lesson, but they are not provable from
the final repository alone.

The expected final result is:

```text
100/100  complete submission
```

> This is a completion score only. It does not assess whether the submitted work is
> mathematically, logically, algorithmically, or factually correct.
