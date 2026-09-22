# Phase 1 — Engine `/implement` v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The engine runs one developer request as a bounded `/implement`: a contract derived by code, one fresh Pi in its own worktree with guards 1–4 and symbol preservation loaded, accepted tests restored read-only before every self-test and before validation, compact test results, and one JSON receipt — every piece proven against fakes, replay fixtures and recorded output, with no inference, and the 120/300 command bounds frozen against measured suite durations.

**Architecture:** Python owns derivation, dispatch, budgets, validation and the receipt (`src/satyrn_engine/`); TypeScript owns the guards on Pi's `tool_call`/`tool_result` events and the two registered tools (`edit` via the mutator, `self_test` via the runner) in `packages/engine/`. Pi owns the per-command bound: the engine only sets or clamps bash `timeout` on `tool_call` and appends one sentence on `tool_result`. Everything the guards learn about the repo travels in the existing `SATYRN_MUTATION_CONTEXT` JSON; every guard firing is a `pi.appendEntry` custom entry, which Pi emits as `entry_appended` in the `--mode json` stream the engine already reads, so the receipt counts firings from the same stream it counts turns and tokens from. Nothing new is a sidecar; nothing new is a wrapper process; nothing the model can write is evidence.

**Tech Stack:** Python 3.14 (`tomllib`), uv, pytest (hermetic default tier; `integration` marker), ruff, just; Node 22+ (`--experimental-strip-types`), `node:test`; Pi 0.85.1 extension API (`tool_call` input mutation, `tool_result` patching, `registerTool`, `registerCommand`, `appendEntry`, `ctx.ui.confirm`/`ctx.hasUI`); git 2.45.

**Spec:** `docs/superpowers/specs/2026-09-13-release-one-design.md` at release-one `00c3c18` (sections "The product: `/implement`", "Bounds ownership", "Budget, both arms", "Before the Phase 1 plan freezes", roadmap row 1). Design ledger: `/private/tmp/claude-501/-Users-pauleveritt-projects-pauleveritt-satyrn-evals/553f3cc9-dfd8-475d-89e0-2859bed390d7/scratchpad/re-plan-ledger.md`. Pi facts: `.../scratchpad/research/pi-bash-bounding.md` and the Opus review `.../scratchpad/phase1-plan/review.md` §1 (verified from Pi 0.85.1 source: `--tools` is one allowlist over built-in, extension and custom tools; `tool_result` carries the post-mutation `input` and never fires for a blocked or schema-invalid call; `pi.appendEntry` appears in `--mode json` as `{"type":"entry_appended","entry":{"type":"custom","customType":…,"data":…}}` even with `--no-session`; `ctx.ui.confirm` exists, works in TUI/RPC and returns `false` in print/json).

## Rulings

Conflicts between the spec and the code as of engine `81e8af6`, each with the ruling taken here, why, and the cost if wrong. Steering rulings from the review are folded in and marked.

1. **Native `bash` versus the engine's `bash` override.** `packages/engine/runner.ts:220-235` registers the test runner under the name `bash` and `src/satyrn_engine/attempt.py:383` passes `--tools read,edit,bash`; the spec says both arms keep Pi's native tools and guard 4 bounds native bash. Ruling: bash is native; the runner is re-registered as `self_test`, and `--tools` becomes `read,bash,edit,write,self_test` (valid: one allowlist over every registered tool, Pi `cli/args.js:100-105`, `agent-session.js:2110-2166`). `runner.py:16-29` records that a parameterless tool named `run_tests` was never invoked in four smoke cells; the schema here is open (`command` optional and ignored, `additionalProperties: true`) so a model call that guesses an argument is not rejected before any hook can see it, and the bash result sentence names `self_test` on every shell call. Phase 3 watches whether `self_test` is invoked (Task 13 Step 5). Cost if wrong: the model verifies through native bash instead; guard 4 bounds it and validation stays authoritative.
2. **Contract field names.** The spec names `objective` and `self_test_command`; the engine's YAML and four test modules use `task` and `test_command` (`contract.py:28-33`). Ruling: keep the existing keys, add the new fields (`preserve`, `checks`, `token_budget`) under the spec's names, and let `derive.py` map objective→`task`. Cost if wrong: a reader of a contract file sees `task` where the spec says objective; Task 13's glossary row says so.
3. **Native `write` and file creation** (steering C2, I1, I2). `attempt.py:290` forbids creation and the mutator only replaces; build tasks create files. Ruling: `write` is allowed inside `writable_paths`. Guard 3 is a `tool_call` handler on `write` and `edit` (`scope.ts`) that resolves the path against the repo (leading `@` stripped, absolute paths inside the worktree admitted, traversal outside refused) before matching; the mutator learns the revision of every successful native `write` from its `tool_result` (`sha256(utf8(content))`, which is what Pi writes, `core/tools/write.js:18,48`) so `edit` after `write` works on existing and new files; a `write` that drops a base-defined symbol is refused like an `edit` would be. Every path key — scope's admission, the mutator's revision map, the loop breaker's revision map — is the same resolved repo-relative path from one module, `packages/engine/paths.ts` (N3), so a write by absolute or `@` path and an edit by relative path agree. Cost if wrong: a `write` to an existing writable file bypasses the mutator's anchor discipline — accepted, since the revision map, scope and symbol checks still hold.
4. **Developer confirmation** (M1). `orchestrator.ts:791` registers `/implement CONTRACT`. Ruling: `/implement <request>` derives, writes the contract under the repo's git dir and shows it; when `ctx.hasUI`, `ctx.ui.confirm("Dispatch this contract?", yaml)` dispatches on `true`; otherwise (print/json, where `confirm` returns `false`) the developer runs `/implement --go <id>`. Both paths are tested. Cost if wrong: one extra command in print mode.
5. **Where the derived contract lives** (steering C1). `deliver` refuses a dirty repo, so the contract cannot be in the working tree. Ruling: `<git-dir>/satyrn/contracts/<id>.yaml`, and `buildDeliveryInvocation` hands `attempt` an **absolute** contract path whenever the repo-relative path's first segment is `.git` — today (`orchestrator.ts:377-386`) it would pass `.git/satyrn/...` relative, which does not exist inside the linked worktree where `.git` is a file, and every dispatch would fail `CONTRACT_UNREADABLE`. Task 10's test fails on the current code first. Receipts are written beside the contracts (`<git-dir>/satyrn/receipts/<id>.json`, M7).
6. **Where the suite-duration measurement lives.** `docs/results/` is launcher-only (hook, Phase 0 Task 10) and results imply a model. Ruling: `scripts/suite_durations.json` written by `scripts/suite_durations.py --write` (integration tier), with a default-tier evals test that pins 120/300 and the runner's 120 s against the measured maxima. Cost if wrong: data beside the instruments that produced it, as `scripts/` already does.
7. **Guard-firing evidence** (steering I9; replaces the earlier side-file ruling). Guards record firings with `pi.appendEntry(kind, data)` as `engine.ts:282` already does; Pi emits them as `entry_appended` events in the child's json stream; the receipt counts them there. No file the model's shell can reach is evidence. Cost if wrong: none identified; the retained `2026-09-05-v11c-spike-184017/cell-008-engine` transcript shows the event shape.
8. **Seconds in the contract.** `deadline_seconds` stays in `Contract`/`Budget` as the engine's own backstop; never derived.
9. **Carried tests** (steering C3 and N2; replaces the sibling-directory ruling). The **carried set** is `preserve`, `checks`, and the test infrastructure tracked at base: every tracked `conftest.py` and, when tracked, `pyproject.toml`, `pytest.ini`, `setup.cfg`, `tox.ini`. It is restored from the accepted base **into the worktree** (`git checkout <base_commit> -- <paths>`, the base commit carried in the mutation context so a model `git commit` cannot move it — m6) immediately before every `self_test` run and into the validation checkout before validation. The project's own pytest configuration and `conftest.py` therefore apply as the developer committed them, tests the model adds run (the first run is the unmodified `test_command`), `preserve` paths and `checks/` files are passed as explicit file arguments in further runs so they are collected regardless of `python_files` or any `collect_ignore`, and the model's edits to anything in the carried set never count because they are overwritten before anything runs. `scope.ts` refuses `write`/`edit` to a carried path with "restored before every self-test" (m5), and `preserve` paths are excluded from derived `writable_paths`. The receipt sets `carried.tampered` to the carried paths the candidate commit changed (a new `conftest.py` under `tests/` counts). Nothing runs from outside the repository. Cost if wrong: a repo whose pytest config lives in a file not on this list (e.g. `.pytest.ini`) can be re-configured by the model; `carried.tampered` still names a changed `pyproject.toml`.
10. **Guards live only in the `/implement` child** (steering I8). `scope.ts`, `bounds.ts` and the symbol check register only when `SATYRN_MUTATION_CONTEXT` parses, exactly as `mutator.ts:352-360` and `runner.ts:249-257` already do, and neither file is added to `packages/engine/package.json` (`attempt.py:352-358` passes `--no-extensions` plus explicit `--extension` paths, so the child never needs the listing). The developer's own session keeps only the loop breaker and the `/implement` command. Tested both directions.
11. **HP1 reuse** (steering I13). The engine never imports evals. HP1's builder (`satyrn-evals/src/satyrn_evals/packet.py:156 build_packet`) derives from a task manifest and a `SessionSpec` step, not from a developer's request, so its body does not carry over; what carries over is its `writable_paths` rendering rule (a directory becomes `dir/*`; `engine_contract.py:33-84 @ 00c3c18`) and its `admits` rule (`engine_contract.py:86-94`), both re-stated in `derive.py`/`scope.ts` with a comment citing that provenance. `derive.py` is new code with a provenance row of its own. Cost if wrong: two ~10-line rules exist in both trees; a change to one is not a change to the other, which is the intended direction (`BRIEF.md`: product code never imports a laboratory).
12. **The self-test command** (steering I7/I14). Read from `pyproject.toml` when declared as `[tool.satyrn] self_test = ["uv", "run", "pytest", "-q"]`; otherwise the default `("uv", "run", "python", "-m", "pytest", "-q")`, which puts the working directory on `sys.path` and so works for the flat AgentClinic layout (`app.py`, `tests/test_app.py`, no `pythonpath`) as well as for src layouts installed by uv. Writable paths admit files a build task creates: a request token naming an untracked path whose parent directory is tracked becomes an exact writable path. Cost if wrong: a repo needing a different runner declares it in one pyproject line.
13. **One token counter** (steering I11/I12). `budget.TurnCounter` is the only stream counter (turns, tool calls, tokens in/out, guard firings). When a budget is declared it runs live in `_stream_implementer`; when none is declared the spool is fed through the same class after the run. One trip reason, `token_exhausted`, with its own receipt message; `deliver` itself defaults `token_limit` to `contract.token_budget`.

## Global Constraints

- **Roles for execution: Sonnet implements, Opus reviews, no haiku.** One fresh implementer per task; one review per task before the next starts.
- **No inference anywhere in this phase.** Fake models, replay over recorded events, fixture repos, recorded pytest output. Guard 4 is proven on a fake Pi event stream in both directions; its live proof is Phase 3.
- **Bounds ownership.** Pi owns the per-command bound. The engine sets or clamps bash `timeout` via `tool_call` input mutation and appends one sentence via `tool_result`. No `timeout(1)`, alarms, `ulimit`, `sandbox-exec` or any wrapper process in either tree; no port of old POSIX clamp code. `runner.py:39` (`DEFAULT_TEST_TIMEOUT_SECONDS = 120.0`) owns the self-test bound; the TS exchange deadline for `self_test` is derived from it (Task 4), never a second number.
- **Budgets in the contract are tokens and turns**; the receipt records budget state. Seconds are the engine's own backstop.
- **The contract is derived by code from the request and the repo**; the developer confirms, never hand-writes. Facts inline in the prompt, no pointer prompts.
- **Reuse over rewrite.** Each task names the file and line it reuses and what changes.
- **Default test tier: no model, no network, no subprocess.** Engine: `tests/conftest.py`'s monkeypatch tripwire; evals: the audit hook. Anything spawning a process is `@pytest.mark.integration`. Node tests run under `node --test --experimental-strip-types`.
- **Every refusal test has a sibling success test.** Every guard has a fixture that fires and a fixture that does not, and a test that it does not register outside the `/implement` child.
- **Every task ends with `just gates` green in the tree it touches** (exit code read, never piped). New files get `PROVENANCE.md` rows via `tools/provenance.py new`. Edited imported files keep their rows.
- **Commit at the end of every task**, on `release-one` of the tree being worked in, with the plan's message. Never `--amend`, never merge, never push. A task whose gates are red is not committed.
- Evals docs caps stand: `ROADMAP.md` ≤ 150 lines; specs ≤ 400; permitted `docs/` directories only. Engine caps: `ROADMAP.md`, `BACKLOG.md` ≤ 400 lines and must exist.
- Old worktrees under `.claude/worktrees/` in evals are read only by `git archive <branch>:<path>`; they are never checked out, edited or removed.
- Engine tree: `/Users/pauleveritt/projects/pauleveritt/satyrn-engine` on `release-one` (HEAD `81e8af6` or later). Evals tree: `/Users/pauleveritt/projects/pauleveritt/satyrn-evals` on `release-one` (HEAD `00c3c18` or later).
- **Phase stop.** If Task 1 ends with `fit_failures` non-empty, nothing is committed and no later task starts; the question goes to the morning status.

---

## File structure

### Engine tree (`satyrn-engine`)

```
packages/engine/engine.ts        # loop breaker (guard 1); learns `write` revisions                       (modify)
packages/engine/mutator.ts       # edit override; context gains writable_paths, test_command, symbols; write revisions; symbol refusal (modify)
packages/engine/runner.ts        # tool renamed `self_test` (open schema); 130 s exchange deadline        (modify)
packages/engine/scope.ts         # guard 3 on tool_call for write/edit paths; write symbol check           (new)
packages/engine/bounds.ts        # guard 4: set/clamp bash timeout; append one sentence on tool_result   (new)
packages/engine/orchestrator.ts  # /implement: derive, confirm or --go, dispatch, write the receipt        (modify)
src/satyrn_engine/contract.py    # preserve, checks, token_budget                                        (modify)
src/satyrn_engine/budget.py      # token_limit; TurnCounter counts tokens, tool calls, guard firings      (modify)
src/satyrn_engine/derive.py      # derive_contract(): request + repo facts -> Contract YAML              (new)
src/satyrn_engine/runner.py      # compact_output(); restore carried; run checks as files                 (modify)
src/satyrn_engine/protocol.py    # RunTestsRequest.command: str | None                                   (modify)
src/satyrn_engine/attempt.py     # prompt, argv, context (writable_paths, test_command, symbols)         (modify)
src/satyrn_engine/delivery.py    # restore carried at validation; stream counts; receipt fields          (modify)
src/satyrn_engine/cli.py         # `derive` subcommand; --token-limit                                    (modify)
tools/replay_events.mjs          # replay tool_call/tool_result/tool_exec fixtures through one extension  (new)
tools/exercise_runner.mjs        # one argument: CONTEXT.json                                            (modify)
tests/fixtures/events/*.json     # bounds-*, scope-*, symbol-* fixtures, both directions                  (new)
tests/fixtures/attempt/fake_pi.py# mode "implement": a fake model that edits, self-tests, spends tokens  (modify)
tests/test_*.py, tests/*.mjs     # per task
docs/usage.md, docs/glossary.md, README.md, ROADMAP.md, BACKLOG.md                                      (modify)
```

### Evals tree (`satyrn-evals`)

```
scripts/suite_durations.py       # measure public-suite and grade durations per candidate task (integration) (new)
scripts/suite_durations.json     # the committed measurement                                                (new)
tests/test_suite_durations.py    # pure fit check of 120/300 and the runner bound against the JSON          (new)
ROADMAP.md                       # synced to the ceiling claim                                              (modify)
```

---

### Task 1: Measure the public-suite durations, with no inference (evals)

**Files:**
- Create: `scripts/suite_durations.py`, `scripts/suite_durations.json`, `tests/test_suite_durations.py`
- Modify: `PROVENANCE.md` (via the recorder)

**Interfaces:**
- Produces: `suite_durations.CANDIDATES: tuple[Candidate, ...]`; `fits(measured_max_seconds: float | None, *, default_seconds: int, clamp_seconds: int, runner_seconds: int, margin: float) -> list[str]` (pure; empty when every bound fits; `None` means no candidate had a suite, which is itself a failure); `longest_public(rows: dict[str, dict]) -> float | None` (pure; ignores rows whose `public_suite` is `None`); `measure(candidate, scratch: Path) -> Measurement` (integration only); the JSON shape below; the CLI `uv run python scripts/suite_durations.py --write`.

The tasks on disk and where they are reached read-only:

| task | branch | why that branch |
|---|---|---|
| `agentclinic-repair-misleading-locus`, `agentclinic-complaint-lifecycle` | `release-one` (this tree) | bundled |
| `agentclinic-repair-depth-2`, `agentclinic-repair-depth-3` | `worktree-ornith-ceiling-probe` (`4f0ee53`) | the tree the ceiling cells ran on |
| `selfhost-docs-linter`, `selfhost-guard-prefixes`, `selfhost-run-record-gate` | `worktree-selfhost-headroom-probe` (`635c12b`) | the only tree holding them |

`selfhost-review-script` (spec, ceiling table) is not on disk; when the generator cuts it, this script is re-run and the fit re-checked before the campaign record freezes (M12). A task tree is materialized with `git archive <branch>:src/satyrn_evals/tasks/<name> | tar -x -C <scratch>/<name>`. `grade.py`, `manifest.py` and `oracle_hook.py` are byte-identical across the three branches, so this tree's `grade` is the right oracle.

Two durations per task, each three runs: **public** — copy `base/`, `git init`, `git apply fixtures/known-good.patch`, run `manifest.public_suite` (the command the model runs; the first run includes `uv sync`), recording wall seconds and the exit code; **grade** — `satyrn_evals.grade.grade(task_dir, known-good.patch, receipt)`. A manifest without `public_suite` (`agentclinic-complaint-lifecycle`, outside the claim per the spec's floor set) records `public_suite: null`, `public_seconds: []`, `public_exits: []` and is excluded from the longest.

- [ ] **Step 1: Write the failing default-tier test**

```python
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from suite_durations import CANDIDATES, fits, longest_public  # noqa: E402  # scripts/ via sys.path, as tests/test_power.py does

JSON = Path(__file__).parents[1] / "scripts" / "suite_durations.json"
BOUNDS = {"default_seconds": 120, "clamp_seconds": 300, "runner_seconds": 120, "margin": 2.0}


def test_the_seven_candidates_are_named_with_their_branches() -> None:
    assert {c.task for c in CANDIDATES} == {
        "agentclinic-repair-misleading-locus", "agentclinic-complaint-lifecycle",
        "agentclinic-repair-depth-2", "agentclinic-repair-depth-3",
        "selfhost-docs-linter", "selfhost-guard-prefixes", "selfhost-run-record-gate"}
    assert {c.branch for c in CANDIDATES} == {
        "release-one", "worktree-ornith-ceiling-probe", "worktree-selfhost-headroom-probe"}


def test_a_bound_fits_when_the_longest_suite_times_the_margin_is_under_it() -> None:
    assert fits(45.0, **BOUNDS) == []


def test_a_default_or_runner_bound_that_does_not_fit_is_named_not_adjusted() -> None:
    assert fits(70.0, **BOUNDS) == [
        "default 120 s < 140.0 s (70.0 s x 2.0)", "runner 120 s < 140.0 s (70.0 s x 2.0)"]


def test_a_clamp_under_twice_the_default_is_refused() -> None:
    assert "clamp 200 s < 240 s (2 x default)" in fits(10.0, **{**BOUNDS, "clamp_seconds": 200})


def test_no_measured_suite_at_all_is_a_failure_not_a_fit() -> None:
    assert fits(None, **BOUNDS) == ["no candidate with a public suite was measured"]


def test_rows_without_a_public_suite_are_excluded_from_the_longest() -> None:
    rows = {"a": {"public_suite": None, "public_seconds": []},
            "b": {"public_suite": ["x"], "public_seconds": [3.0, 2.0]}}
    assert longest_public(rows) == 3.0
    assert longest_public({"a": rows["a"]}) is None


def test_the_committed_measurement_freezes_120_300_and_the_runner_bound() -> None:
    body = json.loads(JSON.read_text())
    assert body["version"] == 1 and body["margin"] == 2.0 and body["fit_failures"] == []
    assert body["longest_public_seconds"] == longest_public(body["tasks"])
    for row in body["tasks"].values():
        assert all(code == 0 for code in row["public_exits"]), row["task"]
    assert fits(body["longest_public_seconds"], **BOUNDS) == []
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_suite_durations.py -q` → FAIL, `No module named 'suite_durations'` (`scripts/` is not a package; tests reach it through `sys.path`, the convention `tests/test_power.py:14-16` uses).

- [ ] **Step 3: Write the script**

```python
"""Public-suite and grade durations per release-one candidate task, no model.

The Phase 1 plan freezes the engine's per-command bounds (bash `timeout`
default 120 s, clamp 300 s) and its self-test bound (runner.py, 120 s)
against these numbers. `fits` is the rule; `measure` produces the numbers;
`--write` commits them. Task trees on probe branches are read with
`git archive`, never checked out.
"""

import json
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "scripts" / "suite_durations.json"
RUNS = 3
DEFAULT_SECONDS = 120
CLAMP_SECONDS = 300
RUNNER_SECONDS = 120   # satyrn-engine runner.py DEFAULT_TEST_TIMEOUT_SECONDS
MARGIN = 2.0


@dataclass(frozen=True, slots=True)
class Candidate:
    task: str
    branch: str

    @property
    def tree_path(self) -> str:
        return f"src/satyrn_evals/tasks/{self.task}"


CANDIDATES: tuple[Candidate, ...] = (
    Candidate("agentclinic-repair-misleading-locus", "release-one"),
    Candidate("agentclinic-complaint-lifecycle", "release-one"),
    Candidate("agentclinic-repair-depth-2", "worktree-ornith-ceiling-probe"),
    Candidate("agentclinic-repair-depth-3", "worktree-ornith-ceiling-probe"),
    Candidate("selfhost-docs-linter", "worktree-selfhost-headroom-probe"),
    Candidate("selfhost-guard-prefixes", "worktree-selfhost-headroom-probe"),
    Candidate("selfhost-run-record-gate", "worktree-selfhost-headroom-probe"),
)


@dataclass(frozen=True, slots=True)
class Measurement:
    task: str
    branch: str
    commit: str
    public_suite: list[str] | None
    public_seconds: list[float]
    public_exits: list[int]
    grade_seconds: list[float]
    grade_verdicts: list[str]


def fits(measured_max_seconds: float | None, *, default_seconds: int, clamp_seconds: int,
         runner_seconds: int, margin: float) -> list[str]:
    """Name every way the frozen bounds fail to cover the longest suite. Pure."""
    if measured_max_seconds is None:
        return ["no candidate with a public suite was measured"]
    failures: list[str] = []
    needed = measured_max_seconds * margin
    if default_seconds < needed:
        failures.append(f"default {default_seconds} s < {needed} s ({measured_max_seconds} s x {margin})")
    if clamp_seconds < 2 * default_seconds:
        failures.append(f"clamp {clamp_seconds} s < {2 * default_seconds} s (2 x default)")
    if runner_seconds < needed:
        failures.append(f"runner {runner_seconds} s < {needed} s ({measured_max_seconds} s x {margin})")
    return failures


def longest_public(rows: dict[str, dict]) -> float | None:
    measured = [max(row["public_seconds"]) for row in rows.values() if row["public_suite"] and row["public_seconds"]]
    return max(measured) if measured else None


def materialize(candidate: Candidate, scratch: Path) -> tuple[Path, str]:
    commit = subprocess.run(["git", "rev-parse", f"{candidate.branch}^{{commit}}"], cwd=ROOT,
                            check=True, capture_output=True, text=True).stdout.strip()
    task_dir = scratch / candidate.task
    task_dir.mkdir(parents=True)
    archive = subprocess.run(["git", "archive", f"{candidate.branch}:{candidate.tree_path}"],
                             cwd=ROOT, check=True, capture_output=True).stdout
    subprocess.run(["tar", "-x", "-C", str(task_dir)], input=archive, check=True)
    return task_dir, commit


def _timed_public_run(task_dir: Path, public_suite: list[str], scratch: Path) -> tuple[float, int]:
    work = scratch / "public"
    if work.exists():
        shutil.rmtree(work)
    shutil.copytree(task_dir / "base", work, symlinks=True)
    subprocess.run(["git", "init", "-q"], cwd=work, check=True)
    subprocess.run(["git", "apply", str(task_dir / "fixtures" / "known-good.patch")], cwd=work, check=True)
    started = time.monotonic()
    completed = subprocess.run(public_suite, cwd=work, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return round(time.monotonic() - started, 1), completed.returncode


def measure(candidate: Candidate, scratch: Path) -> Measurement:
    from satyrn_evals.grade import grade
    from satyrn_evals.manifest import load_manifest

    task_dir, commit = materialize(candidate, scratch)
    manifest = load_manifest(task_dir)
    public_suite = list(manifest.public_suite) or None
    public_seconds: list[float] = []
    public_exits: list[int] = []
    if public_suite:
        for _ in range(RUNS):
            seconds, code = _timed_public_run(task_dir, public_suite, scratch)
            public_seconds.append(seconds)
            public_exits.append(code)
    grade_seconds: list[float] = []
    verdicts: list[str] = []
    for index in range(RUNS):
        receipt = scratch / f"receipt-{index}.json"
        started = time.monotonic()
        try:
            result = grade(task_dir, task_dir / "fixtures" / "known-good.patch", receipt)
        except Exception as exc:  # one task's grader must not abort --write; the error is the record (m10)
            grade_seconds.append(round(time.monotonic() - started, 1))
            verdicts.append(f"grade_error: {type(exc).__name__}: {exc}")
            continue
        grade_seconds.append(round(time.monotonic() - started, 1))
        verdicts.append(str(result.verdict))
    return Measurement(candidate.task, candidate.branch, commit, public_suite,
                       public_seconds, public_exits, grade_seconds, verdicts)


def main(argv: list[str]) -> int:
    if argv != ["--write"]:
        print("usage: suite_durations.py --write", file=sys.stderr)
        return 2
    measurements: list[Measurement] = []
    with tempfile.TemporaryDirectory(prefix="suite-durations-") as scratch:
        for candidate in CANDIDATES:
            measurement = measure(candidate, Path(scratch) / candidate.task)
            measurements.append(measurement)
            print(f"{candidate.task}: public {measurement.public_seconds} exits {measurement.public_exits} "
                  f"grade {measurement.grade_seconds} {measurement.grade_verdicts}")
    rows = {m.task: asdict(m) for m in measurements}
    longest = longest_public(rows)
    failures = fits(longest, default_seconds=DEFAULT_SECONDS, clamp_seconds=CLAMP_SECONDS,
                    runner_seconds=RUNNER_SECONDS, margin=MARGIN)
    failures += [f"{m.task}: public suite exited {m.public_exits} on known-good"
                 for m in measurements if any(code != 0 for code in m.public_exits)]
    body = {
        "version": 1,
        "machine": "the maintainer's batch machine; seconds never compare across machines",
        "recompute": "uv run python scripts/suite_durations.py --write",
        "margin": MARGIN,
        "frozen": {"default_seconds": DEFAULT_SECONDS, "clamp_seconds": CLAMP_SECONDS, "runner_seconds": RUNNER_SECONDS},
        "longest_public_seconds": longest,
        "fit_failures": failures,
        "tasks": rows,
    }
    OUTPUT.write_text(json.dumps(body, indent=2) + "\n")
    print(OUTPUT)
    for failure in failures:
        print(f"fit failure: {failure}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 4: Run the measurement (integration, no model)**

`uv run python scripts/suite_durations.py --write; echo "EXIT: $?"`. Spawns git, tar, uv and pytest; not a default-tier test. Expected: seven lines, `EXIT: 0`. Expected magnitudes from the retained cells (`scratchpad/workload-deep-dive/rationale.md` Q4): AgentClinic 2–6 s, self-hosted 30–45 s. The first run's `uv sync` is the realistic worst case on this machine's warm cache; Phase 2's cell user has a cold cache and re-checks under isolation.

**Stop rule.** If `EXIT: 1`: the longest suite × 2 exceeds a bound, or a known-good public suite did not exit 0. Do not change 120/300/120. **Commit nothing** (the JSON would turn `test_the_committed_measurement_freezes_120_300_and_the_runner_bound` red and gates must be green to commit). Leave the three files uncommitted, put the exact `fit failure:` lines and the question ("longest public suite is N s on task T; a 120 s default needs ≤ 60 s; propose X/Y, or accept a ceiling task with a slow suite?") in the morning status, and stop the phase: Tasks 2–13 do not start.

If a grade verdict is not `pass` for a candidate, that is a finding about the task tree, not the bound: it is recorded in `grade_verdicts`, reported in the status, and does not stop the phase.

- [ ] **Step 5: Tests pass; ruff; record; commit**

```bash
uv run pytest tests/test_suite_durations.py -q          # 7 passed
uv run ruff check; echo "EXIT: $?"
uv run python tools/provenance.py new scripts/suite_durations.py scripts/suite_durations.json tests/test_suite_durations.py
just gates; echo "EXIT: $?"                             # must be 0
git add -A && git commit -m "Phase 1: measure public-suite durations; 120/300 and the runner bound fit"
```

---

### Task 2: Contract fields and the one stream counter (engine)

**Files:**
- Modify: `src/satyrn_engine/contract.py:24-33,82-132`, `src/satyrn_engine/budget.py`, `src/satyrn_engine/delivery.py:314-361` (`deliver`), `:895-916` (`_consume_chunk`), `:840-857` (exhaustion message), `src/satyrn_engine/cli.py:113-122,235`, `tests/test_contract.py`, `tests/test_budget.py`, `tests/test_budget_delivery.py`

**Interfaces:**
- Produces: `Contract.preserve: tuple[str, ...] = ()`, `Contract.checks: tuple[str, ...] = ()`, `Contract.token_budget: int | None = None`; `Budget(turn_limit, deadline_seconds, token_limit=None)`; `BudgetState.TOKEN_EXHAUSTED = "token_exhausted"`; `BudgetUsage(state, turns_used, seconds_used, tokens_used=0)`; `budget.GUARD_KINDS = ("loop_broken", "scope_refused", "symbol_preserved", "command_bounded", "command_timed_out")`; `TurnCounter` gains `.tokens_in`, `.tokens_out`, `.tool_calls`, `.guard_firings: dict[str, int]`; `evaluate(budget, turns_used, seconds_used, tokens_used=0)`; `deliver(..., token_limit: int | None = None)` defaulting to `contract.token_budget`; CLI `--token-limit N`.

Reuse: `budget.py:62-80` `TurnCounter.feed` (counts `turn_start`); it learns `message_end` (assistant `message.usage.input/output`, the shape in every retained `--mode json` transcript, e.g. `~/satyrn-smokes/2026-09-14-ornith9b-ceiling-probe/cell-10-A4/*/transcript.txt`; `cacheRead` is not counted — M13), `tool_execution_start`, and `entry_appended` whose `entry.customType` is a guard kind (shape: `~/satyrn-smokes/2026-09-05-v11c-spike-184017/cell-008-engine/*/transcript.txt`). `delivery.py:914` trips on turns; the token trip sits beside it.

- [ ] **Step 1: Failing tests**

Append to `tests/test_contract.py`:

```python
def test_load_contract_with_carried_fields_and_token_budget(tmp_path: Path) -> None:
    path = tmp_path / "c.yaml"
    path.write_text("id: x\ntask: t\npreserve: [tests/test_a.py]\nchecks: [checks/c.py]\ntoken_budget: 32000\n", encoding="utf-8")
    contract = load_contract(path)
    assert contract.preserve == ("tests/test_a.py",) and contract.checks == ("checks/c.py",)
    assert contract.token_budget == 32000


def test_carried_fields_default_to_empty_and_token_budget_to_absent(tmp_path: Path) -> None:
    path = tmp_path / "c.yaml"
    path.write_text("id: x\ntask: t\n", encoding="utf-8")
    contract = load_contract(path)
    assert contract.preserve == () and contract.checks == () and contract.token_budget is None


@pytest.mark.parametrize("value", ["tests", "[1]", "['']"])
def test_load_invalid_preserve_is_refused(tmp_path: Path, value: str) -> None:
    path = tmp_path / "c.yaml"
    path.write_text(f"id: x\ntask: t\npreserve: {value}\n", encoding="utf-8")
    with pytest.raises(ContractError, match="preserve"):
        load_contract(path)


@pytest.mark.parametrize("value", ["0", "-1", "true", "'32000'"])
def test_load_invalid_token_budget_is_refused(tmp_path: Path, value: str) -> None:
    path = tmp_path / "c.yaml"
    path.write_text(f"id: x\ntask: t\ntoken_budget: {value}\n", encoding="utf-8")
    with pytest.raises(ContractError, match="token_budget"):
        load_contract(path)
```

Append to `tests/test_budget.py`:

```python
def _assistant(output: int, input_tokens: int = 10) -> str:
    return json.dumps({"type": "message_end", "message": {
        "role": "assistant", "usage": {"input": input_tokens, "output": output, "cacheRead": 5000}}})


def _entry(kind: str) -> str:
    return json.dumps({"type": "entry_appended", "entry": {"type": "custom", "customType": kind, "data": {}}})


def test_counter_sums_assistant_usage_tool_calls_and_guard_firings_only() -> None:
    counter = TurnCounter()
    for line in (
        '{"type":"turn_start"}', _assistant(100, 50),
        json.dumps({"type": "message_end", "message": {"role": "user"}}),
        json.dumps({"type": "message_end", "message": {"role": "toolResult", "usage": {"output": 999}}}),
        '{"type":"tool_execution_start","toolName":"bash"}', _assistant(20, 70),
        '{"type":"message_update","usage":{"output":5000}}',
        _entry("loop_broken"), _entry("command_bounded"), _entry("command_bounded"), _entry("unknown_kind"),
    ):
        counter.feed(line)
    assert (counter.turns, counter.tokens_in, counter.tokens_out, counter.tool_calls) == (1, 120, 120, 1)
    assert counter.guard_firings == {"loop_broken": 1, "scope_refused": 0, "symbol_preserved": 0,
                                     "command_bounded": 2, "command_timed_out": 0}


def test_a_token_limit_trips_on_the_limit_plus_one() -> None:
    budget = Budget(token_limit=100)
    assert evaluate(budget, 1, 0.0, tokens_used=100).state is BudgetState.WITHIN
    assert evaluate(budget, 1, 0.0, tokens_used=101).state is BudgetState.TOKEN_EXHAUSTED


def test_token_exhaustion_wins_over_turns_and_deadline() -> None:
    budget = Budget(turn_limit=1, deadline_seconds=1.0, token_limit=1)
    assert evaluate(budget, 5, 5.0, tokens_used=5).state is BudgetState.TOKEN_EXHAUSTED


def test_a_budget_with_only_a_token_limit_is_declared() -> None:
    assert Budget(token_limit=1).declared and not Budget().declared
```

Append to `tests/test_budget_delivery.py`, next to the existing turn-exhaustion delivery test (grep `TURN_EXHAUSTED` there and copy its harness):

```python
def test_token_exhaustion_keeps_the_candidate_and_says_so(...) -> None:
    # same harness as the turn-exhaustion test, with a stream of three assistant message_end lines
    # of 300 output tokens each and a contract `token_budget: 500`, no --token-limit override
    assert receipt.code is DeliveryCode.BUDGET_EXHAUSTED
    assert receipt.budget_usage.state is BudgetState.TOKEN_EXHAUSTED
    assert receipt.budget.token_limit == 500 and receipt.budget_usage.tokens_used == 600
    assert receipt.message == "candidate created; whole-attempt token budget exhausted after 600 output tokens"
```

- [ ] **Step 2: Run to verify failure** — `uv run pytest tests/test_contract.py tests/test_budget.py tests/test_budget_delivery.py -q` → failures naming `preserve`, `token_budget`, `tokens_in`, `guard_firings`, `token_limit`.

- [ ] **Step 3: Implement**

`contract.py`: add to the dataclass after `deadline_seconds`:

```python
    preserve: tuple[str, ...] = ()
    checks: tuple[str, ...] = ()
    token_budget: int | None = None
```

In `load_contract` build them (`preserve=tuple(cast(list[str], data.get("preserve", [])))`, same for `checks`, `token_budget=data.get("token_budget")`). In `_field_problems`, one loop over `("preserve", "checks")` mirroring the `writable_paths` match at lines 90-97 with the field name in the messages, and a `token_budget` match mirroring `turn_budget` at 112-117 (`"optional field 'token_budget' must be a positive integer"`).

`budget.py`:

```python
GUARD_KINDS: tuple[str, ...] = ("loop_broken", "scope_refused", "symbol_preserved", "command_bounded", "command_timed_out")


class BudgetState(StrEnum):
    WITHIN = "within"
    TURN_EXHAUSTED = "turn_exhausted"
    TOKEN_EXHAUSTED = "token_exhausted"
    DEADLINE_EXHAUSTED = "deadline_exhausted"
    NOT_DECLARED = "not_declared"
    NOT_ENFORCED = "not_enforced"


@dataclass(frozen=True, slots=True)
class Budget:
    turn_limit: int | None = None
    deadline_seconds: float | None = None
    token_limit: int | None = None

    @property
    def declared(self) -> bool:
        return self.turn_limit is not None or self.deadline_seconds is not None or self.token_limit is not None


@dataclass(frozen=True, slots=True)
class BudgetUsage:
    state: BudgetState
    turns_used: int
    seconds_used: float
    tokens_used: int = 0


class TurnCounter:
    """The one counter over the implementer's own stream: turns, assistant
    tokens (input and output; cacheRead excluded), tool calls, guard firings."""

    def __init__(self) -> None:
        self._turns = 0
        self.tokens_in = 0
        self.tokens_out = 0
        self.tool_calls = 0
        self.guard_firings: dict[str, int] = dict.fromkeys(GUARD_KINDS, 0)

    def feed(self, line: str) -> None:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            return
        if not isinstance(event, dict):
            return
        match event.get("type"):
            case "turn_start":
                self._turns += 1
            case "tool_execution_start":
                self.tool_calls += 1
            case "message_end":
                message = event.get("message")
                if isinstance(message, dict) and message.get("role") == "assistant":
                    usage = message.get("usage")
                    if isinstance(usage, dict):
                        self.tokens_in += _count(usage.get("input"))
                        self.tokens_out += _count(usage.get("output"))
            case "entry_appended":
                entry = event.get("entry")
                if isinstance(entry, dict) and entry.get("type") == "custom" and entry.get("customType") in self.guard_firings:
                    self.guard_firings[entry["customType"]] += 1

    @property
    def turns(self) -> int:
        return self._turns


def _count(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def evaluate(budget: Budget, turns_used: int, seconds_used: float, tokens_used: int = 0) -> BudgetUsage:
    if budget.token_limit is not None and tokens_used > budget.token_limit:
        return BudgetUsage(BudgetState.TOKEN_EXHAUSTED, turns_used, seconds_used, tokens_used)
    if budget.turn_limit is not None and turns_used > budget.turn_limit:
        return BudgetUsage(BudgetState.TURN_EXHAUSTED, turns_used, seconds_used, tokens_used)
    if budget.deadline_seconds is not None and seconds_used > budget.deadline_seconds:
        return BudgetUsage(BudgetState.DEADLINE_EXHAUSTED, turns_used, seconds_used, tokens_used)
    if not budget.declared:
        return BudgetUsage(BudgetState.NOT_DECLARED, turns_used, seconds_used, tokens_used)
    return BudgetUsage(BudgetState.WITHIN, turns_used, seconds_used, tokens_used)
```

Delete `_is_turn_start` and `_TURN_START_TYPE`.

`delivery.py`: (a) `_consume_chunk` — after the turn trip at 914 add `if budget.token_limit is not None and counter.tokens_out > budget.token_limit: return pending, BudgetState.TOKEN_EXHAUSTED`. (b) `_StreamOutcome` gains `counter: TurnCounter` (replace its `turns_used: int` field, `delivery.py:886-892`; every `_StreamOutcome(` site passes the counter) so the one counter travels with the outcome; `BudgetUsage` built from it takes `tokens_used=counter.tokens_out`. (c) `deliver` (line 333-341): `Budget(turn_limit if turn_limit is not None else contract.turn_budget, deadline_seconds if ... else contract.deadline_seconds, token_limit if token_limit is not None else contract.token_budget)`. (d) the exhaustion message at 840-857: `detail = {TURN_EXHAUSTED: f"turn limit exhausted after {usage.turns_used} turns", TOKEN_EXHAUSTED: f"token budget exhausted after {usage.tokens_used} output tokens", DEADLINE_EXHAUSTED: f"deadline exhausted after {usage.seconds_used:.0f} seconds"}[exhausted]`; message `f"candidate created; whole-attempt {detail}"` (adjust the existing turn/deadline test strings to this one shape — the only permitted assertion change). `cli.py`: `--token-limit N` beside `--turn-limit` with the same `_positive_int` type and `token_limit=args.token_limit` in the `deliver` call.

- [ ] **Step 4: Pass** — `uv run pytest -q > /tmp/p1-t2.log 2>&1; echo "EXIT: $?"` → 0. `tests/test_stream_implementer.py` constructs `_StreamOutcome`; update those constructions to pass a `TurnCounter()`.

- [ ] **Step 5: Gates and commit**

```bash
just gates; echo "EXIT: $?"
git add -A && git commit -m "Phase 1: contract carries preserve, checks and a token budget; one stream counter for turns, tokens, tool calls and guard firings"
```

---

### Task 3: Derive the contract from the request and the repo (engine)

**Files:**
- Create: `src/satyrn_engine/derive.py`, `tests/test_derive.py`, `tests/test_integration_derive.py`
- Modify: `src/satyrn_engine/cli.py` (`derive` subcommand), `tests/test_check_cli.py`

**Interfaces:**
- Produces: `RepoFacts(tracked: tuple[str, ...], pyproject: str, head: str)`; `DeriveError(message)`; `derive_contract(request: str, facts: RepoFacts, *, token_budget: int = 32000, turn_budget: int = 48) -> Contract`; `render_contract(contract: Contract) -> str` (YAML; `None`-valued keys omitted — M9); `contract_id(request: str, head: str) -> str` (`implement-<sha256(head + "\n" + request)[:12]>`, so the same request at a new HEAD is a new contract and `CANDIDATE_EXISTS` is not tripped by a re-run — M3); `self_test_command(pyproject: str) -> tuple[str, ...]`; CLI `satyrn-engine derive --repo REPO -- REQUEST...` prints the YAML to stdout, writes `<git-dir>/satyrn/contracts/<id>.yaml`, prints `satyrn-engine: contract <path>` to stderr; exit 0, or `CONTRACT_MISSING_FIELD` (5) with `satyrn-engine: DERIVE: <message>`.

Rules (deterministic; the request is the only free input; Ruling 11 on what carries over from HP1):
- `writable_paths`, in order of first mention, deduplicated: a request token that names a tracked file exactly → that file; a tracked directory → `dir/*` (HP1's rendering, `engine_contract.py:33-84`); an untracked path with a `/` whose parent directory is tracked → that exact path (a file the task will create, Ruling 12); for a tracked or new `pkg/mod.py`, `tests/test_mod.py` (or any tracked `*/test_mod.py`) **only when it is not in `preserve`** — every tracked test is in `preserve`, so in practice a test file is writable only when it does not exist yet. Empty → `DeriveError("name at least one tracked file, tracked directory, or new file under a tracked directory in the request")`.
- `test_command`: `[tool.satyrn] self_test` from pyproject when declared (a non-empty list of strings), else `("uv", "run", "python", "-m", "pytest", "-q")`. No pyproject at all → `DeriveError("no pyproject.toml; declare [tool.satyrn] self_test or add one")`.
- `preserve`: tracked paths matching `tests/test_*.py`, `tests/*/test_*.py`, `tests/*_test.py`, `tests/*/*_test.py` (sorted). `checks`: tracked paths under `checks/` (sorted).
- `id`: `contract_id(request, head)`; `task`: the request, stripped. Budgets: the defaults (the spec's campaign budget).

- [ ] **Step 1: Failing tests** (`tests/test_derive.py`)

```python
import pytest

from satyrn_engine.derive import DeriveError, RepoFacts, contract_id, derive_contract, render_contract, self_test_command

TRACKED = ("pyproject.toml", "src/app/cli.py", "src/app/gate.py", "tests/test_cli.py",
           "tests/unit/test_gate.py", "tests/conftest.py", "checks/check_public.py", "docs/x.md")
PYPROJECT = '[project]\nname = "app"\n[dependency-groups]\ndev = ["pytest>=8"]\n'
HEAD = "a" * 40
FACTS = RepoFacts(TRACKED, PYPROJECT, HEAD)


def test_writable_paths_come_from_named_files_and_new_files_never_from_preserved_tests() -> None:
    contract = derive_contract("Add --check to src/app/cli.py", FACTS)
    assert contract.writable_paths == ("src/app/cli.py",)          # tests/test_cli.py exists and is preserved
    assert contract.task == "Add --check to src/app/cli.py"


def test_a_new_module_under_a_tracked_directory_is_writable_with_its_new_test() -> None:
    contract = derive_contract("Create src/app/run_record.py with a gate", FACTS)
    assert contract.writable_paths == ("src/app/run_record.py", "tests/test_run_record.py")


def test_a_named_directory_becomes_a_pattern_and_mentions_deduplicate() -> None:
    contract = derive_contract("Rework tests/ and tests again, and src/app/gate.py", FACTS)
    assert contract.writable_paths == ("tests/*", "src/app/gate.py")


def test_self_test_command_defaults_to_python_m_pytest_and_honours_a_declaration() -> None:
    assert self_test_command(PYPROJECT) == ("uv", "run", "python", "-m", "pytest", "-q")
    declared = PYPROJECT + '[tool.satyrn]\nself_test = ["uv", "run", "pytest", "-q", "-p", "no:cacheprovider"]\n'
    assert self_test_command(declared) == ("uv", "run", "pytest", "-q", "-p", "no:cacheprovider")
    with pytest.raises(DeriveError, match="self_test"):
        self_test_command(PYPROJECT + "[tool.satyrn]\nself_test = 'pytest'\n")


def test_carried_sets_and_budgets_are_derived_from_the_repo() -> None:
    contract = derive_contract("Fix src/app/gate.py", FACTS)
    assert contract.preserve == ("tests/test_cli.py", "tests/unit/test_gate.py")
    assert contract.checks == ("checks/check_public.py",)
    assert (contract.token_budget, contract.turn_budget) == (32000, 48)


def test_a_request_naming_nothing_is_refused() -> None:
    with pytest.raises(DeriveError, match="name at least one tracked file"):
        derive_contract("make it faster", FACTS)


def test_a_repo_without_a_pyproject_is_refused() -> None:
    with pytest.raises(DeriveError, match="pyproject"):
        derive_contract("Fix src/app/gate.py", RepoFacts(TRACKED, "", HEAD))


def test_the_id_is_stable_for_request_and_head_and_moves_with_either() -> None:
    assert contract_id("x", HEAD) == contract_id("x", HEAD)
    assert contract_id("x", HEAD) != contract_id("y", HEAD) != contract_id("y", "b" * 40)
    assert contract_id("x", HEAD).startswith("implement-") and len(contract_id("x", HEAD)) == 22


def test_rendered_yaml_omits_absent_values_and_loads_back_to_the_same_contract(tmp_path) -> None:
    from satyrn_engine.contract import load_contract
    contract = derive_contract("Fix src/app/gate.py", FACTS)
    text = render_contract(contract)
    assert "deadline_seconds" not in text and "null" not in text
    path = tmp_path / "c.yaml"
    path.write_text(text, encoding="utf-8")
    assert load_contract(path) == contract
```

`tests/test_check_cli.py`: `parse_args(["derive", "--repo", ".", "--", "-add", "a", "flag"])` → `request == ["-add", "a", "flag"]` (M4: the `--` keeps a leading dash out of argparse).

- [ ] **Step 2: Run to verify failure** — `uv run pytest tests/test_derive.py -q` → `No module named 'satyrn_engine.derive'`.

- [ ] **Step 3: Implement `derive.py`**

```python
"""Derive a contract from one request and the facts of one repository.

Deterministic and pure: the request is the only free input; every other
value is read from the tracked file list, the pyproject text and HEAD the
CLI hands in. The developer confirms the result; nobody hand-writes it.

Two rules restate HP1's builder in satyrn-evals (engine_contract.py:33-84
and :86-94 at 00c3c18): a directory renders as `dir/*`, and admission is
fnmatch with `*` spanning `/`. Nothing is imported from that tree.
"""

import hashlib
import re
import tomllib
from dataclasses import dataclass
from fnmatch import fnmatch

import yaml

from .contract import Contract

DEFAULT_TOKEN_BUDGET = 32000
DEFAULT_TURN_BUDGET = 48
DEFAULT_SELF_TEST = ("uv", "run", "python", "-m", "pytest", "-q")
_TOKEN = re.compile(r"[A-Za-z0-9_./-]+")
_PRESERVE_PATTERNS = ("tests/test_*.py", "tests/*/test_*.py", "tests/*_test.py", "tests/*/*_test.py")


class DeriveError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass(frozen=True, slots=True)
class RepoFacts:
    tracked: tuple[str, ...]
    pyproject: str
    head: str


def contract_id(request: str, head: str) -> str:
    digest = hashlib.sha256(f"{head}\n{request.strip()}".encode()).hexdigest()
    return f"implement-{digest[:12]}"


def self_test_command(pyproject: str) -> tuple[str, ...]:
    if not pyproject.strip():
        raise DeriveError("no pyproject.toml; declare [tool.satyrn] self_test or add one")
    try:
        declared = tomllib.loads(pyproject).get("tool", {}).get("satyrn", {}).get("self_test")
    except tomllib.TOMLDecodeError as exc:
        raise DeriveError(f"pyproject.toml is not valid TOML: {exc}") from exc
    if declared is None:
        return DEFAULT_SELF_TEST
    if not isinstance(declared, list) or not declared or not all(isinstance(t, str) and t for t in declared):
        raise DeriveError("[tool.satyrn] self_test must be a non-empty list of strings")
    return tuple(declared)


def _directories(tracked: tuple[str, ...]) -> set[str]:
    found: set[str] = set()
    for path in tracked:
        parts = path.split("/")
        found.update("/".join(parts[:depth]) for depth in range(1, len(parts)))
    return found


def _test_for(module: str, tracked: tuple[str, ...]) -> str:
    stem = module.rsplit("/", 1)[-1][:-3]
    return next((p for p in tracked if p.endswith(f"/test_{stem}.py")), f"tests/test_{stem}.py")


def _writable_paths(request: str, tracked: tuple[str, ...], preserve: tuple[str, ...]) -> tuple[str, ...]:
    files, directories = set(tracked), _directories(tracked)
    chosen: list[str] = []
    for raw in _TOKEN.findall(request):
        token = raw if raw in files else raw.strip("./").rstrip("/")
        candidates: list[str] = []
        if token in files:
            candidates.append(token)
        elif token in directories:
            candidates.append(f"{token}/*")
        elif "/" in token and token.rsplit("/", 1)[0] in directories:
            candidates.append(token)                       # a file the task will create
        if candidates and token.endswith(".py"):
            test = _test_for(token, tracked)
            if test not in preserve:
                candidates.append(test)
        chosen.extend(c for c in candidates if c not in chosen)
    if not chosen:
        raise DeriveError("name at least one tracked file, tracked directory, or new file under a tracked directory in the request")
    return tuple(chosen)


def derive_contract(request: str, facts: RepoFacts, *, token_budget: int = DEFAULT_TOKEN_BUDGET,
                    turn_budget: int = DEFAULT_TURN_BUDGET) -> Contract:
    text = request.strip()
    if not text:
        raise DeriveError("the request is empty")
    command = self_test_command(facts.pyproject)
    preserve = tuple(sorted(p for p in facts.tracked if any(fnmatch(p, pat) for pat in _PRESERVE_PATTERNS)))
    checks = tuple(sorted(p for p in facts.tracked if p.startswith("checks/")))
    return Contract(id=contract_id(text, facts.head), task=text,
                    writable_paths=_writable_paths(text, facts.tracked, preserve), test_command=command,
                    turn_budget=turn_budget, preserve=preserve, checks=checks, token_budget=token_budget)


def render_contract(contract: Contract) -> str:
    body = {
        "id": contract.id, "task": contract.task,
        "writable_paths": list(contract.writable_paths), "test_command": list(contract.test_command),
        "preserve": list(contract.preserve), "checks": list(contract.checks),
        "token_budget": contract.token_budget, "turn_budget": contract.turn_budget,
        "deadline_seconds": contract.deadline_seconds,
    }
    return yaml.safe_dump({k: v for k, v in body.items() if v is not None}, sort_keys=False, allow_unicode=True)
```

Walk the three writable tests against this code before running them: "Add --check to src/app/cli.py" → `src/app/cli.py` (its test `tests/test_cli.py` is preserved, so not added). "Create src/app/run_record.py with a gate" → `src/app/run_record.py` (parent `src/app` tracked) plus `tests/test_run_record.py` (untracked, so not preserved). "Rework tests/ and tests again, and src/app/gate.py" → `tests/*`, then `src/app/gate.py` (its test `tests/unit/test_gate.py` is preserved).

- [ ] **Step 4: The CLI subcommand**

In `cli.py` `build_parser`, after `check_parser`:

```python
    derive_parser = subparsers.add_parser("derive", help="derive a contract from a request and the repository",
                                          usage="satyrn-engine derive --repo REPO -- REQUEST...")
    derive_parser.add_argument("--repo", required=True, help="working-tree root of a Git repository")
    derive_parser.add_argument("request", nargs="+", help="the developer's request, as words, after --")
```

In `main`, before the final `check` branch: `if args.command == "derive": return _derive(Path(args.repo), " ".join(args.request))`, with (subprocess is fine here: the CLI path is integration-tier; the pure function is what the default tier tests):

```python
def _derive(repo: Path, request: str) -> int:
    from .derive import DeriveError, RepoFacts, derive_contract, render_contract

    def git(*args: str) -> str:
        return subprocess.run(["git", "-C", os.fspath(repo), *args], check=True, capture_output=True, text=True).stdout

    try:
        tracked = tuple(line for line in git("ls-files").splitlines() if line)
        head = git("rev-parse", "--verify", "HEAD^{commit}").strip()
        git_dir = Path(git("rev-parse", "--path-format=absolute", "--git-dir").strip())
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"satyrn-engine: REPO_UNAVAILABLE: {exc}", file=sys.stderr)
        return int(ExitCode.REPO_UNAVAILABLE)
    pyproject = repo / "pyproject.toml"
    facts = RepoFacts(tracked, pyproject.read_text(encoding="utf-8") if pyproject.is_file() else "", head)
    try:
        contract = derive_contract(request, facts)
    except DeriveError as exc:
        print(f"satyrn-engine: DERIVE: {exc.message}", file=sys.stderr)
        return int(ExitCode.CONTRACT_MISSING_FIELD)
    rendered = render_contract(contract)
    target = git_dir / "satyrn" / "contracts" / f"{contract.id}.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    print(f"satyrn-engine: contract {target}", file=sys.stderr)
    return 0
```

Add `import subprocess` to `cli.py`. `tests/test_integration_derive.py` (marked `integration`): init a git repo with the `TRACKED` files and `PYPROJECT`, commit, run `cli.main(["derive", "--repo", str(repo), "--", "Fix", "src/app/gate.py"])` with `capsys`; assert exit 0, the YAML on stdout, the file under `.git/satyrn/contracts/`, and that the same call again writes the same path (same HEAD); sibling: a request naming nothing → exit 5 and `DERIVE:` on stderr.

- [ ] **Step 5: Pass, gates, record, commit**

```bash
uv run pytest -q > /tmp/p1-t3.log 2>&1; echo "EXIT: $?"
uv run pytest -m integration tests/test_integration_derive.py -q; echo "EXIT: $?"
uv run python tools/provenance.py new src/satyrn_engine/derive.py tests/test_derive.py tests/test_integration_derive.py
just gates; echo "EXIT: $?"
git add -A && git commit -m "Phase 1: derive the contract from the request and the repo; the developer confirms, never hand-writes"
```

---

### Task 4: Compact results and the `self_test` tool with carried tests restored (engine)

**Files:**
- Modify: `src/satyrn_engine/runner.py`, `src/satyrn_engine/protocol.py:72-80,176-185,303-311`, `packages/engine/runner.ts`, `tools/exercise_runner.mjs`, `tests/test_runner.py`, `tests/test_protocol.py`, `tests/test_runner.mjs`, `tests/test_runner_prompt.mjs`, `tests/test_integration_runner.py`, `tests/test_integration_runner_tool.py`

**Interfaces:**
- Produces: `runner.compact_output(text: str) -> str` (pure); `runner.INFRASTRUCTURE = ("pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini")`; `runner.carried_paths(repo, contract, base) -> list[str]` (`preserve + checks + every tracked conftest.py at base (git ls-tree -r --name-only <base> | endswith conftest.py) + INFRASTRUCTURE files tracked at base`); `runner.restore_carried(repo: Path, contract: Contract, base: str) -> tuple[str, ...]` (one `git checkout <base> -- <paths>` for the carried paths present at `base`; returns them); `run_tests(repo, contract, command: str | None, *, base_commit: str | None = None, timeout=120.0)` — `base = base_commit or "HEAD"`; restores carried; runs `test_command`, then `test_command + preserve` when `preserve` is non-empty, then `test_command + checks` when `checks` is non-empty (explicit files bypass `python_files` and `collect_ignore` — N2), all with `COLUMNS=500` in the environment (I6) and **one shared deadline**: each run gets `timeout - elapsed` seconds, so the whole self-test stays under `runner.py:39`'s 120 s (m1); `RunnerResult.output` is the compact form of the runs concatenated, `exit_code` the first non-zero; `protocol.RunTestsRequest.command: str | None` and `base_commit: str | None` (optional, 40 hex when present); TS tool `self_test` with parameters `{type:"object", properties:{command:{type:"string", description:"ignored; the contract's own command always runs"}}, additionalProperties:true}` (Ruling 1); `runner.ts` `SELF_TEST_DEADLINE_MS = 130_000` (the runner's 120 s plus the `uv run satyrn-engine protocol` start; `runner.py:39` owns the number, this is its ceiling — I4); `tools/exercise_runner.mjs CONTEXT.json` (one argument; sends `command: null`).

Reuse: `runner.py:117-179` `run_tests` (subprocess with its own 120 s timeout — kept); `runner.py:93-102` `tail_output`; `runner.ts:196-242`; `orchestrator.ts:19` `DEFAULT_DEADLINE_MS` stays 30 s for `edit`.

Compact rule, against real `pytest -q` output (recorded in scratch with pytest 9.1.1; `-q` prints no `=` fence around the final line): keep every line starting with `FAILED ` or `ERROR ` and the final summary line matching `^=*\s*(\d+ \w+(, )?)+ in [\d.]+s(\s*\(\d+:\d{2}:\d{2}\))?\s*=*$` (fenced or not; pytest appends `(0:01:15)` past 60 s — m7). No such lines → the last 20 lines, so a passing `-q` run keeps its progress dots (m3: the combined expectation below includes the `.` line).

- [ ] **Step 1: Failing tests**

`tests/test_runner.py`:

```python
PYTEST_Q_FAIL = """..F.E                                                                    [100%]
==================================== ERRORS ====================================
_________________________ ERROR at setup of test_err __________________________
    raise RuntimeError("boom")
E   RuntimeError: boom
=================================== FAILURES ===================================
___________________________________ test_two ___________________________________
>       assert 1 == 2, "one is not two"
E       AssertionError: one is not two
E       assert 1 == 2
tests/test_a.py:5: AssertionError
=========================== short test summary info ============================
FAILED tests/test_a.py::test_two - AssertionError: one is not two
ERROR tests/test_a.py::test_err - RuntimeError: boom
1 failed, 1 passed, 1 error in 0.01s
"""


def test_compact_output_keeps_failed_and_error_ids_and_the_summary_line() -> None:
    assert compact_output(PYTEST_Q_FAIL) == (
        "FAILED tests/test_a.py::test_two - AssertionError: one is not two\n"
        "ERROR tests/test_a.py::test_err - RuntimeError: boom\n"
        "1 failed, 1 passed, 1 error in 0.01s\n")


def test_compact_output_finds_a_fenced_summary_too() -> None:
    text = "FAILED t.py::a - x\n========= 1 failed in 0.03s =========\n"
    assert compact_output(text) == "FAILED t.py::a - x\n========= 1 failed in 0.03s =========\n"


def test_compact_output_of_a_passing_run_is_its_tail() -> None:
    text = "\n".join(f"line {i}" for i in range(30)) + "\n"
    assert compact_output(text) == "\n".join(f"line {i}" for i in range(10, 30)) + "\n"


def _contract(**over):
    return Contract(id="x", task="t", test_command=("uv", "run", "python", "-m", "pytest", "-q"), **over)


def _fake_runs(monkeypatch, outputs: dict[tuple[str, ...], tuple[int, bytes]]):
    calls: list[tuple[list[str], dict]] = []

    def fake_run(argv, **kwargs):
        calls.append((list(argv), kwargs))
        code, out = outputs.get(tuple(argv), (0, b""))
        return subprocess.CompletedProcess(argv, code, stdout=out)

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    return calls


BASE = "b" * 40
LS_TREE = b"app.py\npyproject.toml\ntests/conftest.py\ntests/test_keep.py\nchecks/check_x.py\n"


def test_run_tests_restores_the_carried_set_from_base_then_runs_suite_preserve_and_checks(monkeypatch, tmp_path: Path) -> None:
    contract = _contract(preserve=("tests/test_keep.py",), checks=("checks/check_x.py",))
    suite = ("uv", "run", "python", "-m", "pytest", "-q")
    calls = _fake_runs(monkeypatch, {
        ("git", "ls-tree", "-r", "--name-only", BASE): (0, LS_TREE),
        suite: (1, PYTEST_Q_FAIL.encode()),
        (*suite, "tests/test_keep.py"): (0, b".\n1 passed in 0.01s\n"),
        (*suite, "checks/check_x.py"): (0, b".\n1 passed in 0.01s\n"),
    })
    receipt = run_tests(tmp_path, contract, None, base_commit=BASE)
    argvs = [argv for argv, _ in calls]
    assert argvs[0] == ["git", "ls-tree", "-r", "--name-only", BASE]
    assert argvs[1] == ["git", "checkout", BASE, "--", "tests/test_keep.py", "checks/check_x.py", "tests/conftest.py", "pyproject.toml"]
    assert argvs[2:] == [list(suite), [*suite, "tests/test_keep.py"], [*suite, "checks/check_x.py"]]
    assert all(kwargs["env"]["COLUMNS"] == "500" for _, kwargs in calls[2:])
    assert calls[2][1]["timeout"] <= 120.0 and calls[3][1]["timeout"] <= calls[2][1]["timeout"]   # one shared deadline
    assert receipt.ok and receipt.result is not None
    assert receipt.result.exit_code == 1
    assert receipt.result.output == (
        "FAILED tests/test_a.py::test_two - AssertionError: one is not two\n"
        "ERROR tests/test_a.py::test_err - RuntimeError: boom\n"
        "1 failed, 1 passed, 1 error in 0.01s\n"
        ".\n1 passed in 0.01s\n"
        ".\n1 passed in 0.01s\n")


def test_run_tests_skips_carried_paths_absent_at_base_and_defaults_to_head(monkeypatch, tmp_path: Path) -> None:
    contract = _contract(preserve=("tests/test_gone.py",))
    calls = _fake_runs(monkeypatch, {("git", "ls-tree", "-r", "--name-only", "HEAD"): (0, b"app.py\n")})
    receipt = run_tests(tmp_path, contract, None)
    argvs = [argv for argv, _ in calls]
    assert argvs == [["git", "ls-tree", "-r", "--name-only", "HEAD"], list(contract.test_command)]
    assert receipt.ok


def test_run_tests_still_refuses_a_string_command_that_does_not_match(tmp_path: Path) -> None:
    receipt = run_tests(tmp_path, _contract(), "rm -rf /")
    assert receipt.code is RunnerCode.TEST_COMMAND_NOT_ALLOWED and "only this exact command" in receipt.message
```

`tests/test_protocol.py`: add `test_test_request_accepts_a_null_or_absent_command` (both parse to `command=None`) and `test_test_request_carries_an_optional_base_commit` (absent → `None`; 40 hex accepted; anything else `INVALID_REQUEST`).

`tests/test_runner.mjs`: `"test request carries repo, contract, and the model's command"` → asserts `buildTestRequest(context())` gives `{version:1, operation:"test", repo, contract, command:null, base_commit: context().base_commit}`; `"the registered tool schema requires a non-empty command string and nothing else"` → asserts the tool is named `self_test`, `parameters.properties.command.type === "string"`, `parameters.additionalProperties === true`, `required` absent; delete `"a missing or empty command is refused locally as INVALID_REQUEST without an exchange"`; add `"the runner's exchange deadline is above the runner's own 120 s timeout"` asserting `SELF_TEST_DEADLINE_MS === 130_000` and that `runnerExtension` passes it (spy on the `createEngineExchange` call the way `"default extension prepares the production transport from valid context"` at line 223 does).

- [ ] **Step 2: Run to verify failure** — `uv run pytest tests/test_runner.py tests/test_protocol.py -q` and `node --test --experimental-strip-types tests/test_runner.mjs` → failures.

- [ ] **Step 3: Implement**

`runner.py`:

```python
COMPACT_TAIL_LINES = 20
_SUMMARY = re.compile(r"^=*\s*(\d+ \w+(, )?)+ in [\d.]+s\s*=*$")


def compact_output(text: str) -> str:
    """Failed and errored test ids with their first assertion line, plus the summary line."""
    lines = text.splitlines()
    kept = [line for line in lines if line.startswith(("FAILED ", "ERROR "))]
    summary = next((line for line in reversed(lines) if _SUMMARY.match(line)), None)
    if kept:
        return "\n".join([*kept, *([summary] if summary else [])]) + "\n"
    return "\n".join(lines[-COMPACT_TAIL_LINES:]) + ("\n" if lines else "")


INFRASTRUCTURE = ("pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini")
_QUIET = {"stdin": subprocess.DEVNULL, "stdout": subprocess.PIPE, "stderr": subprocess.DEVNULL, "check": False}


def carried_paths(repo: Path, contract: Contract, base: str) -> list[str]:
    """preserve + checks + tracked conftest.py files + tracked pytest config, as they exist at `base`."""
    listed = subprocess.run(["git", "ls-tree", "-r", "--name-only", base], cwd=repo, **_QUIET)
    tracked = set(listed.stdout.decode("utf-8", errors="replace").splitlines()) if listed.returncode == 0 else set()
    wanted = [*contract.preserve, *contract.checks,
              *sorted(p for p in tracked if p == "conftest.py" or p.endswith("/conftest.py")),
              *(p for p in INFRASTRUCTURE if p in tracked)]
    return [p for p in dict.fromkeys(wanted) if p in tracked]


def restore_carried(repo: Path, contract: Contract, base: str) -> tuple[str, ...]:
    """Restore the carried set from the accepted base before every self-test, so edits to it never count."""
    present = carried_paths(repo, contract, base)
    if present:
        subprocess.run(["git", "checkout", base, "--", *present], cwd=repo, **_QUIET)
    return tuple(present)


def _run_once(argv: list[str], repo: Path, timeout: float) -> tuple[int, str, bool, bool]:
    env = {**os.environ, "COLUMNS": "500"}
    try:
        completed = subprocess.run(argv, cwd=repo, shell=False, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, timeout=max(timeout, 0.1), check=False, env=env)
    except subprocess.TimeoutExpired as exc:
        text, truncated = tail_output(exc.output if isinstance(exc.output, bytes) else b"")
        return -1, compact_output(text), truncated, True
    text, truncated = tail_output(completed.stdout)
    return completed.returncode, compact_output(text), truncated, False
```

`run_tests`: signature `command: str | None, *, base_commit: str | None = None, timeout=DEFAULT_TEST_TIMEOUT_SECONDS`; keep the `TEST_COMMAND_UNAVAILABLE` and (for a non-`None` string) `TEST_COMMAND_NOT_ALLOWED` branches; `base = base_commit or "HEAD"`; `restore_carried(repo, contract, base)`; `runs = [list(declared)]` + `[*declared, *contract.preserve]` when `preserve` + `[*declared, *contract.checks]` when `checks`; `started = time.monotonic()`; execute each through `_run_once(argv, repo, timeout - (time.monotonic() - started))` inside the existing `except OSError` → `TEST_COMMAND_UNAVAILABLE`, stopping after the first timed-out run; combine: `exit_code` = first non-zero else 0, `output` = concatenation, `truncated` = any, `timed_out` = any. Add `import os`, `import re`, `import time`.

`protocol.py`: `RunTestsRequest.command: str | None`, `base_commit: str | None`; in `parse_request` for `"test"`: `command = payload.get("command")` (`None` stays, else `_required_string`); `base_commit = payload.get("base_commit")` (`None` stays; else must match `[0-9a-f]{40}` or `ProtocolError("request field 'base_commit' must be null or 40 lowercase hexadecimal characters")`); `handle_protocol` passes `base_commit=request.base_commit` to `run_tests`.

`runner.ts`: `export const SELF_TEST_DEADLINE_MS = 130_000;` tool `name: "self_test"`, `label: "Run the contract's self-test"`, `promptSnippet: "runs the contract's declared self-test command (tests carried from the base are restored first) and returns failed test ids; any argument is ignored"`, `description` accordingly; parameters as in Interfaces; `buildTestRequest(context)` sends `command: null, base_commit: context.base_commit` (the context field is added in Task 5; until then `context.base_commit ?? null`); `createRunner.execute` ignores its input; the `tool_result` listener matches `"self_test"`; `runnerExtension` calls `createEngineExchange(spawn, engineRepo, SELF_TEST_DEADLINE_MS)`. `tools/exercise_runner.mjs`: one argument `CONTEXT.json`; `runner.execute("fixture", {})`; usage line updated.

- [ ] **Step 4: Pass** — `uv run pytest -q > /tmp/p1-t4.log 2>&1; echo "EXIT: $?"` → 0; `node --test --experimental-strip-types tests/test_runner.mjs tests/test_runner_prompt.mjs; echo "EXIT: $?"` → 0; `uv run pytest -m integration tests/test_integration_runner.py tests/test_integration_runner_tool.py -q; echo "EXIT: $?"` → 0 (these drive the real runner in a git fixture; update the tool name, the one-argument `exercise_runner.mjs`, and raw-output assertions to the compact form; add one case where a preserve file is edited in the fixture worktree before the run and is restored by it).

- [ ] **Step 5: Gates and commit**

```bash
just gates; echo "EXIT: $?"
git add -A && git commit -m "Phase 1: self_test restores carried tests, runs the suite and the checks, and returns failed ids with the first assertion line"
```

---

### Task 5: Scope in the mutation context; guard 3 on `write`/`edit`; `write` revisions (engine)

**Files:**
- Create: `packages/engine/paths.ts`, `packages/engine/scope.ts`, `tools/replay_events.mjs`, `tests/test_paths.mjs`, `tests/test_scope.mjs`, `tests/fixtures/events/scope-inside.json`, `tests/fixtures/events/scope-outside.json`, `tests/fixtures/events/scope-traversal.json`, `tests/fixtures/events/scope-absolute-inside.json`, `tests/fixtures/events/scope-carried.json`
- Modify: `packages/engine/mutator.ts:21-26,146-175,283-345` (`MutationContext`, `parseMutationContext`, `createMutator`, `registerMutator`), `packages/engine/engine.ts:291-313`, `src/satyrn_engine/attempt.py:558-576,686-694`, `tests/test_mutator.mjs`, `tests/test_loop_breaker.mjs`, `tests/test_attempt.py`, `Justfile`

**Interfaces:**
- Produces: `MutationContext` gains `writable_paths: readonly string[]`, `test_command: readonly string[]`, `symbols: Readonly<Record<string, readonly string[]>>`, `carried: readonly string[]` (preserve + checks + tracked conftest/pytest-config paths at base, computed by `attempt._prepare` with the same rule as `runner.carried_paths` — m5), `base_commit: string` (40 hex — m6); all required; absence is `MUTATION_CONTEXT_INVALID`. `paths.ts` exports `resolveWorkspacePath(repo: string, raw: string): string | null` (strips a leading `@`, `path.resolve(repo, raw)`, returns the repo-relative POSIX path or `null` when outside the repo) — the **one** path key used by scope, the mutator's revision map and the loop breaker (N3). `scope.ts` exports `admits(patterns, path)` (Python `fnmatch` for `*` and `?`; `*` spans `/`), `registerScope(pi, context)`, default `scopeExtension(pi, environment = process.env)` — registers only when the context parses (Ruling 10). `mutator.ts`: `createMutator(context, exchangeRequest, appendEntry = async () => {})`; the revision map is keyed by `resolveWorkspacePath(context.repo, path)` on read and on write; `Mutator.noteWrite(path, content)` (no-op when the path resolves to `null`); `registerMutator` listens on `tool_result` for `write` (C2). `engine.ts` `noteChange` is called with the resolved path. `tools/replay_events.mjs` (fixture shape below); attempt.py writes the five new context keys.

Refusal texts (guard 3): outside scope — `Path outside the contract's writable paths: <path>. Writable: <p1>, <p2>. Edit one of those, or stop and say which file the task needs.`; a carried path — `<path> is carried from the accepted base and restored before every self-test; edits to it never count. Add new tests beside it instead.` Both recorded as `pi.appendEntry("scope_refused", {toolName, toolCallId, path, carried: bool})`. A `write`/`edit` without a `path` never reaches `tool_call` (Pi validates the schema first, `agent-loop.js:411-413`), so nothing counts path-less calls here; that is Phase 2 census work over `tool_execution_end` errors (I3).

Fixture shape for `tools/replay_events.mjs` (Tasks 5, 6, 7):

```json
{
  "name": "scope-outside",
  "extension": "scope.ts",
  "context": {"version": 1, "repo": "/w", "contract": "/w/c.yaml", "revisions": {},
              "writable_paths": ["src/*"], "test_command": ["uv", "run", "python", "-m", "pytest", "-q"], "symbols": {},
              "carried": ["tests/test_keep.py", "tests/conftest.py"], "base_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"},
  "events": [
    {"type": "tool_call", "toolCallId": "c1", "toolName": "write", "input": {"path": "src/a.py", "content": "x"}, "expect": {"blocked": false}},
    {"type": "tool_call", "toolCallId": "c2", "toolName": "write", "input": {"path": "docs/a.md", "content": "x"},
     "expect": {"blocked": true, "reasonContains": "outside the contract's writable paths"}}
  ],
  "expectedEntries": [{"kind": "scope_refused", "data": {"toolName": "write", "path": "docs/a.md", "carried": false}}]
}
```

The replayer imports `packages/engine/<extension>` and calls its default export as `register(pi, environment, fakeExchange)` with a fake `pi` (`on` records handlers by event; `registerTool` records tools by name; `appendEntry(kind, data)` records entries) and `environment = {SATYRN_MUTATION_CONTEXT: JSON.stringify(context), SATYRN_ENGINE_REPO: "/engine"}`; `fakeExchange` resolves `{version:1, ok:true, code:"OK", message:"", result:{path: <request.path>, sha256:"1".repeat(64), region:""}}` so no `uv run satyrn-engine protocol` is ever spawned under `just gates` (M5). Event types: `tool_call` (feeds every `tool_call` handler; checks `expect.blocked`, `expect.reasonContains`, and `expect.input` deep-equal after mutation), `tool_result` (feeds `tool_result` handlers; checks `expect.contentEndsWith` on the last text block of the returned patch, or that no patch was returned when `expect.patched === false`), `tool_exec` (calls the registered tool named `toolName` with `execute(toolCallId, input)`; checks `expect.code` against `details.code`). Finally `expectedEntries` is compared as a subset match per entry (`kind` equal; every key in `data` equal). A fixture with `"context": null` runs without `SATYRN_MUTATION_CONTEXT` and may assert `"expectedHandlers": {"tool_call": 0}`. Exit 1 with the named mismatch, else 0, printing one JSON line per fixture, like `tools/replay_guards.mjs:87-100`.

- [ ] **Step 1: Failing tests**

`tests/test_scope.mjs`:

```js
import assert from "node:assert/strict";
import test from "node:test";

import scopeExtension, { admits, registerScope } from "../packages/engine/scope.ts";
import { resolveWorkspacePath } from "../packages/engine/paths.ts";
import { parseMutationContext } from "../packages/engine/mutator.ts";

const context = () => parseMutationContext(JSON.stringify({
	version: 1, repo: "/w", contract: "/w/c.yaml", revisions: {},
	writable_paths: ["src/*", "tests/*"], test_command: ["uv", "run", "python", "-m", "pytest", "-q"], symbols: {},
	carried: ["tests/test_keep.py", "tests/conftest.py", "pyproject.toml"], base_commit: "b".repeat(40),
}));

function fakePi() {
	const handlers = {}; const entries = [];
	return { pi: { on(event, h) { (handlers[event] ??= []).push(h); }, registerTool() {}, async appendEntry(kind, data) { entries.push({ kind, data }); } }, handlers, entries };
}

test("admits follows python fnmatch: star spans slashes, exact names match exactly", () => {
	assert.equal(admits(["src/*"], "src/pkg/deep/a.py"), true);
	assert.equal(admits(["tests/test_new.py"], "tests/test_new.py"), true);
	assert.equal(admits(["tests/test_new.py"], "tests/test_old.py"), false);
	assert.equal(admits(["tests/*"], "tests/deep/test_x.py"), true);
	assert.equal(admits(["src/?.py"], "src/a.py"), true);
	assert.equal(admits(["src/*"], "docs/a.md"), false);
});

test("paths are resolved against the repo before matching", () => {
	assert.equal(resolveWorkspacePath("/w", "src/a.py"), "src/a.py");
	assert.equal(resolveWorkspacePath("/w", "@src/a.py"), "src/a.py");
	assert.equal(resolveWorkspacePath("/w", "/w/src/a.py"), "src/a.py");
	assert.equal(resolveWorkspacePath("/w", "./src/../src/a.py"), "src/a.py");
	assert.equal(resolveWorkspacePath("/w", "src/../../etc/x"), null);
	assert.equal(resolveWorkspacePath("/w", "/etc/x"), null);
});

test("a write inside the scope is admitted; outside, traversal and absolute-outside are refused with the writable list", async () => {
	const { pi, handlers, entries } = fakePi();
	registerScope(pi, context());
	const [handler] = handlers.tool_call;
	assert.equal(await handler({ toolCallId: "1", toolName: "write", input: { path: "src/a.py", content: "" } }), undefined);
	assert.equal(await handler({ toolCallId: "2", toolName: "write", input: { path: "/w/src/b.py", content: "" } }), undefined);
	for (const path of ["docs/a.md", "src/../../etc/x", "/etc/passwd"]) {
		const refusal = await handler({ toolCallId: path, toolName: "write", input: { path, content: "" } });
		assert.equal(refusal.block, true);
		assert.match(refusal.reason, /outside the contract's writable paths/);
		assert.match(refusal.reason, /Writable: src\/\*, tests\/\*/);
	}
	assert.equal(entries.length, 3);
	assert.deepEqual(entries[0], { kind: "scope_refused", data: { toolName: "write", toolCallId: "docs/a.md", path: "docs/a.md", carried: false } });
});

test("a carried path inside a writable pattern is refused as carried; a new test beside it is admitted", async () => {
	const { pi, handlers, entries } = fakePi();
	registerScope(pi, context());
	const [handler] = handlers.tool_call;
	for (const path of ["tests/test_keep.py", "@tests/conftest.py", "/w/pyproject.toml"]) {
		const refusal = await handler({ toolCallId: path, toolName: "edit", input: { path, edits: [] } });
		assert.equal(refusal.block, true);
		assert.match(refusal.reason, /carried from the accepted base and restored before every self-test/);
	}
	assert.equal(await handler({ toolCallId: "n", toolName: "write", input: { path: "tests/test_new.py", content: "" } }), undefined);
	assert.deepEqual(entries.at(-1).data, { toolName: "edit", toolCallId: "/w/pyproject.toml", path: "pyproject.toml", carried: true });
});

test("edit paths are checked too; read and bash are not", async () => {
	const { pi, handlers } = fakePi();
	registerScope(pi, context());
	const [handler] = handlers.tool_call;
	assert.equal((await handler({ toolCallId: "1", toolName: "edit", input: { path: "docs/a.md", edits: [] } })).block, true);
	assert.equal(await handler({ toolCallId: "2", toolName: "read", input: { path: "docs/a.md" } }), undefined);
	assert.equal(await handler({ toolCallId: "3", toolName: "bash", input: { command: "cat docs/a.md" } }), undefined);
});

test("the default extension registers nothing without a mutation context", () => {
	const { pi, handlers } = fakePi();
	scopeExtension(pi, {});
	assert.deepEqual(handlers, {});
	const withContext = fakePi();
	scopeExtension(withContext.pi, { SATYRN_MUTATION_CONTEXT: JSON.stringify(context()) });
	assert.equal(withContext.handlers.tool_call.length, 1);
});
```

`tests/test_paths.mjs`: the six `resolveWorkspacePath` rows from `test_scope.mjs` above move here (leave the `test_scope.mjs` import so the file still compiles), plus `resolveWorkspacePath("/w", "@/w/src/a.py") === "src/a.py"`.

`tests/test_mutator.mjs`: extend `context()` at line 17 with the five new keys (`writable_paths: ["src/*"]`, `test_command`, `symbols: {}`, `carried: []`, `base_commit: "b".repeat(40)`); add five refusal rows to `"mutation context refuses malformed JSON and shapes"` (missing `writable_paths`; `symbols` not an object; `test_command` not an array of strings; `carried` missing; `base_commit` not 40 hex); add:

```js
test("a successful native write moves the path's revision so a later edit sends the written digest", async () => {
	const requests = [];
	const mutator = createMutator(context(), async (request) => { requests.push(JSON.parse(request)); return success(); });
	mutator.noteWrite("src/app.py", "def value():\n    return 1\n");
	await mutator.execute("1", input());
	assert.equal(requests[0].expected_sha256, createHash("sha256").update("def value():\n    return 1\n", "utf8").digest("hex"));
});

test("a write by absolute or @ path and an edit by relative path share one revision key", async () => {
	const requests = [];
	const mutator = createMutator(context(), async (request) => { requests.push(JSON.parse(request)); return success(); });
	mutator.noteWrite("/workspace/src/app.py", "x = 1\n");
	await mutator.execute("1", input());
	mutator.noteWrite("@src/app.py", "x = 2\n");
	await mutator.execute("2", input());
	mutator.noteWrite("/elsewhere/app.py", "ignored");   // outside the repo: no key moves
	await mutator.execute("3", input());
	assert.deepEqual(requests.map((r) => r.expected_sha256), [
		createHash("sha256").update("x = 1\n", "utf8").digest("hex"),
		createHash("sha256").update("x = 2\n", "utf8").digest("hex"),
		SECOND_REVISION,   // the mutator's own last success
	]);
});

test("a write result with isError leaves the revision alone, and a new file written then edited is not REVISION_UNAVAILABLE", async () => {
	const requests = [];
	const { pi, handlers } = fakePi();
	registerMutator(pi, context(), async (request) => { requests.push(JSON.parse(request)); return success(); });
	const [result] = handlers.tool_result;
	await result({ toolName: "write", isError: true, input: { path: "src/app.py", content: "junk" }, content: [], details: undefined });
	await result({ toolName: "write", isError: false, input: { path: "src/new.py", content: "x = 1\n" }, content: [], details: undefined });
	const tool = registeredTools(pi).edit;   // the fake pi records registerTool calls
	await tool.execute("1", input());
	await tool.execute("2", { path: "src/new.py", edits: [{ oldText: "x = 1", newText: "x = 2" }] });
	assert.equal(requests[0].expected_sha256, FIRST_REVISION);
	assert.equal(requests[1].expected_sha256, createHash("sha256").update("x = 1\n", "utf8").digest("hex"));
});
```

`tests/test_loop_breaker.mjs`: add `"a successful write result records the content digest as the path's revision"` — feed the `tool_result` handler `{toolName:"write", input:{path:"app.py", content:"one"}, isError:false}` and assert a sixth identical `read app.py` is then admitted, mirroring `"editing a path permits reading it back and re-running the test command"` at line 556.

`tests/test_attempt.py`: the test that asserts the `SATYRN_MUTATION_CONTEXT` JSON (grep `MUTATION_CONTEXT_ENV`) gains `"writable_paths"`, `"test_command"`, `"symbols"` (fixture `app.py` containing `def value(): return 1` and a nested `    def inner(self):` → `{"app.py": ["inner", "value"]}`), `"carried"` (the contract's preserve + checks + tracked `conftest.py`/pytest-config files, from the `ls-files` output `_prepare` already has at 530) and `"base_commit"` (the `head` `_prepare` resolves at 517).

Fixtures: `scope-inside.json` (two writes inside; `expectedEntries: []`), `scope-outside.json` (above), `scope-traversal.json` (`src/../../x` blocked), `scope-absolute-inside.json` (`/w/src/a.py` admitted, `expectedEntries: []`), `scope-carried.json` (an `edit` to `tests/test_keep.py` under `tests/*` blocked with `carried: true`; a `write` to `tests/test_new.py` admitted).

- [ ] **Step 2: Run to verify failure** — `node --test --experimental-strip-types tests/test_scope.mjs` → cannot find module; `node --test --experimental-strip-types tests/test_mutator.mjs` → `noteWrite` is not a function; `uv run pytest tests/test_attempt.py -q` → the context assertion fails.

- [ ] **Step 3: Implement**

`paths.ts` (new; the one path key):

```ts
import { isAbsolute, posix, relative, resolve, sep } from "node:path";

/** Pi resolves tool paths against cwd, strips `@`, and accepts absolute paths
 * (core/tools/path-utils.js:42-44); this does the same and returns the repo-relative
 * POSIX path, or null when the path leaves the repo. Every guard keys by this. */
export function resolveWorkspacePath(repo: string, raw: string): string | null {
	const cleaned = raw.startsWith("@") ? raw.slice(1) : raw;
	const absolute = isAbsolute(cleaned) ? resolve(cleaned) : resolve(repo, cleaned);
	const rel = relative(resolve(repo), absolute);
	if (rel === "" || rel === ".." || rel.startsWith(`..${sep}`) || isAbsolute(rel)) return null;
	return rel.split(sep).join(posix.sep);
}
```

`mutator.ts`: extend `MutationContext` with `readonly writable_paths: readonly string[]; readonly test_command: readonly string[]; readonly symbols: Readonly<Record<string, readonly string[]>>; readonly carried: readonly string[]; readonly base_commit: string;` and `parseMutationContext` with `isStringArray(parsed.writable_paths) && isStringArray(parsed.test_command) && isRecord(parsed.symbols) && Object.values(parsed.symbols).every(isStringArray) && isStringArray(parsed.carried) && typeof parsed.base_commit === "string" && /^[0-9a-f]{40}$/.test(parsed.base_commit)` (`function isStringArray(v: unknown): v is string[] { return Array.isArray(v) && v.every((x) => typeof x === "string"); }`). In `createMutator`, `const key = (p: string) => resolveWorkspacePath(context.repo, p)`; the seed map is `new Map(Object.entries(context.revisions).map(([p, sha]) => [key(p) ?? p, sha]))`; `execute` looks up `revisions.get(key(input.path) ?? input.path)` and stores the success under the same key; `Mutator` gains `noteWrite(path: string, content: string): void` — `const k = key(path); if (k !== null) revisions.set(k, createHash("sha256").update(content, "utf8").digest("hex"))` (`import { createHash } from "node:crypto"`). `createMutator(context, exchangeRequest, appendEntry: (kind: string, data: Record<string, unknown>) => Promise<void> = async () => {})`. `registerMutator` passes `(kind, data) => pi.appendEntry(kind, data)` and adds:

```ts
	pi.on("tool_result", async (event) => {
		if (event.toolName === "write" && event.isError !== true && isRecord(event.input)
			&& typeof event.input.path === "string" && typeof event.input.content === "string") {
			mutator.noteWrite(event.input.path, event.input.content);
		}
		return undefined;
	});
```

(beside the existing `edit` result listener at 339-344; two listeners, each returning `undefined` for the other's tool). `mutationExtension` unchanged in shape.

`scope.ts`:

```ts
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

import { MUTATION_CONTEXT_ENV, parseMutationContext, type MutationContext } from "./mutator.ts";
import { resolveWorkspacePath } from "./paths.ts";

const SCOPED_TOOLS = new Set(["write", "edit"]);

function patternToRegExp(pattern: string): RegExp {
	let source = "";
	for (const char of pattern) {
		if (char === "*") source += ".*";
		else if (char === "?") source += ".";
		else source += char.replace(/[.+^${}()|[\]\\]/g, "\\$&");
	}
	return new RegExp(`^${source}$`, "s");
}

/** Python fnmatch for the two wildcards the engine's contracts use; `*` spans `/`
 * (HP1's admission rule, satyrn-evals engine_contract.py:86-94 @ 00c3c18). */
export function admits(patterns: readonly string[], path: string): boolean {
	return patterns.some((pattern) => patternToRegExp(pattern).test(path));
}

function isRecord(value: unknown): value is Record<string, unknown> {
	return value !== null && typeof value === "object" && !Array.isArray(value);
}

export function registerScope(pi: ExtensionAPI, context: MutationContext): void {
	const carried = new Set(context.carried);
	const refuse = async (event: { toolName: string; toolCallId: string }, path: string, isCarried: boolean, reason: string) => {
		try {
			await pi.appendEntry("scope_refused", { toolName: event.toolName, toolCallId: event.toolCallId, path, carried: isCarried });
		} catch {
			// Telemetry is evidence, not permission.
		}
		return { block: true, reason };
	};
	pi.on("tool_call", async (event) => {
		if (!SCOPED_TOOLS.has(event.toolName) || !isRecord(event.input) || typeof event.input.path !== "string") return undefined;
		const resolved = resolveWorkspacePath(context.repo, event.input.path);
		if (resolved !== null && carried.has(resolved)) {
			return refuse(event, resolved, true,
				`${resolved} is carried from the accepted base and restored before every self-test; edits to it never count. ` +
				"Add new tests beside it instead.");
		}
		if (resolved !== null && admits(context.writable_paths, resolved)) return undefined;
		const shown = resolved ?? event.input.path;
		return refuse(event, shown, false,
			`Path outside the contract's writable paths: ${shown}. ` +
			`Writable: ${context.writable_paths.join(", ")}. ` +
			"Edit one of those, or stop and say which file the task needs.");
	});
}

export default function scopeExtension(pi: ExtensionAPI, environment: Readonly<Record<string, string | undefined>> = process.env): void {
	const contextText = environment[MUTATION_CONTEXT_ENV];
	if (contextText === undefined) return;
	let context: MutationContext;
	try {
		context = parseMutationContext(contextText);
	} catch {
		return;
	}
	registerScope(pi, context);
}
```

`engine.ts` `tool_result` handler (line 291): add a branch — when `event.toolName === "write"`, `event.isError !== true`, and `isRecord(event.input)` with string `path` and `content`: `const key = repo ? resolveWorkspacePath(repo, path) : path; if (key !== null) breaker.noteChange(key, createHash("sha256").update(content, "utf8").digest("hex"))`, and key the existing `edit` branch's `path` the same way; `repo` is `parseMutationContext(environment[MUTATION_CONTEXT_ENV]).repo` when a context parses, else `undefined` (`registerLoopBreaker(pi, environment = process.env)`; without a context the raw path is the key, as today). Also key `workspacePart`'s `path` lookup (engine.ts:111) through the same resolver when `repo` is known, so a `read` by absolute path and a `write` by relative path meet. Add a `test_loop_breaker.mjs` row for that pairing.

`attempt.py`: in `_prepare` (558-574), beside `revisions`, build `symbols[normalized] = _defined_symbols(content)` with

```python
_SYMBOL = re.compile(rb"^[ \t]*(?:async\s+)?(?:def|class)\s+([A-Za-z_]\w*)", re.MULTILINE)


def _defined_symbols(content: bytes) -> list[str]:
    """def/class names at any indentation that the accepted base defines in one file (matches scope.ts/mutator.ts)."""
    return sorted({match.group(1).decode("ascii") for match in _SYMBOL.finditer(content)})
```

(I2: same rule as the TS `definitionLine`, indentation allowed). Also compute `carried = [*contract.preserve, *contract.checks, *sorted(p for p in tracked_paths if p == "conftest.py" or p.endswith("/conftest.py")), *(p for p in INFRASTRUCTURE if p in tracked_paths)]` filtered to tracked paths and deduplicated (import `INFRASTRUCTURE` from `.runner`; `tracked_paths` is the decoded `listed.stdout` at 530). Return `symbols` and `carried` from `_prepare`, add `symbols: dict[str, list[str]]` and `carried: tuple[str, ...]` to `AttemptContext`, and in `_run` (686) add `"writable_paths": list(context.contract.writable_paths)`, `"test_command": list(context.contract.test_command)`, `"symbols": context.symbols`, `"carried": list(context.carried)`, `"base_commit": context.base_commit` to the context JSON. `package.json` is **not** changed (Ruling 10). `Justfile`: `node --test` line gains `tests/test_paths.mjs tests/test_scope.mjs`; new gate line `node --experimental-strip-types tools/replay_events.mjs`.

- [ ] **Step 4: Pass**

`node --test --experimental-strip-types tests/test_paths.mjs tests/test_scope.mjs tests/test_mutator.mjs tests/test_loop_breaker.mjs tests/test_runner.mjs; echo "EXIT: $?"` → 0 (`test_runner.mjs`'s `context()` gains the five keys too). `node --experimental-strip-types tools/replay_events.mjs; echo "EXIT: $?"` → 0 (five fixtures). `uv run pytest -q > /tmp/p1-t5.log 2>&1; echo "EXIT: $?"` → 0. `uv run pytest -m integration tests/test_integration_attempt.py tests/test_integration_mutator.py -q; echo "EXIT: $?"` → 0.

- [ ] **Step 5: Record, gates, commit**

```bash
uv run python tools/provenance.py new packages/engine/paths.ts packages/engine/scope.ts tools/replay_events.mjs \
  tests/test_paths.mjs tests/test_scope.mjs \
  tests/fixtures/events/scope-inside.json tests/fixtures/events/scope-outside.json tests/fixtures/events/scope-carried.json \
  tests/fixtures/events/scope-traversal.json tests/fixtures/events/scope-absolute-inside.json
just gates; echo "EXIT: $?"
git add -A && git commit -m "Phase 1: guard 3 on tool_call for write and edit, resolved against the repo; the mutator learns write revisions; the context carries scope, test command and symbols"
```

---

### Task 6: Symbol preservation for `edit` and `write` (engine)

**Files:**
- Modify: `packages/engine/mutator.ts:64-67,283-323` (`createMutator`), `packages/engine/scope.ts` (`write` symbol check), `packages/engine/orchestrator.ts:81-88` (`AdapterRefusalCode`), `tools/replay_events.mjs` (`tool_exec`, already specified in Task 5 — verify it is implemented), `tests/test_mutator.mjs`, `tests/test_scope.mjs`
- Create: `tests/fixtures/events/symbol-kept.json`, `tests/fixtures/events/symbol-removed.json`, `tests/fixtures/events/symbol-write-kept.json`, `tests/fixtures/events/symbol-write-removed.json`

**Interfaces:**
- Produces: `mutator.removedSymbols(oldText: string, newText: string, defined: readonly string[]): string[]` (pure; also imported by `scope.ts` for `write`, with `oldText` = a synthetic text containing one definition line per base symbol and `newText` = the written `content`); refusal code `SYMBOL_REMOVED` (added to `AdapterRefusalCode` and `MutationToolRefusalCode`); message `this edit would remove \`NAME\`, which the accepted base defines in PATH. Keep the definition and change its body, or add new code beside it.` (for `write`: `this write would remove ...`); entry `symbol_preserved` with `{toolName, path, symbols}`.

Rule: NAME counts as removed when a definition line for it (`/^[ \t]*(?:async\s+)?(?:def|class)\s+NAME\b/m`, same as `attempt._SYMBOL`) is in the old text and not in the new text, and NAME is in `context.symbols[path]`. Renames and deletions are refused; body edits pass; a symbol the base does not define may be removed. For `edit` the check runs in the tool's `execute` before the engine exchange (no process spawned for a refusal); for `write` it runs in `scope.ts`'s `tool_call` handler after the path check, as a block with the same text.

- [ ] **Step 1: Failing tests**

`tests/test_mutator.mjs`:

```js
test("removedSymbols names base-defined symbols whose definition line leaves the text", () => {
	assert.deepEqual(removedSymbols("def value():\n    return 1\n", "def other():\n    return 1\n", ["value"]), ["value"]);
	assert.deepEqual(removedSymbols("def value():\n    return 1\n", "def value():\n    return 2\n", ["value"]), []);
	assert.deepEqual(removedSymbols("class A:\n    pass\n", "", ["A", "B"]), ["A"]);
	assert.deepEqual(removedSymbols("def helper():\n    pass\n", "", ["value"]), []);
	assert.deepEqual(removedSymbols("    def value(self):\n        pass\n", "    pass\n", ["value"]), ["value"]);
});

test("an edit that removes a base symbol is refused without an exchange and recorded; a body edit is not", async () => {
	const calls = []; const entries = [];
	const mutator = createMutator({ ...context(), symbols: { "src/app.py": ["value"] } },
		async (request) => { calls.push(request); return success(); },
		async (kind, data) => { entries.push({ kind, data }); });
	const refused = await mutator.execute("1", { path: "src/app.py", edits: [{ oldText: "def value():\n    return 1", newText: "def renamed():\n    return 1" }] });
	assert.equal(refused.details.code, "SYMBOL_REMOVED");
	assert.match(refused.content[0].text, /would remove `value`, which the accepted base defines in src\/app\.py/);
	assert.equal(calls.length, 0);
	assert.deepEqual(entries, [{ kind: "symbol_preserved", data: { toolName: "edit", path: "src/app.py", symbols: ["value"] } }]);
	const kept = await mutator.execute("2", { path: "src/app.py", edits: [{ oldText: "def value():\n    return 1", newText: "def value():\n    return 2" }] });
	assert.equal(kept.details.ok, true);
	assert.equal(calls.length, 1);
});
```

`tests/test_scope.mjs`:

```js
test("a write that drops a base-defined symbol is refused; a write that keeps every definition line is admitted", async () => {
	const { pi, handlers, entries } = fakePi();
	registerScope(pi, { ...context(), symbols: { "src/a.py": ["value", "Helper"] } });
	const [handler] = handlers.tool_call;
	const dropped = await handler({ toolCallId: "1", toolName: "write", input: { path: "src/a.py", content: "def value():\n    return 2\n" } });
	assert.equal(dropped.block, true);
	assert.match(dropped.reason, /this write would remove `Helper`, which the accepted base defines in src\/a\.py/);
	assert.deepEqual(entries.at(-1), { kind: "symbol_preserved", data: { toolName: "write", path: "src/a.py", symbols: ["Helper"] } });
	const kept = await handler({ toolCallId: "2", toolName: "write", input: { path: "src/a.py", content: "class Helper:\n    pass\n\n\ndef value():\n    return 2\n" } });
	assert.equal(kept, undefined);
	const fresh = await handler({ toolCallId: "3", toolName: "write", input: { path: "src/new.py", content: "x = 1\n" } });
	assert.equal(fresh, undefined);   // no base symbols for a new file
});
```

Fixtures (all with `"extension"` and the Task 5 shape, every context carrying all seven keys incl. `carried: []` and a 40-hex `base_commit`): `symbol-removed.json` — `extension: "mutator.ts"`, context with `symbols: {"src/app.py": ["value"]}`, one `tool_exec` event on `edit` renaming `value`, `expect: {code: "SYMBOL_REMOVED"}`, `expectedEntries: [{"kind":"symbol_preserved","data":{"path":"src/app.py"}}]`; `symbol-kept.json` — the body edit, `expect: {code: "OK"}`, `expectedEntries: []`; `symbol-write-removed.json` — `extension: "scope.ts"`, a `tool_call` `write` dropping `Helper`, `expect: {blocked: true, reasonContains: "would remove `Helper`"}`; `symbol-write-kept.json` — the keeping write, `blocked: false`, `expectedEntries: []`.

- [ ] **Step 2: Run to verify failure** — `node --test --experimental-strip-types tests/test_mutator.mjs tests/test_scope.mjs` → `removedSymbols` is not exported.

- [ ] **Step 3: Implement**

`orchestrator.ts`: add `| "SYMBOL_REMOVED"` to `AdapterRefusalCode`. `mutator.ts`:

```ts
function definitionLine(name: string): RegExp {
	return new RegExp(`^[ \\t]*(?:async\\s+)?(?:def|class)\\s+${name}\\b`, "m");
}

/** Base-defined symbols whose definition line is in oldText and absent from newText. */
export function removedSymbols(oldText: string, newText: string, defined: readonly string[]): string[] {
	return defined.filter((name) => definitionLine(name).test(oldText) && !definitionLine(name).test(newText));
}

export function symbolRefusalText(verb: "edit" | "write", name: string, path: string): string {
	return `this ${verb} would remove \`${name}\`, which the accepted base defines in ${path}. ` +
		"Keep the definition and change its body, or add new code beside it.";
}
```

In `createMutator.execute`, after `const input = parseEditInput(rawInput);`:

```ts
				const removed = removedSymbols(input.edits[0].oldText, input.edits[0].newText, context.symbols[input.path] ?? []);
				if (removed.length > 0) {
					try { await appendEntry("symbol_preserved", { toolName: "edit", path: input.path, symbols: removed }); } catch { /* evidence, not permission */ }
					return refusalResult("SYMBOL_REMOVED", symbolRefusalText("edit", removed[0], input.path));
				}
```

Add `"SYMBOL_REMOVED"` to `MutationToolRefusalCode`. `scope.ts`: import `removedSymbols, symbolRefusalText`; in the `tool_call` handler, after the admission check passes and only for `write` with string `content`: `const defined = context.symbols[resolved] ?? []; const synthetic = defined.map((n) => \`def ${n}():\n\`).join(""); const removed = removedSymbols(synthetic, event.input.content, defined);` — if non-empty, `appendEntry("symbol_preserved", {toolName: "write", path: resolved, symbols: removed})` and `return { block: true, reason: symbolRefusalText("write", removed[0], resolved) }`. (`definitionLine` matches `def NAME` or `class NAME` in either text, so the synthetic `def` lines stand for both kinds.)

- [ ] **Step 4: Pass** — `node --test --experimental-strip-types tests/test_mutator.mjs tests/test_scope.mjs; echo "EXIT: $?"` → 0; `node --experimental-strip-types tools/replay_events.mjs; echo "EXIT: $?"` → 0 (eight fixtures).

- [ ] **Step 5: Record, gates, commit**

```bash
uv run python tools/provenance.py new tests/fixtures/events/symbol-kept.json tests/fixtures/events/symbol-removed.json \
  tests/fixtures/events/symbol-write-kept.json tests/fixtures/events/symbol-write-removed.json
just gates; echo "EXIT: $?"
git add -A && git commit -m "Phase 1: an edit or write that removes a base-defined symbol is refused with what to do instead"
```

---

### Task 7: Guard 4 — bound native bash through Pi's own timeout (engine)

**Files:**
- Create: `packages/engine/bounds.ts`, `tests/test_bounds.mjs`, `tests/fixtures/events/bounds-absent.json`, `tests/fixtures/events/bounds-clamped.json`, `tests/fixtures/events/bounds-kept.json`, `tests/fixtures/events/bounds-result-sentence.json`, `tests/fixtures/events/bounds-timed-out.json`, `tests/fixtures/events/bounds-no-context.json`
- Modify: `Justfile`

**Interfaces:**
- Produces: `bounds.ts` exports `DEFAULT_TIMEOUT_SECONDS = 120`, `MAX_TIMEOUT_SECONDS = 300`, `boundTimeout(requested: unknown): { timeout: number; action: "set" | "clamped" | "kept" }` (pure), `bashSentence(seconds: number, testCommand: readonly string[]): string`, `registerBounds(pi, testCommand: readonly string[]): void`, default `boundsExtension(pi, environment = process.env)` — registers **only** when the mutation context parses (Ruling 10); entries `command_bounded` `{toolCallId, action, timeout}` for `set`/`clamped`, and `command_timed_out` `{toolCallId, timeout}` when a bash result's text contains `Command timed out after` (Pi's own message, `core/tools/bash.js:238-260` — M10; this is the pathology-4 evidence).

Rule (Pi 0.85.1): on `tool_call` for `bash`, `input.timeout` is seconds, optional, no default; Pi's `Value.Convert` has already coerced a numeric string, so a string never arrives live (M16 — the test row stays as a pure-function case). Absent, non-finite or ≤ 0 → 120 (`set`); > 300 → 300 (`clamped`); else untouched (`kept`). Mutate in place; never block. On `tool_result` for `bash`, return a patched `content` whose last text block gains one sentence: `Commands here are bounded at N seconds; on timeout Pi kills the process group. The self-test is "<cmd>"; run it with the self_test tool.` N is the effective bound recorded at `tool_call` for that `toolCallId`.

**Freeze gate.** Before writing the constants, read `/Users/pauleveritt/projects/pauleveritt/satyrn-evals/scripts/suite_durations.json` (Task 1). Its `fit_failures` is `[]` if this task is running at all (Global Constraints: phase stop); if it is not, stop here.

- [ ] **Step 1: Failing tests** (`tests/test_bounds.mjs`)

```js
import assert from "node:assert/strict";
import test from "node:test";

import boundsExtension, { DEFAULT_TIMEOUT_SECONDS, MAX_TIMEOUT_SECONDS, bashSentence, boundTimeout, registerBounds } from "../packages/engine/bounds.ts";

const CONTEXT = JSON.stringify({ version: 1, repo: "/w", contract: "/w/c.yaml", revisions: {},
	writable_paths: ["src/*"], test_command: ["uv", "run", "python", "-m", "pytest", "-q"], symbols: {},
	carried: [], base_commit: "b".repeat(40) });
const CMD = ["uv", "run", "python", "-m", "pytest", "-q"];

function fakePi() {
	const handlers = {}; const entries = [];
	return { pi: { on(event, h) { (handlers[event] ??= []).push(h); }, registerTool() {}, async appendEntry(kind, data) { entries.push({ kind, data }); } }, handlers, entries };
}

test("the frozen values are 120 and 300", () => {
	assert.equal(DEFAULT_TIMEOUT_SECONDS, 120);
	assert.equal(MAX_TIMEOUT_SECONDS, 300);
});

test("boundTimeout sets an absent or bad value, clamps a large one, keeps a sane one", () => {
	assert.deepEqual(boundTimeout(undefined), { timeout: 120, action: "set" });
	assert.deepEqual(boundTimeout(0), { timeout: 120, action: "set" });
	assert.deepEqual(boundTimeout(-5), { timeout: 120, action: "set" });
	assert.deepEqual(boundTimeout("60"), { timeout: 120, action: "set" });   // cannot occur live: Pi coerces numeric strings first
	assert.deepEqual(boundTimeout(Number.POSITIVE_INFINITY), { timeout: 120, action: "set" });
	assert.deepEqual(boundTimeout(900), { timeout: 300, action: "clamped" });
	assert.deepEqual(boundTimeout(300), { timeout: 300, action: "kept" });
	assert.deepEqual(boundTimeout(60), { timeout: 60, action: "kept" });
});

test("a bash call without a timeout has one after the handler, clamps record an entry, kept records none, and nothing is blocked", async () => {
	const { pi, handlers, entries } = fakePi();
	registerBounds(pi, CMD);
	const absent = { toolCallId: "1", toolName: "bash", input: { command: "find / -name x" } };
	assert.equal(await handlers.tool_call[0](absent), undefined);
	assert.equal(absent.input.timeout, 120);
	const big = { toolCallId: "2", toolName: "bash", input: { command: "sleep 1", timeout: 900 } };
	await handlers.tool_call[0](big);
	assert.equal(big.input.timeout, 300);
	const sane = { toolCallId: "3", toolName: "bash", input: { command: "sleep 1", timeout: 45 } };
	await handlers.tool_call[0](sane);
	assert.equal(sane.input.timeout, 45);
	assert.deepEqual(entries, [
		{ kind: "command_bounded", data: { toolCallId: "1", action: "set", timeout: 120 } },
		{ kind: "command_bounded", data: { toolCallId: "2", action: "clamped", timeout: 300 } },
	]);
});

test("other tools are untouched", async () => {
	const { pi, handlers } = fakePi();
	registerBounds(pi, []);
	const event = { toolCallId: "1", toolName: "read", input: { path: "a" } };
	assert.equal(await handlers.tool_call[0](event), undefined);
	assert.deepEqual(event.input, { path: "a" });
});

test("the bash result gains exactly one sentence naming the bound and the self-test; a timeout is recorded", async () => {
	const { pi, handlers, entries } = fakePi();
	registerBounds(pi, CMD);
	await handlers.tool_call[0]({ toolCallId: "1", toolName: "bash", input: { command: "ls" } });
	const patch = await handlers.tool_result[0]({ toolCallId: "1", toolName: "bash", input: { command: "ls", timeout: 120 }, isError: false,
		content: [{ type: "text", text: "a\nb\n" }], details: {} });
	assert.deepEqual(patch, { content: [{ type: "text", text: "a\nb\n\n" + bashSentence(120, CMD) }] });
	assert.equal(bashSentence(120, CMD),
		'Commands here are bounded at 120 seconds; on timeout Pi kills the process group. The self-test is "uv run python -m pytest -q"; run it with the self_test tool.');
	assert.equal(bashSentence(300, []), "Commands here are bounded at 300 seconds; on timeout Pi kills the process group.");
	await handlers.tool_call[0]({ toolCallId: "2", toolName: "bash", input: { command: "find /" } });
	await handlers.tool_result[0]({ toolCallId: "2", toolName: "bash", input: { command: "find /", timeout: 120 }, isError: true,
		content: [{ type: "text", text: "partial\n\nCommand timed out after 120 seconds" }], details: {} });
	assert.deepEqual(entries.at(-1), { kind: "command_timed_out", data: { toolCallId: "2", timeout: 120 } });
	assert.equal(await handlers.tool_result[0]({ toolCallId: "9", toolName: "read", content: [], details: {} }), undefined);
});

test("the default extension registers nothing without a mutation context and both handlers with one", () => {
	const bare = fakePi();
	boundsExtension(bare.pi, {});
	assert.deepEqual(bare.handlers, {});
	const child = fakePi();
	boundsExtension(child.pi, { SATYRN_MUTATION_CONTEXT: CONTEXT });
	assert.equal(child.handlers.tool_call.length, 1);
	assert.equal(child.handlers.tool_result.length, 1);
});
```

Fixtures (`"extension": "bounds.ts"`, context as above): `bounds-absent.json` — `find / -name x` without `timeout`; `expect: {blocked: false, input: {command: "find / -name x", timeout: 120}}`; `expectedEntries: [{"kind":"command_bounded","data":{"action":"set","timeout":120}}]`. `bounds-clamped.json` — `timeout: 900` → `300`, entry `clamped`. `bounds-kept.json` — `timeout: 45` unchanged, `expectedEntries: []`. `bounds-result-sentence.json` — a `tool_call` then a `tool_result` for the same id with `expect: {contentEndsWith: "run it with the self_test tool."}`. `bounds-timed-out.json` — a `tool_result` whose text contains `Command timed out after 120 seconds`, `expectedEntries` includes `command_timed_out`. `bounds-no-context.json` — `"context": null`, `"expectedHandlers": {"tool_call": 0, "tool_result": 0}`.

- [ ] **Step 2: Run to verify failure** — `node --test --experimental-strip-types tests/test_bounds.mjs` → cannot find module.

- [ ] **Step 3: Implement `bounds.ts`**

```ts
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

import { MUTATION_CONTEXT_ENV, parseMutationContext } from "./mutator.ts";

/**
 * Guard 4: an unbounded command. Two `depth-3` ceiling cells spent 843 s and
 * 861 s inside one `find /` (scan_table.md, cells A1 and A4). Pi's bash tool
 * takes `timeout` in seconds with no default and kills the process group on
 * expiry (pi-bash-bounding.md §2); this guard only sets or clamps that field.
 * Frozen against scripts/suite_durations.json in satyrn-evals: 120 s is at
 * least twice the longest measured public suite; 300 s is twice the default.
 * Active only inside the /implement child (mutation context present).
 */
export const DEFAULT_TIMEOUT_SECONDS = 120;
export const MAX_TIMEOUT_SECONDS = 300;
const TIMED_OUT = "Command timed out after";

export type BoundAction = "set" | "clamped" | "kept";

export function boundTimeout(requested: unknown): { timeout: number; action: BoundAction } {
	if (typeof requested !== "number" || !Number.isFinite(requested) || requested <= 0) {
		return { timeout: DEFAULT_TIMEOUT_SECONDS, action: "set" };
	}
	if (requested > MAX_TIMEOUT_SECONDS) return { timeout: MAX_TIMEOUT_SECONDS, action: "clamped" };
	return { timeout: requested, action: "kept" };
}

export function bashSentence(seconds: number, testCommand: readonly string[]): string {
	const bound = `Commands here are bounded at ${seconds} seconds; on timeout Pi kills the process group.`;
	if (testCommand.length === 0) return bound;
	return `${bound} The self-test is "${testCommand.join(" ")}"; run it with the self_test tool.`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
	return value !== null && typeof value === "object" && !Array.isArray(value);
}

export function registerBounds(pi: ExtensionAPI, testCommand: readonly string[]): void {
	const bounded = new Map<string, number>();
	const note = async (kind: string, data: Record<string, unknown>): Promise<void> => {
		try { await pi.appendEntry(kind, data); } catch { /* evidence, not permission */ }
	};
	pi.on("tool_call", async (event) => {
		if (event.toolName !== "bash" || !isRecord(event.input)) return undefined;
		const { timeout, action } = boundTimeout(event.input.timeout);
		event.input.timeout = timeout;
		bounded.set(event.toolCallId, timeout);
		if (action !== "kept") await note("command_bounded", { toolCallId: event.toolCallId, action, timeout });
		return undefined;
	});
	pi.on("tool_result", async (event) => {
		if (event.toolName !== "bash") return undefined;
		const seconds = bounded.get(event.toolCallId) ?? DEFAULT_TIMEOUT_SECONDS;
		bounded.delete(event.toolCallId);
		const content = Array.isArray(event.content) ? [...event.content] : [];
		const last = content.length > 0 ? content[content.length - 1] : undefined;
		if (isRecord(last) && last.type === "text" && typeof last.text === "string") {
			if (last.text.includes(TIMED_OUT)) await note("command_timed_out", { toolCallId: event.toolCallId, timeout: seconds });
			content[content.length - 1] = { ...last, text: `${last.text}\n\n${bashSentence(seconds, testCommand)}` };
		} else {
			content.push({ type: "text", text: bashSentence(seconds, testCommand) });
		}
		return { content };
	});
}

export default function boundsExtension(pi: ExtensionAPI, environment: Readonly<Record<string, string | undefined>> = process.env): void {
	const contextText = environment[MUTATION_CONTEXT_ENV];
	if (contextText === undefined) return;
	try {
		registerBounds(pi, parseMutationContext(contextText).test_command);
	} catch {
		// No context, no guard: the developer's own session is not the /implement child.
	}
}
```

`Justfile` `node --test` line gains `tests/test_bounds.mjs`. `package.json` is not changed.

- [ ] **Step 4: Pass** — `node --test --experimental-strip-types tests/test_bounds.mjs; echo "EXIT: $?"` → 0; `node --experimental-strip-types tools/replay_events.mjs; echo "EXIT: $?"` → 0 (fourteen fixtures).

- [ ] **Step 5: Record, gates, commit**

```bash
uv run python tools/provenance.py new packages/engine/bounds.ts tests/test_bounds.mjs \
  tests/fixtures/events/bounds-absent.json tests/fixtures/events/bounds-clamped.json tests/fixtures/events/bounds-kept.json \
  tests/fixtures/events/bounds-result-sentence.json tests/fixtures/events/bounds-timed-out.json tests/fixtures/events/bounds-no-context.json
just gates; echo "EXIT: $?"
git add -A && git commit -m "Phase 1: guard 4 sets or clamps Pi's bash timeout (120/300, frozen against measured suites) inside the /implement child only"
```

---

### Task 8: Validation with carried tests restored, and the receipt (engine)

**Files:**
- Modify: `src/satyrn_engine/delivery.py` (`DeliveryPayload` 129-158, `DeliveryReceipt` 242-311, `_DeliveryContext` 196-205, `_run_and_commit` 617-760 incl. `git add -A` at 740, `_validate_candidate` 1165-1250, `_checkout_candidate` 1125-1142), `tests/test_delivery.py`, `tests/test_delivery_failures.py`, `tests/fixtures/delivery/receipt-*.json`, `tests/test_integration_delivery.py`

**Interfaces:**
- Produces: receipt payload gains, after `budget`: `"turns": int`, `"tool_calls": int`, `"tokens_in": int`, `"tokens_out": int`, `"guard_firings": {kind: int for kind in budget.GUARD_KINDS}`, `"carried": {"preserve": [...], "checks": [...], "infrastructure": [...], "absent": [...], "tampered": [...]}` (restored at validation / absent at base / carried paths the candidate commit changed or added, N2); `budget` gains `"token_limit": int | None`, `"tokens_used": int`; `DeliveryReceipt` gains `turns=0, tool_calls=0, tokens_in=0, tokens_out=0, guard_firings: GuardFirings = GuardFirings(), carried: Carried = Carried()`; `delivery.GuardFirings` (frozen dataclass with one int per kind, `from_counter(counter: TurnCounter)`, `payload()`); `delivery.Carried(preserve, checks, infrastructure, absent, tampered)`; `delivery.restore_carried_at(worktree, environment, base_commit, contract, changed_paths) -> Carried` (the carried set is `runner.carried_paths`'s rule over `git ls-tree -r --name-only <base>`; one `git checkout <base> -- <present...>`; `tampered` = carried paths in `changed_paths` plus any `changed_paths` entry named `conftest.py` or ending `/conftest.py` or in `runner.INFRASTRUCTURE`); `delivery.count_spool(spool: BinaryIO) -> TurnCounter` (`seek(0)`, then feeds the finished spool — an anonymous `tempfile.TemporaryFile`, `delivery.py:624`, so a handle, not a path — through the one counter; used only when no budget was declared — Ruling 13, m2); `_run_and_commit` stages with `git add -A -- . ':(exclude,glob)**/.venv/**' ':(exclude,glob)**/.pytest_cache/**' ':(exclude,glob)**/__pycache__/**'` (N1: verified exit 0 on git 2.45.1 with `.venv` globally ignored; the earlier `:!` form exited 1 on an ignored `.venv` and did not exclude nested `__pycache__`); `_validate_candidate` runs `test_command`, then `test_command + preserve` when non-empty, then `test_command + checks` when non-empty, each with `COLUMNS=500`, exit = first non-zero, output = the tails concatenated.

Reuse: `_stream_implementer` (919) already owns the live `TurnCounter` when a budget is declared; `_validate_candidate` runs the command on the checked-out candidate; `_run_test_command` (1079) gains an `extra_env` parameter for `COLUMNS`.

- [ ] **Step 1: Failing tests**

`tests/test_delivery.py`:

```python
def test_guard_firings_come_from_the_counter_and_render_every_kind() -> None:
    counter = TurnCounter()
    for kind in ("loop_broken", "command_bounded", "command_bounded"):
        counter.feed(json.dumps({"type": "entry_appended", "entry": {"type": "custom", "customType": kind, "data": {}}}))
    firings = delivery.GuardFirings.from_counter(counter)
    assert firings == delivery.GuardFirings(loop_broken=1, command_bounded=2)
    assert firings.payload() == {"loop_broken": 1, "scope_refused": 0, "symbol_preserved": 0, "command_bounded": 2, "command_timed_out": 0}


def test_count_spool_feeds_a_finished_stream_through_the_one_counter() -> None:
    with tempfile.TemporaryFile() as spool:
        spool.write(b'{"type":"turn_start"}\n{"type":"message_end","message":{"role":"assistant","usage":{"input":7,"output":9}}}\n')
        counter = delivery.count_spool(spool)
    assert (counter.turns, counter.tokens_in, counter.tokens_out) == (1, 7, 9)


def test_receipt_payload_carries_counts_firings_and_carried_sets() -> None:
    payload = _receipt(DeliveryCode.OK).payload()
    assert (payload["turns"], payload["tool_calls"], payload["tokens_in"], payload["tokens_out"]) == (0, 0, 0, 0)
    assert payload["guard_firings"] == dict.fromkeys(GUARD_KINDS, 0)
    assert payload["carried"] == {"preserve": [], "checks": [], "infrastructure": [], "absent": [], "tampered": []}
    assert payload["budget"]["token_limit"] is None and payload["budget"]["tokens_used"] == 0
```

Extend the validation tests at `tests/test_delivery.py:239-415` (they stub `_run_test_command` via `_stub_validation_run`): add `test_validation_restores_the_carried_set_then_runs_suite_preserve_and_checks` — a `_validation_context` whose contract has `preserve=("tests/test_keep.py",)`, `checks=("checks/check_x.py", "checks/absent.py")`; stub `_git` to answer `ls-tree -r --name-only <base>` with `app.py\npyproject.toml\ntests/conftest.py\ntests/test_keep.py\nchecks/check_x.py\n` and record argv; `changed_paths=("app.py", "tests/conftest.py", "tests/test_keep.py")`; assert the `checkout <base> -- tests/test_keep.py checks/check_x.py tests/conftest.py pyproject.toml` call, then three `_run_test_command` calls (`test_command`, `+ ("tests/test_keep.py",)`, `+ ("checks/check_x.py",)`) with `extra_env == {"COLUMNS": "500"}`, and `receipt.carried == Carried(("tests/test_keep.py",), ("checks/check_x.py",), ("tests/conftest.py", "pyproject.toml"), ("checks/absent.py",), ("tests/conftest.py", "tests/test_keep.py"))`. Sibling: a contract with neither preserve nor checks in a repo with no conftest or config runs one command and `carried == Carried()`.

Regenerate the five `tests/fixtures/delivery/receipt-*.json` in payload order (`test_receipt_matches_committed_fixture` compares bytes): `...,"budget":{...,"token_limit":null,"tokens_used":0},"turns":0,"tool_calls":0,"tokens_in":0,"tokens_out":0,"guard_firings":{...},"carried":{"preserve":[],"checks":[],"infrastructure":[],"absent":[],"tampered":[]}}`.

`tests/test_integration_delivery.py`, three rows:
- `test_validation_runs_with_the_carried_set_restored_and_checks_as_files` — fixture repo committed with `pyproject.toml` (`[tool.pytest.ini_options]\naddopts = "-p no:cacheprovider"\n`), `tests/conftest.py` (`@pytest.fixture def two(): return 2`), `tests/test_keep.py` using `two`, `checks/check_x.py` with one passing test, and a `.gitignore` listing `.venv/` (N1); contract `test_command: [python, -m, pytest, -q]`, `preserve: [tests/test_keep.py]`, `checks: [checks/check_x.py]`; the attempt command is a shell-free Python script that (1) appends a line to `app.py`, (2) overwrites `tests/test_keep.py` with `def test_keep(): assert False`, (3) creates `.venv/marker`, `__pycache__/x.pyc` and `tests/__pycache__/y.pyc`. Assert `code == "OK"`, `validation == "passed"` (the restored `test_keep.py` ran with the conftest fixture; the overwritten version never counted), `validation_output` contains `passed` three times (suite, preserve file, check file), `changed_paths == ["app.py", "tests/test_keep.py"]` (m4: the model's overwrite is in the candidate and no residue is; validation is authoritative regardless), and `carried == Carried(("tests/test_keep.py",), ("checks/check_x.py",), ("tests/conftest.py", "pyproject.toml"), (), ("tests/test_keep.py",))`.
- `test_a_written_conftest_cannot_hide_a_failing_preserve_test` (N2) — same fixture but `tests/test_keep.py` at base asserts something the attempt breaks in `app.py`; the attempt script writes `tests/conftest.py` with `collect_ignore = ["test_keep.py"]` and edits `pyproject.toml` `addopts` to `"--deselect tests/test_keep.py"`. Assert `code == "TESTS_FAILED"`, `validation == "failed"`, `"FAILED tests/test_keep.py" in validation_output`, `carried.tampered == ("pyproject.toml", "tests/conftest.py")`.
- `test_a_gitignored_venv_does_not_fail_staging` (N1) — the first fixture with the maintainer's real global git config in effect (do **not** set `GIT_CONFIG_GLOBAL`), the attempt creates `.venv/bin/python`; assert `code == "OK"` and `".venv/bin/python" not in changed_paths`. Sibling: a preserve path absent at base lands in `carried.absent` and validation still runs.

- [ ] **Step 2: Run to verify failure** — `uv run pytest tests/test_delivery.py -q` → `GuardFirings` missing.

- [ ] **Step 3: Implement**

```python
@dataclass(frozen=True, slots=True)
class GuardFirings:
    loop_broken: int = 0
    scope_refused: int = 0
    symbol_preserved: int = 0
    command_bounded: int = 0
    command_timed_out: int = 0

    @classmethod
    def from_counter(cls, counter: TurnCounter) -> GuardFirings:
        return cls(**{kind: counter.guard_firings[kind] for kind in GUARD_KINDS})

    def payload(self) -> dict[str, int]:
        return {kind: getattr(self, kind) for kind in GUARD_KINDS}


@dataclass(frozen=True, slots=True)
class Carried:
    preserve: tuple[str, ...] = ()
    checks: tuple[str, ...] = ()
    infrastructure: tuple[str, ...] = ()
    absent: tuple[str, ...] = ()
    tampered: tuple[str, ...] = ()

    def payload(self) -> dict[str, list[str]]:
        return {name: list(getattr(self, name)) for name in ("preserve", "checks", "infrastructure", "absent", "tampered")}


def count_spool(spool: BinaryIO) -> TurnCounter:
    """Feed a finished spool (an anonymous temporary file) through the one counter."""
    counter = TurnCounter()
    spool.seek(0)
    for raw in spool:
        counter.feed(raw.decode("utf-8", errors="replace").rstrip("\n"))
    return counter


def _is_infrastructure(path: str) -> bool:
    return path == "conftest.py" or path.endswith("/conftest.py") or path in INFRASTRUCTURE


def restore_carried_at(worktree: Path, environment: dict[str, str], base_commit: str, contract: Contract,
                       changed_paths: tuple[str, ...]) -> Carried:
    """Restore the carried set from the accepted base into the validation checkout; name what the candidate touched."""
    listed = _git(worktree, environment, "ls-tree", "-r", "--name-only", base_commit)
    tracked = set(listed.stdout.decode("utf-8", errors="replace").splitlines()) if listed.returncode == 0 else set()
    preserve = tuple(p for p in contract.preserve if p in tracked)
    checks = tuple(p for p in contract.checks if p in tracked)
    infrastructure = tuple(p for p in (*sorted(p for p in tracked if p == "conftest.py" or p.endswith("/conftest.py")),
                                       *(p for p in INFRASTRUCTURE if p in tracked)) if p not in preserve and p not in checks)
    absent = tuple(p for p in (*contract.preserve, *contract.checks) if p not in tracked)
    restore = [*preserve, *checks, *infrastructure]
    if restore:
        _git(worktree, environment, "checkout", base_commit, "--", *restore)
    carried = set(restore)
    tampered = tuple(sorted(p for p in changed_paths if p in carried or _is_infrastructure(p)))
    return Carried(preserve, checks, infrastructure, absent, tampered)
```

(`INFRASTRUCTURE` imported from `.runner`; `BinaryIO` from `typing`.) Wire: `_DeliveryContext` gains `contract: Contract | None` (set in `deliver`). `_run_and_commit`: the stage call becomes `_git(state.worktree, context.environment, "add", "-A", "--", ".", ":(exclude,glob)**/.venv/**", ":(exclude,glob)**/.pytest_cache/**", ":(exclude,glob)**/__pycache__/**")`; after the command exits, `counter = stream.counter if context.budget.declared else count_spool(output)` where `output` is the `tempfile.TemporaryFile` spool at 624 (one variable, the one counter) and pass `turns=counter.turns, tool_calls=counter.tool_calls, tokens_in=counter.tokens_in, tokens_out=counter.tokens_out, guard_firings=GuardFirings.from_counter(counter)` through `_context_receipt` (new keyword parameters with zero defaults) into `DeliveryReceipt`. `_validate_candidate`: after `_checkout_candidate`, `carried = restore_carried_at(state.worktree, context.environment, context.base_commit, context.contract, pending.changed_paths or ())` and set it on the receipt; run `test_command` with `extra_env={"COLUMNS": "500"}`; then `(*test_command, *carried.preserve)` when non-empty; then `(*test_command, *carried.checks)` when non-empty; exit = first non-zero, output = the tails joined by `"\n"`. `payload()` emits the new keys after `budget` in Interfaces order; `budget` adds `"token_limit"` and `"tokens_used"`. Validation output stays the tail (`tail_output`) — the receipt is not the model's view; compactness is the tool's.

- [ ] **Step 4: Pass** — `uv run pytest -q > /tmp/p1-t8.log 2>&1; echo "EXIT: $?"` → 0; `uv run pytest -m integration tests/test_integration_delivery.py tests/test_integration_attempt.py -q; echo "EXIT: $?"` → 0.

- [ ] **Step 5: Gates and commit**

```bash
just gates; echo "EXIT: $?"
git add -A && git commit -m "Phase 1: validation restores carried tests and runs the checks; the receipt counts turns, tool calls, tokens and guard firings from the stream"
```

---

### Task 9: The attempt prompt and argv for `/implement` (engine)

**Files:**
- Modify: `src/satyrn_engine/attempt.py:274-291` (`build_prompt`), `:319-386` (`build_pi_command`), `:592-597`, `:703` (the writable list passed to the prompt), `tests/test_attempt.py`
- Create: `tests/test_bounds_pin.py`

**Interfaces:**
- Produces: `attempt.BASH_BOUND_SECONDS = 120` (pinned to `bounds.ts` by `tests/test_bounds_pin.py`, which reads the TS file text and asserts `DEFAULT_TIMEOUT_SECONDS = 120` — M11); `build_prompt(contract: Contract, existing: Sequence[str]) -> str` — lists `contract.writable_paths` patterns, each followed by the existing tracked files beneath it (I14); `build_pi_command(engine_repo, model, prompt, *, test_command=())` → `--extension` for `engine.ts`, `mutator.ts`, `scope.ts`, `bounds.ts` always and `runner.ts` when `test_command`; `--tools read,bash,edit,write,self_test` when `test_command` else `read,bash,edit,write`; the `--append-system-prompt` correction is dropped.

Prompt (facts inline; no pointers):

```
Implement this bounded task:
<task>

Writable paths (edit and write are refused elsewhere; new files are allowed under these):
- <pattern>  (existing: a.py, b.py)      ← "(existing: …)" only when files exist beneath the pattern
- <exact path>  (new file)               ← when nothing exists at an exact path

Tests carried from the accepted base; they are restored before every self-test, so edits to them never count:
- <preserve>...   (section omitted when empty)
Developer checks that must pass:
- <checks>...     (section omitted when empty)

Verify with the self_test tool before finishing: it runs "<test command>" (and the checks) and returns failed test ids with their first assertion line. Shell commands are bounded at 120 seconds. Budget: <token_budget> output tokens and <turn_budget> turns. Stop when the task is complete.
```

- [ ] **Step 1: Failing tests** (`tests/test_attempt.py`, beside the existing `build_prompt`/`build_pi_command` tests)

```python
def test_prompt_states_patterns_with_existing_files_carried_tests_self_test_and_budgets_inline() -> None:
    contract = Contract(id="x", task="Add --check", writable_paths=("src/*", "src/app/new.py"),
                        test_command=("uv", "run", "python", "-m", "pytest", "-q"), preserve=("tests/test_a.py",),
                        checks=("checks/c.py",), token_budget=32000, turn_budget=48)
    prompt = build_prompt(contract, ("src/app/cli.py", "src/app/gate.py"))
    assert "Implement this bounded task:\nAdd --check\n" in prompt
    assert "- src/*  (existing: src/app/cli.py, src/app/gate.py)\n" in prompt
    assert "- src/app/new.py  (new file)\n" in prompt
    assert "restored before every self-test" in prompt and "- tests/test_a.py\n" in prompt
    assert "Developer checks that must pass:\n- checks/c.py\n" in prompt
    assert 'self_test tool before finishing: it runs "uv run python -m pytest -q"' in prompt
    assert "bounded at 120 seconds" in prompt
    assert "Budget: 32000 output tokens and 48 turns" in prompt
    assert "Do not create files" not in prompt


def test_prompt_omits_empty_carried_sections_and_absent_budgets() -> None:
    prompt = build_prompt(Contract(id="x", task="t", writable_paths=("a.py",)), ("a.py",))
    assert "carried from" not in prompt and "Developer checks" not in prompt
    assert "Budget:" not in prompt and "self_test" not in prompt


def test_pi_command_loads_every_guard_and_names_the_native_tools_plus_self_test(tmp_path: Path) -> None:
    command = build_pi_command(tmp_path, "m", "p", test_command=("uv", "run", "python", "-m", "pytest", "-q"))
    package = tmp_path / "packages" / "engine"
    extensions = [command[i + 1] for i, token in enumerate(command) if token == "--extension"]
    assert extensions == [os.fspath(package / name) for name in ("engine.ts", "mutator.ts", "scope.ts", "bounds.ts", "runner.ts")]
    assert command[command.index("--tools") + 1] == "read,bash,edit,write,self_test"
    assert "--append-system-prompt" not in command


def test_pi_command_without_a_test_command_has_no_runner_and_no_self_test(tmp_path: Path) -> None:
    command = build_pi_command(tmp_path, "m", "p")
    assert not any(token.endswith("runner.ts") for token in command)
    assert command[command.index("--tools") + 1] == "read,bash,edit,write"
```

`tests/test_bounds_pin.py`:

```python
import re
from pathlib import Path

from satyrn_engine.attempt import BASH_BOUND_SECONDS

BOUNDS_TS = Path(__file__).parents[1] / "packages" / "engine" / "bounds.ts"


def test_the_prompt_names_the_same_bound_bounds_ts_applies() -> None:
    match = re.search(r"^export const DEFAULT_TIMEOUT_SECONDS = (\d+);$", BOUNDS_TS.read_text(), re.MULTILINE)
    assert match is not None and int(match.group(1)) == BASH_BOUND_SECONDS == 120
```

Existing tests that pin the old prompt sentences (`"Use the edit tool for every write"`, `"Do not create files"`) or the old `--tools read,edit,bash` / `--append-system-prompt` are updated to the new text — the only permitted assertion change.

- [ ] **Step 2: Run to verify failure** — `uv run pytest tests/test_attempt.py tests/test_bounds_pin.py -q` → the five fail.

- [ ] **Step 3: Implement**

```python
BASH_BOUND_SECONDS = 120   # pinned to packages/engine/bounds.ts DEFAULT_TIMEOUT_SECONDS by tests/test_bounds_pin.py


def build_prompt(contract: Contract, existing: Sequence[str]) -> str:
    """The handoff prompt: every fact inline, nothing pointed at."""
    def writable_line(pattern: str) -> str:
        beneath = sorted(p for p in existing if fnmatch(p, pattern))
        if beneath:
            return f"- {pattern}  (existing: {', '.join(beneath)})"
        return f"- {pattern}  (new file)" if not any(c in pattern for c in "*?[") else f"- {pattern}"

    def block(title: str, items: Sequence[str]) -> str:
        return f"{title}\n" + "\n".join(f"- {item}" for item in items) + "\n\n" if items else ""

    writable = "Writable paths (edit and write are refused elsewhere; new files are allowed under these):\n" + \
        "\n".join(writable_line(p) for p in contract.writable_paths) + "\n\n"
    verify = (
        f'Verify with the self_test tool before finishing: it runs "{" ".join(contract.test_command)}"'
        f'{" (and the checks)" if contract.checks else ""} and returns failed test ids with their first assertion line. '
        if contract.test_command else "")
    budget = (
        f"Budget: {contract.token_budget} output tokens and {contract.turn_budget} turns. "
        if contract.token_budget is not None and contract.turn_budget is not None else "")
    return (
        f"Implement this bounded task:\n{contract.task}\n\n"
        + writable
        + block("Tests carried from the accepted base; they are restored before every self-test, so edits to them never count:", contract.preserve)
        + block("Developer checks that must pass:", contract.checks)
        + verify
        + f"Shell commands are bounded at {BASH_BOUND_SECONDS} seconds. "
        + budget
        + "Stop when the task is complete."
    )
```

`_run` (703) passes `tuple(sorted(context.revisions))` as `existing` (the tracked files under the writable patterns — that is what `_prepare` collected). `build_pi_command`: extensions `engine.ts, mutator.ts, scope.ts, bounds.ts` (+ `runner.ts` when `test_command`); `--tools` as specified; delete the `correction` tuple and its comment (keep the `--tools` comment at 370-382 — it is why `self_test` is named). `_prepare` 593: `required_extensions = ("engine.ts", "mutator.ts", "scope.ts", "bounds.ts")`. `_prepare` 575-576 ("contract matches no existing tracked writable file"): relax to a failure only when `writable_paths` is empty — a build task whose only writable path is a new file has no revisions yet and must still run (Ruling 12); add a test row for that.

- [ ] **Step 4: Pass** — `uv run pytest -q > /tmp/p1-t9.log 2>&1; echo "EXIT: $?"` → 0; `uv run pytest -m integration tests/test_integration_attempt.py -q; echo "EXIT: $?"` → 0 (the fake Pi records argv; update any pinned argv).

- [ ] **Step 5: Record, gates, commit**

```bash
uv run python tools/provenance.py new tests/test_bounds_pin.py
just gates; echo "EXIT: $?"
git add -A && git commit -m "Phase 1: the attempt loads every guard, keeps native tools plus self_test, and states every fact inline"
```

---

### Task 10: `/implement` — derive, confirm or go, dispatch, keep the receipt (engine)

**Files:**
- Modify: `packages/engine/orchestrator.ts:225-241,370-421` (invocations), `:428-531` (`exchange` → `collect`), `:732-795` (`createAdapter`, registration), `tests/test_orchestrator.mjs`

**Interfaces:**
- Produces: `buildDeriveInvocation(repo, request, engineRepo): DeriveInvocation` → `{command:"uv", cwd: engineRepo, args:["run","--project",engineRepo,"satyrn-engine","derive","--repo",repo,"--",request]}` (M4); `buildDeliveryInvocation` passes the contract **absolute** whenever its repo-relative path is empty, starts with `..`, or has `.git` as its first segment (C1); `collect(spawner, command, args, cwd, deadlineMs): Promise<{stdout; stderr; code}>` (factored out of `exchange`, which now calls it and keeps its refusal mapping; `tests/test_transport.mjs` unchanged); `parseDeliveryReceipt` passes through the Task 8 fields when present (`validation?`, `tokens_out?`, `turns?`, `guard_firings?`); `receiptSummary(receipt): string` → `validation=<v> tokens_out=<n> turns=<n> guards: <kind=n ...|none>`; `createAdapter(...).implement(args, ctx)`:
  - `/implement <request>` → `collect` derive; on exit ≠ 0 notify stderr as `error`; else notify the YAML (`info`), and when `ctx.hasUI === true` ask `await ctx.ui.confirm("Dispatch this contract?", yaml)` — `true` dispatches at once, `false` notifies `not dispatched; run /implement --go <id> to dispatch later`; when `hasUI` is not `true` notify `satyrn-engine: contract <path>; run /implement --go <id> to dispatch` (Ruling 4).
  - `/implement --go <id>` → `collect` `git -C <cwd> rev-parse --path-format=absolute --git-dir`, contract path `<git-dir>/satyrn/contracts/<id>.yaml`, `runDelivery(...)` as today, write the receipt JSON to `<git-dir>/satyrn/receipts/<id>.json` (M7; `writeFileSync`, failures notified as `ADAPTER_ERROR` but the receipt line still shown), notify `satyrn-engine: <code>: <ref> <commit> <receiptSummary>` for every `candidate-created` outcome (`OK`, `TESTS_FAILED`, `BUDGET_EXHAUSTED` — M8) as `info` for `OK` and `error` otherwise, and `satyrn-engine: <code>: <message>` for refusals/discards.

- [ ] **Step 1: Failing tests** (`tests/test_orchestrator.mjs`; `child(options)` is the fake child helper at line 58; `DELIVERY_OK` is the OK receipt string at line 29 — M15)

```js
test("a contract under the git dir reaches attempt as an absolute path", () => {
	const invocation = buildDeliveryInvocation("/repo", "/repo/.git/satyrn/contracts/implement-abc.yaml", "m", "/engine");
	assert.equal(invocation.args.at(-1), "/repo/.git/satyrn/contracts/implement-abc.yaml");
	assert.equal(buildDeliveryInvocation("/repo", "/repo/contract.yaml", "m", "/engine").args.at(-1), "contract.yaml");
});

test("derive invocation runs the engine's derive subcommand with -- before the request", () => {
	assert.deepEqual(buildDeriveInvocation("/repo", "-add a flag to src/cli.py", "/engine"), {
		command: "uv", cwd: "/engine",
		args: ["run", "--project", "/engine", "satyrn-engine", "derive", "--repo", "/repo", "--", "-add a flag to src/cli.py"],
	});
});

const okReceipt = (extra = {}) => JSON.stringify({ ...JSON.parse(DELIVERY_OK), ...extra });
const ui = (notes, confirmAnswer) => ({ notify: (m, l) => notes.push([l, m]), confirm: async () => confirmAnswer });

test("/implement with a request derives and shows the contract; without a UI it waits for --go", async () => {
	process.env.SATYRN_ENGINE_REPO = "/engine"; process.env.SATYRN_MODEL = "m";
	const spawned = [];
	const spawner = (command, args) => { spawned.push([command, ...args]); return child({ stdout: "id: implement-0123456789ab\ntask: add a flag\n", stderr: "satyrn-engine: contract /repo/.git/satyrn/contracts/implement-0123456789ab.yaml\n" }); };
	const notes = [];
	await createAdapter(spawner).implement("add a flag to src/cli.py", { cwd: "/repo", hasUI: false, ui: ui(notes, false) });
	assert.equal(spawned.length, 1);
	assert.deepEqual(spawned[0].slice(0, 6), ["uv", "run", "--project", "/engine", "satyrn-engine", "derive"]);
	assert.deepEqual(notes[0], ["info", "id: implement-0123456789ab\ntask: add a flag\n"]);
	assert.match(notes[1][1], /run \/implement --go implement-0123456789ab to dispatch/);
});

test("/implement with a UI confirms in place and dispatches on yes, waits on no", async () => {
	process.env.SATYRN_ENGINE_REPO = "/engine"; process.env.SATYRN_MODEL = "m";
	for (const answer of [true, false]) {
		const spawned = [];
		const spawner = (command, args) => {
			spawned.push([command, ...args]);
			if (command === "git") return child({ stdout: "/repo/.git\n" });
			if (args.includes("derive")) return child({ stdout: "id: implement-0123456789ab\ntask: t\n", stderr: "satyrn-engine: contract /repo/.git/satyrn/contracts/implement-0123456789ab.yaml\n" });
			return child({ stdout: okReceipt() });
		};
		const notes = [];
		await createAdapter(spawner, undefined, undefined, () => {}).implement("t src/a.py", { cwd: "/repo", hasUI: true, ui: ui(notes, answer) });   // fake receipt writer: never touch /repo (m8)
		assert.equal(spawned.some((argv) => argv.includes("deliver")), answer);
		if (!answer) assert.match(notes.at(-1)[1], /not dispatched; run \/implement --go implement-0123456789ab/);
	}
});

test("/implement --go resolves the contract under the git dir, dispatches, writes the receipt and summarizes it", async () => {
	process.env.SATYRN_ENGINE_REPO = "/engine"; process.env.SATYRN_MODEL = "m";
	const spawned = []; const written = [];
	const spawner = (command, args) => {
		spawned.push([command, ...args]);
		if (command === "git") return child({ stdout: "/repo/.git\n" });
		return child({ stdout: okReceipt({ code: "TESTS_FAILED", validation: "failed", tokens_out: 1200, turns: 7,
			guard_firings: { loop_broken: 0, scope_refused: 1, symbol_preserved: 0, command_bounded: 2, command_timed_out: 0 } }) });
	};
	const notes = [];
	await createAdapter(spawner, undefined, undefined, (path, text) => written.push([path, text])).implement("--go implement-0123456789ab", { cwd: "/repo", hasUI: false, ui: ui(notes, false) });
	assert.deepEqual(spawned[0], ["git", "-C", "/repo", "rev-parse", "--path-format=absolute", "--git-dir"]);
	assert.equal(spawned[1].at(-1), "/repo/.git/satyrn/contracts/implement-0123456789ab.yaml");
	assert.equal(written[0][0], "/repo/.git/satyrn/receipts/implement-0123456789ab.json");
	assert.deepEqual(notes.at(-1), ["error", "satyrn-engine: TESTS_FAILED: refs/satyrn/candidates/task/head candidate validation=failed tokens_out=1200 turns=7 guards: scope_refused=1 command_bounded=2"]);
});

test("/implement --go with a bad id, and a failed derive, are named refusals", async () => {
	process.env.SATYRN_ENGINE_REPO = "/engine"; process.env.SATYRN_MODEL = "m";
	const notes = [];
	const ctx = { cwd: "/repo", hasUI: false, ui: ui(notes, false) };
	await createAdapter(() => child({ stdout: "", stderr: "satyrn-engine: DERIVE: name at least one tracked file\n", exitCode: 5 })).implement("make it faster", ctx);
	assert.deepEqual(notes.at(-1), ["error", "satyrn-engine: DERIVE: name at least one tracked file"]);
	await createAdapter(() => child({})).implement("--go ../etc", ctx);
	assert.deepEqual(notes.at(-1), ["error", "satyrn-engine: USAGE: --go takes a contract id like implement-0123456789ab"]);
});
```

The first test fails on the current `buildDeliveryInvocation` (it yields `.git/satyrn/contracts/implement-abc.yaml`, relative) — that is the C1 bug, and it must be seen red before Step 3. `parseDeliveryReceipt` currently drops unknown keys; the `TESTS_FAILED` fixture also needs `DELIVERY_CODE_OUTCOMES` (present: `TESTS_FAILED`/`BUDGET_EXHAUSTED` are missing from `orchestrator.ts:171-188` — add both as `"candidate-created"`, matching `delivery.py:75-77`).

- [ ] **Step 2: Run to verify failure** — `node --test --experimental-strip-types tests/test_orchestrator.mjs` → the absolute-path assertion fails with `.git/satyrn/...`; `buildDeriveInvocation` not exported.

- [ ] **Step 3: Implement**

`buildDeliveryInvocation` (377-386): `const innerContract = relativeContract !== "" && relativeContract !== ".." && !relativeContract.startsWith(\`..${sep}\`) && relativeContract.split(sep)[0] !== ".git" ? relativeContract : resolvedContract;`. Add `TESTS_FAILED: "candidate-created", BUDGET_EXHAUSTED: "candidate-created"` to `DELIVERY_CODE_OUTCOMES`; `DeliveryReceiptBase` gains optional `validation?: string; tokens_out?: number; turns?: number; guard_firings?: Record<string, number>` copied by `parseDeliveryReceipt` when the types match. `buildDeriveInvocation` as in Interfaces. Factor `collect` out of `exchange` (same child handling; collects stderr; resolves `{stdout, stderr, code}` on `close`; `ENGINE_TIMEOUT`/`ENGINE_START_FAILED` raised inside), `exchange` = `collect` + `parseResponse` + the `ENGINE_CRASHED` mapping.

```ts
export function receiptSummary(receipt: DeliveryReceipt): string {
	const firings = Object.entries(receipt.guard_firings ?? {}).filter(([, n]) => n > 0).map(([k, n]) => `${k}=${n}`);
	return `validation=${receipt.validation ?? "unknown"} tokens_out=${receipt.tokens_out ?? 0} turns=${receipt.turns ?? 0} guards: ${firings.join(" ") || "none"}`;
}

const CONTRACT_ID = /^implement-[0-9a-f]{12}$/;

export function createAdapter(spawner: DeliverySpawner, deadlineMs = DEFAULT_DELIVERY_DEADLINE_MS,
	processControl: ProcessControl = defaultProcessControl(),
	writeReceipt: (path: string, text: string) => void = (path, text) => { mkdirSync(dirname(path), { recursive: true }); writeFileSync(path, text); }) {
	const dispatch = async (id: string, ctx: ImplementContext, model: string, engineRepo: string): Promise<void> => {
		const gitDir = await collect(spawner, "git", ["-C", ctx.cwd, "rev-parse", "--path-format=absolute", "--git-dir"], ctx.cwd, DEFAULT_DEADLINE_MS);
		if (gitDir.code !== 0) { ctx.ui.notify(`satyrn-engine: REPO_UNAVAILABLE: ${gitDir.stderr.trim()}`, "error"); return; }
		const contractPath = resolve(gitDir.stdout.trim(), "satyrn", "contracts", `${id}.yaml`);
		const invocation = buildDeliveryInvocation(ctx.cwd, contractPath, model, engineRepo);
		try {
			const receipt = await runDelivery(spawner, invocation, deadlineMs, undefined, DELIVERY_TERMINATION_GRACE_MS, processControl);
			try { writeReceipt(resolve(gitDir.stdout.trim(), "satyrn", "receipts", `${id}.json`), `${JSON.stringify(receipt)}\n`); }
			catch (err) { ctx.ui.notify(`satyrn-engine: ADAPTER_ERROR: could not write the receipt: ${String(err)}`, "error"); }
			if (receipt.outcome === "candidate-created") {
				ctx.ui.notify(`satyrn-engine: ${receipt.code}: ${receipt.candidate_ref} ${receipt.candidate_commit} ${receiptSummary(receipt)}`, receipt.code === "OK" ? "info" : "error");
			} else {
				ctx.ui.notify(`satyrn-engine: ${receipt.code}: ${receipt.message}`, "error");
			}
		} catch (err) { /* existing AdapterRefusal mapping and notify */ }
	};
	return {
		async implement(args: string, ctx: ImplementContext): Promise<void> {
			// existing SATYRN_ENGINE_REPO / SATYRN_MODEL checks
			const trimmed = args.trim();
			if (trimmed.startsWith("--go")) {
				const id = trimmed.slice(4).trim();
				if (!CONTRACT_ID.test(id)) { ctx.ui.notify("satyrn-engine: USAGE: --go takes a contract id like implement-0123456789ab", "error"); return; }
				await dispatch(id, ctx, model, engineRepo);
				return;
			}
			if (!trimmed) { ctx.ui.notify("satyrn-engine: USAGE: /implement <request> derives a contract; /implement --go <id> dispatches it", "error"); return; }
			const derive = buildDeriveInvocation(ctx.cwd, trimmed, engineRepo);
			const derived = await collect(spawner, derive.command, derive.args, derive.cwd, DEFAULT_DEADLINE_MS);
			if (derived.code !== 0) { ctx.ui.notify(derived.stderr.trim() || `satyrn-engine: DERIVE: exit ${derived.code}`, "error"); return; }
			ctx.ui.notify(derived.stdout, "info");
			const id = /^id: (implement-[0-9a-f]{12})$/m.exec(derived.stdout)?.[1];
			if (id === undefined) { ctx.ui.notify("satyrn-engine: ENGINE_MALFORMED_RESPONSE: derived contract has no id", "error"); return; }
			if (ctx.hasUI === true && (await ctx.ui.confirm("Dispatch this contract?", derived.stdout))) { await dispatch(id, ctx, model, engineRepo); return; }
			ctx.ui.notify(ctx.hasUI === true
				? `satyrn-engine: not dispatched; run /implement --go ${id} to dispatch later`
				: `${derived.stderr.trim()}; run /implement --go ${id} to dispatch`, "info");
		},
	};
}
```

`ImplementContext = { cwd: string; hasUI?: boolean; ui: { notify(message, level): void; confirm(title: string, message: string): Promise<boolean> } }`. The default export's `registerCommand` handler passes Pi's `ctx` straight through (it has `hasUI` and `ui.confirm`, `types.d.ts:72,209-215`); description: `"Derive a contract from a request (/implement <request>) and dispatch it (confirm, or /implement --go <id>)"`.

- [ ] **Step 4: Pass** — `node --test --experimental-strip-types tests/test_orchestrator.mjs tests/test_transport.mjs; echo "EXIT: $?"` → 0.

- [ ] **Step 5: Gates and commit**

```bash
just gates; echo "EXIT: $?"
git add -A && git commit -m "Phase 1: /implement derives and shows the contract, confirms or waits for --go, dispatches with an absolute contract path, and keeps the receipt"
```

---

### Task 11: A fake model completes `/implement` end to end (engine)

**Files:**
- Modify: `tests/fixtures/attempt/fake_pi.py` (mode `implement`)
- Create: `tests/test_integration_implement.py`

**Interfaces:**
- Produces: `SATYRN_FAKE_PI_MODE=implement` — the fake `pi` (installed on `PATH` by the existing `_fixture` helper, `tests/test_integration_attempt.py:67-73`) reads `SATYRN_MUTATION_CONTEXT` (set by the real `attempt`, `attempt.py:686-700`), emits three `turn_start`, three assistant `message_end` with `usage` (`output` 100/200/300, `input` 1000 each), one `tool_execution_start` per tool call, drives the shipped mutator once through `tools/exercise_mutator.mjs CONTEXT.json INPUT.json` (temp files, as mode `replace` does at `fake_pi.py:40-58`) with `oldText: "return 1"` → `"return 2"`, drives the shipped runner through `tools/exercise_runner.mjs CONTEXT.json` (Task 4's one-argument form) writing its stdout to `SATYRN_FAKE_PI_SELF_TEST_OUT` when set, and emits one `{"type":"entry_appended","entry":{"type":"custom","customType":"command_bounded","data":{"action":"set","timeout":120}}}` line (standing in for a bash call the fake never makes; the TS guard is proven by replay). With `SATYRN_FAKE_PI_TOKENS=<n>` each assistant `output` is `n` instead (for the budget test). Exit 0.

The fixture repo (extends `_fixture`): `app.py` (`def value():\n    return 1\n`), `tests/test_value.py` (`from app import value\n\n\ndef test_value():\n    assert value() == 2\n`), `pyproject.toml` (`[project]\nname = "fx"\nversion = "0"\n`), no `.gitignore` (Task 8's glob-exclude staging keeps `.venv`, `.pytest_cache` and every `__pycache__` out of the candidate whether or not they are ignored), committed. The mutation context the real `attempt` writes carries `writable_paths`, `test_command`, `symbols`, `carried` (`tests/test_value.py`, `pyproject.toml`) and `base_commit`, so `exercise_runner.mjs` restores from the base commit. Contract: derived by `cli.main(["derive", "--repo", repo, "--", "Make value() return 2 in app.py"])` → `test_command` is the default `uv run python -m pytest -q` — but `uv run` needs a project with pytest resolvable; to stay offline the test rewrites the derived YAML's `test_command` to `[python, -m, pytest, -q]` (pytest is in the engine's own venv running the test) and asserts everything else came from derivation. Skip with a stated reason if `node` is absent (as `_fixture` does).

- [ ] **Step 1: The failing integration tests**

```python
import json, os, shutil, subprocess, sys
from pathlib import Path

import pytest
import yaml

from satyrn_engine import cli
from satyrn_engine.delivery import DeliveryCode, deliver
from test_integration_attempt import ROOT, _fixture, _git   # bare name: tests/ has no __init__.py and pytest puts tests/ on sys.path (N4)

pytestmark = pytest.mark.integration


def _implement_fixture(tmp_path: Path, capsys, monkeypatch, token_budget: int | None = None) -> tuple[Path, Path, dict[str, str]]:
    repo, _contract, _target, environment = _fixture(tmp_path)
    (repo / "tests").mkdir()
    (repo / "tests" / "test_value.py").write_text("from app import value\n\n\ndef test_value():\n    assert value() == 2\n")
    (repo / "pyproject.toml").write_text('[project]\nname = "fx"\nversion = "0"\n')
    assert _git(repo, "add", "-A").returncode == 0
    assert _git(repo, "-c", "user.name=F", "-c", "user.email=f@x.invalid", "commit", "-qm", "fixture").returncode == 0
    assert cli.main(["derive", "--repo", str(repo), "--", "Make value() return 2 in app.py"]) == 0
    contract_path = Path(capsys.readouterr().err.split("contract ", 1)[1].strip())
    body = yaml.safe_load(contract_path.read_text())
    # Task 3's rule: app.py, then its test tests/test_app.py, which is untracked (so not preserved) and therefore writable (N5)
    assert body["writable_paths"] == ["app.py", "tests/test_app.py"] and body["preserve"] == ["tests/test_value.py"]
    assert body["test_command"] == ["uv", "run", "python", "-m", "pytest", "-q"]
    assert (body["token_budget"], body["turn_budget"]) == (32000, 48)
    body["test_command"] = [sys.executable, "-m", "pytest", "-q"]      # offline: the engine venv's pytest
    if token_budget is not None:
        body["token_budget"] = token_budget
    contract_path.write_text(yaml.safe_dump(body, sort_keys=False))
    environment["SATYRN_FAKE_PI_MODE"] = "implement"
    environment["SATYRN_FAKE_PI_SELF_TEST_OUT"] = str(tmp_path / "self_test.json")
    for name, value in environment.items():
        monkeypatch.setenv(name, value)
    return repo, contract_path, environment


def _attempt_command(contract_path: Path) -> tuple[str, ...]:
    return ("uv", "run", "--project", str(ROOT), "satyrn-engine", "attempt", "--model=fixture/model", "--", str(contract_path))


def test_a_fake_model_completes_implement_end_to_end(tmp_path: Path, capsys, monkeypatch) -> None:
    repo, contract_path, _ = _implement_fixture(tmp_path, capsys, monkeypatch)
    receipt = deliver(repo, contract_path, _attempt_command(contract_path), timeout=120.0)
    payload = receipt.payload()
    assert (payload["code"], payload["validation"]) == ("OK", "passed"), payload
    assert payload["changed_paths"] == ["app.py"]
    assert (payload["turns"], payload["tool_calls"], payload["tokens_in"], payload["tokens_out"]) == (3, 2, 3000, 600)
    budget = payload["budget"]
    assert (budget["state"], budget["turns_used"], budget["turn_limit"]) == ("within", 3, 48)
    assert (budget["token_limit"], budget["tokens_used"], budget["deadline_seconds"]) == (32000, 600, None)
    assert payload["guard_firings"]["command_bounded"] == 1
    assert payload["carried"] == {"preserve": ["tests/test_value.py"], "checks": [], "infrastructure": ["pyproject.toml"], "absent": [], "tampered": []}
    self_test = json.loads((tmp_path / "self_test.json").read_text())
    assert self_test["details"]["ok"] is True and self_test["details"]["result"]["exit_code"] == 0
    assert "1 passed" in self_test["content"][0]["text"]
    assert _git(repo, "status", "--porcelain").stdout == b""


def test_a_fake_model_that_exceeds_the_token_budget_is_budget_exhausted_with_the_candidate_kept(tmp_path: Path, capsys, monkeypatch) -> None:
    repo, contract_path, _ = _implement_fixture(tmp_path, capsys, monkeypatch, token_budget=500)
    receipt = deliver(repo, contract_path, _attempt_command(contract_path), timeout=120.0)
    payload = receipt.payload()
    assert payload["code"] == "BUDGET_EXHAUSTED" and payload["outcome"] == "candidate-created"
    assert payload["budget"]["state"] == "token_exhausted" and payload["budget"]["token_limit"] == 500
    assert payload["budget"]["tokens_used"] > 500
    assert payload["candidate_commit"] is not None
    assert payload["message"].startswith("candidate created; whole-attempt token budget exhausted after")
```

(The contract lives under `<repo>/.git/satyrn/contracts/`; passing it absolute to `attempt` is the C1 fix exercised through the real `attempt` path.)

- [ ] **Step 2: Run to verify failure** — `uv run pytest -m integration tests/test_integration_implement.py -q` → the fake exits without the stream; `turns == 0`.

- [ ] **Step 3: Implement mode `implement` in `fake_pi.py`**

```python
    if mode == "implement":
        return implement(os.environ["SATYRN_MUTATION_CONTEXT"], Path(os.environ["SATYRN_ENGINE_REPO"]))


def implement(context_text: str, engine_repo: Path) -> int:
    context = json.loads(context_text)
    [path] = list(context["revisions"])
    per_turn = int(os.environ.get("SATYRN_FAKE_PI_TOKENS", "0"))

    def emit(event: dict) -> None:
        print(json.dumps(event), flush=True)

    def assistant(output: int) -> None:
        emit({"type": "message_end", "message": {"role": "assistant", "usage": {"input": 1000, "output": per_turn or output}}})

    def node(script: str, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["node", "--experimental-strip-types", str(engine_repo / "tools" / script), *args],
                              cwd=engine_repo, capture_output=True, text=True, check=False)

    with tempfile.TemporaryDirectory(prefix="satyrn-fake-pi-") as temporary:
        root = Path(temporary)
        (root / "context.json").write_text(context_text, encoding="utf-8")
        (root / "input.json").write_text(json.dumps({"path": path, "edits": [{"oldText": "return 1", "newText": "return 2"}]}), encoding="utf-8")
        emit({"type": "turn_start"}); assistant(100)
        emit({"type": "tool_execution_start", "toolCallId": "e1", "toolName": "edit"})
        edit = node("exercise_mutator.mjs", str(root / "context.json"), str(root / "input.json"))
        if edit.returncode != 0 or '"ok":true' not in edit.stdout:
            sys.stderr.write(edit.stdout + edit.stderr)
            return 3
        emit({"type": "turn_start"}); assistant(200)
        emit({"type": "tool_execution_start", "toolCallId": "t1", "toolName": "self_test"})
        test = node("exercise_runner.mjs", str(root / "context.json"))
        if out := os.environ.get("SATYRN_FAKE_PI_SELF_TEST_OUT"):
            Path(out).write_text(test.stdout, encoding="utf-8")
        emit({"type": "entry_appended", "entry": {"type": "custom", "customType": "command_bounded", "data": {"action": "set", "timeout": 120}}})
        emit({"type": "turn_start"}); assistant(300)
    emit({"type": "session_shutdown", "reason": "implement"})
    return 0
```

The budget test sets `SATYRN_FAKE_PI_TOKENS=300` in its environment (three turns × 300 = 900 > 500); add that to `_implement_fixture` when `token_budget` is given. The fake's `self_test` output is the compact form from Task 4 (`exercise_runner.mjs` prints the tool result JSON; `content[0].text` starts with `Test command exited 0`).

- [ ] **Step 4: Pass** — `uv run pytest -m integration tests/test_integration_implement.py -q; echo "EXIT: $?"` → 0. Then the whole integration tier: `uv run pytest -m integration -q > /tmp/p1-t11i.log 2>&1; echo "EXIT: $?"` → 0.

- [ ] **Step 5: Record, gates, commit**

```bash
uv run python tools/provenance.py new tests/test_integration_implement.py
just gates; echo "EXIT: $?"
git add -A && git commit -m "Phase 1: a fake model completes /implement end to end; budgets, carried tests and firings land in the receipt"
```

---

### Task 12: Sync the roadmaps and park the engine's planning documents

**Files:**
- Modify (evals): `ROADMAP.md`
- Modify (engine): `ROADMAP.md`, `BACKLOG.md`

- [ ] **Step 1: Evals `ROADMAP.md`** — replace the opening paragraph (lines 3-7) with:

```markdown
The design is `docs/superpowers/specs/2026-09-13-release-one-design.md`. One
claim: on the ceiling workload, the Engine delivers a passing candidate within
budget (tokens and turns) more often than bare Pi, on Ornith 1.5 9B. A
declared secondary: on the floor workload, where both pass, the Engine costs no
more. Nothing else is claimed.
```

Replace the phase table rows 1–5 with the spec's roadmap rows verbatim (spec lines 326-330), adding a Status column: Phase 1 `in progress — docs/superpowers/plans/2026-09-14-phase-1-implement.md`, the rest `not started`. Replace the "Ornith ... pathology probe" paragraph with: `The Ornith pathology probe answered 0/8, 1/8, 0/8 on the tagged tree; the claim moved from pathologies to a ceiling (spec, "What the evidence settled").` Under "Rules that bind every phase", replace the first bullet with: `Attended sittings are ≤ 60 min and n ≤ 8; a batch night is 24 cells across both arms, 720 minutes, record and campaign frozen in daylight, on this machine.` Keep the rest. Under "Deferred", replace with the spec's "Deferred, deliberately" list plus the existing session-protocol integration-test item. `just lint-docs; echo "EXIT: $?"` → 0 (≤ 150 lines).

- [ ] **Step 2: Engine `ROADMAP.md` and `BACKLOG.md`** — replace each whole file:

`ROADMAP.md`:

```markdown
# Roadmap

Parked 2026-09-14. This repository's roadmap is the release-one design in
`satyrn-evals` (`docs/superpowers/specs/2026-09-13-release-one-design.md`) and
the plan for the current phase; the phases E, HP3 and V this file used to
narrate are recorded on the tag `pre-release-one-2026-09-13` (`git show
pre-release-one-2026-09-13:ROADMAP.md`). Nothing here is planned separately.

| # | Phase | Direction (one sentence) | Status |
|---|-------|--------------------------|--------|
| 1 | Engine `/implement` v1 | Derived contract, guards 1–4 and symbol preservation, carried tests, compact results, receipt — all proven against fakes and replay | in progress — `satyrn-evals` plan `2026-09-14-phase-1-implement.md` |
```

`BACKLOG.md`:

```markdown
# Backlog

Parked 2026-09-14. Deferred items and their reopen conditions live in the
release-one design's "Deferred, deliberately" section in `satyrn-evals`. The
entries this file held are on the tag (`git show
pre-release-one-2026-09-13:BACKLOG.md`); the two dated 2026-09-06 (file
creation through the mutator; a model-invocable test runner) are done in
Phase 1 as native `write` under guard 3 and the `self_test` tool.
```

`just lint-docs; echo "EXIT: $?"` → 0 (both files exist, under 400 lines, Direction cell under 400 characters).

- [ ] **Step 3: Commit both trees**

Evals: `just gates; echo "EXIT: $?"` → 0; `git add -A && git commit -m "Phase 1: roadmap states the ceiling claim and the batch cap"`. Engine: `just gates; echo "EXIT: $?"` → 0; `git add -A && git commit -m "Phase 1: roadmap and backlog parked; the design lives in satyrn-evals"`.

---

### Task 13: Docs, glossary, and closing the phase

**Files:**
- Modify (engine): `docs/usage.md`, `docs/glossary.md`, `README.md`
- Modify (evals): `ROADMAP.md` (Phase 1 status)

- [ ] **Step 1: `docs/usage.md`** — add a section after "Deliver one candidate":

```markdown
## `/implement`

Inside Pi with the package installed (`pi install <engine>/packages/engine`,
`SATYRN_ENGINE_REPO` and `SATYRN_MODEL` set):

    /implement add --check to src/app/cli.py

derives a contract from the request and the repository — `writable_paths`
from the files, directories and new files the request names, `test_command`
from `[tool.satyrn] self_test` in `pyproject.toml` or the default
`uv run python -m pytest -q`, `preserve` (every tracked test file) and
`checks` (`checks/`), budgets of 32,000 output tokens and 48 turns — writes it
under `.git/satyrn/contracts/<id>.yaml`, and shows it. In the TUI, answer the
confirmation to dispatch; in print mode run:

    /implement --go implement-0123456789ab

One fresh Pi runs in a worktree branched from `HEAD` with the guards loaded
(they register only in that child): the loop breaker; `edit`/`write` refused
outside `writable_paths`; an `edit` or `write` that would remove a symbol the
base defines refused with what to do instead; bash `timeout` set to 120 s
when absent and clamped at 300 s, the result naming the bound and the
self-test. `preserve` and `checks` are restored from the base into the
worktree before every `self_test` run and before validation, so the model's
edits to them never count. The receipt (stdout, and
`.git/satyrn/receipts/<id>.json`) adds `turns`, `tool_calls`, `tokens_in`,
`tokens_out`, `guard_firings` and `carried`; `validation` is the engine's own
run and is authoritative; `budget.state` is `token_exhausted` when the model
spent past its token budget and the candidate is kept.
```

Add the contract fields `preserve`, `checks`, `token_budget`, `turn_budget` to the contract table (lines 27-31) and the `derive` subcommand (`satyrn-engine derive --repo REPO -- REQUEST...`) to the CLI section.

`docs/glossary.md`: add rows `self_test` ("the engine's registered tool that restores carried tests, runs the contract's `test_command` and the checks, and returns failed ids with their first assertion line"), `carried` ("preserve tests and checks restored from the accepted base before every self-test and before validation"), `guard firing` ("a `pi.appendEntry` custom entry the receipt counts from the child's json stream"), and a note under **contract** that the spec's `objective`/`self_test_command` are this file's `task`/`test_command`.

`README.md`: in "What it owns", change "the Pi-side loop breaker for repeated identical tool calls" to "the Pi-side guards: loop breaker, writable-path scope, symbol preservation, command bounds — the last three only inside `/implement`".

- [ ] **Step 2: Full gates and integration tiers, both trees, exit codes read**

Engine: `just gates; echo "EXIT: $?"` → 0; `just integration; echo "EXIT: $?"` → 0. Evals: `just gates; echo "EXIT: $?"` → 0; `just integration; echo "EXIT: $?"` → 0 (unchanged tier).

- [ ] **Step 3: Done-when check against the roadmap row**

- every component has replay or fixture tests both directions: guard 1 (`tests/fixtures/guards/*`), guard 3 (`scope-inside`/`scope-absolute-inside` vs `scope-outside`/`scope-traversal`), symbol (`symbol-kept`, `symbol-write-kept` vs `symbol-removed`, `symbol-write-removed`), guard 4 (`bounds-kept` vs `bounds-absent`/`bounds-clamped`; `bounds-no-context`), derive (named vs nothing named; declared vs default self-test), compact results (failing vs passing), budget (within vs token-exhausted), carried (restored vs absent at base);
- a fake model completes `/implement` end to end: Task 11 (through the real `attempt`, contract under `.git`);
- 120/300 frozen against measured suite durations: Task 1's JSON and its default-tier pin; Task 7's freeze gate; `tests/test_bounds_pin.py`.

- [ ] **Step 4: Mark Phase 1 done and commit**

Evals `ROADMAP.md`: Phase 1 Status → `done <date> — evals <commit>, engine <commit>`. Engine `ROADMAP.md` row: `done <date>`. `just lint-docs` in each → 0. Commit: evals `Phase 1 done: /implement v1 proven against fakes; bounds frozen`; engine `Phase 1 done: /implement v1 — derived contract, four guards, symbol preservation, carried tests, compact results, receipt`.

- [ ] **Step 5: Status page for the morning** (chat message, not a file)

Under 200 words: both branch heads; default-tier and integration counts per tree; the measured suite durations (longest, task) and that 120/300/120 fit; every imported test whose assertion changed (Task 2's exhaustion messages, Task 4's runner tests, Task 8's receipt fixtures, Task 9's prompt/argv tests); the **Phase 3 watch list** — guard 4's kill and sentence on a real timeout (the only event-changing guard; replay cannot show Pi's kill), and whether `self_test` is invoked at all under native bash (`runner.py:16-29` history) — the Pi facts once deferred (`--tools`, `tool_result.input`, `entry_appended`, `ui.confirm`) are answered from source and need no live check; anything that stopped with its named cause. Do **not** start Phase 2.

---

## Self-review against the spec

- **Component 1, contract derivation**: Task 3 (`derive.py`; Rulings 11, 12), Task 2 (fields), Task 10 (shown and confirmed before dispatch; Ruling 4). Ruling 2 on names.
- **Component 2, dispatch** (one fresh Pi, same model and native tools, plus the extension, worktree from HEAD, one process per operation): Task 9 (argv), Task 10 (`--go`/confirm → `runDelivery` → `deliver` → `attempt`, contract absolute; Ruling 5). Ruling 1 on native bash.
- **Component 3, guards 1–4 and symbol preservation** on `tool_call`, in the child only (Ruling 10): guard 1 reused (`engine.ts`; Task 5 learns `write`); guard 2 = `self_test` in the loop with the exit code (Task 4) and validation authoritative (Task 8); guard 3 (Task 5, resolved paths); guard 4 (Task 7, replay both directions plus a no-context fixture; live in Phase 3); symbol refusal for `edit` and `write` with what to do instead (Task 6).
- **Component 4, accepted tests carried read-only and run by the self-test**: Ruling 9; Task 4 (restore before every `self_test`), Task 8 (restore before validation; checks as files).
- **Component 5, compact results** (failed ids, first assertion line, from real `-q` output with `COLUMNS=500`; a successful edit returns the changed hunk — existing `mutation.py:_post_edit_region`; counted in tokens — `tokens_in`): Tasks 4, 8.
- **Component 6, receipt** (candidate commit, validation exit, turns, tool calls, tokens in/out, guard firings, budget state; one JSON file): Task 8 on the existing receipt; Task 10 writes it under `.git/satyrn/receipts/`.
- **Bounds ownership**: Task 7 mutates only `input.timeout`; no wrapper anywhere; `runner.py:39` owns the self-test bound and Task 4's 130 s exchange deadline is its ceiling (I4). "Frozen against measured suite durations": Task 1 (+ runner bound), Task 7's freeze gate, the evals pin, `test_bounds_pin.py`.
- **"Before the Phase 1 plan freezes, no inference"**: Task 1 (public suite and `grade`, exit codes recorded, no-suite tasks excluded). The decode-rate item is answered offline in the deep dive (Q4) and is not re-measured.
- **Roadmap sync**: Task 12.
- **Gates, provenance, tiers**: every task's last step; new files recorded; subprocess only in `integration` tests and in CLI paths the default tier never runs; no fixture spawns the engine under `just gates` (M5).
- **Placeholder scan**: no TBD/TODO; every code step has code or names the exact existing code to change. Two "match the existing helper" notes (`_git` at `delivery.py:1373`, `child` at `test_orchestrator.mjs:58`) cite the line.
- **Type consistency**: `Contract.preserve/checks/token_budget` (Task 2) in Tasks 3, 4, 8, 9, 11; `TurnCounter` fields and `GUARD_KINDS` (Task 2) in Tasks 5–8 (entry kinds `loop_broken`, `scope_refused`, `symbol_preserved`, `command_bounded`, `command_timed_out`); `MutationContext.writable_paths/test_command/symbols/carried/base_commit` (Task 5) in Tasks 4, 6, 7, 11; `paths.resolveWorkspacePath` (Task 5) is the one key in `scope.ts`, `mutator.ts`, `engine.ts`; `createMutator(context, exchange, appendEntry)` (Task 5) in Task 6 and `tools/replay_events.mjs`; `runner.carried_paths`/`INFRASTRUCTURE` (Task 4) is the rule `attempt._prepare` (Task 5) and `delivery.restore_carried_at` (Task 8) both apply — one `git ls-tree -r --name-only <base>`, then one `checkout`; `buildDeriveInvocation` with `--` (Task 10) matches the `derive` parser (Task 3) and its stderr line `satyrn-engine: contract <path>`; `exercise_runner.mjs CONTEXT.json` (Task 4) matches the fake (Task 11).

## Review response

Opus review (`scratchpad/phase1-plan/review.md`), one line per Critical/Important finding:

- **C1** — Ruling 5 rewritten; Task 10 `buildDeliveryInvocation` passes an absolute path when the first segment is `.git`, with a test that fails on the current code; Task 11 dispatches through the real `attempt` with the contract under `.git`.
- **C2** — Ruling 3; Task 5 `registerMutator` listens on `tool_result` for `write` and `Mutator.noteWrite` sets `sha256(content)`; three `test_mutator.mjs` rows (write-then-edit digest, `isError` leaves the revision, new file not `REVISION_UNAVAILABLE`).
- **C3** — Ruling 9 replaced with restore-into-checkout; Task 4 `restore_carried` before every `self_test`, checks as explicit files, `COLUMNS=500`; Task 8 `restore_carried_at` after `_checkout_candidate`, checks as files, integration test with conftest, ini options and a check file; Task 3 excludes `preserve` from `writable_paths`.
- **I1** — Task 5 `resolveWorkspacePath` (strip `@`, resolve against the repo, refuse outside, relativize); fixtures `scope-traversal`, `scope-absolute-inside`; test rows.
- **I2** — Task 5 Python regex allows indentation; Task 6 `write` symbol check in `scope.ts`; fixtures `symbol-write-*`.
- **I3** — `pathless_edit` removed everywhere; noted as Phase 2 census over `tool_execution_end` errors (Task 5 text).
- **I4** — Task 4 `SELF_TEST_DEADLINE_MS = 130_000` passed by `runnerExtension`, test row; Global Constraints name `runner.py:39` as the owner; Task 1 `fits` checks the runner bound.
- **I5** — Ruling 1 cites `runner.py:16-29`; Task 4 schema open (`command` optional, ignored, `additionalProperties: true`); Task 13 Phase 3 watch list.
- **I6** — Task 4 summary regex for `-q` output (recorded in scratch), `ERROR` rows kept, fixture from real output, `COLUMNS=500` in runner and validation.
- **I7** — Ruling 12; Task 3 `self_test_command` reads `[tool.satyrn] self_test`, default `uv run python -m pytest -q`; Task 11 expectations follow.
- **I8** — Ruling 10; Tasks 5 and 7 gate on the mutation context, tests both directions (`bounds-no-context` fixture), `package.json` untouched.
- **I9** — Ruling 7 rewritten; `guardlog.ts` and `SATYRN_GUARD_LOG` dropped; guards use `pi.appendEntry`; Task 2 counts `entry_appended`; Task 8 `GuardFirings.from_counter`; replayer asserts `expectedEntries`; Task 11 fake emits `entry_appended`.
- **I10** — Task 1 handles tasks without `public_suite` (excluded from the longest), records `public_exits` and fails on non-zero, stop rule commits nothing and stops the whole phase (Global Constraints "Phase stop"; Task 7's gate restated); test for exclusion.
- **I11** — Task 11 uses the `attempt` command with the fake `pi` on `PATH`, absolute contract, temp-file arguments to `exercise_mutator.mjs`, one-argument `exercise_runner.mjs` (defined in Task 4), `[python, -m, pytest, -q]` offline, staging excludes residue (Task 8); second test body written.
- **I12** — Ruling 13; Task 2 `deliver` defaults `token_limit` from the contract, `_StreamOutcome` carries the one counter, token-exhaustion message with a `test_budget_delivery.py` row; Task 8 `count_spool` only when no budget is declared.
- **I13** — Ruling 11 (what carries over from HP1, what is new, why no import).
- **I14** — Task 3: new files under tracked directories are writable; `preserve` never writable; Task 9 prompt lists patterns with existing files and `(new file)`; `_prepare` no longer refuses a contract whose writable paths are all new.
- **Minors fixed**: M1 (Ruling 4, Task 10 confirm), M2 (Task 13 watch list), M3 (id includes HEAD), M4 (`--` before the request), M5 (Task 6 Files; replayer fake exchange), M6 (`Carried.absent`), M7 (receipt file), M8 (summary for every candidate-created outcome), M9 (`None` keys omitted), M10 (`command_timed_out` entry), M11 (`test_bounds_pin.py`), M12 (review-script note in Task 1), M13 (cacheRead stated), M14 (moot with I9), M15 (`DELIVERY_OK` line 29), M16 (noted in Task 7 test).
- **Minors left**: none.

Re-review (same file, "Re-review" section), one line per finding:

- **N1** (Critical) — Task 8 staging uses `':(exclude,glob)**/.venv/**' ':(exclude,glob)**/.pytest_cache/**' ':(exclude,glob)**/__pycache__/**'`; new integration rows: a `.gitignore` listing `.venv/` in the main fixture, and `test_a_gitignored_venv_does_not_fail_staging` under the real global git config.
- **N2** — Ruling 9 extended to a carried set (preserve + checks + tracked `conftest.py` files + tracked `pyproject.toml`/`pytest.ini`/`setup.cfg`/`tox.ini`); Task 4 `carried_paths`/`restore_carried(repo, contract, base)` and Task 8 `restore_carried_at` restore it before `self_test` and validation; preserve and checks run as explicit file arguments; `Carried` gains `infrastructure` and `tampered`; integration row `test_a_written_conftest_cannot_hide_a_failing_preserve_test`.
- **N3** — new `packages/engine/paths.ts` holds `resolveWorkspacePath`; scope, the mutator's revision map (seed, lookup, success, `noteWrite`) and the loop breaker key by it; `tests/test_paths.mjs`; `test_mutator.mjs` row "a write by absolute or @ path and an edit by relative path share one revision key"; `test_loop_breaker.mjs` row for read-by-absolute/write-by-relative.
- **N4** — Task 11 imports `from test_integration_attempt import ROOT, _fixture, _git` (bare name).
- **N5** — Task 11 asserts `writable_paths == ["app.py", "tests/test_app.py"]`, matching Task 3's rule (the fake still edits only `app.py`).
- **m1** — Task 4 `run_tests` gives its runs one shared deadline (`timeout - elapsed`), so the whole self-test stays under `runner.py:39`'s 120 s and the 130 s exchange ceiling is derived from it.
- **m2** — `count_spool(spool: BinaryIO)` takes the anonymous `TemporaryFile` handle and seeks to 0.
- **m3** — the compact rule keeps a passing run's tail including its progress dots; the combined expectation in Task 4's test now includes `.\n1 passed in 0.01s\n` per extra run.
- **m4** — Task 8's integration row asserts `changed_paths == ["app.py", "tests/test_keep.py"]` and `validation == "passed"`.
- **m5** — the mutation context carries `carried`; `scope.ts` refuses `write`/`edit` to a carried path with "restored before every self-test"; `scope-carried.json` fixture and a `test_scope.mjs` row.
- **m6** — the mutation context carries `base_commit`; `buildTestRequest` sends it; `RunTestsRequest.base_commit`; `run_tests` restores from it (HEAD only when absent).
- **m7** — the summary regex allows pytest's `(h:mm:ss)` suffix.
- **m8** — the confirm test passes a fake receipt writer.
- **m9** — Task 2 names `_StreamOutcome.turns_used` (`delivery.py:886-892`).
- **m10** — Task 1 wraps `grade()` per run and records `grade_error: …` in `grade_verdicts` instead of aborting `--write`.
- **Left**: none.
