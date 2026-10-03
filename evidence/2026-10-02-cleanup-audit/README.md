# Cleanup audit: satyrn-evals and satyrn-engine, 2026-10-02

A read-only audit of both trees for dead code, fossils, duplication, stale
documents, and planning-surface hygiene, after the churn of release one,
release two, the confinement rewrite, and the `release-one` to `main`
rename. Nothing was changed by the audit itself. Every finding cites a path
and, where it matters, a line; every count carries the command that
recomputes it (section 10). Items are ranked P0 (changes what a cell or a
reader sees), P1 (misleads a maintainer), P2 (weight and tidiness).

Both repositories are at their `main` heads: evals `1432bff`, engine
`f9436aa`. The gates are green in both (`just gates`: evals 2871 passed and
343 deselected; engine 593 passed and 138 deselected; ruff F401/F811/F841
clean; provenance complete; lint-docs within cap). Nothing below is a
failing check. All of it is drift the checks do not cover.

The roadmap-hygiene rules applied are the ones this project already states:
a roadmap is a capped planning surface, one direction at a time; tangents go
to a backlog and every backlog entry carries the condition that reopens it;
a done row keeps its number and stops changing; derived facts stay derived
rather than copied into prose; a waiting item names the upstream decision it
waits on. (The maintainer's `~/.claude/skills/roadmap` symlink is broken; the
rules were taken from the archived skill and the t-strings
`roadmap-standards.md`.)

## 1. P0: the self-hosted task bases nest the whole task corpus, recursively

`tools/cut_task.py:280-282` excludes from a task's `base/` only the task's
own directory (`src/satyrn_evals/tasks/{name}/`) and its own spec. Every
other task that existed at BASE is archived into the new base, including
those tasks' own bases. The result:

| task | tracked files | nested task files | deepest nesting |
|---|---|---|---|
| selfhost-preflight-quiet | 4,235 | 3,821 | 4 levels |
| selfhost-cell-loop | 1,366 | 1,092 | 3 |
| selfhost-speed-probe | 1,362 | 1,092 | 3 |
| selfhost-docs-linter, -guard-prefixes, -review-script, -run-record-gate | 251-259 each | 44 each | 2 |

`src/satyrn_evals/tasks/` is 8,056 of the repository's 8,914 tracked paths
and 98 MB of working tree (606 distinct blobs, so the pack stays small, but
every checkout, `rglob`, provenance row and editor index pays for the paths).
`PROVENANCE.md` is 1.4 MB; 6,181 of its 8,580 rows are nested-task paths.
`BRIEF.md`'s repository-weight budget names exactly this failure mode from
the prior project ("a corpus that no supported code path read").

It is also a harness question, not only weight. `workspace.py:772` copies
the whole base into the cell's workspace with `shutil.copytree`, so a
Baseline or Engine cell on `selfhost-preflight-quiet` works in a tree holding
four nested copies of this repository. Whether that changed what cells did
(search cost, "hunting" classification, guard 4 firings on root-wide
searches) has not been measured and is not claimed here; it belongs in the
C1-C4 re-derivation's list of things the harness did to the cells. The
`.gitignore` the cut writes (`base/.gitignore`) does not touch it, and
`task_tree.tree_digest` includes every nested file, so the digest pinned by
61 records (`digests.task_tree`) would change when the nesting is removed.
Removing it is therefore a re-cut and a new task condition for the 27
records on the three deeply nested tasks, which is why it is a backlog item
with a condition and not a quick fix.

Fix shape: `excluded()` drops `src/satyrn_evals/tasks/` entirely (all tasks,
not only the task's own), plus `tools/task_specs/`; re-cut the seven
selfhost tasks from their specs; re-pin at C1. The residue test
(`tests/test_task_base_residue.py`) already walks every base and would catch
a regression if it gained a "no nested task roots" assertion.

## 2. P0: defects found in passing

These are not cleanup; they are small bugs the audit tripped over. Each
needs its own refusal-plus-success test pair under the project's rule.

- **Red-stop firings never reach a receipt.** `packages/engine/runner.ts:590,599`
  emit the guard kind `self_test_red_stop`; `src/satyrn_engine/budget.py:16-27`
  `GUARD_KINDS` does not list it, and `budget.py:132` drops any kind it does
  not know. Meanwhile `GUARD_KINDS` and `delivery.py:268` still count
  `self_test_redirected`, which nothing in `packages/` emits since the
  redirect was retired (engine `91e467c`). Receipts therefore show the
  retired guard at 0 and the live one not at all; `tests/test_delivery.py:249-252`
  pin the fossil key.
- **The frozen census scripts cannot run.** `scripts/census_night.sh:14`,
  `census_night_2.sh:18`, `census_night_3.sh:16` call
  `preflight_settings.py "$a" --cell`; the parser (`scripts/preflight_settings.py:257-266`)
  no longer has `--cell`, so each exits 2 at its first step. The docstring at
  `:45-54` still documents the flag and the `sudo -u satyrn-cell` read.
  `launch_record.py:121-124` keeps a `cell: bool` branch that would pass the
  same dead flag; both call sites pass `False`.
- **Path admission differs between the two sides.** Python `mutation.py:310`
  uses `fnmatch`, which honours `[seq]`; TypeScript `scope.ts:8-22` reimplements
  only `*` and `?` and escapes `[`. A contract pattern with brackets is
  admitted differently by the mutation protocol and the guard. No fixture
  uses brackets, so it is latent; worth one pinned fixture either way.

## 3. P1: planning surfaces (roadmap, backlog, STATE, archives)

### satyrn-evals `ROADMAP.md`

- **Row R0's "Done when" cell is a log**, 2,159 characters narrating 13 dated
  events across 2026-09-15 to 09-18 (`ROADMAP.md:49`). The release-two
  table has no Status column, so R1-R5 were never marked although the
  Engine was built (engine `bd76401`, `0b496d8`) and the comparison ran; the
  C0 row (`:75`) appends its status inside "Done when" for the same reason.
- **The file contradicts itself about release two.** `:30-31` "The claim is
  met ... 16 of 24 against 2 of 24"; `:67-71` every deciding result under
  isolation, the comparison included, "is unconfirmed until re-derived".
  `:36` "Keep: two-uid isolation" versus `:61` "The two-uid and bwrap
  profiles are retired." The title `:1` says "(both concluded)" above a
  section that reopens release two. `:68` says "the 39-cell census" while the
  ledger's C0 entry and `docs/numbers.md:144` count 45.
- **Deferred items lack reopen conditions.** Of nine items (`:98-116`), one
  carries a condition (the parked `derive-new-top-level-module` branch,
  `:100-109`); eight do not. Three of the eight concern the retired
  isolation layer ("isolation versus guards ablation", "a filesystem
  sandbox for /implement", TODO's "workspace isolation") without naming the
  2026-09-27 decision as their upstream.
- **Row 2d is never closed** (`:18` "not run; release two if still wanted");
  release two concluded without it and it is in neither Deferred nor TODO.
- **Derived facts copied into prose:** the Deferred paragraph restates the
  parked branch's commits and rebase; engine `ROADMAP.md:13` is a verbatim
  copy of evals row 1.

### Three homes for future work

`TODO.md` (Now/Next/Soon/Freezer/Done, two items, no conditions, one commit
on 2026-09-26), `ROADMAP.md` "Deferred", and the engine's `BACKLOG.md` (a
pointer to the tag). `TODO.md:5` "Investigate non-macOS initial setup and
workspace isolation" is overtaken by the Linux port
(`src/satyrn_evals/tasks/KNOWN_DEFECTS.md:92`) and the isolation retirement.
`TODO.md:9`'s `satyrn-setup` skill appears nowhere else; `scripts/prereqs.py`
partly covers it and TODO was not updated. The engine `ROADMAP.md:6` still
says "(R0 in progress)" and "nothing here is planned separately" while an
engine branch is parked with a backlog note of its own (`92c9282`) that
exists only on that branch.

### `STATE.md` (title date 2026-09-21; body edited to 2026-10-02)

Stale sentences, each a live claim a newcomer is told to read first:
`:14-15` head description written at `4d7a200`; `:19` "into release-one";
`:37-38` "The model runs as satyrn-cell" (retired, `fd3cd6b`); `:75-78` and
`:101-102` "classified and signed" (ledger `:303-304` marks it unconfirmed
and night 3 never signed); `:104-106`, `:208-209` "the claim is met"
(unconfirmed, ledger `:305`); `:126-127` sends readers to `docs/numbers.md`
first with no caveat; `:142` "84 files" (117); `:187-193` names
`evidence/2026-09-23-red-stop-gate/` as the re-derivation plan (it is the
red-stop plan; re-derivation is C1-C4); `:200-202` an open parity defect
naming `DELIVER_TIMEOUT_SECONDS`, a constant that exists nowhere in engine
`main`; `:210-212` an integration count at `b624b84`, a commit not on
`main`'s lineage; `:213-218` local state (the `satyrn-cell` user, sudoers,
the `/Users/Shared/satyrn-cells` exports) that is retired.

### Reading orders and front doors

Three different reading orders: `AGENTS.md:3`, `README.md:4-5` (which sends
newcomers to the release-one design that `AGENTS.md:5-7` calls "never
guidance"), `STATE.md:125`. `AGENTS.md:4-5` and `README.md:10-12` present
release two as concluded with a result; the ledger marks that result
unconfirmed. `BRIEF.md:11-12` "Release two starts from the R0 constraints"
predates its conclusion.

### Archives

- Engine tags duplicate: `archive/hp3-chained-isolation-2026-09-11` and
  `pre-release-one-2026-09-13` both point at `1ea478c`;
  `archive/main-hp3-2026-09-09` and `pre-release-one-main-2026-09-09` both at
  `9160493`. Tags `engine-78ab87d` and `engine-803df2d` say they are "pinned
  by satyrn-evals arms"; all three arms now pin `1869397`. Nothing on either
  `main` names the `archive/*`, `e1`, `e2` or `engine-*` tags.
- The engine's `main` documents say only `git show TAG:ROADMAP.md`; nothing
  names `docs/superpowers/phase-history.md` on the tag, which is the only
  definition of the E1-E10 labels that `docs/usage.md` (21 lines),
  `docs/glossary.md` (5 terms) and `BRIEF.md` still use.
- The decision ledger's title (`evidence/2026-09-15-release-one-decision-ledger.md:1`)
  says "(2026-09-13 to 2026-09-15)" over entries to 2026-10-02, and cites a
  `/private/tmp/claude-501/.../scratchpad/` path at `:134` (15 scratchpad
  references).

## 4. P1: the C0 "unconfirmed" mark lives only in the ledger

Ledger entry C0 (`evidence/2026-09-15-release-one-decision-ledger.md:299-310`)
marks census nights 1-3, the release-two comparison, both route proofs, the
red-stop rerun and the sandbox sets. None of the marked artefacts says so:
`docs/numbers.md` (0 hits; `:46` "The win rule is met"), `site/numbers.md:9`,
`site/index.md:19` ("The evidence is in the numbers"),
`evidence/2026-09-16-census/README.md` and `classes-summary.md`,
`evidence/2026-09-23-red-stop-gate/plan.md`, the finishing-counterfactual
READMEs. No record or result file under `records/` carries a marker either
(the only "unconfirmed" string there is a workspace-cleanup message). The
published site therefore states a confirmed win that the roadmap says is
unconfirmed. `docs/numbers.md:17` also pins engine `78ab87d` while every arm
pins `1869397`, with no note.

Related cap drift: `docs/numbers.md` is 169 lines and lives outside
`docs/results/` (which holds only `.gitkeep`), so the "one result file
under docs/results, 120 lines" rule (`ROADMAP.md:86-88`, `tools/lint_docs.py`
RESULT_CAP) never applied to the actual result.

## 5. P1: dead and test-only code in satyrn-evals

Import graph over `src` (excluding `tasks/`), `scripts`, `tools`, `tests`;
no dynamic imports exist.

**Modules nothing in product, scripts or tools imports** (tests only):

- `src/satyrn_evals/hygiene.py` (only `tests/test_hygiene.py`).
- `src/satyrn_evals/packet.py` (HP1 handoff packet from the dropped
  session-mechanics line; `PacketError` in `errors.py:116` raised only here;
  `packet_from_dict` at `:509` has zero callers anywhere).
- `src/satyrn_evals/turn_ledger.py` (only `tests/test_turn_ledger.py`, which
  is the sole reader of the 263 KB
  `tests/data/real-session-phased-verify-transcript.jsonl`; product turn
  counting is in `cell_evidence.py:481`).
- `src/satyrn_evals/session_repeat_limit.py` (`SessionWindowTripwire`,
  `SessionRepeatTripwire` never wired into `session.py`).
- `census_classify.py` and `census_decode.py` are imported by no product
  module; they are kept alive by `evidence/2026-09-16-census/classify.py:46-47`
  (a frozen evidence script ruff excludes). `census_classify.REVIEWER_ONLY:31`
  has zero references.

**The session route is a fossil of dropped work.** `satyrn-evals session`
and the `satyrn-evals-session-pi` console script are wired (`cli.py:69,223-247,670`,
`pyproject.toml:12`), but no Justfile recipe, README, ROADMAP, STATE, script,
arm or record uses them; `ROADMAP.md:114-116` records that the only full
four-phase test was dropped with the `session-mechanics` task. The family is
seven `session_*` modules, `adapters/pi_session.py`, `adapter_process.py`,
17 default-tier test files and 8 integration test files.
`tools/hooks/guard.py:34` still guards the `session` verb.

**Within-module dead symbols** (zero references outside the defining file,
tests included): `launch_cell.py:34-35` `COMMAND_BACKSTOP`, `ATTEMPT_DEADLINE`
(comment: "no readers"); `cell.py:19,42,53` `ISOLATION_ENV`, `isolation_from`,
`path_prefix_from`; `errors.py:120,124` `RouteError`, `ChainRecordError`
(HP2/HP6); `attempt.py:90` `LIVE_TRANSCRIPT_NAME` (comment still says "where
the cell user can write"); `launch_record.py:124` the `--cell` branch.

**Retired isolation that remains as shell:** `cell.py:28-40` keeps
`Isolation.ISOLATED`/`SANDBOX` because all 61 committed records carry
`"isolation": "isolated"` (48) or `"sandbox"` (13) and none carries
`confinement`; `run_record.py:100-131` maps them to `retired:<v>`. That
mapping is load-bearing and stays. The docstring residue is not:
`launch_record.py:14` names `cell_preflight.preflight_cell` (does not exist;
the export is `preflight_confinement`, `cell_preflight.py:51`); `:20` says
settings run "under isolation"; `tests/test_launch_record.py:292-300,486`
and `tests/test_finishing_counterfactual.py:22,390` carry
`/Users/Shared/satyrn-cells` literals.

**Scripts and tools:**

- `scripts/seq_design.py`: referenced only by `PROVENANCE.md` and the
  release-one design ("evidence, not guidance"); no test, no recipe.
- `scripts/suite_durations.json`: covers 7 of 12 tasks; rows pin branches
  `release-one`, `worktree-selfhost-headroom-probe`,
  `worktree-ornith-ceiling-probe` and commits `main` no longer contains;
  `tests/test_suite_durations.py` pins the file rather than checking it
  against the task set; nothing in `src`, `tools` or the Justfile reads it.
- `scripts/token_floor.py:67` and `scripts/usage_totals.py:116`: `_events()`
  is byte-identical except its docstring; their tests share three
  same-named parallel tests.
- `tools/agentclinic_gate.sh`: a six-line wrapper around a pytest invocation
  the `integration` recipe already covers; referenced only by `PROVENANCE.md`.
- `scripts/census_night*.sh`: frozen one-shots that cannot run (section 2);
  STATE.md's inventory line is the only statement that they are kept.

**Arms and records:** `arms/baseline.json` (gemma-4-12B) matches zero
records. `arms/engine-mellum-class-swe-pi.json` and
`arms/engine-mellum-class-swe-pi-redstop.json` are byte-identical.
`arms/baseline-unsloth-ornith15-9b-sandbox.json` differs from its sibling
only in `pins.pi` and names the retired bwrap profile.
`arms/baseline-mellum-swe-pi.json` cannot be rerun (STATE.md `:215-218`).
Five `records/2026-09-25-sandbox-baseline-*.json` have no `.result` sibling
and no file says why. `evidence/2026-09-22-mellum-tool-surface/` holds 23
groups of five byte-identical `run1..run5.request.json` files (92 redundant).

**Config:** `[tool.coverage]` with `fail_under = 100` and `pytest-cov`
are configured and never run; `[tool.pyrefly]` and `pyrefly` likewise (no
gate type-checks either repo). `.github/workflows/gates.yml:14-15` installs
Node 22, but `just gates` never invokes `node`; `packages/confinement/confinement.ts`
is exercised only by `tools/replay_confinement.mjs` through an integration
test that `gates` deselects, so the confinement extension both arms load has
no CI coverage.

## 6. P1: dead and duplicated code in satyrn-engine

- `tools/replay_orchestrator.mjs` (250 lines): referenced by nothing but
  `PROVENANCE.md`; its cases overlap `tests/test_orchestrator.mjs`, which is
  in `gates`. It is the only reader of
  `tests/fixtures/protocol/response-check-refusal-repo.json`.
- Unreferenced fixtures: `tests/fixtures/protocol/request-replace-valid.json`,
  `response-invalid-request.json`, `response-replace-ok.json`.
- `tests/test_protocol.py:33` defines `FIXTURES` and never uses it.
- `tests/test_derive_size.py:50` hard-codes
  `/Users/pauleveritt/projects/pauleveritt/satyrn-evals/...`; on this machine
  it warns that the vendored `selfhost-preflight-quiet` manifest diverges
  from the live one (`produces_count` 10 versus 9), on CI it skips.
- `tests/test_integration_mutator.py:196` and
  `tests/test_integration_runner_tool.py:198` are the same test with one
  string changed.
- Two implementations of the carried-file restore: `runner.py:232`
  `restore_carried` and `delivery.py:329` `restore_carried_at`.
- `src/satyrn_engine/__init__.py:3-8` narrates E1-E5 only; `__version__` is
  read by one test.
- Config never run: `[tool.coverage]` (`fail_under = 100`), `pytest-cov`,
  `[tool.pyrefly]`, `pyrefly`, `types-pyyaml`. `.gitignore` lists
  `docs/_build/`, `.pyrefly_cache/`, `node_modules/`, `dist/`, none produced
  by any tool on `main`; `docs/_build/html` on disk is a Sphinx build from
  2026-08-16 of a docs tree that no longer exists. `pyproject.toml:46-50`'s
  ruff comment describes a `docs/` research record that `main` does not have.
  The root `conftest.py` says "Empty on purpose" but is what lets
  `tests/test_provenance.py:5` import `tools.provenance`.
- `tools/provenance.py` is a strict subset of evals'
  `tools/provenance.py` (evals adds `site`, `_engine` and `record --source`);
  the engine copy lists `scripts`, `arms` and `.claude/settings.json`, none
  of which the engine has. `tools/lint_docs.py` caps 13- and 8-line files at
  400 lines; its docstring cites `CLAUDE.md`, which the engine does not have
  (also cited at `tests/test_doc_caps.py:3`, `tests/test_integration_runner.py:54`).
- Package manifest: `packages/engine/package.json` declares no dependency on
  `@earendil-works/pi-coding-agent`, which every extension imports as a type.

## 7. P1: stale engine documents

- `AGENTS.md:4-6` tells the reader to read three paths that exist only in
  satyrn-evals, plus "the current stage spec" and "the plan for the current
  phase", neither of which exists (both releases concluded).
- `BRIEF.md:66-69` says the preserve-symbols guard "is removed"; it ships
  (`packages/engine/scope.ts:53-60`, `mutator.ts:314-359`) and `README.md:17`
  lists it. `BRIEF.md:51,60,141-142` cite phase E3.5, a "Now" section and
  E3-E6 that `ROADMAP.md` no longer has. Two stacked "Correction" paragraphs
  (`:57-69`) narrate 2026-08 history the tag already holds.
- `ROADMAP.md:5,13`: "frozen at 8049d73" and "done 2026-09-14", while
  `git log 8049d73..main` lists 45 commits (self_test output detection,
  red-stop gate, extension seam, the rename). Only `docs/usage.md:236-246`
  acknowledges post-freeze work.
- `README.md:36-37` points newcomers to the release-one design as "Design
  and roadmap"; both `AGENTS.md` files call it evidence, not guidance.
- `docs/usage.md`: 21 lines of E3/E4/E5 labels; no mention of `--base`,
  `--turn-limit`, `--token-limit`, `--deadline-seconds`, `--token-budget`,
  `--turn-budget`, the `protocol` subcommand, the `test_command` and
  `deadline_seconds` contract fields, or `SATYRN_EXTRA_EXTENSIONS`; exit
  codes 11-14 missing from `:61-73`; `:323` cites an evals `records/` path
  and `:438` a "harvest index" that is in `local-ai-pi`.
- `docs/glossary.md`: four terms defined by E3/E4/E5; no entry for `derive`,
  finish-on-green, `token_budget`/`turn_budget`, `deadline_seconds`;
  `:75,77` cite bare `engine.ts`, `scope.ts`, `bounds.ts`. Both docs are
  MyST (17 `{term}`/`{doc}`/`{glossary}` uses) in a repository with no
  Sphinx; they render only through evals' `tools/engine_sync.py` transform.
- Module comments cite specs that are not on `main`: `runner.py:9`,
  `packages/engine/runner.ts:28`, `mutation.py:36`, `check.py:22`;
  `tools/replay_events.mjs:5` cites `tests/*-brief.md` (none exist);
  `bounds.ts:6-8` cites `scan_table.md` and `pi-bash-bounding.md`, found in
  neither repository nor the tag. `HP3` survives as a label on live code
  (`delivery.py:549`, `cli.py:134`, two tests).
- `PROVENANCE.md`'s 67 "created in release-one" rows name a branch that no
  longer exists; `tools/provenance.py:43` still emits the label.

## 8. P1: stale evals documents

- `docs/lessons.md`: 16 entries, none marked re-opened or settled, against
  `STATE.md:135`'s claim that every entry is. `docs/pathologies.md` entries
  21-23 (`:304,323,336`) unmarked. `docs/pathologies.md:3-10` and
  `docs/remediations.md:3-10` define the "clean harness" as including
  two-uid isolation; remediation 16 (`:218-226`) presents the retired
  `sandbox-exec` profile as the mitigation; `remediations.md:67,289` defer
  to "V12", a label from the pre-reset roadmap. `pathologies.md:220` cites
  `docs/engine/shootout.md` and a 2026-08-04 record that exist in neither the
  tree nor the tag.
- Specs: `2026-09-17-release-two-engine-design.md:3` still reads "approved"
  though built and measured; `2026-09-21-docs-site-design.md` is superseded
  by the public-site design with no banner; `2026-09-27-unisolated-harness-design.md:3`
  says "draft for approval" while its plan says approved and `ROADMAP.md:58`
  cites it as the design. `docs/superpowers/plans/2026-09-18-preflight-quiet.md`
  is the authored task's own solution plan (a task input the spec requires),
  misfiled beside the eval plans with the same "For agentic workers" header.
- Plans: 16 of 19 exceed the 400-line cap that applies only to specs
  (`tools/lint_docs.py:61-63`); nine name the retired isolation as their
  mechanism with no retirement note.
- `site/evals-architecture.md:12-14` publishes "run as a second user that
  cannot see grader material" (retired). `site/models.md` is an eight-line
  placeholder; `site/authoring.md:9`, `site/index.md:36,44`,
  `site/contributing.md:17` say "Coming" or "TBD". `site/glossary.md` (11
  terms) and the synced engine glossary (20 terms) share no term and use
  "isolation" and "attempt" in two senses with no cross-note.
- `evidence/2026-09-17-census-2/`, `2026-09-18-census-3/` and
  `2026-09-23-red-stop-gate/` have no README stating their status;
  `evidence/2026-09-16-census/README.md:3` awaits a signature that the
  ledger says never came.
- Branch-name residue ("on release-one") in dated records is historical and
  fine; `STATE.md:19` is the one live-surface case.

## 9. P2: local and repository fossils

- Engine `docs/_build/html/` (local, ignored, 2026-08-16), both repos'
  `.superpowers/sdd/` (local, ignored, 2026-09-04 to 09-14 SDD artefacts),
  evals `.cache/` (36 numeric entries, ignored by a global rule),
  `.claude/worktrees/` empty in both.
- Engine `.gitignore` and evals `.gitignore` both keep `docs/_build/`; only
  evals builds docs, into `_build/`.
- `scripts/preflight.sh:1` still calls itself "Preflight for a V11b two-arm
  batch".

## 10. What was checked and found clean

Recorded so the next audit does not redo it.

- Every path and commit cited by evals `ROADMAP.md` resolves; every engine
  commit the evals docs cite exists in the engine; `b624b84` exists but is
  off `main`'s lineage.
- `_engine/` (the synced engine docs) is byte-identical to engine `main`'s
  README, usage and glossary; the three files have not changed since the
  `1869397` pin.
- All ten `--8<--` includes in `site/` resolve. No broken relative Markdown
  links outside pasted scripts.
- All seven `tools/task_specs` have a task directory and at least three
  records. All engine `tests/*.mjs` are in the `gates` recipe. All events,
  guards, contracts, delivery and derive_size fixtures are read.
- No orphan top-level symbol in `src/satyrn_engine`; no orphan export in
  `packages/engine`.
- `tools/hooks/guard.py` is wired and has 19 tests covering every rule.
- Named sibling test pairs in both repos test different seams; the one
  near-verbatim duplicate is named in section 6.

Recompute:

```bash
cd ~/projects/pauleveritt/satyrn-evals
git ls-files | wc -l                                   # 8914
git ls-files src/satyrn_evals/tasks | wc -l            # 8056
git ls-files -s src/satyrn_evals/tasks | awk '{print $2}' | sort -u | wc -l   # 606
grep -c '/base/src/satyrn_evals/tasks/' PROVENANCE.md  # 6181
grep -c '^| ' PROVENANCE.md                            # 8580
for t in src/satyrn_evals/tasks/*/; do echo "$(git ls-files "$t" | grep -c '/base/src/satyrn_evals/tasks/') $t"; done
grep -l '"task_tree' records/*.json | wc -l            # 61
grep -c -i unconfirmed docs/numbers.md site/numbers.md site/index.md   # 0 0 0
awk -F'|' 'NR==49{print length($5)}' ROADMAP.md         # R0 Done-when cell
grep -n -- '--cell' scripts/census_night*.sh scripts/preflight_settings.py
uv run pytest -q | tail -1
cd ~/projects/pauleveritt/satyrn-engine
sed -n 16,27p src/satyrn_engine/budget.py; grep -n self_test_red_stop packages/engine/runner.ts
grep -rl replay_orchestrator --exclude-dir=.git --exclude-dir=.venv . # PROVENANCE.md only
git log --oneline 8049d73..main | wc -l                # 45
for t in $(git tag); do echo "$t $(git rev-parse $t^{commit} | cut -c1-7)"; done
uv run pytest -q | tail -1
```

## 11. Backlog entries proposed

Each entry below is added to the backlog of the repository that owns it
(evals `ROADMAP.md` "Deferred"; engine `BACKLOG.md`), with the condition
that reopens or closes it. The ordering is by what a cell or a reader sees
first, not by effort.

1. **Un-nest the self-hosted task bases** (section 1). Do at C1, where the
   tasks are re-qualified on the confinement harness anyway, so the re-cut
   and the re-pin cost one condition change instead of two.
2. **Count `self_test_red_stop` in receipts; drop `self_test_redirected`**
   (section 2). Do before the first Engine record of the re-derivation,
   since C3's classified table reads guard firings from receipts.
3. **Propagate the C0 unconfirmed mark** to `docs/numbers.md`, the site
   pages, the census and red-stop evidence READMEs, and a `status` note in
   the ledger-named record files (section 4). Do now; it is prose.
4. **Rewrite `STATE.md` and reconcile the three front doors** (section 3):
   one reading order, one statement of what is confirmed, the retired local
   state removed. Do now, in the same commit as item 3.
5. **Roadmap shape**: a Status column for the release-two table, R0's cell
   reduced to a pointer at the census page and the ledger, 2d closed, the
   Deferred items given reopen conditions or moved to `TODO.md`, and one
   backlog home chosen between `TODO.md` and "Deferred" (section 3). Do
   with item 4.
6. **Retire the session route or re-justify it** (section 5): `packet.py`,
   `turn_ledger.py`, `hygiene.py`, `session_repeat_limit.py`, the
   `session_*` family and its 25 test files, the 263 KB transcript fixture,
   the `satyrn-evals-session-pi` script. Reopens if a plan names a
   multi-phase workload; otherwise delete at the next instrument-free window.
7. **Delete the small dead symbols and fix the `--cell` residue** (sections
   2, 5): the frozen census scripts either gain a header saying they ran
   once under a retired flag, or lose the flag; `launch_record.py`'s `cell`
   parameter goes. Do with item 2.
8. **Config that nothing runs** (sections 5, 6): either add a type-check
   gate and a coverage gate to `just gates` in both repos, or remove
   `pyrefly`, `pytest-cov`, `types-pyyaml` and their sections; add a Node
   gate to evals (the confinement extension) or drop `setup-node` from CI.
   Decide once for both repos.
9. **Engine docs re-earned on `main`** (section 7): `AGENTS.md`, `BRIEF.md`,
   `ROADMAP.md` and `README.md` rewritten against what `main` has; usage and
   glossary either converted to plain Markdown in the engine (and the sync
   transform retired) or kept MyST with the Sphinx build restored; the
   E-phase labels replaced or defined by a pointer to the tag's
   `phase-history.md`. Reopens with the first engine change after C4.
10. **Evals catalogue marks** (section 8): lessons, pathologies 21-23, the
    two banners and remediation 16 marked against the 2026-09-27 retirement;
    the three specs' headers set to their real status; the misfiled task
    plan moved under the task's spec or `tools/task_specs/`.
11. **Fossil files**: `tools/replay_orchestrator.mjs` and three protocol
    fixtures (engine); `scripts/seq_design.py`, `scripts/suite_durations.json`,
    `tools/agentclinic_gate.sh`, `arms/baseline.json`, the duplicate
    `engine-mellum-class-swe-pi-redstop.json` arm, the 92 duplicate Mellum
    request files (evals); the two duplicate engine tags. Each deletion is
    one provenance row and one commit; none needs a plan.
12. **Lint-docs coverage**: cap plans as specs are capped, or state that
    plans are uncapped; point RESULT_CAP at the file that is the result.
