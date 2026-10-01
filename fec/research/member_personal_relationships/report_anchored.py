"""Generate reviewable reports directly from the fitted pilot artifacts."""
from collections import defaultdict
from pathlib import Path
from .data import ROOT,read_json,write_json,digest
from .run import read_lines
from .run_anchored import HERE,BASE,OUT,CONTROL_NAMES,FEATURE_NAMES


def link(path): return f'[{path.name}](<{path.resolve().as_posix()}>)'
def pct(x): return f'{x:.1%}'
def f(x): return 'unavailable' if x is None else f'{x:.3f}'
def main():
    result=read_json(OUT/'results.json');members=read_json(BASE/'members.json')
    rows=read_lines(OUT/'relationships.ndjson');events=read_lines(OUT/'anchor_events.ndjson')
    cases=read_json(OUT/'anchor_cases.json');catalog=read_json(HERE/'anchor_catalog.json')
    predictions=read_lines(OUT/'heldout_sign_predictions.ndjson')
    name=lambda a:members[a]['name']
    groups=defaultdict(list)
    for e in events: groups[(e['actor'],e['target'])].append(e)
    evidence=['# Source-reviewed relationship anchors — second pilot','',
        'These are dated, assistant-reviewed working labels. Friendship declarations are evidence of affinity; a personal attack is evidence of antagonism at that time. The latter does not automatically establish enduring private dislike. Shared incentives and public-performance incentives remain possible even when a personal relationship is explicit.','',
        'Each direction is coded separately. A public claim of mutual friendship does not manufacture a reciprocal statement from the other member. Dates refer to observations or publication proxies; old statements are not silently renewed.','']
    for (a,b),ee in sorted(groups.items(),key=lambda kv:(kv[1][0]['sign'],name(kv[0][0]),name(kv[0][1]))):
        evidence += [f'## {name(a)} → {name(b)}','']
        for e in sorted(ee,key=lambda e:e['event_date']):
            urls=e['source_urls'];links='; '.join(f'[Source {i+1}]({u})' for i,u in enumerate(urls))
            evidence += [f"**{e['sign']} · {e['event_date']} · {e['category']}**. {e.get('review_note','')}",
                f"{links}. Attribution: {e['attribution']}. Episode: `{e['episode_id']}`."]
            if e.get('alternative_explanation'): evidence.append('Context and competing explanation: '+e['alternative_explanation'])
            evidence += ['']
    evidence += ['## Explicit historical feud outside the current roster','']
    for e in catalog['historical_examples_outside_current_roster']:
        evidence += [f"**{e['actor']} → {e['target']} ({e['event_date']})**. {e['note']} [Original interview]({e['url']}).",'']
    (OUT/'ANCHOR_REVIEW.md').write_text('\n'.join(evidence)+'\n',encoding='utf-8')
    inferred=sorted([r for r in rows if r['affinity_status']=='inferred_friendship_candidate'],key=lambda r:-r['affinity_score'])
    candidates=['# Inferred friendship candidates — second pilot','',
        'The model was trained on explicit affinity anchors versus matched, unlabeled pairs. Scores are fitted ranking contributions beyond the context expectation, not probabilities. These candidates have no accepted direct friendship label in the anchor ledger. Reciprocal rows remain distinct. This is a bounded panel of 2,018 directions, not a ranking of every possible congressional relationship.','',
        'Promotion requires a positive fitted score in both the main model and personality sensitivity model, top-50 rank in the scored panel, and at least two positive channels among distinctive work, matched personality similarity, and personal-network proximity. This gate is exploratory; its precision has not been established.','',
        '| Direction | Different party / state | DW1 distance | Matched work: observed / expected (opportunities) | Personality excess | Personal intermediaries | Fitted score |',
        '|---|---|---:|---|---:|---|---:|']
    for r in inferred:
        candidates.append(f"| {r['actor_name']} → {r['target_name']} | {'yes' if not r['same_party'] else 'no'} / {'yes' if not r['same_state'] else 'no'} | {f(r['nominate_distance'])} | {r['work_observed']} / {r['work_expected']:.2f} ({r['work_opportunities']}) | {f(r['personality_similarity_excess'])} | {', '.join(name(a) for a in r['positive_intermediaries']) or 'none observed'} | {r['affinity_score']:.3f} |")
    candidates += ['', '## Antagonism output','',
        'Eleven directions across nine pairs have source-reviewed personal antagonism. No new pair clears the learned-evidence gate for inferred antagonism. The raw ranking suggested Gosar–Fetterman, Ocasio-Cortez–McConnell, and Gosar–Cruz, but these were blocked: the model had no hostile anchor exemplifying the proposed two-step motif. Low cooperation and an unlearned enemy-of-enemy pattern cannot establish dislike.','',
        '## Post-ranking source checks','',
        'After the initial ranking was frozen, targeted searches examined Panetta–Wilson, Fitzpatrick–Tonko, Davis–Nunn, Britt–Scott, Gillibrand–Britt, King–Moran and Durbin–Grassley. The first pass did not establish an additional personal tie under the anchor standard. Several results concerned shared legislation, international friendship, third parties, or routine colleague language. Search non-confirmation is not a negative label and is not counted as an error or as precision=0. No search result was fed back into this benchmark as a new training label.','',
        'Shared military service, caucus membership, issue specialization and coordinated bill introduction remain plausible explanations for several high-ranked pairs. Committee overlap is controlled at the relationship stage; broad policy-area matching alone cannot eliminate these narrower incentives.']
    (OUT/'INFERRED_RELATIONSHIPS.md').write_text('\n'.join(candidates)+'\n',encoding='utf-8')
    validation=['# Held-out relationship tests — second pilot','',
        'A row is an unordered pair. All direct source episodes for that pair, both directions, and the transitive component of other pairs sharing those source families are removed before graph features are constructed. Every training anchor also has its own direct pair and focal source family hidden from its feature row. Imputers and scalers use only the training fold.','',
        'Sign scores below are conditional classifier outputs within this selected positive/negative anchor set. They are not estimates of whether arbitrary members are friends.','',
        '| Pair | Documented class | Context score | Indirect score | Correct at 0.5? |',
        '|---|---|---:|---:|---|']
    for p in predictions:
        correct=(p['indirect_strict']>=.5)==(p['sign']=='positive')
        validation.append(f"| {' / '.join(name(a) for a in p['pair'])} | {p['sign']} | {p['context_baseline']:.3f} | {p['indirect_strict']:.3f} | {'yes' if correct else 'no'} |")
    validation += ['', '## Recovery among matched, unlabeled alternatives','',
        'For each eligible held-out direction the model ranks the known anchor against up to ten alternatives with the same actor, target chamber, party relation, same-state relation, DW1-distance bin and target leadership status. Test alternatives are excluded from PU training. Unknown alternatives can contain true relationships: this is anchor recovery, not friendship precision. All tied scores receive the expected rank under random tie breaking. Reciprocal directions are averaged within pair.','',
        '| Target | Evaluated pairs | Main mean percentile | With personality | Random expectation |',
        '|---|---:|---:|---:|---:|']
    for sign,v in result['retrieval'].items():
        validation.append(f"| {sign} | {v['pairs']} | {pct(v['mean_percentile'])} | {pct(v['profile_mean_percentile'])} | 50.0% |")
    validation += ['', 'Three positive pairs have too few matched alternatives and are excluded from recovery metrics. The absence of a comparator is retained rather than turning into extra relationship evidence.','',
        'The stronger member-disjoint test removes all source labels and graph edges involving either test member, including linked source families. Its main accuracy is 11/23 and AUROC 0.524: evidence of useful generalization to members absent from the anchor graph is not established.','',
        'The 23 pairs were intentionally selected from explicit public relationships, not sampled randomly. Repeated members, shared source families, selected public visibility and a small sample make naive independence-based confidence claims inappropriate. No significance claim, calibrated probability, population accuracy or causal interpretation is made.']
    (OUT/'VALIDATION.md').write_text('\n'.join(validation)+'\n',encoding='utf-8')
    doc=['# Congressional personal relationships — fitted pilot results','',
        '**The second pilot is built, fitted and tested.** It expands four provisional personal accounts into 23 source-reviewed relationship pairs: 14 affinity and nine antagonism pairs, represented by 27 directed ties and 28 evidence records in 22 deduplicated source families. Ten affinity pairs cross party lines; three antagonism pairs are within the same party. A separately documented Greene–Boebert feud demonstrates a personal conflict within a similar ideological camp, but is outside the current-member benchmark.','',
        'The pilot scores 2,018 directions. It exports 20 inferred friendship candidates alongside the documented ties. The candidates remain hypotheses; they are not relabeled as established friendships.','',
        '## Test results','',
        '| Test / model | Correct sign | Balanced accuracy | AUROC |',
        '|---|---:|---:|---:|']
    labels={'context_baseline':'Geography / ideology / institutional context','indirect_strict':'Context + distinctive work + personal graph',
            'no_network':'Without paths and motifs; degree controls retained','no_work':'Without work; degree controls retained',
            'personality_sensitivity':'Personality sensitivity (not independent validation)'}
    for k,v in result['sign_evaluation'].items():
        doc.append(f"| {labels[k]} | {round(v['accuracy']*v['n'])}/{v['n']} ({pct(v['accuracy'])}) | {pct(v['balanced_accuracy'])} | {v['auc']:.3f} |")
    doc += ['',
        '**Interpretation:** hiding a pair’s direct evidence gives 16/23 correct signs versus 12/23 for the context baseline. An always-affinity classifier would get 14/23 because of class imbalance. More demanding member-disjoint testing falls to 11/23 (baseline 10/23). The current improvement mainly relies on information around members already represented in the anchor graph; it does not establish broad cold-start generalization.','',
        'Finding a known friendship among comparable unlabeled pairs is harder: mean held-out percentile is 54.2%, against 50% under random ranking. Hostile-anchor recovery is 64.4%. These are not precision or recall over all congressional relationships.','',
        '## What the evidence establishes','',
        '- Britt and Fetterman give explicit accounts of personal friendship, trust and support. The two Senate press releases reproduce one NBC interview and count once.',
        '- Burchett’s account of Cohen contacting his family after his father died provides personal evidence beyond their shared Tennessee history. Burchett also explicitly identifies Goldman and Moskowitz as friends while discussing political disagreement.',
        '- AOC’s rejection of Cruz despite agreement on the Robinhood issue is selective personal avoidance, stronger than inferring dislike from ideological distance.',
        '- Mace → Crockett and Comer → Moskowitz are directly observed hostile exchanges. They establish episodes of personal antagonism; durable dislike needs recurrence or an explicit continuing-feud account.',
        '- Greene’s 2023 interview acknowledges a continuing feud with Boebert and rejects reconciliation. Their shared party and ideological camp clearly do not imply friendship.','',
        'Every source, direction, date and competing explanation is in '+link(OUT/'ANCHOR_REVIEW.md')+'.','',
        '## New candidates to examine','',
        '| Candidate direction | Matched 30-day cosponsorships | Ideological / geographical distinction |',
        '|---|---|---|',
        '| Jimmy Panetta → Joe Wilson | 12 observed, 0.94 expected, 30 opportunities | Different parties and states; DW1 distance 0.812 |',
        '| Brian Fitzpatrick → Paul Tonko | 9 observed, 1.93 expected, 17 opportunities | Different parties and states; DW1 distance 0.557 |',
        '| Donald Davis → Zachary Nunn | 12 observed, 2.38 expected, 48 opportunities | Different parties and states; DW1 distance 0.536 |','',
        'All three also have positive personality similarity relative to matched peers. This is suggestive evidence after conditioning on broad incentives, not proof that narrower interests or coordinated policy work are absent. All 20 directed candidates, including reverse directions where eligible, appear in '+link(OUT/'INFERRED_RELATIONSHIPS.md')+'.','',
        '## How inference works','',
        '1. **Start with source-reviewed anchors.** Record the actual speaker, target, sign, relationship category, date, source family and alternative explanation. Retrieved text is never itself a label. A wider read-only scan examined 238,027 corpus turns and retrieved 1,636 candidate passages; most remain unreviewed. Common-word surnames and references to third parties are known retrieval traps.',
        '2. **Condition on observable incentives.** Controls include party relation, same state, both DW-NOMINATE dimensions, chamber, leadership, tenure difference and current committee overlap. Directed positive/negative degree counts serve as additional exposure/popularity controls. Fine geographic distance, caucus/faction membership, shared military careers, district interests and bill-level bargaining remain unmeasured.',
        '3. **Measure distinctive work.** Reuse the frozen 119th-Congress bill panel with complete 30-day exposure windows. Compare each actor’s support with their support of other sponsors in the same party/state/ideological/status stratum and policy area. Remove the focal sponsor from its expectation; use seven-day support as a sensitivity. Shared broad interests are controlled imperfectly, not declared eliminated.',
        '4. **Use personal-network structure.** Compute directed positive paths, resource allocation and all 16 directed signed two-step motifs after masking held-out evidence. Do not force enemy-of-enemy into friendship. No predicted edge feeds back into the graph. This small graph has no useful anchor examples of positive closure after masking; paths/motifs add no held-out sign improvement yet. Degree information accounts for much of the apparent network contribution.',
        '5. **Fit rather than assign weights.** Regularized logistic regression learns conditional polarity among documented ties. Separate positive-unlabeled rankers learn affinity-anchor and antagonism-anchor resemblance against fixed-actor matched unknowns. Each first fits feature expectations from context, then learns from the residuals; published scores omit the selection intercept and contain no direct geography/party bonus. Unknowns are labeled as unselected during PU training, never as confirmed nonfriends or enemies.',
        '6. **Keep personality as a measured sensitivity.** Extraversion of the actor, agreeableness of the target, and matched E/A/O similarity follow the supplied Selfhout study as hypotheses. The local traits are public-text observer estimates, not psychometric self-reports. Their input text was not rebuilt to exclude all anchor passages, so the 19/23 sign result is not an independent validation gain. Adding personality actually worsens friendship-anchor recovery to 46.2%, though it improves hostile-anchor recovery. Similar personality is not a sufficient friendship rule.',
        '7. **Test hidden relationships and new members separately.** Pair/source-family holdout, member-disjoint holdout, matched recovery, channel ablation, evidence deduplication, and direction checks are implemented. An inferred antagonist must have positive contribution from a signed-network pattern actually observed in hostile training anchors. That gate blocks three misleading raw candidates in this run.','',
        'All measurements are **retrospective**: historical relationship statements are compared with a frozen 2026 roster and current behavioral/context features. Dates remain visible; this does not show that a 2016 friendship survives today or that a model predicted it in 2016.','',
        'The cited adolescent and online-network papers motivate features. Their reported coefficients or accuracies are not transferred into congressional probabilities. Shared geography, ideology, status and interests can create opportunities for real friendship; residualization helps prioritize relationships beyond those measured factors, but does not identify an incentive-free private mental state.','',
        '## Deliverables and reproducibility','',
        '- '+link(OUT/'ANCHOR_REVIEW.md')+' — every accepted direction with sources and qualifications.',
        '- '+link(OUT/'INFERRED_RELATIONSHIPS.md')+' — all inferred candidates and post-ranking search outcomes.',
        '- '+link(OUT/'VALIDATION.md')+' — individual held-out predictions and the harder tests.',
        '- '+link(OUT/'relationships.ndjson')+' and '+link(OUT/'fitted_models.json')+' — machine-readable output and learned parameters.',
        '- '+link(OUT/'TEST_RESULTS.txt')+' and '+link(OUT/'verification_receipt.json')+' — software checks and deterministic rebuild receipt.',
        '- '+link(HERE/'run_anchored.py')+' — executable pipeline; '+link(HERE/'anchor_catalog.json')+' — editable seed evidence.','',
        'Run from the workspace with `python -m fec.research.member_personal_relationships.verify_anchored`. The pipeline reads frozen local inputs and writes only to the isolated research output folder. No production network has been updated.','',
        'The next substantive expansion is more personally specific anchors around the same members, including repeated same-party feuds and nonpolitical social ties, plus faction/caucus and finer geographic controls. That would test whether actual network closure and personal similarity recover friendships after the political opportunity structure is accounted for. The current artifacts make that next test concrete.']
    (OUT/'REPORT.md').write_text('\n'.join(doc)+'\n',encoding='utf-8')
    write_json(OUT/'report_receipt.json',{'reports':{p.name:digest(p) for p in OUT.glob('*.md')},
        'results_sha256':digest(OUT/'results.json'),'reporter_sha256':digest(Path(__file__))})
    print('Wrote REPORT.md, ANCHOR_REVIEW.md, INFERRED_RELATIONSHIPS.md, VALIDATION.md')


if __name__=='__main__': main()
