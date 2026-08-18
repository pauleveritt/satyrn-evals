# Satyrn Evals

**Captures a Python-development task, invokes an attempt command, preserves
what happened, and grades the result offline.**

Satyrn is a two-repo effort: a developer's own AI partner works on their
machine, in their repo, at their pace — and the engine delivers the change
it produces as something they review and own. Evals is the measurement half
of that effort. A contributor asks *"did my engine fix help, and if not,
why"*; evals answers with what broke and where — not a confidence interval.

Evals exists because small models — the ones that fit on your own machine —
fail in predictable ways: they lose their place, edit the wrong file, drift
from the task. Evals makes those failures observable. It captures a real
Python-development workflow as a suite of tasks, runs an attempt command
against each, and grades what happened offline — and the failure reasons
and thrashing it summarizes are the evidence engine fixes are built on. The
features built into the engine are the ones that evidence surfaces.

Despite the name, it is not a benchmark: grading runs no model and no
network, and the summary is diagnostic, not statistical — the claims layer
(pre-registration, confidence intervals, A/B publication) is deferred until
a consumer needs it. And evals is not an engine: it never imports engine
internals. Its seam is an executable attempt command — a fake command in
V3, `satyrn-engine attempt` itself in V4, the same slot — so eval
development never waits for the real engine.

> More: [architecture](docs/architecture.md) ·
> [glossary](docs/glossary.md)

## What it owns — and doesn't

Evals owns:

- task capture and task manifests;
- known-good and known-broken fixtures;
- patch application, oracle execution, and grading;
- transcript, patch, receipt, and conditions recording;
- summaries of failure reasons and thrashing behavior.

It does **not** own the engine: it never imports engine internals — the
engine enters only as the attempt command, a subprocess through the seam,
never a library. It does not yet own the claims layer either:
pre-registration, confidence intervals, condition enforcement, A/B
publication machinery — deferred until a consumer needs them. That split is
deliberate: evals runs the measurements, and the features built into the
engine are the ones that evidence surfaces — no machinery ahead of its
contract.

> More: [glossary](docs/glossary.md) — the terms used here (`task`,
> `manifest`, `oracle`, `verdict`, …), defined in this repository's own
> words.

## The diagnostic loop

Evals builds the engine one loop at a time:

1. **Capture** — a real Python-development workflow becomes a task:
   manifest, base state, known-good and known-broken fixture patches. V2's
   `capture --revert SHA` makes a task winnable by construction, in minutes.
2. **Attempt** — the task's attempt command runs in an eval-owned
   disposable worktree; its patch and transcript are preserved before
   cleanup. V3 runs a fake command through the seam; V4 runs
   `satyrn-engine attempt` in the same slot.
3. **Grade** — grading reads only the preserved artifacts and records an
   offline verdict — no model, no network. V1, done.
4. **Diagnose** — a run of n=8 plus a summary: verdict reasons, repeated
   calls, churn, tool calls, context, timeouts. V5.
5. **Fix and re-measure** — the summary names what broke and where; the
   engine gets fixed; the suite re-runs. Each task carries a baseline probe
   — its baseline attempt at n=4–6, recorded once — so a later run shows
   whether the fix moved it. Summaries use counts; they never compare
   wall-clock time between adjacent runs.

## Usage

From a checkout, `uv sync` installs evals into the project environment.
The CLI ships two commands:

```console
$ uv run satyrn-evals grade format_number src/satyrn_evals/tasks/format_number/fixtures/known-good.patch
$ uv run satyrn-evals capture --revert <sha> --repo /src/app --output tasks
```

Grading is silent over the CLI; the verdict — `pass`, `fail`, or
`unavailable` — is written to a receipt, never read from stdout or an exit
code. Exit code `0` means the operation completed, `2` a usage error, `3`
an operational failure that names its cause. No model calls, no network,
on every path. `capture` writes a task directory plus a capture record;
the source repository's working tree, index, branch, and `HEAD` are never
touched.

> More: [usage](docs/usage.md) — the receipt format, the exit-code table,
> the capture record, and the bundled task.

## Status

Phases completed, each with its design spec and implementation plan:

- [_V2_](https://github.com/pauleveritt/satyrn-evals/tree/v2) — capture by
  revert. `satyrn-evals capture --revert SHA` turns a fixing commit into a
  task winnable by construction, in minutes, without touching the source
  repository's working tree.
  ([_spec_](https://github.com/pauleveritt/satyrn-evals/blob/main/docs/superpowers/specs/2026-08-18-v2-capture-by-revert-design.md),
  [_plan_](https://github.com/pauleveritt/satyrn-evals/blob/main/docs/superpowers/plans/2026-08-18-v2-capture-by-revert.md))
- [_V1_](https://github.com/pauleveritt/satyrn-evals/tree/v1) — it
  installs and grades. `satyrn-evals grade TASK PATCH [--receipt PATH]`
  accepts a bundled task's known-good patch and rejects its known-broken
  one, offline and deterministic.
  ([_spec_](https://github.com/pauleveritt/satyrn-evals/blob/main/docs/superpowers/specs/2026-08-16-v1-grade-design.md),
  [_plan_](https://github.com/pauleveritt/satyrn-evals/blob/main/docs/superpowers/plans/2026-08-16-v1-grade.md))

The current phase is **V3 — Attempt persistence**; the roadmap of feature
cycles lives in [`ROADMAP.md`](ROADMAP.md). The `e1` git tag holds the
scaffolded starting state — toolchain, docs stack, CI, the brief, the
roadmap, and the harvest index — for learners following along step by
step.

> More: [architecture](docs/architecture.md) — why the verdict comes from a
> hook file, and the two test tiers.

## Development

This repository presumes `uv`, `ruff`, `pyrefly`, and `pytest`:

```bash
uv sync                # install the project and the dev group
uv run pytest          # default, hermetic suite: no model, no network, no subprocess
uv run ruff check .    # lint
uv run pyrefly check   # type-check
```

Hermeticity is enforced, not promised: a tripwire audit hook in the test
root raises on any subprocess spawn, and real Git, environment
materialization, and oracle execution live in a marked integration tier
(`uv run pytest -m integration`) that does not run in CI.

Docs are Sphinx with MyST and Furo. `just docs` runs the same strict build
CI runs; `just watch-docs` serves a live-rebuilding copy at
http://127.0.0.1:8003.

> More: [contributing](docs/contributing.md) — the integration tier, the
> tripwire, and the repository conventions.

## License

Apache-2.0 — see [LICENSE](LICENSE).
