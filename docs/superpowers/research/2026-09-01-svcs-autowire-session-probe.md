# `svcs` autowire long-session probe

**Date:** 2026-09-01
**Status:** completed locally; proposed as a high-end research suite; not
admitted to V5
**Model:** `omlx/gemma-4-12B-it-MLX-8bit`
**Pi:** 0.84.1

## Decision

Use the real `svcs` autowire development change as the first high-end,
multi-prompt suite proposal. It is a useful capability wall, not a V5
middle-band workload: the four-run baseline's deepest feature-milestone
distribution was `1, 0, 0, 0` out of five.

The suite should be rebuilt on the current Evals workspace, artifact, and
offline-grading boundaries. The spike code is evidence only. None of the old
`local-ai-pi` harness or the local spike runner should be copied into this
repository.

## Workload

The suite replays one substantial change from `hynek/svcs` as five cumulative
feature requests and one final review request in one conversation:

1. synchronous and asynchronous autowire functions;
2. classes and special annotation types;
3. synchronous lifecycle and error behavior;
4. asynchronous feature parity;
5. asynchronous lifecycle behavior;
6. review and full regression repair, which adds no new feature milestone.

The exact public prompt sequence and immutable upstream identities are retained
in the
[`svcs` public curation record](data/2026-09-01-svcs-autowire-session-public.json).
Hidden test selections and grader files are intentionally not part of that
executor-facing record.

The executor starts at immutable upstream commit
`816403b5c1d3b9fff22bd9141fe836221dfe9d9c`. The reference end state is
`6bb3f2800a57f4f74641d6e7415c9865293a4016`, whose change contains 251
production lines in `src/svcs/_autowire.py`, 838 lines of direct tests, and
1,486 added lines in total.

Each prompt describes behavior rather than code. The target revision, target
files, reference patch, hidden test IDs, and grader output are withheld from
the executor. Here, "hidden" means absent from the attempt workspace and
conversation; it is an evaluation boundary, not a claim that public upstream
history is secret or that the local command is security-sandboxed.

## Qualification

Before the model runs, the candidate was checked three times in fresh detached
worktrees:

- the base failed every cumulative selection for the registered missing
  `aautowire` reason;
- the target passed every cumulative selection; and
- the target passed the complete 197-test suite.

The primary measurement was fixed before the repeat runs: the deepest ordered
feature milestone whose cumulative hidden oracle passes. The original spike
numbered the final review checkpoint as six, although it introduced no new
test. The proposed product design corrects the score range to zero through
five without changing the observed distribution.
Session completion, retained-patch production, preservation, turns, tool
calls, and terminal reason remain separate measurements.

## Baseline result

All four runs used one persistent Pi process on an M4 Max with 36 GB unified
memory, the same six prompts, Pi 0.84.1, oMLX 0.6.0rc1,
`omlx/gemma-4-12B-it-MLX-8bit`, `read,bash,edit,write`, an 80,000-token
Pi-declared context, a 16,384-token output limit, and 30 minutes per prompt.
Extensions, skills, prompt templates, context files, and approval prompts were
disabled.

| Run | Terminal condition | Prompts recorded | Turns / tool calls | Deepest pass |
| ---: | --- | ---: | ---: | ---: |
| 1 | timeout during prompt 2 | 2 | 17 / 15 | 1 |
| 2 | completed all prompts | 6 | 40 / 34 | 0 |
| 3 | output limit during prompt 1 | 1 | 18 / 17 | 0 |
| 4 | completed all prompts | 6 | 38 / 32 | 0 |

Every run retained a patch. One passed the first 8-test milestone. None passed
the whole workload. The trace exposed several distinct failure families:

- two runs deleted most of a central 1,199-line module;
- two conversations kept reporting progress after the patch stopped changing;
- rejected exact-text edits were described as completed work;
- one run reached 75,196 input tokens, compacted, and timed out;
- one run exhausted its output allowance; and
- one run modified a test outside the declared source surface.

One pilot runner defect was corrected before this aggregate was frozen: Pi's
`stopReason=length` must terminate the session. The affected run's raw trace
contains a later prompt with no further mutation; its recorded interpretation
is corrected in place to the one-prompt output-limit result above. A separate
no-network launch was excluded and explicitly rerun. No other run was silently
retried or reclassified.

## Remediation screening

Four later n=4 screens kept the task, model, prompts, and primary measurement
fixed. Read-only enumeration produced `0, 0, 0, 0`; bounded anchor feedback
produced `1, 0, 0, 0`; an optional public-check tool produced `0, 0, 0, 0`;
and a runner-owned public-preservation check produced `0, 0, 0, 0`.

The runner-owned check did catch a candidate with 104 public regressions.
Another run passed all 130 public tests at two checkpoints but still failed
the first hidden milestone. This establishes a useful reliability boundary,
not a capability improvement. Remediation work remains separate from the
suite and is not part of the proposed Evals implementation.

## Evidence status and limits

The 42 MiB local bundle contains the exact prompts, immutable revisions,
qualification policy and raw outputs, four included transcripts and patches,
the excluded-run records, graders, audit scripts, derived JSON, and a SHA-256
manifest:

```text
/Users/koudai/work/satyrn/evidence/svcs-autowire-session-20260901
```

`shasum -a 256 -c CHECKSUMS.sha256`, the focused Node and Python tests, Python
compilation, and regeneration of `FOLLOWUP-REMEDIATION.json` pass locally. The
large raw bundle is deliberately not committed to this repository.

This draft therefore records a locally auditable exploratory result, not yet
portable project evidence. The probe did not freeze a model-weight digest,
the server's effective context limit, sampling parameters, or a distributable
task materialization. Those fields must be captured by the product runner
before the result can support a release or comparative claim. The collection
failure at the base also proves only that the complete feature is absent; it
does not prove that each later milestone independently has useful difficulty.

## What the suite needs from Evals

V4 can run one command and preserve one final patch and transcript. This
workload needs one conversation to receive several prompts, with a cumulative
patch captured after each prompt and graded only after the executor has
stopped. The proposed boundary is documented in the
[`svcs` session design](../specs/2026-09-01-svcs-session-eval-design.md).

The suite is intentionally not admitted to V5 yet. A stronger local model may
move it off the floor; until that is measured, it remains the high end of the
suite search rather than evidence that a remediation works.
