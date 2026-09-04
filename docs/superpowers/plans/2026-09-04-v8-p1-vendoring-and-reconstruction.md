# V8 Plan 1 of 5 — Vendoring and reconstruction (slice 1a)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reconstruct the six `agentclinic-repair-*` bases from `swiftstar` per the spec's rule, pin their app-tree inventory by a default-tier test, and re-derive each state's failure signature as the evidence the contracts cite.

**Architecture:** Plan 1 of 5 for V8 (`docs/superpowers/specs/2026-09-04-v8-agentclinic-evals-design.md` §2, §14). The reconstruction is a one-time mechanical composition (reference tree + state deltas, `.delete` honored) whose result is committed and pinned by a default-tier inventory test.

**Tech Stack:** Python 3.14, `uv`, `pytest`. Inputs read-only from `~/projects/pauleveritt/swiftstar/fixtures/agenttest/`.

**Spec:** `docs/superpowers/specs/2026-09-04-v8-agentclinic-evals-design.md` (§2 tables, §14). Plan 2 of 5 (manifests, contracts, fixtures) continues slice 1.


> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Vendor the six `agentclinic-repair-*` tasks from `swiftstar` into `src/satyrn_evals/tasks/`, reconstructing each `base/` per the spec's rule, authoring projects, hidden manifests, failure-digest contracts, and `known_good`/`known_broken` fixtures — offline-verifiable in the default tier except the digest re-derivation run.

**Architecture:** Plan 1 of 4 for V8 (`docs/superpowers/specs/2026-09-04-v8-agentclinic-evals-design.md`), split along its §12 slices by `sdd.md`'s 400-line plan cap. The reconstruction is a one-time mechanical composition (reference tree + state deltas, `.delete` honored) whose result is committed and pinned by a default-tier inventory test. Manifests mirror the V7 hidden shape (`session-mechanics/manifest.json`). Contracts are failure digests naming test ids and assertion messages, never file names.

**Tech Stack:** Python 3.14, `uv`, `pytest`, git. Inputs read-only from `~/projects/pauleveritt/swiftstar/fixtures/agenttest/`.

**Spec:** `docs/superpowers/specs/2026-09-04-v8-agentclinic-evals-design.md` (esp. §2 tables, §4, §11, §14).

## Global Constraints

- Python `>=3.14`; real return annotations; `match`/`case`/walrus house style.
- Default tier: no model/network/subprocess (planted spawn tripwire). Real git/pytest/uv runs are `@pytest.mark.integration` in `tests/integration/` or recorded ad hoc commands.
- A refusal test has a sibling success test, always.
- 100% statement+branch coverage gate: `uv run pytest -m '' --cov=src/satyrn_evals --cov-branch --cov-fail-under=100` (no production code changes in this plan, so it must stay green).
- `ruff check .` clean; `just lint-docs` green.
- MIT notice from swiftstar retained per task (`LICENSE`); `PROVENANCE` names the swiftstar commit, state, reconstruction rule, pins.
- Contracts never contain any string in the overlay-declared set (`overlay`, `test_acceptance.py`, `overlay/test_acceptance.py`) — the validator refuses them (`manifest.py:111-127`).

### Task 1: Reconstruction script + six composed `base/` trees

**Files:** Create `tools/reconstruct_agentclinic.py`; create the six `base/` trees via the script; test `tests/test_agentclinic_reconstruction.py`.

**Interfaces:** Consumes the swiftstar fixtures (read-only) and the spec §2 delta table. Produces six committed `base/` trees; Tasks 3-4 add `pyproject.toml`, `uv.lock`, `tests/`, overlay.

- [ ] **Step 1: Write the failing inventory test**

```python
import pytest

from satyrn_evals.manifest import DEFAULT_TASKS_ROOT

STATES = ["depth-2", "depth-3", "framing-2", "framing-2-edit",
          "misleading-locus", "plausible-wrong-fix"]

# spec §2: per-state content overrides/additions, and .delete removals.
DELTA_FILES = {
    "depth-2": ["app.py", "templates/base.html"],
    "depth-3": ["models.py", "app.py", "templates/base.html"],
    "framing-2": ["app.py"],            # .delete removes models.py
    "framing-2-edit": ["models.py", "app.py"],
    "misleading-locus": ["app.py"],
    "plausible-wrong-fix": ["app.py"],
}
DELETED = {"framing-2": ["models.py"]}
SHARED = ["app.py", "models.py", "templates/home.html", "templates/base.html",
          "templates/complaints.html", "tests/test_app.py"]


def _base(state: str):
    return DEFAULT_TASKS_ROOT / f"agentclinic-repair-{state}" / "base"


@pytest.mark.parametrize("state", STATES)
def test_base_inventory_matches_reconstruction_rule(state: str) -> None:
    base = _base(state)
    assert base.is_dir(), f"missing base for {state}"
    # app-tree inventory only: project files (pyproject.toml, uv.lock) are
    # asserted separately by the Task-3 project test, which runs after lock.
    present = {
        p.relative_to(base).as_posix()
        for p in base.rglob("*")
        if p.is_file() and p.name not in ("pyproject.toml", "uv.lock")
    }
    expected = (set(SHARED) - set(DELETED.get(state, []))) | set(DELTA_FILES[state])
    assert present == expected, f"{state}: {sorted(present)} != {sorted(expected)}"


@pytest.mark.parametrize("state", STATES)
def test_no_junk_or_git_dirs_in_base(state: str) -> None:
    base = _base(state)
    bad = [p.name for p in base.rglob("*")
           if p.name in (".git", "__pycache__", ".delete", "README.md")]
    assert not bad, f"{state} base contains: {bad}"
```

- [ ] **Step 2: Run it to verify it fails** — `uv run pytest tests/test_agentclinic_reconstruction.py -q`; Expected: FAIL (six missing `base/` dirs).

- [ ] **Step 3: Write the reconstruction script**

```python
"""One-time vendoring: compose the six agentclinic repair bases from swiftstar.

Reconstruction rule (V8 spec §2): base = reference app tree (app.py, models.py,
templates/, tests/test_app.py) MINUS each .delete-named reference file, PLUS the
state's content overrides/additions. Per-state README*.md and .delete markers are
reconstruction meta, never vendored into base/.
"""
import shutil
from pathlib import Path

SRC = Path.home() / "projects/pauleveritt/swiftstar/fixtures/agenttest"
DEST = Path("src/satyrn_evals/tasks")

STATES = ["depth-2", "depth-3", "framing-2", "framing-2-edit",
          "misleading-locus", "plausible-wrong-fix"]
REF_FILES = ["app.py", "models.py", "templates/home.html",
             "templates/base.html", "templates/complaints.html",
             "tests/test_app.py"]


def main() -> None:
    for state in STATES:
        base = DEST / f"agentclinic-repair-{state}" / "base"
        shutil.rmtree(base, ignore_errors=True)
        base.mkdir(parents=True)
        for rel in REF_FILES:
            (base / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SRC / "reference" / rel, base / rel)
        state_dir = SRC / "repair" / state
        for path in state_dir.rglob("*"):
            if path.is_file() and path.name != ".delete" and not path.name.endswith("README.md"):
                rel = path.relative_to(state_dir)
                (base / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, base / rel)
        marker = state_dir / ".delete"
        if marker.exists():
            for line in marker.read_text().splitlines():
                (base / line.strip()).unlink(missing_ok=True)
        print(f"composed {state}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the script, then verify the test passes** — `uv run python tools/reconstruct_agentclinic.py` then `uv run pytest tests/test_agentclinic_reconstruction.py -q`; Expected: six "composed …" lines, then PASS.

- [ ] **Step 5: Byte-fidelity evidence (ad hoc)**

Run: `diff src/satyrn_evals/tasks/agentclinic-repair-framing-2/base/app.py ~/projects/pauleveritt/swiftstar/fixtures/agenttest/repair/framing-2/app.py && diff src/satyrn_evals/tasks/agentclinic-repair-depth-2/base/templates/base.html ~/projects/pauleveritt/swiftstar/fixtures/agenttest/repair/depth-2/templates/base.html`
Expected: no output (identical), for every state's delta file.

- [ ] **Step 6: Commit** — `git add tools/reconstruct_agentclinic.py src/satyrn_evals/tasks/agentclinic-repair-*` then `git commit -m "feat: vendor six agentclinic repair bases (reconstruction rule)"`.

### Task 2: Digest re-derivation run (integration evidence)

**Files:** no committed code; a recorded ad hoc run whose output Task 4's contracts cite.

- [ ] **Step 1: Run the six composed bases against the real suite, pinned**

```bash
for s in depth-2 depth-3 framing-2 framing-2-edit misleading-locus plausible-wrong-fix; do
  d=$(mktemp -d); cp -r "src/satyrn_evals/tasks/agentclinic-repair-$s/base/." "$d/"
  cp ~/projects/pauleveritt/swiftstar/fixtures/agenttest/acceptance/test_acceptance.py "$d/"
  echo "== $s =="
  (cd "$d" && uv run --no-project --quiet --with "fastapi[standard]==0.115.10" \
    --with "turbohtml==1.5.0" --with httpx --with "pytest==8.3.4" \
    python -m pytest -q --tb=line test_acceptance.py 2>&1 | tail -6)
  rm -rf "$d"
done
```

- [ ] **Step 2: Verify the output matches spec §2/§14 exactly** — `misleading-locus` 1 failed (`test_posted_complaint_appears_on_complaints_board`); `plausible-wrong-fix` 1 failed (`test_post_complaint_redirects_to_complaints_board`); `depth-2` 3 failed; `depth-3` 4 failed; `framing-2` and `framing-2-edit` collection errors. Any mismatch is a reconstruction bug — stop and fix Task 1.

- [ ] **Step 3: Capture the assertion-mismatch text** (re-derived 2026-09-04; reproduce): `plausible-wrong-fix` → "assert 307 == 303" (307 Temporary Redirect vs expected 303); `misleading-locus` → the posted agent name absent from the board response; `depth-2`/`depth-3` → `AttributeError: 'NoneType' object has no attribute 'casefold'` (missing `lang`) plus depth-3 `assert None is not None` (model contract). Copy the message text into Task 4's contracts, never the `test_acceptance.py` path prefix.

- [ ] **Step 4: Append "digest re-derived 2026-09-04" to each task's `PROVENANCE`** (Task 3 creates them); nothing else commits here.

