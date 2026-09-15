#!/usr/bin/env bash
# V8 qualification gate (spec §6): runs the parametrized three-row and
# contamination-pair tests over the kept tasks. Integration tier (uv,
# network on first sync). Exit code is the test suite's.
set -uo pipefail
uv run pytest tests/integration/test_agentclinic_gate.py -m integration -q "$@"
