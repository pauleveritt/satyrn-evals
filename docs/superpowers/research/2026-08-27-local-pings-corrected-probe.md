# `local-pings` corrected baseline probe

**Date:** 2026-08-27
**Status:** completed locally; not admitted
**Model:** `omlx/gemma-4-12B-it-MLX-8bit`
**Pi:** 0.84.1
**oMLX:** 0.6.0rc1

## Decision

Do not admit `local-pings` to V5 yet. Under the primary metric fixed before the run,
the corrected probe produced 0/4 successful attempts and stopped at n=4 as a
floor. Three attempts timed out and one ended without a patch.

That primary result is not the whole diagnosis. Two timed-out attempts retained
non-empty patches. Both passed the corrected four-test oracle on offline
regrade and passed five fresh runs of the 89-test non-network preservation
suite. The probe therefore separates three measurements:

- **successful attempt outcome:** 0/4;
- **non-empty retained patch production:** 2/4;
- **conditional retained patch quality:** 2/2 passed the corrected oracle and
  preservation suite.

The retained-patch results must not replace the primary result after the run.
They show that the baseline trajectory did not complete after producing a
correct candidate. V5 needs an explicit rule for these measurements before
this task can be reconsidered.

## Oracle correction

The prior three-test oracle accepted a patch that combined registry and local
service types in a `set`, losing the registry's insertion order. The corrected
synthetic task adds one curator preservation test:

```text
tests/test_eval_preservation.py::test_local_ping_keeps_registry_ping_order
```

It registers two registry-only pings in a known order and a local ping. The
assertions require the local ping to appear and the two registry-only pings to
retain their relative order. In the frozen Python 3.14 environment, controlled
class hashes make the previously accepted set-union patch fail deterministically
without requiring a particular position for the local ping.

The test currently identifies registry pings through the private `_svc_type`
field. That is sufficient for this frozen diagnostic run, but couples the
oracle to an implementation detail. A future admission candidate should
observe public names or callable execution order instead.

The task was rebuilt through V2 capture from a new synthetic pair. Its base
contains the exact upstream target test changes plus the curator-authored test;
its fix applies the exact upstream target source change:

```text
upstream base:        31bc6dfd5d1a570b3b96cfefd878ccc686bde980
upstream target:      52c6689d34ce80c0f5a754f95d2aad54837402df
corrected task base:  9261f41efc99732204919cad5432de9085d6a70c
corrected task fix:   0055ea7b3fbee0fd0438be6cf7d0e561c230652e
```

Final-task qualification recorded:

| Input | Corrected oracle |
| --- | ---: |
| base | 0 pass, 4 fail |
| upstream known-good patch | 4 pass |
| previously accepted set-union patch | 3 pass, 1 fail |

There were no collection errors. The test is present in the model workspace;
this probe does not claim a hidden oracle.

## Frozen conditions

| Condition | Value |
| --- | --- |
| Arm | bare Pi plus SLM; no Engine, extensions, skills, or handoff contract |
| Prompt | same visible high-level `local-pings` brief; trailing newline normalized |
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
| Evidence adapter | stream transcript; snapshot tracked Git diff every 2 seconds |

The protocol, run script, adapter, manifest, known-good patch, and curator test
were hashed before attempt 1. No invocation was excluded or replaced. Every
attempt retained a transcript and patch file. Recorded free space before and
after each attempt stayed above the predeclared 2 GiB runtime floor.

## Primary result

The primary result was 0/4, so the fixed stopping rule did not extend the
probe:

| Attempt | Recorded result | Elapsed | Tool calls | Failed `edit` calls | Patch | Offline grade |
| ---: | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `NO_PATCH` | 423 s | 5 | 0 | 0 B | — |
| 2 | `COMMAND_TIMEOUT` | 903 s | 14 | 12 | 0 B | — |
| 3 | `COMMAND_TIMEOUT` | 901 s | 10 | 3 | 2,165 B | pass |
| 4 | `COMMAND_TIMEOUT` | 901 s | 11 | 4 | 1,915 B | pass |

Elapsed time is diagnostic context only, not a comparison claim. The timeout
rows can exceed 900 seconds slightly because the outer timeout must terminate
the process tree and persist artifacts.

Attempt 1 reached the model output limit after locating `get_pings()` but before
editing. Attempt 2 formed a plausible implementation, then repeated the same
invalid `edit` call 12 times because it omitted the required top-level `path`.

Attempts 3 and 4 each made one successful source edit. Both then continued
with failed replacements until the outer deadline. Their retained
patches used ordered dictionary iteration for output and a set only for
membership, so neither repeated the defect that invalidated the first probe.

## Preservation audit

The upstream known-good patch and both retained candidates were each applied to
a fresh copy of the corrected task base and tested five times:

| Patch | Independent runs | Result | Exact target tree |
| --- | ---: | ---: | ---: |
| upstream known-good | 5 × 89 tests | 5 pass | yes |
| attempt 3 | 5 × 89 tests | 5 pass | no |
| attempt 4 | 5 × 89 tests | 5 pass | no |

The network-integration directory was excluded because the command sandbox
used for the audit forbids binding test sockets. The corrected oracle tests and
the existing non-network tests are outside that directory.

## What this establishes

- The corrected task rejects the known non-preserving set-union patch.
- Bare Pi produced no successful attempt under the declared 900-second policy.
- Two of four attempts nevertheless produced distinct, preservation-safe
  candidate patches before timing out.
- Repeated invalid mutations and continued work after a correct edit are
  concrete model/tool-loop signals that an Envelope or Engine may change.
- Successful attempt outcome, retained-patch production, and conditional
  retained-patch quality must remain separate fields in any later summary.

It does not establish an Engine improvement, admit a V5 diagnostic workload,
or justify counting a timed-out patch as a successful product outcome.

## Evidence and recomputation

The local evidence bundle contains the immutable protocol, corrected synthetic
repository, captured task, four attempts, offline receipts, qualification
records, repeated preservation JUnit files, decision, and recomputation script:

```text
/Users/koudai/work/satyrn/evidence/2026-08-27-local-pings-corrected-baseline-probe.tar.gz
sha256: 2feb305fb70c74e06fef80a0f34aa69ad20d54c95e883f8ae2d7e7a41d622386
```

Verify and recompute:

```bash
set -euo pipefail
archive=${EVIDENCE_ARCHIVE:?Set EVIDENCE_ARCHIVE to the local archive path}
(cd "$(dirname "$archive")" && shasum -a 256 -c "$(basename "$archive").sha256")
tmpdir=$(mktemp -d)
tar -xzf "$archive" -C "$tmpdir"
python3 "$tmpdir/satyrn-headroom-local-pings-corrected/analyze.py" \
  --root "$tmpdir/satyrn-headroom-local-pings-corrected"
jq '{primary_probe, retained_patch_audit, task_qualification, preservation, infrastructure}' \
  "$tmpdir/satyrn-headroom-local-pings-corrected/analysis.json"
```
