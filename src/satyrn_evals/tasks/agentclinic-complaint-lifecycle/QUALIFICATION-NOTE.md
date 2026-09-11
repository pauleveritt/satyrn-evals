# Qualifying agentclinic-complaint-lifecycle

Four ordered development requests over one growing checkout, starting from
the same bare base as `agentclinic-session-phased`. Phases 1-3 started as
that task's own phases, reused verbatim; phase 2's prompt has since been
amended (below). Phase 4 is new, scoped by
[the TE4 design](../../../../docs/current/te4-harder-roadmap-design.md).

**Amended 2026-09-10 — the phase-2-board guardrail adopted.** Following
[the runaway investigation](../../../../docs/current/phase-2-board-runaway-investigation.md)
and its [candidate probe](../../../../docs/current/phase2-guardrail-candidate-result.md)
(3 of 3 Engine attempts on a bounded standalone task completed cleanly,
zero destructive edits, one attempt reaching the exact decision point
and taking the safe branch), phase-2-board's prompt gains one bullet,
inserted before "Add `GET /complaints` route":

> - When adding the new route to `app.py`, insert it alongside the
>   existing `/` route — do not remove, replace, or rewrite the route
>   that already works

This is a scoped adoption: **only this task's prompt changed.**
`agentclinic-session-phased` — used by HP7, TE1's ceiling evidence, and
the TE2/HP8 screen, each an already-accepted historical record citing
its own frozen phase-2-board digest — is untouched, deliberately, so
none of those records' digests go stale. `phase-2-board`'s new prompt
digest is `362480e8681f118a` (1774 bytes, was `8bc6457681df6448`,
1622) — this is the number to check against prior records, since it
lives in `session.json`, not here. **The task tree sha256 is
deliberately not quoted in this file**: that digest sweeps this whole
directory, including this note, so any number written here about its
own directory's digest is wrong the moment this sentence is added —
recompute it fresh, or read whichever pre-run record cites it for a
specific run. The
[route proof](../../../../docs/current/te4-route-proof-result.md)
and its own pre-run record predate this change and correctly cite the
pre-amendment digests for the run they document — they are not
retroactively edited. All eight qualification-suite checks re-pass
unchanged: the required app behavior never changed, only the
instruction on how to add the route.

`BRIEF.md`'s two selection rules apply: this note qualifies the task as a
**grader fixture** -- its witnesses are graded and its prompts are shown
to be sufficient. Nothing here establishes it as a diagnostic workload; no
session has been run against it.

## The prompt source

Phases 1-3: identical to `agentclinic-session-phased/session.json`, quoted
from the same upstream source at the same pinned sha (see that task's own
`QUALIFICATION-NOTE.md` for the provenance and the two tightenings applied
there -- both carry over unchanged, since the text is unchanged).

Phase 4 is **newly authored** for this task, not quoted from any upstream
roadmap. It is written directly against the app phases 1-3 produce, using
the same preamble.

## The map: every phase-4 check, and the prompt line that establishes it

| # | check | prompt line |
|---|---|---|
| 14 | `test_complaint_identity_is_stable_and_keyword_only` | "Add a stable `id: int` field to the `Complaint` dataclass in `models.py`, placed after the existing `agent_name`, `text` and `timestamp` fields so `Complaint(agent_name, text)` still constructs positionally; give it an automatic default (for example, an auto-incrementing counter) so it is never required as a constructor argument, is unique, and is never reused or recomputed from its position in the list" (**tightenings 3 and 4**, see below) |
| 15 | `test_seed_complaints_have_distinct_ids` | same bullet -- the seed complaints are complaints too |
| 16 | `test_resolve_route_marks_complaint_resolved_and_redirects` | "Add `POST /complaints/{complaint_id}/resolve`... set that complaint's `status` to `\"resolved\"`, then redirect"; "show each complaint's status as a badge reading exactly \"Open\" or \"Resolved\"" |
| 17 | `test_reopen_route_marks_complaint_open_and_redirects` | "Add `POST /complaints/{complaint_id}/reopen`... set that complaint's `status` back to `\"open\"`, then redirect the same way" |
| 18 | `test_resolve_reopen_does_not_reorder_the_board` | "Complaints stay in the same order they appear today -- resolving or reopening a complaint must not move it" |

Checks 1-13 (phases 1-3) are unchanged from `agentclinic-session-phased`;
see that task's own note for their map. Check 14 needed a tightening,
below -- every other check traces to an explicit bullet, not an
inference.

**Tightening 3, 2026-09-10.** The original bullet said `id` must be
"assigned once... unique... never recomputed from its position" but
never said where in the field list it goes.
[The guardrail re-verification](../../../../docs/current/te4-guardrail-reverification-result.md)'s
Engine-01 attempt read that silence permissively: it declared `id`
before `agent_name`/`text`, breaking `Complaint(agent_name, text)`'s
positional contract and correctly failing checks 9 (phase 2's own) and
14. This is the same ambiguity `agentclinic-session-phased`'s own
`QUALIFICATION-NOTE.md` named as unprobed risk for its task, now
observed live and closed here the same way that task's own two
tightenings were: naming the exact field placement so a solver reading
this prompt has no permissive gap left to fall into. Baseline's own
independent phase-4 solution (the route proof's Baseline-01) already
placed `id` after the existing fields unprompted -- this tightening
codifies what one solver already did correctly, for the one that
didn't. `phase-4-resolve-reopen`'s new prompt digest is
`1fc4d9d0e3ed4586` (1753 bytes, was `9ae6b35208360017`, 1619); all
eight qualification checks re-pass unchanged, and `known-broken`
(which places `id` first, with no default at all) still fails the
same way -- it violated this rule before the rule was written down.

**Tightening 4, 2026-09-10.** Tightening 3 fixed *position* but not
*defaultedness* -- it never said `id` needs a default at all. The
[tightening-3 re-verification](../../../../docs/current/te4-tightening3-reverification-result.md)'s
two Engine attempts both read that silence permissively too: each
declared `id: int` with no default, placed after `agent_name`/`text`
(satisfying tightening 3's own wording) but still a required
constructor argument -- so `Complaint(agent_name, text)` failed again,
by a different route. One attempt's `models.py` failed to import at
all (a non-default field following the defaulted `timestamp`); the
other imported, but that attempt separately deleted phase 3's own
already-accepted `POST /complaints` route via a destructive `edit` --
the same mechanism phase 2's own guardrail exists for, recurring here
with no guardrail at phase 4 (corrected in the re-verification result
after an independent review; not itself closed by tightening 4). The
bullet now also requires an automatic
default (an auto-incrementing counter, matching `known-good`'s own
`itertools.count`-based mechanism) so `id` is never a required
argument. `phase-4-resolve-reopen`'s new prompt digest is
`ef0452709399edba` (1841 bytes, was `1fc4d9d0e3ed4586`, 1753); all
eight qualification checks re-pass unchanged, and `known-broken`
(no default, positioned first) still fails the same way it always
has -- this tightening does not change what `known-broken` violates,
only how completely the prompt now rules out the reading it exploits.

**The phase-4 guardrail, 2026-09-10.** A first draft of the
tightening-4 write-up mischaracterized both graded phase-4 rejections
as an id-field problem or a "rewrite." An independent review, and a
third live attempt found while deciding this, corrected that: **3 of 4
graded (non-voided) phase-4 attempts on record destroyed the
already-accepted phase-3 `POST /complaints` route** via one destructive
`edit` that replaces the whole `create_complaint` handler and
`if __name__ == "__main__":` block with the new resolve route in a
single call -- the identical mechanism named in
[the phase-2-board runaway investigation](../../../../docs/current/phase-2-board-runaway-investigation.md),
which phase 2 already carries a guardrail against. Phase 4 carried no
equivalent. Unlike phase 2's version, this one never produced an
unmeasurable, voided runaway -- every occurrence graded cleanly (13/18
each time), which is exactly why it was mischaracterized as ordinary
implementation variance rather than recognized as the same recurring
defect. Closed the same way tightenings 1-4 closed their own gaps: one
bullet, placed before the route-adding bullets, generalized to every
existing route since phase 4 adds two new ones to three that already
exist:

> - When adding the new routes to `app.py`, insert them alongside the
>   existing routes -- do not remove, replace, or rewrite any route
>   that already works

`phase-4-resolve-reopen`'s new prompt digest is `6c264957e8cdd793`
(1993 bytes, was `ef0452709399edba`, 1841); all eight qualification
checks re-pass unchanged. See
[the tightening-4 result](../../../../docs/current/te4-tightening4-reverification-result.md)
for the full correction and the reasoning for closing rather than
leaving this as observed difficulty.

**Corrected 2026-09-10, from a live transcript.** This section
originally said `kw_only=True` was the fixture author's chosen
mechanism, without dictating it as the prompt's requirement — but
check 14 asserted `kw_only is True` directly anyway, which is exactly
the requirement it claimed not to make. The
[route proof](../../../../docs/current/te4-route-proof-result.md#finding-1-baselines-phase-4-failure-looks-like-a-grader-defect-not-a-real-requirement-violation)'s
first live Baseline transcript produced a valid solution — `id`/
`status` as plain fields with defaults placed after the required two,
not `kw_only` — that satisfies the actual behavioral contract
(`Complaint("first", "First complaint")` still constructs) and was
wrongly rejected. Check 14 is corrected to assert only the behavior:
positional construction still works and ids are distinct.
`known-broken` still exists to prove a solver that breaks the
*behavior* (a plain positional field ahead of `agent_name`, with no
default) is caught — that check's actual failure was never
mechanism-specific.

## The extraction

Unlike the sibling task, phase 4's checks were not extracted from an
external depth-3 module -- they were written directly for this task, so
there is no verbatim-AST proof to run. `_contract.py` and `_seed.py` are
reused byte-identical from `agentclinic-session-phased` (verified by
`diff` at authoring time, not by a repo-checked test, since both files
are literal copies with no independent divergence risk).

## The witnesses

Graded by
`tests/integration/test_complaint_lifecycle_qualification.py`, which
applies each patch over `base/`, materializes the grader modules, and
runs the real oracle over the cumulative selection. No row reads a
fixture's contents.

| witness | checkpoint | result |
|---|---|---|
| `checkpoint-1` | 1 (4 checks) | 4/4 pass (reused from the sibling task) |
| `checkpoint-2` | 2 (10 checks) | 10/10 pass (reused) |
| `checkpoint-3` | 3 (13 checks) | 13/13 pass (reused) |
| `checkpoint-4` | 4 (18 checks) | 18/18 pass |
| `known-good` | 4 | = `checkpoint-4`; 18/18 pass |
| `known-broken` | 2 | fails exactly `test_complaint_model_contract_is_preserved` (`id` declared a required positional field ahead of `agent_name`) |
| `known-broken` | 3 | still fails only that check -- not silently repaired |
| `known-broken` | 4 | fails that check **and** `test_complaint_identity_is_stable_and_keyword_only` -- the new phase's own check independently catches the same root cause |
| `regression` | 1-3 | 4/4, 10/10, 13/13 -- untouched |
| `regression` | 4 | fails exactly `test_resolve_reopen_does_not_reorder_the_board` (resolve moves the complaint to the end of the list); no other check disturbed |
| `prompt-faithful` | 4 | 18/18, written as a deliberately different implementation (a lookup helper instead of a loop, a plain function instead of `itertools.count`, reordered template markup) |
| `contaminated` | 4 | grades 18/18, and the contamination scan flags it |

`known-broken`'s failure at checkpoint 2/3 reproduces the exact ambiguity
`agentclinic-session-phased/QUALIFICATION-NOTE.md` named as unprobed risk
for its own task: "a solver that adds an `id` field ahead of `agent_name`
... fails this check even though the field list it names is present."
This task's own design resolves that risk by requiring `id`/`status`
after the two required fields (kw_only or defaulted, either satisfies
it — see the correction above); this fixture proves the resolution is
load-bearing, not merely asserted.

Contamination is a pair, both halves asserted:
`test_prompt_faithful_scans_clean` / `test_the_contaminated_witness_is_flagged`.
The other witnesses also scan clean, though no test asserts that
individually (mirrors the sibling task's own coverage).

## What is still not established

That the task is a **workload**. It is fair and its scope is stated, but
no session has been run against it, so nothing here shows that phase 4
discriminates between engines or that a model can finish it. TE4's own
screen step (not yet authorized) is what would test that -- and only
after this note and its witnesses are accepted.

## Known limitation: `prompt-faithful` does not establish check-blindness

Same caveat as the sibling task, and sharper here: this fixture's author
wrote the checks and the prompt in the same sitting, so the two witnesses
being differently *implemented* proves a requirement is satisfiable more
than one way, not that a solver who has never read the checks lands in
the passing region. Two readings the phase-4 prompt permits but the
checks require a specific answer to, found by review and still unprobed:

1. "reading exactly \"Open\" or \"Resolved\"" -- a solver that renders
   e.g. "OPEN" (uppercase) or wraps the word in extra markup reads the
   bullet's intent but may fail a check written for exact text. Not
   tested here; `_normalized_text`-style whitespace collapsing is used,
   but case folding is not applied to the badge text, unlike link-text
   checks elsewhere in this task family.
2. "must not move it" -- a solver could satisfy this by construction
   (never reordering) or by re-sorting on every request by a stable key
   (e.g., original insertion order, recomputed) and produce the same
   observable result. Both pass; the check cannot and does not
   distinguish the two, and the prompt does not require one over the
   other.

Closing either needs a fresh-author probe or a model probe, not another
fixture.

## Known limitation: contamination's four-line window, inherited

`GRADER_BLOCK_LINES` (`src/satyrn_evals/contamination.py:20`) is 4, same
as the sibling task and not widened here either. Not independently
re-measured for phase 4's specific check bodies; the sibling task's own
finding (idiomatic POST-test assertions can coincidentally match) is
assumed to generalize, not reconfirmed line-by-line.
