# Glossary

This is optional lookup material, not a prerequisite for running a task. It
defines the small vocabulary used to interpret an evaluation.

```{glossary}
:sorted:

allowlist
  The patch-writable path set in a task manifest (`source_paths`). It does not
  promise that tests are immutable when the manifest allows `tests/`; hidden
  overlay checks are protected separately.

arm
  An executor configuration. It is not the complete evaluation condition.

attempt
  One invocation of an {term}`attempt command`, with whatever patch,
  transcript, and grading evidence Evals retained. An attempt can refuse or
  time out.

attempt command
  The executable command Evals invokes to produce a patch. It is the engine
  seam: Evals does not import engine internals.

batch / run
  A declared group of attempts and the execution that carries it out. It has
  an explicit planned denominator.

cell
  A planned attempt slot in a batch.

evaluation condition / configuration
  The complete frozen choice of task, prompt or rung, executor command, model,
  tools, limits, and relevant revisions.

headroom
  Remaining useful separation for one frozen task-condition-budget
  combination. It is not a permanent task label.

hook result
  Structured test evidence written by the oracle hook. It is the source for a
  {term}`verdict`; stdout and an exit status are not.

public suite / hidden checks
  Feedback available to the solver / independent checks used to derive a
  verdict.

qualification
  Evidence that one task-condition can measure its stated requirements.

receipt
  A saved grading artifact containing a verdict and its hook evidence.

result
  The recorded outcome, including the verdict when available, missingness, and
  links to retained evidence.

rung
  A named prompt form for a task.

task
  A starting project, requested change, and declared checks.

verdict
  The hook-derived `pass`, `fail`, or `unavailable` judgment.
```

Storage-schema and development terms are defined in [task and artifact
formats](reference/formats.md) and [architecture](architecture.md) where they
are needed.
