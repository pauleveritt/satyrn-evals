"""The pre-registered post-hoc read's four pure predicates, each on a synthetic
patch that satisfies it and a sibling that violates it, plus undetermined cases.

Default tier: no model, no network, no subprocess -- every patch here is a
literal string, never read from disk or built with git.
"""

import importlib.util
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent.parent
_MODULE_PATH = _HERE / "evidence" / "2026-09-18-census-3" / "postreg_read.py"
_spec = importlib.util.spec_from_file_location("postreg_read", _MODULE_PATH)
postreg_read = importlib.util.module_from_spec(_spec)
sys.modules["postreg_read"] = postreg_read
_spec.loader.exec_module(postreg_read)

Verdict = postreg_read.Verdict
maxsplit = postreg_read.maxsplit
one_decimal = postreg_read.one_decimal
inputs_keys = postreg_read.inputs_keys
cli_last = postreg_read.cli_last
read_cell = postreg_read.read_cell
COLUMNS = postreg_read.COLUMNS


def _patch(body: str) -> str:
    """A minimal cumulative-patch text adding `scripts/preflight_quiet.py`
    with `body` as its (already `+`-prefixed) added lines."""
    header = (
        "diff --git a/scripts/preflight_quiet.py b/scripts/preflight_quiet.py\n"
        "new file mode 100644\n"
        "index 0000000..1111111\n"
        "--- /dev/null\n"
        "+++ b/scripts/preflight_quiet.py\n"
    )
    return header + body


# ---------------------------------------------------------------------------
# maxsplit


def test_maxsplit_satisfied_on_a_bounded_split() -> None:
    patch = _patch(
        "+def busy_processes(lines):\n"
        "+    out = []\n"
        "+    for line in lines:\n"
        "+        pid, pcpu, comm = line.split(maxsplit=2)\n"
        "+        out.append((pid, pcpu, comm))\n"
        "+    return out\n"
    )
    assert maxsplit(patch) == Verdict.SATISFIED


def test_maxsplit_not_satisfied_on_a_bare_split() -> None:
    patch = _patch(
        "+def busy_processes(lines):\n"
        "+    out = []\n"
        "+    for line in lines:\n"
        "+        pid, pcpu, comm = line.split()\n"
        "+        out.append((pid, pcpu, comm))\n"
        "+    return out\n"
    )
    assert maxsplit(patch) == Verdict.NOT_SATISFIED


def test_maxsplit_undetermined_when_the_function_is_absent() -> None:
    patch = _patch("+def other():\n+    return 1\n")
    assert maxsplit(patch) == Verdict.UNDETERMINED


def test_maxsplit_undetermined_when_the_file_is_not_touched() -> None:
    patch = (
        "diff --git a/scripts/other.py b/scripts/other.py\n"
        "new file mode 100644\n"
        "index 0000000..1111111\n"
        "--- /dev/null\n"
        "+++ b/scripts/other.py\n"
        "+x = 1\n"
    )
    assert maxsplit(patch) == Verdict.UNDETERMINED


# ---------------------------------------------------------------------------
# one_decimal


def test_one_decimal_satisfied_when_both_messages_use_one_decimal_place() -> None:
    patch = _patch(
        '+    msg1 = f"load {one_minute:.1f} > {ceiling * cores:.1f} ({cores} cores)"\n'
        '+    msg2 = f"decode {rate:.1f} tok/s < {floor} over last {n} completions"\n'
    )
    assert one_decimal(patch) == Verdict.SATISFIED


def test_one_decimal_not_satisfied_when_a_message_uses_a_bare_format() -> None:
    patch = _patch(
        '+    msg1 = f"load {one_minute} > {ceiling * cores} ({cores} cores)"\n'
        '+    msg2 = f"decode {rate:.1f} tok/s < {floor} over last {n} completions"\n'
    )
    assert one_decimal(patch) == Verdict.NOT_SATISFIED


def test_one_decimal_undetermined_when_a_message_line_is_absent() -> None:
    patch = _patch('+    msg1 = f"load {one_minute:.1f} > {ceiling * cores:.1f} ({cores} cores)"\n')
    assert one_decimal(patch) == Verdict.UNDETERMINED


# ---------------------------------------------------------------------------
# inputs_keys


def test_inputs_keys_satisfied_on_exactly_the_specified_set() -> None:
    patch = _patch(
        "+    return {\n"
        '+        "inputs": {\n'
        '+            "load": self.load,\n'
        '+            "busy": self.busy,\n'
        '+            "decode": self.decode,\n'
        '+            "floor_tok_s": self.floor_tok_s,\n'
        '+            "model": self.model,\n'
        '+            "last": self.last,\n'
        "+        },\n"
        "+    }\n"
    )
    assert inputs_keys(patch) == Verdict.SATISFIED


def test_inputs_keys_not_satisfied_with_an_extra_key() -> None:
    patch = _patch(
        "+    return {\n"
        '+        "inputs": {\n'
        '+            "load": self.load,\n'
        '+            "busy": self.busy,\n'
        '+            "decode": self.decode,\n'
        '+            "floor_tok_s": self.floor_tok_s,\n'
        '+            "model": self.model,\n'
        '+            "last": self.last,\n'
        '+            "extra": self.extra,\n'
        "+        },\n"
        "+    }\n"
    )
    assert inputs_keys(patch) == Verdict.NOT_SATISFIED


def test_inputs_keys_undetermined_when_inputs_is_absent() -> None:
    patch = _patch("+    return {\n" '+        "outputs": {},\n' "+    }\n")
    assert inputs_keys(patch) == Verdict.UNDETERMINED


# ---------------------------------------------------------------------------
# cli_last


def test_cli_last_satisfied_on_the_parsed_flag() -> None:
    patch = _patch("+    return certificate(problems=problems, last=args.last)\n")
    assert cli_last(patch) == Verdict.SATISFIED


def test_cli_last_not_satisfied_on_the_hardcoded_default() -> None:
    patch = _patch("+    return certificate(problems=problems, last=DEFAULT_LAST)\n")
    assert cli_last(patch) == Verdict.NOT_SATISFIED


def test_cli_last_undetermined_when_certificate_is_not_called() -> None:
    patch = _patch("+    return None\n")
    assert cli_last(patch) == Verdict.UNDETERMINED


# ---------------------------------------------------------------------------
# read_cell: the whole-row assembly, including the no-patch case


def test_read_cell_is_undetermined_on_every_column_with_no_patch() -> None:
    row = read_cell(None)
    assert set(row) == set(COLUMNS)
    assert all(v == Verdict.UNDETERMINED for v in row.values())


def test_read_cell_reads_all_four_columns_from_one_patch() -> None:
    patch = _patch(
        "+def busy_processes(lines):\n"
        "+    for line in lines:\n"
        "+        pid, pcpu, comm = line.split(maxsplit=2)\n"
        '+    msg1 = f"load {one_minute:.1f} > {ceiling * cores:.1f} ({cores} cores)"\n'
        '+    msg2 = f"decode {rate:.1f} tok/s < {floor} over last {n} completions"\n'
        "+    return {\n"
        '+        "inputs": {\n'
        '+            "load": self.load, "busy": self.busy, "decode": self.decode,\n'
        '+            "floor_tok_s": self.floor_tok_s, "model": self.model, "last": self.last,\n'
        "+        },\n"
        "+    }\n"
        "+    return certificate(problems=problems, last=args.last)\n"
    )
    row = read_cell(patch)
    assert row == {name: Verdict.SATISFIED for name in COLUMNS}
