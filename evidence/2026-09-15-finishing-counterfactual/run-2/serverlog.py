import re, glob, statistics, json, collections
pat = re.compile(r"^(?P<ts>\S+ \S+) .*Chat completion: model=(?P<model>[^,]+), (?P<tok>\d+) tokens in (?P<sec>[\d.]+)s \((?P<rate>[\d.]+) tok/s\), prompt: (?P<prompt>\d+), finish_reason=(?P<fin>\w+), max_tokens=(?P<mt>\d+)")
rows = []
for f in sorted(glob.glob("/Users/pauleveritt/.omlx/logs/server.log*")):
    for line in open(f, errors="replace"):
        m = pat.match(line)
        if m and "Ornith-1.5-9B" in m["model"]:
            rows.append(dict(ts=m["ts"], tok=int(m["tok"]), sec=float(m["sec"]), rate=float(m["rate"]), prompt=int(m["prompt"]), fin=m["fin"], mt=int(m["mt"]), file=f))
print("completions:", len(rows), "files:", sorted(set(r["file"].split("/")[-1] for r in rows)))
by_day = collections.Counter(r["ts"][:10] for r in rows); print("by day:", dict(sorted(by_day.items())))
sept = [r for r in rows if r["ts"][:10] >= "2026-09-14" and r["mt"] == 32000]
print("2026-09-14/15 max_tokens=32000 completions:", len(sept))
bins = [(0,5000),(5000,10000),(10000,20000),(20000,40000),(40000,80000),(80000,160000),(160000,10**7)]
print("\ndecode rate by prompt size (2026-09-14/15 cells, completions with >= 100 output tokens):")
for lo,hi in bins:
    xs = [r["rate"] for r in sept if lo <= r["prompt"] < hi and r["tok"] >= 100]
    if xs: print(f"  prompt {lo:>6}-{hi:<6}: n={len(xs):4d} median {statistics.median(xs):5.1f} tok/s  p10 {sorted(xs)[len(xs)//10]:5.1f}  p90 {sorted(xs)[-max(1,len(xs)//10)]:5.1f}")
print("\nfinish_reason counts:", collections.Counter(r["fin"] for r in sept))
big = sorted([r for r in sept if r["tok"] >= 8000], key=lambda r: -r["tok"])
print("\ncompletions >= 8000 output tokens:", len(big))
for r in big[:20]: print(f"  {r['ts']} tok={r['tok']:6d} sec={r['sec']:7.1f} rate={r['rate']:5.1f} prompt={r['prompt']:6d} fin={r['fin']}")
tot_tok = sum(r["tok"] for r in sept); tot_sec = sum(r["sec"] for r in sept)
print(f"\ntotal output tokens {tot_tok}, total decode seconds {tot_sec:.0f} ({tot_sec/3600:.1f} h); mean rate {tot_tok/tot_sec:.1f} tok/s")
# concurrency: count overlapping completions by time window
import datetime
def parse(ts): return datetime.datetime.strptime(ts[:23], "%Y-%m-%d %H:%M:%S,%f")
ivs = [(parse(r["ts"]) - datetime.timedelta(seconds=r["sec"]), parse(r["ts"]), r) for r in sept]
ivs.sort(key=lambda x: x[0])
# for each completion, count how many others overlap its midpoint
import bisect
conc = collections.Counter(); rate_by_conc = collections.defaultdict(list)
for a,b,r in ivs:
    mid = a + (b-a)/2
    k = sum(1 for a2,b2,_ in ivs if a2 <= mid <= b2)
    conc[k] += 1
    if r["tok"] >= 100 and r["prompt"] < 20000: rate_by_conc[k].append(r["rate"])
print("\nconcurrency at completion midpoint:", dict(sorted(conc.items())))
for k in sorted(rate_by_conc): print(f"  k={k}: n={len(rate_by_conc[k])} median per-stream rate {statistics.median(rate_by_conc[k]):.1f} tok/s (prompt<20k, >=100 tok) -> total ~{k*statistics.median(rate_by_conc[k]):.0f}")
json.dump(sept, open("serverlog_sept.json","w"))
