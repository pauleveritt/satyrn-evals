"""Bundled task manifests: load, validate, resolve by name."""

import json
import stat
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from satyrn_evals.errors import ManifestError

DEFAULT_TASKS_ROOT = Path(__file__).resolve().parent / "tasks"


type Provenance = dict[str, str]
type OracleVisibility = Literal["visible", "hidden"]
# The rung ladder: an OPEN map from rung key to the contract text that rung
# exports. Production code carries no enum of rung names (V11a spec §3), so
# R0 and R2 arrive by authoring a key, never by a code change.
type ContractRungs = dict[str, str]


@dataclass(frozen=True)
class TaskManifest:
    name: str
    contract: str
    oracle: tuple[str, ...]
    expected_test_ids: tuple[str, ...]
    source_paths: tuple[str, ...]
    fixtures: dict[str, str]
    provenance: Provenance | None = None
    engine_contract: str | None = None
    grader_overlay: str | None = None
    oracle_visibility: OracleVisibility = "visible"
    contracts: ContractRungs = field(default_factory=dict)


def _validate_grader_overlay(task_dir: Path, value: object) -> str | None:
    """Validate the grader-only overlay directory path without reading files."""
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ManifestError("grader_overlay must be a non-empty relative path string")
    parts = value.split("/")
    if value.startswith("/") or "\\" in value or "\0" in value or any(
        part in ("", ".", "..") for part in parts
    ):
        raise ManifestError("grader_overlay must be a safe relative POSIX path")
    cursor = task_dir
    for index, part in enumerate(parts):
        cursor /= part
        try:
            mode = cursor.lstat().st_mode
        except FileNotFoundError as exc:
            raise ManifestError(f"grader_overlay directory missing: {value}") from exc
        except OSError as exc:
            raise ManifestError(f"cannot inspect grader overlay {value}: {exc}") from exc
        if stat.S_ISLNK(mode):
            raise ManifestError("grader_overlay must not contain symbolic links")
        if index == len(parts) - 1 and not stat.S_ISDIR(mode):
            raise ManifestError("grader_overlay must name a directory")
        if index != len(parts) - 1 and not stat.S_ISDIR(mode):
            raise ManifestError("grader_overlay parent must be a directory")
    return value


def _validate_engine_contract(task_dir: Path, value: object) -> str | None:
    """Validate an opaque Engine contract's path without reading its bytes."""
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ManifestError("engine_contract must be a non-empty relative path string")
    parts = value.split("/")
    if value.startswith("/") or "\\" in value or "\0" in value or any(
        part in ("", ".", "..") for part in parts
    ):
        raise ManifestError("engine_contract must be a safe relative POSIX path")
    cursor = task_dir
    for index, part in enumerate(parts):
        cursor /= part
        try:
            mode = cursor.lstat().st_mode
        except FileNotFoundError as exc:
            raise ManifestError(f"engine contract file missing: {value}") from exc
        except OSError as exc:
            raise ManifestError(f"cannot inspect engine contract {value}: {exc}") from exc
        if stat.S_ISLNK(mode):
            raise ManifestError("engine_contract must not contain symbolic links")
        final = index == len(parts) - 1
        if final and not stat.S_ISREG(mode):
            raise ManifestError("engine_contract must name a regular file")
        if not final and not stat.S_ISDIR(mode):
            raise ManifestError("engine_contract parent must be a directory")
    return value


def _overlay_declared_names(task_dir: Path, overlay_root: str) -> tuple[str, ...]:
    """Authoring-time names whose appearance in authored text leaks a hidden oracle.

    Authored text is matched exactly, so the bare overlay root
    (``grader/overlay``) plus every task-rooted form is enumerated here —
    a mention can stop at the root with no file name attached. This is
    intentionally NOT the same candidate set contamination.scan_texts
    scans (overlay-root-relative rel paths only): the detector's payload
    blobs are matched by rel-suffix containment, not exact authoring text.
    """
    names = [overlay_root]
    root = task_dir / overlay_root
    for path in sorted(root.rglob("*")):
        if path.is_file():
            rel = path.relative_to(root).as_posix()
            names.append(rel)
            names.append(f"{overlay_root}/{rel}")
    return tuple(names)


def _validate_contracts(value: object) -> ContractRungs:
    """Validate the optional rung map generically: {rung key: contract text}.

    Open by construction (V11a spec §3): no rung name is enumerated here, so
    an unknown key such as ``R7`` loads. Absent means the task has no rungs.

    A JSON object cannot carry a non-string key, so the key type check is
    only reachable from a programmatic caller; it is exercised directly by
    ``test_contracts_non_string_key_refused_by_the_validator``.
    """
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ManifestError("contracts must be an object mapping rung key to text")
    for key, text in value.items():
        if not isinstance(key, str) or not key.strip():
            raise ManifestError("contracts keys must be non-empty rung strings")
        if not isinstance(text, str) or not text.strip():
            raise ManifestError(f"contracts[{key!r}] must be a non-empty string")
    return dict(value)


def _authored_texts(
    contract: str, contracts: ContractRungs
) -> Iterator[tuple[str, str]]:
    """Every model-visible authored text, each with the label that names it.

    The default ``contract`` plus every rung value. V11a spec §3: this is the
    one check the trim makes *wider*, and it is not optional.
    """
    yield "contract", contract
    for rung, text in contracts.items():
        yield f"contracts[{rung!r}]", text


def _assert_contract_names_no_overlay(
    task_dir: Path,
    contract: str,
    overlay_root: str | None,
    contracts: ContractRungs,
) -> None:
    """Refuse a hidden task whose contract or any rung names a grader-only path.

    Limitation: this is an exact, case-sensitive substring match; a paraphrase
    passes. The check walks the declared overlay root with plain ``Path.rglob``
    (no overlay loading) once, and compares each candidate name against the
    default contract and every rung text. The raised message names the text it
    refused, so an R1 authoring mistake is attributable.
    """
    if overlay_root is None:
        return
    names = _overlay_declared_names(task_dir, overlay_root)
    for label, text in _authored_texts(contract, contracts):
        for name in names:
            if name in text:
                raise ManifestError(
                    f"{label} names grader-only path: {name} "
                    "(hidden oracle; the docstring limit is: a paraphrase passes)"
                )


def load_manifest(task_dir: Path) -> TaskManifest:
    path = task_dir / "manifest.json"
    try:
        data = json.loads(path.read_text())
    except OSError as e:
        raise ManifestError(f"cannot read manifest: {e}") from e
    except json.JSONDecodeError as e:
        raise ManifestError(f"malformed manifest JSON: {e}") from e
    if not isinstance(data, dict):
        raise ManifestError("manifest is not a JSON object")
    for key in ("name", "contract", "oracle", "expected_test_ids", "source_paths", "fixtures"):
        if key not in data:
            raise ManifestError(f"manifest missing key: {key}")
    name = data["name"]
    contract = data["contract"]
    if not isinstance(data["oracle"], list):
        raise ManifestError("oracle must be a list of command strings")
    if not isinstance(data["expected_test_ids"], list):
        raise ManifestError("expected_test_ids must be a list of strings")
    if not isinstance(data["source_paths"], list):
        raise ManifestError("source_paths must be a list of strings")
    if not isinstance(data["fixtures"], dict):
        raise ManifestError("fixtures must be an object")
    oracle = tuple(data["oracle"])
    expected = tuple(data["expected_test_ids"])
    sources = tuple(data["source_paths"])
    fixtures = dict(data["fixtures"])
    if not isinstance(name, str) or not name or not isinstance(contract, str) or not contract:
        raise ManifestError("name and contract must be non-empty strings")
    if not oracle or not all(isinstance(x, str) and x for x in oracle):
        raise ManifestError("oracle must be a non-empty list of command strings")
    if not expected or not all(isinstance(x, str) for x in expected):
        raise ManifestError("expected_test_ids must be a non-empty list of strings")
    if not sources or not all(isinstance(x, str) for x in sources):
        raise ManifestError("source_paths must be a non-empty list of strings")
    for key in ("known_good",):
        if not isinstance(fixtures.get(key), str) or not fixtures[key]:
            raise ManifestError(f"fixtures.{key} must be a non-empty path string")
    if "known_broken" in fixtures:
        broken = fixtures["known_broken"]
        if not isinstance(broken, str) or not broken:
            raise ManifestError("fixtures.known_broken must be a non-empty path string")
    provenance = data.get("provenance")
    if provenance is not None:
        if not isinstance(provenance, dict):
            raise ManifestError("provenance must be an object")
        if set(provenance) != {"repo", "base_sha", "fix_sha"}:
            raise ManifestError("provenance must have exactly repo, base_sha, fix_sha")
        if not all(
            isinstance(provenance[k], str) and provenance[k]
            for k in ("repo", "base_sha", "fix_sha")
        ):
            raise ManifestError("provenance fields must be non-empty strings")
    if not (task_dir / "base").is_dir():
        raise ManifestError(f"task base directory missing: {task_dir / 'base'}")
    for key in ("known_good", "known_broken"):
        if key not in fixtures:
            continue
        if not (task_dir / fixtures[key]).is_file():
            raise ManifestError(f"fixture file missing: {fixtures[key]}")
    engine_contract = _validate_engine_contract(task_dir, data.get("engine_contract"))
    grader_overlay = _validate_grader_overlay(task_dir, data.get("grader_overlay"))
    visibility_raw = data.get("oracle_visibility", "visible")
    if visibility_raw not in ("visible", "hidden"):
        raise ManifestError(
            f"oracle_visibility must be 'visible' or 'hidden', got {visibility_raw!r}"
        )
    visibility: OracleVisibility = visibility_raw
    # grader_overlay was resolved earlier via _validate_grader_overlay into the
    # local `grader_overlay`; match against that resolved value (the ⇔ rule).
    match (visibility, grader_overlay):
        case ("hidden", None):
            raise ManifestError("hidden oracle requires grader_overlay")
        case ("visible", str()):
            raise ManifestError("grader_overlay requires a hidden oracle")
        case _:
            pass
    contracts = _validate_contracts(data.get("contracts"))
    _assert_contract_names_no_overlay(task_dir, contract, grader_overlay, contracts)
    return TaskManifest(
        name=name,
        contract=contract,
        oracle=oracle,
        expected_test_ids=expected,
        source_paths=sources,
        fixtures=fixtures,
        provenance=provenance,
        engine_contract=engine_contract,
        grader_overlay=grader_overlay,
        oracle_visibility=visibility,
        contracts=contracts,
    )


def is_valid_task_name(name: str) -> bool:
    return Path(name).name == name and "/" not in name and "\\" not in name and name not in ("", ".", "..")


def resolve_task(name: str, tasks_root: Path = DEFAULT_TASKS_ROOT) -> Path:
    if not is_valid_task_name(name):
        raise ManifestError(f"invalid task name: {name}")
    task_dir = tasks_root / name
    if not task_dir.is_dir():
        raise ManifestError(f"unknown task: {name}")
    return task_dir
