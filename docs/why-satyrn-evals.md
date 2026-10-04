# Why Satyrn has its own evals

Satyrn's charter is to keep a small model on track, so a Python developer can
use local AI and stay at the wheel. Every part of the eval harness follows from
that sentence. This page says how, cites the parts of Satyrn Evals that carry
it, and compares one well-known framework, Harbor, as an example.

## The model on the developer's machine

Public agent benchmarks are aimed at hosted frontier models: large models
behind an API, run at scale in cloud sandboxes, ranked on a leaderboard. The
question they answer is "how capable is this model?"

Satyrn asks a different question: can a 9B model running on a laptop finish a
real Python task, and if not, what would help it? That changes what has to be
measured and controlled.

- **The model is served locally, and its settings are part of the
  experiment.** Release two ran Ornith 1.5 9B in MLX 8-bit through oMLX. Each
  run record freezes the model, sampling, context, and per-turn cap, verified
  against the server and client configuration rather than declared
  ([the numbers](numbers.md), "What was compared").
- **Budgets are tokens and turns, not wall-clock time.** A frozen record names
  `token_budget`, `turn_budget`, and a `command_backstop_s` that exists only to
  catch a hung machine. On a shared laptop, wall-clock time measures the
  machine; tokens and turns measure the model.
- **Throughput is a measured constraint.** Running three cells at once was
  adopted only after measuring it on live completions
  (`evidence/2026-09-15-finishing-counterfactual/run-2/q3stats.md`).
- **Small-model failure modes need their own instruments.** A 9B model
  produces failures a frontier model rarely does: a turn that runs to the cap
  with no tool call, repeated identical edits, searching the filesystem for the
  grader. The census has a `runaway` class for the first, and
  [remediations](remediations.md) records the rest, each with the detector
  that found it.

## Evidence fine enough to choose a remedy

A pass rate says whether something works. It does not say what to build next.
Satyrn exists to build remedies for small models, and a remedy has to be aimed
at a cause. The project learned this the hard way: "We built the remedy for
the failures we saw, and the failures we saw were the harness's"
([lessons](lessons.md)). So the harness is built to produce evidence at the
level a remedy is designed against.

- **Every attempt keeps its evidence.** The patch and transcript are saved
  before grading, and grading reads only what was saved. A grading fix is
  re-applied to retained cells with `rescore`, with no new model run
  (`src/satyrn_evals/rescore.py`).
- **Verdicts are per test.** The hidden suite runs under a pytest plugin,
  `-p satyrn_evals.oracle_hook`, which writes one outcome per test ID. Each
  task's manifest names the `expected_test_ids` it must see, so a missing test
  is a finding, not a silent pass.
- **A run can be read at a declared line.** A record's `line_token_budget`
  and `line_turn_budget` snapshot a cell's patch at the transcript line that
  crosses either one, and `satyrn-evals grade-line` grades those snapshots
  offline (`src/satyrn_evals/line_grade.py`). A cell given 48,000 tokens can
  still answer "had it passed by 32,000?"
- **Failures are classified before anything is built.** The release-two census
  classified every Baseline cell by why it failed: information, ambiguity,
  capability, budget, finishing, runaway
  (`evidence/2026-09-16-census/classes-summary.md`). The finishing class, where
  a cell reached a passing state and kept going, is what the Engine's
  finish-on-green behaviour targets.
- **A remedy is estimated offline before it is built.** The finishing
  counterfactual replayed retained cells to ask how many a stop-at-green rule
  would have rescued (`evidence/2026-09-15-finishing-counterfactual/`).
- **Events are counted from the transcript.** Tool calls are counted from
  `tool_execution_start`, one per call, so a cost figure means the same thing
  in both arms.

## A harness a Python developer already knows

The developer Satyrn serves writes specs and tests, not agent infrastructure.
The harness is built from the tools that developer already uses, so reading a
task, a grader, or a result needs nothing new.

- **A task is a Python repository.** Each task under
  `src/satyrn_evals/tasks/` has a `base/` tree with a `pyproject.toml` and
  `uv.lock`, a `manifest.json`, an `overlay/` of hidden tests, and two
  fixtures.
- **The prompt reads like a plan step.** The `selfhost-run-record-gate`
  contract says which files to create, which interfaces to produce, and to
  write failing tests first, then implement, then run `uv run pytest`.
- **The grader is pytest.** The hidden suite is ordinary test files; the
  public suite is `uv run pytest -q`. A known-good and a known-broken patch
  prove each grader in both directions.
- **Results are diffs and JSON.** A cell's output is a patch you can apply and
  a transcript you can read. A run record is one JSON file in `records/`.
- **No containers.** The model runs as a second local user, `satyrn-cell`,
  with no view of grader material, and preflight checks the workspace before
  any cell starts. The checks run through `just gates`.
- **The default test tier runs offline.** No model, network, or subprocess;
  the tripwire in `tests/conftest.py` enforces it.

## An example: Harbor

[Harbor](https://docs.harborframework.com/core-concepts/tasks/overview), from
the team behind Terminal-Bench, is a framework for running agent evaluations at
scale. Its task format (`task.toml` schema 1.4, read 2026-10-03) is close to
Satyrn's in structure, and the two projects reached several of the same
decisions on their own.

| | Harbor | Satyrn Evals |
|---|---|---|
| prompt | `instruction.md` | manifest `contract`, with prompt rungs in `contracts` |
| environment | `environment/Dockerfile`, compose, or Apptainer | a `base/` Git tree at a recorded `base_sha`, run as `satyrn-cell` |
| hidden tests | `tests/`, copied in after the agent finishes | `overlay/`, proven absent from the workspace |
| verdict | `test.sh` writes `reward.txt` or `reward.json` | the pytest hook writes one outcome per expected test ID |
| reference solution | `solution/solve.sh` | `fixtures/known-good.patch`, plus `known-broken.patch` |
| budget | `[agent].timeout_sec` | `token_budget`, `turn_budget`, a per-turn cap |
| when grading happens | in the live container, after the run | offline, from the saved patch and transcript |
| run definition | job config: agents × tasks × attempts | frozen record: also `stop_rule`, `decision_rule`, `task_tree_sha256` |
| trace | ATIF trajectory | Pi transcript, counted from `tool_execution_start` |
| where it runs | Docker locally, or cloud sandboxes | one laptop, local model server |

**Where they agree.** The verdict comes from a file the tests write, not from
stdout or an exit code. Grader tests are hidden from the agent. Every task
ships a reference solution that shows it can be solved.

**Where Harbor fits better.** Comparing many agents and models across
established benchmarks, multi-container environments, cloud sandboxes, and a
shared task registry with adapters for existing datasets.

**Where Satyrn needs something else.** Grading saved evidence, so a cell can
be re-read at a budget line or re-scored after a grader fix; a grader proven
against a known-broken patch; token and turn budgets for a local model; and
run records that freeze the decision rule before the run.

The formats map closely enough that a Satyrn task could be exported as a
Harbor task, with the contract as `instruction.md`, the overlay and hook in
`test.sh`, and the known-good patch in `solve.sh`. That would let Satyrn's
tasks run against other agents; the evidence Satyrn needs would still come
from its own harness.
