# Release two R0 — the authored task `selfhost-preflight-quiet` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status: written 2026-09-17 against evals `release-one` at `40ffcb3`; the branch advanced to `5310ccb` (the approved Engine design) while this was being written.** Nothing in the plan pins that sha: `base` is whatever commit Task 1 writes (Ruling 1), and every other step reads the head it finds. Re-read `STATE.md` and the Engine design before starting, in case the Engine spec names this task. Nothing here was executed: no model was run, no record written, nothing under `/Users/Shared/satyrn-cells` or `~/satyrn-runs` touched, nothing written under `docs/results/` or `docs/reviews/`. Seven tasks. Task 6 is a whole-path review by someone who implemented none of the task; Task 7 ends with a frozen record the maintainer starts.

**Goal:** Author the census's third medium-build task — spec first, hidden tests before implementation, roles separated so no party holds both the prompt and the answer — cut it with `tools/cut_task.py`, certify it under R0 §1.2, measure it against the medium tier's size targets, and freeze one Baseline admission record of six cells with its launch script.

**Architecture:** Opus writes one plan heading document containing the task's prose, its interfaces and the full contents of the hidden acceptance suite, written from the design spec before any implementation exists. Sonnet then implements that heading in a fresh git worktree off the heading's own commit, under the ordinary loop, producing exactly one commit: `good`, whose parent is `base`. `tools/cut_task.py` cuts the task from the heading at its commit exactly as the six self-hosted tasks were cut, with one new optional spec key carrying the authored disclosure into the manifest's `generator` block. The R0 §1.2 validity check runs from the cut prompt and `base/` alone. Size is measured, not asserted. Then one record, one script, the frozen-record guard extended, and the operator's checklist. No harness change beyond the disclosure key and its qualification check; no launcher change; no change to the five existing census task trees.

**Tech Stack:** Python 3.14, uv, pytest, ruff, just, git. Reused evals code: `tools/cut_task.py`, `tools/provenance.py`, `satyrn_evals.qualify`, `satyrn_evals.manifest`, `satyrn_evals.task_tree.tree_digest`, `satyrn_evals.attempt.contract_digest`, `scripts/preflight_settings.py`, and the `record new` / `launch` CLI. Nothing in `counterfactual.py`, the arms, the launcher, the existing task trees or the night scripts is touched.

**Spec:** `docs/superpowers/specs/2026-09-17-release-two-authored-task-design.md` (approved by the maintainer 2026-09-17). Section numbers below are that spec's unless another is named. Bound by `docs/superpowers/specs/2026-09-15-release-two-r0-constraints.md`, the census design `docs/superpowers/specs/2026-09-15-release-two-census-design.md`, and the validity procedure `docs/superpowers/specs/2026-09-15-release-two-task-validity.md`. The census's signed reading — `evidence/2026-09-16-census/README.md` and `evidence/2026-09-16-census/classes-summary.md` — fixes the tier this task must land in. The night-2 plan `docs/superpowers/plans/2026-09-17-release-two-census-night-2.md` is the house style for records, scripts, the frozen-record guard, the validity procedure and the whole-path reviewer; like every other plan on this branch it is **evidence for a named question, never guidance**.

---

## Rulings

Each is a decision the spec left open, with the reason it was decided that way and what it costs if it is wrong.

1. **`base` is the release-one commit Task 1 writes — the commit that adds the plan heading document — and `good` is its single child on the branch `worktree-authored-preflight-quiet`.** The spec fixes the relation (`good`'s parent is `base`) but not which commit that is. Taking the heading's own commit means the base tree is the repository as it stood when the task was specified and before anything about the task existed in code: `scripts/preflight_quiet.py` is absent, `tests/test_preflight_quiet.py` is absent, `tools/task_specs/selfhost-preflight-quiet.json` is absent, and `src/satyrn_evals/tasks/selfhost-preflight-quiet/` — the cut tree, which holds the hidden overlay — is absent, because the cut does not happen until Task 3. **What that means for `base/`'s contents:** `cut_task.py` archives `base` minus `docs/superpowers/plans/`, `docs/superpowers/specs/`, `.claude/`, `.github/`, `PROVENANCE.md` and the HIDDEN files, so the base tree a cell receives is this repository's `src/`, `tests/` (minus the hidden module), `scripts/`, `tools/`, `records/`, `evidence/`, `arms/`, `STATE.md`, `ROADMAP.md`, `BRIEF.md`, `AGENTS.md`, `Justfile`, `pyproject.toml` and `uv.lock` — including the five night-1 task trees and their overlays, exactly as the six cut tasks' base trees already do, and **not** including this task's own answer in any form. **Cost if wrong:** if `base` were taken any later than Task 3's commit the cell would receive its own hidden suite in `src/satyrn_evals/tasks/selfhost-preflight-quiet/overlay/`, which is total leakage; Task 3 Step 5 checks for exactly that mechanically rather than trusting this ruling.

2. **The hidden suite uses no subprocess and no real `ps` because every input is a string and the CLI takes its four readings from injected callables.** `main(argv=None, *, loadavg, cores, read_ps, read_log)` defaults to the real `os.getloadavg`, `os.cpu_count`, a `subprocess.run(["ps", "-axo", "pid,pcpu,comm"])` reader and a reader of oMLX's server log; the suite passes lambdas returning fixed strings and reads stdout with `capsys` and the exit code from `main`'s return value. Nothing in the suite imports `subprocess`, opens a socket, or touches `/proc`, `~/.omlx/` or the load average. Reason: the default test tier's audit hook in `tests/conftest.py` forbids model, network and subprocess, the hidden suite is run by the grader on a machine that has neither the model server nor a quiet machine to observe, and a suite that shelled out to `ps` would measure the grading host rather than the implementation. Injection is also what makes both CLI directions testable at all — a quiet machine and a loud one, on the same host, in the same second. **Cost if wrong:** the real readers are the one part of the module the suite never executes; Task 6's whole-path review reads them by eye, and the deferred `launch --preflight` wiring (Ruling 8) is where they first run for real.

3. **The `formats` string is the one fixed in Task 3 Step 1 and reproduced there in full.** It carries the spec's four messages verbatim — `load <one-minute> > <ceiling × cores> (<cores> cores)`, `busy: <comm> pid <pid> at <pcpu>% cpu`, `decode <rate> tok/s < <floor> over last <n> completions`, `decode: fewer than <n> completions for <model>` — and, in the shape `tools/task_specs/selfhost-speed-probe.json`'s `formats` established, every other literal the suite matches: the dataclass field names, the `as_dict()` JSON shape, the four CLI defaults, the default ignore list, the one-decimal formatting, and the direction of each threshold. Reason: `r1_plan_prompt` strips every fenced block, so a literal that lives only in the heading's code is a fact the prompt does not determine and therefore an R0 §1.2 failure waiting to happen; `formats` is the sanctioned channel for exactly those literals, and the design already names the message paragraph as the task spec's `formats`. **Cost if wrong:** a literal left out shows up as a validity failure in Task 4 and is then repairable only as a recorded prompt edit, which weakens the task's provenance for no gain.

4. **`authored: true` is a new optional key in the cut spec, written by `cut_task.py` into the manifest's `generator` block as `"authored": true` beside `"authoring": {"spec": ..., "roles": {...}}`, and checked by a new `qualify` check `authored-disclosure`.** The two alternatives were both rejected. Writing it by hand into `generator` after the cut is refused by `cut_task.py check`, which compares the whole manifest minus the post-cut keys — the disclosure would show up as a tree that differs from a fresh cut. Adding it to `POST_CUT_MANIFEST_KEYS` beside `validity` would make it a field `check` deliberately ignores, i.e. a disclosure anybody may edit or delete without any command noticing: the opposite of what a disclosure is for. Making it an **optional** spec key keeps every already-cut task re-cutting byte-identically (the same reason `prompt_edits` is optional, `cut_task.py`'s own comment), puts the disclosure inside the manifest that `check` compares, and lets `qualify` refuse a malformed one. The new check is pure and reads the manifest body only: when `generator.authored` is present it must be exactly `true`, `generator.authoring.spec` must be a non-empty path string, and `generator.authoring.roles` must be a non-empty mapping of non-empty strings to non-empty strings; a task without the key is a cut task and passes untouched. **Cost if wrong:** one optional key and one pure check are added to two files that six committed task trees depend on; Task 3 Step 3 re-runs `cut_task.py check` over all six to prove none moved, and the check is the gate on that.

5. **The leak tells for an authored task are the two named in the validity procedure plus three of its own, and the cut prevents the model reading the answer by construction, not by instruction.** The author's plan document lives at `docs/superpowers/plans/2026-09-18-preflight-quiet.md`, inside the repository whose tree becomes `base/`. It is excluded by `cut_task.py`'s `EXCLUDED_PREFIXES`, which drops `docs/superpowers/plans/` and `docs/superpowers/specs/` wholesale — so neither the heading (with the hidden suite in it) nor the design spec is in `base/`, and no instruction to the solver or the cell is load-bearing. The three added tells, all run mechanically in Task 3 Step 5 over the cut tree: (a) `base/` contains no path under `docs/superpowers/`; (b) `base/` contains no file whose text holds `preflight_quiet`, `load_problem`, `busy_processes`, `decode_rate` or `certificate`; (c) `base/src/satyrn_evals/tasks/selfhost-preflight-quiet` does not exist. The validity solver's off-limits list additionally names the plan document and the design spec individually, as the procedure requires instructions to be checkable. The cell gets the same `base/` and reaches nothing else: it runs as `satyrn-cell`, and the preflight's root-anchored hunt — whose `hunt_names` now includes this task's hidden basename — is the standing check on grader material reachable from `/`. **Cost if wrong:** an authored task whose answer is reachable is not a census task at all, which is why (a)–(c) are a gate on the cut and not a paragraph in a README.

6. **Wiring the check into `launch --preflight` is deferred, as the spec says, and is named here as carried-forward work rather than left implicit.** Doing it inside the task would add `src/satyrn_evals/cell_preflight.py` to `files`, which makes the task two modules — outside the medium tier's "one new module" size target measured in Task 5 — and gives the generator a second module to stub, changing the broken fixture's shape. Deferring it also keeps the good commit's diff to exactly the two new files the size target names. It is a separate later commit outside this plan, recorded in Task 7's ROADMAP sentence. **Cost if wrong:** the machine-quiet check exists and is tested but nothing calls it until that commit lands, so night 3 itself is still preceded by the maintainer's own judgement of a quiet machine, exactly as nights 1 and 2 were.

7. **The record is written last, after every edit to the task tree, because `tests/test_census_records_frozen.py` pins `tree_digest(task_dir)` over the whole directory including `manifest.json`.** The `validity` block (Task 4) and the disclosure (Task 3) are both manifest writes; a record frozen before either would pin a digest the next commit moves, and the guard would go red on a tree nobody broke. Task 5 measures and Task 6 reviews, and neither writes into `src/satyrn_evals/tasks/selfhost-preflight-quiet/`. **Cost if wrong:** a red guard and a re-issued record — loud, cheap, and caught inside the plan.

8. **The R0 §1.2 check runs on the harness's selectable model, and the model that ran is recorded in `validity.by`.** Night 1 could not select the design's named instrument and the maintainer ratified the substitution on 2026-09-16 as the instrument for R0 §1.2. This task carries that ratification: request the named role, use what the harness offers, record it, repeat the maintainer's standing caveat in the validity README, and do **not** stop. A harness that could honour no role at all, or a substitution that had not been ratified, would be a stop. **Cost if wrong:** this task's certification reads as slightly weaker than the design's named instrument, exactly as the five before it do.

9. **A validity failure gets a recorded `prompt_edits` entry only when the fact it turns on is stated in the heading's stripped code; every other failure stops the plan for the maintainer.** The spec's own remedy, narrowed to a testable condition: the edit is permitted when the missing fact can be pointed at inside a fenced block of the heading, because that is the class of failure the R1-plan rung creates by construction. A failure that traces to a fact the spec never stated anywhere is a design gap, and a failure that traces to a genuinely ambiguous prose sentence is a task defect — neither is patched by an agent mid-plan. **Cost if wrong:** one attended sitting for the maintainer instead of an agent quietly editing the prompt until the solver passes, which is the failure mode the R0 §1.2 gate exists to prevent.

10. **The size targets are measured on the artefacts the census will use, not on the worktree.** Hidden test count is the length of the cut manifest's `expected_test_ids` (the suite collected at `good` by the generator); public-suite seconds are wall-clock `uv run pytest -q -m "not integration"` in a clean checkout of `base`; the diff is `fixtures/known-good.patch`'s paths plus the good commit's own `--name-only` listing. Reason: the manifest's ids are what the grader executes, and the base tree is what the cell runs its public suite in — measuring anywhere else measures something the cell never sees. **Cost if wrong:** a target measured on the wrong artefact would let a task into the medium tier that does not belong there, and the tier is what the R0 claim is sized on.

11. **A missed size target re-scopes the task before admission, and Task 5 is the last point at which that is cheap.** The spec is explicit — "a task that misses a target is re-scoped before it is admitted, never after". If the hidden count lands outside 15–20, or the public suite reaches 40 s, or the good diff touches a third module, Task 5 stops the plan with the measured number; it does not adjust a target, delete a test to fit, or proceed and note it. **Cost if wrong:** the census page would carry a task the tier's definition does not hold, and the claim table's third column would not mean what its two neighbours mean.

12. **The good commit's diff is two new files plus a `PROVENANCE.md` row, and the size target is read against the graded diff.** `PROVENANCE.md` is in the manifest's `ignored_paths` and is excluded from `base/`; `AGENTS.md` requires a row per file and `just gates` fails without one, so the good commit must carry it. The target "touches one new module and one new test module only" is therefore read as: `fixtures/known-good.patch` touches exactly `scripts/preflight_quiet.py`, and the good commit touches exactly that, `tests/test_preflight_quiet.py` and `PROVENANCE.md`. **Cost if wrong:** none if stated; the risk is a reviewer reading "two files" against a three-file commit and calling a passing target a failure.

13. **The hidden suite is proved unedited by two mechanical checks, not by an assurance.** Its sha256 is recorded in the ledger the moment it is written and before any implementation file exists, and re-checked immediately before the good commit; and its bytes must equal the heading document's first fenced Python block, checked by script in Tasks 2 and 5. Reason: "the hidden tests are not edited to fit the implementation" is the whole reason this task can be called developer-written, and an implementer under a red suite has every incentive and no supervision. **Cost if wrong:** the task's premise fails silently, which is worse than a red suite; two hashes make it fail loudly.

14. **The night-3 record chains from `records/2026-09-17-census2-selfhost-speed-probe.result.json`, the last committed census result on the branch.** Night 2 ran three replacement records in that order and its speed-probe result is the tail of the committed chain; night 2's withdrawn first record never existed. **Cost if wrong:** `record new` refuses a `previous_result` that is not committed, so a wrong pointer fails at write time rather than at launch.

15. **Validity artefacts go under `evidence/2026-09-17-census-2/validity/selfhost-preflight-quiet/` as the spec directs, while night 3's classifier outputs go under `evidence/2026-09-18-census-3/`.** The split is the spec's and looks odd, so it is stated rather than tidied: the certification belongs with the census-2 validity set it was run the same way as, and the night's cells belong to their own night. The classifier's `--out` is not optional and its `night` key refuses an overwrite of another night's directory. **Cost if wrong:** a reader looks for the certificate under the night-3 directory; the README in each directory cross-references the other.

16. **Nothing in this plan touches `counterfactual.py`, the arms, the launcher, the existing task trees, `census_night.sh` or `census_night_2.sh`.** The pre-registered instrument stays the instrument; the two frozen night scripts are history. `scripts/census_night_3.sh` is a new file of the night-2 script's shape with one record in its task list. **Cost if wrong:** none — the alternative makes this census a different instrument from the two nights it is reported beside.

---

## Global Constraints

- **Roles: Sonnet implements each task, Opus reviews it, Sonnet re-reviews the fix diff (scoped). No haiku. Fable only if the maintainer names it.** Task 1 is Opus's own authoring work, by the spec's role separation; Task 2's implementer must not be the agent that wrote Task 1's document. One fresh implementer per task; the controller blocks on every dispatch and nothing runs in the background.
- **No model inference during building, and no network.** No `launch`, no oMLX request, no GPU. Task 4's validity solver is a cloud model working from text and is the only agent that writes code from a prompt; it never touches the GPU.
- **Nothing under `/Users/Shared` is read or written; `~/satyrn-runs` is read-only; nothing is written to `/tmp` or `/private/tmp`.** Scratch work goes in the session scratchpad (`SCRATCH`). Grade roots go under `$HOME/satyrn-census-grades/`.
- **Tests are verified in a scratch clone under the scratchpad, never in the main checkout**, except Task 2's implementation, which happens in a git worktree created for it and removed at the end of the task: `git clone --branch release-one "$EVALS" "$SCRATCH/evals" && cd "$SCRATCH/evals" && uv sync`.
- **`just gates` exits 0 at the end of every task**, run in the evals tree, reading the exit code and never piping a gate. **The integration tier is not in `just gates`** and is checked once at the end of Task 7: `uv run pytest -m integration`. Known failing before any of this: the Xcode-license git integration rows (`/usr/bin/git` needs `sudo xcodebuild -license accept`).
- **Every new file gets a `PROVENANCE.md` row** (`uv run python tools/provenance.py new <paths>`); `just gates` fails without one.
- **Docs caps:** `docs/superpowers/specs/*.md` ≤ 400 lines, `docs/results/*.md` ≤ 120 lines (none written), `ROADMAP.md` ≤ 150 lines. Plans are uncapped.
- **The default test tier uses no model, network or subprocess**; `tests/conftest.py`'s audit hook enforces it. Every refusal test has a sibling success test (BRIEF invariant 5). Every new rule is tested in both directions. **Every review finding becomes a default-tier test.**
- **Grade from hook-written evidence, never stdout or exit status.** Verdicts are read from a receipt's `verdict` field. Count events from `tool_execution_start`, one per call; never `grep -c`.
- **Commit per task on evals `release-one` with explicit paths only.** Never `git add -A`, `git add .`, `git commit -a`, `--amend`, merge or push. A task whose gates are red is not committed. End every commit message with the session's attribution trailer.
- **A stop is a stop.** An agent stops at an underspecified task, a task that fails acceptance twice, a red gate whose fix is not in this plan, a missed size target (Ruling 11), a validity failure that is not the one permitted class (Ruling 9), or any step that wants inference.
- **Digests that must not move:** all five existing census task trees. `tests/test_census_records_frozen.py` fails the gates if one does; a fix that moves a task tree must re-issue every record that pins it (the maintainer's 2026-09-16 ruling).
- **Do not touch:** `evidence/2026-09-15-finishing-counterfactual/counterfactual.py`, `arms/*.json`, the launcher (`src/satyrn_evals/launch*.py`, `cell_*.py`), the five existing task trees under `src/satyrn_evals/tasks/`, `scripts/census_night.sh`, `scripts/census_night_2.sh`, and everything under `/Users/Shared/satyrn-cells`. Write nothing under `docs/results/` or `docs/reviews/`.
- **Worktrees:** the seven worktrees under `.claude/worktrees/` are historical evidence of earlier work — do not enter, modify or remove them. Task 2 creates one fresh worktree and removes it at the end of that task; its **branch ref is kept**, because `base` and `good` must stay reachable for `cut_task.py` and for the manifest's provenance shas.
- **Night-3 constants, verbatim from the spec:** one record; Baseline arm only; `--purpose admission`; `--mode batch`; isolated; n = 6; k = 3; token budget 48,000; turn budget 72; per-turn cap 16,000 (served, unchanged); `--command-backstop 4800`; `--max-minutes 240`; chained from `records/2026-09-17-census2-selfhost-speed-probe.result.json`; the night-1 decision rule; quiet machine; six cells; estimated three hours.
- **Names fixed by this plan, used verbatim everywhere:** task `selfhost-preflight-quiet`; module `scripts/preflight_quiet.py`; hidden suite `tests/test_preflight_quiet.py`; heading document `docs/superpowers/plans/2026-09-18-preflight-quiet.md`; heading `### Task 1: The machine-quiet preflight`; branch `worktree-authored-preflight-quiet`; record `records/2026-09-18-census3-selfhost-preflight-quiet.json`; script `scripts/census_night_3.sh`.
- **Evals checkout** `/Users/pauleveritt/projects/pauleveritt/satyrn-evals` (`EVALS`); starting point `release-one` at its current head (`40ffcb3` when this was written, `5310ccb` by the time it was finished; Ruling 1 pins nothing to either). All commands run from `EVALS` unless a step says otherwise.

---

## File structure

```
docs/superpowers/plans/2026-09-18-preflight-quiet.md        # T1: the authored heading, with the hidden suite in it (create)
scripts/preflight_quiet.py                                  # T2: the module, in the worktree, at `good`      (create)
tests/test_preflight_quiet.py                               # T2: the hidden suite, at `good`                 (create)
tools/task_specs/selfhost-preflight-quiet.json              # T3: the cut spec, with the authored disclosure  (create)
src/satyrn_evals/tasks/selfhost-preflight-quiet/            # T3: the cut task tree                           (create)
tools/cut_task.py                                           # T3: the optional `authored` spec key            (modify)
src/satyrn_evals/qualify.py                                 # T3: CENSUS_TASKS, judge_authored                (modify)
tests/test_cut_task.py                                      # T3: the key, both directions                    (modify)
tests/test_qualify.py                                       # T3: the census map and judge_authored           (modify)
tests/test_census_records_frozen.py                         # T3: CENSUS_TASKS is night 1 + one; T7: night 3  (modify)
evidence/2026-09-17-census-2/validity/selfhost-preflight-quiet/   # T4: PROMPT.txt, solution.diff, receipt.json, REPORT.md (create)
evidence/2026-09-17-census-2/validity/README.md             # T4: the run, the model, the tells               (create)
evidence/2026-09-17-census-2/validity/selfhost-preflight-quiet/SIZE.md  # T5: the three measured targets      (create)
records/2026-09-18-census3-selfhost-preflight-quiet.json    # T7: the frozen record                           (create)
scripts/census_night_3.sh                                   # T7: the one-record launch script                (create)
ROADMAP.md                                                  # T7: the R0 row                                  (modify)
PROVENANCE.md                                               # T1, T2, T3, T4, T5, T7                          (modify)
.superpowers/sdd/2026-09-18-authored-task-preflight-quiet/progress.md  # the ledger (git-ignored, never committed)
```

**Names later tasks rely on:**

```python
# scripts/preflight_quiet.py  (T2) — the module the census task builds
@dataclass(frozen=True, slots=True)
class Process:
    pid: int; comm: str; cpu: float
@dataclass(frozen=True, slots=True)
class Rate:
    tok_s: float; completions: int; tokens: int; seconds: float
@dataclass(frozen=True, slots=True)
class Certificate:
    problems: tuple[str, ...]; record: dict[str, object]
    def as_dict(self) -> dict[str, object]: ...
IGNORE_PREFIXES: tuple[str, ...]
def load_problem(loadavg: tuple[float, float, float], cores: int, *, ceiling: float) -> str | None: ...
def busy_processes(ps_stdout: str, *, cpu_floor: float, ignore_prefixes: Sequence[str]) -> list[Process]: ...
def decode_rate(log_lines: Iterable[str], *, model: str, last: int) -> Rate | None: ...
def certificate(load: str | None, busy: Sequence[Process], rate: Rate | None, *,
                floor_tok_s: float, model: str, last: int) -> Certificate: ...
def main(argv: Sequence[str] | None = None, *, loadavg=..., cores=..., read_ps=..., read_log=...) -> int: ...

# tools/cut_task.py  (T3)
_OPTIONAL_SPEC_KEYS = frozenset({"prompt_edits", "authored"})
@dataclass(frozen=True, slots=True)
class Authored:
    spec: str
    roles: dict[str, str]
# TaskSpec gains:  authored: Authored | None = None
# manifest generator gains, when set:  "authored": True, "authoring": {"spec": ..., "roles": {...}}

# src/satyrn_evals/qualify.py  (T3)
def judge_authored(manifest_body: dict) -> Check: ...   # name "authored-disclosure"
CENSUS_TASKS["selfhost-preflight-quiet"] = PLAN_RUNG
```

---

### Task 1: Opus writes the plan heading document, hidden suite included

Spec section 3, role 1. **This task is Opus's.** The agent that writes this document must not be the agent that implements Task 2, and the document is written from `docs/superpowers/specs/2026-09-17-release-two-authored-task-design.md` section 2 — not from any implementation, which does not exist yet.

**Files:**
- Create: `docs/superpowers/plans/2026-09-18-preflight-quiet.md`
- Modify: `PROVENANCE.md`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: the commit that Task 3's cut spec names as `base` and as `plan.commit`; a document holding exactly one `### Task 1: The machine-quiet preflight` heading whose section is what `cut_task.py`'s `plan_section` + `r1_plan_prompt` turn into the R1-plan prompt; and, in its first fenced Python block after Step 1, the byte-exact contents of `tests/test_preflight_quiet.py`.

- [ ] **Step 1: Re-read the two sources and note the shape the cut requires**

Read `docs/superpowers/specs/2026-09-17-release-two-authored-task-design.md` section 2 and `tools/cut_task.py`'s `plan_section` and `r1_plan_prompt`. Four mechanical facts govern the document:

1. `plan_section` takes the lines from the heading up to the **next** `## `/`### ` heading or a line that is exactly `---`. So the task section must contain no horizontal rule and no sub-heading; a `---` anywhere inside it silently truncates the prompt.
2. `r1_plan_prompt` drops every fenced block, every `- Consumes:` line, the `### ` prefix, the `- [ ] ` markers and the `**` emphasis. **Everything inside a fence is invisible to the model.** Every structural fact the suite asserts must therefore be in prose, in `Produces:`, or in the spec's `formats` (Task 3).
3. Hidden paths are rewritten: `tests/test_preflight_quiet.py` becomes `tests/` and the bare basename becomes "a test module under tests/". Write the path, never the phrase "its test module" — `qualify` refuses that retired stand-in.
4. `judge_prompt` requires every backticked path-like token on a `- Create:`/`- Modify:`/`- Test:` line, and every argument of a backticked `uv run pytest` command, to be a `source_paths` entry, a file in `base/`, or a directory in `base/` written with a trailing slash.

- [ ] **Step 2: Write the document**

Write `docs/superpowers/plans/2026-09-18-preflight-quiet.md` with exactly these bytes. The hidden suite is written here, from the spec, before any implementation exists — that is the whole point of the role separation, and Ruling 13 is how it is proved later.

````markdown
# The machine-quiet preflight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A standalone script that says, with evidence, whether this machine is quiet enough to start a census night.

**Architecture:** One new module, `scripts/preflight_quiet.py`, with a pure API and a thin CLI over it. Three readings — the one-minute load against the core count, the busy processes in a `ps` snapshot, and the recent decode rate from the model server's log — each parsed from a string by a pure function, and one `certificate` that turns the three into a problems list and a JSON record of its inputs. The CLI takes its four readings from injected callables so the whole module is testable without a subprocess, the network, or a loud machine.

**Tech Stack:** Python 3.14, standard library only (`argparse`, `dataclasses`, `json`, `os`, `re`, `subprocess` for the real `ps` reader), pytest.

**Spec:** `docs/superpowers/specs/2026-09-17-release-two-authored-task-design.md` section 2.

## Global Constraints

- Python 3.14, standard library only; no new dependency.
- The acceptance suite runs in the default test tier: no model, no network, **no subprocess**, no real `ps`, no real server log, no reading of the machine's own load. Every input is a string or a number.
- Every refusal has a sibling success: each parser is exercised on a known-good and a known-bad input, and each threshold at its edge and across it.
- `scripts/preflight_quiet.py` is the only source module this work creates.

### Task 1: The machine-quiet preflight

**Files:**
- Create: `scripts/preflight_quiet.py`
- Test: `tests/test_preflight_quiet.py`

**Interfaces:**
- Consumes: nothing; the module stands alone and imports only the standard library.
- Produces: `load_problem(loadavg: tuple[float, float, float], cores: int, *, ceiling: float) -> str | None`; `busy_processes(ps_stdout: str, *, cpu_floor: float, ignore_prefixes: Sequence[str]) -> list[Process]`; `decode_rate(log_lines: Iterable[str], *, model: str, last: int) -> Rate | None`; `certificate(load: str | None, busy: Sequence[Process], rate: Rate | None, *, floor_tok_s: float, model: str, last: int) -> Certificate`; `main(argv: Sequence[str] | None = None, *, loadavg, cores, read_ps, read_log) -> int`; the frozen dataclasses `Process(pid: int, comm: str, cpu: float)`, `Rate(tok_s: float, completions: int, tokens: int, seconds: float)` and `Certificate(problems: tuple[str, ...], record: dict[str, object])` with `Certificate.as_dict()`; and the module constant `IGNORE_PREFIXES`.

- [ ] **Step 1: Write the acceptance suite first, in full**

Write the whole suite before any of the module exists. It imports from `preflight_quiet` with `scripts` on the path, and it drives the CLI through its injected callables rather than through a process, so it obeys the no-subprocess rule of the default tier. Twenty tests: each parser on a known-good and a known-bad input, each threshold at its edge and across it, the ignore list both ways, the token weighting on two completions of unequal length, the fewer-than-N case, the certificate's JSON shape, and both CLI exit codes.

```python
"""The machine-quiet preflight: the acceptance suite, written from the spec.

No network, no subprocess, no real ``ps`` and no real server log: every input
is a string or a number, and the CLI is driven through its injected readers.
"""

import json

import pytest
from preflight_quiet import (
    IGNORE_PREFIXES,
    Process,
    Rate,
    busy_processes,
    certificate,
    decode_rate,
    load_problem,
    main,
)

PS = """\
  PID  %CPU COMM
    1   0.4 /sbin/launchd
  412  93.1 /usr/local/bin/omlx-server
  977  41.7 /Applications/Xcode.app/Contents/MacOS/Xcode
 1201   2.0 /usr/sbin/cfprefsd
"""

QUIET_PS = "  PID  %CPU COMM\n    1   0.4 /sbin/launchd\n"

STAMP = "2026-09-17 21:14:02,004 - omlx.server - INFO - [-] - "
SLOW = (
    STAMP + "Chat completion: model=Ornith-1.5-9B-MLX-8bit, 100 tokens in 20.00s "
    "(5.0 tok/s), prompt: 4000, finish_reason=stop, max_tokens=16000, request_max_tokens=16000"
)
FAST = (
    STAMP + "Chat completion: model=Ornith-1.5-9B-MLX-8bit, 900 tokens in 10.00s "
    "(90.0 tok/s), prompt: 5000, finish_reason=stop, max_tokens=16000, request_max_tokens=16000"
)
OTHER = (
    STAMP + "Chat completion: model=Some-Other-7B, 4000 tokens in 1.00s "
    "(4000.0 tok/s), prompt: 10, finish_reason=stop, max_tokens=16000, request_max_tokens=16000"
)
LOG = [SLOW, FAST]
MODEL = "Ornith-1.5-9B-MLX-8bit"


def test_load_problem_names_the_one_minute_load_over_the_ceiling() -> None:
    assert load_problem((9.5, 4.0, 2.0), 8, ceiling=0.5) == "load 9.5 > 4.0 (8 cores)"


def test_load_problem_is_quiet_at_the_ceiling() -> None:
    assert load_problem((4.0, 4.0, 2.0), 8, ceiling=0.5) is None


def test_busy_processes_reads_a_ps_snapshot_in_order() -> None:
    assert busy_processes(PS, cpu_floor=20.0, ignore_prefixes=()) == [
        Process(pid=412, comm="/usr/local/bin/omlx-server", cpu=93.1),
        Process(pid=977, comm="/Applications/Xcode.app/Contents/MacOS/Xcode", cpu=41.7),
    ]


def test_busy_processes_drops_a_process_whose_comm_starts_with_an_ignored_prefix() -> None:
    busy = busy_processes(PS, cpu_floor=20.0, ignore_prefixes=("/usr/local/bin/omlx-",))
    assert [process.pid for process in busy] == [977]


def test_busy_processes_keeps_a_process_no_ignored_prefix_matches() -> None:
    busy = busy_processes(PS, cpu_floor=20.0, ignore_prefixes=("/usr/sbin/", "/opt/"))
    assert [process.pid for process in busy] == [412, 977]


def test_busy_processes_is_quiet_at_the_cpu_floor() -> None:
    snapshot = "  PID  %CPU COMM\n  310  20.0 /usr/bin/python3\n"
    assert busy_processes(snapshot, cpu_floor=20.0, ignore_prefixes=()) == []


def test_busy_processes_reports_a_process_just_over_the_cpu_floor() -> None:
    snapshot = "  PID  %CPU COMM\n  310  20.1 /usr/bin/python3\n"
    assert busy_processes(snapshot, cpu_floor=20.0, ignore_prefixes=()) == [
        Process(pid=310, comm="/usr/bin/python3", cpu=20.1)
    ]


def test_busy_processes_skips_the_header_and_every_unparsable_line() -> None:
    snapshot = "  PID  %CPU COMM\n\nnot a row\n  310   x.y /usr/bin/python3\n  311  99.0 /usr/bin/yes\n"
    assert [p.pid for p in busy_processes(snapshot, cpu_floor=20.0, ignore_prefixes=())] == [311]


def test_the_default_ignore_prefixes_cover_the_model_server_and_the_system_agents() -> None:
    busy = busy_processes(PS, cpu_floor=20.0, ignore_prefixes=IGNORE_PREFIXES)
    assert [process.pid for process in busy] == [977]


def test_decode_rate_is_token_weighted_not_the_mean_of_the_rates() -> None:
    rate = decode_rate(LOG, model=MODEL, last=2)
    assert rate is not None
    assert rate.completions == 2
    assert rate.tokens == 1000
    assert rate.seconds == pytest.approx(30.0)
    assert rate.tok_s == pytest.approx(1000 / 30.0)
    assert rate.tok_s != pytest.approx((5.0 + 90.0) / 2)


def test_decode_rate_reads_only_the_named_models_completions() -> None:
    rate = decode_rate([SLOW, OTHER, FAST], model=MODEL, last=2)
    assert rate is not None
    assert rate.tokens == 1000


def test_decode_rate_is_none_with_fewer_than_last_completions() -> None:
    assert decode_rate(LOG, model=MODEL, last=3) is None


def test_decode_rate_reads_exactly_last_completions() -> None:
    rate = decode_rate([SLOW, SLOW, FAST], model=MODEL, last=2)
    assert rate is not None
    assert rate.completions == 2
    assert rate.tokens == 1000


def test_decode_rate_ignores_lines_that_are_not_completions() -> None:
    noise = [
        "",
        "2026-09-17 21:10:00,000 - omlx.server - INFO - [-] - Loaded model",
        "Chat completion: model=Ornith-1.5-9B-MLX-8bit, 5 tokens in 1.00s (5.0 tok/s), prompt: 1,",
    ]
    rate = decode_rate([*noise, *LOG], model=MODEL, last=2)
    assert rate is not None
    assert rate.tokens == 1000


def test_certificate_is_empty_on_a_quiet_machine_and_records_its_inputs() -> None:
    rate = Rate(tok_s=41.0, completions=20, tokens=8200, seconds=200.0)
    result = certificate(None, [], rate, floor_tok_s=30.0, model=MODEL, last=20)
    assert result.problems == ()
    body = result.as_dict()
    assert body["problems"] == []
    assert body["inputs"]["load"] is None
    assert body["inputs"]["busy"] == []
    assert body["inputs"]["decode"] == {
        "tok_s": 41.0, "completions": 20, "tokens": 8200, "seconds": 200.0
    }
    assert body["inputs"]["floor_tok_s"] == 30.0
    assert body["inputs"]["model"] == MODEL
    assert body["inputs"]["last"] == 20
    assert json.loads(json.dumps(body)) == body


def test_certificate_lists_the_load_the_busy_and_the_slow_decode_in_order() -> None:
    busy = [Process(pid=977, comm="/Applications/Xcode.app/Contents/MacOS/Xcode", cpu=41.7)]
    rate = Rate(tok_s=18.4, completions=20, tokens=3680, seconds=200.0)
    result = certificate(
        "load 9.5 > 4.0 (8 cores)", busy, rate, floor_tok_s=30.0, model=MODEL, last=20
    )
    assert list(result.problems) == [
        "load 9.5 > 4.0 (8 cores)",
        "busy: /Applications/Xcode.app/Contents/MacOS/Xcode pid 977 at 41.7% cpu",
        "decode 18.4 tok/s < 30.0 over last 20 completions",
    ]
    assert result.as_dict()["inputs"]["busy"] == [
        {"pid": 977, "comm": "/Applications/Xcode.app/Contents/MacOS/Xcode", "cpu": 41.7}
    ]


def test_certificate_has_no_decode_problem_at_the_floor() -> None:
    rate = Rate(tok_s=30.0, completions=20, tokens=6000, seconds=200.0)
    result = certificate(None, [], rate, floor_tok_s=30.0, model=MODEL, last=20)
    assert result.problems == ()


def test_certificate_says_when_there_are_too_few_completions() -> None:
    result = certificate(None, [], None, floor_tok_s=30.0, model=MODEL, last=20)
    assert list(result.problems) == [f"decode: fewer than 20 completions for {MODEL}"]
    assert result.as_dict()["inputs"]["decode"] is None


def test_the_cli_prints_the_certificate_and_exits_zero_on_a_quiet_machine(capsys) -> None:
    code = main(
        ["--model", MODEL, "--floor-tok-s", "10", "--last", "2"],
        loadavg=lambda: (1.0, 1.0, 1.0),
        cores=lambda: 8,
        read_ps=lambda: QUIET_PS,
        read_log=lambda: LOG,
    )
    body = json.loads(capsys.readouterr().out)
    assert code == 0
    assert body["problems"] == []
    assert body["inputs"]["decode"]["completions"] == 2


def test_the_cli_exits_one_and_names_every_problem_on_a_loud_machine(capsys) -> None:
    code = main(
        ["--model", MODEL, "--floor-tok-s", "40", "--last", "2"],
        loadavg=lambda: (9.5, 4.0, 2.0),
        cores=lambda: 8,
        read_ps=lambda: PS,
        read_log=lambda: LOG,
    )
    body = json.loads(capsys.readouterr().out)
    assert code == 1
    assert body["problems"] == [
        "load 9.5 > 4.0 (8 cores)",
        "busy: /Applications/Xcode.app/Contents/MacOS/Xcode pid 977 at 41.7% cpu",
        "decode 33.3 tok/s < 40.0 over last 2 completions",
    ]
```

- [ ] **Step 2: Run the suite and watch every test fail**

Run the acceptance suite from the repository root with `scripts` on the path. Expect a collection error — `ModuleNotFoundError: No module named 'preflight_quiet'` — because the module does not exist yet. That failure is the starting point; do not write the module before seeing it.

```bash
PYTHONPATH=scripts uv run pytest tests/test_preflight_quiet.py -q
```

- [ ] **Step 3: The load reading**

Create `scripts/preflight_quiet.py` with a module docstring, the three frozen dataclasses, the default constants and `load_problem`. `Process` carries `pid` (int), `comm` (str) and `cpu` (float); `Rate` carries `tok_s` (float), `completions` (int), `tokens` (int) and `seconds` (float); both are frozen and slotted. The defaults are module constants: `DEFAULT_CEILING` is 0.5, `DEFAULT_CPU_FLOOR` is 20.0, `DEFAULT_FLOOR_TOK_S` is 30.0, `DEFAULT_LAST` is 20, and `IGNORE_PREFIXES` is the tuple `("/sbin/", "/usr/sbin/", "/usr/libexec/", "/System/", "/usr/local/bin/omlx-")`. `load_problem` takes the three-tuple a load average comes in, the core count, and a keyword-only `ceiling`; it compares only the one-minute figure against `ceiling * cores` and returns `None` when the load is at or below that product — the ceiling itself is quiet — and otherwise the message, with the load and the product each formatted to one decimal place and the bare integer core count in parentheses.

```python
"""Is this machine quiet enough to start a census night?

Three readings, each parsed from a string so the whole module is testable
without a subprocess: the one-minute load against the core count, the busy
processes in a ``ps`` snapshot, and the recent decode rate from the model
server's log. ``certificate`` turns the three into a problems list and a
JSON record of its inputs; the CLI prints it and exits non-zero when the
machine is not quiet.
"""

import argparse
import json
import os
import re
import subprocess
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass

DEFAULT_CEILING = 0.5
DEFAULT_CPU_FLOOR = 20.0
DEFAULT_FLOOR_TOK_S = 30.0
DEFAULT_LAST = 20
IGNORE_PREFIXES: tuple[str, ...] = (
    "/sbin/", "/usr/sbin/", "/usr/libexec/", "/System/", "/usr/local/bin/omlx-",
)
SERVER_LOG = os.path.expanduser("~/.omlx/logs/server.log")


@dataclass(frozen=True, slots=True)
class Process:
    pid: int
    comm: str
    cpu: float


@dataclass(frozen=True, slots=True)
class Rate:
    tok_s: float
    completions: int
    tokens: int
    seconds: float


def load_problem(loadavg: tuple[float, float, float], cores: int, *, ceiling: float) -> str | None:
    one_minute = loadavg[0]
    limit = ceiling * cores
    if one_minute <= limit:
        return None
    return f"load {one_minute:.1f} > {limit:.1f} ({cores} cores)"
```

- [ ] **Step 4: The process snapshot**

Add `busy_processes`. It reads the output of `ps -axo pid,pcpu,comm`: one process per line, the first line a header. Split each line into at most three fields and skip any line that does not yield an integer pid, a float cpu and a non-empty command — that rule disposes of the header, blank lines and anything malformed without a special case for each. A process is busy when its cpu is **strictly greater** than `cpu_floor` and its command starts with none of `ignore_prefixes`; return the busy ones in the order they appeared in the snapshot.

```python
def busy_processes(
    ps_stdout: str, *, cpu_floor: float, ignore_prefixes: Sequence[str]
) -> list[Process]:
    busy: list[Process] = []
    for line in ps_stdout.splitlines():
        fields = line.strip().split(maxsplit=2)
        if len(fields) != 3:
            continue
        try:
            pid, cpu = int(fields[0]), float(fields[1])
        except ValueError:
            continue
        comm = fields[2]
        if cpu > cpu_floor and not comm.startswith(tuple(ignore_prefixes)):
            busy.append(Process(pid=pid, comm=comm, cpu=cpu))
    return busy
```

- [ ] **Step 5: The decode rate**

Add `decode_rate`. oMLX writes one server-log line per completion when it ends, of the shape `2026-09-17 21:14:02,004 - omlx.server - INFO - [-] - Chat completion: model=Ornith-1.5-9B-MLX-8bit, 900 tokens in 10.00s (90.0 tok/s), prompt: 5000, finish_reason=stop, max_tokens=16000, request_max_tokens=16000`. A line is a completion only when it carries both the timestamped `omlx.server - INFO` prefix and that whole `Chat completion: model=..., N tokens in Xs (R tok/s), prompt: P,` shape — a blank line, another logger's line, or a bare `Chat completion:` fragment without the stamp is not one. Keep the completions whose model is exactly `model`, in order. Return `None` when there are fewer than `last` of them; otherwise take the **last** `last` and return a `Rate` whose `tokens` and `seconds` are the sums over them and whose `tok_s` is `sum(tokens) / sum(seconds)`. The rate is token-weighted and never the mean of the per-completion rates: a 32-token completion must not weigh the same as an 8,000-token one, because the question is how fast tokens came out, not how fast the average request was.

```python
_COMPLETION = re.compile(
    r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} - omlx\.server - INFO\b.*?"
    r"Chat completion: model=(?P<model>[^,]+), (?P<tokens>\d+) tokens in "
    r"(?P<seconds>[\d.]+)s \((?P<rate>[\d.]+) tok/s\), prompt: (?P<prompt>\d+),"
)


def decode_rate(log_lines: Iterable[str], *, model: str, last: int) -> Rate | None:
    seen: list[tuple[int, float]] = []
    for line in log_lines:
        match = _COMPLETION.search(line)
        if match is not None and match.group("model") == model:
            seen.append((int(match.group("tokens")), float(match.group("seconds"))))
    if len(seen) < last:
        return None
    window = seen[-last:]
    tokens = sum(count for count, _ in window)
    seconds = sum(span for _, span in window)
    return Rate(tok_s=tokens / seconds, completions=len(window), tokens=tokens, seconds=seconds)
```

- [ ] **Step 6: The certificate**

Add `Certificate` and `certificate`. `Certificate` is frozen, with `problems` (a tuple of strings, empty when the machine is quiet) and `record` (a dict of the inputs); `as_dict()` returns `{"problems": [...], "inputs": {...}}`, where `inputs` has exactly the keys `load` (the load message or null), `busy` (a list of `{"pid", "comm", "cpu"}` objects in snapshot order), `decode` (null, or exactly `{"tok_s", "completions", "tokens", "seconds"}`), `floor_tok_s`, `model` and `last`, and the whole thing round-trips through `json.dumps`. The problems come in one order: the load message when there is one, then one `busy:` line per busy process with its cpu to one decimal place, then the decode problem. There are two decode problems and they are exclusive: when `rate` is `None` the message says fewer than `last` completions were found for `model`; otherwise, when the rate is **strictly less** than `floor_tok_s`, the message names the rate, the floor and the number of completions, the two rates to one decimal place. A rate exactly at the floor is quiet.

```python
@dataclass(frozen=True, slots=True)
class Certificate:
    problems: tuple[str, ...]
    record: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        return {"problems": list(self.problems), "inputs": self.record}


def certificate(
    load: str | None,
    busy: Sequence[Process],
    rate: Rate | None,
    *,
    floor_tok_s: float,
    model: str,
    last: int,
) -> Certificate:
    problems: list[str] = []
    if load is not None:
        problems.append(load)
    for process in busy:
        problems.append(f"busy: {process.comm} pid {process.pid} at {process.cpu:.1f}% cpu")
    if rate is None:
        problems.append(f"decode: fewer than {last} completions for {model}")
    elif rate.tok_s < floor_tok_s:
        problems.append(
            f"decode {rate.tok_s:.1f} tok/s < {floor_tok_s:.1f} "
            f"over last {rate.completions} completions"
        )
    record: dict[str, object] = {
        "load": load,
        "busy": [{"pid": p.pid, "comm": p.comm, "cpu": p.cpu} for p in busy],
        "decode": None
        if rate is None
        else {
            "tok_s": rate.tok_s,
            "completions": rate.completions,
            "tokens": rate.tokens,
            "seconds": rate.seconds,
        },
        "floor_tok_s": floor_tok_s,
        "model": model,
        "last": last,
    }
    return Certificate(problems=tuple(problems), record=record)
```

- [ ] **Step 7: The CLI**

Add `main` and the two real readers. `main(argv=None, *, loadavg, cores, read_ps, read_log)` parses `--model ID` (required), `--ceiling F`, `--cpu-floor F`, `--floor-tok-s F` and `--last N`, whose defaults are the four module constants. It takes its four readings from the keyword-only callables — whose defaults are `os.getloadavg`, the core count, a `ps -axo pid,pcpu,comm` subprocess and a reader of the server log — so the acceptance suite can drive both directions on one machine without spawning anything. It calls the three pure functions, passes `IGNORE_PREFIXES` as the ignore list, prints `certificate(...).as_dict()` as JSON on stdout, and returns 0 when `problems` is empty and 1 when it is not.

```python
def _read_ps() -> str:
    return subprocess.run(
        ["ps", "-axo", "pid,pcpu,comm"], capture_output=True, text=True, check=True
    ).stdout


def _read_log() -> list[str]:
    try:
        with open(SERVER_LOG, encoding="utf-8", errors="replace") as handle:
            return handle.readlines()
    except OSError:
        return []


def main(
    argv: Sequence[str] | None = None,
    *,
    loadavg: Callable[[], tuple[float, float, float]] = os.getloadavg,
    cores: Callable[[], int] = lambda: os.cpu_count() or 1,
    read_ps: Callable[[], str] = _read_ps,
    read_log: Callable[[], Iterable[str]] = _read_log,
) -> int:
    parser = argparse.ArgumentParser(prog="preflight_quiet.py")
    parser.add_argument("--model", required=True)
    parser.add_argument("--ceiling", type=float, default=DEFAULT_CEILING)
    parser.add_argument("--cpu-floor", type=float, default=DEFAULT_CPU_FLOOR)
    parser.add_argument("--floor-tok-s", type=float, default=DEFAULT_FLOOR_TOK_S)
    parser.add_argument("--last", type=int, default=DEFAULT_LAST)
    args = parser.parse_args(argv)
    result = certificate(
        load_problem(loadavg(), cores(), ceiling=args.ceiling),
        busy_processes(read_ps(), cpu_floor=args.cpu_floor, ignore_prefixes=IGNORE_PREFIXES),
        decode_rate(read_log(), model=args.model, last=args.last),
        floor_tok_s=args.floor_tok_s,
        model=args.model,
        last=args.last,
    )
    print(json.dumps(result.as_dict(), sort_keys=True))
    return 1 if result.problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 8: Run the acceptance suite and watch it pass**

Run the suite again with `scripts` on the path and expect all twenty to pass, with no test edited to suit the implementation. Then run the repository's own checks — the whole default tier and the linter — and expect them green too.

```bash
PYTHONPATH=scripts uv run pytest tests/test_preflight_quiet.py -q
just gates
```

- [ ] **Step 9: Record the provenance and commit**

Add a row for each new file to `PROVENANCE.md` with `uv run python tools/provenance.py new`, then commit the two new files and that row together, with explicit paths.
````

- [ ] **Step 3: Check the document against the four mechanical facts**

```bash
cd "$EVALS"
DOC=docs/superpowers/plans/2026-09-18-preflight-quiet.md
grep -c '^### ' "$DOC"                       # expect 1
awk '/^### Task 1: The machine-quiet preflight$/{f=1;next} f&&/^---$/{print "RULE IN SECTION";exit}' "$DOC"
grep -n 'its test module' "$DOC"             # expect no match: the retired stand-in
grep -n '^- Create:\|^- Modify:\|^- Test:' "$DOC"
```

Expect: exactly one `### ` heading, no `RULE IN SECTION` line, no stand-in, and three Files lines naming only `scripts/preflight_quiet.py` and `tests/test_preflight_quiet.py`.

- [ ] **Step 4: Preview the prompt the cut will produce**

The cut spec does not exist yet, so drive the generator's two pure functions directly. This is the text a cell will receive, minus the `formats` paragraph Task 3 appends.

```bash
cd "$EVALS"
uv run python - <<'PY'
from pathlib import Path
import sys
sys.path.insert(0, "tools")
from cut_task import plan_section, r1_plan_prompt
doc = Path("docs/superpowers/plans/2026-09-18-preflight-quiet.md").read_text(encoding="utf-8")
section = plan_section(doc, "### Task 1: The machine-quiet preflight")
prompt = r1_plan_prompt(section, ["tests/test_preflight_quiet.py"], "")
print(prompt)
print("---- chars:", len(prompt))
for bad in ("def ", "assert ", "import ", "```"):
    assert bad not in prompt, f"stripped code leaked into the prompt: {bad!r}"
assert "test_preflight_quiet.py" not in prompt
assert "tests/" in prompt
PY
```

Expect the printed prompt to contain the title, the Files lines with `tests/` in place of the hidden path, the `Produces:` signatures, and the nine steps' prose — and no code, no assertion, and no hidden filename. **Read the printed prompt as a stranger would** and confirm every structural fact the suite asserts is either in that text or destined for `formats`: the module path, the six public names, the three dataclasses' fields, the direction of each of the three thresholds, the ignore-prefix rule, the ordering of the problems list, the token weighting, the `as_dict()` shape, and the two exit codes. A fact that is in neither is a Task 3 `formats` line — write it down now.

- [ ] **Step 5: Provenance, gates and commit**

```bash
cd "$EVALS"
uv run python tools/provenance.py new docs/superpowers/plans/2026-09-18-preflight-quiet.md
just gates; echo "gates=$?"
git add docs/superpowers/plans/2026-09-18-preflight-quiet.md PROVENANCE.md
git commit -m "Authored census task: the machine-quiet preflight plan heading, with its acceptance suite"
git rev-parse HEAD
```

Expected: `gates=0` (the doc caps do not bind plans), and a printed sha. **On a first cut, that sha is both `base` and `plan.commit` for Task 3** (Ruling 1) — write it into the ledger. This commit adds nothing but the document and its provenance row: no `ROADMAP.md` sentence, no `STATE.md` line, nothing naming the task's API anywhere a base tree would carry it. **On a re-cut, `base` and `plan.commit` are deliberately unequal**: every commit that carries the revised heading also carries the task's own previously-committed cut tree, and taking that later commit as `base` would put the answer in the cell's `base/`; `plan.commit` stays this heading commit while `base` moves to the re-cut's own later commit. At head, `plan.commit` is `3cd88a6ce1e6987293dfa638337d8594535bffd3` and `base` is `3f7a561931e4c4fabb79991756359d6d6c9c9aac`.

---

### Task 2: Sonnet implements the heading in a fresh worktree and commits `good`

Spec section 3, role 2. **The implementer must not be the agent that wrote Task 1.** It works from `docs/superpowers/plans/2026-09-18-preflight-quiet.md` under the ordinary loop — Opus reviews, gates green — and the hidden suite is the developer's: it is not edited to fit the implementation (Ruling 13).

**Files:**
- Create, in the worktree only: `scripts/preflight_quiet.py`, `tests/test_preflight_quiet.py`
- Modify, in the worktree only: `PROVENANCE.md`
- Read only, in the main checkout: `docs/superpowers/plans/2026-09-18-preflight-quiet.md`

**Interfaces:**
- Consumes: Task 1's `base` sha and the heading document.
- Produces: `good` — one commit on `worktree-authored-preflight-quiet` whose parent is `base`, holding `scripts/preflight_quiet.py`, `tests/test_preflight_quiet.py` and a `PROVENANCE.md` row for each; and the sha256 of the hidden suite, recorded before implementation and unchanged at commit time. Task 3's cut spec consumes `base`, `good`, and those two paths.

- [ ] **Step 1: Create the worktree off `base`**

The seven worktrees already under `.claude/worktrees/` are historical evidence — do not enter or disturb them. Create one more, branch it off Task 1's commit, and sync it.

```bash
cd "$EVALS"
BASE=$(git rev-parse HEAD)    # Task 1's commit; confirm it against the ledger
echo "BASE=$BASE"
git worktree add -b worktree-authored-preflight-quiet \
  "$EVALS/.claude/worktrees/authored-preflight-quiet" "$BASE"
WT="$EVALS/.claude/worktrees/authored-preflight-quiet"
( cd "$WT" && uv sync && git log --oneline -1 )
```

Expected: the worktree at `$WT` on branch `worktree-authored-preflight-quiet`, its head equal to `BASE`, and `git status --porcelain` in the **main** checkout still printing nothing (a linked worktree inside `.claude/` is not tracked content).

- [ ] **Step 2: Write the acceptance suite, byte-for-byte from the heading**

Extract the heading's first fenced Python block — the hidden suite — into the worktree rather than retyping it, so "written from the spec before the implementation" is a fact and not a claim.

```bash
cd "$EVALS"
uv run python - "$WT" <<'PY'
import re, sys
from pathlib import Path
doc = Path("docs/superpowers/plans/2026-09-18-preflight-quiet.md").read_text(encoding="utf-8")
body = doc[doc.index("### Task 1: The machine-quiet preflight"):]
block = re.search(r"```python\n(.*?)\n```", body, re.S)
assert block is not None, "the heading has no fenced python block"
out = Path(sys.argv[1]) / "tests" / "test_preflight_quiet.py"
out.write_text(block.group(1) + "\n", encoding="utf-8")
print(out)
PY
shasum -a 256 "$WT/tests/test_preflight_quiet.py" | tee "$SCRATCH/hidden-suite.sha256"
```

Expected: the file written and one sha printed. **Record that sha in the ledger now**, before `scripts/preflight_quiet.py` exists — it is the evidence that the suite predates the implementation. Confirm the module is still absent: `ls "$WT/scripts/preflight_quiet.py"` must fail.

- [ ] **Step 3: Run the suite and see it fail for the right reason**

```bash
( cd "$WT" && PYTHONPATH=scripts uv run pytest tests/test_preflight_quiet.py -q ); echo "red=$?"
```

Expected: non-zero, with `ModuleNotFoundError: No module named 'preflight_quiet'` — a collection error, because nothing is implemented. Any other failure means the extracted file is not the suite; stop.

- [ ] **Step 4: Implement the module, following the heading's steps 3 to 7**

In the worktree, create `scripts/preflight_quiet.py` following `### Task 1`'s Step 3 (the dataclasses, the constants, `load_problem`), Step 4 (`busy_processes`), Step 5 (`decode_rate`), Step 6 (`Certificate` and `certificate`) and Step 7 (`main` and the two real readers). The heading's fenced blocks are the implementation; follow them. Nothing else is created: no second module, no package, no `__init__.py`, no change to any existing file but `PROVENANCE.md`.

After each of the five pieces, run the slice of the suite it should turn green — the loop is red, implement, green, not a single write at the end:

```bash
( cd "$WT" && PYTHONPATH=scripts uv run pytest tests/test_preflight_quiet.py -q -k load )
( cd "$WT" && PYTHONPATH=scripts uv run pytest tests/test_preflight_quiet.py -q -k busy )
( cd "$WT" && PYTHONPATH=scripts uv run pytest tests/test_preflight_quiet.py -q -k decode_rate )
( cd "$WT" && PYTHONPATH=scripts uv run pytest tests/test_preflight_quiet.py -q -k certificate )
( cd "$WT" && PYTHONPATH=scripts uv run pytest tests/test_preflight_quiet.py -q -k cli )
```

**If a test stays red, fix the module.** The suite is not touched: a failing assertion is a statement about the implementation, or — in the one case where the spec itself is wrong — a stop for the maintainer (spec section 3: "an implementation that cannot pass them is fixed, or the spec is, before `good` exists"). An agent never edits the suite to agree with its own code.

- [ ] **Step 5: The whole suite, then the whole default tier**

```bash
( cd "$WT" && PYTHONPATH=scripts uv run pytest tests/test_preflight_quiet.py -q ); echo "suite=$?"
( cd "$WT" && PYTHONPATH=scripts uv run pytest tests/test_preflight_quiet.py -q --collect-only | tail -2 )
( cd "$WT" && uv run pytest -q ); echo "tier=$?"
( cd "$WT" && uv run ruff check ); echo "ruff=$?"
```

Expected: `suite=0` with **20 passed**, a collected count of 20, `tier=0`, `ruff=0`. The default tier is run without `PYTHONPATH` too, to confirm the new module does not break collection elsewhere; the new suite is skipped or errors there only if `scripts` is not importable — if it errors, add nothing to `conftest.py` and stop, because the oracle runs the suite with `PYTHONPATH=scripts` (Task 3's `oracle_env`) and a repository-side fix would be a change the cut does not carry.

- [ ] **Step 6: Prove the suite was not edited**

```bash
shasum -a 256 "$WT/tests/test_preflight_quiet.py"
cat "$SCRATCH/hidden-suite.sha256"
uv run python - "$WT" <<'PY'
import re, sys
from pathlib import Path
doc = Path("docs/superpowers/plans/2026-09-18-preflight-quiet.md").read_text(encoding="utf-8")
body = doc[doc.index("### Task 1: The machine-quiet preflight"):]
want = re.search(r"```python\n(.*?)\n```", body, re.S).group(1) + "\n"
got = (Path(sys.argv[1]) / "tests" / "test_preflight_quiet.py").read_text(encoding="utf-8")
print("identical to the heading:", want == got)
raise SystemExit(0 if want == got else 1)
PY
echo "unedited=$?"
```

Expected: the two shas equal and `unedited=0`. **A difference stops the plan** and is reported with the diff: either the suite was edited to fit the implementation, which voids the task's premise, or the heading was edited after the fact, which voids the prompt's provenance.

- [ ] **Step 7: Provenance, gates and the `good` commit**

```bash
( cd "$WT" && uv run python tools/provenance.py new scripts/preflight_quiet.py tests/test_preflight_quiet.py )
( cd "$WT" && just gates ); echo "gates=$?"
( cd "$WT" && git add scripts/preflight_quiet.py tests/test_preflight_quiet.py PROVENANCE.md \
  && git commit -m "The machine-quiet preflight: scripts/preflight_quiet.py and its acceptance suite" )
GOOD=$(git -C "$WT" rev-parse HEAD)
echo "GOOD=$GOOD"
git -C "$WT" show --stat --name-only --oneline HEAD
git -C "$WT" rev-parse HEAD^
```

Expected: `gates=0`; `GOOD` printed; the commit touching exactly `scripts/preflight_quiet.py`, `tests/test_preflight_quiet.py` and `PROVENANCE.md` (Ruling 12); and `HEAD^` equal to `BASE`. Record `BASE` and `GOOD` in the ledger — Task 3's spec file is the only place they are typed again, and they are copied, never remembered.

- [ ] **Step 8: Remove the worktree and keep the branch**

```bash
cd "$EVALS"
git worktree remove "$EVALS/.claude/worktrees/authored-preflight-quiet"
git worktree list
git branch --list 'worktree-authored-preflight-quiet'
git rev-parse "$GOOD^{commit}" "$BASE^{commit}"
git status --porcelain; echo "dirty=$?"
git log --oneline -1
```

Expected: the seven historical worktrees still listed and the new one gone; the branch still present; both shas resolving; `git status --porcelain` printing nothing; and the main checkout's head still Task 1's commit — **this task commits nothing to `release-one`**. The branch is never merged, never pushed, never deleted: `cut_task.py` and the manifest's `provenance` block need both commits reachable forever.

---

### Task 3: The cut spec, the authored disclosure, the cut, and qualification

Spec section 3, role 3, and section 5's disclosure. Everything here lands on `release-one` in one commit.

**Files:**
- Create: `tools/task_specs/selfhost-preflight-quiet.json`, `src/satyrn_evals/tasks/selfhost-preflight-quiet/` (the cut tree)
- Modify: `tools/cut_task.py` (the optional `authored` key), `src/satyrn_evals/qualify.py` (`judge_authored`, `CENSUS_TASKS`), `tests/test_cut_task.py`, `tests/test_qualify.py`, `tests/test_census_records_frozen.py`, `PROVENANCE.md`

**Interfaces:**
- Consumes: Task 1's `base` and plan commit; Task 2's `good`.
- Produces: `qualify.CENSUS_TASKS["selfhost-preflight-quiet"] == PLAN_RUNG`; a committed task tree whose `tree_digest` Task 7's record pins; `manifest["generator"]["authored"] is True` with `generator.authoring.spec` and `generator.authoring.roles`; `manifest["expected_test_ids"]`, which Task 5 counts.

- [ ] **Step 1: Write the cut spec**

Create `tools/task_specs/selfhost-preflight-quiet.json`. `<BASE>` and `<GOOD>` are the two 40-hex shas from Tasks 1 and 2. On a first cut, `plan.commit` equals `<BASE>`, because the heading document is committed by exactly that commit; on a re-cut, `plan.commit` stays Task 1's original heading commit while `<BASE>` moves to the re-cut's own later commit (Ruling 1), so the two are deliberately unequal there. At head, `plan.commit` is `3cd88a6ce1e6987293dfa638337d8594535bffd3` and `base` is `3f7a561931e4c4fabb79991756359d6d6c9c9aac`. `formats` is Ruling 3's string, reproduced here in full: it carries the spec's four messages and every other literal the suite matches, because `r1_plan_prompt` strips the code that would otherwise state them.

```json
{
  "name": "selfhost-preflight-quiet",
  "base": "<BASE>",
  "good": "<GOOD>",
  "files": [
    "scripts/preflight_quiet.py"
  ],
  "hidden": [
    "tests/test_preflight_quiet.py"
  ],
  "plan": {
    "path": "docs/superpowers/plans/2026-09-18-preflight-quiet.md",
    "heading": "### Task 1: The machine-quiet preflight",
    "commit": "<BASE>"
  },
  "formats": "Every name, key, default and message below is matched literally by the acceptance suite, so match it exactly. The module is scripts/preflight_quiet.py and the suite imports load_problem, busy_processes, decode_rate, certificate, main, Process, Rate and IGNORE_PREFIXES from preflight_quiet with scripts on the path. Process is a frozen dataclass with fields pid (int), comm (str) and cpu (float); Rate is frozen with tok_s (float), completions (int), tokens (int) and seconds (float); Certificate is frozen with problems (a tuple of strings, empty when the machine is quiet) and record (a dict), and its as_dict() returns {\"problems\": [...], \"inputs\": {...}} where inputs has exactly the keys load (the load message or null), busy (a list of {\"pid\", \"comm\", \"cpu\"} objects in snapshot order), decode (null, or exactly {\"tok_s\", \"completions\", \"tokens\", \"seconds\"}), floor_tok_s, model and last. load_problem((one, five, fifteen), cores, ceiling=C) returns None when one <= C * cores and otherwise the message `load <one> > <C * cores> (<cores> cores)` with both numbers to one decimal place and the core count as a bare integer, for example `load 9.5 > 4.0 (8 cores)`. busy_processes parses `ps -axo pid,pcpu,comm` output: each line is split into at most three fields and skipped unless they are an integer pid, a float cpu and a command, which disposes of the header and of malformed lines; a process is busy when its cpu is strictly greater than cpu_floor and its command starts with none of ignore_prefixes; the busy processes come back in the order they appear. decode_rate parses oMLX server-log lines of the shape `2026-09-17 21:14:02,004 - omlx.server - INFO - [-] - Chat completion: model=M, 900 tokens in 10.00s (90.0 tok/s), prompt: 5000, finish_reason=stop, max_tokens=16000, request_max_tokens=16000`; a line without that timestamped omlx.server - INFO prefix or without that whole completion shape is not a completion. It keeps the completions whose model is exactly model, returns None when there are fewer than last of them, and otherwise returns a Rate over the last `last` of them whose tokens and seconds are the sums and whose tok_s is sum(tokens) / sum(seconds) -- token-weighted, never the mean of the per-completion rates. certificate(load, busy, rate, *, floor_tok_s, model, last) returns the problems in this order: the load message when it is not None; then one `busy: <comm> pid <pid> at <cpu>% cpu` per busy process, the cpu to one decimal place; then, when rate is None, `decode: fewer than <last> completions for <model>`, and otherwise, only when rate.tok_s is strictly less than floor_tok_s, `decode <rate.tok_s> tok/s < <floor_tok_s> over last <rate.completions> completions` with both numbers to one decimal place. A rate exactly at the floor is quiet, a load exactly at the ceiling is quiet, and a process exactly at the cpu floor is quiet. main(argv=None, *, loadavg, cores, read_ps, read_log) parses --model ID (required), --ceiling F (default 0.5), --cpu-floor F (default 20.0), --floor-tok-s F (default 30.0) and --last N (default 20); it takes the load average, the core count, the ps snapshot and the log lines from those four keyword-only callables, whose defaults read the real machine, so the suite drives it without a subprocess; it passes IGNORE_PREFIXES, the tuple (\"/sbin/\", \"/usr/sbin/\", \"/usr/libexec/\", \"/System/\", \"/usr/local/bin/omlx-\"), as the ignore list; it prints as_dict() as JSON on stdout; and it returns 0 when problems is empty and 1 when it is not.",
  "broken": {
    "scripts/preflight_quiet.py": "\"\"\"known-broken fixture stub: importable, behaviorally incomplete.\"\"\"\n\nfrom dataclasses import dataclass\n\nDEFAULT_CEILING = 0.0\nDEFAULT_CPU_FLOOR = 0.0\nDEFAULT_FLOOR_TOK_S = 0.0\nDEFAULT_LAST = 0\nIGNORE_PREFIXES: tuple[str, ...] = ()\n\n\n@dataclass(frozen=True, slots=True)\nclass Process:\n    pid: int = 0\n    comm: str = \"\"\n    cpu: float = 0.0\n\n\n@dataclass(frozen=True, slots=True)\nclass Rate:\n    tok_s: float = 0.0\n    completions: int = 0\n    tokens: int = 0\n    seconds: float = 0.0\n\n\n@dataclass(frozen=True, slots=True)\nclass Certificate:\n    problems: tuple[str, ...] = ()\n    record: dict = None\n\n    def as_dict(self):\n        return {}\n\n\ndef load_problem(loadavg, cores, *, ceiling):\n    return None\n\n\ndef busy_processes(ps_stdout, *, cpu_floor, ignore_prefixes):\n    return []\n\n\ndef decode_rate(log_lines, *, model, last):\n    return None\n\n\ndef certificate(load, busy, rate, *, floor_tok_s, model, last):\n    return Certificate()\n\n\ndef main(argv=None, **kwargs):\n    return 0\n"
  },
  "oracle_env": {
    "PYTHONPATH": "scripts"
  },
  "authored": {
    "spec": "docs/superpowers/specs/2026-09-17-release-two-authored-task-design.md",
    "roles": {
      "heading": "Opus, from the design spec, before any implementation existed",
      "implementation": "Sonnet, in a worktree under the ordinary loop, without editing the acceptance suite",
      "validity": "recorded in the manifest's validity block"
    }
  }
}
```

Note what is **not** there: no `prompt_edits` key. It is optional, and no edit is justified before the validity check has failed (Ruling 9).

- [ ] **Step 2: Teach `cut_task.py` the optional `authored` key — failing test first**

Add to `tests/test_cut_task.py`, run it (expect FAIL on the unknown key), then make it pass:

```python
def test_a_spec_may_carry_an_authored_disclosure(tmp_path: Path) -> None:
    """Design section 5: an authored task discloses itself in the manifest's
    generator block, inside the body `check` compares — not as a post-cut
    annotation anyone may edit."""
    body = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    body["authored"] = {"spec": "docs/superpowers/specs/x.md", "roles": {"heading": "Opus"}}
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(body), encoding="utf-8")
    spec = cut_task.load_spec(path)
    assert spec.authored == cut_task.Authored(
        spec="docs/superpowers/specs/x.md", roles={"heading": "Opus"}
    )
    generator = cut_task.manifest_body(spec, "prompt", ["a::b"], "digest")["generator"]
    assert generator["authored"] is True
    assert generator["authoring"] == {
        "spec": "docs/superpowers/specs/x.md", "roles": {"heading": "Opus"}
    }


def test_a_cut_spec_without_the_key_carries_no_disclosure(tmp_path: Path) -> None:
    """The sibling: the six cut tasks must re-cut byte-identically, so the key is
    optional and absent means absent — never `authored: false`."""
    spec = cut_task.load_spec(SPEC_PATH)
    assert spec.authored is None
    generator = cut_task.manifest_body(spec, "prompt", ["a::b"], "digest")["generator"]
    assert "authored" not in generator
    assert "authoring" not in generator


@pytest.mark.parametrize(
    "value",
    [
        {"spec": "", "roles": {"heading": "Opus"}},
        {"spec": "docs/x.md", "roles": {}},
        {"spec": "docs/x.md", "roles": {"heading": ""}},
        {"spec": "docs/x.md"},
        {"spec": "docs/x.md", "roles": {"heading": "Opus"}, "extra": "no"},
        "yes",
    ],
)
def test_a_malformed_authored_block_is_refused(tmp_path: Path, value: object) -> None:
    body = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    body["authored"] = value
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(body), encoding="utf-8")
    with pytest.raises(cut_task.CutError):
        cut_task.load_spec(path)
```

`SPEC_PATH` is the module's existing pointer at a committed spec file; if the test module has none, add `SPEC_PATH = ROOT / "tools" / "task_specs" / "selfhost-run-record-gate.json"` beside the other constants. Then the implementation in `tools/cut_task.py`:

```python
_OPTIONAL_SPEC_KEYS = frozenset({"prompt_edits", "authored"})
_AUTHORED_KEYS = frozenset({"spec", "roles"})


@dataclass(frozen=True, slots=True)
class Authored:
    """The disclosure an authored task carries (design section 5).

    A task written for the census rather than cut from a historical plan is
    never pooled with the cut ones, so the manifest says so where
    ``cut_task.py check`` can see it.
    """

    spec: str
    roles: dict[str, str]
```

In `load_spec`, after the `prompt_edits` block:

```python
    raw_authored = body.get("authored")
    authored: Authored | None = None
    if raw_authored is not None:
        if not isinstance(raw_authored, dict) or set(raw_authored) != _AUTHORED_KEYS:
            raise CutError(f"spec {path}: authored must be {{spec, roles}}")
        if not isinstance(raw_authored["spec"], str) or not raw_authored["spec"]:
            raise CutError(f"spec {path}: authored.spec must be a non-empty path string")
        roles = raw_authored["roles"]
        if not isinstance(roles, dict) or not roles or not all(
            isinstance(k, str) and k and isinstance(v, str) and v for k, v in roles.items()
        ):
            raise CutError(f"spec {path}: authored.roles must map non-empty strings to non-empty strings")
        authored = Authored(spec=raw_authored["spec"], roles=dict(roles))
```

`TaskSpec` gains `authored: Authored | None = None` after `prompt_edits`, `load_spec`'s `TaskSpec(...)` call passes `authored=authored`, and `manifest_body` gains, after its `prompt_edits` block:

```python
    if spec.authored is not None:
        generator["authored"] = True
        generator["authoring"] = {"spec": spec.authored.spec, "roles": dict(spec.authored.roles)}
```

Run `uv run pytest tests/test_cut_task.py -q` and expect PASS.

- [ ] **Step 3: Prove the six committed tasks did not move**

```bash
cd "$EVALS"
uv run python tools/cut_task.py check tools/task_specs/selfhost-run-record-gate.json \
  tools/task_specs/selfhost-docs-linter.json tools/task_specs/selfhost-cell-loop.json \
  tools/task_specs/selfhost-speed-probe.json tools/task_specs/selfhost-guard-prefixes.json \
  tools/task_specs/selfhost-review-script.json; echo "others=$?"
uv run pytest tests/test_census_records_frozen.py -q; echo "frozen=$?"
```

Expected: `others=0`, six "matches a fresh cut" lines, and `frozen=0`. A non-zero `others` means the optional key moved a tree that must not move — **stop**; the key is meant to be invisible to a spec that does not carry it.

- [ ] **Step 4: Cut, check, and qualify**

```bash
cd "$EVALS"
uv run python tools/cut_task.py cut tools/task_specs/selfhost-preflight-quiet.json; echo "cut=$?"
uv run python tools/cut_task.py check tools/task_specs/selfhost-preflight-quiet.json; echo "check=$?"
uv run satyrn-evals qualify selfhost-preflight-quiet; echo "qualify=$?"
```

Expected: `cut=0` printing the task directory, `check=0` printing "matches a fresh cut", `qualify=0` with every check `ok` — the known-good patch three times, known-broken failing, the R1-plan prompt's paths resolving, the prompt-edit check (vacuous, none recorded), the authored disclosure, and the live harvest writing `PROVENANCE.md` and having it dropped. A failure here is a generator defect: fix the spec, remove the cut tree deliberately, and re-cut. Two failures of the same check is a stop.

- [ ] **Step 5: The three leak tells for an authored task (Ruling 5)**

```bash
cd "$EVALS"
T=src/satyrn_evals/tasks/selfhost-preflight-quiet
find "$T/base/docs" -type f 2>/dev/null | head            # expect: nothing under docs/superpowers
ls "$T/base/docs/superpowers" 2>&1 | head -1              # expect: No such file or directory
ls "$T/base/src/satyrn_evals/tasks/" | sort               # expect: the five night-1 tasks, not this one
ls "$T/base/tests/test_preflight_quiet.py" 2>&1 | head -1 # expect: No such file or directory
grep -rl 'preflight_quiet\|load_problem\|busy_processes\|decode_rate\|IGNORE_PREFIXES' "$T/base" | head
echo "base-tells=$?"
ls "$T/overlay/"                                          # expect: test_preflight_quiet.py only
```

Expected: no file under `base/docs/superpowers/`; `selfhost-preflight-quiet` absent from `base/src/satyrn_evals/tasks/`; the hidden module absent from `base/tests/`; and the `grep -rl` printing **nothing** — the answer, the API names and the plan document are all outside the tree a cell or a solver receives. Any hit is a leak and **stops the plan**.

- [ ] **Step 6: Add the disclosure check to `qualify` — failing test first**

In `tests/test_qualify.py`:

```python
def test_an_authored_manifest_discloses_its_spec_and_roles() -> None:
    body = {"generator": {"authored": True, "authoring": {
        "spec": "docs/superpowers/specs/x.md", "roles": {"heading": "Opus"}}}}
    check = qualify_module.judge_authored(body)
    assert check.passed
    assert check.name == "authored-disclosure"


def test_a_cut_manifest_without_the_disclosure_passes_untouched() -> None:
    """The sibling: six cut tasks carry no disclosure and must not be failed by it."""
    check = qualify_module.judge_authored({"generator": {"tool": "tools/cut_task.py"}})
    assert check.passed
    assert check.detail == "not an authored task"


@pytest.mark.parametrize(
    "generator",
    [
        {"authored": False, "authoring": {"spec": "x", "roles": {"a": "b"}}},
        {"authored": True},
        {"authored": True, "authoring": {"spec": "", "roles": {"a": "b"}}},
        {"authored": True, "authoring": {"spec": "x", "roles": {}}},
        {"authored": True, "authoring": {"spec": "x", "roles": {"a": ""}}},
        {"authored": True, "authoring": "Opus"},
    ],
)
def test_a_malformed_disclosure_is_refused(generator: dict) -> None:
    assert not qualify_module.judge_authored({"generator": generator}).passed


def test_the_census_set_carries_the_authored_task() -> None:
    """Design section 2: the authored task joins night 1's five as the third
    medium-build member of the census set."""
    assert CENSUS_TASKS["selfhost-preflight-quiet"] == PLAN_RUNG
    assert len(CENSUS_TASKS) == 6
```

Then in `src/satyrn_evals/qualify.py`, beside `judge_prompt_edits`:

```python
def judge_authored(manifest_body: dict) -> Check:
    """An authored task discloses its spec and its roles (design section 5).

    Pure. A task cut from a historical plan carries no ``authored`` key and
    passes untouched; a task that claims to be authored must say under which
    spec and by which roles, because it is reported beside the cut tasks and
    never pooled with them.
    """
    generator = manifest_body.get("generator") or {}
    if "authored" not in generator:
        return Check("authored-disclosure", True, "not an authored task")
    if generator["authored"] is not True:
        return Check("authored-disclosure", False, f"authored is {generator['authored']!r}, want True")
    authoring = generator.get("authoring")
    if not isinstance(authoring, dict) or set(authoring) != {"spec", "roles"}:
        return Check("authored-disclosure", False, "authoring must be {spec, roles}")
    spec, roles = authoring["spec"], authoring["roles"]
    if not isinstance(spec, str) or not spec:
        return Check("authored-disclosure", False, "authoring.spec must be a non-empty path string")
    if not isinstance(roles, dict) or not roles or not all(
        isinstance(key, str) and key and isinstance(value, str) and value for key, value in roles.items()
    ):
        return Check("authored-disclosure", False, "authoring.roles must map non-empty strings to non-empty strings")
    return Check("authored-disclosure", True, f"authored under {spec}, {len(roles)} roles")
```

and register it in `qualify` beside the prompt-edits check:

```python
        checks.append(judge_prompt_edits(manifest_body))
        checks.append(judge_authored(manifest_body))
```

Extend `CENSUS_TASKS`, leaving `CEILING_CANDIDATES`, `FLOOR_CANDIDATES` and `HELDOUT_TASKS` alone:

```python
CENSUS_TASKS: dict[str, str] = {
    "agentclinic-repair-depth-3": "R2",
    "selfhost-run-record-gate": PLAN_RUNG,
    "selfhost-docs-linter": PLAN_RUNG,
    "selfhost-cell-loop": PLAN_RUNG,
    "selfhost-speed-probe": PLAN_RUNG,
    "selfhost-preflight-quiet": PLAN_RUNG,
}
```

- [ ] **Step 7: Repair the night-2 guard's census-set assertion**

`tests/test_census_records_frozen.py` currently asserts `set(CENSUS_TASKS) == NIGHT1_TASKS` — written when night 2's candidate was withdrawn, to stop a later cut silently widening that night's record set. The cut has now happened deliberately, so the assertion becomes the narrower true one: night 2's **records** are still the three replacements, and the census set is night 1's five plus this one task. Replace that test body with:

```python
AUTHORED = {"selfhost-preflight-quiet"}


def test_night_two_is_the_three_replacements_and_the_census_set_gains_only_the_authored_task() -> None:
    """Amendment 2026-09-17 (night-2 design section 4): record 1, the third
    candidate, was withdrawn and Task 2 deferred to a separate spec. Night 2 is
    the three replacement records only. The authored task
    (2026-09-17-release-two-authored-task-design.md) is that deferred third
    build task; it joins CENSUS_TASKS and gets its own night-3 record, and it
    must not widen night 2's record set."""
    assert set(CENSUS_TASKS) == NIGHT1_TASKS | AUTHORED
    assert {json.loads(p.read_text())["task"] for p in NIGHT2} == REPLACED
```

Run `uv run pytest tests/test_census_records_frozen.py -q` before the `CENSUS_TASKS` edit (expect FAIL on the old equality) and after (expect PASS).

- [ ] **Step 8: Provenance, gates and commit**

```bash
cd "$EVALS"
uv run python tools/provenance.py new tools/task_specs/selfhost-preflight-quiet.json \
  $(git status --porcelain --untracked-files=all -- src/satyrn_evals/tasks/selfhost-preflight-quiet | awk '{print $2}')
just gates; echo "gates=$?"
git add tools/task_specs/selfhost-preflight-quiet.json src/satyrn_evals/tasks/selfhost-preflight-quiet \
  tools/cut_task.py src/satyrn_evals/qualify.py tests/test_cut_task.py tests/test_qualify.py \
  tests/test_census_records_frozen.py PROVENANCE.md
git commit -m "Authored census task: cut selfhost-preflight-quiet, disclosed as authored, and qualified"
```

Expected: `gates=0`, including the frozen-record guard (the five existing records still match their trees) and the provenance check (every file of the new task tree has a row).

---

### Task 4: The R0 §1.2 validity check

Spec section 3, role 4, run exactly as `docs/superpowers/specs/2026-09-15-release-two-task-validity.md`'s Recompute block runs it, by the harness's selectable model from the cut prompt and `base/` alone (Ruling 8).

**Files:**
- Create: `evidence/2026-09-17-census-2/validity/selfhost-preflight-quiet/{PROMPT.txt,solution.diff,receipt.json,REPORT.md}`, `evidence/2026-09-17-census-2/validity/README.md`
- Modify: `src/satyrn_evals/tasks/selfhost-preflight-quiet/manifest.json` (the post-cut `validity` block), `PROVENANCE.md`

**Interfaces:**
- Consumes: Task 3's committed task tree and `CENSUS_TASKS` entry.
- Produces: `manifest["validity"] == {"by": <the model that ran>, "commit": <evals HEAD>, "passed": true}`, which Task 7 Step 1 gates the record on.

- [ ] **Step 1: Build the solver's world — a copy of `base/`, one commit, and the cut prompt**

```bash
cd "$EVALS"
T=selfhost-preflight-quiet
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
wc -c "$SCRATCH/validity/$T/PROMPT.txt"
grep -c 'preflight_quiet' "$SCRATCH/validity/$T/PROMPT.txt"
```

Expected: a tree with one commit, and a `PROMPT.txt` that names `scripts/preflight_quiet.py` and `tests/` and nothing hidden. `SCRATCH` is the session scratchpad, never `/tmp`.

- [ ] **Step 2: Dispatch one solver, blocking**

Dispatch **one** subagent, blocking, given `PROMPT.txt`'s text and the tree path and nothing else. Request the design's named role; if the harness offers only one selectable model, use it and record that model — the substitution is ratified (Ruling 8), so this is not a stop. It may read and write only that tree. Off limits, named individually so the instruction is checkable: the `satyrn-evals` checkout; inside the task directory `overlay/`, `fixtures/`, `manifest.json` and `qualification.json`; `~/satyrn-runs/`; `/Users/Shared/`; `docs/superpowers/plans/`, **including `docs/superpowers/plans/2026-09-18-preflight-quiet.md`, which holds both the heading the prompt was cut from and the acceptance suite itself**; and `docs/superpowers/specs/2026-09-17-release-two-authored-task-design.md`. It does not run the hidden suite — it has no access to one — and may run whatever public suite the base carries. It does not write the diff. Its final report says what it changed and why. No haiku, no GPU, no network beyond the model itself.

- [ ] **Step 3: Harvest controller-side and run the leak tells**

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
                     f"tasks/{task}", "2026-09-18-preflight-quiet.md") if w in diff]
print("expected_test_id tells:", tells)
print("path tells:", words)
raise SystemExit(1 if tells or words else 0)
PY
echo "tells=$?"
```

Expected: `tells=0`. Run the same two tells by eye over the agent's final report. A hit voids the run: fresh agent, and the void recorded in the README. Matching the known-good patch is **not** a tell — a correct solution is supposed to look like the fix.

- [ ] **Step 4: Grade offline, from a marker-free directory, and read the receipt**

```bash
( cd "$GRADE_ROOT" && UV_OFFLINE=1 uv run --project "$EVALS" satyrn-evals grade "$T" \
    "$SCRATCH/validity/$T/solution.diff" --receipt receipt.json )
uv run python -c "import json;b=json.load(open('$GRADE_ROOT/receipt.json'));print(b['verdict'], len(b['evidence']['executed_test_ids']), b.get('grader_content_in_patch'))"
```

The grade root must have no `pyproject.toml`, `pytest.ini`, `.pytest.ini`, `tox.ini`, `setup.cfg` or `conftest.py` in it or above it. The verdict is read from `receipt.json`'s `verdict` field, **never** from the exit status. `grader_content_in_patch` is its own field and is reported as its own column — night 1's whole-path review found it must not be conflated with the two named leak tells.

- [ ] **Step 5: Write the `validity` block and re-check the cut**

```bash
cd "$EVALS"
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
uv run python tools/cut_task.py check tools/task_specs/selfhost-preflight-quiet.json; echo "recheck=$?"
```

Expected: `passed: true` and `recheck=0` — `check` ignores the post-cut `validity` key, so the annotation must not move the tree's comparability.

**If `passed` is false (Ruling 9):** a recorded `prompt_edits` entry is permitted **only** for a fact the heading's stripped code stated and the prose and `formats` did not. Point at the fence that states it, add the edit with its `reason`, remove the cut tree deliberately, re-cut, re-check, re-qualify, and re-run this whole task with a fresh agent. If the failure traces to anything else — a fact no part of the spec states, or a genuinely ambiguous sentence — record `passed: false` in the README and **stop for the maintainer**; an agent does not re-scope an approved task.

- [ ] **Step 6: Preserve the artefacts and write the README**

```bash
cd "$EVALS"
mkdir -p "evidence/2026-09-17-census-2/validity/$T"
cp "$SCRATCH/validity/$T/PROMPT.txt" "$SCRATCH/validity/$T/solution.diff" \
   "$GRADE_ROOT/receipt.json" "evidence/2026-09-17-census-2/validity/$T/"
```

Write the solver's final report to `evidence/2026-09-17-census-2/validity/$T/REPORT.md`, and `evidence/2026-09-17-census-2/validity/README.md` in the shape of `evidence/2026-09-16-census/validity/README.md`: the date; a per-task row carrying the task, the verdict, the executed-test count read as `verdict` and `len(evidence.executed_test_ids)` from the receipt, the evals commit the prompt was read from, the two **named** leak tells, and `grader_content_in_patch` as its own separate column; a paragraph saying this task is **authored, not cut**, naming the design spec, the heading document and the three roles, and saying that the plan document is excluded from `base/` by the generator rather than by instruction (Ruling 5); and a Model section naming the model that ran, why it ran (Ruling 8), and the maintainer's standing caveat carried verbatim from night 1 — read the certification as slightly weaker than the design's named instrument, and re-check on that instrument if the task turns out easier than expected. Cross-reference `evidence/2026-09-18-census-3/` as the night this certificate admits (Ruling 15).

- [ ] **Step 7: Provenance, gates and commit**

```bash
cd "$EVALS"
uv run python tools/provenance.py new evidence/2026-09-17-census-2/validity/README.md \
  evidence/2026-09-17-census-2/validity/selfhost-preflight-quiet/PROMPT.txt \
  evidence/2026-09-17-census-2/validity/selfhost-preflight-quiet/solution.diff \
  evidence/2026-09-17-census-2/validity/selfhost-preflight-quiet/receipt.json \
  evidence/2026-09-17-census-2/validity/selfhost-preflight-quiet/REPORT.md
just gates; echo "gates=$?"
git add evidence/2026-09-17-census-2/validity \
  src/satyrn_evals/tasks/selfhost-preflight-quiet/manifest.json PROVENANCE.md
git commit -m "Authored census task: the R0 §1.2 validity check for selfhost-preflight-quiet"
```

Expected: `gates=0`. This is the **last** commit that touches the task tree (Ruling 7); Tasks 5 and 6 measure and review without writing into it.

---

### Task 5: Measure the size targets and record them

Spec section 2, "size targets, measured before admission". Measured on the artefacts the census uses, not on the worktree (Ruling 10). Nothing here writes into the task tree.

**Files:**
- Create: `evidence/2026-09-17-census-2/validity/selfhost-preflight-quiet/SIZE.md`
- Modify: `PROVENANCE.md`

**Interfaces:**
- Consumes: Task 3's manifest and fixtures; Task 2's `base` and `good`.
- Produces: three measured numbers and a pass/fail against the medium tier, which Task 7's record depends on.

- [ ] **Step 1: The hidden test count**

```bash
cd "$EVALS"
uv run python -c "
import json
b = json.load(open('src/satyrn_evals/tasks/selfhost-preflight-quiet/manifest.json'))
ids = b['expected_test_ids']
print('hidden tests:', len(ids))
print('\n'.join(ids))
print('in 15..20:', 15 <= len(ids) <= 20)
"
```

Expected: **20**, and `in 15..20: True`. Twenty is the top of the medium tier's band and deliberately so: the design asks for 15–20 and every one of the twenty is a direction or an edge the spec names. These are the ids the grader executes, collected at `good` by the generator — the authoritative count. A number outside 15–20 is a missed target: **stop** (Ruling 11).

- [ ] **Step 2: The public suite at `base`**

```bash
cd "$EVALS"
BASE=<the base sha>
git worktree add --detach "$SCRATCH/base-preflight-quiet" "$BASE"
( cd "$SCRATCH/base-preflight-quiet" && uv sync -q && time uv run pytest -q -m "not integration" 2>&1 | tail -3 )
git worktree remove --force "$SCRATCH/base-preflight-quiet"
```

Expected: a wall-clock figure **under 40 s**. This is the suite a cell runs dozens of times inside a 4,800 s backstop; at or over 40 s the task spends the night in its own tests and is a missed target: **stop**. Record the measured seconds, the machine, and whether anything else was running. Remove the scratch worktree whether the measurement passed or not; it is not one of the seven historical worktrees and must not be left behind.

- [ ] **Step 3: The diff's reach**

```bash
cd "$EVALS"
grep '^diff --git' src/satyrn_evals/tasks/selfhost-preflight-quiet/fixtures/known-good.patch
git show --name-only --format= <the good sha>
git diff --name-only <the base sha> <the good sha>
```

Expected: the graded patch (`known-good.patch`) touching exactly `scripts/preflight_quiet.py`; the good commit touching exactly `scripts/preflight_quiet.py`, `tests/test_preflight_quiet.py` and `PROVENANCE.md` — one new module, one new test module, and the convention row the base's `AGENTS.md` requires, which is in `ignored_paths` and excluded from `base/` (Ruling 12). A third source module is a missed target: **stop**.

- [ ] **Step 4: Re-confirm the suite is the heading's**

```bash
cd "$EVALS"
uv run python - <<'PY'
import re, subprocess
from pathlib import Path
doc = Path("docs/superpowers/plans/2026-09-18-preflight-quiet.md").read_text(encoding="utf-8")
body = doc[doc.index("### Task 1: The machine-quiet preflight"):]
want = re.search(r"```python\n(.*?)\n```", body, re.S).group(1) + "\n"
got = Path("src/satyrn_evals/tasks/selfhost-preflight-quiet/overlay/test_preflight_quiet.py").read_text(encoding="utf-8")
print("overlay identical to the heading:", want == got)
raise SystemExit(0 if want == got else 1)
PY
echo "unedited=$?"
```

Expected: `unedited=0`. The overlay the grader runs is byte-identical to the suite written from the spec before any implementation existed — the claim on which "authored, not cut" rests (Ruling 13).

- [ ] **Step 5: Write `SIZE.md`, then gates and commit**

Write `evidence/2026-09-17-census-2/validity/selfhost-preflight-quiet/SIZE.md`: the three targets, the three measured numbers, the command that produced each, the machine and date for the timed one, the overlay identity check, and one line saying the task lands in the medium-build tier the census's signed reading describes (`evidence/2026-09-16-census/README.md`, `classes-summary.md`) — the run-record-gate size class of one module, 15–20 hidden tests and a public suite under 40 s — and not the large tier that cell-loop and speed-probe occupy.

```bash
cd "$EVALS"
uv run python tools/provenance.py new evidence/2026-09-17-census-2/validity/selfhost-preflight-quiet/SIZE.md
just gates; echo "gates=$?"
git add evidence/2026-09-17-census-2/validity/selfhost-preflight-quiet/SIZE.md PROVENANCE.md
git commit -m "Authored census task: the measured size targets for selfhost-preflight-quiet"
```

Expected: `gates=0`.

---

### Task 6: Whole-path review by a non-implementer

Spec section 6, "a whole-path reviewer before launch", and the night-2 plan's standing lesson: every accepted finding becomes a default-tier test. The reviewer implemented none of Tasks 1–5.

**Files:**
- Modify (only if a finding requires it): `tests/test_cut_task.py`, `tests/test_qualify.py`, `tools/cut_task.py`, `src/satyrn_evals/qualify.py`
- Never: `src/satyrn_evals/tasks/selfhost-preflight-quiet/` (Ruling 7 — the tree is frozen from Task 4's commit onward)

**Interfaces:**
- Consumes: everything Tasks 1–5 committed.
- Produces: an adjudicated finding list in the ledger, a test per accepted finding, and the go/no-go for Task 7.

- [ ] **Step 1: Review the whole path, in six passes**

Dispatch one reviewer over the task tree, the prompt and the validity artefacts. Name every finding Critical / Important / Minor with the file and line, and say for each whether it is reachable on the night as designed.

1. **The authoring separation** — did the heading precede the implementation, is the overlay byte-identical to the heading's block, and does anything in Tasks 1–5's commits show the suite being bent to the code?
2. **The prompt** — read `manifest.contracts["R1-plan"]` as a stranger. Is every structural fact the 20 tests assert determined by it: the module path, the six names, the three dataclasses, the three thresholds' directions, the ignore rule, the problems order, the token weighting, the JSON shape, the two exit codes, the four CLI defaults? Anything determined only by the stripped code is a finding, even though the validity check passed.
3. **The leak surface** — `base/` against Ruling 5's three tells; the overlay's contents; `hunt_names` now carrying the new basename; and whether any file committed by Tasks 1–5 puts the answer somewhere a later task's `base/` would carry it.
4. **The disclosure** — is `generator.authored` inside what `cut_task.py check` compares, does `judge_authored` refuse every malformed shape, and do the six cut tasks still re-cut byte-identically?
5. **The size targets** — were all three measured on the artefacts Ruling 10 names, and does `SIZE.md` state the machine and the commands?
6. **The record's preconditions** — `validity.passed` true, the tree digest stable since Task 4, `CENSUS_TASKS` carrying the task, and nothing in Tasks 1–6 having touched `counterfactual.py`, the arms, the launcher, the five existing task trees or the two night scripts.

- [ ] **Step 2: Adjudicate each finding, in the ledger**

For each: ADDRESSED (with the commit), NOT ADDRESSED BY DESIGN (with the reason and the ratification, if any), or DEFERRED (with who carries it). **A Critical that is reachable on the night stops the plan** until it is addressed; the record is not written over it. A finding that would require editing the task tree is by construction a stop, not a fix (Ruling 7): fixing it means re-cutting and re-running validity, which is the maintainer's call.

- [ ] **Step 3: Every accepted finding becomes a default-tier test**

Write the failing test first, run it to see it fail, fix, run it to see it pass. No model, no network, no subprocess.

- [ ] **Step 4: Scoped re-review and commit**

Dispatch a scoped re-reviewer on the fix diff only: are all three of ADDRESSED / NOT ADDRESSED / DEFERRED honest, and did the fix break anything?

```bash
cd "$EVALS"
just gates; echo "gates=$?"
git add <the files the fixes touched>
git commit -m "Authored census task: whole-path review findings and their tests"
```

Expected: `gates=0`. If the review found nothing, there is no commit and the ledger says so — a legitimate outcome, recorded, never manufactured.

---

### Task 7: The record, the launch script, the frozen-record guard, the ROADMAP row and the checklist

Spec section 4. Frozen and committed in daylight; the maintainer starts the script. Nothing is launched by this task.

**Files:**
- Create: `records/2026-09-18-census3-selfhost-preflight-quiet.json`, `scripts/census_night_3.sh`
- Modify: `tests/test_census_records_frozen.py`, `ROADMAP.md`, `PROVENANCE.md`

**Interfaces:**
- Consumes: Task 3's task tree and `CENSUS_TASKS`, Task 4's `validity` block, Task 5's measured targets, Task 6's go.
- Produces: one frozen record and one script the maintainer runs.

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
uv run pytest tests/test_census_records_frozen.py -q; echo "frozen-before=$?"
```

Expected: `validity=0` and `frozen-before=0`. A non-zero exit stops this task.

- [ ] **Step 2: Write the record**

```bash
cd "$EVALS"
PREV='records/2026-09-17-census2-selfhost-speed-probe.result.json'
RULE='none for outcomes: release-two admission is decided in section 8 of 2026-09-15-release-two-census-design.md from the classified table, not from a pass count'
AUTH='maintainer-approved authored task, spec docs/superpowers/specs/2026-09-17-release-two-authored-task-design.md, approved 2026-09-17; the third medium-build census task, authored not cut -- heading by Opus from the spec, implementation by Sonnet, prompt-only validity by the harness solver -- reported beside the cut tasks and never pooled with them'

uv run satyrn-evals record new \
  --output records/2026-09-18-census3-selfhost-preflight-quiet.json \
  --task selfhost-preflight-quiet --rung R1-plan \
  --arm baseline --model omlx/Ornith-1.5-9B-MLX-8bit \
  --n 6 --k 3 --purpose admission --isolation isolated --mode batch \
  --max-minutes 240 --token-budget 48000 --turn-budget 72 --command-backstop 4800 \
  --previous-result "$PREV" --authority "$AUTH" --decision-rule "$RULE"

uv run satyrn-evals launch --check records/2026-09-18-census3-selfhost-preflight-quiet.json; echo "check=$?"
uv run python -c "
import json
b = json.load(open('records/2026-09-18-census3-selfhost-preflight-quiet.json'))
print(b['task'], b['rung'], b['n'], b['k'], b['token_budget'], b['turn_budget'],
      b['command_backstop_s'], b['max_minutes'], b['mode'], b['isolation'], b['purpose'])
print('   prev:', b['previous_result'])
print('   auth:', b['authority'])
print('   rule:', b['decision_rule'])
"
```

Expected: `check=0` and one line reading `selfhost-preflight-quiet R1-plan 6 3 48000 72 4800 240 batch isolated admission`, the previous result the committed night-2 speed-probe result (Ruling 14), the authority naming the authored-task design and its 2026-09-17 approval, and the decision rule the night-1 one verbatim. `--command-backstop 4800` satisfies the gate `4800 + 300 <= 240 * 60`; the derived per-cell wall clock is 5,100 s, so n = 6 at k = 3 is two waves, about 170 minutes, inside 240.

- [ ] **Step 3: Write the launch script**

Create `scripts/census_night_3.sh` and `chmod +x` it. It is `scripts/census_night_2.sh` with the task list, the record prefix and the comment changed, and nothing else — neither night-2 nor night-1's script is touched.

```sh
#!/bin/sh
# census_night_3.sh -- run the 2026-09-18 census night 3, from the evals checkout.
# One record, six cells: the authored third medium-build task selfhost-preflight-quiet
# (docs/superpowers/specs/2026-09-17-release-two-authored-task-design.md, approved
# 2026-09-17), Baseline only, n = 6 at k = 3, 48,000 tokens / 72 turns, 4,800 s backstop,
# on a quiet machine. The result is committed when the record completes.
# Exits with the launcher exit code, or 2 before any launch.
set -u
TRAILER="Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
ARM=arms/baseline-ornith15-9b.json
TASKS="selfhost-preflight-quiet"

# Settings provenance, both arms, as the cell user. A disagreement here means the
# oMLX entry or the cell's models.json is not at 16,000; nothing launches.
for a in arms/baseline-ornith15-9b.json arms/engine-ornith15-9b.json; do
  uv run python scripts/preflight_settings.py "$a" --cell > /dev/null || {
    echo "census3: preflight_settings failed for $a" >&2; exit 2; }
done

S=2
for T in $TASKS; do
  R="records/2026-09-18-census3-$T.json"; RES="records/2026-09-18-census3-$T.result.json"
  [ -f "$R" ] || { echo "census3: missing $R" >&2; exit 2; }
  if [ -f "$RES" ] && [ "$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["status"])' "$RES")" = "complete" ]; then
    echo "census3: $T already complete"; continue
  fi
  S=4
  while [ "$S" -eq 4 ]; do          # 4 is CAPPED: the launcher resumes the same record
    uv run satyrn-evals launch "$R" --arm "$ARM"; S=$?
  done
  if [ -f "$RES" ]; then
    STATUS=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["status"])' "$RES")
    git add "$RES" && { git diff --cached --quiet || git commit -qm "Census night 3 result: $T ($STATUS)

$TRAILER"; }
  fi
  [ "$S" -eq 0 ] || { echo "census3: $T stopped with $S" >&2; break; }
done
echo "census3 EXIT: $S"; exit "$S"
```

- [ ] **Step 4: Prove the script's gates without launching**

```bash
cd "$EVALS"
chmod +x scripts/census_night_3.sh
sh -n scripts/census_night_3.sh; echo "syntax=$?"
[ -f records/2026-09-18-census3-selfhost-preflight-quiet.json ] || echo MISSING
grep -n 'census3\|4800\|2026-09-18-census3' scripts/census_night_3.sh | head
git diff --stat -- scripts/census_night.sh scripts/census_night_2.sh
uv run python scripts/preflight_settings.py arms/baseline-ornith15-9b.json --cell > /dev/null; echo "settings=$?"
```

Expected: `syntax=0`, no `MISSING`, the grep showing the night-3 prefix everywhere, and an **empty** diff over the two frozen night scripts (Ruling 16). `settings` may be non-zero until the operator has restarted oMLX with the 16,000 cap; record which it printed — it is the operator's step, not this task's.

- [ ] **Step 5: Extend the frozen-record guard — failing test first**

Add night 3 to `tests/test_census_records_frozen.py`. Run the file before the additions to see the new rows fail on an empty `NIGHT3`, and after to see them pass.

```python
NIGHT3 = _frozen("2026-09-18-census3-")
AUTHORED_TASK = "selfhost-preflight-quiet"
AUTHORED_SPEC = "docs/superpowers/specs/2026-09-17-release-two-authored-task-design.md"
```

Extend the existing tree-pinning parametrization to `NIGHT1 + NIGHT2 + NIGHT3`, then add:

```python
def test_night_three_is_the_one_authored_record() -> None:
    """Authored-task design section 4: one Baseline admission record for the
    third medium-build task, which is authored rather than cut."""
    assert {json.loads(p.read_text())["task"] for p in NIGHT3} == {AUTHORED_TASK}


@pytest.mark.parametrize("record_path", NIGHT3, ids=[p.stem for p in NIGHT3])
def test_a_night_three_record_carries_the_designs_parameters(record_path: Path) -> None:
    """Section 4: Baseline, admission, batch, isolated, n = 6, k = 3, 48,000 / 72,
    a 4,800 s backstop, 240 minutes, chained from the night-2 speed-probe result."""
    record = json.loads(record_path.read_text())
    assert record["arm"] == "baseline"
    assert record["purpose"] == "admission"
    assert record["mode"] == "batch"
    assert record["isolation"] == "isolated"
    assert record["n"] == 6
    assert record["k"] == 3
    assert record["token_budget"] == 48_000
    assert record["turn_budget"] == 72
    assert record["command_backstop_s"] == 4_800
    assert record["max_minutes"] == 240
    assert record["command_backstop_s"] + 300 <= record["max_minutes"] * 60
    assert record["previous_result"] == "records/2026-09-17-census2-selfhost-speed-probe.result.json"
    assert record["rung"] == "R1-plan"
    assert record["model"] == "omlx/Ornith-1.5-9B-MLX-8bit"
    assert record["decision_rule"] == DECISION_RULE


def test_the_night_three_record_names_the_authored_task_design_and_its_approval() -> None:
    """The disclosure travels with the record, not only with the page: a reader of
    the record alone learns the task was authored and under which approved spec."""
    record = json.loads((RECORDS / f"2026-09-18-census3-{AUTHORED_TASK}.json").read_text())
    assert AUTHORED_SPEC in record["authority"]
    assert "approved 2026-09-17" in record["authority"]
    assert "authored not cut" in record["authority"]


def test_the_authored_task_manifest_discloses_itself() -> None:
    """Sibling of the record check, one layer down: the task tree says the same
    thing the record says, inside the body `cut_task.py check` compares."""
    body = json.loads((DEFAULT_TASKS_ROOT / AUTHORED_TASK / "manifest.json").read_text())
    assert body["generator"]["authored"] is True
    assert body["generator"]["authoring"]["spec"] == AUTHORED_SPEC
    assert body["generator"]["authoring"]["roles"]
    assert body["validity"]["passed"] is True


def test_a_cut_census_task_carries_no_authored_disclosure() -> None:
    """The refusal's sibling: the five cut tasks must not claim to be authored,
    or the census page's authored/cut split would be meaningless."""
    for task in NIGHT1_TASKS:
        body = json.loads((DEFAULT_TASKS_ROOT / task / "manifest.json").read_text())
        assert "authored" not in (body.get("generator") or {})
```

Then verify the guard bites and recovers:

```bash
cd "$EVALS"
uv run pytest tests/test_census_records_frozen.py -q; echo "guard=$?"
printf '\n' >> src/satyrn_evals/tasks/selfhost-preflight-quiet/manifest.json
uv run pytest tests/test_census_records_frozen.py -q; echo "drifted=$?"
git checkout -- src/satyrn_evals/tasks/selfhost-preflight-quiet/manifest.json
uv run pytest tests/test_census_records_frozen.py -q; echo "restored=$?"
```

Expected: `guard=0`, `drifted=1` naming the night-3 record, `restored=0`. That is the refusal test and its sibling success test.

- [ ] **Step 6: The ROADMAP row**

Re-read `ROADMAP.md` first. In the R0 row's "Done when" cell, append one sentence:

`The third medium-build task is authored, not cut: selfhost-preflight-quiet (docs/superpowers/specs/2026-09-17-release-two-authored-task-design.md, approved 2026-09-17), cut 2026-09-18, validity-checked under R0 §1.2, 20 hidden tests and a public suite under 40 s; one Baseline admission record frozen for census night 3 (n = 6, 48,000 tokens, 72 turns, 4,800 s, k = 3); wiring the check into launch --preflight is a separate later commit.`

Nothing else changes. `wc -l ROADMAP.md` must print at most 150.

- [ ] **Step 7: Provenance, gates, the integration tier, and commit**

```bash
cd "$EVALS"
uv run python tools/provenance.py new scripts/census_night_3.sh \
  records/2026-09-18-census3-selfhost-preflight-quiet.json
just gates; echo "gates=$?"
uv run pytest -m integration; echo "integration=$?"
git add scripts/census_night_3.sh records/2026-09-18-census3-selfhost-preflight-quiet.json \
  tests/test_census_records_frozen.py ROADMAP.md PROVENANCE.md
git commit -m "Authored census task: the frozen night-3 Baseline record, the launch script, and the guard extended"
```

Expected: `gates=0`. For `integration`, compare against the last recorded baseline (`b624b84`: 335 passed, 1 skipped, 0 failed) and against the known-failing Xcode-license git rows. **A new integration failure is a finding and stops the plan**: `just gates` excludes this tier, so nothing else in the plan would have seen it. Nothing is launched by this task.

---

## Operator commands

Everything in this section is the maintainer's, attended, after Task 7 is committed. No agent runs any of it.

**1. Confirm the served per-turn cap is still 16,000 and both arms agree.**

```bash
uv run python scripts/preflight_settings.py arms/baseline-ornith15-9b.json --cell > /dev/null; echo "baseline=$?"
uv run python scripts/preflight_settings.py arms/engine-ornith15-9b.json --cell > /dev/null; echo "engine=$?"
```

Expected: both 0. A non-zero exit names the field and the two values; fix the config, never the arm file, and restart oMLX. **Nothing launches until both are 0.**

**2. Preflight the cell, and hunt.**

```bash
uv run satyrn-evals launch --preflight records/2026-09-18-census3-selfhost-preflight-quiet.json \
  --arm arms/baseline-ornith15-9b.json; echo "preflight=$?"
```

Expected: `preflight=0`, with the printed JSON's `problems` empty and `hunt_hits` empty. This runs the root-anchored hunt as the cell user; a hit is grader material reachable from `/` and stops the night. **This task is new to the hunt** — `hunt_names` now carries `test_preflight_quiet.py`, a basename it has never searched for before, so read the `hunt_names` list in the output and confirm it is there.

**3. Confirm the cells root is empty, the tree is clean, and the record is frozen.**

```bash
sudo ls -la /Users/Shared/satyrn-cells/ | head
git status --porcelain; echo "dirty=$?"
git log --oneline -1
uv run pytest tests/test_census_records_frozen.py -q; echo "frozen=$?"
```

Expected: no leftover worktree parents beyond the committed engine export; `git status --porcelain` printing nothing; the head Task 7's commit; `frozen=0`. A record must be tracked and unchanged against `HEAD` or `launch` refuses it.

**4. The quiet-machine precondition — the maintainer's.** Nothing else runs on this machine from launch until the script exits: no other model-server client, no build, no indexing, no second agent session. Night 1 lost nine cells to a shared machine at 14–26 tok/s per stream against run 2's ~30. The check this task builds is **not** wired into `launch --preflight` yet (Ruling 6), and it cannot be run from this branch either: `scripts/preflight_quiet.py` is the authored task's own answer, so it lives only in the cut tree's overlay and never on `release-one`. The precondition is therefore the maintainer's judgement, read by hand: the one-minute load average against 0.5 × the core count, the busy processes in `ps -axo pid,pcpu,comm`, and the recent decode rate in `~/.omlx/logs/server.log` against night 2's ~18.5 tok/s baseline. What it shows belongs in the night's ledger either way.

**5. The pre-registered post-hoc read is already committed — read it, do not run it yet.** `evidence/2026-09-18-census-3/postreg.md` was written and committed before Task 7's record existed, against the disclosed four ungraded-literal gaps in the hidden suite (I2/P1/P3/P4, `evidence/2026-09-17-census-2/validity/selfhost-preflight-quiet/README.md`). It is read in the morning, beside the classifier, over each retained cell's harvested patch — **never before the night**, because it has nothing to read until night 3's cells exist, and **never to change a verdict**: it is a disclosure-side read of the four parked literals, not a second grading pass.

**6. Start the night.**

```bash
sh scripts/census_night_3.sh 2>&1 | tee "$HOME/satyrn-census-night-3.log"
```

Expected: about three hours for six cells (two waves at k = 3, 5,100 s per cell of wall clock). The script commits the result when the record completes. A capped record resumes on the next launch of the same record; nothing restarts from zero and no cell is replaced. An `EXIT:` other than 0 means the launcher established an infrastructure failure — diagnose, repair, and re-run the script, which skips a task already `complete`. **`census3 EXIT: 2` does not by itself mean failure**: `2` is both the script's pre-launch sentinel (`S=2`, set before the loop and never reassigned when the record is already `complete` on entry, so a re-run after a finished night falls straight through to `echo "census3 EXIT: $S"` with the untouched sentinel) and `UsageError.exit_code` (`src/satyrn_evals/errors.py`), the code the launcher itself returns for a real usage failure. The three sources read differently on stdout/stderr, so tell them apart there, not from the number: a re-run of an already-finished night prints only `census3: selfhost-preflight-quiet already complete` on stdout, with nothing on stderr; a pre-launch precondition failure (a missing record, or a failed settings preflight) prints a `census3: ...` line on **stderr** and exits immediately, before the script ever reaches its own `EXIT:` line; a genuine launcher failure during an actual launch attempt prints `census3: selfhost-preflight-quiet stopped with 2` on stderr and *then* falls through to `census3 EXIT: 2`. If `EXIT: 2` appears with no `stopped with` line on stderr, it is the already-complete case — re-running the script is a no-op, not a retry.

**7. In the morning: commit the result, then classify into night 3's own directory, and run the pre-registered read alongside it.**

```bash
git status --porcelain -- records
git add records/2026-09-18-census3-selfhost-preflight-quiet.result.json \
  && git commit -m "Census night 3 result: the authored task, 2026-09-18"
uv run --project . python evidence/2026-09-16-census/classify.py \
  --night "$HOME/satyrn-runs/2026-09-18-census3-selfhost-preflight-quiet" \
  --record records/2026-09-18-census3-selfhost-preflight-quiet.json \
  --out evidence/2026-09-18-census-3 \
  --grade-root "$HOME/satyrn-census-grades"; echo "classify=$?"
```

Expected: `classify=0` and `evidence/2026-09-18-census-3/selfhost-preflight-quiet/{cells.json,table.md,classes.md}`. **`--out` is not optional**: the driver's `night` key refuses to overwrite another night's directory, and without it this would land in night 1's folder. The eight class columns in `classes.md` are empty: filling them is the attended review, argued from the reconstruction and cited by turn. Beside the classifier, and only after it, read `evidence/2026-09-18-census-3/postreg.md` against the retained cells' harvested patches, per its own steps — advisory to the ledger, not a second verdict. Then the census page (`evidence/2026-09-16-census/README.md`, ≤ 120 lines) gains this task's rows with the line that it is **authored, not cut** — never pooled with the cut tasks — and the R0 sitting reads whichever of section 5's three branches the night lands in.

**8. What the night decides** (spec section 5). If the six cells show the finishing shape, the medium tier is three tasks wide and the R0 sitting sizes an outcome claim on it. If they pass comfortably, it is a floor task and the tier stays two wide. If they reach no pass state, the size class was misjudged and the task is re-scoped, not claimed against. Either way the census page reports it as authored.

---

## Self-review against the spec

- **Section 1, why an authored task.** The plan never pools it with the cut tasks: the disclosure is in the manifest's `generator` block where `cut_task.py check` compares it (Task 3, Ruling 4), in the record's `authority` (Task 7 Step 2), in the guard's tests (Task 7 Step 5), in the validity README (Task 4 Step 6) and in the census page (operator command 7).
- **Section 2, the task.** Task 1's heading document builds `scripts/preflight_quiet.py` with the four spec'd functions and the CLI, exactly the signatures the spec lists, with two additions recorded as underspecifications below. `source_paths` is `scripts/preflight_quiet.py` plus `tests`, and `ignored_paths` is `PROVENANCE.md`, both by the generator's own rule. The hidden suite is 20 tests: each parser on a known-good and a known-bad input, each threshold at and across its edge, the ignore list both ways, the token weighting on two completions of unequal length, the fewer-than-N case, the certificate JSON shape, and both CLI exit codes — no network, no subprocess, no real `ps` (Ruling 2). The three size targets are measured in Task 5 and a miss stops the plan (Ruling 11). `launch --preflight` wiring is deferred (Ruling 6).
- **Section 3, how it is authored and who sees what.** Role 1 is Task 1 (Opus, heading and suite, before any implementation). Role 2 is Task 2 (Sonnet, worktree, ordinary loop, `good` whose parent is `base`, suite unedited and proved so twice — Ruling 13). Role 3 is Task 3 (`cut_task.py cut`, `check` 0, `qualify` ok, `CENSUS_TASKS` extended). Role 4 is Task 4 (the R0 §1.2 check by the harness's selectable model from the cut prompt and `base/` only, artefacts under `evidence/2026-09-17-census-2/validity/selfhost-preflight-quiet/`, the one permitted prompt-edit path and the stop for everything else — Rulings 8 and 9). Role 5 is the disclosure, above.
- **Section 4, admission.** Task 7: one record, Baseline, `--purpose admission`, batch, n = 6, k = 3, 48,000 / 72, backstop 4,800 s, `--max-minutes 240`, isolated, chained from the last committed census result (Ruling 14), the night-1 decision rule verbatim, and an authority naming the authored-task design and its 2026-09-17 approval. `scripts/census_night_3.sh` is the night-2 script's shape with one record.
- **Section 5, what it decides.** Operator command 8 carries the three readings unchanged.
- **Section 6, rules carried.** Two-uid isolation, launcher-only inference, the record frozen and committed in daylight, no Docker or sandbox, results and reviews written only by their tools, Opus steers and reviews with Sonnet implementing and no haiku, a whole-path reviewer before launch (Task 6), commits at task boundaries with explicit paths, never push, merge or amend — all in the Global Constraints.
- **R0 §1.2 and the validity procedure** are followed step for step: the solver's world is a copy of `base/` plus `PROMPT.txt` and nothing else, the off-limits list is named individually and now names the authored plan document, the controller harvests, the two named leak tells run over the diff and the report, grading is from a marker-free root, and the verdict is read from the receipt.
- **Carried forward, unfixed by this plan and repeated here so the R0 sitting has them:** the Engine's `DELIVER_TIMEOUT_SECONDS` is 1800 against a 4,800 s record backstop, an arm-parity defect to fix **before the first Engine record of release two**; the Pi-loop length-stop semantics are still declared, not measured; `tripped_verdict` still has no denominator rule; the validity certifications rest on an instrument the design did not name; and the machine-quiet check this task builds is not yet called by `launch --preflight`.

## Underspecified or contradictory in the spec

Each was decided in this plan and is flagged for the maintainer rather than buried.

1. **`certificate`'s signature cannot produce its own fourth message.** The spec gives `certificate(load, busy, rate, *, floor_tok_s) -> Certificate` and also fixes the message `decode: fewer than <n> completions for <model>` — but `<n>` and `<model>` are exactly the two facts `rate is None` erases. Decided: two keyword-only parameters are added, `model` and `last`, and the full signature is stated in the heading's `Produces:` so the prompt determines it.
2. **`certificate`'s first parameter is the load *message*, not the load reading.** The spec calls the certificate "a JSON-serialisable record of every input" while passing it `load_problem`'s output, which has already discarded the loadavg and the core count. Decided: `load` is `str | None`, and "every input" means every input to `certificate` — so `as_dict()["inputs"]` records the message, the busy list, the decode reading and the three thresholds, and not the raw load average. If the maintainer wants the raw triple in the certificate, the signature must change and the task must be re-cut.
3. **The CLI's defaults are not in the spec.** `--ceiling`, `--cpu-floor`, `--floor-tok-s` and `--last` are listed as optional flags with no default values, yet a hidden suite that drives the CLI must assert something. Decided: 0.5, 20.0, 30.0 and 20, stated in `formats` so the prompt determines them. The decode floor of 30.0 tok/s is chosen to sit at run 2's measured ~30 tok/s per stream, the number night 1's contention fell below.
4. **The ignore list has no members in the spec.** "System agents, the model server itself" is a description, not a tuple, and the suite asserts the default list's behaviour. Decided: `IGNORE_PREFIXES = ("/sbin/", "/usr/sbin/", "/usr/libexec/", "/System/", "/usr/local/bin/omlx-")`, in `formats`. The last entry is a guess at the local oMLX install path and is the one value the maintainer should check against the real machine before the night; it affects only the CLI's default, never the pure API.
5. **`decode_rate`'s `Rate` type is named but not defined.** Decided: frozen, with `tok_s`, `completions`, `tokens` and `seconds` — the four fields the messages and the certificate need.
6. **`Process` collides with `scripts/preflight_processes.py`'s `Process`.** Different module, different fields (`pid, ppid, command` there; `pid, comm, cpu` here), no import between them, so there is no conflict in code — but a reader of `scripts/` now meets two `Process` classes. Flagged, not renamed: the spec names the type.
7. **The validity artefacts and the night's outputs live under different census directories.** The spec puts the certificate under `evidence/2026-09-17-census-2/validity/`, while night 3's classifier outputs belong under `evidence/2026-09-18-census-3/`. Followed as written, with each directory's README cross-referencing the other (Ruling 15).
8. **The spec says "`--command-backstop 4800`" and "backstop 4,800 s" but does not give `max_minutes`.** Taken as 240 from the night-2 design, which is what satisfies the `command_backstop_s + 300 <= max_minutes * 60` gate and holds n = 6 at k = 3 in two waves.
9. **The spec does not say where `authored: true` lives inside `generator`, nor what checks it.** Decided in Ruling 4: an optional cut-spec key, written by the generator, checked by a new pure `qualify` check — the only placement that both `cut_task.py check` and `qualify` can see.
