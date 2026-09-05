# The two-arm substrate

An **arm** is one complete command surface a task can be attempted under:
an executable, its flags, its tool surface, the model it addresses, and the
versions and file digests that were true when it ran. This page describes
the committed arm definitions, the Baseline attempt adapter, and the three
scripts that run a batch around them.

Nothing here has run a model. The substrate exists so that a later batch is
reproducible; it measures nothing, and no number in this project comes from
it yet.

## The `arms/` directory

`arms/baseline.json` and `arms/engine.json` are the record of what each arm
is. They are read by `satyrn_evals.arms`, so they are executable inputs
rather than a second description that can drift from the code.

```json
{
  "arm": "baseline",
  "argv": ["satyrn-evals-attempt-pi"],
  "tools": ["read", "bash", "edit", "write"],
  "model": "omlx/gemma-4-12B-it-MLX-8bit",
  "server_model": "gemma-4-12B-it-MLX-8bit",
  "pins": {"pi": "0.84.4", "engine_commit": null, "digests": {}}
}
```

- **`model` and `server_model` are both recorded** because they differ. `pi`
  is addressed with the provider-qualified `omlx/<id>`; the local server
  advertises the bare id, and that is the name a preflight completion uses.
  The reader refuses a file whose two names disagree.
- **`pins` are what a preflight re-verifies.** Baseline pins `pi`. Engine
  additionally pins the engine commit and the sha256 of `engine.ts` and
  `mutator.ts` — the two `--extension` files the engine hands `pi`. A
  commit pin alone would not catch an edited file in a matching checkout,
  so both are checked.
- **The reader refuses an under-specified file.** A missing pin, an unknown
  tool name, an empty `argv`, an engine commit that is not a 40-hex sha, a
  digest that is not a 64-hex sha256, or a pin that cannot apply to that arm
  is an error at load, not a value quietly defaulted. There is no partially
  pinned arm.
- **There is no registry and no discovery.** Two files and one reader; a
  caller names a path.

`satyrn_evals.arms.build_argv` turns an arm into the attempt command Evals
invokes. The model is always two tokens, never `--model=VALUE`: `pi` 0.84.4
matches the literal token and records the equals form as an unknown flag.

## The Baseline adapter

`satyrn-evals-attempt-pi` (`satyrn_evals.attempt_pi`) runs one
`pi --print --mode json` turn inside the workspace Evals allocated:

- the prompt is the contract text Evals exported in `SATYRN_TASK_CONTRACT`;
- `pi`'s stream-JSON goes to `SATYRN_ATTEMPT_TRANSCRIPT`;
- after `pi` exits, `git diff HEAD` goes to `SATYRN_ATTEMPT_PATCH`;
- the adapter returns `pi`'s exit code, having written both artifacts first.

**The adapter takes no `--rung`.** The rung reaches it as the contract text,
which is what keeps the evidence ladder and the arm substrate independent of
each other; passing `--rung` is refused by name.

`pi`'s stderr goes to `DEVNULL`. One non-JSON line in the transcript makes
the offline pathology reader report the whole cell as unmeasured, so a
diagnostic must not share that stream. The cost — a lost `pi` diagnostic on
a failed cell — is recorded in
[the adapter derivation](../superpowers/research/2026-09-05-v11b-adapter-derivation.md).

## The three scripts

`scripts/` is instrument. It sits outside the package and outside the
coverage gate's measured path, and it is covered by tests all the same.

**`preflight.sh`** — run before the first cell of a batch. It asserts the
engine checkout is exactly the pinned commit with a clean tree, that both
extension sources hash to their pins, and that `pi` is the pinned version;
it records the Evals commit and refuses a dirty Evals tree; and it writes
the realized arm order before anything runs. Every pin is read out of the
arm files rather than restated in the script.

Its model check is **a live one-word completion, never a model listing**. On
2026-09-05 the local server advertised a model whose weights were nowhere on
the machine, and the listing was cleared later the same session. A listing is
not evidence that a cell can run; only text coming back is.

**`interleave.py`** — builds the seeded, balanced arm order and creates
**one directory per expected cell**. `run` cannot interleave arms, and
`summarize` needs a `summary.json` anchor in the directory it reads, so
repeated `run --n 1` calls into a single directory would overwrite that
anchor. The seed is recorded beside the order so the order can be rebuilt,
and the whole schedule — task, rung, contract digest, model, and each
cell's exact argv — is written before the first cell.

**`tally.py`** — reads exactly the scheduled `summary.json` set and reports
counts per arm. It **refuses** rather than shrinking a denominator: a
missing cell, an aborted cell (`aborted.json`), an unreadable summary, a
duplicated attempt cell, a stray unscheduled directory, or a cell recorded
at the wrong task, rung, contract digest, model, or arm. All discrepancies
are reported together, and a refused batch produces no counts at all.

Contamination is not a refusal. A flagged cell stays **in** the denominator
and is reported beside it.

## Stated limits

- **`git diff HEAD` drops files created with `write`.** Untracked files are
  invisible to it. This is harmless on pure-edit repair and fatal for build
  shapes and for tasks that require creating a file. `git add -A` is not the
  fix — it would sweep a model's `uv run pytest` residue into the patch and
  trip the allowlist check. Creation-capable capture is an entry gate for a
  later phase; until then, a task that needs it must not be measured on this
  adapter, or the adapter's limit would be recorded as model behaviour.
- **A timed-out cell retains no patch.** The diff is harvested only after
  `pi` exits. Report that beside retained-patch production, and never read a
  completion floor under this adapter as a capability wall.
- **Counts only, never durations.** Two figures in the predecessor project
  were retracted for comparing wall-clock time between contiguous arms.
- **The tool surface is a predeclared confound.** Baseline holds
  `read,bash,edit,write`; Engine holds `read,edit` and wraps its prompt with
  its own handoff builder. A comparison between them is meaningful only as
  "the shipped Engine versus bare Pi as shipped" — a product-level
  comparison, which supports no sentence about which component caused a
  difference.
