> **Archived pre-reset record (2026-09-07).**
>
> Original claims, decisions, and instructions may be superseded. This file is evidence, not current guidance.
> For current guidance, read root AGENTS.md, BRIEF.md, and ROADMAP.md. Retrieve one named record when it bears on a concrete question; do not preload this archive.

# V10 P2 — The overlay-window scan: transcript as scanned body

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `src/satyrn_evals/contamination.py` gains one scan entry —
`scan_transcript(text, spec, visible_texts=()) -> tuple[Evidence, ...]` —
that detects verbatim overlay-content windows inside a preserved attempt
transcript, reusing the existing verbatim machinery
(`_nonblank`/`_window_in_visible`/`GRADER_BLOCK_LINES`) with the
model-visible subtraction V7 uses. The count of the returned evidence is
spec §3.8's `overlay_windows` (joined by P3's binder). No behavior change
to the existing checks (`scan_patch`, `scan_texts`, `assert_overlay_absent`).

**Architecture:** The transcript is the scanned body where `scan_patch`
scans added patch lines. One `Evidence` per **overlay file evidenced** —
not per window multiplicity — mirroring `scan_patch`'s per-file first-hit
semantics, so a single `cat` of a hidden file counts once, not once per
sliding window. A file at most `GRADER_BLOCK_LINES` lines matches as a
whole (`whole_file`); a longer file matches on its first ≥4-line window
not present in any visible text (`block`).

**Tech Stack:** Python ≥3.14, stdlib only, house style (`type` aliases,
`match`, `:=`).

**Spec:** `docs/superpowers/specs/2026-09-04-v10-transcript-pathology-counts-design.md`
§3.8 (as amended 2026-09-04: `overlay_windows` counts overlay **files
evidenced**, whole-file when ≤ `GRADER_BLOCK_LINES` lines else first
matching ≥4-line window), §7 module shape, §9.4 done-when.

## Global Constraints

- **No commits.** Commits are maintainer-controlled; leave the worktree
  dirty.
- Default tier: `uv run pytest -q`; tripwire forbids subprocess spawn.
- Every new branch covered (100% statement + branch gate). A refusal has
  a sibling success; the detector fires on a known-bad drawn from the
  current batch and stays silent on a known-good.
- `contamination.py` import note: `OverlaySpec` is imported under
  `TYPE_CHECKING` only (module docstring) — keep that discipline.
- House style: real return annotations, `type` aliases, `match`, `:=`.

---

### Task 1: `scan_transcript` with per-file evidence

**Files:**
- Modify: `src/satyrn_evals/contamination.py`
- Test: `tests/test_contamination.py`

**Interfaces:**
- Consumes: `Evidence`, `_nonblank`, `_window_in_visible`,
  `GRADER_BLOCK_LINES` (all present in `contamination.py`).
- Produces: `scan_transcript(text: str, spec: OverlaySpec,
  visible_texts: Sequence[str] = ()) -> tuple[Evidence, ...]` — one
  `Evidence` per overlay file whose content window appears verbatim in
  `text`; `kind` is `"whole_file"` when the file's non-blank line count is
  ≤ `GRADER_BLOCK_LINES` (matched as a whole) else `"block"` (first
  matching window, overlay line order); `overlay_path` is the overlay-relative
  path; `in_path` is `"transcript.txt"`; `line` is the 1-based raw
  transcript line where the window starts. Windows that appear in any
  `visible_texts` are not evidence. Returns `()` for a transcript with no
  matching window.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_contamination.py`)

```python
def test_transcript_catting_hidden_file_flags_whole_file() -> None:
    spec = make_spec_short()  # single <=4-line overlay file, see Step 3
    leaked = "def test_secret():\n    assert False\n"  # echoed verbatim
    hits = scan_transcript(leaked, spec)
    assert len(hits) == 1
    assert hits[0].overlay_path == "tests/t_hidden.py"
    assert hits[0].kind == "whole_file"
    assert hits[0].in_path == "transcript.txt"
    assert hits[0].line == 1


def test_transcript_with_base_read_stays_clean() -> None:
    spec = make_spec()  # 5+ non-blank overlay lines -> block matching
    visible = "def test_a():\n\n    x = 1\n    y = 2\n    z = 3\n    assert x + y == z\n"
    # A read of the visible base file echoes content the overlay shares.
    assert scan_transcript(visible, spec, visible_texts=[visible]) == ()


def test_transcript_echoing_overlay_block_flags() -> None:
    spec = make_spec()
    leaked = "def test_a():\n\n    x = 1\n    y = 2\n    z = 3\n    assert x + y == z\n"
    hits = scan_transcript(leaked, spec)
    assert len(hits) == 1
    assert hits[0].kind == "block"


def test_transcript_one_idiomatic_line_stays_clean() -> None:
    spec = make_spec()
    assert scan_transcript("import pytest\n", spec) == ()


def test_overlay_window_shared_with_visible_text_is_not_evidence() -> None:
    spec = make_spec()
    shared = "    x = 1\n    y = 2\n    z = 3\n    assert x + y == z\n"
    hits = scan_transcript(shared, spec, visible_texts=[shared])
    assert hits == ()
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest -q tests/test_contamination.py -k "transcript"`
Expected: FAIL — `ImportError`/`AttributeError` (`scan_transcript` missing).

- [ ] **Step 3: Implement `scan_transcript`**

Add a short-file helper spec to the test module:

```python
def make_spec_short() -> OverlaySpec:
    return OverlaySpec(
        root=Path("grader/overlay"),
        rel_paths=("tests/t_hidden.py",),
        digests={"tests/t_hidden.py": "abc"},
        texts={"tests/t_hidden.py": "def test_secret():\n    assert False\n"},
    )
```

In `contamination.py`, after `scan_patch`:

```python
def scan_transcript(
    text: str,
    spec: OverlaySpec,
    visible_texts: Sequence[str] = (),
) -> tuple[Evidence, ...]:
    """Check (d): verbatim overlay windows inside a preserved transcript.

    The transcript is the one graded artifact V7's checks do not cover
    (an attempt's ``clean`` covers the patch and workspace absence only,
    not the transcript -- 2026-09-04 V10 spec §3.8). Matching is verbatim
    raw-line windows exactly as ``scan_patch`` matches added patch lines,
    with the same model-visible subtraction: a window that also appears in
    the visible texts is shown content, not evidence.

    One Evidence per overlay *file evidenced*, never per sliding window:
    an overlay file whose non-blank lines fit in one window (<=$
    GRADER_BLOCK_LINES) matches as ``whole_file``; a longer file matches
    on its first >= GRADER_BLOCK_LINES window (overlay line order) as
    ``block``. ``line`` points into the transcript (1-based raw line).
    """
    transcript_seq = _nonblank(text)
    visible_seqs = tuple(_nonblank(value) for value in visible_texts)
    evidence: list[Evidence] = []
    for overlay_path, overlay_text in spec.texts.items():
        overlay_seq = _nonblank(overlay_text)
        window = min(GRADER_BLOCK_LINES, len(overlay_seq))
        if window == 0:
            continue
        kind = "whole_file" if window == len(overlay_seq) else "block"
        overlay_lines = [line for _, line in overlay_seq]
        transcript_lines = [line for _, line in transcript_seq]
        for start in range(len(overlay_lines) - window + 1):
            needle = overlay_lines[start : start + window]
            if _window_in_visible(needle, visible_seqs):
                continue
            for pos in range(len(transcript_lines) - window + 1):
                if transcript_lines[pos : pos + window] == needle:
                    evidence.append(
                        Evidence(
                            kind, overlay_path, "transcript.txt",
                            transcript_seq[pos][0],
                        )
                    )
                    break
            else:
                continue
            break  # one Evidence per overlay file
    return tuple(evidence)
```

- [ ] **Step 4: Run to verify they pass + module gate**

Run: `uv run pytest -q tests/test_contamination.py`
Expected: PASS (existing checks unchanged, new ones green).

Run: `uv run pytest -q` and `uv run pytest -q --cov=satyrn_evals
--cov-report=term-missing` — 100% statement and branch.
Run: `uv run ruff check src/satyrn_evals/contamination.py tests/test_contamination.py`
Run: `uv run pyrefly`
Expected: clean.

---

## Self-review note for the executor

The spec is binding; where this plan and the spec disagree, the spec wins
and the discrepancy is a plan defect to report. The spec's §3.8 was
amended 2026-09-04 to pin the count as overlay **files evidenced** — read
the amendment before implementing. P2 ships no summary wiring: P3's binder
calls `scan_transcript` with the task's overlay spec and base texts, and
places `overlay_windows` in the wire block for hidden measured cells only.
