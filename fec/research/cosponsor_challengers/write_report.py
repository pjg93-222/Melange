"""Render the measured results into a compact, source-linked research report."""
import json

from audit_data import OUT

LABELS={
    "existing_production":"Existing production logistic (30-day recalibration)",
    "logistic_base":"Basic 30-day logistic",
    "logistic_history":"Logistic + predecessor/policy history",
    "logistic_dynamic":"Logistic + history + timing/activity",
    "boosted_history":"Boosted trees + history",
    "boosted_dynamic":"Boosted trees + history + timing/activity",
    "time_to_sign":"Weekly time-to-sign",
    "logistic_public":"Logistic + timing + public evidence",
    "boosted_public_coverage":"Boosted trees + public coverage/mentions",
    "boosted_public":"Boosted trees + public evidence/positions",
    "time_to_sign_public":"Weekly time-to-sign + public evidence",
}


def pct(x):
    return f"{100*x:.2f}%"


def table(results,names):
    lines=["| Model | Average precision | Precision at 8 | Recall at 8 | Brier |",
           "|---|---:|---:|---:|---:|"]
    for name in names:
        r=results[name]
        lines.append(f"| {LABELS[name]} | {r['average_precision']:.5f} | {pct(r['precision_at_8'])} | {pct(r['recall_at_8'])} | {r['brier']:.6f} |")
    return "\n".join(lines)


def interval_text(result,metric="precision_at_8"):
    r=result[metric]
    a,b=r["ci95"]
    fa,fb=r["familywise_interval"]
    multiplier=100 if metric=="precision_at_8" else 1
    unit=" percentage points" if metric=="precision_at_8" else ""
    decimals=4 if metric=="precision_at_8" else 7
    return f"{a*multiplier:+.{decimals}f} to {b*multiplier:+.{decimals}f}{unit} (95%); {fa*multiplier:+.{decimals}f} to {fb*multiplier:+.{decimals}f}{unit} (multiplicity-adjusted)"


def write():
    audit=json.loads((OUT/"data_audit.json").read_text())
    panel=json.loads((OUT/"panel_receipt.json").read_text())
    public=json.loads((OUT/"public_extended_audit.json").read_text())
    dev=json.loads((OUT/"development_results.json").read_text())
    final=json.loads((OUT/"final_results.json").read_text())
    freeze=json.loads((OUT/"final_prediction_freeze.json").read_text())
    components=json.loads((OUT/"component_diagnostics.json").read_text())
    benchmarks=json.loads((OUT/"simple_benchmark_results.json").read_text())
    chosen=dev.get("chosen_challenger") or max(dev["models"],key=lambda k:dev["models"][k]["selected_metrics"]["average_precision"])
    base=final["models"]["logistic_base"]
    current=final["existing_common_population"]["existing_production"]
    candidate=final["existing_common_population"][chosen]
    extra=candidate['hits_at_8']-current['hits_at_8']
    interval=final['existing_common_uncertainty']['comparisons'][chosen]['precision_at_8']['familywise_interval']
    lines=["# Cosponsorship challenger experiment — 2026-09-05","",
           f"**The clearest improvement comes from better member and predecessor-bill history.** On the identical population covered by the existing model, the selected challenger correctly shortlisted {candidate['hits_at_8']:,} subsequent joins versus {current['hits_at_8']:,}: {extra:,} additional joins, a {extra/current['hits_at_8']:.1%} increase. Precision at eight rose from {pct(current['precision_at_8'])} to {pct(candidate['precision_at_8'])}; the multiplicity-adjusted family-bootstrap interval for the gain is +{100*interval[0]:.2f} to +{100*interval[1]:.2f} percentage points. Absolute next-30-day precision remains modest.","",
           "Trees rank the overall set of bill-member opportunities better in this test, but do not have a statistically clear top-eight advantage over logistic regression given the same history and timing inputs. The weekly survival model is viable but also does not establish a better shortlist. Strictly dated, bill-specific public endorsements are too sparse before signature to fit that proposed model meaningfully.","",
           f"**Selected on Congress 118 development data:** {LABELS[chosen]}. The final Congress 119 results below were evaluated only after all predictions were frozen at {freeze['frozen_utc']}.","",
           "This is a retrospective event-time backtest. Historical publication dates and official event dates are available; historical first-observed snapshots are not comprehensive. It does not establish live prospective accuracy or causal effects of lobbying.","",
           "## Do we have the data?","",
           f"Yes for structural, predecessor/history, boosted-tree, and time-to-sign experiments: {sum(v['bills'] for v in audit['bills'].values()):,} HR/S bills and {sum(v['cosponsor_records'] for v in audit['bills'].values()):,} dated cosponsor records across Congresses 116–119. The extraction found zero missing cosponsor dates. Serving-member terms, introduced titles, dated actions, and previous-Congress ideology are available.","",
           "| Congress | HR/S bills | Finance referral bills | Zero-cosponsor finance bills | Later finance joins |",
           "|---|---:|---:|---:|---:|"]
    for cg,r in audit["bills"].items():
        lines.append(f"| {cg} | {r['bills']:,} | {r['finance_at_introduction']:,} | {r['finance_zero_cosponsor_bills']:,} | {r['finance_later_join_events']:,} |")
    counts=public["counts"]
    lines += ["",f"The expanded text extraction retained {counts['accepted_hearing']:,} relevant hearing turns, {counts['accepted_social']:,} social posts, {counts['accepted_press']:,} official press headlines, and {counts['accepted_interview']:,} interview excerpts. Speaker identity is checked against dated chamber service and party. These are machine-parsed sources, not a fully manually validated speech corpus.","",
              f"**The direct bill-position data are insufficient.** Strict rules found {counts['explicit_bill_position_documents']} documents with an explicit position linked to a bill across all years. The training and development risk sets contain zero usable explicit bill-support or opposition observations. Most matching statements describe existing/same-day cosponsorship, concern other bills, or fall outside this experiment's six-month bill-age window. The final risk set has only {final['public_coverage']['explicit_bill_support_rows']} rows with such support. A direct endorsement-to-sign model cannot be estimated meaningfully from these inputs.","",
              f"The fitted public-evidence variants instead test dated topic mentions and explicit topic-level stance, alongside source-coverage controls. Topic/bill evidence covers {pct(final['public_coverage']['fraction'])} of the final rows and {final['public_coverage']['events']:,} later joins. Zero evidence means no observed coverage, not opposition.","",
              "## Has related research been done?","",
              "- **Cosponsorship/text precedent:** [Russo et al., ACL 2023](https://aclanthology.org/2023.acl-long.166/) combine bill text, congressional speeches, and relational graph representations to distinguish active/original from passive/later cosponsorship. Their reported F1 concerns a different classification task and population, including bills with more than ten cosponsors; it is not an expected accuracy for our unbalanced future-join forecast.",
              "- **Congressional timing precedent:** [Brandenberger, 2018](https://doi.org/10.1016/j.socnet.2018.02.001) models event-ordered reciprocity and time to cosponsorship in the 113th Congress.",
              "- **Duration-model precedent:** [Timing Their Positions](https://www.cambridge.org/core/journals/state-politics-and-policy-quarterly/article/timing-their-positions-cosponsorship-in-the-state-legislature/BDFFF37FE5D8355DC5867387682D3FA7) uses Cox duration models for state legislative cosponsorship.",
              "- **Adjacent ensemble/text precedent:** [Nay, 2017](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0176999) predicts bill enactment using legislative text and an ensemble model. Enactment is a different outcome from a particular member joining.","",
              "## Frozen experiment","",
              "Predict a first cosponsorship in the next 30 days among serving, unsigned, same-chamber members. Original/day-zero cosponsors and bill sponsors are excluded. Bills enter based on introduction-date finance/agriculture committee referrals, with no eventual cosponsor floor. Forecasts occur at ages 0, 35, 70, 105, 140 and 175 days, giving nonoverlapping windows over the first six months. This does not test older bills or a daily event-triggered alert service.","",
              "Train on Congress 117; choose configurations and probability calibration on Congress 118; refit on 117+118; evaluate once on 119, with outcomes cut at 2026-09-03. Earlier Congress 116 supplies the first historical features. All models use the same mature final rows. The weekly survival model also uses censored training exposure and integrates its estimated daily rates across four seven-day intervals plus a two-day interval.","",
              "| Split | Candidate snapshots | Complete 30-day windows | Future joins in complete windows |",
              "|---|---:|---:|---:|"]
    for cg,r in panel["splits"].items():
        lines.append(f"| {cg} | {r['rows']:,} | {r['mature_rows']:,} | {r['mature_events']:,} |")
    lines += ["",f"Final event prevalence is {pct(base['base_rate'])}. Predicting 'no' everywhere would appear highly accurate, which is why ordinary accuracy is not used. Average precision measures ranking across recall levels; precision at 8 is the fraction of the eight highest-ranked candidates per bill/date who subsequently join. Neither is an individual certainty.","",
              "## Final results: complete new-model population","",table(final["models"],list(dev["models"])),"",
              "## Comparison with the actual existing production model","",
              f"The production score exists on {final['existing_coverage']['rows']:,} final rows ({pct(final['existing_coverage']['fraction'])}), covering {final['existing_coverage']['bills']:,} bills. Every entry in the table below is evaluated on exactly those rows. The production model's raw eventual-sign score is recalibrated to the 30-day outcome on Congress 118 only. Its original count-based eligibility and committee snapshot timing remain limitations of that comparator.","",
              table(final["existing_common_population"],["existing_production","logistic_base","logistic_history","logistic_dynamic","boosted_dynamic","time_to_sign","boosted_public_coverage","boosted_public"]),"",
              "## Uncertainty and practical significance","",
              "Confidence intervals resample whole legislative families, preserving bill/date clusters. Brier comparisons also receive a crossed member/family sensitivity check. The report includes multiplicity-adjusted intervals for the fixed challenger family. AP interval computation uses at most 2,048 score bins; exact AP is reported as the point estimate, and binning error is retained in the JSON. There is only one final Congress, so these intervals do not measure variation across future Congresses.","",
              "| Challenger versus existing production on common rows | Change in precision at 8 | Change in Brier (lower is better) |",
              "|---|---|---|"]
    for name,r in final["existing_common_uncertainty"]["comparisons"].items():
        lines.append(f"| {LABELS[name]} | {interval_text(r)} | {interval_text(r,'brier')} |")
    lines += ["","## What accounts for the improvement?","",
              "These paired secondary comparisons use all 3,569,688 complete final forecast rows and 89,256 top-eight slots. They separate richer inputs from the choice of algorithm. Intervals resample 1,736 legislative families 3,000 times and adjust for these five comparisons; they describe this held-out Congress, not variation across future Congresses.","",
              "| Change | Additional correctly shortlisted joins | Change in precision at 8 | Adjusted interval, percentage points |",
              "|---|---:|---:|---:|"]
    descriptions={
        "history_added_to_logistic":"Add predecessor/member-policy history to basic logistic",
        "timing_added_to_logistic":"Add timing/activity to history logistic",
        "trees_vs_logistic_same_history":"Replace logistic with trees, same history inputs",
        "trees_vs_logistic_same_dynamic_inputs":"Replace logistic with trees, same history/timing inputs",
        "survival_vs_dynamic_logistic":"Replace dynamic logistic with weekly survival",
    }
    for key,r in components['comparisons'].items():
        low,high=r['five_comparison_familywise_interval']
        lines.append(f"| {descriptions[key]} | {r['additional_hits']:+,} | {100*r['delta_precision_at_8']:+.3f} pp | {100*low:+.3f} to {100*high:+.3f} |")
    lines += ["","History is the only one of these five changes with a clear positive top-eight interval. On the production-common population, history logistic already captures 990 joins versus the existing model's 734; the selected challenger captures 1,010. This is not a causal decomposition, but it shows how much of the practical shortlist gain is available with the simpler model.","",
              "Overall ranking tells a different, complementary story: adding timing to history logistic increases full-population average precision from 0.02278 to 0.04678; trees with those same dynamic inputs reach 0.06086. Those are measured point estimates. A model can better identify which bills are likely to attract joins without materially changing which eight members to pick for each bill.","",
              "Two simple historical rules, frozen before final performance was inspected, also trail the enhanced logistic model on the complete population:","",
              "| Historical rule | Average precision | Precision at 8 |",
              "|---|---:|---:|"]
    for key,label in [('sponsor_affinity','Prior sponsor affinity'),('prior_analogue_support','Prior analogue support')]:
        r=benchmarks[key]['full']
        lines.append(f"| {label} | {r['average_precision']:.5f} | {pct(r['precision_at_8'])} |")
    lines += ["","These are descriptive benchmarks. The third rule, member signing frequency, collapsed to a constant under development-only monotone calibration and is documented separately in the benchmark results.","",
              "**Public evidence ablation:** compare public-enabled boosted trees with the otherwise comparable dynamic boosted model; then compare explicit stance features with the coverage/mention-only control. This prevents attributing all improvement from richer source coverage to policy stance.",""]
    for name,r in final["public_ablation_uncertainty"]["comparisons"].items():
        lines.append(f"- {LABELS[name]} versus dynamic boosted trees, precision-at-8 difference: {interval_text(r)}.")
    if "public_direction_ablation_uncertainty" in final:
        r=final["public_direction_ablation_uncertainty"]["comparisons"]["boosted_public"]
        lines.append(f"- Adding support/oppose indicators beyond coverage/mentions, precision-at-8 difference: {interval_text(r)}.")
    assert freeze['predictions']['boosted_public']==freeze['predictions']['boosted_public_coverage']
    lines += ["","The directional-stance and coverage-only tree variants produced byte-identical final prediction files. Even the small coverage/mention gain over dynamic trees has an interval spanning zero. This experiment provides no clear incremental public-evidence gain; it does not demonstrate that a sufficiently rich, correctly attributed, pre-signature position corpus would be unhelpful."]
    lines += ["","## What was improved during development","",
              "| Prespecified step | Development average precision |",
              "|---|---:|"]
    for name in ["logistic_base","logistic_history","logistic_dynamic","boosted_dynamic","time_to_sign","boosted_public_coverage","boosted_public"]:
        lines.append(f"| {LABELS[name]} | {dev['models'][name]['selected_metrics']['average_precision']:.5f} |")
    lines += ["","These are development comparisons, not fresh confirmation. No configurations were changed using final-test outcomes. Further improvements must use the historical development period or a new future test window.","",
              "## Next improvements supported by this audit","",
              "1. Preserve daily first-observed timestamps and bill/member source links so the next evaluation can be genuinely prospective.",
              "2. Build a manually checked set of bill-specific statements that precede signature; distinguish endorsement, a past vote, sponsor announcements, third-party quotes, and opposition. Use event-triggered or weekly forecast dates to avoid missing short statement-to-sign intervals.",
              "3. Extend evaluation beyond the first six months and replicate across additional held-out Congresses before treating the result as a general forecasting advantage.",
              "4. Review normalized-title analogue links for substantive changes, and add introduced-text similarity or verified reintroduction links as a separate development experiment.","",
              "## Validation and artifacts","",
              "Eleven boundary tests passed, including post-date exclusion, member/chamber eligibility, bill-versus-amendment joins, withdrawals, first-person attribution, and survival exposure accounting. All three learner families recovered a planted synthetic signal. An independent audit checked 7,500 sampled labels against the frozen dated rosters, checked every feature for finite values, confirmed unique risk rows, and verified file hashes.","",
              "The initial metadata conversion exceeded available shared-host memory and was recovered with the identical deterministic row ordering; future construction streams the metadata. Our research artifacts were NTFS-compressed to free disk space, without changing their bytes. No production model, workbook, rank, scheduler, or other lane's source files were modified.","",
              "- [Final measured results](final_results.json)","- [Development configurations and results](development_results.json)",
              "- [Paired history/timing/algorithm diagnostics](component_diagnostics.json)","- [Simple historical benchmarks](simple_benchmark_results.json)",
              "- [Frozen prediction receipt](final_prediction_freeze.json)","- [Panel validation](panel_validation.json)",
              "- [Boundary and synthetic-test receipt](verification_receipt.json)","- [Final artifact integrity manifest](experiment_manifest.json)",
              "- [Source data audit](data_audit.json)","- [Extended public-source audit](public_extended_audit.json)",
              "- [Explicit-position lead-time audit](public_lead_time_audit.json)","- [Scored final forecasts](scored_final_forecasts.parquet)",
              "- [Model execution log](model_run.log)","",
              f"[Reproduction scripts and instructions](<{(OUT.parent.parent/'fec/research/cosponsor_challengers/README.md').as_posix()}>) and the [pre-fit protocol](<{(OUT.parent.parent/'fec/research/cosponsor_challengers/PROTOCOL.md').as_posix()}>). Dependencies: Python 3.12, NumPy, pandas, SciPy, scikit-learn 1.9, PyYAML, joblib, PyArrow, threadpoolctl. All fit and evaluation routines run locally.",""]
    path=OUT/"REPORT.md"
    report_text="\n".join(lines)
    for name in ("final_results.json","development_results.json","final_prediction_freeze.json","panel_validation.json","data_audit.json", "public_extended_audit.json","public_lead_time_audit.json","scored_final_forecasts.parquet","model_run.log","component_diagnostics.json","simple_benchmark_results.json","verification_receipt.json","experiment_manifest.json"):
        report_text=report_text.replace(f"]({name})",f"](<{(OUT/name).as_posix()}>)")
    path.write_text(report_text,encoding="utf-8")
    print(path)


if __name__=="__main__":
    write()
