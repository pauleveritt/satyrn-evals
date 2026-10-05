"""Offline reader for EB comparison cells (no model, no network, no GPU, read-only).

Usage, from the satyrn-evals repo root:

    uv run python <this file> NIGHT_DIR [NIGHT_DIR ...] [--combine] [--line-report JSON ...] [--json]

Each NIGHT_DIR is a launch directory (``slots/``, ``launch.json``, and one
directory per arm holding ``<task>-<stamp>/`` cells). Output is one block per
(night, task, arm). Nights are NEVER pooled unless ``--combine`` is given, and
then only nights of the same task + arm + arm digest + contract digest (the
arm digest is the digest of the arm file that holds the engine pin).

Definitions are those of ``evidence/2026-10-02-engine-budget/cells.py`` (on
branch worktree-engine-budget) and its README 8b / EB1 README:

* tokens: ``usage.output`` summed over every assistant ``message_end`` in
  ``transcript.txt`` (cells.py:89-92).
* delivered pass: ``attempt.json`` ``verdict == "pass"`` (cells.py:59,139;
  EB1 README line 9). Admission does NOT remove a delivered pass (EB1 README
  line 21: the un-admitted guard-prefixes B pass is "counted"); an admitted-only
  figure is printed separately and labelled.
* output tokens per delivered pass: median (min-max) over delivered passes
  (cells.py:124-130, 141-143), never pooled across tasks or arms.
* calls: one per ``tool_execution_start`` (cells.py:71-72). A rejected call is
  a toolResult with ``isError`` and toolName edit/write (cells.py:101-104);
  every result has a start event (checked, orphans are flagged).
* schema rejection: rejected edit/write whose text starts "Validation failed"
  (cells.py:45-46).
* confinement_refused: ``entry_appended`` with customType ``confinement_refused``
  (cells.py:82-84; confinement.py:210-218).

Nothing here runs grading. For the 32k/48 line it only reads attempt.json's
``line_crossed`` and, if given, a report written by ``satyrn-evals grade-line``.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

EDIT_TOOLS = {"edit", "write"}
# harness codes that measured nothing about the model: launch.py:57-61
INFRASTRUCTURE_CODES = {
    "WORKSPACE_FAILED", "CLEANUP_FAILED", "GRADE_FAILED", "TRANSCRIPT_MISSING",
    "TRANSCRIPT_EMPTY", "MODEL_ERROR", "PATCH_INVALID",
}
WALL_CLOCK_CODES = {"COMMAND_TIMEOUT", "DEADLINE_EXCEEDED"}
_SLOT_RE = re.compile(r"^(\d{2})(\.spec|\.replaced-\d+)?\.json$")


# ----------------------------------------------------------------- transcript
def _events(path: Path):
    with path.open() as handle:
        for line in handle:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def _text(message: dict) -> str:
    return "".join(p.get("text", "") for p in message.get("content", []) if isinstance(p, dict))


def error_shape(text: str) -> str:
    """cells.py:44-55, plus two shapes cells.py leaves in 'other' (named by EB1 README
    section 2): the Engine scope refusal and Pi's 'No changes made'."""
    if text.startswith("Validation failed"):
        return "schema"
    for code in ("ANCHOR_MISSING", "REVISION_STALE", "NO_CHANGE_REQUESTED", "ANCHOR_ALREADY_APPLIED",
                 "ANCHOR_AMBIGUOUS", "INVALID_REQUEST", "REVISION_UNAVAILABLE"):
        if code in text:
            return code
    if "Could not find" in text:
        return "anchor (pi)"
    if "outside the attempt worktree" in text or "protected path" in text:
        return "confinement"
    if "outside the contract's writable paths" in text:  # engine scope.ts:67
        return "scope"
    if "No changes made" in text:
        return "pi no-change"
    return "other"


def read_transcript(path: Path) -> dict:
    starts: dict[str, str] = {}
    n_starts = 0
    out = turns = 0
    rejected: Counter[str] = Counter()
    orphan_results = 0
    results = 0
    guards: Counter[str] = Counter()
    for event in _events(path):
        kind = event.get("type")
        if kind == "tool_execution_start":
            n_starts += 1
            starts[event.get("toolCallId")] = event.get("toolName")
        elif kind == "entry_appended":
            custom = (event.get("entry") or {}).get("customType")
            if custom:
                guards[custom] += 1
        elif kind == "message_end":
            message = event["message"]
            role = message.get("role")
            if role == "assistant":
                turns += 1
                out += message["usage"]["output"]
            elif role == "toolResult":
                results += 1
                if message.get("toolCallId") not in starts:
                    orphan_results += 1
                if message.get("isError") and message.get("toolName") in EDIT_TOOLS:
                    rejected[error_shape(_text(message))] += 1
    return {"output": out, "turns": turns, "calls": n_starts, "results": results,
            "orphan_results": orphan_results, "rejected": rejected, "guards": guards}


# ------------------------------------------------------------------- night io
def _json(path: Path):
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def load_night(night: Path) -> dict:
    launch = _json(night / "launch.json")
    slots: dict[int, dict] = {}
    replaced: list[dict] = []
    sd = night / "slots"
    if sd.is_dir():
        for p in sorted(sd.iterdir()):
            m = _SLOT_RE.match(p.name)
            if not m:
                continue
            idx, suffix = int(m.group(1)), m.group(2)
            data = _json(p) or {}
            if suffix is None:
                slots.setdefault(idx, {})["result"] = data
            elif suffix == ".spec":
                slots.setdefault(idx, {})["spec"] = data
            else:
                replaced.append({"slot": idx, **data})
    return {"dir": night, "launch": launch, "slots": slots, "replaced": replaced}


def read_cell(night: Path, arm: str, slot_idx: int, result: dict) -> dict:
    cell = night / arm / result["attempt_dir"]
    att = _json(cell / "attempt.json") or {}
    row = {
        "slot": slot_idx, "attempt": result["attempt_dir"], "arm": arm, "task": att.get("task"),
        "code": att.get("code") or result.get("code"), "verdict": att.get("verdict", result.get("verdict")),
        "outcome": att.get("outcome"), "message": att.get("message"),
        "contract_digest": att.get("contract_digest"),
        "line_crossed": att.get("line_crossed", result.get("line_crossed")),
        "line_diff": (cell / "line.diff").is_file(),
        "deadline_phase": result.get("deadline_phase"),
        "confinement_attempt": att.get("confinement"), "has_attempt_json": bool(att),
        "output": None, "turns": None, "calls": None, "rejected": Counter(), "guards": Counter(),
        "transcript": False, "orphan_results": 0, "results": 0, "flags": [],
    }
    tpath = cell / "transcript.txt"
    if tpath.is_file():
        row.update(read_transcript(tpath))
        row["transcript"] = True
    else:
        row["flags"].append("transcript missing")
    if not att:
        row["flags"].append("attempt.json missing")
    if row["transcript"] and row["results"] != row["calls"]:
        row["flags"].append(f"calls {row['calls']} != tool results {row['results']} (cut mid-call)")
    if row["orphan_results"]:
        row["flags"].append(f"{row['orphan_results']} tool results without a start event")
    # admission: harness-written attempt.json confinement {refusals, reaches}; both zero = admitted
    conf = row["confinement_attempt"]
    row["conf_refusals_attempt"] = None if conf is None else conf.get("refusals")
    row["conf_reaches"] = None if conf is None else conf.get("reaches")
    row["admitted"] = None if conf is None else (conf.get("refusals") == 0 and conf.get("reaches") == 0)
    row["conf_refused_entries"] = row["guards"].get("confinement_refused", 0)
    row["scope_refused_entries"] = row["guards"].get("scope_refused", 0)
    if (conf is not None and row["transcript"]
            and conf.get("refusals") != row["conf_refused_entries"]):
        row["flags"].append(f"attempt.json refusals {conf.get('refusals')} != transcript entries {row['conf_refused_entries']}")
    code = row["code"]
    if code in INFRASTRUCTURE_CODES:
        row["flags"].append(f"INFRASTRUCTURE {code}")
    if code in WALL_CLOCK_CODES:
        row["flags"].append(f"WALL-CLOCK-CUT {code}" + (f" phase={row['deadline_phase']}" if row["deadline_phase"] else ""))
        if code == "DEADLINE_EXCEEDED" and row["deadline_phase"] not in (None, "command"):
            row["flags"].append("INFRASTRUCTURE deadline outside command phase")
    if row["verdict"] == "unavailable":
        receipt = _json(cell / "receipt.json") or {}
        row["flags"].append("verdict unavailable: " + str(receipt.get("reason", "no reason recorded"))[:120])
    if code == "BUDGET_EXCEEDED":
        row["flags"].append("BUDGET_EXCEEDED (model outcome, no verdict): " + str(row["message"])[:100])
    return row


def line_state(row: dict, line_report: dict[str, dict]) -> str:
    """Pass at the declared line. Mirrors line_grade.py:325-395 without grading anything."""
    rep = line_report.get(row["attempt"])
    if rep is not None:
        return f"{rep['line_verdict']} (grade-line)"
    if row["line_crossed"] is None:
        # never crossed: line_grade._never_crossed_verdict (265-279, 307-322)
        if row["code"] == "OK":
            return f"{row['verdict'] if row['verdict'] in ('pass', 'fail') else 'not-pass'} (never crossed)"
        if row["code"] == "BUDGET_EXCEEDED":
            return "BROKEN RECORD (budget without crossing; grade-line exits 4)"
        if row["code"] in INFRASTRUCTURE_CODES:
            return "unavailable (infrastructure)"
        return f"per line_grade rules for code {row['code']}"
    lc = row["line_crossed"]
    where = f"{lc.get('by')} @turn {lc.get('turn')}, {lc.get('output_tokens'):,} tok"
    return f"NEEDS grade-line [{where}; line.diff {'present' if row['line_diff'] else 'ABSENT'}]"


# -------------------------------------------------------------------- report
def _fmt_num(v: float) -> str:
    return f"{v:,.1f}" if isinstance(v, float) and v != int(v) else f"{int(v):,}"


def median_range(values: list) -> str:
    values = [v for v in values if v is not None]
    if not values:
        return "n/a (no values)"
    return f"{_fmt_num(statistics.median(values))} ({_fmt_num(min(values))}-{_fmt_num(max(values))})"


def group_block(title: str, rows: list[dict], expected: int | None, finished: int,
                notes: list[str], line_report: dict, line_budget: str) -> str:
    rows = sorted(rows, key=lambda r: (r.get("night", ""), r["slot"]))
    L = [f"\n== {title}"]
    L += [f"   {n}" for n in notes]
    passes = [r for r in rows if r["verdict"] == "pass"]
    verdicts = Counter(str(r["verdict"]) for r in rows)
    codes = Counter(str(r["code"]) for r in rows)
    exp = "unknown" if expected is None else str(expected)
    ok = expected is not None and finished == expected == len(rows)
    L.append(f"  denominators: expected cells {exp}; finished slots {finished}; cells read {len(rows)}"
             + ("" if ok else "   ** PARTIAL / MISMATCH **"))
    L.append(f"  verdicts {dict(verdicts)}; codes {dict(codes)}")
    L.append(f"  delivered passes (verdict==pass): {len(passes)} of {len(rows)} read"
             + (f" (of {expected} expected)" if expected is not None else ""))
    out = [r["output"] for r in passes]
    miss = [r["attempt"] for r in passes if r["output"] is None]
    L.append(f"  OUTPUT TOKENS PER DELIVERED PASS (median (min-max), n={len([o for o in out if o is not None])}): "
             f"{median_range(out)}" + (f"   MISSING transcript: {miss}" if miss else ""))
    if passes and all(r["output"] is not None for r in passes):
        L.append(f"     per pass: {sorted(out)}; mean {statistics.mean(out):,.0f} (secondary, not the EB decider)")
    adm = [r for r in passes if r["admitted"]]
    unk = [r for r in passes if r["admitted"] is None]
    L.append(f"     admitted delivered passes only (secondary): n={len(adm)} -> {median_range([r['output'] for r in adm])}"
             f"; un-admitted passes counted above: {[r['attempt'][-13:] for r in passes if r['admitted'] is False]}"
             + (f"; admission unknown: {[r['attempt'][-13:] for r in unk]}" if unk else ""))
    shapes: Counter[str] = Counter()
    for r in rows:
        shapes.update(r["rejected"])
    sch = [r["rejected"].get("schema", 0) for r in rows]
    L.append(f"  schema-rejected edit/write calls: total {sum(sch)} in {sum(1 for s in sch if s)} of {len(rows)} cells; "
             f"per cell {sch}")
    L.append(f"  all rejected edit/write calls: total {sum(shapes.values())} in {sum(1 for r in rows if r['rejected'])} of "
             f"{len(rows)} cells; shapes {dict(shapes)}")
    L.append(f"  confinement_refused entries: {sum(r['conf_refused_entries'] for r in rows)} "
             f"(cells with >=1: {[r['attempt'][-13:] for r in rows if r['conf_refused_entries']]}); "
             f"engine scope_refused entries: {sum(r['scope_refused_entries'] for r in rows)} "
             f"(cells: {[r['attempt'][-13:] for r in rows if r['scope_refused_entries']]})")
    n_adm = sum(1 for r in rows if r["admitted"])
    n_flag = sum(1 for r in rows if r["admitted"] is False)
    n_unk = sum(1 for r in rows if r["admitted"] is None)
    L.append(f"  admission (attempt.json confinement refusals==0 and reaches==0): admitted {n_adm}, flagged {n_flag}, unknown {n_unk}")
    lp = Counter()
    for r in rows:
        lp[line_state(r, line_report).split(" [")[0].split(" (")[0]] += 1
    L.append(f"  line {line_budget}: " + ", ".join(f"{k}: {v}" for k, v in sorted(lp.items()))
             + "  (cells needing `satyrn-evals grade-line` are NOT counted as pass or fail here)")
    L.append("  per cell:")
    L.append("   slot attempt-dir                                      code                 verdict      out_tok turns calls  schema/all-rej conf scope reach adm  line-crossed")
    for r in rows:
        lc = "-" if not r["line_crossed"] else f"{r['line_crossed']['by'][:3]}@{r['line_crossed']['turn']}"
        L.append(
            "   {slot:>2}   {attempt:<46} {code:<20} {verdict:<10} {out:>8} {turns:>5} {calls:>5}  {s:>4}/{a:<4}      {cr:>4} {sr:>5} {rc:>5}  {adm:<3}  {lc}".format(
                slot=r["slot"], attempt=r["attempt"], code=str(r["code"]), verdict=str(r["verdict"]),
                out="-" if r["output"] is None else f"{r['output']:,}", turns="-" if r["turns"] is None else r["turns"],
                calls="-" if r["calls"] is None else r["calls"], s=r["rejected"].get("schema", 0),
                a=sum(r["rejected"].values()), cr=r["conf_refused_entries"], sr=r["scope_refused_entries"],
                rc="-" if r["conf_reaches"] is None else r["conf_reaches"],
                adm={True: "yes", False: "NO", None: "?"}[r["admitted"]], lc=lc))
    for r in rows:
        L.append(f"     line: {r['attempt'][-13:]} -> {line_state(r, line_report)}")
    flagged = [(r["attempt"], f) for r in rows for f in r["flags"]]
    L.append("  infrastructure / wall-clock / anomaly flags: " + ("none" if not flagged else ""))
    for name, f in flagged:
        L.append(f"     {name}: {f}")
    return "\n".join(L)


def record_n_per_arm(night_dir: Path, records_dir: Path, sitting: dict) -> tuple[dict[str, int], str] | None:
    """Expected cells per arm from the frozen record (``n`` is per arm; record.arm is 'a+b')."""
    candidates = [records_dir / f"{night_dir.name}.json"]
    if sitting.get("record"):
        candidates.append(Path(sitting["record"]) if Path(sitting["record"]).is_absolute() else Path.cwd() / sitting["record"])
    for c in candidates:
        rec = _json(c)
        if isinstance(rec, dict) and "n" in rec and "arm" in rec:
            return {a: rec["n"] for a in rec["arm"].split("+")}, f"record {c}"
    return None


def analyse(night_dir: Path, records_dir: Path) -> list[dict]:
    n = load_night(night_dir)
    launch = n["launch"] or {}
    sitting = (launch.get("sittings") or [{}])[0]
    meta = {
        "night": night_dir.name, "launch_status": launch.get("status", "NO launch.json (running or not started)"),
        "ended": sitting.get("ended"), "evals_head": sitting.get("evals_head"),
        "record": sitting.get("record"), "arm_sha256": launch.get("arm_sha256", {}),
        "replaced": [(r["slot"], r.get("arm"), r.get("attempt_dir"), r.get("replaced_because")) for r in n["replaced"]],
        "unslotted": {},
    }
    by_arm: dict[str, list] = {}
    exp: Counter[str] = Counter()
    spec_lines: dict[str, set] = {}
    task_of_arm: dict[str, str] = {}
    for idx, slot in sorted(n["slots"].items()):
        spec, result = slot.get("spec"), slot.get("result")
        arm = (spec or result or {}).get("arm")
        if arm is None:
            continue
        exp[arm] += 1
        if spec:
            task_of_arm[arm] = spec.get("task", "?")
            spec_lines.setdefault(arm, set()).add((spec.get("line_token_budget"), spec.get("line_turn_budget"),
                                                    spec.get("token_budget"), spec.get("turn_budget")))
        by_arm.setdefault(arm, [])
        if result:
            row = read_cell(night_dir, arm, idx, result)
            row["night"] = night_dir.name
            by_arm[arm].append(row)
    rec_n = record_n_per_arm(night_dir, records_dir, sitting)
    if rec_n:
        for arm, k in rec_n[0].items():
            by_arm.setdefault(arm, [])
            exp[arm] = k
    meta["expected_source"] = rec_n[1] if rec_n else "slot spec files only (record not found; may undercount a running night)"
    groups = []
    for arm, rows in sorted(by_arm.items()):
        slotted = {r["attempt"] for r in rows}
        arm_dir = night_dir / arm
        meta["unslotted"][arm] = sorted(c.name for c in arm_dir.iterdir() if c.is_dir() and c.name != "engine-contracts"
                                        and c.name not in slotted) if arm_dir.is_dir() else []
        groups.append({"night": night_dir.name, "arm": arm,
                       "task": task_of_arm.get(arm) or (rows[0]["task"] if rows else "?"),
                       "rows": rows, "expected": exp[arm], "finished": len(rows),
                       "lines": spec_lines.get(arm, set()), "meta": meta})
    return groups


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("nights", nargs="+", type=Path)
    ap.add_argument("--combine", action="store_true",
                    help="also print one block per task+arm over nights with the same arm digest and contract digest")
    ap.add_argument("--line-report", action="append", default=[], type=Path,
                    help="JSON written by `satyrn-evals grade-line` (read only); joins line_verdict by attempt dir")
    ap.add_argument("--records-dir", type=Path, default=Path("records"),
                    help="where frozen run records live, for the expected-n denominator (default ./records)")
    ap.add_argument("--json", action="store_true", help="dump per-cell rows as JSON instead of text")
    args = ap.parse_args(argv)
    line_report: dict[str, dict] = {}
    for p in args.line_report:
        for row in (_json(p.expanduser()) or {}).get("rows", []):
            line_report[row["attempt"]] = row
    all_groups: list[dict] = []
    seen: set[Path] = set()
    for night in args.nights:
        night = night.expanduser()
        if night.resolve() in seen:
            print(f"(duplicate night argument ignored: {night})", file=sys.stderr)
            continue
        seen.add(night.resolve())
        if not night.is_dir():
            print(f"!! not a directory (not started?): {night}", file=sys.stderr)
            continue
        all_groups += analyse(night, args.records_dir.expanduser())
    if args.json:
        print(json.dumps([{k: v for k, v in g.items() if k not in ("meta", "lines")} | {
            "rows": [{**r, "rejected": dict(r["rejected"]), "guards": dict(r["guards"])} for r in g["rows"]]}
            for g in all_groups], indent=1, default=str))
        return 0
    for g in all_groups:
        meta = g["meta"]
        notes = [f"night status: launch.json status={meta['launch_status']}, ended={meta['ended']}, "
                 f"evals_head={str(meta['evals_head'])[:9]}, record={meta['record']}"]
        if meta["launch_status"] != "complete":
            notes.append("** night is not marked complete: treat as PARTIAL **")
        notes.append(f"expected cells per arm from: {meta['expected_source']}")
        if g["lines"]:
            notes.append(f"slot specs (line_tok, line_turns, token_budget, turn_budget): {sorted(g['lines'])}")
        if meta["replaced"]:
            notes.append(f"replaced (infrastructure) slots: {meta['replaced']}")
        if meta["unslotted"].get(g["arm"]):
            notes.append(f"cell dirs in {g['arm']}/ with no finished slot (in progress, replaced or stray; excluded): "
                         f"{meta['unslotted'][g['arm']]}")
        notes.append(f"arm_sha256[{g['arm']}]={str(meta['arm_sha256'].get(g['arm']))[:12]}")
        lb = "32k/48" if g["lines"] and all(l[0] == 32000 and l[1] == 48 for l in g["lines"]) else f"(spec lines {sorted(g['lines'])}; NOT 32k/48)"
        print(group_block(f"{g['night']} / {g['task']} / {g['arm']}", g["rows"], g["expected"] or None, g["finished"],
                          notes, line_report, lb))
    if args.combine:
        keyed: dict[tuple, list[dict]] = {}
        for g in all_groups:
            cds = tuple(sorted({str(r["contract_digest"]) for r in g["rows"]}))
            keyed.setdefault((g["task"], g["arm"], g["meta"]["arm_sha256"].get(g["arm"]), cds), []).append(g)
        print("\n\n######## COMBINED (explicit --combine; same task + arm + arm digest + contract digest only) ########")
        for (task, arm, digest, _), gs in sorted(keyed.items(), key=str):
            if len(gs) < 2:
                print(f"\n(not combined: {task}/{arm} [{str(digest)[:12]}] appears in only one night: {gs[0]['night']})")
                continue
            rows = [r for g in gs for r in g["rows"]]
            notes = [f"nights: {[g['night'] for g in gs]}", f"arm_sha256[{arm}]={str(digest)[:12]}",
                     "nights not marked complete: " + str([g["night"] for g in gs if g["meta"]["launch_status"] != "complete"] or "none")]
            print(group_block(f"COMBINED {task} / {arm}", rows, sum(g["expected"] for g in gs),
                              sum(g["finished"] for g in gs), notes, line_report, "32k/48"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
