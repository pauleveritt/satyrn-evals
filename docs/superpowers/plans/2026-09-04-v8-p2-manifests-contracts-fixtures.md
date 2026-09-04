# V8 Plan 2 of 5 — Manifests, contracts, fixtures (slice 1b)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Author the six tasks' hidden manifests with failure-digest contracts, per-task projects/public tests/overlays/licenses/provenance, and `known_good`/`known_broken` fixtures whose application is validated — offline-verifiable in the default tier.

**Architecture:** Plan 2 of 5 for V8 (`docs/superpowers/specs/2026-09-04-v8-agentclinic-evals-design.md` §2, §4, §11). Continues Plan 1's vendoring (the composed `base/` trees). Manifests mirror the V7 hidden shape; contracts are failure digests naming test ids and assertion messages, never file names.

**Tech Stack:** Python 3.14, `uv`, `pytest`, git.

**Spec:** `docs/superpowers/specs/2026-09-04-v8-agentclinic-evals-design.md` (§2 tables, §4, §11, §14).

## Global Constraints

- Python `>=3.14`; real return annotations; `match`/`case`/walrus house style.
- Default tier: no model/network/subprocess (planted spawn tripwire). Real git/pytest/uv runs are `@pytest.mark.integration` or recorded ad hoc commands.
- A refusal test has a sibling success test, always.
- 100% statement+branch coverage gate stays green; `ruff check .` and `just lint-docs` clean.
- MIT notice from swiftstar retained per task (`LICENSE`); `PROVENANCE` names commit, state, reconstruction rule, pins.
- Contracts never contain any string in the overlay-declared set (`overlay`, `test_acceptance.py`, `overlay/test_acceptance.py`) — `manifest.py:111-127` refuses them.

### Task 3: Projects, public tests, overlays, licenses, provenance (per task)

**Explicit design decision (recorded; do not treat as routine).** Vendoring
`reference/tests/test_app.py` as public tests in each `base/`, and including
`tests/` in `source_paths`, REVERSES the round-1 recommendation "no public
tests in `base/`" (approved with Part 1 of the brainstorm). The reversal was
made at maintainer review round 1 (lean to vendoring), recorded in spec
§11.7 with its reason, and the spec was approved as amended. This plan
implements the approved spec; restoring no-public-tests would be a spec
amendment (back to review), not a plan edit. Consequence (spec §11.5): with
`tests/` inside `source_paths`, public-test edits cannot void an attempt,
and the hidden overlay is the sole grade — safe only because P3's
contamination subtraction lands before P4's gate runs.

**Files:** per state: `base/pyproject.toml`, `base/uv.lock`, `base/tests/test_app.py`, `overlay/test_acceptance.py`, `LICENSE`, `PROVENANCE`.

**Interfaces:** Produces the task dirs Task 4's manifests reference; `base/pyproject.toml` is what P2's `has_locked_project` detects.

- [ ] **Step 1: Author the shared `base/pyproject.toml` (name per state)**

```toml
[project]
name = "agentclinic-complaints-<state>"
version = "0.1.0"
description = "Seeded broken state <state> of the AgentClinic complaints app (repair fixture)"
requires-python = ">=3.12"
dependencies = [
  "fastapi[standard]==0.115.10",
  "turbohtml==1.5.0",
  "httpx",
]

[dependency-groups]
dev = ["pytest==8.3.4"]
```

- [ ] **Step 2: Lock each project** — per state: `cd src/satyrn_evals/tasks/agentclinic-repair-<state>/base && uv lock`; Expected: `uv.lock` resolved with fastapi 0.115.10 and the dev group. Commit the six locks.

- [ ] **Step 2b: Project-inventory test (sibling to Task 1's app-tree inventory)**

Extend `tests/test_agentclinic_reconstruction.py`:

```python
@pytest.mark.parametrize("state", STATES)
def test_base_has_exactly_the_locked_project_files(state: str) -> None:
    base = _base(state)
    project = sorted(p.name for p in base.iterdir()
                     if p.name in ("pyproject.toml", "uv.lock"))
    assert project == ["pyproject.toml", "uv.lock"], state
    assert (base / "uv.lock").read_text().strip()
```

Run: `uv run pytest tests/test_agentclinic_reconstruction.py -q`; PASS.

- [ ] **Step 3: Copy public tests and overlay (per state)**

```bash
for s in depth-2 depth-3 framing-2 framing-2-edit misleading-locus plausible-wrong-fix; do
  t="src/satyrn_evals/tasks/agentclinic-repair-$s"
  mkdir -p "$t/base/tests" "$t/overlay"
  cp ~/projects/pauleveritt/swiftstar/fixtures/agenttest/reference/tests/test_app.py "$t/base/tests/"
  cp ~/projects/pauleveritt/swiftstar/fixtures/agenttest/acceptance/test_acceptance.py "$t/overlay/"
done
```

(The public tests already landed in `base/tests/` via Task 1's `REF_FILES`; the copy here is the idempotent source-of-truth step.)

- [ ] **Step 4: Verify overlays are byte-identical** — `sha256sum src/satyrn_evals/tasks/agentclinic-repair-{depth-2,framing-2,misleading-locus}/overlay/test_acceptance.py`; Expected: identical hashes across all six (spec §2's six self-contained copies).

- [ ] **Step 5: Write per-task `LICENSE` and `PROVENANCE`** — `LICENSE`: the swiftstar MIT text (c) 2026 Paul Everitt. `PROVENANCE`: swiftstar remote + commit (`git -C ~/projects/pauleveritt/swiftstar rev-parse HEAD`), the state, the reconstruction rule ("reference tree + `repair/<state>` deltas, `.delete` honored; `tests/test_app.py` public"), the pins, the digest re-derivation date. For `framing-2` add: "superseded for its original purpose per `repair/framing-2-edit/README.md`; retained as the only author-from-scratch cell."

- [ ] **Step 6: Commit** — `git add src/satyrn_evals/tasks/agentclinic-repair-*` then `git commit -m "feat: agentclinic bases gain projects, public tests, overlays, provenance"`.

### Task 4: Six hidden manifests with failure-digest contracts

**Files:** create `manifest.json` per state. **Interfaces:** consumed by P4's gate; must satisfy `load_manifest` incl. `_assert_contract_names_no_overlay`.

- [ ] **Step 1: Write the reference manifest for `plausible-wrong-fix`**

```json
{
  "name": "agentclinic-repair-plausible-wrong-fix",
  "contract": "Repair the seeded bug in the AgentClinic complaints app. The suite reports one failing check, test_post_complaint_redirects_to_complaints_board (assert 307 == 303: the POST response is a 307 Temporary Redirect, expected 303 See Other). The seeded defect is in app.py; fix it so the redirect is a 303 and the complaint is recorded. Your workspace has a runnable public suite under tests/ (uv run pytest tests/); a fix must keep every existing behavior intact.",
  "oracle": ["python", "-m", "pytest", "-p", "satyrn_evals.oracle_hook"],
  "expected_test_ids": [
    "test_acceptance.py::test_home_still_returns_200_and_tagline",
    "test_acceptance.py::test_home_has_html5_doctype",
    "test_acceptance.py::test_home_html_element_declares_english_language",
    "test_acceptance.py::test_home_still_has_navigation_links",
    "test_acceptance.py::test_complaints_board_still_lists_seed_complaint",
    "test_acceptance.py::test_complaints_board_preserves_the_shared_layout",
    "test_acceptance.py::test_complaints_board_still_has_its_heading",
    "test_acceptance.py::test_complaints_board_still_renders_seed_complaint_details",
    "test_acceptance.py::test_complaint_model_contract_is_preserved",
    "test_acceptance.py::test_seed_complaint_count_is_preserved",
    "test_acceptance.py::test_post_complaint_redirects_to_complaints_board",
    "test_acceptance.py::test_posted_complaint_appears_on_complaints_board",
    "test_acceptance.py::test_complaints_board_renders_add_complaint_form"
  ],
  "source_paths": ["app.py", "models.py", "templates", "tests"],
  "fixtures": {
    "known_good": "fixtures/known-good.patch",
    "known_broken": "fixtures/known-broken.patch"
  },
  "grader_overlay": "overlay",
  "oracle_visibility": "hidden",
  "provenance": {
    "repo": "github.com/pauleveritt/swiftstar",
    "state": "plausible-wrong-fix",
    "reconstruction": "reference tree + repair deltas; tests/test_app.py public",
    "pins": "fastapi[standard]==0.115.10 turbohtml==1.5.0 pytest==8.3.4"
  }
}
```

- [ ] **Step 2: Write the other five manifests by copy-and-vary** — per-state deltas: `name` and the contract's failing-check sentence (below). All six share the 13 `expected_test_ids`, `source_paths`, `fixtures` keys, `grader_overlay`, `oracle_visibility`. The two collection-abort states say "the suite aborts at collection" — never a filename.

| state | contract failing-check sentence |
|---|---|
| `misleading-locus` | one failing check, test_posted_complaint_appears_on_complaints_board: the posted complaint never appears on the board — the POST handler appends to a copy of the seed list |
| `depth-2` | three failing checks, test_home_html_element_declares_english_language, test_complaints_board_preserves_the_shared_layout, test_post_complaint_redirects_to_complaints_board: a template change dropped the html lang attribute ('NoneType' object has no attribute 'casefold') and broke the redirect |
| `depth-3` | four failing checks: the depth-2 three plus test_complaint_model_contract_is_preserved (assert None is not None) — a models/app change broke the layout, the model contract, and the redirect |
| `framing-2` | the suite aborts at collection: importing the app fails because the model module is missing; recreate it per the app's imports and repair app.py |
| `framing-2-edit` | the suite aborts at collection: the model module has no complaints attribute; make the module contract hold and repair the app import |

- [ ] **Step 3: Write the default-tier manifest tests** (`tests/test_agentclinic_manifests.py`)

```python
import json
from pathlib import Path

import pytest

from satyrn_evals.errors import ManifestError
from satyrn_evals.manifest import load_manifest, resolve_task
from tests.test_agentclinic_reconstruction import STATES

FORBIDDEN = ("overlay", "test_acceptance.py", "overlay/test_acceptance.py")


@pytest.mark.parametrize("state", STATES)
def test_manifest_loads_and_is_hidden(state: str) -> None:
    manifest = load_manifest(resolve_task(f"agentclinic-repair-{state}"))
    assert manifest.oracle_visibility == "hidden"
    assert manifest.grader_overlay == "overlay"
    assert len(manifest.expected_test_ids) == 13
    assert len(set(manifest.expected_test_ids)) == 13
    assert all(tid.startswith("test_acceptance.py::") for tid in manifest.expected_test_ids)


@pytest.mark.parametrize("state", STATES)
def test_contract_names_no_grader_path(state: str) -> None:
    manifest = load_manifest(resolve_task(f"agentclinic-repair-{state}"))
    for name in FORBIDDEN:
        assert name not in manifest.contract, f"{state} contract names {name}"
```

- [ ] **Step 4: Refusal sibling (end to end, at load)** — same file:

```python
def test_manifest_whose_contract_names_overlay_is_refused(tmp_path: Path) -> None:
    src = resolve_task("agentclinic-repair-plausible-wrong-fix")
    data = json.loads((src / "manifest.json").read_text())
    data["contract"] = "the failure is in test_acceptance.py — fix it"
    root = tmp_path / "tasks"
    (root / data["name"]).mkdir(parents=True)
    for child in src.iterdir():
        if child.name != "manifest.json":
            (root / data["name"] / child.name).symlink_to(child)
    (root / data["name"] / "manifest.json").write_text(json.dumps(data))
    with pytest.raises(ManifestError):
        load_manifest(root / data["name"])
```

- [ ] **Step 5: Run** — `uv run pytest tests/test_agentclinic_manifests.py tests/test_agentclinic_reconstruction.py -q`; Expected: PASS.

- [ ] **Step 6: Commit** — `git add src/satyrn_evals/tasks/agentclinic-repair-*/manifest.json tests/test_agentclinic_manifests.py` then `git commit -m "feat: six hidden agentclinic manifests with failure-digest contracts"`.

### Task 5: `known_good` and `known_broken` fixtures (per task)

**Files:** create `fixtures/known-good.patch`, `fixtures/known-broken.patch` per state. **Interfaces:** P4's gate grades these by name.

- [ ] **Step 1: Generate each `known-good.patch` from a scratch git repo** (task-relative
`a/`/`b/` headers — never `--no-index` against absolute temp paths, whose
headers would carry temp-dir components and fail the allowlist)

```bash
for s in depth-2 depth-3 framing-2 framing-2-edit misleading-locus plausible-wrong-fix; do
  t="src/satyrn_evals/tasks/agentclinic-repair-$s"
  scratch=$(mktemp -d)
  git -C "$scratch" init -q
  cp -r "$t/base/." "$scratch/"
  git -C "$scratch" add -A
  git -C "$scratch" -c user.email=v8@local -c user.name=v8 commit -qm base
  # replace every tracked file with the reference (fixed) tree
  for f in $(git -C "$scratch" ls-files); do rm -f "$scratch/$f"; done
  for f in app.py models.py templates/home.html templates/base.html templates/complaints.html tests/test_app.py; do
    mkdir -p "$scratch/$(dirname "$f")"
    cp ~/projects/pauleveritt/swiftstar/fixtures/agenttest/reference/"$f" "$scratch/$f"
  done
  git -C "$scratch" add -A
  # index vs HEAD: a/ b/ paths are task-relative; framing-2 shows models.py
  # as a new file (author-from-scratch is the point)
  git -C "$scratch" diff --cached -- app.py models.py templates tests \
    > "$t/fixtures/known-good.patch"
  rm -rf "$scratch"
done
```

The patch touches only `source_paths` files.

- [ ] **Step 2: Verify each known-good parses and stays in scope (default tier)** — extend `tests/test_agentclinic_manifests.py`:

```python
from satyrn_evals.patch import parse_patch_paths
from satyrn_evals.manifest import load_manifest


@pytest.mark.parametrize("state", STATES)
def test_known_good_patch_is_in_scope_and_nonempty(state: str) -> None:
    task_dir = resolve_task(f"agentclinic-repair-{state}")
    manifest = load_manifest(task_dir)
    patch = (task_dir / "fixtures" / "known-good.patch").read_text()
    assert patch.strip()
    paths = parse_patch_paths(patch)
    assert paths, state
    allowed = manifest.source_paths
    for path in paths:
        assert any(path == a or path.startswith(f"{a}/") for a in allowed), (state, path)
```

Run; PASS.

- [ ] **Step 3: Author each `known-broken.patch`** (a plausible wrong repair that still fails the oracle; P4 proves the failure). Wrong-repair intent per state:

| state | wrong-repair content |
|---|---|
| `plausible-wrong-fix` | set `303` on the wrong response object — symptom patched, complaint never recorded |
| `misleading-locus` | mutate the shared seed list in place — symptom gone, seed preservation broken |
| `depth-2` | hard-code `lang="en"` in the home template only — shared layout still broken |
| `depth-3` | alias `complaints` at module scope — model contract still broken |
| `framing-2` | stub `models.py` with only the imported names, wrong shapes — contract tests fail |
| `framing-2-edit` | add `complaints = []` at module scope — seed preservation fails |

Author each by editing a scratch git repo (same recipe as Step 1: commit the
broken tree, apply the wrong edit, `git diff --cached`) so headers stay
task-relative; record the intent in `PROVENANCE`.

- [ ] **Step 4: Extend the Step-2 test to `known_broken`** (parse + in-scope); run; PASS.

- [ ] **Step 4b: Apply-validation test (integration) — every fixture actually applies**

Create `tests/integration/test_agentclinic_fixtures_apply.py`:

```python
import shutil
import subprocess
from pathlib import Path

import pytest

from satyrn_evals.manifest import DEFAULT_TASKS_ROOT
from tests.test_agentclinic_reconstruction import STATES

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("state", STATES)
@pytest.mark.parametrize("fixture", ["known-good", "known-broken"])
def test_fixture_applies_cleanly_to_a_fresh_base(state: str, fixture: str,
                                                 tmp_path: Path) -> None:
    task_dir = DEFAULT_TASKS_ROOT / f"agentclinic-repair-{state}"
    work = tmp_path / state
    shutil.copytree(task_dir / "base", work)
    subprocess.run(["git", "init", "-q"], cwd=work, check=True, capture_output=True)
    patch = (task_dir / "fixtures" / f"{fixture}.patch").read_text()
    applied = subprocess.run(
        ["git", "apply", "-"], input=patch.encode(), cwd=work,
        capture_output=True)
    assert applied.returncode == 0, (state, fixture, applied.stderr.decode())
```

Run: `uv run pytest tests/integration/test_agentclinic_fixtures_apply.py -q`; PASS
(git apply is the integration-tier validation; P4 re-applies each fixture
through the real grade).

- [ ] **Step 5: Commit** — `git add src/satyrn_evals/tasks/agentclinic-repair-*/fixtures` then `git commit -m "feat: agentclinic known-good and known-broken fixtures"`.

### Task 6: Slice-1 self-review

- [ ] **Step 1: Coverage gate** — `uv run pytest -m '' --cov=src/satyrn_evals --cov-branch --cov-report=term-missing --cov-fail-under=100`; Expected: 100% (no production code changed in this plan).
- [ ] **Step 2: Ruff and doc caps** — `ruff check . && just lint-docs`; Expected: clean.
- [ ] **Step 3: Spec cross-check** — spec §2/§4/§11 map to tasks above; interfaces match P2-P4's expectations (`agentclinic-repair-<state>` tasks, 13-id `expected_test_ids`, `source_paths` incl. `tests`, `overlay` grader dir, digest contracts). Hand off to P2.
