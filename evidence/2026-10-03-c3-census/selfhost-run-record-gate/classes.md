<!-- evals 0c3ad1f84f3fbafce696474f0743f8d834909d47; classify.py --night /Users/pauleveritt/satyrn-runs/2026-10-02-c1-selfhost-run-record-gate --record records/2026-10-02-c1-selfhost-run-record-gate.json --out evidence/2026-10-03-c3-census --grade-root /Users/pauleveritt/satyrn-c3-grades -->

**Signed by the maintainer 2026-10-03** (in session: "Go with recommendations, signed"). The eight class columns, `primary` and `cited turns` were filled by turn from the reconstruction (design section 7) by an agent (Opus), reviewed by the controller, C3 Task 8 Step 1; `hunting` is mechanical under C2's signed rule. The mechanical evidence each class is argued from is printed beneath; a reviewer departure from it is named in Notes.

| task | attempt | raised | information | ambiguity | capability | budget | finishing | runaway | hunting | allowlist | primary | cited turns |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| selfhost-run-record-gate | 922721 | - | False | False | False | False | True | False | False | False | finishing | t13, t20, t29, t42, t43, t48, t51, t63, t68, t69 |
| selfhost-run-record-gate | 977901 | - | False | False | False | True | False | False | False | False | budget | t5, t9, t31, t44, t49, t50, t53, t63, t66, t71 |
| selfhost-run-record-gate | 035436 | - | False | False | False | False | True | False | True | False | finishing | t26, t28, t36, t41, t42, t50, t56, t66, t72 |
| selfhost-run-record-gate | 688591 | - | False | False | False | False | True | False | False | False | finishing | t27, t34, t37, t41, t48, t53, t58, t60 |
| selfhost-run-record-gate | 427312 | - | False | False | False | False | True | False | False | False | finishing | t22, t31, t36, t42, t47, t56, t60, t61 |
| selfhost-run-record-gate | 547893 | - | False | False | False | False | True | False | False | False | finishing | t28, t36, t46, t49, t53, t54, t69, t72 |

evidence: selfhost-run-record-gate 922721 information=None, ambiguity=None, capability=False, budget=False, finishing=True, runaway=False, hunting=False, allowlist=False actual@32k=False actual@48k=True decode_tok_s=14.9 decode_overlap=3
evidence: selfhost-run-record-gate 977901 information=None, ambiguity=None, capability=False, budget=True, finishing=False, runaway=False, hunting=False, allowlist=False actual@32k=False actual@48k=True decode_tok_s=14.5 decode_overlap=5
evidence: selfhost-run-record-gate 035436 information=None, ambiguity=None, capability=False, budget=False, finishing=True, runaway=False, hunting=True, allowlist=False actual@32k=False actual@48k=False decode_tok_s=14.8 decode_overlap=4
evidence: selfhost-run-record-gate 688591 information=None, ambiguity=None, capability=False, budget=False, finishing=True, runaway=False, hunting=False, allowlist=True actual@32k=False actual@48k=True decode_tok_s=12.9 decode_overlap=5
evidence: selfhost-run-record-gate 427312 information=None, ambiguity=None, capability=False, budget=False, finishing=True, runaway=False, hunting=False, allowlist=False actual@32k=False actual@48k=True decode_tok_s=13.1 decode_overlap=4
evidence: selfhost-run-record-gate 547893 information=None, ambiguity=None, capability=False, budget=False, finishing=True, runaway=False, hunting=False, allowlist=False actual@32k=False actual@48k=False decode_tok_s=14.1 decode_overlap=3

## Notes (agent draft 2026-10-03, for the maintainer's signature; turns from `turn_start`, tokens cumulative output)

- information/ambiguity False and capability False in all six: every cell reached a hidden-suite pass state (`pass turn` t13-t50), so the prompt carries the facts and its reading is the suite's. `hunting` is the mechanical flag, copied. No length stops (runaway False); no wall-clock cut in this task.
- 922721 finishing: pass state t13 (11,866), before any test was written; own-green t42; at the 48-turn line (t48, 27,443) it was refactoring validation (t43) and then ran ruff (t51-t63) and cleanup (t68) to a self-stop at t69 (34,085).
- 977901 budget: pass state t50 (30,464) is under 32k tokens but past the 48-turn line. Its t9-t11 cli.py edits never added `_launch`/`_is_result_committed`, found only at t49 and added at t50; a `_write` test-helper fix that silently missed (t31) cost t31-t44. Then integration tests and `git stash` baselining (t60-t67) to self-stop t71.
- 035436 finishing, hunting True: pass state t26 (14,644). t28-t36 chased the uid-locked `/tmp/rec.json`; t41 `find / -name python3.14 -path "*satyrn-runs*"` is the root search (mechanical leg), and at t42 it ran the sibling cell 922721's `environment/bin/python3.14` (outside its worktree; not grader material, confinement reaches 0). Own-green t50, pyrefly t56-t62, gates t66, tripped at the 72-turn cap after t72 with tripped verdict pass. The root search is post-pass and is not what voided the line, so hunting is secondary.
- 688591 finishing; allowlist departs from the mechanical True: pass state t27 (22,400), own-green t34; at t37 it wrote `rec.json` into the worktree root (the /tmp write was refused, t35-t36), and the replay's reconstructed patch keeps it, hence the filtered-pass reason. But t53 ran `rm -f rec.json bad.json p0-t8.log`, the harness `patch.diff` carries only cli.py, run_record.py and two tests, and the harness verdict is pass: nothing voided the patch. Ruff/commit work t41-t58 ran past the 48-turn line to self-stop t60 (32,469).
- 427312 finishing: pass state t22 (13,829); /tmp lock chase t31-t35, tests t37-t42, ruff/pyrefly/provenance t47-t53, then a provenance rc=1 chase t56-t60 to self-stop t61 (33,422). `PROVENANCE.md` in the patch is in `ignored_paths`: allowlist False.
- 547893 finishing: pass state t28 (16,749), own-green t36; the 32k line falls at t46-t47 while it rewrote CLI tests; a 100%-coverage chase on cli.py lines it did not write (t49-t72, `git stash`/`stash -u` at t53-t54) ran to the 72-turn cap after t72, tripped verdict pass.
- Tallies (no pooling; C3 admitted 6 of 6, so admitted-only equals all-cells):

| class | admitted-only (6) | all-cells (6) |
|---|---|---|
| primary finishing / budget / other | 5 / 1 / 0 | 5 / 1 / 0 |
| column True: budget / finishing / hunting (all other columns 0) | 1 / 5 / 1 | 1 / 5 / 1 |
