---
title: About Satyrn Evals
---

# About Satyrn Evals

## Why

Small models need help, and help is only help if you can measure it. Before
Satyrn, we built remedies for failures we had not diagnosed — and the failures
turned out to be our own harness's. Evals exists so a claim about a model or
an engine is a measurement, not a story.

## How

Evals captures a task, runs an attempt command in an isolated workspace,
preserves the patch and transcript, and grades the retained evidence offline.
The engine seam is an executable command, so the suite runs against a fake
command and never imports engine internals.

## What

Tasks, isolated cells, a launcher, grading from retained evidence, and the
census that classifies where an arm actually fails. The vocabulary is the
[glossary](glossary.md); the physical run is the
[architecture](evals-architecture.md).
