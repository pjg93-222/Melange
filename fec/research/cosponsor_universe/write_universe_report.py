"""Render only the final frozen 377-member benchmark; never fit or select models."""
import csv
import math
import platform
import sys
import textwrap
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from universe_common import CODE, OUT, read_json, stamp, write_json, digest

CONTROLS=['boosted_dynamic','boosted_public_coverage','boosted_network','boosted_context']
BUDGETS=[250,500,1000,2000,5000]
LABELS={
 'logistic_base':'Basic logistic','logistic_history':'History logistic','logistic_dynamic':'Dynamic logistic',
 'time_to_sign':'Weekly time-to-sign','boosted_dynamic':'Dynamic trees','boosted_public_coverage':'Public-coverage trees',
 'boosted_network':'Network trees','boosted_context':'Context trees','boosted_conduct_history':'+ Prior legislative conduct',
 'boosted_activity':'+ Recent signing activity','boosted_stages':'+ Corrected bill stages','boosted_elections':'+ Earlier elections',
 'boosted_amendments':'+ Earlier amendment activity','boosted_language':'+ Observed language',
 'boosted_language_coverage':'+ Language coverage only','boosted_media':'+ Shared-broadcast graph',
 'boosted_all_new':'All new families: trees','boosted_universe':'All evidence: trees','logistic_universe':'All evidence: logistic',
 'boosted_universe_no_language':'All evidence except language','boosted_universe_no_media':'All evidence except media',
 'boosted_language_placebo':'+ Permuted language (placebo)','boosted_reconstructed_context':'Reconstructed context: trees',
 'logistic_reconstructed_context':'Reconstructed context: logistic'}
DIRECT=[
 ('logistic_history','logistic_base','Predecessor and policy history beyond basic logistic'),
 ('boosted_language','boosted_language_coverage','Language content beyond coverage'),
 ('boosted_language','boosted_language_placebo','Language versus shuffled member assignments'),
 ('boosted_universe','boosted_universe_no_language','Language within all evidence'),
 ('boosted_universe','boosted_universe_no_media','Media within all evidence'),
 ('boosted_universe','logistic_universe','Trees versus logistic, all evidence'),
 ('boosted_reconstructed_context','logistic_reconstructed_context','Trees versus logistic, reconstructed context')]


def label(name):return LABELS.get(name,name.replace('_',' ').capitalize())
def unique(names):return list(dict.fromkeys(names))
def pct(x,d=3):return '—' if x is None else f'{x:.{d}%}'
def interval(x,scale=100,d=3):
    return '—' if not x or any(v is None for v in x) else f'{x[0]*scale:+.{d}f} to {x[1]*scale:+.{d}f}'
def link(file,title=None):
    p=Path(file)
    if not p.is_absolute():p=OUT/p
    return f'[{title or p.name}](<{p.as_posix()}>)'


def paired(stats,first,second):
    if first==second:
        return dict(extra_hits=0,delta_precision=0,ci95=[0,0],adjusted_interval=[0,0],delta_brier=0,
                    brier_ci95=[0,0],brier_adjusted_interval=[0,0],same_model=True)
    direct=stats['paired'].get(first+' vs '+second)
    if direct is not None:return direct
    reverse=stats['paired'].get(second+' vs '+first)
    if reverse is None:return None
    result=dict(reverse)
    for key in ['extra_hits','delta_precision','delta_brier']:result[key]=-reverse[key]
    for key in ['ci95','adjusted_interval','brier_ci95','brier_adjusted_interval']:
        result[key]=[-reverse[key][1],-reverse[key][0]]
    return result


def reading(c):
    if c is None:return 'Not prespecified'
    if c.get('same_model'):return 'Same model'
    if c['adjusted_interval'][0]>0:return 'Favors first model after adjustment'
    if c['adjusted_interval'][1]<0:return 'Favors second model after adjustment'
    return 'Adjusted interval includes zero'


def metrics_table(names,result,plan):
    rows=['| Model | Role | 2023 correct / slots | 2024 correct / slots | 2024 precision at 8 | Event recall | AP | Brier |',
          '|---|---|---:|---:|---:|---:|---:|---:|']
    for name in names:
        a,b=result['models'][name]['year_2023'],result['models'][name]['year_2024'];s=plan['models'][name]
        role='Placebo' if s['placebo'] else ('Refit control' if s['role']=='refit_control' else 'Challenger')
        rows.append(f'| {label(name)} | {role} | {a["hits_at_8"]:,}/{a["slots_at_8"]:,} | '
          f'{b["hits_at_8"]:,}/{b["slots_at_8"]:,} | {pct(b["precision_at_8"])} | {pct(b["recall_at_8"])} | '
          f'{b["average_precision"]:.5f} | {b["brier"]:.7f} |')
    return '\n'.join(rows)


def figure(result,stats,chosen):
    names=unique([chosen,*CONTROLS,'boosted_reconstructed_context','logistic_reconstructed_context',
                  'boosted_universe','logistic_universe'])
    curves=unique([chosen,'boosted_dynamic','boosted_context','boosted_universe','logistic_universe'])
    assert len(names)<=9 and len(curves)<=5
    fig,axes=plt.subplots(1,2,figsize=(15.5,7.8),gridspec_kw={'width_ratios':[1.1,1]})
    values=[100*result['models'][n]['year_2024']['precision_at_8'] for n in names];y=np.arange(len(names))
    axes[0].barh(y,values,height=.65,color=['#174c78' if n==chosen else '#87949f' if n in CONTROLS else '#75abc5' for n in names])
    axes[0].set_yticks(y,['\n'.join(textwrap.wrap(label(n),31)) for n in names],fontsize=9);axes[0].invert_yaxis()
    for i,n in enumerate(names):
        hits=result['models'][n]['year_2024']['hits_at_8']
        axes[0].annotate(f'{values[i]:.2f}% · {hits:,} correct',(values[i],i),xytext=(5,0),textcoords='offset points',va='center',fontsize=8)
    axes[0].set_xlim(0,max(values)*1.45 if max(values)>0 else 1)
    axes[0].set_xlabel('Correct within 30 days / forced top-eight slots (%)')
    axes[0].set_title('Equal recommendation budget at every bill-date',fontsize=11)
    for i,n in enumerate(curves):
        rates=[100*stats['matched_retained_counts'][str(k)][n]['precision'] for k in BUDGETS]
        axes[1].plot(BUDGETS,rates,marker='o',label=label(n),linewidth=2 if n==chosen else 1.4,color=plt.get_cmap('tab10')(i))
    axes[1].set_xscale('log');axes[1].set_xticks(BUDGETS,[f'{k:,}' for k in BUDGETS])
    axes[1].set_xlabel('Retained recommendations, matched across models');axes[1].set_ylabel('Correct within 30 days (%)')
    axes[1].set_title('Narrower recommendations: descriptive ranking budgets',fontsize=11);axes[1].legend(fontsize=8)
    for i,ax in enumerate(axes):
        ax.spines[['top','right']].set_visible(False);ax.grid(axis='x' if i==0 else 'both',alpha=.17);ax.set_axisbelow(True)
    fig.suptitle('Financial bills · 377 continuing members · 2024 development',fontsize=16,y=.98)
    fig.text(.5,.02,'Selection/calibration use 2023. Conditional on continued membership; not whole-population or independent confirmation.',ha='center',fontsize=9)
    fig.tight_layout(rect=[0,.05,1,.94])
    for ext in ['png','pdf','svg']:fig.savefig(OUT/f'universe_comparison.{ext}',dpi=180,bbox_inches='tight')
    plt.close(fig);return names,curves


def run():
    required=['universe_results.json','universe_statistics.json','universe_plan.json','universe_selection.json',
              'universe_statistics_plan.json','gold_cohort.json','gold_cohort.receipt.json','universe_family_triage.json']
    missing=[n for n in required if not (OUT/n).exists()]
    if missing:raise RuntimeError('Final frozen inputs not ready: '+', '.join(missing))
    result,stats,plan,selection,sp,cohort,cr,triage=[read_json(OUT/n) for n in required]
    bindings={n:digest(OUT/n) for n in required};models=plan['models'];chosen=result['chosen_on_2023']
    challengers=[n for n,s in models.items() if s['role']=='challenger'];controls=[n for n,s in models.items() if s['role']=='refit_control']
    eligible=[n for n,s in models.items() if s['historical_selection_eligible']]
    assert len(cohort['member_ids'])==cr['cohort_size']==377
    assert len(models)==24 and len(challengers)==16 and len(controls)==8 and len(eligible)==23
    assert all(s['historical_selection_eligible']==(not s['placebo']) for s in models.values())
    assert set(models)==set(result['models'])==set(selection['models'])
    assert chosen==selection['chosen']==stats['chosen_on_2023'] and chosen in eligible and selection.get('frozen_utc')
    assert result['selection_sha256']==bindings['universe_selection.json'] and selection['plan_sha256']==bindings['universe_plan.json']
    assert plan['input_sha256']['gold_cohort.json']==bindings['gold_cohort.json']
    assert stats['replicates']==100000 and stats['comparisons']==sp['comparisons']==len(sp['pairs'])==79
    assert set(map(int,stats['matched_retained_counts']))==set(BUDGETS)
    for year in [2023,2024]:
        for key in ['rows','events','slots_at_8']:
            assert len({r[f'year_{year}'][key] for r in result['models'].values()})==1,(year,key)
    later=result['models'][chosen]['year_2024'];baseline=result['models']['boosted_dynamic']['year_2024']
    assert stats['rows_2024']==later['rows'] and stats['events_2024']==later['events'] and stats['slots_2024']==later['slots_at_8']
    calibration_bins=[b for b in later['calibration'] if b['rows']>0]
    calibration_rows=sum(b['rows'] for b in calibration_bins)
    calibration_observed=math.fsum(b['rows']*b['observed'] for b in calibration_bins)
    calibration_expected=math.fsum(b['rows']*b['predicted'] for b in calibration_bins)
    assert calibration_rows==later['rows'] and math.isclose(calibration_observed,later['events'],abs_tol=1e-8)
    calibration_shortfall=1-calibration_expected/calibration_observed
    for n in challengers:
        for b in CONTROLS:assert paired(stats,n,b) is not None,(n,b)
    for n,b,_ in DIRECT:assert paired(stats,n,b) is not None,(n,b)
    positives={b:[n for n in challengers if n in eligible and paired(stats,n,b)['adjusted_interval'][0]>0] for b in CONTROLS}
    all_four=[n for n in challengers if all(n in positives[b] for b in CONTROLS)]
    selected_change=paired(stats,chosen,'boosted_dynamic');plot_names,curves=figure(result,stats,chosen)
    conduct=read_json(OUT/'conduct_receipt.json');amendment=read_json(OUT/'amendment_receipt.json')
    election=read_json(OUT/'election_history.receipt.json');checks=read_json(OUT/'universe_extraction_review.json')['checks'];counts=cr['counts']
    if selected_change is None:change='No paired contrast against dynamic trees was prespecified for this selected control; the raw difference is descriptive.'
    elif selected_change.get('same_model'):change='The refitted dynamic-tree control itself won 2023 selection; no new feature family is credited with that selection.'
    else:change=(f'Against refitted dynamic trees, it adds **{selected_change["extra_hits"]:+,} correct recommendations**. '
        f'The adjusted precision change is **{interval(selected_change["adjusted_interval"])} percentage points**. {reading(selected_change)}.')
    activity_dynamic=paired(stats,'boosted_activity','boosted_dynamic')
    activity_public=paired(stats,'boosted_activity','boosted_public_coverage')
    tree_logistic=paired(stats,'boosted_universe','logistic_universe')
    what_sticks=(f'The strongest individual addition in the later 2024 comparisons was **recent legislative activity**: '
      f'{activity_dynamic["extra_hits"]:+,} correct recommendations over dynamic trees and {activity_public["extra_hits"]:+,} over public-coverage trees. '
      f'The adjusted precision intervals were {interval(activity_dynamic["adjusted_interval"],d=4)} and '
      f'{interval(activity_public["adjusted_interval"],d=4)} percentage points, respectively. It did not clear the stronger network/context controls. '
      f'With the full feature set held fixed, trees added {tree_logistic["extra_hits"]:,} correct recommendations over logistic regression '
      f'(adjusted {interval(tree_logistic["adjusted_interval"],d=4)} percentage points). The observed lexical/media blocks did not establish an incremental gain. '
      'These are later descriptive findings; they do not replace the winner selected on 2023.')
    lines=['# Financial-bill cosponsorship among 377 continuing members','',f'Generated {stamp()}.','',
      'Scope: financial House and Senate bills admitted by the inherited finance-at-introduction filter; predict a first cosponsorship in the next 30 days among the fixed 377 continuing members. '
      'The system-wide evidence inventory does not mean all legislation was forecast.','',
      f'**{label(chosen)}** won 2023 selection among {len(eligible)} eligible models. In 2024 development it identified '
      f'**{later["hits_at_8"]:,} correct signatures in {later["slots_at_8"]:,} recommendations** ({pct(later["precision_at_8"])}), '
      f'versus {baseline["hits_at_8"]:,}/{baseline["slots_at_8"]:,} ({pct(baseline["precision_at_8"])}) for refitted dynamic trees.','',change,'',what_sticks,'',
      '**Additions beating all four tree controls after adjustment: '+(', '.join(label(n) for n in all_four) if all_four else 'None')+'.** '
      'These comparisons remain development evidence within the selected cohort, not independent confirmation.','',
      '**Labels are actual dated first cosponsorships within 30 days.** “Gold cohort” names the verified identity intersection; it does not mean gold-standard personality traits. '
      'Current Big Five, receptivity and influence-maximization scores are not admitted as historical measurements.','',
      f'![Measured comparison](<{(OUT/"universe_comparison.png").as_posix()}>)','',
      '## What the selected model adds over the controls','',
      'Every control was refitted on the same cohort, sampled training rows and forecast risk sets. Positive precision changes favor the selected model; '
      'negative Brier changes favor it. Adjusted intervals cover the full comparison family separately for each endpoint.','',
      '| Selected model versus | Extra correct recommendations | Adjusted precision change (pp) | Adjusted Brier change | Reading |',
      '|---|---:|---:|---:|---|']
    for b in CONTROLS:
        c=paired(stats,chosen,b)
        lines.append(f'| {label(b)} | '+('— | — | — | Not prespecified |' if c is None else
          f'{c["extra_hits"]:+,} | {interval(c["adjusted_interval"])} | {interval(c["brier_adjusted_interval"],1,7)} | {reading(c)} |'))
    lines+=['','## Core history, language, coverage, media and model form','',
      'The first contrast isolates the core predecessor and policy-history block beyond basic logistic predictors. It remains visible even when newer evidence families add no detectable value.','',
      'Coverage-only features retain source volume, packages, missingness and thin-source flags. The placebo shuffles complete language vectors within Congress/chamber cohort blocks, '
      'preserving marginal distributions while breaking member assignments. Beating that placebo alone does not show that content adds value beyond coverage; the direct coverage and block-removal contrasts answer different questions.','',
      'PUBLIC denotes dated mentions and source coverage, not validated bill endorsements. The earlier audit found zero usable explicit bill-support or opposition observations '
      'in the training and development risk sets. Follow-up review audited 1,472 source-linked machine candidates and examined two apparently eligible statements in full context; '
      'neither supplied a qualifying positive historical lead within the model’s six-month bill-age eligibility period. These were assistant source-context adjudications, not human gold labels. '
      'The current corpus therefore cannot estimate direct endorsement-to-sign transitions meaningfully. '
      +link(OUT.parent/'cosponsor_challengers_20260905/REPORT.md','Earlier public-position finding')+' · '
      +link(OUT.parent/'cosponsor_refinement_20260905/REPORT.md','Follow-up public-position audit')+' · '
      +link(OUT.parent/'cosponsor_refinement_20260905/public_position_adjudication.json','Source-context adjudications')+'.','',
      '| Prespecified question (first minus second) | Extra correct recommendations | Adjusted precision change (pp) | Adjusted Brier change | Reading |',
      '|---|---:|---:|---:|---|']
    for a,b,title in DIRECT:
        c=paired(stats,a,b);lines.append(f'| {title} | {c["extra_hits"]:+,} | {interval(c["adjusted_interval"])} | {interval(c["brier_adjusted_interval"],1,7)} | {reading(c)} |')
    lc=paired(stats,'boosted_language','boosted_language_coverage')
    lines+=['',('The adjusted language-versus-coverage interval supports an incremental content signal on this benchmark.' if lc['adjusted_interval'][0]>0 else
      'The adjusted language-versus-coverage interval does not establish an incremental content gain on this benchmark.'),'',
      'Both tree-versus-logistic contrasts use matched feature sets and the same training/calibration rows. They separate learner flexibility from access to more evidence; '
      'a language or behavior prediction gain does not validate an intrinsic personality trait.','',
      '## Population, target and time boundaries','',
      f'The user-directed cohort contains **377 people** present in both historical 117/118 risk sets and the official September 2026 roster: '
      f'{counts["cohort_by_current_chamber"]["House"]} currently in the House and {counts["cohort_by_current_chamber"]["Senate"]} in the Senate. '
      f'The historical risk-set intersection contained {counts["both_historical_risk_members"]} people before the current-roster condition. '
      'Cohort construction read identities/membership, without outcome labels. '+link('gold_cohort.receipt.json','Cohort receipt')+'.','',
      'This permits language/media as a **conditional continuing-member benchmark**. It does not repair whole-population survivor selection, recover missing text for departed members, '
      'or establish transport to freshmen or future cohorts. The original coverage audit remains valid; the final task deliberately changes the population being estimated. '+link('coverage_bias.md','Coverage audit')+'.','',
      f'Train on mature Congress 117 rows: {selection["training_rows"]:,} sampled rows, including all {selection["training_events"]:,} cohort positives and a deterministic 10% '
      'sample of negatives weighted by 10. All models use the same rows. Calibrate/select on 2023, freeze all predictions and the winner, then assess 2024.','',
      f'The 2024 assessment contains **{stats["rows_2024"]:,} member–bill–date rows, {stats["events_2024"]:,} positive events, {stats["bills_2024"]:,} bills and '
      f'{stats["bill_dates_2024"]:,} bill-dates**. Finance-at-introduction House/Senate bills are forecast at ages 0, 35, 70, 105, 140 and 175 days; '
      'existing cosponsors are removed from risk. The target is a first signature in the next 30 days. Forced top-eight slots are identical across models.','',
      f'**{len(models)} refits: {len(challengers)} challenger variants and {len(controls)} controls.** Every non-placebo may win 2023 selection, including a control. '
      'Controls include basic/history/dynamic logistic, weekly time-to-sign, and dynamic/PUBLIC/network/context trees. '+link('universe_plan.json','Exact frozen feature lists and settings')+'.','',
      'Both 2023 and 2024 remain development because earlier work used Congress 118. Congress 119 cosponsorship outcomes are not used for these new tests; September 2026 membership '
      'openly defines the requested cohort. Existing September 5 prospective forecasts remain unchanged; their 30-day window ends October 5 and can be assessed no earlier than October 6. '
      'Those forecasts were not issued by the new cohort models.','',
      '## Precision at matched recommendation budgets','',
      'Budgets were fixed before results. Each model ranks its 2024 top-eight candidates and retains the same number. This is descriptive ranking, not a frozen probability policy. '
      'Counts are recommendation events, not unique people.','',
      '| Retained count | Dynamic trees | Context trees | 2023-selected model | Selected event recall | Selected bills / members |',
      '|---:|---:|---:|---:|---:|---:|']
    for k in BUDGETS:
        r=stats['matched_retained_counts'][str(k)];cells=[]
        for n in ['boosted_dynamic','boosted_context',chosen]:cells.append(f'{r[n]["hits"]:,}/{r[n]["recommendations"]:,} ({pct(r[n]["precision"],2)})')
        q=r[chosen];lines.append(f'| {k:,} | '+' | '.join(cells)+f' | {pct(q["recall"],2)} | {q["bills"]:,}/{q["members"]:,} |')
    lines+=['','These probability cutoffs are separately fixed from 2023 top-eight score quantiles and applied unchanged in 2024. The target fraction need not equal '
      'the retained 2024 fraction. Intervals below are ordinary family-bootstrap 95% intervals; the coverage slices are descriptive.','',
      '| Model | Target fraction in 2023 | Frozen cutoff | 2024 correct / retained | Precision (ordinary 95% interval) | Event recall | Bills / members |',
      '|---|---:|---:|---:|---:|---:|---:|']
    for n in unique(['boosted_dynamic','boosted_context',chosen]):
        for r in stats['selective'][n]:
            if r['target_fraction_2023'] not in [.1,.05]:continue
            ci='—' if any(x is None for x in r['ci95']) else f'{pct(r["ci95"][0],2)} to {pct(r["ci95"][1],2)}'
            lines.append(f'| {label(n)} | {pct(r["target_fraction_2023"],0)} | {r["cutoff_2023"]:.7f} | {r["hits"]:,}/{r["recommendations"]:,} | '
              f'{pct(r["precision"],2)} ({ci}) | {pct(r["recall"],2)} | {r["bills"]:,}/{r["members"]:,} |')
    oracle=stats['forced_top8_oracle']
    lines+=['',f'Even perfect knowledge gives a forced-top-eight ceiling of **{pct(oracle["precision"],2)}**: {oracle["zero_event_bill_dates"]:,} bill-dates '
      'have no subsequent joins. Narrow-budget precision must be read with lost recall and coverage.','',
      '## Evidence-family disposition','',
      f'The inventory maps **{triage["scope"]["inventory_artifacts"]:,} artifacts into {len(triage["families"])} path families**, with '
      f'{triage["scope"]["schema_probes"]} schema probes and all {len(triage["declared_stores"])} declared stores mapped. These are not independent observations. '
      'Not every byte or source family was semantically inspected or empirically tested. '+link('universe_family_triage.md','Complete family/store statuses and uninspected boundaries')+'.','',
      '| Family | What was actually used or inspected | Disposition |','|---|---|---|',
      '| Prior cosponsorship / policy history | Dated official signatures, sponsor ties, predecessor and issue history | Refit controls; not new psychology |',
      f'| Conduct / activity / stages | {len(conduct["history_features"])} prior conduct, {len(conduct["activity_features"])} strictly earlier activity and {len(conduct["stage_features"])} corrected bill-stage features | Separate additions and combined models |',
      f'| Amendments | {len(amendment["features"])} count/exposure/coverage features; prior 116: 3,647 submissions, 44 missing sponsors; prior 117: 5,954 submissions, 92 missing sponsors | Tested; incomplete retrospective BICAM source |',
      f'| Elections | {checks["election_complete_rows_independently_recomputed"]:,} accepted past ballots; {election["rows"]:,} full-roster Congress/member rows before cohort filtering | Tested; later vintages/publication uncertainty remain |',
      '| Language / PUBLIC | Pre-cutoff style and source availability from a current-member-centered corpus | Eligible conditionally; content/coverage/placebo comparisons |',
      '| Shared broadcasts | 503 prior-2021 and 301 prior-2023 qualifying episodes after exact duplicate correction | Tested co-appearance graph; not interaction or endorsement |',
      '| Current Big Five / behavior / receptivity | Later outcomes, current normalization and composite or undated inputs | Excluded as historical traits |',
      '| Influence-maximization / pricing / salience | Current formulas mix stance, money, networks, assumed responses and simulations | Inspected; not independent observed or causal effects |',
      '| Staff networks | Technical v5 checks pass within exploratory release; undated policy/identity/publication limits remain | Not promoted to historical influence or employment truth |',
      '| District / money / lobbying | Earlier census and formal bill attention; current releases/geographies and sign-derived member links can leak or be circular | Historical context tested; current aggregates not backdated |',
      '| Audio / latent personality | Prior failed/null criteria and descriptive identity restrictions remain | No new latent-trait validity or audio calibration claim |',
      '| Letters / witnesses / long-form archives | Original signature proof, attribution, source dates and completeness remain unresolved in named families | Not silently counted as tested predictors |',
      '| Dashboards / workbooks / operational and research copies | Repeated upstream evidence and technical status | Inventory/lineage, not independent instruments |','',
      link('psychology_audit.md','Psychology/language audit')+' · '+link('network_audit.md','Network/influence audit')+' · '+link('money_context_audit.md','Money/election/district audit')+'.','',
      '## Uncertainty and interpretation','',
      f'Resample **{stats["families"]:,} legislative families {stats["replicates"]:,} times**, retaining their member rows and dates. '
      f'The plan contains **{stats["comparisons"]} contrasts**; Bonferroni percentile intervals cover all comparisons separately for precision and Brier. '
      'Ordinary 95% intervals remain in the detailed outputs. These are descriptive development intervals, not confirmatory p-values. They do not remove residual member dependence, '
      'historical model-search optimism, source-vintage uncertainty or survival conditioning. '+link('universe_statistics_plan.json','Statistics plan')+'.','',
      'AP measures ranking across candidate rows; precision at 8 measures within-bill-date recommendations. Brier measures probability error, so lower is better. '
      'A ranking gain and a probability-calibration gain are different findings. Probabilities are calibrated on 2023 only.','',
      f'In 2024 the selected model assigned about **{calibration_expected:,.0f} expected events across all {calibration_rows:,} forecasts**, '
      f'versus **{int(round(calibration_observed)):,} observed**. Its probability levels therefore '
      +('underpredicted' if calibration_shortfall>=0 else 'overpredicted')
      +f' the aggregate event count by {abs(calibration_shortfall):.2%}, despite calibration on 2023. This concerns probability levels, not the number of correct top-eight recommendations.','',
      'This is a forecasting comparison. It does not show that lobbying, psychological targeting, staff connections or media co-appearance cause a signature. '
      'Broader claims require newly collected independent outcomes and frozen forecast receipts.','',
      '## Appendix A — all 24 refits','',
      'Rows follow fixed model categories, not a 2024-selected ordering. The placebo is visible but cannot win selection.','',metrics_table(controls+challengers,result,plan),'',
      '## Appendix B — every challenger against four tree controls','',
      'Cells give extra correct top-eight recommendations and adjusted precision intervals in percentage points. A win requires the whole interval above zero.','',
      '| Challenger | Dynamic trees | PUBLIC trees | Network trees | Context trees | Adjusted wins (of 4) |','|---|---:|---:|---:|---:|---:|']
    for n in challengers:
        cells=[];wins=0
        for b in CONTROLS:
            c=paired(stats,n,b);wins+=int(c['adjusted_interval'][0]>0);cells.append(f'{c["extra_hits"]:+,}; [{interval(c["adjusted_interval"])}]')
        lines.append(f'| {label(n)} | '+' | '.join(cells)+f' | {wins} / 4'+(' (placebo)' if models[n]['placebo'] else '')+' |')
    lines+=['','## Appendix C — validation and complete artifacts','',
      f'Independent extraction checks recomputed {checks["election_complete_rows_independently_recomputed"]:,} accepted election rows, '
      f'{checks["election_prior_service_rows_recomputed_by_interval_endpoint_union"]:,} service-exposure rows, '
      f'{checks["conduct_dynamic_rows_independently_recomputed"]:,} sampled dynamic-conduct rows and '
      f'{checks["conduct_history_columns_independently_checked"]} history columns across {checks["conduct_history_rows_checked"]:,} member/Congress rows. '
      'Amendment counts/service intervals were independently recomputed from raw one-to-one joins. Broadcast matrices were rebuilt from episode ledgers, '
      'exact cross-URL duplicates removed and 500 raw rows checked. These extraction counts precede the 377-member analysis filter.','',
      'The preservation review hashed 3,055 unique earlier files and resolved archived protocol byte/newline bindings. Receipt-bound historical/prospective forecasts matched. '
      'Unbound CSV exports are inventoried without claiming independently proven historical immutability. Other tasks may update dashboards/pointers; they do not rewrite frozen feature receipts.','',
      'Earlier designs remain in '+link('pre_coverage_review','pre_coverage_review')+' and '+link('pre_gold_review','pre_gold_review')+'. '
      'The final cohort revision supersedes the abandoned eligibility restrictions. Every metric reported here comes from final shared-cohort refits.','',
      link('universe_results.json','All metrics')+' · '+link('universe_statistics.json','All paired, stratum and coverage results')+' · '+link('model_comparison.csv','Model CSV')+' · '+link('paired_comparison.csv','Paired CSV')+' · '+link('selective_comparison.csv','Frozen-cutoff CSV')+'.','',
      link('universe_plan.json','Frozen model plan')+' · '+link('universe_selection.json','2023 selection freeze')+' · '+link('gold_cohort.csv','Cohort identities')+' · '+link('report_summary.json','Summary and report-input hashes')+'.','',
      link('universe_extraction_review.md','Extraction review')+' · '+link('prior_preservation_review.md','Preservation review')+' · '+link('amendment_receipt.json','Amendment receipt')+' · '+link('relational_receipt.json','Broadcast receipt')+' · '+link('relational_panel_receipt.json','Broadcast panel receipt')+'.','',
      link('universe_comparison.pdf','Figure PDF')+' · '+link('universe_comparison.svg','Figure SVG')+' · '+link('research_context.md','Research precedent and methodological context')+'.']
    for p,title in [(OUT/'universe_boundary_checks.json','Boundary checks'),
                    (OUT/'gold_model_review.md','Final cohort model review'),
                    (OUT/'universe_statistics_review.md','Final statistics review'),
                    (OUT/'verification_receipt.json','Final verification receipt'),
                    (CODE/'README.md','Reproduction instructions'),(OUT/'BRAIN_UPDATE_DRAFT.md','Brain update draft')]:
        if p.exists():lines+=['',link(p,title)+'.']
    for name,h in bindings.items():assert digest(OUT/name)==h,'Report input changed: '+name
    (OUT/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    write_json(OUT/'report_summary.json',dict(schema='continuing-member-report-v1',generated_utc=stamp(),cohort_size=377,
      models=24,challengers=16,refit_controls=8,eligible=eligible,chosen_on_2023=chosen,chosen_2024=later,baseline_2024=baseline,
      selected_vs_dynamic=selected_change,adjusted_positive_by_control=positives,adjusted_positive_against_all_four=all_four,
      selected_2024_calibration=dict(rows=calibration_rows,observed_events=calibration_observed,expected_events=calibration_expected,
        aggregate_fraction_underpredicted=calibration_shortfall,source='Existing frozen calibration bins; no refit or probability changes'),
      uncertainty_comparisons=79,bootstrap_replicates=100000,source_hashes=bindings,report_code_sha256=digest(__file__),
      render_environment=dict(python_executable=sys.executable,python_version=platform.python_version(),
        python_full_version=sys.version,matplotlib_version=matplotlib.__version__,numpy_version=np.__version__,
        role='Report and figure rendering only; distinct from the model-fitting environment'),
      figure_models=plot_names,figure_curves=curves,qualification='Retrospective conditional development for 377 continuing members; actual signature labels, not psychological gold traits.'))
    fields=['model','label','role','source_qualification','year','rows','events','hits_at_8','slots_at_8','precision_at_8','recall_at_8','average_precision','brier']
    with (OUT/'model_comparison.csv').open('w',newline='',encoding='utf8') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for n in controls+challengers:
            for year in [2023,2024]:
                r=result['models'][n][f'year_{year}'];writer.writerow(dict(model=n,label=label(n),role=models[n]['role'],source_qualification=models[n]['source_qualification'],year=year,**{k:r[k] for k in fields[5:]}))
    fields=['comparison','extra_hits','delta_precision','ci95_low','ci95_high','adjusted_low','adjusted_high','delta_brier','brier_ci95_low','brier_ci95_high','brier_adjusted_low','brier_adjusted_high']
    with (OUT/'paired_comparison.csv').open('w',newline='',encoding='utf8') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for n,c in stats['paired'].items():
            row=dict(comparison=n,extra_hits=c['extra_hits'],delta_precision=c['delta_precision'],delta_brier=c['delta_brier'])
            for prefix,key in [('ci95','ci95'),('adjusted','adjusted_interval'),('brier_ci95','brier_ci95'),('brier_adjusted','brier_adjusted_interval')]:row[prefix+'_low'],row[prefix+'_high']=c[key]
            writer.writerow(row)
    fields=['model','target_fraction_2023','cutoff_2023','hits','recommendations','precision','ci95_low','ci95_high','recall','bills','members']
    with (OUT/'selective_comparison.csv').open('w',newline='',encoding='utf8') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for n,rows in stats['selective'].items():
            for r in rows:writer.writerow(dict(model=n,ci95_low=r['ci95'][0],ci95_high=r['ci95'][1],**{k:r[k] for k in fields[1:] if not k.startswith('ci95_')}))
    print('Final continuing-member report, tables and scientific figure written.')


if __name__=='__main__':run()
