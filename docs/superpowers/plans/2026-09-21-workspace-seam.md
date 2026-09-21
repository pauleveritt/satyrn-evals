# Workspace and Seam Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fetch `satyrn-engine` at the commit the Engine arm pins into a sibling checkout, and sync three of its docs into a committed `_engine/` copy with a digest manifest, so one site presents both repositories offline.

**Architecture:** A new `tools/engine_sync.py` script reads the pin from `arms/engine-ornith15-9b.json`, can clone the engine at that commit, and copies the engine's `README.md`, `docs/usage.md`, and `docs/glossary.md` into `_engine/` (outside the site's `docs_dir`) with a `manifest.json` of the commit and each file's sha256. The site includes the synced bytes by reference; default-tier tests prove the copy still matches the manifest and the arm's pin. No harness code changes.

**Tech Stack:** Python 3.14 via `uv`, `git` (integration tier only), Zensical 0.0.63 (existing `docs` group), pytest with the repo's default/integration split.

**Spec:** `docs/superpowers/specs/2026-09-21-workspace-seam-design.md`

## Global Constraints

- Engine pin: `78ab87dbab3381dd585986c43fd49e6e4974f6b6`, read from `arms/engine-ornith15-9b.json` (`pins.engine_commit`). Never hard-code it in new code.
- Engine repository URL: `https://github.com/pauleveritt/satyrn-engine.git`.
- Synced destination: root `_engine/` (never under `site/`, because `exclude_docs` did not keep a `docs_dir` file out of the page tree).
- Synced files: `README.md` from `README.md`, `usage.md` from `docs/usage.md`, `glossary.md` from `docs/glossary.md`. The manifest is `_engine/manifest.json`.
- `satyrn-engine` is read-only: never write in it.
- Default test tier uses no model, network, or subprocess (`tests/conftest.py` tripwire). `git` calls live only in `tests/integration/`, marked `pytest.mark.integration`.
- Never call a model. Never run `satyrn-evals launch`. Never write under `records/`, `arms/`, `evidence/`, `src/satyrn_evals/tasks/`, or `/Users/Shared/satyrn-cells`.
- Scratch only in the session scratchpad or `$HOME/satyrn-docs-scratch/`; never `/tmp`.
- Every new file gets a `PROVENANCE.md` row: `uv run python tools/provenance.py new PATH...`, then `check`.
- Commits use explicit paths (never `git add -A`) and end with `Co-Authored-By: deepseek-v4-flash <noreply@deepseek.com>`.
- `just gates` must exit 0 after every task.
- Spec deviation: spec §4 says the fetch is shallow; this plan clones fully then checks out the commit, because fetching an arbitrary sha shallowly depends on server settings. The engine repo is small; revisit only if clone time matters.
- Zensical is pinned `0.0.63` in the `docs` dependency group; build with `just docs` (strict).
- Included engine text keeps its repo-relative links, which may not resolve on the site; rewriting them is out of scope for this plan.

## File Structure

- `tools/provenance.py` (modify) — add `record_source` and a `record --source` CLI form; add `_engine` to `TRACKED_DIRS`.
- `tests/test_provenance.py` (modify) — tests for `record_source` and the tracked `_engine` dir.
- `tools/engine_sync.py` (create) — pin reading, manifest build/check, `fetch_engine`, `sync_engine`, `main`.
- `tests/test_engine_sync.py` (create) — pure helper tests, fixture trees only.
- `tests/integration/test_engine_sync.py` (create) — `git` tests, marked integration.
- `tests/test_engine_docs.py` (create) — the committed `_engine/` against the arm pin.
- `tests/test_engine_pages.py` (create) — the site's engine includes and banners.
- `Justfile` (modify) — `fetch-engine`, `sync-engine` recipes.
- `_engine/README.md`, `_engine/usage.md`, `_engine/glossary.md`, `_engine/manifest.json` (create via sync) — the committed copy.
- `site/engine.md`, `site/engine-usage.md`, `site/engine-glossary.md` (create) — the engine section.
- `zensical.toml` (modify) — nav entries for the three pages.
- `PROVENANCE.md` (modify) — rows for every new file.

---

### Task 1: Provenance can record an engine source

**Files:**
- Modify: `tools/provenance.py`
- Test: `tests/test_provenance.py`

**Interfaces:**
- Consumes: the existing `_rows_file(root) -> Path` and `HEADER`.
- Produces: `record_source(root: Path, source: str, paths: list[str]) -> None`, which writes one `| path | source |` row per path and replaces any existing rows for those paths. `TRACKED_DIRS` gains `"site"` already and now `"_engine"`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_provenance.py` (and add `record_source` to the existing import line at the top):

```python
def test_recording_a_source_writes_the_source_verbatim(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    (root / "_engine").mkdir()
    (root / "_engine" / "usage.md").write_text("engine bytes\n")
    record_source(root, "satyrn-engine @ " + "a" * 40, ["_engine/usage.md"])
    assert f"| _engine/usage.md | satyrn-engine @ {'a' * 40} |" in (root / "PROVENANCE.md").read_text()


def test_recording_a_source_twice_leaves_one_row_per_path(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    (root / "_engine").mkdir()
    (root / "_engine" / "usage.md").write_text("engine bytes\n")
    record_source(root, "satyrn-engine @ " + "a" * 40, ["_engine/usage.md"])
    record_source(root, "satyrn-engine @ " + "b" * 40, ["_engine/usage.md"])
    text = (root / "PROVENANCE.md").read_text()
    assert text.count("| _engine/usage.md |") == 1
    assert f"satyrn-engine @ {'b' * 40}" in text


def test_check_names_an_engine_file_without_a_row(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    record_imported(root, SHA, ["src/pkg/a.py"])
    record_new(root, ["tools/b.py"])
    (root / "_engine").mkdir()
    (root / "_engine" / "usage.md").write_text("engine bytes\n")
    assert check(root) == ["_engine/usage.md"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest -q tests/test_provenance.py`
Expected: FAIL with `ImportError: cannot import name 'record_source'` (or `AttributeError`), and the tracked-`_engine` test fails.

- [ ] **Step 3: Implement `record_source` and the tracked dir**

In `tools/provenance.py`, change `TRACKED_DIRS` to include `"_engine"`:

```python
TRACKED_DIRS = ("src", "tests", "scripts", "tools", "arms", "docs", "site", "_engine", "packages", ".github")
```

Add `record_source` after `record_new`:

```python
def record_source(root: Path, source: str, paths: list[str]) -> None:
    """One row per path with an arbitrary source; replaces existing rows for those paths.

    Unlike ``record_imported``/``record_new``, this is idempotent: the sync
    runs on every re-pin, and a doubled row would be a lie about a single file.
    """
    for rel in paths:
        if not (root / rel).exists():
            raise FileNotFoundError(rel)
    wanted = set(paths)
    path = _rows_file(root)
    kept = [
        line
        for line in path.read_text().splitlines()
        if not (line.startswith("| ") and line.split("|")[1].strip() in wanted)
    ]
    with path.open("w") as handle:
        handle.write("\n".join(kept) + "\n")
        for rel in paths:
            handle.write(f"| {rel} | {source} |\n")
```

Add a case to `main` before `case _:`:

```python
        case ["record", "--source", source, *paths] if paths:
            record_source(root, source, paths)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest -q tests/test_provenance.py`
Expected: PASS.

- [ ] **Step 5: Run the gates and commit**

```bash
just gates
uv run python tools/provenance.py check
git add tools/provenance.py tests/test_provenance.py
git commit -m "Provenance: record an engine source, idempotently

Co-Authored-By: deepseek-v4-flash <noreply@deepseek.com>"
```

Expected: `just gates` exits 0 (no new files, so no provenance row needed).

---

### Task 2: Manifest helpers

**Files:**
- Create: `tools/engine_sync.py`
- Test: `tests/test_engine_sync.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: `sha256(path) -> str`; `load_arm(path) -> Mapping`; `engine_pin(arm) -> str`; `build_manifest(engine_repo, commit, *, repository=DEFAULT_ENGINE_URL, docs=ENGINE_DOCS) -> dict`; `check_manifest(engine_dir, expected_commit, docs=ENGINE_DOCS) -> list[str]`; constants `DEFAULT_ARM`, `DEFAULT_OUTPUT`, `DEFAULT_ENGINE_URL`, `MANIFEST_NAME`, `ENGINE_DOCS`; exception `EngineSyncError`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_engine_sync.py`:

```python
import json
from pathlib import Path

import pytest

from tools.engine_sync import (
    ENGINE_DOCS,
    EngineSyncError,
    build_manifest,
    check_manifest,
    engine_pin,
    load_arm,
    sha256,
)

ROOT = Path(__file__).resolve().parents[1]
ARM = ROOT / "arms" / "engine-ornith15-9b.json"


def _fake_engine(root: Path) -> Path:
    (root / "docs").mkdir(parents=True)
    (root / "README.md").write_text("readme\n")
    (root / "docs" / "usage.md").write_text("usage\n")
    (root / "docs" / "glossary.md").write_text("glossary\n")
    return root


def test_engine_pin_reads_the_arms_engine_commit() -> None:
    assert engine_pin(load_arm(ARM)) == "78ab87dbab3381dd585986c43fd49e6e4974f6b6"


def test_engine_pin_refuses_an_arm_without_a_pin() -> None:
    with pytest.raises(EngineSyncError, match="engine_commit"):
        engine_pin({"pins": {}})


def test_build_manifest_hashes_each_document(tmp_path: Path) -> None:
    manifest = build_manifest(_fake_engine(tmp_path / "engine"), "a" * 40)
    assert set(manifest["files"]) == {"README.md", "usage.md", "glossary.md"}
    assert manifest["files"]["usage.md"]["source"] == "docs/usage.md"
    assert manifest["files"]["usage.md"]["sha256"] == sha256(tmp_path / "engine" / "docs" / "usage.md")
    assert manifest["engine_commit"] == "a" * 40


def test_build_manifest_names_a_missing_document(tmp_path: Path) -> None:
    engine = _fake_engine(tmp_path / "engine")
    (engine / "docs" / "glossary.md").unlink()
    with pytest.raises(EngineSyncError, match="glossary.md"):
        build_manifest(engine, "a" * 40)


def _synced(tmp_path: Path) -> Path:
    engine = _fake_engine(tmp_path / "engine")
    manifest = build_manifest(engine, "a" * 40)
    out = tmp_path / "_engine"
    out.mkdir()
    for dest, source in ENGINE_DOCS:
        (out / dest).write_bytes((engine / source).read_bytes())
    (out / "manifest.json").write_text(json.dumps(manifest))
    return out


def test_check_manifest_is_clean_on_a_matching_copy(tmp_path: Path) -> None:
    assert check_manifest(_synced(tmp_path), "a" * 40) == []


def test_check_manifest_names_a_changed_file(tmp_path: Path) -> None:
    out = _synced(tmp_path)
    (out / "usage.md").write_text("tampered\n")
    assert any("usage.md" in problem for problem in check_manifest(out, "a" * 40))


def test_check_manifest_names_a_missing_file(tmp_path: Path) -> None:
    out = _synced(tmp_path)
    (out / "glossary.md").unlink()
    assert any("glossary.md" in problem for problem in check_manifest(out, "a" * 40))


def test_check_manifest_names_a_commit_mismatch(tmp_path: Path) -> None:
    out = _synced(tmp_path)
    assert any("engine_commit" in problem for problem in check_manifest(out, "b" * 40))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest -q tests/test_engine_sync.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.engine_sync'`.

- [ ] **Step 3: Write the pure part of `tools/engine_sync.py`**

```python
"""Fetch the pinned engine checkout and sync its docs into the site.

The engine is a separate repository. A collaborator fetches it at the commit
the Engine arm pins; the sync copies the engine's own docs into a committed
``_engine/`` directory outside the site's source directory, with a manifest of
the pinned commit and each file's sha256, so the site shows the engine's own
bytes and a test can prove it. No model and no harness behavior.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path

DEFAULT_ARM = Path("arms/engine-ornith15-9b.json")
DEFAULT_OUTPUT = Path("_engine")
DEFAULT_ENGINE_URL = "https://github.com/pauleveritt/satyrn-engine.git"
MANIFEST_NAME = "manifest.json"
#: (destination name under _engine/, source path in the engine repository)
ENGINE_DOCS: tuple[tuple[str, str], ...] = (
    ("README.md", "README.md"),
    ("usage.md", "docs/usage.md"),
    ("glossary.md", "docs/glossary.md"),
)


class EngineSyncError(Exception):
    """The fetch or sync could not proceed; the message names the step."""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_arm(path: Path) -> Mapping:
    return json.loads(path.read_text())


def engine_pin(arm: Mapping) -> str:
    pin = arm.get("pins", {}).get("engine_commit")
    if not isinstance(pin, str) or not pin:
        raise EngineSyncError("the arm pins no engine_commit")
    return pin


def build_manifest(
    engine_repo: Path,
    commit: str,
    *,
    repository: str = DEFAULT_ENGINE_URL,
    docs: Sequence[tuple[str, str]] = ENGINE_DOCS,
) -> dict:
    files: dict[str, dict[str, str]] = {}
    for dest, source in docs:
        path = engine_repo / source
        if not path.is_file():
            raise EngineSyncError(f"the engine checkout has no {source}")
        files[dest] = {"source": source, "sha256": sha256(path)}
    return {"engine_commit": commit, "source_repository": repository, "files": files}


def check_manifest(
    engine_dir: Path,
    expected_commit: str,
    docs: Sequence[tuple[str, str]] = ENGINE_DOCS,
) -> list[str]:
    manifest_path = engine_dir / MANIFEST_NAME
    try:
        manifest = json.loads(manifest_path.read_text())
    except OSError:
        return [f"no manifest at {manifest_path}"]
    problems: list[str] = []
    if manifest.get("engine_commit") != expected_commit:
        problems.append(
            f"{manifest_path}: engine_commit {manifest.get('engine_commit')!r} "
            f"is not the arm's {expected_commit!r}"
        )
    files = manifest.get("files")
    if not isinstance(files, dict):
        return [*problems, f"{manifest_path}: no files mapping"]
    wanted = {dest: source for dest, source in docs}
    if set(files) != set(wanted):
        problems.append(f"{manifest_path}: files are {sorted(files)}, expected {sorted(wanted)}")
    for dest, source in docs:
        entry = files.get(dest)
        if not isinstance(entry, dict) or entry.get("source") != source:
            continue
        path = engine_dir / dest
        if not path.is_file():
            problems.append(f"{path} is missing")
        elif sha256(path) != entry.get("sha256"):
            problems.append(f"{path} does not match its manifest digest")
    return problems
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest -q tests/test_engine_sync.py`
Expected: PASS (8 tests).

- [ ] **Step 5: Record provenance and commit**

```bash
uv run python tools/provenance.py new tools/engine_sync.py tests/test_engine_sync.py
just gates
git add tools/engine_sync.py tests/test_engine_sync.py PROVENANCE.md
git commit -m "Engine sync: the manifest helpers

Co-Authored-By: deepseek-v4-flash <noreply@deepseek.com>"
```

Expected: `just gates` exits 0.

---

### Task 3: Fetch and sync commands

**Files:**
- Modify: `tools/engine_sync.py`
- Modify: `Justfile`
- Test: `tests/integration/test_engine_sync.py`

**Interfaces:**
- Consumes: `build_manifest`, `check_manifest`, `engine_pin`, `load_arm`, `EngineSyncError`, `DEFAULT_ARM`, `DEFAULT_OUTPUT`, `DEFAULT_ENGINE_URL`, `MANIFEST_NAME`, `ENGINE_DOCS`.
- Produces: `head_commit(engine_repo) -> str`; `fetch_engine(dest, commit, *, repository=DEFAULT_ENGINE_URL) -> Path`; `sync_engine(engine_repo, engine_dir, commit, *, repository=DEFAULT_ENGINE_URL, record_provenance=True) -> dict`; `main(argv=None) -> int` with `fetch` and `sync` subcommands.

- [ ] **Step 1: Write the failing integration tests**

Create `tests/integration/test_engine_sync.py`:

```python
import os
import subprocess
from pathlib import Path

import pytest

from tools.engine_sync import (
    EngineSyncError,
    check_manifest,
    engine_pin,
    fetch_engine,
    head_commit,
    load_arm,
    sync_engine,
)

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[2]
ARM = ROOT / "arms" / "engine-ornith15-9b.json"


def _origin(tmp_path: Path) -> tuple[Path, str]:
    origin = tmp_path / "origin"
    origin.mkdir()
    for argv in (
        ("init", "-q", "-b", "main"),
        ("config", "user.email", "t@example.com"),
        ("config", "user.name", "t"),
    ):
        subprocess.run(["git", *argv], cwd=origin, check=True, capture_output=True, text=True)
    (origin / "README.md").write_text("readme\n")
    subprocess.run(["git", "add", "README.md"], cwd=origin, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-q", "-m", "one"], cwd=origin, check=True, capture_output=True, text=True)
    commit = subprocess.run(
        ["git", "-C", str(origin), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    return origin, commit


def test_fetch_engine_clones_a_repository_at_a_commit(tmp_path: Path) -> None:
    origin, commit = _origin(tmp_path)
    dest = tmp_path / "checkout"
    fetch_engine(dest, commit, repository=str(origin))
    assert head_commit(dest) == commit
    assert (dest / "README.md").read_text() == "readme\n"


def test_fetch_engine_refuses_a_checkout_at_another_commit(tmp_path: Path) -> None:
    origin, commit = _origin(tmp_path)
    dest = tmp_path / "checkout"
    fetch_engine(dest, commit, repository=str(origin))
    with pytest.raises(EngineSyncError, match="not the pinned"):
        fetch_engine(dest, "0" * 40, repository=str(origin))


def _checkout() -> Path | None:
    env = os.environ.get("SATYRN_ENGINE_REPO")
    candidate = Path(env) if env else ROOT.parent / "satyrn-engine"
    return candidate if (candidate / ".git").exists() else None


def test_resync_matches_the_committed_copy(tmp_path: Path) -> None:
    checkout = _checkout()
    if checkout is None:
        pytest.skip("no satyrn-engine checkout")
    commit = engine_pin(load_arm(ARM))
    if head_commit(checkout) != commit:
        pytest.skip(f"checkout is not at the pinned {commit}")
    manifest = sync_engine(checkout, tmp_path / "_engine", commit, record_provenance=False)
    assert check_manifest(tmp_path / "_engine", commit) == []
    assert manifest["engine_commit"] == commit
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest -m integration -q tests/integration/test_engine_sync.py`
Expected: FAIL with `ImportError: cannot import name 'fetch_engine'`.

- [ ] **Step 3: Add the subprocess part and `main` to `tools/engine_sync.py`**

Add these imports at the top:

```python
import argparse
import os
import shutil
import subprocess
import sys
```

Append the functions:

```python
def head_commit(engine_repo: Path) -> str:
    result = subprocess.run(
        ["git", "-C", os.fspath(engine_repo), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise EngineSyncError(f"cannot read HEAD of {engine_repo}: {result.stderr.strip()}")
    return result.stdout.strip()


def fetch_engine(dest: Path, commit: str, *, repository: str = DEFAULT_ENGINE_URL) -> Path:
    if dest.exists():
        if head_commit(dest) == commit:
            return dest
        raise EngineSyncError(
            f"{dest} is at {head_commit(dest)}, not the pinned {commit}; remove it deliberately"
        )
    dest.parent.mkdir(parents=True, exist_ok=True)
    cloned = subprocess.run(
        ["git", "clone", "--quiet", repository, os.fspath(dest)],
        capture_output=True, text=True, check=False,
    )
    if cloned.returncode != 0:
        raise EngineSyncError(f"git clone {repository} failed: {cloned.stderr.strip()}")
    checked_out = subprocess.run(
        ["git", "-C", os.fspath(dest), "checkout", "--quiet", "--detach", commit],
        capture_output=True, text=True, check=False,
    )
    if checked_out.returncode != 0:
        raise EngineSyncError(f"git checkout {commit} in {dest} failed: {checked_out.stderr.strip()}")
    return dest


def sync_engine(
    engine_repo: Path,
    engine_dir: Path,
    commit: str,
    *,
    repository: str = DEFAULT_ENGINE_URL,
    record_provenance: bool = True,
) -> dict:
    if head_commit(engine_repo) != commit:
        raise EngineSyncError(f"{engine_repo} is not at the pinned {commit}")
    manifest = build_manifest(engine_repo, commit, repository=repository)
    engine_dir.mkdir(parents=True, exist_ok=True)
    for dest, source in ENGINE_DOCS:
        shutil.copyfile(engine_repo / source, engine_dir / dest)
    (engine_dir / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    if record_provenance:
        from tools.provenance import record_source

        record_source(
            engine_dir.parent,
            f"satyrn-engine @ {commit}",
            [f"{engine_dir.name}/{dest}" for dest, _ in ENGINE_DOCS],
        )
        record_source(
            engine_dir.parent,
            f"generated by tools/engine_sync.py from satyrn-engine @ {commit}",
            [f"{engine_dir.name}/{MANIFEST_NAME}"],
        )
    return manifest


def _engine_repo(argument: str | None, root: Path) -> Path:
    if argument:
        return Path(argument)
    env = os.environ.get("SATYRN_ENGINE_REPO")
    if env:
        return Path(env)
    return (root / ".." / "satyrn-engine").resolve()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="engine_sync")
    sub = parser.add_subparsers(dest="command", required=True)
    fetch = sub.add_parser("fetch", help="clone the pinned engine commit into a checkout")
    fetch.add_argument("--arm", default=os.fspath(DEFAULT_ARM))
    fetch.add_argument("--engine-repo", default=None)
    fetch.add_argument("--url", default=DEFAULT_ENGINE_URL)
    sync = sub.add_parser("sync", help="copy the pinned engine's docs into the committed _engine/ copy")
    sync.add_argument("--arm", default=os.fspath(DEFAULT_ARM))
    sync.add_argument("--engine-repo", default=None)
    sync.add_argument("--output", default=os.fspath(DEFAULT_OUTPUT))
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    root = Path.cwd()
    try:
        commit = engine_pin(load_arm(root / args.arm))
        engine_repo = _engine_repo(args.engine_repo, root)
        if args.command == "fetch":
            fetch_engine(engine_repo, commit, repository=args.url)
            print(f"export SATYRN_ENGINE_REPO={engine_repo}")
            return 0
        manifest = sync_engine(engine_repo, root / args.output, commit)
        print(f"synced {len(manifest['files'])} engine docs at {commit} into {root / args.output}")
        return 0
    except EngineSyncError as exc:
        print(f"engine-sync: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the integration tests to verify they pass**

Run: `uv run pytest -m integration -q tests/integration/test_engine_sync.py`
Expected: `3 passed` (or `2 passed, 1 skipped` when no engine checkout is present).

- [ ] **Step 5: Add the Justfile recipes**

Add after the `docs-serve` recipe:

```make
# Fetch satyrn-engine at the commit the Engine arm pins, into ../satyrn-engine.
fetch-engine:
    uv run python -m tools.engine_sync fetch

# Sync the pinned engine's docs into the committed _engine/ copy and its provenance rows.
sync-engine:
    uv run python -m tools.engine_sync sync
```

- [ ] **Step 6: Verify the usage error is clean**

Run: `uv run python -m tools.engine_sync; echo "EXIT=$?"`
Expected: argparse usage on stderr, `EXIT=2`.

- [ ] **Step 7: Record provenance and commit**

```bash
uv run python tools/provenance.py new tests/integration/test_engine_sync.py
just gates
git add tools/engine_sync.py Justfile tests/integration/test_engine_sync.py PROVENANCE.md
git commit -m "Engine sync: fetch and sync commands, with recipes

Co-Authored-By: deepseek-v4-flash <noreply@deepseek.com>"
```

Expected: `just gates` exits 0.

---

### Task 4: The committed engine copy

**Files:**
- Create: `_engine/README.md`, `_engine/usage.md`, `_engine/glossary.md`, `_engine/manifest.json` (via `just sync-engine`)
- Modify: `PROVENANCE.md` (written by the sync)
- Test: `tests/test_engine_docs.py`

**Interfaces:**
- Consumes: `check_manifest`, `engine_pin`, `load_arm`, `MANIFEST_NAME`.
- Produces: the committed `_engine/` directory and its provenance rows.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_engine_docs.py`:

```python
import json
from pathlib import Path

from tools.engine_sync import MANIFEST_NAME, check_manifest, engine_pin, load_arm

ROOT = Path(__file__).resolve().parents[1]
ARM = ROOT / "arms" / "engine-ornith15-9b.json"
ENGINE_DIR = ROOT / "_engine"


def test_the_manifest_commit_matches_the_engine_arms_pin() -> None:
    commit = engine_pin(load_arm(ARM))
    manifest = json.loads((ENGINE_DIR / MANIFEST_NAME).read_text())
    assert manifest["engine_commit"] == commit


def test_the_committed_copy_matches_its_manifest() -> None:
    commit = engine_pin(load_arm(ARM))
    assert check_manifest(ENGINE_DIR, commit) == []


def test_the_manifest_names_the_engine_repository() -> None:
    manifest = json.loads((ENGINE_DIR / MANIFEST_NAME).read_text())
    assert manifest["source_repository"] == "https://github.com/pauleveritt/satyrn-engine.git"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest -q tests/test_engine_docs.py`
Expected: FAIL with `FileNotFoundError` on `_engine/manifest.json`.

- [ ] **Step 3: Run the sync**

Run: `just sync-engine; echo "EXIT=$?"`
Expected: `EXIT=0`, a line `synced 3 engine docs at 78ab87d... into .../_engine`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest -q tests/test_engine_docs.py`
Expected: `3 passed`.

- [ ] **Step 5: Verify provenance and commit**

```bash
uv run python tools/provenance.py check
uv run python tools/provenance.py new tests/test_engine_docs.py
uv run python tools/provenance.py check
just gates
git add _engine/README.md _engine/usage.md _engine/glossary.md _engine/manifest.json tests/test_engine_docs.py PROVENANCE.md
git commit -m "Engine sync: the committed engine docs and their manifest

Co-Authored-By: deepseek-v4-flash <noreply@deepseek.com>"
```

Expected: the first `check` names `tests/test_engine_docs.py`; after `new`, the second `check` is clean; `just gates` exits 0. `_engine/` rows were written by the sync.

---

### Task 5: The site's engine section

**Files:**
- Create: `site/engine.md`, `site/engine-usage.md`, `site/engine-glossary.md`
- Modify: `zensical.toml`
- Test: `tests/test_engine_pages.py`

**Interfaces:**
- Consumes: `MANIFEST_NAME`, `ENGINE_DOCS`; the `_engine/` copy from Task 4.
- Produces: three site pages whose includes are `_engine/README.md`, `_engine/usage.md`, `_engine/glossary.md`, and nav entries for them.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_engine_pages.py`:

```python
import json
import re
from pathlib import Path

from tools.engine_sync import MANIFEST_NAME

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
INCLUDE = re.compile(r'--8<--\s+"([^"]+)"')


def _manifest() -> dict:
    return json.loads((ROOT / "_engine" / MANIFEST_NAME).read_text())


def test_every_engine_include_is_in_the_manifest() -> None:
    named = {f"_engine/{dest}" for dest in _manifest()["files"]}
    targets = {
        target
        for page in SITE.glob("**/*.md")
        for target in INCLUDE.findall(page.read_text())
        if target.startswith("_engine/")
    }
    assert targets == named


def test_engine_pages_banner_names_the_manifest_commit() -> None:
    commit = _manifest()["engine_commit"]
    pages = sorted(SITE.glob("engine*.md"))
    assert pages
    for page in pages:
        assert commit in page.read_text(), page
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest -q tests/test_engine_pages.py`
Expected: FAIL — `targets == named` is false (no pages yet).

- [ ] **Step 3: Create the pages**

`site/engine.md`:

```markdown
---
title: The engine
---

Synced from `satyrn-engine` `78ab87dbab3381dd585986c43fd49e6e4974f6b6`; do not edit here.

--8<-- "_engine/README.md"
```

`site/engine-usage.md`:

```markdown
---
title: Using the engine
---

Synced from `satyrn-engine` `78ab87dbab3381dd585986c43fd49e6e4974f6b6`; do not edit here.

--8<-- "_engine/usage.md"
```

`site/engine-glossary.md`:

```markdown
---
title: Glossary
---

Synced from `satyrn-engine` `78ab87dbab3381dd585986c43fd49e6e4974f6b6`; do not edit here.

--8<-- "_engine/glossary.md"
```

- [ ] **Step 4: Add the nav entries**

In `zensical.toml`, insert after the `"The numbers"` entry:

```toml
  { "The engine" = "engine.md" },
  { "Using the engine" = "engine-usage.md" },
  { "Glossary" = "engine-glossary.md" },
```

- [ ] **Step 5: Run the tests and the build**

Run: `uv run pytest -q tests/test_engine_pages.py tests/test_docs_site.py`
Expected: PASS.

Run: `just docs; echo "EXIT=$?"`
Expected: `No issues found`, `EXIT=0`.

- [ ] **Step 6: Record provenance and commit**

```bash
uv run python tools/provenance.py new site/engine.md site/engine-usage.md site/engine-glossary.md tests/test_engine_pages.py
just gates
git add site/engine.md site/engine-usage.md site/engine-glossary.md tests/test_engine_pages.py zensical.toml PROVENANCE.md
git commit -m "Docs site: the engine section, synced and digest-tested

Co-Authored-By: deepseek-v4-flash <noreply@deepseek.com>"
```

Expected: `just gates` exits 0.

---

### Task 6: Whole-path verification

**Files:** none.

- [ ] **Step 1: Run every gate and read its exit code**

```bash
just gates; echo "GATES_EXIT=$?"
```

Expected: `GATES_EXIT=0`.

- [ ] **Step 2: List the built pages**

```bash
find _build -name '*.html' | sort
```

Expected: `404.html`, `index.html`, `numbers/index.html`, `release-one-negative/index.html`, `lessons/index.html`, `engine/index.html`, `engine-usage/index.html`, `engine-glossary/index.html`.

- [ ] **Step 3: Prove the engine bytes are on the site**

```bash
rg -c 'Satyrn Engine' _build/engine/index.html
```

Expected: a positive count.

- [ ] **Step 4: Report**

State the built page list, the commands run, the exit codes, and anything the plan could not do (for example, a skipped integration test because no engine checkout was present).

---

## Self-Review

**Spec coverage:**
- §4 fetch the arm's pin → Task 3 (`fetch_engine`, `fetch-engine`).
- §5 committed, digest-tested sync + manifest → Tasks 2 and 4.
- §6 tests → Tasks 2, 3, 4, 5.
- §7 engine section and banners → Task 5.
- §8 provenance `record --source`, idempotent, `_engine` tracked → Task 1 and Task 4.
- §9 no harness change → no task touches `src/satyrn_evals/` or `arms/`.
- §10 out of scope → not implemented.
- §11 open items → the full-clone deviation is recorded in Global Constraints.

**Placeholder scan:** no `TBD`/`TODO`; every code step carries real code; every command carries an expected result.

**Type consistency:** `build_manifest`, `check_manifest`, `engine_pin`, `load_arm`, `fetch_engine`, `sync_engine`, `head_commit`, `record_source`, and the constants `ENGINE_DOCS`, `MANIFEST_NAME`, `DEFAULT_ARM`, `DEFAULT_OUTPUT`, `DEFAULT_ENGINE_URL`, `EngineSyncError` are defined once and used with the same names throughout.
