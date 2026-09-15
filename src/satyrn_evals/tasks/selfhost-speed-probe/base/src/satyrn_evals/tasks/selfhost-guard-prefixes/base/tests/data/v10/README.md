# V10 pathology fixtures

Synthetic-but-faithful Pi stream-JSON (version 3) documents in the
vocabulary the [archived V10 record](https://github.com/pauleveritt/satyrn-evals/blob/d900325/docs/superpowers/specs/2026-09-04-v10-transcript-pathology-counts-design.md)
pins (§1).
Synthesized from the verified schema, **not** byte-copied from the
preserved V8 smoke transcript (the deep review's §11 sample).

- `good-repair.jsonl` — the faithful-good document. Counting it with
  `count_transcript(text, had_patch=True)` reproduces the spec's §3
  validation row exactly (`tool_calls {read: 6, edit: 2}`, `repeats: 4`,
  `churn: 0`, `noop_edits: 0`, `test_runner_commands: 0`,
  `tool_free_terminal_turns: 0`, `workspace_escapes: 0`, `loop_broken: 0`);
  the spec's §12
  breaks the row down (`read tests/test_app.py` ×3 +2, `read app.py` ×2
  +1, identical `edit app.py` ×2 +1).
