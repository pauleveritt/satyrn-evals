# C4 Re-derive the finishing counterfactual on the C3 census, then resume R0's order — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or superpowers:executing-plans. Steps use `- [ ]`. **Approved 2026-10-03: the maintainer ruled D1-D10 in session ("go with recommendations on C4's decisions"; ledger "2026-10-03 — C4's decisions ruled; the C4 plan approved"). Drafted 2026-10-02 as `2026-10-02-c4-counterfactual-DRAFT.md`, renamed on approval. Task 1's pre-registration is drafted at `docs/superpowers/specs/2026-10-03-c4-finishing-counterfactual-rederive.md` and is not yet approved; it is approved and committed before C3's daylight freeze (D1).** No census cell, result JSON, night directory, grade output or counterfactual tally was opened while drafting.

**Goal:** Pre-register the counterfactual's verdict rule on the C3 census before any C3 tally exists. Read it once, on admitted cells, per task. Then record which C0 marks it clears and which it keeps, and hand R0 its next sitting.

**Architecture:** A pre-registration spec is committed before C3's classifier runs. `evidence/2026-09-16-census/classify.py` already computes both readings per cell, as the census did: run 1's pre-registered rules and run 2's graded trigger-turn tree. A new evidence-local `decide.py` adds nothing per cell. It filters to admitted cells, using each night's `summary.json`, and applies section 5 of `docs/superpowers/specs/2026-09-15-release-two-finishing-counterfactual.md` with amendment 7.1, adapted to n = 6. It writes `decision.txt` and `table.md` once.

**Spec:** No approved C4 design exists. This plan argues from:
- the counterfactual pre-registration (§2–§5, amendments 7.1–7.4, §8 "Run 2");
- `evidence/2026-09-15-finishing-counterfactual/README.md` and `run-2/README.md`;
- census design §7 ("both readings recorded as before") and §8 (the R0 decisions);
- R0 constraints §1.4 and §2;
- the unisolated-harness design §3 C3–C4;
- `ROADMAP.md` "Deferred" (the parked `derive-new-top-level-module` branch);
- the EB design draft §3 (`.claude/worktrees/engine-budget/docs/superpowers/specs/2026-10-02-engine-budget-design.md`).

## Rulings, 2026-10-03

**D1. When the rule is fixed.** `classify.py` prints run 1 and run 2 changes for every cell, so C3's classification step is also C4's data. Options: (A) commit the pre-registration at C3's daylight freeze, before night A; (B) commit it any time before C3 Task 7; (C) after C3's table, which breaks pre-registration. **Recommend A.** C3 Task 7 Step 1 refuses to classify without it either way. The author must have read no C3 cell, result or tally.
- **Ruled 2026-10-03: A.** The rule is fixed at C3's daylight freeze: the pre-registration is approved and committed before night A.

**D2. The method.**
- (A) `classify.py`'s two readings unchanged:
  - run 1 is `cf.unmeasured_reasons` and `cf.counterfactual_pass`, which is §3–§5 plus 7.1–7.4;
  - run 2 is the hidden-suite verdict of the tree at the end of the trigger turn, by **std** replay.
- (B) Run 2 proper, with `trajectory.py` `ext` replay.
- (C) A new instrument.
- **Recommend A.** It is the census's instrument, and changing it re-opens the comparison with the isolated census. Recorded contradiction: census design §7 says "run 2's replay method", but `classify.py` `_snapshot_replay` says "The `ext` replay is not carried over — it executed model-written Python, which needs its own review."
- **Ruled 2026-10-03: A.** `classify.py`'s two readings, unchanged.

**D3. Which reading decides.**
- (A) Run 2 decides, with one amendment: a cell whose run 1 reasons include `fidelity:` or `raised:` is unmeasured under run 2 too. That is §4's fidelity rule; `classify.py`'s run 2 column applies no fidelity check. Run 1 is recorded beside.
- (B) Run 1 decides.
- (C) Both must agree, or the verdict is Verify.
- **Recommend A.** Run 2's README documents three of run 1's rules as bugs (`write_text` heuristic, BSD `sed -i` error, 7.4's read-only list), and ROADMAP's R0 cell already quotes run 2's Verify. A disagreement between the readings is stated on the page.
- **Ruled 2026-10-03: A.** Run 2 decides, with the fidelity amendment: a cell whose run 1 reasons include `fidelity:` or `raised:` is unmeasured under run 2 too. Run 1 is recorded beside.

**D4. The denominator under confinement.**
- (A) Admitted cells only: refusals 0 and reaches 0, per `confinement.Finding.admitted` as of `df3b68f`, where `reaches` counts only reaches that leave the cell's worktree; a hidden basename inside the cell's own worktree is reported as `confinement_reaches_in_worktree` and does not un-admit a cell (C3 D5). Flagged, unmeasured and infrastructure-replaced cells are listed, never rescue or harm.
- (B) Also count a flagged cell whose first refusal or reach falls after its trigger turn, since stopping at green would have avoided it.
- **Recommend A**, with B's count reported beside. C3 took D5 B in its option-1 form (`df3b68f`), so "admitted" means `Finding.admitted` as of `df3b68f`, which is the per-cell `confinement_admitted` in each night's `summary.json`.
- **Ruled 2026-10-03: A, with B beside, plus a third count.** The denominator is admitted cells only. Two counts are reported beside it and never decide:
  - **Flagged after trigger (B):** a flagged cell whose first refusal or reach (a reach `finding` counts, so outside the worktree) falls after its trigger turn.
  - **Flagged only by non-protected refusals:** a cell whose transcript yields a `confinement.finding` with `reaches` 0 and `refusals` ≥ 1, where every `confinement_refused` entry (`entry_appended` with `entry.customType == "confinement_refused"`) has `entry.data.toolName` in `read`, `edit`, `write` and a string `entry.data.path` for which `confinement._reaches(path, cwd, confinement.protected(task_dir.parent, task_dir.name))` is `None`, with the terms admission uses (`attempt.py`, `rescore.py`) and `cwd` from the transcript's first event. A bash refusal never qualifies, since the extension refuses bash only when the command names a protected root (`confinement.ts` `namesRoot`); an entry without a string `path` does not qualify. Example: a `write` to `/tmp/test_guard.py`. These cells stay outside the denominator, and the count shows how much a non-leak refusal shrank it.
  - The two counts may overlap; each is listed per task with its cells.

**D5. Task kinds and thresholds at n = 6, read at the 32,000 / 48 line.** §2 picked budget-shaped tasks as "at least 2 of 4 ended `BUDGET_EXCEEDED` or `COMMAND_TIMEOUT`" at a 32k budget. At a 48k budget, codes miss cells that pass between 32k and 48k.
- (A) A task is budget-shaped when it has ≥ 3 admitted cells and at least half of them are not a pass at the line (`actual_32k` false), which is §2's proportion read at the line (census Ruling 3). Every other task is floor, in scope for harm. Keep §4–§5's thresholds as written: net ≥ 1, insufficient at more than 1 unmeasured, floor harm < 2. Add: fewer than 3 admitted cells is insufficient.
- (B) §2's code rule literally.
- (C) Name the kinds now from the census (depth-3 floor, others budget-shaped), which uses unconfirmed evidence.
- **Recommend A.**
- **Ruled 2026-10-03: A.** A task is budget-shaped when it has at least 3 admitted cells and at least half of them are not a pass at the 32,000 / 48 line; every other task is floor. The thresholds stay as written.

**D6. Scope.**
- (A) Five tasks decide: run-record-gate, docs-linter, preflight-quiet, depth-3 and cell-loop. speed-probe is reported outside the decision, as §2 treated the Engine column: it was dropped for a prompt ambiguity, and R0 §2 never claims against one.
- (B) All six.
- (C) The two cut medium tasks only.
- **Recommend A.** preflight-quiet stays its own row, never pooled ("authored and mixed", census README).
- **Ruled 2026-10-03: A.** Five tasks decide: run-record-gate, docs-linter, preflight-quiet, depth-3 and cell-loop. speed-probe is reported outside the decision.

**D7. What each verdict opens.** These are fixed now and are not re-argued after the read.
- **Ruled 2026-10-03: as written below** (its stale "EB0 runs after C3" text was struck before the ruling).

| verdict | condition (deciding reading) | opens | does not open |
|---|---|---|---|
| **go** | ≥ 2 budget-shaped, sufficient tasks with net ≥ 1; floor harm < 2; no floor task insufficient | The R0 sitting under census design §8: the claim row, the ceiling set, the budget from C3's self-stop distribution, and the win rule and power. The stipulated effect is C4's per-task net / admitted (R0 §2). Then **a finish-on-green Engine spec only** | any Engine build before §8.3 fixes the rule and its power |
| **verify** | exactly one qualifies, or 7.1's gap, or floor harm ≥ 2, or an insufficient floor task | The R0 sitting asks whether a one-task claim is worth a release. On 2026-09-15, power 0.26 at n = 12 was judged too small (run-2 README). If yes, size n first | Engine spec |
| **not-the-lever** | no budget-shaped task has net ≥ 1 | R0 §5 question 3 (is 9B at 48k the honest setting?), and another Engine-addressable class from C3's table (for example runaway's completion-gate trigger), each with its own offline estimate (R0 §1.4) | finish-on-green spec |

Under any verdict:
- EB2 remedies need offline estimates on EB0 cells~~, and EB0 runs in its own sitting after C3~~. Struck 2026-10-03: EB0 ran 2026-10-02 21:50 to 2026-10-03 00:27, before any C3 sitting; its cells and results exist (`worktree-engine-budget` `c805ab1`).
- The Engine's inner-Pi `SATYRN_CONFINEMENT_ROOT` fix lands before the first post-C4 Engine read.
- `derive-new-top-level-module` **stays parked**. This counterfactual scores a stop rule on Baseline cells and cannot name a derive remedy, and EB names EB1 as its only reopener. Spell out the contradiction with ROADMAP's "reopens at C4, only if the re-derived counterfactual names it": the condition cannot be met by this instrument.

**D8. Where the result goes.** Same contradiction as C3 D9 (ROADMAP, versus the hook and §6 "`docs/results/` stays launcher-only"). **Recommend:** an evidence README, and the maintainer writes `docs/results/<date>-c4-counterfactual.md`.
- **Ruled 2026-10-03: the same as C3 D9 as ruled (B).** An agent drafts the evidence README; the maintainer writes `docs/results/<date>-c4-counterfactual.md`.

**D9. How the ledger names a re-derived mark.**
- (A) **SUPERSEDED**: the confinement reading is what is built on, and the isolated reading stays evidence for the isolated condition. **KEPT** for marks not re-derived. No post-hoc "agrees or disagrees" judgment.
- (B) CONFIRMED or DISAGREES, judged after reading.
- **Recommend A.** Also recorded: C0 did not mark the 2026-09-15 counterfactual (runs 1 and 2, release-one cells, isolated), yet ROADMAP C4 re-derives it. The C4 entry names it as SUPERSEDED for building.
- **Ruled 2026-10-03: A.** SUPERSEDED / KEPT.

**D10. The R0 text the sitting resumes under.** `2026-09-15-release-two-r0-constraints.md` §4 still says "Two-uid isolation for every deciding record". The unisolated-harness design says it changes that line, but the file was never amended. Options: (A) annotate R0 §4 with a dated pointer to the confinement design before the R0 sitting; (B) leave it, and let the sitting read the two together. **Recommend A.** It is one line, and the maintainer records it.
- **Ruled 2026-10-03: A.** Annotate R0 §4.

## Global Constraints

- **The line:** 32,000 output tokens / 48 turns (`census_classify.TOKEN_LINE`, `TURN_LINE`).
- **Data:** the C3 census only: `records/<c1-date>-c1-*.json`, `evidence/<c3-date>-c3-census/<task>/cells.json`, and `~/satyrn-runs/<c1-date>-c1-<task>/baseline/summary.json` (and, for D4's beside counts, the same nights' transcripts). Nothing pools with the isolated census, the 2026-09-15 counterfactual, EB0 or any Engine cell. Per task, never summed.
- **One decision run.** A bug found afterwards is fixed and re-run only with both results recorded beside each other (the pre-registration header's clause).
- No Engine component is designed, planned or built before this verdict and the R0 sitting (R0 §1; AGENTS.md).
- The default tier uses no model, network or subprocess. Every refusal test has a success sibling. Read exit codes and never pipe a gate. Every new file gets a PROVENANCE row.
- `ROADMAP.md` is at 149 of its 150-line cap (`tools/lint_docs.py`), so edits append inside existing cells.
- Attended sittings are ≤ 60 min. An executing agent stops before Task 3.

## Review Focus

1. **The rule committed after a C3 tally was visible.** Check the commit order against C3's daylight freeze (D1) and C3 Task 7.
2. **A flagged or unmeasured cell entering a rescue or harm.**
3. **The deciding reading switched after the read.**
4. **Nets pooled across tasks**, or speed-probe counted in.
5. **"Go" read as "build"** rather than as "the R0 sitting and a spec".

---

### Task 1: The pre-registration (agent drafts; attended — the maintainer approves; before C3's daylight freeze, Task 3, D1)

**Files:** Create `docs/superpowers/specs/2026-10-03-c4-finishing-counterfactual-rederive.md` (≤ 200 lines; the spec cap is 400). Modify `PROVENANCE.md`.

- [ ] **Step 1:** Draft it with the same section numbers as the 2026-09-15 pre-registration:
  1. The question, unchanged.
  2. Scope: D6, D4 and the C3 records.
  3. Definitions: §3 unchanged.
  4. Counting: §4 and 7.4 for run 1; D3's run 2 with its amendment.
  5. The decision: D5's kinds, §5 with 7.1, and D7's table.
  6. Deliverables and the one run.
  7. Disclosure: the census page and C2 were read by the author, and the census found medium builds finishing-bound under isolation (UNCONFIRMED, C0).
- [ ] **Step 2 (attended — the maintainer):** Approve it in the sitting. Run `just gates; echo "exit $?"`, then commit it alone: `git commit -m "C4: pre-register the counterfactual on the C3 census"`.

### Task 2: `decide.py` and its tests (unattended; synthetic data only)

Amended 2026-10-03 (controller, after the maintainer approved the pre-registration): the two beside counts of pre-registration section 2 are computed here; the draft had no code for them.

**Files:** Create `evidence/<c4-date>-c4-counterfactual/decide.py` and `tests/test_c4_decide.py`. Modify `PROVENANCE.md`.

**Constraints kept:** tests use synthetic data built in the test file, never a census cell, `summary.json` or transcript. The script adds nothing per cell to the classifier's output: it never writes `cells.json`, and the beside counts are attempt lists per task in `decision.txt` and `table.md`. One decision run; the script refuses while `decision.txt` exists.

**The beside counts (pre-registration section 2), from one transcript per cell:**
- One parse: `cell_evidence._events(text)`, the parse `confinement.audit` and `confinement.finding` use, so event indices agree.
- Refusals: the `(index, entry.data)` of every `entry_appended` with `entry.customType == "confinement_refused"`, with `finding`'s predicate.
- Reaches: `confinement.audit(text, protected_=terms)`, keeping `Reach.index` where `not reach.in_worktree` (what `finding` counts).
- An event's turn: `budget.UsageCounter` fed `events[: index + 1]`, so the number of `turn_start` events at or before it. That is the count `own_green_turn` comes from (`counterfactual.py` `steps_of`).
- Flagged: `finding` is not `None` and not `admitted`. `cwd` comes from the transcript's first event, as `audit` reads it.
- Inputs in `main`, read-only:
  - the trigger turn is the `cells.json` row's `own_green_turn`, joined on `attempt`;
  - the transcript is `<runs-root>/<c1-date>-c1-<task>/baseline/<attempt_dir>/transcript.txt` for each `summary.json` evidence key whose block has `transcript: true` (`classify.py` reads the same file);
  - the terms are `confinement.protected(task_dir.parent, task_dir.name)` with `task_dir = manifest.resolve_task(task)`, which is what `rescore.py` uses.
- `beside` refuses (exit 2, nothing written) if a transcript's recomputed admission disagrees with `summary.json`'s `confinement_admitted`.
- `render` builds the verdict lines from rows and admission only. The beside lists are appended after the verdicts and never reach `tally` or `decide`.

- [ ] **Step 1: Tests first**, loading the script by path as `tests/test_census_classify.py` does:

```python
"""C4 decide: the pure rules, both directions. No model, network, or subprocess."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from satyrn_evals.confinement import Protected

_PATH = next((Path(__file__).resolve().parents[1] / "evidence").glob("*-c4-counterfactual/decide.py"))
_spec = importlib.util.spec_from_file_location("c4_decide", _PATH)
d = importlib.util.module_from_spec(_spec)
sys.modules["c4_decide"] = d
_spec.loader.exec_module(d)

def T(task, admitted=6, miss=4, rescues=0, harms=0, unmeasured=0):
    return d.Tally(task, admitted, miss, rescues, harms, unmeasured)

def row(attempt, change, reasons=(), actual=False, raised=None, green=None):
    return {"attempt": attempt, "actual_32k": actual, "raised": raised, "unmeasured": list(reasons),
            "own_green_turn": green, "run1": {"change": change}, "run2": {"change": change}}

def test_two_qualifying_budget_tasks_and_a_clean_floor_is_go():
    assert d.decide([T("a", rescues=1), T("b", rescues=2), T("f", miss=0)])[0] == "go"

def test_one_qualifying_task_is_verify():
    assert d.decide([T("a", rescues=1), T("b"), T("f", miss=0)])[0] == "verify"

def test_floor_harm_of_two_turns_go_into_verify():
    assert d.decide([T("a", rescues=1), T("b", rescues=1), T("f", miss=0, harms=2)])[0] == "verify"

def test_no_budget_task_with_a_net_rescue_is_not_the_lever():
    assert d.decide([T("a"), T("b", rescues=1, harms=1), T("f", miss=0)])[0] == "not-the-lever"

def test_an_insufficient_task_with_a_net_rescue_is_verify_by_7_1():
    assert d.decide([T("a", rescues=1, unmeasured=2), T("f", miss=0)])[0] == "verify"

def test_fewer_than_three_admitted_cells_is_insufficient_and_three_is_not():
    assert T("a", admitted=2, miss=2).insufficient and not T("a", admitted=3, miss=2).insufficient

def test_a_flagged_cell_is_never_counted_and_an_admitted_one_is():
    rows = [row("1", "rescue"), row("2", "rescue")]
    assert d.tally("a", rows, {"1": True, "2": False}, "run2").rescues == 1

def test_run2_withholds_on_fidelity_and_not_on_an_unverified_rescue():
    assert d.change(row("1", "rescue", ["fidelity: harness pass, replay fail"]), "run2") == "unmeasured"
    assert d.change(row("1", "rescue", ["unverified-rescue: bash at turns 3"]), "run2") == "rescue"
    assert d.change(row("1", "rescue", ["unverified-rescue: bash at turns 3"]), "run1") == "unmeasured"

# --- the beside counts (pre-registration section 2); synthetic transcripts only ---
TERMS = Protected(roots=("/corpus", "/corpus/selfhost-x"), names=("test_hidden.py",))
TURN = {"type": "turn_start"}

def call(tool, **args):
    return {"type": "tool_execution_start", "toolName": tool, "args": args}

def refused(**data):
    return {"type": "entry_appended", "entry": {"customType": "confinement_refused", "data": data}}

def tx(*events):
    return "\n".join(json.dumps(e) for e in ({"type": "session", "cwd": "/w"}, *events))

SCRATCH = refused(toolName="write", toolCallId="c", path="/tmp/test_guard.py")
LEAK = call("read", path="/corpus/selfhost-x/overlay/test_hidden.py")  # a reach finding counts
OWN = call("write", path="tests/test_hidden.py", content="")           # in-worktree: finding ignores it

def test_a_refusal_after_the_trigger_turn_is_flagged_after_trigger():
    assert d.flagged_after_trigger(tx(TURN, call("bash", command="pytest"), TURN, TURN, SCRATCH), TERMS, 1)

def test_a_counted_reach_after_the_trigger_turn_is_flagged_after_trigger():
    assert d.flagged_after_trigger(tx(TURN, TURN, LEAK), TERMS, 1)

def test_a_null_trigger_turn_is_never_flagged_after_trigger():
    assert not d.flagged_after_trigger(tx(TURN, TURN, TURN, SCRATCH), TERMS, None)

def test_the_earlier_flagging_event_at_or_before_the_trigger_turn_is_not_after_trigger():
    text = tx(TURN, LEAK, TURN, TURN, SCRATCH)  # reach at turn 1, refusal at turn 3
    assert not d.flagged_after_trigger(text, TERMS, 1) and not d.flagged_after_trigger(text, TERMS, 2)
    assert d.flagged_after_trigger(text, TERMS, 0)

def test_an_in_worktree_reach_is_not_the_first_flagging_event():
    assert d.flagged_after_trigger(tx(TURN, OWN, TURN, TURN, SCRATCH), TERMS, 2)

def test_a_scratch_write_refusal_alone_is_flagged_only_by_non_protected_refusals():
    assert d.only_non_protected_refusals(tx(TURN, SCRATCH, refused(toolName="read", path="/etc/hosts")), TERMS)

def test_a_reach_that_counts_disqualifies_the_non_protected_count():
    assert not d.only_non_protected_refusals(tx(TURN, SCRATCH, TURN, LEAK), TERMS)

def test_a_refusal_naming_a_protected_root_or_a_hidden_basename_outside_the_worktree_disqualifies():
    # The refusal entry alone (no start event), so the refusal rule decides, not a reach.
    root = refused(toolName="read", path="/corpus/selfhost-x/README.md")
    name = refused(toolName="write", path="/tmp/test_hidden.py")
    assert not d.only_non_protected_refusals(tx(TURN, SCRATCH, root), TERMS)
    assert not d.only_non_protected_refusals(tx(TURN, SCRATCH, name), TERMS)

def test_a_bash_refusal_or_a_refusal_without_a_string_path_disqualifies():
    bash = refused(toolName="bash", command="ls /corpus", root="/corpus")
    assert not d.only_non_protected_refusals(tx(TURN, SCRATCH, bash), TERMS)
    assert not d.only_non_protected_refusals(tx(TURN, refused(toolName="write")), TERMS)

def test_an_admitted_cell_is_in_neither_count_and_an_own_basename_reach_alone_does_not_flag():
    for text in (tx(TURN, call("read", path="src/a.py")), tx(TURN, OWN)):
        assert d.finding(text, protected_=TERMS).admitted
        assert not d.flagged_after_trigger(text, TERMS, 0) and not d.only_non_protected_refusals(text, TERMS)

def test_beside_lists_each_count_by_attempt():
    rows = [row("1", "none", green=1), row("2", "none", green=1), row("3", "none", green=1)]
    texts = {"1": tx(TURN, TURN, SCRATCH), "2": tx(TURN, LEAK), "3": tx(TURN, OWN)}
    assert d.beside(rows, texts, {"1": False, "2": False, "3": True}, TERMS) == (["1"], ["1"])

def test_beside_refuses_when_the_transcript_and_summary_disagree_on_admission():
    with pytest.raises(ValueError, match="disagrees"):
        d.beside([row("1", "none", green=1)], {"1": tx(TURN, SCRATCH)}, {"1": True}, TERMS)

def test_the_beside_counts_never_change_the_verdict():
    per = {t: ([row("1", "rescue", green=1), row("2", "harm", actual=True, green=2)], {"1": True, "2": True})
           for t in d.DECIDING + d.OUTSIDE}
    bare, _ = d.render(per, {})
    full, table = d.render(per, {t: (["3"], ["3", "4"]) for t in per})
    picked = [[line for line in lines if line.startswith(d.READINGS)] for lines in (bare, full)]
    assert picked[0] == picked[1] and len(picked[1]) == 2
    assert any("non-protected refusals only 2 ['3', '4']" in line for line in full)
    assert "| 3, 4 |" in "\n".join(table)
```

- [ ] **Step 2:** Run `uv run pytest -q tests/test_c4_decide.py`. Expect a collection ERROR: no script.
- [ ] **Step 3: Write `decide.py`:**

```python
#!/usr/bin/env python3
"""C4: the finishing counterfactual's verdict on the C3 census.

Pre-registration: docs/superpowers/specs/2026-10-03-c4-finishing-counterfactual-rederive.md.
Reads classify.py's per-cell rows, each night's summary.json admission, and (for the two
beside counts of section 2, which never decide) each cell's transcript, read-only; one run.
"""
from __future__ import annotations
import argparse, json, math, subprocess, sys
from dataclasses import dataclass
from pathlib import Path
from satyrn_evals.budget import UsageCounter
from satyrn_evals.cell_evidence import _events
from satyrn_evals.confinement import Protected, _reaches, audit, finding, protected
from satyrn_evals.manifest import resolve_task

HERE = Path(__file__).resolve().parent
EVALS = HERE.parents[1]
DECIDING = ("selfhost-run-record-gate", "selfhost-docs-linter", "selfhost-preflight-quiet",
            "agentclinic-repair-depth-3", "selfhost-cell-loop")  # D6
OUTSIDE = ("selfhost-speed-probe",)                              # D6: reported only
READINGS = ("run2", "run1")                                      # D3: first decides
FILE_TOOLS = ("read", "edit", "write")


@dataclass(frozen=True, slots=True)
class Tally:
    task: str
    admitted: int
    not_pass_at_line: int
    rescues: int
    harms: int
    unmeasured: int

    @property
    def net(self) -> int:
        return self.rescues - self.harms

    @property
    def budget_shaped(self) -> bool:  # D5
        return self.admitted >= 3 and self.not_pass_at_line >= math.ceil(self.admitted / 2)

    @property
    def insufficient(self) -> bool:  # section 4, plus D5's admitted floor
        return self.admitted < 3 or self.unmeasured > 1


def change(row: dict, reading: str) -> str:
    """D3: both readings withhold on a fidelity failure or a raise; run 1 on any reason."""
    reasons = row["unmeasured"] or []
    if row["raised"] or any(r.startswith(("fidelity:", "raised:")) for r in reasons):
        return "unmeasured"
    return "unmeasured" if reading == "run1" and reasons else row[reading]["change"]


def tally(task: str, rows: list[dict], admitted: dict[str, bool], reading: str) -> Tally:
    mine = [r for r in rows if admitted.get(r["attempt"]) is True]  # D4
    changes = [change(r, reading) for r in mine]
    return Tally(task, len(mine), sum(1 for r in mine if not r["actual_32k"]),
                 changes.count("rescue"), changes.count("harm"), changes.count("unmeasured"))


def decide(tallies: list[Tally]) -> tuple[str, str]:
    """2026-09-15 pre-registration section 5 with amendment 7.1; kinds from D5."""
    budget = [t for t in tallies if t.budget_shaped]
    floor = [t for t in tallies if not t.budget_shaped]
    qualifying = [t.task for t in budget if not t.insufficient and t.net >= 1]
    harm = sum(t.harms for t in floor)
    thin = [t.task for t in floor if t.insufficient]
    detail = f"budget-shaped {[t.task for t in budget]}; qualifying {qualifying}; floor harm {harm}; insufficient floor {thin}"
    if len(qualifying) >= 2 and harm < 2 and not thin:
        return "go", detail
    if qualifying:
        return "verify", detail
    if all(t.net < 1 for t in budget):
        return "not-the-lever", detail
    return "verify", detail + "; a budget-shaped task has net >= 1 but is insufficient (7.1)"


# --- section 2's beside counts: reported per task, never an input to tally or decide ---

def _refusals(events: list[dict]) -> list[tuple[int, dict]]:
    """(event index, entry.data) of each confinement_refused entry, by finding()'s predicate."""
    return [(i, e["entry"].get("data") if isinstance(e["entry"].get("data"), dict) else {})
            for i, e in enumerate(events)
            if e.get("type") == "entry_appended" and isinstance(e.get("entry"), dict)
            and e["entry"].get("customType") == "confinement_refused"]


def _turn_at(events: list[dict], index: int) -> int:
    """The number of turn_start events at or before ``index`` (budget.UsageCounter's count)."""
    usage = UsageCounter()
    for event in events[: index + 1]:
        usage.feed_event(event)
    return usage.turns


def flagged_after_trigger(text: str, terms: Protected, own_green_turn: int | None) -> bool:
    """Flagged, a trigger turn, and the earlier of the first refusal and the first counted
    reach (in-worktree reaches ignored, as finding() ignores them) falls after it."""
    cell = finding(text, protected_=terms)
    if cell is None or cell.admitted or own_green_turn is None:
        return False
    events = _events(text)
    first = min([i for i, _ in _refusals(events)]
                + [r.index for r in audit(text, protected_=terms) if not r.in_worktree])
    return _turn_at(events, first) > own_green_turn


def only_non_protected_refusals(text: str, terms: Protected) -> bool:
    """Reaches 0, refusals >= 1, and every refusal a file tool with a string path that
    reaches no protected term from the first event's cwd. A bash refusal never qualifies."""
    cell = finding(text, protected_=terms)
    if cell is None or cell.reaches != 0 or cell.refusals < 1:
        return False
    events = _events(text)
    cwd = events[0].get("cwd") if isinstance(events[0].get("cwd"), str) else None
    return all(data.get("toolName") in FILE_TOOLS and isinstance(data.get("path"), str)
               and _reaches(data["path"], cwd, terms) is None for _, data in _refusals(events))


def beside(rows: list[dict], texts: dict[str, str], admitted: dict[str, bool], terms: Protected) -> tuple[list[str], list[str]]:
    """One task's two counts as attempt lists. Refuses when a transcript's admission
    disagrees with summary.json's confinement_admitted."""
    green = {r["attempt"]: r["own_green_turn"] for r in rows}
    after, scratch = [], []
    for attempt, text in sorted(texts.items()):
        cell = finding(text, protected_=terms)
        if (cell is not None and cell.admitted) is not (admitted.get(attempt) is True):
            raise ValueError(f"attempt {attempt}: transcript admission disagrees with summary.json")
        if flagged_after_trigger(text, terms, green.get(attempt)):
            after.append(attempt)
        if only_non_protected_refusals(text, terms):
            scratch.append(attempt)
    return after, scratch


def render(per_task: dict[str, tuple[list[dict], dict[str, bool]]],
           side: dict[str, tuple[list[str], list[str]]]) -> tuple[list[str], list[str]]:
    """decision.txt and table.md lines. Verdicts read rows and admission only; ``side`` is appended."""
    lines, table = [], ["| reading | task | admitted | not-pass@line | kind | rescues | harms | net | unmeasured | insufficient |", "|" + "---|" * 10]
    for reading in READINGS:
        tallies = []
        for task in DECIDING + OUTSIDE:
            rows, admitted = per_task[task]
            t = tally(task, rows, admitted, reading)
            tallies.append(t)
            kind = "outside" if task in OUTSIDE else ("budget-shaped" if t.budget_shaped else "floor")
            table.append(f"| {reading} | {task} | {t.admitted} | {t.not_pass_at_line} | {kind} | {t.rescues} | {t.harms} | {t.net} | {t.unmeasured} | {t.insufficient} |")
        verdict, detail = decide([t for t in tallies if t.task in DECIDING])
        lines.append(f"{reading}{' (deciding)' if reading == READINGS[0] else ' (beside)'}: {verdict}\n  {detail}")
    lines.append("beside counts (pre-registration section 2; never decide):")
    table += ["", "| task | flagged after trigger | cells | flagged only by non-protected refusals | cells |", "|---|---|---|---|---|"]
    for task, (after, scratch) in side.items():
        lines.append(f"  {task}: flagged after trigger {len(after)} {after}; non-protected refusals only {len(scratch)} {scratch}")
        table.append(f"| {task} | {len(after)} | {', '.join(after) or '-'} | {len(scratch)} | {', '.join(scratch) or '-'} |")
    return lines, table


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="decide.py")
    p.add_argument("--census", type=Path, required=True, help="evidence/<c3-date>-c3-census")
    p.add_argument("--c1-date", required=True)
    p.add_argument("--runs-root", type=Path, default=Path.home() / "satyrn-runs")
    a = p.parse_args(argv)
    if (HERE / "decision.txt").exists():
        print("decide: decision.txt exists; the pre-registration allows one run", file=sys.stderr)
        return 2
    git = lambda *x: subprocess.run(["git", *x], cwd=EVALS, capture_output=True, text=True).stdout.strip()
    stamp = f"evals {git('rev-parse', 'HEAD')} dirty={bool(git('status', '--porcelain', '--', 'src', 'evidence'))} argv={argv}"
    per_task, side = {}, {}
    for task in DECIDING + OUTSIDE:
        night = a.runs_root / f"{a.c1_date}-c1-{task}" / "baseline"
        rows = json.loads((a.census / task / "cells.json").read_text())["cells"]
        blocks = json.loads((night / "summary.json").read_text())["evidence"] or {}
        admitted = {name.rsplit("-", 1)[-1]: block.get("confinement_admitted") is True for name, block in blocks.items()}
        per_task[task] = (rows, admitted)
        task_dir = resolve_task(task)
        texts = {name.rsplit("-", 1)[-1]: (night / name / "transcript.txt").read_text()
                 for name, block in blocks.items() if block.get("transcript") is True}
        try:
            side[task] = beside(rows, texts, admitted, protected(task_dir.parent, task_dir.name))
        except ValueError as exc:
            print(f"decide: {task}: {exc}; nothing written", file=sys.stderr)
            return 2
    lines, table = render(per_task, side)
    (HERE / "table.md").write_text(f"<!-- {stamp} -->\n\n" + "\n".join(table) + "\n")
    (HERE / "decision.txt").write_text(f"# {stamp}\n" + "\n".join(lines) + "\n")
    print((HERE / "decision.txt").read_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 4:** Run `uv run pytest -q tests/test_c4_decide.py`. Expect PASS (21). Run `just gates; echo "exit $?"` and expect `exit 0`. Add PROVENANCE rows and commit both files.

**An executing agent stops here.**

### Task 3: The one decision run (attended — the maintainer)

- [ ] **Step 1:** Check the order. `git log --format='%h %ad %s' --date=iso -- docs/superpowers/specs/*-c4-* evidence/<c3-date>-c3-census/ evidence/2026-09-15-release-one-decision-ledger.md` must show the pre-registration commit before the first C3 classifier output, and before the ledger line "C3 frozen <sha>" (D1).
- [ ] **Step 2:** Run `uv run --project . python evidence/<c4-date>-c4-counterfactual/decide.py --census evidence/<c3-date>-c3-census --c1-date <c1-date>; echo "exit $?"`. Expect `exit 0`. A stamp with `dirty=True` is a review failure.
- [ ] **Step 3:** Add PROVENANCE rows. Commit `decision.txt` and `table.md` as "C4: the counterfactual's verdict on the C3 census (<verdict>)".

### Task 4: The result page (agent drafts; attended — the maintainer signs)

- [ ] **Step 1:** Write `evidence/<c4-date>-c4-counterfactual/README.md`, ≤ 120 lines:
  - the verdict under both readings, and any disagreement stated;
  - the per-task table;
  - D4's two beside counts: flagged after trigger, and flagged only by non-protected refusals (pre-registration §2);
  - every unmeasured cell with its reason;
  - D7's row for the verdict;
  - the disclosure (Task 1 §7);
  - the replay limits (classify.py std replay; 7.4);
  - the power, if `go` or `verify`: one-sided Fisher at the R0 sitting's candidate n, against Baseline's C3 rate, labelled as an input to §8.3, not a rule;
  - a fenced recompute (Task 3 Step 2's command against a copy without `decision.txt`).
- [ ] **Step 2 (attended — the maintainer):** Sign it. Write `docs/results/<date>-c4-counterfactual.md` (≤ 120 lines, fenced recompute; D8, ruled as C3 D9). Run gates and commit.

### Task 5: Ledger and roadmap (attended — the maintainer)

- [ ] **Step 1:** Append the ledger entry:

```markdown
## <date> — C4: the finishing counterfactual re-derived on the C3 census (<verdict>, decision <sha>)
- Pre-registration <spec path> at <sha>; decide.py <sha>; evidence/<c4-date>-c4-counterfactual/. Deciding reading run 2 (std replay, fidelity-withheld); run 1 beside: <verdict>.
- SUPERSEDED for building: the census's counterfactual columns (nights 1-3, C0) and evidence/2026-09-15-finishing-counterfactual runs 1 and 2 (not marked at C0; release-one cells under isolation).
- Census nights 1-3 and class columns: SUPERSEDED at entry C3 (no change here).
- KEPT UNCONFIRMED (35c298d): docs/numbers.md (Engine 16/24 vs Baseline 2/24), route proofs 2026-09-17 and 2026-09-19, the red-stop replay. They need Engine cells under confinement after the inner-Pi SATYRN_CONFINEMENT_ROOT fix; C1-C4 re-derive none of them.
- Permanent: the sandbox Baseline set.
- Opens: <D7 row>. derive-new-top-level-module stays parked (this instrument cannot name it).
```

- [ ] **Step 2:** Append ` done <date>: ledger entry "C4", <verdict>; next: R0 sitting (census design §8)` to the ROADMAP C4 row, inside its cell. Run `just gates; echo "exit $?"` and commit.

### Task 6: Resume R0's order (attended — the maintainer)

- [ ] Schedule the R0 sitting (≤ 60 min) with three inputs: C3's signed table, C4's verdict, and census design §8 items 1–4 as the agenda.
- [ ] Hold Engine spec work until that sitting fixes §8.3.
- [ ] The confinement fixes follow the engine-side plan, approved on its own branch, whose re-pin waits for C4's verdict. EB2 follows EB's own (unapproved) order, never before this sitting's rule. EB0 has already run (2026-10-02 21:50 to 2026-10-03 00:27, development cells; struck from this step 2026-10-03).

## Done when (ROADMAP C4)

The counterfactual's verdict on the new census, before any Engine build.
