# Next-agent brief: the V11 fix round

**Date:** 2026-09-05. **Status:** handoff, amended after deep review the same
day. Nothing in the "Work to do" section has been started.

**Read this whole file before touching anything.** Most of what follows was
established by two independent reviews on 2026-09-05 and **exists nowhere
else** — losing it repeats this repository's own recorded failure mode: the
record existed and was never retrieved
(`docs/superpowers/research/2026-08-16-harvest-index.md`).

---

## 1. Where everything is

### The branch you want: `main`, uncommitted

All V11a-trim and V11b-trim work is **applied to `main`'s working tree and
deliberately not committed** — `CLAUDE.md` makes commits maintainer-
controlled. At handoff:

```
HEAD                89dba96  (unchanged all session)
dirty paths         55
uv run pytest -q    1055 passed, 270 deselected
```

Deep-review correction: the count is **56**, not 55, once this brief itself
is included. Recompute it rather than carrying either snapshot forward:

```bash
git status --short | wc -l
```

**Do not commit `main` unless the maintainer asks.**

### Scratch branches — history only, safe to delete

| Worktree | Branch | What it holds |
|---|---|---|
| `.worktrees/v11a` | `wt/v11a-trim` @ `435b942` | V11a built here |
| `.worktrees/v11b` | `wt/v11b-trim` @ `83eb87e` | V11b + the `-nc` delta |
| `.worktrees/v11-int` | `wt/v11-int` @ `33731a7` | the merge where the full gate was run |

Their content is already in `main`'s working tree. A fourth worktree
(`wt/v11-fixes`) was created and **deleted** — its base was built by a copy
loop that silently skipped directories (`arms/`, `scripts/`), producing 2
spurious test failures. If you build a scratch base, use `git checkout` or
`rsync -a`, never a `cp` loop over `git status` output.

### Evidence, outside the repo

`~/satyrn-smokes/2026-09-05-v11-trim/`

- `baseline/` — **the only complete cell ever run through this substrate.**
  460 events, 24 turns, 23 tool executions. Your richest artifact.
- `engine/`, `engine-long/` — two failed Engine cells (900 s and 2400 s)
- `token-floor.json` — the measured floor, 1,546

### Documents

Specs: `2026-09-05-v11a-trim-contract-rungs-design.md`,
`2026-09-05-v11b-trim-arm-substrate-design.md` (its §9 is the `-nc`
amendment, §10 a correction about `ruff format`),
`2026-09-05-v11c-spike-protocol-and-v13-firewall.md` (**the confirmed gate,
and the five preconditions**).

Research: `2026-09-05-v11-trim-and-spike-proposal.md` (design of record),
`2026-09-05-roadmap-amendment-v11-trim.md`,
`2026-09-05-pi-context-file-loading-and-arm-parity.md`,
`2026-09-05-v11-baseline-smoke-and-v10-amendment.md` (**its §6 is a
retraction — read it before trusting any claim about the overlay scan**),
plus two agent derivations (`…-v11a-r1-derivation.md`,
`…-v11b-adapter-derivation.md`).

---

## 2. Where the project actually stands

V11a-trim and V11b-trim are **built and green, but not landed**: every V11
change is still uncommitted on `main`, ROADMAP still calls both phases in
progress, and `preflight.sh` deliberately refuses a dirty evals tree. The
V11c spike protocol is **confirmed** by the maintainer. Of its five
preconditions:

| # | Precondition | State |
|---|---|---|
| 1 | Both tracks landed, full gate green | **pending maintainer-controlled landing**; implementation gate is green |
| 2 | Baseline smoke, pathology `measured: true` | **met**, after a V10 amendment |
| 3 | Engine smoke on a generated contract | **FAILS — see §4** |
| 4 | Per-cell input-token floor measured in a workspace | **met — 1,546** |
| 5 | `preflight.sh` green | not attempted |

**No budgeted cell may run while 1, 3, or 5 is unmet.** That is the protocol,
and the maintainer's confirmation explicitly does not waive it.

### The strategic point, easily missed

**V12 is reference-arm only.** Engine's brokenness does *not* block it. But
V12 is not ready immediately after §3: it still needs R0/R2, the four-point
monotonicity check, creation-capable patch capture before `framing-2`, the
live completion and tool-call canary for each model, observed model-identity
validation (§3 Fix 5), and a resume-safe 288-cell driver (§6). The critical
path therefore splits: finish those reference-arm gates and run V12 (~10 h,
one night of model time); repair Engine in parallel, which gates the spike
and V13 but not V12.

### Measured timings — use these, not the proposal's

The proposal sized runs against the 900 s ceiling. Measurement supersedes it:

- Baseline cell: **127 s wall, 118 s inside pi**, ~3 s non-model overhead.
- Mini-probe (12 cells) ≈ **25 min**, not a night.
- V12 (288 cells) ≈ **10 h** — the only genuinely overnight run.
- Engine cells: currently 100% timeout. 12 spike Engine cells = **3 h of
  guaranteed dead time producing twelve empty records.**

---

## 3. Work to do — the fix round

Fixes 1–3 change contract text and therefore every `contract_digest`; they
are free *now* and expensive after the first budgeted cell. Fix 4 changes the
runtime boundary. Fix 5 closes a confirmed-protocol gap in the instrument.

### Fix 1 — the contract's own command does not work. Six tasks.

Every `contract` and `contracts.R1` says:

> Your workspace has a runnable public suite under tests/ (`uv run pytest tests/`)

**It is not runnable.** `uv run pytest tests/` fails at collection on all six
tasks with `ModuleNotFoundError: No module named 'app'`: `tests/` has no
`__init__.py`, there is no `conftest.py`, and no `pythonpath` config, so
pytest puts `tests/` rather than the project root on `sys.path`.
`python -m pytest` reaches the intended suite (which is why the hidden
oracle, `python -m pytest -p satyrn_evals.oracle_hook`, grades fine): in
isolated copies it reproduced the intended five red bases and the one green
`framing-2-edit` base. `framing-2` still aborts collection on its seeded
missing `models` module; that is the task defect, not a runner defect.

Demonstrated in the real cell — three tool results carry the error:

```bash
python3 -c "
import json
res={}
for l in open('$HOME/satyrn-smokes/2026-09-05-v11-trim/baseline/agentclinic-repair-depth-2-20260905-141700-544422/transcript.txt'):
    e=json.loads(l) if l.strip() else None
    if not isinstance(e,dict): continue
    if e.get('type')=='tool_execution_start': res[e.get('toolCallId')]=json.dumps(e.get('args',{}))
    if e.get('type')=='tool_execution_end':
        t=''.join(p.get('text','') for p in (e.get('result') or {}).get('content') or [] if isinstance(p,dict))
        if 'No module named' in t: print(res.get(e.get('toolCallId')))"
```

**Cost:** a fixed confound in all 288 V12 cells. It also *manufactures*
pathology counts — 4 of the 5 counted `repeats` and 3 of the 8
`test_runner_commands` in the smoke are the model retrying around this — and
V12/V13 would read those as model behaviour.

**Recommendation: pick the first option and record why.** It repairs the
truth of the contract without changing `base/`, the contamination
subtraction set, or the 24-cell gate:

- change the sentence to `uv run python -m pytest tests/` (changes contract
  digests — free now), or
- add `[tool.pytest.ini_options] pythonpath = ["."]` to each `base/pyproject.toml`.
  **Precedent in-tree:** `local-pings/base/pyproject.toml:143-144` does exactly
  this "so uninstalled tree copies run". This changes `base/` bytes, so the
  24-cell contamination gate must be re-derived (integration tier, minutes —
  proposal §2.2).

### Fix 2 — the contracts present hidden-suite output as the public runner's

R1 carrying bare hidden test names is **by design** (V11a spec §3). The
defect is the framing: R1 says "The suite reports three failing checks
<names>" immediately beside "runnable public suite under tests/", so the
model believes those names are in its workspace.

They are not. **Zero of the nine test functions named across all R1/R3 texts
exist anywhere under any `base/`.** In the smoke the model grepped for them,
found nothing, and spent **5 turns hunting the names, 7 through abandonment,
9 including the symptom search** — of 24. It concluded "the user's prompt
refers to tests that are not currently present in the workspace."

Per-task exposure:

| task | overlay-only ids named in R1 | public suite masks it? |
|---|---|---|
| `depth-2` | 3 | no — no public lang/layout test at all |
| `depth-3` | 4 | no |
| `misleading-locus` | 1 | yes — public test fails on the same bug |
| `plausible-wrong-fix` | 1 | yes — same `307 == 303` |
| `framing-2`, `framing-2-edit` | 0 | n/a |

**Fix:** say plainly that the named failures come from an acceptance suite
the workspace does not contain. Do not remove the names — that is the rung.
Apply the distinction consistently to the default contract and R3 wherever
they also quote acceptance-only names or symptoms; otherwise the default
path retains the same false provenance after R1 is repaired.

Also: `depth-2`/`depth-3` claim "three/four failing checks" while the public
suite shows one; the model cannot self-verify 2 of 3 (or 3 of 4) named
failures.

### Fix 3 — every `framing-2-edit` contract is refuted by its own workspace

R1 claims "importing the app raises `AttributeError: module 'models' has no
attribute 'complaints'`". In fact `import app` succeeds and the public suite
is **4 passed**. `app.py` does `from models import SEED_COMPLAINTS as
complaints` and works; only the *hidden* `test_acceptance.py` snapshots
`models.complaints`. This is the one task whose public suite is green at base
(proposal §2.1). The default and R3 texts are also false when they ask to
"repair the app's import." All three texts must say that the absent legacy
module attribute is observed by the unavailable acceptance suite; none may
claim the app import or public suite is broken.

### Fix 4 — the attempt runtime environment

Three defects at one runtime boundary:

1. **The model creates a `.venv` inside its own worktree.** `base/` ships
   none (`find src/satyrn_evals/tasks -name .venv` → nothing); the model's
   first `uv run pytest` creates it — 41 MB, 2224 files, 1729 `.py` files
   against 3 real ones. It then greps it: two tool results of ~51 KB each,
   **80% of all tool-result bytes in the cell**, and the two turns carrying
   them are the two longest gaps — **49 s of the 118 s model span (41%)**.
   `grep -r lang .` returns 17.7 KB with the venv and **0 bytes without**.
2. **Evals' own venv leaks into the model's shell.** `attempt.py:149` copies
   `os.environ` wholesale and `:154` prepends `Path(sys.executable).parent`.
   Eight tool results carry a `VIRTUAL_ENV … does not match` warning. Latent
   trap: a bare `python`/`pytest` resolves to Evals' interpreter, which has
   no fastapi. **satyrn-engine's `_clean_environment` already pops
   `VIRTUAL_ENV` and strips its bin from `PATH`; evals does not.**
3. **Bytecode residue** in the worktree.

**Fix:** export a unique, automatically cleaned `UV_PROJECT_ENVIRONMENT`
outside the worktree (precedent: `grade.py:174-194` does this so
"materialization never pollutes the tree"), export
`PYTHONDONTWRITEBYTECODE=1` (precedent: `adapters/pi_session.py`
`_SESSION_RUNTIME_ENV`), and clean `VIRTUAL_ENV`/its bin entries before Pi
inherits the environment. **Zero `base/` bytes change.**

Deep-review correction: "one change in `attempt.py`" was too narrow.
`attempt.py:154` deliberately prepends the evals interpreter's bin so the two
console-script arm commands can start. Removing that entry there either
breaks command discovery or, if it is immediately re-added, leaves bare
`python` resolving to the evals environment. The orchestration should own the
relocated uv environment and bytecode policy; the Baseline adapter should
sanitize the environment it gives its Pi child. Engine already sanitizes its
Pi child in `satyrn-engine` `_clean_environment`. Tests must prove both that
the arm command remains startable and that the model-visible shell has no
ambient evals venv.

**Side benefit worth the change on its own:** with venv and bytecode out of
the tree, `git status` stays clean — which is the stated blocker for
creation-capable patch capture, itself a V12 entry gate for `framing-2`.

### Fix 5 — strict tally verifies the requested model, not the observed one

The confirmed protocol says the model id is read back from every transcript
(V11c spec §4). `scripts/tally.py:131-169` instead extracts `--model` from the
recorded command. That proves only what was requested; it cannot detect a
server routing the request to another model. Correction 5 in §5 was too weak
when it said to "check that assumption before V12": the assumption is already
refuted by the code.

**Fix before any V11c or V12 budgeted cell:** derive the observed id from
`message.model`, require one consistent non-`keepalive` id per transcript,
and compare it with the arm's expected server/model identity. Add the usual
bad/good pair: a wrong observed model refuses the batch, and a matching one
tallies. `responseModel` remains unusable.

### After fixes 1–5

One uncounted V5d re-smoke (~2 min): the attempt-environment path is
materially distinct, so V5d requires it. Read the record against the V5d
checklist and confirm pathology is still `measured: true`. The maintainer
then needs to land the reviewed V11 tree before preflight can make
precondition 1 or 5 green.

---

## 4. Why Engine is blocked (do not spend cells on it)

**It loops to the ceiling every time — three cells for three.** The final
surviving spool (3.5 MB, modified 2026-09-05 11:25 EDT) contains **816 tool
calls, 6 distinct**, of which `read tests/test_app.py` is **811**. **806 of
816 tool results are loop-breaker refusals.** The earlier 749/744/739 counts
were a snapshot while the orphan was still writing, not the final artifact.
The model emits no prose at all. ~3.5 s/turn.

Three stacked causes:

1. The contract sentence "runnable public suite … (`uv run pytest tests/`)"
   is handed verbatim to an arm whose tool surface is `read,edit` — **it has
   no `bash`** and cannot run any command. Combined with Fix 2's phantom test
   names, it re-reads the only test file forever. (Fixes 1–3 may materially
   help here; the arm still cannot run tests.)
2. The loop breaker (`satyrn-engine/packages/engine/engine.ts`,
   `THRESHOLD = 5`, `WINDOW = 20`) **refuses** the repeated call but never
   ends the agent, and pi 0.84.4 has no turn cap — so the identical refusal
   repeats until evals' timeout.
3. **A timed-out Engine cell preserves nothing.** Engine spools the
   transcript and publishes only after pi exits
   (`satyrn-engine/src/satyrn_engine/attempt.py:579-612`); it has no SIGTERM
   guard (the guard at `cli.py:118-129` is `deliver`-only). The spool *is*
   written incrementally into evals' temp parent, but evals'
   `run_workspace` cleanup (`workspace.py:773-790`) removes it. The Baseline
   adapter streams straight to the destination, so **a Baseline timeout keeps
   a partial transcript and an Engine timeout does not** — a predeclarable
   asymmetry.

**Owed to satyrn-engine:** terminate after N consecutive blocked calls (or a
turn cap), and publish the spool on SIGTERM. **Owed to evals:** copy the
spool before teardown.

### Precondition 3 also fails for a second, independent reason

**Engine transcripts carry `entry_appended`, which V10 does not know.** It is
the loop breaker's telemetry (`pi.appendEntry("loop_broken", …)`). Verified:
the final surviving spool holds **806 `entry_appended` events**, all with
`entry.customType == "loop_broken"`, and

```bash
uv run python -c "from satyrn_evals.pathology import EVENT_TYPES; print('entry_appended' in EVENT_TYPES)"   # False
```

So even a completed Engine cell reads `unmeasured: unknown_event`, exactly as
`tool_execution_update` did for Baseline. **Recommendation: do not merely
recognise it — count `loop_broken`.** It is the direct measurement of the
pathology above, and V10 has no other way to see it.

---

## 5. Corrections — do not re-derive these

`CLAUDE.md`: a correction is recorded, not edited away.

1. **The overlay-scan "gap" was wrong in every particular and is
   RETRACTED** (that research doc's §6; the BACKLOG entry was deleted). "16
   of 17" reproduces under no rule (15/17 or 17/17 depending on the rule);
   "diverges after 37 characters" is `len("./.venv/lib/python3.14/site-packages/")`,
   a shared path prefix; "differently ordered" is false — pi's bash tool
   streams a sliding 50 KB tail window, same order, scrolled. **The
   `toolResult` the model receives is byte-identical to the end result**, so
   partials never enter model context and scanning them would create false
   positives. The end result is the correct scan body.
2. **Concurrency is refuted as a throughput lever.** Non-model time is ~7% of
   a cell. Two overlapping Engine cells delivered **0.494 turns/s combined
   versus 0.744 solo** — concurrency made aggregate throughput *worse*.
   Do not build a parallel runner on the strength of a CPU sample.
3. **`ruff format` is not this project's gate** — no Justfile target, no CI
   step, `ruff check` only. 75 files are unformatted tree-wide and
   pre-existing. Do not reformat them; it would rewrite files whose diffs
   this project reads as evidence. (V11b spec §10.)
4. **`usage.input` is pi's *uncached increment*, not total context.**
   `input + output + cacheRead == totalTokens`. The smoke's context grew
   1,546 → 50,775; 1,546 is the floor (first turn), which is the number the
   Envelope cap wants.
5. **Never read model identity from `responseModel`** — it is `"keepalive"`
   on every turn. The real id is in `message.model`. `tally.py` currently
   compares only the requested model from argv; Fix 5 makes observed identity
   a gate before V11c or V12.

---

## 6. Smaller items, recorded so they are not lost

- **`preflight.sh` should refuse a stray *measurement-shaped* `pi` or
  `satyrn-engine` process.** An orphaned engine ran 48 minutes against the
  model server this session and confounded a measurement. A blanket `pi`
  name check is wrong on this machine: IDE integrations keep legitimate,
  long-lived interactive Pi processes. Match the batch argv/cwd/ancestry
  (for example `--print --mode json` plus the pinned model/extensions), or
  record and compare an explicit allowlist. Evals starts commands with
  `start_new_session=True` (`workspace.py:755`), so a parent that dies leaves
  the whole chain alive with no deadline.
- **No resume at V12 scale.** A crash after cell *k* writes `aborted.json`;
  `summarize` refuses it (`rescore.py:58-97`) and rerunning into the same
  directory yields a summary naming only the new cells. V12 is ~48 runs over
  several nights. `interleave.py`'s one-directory-per-cell pattern avoids
  this but is two-arm, single-(task,rung) — **V12 has no driver yet.**
- **Arm files pin one model string**; the 26B needs a second arm file or a
  parameter.
- `turbohtml==1.5.0` in every `base/pyproject.toml` is grader residue — the
  app never imports it, only the hidden suite does.
- `plausible-wrong-fix` R3 says "fix it so the redirect is a 303 **and the
  complaint is recorded**"; recording is not broken at base, so the clause
  invites a wasted search.
- ~601 `satyrn-attempt-*` parents (101 MB) in `$TMPDIR` from session-fixture
  materializations; `tests/integration/test_session_workspace.py` has 8
  `prepare_` against 6 `release_` calls. Hygiene, not throughput.
- `_structure_ok` never pairs a `tool_execution_update` to a start, so an
  orphan update is accepted. Not a count error.

---

## 7. Rules that govern this work

From `CLAUDE.md` and `BRIEF.md`, and every one of them was earned today:

- **Verify, don't assert.** Carry the command. Several claims in the first
  pass of this work were wrong precisely because a number was reported
  without the command that recomputes it.
- **A refusal test has a sibling success test**, and **a detector must
  discriminate in both directions.**
- **Default tests use no model, no network, no subprocess.**
- **Capture is separate from grading** — this is why the V10 defect cost one
  cell instead of two. Prefer re-scoring a preserved artifact over re-running
  a model, always.
- **Counts, never wall-clock, in published comparisons.** Wall-clock for
  planning is explicitly fine (proposal §8).
- **No commits on `main`** unless the maintainer asks.

## 8. Suggested order

1. Fixes 1, 2, 3 together — one pass over all variants in six manifests plus
   their tests; choose the module-form public command.
2. Fix 4 at the orchestration/Pi-child boundary, with startability and
   model-visible-environment success/refusal tests.
3. Fix 5: observed transcript model identity, with a discriminating pair.
4. Full gate, then one uncounted Baseline V5d re-smoke (~2 min).
5. Add `entry_appended`/`loop_broken` to V10 with a discriminating fixture.
6. Take §4's Engine defects to `satyrn-engine`; then rerun its V5d smoke.
7. Maintainer review/landing, then clean-tree preflight.
8. Only then reconsider V11c. V12 may proceed independently only after its
   separate gates in §2, including a resume-safe driver, are closed.
