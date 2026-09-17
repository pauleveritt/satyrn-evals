<!-- evals e6b75b02bc4fb03850a3faaa431e341388533231; classify.py --night /Users/pauleveritt/satyrn-runs/2026-09-17-census2-selfhost-cell-loop --record records/2026-09-17-census2-selfhost-cell-loop.json --out evidence/2026-09-17-census-2 --grade-root /Users/pauleveritt/satyrn-census-grades -->

The eight class columns are the reviewer's, filled by turn from the reconstruction (design section 7), 2026-09-17, for the maintainer's sign-off. `primary` and `cited turns` are the reviewer's too; the primary is the class whose removal would have changed the verdict at the 32,000-token, 48-turn line. The mechanical evidence each class is argued from is printed beneath, paired with the reviewer's `argument:` line. Where a column departs from the mechanical flag the argument says why. Cross-task reading: `classes-summary.md` in `evidence/2026-09-16-census/`.

| task | attempt | raised | information | ambiguity | capability | budget | finishing | runaway | hunting | allowlist | primary | cited turns |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| selfhost-cell-loop | 225004 | - | False | False | True | False | False | True | False | False | runaway | t17, t18 |
| selfhost-cell-loop | 352753 | - | False | False | True | False | False | False | False | False | capability | t17, t18, t24, t30, t31, t33, t35, t36 |
| selfhost-cell-loop | 507079 | - | False | False | True | False | False | True | False | False | runaway | t7, t8, t9 |

evidence: selfhost-cell-loop 225004 information=None, ambiguity=None, capability=True, budget=False, finishing=False, runaway=True, hunting=False, allowlist=False actual@32k=False actual@48k=False decode_tok_s=18.1 decode_overlap=3
argument: Ended by a 16,000-token length-stop at t18 with no tool call: `runaway` is primary, `capability` secondary. The runaway turn is the same `identity` question that ended 442168 -- the cell observed that `RunRecord` carries no `AttemptCode`, that `launch_cells`' signature has no place for one, and set out to reason the ledger identity into existence rather than pick any mapping and move. Night 2's quiet machine changed nothing about this: the cell stopped itself at 22,915 tokens with no patch.

evidence: selfhost-cell-loop 352753 information=None, ambiguity=None, capability=True, budget=False, finishing=False, runaway=False, hunting=False, allowlist=False actual@32k=False actual@48k=False decode_tok_s=20.4 decode_overlap=3
argument: No pass state, the 48k budget tripped at t36 and the tripped tree graded fail: `capability` is primary. The module was written at t17-t18 (2,735 and 4,069 tokens), refactored at t22-t24, then abandoned and rewritten whole at t31 because an edit against a large block would not match; t33 wrote the test file in one 6,013-token turn. At t35-t36 the cell counted 31 test functions against the prompt's "22 passed" and began pruning, and the budget ended it there.

evidence: selfhost-cell-loop 507079 information=None, ambiguity=None, capability=True, budget=False, finishing=False, runaway=True, hunting=False, allowlist=False actual@32k=False actual@48k=False decode_tok_s=17.1 decode_overlap=3
argument: Ended by a 16,000-token length-stop at t9 with no tool call: `runaway` is primary, `capability` secondary. t7 and t8 read the tripwire conftest and listed `src/satyrn_evals`, and at t9 the cell noticed `cell_engine.py`, `cell_preflight.py` and `cell_evidence.py`, told itself "let me not get distracted", and then ran to the cap in the same turn. Nine turns, 17,180 tokens, no patch.
