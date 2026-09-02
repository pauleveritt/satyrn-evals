# `magicmock-factory` baseline probe

**Date:** 2026-08-29  
**Status:** completed locally; not admitted  
**Model:** `omlx/gemma-4-12B-it-MLX-8bit`  
**Pi:** 0.84.1  
**oMLX:** 0.6.0rc1

## Decision

Do not admit `magicmock-factory` to V5 yet. The final, predeclared probe
produced 0/4 successful attempts and stopped at n=4 as a floor. Three attempts
retained non-empty patches, but none passed the final oracle.

The task itself is valid. The exact upstream source fix passes the final
oracle and the complete 142-test upstream suite. This result says that bare Pi
plus this Gemma checkpoint did not complete the task under the declared
conditions; it does not say that the task is unsolvable.

## Why the oracle changed twice

The upstream fixing commit mixes its test and source changes. Direct V2
capture therefore correctly refused it with `NO_DISCRIMINATING_TESTS`: after
reverting the source and tests together, there was no new test left to fail.
The task was reconstructed as a synthetic test-only base followed by the exact
upstream source diff.

That first task still had an unsound oracle. Five retained candidate patches
passed both its oracle and all 142 upstream tests, but all five stopped
rejecting genuine async context managers when `enter=False`. A curator
assertion made that behavior explicit.

The corrected probe then had one passing attempt. Its patch rejected a normal
async context manager, but accepted a genuine object implementing both the
synchronous and asynchronous context-manager protocols. The exact upstream
fix rejects that object. A second curator assertion closed this remaining
gap, and changing the oracle restarted the probe at n=4 as declared.

| Oracle stage | Primary | Non-empty patches | Patches passing oracle | Status |
| --- | ---: | ---: | ---: | --- |
| upstream test only | 3/6 | 5 | 5 | superseded: semantic regression |
| reject ordinary async context managers | 1/6 | 4 | 1 | superseded: dual-protocol regression |
| reject ordinary and dual-protocol async context managers | 0/4 | 3 | 0 | final; floor |

These rates are not a controlled comparison. Each stage used fresh stochastic
attempts, and the visible contract became more explicit as the preservation
requirements were clarified. The score changes therefore cannot be attributed
to the oracle alone. The evidence that justified each correction is narrower:
all five first-stage retained patches fail correction 1, and the sole
second-stage passing patch fails correction 2. Each contract-and-oracle change
started a fresh probe as declared.

## Final task identity

```text
upstream base:        f8585ce9f8fe6df9da4cf405cec1e03f4708be26
upstream target:      c91f1f1736f1fc3b7fdb5b6d79588aa3da53909b
final synthetic base: 21f15112388d0b83f8a58d905c988cd7d631c3e8
final synthetic fix:  2d8de9b4d710acaee3327ab72dbbefd3ec8dfa9a
known-good patch:     d85eeae2ac9674810948e05c3d622b1d8d53c43c4fd3ea5371aec1e355c67717
final test file:      4fa19d0fac4fcdbf4480f5e2552e5ef5e2d9576b8e4f9f51267171c76142007d
```

V2 capture passed source preflight, base-oracle, un-done-at-base, and
winnable checks. The base fails the discriminating test. The exact upstream
source fix passes that test and all 142 upstream tests.

The final visible test requires all of these behaviors:

- a synchronous factory registered with `enter=False` may return a
  `MagicMock`;
- `Container.get()` returns and caches that object;
- a real async context manager remains rejected by `get()`;
- an object implementing both sync and async context-manager protocols also
  remains rejected.

It permits alternative implementations; it does not compare candidate source
to the reference patch.

## Frozen conditions

| Condition | Value |
| --- | --- |
| Arm | bare Pi plus SLM; no Engine, extensions, skills, or handoff contract |
| Contract | high-level behavior statement; no implementation hint |
| Tools | `read`, `bash`, `edit`, `write` |
| Rule | n=4; stop at 0/4 or 4/4, otherwise extend to n=6 |
| Model | `omlx/gemma-4-12B-it-MLX-8bit` |
| Pi-declared context / max output | 80,000 / 8,192 tokens |
| Deadline | 900 seconds per attempt |
| Schedule | one arm, sequential attempts |
| Isolation | one Evals-owned detached worktree per attempt |
| Primary metric | completed attempt whose persisted patch grades `pass` |
| Secondary metrics | non-empty retained patch; its offline oracle verdict |

The protocol, adapter, model files, manifest, test file, and known-good patch
were hashed before attempt 1. No invocation was excluded or replaced. Every
attempt retained its transcript and patch file. There were no workspace
failures, missing artifacts, or runtime free-space violations.

## Final result

| Attempt | Result | Tool calls | Patch | Offline grade | Diagnosis |
| ---: | --- | ---: | ---: | --- | --- |
| 1 | `COMMAND_TIMEOUT` | 14 | 1,184 B | fail | imported `MagicMock` but did not change the rejecting condition |
| 2 | `COMMAND_TIMEOUT` | 20 | 0 B | — | no tracked source patch retained |
| 3 | `COMMAND_TIMEOUT` | 18 | 928 B | fail | referenced unimported `contextlib` and weakened context-manager routing |
| 4 | `COMMAND_TIMEOUT` | 21 | 329 B | unavailable | removed the `typing` import, so `TypeVar` raised during collection |

All four attempts reached the 900-second deadline. The three non-empty
patches are distinct. None passed the final oracle, so retained-patch quality
does not move this result off the floor.

## What this establishes

- A fixing commit can be valid upstream evidence while still requiring a
  synthetic test/source split for capture.
- Passing the target regression and the existing full suite did not preserve
  the behavior the source fix was intended to keep.
- A middle-band baseline score is not trustworthy until candidate passes are
  audited for semantic preservation.
- The final task is qualified and reproducible, but its bare baseline is a
  floor, so it is not currently a V5 admission task.
- Timeouts, failure to retain an edit, and destructive import edits are useful
  Engine/Envelope research signals, but that is a separate experiment.

## Evidence

The evidence bundle contains the direct-capture refusal, all three captured
tasks and protocols, 16 attempt transcripts, retained patches, receipts,
hash-checked preservation JUnit records, and a script that recomputes the
reported counts from primary artifacts:

```text
/Users/koudai/work/satyrn/evidence/2026-08-29-magicmock-factory-baseline-probe.tar.gz
sha256: 8405b27543230078cca7375e39d8b63038353aa5012f6951f4bf28247c083b27
```

Verify it with:

```bash
archive=${EVIDENCE_ARCHIVE:?Set EVIDENCE_ARCHIVE to the archive path}
(cd "$(dirname "$archive")" && shasum -a 256 -c "$(basename "$archive").sha256")
tmpdir=$(mktemp -d)
tar -xzf "$archive" -C "$tmpdir"
python3 "$tmpdir/satyrn-magicmock-final-capture/recompute.py"
```
