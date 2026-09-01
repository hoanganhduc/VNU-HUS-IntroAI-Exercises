# Third-party materials boundary

This public repository cites the following work but does not include or adapt
its exercise statements:

Wolfgang Ertel, *Introduction to Artificial Intelligence*, 3rd edition,
Springer, 2025, DOI
[10.1007/978-3-658-43102-0](https://doi.org/10.1007/978-3-658-43102-0).

The MIT and CC BY 4.0 grants in this repository cover only the files classified
in `PUBLIC-CONTENT.json`. They do not grant rights to the cited book, software
dependencies, container images, GitHub extensions, trademarks, or linked
external content.

The course-authored Dockerfile and image-publishing workflow are MIT-licensed
configuration. The image they build contains independently licensed Microsoft
Dev Container base layers, Ubuntu packages, SWI-Prolog, GNU Prolog, and E prover;
the repository's MIT license does not replace those licenses. The image retains
the pinned E prover corresponding source and its `COPYING` terms under
`/usr/src/eprover`.

Blank targets, generic helpers, completion checkers, and bibliographic metadata
in this repository are course-authored. A course deployment that combines them
with separately authorized third-party material is responsible for keeping that
material within its own permission boundary.
