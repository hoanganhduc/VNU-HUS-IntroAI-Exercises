# Week 0 - Git, GitHub, and collaboration practice

These lessons prepare you to work in the exercise repository before the AI implementation assignments begin. They are written as guided practice rather than as a list of unexplained commands.

Each module follows the same cycle:

```text
Explain → Predict → Perform → Observe → Check → Repair
```

## Before you begin

1. Create **your own private repository** from the `VNU-HUS-IntroAI-Exercises` template. Use a public repository only when the instructor explicitly asks for one.
2. Open your repository in a GitHub Codespace or clone it locally.
3. Perform every command in your own repository. Do not try to push practice changes to the canonical `hoanganhduc/VNU-HUS-IntroAI-Exercises` repository.
4. Verify the basic tools:

   ```bash
   git --version
   gh --version
   python3 --version
   gh auth status
   ```

The Codespace configuration installs GitHub CLI and pins the course's `gh-student` extension release (`v1.40.0`). Local users must install GitHub CLI, then run `gh extension install foundation50/gh-student --pin v1.40.0` and authenticate it themselves.

Never commit passwords, tokens, private keys, browser cookies, university student IDs, legal names, or other unnecessary personal data. Use only the GitHub username requested by the practice files.

## Lessons

### 1. [Personal Git Practice](Personal%20Git%20Practice/)

Learn and practise:

- Git, GitHub, Codespaces, and the Classroom50 web and CLI interfaces;
- repository, working tree, staging area, commit, branch, and remote;
- `git status`, `git diff`, `git add`, `git commit`, `git push`, and `git pull`;
- public checks, deliberate failure, repair, and safe restoration;
- inspection of repository history and the pushed result on GitHub.

Complete this lesson first.

### 2. [Solo Collaboration Practice](Solo%20Collaboration%20Practice/)

Use one GitHub account to practise the mechanics of:

- issues and assignees;
- feature branches;
- draft pull requests;
- automated pull-request checks;
- review comments and corrective commits;
- merge commits and branch synchronization;
- a controlled merge conflict.

This is a **one-person-group simulation**, not real peer collaboration. One account cannot reproduce collaborator permissions, an independent reviewer, or a shared group score. A pull-request author also cannot approve their own pull request. The Classroom50 group-onboarding assignment accepts one to five members: a one-person group repeats the tool workflow, while a multi-person group additionally practises real invitations and peer review.

## Relationship to Classroom50 Week 0

The repository-native lessons let you repeat the mechanics safely in your own template-derived repository. The Classroom50 onboarding assignments add the course submission and feedback workflow:

- accepting a Classroom50 assignment;
- submitting the current assignment snapshot through the course-specified Classroom50 command;
- reading a scored Release and the Classroom50 Feedback PR;
- receiving automatic feedback and resubmitting;
- when the assigned group has several members, joining one shared repository, receiving an independent peer review, and sharing one result.

The canonical simple Classroom50 starter templates are available under [`../Classroom50/`](../Classroom50/). The shared [illustrated Classroom50 web and CLI guide](../Classroom50/shared/CLASSROOM50-WEB-UI.md) explains assignment acceptance, collaborator management, submission, and feedback.

## Submission-model warning

The course pins Classroom50 CLI v1.40.0. Its Week 0–7 assignments use tagged-commit mode: an ordinary `git push` saves work, while `gh student submit` pushes the submission tag that starts grading. Follow the exact assignment README because another course or assignment may use a different mode.
