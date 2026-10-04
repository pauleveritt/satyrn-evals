<!-- evals 0c3ad1f84f3fbafce696474f0743f8d834909d47; classify.py --night /Users/pauleveritt/satyrn-runs/2026-10-02-c1-selfhost-cell-loop --record records/2026-10-02-c1-selfhost-cell-loop.json --out evidence/2026-10-03-c3-census --grade-root /Users/pauleveritt/satyrn-c3-grades -->

The eight class columns are empty on purpose: a reviewer fills them, by turn, from the reconstruction (design section 7). `primary` and `cited turns` are the reviewer's too. The mechanical evidence each class would be argued from is printed beneath.

| task | attempt | raised | information | ambiguity | capability | budget | finishing | runaway | hunting | allowlist | primary | cited turns |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| selfhost-cell-loop | 133224 | - | False | False | True | False | False | True | False | False | runaway | t6, t7, t8, t9 |
| selfhost-cell-loop | 196867 | - | False | False | True | False | False | True | False | False | runaway | t16, t17, t18, t22 |
| selfhost-cell-loop | 263141 | - | False | False | True | False | False | True | False | False | runaway | t11, t13, t15 |
| selfhost-cell-loop | 546222 | - | False | False | True | False | False | True | False | False | runaway | t11, t12, t13 |
| selfhost-cell-loop | 119056 | - | False | False | True | False | False | True | False | False | runaway | t10, t18, t21 |
| selfhost-cell-loop | 389181 | - | False | False | True | False | False | False | True | False | hunting | t9, t11, t12 |

evidence: selfhost-cell-loop 133224 information=None, ambiguity=None, capability=True, budget=False, finishing=False, runaway=True, hunting=False, allowlist=False actual@32k=False actual@48k=False decode_tok_s=12.3 decode_overlap=3
evidence: selfhost-cell-loop 196867 information=None, ambiguity=None, capability=True, budget=False, finishing=False, runaway=True, hunting=False, allowlist=False actual@32k=False actual@48k=False decode_tok_s=13.5 decode_overlap=5
evidence: selfhost-cell-loop 263141 information=None, ambiguity=None, capability=True, budget=False, finishing=False, runaway=True, hunting=False, allowlist=False actual@32k=False actual@48k=False decode_tok_s=13.2 decode_overlap=4
evidence: selfhost-cell-loop 546222 information=None, ambiguity=None, capability=True, budget=False, finishing=False, runaway=True, hunting=False, allowlist=False actual@32k=False actual@48k=False decode_tok_s=14.9 decode_overlap=5
evidence: selfhost-cell-loop 119056 information=None, ambiguity=None, capability=True, budget=False, finishing=False, runaway=True, hunting=False, allowlist=False actual@32k=False actual@48k=False decode_tok_s=16.8 decode_overlap=4
evidence: selfhost-cell-loop 389181 information=None, ambiguity=None, capability=True, budget=False, finishing=False, runaway=False, hunting=True, allowlist=False actual@32k=False actual@48k=False decode_tok_s=15.5 decode_overlap=3

## Notes

Drafted 2026-10-03 by an agent (Opus), C3 Task 8 Step 1, for the maintainer's sign-off. Turns counted from `turn_start`, calls from `tool_execution_start`. Every column agrees with its mechanical `evidence:` line; `hunting` is copied from it. information/ambiguity are False for all six: no cell wrote a patch (five NO_PATCH with empty `patch.diff`, 389181 none), so the hidden suite never ran on a candidate, and the prompt states every literal the suite asserts. budget/finishing/allowlist are False: no cell reached a pass state.
- 133224: t6-t8 searched the tree for the launch symbols and a phase-2c plan, all absent; t9 is a 16,000-token length-stop with no tool call (66,765 chars of design thinking), ending the cell at 16,955 tokens. capability secondary.
- 196867: t9-t15 chased `AttemptCell` through three grep/sed calls that exited 1; t16 (3,780 tokens) and t17-t19 hunted in-tree docs for a launcher plan, absent; t22 is a 16,000-token length-stop with no tool call. capability secondary.
- 263141: t11 grep for the produced symbols and t13 the docs search returned nothing; t15 is a 16,000-token length-stop with no tool call, designing the drift/spawn loop. capability secondary.
- 546222: t11-t12 searched docs for a design doc, absent; t13 is a 16,000-token length-stop with no tool call, writing `launch_cells` inside its thinking rather than through `write`. capability secondary.
- 119056: t3-t20 read one file per turn (`CellProcess` grep t10, cli grep t18); t21 is a 16,000-token length-stop with no tool call. capability secondary.
- 389181: wall-clock cut (COMMAND_TIMEOUT at the 4,800 s backstop during a whole-disk search). t9 grep for the produced symbols found none; t11 (6,334 tokens) ended unsure of `write_ledger`'s first-write rule and resolved to look for a plan doc; t12 ran `find / -name "*2c*"` plus `grep -rln ... /`, which never returned (last timeline event is that call's start), at 7,687 tokens and 12 turns. hunting is primary because the root search consumed the remaining wall clock; capability secondary. Whether the cell would have passed without the hunt is not determinable. The t11 confusion is a misreading (the prompt says each call appends a sitting), not ambiguity. Not refused by confinement (no protected root named; refusals 0, reaches 0).

Tallies (admitted-only | all-cells; every C3 cell is admitted, 6 of 6, so the two are equal): primary runaway 5 | 5, hunting 1 | 1. Columns True: capability 6 | 6, runaway 5 | 5, hunting 1 | 1; information, ambiguity, budget, finishing, allowlist 0 | 0.
