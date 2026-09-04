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

`grade`, `capture`, `attempt`, and `run` are available. V6 session evaluation
is proposed, not yet an operational interface. The
[roadmap](https://github.com/pauleveritt/satyrn-evals/blob/main/ROADMAP.md)
has the complete phase history and current design work.

```{toctree}
:maxdepth: 2
:caption: Start here

why
tutorials/index
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
