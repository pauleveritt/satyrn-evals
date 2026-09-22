#!/usr/bin/env python3
"""Read-only audit of every decision and debug cell: test runs, greens, edits,
skipped writers, per-turn usage, stop reasons. Writes audit.json + audit.md."""
import importlib.util, json, sys, re
from pathlib import Path
EVALS = Path("/Users/pauleveritt/projects/pauleveritt/satyrn-evals")
SCRIPT = EVALS / "evidence/2026-09-15-finishing-counterfactual/counterfactual.py"
OUT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("cf", SCRIPT)
cf = importlib.util.module_from_spec(spec); sys.modules["cf"] = cf; spec.loader.exec_module(cf)

def per_turn(events):
    """turn -> dict(tokens, think_chars, text_chars, args_chars, stop, input, ts)"""
    turns = {}
    turn = 0
    for e in events:
        if e.get("type") == "turn_start":
            turn += 1; turns[turn] = dict(tokens=0, think=0, text=0, args=0, stops=[], input=0, ts=[], reasoning=0)
        if e.get("type") == "message_end":
            m = e.get("message", {})
            if m.get("role") != "assistant": continue
            u = m.get("usage", {}); t = turns.setdefault(turn, dict(tokens=0, think=0, text=0, args=0, stops=[], input=0, ts=[], reasoning=0))
            t["tokens"] += u.get("output", 0); t["input"] = max(t["input"], u.get("input", 0)); t["reasoning"] += u.get("reasoning", 0) or 0
            t["stops"].append(m.get("stopReason")); t["ts"].append(m.get("timestamp"))
            for p in m.get("content", []):
                if p.get("type") == "thinking": t["think"] += len(p.get("thinking", ""))
                elif p.get("type") == "text": t["text"] += len(p.get("text", ""))
                elif p.get("type") == "toolCall": t["args"] += len(json.dumps(p.get("arguments", {})))
    return turns

def audit(spec_):
    manifest = json.loads((cf.TASKS / spec_.task / "manifest.json").read_text())
    sp = tuple(manifest["source_paths"])
    folder = cf.cell_dir(spec_)
    attempt = json.loads((folder / "attempt.json").read_text())
    events = cf.parse_events((folder / "transcript.txt").read_text())
    cwd = cf.session_cwd(events)
    steps = cf.steps_of(events)
    row = dict(task=spec_.task, group=spec_.group, attempt=spec_.attempt, code=attempt.get("code"), verdict=attempt.get("verdict"), cwd=cwd)
    # source edits without bash replay (write/edit only)
    edits = cf.source_edit_indices(steps, sp, cwd, {})
    row["first_source_edit"] = None if not edits else dict(step=edits[0], turn=steps[edits[0]].turn, tokens=steps[edits[0]].output_tokens, name=steps[edits[0]].name, path=steps[edits[0]].args.get("path"))
    row["all_edits"] = [dict(step=i, turn=steps[i].turn, name=steps[i].name, path=cf.tree_path(steps[i].args.get("path",""), cwd)) for i in range(len(steps)) if steps[i].name in ("write","edit") and not steps[i].is_error]
    row["edit_errors"] = [dict(step=s.index, turn=s.turn, name=s.name, path=s.args.get("path")) for s in steps if s.name in ("write","edit") and s.is_error]
    runs = []
    for s in steps:
        if cf.is_test_run(s):
            cmd = s.args.get("command", "") if s.name == "bash" else "<self_test>"
            lines = cf.summary_lines(s.text)
            runs.append(dict(step=s.index, turn=s.turn, tokens=s.output_tokens, name=s.name, cmd=cmd[:200], is_error=s.is_error, green=cf.is_green(s), summary=lines, after_first_edit=(edits and s.index >= edits[0]) or False, text_tail=s.text[-300:]))
    row["test_runs"] = runs
    # bash commands classification
    bashes = []
    for s in steps:
        if s.name == "bash":
            cmd = str(s.args.get("command", ""))
            plan = cf.plan_bash(cmd, cwd)
            bashes.append(dict(step=s.index, turn=s.turn, tokens=s.output_tokens, is_error=s.is_error, replayable=plan.replay is not None, read_only=cf.is_read_only_bash(cmd, cwd), verified=cf.bash_verified(s, cwd), could_write=cf.could_write_source(plan.remainder, sp, cwd) if plan.remainder else False, runs_pytest=cf.runs_pytest(cmd), cmd=cmd[:400]))
    row["bash"] = bashes
    trig = cf.find_trigger(steps, edits, cwd)
    row["trigger_no_bash_replay"] = None if trig is None else trig.__dict__ if hasattr(trig, "__dict__") else dict(step=trig.step, turn=trig.turn, tokens=trig.output_tokens, within=trig.within_budget)
    t = per_turn(events)
    row["turns"] = {k: dict(tokens=v["tokens"], think=v["think"], text=v["text"], args=v["args"], stops=v["stops"], input=v["input"], ts=v["ts"], reasoning=v["reasoning"]) for k, v in t.items()}
    row["n_turns"] = max(t) if t else 0
    row["total_tokens"] = sum(v["tokens"] for v in t.values())
    row["n_steps"] = len(steps)
    return row

rows = [audit(s) for s in (*cf.DECISION, *cf.DEBUG)]
(OUT / "audit.json").write_text(json.dumps(rows, indent=1, default=str))
md = ["| task | group | attempt | code | turns | tokens | 1st src edit (turn/tok) | test runs (turn:g/r) | trigger |", "|---|---|---|---|---|---|---|---|---|"]
for r in rows:
    fe = r["first_source_edit"]; fe_s = "-" if not fe else f"{fe['turn']}/{fe['tokens']}"
    runs = " ".join(f"{x['turn']}:{'G' if x['green'] else ('E' if x['is_error'] else 'r')}{'' if x['summary'] else '?'}" for x in r["test_runs"])
    tr = r["trigger_no_bash_replay"]
    md.append(f"| {r['task']} | {r['group']} | {r['attempt']} | {r['code']}{'-'+r['verdict'] if r['verdict'] else ''} | {r['n_turns']} | {r['total_tokens']} | {fe_s} | {runs} | {tr} |")
(OUT / "audit.md").write_text("\n".join(md) + "\n")
print("\n".join(md))
