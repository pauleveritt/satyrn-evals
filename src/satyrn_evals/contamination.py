"""Contamination detection: grader content in executor-reachable material.

Pure functions — no I/O, no subprocess. Matching is verbatim only: a
tripwire for the copying that actually happened, explicitly NOT a proof
of ignorance. A paraphrased leak passes every check here, and the single
idiomatic line of an honest test must never fire (2026-09-04 V7 spec §3).

Import note: OverlaySpec is imported under TYPE_CHECKING only. overlay.py
imports the absence predicate from this module at runtime; a module-level
import in both directions would be a cycle.
"""

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from satyrn_evals.overlay import OverlaySpec

GRADER_BLOCK_LINES = 4

type ContaminationCheck = Literal[
    "overlay_in_workspace", "grader_content_in_patch", "grader_name_in_payload"
]
type ContaminationOutcome = Literal["flagged", "clean", "unmeasured"]


@dataclass(frozen=True, slots=True)
class Evidence:
    kind: str  # "whole_file" | "block" | "path"
    overlay_path: str
    in_path: str  # patch file rel path, or "<step>/<event kind>" source name
    line: int | None  # 1-based into the `in_path` artifact; None for payload blobs


def evidence_dict(evidence: Evidence) -> dict[str, object]:
    """The serialized evidence shape the spec pins (V7 spec §7).

    The artifact an evidence item points into is keyed ``in`` (a reserved
    word in Python, so the dataclass field is ``in_path`` and the wire
    shape renames it) — receipts and session records carry ``in``.
    """
    return {
        "kind": evidence.kind,
        "overlay_path": evidence.overlay_path,
        "in": evidence.in_path,
        "line": evidence.line,
    }


@dataclass(frozen=True, slots=True)
class CheckResult:
    check: ContaminationCheck
    outcome: ContaminationOutcome
    evidence: tuple[Evidence, ...]


def _nonblank(text: str) -> tuple[tuple[int, str], ...]:
    """(1-based raw line number, raw line) for every non-blank line.

    Matching is verbatim on raw lines: no whitespace, case, or encoding
    normalization (2026-09-04 V7 spec §3). `line.strip()` is the blank
    test only; the stored text stays raw so a re-indented copy does not
    match.
    """
    return tuple(
        (number, line)
        for number, line in enumerate(text.splitlines(), start=1)
        if line.strip()
    )


def _added_files(patch_text: str) -> dict[str, str]:
    """Unified-diff added lines per target path (`+++ b/<path>` sections)."""
    added: dict[str, str] = {}
    current: str | None = None
    buffer: list[str] = []
    for line in patch_text.splitlines():
        if line.startswith("+++ "):
            if current is not None:
                added[current] = "\n".join(buffer)
            current = line[4:].removeprefix("b/").split("\t")[0]
            buffer = []
        elif line.startswith("+") and not line.startswith("+++"):
            buffer.append(line[1:])
    if current is not None:
        added[current] = "\n".join(buffer)
    return added


def _match_block(
    overlay_seq: tuple[tuple[int, str], ...],
    patch_seq: tuple[tuple[int, str], ...],
) -> tuple[str, int] | None:
    """First verbatim window hit: (evidence kind, 1-based patch line)."""
    window = min(GRADER_BLOCK_LINES, len(overlay_seq))
    if window == 0 or len(patch_seq) < window:
        return None
    kind = "whole_file" if window == len(overlay_seq) else "block"
    overlay_texts = [text for _, text in overlay_seq]
    patch_texts = [text for _, text in patch_seq]
    for start in range(len(overlay_texts) - window + 1):
        needle = overlay_texts[start : start + window]
        for pos in range(len(patch_texts) - window + 1):
            if patch_texts[pos : pos + window] == needle:
                return kind, patch_seq[pos][0]
    return None


def scan_patch(patch_text: str | None, spec: OverlaySpec) -> CheckResult:
    """Check (b): grader content inside a retained patch."""
    if patch_text is None:
        return CheckResult("grader_content_in_patch", "unmeasured", ())
    evidence: list[Evidence] = []
    added = _added_files(patch_text)
    for overlay_path, text in spec.texts.items():
        overlay_seq = _nonblank(text)
        for patch_path, patch_body in added.items():
            if (hit := _match_block(overlay_seq, _nonblank(patch_body))) is not None:
                kind, line = hit
                evidence.append(Evidence(kind, overlay_path, patch_path, line))
    return CheckResult(
        "grader_content_in_patch", "flagged" if evidence else "clean", tuple(evidence)
    )


def scan_texts(
    sources: Sequence[tuple[str, str | None]], spec: OverlaySpec
) -> CheckResult:
    """Check (c): overlay paths inside executor-visible texts (spec §4).

    Scans the overlay-root-relative rel paths only (``tests/t_hidden.py``).
    Suffix containment does the rest of the work for free: any longer
    mention — task-relative (``grader/overlay/tests/t_hidden.py``) or an
    absolute machine path — contains the rel path as a substring, so
    detection power is unchanged and no machine-specific absolute form is
    ever a candidate.

    This is deliberately NOT the same candidate set the authoring-time
    check (``manifest._overlay_declared_names``) enumerates. Authored
    texts are matched exactly and can stop at ``grader/overlay`` (the bare
    overlay root) with no file name, so that check separately lists the
    root plus the task-rooted forms. Detected payload blobs are matched
    only for the exact rel suffix, so no ``must agree`` invariant binds
    the two scans.

    Every present, text-bearing source is scanned; a source list with no
    text at all means the check could not run: `unmeasured`.
    """
    evidence: list[Evidence] = []
    measured = False
    for name, text in sources:
        if text is None:
            continue
        measured = True
        for overlay_path in spec.rel_paths:
            if overlay_path in text:
                evidence.append(Evidence("path", overlay_path, name, None))
    if not measured:
        return CheckResult("grader_name_in_payload", "unmeasured", ())
    return CheckResult(
        "grader_name_in_payload", "flagged" if evidence else "clean", tuple(evidence)
    )


def payload_strings(payload: Mapping[str, object]) -> Iterator[str]:
    """Every string value in a retained event payload, depth-first."""
    if isinstance(payload, str):
        yield payload
    elif isinstance(payload, Mapping):
        for value in payload.values():
            yield from payload_strings(value)  # type: ignore[arg-type]
    elif isinstance(payload, list | tuple):
        for value in payload:
            yield from payload_strings(value)  # type: ignore[arg-type]


def overlay_absent_from_inventory(
    inventory: Mapping[str, str], spec: OverlaySpec
) -> bool:
    """Check (a) as a pure predicate: rel-path OR content-digest hit.

    A hit is the authoring defect the builder assertion exists to catch
    (base must never contain grader content) — refusal is correct, not a
    false positive.
    """
    overlay_digests = frozenset(spec.digests.values())
    return not any(
        rel in spec.rel_paths or digest in overlay_digests
        for rel, digest in inventory.items()
    )


def overall(results: Sequence[CheckResult]) -> ContaminationOutcome:
    """Precedence: flagged > unmeasured > clean; requires >= one check."""
    if not results:
        raise ValueError("overall requires at least one check result")
    outcomes = {result.outcome for result in results}
    match outcomes:
        case outcome if "flagged" in outcome:
            return "flagged"
        case outcome if "unmeasured" in outcome:
            return "unmeasured"
        case _:
            return "clean"
