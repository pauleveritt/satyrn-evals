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
ARMS=""

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
    --arms) ARMS="$2"; shift 2 ;;
    *) echo "preflight: unknown argument: $1" >&2; exit 2 ;;
  esac
done

# Written out flag by flag rather than with indirect expansion: macOS
# ships bash 3.2, where ${!var} and ${var,,} are not both available.
require() { [ -n "$2" ] || { echo "preflight: $1 is required" >&2; exit 2; }; }
require --seed "$SEED"
require --n "$N"
require --task "$TASK"
require --rung "$RUNG"
require --contract-digest "$CONTRACT_DIGEST"
require --output "$OUTPUT"
require --token-floor-record "$TOKEN_FLOOR_RECORD"

EVALS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# --arms takes a comma-separated list of arm files, defaulting to the
# two-arm batch this script was written for. A batch that runs one arm
# must be gated on that arm: checking an arm the batch is not running
# would refuse on settings nothing depends on, and -- worse -- pass on an
# arm nobody checked.
if [ -z "$ARMS" ]; then
  ARM_FILES=("$EVALS_ROOT/arms/baseline.json" "$EVALS_ROOT/arms/engine.json")
else
  ARM_FILES=()
  # bash 3.2: no readarray, so split on commas the portable way.
  while IFS= read -r arm_entry; do
    case "$arm_entry" in
      /*) ARM_FILES+=("$arm_entry") ;;
      *) ARM_FILES+=("$EVALS_ROOT/$arm_entry") ;;
    esac
  done <<< "$(printf '%s' "$ARMS" | tr ',' '\n')"
fi
for arm_file in "${ARM_FILES[@]}"; do
  [ -f "$arm_file" ] || { echo "preflight: no such arm file: $arm_file" >&2; exit 2; }
done
BASELINE_ARM="${ARM_FILES[0]}"

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

# The engine pin checks apply only when an arm in *this* batch actually
# runs the engine. A Baseline-only batch pins no commit, and checking one
# anyway would compare against a null and refuse on a condition nothing in
# the batch depends on. The skip is announced, never silent: "a preflight
# that could not fail" is a recorded instrument defect.
ENGINE_PINNING_ARM=""
for arm_file in "${ARM_FILES[@]}"; do
  if [ "$(pin "$arm_file" pins engine_commit)" != "None" ]; then
    ENGINE_PINNING_ARM="$arm_file"
  fi
done
# A first-vs-last comparison of two arms silently skips a third, middle
# arm -- exactly the "pass on an arm nobody checked" defect this script's
# PATH-resolution comment (below) already warns about. preflight_models.py
# checks every arm named on the command line, not just the ends.
uv run --project "$EVALS_ROOT" python \
  "$EVALS_ROOT/scripts/preflight_models.py" "${ARM_FILES[@]}" \
  || fail "the arm files do not all name the same model"

# --- 0a. each arm's declared inference settings are actually enforced ----
# An arm's `inference` block was a claim nobody checked: the served id can
# be absent from the oMLX server's model_settings.json -- the config that
# actually governs sampling -- while pi's models.json agrees, which is
# exactly what made the gap invisible. Checked per arm, not just the
# baseline: each arm can name a different served model. `--record` writes
# the provenance block (arm/entry digests) next to preflight.json, one file
# per arm, so the frozen precondition names what was compared and not only
# that it was; $OUTPUT does not exist yet at this point in the script (only
# interleave.py, in step 6 below, creates it), so it is made here.
mkdir -p "$OUTPUT"
for arm_file in "${ARM_FILES[@]}"; do
  arm_stem="$(basename "$arm_file" .json)"
  uv run --project "$EVALS_ROOT" python \
    "$EVALS_ROOT/scripts/preflight_settings.py" "$arm_file" \
    --record "$OUTPUT/settings-$arm_stem.json" \
    || fail "$arm_file's inference settings are not verified against the server and pi config"
done

SERVER_MODEL="$(pin "$BASELINE_ARM" server_model)"
PI_MODEL="$(pin "$BASELINE_ARM" model)"
ok "all arms address $PI_MODEL (server id $SERVER_MODEL)"

# --- 0. no orphaned measurement-shaped process ---------------------------
# Interactive Pi processes started by IDE integrations are legitimate and
# long-lived. Refuse only a batch-shaped Pi (--print --mode json with the
# pinned model), an Engine attempt, or a Pi descended from that Engine.
MEASUREMENT_PROCESSES="$(ps -axo pid=,ppid=,command= | \
  python3 "$EVALS_ROOT/scripts/preflight_processes.py" --model "$PI_MODEL")"
[ -z "$MEASUREMENT_PROCESSES" ] \
  || fail "measurement-shaped process already running:\n$MEASUREMENT_PROCESSES"
ok "no measurement-shaped Pi or Engine process is running"

# --- 0b. every arm's command is findable on PATH -------------------------
# A commit and a digest prove *which* code would run; they do not prove the
# command can be found. On 2026-09-05 this script went green while
# `satyrn-engine` was absent from PATH (it lives in the engine repo's own
# virtualenv), and the Engine smoke launched from that shell died in under a
# second. A 24-cell spike would have aborted its whole Engine half.
# Run under `uv run` so the check resolves the way a cell resolves: the
# batch is launched as `uv run satyrn-evals run ...`, so its children see
# the evals virtualenv's bin directory. Checked with a bare `python3`, the
# Baseline command reads as missing when it is not.
uv run --project "$EVALS_ROOT" python \
  "$EVALS_ROOT/scripts/preflight_commands.py" "${ARM_FILES[@]}" \
  || fail "an arm's command is not on PATH; put it there before spending a batch"

# --- 0c. pi's inference settings are the ones the arms record -------------
# F6: pi declared a 262,144 context window while the server enforced
# 80,000, so compaction could never fire and seven Baseline cells of the
# V11c spike each burned ten minutes walking into that wall. The mismatch
# was recorded beforehand; what was missing was any check that the
# settings a batch depends on are the settings that are live. A setting
# changed under a batch is now a refusal, not a discovery afterwards.
# Stated limit: this compares pi's *declared* config, and cannot see what
# the server enforces -- that is the live completion's job, and the
# batch's.
uv run --project "$EVALS_ROOT" python \
  "$EVALS_ROOT/scripts/preflight_inference.py" "${ARM_FILES[@]}" \
  || fail "an inference setting drifted from what the arm records"

# --- 1. the engine checkout is exactly the pinned commit, and clean -------

if [ -z "$ENGINE_PINNING_ARM" ]; then
  HEAD_SHA=""
  ACTUAL_ENGINE_TS=""
  ACTUAL_MUTATOR_TS=""
  # A batch whose arms pin no engine never enters the else branch below, where
  # this is otherwise assigned, and `set -u` then killed the record write AFTER
  # every check had passed (2026-09-09, the first Baseline-only batch to use
  # preflight). Assigned here rather than defaulted at the point of use, so the
  # no-engine path holds a real value instead of relying on a `:-`.
  VERIFIED_DIGESTS=""
  ok "no arm in this batch pins an engine commit; engine checks not applicable"
else
PINNED_COMMIT="$(pin "$ENGINE_PINNING_ARM" pins engine_commit)"
require --engine-repo "$ENGINE_REPO"

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

# Every digest the arm records is checked, by iterating the record rather
# than naming source files here. Naming them meant that when engine E7
# added a third `--extension`, widening the arm record alone would have
# left the new file recorded but unchecked -- the same
# recorded-but-not-checked shape as the temperature gap this preflight
# already carried once. The record below emits exactly what was verified,
# so it cannot drift from the check either.
PINNED_NAMES="$(python3 -c '
import json, sys
print("\n".join(json.load(open(sys.argv[1]))["pins"]["digests"]))
' "$ENGINE_PINNING_ARM")"
[ -n "$PINNED_NAMES" ] || fail "the engine arm records no source digests"
CHECKED=0
VERIFIED_DIGESTS=""
while IFS= read -r name; do
  [ -n "$name" ] || continue
  SOURCE="$ENGINE_REPO/packages/engine/$name"
  [ -f "$SOURCE" ] || fail "pinned engine source is missing: $name"
  EXPECTED="$(pin "$ENGINE_PINNING_ARM" pins digests "$name")"
  ACTUAL="$(digest_of "$SOURCE")"
  [ "$ACTUAL" = "$EXPECTED" ] || fail "$name is $ACTUAL, pinned $EXPECTED"
  VERIFIED_DIGESTS="$VERIFIED_DIGESTS${VERIFIED_DIGESTS:+,}
    \"$name\": \"$ACTUAL\""
  CHECKED=$((CHECKED + 1))
done <<< "$PINNED_NAMES"
ok "$CHECKED pinned engine sources match their sha256 digests"
fi

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
  "${ARM_FILES[@]}"

cat > "$OUTPUT/preflight.json" <<JSON
{
  "evals_commit": "$EVALS_SHA",
  "engine_commit": "$HEAD_SHA",
  "engine_digests": {${VERIFIED_DIGESTS:-}
  },
  "pi": "$ACTUAL_PI",
  "model": "$PI_MODEL",
  "server_model": "$SERVER_MODEL",
  "base_url": "$BASE_URL",
  "completion_returned_text": true
}
JSON

ok "preflight complete; schedule and preflight record written under $OUTPUT"
