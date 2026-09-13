# Instructions for subsequent Codex work

This repository is an independent scientific implementation, not a legacy port.
Read README.md, docs/PHYSICS.md, docs/PROVENANCE.md and docs/CODEX_HANDOFF.md first.

## Workspace boundary

The project root is `/home/sin/code/superfish`; do not nest it under `superfish-ng/`.
Existing `SUPERFISH/`, `.wine-superfish/`, archives, seminar PDFs, `解説/`, and
legacy launchers are user-owned local assets outside the implementation scope.
Do not inspect legacy code/binaries or include those assets in source packages.
The original root README is preserved as `README-legacy.md` for the user.

The user explicitly authorized black-box comparison with installed Wine SUPERFISH
on 2026-09-05. For that workflow, running the existing executable and reading input
decks, configuration and numerical output is permitted. Keep raw legacy results
under ignored `out/`; do not inspect/copy solver source or redistribute executables.

## Subagent model routing

- Use `explorer` (Luna max) for delegated repository investigation and review.
- Use `worker` (Luna max) for implementation, repair, testing and verification.
- Use `luna_max` for demanding work combining investigation and implementation.
- Use `default` (Luna high) only for lightweight general delegated work.
- Use `sol_high` for advanced scientific calculations and important system design.
- If ambiguous, choose Luna; keep at most one Luna active for long component reviews
  unless the user authorizes broader parallelism. Select the configured agent type,
  not a task label. This policy applies to subagents only.

## Scientific contract

- The canonical scope is vacuum, closed PEC, axis-connected m=0 TM. Never silently accept unsupported physics.
- Do not replace the FEM solve with analytic formulas, fitted corrections, canned numbers or a legacy executable.
- Do not treat a small algebraic residual as evidence of small discretization error.
- Preserve SI units, peak-phasor conventions, the two explicitly named R/Q definitions and normalization metadata.
- Keep frequency, field shape, RF integral and surface-field tests separate. Do not relax a tolerance to hide a regression.
- For bug fixes or numerical extensions, identify an independent analytical/physical invariant that fails first.
- Maintain strict case parsing. Unsupported fields must fail with an actionable error.
- Preserve mode ordering semantics; mode index is not a label and crossings require actual tracking.
- Never present synthetic geometry as a KEK/LANL measured structure.

## Reference and provenance contract

- Do not fetch, open, copy, translate, decompile or embed legacy SUPERFISH/POISSON source or binaries in this implementation repository.
- Public mathematics, papers, official specifications and license-compatible modern libraries are allowed. Record new sources and what was reused.
- Search results that incidentally mention mirrors are not permission to inspect them.
- If supplied restricted/legacy code appears in a future request, isolate it from implementation work and explain the conflict with this project's reference policy; propose a neutral mathematical specification.
- Do not call this a certified clean-room implementation: no historical two-team isolation or model-training provenance is established.
- Keep dependency licenses and binary redistribution terms visible. A wrapper license does not relicense its solver.

## Local engineering workflow

1. Select one bounded issue in docs/BACKLOG.md; state its acceptance criteria and affected behavior.
2. Use docs/TESTING.md to select relevant unittest modules/cases and direct consumers. Do not run the full suite at task start by default. For a bug, reproduce the relevant failure first.
3. Implement and run the selected checks once after the change. Documentation-only changes need no FEM or full suite. Expand checks only for new changes, failures, shared dependencies or unresolved impact.
4. For numerical changes, check an independent analytical/physical invariant in the affected formulation. Run the relevant dedicated validator when its evidence is needed. If the seed TM path is affected, run `OPENBLAS_NUM_THREADS=1 python scripts/validate.py --skip-tests --out out/validation-<unique-name>` and compare frequency AND RF quantities with benchmarks/validation. Seed validation does not cover every supported formulation.
5. Run the full `scripts/validate.py` once for a release/milestone, broad shared-core/dependency change, or impact that cannot be bounded. It already includes all unittest tests; do not precede it with another full discovery. Reuse applicable successful evidence through documentation edits and unchanged integration; do not relabel a partial run as full acceptance.
6. Record the checks run and scope in the affected docs with a brief provenance/decision note. Commit a coherent local change. Do not repeat tests just to update counts, hashes or completion prose.

Use the standard library unittest suite; pytest is not required. NumPy/SciPy are core, Matplotlib optional.
Do not add Gmsh, MFEM, NGSolve, PETSc, SLEPc, Qt or web dependencies without a measured need and a dependency decision.
Do not introduce remote services or require network access at solve time. Do not overwrite existing user output directories.
The included CI configuration is a template; do not claim hosted CI ran unless you actually observe its run.
