#!/bin/sh
# census_night_2.sh -- run the 2026-09-17 census night 2, in order, from the evals checkout.
# Three records, nine cells: n = 3 replacement records for the nine cells the 2026-09-16
# night lost to a 3,000 s backstop on a shared machine. Record 1 (the third medium-build
# candidate) was withdrawn by the 2026-09-17 amendment -- section 4 of
# docs/superpowers/specs/2026-09-17-release-two-census-night-2-design.md -- so this night
# runs the three replacement records only, in order 2, 3, 4. Each record's result is
# committed before the next record launches.
# Exits with the last launcher exit code, or 2 before any launch.
set -u
TRAILER="Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
ARM=arms/baseline-ornith15-9b.json
TASKS="selfhost-run-record-gate selfhost-cell-loop selfhost-speed-probe"

# Settings provenance, both arms, as the cell user. A disagreement here means the
# oMLX entry or the cell's models.json is not at 16,000; nothing launches.
for a in arms/baseline-ornith15-9b.json arms/engine-ornith15-9b.json; do
  uv run python scripts/preflight_settings.py "$a" --cell > /dev/null || {
    echo "census2: preflight_settings failed for $a" >&2; exit 2; }
done

S=2
for T in $TASKS; do
  R="records/2026-09-17-census2-$T.json"; RES="records/2026-09-17-census2-$T.result.json"
  [ -f "$R" ] || { echo "census2: missing $R" >&2; exit 2; }
  if [ -f "$RES" ] && [ "$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["status"])' "$RES")" = "complete" ]; then
    echo "census2: $T already complete"; continue
  fi
  S=4
  while [ "$S" -eq 4 ]; do          # 4 is CAPPED: the launcher resumes the same record
    uv run satyrn-evals launch "$R" --arm "$ARM"; S=$?
  done
  if [ -f "$RES" ]; then
    STATUS=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["status"])' "$RES")
    git add "$RES" && { git diff --cached --quiet || git commit -qm "Census night 2 result: $T ($STATUS)

$TRAILER"; }
    # A result commit can move a guard (the 2026-09-18 route-proof .result.json
    # files matched the "no fourth record" glob): run the gates so a red head
    # cannot sit unnoticed.
    just gates || { echo "census2: evals gates failed after committing $RES; the head is red" >&2; exit 2; }
  fi
  [ "$S" -eq 0 ] || { echo "census2: $T stopped with $S; the remaining records are not launched" >&2; break; }
done
echo "census2 EXIT: $S"; exit "$S"
