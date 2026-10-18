# Your first run

You are about to drive a small model on your own machine through a small
Python task, grade the result from saved evidence, and send back what you saw.
This page walks the whole journey in order, with **ollama** as the backend and
four commands: `init`, `doctor`, `run`, `report`. Nothing is skipped and
nothing is assumed.

This page runs the *bare* agent, Pi on its own. Running the same task through
Satyrn Engine, the comparison this project exists for, is a longer path; step 9
says where it starts.

It is a *journey*, not a reference. When you want to look one flag up, or you
are using a different backend, the reference is [Using Evals](use-evals.md)
for the four commands and [Getting started](user-guide.md) for the rest.

## The journey at a glance

```mermaid
flowchart LR
  A[1. The cast] --> B[2. What you need]
  B --> C[3. Get satyrn-evals]
  C --> D[4. Watch it grade]
  D --> E[5. Point Pi at ollama]
  E --> F[6. Ask the doctor]
  F --> G[7. Freeze, then run]
  G --> H[8. Read the result]
  H --> I[9. The Engine's turn]
  I --> J[10. Send us your run]
```

*Click a diagram to enlarge it; click again or press Esc to close.*

## 1. The cast: what an engine is, and what evals are for

Two words get used a lot here. It is worth ten minutes to know what they mean,
because the rest of the journey is just those two ideas running.

**An engine is the driver.** When you use a coding agent, something sits
between you and the model. It decides what context the model sees, which tools
it can reach, when a loop has gone on too long, and which mode you are in:
planning, implementing, reviewing. That layer is the engine. It is not the
model and not the terminal UI.

**Evals are the tests for the engine.** An engine makes claims, such as "it
keeps a small model on track". Evals turn a claim like that into a measurement
instead of a story. They drive the agent the way a test suite drives your code.

![The user, Pi, ollama and an eval alongside them](imgs/pi-ollama-user-evals.svg)

*Your prompt goes to Pi, Pi asks the Ollama server, the server runs the model,
and an eval drives the whole thing from the side. (Illustration from the
[satyrn-evals-collector](https://github.com/satyrn-ai/satyrn-evals-collector)
repository.)*

**Evals come first.** You cannot tell whether a remedy helped until you can
measure the failure it was meant to fix. So this journey runs the bare agent
first, on a task with a known answer, and reads the verdict from evidence.

*Going deeper:* [How it works](how-it-works.md) tells the whole story in
diagrams; the [glossary](glossary.md) defines task, arm, cell, record and
verdict; [About Satyrn Evals](evals-about.md) says why the harness exists.

## 2. What you need

**A machine that can run a small model.** The project's target is a laptop
with **16 GB of RAM or shared memory**. A GPU makes everything faster, but it
is not required: every command on this page was run on a CPU-only laptop.

**Four tools, and one local model.**

| thing | why | get it |
| --- | --- | --- |
| `git` | the harness freezes and isolates runs in Git | [git-scm.com/downloads](https://git-scm.com/downloads) |
| `uv` | installs the harness and fetches Python 3.14 for it | [docs.astral.sh/uv](https://docs.astral.sh/uv/#install) |
| `pi` | the coding agent the harness drives, headless | [pi.dev quickstart](https://pi.dev/docs/latest/quickstart) |
| `ollama` | serves the model on your machine | [ollama.com/download](https://ollama.com/download) |

Git needs to know who you are: if you have never committed on this machine,
set `git config --global user.name` and `user.email` first.

**One model.** This journey uses **Ornith 1.5 9B** (`ornith-1.5:9b` on ollama,
a Q4_K_M quantisation) as the worked example. Any model ollama serves will do;
step 4 shows where to name it.

**How long it takes.** Four runs of this page on one laptop, an Intel
i5-10210U with 16 GB of RAM and no GPU: two took under ten minutes with
nothing else running, one took 22 minutes while other work shared the CPU,
and one hit the 30-minute limit an attempt is allowed (step 7 says what that
looks like). A GPU machine is much faster. Treat these as what one modest
laptop did, not as a promise.

| step | time on that laptop |
| --- | --- |
| clone and `uv sync` | seconds to a few minutes, depending on what `uv` has cached |
| grading a patch offline (step 4) | under a second |
| one run of the example task with Ornith 1.5 9B (step 7) | 10 to 30 minutes |

> **You are here.** Nothing installed yet. Everything below is ordinary user
> software. Nothing needs Docker and nothing needs a sandbox.

## 3. Get satyrn-evals

satyrn-evals is not on PyPI yet, so you run it from a clone. The four commands
live on the `cli-ux` branch until it merges:

```bash
mkdir -p ~/satyrn && cd ~/satyrn
git clone https://github.com/pauleveritt/satyrn-evals.git
cd satyrn-evals
git switch cli-ux
uv sync
source .venv/bin/activate
satyrn-evals --help
```

`uv sync` creates a virtual environment inside the clone and installs the
harness into it. Activating it puts the `satyrn-evals` command on your path
for this terminal. Open a new terminal later, and you activate it again.

The help lists four commands at the top. They are the whole journey:

```text
init     scaffold satyrn.yaml, an example task, and a starter arm here
doctor   check this machine and the configured backend
run      write the configured record and launch its cells
report   show a readable result for a finished run
```

Below them sit the expert commands (`grade`, `qualify`, `attempt`, `repeat`,
`launch`, `record` and more). You will meet one of them in the next step.

> **You are here.** The harness is installed. No model has run, and nothing
> has been spent.

## 4. Make a project and watch it grade

Your evals live in their own folder, next to the clone rather than inside it.
`init` creates one:

```bash
cd ~/satyrn
satyrn-evals init my-first-eval --model ollama/ornith-1.5:9b --backend ollama
cd my-first-eval
```

```text
wrote my-first-eval/satyrn.yaml
wrote my-first-eval/eval-tasks/format_number
wrote my-first-eval/arms/baseline.json
next: edit satyrn.yaml, then run `satyrn-evals doctor`
```

You passed the model on the command line, so there is nothing to edit yet.
Three things are now on disk:

- **`satyrn.yaml`** says what to run: the task, the arm, the model, the
  budgets (one attempt, 32,000 tokens, 48 turns, 60 minutes), and the name of
  the run record, `records/my-first-eval-format_number.json`.
- **`eval-tasks/format_number`** is the example task: a `solution.py` with a
  stub `format_number(n)`, four tests, and two ready-made patches, one right
  and one wrong.
- **`arms/baseline.json`** says *how* to run: bare Pi with four tools (`read`,
  `bash`, `edit`, `write`) and your model.

Two notes on that `init` line. `--model` is a **two-part address**: the provider
name Pi knows (`ollama`), then the model id that provider serves
(`ornith-1.5:9b`). And `--backend` is the server you run. Open `satyrn.yaml`
and you will see it written as `backend: openai`: to the harness, ollama is one
of the servers that speak the OpenAI API, and that is the name the run record
keeps.

Before any model gets involved, see the part that makes everything else
trustworthy: grading. Hand the grader the right patch, then the wrong one:

```bash
satyrn-evals grade format_number eval-tasks/format_number/fixtures/known-good.patch \
  --tasks-root eval-tasks --receipt good.json
satyrn-evals grade format_number eval-tasks/format_number/fixtures/known-broken.patch \
  --tasks-root eval-tasks --receipt broken.json
```

`grade` prints nothing; it writes a receipt. Open both:

```bash
cat good.json broken.json
```

The first says `"verdict": "pass"` with 4 tests passed. The second says
`"verdict": "fail"`, 2 passed and 2 failed. No model, no network, under a
second each. The grader applied each patch to a clean copy of the task, ran the
tests, and read the result from evidence the test run wrote, never from an
exit code. Every verdict you will see later comes from this same machinery.

> **You are here.** You have a project, and you have seen the grader tell a
> right answer from a wrong one. Still no model, still nothing spent.

## 5. Point Pi at ollama

### Get the model

Install ollama from [ollama.com/download](https://ollama.com/download), then:

```bash
ollama pull ornith-1.5:9b
```

Ollama now serves the model at `http://localhost:11434`.

**Give it enough context.** A coding agent fills a small context window with
its system prompt and tool definitions before your task even starts, and
ollama's default depends on your machine: on a CPU-only laptop it was 4,096.
Set `OLLAMA_CONTEXT_LENGTH` to `32768` before you run anything. On Linux, the
official installer runs ollama as a system service, so an `export` in your
shell does not reach it; the
[Ollama how-tos on Satyrn Zen](https://satyrn-ai.github.io/satyrn-zen/create/)
show how to set it for each way of running ollama. `ollama ps` shows the
context a loaded model actually got, in its `CONTEXT` column.

### Tell Pi where the server is

Pi reads its models from `~/.pi/agent/models.json`. `init` does not write this
file, so add an `ollama` provider yourself:

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
          "maxTokens": 16000
        }
      ]
    }
  }
}
```

If the file already exists, add the `ollama` block inside `providers` instead
of replacing the file. The `apiKey` is a dummy; ollama ignores it. The `id` is
the part after `ollama/` in your `--model`, and `contextWindow` should be the
context you gave ollama above. Sampling settings (temperature and the like)
can go in this entry too; [Using Evals](use-evals.md#pis-modelsjson-entry)
lists the ones the project uses.

This entry is **required**: before the first attempt, `run` checks that Pi
lists your model, and stops if it does not. It does not check the numbers,
so write them once and write them right.

> **You are here.** A model is installed, and Pi knows how to reach it.
> Still nothing spent.

## 6. Ask the doctor

From inside `my-first-eval`:

```bash
satyrn-evals doctor --check-servers
```

```text
satyrn prerequisites:

  git            OK   /usr/bin/git
  python         OK   python 3.14.6
  uv             OK   /home/you/.local/bin/uv
  pi             OK   /home/you/.local/bin/pi
  model backend  OK   ollama
  model server   OK   ollama/ornith-1.5:9b

All 6 prerequisites are met.
```

`doctor` reads `satyrn.yaml` from the current folder or the nearest one above
it. The `model backend` line names the server programs it found on your path.
`--check-servers` adds the last line: it asks the running ollama server
whether it really serves the model you named. Anything missing comes with a
one-line fix, and `doctor` exits non-zero until it is fixed. A hung or
misconfigured backend is cheaper to find here than ten minutes into a run.

> **You are here.** The machine, the server and the model all answer. The next
> step spends real time.

## 7. Freeze, then run

A run is defined by a **run record**: which task, which arm, which model,
which budgets, when to stop. The harness insists that the record is
**committed to Git, unchanged**, before anything runs. That way a result can
never be shaped after the fact by a changed setting, and anyone can check
exactly what was run.

So the project needs to be a Git repository, and the record needs to exist
before you commit:

```bash
git init
satyrn-evals run --dry-run
git add .
git commit -m "freeze my first run"
```

`run --dry-run` writes the record and checks it, without spending anything:

```text
wrote .../my-first-eval/records/my-first-eval-format_number.json; commit it, unchanged, before launch
record accepted: task format_number, arm baseline, model ollama/ornith-1.5:9b, n=1, k=1
```

Now run it for real:

```bash
satyrn-evals run
```

**Expect no output until it is over.** `run` prints nothing while the model
works, then one block of JSON. On the laptop above that silence lasted ten to
thirty minutes. To see that something is happening, open a second terminal:

```bash
wc -l ~/satyrn-runs/my-first-eval-format_number/baseline/*/timeline.jsonl
```

The count grows by two lines for every tool call the agent makes. If it stays
still for several minutes, the model is writing a long reply, not stuck.

**An attempt gets 30 minutes.** After that the harness stops it, whatever the
budgets in `satyrn.yaml` say. On a CPU-only laptop that is a real limit: if
other programs are using the processor, close what you can before you run.

While it runs, here is what happens:

```mermaid
flowchart TB
  R[committed run record] --> L[launcher]
  L --> W[fresh copy of the task<br/>in its own Git worktree]
  W --> P[Pi with your model<br/>and the four baseline tools]
  P --> E[transcript + patch saved]
  E --> G[offline grade, as in step 4]
  G --> V[verdict: pass, fail or unavailable]
```

The harness makes a fresh copy of the task, runs Pi against your model with
Pi's own skills, templates and extensions switched off, keeps the agent inside
the task folder, saves the full transcript and the patch, and then grades the
saved patch offline. No model is involved in grading. One thing to know when
you read the transcript later: the copy the agent works in has only the
system Python, with no pytest, so the agent cannot run the task's tests
itself. The grader runs them afterwards, on the saved patch.

When it finishes, `run` prints where things went:

```text
{
  "status": "complete",
  "reason": null,
  "night": "/home/you/satyrn-runs/my-first-eval-format_number",
  "result": ".../my-first-eval/records/my-first-eval-format_number.result.json"
}
```

A **night** is the harness's word for one run's results folder. The `result`
file lands next to your record, untracked; commit it if you want the project
to carry its own result. `"status": "complete"` means the run finished, not
that the attempt passed: `report`, next, says how it went.

**If `run` stops before the first attempt**, the message says why. The ones
you are most likely to meet:

- *the record was just written*: you ran `run` without `--dry-run` on a fresh
  project. Commit the record as the message says, then run again.
- *the run record is not frozen*: the record changed since its commit, or was
  never committed. Commit it, then run again.
- *... belongs to another record*: a results folder with this project's name
  already exists from a run with different settings. Move it aside, for
  example `mv ~/satyrn-runs/my-first-eval-format_number ~/satyrn-runs/old-run`.
- *pi: no entry for this model in models.json*: go back to step 5.

> **You are here.** A real model worked on a real task, and a verdict came out
> the other end. This is the moment the whole stack has been aiming at.

## 8. Read the result

```bash
satyrn-evals report
```

```text
task:     format_number
rung:     contract
purpose:  development
status:   complete
cells:    1

arm baseline: 1/1 passed (OK=1)
```

One attempt, one pass. (`rung: contract` means the agent got the task's own
contract text; the record stores that as `null`.)

If the last line reads `arm baseline: 0/1 passed (COMMAND_TIMEOUT=1)`, the
attempt hit the 30-minute limit. Nothing was graded: there is no `patch.diff`
and no `receipt.json` to read, and the work the agent did is gone with its
copy of the task. Free up the processor, give the record a new name in
`satyrn.yaml` (for example `record: records/my-second-try.json`), and go back
to the `--dry-run` and commit in step 7.

If it reads `arm baseline: 0/1 passed (NO_PATCH=1)`, the agent finished but
changed nothing: `patch.diff` is empty and there is no `receipt.json`, because
an empty change cannot be graded. `transcript.txt` and `timeline.jsonl` show
what it did instead. A small model does this now and then; run again with a
new record name, as above.

When the attempt finished, the evidence behind that line is on disk, in the
night:

```bash
cd ~/satyrn-runs/my-first-eval-format_number/baseline
cat summary.json                     # verdict counts; per attempt, tool calls and pathology counters
cat format_number-*/timeline.jsonl   # one line per event: each tool call, in order
cat format_number-*/patch.diff       # the change it made, from the task's base
cat format_number-*/receipt.json     # the grade: verdict and test counts
```

`transcript.txt` in the same folder is the complete Pi session, one JSON event
per line; it is for tools and for the curious, not for reading top to bottom.

**There are three verdicts, not two.**

| verdict | means |
| --- | --- |
| `pass` | the patch makes the hidden tests pass |
| `fail` | the patch was graded, and tests fail |
| `unavailable` | the patch could not be graded at all |

`unavailable` is not a polite `fail`. It says the result cannot be judged, and
`receipt.json` says why. One run on the laptop above, with a 4B model on this
same task, went like this: the agent never opened `solution.py`. It wrote its
answer into a brand-new file instead, and the verdict was `unavailable` with
the reason `patch touches non-source path`. The task only allows changes to
`solution.py`. Its code was in fact correct: pasted into `solution.py` by hand,
it passed all four tests. The model could solve the problem; it did not work
on the repository the way the task asked. That gap, between knowing the answer
and delivering it properly, is exactly what an engine is for.

**Grade from evidence, never from the transcript's ending.** A transcript that
*looks* finished is not a pass. The verdict is what the tests said against the
saved patch.

**If you disagree with a verdict, re-grade, never re-run.** Grading is offline
and deterministic, the same command as in step 4:

```bash
cd ~/satyrn/my-first-eval
satyrn-evals grade format_number ~/satyrn-runs/my-first-eval-format_number/baseline/format_number-*/patch.diff \
  --tasks-root eval-tasks --receipt regrade.json
```

Same patch in, same verdict out, no model, no spend.

If something else went wrong, the reference page has the
[troubleshooting table](user-guide.md#troubleshooting).

> **You are here.** You can run the bare agent and read a graded result from
> retained evidence. That alone is the whole loop.

## 9. The Engine's turn

The next question is whether Satyrn Engine does better than bare Pi on the same
task: same model, same budgets, same tools, plus the Engine's `/implement`.

`init` scaffolds only the Baseline arm today. Running the Engine arm still
takes the longer path, with the Engine checked out at the commit its arm pins:
follow [Getting started](user-guide.md) from "Install the stack".

One honest caveat: **one attempt against one attempt proves nothing.** It is a
flavour of the difference, not a measurement. For how a real comparison is
run, read [First results](numbers.md), including where the Engine did *not*
help, and [the stated negative](release-one-negative.md).

## 10. Send us your run

This is the part the journey is really for. The harness can prove things about
*this* machine and *this* model. What it cannot know is how local models behave
in the wild: on other hardware, other quantisations, other problems. You are
the only source of that.

1. **Fork** [satyrn-ai/satyrn-evals-collector](https://github.com/satyrn-ai/satyrn-evals-collector)
   and create a branch.
2. **Make a folder** named `reports/YYYY-MM-DD_<author>_<topic>/`.
3. **Copy the template** at
   [`reports/0000-00-00_example_template/report.md`](https://github.com/satyrn-ai/satyrn-evals-collector/blob/main/reports/0000-00-00_example_template/report.md)
   into it and fill it in: model and quantisation, hardware, `pi --version`,
   then what you did and how it went.
4. **Add your evidence**: the `report` output, `summary.json`, the timeline.
5. **Redact before you commit.** Everything in that repository is public.
6. **Open a pull request** against `main`.

The team reads reports as the ground truth for what local-model work actually
looks like, and a reported problem can become a new eval task of its own. The
full briefing, with model suggestions and starter problems, is
[`docs/notes/000_engine_engage.md`](https://github.com/satyrn-ai/satyrn-evals-collector/blob/main/docs/notes/000_engine_engage.md).

> **You are here.** You ran the harness, read the evidence, and sent back what
> only you could see. That is the loop this whole project runs on.
