# See one verdict

In a few minutes, you will grade the bundled `format_number` change and read
the `pass` verdict that Evals records. This exercise uses no model and needs no
network access from Evals.

## Before you begin

You need a checkout of this repository, [uv](https://docs.astral.sh/uv/), and
Python 3.14. Run the commands below from the checkout root.

## 1. Install the project environment

```console
$ uv sync
```

You now have the project and its test dependencies in `.venv`.

## 2. Grade a known-good change

Make a temporary directory for the result, then ask Evals to grade the bundled
patch. `format_number` is a small task: its change adds thousands separators
to a Python function.

```console
$ RESULT_DIR="$(mktemp -d)"
$ uv run satyrn-evals grade format_number \
    src/satyrn_evals/tasks/format_number/fixtures/known-good.patch \
    --receipt "$RESULT_DIR/receipt.json"
```

The command completes with exit status `0`. That only tells you that grading
completed; the receipt is the result.

## 3. Read the result

```console
$ uv run python -c 'import json, sys; print(json.load(open(sys.argv[1]))["verdict"])' \
    "$RESULT_DIR/receipt.json"
pass
```

You have seen the whole first loop: a candidate patch was graded against a
task's tests, and Evals saved a receipt that names the verdict and evidence.
Open `$RESULT_DIR/receipt.json` to see the test IDs and outcomes behind this
`pass`.

## What to notice

The word **receipt** names the durable JSON result. The word **verdict** is its
`pass`, `fail`, or `unavailable` field. You do not need the rest of Evals'
vocabulary to repeat this exercise.

To see what actually happened under the hood — the agent, its tools, and the model
behind it — read [what actually happens when an agent works](../what-actually-happens.md).

When you are ready to run a real command that produces a change, continue to
[evaluate one attempt](../guides/evaluate-an-attempt.md). For the reasoning
behind the receipt, read [trust boundaries and limits](../topics/trust-boundaries.md).
