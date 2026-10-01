"""Historical shared-broadcast features; research only, no cosponsorship labels.

Read INTERVIEW turns for the two calendar years preceding Congress 117/118.
The source's `chamber` field is program metadata, not Congressional chamber.
Same broadcast does not establish direct interaction, endorsement or persuasion.
No production module is imported: several legacy producers execute on import.
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import hashlib
import html
import io
import itertools
import json
from pathlib import Path
import re
import sqlite3
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'outputs/cosponsor_universe_20260905'
WINDOWS = {117: ('2019-01-03', '2021-01-03'),
           118: ('2021-01-03', '2023-01-03')}
MIN_TURNS, MIN_WORDS, MAX_MEMBERS = 4, 200, 8


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def norm(value):
    value = unicodedata.normalize('NFKD', str(value))
    return re.sub(r'[^a-z0-9]+', ' ', value.encode('ascii', 'ignore').decode().lower()).strip()


def normalized_turn(text):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', html.unescape(text))).strip()


def episode_key(package):
    parts = urlsplit(str(package).strip())
    if parts.scheme not in ('https', 'http') or not parts.netloc:
        return None
    path = re.sub(r'/segment/\d+.*$', '', parts.path).rstrip('/') or '/'
    # Preserve article ID parameters, drop tracking only. HTTPS equivalence dedups mirrors.
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if not k.lower().startswith('utm_') and k.lower() not in ('fbclid', 'gclid')]
    host = parts.netloc.lower().removeprefix('www.')
    return urlunsplit(('https', host, path, urlencode(sorted(query)), ''))


def date_value(value):
    try:
        d = dt.date.fromisoformat(str(value))
        return str(d) if str(d) == str(value) else None
    except (ValueError, TypeError):
        return None


def load_identities():
    base = ROOT / 'data/staffer_network/reference/congress-legislators'
    dirs = sorted(p for p in base.iterdir() if p.is_dir())
    if len(dirs) != 1:
        raise RuntimeError('Historical identity snapshot is ambiguous')
    aliases = collections.defaultdict(set)
    people, sources = {}, []
    for filename in ('legislators-current.yaml', 'legislators-historical.yaml'):
        p = dirs[0] / filename
        content = p.read_bytes()
        sources.append(dict(path=str(p),sha256=hashlib.sha256(content).hexdigest(),bytes=len(content)))
        for r in yaml.load(content, Loader=yaml.CSafeLoader):
            mid = r['id'].get('bioguide')
            if not mid:
                continue
            terms = [dict(start=str(t['start']), end=str(t['end']),
                          chamber='House' if t['type']=='rep' else 'Senate',
                          party=t.get('party', 'Unknown'), state=t['state'])
                     for t in r.get('terms', []) if t['type'] in ('rep', 'sen')]
            if not terms:
                continue
            nm = r['name']
            name = nm.get('official_full') or nm.get('first','')+' '+nm.get('last','')
            people[mid] = dict(name=name, terms=terms)
            names = [name, nm.get('first','')+' '+nm.get('last','')]
            if nm.get('nickname'):
                names.append(nm['nickname']+' '+nm.get('last',''))
            for value in names:
                aliases[norm(value)].add(mid)
    p = ROOT/'fec/legislators.csv'
    content = p.read_bytes()
    sources.append(dict(path=str(p),sha256=hashlib.sha256(content).hexdigest(),bytes=len(content)))
    for r in csv.DictReader(io.StringIO(content.decode('utf-8-sig'))):
        if r['bioguide_id'] in people:
            aliases[norm(r['full_name'])].add(r['bioguide_id'])
    return people, aliases, sources


def resolve(member, day, people, aliases):
    matches = []
    for mid in sorted(aliases.get(norm(member), set())):
        terms = [t for t in people[mid]['terms'] if t['start'] <= day < t['end']]
        if terms:
            term = max(terms, key=lambda t:t['start'])
            matches.append((mid,term['chamber']))
    return matches[0] if len(matches)==1 else None


def build_window(rows, people, aliases, start, cutoff):
    counts = collections.Counter()
    cells = collections.defaultdict(dict)
    source_digest = hashlib.sha256()
    for row in rows:
        rid, member, day, source, package, stored_words, text = row
        source_digest.update((json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n').encode())
        counts['raw_selected_rows'] += 1
        valid_day = date_value(day)
        if not valid_day or not start <= valid_day < cutoff:
            counts['invalid_or_outside_date'] += 1
            continue
        if source != 'INTERVIEW':
            counts['non_interview_rejected'] += 1
            continue
        identity = resolve(member,valid_day,people,aliases)
        if identity is None:
            counts['unresolved_or_not_serving_rows'] += 1
            continue
        ep = episode_key(package)
        if ep is None:
            counts['missing_or_non_url_package'] += 1
            continue
        text = normalized_turn(text or '')
        if not text:
            counts['empty_text'] += 1
            continue
        mid,chamber=identity
        # Case-folding here conservatively collapses identical quoted repeats.
        key=hashlib.sha256(text.casefold().encode()).hexdigest()
        cell = cells[(ep,valid_day,mid,chamber)]
        if key in cell:
            counts['duplicate_turn_rows'] += 1
            cell[key]['source_rowids'].append(rid)
            continue
        words = len(re.findall(r"\b\w+(?:['’-]\w+)*\b",text))
        counts['stored_wordcount_differs'] += int(stored_words != words)
        cell[key]=dict(words=words,source_rowids=[rid])
        counts['accepted_unique_turns'] += 1
    episodes = collections.defaultdict(list)
    member_stats=collections.defaultdict(collections.Counter)
    for (ep,day,mid,chamber),turns in sorted(cells.items()):
        words=sum(t['words'] for t in turns.values())
        st=member_stats[mid]
        st['unique_turns']+=len(turns);st['words']+=words;st['observed_episodes']+=1
        if len(turns)<MIN_TURNS and words<MIN_WORDS:
            counts['below_floor_member_episodes']+=1
            continue
        st['qualifying_episodes']+=1
        episodes[(ep,day)].append(dict(bioguide=mid,chamber_at_event=chamber,
            turns=len(turns),words=words,turn_sha256=sorted(turns),
            source_rowids=sorted(rid for t in turns.values() for rid in t['source_rowids'])))
    # Exact same-date qualifying participant evidence under different URLs is one
    # observation. Preserve all source URLs/row IDs but remove repeated coverage
    # and edge mass. This is a conservative content-identity rule, not a fuzzy
    # similarity or outcome-driven choice.
    canonical_episodes={};signature_lookup={}
    counts['accepted_unique_turns_before_cross_url_dedup']=counts['accepted_unique_turns']
    for (ep,day),participants in sorted(episodes.items()):
        signature=(day,tuple(sorted((p['bioguide'],tuple(p['turn_sha256'])) for p in participants)))
        if signature in signature_lookup:
            old_key=signature_lookup[signature]
            old=canonical_episodes[old_key]
            old['source_aliases'].append(ep)
            old_people={p['bioguide']:p for p in old['participants']}
            counts['cross_url_duplicate_qualifying_episodes']+=1
            counts['cross_url_duplicate_qualifying_member_cells']+=len(participants)
            for p in participants:
                st=member_stats[p['bioguide']]
                st['qualifying_episodes']-=1;st['observed_episodes']-=1
                st['unique_turns']-=p['turns'];st['words']-=p['words']
                counts['accepted_unique_turns']-=p['turns']
                original=old_people[p['bioguide']]
                original['source_rowids']=sorted(set(original['source_rowids']+p['source_rowids']))
            continue
        signature_lookup[signature]=(ep,day)
        canonical_episodes[(ep,day)]=dict(participants=participants,source_aliases=[ep])
    ledger=[];pairs=collections.Counter()
    for (ep,day),episode in sorted(canonical_episodes.items()):
        participants=episode['participants']
        if len(participants)>MAX_MEMBERS:
            counts['large_episodes_excluded']+=1
            continue
        if len(participants)<2:
            counts['single_member_episodes']+=1
            continue
        counts['shared_episodes']+=1
        for p in participants:
            member_stats[p['bioguide']]['shared_episodes']+=1
        for left,right in itertools.combinations(sorted(p['bioguide'] for p in participants),2):
            assert left!=right
            pairs[(left,right)]+=1
        ledger.append(dict(date=day,episode=ep,source_aliases=episode['source_aliases'],participants=participants,
            relation='shared_broadcast_not_verified_interaction'))
    counts['unique_dyads']=len(pairs)
    counts['repeat_dyads']=sum(v>=2 for v in pairs.values())
    counts['people_with_observed_turns']=len(member_stats)
    counts['people_with_shared_broadcast']=sum(s['shared_episodes']>0 for s in member_stats.values())
    counts['qualifying_member_episodes']=sum(s['qualifying_episodes'] for s in member_stats.values())
    return dict(counts=dict(counts),stats=member_stats,pairs=pairs,ledger=ledger,
                logical_source_sha256=source_digest.hexdigest())


def boundary_checks():
    pp={f'M{i}':dict(name=f'Member{i}',terms=[dict(start='2010-01-03',end='2023-01-03',chamber='House')]) for i in range(10)}
    aa={norm(v['name']):{k} for k,v in pp.items()}
    long=' '.join(['word']*201)
    rows=[(1,'Member0','2020-01-01','INTERVIEW','https://x.test/show/segment/1',201,long),
          (2,'Member0','2020-01-01','INTERVIEW','https://x.test/show/segment/2',201,long),
          (3,'Member1','2020-01-01','INTERVIEW','http://www.x.test/show?utm_source=x',201,long),
          (4,'Member2','2021-01-03','INTERVIEW','https://x.test/show',201,long),
          (5,'Member2','2009-01-01','INTERVIEW','https://x.test/show',201,long),
          (6,'Unknown','2020-01-01','INTERVIEW','https://x.test/show',201,long),
          (7,'Member2','2020-01-01','CREC','https://x.test/show',201,long)]
    r=build_window(rows,pp,aa,'2019-01-03','2021-01-03')
    assert dict(r['pairs'])=={('M0','M1'):1}
    assert r['counts']['duplicate_turn_rows']==1
    assert r['counts']['invalid_or_outside_date']==2
    assert r['counts']['unresolved_or_not_serving_rows']==1
    assert r['counts']['non_interview_rejected']==1
    mirrored=rows[:3]+[(rid+100,member,day,source,'https://x.test/mirrored',nwords,text)
                     for rid,member,day,source,package,nwords,text in [rows[0],rows[2]]]
    dedup=build_window(mirrored,pp,aa,'2019-01-03','2021-01-03')
    assert dict(dedup['pairs'])=={('M0','M1'):1}
    assert dedup['counts']['cross_url_duplicate_qualifying_episodes']==1
    assert dedup['stats']['M0']['qualifying_episodes']==1
    at_lower=[(rid,member,'2019-01-03',source,package,nwords,text)
              for rid,member,day,source,package,nwords,text in rows[:3]]
    inclusive=build_window(at_lower,pp,aa,'2019-01-03','2021-01-03')
    assert dict(inclusive['pairs'])=={('M0','M1'):1}
    many=[(i,f'Member{i}','2020-01-01','INTERVIEW','https://x.test/large',201,long) for i in range(9)]
    rr=build_window(many,pp,aa,'2019-01-03','2021-01-03')
    assert not rr['pairs'] and rr['counts']['large_episodes_excluded']==1
    assert resolve('Member0','2023-01-03',pp,aa) is None
    assert episode_key('https://x.test/a?id=1')!=episode_key('https://x.test/a?id=2')
    return ['cutoff_exclusive','lower_bound_inclusive','non_interview_excluded',
        'unique_serving_identity','end_of_service_exclusive','segment_tracking_dedup',
        'large_episode_excluded','article_id_query_preserved','exact_cross_url_episode_dedup']


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--out',type=Path,default=OUT)
    ap.add_argument('--replace-reviewed',action='store_true')
    args=ap.parse_args();out=args.out.resolve()
    out.mkdir(parents=True,exist_ok=True)
    owned=[out/'relational_receipt.json']+[out/f'relational_{kind}_{cg}.{suffix}'
        for cg in WINDOWS for kind,suffix in [('graph','npz'),('members','csv'),('episodes','jsonl')]]
    if any(p.exists() for p in owned):
        if not args.replace_reviewed:
            raise RuntimeError('Refusing to overwrite existing relational outputs')
        for p in owned:
            archived=out/'relational_pre_review'/p.name
            if not p.exists() or not archived.exists() or sha(p)!=sha(archived):
                raise RuntimeError('Review replacement requires byte-exact archived originals')
    checks=boundary_checks()
    people,aliases,sources=load_identities()
    db=ROOT/'social_media.db';before=sha(db)
    con=sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True)
    con.execute('PRAGMA query_only=1');con.execute('BEGIN')
    results={}
    for cg,(start,cutoff) in WINDOWS.items():
        rows=con.execute('SELECT rowid,member,date,source,package,nwords,text FROM speeches '
            "WHERE source='INTERVIEW' AND date>=? AND date<? ORDER BY rowid",(start,cutoff))
        results[cg]=build_window(rows,people,aliases,start,cutoff)
    con.rollback();con.close()
    if sha(db)!=before:
        raise RuntimeError('Source database changed while reading; no outputs issued')
    sources.append(dict(path=str(db),sha256=before,bytes=db.stat().st_size,
        mtime_utc=dt.datetime.fromtimestamp(db.stat().st_mtime,dt.timezone.utc).isoformat()))
    for source in sources:
        if sha(source['path'])!=source['sha256']:
            raise RuntimeError('Identity/source changed while reading')
    receipts={};artifacts=[]
    for cg,r in results.items():
        start,cutoff=WINDOWS[cg]
        target_end=f'{int(cutoff[:4])+2}-01-03'
        targets={mid for mid,p in people.items() if any(t['start']<target_end and t['end']>cutoff for t in p['terms'])}
        ids=sorted(targets|set(r['stats']));index={mid:i for i,mid in enumerate(ids)}
        counts=np.zeros((len(ids),len(ids)),dtype=np.float64)
        for (left,right),n in r['pairs'].items():
            i,j=index[left],index[right];counts[i,j]=counts[j,i]=n
        exposure=np.array([r['stats'][mid]['qualifying_episodes'] for mid in ids],dtype=float)
        denom=np.sqrt(exposure[:,None]*exposure[None,:])
        adj=np.divide(counts,denom,out=np.zeros_like(counts),where=denom>0)
        assert np.isfinite(adj).all() and (adj>=0).all() and (adj<=1+1e-12).all()
        assert np.allclose(adj,adj.T) and not np.diag(adj).any()
        assert all(start<=e['date']<cutoff for e in r['ledger'])
        graph=out/f'relational_graph_{cg}.npz'
        np.savez_compressed(graph,ids=np.array(ids,dtype='U16'),adjacency=adj.astype('f4'),
            raw_episode_counts=counts.astype('i4'),qualifying_episode_counts=exposure.astype('i4'),
            is_target_member=np.array([mid in targets for mid in ids]),
            window_start=np.array(start),cutoff_exclusive=np.array(cutoff),congress=np.array(cg))
        memberfile=out/f'relational_members_{cg}.csv'
        columns=['congress','bioguide','rel_unique_turns','rel_words','rel_observed_episodes',
            'rel_qualifying_episodes','rel_shared_episodes','rel_degree','rel_raw_strength',
            'rel_normalized_strength','rel_observed_coverage','rel_qualifying_coverage','rel_shared_coverage']
        with memberfile.open('w',encoding='utf8',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=columns);writer.writeheader()
            for mid in sorted(targets):
                s=r['stats'][mid];i=index[mid]
                d=dict(congress=cg,bioguide=mid)
                for field in ('unique_turns','words','observed_episodes','qualifying_episodes','shared_episodes'):
                    d['rel_'+field]=s[field]
                d.update(rel_degree=int((counts[i]>0).sum()),rel_raw_strength=int(counts[i].sum()),
                    rel_normalized_strength=float(adj[i].sum()),rel_observed_coverage=int(s['unique_turns']>0),
                    rel_qualifying_coverage=int(s['qualifying_episodes']>0),rel_shared_coverage=int(s['shared_episodes']>0))
                writer.writerow(d)
        ledgerfile=out/f'relational_episodes_{cg}.jsonl'
        with ledgerfile.open('w',encoding='utf8') as f:
            for row in r['ledger']:
                f.write(json.dumps(row,ensure_ascii=False,sort_keys=True)+'\n')
        for p in [graph,memberfile,ledgerfile]:
            artifacts.append(dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size))
        receipts[cg]=dict(window_start=start,cutoff_exclusive=cutoff,source_counts=r['counts'],
            logical_selected_rows_sha256=r['logical_source_sha256'],graph_nodes=len(ids),target_members=len(targets),
            target_members_with_observed_coverage=sum(r['stats'][m]['unique_turns']>0 for m in targets),
            target_members_with_shared_coverage=sum(r['stats'][m]['shared_episodes']>0 for m in targets),
            shared_episode_dates=[min((e['date'] for e in r['ledger']),default=None),max((e['date'] for e in r['ledger']),default=None)])
    receipt=dict(schema='cosponsor-universe-relational-features-v2',status='PASS_RETROSPECTIVE_EXTRACTION',
        revision_reason='Deduplicate exact same-date qualifying participant evidence across source URLs; preserve aliases and raw source row IDs.',
        previous_generation_archive=str(out/'relational_pre_review') if args.replace_reviewed else None,
        issued_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),code=dict(path=str(Path(__file__).resolve()),sha256=sha(__file__)),
        sources=sources,outputs=artifacts,splits=receipts,boundary_checks=checks,
        graph_definition='Undirected shared-broadcast episode counts divided by sqrt(qualifying episodes_i * qualifying episodes_j).',
        qualification='Shared broadcasts may contain sequential guests or clips. Not verified interaction/endorsement. Historical first-observed time absent; identity is machine-attributed and current collection coverage can be selective.',
        join_recipe=dict(member='CSV join (congress,bioguide) to frozen member IDs. Keep coverage indicators; zero is absence of observed source, not no relationship.',
            sponsor_tie='adjacency[index(candidate), index(sponsor)], missing IDs ->0 plus coverage flags.',
            earlier_coalition='S includes sponsor only if introduced<forecast and cosponsors only if join_date<forecast. sum(adj[candidate,j] for j in S)/sum(adj[candidate,:]), denominator0->0; retain numerator/count and coverage. Current-bill event dates are supplied by parent, not read here.',
            warning='Use117 graph for117 and118 graph for118; no119 extraction or tuning. Graph can include past members to preserve source universe; target member CSV is complete target-Congress roster.'))
    (out/'relational_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(status=receipt['status'],splits=receipts),indent=2))


if __name__=='__main__':
    main()
