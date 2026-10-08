# Plain-language member profile regeneration — September 4, 2026

## Result

All 533 roster members have three-paragraph profiles of 205–243 words. The profile corpus has been activated in `member_narratives_v2.json`, retaining that filename for consumer compatibility but using the explicit `member-narratives-v3-descriptive` schema.

The export is [MEMBER_PROFILES.md](descriptive_profiles_20260904/MEMBER_PROFILES.md). The machine-readable export and validation receipt are in the same folder. Earlier active artifacts were preserved under `descriptive_profiles_20260904/previous_active/`.

## What changed

- Plain-language public record, public communication, and context/evidence sections replace contradictory personality shorthand and individualized meeting playbooks in the profile summary.
- Four editorial profiles describe specific stored interview excerpts: Steve Scalise, Mike Johnson, Alex Padilla, and Maxine Waters.
- Scalise's football example is explicitly secondhand, with unknown date and frequency. It contributes no verified interview evidence.
- Nineteen self-contained public-account quotations were checked against their retained source excerpts. Other generated personal claims were excluded rather than silently repeated.
- Remaining profiles use reproducible, evidence-scoped descriptions of legislative measures and available transcript/audio coverage. Missing information remains explicit.
- Comparison language refers to the covered sample; pooled ranks of standardized measures are not presented as raw chamber-specific activity counts.
- Source hashes, exact roster, word counts, and exclusion of old playbooks are enforced at publication. The receipt describes deterministic checks, not a new independent human or model semantic review.

## Evidence limits

This regeneration made zero API calls and performed no new audio acquisition or review. Only four members currently have stored long-form response excerpts (nine excerpts overall). The archive's accepted short clips and attributed transcript passages do not establish fully reviewed long-form interviews for every member. Old "complete response" labels were not treated as renewed verification of answer boundaries.

Recurring public communication patterns require the same observable behavior in two independently produced interviews in different settings. Single-source observations remain provisional. Leaders' baseline observations must use verified pre-current-role recordings; later material remains role-conditioned. Public recordings do not establish private-meeting preferences or what persuades a particular member.

The evidence ledger was rebuilt because its basis hash was stale. The refresh changed none of the speech records or the three legislative comparison fields used by this generator.

## Verification and reproducibility

- 533 of 533 profiles; every body is 200–250 words (actual range 205–243).
- 98 focused tests passed, including publication, reproducibility, negative controls, evidence boundaries, and the preceding audio-methodology fixes.
- No profile row carries a legacy `meeting_playbook`; recurring-audio authority is false for every row.
- Reproduce with `python -m fec.members.regenerate_descriptive_profiles`; add `--activate` to back up and replace the active corpus.
- Full member-desk rebuild completed successfully, followed by the combined `Moneyball.html` build. No pillar-weight or other engine validation gate was relaxed.
- All 533 rendered profile bodies match the active corpus exactly, with the descriptive format and no old playbook payloads. Three final editorial revisions initially missed the first build's snapshot; a fresh build resolved the mismatch.
- The final rendered-desk audit passed all 15 checks, including script execution, deferred profile loading, roster alignment, and split-versus-monolithic equivalence.
