# Satyrn Evals

**Turn a candidate code change into actionable evidence.**

Satyrn Evals helps an engine developer answer: *did this attempt help, and if
not, where did it fail?* It turns a real Python change into a repeatable task,
runs an attempt command, saves the patch and transcript it produced, and
grades that saved change offline.

```text
task → attempt → saved patch + transcript → offline grade → receipt or summary
```

The resulting receipt or diagnostic summary records what happened so an engine
can be improved from evidence, rather than from a plausible-looking patch or a
process exit status.

## Start here

From a checkout, see a bundled known-good patch earn a `pass` receipt in a few
minutes—no model, GPU, or research-history reading required:

```console
$ uv sync
$ RESULT_DIR="$(mktemp -d)"
$ uv run satyrn-evals grade format_number \
    src/satyrn_evals/tasks/format_number/fixtures/known-good.patch \
    --receipt "$RESULT_DIR/receipt.json"
```

Continue with the [See one verdict tutorial](docs/tutorials/see-one-verdict.md)
to read the receipt's `pass` verdict.

## What it does—and does not do

Evals captures tasks, invokes an executable attempt command, preserves its
artifacts, grades a patch through the task's oracle, and records diagnostic
counts across repeated attempts.

It is not an engine: its boundary is an executable command, never an import of
engine internals. It is not a benchmark or statistical claims system either.
Grading runs no model or network; an attempt command may use a local model.
The summaries diagnose outcomes and failure reasons, but do not claim
confidence intervals or publish A/B results.

An attempt runs in an Evals-owned disposable worktree. That is not a security
sandbox: the command runs with the user's permissions.

## Documentation

- [Why Satyrn Evals](docs/why.md) — the problem and the scope boundary.
- [Use Evals](docs/guides/index.md) — capture a task, evaluate an attempt, or
  run a diagnostic batch.
- [Understand the evidence lifecycle](docs/topics/evidence-lifecycle.md) —
  why Evals preserves artifacts and how it judges them.
- [CLI reference](docs/usage.md) — complete commands, flags, records, and exit
  codes.
- [Development](docs/development/index.md) — architecture, contribution
  guidance, the roadmap, and preserved design history.

## Task visibility and contamination

Each task manifest declares `oracle_visibility` — `visible` (the default;
absent means visible) or `hidden`. A visible task's oracle content lives in
`base/` and may be read or run by the executor. A hidden task's oracle lives
only in the bundled `grader_overlay`, outside `base/`, materialized only into
a fresh grader workspace after the patch applies and before the oracle runs;
the bundled `session-mechanics` task is hidden. The field and the overlay are
two views of one declaration, enforced symmetrically: `hidden` requires a
`grader_overlay`, and a `grader_overlay` requires `hidden` — a manifest
violating either direction is a usage error. `local-pings` stays visible: its
preservation oracle lives in `base/` by V5c design.

Contamination is grader/oracle artifact content reaching executor-visible
material on a hidden task. It is detected by content — a pure, verbatim
tripwire over whole-file bytes and stable fragments, with evidence pointers —
never by "a test file appeared". A hidden task's receipt carries an additive
`contamination` block recording one outcome per graded artifact: `flagged`
(the tripwire matched), `clean` (every applicable check ran over all its
inputs and matched nothing), or `unmeasured` (a required input was absent or
unparseable — recorded, never folded into `clean`, never reported as zero).
Detection is a separate dimension: it never changes a verdict and never
changes an exit code. A visible task's receipt has no `contamination` key.

An ordinary (non-session) hidden attempt preserves only its patch and
transcript, so its `clean` is evidence over the preserved patch and the
workspace-absence invariant only — not a claim about the engine transcript.

Every summary names the exact cell set it was computed over and its
`oracle_visibility`; a hidden-task summary carries a `contamination` section
beside the existing counts with the invariant
`flagged + clean + unmeasured == graded`. Detection outcomes leave every
existing count (`n`, `attempted`, `refused`, `code_counts`,
`verdict_counts`, `timeouts`) and every denominator alone.

None of this adds a CLI flag: visibility rides in the manifest, and
contamination is reported on receipts and summaries, never on an exit code.

## Status

`grade`, `capture`, `attempt`, and `run` are available. V6 session evaluation
is proposed. See [ROADMAP.md](ROADMAP.md) for phases and current design work.

## Development

```bash
uv sync
uv run pytest
uv run ruff check .
uv run pyrefly check
just docs
```

The default test suite is hermetic: no model, network, or subprocess. Real Git,
oracle, and engine behavior live in a marked integration tier. See
[Contributing](docs/contributing.md) for details.

## License

Apache-2.0 — see [LICENSE](LICENSE).
