# The real-model session smoke

V6's layer (b): one uncounted real-model session per materially distinct
execution path, at that path's first real use. This is the V5d pre-flight
practice (`2026-09-03-v5d-preflight-smoke-check-design.md`) applied to the
session machinery; the session-specific assertions live in the V6 delta
spec's Delta 3. Manual, deliberately not automated, never a counted cell.

## The run

```bash
export SMOKE_OUTPUT="$HOME/projects/satyrn-v6-scratch/sessions/smoke-session-mechanics-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$SMOKE_OUTPUT"
uv run satyrn-evals session session-mechanics --output "$SMOKE_OUTPUT" -- \
    uv run satyrn-evals-session-pi --provider PROVIDER --model MODEL
```

`SMOKE_OUTPUT` is durable and uniquely named — never `/tmp`. Its path is
recorded with the outcome in the verification record.

## Read, always: `session-record.json`

Every session that starts writes it — adapter-error and timeout
terminations included. Usage refusals (exit 2) write nothing.
Per-checkpoint receipts under `receipts/` are read only when that
checkpoint's grading ran.

## Smoke fails — stop, fix, do not proceed — on any of:

- the adapter or Pi exits before the model runs (contract, argv,
  dependency, configuration);
- no genuine model-stream events in the retained payloads (empty or
  absent stream content) — without positive evidence the model started,
  an early failure is plumbing-shaped;
- a plumbing code where a model-behavior outcome was expected;
- a receipt that produces no verdict where grading occurred.

## Smoke passes on:

any terminal state — settled, `agent-error`, `output-limit`, timeout —
with genuine model-stream events, a parseable `session-record.json`
recording the terminal reason, and the lifecycle-guaranteed artifacts
for the prompts reached (checkpoint patch, snapshot, transcript prefix
per captured step). Reaching a settled first checkpoint is model
behavior, not a smoke requirement. Model behavior may pass or fail; the
smoke makes no admission, difficulty, or quality claim.

## The five verification-record assertions

1. Pi accepted the model configuration.
2. Genuine model-stream events were emitted.
3. One conversation was maintained across the ordered prompts reached.
4. Session/checkpoint artifacts were parseable.
5. Teardown was clean.

## No compatibility shim

If the run requires an argv compatibility shim, record the stock-adapter
proof as **failed**: the shipped adapter passes against the supported Pi
executable itself.
