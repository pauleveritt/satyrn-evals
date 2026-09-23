---
title: Glossary
---

# Glossary

The Evals harness's vocabulary. The engine's terms live in its own
[glossary](engine-glossary.md).

**task**

One self-contained piece of work: a base commit, a contract, a hidden oracle
test suite, and a public feedback surface. Captured by `satyrn-evals capture`.

**arm**

One measured configuration: the attempt command, the model, and the tool
surface. Baseline and Engine are the two arms.

**cell**

One attempt: a task run once, in one isolated workspace, under one arm.

**launcher**

The `satyrn-evals launch` command that runs a frozen record's cells, arms
interleaved, stopping on infrastructure failure and resuming a stopped night.

**run record**

The frozen JSON that names the task, arms, model, budgets, schedule, and the
decision rule, committed before any cell runs.

**attempt command**

The executable the harness runs in a cell to do the work — bare Pi for
Baseline, the Engine's `/implement` for the Engine arm.

**transcript**

The model's stream, preserved byte-for-byte, from which tool calls and usage
are read.

**patch**

The cumulative diff from the workspace's base commit, harvested after the
attempt — untracked files included, so a model `git commit` hides nothing.

**verdict**

The outcome of offline grading by the oracle test hook — pass or fail, never
an exit code or stdout.

**budget**

The token and turn limits that stop a cell, and the wall-clock backstop. A
cell that runs out of budget is graded, not discarded.

**census**

The classified set of Baseline cells run before any Engine work, to see where
an arm actually fails before building a remedy.
