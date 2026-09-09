# HP4 implementation plan: declared directory source paths

**Design:** [orchestrated delivery](../../current/orchestrated-delivery-design.md),
deliverable D4. Phase HP, cycle 4. **Plan only, no spec**, per the phase
table: the decision this implements was fixed by that design, and nothing
here moves an evaluation condition, an evidence boundary, a task contract or
an interpretation. Authorizes no inference.

**Goal.** Make a task say which of its `source_paths` entries are
directories, so the packet's declared writable scope stops guessing from
disk and stops disagreeing with the scope the grader actually enforces.

## The defect, stated exactly

`engine_contract.writable_paths` decides directory-ness by probing
`base/` with `is_dir` (`src/satyrn_evals/engine_contract.py:43-46`). A path
absent from `base/` renders as an exact filename, because
`agentclinic-repair-framing-2` declares `models.py` whose base deletes the
file, and that entry is a creation target rather than a directory. The probe
therefore cannot tell an **empty-skeleton directory** from a **creation
target**: both are absent.

One shipped task is on the wrong side of it. `agentclinic-session-phased`
declares four entries and its `base/` contains none of them, so the rendered
scope is four exact filenames. Meanwhile the session route enforces scope
through `patch.within_source` (`src/satyrn_evals/patch.py:166-178`), where a
bare entry admits every descendant. The two disagree about
`templates/base.html`: **enforcement admits it and the declaration does
not.** `build_packet` inherits the gap deliberately and says so in its own
docstring (`src/satyrn_evals/packet.py:160-166`).

The consequence is not cosmetic. A bounded implementer reads the rendered
scope and nothing else. Told it may write `templates`, it cannot create
`templates/base.html` without believing it is out of scope, while the grader
would have accepted the file. That is a packet that misdescribes its own
task, and HP7 would spend inference on it.

## The declaration

An **optional** manifest key, `source_dirs`: a list of strings, each of which
must also appear in `source_paths`. A trailing slash is **not** the syntax;
the roadmap rules that spelling out of scope, and a separate key keeps
`source_paths` a plain list of strings for every reader that already parses
it.

The key is **authoritative when present**. If a manifest declares
`source_dirs`, every entry in it is a directory and every other entry in
`source_paths` is a file, with no probe at all. If the key is absent, the
probe runs exactly as it does today, so the ten shipped manifests that agree
with their `base/` need no edit and their rendered contracts do not move.

Two contradictions are refused rather than resolved, because either one means
the manifest and the tree disagree about the task:

- a declared directory that exists in `base/` as a regular file;
- an entry **not** declared a directory that exists in `base/` as a
  directory.

The second is the one worth having. Without it a manifest could declare
`source_dirs: []` and silently narrow a real directory task to four exact
filenames, which is the present defect wearing a declaration.

## Slices

**HP4.1 — the key, loaded and validated.**
`source_dirs` on `TaskManifest`, defaulting to an empty tuple, with a
sentinel distinguishing *absent* from *empty* so the probe still runs for the
ten manifests that omit it. Validation refuses a non-list, a non-string
entry, a duplicate, and an entry absent from `source_paths`.
*Acceptance:* each refusal names the offending entry, and a sibling manifest
differing only in that entry loads. `BRIEF.md` invariant 5: a loader whose
refusals are all that is tested passes when it refuses everything.

**HP4.2 — the renderer consults the declaration.**
`writable_paths(task_dir, source_paths, source_dirs)` uses the declaration
when it is present and probes only when it is absent. The two tree
contradictions above are refused here, where the tree is in hand.
*Acceptance:* on the phased task's empty skeleton, `templates` and `tests`
render as `templates/*` and `tests/*` while `app.py` and `models.py` stay
exact — the case the probe gets wrong. A manifest declaring a directory that
`base/` holds as a file is refused, and its sibling with the entry corrected
renders. The ten existing manifests render byte-identical patterns, asserted
over every shipped manifest rather than spot-checked.

**HP4.3 — the phased task declares, and the two scopes are pinned together.**
Add `source_dirs: ["templates", "tests"]` to
`agentclinic-session-phased/manifest.json`, and add `admits(patterns, path)`
to `engine_contract` — the fnmatch side of the question, stated once so a
test can ask it.
*Acceptance:* for every shipped manifest, every path the declaration admits
is also admitted by `patch.within_source`, so the packet never tells an
implementer it may write something the grader will reject. And for the
phased task specifically, `app.py`, `templates/base.html` and
`tests/test_app.py` are now admitted, where before the fix
`templates/base.html` was not — asserted against the pre-fix behaviour by
constructing the undeclared form, so the test can fail.

The remaining asymmetry is recorded, not closed: `within_source` admits the
bare path `templates`, and the declaration does not. Writing a regular file
named `templates` over a directory is not a case any task wants, and
narrowing enforcement to match is the "relaxing scope enforcement" the
roadmap puts out of scope. The invariant this cycle buys is one-directional
— **declared never exceeds enforced** — and the test says so in its name.

**HP4.4 — the end-to-end witness on the offline route.**
Reuse HP2's route and fake implementer. Phase 1 of the phased task creates
`app.py`, `templates/base.html` and `tests/test_app.py`.
*Acceptance:* zero scope violations across the three creations, and a
sibling in which the same fake attempts `static/app.css` — outside every
declared entry — is **refused by the fake against the packet's own
`writable_paths`**, from the same fixture. Both halves default tier: the
fake writes files, and no subprocess is involved.

## Explicitly not in HP4

A trailing slash as the settled syntax. Any change to `within_source`,
`check_allowlist` or the grader's allowlist. Any relaxation of scope
enforcement. Making `source_dirs` required, or backfilling it onto the ten
manifests that do not need it. Role attribution (HP5), retention (HP6), any
real model (HP7).

## Verification

`just gates`, exit code read directly, never piped — the recorded lesson is
that a piped gate reports `tail`'s status.

The route witnesses in HP4.4 are default tier, so `just gates` reaches them.
The cycle also touches HP2's executable seam only through `writable_paths`,
so the marked tier is re-run once by hand:

```
uv run pytest -q -m integration
```

## What the implementation found, recorded rather than edited away

**Two fakes were reading the packet by the wrong rule.** Both the in-process
`scripted_implementer` and the executable `fake_implementer.py` checked scope
with prefix matching — `within_source` in one, a hand-rolled `startswith` in
the other — against patterns written in fnmatch. The two rules agree on an
exact filename, which is all the phased task rendered, so the mismatch was
invisible until `templates` became `templates/*` and eleven tests failed at
once. A fake that reads the packet by a different rule than the packet is
written in is not enforcing the packet, so this was a real defect that HP4
surfaced rather than caused. Both now use `admits`.

**The golden packet moved by exactly two lines**, `templates` to
`templates/*` and `tests` to `tests/*`, which is the visible diff the golden
exists to produce.

**Four mutations, each killed.** Ignoring the declaration: 22 failures.
Treating an absent key as an empty declaration: 24. Making `admits` always
true: 19. Dropping the undeclared-directory refusal: 1 — the minimum, and
worth naming, since that gate has exactly one test holding it.

**Five marked-tier failures are not HP4's.** `test_attempt` (two), the
uv-isolation witness and both `local-pings` cases fail in this worktree and
pass in the primary checkout. Verified by stashing every change and
re-running at the plan's own commit. Recorded in `BACKLOG.md`.
