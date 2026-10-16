---
title: Using Evals
---

# Using Evals

`satyrn-evals` has two surfaces. Four commands run evals in a project of your
own: `init`, `doctor`, `run` and `report`. This page is their reference. The
expert commands that the project itself uses for campaigns are listed at the
end.

For a guided walk through the four commands, start with
[Your first run](user-journey.md).

<!-- TODO(benx): written against the cli-ux branch. -->

## The project `init` creates

```text
my-first-eval/
  satyrn.yaml                  what to run: task, arm, model, budgets
  arms/baseline.json           how to run it: agent command, tools, model
  eval-tasks/format_number/    the example task, copied from the package
  records/format_number.json   written by the first `run`, then committed
```

The project must be a Git repository before the first `run`: the run record is
read only once it is committed, unchanged.

## `satyrn.yaml`

Every key has a default except `model`. Keys under `run:` go in that block.

| key | default | meaning |
| --- | --- | --- |
| `task` | `format_number` | the task folder to run, under `tasks-root` |
| `tasks-root` | `eval-tasks` | where tasks live, relative to `satyrn.yaml` |
| `arm` | `baseline` | reads `arms/<arm>.json` |
| `model` | none | `provider/model`, as Pi knows it, for example `ollama/ornith-1.5:9b` |
| `backend` | `openai` | `openai` for any OpenAI-compatible server (ollama, unsloth), or `omlx` |
| `record` | `records/<task>.json` | the run record; its file name also names the results folder |
| `rung` | `contract` | which contract text the agent gets; `contract` is the task's own |
| `run.n` | `1` | attempts per arm |
| `run.k` | `1` | attempts at a time, 1 to 3 |
| `run.purpose` | `development` | see below |
| `run.mode` | `attended` | `attended` or `batch` |
| `run.token-budget` | `32000` | tokens one attempt may spend |
| `run.turn-budget` | `48` | turns one attempt may take |
| `run.max-minutes` | `60` | wall clock for the whole run |

Three limits are checked when `run` builds the record:

- **`n` and `max-minutes` are capped by `mode`.** An `attended` run allows at
  most 8 attempts and 60 minutes; a `batch` run, 12 attempts and 720 minutes.
- **`max-minutes` has a floor.** Each attempt gets a 30-minute backstop plus
  5 minutes of margin, so a run needs at least 35 minutes.
- **Only `development` works from `satyrn.yaml`.** The other purposes
  (`admission`, `campaign`, `route-proof`) need a decision rule, which only
  the expert `record new` command can write.

> **Give each project its own `record` name.** Results go to
> `~/satyrn-runs/<record name>/`, and two projects with the same task, model
> and budgets write the same record. With the default name, the second
> project's `run` finds the first one's finished run and reports it again,
> without running anything. `record: records/ornith-first.json` gives the run
> its own folder, `~/satyrn-runs/ornith-first/`.

## `init [DEST]`

Scaffolds `satyrn.yaml`, the example task and a starter arm in `DEST`, which
defaults to the current folder.

| option | default | meaning |
| --- | --- | --- |
| `--model` | `unsloth/ornith-ai/Ornith-1.5-9B-GGUF` | the `provider/model` the arm serves |
| `--backend` | `openai` | written to `satyrn.yaml` and the arm |
| `--task` | `format_number` | which bundled task to copy |
| `--arm` | `baseline` | the arm's name, and its file name |
| `--pi-version` | `0.85.1` | the Pi version the arm records |
| `--force` | off | overwrite files that already exist |

Without `--force`, `init` refuses to touch a file that is already there.

`init` does **not** write Pi's `~/.pi/agent/models.json`. `run` needs an entry
there for your model; [Your first run](user-journey.md#5-point-pi-at-ollama)
shows one for ollama.

> **Do not pass `--backend ollama`.** `init` accepts it, but `run` then
> refuses the record. Use `--backend openai` for ollama.

## `doctor`

Checks this machine before you spend a budget. Each line is `OK` or
`MISSING`, and every `MISSING` comes with a one-line fix.

| option | meaning |
| --- | --- |
| `--config PATH` | the `satyrn.yaml` to read; default: the nearest one at or above the current folder |
| `--check-servers` | also ask the model server whether it serves the configured `model` (network) |

It checks `git`, `uv`, `pi`, a Python at or above the version the harness
needs, and a model backend (`ollama`, `unsloth` or `omlx`) on your path. With
`--check-servers` it adds the model server, reached through the provider entry
in Pi's `models.json`. Exit code 0 means everything is met.

## `run`

Writes the run record if it does not exist yet, then launches its attempts.

| option | meaning |
| --- | --- |
| `--config PATH` | as for `doctor` |
| `--dry-run` | write and check the record, launch nothing |
| `--no-settings` | skip the check of the arm against Pi's `models.json`; development records only |

The order that works on a fresh project:

```bash
git init
satyrn-evals run --dry-run   # writes records/<task>.json and checks it
git add .
git commit -m "freeze the run"
satyrn-evals run
```

A plain `run` on a record that is not committed writes it and stops with
*the run record is not frozen*. Commit it and run again.

Before the first attempt, `run` checks the model server and compares the arm
with Pi's `models.json`. Then each attempt runs in a fresh Git worktree of the
task and is graded offline from the saved patch. Results land in two places:

- `records/<record name>.result.json`, next to the record: what `report` reads.
- `~/satyrn-runs/<record name>/`: per attempt, the transcript, the patch, the
  grade receipt; per arm, `summary.json` with tool calls and pathology counters.

## `report [RECORD]`

Prints a readable summary of a finished run. Without `RECORD`, it reads the
record named in `satyrn.yaml`.

```text
task:     format_number
rung:     contract
purpose:  development
status:   complete
cells:    1

arm baseline: 1/1 passed (OK=1)
```

The last line counts passes over finished attempts, then how each attempt
ended: `OK` means the agent ran to completion, whatever the verdict.

| option | meaning |
| --- | --- |
| `--config PATH` | as for `doctor` |

## Expert commands

Everything else passes straight through to the commands the project uses for
its own campaigns. Each has its own flags: `satyrn-evals <command> --help`.
[Getting started](user-guide.md) walks the longer path, including the Engine
arm.

| command | what it does |
| --- | --- |
| `grade` | apply a patch to a task and record the verdict, offline |
| `regrade` | re-grade a preserved attempt and rewrite its record |
| `qualify` | offline qualification: fixtures both ways, a live harvest, known-good three times |
| `capture` | turn a fixing commit into a task |
| `attempt` | run one attempt command, preserve patch and transcript, grade offline |
| `repeat` | repeat an attempt command n times and write a summary |
| `summarize` | rebuild `summary.json` for a run folder |
| `session` | send ordered prompts to one conversation, snapshot checkpoints, grade offline |
| `record new` | write a run record from flags |
| `launch` | run a frozen record's cells, or check a record |
| `grade-line`, `grade-sensitivity` | campaign readings over a finished night |
