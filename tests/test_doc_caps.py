from pathlib import Path

from tools.lint_docs import check


def _docs(tmp_path: Path) -> Path:
    for d in ("docs/superpowers/specs", "docs/superpowers/plans", "docs/results", "docs/reviews"):
        (tmp_path / d).mkdir(parents=True)
    (tmp_path / "ROADMAP.md").write_text("# Roadmap\n")
    return tmp_path


def test_a_clean_tree_has_no_failures(tmp_path: Path) -> None:
    assert check(_docs(tmp_path)) == []


def test_roadmap_over_150_lines_fails(tmp_path: Path) -> None:
    root = _docs(tmp_path)
    (root / "ROADMAP.md").write_text("x\n" * 151)
    assert check(root) == ["ROADMAP.md: 151 lines > 150"]


def test_result_over_120_lines_fails(tmp_path: Path) -> None:
    root = _docs(tmp_path)
    (root / "docs/results/r.md").write_text("```\nx\n```\n" + "y\n" * 118)
    assert check(root) == ["docs/results/r.md: 121 lines > 120"]


def test_result_without_a_fenced_recompute_block_fails(tmp_path: Path) -> None:
    root = _docs(tmp_path)
    (root / "docs/results/r.md").write_text("# r\n\nno command here\n")
    assert check(root) == ["docs/results/r.md: no fenced recompute block"]


def test_result_with_a_fence_and_under_cap_passes(tmp_path: Path) -> None:
    root = _docs(tmp_path)
    (root / "docs/results/r.md").write_text("# r\n\n```bash\nuv run x\n```\n")
    assert check(root) == []


def test_thirteen_results_fail(tmp_path: Path) -> None:
    root = _docs(tmp_path)
    for i in range(13):
        (root / f"docs/results/r{i}.md").write_text("```\nx\n```\n")
    assert "docs/results: 13 result files > 12" in check(root)


def test_a_spec_over_400_lines_fails_and_a_long_plan_does_not(tmp_path: Path) -> None:
    root = _docs(tmp_path)
    (root / "docs/superpowers/specs/s.md").write_text("x\n" * 401)
    (root / "docs/superpowers/plans/p.md").write_text("x\n" * 900)
    assert check(root) == ["docs/superpowers/specs/s.md: 401 lines > 400"]


def test_an_unlisted_directory_under_docs_fails(tmp_path: Path) -> None:
    root = _docs(tmp_path)
    (root / "docs/current").mkdir()
    assert check(root) == ["docs/current: directory not permitted under docs/"]


def test_trailing_whitespace_and_blank_last_line_fail(tmp_path: Path) -> None:
    root = _docs(tmp_path)
    (root / "docs/lessons.md").write_text("a \nb\n\n")
    assert check(root) == ["docs/lessons.md:1: trailing whitespace", "docs/lessons.md: blank line at EOF"]


def test_the_skip_list_is_relative_to_root_not_absolute(tmp_path: Path) -> None:
    root = _docs(tmp_path / ".claude" / "worktrees" / "x")
    (root / "docs/lessons.md").write_text("a \n")
    assert check(root) == ["docs/lessons.md:1: trailing whitespace"]


def test_gitkeep_does_not_count_toward_the_result_cap(tmp_path: Path) -> None:
    root = _docs(tmp_path)
    (root / "docs/results/.gitkeep").write_text("")
    for i in range(12):
        (root / f"docs/results/r{i}.md").write_text("```\nx\n```\n")
    assert check(root) == []


def test_roadmap_at_exactly_150_lines_passes(tmp_path: Path) -> None:
    root = _docs(tmp_path)
    (root / "ROADMAP.md").write_text("x\n" * 150)
    assert check(root) == []


def test_result_at_exactly_120_lines_passes(tmp_path: Path) -> None:
    root = _docs(tmp_path)
    (root / "docs/results/r.md").write_text("```\nx\n```\n" + "y\n" * 117)
    assert check(root) == []


def test_spec_at_exactly_400_lines_passes(tmp_path: Path) -> None:
    root = _docs(tmp_path)
    (root / "docs/superpowers/specs/s.md").write_text("x\n" * 400)
    assert check(root) == []


def test_twelve_results_passes(tmp_path: Path) -> None:
    root = _docs(tmp_path)
    for i in range(12):
        (root / f"docs/results/r{i}.md").write_text("```\nx\n```\n")
    assert check(root) == []


def test_site_page_trailing_whitespace_fails(tmp_path: Path) -> None:
    root = _docs(tmp_path)
    (root / "site").mkdir()
    (root / "site" / "index.md").write_text("a \nb\n")
    assert check(root) == ["site/index.md:1: trailing whitespace"]


def test_site_page_blank_last_line_fails(tmp_path: Path) -> None:
    root = _docs(tmp_path)
    (root / "site").mkdir()
    (root / "site" / "index.md").write_text("a\n\n")
    assert check(root) == ["site/index.md: blank line at EOF"]


def test_a_clean_site_page_passes(tmp_path: Path) -> None:
    root = _docs(tmp_path)
    (root / "site").mkdir()
    (root / "site" / "index.md").write_text("a\n")
    assert check(root) == []
