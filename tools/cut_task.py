#!/usr/bin/env python3
"""Cut a self-hosted task from this repository's own history, deterministically.

A task is ``(BASE, GOOD, files, HIDDEN, plan-anchor)``, written down once as a
spec file under ``tools/task_specs/`` (spec, "The self-hosted generator"):

- ``base/`` is ``git archive BASE`` minus plans, specs, ``.claude``,
  ``.github``, ``PROVENANCE.md`` and the HIDDEN files, plus a ``.gitignore``
  line for each runtime residue pattern BASE does not already ignore;
- ``overlay/`` holds HIDDEN at GOOD, flattened to each file's basename (the
  layout the headroom probe's tasks graded with, 635c12b);
- ``fixtures/known-good.patch`` is GOOD's diff restricted to ``files``;
  ``fixtures/known-broken.patch`` replaces the spec's ``broken`` files with
  their stub text (a stub that imports and does nothing, or a no-op edit);
- ``manifest.json`` carries the provenance shas, the task-tree digest (every
  file beside the manifest) and the digest of the ``R1-plan`` prompt;
- ``prompt_edits`` in the spec are applied to the cut prompt in order, each
  ``old`` required exactly once, and recorded in the manifest's ``generator``
  block; the plan document is never edited.

The R1-plan prompt is the plan task's title, Files, Interfaces minus its
Consumes lines, and the prose of every step with fenced code removed, plus
the literal message formats the hidden suite asserts (the spec's ``formats``
text). A HIDDEN path is written as its directory (``tests/test_x.py`` becomes
``tests/``) and a bare HIDDEN basename as "a test module under tests/": a
contract that names a grader-only path is refused at load, and the prompt
must still name a directory the model can put its own tests in.

The manifest's ``ignored_paths`` is ``PROVENANCE.md``: ``base/`` drops it but
keeps ``AGENTS.md``, which requires a row per file, so grading drops a
patch's ``PROVENANCE.md`` instead of refusing the verdict. Qualification's
fake attempt writes the same files (``SELF_HOSTED_CONVENTION_FILES``).

The expected test ids are the hidden suite collected at GOOD by this
interpreter's pytest, with the spec's ``oracle_env`` applied.

    uv run python tools/cut_task.py cut tools/task_specs/selfhost-review-script.json
    uv run python tools/cut_task.py check tools/task_specs/selfhost-review-script.json

``check`` cuts again into a temporary directory and exits 1 if the task tree
differs from the committed one. No model and no network; git and pytest run
as subprocesses.
"""

import argparse
import difflib
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from satyrn_evals.attempt import contract_digest
from satyrn_evals.qualify import SELF_HOSTED_CONVENTION_FILES
from satyrn_evals.task_tree import tree_digest

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TASKS_ROOT = ROOT / "src" / "satyrn_evals" / "tasks"
RUNG = "R1-plan"
REPO_URL = "https://github.com/pauleveritt/satyrn-evals.git"
EXCLUDED_PREFIXES = ("docs/superpowers/plans/", "docs/superpowers/specs/", ".claude/", ".github/")
EXCLUDED_FILES = frozenset({"PROVENANCE.md"})
IGNORED_PATHS = SELF_HOSTED_CONVENTION_FILES
RESIDUE_IGNORES = (".pytest_cache/", "__pycache__/", ".ruff_cache/", ".venv/")
ORACLE = ("python", "-m", "pytest", "-p", "satyrn_evals.oracle_hook")
PUBLIC_SUITE = ("uv", "run", "pytest", "-q")
_SHA = re.compile(r"\A[0-9a-f]{40}\Z")
_SPEC_KEYS = frozenset({"name", "base", "good", "files", "hidden", "plan", "formats", "broken", "oracle_env"})
#: Optional in a spec, so every already-cut task re-cuts byte-identically
#: (a required key would move every task tree's digest).
_OPTIONAL_SPEC_KEYS = frozenset({"prompt_edits"})
_EDIT_KEYS = frozenset({"old", "new", "reason"})


class CutError(Exception):
    """The spec is malformed or the history does not hold what it names."""


@dataclass(frozen=True, slots=True)
class PlanAnchor:
    path: str
    heading: str
    commit: str | None


@dataclass(frozen=True, slots=True)
class PromptEdit:
    """One recorded patch to the cut prompt (design section 4).

    The plan document is never edited; the prompt's provenance is the
    historical plan plus this named patch, recorded in the manifest.
    """

    old: str
    new: str
    reason: str


@dataclass(frozen=True, slots=True)
class TaskSpec:
    name: str
    base: str
    good: str
    files: tuple[str, ...]
    hidden: tuple[str, ...]
    plan: PlanAnchor
    formats: str
    broken: dict[str, str]
    oracle_env: dict[str, str]
    prompt_edits: tuple[PromptEdit, ...] = ()


def _strings(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value or not all(isinstance(v, str) and v for v in value):
        raise CutError(f"{field} must be a non-empty list of strings")
    return tuple(value)


def load_spec(path: Path) -> TaskSpec:
    """Read and validate one spec file; every key is required, no other key is allowed."""
    try:
        body = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CutError(f"spec {path}: {error}") from error
    if not isinstance(body, dict) or not (_SPEC_KEYS <= set(body) <= _SPEC_KEYS | _OPTIONAL_SPEC_KEYS):
        raise CutError(
            f"spec {path}: keys must be exactly {sorted(_SPEC_KEYS)}, optionally with {sorted(_OPTIONAL_SPEC_KEYS)}"
        )
    for field in ("base", "good"):
        if not isinstance(body[field], str) or not _SHA.match(body[field]):
            raise CutError(f"spec {path}: {field} must be a full 40-hex commit")
    plan = body["plan"]
    if (
        not isinstance(plan, dict)
        or set(plan) != {"path", "heading", "commit"}
        or not all(isinstance(plan[k], str) and plan[k] for k in ("path", "heading"))
        or not (plan["commit"] is None or (isinstance(plan["commit"], str) and _SHA.match(plan["commit"])))
    ):
        raise CutError(f"spec {path}: plan must be {{path, heading, commit (40-hex or null)}}")
    for field in ("broken", "oracle_env"):
        value = body[field]
        if not isinstance(value, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in value.items()):
            raise CutError(f"spec {path}: {field} must map strings to strings")
    if not body["broken"]:
        raise CutError(f"spec {path}: broken must name at least one file")
    if any(not text.endswith("\n") for text in body["broken"].values()):
        raise CutError(f"spec {path}: every broken stub must end with a newline")
    if not isinstance(body["formats"], str):
        raise CutError(f"spec {path}: formats must be a string (empty when the suite asserts none)")
    hidden = _strings(body["hidden"], "hidden")
    if any("/" not in h for h in hidden):
        raise CutError(f"spec {path}: every hidden file must sit under a directory (the prompt names the directory)")
    if len({Path(h).name for h in hidden}) != len(hidden):
        raise CutError(f"spec {path}: hidden basenames must be distinct (the overlay is flattened)")
    raw_edits = body.get("prompt_edits", [])
    if not isinstance(raw_edits, list):
        raise CutError(f"spec {path}: prompt_edits must be a list of {{old, new, reason}}")
    edits: list[PromptEdit] = []
    for index, item in enumerate(raw_edits, 1):
        if not isinstance(item, dict) or set(item) != _EDIT_KEYS:
            raise CutError(f"spec {path}: prompt_edits[{index}] must have exactly {sorted(_EDIT_KEYS)}")
        if not all(isinstance(item[key], str) and item[key] for key in _EDIT_KEYS):
            raise CutError(f"spec {path}: prompt_edits[{index}] fields must be non-empty strings")
        if item["old"] in item["new"]:
            raise CutError(
                f"spec {path}: prompt_edits[{index}] new text must not contain its own old text "
                "(qualification asks whether the old text is gone from the prompt)"
            )
        edits.append(PromptEdit(item["old"], item["new"], item["reason"]))
    return TaskSpec(
        name=body["name"],
        base=body["base"],
        good=body["good"],
        files=_strings(body["files"], "files"),
        hidden=hidden,
        plan=PlanAnchor(plan["path"], plan["heading"], plan["commit"]),
        formats=body["formats"],
        broken=dict(body["broken"]),
        oracle_env=dict(body["oracle_env"]),
        prompt_edits=tuple(edits),
    )


def excluded(path: str, hidden: Iterable[str]) -> bool:
    """Whether a BASE path stays out of ``base/``."""
    return path in EXCLUDED_FILES or path in set(hidden) or path.startswith(EXCLUDED_PREFIXES)


def residue_gitignore(existing: str | None) -> str | None:
    """The ``.gitignore`` text with every residue pattern, or None when BASE's already has them."""
    lines = [] if existing is None else existing.splitlines()
    missing = [pattern for pattern in RESIDUE_IGNORES if pattern not in {line.strip() for line in lines}]
    if not missing:
        return None
    prefix = "" if existing is None or existing.endswith("\n") or not existing else "\n"
    return (existing or "") + prefix + "".join(f"{pattern}\n" for pattern in missing)


def plan_section(plan_text: str, heading: str) -> str:
    """The lines from ``heading`` up to the next ``##``/``###`` heading or ``---`` rule."""
    lines = plan_text.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == heading)
    except StopIteration:
        raise CutError(f"plan has no heading {heading!r}") from None
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].startswith(("## ", "### ")) or lines[index].strip() == "---":
            end = index
            break
    return "\n".join(lines[start:end])


def r1_plan_prompt(section: str, hidden: Sequence[str], formats: str) -> str:
    """The R1-plan rung: title, Files, Interfaces → Produces, step prose, message formats."""
    kept: list[str] = []
    in_fence = False
    for line in section.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or line.lstrip().startswith("- Consumes:"):
            continue
        text = line.removeprefix("### ").replace("- [ ] ", "").replace("**", "")
        if kept and not text.strip() and not kept[-1].strip():
            continue
        kept.append(text.rstrip())
    prompt = "\n".join(kept).strip()
    if formats.strip():
        prompt += "\n\nMessage formats the acceptance suite asserts, match them exactly: " + formats.strip()
    for path in sorted(hidden, key=len, reverse=True):
        prompt = prompt.replace(path, hidden_directory(path))
    for path in hidden:
        prompt = prompt.replace(Path(path).name, f"a test module under {hidden_directory(path)}")
    return prompt + "\n"


def hidden_directory(path: str) -> str:
    """The directory a HIDDEN path is written as, with a trailing slash (``tests/``)."""
    return f"{Path(path).parent.as_posix()}/"


def apply_prompt_edits(prompt: str, edits: Sequence[PromptEdit]) -> str:
    """Apply each edit in order; each ``old`` must occur exactly once when its turn comes.

    Order matters and is part of the record: a later edit may anchor on text an
    earlier one introduced, which is why the count is checked against the text
    as it stands rather than against the original.
    """
    text = prompt
    for index, edit in enumerate(edits, 1):
        count = text.count(edit.old)
        if count != 1:
            raise CutError(f"prompt edit {index}: its old text occurs {count} times in the prompt, want 1")
        text = text.replace(edit.old, edit.new, 1)
    return text


def broken_patch(base_texts: Mapping[str, str | None], broken: Mapping[str, str]) -> str:
    """A git-style patch replacing each broken file with its stub (new file when absent at BASE)."""
    chunks: list[str] = []
    for path in sorted(broken):
        old, new = base_texts.get(path), broken[path]
        if old == new:
            raise CutError(f"broken stub for {path} is identical to BASE")
        header = f"diff --git a/{path} b/{path}\n"
        if old is None:
            new_lines = new.splitlines(keepends=True)
            body = f"new file mode 100644\n--- /dev/null\n+++ b/{path}\n@@ -0,0 +1,{len(new_lines)} @@\n"
            chunks.append(header + body + "".join(f"+{line}" for line in new_lines))
        else:
            diff = difflib.unified_diff(
                old.splitlines(keepends=True), new.splitlines(keepends=True), f"a/{path}", f"b/{path}"
            )
            chunks.append(header + "".join(diff))
    return "".join(chunks)


def manifest_body(
    spec: TaskSpec, prompt: str, expected_test_ids: Sequence[str], task_tree: str
) -> dict[str, object]:
    """The manifest a cut task carries, in the bundled tasks' shape."""
    oracle = [*(["env", *(f"{k}={v}" for k, v in sorted(spec.oracle_env.items()))] if spec.oracle_env else []), *ORACLE]
    generator: dict[str, object] = {
        "tool": "tools/cut_task.py",
        "rung": RUNG,
        "files": list(spec.files),
        "hidden": list(spec.hidden),
        "plan": {"path": spec.plan.path, "heading": spec.plan.heading, "commit": spec.plan.commit},
    }
    if spec.prompt_edits:
        generator["prompt_edits"] = [
            {"old": edit.old, "new": edit.new, "reason": edit.reason} for edit in spec.prompt_edits
        ]
    return {
        "name": spec.name,
        "contract": prompt,
        "contracts": {RUNG: prompt},
        "oracle": oracle,
        "expected_test_ids": list(expected_test_ids),
        "source_paths": [*spec.files, "tests"],
        "ignored_paths": list(IGNORED_PATHS),
        "public_suite": list(PUBLIC_SUITE),
        "fixtures": {"known_good": "fixtures/known-good.patch", "known_broken": "fixtures/known-broken.patch"},
        "grader_overlay": "overlay",
        "oracle_visibility": "hidden",
        "provenance": {"repo": REPO_URL, "base_sha": spec.base, "fix_sha": spec.good},
        "generator": generator,
        "digests": {"task_tree": task_tree, "prompt": contract_digest(prompt)},
    }


def parse_collected(stdout: str) -> list[str]:
    """Test ids from ``pytest --collect-only -q`` output, in collection order."""
    ids: list[str] = []
    for line in stdout.splitlines():
        if not line.strip():
            break
        if "::" in line:
            ids.append(line.strip())
    if not ids:
        raise CutError(f"pytest collected no tests:\n{stdout}")
    return ids


# --- git and pytest ---------------------------------------------------------


def _git(repo: Path, *args: str) -> bytes:
    completed = subprocess.run(["git", "-C", os.fspath(repo), *args], capture_output=True, check=False)
    if completed.returncode != 0:
        raise CutError(f"git {' '.join(args)} failed: {os.fsdecode(completed.stderr).strip()}")
    return completed.stdout


def show(repo: Path, commit: str, path: str) -> str | None:
    """The text of ``path`` at ``commit``, or None when it does not exist there."""
    probe = subprocess.run(
        ["git", "-C", os.fspath(repo), "cat-file", "-e", f"{commit}:{path}"], capture_output=True, check=False
    )
    return None if probe.returncode != 0 else _git(repo, "show", f"{commit}:{path}").decode("utf-8")


def archive(repo: Path, commit: str, dest: Path, keep: Iterable[str] | None = None) -> None:
    """Extract ``git archive commit`` into ``dest``, keeping only paths ``keep`` holds (all when None)."""
    wanted = None if keep is None else set(keep)
    with tarfile.open(fileobj=io.BytesIO(_git(repo, "archive", "--format=tar", commit))) as tar:
        members = [m for m in tar.getmembers() if not m.isdir() and (wanted is None or m.name in wanted)]
        tar.extractall(dest, members=members, filter="data")


def collect_ids(repo: Path, spec: TaskSpec) -> list[str]:
    """The hidden suite's test ids, collected at GOOD with the overlay flattened to the root."""
    with tempfile.TemporaryDirectory(prefix="satyrn-cut-") as scratch:
        root = Path(scratch)
        archive(repo, spec.good, root)
        for hidden in spec.hidden:
            (root / Path(hidden).name).write_bytes((root / hidden).read_bytes())
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider",
             *(Path(h).name for h in spec.hidden)],
            cwd=root, capture_output=True, text=True, check=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", **spec.oracle_env},
        )
        if completed.returncode != 0:
            raise CutError(f"collecting the hidden suite at {spec.good} failed:\n{completed.stdout}{completed.stderr}")
        return parse_collected(completed.stdout)


def read_plan(repo: Path, anchor: PlanAnchor) -> str:
    if anchor.commit is None:
        return (repo / anchor.path).read_text(encoding="utf-8")
    text = show(repo, anchor.commit, anchor.path)
    if text is None:
        raise CutError(f"plan {anchor.path} is absent at {anchor.commit}")
    return text


def cut(spec: TaskSpec, repo: Path, tasks_root: Path) -> Path:
    """Write ``tasks_root/<name>``; refuse to overwrite an existing task."""
    dest = tasks_root / spec.name
    if dest.exists():
        raise CutError(f"{dest} exists; remove it deliberately to cut again")
    listing = _git(repo, "ls-tree", "-r", "--name-only", "-z", spec.base).decode("utf-8").split("\0")
    base_paths = [path for path in listing if path and not excluded(path, spec.hidden)]
    (dest / "base").mkdir(parents=True)
    archive(repo, spec.base, dest / "base", keep=base_paths)
    gitignore = dest / "base" / ".gitignore"
    if (text := residue_gitignore(gitignore.read_text() if gitignore.exists() else None)) is not None:
        gitignore.write_text(text)
    (dest / "overlay").mkdir()
    for hidden in spec.hidden:
        if (body := show(repo, spec.good, hidden)) is None:
            raise CutError(f"hidden file {hidden} is absent at {spec.good}")
        (dest / "overlay" / Path(hidden).name).write_text(body)
    (dest / "fixtures").mkdir()
    (dest / "fixtures" / "known-good.patch").write_bytes(
        _git(repo, "diff", "--full-index", "--binary", spec.base, spec.good, "--", *spec.files)
    )
    (dest / "fixtures" / "known-broken.patch").write_text(
        broken_patch({path: show(repo, spec.base, path) for path in spec.broken}, spec.broken)
    )
    prompt = apply_prompt_edits(
        r1_plan_prompt(plan_section(read_plan(repo, spec.plan), spec.plan.heading), spec.hidden, spec.formats),
        spec.prompt_edits,
    )
    body = manifest_body(spec, prompt, collect_ids(repo, spec), tree_digest(dest, exclude={"manifest.json"}))
    (dest / "manifest.json").write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n")
    return dest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cut_task.py")
    parser.add_argument("action", choices=("cut", "check"))
    parser.add_argument("specs", nargs="+", type=Path)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--tasks-root", type=Path, default=DEFAULT_TASKS_ROOT)
    args = parser.parse_args(argv)
    try:
        for spec_path in args.specs:
            spec = load_spec(spec_path)
            if args.action == "cut":
                print(cut(spec, args.repo, args.tasks_root))
                continue
            with tempfile.TemporaryDirectory(prefix="satyrn-cut-check-") as scratch:
                fresh = tree_digest(cut(spec, args.repo, Path(scratch)))
            committed = args.tasks_root / spec.name
            if not committed.is_dir() or tree_digest(committed) != fresh:
                print(f"cut_task: {spec.name} differs from a fresh cut", file=sys.stderr)
                return 1
            print(f"cut_task: {spec.name} matches a fresh cut")
    except CutError as error:
        print(f"cut_task: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
