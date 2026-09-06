# Archive

> **Completed phases and superseded framings, most recent first.** Moved
> verbatim from `ROADMAP.md`'s "Prior work" section on 2026-09-06, so the
> planning surface stays inside its 400-line cap.

This file is append-only and **deliberately uncapped**: the roadmap's cap
exists so the planning surface stays readable, and this is where the
overflow is meant to go. Capping it would only create a third file. See
`docs/sdd.md`, "Document caps." A session does not need to read this file
to work — `CLAUDE.md`'s read-in-full list is `BRIEF.md` and `ROADMAP.md`.

- **V10 — Transcript-derived pathology counts (2026-09-04).** An offline
  reader of the preserved Pi attempt transcript reports tool calls, repeat,
  churn, no-op edits, `test_runner_commands` (command-text evidence, **never**
  proof that tests ran), `tool_free_terminal_turns`, workspace escapes and
  overlay windows. Absent or unparseable data is **`unmeasured`, never zero** —
  the discipline four recorded silent-zero incidents paid for. No engine
  telemetry seam changed and no causal claim follows from a count. A standing
  limit the V11 smokes must clear: all eight preserved 2026-09-03 Baseline
  reprobe transcripts read `unmeasured: unknown_event` because they carry
  `tool_execution_update`, so **a non-empty transcript is not proof V10 can
  measure it**. Design:
  `2026-09-04-v10-transcript-pathology-counts-design.md` (adjustments A1–A4,
  tightenings S1–S2, reviews in its research companion); plans
  `2026-09-04-v10-p*`; verification record `docs/sdd.md`.
- **V9 — Loop integrity and re-scoring (2026-09-04).** The batch loop
  survives a failing cell: every cell's record is written before grading
  (`GRADE_FAILED` when grading did not complete), summaries name
  task/command/timeout, and `regrade ATTEMPT_DIR` + `summarize OUTPUT_DIR`
  make BRIEF rule 3 executable — the rebuilt summary is byte-identical to
  the run's own. T5 preservation grading stops auto-overlaying; T6's
  umask-002 stored-file refusal is removed (recorded correction); T7's
  oracle-hook shim keeps the locked env authoritative; T8's grading git
  runs in the cleaned environment; T9 is stated as a limit beside BRIEF
  rule 4; the 30 s attempt default is 900 s. A post-implementation review
  closed three structural blockers: aborted runs write `aborted.json`
  (requested/completed/error, never `summary.json`), `summarize` rebuilds
  over the run's own recorded cells (strays cannot change it), and a
  git-environment probe failure is one `UNAVAILABLE` cell, not a batch
  abort. Default tier 748; full gate 1000 passed, 100% statement +
  branch. Design: `2026-09-04-v9-loop-integrity-and-rescoring-design.md`;
  plans `2026-09-04-v9-p*.md`; verification record `docs/sdd.md`.
- **V8 — AgentClinic through Evals (2026-09-04).** Six bundled
  `agentclinic-repair-*` tasks vendored from the `swiftstar` companion
  repository (MIT, notice retained): reconstructed broken bases as locked
  projects, the full 13-test acceptance suite as a hidden per-task overlay,
  and failure-digest contracts that never name a grader file. Two
  production changes: `grade` materializes a dependency-bearing task's own
  locked environment and attests the executed distributions as
  `resolved_versions` from `uv pip freeze` (stdlib tasks untouched, no key);
  the contamination detector subtracts base-visible overlay windows
  (additive). The 24/24 offline gate proves every task by fixture name
  (base rows from hook records, six known-good 13/13, six known-broken
  fails, six contamination pairs). The uncounted V5d smoke — one real-model
  stock-engine attempt on `plausible-wrong-fix` — passed end to end after
  the engine's pi-argv fix it surfaced (recorded, not fixed in V8). The
  budgeted admission probe stays closed in `BACKLOG.md` until its reopen
  condition is met. Spec and plan under `docs/superpowers/`; verification
  record in `docs/sdd.md`.

- **V7 — Task visibility and leak detection (2026-09-04).** A manifest
  field (`oracle_visibility`) declares each task visible- or hidden-oracle,
  enforced by the ⇔ rule with `grader_overlay` and an authoring-time name
  check. Contamination on hidden tasks is detected by content — a pure,
  verbatim block-rule tripwire with evidence pointers — and reported per
  graded artifact as `flagged`/`clean`/`unmeasured`, never changing a
  verdict, an exit code, or a denominator; an ordinary attempt's `clean`
  covers its preserved patch and the workspace-absence invariant only, not
  the engine transcript. Read-only modes ship with their stated limit:
  `0o444` at materialization is accidental-exposure prevention, not
  security isolation, and a stored-file check refuses group/other-writable
  overlay files. Every summary from V7 names its `cells` and
  `oracle_visibility` (closing the V5 evidence-provenance correction);
  hidden-task summaries carry the contamination tally with
  `flagged + clean + unmeasured == graded`. Spec:
  `2026-09-04-v7-task-visibility-leak-detection-design.md`.
- **D1 — Documentation orientation (2026-09-04, amended the same day).** The
  public docs use a Diátaxis structure: a first-time reader sees the
  actionable-evidence promise and a successful `format_number` receipt before
  operational guides, explanatory topics, CLI reference, or development
  history; capture, attempt, and diagnostic-batch instructions are organized
  by desired outcome; the task/artifact formats have a reference page;
  the architecture and glossary are current. Reopened 2026-09-04 for review
  corrections, then amended: a deep review's nine findings (formats
  reference, guide execution context and `--tasks-root`, capture-record
  filename, refusal and smoke semantics, architecture/glossary currency, the
  receipt example, EOF blank lines) plus the front-page suite example, all
  recorded in the design spec's amendment. Design and plan:
  `2026-09-04-d1-diataxis-documentation-design.md` and
  `2026-09-04-d1-diataxis-documentation.md`.
- **D2 — The learner's big picture (2026-09-04).** A dedicated learner page (`what-actually-happens`) wired into Start here after the first verdict — front page → tutorial → learner page → guides — teaches in ordinary words what actually happens when an AI coding agent works, then maps those pieces onto Evals' evidence loop. Diagram 1 (agent ↔ codebase + tools → inference server containing the model, with request/token edge labels) sits inside that page; diagram 2 (Evals evidence loop) redraws diagram 1's whole agent loop as the opaque attempt command whose patch + transcript are graded offline into a receipt. Zero runtime JavaScript; the sdd discipline bullet and the review template's Visual assets group hold both figures legible at documentation width in light and dark Furo. **Bake-off: PASS — d2 v0.8.2** (`--sketch --theme 0 --scale 0.5`) rendered both diagrams from committed `.d2` sources byte-for-byte; no hand-authored fallback. Design: `2026-09-04-d2-learner-big-picture-design.md`.
- **V6 — Session eval (2026-09-04).** `session TASK -- ADAPTER...`:
  one conversation against one evolving checkout, cumulative checkpoints
  snapshotted and durably linked before the next prompt, offline grading
  through a grader overlay the executor never sees, and a shipped Pi
  adapter over `pi --mode rpc`. Two independent reviews drove recorded
  corrections: prompt-wide deadlines, cleaned Git environment, per-
  checkpoint durable records, collector selectors, context_reset as a
  protocol failure, message_update retention, Pi-declared terminals,
  scope-preserving source_paths, and preservation `invalid` on
  protected-test edits. Session runtime policy
  (`PYTHONDONTWRITEBYTECODE`) keeps bytecode out of the workspace. Three
  uncounted real-model smokes on the local model passed plumbing.
  Bundled `session-mechanics` grader fixture; svcs materialization and
  qualification remain a separate proposal.
- **V5d — The pre-flight smoke check (2026-09-03).** The revised proposal
  was confirmed and landed as a documented practice, not new code: one
  uncounted real-model smoke per materially distinct execution path, at
  that path's first real use; the attempt record read always and the
  receipt only when grading occurred; `NO_PATCH`/`COMMAND_TIMEOUT`
  passing only on positive evidence the model started; durable, uniquely
  named smoke evidence. Supersedes the V5c reconciliation's decision 4,
  which had kept V5d off main while unconfirmed. Spec:
  `2026-09-03-v5d-preflight-smoke-check-design.md`.
- **V5c — Capture the admitted suite (2026-09-02).** `local-pings` is
  captured as a bundled task with the `format_number` shape: manifest with
  the five-id oracle (three upstream local-ping tests plus the two-order
  curator preservation parametrization `[order0]`/`[order1]`), `base/` (the
  N=6 synthetic base; `pyproject.toml` gains `pythonpath = ["src"]` so
  uninstalled tree copies run), known-good and known-broken fixtures, and
  the engine contract. The gate re-recorded at N=6 across fresh processes
  with the canary reporting the scramble face every run: base 0/5,
  known-good 5/5, type-set 3 pass / 2 fail (caught 20/20). Row 3's
  adversary was re-specified by maintainer-confirmed amendment — the
  recorded N=2 type-set does not reproduce on this machine, and the
  cross-machine investigation (research record) shows the set-order catch
  is a discrete function of hash stride versus table geometry and
  allocation phase; the object-set substitution was dropped, and the gate
  gained a canary whose third outcome (inconclusive) stops capture. The
  `local-pings` admission numbers are recorded as unearned pending a
  re-probe against the captured task. The re-probe (2026-09-03) then
  recorded both arms middle (Baseline 3/8, Engine 4/8), and the maintainer
  **de-admitted `local-pings` as a diagnostic workload**, retaining it as a
  bundled grader/smoke/regression fixture
  ([record](docs/superpowers/research/2026-09-03-local-pings-deadmission.md);
  the re-probe results carry the numbers). Spec amendment, reconstruction
  correction, research record, and de-admission record under
  `docs/superpowers/`.
- **V5b — The diagnostic loop (2026-09-02).** `run TASK --n 8 -- COMMAND...`
  repeats the attempt seam and writes a counts-only `summary.json` — verdict
  reasons (`code_counts`/`verdict_counts`), timeouts, and the outcome tally.
  Its four transcript-derived metrics — tool calls, repeat, churn, context —
  were deferred to an engine-side emitter rather than parsed evals-side
  (`BACKLOG.md`; the V5b spec's Out of scope): the loop ships, while the
  diagnosis it is named for waits on that engine-side field. Spec and plan
  recorded under `docs/superpowers/`.
- **V5a — The admission rule (2026-09-02).** Decided the admission bar:
  the middle-band rule applies to the arms under comparison, not to the
  bare-Pi reference alone. The superseded kickoff framing named four probed
  tasks — `local-pings`, `stringified-annotations`, `magicmock-factory`, and
  a multi-prompt `svcs` session — and stated "**No probed task has a bare-Pi
  baseline in the middle band.**", then posed the decision:

  > is the admission bar "middle-band for bare Pi", or "discriminates between
  > the arms under comparison"? Under the first, four rigorously qualified tasks
  > are discarded. Under the second, at least two are admissible today.
  > `BRIEF.md`'s middle-band rule assumes the first without saying which arm is
  > the baseline, and that ambiguity now blocks the diagnostic loop.

  The corrected probes falsified the floor-is-a-wall reading (0/4 successful
  attempts with 2/2 constructible retained quality on `local-pings`; Engine
  2/4 in the follow-up; Engine 6/6 vs Baseline 0/6 in the pilot), so the
  decision admits the two tasks whose recorded arms separate: `local-pings`
  (Baseline floor / Envelope floor / Engine middle; **superseded for the
  captured task by the 2026-09-03 de-admission** —
  [record](docs/superpowers/research/2026-09-03-local-pings-deadmission.md))
  and `stringified-annotations` (Baseline floor / Envelope floor / Engine
  ceiling). `magicmock-factory` (Baseline floor, no other arm recorded) is
  unadmitted on an evidence gap; the multi-prompt `svcs` session is deferred
  to V6. `BRIEF.md` and `docs/glossary.md` were amended with the old wording
  kept in notes. Design spec and GLM 5.3 review recorded under
  `docs/superpowers/`.
- **V4 — A real engine attempt (2026-08-23).** Evals reconstructs a private
  Git repository from the persisted task base, runs the executable once in a
  detached worktree, preserves its artifacts before cleanup, and proves the
  seam with a real Engine E5 attempt.
- **V3 — Attempt persistence (2026-08-18).** `attempt TASK -- COMMAND...`
  runs an executable through the environment seam in a disposable workspace,
  preserves patch and transcript before cleanup, grades the preserved patch,
  and writes an attempt record.
- **V2 — Capture by revert (2026-08-18).** `satyrn-evals capture --revert
  SHA [--repo PATH] [--name NAME] [--contract TEXT] [--output DIR]`:
  four deterministic checks, a detached-worktree lifecycle re-earned from
  the engine's E3 spec, optional `known_broken`/`provenance` in the
  manifest, the E3-shaped capture record, `grade --tasks-root`, and the
  oracle hook recording collection errors. Spec, plan, and revisions are
  recorded under `docs/superpowers/`.
- **V1 — It installs and grades (2026-08-16).** `satyrn-evals grade TASK
  PATCH [--receipt PATH]`: manifest-validated tasks, allowlisted unified
  diffs, hook-result verdicts, receipts, the audit-hook tripwire, and two
  test tiers. Spec, plan, and corrections are recorded under
  `docs/superpowers/`.
