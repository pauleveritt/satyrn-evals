> **Archived pre-reset record (2026-09-07).**
>
> Original claims, decisions, and instructions may be superseded. This file is evidence, not current guidance.
> For current guidance, read root AGENTS.md, BRIEF.md, and ROADMAP.md. Retrieve one named record when it bears on a concrete question; do not preload this archive.

# V8 Plan 3 of 5 — Environment materialization and `resolved_versions` (slice 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When grading a dependency-bearing task (its `base/` carries `pyproject.toml` + `uv.lock`), materialize that locked project environment and run the oracle inside it, attesting the executed distributions as `resolved_versions` on the receipt — while every pre-V8 (stdlib/vendored) task grades exactly as today.

**Architecture:** Plan 3 of 5 for V8 (`docs/superpowers/specs/2026-09-04-v8-agentclinic-evals-design.md` §3, §9). A small new pure module `taskenv.py` holds the detection predicate and the `uv pip freeze` parser (default-tier testable). `grade.py`'s `_run_oracle` materializes the env into a relocated project env under its existing scratch `TemporaryDirectory` (`UV_PROJECT_ENVIRONMENT`, `uv sync --locked`, cwd = the graded tree) and returns the frozen distributions; `grade()` writes them on the receipt. Oracle runs get `PYTHONPATH` to the evals source (the hook plugin) and `PYTHONDONTWRITEBYTECODE=1`.

**Tech Stack:** Python 3.14, `uv`, `pytest`, dataclasses.

**Spec:** `docs/superpowers/specs/2026-09-04-v8-agentclinic-evals-design.md` (§3 environment, §9 receipt field).

## Global Constraints

- Python `>=3.14`; real return annotations; `match`/`case`/walrus house style.
- Default tier: no model/network/subprocess (planted spawn tripwire) — env materialization tests live in `tests/integration/`, marked `@pytest.mark.integration`.
- A refusal test has a sibling success test, always.
- Verdicts come from hook files, never stdout or exit codes; detection never changes a verdict.
- 100% coverage gate: `uv run pytest -m '' --cov=src/satyrn_evals --cov-branch --cov-fail-under=100`.
- `ruff check .` clean; `just lint-docs` green.
- Receipt `resolved_versions` is omitted (None-popped) for ambient/stdlib grading; attested from the env that actually ran (a freeze, never a lock parse).

### Task 1: `taskenv.py` — pure detection and freeze parsing

**Files:**
- Create: `src/satyrn_evals/taskenv.py`
- Test: `tests/test_taskenv.py`

**Interfaces:**
- Produces: `has_locked_project(base: Path) -> bool` and `parse_freeze(text: str) -> dict[str, str]`, consumed by Task 2.

- [ ] **Step 1: Write the failing tests**

```python
from pathlib import Path

from satyrn_evals.taskenv import has_locked_project, parse_freeze


def test_stdlib_base_is_not_dependency_bearing(tmp_path: Path) -> None:
    base = tmp_path / "base"
    base.mkdir()
    (base / "setup.py").write_text("")          # vendored/legacy marker, not a project
    assert has_locked_project(base) is False


def test_project_with_lock_is_dependency_bearing(tmp_path: Path) -> None:
    base = tmp_path / "base"
    base.mkdir()
    (base / "pyproject.toml").write_text("[project]\nname='x'\nversion='0'\n")
    (base / "uv.lock").write_text("version = 1\n")
    assert has_locked_project(base) is True


def test_pyproject_without_lock_is_not_dependency_bearing(tmp_path: Path) -> None:
    base = tmp_path / "base"
    base.mkdir()
    (base / "pyproject.toml").write_text("[project]\n")
    assert has_locked_project(base) is False


def test_parse_freeze_maps_name_to_exact_version() -> None:
    text = "fastapi==0.115.10\nstarlette==0.41.3\n"
    assert parse_freeze(text) == {"fastapi": "0.115.10", "starlette": "0.41.3"}


def test_parse_freeze_ignores_editable_and_comment_lines() -> None:
    text = "-e /tmp/project\n# comment\npytest==8.3.4\n"
    assert parse_freeze(text) == {"pytest": "8.3.4"}
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_taskenv.py -q`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `taskenv.py`**

```python
"""Task-owned project environments: detection and freeze attestation (pure)."""

from pathlib import Path


def has_locked_project(base: Path) -> bool:
    """True when ``base`` is a uv project: pyproject.toml AND uv.lock present.

    A pyproject without a lock is not a locked environment; the whole point
    of V8's environment story is that the lock, not resolution, decides.
    """
    return (base / "pyproject.toml").is_file() and (base / "uv.lock").is_file()


def parse_freeze(text: str) -> dict[str, str]:
    """Map ``uv pip freeze`` output to {normalized name: exact version}.

    Accepts only ``name==version`` lines; editable (``-e ...``) and comment
    lines are skipped. A freeze is an attestation of what is installed, so
    unparseable lines are ignored rather than fatal.
    """
    frozen: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "-e ")) or "==" not in stripped:
            continue
        name, _, version = stripped.partition("==")
        frozen[name.strip()] = version.strip()
    return frozen
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_taskenv.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/satyrn_evals/taskenv.py tests/test_taskenv.py && git commit -m "feat: taskenv detection and freeze parsing (pure)"
```

### Task 2: Receipt field `resolved_versions` with omission semantics

**Files:**
- Modify: `src/satyrn_evals/receipt.py:11-23`
- Test: `tests/test_receipt.py`

**Interfaces:**
- Consumes: `parse_freeze` (Task 1).
- Produces: `Receipt(resolved_versions=...)` — `None` means ambient; serialization omits the key (contamination precedent). Consumed by Task 3 (`grade.py`) and by P4's gate.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_receipt.py`, mirroring its `write_receipt` roundtrip idiom)

```python
def test_receipt_omits_resolved_versions_when_none(tmp_path) -> None:
    receipt = Receipt("t", "d", Verdict.PASS, "ok", None)  # resolved_versions defaults None
    path = tmp_path / "receipt.json"
    write_receipt(path, receipt)
    assert "resolved_versions" not in json.loads(path.read_text())


def test_receipt_serializes_resolved_versions_when_present(tmp_path) -> None:
    receipt = Receipt("t", "d", Verdict.PASS, "ok", None,
                      resolved_versions={"fastapi": "0.115.10"})
    path = tmp_path / "receipt.json"
    write_receipt(path, receipt)
    data = json.loads(path.read_text())
    assert data["resolved_versions"] == {"fastapi": "0.115.10"}
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_receipt.py -q -k resolved`
Expected: FAIL — `TypeError` (unexpected keyword) and missing-key.

- [ ] **Step 3: Implement**

`receipt.py` — add the field and the None-pop (exactly the `contamination` pattern):

```python
@dataclass(frozen=True, slots=True)
class Receipt:
    task: str
    patch_digest: str
    verdict: Verdict
    reason: str
    evidence: HookResultData | None
    contamination: dict | None = None
    resolved_versions: dict[str, str] | None = None
```

`write_receipt` — add before `contamination` handling or after, symmetric:

```python
def write_receipt(path: Path, receipt: Receipt) -> None:
    data = asdict(receipt)
    if receipt.contamination is None:
        del data["contamination"]
    if receipt.resolved_versions is None:
        del data["resolved_versions"]
    path.write_text(json.dumps(data, indent=2) + "\n")
```

- [ ] **Step 4: Run to verify pass, plus the existing receipt tests**

Run: `uv run pytest tests/test_receipt.py -q`
Expected: PASS (existing tests unchanged — the new key never appears for old shapes).

- [ ] **Step 5: Commit**

```bash
git add src/satyrn_evals/receipt.py tests/test_receipt.py && git commit -m "feat: receipt resolved_versions field, omitted for ambient grading"
```

### Task 3: Materialize the locked env in `grade` and attest it

**Files:**
- Modify: `src/satyrn_evals/grade.py` (`_run_oracle` at `:128-171`; `grade()` receipt construction at `:112-125`)
- Test: `tests/integration/test_grade_materialized_env.py` (integration tier)

**Interfaces:**
- Consumes: `has_locked_project`, `parse_freeze` (Task 1); `Receipt(resolved_versions=...)` (Task 2).
- Produces: `_run_oracle(...) -> tuple[HookResult, dict[str, str] | None]`; `grade()` returns a `Receipt` carrying `resolved_versions` for dependency-bearing tasks and `None` (omitted) otherwise. P4's gate and the close-out record read `receipt["resolved_versions"]`.

- [ ] **Step 1: Write the failing integration test** (`tests/integration/test_grade_materialized_env.py`)

```python
import json
import subprocess
from pathlib import Path

import pytest

from satyrn_evals.manifest import resolve_task

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def bundled_task_dir() -> Path:
    return resolve_task("agentclinic-repair-plausible-wrong-fix")


def _grade(task_dir: Path, patch: str, tmp_path: Path) -> dict:
    patch_path = tmp_path / "p.patch"
    patch_path.write_text(patch)
    receipt_path = tmp_path / "receipt.json"
    subprocess.run(  # real CLI keeps env semantics identical to attempt
        ["satyrn-evals", "grade", task_dir.name, str(patch_path),
         "--receipt", str(receipt_path), "--tasks-root", str(task_dir.parent)],
        check=True, capture_output=True)
    return json.loads(receipt_path.read_text())


def test_materialized_grade_attests_resolved_versions(
    bundled_task_dir: Path, tmp_path: Path
) -> None:
    known_good = (bundled_task_dir / "fixtures" / "known-good.patch").read_text()
    receipt = _grade(bundled_task_dir, known_good, tmp_path)
    assert receipt["verdict"] == "pass"
    versions = receipt.get("resolved_versions")
    assert versions is not None, "dependency-bearing grade must attest versions"
    assert versions.get("fastapi") == "0.115.10"
    assert "pytest" in versions  # the locked dev group was materialized
```

(Do not call `grade()` directly from a default-tier test — the planted spawn tripwire forbids it; this file is in `tests/integration/`.)

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/integration/test_grade_materialized_env.py -q`
Expected: FAIL — receipt has no `resolved_versions` key and/or the oracle env lacks deps (collection error under the bare ambient interpreter is acceptable as the pre-change failure signal).

- [ ] **Step 3: Implement in `grade.py`**

(a) `_run_oracle` — after `materialize_overlay` and before the pytest subprocess, materialize when the base is dependency-bearing; thread the freeze back through the return:

```python
from satyrn_evals.taskenv import has_locked_project, parse_freeze

def _materialize_project_env(work: Path, tmp: Path, base: Path) -> Path | None:
    """Relocated project env at tmp/env, uv sync --locked in the graded tree."""
    if not has_locked_project(base):
        return None
    env_root = tmp / "project-env"
    env = dict(os.environ)
    env["UV_PROJECT_ENVIRONMENT"] = os.fspath(env_root)
    try:
        subprocess.run(
            ["uv", "sync", "--locked"],
            cwd=work, env=env, capture_output=True, check=True,
        )
    except (OSError, subprocess.CalledProcessError) as e:
        raise OracleError(f"cannot materialize task environment: {e}") from e
    return env_root
```

(b) `_run_oracle` return change — the interior (tempdir, `copytree(base, work)`, git init/apply, overlay materialize, hook-path reservation) is unchanged; the signature, the env seeding, and the tail change:

```python
def _run_oracle(
    manifest: TaskManifest,
    task_dir: Path,
    patch_text: str,
    *,
    overlay: OverlaySpec | None = None,
    selectors: tuple[str, ...] = (),
) -> tuple[HookResult, dict[str, str] | None]:
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "work"
        shutil.copytree(task_dir / "base", work, symlinks=True)
        # ... unchanged: git init/apply of patch_text, overlay materialize,
        # hook-path reservation — then the env seeding replaces the old PATH block:
        env_root = _materialize_project_env(work, Path(tmp), task_dir / "base")
        env = dict(os.environ)
        env[oracle_hook.RESULT_ENV] = hook_path
        if env_root is not None:
            env["PATH"] = os.fspath(env_root / "bin") + os.pathsep + env.get("PATH", "")
            env["PYTHONPATH"] = os.fspath(Path(satyrn_evals.__file__).resolve().parent.parent)
            env["PYTHONDONTWRITEBYTECODE"] = "1"
        else:
            env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
        # ... unchanged: oracle subprocess([*manifest.oracle, *selectors], env=env)
        frozen: dict[str, str] | None = None
        if env_root is not None:
            try:
                freeze = subprocess.run(
                    ["uv", "pip", "freeze", "--python", os.fspath(env_root / "bin" / "python")],
                    capture_output=True, check=True, text=True,
                )
            except (OSError, subprocess.CalledProcessError) as e:
                raise OracleError(f"cannot attest task environment: {e}") from e
            frozen = parse_freeze(freeze.stdout)
        try:
            return load_hook_result(Path(hook_path), run_started), frozen
        finally:
            Path(hook_path).unlink(missing_ok=True)
```

(Add `import satyrn_evals` to `grade.py`'s imports; the `PYTHONPATH` above is `Path(satyrn_evals.__file__).resolve().parent.parent` — the dir whose child is the package.)

(c) `grade()` — unpack the tuple and pass the attestation into the receipt (the receipt construction at `grade.py:112-125` gains the keyword):

```python
        hook, resolved_versions = _run_oracle(
            manifest, task_dir, patch_text, overlay=overlay, selectors=selectors
        )
        verdict = compute_verdict(
            hook,
            expected if expected is not None else manifest.expected_test_ids,
        )
        # ... unchanged: evidence/reason/contamination construction ...
        receipt = Receipt(
            task=manifest.name,
            patch_digest=patch_digest(patch_bytes),
            verdict=verdict,
            reason=reason,
            evidence=evidence,
            contamination=contamination,
            resolved_versions=resolved_versions,
        )
        write_receipt(receipt_path, receipt)
        return receipt
```

- [ ] **Step 4: Run to verify pass (network: first uv sync of the locked project)**

Run: `uv run pytest tests/integration/test_grade_materialized_env.py -q`
Expected: PASS — verdict pass, 13/13 via the materialized env, `resolved_versions["fastapi"] == "0.115.10"`.

- [ ] **Step 5: Pre-V8 byte-compatibility — existing integration grades unchanged**

Run: `uv run pytest tests/integration/test_grade.py tests/integration/test_grade_overlay.py tests/integration/test_bundled.py -q`
Expected: PASS — stdlib tasks still grade under the ambient interpreter and their receipts carry no `resolved_versions` key.

- [ ] **Step 6: A refusal-grade sibling (materialization failure surfaces, not a void)**

The test calls `grade()` in-process (this file is integration tier) with a
`PATH` that cannot resolve `uv`, so ONLY the child env lacks uv — replacing
`PATH` around a CLI subprocess would prevent launching the CLI itself:

```python
def test_missing_uv_yields_unavailable_not_ambient_pass(
    bundled_task_dir: Path, tmp_path: Path, monkeypatch
) -> None:
    from satyrn_evals.grade import grade
    patch_path = tmp_path / "p.patch"
    patch_path.write_text(
        (bundled_task_dir / "fixtures" / "known-good.patch").read_text())
    nobin = tmp_path / "nobin"
    nobin.mkdir()
    monkeypatch.setenv("PATH", str(nobin))
    receipt_path = tmp_path / "receipt.json"
    receipt = grade(bundled_task_dir, patch_path, receipt_path)
    assert receipt.verdict.value == "unavailable"
    assert "cannot materialize task environment" in receipt.reason
```

Run; PASS.

- [ ] **Step 7: Commit**

```bash
git add src/satyrn_evals/grade.py tests/integration/test_grade_materialized_env.py && git commit -m "feat: grade materializes locked task envs and attests resolved_versions"
```

### Task 4: Slice-2 self-review

- [ ] **Step 1: Coverage gate**

Run: `uv run pytest -m '' --cov=src/satyrn_evals --cov-branch --cov-report=term-missing --cov-fail-under=100`
Expected: 100% (the `env_root is not None` branches in `_run_oracle` are integration-covered; any uncovered branch must gain a default-tier unit or an integration assertion — the gate is the invariant).

- [ ] **Step 2: Ruff and doc caps**

Run: `ruff check . && just lint-docs`
Expected: clean.

- [ ] **Step 3: Spec cross-check.** Spec §3 (two production changes — this plan is change 1), §9 (receipt field), Correction-4 closure. No placeholders. Hand off to P3.