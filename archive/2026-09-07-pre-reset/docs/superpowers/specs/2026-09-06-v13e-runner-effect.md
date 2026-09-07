> **Archived pre-reset record (2026-09-07).**
>
> Original claims, decisions, and instructions may be superseded. This file is evidence, not current guidance.
> For current guidance, read root AGENTS.md, BRIEF.md, and ROADMAP.md. Retrieve one named record when it bears on a concrete question; do not preload this archive.

# V13e — does the test runner buy back the surface deficit? Frozen before the first cell.

**Status: frozen 2026-09-06, before any cell runs.** Exploratory,
diagnostic, admits nothing. Post-pin; never pooled with a pre-pin batch,
and **not pooled with V13d** — the Engine arm's execution path changed.

## 1. The question

V13d measured, on `agentclinic-repair-plausible-wrong-fix` R1 at `n=12`
per arm, interleaved: Baseline **12/12**, Envelope **4/12**, Engine
**6/12**. Removing `bash` and `write` costs 8 of 12 successes
(p = 0.00067). Baseline's `bash` calls are overwhelmingly `pytest`.

`satyrn-engine` E7 (`bc0434a`) adds a `run_tests` tool, registered only
when the contract declares `test_command`; `satyrn-evals` `5ef09fe` emits
it for this task alone. **Does giving the Engine arm the suite recover any
of those 8 successes?**

Not asked: whether the read lock is explained — it is not
(`BACKLOG.md`) — and whether the runner helps on any other task.

## 2. Design, frozen

- Arms `baseline`, `envelope`, `engine`, **interleaved**, `n=12` each,
  36 cells, same task, rung R1, `gemma-4-12B-it-MLX-8bit`, temperature
  1.0 verified both sides, seed recorded before the first cell.
- **All three arms re-run**, though only Engine changed. Baseline and
  Envelope are contemporaneous controls: this project has measured the
  same arm at 7/12 and 2/6 on one task with nothing changed, so a
  cross-batch reference is not trustworthy.
- One uncounted **V5d smoke** first — the Engine execution path materially
  changed. Its pass criterion is **positive evidence**: the transcript must
  show a `run_tests` call that executed the suite and returned output, not
  merely the absence of an error.

> **Amendment, 2026-09-06, before any budgeted cell.** The tool is named
> **`bash`** and takes a `command` argument, not `run_tests` with none, and
> `--tools` now carries its name. The first smoke found the parameterless
> tool was never reachable at all — `--tools read,edit` gates
> extension-registered tools, so every call answered `Tool bash not found`.
> Outcome **D below is therefore already answered**: with the tool
> reachable, three uncounted smoke cells called it 3 times each and ran the
> suite twice each. Rows A–C stand unchanged, read against Engine's 6/12.

## 3. The consequence table, predeclared

Reference: V13d Engine 6/12 (`n=12`, same task, same rung, pre-runner).

| what the Engine arm shows | what it means | what happens next |
|---|---|---|
| **D.** the model never calls `run_tests` | the tool exists and is unused — nothing is learned about runners | the problem is the affordance: the prompt, the tool name, or its description. Fix that before any further runner work |
| **A.** Engine >= 9/12 | the runner recovers a substantial share of the 8-success surface deficit | the runner is the lever; consider `write`/creation next, and re-probe the other tasks |
| **B.** Engine 5–7/12 | the runner does not move outcomes on this task | the deficit is something else — `write`, or the unexplained lock. Do not build more runner affordances on this evidence |
| **C.** Engine <= 4/12 | the runner introduced a new failure mode | diagnose from transcripts before anything else; a capability that lowers the count is a defect |

**D is checked before A–C.** A tool the model does not invoke makes the
other rows meaningless.

Also recorded, kept separate and never pooled: retained patches,
cost-to-succeed in **both** units (tool calls and turn-level `usage`
tokens), and the **unconditional** cost per success — V13d showed the
conditional and unconditional figures pointing in opposite directions.

## 4. Stopping rule

`n` fixed at 12 per arm. No extension after reading, no arm added or
dropped, no change to the tool or the prompt after the first cell.
Interrupted batches resume; incomplete cells are moved aside and logged.

## 5. Limits

- One task, one rung, one model. `plausible-wrong-fix` is the only task
  that declares `public_suite`, by design.
- Baseline still has `write` and Engine still does not, so even outcome A
  would not make the arms surface-equivalent.
- `n=12` distinguishes 6/12 from 11/12 comfortably and 6/12 from 8/12
  poorly; the table's thresholds are set accordingly.
