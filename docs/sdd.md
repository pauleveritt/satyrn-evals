# Current work practice

Start from `AGENTS.md`, `BRIEF.md`, `ROADMAP.md`, and the active design and
plan when named there. Keep designs proportionate: a small, reversible change
does not need a new planning ceremony; work that changes an evaluation
condition, evidence boundary, task contract, or interpretation needs an
explicit, reviewable decision before a budgeted run.

Use retained evidence before requesting inference. Verify claims with commands
and fixtures that distinguish success from failure. Keep default-tier checks
hermetic and use marked integration checks for real execution paths. The
maintainer controls commits.

`just lint-docs` keeps active planning documents bounded and checks whitespace.
History belongs in `archive/`, outside the Sphinx source tree and default text
search. It remains retrievable when a concrete claim needs its original
evidence.
