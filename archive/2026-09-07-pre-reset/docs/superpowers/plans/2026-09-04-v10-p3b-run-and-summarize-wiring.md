> **Archived pre-reset record (2026-09-07).**
>
> Original claims, decisions, and instructions may be superseded. This file is evidence, not current guidance.
> For current guidance, read root AGENTS.md, BRIEF.md, and ROADMAP.md. Retrieve one named record when it bears on a concrete question; do not preload this archive.

# V10 P3 — Summary integration: run and summarize wiring (tasks 3-4 of four)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `summary.json` gains the `pathology` block (spec §4, §6) through
one shared computation — `compute_pathology` in `rescore.py` — called by
`run` (its own summary and the abort marker) and `summarize_output`, so a
rebuilt summary is byte-identical to the run's own under the same code and
artifacts, a pre-V10 run re-summarized under V10 gains the block
(retroactive), and `regrade` is untouched.

**Architecture:** `Summary` gains a required `pathology: dict[str, dict]`
field (one wire block per cell, keys in cell order); `compute_summary`
stays a pure tally. The binder `compute_pathology(output, cells, *,
task_dir, manifest)` reads each cell's preserved transcript (per-cell read
failures are per-cell `absent`, never a batch failure — spec §4), calls
`count_transcript` (P1) with `had_patch = record.patch_path is not None`,
and joins P2's `scan_transcript` for hidden-oracle cells. `run.py` imports
the binder from `rescore.py` (no cycle: `rescore` does not import `run`).

**Tech Stack:** Python ≥3.14, stdlib only, house style.

**Spec:** `docs/superpowers/specs/2026-09-04-v10-transcript-pathology-counts-design.md`
§4–§7, §9.5–9.7. Depends on P1 (`count_transcript`, `CellPathology.to_block`)
and P2 (`scan_transcript`).

## Global Constraints

- **No commits** (maintainer-controlled); leave the worktree dirty.
- Default tier: `uv run pytest -q`; tripwire forbids subprocess spawn. All
  V10 behavior is pure file I/O — no integration tier needed.
- Refusal tests get success siblings. Every new `Summary` field must be
  read in a test (100% branch gate, `fail_under = 100`).
- Overlay load failure on a hidden task is operational (3) on `run`'s own
  summary and on `summarize`; the abort marker must never let a binder
  failure mask the primary abort exception (Task 3).
- House style: real return annotations, `type` aliases, `match`, `:=`.
- Fake-seam cells (e.g. `tests/test_run.py::_fake_attempt`) write no
  transcript; under V10 their cells are `absent` — assert that truth, do
  not hide it.

---

### Task 3: `run` wiring — own summary and abort marker

**Files:** `src/satyrn_evals/run.py`; test `tests/test_run.py`.

**Interfaces:** Consumes `compute_pathology` (Task 2). Produces: `run(...)`
resolves and keeps `task_dir`; after the loop its summary is written with
the pathology block; `_write_aborted(..., pathology, binder_error)` never
lets a binder failure mask the primary abort exception — the marker's
`error` is augmented with the binder failure and the block is omitted
when the binder failed, written when it succeeded (one behavior, tested
both ways).

- [ ] **Step 1: Write the failing tests** (append to `tests/test_run.py`)

```python
def test_run_summary_carries_pathology_for_completed_cells(
    tmp_path: Path,
) -> None:
    output = tmp_path / "runs"
    fake = _fake_attempt(transcript=GOOD)  # helper writes transcript.txt
    monkeypatch.setattr(run_module, "attempt", fake)
    run(task="format_number", tasks_root=DEFAULT_TASKS_ROOT, output=output,
        command=["fake"], n=2, timeout=1.5)
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert set(summary["pathology"]) == set(summary["cells"])
    assert all(block["measured"] is True for block in summary["pathology"].values())
    assert summary["pathology"][summary["cells"][0]]["tool_calls"] == {"read": 2, "edit": 2}


def test_abort_marker_never_masks_the_primary_exception(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "runs"

    def failing_fake(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(run_module, "attempt", failing_fake)
    with pytest.raises(RuntimeError, match="boom"):
        run(task="format_number", tasks_root=DEFAULT_TASKS_ROOT,
            output=output, command=["fake"], n=2, timeout=1.5)
    marker = json.loads((output / "aborted.json").read_text(encoding="utf-8"))
    assert "boom" in marker["error"]
    assert not (output / "summary.json").exists()
```

- [ ] **Step 2: Run to verify they fail** — `uv run pytest -q
  tests/test_run.py -k "pathology or abort_marker"` → FAIL.

- [ ] **Step 3: Implement**

In `src/satyrn_evals/run.py`:

1. Keep the resolved `task_dir` (today the manifest is loaded and the dir
   discarded). After the loop, before `compute_summary`:

```python
    pathology = compute_pathology(
        output, cells, task_dir=task_dir, manifest=manifest
    )
```

2. `_write_aborted` gains a `pathology: dict[str, dict] | None` parameter
   and only sets `data["pathology"]` when not `None`. In `run`'s
   `except BaseException` clause, compute the block for the completed
   cells inside its own guard:

```python
    except BaseException as exc:
        pathology = None
        binder_error = None
        try:
            pathology = compute_pathology(output, cells, task_dir=task_dir, manifest=manifest)
        except BaseException as bind_exc:  # never mask the abort
            binder_error = f"pathology unavailable: {type(bind_exc).__name__}: {bind_exc}"
        _write_aborted(output, requested=n, cells=cells,
                       error=f"{type(exc).__name__}: {exc}"
                             + (f"; {binder_error}" if binder_error else ""),
                       oracle_visibility=manifest.oracle_visibility,
                       pathology=pathology)
        raise
```

3. The `attempt` double in `tests/test_run.py` gains an optional
   `transcript` kwarg writing `transcript.txt` in the cell dir when given
   (the seam path the real command writes through).

- [ ] **Step 4: Run to verify they pass + gate** — `uv run pytest -q
  tests/test_run.py`, full suite, 100% branch, ruff, pyrefly.

---


### Task 4: `summarize` wiring, byte-identity, and retroactive enrichment

**Files:** `src/satyrn_evals/rescore.py`; test `tests/test_rescore.py`.

**Interfaces:** Consumes `compute_pathology` (Task 2). Produces:
`summarize_output` computes the block over the anchored cells and writes
it; a rebuilt summary is byte-identical to `run`'s own under the same code
and artifacts; a pre-V10 `summary.json` (no `pathology` key) re-summarized
under V10 gains the block. `regrade_attempt` unchanged (regrade never
recomputes pathology — spec §8).

- [ ] **Step 1: Write the failing tests** (append to `tests/test_rescore.py`)

```python
def test_run_then_summarize_is_byte_identical_with_pathology(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "runs"
    monkeypatch.setattr(run_module, "attempt", _fake_attempt(transcript=GOOD))
    run(task="format_number", tasks_root=DEFAULT_TASKS_ROOT, output=output,
        command=["fake"], n=2, timeout=1.5)
    own = (output / "summary.json").read_bytes()
    summarize_output(output, tasks_root=DEFAULT_TASKS_ROOT)
    assert (output / "summary.json").read_bytes() == own


def test_summarize_enriches_a_pre_v10_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "runs"
    monkeypatch.setattr(run_module, "attempt", _fake_attempt(transcript=GOOD))
    run(task="format_number", tasks_root=DEFAULT_TASKS_ROOT, output=output,
        command=["fake"], n=2, timeout=1.5)
    path = output / "summary.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    del data["pathology"]  # simulate a pre-V10 summary
    path.write_text(json.dumps(data) + "\n", encoding="utf-8")
    summarize_output(output, tasks_root=DEFAULT_TASKS_ROOT)
    rebuilt = json.loads(path.read_text(encoding="utf-8"))
    assert set(rebuilt["pathology"]) == set(rebuilt["cells"])
    assert all(b["measured"] for b in rebuilt["pathology"].values())


def test_summarize_refuses_an_unreadable_overlay_as_operational(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A hidden task whose overlay load fails (manifest names a missing
    # grader_overlay) must raise operational, not per-cell unmeasured.
    ...
```

- [ ] **Step 2: Run to verify they fail** — `uv run pytest -q
  tests/test_rescore.py -k "byte_identical or pre_v10 or unreadable_overlay"`
  → FAIL.

- [ ] **Step 3: Implement**

In `summarize_output`, after the cells and manifest are resolved, before
`compute_summary`:

```python
    pathology = compute_pathology(
        output, cells, task_dir=task_dir, manifest=manifest
    )
    summary = compute_summary(
        cells,
        oracle_visibility=manifest.oracle_visibility,
        pathology=pathology,
    )
```

(`task_dir` is already resolved in the function — reuse it.) The overlay
load failure inside `compute_pathology` propagates as operational (3) —
wrap it in a `SatyrnError` naming summarize if the error type does not
carry the exit class. `_read_anchor` is untouched: the anchored cell set
still governs the rebuild, and the block is computed over exactly those
cells.

- [ ] **Step 4: Run to verify they pass + gate** — `uv run pytest -q
  tests/test_rescore.py -k "byte_identical or pre_v10 or unreadable_overlay"`,
  full suite, 100% branch, ruff, pyrefly.

---


## Self-review note for the executor

The spec is binding; where this plan and the spec disagree, the spec wins
and the discrepancy is a plan defect to report. Per-cell transcript read
problems are per-cell `absent`, never a batch failure; shared task-data
problems (the overlay) are operational (3) on the summary paths and are
folded into the abort marker's `error` so the primary exception always
surfaces. `regrade` recomputes nothing. Trimmed to the 400-line cap
2026-09-04.
