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
- [x] Milestone-repair scoring: deepest_feature_milestone now scans every
      feature checkpoint, so a later cumulative pass (a repair) raises the
      milestone instead of stopping at the first earlier failure.
- [x] Invalid-UTF8 record path: the transcript spools with
      surrogateescape (byte-verbatim) and digests hash raw bytes, so
      invalid-UTF8 adapter output cannot crash the writer; the session
      still ends with a durable record.
- [x] Status/digest fossils: git status lines are recorded in the durable
      digested snapshot; overlay digests are verified at materialization.
- [x] Stale plan docs: execution/correction notes appended to all three
      `2026-09-03-v6-p*.md` plans.
- [x] Front-door docs and verification numbers: README diagnose wording
      corrected (counts only; transcript metrics deferred); ROADMAP
      states remediation; sdd.md smoke/gate numbers reconciled to the
      actual final commands (574/184/758, 2955 stmts/954 branches), with
      the smoke-2 transcript-prefix-vs-full-length conflation corrected.

### Track 3 — V6 final smoke (exit: durable record proves the five smoke assertions on the corrected path)

Scope:
- [x] One new uncounted real-model smoke after the runtime/capture
      fixes (2026-09-04, evidence dir smoke3-session-mechanics-20260904-063108):
      all four prompts settled, plumbing pass, preservation-invalid rule
      proven on a real model.
- [x] Record the five assertions and the outcome in the V6 verification
      record (docs/sdd.md, third real-model smoke).
- [ ] Only then consider merge/completion of V6.

### Not in this cycle

- V5 diagnostic cells are not reopened; two V5 follow-ons are recorded
  separately (evidence-provenance naming for future summaries; replace
  the allocator-sensitive `local-pings` known-broken adversary).
- svcs materialization/re-baselining stays deferred to its own confirmed
  proposal; it inherits the corrected V6 runtime, record, selector, and
  immutable-public-test rules but is not pulled into this cycle.
