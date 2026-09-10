# Pre-run record — `agentclinic-session-phased`, Baseline

Written 2026-09-09, **before any inference**. Every value below is frozen at
the moment of writing. A value chosen or changed after reading results is the
shape the spike protocol forbids.

Plan: `docs/superpowers/plans/2026-09-09-agentclinic-phased-session.md`, Task 3.
Spec: `docs/superpowers/specs/2026-09-09-agentclinic-phased-session-design.md`,
read with its 2026-09-09 correction section, which governs where the two
disagree.

## What this run is for

To watch one session trajectory across three successive development requests
and find **one concrete obstruction** worth pursuing. It is observational.

## The arm

**Baseline only.** There is no Engine session arm, and building one is engine
design rather than adapter glue: the mutator and runner assume one frozen
contract carrying a `test_command`, and a session has no per-prompt equivalent
(`docs/current/agentclinic-phase-session-proposal.md:118-121`). **No result
from this run may be phrased as Engine versus Baseline, in either direction.**

| Field | Value |
|---|---|
| Arm record | `arms/baseline.json` |
| argv | `satyrn-evals-attempt-pi` |
| Tools | `read, bash, edit, write` |
| Model | `omlx/gemma-4-12B-it-MLX-8bit` |
| Server model | `gemma-4-12B-it-MLX-8bit` |
| pi | `0.84.4` |
| Context window | 80000 |
| Max tokens | 8192 |
| Compaction | enabled, reserve 16384 |
| Temperature | 1.0 |

Gemma rather than Ornith, deliberately: the per-phase turn figures this
workload's design reasons about come from the Gemma-family baseline arm of the
2026-09-01 spike (`archive/2026-09-07-pre-reset/docs/superpowers/research/2026-09-01-agentclinic-spike.md:288-292`),
and using the same family keeps those numbers a usable point of reference. An
Ornith run is a separate record, not a variant of this one.

`arms/baseline.json` records five inference settings. Two more that Ornith's
record carries — `top_p` and `top_k` — are **not** recorded for this arm and
are therefore not preflight-checked. That is a known gap in the arm record,
carried here rather than silently ignored: this run's reproducibility claim
covers the five recorded settings only.

## The task

| Field | Value |
|---|---|
| Task | `agentclinic-session-phased` |
| Task tree sha256 | `bd9ac2fe0c4aeee280802d4c15c00e152728b0c6a48064996009dd4ec9daab10` |
| Repo commit | `ac445c0` (preflight refuses a dirty tree and records the commit) |
| Prompt source | `swiftstar` `ab1d83d`, `fixtures/agenttest/specs/roadmap.md`, sha256 `d470ba450101c669a3475cc388bd753f174bc749f6ed7cf2d3e114853453ff0c` |

Prompt digests (sha256, first 16 hex; the digest of the prompt string as sent,
preamble included):

| Step | Digest | Bytes |
|---|---|---|
| `phase-1-home` | `4fcf7018dc034160` | 1347 |
| `phase-2-board` | `77c1310409d1f1bc` | 1392 |
| `phase-3-add` | `29fcaba91e077d45` | 960 |

Recompute:

```
uv run python -c "
import hashlib, json
from pathlib import Path
spec = json.loads(Path('src/satyrn_evals/tasks/agentclinic-session-phased/session.json').read_text())
for s in spec['steps']:
    print(s['id'], hashlib.sha256(s['prompt'].encode()).hexdigest()[:16])
"
```

## Run parameters

| Field | Value |
|---|---|
| **n** | **1 session** |
| `--step-timeout` | 600s |
| `--start-timeout` | 60s (default) |
| `--close-timeout` | 30s (default) |
| Output | `~/satyrn-smokes/2026-09-09-session-phased-<HHMMSS>/` |

**`n = 1` is frozen and will not be extended after reading the result.** One
session answers "what does a trajectory look like and what obstructs it". It
cannot answer "how often" — a single session distinguishes a pathology from a
fluke not at all. Any rate claim requires its own record with its own frozen
`n`, and this record may not be retroactively treated as its first cell.

600s rather than the spike's 300s: two of the spike's four Phase 3 runs hit the
300s cap, which censored the two largest turn cells and is why this workload
cannot derive a Phase 3 ceiling from that data. A longer bound trades wall
clock for uncensored observation, which is the right trade for an
observational run.

## The two questions, stated separately

**Outcome.** How many phases does the session complete correctly, judged by
the cumulative hidden checks — 4 at checkpoint 1, 10 at checkpoint 2, 13 at
checkpoint 3?

**Cost — descriptive, not graded.** What did each phase cost in turns, tool
calls, compaction events, and seconds? **No budget ceiling is declared, and no
pass/fail cost threshold exists.** `session.json` declares no `turn_budget` or
`tool_budget`, and a test asserts it
(`tests/test_agentclinic_session_phased.py`, `test_no_step_declares_a_budget_ceiling`).
Elapsed seconds are reported with the standing caveat that they are a
diagnostic about this harness, never a basis for comparing arms.

A correctness ceiling is **not** a workload failure. The 2026-09-01 spike
ceilinged at `deepest_pass` 3,3,3,3 and still produced named pathologies.

## Observables — candidate findings, not verdicts

Each of these is a signal to **inspect the trace**, never a pathology verdict
on its own. Named beyond their evidence is how the previous draft of this
work went wrong.

- **A checkpoint patch identical to its predecessor.** This means *no net
  change*. It is consistent with a phase leak (the model built later phases
  early) but does not establish one; establishing it means checking whether a
  later phase's requirements were already satisfied.
- **A stretch of tool calls with no successful write.** Tool names cannot
  establish that nothing was written — `bash` writes files, and a refused
  `edit` writes nothing — and an edit-free stretch does not establish
  misdiagnosis. It marks a trace region to read.
- **Scope violations**, especially root-level config files, which is how a
  skeleton start goes wrong.
- **An earlier phase's check failing at a later checkpoint**, attributed to
  the checkpoint that broke it. This is the cross-phase signal the workload
  exists for.
- **Compaction events**, reported, not scored.
- **`preservation_verdict` unset** on every step. This is correct and
  expected: the base ships no application, so there is no base behaviour to
  preserve, and grading is skipped rather than inferred. An unset verdict is
  never to be summarized as a pass.

## Preconditions, all required before the run starts

1. **The environment the preamble promises must exist.** The preamble tells
   the solver the environment is installed. Materialize `base/`, run the
   pinned install, and confirm `fastapi`, `turbohtml` and `pytest` import at
   `0.115.10 / 1.5.0 / 8.3.4`. If they do not, the preamble is a false
   statement to the model and the run is **void, not merely noisy** — the
   spike's largest phase-1 tool-error class was `pip` reinstalling what was
   already present (7 of 10, `spike:298-301`).
2. **Preflight passes** on a clean tree at `ac445c0`, and records the commit.
3. **The machine is quiet.** A GPU out-of-memory is machine state; no code
   fix reaches it, and `MODEL_ERROR` classifies one after the fact rather
   than preventing it.
4. **Model identity is verified from the transcript's own `message.model`
   field**, not from the requested argv.

## Known limitation carried into this run

The `prompt-faithful` fairness gate establishes that a prompt-derivable
implementation scoring 13/13 **exists**. It does not establish that a
check-blind solver lands in the passing region, because its author had read
the checks — the extraction required it
(`src/satyrn_evals/tasks/agentclinic-session-phased/QUALIFICATION-NOTE.md`).

Two prompt readings are permitted but fail: a `Complaint` with an `id` field
inserted ahead of `agent_name` fails the positional construction the
model-contract check requires; and a nav link labelled "Home Page" fails the
exact `home` / `complaints` normalization.

**If this run fails on either, that is a prompt defect, not a solver finding**,
and the prompt is fixed and the run redone under a new record. Recording this
in advance is what stops it being reasoned about after the fact.

## What happens after

Read the transcripts. Select **one** concrete obstruction to pursue. Build
further classification only if it serves that investigation — a detector
written before a trace has demanded it is instrument work, and `AGENTS.md`
caps consecutive instrument-only pieces at two.

## Correction, 2026-09-09 — task identity leaked into the solver's workspace

Found while verifying precondition 1, **before any inference**. Recorded, not
edited away.

`base/pyproject.toml` was copied from `agentclinic-repair-depth-3` and kept
that task's identity: `name = "agentclinic-complaints-depth-3"` and
`description = "Seeded broken state depth-3 of the AgentClinic complaints app
(repair fixture)"`. That file sits in the solver's workspace and is among the
first things a coding agent reads. It tells a solver that is supposed to be
**building an application from an empty skeleton** that it is instead looking
at a seeded broken state and a repair fixture — a false statement about the
task, in the same class as the preamble promising an environment that does not
exist.

The contamination scanner would not have caught it: it looks for grader
overlay content in the workspace, not for task-identity leakage.

Fixed by renaming the package to `agentclinic-session-phased` in
`base/pyproject.toml` and in the matching root-package name at
`base/uv.lock:20`, and replacing the description with `AgentClinic complaints
app`. The lock was **not** regenerated — only the identity string changed — so
no version moved: `uv sync --frozen` succeeds and resolves fastapi 0.115.10,
turbohtml 1.5.0, pytest 8.3.4, httpx 0.28.1, starlette 0.46.2, verified after
the edit. `base/` is no longer byte-identical to depth-3's, which was never a
required property of this task; the pins are, and they are unchanged.

The frozen task tree sha256 in the table above is updated to `bd9ac2fe0c4aeee280802d4c15c00e152728b0c6a48064996009dd4ec9daab10`
accordingly. The prompt digests are unchanged, since no prompt changed.

Recompute:

```
uv run python -c "
import hashlib
from pathlib import Path
t = Path('src/satyrn_evals/tasks/agentclinic-session-phased')
h = hashlib.sha256()
for p in sorted(t.rglob('*')):
    if p.is_file():
        h.update(p.relative_to(t).as_posix().encode()); h.update(p.read_bytes())
print(h.hexdigest())
"
```

### Precondition 1 result

**PASS**, after the fix. `uv sync --frozen` exits 0 from a clean materialization
of `base/`, and `fastapi`, `turbohtml`, `pytest`, `httpx` and `starlette` all
import at the pinned versions, as do `starlette.testclient.TestClient` and
`turbohtml.parse` / `Doctype` — the exact imports the hidden checks perform.

## Precondition results, 2026-09-09

**1. Environment — PASS after a fix.** See the correction above.

**2. Preflight — NOT APPLICABLE as written; its substance checked directly.**
`scripts/preflight.sh` is attempt-shaped: it requires `--rung` and
`--contract-digest`, and a session has neither. It exits 2 on
`--rung is required`. Rather than bend a session into an attempt's flags, its
two load-bearing checks were performed directly and are recorded here:

- **Clean tree.** `git status --porcelain` empty at `ab1f6fd`.
- **A live completion, never `/v1/models`.** `preflight.sh:11-18` records why:
  on 2026-09-05 the omlx server advertised `gemma-4-26B-A4B-it-OptiQ-4bit`,
  whose weights were nowhere on the machine, and the listing was cleared later
  the same session. A listing is not evidence a cell can run. The probe:
  `POST http://127.0.0.1:8001/v1/chat/completions`, model
  `gemma-4-12B-it-MLX-8bit`, `max_tokens` 8, `temperature` 0 — returned
  `"OK"`, with the response's own `model` field reading
  `gemma-4-12B-it-MLX-8bit`.

Not checked, because they belong to a budgeted multi-cell batch and this is
one session: the per-cell input-token floor, and the realized arm order.
A session run needs a preflight of its own shape; that gap is recorded, not
worked around.

**3. Machine — acceptable, not silent.** No GPU-competing compute was running.
The largest CPU consumers were interactive UI processes (WindowServer, Chrome,
the Claude app). Recorded rather than asserted quiet, because elapsed seconds
are a diagnostic here and no wall-clock comparison between arms is possible in
a single-arm run.

**4. Model identity from the transcript** — to be verified from each
transcript's own `message.model` field after the run, never from the requested
argv.

## The command

```
uv run satyrn-evals session agentclinic-session-phased \
  --output ~/satyrn-smokes/2026-09-09-session-phased-<HHMMSS> \
  --step-timeout 600 \
  -- satyrn-evals-session-pi --provider omlx \
     --model gemma-4-12B-it-MLX-8bit \
     --tools read,bash,edit,write
```

`--tools` is mandatory and stated. The first bounded Baseline session, before
2026-09-08, passed none: the model reached the installed `pi-subagents`
extension and dispatched a **detached** worker that wrote files across two
checkpoint boundaries with no retained events
(`src/satyrn_evals/adapters/pi_session.py:96-102`). `build_pi_argv` now
refuses an unstated surface and disables extension, skill, prompt-template and
context-file discovery.
