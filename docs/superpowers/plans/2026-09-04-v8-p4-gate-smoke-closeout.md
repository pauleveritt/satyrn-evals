# V8 Plan 4 of 4 — Qualification gate, contamination pairs, smoke, close-out (slices 4-6)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove, per bundled task and by fixture name, the offline three-row gate (base fails per its recorded set; known-good passes 13/13; known-broken fails) plus the contamination pairs in both directions — then run the one uncounted V5d smoke on `plausible-wrong-fix`, and record the V8 close-out.

**Architecture:** Plan 4 of 4 for V8 (`docs/superpowers/specs/2026-09-04-v8-agentclinic-evals-design.md` §6, §7, §13). The three-row gate has two mechanisms because grading is patch-based: the **fixture rows** (known-good, known-broken) grade through the real CLI (exercising P2's materialized env and P3's subtraction end to end); the **base row** grades the raw broken tree with the pinned suite directly (the spec §14 recomputation, in-tree), because an empty patch is a refusal, not the base. Both are integration tier. The smoke is not a test — the V5d practice run manually with durable evidence. Close-out writes the `docs/sdd.md` verification record and moves V8 to Prior work.

**Tech Stack:** Python 3.14, `pytest`, `uv`, stock `satyrn-engine` attempt for the smoke.

**Spec:** `docs/superpowers/specs/2026-09-04-v8-agentclinic-evals-design.md` (§2 failing sets, §5, §6, §7, §13, §14).

## Global Constraints

- Integration tier only for real grades: files in `tests/integration/`; CI runs the default tier.
- A refusal test has a sibling success test, always (each gate row asserts a failing row and a passing row).
- Verdicts come from hook records, never stdout or exit codes.
- Default tier unchanged: no model/network/subprocess; tripwire intact.
- 100% coverage gate and `ruff check .` / `just lint-docs` green at close-out.
- The gate is recomputable; its command is recorded here and in `docs/sdd.md`.
- The smoke is uncounted, durable, uniquely named; `NO_PATCH`/`COMMAND_TIMEOUT` pass only on positive evidence the model started.

### Task 1: The three-row gate, parametrized over all six tasks (integration)

**Files:**
- Create: `tests/integration/test_agentclinic_gate.py`

**Interfaces:**
- Consumes: the six bundled tasks (P1), materialized-env grading (P2), subtraction (P3).
- Produces: per-task rows named by fixture; the gate command (Task 2) and the close-out record (Task 4) cite this file's expectations.

- [ ] **Step 1: Write the integration tests**

```python
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from satyrn_evals.manifest import DEFAULT_TASKS_ROOT

pytestmark = pytest.mark.integration

STATES = ["depth-2", "depth-3", "framing-2", "framing-2-edit",
          "misleading-locus", "plausible-wrong-fix"]
ASSERTION_STATES = ["misleading-locus", "plausible-wrong-fix", "depth-2", "depth-3"]
COLLECTION_ABORT = ["framing-2", "framing-2-edit"]

# spec §2, re-derived on the vendored bases in slice 1 (spec §14 command).
EXPECTED_BASE_FAILURES = {
    "misleading-locus": ["test_posted_complaint_appears_on_complaints_board"],
    "plausible-wrong-fix": ["test_post_complaint_redirects_to_complaints_board"],
    "depth-2": [
        "test_home_html_element_declares_english_language",
        "test_complaints_board_preserves_the_shared_layout",
        "test_post_complaint_redirects_to_complaints_board",
    ],
    "depth-3": [
        "test_home_html_element_declares_english_language",
        "test_complaints_board_preserves_the_shared_layout",
        "test_complaint_model_contract_is_preserved",
        "test_post_complaint_redirects_to_complaints_board",
    ],
}
PINS = ["--with", "fastapi[standard]==0.115.10", "--with", "turbohtml==1.5.0",
        "--with", "httpx", "--with", "pytest==8.3.4"]


def _task(state: str) -> Path:
    return DEFAULT_TASKS_ROOT / f"agentclinic-repair-{state}"


def _grade(task_dir: Path, patch_path: Path, tmp_path: Path) -> dict:
    receipt_path = tmp_path / "receipt.json"
    subprocess.run(
        ["satyrn-evals", "grade", task_dir.name, str(patch_path),
         "--receipt", str(receipt_path), "--tasks-root", str(task_dir.parent)],
        check=True, capture_output=True)
    return json.loads(receipt_path.read_text())


def _run_base_suite(state: str, tmp_path: Path) -> tuple[int, str]:
    """Raw broken tree + overlay, pinned suite: the base row's grade."""
    d = tmp_path / state
    shutil.copytree(_task(state) / "base", d)
    shutil.copy(_task(state) / "overlay" / "test_acceptance.py", d / "test_acceptance.py")
    proc = subprocess.run(
        ["uv", "run", "--no-project", "--quiet", *PINS,
         "python", "-m", "pytest", "-q", "test_acceptance.py"],
        cwd=d, capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


@pytest.mark.parametrize("state", ASSERTION_STATES)
def test_base_row_reproduces_recorded_failing_set(state: str, tmp_path: Path) -> None:
    rc, out = _run_base_suite(state, tmp_path)
    assert rc == 1, state
    for tid in EXPECTED_BASE_FAILURES[state]:
        assert f"test_acceptance.py::{tid}" in out, (state, tid)


@pytest.mark.parametrize("state", COLLECTION_ABORT)
def test_base_row_is_collection_abort_not_unavailable(state: str, tmp_path: Path) -> None:
    rc, out = _run_base_suite(state, tmp_path)
    assert rc == 2 or "error during collection" in out, state


@pytest.mark.parametrize("state", STATES)
def test_known_good_passes_13_of_13(state: str, tmp_path: Path) -> None:
    task_dir = _task(state)
    receipt = _grade(task_dir, task_dir / "fixtures" / "known-good.patch", tmp_path)
    assert receipt["verdict"] == "pass", state
    assert receipt["evidence"]["counts"]["passed"] == 13, state
    assert receipt["evidence"]["counts"]["failed"] == 0, state


@pytest.mark.parametrize("state", STATES)
def test_known_broken_fails(state: str, tmp_path: Path) -> None:
    task_dir = _task(state)
    receipt = _grade(task_dir, task_dir / "fixtures" / "known-broken.patch", tmp_path)
    assert receipt["verdict"] == "fail", state
    failing = [tid for tid, out in receipt["evidence"]["outcomes"].items()
               if out != "passed"]
    assert failing, state  # the receipt names the failing ids
```

- [ ] **Step 2: Run to verify the fixture rows fail before the machinery lands**

Run: `uv run pytest tests/integration/test_agentclinic_gate.py -q`
Expected pre-P2/P3: known-good rows fail (no materialized env / contamination semantics pending). After P1-P3 are merged and the gate is green, re-run: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_agentclinic_gate.py
git commit -m "test: agentclinic three-row gate (base, known-good, known-broken)"
```

### Task 2: The recomputable gate command + contamination pairs

**Files:**
- Create: `tools/agentclinic_gate.sh`
- Modify: `tests/integration/test_agentclinic_gate.py` (contamination pairs)

- [ ] **Step 1: Write the gate command**

```bash
#!/usr/bin/env bash
# V8 qualification gate (spec §6): three rows per task, named by fixture.
# Integration tier (uv, network on first sync). Exits nonzero on surprise.
set -euo pipefail
for s in depth-2 depth-3 framing-2 framing-2-edit misleading-locus plausible-wrong-fix; do
  t="src/satyrn_evals/tasks/agentclinic-repair-$s"
  echo "== $s =="
  d=$(mktemp -d)
  cp -r "$t/base/." "$d/"; cp "$t/overlay/test_acceptance.py" "$d/"
  echo -n "  base: "
  (cd "$d" && uv run --no-project --quiet \
    --with "fastapi[standard]==0.115.10" --with "turbohtml==1.5.0" --with httpx \
    --with "pytest==8.3.4" python -m pytest -q test_acceptance.py 2>&1 | tail -1)
  rm -rf "$d"
  for f in known-good known-broken; do
    r=$(mktemp -d)
    satyrn-evals grade "$t" "$t/fixtures/$f.patch" \
      --receipt "$r/receipt.json" --tasks-root src/satyrn_evals/tasks
    echo -n "  $f: "
    python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["verdict"])' "$r/receipt.json"
    rm -rf "$r"
  done
done
```

- [ ] **Step 2: Run the gate and confirm it matches spec §2/§6**

Run: `bash tools/agentclinic_gate.sh`
Expected: base rows print the §2 signature (1 failed/12 passed for `misleading-locus` and `plausible-wrong-fix`; 3 failed and 4 failed for `depth-2`/`depth-3`; a collection error for `framing-2`/`framing-2-edit`); every known-good prints `pass`; every known-broken prints `fail`. Any deviation stops the phase — the smoke does not run on a failing gate.

- [ ] **Step 3: Add the contamination pairs, both directions, per task**

Append to `tests/integration/test_agentclinic_gate.py`:

```python
@pytest.mark.parametrize("state", STATES)
def test_contamination_pairs_fire_and_stay_silent(state: str, tmp_path: Path) -> None:
    task_dir = _task(state)
    overlay_text = (task_dir / "overlay" / "test_acceptance.py").read_text()
    lines = [ln for ln in overlay_text.splitlines() if ln.strip()][:5]
    leak_body = "\n".join(lines) + "\n"
    leak = tmp_path / "leak.patch"
    leak.write_text(
        "--- a/app.py\n+++ b/app.py\n@@ -1,1 +1,%d @@\n" % len(lines)
        + "".join(f"+{ln}\n" for ln in lines)
    )
    firing = _grade(task_dir, leak, tmp_path)
    check = firing["contamination"]["checks"][0]
    assert check["check"] == "grader_content_in_patch", state
    assert check["outcome"] == "flagged", state  # overlay-only block, not in base

    good = _grade(task_dir, task_dir / "fixtures" / "known-good.patch", tmp_path)
    good_check = good["contamination"]["checks"][0]
    assert good_check["outcome"] == "clean", state  # known-good stays silent
```

Run: `uv run pytest tests/integration/test_agentclinic_gate.py -q`
Expected: PASS — the 5-line overlay block is not in any `base/`, so it flags; after P3 the only subtracted needles are base-visible windows, and the known-good patch never contains them.

- [ ] **Step 4: Commit**

```bash
git add tools/agentclinic_gate.sh tests/integration/test_agentclinic_gate.py
git commit -m "test: agentclinic gate command and per-task contamination pairs"
```

### Task 3: The smoke (uncounted, V5d practice) — not a test

**Files:** durable evidence directory only; no committed code.

**Prerequisite:** every gate row green across all six tasks (Task 2).

- [ ] **Step 1: Run one real-model attempt on `plausible-wrong-fix` through the stock engine**

Follow the V6 smoke record's invocation shape (same local model rule: `omlx/gemma-4-12B-it-MLX-8bit`, no shim, durable uniquely-named evidence under `~/projects/satyrn-v8-scratch/`). The attempt command is the product seam — the stock `satyrn-engine` attempt against the base project; consult the V4/V5a records for the exact engine invocation already proven on this machine, and record the exact command in the smoke evidence.

- [ ] **Step 2: Apply the V5d checklist to the retained evidence**

- The attempt record is read always; the receipt only when grading ran.
- `NO_PATCH`/`COMMAND_TIMEOUT` pass ONLY with positive evidence the model started (the transcript shows the model acting), else the smoke fails.
- Evidence is durable and uniquely named (timestamped dir + record).
- Uncounted: no admission, difficulty, or quality claim. The verdict may be pass or fail; the smoke proves the qualified path (dependency-bearing hidden-oracle single-shot attempt through the stock engine) works end to end.
- An engine defect surfaced by the smoke is recorded in a research doc, not fixed in V8 (engine changes excluded).

- [ ] **Step 3: Write the smoke record**

Create `docs/superpowers/research/2026-09-04-v8-agentclinic-smoke.md`: the V5d checklist outcomes, the five smoke assertions restated for this path (model started; attempt recorded; patch+transcript preserved; offline grade ran when eligible; teardown clean), each evidenced from retained artifacts, plus any engine finding.

### Task 4: Close-out records

**Files:**
- Modify: `docs/sdd.md` (V8 verification record), `ROADMAP.md` (V8 row → complete, Prior work)

- [ ] **Step 1: Write the V8 verification record in `docs/sdd.md`**, following the V4/V6/V7 pattern:

```text
## V8 verification record

V8's default tier stays model-, network-, and subprocess-free. The six
agentclinic tasks' qualification rows, contamination pairs, and
materialized-env grades are integration tier (uv + network on first sync).

.venv/bin/pytest -q
<default-tier counts>

uv run pytest tests/integration/test_agentclinic_gate.py -m integration -q
<gate counts: 6 known-good pass 13/13, 6 known-broken fail, base rows per
spec §2, contamination pairs both directions>

uv run pytest -m '' --cov=src/satyrn_evals --cov-branch --cov-fail-under=100
<coverage gate: 100%>

Resolved-version attestation: the plausible-wrong-fix known-good receipt
carries `resolved_versions` naming `fastapi==0.115.10`; stdlib receipts
carry no such key.

Smoke: <durable evidence dir + V5d checklist outcomes>.
```

The statement count is recomputed by the gate command; 100% is the invariant. Fill the counts from actual runs whose full output was read (the V6 tail-of-output correction applies — never assert a number from a truncated tail).

- [ ] **Step 2: Move V8 to Prior work on `ROADMAP.md`**

Status cell → **complete** with a short citation of the spec and verification record; a Prior-work bullet summarizes the phase (six bundled `agentclinic-repair-*` tasks, two production changes — materialized-env grading with `resolved_versions`, contamination base-window subtraction — the offline gate, and the smoke), citing `BACKLOG.md`'s probe entry as the reopen path for measurement. Respect the Status-cell cap; keep the row's Excludes intact.

- [ ] **Step 3: Final gates**

Run: `uv run pytest -q && uv run pytest -m '' --cov=src/satyrn_evals --cov-branch --cov-fail-under=100 && ruff check . && just lint-docs`
Expected: all green; `just lint-docs` within caps.

- [ ] **Step 4: Commit**

```bash
git add docs/sdd.md ROADMAP.md
git commit -m "docs: V8 verification record and close-out"
```

### Task 5: Slice-4..6 self-review

- [ ] **Step 1: Spec cross-check.** Spec §6 gate rows (Task 1-2), §5 contamination pairs (Task 2 Step 3), §7 smoke on `plausible-wrong-fix` via the stock engine (Task 3), §13 record shape (Task 4) each have a home; the base-row mechanism is decided (raw-tree pinned run), so no placeholder remains. The probe (C) is not opened: `BACKLOG.md` carries its reopen condition.
- [ ] **Step 2: Read the full gate output before recording numbers** (the V6 tail-of-output correction applies to this close-out).
