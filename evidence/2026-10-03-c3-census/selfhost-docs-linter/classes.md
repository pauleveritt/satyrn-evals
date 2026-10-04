<!-- evals 0c3ad1f84f3fbafce696474f0743f8d834909d47; classify.py --night /Users/pauleveritt/satyrn-runs/2026-10-02-c1-selfhost-docs-linter --record records/2026-10-02-c1-selfhost-docs-linter.json --out evidence/2026-10-03-c3-census --grade-root /Users/pauleveritt/satyrn-c3-grades -->

**Signed by the maintainer 2026-10-03** (in session: "Go with recommendations, signed"). The eight class columns, `primary` and `cited turns` were filled by turn from the reconstruction (design section 7) by an agent (Opus), reviewed by the controller, C3 Task 8 Step 1; `hunting` is mechanical under C2's signed rule. The mechanical evidence each class is argued from is printed beneath; a reviewer departure from it is named in Notes.

| task | attempt | raised | information | ambiguity | capability | budget | finishing | runaway | hunting | allowlist | primary | cited turns |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| selfhost-docs-linter | 593944 | - | False | False | False | False | False | False | True | False | - | t9, t13, t30, t32, t33, t34, t48 |
| selfhost-docs-linter | 646828 | - | False | False | False | False | True | False | False | False | finishing | t19, t25, t27, t31, t32, t40, t43, t44 |
| selfhost-docs-linter | 708458 | - | False | False | True | False | False | False | False | False | capability | t10, t12, t23, t28, t31, t42 |
| selfhost-docs-linter | 556770 | - | False | False | False | False | False | False | False | False | - | t9, t10, t14, t36, t40, t44 |
| selfhost-docs-linter | 125810 | - | False | False | False | False | False | False | False | False | - | t9, t20, t22, t31, t42 |
| selfhost-docs-linter | 007105 | - | False | False | False | False | False | False | True | False | - | t9, t11, t12, t35, t36, t42 |

evidence: selfhost-docs-linter 593944 information=None, ambiguity=None, capability=False, budget=False, finishing=False, runaway=False, hunting=True, allowlist=False actual@32k=True actual@48k=True decode_tok_s=16.4 decode_overlap=5
evidence: selfhost-docs-linter 646828 information=None, ambiguity=None, capability=False, budget=False, finishing=True, runaway=False, hunting=False, allowlist=False actual@32k=False actual@48k=True decode_tok_s=16.3 decode_overlap=4
evidence: selfhost-docs-linter 708458 information=None, ambiguity=None, capability=True, budget=False, finishing=False, runaway=False, hunting=False, allowlist=False actual@32k=False actual@48k=False decode_tok_s=16.4 decode_overlap=3
evidence: selfhost-docs-linter 556770 information=None, ambiguity=None, capability=False, budget=False, finishing=False, runaway=False, hunting=False, allowlist=True actual@32k=True actual@48k=True decode_tok_s=15.0 decode_overlap=5
evidence: selfhost-docs-linter 125810 information=None, ambiguity=None, capability=False, budget=False, finishing=False, runaway=False, hunting=False, allowlist=False actual@32k=True actual@48k=True decode_tok_s=14.9 decode_overlap=4
evidence: selfhost-docs-linter 007105 information=None, ambiguity=None, capability=False, budget=False, finishing=False, runaway=False, hunting=True, allowlist=True actual@32k=True actual@48k=True decode_tok_s=14.9 decode_overlap=3

## Notes (reviewer draft 2026-10-03, for the maintainer's signature)
- information/ambiguity False in all six: the prompt states every message format verbatim and "Every path in a message is relative to root"; 5 of 6 cells pass on it. `hunting` is copied from the evidence line (C2 rule).
- 593944: pass state t32 (24,591 tokens), own-green t33, self-stop t48 at 28,564: passes inside the line, no primary. Its `hunting` True is the root search at t30 (`find / -name lint_docs.py`, debugging which module imported); the output listed `lint_docs.py` paths in other directories on the host, none of which it opened (confinement reaches 0).
- 646828: pass state t19 (24,051), own-green t25, line crossed in t32 (31,833 -> 32,305), self-stop t44 at 35,739: `finishing` primary. Post-green work: full suite t27, discovery at t31 that its own autouse fixture had rewritten the real `ROADMAP.md` (restored t32), a commit message that broke the shell (t40), re-counting tests (t43).
- 708458: no pass state at any graded turn and final fail (hidden `test_result_over_120_lines_fails`, `test_result_without_a_fenced_recompute_block_fails`): `capability` primary. Its linter reports results paths relative to `docs/results` (`relative_to(base)`), and its own tests assert `a.md: 121 lines > 120` (t10, t23, read back t28), so own-green at t31 locked the defect in; self-stop t42 at 30,833.
- 556770 and 007105: `allowlist` False, departing from the evidence line's True. Both wrote first to a literal `private/var/...` path inside the worktree (556770 t9, 007105 t9) and removed it with bash (556770 t40 `rm -rf private/`, 007105 t12); the harness patches carry only source paths plus ignored `PROVENANCE.md` and graded pass. The replay skips bash writers (unmeasured: turns 14 / 17), so its `-final` tree kept the stray file and graded unavailable ("non-source path: private/var/..."); the filtered pass then set the flag. Nothing voided a real patch. Both pass inside the line (own-green t36 / t35), no primary.
- 007105: `hunting` True is the root search at t11 (`find /private/var/folders/.../T -name lint_docs.py`), looking for its own stray write; no failure follows.
- 125810: pass state t20 (13,464), own-green t22, self-stop t42 at 21,453; t37's `timeout` was "command not found", not a reported timeout. No primary.
- Tallies (admitted-only | all-cells; all 6 cells are admitted, so the two are equal): primary capability 1 | 1, finishing 1 | 1, none 4 | 4; flags True: capability 1 | 1, finishing 1 | 1, hunting 2 | 2, information, ambiguity, budget, runaway, allowlist 0 | 0.
