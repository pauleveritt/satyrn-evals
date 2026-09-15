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
    ],
)
def test_unreplayed_bash_that_could_not_write_a_source_path(command: str) -> None:
    assert not cf.could_write_source(command, SOURCES, CWD)


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
NONE_SKIPPED = {"skipped_writer_turns": [], "anchor_miss_turns": [], "raised": None}


def test_a_failed_fidelity_check_is_unmeasured() -> None:
    reasons = cf.unmeasured_reasons(fidelity_result="fail", harness_verdict="pass", final_verdict="fail", trigger=None, **NONE_SKIPPED)
    assert reasons == ["fidelity: harness pass, replay fail"]


def test_a_passing_fidelity_check_with_nothing_skipped_is_measured() -> None:
    assert cf.unmeasured_reasons(fidelity_result="pass", harness_verdict="pass", final_verdict="pass", trigger=TRIGGER, **NONE_SKIPPED) == []


def test_a_skipped_writer_or_anchor_miss_through_the_trigger_turn_is_unmeasured() -> None:
    reasons = cf.unmeasured_reasons(
        fidelity_result="unverifiable", harness_verdict=None, final_verdict=None, trigger=TRIGGER,
        skipped_writer_turns=[4, 10], anchor_miss_turns=[7], raised=None,
    )
    assert reasons == ["skipped bash writer at turn 4", "skipped bash writer at turn 10", "replay raised: edit anchor missing at turn 7"]


def test_a_skipped_writer_after_the_trigger_or_without_a_counted_trigger_is_measured() -> None:
    late = {"skipped_writer_turns": [11], "anchor_miss_turns": [12], "raised": None}
    assert cf.unmeasured_reasons(fidelity_result="unverifiable", harness_verdict=None, final_verdict=None, trigger=TRIGGER, **late) == []
    early = {"skipped_writer_turns": [2], "anchor_miss_turns": [], "raised": None}
    assert cf.unmeasured_reasons(fidelity_result="unverifiable", harness_verdict=None, final_verdict=None, trigger=None, **early) == []
    over = cf.Trigger(step=5, turn=10, output_tokens=40_000, route="bash", within_budget=False)
    assert cf.unmeasured_reasons(fidelity_result="unverifiable", harness_verdict=None, final_verdict=None, trigger=over, **early) == []


def test_a_raise_is_unmeasured() -> None:
    reasons = cf.unmeasured_reasons(fidelity_result="unverifiable", harness_verdict=None, final_verdict=None, trigger=None, skipped_writer_turns=[], anchor_miss_turns=[], raised="CalledProcessError: git")
    assert reasons == ["raised: CalledProcessError: git"]


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
