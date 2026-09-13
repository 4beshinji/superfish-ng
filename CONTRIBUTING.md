# Contributing

Start with AGENTS.md and docs/PHYSICS.md. Open a small change with a concrete physical or usability objective.
For a numerical change, include a reproducible case, an independent expected behavior, and measured error/convergence.
Do not claim external validation from self-consistency alone.

Select checks using [docs/TESTING.md](docs/TESTING.md). Run affected tests and their
direct consumers during development; documentation-only changes need no FEM run.
Do not run all unittest tests at task start or immediately before validate.py,
which already includes them. Use validate.py --skip-tests when only seed numerical
evidence is needed. Reserve a full run for milestones, broad shared changes or
impact that cannot be bounded, and state the scope actually checked.

All contributions must be compatible with Apache-2.0 and disclose third-party code/data provenance.
Do not contribute legacy SUPERFISH code, binaries, copied manual text or undocumented benchmark decks.
AI-assisted changes must be reviewed for scientific meaning, origin and tests; AI authorship is not a correctness certificate.
Check your ability to contribute under any applicable employment or institutional arrangements.

Use small local commits, readable Python, SI units and explicit result names. Keep core dependencies minimal.
For reference data, use the provenance template in docs/PROVENANCE.md. Cite publications you actually used.
Report regressions with case.json, software/dependency versions, expected/observed results and convergence settings.
