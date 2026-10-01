"""Readable evidence dossiers with actual shared-bill lists and exact methodology."""
import json
import sqlite3
from collections import defaultdict
from pathlib import Path
from .data import ROOT,read_json,write_json,write_ndjson,digest
from .prepare_history import OUT
from .run_history import read_rows


def fmt(v,digits=3):return 'unavailable' if v is None else f'{v:.{digits}f}'
def pct(v):return 'unavailable' if v is None else f'{100*v:.1f}%'
def label(s):return s.replace('_',' ')


def main():
    results=read_json(OUT/'results.json');members=read_json(OUT/'members.json')
    rows=read_rows(OUT/'relationships.ndjson');lookup={(r['actor'],r['target']):r for r in rows}
    events=read_rows(OUT/'reviewed_events.ndjson');evmap=defaultdict(list)
    for e in events:evmap[tuple(sorted((e['actor'],e['target'])))].append(e)
    bills=read_rows(OUT/'bills.ndjson')
    directory=OUT/'pairs';directory.mkdir(exist_ok=True)
    # Evidence dossiers cover every reviewed dyad. Full matrices cover all dyads.
    pair_rows=[];bill_receipts=[]
    for (a,b),ee in sorted(evmap.items(),key=lambda kv:tuple(members[x]['name'] for x in kv[0])):
        ra,rb=lookup[(a,b)],lookup[(b,a)]
        shared=[bill for bill in bills if a in bill['joins'] and b in bill['joins']]
        direct_a=[bill for bill in bills if bill['sponsor']==b and a in bill['joins']]
        direct_b=[bill for bill in bills if bill['sponsor']==a and b in bill['joins']]
        if len(shared)!=ra['shared_bills'] or len(direct_a)!=ra['direct_bills'] or len(direct_b)!=rb['direct_bills']:
            raise AssertionError('Dossier bill recount disagrees with matrix')
        filename=f'{a}__{b}.md';path=directory/filename
        content=[f"# {members[a]['name']} — {members[b]['name']}", '',
            'Relationship evidence is dated; a historical statement is not automatically a claim about the present.', '',
            '| Direction | Friendship assessment | Public antagonism | Personal dislike inference |',
            '|---|---|---|---|']
        for r in [ra,rb]:content.append(f"| {r['actor_name']} → {r['target_name']} | {label(r['friendship'])} | {label(r['hostility'])} | {label(r['dislike'])} |")
        content+=['',f"Same party: **{ra['same_party']}**. Same state: **{ra['same_state']}**. Current DW1 distance: **{fmt(ra['ideology_distance'])}**. These describe the comparison context; none is a negative friendship weight.",
            '',f"Shared third-party bills: **{len(shared)}** across **{int(ra['shared_congresses'])} Congresses** and **{int(ra['shared_areas'])} policy areas**; **{int(ra['shared_original_bills'])}** jointly original. Neither signature later withdrawn on **{int(ra['shared_active_bills'])}** of the shared bills.",
            '', '| Measure | First → second | Second → first |','|---|---:|---:|',
            f"| Signed the other member's bills / opportunities | {int(ra['direct_bills'])}/{int(ra['direct_opportunities'])} | {int(rb['direct_bills'])}/{int(rb['direct_opportunities'])} |",
            f"| Direct propensity | {pct(ra['direct_propensity'])} | {pct(rb['direct_propensity'])} |",
            f"| Joined jointly / bills the other joined when eligible | {len(shared)}/{int(ra['shared_opportunities'])} | {len(shared)}/{int(rb['shared_opportunities'])} |",
            f"| Shared propensity | {pct(ra['shared_propensity'])} | {pct(rb['shared_propensity'])} |",
            f"| Shared-overlap comparison percentile | {pct(ra['shared_percentile'])} | {pct(rb['shared_percentile'])} |",
            f"| Direct-propensity comparison percentile | {pct(ra['direct_percentile'])} | {pct(rb['direct_percentile'])} |",
            f"| Work-network comparison percentile | {pct(ra['network_percentile'])} | {pct(rb['network_percentile'])} |",
            f"| Candidate comparison partners | {int(ra['peer_count'])} | {int(rb['peer_count'])} |",'',
            'A comparison percentile is a position among context-matched partners, not a friendship probability. Insufficient comparison partners leave the value unavailable.',
            '', '## Work history', '', '| Congress | Shared bills | First supports second | Second supports first |','|---|---:|---:|---:|']
        for c,cc in ra['by_congress'].items():content.append(f"| {c} | {cc['shared']} | {cc['direct']}/{cc['opportunities']} | {rb['by_congress'][c]['direct']}/{rb['by_congress'][c]['opportunities']} |")
        content+=['','## Personality and usual expression','',
            f"E/A/O compatibility: **{fmt(ra['compatibility']['EAO_similarity'])}** on a 0–1 similarity scale ({ra['compatibility']['traits_observed']} observed traits). All observed trait similarities: "+', '.join(f'{t}={v:.3f}' for t,v in ra['compatibility']['traits'].items())+'.',
            '', '| Speaker | E percentile | A percentile | Warm-cue turns / all turns | Reviewed-warmth multiplier |',
            '|---|---:|---:|---:|---:|']
        for r in [ra,rb]:
            x=r['expression'];content.append(f"| {r['actor_name']} | {pct(x['E_percentile'])} | {pct(x['A_percentile'])} | {x['warm_turns']}/{x['turns']} ({pct(x['warm_turn_rate'])}) | {x['reviewed_warmth_distinctiveness_multiplier']:.3f} |")
        content+=['','The multiplier implements the proposed personality interpretation. It ranks the distinctiveness of reviewed warmth; it is not an estimate of sincerity. Trait estimates are public-text observations.','',
            '| Direction/source | Warm cues / target mentions | Other-member warm-cue rate |', '|---|---:|---:|']
        for r in [ra,rb]:
            for s in r['rhetoric_by_source']:content.append(f"| {r['actor_name']} → {r['target_name']} / {s['source']} | {s.get('warm_turns',0)}/{s['mention_turns']} | {pct(s['other_warm_rate'])} |")
        content+=['','Automated cue counts are retrieval statistics, not reviewed relationship episodes.','', '## Reviewed personal evidence','']
        for e in sorted(ee,key=lambda e:e['event_date']):
            urls=e.get('source_urls',[])
            if not urls and e.get('source_locator','').startswith('http'):urls=[e['source_locator']]
            if not urls and e.get('source')=='CREC':urls=[f"https://www.govinfo.gov/content/pkg/CREC-{e['event_date']}/pdf/CREC-{e['event_date']}.pdf"]
            note=e.get('review_note') or e.get('reason') or e.get('text','')[:220]
            content += [f"- **{e['event_date']} · {e['actor_name']} → {e['target_name']} · {e['sign']}**. {note} "+' '.join(f'[Source {i+1}]({u})' for i,u in enumerate(urls)),
                f"  Context: {e.get('alternative_explanation') or e.get('naturalness','reviewed in context')}. Evidence ID: `{e['evidence_id']}`. Corpus row: `{e.get('source_rowid')}`."]
        content+=['','## Actual shared bills','',
            'Every shared third-party bill in the frozen source is listed below. Dates are each member’s first recorded join. Identical titles on distinct bills remain separate.','',
            '| Bill | Title | Policy area | First joined | Second joined |', '|---|---|---|---|---|']
        for bill in sorted(shared,key=lambda b:(b['congress'],b['introduced'],b['key']),reverse=True):
            title=bill['title'].replace('|','/').replace('\n',' ')
            content.append(f"| [{bill['key']}]({bill['url']}) | {title} | {bill['area']} | {bill['joins'][a]} | {bill['joins'][b]} |")
            bill_receipts.append(dict(pair=[a,b],bill=bill['key'],source_url=bill['url'],actor_join=bill['joins'][a],target_join=bill['joins'][b],withdrawals={x:bill['withdrawals'][x] for x in [a,b] if x in bill['withdrawals']}))
        content+=['','## Bills sponsored by one member and joined by the other','']
        for name,these in [(f"{members[a]['name']} supports {members[b]['name']}",direct_a),(f"{members[b]['name']} supports {members[a]['name']}",direct_b)]:
            content += [f'**{name}**','']
            content += [f"- [{bill['key']}]({bill['url']}): {bill['title']}" for bill in these] or ['No recorded signatures.']
            content.append('')
        path.write_text('\n'.join(content)+'\n',encoding='utf-8')
        pair_rows.append(dict(a=a,b=b,names=[members[a]['name'],members[b]['name']],shared=len(shared),
            affinity=[label(r['friendship']) for r in [ra,rb]],hostility=any(r['hostility']!='unknown' for r in [ra,rb]),
            path=str(path),directions=[ra,rb]))
    write_ndjson(OUT/'reviewed_pair_bill_receipts.ndjson',bill_receipts)
    con=sqlite3.connect((ROOT/'social_media.db').as_uri()+'?mode=ro',uri=True);con.execute('PRAGMA query_only=ON');con.execute('BEGIN')
    sources=[]
    for rid in sorted({e['source_rowid'] for e in events if e.get('source_rowid')}):
        r=con.execute('SELECT rowid,member,date,source,package,text FROM speeches WHERE rowid=?',(rid,)).fetchone()
        if r:sources.append(dict(zip(['source_rowid','member','date','source','package','text'],r)))
    con.rollback();con.close();write_ndjson(OUT/'reviewed_speech_sources.ndjson',sources)
    # The report foregrounds actual pair evidence and transparent validation.
    wm=results['work'];sm=results['speech'];bm=results['benchmark']
    report=['# Member relationship results — full-history revision','',
        f"Built on {wm['audit']['included_bills']:,} H.R./S. bills across Congresses 116–119, {wm['members']} members, and all {wm['ordered_pairs']:,} directed pairs. The speech baseline includes {sm['deduplicated_turns']:,} deduplicated attributed turns. Shared co-sponsorship now contributes directly. The 30-day gate and title-family deletion are removed.",
        '',f"Reviewed results: **{results['friendship_directions'].get('documented_personal_friendship',0)} directed documented-friendship ties**, **{results['friendship_directions'].get('inferred_personal_affinity',0)} directed affinity inferences**, **{results['hostility_directions']} directed public-antagonism ties**, and **{results['dislike_inferences']} event-dated personal-dislike inferences**. These categories can coexist and are not counts of independently verified current private relationships.",
        '', '## Inferred personal affinity','', '| Direction | Shared bills | Cooperation percentile | Positive support |','|---|---:|---:|---|']
    for r in rows:
        if r['friendship']=='inferred_personal_affinity':
            path=directory/('__'.join(sorted((r['actor'],r['target'])))+'.md')
            report.append(f"| [{r['actor_name']} → {r['target_name']}](<{path}>) | {int(r['shared_bills'])} | {pct(r['shared_percentile'])} | {', '.join(label(x) for x in r['positive_support'])} |")
    report+=['','These combine context-reviewed personal language with supporting behavior. Cooperation alone produces a review candidate. Every row links to statements, personality context, full history, and the actual bill list.','',
        '## Documented evidence and work history','', '| Pair | Shared bills | Evidence assessment | Dossier |','|---|---:|---|---|']
    for p in pair_rows:
        assessment='public antagonism recorded' if p['hostility'] else ' / '.join(dict.fromkeys(p['affinity']))
        report.append(f"| {' — '.join(p['names'])} | {p['shared']} | {assessment} | [Evidence and bills](<{p['path']}>) |")
    report+=['','## What the test found','',
        f"With personal statements hidden from the work calculations, the original documented-friendship pairs averaged the **{100*bm['positive']['mean_shared_percentile']:.1f}th percentile** of matched shared-cosponsorship overlap; documented antagonisms averaged the **{100*bm['negative']['mean_shared_percentile']:.1f}th percentile**. Comparisons were available for {bm['positive']['matched_shared_available']}/{bm['positive']['pairs']} positive pairs and {bm['negative']['matched_shared_available']}/{bm['negative']['pairs']} negative pairs.",
        '',f"The deliberately selective work flag recovered {bm['positive']['work_flags']}/{bm['positive']['pairs']} original friendship pairs and flagged {bm['negative']['work_flags']}/{bm['negative']['pairs']} antagonism pairs. It is therefore a useful supporting channel but misses many documented friendships. This is a retrospective descriptive test, not a calibrated friendship classifier. An unobserved relationship is never a negative test label.",
        '',f"The 90th-percentile work screen flags {bm['sensitivity']['0.9']:,} directions across the full roster. The counts are {bm['sensitivity']['0.85']:,} at the 85th and {bm['sensitivity']['0.95']:,} at the 95th. Those broad work candidates are not automatically called friends.",
        '', '## Implementation and limits','',
        f"- All {wm['audit']['included_bills']:,} canonical bills survive; {wm['audit']['distinct_title_reintroductions_retained']:,} repeated sponsor/title occurrences remain separate bills. {wm['audit']['joins_after_day_30']:,} source signatures after day 30 are retained across the full historical bill rosters. {wm['audit']['withdrawal_records']} withdrawals remain explicit.",
        '- Geography and ideology define comparison groups, with issue-profile similarity. No negative similarity weight is used. State and 0.2-wide DW1 bins are coarse controls; district distance, exact annual context, committee/caucus incentives and all private motives are not fully identified.',
        '- Personality compatibility contributes positive evidence. Rare warmth receives greater descriptive weight for lower E/A estimates. This implements the proposed hypothesis; the multiplier is not research-validated sincerity measurement.',
        '- Every reviewed pair has an independent recount from its actual bill list. Full matrix and decision tests are recorded in TEST_RESULTS.txt and verification_receipt.json.',
        '- Output is isolated under this research run; production relationship files are not overwritten.', '',
        f"[Full implemented mathematics and methodology](<{ROOT/'research/MEMBER_PERSONAL_RELATIONSHIPS_V3_MATH.md'}>) · [Machine-readable results](<{OUT/'results.json'}>) · [Original-pair benchmark](<{OUT/'benchmark.json'}>) · [Verification receipt](<{OUT/'verification_receipt.json'}>)",'']
    (OUT/'REPORT.md').write_text('\n'.join(report),encoding='utf-8')
    (OUT/'METHODOLOGY.md').write_text((ROOT/'research/MEMBER_PERSONAL_RELATIONSHIPS_V3_MATH.md').read_text(encoding='utf-8'),encoding='utf-8')
    write_json(OUT/'dossier_receipt.json',dict(pairs=len(pair_rows),shared_bill_rows=len(bill_receipts),
        independent_pair_recounts_passed=True,reviewed_speech_rows=len(sources),
        report_sha256=digest(OUT/'REPORT.md')))
    print(json.dumps(dict(dossiers=len(pair_rows),shared_bill_receipts=len(bill_receipts))),flush=True)


if __name__=='__main__':main()
