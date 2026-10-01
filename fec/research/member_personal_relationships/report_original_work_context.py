"""Render every declared development result and link the underlying bills."""
from datetime import datetime,timezone
from pathlib import Path
from collections import Counter
import numpy as np
from .data import read_json,digest,ROOT,write_ndjson
from .run_history import read_rows
from .regression import save,clean_json
from .original_work_context import OUT,PREVIOUS,INPUT,MODELS

LABELS={
 'R0_main_effects':'Original work + existing personality/main effects',
 'R1_similarity_distance':'R0 + overall similarity × ideological distance',
 'R2_distance_bipartisanship':'R0 + similarity × distance × bipartisanship',
 'R3_party_bipartisanship':'R0 + similarity × party difference × bipartisanship',
 'R4_separate_traits':'R0 + separate E/A/O similarity × distance',
 'R5_joint_low_agreeableness':'R0 + jointly low A and low A × distance',
 'R6_joint_high_extraversion':'R0 + jointly high E and high E × distance',
}

def fmt(x,n=3):return 'missing' if x is None else f'{x:.{n}f}'
def link(path,label):return f'[{label}](<{str(path.resolve()).replace(chr(92),chr(47))}>)'


def bill_receipts(pairs):
    bills=read_rows(INPUT/'bills.ndjson');receipts=[]
    for p in pairs:
        a,b=p['pair'];shared=[];a_to_b=[];b_to_a=[]
        for bill in bills:
            original=set(bill['original'])
            if a in original and b in original:shared.append(bill)
            if a in original and b==bill['sponsor']:a_to_b.append(bill)
            if b in original and a==bill['sponsor']:b_to_a.append(bill)
        assert len(shared)==p['shared_bills']
        assert len(a_to_b)==p['original_direct_a_to_b']
        assert len(b_to_a)==p['original_direct_b_to_a']
        def compact(bs):return [dict(key=b['key'],introduced=b['introduced'],title=b['title'],sponsor=b['sponsor'],
            original_coalition_size=len(b['original']),url=b['url'],focal_original_withdrawals={k:v for k,v in b['withdrawals'].items() if k in (a,p['pair'][1]) and k in b['original']}) for b in bs]
        receipts.append(dict(pair=p['pair'],names=p['names'],shared_original=compact(shared),
            original_a_to_b=compact(a_to_b),original_b_to_a=compact(b_to_a)))
    write_ndjson(OUT/'original_pair_bill_receipts.ndjson',receipts)
    return receipts


def main():
    run=read_json(OUT/'run_receipt.json');results=read_json(OUT/'model_results.json')
    rank=read_json(OUT/'same_fit_auc.json');previous=read_json(PREVIOUS/'model_results.json')
    oldrank=read_json(PREVIOUS/'same_fit_auc.json');pairs=read_json(OUT/'pair_descriptions.json')
    sensitivity=read_json(OUT/'without_mace_crockett.json');coef=read_json(OUT/'coefficient_stability.json')
    audit=read_json(OUT/'work_audit.json');flag=read_json(OUT/'source_flag_audit.json')
    context=read_rows(OUT/'exchange_context.ndjson');creceipt=read_json(OUT/'exchange_context_receipt.json')
    assert set(results)==set(MODELS)
    receipts=bill_receipts(pairs)
    spectrum=read_rows(OUT/'relationship_spectrum.ndjson')
    graded={r['id']:r for r in read_rows(OUT/'graded_events.ndjson')}
    p0=previous['R0_main_effects']['metrics'];r0=results['R0_main_effects']['metrics'];counts=audit['counts']
    lines=['# Original cosponsorship and personality/context investigation','',
      '**Current relationship representation:** separate graded affinity and tension, with continuous original-work measures. They may coexist. Senate courtesy is explicitly accounted for, and Durbin–Scott’s floor statement does not establish personal closeness. '+link(OUT/'SPECTRUM.md','The 63-pair spectrum and courtesy review')+' is the current interpretation. The binary regression results below are retained only as diagnostics of the old labels, not as the relationship model.','',
      f"The original-only baseline classified {r0['true_positive']+r0['true_negative']}/29 documented dyads correctly ({r0['accuracy']:.1%}), compared with {p0['true_positive']+p0['true_negative']}/29 ({p0['accuracy']:.1%}) using all eventual cosponsorships. Log loss changed from {p0['log_loss']:.3f} to {r0['log_loss']:.3f}; lower is better. The requested behavior is now measured directly, but this change did not itself improve development prediction.",'',
      'These are nested member/source-excluded development results on 20 positive and 9 negative documented ties. They classify the sign of an already documented tie; they are not accuracy across all congressional dyads or calibrated probabilities of private feelings. The 120-pair v5 test remains unopened and unchanged. The new work definition is a versioned development candidate, not a silent amendment to that frozen test.','',
      '## What changed','',
      f"Across {counts['bills']:,} distinct H.R./S. bills from Congresses 116–119, {counts['original_signatures']:,} of {counts['all_valid_signatures']:,} valid cosponsorship records are original ({counts['original_signatures']/counts['all_valid_signatures']:.1%}). Of these, {counts['original_roster_signatures']:,} concern the 532-member analysis roster. {counts['bills_with_originals']:,} bills have originals; zero-original bills remain eligible opportunities. {counts['original_withdrawals']:,} later withdrawals retain their historical original-participation record and are separately identified.",'',
      'The original designation is an explicit source field. [Congress.gov API documentation](https://github.com/LibraryOfCongress/api.congress.gov/blob/main/Documentation/BillEndpoint.md) describes it separately from later cosponsorship; [CRS](https://www.congress.gov/crs-product/RS22477) explains the introduction-stage process. Original participation is evidence of initial coalition membership, not proof of shared drafting or personal friendship.','',
      'Direct propensity, reverse propensity, shared bills, coalition weighting, issue selectivity, network proximity, and the bipartisanship moderator all now use originals. Eligibility is service in the appropriate chamber on introduction day. There is no 30-day window, no title deduplication, and no exclusion merely because a bill is recent. Geography and ideology remain estimated controls, with compatibility allowed to contribute positively.','',
      f"The introduction-day rule removes {int(counts['introduced_opportunity_difference']):,} ineligible actor-to-current-sponsor bill opportunities relative to the eventual-join denominator. No additional original signatures failed introduction-day service eligibility. Shared-original counts exactly reconcile with the preserved earlier original_shared matrix.",'',
      f"Source audit: the six unchanged 116th–118th archives contain {flag['totals']['true']:,} explicit true and {flag['totals']['false']:,} explicit false fields, with no missing/invalid fields. The two 119th archives changed after extraction, so they were not substituted. Their snapshot-level flag completeness cannot be independently recertified from those updated archives; an extracted true always required XML true. The frozen normalization excluded one raw original record whose sponsorship date preceded introduction. This investigation preserves that exclusion and the same snapshot.",'',
      '## All prespecified regressions','',
      '| Specification | Correct | Positive recall | Negative recall | Balanced accuracy | Same-fit AUC | Log loss | Brier |',
      '|---|---:|---:|---:|---:|---:|---:|---:|']
    def metricrow(label,m,auc):return f"| {label} | {m['true_positive']+m['true_negative']}/29 ({m['accuracy']:.1%}) | {m['true_positive']}/20 | {m['true_negative']}/9 | {m['balanced_accuracy']:.1%} | {auc:.3f} | {m['log_loss']:.3f} | {m['brier']:.3f} |"
    lines.append(metricrow('Previous all-cosponsor baseline',p0,oldrank['R0_main_effects']['auc']))
    for k,r in results.items():lines.append(metricrow(LABELS[k],r['metrics'],rank[k]['auc']))
    lines+=['','Every declared specification is shown. The threshold remains 0.5. Always predicting positive gets 20/29 (69.0%) and identifies no negative ties. Same-fit AUC uses all 180 positive–negative comparisons, excluding both pairs’ members and connected source families and scoring each comparison from the same fitted model. Pooled AUC and every prediction are retained in model_results.json.','',
      'All models retain party/state/chamber indicators, DW-NOMINATE positions and distance, observed issue selectivity, leadership indicators, service, interview coverage and role-adjusted visibility, and the existing personality levels/similarities. Geography here means same state, not a full physical-distance model. Controls and current party/leadership measurements remain imperfect.','',
      '## Stability after removing the motivating example','',
      '| Original-work specification | Correct without Mace/Crockett | Negative recall | Log loss |','|---|---:|---:|---:|']
    for k,r in sensitivity.items():
        m=r['metrics'];lines.append(f"| {LABELS[k]} | {m['true_positive']+m['true_negative']}/28 | {m['true_negative']}/8 | {m['log_loss']:.3f} |")
    lines+=['','## Trait-specific reading','',
      'R4 allows E, A and O similarity to interact separately with ideological distance. R5 asks whether both members being low in agreeableness matters; R6 asks the analogous question for high extraversion. Main effects accompany each interaction. High extraversion is not assumed to be dominance, and low agreeableness is not assumed to make either warmth or hostility truthful.','',
      '| Model / interaction | Raw log-odds coefficient | Source-resampling 2.5%–97.5% range | Fraction positive |','|---|---:|---:|---:|']
    for k in ['R1_similarity_distance','R4_separate_traits','R5_joint_low_agreeableness','R6_joint_high_extraversion']:
        for name,e in coef[k]['effects'].items():
            q=e['stability_quantiles'];lines.append(f"| {k}: {name} | {e['raw_coefficient']:+.3f} | {q[0]:+.3f} to {q[2]:+.3f} | {e['positive_fraction']:.1%} |")
    la=coef['R5_joint_low_agreeableness']['effects']['joint_low_A_D']
    lines+=['',f"The most specific directional pattern is jointly low agreeableness: its distance interaction points toward the old negative labels in {1-la['positive_fraction']:.1%} of source resamples. However, that model's held-out log loss is {results['R5_joint_low_agreeableness']['metrics']['log_loss']:.3f}, worse than the original baseline's {r0['log_loss']:.3f}. A stable fitted direction is therefore not a demonstrated predictive improvement. The separate E/A/O similarity interactions each have resampling ranges that span zero; the broad mirror-personality hypothesis is not established.",'',
      'These are descriptive resampling ranges at the selected ridge penalty, not inferential confidence intervals. All seven models were explored on a small, previously inspected development sample; no winning model was selected for deployment. Personality/source overlap, retrospective measurement and visibility bias remain unresolved by this comparison.','',
      '## Concrete work evidence','',
      '| Documented pair | Sign | All shared bills | Shared original bills | A originally supports B / eligible bills | B originally supports A / eligible bills |','|---|---|---:|---:|---:|---:|']
    for p in pairs:
        lines.append(f"| {' / '.join(p['names'])} | {p['sign']} | {p['all_cosponsor_shared_bills']:.0f} | {p['shared_bills']:.0f} | {p['original_direct_a_to_b']:.0f}/{p['original_opportunities_a_to_b']:.0f} | {p['original_direct_b_to_a']:.0f}/{p['original_opportunities_b_to_a']:.0f} |")
    lines+=['','A and B follow the displayed order. Shared counts require both members to be original cosponsors of a third member’s bill; direct columns capture being an original cosponsor of each other’s bills. Zero cooperation never supplies a negative relationship label. '+link(OUT/'original_pair_bill_receipts.ndjson','Every qualifying bill and its public URL')+'.','',
      '## Competitive situations and personal exchanges','',
      f"The separate event audit contains {creceipt['directed_episode_records']} directed episode records across {creceipt['root_episodes']} root episodes, including two newly completed full-turn reviews. Duplicate Raskin–Cole broadcasts count as one encounter. Context coding was completed before attaching traits and original-work values; this is still one assistant’s review, not independent inter-rater validation.",'',
      '| Pair / encounter | Observable situation | What distinguishes the exchange |','|---|---|---|',
      '| Mace → Crockett | Campaign-messaging criticism followed by an address Mace perceived as belittling | Repeated personal challenge after requests for order; violent intent is disputed. Crockett’s reverse personal attack is not assumed. |',
      '| Comer → Moskowitz | Financial-accountability challenge to the committee chair | Appearance/character insults and sustained replies; financial disagreement alone does not establish personal hostility. |',
      '| Luna → Goldman | Procedural attendance dispute | Wealth/status ridicule continues after intervention; status competition is a hypothesis, not an observed motive. |',
      '| Raskin → Donalds; Frost → Mace | Procedural disagreement / appeal | Direct disagreement without an established personal attack in the selected passages. |',
      '| Durbin → Scott, 2020-06-17 | Competing police-reform proposals | Warm wording may reflect traditional Senate courtesy and coalition building. Personal closeness remains unestablished. The separate Grassley negotiation story is not assigned to Scott. |',
      '| Murphy → Bennet, 2021-03-24 | Community tragedy and shared policy advocacy | A recalled supportive call and advice provide concrete relationship content beyond a salutation. |',
      '| Raskin → Cole, 2021-01-12 | Personal bereavement alongside constitutional disagreement | Specific support and appreciation of enduring friendship. |',
      '| Calvert → McCollum; Smucker → Massie | Bill/committee acknowledgments | Routine work thanks remain a comparison category; they are not negative ties. |','',
      'The reviewed passages are supported by the [June 17 Congressional Record](https://www.congress.gov/116/crec/2020/06/17/CREC-2020-06-17-senate.pdf) and [March 24 Congressional Record](https://www.govinfo.gov/link/crec/167/s/1756). The courtesy revision distinguishes observed warm words from evidence of personal closeness. Murphy’s recalled support call adds concrete behavior; Durbin’s warm evaluation alone cannot separate Senate convention from personal regard.','',
      'The event table records roles only where the source supports them. It leaves leadership allegiance/challenge unmeasured, rather than inferring it from party labels. No episode-level event code entered these regressions: using the same confrontation to both label and predict hostility would manufacture accuracy. Future expression predictors need earlier or separately sourced exchanges and an other-colleague exposure denominator. The preserved quieter-member development strata remain the collection frame; these selected cases do not remedy coverage bias by themselves.','',
      link(OUT/'EXCHANGES.md','Source-linked event profiles')+' · '+link(OUT/'exchange_context.ndjson','Machine-readable context, personality and original-work table')+'.','',
      '## Math and execution','',
      'For bill b, O_ib = 1 for a valid recorded original cosponsor; E_ib = 1 for a nonsponsor serving in that chamber on introduction day. Then:',
      '',r'\[P^{orig}_{i\to j}=\frac{\sum_b O_{ib}\mathbf1(s_b=j)}{\sum_b E_{ib}\mathbf1(s_b=j)},\qquad H^{orig}_{ij}=\sum_b O_{ib}O_{jb}.\]','',
      r'\[J^{orig}_{ij}=\frac{\sum_b w_b O_{ib}O_{jb}}{\sum_b w_b(E_{ib}O_{jb}+E_{jb}O_{ib}-O_{ib}O_{jb})},\quad w_b=\frac1{\max(1,\sum_m O_{mb}-1)}.\]','',
      'A zero opportunity denominator is missing. Coalition size includes original cosponsors outside today’s roster. Network proximity is cosine similarity of J rows excluding the focal endpoints. Bipartisanship B uses the mean of each endpoint’s cross-party versus same-party original propensities, excluding the partner from both groups; Independent members are not silently recoded.','',
      r'\[S_t=e^{-|z_{it}-z_{jt}|},\quad D=|DW1_i-DW1_j|,\quad L_A=\sigma(-A_i)\sigma(-A_j),\quad H_E=\sigma(E_i)\sigma(E_j).\]','',
      'The ridge logistic objective is weighted mean negative log likelihood plus λ/2 times the squared standardized coefficients, excluding the intercept. Each dyad has weight one across its observed directions. Mean imputation, missingness indicators and standardization use training data only. λ is selected from {0.03, 0.1, 0.3, 1, 3} using nested member/source exclusions. Coefficients and interaction signs are estimated, not imposed.','',
      'The run receipt hashes inputs and code, and verifies the existing frozen test. '+link(OUT/'PLAN.md','Prefit specification')+' · '+link(OUT/'run_receipt.json','Run receipt')+' · '+link(OUT/'model_results.json','All predictions')+' · '+link(OUT/'gain_stability.json','Paired prediction resampling')+'.','']
    (OUT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    extra=['# Exchange context profiles','',
      'These source-linked descriptions are development evidence. The initial event decisions describe observed content; the subsequent graded courtesy review below controls the affinity interpretation. Traits and original work are current retrospective measurements. Missing information remains missing. None of these event codes was used to predict its own label.','']
    for r in context:
        a,b=r['actor'],r['target'];extra+=[f"## {r['actor_name']} → {r['target_name']} — {r['date']}",'',
            f"**Initial content decision:** {r['decision']}. **Context:** {r['context']}. **Act:** {r['personal_act']}.",'',r['interpretation'],'',
            f"**Current graded review:** affinity evidence {graded[r['id']]['affinity_grade'] if graded[r['id']]['affinity_grade'] is not None else 'unestablished'}; tension evidence {graded[r['id']]['tension_grade'] if graded[r['id']]['tension_grade'] is not None else 'unestablished'}. Reason: {graded[r['id']]['grading_reason']}. Observed warmth is not itself proof of closeness.",'',
            f"Shared original bills: {r['original_shared_bills']:.0f}; original support toward each other: {r['original_direct_a_to_b']:.0f} / {r['original_direct_b_to_a']:.0f}. Ideological distance: {fmt(r['ideology_distance'])}. EAO similarity: {fmt(r['EAO_similarity'])}.",'',
            '| Endpoint | O | C | E | A | N |','|---|---:|---:|---:|---:|---:|']
        for who,name in [(a,r['actor_name']),(b,r['target_name'])]:extra.append('| '+name+' | '+' | '.join(fmt(r['traits'][who].get(t)) for t in 'OCEAN')+' |')
        extra+=['',f"Source locator: {r['source_locator']}. Root episode: {r['episode_id']}.",'',
                ' '.join(f'[Public source {j+1}]({url})' for j,url in enumerate(r['source_urls'])) or 'Full attributed local source turn retained in the v5 development review packets.','']
    (OUT/'EXCHANGES.md').write_text('\n'.join(extra),encoding='utf-8')
    files=['REPORT.md','EXCHANGES.md','original_pair_bill_receipts.ndjson']
    save(OUT/'report_receipt.json',dict(created_utc=datetime.now(timezone.utc).isoformat(),
        report_code_sha256=digest(Path(__file__)),outputs={f:digest(OUT/f) for f in files},
        bill_receipt_pairs=len(receipts),all_declared_models_reported=True))
    print('Reports and complete bill receipts written',flush=True)


if __name__=='__main__':main()
