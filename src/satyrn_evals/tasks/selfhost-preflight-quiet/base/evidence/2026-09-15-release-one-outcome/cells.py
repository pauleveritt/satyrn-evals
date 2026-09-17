#!/usr/bin/env python3
"""Per-cell spend analysis over retained Pi transcripts (read-only).

Walks ~/satyrn-runs/*/{baseline,engine}/<cell>/transcript.txt and emits
per-cell rows (JSON + a markdown table) with: turns, output tokens,
estimated split of output tokens into thinking / visible text / tool
arguments (proportional to characters within each assistant message, since
usage.output is per message), tool calls by name, exploration turns before
the first mutation, edit churn (files edited more than once), test runs,
turn of the first failing-test signal, context (input tokens) growth, tool
result bytes, per-turn seconds, and a short tail of the last assistant text.
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

RUNS = Path.home() / "satyrn-runs"
OUT = Path(__file__).resolve().parent

TEST_RE = re.compile(r"\b(pytest|self_test|python -m pytest|unittest)\b")
PYTEST_FAIL_RE = re.compile(r"(\b\d+ failed\b|FAILED |Error|Traceback|AssertionError)")
PYTEST_PASS_RE = re.compile(r"\b\d+ passed\b")


def load_events(path: Path):
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def analyse(cell_dir: Path, arm: str, run: str):
    tpath = cell_dir / "transcript.txt"
    if not tpath.exists():
        return None
    attempt = {}
    ap = cell_dir / "attempt.json"
    if ap.exists():
        attempt = json.loads(ap.read_text())
    turns = 0
    out_tokens = 0
    think_chars = text_chars = args_chars = 0
    tool_calls = Counter()
    edits_by_file = Counter()
    writes_by_file = Counter()
    first_mut_turn = None
    first_test_turn = None
    first_fail_signal_turn = None
    first_pass_signal_turn = None
    last_test_turn = None
    last_mut_turn = None
    test_runs = 0
    self_test_calls = 0
    inputs = []
    result_bytes = 0
    result_bytes_by_tool = Counter()
    tool_errors = 0
    turn_ts = []
    last_text = ""
    per_turn = []
    call_names = {}
    cur_turn_tools = []
    pending_calls = {}
    first_turn_prompt_len = 0
    prompt_text = ""
    thinking_tokens_reported = 0

    for e in load_events(tpath):
        t = e.get("type")
        if t == "turn_start":
            turns += 1
            cur_turn_tools = []
        elif t == "message_end":
            m = e["message"]
            role = m.get("role")
            if role == "user" and not prompt_text:
                for c in m.get("content", []):
                    if c.get("type") == "text":
                        prompt_text += c.get("text", "")
                first_turn_prompt_len = len(prompt_text)
            if role == "assistant":
                u = m.get("usage", {})
                out = u.get("output", 0) or 0
                out_tokens += out
                thinking_tokens_reported += u.get("reasoning", 0) or 0
                inputs.append(u.get("input", 0) or 0)
                turn_ts.append(m.get("timestamp"))
                th = tx = ar = 0
                for c in m.get("content", []):
                    ct = c.get("type")
                    if ct == "thinking":
                        th += len(c.get("thinking", ""))
                    elif ct == "text":
                        tx += len(c.get("text", ""))
                        if c.get("text", "").strip():
                            last_text = c.get("text", "")
                    elif ct == "toolCall":
                        name = c.get("name")
                        args = c.get("arguments", {})
                        s = json.dumps(args)
                        ar += len(s)
                        tool_calls[name] += 1
                        call_names[c.get("id")] = (name, args)
                        cur_turn_tools.append(name)
                        path = args.get("path") or args.get("file_path") or ""
                        if name in ("edit", "satyrn_edit"):
                            edits_by_file[path] += 1
                            if first_mut_turn is None:
                                first_mut_turn = turns
                            last_mut_turn = turns
                        elif name in ("write", "satyrn_write"):
                            writes_by_file[path] += 1
                            if first_mut_turn is None:
                                first_mut_turn = turns
                            last_mut_turn = turns
                        elif name == "bash":
                            cmd = args.get("command", "")
                            if TEST_RE.search(cmd) and "grep" not in cmd.split("|")[0]:
                                test_runs += 1
                                if first_test_turn is None:
                                    first_test_turn = turns
                                last_test_turn = turns
                            # heredoc-written files count as mutation
                            if re.search(r"(cat\s*>|cat\s*<<|tee\s|sed -i|>\s*\S+\.py)", cmd):
                                if first_mut_turn is None:
                                    first_mut_turn = turns
                                last_mut_turn = turns
                        elif name == "self_test":
                            self_test_calls += 1
                            test_runs += 1
                            if first_test_turn is None:
                                first_test_turn = turns
                            last_test_turn = turns
                think_chars += th
                text_chars += tx
                args_chars += ar
                tot = th + tx + ar or 1
                per_turn.append({
                    "turn": turns,
                    "input": u.get("input", 0),
                    "output": out,
                    "think_share": round(th / tot, 2),
                    "tools": list(cur_turn_tools),
                    "stop": m.get("stopReason"),
                })
            elif role == "toolResult":
                body = "".join(c.get("text", "") for c in m.get("content", []) if c.get("type") == "text")
                result_bytes += len(body)
                name = m.get("toolName")
                result_bytes_by_tool[name] += len(body)
                if m.get("isError"):
                    tool_errors += 1
                cn = call_names.get(m.get("toolCallId"))
                is_test = False
                if cn:
                    n, a = cn
                    if n == "self_test":
                        is_test = True
                    elif n == "bash" and TEST_RE.search(a.get("command", "")):
                        is_test = True
                if is_test:
                    if PYTEST_FAIL_RE.search(body) and first_fail_signal_turn is None:
                        first_fail_signal_turn = turns
                    if PYTEST_PASS_RE.search(body) and not PYTEST_FAIL_RE.search(body) and first_pass_signal_turn is None:
                        first_pass_signal_turn = turns

    secs = None
    if len(turn_ts) >= 2 and turn_ts[0] and turn_ts[-1]:
        secs = (turn_ts[-1] - turn_ts[0]) / 1000
    tot_chars = think_chars + text_chars + args_chars or 1
    receipt = {}
    rp = cell_dir / "receipt.json"
    if rp.exists():
        try:
            receipt = json.loads(rp.read_text())
        except Exception:
            receipt = {}
    patch_lines = None
    pp = cell_dir / "patch.diff"
    if pp.exists():
        patch_lines = sum(1 for l in pp.read_text(errors="replace").splitlines() if l.startswith(("+", "-")) and not l.startswith(("+++", "---")))
    return {
        "run": run,
        "arm": arm,
        "cell": cell_dir.name,
        "task": attempt.get("task"),
        "code": attempt.get("code"),
        "verdict": attempt.get("verdict"),
        "turns": turns,
        "out_tokens": out_tokens,
        "reasoning_tokens_reported": thinking_tokens_reported,
        "think_chars": think_chars,
        "text_chars": text_chars,
        "args_chars": args_chars,
        "think_tok_est": round(out_tokens * think_chars / tot_chars),
        "text_tok_est": round(out_tokens * text_chars / tot_chars),
        "args_tok_est": round(out_tokens * args_chars / tot_chars),
        "tool_calls": dict(tool_calls),
        "n_tool_calls": sum(tool_calls.values()),
        "edits": sum(edits_by_file.values()),
        "writes": sum(writes_by_file.values()),
        "files_edited": len(edits_by_file),
        "edit_churn_files": {k: v for k, v in edits_by_file.items() if v > 1},
        "first_mut_turn": first_mut_turn,
        "last_mut_turn": last_mut_turn,
        "first_test_turn": first_test_turn,
        "last_test_turn": last_test_turn,
        "first_fail_signal_turn": first_fail_signal_turn,
        "first_pass_signal_turn": first_pass_signal_turn,
        "test_runs": test_runs,
        "self_test_calls": self_test_calls,
        "tool_errors": tool_errors,
        "max_input": max(inputs) if inputs else 0,
        "final_input": inputs[-1] if inputs else 0,
        "mean_input_growth_per_turn": round((inputs[-1] - inputs[0]) / max(1, len(inputs) - 1)) if len(inputs) > 1 else 0,
        "result_bytes": result_bytes,
        "result_bytes_by_tool": dict(result_bytes_by_tool),
        "wall_secs": round(secs) if secs else None,
        "secs_per_turn": round(secs / turns, 1) if secs and turns else None,
        "patch_lines": patch_lines,
        "prompt_chars": first_turn_prompt_len,
        "last_text_tail": last_text.strip()[-400:],
        "per_turn": per_turn,
        "guard_firings": receipt.get("guard_firings") or receipt.get("guards"),
    }


def main():
    rows = []
    for run in sorted(RUNS.iterdir()):
        if not run.is_dir():
            continue
        for arm in ("baseline", "engine"):
            ad = run / arm
            if not ad.is_dir():
                continue
            for cell in sorted(ad.iterdir()):
                if cell.is_dir() and cell.name != "engine-contracts":
                    r = analyse(cell, arm, run.name)
                    if r:
                        rows.append(r)
    (OUT / "cells.json").write_text(json.dumps(rows, indent=1))
    # markdown table
    cols = ["run", "arm", "code", "verdict", "turns", "out_tokens", "think_tok_est", "text_tok_est", "args_tok_est",
            "n_tool_calls", "edits", "writes", "first_mut_turn", "first_test_turn", "first_fail_signal_turn",
            "test_runs", "self_test_calls", "tool_errors", "max_input", "result_bytes", "wall_secs", "patch_lines"]
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        lines.append("| " + " | ".join(str(r.get(c)) for c in cols) + " |")
    (OUT / "cells.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
