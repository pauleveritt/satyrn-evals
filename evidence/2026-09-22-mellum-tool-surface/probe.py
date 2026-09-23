"""Capture the Mellum tool-surface probe: exact bodies and raw responses.

Run against a live oMLX server on 127.0.0.1:8001 serving the converted model.
Each case is repeated RUNS times (the model is stochastic); every request body
and verbatim response is written under ./raw/<case>/run<N>.request.json and
./raw/<case>/run<N>.response.json, and a per-case tally is printed and written
to ./raw/summary.json.

A run is a *valid* tool call only if ``message.tool_calls`` is non-empty AND
``finish_reason == "tool_calls"`` AND ``completion_tokens`` is below the
request's ``max_tokens``. A run with ``tool_calls`` that fails either other
condition is counted as ``salvaged_tool_calls``: the server's parser pulled a
call out of a response that ran to the token cap.

    uv run python probe.py                      # run every case, re-tally
    uv run python probe.py --cases 10_x 11_y    # run only the named cases
    uv run python probe.py --tally-only         # no server: re-tally raw/
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

MODEL = "swe-pi-m23-mix4s100-think-ae10k-init800-20260917-bulat-step-500-MLX-8bit"
URL = "http://127.0.0.1:8001/v1/chat/completions"
OUT = Path(__file__).parent / "raw"
RUNS = 5

TASK_TEXT = (Path(__file__).parent / "task-text.txt").read_text()

WEATHER = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get weather",
        "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
    },
}
BASH = {"type": "function", "function": {"name": "bash", "description": "Run a shell command",
        "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}}}
READ = {"type": "function", "function": {"name": "read", "description": "Read a file",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}}
EDIT = {"type": "function", "function": {"name": "edit", "description": "Edit a file",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "old": {"type": "string"}, "new": {"type": "string"}}, "required": ["path", "old", "new"]}}}
WRITE = {"type": "function", "function": {"name": "write", "description": "Write a file",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}}

CASES = {
    "01_weather_one_tool": {"messages": [{"role": "user", "content": "What is the weather in Paris? Use the get_weather tool."}], "tools": [WEATHER], "tool_choice": "auto", "max_tokens": 200},
    "02_task_text_one_tool": {"messages": [{"role": "user", "content": TASK_TEXT}], "tools": [BASH], "max_tokens": 2000},
    "03_two_tools": {"messages": [{"role": "user", "content": TASK_TEXT}], "tools": [READ, BASH], "max_tokens": 2000},
    "04_three_tools": {"messages": [{"role": "user", "content": TASK_TEXT}], "tools": [READ, BASH, EDIT], "max_tokens": 2000},
    "05_four_tools": {"messages": [{"role": "user", "content": TASK_TEXT}], "tools": [READ, BASH, EDIT, WRITE], "max_tokens": 2000},
    "06_four_tools_temp1_topk0": {"messages": [{"role": "user", "content": TASK_TEXT}], "tools": [READ, BASH, EDIT, WRITE], "max_tokens": 2000, "temperature": 1.0, "top_p": 1.0, "top_k": 0},
    "07_four_tools_reppen1_1": {"messages": [{"role": "user", "content": TASK_TEXT}], "tools": [READ, BASH, EDIT, WRITE], "max_tokens": 2000, "temperature": 0.6, "top_p": 0.95, "top_k": 20, "repetition_penalty": 1.1},
    "08_no_tools_coding_short": {"messages": [{"role": "user", "content": "Write a Python function provider_and_model(spec) that splits on the first slash and raises ValueError if there is no slash. Reply with only the code."}], "max_tokens": 800},
    "09_no_tools_coding_long": {"messages": [{"role": "user", "content": "Implement a pure Python function build_prompt(diff, range_label) that returns text containing range_label, the diff verbatim, and the words Accept and itemized. Reply with only the code."}], "max_tokens": 800},
    # Control: tool count without the task text (case 01's prompt, case 05's tools).
    "10_weather_four_tools": {"messages": [{"role": "user", "content": "What is the weather in Paris? Use the get_weather tool."}], "tools": [WEATHER, READ, BASH, EDIT], "tool_choice": "auto", "max_tokens": 200},
    # Control: case 05 with thinking off. oMLX reads enable_thinking from
    # chat_template_kwargs; a request value overrides the model setting (true).
    "11_four_tools_no_thinking": {"messages": [{"role": "user", "content": TASK_TEXT}], "tools": [READ, BASH, EDIT, WRITE], "max_tokens": 2000, "chat_template_kwargs": {"enable_thinking": False}},
    "12_four_tools_16k": {"messages": [{"role": "user", "content": TASK_TEXT}], "tools": [READ, BASH, EDIT, WRITE], "max_tokens": 16000},
}


def classify(resp: dict, max_tokens: int) -> tuple[str, str]:
    """Return (finish_reason, kind) with kind in {valid, salvaged, none}."""
    choice = resp["choices"][0]
    finish = choice.get("finish_reason")
    has_calls = bool(choice["message"].get("tool_calls"))
    completion = resp.get("usage", {}).get("completion_tokens")
    if not has_calls:
        return finish, "none"
    if finish == "tool_calls" and completion is not None and completion < max_tokens:
        return finish, "valid"
    return finish, "salvaged"


def tally_case(name: str) -> dict | None:
    """Recompute one case's row from its committed request/response files."""
    d = OUT / name
    responses = sorted(d.glob("run*.response.json")) if d.is_dir() else []
    if not responses:
        return None
    valid = salvaged = 0
    finishes: dict[str, int] = {}
    for resp_path in responses:
        req_path = resp_path.with_name(resp_path.name.replace(".response.", ".request."))
        max_tokens = json.loads(req_path.read_text())["max_tokens"]
        try:
            finish, kind = classify(json.loads(resp_path.read_text()), max_tokens)
        except Exception as exc:  # noqa: BLE001
            finishes["PARSE_ERROR"] = finishes.get("PARSE_ERROR", 0) + 1
            print(f"{name} {resp_path.name}: PARSE_ERROR {exc}")
            continue
        valid += kind == "valid"
        salvaged += kind == "salvaged"
        finishes[finish] = finishes.get(finish, 0) + 1
    return {"case": name, "runs": len(responses), "valid_tool_calls": valid,
            "salvaged_tool_calls": salvaged, "finish_reasons": dict(sorted(finishes.items()))}


def write_summary() -> None:
    summary = [row for name in CASES if (row := tally_case(name)) is not None]
    for row in summary:
        print(json.dumps(row))
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")


def run_case(name: str) -> None:
    d = OUT / name
    d.mkdir(parents=True, exist_ok=True)
    for run in range(1, RUNS + 1):
        body = {"model": MODEL, **CASES[name]}
        (d / f"run{run}.request.json").write_text(json.dumps(body, indent=2))
        r = subprocess.run(
            ["curl", "-s", "-m", "900", URL, "-H", "Content-Type: application/json",
             "-H", "Authorization: Bearer not-needed", "-d", json.dumps(body)],
            capture_output=True, text=True,
        )
        (d / f"run{run}.response.json").write_text(r.stdout)


def main() -> int:
    global MODEL, OUT
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tally-only", action="store_true", help="re-tally raw/ without a server")
    ap.add_argument("--cases", nargs="+", choices=list(CASES), help="run only these cases")
    ap.add_argument("--model", default=MODEL, help="served model id (default: the qwen3_moe conversion)")
    ap.add_argument("--out", type=Path, default=OUT, help="results directory (default: raw/)")
    args = ap.parse_args()
    MODEL, OUT = args.model, args.out
    if not args.tally_only:
        OUT.mkdir(exist_ok=True)
        for name in args.cases or list(CASES):
            run_case(name)
    write_summary()
    return 0


if __name__ == "__main__":
    sys.exit(main())
