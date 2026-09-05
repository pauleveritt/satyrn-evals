# The Baseline V5d smoke, the V10 amendment it forced, and the measured token floor

**Date:** 2026-09-05. **Status:** the Baseline smoke passed on its second
reading, after a V10 defect it exposed was fixed and the **same preserved
transcript** was re-scored with no model re-run.

Smoke evidence (durable, uniquely named):
`~/satyrn-smokes/2026-09-05-v11-trim/baseline/`.

## 0. Why `depth-2`, and not a mini-probe candidate

The smoke ran `agentclinic-repair-depth-2` at R1. That task is **not** one of
the three V11c mini-probe candidates (`plausible-wrong-fix`,
`misleading-locus`, `depth-3`), so no Baseline outcome on a candidate was
observed before the frozen selection rule runs. Deliberate: the firewall is
cheaper to keep than to argue about afterwards.

## 1. What ran

```bash
uv run satyrn-evals run agentclinic-repair-depth-2 --rung R1 --n 1 \
  --output ~/satyrn-smokes/2026-09-05-v11-trim/baseline \
  -- satyrn-evals-attempt-pi --model omlx/gemma-4-12B-it-MLX-8bit \
     --tools read,bash,edit,write
```

The whole V11a+V11b substrate exercised at once: `--rung R1` selected the
authored rung, the generated engine contract was written to a digest-keyed
path and appended to the command, the in-tree adapter ran pi, and the patch
and transcript were preserved and graded offline.

**Outcome:** `OK` / verdict `fail`, 1 attempt, 0 timeouts,
`contamination: clean`, `rung: "R1"`,
`contract_digest: faa17bbc…`. A `fail` verdict is a **pass for a smoke** —
V5d asks whether the path runs and records, not whether the model solved the
task.

## 2. The defect it exposed — precondition 2 failed

The first reading returned:

```json
"pathology": {"…": {"measured": false, "reason": "unknown_event"}}
```

Cause, counted from the transcript rather than guessed:

| event type | count |
|---|---|
| `tool_execution_start` | 23 |
| `tool_execution_end` | 23 |
| **`tool_execution_update`** | **49** |

`tool_execution_update` was **not in V10's `EVENT_TYPES`**, so one unknown
type made the whole cell unmeasured. This is exactly the failure the V11b
spec §8 predicted from the eight preserved 2026-09-03 Baseline reprobe
transcripts — **a non-empty transcript is not proof V10 can measure it** —
and V11c precondition 2 stopped the run as designed.

Recompute:

```bash
python3 -c "import json,collections,sys;print(collections.Counter(
  json.loads(l)['type'] for l in open(sys.argv[1]) if l.strip()))" \
  ~/satyrn-smokes/2026-09-05-v11-trim/baseline/*/transcript.txt
```

## 3. The amendment

`tool_execution_update` is a **streaming partial** of an execution its
start/end pair already brackets — 49 updates against 23 real executions,
~2 per call. So it is **recognised and counted as nothing**. Counting it
would have roughly doubled every cell's `tool_calls`.

Its payload *is* validated: an update carries a real `toolName`, so the
vocabulary check now runs over `tool_execution_update` alongside start and
end, and an unknown tool name in an update still returns `unknown_event`.

Discriminating fixture and tests, both directions, in
`tests/test_pathology.py`: the update shape measures; two updates on one call
still count one `bash`; an update naming an unknown tool is still
`unknown_event`; and a genuinely unknown type is still `unknown_event` — the
vocabulary widened by exactly one member, not into a check that accepts
anything.

## 4. Re-scored offline, with no model re-run

```
uv run satyrn-evals summarize ~/satyrn-smokes/2026-09-05-v11-trim/baseline
```

```json
"measured": true,
"tool_calls": {"bash": 17, "read": 5, "edit": 1},
"repeats": 5, "churn": 0, "noop_edits": 0,
"test_runner_commands": 8, "tool_free_terminal_turns": 0,
"workspace_escapes": 0, "overlay_windows": 0
```

17 + 5 + 1 = **23**, matching the 23 start/end pairs: the updates counted as
nothing, as designed.

**This is `BRIEF.md` rule 3 doing the job it was written for.** A grading
defect was found, fixed, and re-scored against a preserved artifact without
spending a single model call. The rule is why the smoke cost one cell instead
of two.

## 5. The measured per-cell input-token floor — 1,546

Precondition 4, satisfied from inside a materialized workspace:

```
uv run python scripts/token_floor.py <transcript> --record <record>
input-token floor: 1546 (from usage.input)
```

**The reader's refusal did its job first.** pi's usage shape was unknown to
this repository, so `token_floor.py` refused rather than reporting zero and
**named what it saw** — `usage.input`, `usage.output`, `usage.reasoning`,
`usage.cacheRead`, `usage.cacheWrite`, `usage.totalTokens`. The artifact
taught us the key; recall did not supply it.

**A correction inside that measurement.** The first pass then read
`usage.input == 0` and refused again — correctly. pi streams
`message_update` events whose usage block is not yet populated: **217 events
carry usage and only 68 carry a positive input count.** A zero there means
"not filled in yet", not "zero tokens". Placeholders are now skipped, and an
all-zero transcript is still refused rather than reported as a floor of 0.

1,546 sits where §4 of the context-file record predicted: near the 686–1,267
floor plus real task content, and nowhere near the 13,645 that a repo-root
measurement suggested. It supersedes every repo-root figure as the Envelope
cap input.

## 6. A claimed detection gap — RETRACTED the same day

**This section originally claimed a hole in the contamination scan. The claim
was wrong in every particular, and is retracted rather than edited away.**

What it said: that `decoded_scan_text` (`pathology.py:100-130`) never reads
`tool_execution_update.partialResult.content`; that of 17 tool calls with
partials, "16 were contained in their end result and one was not"; that
`call_f0418a3d`'s partial and end "diverge after 37 characters" and carry
"differently ordered" content; and that therefore "text a model saw in a
stream can be absent from the scanned body."

What an independent review (Fable, 2026-09-05) established:

- **"16 of 17" reproduces under no stated rule.** Every-partial-contained is
  **15/17** (both 51 KB calls fail); last-partial-contained is **17/17**.
- **"Diverges after 37 characters" is not a finding.** 37 is exactly
  `len("./.venv/lib/python3.14/site-packages/")` — a shared path prefix.
- **"Differently ordered" is false.** pi's bash tool streams a sliding 50 KB
  tail window. Against the retained full log
  (`pi-bash-cd2e313d34ce3696.log`, 1,557 lines) the partials begin at lines
  86, 636, 1011, 1244 and the end result is lines 1244-1557. Same order,
  scrolled — 853 lines scrolled out of the end result.
- **The conclusion inverts.** The `toolResult` message the model actually
  received is **byte-identical to the end result** for both calls. Partials
  never enter model context. Scanning them would add text the model never
  saw — **false positives in a contamination tripwire**, not a closed hole.

Corrected statement: an end event is not a superset of its partials
**because of truncation**, and the end result is exactly the right scan body
for the question `overlay_windows` asks, which is *what the model saw*.

**How the error was made, since that is the reusable part.** A containment
check was run over strings whose shared prefix was a filesystem path, the
divergence point was read as semantic rather than lexical, and the result was
generalised into a detector gap without ever checking what the model was
actually handed. `BRIEF.md` rule 8 asks whether a detector fires on a
known-bad and stays silent on a known-good; the discarded step here was
asking what the detector is *for*.

## 7. Precondition state after this smoke

| # | Precondition | State |
|---|---|---|
| 1 | V11a + V11b landed, full gate green | **met** |
| 2 | Baseline smoke passed, pathology `measured: true` | **met, after the §3 amendment** |
| 3 | Engine smoke on a generated contract | **met** — repaired Engine `25ca0be` exited 0 on a generated contract, preserved its transcript and patch, and recorded five recognised `loop_broken` events at `~/satyrn-smokes/2026-09-05-v11-post-landing-engine-rerun/` |
| 4 | Per-cell input-token floor measured in a workspace | **met — 1,546** |
| 5 | `preflight.sh` green | **met** — post-landing preflight evidence at `~/satyrn-smokes/2026-09-05-v11-post-landing/` |
