# D1 design: Diátaxis documentation orientation

## Decision

Adopt Diátaxis as the public documentation structure for Satyrn Evals. The
site will reveal the project through a small, successful experience before it
asks a reader to understand its architecture, terminology, phase history, or
research record.

The front-door promise is:

> Satyrn Evals turns a candidate code change into actionable evidence.

"Actionable" means a contributor can inspect the preserved patch, transcript,
receipt, or summary to decide what failed and where to improve the engine. It
does not promise a benchmark, a confidence claim, or a security sandbox.

## Context

Evals has a deliberately rich surface: task capture, an executable engine
seam, artifact preservation, offline grading, diagnostic runs, and a
spec-driven research record. The current front page accurately presents all
of it, but introduces status, the engine seam, and later-phase vocabulary
before a reader has seen one evaluation complete. Its `usage` page combines a
learning example, goal-directed instructions, and exhaustive command details.

This conflicts with the project's concept budget. It also makes the strong
evidence story harder to discover: a first-time reader should first see a
known-good patch turn into a receipt, then ask why a receipt is trustworthy.

Diátaxis distinguishes four reader needs:

- **Tutorials** are learning-oriented, guided successful experiences.
- **Guides** are goal-oriented instructions for an evaluator's real work.
- **Reference** is complete, neutral machinery lookup.
- **Topics** are explanation that gives context and supports reflection.

The labels in the navigation will use these familiar jobs rather than require
the reader to know the framework. The framework itself is a maintainer-facing
documentation convention, not a new Evals product concept.

## Audience and first outcome

| Reader | First question | First outcome |
| --- | --- | --- |
| Learner | What is Evals for? | Grades a bundled known-good patch and reads `pass` in its receipt. |
| Evaluator | How do I preserve and assess an attempt? | Finds the attempt guide and the resulting artifacts. |
| Contributor | Why is the system shaped this way? | Finds the evidence lifecycle, trust-boundary explanation, and development record. |

The learner tutorial uses `format_number`, not `local-pings`: it is bundled,
small, deterministic, and needs neither a model nor a foreign project. The
de-admitted `local-pings` task remains appropriate for grader/smoke/regression
reference, not for the first diagnostic lesson.

## Information architecture

```text
Start here
  Why Satyrn Evals
  Tutorial: see one verdict

Use Evals
  Evaluate one attempt
  Capture a task from a fixing commit
  Run a diagnostic batch

Understand
  The evidence lifecycle
  Trust boundaries and limits
  Valid tasks and diagnostic workloads

Reference
  CLI reference
  Task and artifact formats
  Glossary

Development
  Architecture
  Contributing
  How we work
  Roadmap and research archive
```

The public front page contains a plain-language promise, a five-stage visual
of the evidence lifecycle, two clear next links (the tutorial and evaluator
guide), a short scope boundary, and a one-sentence current status. It does not
list historical phases. The roadmap retains that job.

The initial path uses ordinary words first and introduces a formal term only
when it helps the reader perform the next action:

| First encounter | Formal term, when needed |
| --- | --- |
| code change to test | task |
| saved result | patch, transcript, receipt |
| trusted test result | verdict and oracle |
| repeated attempts | diagnostic run |

The glossary remains searchable reference; it is not prerequisite reading.

## Scope

D1 creates the public front door, one runnable tutorial, the section indexes,
and the first explanatory pages. It redirects the existing long CLI page to a
reference role, extracts goal-named guides without changing CLI behavior, and
moves the development record behind the user-facing path. README becomes a
terse equivalent of the front door.

Every command in a tutorial or guide is checked from a checkout. The tutorial
states expected observable output and points out that the receipt, rather than
the command exit status, is the result.

## Out of scope

- Changing `grade`, `capture`, `attempt`, `run`, task formats, or the engine
  seam.
- Re-admitting `local-pings`, claiming model quality, or introducing claims
  layer terminology.
- Publishing V6–V8 as operational documentation before those behaviors ship.
- Deleting or rewriting historical specs, plans, and research records.
- Creating an empty documentation taxonomy: each new section has reader-ready
  content before it appears in navigation.

## Acceptance

1. A reader can describe the project's purpose and find a first action from
   the front page without first reading the glossary or phase history.
2. A checkout user can complete the `format_number` tutorial and observe a
   `pass` verdict in a receipt without a model or network request from Evals.
3. An evaluator can locate capture, single-attempt, and diagnostic-batch
   instructions by desired outcome rather than by knowing a command name.
4. The exact CLI flags and artifact formats remain available as reference.
5. Sphinx builds with warnings treated as errors and the document-cap checker
   passes.

## Cross-roadmap gates

| Dependency | Owner | Status | D1 may proceed with | Waits for |
| --- | --- | --- | --- | --- |
| V6 session eval | Evals V6 | **complete** — shipped 2026-09-04, after D1 (reconciled on the merge onto main) | D1 proceeded per this row; V6 operational docs now belong on main. | — (met) |
| Engine telemetry across the seam | satyrn-engine | deferred | Document the current counts-only `run` summary and its limits. | Engine-published telemetry for tool-call/repeat/churn/context guidance. |

## Amendment (2026-09-04, reopened)

A deep review found D1 directionally strong but not honestly complete; the
maintainer reopened the phase rather than opening a corrections phase. Every
finding below was verified against this branch before amending. Root cause of
findings 2 and 8: the plan's verification step ran `git diff --check` on the
working tree only, not the `main...HEAD` range — the unscoped check is itself
part of the defect, and the plan is corrected in place.

1. The promised "Task and artifact formats" reference was never added;
   Reference held only the CLI and the glossary (this spec's Information
   architecture vs `docs/reference/index.md`). Added as
   `docs/reference/formats.md` — the single home for the task directory,
   manifest fields, receipt, capture record, attempt directory and record,
   and run summary; `usage.md` keeps flags, exit codes, and examples and
   links to it.
2. The guides did not compose from a clean checkout: the tutorial ran
   `uv run satyrn-evals` (`docs/tutorials/see-one-verdict.md:28`) while the
   guides ran bare `satyrn-evals` (`docs/guides/capture-a-task.md:16`,
   `docs/guides/evaluate-an-attempt.md:24`,
   `docs/guides/run-a-diagnostic-batch.md:15`), and the capture→attempt
   handoff dropped `--tasks-root`. Guides now run `uv run` from the checkout
   and carry `--tasks-root` through capture → attempt → run.
3. The capture guide named `capture.json`
   (`docs/guides/capture-a-task.md:20`); capture writes
   `<name>.capture.json` (`src/satyrn_evals/capture.py:426`).
4. The attempt guide described refusals as artifact-incompleteness only
   (`docs/guides/evaluate-an-attempt.md:42`); `attempt.py:40-43` also refuses
   as `WORKSPACE_FAILED`, `COMMAND_TIMEOUT`, and `CLEANUP_FAILED`.
5. The diagnostic-batch guide claimed a smoke "confirms that the path starts
   the model and produces the artifacts you expect"
   (`docs/guides/run-a-diagnostic-batch.md:9`); the V5d spec permits
   `NO_PATCH`/`COMMAND_TIMEOUT` smoke passes on positive evidence the model
   started.
6. `docs/architecture.md`'s module table omitted `run.py` and `summary.py`,
   and its `cli.py` row omitted `run`.
7. The glossary's `task` entry implied every task ships both fixtures;
   capture produces known-good only and `known_broken` is optional
   (`src/satyrn_evals/manifest.py:96-99`).
8. Trailing blank lines at EOF in this spec and its plan, found by
   `git diff --check main...HEAD` — a check the plan's verification step did
   not scope.
9. The receipt example (then in `usage.md`, now `docs/reference/formats.md`
   and the front page) showed two of the task's four executed test IDs and
   `passed: 2`. Recomputed during this amendment by running the tutorial's
   grade command: the real receipt executes four IDs and records
   `passed: 4`. Corrected in both places to the recomputed output.

Beyond the corrections, the reopened scope adds: the concrete suite example
(the `format_number` receipt) followed by its runnable command on the
front page, and a trailing-whitespace/EOF check in `tools/lint_docs.py` so
finding 8's class is caught mechanically in live documents
(`docs/superpowers/research/` stays exempt as the preserved record).
