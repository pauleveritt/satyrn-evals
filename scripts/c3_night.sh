#!/bin/sh
# c3_night.sh -- one C3 sitting: three C1 census records under confinement, in order.
# Plan: docs/superpowers/plans/2026-10-03-c3-census-rerun.md. Baseline arm only.
# Usage: scripts/c3_night.sh A|B    C3_DRY_RUN=1 prints the launches and runs nothing.
# Exits with the stopping launcher code; 2 before any launch or on red gates; 5 when the
# next record would cross the 720-minute sitting. Never relaunches on 4: the next
# sitting resumes a capped or stopped record (finished slots never re-run).
set -u
TRAILER="Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
ARM=arms/baseline-ornith15-9b.json; SITTING=720; RECORD_MIN=240; START=$(date +%s)
case "${1:-}" in
  A) TASKS="selfhost-run-record-gate selfhost-docs-linter selfhost-preflight-quiet";;
  B) TASKS="agentclinic-repair-depth-3 selfhost-cell-loop selfhost-speed-probe";;
  *) echo "c3: usage: $0 A|B" >&2; exit 2;;
esac
if [ -z "${C3_DRY_RUN:-}" ]; then
  uv run python scripts/preflight_settings.py "$ARM" > /dev/null; P=$?
  [ "$P" -eq 0 ] || { echo "c3: preflight_settings exited $P for $ARM; nothing launches" >&2; exit 2; }
fi
S=0
for T in $TASKS; do
  set -- records/*-c1-"$T".json
  { [ "$#" -eq 1 ] && [ -f "$1" ]; } || { echo "c3: want one C1 record for $T, found: $*" >&2; exit 2; }
  R=$1; RES=${R%.json}.result.json
  if [ -f "$RES" ] && [ "$(uv run python -c 'import json,sys;print(json.load(open(sys.argv[1]))["status"])' "$RES")" = complete ]; then
    echo "c3: $T already complete"; continue
  fi
  USED=$(( ($(date +%s) - START) / 60 ))
  [ $((USED + RECORD_MIN)) -le "$SITTING" ] || { echo "c3: $T would cross $SITTING min (used $USED); next sitting" >&2; exit 5; }
  if [ -n "${C3_DRY_RUN:-}" ]; then echo "c3: would launch $R --arm $ARM"; continue; fi
  uv run satyrn-evals launch "$R" --arm "$ARM"; S=$?
  if [ -f "$RES" ]; then
    STATUS=$(uv run python -c 'import json,sys;print(json.load(open(sys.argv[1]))["status"])' "$RES")
    git add "$RES" && { git diff --cached --quiet || git commit -qm "C3 result: $T ($STATUS)

$TRAILER"; }
    just gates; G=$?
    [ "$G" -eq 0 ] || { echo "c3: gates exited $G after $RES; the head is red" >&2; exit 2; }
  fi
  [ "$S" -eq 0 ] || { echo "c3: $T stopped with $S; the rest wait for the next sitting" >&2; break; }
done
echo "c3 EXIT: $S"; exit "$S"
