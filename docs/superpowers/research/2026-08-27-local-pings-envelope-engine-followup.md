# Corrected `local-pings`: Envelope and Engine follow-up

**Date:** 2026-08-27
**Status:** completed locally; not admitted
**Model:** `omlx/gemma-4-12B-it-MLX-8bit`
**Pi:** 0.84.1
**oMLX:** 0.6.0rc1

## Question

The corrected bare-Pi probe recorded 0/4 successful attempts, while two
timed-out attempts retained correct patches. What does a basic budget-only
variant record, and what does the current handoff-contract Engine record?

The Baseline result is reused unchanged from its immutable evidence archive.
The follow-up ran Envelope and Engine four times each in alternating order.
This is not a contemporaneous three-arm A/B test, and elapsed time is not
compared.

## Conditions fixed before the follow-up

- **Baseline:** bare Pi with the high-level brief and
  `read,bash,edit,write`; the prior 0/4 result was not rerun or replaced.
- **Envelope:** a controlled budget-only variant with the same brief and tools,
  plus only the existing 16-turn and 30-tool-call extension. It is not a
  reproduction of the canonical product Envelope, which used only
  `read,write`.
- **Engine:** an inspected handoff contract, Engine E5's bounded
  revision/path edit, and the E3.5 loop breaker, exposing `read,edit`.
- Envelope and Engine each ran n=4 with the same local model and a 900-second
  outer deadline.
- The primary metric was a normally completed `satyrn-evals` attempt whose
  oracle verdict was `pass`.
- Retained-patch production and conditional retained-patch quality were
  separate secondary measurements. They never replaced the primary result.

The protocol records the exact task, model, repository, prompt, extension,
contract, script, and known-good receipt hashes.

## Primary result

| Scenario | Successful attempts | Recorded outcomes |
| --- | ---: | --- |
| Baseline | 0/4 | 1 `NO_PATCH`, 3 `COMMAND_TIMEOUT` |
| Envelope | 0/4 | 3 `NO_PATCH`, 1 `COMMAND_TIMEOUT` |
| Engine | 2/4 | 2 oracle pass, 1 oracle fail, 1 `NO_PATCH` |

The Engine arm recorded 2/4 completed passes, while the prior Baseline and the
contemporaneous budget-only Envelope variant each recorded 0/4. This is
product-path evidence under the frozen local model. Because neither budget
limit activated, the run does not estimate the effect of an active cap.

This is a diagnostic count, not a statistical superiority claim. The Engine
arm changes the contract and prompt information, the tool surface and control
flow, and the bounded-mutation mechanism, so the 2/4 result cannot be
attributed to any one of them.

## Retained-patch audit

| Scenario | Non-empty patches | Conditional oracle + preservation quality |
| --- | ---: | ---: |
| Baseline | 2/4 | 2/2 pass |
| Envelope | 1/4 | 0/1 pass |
| Engine | 3/4 | 2/3 pass |

The Envelope's retained timeout patch passed the three upstream behavior tests
but failed the curator preservation test. It formed a `set` of registry and
local types, repeating the ordering defect that invalidated the first probe.

The two passing Engine patches are distinct implementations and neither is an
exact copy of the upstream target tree. Each passed five fresh runs of the
89-test non-network preservation suite: 10/10 runs and 890/890 tests passed.

The failing Engine patch handled local registrations only while iterating main
registry types. It therefore omitted local-only services and failed two of the
four oracle tests.

## Interaction evidence

Envelope attempts used 7–12 turns and 6–11 tool calls. None reached the
16-turn or 30-tool-call limit. Twelve of thirteen `edit` calls failed, and no
budget-exhaustion event was recorded. The limits were real but sat above the
observed failure path, so they could not settle the attempt after a candidate
appeared.

Engine attempts used 3–8 turns and 2–7 tool calls. Four of eleven `edit` calls
failed. No loop-break event occurred because no exact call reached its repeat
threshold. The useful signal in this run is therefore from the composite
contract-plus-bounded-mutation path, not from either budget exhaustion or the
loop breaker firing.

## Decision

Keep `local-pings` as product-path evidence, but do not admit it to V5. The
binding V5 rule asks for a preservation-safe task whose successful-attempt
Baseline is between floor and ceiling. This Baseline remains 0/4, even though
the retained-patch audit shows that the model can sometimes construct the
change.

The next suite-search target is a task whose initial n=4 Baseline is neither
0/4 nor 4/4. Extend such a task to n=6, then admit it only if the final result
remains genuinely between floor and the agreed near-ceiling boundary. That
boundary is not yet defined. This result also supports keeping three fields
separate in V5 design: successful attempt outcome, retained-patch production,
and conditional retained-patch quality.

## Evidence and recomputation

The local evidence bundle contains the immutable protocol, all eight follow-up
attempts, the prior Baseline archive, offline receipts, ten preservation runs,
analysis, decision, a 338-file hash manifest, and recomputation scripts:

```text
/Users/koudai/work/satyrn/evidence/2026-08-27-local-pings-envelope-engine-followup.tar.gz
sha256: 3d99a31b2da56076cdfcf52650b605e9b7a6ca202c7594e38f82740ff67825ff
```

Verify and recompute:

```bash
set -euo pipefail
archive=${EVIDENCE_ARCHIVE:?Set EVIDENCE_ARCHIVE to the local archive path}
(cd "$(dirname "$archive")" && shasum -a 256 -c "$(basename "$archive").sha256")
tmpdir=$(mktemp -d)
tar -xzf "$archive" -C "$tmpdir"
root="$tmpdir/satyrn-local-pings-three-arm"
python3 "$root/analyze.py" --root "$root"
jq '{primary, arms, preservation, infrastructure}' "$root/analysis.json"
```
