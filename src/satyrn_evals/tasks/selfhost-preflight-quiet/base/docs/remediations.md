# Remediations

*Status 2026-09-15: a remediation's "worked" claim is confirmed only where
its pathology entry is settled as a bug fix; where the pathology entry is
re-opened (model behaviour observed before release one's clean harness —
before 2026-09-14 14:25Z declared sampling, two-uid isolation, the budget
tripwire, and the base-commit harvest), the fix's effect on frequency or
severity is unconfirmed. See `docs/pathologies.md` and
`docs/superpowers/specs/2026-09-15-release-one-outcome.md`. Each numbered
entry below carries its own marker, matching its pathology entry.*

What was done about each entry in [pathologies.md](pathologies.md), and
whether it worked. Numbered to match — an entry here without a fix means
none has landed yet, and that is recorded as plainly as a fix that did.

## 1. Redundant-read lock

*Status 2026-09-15: re-opened (model behaviour, pre-clean-harness evidence)
— this fix's effect on the locking rate is unconfirmed.*

**Shipped: a spending rule, not a nudge.** `--max-repeated-calls N` tears
the command down after `N` identical consecutive tool calls, exactly as the
timeout tears it down — the model is sent nothing and told nothing. Off by
default, and the limit a batch used is recorded on every attempt record.
Validated by replaying it offline over the V11c batch's 24 retained
transcripts *before* it ran anywhere: the longest identical-call run was 1,
3, or 5 on every cell that went on to succeed, and 280 on every cell that
locked — a limit anywhere in that gap separates them exactly.
(`src/satyrn_evals/repeat_limit.py:7-23`, `docs/usage.md:128-134`)

Known gap, stated rather than hidden: turning it on forecloses ever
observing whether context compaction would have rescued a locked loop. It
is also validated against one model so far and is meant to be re-checked
per model before being trusted on a new one.

## 2. Streaming updates counted as extra tool calls

*Status 2026-09-15: settled as a bug fix.*

**Shipped.** The V10 amendment (2026-09-05) added `tool_execution_update`
to the recognized event vocabulary and defined it to count as nothing — a
streaming partial of an execution already bracketed by its start/end pair.
Before the amendment, a transcript containing that event type read
`unmeasured: unknown_event` and the whole cell was discarded rather than
merely miscounted.
(`src/satyrn_evals/pathology.py:19-33`)

## 3. `--model=VALUE` silently rejected

*Status 2026-09-15: settled as a bug fix.*

**Shipped, on both sides.** Engine commit `75d4863` fixed pi's parser.
Independently, Evals' own adapter never emits the combined form — it
always builds the model flag as two space-separated tokens — so the arm
substrate doesn't depend on the engine fix alone.
(`src/satyrn_evals/arms.py:198-201`, `src/satyrn_evals/attempt_pi.py:16-19`)

## 4. Untracked files invisible to patch capture

*Status 2026-09-15: re-opened (model behaviour, pre-clean-harness evidence)
— no fix has landed to confirm or disconfirm.*

**Not fixed — scoped around instead.** `git add -A` was considered and
rejected: it would sweep a model's own `uv run pytest` residue into the
patch and trip the writable-path allowlist. The chosen remediation is
containment, not correction: creation-capable capture is gated to a future
phase (V12), and until it lands, a task shape that needs the model to
create a file is excluded from measurement on this adapter rather than
measured wrong.
(`src/satyrn_evals/attempt_pi.py:22-30`)

## 5. Infrastructure crash counted as a plain refusal

*Status 2026-09-15: settled as a bug fix.*

**Shipped: a dedicated outcome code.** `MODEL_ERROR` is recorded when the
preserved transcript shows the inference substrate failed underneath a
well-formed request — a 5xx or a GPU out-of-memory fault — with no patch
delivered. `n` stays intact and the cell is still reported; dropping it
from a success count is left to the maintainer reading the summary, not
decided silently by the tally. The boundary is deliberately narrow: a 4xx
(the server answering and rejecting the input on its own terms, e.g. a
context-window overflow) is *not* `MODEL_ERROR` — it stays counted as
genuine pathology in the denominator.
(`docs/usage.md:136-145`)

## 6. `regrade` could not reach an already-collected infrastructure failure

*Status 2026-09-15: settled as a bug fix.*

**Shipped.** V11d slice 4 moved the reclassification check ahead of the
gradeable check inside `regrade`, and scoped it to exactly `NO_PATCH` and
`MODEL_ERROR` — the codes that name an observed defect rather than a cell
that already produced a patch. A `regrade` can now promote an
already-collected refusal cell offline, from the retained transcript,
without re-running the model.
(`src/satyrn_evals/rescore.py:363-372`)

## 7. A self-reported no-op edit repeated five times without adapting

*Status 2026-09-15: re-opened (model behaviour, pre-clean-harness evidence).*

**Partially covered by existing mechanisms, not a targeted fix.** The
`noop_edits` counter (entry 8's remediation) already measures exactly the
no-op `edit` calls this cell issued, so the pattern is visible in a summary
rather than hidden. `--max-repeated-calls` (entry 1) would have stopped
both the five identical edits and the seven identical route-check probes
had it been turned on for this run; it was off by default, so nothing
intervened and the cell simply ran long enough to recover on its own. No
detector yet distinguishes "the adapter told the model the edit was a
no-op and it repeated the identical call anyway" from an ordinary no-op —
that distinction, and whether it predicts which no-op loops recover versus
lock, is unaddressed.

## 8. No-op edit loop, reported as success

*Status 2026-09-15: settled as a bug fix.*

**Partially shipped — measured, not gated.** This repository's own
pathology counter includes `noop_edits`: any `edit` tool call whose
`oldText` equals its `newText` is counted per cell, using the same
well-formedness gate as every other count (entry 2). That makes the
pattern `local-ai-pi` recorded as a silent harness bug — accepting a
no-op edit and reporting it as changed — visible in every summary rather
than invisible. It is not (yet) a spending rule the way entry 1's repeat
limit is: a cell issuing no-op edits is measured, not stopped, so the
underlying loop-until-timeout shape entry 8 describes is not itself
foreclosed here.
(`src/satyrn_evals/pathology.py:301-312`)

## 9. Near-miss file targeting

*Status 2026-09-15: re-opened (model behaviour, pre-clean-harness evidence).*

**Not addressed.** No detector or adapter behavior in this repository
targets a model writing to a plausible sibling path instead of the one
it was asked to edit. Carried as an open risk, not a closed one.

## 10. Schema-mismatched call repetition

*Status 2026-09-15: re-opened (model behaviour, pre-clean-harness evidence).*

**Partially addressed, structurally rather than by design intent.**
Entry 1's `--max-repeated-calls` spending rule tears down a cell after
`N` identical consecutive tool calls regardless of *why* the calls
repeat — including a call that keeps failing schema validation the same
way. It was built for a different observed shape (a locked cell
re-reading a file it already has), not for this one, but the mechanism
covers it: a batch that turns the limit on stops this loop too, once
`N` identical malformed calls accumulate.
(`src/satyrn_evals/repeat_limit.py:7-23`)

## 11. Destructive failure tied to task shape

*Status 2026-09-15: re-opened (model behaviour, pre-clean-harness evidence).*

**Not addressed.** Nothing in this repository detects a repair attempt
that deletes existing tests rather than fixing them; the failure would
currently surface only as a failed grade, with no distinguishing signal
from an ordinary wrong-answer failure.

## 12. Empty-workspace probing spiral

*Status 2026-09-15: re-opened (model behaviour, pre-clean-harness evidence).*

**Not addressed directly, but partially covered by a general mechanism.**
No task-authoring convention in this repository states workspace
contents as an explicit fact the way the original remediation did. Entry
1's repeat-call limit would still cap a pure `ls -R` spiral once it
repeats identically enough times to cross `N`, but that is incidental
coverage, not a targeted fix.

## 13. Headless conversational stall

*Status 2026-09-15: re-opened (model behaviour, pre-clean-harness evidence).*

**Not addressed.** A cell that takes one turn, makes no tool calls, and
stops asking a question that will never be answered is currently
indistinguishable from any other zero-tool-call `NO_PATCH` cell — nothing
flags the "asked for input in a non-interactive context" shape
specifically.

## 14. Operationally vague self-authored specs

*Status 2026-09-15: re-opened (model behaviour, pre-clean-harness evidence).*

**Out of scope for this repository as currently used.** Every task this
repository runs against is a fixed, hand-authored contract; nothing here
uses a model to author the contract a later attempt executes. The finding
stands as a caution against ever doing so without an operational-vagueness
check, not as something remediated.

## 15. Scope overreach via its own contract's prose

*Status 2026-09-15: re-opened (model behaviour, pre-clean-harness evidence).*

**Partially addressed by a different mechanism, not the one that would
catch this exactly.** `workspace_escapes` (entry 2's module) measures a
file-tool path that resolves *outside* the transcript's working directory
— a lexical escape. The failure this entry names is different and not
covered: every path here stayed inside the workspace; the overreach was
editing a file inside the workspace that the contract's own
writable-path policy excluded. Catching that needs the contract's
allowlist compared against the touched paths, which this counter does
not do.
(`src/satyrn_evals/pathology.py:326-331`)

## 16. Oracle-hunting by filesystem search

*Status 2026-09-15: re-opened (model behaviour, pre-clean-harness evidence).*
Release one's clean harness re-observed hunting under isolation and closed
it with guard 4, which cut a root-wide hunt for the acceptance tests at
120 s that had cost a Baseline cell 1,800 s
(`docs/superpowers/specs/2026-09-15-release-one-outcome.md`); the confounded
ranking below is still unconfirmed.

**Partially shipped, and one hole named rather than hidden.** A
whole-process `sandbox-exec` (Seatbelt) profile closes most of it:
allow-only reads limited to OS/toolchain roots plus the run root, writes
confined to the run root, network limited to the local model server —
verified live, grader reads, `$HOME` listing, and symlink escapes are all
refused while the model still reaches its server.

**What the profile does not close:** Seatbelt enforces on paths, so a hard
link created *inside* the run root and pointing at the grader is still
readable — the probe log records that read succeeding. Whether a sandboxed
process can create such a link was never itself tested. An earlier draft
of the source record claimed hard-link escapes were refused; that claim
was wrong and was corrected in the same document rather than quietly
dropped.

**A behavioral remediation, confounded rather than confirmed:** telling the
model in-prompt that "the acceptance suite is owned by the caller … it is
run for you" measurably suppressed grader-hunting in the transcripts (`ls
-R`/`find` spirals dropped). But the same wording also suppresses the
model's own test-running, and in that spike the two effects were never
disentangled — the pass-rate ranking built on that wording was later
retracted as confounded by unequal exposure to entry 17's defect below,
not by the wording itself. Treat the search-suppression as real and the
ranking as not established.
(archived: `2026-09-02-overnight-packet-and-isolation-run.md` §2, §1 and
its correction)

## 17. Sandbox removed the model's own test runner

*Status 2026-09-15: re-opened (model behaviour, pre-clean-harness evidence).*

**Not fixed within that record — named as a required follow-up.** The
same document that found it (adversarial review, not the original author)
stated the fix directly: a corrected profile must grant the run root a
working interpreter and test runner. No re-run confirming that fix exists
in this repository yet.
(archived: same document, §2)

## 18. A detector that always fires

*Status 2026-09-15: settled as a bug fix.*

**Shipped, in a different module than the one that failed.** The spike's
own proposed standing test — every detector must fire on a known-bad from
the current batch and stay silent on a known-good from the same batch,
both directions, every time — is answered by this repository's live
contamination module. Rather than a path-substring match (which fires
whenever a transcript merely contains its own filesystem path),
`grader_content_in_patch` and the other checks require a verbatim,
multi-line content block (`GRADER_BLOCK_LINES = 4`) and explicitly exclude
any block already shown to the model as visible content — a design
constraint stated directly in its module docstring: "the single idiomatic
line of an honest test must never fire."
(`src/satyrn_evals/contamination.py:1-25`)

## 19. Contamination overstated sixfold on first read

*Status 2026-09-15: settled as a bug fix.*

**Addressed by the same rewrite as entry 18, not by a separate fix.** The
original failure was a filename/path match standing in for evidence of
actually having seen hidden content. The current design's rule — trust the
content-based `COPIED` signal, treat a bare filename/path match as "a
prompt for inspection, not a verdict" — is exactly the correction the
archived record called for after catching its own sixfold overstatement.
Matching is verbatim-only by design, so a *paraphrased* leak still passes
every check; that is a stated, accepted limit, not an oversight.
(`src/satyrn_evals/contamination.py:1-11`; archived: same document, §3)

## What is still open

Entries 4, 9, 11, 13, and 17 have no landed fix. 4 is deliberately scoped
around (deferred to V12); 17 was named by review but not yet re-verified;
9, 11, and 13 have no detector or mechanism addressing them at all. Entries
7, 8, 10, 12, and 15 have partial coverage from a mechanism built for a
different failure shape, not a targeted fix — read those sections for the
gap, not just the heading. Don't read any entry as closed because it has
a number here.
