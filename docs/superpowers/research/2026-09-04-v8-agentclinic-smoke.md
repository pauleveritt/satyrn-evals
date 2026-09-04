# V8 smoke — AgentClinic repair through the stock engine: FAILED on the engine↔pi argv seam

**Date:** 2026-09-04
**Status:** V5d smoke, uncounted, **failed on plumbing** — the qualified evals path was not
exercised end to end because the stock engine could not launch pi. The engine-side
incompatibility is recorded here, not fixed (engine changes are excluded from V8).
**Task:** `agentclinic-repair-plausible-wrong-fix` (all six tasks' offline qualification is
green — 24/24 gate — so this is the sole uncounted real-model run of the phase).
**Model:** `omlx/gemma-4-12B-it-MLX-8bit` (the V6 smoke model; served by the local omlx
server at `127.0.0.1:8001`, already running). **Pi:** 0.84.4.

## Evidence

Durable, uniquely named:

```text
~/projects/satyrn-v8-scratch/smoke-pwf-20260904-155224/
  engine-contract.yaml            # authored for the smoke (block-scalar task)
  evals-attempt.log               # the evals attempt invocation
  agentclinic-repair-plausible-wrong-fix-20260904-195250-781313/attempt.json   # refusal 1
  agentclinic-repair-plausible-wrong-fix-20260904-195324-336128/attempt.json   # refusal 2
```

## What was run

The stock-engine seam per V8 spec §7: `satyrn-evals attempt TASK --output DIR -- satyrn-engine
attempt --model omlx/gemma-4-12B-it-MLX-8bit engine-contract.yaml`, from the `v8-agentclinic`
worktree, engine invoked through its own project (`uv run --project ~/projects/…/satyrn-engine`).

## The two refusals, and the isolated defect

1. **Attempt 1** (record `…-195250`): the engine refused before any model interaction with
   `CONTRACT_INVALID_YAML` — my smoke-authored contract embedded `307 == 303: …` unquoted in a
   YAML scalar. Operator error, same class as the recorded V5c engine-contract bug
   (`BACKLOG.md`, "Engine-contract content is never validated"); the engine's refusal was
   correct. Contract rewritten as a YAML block scalar.
2. **Attempt 2** (record `…-195324`, engine exit 10): with the corrected contract, the engine
   reached its pi launch and pi exited 1 with `Error: Unknown option: --model`.

**Isolated reproduction (the engine defect).** `satyrn-engine`'s `build_pi_command` emits the
pi model as the equals form `f"--model={model}"` (`satyrn-engine/src/satyrn_engine/attempt.py`,
`build_pi_command`). pi 0.84.4's print/json mode **rejects the equals form** but accepts the
same model in space form with the engine's entire remaining flag shape:

```bash
pi --print --mode json --no-session --model omlx/gemma-4-12B-it-MLX-8bit "x"        # OK
pi --print --mode json --no-session --model=omlx/gemma-4-12B-it-MLX-8bit "x"       # Unknown option: --model
pi --print --mode json --no-session --model omlx/gemma-4-12B-it-MLX-8bit \
   --no-extensions --no-skills --no-prompt-templates --no-themes --no-context-files \
   --no-approve --tools read,edit "Reply with exactly: OK"                          # OK — real turn starts
```

This is the recorded engine-side "pi argv incompatibility" (`ROADMAP.md` V5d Excludes;
satyrn-engine `BACKLOG.md`), surfaced here with a one-character repro: equals vs space form.

## V5d checklist outcomes

1. **Model config accepted?** NO via the engine path — pi rejected the engine's argv before
   any model interaction. The model server itself and pi's space-form invocation are verified
   working (a real gemma turn started in the reproduction).
2. **Attempt record read always** — YES: both attempt records read (`NO_PATCH` refusals with
   the engine's exit codes and empty transcripts — no patch, no transcript delivered).
3. **Receipt only when grading ran** — N/A: no patch was ever delivered, so grading never ran.
4. **Positive evidence the model started?** NONE via the engine path — the deciding V5d
   criterion. The smoke therefore **fails** on plumbing. It is not a model-behavior result and
   no admission, difficulty, or quality claim is made or implied.
5. **Teardown/durability** — clean: evidence durable and uniquely named as above.

## What this does and does not establish

- **Does not** exercise the qualified evals path (materialized hidden-oracle attempt through
  the stock engine) with a real model — the phase's single smoke is unearned until the engine
  seam launches pi on this machine.
- **Does** prove the offline qualification stands independently (24/24 gate, 100 % coverage),
  and records a precise, reproducible engine-side defect that blocks the engine arm.
- **Next step (outside V8):** the engine's `--model=` equals form must accept pi 0.84.4 (or pi
  must accept the equals form) before the smoke can be re-run; the smoke is then re-attempted
  uncounted under the same V5d rules. Per spec §7 engine defects are recorded here, not fixed
  in V8.

## Second smoke — the engine fix, PASS (2026-09-04)

The maintainer fixed the recorded engine defect: `satyrn-engine` `build_pi_command`
now emits pi's model as separate tokens (`"--model", model`), with its precise unit
expectation updated (`satyrn-engine` commit `d5d5d37`, branch
`research/facts-field-backlog`). The first timed-out run also surfaced that evals'
`attempt` default command timeout is 30 s (`workspace.py:28`), so the smoke re-ran
with `--timeout 1800`.

Evidence (durable, uniquely named):

```text
~/projects/satyrn-v8-scratch/smoke2-pwf-20260904-160143/
  engine-contract.yaml  evals-attempt2.log
  agentclinic-repair-plausible-wrong-fix-20260904-200233-557586/
    attempt.json  patch.diff (372 B)  transcript.txt (92,801 B)  receipt.json
```

**Verdict: pass.** The five assertions, evidenced from the retained artifacts:

1. **Model accepted config and acted** — 92,801-byte transcript: one session, 9
   turns, 18 messages, 95 `message_update` events, 8 `tool_execution` pairs,
   `agent_settled`; a genuine streamed model session, not a stub.
2. **Attempt record read** — `outcome: attempted`, `code: OK`, `command_exit: 0`.
3. **Receipt read (grading ran)** — verdict `pass`, 13/13
   (`evidence.counts.passed == 13`), reason empty.
4. **Patch + transcript preserved before cleanup** — both on disk in the attempt
   dir; the patch is a real, minimal, correct repair (`RedirectResponse("/complaints")`
   → `status_code=303`), i.e. the model found and fixed the seeded bug. Recorded as
   model behavior, no quality/admission claim.
5. **Teardown clean** — exit 0, record written, workspace released.

**Environment attestation:** `resolved_versions` on the receipt names 47 installed
distributions of the materialized oracle env — `fastapi 0.115.10`, `pytest 8.3.4` —
and the contamination check is `clean` (the model never copied hidden-overlay
content). This is the dependency-bearing hidden-oracle single-shot path through the
stock engine, offline-graded through the locked project environment: the qualified
path V8 set out to prove works end to end.
