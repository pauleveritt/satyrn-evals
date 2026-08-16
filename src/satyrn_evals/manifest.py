"""Bundled task manifests: load, validate, resolve by name."""

import json
from dataclasses import dataclass
from pathlib import Path

from satyrn_evals.errors import ManifestError

DEFAULT_TASKS_ROOT = Path(__file__).resolve().parent / "tasks"


@dataclass(frozen=True)
class TaskManifest:
    name: str
    contract: str
    oracle: tuple[str, ...]
    expected_test_ids: tuple[str, ...]
    source_paths: tuple[str, ...]
    fixtures: dict[str, str]


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
    try:
        name = data["name"]
        contract = data["contract"]
        oracle = tuple(data["oracle"])
        expected = tuple(data["expected_test_ids"])
        sources = tuple(data["source_paths"])
        fixtures = dict(data["fixtures"])
    except KeyError as e:
        raise ManifestError(f"manifest missing key: {e.args[0]}") from e
    except TypeError as e:
        raise ManifestError(f"manifest field has the wrong type: {e}") from e
    if not isinstance(name, str) or not name or not isinstance(contract, str) or not contract:
        raise ManifestError("name and contract must be non-empty strings")
    if not oracle or not all(isinstance(x, str) and x for x in oracle):
        raise ManifestError("oracle must be a non-empty list of command strings")
    if not expected or not all(isinstance(x, str) for x in expected):
        raise ManifestError("expected_test_ids must be a non-empty list of strings")
    if not sources or not all(isinstance(x, str) for x in sources):
        raise ManifestError("source_paths must be a non-empty list of strings")
    for key in ("known_good", "known_broken"):
        if not isinstance(fixtures.get(key), str) or not fixtures[key]:
            raise ManifestError(f"fixtures.{key} must be a non-empty path string")
    if not (task_dir / "base").is_dir():
        raise ManifestError(f"task base directory missing: {task_dir / 'base'}")
    for key in ("known_good", "known_broken"):
        if not (task_dir / fixtures[key]).is_file():
            raise ManifestError(f"fixture file missing: {fixtures[key]}")
    return TaskManifest(
        name=name,
        contract=contract,
        oracle=oracle,
        expected_test_ids=expected,
        source_paths=sources,
        fixtures=fixtures,
    )


def resolve_task(name: str, tasks_root: Path = DEFAULT_TASKS_ROOT) -> Path:
    if Path(name).name != name or "/" in name or "\\" in name:
        raise ManifestError(f"invalid task name: {name}")
    task_dir = tasks_root / name
    if not task_dir.is_dir():
        raise ManifestError(f"unknown task: {name}")
    return task_dir
