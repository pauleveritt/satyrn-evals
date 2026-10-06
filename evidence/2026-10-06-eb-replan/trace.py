import json,re,sys
cell=sys.argv[1]; start=int(sys.argv[2]) if len(sys.argv)>2 else 0
turns=0
for line in open(cell+'/transcript.txt', errors='replace'):
    try: e=json.loads(line)
    except Exception: continue
    t=e.get('type')
    if t=='turn_start': turns+=1
    elif t=='tool_execution_start':
        a=e.get('args') or {}
        s=a.get('command') or a.get('path') or ''
        if turns>=start: print(f"t{turns} {e.get('toolName')}: {str(s)[:140]!r}")
    elif t=='tool_execution_end' and turns>=start:
        r=e.get('result') or {}
        c=r.get('content'); txt=''
        if isinstance(c,list): txt=' '.join(p.get('text','') for p in c if isinstance(p,dict))
        m=re.findall(r'\d+ passed|\d+ failed|\d+ errors?|exit_code\W+\d+|FAILED [^\s]+|ERROR [^\s]+|outside the contract[^.]*|refused[^.]*',txt)
        if m: print('    ->', m[:8])
    elif t=='entry_appended' and e.get('entry',{}).get('customType') in ('finish_nudged','self_test_detected','self_test_red_stop','scope_refused','loop_broken'):
        print(f"t{turns} [{e['entry']['customType']}]")
    elif t=='message_end' and e.get('message',{}).get('role')=='assistant' and turns>=start:
        m=e['message']; c=m.get('content')
        txt=' '.join(p.get('text','') for p in c if isinstance(p,dict) and p.get('type')=='text') if isinstance(c,list) else ''
        if txt.strip(): print(f"t{turns} A: {txt.strip()[:160]!r} stop={m.get('stopReason')}")
