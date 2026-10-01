"""Render the completed development results and prospective receipt."""
import csv
import json

from common import CODE, OLD, OUT, digest, read_json, stamp, write_json

LABELS={
 'logistic_dynamic':'Dynamic logistic control',
 'boosted_dynamic':'Dynamic trees control',
 'boosted_public_coverage':'Public-coverage trees control',
 'boosted_network':'Public coverage + member networks',
 'boosted_demographic':'Public coverage + demographics',
 'boosted_lobbying':'Public coverage + lobbying attention',
 'boosted_context':'Public coverage + networks + demographics + lobbying',
 'boosted_all':'All context + predecessor text, trees',
 'logistic_all':'All context + predecessor text, logistic',
 'boosted_staff_exploratory':'All context + provisional staff (exploratory)',
 'logistic_text_gate':'Logistic with close-text predecessor gate',
 'boosted_text_gate':'Trees with close-text predecessor gate',
 'logistic_text_added':'Logistic + predecessor-text evidence',
 'boosted_text_added':'Trees + predecessor-text evidence',
 'boosted_static_network':'Public coverage + static network structure',
 'boosted_dynamic_exposure':'Public coverage + dated peer exposure',
 'boosted_network_no_eigen':'Network trees without eigenvector features',
 'boosted_network_marginal':'Network trees + marginal coalition coverage',
 'lambdamart_network':'Network LambdaMART + activity',
}


def pct(x):return f'{100*x:.2f}%'


def run():
    extension=read_json(OUT/'extension_results.json');mechanism=read_json(OUT/'network_mechanism_results.json')
    models={**extension['models'],**mechanism['models'],'lambdamart_network':read_json(OUT/'network_ranker_results.json')}
    paired=read_json(OUT/'paired_extension_results.json');rank=read_json(OUT/'ranker_development.json')
    verification=read_json(OUT/'verification_receipt.json')
    assert verification['status']=='passed'
    snapshot=OUT/'prospective_20260905';future=read_json(snapshot/'forecast_manifest.json');policy=read_json(snapshot/'shortlist_policy.json')
    baseline=models['boosted_public_coverage']['year_2024'];network=models['boosted_network']['year_2024']
    lines=[
      '# Cosponsorship refinement: networks, public evidence and selective forecasts',
      '',f'Completed {stamp()}. Research only. Production forecaster and pipeline unchanged.',
      '',
      '**Member-network information improves the development shortlists modestly; higher selective precision comes with much shorter lists.** '
      f"Public-coverage trees found {baseline['hits_at_8']} subsequent joins in {baseline['slots_at_8']:,} top-eight slots in calendar 2024. "
      f"Adding dated member-network structure/exposure found {network['hits_at_8']}, a gain of {network['hits_at_8']-baseline['hits_at_8']}. "
      'The new models have not yet passed an independent future test. All comparisons below use the same eligible historical forecasts.',
      '',
      '## What the results do and do not measure',
      '',
      'The outcome is first cosponsorship in the next 30 days, among serving same-chamber unsigned members other than the sponsor. '
      'The bill universe is House/Senate legislation referred on introduction to House/Senate financial-services/banking or agriculture committees, including bills with zero cosponsors. '
      'Forecasts cover bill ages 0, 35, 70, 105, 140 and 175 days. These are not predictions of floor votes, passage, lifetime support or lobbying response.',
      '',
      f"Calendar 2024 contains {baseline['rows']:,} complete member–bill forecasts, {baseline['events']:,} joins, {baseline['bill_dates']:,} bill-date groups and {baseline['slots_at_8']:,} forced shortlist slots. "
      f"The underlying 30-day event rate is {pct(baseline['base_rate'])}. Most bill-date groups have no joiner. "
      f"Even perfect hindsight could fill only {pct(rank['models']['lambdamart_activity']['year_2024']['oracle_precision'])} of those forced slots correctly. "
      'That ceiling is a population diagnostic, not a forecast or model feature.',
      '',
      'Train on Congress 117; select/calibrate on calendar 2023 within 118; then describe calendar 2024 separately. '
      'Congress 118 was already used to choose phase-one settings, so this is development evidence, including the later year. '
      'Congress 119 outcomes are not reused for tuning or confirmation. Historical sources are reconstructed using event/publication dates and were often first observed now. '
      'The new September 5 observation-time snapshot is the independent test.',
      '',
      '## Same-forecast development comparison',
      '',
      '| Model | Correct top-eight picks | Precision at eight | Average precision | Brier score |',
      '|---|---:|---:|---:|---:|',
    ]
    order=['logistic_dynamic','boosted_dynamic','boosted_public_coverage','boosted_network','boosted_demographic','boosted_lobbying','boosted_context','boosted_all','logistic_all','lambdamart_network','boosted_staff_exploratory']
    for name in order:
        m=models[name]['year_2024'];lines.append(f"| {LABELS[name]} | {m['hits_at_8']} | {pct(m['precision_at_8'])} | {m['average_precision']:.4f} | {m['brier']:.6f} |")
    lines += ['',
      'The all-context logistic model won the original eleven-model extension selection on 2023; the network model was the best non-staff boosted extension on that same selection period. '
      'The combined-context tree model had the largest later-year count in that original batch, but choosing it because of 2024 would reuse the assessment outcomes. '
      'Network LambdaMART used the previously chosen seven leaves and 600 trees with no new hyperparameter search. It found 360 later joins versus 334 for the previous ranker. '
      'Average precision and probability quality do not improve uniformly when top-eight hits improve; the objectives should not be conflated.',
      '',
      f"Paired uncertainty resamples all dates in each of {paired['families']} legislative families together, using {paired['replicates']:,} replicates. "
      'The following intervals are descriptive development uncertainty. Conservative intervals account for all comparisons reported in the paired diagnostic, but they do not turn development into an independent test.',
      '',
      '| Addition versus public-coverage trees | Additional hits | Precision gain, percentage points | 95% family interval, pp | Conservative all-comparison interval, pp |',
      '|---|---:|---:|---:|---:|',
    ]
    for name in ['boosted_network','boosted_demographic','boosted_lobbying','boosted_context','logistic_all','lambdamart_network']:
        r=paired['models'][name];a,b=r['ci95'];c,d=r['conservative_all_comparison_interval']
        lines.append(f"| {LABELS[name]} | {r['extra_hits']:+d} | {100*r['delta_precision']:+.3f} | {100*a:+.3f} to {100*b:+.3f} | {100*c:+.3f} to {100*d:+.3f} |")
    lines += ['',
      '**None of the new additions has a conservative all-comparison interval wholly above zero.** The combined-context model has a positive ordinary 95% interval, but that does not survive the comparison-family adjustment. The individual network addition is also borderline at the ordinary interval. These are promising point improvements, not a confirmed statistically significant advance.',
      '',
      '## Raising precision by reducing the list',
      '',
      'For every model, set a numerical probability cutoff from its top-eight score distribution in 2023, then apply that unchanged cutoff in 2024. '
      'The table uses the cutoff retaining the highest-scored 5% in 2023; the realized 2024 fraction differs because scores and activity change. '
      'These are correct subsequent joins per recommendation, not classification accuracy. The intervals resample whole bills.',
      '',
      '| Model | 2024 recommendations | Correct joins | Precision | 95% interval | Distinct bills / members |',
      '|---|---:|---:|---:|---:|---:|',
    ]
    for name in ['boosted_public_coverage','boosted_network','boosted_context','logistic_all','lambdamart_network']:
        s=next(s for s in models[name]['selective_2024'] if s['target_retained_2023']==.05);a,b=s['ci95']
        lines.append(f"| {LABELS[name]} | {s['recommendations_2024']} | {s['hits_2024']} | {pct(s['precision_2024'])} | {pct(a)}–{pct(b)} | {s['bills_2024']} / {s['members_2024']} |")
    lines += ['',
      'The network-tree example is 69 correct joins out of 585 recommendations (11.8%), covering 100 bills and 217 members; it retains only about 1.5% of all forced 2024 slots and captures only about 2.2% of all observed joins. '
      'The all-context logistic example is 57/450 (12.7%). These models choose different numbers and identities, so the selective percentages alone are not a matched-budget significance test. '
      'The much shorter 1% policies have especially few cases and wide intervals; they are retained in the JSON, not selected as a headline best success rate.',
      '',
      f'![Precision versus recommendation count](<{(OUT/"precision_coverage.png").as_posix()}>)',
      '',
      '## Eigenvector centrality, peer activity and influence maximization',
      '',
      'The production forecaster already contained a prior-network eigenvector feature. This extension adds 17 dated member-network measurements: degree/strength, PageRank, component-local eigenvector centrality, component size/isolation, sponsor ties, earlier active-peer exposure, recent 7/30-day exposure, centrality-weighted exposure and two-hop relationships. '
      'The graph is reconstructed solely from the preceding Congress, separately by chamber. Each bill contributes a total sponsor-edge weight of one. Eigenvector scores are normalized within connected components, not treated as globally comparable influence estimates.',
      '',
      'The first residual-walk score was largely redundant with two-hop exposure. The additional marginal-coverage feature computes how much a candidate adds to the coalition’s strongest historical ties, with overlap discounted. '
      'It uses a monotone submodular coverage function, F(S) = sum_j max_(i in S) q_ij, on column-normalized historical relationship weights. '
      'A candidate feature is [F(S ∪ {i}) − F(S)] divided by graph size. S includes only the sponsor and strictly earlier signers. '
      'This is a structural coverage calculation, not a fitted probability that contacting one person causes another to act.',
      '',
      '| Fixed diagnostic | 2023 selection hits | 2024 development hits | 2024 precision at eight |',
      '|---|---:|---:|---:|',
    ]
    for name in ['boosted_network',*mechanism['models']]:
        r=models[name];lines.append(f"| {LABELS[name]} | {r['year_2023']['hits_at_8']} | {r['year_2024']['hits_at_8']} | {pct(r['year_2024']['precision_at_8'])} |")
    lines += ['',
      'Static network structure alone found 338 later joins and dated exposure alone found 345, versus 355 when combined. Removing eigenvector-derived features yielded 346, while marginal coverage yielded 358. The eigenvector-free model actually ranked better during 2023 selection (1,027 versus 998 hits), illustrating that eigenvector benefits are not stable across periods. The three-hit marginal-coverage increase does not establish a reliable additional gain.',
      '',
      'These feature-family removals identify predictive contributions more directly than an arbitrary centrality score. They still do not establish causal persuasion: similar members may share preferences, information, committee assignments and political incentives. '
      'No outreach was performed and no private member contact was inferred.',
      '',
      '## Do we have the data?',
      '',
      '| Evidence | What was available and used | Remaining limitation |',
      '|---|---|---|',
      '| Member actions | Dated cosponsor histories and prior-Congress relationships; strict earlier-event joins | Historical observation timestamps are generally unavailable |',
      '| Introduced predecessor text | 2,515 of 2,516 requested official IH/IS texts; 640/640 pairs in 117 and 778/779 in 118 verified for availability | Text similarity is not legal equivalence; one missing 117:S3455 source |',
      '| Demographics | Historical ACS 2019, 2021 and 2022 population, age, income, poverty and renter share; estimates and MOEs retained | Missing compatible early-118 district geography and changed 117 NC districts; source MOEs not propagated through the learner |',
      '| Lobbying | Public filing/posting dates, formally cited bills, deduplicated filing/client/registrant/named-lobbyist counts | Bill attention does not reveal member-specific contact or treatment |',
      '| Staff | Explicit member-resolved, bounded prior employment assertions; exploratory shared-office-history sensitivity | V5 remains quarantined for corpus identity/coverage issues; excluded from primary selection and prospective forecast |',
      '| Public positions | 1,472 source-linked machine candidates audited; two superficially eligible statements reviewed in full context | No qualifying positive training leads in the historic six-month prediction window |',
      '',
      'Introduced-body verification classified 412/640 predecessor pairs in 117 and 532/779 in 118 as close text under the fixed Dice ≥ .90, length-ratio ≥ .80, minimum-40-token rule. '
      'Exact normalized matches numbered 97 and 136. Enforcing this as a hard gate did not consistently improve prediction; politically relevant predecessors can change wording. '
      'The continuous-text and gated model results are retained in the full metrics export.',
      '',
      'The public review identified a Massie statement of support after prior committee/floor action, at bill age 321 days with no later cosponsorship, and a Roy statement reporting past floor votes. '
      'Neither supplies a positive lead in the defined training task. A further check found no historic in-window support/intent candidates whose only unresolved issues were press attribution or multiple bill references. '
      'The source-context adjudications are explicitly assistant reviews, not human gold labels. The large newly available press collection is concentrated in 2026 and does not supply a historical positive training set.',
      '',
      '## What prior research supports',
      '',
      '- [Russo et al. (2023)](https://aclanthology.org/2023.acl-long.166/) combine legislative text, speeches and graph information for cosponsorship, distinguishing original from later cosponsorship. Their task and population differ from our next-30-day ranking; published scores are not transferable benchmarks.',
      '- [Brandenberger (2018), Trading Favors](https://doi.org/10.1016/j.socnet.2018.02.001) models temporal reciprocity in congressional cosponsorship. It motivates dated relationships and timing, not treating final coalitions as features available at introduction.',
      '- [Montgomery and Nyhan (2017)](https://www.journals.uchicago.edu/doi/10.1086/690301) find that exchanging senior/policy staff is associated with similarities in legislative effectiveness and voting. The outcome is adjacent to our task; complete longitudinal staff records and role distinctions matter.',
      '- [Estimating the Causal Effects of Social Interaction with Endogenous Networks](https://doi.org/10.1093/pan/mps016) uses the House office lottery and reports no evidence that proximity affected legislative behavior. Physical or organizational connection alone does not guarantee an effect.',
      '- [Kempe, Kleinberg and Tardos (2003)](https://www.cs.cornell.edu/home/kleinber/kdd03-inf.pdf) study influence maximization under specified cascade/threshold assumptions. Their greedy approximation guarantee concerns the assumed diffusion model, not a guarantee of legislative persuasion or a universal eigenvector ranking.',
      '- [Shalizi and Thomas (2011)](https://pmc.ncbi.nlm.nih.gov/articles/PMC3328971/) show why observational network association can confound homophily and contagion. This is why our prediction features are not labeled causal lobbying effects.',
      '- Official Census guidance documents [118th district product timing](https://www.census.gov/programs-surveys/decennial-census/about/rdo/congressional-districts.118th_Congress.html) and [117th geography limitations](https://www.census.gov/geographies/reference-maps/2021/geo/cong-dist-117-wall.html). Those release/boundary constraints are implemented, not filled using today’s district workbook.',
      '',
      '## Independent forecast issued September 5',
      '',
      f"The immutable official-source snapshot contains {future['rows']:,} candidate rows across {future['bills']} bills and {future['members']} members. "
      'Five fixed controls—history logistic, dynamic logistic, weekly time-to-sign, dynamic trees and public-coverage trees—were issued first. '
      'The boosted-network classifier was then refit using mature 117/118 data and separately issued on the exact same rows. '
      'Model, source, feature, code and prediction hashes are retained. Two current official-roster IDs lack the pinned historical identity match and are explicitly excluded.',
      '',
      f"Outcomes run from {future['outcome_start']} through {future['outcome_end']}; the earliest scoring date is **{future['earliest_scoring_date']}**. "
      'The future comparison is pending. Refit scores may shift and current event rates may differ, so the historical 11.8% cannot be promised for today’s shortlist. '
      'The scorer requires a mature later official snapshot and a complete departure review, excludes backfilled prior signatures, censors incomplete service windows and retains original issued ranks.',
      '',
      '| Network policy, set from 2023 | Recommendations issued now | Bills | Members |',
      '|---|---:|---:|---:|',
    ]
    for r in policy['policies']['boosted_network_refit']:
        lines.append(f"| Retain {r['target_retained_2023']:.0%} by historical cutoff | {r['issued_recommendations']} | {r['issued_bills']} | {r['issued_members']} |")
    lines += ['',
      'No model was promoted to production, no outreach was sent, and no future scheduler was installed. The next independent conclusion requires actual outcomes after October 5. '
      'Further causal work needs independently recorded contact dates, recipients, staff roles, bills/issues, commitments and whether a contact was initiated by us or the office; contacts cannot be reconstructed from signing itself. '
      'For staff modeling, the next usable input is a validated source-conserving employment generation with senior/policy role and interval coverage. '
      'For public evidence, record publication and first-observed time, named actor, exact bill version/reference, source passage, stance versus future intent, and later outcome separately.',
      '',
      '## Verification and files',
      '',
      'Seventeen boundary tests pass, including same-day/future exposure exclusion, submodular coverage, introduced-version checks, demographic release/geography checks, public attribution classification and premature-score rejection. '
      'All added matrices are finite and match their source receipts. Frozen development models/predictions match hashes. '
      'Every prospective row independently passes current eligibility checks; 2,000 sampled rows are re-predicted for each of six models. '
      'The entire original experiment’s recorded code and artifact hashes remain unchanged. These checks verify computation and boundaries, not future predictive accuracy.',
      'All 2,515 retained introduced-bill texts and 324 retained Census source files also match their recorded raw hashes; current external-source status is recorded separately in `raw_source_verification.json`.',
      '',
      '- `model_metrics.csv`: all development models, scores and populations.',
      '- `paired_extension_results.json`: ordinary and conservative family-bootstrap intervals.',
      '- `extension_results.json`, `network_mechanism_results.json`, `network_ranker_results.json`: all settings, calibration and precision/coverage policies.',
      '- `public_position_adjudication.json`: source-linked contextual review.',
      '- `prospective_20260905/forecasts.parquet`, `network_forecasts.parquet`, `shortlist_policy.json`: immutable pending forecasts and policies.',
      '- `prospective_20260905/network_selective_shortlist.csv`: 17 highest-policy candidates for later assessment, not guaranteed joiners.',
      '- `verification_receipt.json`, `experiment_manifest.json`: preservation and completion hashes.',
      '- Code and replay instructions: `fec/research/cosponsor_refinement/README.md`.',
    ]
    (OUT/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    with (OUT/'model_metrics.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['model','period','rows','events','hits_at_8','slots_at_8','precision_at_8','recall_at_8','average_precision','brier'])
        writer.writeheader()
        for name,r in models.items():
            for period in ['year_2023','year_2024']:
                writer.writerow(dict(model=name,period=period,**{k:r[period][k] for k in writer.fieldnames[2:]}))
    assert (OUT/'precision_coverage.png').exists(),'Run render_plot.py with a Python runtime containing matplotlib'
    version=CODE/'protocol_versions'/f"{digest(CODE/'PROTOCOL.md')}.md"
    if not version.exists():version.write_bytes((CODE/'PROTOCOL.md').read_bytes())
    files=[p for p in OUT.iterdir() if p.is_file() and p.suffix in {'.json','.md','.csv','.png','.svg'} and p.name!='experiment_manifest.json']
    manifest=dict(completed_utc=stamp(),status='development_complete_prospective_outcomes_pending',
       code_sha256={p.name:digest(p) for p in CODE.iterdir() if p.is_file() and p.suffix in {'.py','.md'}},
       artifacts={p.name:digest(p) for p in files},verification_sha256=digest(OUT/'verification_receipt.json'),
       original_experiment_manifest_sha256=digest(OLD/'experiment_manifest.json'),
       prospective_manifests={p.name:digest(p) for p in snapshot.glob('*.json')})
    write_json(OUT/'experiment_manifest.json',manifest)
    print(str(OUT/'REPORT.md'),flush=True)


if __name__=='__main__':run()
