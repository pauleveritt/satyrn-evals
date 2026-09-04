# Capture a task from a fixing commit

Use this guide when you have a real Python fixing commit and want a repeatable
task that an attempt command can solve.

## What you need

A checkout of this repository, [uv](https://docs.astral.sh/uv/), and a source
repository with a clean working tree containing the fixing commit. Identify
the SHA of the fixing commit and choose an output directory that does not
contain tracked files. Capture does not change the source repository's
existing files, index, branch, or `HEAD`; it writes only the declared output
artifacts.

## Capture the change

```console
$ uv run satyrn-evals capture --revert FIX_SHA --repo /path/to/source --output tasks
```

Replace `FIX_SHA` and `/path/to/source`. A successful capture creates the task
directory and its capture record, `<TASK_NAME>.capture.json`, under `tasks/`.
The record is authoritative: read its `outcome` and `code`, rather than
treating the process exit status as the whole result.

Capture proves four things before it creates a task: the source is eligible,
the base oracle runs, the base is un-done, and the fixing patch is winnable.
It refuses with a precise code if any check cannot be established.

## Use the captured task

First prove that the captured known-good patch grades correctly:

```console
$ uv run satyrn-evals grade --tasks-root tasks TASK_NAME \
    tasks/TASK_NAME/fixtures/known-good.patch
```

Replace `TASK_NAME` with the directory name in the capture record. Then run
an attempt against it — pass `--tasks-root tasks` there as well, since
captured tasks live outside the wheel. See [evaluate one
attempt](evaluate-an-attempt.md).

For every flag and refusal code, see the [`capture`
reference](../usage.md#capture); the capture record's fields are documented in
[task and artifact formats](../reference/formats.md#capture-record).
