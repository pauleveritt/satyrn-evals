# Satyrn Evals

**Turn a candidate code change into actionable evidence.**

Satyrn Evals helps an engine developer answer a practical question: *did this
attempt help, and if not, where did it fail?* It puts a real Python change in
a repeatable task, runs an attempt command, saves what happened, and grades
the saved change offline.

```text
task → attempt → saved patch + transcript → offline grade → receipt or summary
```

You do not need a model, GPU, or the project's research history to begin.
Start with a bundled change and see the result for yourself.

## See one result

Grading a bundled change records a receipt. The receipt — not the command's
exit status — is the result:

```json
{
  "task": "format_number",
  "patch_digest": "251a3d81e289f932d69bb1d93116fda757f47b9dcbdb11e9bc68aab7dd687ebc",
  "verdict": "pass",
  "reason": "",
  "evidence": {
    "executed_test_ids": ["test_solution.py::test_large", "test_solution.py::test_negative", "test_solution.py::test_small", "test_solution.py::test_zero"],
    "outcomes": {"test_solution.py::test_small": "passed", "test_solution.py::test_large": "passed", "test_solution.py::test_negative": "passed", "test_solution.py::test_zero": "passed"},
    "counts": {"passed": 4, "failed": 0, "error": 0, "skipped": 0}
  }
}
```

Reproduce it from a checkout:

```console
$ RESULT_DIR="$(mktemp -d)"
$ uv run satyrn-evals grade format_number \
    src/satyrn_evals/tasks/format_number/fixtures/known-good.patch \
    --receipt "$RESULT_DIR/receipt.json"
$ uv run python -c 'import json, sys; print(json.load(open(sys.argv[1]))["verdict"])' \
    "$RESULT_DIR/receipt.json"
pass
```

- New here? [See one verdict](tutorials/see-one-verdict.md) in a few minutes.
- Ready to use an engine? [Evaluate one attempt](guides/evaluate-an-attempt.md).

## What Evals gives you

Evals preserves a candidate patch and its transcript before it cleans up the
temporary workspace. It then grades the saved patch and writes a receipt with
the result and its test evidence. Repeated attempts produce a counts-only
diagnostic summary. That lets you inspect failures and improve the engine
without needing to rerun a model just to re-grade its work.

Read [why Evals exists](why.md) for the problem it solves, or [the evidence
lifecycle](topics/evidence-lifecycle.md) once you have seen a receipt.

## Scope, briefly

Grading is offline: it runs neither a model nor the network. An attempt
command may use a local model, but it is an executable boundary rather than an
Evals library dependency. Evals is diagnostic, not a benchmark or a claims
layer: its summaries identify outcomes and failure reasons; they do not make
confidence-interval or A/B publication claims.

An attempt runs in an Evals-owned disposable worktree, but it is **not** a
security sandbox. Read [trust boundaries and limits](topics/trust-boundaries.md)
before running an untrusted command.

## Current status

`grade`, `capture`, `attempt`, `run`, `summarize`, `regrade`, `session`, and
`census` are available. The [CLI reference](usage.md) is the complete command
surface. Current instrument work is described in the
[roadmap](https://github.com/pauleveritt/satyrn-evals/blob/main/ROADMAP.md) and [first-milestone documents](current/index.md).

```{toctree}
:maxdepth: 2
:caption: Start here

why
tutorials/index
what-actually-happens
```

```{toctree}
:maxdepth: 2
:caption: Use Evals

guides/index
```

```{toctree}
:maxdepth: 2
:caption: Understand

topics/index
```

```{toctree}
:maxdepth: 2
:caption: Reference

reference/index
```

```{toctree}
:maxdepth: 2
:caption: Development

development/index
```
