# Glossary

This glossary is the concept budget made searchable: every term here names
something the design actually needs, and the definition is the one the
phase that needed it settled on. A term that stops naming anything real
gets removed, not kept for convenience.

```{glossary}
:sorted:

allowlist
  The `source_paths` in a task {term}`manifest`; the only paths a
  {term}`patch` may touch. Tests and the manifest stay at base, so a patch
  cannot change what the {term}`oracle` expects or add test files.

attempt command
  The executable that produces a patch for a {term}`task`; the engine seam.
  Evals never imports engine internals, and a fake command satisfies the
  same seam, so eval development never waits for the real engine. Landed in
  V3.

attempt record
  The durable artifact `attempt` (the command) writes: version, outcome
  (`attempted`/`refused`), a precise `code`, a short `message`, task,
  the command argv, the
  command's exit code (recorded, never trusted), the preserved
  patch/transcript paths and digests, the verdict, and the {term}`receipt`
  path. E3-shaped; the exit code is coarse by design. Parallel to the
  {term}`capture record`.

capture record
  The durable artifact `capture` (the command) writes: version, outcome
  (`captured`/`refused`), a precise `code`, message, repo and SHAs, task
  directory, the recorded {term}`oracle`, the {term}`discriminating set`,
  and the four checks' outcomes. E3-shaped; the exit code is coarse by
  design.

discriminating set
  The test IDs that fail at base and pass with the fix — the captured
  task's {term}`oracle` runs exactly these, and they are its expected test
  IDs. Non-empty proves the task is un-done at base; the four checks prove
  it is winnable.

provenance
  The manifest's `repo`, `base_sha`, and `fix_sha` — where a captured
  {term}`task` came from. Names what re-derivation of the environment and
  future diagnosis need.

baseline probe
  The baseline attempt command at n=4–6, recorded once as a property of
  the task, so the diagnostic loop has something to move. A task at or
  near ceiling is smoke only; a task at the floor is a capability wall.
  V1 picks its bundled task so a baseline *could* move later; the probe
  itself lands with the attempt loop (V3/V4).

diagnostic workload
  A {term}`task` used to see whether an engine change helped; it must be
  able to show a difference. Requires a {term}`baseline probe`. Not the
  same job as a {term}`grader fixture` — picking one artifact for both
  picks the wrong artifact for each.

evidence floor
  The minimum proof a grader must reach: it has accepted a known-good
  input and rejected a known-broken one, each asserted by naming the
  fixture (BRIEF rule 2).

grader fixture
  A {term}`task` that proves the grading machinery discriminates. No model
  runs, so headroom is irrelevant; it must grade offline and
  deterministically, with no network. Not the same job as a
  {term}`diagnostic workload`.

hook result
  The JSON the {term}`oracle` writes through the oracle hook — executed
  test IDs, outcomes, counts — at a path only grading knows. The only
  evidence the {term}`verdict` is computed from.

integration tier
  The marked tests that may legitimately spawn: real git, real oracle
  subprocesses. Run with `uv run pytest -m integration`; excluded from the
  default run and from CI.

manifest
  A task's `manifest.json`: name, contract, {term}`oracle` command,
  expected test IDs, source {term}`allowlist`, a known-good fixture
  {term}`patch` path, and an optional known-broken fixture patch path.

oracle
  The {term}`manifest`'s command that decides whether a {term}`patch` is
  correct. Its {term}`hook result` — never its stdout or exit code — is
  the only verdict evidence.

patch
  A unified diff the grader applies to a task's base state. Must apply
  cleanly and may only touch {term}`allowlist`ed paths.

preservation
  Persisting a patch and its transcript *before* cleanup, so grading reads
  only artifacts and a grading defect can be fixed and re-scored without
  re-running the attempt. Landed in V3; it matters more than any capture
  shape.

receipt
  The durable artifact grading produces and re-scoring reads: task, patch
  digest, {term}`verdict`, reason, and the {term}`hook result` as evidence.

task
  A bundled development task: {term}`manifest`, base state, and
  known-good / known-broken fixture patches. Selected under the
  {term}`grader fixture` rule.

tripwire
  The audit hook in the test root that raises on any subprocess spawn
  during the default tier. Weakening or removing it fails the build; the
  `integration` marker opens the gate for the {term}`integration tier`.

verdict
  `pass`, `fail`, or `unavailable`, recorded in a {term}`receipt`. Never
  read from stdout or an exit code — predecessor graders were defeated by
  `addopts = --collect-only` and an import-time `os._exit(0)`.
```
