# Every gate, in order, failing on the first non-zero exit. Never pipe a
# gate into anything: a check whose exit code is not read cannot fail.
gates:
    uv run pytest -q
    uv run ruff check
    just lint-docs
    just docs
    uv run python tools/provenance.py check

# Document caps and whitespace (tools/lint_docs.py). No model, network, or subprocess.
lint-docs:
    uv run python tools/lint_docs.py

# Build the docs site (Zensical), failing on any validation issue. Offline.
docs:
    uv run --group docs zensical build --strict

# Serve the docs site locally for preview.
docs-serve:
    uv run --group docs zensical serve

# Fetch satyrn-engine at the commit the Engine arm pins, into ../satyrn-engine.
fetch-engine:
    uv run python -m tools.engine_sync fetch

# Sync the pinned engine's docs into the committed _engine/ copy and its provenance rows.
sync-engine:
    uv run python -m tools.engine_sync sync

# The marked tier: real Git, task materialization, oracle execution. Not in CI.
integration:
    uv run pytest -m integration -q
