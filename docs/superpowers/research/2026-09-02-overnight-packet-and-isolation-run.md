# Overnight run: packet content, grader isolation, and four instrument defects

**Date:** 2026-09-02, ~02:00Z to ~14:35Z (an earlier draft labelled local
times as UTC — the same typed-not-clocked error §3 admits)
**Status:** spike evidence; **no task admitted, no phase started**
**Models:** `omlx/gemma-4-12B-it-MLX-8bit`, `Mellum2-12B-A2.5B-Instruct`,
`Qwen3.5-9B-8bit`, `gemma-4-26B-A4B-it-OptiQ-4bit`, `Llama-3.1-8B-Instruct`,
`Qwen2.5-Coder-7B-Instruct` · **Pi:** 0.84.4

Roughly 160 cells through a purpose-built scratchpad harness, not through this
repository's own `attempt` path. **Every number here must be re-derived before
it is cited in a plan**; the raw artifacts are local and unadmitted. Fixtures
came from a private companion repository and its contents are not reproduced.

## 1. The one result worth carrying

A single sentence, added to an otherwise identical repair prompt, is the most
reliable intervention measured:

> "The acceptance suite is owned by the caller. You cannot see it and you do
> not need to; it is run for you."

Final block, 36 cells, all under OS-level isolation, zero voids:

| arm | pass | median turns | timeouts |
| --- | ---: | ---: | ---: |
| task + failure output, which names the suite and embeds paths (`dumb`) | 7/12 | 47.5 | 6/12 |
| same, with the suite's filename and absolute paths redacted (`stripped`) | 7/12 | 25 | 5/12 |
| **`dumb` + the ownership sentence (`factonly`)** | **11/12** | **10** | **1/12** |

All 36 cells are `gemma-4-12B-it-MLX-8bit`, replicates 30–35. (An earlier draft
of this table pooled in two re-run cells from a *different* model, which
inflated `dumb` to 8/12 and understated its median as 32. Corrected.)

**Mechanism, read from transcripts rather than inferred.** In the earlier
*unsandboxed* blocks, unguarded runs spent their budget hunting for the grader:
`ls -R` repeated 139–156 times interleaved with `find . -name
test_acceptance.py`, ending in a timeout with no patch at all. **Every one of
those calls succeeds**, so a loop breaker keyed on failures would never fire —
independently reproducing `local-ai-pi`'s record of 245 identical successful
`ls -R` calls.

**But hunting is not the whole story, and this weakens the reading above.** In
the sandboxed block the spirals are larger (`ls -R` ×203–271) and take other
shapes, and the `stripped` arm — which never sees the grader's filename —
still produced a 245-call `ls -R` spiral. Something more general than
"searching for a named file" is at work in the unguarded arms.

**What is *not* established.** The claim that the fact is *the* active
ingredient did not survive its own test. On one fixture, merely not naming an
unreachable file recovers most of the gain (median 219 → 19) without adding any
fact; on the other it recovers none. Worse, the redaction arm was itself
confounded — removing absolute paths also removes *localisation*, and it **hurt**
the multi-failure fixture (2/6 against 5/6). Neither pre-registered band fits.

So: **a host-computed fact about grader ownership is the best intervention
measured, and the mechanism behind it is not settled.**

## 2. Grader isolation is required, and achievable without a VM

Models found the real acceptance suite on disk, copied it into the workspace,
and iterated against it until green. Two cells did so definitively; more read it
without copying; up to 49 *other cells'* directories were read by a single run,
exposing earlier prompts, patches and workspaces.

A whole-process `sandbox-exec` (Seatbelt) profile closes it: allow-only reads
limited to OS and toolchain roots plus the run root, writes confined to the run
root, network limited to the local model server. Verified live: grader reads, `$HOME` listing and symlink escape all refused,
and the model still reached its server. **No VM, no container, no install.**

**One hole this does NOT close, corrected after review.** Seatbelt enforces on
paths, so a **hard link created inside the run root** pointing at the grader
**is readable** — the probe log records that read succeeding. Whether a
*sandboxed* process can create such a link was never tested. An earlier draft
of this document claimed hard-link escapes were refused; that was wrong, and it
is the kind of error that would let a reader adopt a profile believing it
closes a hole it does not.

**A confound this profile introduced, and did not disclose until review.**
Under the sandbox the model had **no working test runner**: across block 7's 36
cells there were 266 `pytest` invocations, **zero** returned a result, and 179
returned `No module named pytest` — the model's `python` resolved to a build
environment without it, and PyPI was blocked. In the unsandboxed blocks, 8 of
60 cells ran the suite successfully. So block 7 measures models that could not
self-verify, the handicap is uniform across its three arms (the arm ordering
survives) but block 7 is **not comparable to the earlier blocks**, and part of
"sandboxing made the unguarded arm worse" is "the model lost the ability to
check its own work". A corrected profile must grant the run root a working
interpreter and test runner.

This is the same shape as the four defects in §3 — **a capability silently
absent** — and it was found by adversarial review, not by me.

Two further practical notes: an allow-only read profile **must** include
`(literal "/")` and `(subpath "/private/var/select")` or every process aborts
in dyld at exec with no stderr; and blocked escape attempts are worth recording
per cell, since they turn attempted cheating into a measurement.

**Windows is unsolved.** Seatbelt is macOS-only, bubblewrap is Linux-only, and
the remaining options are VMs or containers. For a cross-platform story the
honest answers are architectural — graders never on reachable disk — plus OS
user/ACL separation, neither of which has been tested here.

**The cheap, cross-platform guard** is a content-based tripwire, and it belongs
in the default test tier (no model, no network, no subprocess): hash every file
in the workspace and patch against every oracle file on disk, and count real
test names.

Its COPIED signal is content-based and is the one to trust. Its READ signal, as
implemented, matches a *filename* in a command rather than grader content, so it
also fires when a model reads a test file it wrote itself — it flagged three
sandboxed cells where the grader was provably unreachable. Treat READ as a
prompt for inspection, not a verdict, until it is rewritten to match content.

## 3. Defects in the instrument

**Four of one class**, all mine, all the same shape: **an absence of signal
reported as a finding.**

1. **A void hiding a fail.** Collection errors were all classified as instrument
   failure, but a suite that cannot import because the *model's* code is broken
   is a model failure. Fixing it after seeing results disqualified that block.
2. **A preflight that could not fail.** `/v1/models` answers from a registry, so
   a wedged model slot passed the check; a block then lost 16/16 cells to
   zero-event timeouts while the preflight was green. Fix: a live one-word
   completion per model, before every block.
3. **A verdict computed over zero graded cells.** Two models emitted no
   parseable tool calls at all, and the reporting code called that "does not
   exhibit the behaviour" rather than "unmeasured".
4. **A detector that fired on 104 of 128 cells**, because every transcript
   contains its own path. A detector that always fires is exactly as useless as
   one that never fires.

Two further corrections came from adversarial review, not from me: contamination
was **overstated sixfold** (10 of 12 flagged files were model-authored tests
written from an assertion the prompt already displayed — legitimate), and
pre-registration timestamps were *typed* rather than clocked, making a
discipline claim unverifiable even though the ordering was correct.

**A second class, admitted after a third review pass: accounting.** The
headline table in §1 pooled two cells from a different model into one arm,
inflating it. The audit of blocks 0–6 found the same class three more times —
three median conventions used inconsistently, a table mixing a turns column
with a tool-calls column, and a do-not-cite block pooled into a live figure.
This class is not "absence reported as signal"; it is arithmetic over the wrong
set, and it survived two review passes before being caught.

**And two capability-shaped defects:** the sandbox silently removed the model's
test runner (§2), and an early packet arm bundled three changes at once,
including a clause that targeted the very failure mode under test.

**Proposed standing tests, in place of individual fixes:**
1. every detector must fire on a known-bad drawn from the *current* batch and
   stay silent on a known-good from the same batch, both directions, every time;
2. every reported statistic must name the exact cell set it was computed over,
   and that set must be recomputable by a filter, not by hand.

## 4. Secondary findings

- **Mellum2-12B-A2.5B floors** on the 3-phase build (`deepest_pass` 1,1,1,0).
  Cause is not truncation — stop reason is a clean `stop`, peak output ~1.1k
  tokens — it announces the next action and ends the turn. It also invented its
  own `pyproject.toml`/`uv.lock` in 2 of 8 runs, locking a Starlette version
  different from the oracle's.
- **A model can score zero for a tool-protocol mismatch rather than incapacity.**
  Llama-3.1-8B emits tool calls as literal JSON text; Qwen2.5-Coder-7B answers
  in prose — and *correctly diagnosed the bug* while scoring zero. Any roster
  wider than one model family needs a text-contract path, or it silently becomes
  "models that tool-call".
- **Grader-hunting is not model-specific.** Measured by *reach outside the
  workspace* rather than by a call-count proxy, it appeared in every model that
  acted, including the larger one.
- **Semantic-preservation spot-check.** Following the `magicmock-factory`
  lesson that suite success does not establish preservation, passing repair
  cells were compared against the reference implementation: no semantic
  regression found. Stated as a spot-check rather than an audit — the
  comparison was run ad hoc and **no script was committed**, so by this
  repository's own rule ("carry the command that recomputes it") the claim is
  not yet reproducible.

## 5. What this changes for the roadmap

- **`deepest_pass` should not be a primary measure.** It saturated at both ends
  while `tests fixed` discriminated in every cell.
- **AgentClinic repair fixtures look mid-band** (7/12 unguarded vs 11/12 with
  the fact), where this repository's two other probed tasks both floor at 0/4
  for bare Pi. Hedge this: the comparison crosses harnesses (scratchpad runner,
  sandboxed, imperative wrapper) and the two floors were measured on the Evals
  path under an earlier Pi. Per fixture the picture is also not uniformly
  mid-band — `factonly` on one fixture is 6/6, a ceiling. Worth re-testing on
  the Evals path before treating repair as the better workload.
- **The smallest useful change is one field.** `satyrn-engine`'s `Contract`
  carries `id`, `task`, `writable_paths` and renders no facts. Tonight says a
  single host-computed fact outperforms everything else measured.
- **Do not build an orchestrator yet.** Everything above was measured with none.

## 6. Recomputation

The scratchpad harness, per-cell captures, pre-registrations (the last one
machine-stamped and hashed before its block), and a running findings log are
local and unadmitted. Nothing in this document should enter a plan without
re-deriving it against those artifacts or, better, re-running the question
through this repository's own `capture` / `attempt` / `grade` path.
