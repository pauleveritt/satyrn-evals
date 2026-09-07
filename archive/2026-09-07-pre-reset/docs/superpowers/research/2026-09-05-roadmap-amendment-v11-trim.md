> **Archived pre-reset record (2026-09-07).**
>
> Original claims, decisions, and instructions may be superseded. This file is evidence, not current guidance.
> For current guidance, read root AGENTS.md, BRIEF.md, and ROADMAP.md. Retrieve one named record when it bears on a concrete question; do not preload this archive.

# Amendment to the 2026-09-04 roadmap record: V11 trimmed, `specs/` vendoring reversed

**Date:** 2026-09-05. **Status:** confirmed by the maintainer.

This is a **dated amendment** to
[`2026-09-04-roadmap-to-a-reliable-instrument-and-a-first-engine-result.md`](2026-09-04-roadmap-to-a-reliable-instrument-and-a-first-engine-result.md).
Per `CLAUDE.md` — *a correction is recorded, not edited away* — that record
is left intact and this document supersedes the two decisions named below.

Argument of record:
[`2026-09-05-v11-trim-and-spike-proposal.md`](2026-09-05-v11-trim-and-spike-proposal.md),
§9 items 1–3.

## What is amended

**Decision 2 — "Contract rungs are a manifest field", `contracts: {R0…R3}`.**
*Survives in form, narrows in initial shipment.* The open map is exactly
right and is what makes the narrowing cheap. V11a-trim ships **R1 and R3
only**. R0 and R2 become later **authoring** additions — a new key, not new
machinery — and are a **V12 entry gate**, because V12 still profiles all four
rungs.

**Decision 4 — "Vendor `specs/` into `base/` — yes."** *Reversed.*
`grade.py:121-129` builds `visible_texts` from every file under `base/`, and
the contamination scanner subtracts any overlay window that also appears
there. Vendoring **enlarges that subtraction set** and could silence the
known-broken half of the contamination pair test. With `base/`
byte-identical, the six contamination pairs and the 24/24 gate need no
re-derivation.

The argument is **independence, not cost** — the gate is integration-tier and
runs in minutes. The point is that nothing about it changes.

**A consequence that is not a reversal:** R0 never needed vendoring for five
of six tasks. The public suite is red at base on 5/6, so "the suite is red;
public tests are in `tests/`" is a fair R0 with **zero fixture bytes
changed**. Only `framing-2-edit` (public suite green — its defect is visible
only to the hidden suite) would need the spec.

## What is *not* amended

Decisions 1, 3, 5 and 6 stand. **V12's scientific scope is unchanged** — two
named models, six tasks, four rungs, reference arm only, `n=6`. **V13's
scientific scope is unchanged.**

## Two deferrals, each with its condition

**The widened hidden-id check is deferred.** For these tasks the overlay
declares exactly `overlay`, `test_acceptance.py`, and
`overlay/test_acceptance.py`. The **existing** check already forbids the file
name, so an R1 digest must carry **bare function names**. The proposed
widening would forbid those, which R1 carries by design — at R1 the widening
is **contradictory**. V8 §4 already authorized naming them.

The residual risk it was meant to cover — a model inferring a second suite
and hunting for it, with the overlay present and Baseline holding `bash` — is
**not closed by any text check**. V10 supplies partial detection only:
`workspace_escapes` sees lexical paths passed to file tools but not paths
embedded in `bash`; `overlay_windows` sees verbatim windows but not
paraphrases or short disclosures. **These are tripwires, not containment.**

**Envelope is deferred out of V11b and the spike.** The 900 s / 8192 tokens /
80k context in the de-admission record are **pi and model settings, not what
`envelope-cap.ts` capped** — nobody knows what it capped. The cap value is a
**fresh choice that must be argued**, and an external kill is not an in-loop
cap. V13 defines Envelope once and preregisters it. This closes open question
1 of the 2026-09-04 record by deferring it to the phase that must own it, not
by answering it.

## The V12 entry gate this creates

Before V12 runs, three things are owed:

1. **Author R0 and R2**, restoring the four-point monotonicity check. While
   only R1 and R3 ship, the authoring gate collapses to a two-point
   `R1 ≤ R3` check, and no run in V11 measures even that. **Rung labels are
   unverified authoring claims until V12.**
2. **Creation-capable patch capture.** `git diff HEAD` drops files created by
   `write`. Harmless on pure-edit repair, fatal for `framing-2` — which would
   otherwise measure an adapter limit as model behavior.
3. **Re-run the real one-word completion**, never `/v1/models`, immediately
   before the first cell.

## The sequencing bet, priced openly

Trimming to R1/R3 bets that R1 is not already at ceiling for a 12B. Every
prior points the other way: the fixture author's own review says
`assert 307 == 303` "delivers the answer"; Block B recorded 19/20 on
`plausible-wrong-fix`; the V8 smoke passed first try at R3, and **R1 removes
only the file name and the fix sentence**. If the mini-probe ceilings at R1,
R0 returns before the spike. The open map is what makes losing this bet
cheap.

## Amendments to this amendment

**2026-09-05, same day — `-nc` pinned in both arms.** Measurement showed ~93%
of a repo-root `pi` call was context-file discovery. Both arms pin
`--no-context-files`: it closes an **undetected** instruction-file
contamination surface, and it restores **arm parity**, since `satyrn-engine`
already passes the flag while the scratch Baseline wrapper does not. Record,
including a retracted attribution and two figures that remain unexplained:
[`2026-09-05-pi-context-file-loading-and-arm-parity.md`](2026-09-05-pi-context-file-loading-and-arm-parity.md).
