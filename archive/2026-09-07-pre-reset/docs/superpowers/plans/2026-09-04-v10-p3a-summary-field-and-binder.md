> **Archived pre-reset record (2026-09-07).**
>
> Original claims, decisions, and instructions may be superseded. This file is evidence, not current guidance.
> For current guidance, read root AGENTS.md, BRIEF.md, and ROADMAP.md. Retrieve one named record when it bears on a concrete question; do not preload this archive.

# V10 P3 — Summary integration: the Summary field and the pathology binder (tasks 1-2 of four)

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

### Task 1: `Summary.pathology` and the pure-tally signature change

**Files:** `src/satyrn_evals/summary.py`; construction sites in `run.py`,
`rescore.py`; tests `test_summary.py`, `test_run.py`, `test_rescore.py`.

**Interfaces:** `Summary.pathology: dict[str, dict]` (required, no
default); `compute_summary(cells, *, oracle_visibility, pathology:
dict[str, dict])` — validates `set(pathology) == set(cell names)` (a
mismatch is a `ValueError` naming the missing/extra cells) and every value
carries a boolean `measured`; `write_summary` serializes `pathology`
as-is (always present). `CellPathology.to_block` (P1) is the only block
producer in production; tests may build blocks by hand.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_summary.py`)

```python
def test_summary_pathology_requires_every_cell_key() -> None:
    cells = [_cell("t-1"), _cell("t-2")]
    with pytest.raises(ValueError, match="pathology"):
        compute_summary(
            cells,
            oracle_visibility="visible",
            pathology={"t-1": {"measured": False, "reason": "absent"}},
        )


def test_summary_pathology_writes_through() -> None:
    cells = [_cell("t-1")]
    pathology = {"t-1": {"measured": False, "reason": "absent"}}
    summary = compute_summary(cells, oracle_visibility="visible", pathology=pathology)
    assert summary.pathology == pathology
```

- [ ] **Step 2: Run to verify they fail** — `uv run pytest -q
  tests/test_summary.py -k "pathology"` → FAIL (`compute_summary` takes no
  `pathology`).

- [ ] **Step 3: Implement the field and validation**

In `src/satyrn_evals/summary.py`:

1. Add the field to the dataclass (after `contamination`):

```python
    pathology: dict[str, dict]
```

2. In `__post_init__` and at the top of `compute_summary`, run one key
   check (the same logic, so share it via a small module helper): the
   pathology keys must equal the cell names exactly and every value must
   carry a boolean `measured`. The `ValueError`s name the missing/extra
   cells (`"pathology must name exactly the cells (missing: …, extra:
   …)"`) and the shape violation (`"each pathology block must carry a
   boolean measured"`).

3. Change the `compute_summary` signature:

```python
def compute_summary(
    cells: Sequence[AttemptCell],
    *,
    oracle_visibility: str,
    pathology: dict[str, dict],
) -> Summary:
```

   then pass `pathology` reordered to cell order to the `Summary(...)`
   constructor — the field keys must follow the summary's cell order
   (spec §4).

4. Ripple: every `Summary`/`compute_summary` construction site in
   `summary.py`, `run.py`, `rescore.py`, and the test modules now needs a
   `pathology` value. Mechanical rule: a helper
   `def _absent_pathology(cells) -> dict[str, dict]` in each test module
   mapping every cell name to `{"measured": False, "reason": "absent"}` is
   the honest value for fake-seam cells (no transcript on disk); explicit
   blocks where a test asserts pathology behavior.

- [ ] **Step 4: Run to verify they pass + gate** — `uv run pytest -q
  tests/test_summary.py -k "pathology"` then the full suite; fix every
  construction site the compiler flags. Then `uv run pytest -q
  --cov=satyrn_evals --cov-report=term-missing` (100% statement+branch),
  `uv run ruff check src tests`, `uv run pyrefly`.

---


### Task 2: The shared artifact binder `compute_pathology`

**Files:** `src/satyrn_evals/rescore.py`; test `tests/test_rescore.py`.

**Interfaces:** Consumes `AttemptCell`, `count_transcript` +
`CellPathology` (P1), `scan_transcript` (P2), `load_overlay`, `TaskManifest`.
Produces `compute_pathology(output, cells, *, task_dir, manifest) ->
dict[str, dict]` — per cell, in cell order: no `transcript_path`, or a
named file missing/unreadable/not-regular ⇒ `absent`; otherwise
`count_transcript(text, had_patch=record.patch_path is not None).to_block()`.
Hidden-oracle **measured** cells gain `overlay_windows: len(scan_transcript(
text, spec, visible_texts))` with `spec = load_overlay(task_dir, manifest)`
and `visible_texts` the UTF-8 texts under `task_dir/"base"` (unreadable
files contribute nothing); visible-oracle cells never carry the key. An
overlay load failure raises (operational).

- [ ] **Step 1: Write the failing tests** (append to `tests/test_rescore.py`)

```python
def test_compute_pathology_marks_missing_transcript_absent(
    tmp_path: Path,
) -> None:
    output, cells, task_dir, manifest = _run_dir(tmp_path)  # helper, below
    block = compute_pathology(output, cells, task_dir=task_dir, manifest=manifest)
    assert block == {name: {"measured": False, "reason": "absent"} for name, _, _ in cells}


def test_compute_pathology_counts_a_good_transcript(tmp_path: Path) -> None:
    output, cells, task_dir, manifest = _run_dir(tmp_path)
    (output / cells[0][0] / "transcript.txt").write_text(GOOD, encoding="utf-8")
    block = compute_pathology(output, cells, task_dir=task_dir, manifest=manifest)
    assert block[cells[0][0]]["measured"] is True
    assert block[cells[0][0]]["tool_calls"] == {"read": 2, "edit": 2}
```

`_run_dir` builds a small visible-task output dir whose record names
`transcript.txt` (model it on the existing `test_rescore.py` cell-writer
helper) and returns `(output, cells, task_dir, manifest)`; `task_dir`
points at the bundled `format_number` task via `resolve_task` (existing
tests already resolve a task there).

- [ ] **Step 2: Run to verify they fail** — `uv run pytest -q
  tests/test_rescore.py -k "compute_pathology"` → FAIL (`ImportError`).

- [ ] **Step 3: Implement the binder** (append to `rescore.py`)

```python
def _base_texts(task_dir: Path) -> list[str]:
    """UTF-8 text of the task's model-visible base files (visible windows)."""
    texts: list[str] = []
    base = task_dir / "base"
    if not base.is_dir():
        return []
    for path in sorted(base.rglob("*")):
        if path.is_file() and not path.is_symlink():
            try:
                texts.append(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError):
                continue
    return texts


_ABSENT = {"measured": False, "reason": "absent"}


def compute_pathology(
    output: Path,
    cells: Sequence[AttemptCell],
    *,
    task_dir: Path,
    manifest: TaskManifest,
) -> dict[str, dict]:
    """Per-cell pathology blocks over the preserved transcripts (V10 §4).

    A per-cell read problem is per-cell ``absent``, never a batch failure;
    only shared task-data problems (the overlay) raise. Hidden-oracle
    measured cells gain ``overlay_windows`` from the transcript scan with
    the base texts subtracted; visible-oracle cells never carry the key.
    """
    hidden = manifest.oracle_visibility == "hidden"
    overlay = load_overlay(task_dir, manifest) if hidden else None
    visible_texts = _base_texts(task_dir) if hidden else []
    blocks: dict[str, dict] = {}
    for name, record, _ in cells:
        path = None if record.transcript_path is None else output / name / record.transcript_path
        if path is None or not _readable_regular(path):
            blocks[name] = _ABSENT
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        block = count_transcript(
            text, had_patch=record.patch_path is not None
        ).to_block()
        if hidden and block.get("measured") is True and overlay is not None:
            block["overlay_windows"] = len(
                scan_transcript(text, overlay, visible_texts=visible_texts)
            )
        blocks[name] = block
    return blocks


def _readable_regular(path: Path) -> bool:
    try:
        return stat.S_ISREG(path.lstat().st_mode)
    except OSError:
        return False
```

Read failure is mapped per spec §4's "missing or unreadable at summary
time" by decoding with `errors="replace"` and letting the parser decide
`unparseable` where the text is garbage — the parser stays the single
arbiter of text quality; a genuinely unreadable file is `absent`.

- [ ] **Step 4: Run to verify they pass + gate** — `uv run pytest -q
  tests/test_rescore.py -k "compute_pathology"`, full suite, 100% branch,
  ruff, pyrefly.

---


## Self-review note for the executor

The spec is binding; where this plan and the spec disagree, the spec wins
and the discrepancy is a plan defect to report. Per-cell transcript read
problems are per-cell `absent`, never a batch failure; shared task-data
problems (the overlay) are operational (3) on the summary paths and are
folded into the abort marker's `error` so the primary exception always
surfaces. `regrade` recomputes nothing. Trimmed to the 400-line cap
2026-09-04.
