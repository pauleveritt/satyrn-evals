# TE4 harder-roadmap screen — result

Run and retained 2026-09-11, under
[the pre-run record](te4-screen-pre-run-record.md). 2 attempts per
configuration, under the maintainer's standing overnight authorization
("free use of the GPU... keep working through TE").

## Outcome — both configurations, both attempts, all clean

| Attempt | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Turns | Hidden checks |
|---|---|---|---|---|---|---|
| Baseline-01 | pass (7) | pass (22) | pass (6) | **pass** | 43 (7/22/6/8) | 18/18 |
| Baseline-02 | pass (9) | pass (8) | pass (9) | **pass** | 32 (9/8/9/6) | 18/18 |
| Engine-01 | pass (6) | pass (8) | pass (10) | **pass** | 47 (6/8/10/23) | 18/18 |
| Engine-02 | pass (6) | pass (7) | pass (9) | **pass** | 45 (6/7/9/23) | 18/18 |

Model identity verified from every transcript
(`gemma-4-12B-it-MLX-8bit`), all four within the declared 75-turn
shared ceiling. **Both configurations completed the task both times —
a "both pass" screen outcome.** Per the TE plan's own instruction for
exactly this case: report the finding; do not automatically make the
task harder, enlarge the budget, or shop among variants.

This is Baseline's first data on this task under the current,
fully-fixed prompt (its only prior point, the route proof, predates
every tightening and both guardrails). Engine's cumulative record on
this task family is now **6 of 18** (4 of 16 before this screen); its
two most recent completions bring the running post-guardrail tally of
"destroyed, then restored" phase-4 attempts to 9 (6 of 9 now pass, 3
timed out) — both screen attempts made the same destructive edit named
throughout this sequence and both restored it before finishing.

## Test-file quality, per HP7's Finding 1

Both Baseline attempts extend their test file additively phase to
phase — phase 4's diff against phase 3 adds exactly
`test_resolve_complaint`/`test_reopen_complaint`, with phase 3's own
tests untouched (Baseline runs one continuous session with one file).
Both Engine attempts write a fresh, phase-scoped test file each
phase — this is the isolated-packet route's known, established
behavior (not a new finding; every prior Engine attempt in this
sequence does the same), not a within-phase destructive rewrite of the
kind HP7's Finding 1 flagged. No public-test-quality concern on either
side this round.

## No turn-efficiency contrast — if anything, the opposite of the TE hypothesis, at a sample size that cannot support the claim either way

TE's own working hypothesis, tested since TE1, is that Engine needs
fewer turns than Baseline. At n=2 per arm here: **Baseline's mean is
37.5 turns (32, 43); Engine's mean is 46 (45, 47) — Baseline used
fewer, not more.** This is the opposite direction from the hypothesis,
and it is exactly as unreliable as a favorable result at this sample
size would be — 2 points per arm is far short of what TE1's own
Baseline ceiling needed (six transcripts) to say anything about a
typical range, let alone a paired comparison. Stated plainly because
the honest reporting standard applied to every positive Engine result
in this sequence applies here too: this screen shows no efficiency
advantage for Engine, on either mean turns or completion reliability
at this n (both 2 of 2).

Baseline-02's phase-2-board took 22 turns — well above Baseline's
historic 5–9 range on this phase elsewhere in this task family and
above its own attempt 01's 8 — worth naming as elevated cost, not
investigated further here; it still completed and passed cleanly.

## What this screen does and does not establish

**Establishes**: with every named blocking ambiguity closed, both
configurations can complete this harder roadmap reliably at n=2 each.
Baseline's first fresh attempts under current conditions are both
clean. Engine's completion rate on its own larger sample (6 of 18,
≈33%) is far below what "2 of 2" here would suggest in isolation —
this screen's own 2 Engine attempts are not representative of Engine's
broader, harder-won record on this task, and should not be read as
evidence the completion rate has jumped.

**Does not establish**: a turn-efficiency claim in either direction (n
too small, and the observed direction opposes the hypothesis this
whole phase exists to test), a completion-rate claim for either
configuration from this batch alone, or that TE4's harder-roadmap
claim ("Engine completes harder work more reliably than Baseline
within a shared ceiling") is supported — on the evidence assembled
across this whole sequence, it currently is not: Baseline is 3 of 3 on
this task family (route proof plus these two), Engine is 6 of 18.

## Next, per the standing instruction

Per the plan's own rule for a "both pass" screen: **do not treat this
as grounds to design TE5's confirmation, enlarge this screen's budget,
or search for a harder variant.** The uncomfortable finding this
sequence's full evidence base now supports is that Baseline — never
needing any of the four tightenings or two guardrails this session
built for Engine — is the more reliable configuration on this specific
harder roadmap so far, and shows no turn-cost disadvantage either. Get
an independent review of this result, then bring TE4's full evidence
base (this screen plus every earlier live batch) to TE6's own
explain-and-decide step rather than proposing more live spending
chasing a favorable contrast that has not appeared.
