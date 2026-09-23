# Mellum tool-surface probe — research note

**Date:** 2026-09-22 (cells ran 2026-09-23 01:19–01:41 UTC).
**Author:** maintainer's agent, attended sitting.
**Purpose:** record the probe behind the claim that this week's Mellum
checkpoint degenerates on the harness's four-tool surface. The earlier
chat write-up asserted a root cause with no artifact behind it; this note
and its `raw/` responses are that artifact. Where the probe does not
settle a question, this note says so.

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
holding the tally. "Valid tool call" means the response's `message.tool_calls`
is non-empty. No transcript, no cell, no harness: this is the server path
alone.

## Results (n = 5 per case)

| case | tools | sampling | valid tool calls | finish reasons |
|---|---|---|---|---|
| `01_weather_one_tool` | 1 (get_weather) | server | **5/5** | tool_calls 5 |
| `02_task_text_one_tool` | 1 (bash) | server | 1/5 | length 4, tool_calls 1 |
| `03_two_tools` | 2 | server | 1/5 | length 4, tool_calls 1 |
| `04_three_tools` | 3 | server | **0/5** | length 5 |
| `05_four_tools` | 4 | server | **0/5** | length 5 |
| `06_four_tools_temp1_topk0` | 4 | temp 1.0, top_p 1.0, top_k 0 | 0/5 | length 5 |
| `07_four_tools_reppen1_1` | 4 | temp 0.6, rep_pen 1.1 | 0/5 | length 5 |
| `08_no_tools_coding_short` | 0 | server | (n/a) | stop 5 |
| `09_no_tools_coding_long` | 0 | server | (n/a) | stop 4, length 1 |

The degenerate responses are 2,000-token length stops: raw `tool_call`-shaped
JSON fragments and repeated `</think>` / punctuation inside a text block, never
a parsed call (see any `raw/04_*` or `raw/05_*` response). The no-tools coding
controls return correct code and stop normally.

## Reading

**Leading hypothesis, not a root cause:** this checkpoint's tool-calling
degrades sharply as the number of tool signatures grows — reliable only on a
trivial one-tool prompt, already unreliable (1/5) on the real task with one
or two tools, and absent (0/5) with three or four — independent of the two
sampling variants tried. Pi's four-tool surface sits in the 0/5 region.

**The discriminator is not yet run.** The template path and the checkpoint
path are not separated here. The cheap test is to re-render the same
multi-tool prompt through a different path — a newer `mlx_lm`, or the
model's intended `json_tools` format rather than the snapshot template as
oMLX renders it — and re-probe. Until that runs, "checkpoint" versus
"template rendering" is undecided.

**What is *not* shown:** that the Q8 conversion left tool-calling intact.
The no-tools controls show the quant is not globally broken (it writes
coherent code), but only a bf16 or unquantized control **at 2+ tools** would
separate quantisation damage from a checkpoint/template limitation. That
control was not run.

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

**Revert before an Ornith run?** Not required: the Ornith entries in both Pi
configs and in `model_settings.json` are unchanged, and isolated cells read
the cell's `models.json`, whose Ornith entry is untouched. One side effect:
oMLX now names the Mellum id as its default model, so `omlx launch` without
`--model` selects it; the harness always passes `--model` explicitly.

## Recompute

```bash
# server must be up with the model registered; task-text.txt is the cell prompt
cd evidence/2026-09-22-mellum-tool-surface
python3 probe.py        # rewrites raw/ and prints the per-case tally
```
