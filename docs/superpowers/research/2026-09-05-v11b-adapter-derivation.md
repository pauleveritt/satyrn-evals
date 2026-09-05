# V11b — where the Baseline adapter came from, and what changed

**Date:** 2026-09-05. Plan task 1 of
[`2026-09-05-v11b-trim.md`](../plans/2026-09-05-v11b-trim.md); spec
[`2026-09-05-v11b-trim-arm-substrate-design.md`](../specs/2026-09-05-v11b-trim-arm-substrate-design.md).

The scratch wrapper this adapter replaces carries a recorded warning —
"minor drift between this recorded source and the executable is a
recording defect, not a re-run"
([reprobe protocol](2026-09-03-local-pings-reprobe-protocol.md)). So this
file records the derivation deliberately: what was carried over, what was
changed on purpose, and why. Nothing here is recalled; each claim names a
file or a recomputable command.

## 1. What was read

| Source | What it settled |
|---|---|
| [`2026-09-03-local-pings-reprobe-protocol.md`](2026-09-03-local-pings-reprobe-protocol.md) | The wrapper's exact pi flag set, the space-form `--model` note, and the invalid-YAML smoke incident |
| [`2026-09-04-v8-agentclinic-smoke.md`](2026-09-04-v8-agentclinic-smoke.md) | The one-character `--model=` vs `--model ` reproduction, and that a smoke's job is to find plumbing defects at a cost of one attempt |
| `src/satyrn_evals/adapters/pi_session.py` | Stream handling, `--pi-bin`, `stderr=DEVNULL`, and the split between a verifiable core and a thin `main` shell |
| `src/satyrn_evals/adapter_process.py` | Process lifetime and group teardown — read, and **not** used; see §4 |
| `src/satyrn_evals/attempt.py` | The seam's real variable names |

## 2. Carried over unchanged

- **The pi flag set**, token for token, from the recorded wrapper:
  `--print --mode json --no-session --model <m> --no-extensions
  --no-skills --no-prompt-templates --no-themes --no-context-files
  --no-approve --tools <joined> <prompt>`
  (`src/satyrn_evals/attempt_pi.py`, `build_pi_argv`).
- **Space-form `--model`.** pi 0.84.4 matches the literal token `--model`
  and records `--model=VALUE` as an unknown flag. The adapter refuses the
  equals form at its own boundary too, so the trap cannot re-enter through
  an arm file.
- **Prompt from `SATYRN_TASK_CONTRACT`, diff harvested after pi exits.**
- **`--pi-bin`**, from the session adapter, so an integration test can put
  a fixture where pi would be.

## 3. Deliberate changes from the recorded wrapper

1. **The seam's variable names are the real ones.** The spec's prose says
   `SATYRN_PATCH` / `SATYRN_TRANSCRIPT`; `attempt.py:37-40` exports
   `SATYRN_TASK_NAME`, `SATYRN_TASK_CONTRACT`, **`SATYRN_ATTEMPT_PATCH`**
   and **`SATYRN_ATTEMPT_TRANSCRIPT`**. The adapter reads the exported
   names, and `tests/test_attempt_pi.py::test_the_adapter_reads_exactly_the_names_attempt_exports`
   pins its three constants to `attempt.py`'s, so a rename on either side
   fails the build instead of stranding the adapter silently.

2. **pi's stderr goes to `DEVNULL`, not into the transcript.** The recorded
   wrapper used `stderr=subprocess.STDOUT`. V10's parser refuses a whole
   cell on one non-JSON line — `json.JSONDecodeError` →
   `_unmeasured("unparseable")` (`src/satyrn_evals/pathology.py:88-89`) —
   so folding stderr in would make any cell whose pi printed one warning
   `measured: false`. That directly defeats the spec's §8 vocabulary duty.
   The shipped session adapter already chose `DEVNULL`
   (`adapters/pi_session.py`, `main`), so this aligns the two adapters
   rather than inventing a third behaviour.
   **The cost, stated:** a pi diagnostic on a failed cell is not retained.
   Evals discards the attempt command's stdout/stderr as well
   (`workspace.py:748-754` writes them to temporary files under the
   workspace parent), so no adapter choice preserves them today; retaining
   them would be a change to the *attempt record*, which V11b does not own.
   `tests/integration/test_attempt_pi.py::test_adapter_delivers_a_patch_and_a_json_only_transcript`
   makes the fixture write to stderr and asserts the transcript still
   parses line by line.

3. **`git diff HEAD` failure refuses instead of writing "".** The recorded
   wrapper wrote `diff.stdout` unconditionally, so a git failure would have
   delivered an empty patch — which downstream reads as the legible
   outcome `NO_PATCH` rather than as a fault. `harvest_patch` raises.

4. **The equals form, `--rung`, unknown flags and a second positional are
   refusals with messages**, where the wrapper used `argparse` defaults.
   `--rung` is refused by name because spec §3 makes its absence the seam
   that keeps V11a and V11b independent; a silent accept would erode that
   without anyone noticing.

5. **No `assert` for validation.** The wrapper used
   `assert args.model, "SATYRN_MODEL required"`, which `python -O` removes.

6. **`SATYRN_MODEL` is not read.** The wrapper defaulted `--model` from the
   environment. The arm file is the record of what ran, and an environment
   default is exactly how a cell silently runs a different model from the
   one the schedule names. The model is a required argument.

## 4. What was read and deliberately not reused

`adapter_process.AdapterProcess` — line deadlines, `start_new_session`,
SIGTERM→SIGKILL group teardown — exists because the **session** executor
owns a long-lived conversation it must be able to interrupt between
prompts. The Baseline adapter runs one pi invocation to completion and
exits; Evals' own workspace runner already owns the timeout and the group
teardown for the attempt command (`workspace.py:729-800`). Reusing
`AdapterProcess` here would add a second, redundant teardown path with no
caller that needs it — `CLAUDE.md`: no framework before three concrete
implementations need the same shape.

## 5. The pins, and the commands that recompute them

Computed on 2026-09-05 from the checkout at
`/Users/pauleveritt/projects/pauleveritt/satyrn-engine`, whose working tree
was clean (`git status --porcelain` printed nothing) at the time.

```console
$ git -C ~/projects/pauleveritt/satyrn-engine status --porcelain | wc -l
       0
$ git -C ~/projects/pauleveritt/satyrn-engine rev-parse HEAD
75d486327c513d8e686d5e346c59092548d88a15
$ cd ~/projects/pauleveritt/satyrn-engine \
    && shasum -a 256 packages/engine/engine.ts packages/engine/mutator.ts
41ed48c386d9359b199121dec15b50f8b05bb46662a6816f407f6e60d7509c5a  packages/engine/engine.ts
a08d6dea63fdd382532259a26d178dabc0a8ba499b7c6adcdb56d6ba07e06168  packages/engine/mutator.ts
$ pi --version
0.84.4
```

Cross-checked against the committed blobs, so a checkout filter cannot
have altered what was hashed:

```console
$ cd ~/projects/pauleveritt/satyrn-engine \
    && git cat-file blob HEAD:packages/engine/engine.ts | shasum -a 256 \
    && git cat-file blob HEAD:packages/engine/mutator.ts | shasum -a 256
41ed48c386d9359b199121dec15b50f8b05bb46662a6816f407f6e60d7509c5a  -
a08d6dea63fdd382532259a26d178dabc0a8ba499b7c6adcdb56d6ba07e06168  -
```

`scripts/preflight.sh` re-runs all four checks before a batch, so the pins
are verified rather than trusted.

**Why these two files.** They are the two `--extension` paths
`satyrn-engine`'s `build_pi_command` hands pi
(`satyrn-engine/src/satyrn_engine/attempt.py`, `build_pi_command`, at the
pinned commit), which is also where `--tools read,edit` — the Engine arm's
tool surface — is fixed. The arm files record that surface; they do not set
it.

## 6. What this does not establish

Nothing here has run a model. The adapter is proven against a fixture pi
and real Git only. The two V5d smokes required by spec §8 are the first
evidence that either arm runs, and they are behind the maintainer gate
that V11b does not open.
