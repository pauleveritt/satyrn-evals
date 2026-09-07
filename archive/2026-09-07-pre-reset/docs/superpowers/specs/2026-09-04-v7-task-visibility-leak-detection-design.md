> **Archived pre-reset record (2026-09-07).**
>
> Original claims, decisions, and instructions may be superseded. This file is evidence, not current guidance.
> For current guidance, read root AGENTS.md, BRIEF.md, and ROADMAP.md. Retrieve one named record when it bears on a concrete question; do not preload this archive.

# V7 — Task visibility and leak detection: design spec

**Date:** 2026-09-04.
**Status:** design approved in brainstorm with maintainer corrections
(0o444 as accidental-exposure prevention, conservative content matching);
implementation plan follows external review of this file.

**Amendment (2026-09-04, close-out):** V7 is implemented and merged to
main; its verification record is in `docs/sdd.md`. Post-merge corrections:
`run` names cells from the record's `attempt_dir`, and serialized evidence
is keyed `in`. Backlog anchors for the two entries pruned at close-out are
superseded (outcomes in the ROADMAP V7 row); survivors are cited by title.

## Relationship to what is on main

The grader-overlay *mechanics* are landed and reviewed: `overlay.py`
validates the overlay tree, records per-file digests, and materializes it
into a fresh grader workspace after the patch applies and before the
oracle runs (`src/satyrn_evals/overlay.py`); `grade()` accepts an
optional overlay today and the session grader passes one
(`src/satyrn_evals/grade.py:38,103`, `session_grader.py:144-159`). V6's
non-goal note records the hand-off: "V7 detects leaks and requires cheap
prevention for hidden-oracle tasks rather than V6 preventing them"
(`2026-09-03-v6-session-eval-design.md:245`).

V7 adds what does not exist yet: a declared visibility per task, a
definition of contamination with a detector that discriminates in both
directions, per-arm reporting that leaves every denominator alone, and
the cheap-prevention requirement the backlog pins on this phase (the
"Cheap partial prevention" entry, closed by V7). OS-level containment
stays deferred (its own entry).

## 1. The visibility field

`TaskManifest` gains `oracle_visibility: Literal["visible", "hidden"]`
(`src/satyrn_evals/manifest.py:19-27`), read from the manifest key
`oracle_visibility`. Absent means `"visible"` — all three bundled tasks
remain valid untouched.

- **visible** (default): oracle content lives in `base/` and may be read
  or run by the executor. Normal TDD-style tasks (`format_number`).
- **hidden**: oracle content lives only in the `grader_overlay`
  directory, outside `base/`, materialized only in a fresh grader
  workspace after the patch applies. The V6 session mechanics, now
  declared explicitly. `session-mechanics` gains
  `"oracle_visibility": "hidden"`.

**The ⇔ rule (maintainer-confirmed F1).** One field, two views of one
declaration, enforced symmetrically in `load_manifest`: `hidden`
requires `grader_overlay` to be present; `grader_overlay` present
requires `hidden`. A manifest violating either direction is a
`ManifestError` (exit 2, `errors.py:26-31`).

**Compatibility, stated so nobody "upgrades" a fixture casually.**
`local-pings` stays visible: its preservation oracle lives in `base/` by
V5c design, and moving oracle files to an overlay is a fixture change
that voids the recorded qualification gate — not a flag flip. Any task
converted to hidden is a new fixture needing fresh evidence.

**Authoring-time name check.** A hidden task's executor-visible authored
texts — the manifest `contract`, and for session tasks every
`session.json` step prompt — must not contain any overlay relative path
(exact, case-sensitive substring check on the declared rel paths).
Violation: `ManifestError` / `SessionSpecError`. This encodes the
measured "never named in prompts" clause cheaply and deterministically;
its limit ships in the docstring — a paraphrase passes it.

## 2. What counts as contamination

**Definition.** On a task declared hidden-oracle: grader/oracle artifact
content appearing in executor-reachable material. Three shapes, each
with a recorded precedent:

| # | Shape | Precedent |
|---|-------|-----------|
| a | overlay files present in an executor-reachable workspace (path or content) | models located the suite on disk and optimized against it; one run read up to 49 other cells' directories (`2026-09-02-phase-proposals-and-session-eval-convergence.md:33`) |
| b | grader content inside a retained patch | models copied grader assertions into their own tests |
| c | grader paths/names in executor-visible texts | not naming the grader recovered median 219 → 19 turns (`:36`) |

**Explicitly not contamination** — the sixfold-overstatement lesson
(`2026-09-02-overnight-packet-and-isolation-run.md:168-171`: 10 of 12
flagged files were legitimate model-authored tests): a test restating
behavior the prompt or public tests display; similar-but-not-verbatim
text; same behavior, different bytes. The detector keys on content
derived from grader artifacts, never on "a test file appeared".

## 3. Detection

A pure module `contamination.py` — no I/O of its own, no subprocess —
called where the inputs already exist: `grade()` and the session grader.
Detection never changes a verdict and never changes an exit code; it
annotates the receipt / session record.

### Conservative matching (maintainer correction)

Content matching is exact: **whole-file bytes** or **verbatim stable
fragments**, with evidence pointers. One rule, pinned:

> Reduce both files to their non-blank line sequences (order preserved).
> Flag a patch-added file when any contiguous run of `min(4, n)` lines of
> one overlay file's non-blank sequence appears byte-for-byte as a
> contiguous run of the patch file's non-blank sequence, `n` being that
> overlay file's non-blank-line count (`GRADER_BLOCK_LINES = 4`, a named
> constant). Blank lines in either file never interrupt a run; no
> whitespace, case, or encoding normalization. A three-line overlay file
> is caught only by whole-file match (`min(4, 3) = 3`) — the intended
> floor.

Whole-overlay-file embedding is the `n ≥ 4` case of the same rule; there
is no fuzzy or similarity matching of any kind. A short shared fragment
(`import pytest`, one idiomatic line) cannot fire: the window must come
consecutively *from the overlay file*. The known-good sibling in the
evidence floor includes a model-authored restating test precisely to
prove silence on this class.

The docstring ships the limitation, per the standing rule from the
handoff harvest: this is a verbatim tripwire for the copying that
actually happened — not a proof of ignorance. A paraphrased leak passes
it, and the spec does not claim otherwise.

### The three checks as implemented

- **(a) `overlay_in_workspace` — a structural invariant, test-proven,
  not a receipt check.** Evals constructs every executor workspace from
  `base/` only (V4 `workspace.py`; V6 session worktrees), so the
  executor tree can never contain overlay content by construction. Two
  proofs are required, not one (maintainer pin): the workspace builders
  assert the invariant at build time — a file inventory scan rejecting
  any path equal to an overlay rel path *or* any file whose bytes match
  an overlay digest, refusal-shaped if it ever fires — and integration
  tests drive the real builders and scan the resulting tree. Absence is
  the real invariant; read-only modes are secondary (§5). The check
  name names the builder assertion and its tests; it is **never
  emitted in a receipt's checks array** — receipts carry (b) and, for
  sessions, (c). A base file matching an overlay digest is itself the
  authoring defect the assertion catches, so that refusal is correct,
  not a false positive.
- **(b) `grader_content_in_patch` — receipt check.** Runs in `grade()`
  against the patch bytes already in hand and the loaded `OverlaySpec`,
  which V7 extends to carry each overlay file's verbatim lines (the
  loader already reads every file's bytes for its digest). For
  sessions, runs per checkpoint on the retained
  cumulative patch — including scope-violated checkpoints, whose
  evidence patch stays retained even though hidden grading skips
  (`session_grader.py:75-79`); detection is not grading and still runs.
- **(c) `grader_name_in_payload` — receipt check, sessions and
  authoring.** Exact substring match of overlay rel paths against the
  executor-visible sources pinned in §4. At authoring time this is the
  §1 name check; at run time it scans retained payloads.

### Clean versus unmeasured (maintainer pin)

Per check, exactly three outcomes:

- `flagged` — the rule matched; evidence pointers name the overlay file,
  the patch file or payload source, and the match location.
- `clean` — the check ran to completion over **all of its required
  inputs** and matched nothing.
- `unmeasured` — a required input is absent or unparseable, so the check
  could not run: retained patch bytes missing, a session step with no
  retained payload events, a receipt from a pre-V7 grader (no findings
  key). Recorded as `unmeasured`, **never folded into `clean` and never
  reported as zero** — the absence-of-signal rule
  (`2026-09-02-overnight-packet-and-isolation-run.md:161-163`).

Overall finding for one graded artifact: `flagged` if any check flagged;
else `unmeasured` if any check is unmeasured; else `clean` — so overall
`clean` requires every applicable check clean. A check that does not
apply to the artifact class (payload scan on an ordinary attempt) is not
emitted at all rather than recorded — its non-applicability is stated in
§6, not smuggled into the tally. A multi-checkpoint artifact (a session)
rolls up per cell the same way: `flagged` if any checkpoint's finding is
flagged, else `unmeasured` if any is unmeasured, else `clean`; a
scope-violated checkpoint participates — its retained evidence patch and
payloads are detection inputs even though hidden grading skips.

## 4. Executor-visible sources scanned (exact pin, maintainer request)

Check (c) scans exactly these, and nothing else:

1. **Retained session event payloads** — the `payload` value of every
   retained event line of the five mapped kinds
   (`src/satyrn_evals/session_protocol.py:18-21`: `turn_end`, `tool_end`,
   `context_compacted`, `context_reset`, `other`), walked for string
   values. The payload-retention decision
   (`BACKLOG.md`, "Raw-Pi message retention — decided") is what makes
   this scan bounded: mapped kinds retain the complete original Pi event
   in `payload`; unmapped kinds and malformed lines are not retained and
   are therefore not scanned and not claimed.
2. **Authored executor-visible texts** — each `session.json` step prompt
   and the manifest `contract` (checked at load; §1).

**Not scanned, with reasons:** adapter argv and environment — evals
constructs them; a test asserts they never contain overlay paths.
Engine-spooled ordinary-attempt transcripts — beyond the engine seam
(`BACKLOG.md`, "Transcript-derived summary metrics"); no contamination
claim may rest on them, and none is made.

## 5. Cheap partial prevention, and its stated limit

The "Cheap partial prevention" entry reopens with V7 and requires POSIX file modes *or* a
separate run user for any hidden-oracle task, rather than detection
alone. V7 takes file modes, with the maintainer's correction stated
plainly:

> **0o444 is accidental-exposure prevention, not security isolation.**
> The same executor user that can reach a file can `chmod` it. The real
> invariant is structural: hidden overlays are never materialized in
> executor-reachable paths (§3, check (a)). Modes are defense-in-depth
> against *accidental* materialization and in-place edits — no more.

- **At materialization** (the only place evals controls modes
  end-to-end): `materialize_overlay` chmods each grader-workspace copy
  `0o444` after digest verification. Test-proven both ways: materialized
  files are read-only; a grader run that tries to write one fails.
- **At load, bounded by git's mode vocabulary — superseded by V9.** Git
  stores only `100644`/`100755`, so a committed file cannot carry `0o444`
  and a fresh clone always lands owner-writable. V7's stored-file check
  refused group/other write bits (`mode & 0o022`).
  > **Superseded by V9 (2026-09-04):** removed — the checkout umask
  > makes a clean `100644` store land `664` (umask 002) or `666` (umask
  > 000), so the check refused clean checkouts; materialization `0o444` +
  > the absence invariant remain. V9 spec §4 T6 records the correction.
- **A separate run user** stays recorded in `BACKLOG.md` as the
  alternative, not adopted: not default-tier testable on this repo's
  CI, and an operational system the concept budget cannot carry now.

## 6. What ordinary (non-session) attempts can and cannot measure (maintainer pin)

Ordinary attempts preserve patch and transcript before cleanup
(`attempt.py`; glossary "preservation"), with digests, into an attempt
directory named `<task>-<UTC microsecond timestamp>` (`attempt.py:75`).

- **(b) is measurable**: the preserved patch bytes are the artifact.
- **(a) is structural**: the V4 workspace builder builds from `base/`
  only; the §3 build-time assertion and tests prove absence.
- **(c) does not apply**: evals owns no executor-visible payload stream
  for an ordinary attempt; the transcript is engine-owned and opaque by
  the seam. **An ordinary attempt's `clean` is evidence over the
  preserved patch and the workspace invariant only, and is not a claim
  about the engine transcript.** V5d's smoke discipline governs the
  first real-model use of any new execution path.

## 7. Reporting per arm, denominators intact

**Receipts** gain one additive, optional key `contamination`:

```json
{"visibility": "hidden",
 "checks": [{"check": "grader_content_in_patch", "outcome": "clean", "evidence": []}]}
```

Evidence items: `{"kind": "whole_file" | "block" | "path",
"overlay_path": ..., "in": <patch rel path | step id + event kind>,
"line": <int, 1-based, into the "in" artifact>}`. `grade()` loads the overlay itself when
the manifest declares hidden and no explicit overlay was passed
(`overlay=None` default today, `grade.py:38`); the session grader keeps
passing its explicit overlay, so its path is unchanged. Visible tasks:
no checks run, the key is absent, the receipt shape is byte-compatible.
Loaders tolerate the key's absence — stored artifacts must replay.

**Session records** gain the same additive per-checkpoint key with the
same vocabulary; loaders tolerate absence.

**The summary** — since V7 changes its format, the V5 evidence-provenance
correction fires now (entry pruned at close-out; the ROADMAP V7 row
records it): the summary must name the
exact cell set it was computed over, recomputable by filter, not by
hand. `summary.json` gains, always: `oracle_visibility` (`"visible"` or
`"hidden"`) and `cells` (the n attempt directory names, in run order);
and, for a hidden task, a contamination section **beside** the existing
counts:

```json
{"contamination": {"graded": 8, "flagged": 1, "clean": 6, "unmeasured": 1}}
```

with the invariant `flagged + clean + unmeasured == graded`, where
`graded` counts cells that produced a receipt (refused cells have no
grading and appear only in the existing counts). `n`, `attempted`,
`refused`, `code_counts`, `verdict_counts`, `timeouts` keep their exact
meanings; a flagged attempt stays counted in its verdict bucket — the
tally is a separate dimension, never a reclassification, never a
denominator change. Visible-task summaries omit the section and say why
via `oracle_visibility`.

## 8. CLI surface and exit codes

No new commands, no signature changes. Refusals reuse existing
`SatyrnError.exit_code` semantics: manifest/overlay/session-spec
violations are usage errors, exit 2 (`errors.py:26-31,104-110`);
detection findings never change any exit code; `unmeasured` is a
recorded outcome, not an infrastructure refusal, so it never maps to 3.

## 9. Data shapes

```python
type OracleVisibility = Literal["visible", "hidden"]
type ContaminationCheck = Literal[
    "overlay_in_workspace", "grader_content_in_patch", "grader_name_in_payload"
]
type ContaminationOutcome = Literal["flagged", "clean", "unmeasured"]
```

Per the house style: semantic aliases via `type` statements; the
detector dispatches on check kind with `match`/`case`; bind-and-test
with `:=` where a computed value is branched on.

## 10. Non-goals

- OS-level containment — deferred ("OS-level containment" entry); V7 detects.
- Any claim about engine-owned ordinary-attempt transcripts (§6).
- Preventing paraphrased leaks — the detector is a verbatim tripwire
  whose limitation ships in its docstring (§3).
- The claims layer: no arm-to-arm statistics or intervals; "per arm"
  means findings sit beside per-arm counts, never pooled into them.
- No rerun, reinterpretation, or re-scoring of completed V5 cells; the
  cell-set naming is prospective from V7 onward (V5 evidence-provenance
correction — closed by V7).
  The `local-pings` adversary replacement and V5 evidence-provenance
  maintenance stay backlog tracks; `stringified-annotations` capture and
  svcs materialization/re-baseline stay their own proposals. V7 ships
  the instrument before the next diagnostic workload is captured — the
  rejected order (capture first; no workload is admitted today) is
  recorded deliberately.
- No smoke is owed by V7: no model runs, no new execution path. V5d
  triggers at the first real-model use of a hidden task on a new path.

## 11. Done-when

1. The manifest field lands with the ⇔ rule, each refusal direction
   tested with a success sibling; `session-mechanics` declares hidden;
   `format_number` and `local-pings` manifests unchanged.
2. `grade` on a hidden task auto-loads the overlay and annotates the
   receipt; a visible task's receipt has no `contamination` key.
3. **The evidence floor (BRIEF rule 8):** the detector fires on a
   known-contaminated fixture patch and stays silent on the same task's
   known-good fixture — both asserted by name — and the known-good
   includes a model-authored restating test that must not flag.
4. Executor-workspace **absence** (not only read-only) is proven: the
   build-time invariant assertion, a default-tier test of the pure
   inventory predicate, and an integration-tier scan of real ordinary
   and session executor worktrees finding no overlay path and no
   overlay-digest file.
5. Materialized grader files are `0o444` (test-proven). **Superseded
   (V9, 2026-09-04):** the stored-file group/other-writable refusal was
   removed — checkout umask makes it unsound (§5; V9 spec §4 T6).
6. Summaries name `cells` and `oracle_visibility`; hidden-task summaries
   carry the contamination section with the invariant held; a property
   test proves every existing count is unchanged by detection outcomes.
7. Session records carry per-checkpoint findings additively; loaders
   accept records with and without the key.
8. Default tier stays no-model, no-network, no-subprocess (tripwire
   green); process and real-git proofs live in the marked integration
   tier.
9. `unmeasured` paths each have a test producing exactly that outcome
   (missing patch bytes; a session step with no retained payloads).

## 12. Reviewable slices

1. **Manifest + visibility:** field, ⇔ rule, authoring name check,
   `session-mechanics` flagged hidden, refusal/success siblings.
2. **The detector:** `contamination.py` pure module, the pinned block
   rule, evidence pointers, clean/unmeasured semantics, discrimination
   fixtures (contaminated known-bad; known-good with a restating test).
3. **Grade + summary:** auto-overlay for hidden, receipt key, summary
   `cells`/`oracle_visibility`/contamination section, denominators
   property test, run cell naming.
4. **Session + prevention + absence:** payload scan, per-checkpoint
   record key, materialization modes, stored-file check, workspace
   absence invariant and integration proofs, docs and glossary at
   close-out — including closing the two V7 backlog entries ("Cheap
   partial prevention", "V5 evidence-provenance correction").

## 13. Verification record shape

The V4/V6 pattern (`docs/sdd.md`): default-tier `pytest -q` counts; the integration-tier command; the 100% statement-and-branch coverage gate; no smoke section (§10). The record names the two discrimination fixtures and the absence-proof command.

## 14. Evidence and recomputation

Code anchors, each a one-command check: overlay mechanics and digests
`src/satyrn_evals/overlay.py` (`materialize_overlay`); `grade()` overlay
parameter `grade.py:38,103`; session grader passes it
(`session_grader.py:144-159`, scope-skip at `:75-79`); mapped payload
kinds `session_protocol.py:18-21`; exit mapping `errors.py:22-31,104`;
attempt directory naming `attempt.py:75`; manifest dataclass
`manifest.py:18-27`; V6 hand-off `2026-09-03-v6-session-eval-design.md:245`.

- Measured leak surfaces:
  `docs/superpowers/research/2026-09-02-phase-proposals-and-session-eval-convergence.md:33`
  (stored where reachable), `:36` (named in prompt; 219 → 19 turns).

- Sixfold overstatement:
  `docs/superpowers/research/2026-09-02-overnight-packet-and-isolation-run.md:168-171`;
  the zero-cells "unmeasured" incident `:161-163`.

- Git mode vocabulary: `git ls-files -s
  src/satyrn_evals/tasks/session-mechanics/grader/overlay/` reports all
  three overlay files `100644` — so a stored `0o444` check would fail on
  every fresh clone.