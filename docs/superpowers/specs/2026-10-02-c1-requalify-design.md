# C1: re-cut the selfhost bases, then re-qualify under confinement

Approved in conversation 2026-10-02 (maintainer), three rulings recorded in
section 1. Parent design: `2026-09-27-unisolated-harness-design.md` §6 steps
3-4; roadmap row C1 ("Next — re-derive on the confinement harness"). This note
adds no claim. It fixes the task condition and the records that C2-C4
re-derive on.

**Done when:** six Baseline census records under `confinement` pass
`satyrn-evals launch --preflight` on this machine, on re-cut selfhost bases
that hold no nested selfhost task, and the ledger names the re-cut commit and
the new digests.

## 1. Rulings (2026-10-02)

| # | Ruling | Rests on |
|---|---|---|
| R1 | Re-cut at C1, then qualify; do not qualify on the nested bases | audit §1 (`evidence/2026-10-02-cleanup-audit/README.md`, evals `1432bff`): `selfhost-preflight-quiet/base` carries 3,821 nested task files four levels deep and `workspace.py` copies the whole base into every cell; C3 re-runs every outcome cell anyway, so the task condition changes once |
| R2 | C1 covers the Baseline arm only | the census that C2-C3 re-derive is Baseline-only; the Engine arm's inner Pi inherits `SATYRN_CONFINEMENT_ROOT` from the eval worktree and is never admitted (`2026-10-02-engine-budget-design.md`, confinement-fixes row); that fix stays where EB put it, before the first post-C4 Engine read |
| R3 | Exclude nested `selfhost-*` task directories only | the bases' public suites use `src/satyrn_evals/tasks/` as fixtures (about 30 test files in `selfhost-preflight-quiet/base/tests` resolve tasks, 10 read another task's `base/`); the recursion lives entirely in the `selfhost-*` entries (1,366, 1,362 and 251-259 files each); `agentclinic-*` ×4 and `format_number` total 74 files and nest nothing |
| R4 | Keep k = 3 and the 4,800 s backstop; declare the machine | this machine is an Apple M5 Max, 128 GiB (`sysctl`, 2026-10-02); live runs moved here about 2026-09-26, after the census nights; neither `evidence/2026-09-16-census/README.md` nor `evidence/2026-09-15-finishing-counterfactual/run-2/q3stats.md` names its machine. A faster machine makes the backstop bind less; C3 counts wall-clock cuts and re-measures k only if it sees them |

## 2. The re-cut

`tools/cut_task.py` `excluded()` drops, beyond what it drops today, every path
under `src/satyrn_evals/tasks/selfhost-*/` (all selfhost tasks, not only the
task's own). The five external tasks, `KNOWN_DEFECTS.md` and the other tasks'
specs stay; the task's own spec is already excluded.

Re-cut all seven selfhost tasks from their specs at their recorded BASE
commits (cell-loop `2234240`, docs-linter `73ec172`, guard-prefixes
`3e996a1`, preflight-quiet `3f7a561`, review-script `b253c99`,
run-record-gate `cc9ab53`, speed-probe `bea0b76`); the authored task's good
commit is held by tag `preflight-quiet-good`. Order does not matter, because
no base holds another selfhost task after the change.

What must hold, per task, before anything else is built on it:

1. Old base versus new base differs only by removed paths under
   `src/satyrn_evals/tasks/selfhost-*/`, plus any new `base_edits` (below). The prompt is unchanged:
   `digests.prompt` is byte-identical.
2. `cut_task.py check` passes; `task_self_test` passes on the base;
   `satyrn-evals qualify` passes all five checks.
3. A public test that breaks because it named a removed selfhost task gets a
   recorded `base_edits` entry with its reason, the pattern the 2026-09-25
   `tests/test_timing.py` edit set. Seven public test files in
   `selfhost-preflight-quiet/base/tests` name `selfhost-`; which of them break
   is measured, not assumed. A break with no obvious recorded edit stops the
   work and goes to the maintainer.

## 3. Frozen records stay frozen

`tests/test_census_records_frozen.py` allows one recorded revision per task
(`REVISED_TASK_TREES`, the 2026-09-25 Linux fixes) and fails on a second. The
map becomes a recorded chain per task: the digest a frozen census record pins,
then each recorded revision in order, ending at the C1 digest. The test keeps
both directions: an unrecorded drift fails, and the current tree must be the
chain's last entry. The isolation-era records are not re-issued; they stay
pinned to the trees they ran on, as evidence for the isolated condition
(ledger convention, entry "C0").

`PROVENANCE.md` loses the nested-task rows (about 6,000 of 8,580) with the
paths, and gains none for them.

## 4. The census scripts and the launcher's dead branch

`scripts/census_night.sh`, `census_night_2.sh` and `census_night_3.sh` call
`preflight_settings.py --cell`, a flag the parser no longer has (audit §2).
They are frozen evidence for the isolated nights, so each gains a header
saying so and that it is not runnable under confinement; they are not
edited otherwise. `launch_record.py` drops its `cell: bool` branch (both
call sites pass `False`), and the `launch --preflight` help stops saying
"isolated". C3 gets its own driver in its own plan.

## 5. The C1 records

Six records from `satyrn-evals record new`, one per census task, Baseline arm
`arms/baseline-ornith15-9b.json` (per-turn cap `max_tokens` 16,000), purpose
`admission`, `confinement`, mode `batch`:

| task | rung | n | k | tokens / turns | backstop | max_minutes |
|---|---|---|---|---|---|---|
| agentclinic-repair-depth-3 | R2 | 6 | 3 | 48,000 / 72 | 4,800 s | 240 |
| selfhost-run-record-gate | R1-plan | 6 | 3 | 48,000 / 72 | 4,800 s | 240 |
| selfhost-docs-linter | R1-plan | 6 | 3 | 48,000 / 72 | 4,800 s | 240 |
| selfhost-cell-loop | R1-plan | 6 | 3 | 48,000 / 72 | 4,800 s | 240 |
| selfhost-speed-probe | R1-plan | 6 | 3 | 48,000 / 72 | 4,800 s | 240 |
| selfhost-preflight-quiet | R1-plan | 6 | 3 | 48,000 / 72 | 4,800 s | 240 |

These are census night 1's parameters with nights 2-3's backstop (night 1 ran
3,000 s and lost 9 cells to wall clock on a shared machine). Each record's
`authority` names this note, the re-cut commit, and the machine (R4). Its
`decision_rule` says no outcome is decided from the record; the classified
table at C3 decides.

`launch --preflight` probes the model server, so the preflight step runs in
an attended sitting, by the maintainer or with the maintainer's approval in
that sitting. Its exit code is read directly, never piped. Launching the
records is C3 and the maintainer's decision.

## 6. Close-out

A ledger entry "C1" in `evidence/2026-09-15-release-one-decision-ledger.md`
names the re-cut commit, each task's old and new `digests.task_tree`, and
the six records. The roadmap's C1 row is marked done, and the cleanup item
"Un-nest the task bases" closes, naming the same commit.

## 7. Order and the instrument rule

C1 is one instrument piece: the re-cut, the frozen-record chain, the script
headers and the records. The next piece must be measurement, C2 (re-reading
process classes from retained transcripts), not another fix. The EB
confinement-root fix therefore does not follow C1 directly.

## 8. Out of scope

The Engine arm's confinement root and the red-stop receipt (EB, before C4);
C2's re-read; any cell; re-measuring k; the rest of the cleanup list
(`STATE.md`, the C0 mark's propagation, the session route, unrun gates,
fossil files).
