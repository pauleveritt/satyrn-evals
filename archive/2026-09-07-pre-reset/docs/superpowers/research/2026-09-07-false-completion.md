> **Archived pre-reset record (2026-09-07).**
>
> Original claims, decisions, and instructions may be superseded. This file is evidence, not current guidance.
> For current guidance, read root AGENTS.md, BRIEF.md, and ROADMAP.md. Retrieve one named record when it bears on a concrete question; do not preload this archive.

# False completion: the agent stops, satisfied, while graded-failing

> **REFUTED 2026-09-07, the same day, by an adversarial review — see §7.**
> The observations in §1 are sound and the arithmetic holds. **The
> mechanism, the name, and the experiment this record proposed are all
> wrong**, and the text is kept unedited beneath this banner because a
> correction is recorded, not edited away (`CLAUDE.md`). Two things kill
> it: `depth-3` at rung **R3** passes **12/12** with the same blind public
> suite, and inside the very batch this record was built from, two
> *equally invisible* seams closed at **13/23** and **0/23**. The
> discriminator is how well the contract **describes** the defect, not
> whether the workspace can **verify** it. Do not cite §2, §3 or §5.

**Recorded 2026-09-07.** A second failure mode, distinct from the read-lock
attractor and not addressed by any mechanism this project has measured. No
model ran to find it; it is computed from cells already on disk. Every
number carries the command that recomputes it.

Continues
[the V15 premise correction](2026-09-07-v15-premise-correction.md) §7,
which established that `depth-3`'s workspace suite cannot observe two of
its three graded seams. This record establishes what the agents then do
about it.

## 1. The contrast

One interleaved batch, `~/satyrn-smokes/2026-09-07-v14b-133236`, `n=12` per
arm per task, R1, `gemma-4-12B-it-MLX-8bit`, engine `8b52de9`. Restricted
to cells whose **verdict is not `pass`**:

| task | graded seams invisible to the workspace suite | failing cells | terminated voluntarily (`OK`) | final public-suite result |
|---|---|---|---|---|
| `depth-2` | 1 of 2 | 10 | **10** | GREEN |
| `depth-3` | 2 of 3 | 24 | **23** | GREEN (23), RED (1) |
| `misleading-locus` | 0 of 1 | 9 | **0** | RED |

`misleading-locus`'s nine failures were all terminated by the harness — 8
`REPEAT_LIMIT`, 1 `NO_PATCH`. **Not one stopped of its own accord.** On the
two tasks carrying an unobservable seam, **33 of 34 failing cells exited
`OK`**, voluntarily, with the only oracle available to them reporting
success.

Recompute (both tables, over `attempt.json` `code` and `receipt.json`
`verdict`, and over the last pytest summary line in `transcript.txt`):

```bash
cd ~/satyrn-smokes/2026-09-07-v14b-133236
# termination code of every failing cell, by task and arm
python3 - <<'PY'
import json, glob, os
from collections import Counter
rows = Counter()
for task in sorted(os.listdir('.')):
    if not task.startswith('agentclinic'): continue
    for cell in sorted(os.listdir(task)):
        if not cell.startswith('cell-'): continue
        rp = glob.glob(f'{task}/{cell}/*/receipt.json')
        if rp and json.load(open(rp[0]))['verdict'] == 'pass': continue
        ap = glob.glob(f'{task}/{cell}/*/attempt.json')
        code = json.load(open(ap[0]))['code'] if ap else 'none'
        rows[(task, cell.rsplit('-', 1)[1], code)] += 1
for k in sorted(rows): print(k, rows[k])
PY
```

## 2. Why this is a different failure mode

The project has one named failure mode of its own, the **read-lock
attractor**: an agent repeats an identical read and never converges, and
the harness kills it. Everything measured to date targets that shape — the
loop breaker, the bounded mutator, and the model-invocable test runner all
address an agent that will not stop.

This is its mirror image. Call it **false completion**: the agent stops,
declares success, and is wrong. `depth-3`'s `cell-004-engine` states it
without being asked:

> "`test_complaint_model_contract_is_preserved`: Verified by running the
> test suite. The `Complaint` model in `models.py` remains intact. […] All
> tests passed successfully."

The two modes are cleanly separated in this batch and by termination code:
`REPEAT_LIMIT`/`NO_PATCH` for non-completion, `OK` for false completion.
They do not co-occur.

**It is not arm-differential.** On `depth-3` the voluntary terminations are
11 Baseline and 12 Engine. Neither arm's surface addresses it, and no
census detector names it.

## 3. The uncomfortable version, stated as a hypothesis

The model-invocable test runner was credited with closing Engine's deficit
(V13e, V13f) and generalising (V14b, used in 36/36 cells). On a task whose
seams the suite can see, a runner tells the agent when it is done. On a
task whose seams it cannot, **the same runner tells the agent it is done
when it is not.**

Both arms have the signal — Baseline reaches it through `bash` — so this is
about the signal, not the tool, and the counts above show no arm
difference. But it means "give the agent a test runner" is not
unconditionally good, and its value depends on a property of the *task*
that no arm controls.

**This is a hypothesis.** What is established is the 33/34 against 0/9
contrast in §1. The causal claim is not established and must not be
restated as though it were — that is this project's recorded failure mode,
eight times over
([the V15 premise correction](2026-09-07-v15-premise-correction.md) §3 and
the [next-agent brief](2026-09-07-next-agent-brief-post-v15.md)).

## 4. What it discriminates against

`BRIEF.md` rule 8 requires a detector to fire on a known-bad and stay
silent on a known-good **from the same batch**. This contrast does:

- **Fires:** `depth-2` and `depth-3`, seams invisible, 33/34 voluntary
  terminations on a green suite.
- **Silent:** `misleading-locus`, seam visible, 0/9.

All three tasks are in one interleaved batch, same rung, same model, same
engine commit, so the comparison is within-batch throughout.

**The confound to record.** `misleading-locus`'s failures are read-lock
cells that never produced a working edit, so their suite is red partly
because they fixed nothing. The contrast is therefore between *failure with
false confidence* and *failure with known incompleteness* — which is the
distinction that matters — but it is not a clean manipulation of visibility
alone. Only the experiment in §5 is.

## 5. The prediction this licenses

A task variant identical to `depth-3` except that its workspace suite
covers a currently-invisible seam.

> **If seam visibility is the mechanism, that variant's failing cells stop
> being `OK`-terminations** — they either pass, or they are killed with a
> red suite, as `misleading-locus`'s are.

This is preferable to the outcome measure first proposed ("does it move off
0/12") on two counts: it is a statement about mechanism rather than rate,
and it is readable at `n=12` without depending on the success rate moving
at all. It also fails loudly — a variant whose failing cells still exit
`OK` on a green suite refutes the hypothesis outright.

Design proposal to follow, per `CLAUDE.md`. No task is authored by this
record.

## 6. Terminology

**"False completion" is used here and is not yet in
[`docs/glossary.md`](../../glossary.md).** `ROADMAP.md`'s concept budget
says a term earns its place when the phase that needs it lands, and that
phase has not landed. It is a glossary candidate, recorded as one rather
than added.

## 7. What refuted this, recorded the same day

An adversary was asked to attack this record before any cell was spent. It
succeeded on three independent grounds, each verified at source before
being written down here.

### 7.1 Two equally invisible seams close at wildly different rates

Recomputed over the same 23 graded `depth-3` cells this record was built
from:

| seam | visible to the workspace suite? | closed |
|---|---|---|
| `app.py` (307 → 303) | yes | **22 / 23** |
| `templates/base.html` (`lang`) | **no** | **13 / 23** |
| `models.py` (tz-aware timestamp) | **no** | **0 / 23** |

Both unobservable seams are unobservable in exactly the same way.
Visibility cannot produce 13/23 against 0/23. What differs is the R1
contract: it names `test_home_html_element_declares_english_language` —
a test name that describes its own defect — and gives the timestamp seam
only `assert None is not None`.

### 7.2 A control was already on disk, and this record failed to cite it

`depth-3` at rung **R3** passes **6/6 at each of the two Gemma capability
points**, and **every** patch touches all three files including
`models.py`. The comparison is **within that one batch**: the same night,
the same reference arm, the same models read R1 at **0/6** and **0/6**:

```bash
for d in ~/satyrn-smokes/2026-09-06-overnight-232554/*depth-3*R3*; do
  echo "== $(basename $d)"
  grep -h '^+++ b/' $d/cell-*/*/patch.diff | sort | uniq -c
done
```

Same base, same seeded defects, **same blind public suite**; only the
contract text differs. R3 states the defect in words — "the model's stored
complaint timestamp lost its timezone" — and names where the defects live.
`ROADMAP.md:26-28` already recorded that R3 ceilings almost everywhere.
The evidence that refutes this record was read by its author earlier the
same session and not connected. That is `BRIEF.md` rule 7 for the third
time in one day.

### 7.3 `OK` does not mean "voluntary"

The central framing — "terminated voluntarily (`OK`)" — misreads the
attempt code. `AttemptCode.OK` means *a patch and transcript existed and
grading ran*; `attempt.py:270` says in terms, **"Never the exit code
(BRIEF rule 4)."** It carries no information about whether the agent chose
to stop.

Worse, it is **arm-asymmetric**: a Baseline lock reaches Evals' repeat
tripwire and is coded `REPEAT_LIMIT`, while an Engine lock is cut by the
engine's *own* loop breaker, exits 0, and is coded `OK` whenever any edit
had landed. The review found `depth-3/cell-008-engine` ending with
`"customType": "loop_broken", "terminate": true` after nine identical
edits — a harness kill this record counted as a voluntary stop, and in
fact the single "RED" cell §1 lists as its exception. So §2's claim that
the two modes "do not co-occur" is false, and any criterion built on the
attempt code measures different things in the two arms.

### 7.4 The control arm was structurally empty

§4 claimed to satisfy `BRIEF.md` rule 8. It does not. `misleading-locus`
has **no graded-fail cell** — its nine non-pass cells are all refusals — so
the statistic "code == `OK` among non-pass" cannot fire there at all. That
is a structural zero read as an observation, which is the shape recorded in
[the V15 premise correction](2026-09-07-v15-premise-correction.md) §4 and
in `docs/development/lessons.md` by the same author, one entry earlier.

### 7.5 What survives

- `depth-3` **is not a quality floor.** This is now much better supported
  than by anything in this record: R3 reads 12/12 with all three seams
  closed.
- The public suite **is** blind to two of three graded seams, and failing
  cells **do** end on a green suite. Both are facts; neither carries the
  causal weight put on them.
- The withdrawn V15a experiment — a `depth-3-visible` variant — **is not
  run.** It was designed to test a mechanism the R3 cells had already
  falsified, and its most likely outcome was uninformative besides.
