# V9 P5b — Grade-path fixes: T7 hook shim, T8 cleaned git environment

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The oracle hook resolves through a shim directory that carries
only the running evals package, so the locked task environment supplies
every dependency and `resolved_versions` attests what the oracle actually
used (T7). Grading's `git init`/`git apply` run in the cleaned environment
(T8).

**Architecture:** `grade.py` creates `tmp/hookpath/` with one symlink to
the running package and sets `PYTHONPATH` to that dir. Grading's git runs
under `workspace.clean_git_environment` (a new public wrapper: probes Git's
routing vars exactly as the workspace runner does, strips them). Pure
helpers `_hook_import_path`/`_apply_patch` carry the default-tier tests;
the subprocess proofs are integration.

**Tech Stack:** Python ≥3.14, stdlib only.

**Spec:** `docs/superpowers/specs/2026-09-04-v9-loop-integrity-and-rescoring-design.md`
§4 T7/T8.

## Global Constraints

- **No commits.** Commits are maintainer-controlled (`docs/sdd.md`).
- Default tier must not spawn (tripwire); integration tier proves real
  subprocess behavior (T7 two-env proof, T8 hostile-ambient proof).
- Refusal tests get success siblings.
- House style: real annotations; `type` aliases; `match`/`case`; `:=`.
- `docs/sdd.md` cap: this plan stays ≤400 lines.

---

### Task 1: T7 — the hook shim

**Files:**
- Modify: `src/satyrn_evals/grade.py`
- Test: `tests/test_grade_shim.py` (new, default tier),
  `tests/integration/test_grade_shim.py` (new, integration)

**Interfaces:**
- Produces: `_hook_import_path(work: Path, package_dir: Path) -> Path` — a
  sibling dir `work.parent / "hookpath"` containing exactly one symlink
  `satyrn_evals -> package_dir`; returns it. `grade` sets the oracle's
  `PYTHONPATH` to that dir for dependency-bearing tasks.

- [ ] **Step 1: Write the failing default-tier tests**

```python
"""T7 hook shim: PYTHONPATH carries only the running evals package."""

from pathlib import Path

import pytest

from satyrn_evals import grade as grade_module

def test_hook_import_path_holds_one_symlink(tmp_path: Path) -> None:
    package = tmp_path / "pkg" / "satyrn_evals"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    shim = grade_module._hook_import_path(tmp_path / "work", package)
    assert shim.name == "hookpath"
    assert (shim / "satyrn_evals").is_symlink()
    assert (shim / "satyrn_evals").resolve() == package.resolve()
    # exactly one entry -- nothing else shadows the locked env
    assert list(shim.iterdir()) == [shim / "satyrn_evals"]

def test_hook_import_path_refuses_a_non_package_target(tmp_path: Path) -> None:
    missing = tmp_path / "nope"
    with pytest.raises(ValueError, match="package"):
        grade_module._hook_import_path(tmp_path / "work", missing)
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest -q tests/test_grade_shim.py`
Expected: FAIL — `_hook_import_path` does not exist.

- [ ] **Step 3: Implement the helper and wire it**

In `src/satyrn_evals/grade.py`:

```python
def _hook_import_path(work: Path, package_dir: Path) -> Path:
    """``<work.parent>/hookpath`` holding one symlink to the evals package.

    Nothing else is on PYTHONPATH, so a dependency-bearing oracle resolves
    every task dependency from its own locked environment.
    """
    package_dir = package_dir.resolve()
    if not (package_dir / "__init__.py").is_file():
        raise ValueError(f"not the satyrn_evals package dir: {package_dir}")
    shim = (work.parent / "hookpath").resolve()
    shim.mkdir(exist_ok=True)
    link = shim / "satyrn_evals"
    try:
        link.symlink_to(package_dir, target_is_directory=True)
    except FileExistsError:
        pass
    return shim
```

In `_run_oracle`'s dependency-bearing branch, replace the `PYTHONPATH`
assignment (`grade.py:211-213`):

```python
        if env_root is not None:
            env["PATH"] = os.fspath(env_root / "bin") + os.pathsep + env.get("PATH", "")
            env["PYTHONPATH"] = os.fspath(
                _hook_import_path(
                    work,
                    Path(satyrn_evals.__file__).resolve().parent,
                )
            )
            env["PYTHONDONTWRITEBYTECODE"] = "1"
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest -q tests/test_grade_shim.py`
Expected: PASS.

- [ ] **Step 5: The integration proof (two environments, one interpreter)**

The real T7 hazard: a conflicting dependency lives **beside the running
evals package** — what the old `PYTHONPATH = parent.parent` exposed (the
installer's `site-packages`, which may also carry `fastapi`). The fix puts
only `satyrn_evals` on `PYTHONPATH`, so the *oracle venv's own*
site-packages must supply the dependency. Model it with `python -S` (no
site import): `sys.path` = script-dir + `PYTHONPATH` + stdlib, so
`PYTHONPATH` order decides the shadow:

```python
"""T7: the shim prevents the evals-neighbor dependency shadow."""

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

PROBE = textwrap.dedent(
    """
    import sentinel_dep
    import satyrn_evals
    print(sentinel_dep.__file__)
    print(satyrn_evals.__file__)
    """
)


def _make_env_dirs(tmp_path: Path):
    """evals site-packages (with a conflicting dep) vs the locked env."""
    shadow_site = tmp_path / "shadow_site"  # the OLD PYTHONPATH target
    package = shadow_site / "satyrn_evals"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    dep = shadow_site / "sentinel_dep"
    dep.mkdir()
    (dep / "__init__.py").write_text("MARK = 'shadow'")
    locked_site = tmp_path / "locked_site"  # the oracle venv's site-packages
    dep = locked_site / "sentinel_dep"
    dep.mkdir(parents=True)
    (dep / "__init__.py").write_text("MARK = 'locked'")
    return shadow_site, package, locked_site


def test_shim_keeps_the_locked_env_in_charge(tmp_path: Path) -> None:
    shadow_site, package, locked_site = _make_env_dirs(tmp_path)
    script = tmp_path / "probe.py"
    script.write_text(PROBE)

    # OLD behavior: PYTHONPATH = evals' site-packages, shadow first
    old_env = dict(os.environ)
    old_env["PYTHONPATH"] = os.fspath(shadow_site) + os.pathsep + os.fspath(locked_site)
    old_out = subprocess.run(
        [sys.executable, "-S", str(script)], env=old_env,
        capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    assert "shadow" in old_out[0]  # the hazard is real: shadow wins

    # NEW behavior: PYTHONPATH = shim (only satyrn_evals), locked env second
    shim = tmp_path / "hookpath"
    shim.mkdir()
    (shim / "satyrn_evals").symlink_to(package, target_is_directory=True)
    new_env = dict(os.environ)
    new_env["PYTHONPATH"] = os.fspath(shim) + os.pathsep + os.fspath(locked_site)
    new_out = subprocess.run(
        [sys.executable, "-S", str(script)], env=new_env,
        capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    assert os.fspath(locked_site) in new_out[0]  # dep from the locked env
    assert os.fspath(package) in new_out[1]       # evals via the shim symlink
```

(The `-S` interpreter keeps the probe hermetic — the dev venv's own
site-packages cannot leak a `sentinel_dep`. The real-wheel demonstration is
the recorded verification in plan P6 Task 4.)

- [ ] **Step 6: Run to verify it passes**

Run: `uv run pytest -q tests/integration/test_grade_shim.py -m integration`
Expected: PASS.

### Task 2: T8 — grading's git runs get the cleaned environment

**Files:**
- Modify: `src/satyrn_evals/workspace.py`, `src/satyrn_evals/grade.py`
- Test: `tests/test_grade_git_env.py` (new, default tier),
  `tests/integration/test_grade_git_env.py` (new, integration)

**Interfaces:**
- Consumes: `workspace.clean_git_environment` (new public wrapper),
  `workspace.GIT_SAFETY_CONFIG` (public alias).
- Produces: grade's git init/apply run under the cleaned environment and
  the safety-config argv prefix; `_apply_patch(work, patch_text, git_env)`
  isolates the git pair for default-tier testing.

- [ ] **Step 1: Export the workspace discipline**

In `src/satyrn_evals/workspace.py`:

```python
_GIT_SAFETY_CONFIG = (...)
GIT_SAFETY_CONFIG = _GIT_SAFETY_CONFIG  # V9: grade.py reuses the workspace git discipline


def clean_git_environment(environment: Mapping[str, str]) -> dict[str, str]:
    """Copy an environment minus Git's repository-routing state (T8).

    Probes the routing variables exactly as the workspace runner does
    (`git rev-parse --local-env-vars` under a GIT_-stripped environment)
    and removes them, pinning GIT_TERMINAL_PROMPT/GIT_NO_REPLACE_OBJECTS/
    GIT_GRAFT_FILE. Ambient GIT_DIR/GIT_INDEX_FILE/GIT_WORK_TREE must not
    redirect where evals' own git commands run.
    """
    routing_names = _local_env_vars(environment)
    return clean_environment(environment, routing_names)
```

- [ ] **Step 2: Write the failing default-tier test**

```python
"""T8: grading's git subprocesses run in the cleaned environment."""

import os

import pytest

from satyrn_evals import grade as grade_module
from satyrn_evals.workspace import GIT_SAFETY_CONFIG


def test_apply_patch_passes_env_through_and_leads_with_safety_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []

    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs.get("env", {})))
        return type("R", (), {"returncode": 0, "stderr": b""})()

    monkeypatch.setattr(grade_module.subprocess, "run", fake_run)
    git_env = {"MARKER": "1"}  # whatever clean_git_environment produced
    grade_module._apply_patch(
        tmp_path / "work", "diff --git a/x b/x\n", git_env
    )
    assert len(calls) == 2  # init then apply
    for argv, env in calls:
        assert argv[: len(GIT_SAFETY_CONFIG)] == list(GIT_SAFETY_CONFIG)
        assert env == git_env  # the cleaned env is passed verbatim


def test_apply_patch_raises_apply_error_on_git_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from satyrn_evals.errors import ApplyError

    def failing(argv, **kwargs):
        return type("R", (), {"returncode": 1, "stderr": b"nope"})()

    monkeypatch.setattr(grade_module.subprocess, "run", failing)
    with pytest.raises(ApplyError, match="patch did not apply"):
        grade_module._apply_patch(tmp_path / "work", "x", {})
```

(The *wiring* — that `_run_oracle` obtains its git env from
`clean_git_environment` and not from raw `os.environ` — is proven by the
integration test in Step 6; `clean_git_environment` itself is the
workspace runner's already-tested probe plus `clean_environment`.)

- [ ] **Step 3: Run to verify they fail**

Expected: FAIL — `_apply_patch` does not exist.

- [ ] **Step 4: Implement**

In `src/satyrn_evals/grade.py`:

1. Import the discipline:

```python
from satyrn_evals.workspace import GIT_SAFETY_CONFIG, clean_git_environment
```

2. Factor the git init/apply pair (today `grade.py:185-190`) into a helper:

```python
def _apply_patch(work: Path, patch_text: str, git_env: dict[str, str]) -> None:
    """git init + apply under grading's cleaned environment (T8)."""
    try:
        subprocess.run(
            ["git", *GIT_SAFETY_CONFIG, "init", "-q"],
            cwd=work, env=git_env, check=True, capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as e:
        raise ApplyError(f"cannot run git: {e}") from e
    applied = subprocess.run(
        ["git", *GIT_SAFETY_CONFIG, "apply", "-"],
        input=os.fsencode(patch_text),
        cwd=work,
        env=git_env,
        capture_output=True,
    )
    if applied.returncode != 0:
        raise ApplyError(
            "patch did not apply: " + os.fsdecode(applied.stderr).strip()
        )
```

3. In `_run_oracle`, replace the two inline git calls with:

```python
        git_env = clean_git_environment(dict(os.environ))
        _apply_patch(work, patch_text, git_env)
```

   (Keep `_apply_patch`'s failure messages identical to today's so tests
   matching "patch did not apply" stay green. `clean_git_environment` runs
   one `git rev-parse --local-env-vars` probe — the workspace runner's own
   discipline.)

- [ ] **Step 5: Run the default tests to verify they pass**

Expected: PASS.

- [ ] **Step 6: The integration proof (hostile ambient git)**

```python
"""T8: hostile ambient git cannot redirect grading."""

import os
import subprocess
from pathlib import Path

import pytest

from satyrn_evals.grade import grade
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT
from satyrn_evals.verdict import Verdict

pytestmark = pytest.mark.integration

TASK = DEFAULT_TASKS_ROOT / "format_number"
PATCH = TASK / "fixtures" / "known-good.patch"


def test_grade_ignores_ambient_git_redirect(tmp_path: Path) -> None:
    elsewhere = tmp_path / "elsewhere"
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("GIT_DIR", os.fspath(tmp_path / "trap" / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", os.fspath(elsewhere))
    monkeypatch.setenv("GIT_INDEX_FILE", os.fspath(tmp_path / "trap-index"))
    try:
        receipt = grade(TASK, PATCH, tmp_path / "receipt.json")
    finally:
        monkeypatch.undo()
    assert receipt.verdict is Verdict.PASS  # graded the real tree
    # the redirected work tree was never materialized
    assert not elsewhere.exists()
    assert not (tmp_path / "trap-index").exists()
```

(If `grade` were still running under the ambient `GIT_WORK_TREE`, its
`git init`/`git apply` would have written into `elsewhere` — the success
sibling of Step 5's env-pass-through test.)

- [ ] **Step 7: Run to verify it passes**

Expected: PASS.

### Task 3: whole default tier + gate

Run: `uv run pytest -q` and `uv run ruff check src/satyrn_evals tests`
Expected: both PASS.