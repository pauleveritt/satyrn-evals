# Product-path pilot: Baseline, Envelope, and Engine

**Date:** 2026-08-26–27
**Status:** pilot; completed locally; not a V5 baseline admission
**Model:** `omlx/gemma-4-12B-it-MLX-8bit`
**Pi:** 0.84.1
**oMLX:** 0.6.0rc1

## Question and scope

Can the rewritten Evals and Engine repositories reproduce the prior project's
product-level finding, and which layer produces the observed difference?

The measured batch separates Paul Everitt's three scenarios:

- **Baseline** — bare Pi receives the task's original high-level `brief.md`
  and Pi's built-in `read` and `edit` tools, with no Engine extension.
- **Envelope** — the same Pi, brief, and tools, plus only a 16-turn and
  30-tool-call budget. It has no loop breaker, locating contract, or bounded
  mutation tool.
- **Engine** — Pi receives the existing inspected locating contract and runs
  through Engine E5's loop breaker and bounded, revision-checked `read` and
  `edit` tools.

The Engine arm remains a **composite product comparison**. It measures the
handoff packet and Engine together and does not attribute an effect to the
mutation tool alone.

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
| Schedule | Baseline, Envelope, then Engine, interleaved for six blocks |
| Model | `omlx/gemma-4-12B-it-MLX-8bit` |
| Pi-declared context / max output | 80,000 / 8,192 tokens |
| oMLX configured context ceiling | 32,768 tokens |
| Tools exposed | `read`, `edit` |
| Outer deadline | 900 seconds |
| Isolation | Evals-owned detached worktree |
| Baseline prompt SHA-256 | `5945a5e2c41308ea107ab4b0e97d0e3f11fea04472b515aba646eb543ffc96a2` |
| Envelope prompt SHA-256 | same as Baseline |
| Envelope extension SHA-256 | `0448af1064f173e4018ff34b0953766a39f104401cb3b56d36a188f93f3919e7` |
| Engine prompt SHA-256 | `203b31bb96924d5a9d08ce51f30ee0171222167704ab2861b3791f52d0d2dffb` |

The budget extension comes from the old evidence repository. It was originally
calibrated with `read` and `write`; this pilot keeps `read` and `edit` common
across all arms so Envelope differs from Baseline only by its two budgets.

Every available measured transcript's first user message matched its arm's
frozen hash. The one absent transcript belongs to a Baseline attempt killed at
the recorded 900-second outer deadline, before its child could publish the
artifact. No attempt was dropped, retried, or reclassified.

## Primary result

| Arm | Oracle passes | Attempt result |
| --- | ---: | --- |
| Baseline | 0/6 | 5 `NO_PATCH`, 1 `COMMAND_TIMEOUT` |
| Envelope | 0/6 | 6 `NO_PATCH` |
| Engine | 6/6 | 6 `OK` |

This is a diagnostic pilot, not the deferred claims layer. Counts are the
result; no confidence interval or superiority claim is attached to them.

The excluded smoke runs had the same direction: Baseline and Envelope
`NO_PATCH`, Engine oracle `pass`.

## What happened

Five Baseline attempts exited normally with no patch; one reached Evals' outer
900-second deadline. Its five retained transcripts contain 34 tool calls and
24 tool errors; the timed-out child's missing transcript means those totals
undercount the arm. The model repeatedly tried to read a directory, called
execution tools that were not available, or guessed paths that did not exist.
This is consistent with the prior project's tool-discovery and enumeration
wall, not an unavailable model server or an Evals infrastructure failure.

Envelope did not move the task off the floor: all six attempts produced no
patch. Its transcripts contain 69 tool calls and 50 tool errors. The turn cap
fired in one run; the tool-call cap never fired. Four other runs ended with
`stopReason=length` before reaching the turn cap. A turn limit does not bound
the tokens or latency of an already-admitted turn, so four Envelope attempts
still lasted roughly 398–431 seconds. Its median elapsed time was about 404
seconds, compared with about 401 for Baseline. These times are diagnostic only
because generated content and the shared model server's prefix cache varied.

Every Engine run used `read` followed by `edit`, with no tool error, and
completed in three turns. All six patches passed the recorded two-test oracle
and were byte-identical:

```text
sha256:dc29f84a20933c21d8ff23718196a3529134b8cd50618a78aaf87a38d81984d4
```

They changed only `src/svcs/_core.py` and had a median elapsed time of about 42
seconds. No run retained a worktree, and the temporary svcs clone plus both
Satyrn source checkouts remained clean.

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
- This pilot uses the rewritten repositories end to end and separates bare Pi
  plus brief, the same path with budgets only, and locating contract plus
  Engine: 0/6, 0/6, and 6/6.

The old result is stronger evidence for the causal value of packet content.
This pilot is evidence that the current two-repository product path preserves
the useful effect and that its isolation, artifact, and offline-grading seams
work with a real local model.

## What this does not establish

- It does not show that Engine's mutation tool alone improves correctness.
- It does not show an Envelope correctness or latency benefit on this task.
- It does not establish superiority across tasks or models.
- It does not test Paul's current Mellum/AgentClinic observation. Only the
  Gemma model used by the existing pilot is installed locally, and the old
  evidence already places detailed AgentClinic at a 16/16 ceiling for it.
- It does not solve the suite-headroom requirement. Baseline floored at n=6,
  so this task remains a capability wall used here for a product demonstration,
  not an admissible V5 diagnostic workload under `BRIEF.md`'s middle-band rule.
- It does not compare wall-clock time; elapsed time is diagnostic context only.

## Local evidence bundle

The frozen conditions, task materialization, adapter scripts, attempt records,
receipts, patches, transcripts, summaries, and all three pilot reports are
archived outside the repository at:

```text
/Users/koudai/work/satyrn/evidence/2026-08-27-three-arm-product-path-pilot.tar.gz
```

The archive is local evidence, not a repository or CI dependency:

```text
sha256:11385fceccf38878feae3efd9dcda09c2568ad5f58fc5c05edab900165cda6b2
```
