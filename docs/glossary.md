# Glossary

This glossary is the concept budget made searchable: every term here names
something the design actually needs, and the definition is the one the
phase that needed it settled on. A term that stops naming anything real
gets removed, not kept for convenience.

```{glossary}
:sorted:

admission
  The V5a gate that decides whether a probed {term}`task` may join the
  suite as a {term}`diagnostic workload`: admissible when its
  {term}`baseline probe` records at least one pair of the {term}`arm`s
  under comparison in different successful-attempt {term}`band`s — the
  recorded difference is what the diagnostic loop has to move. It refuses
  {term}`smoke`, and never chooses the band metric after the result.

allowlist
  The `source_paths` in a task {term}`manifest`; the only paths a
  {term}`patch` may touch. Tests and the manifest stay at base, so a patch
  cannot change what the {term}`oracle` expects or add test files.

arm
  One engine configuration probed against a {term}`task` and compared with
  the others — for example the {term}`reference arm` (bare Pi) versus a
  product arm under comparison. Arms are read pairwise: {term}`admission`
  and diagnosis act on a recorded pair in different {term}`band`s.

attempt command
  The executable that produces a patch for a {term}`task`; the
  {term}`engine seam`. Evals never imports engine internals, and a fake
  command satisfies the same seam, so eval development never waits for the
  real engine. Landed in V3.

attempt record
  The durable artifact `attempt` (the command) writes: version, outcome
  (`attempted`/`refused`), a precise `code`, a short `message`, task,
  the command argv, the
  command's nullable exit code (recorded, never trusted), the synthetic
  workspace base, any retained cleanup path, the preserved
  patch/transcript paths and digests, the verdict, and the {term}`receipt`
  path. E3-shaped; the exit code is coarse by design. Parallel to the
  {term}`capture record`.

band
  The class of an arm's successful-attempt outcome on its probe:
  {term}`floor`, middle, or {term}`ceiling`. The successful-attempt metric
  and stopping rule are fixed before the probe runs; retained-patch
  production and conditional retained-patch quality are recorded per arm,
  never substituted for the band metric.

capability wall
  A successful-attempt {term}`floor` is a wall only when no arm under
  comparison is recorded above it *and* no retained patch passes a
  preservation-safe {term}`oracle`: nothing an engine change moves.

capture record
  The durable artifact `capture` (the command) writes: version, outcome
  (`captured`/`refused`), a precise `code`, message, repo and SHAs, task
  directory, the recorded {term}`oracle`, the {term}`discriminating set`,
  and the four checks' outcomes. E3-shaped; the exit code is coarse by
  design.

ceiling
  The high {term}`band`: all or nearly all attempts successful, so nothing
  can be recorded above it. A {term}`task` whose {term}`reference arm`
  sits here is {term}`smoke`.

cell set
  The named attempt directories (in run order) a summary's counts are
  computed over, recorded so the tally is recomputable by filter, not by
  hand. Every summary from V7 names its cell set, so reusing an output
  directory cannot make the summarized {term}`verdict` counts
  unverifiable.

completion floor
  A successful-attempt {term}`floor` whose retained patches pass a
  preservation-safe {term}`oracle`: the arm constructs the change but does
  not finish a successful attempt under its own tool loop. Not a wall — it
  is a floor an engine change exists to move, and {term}`admission`
  accepts the {term}`task` when a compared arm is recorded above it.

contamination
  On a hidden-oracle task: grader/oracle artifact content in
  executor-reachable material — overlay content in a workspace, grader
  content inside a retained patch, or overlay paths/names in
  executor-visible texts. The detector is a verbatim tripwire, not a proof
  of ignorance: it matches whole-file bytes and stable fragments, and
  deliberately passes paraphrased leaks and behavior-restating tests. Per
  graded artifact it records `flagged`, `clean`, or `unmeasured`, reading
  the artifacts {term}`preservation` guarantees exist before cleanup. It is
  a separate dimension from the {term}`verdict`: it never changes one,
  never an exit code, never a denominator.

discriminating set
  The test IDs that fail at base and pass with the fix — the captured
  task's {term}`oracle` runs exactly these, and they are its expected test
  IDs. Non-empty proves the task is un-done at base; the four checks prove
  it is winnable.

engine contract
  The optional opaque engine-owned artifact a {term}`task` ships
  (`engine_contract` in the {term}`manifest`): evals validates only its
  safe task-relative location, appends its absolute path to the
  {term}`attempt command`, and never parses its contents — the engine owns
  the format.

engine seam
  The executable boundary between evals and an engine: evals drives one
  {term}`attempt command` through reserved artifact paths and never imports
  engine internals or parses what runs behind them. A fake command occupies
  the same slot as the real engine, so eval development never waits on the
  engine.

provenance
  The manifest's `repo`, `base_sha`, and `fix_sha` — where a captured
  {term}`task` came from. Names what re-derivation of the environment and
  future diagnosis need.

baseline probe
  The baseline attempt command at n=4–6, recorded once as a property of
  the task, so the diagnostic loop has something to move. The middle-band
  bar applies to the {term}`arm`s under comparison, not to the
  {term}`reference arm` alone: a task is admissible when its probe records
  at least one pair of those arms in different successful-attempt
  {term}`band`s, with the metric fixed before the run and successful-attempt
  outcome, retained-patch production, and conditional retained-patch
  quality kept separate. (Amended by V5a, 2026-09-02; the
  prior wording — "a task at or near ceiling is smoke only; a task at the
  floor is a capability wall" — is superseded by the V5a design spec.)
  V4 provides the real attempt; baseline-probe admission belongs to V5.

diagnostic loop
  The V5b phase that runs an admitted {term}`task`'s {term}`attempt command`
  n times and writes a counts-only summary — the consumer {term}`admission`
  feeds. Arm comparison and any confidence claim are the claims layer, not
  this loop.

diagnostic workload
  A {term}`task` used to see whether an engine change helped; it must be
  able to show a difference between the {term}`arm`s under
  comparison. Requires a {term}`baseline probe`. Not the same job as a
  {term}`grader fixture` —
  picking one artifact for both picks the wrong artifact for each.

evidence floor
  The minimum proof a grader must reach: it has accepted a known-good
  input and rejected a known-broken one, each asserted by naming the
  fixture (BRIEF rule 2).

floor
  The low {term}`band`: zero or near-zero successful attempts recorded, so
  the arm alone moved nothing. A per-arm result, never a verdict on the
  {term}`task` by itself: a {term}`completion floor` when retained patches
  pass a preservation-safe {term}`oracle`, and a {term}`capability wall`
  only when no compared arm sits above it.

grader fixture
  A {term}`task` that proves the grading machinery discriminates. No model
  runs, so headroom is irrelevant; it must grade offline and
  deterministically, with no network. Not the same job as a
  {term}`diagnostic workload`.

hidden oracle
  A {term}`task` whose {term}`oracle` content lives only in the
  `grader_overlay`, outside `base/`, materialized only into a fresh grader
  workspace after the patch applies and before the oracle runs
  (`oracle_visibility: "hidden"`). The V6 session mechanics, now declared.
  The ⇔ rule ties the field to the overlay: `hidden` requires a
  `grader_overlay`; a `grader_overlay` requires `hidden`.

hook result
  The JSON the {term}`oracle` writes through the oracle hook — executed
  test IDs, outcomes, counts — at a path only grading knows. The only
  evidence the {term}`verdict` is computed from.

integration tier
  The marked tests that may legitimately spawn: real git, real oracle
  subprocesses, process groups, and a real engine through the
  {term}`engine seam`. Run with
  `uv run pytest -m integration`; excluded from the default run and from CI.

manifest
  A task's `manifest.json`: name, contract, {term}`oracle` command,
  expected test IDs, source {term}`allowlist`, a known-good fixture
  {term}`patch` path, an optional known-broken fixture patch path, and an
  optional opaque {term}`engine contract` path.

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

reference arm
  The bare-Pi arm, recorded once as a property of the task by the
  {term}`baseline probe`. It is the arm the diagnostic loop moves *from*;
  its {term}`band` never admits or refuses on its own — a floor reference
  can be a {term}`completion floor` a compared arm moves, and a ceiling
  reference refuses only because nothing can be recorded above it.

smoke
  A probed {term}`task` whose {term}`reference arm` sits at or near
  {term}`ceiling`: nothing for an engine change to move, so
  {term}`admission` refuses it.

task
  A bundled development task: {term}`manifest`, base state, and a known-good
  fixture patch — a known-broken fixture patch when the task ships one.
  Selected under the {term}`grader fixture` rule.

tripwire
  The audit hook in the test root that raises on any subprocess spawn
  during the default tier. Weakening or removing it fails the build; the
  `integration` marker opens the gate for the {term}`integration tier`.

unmeasured
  The recorded outcome when a check cannot run over all its required
  inputs — retained patch bytes missing, a session step with no retained
  payload events, a pre-V7 {term}`receipt`. Absence of signal is not
  cleanliness: `unmeasured` is never folded into `clean` and never
  reported as zero, and overall `clean` requires every applicable check
  clean.

verdict
  `pass`, `fail`, or `unavailable`, recorded in a {term}`receipt`. Never
  read from stdout or an exit code — predecessor graders were defeated by
  `addopts = --collect-only` and an import-time `os._exit(0)`.

visible oracle
  A {term}`task` whose {term}`oracle` content lives in `base/` and may be
  read or run by the executor. The default — `oracle_visibility` absent or
  `"visible"` — is the normal TDD-style task. Contrast
  {term}`hidden oracle`.
```
