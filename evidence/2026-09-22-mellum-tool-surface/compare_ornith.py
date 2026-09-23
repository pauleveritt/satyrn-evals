"""Mellum vs Ornith on selfhost-review-script: quality and performance per arm."""
import datetime as dt
import glob
import json
import os
import re
import statistics as st
import sys
from pathlib import Path

RUNS = os.path.expanduser("~/satyrn-runs")
NIGHTS = {
    "Ornith": "2026-09-21-comparison-selfhost-review-script",
    "Mellum": "2026-09-23-spike-mellum-class-review-script-n6",
}
PAT = re.compile(r"^(\S+ \S+),\d+ .*Chat completion: model=([^,]+), (\d+) tokens in ([\d.]+)s \(([\d.]+) tok/s\), prompt: (\d+)")
LOG = []
for f in sorted(glob.glob(os.path.expanduser("~/.omlx/logs/server.log*"))):
    for line in Path(f).read_text(errors="ignore").splitlines():
        if m := PAT.match(line):
            LOG.append((dt.datetime.strptime(m[1], "%Y-%m-%d %H:%M:%S"), m[2], int(m[3]), float(m[4])))

ANNOUNCE = re.compile(r"(let'?s|we'?ll|we will|now,? (i|we)|next,? (i|we))[^.\n]{0,80}\.?\s*$", re.I)


def transcript_facts(path):
    msgs, stamps = [], []
    for line in Path(path).read_text().splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("type") == "session":
            stamps.append(dt.datetime.fromisoformat(ev["timestamp"].replace("Z", "+00:00")))
        if ev.get("type") == "message_end":
            m = ev["message"]
            msgs.append(m)
            if m.get("timestamp"):
                stamps.append(dt.datetime.fromtimestamp(m["timestamp"] / 1000, dt.UTC))
    lint = None
    calls = {}
    for m in msgs:
        if m.get("role") == "assistant":
            for c in m.get("content", []):
                if c.get("type") == "toolCall":
                    calls[c.get("id")] = json.dumps(c.get("arguments"))
        if m.get("role") == "toolResult" and "ruff check" in calls.get(m.get("toolCallId"), ""):
            lint = not m.get("isError")
    last = next((m for m in reversed(msgs) if m.get("role") == "assistant"), None)
    announce = False
    if last and last.get("stopReason") == "stop":
        has_call = any(c.get("type") == "toolCall" for c in last.get("content", []))
        text = "".join(c.get("text", "") for c in last.get("content", []) if c.get("type") == "text").strip()
        think = "".join(c.get("thinking", "") for c in last.get("content", []) if c.get("type") == "thinking").strip()
        announce = not has_call and not text and bool(ANNOUNCE.search(think[-200:]))
    wall = (max(stamps) - min(stamps)).total_seconds() if stamps else None
    return {"lint_clean_last": lint, "announce_stop": announce, "wall": wall,
            "window": (min(stamps), max(stamps)) if stamps else None}


def arm_rows(night, arm):
    s = json.loads(Path(f"{RUNS}/{night}/{arm}/summary.json").read_text())
    rows = []
    for c in s["cells"]:
        a = json.loads(Path(f"{RUNS}/{night}/{arm}/{c}/attempt.json").read_text())
        e, p = s["evidence"][c], s["pathology"].get(c, {})
        t = transcript_facts(f"{RUNS}/{night}/{arm}/{c}/transcript.txt")
        rows.append({"cell": c[-13:], "code": a["code"], "verdict": a["verdict"], "turns": e["turns"],
                     "out": e["output_tokens"], "calls": e["tool_calls"], "commits": e["git_commits"],
                     "repeats": p.get("repeats"), "churn": p.get("churn"), "self_test": e.get("self_test_calls"),
                     "length_stops": e.get("length_stops"), **t})
    return rows


def throughput(model_sub, rows):
    lo = min(r["window"][0] for r in rows if r["window"]).astimezone().replace(tzinfo=None)
    hi = max(r["window"][1] for r in rows if r["window"]).astimezone().replace(tzinfo=None)
    w = [x for x in LOG if lo <= x[0] <= hi + dt.timedelta(seconds=5) and model_sub in x[1]]
    toks, gen = sum(x[2] for x in w), sum(x[3] for x in w)
    return toks / gen if gen else None, (hi - lo).total_seconds()


def med(xs):
    xs = [x for x in xs if x is not None]
    return st.median(xs) if xs else None


out = {}
for model, night in NIGHTS.items():
    for arm in ("baseline", "engine"):
        rows = arm_rows(night, arm)
        tps, span = throughput("Ornith" if model == "Ornith" else "swe-pi", rows)
        passed = [r for r in rows if r["verdict"] == "pass"]
        out[f"{model} {arm}"] = {
            "n": len(rows), "pass": len(passed),
            "codes": dict(sorted({r["code"]: sum(x["code"] == r["code"] for x in rows) for r in rows}.items())),
            "verdicts": {v: sum(r["verdict"] == v for r in rows) for v in {r["verdict"] for r in rows}},
            "median_out": med(r["out"] for r in rows), "median_out_pass": med(r["out"] for r in passed),
            "median_turns": med(r["turns"] for r in rows), "median_turns_pass": med(r["turns"] for r in passed),
            "median_wall": med(r["wall"] for r in rows),
            "committed": sum(1 for r in rows if r["commits"]), "lint_clean_last": sum(1 for r in rows if r["lint_clean_last"]),
            "lint_ran": sum(1 for r in rows if r["lint_clean_last"] is not None),
            "announce_stop": sum(r["announce_stop"] for r in rows),
            "repeats_total": sum(r["repeats"] or 0 for r in rows), "churn_total": sum(r["churn"] or 0 for r in rows),
            "length_stops": sum(r["length_stops"] or 0 for r in rows),
            "decode_tok_s_k3": round(tps, 1) if tps else None, "night_span_s": round(span),
        }
        if "-v" in sys.argv:
            for r in rows:
                print(model, arm, {k: v for k, v in r.items() if k != "window"})
print(json.dumps(out, indent=1))
