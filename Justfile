# Local docs tooling. The CI build (`.github/workflows/pages.yml`) is the
# strict `-W` one-shot; these targets are for working in the docs.

# Rebuild the docs as you edit them, serving the result on
# http://127.0.0.1:8003 (sphinx-autobuild; add `--open-browser` to open it)
watch-docs:
    uv run --group docs sphinx-autobuild --port 8003 docs docs/_build/html

# One-shot strict build — the same gate CI runs, for a quick check
docs:
    uv run --group docs sphinx-build -W -b html docs docs/_build/html

# Every gate, in order, failing on the first non-zero exit. Use this rather
# than typing the four commands: on 2026-09-06 two sessions checked a gate by
# reading the exit code of the `tail` it was piped into — a check that cannot
# fail, which is this project's own named instrument defect. A gate is never
# piped into anything.
gates:
    uv run pytest -q
    uv run ruff check
    just lint-docs
    just docs

# Enforce the document caps in docs/sdd.md. Caps alone do not work.
lint-docs:
    uv run python tools/lint_docs.py

# Render committed diagrams that have .d2 sources (d2 CLI --sketch --theme 0
# --scale 0.5, version v0.8.2). If a diagram fell back to hand-authored SVG,
# it has no source line here and is verified by the strict build instead.
diagrams:
    d2 --sketch --theme 0 --scale 0.5 docs/diagrams/agent-big-picture.d2 docs/diagrams/agent-big-picture.svg
    d2 --sketch --theme 0 --scale 0.5 docs/diagrams/evals-evidence-loop.d2 docs/diagrams/evals-evidence-loop.svg
