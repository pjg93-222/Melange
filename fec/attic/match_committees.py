import csv, sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
# committee master: CMTE_ID|CMTE_NM|...|CMTE_TP(10)|...|ORG_TP(13)|CONNECTED_ORG_NM(14)|CAND_ID(15)
cm=[]
with open('cm.txt', encoding='latin-1') as f:
    for line in f:
        p=line.rstrip('\n').split('|')
        if len(p)>=15: cm.append(p)
print(f'committees: {len(cm)}')
# entity -> distinctive search token(s)
banks={
 'Arvest Bank':r'ARVEST','JPMorgan Chase':r'JPMORGAN','Amalgamated Bank':r'AMALGAMATED',
 'Woodforest Natl Bank':r'WOODFOREST','Wells Fargo':r'WELLS FARGO','American Bankers Assn':r'AMERICAN BANKERS ASS',
 'Bank of America':r'BANK OF AMERICA','1st Financial Bank USA':r'1ST FINANCIAL BANK','Truist Financial':r'TRUIST',
 'Citigroup':r'CITIGROUP','Citizens First Bank':r'CITIZENS FIRST','Beneficial State Bank':r'BENEFICIAL STATE',
 'ICBA':r'INDEPENDENT COMMUNITY BANKERS','PNC Financial':r'\bPNC\b','US Bancorp':r'US BANCORP|U\.S\. BANCORP',
 'Regions Financial':r'REGIONS FINANCIAL','First Premier Bank':r'FIRST PREMIER','Emigrant Bank':r'EMIGRANT',
 'Toronto-Dominion':r'TORONTO.DOMINION|\bTD \b|TD BANK','IntraFi Network':r'INTRAFI',
 'Sherman Financial':r'SHERMAN FINANCIAL','Advance Financial':r'ADVANCE FINANCIAL','GreenSky':r'GREENSKY',
 'Discover Financial':r'DISCOVER FINANCIAL','Golub Capital':r'GOLUB','American Express':r'AMERICAN EXPRESS',
 'Oto Analytics':r'OTO ANALYTICS|\bOMNI\b','Visa Inc':r'\bVISA\b','Capital One':r'CAPITAL ONE',
 'American Financial Svcs Assn':r'AMERICAN FINANCIAL SERVICES','Amscot Financial':r'AMSCOT','MasterCard':r'MASTERCARD',
 'Tower Loan':r'TOWER LOAN','Ally Financial':r'ALLY FINANCIAL','Synchrony Financial':r'SYNCHRONY',
 'Dollar Loan Center':r'DOLLAR LOAN','Concord Servicing':r'CONCORD SERVICING',
}
cus={
 "America's Credit Unions":r'CREDIT UNION NATIONAL|AMERICA.S CREDIT UNION|CULAC|NAFCU',
 'SchoolsFirst FCU':r'SCHOOLSFIRST','CUNA Mutual':r'CUNA MUTUAL','Boeing Employees CU':r'BOEING EMPLOYEES',
 'Navy Federal CU':r'NAVY FEDERAL','South Carolina FCU':r'SOUTH CAROLINA FEDERAL','Kinecta FCU':r'KINECTA',
 'Elevations CU':r'ELEVATIONS CREDIT','Truliant FCU':r'TRULIANT','GoWest CU Assn':r'GOWEST|NORTHWEST CREDIT UNION|MOUNTAIN WEST CREDIT',
 'Wescom CU':r'WESCOM','Security Service FCU':r'SECURITY SERVICE','Valley Strong CU':r'VALLEY STRONG',
 'CU of Southern CA':r'CREDIT UNION OF SOUTHERN','California CU':r'CALIFORNIA CREDIT UNION','Mountain America CU':r'MOUNTAIN AMERICA',
}
def find(tok):
    rx=re.compile(tok)
    hits=[]
    for p in cm:
        nm=p[1]; org=p[13]
        if rx.search(nm) or rx.search(org):
            hits.append((p[0],nm,p[9],org))  # id,name,type,connected
    return hits
import json
xwalk={}
for grp,ents in (('BANK',banks),('CU',cus)):
    print(f'\n===== {grp} =====')
    for ent,tok in ents.items():
        h=find(tok)
        xwalk[ent]={'grp':grp,'cmtes':[x[0] for x in h]}
        if not h: print(f'  [NO MATCH] {ent}  (tok {tok})')
        else:
            shown='; '.join(f'{x[0]}:{x[1][:38]}' for x in h[:3])
            print(f'  {ent:28s} -> {len(h)} cmte | {shown}')
json.dump(xwalk, open('xwalk.json','w'))
