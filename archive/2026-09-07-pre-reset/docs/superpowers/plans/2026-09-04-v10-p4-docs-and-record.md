> **Archived pre-reset record (2026-09-07).**
>
> Original claims, decisions, and instructions may be superseded. This file is evidence, not current guidance.
> For current guidance, read root AGENTS.md, BRIEF.md, and ROADMAP.md. Retrieve one named record when it bears on a concrete question; do not preload this archive.

# V10 P4 — Docs and record: schema reference, roadmap, backlog, verification

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every documentation surface V10 touches is current, the
superseded V5b deferral carries its supersession note, the backlog entry
closes with its outcome recorded, and the verification record lands in
`docs/sdd.md` with real gate numbers from the implemented tree.

**Architecture:** Docs edits only (no behavior change): `formats.md` gains
the `pathology` block in the run-summary reference and amends the
byte-identity statement to "same code and artifacts"; `ROADMAP.md`'s V10
row updates direction/excludes to the accepted design and marks the phase
in progress; `BACKLOG.md`'s transcript-metrics entry resolves; the V5b
spec's deferral note gains the supersession pointer; the verification
record follows the V9 pattern in `docs/sdd.md`.

**Tech Stack:** Markdown, Sphinx (MyST), `just lint-docs` for caps.

**Spec:** `docs/superpowers/specs/2026-09-04-v10-transcript-pathology-counts-design.md`
§4 (wire shape), §5 (CLI unchanged), §9.9 (done-when item 9), §11
(verification record shape). Depends on P1–P3 being implemented and green.

## Global Constraints

- **No commits.** Commits are maintainer-controlled; leave the worktree
  dirty.
- Documentation caps: `just lint-docs` enforces per-file caps (see
  `docs/sdd.md`); do not grow files past their caps — prefer tight prose.
- Corrections are recorded, not edited away: superseded documents get a
  supersession note pointing at this spec; the backlog entry's resolution
  is recorded where the phase row lives.
- House voice: counts-only summaries; no new wall-clock or causal claims.
- Verify, don't assert: every number in the verification record comes from
  a command run on the implemented tree in this session.

---

### Task 1: `formats.md` — the summary gains the pathology block

**Files:**
- Modify: `docs/reference/formats.md`

- [ ] **Step 1:** Read the current "Run summary" section and the
  byte-identity paragraph (the section V9 wrote). Update the field table
  with the `pathology` entry and add a compact block description:

```markdown
| `pathology` | per-cell block keyed by the cell names in `cells` order:
each a measured count set or `{"measured": false, "reason": …}`; absent or
unparseable/unknown-vocabulary/structurally-unsound transcripts are
`unmeasured`, never zero. Hidden-oracle runs add `overlay_windows` to
measured cells; visible-oracle runs carry no overlay key. See the V10
spec (`docs/superpowers/specs/2026-09-04-v10-…-design.md`) for the count
definitions and the reason set |
```

- [ ] **Step 2:** Amend the byte-identity sentence. Today it says a rebuilt
  summary is byte-identical to the run's own; under V10 the identity holds
  under the same code and artifacts, and re-running `summarize` over a
  pre-V10 run *enriches* it (adds the `pathology` block) — the retroactive
  mechanism the spec's §4 describes. State that explicitly.
- [ ] **Step 3:** Add one line noting that a transcript no V10 vocabulary
  recognizes (a fake command's arbitrary text, a session's mapped
  transcript) makes the cell `{"measured": false, "reason": …}`, and that
  this is a reporting state, never an error or a change to any exit code.
- [ ] **Step 4:** Run `just lint-docs`; fix cap or link issues. Show the
  diff of the section in your report.

---

### Task 2: `ROADMAP.md` — V10 row current and in progress

**Files:**
- Modify: `ROADMAP.md` (row 98 only; no other rows)

- [ ] **Step 1:** Update the V10 row's Direction and Excludes to the
  accepted design (the row still names `announce-and-stop` and `test
  runs`; the recorded design names `tool_free_terminal_turns` and
  `test_runner_commands` — spec §0 A2/A3). Keep the direction to one
  sentence. The Excludes column already names wall-clock, the engine seam,
  and causal claims; add sessions (A1) if not already excluded.
- [ ] **Step 2:** Update the Status cell to:

```markdown
**in progress** — design spec
`docs/superpowers/specs/2026-09-04-v10-transcript-pathology-counts-design.md`
accepted 2026-09-04 (maintainer adjustments A1–A4, schema tightenings
S1–S2; self-review and GLM 5.3 review recorded in spec §13); plans
`2026-09-04-v10-p1` … `p4`; verification record lands in `docs/sdd.md`
```

- [ ] **Step 3:** Check the "Next roadmap: gates and sequence" paragraph
  that mentions V10 ("applied retroactively to V12's preserved transcripts
  …") still reads true — it does; do not rewrite it.
- [ ] **Step 4:** `just lint-docs` and `git diff --check` clean.

---

### Task 3: `BACKLOG.md` close-out and V5b supersession note

**Files:**
- Modify: `BACKLOG.md`
- Modify: `docs/superpowers/specs/2026-09-02-v5b-diagnostic-loop-design.md`

- [ ] **Step 1:** In `BACKLOG.md`, the "Transcript-derived summary
  metrics" entry (the reopened V10 entry) resolves. Per the backlog's own
  three rules, a resolved entry is removed once its outcome is recorded in
  a phase row or research doc — the outcome now lives in ROADMAP row V10
  and this spec — so remove the entry and leave the definitions it carried
  cited from the spec (the spec §3 cites the same harvest-index anchors).
  If the entry's removal leaves the reopen-condition history orphaned,
  record one line in the spec §13 review record that the backlog entry was
  removed on resolution.
- [ ] **Step 2:** In the V5b design spec, the "Out of scope" note that
  deferred the four transcript-derived metrics to an engine-side emitter
  gains a supersession note pointing at the V10 spec — the recorded change
  of grounds (`BACKLOG.md:37-44` reopen) and the evals-side offline reader
  that shipped. Preserve the original text; append the note.
- [ ] **Step 3:** `just lint-docs` and `git diff --check` clean.

---

### Task 4: Verification record in `docs/sdd.md`

**Files:**
- Modify: `docs/sdd.md` (append the V10 phase record, V9-pattern)

- [ ] **Step 1:** Run the gate on the implemented tree and record real
  numbers (these are the record's evidence — every number must come from
  a command you ran):
  - `uv run pytest -q` (default-tier count) — must include the new
    `test_pathology.py` and extended contamination/summary/run/rescore
    suites and stay tripwire-green.
  - `uv run pytest -q --cov=satyrn_evals --cov-report=term-missing` —
    100% statement and branch (`fail_under = 100`).
  - `uv run ruff check src tests`; `uv run pyrefly`; `just lint-docs`;
    `git diff --check` — all clean.
- [ ] **Step 2:** Run the two named-evidence commands:
  - the P1 validation-row fixture test (`uv run pytest -q
    tests/test_pathology.py -k validation_row`);
  - one retroactive demonstration: build a run dir with a
    transcript-writing fake, run it, delete the `pathology` key from its
    `summary.json` (simulating pre-V10), run `summarize_output` over it,
    and record that the block returns and the rest of the file is
    unchanged.
- [ ] **Step 3:** Append the phase record to `docs/sdd.md` in the V9
  pattern: what shipped (the offline reader, the seven axes plus
  overlay_windows, whole-cell unmeasured, the shared block on
  run/abort/summarize, retroactive enrichment), the gate numbers from
  Step 1, the named evidence from Step 2, and the corrections recorded
  along the way (the spec's self-review `repeats` correction and the GLM
  5.3 findings — both recorded in spec §13, cited, not restated).
- [ ] **Step 4:** `just lint-docs` and `git diff --check` clean; confirm no
  ROADMAP/backlog claim contradicts the record.

---

## Self-review note for the executor

The spec is binding; where this plan and the spec disagree, the spec wins
and the discrepancy is a plan defect to report. P4 changes no behavior:
if a doc edit requires a code change to stay truthful, stop and report —
that is a plan defect, not an excuse to edit code under a docs slice.
