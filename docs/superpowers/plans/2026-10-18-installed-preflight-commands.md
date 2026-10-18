# Installed preflight commands implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove import-path mutation from the live preflight tools.

**Architecture:** Move maintained command implementations into `satyrn_evals` and expose their `main` functions through installed commands. Keep the existing script paths as thin wrappers for callers and arm metadata. Keep `scripts/prereqs.py` standalone with standard-library imports only.

**Tech Stack:** Python 3.14, uv, Hatch, pytest, Ruff.

**Spec:** The approved description in this conversation: use normal package imports and installed commands, preserve standalone prerequisite checks, and update callers and tests on the PR branch.

## Global constraints

- Work in `.worktrees/installed-preflight-commands` on `refactor/installed-preflight-commands`, based on `main`.
- Keep eval-owned configuration in the separate `fix/eval-pi-config` branch, stacked on this refactor. The user requested this split on 2026-10-18.
- Do not run inference, change evaluation policy, or edit historical evidence and bundled task snapshots.
- Keep command arguments, exit codes, settings provenance, and arm metadata unchanged.
- Use existing behavior tests for moved logic. Check entry-point configuration through actual command execution, not new static assertions.
- Record every new file in `PROVENANCE.md`.

## Review focus

- Installed commands must load outside the repository working directory. Check each command with `uv run --project ...` from a temporary directory.
- Existing script wrappers must still load through the project interpreter. Check their help output directly.
- Prerequisite checks must work without an installed `satyrn_evals` package. Add success and refusal cases for a standalone backend check.
- Model configuration selection and provenance must remain unchanged. Run the existing configuration and settings tests.
- Historical evidence, task snapshots, and arm metadata must remain unchanged. Check the final diff and run the full gates.

## Task 1: Replace script import bootstrap with package loading

**Files:**
- Create: `src/satyrn_evals/{preflight_commands,preflight_models,preflight_settings,preflight_inference,interleave}.py`.
- Modify: the matching five wrappers under `scripts/`. Preserve standalone `scripts/prereqs.py`.
- Modify: `pyproject.toml`, `scripts/preflight.sh`, `scripts/c3_night.sh`, `README.md`, `docs/user-guide.md`, and `docs/user-journey.md`.
- Modify: the matching existing tests, `tests/test_prereqs.py`, and `PROVENANCE.md`. Keep `tests/test_eval_pi_config.py` in the stacked configuration branch.

**Interfaces:**
- Preserve each command's `main(argv: list[str] | None = None) -> int` and existing behavior helpers.
- Expose `satyrn-evals-preflight-{commands,models,settings,inference}` and `satyrn-evals-interleave`.
- Preserve `scripts/prereqs.py` and its existing CLI without importing the project package.

- [ ] Add paired backend success/refusal tests that block imports of `satyrn_evals` and execute the standalone prerequisite logic.
- [ ] Retain the red/green evidence from the original combined branch. On `main`, prerequisite checks already use only the standard library; preserve that behavior here.
- [ ] Move command implementations without changing their behavior. Remove path mutation and import-order suppressions. Replace the original scripts with wrappers.
- [ ] Register the five installed commands. Update current shell callers and documentation. Keep retired drivers unchanged.
- [ ] Keep prerequisite configuration selection unchanged from `main`. In the stacked eval configuration branch, read eval-owned model JSON through the standard library without importing the project package.
- [ ] Update existing tests to import command implementations normally. Use normal `scripts` imports for standalone tools used by tests.
- [ ] Run the focused tests, installed-command and wrapper smoke checks, and an isolated standalone prerequisite check.
- [ ] Run `just gates` and `git diff --check`. Check that no live script mutates `sys.path` and that retained evidence is unchanged.
- [ ] Commit the tested refactor. Preserve the worktree for PR follow-up.
