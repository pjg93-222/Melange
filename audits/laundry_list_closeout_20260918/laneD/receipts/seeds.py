import json,os,sys
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
R=r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
for name in ('budget_frontier_electoral.json','budget_frontier.json'):
    d=json.load(open(R+r'\data\money\%s'%name,encoding='utf-8'))
    T=d['topics']
    print('### '+name)
    tc=td=0; kf=0
    for lab,t in T.items():
        tc+=t.get('contest_seeds',0); td+=t.get('defend_seeds',0)
        kf+=1 if t.get('knee_found') else 0
        n=len(t.get('path',[]))-1
        print('   %-32s base %6.1f  end %6.1f  seeds %2d  contest %d defend %d  knee %-8s %s'%(
            lab[:32],t['base'],t['path'][-1]['spread'],n,t.get('contest_seeds',0),t.get('defend_seeds',0),
            t.get('knee'),t.get('knee_found')))
    print('   TOTAL contest_seeds=%d defend_seeds=%d ; knee_found %d/%d topics'%(tc,td,kf,len(T)))
    pk=sorted(set(k for t in T.values() for p in t['path'] for k in p.keys()))
    print('   path-entry keys: %s'%pk)
    print('   sample path[0:3] of Interchange: %s'%json.dumps(T['Interchange']['path'][:3]))
    print()
