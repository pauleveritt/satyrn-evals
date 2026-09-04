# Local docs tooling. The CI build (`.github/workflows/pages.yml`) is the
# strict `-W` one-shot; these targets are for working in the docs.

# Rebuild the docs as you edit them, serving the result on
# http://127.0.0.1:8003 (sphinx-autobuild; add `--open-browser` to open it)
watch-docs:
    uv run --group docs sphinx-autobuild --port 8003 docs docs/_build/html

# One-shot strict build — the same gate CI runs, for a quick check
docs:
    uv run --group docs sphinx-build -W -b html docs docs/_build/html

# Enforce the document caps in docs/sdd.md. Caps alone do not work.
lint-docs:
    uv run python tools/lint_docs.py

# Render committed diagrams that have .d2 sources (d2 CLI --sketch --theme 0,
# version v0.8.2). If a diagram fell back to hand-authored SVG, it has no
# source line here and is verified by the strict build instead.
diagrams:
    d2 --sketch --theme 0 docs/diagrams/agent-big-picture.d2 docs/diagrams/agent-big-picture.svg
