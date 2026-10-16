---
title: Using Evals
---

# Using Evals

`satyrn-evals` has two surfaces. Four commands run evals in a project of your
own: `init`, `doctor`, `run` and `report`. This page is their reference. The
expert commands that the project itself uses for campaigns are listed at the
end. The four commands live on the `docs/first-run-cli` branch until it merges.

For a guided walk through the four commands, start with
[Your first run](user-journey.md).

## The project `init` creates

```text
my-first-eval/
  satyrn.yaml                                 what to run: task, arm, model, budgets
  arms/baseline.json                          how to run it: agent command, tools, model
  eval-tasks/format_number/                   the example task, copied from the package
  records/my-first-eval-format_number.json    written by the first `run`, then committed
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
| `backend` | `openai` | the API the record names: `openai` for any OpenAI-compatible server (ollama, unsloth), or `omlx`; `init` writes it from `--backend` |
| `record` | `records/<project>-<task>.json` | the run record; its file name also names the results folder under `~/satyrn-runs/` |
| `rung` | `contract` | which contract text the agent gets; `contract` is the task's own |
| `run.n` | `1` | attempts per arm |
| `run.k` | `1` | attempts at a time, 1 to 3 |
| `run.purpose` | `development` | see below |
| `run.mode` | `attended` | `attended` or `batch` |
| `run.token-budget` | `32000` | tokens one attempt may spend |
| `run.turn-budget` | `48` | turns one attempt may take |
| `run.max-minutes` | `60` | wall clock for the whole run, all attempts included |

Three limits are checked when `run` builds the record, and a limit that fails
prints as a message naming the key to change:

- **`max-minutes` bounds the whole run, and one attempt must fit.** An
  attempt gets a 30-minute backstop plus 5 minutes of margin, so the floor is
  35 minutes. Attempts beyond the first share whatever is left; with the
  default 60 minutes and `n: 1`, a first run uses about a sixth of its budget.
- **`mode` caps `n` and `max-minutes`.** `attended`: at most 8 attempts and
  60 minutes. `batch`: at most 12 attempts and 720 minutes.
- **`campaign` and `route-proof` need a decision rule**, which only the expert
  `record new` command can write. `development` and `admission` work from
  `satyrn.yaml`; `admission` is a deciding record, so `run` keeps every check
  on for it.

For a first run, leave the defaults alone.

## `init [DEST]`

Scaffolds `satyrn.yaml`, the example task and a starter arm in `DEST`, which
defaults to the current folder. The record is named after `DEST`, so each
project gets its own results folder.

| option | default | meaning |
| --- | --- | --- |
| `--model` | `unsloth/ornith-ai/Ornith-1.5-9B-GGUF` | the `provider/model` the arm serves |
| `--backend` | `openai` | the server you run: `ollama`, `unsloth`, `omlx` or `openai`; `ollama` and `unsloth` are recorded as `openai`, the API they speak |
| `--task` | `format_number` | which bundled task to copy |
| `--arm` | `baseline` | the arm's name, and its file name |
| `--pi-version` | `0.85.1` | the Pi version the arm records |
| `--force` | off | overwrite files that already exist |

Without `--force`, `init` refuses to touch a file that is already there.

`init` does **not** write Pi's `~/.pi/agent/models.json`. `run` needs an entry
there for your model; the next section has one.

## Pi's `models.json` entry

Pi reads `~/.pi/agent/models.json`. One provider block per server, one entry
per model. For ollama:

```json
{
  "providers": {
    "ollama": {
      "baseUrl": "http://localhost:11434/v1",
      "api": "openai-completions",
      "apiKey": "ollama",
      "models": [
        {
          "id": "ornith-1.5:9b",
          "contextWindow": 32768,
          "maxTokens": 16000,
          "reasoning": true,
          "samplingParams": {
            "temperature": 0.6,
            "top_p": 0.95,
            "top_k": 20,
            "min_p": 0.0,
            "presence_penalty": 0.0,
            "repetition_penalty": 1.0
          }
        }
      ]
    }
  }
}
```

`id` is the part after the provider in `model`. `contextWindow` should match
the context the server actually serves (`ollama ps` shows it). The
`samplingParams` are the values the project's own arms declare for Ornith;
they are optional for a first run. Before the first attempt, `run` checks that
an entry for your model exists. Values are compared only when the arm carries
an `inference` block, which the starter arm does not.

## `doctor`

Checks this machine before you spend a budget. Each line is `OK` or
`MISSING`, and every `MISSING` comes with a one-line fix.

| option | meaning |
| --- | --- |
| `--config PATH` | the `satyrn.yaml` to read; default: the nearest one at or above the current folder |
| `--check-servers` | also ask the model server whether it serves the configured `model` (network) |

It checks `git`, `uv`, `pi`, a Python at or above the version the harness
needs, and that a server program (`ollama`, `unsloth` or `omlx`) is on your
path; the `model backend` line names the ones it found. With
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
satyrn-evals run --dry-run   # writes records/<project>-<task>.json and checks it
git add .
git commit -m "freeze the run"
satyrn-evals run
```

A plain `run` on a fresh project writes the record and stops with *the record
was just written*, followed by the `git add` and `git commit` to run. A record
that was edited after its commit stops with *the run record is not frozen*.

`run` prints nothing while attempts are running, then one JSON block with the
`status`, the `night` (the results folder) and the `result` file. Before the
first attempt it checks that the record is committed, that the model server
answers and lists the model, and that Pi's `models.json` has an entry for it.
Then each attempt runs in a fresh Git worktree of the task, with the system
Python only (the agent cannot run the task's tests itself), and is graded
offline from the saved patch. Results land in two places:

- `records/<record name>.result.json`, next to the record: what `report` reads.
- `~/satyrn-runs/<record name>/`: per attempt, `timeline.jsonl` (one event per
  line), `transcript.txt` (the full Pi session as JSON lines), `patch.diff` and
  `receipt.json` (the grade); per arm, `summary.json` with verdict counts, tool
  calls and pathology counters.

Running the same project again finds its finished results folder and reports
it again. To run again for real, move the folder aside or change `record:`.

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
