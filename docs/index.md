# Satyrn Evals

**Captures a Python-development task, invokes an attempt command, preserves
what happened, and grades the result offline.**

Evals is the diagnostic loop of the two-repo satyrn effort: {term}`task`
capture and task manifests, known-good and known-broken fixtures,
{term}`patch` application, {term}`oracle` execution and grading, and
transcripts of what an attempt did — regradable offline without another
model call.

Its only seam into the engine is an executable {term}`attempt command`,
run inside an eval-owned disposable worktree with the contract path as
its final argument. Evals does not import engine internals, and a fake
command satisfies the same seam so eval development never waits for the
real engine.

V1 — *It installs and grades* — is implemented: `satyrn-evals grade`
applies a {term}`patch` to a bundled {term}`task` and records an offline
{term}`verdict` {term}`receipt`.
See [usage](usage.md), [architecture](architecture.md), and the
[glossary](glossary.md). The roadmap of feature cycles lives in
`ROADMAP.md`; the design and implementation record is under
[`superpowers/`](superpowers/index.md).

```{toctree}
:maxdepth: 1
:caption: User guide

usage
architecture
glossary
```

```{toctree}
:maxdepth: 1
:caption: Development

contributing
sdd
superpowers/index
```
