# Satyrn Evals

**Captures a Python-development task, invokes an attempt command, preserves
what happened, and grades the result offline.**

Evals is the diagnostic loop of the two-repo satyrn effort: task capture
and task manifests, known-good and known-broken fixtures, patch
application, oracle execution and grading, and transcripts of what an
attempt did — regradable offline without another model call.

Its only seam into the engine is an executable attempt command, run inside
an eval-owned disposable worktree with the contract path as its final
argument. Evals does not import engine internals, and a fake command
satisfies the same seam so eval development never waits for the real
engine.

This repository is scaffolding: the roadmap of feature cycles derived from
the two-repo rewrite brief is not yet written. See `ROADMAP.md` in this
checkout for the current state.

```{toctree}
:maxdepth: 1
:caption: Development

contributing
sdd
superpowers/index
```
