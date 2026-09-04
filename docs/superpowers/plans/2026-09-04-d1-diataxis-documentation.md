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
  docs/_build/html`, and `git diff --check`.
- Check that the finished roadmap row summarizes the delivered IA and move D1
  to Prior work without changing V6's runtime status.

