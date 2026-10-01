"""Manual v6 intensity assessments, independent of old numeric evidence grades.

Each decision cites its existing source/context review. These are one assistant's
development annotations, not independent human consensus or verified private
feelings. The opposite dimension is intentionally left unassessable.
"""
from collections import defaultdict

# id: dimension, grade, plausible lower/upper grade, rationale
DECISIONS = {
 '90f03416cc5a4bbf3632': ('affinity',4,3,4,'Oldest/good personal friend, explained through a deeply valued condolence call to his mother.'),
 '90cd69ba983466502e47': ('affinity',3,2,4,'Affection toward Curtis and spouse and longstanding personal acquaintance; maiden-speech ceremony limits certainty.'),
 'df929387644162fa212f': ('affinity',2,1,3,'Explicit personal friendship beyond a passing salutation, without a concrete intimate relationship account.'),
 '5c41003a37ab9ecc9441': ('affinity',2,1,3,'Affection toward the family and evenings together support liking; dyadic closeness is less clear than affection for the daughter.'),
 'anchor-britt_fetterman_nbc_202604-0': ('affinity',4,3,4,'Personal trust and family conversations describe a particularly close bond; joint media context retained.'),
 'anchor-britt_fetterman_nbc_202604-1': ('affinity',4,3,4,'Fetterman explains the personal importance of Britt visiting during hospitalization.'),
 'anchor-britt_louisville_20240402-0': ('affinity',3,2,4,'Britt identifies Fetterman among her greatest Senate friends; public bipartisanship occasion.'),
 'anchor-britt_louisville_20240402-1': ('affinity',3,2,4,'Britt identifies Welch among her greatest Senate friends; public bipartisanship occasion.'),
 'anchor-britt_louisville_20240402-2': ('affinity',3,2,4,'Britt identifies Booker among her greatest Senate friends; public bipartisanship occasion.'),
 'anchor-booker_scott_cbs_20160912-0': ('affinity',3,2,4,'Explicit media account of a personal friendship across disagreement.'),
 'anchor-lee_cruz_radio_20160629-0': ('affinity',4,3,4,'Best-friend description denotes intensity; political defense is a possible additional motive.'),
 'anchor-collins_murkowski_fox_20181221-0': ('affinity',4,3,4,'Describes a deep personal friendship surviving a consequential disagreement.'),
 'anchor-coons_lankford_rns_20190130-0': ('affinity',3,2,4,'Personal faith conversations and increased closeness, beyond a legislative acknowledgment.'),
 'anchor-cole_mcgovern_20190515-0': ('affinity',4,3,4,'Says nobody in the House is a better personal friend; floor context retained.'),
 'anchor-mcgovern_cole_20200423-0': ('affinity',2,1,3,'Years-long friendship/work acknowledgment supports liking, without establishing equivalent superlative intensity in this direction.'),
 'anchor-burchett_cspan_20240517-0': ('affinity',2,1,3,'Explicit friendship and social compatibility with Goldman despite political opposition.'),
 'anchor-burchett_cspan_20240517-1': ('affinity',2,1,3,'Explicit friendship and social compatibility with Moskowitz despite political opposition.'),
 'anchor-aoc_cruz_20210128-0': ('friction',3,2,4,'Explicit targeted refusal to work with Cruz while welcoming other Republicans; strong aversion with a political trigger.'),
 'anchor-aoc_fetterman_20240517-0': ('friction',2,1,3,'Direct personal rebuke identifying Fetterman with bullying; no claim of persistent intense hatred.'),
 'anchor-boebert_omar_202111-0': ('friction',3,2,4,'Severe personal terrorism insinuation and confrontational response; degree applies to this episode.'),
 'anchor-boebert_omar_202111-1': ('friction',3,2,4,'Reports ending the confrontational call when the attack continued; strong aversion in the exchange.'),
 'anchor-gosar_aoc_video_20211107-0': ('friction',3,2,4,'Severe personalized violent imagery supports strong public friction, without proving physical intent or private emotional intensity.'),
 'anchor-vanorden_roy_20240418-0': ('friction',2,1,3,'Direct bully characterization and targeted pushback with a political trigger.'),
 'anchor-comer_jeffries_20251120-0': ('friction',2,1,3,'Direct character accusation and described name calling; stronger than policy disagreement.'),
 'anchor-cruz_mcconnell_20150724-0': ('friction',2,1,3,'Targeted accusation of deceiving colleagues about a promise; a dated personal-trust conflict, not proven lasting dislike.'),
 'history-rollcall_civility_20171204-0': ('affinity',3,2,4,'Lifelong appreciation of the friendship; prompted media question affects certainty, not the meaning of the expressed degree.'),
 'history-rollcall_civility_20171204-1': ('affinity',3,2,4,'Explicit close-friend description of Panetta.'),
 'history-rollcall_civility_20171204-2': ('affinity',2,1,3,'Names Dunn as a cross-party friend; little independent detail about intimacy.'),
 'history-rollcall_civility_20171204-3': ('affinity',2,1,3,'Friend nomination with a softball account; personal liking supported, exceptional closeness unestablished.'),
 'history-rollcall_civility_20171204-4': ('affinity',2,1,3,'Specific friendship nomination, without a more intense relationship account.'),
 'history-rollcall_civility_20171204-5': ('affinity',1,1,2,'Enjoyment of collaboration and contemplated visits support mild personal regard, not an intimate friendship.'),
 'history-rollcall_civility_20171204-6': ('affinity',1,1,2,'Enjoyment of collaboration supports mild regard; no stronger personal bond established.'),
 'history-rollcall_civility_20171204-7': ('affinity',2,1,3,'Specific friend nomination and personal approval.'),
 'history-rollcall_civility_20171204-8': ('affinity',2,1,3,'Specific cross-party friend nomination.'),
 'history-sanders_warren_20191012-0': ('affinity',3,2,4,'Describes a decades-long friendship while discussing their differences.'),
 'history-sanders_warren_20190728-0': ('affinity',2,1,3,'Affirms friendship and appreciation of joint work without a strong intimacy claim.'),
 'history-durbin_duckworth_20240227-0': ('affinity',4,3,4,'Being entrusted with private family news and explicit personal friendship support unusually close regard.'),
 'history-roy_massie_20240925-0': ('affinity',2,1,3,'Direct friendship affirmation during disagreement; public political context remains relevant.'),
 'history-omar_aoc_personal_defense_20200723-0': ('affinity',2,1,3,'Personal defense of a named friend with family reference; not an automatic inference of closest friendship.'),
 'luna_to_goldman_status_escalation': ('friction',3,2,4,'Personally directed wealth epithet and escalating exchange; strong friction at that hearing.'),
 'comer_to_moskowitz_personal_escalation': ('friction',3,2,4,'Personal appearance ridicule and direct accusations persist through an exchange; no extrapolation to enduring hatred.'),
 'mace_to_crockett_confrontation': ('friction',3,2,4,'Escalating personal confrontation with a challenge to continue outside; physical intent remains disputed.'),
 'comer_to_goldman_status_jab': ('friction',1,1,2,'An isolated personal epithet, without a sustained confrontation with this target.'),
 'review_215949': ('affinity',3,2,4,'Treasures an enduring friendship in response to specific bereavement support.'),
 'review_65329': ('affinity',1,1,2,'Personal appreciation of collegiality in a tribute; the evidence supports mild regard more clearly than private closeness.'),
 'new_review_60458': ('affinity',2,1,3,'Remembers a supportive advice call; friendship appreciation accompanies shared policy advocacy.'),
}


def build_annotations(events, context, original):
    """Retain provenance and unresolved cases; collapse duplicate source records."""
    metadata = {r['evidence_id']: r for r in original}
    metadata.update({r['id']: r for r in context})
    seen_ids = {e['id'] for e in events}
    if not set(DECISIONS).issubset(seen_ids):
        raise ValueError('Manual decision refers to absent evidence')
    groups = defaultdict(list)
    for e in events:
        groups[(e['actor'], e['target'], e['date'], e['episode_id'])].append(e)
    out = []
    for (actor, target, day, episode), es in sorted(groups.items()):
        votes = [DECISIONS[e['id']] for e in es if e['id'] in DECISIONS]
        row = dict(id='v6:'+es[0]['id'], actor=actor, target=target, pair=sorted([actor,target]), date=day,
                   episode_id=episode, evidence_ids=[e['id'] for e in es], affinity=None, friction=None,
                   affinity_range=None, friction_range=None, neutral_evidence=False,
                   families=sorted({episode} | {metadata[e['id']].get('source_family', episode) for e in es}),
                   source_urls=sorted({u for e in es for u in e.get('source_urls', [])}),
                   assessment_basis='single_assistant_rereview_of_existing_context_reviews_and_available_text',
                   inference_scope='dated_public_evidence_proxy; not a measurement of enduring private feelings',
                   confidence=None, rationale='; '.join(e.get('note') or e.get('grading_reason','') for e in es),
                   date_basis=metadata[es[0]['id']].get('date_basis','existing_record_date; retrospective event dates may be unknown'),
                   venue=metadata[es[0]['id']].get('venue',metadata[es[0]['id']].get('source','media_or_official_web')),
                   purpose=metadata[es[0]['id']].get('context','context_preserved_in_source_review'),
                   courtesy_reviewed=True, closeness_and_trust_note=None)
        for dimension, grade, lo, hi, why in votes:
            if row[dimension] is not None and row[dimension] != grade:
                raise ValueError('Conflicting grades inside one event; needs adjudication')
            row[dimension], row[dimension+'_range'] = grade, [lo, hi]
            row['rationale'] = why
            row['confidence'] = 'provisional_single_reviewer'
        out.append(row)
    return out
