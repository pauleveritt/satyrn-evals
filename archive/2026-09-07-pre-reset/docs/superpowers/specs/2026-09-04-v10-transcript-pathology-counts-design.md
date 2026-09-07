> **Archived pre-reset record (2026-09-07).**
>
> Original claims, decisions, and instructions may be superseded. This file is evidence, not current guidance.
> For current guidance, read root AGENTS.md, BRIEF.md, and ROADMAP.md. Retrieve one named record when it bears on a concrete question; do not preload this archive.

# V10 — Transcript-derived pathology counts: design spec

**Date:** 2026-09-04.
**Status:** accepted by the maintainer 2026-09-04 with four adjustments
and two schema tightenings (§0); the standing instruction runs spec →
self-review → external review → plan → subagent implementation without a
per-phase confirm round. Self-review and GLM 5.3 review closed with no
Critical findings (§13).

**Amends:** V5b's deferral of the four transcript-derived metrics
(`docs/superpowers/specs/2026-09-02-v5b-diagnostic-loop-design.md:132-136`)
— superseded on the recorded change of grounds in `BACKLOG.md:37-44`; the
`summary.json` schema in `docs/reference/formats.md` (gains a `pathology`
block, §4); ROADMAP row V10 (`ROADMAP.md:98`) status. Supersession notes go
into those files, not edited away.
## 0. Confirmed decisions

The roadmap row (`ROADMAP.md:98`) and the reopened backlog entry
(`BACKLOG.md:29-44`) are the confirmed direction: an **offline reader of
the preserved attempt transcript** — the same relationship `grade` has to
`patch.diff` — counting pathologies per attempt, carried by `summarize`
beside the verdict counts, reporting `unmeasured` (never zero) where the
artifact is absent or unparseable, with no wall-clock and no causal claim.
The maintainer accepted that direction with four adjustments and two
schema tightenings, all binding:

| # | Adjustment / tightening | Effect on this spec |
|---|---|---|
| A1 | **Attempt transcripts only** | Sessions are out of scope; their mapped vocabulary gets its own adapter/mapping design when the session path matters again (§1, §8). |
| A2 | **`test_runs` → `test_runner_commands`** | Command-text evidence only — never proof that tests executed. Match a documented, finite runner pattern (`pytest`); shell aliases, wrappers, and indirect invocations are intentionally out of scope (§3.5). |
| A3 | **No semantic `announce_and_stop`** | Replaced by the structural `tool_free_terminal_turns`: a terminal turn containing assistant text but no tool execution and no retained patch. No prose classifier (§3.6). |
| A4 | **`workspace_escapes` is lexical** | Normalize file-tool paths against the transcript `cwd`; count paths outside that root. No filesystem resolution; symlink traversal and shell-command paths are explicitly unmeasured (§3.7). |
| S1 | **Malformed/partial ⇒ whole-cell `measured: false`** | One bad or partial stream means the whole cell publishes no counts — never partial counts beside a clean-looking zero (§2). |
| S2 | **Tool-call counting by unique `tool_execution_start` ids** | End events are paired only where a metric needs completion semantics. Repeated starts with the same id and unmatched starts are malformed (§2, §3.1). |

The result is a mostly structural, offline parser with exactly one
transparent heuristic — the test-runner command matcher — and no NLP.
## 1. What V10 reads

The preserved **attempt** transcript named by each cell's attempt record:
`record.transcript_path` (`attempt_record.py:159-176`), stored as
`<attempt_dir>/transcript.txt`. On the reference-arm path the attempt
command spools Pi print-mode stream-JSON to `SATYRN_ATTEMPT_TRANSCRIPT`
(`attempt.py:40`); that version-3 stream is the vocabulary V10 parses.
Anything else (a session's mapped transcript, the engine's own spool, a
fake command's arbitrary text) is not this vocabulary and measures `false`
(§2) — the honest output for a non-model transcript, not an error.

**Vocabulary anchor (verified).** The preserved V8 smoke transcript
(`~/projects/satyrn-v8-scratch/smoke2-pwf-*/.../transcript.txt`, the deep
review's §11 recompute source) was inspected whole for this spec. Its
top-level event vocabulary is exactly:

`session`, `agent_start`, `turn_start`, `turn_end`, `message_start`,
`message_update`, `message_end`, `tool_execution_start`,
`tool_execution_end`, `agent_end`, `agent_settled`.

The `session` header carries `version: 3` and `cwd` (the workspace root).
Streaming deltas (`toolcall_*`, `text_delta`, `thinking_*`) appear only
nested inside `message_update.assistantMessageEvent` — payload, never
validated, never counted. The counted unit is the top-level
`tool_execution_start` event (`toolCallId`, `toolName`, `args`); its
matching `tool_execution_end` carries the result. Read/edit argument
shapes are `{"path": ...}` and `{"path": ..., "edits": [{oldText,
newText}, ...]}`.

Two payload shapes the metrics read are documented here (they are inputs
to counts, not free payload):

- **Tool names.** The documented tool-name set is the reference arm's
  surface, `{read, bash, edit, write}`. The anchor verifies `read` and
  `edit`; `bash` and `write` shapes are the surface's own (V11b pins the
  adapter), assumed until a real transcript confirms them (vocabulary
duty). An execution with a `toolName` outside the set is `unknown_event`
(§2 R3) — an unmappable tool must not let `test_runner_commands` publish
a silent zero.
- **The `turn_end` message.** A `turn_end` carries
  `message: {role, content: [{type: thinking|text|toolCall, ...}, ...]}`;
  "assistant text" (3.6) means a `text` part with non-whitespace content
  there (the anchor's final turn has `thinking` + `text`). A missing or
  `text`-less message contributes no assistant text under the
  per-metric-key rule (§2) — never `malformed`.

**Vocabulary duty.** V10's purpose is V12's preserved reference-arm
transcripts (adapter pinned by V11b). Before first budgeted use the plan
must re-verify the vocabulary constant against a real reference-arm
transcript (the V5d smoke's) — **both event types and tool names** — and
confirm the assumed `bash`/`write` shapes; anything the documented set
does not name is added by recorded amendment (with fixtures and tests) or
the cell stays `unmeasured`. The conservative rule is the point: a stream
we only partly understand must not publish clean-looking zeros.
## 2. Document well-formedness; whole-cell `measured: false`

A cell is **measured** only when its transcript satisfies every rule
below; one violation makes the whole cell `measured: false` with a single
reason (S1): no counts are published, and nothing in the block may be a
zero that hides the failure. This is the absence-of-signal rule the
backlog records (`BACKLOG.md:34-36`, citing `…overnight…md:160-162`),
tightened from "where a transcript yields no parseable events" to "where
the stream is absent, empty, unparseable, of unknown vocabulary or
version, or structurally unsound" — a partial stream yields no parseable
*countable* document.

| Rule | Statement | Violation reason |
|---|---|---|
| R1 | Every non-blank line parses as a JSON object | `unparseable` |
| R2 | The first event is `session` with `version == 3` and a non-empty string `cwd` | `unsupported_version` (any other version) or `malformed` (absent/malformed header) |
| R3 | Every event's top-level `type` is in the documented vocabulary (§1), and every `tool_execution_start`/`tool_execution_end` carries a `toolName` in the documented tool set `{read, bash, edit, write}` (§1) | `unknown_event` |
| R4 | Turns bracket executions: the turn markers **strictly alternate**, `turn_start`/`turn_end`/`turn_start`/`turn_end`… — no `turn_start` while a turn is open and no `turn_end` while none is open (no nesting, no reversal; a running balance never negative and never above 1) — at least one full turn; and no `tool_execution_*` event appears before the first `turn_start` or after the last `turn_end` | `malformed` |
| R5 | Executions pair exactly: every `tool_execution_start` has exactly one `tool_execution_end` with the same `toolCallId`, appearing after it and carrying the **same `toolName`** as its start; start ids are unique across the document; `toolName` is a non-empty string; a file-tool (`read`/`edit`/`write`) execution carries a string `args.path` | `malformed` (S2) |
| R6 | The document closes with its terminal: at least one `agent_end` exists; only `agent_settled` may follow it, and then as the final event (ending on `agent_end` with no `agent_settled` is well-formed) | `partial` (no terminal) or `malformed` (a duplicate `agent_end`, or events after the terminal) |

An absent transcript (the record names no `transcript_path`) is
`absent`; an existing file with no non-blank lines is `empty`. Reason set:
`absent`, `empty`, `unparseable`, `unsupported_version`, `unknown_event`,
`malformed`, `partial`.

**Per-metric key requirements are not structural rules.** A documented
tool execution lacking the argument key a metric needs (a `bash` with no
`command`, a `write` with no `content`) is not malformed — it contributes
nothing to that metric (§3). Only the file-tool `path` is structural,
because `churn`, `noop_edits`, and `workspace_escapes` are path-keyed and
the verified vocabulary guarantees a `path` on file tools (R5). Strictness
sits on structure verified against a real document, not on tool argument
shapes that vary across adapters.

**Why whole-cell and not per-count.** A stream with one garbage line
after forty good ones is not 98% measurable: the garbage may be a dropped
or reformatted execution, and forty good lines would publish beside a zero
that reads "measured clean". A cell either reports counts over a document
that satisfied every structural rule, or nothing but a reason. V12 needs
to tell a floor cell "stopped, no patch" from "unmeasured transcript" —
different rows.
## 3. The counts

Counts run over one well-formed cell document (measured cells only). A
measured cell may legitimately have zero of everything except text (an
agent that only talks): all counts `0`, `measured: true` — countable,
distinct from a cell whose stream was unmeasurable. Units are counts of
events or turns — never wall-clock, never tokens, never a causal claim
(row excludes). Where the project recorded a definition, this spec adopts
it verbatim and cites it.

| # | Count | Unit | Definition |
|---|---|---|---|
| 3.1 | `tool_calls` | map | `toolName` → number of unique `tool_execution_start` events (S2). Keys in first-seen stream order. Well-formed documents have exactly one end per start (R5), so no completion semantics are needed here. |
| 3.2 | `repeats` | int | Identical `(toolName, arguments)` executions counted regardless of success — occurrences beyond the first of each identical pair (`BACKLOG.md:29-31`, harvest-index `:69-71`). Identity is on the parsed `args` value compared by equality (`json.dumps(sort_keys=True)`), so list order inside `args` is significant; re-reading the same file and re-issuing the same edit both repeat. |
| 3.3 | `churn` | int | The same target path rewritten with differing content (`BACKLOG.md:31-33`, harvest-index `:74`), kept separate from repeats (handoff `:360`). Count = edit/`write` executions (2nd+) on the same `args.path` whose text payload differs from the immediately previous execution on that path — a later execution counts regardless of the earlier one's tool, so an `edit` following a `write` on the same path with a differing payload is churn (payload shapes differ by construction, so it always is). Payload = `args["edits"]` for `edit`, `args["content"]` for `write`, compared by parsed-value equality with the same stable serialization as 3.2 (`json.dumps(sort_keys=True)`); an execution lacking its payload key contributes nothing. The axes overlap by design: one execution may count in several (an execution with a no-op block *and* a payload differing from its predecessor counts both `noop_edits` and `churn`); an execution whose payload is identical to its predecessor is a `repeat` (3.2) and never churn. A `bash` heredoc write is not counted — churn observes the write tools only (a shell-command limit, A4's cousin). |
| 3.4 | `noop_edits` | int | Edit executions containing at least one `edits` block whose `oldText` is byte-identical to `newText` (harvest-index `:44-46`: "five consecutive edits whose `oldText` was byte-identical to `newText`"). Execution-level and orthogonal to churn (3.3): one no-op block makes the execution a no-op edit; a mixed execution (a no-op block plus a real change) still counts. Only `edit` carries `oldText`/`newText`, so `write` cannot be a no-op edit and contributes nothing. |
| 3.5 | `test_runner_commands` | int | Shell-tool (`bash`) executions whose `command` text contains a whole-token match to a runner name in a documented finite set. The set ships as `{"pytest"}`. Whole token = whitespace-delimited equality after splitting the command (no quoting, alias, or wrapper resolution): `uv run pytest tests/` and `python -m pytest` match; `pt`, `make test`, `./run_tests.sh` do not (A2). The count is command-text evidence that the runner was invoked, never proof that tests executed; aliases/wrappers/indirect invocations are intentionally out of scope and simply not matched. |
| 3.6 | `tool_free_terminal_turns` | int (0/1) | The session's final turn (closed by the last `turn_end`, immediately before the document terminal) contains assistant text — a `text` part with non-whitespace content in its `turn_end` message, per §1's documented `turn_end` shape — and no tool execution within that turn (no `tool_execution_start` between that turn's `turn_start` and `turn_end`), and the cell has **no retained patch** (`record.patch_path is None`, A3). A `turn_end` with no message or no `text` part contributes no assistant text under the per-metric-key rule (§2) — never `malformed`. Structural only: no prose classifier decides what the text "announces". A floored model that stops after a text turn without ever editing counts 1; a model that completes in a final text turn after its edits counts 0 because a patch was retained. |
| 3.7 | `workspace_escapes` | int | File-tool (`read`/`edit`/`write`) executions whose `path` resolves **lexically** outside the transcript `cwd` (A4): the candidate is `cwd / path` when relative, else `path`, `posixpath.normpath`'d, then compared with `PurePath.is_relative_to(cwd)`. No symlink resolution, no home expansion, no shell interpretation; `bash` command paths are not scanned. Both root and candidate come from the same document, so machine-level root aliasing is never resolved: in a session whose `cwd` is `/private/var/...`, a read of `/var/...` counts as an escape even where the OS aliases the two, and symlink-equivalent roots and shell-command paths count only by lexical shape — both failure directions are accepted and documented, never resolved. |
| 3.8 | `loop_broken` | int | Engine `entry_appended` events whose `entry.customType` is exactly `loop_broken`. This counts the loop breaker's explicit refusal telemetry; it is not a tool call and does not affect tool-derived axes. Other `entry_appended` custom types remain unknown vocabulary rather than being silently accepted. |
| 3.9 | `overlay_windows` | int, hidden-oracle cells only | Number of overlay **files evidenced** in a hidden cell's *decoded payload text* — never per sliding window, mirroring `scan_patch`'s per-file first-hit semantics: an overlay file whose non-blank lines fit one window (≤ `GRADER_BLOCK_LINES`) matches as a whole (`whole_file`); a longer file on its first ≥4-line window in overlay line order (`block`), with the model-visible subtraction V7 uses (`contamination.py:20,58,108-130`). The scanned body is the transcript's **decoded** text — the content of `tool_execution_end` result text parts and of message content text parts, newline-joined (amendment 2026-09-05, recorded §13: raw-line matching over the JSON-escaped transcript alone cannot fire on any measured cell, and shipping a dead detector would violate BRIEF rule 8; decoding is part of the definition; the payload scope is the maintainer's to rescope). One `cat` of a hidden file therefore counts once. This closes the deep review's "scan the transcript bytes for overlay windows" option (`…ladder…md:303-305`) for the artifact V7 does not cover (`ROADMAP.md:251-252`). Visible-oracle tasks carry no key (§4). |

**Validation table (spec-time, from the real document).** Counting the
preserved V8 smoke transcript (a successful 12B repair) reproduces the
roadmap record's audit — 6 reads, 2 edits, **0 test runs** (audit; **M3**),
"invisible to `summary.json`" (`…roadmap…md:134-138`) — plus two
pathologies the audit did not count:

```
tool_calls: {read: 6, edit: 2}   repeats: 4   churn: 0   noop_edits: 0
test_runner_commands: 0          tool_free_terminal_turns: 0
workspace_escapes: 0             loop_broken: 0             overlay_windows: 0
```

`repeats: 4` counts every identical execution beyond the first:
`read tests/test_app.py` ×3 (+2), `read app.py` ×2 (+1), identical
`edit app.py` ×2 (+1). `tool_free_terminal_turns: 0` because the final
text turn followed edits that retained a patch (`record.patch_path`
present); `overlay_windows: 0` because the verbatim window scan against
this task's bundled `overlay/` tree, subtracting the `base/` texts, finds
nothing (commands in the §12 research companion). The faithful-good test
fixture reproduces this row.
## 4. Where the counts land

`summary.json` gains a **`pathology` block**: a map keyed by the run's
cell names (`cells`' identity), each value a measured count set or
`{"measured": false, "reason": …}`, in the summary's cell order — the
block is deterministic.

- **Computed by one shared function** over the preserved artifacts — each
  cell's transcript bytes, the record's `patch_path` presence, the task
  manifest and (hidden) overlay, and `base/` texts for subtraction —
  called by `run` (its own summary), the abort marker ("carries the same
  tally a summary would carry", `run.py:33-45`), and `summarize_output`.
  A rebuilt summary is byte-identical to the run's own under the same
  code and artifacts (V9's invariant, extended).
- **Retroactive by re-running `summarize`.** V12 dirs preserved before V10
  have no `pathology` block; `satyrn-evals summarize OUTPUT_DIR` over a
  preserved run rewrites its `summary.json` with the block computed from
  the same transcripts, overlay, and records — the executable form of
  "applied retroactively to V12's preserved transcripts"
  (`…roadmap…md:140-141`). A pre-V10 summary rebuilt under V10 gains the
  block; the formats.md statement of byte-identity is amended to "same
  code and artifacts" so the enrichment is a deliberate, documented change.
- **No run-level aggregate.** A batch mixes measured and unmeasured cells
  (fake-command transcripts, timeouts, refusals); summing across them
  would publish partial totals beside zeros — the exact shape S1 forbids
  at the cell level, refused at the run level for the same reason. V12
  reads per-cell placement; a consumer tallies measured cells only.
- **Per-cell, not per-code.** A refused cell with a transcript is measured
  if its transcript is well-formed; the verdict is not an input to any
  count. Correlation with verdicts happens when the summary is read.
- **Per-cell reads never fail a batch.** A record naming a transcript
  that is missing or unreadable at summary time reports that cell
  `absent` and the summary proceeds: pathology enriches, it does not
grade. Per-cell problems are per-cell unmeasured; only shared task-data
problems (the overlay) are operational.
- **Overlay origin and time-base differ from contamination.** The
  `contamination` tally is receipt-driven (grading-time, stored in the
  receipt); `pathology.overlay_windows` is transcript-driven, computed at
  summary time from the task's *current* overlay and `base/` texts —
  separate sections, never merged. Re-deriving from current task files
  is the currency `summarize` already uses to resolve the task; overlay/
  base drift between run and a later rebuild is a stated limit (a
  rebuilt summary reflects the task as it is when the rebuild runs).
- **Overlay load failure is operational (3), refused before any cell on
  `run`'s own summary path.** `run` validates the shared pathology context
  (the overlay, hidden tasks) **before the first attempt** — a broken
  overlay refuses the run pre-cell (exit 3, nothing preserved, recoverable
  by repair + rerun) — and the binder runs on the pre-loaded context, so
  no shared-context failure can strand preserved cells post-loop
  (close-out correction 2026-09-05, §13 companion). `summarize` loads the
  overlay at rebuild time; a broken overlay there is operational (3) and
  recoverable because the run is already anchored — repair and re-run
  `summarize`.
## 5. CLI surface and exit codes

No new subcommand; no changed exit code. `run`, `summarize` (and the
abort marker) extend their output in place:

    satyrn-evals run TASK [flags] -- COMMAND...      # summary.json gains pathology
    satyrn-evals summarize OUTPUT_DIR [--tasks-root DIR]  # rebuild includes pathology

The exit-code contract is untouched: a run whose cells are all unmeasured
completes `0` with every reason visible in the block — unmeasured is a
reporting state, never an error.
## 6. Data shapes

```json
// summary.json (V10). Every cell in `cells` has one entry, keys in cell
// order. Hidden runs add overlay_windows to measured cells; visible runs
// omit both contamination and overlay_windows (pathology is always
// present — real transcripts exist for visible tasks too).
{ "n": 8, "attempted": 7, "refused": 1, "code_counts": { "…": 0, "OK": 7 },
  "verdict_counts": { "pass": 6, "fail": 0, "unavailable": 1 },
  "task": "agentclinic-repair-plausible-wrong-fix", "command": ["…"],
  "timeout": 900.0, "oracle_visibility": "hidden", "cells": ["…", "…"],
  "contamination": { "graded": 7, "flagged": 0, "clean": 7, "unmeasured": 0 },
  "pathology": {
    "<cell-a>": { "measured": true,
      "tool_calls": { "read": 6, "edit": 2 },
      "repeats": 4, "churn": 0, "noop_edits": 0,
      "test_runner_commands": 0, "tool_free_terminal_turns": 0,
      "workspace_escapes": 0, "loop_broken": 0, "overlay_windows": 0 },
    "<cell-b>": { "measured": false, "reason": "partial" },
    "<cell-c>": { "measured": false, "reason": "absent" }
  } }
// aborted.json: the completed cells' pathology block rides the same
// tally payload run writes for a completed summary.
```

House style: `type` aliases; frozen dataclasses or plain dicts per module
purity; `match` over the reason set; walrus where bound-and-tested. The
parser is pure (text in, result out), so the default tier exercises every
branch with no model, network, or subprocess.
## 7. Module shape and test layout

- **`src/satyrn_evals/pathology.py`** — the parser and counters: the
  vocabulary and tool-name constants, R1–R6 well-formedness,
  `count_transcript(text, *, had_patch) -> CellPathology` returning the
  **eight transcript-local axes** (`tool_calls`, `repeats`, `churn`,
  `noop_edits`, `test_runner_commands`, `tool_free_terminal_turns`,
  `workspace_escapes`, `loop_broken`), and per-metric helpers. Pure; no I/O.
- **`contamination.py`** — one added scan entry (`scan_transcript`,
  transcript as the scanned body, reusing `_nonblank`/`_match_block`/
  `GRADER_BLOCK_LINES` + visible subtraction) returning matched windows;
  no behavior change to existing checks. `overlay_windows` (the eighth
  axis) is produced here, not by `count_transcript` — the scan needs the
  overlay spec and `base/` texts, which the pure parser does not take.
- **`summary.py` / `run.py` / `rescore.py`** — the `pathology` field on
  `Summary`; one shared artifact binder (loads each cell's transcript and
  record, runs `count_transcript`, joins the scan for hidden tasks, hands
  the map to `compute_summary`/`write_summary`) on all three write paths.
- **Fixtures** under `tests/data/v10/` (`norecursedirs` excludes
  `tests/data`, `pyproject.toml:52`): synthetic-but-faithful JSONL in the
  §1 vocabulary — the good repair document reproducing the §3 row; one
  per pathology; one per R1–R6 violation; an empty file; a truncated
  stream; a non-Pi text transcript. Synthesized from the verified
  schema, not byte-copied from the scratch transcript.
- **Default-tier tests only** (pure text/JSON/file processing; no
  integration tier). `test_pathology.py` for the parser; summary/run/
  rescore tests extended for the block; overlay tests in
  `test_contamination.py`. Every refusal has a sibling success; every
  detector fires on a known-bad from the same batch and stays silent on
  the known-good (`BRIEF.md` rules 6, 8); the tripwire stays green.
## 8. Non-goals

- Session transcripts and the session path (A1) — frozen until a consumer
  needs them; their mapped vocabulary is a separate design.
- The engine telemetry seam, `facts`, or any engine-side emitter; any
  run-time seam change (row excludes).
- Wall-clock, token/context metrics, or any causal claim from counts.
- Semantic `announce_and_stop`; prose classification of any kind (A3).
- Filesystem-resolution escape detection: symlink traversal, shell-command
  paths (A4); a bash `cd` out of the worktree is not counted.
- Bash-path scanning beyond the runner matcher; runner detection beyond
  the documented token set (aliases, wrappers, indirect invocation).
- Storing pathology at attempt time or changing the attempt record or
  transcript schema (the retroactive summarize path is the mechanism).
- A run-level pathology aggregate (§4); publishing partial counts for a
  malformed/partial cell under any condition (S1).
- `regrade` never recomputes pathology: it rewrites receipt + record
  only; the block is a summary artifact rebuilt by `summarize`.
- New CLI surface, exit codes, task fixtures, or model runs.
## 9. Done-when

1. The parser enforces R1–R6 with the closed reason set; each violation
   has a fixture and a refusal/success sibling; the faithful-good document
   reproduces the §3 validation row exactly (including `repeats: 4`).
2. Whole-cell unmeasured (S1): any malformed/partial/unknown-vocabulary/
   unsupported-version/empty/absent cell publishes only
   `{"measured": false, "reason": …}` — a test asserts no count key
   coexists with `measured: false`.
3. Each count's boundary is pinned by a known-bad/known-good pair from
   the same fixture batch (rule 8): repeat vs distinct; churn vs repeat
   vs no-op; no-op firing; `pytest` token with `pt`/`make test`/wrapper
   silence; 0/1 terminal-turn both directions; lexical escape on
   `..`/absolute-outside with same-root-absolute and in-root `..`
   silence.
4. Hidden-oracle `overlay_windows`: overlay content fires once per file
   evidenced (a whole-file cat of a short hidden file counts 1); a
   window shared with `base/` does not (visible subtraction);
   visible-oracle cells carry no key.
5. `summary.json` carries the block through the one shared computation:
   identical over the same completed cells in `run`'s summary,
   `aborted.json`, and a `summarize` rebuild (byte-identical files where
   the surrounding payload is identical too); a pre-V10 summary
   re-summarized under V10 gains the block (refusal/success siblings).
6. No run-level aggregate; mixed measured/unmeasured batches keep
   per-cell truth only.
7. A broken overlay on a hidden task is operational (3): `run` refuses
   pre-cell (nothing preserved) and `summarize` fails at rebuild with the
   run anchored; repair + rerun/summarize recovers with zero new attempts
   (the recovery test proves it); a readable hidden run summarizes with
   the block.
8. Default tier model/network/subprocess-free (tripwire green); 100%
   statement-and-branch gate; ruff, pyrefly, lint-docs, `git diff
   --check` clean.
9. Docs current: formats.md, ROADMAP row, BACKLOG close-out, V5b note;
   verification record in `docs/sdd.md`.
## 10. Reviewable slices (plan files)

1. **Parser** (P1) — `pathology.py`: vocabulary + tool-name sets,
   R1–R6, the eight transcript-local axes, fixtures, tests, validation
   row. (`overlay_windows` is not a P1 deliverable — the scan is P2,
   the binder joins it in P3.)
2. **Overlay scan** (P2) — `contamination.py` `scan_transcript`,
   hidden-only wiring, visible subtraction, visible-task omission.
3. **Summary integration** (P3) — `Summary.pathology`, the shared
   binder, run/abort/summarize byte-identity, retroactive enrichment.
4. **Docs and record** (P4) — formats.md, ROADMAP row, BACKLOG
   close-out, V5b supersession note, verification record in `docs/sdd.md`.

Each slice lands with its tests and refusal/success siblings; no slice
commits itself (commits are maintainer-controlled).
## 11. Verification record shape

V9 pattern (`docs/sdd.md`): default-tier counts; the 100% branch gate;
ruff/pyrefly/lint-docs/`git diff --check`; named evidence — the
faithful-good fixture reproducing the §3 row, one retroactive `summarize`
demonstration over a preserved fixture run, and (once at verification,
not CI) the V10 counts over the preserved V8 smoke transcript, matching
the research record's 6/2/0 shape plus the two newly counted
pathologies.
## 12. Evidence and recomputation

**Anchors (HEAD `42f0160`):** `summary.py:32,84`; `run.py:34`;
`rescore.py:112,158`; `contamination.py:20,58,108-130`;
`attempt_record.py:41,159-172`; `attempt.py:40`; formats.md summary table.

**Recompute:** the §3 validation row and the verbatim overlay scan (0
windows) recompute from the preserved V8 smoke transcript; full commands
in `docs/superpowers/research/2026-09-04-v10-spec-evidence-and-reviews.md`.
The P1 fixture `tests/data/v10/good-repair.jsonl` reproduces the row
(`repeats: 4` = `read tests/test_app.py` ×3 +2, `read app.py` ×2 +1,
identical `edit app.py` ×2 +1); the parser replaces the hand counts.
## 13. Review record

Self-review and the GLM 5.3 review (2026-09-04) closed with no Critical
findings; all Important and Minor findings were accepted and fixed in
place — every finding, the fix each produced, and the `repeats`
correction are in `docs/superpowers/research/2026-09-04-v10-spec-evidence-and-reviews.md`;
the amendments this spec carries (§0 A1–A4/S1–S2, §2 R5/R6, §3.3–§3.8,
§4) are the accepted findings made binding.
