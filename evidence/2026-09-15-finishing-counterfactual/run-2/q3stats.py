import json, statistics
rows = json.load(open("audit.json"))
cf = {r["attempt"]: r for r in rows}
out = ["| task | group | attempt | code | turns | tokens | think% | args% | text% | biggest turn (t:tok) | biggest/total | turns>=4k | length-stops | trigger t/tok | after-trigger turns/tok | ctx at end |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
agg = {}
for r in rows:
    T = r["turns"]; tot = r["total_tokens"] or 1
    think = sum(v["think"] for v in T.values()); text = sum(v["text"] for v in T.values()); args = sum(v["args"] for v in T.values()); chars = (think + text + args) or 1
    big_t, big = max(((int(k), v["tokens"]) for k, v in T.items()), key=lambda x: x[1])
    n4k = sum(1 for v in T.values() if v["tokens"] >= 4000)
    length_stops = sum(1 for v in T.values() for s in v["stops"] if s == "length")
    ctx = max(v["input"] for v in T.values())
    trig = r["trigger_no_bash_replay"]
    if trig:
        after_turns = r["n_turns"] - trig["turn"]; after_tok = tot - trig["tokens"]; trig_s = f"{trig['turn']}/{trig['tokens']}"; after_s = f"{after_turns}/{after_tok}"
    else: trig_s = after_s = "-"
    out.append(f"| {r['task']} | {r['group']} | {r['attempt']} | {r['code']}{'-'+r['verdict'] if r['verdict'] else ''} | {r['n_turns']} | {tot} | {100*think/chars:.0f} | {100*args/chars:.0f} | {100*text/chars:.0f} | t{big_t}:{big} | {100*big/tot:.0f}% | {n4k} | {length_stops} | {trig_s} | {after_s} | {ctx} |")
    agg.setdefault((r["task"], r["group"]), []).append(dict(tokens=tot, turns=r["n_turns"], think=100*think/chars, big=100*big/tot, ctx=ctx, code=r["code"], verdict=r["verdict"]))
out.append("\n## Per task/group medians\n")
out.append("| task | group | n | pass within budget | median tokens | median turns | median think% | median biggest-turn share | median max context |")
out.append("|---|---|---|---|---|---|---|---|---|")
for (task, group), xs in agg.items():
    p = sum(1 for x in xs if x["code"] == "OK" and x["verdict"] == "pass")
    out.append(f"| {task} | {group} | {len(xs)} | {p}/{len(xs)} | {statistics.median(x['tokens'] for x in xs):.0f} | {statistics.median(x['turns'] for x in xs):.0f} | {statistics.median(x['think'] for x in xs):.0f} | {statistics.median(x['big'] for x in xs):.0f}% | {statistics.median(x['ctx'] for x in xs):.0f} |")
open("q3stats.md", "w").write("\n".join(out) + "\n"); print("\n".join(out))
