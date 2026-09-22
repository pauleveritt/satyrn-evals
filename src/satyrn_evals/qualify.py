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

Two more, for the generator's defects the 2026-09-14 admission cells found:

4. on a task cut by ``tools/cut_task.py`` (its manifest has a ``generator``
   block) the fake attempt also writes ``PROVENANCE.md``, as a model
   following the base's ``AGENTS.md`` does, and still grades pass, with the
   receipt listing the dropped file;
5. the ``R1-plan`` prompt never writes the retired stand-in "its test
   module", and every path its Files lines and ``uv run pytest`` commands
   name is a ``source_paths`` entry, a file in ``base/``, or a directory in
   ``base/`` written with a trailing slash -- so it never names a hidden file.

`judge_fixture`, `judge_harvest` and `judge_prompt` are pure but for
`judge_prompt`'s look at ``base/``; `qualify` runs the grades and the attempt,
so it spawns and belongs to the integration tier.
"""

import json
import os
import re
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
PLAN_RUNG = "R1-plan"
#: Files a self-hosted base's conventions require that its ``base/`` lacks.
#: The generator ignores exactly these (``ignored_paths``) and the fake writes them.
SELF_HOSTED_CONVENTION_FILES: tuple[str, ...] = ("PROVENANCE.md",)
#: The stand-in the generator used for hidden names until 2026-09-15.
RETIRED_STAND_IN = "its test module"
_BACKTICKED = re.compile(r"`([^`\n]+)`")
_PATH_LIKE = re.compile(r"\A[\w.\-/]+\Z")
_FILES_LINE = ("- Create:", "- Modify:", "- Test:")
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
#: The spec's held-out tasks ("Held-out tasks"): cut at batch freeze, qualified offline, never pre-measured.
HELDOUT_TASKS: dict[str, str] = {
    "selfhost-cell-loop": "R1-plan",
    "selfhost-speed-probe": "R1-plan",
}
#: The census set and the rung each task runs at (design section 4). The three
#: maps above name what release one's spec ran and are left as they are: they
#: are cited as evidence of that campaign, and rewriting them would change the
#: record of what was measured, not what will be.
CENSUS_TASKS: dict[str, str] = {
    "agentclinic-repair-depth-3": "R2",
    "selfhost-run-record-gate": PLAN_RUNG,
    "selfhost-docs-linter": PLAN_RUNG,
    "selfhost-cell-loop": PLAN_RUNG,
    "selfhost-speed-probe": PLAN_RUNG,
    "selfhost-preflight-quiet": PLAN_RUNG,
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


def judge_harvest(
    code: AttemptCode,
    verdict: Verdict | None,
    patch_text: str | None,
    known_good: str,
    *,
    extra: tuple[str, ...] = (),
    dropped: tuple[str, ...] = (),
) -> Check:
    """The live harvest: whole (the known-good paths plus ``extra``), graded pass, ``extra`` dropped."""
    want = sorted({*parse_patch_paths(known_good), *extra})
    got = sorted(parse_patch_paths(patch_text)) if patch_text else []
    detail = f"code {code}, verdict {verdict}, paths {got} (want {want}), ignored {sorted(dropped)}"
    passed = code is AttemptCode.OK and verdict is Verdict.PASS and got == want and sorted(dropped) == sorted(extra)
    return Check("live-harvest", passed, detail)


def prompt_paths(prompt: str) -> list[str]:
    """The paths a prompt's Files lines and ``uv run pytest`` commands name, in order."""
    found: list[str] = []
    for line in prompt.splitlines():
        if line.lstrip().startswith(_FILES_LINE):
            found += [token for token in _BACKTICKED.findall(line) if _PATH_LIKE.match(token) and ("/" in token or "." in token)]
    for command in _BACKTICKED.findall(prompt):
        words = command.split()
        if words[:3] != ["uv", "run", "pytest"]:
            continue
        for word in words[3:]:
            if any(mark in word for mark in "<>|;&"):
                break
            if not word.startswith("-"):
                found.append(word)
    return found


def judge_prompt(contracts: dict[str, str], source_paths: tuple[str, ...], base: Path) -> Check:
    """The R1-plan prompt names no stand-in and no path the model cannot find or is not asked to write."""
    prompt = contracts.get(PLAN_RUNG)
    if prompt is None:
        return Check("r1-plan-prompt", True, "no R1-plan rung")
    if RETIRED_STAND_IN in prompt:
        return Check("r1-plan-prompt", False, f"names the retired stand-in {RETIRED_STAND_IN!r}")
    unresolved = [
        path
        for path in prompt_paths(prompt)
        if path not in source_paths
        and not (base / path).is_file()
        and not (path.endswith("/") and (base / path).is_dir())
    ]
    detail = f"unresolved paths {unresolved}" if unresolved else f"{len(prompt_paths(prompt))} paths resolve"
    return Check("r1-plan-prompt", not unresolved, detail)


def judge_prompt_edits(manifest_body: dict) -> Check:
    """Every recorded prompt edit is the one the shipped prompt carries (Ruling 5).

    Pure, and deliberately weaker than ``cut_task.py check``: the plan's history
    is that command's business. The question here is only whether the manifest's
    record of the patch matches the prompt it ships beside, so a reader can
    trust ``generator.prompt_edits`` as provenance without a git checkout.
    """
    generator = manifest_body.get("generator")
    edits = (generator or {}).get("prompt_edits") or []
    if not edits:
        return Check("prompt-edits", True, "no recorded prompt edits")
    prompt = (manifest_body.get("contracts") or {}).get(PLAN_RUNG)
    if not isinstance(prompt, str):
        return Check("prompt-edits", False, f"{len(edits)} recorded edits but no {PLAN_RUNG} prompt")
    problems: list[str] = []
    for index, edit in enumerate(edits, 1):
        if not isinstance(edit, dict) or not all(
            isinstance(edit.get(key), str) and edit.get(key) for key in ("old", "new", "reason")
        ):
            problems.append(f"edit {index} is not {{old, new, reason}} of non-empty strings")
            continue
        if (count := prompt.count(edit["new"])) != 1:
            problems.append(f"edit {index}: its new text occurs {count} times, want 1")
        if edit["old"] in prompt:
            problems.append(f"edit {index}: its old text is still in the prompt")
    detail = "; ".join(problems) if problems else f"{len(edits)} recorded edits are in the prompt"
    return Check("prompt-edits", not problems, detail)


def judge_authored(manifest_body: dict) -> Check:
    """An authored task discloses its spec and its roles (design section 5).

    Pure. A task cut from a historical plan carries no ``authored`` key and
    passes untouched; a task that claims to be authored must say under which
    spec and by which roles, because it is reported beside the cut tasks and
    never pooled with them.
    """
    generator = manifest_body.get("generator")
    if generator is None:
        generator = {}
    if not isinstance(generator, dict):
        return Check("authored-disclosure", False, f"generator must be a dict, got {type(generator).__name__}")
    if "authored" not in generator:
        if "authoring" in generator:
            return Check(
                "authored-disclosure", False, "authoring present without authored: true"
            )
        return Check("authored-disclosure", True, "not an authored task")
    if generator["authored"] is not True:
        return Check("authored-disclosure", False, f"authored is {generator['authored']!r}, want True")
    authoring = generator.get("authoring")
    if not isinstance(authoring, dict) or set(authoring) != {"spec", "roles"}:
        return Check("authored-disclosure", False, "authoring must be {spec, roles}")
    spec, roles = authoring["spec"], authoring["roles"]
    if not isinstance(spec, str) or not spec.strip():
        return Check("authored-disclosure", False, "authoring.spec must be a non-empty path string")
    if not isinstance(roles, dict) or not roles or not all(
        isinstance(key, str) and key.strip() and isinstance(value, str) and value.strip() for key, value in roles.items()
    ):
        return Check("authored-disclosure", False, "authoring.roles must map non-empty strings to non-empty strings")
    return Check("authored-disclosure", True, f"authored under {spec}, {len(roles)} roles")


def convention_files_patch(paths: tuple[str, ...]) -> str:
    """New-file sections for ``paths``, as a model following the base's conventions writes them."""
    return "".join(
        f"diff --git a/{path} b/{path}\nnew file mode 100644\n--- /dev/null\n+++ b/{path}\n@@ -0,0 +1 @@\n+| qualify | row |\n"
        for path in paths
    )


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
        checks.append(judge_prompt(manifest.contracts, manifest.source_paths, task_dir / "base"))
        manifest_body = json.loads((task_dir / "manifest.json").read_text(encoding="utf-8"))
        checks.append(judge_prompt_edits(manifest_body))
        checks.append(judge_authored(manifest_body))
        generated = "generator" in manifest_body
        extra = SELF_HOSTED_CONVENTION_FILES if generated else ()
        harvest = root / "harvest.patch"
        harvest.write_text(convention_files_patch(extra) + good.read_text(encoding="utf-8"), encoding="utf-8")
        with _fake_pi_on_path(root, harvest):
            record = attempt(
                task=manifest.name,
                tasks_root=task_dir.parent,
                output=root / "attempts",
                command=[sys.executable, "-m", "satyrn_evals.attempt_pi", "--model", "omlx/qualify"],
                timeout=600,
            )
        patch = root / "attempts" / record.attempt_dir / "patch.diff" if record.attempt_dir else None
        patch_text = patch.read_text(encoding="utf-8") if patch is not None and patch.is_file() else None
        receipt = root / "attempts" / record.attempt_dir / "receipt.json" if record.attempt_dir else None
        dropped = tuple(json.loads(receipt.read_text(encoding="utf-8")).get("ignored_paths", [])) if receipt is not None and receipt.is_file() else ()
        checks.append(
            judge_harvest(record.code, record.verdict, patch_text, good.read_text(encoding="utf-8"), extra=extra, dropped=dropped)
        )
        return checks
    finally:
        shutil.rmtree(root, ignore_errors=True)
