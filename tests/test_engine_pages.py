import json
import re
from pathlib import Path

from tools.engine_sync import MANIFEST_NAME

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
INCLUDE = re.compile(r'--8<--\s+"([^"]+)"')


def _manifest() -> dict:
    return json.loads((ROOT / "_engine" / MANIFEST_NAME).read_text())


def test_every_engine_include_is_in_the_manifest() -> None:
    named = {f"_engine/{dest}" for dest in _manifest()["files"]}
    targets = {
        target
        for page in SITE.glob("**/*.md")
        for target in INCLUDE.findall(page.read_text())
        if target.startswith("_engine/")
    }
    assert targets == named


def test_engine_pages_banner_names_the_manifest_commit() -> None:
    commit = _manifest()["engine_commit"]
    pages = sorted(SITE.glob("engine*.md"))
    assert pages
    for page in pages:
        assert commit in page.read_text(), page
