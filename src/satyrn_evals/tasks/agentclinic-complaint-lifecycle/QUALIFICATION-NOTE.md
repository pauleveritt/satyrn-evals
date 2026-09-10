# Qualifying agentclinic-complaint-lifecycle

Four ordered development requests over one growing checkout, starting from
the same bare base as `agentclinic-session-phased`. Phases 1-3 are that
task's own phases, reused verbatim; phase 4 is new, scoped by
[the TE4 design](../../../../docs/current/te4-harder-roadmap-design.md).

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
| 14 | `test_complaint_identity_is_stable_and_keyword_only` | "Add a stable `id: int` field to the `Complaint` dataclass in `models.py`, assigned once when a complaint is created, unique and never reused or recomputed from its position in the list" |
| 15 | `test_seed_complaints_have_distinct_ids` | same bullet -- the seed complaints are complaints too |
| 16 | `test_resolve_route_marks_complaint_resolved_and_redirects` | "Add `POST /complaints/{complaint_id}/resolve`... set that complaint's `status` to `\"resolved\"`, then redirect"; "show each complaint's status as a badge reading exactly \"Open\" or \"Resolved\"" |
| 17 | `test_reopen_route_marks_complaint_open_and_redirects` | "Add `POST /complaints/{complaint_id}/reopen`... set that complaint's `status` back to `\"open\"`, then redirect the same way" |
| 18 | `test_resolve_reopen_does_not_reorder_the_board` | "Complaints stay in the same order they appear today -- resolving or reopening a complaint must not move it" |

Checks 1-13 (phases 1-3) are unchanged from `agentclinic-session-phased`;
see that task's own note for their map. No tightening was needed for
phase 4 -- every check traces to an explicit bullet, not an inference.

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
