# local-pings re-probe — pre-registered protocol

**Date:** 2026-09-03. **Status:** pre-registered; no model run before this
commit. **Branch:** `research/local-pings-reprobe`.

## Purpose

V5c recorded that `local-pings`'s admission numbers — Baseline 0/4,
Envelope 0/4, Engine 2/4, retained-patch 2/2 (V5a spec's index) — are
**unearned**: they were graded under the superseded four-test oracle at the
N=2 fixture, and the captured task's oracle is now five ids at an N=6
fixture. This probe re-runs the arms that carry V5a's admission against the
captured task, so the numbers are either re-earned or revised. It is also
the first real execution of V5b's `run --n 8` loop with a model rather than
a fake seam.

## Arms (fixed before the run)

- **Baseline** — bare Pi: `pi --print`, no Engine, no extensions, no skills,
  no handoff contract. Tools `read,bash,edit,write`. Prompt = the task
  contract only. Run through a minimal seam wrapper that harvests the
  worktree `git diff` to `SATYRN_ATTEMPT_PATCH` and Pi's stream to
  `SATYRN_ATTEMPT_TRANSCRIPT` (wrapper source below).
- **Engine** — `satyrn-engine attempt` (E5 composite: engine and mutator
  extensions, loop breaker, bounded replacement). Tools `read,edit` per the
  engine's own `build_pi_command`.
- **Envelope — deliberately deferred, recorded, not run.** V5a's admission
  rests on at least one pair separating, which is Baseline floor vs Engine
  middle; the follow-up recorded its Envelope as a budget-only variant of
  the broader tool surface, not the canonical `read,write` Envelope
  (`2026-08-27-local-pings-envelope-engine-followup.md:24-27`). Re-running
  it would triple nothing useful. *Reopens under a canonical-Envelope
  definition.*

n = **8 per arm, 16 attempts total** (V5b's fixed count; no mid-run
stopping — the run loop executes all n and the summary is counts-only).

## Model and backend (recorded, not guessed)

`omlx/gemma-4-12B-it-MLX-8bit` — the model every recorded local-pings probe
used (`2026-08-27-local-pings-corrected-probe.md`, `...-envelope-engine-followup.md:5`),
served by this machine's local oMLX server at `127.0.0.1:8001` (verified
up; the model id appears in `/v1/models`). No API cost; local inference.

## Measurements (fixed before the run; never switched after)

Mirroring the corrected probe's three-way split, in this repository's own
terms:

1. **Primary — successful-attempt outcome per arm:** attempts whose record
   outcome is ACCEPTED (completed within the deadline and delivered a
   parseable patch and a non-empty transcript), reported as X/8. A timeout,
   a no-patch exit, an unparseable patch, or a missing/empty transcript is
   a refusal, not a success — even when the retained patch later grades
   pass. This is the metric the admission bar reads.
2. **Retained-patch production per arm:** attempts whose preserved
   `patch.diff` is non-empty, counted separately (a timed-out attempt may
   retain a patch; that is production, not completion).
3. **Conditional retained-patch quality:** offline grade of every retained
   patch against the captured task's five-id oracle (pass/fail), kept
   separate from completion — a patch that passes does not turn a refusal
   into a success, and a completed-but-wrong attempt is a completion whose
   conditional quality fails.

The verdict never comes from stdout or an exit code: attempt records,
receipts, and the summary.json (V5b's counts-only shape) are the record.

## Conditions

- **Deadline:** 900 seconds per attempt (`run --timeout 900`), matching the
  recorded probes.
- **Isolation:** one eval-owned detached worktree per attempt (V4/V5b
  machinery); patch and transcript are preserved before cleanup by the
  attempt loop itself.
- **Task:** the captured `local-pings` task (five-id oracle) on branch
  `v5c-capture-admitted-suite`, graded offline after each attempt.
- **Backend env:** `SATYRN_MODEL=omlx/gemma-4-12B-it-MLX-8bit`;
  `SATYRN_ENGINE_REPO=/Users/pauleveritt/projects/pauleveritt/satyrn-engine`
  (Engine arm only).

## Sequence and commands

1. **Smoke, one `--n 1` per arm, results not counted** — plumbing before
   budget: the first time V5b's loop executes with a real model. A bug found
   on attempt 1 costs one attempt; on attempt 12 it muddies the record.
2. Then the arms, n=8 each.

```bash
# Engine arm (env + command)
cd <evals worktree>
SATYRN_MODEL=omlx/gemma-4-12B-it-MLX-8bit \
SATYRN_ENGINE_REPO=/Users/pauleveritt/projects/pauleveritt/satyrn-engine \
  .venv/bin/satyrn-evals run local-pings --n 8 --timeout 900 \
  --output scratch/runs/engine -- /Users/pauleveritt/projects/pauleveritt/satyrn-engine/.venv/bin/satyrn-engine attempt

# Baseline arm
SATYRN_MODEL=omlx/gemma-4-12B-it-MLX-8bit \
  .venv/bin/satyrn-evals run local-pings --n 8 --timeout 900 \
  --output scratch/runs/baseline -- python3 <baseline wrapper>
```

## Baseline wrapper source (recorded here; executable lives in the durable
scratch `~/projects/pauleveritt/satyrn-v5c-scratch/arms/baseline_pi.py`)

```python
import argparse, os, subprocess, sys

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("contract", nargs="?")  # evals appends the engine-contract path
    p.add_argument("--model", default=os.environ.get("SATYRN_MODEL"))
    args = p.parse_args()
    assert args.model, "SATYRN_MODEL required"
    patch_path = os.environ["SATYRN_ATTEMPT_PATCH"]
    transcript_path = os.environ["SATYRN_ATTEMPT_TRANSCRIPT"]
    prompt = os.environ.get("SATYRN_TASK_CONTRACT", "")
    cmd = [
        "pi", "--print", "--mode", "json", "--no-session",
        "--model", args.model,  # space form: pi 0.84.x rejects --model=VALUE
        "--no-extensions", "--no-skills", "--no-prompt-templates",
        "--no-themes", "--no-context-files", "--no-approve",
        "--tools", "read,bash,edit,write", prompt,
    ]
    with open(transcript_path, "wb") as tf:
        proc = subprocess.run(cmd, stdout=tf, stderr=subprocess.STDOUT)
    diff = subprocess.run(["git", "diff", "HEAD"], capture_output=True, text=True)
    open(patch_path, "w").write(diff.stdout)
    sys.exit(proc.returncode)

if __name__ == "__main__":
    main()
```

(Minor drift between this recorded source and the executable is a
recording defect, not a re-run — the executable is the one that ran.)

## Recording plan

Attempt directories (patch, transcript, receipt, attempt.json) and each
arm's `summary.json` are the raw record, preserved under
`~/projects/pauleveritt/satyrn-v5c-scratch/runs/{arm}/`. The three
measurements above are computed from attempt records, plus an offline
re-grade of every retained patch. Results append to this file as a dated
result section; the admission caveat in the V5a spec is updated only by
what the numbers show.

## Smoke findings (2026-09-03; each cost one attempt, per the protocol)

Smoke ran before the arms and caught three plumbing defects, exactly its
job. None is a model-behavior finding; all are recorded here:

1. **The captured task's `engine-contract.yaml` was invalid YAML** — the
   unquoted `task:` value contained a colon-plus-space, which the engine's
   `check` refused as `CONTRACT_INVALID_YAML` (exit 4) before any model
   ran. Fixed by quoting the value; committed.
2. **The Engine composite's pi child argv is incompatible with pi 0.84.x's
   hand-rolled arg parser.** `satyrn-engine` builds `--model=VALUE`
   (equals form), but pi's `dist/cli/args.js` only matches the literal
   token `--model` and records `--model=...` as an unknown flag — verified
   against pi 0.80.10, 0.84.1, 0.84.2, and 0.84.4. The recorded E5 live
   run (pi 0.84.1, `docs/sdd.md` in satyrn-engine) is therefore **not
   reproducible against stock pi**: its external transcript artifact is
   the only evidence it happened. The re-probe runs the engine under a
   recorded argv-compat shim (scratch `arms/pi`, rewrites `--model=X` to
   the space form, then execs the real pi); the engine code is measured as
   shipped. This is a finding for the engine's backlog: either its pi
   child must use the space form or E5's verification needs a recorded,
   reproducible pi.
3. **The shim must be named `pi`** to intercept PATH resolution — a
   self-inflicted first attempt (`pi-shim` was never found), recorded to
   avoid repeating it.

Smoke outcomes: the direct engine run produced a real patch (graded fail,
4 pass / 1 fail — a near-miss implementation, model behavior, not
plumbing); one evals-seam engine attempt produced no patch because the
model repeated the recorded invalid-`edit` shape (omitting the required
`path` property) and declared completion — a legitimate refused attempt.
The engine arm's plumbing is verified end to end.
