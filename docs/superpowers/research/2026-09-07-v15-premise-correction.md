# V15's premise is refuted by retained cells, before any authoring

**Recorded 2026-09-07.** A correction, not an edit: the V15 handoff brief
and the `ROADMAP.md` V15 row are left standing and are refuted here. No
model ran to produce anything below. Every number carries the command that
recomputes it.

## 1. What the brief claimed, and what the fixtures say

The V15 brief opens:

> The suite is five single-file, single-anchor repair tasks on a toy Flask
> app. [...] a single-anchor repair is a few hundred tokens of work — there
> is nothing for an engine to coordinate.

Both halves are wrong at source.

**The app is FastAPI, not Flask**
(`src/satyrn_evals/tasks/agentclinic-repair-misleading-locus/base/app.py:3`).
Cosmetic, recorded for completeness.

**The tasks are not single-file.** `depth-2` and `depth-3` are named for
their seam count:

```bash
for t in depth-2 depth-3 misleading-locus plausible-wrong-fix; do
  echo "== $t"
  grep '^+++ b/' src/satyrn_evals/tasks/agentclinic-repair-$t/fixtures/known-good.patch
done
```

| task | files in known-good | seams |
|---|---|---|
| `misleading-locus` | `app.py` | 1 |
| `plausible-wrong-fix` | `app.py` | 1 |
| `depth-2` | `app.py`, `templates/base.html` | 2 |
| `depth-3` | `app.py`, `models.py`, `templates/base.html` | 3 |

A 1/2/3-seam ladder on one application already exists, and V14b ran it at
`n=12` per arm, interleaved, in one batch
(`~/satyrn-smokes/2026-09-07-v14b-133236/RESULT.md`). The phase proposed to
build what was already built and already measured.

This is `BRIEF.md` rule 7's exact shape — a conclusion restated rather than
re-derived. `ROADMAP.md:188` carries the same "single-anchor" wording.

## 2. Partial application is real, observed, and symmetric across arms

> **Superseded in part by §7, and left standing.** The observations in
> this section hold. The word *partial application* does not: §7 shows
> the cells stop because the workspace's only runnable oracle reports
> success, not because they fail to carry a change across files.

The V15 design proposal named **partial application** — the model edits one
layer and never reaches the others — as the pathology to induce. It does
not need inducing. It is already the dominant behaviour on `depth-3`, and
it is the same in both arms.

```bash
cd ~/satyrn-smokes/2026-09-07-v14b-133236/agentclinic-repair-depth-3
for p in $(find . -name patch.diff); do
  echo "$(basename $(dirname $(dirname $p)))|$(grep '^+++ b/' $p | sed 's|+++ b/||' | tr '\n' ',')"
done | sort
```

**0 of 23 retained patches touch `models.py`** — 0 of 12 Engine, 0 of 11
Baseline. (The 24th cell, `cell-022-baseline`, is `REPEAT_LIMIT` and
retained no patch.)

Three facts rule out the cheap explanations:

1. **It was not undiscoverable.** All **24 of 24** transcripts mention
   `models.py`:
   `for t in $(find . -name transcript.txt); do grep -q 'models\.py' "$t" && echo hit; done | wc -l`
2. **It was named in the contract.** `depth-3`'s R1 text names the failing
   check for that seam explicitly —
   `test_complaint_model_contract_is_preserved`, failing
   `assert None is not None`
   (`src/satyrn_evals/tasks/agentclinic-repair-depth-3/manifest.json`,
   `contracts.R1`).
3. **It was not hard.** The seam is a two-line change: import `timezone`
   and wrap the `default_factory` in a lambda
   (`fixtures/known-good.patch:14-30`).

The models read the file, were told which check it broke, and did not edit
it — in every cell of both arms.

**And touching it is not enough.** The same re-score over V13c — same task,
same rung `R1`, same `n=12` per arm, so a replication and never pooled with
the above — records **3 of 24** cells that *did* touch `models.py`
(Baseline 2, Engine 1). None of them closed the seam, and the verdict there
is 0/12 in both arms as well. So the seam resists both shapes of failure:
cells that never reach it, and cells that reach it and get it wrong. Note
that V13c ran engine `b977941`, pre-runner, against V14b's `8b52de9`, so
only the **Baseline** arm is configuration-identical across the two — and
Baseline's "touched all three seams" count is 2/12 there against 0/11 here,
a clean demonstration of why cross-batch counts are not compared.

## 3. The proposal's arm-difference prediction is refuted by the batch it cited

The proposal predicted: *more seams means more to read, and Engine's
advantage is read-lock resistance*, citing V14b's Baseline 8/12 versus
Engine 1/12 lock asymmetry.

`uv run satyrn-evals census ~/satyrn-smokes/2026-09-07-v14b-133236`

| task | seams | `read_lock` Baseline | `read_lock` Engine |
|---|---|---|---|
| `misleading-locus` | 1 | **8** | **1** |
| `depth-2` | 2 | 0 | 0 |
| `depth-3` | 3 | 0 | 0 |

Within this batch the read-lock attractor occurs **only on the one-file
task** and is absent from both multi-file tasks. The prediction is
backwards: the asymmetry that motivated it does not survive the addition of
a second file.

**Scope, stated deliberately.** That is a within-V14b reading, which is the
only comparable kind. `read_lock` is not identically zero on multi-file
tasks in every batch — V13c's `depth-3` Engine cells read 3
(`uv run satyrn-evals census ~/satyrn-smokes/2026-09-06-v13c-200158`). The
claim here is about the arm *asymmetry* inside one interleaved batch, not
about the detector's absolute rate.

This is the shape the V15 brief itself lists as trap 3 — a finding from
cells of one task, stated generally, with a third task showing the
opposite. It is recorded here as a fourth instance of the same error, made
by the agent writing this document.

## 4. A new instrument finding: two census columns are not cross-arm comparable

The remaining columns that *look* arm-differential on the multi-file tasks
cannot be read across arms.

- `detect_anchor_refusal` keys on `details.satyrn is True and
  details.ok is False` (`src/satyrn_evals/census.py:172-182`).
  `details.satyrn` is an **Engine mutator marker**; a bare-pi transcript
  cannot carry it. Baseline's `0` is structurally impossible, not observed.
- `detect_noop_edit` keys on `toolName == "edit"` plus pi's own refusal
  strings — `no change`, `no matching text`, `could not find the exact
  text` (`src/satyrn_evals/census.py:224-233`). Engine's edit tool refuses
  through the `details.satyrn` path instead, so Engine's `0` is likewise
  near-structural.

The two are plausibly **the same underlying event** — a failed anchor match
— counted through two arm-specific vocabularies and printed in adjacent
columns of a per-arm table, which invites precisely the cross-arm reading
they cannot support. That is `BRIEF.md` rule 8's named shape.

**Consequence for V15:** the census offers no pathology that is both
arm-differential and present on a multi-file task. `read_lock` is 0/0 at
two and three seams; `anchor_refusal` and `noop_edit` are arm-specific
instruments.

**Consequence for the instrument:** this is re-scorable from retained
transcripts, so by `CLAUDE.md`'s stopping rule it blocks nothing and is
recorded rather than fixed ahead of authorized work. It is not a defect in
any published count — no V14b or V13c claim rests on a cross-arm reading of
those two columns — but the table's shape invites one.

## 5. What the retained data says instead

| seams | task | Baseline | Engine | Fisher one-sided |
|---|---|---|---|---|
| 1 | `misleading-locus` | 4/12 | **11/12** | p = 0.005 |
| 2 | `depth-2` | 6/12 | 8/12 | p = 0.340 |
| 3 | `depth-3` | 0/12 | 0/12 | — |

Source: `~/satyrn-smokes/2026-09-07-v14b-133236/RESULT.md:11-14`, one
interleaved batch, so these three rows are within-batch comparable.

**Engine's advantage is largest at one seam and gone by three.**

**The caveat that binds this reading.** These are three *different tasks*,
not one task with seam count varied. Seam count is confounded with
everything else about them, and the V15 brief's own caution applies —
Baseline's `misleading-locus` rate reads 0.50, 0.58 and 0.33 across
batches, so the 1-seam row caught its low end. This is suggestive of a
convergence, **not** a dose-response, and no monotonic claim is made. It is
recorded because it is sufficient to refuse the proposed design, not
because it establishes a trend.

## 6. The re-score: `seams_closed` earns its place on exactly one rung

The V15 proposal argued that a graded seam measure would convert a
Bernoulli into a count and buy power at `n=12`. It was computed over the
retained cells rather than argued:

```bash
uv run python scripts/rescore_seams.py ~/satyrn-smokes/2026-09-07-v14b-133236
```

| seams | task | arm | touched dist | closed dist | mean closed/n | verdict |
|---|---|---|---|---|---|---|
| 1 | `misleading-locus` | baseline | 1:4, unmeasured:8 | 1:4, unmeasured:8 | 1.000 | 4/12 |
| 1 | `misleading-locus` | engine | 1:11, unmeasured:1 | 1:11, unmeasured:1 | 1.000 | 11/12 |
| 2 | `depth-2` | baseline | 1:1, 2:11 | 1:6, 2:6 | 0.750 | 6/12 |
| 2 | `depth-2` | engine | 1:3, 2:9 | 1:4, 2:8 | 0.833 | 8/12 |
| 3 | `depth-3` | baseline | 1:4, 2:7, unmeasured:1 | 1:5, 2:6, unmeasured:1 | 0.515 | 0/12 |
| 3 | `depth-3` | engine | 1:3, 2:9 | 0:1, 1:4, 2:7 | 0.500 | 0/12 |

The seam map validated: **no seam was ever closed in a cell that did not
touch its file**, across all 72 cells. That silence is only evidence if the
check can speak, so it was shown to discriminate in both directions
(`BRIEF.md` rule 8) against a hand-built known-bad and its known-good
sibling — a seam marked closed with an empty `touched` set produces
`seam 'models.py' closed but not touched`, the same seam with its file
touched produces nothing, and an `unmeasured` seam yields `n_closed is
None` rather than `0`. The script carries **no committed test**; it is
marked a W1 deletion candidate in its own docstring, and if it outlives
this correction it owes one. Ten cells are `unmeasured` for
`seams_closed`; all are `REPEAT_LIMIT`/`refused` with no patch harvested
(`attempt_pi.py:30-33` — the diff is taken only after pi exits), so what
they touched is genuinely unknown rather than zero.

**Three readings, and only one of them is good news for the measure.**

1. **At one seam it is degenerate and actively misleading.** Mean
   `closed/n` reads **1.000 for both arms** while the verdicts are 4/12 and
   11/12, because the measure is conditional on a cell that produced a
   patch and every such cell closed the only seam there is. A mean of 1.000
   over an arm that failed two-thirds of its cells is the harvest index's
   "suspiciously clean" shape. The script reports the eight unmeasured
   cells rather than absorbing them, which is the only reason this is
   visible.
2. **At two seams it carries no information the verdict lacks.**
   `closed == 2` holds in exactly the cells that pass — 6 and 8, matching
   the verdicts exactly. `seams_closed` is `1 + verdict`. The seams are
   closed in a fixed order, so the within-cell correlation is not merely
   high, it is deterministic, and the claimed power gain is nil.
3. **At three seams it is informative, and what it reports is that the
   arms are the same.** Both verdicts are 0/12 — the measure is the only
   thing that separates the cells at all — and it separates them into
   **0.515 against 0.500**. No cell in either arm ever closed three seams.

So the measure is worth having only where the verdict is floored, and there
it says the arms are indistinguishable. That is the design's own declared
falsifier — *"if `seams_closed` falls equally in both arms as seam count
rises, the app is merely harder and V15's premise is refuted"* — met from
data that already existed.

## 7. The seams are invisible to the only oracle the model can run

Added after a second adversarial review, which attacked the follow-up plan
and found the mechanism instead. **This supersedes the reading in §2**:
what looks like a coordination failure is a model stopping correctly on a
blind signal.

`depth-3` grades on four acceptance checks. The runnable suite in the
model's workspace — `base/tests/test_app.py`, the one the contract tells it
to use and the one Engine's runner executes — has four tests, and **none of
them can observe two of the three seams**:

```bash
cd src/satyrn_evals/tasks/agentclinic-repair-depth-3
grep -n '^def test' base/tests/test_app.py
grep -c 'lang\|tzinfo\|timezone' base/tests/test_app.py   # -> 0
```

| seam | acceptance check | visible to the public suite? |
|---|---|---|
| `app.py` (307 → 303) | `test_post_complaint_redirects_to_complaints_board` | **yes** |
| `templates/base.html` (`<html lang="en">`) | `test_home_html_element_declares_english_language`, `test_complaints_board_preserves_the_shared_layout` | **no** |
| `models.py` (tz-aware timestamp) | `test_complaint_model_contract_is_preserved` | **no** |

So the loop the cells actually run is: fix `app.py`, run the suite, see it
go green, stop. The cells end that way — `4 passed, 4 warnings` is the last
suite result in the failing cells of both arms
(`grep -o '[0-9]* passed[^"]*' transcript.txt | tail -1` over
`~/satyrn-smokes/2026-09-07-v14b-133236/agentclinic-repair-depth-3`).

`cell-004-engine` states it outright, unprompted:

> "**`test_complaint_model_contract_is_preserved`**: Verified by running the
> test suite. The `Complaint` model in `models.py` remains intact. […] All
> tests passed successfully."

The model was told that check was failing, ran the only verification
available to it, was told everything passed, and believed it. **That is not
a failure to coordinate. It is correct behaviour against an instrument that
cannot see the target.**

Three consequences, and they run in the project's favour:

1. **`depth-3` is not a quality floor.** It has been recorded as one since
   V11c ("a quality floor, not a capability wall", `ROADMAP.md:183`). It is
   an *unobservable-target artifact*: 0/12 in both arms because the seams
   cannot be verified from inside the workspace, not because the change is
   hard. The seam is two lines.
2. **It explains why the runner does not help.** V13e/V14b established the
   model-invocable runner as used in 36/36 cells and credited it with
   closing Engine's deficit. On `depth-3` it runs the same blind suite, so
   it cannot help, and the census shows it did not.
3. **A hypothesis, not a finding.** Across the four tasks, outcome tracks
   *seam visibility* better than seam count: `plausible-wrong-fix` 1 seam,
   1 visible, 12/12 both arms; `misleading-locus` 1 seam, 1 visible (its
   public suite carries `test_posted_complaint_appears_on_the_board`, which
   is the seam), 4/12 vs 11/12; `depth-2` 2 seams, 1 visible, 6/12 vs 8/12;
   `depth-3` 3 seams, 1 visible, 0/12 both. **This is four tasks with
   everything confounded and is offered as a hypothesis to test, not a
   mechanism.** Stating it any more strongly would be this project's
   recorded error for the fifth time in two days.

The cheap test of it is a task-authoring change, not an engine change:
extend a variant's public suite to cover a currently-invisible seam and see
whether the arms move off the floor. That is a `capture`-level edit,
gradeable offline, and it needs no new machinery.

## 8. What follows

**The proposed V15 design is withdrawn before implementation.** Building a
four-seam application extends a wall already visible at seam three, and
would spend authoring and inference to re-measure it.

The question V15 was formed to ask — *how do we give coordination room to
pay off* — dissolves under §7. The arms do not stop because coordination is
hard; they stop because the workspace's only oracle says they are done.

**A follow-up plan to author `agentclinic-repair-depth-1` and run a
controlled 1/2/3-seam ladder was proposed and withdrawn**, for two reasons
found by the second review and verified here:

- **`depth-1` already exists.** It is `plausible-wrong-fix`. Its base
  differs from `depth-3`'s only in the two un-seeded defects and the
  package name (`diff -r` over the two `base/` trees), its known-good
  `app.py` hunk is byte-identical, its overlay and `expected_test_ids` are
  identical, and its R1 names exactly one check.
- **Both ends of that ladder are saturated.** `plausible-wrong-fix` reads
  12/12 vs 12/12 in two separate batches (V13e, V13f) and `depth-3` reads
  0/12 vs 0/12 in two (V13c, V14b). A ladder whose endpoints are pinned to
  ceiling and floor cannot show a dose-response at any `n`.

The next move is therefore **neither** a second application **nor** an
engine change, but a task-authoring test of §7's hypothesis, at no
inference cost until it is worth spending.

**Not concluded here**, and left open deliberately:

- Whether the convergence is real or an artifact of three unlike tasks. A
  controlled test would vary seam count within one task.
- Whether the V16 §6 stopping rule ("a second application only if fewer
  than two of at most four probed variants are admitted") has been met. It
  appears not to have been — V14b admits at least two on the recorded axes
  — and V15 proceeded without reconciling that. Recorded as an open
  contradiction, not resolved.

## 9. Unverified claims from the adversarial review, not repeated as fact

The review that opened this correction also asserted that the Engine arm
receives a `bash` tool through `runner.ts`, making `arms/engine.json`'s
`tools` list a mis-description of the arm. That is in the `satyrn-engine`
repository, was not opened, and is **not** relied on anywhere above. If
true it is a `CLAUDE.md` condition-(d) recording gap and should be checked
before the next batch.

Its `scripts`+`arms` line count (1,591) also disagrees with the count taken
here (2,096); the globs differ and nothing rests on either.

## 10. Provenance

The design that this document refutes was proposed in session on
2026-09-07 and never implemented. The adversarial review that found the
first three items was dispatched deliberately to a separate context, per
the V15 brief's rule that the reviewer "must not be the same context that
formed the belief". Item 4 was found while verifying that review rather
than accepting it.

## 11. Appendix: the superseded `ROADMAP.md` V15 status, verbatim

`ROADMAP.md`'s V15 row was amended on 2026-09-07 and its prior status cell
would not fit under the phase-table character cap (`just lint-docs` refused
it at 2,257 against 1,000). It is preserved here in full instead of being
edited away, per `CLAUDE.md`. Recovered with
`git show 96a470c:ROADMAP.md | grep '^| V15 |'`.

> **unblocked 2026-09-07; the next content phase.** The instrument answered a p = 0.005 difference, a null and a floor in one 80-minute batch, so the constraint is content: five single-anchor repairs oscillating between 12/12 and 0/12 leave an engine nothing to coordinate. **One** app, graded ladder, pathology named before authoring, candidates probed at `n=6`. Old trigger **refuted** (2026-09-06) — the wording above assumes the 26B-A4B point exhausts the suite first; the staged profile refuted that ordering (the 26B is *worse* on `depth-2` R1, 1/6 against 3/6), and nothing in V13, W1 or the headroom proposal runs a build rung to test it. The old wording stays visible until **the headroom proposal rewrites this row**, keyed to tasks rather than a model — reopening when no task on the current app places any compared pair in different bands, which is the admission rule's own question

Of that text: the first sentence's premise is refuted by §1 and §7 above;
the "floor" is withdrawn by §7; and the 2026-09-06 "old trigger refuted"
note it carries is untouched by this correction and remains true.
