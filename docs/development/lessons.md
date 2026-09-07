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
quality floor from V11c until 2026-09-07. It is not hard. Its graded
acceptance suite checks four things; the suite the agent can actually run
in its workspace checks one. Two of three seams are unobservable from
inside the task, and the seam nobody closed is a two-line change the
contract names explicitly.

**Ask:** can the agent *verify* the thing being graded, using only what is
in its workspace? A floor that appears in every arm at once is a property
of the task before it is a property of the agents.

**Check it:** compare the task's `expected_test_ids` against what its
`base/tests/` can actually detect.

Record:
[V15 premise correction](../superpowers/research/2026-09-07-v15-premise-correction.md) §7.

---

## "The agent said it was done, and it was wrong"

**False completion.** Distinct from the read-lock attractor, and its mirror
image: rather than never stopping, the agent stops early and declares
success. In one interleaved batch, **33 of 34 failing cells** on tasks with
an unobservable seam terminated *voluntarily* (`OK`) with their public
suite green, against **0 of 9** on the task whose seam that suite can see.
Both arms equally.

Every mechanism this project has measured — loop breaker, bounded mutator,
model-invocable test runner — targets an agent that will not stop. Nothing
targets one that stops too soon, and no census detector names it.

**Ask:** of the failing cells, how many exited `OK`? A high count is not
reassuring; it means they believed they were finished.

Record:
[False completion](../superpowers/research/2026-09-07-false-completion.md).

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
