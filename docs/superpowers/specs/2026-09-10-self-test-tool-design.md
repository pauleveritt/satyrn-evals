# Self-test tool design: closing the implementer-local correction loop

Written 2026-09-10. A TE readiness item, not a numbered HP cycle. Design
only: **it authorizes offline implementation and proof; it does not
authorize any live `pi` process, any inference, or any comparison
spending.** Read with
[the self-test-harness design](2026-09-10-self-test-harness-design.md),
whose "What this is not" section this closes, and with
[the TE plan](../../current/engine-turn-efficiency-plan.md)'s "Repair
ownership" section, which already requires this: "Both configurations need
equivalent verification capabilities; a bounded test tool can supply them
without unrestricted `bash`."

## What this closes

The harness-run self-test (already shipped) makes `self_test_command`
honestly `applied` and retains its outcome, but the implementer never sees
the result — the harness runs it after the process has already exited. This
closes that: the implementer gets the result **inside its own invocation**,
through a tool call, so Pi's own existing multi-generation agent loop can
read a failure and correct it — the same loop that already produces the
6-7-turns-per-phase shape the turn ledger proved is real. No new retry
mechanism is added; Pi's loop already has the turn capacity.

The harness-run self-test is not replaced. It remains the guaranteed,
model-independent evidence of record — `applied` regardless of whether the
model ever calls the new tool. The tool is what gives the model a reason to
loop toward a passing state instead of stopping at its first attempt;
`declaration_ledger`'s `self_test_command: applied` state does not change.

## The mechanism, grounded in pi's own documented API

`pi --print --mode json --no-extensions --no-skills ...` — the flags
`adapters/pi_implementer.py` already passes — disables *discovered*
extensions (including any ambient satyrn-engine guard extension), but pi's
own `--help` states plainly: `--no-extensions, -ne  Disable extension
discovery (explicit -e paths still work)`. An **explicit** `-e <path>`
extension loads regardless. This is the seam: a small, purpose-built
extension, loaded explicitly, exposing exactly one narrow tool — not a
architecture change to how `pi_implementer.py` invokes Pi (still one CLI
subprocess, still JSON-mode stdout piped to a file).

Extensions register tools via `pi.registerTool()`
(`extensions.md`, "Tool Definition"), and pi ships a sanctioned command
runner for exactly this: **`pi.exec(command, args, {signal, timeout})` →
`{stdout, stderr, code, killed}`** (`extensions.md`, "pi.exec"). This is
the "reuse an existing tool" answer: the extension does not shell out by
hand: it calls the same helper pi's own built-in `bash` tool is documented
alongside.

**Signaling errors:** per `extensions.md` ("Signaling errors"), throwing
from `execute()` sets the tool result's `isError: true`; returning a value
never does, regardless of its contents. This maps directly onto the
already-shipped `SelfTestOutcome` distinction (`route.py`): a launch
failure or timeout (`ran=False`) throws — a tool malfunction, distinct from
a test that ran and failed. A nonzero `code` from a test that genuinely ran
(`ran=True`) returns normally; the content states the failure so Pi reads
it as the ordinary tool-result path its agent loop already handles every
turn, not as an exceptional error path.

## What the tool exposes, and what it does not

**Named `run_self_test`.** One tool, one name, used throughout the rest of
this document and its plan.

**Zero model-supplied parameters.** `parameters: Type.Object({})`. The
command that runs is fixed — the packet's own declared
`self_test_command` — never a string the model supplies or can redirect.
This is the same boundary HP1's design already drew for why this adapter
has no `bash`: a tool that took a command argument would be `bash` wearing
a different name, and would reopen the hidden-oracle-discovery risk
`self_test_command` naming `ORACLE_HOOK_PLUGIN` is already refused for
(`packet.py`, `build_packet`).

**The command crosses via an environment variable, not the packet file.**
`worker_projection` already renders `self_test_command` into the text the
model reads (`RENDERED_FIELDS`, `packet.py`) — the model already knows what
command exists to run, it just cannot make Pi execute it. The extension
reads the same value a second way, structurally: a new env var (proposed
name `SATYRN_SELF_TEST_COMMAND`, a JSON array of argv tokens, mirroring
`PACKET_ENV`/`RESULT_ENV`'s existing crossing pattern), set by
`command_implementer` only when `packet.self_test_command` is non-empty.
Nothing else about the packet crosses this way — no `redacts`, no
`writable_paths`, no facts.

**The tool is registered, and named in `--tools`, only when a command is
declared.** Rather than a tool that always exists and sometimes throws
"no command declared," `pi_implementer.py` omits both the `-e` flag and the
tool name from `--tools` entirely for a packet with no `self_test_command`
— an absent capability, not a capability that reliably fails.

**Output is bounded and legible, not raw-dumped — and capped, unlike the
harness-side retention.** The returned `content` states the exit code
plainly, then the combined stdout+stderr. This is a different concern from
`SelfTestOutcome`'s own "no truncation" decision: that decision governs
*retained evidence*, written once to a file nobody re-consumes as model
input. This tool's `content` is *fed back into the model's own context* on
every call, inside the same `turn_budget`-declared, `context_window`-capped
(80000 tokens, `arms/baseline.json`) conversation — an unbounded pytest
dump repeated across retries could exhaust context on its own, which is a
context-economy problem, not an evidence-fidelity one. A fixed cap (last
`SELF_TEST_TOOL_OUTPUT_CHARS` characters of the combined output, a
constant chosen against a representative real pytest failure once one
exists, not guessed) applies to the tool's *returned content* only. The
harness-side `SelfTestOutcome.output` this tool does not touch stays
exactly as built — full, untruncated, and separately retained by
`command_implementer`'s own post-exit run.

## Budget: no new enforcement invented

`turn_budget`/`tool_call_budget` are declared in every packet and applied
nowhere on this route today (`declaration_ledger`,
`AppliedState.DECLARED_NOT_APPLIED` for both, unconditionally) — a
pre-existing, disclosed HP gap, not something this design closes. Turns
the model spends calling this tool, reading its result, and correcting are
ordinary generations against that same unenforced declaration; this design
adds no second, competing budget concept and no new enforcement. If turn
budgets are ever actually applied to this route, this tool's turns are
already inside that scope by construction — it is a normal tool call, not
a special-cased escape hatch.

## Equivalent verification capability, not an identical tool surface

Baseline's continuous session has `bash` and can run
`self_test_command` (or anything else) at will, interleaved with edits, any
number of times. This tool gives Engine's implementer the same
**verification workflow** — run the declared test, read the result, edit,
retry — without unrestricted `bash`. The two are not the same tool surface,
and this design does not try to make them one; TE1's own "configuration-
bundle comparison" framing already requires disclosing, not erasing,
workflow differences between the two routes. What must be equivalent is
the *opportunity to verify and correct*, which this closes; broader shell
access is a separately disclosed difference, not a gap this tool needs to
fill.

## Proof, offline, before any live `pi` process

None of the tests below invoke a real `pi` process or a real model. The
extension's `execute()` logic is exercised directly, via Node, the same
way `pi_implementer.py`'s own logic is exercised via Python — proving the
tool's behavior does not require proving Pi calls it.

1. **A declared command that exits 0** returns normally (`isError`
   unset/false), content states exit code 0 and the command's real stdout.
2. **A declared command that exits non-zero** returns normally (not an
   error) — the same "ran, and the content says how it went" shape as
   `SelfTestOutcome.ran=True, exit_code != 0`.
3. **A command that cannot launch** (bad executable) throws, driven by a
   real launch failure, not a mock — mirroring this repository's existing
   standard for subprocess-ordering claims
   (`tests/integration/test_pi_implementer_ordering.py`'s precedent).
4. **A command that exceeds the bound timeout** throws, driven by a real
   process that actually outlives a short timeout, `result.killed` true.
5. **No `SATYRN_SELF_TEST_COMMAND` set** — proven only at the
   `pi_implementer.py` wiring level (Python), **not** `command_implementer`
   (that seam stays adapter-agnostic; it already owns the separate,
   already-shipped post-exit harness self-test and knows nothing about
   `-e` or pi-specific env vars): `build_pi_argv` never adds `-e` or the
   tool name to `--tools` for a packet declaring no `self_test_command`,
   so this case has no Node-side behavior to test at all.
6. **`pi_implementer.main()` sets the env var only when declared**, and
   omits it otherwise — a default-tier Python test on the argv/env
   construction, not on `pi.exec` itself.

## What this does not do

- **Does not invoke a real `pi` process or spend any inference.** That is
  a separate, explicitly authorized live-verification smoke, proposed but
  not run by this design (see below).
- **Does not change `declaration_ledger`'s `self_test_command` semantics.**
  `applied` still means the harness ran it; this tool's own calls are not
  separately tracked in that ledger. Whether the model actually called the
  tool, and to what effect, is retained transcript evidence for TE's own
  later analysis, not a new declaration field.
- **Does not add orchestrator-directed repair.** This is entirely inside
  one implementer's own invocation, matching the TE plan's "implementer-
  local verification and correction" scope exactly; the TE plan's
  separately-authorized outer repair loop is untouched.
- **Does not enforce a turn or tool-call budget.** Named above; a
  pre-existing gap, not invented or worsened here.

## The live-verification proposal, to be written after offline proof lands

Once the offline tasks below are implemented and green, write one short
pre-run record (matching `hp7-live-route-proof-pre-run-record.md`'s shape)
proposing exactly one bounded `pi` invocation: a trivial workspace, a
packet declaring a `self_test_command` engineered to fail once and pass
after one obvious fix, and a prompt asking the implementer to make it pass.
Its only question is operability — **can Pi actually discover and call
this tool, and does a real failure's content reach it legibly** — not
whether it improves anything, and its `n=1` stays outside every TE
denominator, the same discipline HP7 itself already applies. That record
states its own budget explicitly; this document authorizes none of it.
This is route-verification spending, separate from and outside the
denominator of comparison spending — an explicit "before comparison
spending" smoke, not a comparison run brought forward.
