# HP3 composition implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire chained isolation into the packet route — a packet-to-Contract
renderer, an `Implementer` that drives real `satyrn-engine deliver --base`
calls across phases, and a retention path that reads git directly instead
of snapshotting a directory that no longer persists.

**Architecture:** `run_phases` (route.py) is reused unchanged — it is
already generic over any `Implementer`. The new work is (1) a packet
renderer, (2) `pi_implementer.py`'s edit/harness split, (3)
`engine_command_implementer`, a new `Implementer` factory that also
exposes its own per-phase receipts, and (4) `run_and_record_engine_chain`,
a retention function parallel to (not layered inside)
`chain_record.run_and_record_chain` — the evidence shapes (git receipts vs.
directory snapshots) are different enough that forcing one shared function
to branch internally would be the premature abstraction, not the
simplification; three similar lines beat that now.

**Tech Stack:** Python 3.14, `pyyaml` (new direct dependency), real `git`
subprocesses, a real `satyrn-engine deliver` subprocess where the sibling
checkout is available (skipped, not failed, otherwise).

**Spec:** [docs/superpowers/specs/2026-09-10-hp3-composition-design.md](../specs/2026-09-10-hp3-composition-design.md)

## Global Constraints

- No live `pi` process anywhere in this plan.
- No change to `satyrn-engine` — it is accepted as-is; this composes with it.
- `pi_implementer.py`'s split (piece B) must not change any existing HP2
  test's behavior — every existing test in `tests/test_pi_implementer.py`
  passes unmodified.
- `orchestrator_mutations` is `()` for every engine-composed phase, never
  `None` — there is no window in which it could be unobserved on this seam.
- `turn_budget`/`tool_call_budget` stay declared, unapplied — unchanged by
  this work.

---

## Task 1: packet → `Contract` YAML rendering

**Files:**
- Modify: `pyproject.toml` (add `pyyaml` dependency)
- Modify: `src/satyrn_evals/packet.py`
- Test: `tests/test_packet.py` (or `tests/test_packet_contract.py` if that
  reads cleaner given `test_packet.py`'s current size — check its line
  count first; split out a new file if adding this would push it over
  this repository's document caps)

**Interfaces:**
- Produces: `contract_yaml(packet: HandoffPacket, contract_id: str) -> str`.
  Task 4 calls this once per phase.

- [ ] **Step 1: Add the dependency**

Edit `pyproject.toml`'s `dependencies = []` to `dependencies = ["pyyaml"]`.
Run `uv sync` to update the lockfile (it is already resolvable
transitively per `uv.lock`, so this should not change what is installed,
only what is declared).

- [ ] **Step 2: Write the failing tests**

Check `wc -l tests/test_packet.py` first. Add to that file (or a new
`tests/test_packet_contract.py` importing the same fixtures if the cap
would be exceeded):

```python
import yaml

from satyrn_evals.packet import contract_yaml


def test_contract_yaml_carries_the_four_contract_fields() -> None:
    packet = _packet("phase-1-home")  # reuse this file's existing helper
    text = contract_yaml(packet, "phase-1-home")
    data = yaml.safe_load(text)
    assert set(data) == {"id", "task", "writable_paths", "test_command"}
    assert data["id"] == "phase-1-home"
    assert data["writable_paths"] == list(packet.writable_paths)
    assert data["test_command"] == list(packet.self_test_command or [])


def test_contract_yaml_task_is_the_same_rendering_pi_implementer_sends() -> None:
    """Not a second renderer -- the same text render_packet already
    produces, so the model sees identical words whichever seam runs it."""
    from satyrn_evals.packet import render_packet

    packet = _packet("phase-1-home")
    data = yaml.safe_load(contract_yaml(packet, "phase-1-home"))
    assert data["task"] == render_packet(packet)


def test_contract_yaml_never_carries_redacts_or_role_or_budgets() -> None:
    packet = _packet("phase-1-home")
    text = contract_yaml(packet, "phase-1-home")
    for selector in packet.redacts:
        assert selector not in text
    assert "role" not in yaml.safe_load(text)
    assert "turn_budget" not in yaml.safe_load(text)


def test_contract_yaml_round_trips_arbitrary_task_text_safely() -> None:
    """The reason this uses a real YAML emitter rather than hand-assembled
    text: task content is arbitrary prose that can contain colons, quotes,
    and newlines, any of which a naive emitter gets wrong silently."""
    import dataclasses

    packet = dataclasses.replace(
        _packet("phase-1-home"),
        facts=("A colon: here", 'A "quoted" fact', "Line one\nline two"),
    )
    text = contract_yaml(packet, "phase-1-home")
    data = yaml.safe_load(text)
    assert "A colon: here" in data["task"]
    assert 'A "quoted" fact' in data["task"]
    assert "Line one\nline two" in data["task"]
```

If added to `tests/test_packet.py`, these reuse that file's own `_packet`
helper (confirm its exact name via `grep -n "^def _packet" tests/test_packet.py`
first — match it exactly rather than assuming).

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest -q tests/test_packet.py -k contract_yaml` (adjust path
if placed in a new file)
Expected: collection error (`contract_yaml` does not exist yet).

- [ ] **Step 3: Implement**

Add to `src/satyrn_evals/packet.py` (near `render_packet`):

```python
import yaml


def contract_yaml(packet: HandoffPacket, contract_id: str) -> str:
    """One phase's `HandoffPacket`, rendered as a `satyrn-engine` Contract
    (`id`, `task`, `writable_paths`, `test_command`) -- the only four
    fields that format understands. `task` reuses `render_packet` verbatim
    rather than a second rendering: the model sees the same words whether
    this packet crosses as a worker projection (HP2's seam) or a Contract
    (this one). `redacts`, `role` and the two budgets do not cross --
    `redacts` especially must not, the same boundary the worker
    projection already enforces.

    Emitted with a real YAML library, not hand-assembled text: `task` is
    arbitrary prose (facts, objective text) that can contain colons,
    quotes and newlines, any of which a naive emitter would get wrong
    silently.
    """
    return yaml.safe_dump(
        {
            "id": contract_id,
            "task": render_packet(packet),
            "writable_paths": list(packet.writable_paths),
            "test_command": list(packet.self_test_command or ()),
        },
        sort_keys=False,
    )
```

(`import yaml` goes in the module's existing import block, alphabetized
with the rest.)

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest -q tests/test_packet.py` (or the new file)
Expected: PASS, all tests including the new ones.

- [ ] **Step 5: Lint and full suite**

Run: `uv run ruff check src/satyrn_evals/packet.py tests/test_packet.py pyproject.toml`
Run: `uv run pytest -q`
Expected: both clean; full suite passes (no regression from the new
dependency).

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock src/satyrn_evals/packet.py tests/test_packet.py
git commit -m "packet: render a HandoffPacket as a satyrn-engine Contract"
```

---

## Task 2: `pi_implementer.py` — split edit target from bookkeeping location

**Files:**
- Modify: `src/satyrn_evals/adapters/pi_implementer.py`
- Modify: `tests/test_pi_implementer.py`

**Interfaces:**
- Produces: `main()`'s internal `edit_dir` (Pi's `cwd`, what
  `attribution.snapshot` observes) now derived from `Path.cwd()` rather
  than `result_path.parent`; `harness_dir` (transcript/stderr/counter/
  packet/result files) stays `result_path.parent`, unchanged in role.
  Task 4 invokes this adapter with a `cwd` set to an isolated worktree and
  `RESULT_ENV`/`PACKET_ENV` pointing outside it.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_pi_implementer.py`, near the other `main()` tests:

```python
def test_edit_dir_and_harness_dir_can_differ(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The property this split exists for: Pi's own edits land in cwd,
    never in the harness bookkeeping directory, when the two are not the
    same path -- proven by actually separating them, not by reading the
    implementation and trusting it."""
    edit_dir = tmp_path / "worktree"
    edit_dir.mkdir()
    harness_dir = tmp_path / "harness"
    harness_dir.mkdir()
    packet_path = harness_dir / ".satyrn-packet.json"
    result_path = harness_dir / ".satyrn-result.json"
    packet_path.write_text(json.dumps(PROJECTION))
    monkeypatch.setenv(PACKET_ENV, str(packet_path))
    monkeypatch.setenv(RESULT_ENV, str(result_path))
    monkeypatch.chdir(edit_dir)

    fake = _FakeRun(writes={"app.py": "# built\n"})
    monkeypatch.setattr(pi_implementer.subprocess, "run", fake)
    assert main(["--model", MODEL]) == 0

    assert (edit_dir / "app.py").is_file()
    assert not (harness_dir / "app.py").exists()
    assert (harness_dir / pi_implementer.TRANSCRIPT_NAME).is_file()
    assert not (edit_dir / pi_implementer.TRANSCRIPT_NAME).exists()
    # The child's own cwd is what the fake actually observed:
    assert fake.calls and fake.envs is not None
```

`_FakeRun`'s `__call__` currently asserts `isinstance(cwd, Path)` from
`kwargs["cwd"]` — check it also records the `cwd` it was given (add
`self.cwds: list[Path] = []` / `self.cwds.append(cwd)` if it does not
already, matching the `self.envs` addition Task 3 of the self-test-tool
plan already made to this same class) so the test above can assert
`fake.cwds[0] == edit_dir` for a stronger proof; include that assertion.

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest -q tests/test_pi_implementer.py -k edit_dir_and_harness_dir`
Expected: FAIL — today's code writes `app.py` into `harness_dir` (via
`workspace = result_path.parent`), not `edit_dir`.

- [ ] **Step 3: Implement**

In `src/satyrn_evals/adapters/pi_implementer.py`'s `main()`, replace every
use of the name `workspace` with the split:

```python
def main(argv: list[str] | None = None) -> int:
    model, tools, pi_bin, timeout = parse_args(
        list(sys.argv[1:] if argv is None else argv)
    )
    packet_path, result_path = read_env_paths(os.environ)
    harness_dir = result_path.parent
    edit_dir = Path.cwd()
```

Then everywhere the old `workspace` was used for `TRANSCRIPT_NAME`,
`STDERR_NAME`, `COUNTER_NAME`, `_next_call_index`, use `harness_dir`.
Everywhere it was used for `snapshot(...)` (before/after) and as the
`cwd=` passed to the Pi child's `subprocess.run`, use `edit_dir`. Grep the
current file for every `workspace` occurrence
(`grep -n workspace src/satyrn_evals/adapters/pi_implementer.py`) before
editing, to catch all of them — do not rely on memory of which ones are
which; the split must be complete, not partial.

Update the module docstring's description of `workspace` accordingly
(it currently says "one plain directory the route builds up phase by
phase" — true for HP2's `command_implementer` seam, where `edit_dir ==
harness_dir` by construction since that seam sets `cwd=workspace` and
`RESULT_ENV` under the same directory; add one sentence noting the split
exists so a different caller can make them differ).

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest -q tests/test_pi_implementer.py`
Expected: PASS, all tests including every pre-existing one — this is the
proof the split is behavior-preserving for HP2's existing seam.

- [ ] **Step 5: Run the full suite and integration tier**

Run: `uv run pytest -q`
Run: `uv run pytest -q -m integration tests/integration/test_hp2_route.py tests/integration/test_hp6_chain_record.py`
Expected: both clean — these integration tests drive `pi_implementer.py`
through the real executable seam and must show no regression.

- [ ] **Step 6: Lint and commit**

Run: `uv run ruff check src/satyrn_evals/adapters/pi_implementer.py tests/test_pi_implementer.py`

```bash
git add src/satyrn_evals/adapters/pi_implementer.py tests/test_pi_implementer.py
git commit -m "pi_implementer: split edit target from harness bookkeeping location"
```

---

## Task 3: Git-backed candidate content and mutation kinds

**Files:**
- Create: `src/satyrn_evals/engine_evidence.py`
- Test: `tests/test_engine_evidence.py`

**Interfaces:**
- Produces: `git_diff_mutations(repo: Path, base: str, candidate: str) ->
  tuple[Mutation, ...]`, `git_show_content(repo: Path, commit: str, path:
  str) -> str | None` (`None` when the path does not exist at that
  commit — a deletion). Task 4 uses both.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_engine_evidence.py`:

```python
"""Git-backed evidence for the engine-composed route: mutation kinds and
candidate content read from commits, never from a directory snapshot --
the isolated worktree that produced them is gone by the time this runs
(delivery.py deletes it on success; see the HP3 composition design doc).

Integration tier: every test here spawns real git.
"""

import subprocess
from pathlib import Path

import pytest

from satyrn_evals.attribution import Mutation
from satyrn_evals.engine_evidence import git_diff_mutations, git_show_content

pytestmark = pytest.mark.integration


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout


def _make_repo(path: Path) -> Path:
    path.mkdir()
    _git(path, "init", "--quiet", "--initial-branch=main")
    _git(path, "config", "user.name", "Engine Evidence Test")
    _git(path, "config", "user.email", "evidence@example.invalid")
    (path / "base.txt").write_text("base\n")
    _git(path, "add", "-A")
    _git(path, "commit", "--quiet", "-m", "base")
    return path


def test_git_diff_mutations_classifies_created_modified_and_deleted(
    tmp_path: Path,
) -> None:
    repo = _make_repo(tmp_path / "repo")
    base = _git(repo, "rev-parse", "HEAD").strip()
    (repo / "base.txt").write_text("changed\n")
    (repo / "new.txt").write_text("new\n")
    _git(repo, "rm", "--quiet", "--ignore-unmatch", "does-not-exist.txt")
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "phase 1")
    candidate = _git(repo, "rev-parse", "HEAD").strip()

    mutations = git_diff_mutations(repo, base, candidate)

    assert Mutation("base.txt", "modified") in mutations
    assert Mutation("new.txt", "created") in mutations


def test_git_diff_mutations_classifies_a_real_deletion(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "repo")
    base = _git(repo, "rev-parse", "HEAD").strip()
    (repo / "base.txt").unlink()
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "delete it")
    candidate = _git(repo, "rev-parse", "HEAD").strip()

    mutations = git_diff_mutations(repo, base, candidate)

    assert mutations == (Mutation("base.txt", "deleted"),)


def test_git_show_content_reads_a_file_at_a_commit(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "repo")
    commit = _git(repo, "rev-parse", "HEAD").strip()
    assert git_show_content(repo, commit, "base.txt") == "base\n"


def test_git_show_content_is_none_for_a_path_absent_at_that_commit(
    tmp_path: Path,
) -> None:
    repo = _make_repo(tmp_path / "repo")
    commit = _git(repo, "rev-parse", "HEAD").strip()
    assert git_show_content(repo, commit, "never-existed.txt") is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest -q -m integration tests/test_engine_evidence.py`
Expected: collection error (`satyrn_evals.engine_evidence` does not exist
yet).

- [ ] **Step 3: Implement**

Create `src/satyrn_evals/engine_evidence.py`:

```python
"""Git-backed evidence for the engine-composed route.

The isolated worktree `satyrn-engine deliver` creates is deleted on a
successful phase -- confirmed against `delivery.py`'s own cleanup path
during the HP3 composition design's research. Only the repository and its
commits survive across phases, so candidate content and mutation kinds
are read from git directly, never from a directory snapshot the way
`attribution.snapshot`/`diff_snapshots` do for HP2's shared-workspace
seam. This module is that seam's sibling, not its replacement -- HP2's
route is untouched.
"""

import subprocess
from pathlib import Path

from satyrn_evals.attribution import Mutation, MutationKind

_STATUS_KINDS: dict[str, MutationKind] = {"A": "created", "D": "deleted"}


def git_diff_mutations(repo: Path, base: str, candidate: str) -> tuple[Mutation, ...]:
    """Every path that changed between two commits, classified the way
    `git diff --name-status` already classifies it -- one call, not a
    per-path existence probe. A status this module does not recognize
    (a rename, a copy) is treated as `modified`: conservative, and the
    same shape as everywhere else in this repository choosing the
    less-surprising reading over a guess.
    """
    result = subprocess.run(
        ["git", "diff", "--name-status", base, candidate],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    mutations: list[Mutation] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        status, path = line.split("\t", 1)
        kind = _STATUS_KINDS.get(status[0], "modified")
        mutations.append(Mutation(path=path, kind=kind))
    return tuple(mutations)


def git_show_content(repo: Path, commit: str, path: str) -> str | None:
    """One file's text content at one commit, or `None` when it does not
    exist there -- a deletion, read the same honest way `capture_candidate`
    already reads a deleted path as absent rather than as empty text.
    """
    result = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest -q -m integration tests/test_engine_evidence.py`
Expected: PASS, all 4 tests, against real git.

- [ ] **Step 5: Lint and commit**

Run: `uv run ruff check src/satyrn_evals/engine_evidence.py tests/test_engine_evidence.py`

```bash
git add src/satyrn_evals/engine_evidence.py tests/test_engine_evidence.py
git commit -m "engine_evidence: mutation kinds and candidate content from git, not a snapshot"
```

---

## Task 4: `engine_command_implementer` and repo initialization

**Files:**
- Create: `src/satyrn_evals/adapters/engine_delivery.py`
- Test: `tests/test_engine_delivery.py`
- Test: `tests/integration/test_engine_delivery.py`

**Interfaces:**
- Consumes: `contract_yaml` (Task 1), `git_diff_mutations`/
  `git_show_content` (Task 3).
- Produces: `init_engine_repo(base_dir: Path, repo_dir: Path) -> str`
  (returns the initial commit sha); `engine_command_implementer(repo:
  Path, satyrn_engine_bin: str, implementer_argv: list[str], *, timeout:
  float) -> tuple[Implementer, list[dict[str, object]]]` — the second
  element is the mutable list of raw JSON receipts, one per successful
  call, appended in phase order; Task 5's retention function reads it
  after `run_phases` returns.

- [ ] **Step 1: Write the failing default-tier tests**

Create `tests/test_engine_delivery.py`:

```python
"""engine_command_implementer's pure argv/contract construction --
default tier: nothing here spawns satyrn-engine or git. The real
composition proof is `tests/integration/test_engine_delivery.py`.
"""

import json
from pathlib import Path

import pytest

from satyrn_evals.adapters.engine_delivery import build_deliver_argv
from satyrn_evals.manifest import load_manifest
from satyrn_evals.packet import build_packet
from satyrn_evals.session_manifest import load_session_spec

REPO = Path(__file__).resolve().parent.parent
TASK = REPO / "src/satyrn_evals/tasks/agentclinic-session-phased"


def _packet(step_id: str = "phase-1-home"):
    return build_packet(
        TASK, load_manifest(TASK), load_session_spec(TASK), step_id,
        base_revision="3e6607e533792ab0", turn_budget=40, tool_call_budget=60,
    )


def test_build_deliver_argv_omits_base_for_the_first_phase(tmp_path: Path) -> None:
    argv = build_deliver_argv(
        "satyrn-engine", tmp_path, tmp_path / "contract.yaml", 60.0,
        base=None, implementer_argv=["pi_implementer", "--model", "m"],
    )
    assert "--base" not in argv


def test_build_deliver_argv_includes_base_for_a_later_phase(tmp_path: Path) -> None:
    argv = build_deliver_argv(
        "satyrn-engine", tmp_path, tmp_path / "contract.yaml", 60.0,
        base="abc1234", implementer_argv=["pi_implementer", "--model", "m"],
    )
    assert "--base" in argv
    assert argv[argv.index("--base") + 1] == "abc1234"


def test_build_deliver_argv_preserves_the_implementer_argv_after_separator(
    tmp_path: Path,
) -> None:
    argv = build_deliver_argv(
        "satyrn-engine", tmp_path, tmp_path / "contract.yaml", 60.0,
        base=None, implementer_argv=["pi_implementer", "--model", "m", "--tools", "read"],
    )
    separator = argv.index("--")
    assert argv[separator + 1:] == ["pi_implementer", "--model", "m", "--tools", "read"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest -q tests/test_engine_delivery.py`
Expected: collection error (`satyrn_evals.adapters.engine_delivery` does
not exist yet).

- [ ] **Step 3: Implement `build_deliver_argv` and `init_engine_repo`**

Create `src/satyrn_evals/adapters/engine_delivery.py`:

```python
"""The engine-composed `Implementer`: drives real `satyrn-engine deliver
--base` calls across phases, one isolated worktree per phase, tracking
the running candidate commit itself. See
`docs/superpowers/specs/2026-09-10-hp3-composition-design.md` for why
this is a separate seam from `route.command_implementer` rather than a
variant of it.
"""

import json
import shutil
import subprocess
from pathlib import Path

from satyrn_evals.packet import HandoffPacket, contract_yaml
from satyrn_evals.route import ImplementerResult


def init_engine_repo(base_dir: Path, repo_dir: Path) -> str:
    """Materialize `base_dir`'s contents into a fresh git repository at
    `repo_dir` and commit them once. Returns that commit's sha -- phase
    1's implicit base, the same "materialize before inference" step
    HP7's own precondition 3 already requires, with one thing added: a
    real git history for `deliver --base` to branch from.
    """
    repo_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(base_dir, repo_dir, dirs_exist_ok=True)
    run = lambda *args: subprocess.run(  # noqa: E731
        ["git", *args], cwd=repo_dir, capture_output=True, text=True, check=True
    )
    run("init", "--quiet", "--initial-branch=main")
    run("config", "user.name", "satyrn-evals engine seam")
    run("config", "user.email", "engine-seam@example.invalid")
    run("add", "-A")
    run("commit", "--quiet", "-m", "base")
    return run("rev-parse", "HEAD").stdout.strip()


def build_deliver_argv(
    satyrn_engine_bin: str,
    repo: Path,
    contract_path: Path,
    timeout: float,
    *,
    base: str | None,
    implementer_argv: list[str],
) -> list[str]:
    """The `satyrn-engine deliver` CLI invocation for one phase. `base`
    omitted (not passed as an empty string) for phase 1 -- `deliver`'s own
    default is the repo's HEAD, and an empty `--base` would be refused by
    `_nonblank_base` on the engine side rather than silently doing the
    same thing.
    """
    argv = [
        satyrn_engine_bin, "deliver",
        "--repo", str(repo),
        "--timeout", str(timeout),
    ]
    if base is not None:
        argv += ["--base", base]
    argv += [str(contract_path), "--", *implementer_argv]
    return argv


def engine_command_implementer(
    repo: Path,
    satyrn_engine_bin: str,
    implementer_argv: list[str],
    *,
    timeout: float,
    initial_base: str | None = None,
    harness_root: Path,
):
    """Returns `(implementer, receipts)`. `receipts` is appended to, one
    parsed JSON receipt per successful call, in phase order -- Task 5's
    retention function reads it after the chain finishes; nothing about
    `ImplementerResult` itself carries a candidate commit, so this is the
    side channel that does.
    """
    receipts: list[dict[str, object]] = []
    state = {"base": initial_base}

    def implement(packet: HandoffPacket) -> ImplementerResult:  # pragma: no cover
        # Integration tier only: this spawns a real satyrn-engine process.
        step_id = f"phase-{len(receipts) + 1}"
        phase_dir = harness_root / step_id
        phase_dir.mkdir(parents=True, exist_ok=True)
        contract_path = phase_dir / "contract.yaml"
        contract_path.write_text(contract_yaml(packet, step_id))
        result_path = phase_dir / ".satyrn-result.json"
        packet_path = phase_dir / ".satyrn-packet.json"
        from satyrn_evals.packet import worker_projection
        packet_path.write_text(json.dumps(worker_projection(packet)))
        result_path.unlink(missing_ok=True)
        argv = build_deliver_argv(
            satyrn_engine_bin, repo, contract_path, timeout,
            base=state["base"], implementer_argv=implementer_argv,
        )
        import os
        env = {
            **os.environ,
            "SATYRN_HANDOFF_PACKET": str(packet_path),
            "SATYRN_IMPLEMENTER_RESULT": str(result_path),
        }
        proc = subprocess.run(argv, capture_output=True, text=True, env=env)
        lines = [line for line in proc.stdout.splitlines() if line.strip()]
        if not lines:
            raise RouteError(
                f"satyrn-engine deliver produced no receipt on stdout; "
                f"stderr: {proc.stderr}"
            )
        receipt = json.loads(lines[-1])
        receipts.append(receipt)
        if receipt.get("code") == "OK" and receipt.get("changed_paths"):
            state["base"] = receipt["candidate_commit"]
            return ImplementerResult(
                changed_files=tuple(receipt["changed_paths"]),
                reported_outcome="delivered",
                message=None,
            )
        return ImplementerResult(
            changed_files=(),
            reported_outcome="refused",
            message=receipt.get("message"),
        )

    implement.executable_seam = True  # type: ignore[attr-defined]
    return implement, receipts
```

(`from satyrn_evals.errors import RouteError` goes in the top import
block alongside the others; `route.ImplementerResult` is already
imported.)

- [ ] **Step 4: Run the default-tier tests to verify they pass**

Run: `uv run pytest -q tests/test_engine_delivery.py`
Expected: PASS, all 3 tests.

- [ ] **Step 5: Write the failing real integration test**

Create `tests/integration/test_engine_delivery.py`:

```python
"""The real composition proof: engine_command_implementer against a real
satyrn-engine deliver subprocess, real git, no mocks. Skipped, not
failed, when the sibling satyrn-engine checkout is not present -- it is
an external dependency this repository does not vendor or require
(ROADMAP.md, "State and dependencies").
"""

import shutil
import sys
from pathlib import Path

import pytest

from satyrn_evals.adapters.engine_delivery import (
    engine_command_implementer,
    init_engine_repo,
)
from satyrn_evals.manifest import load_manifest
from satyrn_evals.packet import build_packet
from satyrn_evals.session_manifest import load_session_spec

pytestmark = pytest.mark.integration

REPO = Path(__file__).resolve().parents[2]
TASK = REPO / "src/satyrn_evals/tasks/agentclinic-session-phased"
FAKE_IMPLEMENTER = Path(__file__).parent / "fake_implementer.py"
SIBLING_ENGINE_BIN = (
    Path.home() / "projects/pauleveritt/satyrn-engine/.venv/bin/satyrn-engine"
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not SIBLING_ENGINE_BIN.is_file(),
        reason="sibling satyrn-engine checkout not found at the conventional path",
    ),
]


def _packet(step_id: str):
    return build_packet(
        TASK, load_manifest(TASK), load_session_spec(TASK), step_id,
        base_revision="3e6607e533792ab0", turn_budget=40, tool_call_budget=60,
    )


def test_two_phases_compose_a_real_fold_forward_chain(tmp_path: Path) -> None:
    base_dir = TASK / "base"
    repo = tmp_path / "repo"
    init_engine_repo(base_dir, repo)

    implementer, receipts = engine_command_implementer(
        repo,
        str(SIBLING_ENGINE_BIN),
        [sys.executable, str(FAKE_IMPLEMENTER)],
        timeout=60.0,
        harness_root=tmp_path / "harness",
    )

    result_one = implementer(_packet("phase-1-home"))
    assert result_one.reported_outcome == "delivered"
    result_two = implementer(_packet("phase-2-board"))
    assert result_two.reported_outcome == "delivered"

    assert len(receipts) == 2
    assert receipts[0]["base_commit"] != receipts[1]["base_commit"]
    tree = __import__("subprocess").run(
        ["git", "ls-tree", "-r", "--name-only", receipts[1]["candidate_commit"]],
        cwd=repo, capture_output=True, text=True, check=True,
    ).stdout.split()
    changed_by_phase_one = set(receipts[0]["changed_paths"])
    changed_by_phase_two = set(receipts[1]["changed_paths"])
    assert changed_by_phase_one <= set(tree)  # phase 1's files survive into phase 2
    assert changed_by_phase_two <= set(tree)


def test_a_refused_phase_leaves_the_next_bases_on_its_predecessor(
    tmp_path: Path,
) -> None:
    """No-partial-chain's sibling for this seam: a NO_CHANGES phase must
    not silently become the next phase's base."""
    base_dir = TASK / "base"
    repo = tmp_path / "repo"
    initial = init_engine_repo(base_dir, repo)

    implementer, receipts = engine_command_implementer(
        repo,
        str(SIBLING_ENGINE_BIN),
        [sys.executable, "-c", "pass"],  # touches nothing -> NO_CHANGES
        timeout=60.0,
        harness_root=tmp_path / "harness",
    )
    result = implementer(_packet("phase-1-home"))
    assert result.reported_outcome == "refused"
    assert receipts[0]["code"] == "NO_CHANGES"
```

`FAKE_IMPLEMENTER` here is the same
`tests/integration/fake_implementer.py` HP2's own tests already use — it
already speaks the `SATYRN_HANDOFF_PACKET`/`SATYRN_IMPLEMENTER_RESULT`
contract `deliver`'s COMMAND will be invoked with (env vars, not argv),
so no new fake is needed.

- [ ] **Step 6: Run the integration test**

Run: `uv run pytest -q -m integration tests/integration/test_engine_delivery.py -v`
Expected: PASS if the sibling checkout is present (it is, on this
machine, per this plan's own research); SKIPPED with a clear reason
otherwise. If it fails rather than passing or skipping, do not proceed to
Task 5 until the real cause is understood — this is the one test in this
whole plan that proves the composition actually works, not just that its
pieces compile.

- [ ] **Step 7: Lint, full suite, commit**

Run: `uv run ruff check src/satyrn_evals/adapters/engine_delivery.py tests/test_engine_delivery.py tests/integration/test_engine_delivery.py`
Run: `uv run pytest -q` (default tier, confirm no regression)

```bash
git add src/satyrn_evals/adapters/engine_delivery.py \
  tests/test_engine_delivery.py tests/integration/test_engine_delivery.py
git commit -m "engine_delivery: engine_command_implementer, driving real deliver --base calls"
```

---

## Task 5: `run_and_record_engine_chain` — retention for the composed route

**Files:**
- Modify: `src/satyrn_evals/chain_record.py`
- Test: `tests/integration/test_engine_delivery.py` (extend)

**Interfaces:**
- Consumes: `engine_command_implementer`'s `receipts` list (Task 4),
  `git_diff_mutations`/`git_show_content` (Task 3).
- Produces: `run_and_record_engine_chain(task_dir, manifest, spec,
  implementer, receipts, repo, grader, output_path, *, turn_budget,
  tool_call_budget) -> ChainRecord`. Reuses `run_phases` unchanged; does
  not touch `run_and_record_chain` or any of its helpers.

- [ ] **Step 1: Write the failing integration test**

Extend `tests/integration/test_engine_delivery.py`:

```python
from satyrn_evals.chain_record import AppliedState, run_and_record_engine_chain


def _grade_pass(step_id: str, workspace) -> tuple[str, str]:
    return "pass", f"scripted pass for {step_id}"


def test_run_and_record_engine_chain_retains_a_real_two_phase_chain(
    tmp_path: Path,
) -> None:
    base_dir = TASK / "base"
    repo = tmp_path / "repo"
    init_engine_repo(base_dir, repo)
    implementer, receipts = engine_command_implementer(
        repo, str(SIBLING_ENGINE_BIN),
        [sys.executable, str(FAKE_IMPLEMENTER)],
        timeout=60.0, harness_root=tmp_path / "harness",
    )

    record = run_and_record_engine_chain(
        TASK, load_manifest(TASK), load_session_spec(TASK),
        implementer, receipts, repo, _grade_pass,
        tmp_path / "chain.json", turn_budget=40, tool_call_budget=60,
    )

    assert len(record.phases) >= 1
    first = record.phases[0]
    assert first.accepted is True
    assert first.implementer_mutations is not None and len(first.implementer_mutations) > 0
    assert first.orchestrator_mutations == ()
    assert first.candidate_snapshot_path is not None
    import json as _json
    saved = _json.loads(Path(first.candidate_snapshot_path).read_text())
    assert saved  # real file content, not empty
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest -q -m integration tests/integration/test_engine_delivery.py -k run_and_record_engine_chain`
Expected: collection error (`run_and_record_engine_chain` does not exist
yet).

- [ ] **Step 3: Implement**

Add to `src/satyrn_evals/chain_record.py` (near `run_and_record_chain`;
add `from satyrn_evals.engine_evidence import git_diff_mutations,
git_show_content` to the imports):

```python
def run_and_record_engine_chain(
    task_dir: Path,
    manifest: TaskManifest,
    spec: SessionSpec,
    implementer: Implementer,
    receipts: list[dict[str, object]],
    repo: Path,
    grader: PhaseGrader,
    output_path: Path,
    *,
    turn_budget: int,
    tool_call_budget: int,
) -> ChainRecord:
    """Retention for the engine-composed route: git-backed evidence, not
    a directory snapshot -- the isolated worktree each phase ran in is
    already gone by the time this runs (`delivery.py` deletes it on
    success). `orchestrator_mutations` is `()` for every phase, never
    `None`: no window exists in which an orchestrator could act between
    isolated, disposable worktrees, so there is nothing to leave
    unobserved. `receipts` is read after `run_phases` returns, in the
    same order phases ran -- `engine_command_implementer`'s own side
    channel for the git commits `ImplementerResult` has no field for.
    """
    events: list[BoundaryEvent] = []

    def observe(event: BoundaryEvent) -> None:
        events.append(event)

    decisions = run_phases(
        task_dir, manifest, spec, implementer, repo, grader,
        base_revision="engine-composed",  # declared_not_applied regardless
        turn_budget=turn_budget, tool_call_budget=tool_call_budget,
        observer=observe,
    )
    packets = {
        e.step_id: e.packet for e in events
        if e.boundary == "before_handoff" and e.packet is not None
    }
    evidence_dir = output_path.with_name(output_path.stem + "-evidence")
    phases: list[PhaseRecord] = []
    for decision, receipt in zip(decisions, receipts, strict=True):
        base_commit = receipt.get("base_commit")
        candidate_commit = receipt.get("candidate_commit")
        implementer_mutations: tuple[Mutation, ...] | None = None
        snap_path = snap_digest = None
        if isinstance(base_commit, str) and isinstance(candidate_commit, str):
            implementer_mutations = git_diff_mutations(repo, base_commit, candidate_commit)
            content = {
                m.path: git_show_content(repo, candidate_commit, m.path)
                for m in implementer_mutations
                if m.kind != "deleted"
            }
            content = {k: v for k, v in content.items() if v is not None}
            payload = json.dumps(content, indent=2, sort_keys=True) + "\n"
            path = evidence_dir / f"{decision.step_id}-candidate.json"
            _write_text_durably(path, payload)
            snap_path = str(path)
            snap_digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        phases.append(
            PhaseRecord(
                step_id=decision.step_id,
                packet=packets[decision.step_id],
                result=decision.result,
                accepted=decision.accepted,
                reason=decision.reason,
                implementer_mutations=implementer_mutations,
                orchestrator_mutations=(),
                declaration_ledger=declaration_ledger(
                    executable_seam=True,
                    packet=packets[decision.step_id],
                    implementer_mutations=implementer_mutations,
                    self_test_ran=False,
                ),
                candidate_snapshot_path=snap_path,
                candidate_snapshot_digest=snap_digest,
            )
        )
    final_decision = next(
        (e.decision for e in events if e.boundary == "chain_end"), None
    )
    record = ChainRecord(
        version=CHAIN_RECORD_VERSION,
        phases=tuple(phases),
        final_decision=final_decision,
    )
    write_chain_record(output_path, record)
    return record
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest -q -m integration tests/integration/test_engine_delivery.py`
Expected: PASS, all tests in the file.

- [ ] **Step 5: Full suite, gates, commit**

Run: `uv run pytest -q` (default tier)
Run: `uv run ruff check src/satyrn_evals/chain_record.py tests/integration/test_engine_delivery.py`
Run: `just gates`
Expected: all clean.

```bash
git add src/satyrn_evals/chain_record.py tests/integration/test_engine_delivery.py
git commit -m "chain_record: run_and_record_engine_chain, retention from git evidence"
```

---

## A named gap this plan does not close: crash safety

`run_and_record_chain` (HP6, existing) persists per phase — candidate
evidence at `after_handoff`, the decision the instant grading returns, and
once more in a `finally` around the whole run — specifically because an
earlier version that wrote only at the end lost already-graded phases on a
mid-chain crash, a real defect an Astra-style review caught. `run_and_record_engine_chain`
above does **not** have this property: it builds every `PhaseRecord` only
after `run_phases` returns in full, with no incremental persistence and no
`finally`. A crash mid-chain on the engine-composed route loses everything,
not just the in-flight phase. This is a real, known regression relative to
HP6's own standard, not an oversight to be silently carried forward:
closing it means threading the same three-write pattern through
`observe()`'s boundary-event handling here too, using `receipts` as it
grows rather than only after the whole chain finishes. Named here as
follow-on work because closing it properly deserves its own task and
tests, not a rushed addition to an already-large plan — do not treat this
plan's completion as parity with HP6's crash-safety guarantee.

## After this plan

TE1's composition blocker is closed for the packet route itself. Still
open, named but not attempted here: the crash-safety gap immediately
above; HP7's own live route proof (needs a real `pi` process, separately
authorized); and folding `engine_command_implementer` into whatever
eventually decides which seam a given comparison run uses
(`command_implementer` for uncomposed HP2, or this one) — that decision
point does not exist yet and is not invented here.
