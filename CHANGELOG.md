# Changelog

## Unreleased

- Establish `/home/sin/code/superfish` as the development root with a dedicated Python 3.12 environment.
- Restrict ZIP packaging to explicit project paths and reject file/directory symlinks before reading them.
- Add packaging regression tests; exclude pre-existing workspace assets and preserve the seed evidence.
- Document local verification and development commands in `docs/LOCAL_DEVELOPMENT.md`.

## 0.1.0 — 2026-09-05

- New independent axisymmetric m=0 TM FEM solver, vacuum closed PEC cavities.
- Pillbox and piecewise-linear outer-radius profiles with structured triangular mesh.
- Generalized eigenmodes, RF postprocessing, explicit phasor and R/Q conventions.
- CLI, JSON/CSV/NPZ/VTK output, optional field plotting.
- Analytical and invariant tests, reproducible validation runner and benchmark evidence.
- Japanese research/design/roadmap/reference documents and Codex handoff instructions.
- Apache-2.0 project license; no legacy source/binary or external reference dataset bundled.

This is a research seed, not a complete or validated SUPERFISH-compatible release.
