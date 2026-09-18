# Route-proof defect fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the Engine defects that made the 2026-09-18 route proof void, stage the census exclusion row, and pre-register the second route proof.

**Architecture:** The route proof was read as "steer 0 of 4", but the steer's trigger could not fire: the Engine's `self_test` returns exit 2 on this repo because `run_tests` appends the contract's `preserve` paths and pytest collects the fixture trees the repo's `norecursedirs` excludes. Two harness fixes precede any new night: `derive` must keep the repo's excluded directories out of `preserve`, and the launcher preflight must run one self-test on the unmodified base and require exit 0. The redirect-widening and the budget-mirror are design decisions recorded here, not silently made.

**Tech Stack:** Python 3.14 (`satyrn-engine`, `satyrn-evals`), TypeScript (Engine extension), pytest, node:test, uv.

**Spec:** the 2026-09-18 route-proof review (the maintainer's memo) and `docs/superpowers/specs/2026-09-17-release-two-engine-design.md` §7. Evidence: `records/2026-09-17-route-proof-engine-*.result.json`, `~/satyrn-runs/2026-09-17-route-proof-engine-*`.

## Global Constraints

- The default test tier uses no model, network, or subprocess; the tripwire in each repo's `tests/conftest.py` enforces it. Process behaviour is the `integration` tier.
- Every refusal test has a sibling success test.
- Grade from hook-written evidence, never stdout or exit status. Count events from `tool_execution_start`.
- The engine repo is frozen at `0b496d8`; these are the fixes that precede a re-freeze. Commits with explicit paths; never merge, push, or amend.
- Every new engine file has a row in the engine's `PROVENANCE.md`; `just gates` fails without one.
- No Engine design before diagnosed admission and an offline estimate; these are harness fixes, so they re-open nothing built on the engine's budget or steer, but the second route proof must be re-read on the fixed harness.
- Item 4 of the review (re-freeze, re-pin, second route proof) is attended and spending; it is out of this plan.

---

### Task 1: Engine — `preserve` honours the repo's pytest-excluded directories

**Files:**
- Modify: `satyrn-engine/src/satyrn_engine/derive.py` (add `_pytest_excluded_dirs`, `_is_excluded`; filter `preserve` in `derive_contract`)
- Test: `satyrn-engine/tests/test_derive.py`

**Interfaces:**
- Consumes: `RepoFacts(tracked, pyproject, head)`, `_PRESERVE_PATTERNS`, `fnmatch`, `tomllib`.
- Produces: `derive_contract` still returns a `Contract`; its `preserve` tuple no longer contains any tracked path under a `norecursedirs` entry.

- [ ] **Step 1: Write the failing test**

```python
def test_preserve_omits_the_repos_pytest_excluded_directories() -> None:
    tracked = (
        "pyproject.toml",
        "src/app/gate.py",
        "tests/test_gate.py",
        "tests/data/overlay-task/grader/overlay/test_hidden.py",
        "tests/integration/data/mini-session/base/test_solution.py",
    )
    pyproject = (
        '[project]\nname = "app"\n'
        "[tool.pytest.ini_options]\n"
        'norecursedirs = [".claude", "tests/data", "tests/integration/data"]\n'
    )
    contract = derive_contract("Fix src/app/gate.py", RepoFacts(tracked, pyproject, HEAD))
    assert contract.preserve == ("tests/test_gate.py",)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_derive.py::test_preserve_omits_the_repos_pytest_excluded_directories -v`
Expected: FAIL — the two fixture paths are in `contract.preserve`.

- [ ] **Step 3: Write minimal implementation**

In `derive.py`, beside `self_test_command`:

```python
def _pytest_excluded_dirs(pyproject: str) -> tuple[str, ...]:
    """The repo's declared pytest ``norecursedirs``, or ``()``.

    The carried set is restored before every self-test and `run_tests` runs
    the contract command once more with the carried paths appended. Naming a
    path pytest's own config excludes (``tests/data``,
    ``tests/integration/data`` in the self-hosted tasks) makes pytest collect
    it anyway -- an explicit path defeats ``norecursedirs`` -- so a repo whose
    suite is green still exits 2 on the fixture trees' import errors.
    """
    try:
        ini = tomllib.loads(pyproject).get("tool", {}).get("pytest", {}).get("ini_options", {})
    except tomllib.TOMLDecodeError:
        return ()
    declared = ini.get("norecursedirs") if isinstance(ini, dict) else None
    if not isinstance(declared, list):
        return ()
    return tuple(d for d in declared if isinstance(d, str) and d)


def _is_excluded(path: str, patterns: tuple[str, ...]) -> bool:
    """True when ``path`` is under a directory pytest is told not to recurse."""
    for pattern in patterns:
        prefix = pattern.rstrip("/")
        if path == prefix or path.startswith(prefix + "/"):
            return True
        if fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(path, f"{prefix}/*"):
            return True
    return False
```

In `derive_contract`, replace the `preserve` line:

```python
    excluded = _pytest_excluded_dirs(facts.pyproject)
    preserve = tuple(sorted(p for p in facts.tracked
                            if any(fnmatch(p, pat) for pat in _PRESERVE_PATTERNS)
                            and not _is_excluded(p, excluded)))
```

- [ ] **Step 4: Run test to verify it passes, then the file**

Run: `uv run pytest tests/test_derive.py -q`
Expected: PASS.

- [ ] **Step 5: Prove the sibling direction still holds**

`test_carried_sets_and_budgets_are_derived_from_the_repo` (a repo with no `norecursedirs`) must still see `("tests/test_cli.py", "tests/unit/test_gate.py")`. Run the whole default tier; expected `just gates` EXIT 0.

- [ ] **Step 6: Commit**

```bash
git add src/satyrn_engine/derive.py tests/test_derive.py
git commit -m "Release two fix: preserve honours the repo's pytest-excluded directories"
```

---

### Task 2: Engine — the self-test on a clean excluded tree exits 0

**Files:**
- Test: `satyrn-engine/tests/test_integration_runner.py` (integration tier) or a new `tests/test_integration_excluded_tree.py`
- Test: `satyrn-engine/tests/test_derive.py` (default tier, already Task 1)

**Interfaces:**
- Consumes: `derive_contract`, `run_tests`, a real temp git repo.
- Produces: evidence that a repo whose only red paths are pytest-excluded exits 0 through `run_tests`.

- [ ] **Step 1: Write the integration test**

Construct a temp git repo with `pyproject.toml` (declaring `norecursedirs = ["tests/data"]`), a passing `tests/test_ok.py`, and a `tests/data/bad/test_hidden.py` that raises on import. Derive the contract from its `RepoFacts`, call `run_tests(repo, contract, None)`, assert `result.exit_code == 0` and `"tests/data" not in " ".join(contract.preserve)`.

- [ ] **Step 2: Run it before the fix, then after**

Run: `uv run pytest -m integration tests/test_integration_excluded_tree.py -v`
Expected: RED on the unfixed tree (exit 2), GREEN with Task 1.

- [ ] **Step 3: Commit**

```bash
git add tests/test_integration_excluded_tree.py PROVENANCE.md
git commit -m "Release two fix: pin that an excluded tree self-tests green"
```

---

### Task 3: Evals — preflight runs one self-test on the unmodified base

**Files:**
- Modify: `satyrn-evals/src/satyrn_evals/cell_preflight.py` (or `launch_record.py`'s facts)
- Test: `satyrn-evals/tests/test_cell_preflight.py`

**Interfaces:**
- Consumes: the task's `public_suite` and the task base tree.
- Produces: a `CellPreflight` problem (non-empty `problems`) when the unmodified base's self-test exits non-zero; empty when it exits 0. This is the check the whole-path review owed: one self-test on the unmodified base must exit 0.

- [ ] **Step 1: Write the failing fixture test** (both directions): a fake base whose suite exits 0 adds no problem; one whose suite exits 2 adds a problem naming the base and the exit code.
- [ ] **Step 2: Run it to verify it fails.**
- [ ] **Step 3: Implement the check, reusing the preflight's existing subprocess seam.**
- [ ] **Step 4: Run the default and integration tiers.**
- [ ] **Step 5: Commit.**

---

### Task 4: Evals — stage the census exclusion row

**Files:**
- Modify: `satyrn-evals/evidence/2026-09-16-census/README.md` (under "Deviations, stated")

- [ ] **Step 1: Append the row**, adapting the plan's text (`2026-09-17-release-two-engine.md:1732-1734`) to mark this night void:

> **Three route-proof records are excluded from every comparison denominator,** by the maintainer's choice of §7's first option on 2026-09-17: `records/2026-09-17-route-proof-engine-selfhost-run-record-gate.json` (n = 2), `…-selfhost-docs-linter.json` (n = 2) and `…-selfhost-cell-loop.json` (n = 3), all Engine at the release-two commit, `--purpose route-proof`. **This night is void as a behavioural read: trigger unreachable, Engine defect.** The Engine's self-test could not go green on this repo, so "steer 0 of 4" is not a finding; the cells are read for the two facts that remain (2 of 2 resumes produced a tool call; both docs-linter cells passed inside 32,000 tokens against Baseline's 1 of 6, n = 2, a hint at most). A second route proof is reported beside this one.

- [ ] **Step 2: Commit** with explicit path.

---

### Task 5: Declare the 32,000 stop and decide the Baseline mirror

**Files:**
- Modify: `satyrn-evals/docs/superpowers/specs/2026-09-17-release-two-engine-design.md` (§3 or §7) and `2026-09-15-release-two-r0-constraints.md` if the claim line moves.

**Decision required (maintainer):** the route-proof records are 48,000/72; the Engine's derived contract is 32,000/48 (`DEFAULT_TOKEN_BUDGET`/`DEFAULT_TURN_BUDGET`), so the Engine self-stopped about 32,100 tokens while Baseline ran to 48,000. Matching the claim line (32k/48) is defensible but must be declared, and Baseline must stop at the same line or the arms are not under identical budgets. Options: (a) make the Engine's contract budget follow the record and launch both arms at 32k/48 for the claim; (b) keep 48k/72 and give the Engine a 48k/72 contract. This is a spec change with the reason recorded, per R0 §0.

- [ ] **Step 1: Record the decision and the reason in the design.**
- [ ] **Step 2: If the contract budget must follow the record, file that as its own engine task with its own tests.**
- [ ] **Step 3: Commit.**

---

### Task 6: Widen the redirect to the observed evasion forms

**Files:**
- Modify: `satyrn-engine/packages/engine/runner.ts` (`shellSegments`, `isTestRunCommand`)
- Test: `satyrn-engine/tests/test_runner.mjs` (the `TEST_RUNS` table)
- Fixtures: `satyrn-engine/tests/fixtures/events/` (one per new form)

**Forms seen in the 2026-09-18 transcripts:**
1. A real test run inside a compound with a non-test companion: `uv run pytest -q 2>&1 | grep … | head; echo …; git status --short`.
2. A heredoc Python wrapper: `cat > /tmp/runpt.py <<'PY' … subprocess.run([sys.executable, "-m", "pytest", …]) … PY; uv run python /tmp/runpt.py | tail`.
3. `self_test` invoked through bash.

**Decision required (maintainer/Opus):** widening the whole-command redirect drops the companions' output, which the current design forbids ("the Engine never drops work the model asked for"). The fix is either (a) redirect only the test-run segment and keep the rest, or (b) recognise the specific companions as harmless and accept their loss. Pick one before implementing; add each observed form to `TEST_RUNS` and a `NOT_TEST_RUNS` sibling that must stay untouched.

- [ ] **Step 1: Record the decision.**
- [ ] **Step 2: Add one failing `TEST_RUNS` case per form.**
- [ ] **Step 3: Implement the chosen widening.**
- [ ] **Step 4: Add the replay fixture(s); prove both directions.**
- [ ] **Step 5: Commit.**

---

### Task 7 (attended, out of this plan): re-freeze, re-pin, second route proof

After Tasks 1-6: engine gates green, integration green, `PROVENANCE.md` complete; re-export the frozen engine (root, maintainer's step); re-pin `arms/engine-ornith15-9b.json`; re-issue the three records chained from the latest result; one quiet night. Then read the §7 go criterion on the fixed harness and report the second route proof beside the void one.

## Self-review

- **Spec coverage:** item 1 → Tasks 1-2; item 2 → Task 6; item 3 → Task 5; item 4 → Task 7 (attended); item 5 → Task 4; the preflight self-test → Task 3. Every bullet in the memo maps to a task.
- **Decisions surfaced, not guessed:** Task 5's budget mirror and Task 6's redirect boundary are maintainer decisions; the plan records them rather than choosing.
- **Type consistency:** `derive_contract`, `Contract.preserve`, `RepoFacts`, `run_tests`, `CellPreflight.problems` are the names used throughout.
