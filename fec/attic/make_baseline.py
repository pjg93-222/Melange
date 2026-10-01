import shutil,os,datetime,json,sys
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
B=r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
bdir=os.path.join(B,'baseline'); os.makedirs(bdir,exist_ok=True)
# the decision-relevant outputs a scenario perturbs and is compared against
files=['category_stance.json','per_topic_alloc.json','data/lobbying/per_topic_coalition.json','bipartisan.json','data/engine/congestion.json']
copied=[]
for f in files:
    p=os.path.join(B,f)
    if os.path.exists(p):
        destination=os.path.join(bdir,f); os.makedirs(os.path.dirname(destination),exist_ok=True)
        shutil.copy(p,destination); copied.append(f)
man={'created':datetime.datetime.now().isoformat(timespec='minutes'),'seed':7,'MC':20,'budget':2_000_000,'cap':50_000,'files':copied}
json.dump(man,open(os.path.join(bdir,'manifest.json'),'w'),indent=1)
print('BASELINE frozen %s  (%d outputs) -> %s'%(man['created'],len(copied),bdir))
print('scenarios now diff current state vs this baseline via scenario_diff.py')
