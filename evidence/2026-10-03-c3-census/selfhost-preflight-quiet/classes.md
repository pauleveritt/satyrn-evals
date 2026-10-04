<!-- evals 0c3ad1f84f3fbafce696474f0743f8d834909d47; classify.py --night /Users/pauleveritt/satyrn-runs/2026-10-02-c1-selfhost-preflight-quiet --record records/2026-10-02-c1-selfhost-preflight-quiet.json --out evidence/2026-10-03-c3-census --grade-root /Users/pauleveritt/satyrn-c3-grades -->

**Signed by the maintainer 2026-10-03** (in session: "Go with recommendations, signed"). The eight class columns, `primary` and `cited turns` were filled by turn from the reconstruction (design section 7) by an agent (Opus), reviewed by the controller, C3 Task 8 Step 1; `hunting` is mechanical under C2's signed rule. The mechanical evidence each class is argued from is printed beneath; a reviewer departure from it is named in Notes.

| task | attempt | raised | information | ambiguity | capability | budget | finishing | runaway | hunting | allowlist | primary | cited turns |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| selfhost-preflight-quiet | 274281 | - | False | False | True | False | False | False | False | False | capability | t18, t24, t39, t41, t45, t53 |
| selfhost-preflight-quiet | 343289 | - | False | False | False | False | True | False | False | False | finishing | t16, t21, t30, t37, t38, t40 |
| selfhost-preflight-quiet | 420082 | - | False | False | False | False | True | False | False | False | finishing | t13, t19, t37, t48, t49, t58, t60 |
| selfhost-preflight-quiet | 731480 | - | False | False | False | False | True | False | False | False | finishing | t10, t17, t23, t24, t29, t31, t47 |
| selfhost-preflight-quiet | 329119 | - | False | False | False | False | True | False | False | False | finishing | t14, t32, t39, t48, t51, t62, t64 |
| selfhost-preflight-quiet | 035112 | - | False | False | False | True | False | False | False | False | budget | t10, t15, t16, t26, t39, t47, t56 |

evidence: selfhost-preflight-quiet 274281 information=None, ambiguity=None, capability=True, budget=False, finishing=False, runaway=False, hunting=False, allowlist=False actual@32k=False actual@48k=False decode_tok_s=14.0 decode_overlap=5
evidence: selfhost-preflight-quiet 343289 information=None, ambiguity=None, capability=False, budget=False, finishing=True, runaway=False, hunting=False, allowlist=False actual@32k=False actual@48k=True decode_tok_s=14.5 decode_overlap=4
evidence: selfhost-preflight-quiet 420082 information=None, ambiguity=None, capability=False, budget=False, finishing=True, runaway=False, hunting=False, allowlist=False actual@32k=False actual@48k=True decode_tok_s=14.7 decode_overlap=3
evidence: selfhost-preflight-quiet 731480 information=None, ambiguity=None, capability=False, budget=False, finishing=True, runaway=False, hunting=False, allowlist=False actual@32k=False actual@48k=False decode_tok_s=13.7 decode_overlap=5
evidence: selfhost-preflight-quiet 329119 information=None, ambiguity=None, capability=False, budget=False, finishing=True, runaway=False, hunting=False, allowlist=False actual@32k=False actual@48k=True decode_tok_s=14.0 decode_overlap=4
evidence: selfhost-preflight-quiet 035112 information=None, ambiguity=None, capability=False, budget=True, finishing=False, runaway=False, hunting=False, allowlist=False actual@32k=False actual@48k=False decode_tok_s=14.1 decode_overlap=3

## Notes (reviewer draft, 2026-10-03, for the maintainer's sign-off; primary = the class whose removal would have changed the verdict at 32,000 tokens / 48 turns; `hunting` is copied from the mechanical flag)

- 274281 capability: module at t18, hidden 19/20 at every measured turn t18-t39, failing only `test_certificate_is_empty_on_a_quiet_machine_and_records_its_inputs` because `as_dict()` returns the `problems` tuple where the prompt writes `{"problems": [...]}`. t24 saw `() != []` and t39 edited its own round-trip test to accept the tuple instead of the module; own green t41, line at t45 (32,254), self-stop t53. Unambiguous shape the prompt fixed, so no ambiguity.
- 343289 finishing: hidden pass at t21 (23,748); own green t30; crosses 32k at t37 (32,138) before the commit at t38; self-stop t40 (33,629).
- 420082 finishing: hidden pass at t19 (18,287); own green t37; the 48-turn line falls at t48 (28,386) before ruff green t49 and the commit t58; self-stop t60 (32,822).
- 731480 finishing, verdict fail even at 48k: hidden pass at t17 (26,261) and t19. Its own suite (t10) wrote the `ps -axo pid,pcpu,comm` fixture comma-separated; at t23-t24 it conformed `busy_processes` to that fixture (split on commas), hidden 13/20 from t24 to the end; own green t29, 32k crossed t31, self-stop t47. Capability is not marked (a pass state was reached, census §7); the post-pass regression is named here. Ambiguity not marked: the prompt names the real command, whose whitespace output the cell never ran.
- 329119 finishing: hidden pass at t32 (28,631); 32k crossed t39 (32,414), 48-turn line t48, own green t51, commit t62, self-stop t64 (44,345).
- 035112 budget: t10-t15 a `/tmp` coverage experiment (13,887-token t10, a scratch venv at t14); module at t16 with invalid bare-`*` call sites, grades unavailable t16-t35 (collection error); 32k crossed t26 (32,040); call sites fixed t39; hidden pass first at t47 (42,253); BUDGET_EXCEEDED at t56 (48,290), tripped verdict pass. `/tmp` scratch work is not a root search; mechanical `hunting` False agrees.
- Information False for all six: four cells held a hidden pass on the prompt alone. Ambiguity False for all six: no cell failed on a reading the prompt admits (the isolated census's decode-null reading did not recur here).
- No wall-clock cut in this task. The mechanical evidence lines agree with every column.
- Tallies (column counts / primary). Admitted-only (6 of 6): information 0, ambiguity 0, capability 1, budget 1, finishing 4, runaway 0, hunting 0, allowlist 0 / capability 1, finishing 4, budget 1. All-cells (6): identical, because every C3 cell of this task is admitted (confinement.json: 6 measured, 6 admitted, 0 flagged, 0 unmeasured).
