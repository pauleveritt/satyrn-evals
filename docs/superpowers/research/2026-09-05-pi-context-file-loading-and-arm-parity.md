# Pi context-file loading, a retracted attribution, and an arm-parity finding

**Date:** 2026-09-05. **Status:** a recorded correction plus one open
question. Feeds `arms/*.json` (V11b-trim) and the Envelope cap decision
deferred in
[`the V11 trim proposal`](2026-09-05-v11-trim-and-spike-proposal.md) §2.4.

## 1. The correction, recorded rather than edited away

An earlier claim in this session attributed a **13,645-token** input count to
"pi's system prompt and tool schemas."

**That was wrong**, and wrong in the direction that matters: the tokens were
**project context introduced by running `pi` from the repository root**, not a
fixed property of the tool. Attributing our own context to the vendor's floor
would have made every later per-cell budget estimate wrong in the same
direction, and would have inflated any Envelope cap argued from it.

`CLAUDE.md`: *a correction is recorded, not edited away.*

## 2. The measurement

Same model, same trivial prompt, three calls:

| cwd | flags | input tokens |
|---|---|---|
| empty directory | default | 1,267 |
| `satyrn-evals` repo root | default | 9,753 |
| `satyrn-evals` repo root | `-nc` | **686** |

`pi --help` documents `--no-context-files, -nc` as "Disable AGENTS.md and
CLAUDE.md discovery and loading."

So roughly **93%** of the repo-root call was context-file discovery, and
**pi's own floor — system prompt plus tool schemas — is about 686 tokens.**

## 3. What this does *not* explain — stated, not papered over

Two things remain unresolved, and neither should be guessed at in a later
document:

1. **The arithmetic does not close.** `CLAUDE.md` is 5,040 bytes (~1,260
   tokens) and the home files total ~3 KB. That does not account for ~9,000
   tokens. **Something else is being pulled in and we do not know what.**
2. **The same directory gave 13,645 on one call and 9,753 on another.**
   Unexplained.

Both need a stream capture that was not obtained. Until it is, no number in
this section may be used as a budget input.

## 4. Why this mostly does not affect the plan

Real attempts do not run in the repository root. `run_workspace`
materializes a clean Git workspace from the task's `base/` and the adapter
runs **there**, so a cell's context should sit near the 686–1,267 floor plus
actual task content. **The 13.6k figure was an artifact of test location, not
a property of the arms.**

## 5. Two things that follow anyway

### 5.1 An undetected contamination surface

A stray `AGENTS.md` or `CLAUDE.md` in some future task's `base/` would
**silently inject instructions into the model's context, and nothing would
flag it.** The V7/V8 contamination detector scans for **grader overlay
text**, not for instruction files, so this surface has no detector at all.

Pinning `-nc` closes it by construction, which is cheaper than building a
second detector. Backlog entry owed with its reopen condition.

### 5.2 The arms are not at parity today — and the protected arm is Engine

`satyrn-engine`'s hermetic child argv already passes `--no-context-files`,
alongside `--no-extensions`, `--no-skills`, `--no-prompt-templates` and
`--no-themes`:

```
satyrn-engine/src/satyrn_engine/attempt.py:240-264   build_pi_command()
```

Recomputed with:

```bash
sed -n '240,264p' ~/projects/pauleveritt/satyrn-engine/src/satyrn_engine/attempt.py
```

at engine `main` = `75d4863`, clean tree.

The scratch Baseline wrapper carries **no such flag**. Pi's context-file
discovery includes **home** files, so a Baseline cell in a materialized
workspace still loads ~3 KB that the Engine cell is hermetically shielded
from.

**This is `BRIEF.md` rule 8's shape — "an arm protected from a harness defect
its rivals were exposed to" — with Engine as the protected arm.** It applies
retrospectively to the eight preserved 2026-09-03 Baseline reprobe cells.

**It does not invalidate the de-admission.** `local-pings` was de-admitted
because Baseline 3/8 and Engine 4/8 occupied the **same band**
([record](2026-09-03-local-pings-deadmission.md)) — a conclusion an
extra ~3 KB of Baseline context does not overturn in either direction. The
finding is recorded because an undocumented asymmetry is the thing rule 8
exists to catch, not because a published number changes.

**Consequence for V11b-trim:** pin `-nc` in `arms/baseline.json` for **two
independent reasons** — the undetected instruction-file surface (§5.1) and
**arm parity** (§5.2). No Engine change is owed.

## 6. Owed measurement

`scripts/preflight.sh` must record the **real per-cell input-token floor,
measured from inside a materialized workspace**, during the V5d smokes — not
from the repository root, and not as an estimate.

That number is the input to the Envelope cap decision (proposal §2.4), where
the spec already says the cap "is a fresh choice that must be argued." An
argued cap built on §2's repo-root figures would inherit exactly the error
§1 retracts.
