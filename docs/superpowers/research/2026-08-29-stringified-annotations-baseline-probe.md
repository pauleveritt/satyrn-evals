# `stringified-annotations` baseline probe

**Date:** 2026-08-29  
**Status:** completed locally; not admitted  
**Model:** `omlx/gemma-4-12B-it-MLX-8bit`  
**Pi:** 0.84.1  
**oMLX:** 0.6.0rc1

## Decision

Do not admit `stringified-annotations` to V5 under this protocol. The frozen
bare-Pi probe produced 0/4 primary passes and stopped at n=4 as a floor. Two
attempts retained patches, but neither passed the oracle when regraded
offline.

The task is winnable: the exact upstream source fix passes the final oracle and
all 125 upstream tests. The result only establishes a floor for bare Pi plus
this Gemma checkpoint under the frozen conditions. It does not measure an
Envelope or Engine effect.

## Capture and oracle construction

The upstream target commit introduces both tests and source. Direct V2 capture
against upstream base `4b05ab8` and target `f81e493` therefore correctly
refused with `NO_DISCRIMINATING_TESTS`: reverting the target also removes the
tests that expose the bug.

The synthetic history places the exact upstream test diff on the parent, then
applies the exact upstream source diff. The final oracle selects all five
upstream string-annotation forms. Preservation checks live inside every
selected parameterized case, so capture cannot narrow them away. A candidate
must also:

- reject an unrelated string annotation for `Registry`;
- recognize unqualified and qualified `Container` annotations when the
  ordinary parameter name is `dependency`;
- preserve the documented `svcs_container` name convention even when an
  unrelated annotation cannot be resolved;
- reject a factory with two parameters.

Three deliberately naive candidates fail all 5/5 selected cases:

- accepting every string annotation violates the `Registry` requirement;
- `inspect.signature(..., eval_str=True)` without a fallback loses required
  behavior when names cannot be resolved;
- relying on the ordinary parameter name `container` misses the `dependency`
  cases.

An earlier probe selected only two forms, both using the name `container`.
That oracle had the third loophole and omitted three already-qualified upstream
forms. Its 0/4 result and artifacts are retained in the final bundle for
auditability, but it is superseded and does not support the decision. The
oracle and attempts both changed, so the two 0/4 rates are not a controlled
comparison.

## Task identity

```text
upstream base:        4b05ab8465f3d9a5ce7d1e40eaf808b0cb92a26c
upstream target:      f81e493487d872198981fa6cefb3a0d93ab03c08
synthetic base:       eab660aae2ded93e0bf18010d88df6df445adf74
synthetic fix:        a5d3ecd61cef43a89b410ead069d2082011506f5
known-good patch:     b4dc310c2266280be05f034b2f24bb11cee427f1528a7d710d4ddeb402af48aa
final test file:      0339537c76f99fb81d9fa8b2d790c9db521573176e1e209f4de00d85dea6f3aa
```

V2 capture passed source-preflight, base-oracle, un-done-at-base, and
winnable checks. All five selected cases fail at the synthetic base. The exact
upstream source fix passes them, their preservation checks, and all 125
upstream tests.

The Evals phase commit recorded by the frozen protocol was `9f2aec1`. Its tree
`921f23f` was identical to origin/main's merge commit `b0029b6` at run time.

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

The protocol, adapter, model files, manifest, final test file, and known-good
patch were hashed before attempt 1. No invocation was excluded or replaced.
There were no workspace failures, missing attempt artifacts, or free-space
violations.

## Result

| Attempt | Result | Tool calls | Patch | Offline grade | Diagnosis |
| ---: | --- | ---: | ---: | --- | --- |
| 1 | `OK` | 7 | 428 B | fail | suffix matching missed all unqualified forms; 120/125 full-suite tests passed |
| 2 | `COMMAND_TIMEOUT` | 12 | 871 B | fail | `get_type_hints` missed the `TYPE_CHECKING` unqualified form; 124/125 passed |
| 3 | `COMMAND_TIMEOUT` | 17 | 0 B | — | repeated edit calls did not match the source before the deadline |
| 4 | `NO_PATCH` | 0 | 0 B | — | asked for codebase context instead of using the available tools |

The two retained patches show partial progress, but both fail selected target
behavior rather than unrelated preservation tests.

## What this establishes

- A mixed test-and-source upstream commit can require a synthetic test/source
  split even when its behavior is suitable for an eval.
- The final oracle protects target generality and existing behavior while
  accepting the exact upstream fix and the complete upstream suite.
- Under this bare arm the task remains a floor. Its old Cycle 7 discrimination
  does not by itself qualify the rebooted task under the current protocol.
- The timeouts, edit mismatch, missing repository discovery, and unresolved
  `TYPE_CHECKING` form are possible Envelope or Engine research targets, but
  testing that requires a separately declared comparison.

## Evidence

The evidence bundle contains the direct-capture refusal, captured task,
protocol, final and superseded probes, receipts, full-suite and oracle-audit
JUnit records, and a script that recomputes both decisions from primary
artifacts:

```text
/Users/koudai/work/satyrn/evidence/2026-08-29-stringified-annotations-final-baseline-probe.tar.gz
sha256: 2020f2cfed8083b19b42bb2ac525e14561653a1e17198a03c52490f8255f49f7
```

Verify an extracted bundle with:

```bash
archive=${EVIDENCE_ARCHIVE:?Set EVIDENCE_ARCHIVE to the archive path}
(cd "$(dirname "$archive")" && shasum -a 256 -c "$(basename "$archive").sha256")
tmpdir=$(mktemp -d)
tar -xzf "$archive" -C "$tmpdir"
python3 "$tmpdir/satyrn-stringified-final-probe/recompute.py"
```
