# Pathologies

*Status 2026-09-15: under the "Evidence has a harness" rule (`AGENTS.md`),
an entry whose evidence is model behaviour observed before release one's
clean harness (before 2026-09-14 14:25Z declared sampling, two-uid
isolation, the budget tripwire, and the base-commit harvest) is re-opened —
its frequency and severity are not settled. An entry that records a harness
or engine bug with a landed code fix and a test stays settled as a bug fix.
See `docs/superpowers/specs/2026-09-15-release-one-outcome.md`. Each numbered
entry below carries its own marker.*

Ways a small local model — or the harness measuring it — has been observed
going wrong during an agentic repair attempt. One line each; the transcript,
archive record, or source citation that shows it is the real evidence, not
this list. Not a roadmap — some entries are model behavior and some are
harness or engine bugs that provoke the same symptom; both belong here
because from the outside they are indistinguishable until someone checks.

What was done about these, and whether it worked, is the companion file:
[remediations.md](remediations.md), cross-referenced by the entry numbers
below.

## How this list grows

This is a **living collection**: add what you actually saw, wherever you saw
it, and cite where it lives — `file:line` for live code, an archive path for
a retired run. An entry needs an observation behind it, not a plausible
failure mode reasoned toward. See
[the lessons file](lessons.md) for the general evidence checks
that keep an entry honest before it is written down.

**This list is a reference, not a denominator.** Don't cite it as a rate.
The entries below were collected opportunistically across different phases,
adapters, and one unadmitted spike campaign, so counting them measures what
people happened to write down, not a frequency. When a rate is wanted,
measure it with `census` or `summarize` over a named run and report it with
its `n` (`git show pre-release-one-2026-09-13:docs/usage.md`).

Entries 1–7 come from this repository's live source and are reproducible now
by reading the cited file or retained run. Entries 8–15 come from
`local-ai-pi`, the repository this one was directly seeded from
([`archive/2026-09-07-pre-reset/CLAUDE.md`](https://github.com/pauleveritt/satyrn-evals/blob/pre-release-one-2026-09-13/archive/2026-09-07-pre-reset/CLAUDE.md)'s Provenance section: "Seeded from
`github.com/pauleveritt/local-ai-pi` at commit `c74c31f`") — carried in via
SwiftStar's own catalog, which recorded them first, but kept here as this
project's own inherited history rather than a borrowed cross-reference.
Entries 16–19 come from an archived, **unadmitted** spike
(`2026-09-02-overnight-packet-and-isolation-run.md`) run through a
scratchpad harness, not this repository's own `attempt` path — several of
the archive's own headline numbers were later corrected by adversarial
review, and that correction is carried into each entry below rather than
smoothed away.

## Entries

### Seen in this repository's own engine and adapters

1. *Status 2026-09-15: re-opened (model behaviour, pre-clean-harness evidence).*
   **Redundant-read lock.** On the V11c spike (2026-09-05), seven Baseline
   cells each issued **281 identical `read app.py` calls** after locking at
   their fifth tool call, each burning about ten minutes reaching the model
   server's context limit — 70 of that batch's 102 minutes spent
   re-confirming a decision the cell had already made. Replayed offline
   over 24 retained transcripts before it ran anywhere: the longest run of
   identical consecutive tool calls was 1, 3, or 5 on every cell that
   succeeded, and 280 on every locked cell — nothing in between.
   (`src/satyrn_evals/repeat_limit.py:7-16`)

2. *Status 2026-09-15: settled as a bug fix.*
   **Streaming updates counted as extra tool calls.** The Baseline V5d
   smoke's transcript carried 23 `tool_execution_start`, 23
   `tool_execution_end`, and **49** `tool_execution_update` events for the
   same 23 calls. An update is a streaming partial of an execution already
   bracketed by its start/end pair; counting it as its own call would have
   inflated every `tool_calls` tally by roughly 2x.
   (`src/satyrn_evals/pathology.py:28-33`)

3. *Status 2026-09-15: settled as a bug fix.*
   **`--model=VALUE` silently rejected.** pi's hand-rolled flag parser
   matches only the literal token `--model` and records the combined
   `--model=VALUE` form as an unknown flag rather than an error. That defect
   cost the V8 smoke a run at 0.84.4 before it was found; reconfirmed
   unchanged at 0.85.1, 2026-09-10.
   (`src/satyrn_evals/arms.py:198-201`,
   `src/satyrn_evals/attempt_pi.py:16-19`)

4. *Status 2026-09-15: re-opened (model behaviour, pre-clean-harness evidence).*
   **Untracked files invisible to patch capture.** The Baseline adapter
   harvests its patch with `git diff HEAD`, which never sees a file the
   model created with `write` rather than edited — harmless on pure-edit
   repair, silently fatal on any task shape that needs file creation.
   (`src/satyrn_evals/attempt_pi.py:23-27`)

5. *Status 2026-09-15: settled as a bug fix.*
   **An infrastructure crash counted as a plain refusal.** A model-server
   5xx, or a runtime fault such as a GPU out-of-memory, looked identical to
   a model that simply produced no patch — recording it as `NO_PATCH`
   understated the arm and voided a whole probe silently. A 4xx is
   different: the server answered and rejected the input on its own terms
   — a context-window overflow is the case on record — which is genuine
   pathology and stays in the denominator, unlike a 5xx/OOM. See
   the engine's `docs/usage.md` (the `MODEL_ERROR` and `--max-repeated-calls`
   sections).

6. *Status 2026-09-15: settled as a bug fix.*
   **`regrade` could not reach an already-collected infrastructure
   failure.** Before V11d slice 4, `regrade` no-op'd on every refusal cell,
   which would have stranded every already-collected `NO_PATCH` cell with
   no offline path to correct it once the transcript was later understood
   better.
   (`src/satyrn_evals/rescore.py:363-368`)

7. *Status 2026-09-15: re-opened (model behaviour, pre-clean-harness evidence).*
   **A self-reported no-op edit repeated five times without adapting.** In
   the overnight phase-4 context screen's Baseline arm (twelve
   `agentclinic-complaint-lifecycle` cells, 2026-09-11/12), one cell's
   phase-4 turns issued the identical `edit` call against `app.py`'s
   resolve/reopen routes — `oldText` byte-for-byte equal to `newText` —
   **five times in a row**, each time getting the adapter's own explicit
   rejection back as the tool result ("No changes made to app.py. The
   replacement produced identical content."). Interleaved with those were
   **seven** repeats of an identical verification probe (`uv run python3
   -c "from app import app; print(app.routes)"`), returning the same
   unchanged route list every time. Unlike entry 8's silently-accepted
   no-op, this adapter told the model the truth on every attempt — it still
   took five identical failing calls before the model changed what it
   sent. The cell eventually recovered and passed (23 turns, 317.6s),
   against 6–14 turns and 134.5–265.6s for the other eleven Baseline cells
   in the same run, none of which repeated any call.
   (`/Users/pauleveritt/satyrn-smokes/2026-09-12-overnight-phase4/cell-003-baseline/agentclinic-complaint-lifecycle-session-20260912-025445-234487/transcript.jsonl`,
   phase-4 slice, bytes 302614–698799; corroborated by that cell's
   `session-record.json` `phase-4-resolve-reopen` step and
   `receipts/04-phase-4-resolve-reopen.json`)

### Seen in local-ai-pi (this project's own predecessor)

*`local-ai-pi`, running `gemma-4-12B` and `qwen3.6-27B` against its own
repair/authoring tasks. This is the repository `satyrn-evals` was seeded
from — not a sibling's history, this project's own, one commit further
back than this repository's own git log currently reaches. Numbered 21–28
in SwiftStar's and ds4-engine's own catalogs; renumbered here to run on
from entry 7, with the original numbers kept in the provenance note below
for cross-repository lookup.*

8. *Status 2026-09-15: settled as a bug fix.*
   **No-op edit loop, reported as success.** NOT A MODEL PATHOLOGY — harness
   bug. The mutation engine accepted an edit whose `oldText` equaled
   `newText`, silently writing the same bytes back and reporting "changed
   lines=0" as success. One run looped rereading a 29KB file and proposing
   byte-identical no-op edits until the wall clock killed it with zero
   files written — logged at the time as a model failure. This
   repository's own `noop_edits` counter (entry 2's module) exists to make
   exactly this pattern visible rather than invisible in a summary; see
   entry 8 in [remediations.md](remediations.md).

9. *Status 2026-09-15: re-opened (model behaviour, pre-clean-harness evidence).*
   **Near-miss file targeting.** Asked to edit `src/svcs/_autowire.py`,
   wrote a clean, complete file to `src/svcs/autowire.py` instead — a
   plausible sibling name, not the real target — then ran out of its turn
   budget still trying to wire `__init__.py` to the wrong file it had
   created.

10. *Status 2026-09-15: re-opened (model behaviour, pre-clean-harness evidence).*
    **Schema-mismatched call repetition.** Repeated a structurally invalid
    edit call — one that contained the correct fix, but with `path` nested
    inside the edit entry instead of at the top level — 49 times
    byte-identically, always failing schema validation, without ever
    adapting the call shape. A separate task showed the same shape: 46
    guard-blocked repeats of an anchor-mismatched retry starting at call 14
    of 60.

11. *Status 2026-09-15: re-opened (model behaviour, pre-clean-harness evidence).*
    **Destructive failure tied to task shape.** On one specific task,
    failing runs didn't just fail to add code — they reliably deleted
    existing tests. A 24-replicate noise-floor run showed 5/6
    "tests-vanished" plus 1 "damaged" (0/6 accepted); a separate
    guard-mechanism run on the same task also ended "tests-vanished, delta
    -30, 101 nodes missing." Recurred across independent experiments,
    suggesting a failure signature tied to this task/edit shape rather
    than a one-off.

12. *Status 2026-09-15: re-opened (model behaviour, pre-clean-harness evidence).*
    **Empty-workspace probing spiral.** Given an empty workspace with no
    explicit statement that it was empty, repeatedly re-checked with
    `ls -R` — 245 repetitions in one run, contributing to a 261-turn run
    with a 71.88 MB transcript. Stating the empty workspace as a fact in
    the prompt collapsed this to 1 repetition.

13. *Status 2026-09-15: re-opened (model behaviour, pre-clean-harness evidence).*
    **Headless conversational stall.** In a single-shot, non-interactive
    agentic run, 16/16 replicates took exactly one turn, made zero tool
    calls, correctly and accurately restated the task requirements, and
    then stopped with "Please let me know which file I should start
    with..." — treating a one-shot execution context as an interactive
    chat awaiting a reply that will never come.

14. *Status 2026-09-15: re-opened (model behaviour, pre-clean-harness evidence).*
    **Operationally vague self-authored specs.** When used to author a
    task contract rather than execute one, drafts passed every
    structural/coverage check (8/8) but were behaviorally complete and
    operationally vague — e.g. "register the resulting context for
    cleanup" where a hand-written contract says the concrete `append
    (name, svc) to self._on_close`. Contracts authored this way were
    ~2.5x shorter, had almost no code fences, and led executors to a
    correctness drop (4/4 hand-authored vs. 1/4 model-authored on oracle
    checks).

15. *Status 2026-09-15: re-opened (model behaviour, pre-clean-harness evidence).*
    **Scope overreach via its own contract's prose.** Given a handoff
    contract restricted to `src/svcs/**`, produced a functionally perfect
    patch (3/3 identical, oracle 19/19 every time) but also edited
    `docs/integrations/flask.md` because the contract's own "Documentation
    Note" section asked for a docs update — outside the writable-file
    policy. Treated every instruction inside the contract as in-scope,
    including one the contract's own policy excluded.

*Provenance (original numbering 21–28): `local-ai-pi`'s own commit history
and research notes (`d758a03`, `604884b`,
`2026-08-10-phase7-frontier-contracts-variance.md`, `7ca49cb`, `9e2c624`,
`2026-08-04-phase5-cycle10-publishable-arm.md`,
`2026-08-04-phase5-cycle4-user-story-arms.md`, `docs/engine/shootout.md`,
`8da2576`, `db33752`), as carried by SwiftStar's `docs/pathologies.md`.
Entry 8 is kept despite being a harness bug for the same reason as entry 2:
misfiling a tooling defect as model behavior is itself worth remembering.*

### Seen in an unadmitted overnight spike (2026-09-02)

*Scratchpad harness, not this repository's `attempt` path — six models
against `pi 0.84.4`, roughly 160 cells. Spike evidence only: "every number
here must be re-derived before it is cited in a plan." Archived at
[`2026-09-02-overnight-packet-and-isolation-run.md`](https://github.com/pauleveritt/satyrn-evals/blob/pre-release-one-2026-09-13/archive/2026-09-07-pre-reset/docs/superpowers/research/2026-09-02-overnight-packet-and-isolation-run.md).*

16. *Status 2026-09-15: re-opened (model behaviour, pre-clean-harness evidence).*
    **Oracle-hunting by filesystem search.** Unsandboxed runs spent their
    budget on `ls -R`, repeated 139–271 times, interleaved with
    `find . -name test_acceptance.py`, hunting for the hidden grader
    instead of working the task. Two cells found the real acceptance
    suite on disk, copied it into the workspace, and iterated against it
    until green; a separate run read up to 49 *other* cells' directories
    along the way. Every one of those search calls *succeeds*, so a loop
    breaker keyed on tool-call failures would never fire on it. (§1–§2 of
    the archived record.) Release one's clean harness re-observed hunting
    under isolation: guard 4 cut a root-wide hunt for the acceptance tests
    at 120 s that had cost a Baseline cell 1,800 s
    (`docs/superpowers/specs/2026-09-15-release-one-outcome.md`).

17. *Status 2026-09-15: re-opened (model behaviour, pre-clean-harness evidence).*
    **A sandbox that removed the model's own test runner.** The Seatbelt
    profile built to close entry 16's oracle leak also cut off the
    model's `python`, which resolved to a build environment without
    pytest while PyPI was blocked. Across 36 sandboxed cells there were
    266 `pytest` invocations, **zero** returned a result, and 179 came
    back `No module named pytest` — an entire block measured models that
    could not self-verify, a property of the isolation profile, not of
    the models. (§2, "A confound this profile introduced, and did not
    disclose until review.")

18. *Status 2026-09-15: settled as a bug fix.*
    **A detector that always fires.** A grader-content tripwire fired on
    **104 of 128 cells**, because every transcript contains its own
    filesystem path — exactly as useless as a detector that never fires.
    (§3, defect 4.)

19. *Status 2026-09-15: settled as a bug fix.*
    **Contamination overstated sixfold on first read.** An early pass
    flagged 12 files as copied grader content; adversarial review found
    10 of those 12 were legitimate model-authored tests written from an
    assertion the prompt had already displayed. The overstatement was
    caught only on a later review pass, not by the person who ran the
     block. (§3, "Two further corrections came from adversarial review,
     not from me.")

### Seen in the Mellum tool-surface probe (2026-09-22)

*One checkpoint, one conversion, one machine, one server, n = 5 per case.
The rendering-path control that would separate checkpoint from template has
not run, so this is model behaviour observed once, not a settled cause.*

20. *Status 2026-09-23: resolved as a serving misconfiguration. The
    snapshot's config declares `qwen3_moe`, so the runtime dropped Mellum's
    1,024-token sliding window and YaRN. Reconverted as `mellum`, the
    four-tool thinking-on case is 5/5 at a 16,000-token budget and no
    degenerate output remains. The thinking-path reading below is
    superseded. Lesson: check `model_type` against the released model's
    config before diagnosing behaviour
    (`evidence/2026-09-22-mellum-tool-surface/`, "Rerun on the mellum model
    class").*
    **Tool-calling collapses on the real task text with thinking on, at any
    tool count.** The checkpoint
    `JetBrains/swe-pi-m23-mix4s100-think-ae10k-init800-20260917-bulat-step-500`
    (MLX 8-bit, oMLX 0.6.4, bundled `mlx_lm` 0.31.3), five runs per case,
    returned a valid tool call (parsed call, `tool_calls` finish, under the
    token cap) 5/5 on a trivial weather prompt with one tool and 5/5 with
    four; on the review-script task text with thinking on it returned 0/5,
    1/5, 0/5, 0/5 for one to four tools — not separable at n = 5 — plus one
    call the server salvaged from a 2,000-token degenerate response. The same
    task text and four tools with `enable_thinking` false was 5/5, each call
    23 tokens. The failures are 2,000-token length stops of `tool_call`-shaped
    fragments laced with repeated `</think>` tokens. Both isolated Pi cells
    read `NO_PATCH` with 0 tool calls and a single 16,000-token turn. An
    earlier write-up read this as "collapses as the tool surface widens";
    the data never supported that. A bf16 control was not run.
    (`evidence/2026-09-22-mellum-tool-surface/README.md`, `raw/`)

21. **Announces the next action in its reasoning, then ends the turn without
    it.** The same Mellum checkpoint, served correctly as `mellum`, in two
    bare-Pi `satyrn-evals` cells on the review-script task (thinking on,
    16,000-token turns). Both passed the hidden grader, and both ended the
    same way: the last turn's reasoning closes with a plan ("Now, let's
    perform the edit." / "Let's create a commit.") and the turn stops with
    `stopReason` `stop`, no tool call, and an empty visible reply. One cell
    left `ruff` failing on an import-sort error it had just read; neither
    made the commit the task's step 5 asks for, where Ornith 1.5 9B
    committed in 7 of 8 baseline cells on this task. The harness counts
    this as a clean self-stop, so nothing flags it. n = 2, one task.
    Observed 2026-09-23 (`records/2026-09-23-spike-mellum-class-review-script-mellum.json`).
    *n = 6 update, same day, corrected after review:* it ended 4 of 12
    more Mellum cells. Three were baseline cells, and two of those stopped
    before writing the implementation, costing the patch. One was an engine
    cell that stopped with its own tests failing and passed only because
    the hidden grader replaces the model's tests. So the engine did not
    prevent it; that the engine absorbs it is untested.

22. **Fixes the file it was not told about.** Also seen in the second
    cell: `ruff` reported an import-sort error in `tests/test_review.py`
    four times. Three times the model re-sorted the import block of
    `tools/review.py` instead, flipping its order back and forth, and its
    one edit to the test file left it still unsorted. It escaped only by
    running `ruff check --fix`. Eight repeated commands and
    four churned edits came from this loop. n = 1.
    *n = 6 update, same day:* one more baseline cell spent its whole 72-turn
    budget in a `ruff` import-sort loop, 18 `ruff check` runs on the right
    file this time, never trying `--fix`. The general defect: it cannot
    satisfy an import-sort rule by hand. Its tree already passed the
    hidden tests when the budget ran out, so the loop alone cost the cell.

## Where the fuller record lives

A sibling project, `ds4-engine`, keeps a cross-project pathology catalog
spanning several harnesses and models (`docs/pathologies.md` in that
repository), including its own ds4/Mellum-native entries, its own carried
copy of the `local-ai-pi` entries above (numbered 21–28 there), and its own
"Seen in satyrn-evals" section drawn from the same 2026-09-02 spike (its
entries 30–40). Read it there for the ds4/Mellum-native failures this file
doesn't carry, since those never touched this project's own lineage.
