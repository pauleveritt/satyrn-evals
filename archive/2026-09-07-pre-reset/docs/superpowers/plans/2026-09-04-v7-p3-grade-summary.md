> **Archived pre-reset record (2026-09-07).**
>
> Original claims, decisions, and instructions may be superseded. This file is evidence, not current guidance.
> For current guidance, read root AGENTS.md, BRIEF.md, and ROADMAP.md. Retrieve one named record when it bears on a concrete question; do not preload this archive.

# V7 P3 — Grade annotation and per-cell summary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `grade` auto-overlays hidden tasks and annotates receipts with contamination findings; `run`'s summary names its exact cell set and reports a contamination tally beside verdict counts, never altering a denominator.

**Architecture:** `grade()` loads the overlay itself when the manifest declares hidden and no explicit overlay was passed (the session grader keeps passing its own), runs `scan_patch`, and writes an additive optional `contamination` key on the receipt — omitted entirely for visible tasks so their receipt shape is byte-compatible. `run` names cells by directory delta, reads each cell's receipt, and `compute_summary` moves to cell inputs with `oracle_visibility` explicit. Ordinary-attempt records are NOT schema-changed.

**Tech:** Python ≥3.14, pytest, no new dependencies, no subprocess in the default tier.

**Spec:** `docs/superpowers/specs/2026-09-04-v7-task-visibility-leak-detection-design.md` (§6, §7, §9 govern this plan).

## Global Constraints

- Detection never changes a verdict or an exit code; a flagged attempt stays counted in its verdict bucket.
- `unmeasured` never folds into `clean` and is never reported as zero.
- Loaders tolerate the key's absence — stored artifacts must replay.
- Every refusal test has a success sibling; house style: `type` aliases, `match`/`case`, `:=`, full annotations.
- Verify with `.venv/bin/pytest -q` and `ruff check .` at every task end.

---

### Task 1: Receipt carries optional contamination; grade auto-overlays hidden tasks

**Files:**
- Modify: `src/satyrn_evals/receipt.py`, `src/satyrn_evals/grade.py`
- Test: `tests/test_receipt.py`, `tests/test_grade.py` (create if absent — check `ls tests/ | grep grade` first; the default-tier grade tests may live in `tests/test_cli.py`; put unit tests beside the module: create `tests/test_grade.py`)

**Interfaces:**
- Consumes: `load_overlay` (P1 state), `scan_patch`/`overall` from `contamination.py` (P2).
- Produces: `Receipt.contamination: dict | None = None`; `write_receipt` omits the key when `None`; `grade(task_dir, patch_path, receipt_path, *, overlay=None, ...)` — when `overlay is None` and the manifest is hidden, grade loads the overlay itself, detects, and annotates. The receipt dict shape: `{"visibility": "hidden", "checks": [{"check": ..., "outcome": ..., "evidence": [{"kind", "overlay_path", "in_path", "line"}, ...]}, ...]}`.

- [ ] **Step 1: Write the failing tests**

In `tests/test_receipt.py`:

```python
def test_visible_receipt_has_no_contamination_key(tmp_path):
    receipt = Receipt("t", "d", Verdict.PASS, "", None)
    path = tmp_path / "receipt.json"
    write_receipt(path, receipt)
    assert "contamination" not in json.loads(path.read_text())


def test_hidden_receipt_round_trips_contamination(tmp_path):
    finding = {"visibility": "hidden", "checks": [
        {"check": "grader_content_in_patch", "outcome": "clean", "evidence": []}
    ]}
    receipt = Receipt("t", "d", Verdict.PASS, "", None, contamination=finding)
    path = tmp_path / "receipt.json"
    write_receipt(path, receipt)
    assert json.loads(path.read_text())["contamination"] == finding
```

In `tests/test_grade.py` (new file; a hidden task fixture dir with overlay, patched via a clean patch that applies to its base):

```python
def test_hidden_task_receipt_annotated(tmp_hidden_task, clean_patch):
    receipt = grade(tmp_hidden_task, clean_patch, tmp_hidden_task / "receipt.json")
    data = json.loads((tmp_hidden_task / "receipt.json").read_text())
    assert data["contamination"]["visibility"] == "hidden"
    checks = {c["check"]: c["outcome"] for c in data["contamination"]["checks"]}
    assert checks == {"grader_content_in_patch": "clean"}


def test_visible_task_receipt_unannotated(tmp_visible_task, clean_patch):
    grade(tmp_visible_task, clean_patch, tmp_visible_task / "receipt.json")
    data = json.loads((tmp_visible_task / "receipt.json").read_text())
    assert "contamination" not in data


def test_contaminated_patch_flags_but_verdict_unchanged(tmp_hidden_task, contaminated_patch):
    receipt = grade(tmp_hidden_task, contaminated_patch, tmp_hidden_task / "receipt.json")
    data = json.loads((tmp_hidden_task / "receipt.json").read_text())
    checks = {c["check"]: c["outcome"] for c in data["contamination"]["checks"]}
    assert checks["grader_content_in_patch"] == "flagged"
    # detection never reclassifies: the verdict is whatever the oracle said
    assert receipt.verdict in (Verdict.PASS, Verdict.FAIL, Verdict.UNAVAILABLE)
```

(`tmp_hidden_task` / `tmp_visible_task` / `clean_patch` / `contaminated_patch` are conftest fixtures to ADD in this task: hidden = the P1 `_write_task` shape with overlay + a one-file base that the clean patch modifies; `contaminated_patch` embeds a copied overlay block exactly as `tests/test_contamination.py::_patch_adding` builds one. Reuse the P1 helper by importing it or duplicating the 15-line builder in `tests/conftest.py` — duplicating is fine, the helpers are small.)

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/test_receipt.py tests/test_grade.py -q`
Expected: FAIL — no `contamination` field; no auto-annotation.

- [ ] **Step 3: Implement**

`receipt.py`: add the field `contamination: dict | None = None` after `evidence`; rewrite `write_receipt`:

```python
def write_receipt(path: Path, receipt: Receipt) -> None:
    data = asdict(receipt)
    if receipt.contamination is None:
        del data["contamination"]
    path.write_text(json.dumps(data, indent=2) + "\n")
```

`grade.py`: after `manifest = load_manifest(task_dir)`:

```python
    auto_overlay = overlay is None and manifest.oracle_visibility == "hidden"
    if auto_overlay:
        overlay = load_overlay(task_dir, manifest)
```

and after `evidence` is built (and also in the `except` branch — detection runs on the patch bytes whenever a receipt is written), before constructing `Receipt`:

```python
    contamination: dict | None = None
    if auto_overlay:
        result = scan_patch(patch_text, overlay)
        contamination = {
            "visibility": "hidden",
            "checks": [
                {
                    "check": result.check,
                    "outcome": result.outcome,
                    "evidence": [asdict(item) for item in result.evidence],
                }
            ],
        }
```

pass `contamination=contamination` to the `Receipt` constructor. Note in the docstring: explicit-overlay callers (the session grader) get no annotation here — session findings land on the session record (P4).

- [ ] **Step 4: Run to verify pass**

Run: `.venv/bin/pytest tests/test_receipt.py tests/test_grade.py -q`
Expected: PASS. Then `.venv/bin/pytest -q` — every existing grade/receipt/CLI test must still pass (visible receipt bytes unchanged; the session grader passes an explicit overlay so its receipts are unannotated).

- [ ] **Step 5: Commit**

```bash
ruff check src/satyrn_evals/receipt.py src/satyrn_evals/grade.py
git add src/satyrn_evals/receipt.py src/satyrn_evals/grade.py tests/test_receipt.py tests/test_grade.py tests/conftest.py
git commit -m "feat: hidden-task receipts carry contamination findings; grade auto-overlays"
```

---

### Task 2: Cells, visibility, and the contamination section in summaries

**Files:**
- Modify: `src/satyrn_evals/summary.py`, `src/satyrn_evals/run.py`
- Test: `tests/test_summary.py`, `tests/test_run.py`

**Interfaces:**
- Consumes: `AttemptRecord` (unchanged), the parsed receipt dict from Task 1's on-disk shape.
- Produces:
  - `type AttemptCell = tuple[str, AttemptRecord, dict | None]` — (attempt directory name, record, parsed receipt dict or None).
  - `compute_summary(cells: Sequence[AttemptCell], *, oracle_visibility: str) -> Summary`.
  - `Summary` gains `oracle_visibility: str`, `cells: list[str]`, `contamination: dict[str, int] | None`; `__post_init__` enforces `flagged + clean + unmeasured == graded` and the exact key set `{"graded", "flagged", "clean", "unmeasured"}` when contamination is present.
  - `write_summary` omits `contamination` when `None`.
  - `run` names cells by directory delta and reads `receipt.json` per cell.

- [ ] **Step 1: Write the failing tests**

In `tests/test_summary.py` (the file has record builders — reuse them; the cells below are built inline):

```python
def _cell(name, code=AttemptCode.OK, verdict=Verdict.PASS, receipt=None):
    record = _record(code=code, verdict=verdict)  # existing builder in this file
    return (name, record, receipt)


def _receipt_dict(checks=(("grader_content_in_patch", "clean"),)):
    return {"contamination": {"visibility": "hidden", "checks": [
        {"check": c, "outcome": o, "evidence": []} for c, o in checks
    ]}}


def test_summary_names_cells_and_visibility():
    summary = compute_summary(
        [_cell("task-1"), _cell("task-2")], oracle_visibility="visible"
    )
    assert summary.cells == ["task-1", "task-2"]
    assert summary.oracle_visibility == "visible"
    assert summary.contamination is None


def test_hidden_summary_counts_and_invariant():
    cells = [
        _cell("task-1", receipt=_receipt_dict()),
        _cell("task-2", receipt=_receipt_dict((("grader_content_in_patch", "flagged"),))),
        _cell("task-3", receipt={}),  # pre-V7 receipt: no key
        _cell("task-4", code=AttemptCode.NO_PATCH, verdict=None, receipt=None),  # refused
    ]
    summary = compute_summary(cells, oracle_visibility="hidden")
    assert summary.contamination == {
        "graded": 3, "flagged": 1, "clean": 1, "unmeasured": 1
    }
    assert summary.n == 4 and summary.refused == 1
    assert summary.verdict_counts[Verdict.PASS.value] == 2  # denominators untouched


def test_denominators_unchanged_by_contamination_outcomes():
    verdicts = [Verdict.PASS, Verdict.FAIL, Verdict.UNAVAILABLE]
    clean = [_cell(f"t-{i}", verdict=v) for i, v in enumerate(verdicts)]
    flagged = [
        _cell(f"t-{i}", verdict=v, receipt=_receipt_dict(
            (("grader_content_in_patch", "flagged"),)))
        for i, v in enumerate(verdicts)
    ]
    a = compute_summary(clean, oracle_visibility="visible")
    b = compute_summary(flagged, oracle_visibility="hidden")
    assert (a.n, a.attempted, a.refused, a.code_counts, a.verdict_counts, a.timeouts) == \
           (b.n, b.attempted, b.refused, b.code_counts, b.verdict_counts, b.timeouts)


def test_summary_invariant_refuses_bad_tally():
    with pytest.raises(ValueError, match="flagged \\+ clean \\+ unmeasured"):
        Summary(
            n=1, attempted=1, refused=0,
            code_counts={c.value: 0 for c in AttemptCode},
            verdict_counts={v.value: 0 for v in Verdict},
            timeouts=0,
            oracle_visibility="hidden", cells=["t-1"],
            contamination={"graded": 2, "flagged": 1, "clean": 1, "unmeasured": 1},
        )


def test_write_summary_omits_contamination_when_visible(tmp_path):
    path = tmp_path / "summary.json"
    write_summary(path, compute_summary([], oracle_visibility="visible"))
    assert "contamination" not in json.loads(path.read_text())
```

In `tests/test_run.py` (uses the fake seam command — follow the file's existing pattern; the key new assertion is the cell set):

```python
def test_run_summary_names_created_attempt_dirs(tmp_output, fake_seam):
    summary = run(task="format_number", tasks_root=DEFAULT_TASKS_ROOT,
                  output=tmp_output, command=fake_seam, n=3)
    assert len(summary.cells) == 3
    assert all(name.startswith("format_number-") for name in summary.cells)
    assert summary.oracle_visibility == "visible"
    assert summary.contamination is None
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/test_summary.py tests/test_run.py -q`
Expected: FAIL — `compute_summary` takes records, not cells; new fields missing.

- [ ] **Step 3: Implement**

`summary.py`: add `oracle_visibility`, `cells`, `contamination` to `Summary` (defaults `cells` field default `None`-free: make them required and update every construction site — there are exactly two: `compute_summary` and tests). Extend `__post_init__`:

```python
        if self.contamination is not None:
            if set(self.contamination) != {"graded", "flagged", "clean", "unmeasured"}:
                raise ValueError("contamination must hold exactly graded/flagged/clean/unmeasured")
            if sum(self.contamination[k] for k in ("flagged", "clean", "unmeasured")) != self.contamination["graded"]:
                raise ValueError("flagged + clean + unmeasured must equal graded")
```

Replace `compute_summary`:

```python
type AttemptCell = tuple[str, AttemptRecord, dict | None]


def _cell_outcome(receipt: dict) -> str:
    """Per-cell contamination outcome from a parsed receipt dict.

    Callers pass only receipts of graded cells (the graded filter is
    `attempted and receipt is not None`), so `receipt` is never None
    here. A pre-V7 receipt — no `contamination` key — is `unmeasured`:
    grading ran, detection did not.
    """
    if (finding := receipt.get("contamination")) is None:
        return "unmeasured"
    results = [
        CheckResult(check["check"], check["outcome"], ())
        for check in finding["checks"]
    ]
    return overall(results)


def compute_summary(
    cells: Sequence[AttemptCell], *, oracle_visibility: str
) -> Summary:
    n = len(cells)
    attempted = sum(1 for _, record, _ in cells if record.outcome is AttemptOutcome.ATTEMPTED)
    code_counts = {code.value: 0 for code in AttemptCode}
    verdict_counts = {verdict.value: 0 for verdict in Verdict}
    for _, record, _ in cells:
        code_counts[record.code.value] += 1
        if record.verdict is not None:
            verdict_counts[record.verdict.value] += 1
    contamination = None
    if oracle_visibility == "hidden":
        graded = [receipt for _, record, receipt in cells
                  if record.outcome is AttemptOutcome.ATTEMPTED and receipt is not None]
        tally = {"graded": len(graded), "flagged": 0, "clean": 0, "unmeasured": 0}
        for receipt in graded:
            tally[_cell_outcome(receipt)] += 1
        contamination = tally
    return Summary(
        n=n, attempted=attempted, refused=n - attempted,
        code_counts=code_counts, verdict_counts=verdict_counts,
        timeouts=code_counts[AttemptCode.COMMAND_TIMEOUT.value],
        oracle_visibility=oracle_visibility,
        cells=[name for name, _, _ in cells],
        contamination=contamination,
    )
```

`write_summary`: build the dict via `asdict`, drop `contamination` when `None`, keep the trailing newline.

`run.py`: capture the directory delta and read receipts:

```python
def run(*, task, tasks_root, output, command, n, timeout=DEFAULT_TIMEOUT) -> Summary:
    ...
    manifest = load_manifest(resolve_task(task, tasks_root=tasks_root))
    cells: list[AttemptCell] = []
    for _ in range(n):
        before = {p.name for p in output.iterdir()} if output.is_dir() else set()
        record = attempt(task=task, tasks_root=tasks_root, output=output,
                         command=command, timeout=timeout)
        after = {p.name for p in output.iterdir()} if output.is_dir() else set()
        if not (new := after - before):
            raise RuntimeError("attempt created no attempt directory")
        (cell_name,) = new  # exactly one directory per attempt call
        receipt = None
        if record.receipt_path is not None:
            receipt_path = output / cell_name / record.receipt_path
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        cells.append((cell_name, record, receipt))
    summary = compute_summary(cells, oracle_visibility=manifest.oracle_visibility)
    output.mkdir(parents=True, exist_ok=True)
    write_summary(output / "summary.json", summary)
    return summary
```

- [ ] **Step 4: Run to verify pass**

Run: `.venv/bin/pytest tests/test_summary.py tests/test_run.py tests/test_cli.py -q`
Expected: PASS (existing run tests updated to the cell-based summary — the record-level assertions carry over; only the summary construction input changed).

- [ ] **Step 5: Commit**

```bash
ruff check src/satyrn_evals/summary.py src/satyrn_evals/run.py
git add src/satyrn_evals/summary.py src/satyrn_evals/run.py tests/test_summary.py tests/test_run.py
git commit -m "feat: summaries name their cell set and tally contamination beside verdict counts"
```

---

### Task 3: End-to-end hidden-task run through the fake seam

**Files:**
- Test: `tests/test_run.py` (default tier; the fake seam command is the established pattern from `tests/integration/fake_attempt.py` reduced to a deterministic shell-free script — check how `tests/test_run.py` fakes the seam today and follow it)

**Interfaces:**
- Consumes: everything above.
- Produces: the denominators-and-cells proof on a hidden task end to end (still no subprocess in the default tier — reuse whatever the existing test_run faking mechanism is; if the seam fake requires a process, this test belongs in `tests/integration/test_run.py` and is marked accordingly).

- [ ] **Step 1: Write the failing test**

```python
def test_hidden_task_run_reports_contamination(tmp_output, hidden_seam):
    summary = run(task=HIDDEN_TASK_NAME, tasks_root=DEFAULT_TASKS_ROOT,
                  output=tmp_output, command=hidden_seam, n=2)
    assert summary.oracle_visibility == "hidden"
    assert summary.contamination is not None
    assert summary.contamination["graded"] == summary.contamination["flagged"] + \
        summary.contamination["clean"] + summary.contamination["unmeasured"]
    assert len(summary.cells) == 2
```

(`hidden_seam` = the same fake seam used for `format_number` runs, pointed at `session-mechanics` with a patch fixture that applies cleanly; `HIDDEN_TASK_NAME = "session-mechanics"`.)

- [ ] **Step 2: Run to verify, then commit**

Run: `.venv/bin/pytest tests/test_run.py -q` — PASS (this is a composes-everything test; if it fails, fix the failing piece above, never the assertion).

```bash
.venv/bin/pytest -q && ruff check .
git add tests/test_run.py
git commit -m "test: hidden-task run carries the contamination tally end to end"
```
