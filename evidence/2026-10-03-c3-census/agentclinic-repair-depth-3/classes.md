<!-- evals 0c3ad1f84f3fbafce696474f0743f8d834909d47; classify.py --night /Users/pauleveritt/satyrn-runs/2026-10-02-c1-agentclinic-repair-depth-3 --record records/2026-10-02-c1-agentclinic-repair-depth-3.json --out evidence/2026-10-03-c3-census --grade-root /Users/pauleveritt/satyrn-c3-grades -->

The eight class columns are empty on purpose: a reviewer fills them, by turn, from the reconstruction (design section 7). `primary` and `cited turns` are the reviewer's too. The mechanical evidence each class would be argued from is printed beneath.

| task | attempt | raised | information | ambiguity | capability | budget | finishing | runaway | hunting | allowlist | primary | cited turns |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| agentclinic-repair-depth-3 | 107978 | - | False | False | False | False | False | False | False | False | - | t3, t4, t5, t6, t7 |
| agentclinic-repair-depth-3 | 152067 | - | False | False | False | False | False | False | False | False | - | t4, t6, t7, t8, t9, t12 |
| agentclinic-repair-depth-3 | 197431 | - | False | False | False | False | False | False | False | False | - | t7, t8, t9, t10, t11 |
| agentclinic-repair-depth-3 | 550946 | - | False | False | False | False | False | False | False | False | - | t5, t6, t7, t11, t12, t14 |
| agentclinic-repair-depth-3 | 810657 | - | False | False | False | False | False | False | False | False | - | t6, t7, t8, t9, t10, t12 |
| agentclinic-repair-depth-3 | 499793 | - | False | False | False | False | False | False | True | False | hunting | t5, t7, t8, t9, t10, t11 |

evidence: agentclinic-repair-depth-3 107978 information=None, ambiguity=None, capability=False, budget=False, finishing=False, runaway=False, hunting=False, allowlist=False actual@32k=True actual@48k=True decode_tok_s=30.7 decode_overlap=3
evidence: agentclinic-repair-depth-3 152067 information=None, ambiguity=None, capability=False, budget=False, finishing=False, runaway=False, hunting=False, allowlist=False actual@32k=True actual@48k=True decode_tok_s=29.4 decode_overlap=4
evidence: agentclinic-repair-depth-3 197431 information=None, ambiguity=None, capability=False, budget=False, finishing=False, runaway=False, hunting=False, allowlist=False actual@32k=True actual@48k=True decode_tok_s=23.9 decode_overlap=6
evidence: agentclinic-repair-depth-3 550946 information=None, ambiguity=None, capability=False, budget=False, finishing=False, runaway=False, hunting=False, allowlist=False actual@32k=True actual@48k=True decode_tok_s=22.9 decode_overlap=4
evidence: agentclinic-repair-depth-3 810657 information=None, ambiguity=None, capability=False, budget=False, finishing=False, runaway=False, hunting=False, allowlist=False actual@32k=True actual@48k=True decode_tok_s=20.7 decode_overlap=4
evidence: agentclinic-repair-depth-3 499793 information=None, ambiguity=None, capability=True, budget=False, finishing=False, runaway=False, hunting=True, allowlist=False actual@32k=False actual@48k=False decode_tok_s=21.1 decode_overlap=3

## Notes (reviewer draft, 2026-10-03; for the maintainer's signature)

Vocabulary as the signed isolated example; primary is the class whose removal would change the verdict at 32,000 / 48; `-` for a pass. All six cells admitted (refusals 0, reaches 0). Every `patch.diff` touches only app.py, models.py, templates/base.html (inside `source_paths`), so `allowlist` is False throughout; the bad `base.html` edits at 550946 t6 and 810657 t8 failed ENOENT and were redone at t7 / t9. `information` and `ambiguity` are False: the R2 prompt names all four failure texts and five cells derived the three seams from them.
- 107978: all three hunks in one turn t4 (pass state t4, 1,162 tok); own-green t5, simulated checks t6, self-stop t7. No class fires.
- 152067: hunks at t6, t7, t8 (pass t8, 2,241 tok); own-green t9; self-stop t12. No class fires.
- 197431: t7 learns Starlette 0.46.2 defaults to 307; 2,621-token think t8; hunks t9 (pass t9, 7,202 tok); self-stop t11. No class fires.
- 550946: hunks t6-t7; a dropped paren in models.py broke collection (t9-t10), repaired t11 (pass t11, 3,920 tok); own-green t12; self-stop t14. No class fires.
- 810657: t7 greps site-packages/starlette for `casefold` (inside the cell's environment, not a root search); hunks t8-t9 (pass t9, 6,998 tok); self-stop t12. No class fires.
- 499793: wall-clock cut (COMMAND_TIMEOUT at the 4,800 s backstop during a whole-disk search). It had found 307 (t7) and the missing `lang` (t8) but made no edit; at t9-t10 it settled on a Content-Language header as the `casefold` source, then ran `find / -iname "*agentclinic*"` (t10) and `grep -rl <test names> /` (t11), which never returned (5,373 tokens, 11 turns). `hunting` True is the mechanical flag and I agree. `capability` departs from the mechanical True: the cell spent 5,373 of 32,000 tokens and 11 of 48 turns, so it did not spend its budget; the backstop ended it. Primary `hunting` is the class that precedes the failure; whether the cell would have passed without the search is not shown (no edit yet, and its t10 reading is one the hidden suite rejects).
- t10's output listed host paths outside the worktree (records/*.json under satyrn-docs-scratch, a c3-eb0-debug directory); confinement reports reaches 0 and no file was opened. Recorded, not re-judged.

Tallies (C3 admits every cell, so admitted-only equals all-cells):

| class | admitted-only (6) | all-cells (6) |
|---|---|---|
| information / ambiguity / capability / budget / finishing / runaway / allowlist | 0 each | 0 each |
| hunting | 1 (primary 1) | 1 (primary 1) |
| pass, no class | 5 | 5 |
