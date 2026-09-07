# Lessons, indexed by symptom

**What this is.** `CLAUDE.md` says: *"If you find a new failure mode worth
keeping, add it to this repository's own lessons file the same way, indexed
by symptom."* This is that file. It did not exist until 2026-09-07 and is
seeded here with the failure modes this repository found itself.

**Indexed by symptom, not by mechanism**, for the reason the inherited
[harvest index](../superpowers/research/2026-08-16-harvest-index.md) gives:
a prior cycle spent a full spec, build and pilot on a premise two committed
documents already refuted, because the record filed the fact under *what a
child inherits* while the cycle was searching for *how to reach a child*.
Keep the symptom in the heading.

**This file is an index, not a store.** Each entry is a few lines and a
link to the record that carries the evidence and the commands.

**Inherited lessons are not duplicated here.** Failure modes from
`local-ai-pi` live in the
[harvest index](../superpowers/research/2026-08-16-harvest-index.md); read
both.

---

## "Every arm failed the same way, so the task must be hard"

`depth-3` read 0/12 in both arms across two batches and was recorded as a
quality floor from V11c until 2026-09-07. It is not hard: at rung **R3** it
reads **12/12**, every patch touching all three files. The base, the seeded
defects and the workspace test suite are identical at both rungs. Only the
contract text differs — R3 says "the model's stored complaint timestamp
lost its timezone", R1 says `assert None is not None` — and the seam that
nobody closed at R1 is a two-line change.

**Ask:** does the contract *describe* the defect, or only name a failing
assertion? A floor that appears in every arm at once is a property of the
task before it is a property of the agents — and on this suite the property
that moves it is description, not verifiability: R1 reads 0/12 and R3, with
the same blind suite, reads 12/12.

**Check it:** run the task at a more explanatory rung before concluding
anything about the agents.

Record:
[V15 premise correction](../superpowers/research/2026-09-07-v15-premise-correction.md) §7.

---

## "The contrast is so clean it must be the mechanism"

**The entry that used to sit here was wrong, and its error is the lesson.**
It named *false completion* — agents stopping early because their workspace
suite could not observe the graded seam — on a contrast of 33/34 against
0/9. It was refuted the same day, before any cell was spent, on three
grounds:

- **Two equally invisible seams closed at 13/23 and 0/23** in the very
  batch the claim was built from. Visibility cannot produce that spread.
  What differed was the contract: one seam's acceptance test *names its own
  defect*, the other's reads `assert None is not None`.
- **A control was already on disk.** `depth-3` at rung R3 passes **12/12**
  with the same blind suite, every patch touching all three files. Only the
  contract text changed. `ROADMAP.md` already recorded that R3 ceilings
  almost everywhere, and the author had read that line the same session.
- **The statistic did not mean what it was read to mean.** See the next
  entry.

**Ask:** before naming a mechanism from a contrast, search the retained
batches for a cell that varies your proposed cause while holding the rest.
This project's rungs are exactly that control and they are already run.
`grep -rn "R3" ROADMAP.md` costs nothing.

Records:
[False completion](../superpowers/research/2026-09-07-false-completion.md)
(refuted — read its §7 first).

---

## "The exit code says the agent finished"

`AttemptCode.OK` means *a patch and a transcript existed and grading ran*.
It says nothing about why the agent stopped — `attempt.py:270` states
outright, "Never the exit code (BRIEF rule 4)." Reading it as "terminated
voluntarily" put a wrong mechanism into a committed record.

It is also **arm-asymmetric**, which is worse. A Baseline lock reaches
Evals' repeat tripwire and is coded `REPEAT_LIMIT`; an Engine lock is cut
by the engine's *own* loop breaker, exits 0, and is coded `OK` whenever any
edit had landed. One `depth-3` cell ended `"customType": "loop_broken",
"terminate": true` after nine identical edits and was counted as a
voluntary stop.

**Ask:** does this field mean what its name suggests, in *both* arms? Read
the assignment site. For stopping behaviour the evidence is the
transcript's own `stopReason`, never the attempt code.

Records:
[False completion](../superpowers/research/2026-09-07-false-completion.md) §7.3.

---

## "The per-arm table shows a huge difference in that column"

Two census columns cannot be read across arms. `detect_anchor_refusal`
keys on `details.satyrn`, an Engine mutator marker a bare-pi transcript
cannot carry; `detect_noop_edit` keys on pi's own edit-refusal strings,
which Engine never emits. So "Engine 25 / Baseline 0" and "Baseline 11 /
Engine 0" are plausibly the *same event* counted through two arm-specific
vocabularies — printed in adjacent columns of a per-arm table, which
invites exactly the comparison they cannot support.

**Ask, of any per-arm count:** could this detector fire on *both* arms at
all? A structural zero is not an observation. This is `BRIEF.md` rule 8's
shape arriving through the reporting layer rather than the detector.

Record:
[V15 premise correction](../superpowers/research/2026-09-07-v15-premise-correction.md) §4.

---

## "The task we need doesn't exist yet"

A phase proposed authoring `depth-1` — a one-seam variant derived from
`depth-3`'s base by un-seeding two defects. It already shipped, as
`plausible-wrong-fix`. Its base differs from `depth-3`'s only in those two
un-seeded defects and the package name, and nobody had run `diff -r` over
the two trees. Relatedly, `depth-2` and `depth-3` were described in a
handoff brief as single-anchor repairs while being a byte-identical nested
2- and 3-seam ladder.

**Ask, before authoring any fixture:** `diff -r` it against every existing
task's `base/`, and read the known-good patches rather than the task names.
The suite is smaller than its documentation suggests and the names carry
more meaning than they appear to.

Record:
[V15 premise correction](../superpowers/research/2026-09-07-v15-premise-correction.md) §1 and §8.
