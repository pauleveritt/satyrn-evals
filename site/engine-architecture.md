---
title: Architecture
---

# Engine architecture

`/implement` is two steps: **derive** a contract from the task text, then
**deliver** one bounded change.

- **derive** parses and validates the contract, with the record's budget
  carried verbatim.
- **deliver** runs one fresh Pi subprocess — every guard loaded — in its own
  linked Git **worktree**, commits a candidate, validates it, and writes a
  **receipt**.
- Worktree isolation keeps ordinary writes off the caller's checkout; it is
  isolation from the caller's files, not a security sandbox.

The pieces are the TypeScript adapter that exposes `/implement` inside Pi,
and the Python core that does the work. Terms are in the engine
[glossary](engine-glossary.md); the product is described on
[About Satyrn Engine](engine.md).

Describes the engine synced at `78ab87dbab3381dd585986c43fd49e6e4974f6b6`.
