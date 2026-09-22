#!/usr/bin/env python3
"""Reconstruct the worktree state of BUDGET_EXCEEDED cells from their
transcripts and grade every mutation snapshot offline against the hidden
suite (no model inference; nothing under /Users/Shared is touched).

Replays, in transcript order and only where the tool result was not an
error: `write` (full content), `edit` (exact-text replacement, first
occurrence; Pi and the Engine both require the anchor to exist), and the
few bash commands that only write files (`cat >`/`cat >>` heredocs, `sed
-i`, `printf ... >`), executed in the scratch copy with the worktree `cd`
prefix stripped. Everything else (uv run, pytest, ls, grep) is skipped.

After each turn that mutated the tree, `git add -A && git diff --cached`
restricted to the task's source_paths (PROVENANCE.md dropped, as grading
does) is written to snapshots/<cell>/turn-NN.patch and graded with
`satyrn-evals grade`. Output: recon.json and recon.md.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

RUNS = Path.home() / "satyrn-runs"
EVALS = Path(__file__).resolve().parents[2]  # the evals checkout; the review scratch used an absolute path
TASKS = EVALS / "src/satyrn_evals/tasks"
OUT = Path(__file__).resolve().parent
WORK = OUT / "recon"

CELLS = {
    "selfhost-run-record-gate": [
        ("2026-09-14-admission-selfhost-run-record-gate", "baseline"),
        ("2026-09-15-admission-selfhost-run-record-gate", "baseline"),
        ("2026-09-15-route-proof-selfhost-run-record-gate", "engine"),
    ],
    "selfhost-docs-linter": [
        ("2026-09-15-admission-selfhost-docs-linter", "baseline"),
        ("2026-09-15-route-proof-selfhost-docs-linter", "engine"),
    ],
    "selfhost-guard-prefixes": [("2026-09-15-admission-selfhost-guard-prefixes", "baseline")],
    "selfhost-review-script": [("2026-09-15-admission-selfhost-review-script", "baseline")],
    "agentclinic-repair-depth-2": [("2026-09-14-admission-agentclinic-repair-depth-2", "baseline")],
    "agentclinic-repair-depth-3": [
        ("2026-09-14-admission-agentclinic-repair-depth-3", "baseline"),
        ("2026-09-15-route-proof-agentclinic-repair-depth-3", "engine"),
        ("2026-09-15-route-proof-b-agentclinic-repair-depth-3", "engine"),
    ],
}

SAFE_BASH = re.compile(r"^\s*(cat\s*>>?\s*\S+\s*<<|sed\s+-i|printf\s[^|&;]*(?<![0-9&])>\s*\S+$|echo\s[^|&;]*(?<![0-9&])>\s*\S+$)")
CD_PREFIX = re.compile(r"^\s*cd\s+(\"[^\"]*\"|'[^']*'|\S+)\s*(;|&&)\s*")


def events(path: Path):
    with path.open() as f:
        for line in f:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def rel(path: str) -> str | None:
    if not path:
        return None
    if "/worktree/" in path:
        return path.split("/worktree/", 1)[1]
    if path.startswith("/"):
        return None  # outside the tree (e.g. /tmp)
    return path


def git(work: Path, *args) -> str:
    return subprocess.run(["git", *args], cwd=work, capture_output=True, text=True).stdout


def grade(task: str, patch: Path, receipt: Path) -> dict:
    r = subprocess.run(
        ["uv", "run", "--project", os.fspath(EVALS), "satyrn-evals", "grade", task, os.fspath(patch), "--receipt", os.fspath(receipt)],
        cwd=OUT, capture_output=True, text=True, timeout=600,
    )
    try:
        rc = json.loads(receipt.read_text())
        return {"verdict": rc.get("verdict"), "counts": rc.get("evidence", {}).get("counts"), "failed": [k for k, v in rc.get("evidence", {}).get("outcomes", {}).items() if v != "passed"]}
    except Exception:
        return {"verdict": "unavailable", "stderr": r.stderr[-400:]}


def snapshot(work: Path, source_paths: list[str], dest: Path, extra: list[str] = ()) -> int:
    git(work, "add", "-A")
    diff = subprocess.run(["git", "diff", "--cached", "--binary", "HEAD", "--", *source_paths, *extra], cwd=work, capture_output=True, text=True).stdout
    dest.write_text(diff)
    return sum(1 for l in diff.splitlines() if l.startswith(("+", "-")) and not l.startswith(("+++", "---")))


def grade_noallow(task: str, patch: Path, receipt: Path) -> dict:
    """Grade with the source_paths allowlist off (what a task whose allowlist named errors.py would score)."""
    code = (
        "import sys, json; from pathlib import Path; from satyrn_evals.grade import grade; from satyrn_evals.manifest import resolve_task\n"
        "from satyrn_evals.manifest import DEFAULT_TASKS_ROOT\n"
        "r = grade(resolve_task(sys.argv[1], tasks_root=Path(DEFAULT_TASKS_ROOT)), Path(sys.argv[2]), Path(sys.argv[3]), enforce_allowlist=False)\n"
    )
    subprocess.run(["uv", "run", "--project", os.fspath(EVALS), "python", "-c", code, task, os.fspath(patch), os.fspath(receipt)], cwd=OUT, capture_output=True, text=True, timeout=600)
    try:
        rc = json.loads(receipt.read_text())
        return {"verdict": rc.get("verdict"), "counts": rc.get("evidence", {}).get("counts")}
    except Exception:
        return {"verdict": "unavailable", "counts": None}


def replay(task: str, run: str, arm: str, cell: Path, manifest: dict) -> dict:
    work = WORK / cell.name
    if work.exists():
        shutil.rmtree(work)
    shutil.copytree(TASKS / task / "base", work, symlinks=True)
    git(work, "init", "-q")
    git(work, "add", "-A")
    subprocess.run(["git", "-c", "user.email=r@x", "-c", "user.name=r", "commit", "-q", "-m", "base"], cwd=work, capture_output=True)
    snaps = OUT / "snapshots" / cell.name
    snaps.mkdir(parents=True, exist_ok=True)
    source_paths = manifest["source_paths"]

    calls = {}
    turn = 0
    mutated_this_turn = False
    log = []
    snapshots = []
    applied = {"write": 0, "edit": 0, "bash": 0}
    green_turns = []  # turns whose own test run reported green
    out_tokens = 0
    tokens_at_turn = {}
    skipped = {"write": 0, "edit": 0, "bash_unsafe": 0, "anchor_miss": 0, "err": 0}

    def flush():
        nonlocal mutated_this_turn
        if mutated_this_turn:
            p = snaps / f"turn-{turn:02d}.patch"
            n = snapshot(work, source_paths, p)
            entry = {"turn": turn, "patch": os.fspath(p), "patch_lines": n, "tokens": tokens_at_turn.get(turn, out_tokens)}
            if task == "selfhost-run-record-gate":
                p2 = snaps / f"turn-{turn:02d}.witherrors.patch"
                snapshot(work, source_paths, p2, ["src/satyrn_evals/errors.py"])
                entry["patch_witherrors"] = os.fspath(p2)
            snapshots.append(entry)
            mutated_this_turn = False

    for e in events(cell / "transcript.txt"):
        t = e.get("type")
        if t == "turn_start":
            flush()
            turn += 1
        elif t == "message_end":
            m = e["message"]
            if m["role"] == "assistant":
                out_tokens += (m.get("usage", {}) or {}).get("output", 0) or 0
                tokens_at_turn[turn] = out_tokens
                for c in m.get("content", []):
                    if c.get("type") == "toolCall":
                        calls[c["id"]] = c
            elif m["role"] == "toolResult":
                c = calls.get(m.get("toolCallId"))
                if not c:
                    continue
                name, args = c["name"], c.get("arguments", {})
                body = "".join(x.get("text", "") for x in m.get("content", []) if x.get("type") == "text")
                is_test = name == "self_test" or (name == "bash" and re.search(r"\bpytest\b", args.get("command", "")) and not re.search(r"grep|cat |sed ", args.get("command", "").split("|")[0]))
                if is_test and re.search(r"\b\d+ passed\b", body) and not re.search(r"\b\d+ (failed|error)s?\b|Traceback|ERROR", body):
                    green_turns.append(turn)
                if m.get("isError"):
                    skipped["err"] += 1
                    continue
                if name == "write":
                    p = rel(args.get("path", ""))
                    if p is None:
                        skipped["write"] += 1
                        continue
                    fp = work / p
                    fp.parent.mkdir(parents=True, exist_ok=True)
                    fp.write_text(args.get("content", ""))
                    applied["write"] += 1
                    mutated_this_turn = True
                elif name == "edit":
                    p = rel(args.get("path", ""))
                    if p is None or not (work / p).exists():
                        skipped["edit"] += 1
                        continue
                    text = (work / p).read_text()
                    ok = True
                    edits = args.get("edits") or ([{"oldText": args.get("oldText", ""), "newText": args.get("newText", "")}] if args.get("oldText") else [])
                    for ed in edits:
                        old, new = ed.get("oldText", ""), ed.get("newText", "")
                        if old and old in text:
                            text = text.replace(old, new, 1)
                        else:
                            ok = False
                            skipped["anchor_miss"] += 1
                            log.append(f"turn {turn}: edit anchor miss in {p} (tool said ok: {body[:60]!r})")
                    (work / p).write_text(text)
                    if ok:
                        applied["edit"] += 1
                    mutated_this_turn = True
                elif name == "bash":
                    cmd = args.get("command", "")
                    stripped = CD_PREFIX.sub("", cmd)
                    if SAFE_BASH.match(stripped) and "/tmp" not in stripped.split("<<")[0]:
                        try:
                            subprocess.run(stripped, shell=True, cwd=work, capture_output=True, timeout=10, env={"PATH": os.environ["PATH"]})
                            applied["bash"] += 1
                            mutated_this_turn = True
                        except Exception as exc:
                            log.append(f"turn {turn}: bash write failed: {exc}")
                    elif re.search(r"(cat\s*>|sed -i|tee\s)", cmd) and "/tmp" not in cmd:
                        skipped["bash_unsafe"] += 1
                        log.append(f"turn {turn}: skipped bash mutation: {cmd[:100]!r}")
    flush()

    # grade every snapshot
    for s in snapshots:
        rcpt = Path(s["patch"]).with_suffix(".receipt.json")
        s.update(grade(task, Path(s["patch"]), rcpt))
        if "patch_witherrors" in s:
            r2 = grade_noallow(task, Path(s["patch_witherrors"]), Path(s["patch_witherrors"]).with_suffix(".receipt.json"))
            s["verdict_witherrors"] = r2["verdict"]; s["counts_witherrors"] = r2["counts"]
    first_green = green_turns[0] if green_turns else None
    def hidden_at(t):
        prior = [x for x in snapshots if x["turn"] <= t]
        return (prior[-1].get("verdict"), (prior[-1].get("counts") or {}).get("passed")) if prior else None
    first_pass_witherrors = next((s["turn"] for s in snapshots if s.get("verdict_witherrors") == "pass"), None)
    final = snapshots[-1] if snapshots else None
    first_pass = next((s["turn"] for s in snapshots if s.get("verdict") == "pass"), None)
    best = max((s.get("counts", {}) or {}).get("passed", 0) for s in snapshots) if snapshots else 0
    return {
        "task": task, "run": run, "arm": arm, "cell": cell.name, "turns": turn,
        "applied": applied, "skipped": skipped,
        "final_verdict": final and final.get("verdict"), "final_counts": final and final.get("counts"),
        "final_failed": final and final.get("failed"),
        "first_pass_turn": first_pass, "best_passed": best,
        "first_pass_turn_witherrors": first_pass_witherrors,
        "tokens_at_first_pass": next((s["tokens"] for s in snapshots if s.get("verdict") == "pass"), None),
        "green_turns": green_turns, "first_green_turn": first_green,
        "hidden_at_first_green": hidden_at(first_green) if first_green else None,
        "hidden_at_each_green": [(g, hidden_at(g)) for g in green_turns],
        "total_tokens": out_tokens,
        "snapshots": [{k: v for k, v in s.items() if k not in ("patch", "patch_witherrors")} for s in snapshots],
        "log": log,
    }


def main():
    only = sys.argv[1:] or list(CELLS)
    results = []
    for task in only:
        manifest = json.loads((TASKS / task / "manifest.json").read_text())
        for run, arm in CELLS[task]:
            for cell in sorted((RUNS / run / arm).iterdir()):
                if not cell.is_dir() or cell.name == "engine-contracts" or not (cell / "transcript.txt").exists():
                    continue
                attempt = json.loads((cell / "attempt.json").read_text()) if (cell / "attempt.json").exists() else {}
                r = replay(task, run, arm, cell, manifest)
                r["code"] = attempt.get("code")
                r["graded_verdict"] = attempt.get("verdict")
                results.append(r)
                print(f"{run} {arm} {cell.name[-6:]} code={r['code']} turns={r['turns']} applied={r['applied']} skipped={r['skipped']} final={r['final_verdict']} {r['final_counts']} first_pass_turn={r['first_pass_turn']} (with errors.py: {r['first_pass_turn_witherrors']}) best={r['best_passed']} first_green={r['first_green_turn']} hidden@green={r['hidden_at_first_green']} greens={r['hidden_at_each_green'][:6]}", flush=True)
                for l in r["log"]:
                    print("   ", l)
    (OUT / "recon.json").write_text(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
