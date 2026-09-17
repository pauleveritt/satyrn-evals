#!/usr/bin/env python3
"""Alternative Engine-observable triggers, evaluated offline on the same cells,
prefix-preserving: each trigger names a turn; the counterfactual verdict is the
graded worktree at the end of that turn (trajectory.json, std replay), with the
committed instrument's unmeasured caveats reported beside it."""
import json, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
audit = {r["attempt"]: r for r in json.load(open(HERE / "audit.json"))}
traj = {r["attempt"]: r for r in json.load(open(HERE / "trajectory.json"))}
cells = json.load(open("/Users/pauleveritt/projects/pauleveritt/satyrn-evals/evidence/2026-09-15-finishing-counterfactual/cells.json"))["cells"]
dcells = json.load(open("/Users/pauleveritt/projects/pauleveritt/satyrn-evals/evidence/2026-09-15-finishing-counterfactual/debug/cells.json"))["cells"]
committed = {c["attempt"]: c for c in cells + dcells}
PUBLIC = {"selfhost-run-record-gate": "uv run pytest -q", "selfhost-docs-linter": "uv run pytest -q", "selfhost-guard-prefixes": "uv run pytest -q", "selfhost-review-script": "uv run pytest -q", "agentclinic-repair-depth-3": "uv run python -m pytest tests/", "agentclinic-repair-depth-2": "uv run python -m pytest tests/", "agentclinic-repair-misleading-locus": "uv run python -m pytest tests/"}
BUDGET_TOK, BUDGET_TURN = 32000, 48

def within(run): return run["tokens"] <= BUDGET_TOK and run["turn"] <= BUDGET_TURN

def is_whole_suite(run, task):
    """The run targets the whole public suite: no node id (::), no -k, and either no path or a bare tests/ path."""
    cmd = run["cmd"]
    if run["name"] == "self_test": return True
    seg = [s for s in re.split(r"&&|;|\|\||\n", cmd) if "pytest" in s]
    if not seg: return False
    s = seg[0]
    if "::" in s or " -k " in s: return False
    paths = [w for w in s.split() if (w.startswith("tests") or w.endswith(".py")) and not w.startswith("-")]
    return all(p.rstrip("/") == "tests" for p in paths)

def verdict_at(attempt, turn):
    t = traj.get(attempt, {}).get("turns", {})
    if not t: return None
    keys = sorted(int(k) for k in t)
    prev = [k for k in keys if k <= turn]
    if not prev: return "base"
    return t[str(prev[-1])]["std"]["verdict"]

def first_pass_turn(attempt):
    t = traj.get(attempt, {}).get("turns", {})
    ks = sorted((int(k) for k, v in t.items() if v["std"]["verdict"] == "pass"))
    return ks[0] if ks else None

def tokens_at(attempt, turn):
    return audit[attempt]["turns"].get(str(turn), {}).get("tokens")

def cum_tokens(attempt, turn):
    return sum(v["tokens"] for k, v in audit[attempt]["turns"].items() if int(k) <= turn)

def edits_between(attempt, a, b):
    """Non-error write/edit steps with turn in (a, b]."""
    return [e for e in audit[attempt]["all_edits"] if a < e["turn"] <= b]

def triggers(attempt):
    r = audit[attempt]; task = r["task"]
    fe = r["first_source_edit"]
    runs = [x for x in r["test_runs"] if fe and x["step"] >= fe["step"]]
    greens = [x for x in runs if x["green"]]
    out = {}
    g_in = [g for g in greens if within(g)]
    out["T1 own-green (first)"] = greens[0]["turn"] if greens and within(greens[0]) else None
    ws = [g for g in greens if is_whole_suite(g, task)]
    out["T2 first whole-suite green"] = ws[0]["turn"] if ws and within(ws[0]) else None
    # T3: green with no write/edit in the N turns before it (N=1: the previous turn had no edit)
    for n in (1, 2):
        c = [g for g in greens if not edits_between(attempt, g["turn"] - n - 1, g["turn"] - 1) and not [e for e in r["all_edits"] if e["turn"] == g["turn"] and e["step"] < g["step"]]]
        out[f"T3 green after {n} non-editing turn(s)"] = c[0]["turn"] if c and within(c[0]) else None
    # T4: second green (a green re-confirmed by a later green with no source edit between)
    sec = None
    for i, g in enumerate(greens[1:], 1):
        if not [e for e in r["all_edits"] if greens[i-1]["turn"] < e["turn"] <= g["turn"] and not e["path"] is None and not (e["path"].startswith("tests") or "/test_" in e["path"])]:
            sec = g; break
    out["T4 green re-confirmed (no source edit since previous green)"] = sec["turn"] if sec and within(sec) else None
    out["T5 last green within budget"] = g_in[-1]["turn"] if g_in else None
    fp = first_pass_turn(attempt)
    out["T6 oracle: first hidden-pass turn"] = fp if fp is not None and cum_tokens(attempt, fp) <= BUDGET_TOK and fp <= BUDGET_TURN else None
    return out

NAMES = ["T1 own-green (first)", "T2 first whole-suite green", "T3 green after 1 non-editing turn(s)", "T3 green after 2 non-editing turn(s)", "T4 green re-confirmed (no source edit since previous green)", "T5 last green within budget", "T6 oracle: first hidden-pass turn"]
rows = []
for attempt, r in audit.items():
    c = committed.get(attempt, {})
    actual = c.get("actual") == "pass"
    tr = triggers(attempt) if r["first_source_edit"] else {n: None for n in NAMES}
    row = dict(task=r["task"], group=r["group"], attempt=attempt, code=r["code"], actual="pass" if actual else "not-pass", committed_unmeasured=c.get("unmeasured", []))
    for n in NAMES:
        t = tr.get(n)
        v = verdict_at(attempt, t) if t is not None else None
        cf = (v == "pass") if t is not None else actual
        row[n] = dict(turn=t, tokens=cum_tokens(attempt, t) if t else None, verdict=v, change=("rescue" if (not actual and cf) else "harm" if (actual and not cf) else "none"))
    rows.append(row)
json.dump(rows, open(HERE / "triggers.json", "w"), indent=1)
lines = ["| task | group | attempt | actual | " + " | ".join(n.split(" ")[0] + " turn:verdict" for n in NAMES) + " |", "|" + "---|" * (4 + len(NAMES))]
for row in rows:
    cells_ = []
    for n in NAMES:
        x = row[n]
        cells_.append("-" if x["turn"] is None else f"{x['turn']}:{(x['verdict'] or '?')[0]}{'*' if x['change']=='rescue' else ('!' if x['change']=='harm' else '')}")
    lines.append(f"| {row['task']} | {row['group']} | {row['attempt']} | {row['actual']} | " + " | ".join(cells_) + " |")
lines.append("\n`*` rescue (actual not-pass, graded pass at the trigger turn); `!` harm. Verdicts: p pass, f fail, u unavailable.\n")
lines.append("| trigger | decision rescues | decision harms | decision unmeasured-by-committed-rules among rescues | debug rescues | debug harms |")
lines.append("|---|---|---|---|---|---|")
for n in NAMES:
    dr = [r for r in rows if r["group"] == "decision" and r[n]["change"] == "rescue"]; dh = [r for r in rows if r["group"] == "decision" and r[n]["change"] == "harm"]
    br = [r for r in rows if r["group"] != "decision" and r[n]["change"] == "rescue"]; bh = [r for r in rows if r["group"] != "decision" and r[n]["change"] == "harm"]
    lines.append(f"| {n} | {len(dr)} ({', '.join(r['attempt'] for r in dr)}) | {len(dh)} ({', '.join(r['attempt'] for r in dh)}) | {sum(1 for r in dr if r['committed_unmeasured'])} | {len(br)} ({', '.join(r['attempt'] for r in br)}) | {len(bh)} ({', '.join(r['attempt'] for r in bh)}) |")
open(HERE / "triggers.md", "w").write("\n".join(lines) + "\n"); print("\n".join(lines))
