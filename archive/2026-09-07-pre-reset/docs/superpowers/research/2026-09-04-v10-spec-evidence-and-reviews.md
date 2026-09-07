> **Archived pre-reset record (2026-09-07).**
>
> Original claims, decisions, and instructions may be superseded. This file is evidence, not current guidance.
> For current guidance, read root AGENTS.md, BRIEF.md, and ROADMAP.md. Retrieve one named record when it bears on a concrete question; do not preload this archive.

# V10 — Evidence, recomputation, and review record (spec companion)

Research record accompanying the V10 design spec
(`docs/superpowers/specs/2026-09-04-v10-transcript-pathology-counts-design.md`),
which carries a condensed pointer to this file. Research documents carry
no line cap; the spec and plans do. Content below is the full text the
spec's §12/§13 originally carried, relocated verbatim when the spec was
trimmed to the repository's 400-line cap (2026-09-04, maintainer
instruction: genuine trim, not file-splitting; nothing cut, relocated).

---

## 12. Evidence and recomputation

**Anchors (HEAD `42f0160`):** `Summary` fields and the contamination
section `summary.py:32-47`; `compute_summary` `summary.py:84`; the abort
marker's "same tally" payload `run.py:34-45`; summarize/regrade paths
`rescore.py:112,158`; verbatim-window machinery `contamination.py:20
(GRADER_BLOCK_LINES)`, `:58` (`_nonblank`), `:108-130` (`_match_block`),
`:130` (`scan_patch` with visible subtraction); record codes and the
`transcript_path`/`patch_path` fields `attempt_record.py:41,159-172`;
transcript preservation seam `attempt.py:40`; formats.md summary table.

**Recompute of the §3 validation row** — inspection commands run at spec
time over the preserved V8 smoke transcript (the deep review's §11
sample, `…ladder…md` §11):

```bash
TR=~/projects/satyrn-v8-scratch/smoke2-pwf-20260904-160143/agentclinic-repair-plausible-wrong-fix-20260904-200233-557586/transcript.txt
python3 - "$TR" <<'EOF'
import json, posixpath, sys
from pathlib import PurePosixPath
from collections import Counter
lines = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
cwd = lines[0]["cwd"]
execs = [e for e in lines if e.get("type") == "tool_execution_start"]
print("vocab:", sorted({e.get("type") for e in lines}))
print("tool_calls:", dict(Counter(e.get("toolName") for e in execs)))
pairs = Counter((e.get("toolName"), json.dumps(e.get("args"), sort_keys=True))
                for e in execs)
print("repeats:", sum(n - 1 for n in pairs.values()))
seen, churn = {}, 0
for e in execs:
    if e.get("toolName") in ("edit", "write"):
        a, p = e.get("args") or {}, (e.get("args") or {}).get("path")
        if p is None: continue
        payload = json.dumps(a.get("edits") if e.get("toolName") == "edit"
                             else a.get("content"), sort_keys=True)
        if p in seen and payload != seen[p]: churn += 1
        seen[p] = payload
print("churn:", churn)
noop = sum(1 for e in execs if e.get("toolName") == "edit" and any(
    b.get("oldText") == b.get("newText")
    for b in (e.get("args") or {}).get("edits", []) if isinstance(b, dict)))
print("noop_edits:", noop)
runner = sum(1 for e in execs if e.get("toolName") == "bash"
             and "pytest" in (e.get("args") or {}).get("command", "").split())
print("test_runner_commands:", runner)
ends = [i for i, e in enumerate(lines) if e.get("type") == "turn_end"]
last = ends[-1]
ts = max(i for i, e in enumerate(lines[:last]) if e.get("type") == "turn_start")
parts = lines[last].get("message", {}).get("content", [])
print("terminal text:", any(c.get("type") == "text" and c.get("text", "").strip()
                             for c in parts))
print("execs in final turn:", any(
    e.get("type") == "tool_execution_start" for e in lines[ts:last]))
print("escapes:", sum(1 for e in execs
    if e.get("toolName") in ("read", "edit", "write") and not PurePosixPath(
        posixpath.normpath(posixpath.join(cwd, (e.get("args") or {}).get("path", "")))
    ).is_relative_to(PurePosixPath(cwd))))
EOF
```

The `tool_free_terminal_turns` value combines the last two prints: the
terminal turn has text and no executions inside it, and the smoke cell's
record preserved a patch, so the count is 0.

**Overlay scan (0 windows)** — ran at spec time as a Python window scan
of the transcript against this repo's bundled
`src/satyrn_evals/tasks/agentclinic-repair-plausible-wrong-fix/overlay/`
tree, matching ≥ 4-line raw windows verbatim and subtracting windows that
also appear in the task's `base/` texts (0 hits). The P2 slice re-runs
this through the shipped scan entry; the P1 test fixture reproduces the
validation row — `repeats: 4` breaks down as `read tests/test_app.py` ×3
(+2), `read app.py` ×2 (+1), identical `edit app.py` ×2 (+1) — and the
parser replaces both hand counts.

## 13. Review record

**External review (GLM 5.3, 2026-09-04).** One independent review of
this spec closed with no Critical findings and five Important findings,
all accepted and fixed in place (the findings below are the record, not
the fix list):

1. The `bash` tool name was asserted from the reference surface but never
   verified in the anchor transcript (which shows only `read`/`edit`) —
   an unverifiable tool name could let `test_runner_commands` publish a
   silent zero. Fixed: §1 documents the tool-name set `{read, bash,
   edit, write}` with its verified/assumed split, R3 requires executions'
   `toolName` to be in the set (`unknown_event` otherwise), and the
   vocabulary duty now re-verifies event types **and** tool names (and
the assumed `bash`/`write` argument shapes) against a real
reference-arm transcript before first budgeted use.
2. §3.6's "assistant text" read an undocumented payload shape. Fixed:
   §1 documents the `turn_end` message shape (`role` + content parts
   `thinking`/`text`/`toolCall`) and states that a missing or `text`-less
   message contributes no assistant text under the per-metric-key rule,
   never `malformed`.
3. Churn's comparison and precedence were under-specified. Fixed: §3.3
   now states the equality rule (same stable serialization as repeats),
   cross-tool continuity on a path, and that the axes overlap by design
   (a mixed no-op + changed execution counts both; an identical payload
   is a repeat, never churn); §3.4 states no-op is execution-level and
   orthogonal to churn.
4. `count_transcript`'s signature could not produce `overlay_windows`.
   Fixed: §7/§10 now state that `count_transcript` returns the seven
   transcript-local axes and the shared binder joins the eighth from
   `contamination.py`'s scan (P2), so the P1 slice owns seven axes.
5. §12's recompute did not recompute the row it validated. Fixed: §12's
   command now prints every count in the validation row, and the
   overlay-scan command is recorded.

The four Minor findings were also accepted: §9.5 now says "identical
pathology blocks over the same completed cells" (not identical files),
§3.2 states key order is not significant, R6 states an `agent_end`-only
ending is well-formed, and §3.7 notes that both root and candidate come
from the same document so machine-level root aliasing is never resolved.

**Self-review (2026-09-04).** The author's own review pass, run before
the external review, corrected the §3 validation row's `repeats` (hand
counted 1, recomputed 4 — the two identical `edit app.py` executions
contribute one repeat, and the identical re-reads of `tests/test_app.py`
and `app.py` contribute the rest), replaced wrong file:line anchors
(verified against HEAD `42f0160`), integrated the file-tool `path` rule
into R5 rather than deferring it to the plan, split R6's reasons between
`partial` and `malformed`, and added per-cell read-failure semantics to
§4. The correction is recorded here, not edited away.


**Close-out record (2026-09-04, P4).** The BACKLOG.md "Transcript-derived
summary metrics" entry was removed on resolution per the backlog's own
rule 3 — its outcome lives in ROADMAP row V10 and this spec's §9.9. The
spec's `BACKLOG.md:29-44` / `:34-36` / `:37-44` anchors are superseded
(V7 close-out wording; the V10 spec predates the entry's removal).

**Amendment narratives (post-GLM, from the phase review ledgers).** (a)
R4 turn alternation (2026-09-05): a task review found `count_transcript`
could raise an uncaught ValueError on an R1-R6-passing document whose turn
markers ran reversed (a `turn_end` before its `turn_start`) — an S1
refuse-don't-crash violation. Spec §2 R4 was amended to require strict
alternation (a running balance of `turn_start` minus `turn_end` never
negative); `_structure_ok` enforces it with a discriminating refusal
test. (b) Decoded-payload overlay scan (2026-09-05): a task review proved
`overlay_windows` was structurally always 0 on measured cells — a
well-formed transcript is JSON-escaped, so raw-line matching cannot fire,
and raw echoing makes the cell unmeasured (S1). Shipping a dead detector
would violate BRIEF rule 8. Spec §3.8 was amended so the scanned body is
the transcript's decoded payload text (tool-result content + message
text, newline-joined); the binder scans it for hidden measured cells, and
the detector now fires on a known-bad and stays silent on a known-good.
The payload scope is the maintainer's to rescope.
**Close-out corrections (2026-09-05, maintainer review).** Three defects
found in maintainer close-out, all fixed:
(a) R4 strict alternation — the amended rule allowed nesting
(`turn_start, turn_start, turn_end, turn_end` measured clean); the spec
row now requires strict alternation (no `turn_start` while a turn is
open, no `turn_end` while none is open), and the parser enforces an
open/closed turn state with a nested-start refusal fixture.
(b) R5 toolName pairing — an end event's `toolName` was validated only
for vocabulary, not against its start's; a `read` start closed by a
`write` end measured clean. R5 now requires the paired end to carry the
same `toolName`; mismatch is `malformed` (S1), with a discriminating
refusal test.
(c) run completion-path recoverability — a post-loop overlay failure
raised before either marker was written, stranding preserved cells that
`summarize` (anchor-requiring) could not recover without re-running the
model, while the test's docstring claimed the opposite. `run` now
validates the shared pathology context before the first attempt (broken
overlay = pre-cell refusal, nothing preserved) and the binder runs on
the pre-loaded context; the recovery test proves repair + `summarize`
with zero additional attempt invocations.
