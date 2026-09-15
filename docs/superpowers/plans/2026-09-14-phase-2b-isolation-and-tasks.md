# Phase 2b — Isolation and tasks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status: draft for approval, 2026-09-14.** Planned against evals `release-one` `d22387b` (Phase 2a done) and engine `release-one` `341d4c4`. Every test below was run before hand-back (see "Test verification").

**Goal:** Roadmap row 2b: the eval runs both arms against a fake model under two-uid isolation with the budget tripwire; every ceiling and floor candidate passes offline qualification; the tooling that measures k and the context-speed curve exists and is tested against recorded log lines; settings provenance is verified against the cell user's Pi config.

**Architecture:** A new `cell` module owns the second uid: the workspace is allocated under `/Users/Shared/satyrn-cells`, shared with the cell group and kept readable by the maintainer through an inherited ACL; adapters run only their model-side children (Pi; the engine's `derive` and `deliver`) through `sudo -n -H -u satyrn-cell` with an `env -i` environment; the harness tears a stopped cell down from the cell side too. Run records gain a required launcher profile and purpose, and `attempt`/`run` refuse a record whose task, tree, arm or model is not the invocation's. A deterministic generator cuts self-hosted tasks from spec files, AgentClinic tasks are imported from the ceiling probe, and `satyrn-evals qualify` proves every candidate offline. The probe tooling reads k and decode rates from oMLX's own log.

**Tech Stack:** Python 3.14, uv, pytest (default tier: audit-hook spawn tripwire; `integration` marker), ruff, just; git 2.45.1 (Homebrew); sudo 1.9.17p2; macOS ACLs (`chmod +a`); `satyrn-engine` CLI (engine `341d4c4`) for the Engine rows.

**Spec:** `docs/superpowers/specs/2026-09-13-release-one-design.md` — "The model" (settings verified; context-speed and concurrency probe), "The eval" (isolation, budget, concurrency, workloads, the self-hosted generator, rungs, conditions, campaign record), "Harness work" items 2 and 6, "Process" (six tasks, plan tests verified up front), roadmap row 2b. House style and predecessor: `docs/superpowers/plans/2026-09-14-phase-2a-eval-core.md` (Ruling 9 lists what moved here) and its ledger `.superpowers/sdd/2026-09-14-phase-2a-eval-core/progress.md`. Evidence: the workload deep dive (`.../scratchpad/workload-deep-dive/rationale.md`, Q2, Q3, Q6) and the isolation spike (`.../scratchpad/isolation-spike/`).

## Rulings

Conflicts between the spec, the evidence and the code as of evals `d22387b`, each with the ruling, why, and the cost if wrong. Rulings 1–3 were taken with the maintainer before this plan was written; the rest are this plan's, several forced by its own test verification.

1. **Launcher profiles** (taken). `isolated` is two-uid and is required for admission, route-proof and campaign records; the gate refuses those records under any other profile. `local` is the maintainer's own uid, for Engine users and harness contributors, allowed only for records that declare it (`purpose: development`). Contributors never need a second user: every row that needs it skips with the reason. Cost if wrong: none identified; a record says which it is.
2. **No Docker, no container, no `sandbox-exec`, ever; no wrapper process around a per-command bound** (taken). `sudo`, `env -i` and `sh -c 'cd … && exec'` are a user switch that `exec`s away, not a bound; Pi still owns its bash timeout and the engine still only sets or clamps it. Cost if wrong: none; the spec forbids the alternatives.
3. **Preflight reads the cell user's Pi config** (taken). `scripts/preflight_settings.py --cell` reads `/Users/satyrn-cell/.pi/agent/models.json` through `sudo -n -H -u satyrn-cell cat` and records that file as its Pi source; the maintainer cannot open that home. Cost if wrong: none; the maintainer's file is not what the cell's Pi loads.
4. **Only the model side runs as the cell.** The harness, the adapter process, the harvest and the grader stay the maintainer's (the task directory holds the hidden suite and known-good). The Baseline adapter wraps `pi`; the Engine adapter wraps `derive` and `deliver` (whose `attempt` then spawns Pi as the cell). Pi's stream still reaches the transcript through the inherited stdout. Cost if wrong: none identified; the deep dive's Q3 corrected a one-uid proposal on exactly this.
5. **Who can touch what.** The workspace parent is allocated under `/Users/Shared/satyrn-cells` (`pauleveritt:satyrn` 2770). The cell writes into maintainer-made entries through the group (directories 2770, files g+rw, `core.sharedRepository=group`, cell commands under `umask 007`). The maintainer reads and removes what the cell makes through an ACL entry on the parent inherited by every file and directory below it. Group bits alone are not enough (found by this plan's verification): the engine creates its transcript `0600` with `O_EXCL`, and any tool may make a `0700` directory, which would make every Engine cell unreadable and every cleanup `CLEANUP_FAILED`. Cost if wrong: an ACL-less filesystem refuses the workspace loudly (`cannot keep the maintainer's access`); this Mac's APFS accepts it (verified).
6. **Git's dubious-ownership refusal** (the spike's open question, run as a test). A cell `git status` in the maintainer-made worktree fails with exit 128 "detected dubious ownership" (verified). Each cell gets its own global git config, `GIT_CONFIG_GLOBAL=<parent>/gitconfig`, naming its one worktree as `safe.directory` and a commit identity (`satyrn-cell`). Not `GIT_CONFIG_COUNT`: git lists it among the repository-local variables that `satyrn-engine deliver` strips before it runs git (`git rev-parse --local-env-vars`; `delivery.py` `_sanitized_environment`). Not `safe.directory=*` in the cell's `~/.gitconfig`: narrower is available. Cost if wrong: the model sees `GIT_CONFIG_GLOBAL` and a `satyrn-cell` identity where local Pi saw the maintainer's; both arms alike.
7. **Teardown from the cell side.** sudo runs the command in the caller's process group and relays SIGTERM, but the maintainer's `killpg` silently skips cell-owned members and SIGKILL never reaches them (verified: a cell `sleep` survived both). After the SIGTERM half of the grace, an isolated teardown also runs `sudo -n -u satyrn-cell /bin/kill -KILL -- -PGID` (18 ms per call measured). A process a stopped Pi started in its own session (Pi's bash tool detaches) is not in that group — exactly as under the local profile, where `killpg` misses it too. `launch --preflight` refuses while any non-system cell process runs. Never `pkill -U satyrn-cell`: the OS runs agents (`lsd`, `cfprefsd`, …) as that user. Cost if wrong: a stopped cell's detached `find /` keeps a CPU busy until the next preflight names it; Pi itself, the GPU consumer, is in the group.
8. **The cell environment is an allowlist.** `env -i` with `HOME`, `USER`, `LOGNAME`, `SHELL`, `PATH` (the cell's `~/.local/bin`, `~/.npm-global/bin`, Homebrew, system), a per-cell `TMPDIR`, `UV_PROJECT_ENVIRONMENT` and `GIT_CONFIG_GLOBAL` beside the worktree, `PYTHONDONTWRITEBYTECODE=1`. Nothing of the maintainer's environment and none of sudo's `SUDO_*` variables reach the model. `SATYRN_CELL_PATH_PREFIX` prepends directories to the cell's PATH for the fake `pi`; `launch --preflight` refuses while it is set. Cost if wrong: a tool the model needs outside that PATH is missing under isolation for both arms; Phase 3 reads it in the first cells.
9. **Transcripts and engine artifacts under isolation.** The command's transcript is written to `<parent>/transcript.txt`, where the cell can write it, and copied into the attempt directory as soon as the command returns (the harness tails the live file for the budget and timeline). The Engine adapter writes its logs and receipt beside `patch.diff`, not beside the transcript (found by verification: they were landing in the parent and deleted with it). Cost if wrong: the model can read its own transcript, and under the Engine arm the cell owns it; a model rewriting its own stream is not an observed behaviour.
10. **The engine the cell runs is an export.** `satyrn-evals cell-engine --engine-repo R --commit SHA` writes `git archive SHA` to `/Users/Shared/satyrn-cells/engine-<sha>`, syncs it offline from the maintainer's uv cache against Homebrew's Python 3.14 (uv's managed Pythons live under his 700 home: the first export's venv could not start as the cell, verified) and shares it. The Engine adapter refuses an isolated engine outside the cells root and runs the engine with `uv run --no-sync` (found by verification: a plain `uv run` as the cell rebuilt the shared export's package). The export holds no evals task material (`git grep` at `341d4c4`). Cost if wrong: a stale export after an engine change; the export is keyed by the full commit.
11. **The run record carries its profile and purpose; the invocation must be the record's.** `isolation` (`isolated|local`) and `purpose` (`admission|route-proof|campaign|development`) are required, no default, like the budgets. `attempt`/`run --run-record` now refuse a task other than the record's, a task tree whose `tree_digest` differs from `task_tree_sha256`, an adapter other than the record's arm, and a `--model` other than the record's (Phase 2a ledger, "before Phase 3"), and take the profile from the record. The digest covers every file of the task directory, the manifest included, residue excluded. Cost if wrong: nine existing record rows change shape (listed in Task 3); a record without the new fields refuses to load, loudly.
12. **The generator's shape.** A task spec (`tools/task_specs/<name>.json`) names BASE, GOOD, files, HIDDEN, a plan anchor, the formats text and the known-broken stubs. The overlay is flattened to each hidden file's basename and the expected ids are the hidden suite collected at GOOD — the headroom probe's layout, reproduced byte for byte (verified: the generator's `base/`, `overlay/` and expected ids for `guard-prefixes`, `docs-linter` and `run-record-gate` equal the probe's at `635c12b`; `known-good.patch` differs only in full-length index lines). HIDDEN paths and basenames become "its test module" in the prompt, because a contract naming a grader-only path is refused at load. The formats text for `docs-linter` and `run-record-gate` is the probe's disclosed paragraph. Cost if wrong: R1-plan is richer than the probe's hand-written R1; the two are never compared (spec, "Rungs").
13. **Two anchors the spec's table does not settle.** `selfhost-review-script` is BASE `b253c99` → GOOD `fdd2161`, the commit that is Phase 0 plan Task 9 exactly; `52a3449` adds refusals the plan task never states. `selfhost-guard-prefixes` came from a review's fix wave, not a plan task, so its anchor is a committed plan-shaped file (`tools/task_specs/selfhost-guard-prefixes.plan.md`) whose prose is the probe's R1 text for the same fix. Cost if wrong: one prompt was written by hand once (at the probe) rather than derived from a plan.
14. **AgentClinic candidates are imported, not regenerated.** `agentclinic-repair-depth-3` and `-depth-2` are copied byte-identical from `worktree-ornith-ceiling-probe` `4f0ee53` with `PROVENANCE.md` rows naming that commit; their manifests already carry `R1`. Cost if wrong: none; the probe measured these trees.
15. **Qualification is a command, and its results are the morning status.** `satyrn-evals qualify TASK…` grades known-good three times (the three-run flake check), known-broken once, and runs one live-harvest attempt through the real Baseline adapter with a fake `pi` that applies known-good, commits part and leaves the rest uncommitted; collection errors fail every fixture check. It runs under the local profile: qualification proves the task and the harvest, and isolation is proven by Task 2's rows. Nothing is committed as a result file (docs caps). Cost if wrong: none identified; all six qualify in 38 s (verified).
16. **The probe reads oMLX's own log.** The format was read from `~/.omlx/logs/server.log` without inference (one `Chat completion:` line per request, written at its end; its `tok/s` is decode-only), so no attended step is spent confirming it. k is the largest of 1, 2, 3 whose total throughput is at least 1.5 × k = 1's, read literally: k = 3 qualifies on its own ratio even when k = 2 does not. Cost if wrong: a future oMLX changes the line; `analyze` then finds no completions and exits 2.
17. **The timeline clock is monotonic** (Phase 2a ledger, "before Phase 3"). Spans are differences within one harness process; a wall-clock step no longer makes a command negative or hours long. Cost if wrong: none; nothing compares timeline stamps across processes.
18. **The cell's Pi settings match the maintainer's where they change behaviour** (found by this plan's verification). The cell's `~/.pi/agent/` holds only `models.json`; the maintainer's `settings.json` also sets `compaction` (`enabled: true`, `reserveTokens: 16384`, what the arm declares) and `defaultThinkingLevel: "high"`, and `scripts/preflight_inference.py` cannot even run against the cell's directory (`settings.json` missing). The attended checklist writes exactly those two keys into the cell's `settings.json` — nothing else of the maintainer's (no packages, skills or default provider) — and verifies compaction with `preflight_inference.py` on a copy. Cost if wrong: without it the isolated Baseline would think at Pi's default level, unlike every earlier Ornith cell; admission would read a different model behaviour.
19. **What moves out of 2b.** To **2c**, which lands before Phase 3's first sitting: the launcher's cell loop (`launch RECORD` running n cells at k with arms interleaved; 2b's launcher checks and preflights only), and warm-prefix recording and byte-identical replay (a declared secondary outside the win rule, used only in Phase 4). To **the campaign freeze**: the committed Engine arm file and `arms.ENGINE_SOURCES` gaining `scope.ts` and `bounds.ts` (the engine commit is not frozen until Phase 3's route proof). Unchanged from 2a Ruling 9: the tally that counts a contaminated pass as a fail and per-turn seconds (result time). Every other deferred minor in the 2a ledger stays deferred. In 2b from that ledger: the monotonic clock (Ruling 17), the failed candidate checkout (Task 2), the run-record cross-check (Ruling 11).

## Global Constraints

- **Roles: Sonnet implements, Opus reviews each task, Sonnet re-reviews a fix diff (scoped). No haiku. No Fable.** One fresh implementer per task; one Opus review per task before the next starts.
- **The controller blocks on every dispatch; nothing runs in the background.**
- **No inference anywhere.** Fake `pi`, fixture repositories, recorded log lines, a fake HTTP opener. No launcher cells, no `pi -p`, no request to oMLX, no `scripts/speed_probe.py run`.
- **Default test tier: no subprocess, no network, no model** (the audit hook in `tests/conftest.py`). Anything that spawns is `@pytest.mark.integration`. Every integration row that needs `satyrn-cell` takes the `cell_scratch` fixture, which skips with the reason when `sudo -n -u satyrn-cell true` fails.
- **Every refusal test has a sibling success test**; every detector has a firing row and a silent row.
- **Every task ends with `just gates` exit 0** (read the exit code; never pipe a gate). New files get `PROVENANCE.md` rows (`uv run python tools/provenance.py new <paths>`; imports with `record --sha`); edited files keep theirs. Run `uv run ruff check --fix` before gates.
- **Integration runs name their files.** After any task that touches `workspace.py`, `attempt.py` or an adapter, these still pass: `tests/integration/test_engine_arm.py`, `test_harvest_qualification.py`, `test_budget_attempt.py`, `test_timeline_attempt.py`, `test_evidence_run.py`, `test_workspace.py`, and `test_attempt.py::test_real_e5_*`. Engine rows need `SATYRN_V4_ENGINE_REPO=/Users/pauleveritt/projects/pauleveritt/satyrn-engine` set explicitly.
- **Four integration rows fail on this Mac before any change**: `tests/test_workspace_failures.py::test_prepare_repository_fails_closed_on_verification[*]` reach `/usr/bin/git`, which refuses until the Xcode license is accepted. They are reported, never "fixed" here, and never counted against a task.
- **Commit at the end of every task** on evals `release-one`, with the plan's message. Never `--amend`, merge or push. A task whose gates are red is not committed.
- **Evals tree only.** The engine is read, never edited.
- **The cell user is the maintainer's.** Never create or change users, groups or `/etc/sudoers.d`; the only sudo forms are `sudo -n -u satyrn-cell` and `sudo -n -H -u satyrn-cell`. Never `pkill -U satyrn-cell`. Under `/Users/Shared/satyrn-cells` create only what tests and attempts create and remove; never touch `spike/` or an `engine-*` export the maintainer made.
- **Nothing is written to `/tmp` or `/private/tmp`** except under the session scratchpad `$SCR` (`/private/tmp/claude-501/-Users-pauleveritt-projects-pauleveritt-satyrn-evals/553f3cc9-dfd8-475d-89e0-2859bed390d7/scratchpad/phase2b-exec/`). Tests use pytest's `tmp_path`; a `--basetemp` is under `$SCR` and removed right after the run.
- **No test copies a bundled hidden task into pytest's temp directory** (Phase 2a Task 6): the self-hosted bases carry other tasks' overlays. Refusal rows use `calc-build` or a synthetic repository.
- **Starting point:** evals `release-one` at `d22387b` plus this plan's commit; engine `341d4c4`. Docs caps stand: `ROADMAP.md` ≤ 150 lines; `just lint-docs` exit 0. Old worktrees under `.claude/worktrees/` are never checked out, edited or removed.

---

## File structure

```
src/satyrn_evals/cell.py              # the second uid: profile, cell command and environment, kill, ACL, sharing   (new, T1)
src/satyrn_evals/workspace.py         # isolated allocation under the cells root, sharing, cell-side teardown          (modify, T1)
src/satyrn_evals/attempt.py           # attempt(isolation=); live transcript beside the worktree, copied back          (modify, T1)
src/satyrn_evals/attempt_pi.py        # pi_command: pi as the cell under isolation                                       (modify, T2)
src/satyrn_evals/attempt_engine.py    # derive/deliver as the cell; --no-sync; logs beside patch.diff; checkout failure (modify, T2)
src/satyrn_evals/cell_engine.py       # export_engine: one engine commit the cell can run                                (new, T2)
src/satyrn_evals/cli.py               # cell-engine (T2); record settings, launch --preflight (T3); qualify (T5)         (modify, T2 T3 T5)
src/satyrn_evals/task_tree.py         # tree_digest                                                                      (new, T3)
src/satyrn_evals/run_record.py        # isolation, purpose; DECIDING_PURPOSES gate; check_invocation                     (modify, T3)
src/satyrn_evals/run.py               # run(isolation=)                                                                  (modify, T3)
src/satyrn_evals/cell_preflight.py    # stale cell processes, unreadable trees, pinned pi, the hunt                      (new, T3)
src/satyrn_evals/timeline.py          # monotonic clock                                                                   (modify, T3)
scripts/preflight_settings.py         # --cell                                                                            (modify, T3)
tools/cut_task.py                     # the generator                                                                     (new, T4)
tools/task_specs/*.json, *.plan.md    # four self-hosted task specs, one plan-shaped anchor                              (new, T4)
src/satyrn_evals/tasks/selfhost-*/    # four cut tasks                                                                     (new, T4)
src/satyrn_evals/tasks/agentclinic-repair-depth-{2,3}/ # imported from 4f0ee53                                           (new, T5)
src/satyrn_evals/qualify.py, qualify_fake_pi.py        # offline qualification                                          (new, T5)
scripts/speed_probe.py                # the context-speed and concurrency probe                                          (new, T6)
tests/...                             # per task; tests/integration/conftest.py and cell_support.py (T1)
ROADMAP.md                            # rows 2b and 2c                                                                     (modify, T6)
```

---

### Task 1: Two-uid isolation at the workspace boundary

**Files:**
- Create: `src/satyrn_evals/cell.py`, `tests/test_cell.py`, `tests/integration/conftest.py`, `tests/integration/cell_support.py`, `tests/integration/test_cell_isolation.py`
- Modify: `src/satyrn_evals/workspace.py` (imports; `_WorkspaceState`; `_safe_temp_parent`; `_teardown_process`; new `_teardown`, `_share_workspace`; `_run_command`'s three teardown calls; `prepare_workspace`), `src/satyrn_evals/attempt.py` (imports; `LIVE_TRANSCRIPT_NAME`; `_collect_live_transcript`; `attempt`/`_attempt` `isolation=`; the `run_prepared_command` call)

**Interfaces:**
- Produces: `cell.CELL_USER = "satyrn-cell"`, `CELL_HOME`, `CELLS_ROOT = Path("/Users/Shared/satyrn-cells")`, `ISOLATION_ENV = "SATYRN_ISOLATION"`, `CELL_PARENT_ENV = "SATYRN_CELL_PARENT"`, `CELL_PATH_PREFIX_ENV = "SATYRN_CELL_PATH_PREFIX"`, `CELL_PATH`; `class Isolation(StrEnum)`: `ISOLATED`, `LOCAL`; `isolation_from(environment) -> Isolation` (ValueError on an unknown value); `cell_paths(parent) -> (tmpdir, uv_environment, gitconfig)`; `cell_gitconfig(worktree) -> str`; `cell_environment(*, parent, extra=None, path_prefix=()) -> dict[str, str]`; `model_environment(environment, extra=None) -> dict[str, str]` (ValueError without `SATYRN_CELL_PARENT`); `path_prefix_from(environment) -> tuple[str, ...]`; `cell_command(argv, *, cwd, environment) -> list[str]`; `cell_kill_command(process_group) -> list[str]`; `kill_cell_group(process_group, *, timeout, run=subprocess.run) -> str | None`; `cell_unavailable_reason(run=subprocess.run) -> str | None`; `maintainer_ace() -> str`; `grant_maintainer(directory, run=subprocess.run) -> str | None`; `share_with_cell(root) -> None`. `workspace.prepare_workspace(..., isolation: Isolation = Isolation.LOCAL)`; `workspace._teardown_process(process, grace, *, cell=False)`. `attempt.attempt(..., isolation: Isolation = Isolation.LOCAL)`, `attempt.LIVE_TRANSCRIPT_NAME = "transcript.txt"`, `attempt._collect_live_transcript(live, transcript_path)`. Under isolation the command's environment additionally holds `SATYRN_ISOLATION=isolated`, `SATYRN_CELL_PARENT=<parent>` and `SATYRN_ATTEMPT_TRANSCRIPT=<parent>/transcript.txt`; under local it is unchanged. Integration fixture `cell_scratch` (skips without the cell user); helpers `cell_support.cell_process_alive(pid) -> bool`, `cell_support.run_as_cell(argv, *, cwd, environment)`.

- [ ] **Step 1: Failing tests.** `tests/test_cell.py`:

```python
"""The cell module's pure pieces: command shape, environment, profile, kill."""

import os
import stat
import subprocess
from pathlib import Path

import pytest

from satyrn_evals.attempt import LIVE_TRANSCRIPT_NAME, _collect_live_transcript
from satyrn_evals.cell import (
    CELL_PARENT_ENV,
    CELL_PATH_PREFIX_ENV,
    CELL_USER,
    ISOLATION_ENV,
    Isolation,
    cell_command,
    cell_environment,
    cell_gitconfig,
    cell_kill_command,
    cell_unavailable_reason,
    isolation_from,
    kill_cell_group,
    maintainer_ace,
    model_environment,
    share_with_cell,
)


def _completed(code: int, stderr: bytes = b"") -> subprocess.CompletedProcess[bytes]:
    return subprocess.CompletedProcess([], code, b"", stderr)


def test_a_cell_command_switches_user_clears_the_environment_and_changes_directory() -> None:
    argv = cell_command(["pi", "--version"], cwd=Path("/w"), environment={"PATH": "/bin", "HOME": "/h"})
    assert argv[:6] == ["sudo", "-n", "-H", "-u", CELL_USER, "--"]
    assert argv[6:10] == ["/usr/bin/env", "-i", "HOME=/h", "PATH=/bin"]
    assert argv[10:13] == ["/bin/sh", "-c", 'umask 007 && cd "$1" && shift && exec "$@"']
    assert argv[13:] == ["satyrn-cell", "/w", "pi", "--version"]


def test_an_empty_cell_command_is_refused() -> None:
    with pytest.raises(ValueError, match="empty"):
        cell_command([], cwd=Path("/w"), environment={})


def test_the_cell_environment_is_the_cells_own_and_names_its_git_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRET_OF_THE_MAINTAINER", "x")
    environment = cell_environment(parent=Path("/cells/a"), extra={"K": "v"}, path_prefix=("/fake/bin",))
    assert environment["HOME"] == "/Users/satyrn-cell"
    assert environment["TMPDIR"] == "/cells/a/tmp"
    assert environment["UV_PROJECT_ENVIRONMENT"] == "/cells/a/environment"
    assert environment["GIT_CONFIG_GLOBAL"] == "/cells/a/gitconfig"
    assert environment["PATH"].split(os.pathsep)[0] == "/fake/bin"
    assert environment["K"] == "v"
    assert "SECRET_OF_THE_MAINTAINER" not in environment


def test_the_cell_git_config_names_one_safe_directory_and_an_identity() -> None:
    text = cell_gitconfig(Path("/cells/a/worktree"))
    assert "[safe]\n\tdirectory = /cells/a/worktree\n" in text
    assert f"name = {CELL_USER}" in text


def test_the_model_environment_comes_from_what_the_harness_exported() -> None:
    exported = {CELL_PARENT_ENV: "/cells/a", CELL_PATH_PREFIX_ENV: f"/p1{os.pathsep}/p2"}
    environment = model_environment(exported)
    assert environment["TMPDIR"] == "/cells/a/tmp"
    assert environment["PATH"].startswith(f"/p1{os.pathsep}/p2{os.pathsep}")


def test_the_model_environment_refuses_without_a_workspace_parent() -> None:
    with pytest.raises(ValueError, match=CELL_PARENT_ENV):
        model_environment({})


def test_the_profile_defaults_to_local_and_refuses_an_unknown_one() -> None:
    assert isolation_from({}) is Isolation.LOCAL
    assert isolation_from({ISOLATION_ENV: "isolated"}) is Isolation.ISOLATED
    with pytest.raises(ValueError, match="isolated or local"):
        isolation_from({ISOLATION_ENV: "docker"})


def test_the_cell_kill_targets_a_group_and_never_init() -> None:
    assert cell_kill_command(4242)[-3:] == ["-KILL", "--", "-4242"]
    with pytest.raises(ValueError, match="refusing"):
        cell_kill_command(1)


@pytest.mark.parametrize("code", [0, 1])
def test_a_cell_kill_that_ran_or_found_the_group_empty_succeeds(code: int) -> None:
    assert kill_cell_group(4242, timeout=1, run=lambda *a, **k: _completed(code)) is None


def test_a_cell_kill_that_sudo_refused_is_described() -> None:
    failure = kill_cell_group(4242, timeout=1, run=lambda *a, **k: _completed(2, b"a password is required"))
    assert failure is not None and "password" in failure


def test_the_cell_is_unavailable_when_sudo_refuses(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("satyrn_evals.cell.CELLS_ROOT", tmp_path)
    assert "exited 1" in (cell_unavailable_reason(run=lambda *a, **k: _completed(1)) or "")
    assert cell_unavailable_reason(run=lambda *a, **k: _completed(0)) is None


def test_the_cell_is_unavailable_without_the_cells_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("satyrn_evals.cell.CELLS_ROOT", tmp_path / "absent")
    assert "does not exist" in (cell_unavailable_reason(run=lambda *a, **k: _completed(0)) or "")


def test_the_maintainer_ace_is_inherited_by_files_and_directories() -> None:
    ace = maintainer_ace()
    assert ace.startswith("user:") and "file_inherit" in ace and "directory_inherit" in ace and "delete_child" in ace


def test_sharing_widens_group_bits_on_the_maintainers_entries(tmp_path: Path) -> None:
    (tmp_path / "d").mkdir(mode=0o700)
    (tmp_path / "d" / "f").write_text("x")
    (tmp_path / "d" / "f").chmod(0o600)
    share_with_cell(tmp_path)
    assert stat.S_IMODE((tmp_path / "d").stat().st_mode) == 0o2770
    assert stat.S_IMODE((tmp_path / "d" / "f").stat().st_mode) == 0o660


def test_a_live_transcript_is_copied_into_the_attempt_directory(tmp_path: Path) -> None:
    live = tmp_path / "parent" / LIVE_TRANSCRIPT_NAME
    live.parent.mkdir()
    live.write_text('{"type": "agent_start"}\n')
    destination = tmp_path / "attempt" / "transcript.txt"
    destination.parent.mkdir()
    _collect_live_transcript(live, destination)
    assert destination.read_text() == live.read_text()


def test_a_local_transcript_or_a_missing_live_one_is_left_alone(tmp_path: Path) -> None:
    destination = tmp_path / "transcript.txt"
    _collect_live_transcript(destination, destination)
    _collect_live_transcript(tmp_path / "absent.txt", destination)
    assert not destination.exists()
```

`tests/integration/conftest.py`:

```python
"""Integration-tier fixtures.

``cell_scratch``: every row that runs a command as ``satyrn-cell`` asks for
it. It skips with the reason when ``sudo -n -u satyrn-cell true`` fails or
the cells root is absent, so contributors without the second user still get
a green integration tier. The directory lives under the cells root (the
cell cannot read pytest's temp directory) and is removed afterwards.
"""

import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from satyrn_evals.cell import (
    CELLS_ROOT,
    cell_unavailable_reason,
    grant_maintainer,
    share_with_cell,
)


@pytest.fixture
def cell_scratch() -> Iterator[Path]:
    if (reason := cell_unavailable_reason()) is not None:
        pytest.skip(f"the cell user is not set up: {reason}")
    root = Path(tempfile.mkdtemp(prefix="satyrn-test-", dir=CELLS_ROOT))
    assert grant_maintainer(root) is None
    share_with_cell(root)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)
```

`tests/integration/cell_support.py`:

```python
"""Helpers for integration rows that run commands as the cell user (fixture: ``conftest.cell_scratch``)."""

import os
import subprocess
from pathlib import Path

from satyrn_evals.cell import cell_command


def cell_process_alive(pid: int) -> bool:
    """Whether ``pid`` still exists; the maintainer may not signal it, so EPERM means alive."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def run_as_cell(argv: list[str], *, cwd: Path, environment: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cell_command(argv, cwd=cwd, environment=environment), cwd=cwd, capture_output=True, text=True, check=False
    )
```

`tests/integration/test_cell_isolation.py` (the dubious-ownership row the spike left open is `test_the_cell_cannot_use_the_maintainers_worktree_without_its_git_config`; its sibling is the commit-and-harvest row):

```python
"""Two-uid isolation at the workspace boundary: real sudo, real git, no model.

Skips when the cell user is not set up (``cell_support.cell_scratch``).
"""

import os
import stat
import subprocess
import time
from pathlib import Path

import pytest

from integration.cell_support import cell_process_alive, run_as_cell
from satyrn_evals.attempt_pi import harvest_patch
from satyrn_evals.cell import (
    CELLS_ROOT,
    Isolation,
    cell_command,
    cell_environment,
    cell_paths,
    kill_cell_group,
)
from satyrn_evals.patch import parse_patch_paths
from satyrn_evals.workspace import (
    WorkspaceCode,
    _teardown_process,
    prepare_workspace,
    release_workspace,
    run_prepared_command,
)

pytestmark = pytest.mark.integration

CALC = Path(__file__).parent / "data" / "tasks" / "calc-build"
WRITE_AND_COMMIT = (
    "mkdir -p calc && printf 'def add_all(xs):\\n    return sum(xs)\\n' > calc/helpers.py"
    " && printf 'def render(n):\\n    return f\"{n:,}\"\\n' > calc/format.py"
    " && git add calc/helpers.py && git commit -qm model"
)


def _isolated(tmp_path: Path):
    return prepare_workspace(
        base=CALC / "base", protected_paths=(CALC, tmp_path), environment=dict(os.environ), isolation=Isolation.ISOLATED
    )


def test_an_isolated_workspace_is_shared_with_the_cell_group_under_the_cells_root(
    tmp_path: Path, cell_scratch: Path
) -> None:
    lease = _isolated(tmp_path)
    try:
        assert lease.parent.parent == CELLS_ROOT.resolve()
        tmpdir, uv_environment, gitconfig = cell_paths(lease.parent)
        for directory in (lease.parent, lease.worktree, tmpdir, uv_environment, lease.repository / ".git" / "objects"):
            assert stat.S_IMODE(directory.stat().st_mode) == 0o2770, directory
        assert f"directory = {lease.worktree}" in gitconfig.read_text()
    finally:
        assert release_workspace(lease) is None
    assert not lease.parent.exists()


def test_the_cell_cannot_use_the_maintainers_worktree_without_its_git_config(
    tmp_path: Path, cell_scratch: Path
) -> None:
    lease = _isolated(tmp_path)
    try:
        bare = {"HOME": "/Users/satyrn-cell", "PATH": "/opt/homebrew/bin:/usr/bin:/bin"}
        refused = run_as_cell(["git", "status", "--short"], cwd=lease.worktree, environment=bare)
        assert refused.returncode == 128 and "dubious ownership" in refused.stderr
    finally:
        assert release_workspace(lease) is None


def test_the_cell_commits_in_its_worktree_and_the_maintainer_harvests_every_change(
    tmp_path: Path, cell_scratch: Path
) -> None:
    lease = _isolated(tmp_path)
    try:
        wrote = run_as_cell(["/bin/sh", "-c", WRITE_AND_COMMIT], cwd=lease.worktree, environment=cell_environment(parent=lease.parent))
        assert wrote.returncode == 0, wrote.stderr
        assert (lease.worktree / "calc" / "format.py").stat().st_uid != os.getuid()
        patch = harvest_patch(lease.worktree, lease.base_sha)
        assert sorted(parse_patch_paths(patch)) == ["calc/format.py", "calc/helpers.py"]
    finally:
        assert release_workspace(lease) is None
    assert not lease.parent.exists()


def _stubborn(lease, pidfile: Path) -> list[str]:
    """A cell command that ignores SIGTERM and leaves a background child in the group."""
    script = f"trap '' TERM; sleep 60 & echo $! > {pidfile}; wait"
    return cell_command(["/bin/sh", "-c", script], cwd=lease.worktree, environment=cell_environment(parent=lease.parent))


def test_an_isolated_command_that_ignores_sigterm_is_killed_from_the_cell_side(
    tmp_path: Path, cell_scratch: Path
) -> None:
    lease = _isolated(tmp_path)
    pidfile = lease.parent / "tmp" / "child.pid"
    try:
        result = run_prepared_command(lease, command=_stubborn(lease, pidfile), timeout=2)
        assert result.code is WorkspaceCode.COMMAND_TIMEOUT, result.message
        assert not cell_process_alive(int(pidfile.read_text()))
    finally:
        assert release_workspace(lease) is None


def test_without_the_cell_side_kill_the_maintainer_cannot_confirm_teardown(
    tmp_path: Path, cell_scratch: Path
) -> None:
    lease = _isolated(tmp_path)
    pidfile = lease.parent / "tmp" / "child.pid"
    process = subprocess.Popen(_stubborn(lease, pidfile), cwd=lease.worktree, start_new_session=True)
    try:
        deadline = time.monotonic() + 10
        while not pidfile.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        safe, detail = _teardown_process(process, 0.25)
        assert safe is False and "unconfirmed" in (detail or "")
        assert cell_process_alive(int(pidfile.read_text()))
    finally:
        assert kill_cell_group(process.pid, timeout=5) is None
        process.wait(timeout=5)
        lease._state.process_cleanup_safe = True
        assert release_workspace(lease) is None
```

- [ ] **Step 2: Run to verify failure.** `uv run pytest tests/test_cell.py -q` → collection error `ImportError: cannot import name 'LIVE_TRANSCRIPT_NAME' from 'satyrn_evals.attempt'`. `uv run pytest -m integration -q tests/integration/test_cell_isolation.py` → `ImportError while loading conftest '…/tests/integration/conftest.py'` … `No module named 'satyrn_evals.cell'` (the new conftest stops every integration collection until Step 3 lands; nothing is committed in between).

- [ ] **Step 3: Implement.** `src/satyrn_evals/cell.py`:

```python
"""Two-uid isolation: the model runs as ``satyrn-cell``, everything else as the maintainer.

The spec's isolation condition ("Isolation, both arms"): the harness, grader,
task directories and retained cells stay under the maintainer's uid; the
worktree lives in a group directory the cell user writes and the grader
reads; the model process runs as a second local user with its own home,
per-cell ``TMPDIR``, Pi, uv and Pi model config. Nothing is sandboxed.

What this module knows, verified on the maintainer's Mac on 2026-09-14
(isolation spike):

- ``sudo -n -H -u satyrn-cell`` works without a password (one sudoers line).
  sudo keeps the caller's working directory, and node dies with
  ``EACCES uv_cwd`` when the cell cannot enter it, so every cell command
  ``cd``s first and every caller starts sudo from a cell-readable directory.
- sudo runs the command in the caller's process group (no pty when no
  terminal is attached) and relays SIGTERM to it, but the maintainer cannot
  signal a cell-owned process: ``killpg`` skips them silently and SIGKILL
  never reaches them. A cell-side ``kill -KILL -- -PGID`` does.
- Git refuses a repository the current user does not own ("dubious
  ownership"). Each cell gets its own global git config
  (``GIT_CONFIG_GLOBAL``, protected configuration) naming its one worktree
  as a ``safe.directory`` and a commit identity. ``GIT_CONFIG_COUNT`` would
  not do: it is a repository-local variable, and the engine's ``deliver``
  strips those before it runs git.
- The cell writes into maintainer-made entries through the group
  (``satyrn``, mode 2770/660). The maintainer reads and removes what the
  cell makes through an inherited ACL entry on the workspace parent: the
  engine creates its transcript ``0600`` with ``O_EXCL``, and a tool may make
  a ``0700`` directory, so neither umask nor group bits are enough.

``env -i`` gives the model an ordinary user environment: sudo's own
``SUDO_*`` variables and the maintainer's environment never reach it.
"""

import os
import pwd
import subprocess
from collections.abc import Callable, Mapping, Sequence
from enum import StrEnum
from pathlib import Path

CELL_USER = "satyrn-cell"
CELL_HOME = Path("/Users/satyrn-cell")
CELLS_ROOT = Path("/Users/Shared/satyrn-cells")
#: What the harness exports to an adapter: which profile this attempt runs under.
ISOLATION_ENV = "SATYRN_ISOLATION"
#: The workspace parent the harness allocated under ``CELLS_ROOT``; the
#: cell's TMPDIR, uv project environment and git config live beside the worktree.
CELL_PARENT_ENV = "SATYRN_CELL_PARENT"
#: Directories prepended to the cell's PATH. A test seam (fake ``pi``); the
#: launcher refuses an isolated admission, route-proof or campaign run with it set.
CELL_PATH_PREFIX_ENV = "SATYRN_CELL_PATH_PREFIX"
CELL_PATH: tuple[str, ...] = (
    os.fspath(CELL_HOME / ".local" / "bin"),
    os.fspath(CELL_HOME / ".npm-global" / "bin"),
    "/opt/homebrew/bin",
    "/usr/bin",
    "/bin",
    "/usr/sbin",
    "/sbin",
)
_CELL_SCRIPT = 'umask 007 && cd "$1" && shift && exec "$@"'


class Isolation(StrEnum):
    """The launcher profiles (Ruling 1): two-uid, or the maintainer's own uid."""

    ISOLATED = "isolated"
    LOCAL = "local"


def isolation_from(environment: Mapping[str, str]) -> Isolation:
    """The profile the harness exported; absent means local (contributors, Engine users)."""
    raw = environment.get(ISOLATION_ENV, Isolation.LOCAL.value)
    try:
        return Isolation(raw)
    except ValueError:
        raise ValueError(f"{ISOLATION_ENV} must be isolated or local, got {raw!r}") from None


def cell_paths(parent: Path) -> tuple[Path, Path, Path]:
    """(TMPDIR, uv project environment, git config) of the cell whose workspace parent is ``parent``."""
    return parent / "tmp", parent / "environment", parent / "gitconfig"


def cell_gitconfig(worktree: Path) -> str:
    """The per-cell global git config: the one safe directory and a commit identity."""
    return (
        f"[safe]\n\tdirectory = {os.fspath(worktree)}\n"
        f"[user]\n\tname = {CELL_USER}\n\temail = {CELL_USER}@localhost\n"
    )


def cell_environment(
    *,
    parent: Path,
    extra: Mapping[str, str] | None = None,
    path_prefix: Sequence[str] = (),
) -> dict[str, str]:
    """The whole environment a cell command sees; nothing else is inherited."""
    tmpdir, uv_environment, gitconfig = cell_paths(parent)
    environment = {
        "HOME": os.fspath(CELL_HOME),
        "USER": CELL_USER,
        "LOGNAME": CELL_USER,
        "SHELL": "/bin/zsh",
        "PATH": os.pathsep.join([*path_prefix, *CELL_PATH]),
        "TMPDIR": os.fspath(tmpdir),
        "UV_PROJECT_ENVIRONMENT": os.fspath(uv_environment),
        "PYTHONDONTWRITEBYTECODE": "1",
        "GIT_CONFIG_GLOBAL": os.fspath(gitconfig),
    }
    environment.update(extra or {})
    return environment


def model_environment(environment: Mapping[str, str], extra: Mapping[str, str] | None = None) -> dict[str, str]:
    """The cell environment for an adapter, from what the harness exported."""
    if not (parent := environment.get(CELL_PARENT_ENV, "")):
        raise ValueError(f"{CELL_PARENT_ENV} is required under isolation")
    return cell_environment(parent=Path(parent), extra=extra, path_prefix=path_prefix_from(environment))


def path_prefix_from(environment: Mapping[str, str]) -> tuple[str, ...]:
    return tuple(entry for entry in environment.get(CELL_PATH_PREFIX_ENV, "").split(os.pathsep) if entry)


def cell_command(argv: Sequence[str], *, cwd: Path, environment: Mapping[str, str]) -> list[str]:
    """``argv`` run as the cell user, in ``cwd``, with exactly ``environment``."""
    if not argv:
        raise ValueError("cell command is empty")
    return [
        "sudo", "-n", "-H", "-u", CELL_USER, "--",
        "/usr/bin/env", "-i", *(f"{key}={value}" for key, value in sorted(environment.items())),
        "/bin/sh", "-c", _CELL_SCRIPT, "satyrn-cell", os.fspath(cwd), *argv,
    ]


def cell_kill_command(process_group: int) -> list[str]:
    """SIGKILL, sent as the cell user, to every cell-owned process in ``process_group``."""
    if process_group <= 1:
        raise ValueError(f"refusing to signal process group {process_group}")
    return ["sudo", "-n", "-u", CELL_USER, "--", "/bin/kill", "-KILL", "--", f"-{process_group}"]


def kill_cell_group(
    process_group: int, *, timeout: float, run: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run
) -> str | None:
    """Kill the cell's members of a process group; a description of any failure, else None.

    ``kill`` exits 1 when the group is already empty; that is success here.
    """
    try:
        completed = run(
            cell_kill_command(process_group), cwd="/", capture_output=True, timeout=timeout, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"cannot kill the cell's process group: {exc}"
    if completed.returncode not in (0, 1):
        return f"cell kill exited {completed.returncode}: {os.fsdecode(completed.stderr).strip()}"
    return None


def cell_unavailable_reason(run: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run) -> str | None:
    """None when ``sudo -n -u satyrn-cell true`` works and the cells root exists; else why not."""
    if not CELLS_ROOT.is_dir():
        return f"{CELLS_ROOT} does not exist (run the isolation setup)"
    try:
        completed = run(
            ["sudo", "-n", "-u", CELL_USER, "--", "/usr/bin/true"], cwd="/", capture_output=True, timeout=10, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"sudo -n -u {CELL_USER} cannot run: {exc}"
    if completed.returncode != 0:
        return f"sudo -n -u {CELL_USER} true exited {completed.returncode}: {os.fsdecode(completed.stderr).strip()}"
    return None


#: The rights the maintainer keeps, inherited by every file and directory created below.
MAINTAINER_RIGHTS = (
    "list,search,add_file,add_subdirectory,delete_child,read,write,append,"
    "readattr,writeattr,readextattr,writeextattr,readsecurity,delete,file_inherit,directory_inherit"
)


def maintainer_ace() -> str:
    return f"user:{pwd.getpwuid(os.getuid()).pw_name} allow {MAINTAINER_RIGHTS}"


def grant_maintainer(
    directory: Path, run: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run
) -> str | None:
    """Add the inherited maintainer ACL entry to ``directory``; why it failed, else None.

    Only entries created after this carry it, so call it on an empty directory.
    """
    try:
        completed = run(["/bin/chmod", "+a", maintainer_ace(), os.fspath(directory)], capture_output=True, check=False)
    except OSError as exc:
        return f"cannot run chmod +a: {exc}"
    if completed.returncode != 0:
        return f"chmod +a exited {completed.returncode}: {os.fsdecode(completed.stderr).strip()}"
    return None


def share_with_cell(root: Path) -> None:
    """Make every directory under ``root`` group rwx+setgid and every file group rw.

    The cells root is ``pauleveritt:satyrn`` 2770, so new entries are already
    group ``satyrn`` (BSD group inheritance); only the mode needs widening.
    Entries the cell user created are its own to share (it writes under
    ``umask 007``) and are left alone, as are symbolic links.
    """
    owner = os.getuid()
    for directory, _dirs, files in os.walk(root):  # never follows directory symlinks
        if os.stat(directory).st_uid == owner:
            os.chmod(directory, 0o2770)
        for name in files:
            path = Path(directory) / name
            if not path.is_symlink() and (info := path.stat()).st_uid == owner:
                os.chmod(path, info.st_mode & 0o7777 | 0o060)
```

`src/satyrn_evals/workspace.py` (the three teardown call sites go through `_teardown` so the existing default-tier rows that replace `_teardown_process` with a two-argument fake keep working; the local allocation call is unchanged for the same reason):

```diff
diff --git a/src/satyrn_evals/workspace.py b/src/satyrn_evals/workspace.py
index ccdc78d..e599869 100644
--- a/src/satyrn_evals/workspace.py
+++ b/src/satyrn_evals/workspace.py
@@ -24,6 +24,15 @@ from typing import BinaryIO

 from satyrn_evals.attempt_record import DeadlinePhase
 from satyrn_evals.budget import AttemptBudget, BudgetTripwire
+from satyrn_evals.cell import (
+    CELLS_ROOT,
+    Isolation,
+    cell_gitconfig,
+    cell_paths,
+    grant_maintainer,
+    kill_cell_group,
+    share_with_cell,
+)
 from satyrn_evals.deadline import AttemptDeadline, AttemptDeadlineExceeded
 from satyrn_evals.errors import OracleError, OverlayError, SatyrnError
 from satyrn_evals.overlay import OverlaySpec, assert_overlay_absent
@@ -200,6 +209,7 @@ class _WorkspaceState:
     registration: Registration = Registration.ABSENT
     process_cleanup_safe: bool = True
     base_sha: str | None = None
+    isolation: Isolation = Isolation.LOCAL

     def begin_add(self) -> None:
         if self.registration is not Registration.ABSENT:
@@ -356,10 +366,18 @@ def _contains_path(root: Path, path: Path) -> bool:
         ) from exc


-def _safe_temp_parent(protected: Sequence[Path]) -> Path:
-    """Allocate outside task/output roots without trusting inherited TMPDIR."""
+def _safe_temp_parent(
+    protected: Sequence[Path], roots: Sequence[Path] | None = None
+) -> Path:
+    """Allocate outside task/output roots without trusting inherited TMPDIR.
+
+    ``roots`` replaces the temporary-directory candidates; an isolated
+    attempt passes the cells root and nothing else.
+    """
     candidate_roots = dict.fromkeys(
-        (Path(tempfile.gettempdir()), Path("/tmp"), Path("/var/tmp"))
+        roots
+        if roots is not None
+        else (Path(tempfile.gettempdir()), Path("/tmp"), Path("/var/tmp"))
     )
     failures: list[str] = []
     protected_roots = tuple(path.resolve() for path in protected)
@@ -867,13 +885,17 @@ def _wait_until_group_gone(process_group: int, deadline: float) -> bool:


 def _teardown_process(
-    process: subprocess.Popen[bytes], grace: float
+    process: subprocess.Popen[bytes], grace: float, *, cell: bool = False
 ) -> tuple[bool, str | None]:
     """Best-effort teardown within one grace period.

     The allowance begins with termination, rather than being granted afresh
     for each signal, reap, and process-group observation.  Safe still means
     that the direct child is reaped and (on POSIX) its process group is gone.
+
+    ``cell``: the group holds processes the cell user owns. The maintainer's
+    SIGKILL cannot reach them, so a group still present after SIGTERM is
+    also killed from the cell side (`cell.kill_cell_group`).
     """
     details: list[str] = []
     started = time.monotonic()
@@ -901,6 +923,10 @@ def _teardown_process(
                 pass
             except OSError as exc:
                 details.append(f"cannot signal process group with SIGKILL: {exc}")
+            if cell and (
+                failure := kill_cell_group(process.pid, timeout=max(remaining(), 0.05))
+            ):
+                details.append(failure)
     else:  # Windows is a direct-child fallback, not part of V4's proof.
         try:
             process.terminate()
@@ -928,6 +954,15 @@ def _teardown_process(
     return reaped and gone, "; ".join(details) or None


+def _teardown(
+    process: subprocess.Popen[bytes], grace: float, state: _WorkspaceState
+) -> tuple[bool, str | None]:
+    """Tear down the command, from the cell side too when the attempt is isolated."""
+    if state.isolation is Isolation.ISOLATED:
+        return _teardown_process(process, grace, cell=True)
+    return _teardown_process(process, grace)
+
+
 def _wait_or_trip(
     process: subprocess.Popen[bytes],
     *,
@@ -1103,7 +1138,7 @@ def _run_command(
                 )
             except subprocess.TimeoutExpired:
                 try:
-                    safe, detail = _teardown_process(process, teardown_grace)
+                    safe, detail = _teardown(process, teardown_grace, state)
                 except BaseException as exc:
                     active_exception = exc
                     _add_exception_note(
@@ -1131,7 +1166,7 @@ def _run_command(
             except BaseException as exc:
                 active_exception = exc
                 try:
-                    safe, detail = _teardown_process(process, teardown_grace)
+                    safe, detail = _teardown(process, teardown_grace, state)
                 except BaseException as cleanup_error:
                     _add_exception_note(
                         exc,
@@ -1164,7 +1199,7 @@ def _run_command(
                     # a stopped cell is never mistaken for one that refused
                     # on its own. Artifacts already written are harvested.
                     try:
-                        safe, detail = _teardown_process(process, teardown_grace)
+                        safe, detail = _teardown(process, teardown_grace, state)
                     except BaseException as exc:
                         active_exception = exc
                         _add_exception_note(
@@ -1577,6 +1612,30 @@ def _validate_command_limits(
         )


+def _share_workspace(
+    state: _WorkspaceState,
+    environment: Mapping[str, str],
+    *,
+    deadline: AttemptDeadline | None = None,
+) -> None:
+    """Hand the cell user a group-shared repository and its own TMPDIR, uv environment and git config."""
+    _deadline_git(
+        state.repository,
+        ("config", "core.sharedRepository", "group"),
+        environment,
+        deadline=deadline,
+        phase=DeadlinePhase.SETUP,
+    )
+    tmpdir, uv_environment, gitconfig = cell_paths(state.parent)
+    try:
+        tmpdir.mkdir()
+        uv_environment.mkdir()
+        gitconfig.write_text(cell_gitconfig(state.worktree), encoding="utf-8")
+        share_with_cell(state.parent)
+    except OSError as exc:
+        raise _WorkspaceError(f"cannot share the workspace with the cell user: {exc}") from exc
+
+
 def prepare_workspace(
     *,
     base: Path,
@@ -1584,8 +1643,15 @@ def prepare_workspace(
     environment: Mapping[str, str],
     overlay: OverlaySpec | None = None,
     deadline: AttemptDeadline | None = None,
+    isolation: Isolation = Isolation.LOCAL,
 ) -> PreparedWorkspace:
-    """Reconstruct a detached worktree and retain its cleaned environment."""
+    """Reconstruct a detached worktree and retain its cleaned environment.
+
+    ``Isolation.ISOLATED`` allocates the parent under the cells root and,
+    once the base is verified, shares it with the cell user: a group-shared
+    repository, the cell's TMPDIR, uv environment and git config beside the
+    worktree, every entry group-writable.
+    """
     state: _WorkspaceState | None = None
     parent: Path | None = None
     git_environment: dict[str, str] | None = None
@@ -1607,7 +1673,13 @@ def prepare_workspace(
             git_protected = _git_protected_paths(requested_protected, git_environment)
         if deadline is not None:
             deadline.remaining(DeadlinePhase.SETUP)
-        parent = _safe_temp_parent((*requested_protected, *git_protected))
+        parent = (
+            _safe_temp_parent((*requested_protected, *git_protected), (CELLS_ROOT,))
+            if isolation is Isolation.ISOLATED
+            else _safe_temp_parent((*requested_protected, *git_protected))
+        )
+        if isolation is Isolation.ISOLATED and (failure := grant_maintainer(parent)):
+            raise _WorkspaceError(f"cannot keep the maintainer's access to {parent}: {failure}")
         if deadline is not None:
             deadline.remaining(DeadlinePhase.SETUP)
         state = _WorkspaceState(
@@ -1617,6 +1689,7 @@ def prepare_workspace(
             # neutral lease must not rename this internal directory.
             repository=parent / "seed",
             worktree=parent / "worktree",
+            isolation=isolation,
         )
         if deadline is not None:
             _prepare_repository(base, state, git_environment, deadline=deadline)
@@ -1628,6 +1701,8 @@ def prepare_workspace(
             assert_overlay_absent(state.worktree, overlay)
             if deadline is not None:
                 deadline.remaining(DeadlinePhase.SETUP)
+        if isolation is Isolation.ISOLATED:
+            _share_workspace(state, git_environment, deadline=deadline)
         assert state.base_sha is not None
         return PreparedWorkspace(
             parent=parent,
```

`src/satyrn_evals/attempt.py` (under the local profile the exported environment is byte-for-byte what 2a exported; `tests/test_attempt.py` pins it):

```diff
diff --git a/src/satyrn_evals/attempt.py b/src/satyrn_evals/attempt.py
index 0fe9bcb..042ef2d 100644
--- a/src/satyrn_evals/attempt.py
+++ b/src/satyrn_evals/attempt.py
@@ -29,6 +29,7 @@ from satyrn_evals.attempt_record import (
     write_attempt_record,
 )
 from satyrn_evals.budget import AttemptBudget
+from satyrn_evals.cell import CELL_PARENT_ENV, ISOLATION_ENV, Isolation
 from satyrn_evals.deadline import AttemptDeadline, AttemptDeadlineExceeded
 from satyrn_evals.engine_contract import (
     engine_contract_path,
@@ -61,6 +62,10 @@ TASK_CONTRACT_ENV = "SATYRN_TASK_CONTRACT"
 PATCH_ENV = "SATYRN_ATTEMPT_PATCH"
 TRANSCRIPT_ENV = "SATYRN_ATTEMPT_TRANSCRIPT"
 BASE_SHA_ENV = "SATYRN_WORKSPACE_BASE_SHA"
+#: Under isolation the command's transcript is written here, beside the
+#: worktree where the cell user can write, and copied into the attempt
+#: directory as soon as the command returns.
+LIVE_TRANSCRIPT_NAME = "transcript.txt"

 type SelectedContract = tuple[str | None, str]

@@ -147,6 +152,12 @@ def _is_engine_wrapper_command(command: list[str]) -> bool:
     )


+def _collect_live_transcript(live: Path, transcript_path: Path) -> None:
+    """Copy an isolated command's transcript into the attempt directory, if it wrote one."""
+    if live != transcript_path and live.is_file():
+        shutil.copyfile(live, transcript_path)
+
+
 def _add_exception_note(error: BaseException, note: str) -> None:
     """Attach recovery evidence without replacing the primary exception."""
     with suppress(BaseException):
@@ -191,6 +202,7 @@ def attempt(
     max_repeated_calls: int | None = None,
     attempt_timeout: float | None = None,
     budget: AttemptBudget | None = None,
+    isolation: Isolation = Isolation.LOCAL,
 ) -> AttemptRecord:
     """Run an unbounded attempt through the stable public API."""
     return _attempt(
@@ -203,6 +215,7 @@ def attempt(
         max_repeated_calls=max_repeated_calls,
         attempt_timeout=attempt_timeout,
         budget=budget,
+        isolation=isolation,
     )


@@ -218,6 +231,7 @@ def _attempt(
     deadline: AttemptDeadline | None = None,
     attempt_timeout: float | None = None,
     budget: AttemptBudget | None = None,
+    isolation: Isolation = Isolation.LOCAL,
 ) -> AttemptRecord:
     """Run COMMAND against TASK, preserve patch + transcript, grade, and record.

@@ -301,6 +315,7 @@ def _attempt(
                     else None
                 ),
                 deadline=deadline,
+                isolation=isolation,
             )
         except WorkspacePrepareError as exc:
             if exc.deadline is not None:
@@ -354,18 +369,28 @@ def _attempt(
                 # above) so prepare_workspace still receives it for anything
                 # that materializes the task workspace's environment.
                 workspace_lease._environment.pop("UV_PROJECT_ENVIRONMENT", None)
+            exported = {BASE_SHA_ENV: workspace_lease.base_sha}
+            live_transcript = transcript_path
+            if isolation is Isolation.ISOLATED:
+                live_transcript = workspace_lease.parent / LIVE_TRANSCRIPT_NAME
+                exported[ISOLATION_ENV] = isolation.value
+                exported[CELL_PARENT_ENV] = os.fspath(workspace_lease.parent)
+                exported[TRANSCRIPT_ENV] = os.fspath(live_transcript)
             try:
-                workspace = run_prepared_command(
-                    workspace_lease,
-                    command=effective_command,
-                    timeout=timeout,
-                    transcript=transcript_path,
-                    max_repeated_calls=max_repeated_calls,
-                    deadline=deadline,
-                    extra_environment={BASE_SHA_ENV: workspace_lease.base_sha},
-                    budget=budget,
-                    timeline=attempt_dir / TIMELINE_NAME,
-                )
+                try:
+                    workspace = run_prepared_command(
+                        workspace_lease,
+                        command=effective_command,
+                        timeout=timeout,
+                        transcript=live_transcript,
+                        max_repeated_calls=max_repeated_calls,
+                        deadline=deadline,
+                        extra_environment=exported,
+                        budget=budget,
+                        timeline=attempt_dir / TIMELINE_NAME,
+                    )
+                finally:
+                    _collect_live_transcript(live_transcript, transcript_path)
                 if deadline is not None and workspace.code not in (
                     WorkspaceCode.COMMAND_TIMEOUT,
                     WorkspaceCode.REPEAT_LIMIT,
```

- [ ] **Step 4: Pass.** `uv run pytest tests/test_cell.py -q` → 17 passed. `uv run pytest -m integration -q tests/integration/test_cell_isolation.py; echo "EXIT: $?"` → 5 passed (or 5 skipped naming the reason on a machine without the cell user; on the maintainer's Mac they must pass). Then the named 2a rows: `SATYRN_V4_ENGINE_REPO=/Users/pauleveritt/projects/pauleveritt/satyrn-engine uv run pytest -m integration -q tests/integration/test_engine_arm.py tests/integration/test_harvest_qualification.py tests/integration/test_budget_attempt.py tests/integration/test_timeline_attempt.py tests/integration/test_evidence_run.py tests/integration/test_workspace.py "tests/integration/test_attempt.py::test_real_e5_attempt_produces_persisted_patch_and_transcript"; echo "EXIT: $?"` → 0. Confirm nothing was left: `ls /Users/Shared/satyrn-cells` shows no `satyrn-attempt-*` or `satyrn-test-*`, and `ps -A -o user=,command= | grep '^satyrn-cell' | grep -v -e /usr/libexec/ -e /usr/sbin/ -e /System/` prints nothing.

- [ ] **Step 5: Record, gates, commit.**

```bash
uv run python tools/provenance.py new src/satyrn_evals/cell.py tests/test_cell.py tests/integration/conftest.py tests/integration/cell_support.py tests/integration/test_cell_isolation.py
uv run ruff check --fix; just gates; echo "EXIT: $?"
git add -A && git commit -m "Phase 2b: the model side of a cell can run as satyrn-cell; the workspace is shared under the cells root and a stopped cell is killed from the cell side"
```

---

### Task 2: Both arms under isolation against a fake, with the budget tripwire

**Files:**
- Create: `src/satyrn_evals/cell_engine.py`, `tests/integration/test_isolated_arms.py`
- Modify: `src/satyrn_evals/attempt_pi.py` (import; `pi_command`; `main`), `src/satyrn_evals/attempt_engine.py` (imports; `CHECKOUT_LOG_NAME`; `_engine`, `derive_argv`, `deliver_argv` `no_sync=`; `isolated`, `as_cell`, `checkout_candidate`; `main`), `src/satyrn_evals/cli.py` (`cell-engine`), `tests/test_attempt_pi.py`, `tests/test_attempt_engine.py`

**Interfaces:**
- Consumes (Task 1): `cell.Isolation`, `isolation_from`, `model_environment`, `cell_command`, `CELLS_ROOT`, `CELL_PATH_PREFIX_ENV`, `grant_maintainer`, `share_with_cell`; `attempt.attempt(isolation=)`; fixture `cell_scratch`; `cell_support.cell_process_alive`, `run_as_cell`.
- Produces: `attempt_pi.pi_command(args, prompt, environment, worktree) -> list[str]` (AdapterError on an incomplete isolated export); `attempt_engine.derive_argv(args, worktree, request, *, no_sync=False)`, `deliver_argv(args, worktree, contract, *, no_sync=False)`, `isolated(args, environment) -> bool` (AdapterError for an engine outside the cells root), `as_cell(argv, args, environment, worktree) -> list[str]`, `checkout_candidate(commit, log) -> int`, `CHECKOUT_LOG_NAME = "engine-checkout.txt"`; the Engine adapter writes `engine-derive.txt`, `engine-deliver.txt`, `engine-receipt.json` and `engine-checkout.txt` beside `patch.diff`. `cell_engine.export_engine(engine_repo, commit, *, root=CELLS_ROOT, python=CELL_PYTHON) -> Path`, `export_path(commit, root)`, `EngineExportError(UsageError)`, `MARKER`; `satyrn-evals cell-engine --engine-repo R --commit SHA` prints the export path.

- [ ] **Step 1: Failing tests.** Append to `tests/test_attempt_pi.py` and `tests/test_attempt_engine.py` (the import blocks gain the new names; no existing assertion changes):

```diff
diff --git a/tests/test_attempt_pi.py b/tests/test_attempt_pi.py
index 3f187ef..83713ca 100644
--- a/tests/test_attempt_pi.py
+++ b/tests/test_attempt_pi.py
@@ -26,10 +26,12 @@ from satyrn_evals.attempt_pi import (
     harvest_patch,
     main,
     parse_args,
+    pi_command,
     read_artifact_paths,
     read_base_sha,
     read_prompt,
 )
+from satyrn_evals.cell import CELL_PARENT_ENV, ISOLATION_ENV
 from satyrn_evals.session_patch import RESIDUE_EXCLUDES, PatchCapture

 MODEL = "omlx/gemma-4-12B-it-MLX-8bit"
@@ -400,3 +402,29 @@ def test_an_argv_without_the_flag_is_detected_as_non_parity() -> None:
     tampered = [token for token in argv if token != "--no-context-files"]
     missing = [flag for flag in ENGINE_HERMETIC_FLAGS if flag not in tampered]
     assert missing == ["--no-context-files"]
+
+
+# --- 2b: the isolated profile ------------------------------------------------
+
+
+def test_the_local_profile_runs_pi_directly() -> None:
+    args = parse_args(["--model", MODEL])
+    assert pi_command(args, "fix it", {}, Path("/w")) == build_pi_argv(args, "fix it")
+
+
+def test_the_isolated_profile_runs_pi_as_the_cell_user_in_the_worktree() -> None:
+    args = parse_args(["--model", MODEL])
+    exported = {ISOLATION_ENV: "isolated", CELL_PARENT_ENV: "/cells/a"}
+    argv = pi_command(args, "fix it", exported, Path("/cells/a/worktree"))
+    assert argv[:5] == ["sudo", "-n", "-H", "-u", "satyrn-cell"]
+    assert "TMPDIR=/cells/a/tmp" in argv and "UV_PROJECT_ENVIRONMENT=/cells/a/environment" in argv
+    assert argv[argv.index("satyrn-cell", 5) + 1 :] == ["/cells/a/worktree", *build_pi_argv(args, "fix it")]
+
+
+@pytest.mark.parametrize(
+    ("exported", "message"),
+    [({ISOLATION_ENV: "isolated"}, CELL_PARENT_ENV), ({ISOLATION_ENV: "sandbox"}, "isolated or local")],
+)
+def test_an_isolated_profile_the_harness_did_not_complete_is_refused(exported: dict[str, str], message: str) -> None:
+    with pytest.raises(AdapterError, match=message):
+        pi_command(parse_args(["--model", MODEL]), "fix it", exported, Path("/w"))
```

```diff
diff --git a/tests/test_attempt_engine.py b/tests/test_attempt_engine.py
index 5af17a1..fcfdf56 100644
--- a/tests/test_attempt_engine.py
+++ b/tests/test_attempt_engine.py
@@ -13,18 +13,23 @@ import pytest

 from satyrn_evals import attempt_engine, attempt_pi
 from satyrn_evals.attempt_engine import (
+    CHECKOUT_LOG_NAME,
     DELIVER_TIMEOUT_SECONDS,
     ENGINE_REPO_ENV,
     RECEIPT_NAME,
     AdapterError,
+    as_cell,
     candidate_commit,
+    checkout_candidate,
     contract_path,
     deliver_argv,
     delivery_environment,
     derive_argv,
+    isolated,
     main,
     parse_args,
 )
+from satyrn_evals.cell import CELL_PARENT_ENV, ISOLATION_ENV

 ENGINE = Path("/opt/satyrn-engine")
 WORKTREE = Path("/w/worktree")
@@ -125,3 +130,71 @@ def test_main_without_a_candidate_checks_out_nothing_and_still_writes_the_patch(
     assert main(["--model", "omlx/m"]) == 5
     assert len(calls) == 1 and "derive" in calls[0]
     assert (seam / "patch.diff").read_text() == f"harvested {BASE}\n"
+
+
+# --- 2b: the isolated profile ------------------------------------------------
+
+
+def _args(engine: Path = ENGINE) -> attempt_engine.EngineArgs:
+    return parse_args(["--model", "omlx/m", "--engine-repo", str(engine)], {})
+
+
+def test_under_isolation_the_engine_calls_do_not_sync_the_shared_export() -> None:
+    assert derive_argv(_args(), WORKTREE, "req", no_sync=True)[:3] == ["uv", "run", "--no-sync"]
+    delivered = deliver_argv(_args(), WORKTREE, CONTRACT, no_sync=True)
+    assert delivered.count("--no-sync") == 2
+    assert "--no-sync" not in derive_argv(_args(), WORKTREE, "req")
+
+
+def test_the_local_profile_is_not_isolated() -> None:
+    assert isolated(_args(), {}) is False
+
+
+def test_an_isolated_engine_outside_the_cells_root_is_refused(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
+    monkeypatch.setattr(attempt_engine, "CELLS_ROOT", tmp_path)
+    with pytest.raises(AdapterError, match="must be an export under"):
+        isolated(_args(Path("/Users/someone/satyrn-engine")), {ISOLATION_ENV: "isolated"})
+    assert isolated(_args(tmp_path / "engine-abc"), {ISOLATION_ENV: "isolated"}) is True
+
+
+def test_an_engine_call_as_the_cell_carries_the_transcript_and_the_export_but_not_the_models_uv_environment() -> None:
+    exported = {ISOLATION_ENV: "isolated", CELL_PARENT_ENV: "/cells/a", attempt_pi.TRANSCRIPT_ENV: "/cells/a/transcript.txt"}
+    argv = as_cell(["uv", "run"], _args(Path("/cells/engine-abc")), exported, Path("/cells/a/worktree"))
+    assert "SATYRN_ATTEMPT_TRANSCRIPT=/cells/a/transcript.txt" in argv
+    assert "SATYRN_ENGINE_REPO=/cells/engine-abc" in argv
+    assert not any(token.startswith("UV_PROJECT_ENVIRONMENT=") for token in argv)
+    assert argv[-2:] == ["uv", "run"]
+
+
+def test_an_engine_call_as_the_cell_without_the_harness_exports_is_refused() -> None:
+    with pytest.raises(AdapterError, match="cell environment"):
+        as_cell(["uv"], _args(), {ISOLATION_ENV: "isolated"}, WORKTREE)
+
+
+def test_a_failed_candidate_checkout_is_logged_and_returned(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    monkeypatch.setattr(
+        attempt_engine.subprocess, "run", lambda argv, **kw: subprocess.CompletedProcess(argv, 128, "", "fatal: bad object\n")
+    )
+    log = tmp_path / CHECKOUT_LOG_NAME
+    assert checkout_candidate(COMMIT, log) == 128
+    assert "fatal: bad object" in log.read_text()
+
+
+def test_a_candidate_checkout_that_succeeds_writes_no_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    monkeypatch.setattr(attempt_engine.subprocess, "run", lambda argv, **kw: subprocess.CompletedProcess(argv, 0, "", ""))
+    assert checkout_candidate(COMMIT, tmp_path / CHECKOUT_LOG_NAME) == 0
+    assert not (tmp_path / CHECKOUT_LOG_NAME).exists()
+
+
+def test_main_returns_the_checkout_failure_and_still_writes_the_patch(seam: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    calls, run = _fake_run(0, {"code": "OK", "candidate_commit": COMMIT})
+
+    def failing_checkout(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
+        if argv[0] == "git":
+            return subprocess.CompletedProcess(argv, 128, "", "fatal: reference is not a tree\n")
+        return run(argv, **kwargs)  # type: ignore[operator]
+
+    monkeypatch.setattr(attempt_engine.subprocess, "run", failing_checkout)
+    assert main(["--model", "omlx/m"]) == 128
+    assert "reference is not a tree" in (seam / CHECKOUT_LOG_NAME).read_text()
+    assert (seam / "patch.diff").read_text() == f"harvested {BASE}\n"
```

`tests/integration/test_isolated_arms.py` (row 2b's "both arms against a fake under isolation with the budget tripwire"):

```python
"""Both arms under two-uid isolation, against a fake model, with the budget tripwire.

Roadmap row 2b: "the eval runs both arms against a fake under isolation
with the budget tripwire". The real harness, the real adapters, real sudo
and git; ``pi`` is `fake_pi_build.py` run as the cell user from a scratch
directory under the cells root. The Engine rows also need an engine
checkout (``SATYRN_V4_ENGINE_REPO``, as the Phase 2a rows do), exported for
the cell with `cell_engine.export_engine`. No model runs.
"""

import json
import os
import shutil
import sys
import time
from pathlib import Path

import pytest

from integration.cell_support import cell_process_alive
from integration.test_attempt import (
    _engine_repo,  # type: ignore[missing-import]  # pytest sibling resolution
)
from satyrn_evals.attempt import attempt
from satyrn_evals.attempt_engine import RECEIPT_NAME
from satyrn_evals.attempt_record import AttemptCode
from satyrn_evals.budget import AttemptBudget
from satyrn_evals.cell import (
    CELL_PATH_PREFIX_ENV,
    CELLS_ROOT,
    Isolation,
    share_with_cell,
)
from satyrn_evals.cell_engine import export_engine
from satyrn_evals.patch import parse_patch_paths
from satyrn_evals.verdict import Verdict

pytestmark = pytest.mark.integration

TASKS = Path(__file__).parent / "data" / "tasks"
FAKE_PI = Path(__file__).parent / "fake_pi_build.py"
CAMPAIGN = AttemptBudget(output_tokens=32_000, turns=48)


def _cell_pi(scratch: Path, monkeypatch: pytest.MonkeyPatch, mode: str) -> Path:
    """Put a cell-readable fake ``pi`` first on the cell's PATH; return its pidfile path."""
    bin_dir = scratch / "bin"
    bin_dir.mkdir()
    shutil.copyfile(FAKE_PI, bin_dir / "fake_pi_build.py")
    pidfile = scratch / "pi.pid"
    shim = bin_dir / "pi"
    shim.write_text(
        f"#!/bin/sh\nSATYRN_FAKE_PI_MODE={mode} SATYRN_FAKE_PI_PIDFILE={pidfile} "
        f'exec python3 {bin_dir / "fake_pi_build.py"} "$@"\n'
    )
    shim.chmod(0o755)
    share_with_cell(scratch)
    monkeypatch.setenv(CELL_PATH_PREFIX_ENV, os.fspath(bin_dir))
    return pidfile


def _gone(pidfile: Path) -> None:
    pid = int(pidfile.read_text())
    stop = time.monotonic() + 15
    while time.monotonic() < stop:
        if not cell_process_alive(pid):
            return
        time.sleep(0.1)
    pytest.fail(f"fake pi {pid} outlived its cell")


def _baseline() -> list[str]:
    return [sys.executable, "-m", "satyrn_evals.attempt_pi", "--model", "omlx/fixture"]


def _no_cells_left(before: set[str]) -> None:
    assert {p.name for p in CELLS_ROOT.iterdir() if p.name.startswith("satyrn-attempt-")} <= before


def test_an_isolated_baseline_cell_commits_as_the_cell_user_and_is_harvested_whole(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cell_scratch: Path
) -> None:
    _cell_pi(cell_scratch, monkeypatch, "commit")
    before = {p.name for p in CELLS_ROOT.iterdir()}
    output = tmp_path / "attempts"
    record = attempt(
        task="calc-build", tasks_root=TASKS, output=output, command=_baseline(), timeout=120,
        budget=CAMPAIGN, isolation=Isolation.ISOLATED,
    )
    assert (record.code, record.verdict) == (AttemptCode.OK, Verdict.PASS), record.message
    assert record.attempt_dir is not None
    cell = output / record.attempt_dir
    assert sorted(parse_patch_paths((cell / "patch.diff").read_text())) == ["calc/core.py", "calc/format.py", "calc/helpers.py"]
    assert json.loads((cell / "transcript.txt").read_text().splitlines()[0])["cwd"].startswith(os.fspath(CELLS_ROOT.resolve()))
    _no_cells_left(before)


def test_an_isolated_baseline_cell_over_budget_is_stopped_and_leaves_no_model_running(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cell_scratch: Path
) -> None:
    pidfile = _cell_pi(cell_scratch, monkeypatch, "spend")
    record = attempt(
        task="calc-build", tasks_root=TASKS, output=tmp_path / "attempts", command=_baseline(), timeout=120,
        budget=CAMPAIGN, isolation=Isolation.ISOLATED,
    )
    assert record.code is AttemptCode.BUDGET_EXCEEDED, record.message
    assert (record.command_exit, record.retained_path) == (None, None)
    _gone(pidfile)


def _engine_arm(scratch: Path) -> list[str]:
    export = export_engine(_engine_repo(), "HEAD", root=scratch)
    uv = shutil.which("uv")
    assert uv is not None
    return [sys.executable, "-m", "satyrn_evals.attempt_engine", "--model", "omlx/fixture",
            "--engine-repo", os.fspath(export), "--uv-bin", "uv"]


def test_an_isolated_engine_cell_delivers_a_candidate_that_is_harvested_and_graded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cell_scratch: Path
) -> None:
    _cell_pi(cell_scratch, monkeypatch, "write")
    command = _engine_arm(cell_scratch)
    output = tmp_path / "attempts"
    record = attempt(
        task="calc-build", tasks_root=TASKS, output=output, command=command, timeout=300,
        budget=CAMPAIGN, isolation=Isolation.ISOLATED,
    )
    assert (record.code, record.verdict) == (AttemptCode.OK, Verdict.PASS), record.message
    assert record.attempt_dir is not None
    receipt = json.loads((output / record.attempt_dir / RECEIPT_NAME).read_text())
    assert (receipt["code"], receipt["validation"]) == ("OK", "passed")


def test_an_isolated_engine_cell_stopped_by_the_harness_leaves_no_model_running(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cell_scratch: Path
) -> None:
    pidfile = _cell_pi(cell_scratch, monkeypatch, "trickle")
    command = _engine_arm(cell_scratch)
    output = tmp_path / "attempts"
    record = attempt(
        task="calc-build", tasks_root=TASKS, output=output, command=command, timeout=300,
        budget=AttemptBudget(output_tokens=16_000, turns=48), isolation=Isolation.ISOLATED,
    )
    assert record.code is AttemptCode.BUDGET_EXCEEDED, record.message
    assert (record.command_exit, record.retained_path) == (None, None)
    _gone(pidfile)
    assert record.attempt_dir is not None
    assert not (output / record.attempt_dir / RECEIPT_NAME).exists()


def test_the_engine_export_is_made_once_and_runs_as_the_cell_user(cell_scratch: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from integration.cell_support import run_as_cell
    from satyrn_evals.cell import cell_environment
    from satyrn_evals.cli import main

    first = export_engine(_engine_repo(), "HEAD", root=cell_scratch)
    assert export_engine(_engine_repo(), "HEAD", root=cell_scratch) == first
    environment = cell_environment(parent=cell_scratch)
    environment.pop("UV_PROJECT_ENVIRONMENT")  # as `attempt_engine.as_cell` does
    ran = run_as_cell(
        ["uv", "run", "--no-sync", "--project", os.fspath(first), "satyrn-engine", "--help"],
        cwd=first, environment=environment,
    )
    assert ran.returncode == 0 and "derive" in ran.stdout, ran.stderr
    assert main(["cell-engine", "--engine-repo", os.fspath(_engine_repo()), "--commit", "not-a-commit"]) == 2
```

- [ ] **Step 2: Run to verify failure.** `uv run pytest tests/test_attempt_pi.py tests/test_attempt_engine.py -q` → collection errors: `ImportError: cannot import name 'pi_command'` and `cannot import name 'CHECKOUT_LOG_NAME'`. `uv run pytest -m integration -q tests/integration/test_isolated_arms.py` → `ModuleNotFoundError: No module named 'satyrn_evals.cell_engine'`.

- [ ] **Step 3: Implement.** `src/satyrn_evals/cell_engine.py`:

```python
"""The engine the cell user runs: an export of one engine commit under the cells root.

The Engine arm's ``derive`` and ``deliver`` run as the cell user, and the
cell cannot read the maintainer's engine checkout (his home is 700). So the
maintainer exports the pinned commit -- ``git archive``, no history -- into
``CELLS_ROOT/engine-<commit>``, syncs its environment offline from his own
uv cache against a Python the cell can execute (Homebrew's, world-readable;
uv's managed Pythons live under his home), and shares it with the group.
The marker file is written last, so a half-made export is never reused.
"""

import io
import os
import subprocess
import tarfile
from pathlib import Path

from satyrn_evals.cell import CELLS_ROOT, grant_maintainer, share_with_cell
from satyrn_evals.errors import UsageError

MARKER = ".satyrn-engine-export"
CELL_PYTHON = Path("/opt/homebrew/bin/python3.14")


class EngineExportError(UsageError):
    """The export could not be made; the message says which step failed."""


def export_path(commit: str, root: Path = CELLS_ROOT) -> Path:
    return root / f"engine-{commit}"


def export_engine(engine_repo: Path, commit: str, *, root: Path = CELLS_ROOT, python: Path = CELL_PYTHON) -> Path:
    """The export directory for ``commit``, made once; an existing complete export is reused."""
    resolved = subprocess.run(
        ["git", "-C", os.fspath(engine_repo), "rev-parse", "--verify", f"{commit}^{{commit}}"],
        capture_output=True, text=True, check=False,
    )
    if resolved.returncode != 0:
        raise EngineExportError(f"{commit} is not a commit in {engine_repo}: {resolved.stderr.strip()}")
    sha = resolved.stdout.strip()
    dest = export_path(sha, root)
    if (dest / MARKER).is_file() and (dest / MARKER).read_text().strip() == sha:
        return dest
    if dest.exists():
        raise EngineExportError(f"{dest} exists without a complete export marker; remove it deliberately")
    archive = subprocess.run(["git", "-C", os.fspath(engine_repo), "archive", "--format=tar", sha], capture_output=True, check=False)
    if archive.returncode != 0:
        raise EngineExportError(f"git archive {sha} failed: {os.fsdecode(archive.stderr).strip()}")
    dest.mkdir()
    if failure := grant_maintainer(dest):
        raise EngineExportError(failure)
    with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tar:
        tar.extractall(dest, filter="data")
    environment = {k: v for k, v in os.environ.items() if k not in ("VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT")}
    synced = subprocess.run(
        ["uv", "sync", "--frozen", "--offline", "--python", os.fspath(python)],
        cwd=dest, env=environment, capture_output=True, text=True, check=False,
    )
    if synced.returncode != 0:
        raise EngineExportError(f"uv sync in {dest} failed: {synced.stderr.strip()}")
    share_with_cell(dest)
    (dest / MARKER).write_text(sha + "\n")
    share_with_cell(dest)
    return dest
```

```diff
diff --git a/src/satyrn_evals/attempt_pi.py b/src/satyrn_evals/attempt_pi.py
index 38423f4..bb66bc8 100644
--- a/src/satyrn_evals/attempt_pi.py
+++ b/src/satyrn_evals/attempt_pi.py
@@ -44,6 +44,7 @@ from dataclasses import dataclass
 from pathlib import Path

 from satyrn_evals.arms import KNOWN_TOOLS
+from satyrn_evals.cell import Isolation, cell_command, isolation_from, model_environment
 from satyrn_evals.errors import UsageError
 from satyrn_evals.session_patch import RESIDUE_EXCLUDES, build_cumulative_patch

@@ -156,6 +157,23 @@ def build_pi_argv(args: AdapterArgs, prompt: str) -> list[str]:
     ]


+def pi_command(args: AdapterArgs, prompt: str, environment: Mapping[str, str], worktree: Path) -> list[str]:
+    """The pi argv, run as the cell user when the harness exported the isolated profile.
+
+    Under isolation Pi sees only the cell environment (`cell.cell_environment`):
+    its own home, PATH, TMPDIR and uv project environment, never the
+    maintainer's. The transcript still reaches the file this adapter opened,
+    through the inherited stdout.
+    """
+    command = build_pi_argv(args, prompt)
+    try:
+        if isolation_from(environment) is Isolation.LOCAL:
+            return command
+        return cell_command(command, cwd=worktree, environment=model_environment(environment))
+    except ValueError as exc:
+        raise AdapterError(str(exc)) from exc
+
+
 def read_prompt(environment: Mapping[str, str]) -> str:
     """The model-visible contract Evals exported, refusing an empty one.

@@ -236,7 +254,7 @@ def main(argv: list[str] | None = None) -> int:
     prompt = read_prompt(os.environ)
     patch_path, transcript_path = read_artifact_paths(os.environ)
     base_sha = read_base_sha(os.environ)
-    command = build_pi_argv(args, prompt)
+    command = pi_command(args, prompt, os.environ, Path.cwd())
     with open(transcript_path, "wb") as transcript:
         completed = subprocess.run(
             command,
```

```diff
diff --git a/src/satyrn_evals/attempt_engine.py b/src/satyrn_evals/attempt_engine.py
index fd53482..18078ec 100644
--- a/src/satyrn_evals/attempt_engine.py
+++ b/src/satyrn_evals/attempt_engine.py
@@ -33,6 +33,7 @@ from pathlib import Path

 from satyrn_evals.attempt_pi import (
     PATCH_ENV,
+    TRANSCRIPT_ENV,
     AdapterError,
     clean_pi_environment,
     harvest_patch,
@@ -40,11 +41,19 @@ from satyrn_evals.attempt_pi import (
     read_base_sha,
     read_prompt,
 )
+from satyrn_evals.cell import (
+    CELLS_ROOT,
+    Isolation,
+    cell_command,
+    isolation_from,
+    model_environment,
+)

 ENGINE_REPO_ENV = "SATYRN_ENGINE_REPO"
 RECEIPT_NAME = "engine-receipt.json"
 DERIVE_LOG_NAME = "engine-derive.txt"
 DELIVER_LOG_NAME = "engine-deliver.txt"
+CHECKOUT_LOG_NAME = "engine-checkout.txt"
 #: The deliver timeout: the spec's attempt-command backstop on this machine.
 #: The harness's own command timeout and budget stop the cell first.
 DELIVER_TIMEOUT_SECONDS = 1800
@@ -92,19 +101,20 @@ def parse_args(args: list[str], environment: Mapping[str, str]) -> EngineArgs:
     return EngineArgs(model=model, engine_repo=Path(engine_repo), uv_bin=uv_bin)


-def _engine(args: EngineArgs) -> list[str]:
-    return [args.uv_bin, "run", "--project", os.fspath(args.engine_repo), "satyrn-engine"]
+def _engine(args: EngineArgs, no_sync: bool) -> list[str]:
+    sync = ["--no-sync"] if no_sync else []
+    return [args.uv_bin, "run", *sync, "--project", os.fspath(args.engine_repo), "satyrn-engine"]


-def derive_argv(args: EngineArgs, worktree: Path, request: str) -> list[str]:
-    return [*_engine(args), "derive", "--repo", os.fspath(worktree), "--", request]
+def derive_argv(args: EngineArgs, worktree: Path, request: str, *, no_sync: bool = False) -> list[str]:
+    return [*_engine(args, no_sync), "derive", "--repo", os.fspath(worktree), "--", request]


-def deliver_argv(args: EngineArgs, worktree: Path, contract: Path) -> list[str]:
+def deliver_argv(args: EngineArgs, worktree: Path, contract: Path, *, no_sync: bool = False) -> list[str]:
     return [
-        *_engine(args), "deliver", "--repo", os.fspath(worktree),
+        *_engine(args, no_sync), "deliver", "--repo", os.fspath(worktree),
         "--timeout", str(DELIVER_TIMEOUT_SECONDS), os.fspath(contract),
-        "--", *_engine(args), "attempt", f"--model={args.model}", "--", os.fspath(contract),
+        "--", *_engine(args, no_sync), "attempt", f"--model={args.model}", "--", os.fspath(contract),
     ]


@@ -142,28 +152,74 @@ def delivery_environment(environment: Mapping[str, str]) -> dict[str, str]:
     return cleaned


+def isolated(args: EngineArgs, environment: Mapping[str, str]) -> bool:
+    """Whether the engine runs as the cell user; refuses an engine the cell cannot read."""
+    try:
+        if isolation_from(environment) is Isolation.LOCAL:
+            return False
+    except ValueError as exc:
+        raise AdapterError(str(exc)) from exc
+    if not args.engine_repo.resolve().is_relative_to(CELLS_ROOT.resolve()):
+        raise AdapterError(
+            f"under isolation the engine must be an export under {CELLS_ROOT} "
+            f"(satyrn-evals cell-engine), not {args.engine_repo}"
+        )
+    return True
+
+
+def as_cell(argv: list[str], args: EngineArgs, environment: Mapping[str, str], worktree: Path) -> list[str]:
+    """An engine call run as the cell user: the transcript path and the engine
+    export are passed through; the model's ``UV_PROJECT_ENVIRONMENT`` is not
+    (Ruling 7 of Phase 2a, unchanged under isolation)."""
+    try:
+        cell = model_environment(
+            environment,
+            {TRANSCRIPT_ENV: environment[TRANSCRIPT_ENV], ENGINE_REPO_ENV: os.fspath(args.engine_repo)},
+        )
+    except (KeyError, ValueError) as exc:
+        raise AdapterError(f"cannot build the cell environment: {exc}") from exc
+    cell.pop("UV_PROJECT_ENVIRONMENT", None)
+    return cell_command(argv, cwd=worktree, environment=cell)
+
+
+def checkout_candidate(commit: str, log: Path) -> int:
+    """Check the candidate out into the Evals worktree; a failure is logged, never raised."""
+    checkout = subprocess.run(["git", "checkout", "-q", "--detach", commit], capture_output=True, text=True, check=False)
+    if checkout.returncode != 0:
+        log.write_text(f"git checkout {commit} exited {checkout.returncode}\n{checkout.stderr}", encoding="utf-8")
+    return checkout.returncode
+
+
 def main(argv: list[str] | None = None) -> int:
     args = parse_args(list(sys.argv[1:] if argv is None else argv), os.environ)
     request = read_prompt(os.environ)
     patch_path, transcript_path = read_artifact_paths(os.environ)
     base_sha = read_base_sha(os.environ)
     worktree = Path.cwd()
+    cell = isolated(args, os.environ)
     environment = delivery_environment(os.environ)
+
+    def command(engine_argv: list[str]) -> list[str]:
+        return as_cell(engine_argv, args, os.environ, worktree) if cell else engine_argv
+
     derived = subprocess.run(
-        derive_argv(args, worktree, request), capture_output=True, text=True, env=environment, check=False
+        command(derive_argv(args, worktree, request, no_sync=cell)),
+        capture_output=True, text=True, env=environment, check=False,
     )
-    (transcript_path.parent / DERIVE_LOG_NAME).write_text(derived.stderr, encoding="utf-8")
+    (patch_path.parent / DERIVE_LOG_NAME).write_text(derived.stderr, encoding="utf-8")
     exit_code = derived.returncode
     if derived.returncode == 0:
-        with (transcript_path.parent / DELIVER_LOG_NAME).open("w", encoding="utf-8") as log:
+        with (patch_path.parent / DELIVER_LOG_NAME).open("w", encoding="utf-8") as log:
             delivered = subprocess.run(
-                deliver_argv(args, worktree, contract_path(derived.stderr)),
+                command(deliver_argv(args, worktree, contract_path(derived.stderr), no_sync=cell)),
                 stdout=subprocess.PIPE, stderr=log, text=True, env=environment, check=False,
             )
-        (transcript_path.parent / RECEIPT_NAME).write_text(delivered.stdout, encoding="utf-8")
+        (patch_path.parent / RECEIPT_NAME).write_text(delivered.stdout, encoding="utf-8")
         exit_code = delivered.returncode
-        if (commit := candidate_commit(delivered.stdout)) is not None:
-            subprocess.run(["git", "checkout", "-q", "--detach", commit], check=True, capture_output=True)
+        if (commit := candidate_commit(delivered.stdout)) is not None and (
+            checkout := checkout_candidate(commit, patch_path.parent / CHECKOUT_LOG_NAME)
+        ):
+            exit_code = checkout
     patch_path.write_text(harvest_patch(worktree, base_sha), encoding="utf-8")
     return exit_code

```

```diff
diff --git a/src/satyrn_evals/cli.py b/src/satyrn_evals/cli.py
index 16cbedf..8900450 100644
--- a/src/satyrn_evals/cli.py
+++ b/src/satyrn_evals/cli.py
@@ -11,6 +11,7 @@ from satyrn_evals.attempt_record import AttemptCode, AttemptOutcome
 from satyrn_evals.budget import AttemptBudget
 from satyrn_evals.capture import capture
 from satyrn_evals.capture_record import CaptureOutcome
+from satyrn_evals.cell_engine import export_engine
 from satyrn_evals.census import build_arg_parser as build_census_parser
 from satyrn_evals.census import run_cli as run_census
 from satyrn_evals.errors import SatyrnError, UsageError
@@ -178,6 +179,9 @@ def main(argv: list[str] | None = None) -> int:
             gate(record, previous_result_committed=previous_result_committed)
             print("launch: record accepted")
             return 0
+        if args.command == "cell-engine":
+            print(export_engine(Path(args.engine_repo), args.commit))
+            return 0
         if args.command == "grade":
             task_dir = resolve_task(args.task, tasks_root=Path(args.tasks_root))
             receipt = grade(task_dir, Path(args.patch), Path(args.receipt))
@@ -228,6 +232,12 @@ grade_p.add_argument(
     help="task root (default: bundled tasks)",
 )

+cell_engine_p = sub.add_parser(
+    "cell-engine", help="export one engine commit under the cells root for the isolated Engine arm"
+)
+cell_engine_p.add_argument("--engine-repo", required=True, help="the maintainer's engine checkout")
+cell_engine_p.add_argument("--commit", required=True, help="the engine commit the arm runs")
+
 capture_p = sub.add_parser(
     "capture", help="turn a fixing commit into a task (winnable by construction)"
 )
```

- [ ] **Step 4: Pass, three times for the teardown rows.** `uv run pytest tests/test_attempt_pi.py tests/test_attempt_engine.py -q` → 60 passed. `for i in 1 2 3; do SATYRN_V4_ENGINE_REPO=/Users/pauleveritt/projects/pauleveritt/satyrn-engine uv run pytest -m integration -q tests/integration/test_isolated_arms.py; echo "EXIT: $?"; done` → 5 passed, EXIT 0, three times. Then Task 1 Step 4's named 2a rows and `tests/integration/test_attempt_pi.py` → EXIT 0, and the same leftover checks (no `satyrn-attempt-*`, `satyrn-test-*` or cell process).

- [ ] **Step 5: Record, gates, commit.**

```bash
uv run python tools/provenance.py new src/satyrn_evals/cell_engine.py tests/integration/test_isolated_arms.py
uv run ruff check --fix; just gates; echo "EXIT: $?"
git add -A && git commit -m "Phase 2b: both arms run against a fake model as satyrn-cell under the budget tripwire; a stopped isolated cell leaves no model running"
```

---

### Task 3: The record's profile and purpose, the invocation cross-check, and the cell preflight

**Files:**
- Create: `src/satyrn_evals/task_tree.py`, `src/satyrn_evals/cell_preflight.py`, `tests/test_cell_preflight.py`, `tests/integration/test_cell_preflight.py`
- Modify: `src/satyrn_evals/run_record.py`, `src/satyrn_evals/run.py`, `src/satyrn_evals/cli.py` (`_record_settings` replaces `_budget`; `launch --preflight`), `src/satyrn_evals/timeline.py`, `scripts/preflight_settings.py`, `tests/test_run_record.py` (`GOOD` gains `isolation`/`purpose`: the only change to an existing row), `tests/test_cli.py` (`_record` gains a real tree digest, the new fields and an adapter command; `test_run_takes_its_budget_from_the_run_record` becomes `test_run_takes_its_budget_and_profile_from_the_run_record` with the adapter command: the only changes to existing rows), `tests/test_preflight_settings.py`, `tests/test_timeline.py`

**Interfaces:**
- Consumes (Task 1): `cell.Isolation`, `CELL_HOME`, `CELL_PATH`, `CELL_USER`, `CELL_PATH_PREFIX_ENV`, `cell_command`, `cell_unavailable_reason`; fixture `cell_scratch`. `hygiene.overlay_digests` (2a).
- Produces: `task_tree.tree_digest(root, *, exclude=()) -> str`, `task_tree.RESIDUE_PARTS`; `run_record.RunRecord.isolation: Isolation`, `.purpose: Purpose`; `run_record.PURPOSES`, `DECIDING_PURPOSES`, `ARM_ADAPTERS`; `gate()` refuses a deciding purpose under the local profile; `run_record.command_model(command) -> str | None`, `command_arm(command) -> str | None`, `check_invocation(record, *, task, task_dir, command) -> None` (RunRecordError); `run.run(..., isolation=Isolation.LOCAL)`; `satyrn-evals attempt|run --run-record` cross-check and take the profile; `satyrn-evals launch --preflight RECORD --arm ARM [--no-hunt] [--tasks-root]` (exit 0 clean, 1 on a problem, 2 on a local record or an arm the record does not name); `cell_preflight.HUNT_NAMES`, `SYSTEM_PREFIXES`, `hunt_names(tasks_root) -> tuple[str, ...]`, `hunt_argv(names, root="/") -> list[str]`, `stale_cell_processes(ps_stdout, cell_uid) -> list[str]`, `preflight_cell(*, pinned_pi, protected, tasks_root=DEFAULT_TASKS_ROOT, hunt_root="/", run=subprocess.run) -> CellPreflight(problems, checked)`; `preflight_settings.read_cell_pi_models(run=subprocess.run) -> dict`, `CELL_PI_MODELS`, `--cell`, provenance key `pi_models`; `timeline.TimelineWriter` default clock `time.monotonic`.

- [ ] **Step 1: Failing tests.**

```diff
diff --git a/tests/test_run_record.py b/tests/test_run_record.py
index cd0ead4..57d92cd 100644
--- a/tests/test_run_record.py
+++ b/tests/test_run_record.py
@@ -4,15 +4,21 @@ from pathlib import Path
 import pytest

 from satyrn_evals.budget import AttemptBudget
+from satyrn_evals.cell import Isolation
 from satyrn_evals.cli import main
 from satyrn_evals.errors import UsageError
+from satyrn_evals.manifest import DEFAULT_TASKS_ROOT
 from satyrn_evals.run_record import (
     RunRecord,
     RunRecordError,
     attempt_budget,
+    check_invocation,
+    command_arm,
+    command_model,
     gate,
     load_run_record,
 )
+from satyrn_evals.task_tree import tree_digest

 GOOD = {
     "version": 1, "task": "agentclinic-repair-misleading-locus", "task_tree_sha256": "a" * 64,
@@ -20,6 +26,7 @@ GOOD = {
     "mode": "attended", "max_minutes": 60,
     "stop_rule": "established infrastructure failure only", "decision_rule": "presence counts; no rate",
     "previous_result": None, "token_budget": 32000, "turn_budget": 48,
+    "isolation": "isolated", "purpose": "admission",
 }


@@ -142,3 +149,89 @@ def test_a_record_without_a_budget_is_refused(tmp_path: Path, field: str) -> Non
 def test_a_non_positive_budget_is_refused(tmp_path: Path, field: str, value: int) -> None:
     with pytest.raises(RunRecordError, match=f"{field} must be a positive integer"):
         load_run_record(_write(tmp_path, **{field: value}))
+
+
+@pytest.mark.parametrize("field", ["isolation", "purpose"])
+def test_a_record_without_a_profile_or_purpose_is_refused(tmp_path: Path, field: str) -> None:
+    body = {k: v for k, v in GOOD.items() if k != field}
+    path = tmp_path / "r.json"
+    path.write_text(json.dumps(body))
+    with pytest.raises(RunRecordError, match=f"missing {field}"):
+        load_run_record(path)
+
+
+def test_an_unknown_profile_is_refused(tmp_path: Path) -> None:
+    with pytest.raises(RunRecordError, match="isolation must be isolated or local"):
+        load_run_record(_write(tmp_path, isolation="docker"))
+
+
+def test_an_unknown_purpose_is_refused(tmp_path: Path) -> None:
+    with pytest.raises(RunRecordError, match="purpose must be one of"):
+        load_run_record(_write(tmp_path, purpose="probe"))
+
+
+@pytest.mark.parametrize("purpose", ["admission", "route-proof", "campaign"])
+def test_a_deciding_record_is_refused_under_the_local_profile(tmp_path: Path, purpose: str) -> None:
+    record = load_run_record(_write(tmp_path, isolation="local", purpose=purpose))
+    with pytest.raises(RunRecordError, match="only under the isolated profile"):
+        gate(record, previous_result_committed=None)
+
+
+@pytest.mark.parametrize("purpose", ["admission", "route-proof", "campaign", "development"])
+def test_every_purpose_passes_the_gate_under_the_isolated_profile(tmp_path: Path, purpose: str) -> None:
+    record = load_run_record(_write(tmp_path, purpose=purpose))
+    assert record.isolation is Isolation.ISOLATED
+    gate(record, previous_result_committed=None)
+
+
+def test_a_local_development_record_passes_the_gate(tmp_path: Path) -> None:
+    record = load_run_record(_write(tmp_path, isolation="local", purpose="development"))
+    assert record.isolation is Isolation.LOCAL
+    gate(record, previous_result_committed=None)
+
+
+def test_launch_check_refuses_a_local_admission_record(tmp_path: Path) -> None:
+    assert main(["launch", "--check", str(_write(tmp_path, isolation="local"))]) == 2
+
+
+TASK = "agentclinic-repair-misleading-locus"
+BASELINE = ["satyrn-evals-attempt-pi", "--model", "omlx/gemma-4-12B-it-MLX-8bit"]
+
+
+def _pinned(tmp_path: Path, **over: object) -> RunRecord:
+    return load_run_record(_write(tmp_path, task_tree_sha256=tree_digest(DEFAULT_TASKS_ROOT / TASK), **over))
+
+
+def test_an_invocation_that_matches_the_record_is_accepted(tmp_path: Path) -> None:
+    check_invocation(_pinned(tmp_path), task=TASK, task_dir=DEFAULT_TASKS_ROOT / TASK, command=BASELINE)
+
+
+def test_an_invocation_for_another_task_is_refused(tmp_path: Path) -> None:
+    with pytest.raises(RunRecordError, match="is for task"):
+        check_invocation(_pinned(tmp_path), task="format_number", task_dir=DEFAULT_TASKS_ROOT / "format_number", command=BASELINE)
+
+
+def test_a_drifted_task_tree_is_refused(tmp_path: Path) -> None:
+    with pytest.raises(RunRecordError, match="task_tree_sha256 drifted"):
+        check_invocation(load_run_record(_write(tmp_path)), task=TASK, task_dir=DEFAULT_TASKS_ROOT / TASK, command=BASELINE)
+
+
+def test_an_invocation_of_another_arm_is_refused(tmp_path: Path) -> None:
+    engine = [".venv/bin/satyrn-evals-attempt-engine", "--model", "omlx/gemma-4-12B-it-MLX-8bit"]
+    with pytest.raises(RunRecordError, match="the command runs engine"):
+        check_invocation(_pinned(tmp_path), task=TASK, task_dir=DEFAULT_TASKS_ROOT / TASK, command=engine)
+
+
+def test_an_invocation_with_another_model_is_refused(tmp_path: Path) -> None:
+    with pytest.raises(RunRecordError, match="--model omlx/other"):
+        check_invocation(
+            _pinned(tmp_path), task=TASK, task_dir=DEFAULT_TASKS_ROOT / TASK,
+            command=["satyrn-evals-attempt-pi", "--model=omlx/other"],
+        )
+
+
+def test_the_command_arm_and_model_are_read_from_either_spelling() -> None:
+    assert command_arm(["/x/python", "-m", "satyrn_evals.attempt_engine"]) == "engine"
+    assert command_arm(["cmd"]) is None
+    assert command_model(["a", "--model=omlx/m"]) == "omlx/m"
+    assert command_model(["a", "--model"]) is None
```

```diff
diff --git a/tests/test_cli.py b/tests/test_cli.py
index 1aa74be..10afe60 100644
--- a/tests/test_cli.py
+++ b/tests/test_cli.py
@@ -6,6 +6,7 @@ import pytest

 from satyrn_evals import cli as cli_module
 from satyrn_evals.budget import AttemptBudget
+from satyrn_evals.cell import Isolation
 from satyrn_evals.cli import (
     main,
     parser,
@@ -14,7 +15,9 @@ from satyrn_evals.cli import (
     split_attempt_argv,
 )
 from satyrn_evals.errors import SatyrnError, UsageError
+from satyrn_evals.manifest import DEFAULT_TASKS_ROOT
 from satyrn_evals.summary import SUMMARY_NAME
+from satyrn_evals.task_tree import tree_digest
 from satyrn_evals.workspace import DEFAULT_TIMEOUT


@@ -320,22 +323,45 @@ def test_run_cli_rung_defaults_to_none() -> None:
     assert parser.parse_args(["run", "task", "--n", "1"]).rung is None


-def _record(tmp_path: Path) -> Path:
+PI = ["satyrn-evals-attempt-pi", "--model", "omlx/Ornith-1.5-9B-MLX-8bit"]
+
+
+def _record(tmp_path: Path, **over: object) -> Path:
     path = tmp_path / "record.json"
     path.write_text(json.dumps({
-        "version": 1, "task": "format_number", "task_tree_sha256": "a" * 64, "arm": "baseline",
-        "model": "omlx/Ornith-1.5-9B-MLX-8bit", "condition": "cold", "n": 4, "mode": "attended",
+        "version": 1, "task": "format_number", "task_tree_sha256": tree_digest(DEFAULT_TASKS_ROOT / "format_number"),
+        "arm": "baseline", "model": "omlx/Ornith-1.5-9B-MLX-8bit", "condition": "cold", "n": 4, "mode": "attended",
         "max_minutes": 60, "stop_rule": "infrastructure only", "decision_rule": "fisher",
         "previous_result": None, "token_budget": 24000, "turn_budget": 36,
+        "isolation": "local", "purpose": "development", **over,
     }))
     return path


-def test_run_takes_its_budget_from_the_run_record(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+def test_run_takes_its_budget_and_profile_from_the_run_record(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
     seen: dict[str, object] = {}
     monkeypatch.setattr(cli_module, "run", lambda **kwargs: seen.update(kwargs))
-    assert main(["run", "format_number", "--n", "1", "--run-record", str(_record(tmp_path)), "--", "cmd"]) == 0
+    assert main(["run", "format_number", "--n", "1", "--run-record", str(_record(tmp_path)), "--", *PI]) == 0
     assert seen["budget"] == AttemptBudget(output_tokens=24000, turns=36)
+    assert seen["isolation"] is Isolation.LOCAL
+
+
+def test_attempt_takes_the_isolated_profile_from_the_run_record(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    seen: dict[str, object] = {}
+
+    def fake_attempt(**kwargs: object) -> object:
+        seen.update(kwargs)
+        raise UsageError("stop here")
+
+    monkeypatch.setattr(cli_module, "attempt", fake_attempt)
+    record = _record(tmp_path, isolation="isolated", purpose="admission")
+    assert main(["attempt", "format_number", "--run-record", str(record), "--", *PI]) == 2
+    assert seen["isolation"] is Isolation.ISOLATED
+
+
+def test_attempt_refuses_a_command_the_record_does_not_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    monkeypatch.setattr(cli_module, "attempt", lambda **kw: pytest.fail("no cell may start"))
+    assert main(["attempt", "format_number", "--run-record", str(_record(tmp_path)), "--", "cmd"]) == 2


 def test_run_without_a_record_has_no_budget(monkeypatch: pytest.MonkeyPatch) -> None:
```

`tests/test_cell_preflight.py`:

```python
"""The isolated sitting's cell preflight, driven by a scripted runner: nothing spawns."""

import json
import pwd
import subprocess
from pathlib import Path

import pytest

from satyrn_evals import cell_preflight
from satyrn_evals import cli as cli_module
from satyrn_evals.cell import CELL_PATH_PREFIX_ENV
from satyrn_evals.cell_preflight import (
    CellPreflight,
    hunt_argv,
    hunt_names,
    preflight_cell,
    stale_cell_processes,
)
from satyrn_evals.cli import main
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT

CELL_UID = 560
REPO = Path(__file__).resolve().parent.parent


def test_the_hunt_names_carry_every_bundled_hidden_suite_but_not_its_helpers() -> None:
    names = hunt_names(DEFAULT_TASKS_ROOT)
    assert {"satyrn_evals", "known-good.patch", "known-broken.patch", "test_acceptance.py"} <= set(names)
    assert "test_phase1_home.py" in names  # agentclinic-complaint-lifecycle's hidden suite
    assert "_seed.py" not in names


def test_the_hunt_is_one_root_anchored_find() -> None:
    assert hunt_argv(["a", "b"]) == ["/usr/bin/find", "/", "-xdev", "(", "-name", "a", "-o", "-name", "b", ")", "-print"]


def test_a_leftover_cell_process_is_stale_and_an_os_agent_is_not() -> None:
    ps = (
        "  101 560 /usr/libexec/lsd\n"
        "  102 560 /System/Library/Frameworks/x\n"
        "  103 560 /usr/bin/find / -name x\n"
        "  104 501 /bin/zsh\n"
    )
    assert stale_cell_processes(ps, CELL_UID) == ["103 /usr/bin/find / -name x"]
    assert stale_cell_processes("  101 560 /usr/libexec/lsd\n", CELL_UID) == []


class _Runner:
    """Answers the preflight's commands from a script; records nothing spawns."""

    def __init__(self, *, sudo: int = 0, ps: str = "", readable: str = "", version: str = "0.85.1\n", hits: str = "") -> None:
        self.sudo, self.ps, self.readable, self.version, self.hits = sudo, ps, readable, version, hits

    def __call__(self, argv: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        text = kwargs.get("text", False)
        if argv[:1] == ["/bin/ps"]:
            out = self.ps
        elif "/usr/bin/true" in argv:
            return subprocess.CompletedProcess(argv, self.sudo, b"", b"sudo: a password is required")
        elif "pi" in argv and "--version" in argv:
            out = self.version
        elif "/usr/bin/find" in argv:
            out = self.hits
        else:
            out = self.readable
        return subprocess.CompletedProcess(argv, 0, out if text else out.encode(), "")


@pytest.fixture(autouse=True)
def _cell_user(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("satyrn_evals.cell.CELLS_ROOT", tmp_path)
    monkeypatch.setattr(pwd, "getpwnam", lambda name: type("P", (), {"pw_uid": CELL_UID})())


def _preflight(runner: _Runner, hunt_root: str | None = "/") -> CellPreflight:
    return preflight_cell(pinned_pi="0.85.1", protected=(REPO,), hunt_root=hunt_root, run=runner)


def test_a_clean_cell_has_no_problems() -> None:
    report = _preflight(_Runner(ps="  101 560 /usr/libexec/lsd\n"))
    assert report.problems == []
    assert report.checked["pi_version"] == "0.85.1"


def test_each_cell_problem_is_named() -> None:
    report = _preflight(
        _Runner(ps="  103 560 /bin/bash -c sleep 9\n", readable=f"{REPO}\n", version="0.84.4\n", hits="/private/tmp/x/known-good.patch\n")
    )
    assert report.problems == [
        "a cell process is still running: 103 /bin/bash -c sleep 9",
        f"the cell can read {REPO}",
        "the cell's pi --version is 0.84.4, the arm pins 0.85.1",
        "the cell can find /private/tmp/x/known-good.patch",
    ]


def test_skipping_the_hunt_runs_no_find() -> None:
    report = _preflight(_Runner(hits="/private/tmp/x/known-good.patch\n"), hunt_root=None)
    assert report.problems == [] and report.checked["hunt_hits"] == []


def test_a_cell_user_that_is_not_set_up_is_the_only_problem() -> None:
    report = _preflight(_Runner(sudo=1))
    assert len(report.problems) == 1 and "a password is required" in report.problems[0]


# --- launch --preflight -------------------------------------------------------

RECORD = {
    "version": 1, "task": "agentclinic-repair-misleading-locus", "task_tree_sha256": "a" * 64,
    "arm": "baseline", "model": "omlx/Ornith-1.5-9B-MLX-8bit", "condition": "cold", "n": 4,
    "mode": "attended", "max_minutes": 60, "stop_rule": "infrastructure", "decision_rule": "fisher",
    "previous_result": None, "token_budget": 32000, "turn_budget": 48,
    "isolation": "isolated", "purpose": "admission",
}
ARM = REPO / "arms" / "baseline-ornith15-9b.json"


def _record(tmp_path: Path, **over: object) -> str:
    path = tmp_path / "record.json"
    path.write_text(json.dumps({**RECORD, **over}))
    return str(path)


def test_preflight_refuses_a_local_record(tmp_path: Path) -> None:
    assert main(["launch", "--preflight", _record(tmp_path, isolation="local", purpose="development"), "--arm", str(ARM)]) == 2


def test_preflight_refuses_an_arm_the_record_does_not_name(tmp_path: Path) -> None:
    assert main(["launch", "--preflight", _record(tmp_path, model="omlx/other"), "--arm", str(ARM)]) == 2


def test_preflight_passes_a_clean_cell_and_prints_the_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    seen: dict[str, object] = {}

    def clean(**kwargs: object) -> CellPreflight:
        seen.update(kwargs)
        return CellPreflight([], {"pi_version": "0.85.1"})

    monkeypatch.setattr(cli_module, "preflight_cell", clean)
    assert main(["launch", "--preflight", _record(tmp_path), "--arm", str(ARM), "--no-hunt"]) == 0
    assert json.loads(capsys.readouterr().out)["problems"] == []
    assert seen["pinned_pi"] == "0.85.1" and seen["hunt_root"] is None


def test_preflight_fails_on_a_cell_problem_or_the_test_path_seam(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli_module, "preflight_cell", lambda **kw: CellPreflight(["the cell can read /x"], {}))
    assert main(["launch", "--preflight", _record(tmp_path), "--arm", str(ARM)]) == 1
    assert "launch preflight FAILED: the cell can read /x" in capsys.readouterr().err
    monkeypatch.setattr(cli_module, "preflight_cell", lambda **kw: CellPreflight([], {}))
    monkeypatch.setenv(CELL_PATH_PREFIX_ENV, "/fake/bin")
    assert main(["launch", "--preflight", _record(tmp_path), "--arm", str(ARM)]) == 1


def test_the_preflight_module_names_its_runner_default() -> None:
    assert cell_preflight.preflight_cell.__kwdefaults__["run"] is subprocess.run
```

```diff
diff --git a/tests/test_preflight_settings.py b/tests/test_preflight_settings.py
index 7103a8c..1873e46 100644
--- a/tests/test_preflight_settings.py
+++ b/tests/test_preflight_settings.py
@@ -625,3 +625,48 @@ def test_every_arm_names_a_settings_checker_that_exists(arm_path: Path) -> None:
     named = arm["settings_verified_by"]
     assert named == "scripts/preflight_settings.py"
     assert (_REPO_ROOT / named).is_file()
+
+
+# --- 2b: the cell user's models.json -----------------------------------------
+
+import subprocess  # noqa: E402
+
+import preflight_settings as preflight_settings_module  # noqa: E402
+from preflight_settings import CELL_PI_MODELS, read_cell_pi_models  # noqa: E402
+
+
+def test_the_cell_models_are_read_as_the_cell_user() -> None:
+    seen: list[list[str]] = []
+
+    def run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
+        seen.append(argv)
+        return subprocess.CompletedProcess(argv, 0, json.dumps(_PI_MODELS), "")
+
+    assert read_cell_pi_models(run) == _PI_MODELS
+    assert seen == [["sudo", "-n", "-H", "-u", "satyrn-cell", "--", "/bin/cat", str(CELL_PI_MODELS)]]
+
+
+def test_unreadable_cell_models_are_an_os_error() -> None:
+    def run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
+        return subprocess.CompletedProcess(argv, 1, "", "sudo: a password is required")
+
+    with pytest.raises(OSError, match="a password is required"):
+        read_cell_pi_models(run)
+
+
+def test_cli_cell_compares_against_the_cell_users_models(
+    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
+) -> None:
+    monkeypatch.setattr(preflight_settings_module, "read_cell_pi_models", lambda: _PI_MODELS)
+    omlx_path = _write(tmp_path / "model_settings.json", _OMLX_SETTINGS)
+    assert main([str(_arm_file(tmp_path)), "--omlx-settings", str(omlx_path), "--cell"]) == 0
+    assert json.loads(capsys.readouterr().out)["pi_models"] == f"satyrn-cell:{CELL_PI_MODELS}"
+
+
+def test_cli_cell_exits_2_when_the_cell_models_cannot_be_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
+    def unreadable() -> dict:
+        raise OSError("cannot read as satyrn-cell")
+
+    monkeypatch.setattr(preflight_settings_module, "read_cell_pi_models", unreadable)
+    omlx_path = _write(tmp_path / "model_settings.json", _OMLX_SETTINGS)
+    assert main([str(_arm_file(tmp_path)), "--omlx-settings", str(omlx_path), "--cell"]) == 2
```

```diff
diff --git a/tests/test_timeline.py b/tests/test_timeline.py
index b18390a..d7db371 100644
--- a/tests/test_timeline.py
+++ b/tests/test_timeline.py
@@ -42,3 +42,11 @@ def test_spans_pair_starts_with_ends_and_keep_unfinished_calls() -> None:
     spans = read_timeline(text)
     assert spans == {"a": ToolSpan("bash", 1.0, None), "b": ToolSpan("read", 2.0, 2.5)}
     assert spans["b"].seconds == 0.5 and spans["a"].seconds is None
+
+
+def test_the_default_clock_is_monotonic(tmp_path: Path) -> None:
+    import time
+
+    from satyrn_evals.timeline import TimelineWriter as Writer
+
+    assert Writer.__init__.__defaults__ == (time.monotonic,)
```

`tests/integration/test_cell_preflight.py`:

```python
"""The cell preflight on this machine: real sudo, a hunt scoped to a scratch directory.

The full root-anchored hunt takes about a minute and is the maintainer's
attended step; here the hunt runs over the test's own scratch directory so a
planted file proves the refusal and its removal proves the silence.
"""

import json
import sys
from pathlib import Path

import pytest

from satyrn_evals.arms import load_arm
from satyrn_evals.cell_preflight import preflight_cell
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from preflight_settings import read_cell_pi_models  # noqa: E402

pytestmark = pytest.mark.integration

REPO = Path(__file__).resolve().parents[2]
PINNED = load_arm(REPO / "arms" / "baseline-ornith15-9b.json").pins.pi


def test_the_cell_cannot_read_the_maintainers_trees_and_runs_the_pinned_pi(cell_scratch: Path) -> None:
    report = preflight_cell(pinned_pi=PINNED, protected=(REPO, DEFAULT_TASKS_ROOT, Path.home()), hunt_root=None)
    assert report.problems == []


def test_a_directory_the_cell_can_read_is_a_problem(cell_scratch: Path) -> None:
    report = preflight_cell(pinned_pi=PINNED, protected=(cell_scratch,), hunt_root=None)
    assert report.problems == [f"the cell can read {cell_scratch}"]


def test_the_hunt_finds_a_planted_answer_key_and_nothing_once_it_is_gone(cell_scratch: Path) -> None:
    planted = cell_scratch / "leak" / "known-good.patch"
    planted.parent.mkdir()
    planted.write_text("diff --git a/x b/x\n")
    planted.chmod(0o664)
    planted.parent.chmod(0o2770)
    report = preflight_cell(pinned_pi=PINNED, protected=(), hunt_root=str(cell_scratch))
    assert report.problems == [f"the cell can find {planted}"]
    planted.unlink()
    assert preflight_cell(pinned_pi=PINNED, protected=(), hunt_root=str(cell_scratch)).problems == []


def test_the_cell_users_pi_models_are_read_as_the_cell(cell_scratch: Path) -> None:
    models = read_cell_pi_models()
    assert "omlx" in models["providers"], json.dumps(models)[:200]
```

- [ ] **Step 2: Run to verify failure.** `uv run pytest -q tests/test_run_record.py tests/test_cli.py tests/test_cell_preflight.py tests/test_preflight_settings.py tests/test_timeline.py` → `Interrupted: 4 errors during collection`: `cannot import name 'check_invocation' from 'satyrn_evals.run_record'`, `No module named 'satyrn_evals.task_tree'`, `cannot import name 'cell_preflight' from 'satyrn_evals'`, `cannot import name 'CELL_PI_MODELS' from 'preflight_settings'`. `uv run pytest -q tests/test_timeline.py` → `1 failed, 2 passed`: `test_the_default_clock_is_monotonic`.

- [ ] **Step 3: Implement.** `src/satyrn_evals/task_tree.py`:

```python
"""The task-tree digest a manifest carries and a run record pins.

One function, two uses. ``tree_digest(task_dir, exclude={"manifest.json"})``
is what a generated manifest records about the files beside it (a manifest
cannot hold its own digest). ``tree_digest(task_dir)`` is what a run record's
``task_tree_sha256`` pins: every file, the manifest included, so a changed
contract, oracle or expected id is drift too. Runtime residue never counts.
"""

import hashlib
from collections.abc import Iterable
from pathlib import Path

RESIDUE_PARTS = frozenset({"__pycache__", ".pytest_cache", ".ruff_cache", ".venv"})


def tree_digest(root: Path, *, exclude: Iterable[str] = ()) -> str:
    """SHA-256 over (root-relative POSIX path, NUL, bytes, NUL) of every file, sorted.

    ``exclude`` names root-relative paths left out. Symbolic links are hashed
    as their target text, never followed.
    """
    skipped = frozenset(exclude)
    digest = hashlib.sha256()
    paths = sorted(
        path
        for path in root.rglob("*")
        if (path.is_file() or path.is_symlink())
        and not RESIDUE_PARTS.intersection(path.relative_to(root).parts)
        and path.relative_to(root).as_posix() not in skipped
    )
    for path in paths:
        relative = path.relative_to(root).as_posix()
        body = str(path.readlink()).encode() if path.is_symlink() else path.read_bytes()
        digest.update(relative.encode() + b"\0" + body + b"\0")
    return digest.hexdigest()
```

`src/satyrn_evals/cell_preflight.py`:

```python
"""Before an isolated sitting: the cell reaches nothing that grades, and nothing of it is left running.

``satyrn-evals launch --preflight RECORD --arm ARM`` runs these as the
maintainer, spawning the cell-side commands through sudo:

- the cell user is set up (`cell.cell_unavailable_reason`);
- no cell process is left over from an earlier cell (system agents the OS
  starts for any user are not cells);
- the cell cannot read the maintainer's checkout, task root or home;
- the cell's own ``pi --version`` is the arm's pin;
- a root-anchored ``find`` run as the cell -- the hunt Ornith ran on
  2026-09-14 -- finds no file named like grader material: ``satyrn_evals``,
  a known-good or known-broken patch, or any bundled hidden-suite file name.

The parsers are pure; `preflight_cell` takes the runner so the default tier
can drive it without spawning.
"""

import os
import pwd
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from satyrn_evals.cell import (
    CELL_HOME,
    CELL_PATH,
    CELL_USER,
    cell_command,
    cell_unavailable_reason,
)
from satyrn_evals.hygiene import overlay_digests
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT

HUNT_NAMES = ("satyrn_evals", "known-good.patch", "known-broken.patch", "test_acceptance.py")
#: Executables the OS runs for every user; a cell never starts these.
SYSTEM_PREFIXES = ("/usr/libexec/", "/usr/sbin/", "/System/", "/Library/Apple/")
HUNT_TIMEOUT = 1800
_READABLE = 'for p in "$@"; do if [ -r "$p" ]; then echo "$p"; fi; done'

type Runner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True, slots=True)
class CellPreflight:
    problems: list[str]
    checked: dict[str, object] = field(default_factory=dict)


def hunt_names(tasks_root: Path = DEFAULT_TASKS_ROOT) -> tuple[str, ...]:
    """The fixed names plus every bundled hidden-suite ``test_*.py`` file name.

    Other overlay files (``_seed.py``, ``_contract.py``) are helpers whose
    names third-party packages also use; hunting them would refuse on noise.
    """
    overlay = {Path(path).name for path in overlay_digests(tasks_root).values()}
    return tuple(sorted({*HUNT_NAMES, *(name for name in overlay if name.startswith("test_"))}))


def hunt_argv(names: Sequence[str], root: str = "/") -> list[str]:
    expression: list[str] = []
    for index, name in enumerate(names):
        expression += [*(["-o"] if index else []), "-name", name]
    return ["/usr/bin/find", root, "-xdev", "(", *expression, ")", "-print"]


def stale_cell_processes(ps_stdout: str, cell_uid: int) -> list[str]:
    """``pid command`` for every cell-owned process that is not an OS agent (``ps -A -o pid=,uid=,command=``)."""
    stale: list[str] = []
    for line in ps_stdout.splitlines():
        parts = line.split(None, 2)
        if len(parts) < 3 or not parts[1].isdigit() or int(parts[1]) != cell_uid:
            continue
        if not parts[2].startswith(SYSTEM_PREFIXES):
            stale.append(f"{parts[0]} {parts[2]}")
    return stale


def _lines(stdout: str) -> list[str]:
    return [line for line in stdout.splitlines() if line.strip()]


def preflight_cell(
    *,
    pinned_pi: str,
    protected: Sequence[Path],
    tasks_root: Path = DEFAULT_TASKS_ROOT,
    hunt_root: str | None = "/",
    run: Runner = subprocess.run,
) -> CellPreflight:
    """Every check; ``hunt_root=None`` skips the hunt (minutes on a real disk)."""
    if (reason := cell_unavailable_reason(run)) is not None:
        return CellPreflight([reason])
    environment = {"HOME": os.fspath(CELL_HOME), "PATH": os.pathsep.join(CELL_PATH)}
    root = Path("/")

    def as_cell(argv: list[str], timeout: float = 60) -> subprocess.CompletedProcess[str]:
        return run(
            cell_command(argv, cwd=root, environment=environment),
            cwd="/", stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=timeout, check=False,
        )

    problems: list[str] = []
    ps = run(["/bin/ps", "-A", "-o", "pid=,uid=,command="], capture_output=True, text=True, check=False, timeout=60)
    stale = stale_cell_processes(ps.stdout, pwd.getpwnam(CELL_USER).pw_uid)
    problems += [f"a cell process is still running: {line}" for line in stale]
    paths = [os.fspath(path) for path in protected]
    problems += [f"the cell can read {path}" for path in _lines(as_cell(["/bin/sh", "-c", _READABLE, "sh", *paths]).stdout)]
    version = as_cell(["pi", "--version"]).stdout.strip()
    if version != pinned_pi:
        problems.append(f"the cell's pi --version is {version or 'missing'}, the arm pins {pinned_pi}")
    names = hunt_names(tasks_root)
    hits: list[str] = []
    if hunt_root is not None:
        hits = _lines(as_cell(hunt_argv(names, hunt_root), timeout=HUNT_TIMEOUT).stdout)
        problems += [f"the cell can find {hit}" for hit in hits]
    checked: dict[str, object] = {
        "cell_user": CELL_USER,
        "pi_version": version,
        "unreadable_checked": paths,
        "hunt_root": hunt_root,
        "hunt_names": list(names),
        "hunt_hits": hits,
        "stale_processes": stale,
    }
    return CellPreflight(problems, checked)
```

```diff
diff --git a/src/satyrn_evals/run_record.py b/src/satyrn_evals/run_record.py
index 38b5177..842717b 100644
--- a/src/satyrn_evals/run_record.py
+++ b/src/satyrn_evals/run_record.py
@@ -8,15 +8,30 @@ is pure; the CLI supplies the one fact that needs git.

 import json
 import re
+from collections.abc import Sequence
 from dataclasses import dataclass
 from pathlib import Path
 from typing import Literal

 from satyrn_evals.budget import AttemptBudget
+from satyrn_evals.cell import Isolation
 from satyrn_evals.errors import UsageError
+from satyrn_evals.task_tree import tree_digest

 type Mode = Literal["attended", "batch"]
 type Condition = Literal["cold", "warm"]
+type Purpose = Literal["admission", "route-proof", "campaign", "development"]
+
+#: Purposes whose cells decide something: the launcher runs them only isolated (Ruling 1).
+DECIDING_PURPOSES = frozenset({"admission", "route-proof", "campaign"})
+PURPOSES = DECIDING_PURPOSES | {"development"}
+#: The adapter each committed arm runs, by module or console-script name.
+ARM_ADAPTERS = {
+    "satyrn_evals.attempt_pi": "baseline",
+    "satyrn-evals-attempt-pi": "baseline",
+    "satyrn_evals.attempt_engine": "engine",
+    "satyrn-evals-attempt-engine": "engine",
+}

 CAPS: dict[str, tuple[int, int]] = {"attended": (8, 60), "batch": (12, 720)}
 _HEX64 = re.compile(r"^[0-9a-f]{64}$")
@@ -43,13 +58,16 @@ class RunRecord:
     # The campaign budget per attempt, spec "Budget, both arms".
     token_budget: int
     turn_budget: int
+    # The launcher profile and what the run is for (Ruling 1).
+    isolation: Isolation
+    purpose: Purpose


 _REQUIRED: dict[str, type | tuple[type, ...]] = {
     "version": int, "task": str, "task_tree_sha256": str, "arm": str, "model": str,
     "condition": str, "n": int, "mode": str, "max_minutes": int,
     "stop_rule": str, "decision_rule": str, "previous_result": (str, type(None)),
-    "token_budget": int, "turn_budget": int,
+    "token_budget": int, "turn_budget": int, "isolation": str, "purpose": str,
 }


@@ -79,7 +97,15 @@ def load_run_record(path: Path) -> RunRecord:
             raise RunRecordError(
                 f"run record {path}: {field} must be a positive integer"
             )
-    return RunRecord(**{k: body[k] for k in _REQUIRED})
+    if body["isolation"] not in {profile.value for profile in Isolation}:
+        raise RunRecordError(f"run record {path}: isolation must be isolated or local")
+    if body["purpose"] not in PURPOSES:
+        raise RunRecordError(
+            f"run record {path}: purpose must be one of {', '.join(sorted(PURPOSES))}"
+        )
+    fields = {k: body[k] for k in _REQUIRED}
+    fields["isolation"] = Isolation(body["isolation"])
+    return RunRecord(**fields)


 def attempt_budget(record: RunRecord) -> AttemptBudget:
@@ -95,3 +121,40 @@ def gate(record: RunRecord, *, previous_result_committed: bool | None) -> None:
             f"record asks n={record.n}, {record.max_minutes} minutes")
     if record.previous_result is not None and previous_result_committed is not True:
         raise RunRecordError(f"previous_result {record.previous_result} is not committed")
+    if record.purpose in DECIDING_PURPOSES and record.isolation is not Isolation.ISOLATED:
+        raise RunRecordError(
+            f"{record.purpose} records run only under the isolated profile; "
+            "the local profile is for development records"
+        )
+
+
+def command_model(command: Sequence[str]) -> str | None:
+    """The value of the command's ``--model`` flag (space or equals form), if any."""
+    for index, token in enumerate(command):
+        if token == "--model" and index + 1 < len(command):
+            return command[index + 1]
+        if token.startswith("--model="):
+            return token.removeprefix("--model=")
+    return None
+
+
+def command_arm(command: Sequence[str]) -> str | None:
+    """The committed arm whose adapter the command runs, if it runs one."""
+    for token in command:
+        if (arm := ARM_ADAPTERS.get(token)) or (arm := ARM_ADAPTERS.get(Path(token).name)):
+            return arm
+    return None
+
+
+def check_invocation(record: RunRecord, *, task: str, task_dir: Path, command: Sequence[str]) -> None:
+    """Refuse an attempt or run whose task, tree, arm or model is not the record's."""
+    if task != record.task:
+        raise RunRecordError(f"the record is for task {record.task}, not {task}")
+    if (actual := tree_digest(task_dir)) != record.task_tree_sha256:
+        raise RunRecordError(
+            f"task_tree_sha256 drifted: the record pins {record.task_tree_sha256}, the tree is {actual}"
+        )
+    if (arm := command_arm(command)) != record.arm:
+        raise RunRecordError(f"the record is for arm {record.arm}; the command runs {arm or 'no known adapter'}")
+    if (model := command_model(command)) != record.model:
+        raise RunRecordError(f"the record is for model {record.model}; the command passes --model {model}")
```

```diff
diff --git a/src/satyrn_evals/run.py b/src/satyrn_evals/run.py
index 503d7ab..e6ae185 100644
--- a/src/satyrn_evals/run.py
+++ b/src/satyrn_evals/run.py
@@ -35,6 +35,7 @@ from types import FrameType

 from satyrn_evals.attempt import DEFAULT_TIMEOUT, attempt, resolve_contract
 from satyrn_evals.budget import AttemptBudget
+from satyrn_evals.cell import Isolation
 from satyrn_evals.deadline import validate_attempt_timeout
 from satyrn_evals.errors import OverlayError, SatyrnError, UsageError
 from satyrn_evals.manifest import load_manifest, resolve_task
@@ -155,6 +156,7 @@ def run(
     max_repeated_calls: int | None = None,
     attempt_timeout: float | None = None,
     budget: AttemptBudget | None = None,
+    isolation: Isolation = Isolation.LOCAL,
 ) -> Summary:
     if n < 1:
         raise UsageError("run requires a positive --n")
@@ -195,6 +197,8 @@ def run(
                     attempt_kwargs["attempt_timeout"] = attempt_timeout
                 if budget is not None:
                     attempt_kwargs["budget"] = budget
+                if isolation is Isolation.ISOLATED:
+                    attempt_kwargs["isolation"] = isolation
                 record = attempt(**attempt_kwargs)  # type: ignore[arg-type]
                 if record.attempt_dir is None:
                     raise RuntimeError(
```

```diff
diff --git a/src/satyrn_evals/cli.py b/src/satyrn_evals/cli.py
index 8900450..1ef09a5 100644
--- a/src/satyrn_evals/cli.py
+++ b/src/satyrn_evals/cli.py
@@ -1,17 +1,22 @@
 """Console entry point: satyrn-evals grade, capture, and attempt."""

 import argparse
+import json
 import math
+import os
 import subprocess
 import sys
 from pathlib import Path

+from satyrn_evals.arms import load_arm
 from satyrn_evals.attempt import attempt
 from satyrn_evals.attempt_record import AttemptCode, AttemptOutcome
 from satyrn_evals.budget import AttemptBudget
 from satyrn_evals.capture import capture
 from satyrn_evals.capture_record import CaptureOutcome
+from satyrn_evals.cell import CELL_PATH_PREFIX_ENV, Isolation
 from satyrn_evals.cell_engine import export_engine
+from satyrn_evals.cell_preflight import preflight_cell
 from satyrn_evals.census import build_arg_parser as build_census_parser
 from satyrn_evals.census import run_cli as run_census
 from satyrn_evals.errors import SatyrnError, UsageError
@@ -19,7 +24,13 @@ from satyrn_evals.grade import grade
 from satyrn_evals.manifest import DEFAULT_TASKS_ROOT, resolve_task
 from satyrn_evals.rescore import regrade_attempt, summarize_output
 from satyrn_evals.run import run
-from satyrn_evals.run_record import attempt_budget, gate, load_run_record
+from satyrn_evals.run_record import (
+    RunRecordError,
+    attempt_budget,
+    check_invocation,
+    gate,
+    load_run_record,
+)
 from satyrn_evals.session import run_session
 from satyrn_evals.session_grader import SessionGrader
 from satyrn_evals.session_manifest import DEFAULT_SESSION_SPEC
@@ -60,9 +71,20 @@ def positive_int(value: str) -> int:
     return number


-def _budget(run_record: str | None) -> AttemptBudget | None:
-    """The attempt budget a run record froze; none without a record."""
-    return None if run_record is None else attempt_budget(load_run_record(Path(run_record)))
+def _record_settings(
+    run_record: str | None, *, task: str, tasks_root: str, command: list[str]
+) -> tuple[AttemptBudget | None, Isolation]:
+    """The budget and profile a run record froze, after checking the invocation is the record's.
+
+    Without a record: no budget, the local profile.
+    """
+    if run_record is None:
+        return None, Isolation.LOCAL
+    record = load_run_record(Path(run_record))
+    check_invocation(
+        record, task=task, task_dir=resolve_task(task, tasks_root=Path(tasks_root)), command=command
+    )
+    return attempt_budget(record), record.isolation


 def split_attempt_argv(argv: list[str]) -> tuple[list[str], list[str]]:
@@ -88,6 +110,9 @@ def main(argv: list[str] | None = None) -> int:
                     "attempt command is required: attempt TASK [flags] -- COMMAND..."
                 )
             args = parser.parse_args(["attempt", *flags])
+            budget, isolation = _record_settings(
+                args.run_record, task=args.task, tasks_root=args.tasks_root, command=command
+            )
             record = attempt(
                 task=args.task,
                 tasks_root=Path(args.tasks_root),
@@ -97,7 +122,8 @@ def main(argv: list[str] | None = None) -> int:
                 attempt_timeout=args.attempt_timeout,
                 max_repeated_calls=args.max_repeated_calls,
                 rung=args.rung,
-                budget=_budget(args.run_record),
+                budget=budget,
+                isolation=isolation,
             )
             if record.code is AttemptCode.GRADE_FAILED:
                 print(f"satyrn-evals: {record.message}", file=sys.stderr)
@@ -117,6 +143,9 @@ def main(argv: list[str] | None = None) -> int:
                     "run command is required: run TASK [flags] -- COMMAND..."
                 )
             args = parser.parse_args(["run", *flags])
+            budget, isolation = _record_settings(
+                args.run_record, task=args.task, tasks_root=args.tasks_root, command=command
+            )
             run(
                 task=args.task,
                 tasks_root=Path(args.tasks_root),
@@ -127,7 +156,8 @@ def main(argv: list[str] | None = None) -> int:
                 attempt_timeout=args.attempt_timeout,
                 max_repeated_calls=args.max_repeated_calls,
                 rung=args.rung,
-                budget=_budget(args.run_record),
+                budget=budget,
+                isolation=isolation,
             )
             return 0
         if argv[:1] == ["session"]:
@@ -163,8 +193,10 @@ def main(argv: list[str] | None = None) -> int:
         if args.command == "census":
             return run_census(args.runs_root, args.json_path)
         if args.command == "launch":
+            if args.preflight is not None:
+                return _launch_preflight(args)
             if args.check is None:
-                print("launch: cells are Phase 2; use --check", file=sys.stderr)
+                print("launch: cells are Phase 2c; use --check or --preflight", file=sys.stderr)
                 return UsageError.exit_code
             record = load_run_record(Path(args.check))
             previous_result_committed = None
@@ -214,6 +246,34 @@ def main(argv: list[str] | None = None) -> int:
         return e.exit_code


+def _launch_preflight(args: argparse.Namespace) -> int:
+    """The isolated sitting's cell checks; the JSON report goes to stdout, each problem to stderr."""
+    record = load_run_record(Path(args.preflight))
+    if record.isolation is not Isolation.ISOLATED:
+        raise RunRecordError(f"launch --preflight checks the cell user; {args.preflight} is a local record")
+    if args.arm is None:
+        raise UsageError("launch --preflight needs --arm ARM.json")
+    arm = load_arm(Path(args.arm))
+    if (arm.arm, arm.model) != (record.arm, record.model):
+        raise RunRecordError(
+            f"arm file {args.arm} is {arm.arm} on {arm.model}; the record is {record.arm} on {record.model}"
+        )
+    tasks_root = Path(args.tasks_root)
+    report = preflight_cell(
+        pinned_pi=arm.pins.pi,
+        protected=(Path.cwd(), tasks_root, Path.home()),
+        tasks_root=tasks_root,
+        hunt_root=None if args.no_hunt else "/",
+    )
+    problems = list(report.problems)
+    if os.environ.get(CELL_PATH_PREFIX_ENV):
+        problems.append(f"{CELL_PATH_PREFIX_ENV} is set; it is a test seam, never a sitting's PATH")
+    print(json.dumps({"record": args.preflight, "arm": args.arm, "problems": problems, **report.checked}, indent=2))
+    for problem in problems:
+        print(f"launch preflight FAILED: {problem}", file=sys.stderr)
+    return 1 if problems else 0
+
+
 parser = argparse.ArgumentParser(
     prog="satyrn-evals",
     description="Offline grading and task capture for development tasks.",
@@ -397,8 +457,14 @@ session_p.add_argument(
 )

 launch_p = sub.add_parser(
-    "launch", help="check a run record's cadence before spending anything (cells are Phase 2)"
+    "launch", help="check a run record, or preflight the cell user for an isolated one (cells are Phase 2c)"
 )
 launch_p.add_argument("--check", default=None, help="run record JSON path to check")
+launch_p.add_argument("--preflight", default=None, help="isolated run record JSON path to preflight the cell for")
+launch_p.add_argument("--arm", default=None, help="arm JSON the preflight pins pi against")
+launch_p.add_argument("--no-hunt", action="store_true", help="skip the root-anchored find (minutes)")
+launch_p.add_argument(
+    "--tasks-root", default=str(DEFAULT_TASKS_ROOT), help="task root (default: bundled tasks)"
+)

 build_census_parser(sub)
```

```diff
diff --git a/src/satyrn_evals/timeline.py b/src/satyrn_evals/timeline.py
index cffd9cf..1a3ff61 100644
--- a/src/satyrn_evals/timeline.py
+++ b/src/satyrn_evals/timeline.py
@@ -3,12 +3,14 @@
 Pi's ``--mode json`` events carry no timestamps, so per-command seconds
 cannot be recovered from a transcript afterwards. The harness already reads
 the transcript as it is written (``workspace._wait_or_trip``); it stamps the
-wall-clock moment it read each ``tool_execution_start`` and
+monotonic-clock moment it read each ``tool_execution_start`` and
 ``tool_execution_end`` line into ``timeline.jsonl`` beside the transcript.
 One writer serves both arms, and nothing the model's tools write is used.

 Resolution is the harness's poll interval (0.25 s): a stamp is when the line
-was read, never earlier than when it was written. Seconds are reported per
+was read, never earlier than when it was written. The clock is monotonic, so
+a wall-clock step (NTP, sleep) never makes a command negative or hours long;
+stamps compare only within one harness process, which is all a span needs. Seconds are reported per
 machine and never compared across machines (spec, "Budget, both arms").
 """

@@ -25,7 +27,7 @@ _EVENTS = {"tool_execution_start": "start", "tool_execution_end": "end"}
 class TimelineWriter:
     """Append one stamped record per tool start or end line fed to it."""

-    def __init__(self, path: Path, clock: Callable[[], float] = time.time) -> None:
+    def __init__(self, path: Path, clock: Callable[[], float] = time.monotonic) -> None:
         self._handle = path.open("a", encoding="utf-8")
         self._clock = clock

```

```diff
diff --git a/scripts/preflight_settings.py b/scripts/preflight_settings.py
index a184d04..fc3340f 100755
--- a/scripts/preflight_settings.py
+++ b/scripts/preflight_settings.py
@@ -34,28 +34,35 @@ deliberately separate rather than merged into one wider one.
 config files say", never "the server actually samples this way" -- that
 would take a live completion, which is a different check's job.

-Deliberately no subprocess: these are file reads.
+File reads, with one exception: ``--cell`` reads the cell user's
+``models.json`` -- the config Pi actually loads under isolation -- through
+``sudo -n -H -u satyrn-cell cat``, because the maintainer cannot open that
+home. The provenance block then names the cell's file as its Pi source.

 Usage::

     scripts/preflight_settings.py arms/baseline-ornith15-9b.json \\
         [--omlx-settings ~/.omlx/model_settings.json] \\
-        [--pi-models ~/.pi/agent/models.json] \\
+        [--pi-models ~/.pi/agent/models.json | --cell] \\
         [--record PATH]
 """

 import argparse
 import hashlib
 import json
+import subprocess
 import sys
+from collections.abc import Callable
 from pathlib import Path

 sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

 from satyrn_evals.arms import ArmError, load_arm  # noqa: E402
+from satyrn_evals.cell import CELL_HOME, CELL_USER  # noqa: E402

 DEFAULT_OMLX_SETTINGS = Path.home() / ".omlx" / "model_settings.json"
 DEFAULT_PI_MODELS = Path.home() / ".pi" / "agent" / "models.json"
+CELL_PI_MODELS = CELL_HOME / ".pi" / "agent" / "models.json"

 # arm field -> oMLX `models[server_model]` field. Checked only where the
 # arm declares the field: an arm that does not pin a setting is not making
@@ -221,6 +228,17 @@ def provenance(arm_path_text: str, omlx: dict | None, pi: dict | None) -> dict:
     }


+def read_cell_pi_models(run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run) -> dict:
+    """The cell user's Pi model config, read as the cell user; OSError when it cannot be."""
+    completed = run(
+        ["sudo", "-n", "-H", "-u", CELL_USER, "--", "/bin/cat", str(CELL_PI_MODELS)],
+        cwd="/", capture_output=True, text=True, check=False, timeout=30,
+    )
+    if completed.returncode != 0:
+        raise OSError(f"cannot read {CELL_PI_MODELS} as {CELL_USER}: {completed.stderr.strip()}")
+    return json.loads(completed.stdout)
+
+
 def _read_json(path: Path) -> dict:
     """Parse `path` as a JSON object; raises on any unreadable input.

@@ -235,7 +253,9 @@ def main(argv: list[str] | None = None) -> int:
     parser = argparse.ArgumentParser()
     parser.add_argument("arm", type=Path)
     parser.add_argument("--omlx-settings", type=Path, default=DEFAULT_OMLX_SETTINGS)
-    parser.add_argument("--pi-models", type=Path, default=DEFAULT_PI_MODELS)
+    sources = parser.add_mutually_exclusive_group()
+    sources.add_argument("--pi-models", type=Path, default=DEFAULT_PI_MODELS)
+    sources.add_argument("--cell", action="store_true", help=f"read {CELL_USER}'s models.json as {CELL_USER}")
     parser.add_argument("--record", type=Path, default=None)
     args = parser.parse_args(argv)

@@ -252,8 +272,8 @@ def main(argv: list[str] | None = None) -> int:
         arm_text = args.arm.read_text(encoding="utf-8")
         arm = json.loads(arm_text)
         omlx_settings = _read_json(args.omlx_settings)
-        pi_models = _read_json(args.pi_models)
-    except (OSError, json.JSONDecodeError, ArmError) as exc:
+        pi_models = read_cell_pi_models() if args.cell else _read_json(args.pi_models)
+    except (OSError, json.JSONDecodeError, subprocess.SubprocessError, ArmError) as exc:
         print(f"preflight_settings: unreadable input: {exc}", file=sys.stderr)
         return 2

@@ -266,6 +286,7 @@ def main(argv: list[str] | None = None) -> int:

     mismatches = compare(inference, omlx, pi)
     record = provenance(arm_text, omlx, pi)
+    record["pi_models"] = f"{CELL_USER}:{CELL_PI_MODELS}" if args.cell else str(args.pi_models)

     payload = json.dumps(record, indent=2, sort_keys=True)
     print(payload)
```

- [ ] **Step 4: Pass, and verify settings provenance against the cell.** `uv run pytest -q tests/test_run_record.py tests/test_cli.py tests/test_cell_preflight.py tests/test_preflight_settings.py tests/test_timeline.py` → 169 passed. `uv run pytest -m integration -q tests/integration/test_cell_preflight.py; echo "EXIT: $?"` → 4 passed. Then the done-when's settings check, a file read and one `sudo cat`, no inference: `uv run python scripts/preflight_settings.py arms/baseline-ornith15-9b.json --cell --record "$SCR/settings-cell.json"; echo "EXIT: $?"` → `preflight_settings ok: 'baseline' settings verified against oMLX and pi config`, EXIT 0, and the record's `pi_models` is `satyrn-cell:/Users/satyrn-cell/.pi/agent/models.json`. A non-zero exit here stops the task: report the mismatch lines verbatim (the cell's `models.json` is the maintainer's to change). Re-run Task 1 Step 4's named 2a rows and `tests/integration/test_isolated_arms.py` → EXIT 0.

- [ ] **Step 5: Record, gates, commit.**

```bash
uv run python tools/provenance.py new src/satyrn_evals/task_tree.py src/satyrn_evals/cell_preflight.py tests/test_cell_preflight.py tests/integration/test_cell_preflight.py
uv run ruff check --fix; just gates; echo "EXIT: $?"
git add -A && git commit -m "Phase 2b: run records carry their launcher profile and purpose; attempt and run refuse a record that is not the invocation's; launch --preflight checks the cell user; the timeline clock is monotonic"
```

---

### Task 4: The self-hosted generator, R1-plan, and four cut tasks

**Files:**
- Create: `tools/cut_task.py`, `tools/task_specs/selfhost-docs-linter.json`, `tools/task_specs/selfhost-guard-prefixes.json`, `tools/task_specs/selfhost-guard-prefixes.plan.md`, `tools/task_specs/selfhost-review-script.json`, `tools/task_specs/selfhost-run-record-gate.json`, `tests/test_cut_task.py`, `tests/integration/test_cut_task.py`; cut by the tool: `src/satyrn_evals/tasks/selfhost-{docs-linter,guard-prefixes,review-script,run-record-gate}/`
- Modify: `tests/test_writable_paths_declaration.py` (`FLEET` gains the four rows)

**Interfaces:**
- Consumes (Task 3): `task_tree.tree_digest`. `attempt.contract_digest` (existing).
- Produces: `tools.cut_task.RUNG = "R1-plan"`, `HIDDEN_STAND_IN`, `EXCLUDED_PREFIXES`, `EXCLUDED_FILES`, `RESIDUE_IGNORES`, `ORACLE`, `PUBLIC_SUITE`, `CutError`, `PlanAnchor`, `TaskSpec`, `load_spec(path) -> TaskSpec`, `excluded(path, hidden) -> bool`, `residue_gitignore(existing) -> str | None`, `plan_section(plan_text, heading) -> str`, `r1_plan_prompt(section, hidden, formats) -> str`, `broken_patch(base_texts, broken) -> str`, `manifest_body(spec, prompt, expected_test_ids, task_tree) -> dict`, `parse_collected(stdout) -> list[str]`, `show`, `archive`, `collect_ids(repo, spec)`, `read_plan`, `cut(spec, repo, tasks_root) -> Path`, `main(argv)` with `cut SPEC…` and `check SPEC…` (`--repo`, `--tasks-root`; exit 0 match, 1 drift, 2 CutError). A cut manifest carries `contracts["R1-plan"]` (= `contract`), `generator`, and `digests: {task_tree, prompt}`.

- [ ] **Step 1: Failing tests.** `tests/test_cut_task.py`:

````python
"""The generator's pure core: spec, exclusions, residue, the R1-plan rung, the broken patch, the manifest."""

import json
from pathlib import Path

import pytest

from satyrn_evals.attempt import contract_digest
from tools.cut_task import (
    HIDDEN_STAND_IN,
    RUNG,
    CutError,
    broken_patch,
    excluded,
    load_spec,
    manifest_body,
    parse_collected,
    plan_section,
    r1_plan_prompt,
    residue_gitignore,
)

SPECS = Path(__file__).resolve().parent.parent / "tools" / "task_specs"
SHA_A, SHA_B = "a" * 40, "b" * 40
SPEC = {
    "name": "t", "base": SHA_A, "good": SHA_B, "files": ["tools/x.py"], "hidden": ["tests/test_x.py"],
    "plan": {"path": "docs/plan.md", "heading": "### Task 1: X", "commit": SHA_A},
    "formats": "", "broken": {"tools/x.py": "def f():\n    return None\n"}, "oracle_env": {},
}
PLAN = """# Plan

### Chunk 1: The x tool

**Files:**
- Create: `tools/x.py`, `tests/test_x.py`

**Interfaces:**
- Consumes: `y()` from Task 0
- Produces: `f() -> int`

- [ ] **Stage 1: Failing test**

```python
def test_f():
    assert f() == 1
```

- [ ] **Stage 2: Run** `uv run pytest tests/test_x.py -q` → FAIL

---

### Chunk 2: Other
"""


def _spec(tmp_path: Path, **over: object) -> Path:
    path = tmp_path / "spec.json"
    path.write_text(json.dumps({**SPEC, **over}))
    return path


def test_a_complete_spec_loads(tmp_path: Path) -> None:
    spec = load_spec(_spec(tmp_path))
    assert (spec.files, spec.hidden, spec.plan.heading) == (("tools/x.py",), ("tests/test_x.py",), "### Task 1: X")


@pytest.mark.parametrize(
    ("over", "message"),
    [
        ({"base": "abc"}, "base must be a full 40-hex commit"),
        ({"extra": 1}, "keys must be exactly"),
        ({"broken": {}}, "broken must name at least one file"),
        ({"broken": {"tools/x.py": "no newline"}}, "must end with a newline"),
        ({"hidden": ["tests/a/test_x.py", "tests/b/test_x.py"]}, "basenames must be distinct"),
        ({"plan": {"path": "p", "heading": "h"}}, "plan must be"),
    ],
)
def test_a_malformed_spec_is_refused(tmp_path: Path, over: dict[str, object], message: str) -> None:
    with pytest.raises(CutError, match=message):
        load_spec(_spec(tmp_path, **over))


def test_every_committed_spec_loads() -> None:
    names = sorted(load_spec(path).name for path in SPECS.glob("*.json"))
    assert names == ["selfhost-docs-linter", "selfhost-guard-prefixes", "selfhost-review-script", "selfhost-run-record-gate"]


@pytest.mark.parametrize(
    "path",
    ["docs/superpowers/plans/p.md", "docs/superpowers/specs/s.md", ".claude/settings.json", ".github/w.yml", "PROVENANCE.md", "tests/test_x.py"],
)
def test_the_answer_bearing_paths_stay_out_of_the_base(path: str) -> None:
    assert excluded(path, ["tests/test_x.py"])


@pytest.mark.parametrize("path", ["docs/lessons.md", "tests/test_other.py", "tools/x.py", "docs/superpowers/research/r.md"])
def test_everything_else_stays_in_the_base(path: str) -> None:
    assert not excluded(path, ["tests/test_x.py"])


def test_a_gitignore_that_ignores_all_residue_is_left_alone() -> None:
    assert residue_gitignore(".venv/\n__pycache__/\n.pytest_cache/\n.ruff_cache/\n") is None


def test_missing_residue_patterns_are_appended_or_written() -> None:
    assert residue_gitignore("node_modules/") == "node_modules/\n.pytest_cache/\n__pycache__/\n.ruff_cache/\n.venv/\n"
    assert residue_gitignore(None) == ".pytest_cache/\n__pycache__/\n.ruff_cache/\n.venv/\n"


def test_the_plan_section_runs_to_the_next_rule_or_heading() -> None:
    section = plan_section(PLAN, "### Chunk 1: The x tool")
    assert section.startswith("### Chunk 1: The x tool") and "Chunk 2" not in section and "---" not in section


def test_a_plan_without_the_heading_is_refused() -> None:
    with pytest.raises(CutError, match="no heading"):
        plan_section(PLAN, "### Chunk 9: Absent")


def test_the_r1_plan_rung_keeps_prose_and_produces_and_drops_code_consumes_and_hidden_names() -> None:
    prompt = r1_plan_prompt(plan_section(PLAN, "### Chunk 1: The x tool"), ["tests/test_x.py"], "`f` returns `1`.")
    assert prompt.startswith("Chunk 1: The x tool\n\nFiles:\n")
    assert "Produces: `f() -> int`" in prompt
    assert "Consumes" not in prompt and "def test_f" not in prompt and "**" not in prompt and "- [ ]" not in prompt
    assert "test_x.py" not in prompt and f"`tools/x.py`, `{HIDDEN_STAND_IN}`" in prompt
    assert prompt.endswith("Message formats the acceptance suite asserts, match them exactly: `f` returns `1`.\n")


def test_the_r1_plan_rung_has_no_formats_paragraph_when_the_suite_asserts_none() -> None:
    assert "Message formats" not in r1_plan_prompt(plan_section(PLAN, "### Chunk 1: The x tool"), ["tests/test_x.py"], "")


def test_a_broken_stub_for_a_new_file_is_a_new_file_patch() -> None:
    patch = broken_patch({"tools/x.py": None}, {"tools/x.py": "def f():\n    return None\n"})
    assert patch == (
        "diff --git a/tools/x.py b/tools/x.py\nnew file mode 100644\n--- /dev/null\n+++ b/tools/x.py\n"
        "@@ -0,0 +1,2 @@\n+def f():\n+    return None\n"
    )


def test_a_broken_stub_for_an_existing_file_is_a_unified_diff() -> None:
    patch = broken_patch({"tools/x.py": "a\nb\n"}, {"tools/x.py": "a\n# stub\nb\n"})
    assert patch.startswith("diff --git a/tools/x.py b/tools/x.py\n--- a/tools/x.py\n+++ b/tools/x.py\n@@ ")
    assert "+# stub\n" in patch


def test_a_broken_stub_identical_to_base_is_refused() -> None:
    with pytest.raises(CutError, match="identical to BASE"):
        broken_patch({"tools/x.py": "a\n"}, {"tools/x.py": "a\n"})


def test_the_manifest_pins_the_rung_the_provenance_and_both_digests(tmp_path: Path) -> None:
    spec = load_spec(_spec(tmp_path, oracle_env={"PYTHONPATH": "src"}))
    body = manifest_body(spec, "prompt\n", ["test_x.py::test_f"], "d" * 64)
    assert body["contract"] == "prompt\n" and body["contracts"] == {RUNG: "prompt\n"}
    assert body["oracle"] == ["env", "PYTHONPATH=src", "python", "-m", "pytest", "-p", "satyrn_evals.oracle_hook"]
    assert body["source_paths"] == ["tools/x.py", "tests"]
    assert body["provenance"] == {"repo": "https://github.com/pauleveritt/satyrn-evals.git", "base_sha": SHA_A, "fix_sha": SHA_B}
    assert body["digests"] == {"task_tree": "d" * 64, "prompt": contract_digest("prompt\n")}


def test_collected_ids_stop_at_the_summary_and_none_is_refused() -> None:
    assert parse_collected("test_x.py::test_f\ntest_x.py::test_g[a]\n\n2 tests collected in 0.01s\n") == [
        "test_x.py::test_f", "test_x.py::test_g[a]"]
    with pytest.raises(CutError, match="collected no tests"):
        parse_collected("\nno tests ran\n")
````

`tests/integration/test_cut_task.py`:

````python
"""The generator against real history: a synthetic repository, and this repository's committed cuts.

Integration tier: git and pytest run as subprocesses. The committed-cut rows
need this repository's own history (a full clone), as the tasks were cut from it.
"""

import json
import subprocess
from pathlib import Path

import pytest

from satyrn_evals.manifest import load_manifest
from satyrn_evals.task_tree import tree_digest
from tools.cut_task import CutError, cut, load_spec, main

pytestmark = pytest.mark.integration

REPO = Path(__file__).resolve().parents[2]
SPECS = sorted((REPO / "tools" / "task_specs").glob("*.json"))
PLAN = """### Chunk 1: The adder

**Files:**
- Create: `calc/add.py`, `tests/test_add.py`

**Interfaces:**
- Produces: `add(a: int, b: int) -> int`

- [ ] **Stage 1: Test**

```python
assert add(1, 2) == 3
```
"""


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


def _commit(repo: Path, files: dict[str, str], message: str) -> str:
    for name, text in files.items():
        (repo / name).parent.mkdir(parents=True, exist_ok=True)
        (repo / name).write_text(text)
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-qm", message)
    return _git(repo, "rev-parse", "HEAD")


def _history(tmp_path: Path) -> tuple[Path, dict[str, object]]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    base = _commit(repo, {
        "calc/__init__.py": "", "docs/superpowers/plans/p.md": PLAN, "PROVENANCE.md": "rows\n",
        "tests/test_add.py": "def test_old():\n    pass\n", "pyproject.toml": "[project]\nname = 'calc'\n",
    }, "base")
    good = _commit(repo, {
        "calc/add.py": "def add(a, b):\n    return a + b\n",
        "tests/test_add.py": "from calc.add import add\n\n\ndef test_add():\n    assert add(1, 2) == 3\n",
    }, "good")
    spec = {
        "name": "calc-add", "base": base, "good": good, "files": ["calc/add.py"], "hidden": ["tests/test_add.py"],
        "plan": {"path": "docs/superpowers/plans/p.md", "heading": "### Chunk 1: The adder", "commit": base},
        "formats": "", "broken": {"calc/add.py": "def add(a, b):\n    return None\n"}, "oracle_env": {},
    }
    return repo, spec


def test_a_cut_task_has_the_generator_shape_and_loads(tmp_path: Path) -> None:
    repo, body = _history(tmp_path)
    (tmp_path / "spec.json").write_text(json.dumps(body))
    task = cut(load_spec(tmp_path / "spec.json"), repo, tmp_path / "tasks")
    assert sorted(p.relative_to(task / "base").as_posix() for p in (task / "base").rglob("*") if p.is_file()) == [
        ".gitignore", "calc/__init__.py", "pyproject.toml"]
    assert (task / "overlay" / "test_add.py").read_text().startswith("from calc.add import add")
    assert "+    return a + b" in (task / "fixtures" / "known-good.patch").read_text()
    manifest = load_manifest(task)
    assert manifest.expected_test_ids == ("test_add.py::test_add",)
    data = json.loads((task / "manifest.json").read_text())
    assert data["digests"]["task_tree"] == tree_digest(task, exclude={"manifest.json"})
    assert "test_add.py" not in manifest.contract and "assert add" not in manifest.contract


def test_cutting_over_an_existing_task_is_refused(tmp_path: Path) -> None:
    repo, body = _history(tmp_path)
    (tmp_path / "spec.json").write_text(json.dumps(body))
    (tmp_path / "tasks" / "calc-add").mkdir(parents=True)
    with pytest.raises(CutError, match="exists"):
        cut(load_spec(tmp_path / "spec.json"), repo, tmp_path / "tasks")


def test_the_same_spec_cuts_the_same_tree_twice(tmp_path: Path) -> None:
    repo, body = _history(tmp_path)
    (tmp_path / "spec.json").write_text(json.dumps(body))
    first = cut(load_spec(tmp_path / "spec.json"), repo, tmp_path / "one")
    second = cut(load_spec(tmp_path / "spec.json"), repo, tmp_path / "two")
    assert tree_digest(first) == tree_digest(second)


@pytest.mark.parametrize("spec", SPECS, ids=lambda p: p.stem)
def test_every_committed_self_hosted_task_matches_a_fresh_cut(spec: Path) -> None:
    assert main(["check", str(spec)]) == 0


def test_a_committed_task_that_drifted_from_its_spec_fails_the_check(tmp_path: Path) -> None:
    repo, body = _history(tmp_path)
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps(body))
    task = cut(load_spec(spec), repo, tmp_path / "tasks")
    args = ["check", str(spec), "--repo", str(repo), "--tasks-root", str(tmp_path / "tasks")]
    assert main(args) == 0
    (task / "base" / "pyproject.toml").write_text("[project]\nname = 'drifted'\n")
    assert main(args) == 1
````

- [ ] **Step 2: Run to verify failure.** `uv run pytest -q tests/test_cut_task.py` → `ModuleNotFoundError: No module named 'tools.cut_task'`.

- [ ] **Step 3: Implement the generator and the specs.** `tools/cut_task.py`:

````python
#!/usr/bin/env python3
"""Cut a self-hosted task from this repository's own history, deterministically.

A task is ``(BASE, GOOD, files, HIDDEN, plan-anchor)``, written down once as a
spec file under ``tools/task_specs/`` (spec, "The self-hosted generator"):

- ``base/`` is ``git archive BASE`` minus plans, specs, ``.claude``,
  ``.github``, ``PROVENANCE.md`` and the HIDDEN files, plus a ``.gitignore``
  line for each runtime residue pattern BASE does not already ignore;
- ``overlay/`` holds HIDDEN at GOOD, flattened to each file's basename (the
  layout the headroom probe's tasks graded with, 635c12b);
- ``fixtures/known-good.patch`` is GOOD's diff restricted to ``files``;
  ``fixtures/known-broken.patch`` replaces the spec's ``broken`` files with
  their stub text (a stub that imports and does nothing, or a no-op edit);
- ``manifest.json`` carries the provenance shas, the task-tree digest (every
  file beside the manifest) and the digest of the ``R1-plan`` prompt.

The R1-plan prompt is the plan task's title, Files, Interfaces minus its
Consumes lines, and the prose of every step with fenced code removed, plus
the literal message formats the hidden suite asserts (the spec's ``formats``
text). HIDDEN paths and basenames are written as "its test module": a
contract that names a grader-only path is refused at load.

The expected test ids are the hidden suite collected at GOOD by this
interpreter's pytest, with the spec's ``oracle_env`` applied.

    uv run python tools/cut_task.py cut tools/task_specs/selfhost-review-script.json
    uv run python tools/cut_task.py check tools/task_specs/selfhost-review-script.json

``check`` cuts again into a temporary directory and exits 1 if the task tree
differs from the committed one. No model and no network; git and pytest run
as subprocesses.
"""

import argparse
import difflib
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from satyrn_evals.attempt import contract_digest
from satyrn_evals.task_tree import tree_digest

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TASKS_ROOT = ROOT / "src" / "satyrn_evals" / "tasks"
RUNG = "R1-plan"
REPO_URL = "https://github.com/pauleveritt/satyrn-evals.git"
EXCLUDED_PREFIXES = ("docs/superpowers/plans/", "docs/superpowers/specs/", ".claude/", ".github/")
EXCLUDED_FILES = frozenset({"PROVENANCE.md"})
RESIDUE_IGNORES = (".pytest_cache/", "__pycache__/", ".ruff_cache/", ".venv/")
HIDDEN_STAND_IN = "its test module"
ORACLE = ("python", "-m", "pytest", "-p", "satyrn_evals.oracle_hook")
PUBLIC_SUITE = ("uv", "run", "pytest", "-q")
_SHA = re.compile(r"\A[0-9a-f]{40}\Z")
_SPEC_KEYS = frozenset({"name", "base", "good", "files", "hidden", "plan", "formats", "broken", "oracle_env"})


class CutError(Exception):
    """The spec is malformed or the history does not hold what it names."""


@dataclass(frozen=True, slots=True)
class PlanAnchor:
    path: str
    heading: str
    commit: str | None


@dataclass(frozen=True, slots=True)
class TaskSpec:
    name: str
    base: str
    good: str
    files: tuple[str, ...]
    hidden: tuple[str, ...]
    plan: PlanAnchor
    formats: str
    broken: dict[str, str]
    oracle_env: dict[str, str]


def _strings(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value or not all(isinstance(v, str) and v for v in value):
        raise CutError(f"{field} must be a non-empty list of strings")
    return tuple(value)


def load_spec(path: Path) -> TaskSpec:
    """Read and validate one spec file; every key is required, no other key is allowed."""
    try:
        body = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CutError(f"spec {path}: {error}") from error
    if not isinstance(body, dict) or set(body) != _SPEC_KEYS:
        raise CutError(f"spec {path}: keys must be exactly {sorted(_SPEC_KEYS)}")
    for field in ("base", "good"):
        if not isinstance(body[field], str) or not _SHA.match(body[field]):
            raise CutError(f"spec {path}: {field} must be a full 40-hex commit")
    plan = body["plan"]
    if (
        not isinstance(plan, dict)
        or set(plan) != {"path", "heading", "commit"}
        or not all(isinstance(plan[k], str) and plan[k] for k in ("path", "heading"))
        or not (plan["commit"] is None or (isinstance(plan["commit"], str) and _SHA.match(plan["commit"])))
    ):
        raise CutError(f"spec {path}: plan must be {{path, heading, commit (40-hex or null)}}")
    for field in ("broken", "oracle_env"):
        value = body[field]
        if not isinstance(value, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in value.items()):
            raise CutError(f"spec {path}: {field} must map strings to strings")
    if not body["broken"]:
        raise CutError(f"spec {path}: broken must name at least one file")
    if any(not text.endswith("\n") for text in body["broken"].values()):
        raise CutError(f"spec {path}: every broken stub must end with a newline")
    if not isinstance(body["formats"], str):
        raise CutError(f"spec {path}: formats must be a string (empty when the suite asserts none)")
    hidden = _strings(body["hidden"], "hidden")
    if len({Path(h).name for h in hidden}) != len(hidden):
        raise CutError(f"spec {path}: hidden basenames must be distinct (the overlay is flattened)")
    return TaskSpec(
        name=body["name"],
        base=body["base"],
        good=body["good"],
        files=_strings(body["files"], "files"),
        hidden=hidden,
        plan=PlanAnchor(plan["path"], plan["heading"], plan["commit"]),
        formats=body["formats"],
        broken=dict(body["broken"]),
        oracle_env=dict(body["oracle_env"]),
    )


def excluded(path: str, hidden: Iterable[str]) -> bool:
    """Whether a BASE path stays out of ``base/``."""
    return path in EXCLUDED_FILES or path in set(hidden) or path.startswith(EXCLUDED_PREFIXES)


def residue_gitignore(existing: str | None) -> str | None:
    """The ``.gitignore`` text with every residue pattern, or None when BASE's already has them."""
    lines = [] if existing is None else existing.splitlines()
    missing = [pattern for pattern in RESIDUE_IGNORES if pattern not in {line.strip() for line in lines}]
    if not missing:
        return None
    prefix = "" if existing is None or existing.endswith("\n") or not existing else "\n"
    return (existing or "") + prefix + "".join(f"{pattern}\n" for pattern in missing)


def plan_section(plan_text: str, heading: str) -> str:
    """The lines from ``heading`` up to the next ``##``/``###`` heading or ``---`` rule."""
    lines = plan_text.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == heading)
    except StopIteration:
        raise CutError(f"plan has no heading {heading!r}") from None
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].startswith(("## ", "### ")) or lines[index].strip() == "---":
            end = index
            break
    return "\n".join(lines[start:end])


def r1_plan_prompt(section: str, hidden: Sequence[str], formats: str) -> str:
    """The R1-plan rung: title, Files, Interfaces → Produces, step prose, message formats."""
    kept: list[str] = []
    in_fence = False
    for line in section.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or line.lstrip().startswith("- Consumes:"):
            continue
        text = line.removeprefix("### ").replace("- [ ] ", "").replace("**", "")
        if kept and not text.strip() and not kept[-1].strip():
            continue
        kept.append(text.rstrip())
    prompt = "\n".join(kept).strip()
    if formats.strip():
        prompt += "\n\nMessage formats the acceptance suite asserts, match them exactly: " + formats.strip()
    for path in sorted(hidden, key=len, reverse=True):
        prompt = prompt.replace(path, HIDDEN_STAND_IN)
    for path in hidden:
        prompt = prompt.replace(Path(path).name, HIDDEN_STAND_IN)
    return prompt + "\n"


def broken_patch(base_texts: Mapping[str, str | None], broken: Mapping[str, str]) -> str:
    """A git-style patch replacing each broken file with its stub (new file when absent at BASE)."""
    chunks: list[str] = []
    for path in sorted(broken):
        old, new = base_texts.get(path), broken[path]
        if old == new:
            raise CutError(f"broken stub for {path} is identical to BASE")
        header = f"diff --git a/{path} b/{path}\n"
        if old is None:
            new_lines = new.splitlines(keepends=True)
            body = f"new file mode 100644\n--- /dev/null\n+++ b/{path}\n@@ -0,0 +1,{len(new_lines)} @@\n"
            chunks.append(header + body + "".join(f"+{line}" for line in new_lines))
        else:
            diff = difflib.unified_diff(
                old.splitlines(keepends=True), new.splitlines(keepends=True), f"a/{path}", f"b/{path}"
            )
            chunks.append(header + "".join(diff))
    return "".join(chunks)


def manifest_body(
    spec: TaskSpec, prompt: str, expected_test_ids: Sequence[str], task_tree: str
) -> dict[str, object]:
    """The manifest a cut task carries, in the bundled tasks' shape."""
    oracle = [*(["env", *(f"{k}={v}" for k, v in sorted(spec.oracle_env.items()))] if spec.oracle_env else []), *ORACLE]
    return {
        "name": spec.name,
        "contract": prompt,
        "contracts": {RUNG: prompt},
        "oracle": oracle,
        "expected_test_ids": list(expected_test_ids),
        "source_paths": [*spec.files, "tests"],
        "public_suite": list(PUBLIC_SUITE),
        "fixtures": {"known_good": "fixtures/known-good.patch", "known_broken": "fixtures/known-broken.patch"},
        "grader_overlay": "overlay",
        "oracle_visibility": "hidden",
        "provenance": {"repo": REPO_URL, "base_sha": spec.base, "fix_sha": spec.good},
        "generator": {
            "tool": "tools/cut_task.py",
            "rung": RUNG,
            "files": list(spec.files),
            "hidden": list(spec.hidden),
            "plan": {"path": spec.plan.path, "heading": spec.plan.heading, "commit": spec.plan.commit},
        },
        "digests": {"task_tree": task_tree, "prompt": contract_digest(prompt)},
    }


def parse_collected(stdout: str) -> list[str]:
    """Test ids from ``pytest --collect-only -q`` output, in collection order."""
    ids: list[str] = []
    for line in stdout.splitlines():
        if not line.strip():
            break
        if "::" in line:
            ids.append(line.strip())
    if not ids:
        raise CutError(f"pytest collected no tests:\n{stdout}")
    return ids


# --- git and pytest ---------------------------------------------------------


def _git(repo: Path, *args: str) -> bytes:
    completed = subprocess.run(["git", "-C", os.fspath(repo), *args], capture_output=True, check=False)
    if completed.returncode != 0:
        raise CutError(f"git {' '.join(args)} failed: {os.fsdecode(completed.stderr).strip()}")
    return completed.stdout


def show(repo: Path, commit: str, path: str) -> str | None:
    """The text of ``path`` at ``commit``, or None when it does not exist there."""
    probe = subprocess.run(
        ["git", "-C", os.fspath(repo), "cat-file", "-e", f"{commit}:{path}"], capture_output=True, check=False
    )
    return None if probe.returncode != 0 else _git(repo, "show", f"{commit}:{path}").decode("utf-8")


def archive(repo: Path, commit: str, dest: Path, keep: Iterable[str] | None = None) -> None:
    """Extract ``git archive commit`` into ``dest``, keeping only paths ``keep`` holds (all when None)."""
    wanted = None if keep is None else set(keep)
    with tarfile.open(fileobj=io.BytesIO(_git(repo, "archive", "--format=tar", commit))) as tar:
        members = [m for m in tar.getmembers() if not m.isdir() and (wanted is None or m.name in wanted)]
        tar.extractall(dest, members=members, filter="data")


def collect_ids(repo: Path, spec: TaskSpec) -> list[str]:
    """The hidden suite's test ids, collected at GOOD with the overlay flattened to the root."""
    with tempfile.TemporaryDirectory(prefix="satyrn-cut-") as scratch:
        root = Path(scratch)
        archive(repo, spec.good, root)
        for hidden in spec.hidden:
            (root / Path(hidden).name).write_bytes((root / hidden).read_bytes())
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider",
             *(Path(h).name for h in spec.hidden)],
            cwd=root, capture_output=True, text=True, check=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", **spec.oracle_env},
        )
        if completed.returncode != 0:
            raise CutError(f"collecting the hidden suite at {spec.good} failed:\n{completed.stdout}{completed.stderr}")
        return parse_collected(completed.stdout)


def read_plan(repo: Path, anchor: PlanAnchor) -> str:
    if anchor.commit is None:
        return (repo / anchor.path).read_text(encoding="utf-8")
    text = show(repo, anchor.commit, anchor.path)
    if text is None:
        raise CutError(f"plan {anchor.path} is absent at {anchor.commit}")
    return text


def cut(spec: TaskSpec, repo: Path, tasks_root: Path) -> Path:
    """Write ``tasks_root/<name>``; refuse to overwrite an existing task."""
    dest = tasks_root / spec.name
    if dest.exists():
        raise CutError(f"{dest} exists; remove it deliberately to cut again")
    listing = _git(repo, "ls-tree", "-r", "--name-only", "-z", spec.base).decode("utf-8").split("\0")
    base_paths = [path for path in listing if path and not excluded(path, spec.hidden)]
    (dest / "base").mkdir(parents=True)
    archive(repo, spec.base, dest / "base", keep=base_paths)
    gitignore = dest / "base" / ".gitignore"
    if (text := residue_gitignore(gitignore.read_text() if gitignore.exists() else None)) is not None:
        gitignore.write_text(text)
    (dest / "overlay").mkdir()
    for hidden in spec.hidden:
        if (body := show(repo, spec.good, hidden)) is None:
            raise CutError(f"hidden file {hidden} is absent at {spec.good}")
        (dest / "overlay" / Path(hidden).name).write_text(body)
    (dest / "fixtures").mkdir()
    (dest / "fixtures" / "known-good.patch").write_bytes(
        _git(repo, "diff", "--full-index", "--binary", spec.base, spec.good, "--", *spec.files)
    )
    (dest / "fixtures" / "known-broken.patch").write_text(
        broken_patch({path: show(repo, spec.base, path) for path in spec.broken}, spec.broken)
    )
    prompt = r1_plan_prompt(plan_section(read_plan(repo, spec.plan), spec.plan.heading), spec.hidden, spec.formats)
    body = manifest_body(spec, prompt, collect_ids(repo, spec), tree_digest(dest, exclude={"manifest.json"}))
    (dest / "manifest.json").write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n")
    return dest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cut_task.py")
    parser.add_argument("action", choices=("cut", "check"))
    parser.add_argument("specs", nargs="+", type=Path)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--tasks-root", type=Path, default=DEFAULT_TASKS_ROOT)
    args = parser.parse_args(argv)
    try:
        for spec_path in args.specs:
            spec = load_spec(spec_path)
            if args.action == "cut":
                print(cut(spec, args.repo, args.tasks_root))
                continue
            with tempfile.TemporaryDirectory(prefix="satyrn-cut-check-") as scratch:
                fresh = tree_digest(cut(spec, args.repo, Path(scratch)))
            committed = args.tasks_root / spec.name
            if not committed.is_dir() or tree_digest(committed) != fresh:
                print(f"cut_task: {spec.name} differs from a fresh cut", file=sys.stderr)
                return 1
            print(f"cut_task: {spec.name} matches a fresh cut")
    except CutError as error:
        print(f"cut_task: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
````

`tools/task_specs/selfhost-guard-prefixes.plan.md`:

```markdown
<!-- The Phase 0 fix wave that widened the guard's pi lead (4a54743) was dispatched from a review, not from a plan task. This file writes that item in the plan-task shape so tools/cut_task.py can derive its R1-plan rung; the prose is the headroom probe's R1 text for the same task (worktree-selfhost-headroom-probe 635c12b, src/satyrn_evals/tasks/selfhost-guard-prefixes/manifest.json). -->

### Fix wave: guard wrapper prefixes before pi

**Files:**
- Modify: `tools/hooks/guard.py`

**Interfaces:**
- Produces: `decide(tool_name: str, tool_input: dict) -> str | None` (signature unchanged; only the pi-lead regex changes)

`_PI_LEAD = ^[\s(]*pi\b` lets `uv run pi -p hi`, `env K=1 pi -p hi`, `time pi -p hi`, `timeout 60 pi -p hi`, `sudo pi -p hi`, `nohup pi -p hi`, `$(pi -p hi)` and `` `pi -p hi` `` through. `uv run` is this repository's habitual prefix. Widen the lead to accept an optional run of known wrapper tokens before `pi`: `uv run`, `env` (with optional `K=V` assignments), `time`, `timeout <arg>`, `sudo`, `nohup`, and an opening `$(` or backtick. Keep `ls pi -p`, `grep -rn pi docs`, `echo pi`, `pip install -p x`, `pipx -p` allowed. Do not touch the write-protection rules.
```

`tools/task_specs/selfhost-review-script.json`:

```json
{
  "name": "selfhost-review-script",
  "base": "b253c993539c9bca3cb5103bbd5ac159350ae9d3",
  "good": "fdd21615ab15c0337ee9e5c421b764d892e8dfe1",
  "files": [
    "tools/review.py"
  ],
  "hidden": [
    "tests/test_review.py"
  ],
  "plan": {
    "path": "docs/superpowers/plans/2026-09-13-phase-0-restart.md",
    "heading": "### Task 9: The review script's pure core",
    "commit": "73ec17217a38b9730c9d34d47c0a5163d9c421e7"
  },
  "formats": "provider_and_model raises ValueError when the spec has no slash, and the message contains the exact phrase `provider/model`. build_prompt(diff, range_label) returns text that contains range_label, the diff verbatim, and the exact words `Accept` and `itemized`. refuse_if_exists raises FileExistsError only when the path exists. review_path replaces every `/` in the model spec with `-`.",
  "broken": {
    "tools/review.py": "\"\"\"known-broken fixture stub: importable, behaviorally incomplete.\"\"\"\n\nfrom pathlib import Path\n\n\ndef review_path(root: Path, commit_range: str, model: str) -> Path:\n    return root\n\n\ndef refuse_if_exists(path: Path) -> None:\n    return None\n\n\ndef provider_and_model(spec: str) -> tuple[str, str]:\n    return (\"\", \"\")\n\n\ndef build_prompt(diff: str, range_label: str) -> str:\n    return \"\"\n"
  },
  "oracle_env": {}
}
```

`tools/task_specs/selfhost-guard-prefixes.json` (the stub is BASE's `tools/hooks/guard.py` with one comment line after its docstring, the probe's no-op known-broken):

```json
{
  "name": "selfhost-guard-prefixes",
  "base": "3e996a1437485c394f4032c18dc75eb0934a0c9d",
  "good": "4a5474320590ef4b9db5b26f48f175965e58743e",
  "files": [
    "tools/hooks/guard.py"
  ],
  "hidden": [
    "tests/test_hook_guard.py"
  ],
  "plan": {
    "path": "tools/task_specs/selfhost-guard-prefixes.plan.md",
    "heading": "### Fix wave: guard wrapper prefixes before pi",
    "commit": null
  },
  "formats": "",
  "broken": {
    "tools/hooks/guard.py": "\"\"\"PreToolUse guard for Claude Code. Exit 2 blocks the tool call and shows\nthe message; exit 0 allows it. A tripwire for agents, not a sandbox.\n\"\"\"\n# known-broken fixture: wrapper-prefix widening intentionally not applied.\n\nimport json\nimport re\nimport sys\n\n# A command segment boundary: ; & | or a newline. Splitting on these (rather\n# than only searching the whole command) keeps \"pi\" on one line from pulling\n# in a \"-p\" flag that belongs to an unrelated command on the next line.\n_SEGMENT_SPLIT = re.compile(r\"[;&|\\n]\")\n# \"pi\" must LEAD its segment (only whitespace / \"(\" may precede it) \u2014 not\n# merely appear as a bare word anywhere in it \u2014 so \"ls pi -p\" (pi as an\n# argument to ls) and \"grep -rn pi docs\" do not count as a \"pi\" invocation.\n_PI_LEAD = re.compile(r\"^[\\s(]*pi\\b\")\n# The print flag as its own token, anywhere later in the same segment (other\n# flags/args may sit between \"pi\" and it).\n_PRINT_FLAG = re.compile(r\"(?:^|\\s)(?:-p|--print)\\b\")\n\n# A pacing-tool invocation, anchored so it starts a command (start of\n# string, or after whitespace / ; & | ( ) rather than matching a quoted\n# occurrence inside e.g. a commit message.\n_DIRECT_RUN = re.compile(r\"(?:^|[\\s;&|(])satyrn-evals\\s+(?:run|session|attempt)\\s\")\n\n_RESULT_PATHS = re.compile(r\"docs/(?:results|reviews)/\")\n\n# cp/mv/tee/touch put their target in varying argument positions (last for\n# cp/mv, first for tee/touch) \u2014 a shell parser would be needed to find the\n# exact destination, which is out of scope for a tripwire. So: block\n# whenever one of these tokens and a protected path both appear anywhere in\n# the command. This deliberately over-blocks a read like\n# \"cp docs/results/a.md /tmp/\" \u2014 accepted, since missing a write is worse.\n_WRITE_TOKEN = re.compile(r\"\\b(?:tee|cp|mv|touch)\\b\")\n\n# A redirect operator (>, >>, or >|) followed by its target token. The\n# target is checked for a protected path anywhere within it (after\n# stripping surrounding quotes), so \"./docs/results/\u2026\", \"/repo/docs/\u2026\",\n# \"$PWD/docs/\u2026\" and quoted forms are all caught, not just the bare path.\n# This deliberately over-blocks a redirect to an unrelated path that merely\n# contains \"docs/results/\" as a substring (e.g. \"/tmp/docs/results/a.md\") \u2014\n# accepted, for the same reason.\n_REDIRECT_TARGET = re.compile(r\"(?:>>|>\\|?)\\s*(\\S+)\")\n\n\ndef _blocks_pi_print(command: str) -> bool:\n    for segment in _SEGMENT_SPLIT.split(command):\n        if _PI_LEAD.match(segment) and _PRINT_FLAG.search(segment):\n            return True\n    return False\n\n\ndef _writes_into_protected_path(command: str) -> bool:\n    if _WRITE_TOKEN.search(command) and _RESULT_PATHS.search(command):\n        return True\n    for match in _REDIRECT_TARGET.finditer(command):\n        target = match.group(1).strip(\"'\\\"\")\n        if _RESULT_PATHS.search(target):\n            return True\n    return False\n\n\ndef decide(tool_name: str, tool_input: dict) -> str | None:\n    if tool_name == \"Bash\":\n        command = str(tool_input.get(\"command\", \"\"))\n        if _blocks_pi_print(command) and \"tools/review.py\" not in command:\n            return \"blocked: model reviews run only through tools/review.py (one range, one model, one file)\"\n        if _DIRECT_RUN.search(command) and \"satyrn-evals launch\" not in command:\n            return \"blocked: cells run only through `satyrn-evals launch` with a frozen record\"\n        if _writes_into_protected_path(command) \\\n                and \"satyrn-evals launch\" not in command and \"tools/review.py\" not in command:\n            return \"blocked: docs/results and docs/reviews are written only by the launcher and the review script\"\n        return None\n    if tool_name in (\"Write\", \"Edit\", \"MultiEdit\"):\n        path = str(tool_input.get(\"file_path\", \"\"))\n        if _RESULT_PATHS.search(path):\n            return \"blocked: docs/results and docs/reviews are written only by the launcher and the review script\"\n    return None\n\n\ndef main() -> int:\n    try:\n        payload = json.load(sys.stdin)\n    except json.JSONDecodeError:\n        return 0\n    message = decide(str(payload.get(\"tool_name\", \"\")), payload.get(\"tool_input\") or {})\n    if message is None:\n        return 0\n    print(message, file=sys.stderr)\n    return 2\n\n\nif __name__ == \"__main__\":\n    sys.exit(main())\n"
  },
  "oracle_env": {}
}
```

`tools/task_specs/selfhost-docs-linter.json` (formats: the probe's disclosed "Message formats" and skip-list paragraphs; stub: the probe's known-broken module):

```json
{
  "name": "selfhost-docs-linter",
  "base": "73ec17217a38b9730c9d34d47c0a5163d9c421e7",
  "good": "cc9ab53107a8862a84843b1c3030274503d53d0b",
  "files": [
    "tools/lint_docs.py"
  ],
  "hidden": [
    "tests/test_doc_caps.py"
  ],
  "plan": {
    "path": "docs/superpowers/plans/2026-09-13-phase-0-restart.md",
    "heading": "### Task 7: The docs linter, rewritten to the release-one caps",
    "commit": "73ec17217a38b9730c9d34d47c0a5163d9c421e7"
  },
  "formats": "check(root) returns a list of plain strings, one per failure, and its acceptance suite matches these literally, so match them exactly. Every path in a message is relative to root, using `/` as the separator. A line-count failure reads `<path>: <n> lines > <cap>` (`<cap>` is 150 for ROADMAP.md, 120 for a docs/results file, 400 for a spec) -- for example `ROADMAP.md: 151 lines > 150`. A docs/results file with no fenced code block reads `<path>: no fenced recompute block`. Too many files under docs/results/ reads `docs/results: <count> result files > 12`. A directory under docs/ that is not on the permitted list reads `docs/<name>: directory not permitted under docs/`. A line with trailing whitespace reads `<path>:<line number>: trailing whitespace` (1-indexed). A file whose last line is blank reads `<path>: blank line at EOF`. When both apply to the same file, list every trailing-whitespace line, in ascending line-number order, before that file's own blank-line-at-EOF entry. A clean tree returns an empty list, not a falsy placeholder. The trailing-whitespace / blank-EOF check also carries a small, fixed skip list of build/cache/vendor-style directory names (the kind a project's own tooling generates, never hand-authored prose) that never count as documents; whatever the skip list contains, membership must be decided from each file's path relative to the tree root, never from the absolute filesystem path -- a tree that happens to be checked out several directories deep must lint exactly as if it were checked out at the top level.",
  "broken": {
    "tools/lint_docs.py": "\"\"\"known-broken fixture stub: importable, behaviorally incomplete.\"\"\"\n\nimport sys\nfrom pathlib import Path\n\n\ndef check(root: Path) -> list[str]:\n    return None\n\n\ndef main() -> int:\n    return 0\n\n\nif __name__ == \"__main__\":\n    sys.exit(main())\n"
  },
  "oracle_env": {}
}
```

`tools/task_specs/selfhost-run-record-gate.json` (formats and stub from the probe; `PYTHONPATH=src` is the probe's fix-round oracle, `0b2d4b6`):

```json
{
  "name": "selfhost-run-record-gate",
  "base": "cc9ab53107a8862a84843b1c3030274503d53d0b",
  "good": "b253c993539c9bca3cb5103bbd5ac159350ae9d3",
  "files": [
    "src/satyrn_evals/run_record.py",
    "src/satyrn_evals/cli.py"
  ],
  "hidden": [
    "tests/test_run_record.py"
  ],
  "plan": {
    "path": "docs/superpowers/plans/2026-09-13-phase-0-restart.md",
    "heading": "### Task 8: The run-record gate",
    "commit": "73ec17217a38b9730c9d34d47c0a5163d9c421e7"
  },
  "formats": "RunRecordError's text is what its acceptance suite matches, by exact substring in most cases and by these two exact phrases in the strict cases -- match them exactly. When the parsed JSON is not an object (for example it parses to null or to a bare number), the message contains the exact phrase `not a JSON object`. When a required field is present but the wrong Python type for its column above, the message contains the exact phrase `<field> has the wrong type`, with `<field>` replaced by that field's schema name (for example `n has the wrong type` when n is a string instead of an int). When mode is neither attended nor batch, the message contains the exact phrase `mode must be attended or batch`. When stop_rule or decision_rule is empty or all whitespace, the message contains the exact phrase `<field> is empty` (for example `stop_rule is empty`). Every other refusal's message only needs to mention, somewhere, the name of the field or mode it concerns (a missing field names that field; an attended- or batch-cap refusal says \"attended\" or \"batch\"; a bad digest names task_tree_sha256; an uncommitted result names previous_result; a bad condition names condition), and a message about a file that could not be read or parsed should include that file's path. Malformed JSON syntax (not merely the wrong shape) is refused too, with a message including the path.",
  "broken": {
    "src/satyrn_evals/run_record.py": "\"\"\"known-broken fixture stub: importable, behaviorally incomplete.\"\"\"\n\nfrom dataclasses import dataclass\nfrom pathlib import Path\n\nfrom satyrn_evals.errors import UsageError\n\n\nclass RunRecordError(UsageError):\n    \"\"\"Stub: not yet implemented.\"\"\"\n\n\n@dataclass(frozen=True, slots=True)\nclass RunRecord:\n    version: int | None = None\n    task: str | None = None\n    task_tree_sha256: str | None = None\n    arm: str | None = None\n    model: str | None = None\n    condition: str | None = None\n    n: int | None = None\n    mode: str | None = None\n    max_minutes: int | None = None\n    stop_rule: str | None = None\n    decision_rule: str | None = None\n    previous_result: str | None = None\n\n\ndef load_run_record(path: Path) -> None:\n    return None\n\n\ndef gate(record: RunRecord, *, previous_result_committed: bool | None) -> None:\n    return None\n"
  },
  "oracle_env": {
    "PYTHONPATH": "src"
  }
}
```

- [ ] **Step 4: Cut, pin the fleet table, pass.** `uv run python tools/cut_task.py cut tools/task_specs/selfhost-docs-linter.json tools/task_specs/selfhost-guard-prefixes.json tools/task_specs/selfhost-review-script.json tools/task_specs/selfhost-run-record-gate.json; echo "EXIT: $?"` → four paths, EXIT 0. Check each cut against the probe it reproduces (no model; read-only git): `for t in selfhost-guard-prefixes selfhost-docs-linter selfhost-run-record-gate; do mkdir -p "$SCR/probe/$t" && git archive worktree-selfhost-headroom-probe src/satyrn_evals/tasks/$t | tar -x -C "$SCR/probe/$t" --strip-components=4 && diff -r "$SCR/probe/$t/base" src/satyrn_evals/tasks/$t/base && diff -r "$SCR/probe/$t/overlay" src/satyrn_evals/tasks/$t/overlay && echo "$t identical"; done; rm -rf "$SCR/probe"` → three "identical" lines (the removal matters: those trees hold hidden suites). Then:

```diff
diff --git a/tests/test_writable_paths_declaration.py b/tests/test_writable_paths_declaration.py
index 59c4e84..d8123e5 100644
--- a/tests/test_writable_paths_declaration.py
+++ b/tests/test_writable_paths_declaration.py
@@ -35,6 +35,10 @@ FLEET: dict[str, tuple[str, ...]] = {
         "tests/*",
     ),
     "format_number": ("solution.py",),
+    "selfhost-docs-linter": ("tools/lint_docs.py", "tests/*"),
+    "selfhost-guard-prefixes": ("tools/hooks/guard.py", "tests/*"),
+    "selfhost-review-script": ("tools/review.py", "tests/*"),
+    "selfhost-run-record-gate": ("src/satyrn_evals/run_record.py", "src/satyrn_evals/cli.py", "tests/*"),
 }


```

`uv run pytest -q tests/test_cut_task.py tests/test_writable_paths_declaration.py` → 44 passed. `uv run pytest -m integration -q tests/integration/test_cut_task.py; echo "EXIT: $?"` → 8 passed.

- [ ] **Step 5: Record, gates, commit.** The cut trees are generated; they get "created in release-one" rows, and their manifests carry the provenance shas.

```bash
uv run python tools/provenance.py new tools/cut_task.py tools/task_specs/*.json tools/task_specs/selfhost-guard-prefixes.plan.md tests/test_cut_task.py tests/integration/test_cut_task.py
uv run python tools/provenance.py new $(uv run python tools/provenance.py check | sed 's/^no provenance: //' | grep '^src/satyrn_evals/tasks/selfhost-')
uv run python tools/provenance.py check; echo "EXIT: $?"
uv run ruff check --fix; just gates; echo "EXIT: $?"
git add -A && git commit -m "Phase 2b: tools/cut_task.py cuts self-hosted tasks with the R1-plan rung; run-record-gate, guard-prefixes, review-script and docs-linter are cut"
```

---

### Task 5: The AgentClinic candidates and offline qualification

**Files:**
- Create: `src/satyrn_evals/qualify.py`, `src/satyrn_evals/qualify_fake_pi.py`, `tests/test_qualify.py`, `tests/integration/test_qualify.py`; imported: `src/satyrn_evals/tasks/agentclinic-repair-depth-3/`, `src/satyrn_evals/tasks/agentclinic-repair-depth-2/`
- Modify: `src/satyrn_evals/cli.py` (`qualify`), `tests/test_writable_paths_declaration.py` (`FLEET` gains two rows)

**Interfaces:**
- Consumes: `attempt.attempt`, `grade.grade`, `manifest.load_manifest`, `patch.parse_patch_paths` (existing); the four Task 4 tasks.
- Produces: `qualify.GOOD_RUNS = 3`, `CEILING_CANDIDATES: dict[str, str]` (task → rung), `FLOOR_CANDIDATES`, `Check(name, passed, detail)` with `.line(task)`, `judge_fixture(name, receipt, *, expect, expected_ids) -> Check`, `judge_harvest(code, verdict, patch_text, known_good) -> Check`, `qualify(task_dir, *, scratch=None) -> list[Check]` (names `known-good run 1..3`, `known-broken`, `live-harvest`); `qualify_fake_pi.PATCH_ENV = "SATYRN_QUALIFY_PATCH"`, `committed_paths(paths, existing) -> list[str]`; `satyrn-evals qualify TASK… [--tasks-root]` (exit 0 when every check passes, else 1).

- [ ] **Step 1: Import the two AgentClinic tasks** (byte-identical, Ruling 14):

```bash
for t in agentclinic-repair-depth-3 agentclinic-repair-depth-2; do git archive worktree-ornith-ceiling-probe src/satyrn_evals/tasks/$t | tar -x; done
git status --short src/satyrn_evals/tasks | wc -l   # 2 new directories
```

```diff
diff --git a/tests/test_writable_paths_declaration.py b/tests/test_writable_paths_declaration.py
index d8123e5..2451b63 100644
--- a/tests/test_writable_paths_declaration.py
+++ b/tests/test_writable_paths_declaration.py
@@ -34,6 +34,8 @@ FLEET: dict[str, tuple[str, ...]] = {
         "templates/*",
         "tests/*",
     ),
+    "agentclinic-repair-depth-2": ("app.py", "models.py", "templates/*", "tests/*"),
+    "agentclinic-repair-depth-3": ("app.py", "models.py", "templates/*", "tests/*"),
     "format_number": ("solution.py",),
     "selfhost-docs-linter": ("tools/lint_docs.py", "tests/*"),
     "selfhost-guard-prefixes": ("tools/hooks/guard.py", "tests/*"),
```

- [ ] **Step 2: Failing tests.** `tests/test_qualify.py`:

```python
"""Offline qualification's pure judgements and the candidate list."""

import pytest

from satyrn_evals.attempt_record import AttemptCode
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT, load_manifest
from satyrn_evals.qualify import (
    CEILING_CANDIDATES,
    FLOOR_CANDIDATES,
    judge_fixture,
    judge_harvest,
)
from satyrn_evals.qualify_fake_pi import committed_paths
from satyrn_evals.receipt import Receipt
from satyrn_evals.verdict import Verdict

IDS = ("t.py::a", "t.py::b")
GOOD_PATCH = "diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-a\n+b\n"


def _receipt(verdict: Verdict, *, executed: tuple[str, ...] = IDS, errors: int = 0, evidence: bool = True) -> Receipt:
    data = {"executed_test_ids": list(executed), "outcomes": {}, "counts": {"passed": 0, "failed": 0, "error": errors, "skipped": 0}}
    return Receipt("t", "d" * 64, verdict, "", data if evidence else None)  # type: ignore[arg-type]


def test_known_good_qualifies_when_it_passes_every_expected_test_without_errors() -> None:
    assert judge_fixture("known-good", _receipt(Verdict.PASS), expect=Verdict.PASS, expected_ids=IDS).passed


@pytest.mark.parametrize(
    "receipt",
    [_receipt(Verdict.PASS, errors=1), _receipt(Verdict.PASS, executed=IDS[:1]), _receipt(Verdict.FAIL), _receipt(Verdict.UNAVAILABLE, evidence=False)],
)
def test_known_good_does_not_qualify_otherwise(receipt: Receipt) -> None:
    assert not judge_fixture("known-good", receipt, expect=Verdict.PASS, expected_ids=IDS).passed


def test_known_broken_qualifies_when_it_fails_on_behaviour() -> None:
    assert judge_fixture("known-broken", _receipt(Verdict.FAIL), expect=Verdict.FAIL, expected_ids=IDS).passed


@pytest.mark.parametrize("receipt", [_receipt(Verdict.FAIL, errors=2), _receipt(Verdict.PASS)])
def test_known_broken_does_not_qualify_when_it_errors_or_passes(receipt: Receipt) -> None:
    assert not judge_fixture("known-broken", receipt, expect=Verdict.FAIL, expected_ids=IDS).passed


def test_a_whole_graded_harvest_qualifies() -> None:
    assert judge_harvest(AttemptCode.OK, Verdict.PASS, GOOD_PATCH, GOOD_PATCH).passed


@pytest.mark.parametrize(
    ("code", "verdict", "patch"),
    [(AttemptCode.NO_PATCH, None, None), (AttemptCode.OK, Verdict.FAIL, GOOD_PATCH), (AttemptCode.OK, Verdict.PASS, GOOD_PATCH.replace("x.py", "y.py"))],
)
def test_a_partial_or_failing_harvest_does_not_qualify(code: AttemptCode, verdict: Verdict | None, patch: str | None) -> None:
    assert not judge_harvest(code, verdict, patch, GOOD_PATCH).passed


def test_the_fake_commits_half_of_several_files_and_a_lone_file_only_when_it_existed() -> None:
    assert committed_paths(["c", "a", "b"], set()) == ["a"]
    assert committed_paths(["b", "a"], set()) == ["a"]
    assert committed_paths(["a"], {"a"}) == ["a"]
    assert committed_paths(["a"], set()) == []


@pytest.mark.parametrize(("name", "rung"), [*CEILING_CANDIDATES.items(), *FLOOR_CANDIDATES.items()])
def test_every_candidate_is_bundled_hidden_and_carries_its_rung(name: str, rung: str) -> None:
    manifest = load_manifest(DEFAULT_TASKS_ROOT / name)
    assert manifest.oracle_visibility == "hidden"
    assert rung in manifest.contracts
```

`tests/integration/test_qualify.py`:

```python
"""Offline qualification with the real grader, adapter and harness; no model.

Roadmap row 2b: "every candidate passes offline qualification". Nothing is
copied out of a bundled hidden task: the refusal row uses the visible
``calc-build`` fixture task.
"""

import shutil
from pathlib import Path

import pytest

from satyrn_evals.cli import main
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT
from satyrn_evals.qualify import CEILING_CANDIDATES, FLOOR_CANDIDATES, qualify

pytestmark = pytest.mark.integration

FIXTURE_TASKS = Path(__file__).parent / "data" / "tasks"


@pytest.mark.parametrize("name", [*CEILING_CANDIDATES, *FLOOR_CANDIDATES])
def test_every_candidate_qualifies_offline(name: str) -> None:
    checks = qualify(DEFAULT_TASKS_ROOT / name)
    assert [check.name for check in checks] == ["known-good run 1", "known-good run 2", "known-good run 3", "known-broken", "live-harvest"]
    assert all(check.passed for check in checks), "\n".join(check.line(name) for check in checks)


def test_a_task_whose_known_broken_fixture_passes_does_not_qualify(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "calc-build"
    shutil.copytree(FIXTURE_TASKS / "calc-build", task)
    shutil.copyfile(task / "fixtures" / "known-good.patch", task / "fixtures" / "known-broken.patch")
    failed = [check.name for check in qualify(task) if not check.passed]
    assert failed == ["known-broken"]


def test_the_qualify_command_exits_zero_for_a_qualifying_task(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["qualify", "calc-build", "--tasks-root", str(FIXTURE_TASKS)]) == 0
    assert capsys.readouterr().out.count(" ok: ") == 5
```

- [ ] **Step 3: Run to verify failure.** `uv run pytest -q tests/test_qualify.py tests/test_writable_paths_declaration.py` → `ModuleNotFoundError: No module named 'satyrn_evals.qualify'` (the fleet table already passes with the imports in place).

- [ ] **Step 4: Implement.** `src/satyrn_evals/qualify_fake_pi.py`:

```python
"""The qualification's fake ``pi``: apply the task's known-good patch, commit part of it.

No model. It runs in the attempt worktree, applies ``SATYRN_QUALIFY_PATCH``
with ``git apply``, then commits some of the touched files and leaves the
rest uncommitted -- the shapes that scored ``NO_PATCH`` under
``git diff HEAD`` (spec, "What the evidence settled"). With two or more
files it commits the first half, sorted; with one file it commits it when
BASE already had it and leaves it untracked when it is new. It writes a
Pi-shaped ``--mode json`` stream so the harness's tail has something to read.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from satyrn_evals.patch import parse_patch_paths

PATCH_ENV = "SATYRN_QUALIFY_PATCH"


def committed_paths(paths: list[str], existing: set[str]) -> list[str]:
    """Which touched paths the fake commits; the rest stay uncommitted."""
    ordered = sorted(paths)
    if len(ordered) >= 2:
        return ordered[: len(ordered) // 2]
    return [path for path in ordered if path in existing]


def _emit(event: dict) -> None:
    print(json.dumps(event), flush=True)


def main() -> int:
    patch_text = Path(os.environ[PATCH_ENV]).read_text(encoding="utf-8")
    paths = list(parse_patch_paths(patch_text))
    existing = {path for path in paths if Path(path).exists()}
    _emit({"type": "session", "version": 3, "cwd": os.getcwd()})
    _emit({"type": "agent_start"})
    _emit({"type": "turn_start"})
    subprocess.run(["git", "apply", "-"], input=patch_text.encode("utf-8"), check=True, capture_output=True)
    if commit := committed_paths(paths, existing):
        subprocess.run(["git", "add", "--", *commit], check=True, capture_output=True)
        subprocess.run(
            ["git", "-c", "user.name=qualify", "-c", "user.email=qualify@example.invalid", "commit", "-qm", "qualify"],
            check=True, capture_output=True,
        )
    _emit({"type": "message_end", "message": {"role": "assistant", "usage": {"input": 1000, "output": 10}}})
    _emit({"type": "turn_end", "message": {"role": "assistant", "content": [{"type": "text", "text": "done"}]}})
    _emit({"type": "agent_end"})
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

`src/satyrn_evals/qualify.py`:

```python
"""Offline qualification: a task earns a cell only by passing these, with no model.

The spec's three checks ("The self-hosted generator"), applied to every
candidate whatever its source:

1. ``grade`` passes known-good with every expected test executed and fails
   known-broken, both with zero collection errors;
2. a fake attempt that applies known-good, commits part of it and leaves the
   rest uncommitted (`qualify_fake_pi`) goes through the real Baseline
   adapter and harness, is harvested whole -- the same paths as known-good --
   and grades pass;
3. the hidden suite passes GOOD (known-good) three times running.

`judge_fixture` and `judge_harvest` are pure; `qualify` runs the grades and
the attempt, so it spawns and belongs to the integration tier.
"""

import os
import shutil
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from satyrn_evals.attempt import attempt
from satyrn_evals.attempt_record import AttemptCode
from satyrn_evals.grade import grade
from satyrn_evals.manifest import load_manifest
from satyrn_evals.patch import parse_patch_paths
from satyrn_evals.qualify_fake_pi import PATCH_ENV
from satyrn_evals.receipt import Receipt
from satyrn_evals.verdict import Verdict

GOOD_RUNS = 3
#: The spec's candidates ("Workloads"), each with the rung it runs at.
CEILING_CANDIDATES: dict[str, str] = {
    "agentclinic-repair-depth-3": "R1",
    "selfhost-run-record-gate": "R1-plan",
    "selfhost-guard-prefixes": "R1-plan",
    "selfhost-review-script": "R1-plan",
}
FLOOR_CANDIDATES: dict[str, str] = {
    "agentclinic-repair-depth-2": "R1",
    "selfhost-docs-linter": "R1-plan",
}


@dataclass(frozen=True, slots=True)
class Check:
    name: str
    passed: bool
    detail: str

    def line(self, task: str) -> str:
        return f"qualify {task}: {self.name} {'ok' if self.passed else 'FAILED'}: {self.detail}"


def judge_fixture(name: str, receipt: Receipt, *, expect: Verdict, expected_ids: tuple[str, ...]) -> Check:
    """One fixture grade against its expectation; collection errors always fail."""
    evidence = receipt.evidence
    if evidence is None:
        return Check(name, False, f"verdict {receipt.verdict} with no oracle evidence: {receipt.reason}")
    errors = evidence.get("counts", {}).get("error", 0) + len(evidence.get("collect_errors", []))
    executed = len(evidence["executed_test_ids"])
    detail = f"verdict {receipt.verdict}, executed {executed} of {len(expected_ids)}, errors {errors}"
    passed = receipt.verdict is expect and errors == 0
    if expect is Verdict.PASS:
        passed = passed and set(evidence["executed_test_ids"]) >= set(expected_ids)
    return Check(name, passed, detail)


def judge_harvest(code: AttemptCode, verdict: Verdict | None, patch_text: str | None, known_good: str) -> Check:
    """The live harvest: whole (the known-good paths) and graded pass."""
    want = sorted(parse_patch_paths(known_good))
    got = sorted(parse_patch_paths(patch_text)) if patch_text else []
    detail = f"code {code}, verdict {verdict}, paths {got} (known-good {want})"
    passed = code is AttemptCode.OK and verdict is Verdict.PASS and got == want
    return Check("live-harvest", passed, detail)


@contextmanager
def _fake_pi_on_path(scratch: Path, patch: Path) -> Iterator[None]:
    bin_dir = scratch / "bin"
    bin_dir.mkdir()
    shim = bin_dir / "pi"
    shim.write_text(f'#!/bin/sh\nexec {sys.executable} -m satyrn_evals.qualify_fake_pi "$@"\n')
    shim.chmod(0o755)
    saved = {name: os.environ.get(name) for name in ("PATH", PATCH_ENV)}
    os.environ["PATH"] = f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"
    os.environ[PATCH_ENV] = os.fspath(patch)
    try:
        yield
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def qualify(task_dir: Path, *, scratch: Path | None = None) -> list[Check]:
    """Run every check against ``task_dir``; the scratch directory is removed afterwards."""
    manifest = load_manifest(task_dir)
    expected = manifest.expected_test_ids
    good = task_dir / manifest.fixtures["known_good"]
    broken = task_dir / manifest.fixtures["known_broken"]
    root = Path(tempfile.mkdtemp(prefix="satyrn-qualify-", dir=scratch))
    try:
        checks = [
            judge_fixture(
                f"known-good run {run}",
                grade(task_dir, good, root / f"good-{run}.json"),
                expect=Verdict.PASS,
                expected_ids=expected,
            )
            for run in range(1, GOOD_RUNS + 1)
        ]
        checks.append(
            judge_fixture("known-broken", grade(task_dir, broken, root / "broken.json"), expect=Verdict.FAIL, expected_ids=expected)
        )
        with _fake_pi_on_path(root, good):
            record = attempt(
                task=manifest.name,
                tasks_root=task_dir.parent,
                output=root / "attempts",
                command=[sys.executable, "-m", "satyrn_evals.attempt_pi", "--model", "omlx/qualify"],
                timeout=600,
            )
        patch = root / "attempts" / record.attempt_dir / "patch.diff" if record.attempt_dir else None
        patch_text = patch.read_text(encoding="utf-8") if patch is not None and patch.is_file() else None
        checks.append(judge_harvest(record.code, record.verdict, patch_text, good.read_text(encoding="utf-8")))
        return checks
    finally:
        shutil.rmtree(root, ignore_errors=True)
```

```diff
diff --git a/src/satyrn_evals/cli.py b/src/satyrn_evals/cli.py
index 1ef09a5..f5d8516 100644
--- a/src/satyrn_evals/cli.py
+++ b/src/satyrn_evals/cli.py
@@ -22,6 +22,7 @@ from satyrn_evals.census import run_cli as run_census
 from satyrn_evals.errors import SatyrnError, UsageError
 from satyrn_evals.grade import grade
 from satyrn_evals.manifest import DEFAULT_TASKS_ROOT, resolve_task
+from satyrn_evals.qualify import qualify
 from satyrn_evals.rescore import regrade_attempt, summarize_output
 from satyrn_evals.run import run
 from satyrn_evals.run_record import (
@@ -214,6 +215,13 @@ def main(argv: list[str] | None = None) -> int:
         if args.command == "cell-engine":
             print(export_engine(Path(args.engine_repo), args.commit))
             return 0
+        if args.command == "qualify":
+            failed = False
+            for task in args.tasks:
+                for check in qualify(resolve_task(task, tasks_root=Path(args.tasks_root))):
+                    print(check.line(task))
+                    failed = failed or not check.passed
+            return 1 if failed else 0
         if args.command == "grade":
             task_dir = resolve_task(args.task, tasks_root=Path(args.tasks_root))
             receipt = grade(task_dir, Path(args.patch), Path(args.receipt))
@@ -298,6 +306,16 @@ cell_engine_p = sub.add_parser(
 cell_engine_p.add_argument("--engine-repo", required=True, help="the maintainer's engine checkout")
 cell_engine_p.add_argument("--commit", required=True, help="the engine commit the arm runs")

+qualify_p = sub.add_parser(
+    "qualify", help="offline qualification: fixtures both ways, a live harvest, known-good three times"
+)
+qualify_p.add_argument("tasks", nargs="+", help="task names")
+qualify_p.add_argument(
+    "--tasks-root",
+    default=str(DEFAULT_TASKS_ROOT),
+    help="task root (default: bundled tasks)",
+)
+
 capture_p = sub.add_parser(
     "capture", help="turn a fixing commit into a task (winnable by construction)"
 )
```

- [ ] **Step 5: Pass, and qualify every candidate.** `uv run pytest -q tests/test_qualify.py tests/test_writable_paths_declaration.py` → 36 passed. `uv run pytest -m integration -q tests/integration/test_qualify.py; echo "EXIT: $?"` → 8 passed (about 40 s). Then the record for the morning status: `uv run satyrn-evals qualify agentclinic-repair-depth-3 selfhost-run-record-gate selfhost-guard-prefixes selfhost-review-script agentclinic-repair-depth-2 selfhost-docs-linter; echo "EXIT: $?"` → 30 lines ending ` ok: …`, EXIT 0. Keep the output verbatim for Task 6's status.

- [ ] **Step 6: Record, gates, commit.**

```bash
uv run python tools/provenance.py record --sha 4f0ee53c79bab42da4ad3db8d43ec929521010c3 $(find src/satyrn_evals/tasks/agentclinic-repair-depth-3 src/satyrn_evals/tasks/agentclinic-repair-depth-2 -type f | sort)
uv run python tools/provenance.py new src/satyrn_evals/qualify.py src/satyrn_evals/qualify_fake_pi.py tests/test_qualify.py tests/integration/test_qualify.py
uv run ruff check --fix; just gates; echo "EXIT: $?"
git add -A && git commit -m "Phase 2b: depth-3 and depth-2 imported from the ceiling probe; satyrn-evals qualify proves every candidate offline"
```

---

### Task 6: The probe tooling, the roadmap, the isolated preflight, and the maintainer checklist

**Files:**
- Create: `scripts/speed_probe.py`, `tests/test_speed_probe.py`
- Modify: `ROADMAP.md`

**Interfaces:**
- Produces: `speed_probe.CONTEXT_SIZES`, `CONCURRENCY`, `K_THRESHOLD = 1.5`, `SIZE_TOLERANCE`, `Completion`, `parse_line(line) -> Completion | None`, `completions_in(lines, model, start, end)`, `nearest_size(prompt)`, `decode_by_size(completions) -> dict[int, float]`, `total_throughput(completions) -> float`, `choose_k(throughput) -> int`, `analyze(plan, lines) -> dict`, `filler`, `request`, `run(base_url, model, *, streams_seconds, max_tokens, opener)`, `main` (`run`, `analyze`).

- [ ] **Step 1: Failing tests.** `tests/test_speed_probe.py`:

```python
"""The probe's numbers from recorded-format oMLX log lines; the driver against a fake server. No network."""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from speed_probe import (  # noqa: E402
    CONCURRENCY,
    CONTEXT_SIZES,
    analyze,
    choose_k,
    decode_by_size,
    filler,
    main,
    nearest_size,
    parse_line,
    run,
    total_throughput,
)

MODEL = "Ornith-1.5-9B-MLX-8bit"
#: Verbatim from ~/.omlx/logs/server.log, 2026-09-14.
RECORDED = (
    "2026-09-14 09:51:27,151 - omlx.server - INFO - [-] - Chat completion: model=Ornith-1.5-9B-MLX-8bit, "
    "758 tokens in 30.62s (27.3 tok/s), prompt: 44644, finish_reason=stop, max_tokens=32000, request_max_tokens=32000"
)
T0 = 1_800_000_000.0


def _line(ended: float, tokens: int, seconds: float, rate: float, prompt: int, model: str = MODEL) -> str:
    stamp = datetime.fromtimestamp(ended).strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
    return (
        f"{stamp} - omlx.server - INFO - [-] - Chat completion: model={model}, {tokens} tokens in {seconds}s "
        f"({rate} tok/s), prompt: {prompt}, finish_reason=stop, max_tokens=512, request_max_tokens=512"
    )


def test_a_recorded_completion_line_parses() -> None:
    completion = parse_line(RECORDED)
    assert completion is not None
    assert (completion.model, completion.tokens, completion.seconds, completion.rate, completion.prompt) == (MODEL, 758, 30.62, 27.3, 44644)
    assert completion.started == pytest.approx(completion.ended - 30.62)


@pytest.mark.parametrize(
    "line",
    [
        "2026-09-13 02:00:48,606 - omlx.scheduler - INFO - [-] - Cache phase timings: boundary_capture_extract=26.9ms/1294",
        "",
        "Chat completion: model=x, 1 tokens in 1s (1 tok/s), prompt: 1,",
    ],
)
def test_every_other_line_is_not_a_completion(line: str) -> None:
    assert parse_line(line) is None


def test_a_prompt_counts_for_the_nearest_size_within_a_quarter() -> None:
    assert nearest_size(21_000) == 20_000
    assert nearest_size(160_000 * 0.76) == 160_000
    assert nearest_size(60_000) is None


def test_decode_rate_is_the_median_per_size() -> None:
    lines = [_line(T0 + i, 100, 3.0, rate, prompt) for i, (rate, prompt) in enumerate([(50.0, 5_100), (48.0, 4_900), (52.0, 5_000), (30.0, 81_000)])]
    completions = [c for c in map(parse_line, lines) if c is not None]
    assert decode_by_size(completions) == {5_000: 50.0, 80_000: 30.0}


def test_total_throughput_spans_first_start_to_last_end() -> None:
    completions = [c for c in (parse_line(_line(T0 + 10, 400, 10.0, 40.0, 5_000)), parse_line(_line(T0 + 12, 400, 10.0, 40.0, 5_000))) if c]
    assert total_throughput(completions) == pytest.approx(800 / 12)
    with pytest.raises(ValueError, match="no completions"):
        total_throughput([])


@pytest.mark.parametrize(
    ("throughput", "k"),
    [({1: 40.0, 2: 59.9, 3: 59.0}, 1), ({1: 40.0, 2: 60.0, 3: 59.0}, 2), ({1: 40.0, 2: 70.0, 3: 90.0}, 3), ({1: 40.0, 2: 50.0, 3: 61.0}, 3)],
)
def test_k_is_the_largest_concurrency_at_one_and_a_half_times_single_stream(throughput: dict[int, float], k: int) -> None:
    assert choose_k(throughput) == k


def test_k_needs_the_single_stream_measure() -> None:
    with pytest.raises(ValueError, match="k = 1"):
        choose_k({2: 80.0})


def _plan_and_log() -> tuple[dict, list[str]]:
    lines, context = [], []
    for index, size in enumerate(CONTEXT_SIZES):
        start = T0 + index * 100
        lines.append(_line(start + 50, 512, 40.0, 50.0 - index * 5, size + 37))
        context.append({"size": size, "start": start, "end": start + 99})
    concurrency = []
    for index, k in enumerate(CONCURRENCY):
        start = T0 + 1000 + index * 1000
        for stream in range(k):
            lines.append(_line(start + 100, 1000, 100.0, 45.0, 5_000 + stream))
        lines.append(_line(start + 100, 999, 1.0, 45.0, 5_000, model="gemma-4-12B-it-MLX-8bit"))
        concurrency.append({"k": k, "start": start, "end": start + 999})
    lines.insert(3, "2026-09-14 00:00:00,000 - omlx.scheduler - INFO - [-] - noise")
    return {"model": MODEL, "context": context, "concurrency": concurrency}, lines


def test_the_analysis_reports_decode_by_size_throughput_by_k_and_k() -> None:
    plan, lines = _plan_and_log()
    report = analyze(plan, lines)
    assert report["decode_tok_s_by_prompt"] == {"5000": 50.0, "20000": 45.0, "40000": 40.0, "80000": 35.0, "160000": 30.0}
    assert report["missing_sizes"] == []
    assert report["total_tok_s_by_k"] == {"1": 10.0, "2": 20.0, "3": 30.0}
    assert report["k"] == 3


def test_the_analyze_command_reads_the_plan_and_log(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    plan, lines = _plan_and_log()
    (tmp_path / "plan.json").write_text(json.dumps(plan))
    (tmp_path / "server.log").write_text("\n".join(lines) + "\n")
    assert main(["analyze", "--plan", str(tmp_path / "plan.json"), "--log", str(tmp_path / "server.log")]) == 0
    assert json.loads(capsys.readouterr().out)["k"] == 3


def test_the_analyze_command_refuses_a_phase_with_no_completions(tmp_path: Path) -> None:
    plan, lines = _plan_and_log()
    plan["concurrency"][0]["start"] = plan["concurrency"][0]["end"] = 0.0
    (tmp_path / "plan.json").write_text(json.dumps(plan))
    (tmp_path / "server.log").write_text("\n".join(lines))
    assert main(["analyze", "--plan", str(tmp_path / "plan.json"), "--log", str(tmp_path / "server.log")]) == 2


def test_the_filler_approximates_the_requested_size() -> None:
    assert 19_000 * 4 <= len(filler(20_000)) <= 20_000 * 4


class _FakeServer:
    def __init__(self) -> None:
        self.bodies: list[dict] = []

    def __call__(self, request: object, timeout: float) -> object:
        self.bodies.append(json.loads(request.data))  # type: ignore[attr-defined]
        time.sleep(0.005)
        server = self

        class _Response:
            def __enter__(self) -> _Response:
                return self

            def __exit__(self, *exc: object) -> None:
                return None

            def read(self) -> bytes:
                return json.dumps({"n": len(server.bodies)}).encode()

        return _Response()


def test_the_driver_times_every_phase_and_sends_only_model_messages_and_max_tokens() -> None:
    server = _FakeServer()
    plan = run("http://fake/v1", MODEL, streams_seconds=0.05, max_tokens=64, opener=server)
    assert [phase["size"] for phase in plan["context"]] == list(CONTEXT_SIZES)
    assert [phase["k"] for phase in plan["concurrency"]] == list(CONCURRENCY)
    assert all(phase["start"] < phase["end"] for phase in [*plan["context"], *plan["concurrency"]])
    assert {tuple(sorted(body)) for body in server.bodies} == {("max_tokens", "messages", "model", "stream")}
    assert len(server.bodies) >= len(CONTEXT_SIZES) + sum(CONCURRENCY)
```

- [ ] **Step 2: Run to verify failure.** `uv run pytest -q tests/test_speed_probe.py` → `ModuleNotFoundError: No module named 'speed_probe'`.

- [ ] **Step 3: Implement.** `scripts/speed_probe.py`:

```python
#!/usr/bin/env python3
"""The context-speed and concurrency probe: requests to oMLX, numbers from its log.

Instrument for the attended probe (spec, "The model"): decode tok/s at prompt
sizes near 5k, 20k, 40k, 80k and 160k tokens, and total output tok/s with 1,
2 and 3 concurrent streams. No task outcome; no Pi. Two steps:

``run`` sends the requests and writes a plan: for each phase, its wall-clock
window. It uses the server's own sampling settings (it sends only the model,
the messages and ``max_tokens``), so the numbers are for the served
configuration ``preflight_settings`` verified.

``analyze`` reads the server log -- one line per completion, written when it
ends (format confirmed against ``~/.omlx/logs/server.log`` on 2026-09-14)::

    2026-09-14 09:51:27,151 - omlx.server - INFO - [-] - Chat completion:
    model=Ornith-1.5-9B-MLX-8bit, 758 tokens in 30.62s (27.3 tok/s),
    prompt: 44644, finish_reason=stop, max_tokens=32000, request_max_tokens=32000

(one physical line). The reported rate is decode-only: the seconds include
prefill, the rate does not. A completion belongs to the phase whose window
holds its end time. For a concurrency phase, total throughput is the phase's
output tokens over the span from its first completion's start (end minus
seconds) to its last completion's end.

k is the largest of 1, 2 or 3 whose total throughput is at least 1.5 times
k = 1's (spec, "Concurrency, both arms").

    uv run python scripts/speed_probe.py run --model Ornith-1.5-9B-MLX-8bit --plan PLAN.json
    uv run python scripts/speed_probe.py analyze --plan PLAN.json --log ~/.omlx/logs/server.log
"""

import argparse
import json
import re
import statistics
import sys
import threading
import time
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

CONTEXT_SIZES = (5_000, 20_000, 40_000, 80_000, 160_000)
CONCURRENCY = (1, 2, 3)
K_THRESHOLD = 1.5
#: A context completion counts for the nearest size within this fraction.
SIZE_TOLERANCE = 0.25
DEFAULT_BASE_URL = "http://127.0.0.1:8001/v1"
_LINE = re.compile(
    r"^(?P<at>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - omlx\.server - INFO - .*Chat completion: "
    r"model=(?P<model>[^,]+), (?P<tokens>\d+) tokens in (?P<seconds>[\d.]+)s \((?P<rate>[\d.]+) tok/s\), "
    r"prompt: (?P<prompt>\d+),"
)
_FILLER = "The quick brown fox jumps over the lazy dog while the probe counts tokens. "


@dataclass(frozen=True, slots=True)
class Completion:
    ended: float
    model: str
    tokens: int
    seconds: float
    rate: float
    prompt: int

    @property
    def started(self) -> float:
        return self.ended - self.seconds


def parse_line(line: str) -> Completion | None:
    """One completion from one log line; None for every other line."""
    if (match := _LINE.match(line)) is None:
        return None
    ended = datetime.strptime(match["at"], "%Y-%m-%d %H:%M:%S,%f").timestamp()
    return Completion(ended, match["model"], int(match["tokens"]), float(match["seconds"]), float(match["rate"]), int(match["prompt"]))


def completions_in(lines: Sequence[str], model: str, start: float, end: float) -> list[Completion]:
    parsed = (parse_line(line) for line in lines)
    return [c for c in parsed if c is not None and c.model == model and start <= c.ended <= end]


def nearest_size(prompt: int, sizes: Sequence[int] = CONTEXT_SIZES) -> int | None:
    size = min(sizes, key=lambda s: abs(s - prompt))
    return size if abs(size - prompt) <= SIZE_TOLERANCE * size else None


def decode_by_size(completions: Sequence[Completion]) -> dict[int, float]:
    """Median decode tok/s per context size, from the completions near each size."""
    rates: dict[int, list[float]] = {}
    for completion in completions:
        if (size := nearest_size(completion.prompt)) is not None:
            rates.setdefault(size, []).append(completion.rate)
    return {size: statistics.median(values) for size, values in sorted(rates.items())}


def total_throughput(completions: Sequence[Completion]) -> float:
    """Output tokens over the span from the first start to the last end."""
    if not completions:
        raise ValueError("no completions in the phase")
    span = max(c.ended for c in completions) - min(c.started for c in completions)
    if span <= 0:
        raise ValueError("the phase spans no time")
    return sum(c.tokens for c in completions) / span


def choose_k(throughput: dict[int, float]) -> int:
    """The largest k in 1, 2, 3 with total throughput >= 1.5 x k=1's."""
    if 1 not in throughput:
        raise ValueError("k = 1 was not measured")
    return max(k for k in CONCURRENCY if k == 1 or throughput.get(k, 0.0) >= K_THRESHOLD * throughput[1])


def analyze(plan: dict, lines: Sequence[str]) -> dict:
    model = plan["model"]
    context = [c for phase in plan["context"] for c in completions_in(lines, model, phase["start"], phase["end"])]
    throughput = {
        int(phase["k"]): total_throughput(completions_in(lines, model, phase["start"], phase["end"]))
        for phase in plan["concurrency"]
    }
    decode = decode_by_size(context)
    return {
        "model": model,
        "decode_tok_s_by_prompt": {str(size): round(rate, 1) for size, rate in decode.items()},
        "missing_sizes": [size for size in CONTEXT_SIZES if size not in decode],
        "total_tok_s_by_k": {str(k): round(value, 1) for k, value in sorted(throughput.items())},
        "k": choose_k(throughput),
    }


# --- the requests (attended; inference) ---------------------------------------


def filler(tokens: int, chars_per_token: float = 4.0) -> str:
    count = max(1, int(tokens * chars_per_token / len(_FILLER)))
    return _FILLER * count


def request(base_url: str, model: str, prompt: str, max_tokens: int, opener: Callable = urllib.request.urlopen) -> None:
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt + "\nSummarize the text above in one sentence."}], "max_tokens": max_tokens, "stream": False}).encode()
    call = urllib.request.Request(f"{base_url}/chat/completions", data=body, headers={"Content-Type": "application/json", "Authorization": "Bearer local"})
    with opener(call, timeout=3600) as response:
        response.read()


def _stream(base_url: str, model: str, stop: float, max_tokens: int, opener: Callable) -> None:
    while time.time() < stop:
        request(base_url, model, filler(CONTEXT_SIZES[0]), max_tokens, opener)


def run(base_url: str, model: str, *, streams_seconds: float, max_tokens: int, opener: Callable = urllib.request.urlopen) -> dict:
    plan: dict = {"model": model, "base_url": base_url, "context": [], "concurrency": []}
    for size in CONTEXT_SIZES:
        start = time.time()
        request(base_url, model, filler(size), max_tokens, opener)
        plan["context"].append({"size": size, "start": start, "end": time.time() + 1})
    for k in CONCURRENCY:
        start = time.time()
        stop = start + streams_seconds

        threads = [threading.Thread(target=_stream, args=(base_url, model, stop, max_tokens, opener)) for _ in range(k)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        plan["concurrency"].append({"k": k, "start": start, "end": time.time() + 1})
    return plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="speed_probe.py")
    sub = parser.add_subparsers(dest="action", required=True)
    run_p = sub.add_parser("run")
    run_p.add_argument("--model", required=True)
    run_p.add_argument("--plan", type=Path, required=True)
    run_p.add_argument("--base-url", default=DEFAULT_BASE_URL)
    run_p.add_argument("--stream-seconds", type=float, default=180.0)
    run_p.add_argument("--max-tokens", type=int, default=512)
    analyze_p = sub.add_parser("analyze")
    analyze_p.add_argument("--plan", type=Path, required=True)
    analyze_p.add_argument("--log", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.action == "run":
        plan = run(args.base_url, args.model, streams_seconds=args.stream_seconds, max_tokens=args.max_tokens)
        args.plan.write_text(json.dumps(plan, indent=2) + "\n")
        print(args.plan)
        return 0
    try:
        report = analyze(json.loads(args.plan.read_text()), args.log.read_text(encoding="utf-8").splitlines())
    except (OSError, ValueError, KeyError) as exc:
        print(f"speed_probe: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

`ROADMAP.md` (row 2b loses the warm prefix, which moves to the new row 2c; the status cell's date is the day Task 6 commits):

```diff
diff --git a/ROADMAP.md b/ROADMAP.md
index ff65f78..777cf9f 100644
--- a/ROADMAP.md
+++ b/ROADMAP.md
@@ -13,7 +13,8 @@ more. Nothing else is claimed.
 | 0 | Restart: tags, orphan trees, the import with provenance, gates green, launcher gate, docs caps, review script, hooks | overnight | both trees build; default tiers green; `just gates` enforces the caps; `PROVENANCE.md` names every file's source | done 2026-09-14 |
 | 1 | Engine `/implement` v1: derived contract, guards 1–4 and symbol preservation, carried tests, compact results, receipt | overnight, fake-first | every component has replay or fixture tests both directions; a fake model completes `/implement` end to end; 120/300 frozen against measured suite durations | done 2026-09-14 — evals e0f25df, engine 46d4514 |
 | 2a | Eval core: harvest, token and turn tripwire, census extensions, hygiene | overnight | harness items 1, 3, 4, 5 have fixture tests both directions; the Engine arm runs against a fake | done 2026-09-14 — docs/superpowers/plans/2026-09-14-phase-2a-eval-core.md |
-| 2b | Isolation and tasks: two-uid isolation, generator and R1-plan, candidates qualified, context-speed and concurrency probe, warm prefix recorded | overnight, plus attended isolation setup, probe and recording | the eval runs both arms against a fake under isolation with the budget tripwire; every candidate passes offline qualification; k measured; settings provenance verified by preflight | not started |
+| 2b | Isolation and tasks: two-uid isolation, generator and R1-plan, candidates qualified, context-speed and concurrency probe | overnight, plus attended isolation setup and probe | the eval runs both arms against a fake under isolation with the budget tripwire; every candidate passes offline qualification; k measured; settings provenance verified by preflight | built 2026-09-15 — docs/superpowers/plans/2026-09-14-phase-2b-isolation-and-tasks.md; k and the first isolated Pi turn are the attended checklist in its Task 6 |
+| 2c | Launcher loop and warm prefix: `launch RECORD` runs n cells at k with arms interleaved under the record's profile; the warm prefix recorded and replayed byte-identically | overnight, plus attended recording | a fake completes a k = 2 interleaved record under isolation through the launcher; a recorded prefix replays byte-identically against a fake | not started; lands before Phase 3 |
 | 3 | Admission and route proof: Baseline admission cells; one Engine cell per ceiling task | attended | ceiling and floor sets fixed; guards fire where retained evidence says they should; receipts read | not started |
 | 4 | Comparison: campaign record, held-out cut, seven batch nights | unattended batch, frozen in daylight | one result page per task and one against the rule | not started |
 | 5 | Decide and ship, or stop | attended | release one published, or a stated negative | not started |
```

- [ ] **Step 4: Pass, and preflight an isolated admission record** (no inference: a minute of `find` as the cell).

```bash
uv run pytest -q tests/test_speed_probe.py            # 17 passed
just lint-docs; echo "EXIT: $?"                        # 0
DIGEST=$(uv run python -c 'from satyrn_evals.task_tree import tree_digest; from satyrn_evals.manifest import DEFAULT_TASKS_ROOT as R; print(tree_digest(R / "agentclinic-repair-depth-3"))')
cat > "$SCR/depth-3-admission.json" <<JSON
{"version": 1, "task": "agentclinic-repair-depth-3", "task_tree_sha256": "$DIGEST", "arm": "baseline",
 "model": "omlx/Ornith-1.5-9B-MLX-8bit", "condition": "cold", "n": 4, "mode": "attended", "max_minutes": 60,
 "stop_rule": "established infrastructure failure only", "decision_rule": "admission: at most 1 of 4 within budget, uncontaminated",
 "previous_result": null, "token_budget": 32000, "turn_budget": 48, "isolation": "isolated", "purpose": "admission"}
JSON
uv run satyrn-evals launch --check "$SCR/depth-3-admission.json"; echo "EXIT: $?"     # launch: record accepted, 0
uv run satyrn-evals launch --preflight "$SCR/depth-3-admission.json" --arm arms/baseline-ornith15-9b.json > "$SCR/preflight.json"; echo "EXIT: $?"
```

Expected: EXIT 0 and `"problems": []` in `$SCR/preflight.json` (on 2026-09-14: no problem, 53 s). A non-zero exit is not fixed here: report the problem lines verbatim (a hit is material a hunting model could read, and removing it is the maintainer's). The isolation spike's `/Users/Shared/satyrn-cells/spike` is cell-readable but is neither a protected path nor a hunted name.

- [ ] **Step 5: Record, gates, commit.**

```bash
uv run python tools/provenance.py new scripts/speed_probe.py tests/test_speed_probe.py
uv run ruff check --fix; just gates; echo "EXIT: $?"
git add -A && git commit -m "Phase 2b: the context-speed and concurrency probe reads k and decode rates from oMLX's log; roadmap rows 2b and 2c"
```

- [ ] **Step 6: The maintainer's attended checklist** (written into the morning status, not executed; each line is Paul's, in daylight, in this order):

Commands run from `~/projects/pauleveritt/satyrn-evals` unless a line says otherwise. `W=~/satyrn-smokes/2b` is a directory under the maintainer's 700 home (`mkdir -p "$W"`). None of steps 1–7 spends inference.

1. **Close what a hunting cell could still read.** If 2a's checklist is not done: `chmod 700 ~/satyrn-smokes`. Remove the isolation spike's cell-owned leftover: `sudo -n -u satyrn-cell rm -rf /Users/Shared/satyrn-cells/spike`.
2. **The cell's Pi settings (Ruling 18).** Write exactly the two behaviour keys the maintainer's Pi uses, then verify compaction against the arm on a copy:
   ```bash
   (cd / && printf '{"compaction": {"enabled": true, "reserveTokens": 16384}, "defaultThinkingLevel": "high"}\n' | sudo -n -H -u satyrn-cell -- /bin/sh -c 'cat > /Users/satyrn-cell/.pi/agent/settings.json')
   C=$(mktemp -d "$W/cellpi-XXXX")
   (cd / && sudo -n -H -u satyrn-cell -- /bin/cat /Users/satyrn-cell/.pi/agent/models.json) > "$C/models.json"
   (cd / && sudo -n -H -u satyrn-cell -- /bin/cat /Users/satyrn-cell/.pi/agent/settings.json) > "$C/settings.json"
   uv run python scripts/preflight_inference.py arms/baseline-ornith15-9b.json --pi-config-dir "$C"; echo "EXIT: $?"   # 0
   rm -rf "$C"
   ```
3. **Export the engine for the cell** (Ruling 10): `uv run satyrn-evals cell-engine --engine-repo ~/projects/pauleveritt/satyrn-engine --commit release-one` → prints `/Users/Shared/satyrn-cells/engine-<sha>`; re-run after any engine commit the Engine arm should use.
4. **Warm the cell's uv cache for every candidate base** (network, no model). The base copy is removed at once: a self-hosted base carries other tasks' hidden suites, and step 6's hunt must find nothing.
   ```bash
   for t in agentclinic-repair-depth-3 agentclinic-repair-depth-2 selfhost-run-record-gate selfhost-guard-prefixes selfhost-review-script selfhost-docs-linter; do
     D=$(mktemp -d /Users/Shared/satyrn-cells/warm-XXXXXX); chmod 2770 "$D"
     chmod +a "user:$USER allow list,search,add_file,add_subdirectory,delete_child,read,write,append,readattr,writeattr,readextattr,writeextattr,readsecurity,delete,file_inherit,directory_inherit" "$D"
     cp -R src/satyrn_evals/tasks/$t/base/. "$D/"; chmod -R g+rwX "$D"
     (cd /Users/Shared && sudo -n -H -u satyrn-cell -- /usr/bin/env -i HOME=/Users/satyrn-cell PATH=/Users/satyrn-cell/.local/bin:/opt/homebrew/bin:/usr/bin:/bin /bin/sh -c "umask 007 && cd '$D' && uv sync --frozen && uv sync --frozen --offline"); echo "$t EXIT: $?"
     rm -rf "$D"
   done
   ```
   Every line `EXIT: 0`; `ls /Users/Shared/satyrn-cells` shows no `warm-*`.
5. **Settings provenance under the cell** (Task 3 ran it; re-run after any oMLX restart or config change): `uv run python scripts/preflight_settings.py arms/baseline-ornith15-9b.json --cell --record "$W/settings-cell.json"; echo "EXIT: $?"` → 0.
6. **The isolated preflight with the full hunt**, after steps 1–4: write `$W/depth-3-admission.json` exactly as Task 6 Step 4 does (with `$W` for `$SCR`), then `uv run satyrn-evals launch --preflight "$W/depth-3-admission.json" --arm arms/baseline-ornith15-9b.json > "$W/preflight.json"; echo "EXIT: $?"` → 0, `"problems": []`. A hit is material a hunting model could read: remove it and re-run.
7. **Confirm nothing of a cell is left**: `ps -A -o user=,command= | grep '^satyrn-cell' | grep -v -e /usr/libexec/ -e /usr/sbin/ -e /System/` prints nothing; `ls /Users/Shared/satyrn-cells` shows only `engine-<sha>`.
8. **The first Pi turn as the cell** (attended; inference; the calc-build fixture, no task outcome; the one sanctioned direct `attempt`, because 2b has no launcher loop — 2c replaces it):
   ```bash
   DIGEST=$(uv run python -c 'from pathlib import Path; from satyrn_evals.task_tree import tree_digest; print(tree_digest(Path("tests/integration/data/tasks/calc-build")))')
   cat > "$W/first-turn.json" <<JSON
   {"version": 1, "task": "calc-build", "task_tree_sha256": "$DIGEST", "arm": "baseline", "model": "omlx/Ornith-1.5-9B-MLX-8bit",
    "condition": "cold", "n": 1, "mode": "attended", "max_minutes": 60, "stop_rule": "any infrastructure failure stops the sitting",
    "decision_rule": "none: an isolation smoke, no task outcome", "previous_result": null, "token_budget": 32000, "turn_budget": 48,
    "isolation": "isolated", "purpose": "development"}
   JSON
   uv run satyrn-evals launch --check "$W/first-turn.json"
   uv run satyrn-evals attempt calc-build --tasks-root tests/integration/data/tasks --run-record "$W/first-turn.json" --output "$W/attempts" --timeout 1800 --attempt-timeout 2100 -- satyrn-evals-attempt-pi --model omlx/Ornith-1.5-9B-MLX-8bit
   ```
   Then read: `attempt.json` (any code; `NO_PATCH` or a fail is a finding, not a failure of the smoke), the transcript's first line (`"cwd"` under `/Users/Shared/satyrn-cells/`), that it holds `turn_start` events, whether the model's `git`/`uv run` commands succeeded, and step 7 again. An `EACCES`, "dubious ownership" or missing-tool error stops the sitting and goes to the status page verbatim.
9. **The context-speed and concurrency probe** (attended; exclusive GPU; about 25 minutes; no task outcome). Keep other clients off the server for the whole run:
   ```bash
   uv run python scripts/speed_probe.py run --model Ornith-1.5-9B-MLX-8bit --plan "$W/probe-plan.json"
   uv run python scripts/speed_probe.py analyze --plan "$W/probe-plan.json" --log ~/.omlx/logs/server.log | tee "$W/probe.json"
   ```
   If the run crosses midnight, the server rotates its log: `cat ~/.omlx/logs/server.log.<date> ~/.omlx/logs/server.log > "$W/server.log"` and analyze that. Decide in the sitting, from `decode_tok_s_by_prompt`, whether a context cap is set, and take `k` from the report; both go into Phase 3's run records and later the campaign record.
10. **Not tonight:** the warm prefix recording (2c, Ruling 19).

- [ ] **Step 7: Morning status** (under 250 words): evals head and the six task commits; default-tier and named integration counts; Task 3 Step 4's `preflight_settings --cell` line verbatim; Task 5 Step 5's 30 qualify lines summarized as six "qualified" lines (verbatim on any failure); Task 6 Step 4's preflight `problems` verbatim; the attended checklist above; the **Phase 3 watch list**: the model's first real `git commit` and `uv run` as `satyrn-cell` (Rulings 6, 8); a real Pi (Node) under the cell-side teardown (Ruling 7); a stopped cell's detached commands until the next preflight (Ruling 7); the Engine arm's transcript owned by the cell (Ruling 9); stray files outside `source_paths` (2a Ruling 2); the cell's Pi settings written by the checklist before any Pi turn (Ruling 18); what moved to 2c (Ruling 19). Do **not** start 2c.

---

## Self-review against the spec

- **Harness item 2, two-uid isolation** (second local user with its own home, per-cell TMPDIR, Pi, uv and model config; harness, grader, task directories and retained cells under the maintainer's uid; worktree in a group directory the cell writes and the grader reads; nothing sandboxed; one condition for both arms): Tasks 1–2; preflight reading the cell's Pi config: Task 3 (Ruling 3). `~/satyrn-smokes` closed: 2a's checklist, repeated in this one.
- **Budget under isolation, both arms**: Task 2's rows run at the campaign budget (32,000/48) and a harness-only budget (16,000/48).
- **Concurrency, k** from total throughput ≥ 1.5 × k = 1: Task 6 tooling; measured in the attended checklist.
- **Context-speed probe** (decode tok/s near 5k–160k, from server logs): Task 6 tooling; measured in the checklist; the context-cap decision is the maintainer's in that sitting.
- **Workloads**: the four ceiling candidates and the two floor tasks in the spec's tables are bundled (Tasks 4–5) and qualify offline (Task 5). Held-out tasks: cut at batch freeze, not here (brief).
- **Generator** (`(BASE, GOOD, files, HIDDEN, plan-anchor)`; base exclusions; `.gitignore` for residue; overlay HIDDEN at GOOD; known-good restricted to files; known-broken stubs the target; manifest provenance shas, task-tree digest, prompt digest; deterministic): Task 4. **Qualification** (fixtures both ways with zero collection errors; a committing, partly untracked fake attempt harvested whole and graded pass; hidden suite on GOOD three times): Task 5.
- **Rungs**: AgentClinic at R1 (manifests carry it); self-hosted at R1-plan (Task 4's derivation, formats disclosed).
- **Conditions**: cold everywhere; the warm prefix moved to 2c (Ruling 19).
- **Settings verified by preflight**: Task 3 Step 4 runs `preflight_settings --cell`.
- **Launcher refuses a drifted pin**: `--run-record` refuses a drifted task tree, arm or model (Task 3); the campaign-record comparison is Phase 4's.
- **Process**: six tasks; every test run before hand-back (below).

## Test verification (plan review, 2026-09-14)

Every test this plan specifies was run in scratch clones of evals `release-one` at `d22387b` (never the main checkout), against the engine checkout at `341d4c4`, on the maintainer's Mac with `satyrn-cell` set up. The code in this plan is not a sketch: a prototype was written first, then replayed as the six task commits in a fresh clone, each task's tests run before its implementation (the Step 2 messages above are those runs) and after it, with `just gates` exit 0 at every commit. The file blocks and diffs above are extracted from those six commits.

- **Unchanged tree:** default tier 1,772 passed; integration tier 276 passed, 1 skipped, 4 failed.
- **After Task 6:** default tier 1,916 passed; integration tier 306 passed, 1 skipped, 4 failed. The 4 failures are the same rows on the unchanged tree, `tests/test_workspace_failures.py::test_prepare_repository_fails_closed_on_verification[*]`: their fake environment reaches `/usr/bin/git`, which refuses with "You have not agreed to the Xcode license agreements" on this machine. Environmental, not this plan's; the executor reports them and does not touch them.
- **Per task, new or changed rows only:** T1 `tests/test_cell.py` 17 passed, `test_cell_isolation.py` 5 passed, the named 2a rows 26 passed; T2 adapters 60 passed, `test_isolated_arms.py` 5 passed three runs in a row (7.6–8.0 s), 2a rows plus `test_attempt_pi.py` 28 passed; T3 169 passed, `test_cell_preflight.py` (integration) 4 passed, `preflight_settings.py --cell` exit 0, isolated arms plus 2a rows 31 passed; T4 44 passed, cuts identical to the probe's for three tasks, `test_cut_task.py` (integration) 8 passed; T5 36 passed, `test_qualify.py` (integration) 8 passed in 38.6 s, `satyrn-evals qualify` on the six candidates 30 lines `ok`; T6 17 passed; `launch --check` accepted and `launch --preflight` with the full hunt reported no problem in 53 s.
- **The plan text itself reproduces the commits**: its file blocks written and its diff blocks applied with `git apply`, in order, with Task 4's cut and Task 5's import commands, on a fresh clone of `d22387b`, give trees identical to the six replay commits except two trailing blank lines at the end of `tests/integration/conftest.py` (absent from the plan, which is the cleaner file); default tier 1,916 passed there too.
- **Each new test fails on the tree before its task for the missing implementation only**: import errors at collection (T1–T6), and in T3 the monotonic-clock row's assertion.
- **The dubious-ownership check ran**: as the cell, `git status` in a worktree the maintainer made exits 128 "detected dubious ownership"; with the per-cell `GIT_CONFIG_GLOBAL` the cell writes, commits and leaves a file untracked, and the maintainer's harvest returns both paths and removes the workspace (Task 1's two rows).
- **Left behind:** after every run, no `satyrn-attempt-*` or `satyrn-test-*` under the cells root and no non-system `satyrn-cell` process. A full-disk hunt as the cell for the plan's names found nothing (58 s).

Defects found in the draft by running it, and fixed in this plan: group bits could not give the maintainer the engine's `0600` transcript (Ruling 5, inherited ACL); `GIT_CONFIG_COUNT` is stripped by `deliver` (Ruling 6); the engine export's venv pointed at a Python under the maintainer's home, and a plain `uv run` as the cell rebuilt the shared export (Ruling 10); the Engine adapter's receipt and logs landed in the workspace parent and were deleted with it (Ruling 9); `share_with_cell` raised on a `__pycache__` the cell had made (it now changes only the maintainer's entries); the existing rows that fake `_teardown_process` and `_safe_temp_parent` with narrower signatures, and `tests/test_attempt.py`'s exact exported environment, are kept by routing only the isolated profile through the new arguments; a hunt name list built from every overlay file would have refused on `_seed.py`-style helper names; a T3 row asserted hidden-suite names that only exist after T4; an integration drift row that copied a bundled task into pytest's temp directory was replaced by a synthetic repository; the cell has no Pi `settings.json`, so compaction and thinking level were unverified and different under isolation (Ruling 18).

Not executed, because they are the maintainer's or spend inference: the attended checklist's steps 2–4 and 8–9 (step 5's command is Task 3 Step 4's and ran; step 6's is Task 6 Step 4's and ran).
