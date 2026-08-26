# Product-path pilot: bare Pi versus inspected handoff plus Engine

**Date:** 2026-08-26  
**Status:** pilot; completed locally; not a V5 baseline admission  
**Model:** `omlx/gemma-4-12B-it-MLX-8bit`  
**Pi:** 0.84.1  
**oMLX:** 0.6.0rc1

## Question and scope

Can the rewritten Evals and Engine repositories reproduce the prior project's
product-level finding: a small model given an inspected, concrete handoff and
the bounded Engine path succeeds where bare Pi given only a high-level task
does not?

This is deliberately a **composite product comparison**:

- **Baseline** — bare Pi receives the task's original high-level `brief.md`
  and Pi's built-in `read` and `edit` tools.
- **Product** — Pi receives the existing inspected locating contract and runs
  through Engine E5's loop breaker and bounded, revision-checked `read` and
  `edit` tools.

The result measures the handoff packet and Engine together. It does not
attribute an effect to the mutation tool alone.

## Why this task

`stringified-annotations` was the only task to discriminate the two arms in
the old Phase 7 confirmatory batch: locating contract 8/8, brief 3/8. That
result is recorded at local-ai-pi commit `8588ba4bf35abf4a4ea1d3cd591741025063e119`
in its [Cycle 7 confirmatory result](https://github.com/pauleveritt/local-ai-pi/blob/8588ba4bf35abf4a4ea1d3cd591741025063e119/docs/superpowers/research/2026-08-11-phase7-cycle7-confirmatory-result.md).
The new pilot uses the same upstream `hynek/svcs` pair and the same brief and
locating-contract texts, but exercises the rewritten `satyrn-evals attempt`
to `satyrn-engine attempt` path.

The upstream fix commit adds both regression tests and source. V2 capture
requires failing tests to exist at the base, so an experiment-only clone split
those exact changes into two commits: the target's test change first, then its
source change. Capture then passed all four checks and the generated
known-good patch independently graded `pass` before any model attempt.

```text
upstream base:       4b05ab8465f3d9a5ce7d1e40eaf808b0cb92a26c
upstream fix:        f81e493487d872198981fa6cefb3a0d93ab03c08
synthetic test base: e1489c445283b650febd8f1a32df08ef85ab9b5e
synthetic source fix: 22df960696a2b76a37165067a000e0d163398915
```

## Conditions fixed before the measured batch

| Condition | Value |
| --- | --- |
| Task | `stringified-annotations` |
| Repetitions | one smoke per arm, excluded; then n=6 per arm |
| Schedule | Baseline then Product, interleaved for six blocks |
| Model | `omlx/gemma-4-12B-it-MLX-8bit` |
| Context / max output | 80,000 / 8,192 tokens |
| Tools exposed | `read`, `edit` |
| Outer deadline | 900 seconds |
| Isolation | Evals-owned detached worktree |
| Baseline prompt SHA-256 | `5945a5e2c41308ea107ab4b0e97d0e3f11fea04472b515aba646eb543ffc96a2` |
| Product prompt SHA-256 | `203b31bb96924d5a9d08ce51f30ee0171222167704ab2861b3791f52d0d2dffb` |

Every measured transcript's first user message matched its arm's frozen hash.
No attempt was dropped, retried, or reclassified.

## Primary result

| Arm | Oracle passes | Refusals |
| --- | ---: | ---: |
| Baseline | 0/6 | 6 `NO_PATCH` |
| Product | 6/6 | 0 |

This is a diagnostic pilot, not the deferred claims layer. Counts are the
result; no confidence interval or superiority claim is attached to them.

The excluded smoke run had the same direction: Baseline `NO_PATCH`, Product
oracle `pass`.

## What happened

All six Baseline commands exited normally but produced no patch, so Evals
recorded six `NO_PATCH` refusals. Each model run ended with
`stopReason=length`, after 8–23 turns and 7–22 tool calls. Across the batch,
66 of 77 tool calls failed. The model repeatedly tried to read a directory,
called execution tools that were not available, or guessed paths that did not
exist. This is consistent with the prior project's tool-discovery and
enumeration wall; it is not an unavailable model server or an Evals
infrastructure failure.

Every Product run used `read` followed by `edit`, with no tool error, and
completed in three turns. All six patches passed the recorded two-test oracle
and were byte-identical:

```text
sha256:dc29f84a20933c21d8ff23718196a3529134b8cd50618a78aaf87a38d81984d4
```

They changed only `src/svcs/_core.py`. No run retained a worktree, and the
temporary svcs clone plus both Satyrn source checkouts remained clean.

## A narrower comparison run first

Before changing the task information between arms, a separate pilot held the
locating-contract user prompt constant and changed only the mutation boundary:
Pi built-in edit versus Engine E5. Both arms passed 4/4 and all eight patches
were byte-identical. That task/prompt combination was at ceiling and supplied
no evidence that the mutation boundary alone improved correctness.

This null result is why the primary result above is described as a composite
product effect, not an Engine-mutator effect.

## Relationship to old evidence

The result agrees in direction with the Phase 7 confirmatory result, but it is
not a direct replication:

- Phase 7 used the old bounded implementer in both arms and isolated locating
  contract versus brief content: 8/8 versus 3/8.
- This pilot uses the rewritten repositories end to end and compares bare Pi
  plus brief against locating contract plus Engine: 6/6 versus 0/6.

The old result is stronger evidence for the causal value of packet content.
This pilot is evidence that the current two-repository product path preserves
the useful effect and that its isolation, artifact, and offline-grading seams
work with a real local model.

## What this does not establish

- It does not show that Engine's mutation tool alone improves correctness.
- It does not establish superiority across tasks or models.
- It does not solve the suite-headroom requirement. Baseline floored at n=6,
  so this task remains a capability wall used here for a product demonstration,
  not an admissible V5 diagnostic workload under `BRIEF.md`'s middle-band rule.
- It does not compare wall-clock time; elapsed time is diagnostic context only.

## Local evidence bundle

The frozen conditions, task materialization, adapter scripts, attempt records,
receipts, patches, transcripts, summaries, and both pilot reports are archived
outside the repository at:

```text
/Users/koudai/work/satyrn/evidence/2026-08-26-product-path-pilot.tar.gz
```

The archive is local evidence, not a repository or CI dependency:

```text
sha256:f899a7cffc6c9f55a4643a1b0733f4ec5111506fca7a31426fb67a2ecae89f75
```
