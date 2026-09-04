# D1 plan: Diátaxis documentation orientation

> **Implementation plan.** The approved design is
> `2026-09-04-d1-diataxis-documentation-design.md`.

## 1. Establish the public front door

- Replace the documentation home page's phase-first opening with the promise
  that Evals turns a candidate code change into actionable evidence.
- Put a small evidence-lifecycle diagram and two next actions before status,
  vocabulary, architecture, or development history.
- Reduce README to the same terse promise, lifecycle, scope boundary, and
  links into the appropriate documentation sections.
- Check the README links from the repository root and the docs links through
  the Sphinx build.

## 2. Create a reliable first learning experience

- Add `docs/tutorials/index.md` and a `see-one-verdict.md` tutorial.
- Use the bundled `format_number` task and its known-good fixture. Start from
  `uv sync`, write a deliberately named receipt, and read its `verdict`.
- State the expected `pass` observation at every command transition. Mention
  only the vocabulary needed to carry out that step; link deeper explanation
  instead of embedding it.
- Verify the complete command sequence in a disposable directory from the
  checkout.

## 3. Split operational work from lookup

- Add goal-named `docs/guides/` pages for capturing a task, evaluating one
  attempt, and running a diagnostic batch. Each starts from the reader's
  outcome, names the safety/result boundary early, and links to the exact CLI
  details.
- Add `docs/reference/index.md`; retain `usage.md` as the complete CLI
  reference and place the glossary alongside it.
- Do not make empty section indexes: every navigation entry must lead to
  useful content.

## 4. Explain the design only after the reader has a concrete result

- Add `docs/topics/` pages for the evidence lifecycle, trust boundaries, and
  task validity versus diagnostic admission.
- Move or link architecture material to its appropriate explanatory page.
  Correct its stale V5 "not here yet" wording rather than carrying it into
  the new structure.
- Add `docs/development/index.md` as the entrance to architecture,
  contribution guidance, SDD, roadmap, and the preserved Superpowers archive.
  The archive stays published but is not positioned as primary user
  onboarding.

## 5. Wire, verify, and record

- Replace the existing two-level toctree with Start Here, Use Evals,
  Understand, Reference, and Development sections.
- Run `just lint-docs`, `uv run --group docs sphinx-build -W -b html docs
  docs/_build/html`, and `git diff --check main...HEAD`.
- Check that the finished roadmap row summarizes the delivered IA and move D1
  to Prior work without changing V6's runtime status.

## Amendment (2026-09-04): reopened for review corrections

The maintainer reopened D1 after a deep review; the design spec's amendment
records the verified findings. Correction tasks, all docs-side:

1. Add `docs/reference/formats.md` — task directory, manifest fields, receipt,
   capture record, attempt directory and record, run summary, hook result —
   as the single home for artifact formats; `usage.md` keeps flags, exit
   codes, and examples and links to it; Reference's toctree gains the page.
2. Add the concrete suite example (the `format_number` receipt) followed by
   its runnable command to the front page. While verifying it, the receipt
   example was found stale (two of four executed test IDs, `passed: 2`) and
   corrected to the recomputed output in both the front page and the formats
   reference — see the spec amendment's finding 9.
3. Guides: run `uv run satyrn-evals` from the checkout; carry `--tasks-root`
   through capture → attempt → run; correct `<TASK_NAME>.capture.json`;
   state the full refusal-code set; restate the smoke rule per V5d.
4. Architecture: add `run.py` and `summary.py` rows and `run` to the `cli.py`
   row. Glossary: `task` entry — the known-broken fixture is optional.
5. Record the amendment in the design spec; set the D1 roadmap row to active
   and note the amendment under Prior work.
6. Add a trailing-whitespace/EOF-blank-line check to `tools/lint_docs.py`
   (with sibling tests in `tests/test_doc_caps.py`); fix the EOF blank lines
   in this plan and the design spec that the missing check let through.
7. Step 5's `git diff --check` is corrected above to `git diff --check
   main...HEAD` — the unscoped check is how the EOF defects landed.

Verification: `just lint-docs`, `just docs` (strict Sphinx),
`git diff --check main...HEAD`, and a rerun of the tutorial's command
sequence from a clean checkout.
