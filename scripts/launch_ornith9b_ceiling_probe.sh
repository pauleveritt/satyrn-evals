#!/usr/bin/env bash
# Ornith 9B ceiling probe launcher. Serial, one cell at a time.
# Repeat limit off. Baseline only. 2h wall-clock stop from the first cell.
# Twelve cells: A1 B1 C1 A2 B2 C2 A3 B3 C3 A4 B4 C4.
# See docs/current/ornith-9b-ceiling-probe-pre-run-record.md and
# docs/current/ornith-9b-ceiling-probe-brief.md. Adapted from the retained
# ~/satyrn-smokes/2026-09-13-ornith9b-pathology-probe/launch.sh with the
# three blocks substituted (depth-3 R1, depth-2 R1, complaint-lifecycle) and
# a third block inserted into the cell order.
#
# Controller runs this. It is not run as part of preparing the pre-run
# record.
set -uo pipefail

ROOT="$HOME/satyrn-smokes/2026-09-14-ornith9b-ceiling-probe"
WT="/Users/pauleveritt/projects/pauleveritt/satyrn-evals/.claude/worktrees/ornith-ceiling-probe"
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

def A(out):
    return ["uv","run","satyrn-evals","run","agentclinic-repair-depth-3",
            "--n","1","--rung","R1","--output",out,"--timeout","900","--attempt-timeout","1200",
            "--","satyrn-evals-attempt-pi","--model","omlx/Ornith-1.5-9B-MLX-8bit",
            "--tools","read,bash,edit,write"]

def B(out):
    return ["uv","run","satyrn-evals","run","agentclinic-repair-depth-2",
            "--n","1","--rung","R1","--output",out,"--timeout","900","--attempt-timeout","1200",
            "--","satyrn-evals-attempt-pi","--model","omlx/Ornith-1.5-9B-MLX-8bit",
            "--tools","read,bash,edit,write"]

def C(out):
    return ["uv","run","satyrn-evals","session","agentclinic-complaint-lifecycle",
            "--output",out,"--step-timeout","600",
            "--","satyrn-evals-session-pi","--provider","omlx","--model","Ornith-1.5-9B-MLX-8bit",
            "--tools","read,bash,edit,write"]

order = [
 ("cell-01-A1","A","agentclinic-repair-depth-3","R1"),
 ("cell-02-B1","B","agentclinic-repair-depth-2","R1"),
 ("cell-03-C1","C","agentclinic-complaint-lifecycle",None),
 ("cell-04-A2","A","agentclinic-repair-depth-3","R1"),
 ("cell-05-B2","B","agentclinic-repair-depth-2","R1"),
 ("cell-06-C2","C","agentclinic-complaint-lifecycle",None),
 ("cell-07-A3","A","agentclinic-repair-depth-3","R1"),
 ("cell-08-B3","B","agentclinic-repair-depth-2","R1"),
 ("cell-09-C3","C","agentclinic-complaint-lifecycle",None),
 ("cell-10-A4","A","agentclinic-repair-depth-3","R1"),
 ("cell-11-B4","B","agentclinic-repair-depth-2","R1"),
 ("cell-12-C4","C","agentclinic-complaint-lifecycle",None),
]

BUILD = {"A": A, "B": B, "C": C}

cells=[]
for i,(cell,block,task,rung) in enumerate(order):
    d=os.path.join(root,cell)
    cmd=BUILD[block](d)
    cells.append({"index":i,"cell":cell,"block":block,"task":task,"rung":rung,
                  "dir":d,"arm":"baseline","model":"omlx/Ornith-1.5-9B-MLX-8bit",
                  "repeat_limit":"off","command":cmd})

sched={"version":1,
       "created_at":datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
       "task_family":"ornith9b-ceiling-probe","arm":"baseline",
       "model":"omlx/Ornith-1.5-9B-MLX-8bit","server_model":"Ornith-1.5-9B-MLX-8bit",
       "repeat_limit":"off","wall_clock_stop_seconds":7200,"worktree":wt,
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
for i in 0 1 2 3 4 5 6 7 8 9 10 11; do
  CELL=$(python3 -c "import json;print(json.load(open('$ROOT/schedule.json'))['cells'][$i]['cell'])")
  DIR=$(python3 -c "import json;print(json.load(open('$ROOT/schedule.json'))['cells'][$i]['dir'])")
  CMD=()
  while IFS= read -r p; do CMD+=("$p"); done < <(python3 -c "import json;[print(p) for p in json.load(open('$ROOT/schedule.json'))['cells'][$i]['command']]")

  if [ -z "$START_EPOCH" ]; then
    START_EPOCH=$(date +%s)
    DEADLINE=$((START_EPOCH + 7200))
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) first cell; 2h wall-clock deadline epoch=$DEADLINE" | tee -a "$LOG"
  fi

  NOW=$(date +%s)
  if [ "$NOW" -ge "$DEADLINE" ]; then
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $CELL: NOT-RUN (2h wall-clock stop reached)" | tee -a "$LOG"
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

  if [ "$RC" -eq 127 ]; then
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) INFRASTRUCTURE STOP: command not found (exit 127) at $CELL" | tee -a "$LOG"
    exit 3
  fi
done

echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) launcher COMPLETE" | tee -a "$LOG"
