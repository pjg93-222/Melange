import json,sys,os
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
# scenario_diff.py  <current.json> <baseline.json>  -> top per-member $ movers across topics
a=sys.argv[1] if len(sys.argv)>1 else r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\data\lobbying\per_topic_coalition.json'
b=sys.argv[2] if len(sys.argv)>2 else r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\baseline\data\lobbying\per_topic_coalition.json'
A=json.load(open(a)); B=json.load(open(b))
moves=[]; tot=0
for t in set(A)|set(B):
    c=A.get(t,{}); d=B.get(t,{})
    for n in set(c)|set(d):
        delta=c.get(n,0)-d.get(n,0)
        if delta: moves.append((delta,n,t)); tot+=abs(delta)
moves.sort(key=lambda x:-abs(x[0]))
print('DIFF %s  vs  %s'%(os.path.basename(a),os.path.basename(b)))
print('%d member-topic cells changed | total |Δ| $%s | members moved: %d'%(len(moves),f'{tot:,}',len({n for _,n,_ in moves})))
for delta,n,t in moves[:15]: print('   %+6dk  %-22s %s'%(delta//1000,n,t[:30]))
