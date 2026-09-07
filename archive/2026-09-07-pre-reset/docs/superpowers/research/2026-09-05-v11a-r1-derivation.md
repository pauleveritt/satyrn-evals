> **Archived pre-reset record (2026-09-07).**
>
> Original claims, decisions, and instructions may be superseded. This file is evidence, not current guidance.
> For current guidance, read root AGENTS.md, BRIEF.md, and ROADMAP.md. Retrieve one named record when it bears on a concrete question; do not preload this archive.

# V11a-trim: the six R1 rows, re-derived from this repository's own bases

**Derived 2026-09-05, on this worktree, by running each task's hidden
overlay against that task's own `base/`.** Nothing here is copied from the
existing R3 `contract` text and nothing is from recall (BRIEF rule 7, plan
Task 8).

## The command that recomputes every row

The derivation script mirrors
`tests/integration/test_agentclinic_gate.py::_run_base_with_hook`: it copies
each task's `base/` to a temporary tree, drops the task's own hidden overlay
file beside it, materializes the copy's **own** locked environment
(`uv sync --locked`), and runs the oracle with the result hook.

```bash
uv run python - <<'PY' > r1-derivation.json
# the script is reproduced verbatim below
PY
```

The script is `tools/derive_r1.py`-shaped but was run from a scratch path;
its exact body is:

```python
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
import satyrn_evals
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT

STATES = ["depth-2", "depth-3", "framing-2", "framing-2-edit",
          "misleading-locus", "plausible-wrong-fix"]

def derive(state, workdir):
    task_dir = DEFAULT_TASKS_ROOT / f"agentclinic-repair-{state}"
    tree = workdir / state
    shutil.copytree(task_dir / "base", tree)
    shutil.copy(task_dir / "overlay" / "test_acceptance.py",
                tree / "test_acceptance.py")
    subprocess.run(["uv", "sync", "--locked"], cwd=tree, check=True,
                   capture_output=True)
    hook = workdir / f"hook-{state}.json"
    env = dict(os.environ)
    env["SATYRN_ORACLE_RESULT"] = str(hook)
    env["PYTHONPATH"] = os.fspath(
        Path(satyrn_evals.__file__).resolve().parent.parent)
    env["PATH"] = os.fspath(tree / ".venv" / "bin") + os.pathsep + env["PATH"]
    proc = subprocess.run(
        [os.fspath(tree / ".venv" / "bin" / "python"), "-m", "pytest",
         "-p", "satyrn_evals.oracle_hook", "-q", "--tb=line",
         "-p", "no:cacheprovider", "test_acceptance.py"],
        cwd=tree, env=env, capture_output=True, text=True)
    record = json.loads(hook.read_text())
    return {
        "state": state,
        "hook_counts": record["counts"],
        "failing_function_names": sorted(
            nodeid.split("::", 1)[1]
            for nodeid, outcome in record["outcomes"].items()
            if outcome != "passed"),
        "collect_errors": record["collect_errors"],
        "pytest_stdout": proc.stdout,
    }

with tempfile.TemporaryDirectory() as tmp:
    print(json.dumps([derive(s, Path(tmp)) for s in STATES], indent=2))
```

**Which evidence is authoritative for what.** The failing *set* is read from
the oracle hook's JSON record — never from pytest's stdout and never from an
exit code (BRIEF rule 4). The assertion *text* is read from pytest's
`--tb=line` report; that is authoring evidence for a prompt, not a verdict.

## The six derived rows

| Task | Hook counts | Failing bare function name(s) | Derived assertion text |
|---|---|---|---|
| `depth-2` | 10 passed, 3 failed | `test_home_html_element_declares_english_language`, `test_complaints_board_preserves_the_shared_layout`, `test_post_complaint_redirects_to_complaints_board` | `AttributeError: 'NoneType' object has no attribute 'casefold'` (first two), `assert 307 == 303` (third) |
| `depth-3` | 9 passed, 4 failed | `test_home_html_element_declares_english_language`, `test_complaints_board_preserves_the_shared_layout`, `test_complaint_model_contract_is_preserved`, `test_post_complaint_redirects_to_complaints_board` | `AttributeError: 'NoneType' object has no attribute 'casefold'` (first two), `AssertionError: assert None is not None` (third), `assert 307 == 303` (fourth) |
| `framing-2` | 0 collected — collection abort | none (nothing collected) | `ModuleNotFoundError: No module named 'models'` |
| `framing-2-edit` | 0 collected — collection abort | none (nothing collected) | `AttributeError: module 'models' has no attribute 'complaints'. Did you mean: 'Complaint'?` |
| `misleading-locus` | 12 passed, 1 failed | `test_posted_complaint_appears_on_complaints_board` | `assert 'Codex acceptance test' in '<!DOCTYPE html>…'` (the rendered board HTML) |
| `plausible-wrong-fix` | 12 passed, 1 failed | `test_post_complaint_redirects_to_complaints_board` | `assert 307 == 303` |

These rows agree with the failing sets already pinned by
`tests/integration/test_agentclinic_gate.py::EXPECTED_BASE_FAILURES`, which
is an independent check on the derivation rather than its source.

## What was carried into R1, and what was trimmed

R1 is **task statement + failing bare function names + assertion text**. It
carries **no file name and no fix sentence** — that is the whole difference
between R1 and R3 (spec §1, plan Task 8).

Two deliberate deviations from the raw derived text, recorded rather than
edited away:

1. **The traceback frames are dropped.** The two collection-abort rows'
   full `--tb=line` output names `test_acceptance.py` and `app.py`. Carrying
   them would be refused at manifest load by
   `_assert_contract_names_no_overlay` and would reinstate the file name R1
   exists to withhold. R1 carries the terminal exception line only.
2. **`misleading-locus`'s assertion text is abbreviated.** The raw text
   embeds the entire rendered page. R1 keeps the discriminating half — the
   posted complaint's text is absent from the board's HTML.

`framing-2-edit`'s `Did you mean: 'Complaint'?` **is** kept: it is part of
the interpreter's own exception message, and R3 for that task already says
more (it names the cause *and* what to do).

## Stated limit

The `R1 ≤ R3` relation asserted by the authoring above is a two-point
authoring claim, not a measurement. No run in this phase measures it, and
the rung labels stay unverified authoring claims until V12 (spec §8).
