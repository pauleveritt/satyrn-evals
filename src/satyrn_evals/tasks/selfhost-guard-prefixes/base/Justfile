# Every gate, in order, failing on the first non-zero exit. Never pipe a
# gate into anything: a check whose exit code is not read cannot fail.
gates:
    uv run pytest -q
    uv run ruff check
    just lint-docs
    uv run python tools/provenance.py check

# Document caps and whitespace (tools/lint_docs.py). No model, network, or subprocess.
lint-docs:
    uv run python tools/lint_docs.py

# The marked tier: real Git, task materialization, oracle execution. Not in CI.
integration:
    uv run pytest -m integration -q
