"""Manual disposition of all 23 cue-independent development candidates."""
from .data import write_ndjson,digest
from .run_history import read_rows
from .regression import save
from .run_chamber_degrees import OUT

REVIEWS={
 117530:('work_context','Own family caregiving experience motivates work with Bennet; it is not an account of Bennet providing personal support.'),
 101362:('date_needs_verification','Admiration for policy leadership and a Senate campaign announcement; recorded December 2024 date conflicts with announcing a run for the seat. Preserve raw date and require original verification.'),
 244305:('work_context','Describes a joint Navy report with Cotton, without a personal relationship account.'),
 101496:('date_needs_verification','Defense of the proposed committee role for Banks; discussion appears contemporaneous with a past committee. Original interview date needs verification.'),
 101493:('date_needs_verification','Defends seating Banks on the January 6 committee and discusses its hearings; original interview date needs verification.'),
 174600:('ritual_or_work_courtesy','Gratitude for Britt and Budd bringing legislation forward; the personal tragedy concerns Laken Riley, not this dyad.'),
 93443:('work_context','Describes legislation introduced by Jeffries and DeLauro; no personal account.'),
 171062:('page_chrome_contamination','Only the initial thank-you is an utterance; Jeffries appears in unrelated web-page story links, not in Crow\'s speech.'),
 14484:('collective_political_defense','Defends the patriotism of Crow and other combat veterans in a legislative dispute; does not establish private affection or its absence.'),
 70108:('campaign_roster','Gallego appears among a list of party candidates; praise concerns electoral support.'),
 142323:('work_context','Kaine appears among co-introducers of the noncompete bill; policy common ground is not a private relationship assessment.'),
 112781:('speaker_and_historical_identity_contamination','Lankford\'s short opening is followed by multiple other speakers. John Kennedy is historical footage of the future president, not the current Louisiana senator.'),
 74537:('political_legacy_assessment','Murphy praises particular McConnell votes and criticizes his impeachment decision. Mixed political evaluation does not establish mixed personal affection/aversion.'),
 111046:('policy_position_reference','McConnell appears among leaders opposing default; discussion chiefly criticizes McCarthy\'s position.'),
 309416:('policy_disagreement','Blames pandemic-package limitations on McConnell and Trump; distrust is expressed toward Congress as an institution, not a private dyadic relationship.'),
 57898:('policy_disagreement','Criticism concerns pandemic relief and institutional resistance, without a separate personal relationship account.'),
 130233:('work_context','Names Moran as partner on solar manufacturing legislation; no personal warmth or aversion claim.'),
 109681:('campaign_endorsement','Expresses electoral support for Scott, without describing personal affection or intimacy.'),
 109680:('campaign_endorsement','Expresses electoral support for Scott; same interview as the other Rounds turn, not an independent relationship episode.'),
 172879:('ceremonial_welcome','Welcome to incoming senators with praise of their qualifications; no concrete private relationship account.'),
 231573:('mixed_speaker_contamination','Schumer\'s appeal is to the attorney general; Schiff appears in an appended reporter transition, not in Schumer\'s attributed utterance.'),
 179682:('embedded_name_list','Shaheen appears in a list of past amendment supporters; the direct exchange is with a different senator.'),
 60423:('embedded_quoted_letter','Shaheen is a signatory on an embedded historical letter; no direct personal relationship statement about her.'),
}


def main():
    rows=read_rows(OUT/'routine_encounter_candidates.ndjson')
    if {r['source_rowid'] for r in rows}!=set(REVIEWS):raise ValueError('Review packet changed')
    reviewed=[]
    for r in rows:
        status,note=REVIEWS[r['source_rowid']]
        reviewed.append(dict(source_rowid=r['source_rowid'],pair=r['pair'],names=r['names'],date=r['date'],
            source_family=r['source_family'],source_hash=r['source_hash'],review_status='single_assistant_full_packet_review',
            disposition=status,rationale=note,affinity=None,friction=None,neutral_evidence=False,
            use_as_relationship_label=False,use_as_representative_speaker_denominator=False,
            original_source_reverified=False,model_values_shown_during_review=False,
            note='Reviews completed after the primary model fit; not included in that fit or reported as a new test set.'))
    write_ndjson(OUT/'routine_reviewed.ndjson',reviewed)
    save(OUT/'routine_review_receipt.json',dict(candidates_sha256=digest(OUT/'routine_encounter_candidates.ndjson'),
        code_sha256=digest(__file__),reviewed_sha256=digest(OUT/'routine_reviewed.ndjson'),reviewed_records=len(reviewed),
        supported_neutral_labels=0,relationship_labels_added_to_fit=0,all_development=True,
        critical_source_findings={'page_chrome':1,'mixed_or_wrong_historical_speaker':2,'dates_needing_verification':3}))


if __name__=='__main__':main()
