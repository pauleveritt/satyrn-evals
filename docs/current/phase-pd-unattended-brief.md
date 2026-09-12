# Phase PD, unattended: brief for a new agent

**This brief is the authorization for PD2–PD5, and its scope is a ceiling,
not a target.** [The design](prompt-delivery-design.md) says why and names
what is out of bounds; do not re-derive the goal from memory, read it there.
Nothing in this brief supersedes anything the design marks excluded. If a
step in this brief and the design ever disagree, the design wins and the
agent stops to say so.

## What this authorizes, precisely

PD2 through PD5, exactly as scoped in
[prompt-delivery-design.md](prompt-delivery-design.md)'s own sequence
section, run once, unattended, to completion or to a named stop. It does
**not** authorize: touching `.claude/worktrees/overnight-phase4-context` in
any way; a change to `satyrn-engine`; extending PD5 past `n=2` per arm per
variant for any reason, including a favorable or an ambiguous result;
merging this work's branch to `main`; a confirmation campaign; adopting the
edit guard or `base_files`; or any claim that Baseline or Engine is the more
reliable architecture. Those are the design's own exclusions, restated here
because an unattended run has no one to catch it reaching for them.

## Operating model: three roles, one cycle each

A **cycle** is one of PD2, PD3, PD4, PD5, run in that order — each is a gate
the next cycle does not start without clearing. Every cycle has the same
shape:

1. **Opus steers.** Reads this brief's section for the cycle and the
   matching section of the design doc, decides the concrete plan for that
   cycle, resolves any ambiguity by re-reading `AGENTS.md`, `BRIEF.md`, and
   the design doc rather than guessing, and hands Sonnet a specific,
   bounded task list. Opus does not write code or prose deliverables itself
   except the cycle's own status note.
2. **Sonnet implements.** Executes exactly what Opus specified: writes the
   files, runs the commands, makes the commits. Sonnet does not expand
   scope on its own judgment; if the task list turns out to be
   underspecified or wrong, it stops and reports back to Opus rather than
   improvising past what was asked.
3. **Fable reviews, once the cycle's work is assembled.** Reads the actual
   diff and output against the design doc's stated intent for that step and
   this project's own evidentiary standard — cited file paths, no rounded
   figures, no claim beyond what the retained evidence supports, and for
   PD3 specifically, whether a developer would actually recognize the
   result. Fable returns one of:
   - **Approved.** State why, briefly, and the cycle advances.
   - **Send back**, with a specific, itemized list of what must change.
     Opus re-steers from the list; Sonnet fixes; Fable reviews again.
   - **Stop.** Reserved for a genuine scope question the brief and design
     do not resolve, or a second rejection of the same issue. A stop ends
     the unattended run here — it is not a third review cycle.

Every commit is authored by whichever model actually did the work, with
that model's own attribution line. Opus's steering decisions and Fable's
review verdicts are recorded as a short note in the cycle's own commit or a
running log file in the new worktree (`docs/current/phase-pd-cycle-log.md`,
appended to, never overwritten) — an unattended run with no visible
transcript to the user needs this to be legible after the fact.

## PD2 — worktree and branch

**Opus:** confirm `.claude/worktrees/overnight-phase4-context` is untouched
and will stay that way; name the new worktree and branch (a name that says
what this is, not a version number). **Sonnet:** create it per
`superpowers:using-git-worktrees`, confirm it is clean and on the intended
base. **Fable:** confirm the old worktree's git state is unchanged (a `git
status`/`git log -1` check against the SHA already on record,
`fbb23f4`) and the new one is correctly isolated. This cycle has no other
output; it does not touch task code.

## PD3 — SDD delivery (heaviest scrutiny; do not shortcut the review)

**Opus:** translate the design's PD3 section into concrete file changes:
`base/specs/{mission,tech-stack,roadmap}.md` materialized into the
workspace, the per-phase prompt collapsed to a pointer sentence, and the
packet builder (HP1, evals-owned) changed so it carries the specs files
rather than re-inlining the roadmap into `objective` or `preserve`. Name
both call sites that must change: the Baseline session's prompt
construction and Engine's packet builder. **Sonnet:** make the change,
write or update a `prompt-faithful` witness authored from the pointer
prompt plus the specs alone, and run it through the existing qualification
checks. **Fable:** this review is not a code-quality pass. Read the
resulting workspace and prompt as if you were the developer being handed
this task cold, with no memory of the detailed version. Ask directly: does
this look like a real spec-driven-development handoff, or does it still
smell like a test harness? Compare it side by side with
`dlai-local-ai-course/specs/` and SwiftStar's `main.swift:75-76`
shared-context convention, named in the design doc — not as a formality,
as the actual bar. A delivery that passes qualification but reads as
synthetic is a failed cycle, not a passed one; send it back with the
specific tell that gave it away.

## PD4 — easy and hard variants, one grader

**Opus:** confirm the plan is exactly the design's two bullets — easy is
the current text relocated into `specs/roadmap.md` verbatim, hard is
`local-ai-pi`'s `roadmap-user-story.md` and `domain.md` for phases 1–3
plus a newly authored phase-4 story in the same voice — and confirm both
will run against the byte-identical `grader/overlay` and fixtures already
qualified for this task family. **Sonnet:** build both, author the phase-4
story, run qualification for each, and when a hidden check cannot be
reached from story-level wording (the design names check 14, the
keyword-only `id` contract, as the likely case), record that as a
qualification finding in the new task's own note rather than quietly
loosening the check or padding the story with implementation language to
route around it. **Fable:** verify the two variants differ only in prompt
style, not in what they are allowed to touch or what they are graded
against; verify the phase-4 story reads as an outcome an agent experiences,
not a rewritten implementation bullet with the technical nouns filed off;
verify any qualification finding is stated as a finding, not silently
absorbed.

## PD5 — n=2 screen, route verification, no budget beyond what's here

**Opus:** before anything runs, write the pre-run record this brief already
authorizes: the outcome question (hidden-grader completion) and the cost
question (per-phase `turn_count`, `tool_count`, `elapsed_seconds` from
`session-record.json`; `implementer_cost`/`orchestrator_cost` from
`chain.json`; `turn_ledger.py` across both), frozen before the first cell,
per the design's own instruction. Check GPU/model-server availability
first; if unavailable, stop and report rather than fabricate or skip a
cell. **Sonnet:** run one route-verification attempt per arm per variant
(outside the denominator), then the eight screen cells (two interleaved
attempts per arm, per variant), retaining every transcript and patch the
way every other run in this project is retained. **Fable:** confirm the
screen matches its own pre-run record exactly — no cell added or dropped,
no denominator redefined after seeing a result — and write the result
doc: completion by arm and variant with denominators, the cost figures, and
a plain statement that eight attempts support an observation and a route
verification, not a superiority claim, not a rate, and not a mechanism
attribution. A negative, mixed, or blocked result is reported the same way
a favorable one would be.

## Ending the run

The phase is done when PD5's result doc is written and committed in the new
worktree, or when a cycle stops for a genuine, brief-and-design-unresolved
reason. Either way, the run ends there: it does **not** merge to `main`, does
**not** propose a next phase, and does **not** re-run anything to try for a
better number. Leave that decision, and whatever comes after it, to whoever
reads the result.
