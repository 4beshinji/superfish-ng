# Changelog

## Unreleased

- Add optional reflection-neutral crossed P1 triangulation, verified by periodic cell-amplitude, geometry and analytic RF invariants; preserve default meshes and v1 case hashes.
- Support radius-preserving arc reflection and seminar full/half end-cell geometry, numerical refinement and field visualization without transferring half-end phase labels.
- Complete all-mode flat4 and rounded4 Wine comparisons with independent refinement gates; retain failed intermediate reports. Rounded7 native/geometry convergence passes, Wine verification remains in progress.

- Add radius-preserving circular profiles, bounded chord approximation and independent area/convergence checks for the rounded four/seven-cell seminar examples.
- Identify the four/seven-cell band using cell fields and zero counts, fit cosine dispersion with residuals, and generate multi-mode result galleries with explicit failed gates.
- Add optional dependency-free Node/Chrome headless keyboard/graphics/link verification, including an intentionally failing gallery fixture.
- Add explicit v2 stepped profiles and conforming slab meshes with boundary/topology/area checks; solve the seminar flat-nose 4-cell example and record preliminary signed Wine comparisons, including unresolved cancellation-sensitive R/Q error.
- Add strict v2 electric/magnetic end symmetry, essential-DOF elimination, loss-free symmetry tags and explicit full-cavity field reflection; preserve v1 PEC inputs.
- Verify both half-domain pillbox parities at either end against theory, independent full FEM and signed full-domain Wine SF7; export half/full plots and RF metadata.
- Add full-domain seminar pillbox TM010/TM011 runs, field-overlap mode identification, three-level length sweeps and a local result gallery.
- Add arbitrary saved-mode plots with electric field arrows, magnetic fields and axial/radial probes.
- Use signed SF7 fields for higher-mode Wine comparisons; align voltage and power to a common energy normalization.
- Compare three fundamental-mode cases against installed SUPERFISH under Wine with independent mesh refinement and aligned RF conventions.
- Add opt-in reference runner, comparison plots, and four offline conversion tests; document the remaining corner peak-field discrepancy.
- Set the near-term milestone to calculation and visualization of the four user-supplied seminar documents' examples.
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
