#!/usr/bin/env python3
"""Grade the reconstructed worktree at every turn (unique trees only) for every
cell that landed a source edit. Read-only on the repo and ~/satyrn-runs; scratch
trees and grade receipts live under this directory. Two replays per cell:
  std  = the committed script's replay (write/edit/heredoc/one simple write)
  ext  = std + python heredoc bodies (`python3 - <<'X'` / `uv run python - <<'X'`)
         executed in the scratch tree when they contain a file write and none of
         a small deny-list of calls.
Also grades the allowlist-filtered patch (source_paths only) when the harness
verdict is `unavailable` for a non-source path."""
import importlib.util, json, os, re, shutil, subprocess, sys, hashlib, tempfile, posixpath
from pathlib import Path
EVALS = Path("/Users/pauleveritt/projects/pauleveritt/satyrn-evals")
SCRIPT = EVALS / "evidence/2026-09-15-finishing-counterfactual/counterfactual.py"
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("cf", SCRIPT); cf = importlib.util.module_from_spec(spec); sys.modules["cf"] = cf; spec.loader.exec_module(cf)
cf.WORK = HERE / "work"; cf.WORK.mkdir(exist_ok=True)
GRADES = HERE / "grades"; GRADES.mkdir(exist_ok=True)
assert not cf.project_markers(GRADES), cf.project_markers(GRADES)
from satyrn_evals.session_patch import RESIDUE_EXCLUDES, build_cumulative_patch


_HEREDOC_BODY = re.compile(r"<<-?\s*'?(?P<w>\w+)'?[ \t]*\n(?P<body>.*?)\n(?P=w)[ \t]*(?:\n|$)", re.S)
DENY = ("subprocess", "os.system", "rmtree", "socket", "urllib", "requests", "http", "os.remove", "os.unlink", "shutil", "os.rename", "os.replace")

def ext_replay_command(command, cwd, work, tmp):
    """Segment-wise selective replay of one bash command in the scratch tree: cd into
    the worktree (ignored), cp/mv inside the tree or to the remapped /tmp, python
    heredoc bodies (deny-listed calls refused), and sed -i. Everything else is skipped.
    Returns a list of (segment, changed files) for segments that ran."""
    text = command
    if cwd:
        text = text.replace("/private" + cwd + "/", "").replace(cwd + "/", "").replace("/private" + cwd, ".").replace(cwd, ".")
    text = text.replace("/tmp/", os.fspath(tmp) + "/")
    bodies = [m["body"] for m in _HEREDOC_BODY.finditer(text)]
    ran = []
    sd = ["."]
    env = {"PATH": os.environ["PATH"], "HOME": os.fspath(work), "TMPDIR": os.fspath(tmp), "PYTHONPATH": os.fspath(work)}
    def run(argv_or_text, shell=False, stdin=None):
        before = cf._digests(work)
        try:
            if shell: r = subprocess.run(["/bin/bash", "-c", argv_or_text], cwd=work / sd[0], capture_output=True, text=True, timeout=20, env=env)
            else: r = subprocess.run(argv_or_text, cwd=work / sd[0], capture_output=True, text=True, timeout=20, env=env, input=stdin)
            rc, err = r.returncode, r.stderr[-160:]
        except subprocess.TimeoutExpired:
            rc, err = -1, "timeout"
        after = cf._digests(work)
        changed = sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p) and "__pycache__" not in p)
        return rc, err, changed
    body_i = 0
    for seg in cf._segments(text):
        prog = seg[0]
        if prog == "cd":
            dest = seg[1] if len(seg) > 1 else "~"
            if dest in (".", "$(pwd)", "$PWD", "${PWD}") or dest == "$": continue
            rel = cf.tree_path(dest, None)
            if rel is not None and (work / rel).is_dir():
                sd[0] = rel; continue
            ran.append((seg, "abort: cd " + dest, [])); break
        if prog in ("cp", "mv") and len(seg) == 3 and all(not a.startswith("-") for a in seg[1:]):
            ok = all(cf.tree_path(posixpath.join(sd[0], a), None) is not None or a.startswith(os.fspath(tmp)) for a in seg[1:])
            if ok:
                rc, err, changed = run([prog, seg[1], seg[2]]); ran.append((seg, f"rc={rc} {err}", changed))
            continue
        is_py = (prog in ("python3", "python") and (seg[1:3] == ["-", "<<"] or seg[1:2] == ["<<"])) or (prog == "uv" and seg[1:3] == ["run", "python"] and (seg[3:5] == ["-", "<<"] or seg[3:4] == ["<<"]))
        if is_py:
            if body_i >= len(bodies): continue
            body = bodies[body_i]; body_i += 1
            if any(d in body for d in DENY): ran.append((seg[:3], "refused: deny-list", [])); continue
            rc, err, changed = run([sys.executable, "-"], stdin=body); ran.append((seg[:3], f"rc={rc} {err}", changed)); continue
        if "<<" in seg:
            body_i += 1  # a heredoc we do not run (cat > file is std's job; others skipped)
            continue
        if prog == "sed" and any(re.fullmatch(r"-[a-zA-Z0-9]*i\S*", w) or w == "--in-place" for w in seg[1:]):
            rc, err, changed = run(__import__("shlex").join(seg), shell=True); ran.append((seg[:2] + seg[-1:], f"rc={rc} {err}", changed)); continue
    return ran

_PYHEREDOC = re.compile(r"^(?:uv run )?python3? - <<'?(?P<w>\w+)'?[ \t]*\n(?P<body>.*?)\n(?P=w)[ \t]*$", re.S | re.M)
DENY = ("subprocess", "os.system", "rmtree", "socket", "urllib", "requests", "http", "os.remove", "os.unlink", "shutil")

def py_bodies(command, cwd):
    """Python heredoc bodies in a bash command that write a file, after stripping a leading cd into the worktree."""
    text = command
    if cwd:
        text = text.replace("/private" + cwd, ".").replace(cwd, ".")
    text = re.sub(r"^\s*cd\s+(?:\.|\"\$\(pwd\)\"|\$\(pwd\)|\$PWD|\"\$PWD\")\s*(?:&&|;|\n)\s*", "", text)
    out = []
    for m in _PYHEREDOC.finditer(text):
        body = m["body"]
        if re.search(r"open\([^)]*['\"][wa]['\"]|write_text\(|write_bytes\(", body) and not any(d in body for d in DENY):
            out.append(body)
    return out

def replay(spec_, steps, cwd, source_paths, stop_after_turn, ext):
    work = cf.WORK / f"{spec_.attempt}-{'ext' if ext else 'std'}"
    if work.exists(): shutil.rmtree(work)
    shutil.copytree(cf.TASKS / spec_.task / "base", work, symlinks=True)
    cf._git(work, "init", "-q"); cf._git(work, "add", "-A")
    cf._git(work, "-c", "user.email=replay@localhost", "-c", "user.name=replay", "commit", "-q", "-m", "base")
    base = cf._git(work, "rev-parse", "HEAD").strip()
    snapshots = {}  # turn -> patch text (at the end of each turn)
    ext_applied = []
    cur_turn = None
    def snap(turn):
        tempfile.tempdir = os.fspath(cf.WORK)
        snapshots[turn] = build_cumulative_patch(work, base, os.environ, exclude=RESIDUE_EXCLUDES).patch_text
    tmp = cf.WORK / "tmp"; tmp.mkdir(exist_ok=True)
    for step in steps:
        if cur_turn is not None and step.turn != cur_turn:
            snap(cur_turn)
        cur_turn = step.turn
        if step.name == "write" and not step.is_error:
            p = cf.tree_path(step.args.get("path", ""), cwd)
            if p is not None:
                t = work / p; t.parent.mkdir(parents=True, exist_ok=True); t.write_text(str(step.args.get("content", "")))
        elif step.name == "edit" and not step.is_error:
            p = cf.tree_path(step.args.get("path", ""), cwd)
            if p is None: continue
            t = work / p
            edits = step.args.get("edits") or ([{"oldText": step.args.get("oldText", ""), "newText": step.args.get("newText", "")}] if step.args.get("oldText") else [])
            text = t.read_text() if t.is_file() else None
            for e in edits:
                old, new = str(e.get("oldText", "")), str(e.get("newText", ""))
                if text is not None and old and old in text: text = text.replace(old, new, 1)
            if text is not None: t.write_text(text)
        elif step.name == "bash":
            command = str(step.args.get("command", ""))
            plan = cf.plan_bash(command, cwd)
            if plan.replay is not None:
                subprocess.run(["/bin/bash", "-c", plan.replay], cwd=work, capture_output=True, timeout=10, env={"PATH": os.environ["PATH"], "HOME": os.fspath(work), "TMPDIR": os.fspath(tmp)})
            elif ext:
                for seg, note, changed in ext_replay_command(command, cwd, work, tmp):
                    if changed or note.startswith(("abort", "refused")) or not note.startswith("rc=0"):
                        ext_applied.append(dict(turn=step.turn, seg=" ".join(seg)[:80], note=note, changed=changed))
    if cur_turn is not None: snap(cur_turn)
    shutil.rmtree(work, ignore_errors=True)
    return snapshots, ext_applied

def filter_patch(patch, source_paths):
    """Keep only file sections whose path is inside source_paths (what reconstruct.py did)."""
    out = []; keep = False
    for line in patch.splitlines(keepends=True):
        if line.startswith("diff --git "):
            path = line.split(" b/", 1)[1].strip() if " b/" in line else ""
            keep = cf.in_source_paths(path, source_paths)
        if keep: out.append(line)
    return "".join(out)

cache = {}
def grade(task, patch):
    key = hashlib.sha256((task + patch).encode()).hexdigest()
    if key in cache: return cache[key]
    folder = GRADES / key[:16]
    if (folder / "receipt.json").exists():
        rec = json.loads((folder / "receipt.json").read_text())
    else:
        if folder.exists(): shutil.rmtree(folder)
        folder.mkdir(parents=True); (folder / "patch.diff").write_text(patch)
        subprocess.run([os.fspath(Path(sys.executable).parent / "satyrn-evals"), "grade", task, "patch.diff", "--receipt", "receipt.json"], cwd=folder, capture_output=True, text=True, timeout=900, env={**os.environ, "UV_OFFLINE": "1", "TMPDIR": os.fspath(folder)})
        rec = json.loads((folder / "receipt.json").read_text())
    ev = rec.get("evidence"); 
    if isinstance(ev, str):
        try: ev = json.loads(ev)
        except Exception: ev = {}
    failed = sorted(k for k, v in (ev or {}).get("outcomes", {}).items() if v != "passed") if isinstance(ev, dict) else []
    res = dict(verdict=rec["verdict"], reason=(rec.get("reason") or "")[:160], failed=failed[:12], n_failed=len(failed))
    cache[key] = res
    return res

only = set(sys.argv[1:])
results = []
for s in (*cf.DECISION, *cf.DEBUG):
    if only and s.attempt not in only: continue
    manifest = json.loads((cf.TASKS / s.task / "manifest.json").read_text()); sp = tuple(manifest["source_paths"])
    folder = cf.cell_dir(s); attempt = json.loads((folder / "attempt.json").read_text())
    events = cf.parse_events((folder / "transcript.txt").read_text()); cwd = cf.session_cwd(events); steps = cf.steps_of(events)
    edits = cf.source_edit_indices(steps, sp, cwd, {})
    row = dict(task=s.task, group=s.group, attempt=s.attempt, code=attempt.get("code"), verdict=attempt.get("verdict"), first_edit_turn=None if not edits else steps[edits[0]].turn, turns={}, ext_applied=[])
    if edits:
        tokens_at_turn_end = {}
        for st in steps: tokens_at_turn_end[st.turn] = st.output_tokens
        for mode in ("std", "ext"):
            snaps, ext_applied = replay(s, steps, cwd, sp, None, mode == "ext")
            if mode == "ext": row["ext_applied"] = ext_applied
            prev = None
            for turn in sorted(snaps):
                if turn < row["first_edit_turn"]: continue
                patch = snaps[turn]
                digest = hashlib.sha256(patch.encode()).hexdigest()[:12]
                entry = row["turns"].setdefault(str(turn), dict(tokens=tokens_at_turn_end.get(turn)))
                g = grade(s.task, patch)
                entry[mode] = dict(digest=digest, **g)
                if g["verdict"] == "unavailable" and "non-source path" in g["reason"]:
                    entry[mode + "_filtered"] = grade(s.task, filter_patch(patch, sp))
    results.append(row)
    summary = " ".join(f"{t}:{v.get('std',{}).get('verdict','?')[0]}{('/'+v['ext']['verdict'][0]) if v.get('ext') and v['ext'].get('verdict')!=v.get('std',{}).get('verdict') else ''}{('(f:'+v['std_filtered']['verdict'][0]+')') if 'std_filtered' in v else ''}" for t, v in row["turns"].items())
    print(f"{s.task} {s.attempt} {row['code']} first_edit={row['first_edit_turn']} :: {summary}", flush=True)
    json.dump(results, open(HERE / f"trajectory{'-' + '-'.join(sorted(only)) if only else ''}.json", "w"), indent=1)
