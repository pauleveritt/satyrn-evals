"""EB1: offline read of the EB0 cells, no model, no network, stdlib only.

Usage: ``python3 evidence/2026-10-03-eb1-read/eb1.py [RUNS_ROOT]`` (default
``~/satyrn-runs``). Prints every table in this directory's README.

Rules: tool calls are counted from ``tool_execution_start``, one per call;
context for a turn is ``usage.input + usage.cacheRead``; a delivered pass is
``attempt.json`` ``verdict == "pass"``; medians carry ranges and
denominators; nothing is pooled across tasks or arms.
"""

from __future__ import annotations

import itertools
import json
import math
import random
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

TASKS = {
    "depth-3": "2026-10-02-eb0-agentclinic-repair-depth-3",
    "guard-prefixes": "2026-10-02-eb0-selfhost-guard-prefixes",
    "review-script": "2026-10-02-eb0-selfhost-review-script",
}
ARMS = ("baseline", "engine")
EDIT_TOOLS = {"edit", "write"}
NOTE = "[satyrn-engine note"
SELF_TEST_NOTE = "The Engine also ran self_test"
SUMMARY = re.compile(r"^.*\b\d+ (?:passed|failed|errors?|deselected|skipped)\b.* in [\d.]+s.*$", re.M)
TESTISH = re.compile(r"tests/|test_\w*\.py")
SEED = 20261003


# ---------------------------------------------------------------- parsing

def _events(path: Path):
    with path.open() as handle:
        for line in handle:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def _text(message: dict) -> str:
    content = message.get("content")
    if isinstance(content, str):
        return content
    return "".join(p.get("text", "") for p in content or [] if isinstance(p, dict))


def shape(text: str) -> str:
    if text.startswith("Validation failed"):
        return "schema"
    for code in ("ANCHOR_MISSING", "NO_CHANGE_REQUESTED", "REVISION_STALE", "ANCHOR_ALREADY_APPLIED"):
        if code in text:
            return code
    if text.startswith("No changes made"):
        return "NO_CHANGE (pi)"
    if text.startswith("Could not find"):
        return "Could not find (pi)"
    if "outside the attempt worktree" in text:
        return "confinement"
    if "outside the contract's writable paths" in text:
        return "scope (engine)"
    return "other"


def schema_shape(args: dict) -> str:
    """Shape of an edit call Pi's schema refused (from recorded args)."""
    edits = args.get("edits")
    if "path" not in args:
        if isinstance(edits, list) and edits and all(isinstance(e, dict) for e in edits):
            if all("edits" in e for e in edits):
                paths = {e.get("path") for e in edits}
                return "nested one-file" if len(paths) == 1 else "multi-file"
            paths = {e.get("path") for e in edits}
            if None not in paths and len(paths) == 1:
                return "per-item path, one file"
            if len(paths - {None}) > 1:
                return "multi-file"
        return "other"
    if isinstance(edits, str):
        return "edits as string"
    return "other"


def is_test_cmd(cmd: str) -> bool:
    return "pytest" in cmd


def targeted(cmd: str) -> list[str]:
    """Test paths named in a pytest command (empty = full run)."""
    return sorted(set(re.findall(r"(tests/[\w/.-]*\.py|test_\w+\.py)", cmd)))


def red(summary: str) -> bool:
    return bool(re.search(r"\b\d+ (failed|errors?)\b", summary))


def read_cell(cell: Path) -> dict:
    att = json.loads((cell / "attempt.json").read_text())
    turns: list[dict] = []
    calls: dict[str, dict] = {}
    order: list[str] = []
    customs: list[tuple[int, str, str]] = []
    first_user = ""
    for e in _events(cell / "transcript.txt"):
        t = e.get("type")
        if t == "tool_execution_start":
            cid = e["toolCallId"]
            calls[cid] = {"name": e.get("toolName"), "args": e.get("args") or {}, "turn": len(turns) - 1,
                          "text": "", "error": None, "ts": None}
            order.append(cid)
            turns[-1]["calls"].append(cid)
        elif t == "message_end":
            m = e["message"]
            role = m.get("role")
            if role == "assistant":
                u = m["usage"]
                turns.append({"out": u["output"], "ctx": u["input"] + u.get("cacheRead", 0),
                              "ts": m.get("timestamp"), "calls": [], "stop": m.get("stopReason")})
            elif role == "toolResult":
                c = calls.get(m.get("toolCallId"))
                if c is not None:
                    c["text"], c["error"], c["ts"] = _text(m), bool(m.get("isError")), m.get("timestamp")
            elif role == "custom":
                customs.append((len(turns), m.get("customType"), _text(m)))
            elif role == "user" and not first_user:
                first_user = _text(m)
    timeline: dict[str, list[float]] = defaultdict(list)
    stamps = []
    if (cell / "timeline.jsonl").exists():
        for e in _events(cell / "timeline.jsonl"):
            timeline[e.get("toolCallId")].append(e["at"])
            stamps.append(e["at"])
    patch = (cell / "patch.diff").read_text(errors="replace") if (cell / "patch.diff").exists() else ""
    new_files = set(re.findall(r"^diff --git a/(\S+) b/\S+\nnew file mode", patch, re.M))
    patched = set(re.findall(r"^diff --git a/(\S+) b/", patch, re.M))
    cell_d = {"name": cell.name, "verdict": att.get("verdict"), "code": att.get("code"),
              "confinement": att.get("confinement"), "turns": turns, "calls": calls, "order": order,
              "customs": customs, "timeline": timeline, "stamps": stamps, "new_files": new_files,
              "patched": patched, "first_user": first_user}
    classify(cell_d)
    return cell_d


def created_tests(cell: dict) -> set[str]:
    out = {p for p in cell["new_files"] if TESTISH.search(p)}
    for c in cell["calls"].values():
        p = str(c["args"].get("path", "")) if isinstance(c["args"], dict) else ""
        if c["name"] == "write" and c["error"] is False and TESTISH.search(p) and p not in cell["patched"]:
            out.add(p)  # created then removed (scratch)
    return out


def classify(cell: dict) -> None:
    turns, calls = cell["turns"], cell["calls"]
    created = created_tests(cell)
    bases = {Path(p).name for p in created}
    steer = next((i for i, kind, _ in cell["customs"] if kind == "finish_nudged"), None)
    landed = [i for i, t in enumerate(turns)
              if any(calls[c]["name"] in EDIT_TOOLS and calls[c]["error"] is False for c in t["calls"])]
    first_landed = landed[0] if landed else len(turns)
    cell["first_landed"] = first_landed
    cell["steer"] = steer
    cell["created_tests"] = created
    pre_calls = [c for c in cell["order"] if calls[c]["turn"] < first_landed]
    cell["pre_calls"] = len(pre_calls)
    cell["pre_test_calls"] = sum(1 for c in pre_calls if TESTISH.search(json.dumps(calls[c]["args"])))
    prev_rej = None
    for i, t in enumerate(turns):
        cs = [calls[c] for c in t["calls"]]
        rej = [c for c in cs if c["name"] in EDIT_TOOLS and c["error"]]
        touches_created = False
        for c in cs:
            a = c["args"] if isinstance(c["args"], dict) else {}
            if c["name"] in EDIT_TOOLS and str(a.get("path", "")) in created:
                touches_created = True
            if c["name"] == "bash" and any(b in str(a.get("command", "")) for b in bases):
                touches_created = True
        if not cs:
            cat = "final"
        elif steer is not None and i >= steer:
            cat = "post-steer"
        elif prev_rej is not None:
            cat = "retry:" + prev_rej
        elif touches_created:
            cat = "test file"
        elif i < first_landed:
            cat = "pre-edit"
        elif any(c["name"] in EDIT_TOOLS and c["error"] is False for c in cs):
            cat = "src edit"
        elif any(c["name"] == "self_test" or (c["name"] == "bash" and is_test_cmd(str(c["args"].get("command", ""))))
                 for c in cs):
            cat = "test run"
        else:
            cat = "probe"
        t["cat"] = cat
        prev_rej = shape(rej[0]["text"]) if rej else None


# ---------------------------------------------------------------- helpers

def med(values, fmt="{:,.0f}") -> str:
    v = [x for x in values if x is not None]
    if not v:
        return "-"
    return f"{fmt.format(statistics.median(v))} ({fmt.format(min(v))}-{fmt.format(max(v))})"


def m(values) -> float:
    v = [x for x in values if x is not None]
    return statistics.median(v) if v else 0.0


def out_total(cell) -> int:
    return sum(t["out"] for t in cell["turns"])


def load(root: Path) -> dict:
    data = {}
    for task, d in TASKS.items():
        for arm in ARMS:
            arm_dir = root / d / arm
            data[task, arm] = [read_cell(c) for c in sorted(arm_dir.iterdir()) if (c / "attempt.json").exists()]
    return data


def passes(cells):
    return [c for c in cells if c["verdict"] == "pass"]


# ---------------------------------------------------------------- section 1

def section1(data) -> list[str]:
    print("\n## 1. Floor set")
    floor = []
    for task in TASKS:
        b, e = (passes(data[task, a]) for a in ARMS)
        bo, eo = [out_total(c) for c in b], [out_total(c) for c in e]
        pairs = len(bo) * len(eo)
        eh = sum(1 for x in eo for y in bo if x > y)
        bh = sum(1 for x in eo for y in bo if y > x)
        need = -(-3 * pairs // 4)
        verdicts = {a: Counter(str(c["verdict"]) + ("" if c["code"] == "OK" else f"/{c['code']}") for c in data[task, a])
                    for a in ARMS}
        ok = len(b) >= 4 and len(e) >= 4 and max(eh, bh) >= need
        if ok:
            floor.append(task)
        print(f"{task}: B {len(b)}/6 {dict(verdicts['baseline'])}; E {len(e)}/6 {dict(verdicts['engine'])}; "
              f"pairs {pairs}, Engine higher {eh}, Baseline higher {bh}, ties {pairs - eh - bh}, need {need} -> "
              f"{'IN' if ok else 'out'}")
        print(f"   output/pass B {med(bo)}  E {med(eo)}; turns B {med([len(c['turns']) for c in b])} "
              f"E {med([len(c['turns']) for c in e])}; calls B {med([len(c['order']) for c in b])} "
              f"E {med([len(c['order']) for c in e])}; peak B {med([max(t['ctx'] for t in c['turns']) for c in b])} "
              f"E {med([max(t['ctx'] for t in c['turns']) for c in e])}; span min B "
              f"{med([(max(c['stamps']) - min(c['stamps'])) / 60 for c in b], '{:.1f}')} E "
              f"{med([(max(c['stamps']) - min(c['stamps'])) / 60 for c in e], '{:.1f}')}")
        for a in ARMS:
            flagged = [c["name"][-13:] for c in data[task, a] if (c["confinement"] or {}).get("refusals")]
            if flagged:
                print(f"   {a}: cells with confinement refusals: {flagged}")
    return floor


# ---------------------------------------------------------------- section 2

CATS = ["pre-edit", "test file", "retry:schema", "retry:ANCHOR_MISSING", "retry:NO_CHANGE_REQUESTED",
        "retry:NO_CHANGE (pi)", "retry:Could not find (pi)", "retry:confinement", "retry:scope (engine)",
        "retry:other", "post-steer", "src edit", "test run", "probe", "final"]


def cat_tokens(cell) -> Counter:
    c = Counter({k: 0 for k in CATS})
    for t in cell["turns"]:
        c[t["cat"]] += t["out"]
    return c


def section2(data, tasks) -> None:
    print("\n## 2. Attribution (output tokens per delivered pass; median and mean per arm)")
    for task in tasks:
        b, e = (passes(data[task, a]) for a in ARMS)
        cb, ce = [cat_tokens(c) for c in b], [cat_tokens(c) for c in e]
        print(f"\n### {task} (B n={len(b)}, E n={len(e)})")
        print("| category | B median | E median | d median | B mean | E mean | d mean | E cells>0 | B cells>0 |")
        print("|---|---|---|---|---|---|---|---|---|")
        sd_med = 0.0
        for k in CATS:
            vb, ve = [x[k] for x in cb], [x[k] for x in ce]
            if not any(vb) and not any(ve):
                continue
            dm = m(ve) - m(vb)
            sd_med += dm
            print(f"| {k} | {m(vb):,.0f} | {m(ve):,.0f} | {dm:+,.0f} | {statistics.mean(vb):,.0f} | "
                  f"{statistics.mean(ve):,.0f} | {statistics.mean(ve) - statistics.mean(vb):+,.0f} | "
                  f"{sum(1 for x in ve if x)}/{len(ve)} | {sum(1 for x in vb if x)}/{len(vb)} |")
        tb, te = [out_total(c) for c in b], [out_total(c) for c in e]
        print(f"| **total** | {m(tb):,.0f} | {m(te):,.0f} | {m(te) - m(tb):+,.0f} | {statistics.mean(tb):,.0f} | "
              f"{statistics.mean(te):,.0f} | {statistics.mean(te) - statistics.mean(tb):+,.0f} | | |")
        print(f"residual of medians (total d - sum of category d): {m(te) - m(tb) - sd_med:+,.0f}")
        for a, cs in (("B", b), ("E", e)):
            print(f"  {a}: turns before first landed edit {med([c['first_landed'] for c in cs])}; calls before it "
                  f"{med([c['pre_calls'] for c in cs])}, touching tests {med([c['pre_test_calls'] for c in cs])}; "
                  f"passes creating a test file {sum(1 for c in cs if c['created_tests'])}/{len(cs)}; "
                  f"retry turns {med([sum(1 for t in c['turns'] if t['cat'].startswith('retry')) for c in cs])}; "
                  f"post-steer turns {med([sum(1 for t in c['turns'] if t['cat'] == 'post-steer') for c in cs]) if a == 'E' else '-'}")
    print("\n### Rejected edit/write calls, all cells (not only passes)")
    for task in TASKS:
        for a in ARMS:
            shapes, sch, cells_with = Counter(), Counter(), 0
            for c in data[task, a]:
                n = 0
                for x in c["calls"].values():
                    if x["name"] in EDIT_TOOLS and x["error"]:
                        n += 1
                        s = shape(x["text"])
                        shapes[s] += 1
                        if s == "schema":
                            sch[schema_shape(x["args"])] += 1
                cells_with += n > 0
            print(f"  {task} {a}: {sum(shapes.values())} in {cells_with}/{len(data[task, a])} cells {dict(shapes)}"
                  f"{' schema shapes ' + str(dict(sch)) if sch else ''}")


# ---------------------------------------------------------------- section 3

def self_test_events(cell) -> list[dict]:
    evs = []
    last_model_run = None
    for cid in cell["order"]:
        c = cell["calls"][cid]
        txt = c["text"] or ""
        cmd = str(c["args"].get("command", "")) if isinstance(c["args"], dict) else ""
        tl = cell["timeline"].get(cid, [])
        dur = (max(tl) - min(tl)) if len(tl) >= 2 else None
        if c["name"] == "bash" and is_test_cmd(cmd):
            model_part = txt.split(NOTE)[0]
            ms = SUMMARY.findall(model_part)
            model = {"targeted": bool(targeted(cmd)), "paths": targeted(cmd), "red": bool(ms) and red(ms[-1]),
                     "summary": ms[-1] if ms else None}
        else:
            model = None
        if c["name"] == "self_test" or SELF_TEST_NOTE in txt:
            eng = txt[txt.find(NOTE):] if c["name"] != "self_test" else txt
            sums = SUMMARY.findall(eng)
            prev = model if c["name"] != "self_test" else last_model_run
            failed_files = sorted(set(re.findall(r"^(?:FAILED|ERROR) (\S+?\.py)", eng, re.M)))
            outside = None
            if sums and red(sums[0]) and prev and prev["targeted"]:
                outside = [f for f in failed_files if f not in prev["paths"] and Path(f).name not in
                           {Path(p).name for p in prev["paths"]}]
            evs.append({"kind": "tool" if c["name"] == "self_test" else "note", "summaries": len(sums),
                        "sum_text": sums, "dur": dur, "bytes": len(eng.encode()),
                        "dots": sum(len(line) + 1 for line in eng.splitlines() if re.fullmatch(r"[.sFExX]+\s+\[\s*\d+%\]", line)),
                        "venv": "VIRTUAL_ENV" in eng,
                        "venv_line": next((ln for ln in eng.splitlines() if "VIRTUAL_ENV" in ln), None), "red": bool(sums) and red(sums[0]), "prev": prev,
                        "outside": outside, "in_s": [float(x) for x in re.findall(r" in ([\d.]+)s", "\n".join(sums))]})
        if model is not None:
            last_model_run = model
    return evs


def section3(data) -> None:
    print("\n## 3. self_test path (Engine arm, all cells)")
    for task in TASKS:
        cells = data[task, "engine"]
        evs = [(c, ev) for c in cells for ev in self_test_events(c)]
        print(f"\n### {task}: {len(evs)} events in {len({c['name'] for c, _ in evs})}/{len(cells)} cells "
              f"(tool {sum(1 for _, e in evs if e['kind'] == 'tool')}, note {sum(1 for _, e in evs if e['kind'] == 'note')})")
        if not evs:
            continue
        print(f"  two suite summaries: {sum(1 for _, e in evs if e['summaries'] >= 2)}/{len(evs)}; "
              f"summary counts {dict(Counter(e['summaries'] for _, e in evs))}")
        for kind in ("tool", "note"):
            ks = [e for _, e in evs if e["kind"] == kind]
            if ks:
                print(f"  {kind}: call wall clock s {med([e['dur'] for e in ks], '{:.1f}')} (missing "
                      f"{sum(1 for e in ks if e['dur'] is None)}); Engine pytest in-times summed s "
                      f"{med([sum(e['in_s']) for e in ks], '{:.1f}')}; bytes "
                      f"{med([e['bytes'] for e in ks])}; dot-line bytes {med([e['dots'] for e in ks])}; "
                      f"VIRTUAL_ENV warning {sum(e['venv'] for e in ks)}/{len(ks)}; dot lines present {sum(1 for e in ks if e['dots'])}/{len(ks)}")
        withprev = [e for _, e in evs if e["prev"]]
        print(f"  model's preceding run known: {len(withprev)}/{len(evs)}; targeted "
              f"{sum(e['prev']['targeted'] for e in withprev)}, full {sum(not e['prev']['targeted'] for e in withprev)}; "
              f"red {sum(e['prev']['red'] for e in withprev)}, green {sum(not e['prev']['red'] for e in withprev)}")
        reds = [e for _, e in evs if e["red"]]
        print(f"  Engine red: {len(reds)}/{len(evs)}; of which model's run was red {sum(1 for e in reds if e['prev'] and e['prev']['red'])}; "
              f"after a targeted model run {sum(1 for e in reds if e['outside'] is not None)}, of those with any failure "
              f"outside the files the model ran: {sum(1 for e in reds if e['outside'])}")
        per_cell = Counter(c["name"] for c, _ in evs)
        print(f"  events per cell (all 6): {med([per_cell.get(c['name'], 0) for c in cells])}; Engine seconds per cell "
              f"(sum of call durations): {med([sum(e['dur'] or 0 for cc, e in evs if cc is c) for c in cells], '{:.0f}')}")
        for c, e in evs:
            print(f"    {c['name'][-13:]} {c['verdict']:5} {e['kind']:4} dur {e['dur'] or 0:6.1f}s bytes {e['bytes']:5} "
                  f"prev {('T' if e['prev']['targeted'] else 'F') + ('red' if e['prev']['red'] else 'grn') if e['prev'] else '-':6} "
                  f"{' | '.join(s.strip('= ') for s in e['sum_text'])}")


# ---------------------------------------------------------------- section 4

def context_parts(cell) -> dict:
    """Split context at the peak turn into first-turn, own output, injected classes (tokens)."""
    turns, calls = cell["turns"], cell["calls"]
    peak_i = max(range(len(turns)), key=lambda i: turns[i]["ctx"])
    parts = Counter(first=turns[0]["ctx"])
    neg = 0
    customs_by_turn = defaultdict(list)
    for i, kind, text in cell["customs"]:
        customs_by_turn[i - 1].append(text)  # custom message arrives after turn i-1's results
    for i in range(peak_i):
        parts["own output"] += turns[i]["out"]
        inj = turns[i + 1]["ctx"] - turns[i]["ctx"] - turns[i]["out"]
        if inj < 0:
            neg += 1
        b = Counter()
        for cid in turns[i]["calls"]:
            c = calls[cid]
            txt = c["text"] or ""
            if c["name"] == "self_test":
                b["engine notes"] += len(txt)
            elif NOTE in txt:
                at = txt.find(NOTE)
                b["engine notes"] += len(txt) - at
                b["other tool results"] += at
            elif c["name"] in EDIT_TOOLS and c["error"]:
                b["rejections"] += len(txt)
            elif c["name"] == "edit":
                b["edit-result echo"] += len(txt)
            else:
                b["other tool results"] += len(txt)
        for text in customs_by_turn.get(i, []):
            b["engine steer"] += len(text)
        tot = sum(b.values())
        for k, v in b.items():
            parts[k] += inj * v / tot if tot else 0
        if not tot:
            parts["unattributed"] += inj
    parts["peak"] = turns[peak_i]["ctx"]
    parts["peak_is_last"] = peak_i == len(turns) - 1
    parts["neg"] = neg
    return parts


def timing(cell) -> dict:
    model = tool = 0.0
    model_out = 0
    for t in cell["turns"]:
        ts_res = [cell["calls"][c]["ts"] for c in t["calls"] if cell["calls"][c]["ts"]]
        if not ts_res or t["ts"] is None:
            continue
        wall = (max(ts_res) - t["ts"]) / 1000
        ivs = sorted((min(v), max(v)) for c in t["calls"] if len(v := cell["timeline"].get(c, [])) >= 2)
        busy, cur = 0.0, None
        for s, e in ivs:
            if cur is None or s > cur[1]:
                if cur:
                    busy += cur[1] - cur[0]
                cur = [s, e]
            else:
                cur[1] = max(cur[1], e)
        if cur:
            busy += cur[1] - cur[0]
        model += wall - busy
        tool += busy
        model_out += t["out"]
    return {"model": model, "tool": tool, "s_per_k": model / model_out * 1000 if model_out else None}


def section4(data, tasks) -> None:
    print("\n## 4. Context and wall clock (delivered passes)")
    keys = ["first", "own output", "edit-result echo", "engine notes", "engine steer", "rejections",
            "other tool results", "unattributed"]
    for task in tasks:
        print(f"\n### {task}")
        rows = {}
        for a in ARMS:
            ps = passes(data[task, a])
            parts = [context_parts(c) for c in ps]
            tm = [timing(c) for c in ps]
            rows[a] = parts
            print(f"  {a} n={len(ps)}: peak {med([p['peak'] for p in parts])}; peak is last turn "
                  f"{sum(p['peak_is_last'] for p in parts)}/{len(ps)}; turns with negative injection "
                  f"{sum(p['neg'] for p in parts)}; model s {med([t['model'] for t in tm])}; tool s "
                  f"{med([t['tool'] for t in tm])}; model s per 1k output {med([t['s_per_k'] for t in tm], '{:.1f}')}")
        print("| component (tokens at peak) | B median | E median | d median |")
        print("|---|---|---|---|")
        for k in keys:
            vb, ve = [p[k] for p in rows["baseline"]], [p[k] for p in rows["engine"]]
            if any(vb) or any(ve):
                print(f"| {k} | {m(vb):,.0f} | {m(ve):,.0f} | {m(ve) - m(vb):+,.0f} |")


# ---------------------------------------------------------------- section 5

def section5(data) -> None:
    print("\n## 5. Remedy estimates (output tokens per delivered pass, Engine passes; median (range), mean)")
    for task in TASKS:
        b, e = (passes(data[task, a]) for a in ARMS)
        ce, cb = [cat_tokens(c) for c in e], [cat_tokens(c) for c in b]

        def est(keys, cells):
            return [sum(x[k] for k in keys) for x in cells]

        normal = []
        for c in e:  # schema retries whose rejected call a normalizer would accept
            tok = 0
            for i, t in enumerate(c["turns"][:-1]):
                rej = [c["calls"][x] for x in t["calls"] if c["calls"][x]["name"] in EDIT_TOOLS and c["calls"][x]["error"]]
                if rej and shape(rej[0]["text"]) == "schema" and schema_shape(rej[0]["args"]) in (
                        "per-item path, one file", "nested one-file", "edits as string") and \
                        c["turns"][i + 1]["cat"] == "retry:schema":
                    tok += c["turns"][i + 1]["out"]
            normal.append(tok)
        rows = {
            "R2 normalizer (schema, unambiguous shapes)": normal,
            "R2 all schema + ANCHOR_MISSING retries": est(["retry:schema", "retry:ANCHOR_MISSING"], ce),
            "contract test lines (E pre-edit + test file)": est(["pre-edit", "test file"], ce),
            "  same, minus Baseline median": None,
            "light path: whole E-B gap": None,
        }
        print(f"\n### {task} (E n={len(e)}, B n={len(b)})")
        for k, v in rows.items():
            if k.startswith("  same"):
                d = m(est(["pre-edit", "test file"], ce)) - m(est(["pre-edit", "test file"], cb))
                print(f"  {k}: {d:+,.0f}")
            elif k.startswith("light"):
                print(f"  {k}: {m([out_total(c) for c in e]) - m([out_total(c) for c in b]):+,.0f}")
            else:
                print(f"  {k}: {med(v)}; mean {statistics.mean(v):,.0f}")
        dedup, second, trimmed = [], [], []
        for c in e:
            evs = self_test_events(c)
            dedup.append(sum(ev["dur"] or 0 for ev in evs if ev["kind"] == "note" and ev["prev"] and ev["prev"]["red"]))
            second.append(sum(ev["in_s"][-1] for ev in evs if len(ev["in_s"]) >= 2))
            trimmed.append(sum(ev["dots"] + (len(ev["venv_line"]) if ev["venv_line"] else 0) for ev in evs))
        print(f"  self-test (all Engine passes; output tokens: none measurable, see README): seconds saved per pass by "
              f"dedup after a red model run {med(dedup)}; by dropping the second suite run {med(second)}; "
              f"note bytes removed by dot filter + VIRTUAL_ENV strip {med(trimmed)}")
        echo = [context_parts(c)["edit-result echo"] for c in e]
        print(f"  echo trimming: context tokens at peak {med(echo)}")


# ---------------------------------------------------------------- section 6

_DIST_CACHE: dict = {}


def mw_p(eng, base) -> float:
    """Exact permutation p of U_engine >= observed (H0 Engine <= Baseline), midranks for ties."""
    vals = list(eng) + list(base)
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    ranks = [0.0] * len(vals)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2 + 1
        i = j + 1
    ne = len(eng)
    obs = sum(ranks[:ne])
    key = (tuple(sorted(ranks)), ne)
    dist = _DIST_CACHE.get(key)
    if dist is None:
        r = sorted(ranks)
        dist = [sum(cmb) for cmb in itertools.combinations(r, ne)]
        _DIST_CACHE[key] = dist
    return sum(1 for s in dist if s >= obs - 1e-9) / len(dist)


def parity(eng, base, margin=1.25) -> bool:
    return statistics.median(eng) <= margin * statistics.median(base) and mw_p(eng, base) >= 0.05


def section6(data, tasks, reps=4000) -> None:
    print(f"\n## 6. Power of the parity rule (seed {SEED}, {reps} reps per world, n=6 per arm, Baseline passes resampled)")
    rng = random.Random(SEED)
    for task in tasks:
        bo = [out_total(c) for c in passes(data[task, "baseline"])]
        print(f"\n### {task}: Baseline passes {len(bo)}: {sorted(bo)}")
        logs = [math.log(x) for x in bo]
        mu, sd = statistics.mean(logs), statistics.stdev(logs)
        print(f"  log-normal fit: mu {mu:.3f}, sigma {sd:.3f}")
        for world, draw in (("resample", lambda: rng.choice(bo)), ("log-normal", lambda: math.exp(rng.gauss(mu, sd)))):
          for mult in (1.0, 1.1, 1.25, 1.5, 2.0, 3.0):
            hits = med_ok = mw_ok = 0
            for _ in range(reps):
                base = [draw() for _ in range(6)]
                eng = [draw() * mult for _ in range(6)]
                a = statistics.median(eng) <= 1.25 * statistics.median(base)
                bb = mw_p(eng, base) >= 0.05
                med_ok += a
                mw_ok += bb
                hits += a and bb
            print(f"  {world:10} Engine = {mult:.2f} x Baseline: parity declared {hits / reps:.3f} (median clause {med_ok / reps:.3f}, "
                  f"MW clause {mw_ok / reps:.3f})")
          ratios = sorted(statistics.median([draw() for _ in range(6)]) /
                          statistics.median([draw() for _ in range(6)]) for _ in range(reps))
          q = lambda p: ratios[int(p * (reps - 1))]
          print(f"  {world:10} true-parity median ratio E/B quantiles: 50% {q(.5):.2f}, 80% {q(.8):.2f}, "
                f"90% {q(.9):.2f}, 95% {q(.95):.2f}")


def main(argv) -> int:
    root = Path(argv[1]).expanduser() if len(argv) > 1 else Path("~/satyrn-runs").expanduser()
    data = load(root)
    floor = section1(data)
    print(f"\nfloor set: {floor}")
    section2(data, list(TASKS))
    section3(data)
    section4(data, list(TASKS))
    section5(data)
    section6(data, list(TASKS))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
