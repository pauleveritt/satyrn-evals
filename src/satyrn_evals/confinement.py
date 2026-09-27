"""The confinement audit: did a cell reach the material that grades it?

Pure -- no I/O, no subprocess. The shipped Pi extension
(``packages/confinement/confinement.ts``) refuses an in-worktree escape while
the cell runs; this reads the transcript afterwards and reports every
file-tool path or bash path token that reached the corpus root, a task
directory, a hidden grader filename or a fixture. A deciding cell is admitted
only when this is clean and the extension recorded no refusal (design C3).

The claim it supports is "no observed access", never "no possible access": the
screen is lexical, and a paraphrase or an indirect read is not excluded
(design C4, the same limit ``contamination.py`` declares).
"""

import posixpath
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from satyrn_evals.cell_evidence import _events, _segments

#: The shared Pi extension both arms load (design C1). The Baseline adapter puts
#: it on Pi's argv; the harness names it in :data:`EXTENSION_ENV` so the Engine
#: arm's own Pi spawn loads it too.
EXTENSION_PATH = Path(__file__).resolve().parents[2] / "packages" / "confinement" / "confinement.ts"
#: Environment the harness exports to a cell: the extension to load, the
#: worktree the model is confined to, and the roots it must not reach.
EXTENSION_ENV = "SATYRN_EXTRA_EXTENSIONS"
ROOT_ENV = "SATYRN_CONFINEMENT_ROOT"
ROOTS_ENV = "SATYRN_CONFINEMENT_ROOTS"
#: The condition's stated limit (design C4), carried into every summary. The
#: extension refuses at call time and the audit reports what the transcript
#: shows; neither is a proof that the model could not have reached grader
#: material, so a result page must never read as one.
CONFINEMENT_LIMIT = (
    "confinement reports observed access only: the shared extension refused the calls "
    "listed here, and the audit found no reach to grader material in the transcript. "
    "It is not proof the model could not have reached it (design C4)."
)


@dataclass(frozen=True, slots=True)
class Protected:
    """The absolute roots and grader filenames a cell must not reach."""

    roots: tuple[str, ...]
    names: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Reach:
    """One call that reached protected material."""

    kind: str  # "file_tool" | "bash"
    source: str  # the file-tool path or the bash command
    protected: str  # the root or filename it reached
    index: int  # the 0-based transcript event index


def protected(tasks_root: Path, task: str | None = None) -> Protected:
    """The tasks root (and, when named, one task directory) and every grader
    filename beneath them.

    The roots are the whole-tree paths a cell must leave the worktree to read.
    The names are the two things that grade or answer a task: the hidden
    ``overlay/`` files and the ``fixtures/*.patch`` that hold known-good and
    known-broken. Only the files' basenames travel, so no content is copied
    into the terms.
    """
    task_dirs = (
        [tasks_root / task]
        if task is not None
        else sorted(path for path in tasks_root.iterdir() if path.is_dir())
    )
    roots = [str(tasks_root.resolve())]
    names: list[str] = []
    for task_dir in task_dirs:
        roots.append(str(task_dir.resolve()))
        for sub, glob in (("overlay", "*"), ("fixtures", "*.patch")):
            directory = task_dir / sub
            if directory.is_dir():
                names += [entry.name for entry in directory.glob(glob) if entry.is_file()]
    return Protected(tuple(dict.fromkeys(roots)), tuple(dict.fromkeys(names)))


def _under(candidate: str, roots: Sequence[str]) -> str | None:
    resolved = PurePosixPath(posixpath.normpath(candidate))
    for root in roots:
        pure = PurePosixPath(posixpath.normpath(root))
        if resolved == pure or resolved.is_relative_to(pure):
            return root
    return None


def _resolve(cwd: str | None, path: str) -> str | None:
    if posixpath.isabs(path):
        return posixpath.normpath(path)
    return None if cwd is None else posixpath.normpath(posixpath.join(cwd, path))


def _reaches(path: str, cwd: str | None, protected_: Protected) -> str | None:
    """The protected term a path reaches, or None: a named grader file first,
    then a resolved path under a protected root."""
    if posixpath.basename(posixpath.normpath(path)) in protected_.names:
        return posixpath.basename(posixpath.normpath(path))
    resolved = _resolve(cwd, path)
    return None if resolved is None else _under(resolved, protected_.roots)


def _candidate_tokens(words: Sequence[str]) -> list[str]:
    """Every word in a bash segment that could name a path, relative or absolute.

    ``cell_evidence._path_tokens`` keeps only absolute, ``~`` and ``$HOME``
    tokens, because it answers "outside the worktree" -- from inside, a
    relative path is not outside. The audit must also see a relative traversal
    (``cat ../../<corpus>/.../test_hidden.py``), so it hands every word to
    :func:`_reaches`, which resolves a relative token against the transcript's
    cwd and checks the basename first. The ``--opt=value`` form is unwrapped;
    a bare assignment or flag is harmless because it only matches a protected
    basename when it literally spells one."""
    tokens: list[str] = []
    for word in words:
        value = word.split("=", 1)[1] if word.startswith("-") and "=" in word else word
        if value:
            tokens.append(value)
    return tokens


def audit(transcript: str, *, protected_: Protected) -> tuple[Reach, ...]:
    """Every file-tool path and bash path token that reached protected material."""
    events = _events(transcript)
    cwd = events[0].get("cwd") if events and isinstance(events[0].get("cwd"), str) else None
    reached: list[Reach] = []
    for index, event in enumerate(events):
        if event.get("type") != "tool_execution_start":
            continue
        tool, args = event.get("toolName"), event.get("args")
        if not isinstance(args, dict):
            continue
        if tool in ("read", "edit", "write") and isinstance(args.get("path"), str):
            path = args["path"]
            if (term := _reaches(path, cwd, protected_)) is not None:
                reached.append(Reach("file_tool", path, term, index))
        elif tool == "bash" and isinstance(args.get("command"), str):
            command = args["command"]
            for segment in _segments(command):
                for token in _candidate_tokens(segment):
                    if (term := _reaches(token, cwd, protected_)) is not None:
                        reached.append(Reach("bash", command, term, index))
                        break
                else:
                    continue
                break
    return tuple(reached)
