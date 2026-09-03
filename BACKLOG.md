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

**`stringified-annotations` capture** (V5c, 2026-09-03). Deferred from V5c,
which captures `local-pings` only: its Engine arm is pinned at ceiling (6/6,
`docs/superpowers/specs/2026-09-02-v5a-admission-rule-design.md:78`), so it
buys regression detection rather than headroom. **Reopens once the
diagnostic loop has run on `local-pings`** (the V5c spec's Out of scope).

**`local-pings` oracle improvement — drop `_svc_type`.** The corrected
probe's preservation test identifies registry pings through the private
`_svc_type` field
(`docs/superpowers/research/2026-08-27-local-pings-corrected-probe.md:46-49`),
coupling the oracle to an implementation detail. Changing it changes what is
measured and voids comparison with the recorded probes, so it is not done in
V5c. **Reopens as its own proposal** — a future admission candidate observing
public names or callable execution order.

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

**Captured base trees must not be filtered by the repository `.gitignore`**
(V5c, 2026-09-02). A bundled task's `base/` is a vendored foreign tree; the
repo's `.gitignore` patterns (`.idea/`, `.coverage*`, `node_modules/`,
`docs/_build/`, …) silently drop any *legitimately tracked* file of that name
when the task is committed, and the loss surfaces only on a fresh clone.
`local-pings` was unaffected (only ruff's `.ruff_cache/` junk was filtered),
but the mechanism is live. **Reopens with the next capture whose base tracks a
file matching a repo `.gitignore` pattern** — fix by committing the vendored
tree with an explicit allow (e.g. `git add -f`) or by verifying disk-vs-index
parity after `git add`.

**`python -m satyrn_evals.cli` silently no-ops** (V5c, 2026-09-02). `cli.py`
has no `if __name__ == "__main__"` guard, so module invocation imports the
parser, does nothing, and exits 0 — it cost one confused capture run (reported
"captured", wrote nothing). The console script `satyrn-evals` is the supported
entry. **Reopens when module invocation should either work or fail loudly** —
the fix is a two-line guard plus a tripwire test asserting `python -m` runs.
