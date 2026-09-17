# Disclosed, not fixed: gaps the whole-path review found in the hidden suite

`selfhost-preflight-quiet` is **frozen as cut** (maintainer ruling,
2026-09-18): `base` = `3f7a561931e4c4fabb79991756359d6d6c9c9aac`, `good` =
`f7459ef5a4ccece490c8a7cb48a8e0dfea713d6b`, `plan.commit` =
`3cd88a6ce1e6987293dfa638337d8594535bffd3`. It passed the R0 §1.2 validity
check (`verdict: pass`, 20/20; see the run tables in
`evidence/2026-09-17-census-2/validity/README.md`, which this page
supplements rather than replaces).

A whole-path review of the hidden suite (the fenced acceptance-test block
and the reference module, both extracted from the heading document
`docs/superpowers/plans/2026-09-18-preflight-quiet.md` at `3cd88a6`) found
four places where the suite is more lenient than the prompt's own prose.
Closing any of them means editing the heading document, which would move
`base`, orphan `good`, and re-open the R0 §1.2 certificate above — exactly
what the maintainer's freeze rules out. The maintainer's ruling is
therefore: **disclose these, and instrument them for the night's own
reading (`evidence/2026-09-18-census-3/postreg.md`); do not fix them.**
None of the four is a defect in `scripts/preflight_quiet.py` or in the
task's cut; each is a gap in what the **developer's tests** grade, against
what the **prompt's prose** states.

## I2 — the `ps`-line split rule is not graded

The prompt (Step 4) states the rule in prose: `busy_processes` "split[s]
each line into at most three fields." No fixture in the twenty-test suite
has a space in a `comm` value, so the suite's one malformed-line test
cannot distinguish `line.strip().split(maxsplit=2)` from a bare
`line.strip().split()` — both satisfy every assertion the suite makes.
**The prompt states the rule; the developer's tests do not grade it.**

### Re-run, 2026-09-17

Extracted the first fenced `python` block (lines 35-264 of the heading at
`3cd88a6`, the acceptance suite) and the five remaining fenced `python`
blocks (lines 280-481, the reference module in Step order) into
`$SCRATCH/i2-remeasure/`, cleared `__pycache__` between runs, and ran with
`PYTHONPATH` pointed at the extracted module:

```bash
$ PYTHONPATH="$SCRATCH/i2-remeasure" uv run pytest \
    "$SCRATCH/i2-remeasure/test_preflight_quiet.py" -q
....................                                                     [100%]
20 passed in 0.02s
```

Mutated only the one line (`fields = line.strip().split(maxsplit=2)` ->
`fields = line.strip().split()`) in a copy of the module, cleared
`__pycache__`, and ran the same suite against the mutant:

```bash
$ PYTHONPATH="$SCRATCH/i2-remeasure/mutated_run" uv run pytest \
    "$SCRATCH/i2-remeasure/mutated_run/test_preflight_quiet.py" -q
....................                                                     [100%]
20 passed in 0.02s
```

Reference module: **20 passed.** Mutant with plain `split()`: **20
passed.** Identical result; the suite cannot tell them apart.

### The consequence on a real snapshot

`ps -axo comm` prints paths containing spaces routinely on macOS, and the
prompt's own `IGNORE_PREFIXES` names `/Applications/oMLX.app/` — exactly
the `.app` family that has them. Against the mutant module:

```bash
$ PYTHONPATH="$SCRATCH/i2-remeasure/mutated_run" uv run python3 -c "
from preflight_quiet import busy_processes, IGNORE_PREFIXES
PS = '  PID  %CPU COMM\n  977  93.1 /Applications/Google Chrome.app/Contents/MacOS/Google Chrome\n'
print(busy_processes(PS, cpu_floor=20.0, ignore_prefixes=IGNORE_PREFIXES))
"
[]
```

A process at **93.1% cpu is reported as not busy.** Plain `split()` yields
five fields on that line; the module's `len(parts) != 3` guard treats it as
malformed and skips it; `busy_processes` returns `[]`. The check **declares
a loud machine quiet** — the one failure mode this task exists to prevent.

### Direction

Leniency. A cell that writes a bare `split()` — a natural, unforced choice,
not an adversarial one — scores 20/20 on the hidden suite exactly as a
correct `split(maxsplit=2)` would. The measured admission rate for a
correct check is therefore, if anything, an **over-estimate**: some cells
counted as full passes may carry this miss.

## Three more parked literals, same class

Each is prose-stated in the heading and ungraded by the suite, confirmed by
both the controller's own extraction and the whole-path review:

- **P1 (one-decimal formatting).** The `load` and `decode` messages are
  specified to format their numbers to one decimal place (Steps 3 and 6).
  Every fixture value already has exactly one decimal digit, so `f"{x}"`
  and `f"{x:.1f}"` produce the same string on every fixture and the suite
  cannot tell them apart.
- **P3 (`inputs` key set).** Step 6 specifies that `as_dict()["inputs"]`
  carries "exactly" a named set of keys. The suite asserts each key's value
  individually and never asserts the key set itself, so an implementation
  that adds a spurious key to `inputs` still passes.
- **P4 (CLI `last` plumbing).** Step 7 specifies that the parsed `--last`
  is passed through to `certificate`. The quiet CLI test passes `--last 2`
  but asserts only `inputs.decode.completions`, never `inputs.last`, so a
  `main` that hardcodes `DEFAULT_LAST` into that call instead of the parsed
  value still passes; `--model`'s `required=True` is likewise asserted by
  no test.

## Where this is counted

`evidence/2026-09-18-census-3/postreg.md` is the pre-registered read that
counts all four parked literals (`maxsplit`, `one_decimal`, `inputs_keys`,
`cli_last`) against every retained night-3 cell's harvested patch, written
and committed before the night runs. Per that page's own load-bearing
rule, none of the four columns changes a verdict, a pass count, or a
classification — the night's verdict comes from the hidden suite via the
receipt, exactly as for the other five census tasks.

## For the census page (quotable verbatim)

> The hidden suite does not grade `busy_processes`'s three-field split
> rule, so a cell whose check uses a bare `split()` is graded a pass
> identical to one that implements the stated rule; counted, not
> corrected, in `evidence/2026-09-18-census-3/postreg.md`.

---

This page is cross-referenced from
`evidence/2026-09-17-census-2/validity/README.md`. See that page for the
task's overall run history, leak-tell checks, and the two prior heading
edits (F1, F2) and the `Certificate.as_dict` `Produces:`-count note; this
page covers only the disclose-not-fix findings named above.
