# Mellum tool-surface probe — research note

**Date:** 2026-09-22 (cells ran 2026-09-23 01:19–01:41 UTC).
**Author:** maintainer's agent, attended sitting.
**Purpose:** record the probe behind the claim that this week's Mellum
checkpoint degenerates on the harness's four-tool surface. The earlier
chat write-up asserted a root cause with no artifact behind it; this note
and its `raw/` responses are that artifact. Where the probe does not
settle a question, this note says so.

> **2026-09-23 update: the cause is found.** The snapshot's `config.json`
> declares `qwen3_moe`, so oMLX served it without Mellum's sliding-window
> attention or YaRN. Reconverted as `mellum`, the degeneration is gone and
> the four-tool thinking-on case is 5/5 at the harness budget. See
> "Rerun on the mellum model class" below. The "Reading" section is kept
> as written; it is superseded, not deleted.

## The model

- **Served id:** `swe-pi-m23-mix4s100-think-ae10k-init800-20260917-bulat-step-500-MLX-8bit`
- **Source checkpoint:** `JetBrains/swe-pi-m23-mix4s100-think-ae10k-init800-20260917-bulat-step-500`
  (HF cache snapshot `a8f4194c56735020996acadfa8c0b98f2737a67f`), raw HF bf16,
  `Qwen3MoeForCausalLM`, 12.15B params, 24.3 GB.
- **Converted:** `~/.cache/huggingface/hub/mlx-community/JetBrains/swe-pi-m23-mix4s100-think-ae10k-init800-20260917-bulat-step-500-MLX-8bit`,
  MLX 8-bit affine, group size 64, 8.5 bits/weight, 12 GB. Converted with
  oMLX's bundled `mlx_lm.convert`; `config.json` sha256
  `63f390dce1f01df3ab6494a79104907b7fd1f3d0e30b704c7b1a0823f1b74601`.
  The conversion aliased transformers-5.x field names
  (`num_local_experts`→`num_experts`, nested `rope_parameters.rope_theta`→top-level)
  so the older runtime could load it; the source snapshot was not modified.
- **Runtime:** oMLX 0.6.4, bundled `mlx_lm` 0.31.3, `mlx` 0.32.0, Python 3.11.10.
- **Server settings applied to this id** (`~/.omlx/model_settings.json`):
  temperature 0.6, top_p 0.95, top_k 20, min_p 0.0, `enable_thinking` true,
  `preserve_thinking` true, `reasoning_parser` `qwen_3`.

## The question

The harness (Pi, via `satyrn-evals-attempt-pi`) always exposes four tools:
`read`, `bash`, `edit`, `write`. Does this checkpoint emit valid tool calls
on that surface?

## Method

`probe.py` sends OpenAI-style chat-completions to the live server at
`http://127.0.0.1:8001/v1/chat/completions` with the checkpoint's own
chat template (oMLX renders it), the task text the cells received
(`task-text.txt`), and 1–4 tool signatures. Each case is run **5 times**
(the model is stochastic); every request body and verbatim response is
under `raw/<case>/run<N>.{request,response}.json`, with `raw/summary.json`
holding the tally. No transcript, no cell, no harness: this is the server
path alone.

**Valid tool call** means `message.tool_calls` is non-empty **and**
`finish_reason` is `tool_calls` **and** `completion_tokens` is below the
request's `max_tokens`. A run with `tool_calls` that fails either other test
is counted **salvaged**: the server's parser pulled a call out of a response
that ran to the cap. The first version of this note counted any non-empty
`tool_calls`, which scored `02` run5 — 2,000 tokens, 3,808 characters of
garbage content, and a call `bash` with `{"command": "bash"}` — as a success.
Cases 01–09 were re-tallied from the unchanged response files
(`probe.py --tally-only`); cases 10–11 were run 2026-09-23 11:06 UTC.

## Results (n = 5 per case)

| case | prompt | tools | sampling | valid | salvaged | finish reasons |
|---|---|---|---|---|---|---|
| `01_weather_one_tool` | weather | 1 (get_weather) | server | **5/5** | 0 | tool_calls 5 |
| `02_task_text_one_tool` | task | 1 (bash) | server | **0/5** | 1 | length 4, tool_calls 1 |
| `03_two_tools` | task | 2 | server | 1/5 | 0 | length 4, tool_calls 1 |
| `04_three_tools` | task | 3 | server | **0/5** | 0 | length 5 |
| `05_four_tools` | task | 4 | server | **0/5** | 0 | length 5 |
| `06_four_tools_temp1_topk0` | task | 4 | temp 1.0, top_p 1.0, top_k 0 | 0/5 | 0 | length 5 |
| `07_four_tools_reppen1_1` | task | 4 | temp 0.6, rep_pen 1.1 | 0/5 | 0 | length 5 |
| `08_no_tools_coding_short` | code | 0 | server | (n/a) | – | stop 5 |
| `09_no_tools_coding_long` | code | 0 | server | (n/a) | – | stop 4, length 1 |
| `10_weather_four_tools` | weather | 4 (get_weather, read, bash, edit) | server | **5/5** | 0 | tool_calls 5 |
| `11_four_tools_no_thinking` | task | 4 | server, `enable_thinking` false | **5/5** | 0 | tool_calls 5 |

`09`'s one length stop (run1) is coherent reasoning about the answer cut off
at the 800-token cap, not degeneration.

The degenerate responses are 2,000-token length stops: ~2,300 characters of
split-off reasoning, then a content block of `tool_call`-shaped JSON
fragments with the `</think>` token repeated inside it (24–142 times per
`05` response), never a parsed call. The one valid task-text call with
thinking on (`03` run3) is 623 tokens, empty content, `mkdir -p tools
tests`. Every `11` call is 23 tokens with empty content (`read
tools/review.py` ×2, `mkdir -p tools tests` ×3). The no-tools coding
controls return correct code and stop normally.

`11` sends `chat_template_kwargs: {"enable_thinking": false}`: oMLX takes the
toggle from there, a request value overrides the model setting (`true`),
and the snapshot's `chat_template.jinja` branches on it.

## Reading

**Supported at n = 5:** the trivial weather prompt works 5/5 with one tool
and with four (`01`, `10`); the real task text with thinking on collapses at
every tool count tried — 0/5, 1/5, 0/5, 0/5 for one to four tools — and
those four counts are **not separable** from each other at n = 5. The same
task text with the same four tools and thinking off is 5/5 (`11`).

**Not supported:** that the collapse grows with the tool surface. The first
version of this note said so, on a 1/5-vs-0/5 difference that included a
salvaged call. Case `01` also differs from `02` in *both* the prompt and the
tool, so `01`–`05` alone could not say whether tool count, prompt length, or
their combination drove it. `10` removes tool count as a sufficient cause on
the trivial prompt; `11` points at the thinking path on the task text.

**Leading hypothesis, not a root cause:** with thinking on, this checkpoint
does not close its reasoning cleanly on the task text and degenerates into
`</think>`-laced tool-call fragments; with thinking off it calls a tool
immediately. Two single controls at n = 5 each, one server, one conversion —
enough to redirect the next probe, not to settle the cause.

**Next, in order.** (1) Thinking off at one tool (`02` with
`enable_thinking` false) and thinking on with a larger `max_tokens`, to
separate "thinking breaks tool emission" from "thinking runs out of budget".
(2) Then the rendering-path discriminator: re-render the multi-tool prompt
through a different path — a newer `mlx_lm`, or the model's intended
`json_tools` format rather than the snapshot template as oMLX renders it —
and re-probe. Until that runs, "checkpoint" versus "template rendering" is
undecided.

**What is *not* shown:** that the Q8 conversion left tool-calling intact.
The no-tools controls and `11` show the quant is not globally broken, but
only a bf16 control with thinking on would separate quantisation damage from
a checkpoint/template limitation. That control was not run.

## Rerun on the mellum model class (2026-09-23)

**The mislabel.** The snapshot's `config.json` says `qwen3_moe` /
`Qwen3MoeForCausalLM`. The released `JetBrains/Mellum2-12B-A2.5B-Thinking`
config says `mellum` / `MellumForCausalLM` and has the same shapes. Under
`qwen3_moe`, oMLX's `mlx_lm` 0.31.3 ran full attention on all 28 layers,
where 21 are trained with a 1,024-token sliding window, and dropped YaRN.
Every clean call in `raw/` finished under about 1,024 total tokens except
one at 1,252. Every thinking-on task-text run had to cross it.

**The fix.** The Mellum team said sliding layers take no YaRN and that the
official config can be copied. The new source directory is the snapshot's
files with only `config.json` replaced by the official one (model type
`mellum`, `num_experts`, `rope_parameters` keyed by layer type: YaRN on
`full_attention`, plain RoPE on `sliding_attention`). The snapshot's chat
template and tokenizer were kept, so the config is the only variable. It was
converted with the same bundled `mlx_lm`, 8-bit, group size 64, to
`...-step-500-mellum-MLX-8bit` (12 GB, the same 791 tensors). `mlx_lm` picks
its model module from the model type, so this is served by `mellum.py`.

**Results** (`raw-mellum/`, n = 5 per case, same cases and criterion):

| case | qwen3_moe (`raw/`) | mellum (`raw-mellum/`) |
|---|---|---|
| `01` weather, 1 tool | 5/5 | 5/5 |
| `02`–`05` task text, 1–4 tools, 2,000 cap | 0, 1, 0, 0 | 0, 0, 1, 0 |
| `06`, `07` four tools, sampling variants | 0, 0 | 1, 1 |
| `10` weather, 4 tools | 5/5 | 5/5 |
| `11` four tools, thinking off | 5/5 | 5/5 |
| `12` four tools, thinking on, 16,000 cap | not run | **5/5** |

The 2,000-cap counts look alike, but the failures are different in kind.
Across the length-stopped runs of cases `02`–`07`, the qwen3_moe responses
carry 6–166 stray `</think>` tags and up to 347 `{"name` fragments each,
with as few as 11% distinct lines. The mellum responses carry none of
either, with 80–100% distinct lines: coherent reasoning cut off by the cap.
Case `12` gives the model the harness's own budget. All five runs return a
clean call (`mkdir`, or a `write` of `tools/review.py`) after 529–7,138
completion tokens, far past the 1,024-token window.

**Reading.** The collapse was a serving misconfiguration, not a checkpoint
limitation or a thinking-mode defect. Quantisation is not implicated: the
same 8-bit conversion recipe works once the model class is right. Still
unmeasured: whether the mellum conversion completes the task in a cell,
which needs the two n = 2 cells rerun on the new model id. The bf16 control
is no longer needed for this question.

**Cells on the mellum class (2026-09-23).** The two n = 2 cells were rerun
with only the model id changed (`arms/baseline-mellum-class-swe-pi.json`,
`records/2026-09-23-spike-mellum-class-review-script-mellum.json`). Both
passed the hidden grader:

| cell | verdict | turns | output tokens | tool calls | repeats | churn |
|---|---|---|---|---|---|---|
| `121635` | pass | 8 | 9,701 | 7 | 0 | 0 |
| `121830` | pass | 25 | 14,687 | 24 | 8 | 4 |

Both ended by announcing an action in their reasoning and stopping without
it: one left `ruff` failing, and neither committed. The second cell spent 11
turns editing the wrong file's imports. These are pathologies 21 and 22 in
`docs/pathologies.md`. Ornith 1.5 9B on this task, for scale only: the
2026-09-22 spike pair (same record settings) scored 0/2; the 2026-09-21
comparison (48k tokens, 72 turns) scored Baseline 2/6 and Engine 5/6. At
n = 2 these counts do not rank the models.

## The cells

Two `purpose=development` records, bare Pi, `selfhost-review-script` R1-plan,
n = 2, k = 1, 32k/48, isolated (records and results committed at
`d5a8e68`, `f2732c1`; cells under `~/satyrn-runs/2026-09-22-spike-mellum-review-script-*`):

| arm | passes | cells |
|---|---|---|
| Ornith 1.5 9B | 0/2 | one `OK`/fail with 16 tool calls; one `BUDGET_EXCEEDED` at turn 49 with 48 tool calls |
| Mellum checkpoint | 0/2 | both `NO_PATCH`: 1 turn, 0 tool calls, 16,000 output tokens, length stop, empty patch |

The Ornith 0/2 is n = 2 triage and is consistent with the earlier
comparison's 2/6 on this task; it is not a re-measurement and carries little
weight on its own.

## Instrument gap found

`baseline/summary.json` reports `invalid_tool_calls: 0` and `tool_calls: {}`
for both Mellum cells — cells that emitted ~16,000 tokens of malformed
tool-call JSON inside a text block. The pathology counter counts **parsed**
tool calls and tool-execution events, so a model that writes malformed
`tool_call` text is invisible: `tool_free_terminal_turns` is 1 and the cell
reads as a plain refusal. A future model failing this way would look like
`NO_PATCH` and nothing more. Logged as an open item in `STATE.md`.

## Caveats

- n = 5 per probe point, n = 2 per cell; the model is stochastic. These are
  counts, not rates.
- One machine, one server, one conversion.
- The checkpoint declares YaRN RoPE (factor 16) that oMLX's `mlx_lm` 0.31.3
  `qwen3_moe` ignores, and its context is 131072 against Ornith's 262144.
  Neither was exercised: the failure is at turn 1.

## Local state changed

| file | backup |
|---|---|
| `~/.omlx/model_settings.json` (added the model's entry) | `~/.omlx/model_settings.json.bak-pre-mellum-20260922-201215` |
| `~/.pi/agent/models.json` (added the entry) | `~/.pi/agent/models.json.bak-pre-mellum-20260922` |
| `/Users/satyrn-cell/.pi/agent/models.json` (added the entry) | `/Users/satyrn-cell/.pi/agent/models.json.bak-pre-mellum-20260922` |
| `~/.omlx/model_settings.json` (2026-09-23: added the `-mellum-MLX-8bit` entry, same settings) | `~/.omlx/model_settings.json.bak-pre-mellum-class-20260923` |

**Revert before an Ornith run?** Not required: the Ornith entries in both Pi
configs and in `model_settings.json` are unchanged, and isolated cells read
the cell's `models.json`, whose Ornith entry is untouched. One side effect:
oMLX now names the Mellum id as its default model, so `omlx launch` without
`--model` selects it; the harness always passes `--model` explicitly.

## Recompute

```bash
# task-text.txt (beside probe.py) is the cell prompt
cd evidence/2026-09-22-mellum-tool-surface
uv run python probe.py --tally-only   # no server: re-tally raw/ into summary.json
uv run python probe.py                # server up, model registered: rewrites raw/
uv run python probe.py --cases 10_weather_four_tools 11_four_tools_no_thinking
# the mellum-class rerun, into raw-mellum/
uv run python probe.py --out raw-mellum \
  --model swe-pi-m23-mix4s100-think-ae10k-init800-20260917-bulat-step-500-mellum-MLX-8bit
uv run python probe.py --tally-only --out raw-mellum
```
