# Frozen conditions: bounded Baseline session, session-ordering-regression

Written before the run. **Baseline only. No comparison, no Engine arm** — no
Engine session arm exists (the mutator and runner assume one frozen contract
with a `test_command`; a session has no per-prompt contract).

## Purpose

Establish that the workload **exercises the cross-prompt dependency** it was
built for: that a later request can regress an earlier request's feature and a
base behaviour, and that the retained checkpoints show it. Judged by the
intended behaviours and the retained evidence, **not** by a context-occupancy
threshold. Low context occupancy would not show the app cannot expose
cross-prompt failures.

## Conditions

| | |
|---|---|
| task | `session-ordering-regression` |
| arm | Baseline only (`satyrn-evals-session-pi`) |
| adapter argv | `satyrn-evals-session-pi --provider omlx --model gemma-4-12B-it-MLX-8bit` |
| model | `gemma-4-12B-it-MLX-8bit`, local at `127.0.0.1:8001` |
| sessions | **1** |
| **effective tool surface** | **`read,bash,edit,write`**, with extension, skill, prompt-template and context-file discovery all disabled |
| delegation | **disabled** — no `subagent`, verified from the transcript after the run |
| step timeout | 600 s |
| start / close timeout | 60 s / 30 s |

## Stopping rules

One session is the whole budget. **No re-run on an unfavourable outcome.** An
ordinary failed repair, a scope violation, or a model that never reaches the
last prompt are all valid observations and are reported as they occur.
Infrastructure failure — the adapter or pi exiting before the model runs, no
genuine model-stream events, a plumbing code where a model outcome was
expected — stops the run and the evidence is retained.

> **Amended 2026-09-08, after the first run.** The first version of this
> record had **no tool-surface row**, and that omission is why the run is not
> counted: the adapter passed no `--tools`, the model reached the installed
> `pi-subagents` extension, and a **detached worker** wrote files across two
> checkpoint boundaries with no retained events. The R1 pre-run record froze
> tools per arm and this one did not. The rows above are the repair; the first
> run's record is retained separately and unchanged.

## What is read afterwards

1. `session-record.json` parses, and records the terminal reason.
2. Genuine model-stream events are present in the retained payloads.
3. One conversation is maintained across the prompts reached
   (`conversation_id` identity).
4. Per-checkpoint artifacts exist for the prompts reached: patch, snapshot,
   transcript prefix.
5. **Per-checkpoint feature and preservation verdicts**, which is the new
   coverage — whether a regression appears at the checkpoint that caused it.
6. Per-step turn and tool counts, and context accumulation across steps.
7. **The effective tool surface, read from the transcript** — every tool name
   the model actually called, checked against the allowlist above. A name
   outside it, or any dispatch of a detached worker, voids the run's evidence
   rather than merely annotating it.

## What this cannot establish

Anything about Engine versus Baseline. Any success rate — `n=1`. Any claim
about difficulty. Whether compaction fires under legitimate accumulation is a
separate, later question, and if it is ever asked the evidence must be the
observed compaction event and the requirements before and after it, not a
fraction of the window.
