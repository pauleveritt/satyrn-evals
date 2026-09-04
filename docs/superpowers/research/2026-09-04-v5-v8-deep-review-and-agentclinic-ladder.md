# Deep review of V5–V8, and the road to an AgentClinic ladder

**Status: DRAFT for maintainer review. Not committed. Not a decision.**
Written 2026-09-04 against `main` @ `a58f583`, from five parallel audits
(code: V7+V8; code: V5b+V6; repository weight; the swiftstar evidence
record; this repository's AgentClinic line and the V8 smoke transcript)
plus direct re-derivation where a number mattered. Every claim carries a
`file:line`; numbers I did not compute myself say who did. Nothing here
reopens the phase list, the diagnosis-before-claims split, or the two
selection rules — it proposes phases *after* V8, inside those rules, and
names the recorded reopen condition wherever it touches a backlog entry.

Path shorthands: `S/` = `docs/superpowers/`; `R/` = swiftstar
`docs/superpowers/research/`; `F/` = swiftstar `fixtures/agenttest/`;
`E/` = satyrn-engine `src/satyrn_engine/`.

## 0. The short version

1. **The instrument is trustworthy on the six bundled tasks, on this
   laptop, in an editable checkout — and the suite it grades is set to
   "easy" by its contracts.** All six shipped contracts state the fix
   (the ladder's L3 rung, `R/2026-08-24-laguna-revision-test-spec.md:43-51`);
   four name hidden test ids; all name the file. The fixtures' own README
   warns that this makes `plausible-wrong-fix` "an L3 cell (fix stated)
   wearing L1 clothes" (`F/repair/README.md:67-76`). The difficulty axis
   the user wants already exists as a design — nobody has run it.
2. **The good prior evidence was not cited.** Swiftstar holds
   pre-registered, TSV-recomputable n=20 rates for Mellum-2.1 Thinking
   (12B-A2.5B) on these exact fixtures — `plausible-wrong-fix` 19/20,
   `depth-2` 12/19, `depth-3` 8/18, `framing-2` ~1/6 — and Laguna S at
   ceiling (`R/2026-08-29-block-b-negative-result-analysis.md:49-60`;
   `R/experiment-results-editing-n20.tsv`). V8 §6's "the only prior signal
   is the confounded overnight block" (`S/specs/…v8…design.md:246-249`)
   is wrong. No 27B-class model has been run on these fixtures in either
   repository.
3. **The admission rule cannot express what the goal needs.** V5a's band
   rule compares two engine arms on one model at n=8 and de-admits when
   both land "middle" (3/8 vs 4/8). It has no power to separate those, and
   it cannot say whether a task is hard *for a 27B*. The goal — easy→hard
   with headroom at 12B and 27B — needs a difficulty profile over a model
   ladder, which nothing in V5–V8 measures.
4. **The pathologies will happen and the instrument will not count them.**
   V5b's transcript metrics were deferred to an engine-side emitter
   (`BACKLOG.md:21-38`); `summary.json` carries verdict counts and
   timeouts only. The V8 smoke transcript shows the engine arm making zero
   test runs (it has no shell) — a capability silently absent, unrecorded.
5. **The V5b loop is the weakest link for a budgeted batch**: no per-cell
   failure boundary, no re-summarize from disk, `attempt.json` written
   only after grading succeeds, summaries that don't name their arm. BRIEF
   rule 3 has no executable form — there is no `regrade`.
6. **About 30% of `workspace.py`/`capture.py` and ~2,000 default-tier test
   lines serve hypotheticals no recorded incident produced**, held in
   place by the 100% branch gate. The session path (1,881 src / 3,481
   test) has one toy consumer today — but it is the right vehicle for the
   build rung, so freeze, don't delete.

Proposed phases: **V9** loop integrity + `regrade`; **V10** pathology
counts from the preserved transcript; **V11** the contract ladder
(R0–R3) + a shipped baseline adapter; **V12** the model-ladder profile;
**V13** build rungs on the same app (single-shot, then session);
**V14** a second application (reopen-conditioned); **W1** weight.

## 1. Evidence from other repositories — what is wrong or unsupported

| # | Claim in this repo | What the source says | Where |
|---|---|---|---|
| E1 | "the only prior signal is the confounded overnight block" (V8 §6) | Block B n=20 per-fixture rates recompute from committed TSVs; P17 n=3/cell; Laguna 3/3 ×2 | `R/2026-08-29-block-b…md:49-60`; `R/2026-08-26-p17-repair-limit-verdict.md:22-39`; `R/experiment-results*.tsv` |
| E2 | "a designed gradient — one-file to three-file fixes … built with headroom as a design axis" (V8 §6) | The fixtures' author overturned it: "DEPTH IS CONFOUNDED WITH DEFECT DIFFICULTY … NO n fixes this"; the `depth-3-easy` control was never built | `R/experiment-manifest-depth3-estimation.tsv` header 27-34; swiftstar `ROADMAP.md:49` |
| E3 | "oracle env differing from the model's (six false passes, spike Correction 4)" attributed to the overnight repair run (V8 §1) | The six false passes are the 09-01 spike's gemma *user-story* arm, not the repair instrument | `S/research/2026-09-01-agentclinic-spike.md:330-349` vs `…overnight…md:194-197` |
| E4 | "V6 and V7 landed the first three [review steps]" (V8 §1) | Step 3 was "make containment genuinely usable, including a test runner"; V7 deferred containment | `S/research/2026-09-02-phase-proposals…md:171-173`; `ROADMAP.md:20-21` |
| E5 | One overnight run, four cell totals: ~130, ~160, 166, ~100 | Never reconciled | spike `:160`; overnight `:10`; proposals `:160`; gap `:184` |
| E6 | Overnight "7/12 vs 11/12" mid-band signal | The two fixtures run are never named; cannot be mapped onto the six | `…overnight…md:49-54, :219-225` |
| E7 | swiftstar cited as `github.com/pauleveritt/swiftstar` (V8 §1) | The repository is **private** (`gh repo view`: `isPrivate: true`); MIT still holds for the vendored content | this session |
| E8 | V8 smoke "passed … after the engine's pi-argv fix" (ROADMAP V8 row; `docs/sdd.md:460-464`) | The fix `d5d5d37` sits on `research/facts-field-backlog`, not an ancestor of the engine's `main` | audit 5, `git merge-base --is-ancestor` |
| E9 | "the model found and fixed the seeded bug" (smoke record `:107-109`) | The prompt stated the file, the assertion, and the value; `writable_paths: [app.py]`; the patch is byte-identical to `known-good.patch` | `~/projects/satyrn-v8-scratch/smoke2-…/engine-contract.yaml`; audit 5 §5 |
| E10 | Ladder rungs assumed for depth/framing fixtures | Only `misleading-locus` and `plausible-wrong-fix` were ever assigned a rung (L1); the ladder itself was "specification only. Nothing run" | `F/repair/README.md:81-83`; `R/…laguna-revision-test-spec.md:5-6` |
| E11 | Redaction makes `plausible-wrong-fix` an L1 cell | The superseding review found redaction is theater — `assert 307 == 303` delivers the answer; the fixture "measures assert-reading, not diagnosis" | `R/2026-08-24-p12-4-repair-role-fable-review.md:29-40, :97-102` |

What *is* solid and should be carried forward: Block B's per-fixture rates
(E1); the "depth is confounded" retraction (E2); "grader-hunting is not
model-specific … including the larger one" (`…overnight…md:204-206`); the
tool-protocol finding — Llama-3.1-8B emits tool calls as text,
Qwen2.5-Coder-7B "correctly diagnosed the bug while scoring zero"
(`:199-203`); Mellum "announces the next action and ends the turn"
(`:194-198`); the agency floor — bare Pi "read the spec, restated it
accurately, and stopped to ask" (`local-ai-pi/docs/evals/slm-struggles.md:82-87`).

## 2. Methodology

**M1. Every contract is L3.** Verbatim, `plausible-wrong-fix`
(`src/satyrn_evals/tasks/agentclinic-repair-plausible-wrong-fix/manifest.json:3`):

> … (assert 307 == 303: the POST response is a 307 Temporary Redirect,
> expected 303 See Other). The seeded defect is in app.py; fix it so the
> redirect is a 303 …

`misleading-locus` hands over the diagnosis ("appends to a copy of the
seed list") for a fixture whose stated purpose is "localization from
behavior rather than from a quoted line" (`F/repair/README.md`). V8 §4
authorized a *digest* (ids + assertion text); the shipped text adds
location and fix. Consequence: the six tasks cannot discriminate anything
the ladder was built to discriminate until the contracts are re-authored
per rung. This is harmless for V8's stated job (grader fixture) and fatal
for the probe the backlog reopens on it (`BACKLOG.md:219-229`).

**M2. Hidden test ids leak in 4/6 contracts.** The public suite names
`test_post_complaint_redirects_to_complaints`
(`…/base/tests/test_app.py:20`); the contract names
`…_to_complaints_board` (`overlay/test_acceptance.py:158`). A model can
infer a second, differently-named suite. The V7 validator checks overlay
*filenames* only (`src/satyrn_evals/manifest.py:91-127`).

**M3. The arms are asymmetric and the asymmetry is unrecorded.** The
engine prompt says "Do not create files"; its tools are `read,edit`
(`E/attempt.py:229-266`). So the engine arm cannot author `models.py`
(`framing-2`'s known-good) and cannot run the public tests V8 §11.7 added
"as the runnable local signal". The smoke transcript: 6 `read`, 2 `edit`,
0 `bash`, 0 pytest; four of eight calls are post-fix re-reads standing in
for a test run (audit 5 §5). The baseline wrapper has `read,bash,edit,write`
(`S/research/2026-09-03-local-pings-reprobe-protocol.md:130`). Any
baseline-vs-engine comparison on these tasks is confounded by tool
surface before the engine's logic is measured.

**M4. The band rule has no power and the wrong domain.** V5a admits a task
when "at least one pair of the arms under comparison [sits] in different
successful-attempt bands" (`S/specs/2026-09-02-v5a-admission-rule-design.md:94-97`).
The captured `local-pings` re-probe recorded Baseline 3/8, Engine 4/8,
"both middle", and the task was de-admitted
(`S/research/2026-09-03-local-pings-deadmission.md:12-22`). At n=8 with
three bands, 3/8 and 4/8 are indistinguishable from each other *and* from
2/8 or 5/8; "no pair separates" was read as "does not discriminate". The
reprobe record itself lists "a revised band rule" as a candidate reopen
condition (`…reprobe-protocol.md:266-267`), so this is inside the rules to
raise. Separately: the rule is defined over engine arms on one model; the
goal is defined over model sizes. It cannot say "hard for a 27B".

**M5. Wall-clock in disguise.** Cell directories are microsecond UTC
stamps listed verbatim in `summary.json` `cells`
(`src/satyrn_evals/attempt.py:75-78`, `summary.py:111`); consecutive deltas
are durations, and two arm summaries side by side invite the comparison
`BRIEF.md:39-40` forbids. Two integration tests assert elapsed seconds
(`tests/integration/test_session_run.py:557-559`,
`tests/integration/test_adapter_process.py:91`).

**M6. Known-broken adversaries drifted from plan to ship, unrecorded.**
`misleading-locus`'s known-broken slices the template
(`complaints[1:]`) — a strawman unrelated to the fixture's predicted
wrong-locus edit; the plan's intent (`S/plans/…v8-p2…md:257`) was actually
the reference fix. Four of six intents (`:255-262`) differ from what
shipped; only `PROVENANCE:7` and commit `4ecb4c9` record it.

**M7. The identity assertion in the V6 smokes is a tautology.** The
adapter mints `pi-<uuid>` once (`src/satyrn_evals/adapters/pi_session.py:328`);
Pi is never asked for a session id. "One stable conversation identity"
(`docs/sdd.md:218-219, :340-341`) can only fail against a fake adapter.

## 3. Trust — implementation defects (verified by the code audits)

Ordered by what they cost the next batch.

| # | Defect | Where | Cost |
|---|---|---|---|
| T1 | `run` has no per-cell failure boundary; one exception from cell k discards the whole summary | `src/satyrn_evals/run.py:35-46` (read directly) | a 12B batch re-runs the model |
| T2 | `attempt.json` is written only after `grade()` returns; a grading exception leaves patch+transcript with no record | `attempt.py:229, :247` | invisible cells |
| T3 | No production caller of `load_attempt_record`/`load_session_record`; `summary.json` cannot be rebuilt from disk; no `regrade` command | `attempt_record.py:277`; `run.py:44-46` | BRIEF rule 3 is asserted, not executable |
| T4 | `summary.json` names cells but not task, command, or timeout — two arms differ only by the directory chosen | `summary.py:24-34` | arm identity lives in each cell's `attempt.json` |
| T5 | V7 auto-overlay hijacks the V6 preservation grade: `session_grader.py:122-128` passes `overlay=None` on a hidden task; `grade.py:67-70, :87-90` then materializes the overlay and swaps `selectors` for `expected_test_ids` while `expected` stays the preservation list — `UNAVAILABLE` for any task where the lists differ | masked because both fixtures' lists coincide | latent regression |
| T6 | `mode & 0o022` refuses every hidden task on umask-002 systems (Debian/Ubuntu user-private-group) | `overlay.py:74-79` | exit 2 off this laptop |
| T7 | `PYTHONPATH` for the oracle is the evals *install location*; in a wheel install that is the installer's `site-packages`, ahead of the locked env — `resolved_versions` would attest an env the oracle did not use | `grade.py:211-213` | wrong attestation off this checkout |
| T8 | `grade.py:184-198` runs `git init`/`git apply` with the ambient env — a caller's `GIT_DIR` redirects grading; the one place V4's env cleaning was skipped | — | latent |
| T9 | Verdict forgery by model code at collection: the overlay imports `app.py`/`models.py`; `SATYRN_ORACLE_RESULT` is in the oracle env (`grade.py:208`); a shape-valid 13-passed JSON + `os._exit(0)` passes `load_hook_result` (`verdict.py:37-79`) | not recorded anywhere | a limit to state beside "the verdict never comes from stdout" |
| T10 | Evidence `line` points into the concatenated added-lines blob, not the patch; cross-hunk concatenation can flag lines never contiguous | `contamination.py:73-88, :126` | evidence pointers mislead |
| T11 | Base-window subtraction not applied on the session path | `session.py:160` | rule-8 shape waiting for the first session task with public tests |
| T12 | Settled non-final step + crash leaves `session-record.json` reading `COMPLETE`, exit 0 | `session.py:353, :535-549`; pinned by `tests/integration/test_session_run.py:626-637` | Ctrl-C mid-session looks clean |
| T13 | `pyproject.toml` without `uv.lock` silently falls to ambient grading | `taskenv.py:6-12`; `grade.py:150-151` | misleading UNAVAILABLE or silent pass |
| T14 | Default attempt timeout is 30 s (`workspace.py:28`); it cost one smoke run | `docs/sdd.md:461-462` | footgun |

Detector evasions the spec does not name (audit 1 §3, probed on
`plausible-wrong-fix`): trailing whitespace, re-indent, quote swap, a
comment inserted every three lines, one window line already present as
context — all `clean`. Three of the thirteen acceptance tests are shorter
than four non-blank lines and are undetectable when copied alone. The
docstring's stance ("a verbatim tripwire, not a proof of ignorance",
`contamination.py:3-6`) is honest; the list above belongs in it.

A hole neither spec names: the hidden overlay is absent from the
*workspace* but present on this machine seven times over (`grep -rl` for a
hidden test id across swiftstar and the six overlays → 7), and the
baseline arm has `bash`. Check (c) does not run on ordinary attempts
(V7 §6) and the transcript is never scanned for overlay *content*. A model
that `find`s the overlay and paraphrases is undetected; the V7 spec says
so about paraphrase, but not about the on-disk copies.

## 4. Conclusions that do not follow

- **"24/24 gate + smoke pass ⇒ the repair path is qualified"** is true
  for plumbing and says nothing about difficulty — V8 says this itself
  (§6 "unmeasured"). But `ROADMAP.md:149-165` and the smoke record's
  "found and fixed" invite the stronger reading. Under an L3 contract with
  `writable_paths: [app.py]`, the smoke measured transcription.
- **"framing-2 is retained as the only author-from-scratch cell"** (V8
  §2) is unreachable by the engine arm (M3). Either the engine gains
  `write`, or the cell is baseline-only and says so.
- **"public tests give the model a working runner"** (V8 §11.7) — for the
  baseline arm only (M3).
- **"local-pings does not discriminate"** — not shown (M4). What was shown
  is "not separated at n=8 under a three-band rule". The de-admission is
  a maintainer decision and stands; the *inference* should not be reused.
- **"depth is a gradient"** — retracted by its author (E2). The six tasks
  are six defects of unmeasured relative difficulty on this path.

## 5. Architecture — what is not load-bearing

From the weight audit (commands in its transcript; line counts by `wc -l`):
src 6,609 (ex. tasks); tests 14,501 (2.2:1); docs 20,198 lines, of which
plans 9,922.

**Not load-bearing for the goal, and why:**

- `workspace.py` ≈350 of 1,138 lines (31%): nested cleanup ladders in
  `_safe_temp_parent` (`:311-387`), `BaseException`/spool-close
  scaffolding in `_run_command` (`:742-850`), the 8-arm `finally`
  (`:964-1045`), the Windows branch (`:675-686`; Windows is excluded by
  the V4 row). Seventeen `except BaseException`, twenty-two
  `_add_exception_note` calls in one file. The harvest index records no
  incident involving interrupts, cleanup, `TMPDIR`, or worktrees.
- `capture.py` ≈270 of 754 (36%): two-fault precedence arms
  (`:644-707, :709-754`) plus a second copy of workspace's git plumbing
  (`:60-217`, `:302-320`). Capture produced one task, since de-admitted;
  V8 did not use it. **Freeze.**
- `tests/test_workspace_failures.py` (1,376 lines, 135 `monkeypatch.setattr`)
  and `tests/test_capture_failures.py` (1,057): roughly three quarters
  two-fault/interrupt compositions that exist to reach the arms above.
  The 100% branch gate and the defensive arms are feeding each other.
- Duplication: git runner ×4 (two skip the safety config), env cleaning
  ×2 with drift, registration/containment/temp-parent/cleanup ×2,
  oracle runner ×2, presence-policy table ×2, hex validator ×2, four code
  enums (33 values) with three refusal idioms, five artifact writers with
  three durability policies, three legacy record generations for a
  12-day-old format with no legacy artifact in the repo
  (`attempt_record.py:15-33`).
- Glossary stopped at V4 (`ROADMAP.md:76-77`); `docs/reference/formats.md`
  has zero mentions of session/checkpoint/overlay and omits
  `cells`/`oracle_visibility`/`contamination` from the summary.

**Load-bearing and under-built:** the 170-line V5b path (`run.py`,
`summary.py`) that every model batch runs through (T1–T4).

**The session path** (1,881 src / 3,481 test): one toy fixture, `run`
cannot iterate sessions, the svcs workload is at a wall. Machinery ahead
of its consumer *today* — but the three-phase build over one evolving
checkout is exactly what it was built for, and that is the "feels like
actual development" rung (§7). Freeze until V13; do not delete.

## 6. What we should be doing and aren't

1. **Read the transcript we already preserve.** Every pathology in
   `slm-struggles.md` — the 245× `ls -R`, no-op edits, path-keyed churn,
   announce-and-stop, grader hunting, installing into the venv — is
   countable from Pi's stream-JSON, which both arms spool to disk. The
   backlog defers this to an engine-side emitter "not when a transcript
   sample becomes available" (`BACKLOG.md:37-38`). I think the seam
   argument was over-applied: reading a *preserved artifact offline* is
   the relationship `grade` already has to the patch, the session adapter
   already parses Pi events (`session_protocol.py`), and the baseline
   arm's transcript is not the engine's at all. Decision needed (§10).
2. **A model ladder defines "hard", not an arm pair.** On disk under
   `~/.cache/huggingface/hub` and `~/.omlx/model_settings.json`:
   Qwen3.5-9B, Ornith-1.5-9B, gemma-4-12B, Mellum2-12B-A2.5B
   (instruct and thinking), Qwen3.6-27B-8bit, Ornith-1.0-35B; Laguna and
   DeepSeek-V4 as GGUF. A 9B/12B/27B ladder is runnable tonight.
3. **The contract is the difficulty dial** and it is hard-wired to L3.
   Same base, same oracle, four rungs — the cheapest headroom there is.
4. **Vendor `specs/roadmap.md` into `base/`.** Real repositories have a
   spec; the blind rung is only fair if the model can read what
   `lang="en"` and "timezone-aware" mean. Public tests at base are red
   for 5/6 states (this session, `uv run --locked pytest tests` per base:
   1 failed/3 passed ×4, collection abort, and `framing-2-edit` 4 passed)
   — for the sixth, only the hidden suite sees the bug, so R0 is a wall
   there and the profile should say so rather than hide it.
5. **Ship the baseline adapter.** The reference arm of every probe is a
   Python script in a research doc, executed from `~/…/satyrn-v5c-scratch`
   (`…reprobe-protocol.md:110-143`, with a recorded "minor drift between
   this source and the executable"). `satyrn-evals-session-pi` is shipped
   and versioned; `satyrn-evals-attempt-pi` should be too.
6. **Generate the engine contract from the manifest.** The smoke's
   hand-authored `engine-contract.yaml` differed from the manifest by one
   token and narrowed `writable_paths` to `[app.py]` (audit 5 §5).
   `attempt --rung R1` should write it from `contract[R1]` +
   `source_paths`, so the text the model sees is the text on record.
7. **Per-model tool-call preflight.** Two of six roster models scored zero
   for protocol, not capability. Extend V5d's "positive evidence the model
   started" to "positive evidence the model emitted a well-formed tool
   call" — a one-turn canary before each model's first cell.
8. **Make BRIEF rule 3 executable**: `regrade ATTEMPT_DIR` and
   `summarize OUTPUT_DIR`.
9. **Pre-register the expected band per cell** from Block B before
   running V12 — `plausible-wrong-fix` is guard-only for a 12B already
   (`R/superseded/fixture-split.tsv:8-9`); expect ceiling at 27B; the 27B
   headroom must come from the author and build rungs. Writing the
   prediction down first is what keeps the profile from being read
   after the fact.
10. **State the forgery limit (T9)** next to rule 4, and either scan the
    transcript bytes for overlay windows or say plainly that a
    `bash`-armed baseline on this machine can read the overlay.

## 7. The ladder: how difficulty is defined and measured

Two axes the record supports, one it warns against.

**Axis A — evidence rung (per task, same base and oracle).** From the
revision-test spec, renamed so the numbers do not collide with the
superseded L-labels:

| rung | the contract carries | fair when |
|---|---|---|
| **R0 blind** | task statement + "the acceptance suite is red; the spec is in `specs/`; the public tests are in `tests/`" | public suite or spec exposes the defect (5/6 today) |
| **R1 digest** | + failing hidden test ids and assertion text (V8 §4 as written) | always |
| **R2 located** | + the file(s) | always |
| **R3 stated** | + the fix in prose — **today's contracts** | always; measures apply-an-instruction |

A task-rung is *mislabeled* if a model's successful-attempt count is not
non-decreasing R0→R3 at fixed n; that is the authoring gate.

**Axis B — task shape (same app, same 13-test oracle).**

| shape | base | example | who can attempt |
|---|---|---|---|
| repair, 1 file | reference − one defect | `plausible-wrong-fix`, `misleading-locus` | both arms |
| repair, 2–3 files | reference − 2/3 defects | `depth-2`, `depth-3` (defect identity confounded — say so) | both arms |
| author a module from implied contract | reference − `models.py` | `framing-2` | baseline only until the engine can create files |
| build phase 3 | reference − POST route/form/tests | *new* | baseline; engine after `write` |
| build phases 2–3 | phase 1 only | *new* | same |
| build all | `broken/app.py` | *new* — measured on swiftstar's harness from an empty repo: Laguna 39/40 (`R/…80-cell-verdict.md:34-50`), Mellum text-mode 3/9 (`R/…p15-verdict-record.md:47-57`) | same |
| build all, three prompts | `broken/app.py`, session | *new* — the V6 consumer | session adapter |

**Not an axis — file count.** Depth is confounded with defect identity
(E2). Report the depth tasks as what they are.

**The profile.** For each (task, rung) × model on the ladder, at
pre-registered n, record the V5b three-way split (successful attempts /
retained patches / conditional quality) and the V10 pathology counts.
Band per V5a's definitions. The suite is *representative for model M*
when M has at least one task-rung in each band; *has headroom at M* when
at least one task-rung sits below ceiling on the baseline arm. That is
counts and bands — no intervals, no claims layer; it replaces nothing in
V5a for engine-arm comparison, it adds the placement instrument V5a was
never designed to be.

## 8. Proposed roadmap

Rows in the repository's own format. Excludes are provisional until each
phase has a spec (`docs/sdd.md:72-75`).

| # | Phase | Direction (one sentence) | Excludes | Depends on |
|---|---|---|---|---|
| V9 | Loop integrity and re-scoring | `run` survives a failing cell, writes each cell's record before grading, and names task/command/timeout in the summary; `regrade ATTEMPT_DIR` and `summarize OUTPUT_DIR` rebuild receipts and summaries from disk; T5–T8 fixed with refusal/success siblings; T9 recorded as a stated limit; T14's default raised | transcript metrics (V10); new tasks; any model run | — |
| V10 | Pathology counts from the preserved transcript | an offline reader of the preserved Pi stream-JSON (both arms) counts tool calls by name, identical repeats, churn, no-op edits, test-runner invocations, announce-and-stop turns, reach outside the workspace, and overlay-content windows, reporting `unmeasured` where the artifact is unparseable, carried by `summarize` beside the verdict counts | an engine-side emitter; wall-clock; any change to the run-time seam | V9; the §10 decision on the backlog entry |
| V11 | The evidence ladder | each agentclinic task carries contracts at R0–R3 selectable at `attempt`/`run`; today's contracts become R3; hidden test ids are re-checked by a widened name check; `base/` vendors `specs/`; the engine contract is generated from manifest+rung; a shipped `satyrn-evals-attempt-pi` baseline adapter replaces the scratch wrapper; the 24/24 gate re-runs on the changed fixtures | measuring; engine changes (`write`, a runner) — owed to the engine roadmap | V9 |
| V12 | The model-ladder profile | pre-registered n per cell over {9B, 12B, 27B} × 6 tasks × {R1, R3} on the baseline adapter, then the engine arm where the baseline is below ceiling; a per-model tool-call preflight; expected bands written down from Block B before the first cell; the profile table places every task-rung per model and names the 27B headroom cells | the claims layer; admission verdicts beyond placement; re-scoring `local-pings`; interleaving models (arms interleave, models do not — reload cost) | V10, V11 |
| V13 | Build rungs on the same app | three hand-authored single-shot tasks (phase-3-missing, phases-2–3-missing, all-missing) with the 13-test cumulative hidden oracle and the vendored spec; then the three-prompt session task over `broken/app.py` for the V6 path; `framing-2` joins this rung; the cumulative-suite backlog entry closes as "hand-authored" | a second app; `capture` changes; session support in `run` unless V12 shows the session rung is where the headroom is | V11; V12's profile |
| V14 | A second application | a larger fixture (≥500 lines, ≥3 modules, a real dependency graph) packaged the V8 way | — | **reopens only when** V12/V13's profile places the 27B baseline at ceiling on every rung of AgentClinic |
| W1 | Weight | collapse the hypothetical arms in `workspace.py`/`capture.py` to a `try/finally` + a 20-line containment check; one git-plumbing module; delete legacy record generations and the Windows branch; unify the four code enums; freeze capture; glossary and formats catch up to V6–V8; the coverage gate re-baselined with a recorded correction in `docs/sdd.md` | behavior changes; the session path (frozen, consumed by V13) | V9 (touches the same files; land V9 first) |

**Sequencing.** V9 → V11 → V12 batches run overnight; W1 and V10 are
no-model work that fits between batches (V10 reads artifacts V12 has
already preserved, so it can land after the first batch and apply to it).
V13 after V12's profile says where the 12B and 27B headroom is. V14 on its
reopen condition.

**Budget check (V12).** 6 tasks × 2 rungs × 3 models × n=6 = 216 baseline
cells; at the reprobe's observed 2–15 min per cell that is two to four
nights. Engine cells only where the baseline is below ceiling — on Block
B's numbers, expect that to exclude `plausible-wrong-fix` at 12B and most
R3 cells at 27B.

## 9. Owed to satyrn-engine (not this repository's phases)

1. Merge `d5d5d37` (pi `--model` space form) to `main`; until then the V8
   smoke depends on an unmerged branch (E8).
2. A test runner the model can invoke (a restricted `bash`, or a `test`
   tool) — the overnight record's own requirement for a corrected profile
   (`…overnight…md:124-126`); without it the engine arm cannot attempt R0
   and cannot self-verify.
3. File creation (`write`, or an `edit` that creates) for the author and
   build rungs; "Do not create files" (`E/attempt.py:238`) is a wall for
   every shape past repair.
4. The `facts` field stays where the engine backlog put it: after an
   Evals experiment isolates content from delivery (`satyrn-engine/BACKLOG.md:48-54`).
   V11+V12 is that experiment's instrument.

## 10. Decisions needed from the maintainer

1. **Reopen "Transcript-derived summary metrics" against its reopen
   condition?** The entry says reopen "when the engine exposes these
   counts", not on a transcript sample. V10 argues the artifact is
   already preserved and the reader is offline. Yes/no decides V10.
2. **Contract rungs: a manifest field (`contracts: {R0..R3}` with
   `contract` as the default) or four task directories per state?** Six
   tasks already need the shape, which satisfies the three-implementations
   rule; a field is my recommendation.
3. **The ladder composition.** Qwen3.5-9B / gemma-4-12B / Qwen3.6-27B is
   the minimal omlx ladder. Add Mellum2-12B (which variant — instruct or
   thinking?) as a second 12B? Ornith-35B? Laguna (llama.cpp, not omlx)
   is out of scope unless there is a served endpoint.
4. **Vendor `specs/` into `base/`?** It changes the fixture, so the 24/24
   gate re-runs and every contamination pair is re-derived. Needed for
   R0 to be fair.
5. **Amend V5a's band note** with M4's power observation (a recorded
   reopen condition), or leave it as this document's finding?
6. **W1's scope and the coverage gate.** Keep 100% branch as the invariant
   and let it fall out of deletion, or scope the gate to load-bearing
   modules? I recommend the former: delete arms, coverage follows, record
   the correction.

## 11. Recomputation

```bash
# six-state hidden-suite signature (matches V8 §14)
cd ~/projects/pauleveritt/swiftstar/fixtures/agenttest && for s in misleading-locus plausible-wrong-fix depth-2 depth-3 framing-2 framing-2-edit; do d=$(mktemp -d); cp reference/app.py reference/models.py "$d"/ && cp -r reference/templates "$d"/; cp -r "repair/$s/." "$d"/; [ -f "repair/$s/.delete" ] && while read -r f; do rm -f "$d/$f"; done < "repair/$s/.delete"; cp acceptance/test_acceptance.py "$d"/; (cd "$d" && uv run --no-project --quiet --with "fastapi[standard]==0.115.10" --with "turbohtml==1.5.0" --with httpx --with "pytest==8.3.4" python -m pytest -q -p no:cacheprovider test_acceptance.py 2>&1 | tail -1); rm -rf "$d"; done

# public suite at base, per shipped task (5/6 red)
cd ~/projects/pauleveritt/satyrn-evals && for t in misleading-locus plausible-wrong-fix depth-2 depth-3 framing-2 framing-2-edit; do (cd src/satyrn_evals/tasks/agentclinic-repair-$t/base && UV_PROJECT_ENVIRONMENT=/tmp/pubenv-$t uv run --locked --quiet python -m pytest tests -q -p no:cacheprovider 2>&1 | tail -1); done

# shared 4-line windows, public tests vs overlay (1)
python3 - <<'EOF'
from pathlib import Path
F=Path.home()/"projects/pauleveritt/swiftstar/fixtures/agenttest"
nb=lambda p:[l for l in p.read_text().splitlines() if l.strip()]
a,o=nb(F/"reference/tests/test_app.py"),nb(F/"acceptance/test_acceptance.py")
print(sum(1 for i in range(len(a)-3) for j in range(len(o)-3) if a[i:i+4]==o[j:j+4]))
EOF

# engine fix not on main
git -C ~/projects/pauleveritt/satyrn-engine merge-base --is-ancestor d5d5d37 main; echo $?

# swiftstar visibility
gh repo view pauleveritt/swiftstar --json isPrivate

# smoke transcript tool calls (audit 5's script is in this session's scratchpad)
grep -o '"toolName":"[a-z]*"' ~/projects/satyrn-v8-scratch/smoke2-pwf-20260904-160143/agentclinic-repair-plausible-wrong-fix-*/transcript.txt | sort | uniq -c
```

Block B and P17 rates recompute from `R/experiment-results*.tsv`; the
overnight run's numbers recompute only from the local tarball
(`~/work/satyrn/evidence/2026-09-02-agentclinic-spike.tar.gz`) and its
two fixtures are unnamed there.
