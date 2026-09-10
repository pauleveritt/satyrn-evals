# HP3 composition: wiring chained isolation into the packet route

Written 2026-09-10. TE1's remaining exit blocker, not a numbered HP cycle
of its own — HP3 is `satyrn-engine`'s cycle, accepted there 2026-09-10;
this is the composition TE1 itself names as the readiness blocker
("The treatment, resolved", `engine-turn-efficiency-plan.md`). Design
only: **it authorizes offline implementation; it does not authorize any
live `pi` process or any inference.**

## Why this is architectural, not a new seam bolted onto the old one

HP2's route was built explicitly around one fact, stated in
`adapters/pi_implementer.py`'s own docstring: **"a route workspace is a
plain directory... not a git checkout."** HP3 composition inverts that
assumption, and the inversion cascades through three more places that
were quietly built on top of it. Each is verified against actual code
during this design's own research, not assumed:

1. **`deliver` deletes the isolated worktree on success.** Confirmed in
   `satyrn-engine/src/satyrn_engine/delivery.py`: cleanup runs whenever
   `state.needs_cleanup`, and `worktree_path` in the receipt is non-null
   only when cleanup *fails*. Only the git commit survives a successful
   phase. `chain_record.capture_candidate` reads candidate file content by
   opening files from a workspace that, for this route, is already gone by
   the time it runs.
2. **`deliver`'s own receipt already reports `changed_paths`.** Confirmed
   against `satyrn-engine`'s CLI JSON output
   (`tests/test_integration_delivery.py`'s fixtures). `attribution.snapshot`'s
   whole-tree content-digest diffing exists to answer a question this seam
   answers for free.
3. **No orchestrator window exists to observe.** Each phase's worktree is
   isolated and destroyed before the next phase's exists; nothing is
   shared between them but git history. HP5's attribution — built to catch
   an orchestrator silently doing an implementer's work between handoffs —
   has no vector to guard against here: `orchestrator_mutations` becomes
   `()`, a structural guarantee, not an observed-empty assumption.
4. **`pi_implementer.py` conflates two things that must split.** `main()`
   derives `workspace` from `RESULT_ENV`'s parent, then uses that single
   path both as the Pi child's `cwd` (where edits happen) and as where
   harness bookkeeping files (transcript, stderr, counter) land. For HP3,
   Pi's edit target must be the isolated worktree `deliver` creates;
   harness files must **not** land there, or they get swept into the
   candidate commit as contamination.
5. **The packet's `base_revision` and the engine's `base` are different
   things.** `base_revision` is a content digest of the task tree
   (`hashlib.sha256` over file bytes) — an HP2 packet-declaration concept,
   `declared_not_applied` today and staying that way. `deliver --base`
   needs a real git commit-ish. Composition introduces a **second**, new
   kind of base tracking — the running candidate commit across phases —
   that has no relationship to the packet field of a similar name.

## The four pieces, and why they're one spec

Piece B exists only to make piece D's worktree isolation real. Piece C
exists only because piece D's worktrees don't persist. Designing them
separately risks piece B or C being built against an imagined version of
D's actual call shape, discovered wrong only once D is written.

### A — packet → `Contract` rendering

`satyrn-engine`'s `Contract` (`contract.py`): `id`, `task`,
`writable_paths`, `test_command` — a YAML file per phase. `HandoffPacket`
carries more (`facts`, `preserve`, `redacts`, budgets, `role`) that has no
structured home in a `Contract`.

- `task`: reuse `packet.render_packet(packet)` verbatim — it already folds
  `objective`/`facts`/`preserve`/`self_test_command` into one text blob,
  the same rendering `pi_implementer.py` already sends as the prompt.
  **Not a second rendering function.**
- `writable_paths`: `packet.writable_paths`, direct.
- `test_command`: `packet.self_test_command`, direct (empty when `None`).
- `id`: supplied by the caller (the step id) — `Contract` needs one and a
  packet carries none on purpose.
- `redacts`, `role`, budgets: do not cross. `redacts` especially must
  not — the same boundary that keeps it off the worker projection today.

Emitted as real YAML (`pyyaml.safe_dump`), not hand-assembled text:
`task`'s content is arbitrary free text (facts, prose) that can contain
colons, quotes, newlines — anything a hand-rolled emitter would get wrong
silently. **This adds `pyyaml` as a direct dependency**
(`pyproject.toml` currently declares none at all; `pyyaml` is already
resolvable transitively per `uv.lock`, so this formalizes an existing
availability rather than introducing a new supply-chain surface).

### B — `pi_implementer.py`: split edit target from bookkeeping location

Replace the single derived `workspace = result_path.parent` with two
names:

- `edit_dir = Path.cwd()` — where the Pi child's `cwd` is set, and what
  `attribution.snapshot`'s before/after pair observes. For HP2's existing
  `command_implementer` seam, this is **unchanged behavior**:
  `command_implementer` already sets `cwd=workspace` when it spawns this
  adapter, so `Path.cwd()` inside it resolves to the exact same directory
  `result_path.parent` always did. No HP2 test should need to change.
- `harness_dir = result_path.parent` — unchanged in name and role:
  `TRANSCRIPT_NAME`/`STDERR_NAME`/`COUNTER_NAME`/the packet/result files
  all stay here. For the new engine seam, the caller sets `PACKET_ENV`/
  `RESULT_ENV` to a scratch directory **outside** the isolated worktree,
  while the worktree itself (via `deliver`'s own `cwd` for the COMMAND it
  runs) becomes `edit_dir` through inherited `Path.cwd()` — no new env var
  needed.

Acceptance: every existing HP2 test passes unchanged (proving the split
is behavior-preserving there); a new test proves `edit_dir` and
`harness_dir` can differ — spawn the adapter with a `cwd` distinct from
`RESULT_ENV`'s parent, confirm Pi's mutations land in `cwd` and harness
files land in the other directory, confirmed by real subprocess, not
mocked (matching this repository's own standard).

### C — candidate content, sourced from git for this seam only

`chain_record.run_and_record_chain`'s `capture_candidate` gains a second,
injected way to answer "what did this phase change, and what does the
changed content say" — matching this repository's existing pattern
(implementer, grader, observer are already injected callables; "a test
seam is the extension seam"). The default stays exactly what it is today
(snapshot-diff a shared workspace) for HP2's route. The engine-composed
caller supplies one sourced from `deliver`'s own receipt:
`changed_paths` for the mutation list, `git show <candidate_commit>:<path>`
against the **repo** (which persists across phases, unlike the destroyed
worktrees) for content — no snapshot, no diffing, because `deliver`
already answered the question.

The exact injection shape (a new parameter on `run_and_record_chain`
itself, or a small wrapping function around it) is a plan-level decision,
not frozen here; the constraint is that HP2's default path takes no new
parameter it does not already need and no behavior change.

### D — `engine_command_implementer`, and the repo a chain needs

A new `Implementer` factory, parallel to `command_implementer`:

- Takes the task's repo path (now a **real git checkout**, not a plain
  directory — the task's `base/` fixture materialized and committed once,
  the same "materialize before inference" step HP7's own precondition 3
  already requires, with one added step: `git init` and one commit).
- Closure state: the running `base` commit-ish, `None` for phase 1
  (`deliver`'s own HEAD-default), then each phase's `receipt["candidate_commit"]`
  for the next.
- Per phase: render the packet to a `Contract` (piece A), write it to a
  scratch YAML file, invoke
  `satyrn-engine deliver --repo REPO --base <current-or-omitted> --timeout T
  CONTRACT.yaml -- <pi_implementer argv, with PACKET_ENV/RESULT_ENV
  pointing at the scratch harness_dir>` as a subprocess, parse the JSON
  receipt from stdout.
- Translate the receipt to `ImplementerResult`: `code == "OK"` with
  `changed_paths` non-empty → `delivered`; `code == "NO_CHANGES"` →
  `refused`; anything else → let the non-zero/refusal propagate the way
  `command_implementer`'s own `check=True` subprocess failure already does
  today, so HP6's existing crash handling in `run_phases` needs no new
  branch.
- Marked as the executable seam the same way `command_implementer` is
  (`is_executable_seam`), so `declaration_ledger`'s existing `redacts`/
  `self_test_command` logic applies unchanged — this seam does not
  reinvent that ledger, only supplies a different way to run a phase.

## Acceptance, across all four pieces together

1. A real two-phase chain, driven through `engine_command_implementer`
   against a real git repo, real `satyrn-engine deliver` subprocess calls
   (no in-process shortcuts): phase 2's worktree contains phase 1's
   committed file, proven the same way `satyrn-engine`'s own HP3
   acceptance proved it — read the resulting tree via `git ls-tree`, not
   inferred from a green exit code.
2. A refused phase stops the chain, `candidate_ref` absent from the
   `ChainRecord`'s effect, matching HP6's existing no-partial-chain rule —
   proven through this seam specifically, not assumed inherited from HP2.
3. `implementer_mutations` for an engine-composed phase come from
   `deliver`'s receipt, never from a directory snapshot; `orchestrator_mutations`
   is `()` for every phase on this seam, never `None` — there is no window
   in which it could be unobserved, and the retained record says so
   structurally, not by omission.
4. `PhaseRecord.candidate_snapshot_path`/`_digest` for an engine-composed
   phase are populated from `git show`-retrieved content, and
   `test_offline_regrading_from_only_the_retained_candidate_snapshots`'s
   own proof (re-grade from retained bytes alone) holds for this seam too.
5. Every existing HP2 test (`command_implementer`, `pi_implementer.py`'s
   own suite, `chain_record`'s default-tier and integration tests) passes
   unmodified in behavior — piece B and C's changes are additive, proven
   by running the full existing suite, not by inspection alone.
6. `just gates` clean; the new engine-seam integration tests are real
   subprocess calls to a real `satyrn-engine deliver`, not mocked.

## Out of scope

- **Any change to `satyrn-engine`.** HP3 is accepted there as-is; this
  spec composes with it, not into it.
- **A live `pi` process anywhere in this work.** Every acceptance item
  above uses `scripted_implementer`/`fake_implementer.py`-shaped fixtures
  or `pi_implementer.py` driven by a fake `pi` binary, the same pattern
  `tests/integration/test_hp2_route.py` already uses for HP2.
- **Applying `turn_budget`/`tool_call_budget`.** Still declared, still
  unapplied, unchanged by this work — a pre-existing, disclosed gap.
- **`run_self_test` on the composed seam.** The tool already threads
  through whatever `pi_implementer.py`'s argv is; nothing here changes
  that wiring. Its own live verification stays separately proposed.
- **HP8's workflow comparison, or any TE2+ confirmation.** This closes
  TE1's composition blocker; it does not run one.
