> **Archived pre-reset record (2026-09-07).**
>
> Original claims, decisions, and instructions may be superseded. This file is evidence, not current guidance.
> For current guidance, read root AGENTS.md, BRIEF.md, and ROADMAP.md. Retrieve one named record when it bears on a concrete question; do not preload this archive.

# Decision: pi's context window is corrected to 80,000

**Decided and recorded 2026-09-05, before the next batch**, as
`CLAUDE.md` requires of any inference setting.

## What changed

`~/.pi/agent/models.json`, the `gemma-4-12B-it-MLX-8bit` entry:
`contextWindow` 262,144 → **80,000**, the limit the omlx server actually
enforces. `arms/baseline.json` and `arms/engine.json` record the same
number, so preflight check 0c refuses any batch where the two disagree.

Until now pi believed it had 262,144 tokens against a server that killed
the request at 80,000, so pi's compaction could never fire first.

## Why, given that it does not change who succeeds

The compaction probe
(`~/satyrn-smokes/2026-09-05-compaction-probe-214218/RESULT.md`) tested exactly that and found
no rescue: 5 of 6 cells locked, none recovered, all ran past the old
285-turn wall and timed out still looping. So this is not a correctness
fix — it is a truthfulness one. Two things it does change, both measured
rather than assumed:

- **Cells get slower**, roughly 15 minutes against 10, because a 900 s
  timeout replaces a 285-turn wall. The lever on batch cost is the
  repeated-call spending rule (`--max-repeated-calls`), not this.
- **The recorded failure code changes**, `COMMAND_TIMEOUT` where the
  V11c spike recorded `NO_PATCH`.

The setting is corrected anyway because a configuration that lies about
its own limit is the kind of lurking condition that gets rediscovered as
a finding — which is precisely what happened on 2026-09-05, when a frozen
mismatch was reclassified as an instrument failure after a count was read.
A recorded, checked setting cannot be rediscovered.

## The comparability caveat

**Successful-attempt counts stay comparable** across this change: the
probe showed the same cells fail either way. **`code_counts` do not.** A
batch run after this date records `COMMAND_TIMEOUT` for a pathology that
earlier batches recorded as `NO_PATCH`, and the V5d smoke practice treats
those two differently. Any table pooling batches across this boundary
must say which side each batch is on.

## Reversal

Backup of the pre-change file:
`~/satyrn-smokes/models.json.backup-before-correction-20260905-231005`.
Reversing means editing both arm records back as well — check 0c will
refuse the batch otherwise, which is the point.
