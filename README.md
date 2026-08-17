# Satyrn Evals

**Captures a Python-development task, invokes an attempt command, preserves
what happened, and grades the result offline.**

Evals is the diagnostic loop of the two-repo satyrn effort. It owns:

- task capture and task manifests;
- known-good and known-broken fixtures;
- patch application, oracle execution, and grading;
- transcript, patch, receipt, and conditions recording;
- summaries of failure reasons and thrashing behavior.

It does **not** import engine internals. Its engine seam is an executable
attempt command run inside an eval-owned disposable worktree — the command
receives the contract path as its final argument and needs no eval-specific
SDK. A fake command satisfies the same seam, so eval development never
waits for the real engine.

## Status

Each episode below is a git tag — learners can check out a tag and follow
along step by step.

- [_E1_](https://github.com/pauleveritt/satyrn-evals/tree/e1) — project
  scaffolded and grounded: toolchain, docs stack, CI, the brief, the
  roadmap, and the harvest index, with V1 as the current phase.
  ([_spec_](https://github.com/pauleveritt/satyrn-evals/blob/main/docs/superpowers/specs/2026-08-16-v1-grade-design.md),
  [_plan_](https://github.com/pauleveritt/satyrn-evals/blob/main/docs/superpowers/plans/2026-08-16-v1-grade.md))

V1 is implemented: `satyrn-evals grade TASK PATCH [--receipt PATH]` applies
a patch to a bundled task and records an offline verdict receipt — no
model, no network. The roadmap of feature cycles is in
[`ROADMAP.md`](ROADMAP.md).

## Toolchain

This repository presumes `uv`, `ruff`, `pyrefly`, and `pytest`:

```bash
uv sync                # install the project and the dev group
uv run pytest          # default, hermetic test suite
uv run ruff check .    # lint
uv run pyrefly check   # type-check
```

Docs are Sphinx with MyST and Furo. `just docs` runs the same strict build
CI runs; `just watch-docs` serves a live-rebuilding copy at
http://127.0.0.1:8000.
