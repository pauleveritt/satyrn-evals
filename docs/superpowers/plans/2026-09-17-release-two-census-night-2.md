# Release two R0 — census night 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status: written 2026-09-17 against evals `release-one` at `b293448`.** Nothing here was executed: no model was run, no record written, nothing under `/Users/Shared/satyrn-cells` or `~/satyrn-runs` touched, nothing written under `docs/results/` or `docs/reviews/`. Six tasks. Task 1 ends in a **STOP** for the maintainer's pick; Task 5 is a whole-path review by someone who did not implement.

**Goal:** Put a third medium-build census task, a classifier that reads the actual at the pre-registered 32,000-token / 48-turn line, and an offline per-cell decode rate into the tree, then freeze four Baseline records and one launch script so the maintainer can run fifteen cells on a quiet machine.

**Architecture:** One attended survey of the Phase 2a/2b/2c plans that proposes two build-shaped candidates and stops; one cut of the chosen candidate with the R0 §1.2 validity check run exactly as night 1 ran it; two classifier changes (the actual read at the line, with the 48k verdict kept beside it; a `decode_tok_s` column attributed from the oMLX server log by the cell's time span) with night 1's five outputs regenerated under each; a whole-path review before anything is frozen; then four records, `scripts/census_night_2.sh`, an extension of the frozen-record guard, and the operator checklist. No harness change, no launcher change, no change to the five night-1 task trees.

**Tech Stack:** Python 3.14, uv, pytest, ruff, just, git. Reused evals code: `satyrn_evals.census_classify`, `satyrn_evals.budget.UsageCounter`, `satyrn_evals.cell_evidence.collect_evidence`, `satyrn_evals.qualify`, `satyrn_evals.manifest`, `satyrn_evals.task_tree.tree_digest`, `tools/cut_task.py`, `tools/provenance.py`, `scripts/preflight_settings.py`, and — **by path and unmodified** — `evidence/2026-09-15-finishing-counterfactual/counterfactual.py`.

**Spec:** `docs/superpowers/specs/2026-09-17-release-two-census-night-2-design.md` (approved 2026-09-17, four decisions in its section 8). Bound by `docs/superpowers/specs/2026-09-15-release-two-r0-constraints.md` and by the census design `docs/superpowers/specs/2026-09-15-release-two-census-design.md`, whose harness, budget line and classification scheme this night reuses unchanged. Section numbers below are the night-2 design's unless another spec is named. The night-1 plan `docs/superpowers/plans/2026-09-15-release-two-census.md` and the Phase 2a/2b/2c plans are evidence for a named question, never guidance.

---

## Rulings

Each is a decision the spec left open, with the reason it was decided that way and what it costs if it is wrong.

1. **The survey's rejection criteria are these seven, applied in this order, and every rejected candidate is reported with the criterion that rejected it.** A plan section is rejected when: (a) it is already cut — the six specs in `tools/task_specs/`; (b) it is not build-shaped — it modifies an existing module's behaviour rather than adding one source module plus its test module, so the generator has no clean broken stub to strip back to; (c) its hidden-test count, **measured** by collecting the plan section's test module at the `good` commit, is outside 15–20; (d) its public suite at the `base` commit does not finish in under 40 s, **measured**; (e) the plan section creates files outside its own `Files:` list (a doc, a `PROVENANCE.md` row, a `ROADMAP.md` edit), which the grader reads as non-source paths; (f) it needs a model, the network, a GPU or the `satyrn-cell` uid to test — the cell has none of them; (g) its source module is already the source module of a cut census task, because two census tasks over one module measure the same prompt surface twice and the census page's build-task denominator would double-count the tier. Reason: (a)–(b) and (f)–(g) are hard properties of the cut and the cell, so they are cheap and decidable before any measurement; (c)–(d) are the spec's own size class and must be measured rather than estimated, since a mis-sized task changes what "medium-build" means in the claim table. Reporting the rejects, not only the survivors, is what lets the maintainer see the whole field before picking. **Cost if wrong:** a viable candidate is dropped and the third build task is weaker than it could have been; the survey's reject list makes that recoverable in one sitting.

2. **A prompt whose structural facts live only in the plan's stripped code is not rejected by the survey; it is flagged as a predicted validity risk and decided by the check.** R0 §1.2 is an empirical gate, not a guess, and the spec already fixes the remedy: a candidate that fails validity gets a recorded prompt edit **only for a fact the plan's stripped code stated**, otherwise it is dropped and the second proposal is cut. **Cost if wrong:** one wasted validity run, which costs a cloud dispatch and no GPU.

3. **`actual_32k` ignores `tripped_verdict` entirely: it is `verdict == "pass" and output_tokens <= 32_000 and turns <= 48`.** A tripped cell's `verdict` is `null` by the census design's own rule (night-1 plan Ruling 2: the tripped grade is never a pass and never moves a rate), so a tripped cell is not actual at the line no matter what the torn-down worktree graded. This is not a loophole but the honest reading: the tripped verdict describes a worktree state reached **at the 48,000-token teardown**, so by construction it cannot be a delivered pass inside a 32,000-token line, and folding it in would print the harness's non-delivery as a delivery, which BRIEF invariant 3 forbids. `tripped_verdict` stays its own column, beside the two actuals. **Cost if wrong:** a cell whose torn-down worktree would have graded pass is counted as a not-pass at the line and so is eligible to be *rescued* by the counterfactual — the direction that can only overstate the remedy, which is why the `tripped` column is printed on the same row and the census page reads them together.

4. **`code` is not part of `actual_32k`.** Night 1's `actual` was `code == "OK" and verdict == "pass"`; the line reading drops the code term because only an `OK` cell ever carries a graded `verdict` (every `BUDGET_EXCEEDED`, `COMMAND_TIMEOUT`, `NO_PATCH` and `REPEAT_LIMIT` cell has `verdict: null`), so the term is redundant and a redundant term invites a reader to think it is doing work. A fixture asserts a tripped cell with `tripped_verdict == "pass"` and `verdict is None` is not actual at the line. **Cost if wrong:** none that is silent — a code that ever ships a graded verdict would show up as a row whose `code` is not `OK` and whose `verdict` is `pass`, which the table prints side by side.

5. **The mechanical class flags move to the line too: `Facts` gains `passed_at_line` and `capability`/`budget`/`finishing` are computed from it, not from the 48k verdict.** Without this, `classes.md` would print `finishing=False` beneath a cell that the tally on the same night counts as a rescue — night 1's `selfhost-run-record-gate` 275888 passed at turn 55 with 30,444 tokens, which is outside the line by turns while its pass **state** (turn 16, 13,809 tokens) is inside it. Two readings of the same line in one output directory is the contradiction the reviewer would have to untangle by hand. Reason for making it a ruling rather than a silent fix: it moves numbers in night 1's regenerated `classes.md` beyond "the tally and the new columns", and the four cells it moves are named in Task 3 Step 8 so the diff is predicted before it is produced. **Cost if wrong:** the eight class columns stay the reviewer's either way (they are empty in the file); only the `evidence:` line beneath a row changes, and it now agrees with the tally above it.

6. **The regenerated tables must differ from the committed ones in exactly the predicted places, and a difference anywhere else stops the task.** Task 3's diff is confined to: `table.md`'s new `verdict@32k` column; `cells.json`'s `actual_32k`/`actual_48k`/`run1`/`run2`/`unmeasured`/`tallies` and the header's new `night` key; `classes.md`'s `evidence:` lines for the four named cells. Task 4's diff is confined to the two new decode columns in `table.md`, the five decode keys in `cells.json`, and `decode_tok_s=` in `classes.md`'s evidence lines. Reason: a regeneration that quietly moved a turn count or a pass turn would mean the instrument changed under the night-1 reading that STATE.md calls complete, and the fix-wave ledger's own lesson is that cross-task effects are invisible to per-task gates. **Cost if wrong:** none; the check is a `git diff` and it is cheap.

7. **A cell's span for the server-log attribution is `[attempt directory stamp, mtime(attempt.json)]`, and the log cannot say which cell a completion inside it belongs to.** The attempt directory name carries a microsecond UTC stamp and `attempt.json` is written last (night-1 plan Ruling 8), so the pair already brackets the cell with no new clock. **The limit, stated plainly:** an oMLX completion line carries a timestamp, a model, tokens, seconds, prompt size, finish reason and `max_tokens` — and **no session, request or cell identifier**. At k = 3 up to three cell spans overlap, and a completion inside the overlap is attributed to every one of them. So `decode_tok_s` is *the machine's decode rate while this cell ran*, shared with whatever else was decoding, and never the cell's private stream. That is exactly the quantity the contention question asks for — the design says "contention is a number on the row" and "the decode-rate column is how the census page shows whether the precondition held" — but the column must never be read as per-cell throughput. A companion `decode_overlap` column counts how many of the night's cell spans intersect this one, so the sharing is a number rather than an inference. **Cost if wrong:** a reader takes an overlapped row for a single stream; the overlap column and the header note are there to prevent it, and the census page repeats the sentence.

8. **`decode_tok_s` is token-weighted: `sum(tokens) / sum(seconds)` over the attributed completions.** A per-completion mean gives a 32-token completion the same weight as an 8,000-token one, and a short completion's rate is dominated by scheduling and prefill rather than decode; the question "how fast did tokens come out while this cell ran" is total tokens over total decode seconds by definition. It also matches the headline run 2 committed (`run-2/serverlog.py` prints `tot_tok/tot_sec` as "mean rate"), so the census's number and the counterfactual's are the same statistic. The per-completion **median** is carried beside it as `decode_median_tok_s` in `cells.json`, because `run-2/q3stats.md`'s bins are medians and a reader comparing the two needs both. **Cost if wrong:** a cell whose span holds one enormous completion and many tiny ones reads faster than its typical turn did; the median column is the check on that, and both are in `cells.json`.

9. **Server-log timestamps are naive **local** time; attempt directory stamps are UTC; both are converted to epoch seconds before they are compared.** The log writes `2026-09-16 18:54:37,741` with no offset and the machine's clock is `EDT-0400`, while `launch.json` records the same sitting's start as `18:29:41+00:00` and the attempt directory as `...-20260916-182941-...`. Parsing is `datetime.strptime(...).astimezone()` — naive means "this machine's local time" — and the tz offset actually used is written into the output header so a recomputation on another machine, or after a DST change, is visibly a different reading rather than a silently different one. **Cost if wrong:** every attributed window shifts by hours and almost every cell reads "no completions in the span", which is loud, not silent.

10. **A null `decode_tok_s` always carries a reason string, and there are four of them:** `"no completions in the cell's span"`; `"attributed completions report no decode seconds"`; `"no attempt stamp in the directory name"`; `"attempt.json is missing or unreadable"`. Reason: the spec asks for "null with a stated reason when the log has no completions in the span", and a bare null cannot distinguish a quiet machine from a rotated log from an unreadable cell. **Cost if wrong:** none; the reason is one string in `cells.json` and the table prints `-` with the reason available beside it.

11. **Night 2's classifier outputs go under `evidence/2026-09-17-census-2/<task>/`, never the night-1 directory, and the driver refuses to overwrite a `<task>/cells.json` written for a different night.** `classify.py`'s `--out` defaults to its own directory, `evidence/2026-09-16-census/`; three of night 2's four tasks have the same names as night 1's, so a morning command that forgot `--out` would overwrite three committed tables with three-cell nights and destroy the reading STATE.md calls complete. The guard is the cheap half: `cells.json`'s header gains a `night` key and `main` refuses when the target exists with a different one. Reason: this is precisely the class the fix-wave ledger names — a cross-task effect no per-task gate can see — and the maintainer's record-drift finding is the precedent for making it mechanical. **Cost if wrong:** a deliberate re-classification of the same night into the same folder still works (same `night`), and any other overwrite needs the operator to move or delete the folder first, which is the intended friction.

12. **All four records chain from the one committed result `records/2026-09-16-census-selfhost-speed-probe.result.json`; none chains to another night-2 result.** The spec says all four are "chained from" that result, and the flat chain is what makes section 4's reach rule true: a record the night does not reach stays *launchable* later, because its `previous_result` is already committed, whereas a serial chain would leave an unreached record pinned to a result that does not exist. Night 1's script still commits each result before the next launch and this plan keeps that, not because the chain needs it but because a result committed in the night is a result that cannot be lost. **Cost if wrong:** the four records do not record an internal ordering; the script, the log and the results' timestamps do, and section 4's table is the authority on order.

13. **`max_minutes` is 240 on all four records.** The gate is `command_backstop_s + 300 <= max_minutes * 60`, so 4,800 s needs at least 85 minutes; the derived per-cell wall clock is `4800 + 300 = 5,100 s`, so record 1's n = 6 at k = 3 is two waves (10,200 s ≈ 170 min) and records 2–4's n = 3 is one wave (5,100 s = 85 min). 240 holds record 1's two waves with room for the resume a capped record takes, is uniform across the four so no reader has to ask why one differs, and is well inside `batch`'s 720-minute cap. **Cost if wrong:** a record that needs a third wave is capped and resumed by the script's `S -eq 4` loop rather than lost.

14. **The script runs the four records in section 4's order — candidate, run-record-gate, cell-loop, speed-probe — and a non-zero launcher exit stops the remaining records.** The candidate is first because it is the night's question; the replacements follow in the order the spec tabulates. A record the night does not reach is left unlaunched, uncommitted and unmodified: nothing is re-issued, nothing is resumed silently, and launching it later is a fresh, attended sitting in which the maintainer re-runs the script (which skips every task whose result is already `complete`) and records that decision in the night's ledger. The launcher's own `CAPPED` resume loop stays: it resumes *a record the night reached*, inside one sitting, which is a different thing from reaching a record it never started. **Cost if wrong:** the night ends with fewer than fifteen cells and says so; the design's precondition paragraph already contemplates launching only record 1.

15. **Record 1's `authority` names the approval; records 2–4's `authority` is the spec's replacement sentence verbatim.** The spec fixes 2–4's text so the caveat that the originals stand in their denominator travels **with the record** rather than only in a page, and a reviewer can grep for it. The section 8 approval covers all four and is cited in record 1 and in the ledger. **Cost if wrong:** a reader of record 2 alone sees the replacement caveat but not the approval date; the ledger and the spec carry it, and the `decision_rule` (identical on all four) names the spec that decides outcomes.

16. **The whole-path review runs after the classifier changes and before any record is written, and every finding it raises becomes a default-tier test before the records are frozen.** The fix-wave ledger's own note — "`just gates` excludes integration, so this regression was invisible to every per-task gate; it is exactly the class the whole-path review exists to catch" — is the reason it is a task and not a step. The reviewer did not implement Tasks 2–4. **Cost if wrong:** the review costs one dispatch and delays the night by an hour.

17. **The harness has one selectable agent model. If it is not the design's named instrument, that is recorded and the work continues.** Night 1 could not select Sonnet for the R0 §1.2 validity solver and the maintainer ratified `deepseek-v4-flash` as the instrument on 2026-09-16 (fix-wave ledger, Task 5; procedure spec's dispatch paragraph). Task 2 records `validity.by` as whatever model actually ran and repeats the maintainer's standing caveat in the night-2 validity README. It does **not** stop: the ratification is on the record. A harness that could not honour a role and had *not* been ratified would be a stop. **Cost if wrong:** the candidate's certification is read as slightly weaker than a Sonnet run, exactly as night 1's four are.

18. **Nothing in this plan changes `counterfactual.py`, the arms, the launcher, the five night-1 task trees, or `census_night.sh`.** The pre-registered instrument is loaded by path and unmodified (night-1 plan Ruling 7); the census reads the same instrument run 1 and run 2 read. The new actual is computed in the driver and in `census_classify`, both of which are the census's own code, and handed to `cf.counterfactual_pass`, `cf.unmeasured_reasons` and `cf.change` through their existing `actual` parameters. **Cost if wrong:** none — the alternative (editing the pre-registered script) would make the census a different instrument from the one whose numbers it is compared with.

19. **Feeding `actual_32k` to `cf.unmeasured_reasons` will move run 1's unmeasured list, and that is correct.** That function withholds a rescue as `unverified-rescue` only when `not actual and trigger_verdict == "pass" and unverified_bash_turns`; more cells are now `not actual`, so more can be withheld. Run 1's pre-registered conservatism is the point of keeping it beside run 2. **Cost if wrong:** run 1 under-reports rescues, which is the direction it was pre-registered to err in, and run 2 is printed on the next line.

---

## Global Constraints

- **Roles: Sonnet implements each task, Opus reviews it, Sonnet re-reviews the fix diff (scoped). No haiku. Fable only if the maintainer names it.** One fresh implementer per task; the controller blocks on every dispatch and nothing runs in the background.
- **No model inference during building, and no network.** No `launch`, no oMLX request, no GPU. Task 2's validity solver is a cloud model working from text and is the only agent that writes code from a prompt; it never touches the GPU.
- **Nothing under `/Users/Shared` is read or written; `~/satyrn-runs` and `~/.omlx/logs/` are read-only; nothing is written to `/tmp` or `/private/tmp`.** Scratch work goes in the session scratchpad (`SCRATCH`). Grade roots go under `$HOME/satyrn-census-grades/`.
- **Tests are verified in a scratch clone under the scratchpad, never in the main checkout.** `git clone --branch release-one "$EVALS" "$SCRATCH/evals" && cd "$SCRATCH/evals" && uv sync`.
- **`just gates` exits 0 at the end of every task**, run in the evals tree, reading the exit code and never piping a gate. **The integration tier is not in `just gates`** and is checked once at the end of the last task: `uv run pytest -m integration`. Known failing before any of this: the Xcode-license git integration rows (`/usr/bin/git` needs `sudo xcodebuild -license accept`); they are in the marked integration tier.
- **Every new file gets a `PROVENANCE.md` row** (`uv run python tools/provenance.py new <paths>`); `just gates` fails without one.
- **Docs caps:** `docs/superpowers/specs/*.md` ≤ 400 lines, `docs/results/*.md` ≤ 120 lines (none written), `ROADMAP.md` ≤ 150 lines. Plans are uncapped.
- **The default test tier uses no model, network or subprocess**; `tests/conftest.py`'s audit hook enforces it. Every refusal test has a sibling success test (BRIEF invariant 5). Every new rule is tested in both directions. **Every review finding becomes a default-tier test** (the 2026-09-16 fix wave's standing lesson).
- **Grade from hook-written evidence, never stdout or exit status.** Count events from `tool_execution_start`, one per call; never `grep -c`.
- **Commit per task on evals `release-one` with explicit paths only.** Never `git add -A`, `git add .`, `git commit -a`, `--amend`, merge or push. A task whose gates are red is not committed. End every commit message with the session's attribution trailer.
- **A stop is a stop.** An agent stops at an underspecified task, a task that fails acceptance twice, a red gate whose fix is not in this plan, or any step that wants inference. **A harness that cannot honour a named role is a stop** unless the substitution is already ratified (Ruling 17).
- **Digests that must not move:** all five night-1 census task trees. `tests/test_census_records_frozen.py` fails the gates if one does; a fix that moves a task tree must re-issue every record that pins it (the maintainer's 2026-09-16 ruling).
- **Census night-2 constants, verbatim from the spec:** per-turn cap 16,000 tokens (unchanged, served); token budget 48,000; turn budget 72; **backstop 4,800 s**; k = 3; n = 6 for the candidate and n = 3 for each replacement; four records; Baseline arm only; `--purpose admission`; `--mode batch`; isolated; `--max-minutes 240`; stop rule "established infrastructure failure only"; fifteen cells; estimated five hours.
- **`CANDIDATE`** is the task name the maintainer picks at Task 1's STOP and Task 2 cuts. It appears in `qualify.CENSUS_TASKS`, in `tools/task_specs/<CANDIDATE>.json`, in `records/2026-09-17-census2-<CANDIDATE>.json` and once at the top of `scripts/census_night_2.sh`. No step guesses it; every step that needs it reads it from `CENSUS_TASKS`.
- **Evals checkout** `/Users/pauleveritt/projects/pauleveritt/satyrn-evals` (`EVALS`); starting point `release-one` at `b293448`. All commands run from `EVALS`.

---

## File structure

```
.superpowers/sdd/2026-09-17-release-two-census-night-2/progress.md   # T1: the survey and the STOP (git-ignored)
tools/task_specs/<CANDIDATE>.json                    # T2: the candidate's cut spec              (create)
src/satyrn_evals/tasks/<CANDIDATE>/                  # T2: the cut task tree                     (create)
src/satyrn_evals/qualify.py                          # T2: CENSUS_TASKS gains the candidate      (modify)
evidence/2026-09-17-census-2/validity/<CANDIDATE>/   # T2: PROMPT.txt, solution.diff, receipt.json, REPORT.md (create)
evidence/2026-09-17-census-2/validity/README.md      # T2: the run, the model, the tells          (create)
src/satyrn_evals/census_classify.py                  # T3: actual_at_line, attempt_started, Facts.passed_at_line (modify)
evidence/2026-09-16-census/classify.py               # T3: the two actuals, the night key, the overwrite refusal;
                                                     # T4: the decode columns                     (modify)
tests/test_census_classify.py                        # T3: fixtures both directions               (modify)
evidence/2026-09-16-census/<task>/{cells.json,table.md,classes.md}  # T3, T4: five tasks regenerated (modify)
src/satyrn_evals/census_decode.py                    # T4: the pure server-log rules              (create)
tests/test_census_decode.py                          # T4: fixtures both directions               (create)
records/2026-09-17-census2-<CANDIDATE>.json          # T6                                         (create)
records/2026-09-17-census2-selfhost-run-record-gate.json            # T6                          (create)
records/2026-09-17-census2-selfhost-cell-loop.json                  # T6                          (create)
records/2026-09-17-census2-selfhost-speed-probe.json                # T6                          (create)
scripts/census_night_2.sh                            # T6: the launch script                      (create)
tests/test_census_records_frozen.py                  # T6: the night-2 records                    (modify)
ROADMAP.md                                           # T6: the R0 row                             (modify)
PROVENANCE.md                                        # T2, T4, T6                                 (modify)
```

**Names later tasks rely on:**

```python
# src/satyrn_evals/census_classify.py  (T3)
def actual_at_line(*, verdict: str | None, output_tokens: int, turns: int) -> bool: ...
def attempt_started(attempt_dir: str) -> float | None: ...
def whole_attempt_seconds(attempt_dir: str, record_mtime: float) -> float | None: ...
@dataclass(frozen=True, slots=True)
class Facts:  # gains one field, in this position
    code: str | None
    verdict: str | None
    passed_at_line: bool          # NEW
    tripped_verdict: str | None
    raised: str | None
    length_stops: int
    root_searches: int
    tool_reported_timeouts: int
    first_pass_turn: int | None
    first_pass_tokens: int | None
    self_stop_turn: int | None
    allowlist_reason: str | None

# src/satyrn_evals/census_decode.py  (T4)
@dataclass(frozen=True, slots=True)
class Completion:
    ended: float; seconds: float; tokens: int; prompt: int; max_tokens: int
    @property
    def started(self) -> float: ...
@dataclass(frozen=True, slots=True)
class DecodeReading:
    tok_s: float | None; median_tok_s: float | None
    completions: int; tokens: int; seconds: float; reason: str | None
def parse_completions(text: str, *, model_contains: str = "Ornith-1.5-9B") -> list[Completion]: ...
def decode_rate(completions: Sequence[Completion], *, start: float, end: float) -> DecodeReading: ...
def span_overlap(spans: Sequence[tuple[float, float]], start: float, end: float) -> int: ...
LOCAL_OFFSET_REASON = "no completions in the cell's span"   # and the three siblings, as module constants

# evidence/2026-09-16-census/classify.py  (T3, T4)
@dataclass(frozen=True, slots=True)
class DecodeLog:
    completions: list         # census_decode.Completion
    spans: list               # (start, end) for every selected cell of this night
def cell_span(cell: Cell) -> tuple[float | None, float | None, str | None]: ...
def decode_row(cell: Cell, log: DecodeLog | None) -> dict: ...
def load_decode_log(pattern: str, selected: list[Cell]) -> DecodeLog | None: ...
```

---

### Task 1: Survey the Phase 2a/2b/2c plans, propose two candidates, and STOP

Spec section 3.1, first half. This task measures and reports; it cuts nothing, commits nothing, and ends with the maintainer's pick.

**Files:**
- Create: `.superpowers/sdd/2026-09-17-release-two-census-night-2/progress.md` (git-ignored; `.superpowers/` is in `.gitignore`, so no `PROVENANCE.md` row and no commit)
- Read only: `docs/superpowers/plans/2026-09-14-phase-2a-eval-core.md`, `docs/superpowers/plans/2026-09-14-phase-2b-isolation-and-tasks.md`, `docs/superpowers/plans/2026-09-14-phase-2c-launcher-loop.md`, `tools/task_specs/*.json`, `src/satyrn_evals/tasks/*/manifest.json`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: two proposals, each with **plan file and heading**, **base commit**, **good commit**, **`Files:` source list**, **hidden test module and measured test count**, **measured public-suite seconds**, and the predicted validity risk (Ruling 2). Task 2 consumes exactly these six fields.

- [ ] **Step 1: List the field**

```bash
cd "$EVALS"
ls tools/task_specs/*.json | sed 's|.*/||; s|\.json$||'
grep -n '^### Task ' docs/superpowers/plans/2026-09-14-phase-2a-eval-core.md \
  docs/superpowers/plans/2026-09-14-phase-2b-isolation-and-tasks.md \
  docs/superpowers/plans/2026-09-14-phase-2c-launcher-loop.md
```

Expected: six already-cut specs (`selfhost-cell-loop`, `selfhost-docs-linter`, `selfhost-guard-prefixes`, `selfhost-review-script`, `selfhost-run-record-gate`, `selfhost-speed-probe`) and fifteen `### Task` headings across the three plans. Write both lists into the ledger as the starting field.

- [ ] **Step 2: Read each heading's `Files:` and `Test:` block and apply criteria (a), (b), (e), (f), (g)**

For every heading, read its `**Files:**` block and the steps beneath it, and record in the ledger one row: heading, source modules created vs modified, test module, files touched outside `Files:`, whether any step needs a model/network/GPU/`satyrn-cell`, and whether its source module is already a cut task's `files` entry (read those from `tools/task_specs/*.json`). Reject with the criterion letter; keep the rest.

Criterion (b) in practice: a heading qualifies as build-shaped when the generator can strip its source module back to an importable, behaviourally incomplete stub — that is, the module is **created** by that heading rather than extended. `tools/task_specs/selfhost-run-record-gate.json`'s `broken` block is the shape to compare against: one module, a dataclass and two functions, stubbed to `return None`.

- [ ] **Step 3: Measure the hidden-test count for each survivor — criterion (c)**

For each survivor, find its plan anchor's commit the way the cut generator does (`tools/cut_task.py`'s `read_plan`/`collect_ids`), then collect the test module at the `good` commit in a scratch worktree. Do not estimate from the plan text.

```bash
SURV=docs/superpowers/plans/2026-09-14-phase-2b-isolation-and-tasks.md   # per survivor
GOOD=<the good commit for this heading>
TESTMOD=<the heading's test module path>
git worktree add --detach "$SCRATCH/good-$GOOD" "$GOOD"
( cd "$SCRATCH/good-$GOOD" && uv run pytest "$TESTMOD" --collect-only -q 2>/dev/null | tail -3 )
git worktree remove --force "$SCRATCH/good-$GOOD"
```

Expected: a collected count per survivor. Reject anything outside 15–20 inclusive with criterion (c) and the measured number.

- [ ] **Step 4: Measure the public suite at the base commit — criterion (d)**

```bash
BASE=<the base commit for this heading>
git worktree add --detach "$SCRATCH/base-$BASE" "$BASE"
( cd "$SCRATCH/base-$BASE" && time uv run pytest -q -m "not integration" 2>&1 | tail -3 )
git worktree remove --force "$SCRATCH/base-$BASE"
```

Expected: a wall-clock figure per survivor. Reject anything at or over 40 s with criterion (d) and the measured seconds. The public suite is what a cell runs dozens of times inside a 4,800 s backstop; a slow one spends the night in its own tests.

- [ ] **Step 5: Predict the validity risk for each remaining survivor — Ruling 2**

For each survivor, read the plan section as the cut prompt would read it (the section text minus its code blocks, which `r1_plan_prompt` strips) and write one paragraph in the ledger: which structural choices its hidden suite asserts (where a class lives, which function refuses what, which files may change), and whether the section's prose — not its code — states each one. Mark `risk: low|high` with the specific fact that is at risk. This is a prediction, not a gate: the R0 §1.2 check in Task 2 decides.

- [ ] **Step 6: Write the survey and STOP**

Write `.superpowers/sdd/2026-09-17-release-two-census-night-2/progress.md` with: the starting field, the reject table (heading, criterion letter, the measured number where one applies), and the two proposals in full — plan file, heading, base commit, good commit, `Files:` source list, hidden test module, **measured** hidden-test count, **measured** public-suite seconds, predicted validity risk. Rank them and say why.

Then **STOP** and report to the maintainer. The task ends here: no cut, no commit, no `git add`. If fewer than two candidates survive, report that instead — with the reject table — and stop; the census page then says the finishing tier is two tasks wide, which section 7 of the spec explicitly allows.

---

### Task 2: Cut the chosen candidate, qualify it, and run the R0 §1.2 validity check

Spec section 3.1, second half. `CANDIDATE` is the maintainer's pick from Task 1.

**Files:**
- Create: `tools/task_specs/<CANDIDATE>.json`, `src/satyrn_evals/tasks/<CANDIDATE>/` (the cut tree), `evidence/2026-09-17-census-2/validity/<CANDIDATE>/{PROMPT.txt,solution.diff,receipt.json,REPORT.md}`, `evidence/2026-09-17-census-2/validity/README.md`
- Modify: `src/satyrn_evals/qualify.py` (`CENSUS_TASKS`), `src/satyrn_evals/tasks/<CANDIDATE>/manifest.json` (the post-cut `validity` block), `PROVENANCE.md`
- Test: `tests/test_qualify.py` (the census map's new member)

**Interfaces:**
- Consumes: Task 1's six fields per proposal.
- Produces: `qualify.CENSUS_TASKS["<CANDIDATE>"] == "R1-plan"`; a committed task tree whose `tree_digest` Task 6's record pins; `manifest["validity"] == {"by": <model>, "commit": <evals HEAD>, "passed": true}`.

- [ ] **Step 1: Write the cut spec**

Create `tools/task_specs/<CANDIDATE>.json` in the shape of `tools/task_specs/selfhost-run-record-gate.json`: `name`, `base`, `good`, `files` (the heading's source modules), `hidden` (its test modules), `plan` (`path`, `heading`, `commit`), `formats` (the exact-message contract the hidden suite matches, copied from the heading's own prose), `broken` (one importable, behaviourally incomplete stub per source module), `oracle_env` if the suite needs `PYTHONPATH=src`. Do **not** add a `prompt_edits` key: it is optional (night-1 plan Ruling 17) and no edit is justified before the validity check has failed.

- [ ] **Step 2: Cut and check**

```bash
cd "$EVALS"
uv run python tools/cut_task.py cut tools/task_specs/<CANDIDATE>.json; echo "cut=$?"
uv run python tools/cut_task.py check tools/task_specs/<CANDIDATE>.json; echo "check=$?"
uv run python tools/cut_task.py check tools/task_specs/selfhost-run-record-gate.json \
  tools/task_specs/selfhost-docs-linter.json tools/task_specs/selfhost-cell-loop.json \
  tools/task_specs/selfhost-speed-probe.json tools/task_specs/selfhost-guard-prefixes.json \
  tools/task_specs/selfhost-review-script.json; echo "others=$?"
```

Expected: `cut=0`, `check=0` printing "matches a fresh cut", `others=0`. A non-zero `others` means the cut moved a tree that must not move — stop.

- [ ] **Step 3: Qualify**

```bash
uv run satyrn-evals qualify <CANDIDATE>; echo "qualify=$?"
```

Expected: `qualify=0` with every check `ok`. Offline qualification runs the fixtures both ways, a live harvest, and the known-good patch three times. A failure here is a generator defect: fix the spec and re-cut, or drop the candidate and cut the second proposal.

- [ ] **Step 4: Add the candidate to `CENSUS_TASKS`**

In `src/satyrn_evals/qualify.py`, extend the map (leave `CEILING_CANDIDATES`, `FLOOR_CANDIDATES` and `HELDOUT_TASKS` alone — night-1 plan Ruling 18):

```python
CENSUS_TASKS: dict[str, str] = {
    "agentclinic-repair-depth-3": "R2",
    "selfhost-run-record-gate": PLAN_RUNG,
    "selfhost-docs-linter": PLAN_RUNG,
    "selfhost-cell-loop": PLAN_RUNG,
    "selfhost-speed-probe": PLAN_RUNG,
    "<CANDIDATE>": PLAN_RUNG,
}
```

Add the failing test first, in `tests/test_qualify.py`:

```python
def test_the_census_set_carries_the_night_two_candidate() -> None:
    """Night 2 adds exactly one build task to the census set (spec section 3.1)."""
    night_one = {
        "agentclinic-repair-depth-3", "selfhost-run-record-gate", "selfhost-docs-linter",
        "selfhost-cell-loop", "selfhost-speed-probe",
    }
    added = set(CENSUS_TASKS) - night_one
    assert len(added) == 1
    assert CENSUS_TASKS[added.pop()] == PLAN_RUNG
```

Run `uv run pytest tests/test_qualify.py -q` before the edit (expected FAIL: `assert 0 == 1`) and after (expected PASS).

- [ ] **Step 5: Run the validity check exactly as night 1 ran it**

Follow `docs/superpowers/specs/2026-09-15-release-two-task-validity.md`'s Recompute block with `T=<CANDIDATE>` and `SCRATCH` pointing at the session scratchpad — not `/tmp`. In full, so nothing is inferred:

```bash
cd "$EVALS"
T=<CANDIDATE>
GRADE_ROOT="$HOME/satyrn-census-grades/validity/$T"
mkdir -p "$SCRATCH/validity/$T" "$GRADE_ROOT"

cp -R "src/satyrn_evals/tasks/$T/base" "$SCRATCH/validity/$T/tree"
git -C "$SCRATCH/validity/$T/tree" init -q
git -C "$SCRATCH/validity/$T/tree" add -A
git -C "$SCRATCH/validity/$T/tree" \
  -c user.name=validity -c user.email=validity@example.invalid commit -qm base
uv run python - "$T" "$SCRATCH/validity/$T/PROMPT.txt" <<'PY'
import json, sys
from pathlib import Path
from satyrn_evals.qualify import CENSUS_TASKS
task, out = sys.argv[1], Path(sys.argv[2])
body = json.loads((Path("src/satyrn_evals/tasks") / task / "manifest.json").read_text())
out.write_text(body["contracts"][CENSUS_TASKS[task]])
PY
```

Then dispatch **one** solver subagent, blocking, given `PROMPT.txt`'s text and the tree path and nothing else. It may read and write only that tree. Off limits, named individually: the `satyrn-evals` checkout; inside the task directory `overlay/`, `fixtures/`, `manifest.json`, `qualification.json`; `~/satyrn-runs/`; `/Users/Shared/`; `docs/superpowers/plans/`. It does not run the hidden suite and does not write the diff. Its final report says what it changed and why. **Ruling 17:** request the design's named role; if the harness offers only one model, use it and record that model in `validity.by` — do not stop, the substitution is ratified.

Harvest controller-side, then run both named leak tells over `solution.diff` **and** the agent's report:

```bash
git -C "$SCRATCH/validity/$T/tree" add -A
git -C "$SCRATCH/validity/$T/tree" diff --cached > "$SCRATCH/validity/$T/solution.diff"
uv run python - "$T" "$SCRATCH/validity/$T/solution.diff" <<'PY'
import json, sys
from pathlib import Path
task, diff = sys.argv[1], Path(sys.argv[2]).read_text()
body = json.loads((Path("src/satyrn_evals/tasks") / task / "manifest.json").read_text())
tells = [i for i in body["expected_test_ids"] if i in diff]
words = [w for w in ("overlay", "known-good.patch", "known-broken.patch", "manifest.json",
                     f"tasks/{task}") if w in diff]
print("expected_test_id tells:", tells)
print("path tells:", words)
raise SystemExit(1 if tells or words else 0)
PY
echo "tells=$?"
```

Expected: `tells=0`. A hit voids the run: fresh agent, and the void recorded in the README. Matching the known-good patch is **not** a tell.

Grade from a directory with no `pyproject.toml`, `pytest.ini`, `.pytest.ini`, `tox.ini`, `setup.cfg` or `conftest.py` in it or above it, and read the verdict from the receipt, never the exit status:

```bash
( cd "$GRADE_ROOT" && UV_OFFLINE=1 uv run --project "$EVALS" satyrn-evals grade "$T" \
    "$SCRATCH/validity/$T/solution.diff" --receipt receipt.json )
uv run python -c "import json;b=json.load(open('$GRADE_ROOT/receipt.json'));print(b['verdict'], len(b['evidence']['executed_test_ids']))"
```

- [ ] **Step 6: Write the `validity` block**

```bash
uv run python - "$T" "$GRADE_ROOT/receipt.json" <<'PY'
import json, subprocess, sys
from pathlib import Path
task, receipt = sys.argv[1], json.loads(Path(sys.argv[2]).read_text())
commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
path = Path("src/satyrn_evals/tasks") / task / "manifest.json"
body = json.loads(path.read_text())
body["validity"] = {"by": "<the model that actually ran>", "commit": commit, "passed": receipt["verdict"] == "pass"}
path.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(task, body["validity"])
PY
uv run python tools/cut_task.py check tools/task_specs/<CANDIDATE>.json; echo "recheck=$?"
```

Expected: `passed: true` and `recheck=0` — `check` ignores `validity` (night-1 plan Ruling 17), so a post-cut annotation must not move the tree's comparability.

**If `passed` is false:** a recorded `prompt_edits` entry is permitted **only** for a fact the plan's stripped code stated (spec section 3.1). Add it to the cut spec, re-cut, re-check, re-qualify, and re-run the whole check with a fresh agent. If no such fact exists, drop this candidate, record the failure in the README with `passed: false`, and cut the second proposal from Task 1.

- [ ] **Step 7: Preserve the artefacts**

```bash
mkdir -p "evidence/2026-09-17-census-2/validity/$T"
cp "$SCRATCH/validity/$T/PROMPT.txt" "$SCRATCH/validity/$T/solution.diff" \
   "$GRADE_ROOT/receipt.json" "evidence/2026-09-17-census-2/validity/$T/"
```

Write the solver's final report to `evidence/2026-09-17-census-2/validity/$T/REPORT.md`, and `evidence/2026-09-17-census-2/validity/README.md` in the shape of `evidence/2026-09-16-census/validity/README.md`: the date; a per-task row (task, verdict, counts read as `verdict` and `len(evidence.executed_test_ids)` from the receipt, the evals commit the prompt was read from, the two **named** leak tells, and the receipt's separate `grader_content_in_patch` field reported as its own column — night 1's whole-path review found those two must not be conflated); a Model section naming the model that ran, why it ran (Ruling 17), and the maintainer's standing caveat carried verbatim from night 1: read the certification as slightly weaker than the design's named instrument, and re-check on that instrument if the task turns out easier than expected.

- [ ] **Step 8: Provenance, gates and commit**

```bash
uv run python tools/provenance.py new tools/task_specs/<CANDIDATE>.json \
  evidence/2026-09-17-census-2/validity/README.md \
  evidence/2026-09-17-census-2/validity/<CANDIDATE>/PROMPT.txt \
  evidence/2026-09-17-census-2/validity/<CANDIDATE>/solution.diff \
  evidence/2026-09-17-census-2/validity/<CANDIDATE>/receipt.json \
  evidence/2026-09-17-census-2/validity/<CANDIDATE>/REPORT.md \
  $(git status --porcelain --untracked-files=all -- src/satyrn_evals/tasks/<CANDIDATE> | awk '{print $2}')
just gates; echo "gates=$?"
git add tools/task_specs/<CANDIDATE>.json src/satyrn_evals/tasks/<CANDIDATE> \
  src/satyrn_evals/qualify.py tests/test_qualify.py evidence/2026-09-17-census-2/validity PROVENANCE.md
git commit -m "Census night 2: cut <CANDIDATE> as the third medium-build task, qualified and validity-checked"
```

Expected: `gates=0`, including `test_census_records_frozen.py` (the five night-1 records still match their trees — this cut must not have moved one).

---

### Task 3: The classifier's actual at the 32k line

Spec section 3.2. The 48k verdict stays as a second column; both readings are printed in the per-task tally; night 1's five outputs are regenerated.

**Files:**
- Modify: `src/satyrn_evals/census_classify.py`, `evidence/2026-09-16-census/classify.py`
- Modify (regenerated): `evidence/2026-09-16-census/<task>/{cells.json,table.md,classes.md}` for all five night-1 tasks
- Test: `tests/test_census_classify.py`

**Interfaces:**
- Consumes: nothing from Tasks 1–2.
- Produces: `census_classify.actual_at_line`, `census_classify.attempt_started`, `Facts.passed_at_line`; driver row keys `actual_32k` and `actual_48k`; `cells.json` header key `night`. Task 4 adds decode keys to the same row and the same header.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_census_classify.py` (and update `_facts` to carry the new field):

```python
from satyrn_evals.census_classify import actual_at_line, attempt_started


def test_a_pass_inside_the_line_is_actual_at_the_line() -> None:
    assert actual_at_line(verdict="pass", output_tokens=19_556, turns=40) is True


def test_a_pass_whose_turns_left_the_line_is_not_actual_at_the_line() -> None:
    """Night 1's run-record-gate 275888: OK/pass at turn 55 with 30,444 tokens."""
    assert actual_at_line(verdict="pass", output_tokens=30_444, turns=55) is False


def test_a_pass_whose_tokens_left_the_line_is_not_actual_at_the_line() -> None:
    """Night 1's docs-linter 845472: OK/pass at turn 54 with 38,999 tokens."""
    assert actual_at_line(verdict="pass", output_tokens=38_999, turns=54) is False


def test_a_fail_inside_the_line_is_not_actual_at_the_line() -> None:
    assert actual_at_line(verdict="fail", output_tokens=1_000, turns=3) is False


def test_a_tripped_cell_is_not_actual_at_the_line_whatever_the_tripped_grade() -> None:
    """Ruling 3: the tripped verdict describes the 48k teardown, never a delivery at the line."""
    assert actual_at_line(verdict=None, output_tokens=20_000, turns=30) is False


def test_the_boundary_is_inclusive_on_both_axes() -> None:
    assert actual_at_line(verdict="pass", output_tokens=32_000, turns=48) is True
    assert actual_at_line(verdict="pass", output_tokens=32_001, turns=48) is False
    assert actual_at_line(verdict="pass", output_tokens=32_000, turns=49) is False


def test_the_class_flags_read_the_line_not_the_budget() -> None:
    """Ruling 5: a cell that passed outside the line, holding a pass state inside it,
    is a finishing row -- the same reading the tally uses."""
    row = flags(_facts(verdict="pass", code="OK", passed_at_line=False,
                       first_pass_turn=16, first_pass_tokens=13_809))
    assert (row["finishing"], row["capability"], row["budget"]) == (True, False, False)


def test_a_cell_that_passed_inside_the_line_flags_none_of_the_three() -> None:
    row = flags(_facts(verdict="pass", code="OK", passed_at_line=True,
                       first_pass_turn=16, first_pass_tokens=9_081))
    assert not any(row[name] for name in ("capability", "budget", "finishing"))


def test_attempt_started_is_the_directorys_utc_stamp() -> None:
    from datetime import UTC, datetime

    expected = datetime(2026, 9, 16, 18, 29, 41, 312540, tzinfo=UTC).timestamp()
    assert attempt_started("selfhost-docs-linter-20260916-182941-312540") == expected


def test_a_directory_name_without_a_stamp_has_no_start() -> None:
    assert attempt_started("not-a-stamp") is None
```

Change the shared `_facts` helper so the new field has a default and both directions are reachable:

```python
def _facts(**overrides: object) -> Facts:
    base: dict = dict(
        code="BUDGET_EXCEEDED", verdict=None, passed_at_line=False, tripped_verdict=None,
        raised=None, length_stops=0, root_searches=0, tool_reported_timeouts=0,
        first_pass_turn=None, first_pass_tokens=None, self_stop_turn=None, allowlist_reason=None,
    )
    return Facts(**(base | overrides))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_census_classify.py -q`
Expected: FAIL with `ImportError: cannot import name 'actual_at_line'`.

- [ ] **Step 3: Implement in `src/satyrn_evals/census_classify.py`**

Add, beside `within_32k`:

```python
def actual_at_line(*, verdict: str | None, output_tokens: int, turns: int) -> bool:
    """The harness verdict read at the pre-registered line, not at the record's budget.

    Night 1 compared own-green triggers at 32,000 tokens / 48 turns against the
    verdict at the record's 48,000-token budget, so a cell that only reached its
    pass *between* the two lines counted as no rescue (night-2 design section
    3.2). A pass is a pass at the line only if the cell's own spend stayed
    inside it.

    ``verdict`` is the delivered patch's. A torn-down cell's verdict is ``None``
    by the census's own rule, so its ``tripped_verdict`` -- a 48k teardown state
    -- can never make it actual at the line (Ruling 3), and ``code`` adds
    nothing because only an ``OK`` cell carries a graded verdict (Ruling 4).
    """
    return verdict == "pass" and within_32k(output_tokens, turns)
```

Split the timestamp helper so the driver can reach the start alone (Task 4 needs it for the span):

```python
def attempt_started(attempt_dir: str) -> float | None:
    """The attempt directory's microsecond UTC stamp, as epoch seconds."""
    match = _STAMP.search(attempt_dir)
    if match is None:
        return None
    started = datetime.strptime(match.group(1), "%Y%m%d-%H%M%S-%f").replace(tzinfo=UTC)
    return started.timestamp()


def whole_attempt_seconds(attempt_dir: str, record_mtime: float) -> float | None:
    """Ruling 8 of the night-1 plan: the directory's stamp to `attempt.json`'s mtime.

    No new harness clock. `timeline.jsonl` is monotonic and holds only tool
    events, so it gives the tool span and never the whole attempt; these two
    stamps already exist and bracket setup, command, preservation and grading.
    """
    started = attempt_started(attempt_dir)
    return None if started is None else record_mtime - started
```

Add `passed_at_line: bool` to `Facts` immediately after `verdict`, with its docstring line, and change one line in `flags`:

```python
    # Ruling 5: the classes read the same line the tally reads. `verdict` and
    # `code` stay on Facts as the 48k reading, printed in their own columns.
    passed = facts.passed_at_line
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_census_classify.py -q`
Expected: PASS, every test in the file.

- [ ] **Step 5: Teach the driver both readings**

In `evidence/2026-09-16-census/classify.py`:

In `counterfactual(...)`, replace the single `actual` line with:

```python
    # Design section 3.2: the counterfactual is read at the pre-registered line.
    # The record's 48,000-token budget stays as a second column, never as the
    # comparison (Ruling 3). Feeding the line reading to `cf.unmeasured_reasons`
    # moves run 1's unmeasured list, which is correct: run 1 withholds an
    # unverified rescue, and more cells are now not-actual (Ruling 19).
    actual_48k = audit_row["code"] == "OK" and audit_row["verdict"] == "pass"
    actual = cc.actual_at_line(
        verdict=audit_row["verdict"],
        output_tokens=audit_row["evidence"]["output_tokens"],
        turns=audit_row["evidence"]["turns"],
    )
```

and add `"actual_48k": actual_48k,` to its returned dict beside `"actual": actual,`. Make the same two changes in `_no_reading(...)`, whose `value` keeps following `actual` (the line reading), so a cell with no reading keeps its own outcome at the line.

In `row(...)`, pass the line reading into the facts and print both actuals:

```python
    facts = cc.Facts(
        code=audit_row["code"],
        verdict=audit_row["verdict"],
        passed_at_line=bool(reading["actual"]),
        tripped_verdict=audit_row["tripped_verdict"],
        ...
    )
```

and add to the returned row, beside `"verdict"`:

```python
        "actual_32k": reading["actual"],
        "actual_48k": reading["actual_48k"],
```

In `table(...)`, add the column `"verdict@32k"` immediately after `"verdict"`, and its value `("pass" if r["actual_32k"] else "not-pass")`. In `tally_table(...)`, add two columns so both readings are in the tally the spec asks for:

```python
        "| task | reading | cells | actual pass @32k | actual pass @48k | rescues | harms | net | unmeasured cells |",
```

with `tallies(...)` gaining, per row, `"actual_32k": sum(1 for r in mine if r["actual_32k"])` and `"actual_48k": sum(1 for r in mine if r["actual_48k"])`.

In `classes(...)`, append the two actuals to each `evidence:` line so the reviewer sees which line the flags were computed at:

```python
        lines.append(f"evidence: {r['task']} {r['attempt']} {shown} actual@32k={r['actual_32k']} actual@48k={r['actual_48k']}")
```

- [ ] **Step 6: Record the night in the header, and refuse to overwrite another night's folder**

Ruling 11. In `stamp(argv)` add `night` as a parameter and key:

```python
def stamp(argv: list[str], night: Path) -> dict:
    ...
    return {"evals_commit": commit, "evals_dirty": dirty, "night": night.name,
            "command": " ".join(["classify.py", *argv])}
```

In `main`, call it as `stamp(argv, args.night)`, and before writing anything:

```python
    for task in sorted({r["task"] for r in rows}):
        existing = args.out / task / "cells.json"
        if existing.is_file():
            previous = json.loads(existing.read_text()).get("night")
            if previous is not None and previous != header["night"]:
                print(
                    f"classify: {existing} holds {previous}, not {header['night']}; "
                    "pass --out for this night rather than overwriting another night's table",
                    file=sys.stderr,
                )
                return 2
```

Reason in one comment above it: three of night 2's four tasks share night 1's names, and the default `--out` is night 1's directory.

- [ ] **Step 7: Verify the refusal and the two readings on a retained night, read-only**

```bash
cd "$EVALS"
mkdir -p "$HOME/satyrn-census-grades"
uv run --project . python evidence/2026-09-16-census/classify.py \
  --night "$HOME/satyrn-runs/2026-09-15-admission-selfhost-docs-linter" \
  --record records/2026-09-15-admission-selfhost-docs-linter.json \
  --out "$SCRATCH/census-verify" --grade-root "$SCRATCH/census-grades"; echo "first=$?"
uv run --project . python evidence/2026-09-16-census/classify.py \
  --night "$HOME/satyrn-runs/2026-09-16-census-selfhost-docs-linter" \
  --record records/2026-09-16-census-selfhost-docs-linter.json \
  --out "$SCRATCH/census-verify" --grade-root "$SCRATCH/census-grades"; echo "second=$?"
```

Expected: `first=0`, `second=2` with the refusal naming both nights — the sibling success case is `first`, the refusal is `second`. Then re-run the second command with `--out "$SCRATCH/census-verify-2"` and expect `0`.

- [ ] **Step 8: Regenerate night 1's five outputs and check the diff is exactly what was predicted**

```bash
cd "$EVALS"
for T in agentclinic-repair-depth-3 selfhost-run-record-gate selfhost-docs-linter selfhost-cell-loop selfhost-speed-probe; do
  uv run --project . python evidence/2026-09-16-census/classify.py \
    --night "$HOME/satyrn-runs/2026-09-16-census-$T" \
    --record "records/2026-09-16-census-$T.json" \
    --grade-root "$HOME/satyrn-census-grades"; echo "$T=$?"
done
git diff --stat -- evidence/2026-09-16-census
git diff -- evidence/2026-09-16-census/*/table.md
```

Expected: five `=0`. Ruling 6 — the diff must be confined to:

- `table.md`: the new `verdict@32k` column, and the two new tally columns. **No other cell of any row changes.**
- `cells.json`: `actual_32k`, `actual_48k`, the `run1`/`run2` blocks, `unmeasured`, `tallies`, and the header's new `night` key.
- `classes.md`: the `evidence:` lines, whose `capability`/`budget`/`finishing` values move for exactly the four cells whose 48k pass fell outside the line — `selfhost-run-record-gate` 275888 (turn 55), `selfhost-docs-linter` 374751 (turn 52), 906198 (turn 66, 38,476 tokens) and 845472 (turn 54, 38,999 tokens) — plus the appended `actual@32k=`/`actual@48k=` on every line.

Confirm the pre-registered denominators STATE.md records still hold in the regenerated `verdict@32k` column: depth-3 6/6, run-record-gate 1/6, docs-linter 1/6, cell-loop 0/6, speed-probe 0/6. **Any difference outside this list stops the task** and is reported rather than tuned away.

- [ ] **Step 9: Gates and commit**

```bash
just gates; echo "gates=$?"
git add src/satyrn_evals/census_classify.py evidence/2026-09-16-census/classify.py \
  tests/test_census_classify.py evidence/2026-09-16-census/agentclinic-repair-depth-3 \
  evidence/2026-09-16-census/selfhost-run-record-gate evidence/2026-09-16-census/selfhost-docs-linter \
  evidence/2026-09-16-census/selfhost-cell-loop evidence/2026-09-16-census/selfhost-speed-probe
git commit -m "Census classifier: the actual is read at the 32k/48 line, the 48k verdict kept beside it; night 1's five tables regenerated"
```

Expected: `gates=0`. The commit message names the change, as the spec requires. No new file, so no `PROVENANCE.md` row.

---

### Task 4: Decode rate per cell, offline from the oMLX server log

Spec section 3.3. No harness change. `~/.omlx/logs/` is read-only.

**Files:**
- Create: `src/satyrn_evals/census_decode.py`
- Modify: `evidence/2026-09-16-census/classify.py`, `PROVENANCE.md`
- Modify (regenerated): `evidence/2026-09-16-census/<task>/{cells.json,table.md,classes.md}` for all five night-1 tasks
- Test: `tests/test_census_decode.py`

**Interfaces:**
- Consumes: `census_classify.attempt_started` (Task 3).
- Produces: `census_decode.{Completion, DecodeReading, parse_completions, decode_rate, span_overlap}`; driver row keys `decode_tok_s`, `decode_median_tok_s`, `decode_completions`, `decode_overlap`, `decode_reason`; the CLI option `--server-log GLOB`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_census_decode.py`:

```python
"""Decode rate read from the oMLX server log. Default tier: synthetic log text, no filesystem.

The log does not name the cell (Ruling 7), so these rules answer "how fast did
tokens come out of the machine while this cell ran", never "how fast was this
cell's own stream". Every rule has a firing row and a silent row.
"""

from datetime import datetime

from satyrn_evals.census_decode import (
    NO_COMPLETIONS,
    NO_DECODE_SECONDS,
    decode_rate,
    parse_completions,
    span_overlap,
)

LINE = (
    "2026-09-16 12:41:44,035 - omlx.server - INFO - [-] - Chat completion: "
    "model=Ornith-1.5-9B-MLX-8bit, {tok} tokens in {sec}s ({rate} tok/s), "
    "prompt: {prompt}, finish_reason=tool_calls, max_tokens=16000, request_max_tokens=16000"
)


def _line(ts: str, tok: int, sec: float, prompt: int = 1702) -> str:
    rate = round(tok / sec, 1) if sec else 0.0
    body = LINE.format(tok=tok, sec=sec, rate=rate, prompt=prompt)
    return ts + body[len("2026-09-16 12:41:44,035") :]


def _epoch(ts: str) -> float:
    return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S,%f").astimezone().timestamp()


def test_a_completion_line_parses_into_tokens_seconds_and_the_local_instant() -> None:
    (one,) = parse_completions(_line("2026-09-16 12:41:44,035", 102, 4.11))
    assert (one.tokens, one.seconds, one.prompt, one.max_tokens) == (102, 4.11, 1702, 16000)
    assert one.ended == _epoch("2026-09-16 12:41:44,035")
    assert one.started == one.ended - 4.11


def test_a_line_for_another_model_is_not_a_completion() -> None:
    other = _line("2026-09-16 12:41:44,035", 102, 4.11).replace("Ornith-1.5-9B-MLX-8bit", "Some-Other-7B")
    assert parse_completions(other) == []


def test_a_line_that_is_not_a_completion_is_skipped() -> None:
    assert parse_completions("2026-09-16 12:41:44,035 - omlx.scheduler - INFO - [-] - Cache phase timings: x\n") == []


def test_the_rate_is_token_weighted_not_a_per_completion_mean() -> None:
    """Ruling 8: 1,900 tokens in 30 decode seconds is 63.3 tok/s, though the
    per-completion median is 90."""
    text = "\n".join(
        [
            _line("2026-09-16 12:00:10,000", 100, 10.0),
            _line("2026-09-16 12:00:30,000", 900, 10.0),
            _line("2026-09-16 12:00:50,000", 900, 10.0),
        ]
    )
    reading = decode_rate(parse_completions(text), start=_epoch("2026-09-16 12:00:00,000"),
                          end=_epoch("2026-09-16 12:01:00,000"))
    assert reading.completions == 3
    assert round(reading.tok_s, 1) == 63.3
    assert reading.median_tok_s == 90.0
    assert reading.reason is None


def test_a_completion_that_began_before_the_span_is_not_attributed() -> None:
    text = _line("2026-09-16 12:00:05,000", 100, 10.0)   # started 11:59:55
    reading = decode_rate(parse_completions(text), start=_epoch("2026-09-16 12:00:00,000"),
                          end=_epoch("2026-09-16 12:01:00,000"))
    assert (reading.tok_s, reading.completions, reading.reason) == (None, 0, NO_COMPLETIONS)


def test_a_completion_that_ended_after_the_span_is_not_attributed() -> None:
    text = _line("2026-09-16 12:01:05,000", 100, 10.0)
    reading = decode_rate(parse_completions(text), start=_epoch("2026-09-16 12:00:00,000"),
                          end=_epoch("2026-09-16 12:01:00,000"))
    assert (reading.tok_s, reading.completions, reading.reason) == (None, 0, NO_COMPLETIONS)


def test_attributed_completions_with_no_decode_seconds_are_a_stated_reason() -> None:
    """Ruling 10: a null rate always says why."""
    text = _line("2026-09-16 12:00:30,000", 0, 0.0)
    reading = decode_rate(parse_completions(text), start=_epoch("2026-09-16 12:00:00,000"),
                          end=_epoch("2026-09-16 12:01:00,000"))
    assert reading.completions == 1
    assert (reading.tok_s, reading.median_tok_s, reading.reason) == (None, None, NO_DECODE_SECONDS)


def test_span_overlap_counts_the_nights_concurrent_cells_including_this_one() -> None:
    spans = [(0.0, 100.0), (50.0, 150.0), (140.0, 200.0)]
    assert span_overlap(spans, 0.0, 100.0) == 2
    assert span_overlap(spans, 50.0, 150.0) == 3


def test_a_cell_that_shared_the_machine_with_nobody_overlaps_only_itself() -> None:
    assert span_overlap([(0.0, 100.0)], 0.0, 100.0) == 1
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_census_decode.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'satyrn_evals.census_decode'`.

- [ ] **Step 3: Write `src/satyrn_evals/census_decode.py`**

```python
"""Decode rate per cell, read offline from the oMLX server log.

Night-2 design section 3.3: no harness change and no new clock. The server log
records one line per chat completion carrying the wall-clock instant it
finished, the seconds it decoded for and the tokens it produced; a cell's span
is its attempt directory's UTC stamp to `attempt.json`'s mtime. Text in,
numbers out -- the night driver does the globbing and owns the spans.

**The log does not name the cell** (Ruling 7). A completion line has a model, a
size, a duration and a finish reason, and no session, request or cell id. At
k = 3 up to three cell spans overlap, so a completion inside the overlap is
attributed to all three: this module reports *the machine's decode rate while
the cell ran*, which is the contention number the design asks for, and never a
private per-cell stream. `span_overlap` puts the sharing on the row as a number.

Timestamps in the log are naive **local** time (Ruling 9); attempt stamps are
UTC. Both become epoch seconds before anything is compared.

The pattern is `run-2/serverlog.py`'s, unchanged, so the census parses the log
exactly as the committed counterfactual parsed it.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from statistics import median

#: `evidence/2026-09-15-finishing-counterfactual/run-2/serverlog.py`, verbatim.
_COMPLETION = re.compile(
    r"^(?P<ts>\S+ \S+) .*Chat completion: model=(?P<model>[^,]+), (?P<tok>\d+) tokens "
    r"in (?P<sec>[\d.]+)s \((?P<rate>[\d.]+) tok/s\), prompt: (?P<prompt>\d+), "
    r"finish_reason=(?P<fin>\w+), max_tokens=(?P<mt>\d+)"
)

#: The four reasons a `decode_tok_s` is null (Ruling 10). The last two are the
#: driver's: it owns the attempt directory and `attempt.json`.
NO_COMPLETIONS = "no completions in the cell's span"
NO_DECODE_SECONDS = "attributed completions report no decode seconds"
NO_STAMP = "no attempt stamp in the directory name"
NO_ATTEMPT_JSON = "attempt.json is missing or unreadable"


@dataclass(frozen=True, slots=True)
class Completion:
    """One served completion: when it finished, how long it decoded, how much it produced."""

    ended: float
    seconds: float
    tokens: int
    prompt: int
    max_tokens: int

    @property
    def started(self) -> float:
        return self.ended - self.seconds


@dataclass(frozen=True, slots=True)
class DecodeReading:
    """`tok_s` is token-weighted (Ruling 8); `median_tok_s` is the per-completion median,
    carried because `run-2/q3stats.md`'s bins are medians. `reason` is non-null exactly
    when `tok_s` is null."""

    tok_s: float | None
    median_tok_s: float | None
    completions: int
    tokens: int
    seconds: float
    reason: str | None


def parse_completions(text: str, *, model_contains: str = "Ornith-1.5-9B") -> list[Completion]:
    """Every completion line for the census model, in log order."""
    out: list[Completion] = []
    for line in text.splitlines():
        match = _COMPLETION.match(line)
        if match is None or model_contains not in match["model"]:
            continue
        # Naive stamp: this machine's local time, the machine that also wrote
        # the attempt directories (Ruling 9).
        ended = datetime.strptime(match["ts"], "%Y-%m-%d %H:%M:%S,%f").astimezone()
        out.append(
            Completion(
                ended=ended.timestamp(),
                seconds=float(match["sec"]),
                tokens=int(match["tok"]),
                prompt=int(match["prompt"]),
                max_tokens=int(match["mt"]),
            )
        )
    return out


def decode_rate(completions: Sequence[Completion], *, start: float, end: float) -> DecodeReading:
    """The machine's decode rate over the completions wholly inside `[start, end]`.

    A completion counts only when it both began and ended inside the span: a
    completion straddling the boundary decoded partly for some other cell's
    wall clock and would bias the rate with seconds the span did not contain.
    """
    inside = [c for c in completions if start <= c.started and c.ended <= end]
    if not inside:
        return DecodeReading(None, None, 0, 0, 0.0, NO_COMPLETIONS)
    tokens = sum(c.tokens for c in inside)
    seconds = sum(c.seconds for c in inside)
    rates = [c.tokens / c.seconds for c in inside if c.seconds > 0]
    if seconds <= 0 or not rates:
        return DecodeReading(None, None, len(inside), tokens, seconds, NO_DECODE_SECONDS)
    return DecodeReading(
        tok_s=tokens / seconds,
        median_tok_s=median(rates),
        completions=len(inside),
        tokens=tokens,
        seconds=seconds,
        reason=None,
    )


def span_overlap(spans: Sequence[tuple[float, float]], start: float, end: float) -> int:
    """How many of the night's cell spans intersect `[start, end]`, this one included.

    The honest statement of Ruling 7's limit: the log cannot say which cell a
    completion belonged to, so this says how many it could have belonged to.
    """
    return sum(1 for s, e in spans if s < end and start < e)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_census_decode.py -q`
Expected: PASS. If `test_attributed_completions_with_no_decode_seconds_are_a_stated_reason` does not construct a parseable zero-second line, adjust the helper to emit `0 tokens in 0.0s (0.0 tok/s)` rather than changing the module.

- [ ] **Step 5: Wire the column into the driver**

In `evidence/2026-09-16-census/classify.py`, import the module and `glob` (`import glob` beside the existing `import json`; `from satyrn_evals import census_decode as cd` beside `from satyrn_evals import census_classify as cc`), add the CLI option, and add these three functions above `measure`:

```python
@dataclass(frozen=True, slots=True)
class DecodeLog:
    """The night's completions and every selected cell's span (Ruling 7)."""

    completions: list
    spans: list


def cell_span(cell: Cell) -> tuple[float | None, float | None, str | None]:
    """`[attempt directory stamp, mtime(attempt.json)]`, or a stated reason (Ruling 10)."""
    started = cc.attempt_started(cell.attempt_dir)
    if started is None:
        return None, None, cd.NO_STAMP
    try:
        ended = (cell.folder / "attempt.json").stat().st_mtime
    except OSError:
        return None, None, cd.NO_ATTEMPT_JSON
    return started, ended, None


def load_decode_log(pattern: str, selected: list[Cell]) -> DecodeLog:
    """Read-only over `~/.omlx/logs/`. Files are read in name order, which is
    date order for oMLX's rotation, and the completions are not re-sorted: the
    attribution is by instant, not by position."""
    completions: list = []
    for name in sorted(glob.glob(pattern)):
        completions.extend(cd.parse_completions(Path(name).read_text(errors="replace")))
    spans = [(s, e) for s, e, reason in map(cell_span, selected) if reason is None]
    return DecodeLog(completions=completions, spans=spans)


def decode_row(cell: Cell, log: DecodeLog) -> dict:
    start, end, reason = cell_span(cell)
    if reason is not None:
        return {"decode_tok_s": None, "decode_median_tok_s": None, "decode_completions": 0,
                "decode_overlap": None, "decode_reason": reason}
    reading = cd.decode_rate(log.completions, start=start, end=end)
    return {
        "decode_tok_s": reading.tok_s,
        "decode_median_tok_s": reading.median_tok_s,
        "decode_completions": reading.completions,
        "decode_overlap": cd.span_overlap(log.spans, start, end),
        "decode_reason": reading.reason,
    }
```

`measure(cell, grade_root, log)` gains the third parameter and merges `decode_row(cell, log)` into the row it returns (both on the normal path and on the `raised` path, so an unreadable cell still carries its span's rate). `main` builds the log once before the loop:

```python
    parser.add_argument(
        "--server-log",
        default=str(Path.home() / ".omlx" / "logs" / "server.log*"),
        help="glob for the oMLX server logs the decode rate is read from (read-only)",
    )
    ...
    log = load_decode_log(args.server_log, selected)
```

If `load_decode_log` finds no file at all, print one line to stderr and carry on with an empty log: every row then reads `decode_reason = "no completions in the cell's span"`, which is the honest outcome and not a refusal — the classifier's other columns do not depend on the log.

In `table(...)`, add `"decode tok/s"` and `"decode n"` after `"whole-attempt s"`, formatted `"-" if r["decode_tok_s"] is None else f"{r['decode_tok_s']:.1f}"` and `str(r["decode_completions"])`. In `classes(...)`, append `decode_tok_s=` and `decode_overlap=` to each `evidence:` line. In `stamp(...)`, add the offset actually used so a recomputation elsewhere is visibly different (Ruling 9) — this needs `from datetime import datetime` at the top of the driver, which does not import it yet:

```python
    "tz_offset": datetime.now().astimezone().strftime("%z"),
```

- [ ] **Step 6: Verify on a retained night, read-only, and sanity-check the number**

```bash
cd "$EVALS"
uv run --project . python evidence/2026-09-16-census/classify.py \
  --night "$HOME/satyrn-runs/2026-09-16-census-selfhost-run-record-gate" \
  --record records/2026-09-16-census-selfhost-run-record-gate.json \
  --out "$SCRATCH/decode-verify" --grade-root "$SCRATCH/census-grades"; echo "exit=$?"
sed -n '1,12p' "$SCRATCH/decode-verify/selfhost-run-record-gate/table.md"
```

Expected: `exit=0`, and a `decode tok/s` per row. Three checks, each reported rather than tuned to:

1. The night-1 rows land in the **14–26 tok/s per stream** band the design reports for that shared night, not run 2's ~30 (spec section 2, consequence 3). A number far outside it means the span or the timezone is wrong.
2. `decode n` is non-zero on every cell of a night whose log is still on disk, and `decode overlap` is 3 on the cells that ran concurrently at k = 3.
3. `git status --porcelain` prints nothing and nothing was written under `~/satyrn-runs` or `~/.omlx`.

- [ ] **Step 7: Regenerate night 1's five outputs; the diff is exactly the decode fields**

```bash
cd "$EVALS"
rm -rf "$SCRATCH/decode-verify"
for T in agentclinic-repair-depth-3 selfhost-run-record-gate selfhost-docs-linter selfhost-cell-loop selfhost-speed-probe; do
  uv run --project . python evidence/2026-09-16-census/classify.py \
    --night "$HOME/satyrn-runs/2026-09-16-census-$T" \
    --record "records/2026-09-16-census-$T.json" \
    --grade-root "$HOME/satyrn-census-grades"; echo "$T=$?"
done
git diff -- evidence/2026-09-16-census/*/table.md | grep '^[-+]' | grep -v '^[-+][-+]' | head -40
```

Expected: five `=0`, and a `table.md` diff that changes only the header row and adds two values per row (Ruling 6). `cells.json` gains the five decode keys and `tz_offset`; `classes.md`'s evidence lines gain `decode_tok_s=` and `decode_overlap=`. **Any change to a turn count, a pass turn, a verdict or a tally stops the task.**

- [ ] **Step 8: Provenance, gates and commit**

```bash
uv run python tools/provenance.py new src/satyrn_evals/census_decode.py tests/test_census_decode.py
just gates; echo "gates=$?"
git add src/satyrn_evals/census_decode.py tests/test_census_decode.py \
  evidence/2026-09-16-census/classify.py PROVENANCE.md \
  evidence/2026-09-16-census/agentclinic-repair-depth-3 evidence/2026-09-16-census/selfhost-run-record-gate \
  evidence/2026-09-16-census/selfhost-docs-linter evidence/2026-09-16-census/selfhost-cell-loop \
  evidence/2026-09-16-census/selfhost-speed-probe
git commit -m "Census classifier: an offline decode rate per cell from the oMLX server log; night 1's five tables carry it"
```

Expected: `gates=0`.

---

### Task 5: One whole-path review, before any record is written

Spec section 9 ("a whole-path reviewer traces one cell end to end before launch") and Ruling 16. The reviewer did **not** implement Tasks 2–4.

**Files:**
- Modify (only if the review raises a finding): the file the finding names, plus the default-tier test that pins it
- Modify: `.superpowers/sdd/2026-09-17-release-two-census-night-2/progress.md` (the review and its disposition; git-ignored)

**Interfaces:**
- Consumes: the package `HEAD~3..HEAD` (Tasks 2, 3, 4) and the regenerated night-1 outputs.
- Produces: a finding list with a disposition each, and a default-tier test per accepted finding.

- [ ] **Step 1: Dispatch one fresh reviewer with the whole path, not the diff**

The reviewer's brief, verbatim in the dispatch: trace **one retained cell** of `~/satyrn-runs/2026-09-16-census-selfhost-run-record-gate` from launch to the classified row, and say at each stage what could be wrong and how you checked:

1. **Launch and record** — the frozen record's fields reach the cell: budgets, backstop, per-turn cap, isolation, k.
2. **Cell run and teardown** — where the attempt directory's name comes from, when `attempt.json` is written, which codes are harness cuts, and what a `BUDGET_EXCEEDED` teardown harvests.
3. **Harvest and grade** — the delivered patch's verdict, the tripped patch's offline verdict, and the rule that the tripped verdict is never a pass and never moves a rate.
4. **Evidence** — `collect_evidence`'s turns, tokens, length stops, self stop, tool span; the `cut=` argument and why a normal-exit over-budget cell is not a cut.
5. **The classifier, including the new columns** — the replay, the trigger, the graded trajectory; **`actual_32k` vs `actual_48k`** and whether every consumer of `actual` now reads the intended one; `Facts.passed_at_line` and whether `classes.md`'s evidence lines agree with `table.md`'s tally; **`decode_tok_s`** — the span's two ends, the timezone, the whole-inside-the-span rule, the token weighting, the four null reasons, and whether `decode_overlap` states the k = 3 limit honestly.
6. **The outputs** — the overwrite refusal, the header's `night` and `tz_offset`, and whether night 2's four records could land anywhere that overwrites night 1.

Name every finding Critical / Important / Minor with the file and line, and say for each whether it is reachable on the night as designed.

- [ ] **Step 2: Adjudicate each finding, in the ledger**

For each: ADDRESSED (with the commit), NOT ADDRESSED BY DESIGN (with the reason and the ratification, if any), or DEFERRED (with who carries it). A Critical that is reachable on the night **stops the plan** until it is addressed; the records are not written over it.

- [ ] **Step 3: Every accepted finding becomes a default-tier test**

The standing lesson of the 2026-09-16 fix wave. Write the failing test first, run it to see it fail, fix, run it to see it pass. Tests go in `tests/test_census_classify.py` or `tests/test_census_decode.py` — no model, no network, no subprocess.

- [ ] **Step 4: Scoped re-review and commit**

Dispatch a scoped re-reviewer on the fix diff only: are all three of ADDRESSED/NOT ADDRESSED/DEFERRED honest, and did the fix break anything? Then:

```bash
just gates; echo "gates=$?"
git add <the files the fixes touched>
git commit -m "Census night 2: whole-path review findings and their tests"
```

Expected: `gates=0`. If the review found nothing, there is no commit and the ledger says so — that is a legitimate outcome and is recorded, not manufactured.

---

### Task 6: The four records, the launch script, the frozen-record guard, and the operator checklist

Spec section 4. Frozen and committed in daylight; the maintainer starts the script.

**Files:**
- Create: `records/2026-09-17-census2-<CANDIDATE>.json`, `records/2026-09-17-census2-selfhost-run-record-gate.json`, `records/2026-09-17-census2-selfhost-cell-loop.json`, `records/2026-09-17-census2-selfhost-speed-probe.json`, `scripts/census_night_2.sh`
- Modify: `tests/test_census_records_frozen.py`, `ROADMAP.md`, `PROVENANCE.md`

**Interfaces:**
- Consumes: Task 2's `CENSUS_TASKS` and committed task tree; Tasks 3–5's classifier.
- Produces: four frozen records and one script the maintainer runs.

- [ ] **Step 1: Refuse to write a record for a task that did not pass validity**

```bash
cd "$EVALS"
uv run python - <<'PY'
import json, sys
from pathlib import Path
from satyrn_evals.qualify import CENSUS_TASKS

bad = []
for task in CENSUS_TASKS:
    body = json.loads((Path("src/satyrn_evals/tasks") / task / "manifest.json").read_text(encoding="utf-8"))
    validity = body.get("validity")
    if not validity or validity.get("passed") is not True:
        bad.append((task, validity))
for task, validity in bad:
    print(f"no census record for {task}: validity {validity}", file=sys.stderr)
raise SystemExit(1 if bad else 0)
PY
echo "validity=$?"
```

Expected: `validity=0`. A non-zero exit stops this task.

- [ ] **Step 2: Write the four records**

`CAND` is `CENSUS_TASKS` minus night 1's five — read it, do not type it from memory.

```bash
cd "$EVALS"
CAND=$(uv run python -c "
from satyrn_evals.qualify import CENSUS_TASKS
night1 = {'agentclinic-repair-depth-3','selfhost-run-record-gate','selfhost-docs-linter','selfhost-cell-loop','selfhost-speed-probe'}
print(sorted(set(CENSUS_TASKS) - night1)[0])")
echo "CAND=$CAND"

PREV='records/2026-09-16-census-selfhost-speed-probe.result.json'
RULE='none for outcomes: release-two admission is decided in section 8 of 2026-09-15-release-two-census-design.md from the classified table, not from a pass count'
AUTH1='maintainer-approved census night 2, spec 2026-09-17-release-two-census-night-2-design.md section 8; the third medium-build candidate at n = 6'
RG='replacement for contended cells 470484, 533788, 609675 of 2026-09-16-census-selfhost-run-record-gate; originals stand in their denominator and this record is reported beside them, never in their place'
CL='replacement for contended cells 631530, 918779, 320931 of 2026-09-16-census-selfhost-cell-loop; originals stand in their denominator and this record is reported beside them, never in their place'
SP='replacement for contended cells 529092, 941646, 944467 of 2026-09-16-census-selfhost-speed-probe; originals stand in their denominator and this record is reported beside them, never in their place'

new() {  # new TASK N AUTHORITY
  uv run satyrn-evals record new \
    --output "records/2026-09-17-census2-$1.json" --task "$1" --rung R1-plan \
    --arm baseline --model omlx/Ornith-1.5-9B-MLX-8bit \
    --n "$2" --k 3 --purpose admission --isolation isolated --mode batch \
    --max-minutes 240 --token-budget 48000 --turn-budget 72 --command-backstop 4800 \
    --previous-result "$PREV" --authority "$3" --decision-rule "$RULE"
}

new "$CAND"                   6 "$AUTH1"
new selfhost-run-record-gate  3 "$RG"
new selfhost-cell-loop        3 "$CL"
new selfhost-speed-probe      3 "$SP"
```

All four pin the same committed night-1 result (Ruling 12). `--command-backstop 4800` satisfies the gate `4800 + 300 <= 240 * 60`, and the derived per-cell wall clock is 5,100 s (Ruling 13).

Then check every one:

```bash
for r in records/2026-09-17-census2-*.json; do
  case "$r" in *.result.json) continue;; esac
  uv run satyrn-evals launch --check "$r"; echo "$r=$?"
done
uv run python -c "
import json, glob
for p in sorted(glob.glob('records/2026-09-17-census2-*.json')):
    if p.endswith('.result.json'): continue
    b = json.load(open(p))
    print(b['task'], b['rung'], b['n'], b['k'], b['token_budget'], b['turn_budget'],
          b['command_backstop_s'], b['max_minutes'], b['mode'], b['isolation'], b['purpose'])
    print('   prev:', b['previous_result'])
    print('   auth:', b['authority'])
"
```

Expected: every `=0`; one line per record reading `<task> R1-plan <n> 3 48000 72 4800 240 batch isolated admission`, `n` being 6 for the candidate and 3 for each replacement; every `prev` the same committed night-1 speed-probe result; each replacement's `auth` the spec's sentence with its own three cell ids.

- [ ] **Step 3: Write the launch script**

Create `scripts/census_night_2.sh` and `chmod +x` it. It is `scripts/census_night.sh` with the task list, the record prefix and the candidate lookup changed, and nothing else:

```sh
#!/bin/sh
# census_night_2.sh -- run the 2026-09-17 census night 2, in order, from the evals checkout.
# Four records: the third medium-build candidate at n = 6, then three n = 3 replacement
# records for the nine cells the 2026-09-16 night lost to a 3,000 s backstop on a shared
# machine. Each record's result is committed before the next record launches.
# Exits with the last launcher exit code, or 2 before any launch.
set -u
TRAILER="Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
ARM=arms/baseline-ornith15-9b.json
CAND=<CANDIDATE>                # the task Task 2 cut; must match records/2026-09-17-census2-$CAND.json
TASKS="$CAND selfhost-run-record-gate selfhost-cell-loop selfhost-speed-probe"

# Settings provenance, both arms, as the cell user. A disagreement here means the
# oMLX entry or the cell's models.json is not at 16,000; nothing launches.
for a in arms/baseline-ornith15-9b.json arms/engine-ornith15-9b.json; do
  uv run python scripts/preflight_settings.py "$a" --cell > /dev/null || {
    echo "census2: preflight_settings failed for $a" >&2; exit 2; }
done

S=2
for T in $TASKS; do
  R="records/2026-09-17-census2-$T.json"; RES="records/2026-09-17-census2-$T.result.json"
  [ -f "$R" ] || { echo "census2: missing $R" >&2; exit 2; }
  if [ -f "$RES" ] && [ "$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["status"])' "$RES")" = "complete" ]; then
    echo "census2: $T already complete"; continue
  fi
  S=4
  while [ "$S" -eq 4 ]; do          # 4 is CAPPED: the launcher resumes the same record
    uv run satyrn-evals launch "$R" --arm "$ARM"; S=$?
  done
  if [ -f "$RES" ]; then
    STATUS=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["status"])' "$RES")
    git add "$RES" && { git diff --cached --quiet || git commit -qm "Census night 2 result: $T ($STATUS)

$TRAILER"; }
  fi
  [ "$S" -eq 0 ] || { echo "census2: $T stopped with $S; the remaining records are not launched" >&2; break; }
done
echo "census2 EXIT: $S"; exit "$S"
```

Replace `<CANDIDATE>` with the value `CAND` printed in Step 2 — it is the one line in this file that Task 2 determines. Ruling 14: the order is the spec's, a non-zero launcher exit stops the remaining records, and a record the night never reaches is left untouched and stays launchable because its `previous_result` is already committed.

- [ ] **Step 4: Prove the script's gates without launching**

```bash
sh -n scripts/census_night_2.sh; echo "syntax=$?"
sh -c 'set -u; CAND='"$CAND"'; TASKS="$CAND selfhost-run-record-gate selfhost-cell-loop selfhost-speed-probe";
  for T in $TASKS; do [ -f "records/2026-09-17-census2-$T.json" ] || echo "MISSING $T"; done'; echo "records=$?"
grep -n 'census2\|4800\|2026-09-17-census2' scripts/census_night_2.sh | head
uv run python scripts/preflight_settings.py arms/baseline-ornith15-9b.json --cell > /dev/null; echo "settings=$?"
```

Expected: `syntax=0`, no `MISSING` line, and the grep showing the prefix everywhere. `settings` may be non-zero until the operator has restarted oMLX with the 16,000 cap; record which it printed — it is the operator's step, not this task's.

- [ ] **Step 5: Extend the frozen-record guard — write the failing test first**

The guard is what caught the 2026-09-16 record-drift gap. Rewrite `tests/test_census_records_frozen.py` so both nights are parametrized and night 2's parameters are pinned:

```python
"""The frozen census records still match the task trees they pin, and night 2's
four records carry the parameters their design fixed.

A record's ``task_tree_sha256`` is checked by the launcher at launch, which
refuses on drift; these rows catch the drift in the default tier instead, before
a night is started. The 2026-09-16 fix wave moved ``selfhost-cell-loop``'s
digest under a record frozen the day before and nothing in the gates saw it.
No model, network, or subprocess.
"""

import json
from pathlib import Path

import pytest

from satyrn_evals.manifest import DEFAULT_TASKS_ROOT
from satyrn_evals.qualify import CENSUS_TASKS
from satyrn_evals.task_tree import tree_digest

RECORDS = Path(__file__).resolve().parent.parent / "records"


def _frozen(prefix: str) -> list[Path]:
    return sorted(p for p in RECORDS.glob(f"{prefix}*.json") if not p.name.endswith(".result.json"))


NIGHT1 = _frozen("2026-09-16-census-")
NIGHT2 = _frozen("2026-09-17-census2-")
NIGHT1_TASKS = {
    "agentclinic-repair-depth-3", "selfhost-cell-loop", "selfhost-docs-linter",
    "selfhost-run-record-gate", "selfhost-speed-probe",
}
REPLACED = {"selfhost-run-record-gate", "selfhost-cell-loop", "selfhost-speed-probe"}


@pytest.mark.parametrize("record_path", NIGHT1 + NIGHT2, ids=[p.stem for p in NIGHT1 + NIGHT2])
def test_a_frozen_census_record_pins_the_current_task_tree(record_path: Path) -> None:
    record = json.loads(record_path.read_text())
    task_dir = DEFAULT_TASKS_ROOT / record["task"]
    assert record["task_tree_sha256"] == tree_digest(task_dir), (
        f"{record_path.name} pins a tree that has drifted; re-issue the record "
        "with `record new` before the night"
    )


def test_the_five_night_one_records_are_all_present() -> None:
    assert {p.stem.removeprefix("2026-09-16-census-") for p in NIGHT1} == NIGHT1_TASKS


def test_night_two_is_the_three_replacements_and_the_one_new_candidate() -> None:
    added = set(CENSUS_TASKS) - NIGHT1_TASKS
    assert len(added) == 1, "night 2 cuts exactly one new census task (design section 3.1)"
    assert {json.loads(p.read_text())["task"] for p in NIGHT2} == REPLACED | added


@pytest.mark.parametrize("record_path", NIGHT2, ids=[p.stem for p in NIGHT2])
def test_a_night_two_record_carries_the_designs_parameters(record_path: Path) -> None:
    """Design section 4: Baseline, admission, batch, isolated, k = 3, 48,000 / 72,
    a 4,800 s backstop, 240 minutes, chained from the night-1 speed-probe result."""
    record = json.loads(record_path.read_text())
    assert record["arm"] == "baseline"
    assert record["purpose"] == "admission"
    assert record["mode"] == "batch"
    assert record["isolation"] == "isolated"
    assert record["k"] == 3
    assert record["token_budget"] == 48_000
    assert record["turn_budget"] == 72
    assert record["command_backstop_s"] == 4_800
    assert record["max_minutes"] == 240
    assert record["command_backstop_s"] + 300 <= record["max_minutes"] * 60
    assert record["previous_result"] == "records/2026-09-16-census-selfhost-speed-probe.result.json"
    assert record["n"] == (3 if record["task"] in REPLACED else 6)


@pytest.mark.parametrize("task", sorted(REPLACED))
def test_a_replacement_record_says_the_originals_stand_in_their_denominator(task: str) -> None:
    """Design section 4, verbatim: the caveat travels with the record, not only the page."""
    record = json.loads((RECORDS / f"2026-09-17-census2-{task}.json").read_text())
    assert record["authority"].startswith(f"replacement for contended cells ")
    assert f"of 2026-09-16-census-{task};" in record["authority"]
    assert record["authority"].endswith(
        "originals stand in their denominator and this record is reported beside "
        "them, never in their place"
    )
```

Run `uv run pytest tests/test_census_records_frozen.py -q` **before** Step 2's records exist to see the night-2 rows fail (`assert len(added) == 1` or an empty `NIGHT2`), and after to see them pass. Because this task writes the records first, run the file once now and expect PASS; then verify the guard bites by temporarily touching a task tree:

```bash
uv run pytest tests/test_census_records_frozen.py -q; echo "guard=$?"
printf '\n' >> "src/satyrn_evals/tasks/$CAND/manifest.json"
uv run pytest tests/test_census_records_frozen.py -q; echo "drifted=$?"
git checkout -- "src/satyrn_evals/tasks/$CAND/manifest.json"
uv run pytest tests/test_census_records_frozen.py -q; echo "restored=$?"
```

Expected: `guard=0`, `drifted=1` naming the candidate's record, `restored=0`. That is the refusal test and its sibling success test.

- [ ] **Step 6: Record the state in `ROADMAP.md`**

Re-read `ROADMAP.md` first. In the R0 row's "Done when" cell, append one sentence: `Census night 2: four records frozen 2026-09-17 (48,000 tokens, 72 turns, 4,800 s, k = 3; the third build candidate at n = 6 and three n = 3 replacement records for the nine contended cells, Baseline only; docs/superpowers/specs/2026-09-17-release-two-census-night-2-design.md section 4).` Nothing else changes. `wc -l ROADMAP.md` must print at most 150.

- [ ] **Step 7: Provenance, gates, the integration tier, and commit**

```bash
uv run python tools/provenance.py new scripts/census_night_2.sh \
  "records/2026-09-17-census2-$CAND.json" \
  records/2026-09-17-census2-selfhost-run-record-gate.json \
  records/2026-09-17-census2-selfhost-cell-loop.json \
  records/2026-09-17-census2-selfhost-speed-probe.json
just gates; echo "gates=$?"
uv run pytest -m integration; echo "integration=$?"
git add scripts/census_night_2.sh "records/2026-09-17-census2-$CAND.json" \
  records/2026-09-17-census2-selfhost-run-record-gate.json \
  records/2026-09-17-census2-selfhost-cell-loop.json \
  records/2026-09-17-census2-selfhost-speed-probe.json \
  tests/test_census_records_frozen.py ROADMAP.md PROVENANCE.md
git commit -m "Census night 2: four frozen Baseline records at a 4,800 s backstop, the launch script, and the frozen-record guard extended"
```

Expected: `gates=0`. For `integration`, compare against the last recorded baseline (`b624b84`: 335 passed, 1 skipped, 0 failed; the fix wave's final head `134cc61`: 316 passed, 20 skipped, 0 failed — the skip count is environmental and unexplained) and against the known-failing Xcode-license git rows. **A new integration failure is a finding and stops the plan**: `just gates` excludes this tier, so nothing else in the plan would have seen it. Nothing is launched by this task.

---

## Operator commands

Everything in this section is the maintainer's, attended, after Task 6 is committed. No agent runs any of it. `CAND` is the candidate's task name.

**1. Confirm the served per-turn cap is still 16,000 and both arms agree.** The arm files are in git; the two configs are local state and are not. Nothing changed them since night 1, so this is a check, not an edit.

```bash
uv run python scripts/preflight_settings.py arms/baseline-ornith15-9b.json --cell > /dev/null; echo "baseline=$?"
uv run python scripts/preflight_settings.py arms/engine-ornith15-9b.json --cell > /dev/null; echo "engine=$?"
```

Expected: `baseline=0` and `engine=0`. A non-zero exit names the field and the two values; fix the config, never the arm file, and restart oMLX. **Nothing launches until both are 0.**

**2. Preflight the cell, and hunt.**

```bash
uv run satyrn-evals launch --preflight "records/2026-09-17-census2-$CAND.json" --arm arms/baseline-ornith15-9b.json; echo "preflight=$?"
```

Expected: `preflight=0`, and the printed JSON's `problems` empty and `hunt_hits` empty. This runs the root-anchored hunt as the cell user; a hit is grader material reachable from `/` and stops the night. Note that the candidate is a task the hunt has never covered before — its hidden test module's basename is new to `hunt_names`.

**3. Confirm the cells root is empty, the tree is clean, and the records are frozen.**

```bash
sudo ls -la /Users/Shared/satyrn-cells/ | head
git status --porcelain; echo "dirty=$?"
git log --oneline -1
uv run pytest tests/test_census_records_frozen.py -q; echo "frozen=$?"
```

Expected: no leftover worktree parents beyond the committed engine export; `git status --porcelain` prints nothing; the head is Task 6's commit; `frozen=0`. A record must be tracked and unchanged against `HEAD` or `launch` refuses it.

**4. The quiet-machine precondition — the maintainer's, and the reason for the whole night.** Nothing else runs on this machine from launch until the script exits: no other model server client, no build, no indexing, no second agent session. Night 1 lost nine cells to a shared machine at 14–26 tok/s per stream against run 2's ~30. **If that cannot be promised for the whole night, launch only record 1** and let records 2–4 wait for a night that can:

```bash
uv run satyrn-evals launch "records/2026-09-17-census2-$CAND.json" --arm arms/baseline-ornith15-9b.json
```

Then commit its result and stop. The `decode tok/s` column of the morning's tables is how the census page shows whether the precondition held.

**5. Start the night.**

```bash
sh scripts/census_night_2.sh 2>&1 | tee "$HOME/satyrn-census-night-2.log"
```

Expected: about five hours for fifteen cells (spec section 4). The script commits each task's result before launching the next. A capped record resumes on the next launch of the same record; nothing restarts from zero and no cell is replaced. An `EXIT:` other than 0 means the launcher established an infrastructure failure and the remaining records were **not** launched — diagnose, repair, and re-run the script, which skips the tasks already complete. A record the night never reached is launched, if at all, in a later attended sitting recorded in the ledger (Ruling 14).

**6. In the morning: commit the results, then classify into night 2's own directory.**

```bash
git status --porcelain -- records
git add records/2026-09-17-census2-*.result.json && git commit -m "Census night 2 results: four Baseline records, 2026-09-17"
for T in "$CAND" selfhost-run-record-gate selfhost-cell-loop selfhost-speed-probe; do
  uv run --project . python evidence/2026-09-16-census/classify.py \
    --night "$HOME/satyrn-runs/2026-09-17-census2-$T" \
    --record "records/2026-09-17-census2-$T.json" \
    --out evidence/2026-09-17-census-2 \
    --grade-root "$HOME/satyrn-census-grades"
  echo "$T=$?"
done
```

Expected: four `=0`, and `evidence/2026-09-17-census-2/<task>/{cells.json,table.md,classes.md}` for each. **`--out` is not optional** (Ruling 11): without it three of the four would overwrite night 1's committed tables, and the driver refuses rather than doing so. The eight class columns in `classes.md` are empty: filling them is the attended review, argued from the reconstruction and cited by turn, for these 15 cells and for night 1's 30. Then the census page `evidence/2026-09-16-census/README.md` (≤ 120 lines, a fenced recompute block, covering both nights and citing both output directories), and the R0 sitting.

---

## Self-review against the spec

- **Section 3.1, the third candidate.** Task 1 surveys the three Phase 2 plans against seven stated rejection criteria (Ruling 1), measures the hidden-test count and the public-suite seconds rather than estimating them, predicts the validity risk (Ruling 2), proposes two and **stops**. Task 2 cuts the pick, runs `check` and `qualify`, extends `CENSUS_TASKS`, runs the R0 §1.2 check exactly as the procedure spec's Recompute block does — solver sees `base/` and the prompt and nothing else, controller harvests, two named leak tells, grade from a marker-free root, verdict from the receipt — preserves the artefacts under `evidence/2026-09-17-census-2/validity/<task>/`, and records `validity.by` as the model that actually ran (Ruling 17). The drop-and-cut-the-second path and the single permitted prompt-edit path are both written out.
- **Section 3.2, the 32k-line actual.** Task 3: `actual_at_line` in the package with boundary fixtures on both axes and both directions, the 48k verdict kept as `verdict@32k`'s sibling column, both readings in the per-task tally, the class flags moved to the same line (Ruling 5), night 1's five outputs regenerated and the change named in the commit, and the diff confined to a predicted list with four named cells (Ruling 6). `tripped_verdict`'s treatment is Ruling 3 with its own fixture.
- **Section 3.3, decode rate per cell.** Task 4: a pure `census_decode` module using `run-2/serverlog.py`'s pattern verbatim, token-weighted (Ruling 8) with the per-completion median beside it, the span from the attempt stamp to `attempt.json`'s mtime, the timezone stated and stamped (Ruling 9), four null reasons (Ruling 10), `decode_overlap` stating the k = 3 limit the log cannot resolve (Ruling 7), added to `cells.json`, `table.md` and `classes.md`, night 1's tables carrying it, and **no harness change**.
- **Section 3.4, nothing else changes.** Ruling 18: no edit to `counterfactual.py`, the arms, the launcher, the five night-1 task trees or `census_night.sh`; the per-turn cap, tripped harvest, backstop field and evidence fields run as frozen.
- **Section 4, the night.** Task 6: four records with every value from the table (Baseline, admission, batch, isolated, k = 3, 48,000 / 72, 4,800 s, 240 minutes, n = 6 and three × n = 3), the flat chain (Ruling 12), record 1's authority and the three verbatim replacement authorities (Ruling 15), the night-1 decision rule verbatim, `census_night_2.sh` as the night-1 script with the task list and prefix changed, the order and the unreached-record rule (Ruling 14), and the frozen-record guard extended to the new prefix with parameter and authority rows.
- **Section 5, what every cell records.** As night 1 plus the offline `decode_tok_s`; nothing new in the launcher.
- **Section 6, the day after.** Operator command 6 classifies into night 2's own directory with the overwrite refusal behind it (Ruling 11); the eight class columns stay the reviewer's; the census page and the R0 sitting are the maintainer's attended work and are not in this plan.
- **Section 7, what this night can and cannot decide.** Task 1 Step 6 provides for fewer than two survivors — the census page then says the tier is two tasks wide.
- **Section 9, rules carried.** Isolation, launcher-only inference, records frozen and committed in daylight, no Docker or sandbox, results and reviews written only by their tools, Opus steers and reviews with Sonnet implementing and no haiku, a whole-path reviewer before launch (Task 5), commits at task boundaries with explicit paths, never push, merge or amend — all in the Global Constraints.
- **Carried forward, unfixed by this plan and repeated here so the R0 sitting has them:** the Engine's `DELIVER_TIMEOUT_SECONDS` is 1800 against a 4,800 s record backstop, so an Engine cell stops inside `deliver` far earlier than Baseline — an arm-parity defect to fix **before the first Engine record of release two**, and larger now than it was at 3,000 s; section 3.1's Pi-loop length-stop semantics are still declared, not measured; `tripped_verdict` still has no denominator rule; and the four (now five) validity certifications rest on an instrument the design did not name.
