# Classroom50 assignment source packages

This directory is a public source and export factory for course-authored
Classroom50 scaffolding. Each package is exported to the root of a dedicated
template repository; this monorepo itself is not registered as one assignment.

The chapter packages contain citations, response scaffolds, blank solution
targets, and completion-only checkers. They intentionally contain no copied or
adapted exercise statement, statement PDF, or statement TeX source. Use an
authorized copy of the cited work or separately supplied course material.

[`catalog.json`](catalog.json) is the machine-readable source of truth for
package readiness, file inventories, bibliographic references, reusable
Classroom50 settings, and the pinned environment. It contains no classroom
identifier, roster, date, or secret.

Start with the shared
[Classroom50 graphical and command-line guide](shared/CLASSROOM50-WEB-UI.md).

## Package index

| Slug | Reference | Public-source status |
|---|---|---|
| `w00-individual-onboarding` | Course-authored Week 0A | Ready; complete public source |
| `w00-group-collaboration` | Course-authored Week 0B | Ready; complete public source |
| `ch01-introduction` | Ertel (2025), Exercise 1.1, p. 23 | Ready reusable scaffold |
| `ch02-propositional-logic` | Ertel (2025), Exercise 2.5, p. 39 | Ready reusable scaffold |
| `ch03-first-order-logic` | Ertel (2025), Exercise 3.9, p. 66 | Ready reusable scaffold |
| `ch04-limitations-of-logic` | Ertel (2025), p. 75; course numbering correction 4.3 | Ready reusable scaffold |
| `ch05-prolog` | Ertel (2025), Exercises 5.2, 5.3, 5.5, 5.8, pp. 90–91 | Ready reusable scaffold |
| `ch06-search` | Ertel (2025), Exercises 6.6 and 6.12, pp. 125–126 | Ready reusable scaffold |
| `ch07-uncertainty` | Ertel (2025), Exercises 7.9 and 7.10 | Blocked |

Chapter 7 is retained only as an inert placeholder. The exporter refuses it.

The Week 0 group assignment accepts one to five actual members. A singleton
tests the branch–pull-request–merge mechanics; it does not prove peer
collaboration or independent review.

## Validate

```bash
PYTHONDONTWRITEBYTECODE=1 \
python3 -I Classroom50/tools/template_tool.py validate
```

Validation checks the catalog schema, bibliographic records, package
inventories, trusted checker digests, guide copies, pinned environment,
repository-wide public-content manifest, license classification, and prohibited
content boundary.

## Export

```bash
git fetch origin
python3 -I Classroom50/tools/template_tool.py \
  export <slug> /absolute/path/to/new-destination
```

Export requires:

- the canonical public `origin` and its immutable GitHub repository ID;
- checked-out `main`;
- `HEAD == origin/main`;
- committed, byte-identical validated inputs; and
- a new destination outside this source repository.

The output is deterministic. Its README and `SOURCE-INVENTORY.md` record the
source repository ID, source commit, source tree, and source slug.

`classroom50-tests.json` is a teacher-side registration input. It is public
for review but is not copied into a student template. Each definition
authenticates the exact public checker bytes before running them.

## Reusable Classroom50 settings

Ready packages use a tagged-commit submission, a Feedback PR, and a
100-point completion threshold. All are individual except Week 0B, which is
group mode with maximum size five. Classroom identifiers, dates, and deployment
repository names are deliberately configured outside this public catalog.

## Completion-only checks

```text
100/100  complete submission
0/100    incomplete submission
```

The checkers do not assess academic correctness.
