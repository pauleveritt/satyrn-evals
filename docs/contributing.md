# Contributing

Welcome. The most useful thing to know up front: **you can contribute here
without a model server, a GPU, or any of the research history.** This is
ordinary Python with hermetic tests.

You need Git 2.36 or newer, `uv`, `ruff`, `pyrefly`, `pytest`, and
[D2](https://d2lang.com/) installed.

## Test commands

```bash
uv sync                  # install the project and the dev group
uv run pytest            # default, hermetic suite
uv run ruff check .      # lint
uv run pyrefly check     # type-check
```

`just docs` runs the same strict Sphinx build CI runs; `just watch-docs`
serves a live-rebuilding copy at http://127.0.0.1:8003.

## Repository conventions

- **Proportionate planning.** Use the current design and plan for work that
  changes an evaluation condition, evidence boundary, task contract, or result
  interpretation. Small reversible changes need no planning ceremony — see
  [`sdd.md`](sdd.md). Commit timing is maintainer-controlled.
- **Verify, don't assert.** A claim (a fix works, a test is non-vacuous, a
  refusal fires) gets demonstrated — stash the fix and show the new test
  fails first, or write the exploit and run it — not just stated.
- **Build against a concrete need.** Keep deferred work in `BACKLOG.md` and
  historical rationale in the archive.
- **A refusal test has a sibling success test**, so rejection cannot pass
  vacuously.
