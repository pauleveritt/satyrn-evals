# Architecture

V1 is the grading seam the rest of the roadmap builds on. One command,
seven small modules, two test tiers.

## Data flow

```
PATCH ──► parse ──► allowlist ──► copy base ──► git apply ──► oracle ──► hook result ──► verdict ──► receipt
              │                                                        (unique path)
              ▼
         manifest
```

`grade()` in `src/satyrn_evals/grade.py`:

1. **Load the manifest** — `manifest.py` validates the {term}`task`'s
   {term}`manifest` (`manifest.json`): contract, {term}`oracle` command,
   expected test IDs, source {term}`allowlist`, fixture {term}`patch`
   paths.
2. **Read and vet the patch** — `patch.py` parses the unified diff,
   extracts the touched paths, and checks the {term}`allowlist`; a
   {term}`patch` touching anything else is rejected before anything runs.
3. **Materialize and apply** — the {term}`task`'s base state is copied to a
   temp directory, `git init` + `git apply` apply the {term}`patch`.
4. **Run the oracle** — the {term}`manifest`'s {term}`oracle` command (for
   `format_number`, `python -m pytest -p satyrn_evals.oracle_hook`) runs
   in the workspace with a *unique, reserved-but-unlinked* hook-result
   path in its environment. The hook's `pytest_sessionfinish` writes the
   {term}`hook result` JSON.
5. **Load and validate the hook result** — `verdict.py` rejects a missing,
   stale, unparseable, or internally inconsistent file as `unavailable`.
6. **Compute the verdict** — executed test IDs must equal the
   {term}`manifest`'s expected IDs; any skip means `unavailable`; any
   failure or error means `fail`; all pass means `pass`.
7. **Write the receipt** — `receipt.py`; the CLI maps the {term}`verdict`
   to an exit code (0 / 2 / 3).

The {term}`oracle`'s stdout and exit code are discarded. The
{term}`receipt` — not the process result — is what a caller reads.

## Why the verdict comes from a hook file

Predecessor graders were defeated twice by a clean zero that proved
nothing: `addopts = --collect-only` made pytest collect without running a
single test, and an import-time `os._exit(0)` killed the process before
anything ran. Both produce exit code 0.

The defense is structural, not behavioral:

- the {term}`oracle` command is fixed in the {term}`manifest`, and the
  {term}`allowlist` stops a {term}`patch` from adding `addopts` or
  replacing the hook;
- the hook writes to a path the {term}`patch` cannot predict — and the
  path is unlinked before the oracle runs, so a silent oracle leaves *no*
  file;
- a missing, stale, empty, or inconsistent file is `unavailable`, never
  `pass`;
- the executed-vs-expected-ID guard means "tests ran" is checked, not
  assumed.

## Modules

| Module | Responsibility |
|--------|----------------|
| `cli.py` | argparse, `grade` command, exit-code mapping |
| `grade.py` | orchestration: materialize, apply, run oracle, write receipt |
| `manifest.py` | load/validate the {term}`task` {term}`manifest`; resolve tasks by name |
| `patch.py` | parse unified diffs; enforce the source {term}`allowlist` |
| `verdict.py` | load/validate the hook result; compute the verdict |
| `receipt.py` | the durable grading artifact (JSON) |
| `oracle_hook.py` | pytest plugin writing the trusted hook result |
| `errors.py` | error hierarchy carrying exit codes (usage 2, operational 3) |

## Testing: two tiers and the tripwire

- **Default tier** — no model, no network, no subprocess, enforced by the
  {term}`tripwire`: a CPython audit hook in `tests/conftest.py` that
  raises on any spawn. Weakening it fails the build.
- **Integration tier** — marked `integration` and excluded from the
  default run: real `git apply`, real oracle subprocesses, and the
  {term}`evidence floor`: the bundled {term}`task`'s known-good
  {term}`patch` is accepted and its known-broken {term}`patch` rejected,
  each asserted by naming the fixture.

Every refusal test has a sibling success test, so rejection cannot pass
vacuously.

## What is not here yet

- capture by revert — V2
- the {term}`attempt command` and {term}`preservation` — V3
- the real engine seam — V4
- the diagnostic loop — V5
- the {term}`baseline probe` — with the attempt loop

One phase at a time; no machinery ahead of the contract it serves.
