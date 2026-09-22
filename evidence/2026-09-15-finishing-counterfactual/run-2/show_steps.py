import importlib.util, json, sys
from pathlib import Path
SCRIPT = Path("/Users/pauleveritt/projects/pauleveritt/satyrn-evals/evidence/2026-09-15-finishing-counterfactual/counterfactual.py")
spec = importlib.util.spec_from_file_location("cf", SCRIPT); cf = importlib.util.module_from_spec(spec); sys.modules["cf"] = cf; spec.loader.exec_module(cf)
attempt = sys.argv[1]; turns = set(map(int, sys.argv[2].split(","))) if len(sys.argv) > 2 else None
s = next(c for c in (*cf.DECISION, *cf.DEBUG) if c.attempt == attempt)
events = cf.parse_events((cf.cell_dir(s) / "transcript.txt").read_text()); cwd = cf.session_cwd(events)
for st in cf.steps_of(events):
    if turns is None or st.turn in turns:
        print(f"\n### step {st.index} turn {st.turn} tok {st.output_tokens} {st.name} err={st.is_error}")
        a = dict(st.args)
        if st.name == "bash": print("CMD:", a.get("command"))
        else: print("ARGS:", json.dumps(a)[:1500])
        print("RESULT:", st.text[:1200])
