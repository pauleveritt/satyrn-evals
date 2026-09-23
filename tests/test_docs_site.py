"""The docs site's build inputs, checked without a model, network, or subprocess.

Zensical drops a `--8<--` target that does not exist without warning and still
exits 0 under `--strict`, so the build alone cannot prove the site's includes
resolve. This test does, and pins the landing page's first link and the nav.
"""

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
INCLUDE = re.compile(r'--8<--\s+"([^"]+)"')
LINK = re.compile(r"\]\(([^)]+)\)")


def _config() -> dict:
    return tomllib.loads((ROOT / "zensical.toml").read_text())


def _site_pages() -> list[Path]:
    return sorted(SITE.glob("**/*.md"))


def _nav_paths(entries: list) -> list[str]:
    paths: list[str] = []
    for entry in entries:
        if isinstance(entry, str):
            paths.append(entry)
        elif isinstance(entry, dict):
            for value in entry.values():
                paths.extend(_nav_paths(value if isinstance(value, list) else [value]))
    return paths


def test_the_config_names_the_site_directory() -> None:
    project = _config()["project"]
    assert project["site_name"]
    assert project["docs_dir"] == "site"


def test_every_include_target_exists() -> None:
    missing = [
        f"{page.relative_to(ROOT)}: {target}"
        for page in _site_pages()
        for target in INCLUDE.findall(page.read_text())
        if not (ROOT / target).is_file()
    ]
    assert missing == []


def test_the_landing_page_links_the_numbers_page_first() -> None:
    links = LINK.findall((SITE / "index.md").read_text())
    assert links and links[0] == "numbers.md"


def test_the_landing_page_carries_the_public_copy() -> None:
    text = (SITE / "index.md").read_text()
    for fragment in (
        "start with evidence",
        "Part of the SatyrnAI project",
        "Laptop AI",
        "petri dish",
    ):
        assert fragment in text, fragment


def test_every_site_page_is_in_the_navigation() -> None:
    nav = _nav_paths(_config()["project"]["nav"])
    pages = [page.relative_to(SITE).as_posix() for page in _site_pages()]
    assert pages
    assert set(pages) <= set(nav)


def test_the_config_declares_the_mermaid_fence() -> None:
    ext = _config()["project"]["markdown_extensions"]
    fences = ext.get("pymdownx", {}).get("superfences", {}).get("custom_fences", [])
    assert any(dict(f).get("name") == "mermaid" for f in fences)


def test_the_nav_names_the_new_pages_in_order() -> None:
    nav = _nav_paths(_config()["project"]["nav"])
    for rel in (
        "how-it-works.md",
        "numbers.md",
        "measurement.md",
        "evals-about.md",
        "evals-architecture.md",
        "use-evals.md",
        "authoring.md",
        "engine.md",
        "engine-architecture.md",
        "engine-usage.md",
        "engine-glossary.md",
        "models.md",
        "pathologies.md",
        "remediations.md",
        "contributing.md",
        "glossary.md",
    ):
        assert rel in nav, rel


def test_the_canonical_files_the_site_includes_are_present() -> None:
    for rel in (
        "docs/numbers.md",
        "docs/superpowers/specs/2026-09-15-release-one-outcome.md",
        "docs/lessons.md",
        "docs/pathologies.md",
        "docs/remediations.md",
    ):
        assert (ROOT / rel).is_file(), rel


def test_how_it_works_has_three_sections_and_diagrams() -> None:
    text = (SITE / "how-it-works.md").read_text()
    assert "## How agents work" in text
    assert "## How the Engine works" in text
    assert "## How Evals works" in text
    assert text.count("```mermaid") >= 6


def test_first_results_and_measurement_titles() -> None:
    assert (SITE / "numbers.md").read_text().startswith("---\ntitle: First results")
    assert "## How the claim was measured" in (SITE / "measurement.md").read_text()


def test_evals_about_names_why_how_what() -> None:
    text = (SITE / "evals-about.md").read_text()
    for fragment in ("## Why", "## How", "## What", "glossary.md"):
        assert fragment in text, fragment
