# Decision ledger — release one and release two R0 (2026-09-13 to 2026-09-15)

The working record kept while Phases 1 to 3b ran, the stated negative was
written, and release two's R0 design sitting began. Committed on 2026-09-15
so the reasoning behind each ruling outlives the session that made it. The
pages that cite it: `docs/superpowers/specs/2026-09-15-release-one-outcome.md`,
`docs/lessons.md`, `evidence/2026-09-15-finishing-counterfactual/` and its
`run-2/`.

Provenance: the session scratchpad copy was truncated to its last 26 entries
before it could be committed, so this file was reconstructed from the session
transcript's own append commands (72 appends, duplicates removed, four
read-only commands discarded). Entries are dated, in the order they were
written; times are local (EDT) unless marked Z. A few early entries are
headed "Added 2026-09-13 (cont.)" from the sessions that preceded the
rewrite.

---

## Added 2026-09-13 (cont.)
- Restart: orphan branch + worktree in each repo (`release-one`), tag old mains first; import by explicit `git checkout main -- path` with source SHA recorded. Create when the import list is decided.
- Contract is DERIVED (deterministic builder, as HP1 was) with the developer's request as the one free input; developer reviews, never hand-writes. Interface requirements become executable public checks; facts inline, never pointers to files (PD's pointer prompts: 1/8).
- Workloads for release one: `misleading-locus` R1 (pathologies 1-2, cold) and `complaint-lifecycle` plain (pathologies 1, 3; the WARM workload). User-story hard variant retired from the claim.
- Ornith probe Block A swapped depth-3 -> misleading-locus R1.
- DEFERRED: contributors bringing their own workflows in as eval suites. Revisit after release one.
- Eval question to add: how much does SLM-authored objective degrade a derived contract (one cheap probe).
- Eval size: (b) minimal plus the contract. Import: grade/capture/attempt/session core (workspace, patch, oracle_hook, verdict, receipt, manifest, taskenv, deadline, repeat_limit, contamination), the two release-one tasks with witnesses, census, preflight, interleave, tally, Pi adapters, packet.py schema+builder renamed "contract". Leave behind: packet route/chain_record/route.py, claim_inventory/claim_measures/phase_ledger/claim_closeout, attempt_grading extractors, overnight launchers, session-ordering-regression/session-mechanics/hard variant. Docs that come: BRIEF invariants + comparison policy, pathologies.md, remediations.md, lessons.md.
- Cadence: (c) — one decision per sitting (<=1 GPU-h, n<=8, attended) until the guards-loaded /implement route runs clean once and the Ornith probe answers; then weekly powered batch (n=12/arm, ~10 GPU-h, unattended). Rules kept: instrument-only cap (token n=1 does not restart the loop); one-page results with recompute commands. New: one review pass, one model, accept or itemized list; no reviews of reviews.
- Maintainer notes: (1) enforce pacing MECHANICALLY, BRIEF.md prose did not hold; (2) a 32 GB M1 Pro is available for slow unattended batches; (3) maximize fake-model / unit-test coverage — record once, replay many.

## 2026-09-14 design-rewrite decisions (Fable brainstorm with Paul)
- Claim: ONE primary — outcome within budget on the ceiling workload (depth-3 R1; self-hosted tasks pending the headroom probe). Secondary, declared, reported regardless: cost at equal outcome on workloads both arms pass.
- Budget unit: tokens and turns (portable); seconds reported per machine only.
- Pathology 4 "unbounded command" (evidence: ceiling probe A1/A4 `find /` at 900 s). Remedy: Engine sets Pi bash `timeout` when absent (120 s) and clamps above 300 s, via the `tool_call` mutation; `tool_result` appends one fixed sentence naming the bound and the self-test command. Values frozen in the Phase 1 plan against measured suite durations. Proven live in Phase 3 (event-changing intervention; replay insufficient).
- Contract fact for hidden-suite tasks carried, not bet on. Pattern refusal deferred. Filesystem sandbox: release-two candidate for /implement only; NEVER applied to Baseline (fidelity to bare Pi); archived 2026-09-02 profile + Claude Code sandbox runtime as starting points.
- Bounds ownership (Paul 2026-09-14: "don't bring over the existing POSIX clamp stuff"):
  - Pi owns the per-command bound (bash `timeout` + its own process-group kill). Engine only sets/clamps the field. No wrapper processes (timeout/perl alarm/ulimit/sandbox-exec) in either tree, ever.
  - Evals keeps exactly two existing bounds, both already imported: the whole-attempt deadline (evidence preservation, `deadline.py`) and adapter process-group teardown (`adapter_process.py`, `pi_session.py` kill/wait). No per-command bound in evals, in either arm — Baseline commands stay unbounded because that is bare Pi. `--timeout` stays the executor-command budget, not a per-command clamp.
  - Engine `runner.py` keeps its own subprocess timeout for the self-test command it runs itself (not a model command).
  - Eval measures per-command durations and tool-reported timeouts from events (census columns), both arms.
- Conditions: warm applies only to the build workload (complaint-lifecycle); repair and self-hosted tasks run cold. Batch runs on this machine if exclusive overnight (~12 h sketch); M1 Pro optional.
- Settings provenance (finding 2026-09-14): arm `inference` blocks were declarations; the served Ornith id was registered in neither oMLX model_settings.json nor Pi models.json → all Ornith cells ran on server defaults (thinking on via chat template, temperature unknown). Fix in flight: `scripts/preflight_settings.py` verifies arm vs both configs, provenance block pasted into pre-run records; README/lessons/ROADMAP/BRIEF updated. Registration of the served id in both configs is applied AFTER the headroom probe's launcher completes (frozen condition), with the card's coding values (temp 0.6, top_p 0.95, top_k 20, min_p 0), thinking on, context cap chosen deliberately.
- Speed facts (server logs): Ornith 1.5 9B median decode 43.5 tok/s (n=588) vs gemma-4-12B 25.8 (n=5806); equal wall clock per misleading-locus cell (~50 s) because Ornith writes 2–3x the output tokens; thinking = 56–68% of output in depth-3 cells.
- DEFERRED MEASUREMENT (Paul): tokens-per-second vs context size on Ornith — a Phase 2 instrument probe (attended, no task outcome): decode tok/s at prompt sizes ~5k/20k/40k/80k/160k from server logs, plus the warm-condition transcripts. Decides the context cap and the warm-condition cost story.

## 2026-09-14 ~11:05Z — settings-provenance merged; headroom probe cell 2 findings
- settings-provenance: 898af1f, 3c6e5a5, fix round d08e912 (Opus review 0C/6I/9M, all I addressed, Sonnet re-review clean) merged into release-one as 9f40bc0 (--no-ff). Gates exit 0. Worktree removed, branch kept. 63 tests. Real check: all three arms FAIL today (Ornith absent from oMLX model_settings.json; gemma entries pin no temperature). preflight.sh step 0a now blocks batches until the server file is registered. Brief premise correction: Pi models.json already had the served id (Sep 9); only the server side was missing.
- Headroom probe (launched 10:43Z): cell-01-G1 guard-prefixes PASS 66 s, 4 tool calls, zero churn. cell-02-R1 run-record-gate NO_PATCH 500 s; model ran `find / -type d -name satyrn_evals`, found scratchpad/rev/basesuite staging, read GOOD run_record.py and hidden tests/test_run_record.py; census said contamination clean, workspace_escapes 0 (detector gap). Then `git commit` inside attempt worktree -> empty working-tree diff -> NO_PATCH (harness artifact). Same `find /` reaches main checkout + worktrees, which hold all answers: self-hosted tasks on this machine are answer-key-exposed by construction. Condition left frozen; controller told to rule, scan all cells post-run.
- Design implications for the spec: (1) hunt pathology reproduced on a self-hosted task = candidate repeatable task; (2) census needs an out-of-workspace absolute-path/`find /` detector; (3) patch capture must diff against workspace_base_sha, not working tree, or forbid/handle commits; (4) self-hosted tasks need the answer key absent from the machine or the run needs an isolated host/sandbox (ties to release-two sandbox candidate).
- 2026-09-14 ~11:30Z: Ornith-1.5-9B-MLX-8bit entry added to ~/.omlx/model_settings.json (backup model_settings.json.bak-2026-09-14T11). Safe mid-run: oMLX ModelSettingsManager loads the file once in __init__ and serves lookups from memory; disk is re-read only on admin "Reload models" or restart. LIVE SERVER STILL ON DEFAULTS FOR ORNITH until reload after the probe. preflight_settings on the Ornith arm: exit 0 (files agree); the check compares files, not live server state. gemma arms still fail (no temperature pinned server-side) — decide: pin 1.0 server-side or drop the field from the arms.
- 2026-09-14 ~11:35Z: Paul: pin temperature 1.0 server-side for both gemma models. Done in ~/.omlx/model_settings.json (backup .bak-2026-09-14T11b). All three arms now preflight_settings exit 0. Live server not reloaded (probe running); reload after probe. Cosmetic: the ok line prints "'baseline'" for all three arms (arm name field, not file stem) — tidy later.
- 2026-09-14 14:25Z: Paul restarted oMLX. Startup log "Loaded settings for 8 models" (was 7; includes Ornith-1.5-9B-MLX-8bit). All three arms preflight_settings exit 0. Smoke request to Ornith: content 'ready', reasoning present, 35.1 tok/s decode. Server log does not print per-request sampling params, so live application of temperature/top_p is inferred from code path (get_settings_for_request reads in-memory _settings loaded at startup), not observed. Every Ornith cell before this restart (pathology probe, ceiling probe, headroom probe) ran on server defaults for sampling.

## 2026-09-14 — Workload decisions (Paul, on Fable deep dive scratchpad/workload-deep-dive/)
- Isolation: two-uid split (harness/grader as Paul, model as dedicated `satyrn-cell` user), ~/satyrn-smokes closed, per-cell TMPDIR, same for both arms. Paul: "I do NOT want Docker" — no container path, not even as a release-two candidate.
- Ceiling set and rule: 4 ceiling + 2 held-out (cut at batch freeze) + 2 floor; Engine wins with >=2 wins, 0 losses, floor parity. ~7 batch nights accepted.
- Budget: 32k output tokens, 48 turns per attempt (transcript tripwire), 1,800 s wall backstop that still scores.
- Fourth ceiling task: cut from Phase 0 Task 9 (tools/review.py).
- If depth-3 re-measures >=2/4 on declared sampling under isolation: move to floor set.
- Ceiling-probe record: annotate with A3 contamination finding; restate Block A as 0/4 uncontaminated.
- Verified by Opus: A3 read pytest-of-pauleveritt/.../agentclinic-repair-misleading-locus/overlay/test_acceptance.py (copied by tests/test_agentclinic_manifests.py refusal test), byte-identical to depth-3 overlay, ran it to 13 passed; summary.json workspace_escapes=1, receipt contamination clean.
import sys
p=sys.argv[1]; s=open(p).read()
old=[l for l in s.splitlines() if "feedback_review_roles.md" in l][0]
s=s.replace(old,"- [Review roles](feedback_review_roles.md) — Opus steers/designs/reviews, Sonnet implements, Fable only when Paul explicitly asks (quota), no haiku")
open(p,"w").write(s)
- 2026-09-14 ~21:45Z isolation spike (no sudo part done): home /Users/pauleveritt is 700 + ACL, so a second uid cannot read checkouts, smokes, Pi config, per-user TMPDIR (700) or the Claude scratchpad (/private/tmp/claude-501 is 700). Leak surface for a second uid = /private/tmp: 1,145 world-readable files mentioning test_acceptance/satyrn_evals written by agents (e.g. new_prefix.py, old_guard_tests.py, exp_selfhost-guard-prefixes.txt). Pi (Volta) and uv live in the maintainer's home -> cell needs its own; Homebrew node/git/python world-readable. oMLX needs no auth. sudo needs a password -> NOPASSWD rule scoped to (satyrn-cell). Pi adapters already pass --no-extensions --no-skills --no-prompt-templates (--no-context-files in session). Scripts: scratchpad/isolation-spike/{setup-as-root,verify-as-cell,undo-as-root}.sh; Paul runs setup with sudo.

## 2026-09-14 ~18:00 — isolation spike result (Paul ran setup + verify)
- WORKS: sudo -n -u satyrn-cell without password; cell cannot read /Users/pauleveritt (home, .pi models.json, evals checkout, satyrn-smokes) nor /private/tmp/claude-501; own 700 TMPDIR; shared dir 2770 round-trip OK; homebrew git/python3/node/npm visible; own uv 0.11.6; oMLX GET /v1/models 200 with placeholder key.
- Pi 0.85.1 install failed in verify only because sudo keeps the caller's cwd (inaccessible to the cell: EACCES uv_cwd). Rerun with `cd "$HOME"` first: installed in 2s, `pi --version` 0.85.1. Launcher rule: every cell command must cd to a cell-readable dir first (worktree or $HOME).
- LEAK CONFIRMED: root-anchored find as the cell returns world-readable full checkouts in /private/tmp: se2 (192M, all task overlays + known-good.patch), scratch-guard (evals src + tools), ornith-clone (484M, fixture captures with acceptance tests), satyrn-evals (empty). Plus loose files (old_guard_tests.py, rescore_cell.py, exp_/act_ selfhost outputs). Hygiene must delete these before any isolated run; launcher preflight should run the same find as the cell and refuse on hits.
- Not tested (no inference): an actual Pi turn as the cell; git ownership ("dubious ownership") when the maintainer creates worktrees the cell writes to.

## 2026-09-14 ~18:20 — Paul: fix the uv line first so Phase 1 closes green
- Supersedes controller R16 "do not fix". Sent to Phase 1 controller as Task 13b after the R18 wave: attempt.py engine spawn env drops UV_PROJECT_ENVIRONMENT (same as 2a Ruling 7), workspace prep keeps it; done when evals gates + integration 0, then mark Phase 1 done in both ROADMAPs.
- On merging phase-2-prep: 2a's Ruling 7 step becomes a verify-only step (already fixed on release-one).
- /private/tmp cleanup: four checkouts + ds4-flash-check + 196 loose entries moved to ~/.Trash/tmp-satyrn-copies-2026-09-14; cell hunt now 0 hits. Held: childhelper.mjs, payload.txt, red.out (Phase 1 agents, <2h old).

## 2026-09-14 ~19:30 — Phase 1 done; phase-2-prep merged; 2a approved and dispatched
- Phase 1 done: evals b7cf775, engine 9ad3583; 13b fixed E5 uv; R21 pump hang parked.
- Merged phase-2-prep into release-one: 69fad8d (clean, no conflicts).
- 2a plan edit 70b1d29: Ruling 11 + Task 5 Steps 0a–0c (R21 engine fix: drop failing sink, keep draining, raise OSError after exit; new engine tests/test_integration_pi_pump.py). Verified in scratch clone: 3 fail/1 pass unfixed (hangs), 4 pass fixed, engine default 486, attempt/delivery/implement integration 70+1 skip. E5 constraint updated (rows now pass); 13b wrapper detector kept while E5 wrapper exists.
- Paul approved 2a; Opus controller dispatched (background), status to scratchpad phase2a-exec/status.md.

## 2026-09-14 ~21:40 — Paul asleep; unattended overnight authority
- Paul: finish 2b unattended, answer questions with my own recommendation, then do overnight work for a run. Then: "Make an exception this time... use the overnight time to catch up" (unattended inference authorized, one time). "You have the GPU to yourself."
- Exception to spec Process ("attended is for deciding and spending") recorded here and in each run record. Scope: preflight under isolation; one trivial Pi turn as satyrn-cell; context-speed/concurrency probe (k); Baseline admission 4x4 (depth-3, run-record-gate, guard-prefixes, review-script) at k, full budget, isolation; floor re-measure (depth-2, docs-linter) if time. No Engine cells, no warm prefix. Set changes recorded but decided by Paul. Stop on infra failure; machine free by 08:00.

## 2026-09-14 22:55 — 2b plan landed; 2b executing; 2c planned in parallel
- 2b plan: 6 tasks, 4,562 lines, 19 rulings, tests verified via replay clone t1–t6 (default 1,772→1,916; integ 276→306+1 skip; 4 pre-existing Xcode-license git rows fail). Committed ec5482f with provenance. Reviewed rulings: accepted as written (unattended authority).
- Decision: 2b Ruling 19 moved the launcher cell loop to 2c; overnight admission needs it. Rather than hand-run cells outside the launcher (violates "launcher is the only path"), plan 2c = cell loop only (≤3 tasks) in parallel against 2b's replay t6; warm prefix moves to a later letter.
- Dispatched: Opus 2b controller (background); Opus 2c plan writer (background, writes file only).
- Note for Paul: /usr/bin/git needs `sudo xcodebuild -license accept` (system setting; his to run).

## 2026-09-15 01:20 — 2b done (772afc2); checklist 1–7 run by me; 2c plan committed
- Step 1: spike removed, chmod +t cells root. Step 2: cell settings.json (compaction 16384, thinking high = maintainer's), preflight_inference exit 0. Step 3: engine export engine-341d4c4 created. Step 4: uv warm all six EXIT 0 on uv sync; AgentClinic collect needs `python -m pytest` (plan's added bare `pytest --collect-only` can't import app): 4 tests collected each. Step 5: preflight_settings --cell exit 0 → ~/satyrn-smokes/2b/settings-cell.json. Step 6: FAILED first: the engine export's tests/test_doc_caps.py matches selfhost-docs-linter's hidden name → moved export to ~/.Trash/engine-export-341d4c4-2026-09-15; rerun problems [] exit 0. Step 7: no cell processes; cells root empty.
- Finding for Phase 3: cell-engine export must exclude the engine's tests/ (or pass the hunt) before any Engine cell; 2b R14 already parked "export hunt guard" to 2c.

## 2026-09-15 02:15 — 2c done (e6ebf6b); night run started
- 2c: 3 tasks, gates 0 (2,009), launch integration 5/5 ×4. R9 rolling loop (arms alternate by start, pairs not guaranteed mixed); R11 infra cells excluded from counts.
- Overnight checklist: step 2 (engine export) skipped deliberately — export leaked docs-linter's hidden test name; no Engine cells tonight. Steps 4–6: settings --cell 0, preflight problems [], no cell processes, cells root empty.
- First isolated Pi turn via launch (records/2026-09-14-first-turn.json de4640f; result 4690a41): complete, OK, pass, 5 turns, 792 output tokens, cwd under cells root, no EACCES/dubious/missing-tool, nothing left. Model ran no git or uv run (watch item still open).
- admit.sh written at ~/satyrn-smokes/2c/admit.sh (plan text + commit trailers).
- Probe started ~02:17 (background).

## 2026-09-15 02:25 — probe done: k = 3
- decode tok/s by prompt: 5k 55.9, 20k 55.7, 40k 53.6, 80k 43.9, 160k 33.8. total tok/s by k: 1 36.5, 2 47.5, 3 60.7 → k=3 (1.66×). No context cap set (2c Ruling 13; Paul decides).
- Ruling (operator): use k=3 per the spec rule. Risk checked: at k=3 each stream ~20 tok/s; max passing Ornith cell in retained probes 21,150 output tokens → ~1,060 s decode < 1,800 s backstop, so k=3 should not convert passes to COMMAND_TIMEOUT. Tripwire: if any admission cell is COMMAND_TIMEOUT with < 24,000 output tokens, later records drop to k=1 (records already written keep their k). Also: at k>1 siblings' worktrees are readable (2c R7); evidence `bash_outside_paths`/overlay scan flags it; reported per record. Cost if wrong: some admission cells time out instead of spending budget; both are fails, pass counts unchanged.

## 2026-09-15 03:05 — depth-3 admission complete (records 2a5372c, result dbc571c)
- Baseline 0 of 4: COMMAND_TIMEOUT 1 (6,802 out, 11 turns), BUDGET_EXCEEDED 2 (39,461/10 turns; 41,861/35 turns), OK-fail 1 (24,129/25 turns). Contamination: 1 graded clean, 0 flagged. Meets ceiling admission (≤1/4, no contaminated pass) — Paul decides.
- Tripwire check: the COMMAND_TIMEOUT cell's unfinished command was a root hunt `grep -rln "model_contract\|preserves_the_shared\|english_language\|complaints_board" / ...` (hung until the 1,800 s backstop), not slow decode. Ruling: keep k=3; the tripwire is narrowed to COMMAND_TIMEOUT cells with <24k output tokens AND no unfinished command. Cost if wrong: none for pass counts. Guard-4 relevance: exactly the Engine's per-command bound case.
- Isolation held: the hunt ran as satyrn-cell across / and the cell did not pass.

## 2026-09-15 03:50 — run-record-gate admission complete (af36aaf, 4212ed3)
- Baseline 0 of 4, all BUDGET_EXCEEDED (29,667/49; 25,907/49; 32,382/43; 32,493/49). No root searches, no overlay windows, no commits. Graded 0.

## 2026-09-15 04:03 — guard-prefixes admission complete (9a3b842, f9c3eb1)
- Baseline 2 of 4 (clean passes 4,475/6 and 4,379/10; two BUDGET_EXCEEDED at 49 turns ~18.6k tokens). By spec rule a ceiling candidate passing >=2/4 moves to floor — Paul decides.

## 2026-09-15 04:20 — review-script admission complete (6f7e9bf, 8f2edd5): INVALID MEASURE
- Baseline 4/4 OK, verdict unavailable ×4 (9.1–13.1k tokens, 21–33 turns, 1 commit each, clean evidence).
- Cause (generator defects, all R1-plan tasks): (1) base keeps AGENTS.md ("every file has a row in PROVENANCE.md; just gates fails") but the generator strips PROVENANCE.md → every model creates PROVENANCE.md, outside source_paths → unavailable (2a Ruling 2). (2) 2b Ruling 12 replaces hidden names with "its test module", so the prompt says "Create: `tools/review.py`, `its test module`" and "uv run pytest its test module -q" → models created its/test_review.py and tests/its.py.
- Consequence: run-record-gate's 0/4 (all BUDGET_EXCEEDED) and guard-prefixes' 2/4 were measured under the same defective prompts/bases; guard-prefixes passes survived. Self-hosted admission results need re-cut + re-qualify + rerun after a generator fix (Paul's call: include PROVENANCE.md in base or in source_paths; strip the AGENTS.md rule; name the test module path generically e.g. "a test module under tests/").
- Ruling (operator): skip docs-linter floor tonight (same defects → low-value cells); run depth-2 floor (AgentClinic, unaffected). No generator change unattended (changes task trees and qualification).

## 2026-09-15 04:25 — depth-2 floor complete (00e4aae, 2b04227): 4/4 clean. Night runs finished; no cell processes; cells root empty. Morning status: scratchpad/overnight-status.md.

# Write the plan: self-hosted generator fix (Phase 2b fix, "2b.1")

Load `superpowers:writing-plans` and follow it. No execution handoff. At most **two tasks**; aim to execute in under an hour.

## The defects (found by last night's admission cells; evidence in `~/satyrn-runs/2026-09-14-admission-selfhost-review-script/baseline/*/patch.diff` and the re-plan ledger `/private/tmp/claude-501/-Users-pauleveritt-projects-pauleveritt-satyrn-evals/553f3cc9-dfd8-475d-89e0-2859bed390d7/scratchpad/re-plan-ledger.md`, 04:20 entry)
1. `tools/cut_task.py` strips `PROVENANCE.md` from `base/` (EXCLUDED_FILES), but the base keeps `AGENTS.md`, which says every file has a row in `PROVENANCE.md` and `just gates` fails otherwise. All four review-script cells created `PROVENANCE.md`; it is outside `source_paths`, so `check_allowlist` (grade.py:163) made every verdict `unavailable`.
2. `HIDDEN_STAND_IN = "its test module"` replaces HIDDEN paths and basenames in the R1-plan prompt, producing "Create: `tools/review.py`, `its test module`" and "`uv run pytest its test module -q`". Models created `its/test_review.py` and `tests/its.py`.

## Rulings (take these; the maintainer delegated the design choice to my recommendation)
- **PROVENANCE.md:** the manifest gains `ignored_paths` (list of repo-relative files, default empty; validated). The generator sets `["PROVENANCE.md"]` on self-hosted tasks. Grading drops patch sections for ignored paths before the allowlist check and before applying the patch, and the grade record lists the dropped paths. The base stays as the spec defines it (no PROVENANCE.md; AGENTS.md unchanged): editing the repository's own conventions out would make the task less like real work. Both arms get the same rule. Cost if wrong: a model spends turns on provenance rows that do not count.
- **Hidden-name wording:** a HIDDEN path is replaced by its parent directory with a trailing slash (`tests/test_review.py` → `tests/`), and a bare HIDDEN basename by "a test module under tests/" (or the parent dir generically). So "Create: `tools/review.py`, `tests/`" and "`uv run pytest tests/ -q`". It never names the hidden file and always names a real directory. Cost if wrong: the model writes its own tests elsewhere under tests/; the overlay still decides.
- Re-cut all four self-hosted tasks (`selfhost-run-record-gate`, `selfhost-guard-prefixes`, `selfhost-review-script`, `selfhost-docs-linter`) with the fixed generator; `cut_task.py check` exit 0; `satyrn-evals qualify` all six candidates ok. Keep 2b R8 (run-record-gate formats disclose the record's fields). The AgentClinic tasks are unchanged (their digests must not move).
- Add a qualification check that would have caught both: a fake attempt that also creates `PROVENANCE.md` grades pass on a self-hosted task; and no R1-plan prompt contains the stand-in text or a path that is not a directory in base or a file in `files`. Your choice of exact form.

## Authority and state
- Spec `docs/superpowers/specs/2026-09-13-release-one-design.md` (generator paragraph, rungs). 2b plan and its ledger `.superpowers/sdd/2026-09-14-phase-2b-isolation-and-tasks/progress.md` (R8, Ruling 12). Evals `release-one` head `2b04227` (2c done; tonight's records under `records/`).
- House style: 2b/2c plans. Global Constraints as there (Sonnet implements, Opus task review, Sonnet re-review, controller blocks, no haiku/Fable, `just gates` 0 per task, provenance rows, commit per task, no merge/push/amend, no /tmp writes, docs caps). Known failing: 4 Xcode-license integration rows.
- Verify every test in a scratch clone under `.../scratchpad/genfix-plan/`, never the main checkout. No inference.
- Last step of the plan: list the exact rerun commands for the operator (not executed by the controller): new admission records `records/2026-09-15-admission-<task>.json` for the four self-hosted tasks via `record new` (Baseline, n=4, k=3, R1-plan, 32,000/48, isolated, `--purpose admission`, `--authority "maintainer-requested rerun after the generator fix, 2026-09-15"`), chained `--previous-result` starting from `records/2026-09-14-admission-agentclinic-repair-depth-2.result.json`, committed, launched one at a time, results committed. The 2026-09-14 self-hosted results stay committed and are marked superseded in the result reading, not edited.

## Deliverable
Write `docs/superpowers/plans/2026-09-15-generator-fix.md` in `/Users/pauleveritt/projects/pauleveritt/satyrn-evals`. Do not commit. Return only: path, lines, tasks, rulings one line each, test verification, the rerun commands.

## 2026-09-15 — Paul: "Plan the generator fix and rerun the self-hosted admissions"
- Rulings given to the plan writer: manifest `ignored_paths` (self-hosted: PROVENANCE.md) dropped from the patch before allowlist/apply and listed in the grade record; base and AGENTS.md unchanged. HIDDEN path -> its parent dir (`tests/`), bare basename -> generic "a test module under tests/". Re-cut 4 self-hosted tasks; AgentClinic digests unchanged; add qualification checks for both defects. Plan <=2 tasks, file 2026-09-15-generator-fix.md. Reruns: 4 new records 2026-09-15-admission-<task> at k=3, chained from depth-2 result; 2026-09-14 self-hosted results kept, marked superseded.

## 2026-09-15 08:32 — rerun run-record-gate (6ed2462, b94b68d): 0/4, all BUDGET_EXCEEDED (27.5k/49, 32.1k/30, 29.2k/49, 24.9k/49), 2 sittings, clean evidence. Same as the 09-14 reading.

## 2026-09-15 08:50 — rerun guard-prefixes (1360c7d, ebb7a6c): 4/4 clean passes (2.3k/5, 27.6k/46, 9.2k/19, 19.5k/34). Fixed prompt turned 2/4 into 4/4: floor by the rule (Paul decides).

## 2026-09-15 09:03 — rerun review-script (90c0b42, 8d55692): 4/4 clean passes (10.0k/25, 6.1k/17, 9.9k/30, 10.6k/30); 3 cells wrote PROVENANCE.md and it was dropped at grading (fix confirmed). Floor by rule. Ceiling set now likely only depth-3 and run-record-gate (both 0/4).

## 2026-09-15 09:53 — rerun docs-linter (47c3dd9, edda258): 1/4 (clean pass 28.5k/48; three BUDGET_EXCEEDED 32.2k/38, 32.1k/30, 30.4k/49). Spec listed it as floor; on the fixed harness it meets the ceiling rule (<=1/4, uncontaminated). Reruns done; cells root empty, no cell processes.
- Admission counts (valid): depth-3 0/4, run-record-gate 0/4 (x2), docs-linter 1/4 -> ceiling-eligible (3). guard-prefixes 4/4, review-script 4/4, depth-2 4/4 -> floor. Ceiling set short of four; Paul decides (accept three with win rule adjusted, or cut more candidates).

## 2026-09-15 ~10:05 — Paul: "proceed" (option 1)
- Spec f966016: ceiling = depth-3, run-record-gate, docs-linter; floor = depth-2, guard-prefixes, review-script; win at >=2 of 3 (null <=0.007); schedule 2–5 nights.
- Next: plan "Engine arm ready for route proof" (Opus writer): export allowlist (no tests/docs/tools) + overlay-digest guard; ENGINE_SOURCES = seven packages/engine/*.ts; commit arms/engine-ornith15-9b.json pinned to 341d4c4; route-proof records through launch. Then controller, then 3 route-proof Engine cells (depth-3, run-record-gate, docs-linter).

## 2026-09-15 ~10:30 — Paul: five nights beyond budget; approved both spec changes (b39590f)
- Batch sittings: 720 min wall clock, no cell cap. Floor tasks n=6 per arm (held-out parity test). Roadmap Phase 4: one night plus a day at k=3.
- Schedule: today Engine arm (~2h) + route proof (3 cells) + held-out cut/qualify + campaign freeze; tonight ceiling 72 cells (~10h); tomorrow held-out 24 + floor 36 (~4.5h) + result pages; day 3 Phase 5. Risk: route-proof bug slips night one.
- Open: roadmap 2d (warm prefix) says "before Phase 4"; recommend deferring (outside win rule).

## 2026-09-15 ~11:30 — held-out cut (clone branch heldout-cut 1030d77 on b39590f)
- selfhost-cell-loop (2c Task 2, 2234240->2ad30ab, launch.py, hidden tests/test_launch.py 22) and selfhost-speed-probe (2b Task 6, bea0b76->ec98c44, speed_probe.py+ROADMAP.md, hidden tests/test_speed_probe.py 17). Both build shape (no repair plan task cut without generator change). qualify 6/6 each; existing 36/36; gates 0.
- Measured public suites: 31.6 s (1,965) and 31.2 s (1,900): fit 120 s self_test bound at 2x like run-record-gate (32.4 s).
- Accepted costs: each base ~17 MB with nested copies of the four earlier self-hosted tasks (their overlays/known-good patches) -> 2,730 PROVENANCE rows; not answer material for the held-out tasks themselves and never concurrent with those tasks'"'"' cells (one record at a time). Grading sets PYTHONPATH (src/scripts) to avoid importing the grader'"'"'s satyrn_evals.
- Cherry-pick after the Engine-arm controller lands (avoid its review diffs). Engine-arm plan 2dc4fbf executing.

## 2026-09-15 ~12:20 — Engine arm built (cc71916, 804a74d, 7f02ea2); held-out cherry-picked cd557c9 (PROVENANCE conflict: both sides kept); gates 0; cut check 0 (6 specs); qualify 48/48 (8 tasks). Engine export 341d4c4 into cells root (allowlist only); preflight_settings engine --cell 0. Route proof depth-3 launched (routeproof.sh).

## 2026-09-15 11:20 — route proof depth-3: INFRASTRUCTURE stop (2581090, 74962c2)
- oMLX shut down cleanly at 10:12 local (server.log: engine pool shutdown, model unloaded); 127.0.0.1:8001 unreachable from maintainer and cell. Launcher stopped correctly (MODEL_ERROR infra). Gap: launch preflight does not check server reachability.
- Real finding: derive gave writable_paths [tests/*] only for depth-3 R1 (engine derive.py _writable_paths takes paths named in the request; R1 names no source location, only tests/). Scope guard 3 would refuse every source edit: Engine cannot pass R1 AgentClinic tasks. Self-hosted R1-plan prompts name Files, so they likely derive correctly.

## 2026-09-15 11:30 — Paul chose "derive falls back"
- Engine (Sonnet, background): when request names no non-test path, writable_paths = top-level tracked entries (files not preserve/checks, dir/*), preserved files stay refused. Evals (Sonnet, background, parallel tree): launch preflight refuses unreachable model server / missing served model.
- After both: Opus review each; bump arms/engine-ornith15-9b.json engine_commit + digests to the new engine commit; re-export engine (new sha dir; old export to Trash); rerun route proof depth-3 as a new record (the 2581090 record stays with its infra result). Needs oMLX restarted by Paul.

## 2026-09-15 ~12:40 — fixes reviewed and re-pinned
- Engine f6f9d23 (derive fallback) + cf71c74 (test-support files count as tests; fallback omits carried files): Opus review approved, Sonnet re-review addressed.
- Evals e96676c + 957f648 (launch and launch --preflight check model server; URL from arm Pi config; every server_model; non-object payload): Opus review found Critical (preflight path unchecked) + 2 Important; fixed; Sonnet re-review addressed.
- Arm re-pinned to cf71c74 (ts digests unchanged), tests updated; gates 2,114; engine pins + launch integration 11 passed; old export trashed, new export engine-cf71c74 in cells root.
- Blocked: oMLX down since 10:12; route proof waits for Paul to restart it.

## 2026-09-15 12:25 — route proof depth-3 relaunched on the same record (31029b0): Engine BUDGET_EXCEEDED, NOT A MEASURE
- Contract fallback correct (app.py, models.py, templates/*, tests/*, uv.lock). Guard 4 worked: command_bounded 18, command_timed_out 1 (a root hunt for acceptance test names cut at 120 s). 28 turns, 32.7k tokens, root_searches 2, no overlay.
- Defect: every TS->engine exchange (self_test, edit) ENGINE_CRASHED exit 2 then MUTATION_CONTEXT_POISONED; model fell back to plain write. Root cause reproduced as the cell: orchestrator.ts:617 spawns `uv run --project <export> satyrn-engine protocol` without --no-sync; uv re-syncs the read-only export (different uid cache) -> Permission denied exit 2. `--no-sync` answers.
- Why earlier tests missed it: isolated Engine rows used the fake pi (no protocol exchange) and/or exports synced/writable by the same uid. Add an isolated row that makes a real protocol exchange on a read-only export owned by the maintainer.
- Fix dispatched (Sonnet): protocol spawn always --no-sync (derive/deliver unchanged). Then: Opus review, re-pin orchestrator.ts digest, re-export, rerun depth-3 as a new record (TAG -b).

## 2026-09-15 12:40 — engine 56f4ac0 (protocol --no-sync; Opus=me reviewed: one argv + comment + node tests both directions; gates 494/143, integration 118+1 skip). Arm re-pinned (orchestrator.ts digest), gates 2,114, pins+launch integration 11, fresh export; protocol call as cell answers. Route proof b depth-3 launched (records/2026-09-15-route-proof-b-agentclinic-repair-depth-3.json).

## 2026-09-15 12:50 — route proof b depth-3 (dc58193, da0f969): BUDGET_EXCEEDED, 9 turns, 42.1k output tokens (thinking-heavy), 13 tool calls (reads, pytest, env checks), 0 edits, 0 self_test, command_bounded 6, no errors, no root search. Protocol fix not exercised live yet. Next: run-record-gate route proof.

## 2026-09-15 13:10 — route proof run-record-gate (result b467aa1): BUDGET_EXCEEDED at 49 turns, 31.3k tokens, 57 tool calls. Protocol exchange WORKS live: engine edits applied, ANCHOR_MISSING and INVALID_REQUEST (absolute path) returned as tool errors, no crash. self_test never called (model tested with bash python -c); guards: command_bounded 38 only; no scope refusals, no loop break. ~12 turns of exploration (AGENTS, BRIEF, cli.py by sed), 8 separate cli.py edits, ran out while writing tests/test_run_record.py. Same shape as Baseline (0/4, 49 turns).

## 2026-09-15 13:30 — route proof docs-linter (fcdfc5f): BUDGET_EXCEEDED, 44 turns, 32.1k tokens, 47 tools (bash 32, edit 10, write 4, read 1). No self_test again. Engine edit refusals: ANCHOR_MISSING x3 (model oldText not matching; one identical edit retried twice), schema maxItems 1 x1 (deliberate mutator rule). Ad-hoc python -c tests x3 failing. command_bounded 31; no scope/loop/symbol firings.
- Phase 3 reading: all 3 ceiling tasks Engine n=1 BUDGET_EXCEEDED. Guards fire where waste occurs (guard 4); binding failure modes are unaddressed: thinking burn (depth-3), no self_test use (0 of 3 cells), exploration/piecemeal edits. Proposed Phase 3b remediation iteration awaiting Paul.

# Write the Phase 3b plan: self_test enforcement

Load `superpowers:writing-plans` and follow it. No execution handoff. At most **four tasks**; aim to build in about two hours. The maintainer approved Phase 3b and this first remediation; decide open design questions as Rulings with your recommendation (the maintainer reviews rulings after).

## Evidence (read the transcripts; do not re-run)
Route-proof Engine cells, isolated, engine `56f4ac0` (except the first): `~/satyrn-runs/2026-09-15-route-proof-b-agentclinic-repair-depth-3/`, `~/satyrn-runs/2026-09-15-route-proof-selfhost-run-record-gate/`, `~/satyrn-runs/2026-09-15-route-proof-selfhost-docs-linter/` (each `engine/<attempt>/transcript.txt`, `summary.json` evidence). All BUDGET_EXCEEDED; **0 of 3 called `self_test`** although the prompt says "Verify with the self_test tool before finishing: it runs "uv run python -m pytest -q" and returns failed test ids with their first assertion line." Instead: run-record-gate ran ad-hoc `bash python -c` checks (several tracebacks) and 8 piecemeal `cli.py` edits, ending at 49 turns while writing tests; docs-linter ran 32 bash calls incl. failing `python -c` probes, 3 ANCHOR_MISSING edits (one identical edit retried twice), 44 turns; depth-3 b spent 42k tokens in 9 turns thinking and ran `uv run python -m pytest tests/ -q` via bash. Baseline admission cells for the same tasks: `~/satyrn-runs/2026-09-1[45]-admission-*`. The ledger `/private/tmp/claude-501/-Users-pauleveritt-projects-pauleveritt-satyrn-evals/553f3cc9-dfd8-475d-89e0-2859bed390d7/scratchpad/re-plan-ledger.md` (entries from 12:25 on) summarises.

## Design space (choose with evidence; Pi 0.85.1 extension API verified from its source — cite what you rely on)
1. **Redirect ad-hoc test runs:** when bash runs the repository's test runner (pytest in its usual spellings: `pytest`, `python -m pytest`, `uv run [python -m] pytest`, with or without paths/flags), the Engine runs `self_test` instead (or in addition) and returns its compact result with one sentence saying so. Consider whether `python -c` probes importing the project should be redirected, nudged, or left alone.
2. **Completion gate:** if the model ends its turn/session with mutations since the last `self_test` (or never ran it), the Engine runs `self_test` itself, or sends one follow-up message asking for it (once per mutation generation). Check how `pi.sendUserMessage` / `agent_end` / `turn_end` behave in print/json mode (the eval runs `pi -p --mode json`).
3. **Automatic feedback after mutations:** e.g. run `self_test` after a write/edit batch when the model next issues a non-mutation tool; cost: ~30 s suites.
4. **Prompt wording:** stronger instruction is cheapest; route proof shows wording alone is not enough, so wording can only accompany a mechanism.
Recommendation to test first (you may overrule with reasons): 1 + 2. Each firing is recorded via `appendEntry` with a new customType (e.g. `self_test_redirected`, `self_test_enforced`) and counted in the receipt's `guard_firings` and in evals' `pathology.GUARD_KINDS`/evidence so Phase 4 reads it.

## Measurement (the Phase 3b done-when for this change)
Development records only, on tasks outside the ceiling (depth-3, run-record-gate, docs-linter), floor (depth-2, guard-prefixes, review-script) and held-out (cell-loop, speed-probe) sets. Candidates: `agentclinic-repair-misleading-locus`, `agentclinic-repair-complaint-lifecycle`, and at most one fresh self-hosted dev task cut with `tools/cut_task.py` from a plan task no claim task uses (the held-out cut report rejected several; pick a build-shaped one). Plan the operator commands (not executed by the controller): Engine arm at the new engine commit, isolated, `--purpose development`, n=2 per dev task at k=3, before (engine 56f4ac0 export) and after (new commit) — or after only if you rule the before is not needed; state why. Target behaviour: `self_test` calls per cell > 0 and ad-hoc pytest bash runs replaced; secondary: turns and tokens to first passing self_test. The plan's last step lists those commands and a short reading template.

## Trees and rules
- Engine `/Users/pauleveritt/projects/pauleveritt/satyrn-engine` release-one `56f4ac0` (TS extensions in `packages/engine/`, bounds.ts is guard 4's pattern for intercepting bash; runner.ts owns `self_test`; replay fixtures and `tools/replay_*` prove guards without a model). Evals `release-one` `91b6da8` (arm pins `arms/engine-ornith15-9b.json`, `arms.ENGINE_SOURCES`, `pathology.GUARD_KINDS`, `cell_evidence`). The Engine arm re-pin and re-export are a plan step.
- Global Constraints as in the 2c/engine-arm plans (Sonnet implements, Opus task review, Sonnet re-review, blocking dispatch, no haiku/Fable, gates 0 per task in each tree, provenance rows, commit per task, no merge/push/amend, no /tmp writes, isolated rows serial, cells root holds only the current export). No inference while building.
- Verify every test in scratch clones under `.../scratchpad/selftest-plan/`, never the main checkouts.
- The identical-prompt rule: prompts stay identical across arms; the Engine's own tool results and messages are the product and may differ.

## Deliverable
Write `docs/superpowers/plans/2026-09-15-phase-3b-self-test-enforcement.md` in the evals repo. Do not commit. Never end your turn while a child runs (Sonnet surveys only, run_in_background false). Return only: path, lines, tasks, rulings one line each (design choice first), the Pi API facts relied on, test verification, operator commands.

## 2026-09-15 13:40 — Paul: add Phase 3b and plan self_test enforcement
- Spec/roadmap 91b6da8: row 3b (one day, dev records on tasks outside ceiling/floor/held-out; engine freezes after). Roadmap row 3 marked done.
- Plan writer (Opus) dispatched: <=4 tasks; recommended design = redirect bash test-runner invocations to self_test + completion gate when mutations since last self_test; firings recorded via appendEntry and counted; measure on dev tasks (misleading-locus, complaint-lifecycle, maybe one fresh cut) n=2 at k=3 isolated. Night one moves to tomorrow.

## 2026-09-15 14:20 — before measurement + plan landed
- Plan fc6f820 (4 tasks): redirect pure pytest bash runs to self_test (self_test_redirected); completion gate at turn_end with no tool call runs self_test, one follow-up on failure (self_test_enforced); evals counts; re-pin (runner.ts digest). Controller dispatched (engine tasks now, evals after before-results commit).
- Before locus (51ab8df, c719689): Engine 2/2 pass, 5–6 turns, 1.2–2.0k tokens; EACH cell called self_test once at the end (one also ran pytest via bash first). So the model does use self_test on easy tasks; on ceiling tasks it exhausted the budget before verifying. Implication: the completion gate never fires in a BUDGET_EXCEEDED cell; redirect helps only where bash pytest runs occur. The dev tasks are too easy to show ceiling-relevant movement. complaint-lifecycle through launch is a build over an empty repo with no tests (self_test exit 5): behaviour-only, already running.
- Operator view: the binding failure on ceiling tasks is budget exhaustion before convergence (thinking, exploration, piecemeal edits). Candidate next remediation: early automatic self_test after the first mutation batch (plan design 3, deferred) and context seeding; needs a harder dev task.

## 2026-09-15 14:25 — before complaint-lifecycle (d9990a1, 7a595ec): 0/2 (BUDGET_EXCEEDED 1 at 30.6k tokens with 45 bash, 1 self_test; NO_PATCH 1 at 20.1k with 34 bash, 3 self_test). Behaviour-only task (no tests). Before sitting done; cells root holds only the 56f4ac0 export; controller may proceed to evals tasks.

## 2026-09-15 ~15:10 — Phase 3b build done: engine 128ce82, 316432c, 8049d73 (test-only fix); evals 213e8bb, 35374b1 (pin 8049d73), 79a74eb (plan after-procedure fix). Gates: engine 494/152, integration 118+1 skip; evals 2,131; replay 4 self-test fixtures pass. Export 56f4ac0 trashed; 8049d73 exported; preflight_settings --cell 0. After cells launched (locus then lifecycle, devcell.sh label after, chained with &&).

## 2026-09-15 15:30 — after cells (92d41e5/1e4452d locus; 1b06857/49c58ef lifecycle), engine 8049d73

- misleading-locus: before 2/2 pass (6 t/2.0k, 5 t/1.2k; self_test 1,1; bash tests 1,0); after 2/2 pass (11 t/2.7k, 5 t/0.8k; self_test 1,1; bash tests 1 redirected, 0). No change.
- complaint-lifecycle (no tests; behaviour only): before 0/2 (BUDGET 49 t/30.6k, NO_PATCH 40 t/20.1k; bash test runs 17 and 6; self_test 1, 3); after 0/2 (BUDGET 46 t/32.3k, BUDGET 49 t/27.0k; bash test runs 2 (both redirected) and 0; self_test 2, 3).
- Reading: target moved (ad-hoc bash test runs 23 -> 2, both redirected); completion gate fired 0 times (cells end at budget, as predicted); outcomes unchanged. Engine 8049d73 is a safe improvement but not ceiling-moving. Decision to Paul: freeze vs next remediation (early auto self_test after first mutation batch + context seeding) on a harder dev task.

# Deep review: why the Engine does not lift Ornith on the ceiling tasks, and what to do before Phase 4

The maintainer (Paul, sole maintainer, volunteer hours, days not weeks left) asked for your deep review. Be candid; a well-argued "stop, the claim won't hold" is a valid answer. Read-only: do not edit repository files, do not commit, no model inference, do not touch `/Users/Shared/satyrn-cells` or run isolated tests. You may dispatch Sonnet or Opus subagents for read-only surveys (blocking, `run_in_background: false`); no haiku.

## The claim and rules
Spec: `/Users/pauleveritt/projects/pauleveritt/satyrn-evals/docs/superpowers/specs/2026-09-13-release-one-design.md` (release-one). Release one claims the Engine (`/implement`: derived contract, guards 1–4, symbol preservation, carried tests, `self_test`, receipt) takes Ornith 1.5 9B (oMLX, temp 0.6, thinking on high) past its ceiling within a 32k-output-token / 48-turn budget, isolated as `satyrn-cell`, k = 3. Win: ≥2 of 3 ceiling tasks reject for the Engine (one-sided Fisher, n = 12 per arm: Baseline 0/12 needs Engine ≥4/12; 1/12 needs ≥6/12), no losses, floor parity (n = 6). Phase 3b (one day) allows Engine remediations measured on development tasks outside the ceiling, floor and held-out sets; the engine commit freezes after. Identical prompts, tools, model and sampling across arms.

## Evidence (all retained; read transcripts, not just summaries)
- Ledger with every decision and reading: `/private/tmp/claude-501/-Users-pauleveritt-projects-pauleveritt-satyrn-evals/553f3cc9-dfd8-475d-89e0-2859bed390d7/scratchpad/re-plan-ledger.md` (2026-09-15 entries from 02:25 on are the live-model evidence).
- Baseline admission (isolated, k = 3): `~/satyrn-runs/2026-09-14-admission-agentclinic-repair-depth-3/`, `~/satyrn-runs/2026-09-15-admission-selfhost-run-record-gate/`, `~/satyrn-runs/2026-09-15-admission-selfhost-docs-linter/` (ceiling: 0/4, 0/4, 1/4); floor `...-guard-prefixes`, `...-review-script` (2026-09-15), `2026-09-14-admission-agentclinic-repair-depth-2` (4/4 each). Superseded 2026-09-14 self-hosted nights exist too (prompt defects; ignore for outcomes). Each has `baseline/<attempt>/transcript.txt` (Pi json events incl. thinking and usage), `summary.json` with an `evidence` block.
- Engine route proof, one cell per ceiling task (all BUDGET_EXCEEDED, 0 self_test): `~/satyrn-runs/2026-09-15-route-proof-b-agentclinic-repair-depth-3/` (9 turns, 42k tokens, thinking-heavy), `...-route-proof-selfhost-run-record-gate/` (49 turns), `...-route-proof-selfhost-docs-linter/` (44 turns). The first depth-3 route proof (`2026-09-15-route-proof-agentclinic-repair-depth-3/`) had a now-fixed engine crash (protocol spawn without --no-sync) — not a measure.
- Phase 3b before/after development cells (Engine 56f4ac0 vs 8049d73 = pytest-in-bash redirected to self_test + completion gate): `~/satyrn-runs/2026-09-15-dev-{before,after}-agentclinic-{repair-misleading-locus,complaint-lifecycle}/`. Reading in the ledger 15:30: redirect fired (bash pytest runs 24 → 3, all redirected), gate never fired, outcomes unchanged; misleading-locus is easy (passes in ~5 turns), complaint-lifecycle has no tests (behaviour only).
- Engine source: `/Users/pauleveritt/projects/pauleveritt/satyrn-engine` release-one `8049d73` (`packages/engine/*.ts` guards and runner; `src/satyrn_engine/derive.py`, `attempt.py` prompt at ~354). Evals: `/Users/pauleveritt/projects/pauleveritt/satyrn-evals` release-one; `records/` holds every record and result.
- Probe: decode 55.9 tok/s at 5k prompt → 33.8 at 160k; k = 3 total 60.7 tok/s.

## Questions
1. **Diagnosis.** From the transcripts, where do ceiling cells (both arms) actually spend output tokens and turns? Quantify: thinking vs visible text vs tool args; exploration turns before first edit; edit churn; test runs; time to first failing-test signal; context growth per turn. How do the Engine route-proof cells differ from the Baseline cells on the same tasks? Is the binding constraint budget (tokens/turns), capability (the model can't solve it even with unlimited budget — look for cells that were close), or task/prompt design?
2. **Does any Engine remediation plausibly move 0–1/12 to ≥4–6/12 on two of three ceiling tasks?** Evaluate at least: early automatic `self_test` after the first mutation batch; context seeding (file outlines/contents in the prompt); edit batching; a planning/decomposition step; turn-budget-aware nudges; anything the evidence suggests that I have not listed. For each: mechanism, evidence it targets the binding constraint, expected effect size, cost to build and measure, risk to floor parity.
3. **Is the claim design itself the problem?** E.g. thinking level fixed across arms (thinking burn); 32k/48 budget; R1/R1-plan prompts; ceiling tasks that are really capability-bound; n and power; k = 3 contention. What change (if any) would be legitimate rather than tuning, and what would it cost in credibility?
4. **Recommendation** for the next 1–2 days with a decision tree: which remediation(s) to build and how to measure them in Phase 3b (which development tasks — consider cutting a harder one; how many cells), what result would justify running Phase 4, and when to stop with a stated negative. Include anything in the harness or evidence you think is wrong or misleading.

## Deliverable
Write your review to `/private/tmp/claude-501/-Users-pauleveritt-projects-pauleveritt-satyrn-evals/553f3cc9-dfd8-475d-89e0-2859bed390d7/scratchpad/fable-3b-review/review.md` (as long as it needs, with numbers and file:line or transcript citations; put a one-screen summary with the recommendation at the top), and save any analysis scripts and outputs under `.../fable-3b-review/evidence/`. Never end your turn while a child agent runs. Return only the summary section.

## 2026-09-15 15:40 — Paul: "Ask Fable for a deep review of this". Fable dispatched (read-only) with brief scratchpad/fable-3b-review/brief.md: diagnosis of token/turn spend in ceiling cells both arms, whether any remediation can reach >=4-6/12 on 2 of 3, whether the claim design (thinking level, budget, rungs, k) is the problem, and a 1–2 day decision tree. Output review.md. GPU idle meanwhile.

## 2026-09-15 ~16:35 — Fable review landed (scratchpad/fable-3b-review/review.md)
- Verdict: claim as posed will not hold; no one-day remediation changes it. depth-3 R1 information-bound (tzinfo seam hidden by R1 text; 0/7 cells found it; two cells spent the budget in one 32k-token turn, max_tokens = budget). run-record-gate spec-ambiguity-bound (errors.py outside source_paths in 5/9 cells; gate rules vs load_run_record trap; one Baseline cell passing at turn 39 then tripped). docs-linter budget-edge; Baseline too good to power a win.
- Options: A stated negative now (0 GPU); B futility-look night only (~5–6 GPU h); C fix tasks, replace a ceiling task, finish-on-green + hygiene, fresh dev cut, then Phase 4 (3+ days, P(win) ~20–30%).
- Flags: BUDGET_EXCEEDED worktrees ungraded; per-turn max_tokens = budget; k=3 check (Fable compares 60.7 vs 55.9 single-stream decode; probe rule used total_tok_s_by_k 36.5 at k=1 -> 1.66x; the k=1 total looks low vs decode, verify); mutator maxItems 1; self_test runs suite twice; gate cannot fire at budget.

## 2026-09-15 ~17:10 — Paul chose A. Outcome committed 58742be: docs/superpowers/specs/2026-09-15-release-one-outcome.md (docs/results is launcher-only by hook, so the stated negative sits beside the spec); evidence/2026-09-15-release-one-outcome/ (Fable review + scripts; stats recompute verified); spec header marks concluded; roadmap: 3b done, 4 not run, 5 stated negative, release two R0–R5 proposed; gates 2,131. Engine frozen 8049d73; cells root holds its export.

## 2026-09-15 ~17:30 — lesson + R0 constraints committed bf4347f (docs/lessons.md entry "We built the remedy for the failures we saw..."; docs/superpowers/specs/2026-09-15-release-two-r0-constraints.md; roadmap R0 links it).

## 2026-09-15 ~18:00 — Paul approved the pre-registration (3f5a8a9) and decoy cleanup. Cleanup agents running (evals + engine, docs only). Counterfactual plan writer (Opus) dispatched: <=2 tasks; hard rule: prototype/verify on debug cells only, never read decision cells; plan file docs/superpowers/plans/2026-09-15-finishing-counterfactual.md.

## 2026-09-15 ~17:40 — decoy cleanup done: evals 28cb6b0 (+ wording fix), engine ea49666. Reviewed: both read-orders re-pointed; engine BRIEF no longer forbids re-opening; pathologies/remediations banner + per-entry status (19); corpus KNOWN_DEFECTS.md (per-task file would change task_tree_sha256).

## 2026-09-15 ~18:45 — Paul: record amendment with verify, send to controller. Spec section 7 pre-run amendment + plan committed 6599a4e (7.1 insufficient positive -> verify; 7.2 grades under ~/satyrn-counterfactual-grades; 7.3 disclosure of prior Fable pass-state knowledge). Controller (Opus) dispatched: Task 1 build+review, mandatory Opus line-by-line review gate, then single decision run, README, R0 row.

## 2026-09-15 ~19:40 — review gate stopped the run (no decision cell touched; commits 434b4ad, be18c1c, 3ddd9fe). Paul approved: spec 7.4 conservative rescues committed 0e33034 (rescue only if every bash command to the trigger replayed or provably read-only, else unverified-rescue; harms unchanged). Controller resumed with 7.4 + two code fixes (same-step write+green triggers; errored original + identical failed replay is not a skipped writer), re-gate, then single decision run.
