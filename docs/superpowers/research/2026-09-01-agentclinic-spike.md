# AgentClinic as a V5 workload — spike

**Date:** 2026-09-01
**Status:** spike; no task admitted; **recommend proceeding, but not as
originally framed**
**Model:** `omlx/gemma-4-12B-it-MLX-8bit`
**Pi:** 0.84.4
**Arm:** bare Pi plus SLM; no Engine, extensions, skills, context files, or
handoff contract; tools `read,bash,edit,write`

This is a decision record, not an admission record. It answers: is an
AgentClinic-based suite worth building, what should be built, and where the
inputs live. It does **not** start V5 or add a baseline field to any manifest.

## Decision

**Do not admit AgentClinic-from-roadmap as a V5 diagnostic workload.** As
specified by `roadmap.md`, it is at ceiling for this model: four independent
3-prompt sessions each completed all three phases (`deepest_pass` 3, 3, 3, 3),
and a single-shot Phase 1 probe passed 4/4. Under the probe rule (n=4; stop at
0/4 or 4/4) this stops at four; no extension to n=6 is warranted.

**Do proceed** with a follow-up phase, on a narrower premise: AgentClinic's
value is not the app, it is that the same app ships with **three prompt
variants at different prescriptiveness levels** plus a set of **seeded repair
bugs**. Those are headroom levers that nothing in the prior project had. The
suite that `BRIEF.md` says this project still owes is more likely to come from
the least-prescriptive variant or the repair fixtures than from building the
app again.

## Where the inputs are

Everything already exists. **Nothing needs to be authored from scratch**, and
the best copies are not in `local-ai-pi`.

| Input | Location |
| --- | --- |
| Full 3-phase specs, both variants | `local-ai-pi` branch `pre-restructure`, `examples/agentclinic/specs/` |
| 3-phase references + per-phase cumulative acceptance suites | `local-ai-pi` branch `pre-restructure`, `examples/reference/phase-{1,2,3}`, `examples/acceptance/phase-{1,2,3}` |
| **Best packaged fixture set** | a private companion repository (contents not reproduced here) |

`local-ai-pi`'s `main` keeps **only Phase 1** (`examples/agentclinic/phase-1/`);
Phases 2 and 3 must come from `pre-restructure` or from `swiftstar`.

The private companion repository holds a better-packaged copy than
`local-ai-pi`, and should be preferred over re-deriving. Its contents are not
reproduced here; the shape is:

- `acceptance/test_acceptance.py` — one cumulative 13-test suite, harness-owned.
- `reference/` — the full 3-phase solution; `broken/app.py` — bare app.
- `specs/` — `roadmap.md`, `roadmap-user-story.md` (a **later, prose-ified
  revision** of the `pre-restructure` copy, with a "Shared data model"
  preamble), and `roadmap-user-story-mellum-decomposed.md` (a **more**
  prescriptive decomposition).
- `repair/` — six seeded broken states (`depth-2`, `depth-3`, `framing-2`,
  `framing-2-edit`, `misleading-locus`, `plausible-wrong-fix`), **authored
  there, not transplanted**, specifically to close a gap its README names:
  every bug tested until then had a traceback quoting its own defective line
  and a single canonical fix.
- a provenance record naming the `local-ai-pi` commits each file was recovered
  from, and the dependency pins.

## What was measured

Two probes, both through the real Evals path (`capture`, `attempt`, `grade`),
bare Pi as the attempt command, artifacts preserved before grading.

### Single-shot Phase 1 — a dependency-pin dial, not a confound

| Environment | Result |
| --- | ---: |
| unpinned `--with fastapi` (resolved Starlette 1.6.0) | 0/4 |
| pinned `fastapi[standard]==0.115.10` (`local-ai-pi`'s own pin) | 4/4 |

All four unpinned attempts failed **identically**: the model wrote
`templates.TemplateResponse("home.html", {"request": request})`, the older and
far more common idiom, which the pinned Starlette accepts and the new one
raises on. The reference solution uses the newer positional form.

This was first recorded here as a harness confound. That reading is **partly
withdrawn**: the pin is a choice about *what the eval measures*, not an error.
Unpinned measures API-knowledge currency and produces a hard wall with zero
variance across attempts; pinned measures whether the model can build the app.
Neither is middle-band, but they are two ends of a dial. `swiftstar`
independently pins the same versions.

### Cumulative 3-prompt session — ceiling

One Pi session per run, three sequential prompts (Phase 1, 2, 3) against one
workspace, the model building on its own prior work. Measurement fixed before
the runs: the deepest ordered phase whose cumulative oracle passes (0–3).

Recorded `deepest_pass`: **3, 3, 3, 3** across four formal runs, plus a
pipeline validation run that also reached 3. Every phase of every run passed
its full cumulative suite (4/4, 16/16, 14/14).

Two of the four Phase 3 prompts (runs 1 and 3) reached the 300 s per-prompt
timeout and were killed, and **still graded pass** — the workspace already
satisfied the contract when the model was cut off, with the remaining turns
going to its own `tests/test_app.py`. Consequences: the ceiling reading is
unaffected, but per-phase elapsed times are censored at 300 s and must not be
read as a duration distribution, and a timeout in this design is not a failure
signal. Elapsed figures are diagnostic context only, never a comparison claim.

The solutions were genuine, not passing for the wrong reason: **all five
runs** used `await request.form()` rather than the reference's `Form()`
annotations and still satisfied the suite, which is evidence the suite grades
contract rather than implementation. (Corrected: an earlier draft said "one
used", understating its own point.)

## Two defects found in the Evals path

Both are about `capture --revert` meeting **cumulative** acceptance suites.
Neither is a defect in the fixtures.

### 1. Capture reduces a cumulative suite to an unsound oracle

`capture` records only the *discriminating set* — tests failing at base and
passing at fix. For Phase 3 that recorded **3 of 14** tests, discarding every
preservation check, which is the suite's stated purpose.

Demonstrated, not asserted. A patch implementing Phase 3 correctly while
deleting the Phase 1 home route, touching only allowlisted files:

- captured 3-test oracle → **pass**, 3/3
- full 14-test suite → **fail**, 4 failed

The `source_paths` allowlist did block a cruder sabotage that edited
`templates/home.html`, but that is a patch-layer guard, not the oracle, and it
does not stop equivalent damage inside allowed files.

### 2. Capture cannot ingest a phase whose suite imports what that phase creates

`capture --revert` refuses Phase 2 with `ORACLE_ENV`: the cumulative suite does
`import models` at module scope, and `models.py` does not exist at the Phase 1
base, so the base oracle cannot collect. This is structural for cumulative
suites, not a fixture defect. `swiftstar`'s own evidence floor records the same
observation for its bare app.

A consequence worth keeping visible: Phase 2's known-broken therefore grades
`unavailable` (collection error), not `fail` — weaker evidence, and the shape
that has produced silent-zero incidents before. Phase 2's floor is established
instead by a plausible-but-wrong implementation (naive timestamp, altered seed
text), which the suite rejects on exactly
`test_complaint_literal_seed` and `test_complaint_timestamp_has_timezone` and
nothing else.

**Workaround used:** hand-authored manifests whose oracle is the *full*
cumulative suite. Under those, known-good passes (16/16 Phase 2, 14/14
Phase 3), known-broken is rejected, and the sabotage patch above correctly
fails.

## What this does not establish

- ~~Nothing about the **user-story variant**. It was never run. It is the
  single most decision-relevant missing measurement.~~ **Superseded** by the
  later arm below — and by the discovery that `local-ai-pi` had already
  recorded that suite at 15/16 once the same two facts were supplied, so it
  was never the open question this bullet claimed (Correction 9).
- ~~Nothing about the **repair fixtures**. Never run here.~~ **Superseded** — roughly 130 repair cells were run overnight; see
  [the overnight record](2026-09-02-overnight-packet-and-isolation-run.md).
- Nothing about other models. One model, one arm.
- No cross-comparison with `swiftstar`'s recorded numbers: its suite is 13
  tests from commit `8af05f8`; the per-phase suites used here are 14 and 16
  tests from `pre-restructure`. Comparisons *within* these runs are sound;
  comparisons against its figures are not until one vintage is standardized.
- `deepest_pass` records how far a session got, not why it stopped. On a
  mid-band result the diagnosis matters more than the count.

## Recommended next phase

1. **Adopt the private companion repository's fixture set as the input.** Do not re-derive
   from `local-ai-pi`, and do not keep the parallel per-phase copies this spike
   built beyond what the next probe needs.
2. **Probe the user-story variant first**, same protocol, changing only the
   prompt. `roadmap.md` (middle rung) ceilings; `mellum-decomposed` is a
   *more* prescriptive rung, so the least-prescriptive rung is where headroom
   is plausible. n=4, extend to 6 unless 0/4 or 4/4.
3. **Then the repair fixtures**, as a separate probe. A bug whose traceback
   does not quote its own defective line is a different and probably harder
   axis than building from a roadmap.
4. **Decide what `capture` should do with cumulative suites** — either record
   the full suite when the task declares itself cumulative, or document that
   cumulative tasks are hand-authored. Today's silent reduction is the same
   class of defect as the `local-pings` unsound oracle.

One caution, a private companion repository's own audit warns against multiplying independent eval runners and result schemas. The probe runner this spike wrote is a candidate to
become the next one. Prefer extending the Evals path over adding a runner.

## Corrections and later arms, same day

Recorded beneath what they correct, not edited into it.

### Correction 1 — the Gemma ceiling was already recorded here

This document's ceiling result is a **replication, not a discovery**.
[`2026-08-26-product-path-pilot.md:156`](2026-08-26-product-path-pilot.md)
already states that *"the old evidence already places detailed AgentClinic at
a 16/16 ceiling"* for `gemma-4-12B-it-MLX-8bit`. `BRIEF.md` and `ROADMAP.md`
were read before this spike; the research directory was never searched for the
workload name. Roughly eight sessions of model time confirmed a recorded fact.

What survives as new: the two `capture` defects, the framing artifacts, the
`deepest_pass` framing, and the effort spread at fixed verdict.

### Correction 2 — "not worth keeping" was too strong

The decision above says do not admit it as a **V5 diagnostic workload**, which
stands. It should not be read as "discard." A saturated task is still a valid
smoke fixture and the right baseline for smaller models and heavier quants,
and the effort metrics below discriminate where the verdict does not.

### Correction 3 — the dependency pin is a dial, not a harness error

Already noted in the single-shot section; restated here because the original
framing called it my confound. Unpinned measures API-knowledge currency;
pinned measures whether the model can build the app. `swiftstar` pins the same
versions independently.

### Later arm — user story, with `tech-stack.md`

Two framing artifacts had to be cleared first, both of which are **recorded
failure modes in the evidence repositories**, re-derived here (see
[the harvest notes](2026-09-01-handoff-and-eval-harvest.md), §5):

1. The user-story spec, run bare, produced a spec summary, **zero tool calls**
   and an empty patch — it reads as a document to acknowledge, not a work
   order. An imperative was added **to the runner**, and therefore to the
   user-story arms only: the roadmap arm had already completed and was never
   re-run with it (see Correction 5). It fixed the failure it targeted — zero
   tool calls became a complete application — and a different missing fact
   then caused the next failure.
2. With the imperative, the model wrote a **Flask** app with
   `render_template_string` (n=1) and every phase graded `unavailable`. The
   user-story spec names no framework; the stack lives in `tech-stack.md`,
   which the harness had never included. Adding that fact fixed *that*
   failure.

   The earlier draft read this pair as reproducing "facts work; rules of
   conduct do not." That is **withdrawn**: each intervention fixed the failure
   it targeted, and there was no Flask arm before the imperative, so the two
   are sequential repairs rather than a controlled contrast.

With `tech-stack.md` supplied, n=2 per model, 120 s per prompt (a deliberate
reduction from 300 s, recorded because it is binding):

| Arm | `deepest_pass` | Phases that hit the 120 s cap |
| --- | --- | ---: |
| `deepseek-v4-flash` (hosted) | 3, 3 | 1 of 6 |
| `gemma-4-12B-it-MLX-8bit` | 3, 3 | **6 of 6** |

The Gemma column is **withdrawn** — its passes are an artifact of grading in
an environment the model never ran in (Correction 4). The DeepSeek Flash
column stands.

The comparison to the private repository's own prescriptiveness figures is also
**withdrawn as evidence of a dial**: that source records overlapping confidence
intervals and states it does not establish a difference. Its numbers are not
reproduced here — see Correction 8.

**Every Gemma phase was killed at the cap and still graded pass** — the
contract was satisfied before the kill, with remaining turns going to the
model's own tests. Two consequences, both limiting:

- Gemma's elapsed times are **fully censored**; there is no duration
  information in this arm at all, and none is claimed.
- Gemma's turn and tool-call counts are **lower bounds, not completed
  counts**. Comparing them against DeepSeek Flash's mostly-uncensored counts
  is therefore unsound, and the earlier draft of this section overstated it.
  The one comparison that survives is directional: Gemma logged *more* tool
  errors (4 in phase 1) than DeepSeek Flash (0 and 2) **despite** truncation,
  and truncation can only lower a count.

Timeout incidence (6/6 versus 1/6) is a count and is reported as one. It is
not a wall-clock comparison, which `BRIEF.md` forbids and which the local-MLX
versus hosted-API split would confound regardless.

### Effort discriminates where the verdict does not

From preserved transcripts, no model re-run. Baseline roadmap arm, all four
runs `pass` at every phase:

| Phase | turns across runs | tool errors |
| --- | --- | --- |
| 1 | 8, 10, 10, 11 | 1, 3, 3, 3 |
| 2 | 6, 6, 6, 8 | 0, 0, 0, 1 |
| 3 | 22, 7, 24, 11 | 9, 1, 8, 4 |

Phase 3 spans a **≥3.4×** turn range at identical verdicts — "≥" because the
24 and 22 cells are the two runs that hit the 300 s cap, so both are lower
bounds. The censoring caveat applied to the Gemma arm below applies here too;
the earlier draft omitted it.

Phase 1's tool errors are largely `pip: command not found` (7 of 10) — the
model installing what is already installed, because the 3-phase `roadmap.md`
on `pre-restructure` carries no Environment section.

**What the Phase 3 turns were actually spent on** (corrected): not the model's
own test-writing, as first stated. The POST route landed at tool call #2 in
both long runs. What followed was a `TestClient` redirect-following loop — the
model asserted `303`, `TestClient` followed the redirect and returned `200`,
and it spent ~17 further calls "fixing" a redirect that was already correct;
one run ended in `httpx.TooManyRedirects`. This is the **`follow_redirects`
trap**, recorded as lesson #13 in `local-ai-pi` and the cause of its 4/16
Phase 3 hang incident. Incidence here: **2 of 4 baseline runs**. A named
failure mode is the useful unit, not the turn count.

Cross-model tool-error comparison from the user-story arm is **withdrawn**:
Gemma's phase-1 errors are [4, 2] rather than 4, DeepSeek Flash's run-1 phase
1 also hit the cap so its 0 is censored too, and `isError` counts any nonzero
exit — DeepSeek's two are a `find` and a `grep` that matched nothing, while
Gemma's are real application failures. The metric conflates exploration with
breakage.

This is the same shape as the recorded precedent where two prompt variants
differing only in wording scored 16/16 both times while hang incidence went
0/16 → 6/16. On a saturated workload, success rate reports nothing and
incidence does.

## Corrections from adversarial review, same day

Two independent reviews re-executed the load-bearing recomputations and
recomputed every number from the artifacts. Both load-bearing technical
claims — the oracle reduction and the Phase 2 refusal — **survived
independent re-execution**. The grading path was also checked and holds: the
verdict comes from a hook file outside the workspace, `executed == expected`
is enforced, and no spurious pass is constructible from stdout or an exit
code. What follows is what did not survive.

### Correction 4 — the Gemma user-story passes are an environment artifact

Gemma wrote its own `pyproject.toml` (`fastapi[standard]>=0.115.10`), which
resolved to **fastapi 0.141.1 / starlette 1.6.0**, and wrote the old
`TemplateResponse("home.html", {"request": request})` idiom. Its own
`uv run pytest` fails every time with
`TypeError: cannot use 'tuple' as a dict key`. The grader ran under **pinned
0.115.10**, which accepts that idiom, so all six phases graded `pass`.
DeepSeek Flash pinned `==0.115.10` exactly, so its environment matched.

Graded in the environment the model built and tested in — which
`tech-stack.md` instructs — Gemma's user-story arm is plausibly **0/6, not
6/6**. The six timeouts are not effort; they are the model chasing a real
failure the grader could not see.

This is the single-shot pin dial reappearing as a split between the model's
environment and the grader's, and it is the "harness, not the model" class the
harvest documents four instances of. **The verdict is environment-dependent
and no model claim should rest on it until one environment is chosen and
recorded.** `run.json` currently records nothing about the oracle environment;
it should record the resolved versions.

### Correction 5 — the arms differ in four ways, not one

The roadmap arm's prompts contain no imperative; it completed before the
imperative existed and was never re-run. The compared arms differ in: the
imperative, `tech-stack.md` (2,794 versus 1,142 bytes of phase-1 prompt), the
timeout (300 s versus 120 s), and spec vintage (`pre-restructure` versus
`swiftstar`). The runner's "prescriptiveness is the only variable" comment is
wrong and should be struck. No roadmap-versus-user-story sentence in this
document is a controlled comparison.

### Correction 6 — capture broke on one run (BRIEF rule 3)

`user-story-dsflash/run-2` preserved **three zero-byte patches for three
passing phases**. The model ran `git add -A && git commit` itself, moving
`HEAD`, and the runner's `snapshot_patch` diffs `--cached` against `HEAD`. The
work survives only because that workspace's `.git` still exists.

`pi_attempt.sh` carries the identical exposure; in the Evals path it would
surface as a false `fail` on an empty patch. Fix: diff against the recorded
base SHA, never `HEAD`.

### Correction 7 — the user-story phase-1 prompt discloses later phases

`tech-stack.md` plus the "Shared data model" preamble leak Phase 2/3 scope
into the phase-1 prompt. DeepSeek Flash run-1 built **all three phases during
phase 1**; its phase-2 and phase-3 patches are byte-identical. Its p2/p3 turn
counts are verification, not implementation. `deepest_pass` survives; the
per-phase effort reading for that arm does not.

### Correction 8 — the `swiftstar` headroom comparison does not establish a dial

That private source records **overlapping confidence intervals** between its
two arms and states plainly that it does **not** establish a difference — only
that a generalization bar was not reached. Its pass criterion also required a
delegation to have occurred, a stricter bar than acceptance. Its figures are
not reproduced here. "The dial is real" is withdrawn.

Also withdrawn: the claim elsewhere that detailed AgentClinic is saturated for
DeepSeek Flash. **That was never measured** — DeepSeek Flash ran only the
user-story arm, n=2.

### Correction 9 — a fourth re-derivation

`local-ai-pi` had already recorded the **user-story** suite at **15/16** once
the same two facts were supplied, with its roadmap noting the suite "has no
headroom". The later arm here re-derived that. Added to §5 of
[the harvest notes](2026-09-01-handoff-and-eval-harvest.md) as the fourth
instance, and it undercuts the premise that the user-story variant is where
headroom lives.

### Also recorded

- The Phase 3 turn spread is **≥3.4×**; its two largest cells are censored.
- The long Phase 3 runs were a `follow_redirects` misdiagnosis loop, not
  test-writing — a named failure mode at 2/4 incidence.
- Timeout incidence (6/6 versus 1/6) is reported as **per-arm disclosure**,
  not as a comparison column: it is an elapsed-time threshold across a local
  MLX server and a hosted API, and `BRIEF.md` forbids that comparison.
- The Flask arm is **n=1**; the zero-tool-call arm is two complete runs plus a
  partial.
- `run.json` and `grade.json` record no conditions — no dependency versions,
  no oracle environment. Correction 4 is the direct consequence.
- `run_oracle` has no `source_paths` allowlist and grades the whole workspace,
  so a model-written `conftest.py` or `addopts` would be honoured. None was
  present in these runs, but the exposure is real and is the predecessor
  grader's exact defeat.
- The recomputation block below writes `receipt.json` to the working directory
  unless `--receipt` is passed.

## Evidence and recomputation

All artifacts are local and unadmitted: captured tasks, hand-authored task
manifests, **eight** single-shot attempt records (four unpinned, four pinned;
each with patch, transcript and receipt), and four baseline session runs plus
four later-arm runs (per-phase patches, transcripts and grades)
live under this session's scratchpad, not in this repository. The probe runner
and the attempt wrapper are there too.

The two defects above recompute without a model, from preserved artifacts:

```bash
# 1. captured oracle accepts a patch that deletes the Phase 1 home route
uv run --with "fastapi[standard]==0.115.10" --with turbohtml --with httpx \
  satyrn-evals grade agentclinic-phase3 "$SCRATCH/phase3-sabotage2.patch" \
  --tasks-root "$SCRATCH/agentclinic-phase1-task"      # -> pass, 3/3

# ...while the full cumulative suite rejects the same tree
cd "$SCRATCH/sabotage-gen2" && uv run --project <repo> \
  --with "fastapi[standard]==0.115.10" --with turbohtml --with httpx \
  python -m pytest test_acceptance.py -q                # -> 4 failed, 10 passed

# 2. capture refuses Phase 2 on a cumulative suite
uv run --with "fastapi[standard]==0.115.10" --with turbohtml --with httpx \
  satyrn-evals capture --revert <phase2-fix-sha> \
  --repo "$SCRATCH/agentclinic-phase2-capture" --name agentclinic-phase2 \
  --output "$SCRATCH/agentclinic-phase1-task"          # -> refused ORACLE_ENV
```
