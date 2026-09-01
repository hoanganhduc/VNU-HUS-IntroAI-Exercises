# VNU-HUS IntroAI Classroom50 resources

This public repository contains reusable, course-authored scaffolding and
completion-only checkers for introductory artificial-intelligence assignments.
It also contains the two Week 0 Git and GitHub practice lessons.

The chapter packages cite exercises from Wolfgang Ertel's *Introduction to
Artificial Intelligence*, 3rd edition (2025), but this repository does **not**
reproduce or adapt those exercise statements. Instructors and students must use
an authorized copy of the cited book or separately supplied course material.

## Repository layout

- [`Week 0/`](Week%200/) contains the guided Git and GitHub practice lessons.
- [`Classroom50/`](Classroom50/) contains one source package per assignment,
  the shared student guide, public completion checkers, teacher registration
  test definitions, and the validator/exporter.
- [`.devcontainer/`](.devcontainer/) pins the course environment and
  `gh-student` version used by exported templates.
- [`Dockerfile`](Dockerfile) is the canonical source for the public
  `ghcr.io/hoanganhduc/vnu-hus-introai-exercises` development image.

The two Week 0 packages are complete public assignment sources. The chapter
packages are reusable public scaffolds only: production course deployments may
add authorized statement or support files from a separate course-controlled
source.

## Validate and export

Run from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 \
python3 -I Classroom50/tools/template_tool.py validate
```

After fetching `origin/main`, export one ready package to a new directory:

```bash
git fetch origin
python3 -I Classroom50/tools/template_tool.py \
  export <slug> /absolute/path/to/new-destination
```

The exporter copies only catalogued student files and the pinned shared
environment. It never copies `classroom50-tests.json`, generated Classroom50
configuration, or an autograding workflow.

Chapter 7 remains blocked and cannot be exported.

## Automation boundary

This source repository contains three reviewed workflows: the repository-wide
Classroom50 source validator, the Week 0 solo-collaboration pull-request check,
and the manual image publisher. All use the same full-SHA-pinned GitHub checkout
action with credential persistence disabled. The public validator authenticates
the exact workflow and Dockerfile bytes before accepting the source tree.
Exported assignment templates receive neither the Dockerfile nor any
source-repository workflow.

The publisher builds a uniquely tagged candidate only from the reviewed public
`main` commit. After consumers have tested its immutable digest, a separate
manual operation promotes that same manifest to `latest` without rebuilding it.
Consumers use the immutable image digest recorded in the catalog and
devcontainer definition; they do not use the mutable `latest` tag. The resulting
image includes independently licensed base layers and software packages.
The image records its exact installed Debian-package versions at
`/usr/local/share/vnu-hus-introai/installed-packages.tsv`; the digest, rather
than the source revision alone, identifies the tested artifact.

## Completion-score boundary

Every checker in `Classroom50/` reports only whether observable submission
requirements are present:

```text
100/100  complete submission
0/100    incomplete submission
```

A passing result does not establish mathematical, logical, algorithmic, or
factual correctness.

## Reference

Wolfgang Ertel, *Introduction to Artificial Intelligence*, 3rd edition,
Springer, 2025. DOI:
[10.1007/978-3-658-43102-0](https://doi.org/10.1007/978-3-658-43102-0).

## Licensing and third-party boundary

Code and configuration are licensed under the MIT License. Original
instructional prose is licensed under Creative Commons Attribution 4.0
International. See [`LICENSE`](LICENSE) and [`LICENSES/`](LICENSES/).

No license in this repository grants rights to the cited book or other
third-party material. See
[`THIRD-PARTY-MATERIALS.md`](THIRD-PARTY-MATERIALS.md).
