#!/usr/bin/env bash
# Self-hosted headroom probe launcher. Serial, one cell at a time.
# Repeat limit off. Baseline only. 3h wall-clock stop from the first cell.
# Twelve cells: G1 R1 D1 G2 R2 D2 G3 R3 D3 G4 R4 D4 (guard, run-record,
# docs-linter). See docs/current/selfhost-headroom-probe-pre-run-record.md
# and docs/current/selfhost-headroom-probe-brief.md. Adapted from the
# retained ~/satyrn-smokes/2026-09-14-ornith9b-ceiling-probe/launch.sh with
# the three tasks substituted (selfhost-guard-prefixes,
# selfhost-run-record-gate, selfhost-docs-linter, all at R1) and the
# 900s/1200s budgets widened to 1200s/1500s per the pre-run record.
#
# FIX ROUND (see the pre-run record, "Task qualification"): all three tasks
# qualify in both directions as of this round. selfhost-run-record-gate
# initially did not (its oracle's default PYTHONPATH shim shadowed the
# workspace's own `satyrn_evals` copy with the outer, real package); its
# manifest.json now sets `oracle` to `env PYTHONPATH=src python -m pytest
# -p satyrn_evals.oracle_hook`, which replaces rather than prepends
# PYTHONPATH for that one task so the workspace's own package resolves.
# The allowlist (`source_paths` excludes oracle_hook.py) still refuses any
# patch that touches the oracle plugin before the oracle ever runs, so
# this does not reopen the forgery vector the brief's hazard section warns
# about. The controller confirmed all twelve cells (n=12) stand.
#
# Controller runs this. It is not run as part of preparing the pre-run
# record.
set -uo pipefail

ROOT="$HOME/satyrn-smokes/2026-09-14-selfhost-headroom-probe"
WT="/Users/pauleveritt/projects/pauleveritt/satyrn-evals/.claude/worktrees/selfhost-headroom-probe"
SERVER_MODEL="Ornith-1.5-9B-MLX-8bit"
LOG="$ROOT/run.log"

# --- 0) refuse to start if the output root already exists ---
if [ -e "$ROOT" ]; then
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) refusing to start: output root already exists: $ROOT" >&2
  exit 1
fi

mkdir -p "$ROOT"
cp "$0" "$ROOT/launch.sh" 2>/dev/null || true

echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) launcher start; root=$ROOT" | tee -a "$LOG"

# --- 1) schedule.json FIRST, before any cell ---
python3 - "$ROOT" "$WT" <<'PY'
import json, sys, datetime, os
root, wt = sys.argv[1], sys.argv[2]

def CMD(task, out):
    return ["uv","run","satyrn-evals","run",task,
            "--n","1","--rung","R1","--output",out,"--timeout","1200","--attempt-timeout","1500",
            "--","satyrn-evals-attempt-pi","--model","omlx/Ornith-1.5-9B-MLX-8bit",
            "--tools","read,bash,edit,write"]

order = [
 ("cell-01-G1","G","selfhost-guard-prefixes"),
 ("cell-02-R1","R","selfhost-run-record-gate"),
 ("cell-03-D1","D","selfhost-docs-linter"),
 ("cell-04-G2","G","selfhost-guard-prefixes"),
 ("cell-05-R2","R","selfhost-run-record-gate"),
 ("cell-06-D2","D","selfhost-docs-linter"),
 ("cell-07-G3","G","selfhost-guard-prefixes"),
 ("cell-08-R3","R","selfhost-run-record-gate"),
 ("cell-09-D3","D","selfhost-docs-linter"),
 ("cell-10-G4","G","selfhost-guard-prefixes"),
 ("cell-11-R4","R","selfhost-run-record-gate"),
 ("cell-12-D4","D","selfhost-docs-linter"),
]

cells=[]
for i,(cell,block,task) in enumerate(order):
    d=os.path.join(root,cell)
    cmd=CMD(task,d)
    cells.append({"index":i,"cell":cell,"block":block,"task":task,"rung":"R1",
                  "dir":d,"arm":"baseline","model":"omlx/Ornith-1.5-9B-MLX-8bit",
                  "repeat_limit":"off","command":cmd})

sched={"version":1,
       "created_at":datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
       "task_family":"selfhost-headroom-probe","arm":"baseline",
       "model":"omlx/Ornith-1.5-9B-MLX-8bit","server_model":"Ornith-1.5-9B-MLX-8bit",
       "repeat_limit":"off","wall_clock_stop_seconds":10800,"worktree":wt,
       "output_root":root,"cells":cells}
with open(os.path.join(root,"schedule.json"),"w") as fh:
    json.dump(sched, fh, indent=2); fh.write("\n")
print("schedule.json written:", len(cells), "cells")
PY

[ -s "$ROOT/schedule.json" ] || { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) INFRASTRUCTURE STOP: schedule.json not written" | tee -a "$LOG"; exit 3; }

[ -d "$WT" ] || { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) INFRASTRUCTURE STOP: worktree $WT missing" | tee -a "$LOG"; exit 3; }

# --- 2) model loadability: one live completion, never /v1/models ---
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) model loadability check" | tee -a "$LOG"
LOAD_RESP=$(curl -sS --max-time 180 http://127.0.0.1:8001/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d "{\"model\":\"$SERVER_MODEL\",\"max_tokens\":8,\"messages\":[{\"role\":\"user\",\"content\":\"Reply with OK\"}]}" 2>&1)
LOAD_RC=$?
OBS=$(printf '%s' "$LOAD_RESP" | python3 -c 'import sys,json
try:
    d=json.load(sys.stdin); print(d.get("model",""))
except Exception:
    print("")')
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) loadability rc=$LOAD_RC observed_model='$OBS'" | tee -a "$LOG"
if [ "$LOAD_RC" -ne 0 ] || [ "$OBS" != "$SERVER_MODEL" ]; then
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) INFRASTRUCTURE STOP: model not loadable (observed '$OBS', rc=$LOAD_RC)" | tee -a "$LOG"
  exit 3
fi

# --- 3) run the twelve cells serially ---
START_EPOCH=""
DEADLINE=0
RAN_ANY=0
for i in 0 1 2 3 4 5 6 7 8 9 10 11; do
  CELL=$(python3 -c "import json;print(json.load(open('$ROOT/schedule.json'))['cells'][$i]['cell'])")
  DIR=$(python3 -c "import json;print(json.load(open('$ROOT/schedule.json'))['cells'][$i]['dir'])")
  CMD=()
  while IFS= read -r p; do CMD+=("$p"); done < <(python3 -c "import json;[print(p) for p in json.load(open('$ROOT/schedule.json'))['cells'][$i]['command']]")

  # A truncated/empty argv would otherwise silently "succeed" at running
  # nothing (`"${CMD[@]}"` with zero elements is a no-op that exits 0), and
  # the per-cell log would then read "done exit=0 duration=0s" for a cell
  # that never invoked satyrn-evals. Refuse to proceed on that shape.
  if [ "${#CMD[@]}" -lt 3 ]; then
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) INFRASTRUCTURE STOP: $CELL command argv extracted short (${#CMD[@]} elements): ${CMD[*]-}" | tee -a "$LOG"
    exit 3
  fi

  if [ -z "$START_EPOCH" ]; then
    START_EPOCH=$(date +%s)
    DEADLINE=$((START_EPOCH + 10800))
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) first cell; 3h wall-clock deadline epoch=$DEADLINE" | tee -a "$LOG"
  fi

  NOW=$(date +%s)
  if [ "$NOW" -ge "$DEADLINE" ]; then
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $CELL: NOT-RUN (3h wall-clock stop reached)" | tee -a "$LOG"
    continue
  fi
  if [ -e "$DIR" ] && [ -n "$(ls -A "$DIR" 2>/dev/null)" ]; then
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $CELL: NOT-RUN (dir already non-empty; refusing to overwrite)" | tee -a "$LOG"
    continue
  fi

  mkdir -p "$DIR"
  START_TS=$(date -u +%Y-%m-%dT%H:%M:%SZ); START_S=$(date +%s)
  echo "$START_TS $CELL: start" | tee -a "$LOG"
  ( cd "$WT" && "${CMD[@]}" ) > "$ROOT/$CELL.stdout.log" 2>&1
  RC=$?
  END_TS=$(date -u +%Y-%m-%dT%H:%M:%SZ); END_S=$(date +%s)
  echo "$END_TS $CELL: done exit=$RC duration=$((END_S-START_S))s" | tee -a "$LOG"
  RAN_ANY=1

  if [ "$RC" -eq 127 ]; then
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) INFRASTRUCTURE STOP: command not found (exit 127) at $CELL" | tee -a "$LOG"
    exit 3
  fi
done

if [ "$RAN_ANY" -eq 1 ]; then
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) launcher COMPLETE" | tee -a "$LOG"
else
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) launcher COMPLETE, all cells NOT-RUN" | tee -a "$LOG"
fi
