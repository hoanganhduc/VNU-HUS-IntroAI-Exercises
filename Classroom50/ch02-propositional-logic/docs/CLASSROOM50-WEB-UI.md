# Classroom50 graphical workflow

This guide shows the browser workflow used together with the command-line
instructions in each assignment. Classroom50, GitHub, and the local terminal
have different roles:

| System | Main role in the course |
|---|---|
| **Classroom50 web app** | Find or accept an assignment, manage group collaborators, and inspect a weekly submission result. |
| **GitHub web interface** | Open the repository, Codespaces, Issues, Pull Requests, commits, and the Feedback PR. |
| **Terminal and CLI** | Run Git commands, public checks, and the course submission command when required. |

This guide is text-only, so it stays usable on a slow connection and with a
screen reader. Button labels can change between Classroom50 versions; when a
label differs from the one printed here, look for the nearest equivalent on the
same page and report the difference to the instructor.

## 1. Sign in and find the course

### Graphical path

1. Open <https://classroom50.org>.
2. Choose **Sign in with GitHub**.
3. Open the VNU-HUS organization card marked **Student**.
4. Open the appropriate classroom and assignment.

### CLI alternative

When the instructor supplies an acceptance command, use:

```bash
gh student accept VNU-HUS <classroom> <assignment-slug>
```

### Expected result

Classroom50 shows the assignment and, after acceptance, a link to the GitHub
repository created for the student or group.

### If it does not work

When no **Student** card for VNU-HUS appears, the organization invitation is
still pending: open the invitation email or
<https://github.com/orgs/VNU-HUS/invitation>, accept it, then reload
Classroom50. When the classroom appears but the assignment does not, the
acceptance link has not been published yet.

## 2. Accept an individual assignment

### Graphical path

1. Open the assignment link supplied by the instructor.
2. Check the classroom and assignment name.
3. Choose **Accept assignment**.
4. Follow the repository link shown after acceptance.

### CLI alternative

```bash
gh student accept VNU-HUS <classroom> <assignment-slug>
```

Do not accept the same assignment through both routes. They are alternatives
that should lead to the same repository.

### Expected result

Classroom50 reports that the assignment is accepted and shows a link to a new
repository whose name ends with your GitHub username.

### If it does not work

An acceptance that appears to hang usually finished on the server: reload the
assignment page before accepting again. When the repository link returns a 404,
wait a few seconds and reload, because the repository is created immediately
after acceptance.

## 3. Accept a group assignment and add members

Only the designated founder accepts a group assignment.

### Graphical path

1. The founder opens the group-assignment link and chooses **Accept assignment**.
2. On the accepted assignment, open **Assignment settings**.
3. Choose **Manage collaborators**.
4. Add the other enrolled GitHub usernames. A one-person group adds nobody.
5. Every member opens the same GitHub repository.

### CLI alternative

```bash
gh student accept VNU-HUS <classroom> <assignment-slug>
gh student invite VNU-HUS/<shared-repository> <github-username>
```

Other members must not accept separately, because that may create duplicate
repositories.

### Expected result

One shared repository exists for the group, and every added member can open it
and push.

### If it does not work

A member who cannot open the repository has not been added as a collaborator,
or has not accepted the repository invitation on GitHub. When a second
repository was created by mistake, tell the instructor which repository the
group will use; do not delete anything yourself.

## 4. Open and edit the repository

Classroom50 creates or locates the assignment repository, but it does not edit
files or create Git commits.

### Graphical path

From the GitHub repository, choose **Code → Codespaces** to create or open a
Codespace. VS Code Source Control, GitHub Desktop, or another Git client may be
used for ordinary edits, commits, and pushes.

### Terminal path

```bash
git status
git add <files>
git commit -m "<message>"
git push
```

Follow the assignment README when it prescribes exact filenames or commit
messages.

### Expected result

`git push` reports the new commit, and the GitHub repository page shows it.

### If it does not work

When the push is rejected because the remote has newer commits, run
`git pull --ff-only`. If that reports divergent histories, stop and follow the
assignment-specific recovery instructions or ask the instructor; rebasing can
destroy merge-history evidence required by the group assignment. Before
deleting a Codespace, commit and push any work you need to keep. Unpushed work
can be lost when a Codespace is deleted.

## 5. Submit a Week 0–7 assignment

The course's current weekly assignments use the CLI submission command below.
Classroom50 may also display a browser submission action; follow the assignment
README when the available interfaces differ.

```bash
python3 check_submission.py
gh student submit
```

The first command is the public local completion check. For the course's tagged
submission mode, the second command pushes the current branch and a submission
tag, which records the official snapshot and starts grading.

### Expected result

`check_submission.py` prints the remaining requirements or reports that the
submission is complete, and `gh student submit` reports the recorded snapshot.

### If it does not work

Commit the intended snapshot before running `gh student submit`; the course
instructions also ask you to push regularly so that work is backed up. When
the command is not found, reopen the Codespace terminal so that the course CLI
extension is on the path.

## 6. Inspect a Week 0–7 result

### Graphical path

1. Return to the assignment in Classroom50.
2. Choose **My submission**.
3. Choose **View score** when it is available.
4. Follow the repository link to the GitHub Feedback PR for the detailed
   checklist and discussion.

### CLI path

The output of `gh student submit` provides the relevant repository, result, or
feedback links. The browser and CLI views describe the same submitted snapshot.

### Expected result

**My submission** names the submitted snapshot, and **View score** shows the
completion result once the automatic check has finished.

### If it does not work

The result appears only after the check finishes, so reload the page after a
minute. When the result still refers to an older snapshot, submit again and
check that the newest commit was pushed first.

## 7. Final-project difference

The final project is an empty, non-autograded Classroom50 group assignment.
Classroom50 is used graphically to accept the assignment, manage collaborators,
and open the repository. A Classroom50 submission or **View score** page is not
the authoritative final-project hand-in record.

The authoritative project milestones are instead:

```text
proposal: exact Git commit URL posted in the group's topic issue
final:    exact Git commit URL posted in the same topic issue
```

The instructor grades the final project manually.

### Expected result

The project repository is empty until the group bootstraps the public starter,
and no automatic score, Release, or Feedback PR ever appears.

### If it does not work

When Classroom50 shows no grade for the project, nothing is wrong: the project
carries no automatic grade. Post the exact commit URL in the group's topic
issue, which is the only record the instructor grades.

## 8. Getting help

Every section above states the browser path, the command-line equivalent, the
expected result, and what to do when the result differs. When none of the
recovery instructions applies, report the assignment, the exact step, and the
message shown, so that the instructor can reproduce the problem.

Official project documentation:

- [Classroom50 Web Student Guide](https://github.com/foundation50/classroom50/wiki/Web-Student-Guide)
- [Classroom50 CLI Student Guide](https://github.com/foundation50/classroom50/wiki/CLI-Student-Guide)
