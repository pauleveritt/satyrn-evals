"""Bundled task manifests: load, validate, resolve by name."""

import json
import stat
from dataclasses import dataclass
from pathlib import Path

from satyrn_evals.errors import ManifestError

DEFAULT_TASKS_ROOT = Path(__file__).resolve().parent / "tasks"


type Provenance = dict[str, str]


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
    return TaskManifest(
        name=name,
        contract=contract,
        oracle=oracle,
        expected_test_ids=expected,
        source_paths=sources,
        fixtures=fixtures,
        provenance=provenance,
        engine_contract=engine_contract,
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
