# V6 — Session eval: delta design spec

**Date:** 2026-09-03.
**Status:** design approved in brainstorm; implementation plan follows
maintainer review of this file.

## Relationship to the design of record

The session mechanics are designed, reviewed, and recorded in
[`2026-09-01-svcs-session-eval-design.md`](2026-09-01-svcs-session-eval-design.md),
imported verbatim from PR #17 under a superseded banner. Its normative
content is unchanged by this phase: the adapter protocol (versioned
JSONL, one conversation identity, terminal-message rules), the checkpoint
lifecycle, the `session.json` schema and loader refusal rules, the
grader-overlay mechanics, the feature-versus-preservation grader split,
the artifacts and record, the exit codes, and the qualification rule any
future curated session task must pass. That file's banner promises: "The
V6 phase document states only what changed and why." This file is that
document; it records deltas only.

## Delta 1 — slice 5 replaced: the workload is decoupled from the machinery

The 2026-09-01 spec's fifth slice — "the locally materialized `svcs`
task, Pi adapter, integration evidence, and user documentation" — is
replaced with:

> A small bundled session fixture proves the shipped Pi adapter through
> the real executable seam. The fixture validates mechanics only; it
> provides no admission or model-quality claim. svcs materialization and
> qualification reopen in a separate proposal after its probe record is
> restored to main.

Why: the machinery (slices 1–4) is fully provable with a deterministic
fake adapter and needs no workload curation. The svcs probe record was
branch-local until Delta 5 imports it. Curating a large upstream
repository is workload-qualification work, not a machinery proof, and
`capture --revert` cannot construct the multi-prompt hidden overlay
without extension (2026-09-01 spec, CLI section). The recorded svcs
baseline sits at a capability wall — deepest milestone 1, 0, 0, 0 of five
(`2026-09-02-v5a-admission-rule-design.md:270-276`) — which qualifies it
for nothing in V6 and would prove the machinery no better than the
fixture does. svcs's admission question stays governed by the V5a rule
and is not decided in V6.

## Delta 2 — the session fixture is a grader fixture

`src/satyrn_evals/tasks/session-mechanics/` (name provisional), beside
`format_number` and `local-pings`:

- `base/`: a tiny pure-Python `textkit` package with existing functions
  and **public tests in `base/tests/`**, pytest, `pyproject.toml` with
  `pythonpath = ["src"]` — the V5c correction for uninstalled tree
  copies. Committed with the BACKLOG's `.gitignore`-filtering check in
  mind.
- `session.json`: **3 feature steps + 1 review step** (add `slugify`,
  add `truncate`, add `pluralize`, then review-and-run-the-public-suite).
  Three feature steps exercise the cumulative-selection union across
  more than one prefix; the review step exercises its
  does-not-raise-the-milestone path. Loader refusals per the 2026-09-01
  rejection list, each with a valid-load sibling.
- `grader/overlay/`: one hidden test module per milestone, selectors
  cumulative by construction; `base_preservation_selectors: ["tests"]`.
  The separate feature and preservation grader workspaces (2026-09-01
  spec) keep the overlay out of preservation grading.
- `manifest.json` gains `grader_overlay` per the 2026-09-01 spec. The
  fixture carries **no `engine_contract`**: its adapter protocol does
  not need one, and the fixture avoids creating a second instance of
  the already-fired contract-validation trigger — the re-probe's engine
  arm was the first real engine run on a captured task, so the fuller
  fix is owed per `BACKLOG.md`, with V5d's smoke as the interim
  mitigation.

**Classification, per the two selection rules.** This is a *grader
fixture*: offline and deterministic — no model, no network — with the
oracle's pytest the same established bundled-task pattern as
`format_number` and `local-pings`. It proves the grading machinery
discriminates — accepting
a known-good and rejecting a known-broken, each asserted by naming the
fixture:

- `fixtures/known-good.patch` — the complete three-function patch;
  accepted: every cumulative feature selection and base preservation
  pass.
- `fixtures/known-broken.patch` — milestone-1-only; preserves base,
  **fails** the cumulative selections of milestones 2–3.

It makes no diagnostic-workload claim: no baseline probe, no admission,
no arm comparison. The scripted refusal scenarios have required success
siblings (refusal tests never stand alone):

- **Scope violation:** a fake-adapter scenario that writes outside
  `source_paths` — the checkpoint is retained as evidence,
  `scope_valid=false`, hidden grading is skipped for that checkpoint,
  and the record fails; sibling: the scope-clean session.
- **Conversation-identity violation:** a scripted adapter that changes
  identity mid-session — protocol failure, sequence stopped; sibling:
  the identity-clean session.

## Delta 3 — the proof ladder: two layers, no third thing

### Layer (a) — deterministic Pi-adapter integration (CI-marked integration tier)

The `session` machinery starts the shipped adapter executable exactly as
a real run would; behind it, **Pi is replaced by a deterministic
scripted RPC fixture** — the same substitution as V4's E5 proof ("Only
Pi is replaced by a deterministic fixture", `docs/sdd.md`, V4
verification record). The integration drives **all four prompts** —
two prove identity persistence, all four cheaply prove the cumulative
behaviors — and asserts:

- one conversation identity held across all four prompts;
- event-kind mapping with the complete original Pi event retained in
  `payload`;
- any compaction event recorded;
- **cumulative union**: checkpoint *n*'s feature selection is the union
  of hidden selectors introduced through that step;
- **review-does-not-advance**: the final feature milestone is unchanged
  by the review step;
- the full checkpoint lifecycle (snapshot, cumulative patch from the
  exact base, digest, durable step record) and teardown.

Zero model. This layer is called **adapter integration** and makes no
real-model claim.

### Layer (b) — the real-model smoke, an explicit done-when item

V5d's confirmed practice governs scoping and reading
(`2026-09-03-v5d-preflight-smoke-check-design.md`, landed on main
2026-09-03); this section states only the session-specific assertions.

- **Scoping is per materially distinct execution path**, not per task:
  the shipped session adapter driving real Pi is one path, smoked once,
  uncounted, at its first real use. A future Engine-backed session
  adapter, or any materially different runtime, is a new path owing its
  own smoke. A path that already carries a budgeted real-model run
  needs none.
- **Reading rules, session-side.** One normative addition to the
  2026-09-01 record behavior: `session-record.json` is written for
  every session that starts, including adapter-error and timeout
  terminations; usage refusals (exit 2) write nothing. The smoke reads
  the record always and per-checkpoint receipts only when that
  checkpoint's grading ran.
- **Plumbing-failure shapes, session-side:** the adapter or Pi exits
  before the model runs; no genuine model-stream events (empty or
  absent stream content in the retained payloads); a plumbing code
  where a model-behavior outcome was expected; a receipt that produces
  no verdict where grading occurred. Smoke fails on any of these —
  stop, fix, do not proceed.
- **Positive evidence** that the model started is genuine
  model-stream events retained through the adapter's payload mapping —
  the session-side form of V5d's transcript discriminator.
- **No compatibility shim:** if the smoke requires an argv
  compatibility shim, that is recorded as a **failed stock-adapter
  proof**; the shipped adapter passes against the supported Pi
  executable itself. (The recorded engine smoke needed exactly such a
  shim; under this rule that outcome is a visible failure, and the shim
  debt stays in satyrn-engine's backlog.)
- **Durable evidence:** a uniquely named directory, never `/tmp`; its
  path is recorded with the outcome in the verification record.

Normative done-when text:

> The deterministic integration tier starts the shipped Pi adapter and
> proves the complete session protocol against a scripted Pi RPC
> fixture, without a model.
>
> Separately, one uncounted real-model smoke runs the small bundled
> session fixture through the shipped adapter. The durable verification
> record proves that Pi accepted the model configuration, emitted
> genuine model-stream events, maintained one conversation across the
> ordered prompts reached, produced parseable session/checkpoint
> artifacts, and tore down cleanly. Model behavior may pass or fail;
> the smoke makes no admission, difficulty, or quality claim.

## Delta 4 — the shipped adapter is Python, derived from official Pi RPC documentation

The adapter ships with satyrn-evals as a console-script executable
(entry-point name provisional, e.g. `satyrn-evals-session-pi`), speaking
the 2026-09-01 session JSONL protocol on stdin/stdout and driving one
`pi` child in RPC mode.

- **Derivation source: Pi's official RPC documentation**, not Engine
  internals. `pi --mode rpc --no-session` — RPC mode is "headless
  operation of the coding agent via a JSON protocol over stdin/stdout"
  with strict JSONL, LF framing (`docs/rpc.md:9-31` in pi 0.84.4), and
  the docs carry a Python `subprocess.Popen` client example
  (`rpc.md:1526-1532`). Engine evidence corroborates but does not
  derive; evals imports no Engine module.
- The scripted RPC fixture (layer (a)) asserts the wire protocol in
  CI, so a Pi runtime change is caught without a model.
- **Plan obligations:** pin the tested Pi version; pin the protocol
  messages the adapter uses (the session-relevant subset of
  `rpc.md`); the smoke then proves the real path end to end.

## Delta 5 — docs task: import the svcs probe record byte-for-byte

The probe record behind the svcs task's difficulty claims
(`2026-09-01-svcs-autowire-session-probe.md`) is not on main. V6
imports it exactly:

```bash
git show 577d540:docs/superpowers/research/2026-09-01-svcs-autowire-session-probe.md \
  > docs/superpowers/research/2026-09-01-svcs-autowire-session-probe.md
```

- The committed file is the **exact blob** — no banner, no header, no
  edit of any kind. A banner would change the digest. Provenance lives
  here and in the landing commit message, not in the preserved file.
- Expected SHA-256 of the committed file:
  `296a961fcb68cf66fbeef430df998d24e539bb1117a499751b9766d43915f664`.
- Verify after commit:

```bash
shasum -a 256 docs/superpowers/research/2026-09-01-svcs-autowire-session-probe.md
# -> 296a961fcb68cf66fbeef430df998d24e539bb1117a499751b9766d43915f664
```

Source: commit `577d540` on `origin/svcs-session-eval-design` — the
commit the 2026-09-01 spec banner already names; the blob is
byte-identical at the local PR-17 worktree tip `720e97d`.

## Non-goals (delta-level; the 2026-09-01 spec's Deferred list stands)

- `run` (V5b) gains no session support and cannot iterate sessions; a
  session-iterating loop belongs to a later admission/probe cycle.
- No admission decision for any session task in V6; the V5a rule
  applies when a probe with compared arms exists.
- No model-client integration, retries, hostile-command sandbox, or
  persistent Engine daemon — per the phase row. V7 detects leaks and
  requires cheap prevention for hidden-oracle tasks rather than V6
  preventing them.
- No svcs curation (Delta 1).
- Glossary additions wait for phase close-out, per the concept budget's
  rhythm.

## Done-when

The 2026-09-01 spec's done-when list stands, amended by:

1. **Slice-5 replacement** (Delta 1) — the svcs materialization
   requirement is gone; the fixture requirement replaces it.
2. **The session fixture** (Delta 2) exists with the named evidence
   floor — known-good accepted, known-broken rejected, both asserted by
   name — and the two refusal scenarios, each with its success sibling.
3. **Layer (a):** the deterministic integration drives all four prompts
   through the shipped adapter and asserts the listed behaviors.
4. **Layer (b):** the real-model smoke has run; its evidence is durable
   and recorded; the verification record evidences the five assertions
   in the normative text individually, with the no-shim outcome stated.
5. **The probe import** (Delta 5) is committed and its digest verified.
6. "deepest feature milestone, from zero through five" (2026-09-01
   record) reads "zero through N" for this fixture: N = 3.

## Reviewable slices (renumbered)

1. Grader-only overlay, its known-good/known-broken evidence floor, and
   backward-compatible ordinary grading (2026-09-01 slice 1).
2. Session manifest, typed records, protocol parser, and pure state
   tests (slice 2).
3. A shared V4 workspace lifecycle plus fake-adapter process and
   checkpoint preservation tests (slice 3).
4. Cumulative feature/base grading, scope enforcement, and records
   (slice 4).
5. **Replaced:** the `session-mechanics` fixture; the shipped Python Pi
   adapter derived from `rpc.md`; the all-four-prompt scripted-RPC
   integration proof; the real-model smoke (done-when); the probe
   import with digest verification; user documentation.

## Verification record shape

V4's pattern (`docs/sdd.md`): default-tier `pytest -q` counts; the
integration-tier command; the 100% statement-and-branch coverage gate;
then a smoke section recording the durable evidence path and each of
the five assertions individually, plus the explicit statement that
model behavior may pass or fail and makes no admission, difficulty, or
quality claim. If the smoke needed a shim, the record states that the
stock-adapter proof failed and what shim was avoided.

## Evidence and recomputation

- Probe blob digest, recomputed at spec time (both candidate commits
  agree):

  ```bash
  git show 577d540:docs/superpowers/research/2026-09-01-svcs-autowire-session-probe.md \
    | shasum -a 256
  # -> 296a961fcb68cf66fbeef430df998d24e539bb1117a499751b9766d43915f664
  ```

- Pi RPC surface (pi 0.84.4, installed package docs): `docs/rpc.md:9-31`
  — `pi --mode rpc [options]` (`:10`), `--no-session` (`:17`), protocol
  overview and LF framing (`:20-31`); Python `subprocess.Popen` example
  (`:1526-1532`). The docs ship inside the installed pi package — on
  this machine, under the
  `@earendil-works/pi-coding-agent` package's `docs/` directory; the
  line numbers above were read from pi 0.84.4's installed tree and must
  be re-checked when the plan pins the tested version.

- svcs baseline at the wall:
  `2026-09-02-v5a-admission-rule-design.md:270-276` (the recorded table
  row "1, 0, 0, 0", floor/wall).

  ```bash
  sed -n '270,276p' docs/superpowers/specs/2026-09-02-v5a-admission-rule-design.md
  ```

- Overlay clause measured both ways — models located graders on disk
  and optimized against them; not naming the grader recovered
  throughput: `2026-09-02-phase-proposals-and-session-eval-convergence.md:24-40`.

  ```bash
  grep -n "Stored where the attempt\|Named in the prompt" \
    docs/superpowers/research/2026-09-02-phase-proposals-and-session-eval-convergence.md
  # -> :33 and :36
  ```

- Contract-validation trigger already fired: the re-probe's engine arm
  was the first real engine run on a captured task — recorded in the
  landed V5d spec
  (`2026-09-03-v5d-preflight-smoke-check-design.md`, "The problem"),
  citing `2026-09-03-local-pings-reprobe-protocol.md:224-231`.
- V4 substitution precedent: `docs/sdd.md`, V4 verification record
  ("Only Pi is replaced by a deterministic fixture").
