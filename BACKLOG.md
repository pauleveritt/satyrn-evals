# Backlog: satyrn-evals

Deferred work. Read [`BRIEF.md`](BRIEF.md) first; the phase list is in
[`ROADMAP.md`](ROADMAP.md).

**Three rules, from `docs/sdd.md`:**

1. **Every entry states what reopens it.** An entry that cannot say what would
   make it relevant again is deleted, not kept "just in case".
2. **An entry over its cap owes a research doc.** The entry then keeps a
   summary, a link, and the reopen condition — not the argument.
3. **Entries are pruned, not archived in place.** Resolved, retired and
   superseded entries are removed once their outcome is recorded in a phase row
   or a research doc that the row links.

This file exists because a predecessor project's `ROADMAP.md` reached roughly
1,000 lines, about 800 of them Backlog, one defensible paragraph at a time.

## Entries

**Transcript-derived summary metrics** — `tool_calls`, `repeat`, `churn`,
`context` (V5b, 2026-09-02). Their data is Pi's print-mode stream-JSON,
spooled verbatim by the engine as `transcript.jsonl`
(`satyrn-engine/src/satyrn_engine/attempt.py:578`, `:206-225`); parsing it in
evals would reach through the engine seam that V4 established as opaque to
evals. These counts belong engine-side, published as structured fields — the
`facts` field already named in `ROADMAP.md:60` (satyrn-engine `BACKLOG.md`).
Definitions are recorded: `repeat` is identical `(toolName, arguments)` calls
counted regardless of success
(`docs/superpowers/research/2026-08-16-harvest-index.md:69-71`); `churn` is
the same target rewritten with differing content (`:74`), kept separate
(`docs/superpowers/research/2026-09-01-handoff-and-eval-harvest.md:360`); the
counts must report **unmeasured**, never zero, where a transcript yields no
parseable events
(`docs/superpowers/research/2026-09-02-overnight-packet-and-isolation-run.md:160-162`).
**Reopens when the engine exposes these counts across the seam** — not when a
transcript sample becomes available.

**Automated commit mining.** Reopens after three manual captures show which
steps repeat.

**Paired A/B of two engine versions.** Reopens when a contributor needs "did my
fix help" across versions.

**Resumable large batches.** Reopens only if the prior checkpoint transplants
verbatim.

**The whole claims layer** — pre-registration, confidence intervals, condition
enforcement, cells and digest pinning, void and retry accounting, the
pilot/confirmatory distinction, model canaries, A/B publication machinery.
Deferred by the diagnosis-before-claims split, which is the decision governing
everything else and is not reopened here. **Reopens on a later consumer**, in
`BRIEF.md`'s own words (`BRIEF.md:33-36`).

**OS-level containment for the attempt** (reopens when all four recorded
blockers are cleared, or when detection proves insufficient in practice). A
whole-process sandbox profile was built and measured during the 2026-09-01
spike and is **deferred, not adopted**: it is macOS-only; it silently removed
the model's own test runner, so an entire block measured models that could not
self-verify; a hard link created inside the run root still read the grader
through it; and it conflicts with V4's absolute external engine-contract path
— though the V6 design already routes around that last one by copying a public
contract into the worktree rather than referencing it by task path. V7 uses
after-the-fact content detection instead. *Recorded direction change:* an
earlier note in this planning cycle said "make containment genuinely usable,
including a test runner"; this entry defers it rather than fixing it, and a
still earlier draft wrote "refused" where the evidence only supports
"deferred".

**Cheap partial prevention** (reopens with V7): POSIX file modes and a separate
run user need no new system, and V7 should require one of them for any task
declaring a hidden oracle rather than relying on detection alone.

**Text-contract support.** Reopens when a roster model cannot emit tool calls —
two of six models measured in the spike could not, so this is when, not if.

**Writable-scope injection.** Reopens if scope overreach is measured here.

**An orchestrator process.** Remains unjustified — every effect measured so far
was obtained without one, and autonomous contract authoring measured worse than
hand authoring.
