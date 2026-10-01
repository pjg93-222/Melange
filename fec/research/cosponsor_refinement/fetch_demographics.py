"""Historical Census ACS, including the pre-table-format 2019 release."""
import collections
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import io
import re
import zipfile
import threading
import time

import requests

from common import OUT, digest, log, stamp, write_json

BASE='https://www2.census.gov/programs-surveys/acs/summary_file/'
VARIABLES={
 'population':('B01003',1),'median_age':('B01002',1),'median_household_income':('B19013',1),
 'poverty_universe':('B17001',1),'below_poverty':('B17001',2),
 'occupied_housing':('B25003',1),'renter_housing':('B25003',3)}
CACHE=OUT/'acs_sources'
RECEIPTS=[]
REQUEST_LOCK=threading.Lock()
LAST_REQUEST=0.0


def cached(url):
    CACHE.mkdir(exist_ok=True)
    key=url.removeprefix(BASE).replace('/','__')
    path=CACHE/key
    if not path.exists():
        global LAST_REQUEST
        for attempt in range(4):
            with REQUEST_LOCK:
                delay=max(0,1.0-(time.monotonic()-LAST_REQUEST))
                if delay:time.sleep(delay)
                LAST_REQUEST=time.monotonic()
            response=requests.get(url,timeout=(10,60))
            if response.status_code!=429:break
            retry=response.headers.get('Retry-After','30')
            time.sleep(min(60,max(15,float(retry) if retry.isdigit() else 30)))
        response.raise_for_status()
        path.write_bytes(response.content)
    RECEIPTS.append(dict(url=url,path=str(path),sha256=digest(path),observed_utc=stamp()))
    return path.read_bytes()


def number(value):
    try:
        n=float(value)
        return n if n>=0 else None
    except (ValueError,TypeError):return None


def legacy_state(args):
    directory,lookup=args
    root=BASE+'2019/data/1_year_seq_by_state/'+directory+'/'
    # Directory listings supply native state abbreviations and geography file names.
    listing=cached(root).decode('utf-8')
    geo_name=re.search(r'href="(g20191[a-z]{2}\.csv)"',listing).group(1)
    abbrev=geo_name[6:8]
    geos={}
    for row in csv.reader(io.StringIO(cached(root+geo_name).decode('cp1252'))):
        if row[2] in ['040','500'] and row[3]=='00':
            geos[row[4]]=dict(geoid=row[48],name=row[49],state_abbr=row[1],year=2019,
                             geography='state' if row[2]=='040' else 'district',values={},moe90={})
    for seq in sorted({lookup[t]['sequence'] for t,i in VARIABLES.values()}):
        payload=cached(root+f'20191{abbrev}{seq}000.zip')
        with zipfile.ZipFile(io.BytesIO(payload)) as z:
            for prefix,field in [('e','values'),('m','moe90')]:
                name=next(n for n in z.namelist() if n.startswith(prefix))
                for row in csv.reader(io.StringIO(z.read(name).decode('utf-8-sig'))):
                    if row[5] not in geos:continue
                    for label,(table,line) in VARIABLES.items():
                        if lookup[table]['sequence']==seq:
                            index=lookup[table]['start']-1+line-1
                            geos[row[5]][field][label]=number(row[index])
    return list(geos.values())


def modern(year):
    geos={}
    for table in sorted({t for t,i in VARIABLES.values()}):
        u=BASE+f'{year}/table-based-SF/data/1YRData/acsdt1y{year}-{table.lower()}.dat'
        for row in csv.DictReader(io.StringIO(cached(u).decode('utf-8-sig')),delimiter='|'):
            g=row['GEO_ID']
            if not (g.startswith('0400000US') or g.startswith('5001800US') or g.startswith('5001700US')):continue
            level='state' if g.startswith('040') else 'district'
            if level=='district' and year==2021:continue
            # Normalize Census format across legacy and modern release containers.
            geoid=('04000US' if level=='state' else '50000US')+g.split('US')[1]
            record=geos.setdefault(geoid,dict(geoid=geoid,name='',year=year,geography=level,values={},moe90={}))
            for label,(t,i) in VARIABLES.items():
                if t==table:
                    record['values'][label]=number(row[f'{table}_E{i:03d}'])
                    record['moe90'][label]=number(row[f'{table}_M{i:03d}'])
    return list(geos.values())


def run(repair=False):
    suffix='_v2' if repair else ''
    if (OUT/f'demographics_audit{suffix}.json').exists():raise RuntimeError('Demographic snapshot exists')
    data=cached(BASE+'2019/documentation/user_tools/ACS_1yr_Seq_Table_Number_Lookup.txt').decode('cp1252')
    lookup={r['Table ID']:dict(sequence=r['Sequence Number'],start=int(r['Start Position']))
            for r in csv.DictReader(io.StringIO(data)) if r['Start Position'] and r['Table ID'] in {t for t,i in VARIABLES.values()}}
    root=BASE+'2019/data/1_year_seq_by_state/'
    links=re.findall(r'href="([A-Za-z]+/)"',cached(root).decode('utf-8'))
    directories=[x.rstrip('/') for x in links if x!='UnitedStates/']
    rows=[];failures=[]
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures={pool.submit(legacy_state,(d,lookup)):d for d in directories}
        for i,future in enumerate(as_completed(futures),1):
            try:rows.extend(future.result())
            except Exception as e:failures.append(dict(state=futures[future],error=str(e)))
            if i%10==0:log(f'ACS2019: {i}/{len(directories)} jurisdictions; {len(failures)} failures')
    for year in [2021,2022]:rows.extend(modern(year))
    path=OUT/f'historical_demographics{suffix}.json';write_json(path,rows)
    audit=dict(completed_utc=stamp(),counts=dict(collections.Counter(f"{r['year']}:{r['geography']}" for r in rows)),
               failures=failures,variables=VARIABLES,records_sha256=digest(path),sources=RECEIPTS,
               note='Raw estimates and 90% MOEs retained. Release-date and boundary guards are applied when constructing features.')
    write_json(OUT/f'demographics_audit{suffix}.json',audit);log(f"Demographic retrieval complete: {audit['counts']}; failures={len(failures)}")


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--repair-missing',action='store_true')
    run(parser.parse_args().repair_missing)
