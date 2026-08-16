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

V1 — It installs and grades — is implemented: `satyrn-evals grade TASK
PATCH [--receipt PATH]` applies a patch to a bundled task
(`format_number`) and records an offline verdict receipt — no model, no
network. The roadmap of feature cycles is in [`ROADMAP.md`](ROADMAP.md);
the design and implementation record is under `docs/superpowers/`.

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
