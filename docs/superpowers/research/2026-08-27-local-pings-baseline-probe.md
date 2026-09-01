# `local-pings` baseline probe

**Date:** 2026-08-27
**Status:** completed locally; not admitted; headroom undetermined
**Model:** `omlx/gemma-4-12B-it-MLX-8bit`
**Pi:** 0.84.1
**oMLX:** 0.6.0rc1

**Follow-up:** a preservation-safe oracle was built and used for a fresh
probe. The task remains unadmitted; see the
[`local-pings` corrected probe](2026-08-27-local-pings-corrected-probe.md).

## Decision

Do not admit `local-pings` to V5 yet. The clean run's three-test oracle
reported 1/6 bare-Pi passes, apparently placing the task between the floor and
ceiling. An offline preservation audit then showed that this run's only
passing patch loses registry ordering and is nondeterministic across Python
processes.

Two superseded runs produced three other oracle-passing patches that passed
the wider preservation audit. The evidence therefore shows that the current
oracle is unsound, not that the task lacks headroom. Headroom remains
undetermined until a fresh probe uses a preservation-safe oracle.

This is a rejected-candidate record. It does not add a baseline field to a
task manifest or start V5.

## Why this task

The old `local-ai-pi` evidence gave `local-pings` a
[4/6 bare-Pi result with full tools](https://github.com/pauleveritt/local-ai-pi/blob/8588ba4bf35abf4a4ea1d3cd591741025063e119/docs/superpowers/research/2026-08-10-phase7-frontier-contracts-variance.md).
That was a selection prior, not a comparable result: it used a 1,800-second
deadline, an 8,192-token output cap, and caps of 60 turns and 150 tool calls.
Several other `svcs` tasks were already at a floor or ceiling, so
`local-pings` was the strongest first candidate for a fresh probe through the
rewritten Evals path.

The upstream commit changed tests and source together. An experiment-only
clone applied the target's exact regression-test file first and its exact
source file second:

```text
upstream base:        31bc6dfd5d1a570b3b96cfefd878ccc686bde980
upstream target:      52c6689d34ce80c0f5a754f95d2aad54837402df
synthetic test base:  5b2100410ee4ceb869d8ee35b9f36c6443ea1dad
synthetic source fix: 22d7539f6b00d968499efba4195f30ea16b898e3
```

V2 capture passed its four deterministic checks. The generated known-good
patch independently passed the original three-test oracle before any model
run.

## Run history

Three same-day batches used the same model, prompt, task, tools, and
900-second deadline. The first two are disclosed but superseded as primary
evidence:

| Run | Original oracle | Why superseded | Passing-patch preservation audit |
| --- | ---: | --- | ---: |
| initial | 2/6 | buffered adapter lost transcript and patch for both timeouts | both patches passed 5/5 × 88 tests |
| formal | 1/6 | disk exhaustion caused two replacements and affected two counted attempts | its patch passed 5/5 × 88 tests |
| clean | 1/6 | no infrastructure exclusion or replacement | its patch passed 1/10 × 88 tests |

The original oracle therefore recorded 4/18 passes across the history, but
this is not a pooled admission result. The runs have different evidence
quality, and one of the four patches demonstrates that the oracle can accept
broken behavior. Only a new run under a corrected oracle can determine
headroom.

The superseded archives remain available for audit:

```text
initial: 2026-08-27-local-pings-baseline-probe.tar.gz
sha256:  7539e791a30163b532d635426f4199d1e8707d88ae9de174d3db799297b32673

formal:  2026-08-27-local-pings-baseline-probe-formal.tar.gz
sha256:  6daebff785f5aacccf027d699f3fa3af2b32c70893fa2f345833716874df9a73
```

## Frozen conditions

| Condition | Value |
| --- | --- |
| Arm | bare Pi plus SLM; no Engine, extensions, skills, or handoff contract |
| Prompt | high-level `local-pings` brief; SHA-256 `60b0e1b0922f923ef0ab0fdcf10c527bb095a1a95364aaf0accf7aed7cebead1` |
| Tools | `read`, `bash`, `edit`, `write` |
| Probe rule | n=4; stop at 0/4 or 4/4, otherwise extend to n=6 |
| Model | `omlx/gemma-4-12B-it-MLX-8bit` |
| Pi-declared context / max output | 80,000 / 8,192 tokens |
| oMLX global context-window setting | 32,768 tokens |
| Sampling defaults | temperature 1.0, top-p 0.95, top-k 0, repetition penalty 1.0 |
| oMLX concurrency / cache | 1 request / disabled |
| Outer deadline | 900 seconds per attempt |
| Schedule | one arm, sequential attempts |
| Isolation | one Evals-owned detached worktree per attempt |
| Evidence adapter | stream transcript; snapshot `git diff` every 2 seconds |

The protocol was written before attempt 1 and identifies all three model
shards by SHA-256. No invocation was excluded or replaced. All six attempts
retained their attempt record, transcript, and patch. Recorded free space
before and after every attempt stayed above the predeclared 2 GiB runtime
floor.

## Recorded result

The initial batch was 1/4, so the fixed rule extended it to n=6. The original
oracle result was 1/6:

| Attempt | Recorded result | Elapsed | Tool calls | Invalid `edit` calls | Peak reported `totalTokens` |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | `COMMAND_TIMEOUT` | 901 s | 13 | 1 | 35,053 |
| 2 | pass | 448 s | 8 | 0 | 18,897 |
| 3 | `COMMAND_TIMEOUT` | 901 s | 13 | 4 | 29,836 |
| 4 | oracle fail | 204 s | 5 | 2 | 13,794 |
| 5 | `NO_PATCH` | 608 s | 7 | 0 | 28,095 |
| 6 | `COMMAND_TIMEOUT` | 900 s | 12 | 7 | 39,256 |

Elapsed time is diagnostic context only. It is not a comparison claim.
`totalTokens` is Pi's reported value; this record does not equate it with the
server's effective context accounting.

## Oracle audit

Attempt 2 combined registry and local service types with a `set`, then
iterated that set to build the result. It satisfied the three new regression
tests but discarded the registry's stable insertion order. The existing
`tests/test_integration.py::TestAsync::test_aping` test observes that order.

Adding that existing test to an audit-only four-test oracle produced:

| Fixed patch | Independent grades | Result |
| --- | ---: | --- |
| upstream known-good | 20 | 20 pass |
| attempt 2 | 20 | 10 pass, 10 fail |

The patch iterates over a set, whose order is not guaranteed and varied
between processes in these runs. A wider non-network preservation run
confirmed the same defect:

| Fixed patch | Independent runs | Result |
| --- | ---: | --- |
| upstream known-good | 5 × 88 tests | 5 pass |
| attempt 2 | 10 × 88 tests | 1 pass, 9 fail |

The network-integration directory was excluded from this audit because the
Codex command sandbox used for it forbids binding test sockets. The failing
ordering test is outside the excluded directory. Applying the known-good
patch also reproduced the synthetic fix commit's exact Git tree; the
candidate patch did not.

Because capture and grading are separate, this audit reused the six preserved
model outputs. No model was rerun and the original records were not rewritten.

## Failure diagnosis

Four attempts sent Pi's `edit` tool a batch in which `path` was nested inside
an edit item or otherwise omitted from the top level. Pi 0.84.1 expects
`path` at the top level and `edits=[{oldText, newText}, ...]`. Fourteen such
calls failed schema validation.

Attempts 1, 3, and 6 reached the outer deadline. Attempt 5 ended at the model's
output limit without a patch. These are useful hypotheses for later Envelope
or Engine arms, but they do not rescue an unsound task oracle.

Attempts 1 and 6 reported peak `totalTokens` values above the recorded 32,768
oMLX setting. The relationship between Pi's telemetry and the server's
effective context enforcement is unverified, so the record does not attribute
their timeouts to context overflow.

## What this establishes

- The clean bare-Pi result is recomputable as 1/6 under the original oracle.
- That clean run's sole pass is not preservation-safe or deterministic.
- Three earlier oracle-passing patches did pass the non-network preservation
  audit, so the task's headroom cannot be inferred from the defective clean
  pass.
- `local-pings` needs a preservation-safe oracle and a fresh baseline protocol
  before it can be reconsidered.
- Rejected candidates need prose records; silently retaining this one would
  overstate suite headroom.

It does not establish an Engine improvement, compare models, or start V5.

## Evidence and recomputation

The local evidence bundle contains the immutable protocol, task
materialization, adapter and analysis scripts, all six attempt artifacts, raw
receipts, the audit-only manifest, repeated regrades, prior-run metadata and
passing patches, and preservation JUnit files:

```text
/Users/koudai/work/satyrn/evidence/2026-08-27-local-pings-baseline-probe-clean.tar.gz
sha256: e7d582f345966a7d80ea026695ac57d5d0a127be12e1e984f3463133fd71be0c
```

The archive is local evidence, not a repository or CI dependency. Verify its
SHA-256 from the adjacent `.sha256` file, then recompute `analysis.json`:

```bash
set -euo pipefail
archive=${EVIDENCE_ARCHIVE:?Set EVIDENCE_ARCHIVE to the local archive path}
(cd "$(dirname "$archive")" && shasum -a 256 -c "$(basename "$archive").sha256")
tmpdir=$(mktemp -d)
tar -xzf "$archive" -C "$tmpdir"
python3 "$tmpdir/satyrn-headroom-local-pings-clean/analyze.py" \
  --root "$tmpdir/satyrn-headroom-local-pings-clean"
jq '{primary_oracle, recorded_decision, historical_context, oracle_audit, infrastructure}' \
  "$tmpdir/satyrn-headroom-local-pings-clean/analysis.json"
```
