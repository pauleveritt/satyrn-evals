# V6 Remediation and Re-verification

> **For agentic workers:** this is a bounded remediation plan for the
> V6 session-eval branch while it stays open. V6 is not ready to merge
> and is not complete. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Bring V6 to a state where a final uncounted real-model smoke
on the corrected runtime passes and merge/completion can be considered.

**Architecture:** One open branch, three sequential tracks with explicit
exit conditions (below). V5 diagnostic cells are not reopened; svcs
materialization/re-baselining stays deferred to its own confirmed
proposal.

**Spec:** `docs/superpowers/specs/2026-09-03-v6-session-eval-design.md`
(and the 2026-09-01 design of record), amended by the remediation record
in that file.

## Global Constraints

- A refusal test has a sibling success test (BRIEF).
- The verdict comes from retained artifacts, never stdout/exit code.
- 100% statement+branch gate; ruff clean; `just lint-docs` within caps.
- Corrections are recorded, not edited away.

---

### Track 1 — V6 integrity remediation (exit: new failure-path tests and all gates green)

Scope: prompt-wide deadline; sanitized Git environment for the adapter
and the alternate-index capture; per-checkpoint durable record linkage;
generic selector semantics for the grader verdict.

- [x] Prompt-wide deadline (`step_timeout` bounds the whole prompt).
- [x] Sanitized Git environment (adapter spawn + capture use the
      workspace's cleaned environment).
- [x] Per-checkpoint durable linkage (record atomically replaced after
      each captured checkpoint).
- [x] Generic selector semantics (collectors without `::` grade).
- [x] Failure-path tests for all four.
- [x] Gates green: 754 passed / 3 skipped, 100% coverage.

### Track 2 — V6 evidence reconciliation (exit: specs, plans, docs, and code agree)

Scope:
- [ ] Milestone-repair scoring: a later repaired milestone must not be
      zero because an earlier checkpoint failed (scoring currently stops
      at the first failed earlier checkpoint).
- [ ] Invalid-UTF8 record path: adapter output that is not valid UTF-8
      must not bypass the started-session durable-record guarantee.
- [ ] Status/digest fossils: the full Git status and
      `OverlaySpec.digests` are computed but not load-bearing — persist
      and enforce them, or remove them.
- [ ] Stale plan docs: append execution/correction notes to
      `docs/superpowers/plans/2026-09-03-v6-p*.md` so they are not
      mistaken for current truth.
- [ ] Front-door docs and verification numbers: correct the active docs
      (V5b diagnosis overstatement; V6 still described as proposed;
      `docs/sdd.md` smoke/gate numbers — including the checkpoint-prefix
      vs full-transcript-length conflation).

### Track 3 — V6 final smoke (exit: durable record proves the five smoke assertions on the corrected path)

Scope:
- [ ] One new uncounted real-model smoke after the runtime/capture
      fixes (sanitized environment and durable capture are a materially
      revised execution path). Model and rule as the prior smokes
      (local omlx model, stock pi, no shim, durable evidence dir).
- [ ] Record the five assertions and the outcome in the V6 verification
      record.
- [ ] Only then consider merge/completion of V6.

### Not in this cycle

- V5 diagnostic cells are not reopened; two V5 follow-ons are recorded
  separately (evidence-provenance naming for future summaries; replace
  the allocator-sensitive `local-pings` known-broken adversary).
- svcs materialization/re-baselining stays deferred to its own confirmed
  proposal; it inherits the corrected V6 runtime, record, selector, and
  immutable-public-test rules but is not pulled into this cycle.
