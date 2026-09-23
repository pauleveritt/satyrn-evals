---
title: Using Evals
---

# Using Evals

The harness is a console command, `satyrn-evals`. Install with `uv sync`, then:

```bash
uv run satyrn-evals qualify <task>            # does the task qualify offline?
uv run satyrn-evals record new ...            # freeze a run record
uv run satyrn-evals launch <record> --arm ... # run the record's cells
```

A full run needs an arm file (model + tool surface) and a frozen record.
Grading is offline: `uv run satyrn-evals grade <task> <patch>`. See `--help`
on each subcommand for the exact flags, and the repository's `README.md` for
the model-settings preflight.
