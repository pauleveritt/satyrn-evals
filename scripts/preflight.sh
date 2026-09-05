#!/usr/bin/env bash
# Preflight for a V11b two-arm batch: assert every pin, prove the model
# answers, record what is about to run, and write the realized arm order
# before the first cell.
#
# Instrument, not production code. It is deliberately loud and it stops on
# the first failure: a preflight that keeps going is a preflight that
# cannot fail, and the harvest index records exactly that instrument defect
# ("a preflight that could not fail").
#
# WHY A LIVE COMPLETION AND NEVER `/v1/models`
# --------------------------------------------
# On 2026-09-05 the omlx server on :8001 advertised a model,
# `gemma-4-26B-A4B-it-OptiQ-4bit`, whose weights were nowhere on the
# machine; the listing was cleared later in the same session. A listing is
# therefore not stable within one session and is not evidence that a cell
# can run. Only a completion that comes back with text proves the model is
# loadable. This check must never be "simplified" into a `/v1/models` call.
#
# Nothing here is a measurement. It runs one throwaway completion so that a
# budgeted batch does not discover a dead model on cell 1 of 24.
#
# Usage:
#   scripts/preflight.sh --engine-repo PATH --seed N --n 12 \
#       --task TASK --rung R1 --contract-digest HEX --output RUNS_ROOT \
#       [--base-url http://127.0.0.1:8001/v1]

set -euo pipefail

ENGINE_REPO=""
BASE_URL="http://127.0.0.1:8001/v1"
SEED=""
N=""
TASK=""
RUNG=""
CONTRACT_DIGEST=""
OUTPUT=""
TOKEN_FLOOR_RECORD=""

while [ $# -gt 0 ]; do
  case "$1" in
    --engine-repo) ENGINE_REPO="$2"; shift 2 ;;
    --base-url) BASE_URL="$2"; shift 2 ;;
    --seed) SEED="$2"; shift 2 ;;
    --n) N="$2"; shift 2 ;;
    --task) TASK="$2"; shift 2 ;;
    --rung) RUNG="$2"; shift 2 ;;
    --contract-digest) CONTRACT_DIGEST="$2"; shift 2 ;;
    --output) OUTPUT="$2"; shift 2 ;;
    --token-floor-record) TOKEN_FLOOR_RECORD="$2"; shift 2 ;;
    *) echo "preflight: unknown argument: $1" >&2; exit 2 ;;
  esac
done

# Written out flag by flag rather than with indirect expansion: macOS
# ships bash 3.2, where ${!var} and ${var,,} are not both available.
require() { [ -n "$2" ] || { echo "preflight: $1 is required" >&2; exit 2; }; }
require --engine-repo "$ENGINE_REPO"
require --seed "$SEED"
require --n "$N"
require --task "$TASK"
require --rung "$RUNG"
require --contract-digest "$CONTRACT_DIGEST"
require --output "$OUTPUT"
require --token-floor-record "$TOKEN_FLOOR_RECORD"

EVALS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASELINE_ARM="$EVALS_ROOT/arms/baseline.json"
ENGINE_ARM="$EVALS_ROOT/arms/engine.json"

fail() { echo "preflight FAILED: $*" >&2; exit 1; }
ok() { echo "preflight ok: $*"; }

# Every pin is read out of the committed arm files. Restating a digest here
# would create a second copy that can drift from the one the reader loads.
pin() { python3 -c '
import json, sys
data = json.load(open(sys.argv[1]))
cursor = data
for key in sys.argv[2:]:
    cursor = cursor[key]
print(cursor)
' "$@"; }

PINNED_PI="$(pin "$BASELINE_ARM" pins pi)"
PINNED_COMMIT="$(pin "$ENGINE_ARM" pins engine_commit)"
PINNED_ENGINE_TS="$(pin "$ENGINE_ARM" pins digests engine.ts)"
PINNED_MUTATOR_TS="$(pin "$ENGINE_ARM" pins digests mutator.ts)"
SERVER_MODEL="$(pin "$BASELINE_ARM" server_model)"
PI_MODEL="$(pin "$BASELINE_ARM" model)"
ENGINE_ARM_MODEL="$(pin "$ENGINE_ARM" model)"

[ "$PI_MODEL" = "$ENGINE_ARM_MODEL" ] \
  || fail "the arm files name different models: $PI_MODEL vs $ENGINE_ARM_MODEL"
ok "both arms address $PI_MODEL (server id $SERVER_MODEL)"

# --- 0. no orphaned measurement-shaped process ---------------------------
# Interactive Pi processes started by IDE integrations are legitimate and
# long-lived. Refuse only a batch-shaped Pi (--print --mode json with the
# pinned model), an Engine attempt, or a Pi descended from that Engine.
MEASUREMENT_PROCESSES="$(ps -axo pid=,ppid=,command= | \
  python3 "$EVALS_ROOT/scripts/preflight_processes.py" --model "$PI_MODEL")"
[ -z "$MEASUREMENT_PROCESSES" ] \
  || fail "measurement-shaped process already running:\n$MEASUREMENT_PROCESSES"
ok "no measurement-shaped Pi or Engine process is running"

# --- 1. the engine checkout is exactly the pinned commit, and clean -------

HEAD_SHA="$(git -C "$ENGINE_REPO" rev-parse HEAD)"
[ "$HEAD_SHA" = "$PINNED_COMMIT" ] \
  || fail "engine HEAD $HEAD_SHA is not the pinned $PINNED_COMMIT"
ok "engine HEAD is $PINNED_COMMIT"

[ -z "$(git -C "$ENGINE_REPO" status --porcelain)" ] \
  || fail "the engine working tree is dirty; the pinned commit is not what would run"
ok "engine working tree is clean"

# --- 2. the two extension sources hash to their pins ---------------------
# These are the two --extension files satyrn-engine's build_pi_command
# hands pi, which is also where the Engine arm's read,edit tool surface is
# fixed. A matching commit with an edited file is exactly the drift a
# commit pin alone cannot catch, so both are checked.

digest_of() { shasum -a 256 "$1" | awk '{print $1}'; }

ACTUAL_ENGINE_TS="$(digest_of "$ENGINE_REPO/packages/engine/engine.ts")"
[ "$ACTUAL_ENGINE_TS" = "$PINNED_ENGINE_TS" ] \
  || fail "engine.ts is $ACTUAL_ENGINE_TS, pinned $PINNED_ENGINE_TS"
ACTUAL_MUTATOR_TS="$(digest_of "$ENGINE_REPO/packages/engine/mutator.ts")"
[ "$ACTUAL_MUTATOR_TS" = "$PINNED_MUTATOR_TS" ] \
  || fail "mutator.ts is $ACTUAL_MUTATOR_TS, pinned $PINNED_MUTATOR_TS"
ok "engine.ts and mutator.ts match their pinned sha256 digests"

# --- 3. pi is the pinned version -----------------------------------------

ACTUAL_PI="$(pi --version | tr -d '[:space:]')"
[ "$ACTUAL_PI" = "$PINNED_PI" ] || fail "pi is $ACTUAL_PI, pinned $PINNED_PI"
ok "pi is $PINNED_PI"

# --- 4. a live one-word completion (never /v1/models) --------------------

COMPLETION_BODY="$(python3 -c '
import json, sys
print(json.dumps({
    "model": sys.argv[1],
    "messages": [{"role": "user", "content": "Reply with exactly: OK"}],
    "max_tokens": 8,
    "temperature": 0,
}))
' "$SERVER_MODEL")"

RESPONSE="$(curl -sS --fail-with-body --max-time 120 \
  -H 'Content-Type: application/json' \
  -d "$COMPLETION_BODY" \
  "$BASE_URL/chat/completions")" || fail "the completion request itself failed"

MODEL_REPLY="$(printf '%s' "$RESPONSE" | python3 -c '
import json, sys
data = json.load(sys.stdin)
choices = data.get("choices") or []
print((choices[0]["message"]["content"] if choices else "").strip())
')"
[ -n "$MODEL_REPLY" ] || fail "the model returned no text; a listed model is not a loadable one"
ok "live completion returned text from $SERVER_MODEL: ${MODEL_REPLY:0:40}"

# --- 4b. a measured per-cell input-token floor must already exist --------
#
# Confirmed amendment 2026-09-05 (V11b spec §9). The floor must be measured
# *inside a materialized workspace*, and preflight runs before any workspace
# exists -- so preflight cannot measure it, only insist it was measured. The
# number comes from a V5d smoke's preserved transcript via
# scripts/token_floor.py, which refuses rather than reporting a zero.
#
# It is required here because it is the input to the Envelope cap decision,
# and the repo-root figures it replaces were wrong in the direction that
# inflates a cap: ~93% of a repo-root pi call was context-file discovery.

[ -n "$TOKEN_FLOOR_RECORD" ] \
  || fail "no --token-floor-record given; a budgeted batch needs a floor measured inside a materialized workspace (scripts/token_floor.py against a smoke transcript)"
[ -f "$TOKEN_FLOOR_RECORD" ] \
  || fail "token-floor record not found: $TOKEN_FLOOR_RECORD"
FLOOR="$(python3 -c '
import json, sys
data = json.load(open(sys.argv[1]))
value = data.get("input_token_floor")
if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
    raise SystemExit("token-floor record carries no positive input_token_floor")
print(value)
' "$TOKEN_FLOOR_RECORD")" || fail "the token-floor record is unusable; re-run scripts/token_floor.py"
ok "per-cell input-token floor on record: $FLOOR (from $TOKEN_FLOOR_RECORD)"

# --- 5. record what is about to run --------------------------------------

EVALS_SHA="$(git -C "$EVALS_ROOT" rev-parse HEAD)"
[ -z "$(git -C "$EVALS_ROOT" status --porcelain)" ] \
  || fail "the evals working tree is dirty; the batch would not be reproducible from $EVALS_SHA"
ok "evals is $EVALS_SHA with a clean working tree"

# --- 6. write the realized arm order, before any cell runs ---------------

# interleave.py imports satyrn_evals.arms, so it needs this project's
# interpreter (Python >= 3.14), not whatever python3 is on PATH.
uv run --project "$EVALS_ROOT" python "$EVALS_ROOT/scripts/interleave.py" \
  --seed "$SEED" --n "$N" --task "$TASK" --rung "$RUNG" \
  --contract-digest "$CONTRACT_DIGEST" --output "$OUTPUT" \
  "$BASELINE_ARM" "$ENGINE_ARM"

cat > "$OUTPUT/preflight.json" <<JSON
{
  "evals_commit": "$EVALS_SHA",
  "engine_commit": "$HEAD_SHA",
  "engine_digests": {
    "engine.ts": "$ACTUAL_ENGINE_TS",
    "mutator.ts": "$ACTUAL_MUTATOR_TS"
  },
  "pi": "$ACTUAL_PI",
  "model": "$PI_MODEL",
  "server_model": "$SERVER_MODEL",
  "base_url": "$BASE_URL",
  "completion_returned_text": true
}
JSON

ok "preflight complete; schedule and preflight record written under $OUTPUT"
