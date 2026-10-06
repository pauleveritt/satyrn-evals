"""Per-cell scan of the campaign nights (and any night given): turns, tokens,
finish_nudged turn, git commit calls, last green test run, tool calls after nudge.
Counts: turns from turn_start; tokens from assistant message_end usage.output;
tool calls from tool_execution_start; guard firings from entry_appended custom."""
import json, sys, os, re, collections
def scan(cell):
    turns=0; tokens=0; calls=[]; nudge_turn=None; guards=collections.Counter()
    results={}  # toolCallId -> (turn, text, isError)
    green_turns=[]; red_turns=[]; last_green=None; last_test=None
    commits=[]; resumes=0
    cwd=None
    last_stop=None
    for line in open(os.path.join(cell,'transcript.txt'), encoding='utf-8', errors='replace'):
        try: e=json.loads(line)
        except Exception: continue
        t=e.get('type')
        if t=='session': cwd=e.get('cwd')
        elif t=='turn_start': turns+=1
        elif t=='message_end':
            m=e.get('message',{})
            if m.get('role')=='assistant':
                u=m.get('usage') or {}
                o=u.get('output')
                if isinstance(o,int): tokens+=o
                last_stop=m.get('stopReason')
        elif t=='tool_execution_start':
            name=e.get('toolName'); args=e.get('args') or {}
            cmd=args.get('command') if isinstance(args,dict) else None
            path=args.get('path') if isinstance(args,dict) else None
            calls.append((turns,name,cmd,path,e.get('toolCallId')))
            if name=='bash' and cmd and re.search(r'\bgit\s+commit\b',cmd): commits.append((turns,cmd[:120]))
        elif t=='tool_execution_end':
            r=e.get('result') or {}
            txt=''
            c=r.get('content') if isinstance(r,dict) else None
            if isinstance(c,list):
                txt=' '.join(p.get('text','') for p in c if isinstance(p,dict))
            elif isinstance(c,str): txt=c
            name=e.get('toolName')
            if name in ('bash','self_test'):
                m=re.search(r'(\d+) passed',txt); f=re.search(r'(\d+) failed',txt); er=re.search(r'(\d+) errors?\b',txt)
                if m or f or 'self_test' in txt or name=='self_test':
                    ok = (m is not None) and not f and not er and 'error' not in txt.lower()[:0]
                    if name=='self_test':
                        ok = ('exit_code": 0' in txt) or ('"exit_code": 0' in txt) or ('passed' in txt and 'failed' not in txt)
                    last_test=(turns,name,ok)
                    if ok: green_turns.append(turns); last_green=turns
                    else: red_turns.append(turns)
        elif t=='entry_appended':
            en=e.get('entry',{})
            if en.get('type')=='custom':
                k=en.get('customType'); guards[k]+=1
                if k=='finish_nudged' and nudge_turn is None: nudge_turn=turns
    a=json.load(open(os.path.join(cell,'attempt.json')))
    after=[c for c in calls if nudge_turn is not None and c[0]>nudge_turn]
    edits_after=[c for c in after if c[1] in ('edit','write')]
    return dict(cell=os.path.basename(cell)[-13:], code=a['code'], verdict=a.get('verdict'), turns=turns, tokens=tokens,
                calls=len(calls), nudge=nudge_turn, calls_after_nudge=len(after), edits_after_nudge=len(edits_after),
                commits=commits, last_green=last_green, greens=len(green_turns), last_test=last_test, guards=dict(guards), cwd=cwd, last_stop=last_stop,
                line=a.get('line_crossed'), tripped=a.get('tripped_patch_path'))
if __name__=='__main__':
    for night in sys.argv[1:]:
        for arm in ('baseline','engine'):
            p=os.path.join(night,arm)
            if not os.path.isdir(p): continue
            for c in sorted(os.listdir(p)):
                if not c.startswith('selfhost'): continue
                r=scan(os.path.join(p,c))
                print(json.dumps({'night':os.path.basename(night)[-1:],'arm':arm,**r}))
