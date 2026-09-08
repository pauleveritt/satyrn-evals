# Qualifying session-ordering-regression

Written 2026-09-08, after a live Baseline session failed every checkpoint from
step 1 on. This task had been authored as a **grader fixture** and then run as
a **diagnostic workload** without qualification — the two jobs `BRIEF.md`'s
selection rules keep apart. This note is the missing half.

## What went wrong

The hidden checks demanded two things the prompts never stated:

| requirement | hidden check | the prompt said |
|---|---|---|
| ellipsis is `…` (U+2026), counted **inside** `width` | `summarize(…, 8) == "Hello w…"` | "a trailing ellipsis" |
| the first sentence has terminal punctuation **stripped** | `summarize(…, 20) == "Hello world"` | "the first sentence" |

A solver returning `"Hello..."` at `width-3`, keeping the period, is reading the
prompt correctly. Ordinary code reasoning is allowed here; hidden requirements
are not.

**The fix is in the prompt, not the checks.** Relaxing the hidden tests would
have invalidated the three committed checkpoint patches, which are this task's
witness and were written to satisfy them.

## The mapping

Every hidden check, and where the accessible text establishes it.

| hidden check | requires | stated in |
|---|---|---|
| `test_summarize_cuts_with_marker` | first sentence, punctuation dropped; whitespace collapsed; exactly `width` chars ending `…` | step 1 prompt |
| `test_summarize_collapses_internal_whitespace` | whitespace collapsed like `normalize`; no ellipsis when not cut | step 1 prompt ("collapse whitespace the way normalize does", "Otherwise return it unchanged") |
| `test_initials_basic` | uppercase first letter of each word, no separator | step 2 prompt |
| `test_initials_ignores_extra_spaces` | extra and repeated spaces handled | step 2 prompt ("Handle names with extra or repeated spaces") |
| `test_normalize`, `test_wrap` (base) | existing behaviour preserved | every prompt ("Preserve all existing behavior, including wrap"), and readable in `base/` |

Writable scope — `src/textkit/` only, `tests/` fixed — is stated in every
prompt. It is the information a single-prompt contract carries in
`writable_paths`, and its absence is what sent the first session's model to
write a new top-level module.

## The gate

`fixtures/prompt-faithful.patch` is an implementation written **strictly from
the prompt text**, and
`tests/integration/test_session_ordering_regression_fairness.py` asserts it
satisfies every hidden check and preserves base. That is the mechanical form of
"no hidden requirements": tighten a check without following in the prompt and
the row goes red.

Verified by mutation on 2026-09-08 — adding a spacing requirement the prompt
does not state (`"Hello w…"` → `"Hello  …"`) turned the gate red, and reverting
it turned it green. The sibling row keeps it honest in the other direction:
`known-broken.patch` must still fail, so a grader that passed everything would
not satisfy the gate.

## What is still not established

That the task is a **workload**. It is now fair and its scope is stated, but no
session has yet completed step 1, so the cross-prompt dependency it was built
around remains unexercised. Admission would need a probe showing the task can
be finished and that its steps discriminate — a separate job from this one, and
one no fixture can substitute for.
