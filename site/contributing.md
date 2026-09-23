---
title: Contributing
---

# Contributing

The work is governed by `AGENTS.md` and `BRIEF.md` in the repository — read
those before writing code. The essentials:

- **`just gates`** runs the full check: tests, lint, doc caps, the strict site
  build, and provenance. It must exit 0.
- **Provenance** is the rule, not a nicety: every file has a row in
  `PROVENANCE.md`, and a file without one fails the gate.
- **The default test tier** runs without a model, network, or subprocess; the
  real run is the marked integration tier.

Reach us on Mastodon — **TBD** — to start.
