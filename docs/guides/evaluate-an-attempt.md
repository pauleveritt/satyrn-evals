# Evaluate one attempt

Use this guide when you have a command that can work on a task and deliver a
patch plus transcript. Evals runs that command once in a disposable detached
worktree, preserves its delivered artifacts, then grades the patch offline.

## Before you run it

The attempt command must write a unified-diff patch to
`SATYRN_ATTEMPT_PATCH` and a non-empty transcript to
`SATYRN_ATTEMPT_TRANSCRIPT`. Evals supplies those absolute paths, along with
the task name and task statement, in the command environment.

The command runs with your permissions. The temporary worktree is lifecycle
isolation, not a security sandbox; review the command before running it.

## Run the command

Use an absolute output path and absolute paths in the attempt command, because
the command's working directory is the disposable worktree.

Run from your Evals checkout:

```console
$ ROOT="$(pwd)"
$ uv run satyrn-evals attempt TASK_NAME --output "$ROOT/attempts" -- \
    /absolute/path/to/attempt-command ARGUMENTS
```

For a task captured under `tasks/`, add `--tasks-root tasks` so Evals finds
it; without the flag, `attempt` resolves tasks only from the bundled set.

For a task carrying an engine contract, leave the engine command's final `--`
in place; Evals supplies the contract path after it.

## Inspect the saved evidence

Evals creates one timestamped directory beneath `attempts/` containing:

```text
patch.diff        # the delivered patch, if present
transcript.txt    # the delivered transcript, if present
receipt.json      # the offline grading result, if grading ran
attempt.json      # always: outcome, code, paths, and diagnostics
```

Read `attempt.json` first. A refusal is broader than a missing patch:
incomplete deliveries (`NO_PATCH`, `PATCH_INVALID`, `TRANSCRIPT_MISSING`,
`TRANSCRIPT_EMPTY`) and workspace, timeout, and cleanup failures
(`WORKSPACE_FAILED`, `COMMAND_TIMEOUT`, `CLEANUP_FAILED`) all refuse. A
gradeable patch instead receives a receipt whose verdict can be `pass`,
`fail`, or `unavailable`. A nonzero command exit does not override complete,
gradeable artifacts.

For the exact command contract and timeouts, see the [`attempt`
reference](../usage.md#attempt); the attempt directory and record fields are
documented in [task and artifact
formats](../reference/formats.md#attempt-directory-and-record).
