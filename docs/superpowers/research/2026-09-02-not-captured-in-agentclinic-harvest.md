# What this session found that `research/agentclinic-spike-harvest` doesn't capture

**Date:** 2026-09-02
**Status:** companion note to
[`2026-09-01-handoff-and-eval-harvest.md`](2026-09-01-handoff-and-eval-harvest.md)
and [`2026-09-01-agentclinic-spike.md`](2026-09-01-agentclinic-spike.md) —
read-only gap analysis, not a design and not a plan.
**Method:** a separate cross-repo investigation (SwiftStar, local-ai-pi,
ds4-engine, satyrn-engine, and satyrn-evals' own unmerged branches),
conducted independently, then checked line by line against a full read of
both harvest documents above. Nothing here has had the adversarial-review
pass those documents describe applying to themselves; treat it with the same
caution they ask for their own claims.

**Why this exists.** The harvest documents' own §5 makes the case for this
kind of check: the same spike re-derived four already-recorded findings in
one afternoon before anyone thought to grep the research directory first.
This note is that grep, run in the other direction — after independently
covering similar ground, checking what the harvest already has and listing
only what it doesn't, so a future reader does not re-derive a fifth time.

## A. SwiftStar findings not in the harvest

- **Pathology #28 — scope overreach via the contract's own prose, and its
  unvalidated fix.** A contract restricted to `src/svcs/**` still got a docs
  file edited because the contract's own "Documentation Note" prose asked
  for it (`swiftstar/docs/pathologies.md:23-28`). SwiftStar built a
  writable-scope-injection fix and never ran it
  (`swiftstar/docs/remediations.md:257-266`, under "Built but never measured
  against the pathology"). This is the single most concretely portable,
  ready-to-test idea found in either source repo, and it does not appear
  anywhere in the harvest.
- **Pathology #2 — "talk yourself out of the answer."** The largest single
  failure population in a 2026-08-29 classification: 7 of 24 non-passing
  repair captures, larger than the delivery-defect population (2 of 24) the
  campaign was actually chasing that day (`swiftstar/ROADMAP.md:798-812`,
  `docs/pathologies.md:18-19`). Not in the harvest's §4 failure-mode list.
- **Pathology #19 (locate-only stall)** — real-app turns stalled issuing only
  read/list/search with zero mutations 4/6 (67%) of the time vs. 12% in a
  file-list-primed harness — and **pathology #16's specific numbers** (97% of
  a 16,384-token context consumed by one think-loop probe with no answer;
  P23 measured the wall-clock ceiling of removing thinking at ~9.3%, "not a
  throughput lever"). Neither appears.
- **Two retracted quantitative claims from local-ai-pi**, both published and
  withdrawn the same night: a "4.4× tool-call ratio" that was a
  substring-counting bug over a re-serialized transcript (real ratio 21.9×
  vs. 10.0×), and a "1,416 seconds" wall-clock gap invalidated by
  contiguous-block scheduling on a variable-load machine
  (`local-ai-pi/docs/superpowers/phase-history.md:134-144`). Not mentioned.
- **`swiftstar/docs/remediations.md`'s ranked-15 list, and its provenance
  footer.** The footer explicitly separates which remediations trace back to
  local-ai-pi's own phase 5/7/11 work (ranks 1, 2, 4, 10, 13, 14, 15) from
  which are SwiftStar-native (ranks 3, 5, 7, 8, 9, 11, 12). Two SwiftStar-
  original packet-directive fixes with real measured effect — the multi-file
  repair directive (false clause wrong in 39/40 cells,
  `remediations.md:121-133`) and count-free plural emission (a 40-cell arm
  landing 62% [47%,76%], `remediations.md:165-179`, reported honestly as
  narrowly missing its pre-registered bar) — are not cited. This whole
  document, and the directionality it establishes, is absent from the
  harvest.
- **The stated origin of the `facts` field.** SwiftStar's own design spec:
  *"Grounded in the recorded `local-ai-pi` result that facts work and rules
  of conduct do not"* (`swiftstar/docs/superpowers/specs/2026-08-21-swiftstar-design.md:94`)
  — a direct provenance citation the harvest's Gen 3→4 lineage discussion
  (§0-§1) does not include.

## B. local-ai-pi findings not in the harvest

- **The Phase 11 spike's actual numbers.** Bare envelope 0/24 candidates
  created vs. bounded contract 8/8; hand-authored contract 8/8 vs. a weak
  brief 0/4; model-authored contract 3/8 vs. hand-authored 8/8; a remediated
  authoring prompt collapsing to 0/8, all no-op
  (`local-ai-pi/ROADMAP.md:388-401`). The harvest cites the related "user-story
  suite at 15/16 with facts, no headroom left" result (Correction 9, from a
  *different* experiment — the Cycle 10/11 pair), but this Phase 11 material
  is absent entirely.
- **HARVEST-INDEX's derive-vs-apply / no-op attractor** — asked to *derive* an
  edit rather than reproduce it verbatim, the model emitted 5 consecutive
  byte-identical no-ops, and the engine's "changed lines=0" was read as
  success — a harness bug compounding a model failure
  (`local-ai-pi/docs/superpowers/handoff/HARVEST-INDEX.md:44-55`). And the
  **`PI_CODING_AGENT_DIR` scope-leak fix** (an unset env var let a delegated
  child inherit the operator's own extensions; timeouts 2/6→0/6, worst
  repeated command 178→5 after the fix). Neither is in the satyrn harvest's
  §4 failure-mode list, though §4.1's "mechanism never engaged, graded
  accepted" finding is a related but distinct failure shape.
- **Pathology #24** — a 24-replicate noise-floor run with 5/6 "tests-vanished"
  plus 1 damaged (0/6 accepted).

## C. ds4-engine work — a different repository, not referenced by the harvest at all

None of this touches the harvest, since it lives outside the satyrn split
entirely:

- The full **`ds4-engine/docs/capability-map.md`** ranked capability list (35
  entries) and the specific pairing of SwiftStar/local-ai-pi pathologies to
  capability entries — e.g. pathology 28 (scope overreach) to capability #1
  (symbol-mask enforcement) and #29 (contract linting); the "talk yourself
  out of the answer" pathology to #17/#18 (mask-rejection calibration,
  logprob-aware termination); the Cycle 10/11 measurement collapse to #14
  (shared-prefix counterfactual sampling).
- The drafted research note
  `ds4-engine/docs/superpowers/research/2026-09-01-handoff-packet-engine-capabilities.md`,
  arguing that packet *authoring* should move to deterministic tooling rather
  than a second model agent — reaching a similar destination to the harvest's
  open question 1 ("is a packet with no orchestrator machinery ahead of its
  contract?"), but by an independent route through a different project's own
  architecture rules.

## D. satyrn-engine's own current state — the harvest never inspects this repo

- The **actual current `Contract` dataclass**
  (`satyrn-engine/src/satyrn_engine/contract.py:23-28`): three fields —
  `id`, `task`, `writable_paths` — and that `build_prompt`
  (`attempt.py:229-238`) renders no `facts` field today. This is the concrete
  object any "smallest useful subset of fields" decision (harvest's open
  question 2) would actually be edited on, and the harvest doesn't cite it.
- **`satyrn-engine/BRIEF.md:67-90`'s "trap we are avoiding"** — three prior
  attempts became engineering efforts about orchestration until the machinery
  outgrew anyone's ability to hold it in their head; the concept-budget and
  repository-weight-budget consequences drawn from it — and the explicit
  Backlog exclusion, **"contract authoring (stays a main-agent skill)."** The
  harvest's open question 1 asks almost the identical question independently,
  without knowing this repo already answered the authoring half of it.
- `tools/replay_orchestrator.mjs`, and that satyrn-engine's phase history
  (E1–E5 done, E6 "Packaged" current, 15 merged PRs, none open) is a clean,
  linear, uncontested trail — no in-flight work to coordinate around.

## E. satyrn-evals' own separate, unmerged headroom probes — not cross-referenced by the harvest branch either

This is the most surprising gap: two more local-only branches exist in this
same repository, alongside the harvest branch, and the harvest doesn't
mention them — meaning at least three independent, uncoordinated research
efforts exist in this repo right now.

- **`origin/research/stringified-annotations-baseline`** (PR #16, commit
  `a6d43e5`) — bare Pi floors 0/4 under the *final*, curator-strengthened
  oracle; not admitted. Full oracle-evolution history: an earlier, looser
  oracle with a parameter-name loophole is superseded and explicitly
  disclaimed as not supporting the decision.
- **`origin/research/magicmock-factory-baseline`** (PR #15, commit
  `ac11b33`) — same pattern: bare Pi floors 0/4 under the final oracle, not
  admitted, with its own two-stage oracle-correction history (an unsound
  oracle that missed a genuine async-context-manager case).
- **`origin/svcs-session-eval-design`** (PR #17) — a draft multi-prompt
  session-eval design, unrelated to headroom, but still a third piece of
  concurrent unmerged work the harvest doesn't acknowledge exists.
- **The observation that the Engine arm has never been run against either
  currently-floored task.** Only bare Pi was probed to establish both floors.
  This is the load-bearing move behind this session's proposed "Stage 0" (run
  the existing 3-field `Contract` against `magicmock-factory` before changing
  anything), and it is absent from the harvest, which never engages with
  these two probe documents at all.

## F. This session's own operational output

- A **worktree/spike-branch brief** for satyrn-engine + satyrn-evals: pin the
  cross-repo seam with `SATYRN_V4_ENGINE_REPO` rather than a submodule or
  package dependency (satyrn-evals deliberately has zero Python dependency on
  satyrn-engine — `docs/superpowers/plans/2026-08-23-v4-real-engine-attempt.md:59`);
  a two-stage plan (run the existing Engine arm first, add `facts` only if it
  still floors); and guardrails tying the "don't build orchestration
  machinery" rule explicitly to `satyrn-engine/BRIEF.md:67-90`.

## G. Live machine-state verification

- Confirming that `omlx-server`'s `/v1/models` catalog (this machine, port
  8001) **lists `gemma-4-12B-it-MLX-8bit` as if available**, while the
  weights are genuinely absent from `~/.cache/huggingface/hub` — the catalog
  is a registered/known-model list, not a cached-and-loadable list. The
  harvest's open question 6 flags Mellum as "not verified to load," which is
  the right caution, but doesn't identify that the server's own model list
  can't be trusted as evidence of availability either — a sharper and more
  actionable version of the same caution.

## One tension worth checking, not resolving here

The harvest's open question 2 states `removableSymbols` has "no measured
incidence data in either repo." `swiftstar/docs/remediations.md` rank 13
describes a measured result (1/4→4/4, Fisher p=0.14, n=4 capped) tied to
`HandoffContract.removableSymbols`. On a closer read, that measurement may be
of the *pre-edit guard* that referenced the field and was later removed for
lacking visibility into contract-authorized renames — not a direct test of
the field's own effect — so this may not actually contradict the harvest's
claim. Flagged here rather than adjudicated, since resolving it needs a
direct re-read of `swiftstar/docs/remediations.md:181-192` against whatever
source the harvest's open question 2 was drawing on.

## What this note does not do

It does not evaluate whether any of the above should be *adopted* — that is
exactly the kind of premature-machinery judgment call `satyrn-engine/BRIEF.md`
warns against making ahead of a concrete need. It is an inventory of what one
more independent pass found that the existing harvest didn't, so the next
person deciding what to build next has the fuller set of prior art in view
before choosing.
