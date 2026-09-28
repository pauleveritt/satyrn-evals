# Getting started — run Satyrn on your machine

This is a **user's guide**, not a contributor's guide. It shows a developer or
a non-developer how to run the Satyrn stack on their own machine and grade a
task, using one of three local model backends:

> **Guided tour?** [Your first run](user-journey.md) walks the whole thing as a
> journey, ollama-only, from first principles to reporting your own result.
> This page is the reference it links back to: denser, and covering all three
> backends.

- **unsloth** — a locally quantised model on a GPU (Linux or Windows), served
  through [unsloth](https://unsloth.ai).
- **ollama** — a locally quantised model on CPU or GPU (Linux or Windows),
  served by [ollama](https://ollama.com).
- **oMLX** — a locally quantised model on Apple Silicon (macOS), served by
  [oMLX](https://github.com/jundot/omlx).

You do not need to understand the comparison methodology to use it. This guide
assumes you want to try the stack, pick a model that fits your hardware, and
run one task end to end.

> **Verified on this host.** The unsloth and ollama paths below were each run
> end to end on a Linux machine — unsloth at `localhost:8888`, ollama at
> `localhost:11434` — creating a run record, preflighting, launching, and
> producing a real graded model cell (a patch, a transcript, and a receipt,
> graded offline). The oMLX path is macOS/Apple Silicon only and was not run
> here; its setup follows the oMLX project's own documentation and the same Pi
> model configuration. For any backend, the prerequisite check's
> `--check-servers` and `launch --preflight` are what tell you the server is
> actually serving the model.

## What the stack is

Three pieces, two of them local models:

```text
satyrn-evals   the eval harness: tasks, isolated cells, a launcher, offline grading
satyrn-engine  the engine: the /implement command and the attempt adapter the harness drives
the model      Pi (the coding agent) + one local model backend (unsloth, ollama, or oMLX)
```

The harness captures a task, invokes an attempt command, persists the patch and
the transcript, and grades the saved evidence offline — no model is needed for
grading. The model (Pi) is what does the work; the backend (unsloth / ollama /
oMLX) is what serves the model.

You need **two repositories**:

- `satyrn-evals` — this repository, the harness.
- `satyrn-engine` — the engine, fetched at a pinned commit.

## Prerequisites

- **`uv`** and **Python 3.14**, the interpreter this project pins
  ([`uv`](https://docs.astral.sh/uv/) is the Python package manager). `uv`
  installs the project into a local virtual environment, and can fetch the
  pinned Python if your machine's is older; nothing is installed globally
  except the Pi adapter.
- **`pi`** — the coding agent. Install it from
  [pi.dev](https://pi.dev/docs/latest/quickstart) (`curl -fsSL https://pi.dev/install.sh | sh`).
  The stack drives `pi` as a non-interactive, print-mode agent, so you do not
  need the interactive TUI.
- **`git`** — the engine works in a Git working tree.
- **One model backend** — install and start exactly one of unsloth, ollama, or
  oMLX (see the sections below).

Windows works for unsloth and ollama. oMLX is macOS-only (Apple Silicon).

Before installing anything, check what is already on your machine with
`uv run python scripts/prereqs.py`. It reports each prerequisite with a
one-line fix when one is missing, and exits non-zero if any is.

## Install the stack

From an empty directory:

```bash
# 1. The harness.
git clone https://github.com/pauleveritt/satyrn-evals.git
cd satyrn-evals
uv sync

# 2. The engine, at the commit the pinned arm expects.
uv run python -m tools.engine_sync fetch

# 3. Reach the engine from Pi as /implement.
pi install ./satyrn-engine/packages/engine
```

`uv sync` installs the harness into a local `.venv`. `fetch` clones
`satyrn-engine` at the commit its arm pins (default `baseline-ornith15-9b.json`).
`pi install` registers `/implement` once, globally — do **not** also load the
engine as a pi extension with `-e`, or `/implement` is registered twice and the
plain name stops dispatching.

## Point the engine at your model

The stack is built around **Ornith 1.5 9B**. Two environment variables name the
engine checkout and the model Pi uses for `/implement`:

```bash
export SATYRN_ENGINE_REPO="../satyrn-engine"
export SATYRN_MODEL="unsloth/ornith-ai/Ornith-1.5-9B-GGUF"
```

`SATYRN_MODEL` is a two-token address: a **provider** prefix and the model the
provider serves. The provider prefix selects the block in Pi's model
configuration (`~/.pi/agent/models.json`) that holds where the server lives and
its API key; the harness reads that same configuration to check the server is
up. An eval **arm** carries its own model string, so `launch` uses the arm's —
keep the arm and `SATYRN_MODEL` equal for the same backend. Start your backend
(the commands below), then set both strings to the Ornith model you started.

### unsloth (Linux or Windows, GPU)

unsloth runs a model on your GPU and exposes it as an OpenAI-compatible server.
`unsloth start pi` starts that server **and** writes the Pi model
configuration, so you do not hand-edit `models.json`.

```bash
# Install the unsloth CLI.
curl -fsSL https://unsloth.ai/install.sh | sh

# Start a persistent Pi server on a model. --persist keeps the session so you
# can resume it later. The API key is minted for your local server and
# remembered automatically.
unsloth start pi --persist --model ornith-ai/Ornith-1.5-9B-GGUF:Q8_0
```

Then point the engine at it:

```bash
export SATYRN_MODEL="unsloth/ornith-ai/Ornith-1.5-9B-GGUF"
```

The `unsloth/` prefix tells the harness to read the server address and key from
the `unsloth` provider block in `models.json`, which `unsloth start pi` wrote.
`unsloth start` names the model without that prefix; `SATYRN_MODEL` adds it.

**Ornith 1.5 9B by VRAM.** Pick the largest quantisation your GPU holds:

| VRAM | quantisation |
| --- | --- |
| 8 GB | `ornith-ai/Ornith-1.5-9B-GGUF:Q4_K_M` |
| 12 GB | `ornith-ai/Ornith-1.5-9B-GGUF:Q8_0` |
| 24 GB+ | `ornith-ai/Ornith-1.5-9B-GGUF:BF16` |

The `:Q8_0` suffix is a load-time choice; the served id is
`ornith-ai/Ornith-1.5-9B-GGUF` (check the server's `/v1/models`), so
`SATYRN_MODEL` is the same at every quantisation and the committed arm matches.
Other models (for example `unsloth/gemma-4-12b-it-GGUF:UD-Q6_K_XL`) run too, but
need their own arm and record.

### ollama (Linux or Windows, CPU or GPU)

ollama runs a model locally and exposes it as an OpenAI-compatible server at
`http://localhost:11434`, serving `ornith-1.5:9b` at 32768 context by default.

```bash
# Install ollama, then pull the model the stack uses.
curl -fsSL https://ollama.com/install.sh | sh
ollama pull ornith-1.5:9b
```

Add the ollama provider to `~/.pi/agent/models.json` (Pi ships this file). The
entry's fields must equal the settings the committed arm declares, because the
settings preflight compares them:

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

The `apiKey` is a dummy; Ollama ignores it. `contextWindow` is what ollama
actually serves (32768, even though the model card says 262144); to serve more,
start ollama with `OLLAMA_CONTEXT_LENGTH` set and raise this to match. Then
point the engine at it — the `ollama/` prefix selects the ollama provider block:

```bash
export SATYRN_MODEL="ollama/ornith-1.5:9b"
```

`ornith-1.5:35b` is the larger sibling. A different model needs an entry here
*and* a matching arm — see "Run a task" below.

### oMLX (macOS, Apple Silicon)

[oMLX](https://github.com/jundot/omlx) serves a model locally on Apple Silicon
and exposes an OpenAI-compatible endpoint at `http://localhost:8000/v1`. This
is the default backend, so the record's `--backend` stays `omlx`.

```bash
# Install oMLX from its Homebrew tap (or download the .dmg from its Releases).
brew install jundot/omlx/omlx

# Serve the directory your models live in; oMLX discovers them.
omlx serve --model-dir ~/models
```

Point the stack at the model oMLX lists (check `http://localhost:8000/v1/models`):

```bash
export SATYRN_MODEL="omlx/Ornith-1.5-9B-MLX-8bit"
```

oMLX writes no `models.json` for you, so add its provider block yourself — the
`baseUrl` must match your server, which listens on 8000 by default:

```json
{
  "providers": {
    "omlx": {
      "baseUrl": "http://localhost:8000/v1",
      "api": "openai-completions",
      "models": [{ "id": "Ornith-1.5-9B-MLX-8bit" }]
    }
  }
}
```

Add an `"apiKey"` to the block if your oMLX server requires one.

## Check your backend before you spend a run

Before launching cells, confirm the server is up and actually serving your
model. This is the one preflight step that catches a dead backend — a hung
server costs a wall-clock slot and a model load before you know it is broken.
Pass the arm that matches your backend (the table in "Run a task" lists them):

```bash
uv run satyrn-evals launch --preflight ./my-record.json --arm arms/baseline-unsloth-ornith15-9b.json
```

`--preflight` prints a report with `problems: []` when the server answers
`GET /v1/models` and lists your model, and a per-server `authenticated` flag
when the server needs a key. A non-empty `problems` list names the cause —
usually an unreachable server or a model id the server does not know. Fix the
backend, then re-run `--preflight`; a clean report is the green light for
`launch`.

## Run a task

A **run record** freezes the task, the arm (model + tool surface), the budgets,
and the stopping rules before a budgeted run. The arm and the record must agree
on the model and the backend. The committed Ornith arms are:

| arm file | backend | model |
| --- | --- | --- |
| `arms/baseline-unsloth-ornith15-9b.json` | `openai` (unsloth) | `unsloth/ornith-ai/Ornith-1.5-9B-GGUF` |
| `arms/baseline-ornith15-9b.json` | `omlx` | `omlx/Ornith-1.5-9B-MLX-8bit` |
| `arms/engine-ornith15-9b.json` | `omlx` | `omlx/Ornith-1.5-9B-MLX-8bit` |

ollama has no committed arm; copy the unsloth one and set three things to match
the ollama provider block above:

```bash
cp arms/baseline-unsloth-ornith15-9b.json arms/baseline-ollama-ornith15-9b.json
# "model":        "ollama/ornith-1.5:9b"
# "server_model": "ornith-1.5:9b"
# "inference":    context_window 32768   (ollama serves 32768, not 262144)
```

Create a record for the arm, commit it, then launch. The record is created with
the arm's **name** (`baseline`), while `launch --arm` takes the arm **file**:

```bash
uv run satyrn-evals record new \
  --output ./my-record.json \
  --task agentclinic-repair-depth-2 \
  --arm baseline \
  --rung R1 \
  --n 1 --k 1 \
  --purpose development \
  --backend openai \
  --model "unsloth/ornith-ai/Ornith-1.5-9B-GGUF"

git add ./my-record.json && git commit -m "freeze unsloth development record"

# Pre-flight the backend, then run the cells.
uv run satyrn-evals launch --preflight ./my-record.json --arm arms/baseline-unsloth-ornith15-9b.json
uv run satyrn-evals launch ./my-record.json --arm arms/baseline-unsloth-ornith15-9b.json
```

That example is the unsloth path. For oMLX use `arms/baseline-ornith15-9b.json`,
`--backend omlx`, and `--model "omlx/Ornith-1.5-9B-MLX-8bit"`; for ollama use
your copied arm, `--backend openai`, and `--model "ollama/ornith-1.5:9b"`.
`--backend` and `--model` must match the arm exactly, or `launch` refuses.

### What a launch does

For each cell the record names:

1. the harness materialises an isolated task workspace from the base commit;
2. a fresh Pi runs the task's prompt against your model, with Pi's skills,
   prompt templates, themes, context files, and ambient extensions disabled;
3. the patch and the full transcript are written to pinned directories outside
   every Git worktree, so nothing a model writes can hide the result;
4. the harness grades the saved evidence offline — no model is involved in
   grading.

The result is a per-cell verdict (`pass`, `fail`, or an infrastructure signal)
plus a receipt with the turns, tool calls, and token usage. Grading is
deterministic and reproducible: re-running `grade` on the saved patch reproduces
the verdict without another model run.

A full run needs an arm file (model + tool surface) and a frozen record. See
`--help` on each subcommand for the exact flags.

## Verify locally, then read the results

After a launch, the result JSON names the night directory and the per-arm
summary; the night directory holds each cell's patch, transcript, and receipt.
Open a transcript to watch the model work — it will show the model reading,
editing, and running bash against the task, served through your backend.

```bash
cat ./my-record.result.json
# and, in the night directory:
cat <night>/<cell-name>/transcript.txt
cat <night>/<cell-name>/receipt.json
```

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| A step complains about a missing tool | Run `uv run python scripts/prereqs.py` to see every prerequisite with its fix. |
| `--preflight` lists `problems` naming an unreachable server | The backend is not running, or `SATYRN_MODEL`'s provider block in `models.json` names a different address. Start the backend and run `uv run python scripts/prereqs.py --check-servers` (with `SATYRN_MODEL` exported). |
| `--preflight` says the server does not serve the model | The model id in `SATYRN_MODEL` (after the provider prefix) is not in the server's `/v1/models`. Pull or `unsloth start pi --model` the exact id. |
| `/implement` is missing or shows `/implement:1` | The engine was installed twice. Reinstall once: `pi uninstall <path>/packages/engine && pi install <path>/packages/engine`. |
| A cell times out or is slow | The model is too large or unquantised for the hardware. Switch to a smaller quantisation (see the tables above). |
| Grading disagrees with what you saw | Do not re-run the model. Re-grade the saved patch: `uv run satyrn-evals grade <task> <patch.diff>`. Grading is offline and deterministic. |

## Next step

When the stack runs on your machine, read [How it works](how-it-works.md)
for the whole story in diagrams, and [Using Evals](use-evals.md) for
authoring your own tasks.
