# `--session-spec` selector

## What changed

- `src/satyrn_evals/session_manifest.py:68-92` — new `_check_spec_name`:
  refuses (each with its own `SessionSpecError` message) a name that
  doesn't end `.json`, is absolute, contains a `..` path segment, or
  contains any separator (`Path(name).name != name`).
- `src/satyrn_evals/session_manifest.py:95-98` — `load_session_spec` gained
  `spec_name: str = "session.json"`, calls `_check_spec_name` first, then
  loads `task_dir / spec_name`. All internal error strings still say
  literally `"session.json"`, so every existing single-arg caller (grep
  confirmed 30+ call sites across `tests/`) is byte-identical.
- `src/satyrn_evals/session.py:243-249` — `run_session` gained
  `session_spec: str = "session.json"`, passed through as
  `load_session_spec(task_dir, spec_name=session_spec)`. No second load path.
- `src/satyrn_evals/cli.py:309-348` — `session` subparser gained
  `--session-spec` (default `"session.json"`); the `session` branch threads
  `args.session_spec` into `run_session(...)` (`cli.py:139`).

No new task directory, no touch to `tasks/agentclinic-session-phased/`, no
prompt content authored.

## Tests

- `tests/test_session_manifest.py` — success:
  `test_session_spec_name_loads_a_named_file` (default loads
  `session.json`'s first step id, `spec_name="other.json"` loads the other
  file's). Refusals (parametrized, each asserting the raise):
  `sub/other.json` → "bare filename", `../other.json` → "traverse",
  `/etc/passwd.json` → "absolute", `other.txt` → "\.json".
- `tests/test_cli_session.py` — `test_session_spec_flag_threads_to_run_session`
  (sibling of the existing `test_session_exit_code_mapping`, which now also
  asserts `seen["session_spec"] == "session.json"`).

## Discrimination transcript

Commented out `_check_spec_name(spec_name)` at `session_manifest.py:97`,
reran `pytest tests/test_session_manifest.py -k "traversal or refusals"`:

```
4 failed, 10 passed, 14 deselected in 3.45s
FAILED ...refusals[sub/other.json-bare filename]  -> got "cannot read session.json: ...No such file..."
FAILED ...refusals[../other.json-traverse]        -> got "cannot read session.json: ...No such file..."
FAILED ...refusals[/etc/passwd.json-absolute]      -> got "cannot read session.json: ...No such file..."
FAILED test_session_spec_name_traversal_cannot_read_outside_task_dir
    -> Failed: DID NOT RAISE SessionSpecError
```

The traversal test's failure mode is the important one: with validation
disabled, `load_session_spec(task_dir, spec_name="../secret/session.json")`
did not raise at all — it successfully resolved to the sibling
`secret/session.json` and returned its (`"exfiltrated"`-tagged) steps. That
is the actual escape the guard exists to prevent, not a proxy for it.
Restored the line; reran the same file — `39 passed in 0.34s`.

## Full validation

- `uv run pytest tests/test_session_manifest.py tests/test_cli_session.py -q`
  → `39 passed`
- `uv run pytest -q` → `1467 passed, 341 deselected` (0 failures; the 5
  known pre-existing integration failures live in the deselected
  integration tier and were not run)
- `just gates` → exit 0 (pytest, ruff check, lint-docs, docs all green)

## Concerns

- On POSIX, "absolute" and "traverse" checks are reachable independent of
  the separator check only because the check order deliberately puts
  suffix → absolute → traversal → bare-filename, so each fires before the
  generic separator catch-all would mask it with a less specific message.
- Did not add a fixture spec file to the shared `mini-session` integration
  task; the CLI-level test only proves the flag threads through (via a
  monkeypatched `run_session`), not an end-to-end read against a real
  second spec file in a bundled task. `load_session_spec`'s own tests cover
  the real read.
