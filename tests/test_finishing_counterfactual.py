"""Pure rules of evidence/2026-09-15-finishing-counterfactual/counterfactual.py.

The script lives in a dated evidence directory (not an importable package),
so it is loaded by path. Every test here is default tier: synthetic event
streams and strings, no subprocess, no ~/satyrn-runs.
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parents[1] / "evidence" / "2026-09-15-finishing-counterfactual" / "counterfactual.py"
_SPEC = importlib.util.spec_from_file_location("finishing_counterfactual", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
cf = importlib.util.module_from_spec(_SPEC)
sys.modules["finishing_counterfactual"] = cf
_SPEC.loader.exec_module(cf)

CWD = "/Users/Shared/satyrn-cells/a/worktree"
SOURCES = ("src/satyrn_evals/run_record.py", "src/satyrn_evals/cli.py", "tests")


# --- synthetic Pi --mode json streams ------------------------------------------


def turn() -> dict:
    return {"type": "turn_start"}


def assistant(output: int) -> dict:
    return {"type": "message_end", "message": {"role": "assistant", "usage": {"output": output}, "content": []}}


def call(call_id: str, name: str, args: dict, text: str = "", *, error: bool = False, details: object = None) -> list[dict]:
    result: dict = {"content": [{"type": "text", "text": text}]}
    if details is not None:
        result["details"] = details
    return [
        {"type": "tool_execution_start", "toolCallId": call_id, "toolName": name, "args": args},
        {"type": "tool_execution_end", "toolCallId": call_id, "toolName": name, "result": result, "isError": error},
    ]


def self_test_details(exit_code: int, *, ok: bool = True, timed_out: bool = False) -> dict:
    return {"satyrn": True, "ok": ok, "code": "OK", "result": {"exit_code": exit_code, "output": "", "truncated": False, "timed_out": timed_out}}


def stream(*chunks: dict | list[dict]) -> list[dict]:
    events: list[dict] = [{"type": "session", "cwd": CWD}]
    for chunk in chunks:
        events.extend(chunk if isinstance(chunk, list) else [chunk])
    return events


EDIT_SOURCE = {"path": "src/satyrn_evals/run_record.py", "edits": [{"oldText": "a", "newText": "b"}]}
PYTEST = {"command": "uv run pytest tests/test_run_record.py -q"}


# --- phase selection -----------------------------------------------------------


def test_debug_phase_refuses_a_decision_attempt_id() -> None:
    with pytest.raises(cf.DecisionCellRefused, match="971281"):
        cf.select_cells("debug", ("971281",))


def test_debug_phase_refuses_a_decision_id_mixed_with_debug_ids() -> None:
    with pytest.raises(cf.DecisionCellRefused, match="028222"):
        cf.select_cells("debug", ("490384", "028222"))


def test_debug_phase_accepts_a_debug_id() -> None:
    assert [c.attempt for c in cf.select_cells("debug", ("490384",))] == ["490384"]


def test_debug_phase_without_a_filter_reads_only_debug_cells() -> None:
    cells = cf.select_cells("debug")
    assert len(cells) == 19
    assert not {c.attempt for c in cells} & cf.DECISION_IDS


def test_the_cli_refuses_a_decision_id_in_debug_before_reading_anything(capsys: pytest.CaptureFixture[str]) -> None:
    assert cf.main(["--phase", "debug", "--cell", "616367"]) == 2
    assert "refuses decision attempt ids: 616367" in capsys.readouterr().err


def test_decision_phase_is_exactly_the_spec_table_and_takes_no_filter() -> None:
    cells = cf.select_cells("decision")
    assert len(cells) == 24 and {c.attempt for c in cells} == cf.DECISION_IDS
    with pytest.raises(ValueError, match="refused"):
        cf.select_cells("decision", ("971281",))


# --- section 3: source edits ---------------------------------------------------


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("tests/test_cli.py", True),
        ("tools/hooks/test_guard.py", True),
        ("pkg/guard_test.py", True),
        ("tests/conftest.py", True),
        ("src/satyrn_evals/cli.py", False),
        ("tools/testing.py", False),
    ],
)
def test_test_file_rule(path: str, expected: bool) -> None:
    assert cf.is_test_file(path) is expected


def test_a_source_file_is_inside_source_paths_and_not_a_test() -> None:
    assert cf.is_source_file("src/satyrn_evals/cli.py", SOURCES)
    assert not cf.is_source_file("tests/test_cli.py", SOURCES)
    assert not cf.is_source_file("src/satyrn_evals/errors.py", SOURCES)


def test_tree_path_relativizes_the_worktree_and_drops_outside_paths() -> None:
    assert cf.tree_path(f"{CWD}/src/satyrn_evals/cli.py", CWD) == "src/satyrn_evals/cli.py"
    assert cf.tree_path(f"/private{CWD}/app.py", CWD) == "app.py"
    assert cf.tree_path("./app.py", CWD) == "app.py"
    assert cf.tree_path("/tmp/dbg.py", CWD) is None
    assert cf.tree_path("../escape.py", CWD) is None


def test_landed_writes_and_edits_to_source_files_are_source_edits() -> None:
    steps = cf.steps_of(stream(
        turn(), assistant(10),
        call("a", "write", {"path": f"{CWD}/src/satyrn_evals/cli.py", "content": "x"}, "Successfully wrote"),
        call("b", "edit", EDIT_SOURCE, "Successfully replaced"),
    ))
    assert cf.source_edit_indices(steps, SOURCES, CWD, {}) == [0, 1]


def test_test_files_errors_and_outside_paths_are_not_source_edits() -> None:
    steps = cf.steps_of(stream(
        turn(), assistant(10),
        call("a", "write", {"path": "tests/test_cli.py", "content": "x"}),
        call("b", "edit", EDIT_SOURCE, "ANCHOR_MISSING", error=True),
        call("c", "write", {"path": "/tmp/dbg.py", "content": "x"}),
        call("d", "write", {"path": "src/satyrn_evals/cli.py", "content": "x"}, "failed", error=True),
    ))
    assert cf.source_edit_indices(steps, SOURCES, CWD, {}) == []


def test_a_replayed_bash_write_counts_only_when_it_touched_a_source_file() -> None:
    steps = cf.steps_of(stream(
        turn(), assistant(10),
        call("a", "bash", {"command": "cat > tests/test_x.py <<EOF\nx\nEOF\n"}),
        call("b", "bash", {"command": "cat > src/satyrn_evals/cli.py <<EOF\nx\nEOF\n"}),
    ))
    touched = {0: ("tests/test_x.py",), 1: ("src/satyrn_evals/cli.py",)}
    assert cf.source_edit_indices(steps, SOURCES, CWD, touched) == [1]


# --- section 3: own-green ------------------------------------------------------


@pytest.mark.parametrize(
    ("output", "green"),
    [
        ("....\n4 passed, 4 warnings in 0.49s\n", True),
        ("===== 10 passed, 2 xfailed in 1.20s =====", True),
        ("F...\n1 failed, 3 passed in 0.20s\n", False),
        ("===== 2 passed, 1 error in 1.00s =====", False),
        ("3 passed, 2 errors in 0.3s", False),
        ("5 deselected in 0.10s", False),
        ("no tests ran in 0.01s", False),
        ("....\n[100%]\n", False),
        ("2 passed in 0.1s\n1 failed, 1 passed in 0.1s", False),
    ],
)
def test_a_pytest_summary_is_green_only_with_a_pass_and_no_failure(output: str, green: bool) -> None:
    assert cf.pytest_output_green(output) is green


def test_a_bash_pytest_run_with_a_green_summary_is_green() -> None:
    [step] = cf.steps_of(stream(turn(), assistant(5), call("a", "bash", PYTEST, "4 passed in 0.5s")))
    assert cf.is_test_run(step) and cf.is_green(step)


def test_an_errored_bash_pytest_run_is_not_green_even_with_a_passing_summary() -> None:
    [step] = cf.steps_of(stream(turn(), assistant(5), call("a", "bash", PYTEST, "4 passed in 0.5s", error=True)))
    assert cf.is_test_run(step) and not cf.is_green(step)


def test_a_bash_command_that_does_not_run_pytest_is_not_a_test_run() -> None:
    [step] = cf.steps_of(stream(turn(), assistant(5), call("a", "bash", {"command": "cat log.txt"}, "4 passed in 0.5s")))
    assert not cf.is_test_run(step) and not cf.is_green(step)


def test_a_self_test_that_exited_zero_is_green() -> None:
    [step] = cf.steps_of(stream(turn(), assistant(5), call("a", "self_test", {}, "Test command exited 0\n4 passed in 0.5s", details=self_test_details(0))))
    assert cf.is_test_run(step) and cf.is_green(step)


@pytest.mark.parametrize(
    "details",
    [self_test_details(1), self_test_details(0, ok=False), self_test_details(0, timed_out=True), None],
)
def test_a_self_test_that_failed_refused_or_timed_out_is_not_green(details: dict | None) -> None:
    [step] = cf.steps_of(stream(turn(), assistant(5), call("a", "self_test", {}, "Test command exited 1\n1 failed in 0.5s", details=details)))
    assert cf.is_test_run(step) and not cf.is_green(step)


def test_a_self_test_with_ok_details_but_a_failing_summary_text_is_not_green() -> None:
    """Documents behaviour: exit_code 0 / ok True in details does not override a
    failing pytest summary in the step's own text."""
    [step] = cf.steps_of(stream(turn(), assistant(5), call("a", "self_test", {}, "1 failed, 2 passed in 0.1s", details=self_test_details(0))))
    assert cf.is_test_run(step) and not cf.is_green(step)


def test_steps_carry_evals_turn_and_output_token_counts_at_their_end() -> None:
    steps = cf.steps_of(stream(
        turn(), assistant(100), call("a", "bash", {"command": "ls"}),
        turn(), assistant(250), call("b", "bash", {"command": "ls"}),
        {"type": "message_end", "message": {"role": "user", "usage": {"output": 999}}},
    ))
    assert [(s.turn, s.output_tokens) for s in steps] == [(1, 100), (2, 350)]


# --- section 3: trigger and budget ---------------------------------------------


def test_the_trigger_is_the_first_green_run_after_the_first_source_edit() -> None:
    steps = cf.steps_of(stream(
        turn(), assistant(100), call("a", "bash", PYTEST, "3 passed in 0.1s"),
        turn(), assistant(100), call("b", "edit", EDIT_SOURCE, "ok"),
        turn(), assistant(100), call("c", "bash", PYTEST, "1 failed, 2 passed in 0.1s", error=True),
        turn(), assistant(100), call("d", "bash", PYTEST, "3 passed in 0.1s"),
        turn(), assistant(100), call("e", "bash", PYTEST, "3 passed in 0.1s"),
    ))
    trigger = cf.find_trigger(steps, cf.source_edit_indices(steps, SOURCES, CWD, {}))
    assert trigger == cf.Trigger(step=3, turn=4, output_tokens=400, route="bash", within_budget=True)


def test_no_source_edit_means_no_trigger() -> None:
    steps = cf.steps_of(stream(turn(), assistant(100), call("a", "bash", PYTEST, "3 passed in 0.1s")))
    assert cf.find_trigger(steps, cf.source_edit_indices(steps, SOURCES, CWD, {})) is None


def test_no_green_run_after_the_edit_means_no_trigger() -> None:
    steps = cf.steps_of(stream(
        turn(), assistant(100), call("a", "edit", EDIT_SOURCE, "ok"),
        turn(), assistant(100), call("b", "bash", PYTEST, "1 failed in 0.1s", error=True),
    ))
    assert cf.find_trigger(steps, [0]) is None


def test_a_same_step_source_write_with_a_green_pytest_remainder_is_its_own_trigger() -> None:
    """Finding 3: a source write earlier in the same bash command as a green pytest
    run precedes that pytest in stream order, so the write-and-test step is its own
    trigger when the replay performed the write and the remainder runs pytest."""
    command = "cat > src/satyrn_evals/cli.py <<EOF\nx\nEOF\nuv run pytest tests/test_run_record.py -q"
    steps = cf.steps_of(stream(turn(), assistant(100), call("a", "bash", {"command": command}, "3 passed in 0.1s")))
    touched = {0: ("src/satyrn_evals/cli.py",)}
    source_edits = cf.source_edit_indices(steps, SOURCES, CWD, touched)
    assert source_edits == [0]
    trigger = cf.find_trigger(steps, source_edits, CWD)
    assert trigger == cf.Trigger(step=0, turn=1, output_tokens=100, route="bash", within_budget=True)


def test_a_same_step_write_to_a_test_file_only_with_a_green_remainder_is_not_a_trigger() -> None:
    """The same shape, but the write lands on a test file (not a source edit) and there
    is no other edit: no source edit at all, so there is nothing to trigger from."""
    command = "cat > tests/test_x.py <<EOF\nx\nEOF\nuv run pytest tests/test_run_record.py -q"
    steps = cf.steps_of(stream(turn(), assistant(100), call("a", "bash", {"command": command}, "3 passed in 0.1s")))
    touched = {0: ("tests/test_x.py",)}
    source_edits = cf.source_edit_indices(steps, SOURCES, CWD, touched)
    assert source_edits == []
    assert cf.find_trigger(steps, source_edits, CWD) is None


def test_a_non_bash_first_edit_step_is_never_its_own_trigger() -> None:
    """A write/edit tool step is never itself a trigger -- ``is_test_run`` is only ever
    true for ``self_test`` or a ``bash`` step -- so the trigger is the later bash run."""
    steps = cf.steps_of(stream(
        turn(), assistant(100), call("a", "edit", EDIT_SOURCE, "ok"),
        turn(), assistant(100), call("b", "bash", PYTEST, "3 passed in 0.1s"),
    ))
    source_edits = cf.source_edit_indices(steps, SOURCES, CWD, {})
    assert source_edits == [0]
    trigger = cf.find_trigger(steps, source_edits, CWD)
    assert trigger is not None and trigger.step == 1


@pytest.mark.parametrize(
    ("tokens", "turns", "within"),
    [(32_000, 48, True), (32_001, 3, False), (100, 49, False), (31_999, 47, True)],
)
def test_a_trigger_counts_only_within_the_budget(tokens: int, turns: int, within: bool) -> None:
    chunks: list[dict | list[dict]] = [turn(), assistant(tokens), call("a", "edit", EDIT_SOURCE, "ok")]
    chunks += [turn(), assistant(0)] * (turns - 1)
    chunks.append(call("b", "bash", PYTEST, "3 passed in 0.1s"))
    steps = cf.steps_of(stream(*chunks))
    trigger = cf.find_trigger(steps, [0])
    assert trigger is not None and (trigger.turn, trigger.output_tokens) == (turns, tokens)
    assert trigger.within_budget is within


# --- replay rules ----------------------------------------------------------------


def test_a_heredoc_write_replays_up_to_its_terminator_and_keeps_the_rest() -> None:
    plan = cf.plan_bash(f"cd {CWD} && cat > tools/hooks/guard.py << 'EOF'\nprint(1)\nEOF\nuv run pytest -q", CWD)
    assert plan.replay == "cat > tools/hooks/guard.py << 'EOF'\nprint(1)\nEOF\n"
    assert plan.remainder == "uv run pytest -q"


def test_a_word_first_heredoc_and_a_single_sed_replay() -> None:
    assert cf.plan_bash("cat <<EOF > app.py\nx\nEOF", CWD).replay == "cat <<EOF > app.py\nx\nEOF\n"
    assert cf.plan_bash("sed -i '' 's/a/b/' app.py", CWD).replay == "sed -i '' 's/a/b/' app.py"


@pytest.mark.parametrize(
    "command",
    [
        "cat > /tmp/dbg.py <<EOF\nx\nEOF",
        "cd tests && cat > test_x.py <<EOF\nx\nEOF",
        "echo x > app.py && uv run pytest",
        "cat > app.py <<EOF\nnever terminated",
        "python3 -c \"open('app.py','w').write('x')\"",
    ],
)
def test_other_bash_forms_do_not_replay(command: str) -> None:
    assert cf.plan_bash(command, CWD).replay is None


@pytest.mark.parametrize(
    "command",
    [
        "git checkout -- .",
        "git stash",
        "uv run ruff format .",
        "uv run ruff check --fix src/",
        "echo x > src/satyrn_evals/cli.py && true",
        f"printf 'x' >> {CWD}/src/satyrn_evals/run_record.py; ls",
        "python3 -c \"open('src/satyrn_evals/cli.py','w').write(s)\"",
        "cp /tmp/fixed.py src/satyrn_evals/run_record.py",
        "sed -i '' 's/a/b/' src/satyrn_evals/cli.py && uv run pytest",
        "cd src/satyrn_evals && perl -i -pe 's/a/b/' cli.py && cd ../.. && uv run pytest",
        "mv src/satyrn_evals/run_record.py /tmp/r.bak; uv run pytest; mv /tmp/r.bak src/satyrn_evals/run_record.py",
        "uv run python - <<'EOF'\nfrom pathlib import Path\nPath('src/satyrn_evals/cli.py').write_text(s)\nEOF",
        f"python3 -c \"open('{CWD}/tests/x.py','w').write('x')\"",
        "python3 -c \"open('./tests/x.py','w').write('x')\"",
        "sed --in-place 's/a/b/' src/satyrn_evals/cli.py && uv run pytest",
        "sed --in-place=bak 's/a/b/' src/satyrn_evals/cli.py && uv run pytest",
        'cd "$(pwd)" && sed -i \'s/a/b/\' src/satyrn_evals/cli.py && uv run pytest',
        "cd $(pwd) && perl -i -pe 's/a/b/' src/satyrn_evals/cli.py",
        "cd $PWD && echo x > src/satyrn_evals/cli.py; ls",
        'echo x > "$(pwd)/src/satyrn_evals/cli.py" && true',
    ],
)
def test_unreplayed_bash_that_could_write_a_source_path(command: str) -> None:
    assert cf.could_write_source(command, SOURCES, CWD)


@pytest.mark.parametrize(
    "command",
    [
        "uv run pytest tests/ -q 2>&1 | tail -30",
        "cat src/satyrn_evals/cli.py > /tmp/cli.txt",
        "grep -n def src/satyrn_evals/cli.py > /dev/null",
        "python3 -c \"import sys; sys.stdout.write('hi')\"",
        "echo done > notes.txt",
        "sed -i 's/x/y/' /dev/null; grep -c to_dict tests/test_run_record.py",
        "touch .testfile && ls tools/hooks/guard.py && rm .testfile",
        "uv run python - <<'EOF'\nprint(decide('cp docs x'))\nEOF",
        "uv run ruff format --check src/",
        "cd /tmp && echo x > cli.py",
        "cp tests/its.py its.py",
        'cd "$(pwd)" && echo x > notes.txt',
        'cd "$(pwd)" && uv run pytest tests/ -q',
    ],
)
def test_unreplayed_bash_that_could_not_write_a_source_path(command: str) -> None:
    assert not cf.could_write_source(command, SOURCES, CWD)


def test_mentions_source_matches_a_directory_entry_by_absolute_or_dot_slash_path() -> None:
    assert cf.mentions_source(f"open('{CWD}/tests/x.py','w')", SOURCES)
    assert cf.mentions_source("open('./tests/x.py','w')", SOURCES)
    assert not cf.mentions_source("open('mytests/x.py','w')", SOURCES)


def test_unroot_head_strips_the_private_alias_deterministically() -> None:
    cwd = "/Users/Shared/satyrn-cells/a/worktree"
    command = f"cat > /private{cwd}/app.py << 'EOF'\nx\nEOF\n"
    result = cf._unroot_head(command, cwd)
    assert result.startswith("cat > app.py")
    assert "/private" not in result


def test_counts_as_skipped_write_only_when_failed() -> None:
    assert not cf.counts_as_skipped_write(0, False)
    assert not cf.counts_as_skipped_write(0, True)


def test_counts_as_skipped_write_keeps_the_non_error_rule() -> None:
    assert cf.counts_as_skipped_write(1, False)


def test_counts_as_skipped_write_is_false_when_the_original_also_errored() -> None:
    """Finding 4, reversed from the prior round: if the original step already errored,
    a failing replay landed no write either time -- not a skipped writer, even on a
    target inside source_paths."""
    assert not cf.counts_as_skipped_write(1, True)


# --- section 4: outcomes, fidelity, unmeasured ----------------------------------


def test_actual_pass_needs_ok_and_pass() -> None:
    assert cf.actual_pass("OK", "pass")
    assert not cf.actual_pass("OK", "fail")
    assert not cf.actual_pass("BUDGET_EXCEEDED", None)


@pytest.mark.parametrize(
    ("harness", "replayed", "expected"),
    [
        ("pass", "pass", "pass"),
        ("fail", "fail", "pass"),
        ("unavailable", "unavailable", "pass"),
        ("pass", "fail", "fail"),
        ("fail", None, "fail"),
        (None, "pass", "unverifiable"),
    ],
)
def test_fidelity(harness: str | None, replayed: str | None, expected: str) -> None:
    assert cf.fidelity(harness, replayed) == expected


TRIGGER = cf.Trigger(step=5, turn=10, output_tokens=20_000, route="bash", within_budget=True)
NONE_SKIPPED = {
    "skipped_writer_turns": [], "anchor_miss_turns": [], "raised": None,
    "actual": True, "trigger_verdict": None, "unverified_bash_turns": [],
}


def test_a_failed_fidelity_check_is_unmeasured() -> None:
    reasons = cf.unmeasured_reasons(fidelity_result="fail", harness_verdict="pass", final_verdict="fail", trigger=None, **NONE_SKIPPED)
    assert reasons == ["fidelity: harness pass, replay fail"]


def test_a_passing_fidelity_check_with_nothing_skipped_is_measured() -> None:
    assert cf.unmeasured_reasons(fidelity_result="pass", harness_verdict="pass", final_verdict="pass", trigger=TRIGGER, **NONE_SKIPPED) == []


def test_a_skipped_writer_or_anchor_miss_through_the_trigger_turn_is_unmeasured() -> None:
    reasons = cf.unmeasured_reasons(
        fidelity_result="unverifiable", harness_verdict=None, final_verdict=None, trigger=TRIGGER,
        skipped_writer_turns=[4, 10], anchor_miss_turns=[7], raised=None,
        actual=True, trigger_verdict=None, unverified_bash_turns=[],
    )
    assert reasons == ["skipped bash writer at turn 4", "skipped bash writer at turn 10", "replay raised: edit anchor missing at turn 7"]


def test_a_skipped_writer_after_the_trigger_or_without_a_counted_trigger_is_measured() -> None:
    late = {"skipped_writer_turns": [11], "anchor_miss_turns": [12], "raised": None, "actual": True, "trigger_verdict": None, "unverified_bash_turns": []}
    assert cf.unmeasured_reasons(fidelity_result="unverifiable", harness_verdict=None, final_verdict=None, trigger=TRIGGER, **late) == []
    early = {"skipped_writer_turns": [2], "anchor_miss_turns": [], "raised": None, "actual": True, "trigger_verdict": None, "unverified_bash_turns": []}
    assert cf.unmeasured_reasons(fidelity_result="unverifiable", harness_verdict=None, final_verdict=None, trigger=None, **early) == []
    over = cf.Trigger(step=5, turn=10, output_tokens=40_000, route="bash", within_budget=False)
    assert cf.unmeasured_reasons(fidelity_result="unverifiable", harness_verdict=None, final_verdict=None, trigger=over, **early) == []


def test_a_raise_is_unmeasured() -> None:
    reasons = cf.unmeasured_reasons(
        fidelity_result="unverifiable", harness_verdict=None, final_verdict=None, trigger=None,
        skipped_writer_turns=[], anchor_miss_turns=[], raised="CalledProcessError: git",
        actual=True, trigger_verdict=None, unverified_bash_turns=[],
    )
    assert reasons == ["raised: CalledProcessError: git"]


# --- spec 7.4: conservative rescues --------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        'cd "$(pwd)" && uv run pytest tests/ -q 2>&1 | tail -30',
        "grep -n def src/x.py | head",
        "git diff",
        "find . -name '*.py'",
        "sed -n '1,20p' f",
    ],
)
def test_is_read_only_bash_true_cases(command: str) -> None:
    assert cf.is_read_only_bash(command, CWD)


@pytest.mark.parametrize(
    "command",
    [
        "echo x > f",
        "sort -o out f",
        "find . -delete",
        "sed -i 's/a/b/' f",
        "git checkout .",
        "cat f > /dev/null",
        "cd /tmp && ls",
        "ls $(python fix.py)",
        "tee f",
        "sed -n 'w out.txt' f",
        "find . -fls out.txt",
        "uniq a.txt src/satyrn_evals/cli.py",
    ],
)
def test_is_read_only_bash_false_cases(command: str) -> None:
    assert not cf.is_read_only_bash(command, CWD)


def test_is_read_only_bash_uniq_with_a_single_operand_is_still_true() -> None:
    assert cf.is_read_only_bash("uniq a.txt", CWD)


def test_a_reconstructed_pass_over_read_only_only_bash_history_is_a_rescue() -> None:
    steps = cf.steps_of(stream(
        turn(), assistant(100), call("a", "bash", {"command": "cat notes.txt"}, "hi"),
        turn(), assistant(100), call("b", "edit", EDIT_SOURCE, "ok"),
        turn(), assistant(100), call("c", "bash", PYTEST, "3 passed in 0.1s"),
    ))
    trigger = cf.find_trigger(steps, cf.source_edit_indices(steps, SOURCES, CWD, {}), CWD)
    assert trigger is not None and trigger.within_budget
    unverified = cf.unverified_bash_turns(steps, CWD, trigger.turn)
    assert unverified == []
    reasons = cf.unmeasured_reasons(
        fidelity_result="unverifiable", harness_verdict=None, final_verdict=None, trigger=trigger,
        skipped_writer_turns=[], anchor_miss_turns=[], raised=None,
        actual=False, trigger_verdict="pass", unverified_bash_turns=unverified,
    )
    assert reasons == []
    counter = cf.counterfactual_pass(False, trigger, reasons, "pass")
    assert cf.change(False, counter) == "rescue"


def test_a_reconstructed_pass_with_unverified_bash_in_history_is_not_a_rescue() -> None:
    steps = cf.steps_of(stream(
        turn(), assistant(100), call("a", "bash", {"command": "python fix.py"}, ""),
        turn(), assistant(100), call("b", "edit", EDIT_SOURCE, "ok"),
        turn(), assistant(100), call("c", "bash", {"command": "patch -p1 < fix.diff"}, ""),
        turn(), assistant(100), call("d", "bash", {"command": "uv run ruff format ."}, ""),
        turn(), assistant(100), call("e", "bash", PYTEST, "3 passed in 0.1s"),
    ))
    trigger = cf.find_trigger(steps, cf.source_edit_indices(steps, SOURCES, CWD, {}), CWD)
    assert trigger is not None and trigger.within_budget
    unverified = cf.unverified_bash_turns(steps, CWD, trigger.turn)
    assert unverified
    reasons = cf.unmeasured_reasons(
        fidelity_result="unverifiable", harness_verdict=None, final_verdict=None, trigger=trigger,
        skipped_writer_turns=[], anchor_miss_turns=[], raised=None,
        actual=False, trigger_verdict="pass", unverified_bash_turns=unverified,
    )
    assert reasons and reasons[-1].startswith("unverified-rescue")
    counter = cf.counterfactual_pass(False, trigger, reasons, "pass")
    assert counter is False
    assert cf.change(False, counter) == "none"


def test_a_replayed_writer_with_a_read_only_remainder_is_verified_and_rescue_still_allowed() -> None:
    """A source write covered by the replay, whose remainder is itself a read-only test
    run, is not unverified -- the rescue still goes through."""
    write_command = "cat > src/satyrn_evals/cli.py <<EOF\nx\nEOF\nuv run pytest -q"
    steps = cf.steps_of(stream(turn(), assistant(100), call("a", "bash", {"command": write_command}, "3 passed in 0.1s")))
    touched = {0: ("src/satyrn_evals/cli.py",)}
    source_edits = cf.source_edit_indices(steps, SOURCES, CWD, touched)
    trigger = cf.find_trigger(steps, source_edits, CWD)
    assert trigger is not None and trigger.step == 0 and trigger.within_budget
    unverified = cf.unverified_bash_turns(steps, CWD, trigger.turn)
    assert unverified == []
    reasons = cf.unmeasured_reasons(
        fidelity_result="unverifiable", harness_verdict=None, final_verdict=None, trigger=trigger,
        skipped_writer_turns=[], anchor_miss_turns=[], raised=None,
        actual=False, trigger_verdict="pass", unverified_bash_turns=unverified,
    )
    assert reasons == []
    assert cf.change(False, cf.counterfactual_pass(False, trigger, reasons, "pass")) == "rescue"


def test_unverified_bash_does_not_prevent_harm_on_an_actual_pass_cell() -> None:
    """Harm counting is unaffected by 7.4: an actual pass with unverified bash and a
    failing trigger verdict is still a harm."""
    reasons = cf.unmeasured_reasons(
        fidelity_result="pass", harness_verdict="pass", final_verdict="pass", trigger=TRIGGER,
        skipped_writer_turns=[], anchor_miss_turns=[], raised=None,
        actual=True, trigger_verdict="fail", unverified_bash_turns=[3, 7],
    )
    assert reasons == []
    assert cf.change(True, cf.counterfactual_pass(True, TRIGGER, reasons, "fail")) == "harm"


def test_replay_records_failed_replay_turns() -> None:
    """Gate fix (Finding 4 follow-up): the ``Replay`` dataclass records the turns of
    failed bash replays, independently of skipped_writer_turns."""
    assert cf.Replay().failed_replay_turns == []
    assert cf.Replay(failed_replay_turns=[3, 7]).failed_replay_turns == [3, 7]


def test_a_failed_replay_turn_through_the_trigger_makes_a_would_be_rescue_unverified() -> None:
    """Gate fix: a failed bash replay is unioned into the turns passed to
    ``unmeasured_reasons`` as ``unverified_bash_turns`` (the way ``measure`` unions
    ``Replay.failed_replay_turns``, filtered to turns at or before the trigger) --
    never into ``skipped_writer_turns``, and it does not touch fidelity."""
    failed_replay_turns = [3, 9]
    unified = sorted(set() | {t for t in failed_replay_turns if t <= TRIGGER.turn})
    assert unified == [3, 9]
    reasons = cf.unmeasured_reasons(
        fidelity_result="pass", harness_verdict="pass", final_verdict="pass", trigger=TRIGGER,
        skipped_writer_turns=[], anchor_miss_turns=[], raised=None,
        actual=False, trigger_verdict="pass", unverified_bash_turns=unified,
    )
    assert reasons and reasons[0].startswith("unverified-rescue")
    counter = cf.counterfactual_pass(False, TRIGGER, reasons, "pass")
    assert cf.change(False, counter) == "none"


def test_a_failed_replay_turn_does_not_prevent_harm_on_an_actual_pass_cell() -> None:
    unified = sorted({t for t in [3, 9] if t <= TRIGGER.turn})
    reasons = cf.unmeasured_reasons(
        fidelity_result="pass", harness_verdict="pass", final_verdict="pass", trigger=TRIGGER,
        skipped_writer_turns=[], anchor_miss_turns=[], raised=None,
        actual=True, trigger_verdict="fail", unverified_bash_turns=unified,
    )
    assert reasons == []
    assert cf.change(True, cf.counterfactual_pass(True, TRIGGER, reasons, "fail")) == "harm"


def test_a_failed_replay_turn_after_the_trigger_changes_nothing() -> None:
    failed_replay_turns = [TRIGGER.turn + 5]
    unified = sorted({t for t in failed_replay_turns if t <= TRIGGER.turn})
    assert unified == []
    reasons = cf.unmeasured_reasons(
        fidelity_result="unverifiable", harness_verdict=None, final_verdict=None, trigger=TRIGGER,
        skipped_writer_turns=[], anchor_miss_turns=[], raised=None,
        actual=False, trigger_verdict="pass", unverified_bash_turns=unified,
    )
    assert reasons == []
    assert cf.change(False, cf.counterfactual_pass(False, TRIGGER, reasons, "pass")) == "rescue"


def test_rescue_harm_and_no_change() -> None:
    assert cf.change(False, cf.counterfactual_pass(False, TRIGGER, [], "pass")) == "rescue"
    assert cf.change(True, cf.counterfactual_pass(True, TRIGGER, [], "fail")) == "harm"
    assert cf.change(True, cf.counterfactual_pass(True, TRIGGER, [], "pass")) == "none"
    assert cf.change(False, cf.counterfactual_pass(False, TRIGGER, [], "unavailable")) == "none"


def test_no_trigger_an_over_budget_trigger_or_unmeasured_keeps_the_actual_outcome() -> None:
    over = cf.Trigger(step=5, turn=10, output_tokens=40_000, route="bash", within_budget=False)
    assert cf.counterfactual_pass(False, None, [], None) is False
    assert cf.counterfactual_pass(False, over, [], "pass") is False
    assert cf.counterfactual_pass(True, TRIGGER, ["fidelity: harness pass, replay fail"], "fail") is True


# --- section 5 ---------------------------------------------------------------------


def test_budget_shaped_needs_two_budget_or_timeout_codes() -> None:
    assert cf.budget_shaped(["COMMAND_TIMEOUT", "BUDGET_EXCEEDED", "OK", "OK"])
    assert not cf.budget_shaped(["BUDGET_EXCEEDED", "OK", "OK", "OK"])


def test_the_spec_codes_select_the_spec_budget_shaped_tasks() -> None:
    shaped = [
        task for task in (*cf.BUDGET_SHAPED, *cf.FLOOR)
        if cf.budget_shaped([cf.RECORDED[c.attempt][0] for c in cf.DECISION if c.task == task])
    ]
    assert shaped == list(cf.BUDGET_SHAPED)


def test_more_than_one_unmeasured_cell_makes_a_task_insufficient() -> None:
    assert cf.tally("t", ["none"] * 4, [True, True, False, False]).insufficient
    assert not cf.tally("t", ["none"] * 4, [True, False, False, False]).insufficient
    assert cf.tally("t", ["rescue", "rescue", "harm", "none"], [False] * 4).net == 1


def tallies(**overrides: tuple[int, int, int]) -> dict:
    """task -> (rescues, harms, unmeasured); every other task all zeros."""
    return {t: cf.TaskTally(t, 4, *overrides.get(t.replace("-", "_"), (0, 0, 0))) for t in (*cf.BUDGET_SHAPED, *cf.FLOOR)}


def test_go_needs_two_qualifying_tasks_low_floor_harm_and_no_insufficient_floor() -> None:
    outcome, _ = cf.decide(tallies(agentclinic_repair_depth_3=(1, 0, 0), selfhost_docs_linter=(2, 1, 1), selfhost_review_script=(0, 1, 1)))
    assert outcome == "go"


def test_verify_when_exactly_one_task_qualifies() -> None:
    assert cf.decide(tallies(selfhost_run_record_gate=(1, 0, 0)))[0] == "verify"


def test_verify_when_two_qualify_but_floor_harm_reaches_two() -> None:
    t = tallies(agentclinic_repair_depth_3=(1, 0, 0), selfhost_run_record_gate=(1, 0, 0), selfhost_guard_prefixes=(0, 1, 0), agentclinic_repair_depth_2=(0, 1, 0))
    assert cf.decide(t)[0] == "verify"


def test_verify_when_two_qualify_but_a_floor_task_is_insufficient() -> None:
    t = tallies(agentclinic_repair_depth_3=(1, 0, 0), selfhost_run_record_gate=(1, 0, 0), agentclinic_repair_depth_2=(0, 0, 2))
    assert cf.decide(t)[0] == "verify"


def test_an_insufficient_task_does_not_qualify() -> None:
    t = tallies(agentclinic_repair_depth_3=(1, 0, 0), selfhost_run_record_gate=(2, 0, 2))
    assert cf.decide(t)[0] == "verify"


def test_not_the_lever_when_no_budget_shaped_task_nets_a_rescue() -> None:
    assert cf.decide(tallies(agentclinic_repair_depth_3=(1, 1, 0), selfhost_guard_prefixes=(3, 0, 0)))[0] == "not-the-lever"


def test_verify_when_the_only_net_rescue_is_on_an_insufficient_task() -> None:
    outcome, reason = cf.decide(tallies(selfhost_docs_linter=(1, 0, 2)))
    assert outcome == "verify" and "section 7.1" in reason


def test_the_table_row_marks_an_over_budget_trigger_and_joins_reasons() -> None:
    row = {
        "task": "t", "group": "engine", "attempt": "000001", "code": "BUDGET_EXCEEDED", "harness_verdict": None,
        "trigger": {"step": 1, "turn": 50, "output_tokens": 30_000, "route": "bash", "within_budget": False},
        "actual": "not-pass", "counterfactual": "not-pass", "change": "none", "fidelity": "unverifiable",
        "unmeasured": ["a", "b"],
    }
    text = cf.table([row], {"evals_commit": "abc", "evals_dirty": False, "command": "counterfactual.py --phase debug"})
    assert "| 50 (over budget) | 30000 |" in text and "| a; b |" in text
    assert json.dumps(row)  # rows stay JSON-serializable


def test_a_grade_root_under_a_python_project_is_found(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\n")
    (tmp_path / "grades").mkdir()
    assert cf.project_markers(tmp_path / "grades") == [tmp_path / "pyproject.toml"]


def test_a_grade_root_with_no_project_above_it_is_clean(tmp_path: Path) -> None:
    (tmp_path / "grades").mkdir()
    assert [m for m in cf.project_markers(tmp_path / "grades") if m.is_relative_to(tmp_path)] == []


def test_the_cli_refuses_a_grade_root_inside_the_evals_checkout(capsys: pytest.CaptureFixture[str]) -> None:
    assert cf.main(["--phase", "debug", "--cell", "490384", "--grade-root", str(cf.HERE / "work")]) == 2
    assert "pytest would read it while grading" in capsys.readouterr().err


def test_the_cli_refuses_a_grade_root_whose_phase_folder_itself_has_a_marker(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "debug").mkdir()
    (tmp_path / "debug" / "pyproject.toml").write_text("[project]\n")
    assert cf.main(["--phase", "debug", "--cell", "490384", "--grade-root", str(tmp_path)]) == 2
    assert "pytest would read it while grading" in capsys.readouterr().err
