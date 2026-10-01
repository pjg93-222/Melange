"""Render the pilot's measured findings and reviewable evidence as Markdown."""
from collections import Counter
from .data import ROOT,read_json,write_json,digest
from .run import read_lines


def main():
    out=ROOT/"outputs/member_personal_relationships/20260910_pilot"
    m=read_json(out/"manifest.json"); s=m["results"]; v=read_json(out/"verification_receipt.json")
    features=read_lines(out/"pair_features.ndjson"); relations=read_lines(out/"relationships.ndjson")
    events=read_lines(out/"events.ndjson"); ablations=read_lines(out/"ablations.ndjson")
    relation={(r["actor"],r["target"]):r for r in relations}
    by_pair={(f["actor"],f["target"]):f for f in features}
    coverage=read_lines(out/"coverage.ndjson")
    matched=[f for f in features if f["work_opportunities"]]
    positive=[f for f in matched if f["work_residual_rate"]>0]
    stable=sum(f["work_residual_rate_7"]>0 for f in positive)
    cross=[r for r in relations if r["affinity"]=="indirect_candidate" and
           not by_pair[(r["actor"],r["target"])]["same_party"]]
    no_coverage=sum(not c["speech_counts"] for c in coverage)
    lines=[
        "# Member personal relationships — first pilot results",
        "September 10, 2026. Research prototype; production network unchanged.",
        "The prototype runs and passes its software checks. It identifies personal accounts and produces candidates whose cooperation and personality similarities exceed matched political comparisons. **It has not established that these proxy signals predict friendship accurately.** The necessary independent relationship labels are not available yet.",
        "| Test or run result | Measured result |",
        "|---|---:|",
        f"| Software and corpus checks | {v['tests_run']} passed; {v['failures']} failures; {v['errors']} errors |",
        f"| Deterministic rebuild | {v['artifacts_compared']} core artifact hashes identical |",
        f"| Dated target roster | {m['roster']['dated_roster']} of {m['roster']['roster_input']} stored members |",
        f"| Speech/interview/hearing turns scanned, September 10, 2024–September 10, 2026 | {m['speeches']['scanned']:,} |",
        f"| All-topic mature 119th-Congress bills | {m['bills']['included_bills']:,}, across {m['bills']['policy_areas']} policy areas |",
        f"| Eligible member–bill opportunities in the roster | {s['all_work_observations']:,} |",
        f"| Pair pilot | {s['pilot_pairs']} pairs, {s['directed_assessments']} directions |",
        f"| Source candidates retrieved | {m['speeches']['candidates']} |",
        f"| Deliberately selected source cases reviewed by the assistant | {s['reviewed_source_rows']} |",
        f"| Retained provisional personal-affinity accounts | {s['personal_seed_events']} |",
        f"| Indirect review candidates | {s['affinity_status']['indirect_candidate']} directions, including {len(cross)} across parties |",
        "| Established antagonism ties | 0; all 320 remain unknown |",
        "| Friendship prediction accuracy / probability calibration | Not estimated |",
        "",
        "**What looks beyond political and geographic incentives**",
        "For A→B, the work comparison asks how often A joins B's bills relative to A's support for other sponsors with matching party relationship, state relationship, ideological-distance bin, and leadership status, within policy areas and dated same-chamber service. Every A→B observation is excluded from its own baseline. Personality compatibility is also compared within the same member's political/geographic/chamber/status strata and the same available E/A/O trait set. Similarity or distance in politics/geography alone produces no personal score.",
        f"Of the 320 directions, {s['work_baseline_available']} had usable work comparisons, covering {s['matched_work_observations']:,} opportunities; {s['work_baseline_unavailable']} lacked opportunities or enough comparators. Personality estimates were available for {s['personality_pair_coverage']} directions, and matched personality comparisons for {s['personality_matched_coverage']}.",
        "These controls are an initial approximation. State match and coarse DW-NOMINATE bins do not fully remove geographic or ideological incentives. Shared committees, caucuses, donor networks, district proximity, bill popularity, and narrower policy interests remain possible explanations. The residual is unusual cooperation, not an identified personal effect.",
        "",
        "**Personal accounts retained after source review**",
        "Each account is a dated public expression reviewed by the assistant and checked against the original Congressional Record. None is an independently labeled model test case. A single source occasion does not establish repeated independent evidence or current mutual friendship.",
        "| Direction | Evidence and qualification | Original record |",
        "|---|---|---|",
    ]
    descriptions={
        "90f03416cc5a4bbf3632":"Burchett describes a longstanding friendship and a condolence call to his mother after his father's death. Strongest specific personal account in this review; shared Tennessee history remains context, not the reason for retaining it.",
        "90cd69ba983466502e47":"Lee describes longstanding affection involving both spouses. Specific personal content, but delivered during a ceremonial welcome; weaker than a repeated voluntary-interaction history.",
        "df929387644162fa212f":"Womack explicitly distinguishes his friendship with Clyburn from their political differences. Surrounding proceedings include Clyburn's sympathy for Womack's bereavement; one floor episode, not independent corroboration.",
        "5c41003a37ab9ecc9441":"Stevens describes affection for the McGovern family and repeated evenings together. Main subject is Molly McGovern, so dyad-specific warmth toward Jim is a weaker provisional inference."
    }
    for e in events:
        if e["evidence_id"] in descriptions:
            source=e["official_verification"]
            lines.append(f"| {e['actor_name']} → {e['target_name']} | {descriptions[e['evidence_id']]} | [{e['event_date']}, {source['page_label']}]({source['url']}) |")
    lines.extend([
        "",
        "**Illustrative cooperation candidates — not friendship findings**",
        "These examples were selected from the pilot after seeing their residuals. Expected signatures come from the matched descriptive baseline; these are not out-of-sample forecasts. More than 20 opportunities are required for this display. The first value is A joining bills sponsored by B.",
        "| Direction | Party / state relationship | Observed / opportunities | Expected signatures | Interpretation |",
        "|---|---|---:|---:|---|",
    ])
    display=[("Jimmy Panetta","Joe Wilson"),("Jimmy Panetta","Mike Kelly"),("Zachary Nunn","Donald Davis")]
    for names in display:
        f=next(f for f in features if (f["actor_name"],f["target_name"])==names)
        r=relation[(f["actor"],f["target"])]; label=("Both excess personality similarity and excess cooperation; review candidate."
            if r["affinity"]=="indirect_candidate" else "Cooperation stands out, but no positive matched personality signal; relationship remains unknown.")
        lines.append(f"| {names[0]} → {names[1]} | Different parties and states | {f['work_observed']} / {f['work_opportunities']} | {f['work_expected']:.2f} | {label} |")
    lines.extend([
        "",
        "**Network proximity and sensitivity tests**",
        "The signed personal graph implements directed shortest paths, normalized neighbor overlap, hub-downweighted resource allocation, degrees, and all 16 directed signed two-step motifs. Before calculating them, it removes the focal pair in both directions and any linked source families. Neither predicted edges nor ordinary policy-reference edges are allowed into the personal seed graph.",
        "The four accepted seeds are too sparse to provide an indirect path for any pilot pair. Consequently, the network component changes zero real-data scores. This is a data limitation revealed by the run; synthetic network tests verify the calculations and masking, but do not establish predictive value. The much denser legacy reference graph remains a discovery aid and contact diagnostic.",
        f"Context alone produced a nonzero personal score in **{s['context_only_nonzero']} of 320** directions. Removing personality changed {s['personality_score_changes']} exploratory scores; removing distinctive cooperation changed {s['work_score_changes']}; removing the personal graph changed {s['network_score_changes']}. Of {len(positive)} positive 30-day cooperation residuals, {stable} remained positive with the 7-day window. These are engineering sensitivities, not estimates of predictive improvement.",
        "",
        "**Errors caught by reviewing the original meaning**",
        "The 27 cases were chosen to stress the system; their acceptance rate is not a precision estimate. Twenty-three did not qualify as personal seeds. Examples include the singer Al Green being matched to the congressman, former President James Earl Carter being matched to Representative Earl Carter, praise of Curtis being attached to Booker in the same paragraph, and Barrasso quoting Schatz about a third person. Group meals, policy references to fishing or school lunch, ordinary leadership praise, and explicit status deference were retained as context instead of personal ties.",
        f"The extractor retrieved {m['speeches']['candidates']} cases but missed surname-only/pronoun relationships by design. {no_coverage} dated members had no qualifying speech rows in the window; {m['speeches']['unknown_or_out_of_service_speaker']:,} rows could not be assigned to an in-service target-roster speaker. The dated service reference excluded one stored roster entry; details are in the source manifest. Original-record checks confirmed the four retained accounts, but do not validate the rest of the corpus.",
        "",
        "**What is implemented and what remains**",
        "Implemented: read-only frozen ingestion; original locators and text hashes; episode/source-family deduplication; reviewed source ledger; separate directed affinity and antagonism; active weak E/A/O similarity prior; matched political/geographic personality comparison; opportunity-adjusted work residuals; signed network features and pair masking; a reproducible stratified pilot; source review queue; ablations; source/output/production hash checks.",
        "Remaining before a predictive relationship model: broader personal and antagonism evidence; independent human relationship labels; precise geography and institutional/caucus controls; source-excluded personality measurements; joint fitted coefficients and interactions; formation/persistence modeling; held-out member/time/pair evaluation; calibration and uncertainty estimates. C/N and directed E-ego/A-alter values are exported but their effects are not fitted. No numeric friendship probabilities are emitted.",
        "The next useful step is to review the 35 indirect candidates and add independent positive, negative, and well-observed non-tie labels alongside the random sample. Then test whether the full model improves on the political/opportunity baseline within comparable pairs. Stronger controls should be added before treating the work residuals as evidence of personal attachment.",
        "",
        " · ".join(f"[{label}](<{(out/name).as_posix()}>)" for label,name in [
            ("All 320 directional assessments","PAIR_REVIEW.md"),("The 27 source decisions","EVIDENCE_REVIEW.md"),
            ("Test output","TEST_RESULTS.txt"),("Verification receipt","verification_receipt.json"),("Run manifest","manifest.json")]),
    ])
    # Keep contiguous table rows together; every prose paragraph is separated.
    content=""
    previous=""
    for line in (x for x in lines if x):
        separator="\n" if previous.startswith("|") and line.startswith("|") else "\n\n"
        content+=(separator if content else "")+line
        previous=line
    (out/"REPORT.md").write_text(content+"\n",encoding="utf-8")
    pair_lines=["# Directional pilot review","","Exploratory candidates, not calibrated friendship predictions. Unknown is not neutral. Numerical work rates are descriptive. See REPORT.md for controls and limitations.","",
        "| Member A → member B | Affinity status | Personal episodes | Observed / matched opportunities | Expected | Excess E/A/O similarity |",
        "|---|---|---:|---:|---:|---:|"]
    for r in sorted(relations,key=lambda r:(-r["positive_episodes"],-r["affinity_candidate_score"],r["actor_name"],r["target_name"])):
        f=by_pair[(r["actor"],r["target"])]; excess=f["personality_similarity_excess"]
        pair_lines.append(f"| {r['actor_name']} → {r['target_name']} | {r['affinity']} | {r['positive_episodes']} | {f['work_observed']} / {f['work_opportunities']} | {f['work_expected']:.2f} | {excess:+.3f} |" if excess is not None else
                          f"| {r['actor_name']} → {r['target_name']} | {r['affinity']} | {r['positive_episodes']} | {f['work_observed']} / {f['work_opportunities']} | {f['work_expected']:.2f} | unavailable |")
    (out/"PAIR_REVIEW.md").write_text("\n".join(pair_lines)+"\n",encoding="utf-8")
    ev_lines=["# Source review ledger","","Assistant-reviewed, purposive cases; not independent human gold. Excerpts retain original source wording. Rejected retrievals remain visible so their failure modes can be inspected.",""]
    for e in events:
        ev_lines += [f"## {e['actor_name']} → {e['target_name']} — {e['category']}","",
                     f"{e['event_date']} · {e['source']} · {e['evidence_id']}","",e["reason"],"",
                     f"Locator: `{e['source_locator']}`; package: `{e['package']}`.","",
                     "\n".join("> "+line for line in e["text"].splitlines()),""]
        if e.get("official_verification"):
            ev_lines += [f"[Official record]({e['official_verification']['url']}). {e['official_verification']['finding']}",""]
    (out/"EVIDENCE_REVIEW.md").write_text("\n".join(ev_lines)+"\n",encoding="utf-8")
    write_json(out/"report_receipt.json",dict(report_sha256={name:digest(out/name) for name in
        ["REPORT.md","PAIR_REVIEW.md","EVIDENCE_REVIEW.md"]},results_sha256=digest(out/"results.json"),
        verification_sha256=digest(out/"verification_receipt.json"),reporter_sha256=digest(__file__)))
    print(out/"REPORT.md")


if __name__=="__main__":
    main()
