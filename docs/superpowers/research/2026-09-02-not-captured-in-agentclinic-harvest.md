# What this session found that `research/agentclinic-spike-harvest` doesn't capture

**Date:** 2026-09-02
**Status:** companion note to
[`2026-09-01-handoff-and-eval-harvest.md`](2026-09-01-handoff-and-eval-harvest.md)
and [`2026-09-01-agentclinic-spike.md`](2026-09-01-agentclinic-spike.md) —
read-only gap analysis, not a design and not a plan.
**Sanitized for a public repository (2026-09-02).** Two of the repositories
surveyed here — `swiftstar` and `ds4-engine` — are **private**. Their file
paths, verbatim text, and unpublished measurements have been removed; what
remains is the transferable lesson and a pointer to where the detail lives.
`local-ai-pi` and `satyrn-engine` are public and cited normally.

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

- **Scope overreach caused by the contract's own prose, and its unvalidated
  fix.** A contract restricted to one source subtree still had a docs file
  edited, because the contract's *own explanatory prose* asked for it. That
  repository built a writable-scope-injection fix and filed it under "built but
  never measured against the pathology". This is the single most concretely
  portable, ready-to-test idea found in either source repo, and it does not
  appear anywhere in the harvest.

- **"Talk yourself out of the answer."** The largest single failure population
  in that repository's own classification of non-passing repair captures —
  larger than the delivery-defect population the campaign was actually chasing
  that day. Not in the harvest's failure-mode list, and it is plausibly the
  same shape as the announce-then-stop behaviour the overnight run recorded.

- **A locate-only stall**, where real-app turns issue only read/list/search
  calls and never mutate anything — markedly more common without a primed file
  list — and a **think-loop probe** that consumed nearly all of a small context
  window without producing an answer, alongside a measurement that removing
  thinking was not a throughput lever. Neither appears in the harvest; the
  figures stay in the private repository.

- **Two retracted quantitative claims from local-ai-pi**, both published and
  withdrawn the same night: a "4.4× tool-call ratio" that was a
  substring-counting bug over a re-serialized transcript (real ratio 21.9×
  vs. 10.0×), and a "1,416 seconds" wall-clock gap invalidated by
  contiguous-block scheduling on a variable-load machine
  (`local-ai-pi/docs/superpowers/phase-history.md:134-144`). Not mentioned.
- **That repository's ranked remediation list, and its provenance footer.** The footer explicitly separates which remediations trace back to
  `local-ai-pi`'s own earlier phases from which originated in that repository.
  Two of its
  original packet-directive fixes with real measured effect — a multi-file
  repair directive (correcting a false clause that was wrong in nearly every
  cell of its arm) and a count-free plural emission (an arm reported honestly
  as narrowly missing its own pre-registered bar) — are not cited. The figures
  themselves stay in the private repository. This whole
  document, and the directionality it establishes, is absent from the
  harvest.
- **The stated origin of the `facts` field.** That repository's own design
  spec grounds the field explicitly in the recorded `local-ai-pi` result that
  facts work and rules of conduct do not
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
- **A noise-floor replicate run** in which almost every cell lost its tests or
  was damaged, accepting none.
  plus 1 damaged (0/6 accepted).

## C. ds4-engine work — a different repository, not referenced by the harvest at all

None of this touches the harvest, since it lives outside the satyrn split
entirely:

- A ranked capability list in a third, private engine repository, and the
  specific pairing of the pathologies above to entries on it — scope overreach
  to symbol-mask enforcement and contract linting; "talk yourself out of the
  answer" to mask-rejection calibration and termination criteria; a measurement
  collapse to shared-prefix counterfactual sampling.
- A drafted research note in that same repository, arguing that packet
  *authoring* should move to deterministic tooling rather than to a second
  model agent — reaching a similar destination to the harvest's open question 1
  ("is a packet with no orchestrator machinery ahead of its contract?"), but by
  an independent route through a different project's own architecture rules.

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
  Backlog exclusion, which states that **contract authoring is a main-agent skill rather than engine work.** The
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

  **Correction (2026-09-02, from the overnight run).** The supporting instance
  is wrong; the lesson is right. `gemma-4-12B-it-MLX-8bit` **is** cached
  locally, at
  `~/.cache/huggingface/hub/lmstudio-community/gemma-4-12B-it-MLX-8bit` — the
  search looked under `mlx-community/`, where only the 26B sibling lives. The
  model demonstrably loads and generates: it served roughly 100 measured cells
  overnight, and a one-word probe returned in 3.8 s while this correction was
  being written. So this cannot be cited as an example of a catalog entry
  without weights.

  The *claim* the instance was offered for still holds, and was independently
  established the same night by a different route: block 5 of the overnight run
  lost 16 of 16 cells to zero-event timeouts while `/v1/models` answered
  normally, because that endpoint is served from a registry and says nothing
  about whether a model can generate. The fix adopted there was a live
  one-word completion per model before each block, not a catalog check
  (overnight `notes/FINDINGS.md` F10). Cite that instance instead of this one.

## One tension worth checking, not resolving here

The harvest's open question 2 states `removableSymbols` has "no measured
incidence data in either repo." that repository's remediation list
describes a measured result (a small, n-capped result) tied to
that contract type's rename-declaring field. On a closer read, that measurement may be
of the *pre-edit guard* that referenced the field and was later removed for
lacking visibility into contract-authorized renames — not a direct test of
the field's own effect — so this may not actually contradict the harvest's
claim. Flagged here rather than adjudicated, since resolving it needs a
direct re-read of that repository's remediation list against whatever
source the harvest's open question 2 was drawing on.

## What this note does not do

It does not evaluate whether any of the above should be *adopted* — that is
exactly the kind of premature-machinery judgment call `satyrn-engine/BRIEF.md`
warns against making ahead of a concrete need. It is an inventory of what one
more independent pass found that the existing harvest didn't, so the next
person deciding what to build next has the fuller set of prior art in view
before choosing.
