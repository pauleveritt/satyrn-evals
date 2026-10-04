"""replay_ops: delete-only interpretation, both directions."""

from pathlib import Path

import pytest

from satyrn_evals.replay_ops import Delete, apply, interpret_bash

CWD = "/tmp/wt"


def paths(command: str, cwd: str | None = CWD) -> list[str]:
    return [op.path for op in interpret_bash(command, cwd).ops]


def test_heredoc_remainder_rm_is_delete():
    cmd = "cat > ./x <<'EOF'\nrm -rf nothing\nEOF\nuv run thing --check ./x; rm -f ./x"
    got = interpret_bash(cmd, CWD)
    assert got.ops == (Delete("x", False),)
    assert not any("nothing" in s for s in got.skipped)  # heredoc body is never a command


def test_wt_quoted_rm_rf():
    got = interpret_bash('rm -rf "$WT/private"', CWD)
    assert got.ops == (Delete("private", True),)


@pytest.mark.parametrize(
    "command,expected",
    [
        ("rm a b", ["a", "b"]),
        ("rm -fr ./a/b", ["a/b"]),
        ("cd /tmp/wt && rm -r -f $WT/x", ["x"]),
        ("rm $(pwd)/y", ["y"]),
        ("rm /tmp/wt/z", ["z"]),
        ("rm -f a; rm -f b || rm -f c\nrm d", ["a", "b", "c", "d"]),
    ],
)
def test_literal_in_tree_forms(command: str, expected: list[str]):
    assert paths(command) == expected


@pytest.mark.parametrize(
    "command",
    [
        "rm -rf /tmp/x",
        "rm -rf ~",
        "rm $VAR",
        "rm *.json",
        "rm ../escape",
        "rm -rf .",
        "rm -rf $WT",
        "rm -rf a /tmp/x",
        "rm -z a",
        "mv a b",
        "mkdir -p d",
        "echo hi > f",
        "sed -i s/a/b/ f",
        "ruff format .",
        "git add -A",
        "python3 -c \"open('f','w').write('x')\"",
    ],
)
def test_refused_yields_no_op_and_skipped(command: str):
    got = interpret_bash(command, CWD)
    assert got.ops == ()
    assert got.skipped


def test_absolute_path_refused_without_cwd():
    assert paths("rm /tmp/wt/x", None) == []
    assert paths("rm x", None) == ["x"]


def test_apply_removes_stray_file_and_dir(tmp_path: Path):
    (tmp_path / "x").write_text("1")
    (tmp_path / "d" / "e").mkdir(parents=True)
    (tmp_path / "d" / "e" / "f").write_text("1")
    removed = apply((Delete("x"), Delete("d", True)), tmp_path)
    assert removed == (tmp_path.resolve() / "x", tmp_path.resolve() / "d")
    assert not (tmp_path / "x").exists() and not (tmp_path / "d").exists()


def test_apply_plain_rm_leaves_directory(tmp_path: Path):
    (tmp_path / "d").mkdir()
    assert apply((Delete("d", False),), tmp_path) == ()
    assert (tmp_path / "d").is_dir()


def test_apply_never_touches_outside(tmp_path: Path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("keep")
    (root / "link").symlink_to(tmp_path)
    assert apply((Delete("../outside.txt"), Delete(str(outside)), Delete("link/outside.txt")), root) == ()
    assert outside.read_text() == "keep"


def test_apply_missing_is_noop(tmp_path: Path):
    assert apply((Delete("nope"), Delete("a/b", True)), tmp_path) == ()


def test_apply_unlinks_symlink_without_following(tmp_path: Path):
    root = tmp_path / "root"
    root.mkdir()
    target = tmp_path / "t"
    target.mkdir()
    (target / "keep").write_text("1")
    (root / "link").symlink_to(target)
    assert len(apply((Delete("link", True),), root)) == 1
    assert (target / "keep").exists() and not (root / "link").is_symlink()
