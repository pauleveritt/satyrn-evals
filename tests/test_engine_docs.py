import json
from pathlib import Path

from tools.engine_sync import MANIFEST_NAME, check_manifest, engine_pin, load_arm

ROOT = Path(__file__).resolve().parents[1]
ARM = ROOT / "arms" / "engine-ornith15-9b.json"
ENGINE_DIR = ROOT / "_engine"
#: `shasum -a 256 _engine/README.md`, computed outside the code under test.
README_SHA256 = "56fcca41f648ce0fd730b00baf2fade8ed05f6cda569bf51b809b7c32a708097"


def test_the_manifest_commit_matches_the_engine_arms_pin() -> None:
    commit = engine_pin(load_arm(ARM))
    manifest = json.loads((ENGINE_DIR / MANIFEST_NAME).read_text())
    assert manifest["engine_commit"] == commit


def test_the_committed_copy_matches_its_manifest() -> None:
    commit = engine_pin(load_arm(ARM))
    assert check_manifest(ENGINE_DIR, commit) == []


def test_the_manifest_pins_the_readme_known_answer() -> None:
    manifest = json.loads((ENGINE_DIR / MANIFEST_NAME).read_text())
    assert manifest["files"]["README.md"]["sha256"] == README_SHA256


def test_the_manifest_names_the_engine_repository() -> None:
    manifest = json.loads((ENGINE_DIR / MANIFEST_NAME).read_text())
    assert manifest["source_repository"] == "https://github.com/pauleveritt/satyrn-engine.git"
