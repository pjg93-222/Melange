import sys, re, collections
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
# committees that ACTUALLY give to federal candidates (appear in itpas2)
active=set()
for line in open('itpas2.txt',encoding='latin-1'):
    active.add(line.split('|',1)[0])
cm=[l.rstrip('\n').split('|') for l in open('cm.txt',encoding='latin-1') if l.count('|')>=14]

# ALL 60 entities the user gave, with search tokens (incl. the ones I omitted before)
ALL={
'F03':{'Arvest':r'ARVEST BANK','JPMorgan':r'JPMORGAN','Amalgamated Bank':r'AMALGAMATED BANK','Woodforest':r'WOODFOREST',
 'Wells Fargo':r'WELLS FARGO','American Bankers Assn':r'AMERICAN BANKERS ASSOCIATION','Bank of America':r'BANK OF AMERICA CORP',
 '1st Financial Bank':r'1ST FINANCIAL BANK|FIRST FINANCIAL BANK USA','Truist':r'TRUIST','Citigroup':r'CITIGROUP',
 'Citizens First Bank':r'CITIZENS FIRST','Beneficial State Bank':r'BENEFICIAL STATE','ICBA':r'INDEPENDENT COMMUNITY BANKERS',
 'PNC':r'PNC FINANCIAL','US Bancorp':r'BANCORP','Regions Financial':r'REGIONS FINANCIAL','First Premier Bank':r'FIRST PREMIER|PREMIER BANKCARD',
 'Emigrant Bank':r'EMIGRANT','Toronto-Dominion':r'TD BANK|TORONTO.DOMINION','IntraFi':r'INTRAFI|PROMONTORY INTERFINANCIAL'},
'CU':{"America's Credit Unions":r"AMERICA'S CREDIT UNION|CREDIT UNION NATIONAL ASSN|NAFCU",'SchoolsFirst':r'SCHOOLSFIRST',
 'CUNA Mutual':r'CUNA MUTUAL','Boeing Employees CU':r'BOEING EMPLOYEES','Navy Federal':r'NAVY FEDERAL','South Carolina FCU':r'SOUTH CAROLINA FEDERAL CREDIT',
 'Kinecta':r'KINECTA','Elevations CU':r'ELEVATIONS CREDIT','Truliant':r'TRULIANT','7-17 CU':r'SEVEN SEVENTEEN|7-17 CREDIT|717 CREDIT',
 'GoWest CU Assn':r'GOWEST|MOUNTAIN WEST CREDIT UNION|NORTHWEST CREDIT UNION','Wescom':r'WESCOM','American First CU':r'AMERICAN FIRST CREDIT',
 'Florida CU':r'FLORIDA CREDIT UNION','Security Service FCU':r'SECURITY SERVICE FEDERAL','Valley Strong CU':r'VALLEY STRONG',
 'CU of Southern CA':r'CREDIT UNION OF SOUTHERN','California CU':r'CALIFORNIA CREDIT UNION','TruWest CU':r'TRUWEST','Mountain America CU':r'MOUNTAIN AMERICA'},
'F05':{'Sherman Financial':r'SHERMAN FINANCIAL','Advance Financial':r'ADVANCE FINANCIAL|ADVANCE AMERICA','GreenSky':r'GREENSKY',
 'Discover':r'DISCOVER FINANCIAL','Golub Capital':r'GOLUB CAPITAL','American Express':r'AMERICAN EXPRESS','Oto Analytics':r'OTO ANALYTICS|ONDECK',
 'Visa':r'VISA','Capital One':r'CAPITAL ONE','Corporate Capital':r'CORPORATE CAPITAL','American Financial Svcs Assn':r'AMERICAN FINANCIAL SERVICES ASSN|AMERICAN FINANCIAL SERVICES ASSOCIATION',
 'Amscot':r'AMSCOT','MasterCard':r'MASTERCARD','Tower Loan':r'TOWER LOAN','Ally Financial':r'ALLY FINANCIAL','Synchrony':r'SYNCHRONY',
 'US Education Servicing':r'US EDUCATION SERVICING|NELNET','Dollar Loan Center':r'DOLLAR LOAN','Concord Servicing':r'CONCORD SERVICING','Deerpath Capital':r'DEERPATH'}}

for grp,ents in ALL.items():
    print(f'\n===== {grp} =====')
    for ent,tok in ents.items():
        rx=re.compile(tok)
        hits=[(p[0],p[1]) for p in cm if rx.search(p[1]) or rx.search(p[13])]
        act=[(cid,nm) for cid,nm in hits if cid in active]
        if act: print(f'  [PAC] {ent:26s} {act[0][0]}:{act[0][1][:40]}'+(f' (+{len(act)-1})' if len(act)>1 else ''))
        elif hits: print(f'  [committee but NO fed contribs] {ent:26s} {hits[0][1][:40]}')
        else: print(f'  [NO PAC at all] {ent}')
