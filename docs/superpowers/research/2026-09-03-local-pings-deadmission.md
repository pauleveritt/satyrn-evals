# `local-pings` de-admission — and the canonical-Envelope reconstruction stop

**Date:** 2026-09-03. **Status:** decision recorded by the maintainer.
**Branch:** `de-admit-local-pings`.

## The decision

The maintainer de-admitted `local-pings` as a diagnostic workload while
retaining it as a valid bundled task usable as a grader, smoke, or
regression fixture.

**Binding evidence.** The completed captured-task re-probe
([results section](2026-09-03-local-pings-reprobe-protocol.md)) recorded
Baseline 3/8 and Engine 4/8 successful attempts — both middle-band under
the V5a band definitions. V5a requires at least one pair of compared arms
in different successful-attempt bands; no pair separates, so the task does
not satisfy the admission rule. This supersedes the V5a "admissible"
reading for the captured N=6/five-ID task; the N=2/four-test admission
evidence it was built on is preserved historically
(`2026-09-02-v5a-admission-rule-design.md`) and does not govern the
captured task. No recorded cell was rerun or reinterpreted; the n=8 cells
stand as recorded.

**Recorded points**

- `local-pings` remains a valid bundled task and may serve as a grader,
  smoke, or regression fixture.
- It is no longer admitted as a diagnostic workload.
- The obsolete N=2/four-test admission evidence remains preserved
  historically but does not govern the captured N=6/five-ID task.
- No existing cells are rerun or reinterpreted.
- Re-admission of the *unchanged* captured task requires a newly
  preregistered qualifying probe; simply increasing n was set aside as a
  tune-until-separated risk.
- A *materially revised* task or adversary is not re-admission of this
  task: it is a **new admission candidate** requiring its own capture and
  fresh qualification.
- Recovering the historical Envelope artifact is optional research, not a
  V5c blocker (backlogged with a precise reopen condition that requires
  the `b7455133` extension *and* the era's Pi/prompt/adapter/harvesting
  provenance — the file alone is insufficient).
- Any Envelope assembled with current Pi, a new adapter, or a selected
  prompt must be described as a **new prospective arm, not a
  reproduction**.

## Why the Envelope re-earn path stopped

The cleanest attempted route to *re-earn* admission was a canonical
Envelope arm; higher-n and new prospective-arm routes remain open, and a
materially revised task or adversary is a separate new-candidate track.
Its definition was located in the seed
repository (`local-ai-pi`): `workloads/svcs/cells/gemma12b-envelope.toml`
pins model `omlx/gemma-4-12B-it-MLX-8bit`, `tools = "read,write"`,
`extensions = "envelope-cap.ts"` at
`extensions_sha256 = b7455133…`, a 900-second wall clock, 8192 max
tokens, an 80 000-token context, and the local oMLX base URL.

Faithful reconstruction is impossible from this machine's records:

1. **The pinned extension is absent.** All seven `envelope-cap.ts` copies
   on this machine (main checkout plus the era worktrees) hash
   `0448af10…` — the pilot's extension — never the canonical pin
   `b7455133…`. The pin exists in no revision of `local-ai-pi`'s git
   history (the extension entered as `0448af10`; the toml entered later
   pinning `b7455133`), and the canonical toml itself was once mutated in
   place (v2-cell note; commit `5d04a3e`). The pinned file lived in
   `phase7-workload@2fdce499…` on the other machine.
2. **Pi version, adapter, and artifact harvesting were never recorded for
   the canonical runs.** The one canonical-envelope run (phase7-cycle3
   envelope screen, 0/24) executed on the predecessor harness, whose
   plumbing its docs do not record and whose code this repository's
   provenance rule forbids transplanting.
3. **The prompt is contested even in the era record** — brief-only and
   contract were separate arms of that screen — while the comparison
   cells on this task ran contract-only.

Per the maintainer's Phase-1 gate, the probe stopped and no protocol was
written. Even recovering `b7455133` would not fully reconstruct the
historical Envelope — Pi version, adapter/harvesting, and prompt remain
unresolved — so **any** Envelope run on current machinery is a new
prospective arm, not a reproduction. Recovery is backlogged as optional
research.

## Status effects

- `local-pings` stays bundled (`src/satyrn_evals/tasks/local-pings/`),
  unchanged: manifest, oracle, fixtures, and engine contract stand.
- The V5a spec's `local-pings` index carries a dated supersession note;
  the historical verdict and tables are untouched.
- ROADMAP, README, `docs/index.md`, and `docs/usage.md` state the
  de-admission consistently.
- BACKLOG carries the re-admission and Envelope-recovery entries, each
  with a precise reopen condition.

## Pointers

- Re-probe results: `2026-09-03-local-pings-reprobe-protocol.md`
  (results section; both arms' `summary.json` under
  `~/projects/pauleveritt/satyrn-v5c-scratch/runs/{baseline,engine}/`).
- V5a index and supersession: `2026-09-02-v5a-admission-rule-design.md`.
- Canonical-Envelope evidence: `local-ai-pi`
  `workloads/svcs/cells/gemma12b-envelope.toml`,
  `extensions/envelope-cap.ts` (sha256 `0448af10…` on disk vs the pinned
  `b7455133…`), and
  `2026-08-10-phase7-cycle3-envelope-screen.md`.
