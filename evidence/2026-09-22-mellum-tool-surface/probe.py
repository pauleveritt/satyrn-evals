"""Capture the Mellum tool-surface probe: exact bodies and raw responses.

Run against a live oMLX server on 127.0.0.1:8001 serving the converted model.
Each case is repeated RUNS times (the model is stochastic); every request body
and verbatim response is written under ./raw/<case>/run<N>.json, and a per-case
valid-tool-call tally is printed and written to ./raw/summary.json.
"""

import json
import subprocess
import sys
from pathlib import Path

MODEL = "swe-pi-m23-mix4s100-think-ae10k-init800-20260917-bulat-step-500-MLX-8bit"
URL = "http://127.0.0.1:8001/v1/chat/completions"
OUT = Path(__file__).parent / "raw"
RUNS = 5

TASK_TEXT = Path("/private/tmp/task-text.txt").read_text()

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
}


def main() -> int:
    OUT.mkdir(exist_ok=True)
    summary = []
    for name, case in CASES.items():
        d = OUT / name
        d.mkdir(exist_ok=True)
        valid = 0
        finishes: dict[str, int] = {}
        for run in range(1, RUNS + 1):
            body = {"model": MODEL, **case}
            (d / f"run{run}.request.json").write_text(json.dumps(body, indent=2))
            r = subprocess.run(
                ["curl", "-s", "-m", "180", URL, "-H", "Content-Type: application/json",
                 "-H", "Authorization: Bearer not-needed", "-d", json.dumps(body)],
                capture_output=True, text=True,
            )
            (d / f"run{run}.response.json").write_text(r.stdout)
            try:
                resp = json.loads(r.stdout)
                choice = resp["choices"][0]
                msg = choice["message"]
                ok = bool(msg.get("tool_calls"))
                finish = choice.get("finish_reason")
                valid += ok
                finishes[finish] = finishes.get(finish, 0) + 1
            except Exception as exc:  # noqa: BLE001
                finishes["PARSE_ERROR"] = finishes.get("PARSE_ERROR", 0) + 1
                print(f"{name} run{run}: PARSE_ERROR {exc} {r.stdout[:120]}")
        row = {"case": name, "runs": RUNS, "valid_tool_calls": valid, "finish_reasons": finishes}
        summary.append(row)
        print(json.dumps(row))
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
