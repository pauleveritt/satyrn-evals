import json
import re
from pathlib import Path

from tools.engine_sync import MANIFEST_NAME, RENDERED_DIR

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
INCLUDE = re.compile(r'--8<--\s+"([^"]+)"')
PAGE_INCLUDES = {
    "engine.md": f"_engine/{RENDERED_DIR}/README.md",
    "engine-usage.md": f"_engine/{RENDERED_DIR}/usage.md",
    "engine-glossary.md": f"_engine/{RENDERED_DIR}/glossary.md",
}


def _manifest() -> dict:
    return json.loads((ROOT / "_engine" / MANIFEST_NAME).read_text())


def test_every_engine_include_is_in_the_manifest() -> None:
    named = {f"_engine/{RENDERED_DIR}/{dest}" for dest in _manifest()["files"]}
    targets = {
        target
        for page in SITE.glob("**/*.md")
        for target in INCLUDE.findall(page.read_text())
        if target.startswith("_engine/")
    }
    assert targets == named


def test_each_engine_page_includes_its_own_document() -> None:
    for name, target in PAGE_INCLUDES.items():
        targets = INCLUDE.findall((SITE / name).read_text())
        assert target in targets, f"{name} should include {target}"


def test_engine_pages_banner_names_the_manifest_commit() -> None:
    commit = _manifest()["engine_commit"]
    pages = sorted(SITE.glob("engine*.md"))
    assert pages
    for page in pages:
        assert commit in page.read_text(), page
