import json
from pathlib import Path

import pytest

from tools.engine_sync import (
    ENGINE_DOCS,
    RENDERED_DIR,
    TRANSFORM_VERSION,
    EngineSyncError,
    build_manifest,
    check_manifest,
    engine_pin,
    load_arm,
    render_myst,
    sha256,
)

ROOT = Path(__file__).resolve().parents[1]
ARM = ROOT / "arms" / "engine-ornith15-9b.json"


def _fake_engine(root: Path) -> Path:
    (root / "docs").mkdir(parents=True)
    (root / "README.md").write_text("readme\n")
    (root / "docs" / "usage.md").write_text("usage\n")
    (root / "docs" / "glossary.md").write_text("glossary\n")
    return root


def test_engine_pin_reads_the_arms_engine_commit() -> None:
    assert engine_pin(load_arm(ARM)) == "78ab87dbab3381dd585986c43fd49e6e4974f6b6"


def test_engine_pin_refuses_an_arm_without_a_pin() -> None:
    with pytest.raises(EngineSyncError, match="engine_commit"):
        engine_pin({"pins": {}})


def test_engine_pin_refuses_a_pin_that_is_not_a_commit_sha() -> None:
    for pin in ("   ", "abc123", "z" * 40, "a" * 39):
        with pytest.raises(EngineSyncError, match="engine_commit"):
            engine_pin({"pins": {"engine_commit": pin}})


def test_build_manifest_hashes_each_document(tmp_path: Path) -> None:
    manifest = build_manifest(_fake_engine(tmp_path / "engine"), "a" * 40)
    assert set(manifest["files"]) == {"README.md", "usage.md", "glossary.md"}
    assert manifest["files"]["usage.md"]["source"] == "docs/usage.md"
    assert manifest["files"]["usage.md"]["sha256"] == sha256(tmp_path / "engine" / "docs" / "usage.md")
    assert manifest["files"]["usage.md"]["rendered_sha256"]
    assert manifest["transform"] == TRANSFORM_VERSION
    assert manifest["engine_commit"] == "a" * 40


def test_build_manifest_names_a_missing_document(tmp_path: Path) -> None:
    engine = _fake_engine(tmp_path / "engine")
    (engine / "docs" / "glossary.md").unlink()
    with pytest.raises(EngineSyncError, match="glossary.md"):
        build_manifest(engine, "a" * 40)


def _synced(tmp_path: Path) -> Path:
    engine = _fake_engine(tmp_path / "engine")
    manifest = build_manifest(engine, "a" * 40)
    out = tmp_path / "_engine"
    out.mkdir()
    (out / RENDERED_DIR).mkdir()
    for dest, source in ENGINE_DOCS:
        data = (engine / source).read_bytes()
        (out / dest).write_bytes(data)
        (out / RENDERED_DIR / dest).write_bytes(render_myst(data.decode()).encode())
    (out / "manifest.json").write_text(json.dumps(manifest))
    return out


def test_check_manifest_is_clean_on_a_matching_copy(tmp_path: Path) -> None:
    assert check_manifest(_synced(tmp_path), "a" * 40) == []


def test_check_manifest_names_a_changed_file(tmp_path: Path) -> None:
    out = _synced(tmp_path)
    (out / "usage.md").write_text("tampered\n")
    assert any("usage.md" in problem for problem in check_manifest(out, "a" * 40))


def test_check_manifest_names_a_missing_file(tmp_path: Path) -> None:
    out = _synced(tmp_path)
    (out / "glossary.md").unlink()
    assert any("glossary.md" in problem for problem in check_manifest(out, "a" * 40))


def test_check_manifest_names_a_commit_mismatch(tmp_path: Path) -> None:
    out = _synced(tmp_path)
    assert any("engine_commit" in problem for problem in check_manifest(out, "b" * 40))


def test_check_manifest_names_a_missing_manifest(tmp_path: Path) -> None:
    out = tmp_path / "_engine"
    out.mkdir()
    problems = check_manifest(out, "a" * 40)
    assert len(problems) == 1
    assert "manifest" in problems[0]


def test_check_manifest_names_a_wrong_file_set(tmp_path: Path) -> None:
    out = _synced(tmp_path)
    manifest = json.loads((out / "manifest.json").read_text())
    manifest["files"]["extra.md"] = manifest["files"].pop("usage.md")
    (out / "manifest.json").write_text(json.dumps(manifest))
    problems = check_manifest(out, "a" * 40)
    assert len(problems) == 1
    assert "extra.md" in problems[0]
    assert "usage.md" in problems[0]


def test_check_manifest_names_a_wrong_source_and_still_checks_the_digest(tmp_path: Path) -> None:
    out = _synced(tmp_path)
    manifest = json.loads((out / "manifest.json").read_text())
    manifest["files"]["usage.md"]["source"] = "docs/elsewhere.md"
    (out / "manifest.json").write_text(json.dumps(manifest))
    (out / "usage.md").write_text("tampered\n")
    problems = check_manifest(out, "a" * 40)
    assert any("source" in problem for problem in problems)
    assert any("digest" in problem for problem in problems)


def test_check_manifest_names_corrupt_json(tmp_path: Path) -> None:
    out = tmp_path / "_engine"
    out.mkdir()
    (out / "manifest.json").write_text("{not json")
    problems = check_manifest(out, "a" * 40)
    assert len(problems) == 1
    assert "JSON" in problems[0]


def test_check_manifest_names_a_non_object_manifest(tmp_path: Path) -> None:
    out = tmp_path / "_engine"
    out.mkdir()
    (out / "manifest.json").write_text(json.dumps(["not", "an", "object"]))
    problems = check_manifest(out, "a" * 40)
    assert len(problems) == 1
    assert "object" in problems[0]


def test_check_manifest_names_a_changed_rendered_file(tmp_path: Path) -> None:
    out = _synced(tmp_path)
    (out / RENDERED_DIR / "usage.md").write_text("tampered\n")
    assert any("rendered" in problem for problem in check_manifest(out, "a" * 40))


def test_check_manifest_names_a_missing_rendered_file(tmp_path: Path) -> None:
    out = _synced(tmp_path)
    (out / RENDERED_DIR / "glossary.md").unlink()
    assert any("rendered" in problem for problem in check_manifest(out, "a" * 40))


def test_check_manifest_names_a_wrong_transform(tmp_path: Path) -> None:
    out = _synced(tmp_path)
    manifest = json.loads((out / "manifest.json").read_text())
    manifest["transform"] = "some-other-transform"
    (out / "manifest.json").write_text(json.dumps(manifest))
    assert any("transform" in problem for problem in check_manifest(out, "a" * 40))


def test_render_myst_strips_term_roles() -> None:
    assert render_myst("the {term}`engine` runs\n") == "the engine runs\n"


def test_render_myst_strips_doc_roles() -> None:
    assert render_myst("see {doc}`usage` for more\n") == "see usage for more\n"


def test_render_myst_turns_rst_literals_into_code_spans() -> None:
    assert render_myst("run ``/implement`` now\n") == "run `/implement` now\n"


def test_render_myst_leaves_triple_backtick_fences_alone() -> None:
    source = "```console\n$ run ``literal``\n```\n"
    assert render_myst(source) == source


def test_render_myst_leaves_ordinary_prose_and_tables_alone() -> None:
    source = "| a | b |\n|---|---|\n| 1 | 2 |\n\nplain text\n"
    assert render_myst(source) == source


def test_render_myst_renders_a_glossary_block() -> None:
    source = (
        "```{glossary}\n"
        "alpha\n"
        "  The first ``letter`` in the {term}`alphabet`.\n"
        "\n"
        "beta\n"
        "  The second.\n"
        "```\n"
    )
    assert render_myst(source) == (
        "**alpha**\n"
        "\n"
        "The first `letter` in the alphabet.\n"
        "\n"
        "**beta**\n"
        "\n"
        "The second.\n"
    )


def test_the_committed_rendered_copy_is_the_transform_of_the_committed_source() -> None:
    for dest, _ in ENGINE_DOCS:
        source = (ROOT / "_engine" / dest).read_text()
        rendered = (ROOT / "_engine" / RENDERED_DIR / dest).read_text()
        assert render_myst(source) == rendered
