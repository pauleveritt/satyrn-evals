#!/bin/sh
# census_night_3.sh -- run the 2026-09-18 census night 3, from the evals checkout.
# One record, six cells: the authored third medium-build task selfhost-preflight-quiet
# (docs/superpowers/specs/2026-09-17-release-two-authored-task-design.md, approved
# 2026-09-17), Baseline only, n = 6 at k = 3, 48,000 tokens / 72 turns, 4,800 s backstop,
# on a quiet machine. The result is committed when the record completes.
# Exits with the launcher exit code, or 2 before any launch.
set -u
TRAILER="Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
ARM=arms/baseline-ornith15-9b.json
TASKS="selfhost-preflight-quiet"

# Settings provenance, both arms, as the cell user. A disagreement here means the
# oMLX entry or the cell's models.json is not at 16,000; nothing launches.
for a in arms/baseline-ornith15-9b.json arms/engine-ornith15-9b.json; do
  uv run python scripts/preflight_settings.py "$a" --cell > /dev/null || {
    echo "census3: preflight_settings failed for $a" >&2; exit 2; }
done

S=2
for T in $TASKS; do
  R="records/2026-09-18-census3-$T.json"; RES="records/2026-09-18-census3-$T.result.json"
  [ -f "$R" ] || { echo "census3: missing $R" >&2; exit 2; }
  if [ -f "$RES" ] && [ "$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["status"])' "$RES")" = "complete" ]; then
    echo "census3: $T already complete"; continue
  fi
  S=4
  while [ "$S" -eq 4 ]; do          # 4 is CAPPED: the launcher resumes the same record
    uv run satyrn-evals launch "$R" --arm "$ARM"; S=$?
  done
  if [ -f "$RES" ]; then
    STATUS=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["status"])' "$RES")
    git add "$RES" && { git diff --cached --quiet || git commit -qm "Census night 3 result: $T ($STATUS)

$TRAILER"; }
    # A result commit can move a guard (the 2026-09-18 route-proof .result.json
    # files matched the "no fourth record" glob): run the gates so a red head
    # cannot sit unnoticed.
    just gates || { echo "census3: evals gates failed after committing $RES; the head is red" >&2; exit 2; }
  fi
  [ "$S" -eq 0 ] || { echo "census3: $T stopped with $S" >&2; break; }
done
echo "census3 EXIT: $S"; exit "$S"
