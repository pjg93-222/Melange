"""Readable, complete institutional comparison from frozen machine receipts."""
import importlib.metadata
import platform
import re
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from institutions_common import CODE, OUT, digest, read_json, write_json, stamp

LABELS = {
 'institution_backbone':'Coverage + network + activity',
 'institution_votes':'Backbone + votes', 'institution_committees':'Backbone + committees',
 'institution_caucus':'Backbone + caucus evidence', 'institution_votes_committees':'Backbone + votes + committees',
 'institution_votes_caucus':'Backbone + votes + caucus', 'institution_committees_caucus':'Backbone + committees + caucus',
 'institution_all':'Backbone + all three blocks', 'institution_logistic_backbone':'Logistic backbone',
 'institution_logistic_all':'Logistic all three blocks', 'institution_universe_all':'Prior universe + all three blocks',
 'institution_caucus_leadership':'Backbone + caucus leadership only',
 'institution_hearing_sensitivity':'All three + hearing timing sensitivity',
 'boosted_activity':'Frozen activity trees', 'boosted_network':'Frozen network trees',
 'boosted_context':'Frozen context trees', 'boosted_universe':'Frozen universe trees'}


def paired(stats,a,b):
    key=a+' vs '+b
    if key in stats['paired']:return stats['paired'][key]
    r=stats['paired'][b+' vs '+a]
    return {k: [-v[1],-v[0]] if isinstance(v,list) else -v for k,v in r.items()}


def percent(value):
    return f'{value:.3%}' if value is not None else 'undefined (no selections)'


def run():
    results=read_json(OUT/'institutions_results.json');stats=read_json(OUT/'institutions_statistics.json')
    plan=read_json(OUT/'institutions_plan.json');selection=read_json(OUT/'institutions_selection.json')
    chosen=results['chosen_on_2023'];models=results['models'];selected=models[chosen]['year_2024']
    coverage=read_json(OUT/'cohort_feature_coverage.json')['periods']['forecast_dates_2024']
    refs=[n for n,s in plan['models'].items() if s['role']=='frozen_reference']
    strong=[n for n,s in plan['models'].items() if s['role']=='new' and s['eligible'] and
            all(paired(stats,n,b)['adjusted_interval'][0]>0 for b in refs)]
    evidence_pairs=[('institution_votes','institution_backbone'),('institution_committees','institution_backbone'),
        ('institution_caucus','institution_backbone'),('institution_all','institution_backbone'),
        ('institution_all','institution_votes_committees'),('institution_all','institution_votes_caucus'),
        ('institution_all','institution_committees_caucus'),('institution_caucus','institution_caucus_leadership'),
        ('institution_all','institution_logistic_all'),('institution_backbone','institution_logistic_backbone'),
        ('institution_hearing_sensitivity','institution_all')]
    evidence_pairs=[p for p in evidence_pairs if all(n in models for n in p)]
    incremental={label:paired(stats,'institution_all',without) for label,without in
        [('votes','institution_committees_caucus'),('committees','institution_votes_caucus'),('caucus evidence','institution_votes_committees')]}
    expected=sum(b['rows']*b['predicted'] for b in selected['calibration'])
    network=models['boosted_network']['year_2024']
    activity_pair=paired(stats,chosen,'boosted_activity')
    lines=['# Caucus, committee and voting evidence', '',
      f'Completed {stamp()}. Observational development study of the same 377 continuing members and financial bills.', '',
      f'The model chosen on forecasts dated in 2023 is **{LABELS[chosen]}** (`{chosen}`). In the later 2024 development period it found '
      f"**{selected['hits_at_8']:,} correct selections in {selected['slots_at_8']:,} forced top-eight slots ({selected['precision_at_8']:.3%})**. "
      f'Eligible new models beating all four frozen references after multiplicity adjustment: **{", ".join(LABELS[n] for n in strong) if strong else "none"}**.', '',
      f"Against the strongest prior top-eight reference (activity trees), the selected model adds {activity_pair['extra_hits']:+d} hits. Its adjusted precision-change interval is {100*activity_pair['adjusted_interval'][0]:+.3f} to {100*activity_pair['adjusted_interval'][1]:+.3f} percentage points. That small gain is not established as reliable.", '',
      'Both historical years had already been inspected in earlier research. These comparisons are development evidence; they do not establish future accuracy or a causal effect of caucuses, committees, peers or lobbying.', '',
      '## Evidence actually tested', '',
      '- **Caucuses: 15 features.** Eight prior-Congress leadership features from official CMO lists: 1,108 accepted observations in the 116th and 957 in the 117th. Seven membership features use dated Problem Solvers announcements: 54 explicitly named people for the 117th and 63 for the 118th. Membership is a documented historical positive, not proof of continuity. Unlisted members remain unknown. This is one caucus, not a test of a complete caucus census.',
      '- **Votes: 25 features.** Raw dated decisions from Congresses 116–118, joined by Congress, chamber, roll call and member. Related-bill topics use as-introduced titles. Substantive, procedural and amendment questions are separate; procedural Yea is not a policy endorsement. No fitted Voteview probabilities or whole-Congress ideology estimates enter this block.',
      '- **Committees: 21 primary features.** Archived committee assignments, dated referrals, shared assignments and conservative record-dated bill opportunities. Leadership reflects archived reported/derived titles: the upstream scraper can infer Chair or Ranking Member from rank and majority/minority status. Empty and incomplete historical snapshots remain visible as missing coverage. Four additional event-dated hearing features enter only the explicitly ineligible sensitivity model.',
      '- **Historical availability limits.** Sources were retrieved in 2026. Archived Git commit dates are observation proxies, not verified push times; BillStatus actions and votes are reconstructed historical events. Committee latest-update dates are not first-publication dates. The primary event features require both the event and latest update to precede the forecast; sensitivity hearings require exact bill/date corroboration but lack proven contemporaneous availability. Same-day evidence is excluded throughout.', '',
      'Source details: [caucus audit](caucus_source_audit.md), [vote receipt](votes_receipt.json), [committee receipt](committees_receipt.json). '
      'Current 2026 caucus compilations, unverified hearing-member attendance and current psychological composites were not admitted as historical evidence.', '',
      '## Matched comparison', '',
      f"Train: Congress 117, 214,132 sampled rows including 6,529 events; all positives and the same deterministic 10% negative sample weighted by 10. Calibrate and select: 2023, 1,858,229 rows and 4,731 events. Later development: {stats['rows_2024']:,} rows, {stats['events_2024']:,} events, {stats['bills_2024']:,} bills and {stats['bill_dates_2024']:,} bill-dates. The target is first cosponsorship within the next 30 days, forecast at bill ages 0, 35, 70, 105, 140 and 175 days.", '',
      'The backbone combines public coverage, prior cosponsorship networks and recent signing activity. Tree settings are fixed across new variants. Four earlier forecasts are exact hash-verified copies from the same cohort and time split. The model and its calibration were fixed before the new later-period metrics were calculated.', '',
      'The split uses forecast dates. It includes 136,558 calibration rows dated December 4–29, 2023 whose 30-day windows reach 2024; 48 positive calibration outcomes occur in January 2024. This inherited comparison is not a purged temporal holdout, and the calibrated model is not claimed to have been available on January 1, 2024.', '',
      '| Model | Features | 2023 hits / 67,816 | 2024 hits / 38,128 | Precision | Average precision | Brier |',
      '|---|---:|---:|---:|---:|---:|---:|']
    for n,r in models.items():
        x=r['year_2024'];label=LABELS[n]+(' **selected**' if n==chosen else '')+(' (sensitivity)' if not r['eligible'] else '')
        lines.append(f"| {label} | {len(plan['models'][n]['features'])} | {r['year_2023']['hits_at_8']} | {x['hits_at_8']} | {x['precision_at_8']:.3%} | {x['average_precision']:.6f} | {x['brier']:.9f} |")
    lines += ['', 'Selected model versus the four prespecified references:', '',
      '| Reference | Extra correct selections | Precision change, percentage points | Adjusted interval, percentage points |',
      '|---|---:|---:|---:|']
    for baseline in refs:
        r=paired(stats,chosen,baseline)
        lines.append(f"| {LABELS[baseline]} | {r['extra_hits']:+d} | {100*r['delta_precision']:+.3f} | {100*r['adjusted_interval'][0]:+.3f} to {100*r['adjusted_interval'][1]:+.3f} |")
    lines += ['', 'Observed source coverage among the 1,048,932 later-period candidate rows and 377 members:', '',
      '| Evidence | Observed rows | Share of rows | Distinct members with evidence |', '|---|---:|---:|---:|']
    for block,fields in coverage['blocks'].items():
        for label,r in fields.items():
            if label=='membership_source_released':continue
            display='prior topic roll-call record' if label=='prior_topic_vote_observed' else label.replace('_',' ')
            lines.append(f"| {block}: {display} | {r['rows']:,} | {r['fraction']:.2%} | {r['members']} |")
    lines += ['', 'The meeting coverage consists of 10 bills and 24 bill-dates, shared across 2,811 candidate rows; it is not evidence that those members attended. Topic roll-call coverage includes present/not-voting records: actual Yea/Nay history covers 692,562 rows, with 1,214 additional eligible-record rows lacking a Yea/Nay. Positive source coverage is not completeness. Full training/selection-period coverage is in [the coverage receipt](cohort_feature_coverage.json), checked in [the independent coverage review](coverage_review.json).', '', '## What each evidence block adds', '',
      f"Paired differences preserve the same selection budget. Intervals use {stats['replicates']:,} resamples of {stats['families']:,} complete legislative families. Bonferroni correction includes all {stats['comparisons']} prespecified comparisons, separately for precision and Brier. Remaining member dependence and repeated historical model search are not removed by this adjustment.", '',
      '| Challenger versus comparator | Extra correct selections | Precision change, percentage points | Adjusted interval, percentage points |',
      '|---|---:|---:|---:|']
    for a,b in evidence_pairs:
        p=paired(stats,a,b)
        lines.append(f"| {LABELS[a]} versus {LABELS[b]} | {p['extra_hits']:+d} | {100*p['delta_precision']:+.3f} | {100*p['adjusted_interval'][0]:+.3f} to {100*p['adjusted_interval'][1]:+.3f} |")
    lines += ['', 'Removing one block at a time from the three-block model tests its contribution conditional on the other two:']
    for label,p in incremental.items():
        verdict='positive after adjustment' if p['adjusted_interval'][0]>0 else 'negative after adjustment' if p['adjusted_interval'][1]<0 else 'inconclusive after adjustment'
        lines += ['', f"- Adding {label}: {p['extra_hits']:+d} correct selections; {verdict}."]
    lines += ['', 'All reference contrasts and Brier intervals are retained in [the statistics receipt](institutions_statistics.json). A positive difference whose interval crosses zero is inconclusive.', '',
      '## Coverage and calibration', '',
      f"Forcing eight choices on every bill-date limits the meaning of this success rate: {stats['forced_top8_oracle']['zero_event_bill_dates']:,} of {stats['bill_dates_2024']:,} dates had no new signers. Even perfect knowledge could score only {stats['forced_top8_oracle']['hits']:,}/{stats['slots_2024']:,} ({stats['forced_top8_oracle']['precision']:.3%}) under that rule.", '',
      f"The selected model assigns expected event mass {expected:,.2f} across {stats['rows_2024']:,} candidate rows, versus {stats['events_2024']:,} observed events ({100*(expected/stats['events_2024']-1):+.2f}%). These probabilities are not a validated individual success guarantee.", '',
      f"Its average precision is {selected['average_precision']:.6f} and Brier score is {selected['brier']:.9f}; the frozen network reference scores {network['average_precision']:.6f} and {network['brier']:.9f}, respectively. Higher average precision and lower Brier are better. Selection for the top-eight endpoint does not guarantee better overall ranking or probability quality; paired Brier intervals are retained in the statistics receipt.", '',
      'Narrower retained sets below are descriptive subsets of the selected model\'s original top-eight lists, ordered by score. They do not rerank all candidate rows globally. Counts are member–bill–date selections; reducing coverage can raise precision while missing many positive member–bill cases in this benchmark.', '',
      '| Retained selections | Correct | Precision | Recall of all 2,100 events |', '|---:|---:|---:|---:|']
    for count,mm in stats['matched_retained_counts'].items():
        r=mm[chosen];lines.append(f"| {count} | {r['hits']} | {r['precision']:.3%} | {r['recall']:.3%} |")
    lines += ['', 'Cutoffs fixed using 2023 top-eight score quantiles:', '',
      '| 2023 retained fraction | Fixed cutoff | 2024 retained | Correct | Precision | Recall |', '|---:|---:|---:|---:|---:|---:|']
    for r in stats['selective'][chosen]:
        lines.append(f"| {r['target_fraction_2023']:.0%} | {r['cutoff_2023']:.6f} | {r['recommendations']} | {r['hits']} | {percent(r['precision'])} | {r['recall']:.3%} |")
    lines += ['', 'Strata retain selections from the original top-eight lists; no within-stratum reranking:', '',
      '| Stratum | Candidate rows | Events | Selected | Correct | Precision | Recall |','|---|---:|---:|---:|---:|---:|---:|']
    for name,r in stats['strata'][chosen].items():
        lines.append(f"| {name} | {r['candidate_rows']} | {r['candidate_events']} | {r['recommendations']} | {r['hits']} | {percent(r['precision'])} | {r['recall']:.3%} |")
    lines += ['', '## Interpretation and remaining evidence', '',
      'Caucus affiliation, committee opportunity and recorded policy decisions are plausible observational predictors. This design tests their incremental forecast contribution on the available evidence; it does not identify whom to lobby, psychological susceptibility or which intervention changes a vote or signature.', '',
      'The next data gaps are broader historically dated caucus rosters, verified publication times for hearings/meetings and bill-specific public positions available before forecasts. Existing raw coverage is not equivalent to an endorsement. More algorithms cannot substitute for missing or incorrectly dated evidence.', '',
      'Earlier issued September 5 forecasts remain immutable; their 30-day outcome window ends October 5 and can be scored no earlier than October 6. Those are prior models, not these new institutional variants. A future comparison of this generation requires its own frozen forecast receipt before outcomes.', '',
      'The user-selected continuing cohort conditions this analysis on remaining in office. Results do not generalize automatically to departed members, new members or bills outside the financial-bill corpus.', '',
      '## Reproduction', '',
      'Model plan, source hashes, exact predictions, selection chronology, independent reviews and verification are retained in this directory. [Research instructions](../../fec/research/cosponsor_institutions/README.md) describe reproduction. The final manifest binds the completed report and exact code archive.', '',
      '![Later-period development comparisons](institution_comparison.png)', '']
    # selected_summary field contracts are checked against frozen receipts by the caller.
    report='\n'.join(lines)
    report=re.sub(r'\]\(([^)]+)\)',lambda m: '](' + ('<'+(OUT/m.group(1)).resolve().as_posix()+'>' if '://' not in m.group(1) else m.group(1)) + ')',report)
    (OUT/'REPORT.md').write_text(report,encoding='utf-8')
    fig,ax=plt.subplots(figsize=(11,8));names=list(models)
    positions=list(range(len(names)));values=[100*models[n]['year_2024']['precision_at_8'] for n in names]
    colors=['#077f8c' if n==chosen else '#a7bdcb' if models[n]['role']=='frozen_reference' else '#667e91' for n in names]
    ax.barh(positions,values,color=colors);ax.set_yticks(positions,[LABELS[n] for n in names]);ax.invert_yaxis()
    for y,n,x in zip(positions,names,values):ax.text(x+.015,y,str(models[n]['year_2024']['hits_at_8']),va='center',fontsize=9)
    ax.set_xlim(0,max(values)*1.16);ax.set_xlabel('Correct selections / 38,128 fixed slots (%)')
    ax.set_title('Financial bills: 2024 development, first cosponsorship within 30 days\n377 continuing members; labels show correct-selection counts\nTeal marks the model selected on 2023 forecast dates',loc='left',fontsize=11)
    ax.spines[['top','right']].set_visible(False);fig.tight_layout();fig.savefig(OUT/'institution_comparison.png',dpi=170);plt.close(fig)
    write_json(OUT/'report_summary.json',dict(created_utc=stamp(),chosen=chosen,selected_metrics=selected,
        expected_events=expected,beats_all_four_adjusted=strong,model_count=len(models),pair_count=stats['comparisons'],
        evidence_pairs=[{'challenger':a,'comparator':b,**paired(stats,a,b)} for a,b in evidence_pairs],
        source_hashes={f:digest(OUT/f) for f in ['institutions_results.json','institutions_statistics.json','institutions_selection.json','cohort_feature_coverage.json','coverage_review.json']},
        render_environment={'python':platform.python_version(),'executable':sys.executable,
        'packages':{n:importlib.metadata.version(n) for n in ['matplotlib','numpy']}}))
    print('Institutional report written')


if __name__=='__main__':run()
