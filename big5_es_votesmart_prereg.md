# ES external corroboration — Vote Smart PCT respond (the recorded sole remaining ES path)

STATUS: LOCKED (2026-07-09, committed BEFORE the data exists in-repo — the collection is pending an
API key only the user can obtain; locking pre-collection is the strongest possible ordering;
adversarially reviewed pre-lock, all required changes incorporated). User opened the gate 2026-07-09
("Vote Smart ES pull" selected). This is the §18-recorded path: "the one remaining powered ES path:
a fresh full-roster Vote Smart PCT pull — external collection, user-gated." (Roster correction in
passing: §18 said votesmart_id was "available for all 533"; the verified number is **518 of the 533
joinable** — 520/537 legislators.csv rows carry an id.) The lock commit contains the collector
(fec/votesmart_npat_fetch.py) and the look script (fec/b5_es_votesmart_look.py).

## Adverse prior, disclosed (the round-4 standard)

§18's RESULT-E2 already tested v2-ES against an NPAT-respond criterion and returned **−.042
WRONG-SIGNED (perm .70), not ES-specific (v2-E carried the largest |r| −.072), partial null** — at
N=171 current-roster members from the on-disk 2013-14 .tab snapshot. The criterion here ("≥1
completed PCT/NPAT in ANY cycle") INCLUDES those same NPATs, so this look is not independent of
that record. Load-bearing differences, stated: N≈518 vs 171 (3× the roster, both chambers); the
Vote Smart record covers ALL cycles per member, not one historical snapshot (many members' response
behavior post-dates the snapshot); and E2's power warning was pre-declared as the likely cause of
its null ("RKH's own effect +.063 — under our bar even at perfect transfer"). Still, a wrong-signed
prior at N=171 is a wrong-signed prior: **honest prior for the CORROBORATION tier is LOW**
(lowered from LOW-MODERATE by this disclosure), **and VERY LOW for the validity tier.**

## What this look is — and is not (expectations pinned up front)

RKH's own in-sample ES→NPAT-respond effect was +.063. At N≈518 that is *detectable* (one-sided .05
threshold ≈ .072; power vs true .063 ≈ 40%) but can never clear the +.15 validity bar. This is
pre-declared as a **CORROBORATION look, not a validation look**. A corroboration MISS at ~40%
power is recorded as "uncorroborated," never "disproven" — wording fixed here.

## Criterion & roster

- **pct_respond ∈ {0,1}** per member: 1 iff Vote Smart records ≥1 completed Political Courage
  Test / NPAT in ANY cycle for the member's votesmart_id (the trait-like RKH reading). The exact
  API field mapping is pinned in the COLLECTION RECORD addendum (below) before the look.
  Known limitation, stated: members with multiple Vote Smart candidate records (chamber switchers)
  are read via the legislators.csv id-of-record; an undercount there biases toward 0, reported not
  corrected.
- **Analysis roster, exact**: 533-roster ∩ votesmart_id = **518** (verified pre-lock) ∩ v2-ES
  non-null ∩ gender M/F (both verified 518 pre-lock) ∩ responded ∈ {0,1} (fetch_failed EXCLUDED,
  count reported). **Coverage floor: joined N < 450 ⇒ VOID-FOR-COVERAGE — no look consumed;
  collection may be completed/retried and the check re-run.**
- **Degeneracy guard**: base rate computed from the collection artifact ALONE, before any
  instrument file is opened; base rate <5% or >95% ⇒ **VOID-FOR-DEGENERACY — no look consumed**
  (criterion degeneracy is observable without any instrument pairing; the ordering makes the
  no-consumption claim true).
- Sign pre-declared: **higher ES → more likely to respond** (RKH direction).

## Collection protocol (collector committed in this lock; may run before or after lock, never after the look)

`fec/votesmart_npat_fetch.py`: Vote Smart API Npat.getNpat per candidateId (JSON), key from
fec/votesmart_api_key.txt (gitignored — the ignore entry rides this lock commit), 0.5s politeness
delay, resume cache. **Error taxonomy (pinned): responded=0 ONLY on a recognized no-NPAT/empty-npat
response; auth/quota/transport/unparseable ⇒ fetch_failed — retryable, never cached as done, never
counted in the base rate.** fetch_failed members may be retried until the COLLECTION RECORD is
written; the record freezes the artifact. Output votesmart_npat.json with per-member
{votesmart_id, responded, cycles (as extractable from the npat payload), note}; failures recorded,
never guessed.

## COLLECTION RECORD addendum (the ONLY permitted post-lock edit before the RESULT)

When collection completes, ONE scoped addendum is appended to this file containing exactly:
votesmart_npat.json SHA-256, joined analysis N, base rate, fetch_failed count, and the exact API
field mapping used for responded. Nothing else in this document may be touched. The look is gated
on this addendum existing and matching the artifact.

## Instruments under test (existing display reads only — nothing is trained on this criterion)

- PRIMARY: **v2-ES** (big5_v2.json). SECONDARY (reported): Pink-ES (big5_llm_opus.json).
- Excluded: voice-ES (CLOSED PERMANENTLY); any newly supervised model (would be a new route).
- Statistics: point-biserial r; exact permutation p imported from b5_behavioral_instrument
  (K=5000, seed 20260708); Frisch–Waugh partial imported from b5_n_matrix.fw_partial (K=5000,
  seed 20260710 — permutes the residualized criterion, the locked repo idiom). Unstratified
  permutation is deliberate and adequate for a rare binary: every replicate preserves the base
  rate exactly, and the exact-p construction carries the variance (on record to preempt the
  stratification attack).
- Deterministic pipeline (no folds): adversarial re-derivation of any non-MISS outcome =
  independent recomputation of the join and every statistic from the raw artifacts in a fresh
  process; **a mismatch is a DEFECT HALT — nothing is recorded until both computations agree, and
  the resolution is recorded.**

## Conditioning set for partials

[gender, party, chamber, log(1 + years since first election)] — tenure because PCT response rates
collapsed secularly. **Tenure source pinned**: first_congress = min(congress) for the member's
bioguide_id in votes/HSall_members.csv (SHA-256
`7f7b41cfec668961587c8902963b2ab491d811bd8841707e436e58ad7709553a`); years since first election =
2026 − (1789 + 2·(first_congress − 1) − 1). Verified computable for all 518 joinable members.
vote_share_last (behavior_panel.json members[m].vote_share_last) = one REPORTED extra partial,
non-gating.

## Input pinning (recorded at lock; the look aborts, not consumed, on mismatch)

- big5_v2.json `aed97ffa7c5cabf933bb7924b9c01d80c076452a137d4ebecf6b64c5c217fd7b`
- big5_llm_opus.json `4b462228f5445dec43d66fc04e801cbd1974d31d569908938150604c8ec19632`
- fec/legislators.csv `c5a6cbdbaae0bb19faa89852c29922809ececc70b97c149b4709588087e5e391`
- votes/HSall_members.csv `7f7b41cfec668961587c8902963b2ab491d811bd8841707e436e58ad7709553a`
- behavior_panel.json `f47b9b045357cad2c5644f551fc934e8a0aa793a22d98272632547a276d22a50`
- votesmart_npat.json: SHA deferred to the COLLECTION RECORD (the artifact does not exist at lock).

## Outcome space (nested tiers; the HIGHEST tier met is recorded; wordings fixed; exhaustive)

Let: S = right-signed r with exact perm-p < .05; SPEC = |r(v2-ES, criterion)| STRICTLY greatest
among the five v2 axes (tie = not specific; a Williams-t between ES and its nearest rival axis is
REPORTED so a knife-edge call is legible); PART-C = FW partial right-signed with perm-p < .05;
PART-M = FW partial ≥ +0.10 with perm-p < .05.

1. **VALIDITY** (expected UNMET): r ≥ +0.15 AND S AND SPEC AND PART-M AND re-derivation agreement
   → "ES text read externally validated (PCT respond)"; desk caveat updated; all prior caveats
   stand in history.
2. **CORROBORATION**: S AND SPEC AND PART-C → fixed wording: **"ES text read WEAKLY CORROBORATED
   by PCT-respond (r=…, under the validity bar; annotation only)"** — methods §22 + one desk
   caveat clause; no promotion, no un-caveating.
3. **SIGNAL, NOT SPECIFIC**: S AND NOT SPEC → fixed wording: **"corroboration signal present but
   not ES-specific — closed"** (an observed signal is never denied; given the v2 E-ES axis
   correlation of +.445 and a true effect ~.06, this branch is the likely one under an RKH-true
   world — stated now so its wording cannot be composed post-look).
4. **SIGNAL, CONFOUND-ATTRIBUTABLE**: S AND SPEC AND NOT PART-C → fixed wording: **"signal
   present, confound-attributable (fails the conditioning set) — closed, no corroboration claim."**
5. **UNCORROBORATED**: NOT S (wrong-signed or n.s.) → fixed wording: **"ES text read externally
   UNCORROBORATED — the §18 limbo closes with evidence"**; desk caveat gains "PCT-respond null
   (2026-07-09)."
Tiers 2–5 all CLOSE the respond-criterion route (one look). Any richer use of PCT content
(issue-position volatility etc.) is a new construct needing its own prereg — not a re-spec.

## Look gate (complete refusal conditions — fec/b5_es_votesmart_look.py, same commit)

REFUSES if: (a) this file is absent; (b) the literal line `STATUS: LOCKED` is absent; (c) a
newline-anchored `RESULT-VS` H2 heading exists (look consumed); (d) the COLLECTION RECORD addendum
is absent, or votesmart_npat.json's SHA / joined N / base rate mismatch it; (e) any instrument/join
fingerprint above mismatches; (f) VOID-FOR-COVERAGE or VOID-FOR-DEGENERACY fired. Default no-arg
mode = status. No LLM calls. Secondaries (Pink-ES, extra partials, Williams-t) firewalled — no
claim derives from them. §21 (round 5) and §22 (this look) serialize in that order — both preregs
lock in the same commit. The RESULT-VS section appends verbatim (MISSes included), committed same
session as the look.

## COLLECTION PROTOCOL AMENDMENT 1 (2026-07-09, PRE-COLLECTION — before any member's data exists)

Scope acknowledgment: the lock permitted only the COLLECTION RECORD as a post-lock edit. This
amendment nonetheless changes the COLLECTION METHOD — and is recorded openly rather than laundered
through a false record — because the API-key route is contact-gated with no timeline while the same
public data is readable today, and because the edit-restriction exists to protect the criterion,
roster, bars, tiers, and wordings, ALL OF WHICH ARE BYTE-UNTOUCHED. No collection data existed at
the time of this amendment; collection is not a look and is not consumable.

Method: the user's own Chrome session (claude-in-chrome), user-directed (Paul supplied the PCT URL
after the API's "Book Demo" gate), reading the PUBLIC per-candidate PCT pages
`justfacts.votesmart.org/candidate/political-courage-test/<votesmart_id>` (id-only; the site
redirects to the canonical slug), same-origin fetch, 0.8s politeness delay, single pass + retry of
failures, batches of ~20/call. Server-side routes (WebFetch, urllib with browser headers) return
403; the user's browser session renders the same pages any voter can read.

Responded mapping, PINNED BEFORE COLLECTION (raw markers stored per member so the mapping is
auditable from the artifact alone):
- `prev` = page contains "has responded to a Political Courage Test in a previous election"
- `tookCount` = occurrences of "addressed this issue directly by taking the Political Courage Test"
  (legend contributes ~1; a completed CURRENT test contributes one per answered item)
- `refusedCycle` = year in "did not provide voters with positions on key issues covered by the
  <YYYY> Political Courage Test"
- **responded = 1 iff prev OR tookCount ≥ 2; responded = 0 on a full page (>5,000 chars) with
  neither; fetch_failed (retryable, excluded from base rate) on non-200 or shell page (≤5,000
  chars — the SPA fallback observed during the pilot).**
- cycles = distinct years in "<YYYY> Political Courage Test" mentions (informational).
Pilot validation (recorded): Bean prev→1; Sanders prev+refused-2024→1 (the any-cycle trait
reading); Cruz refused-2024-only→0; Harrigan no-markers→0. Everything else in this document —
criterion definition, roster, coverage/degeneracy guards, conditioning set, tiers, wordings,
fingerprints, gates — stands verbatim. The COLLECTION RECORD (SHA, joined N, base rate, mapping
confirmation) follows collection as originally pinned; fec/votesmart_npat_fetch.py remains the
API-route collector should the key ever arrive (unused in this collection).

## COLLECTION RECORD (2026-07-09 — collection complete; artifact frozen; written BEFORE the look)

artifact_sha = 8b16c6812bccea0e9eb8d75876470992fb6afced0747846b1c84365c3ab41385
joined_n = 517
base_rate = 0.3133
fetch_failed = 1 (Lance Gooden, vsid 177282: full-size 112k-char page variant that failed the
proof-of-render check on repeated retries; retries exhausted under renderer throttling; excluded
from the base rate per the pinned taxonomy — never guessed)

Marker→responded mapping: BYTE-IDENTICAL to Amendment 1 (prev OR tookCount≥2 → 1; rendered page
with neither → 0; raw markers prev/took/refusedCycle/cycles stored per member in the artifact, so
the mapping is auditable from the artifact alone).

Full-page test resolution (recorded honestly, decided DURING collection, before any base-rate or
instrument computation): the pilot's ">5,000 chars = full page" proxy conflated two cases at
production scale — true load-shed SPA shells (~2–4k HTML, no member content; appeared only under
concurrent fetch load) versus sparse-but-real pages of members with NO test content (75–112k HTML
whose VISIBLE text after script-stripping is <5k). Ground truth: Lankford (vsid 124938) live-DOM
rendered 2,274 visible chars yet is a genuine member page ("James Lankford's Issue Positions…
Office: U.S. Senate (OK)"). Operationalization used: full page ⇔ proof-of-render — stripped DOM
text contains "Issue Positions (Political Courage Test)" AND "Office:" — strictly more accurate
than any char threshold; shells fail it, sparse-real pages pass it. Collection ran serial/low
concurrency (0.45–1.2s spacing, cache:no-store) after concurrent pools triggered server-side
load-shedding (SPA shell fallback) — 517/518 classified, zero shells in the final pass.

Roster note: joinable = 518 (533-roster ∩ votesmart_id in legislators.csv); artifact rows with
responded ∈ {0,1} = 517 of 518 (responded=1: 162, responded=0: 355). Coverage floor 517 ≥ 450
PASS; degeneracy guard .05 ≤ .3133 ≤ .95 PASS. Collected via the Amendment-1 browser-session
route, single pass + straggler retries, 2026-07-09 evening.

## RESULT-VS (2026-07-09 — the one look; recorded verbatim, same session)

Gate state at the look: lock TRUE | look not yet taken | instrument fingerprints MATCH |
collection artifact present, sha/joined_n/base_rate MATCH the COLLECTION RECORD | coverage and
degeneracy guards PASS. (Denominator note: the script prints fetch_failed=0 because Gooden is
absent from the artifact entirely — the RECORD's fetch_failed=1 counts him at collection; same
fact, two denominators, nothing gated on it.)

Look transcript (verbatim):

    criterion-side join: votesmart_id members=518 | responded-in-{0,1}=517 | fetch_failed=0 | base rate=0.313
    analysis roster (∩ v2-ES non-null ∩ gender M/F ∩ tenure computable): n=517

    === PRIMARY: v2-ES vs pct_respond ===
      [v2-ES] point-biserial r=+0.0550 exact perm-p=0.1080 (param 0.1057) | FW partial (gender,party,chamber,log-tenure) = -0.0075 p=0.5751
        specificity rival v2-O: r=+0.0857
        specificity rival v2-C: r=+0.0692
        specificity rival v2-E: r=+0.0633
        specificity rival v2-A: r=+0.0572
        Williams-t ES vs nearest rival (O): t=-0.57 p=0.5667 (reported)

    === SECONDARY (reported, firewalled): Pink-ES ===
      [Pink-ES] point-biserial r=+0.0886 exact perm-p=0.0242 (param 0.0242) | FW partial (gender,party,chamber,log-tenure) = +0.0464 p=0.1554
      extra reported partial (| vote_share_last): +0.0684 p=0.0620 (n=489)

    === VERDICT (nested tiers, highest met; wordings fixed by the prereg) ===
      TIER 5: "ES text read externally UNCORROBORATED — the §18 limbo closes with evidence"

    artifact sha at look: 8b16c6812bcc… | joined n=517 | base rate=0.313 | non-finite events: 0

**OUTCOME: TIER 5 (fixed wording): "ES text read externally UNCORROBORATED — the §18 limbo
closes with evidence."** S fails (r=+.0550, exact perm-p=.1080 ≥ .05); had S passed, SPEC would
also have failed — v2-ES is the WEAKEST of the five axes against this criterion (O +.0857,
C +.0692, E +.0633, A +.0572 all exceed it), and the FW partial is signless (−.0075, p=.575).
The Pink-ES secondary (raw +.0886, perm-p .0242; partial +.0464, p .155 — confound-attributable)
is REPORTED under the firewall: no claim derives from it. Tier 5's pre-declared consequences
apply: the desk ES caveat gains "PCT-respond null (2026-07-09)"; methods §22; the respond-
criterion route is CLOSED (one look). Richer PCT content (issue-position volatility etc.) remains
a new construct requiring its own prereg. Honest-prior accounting: the LOW/VERY-LOW prior and the
§18 RESULT-E2 adverse prior (−.042 wrong-signed at N=171) pointed here; the any-cycle criterion
at full power (n=517, base rate .313) settles it — the §18 limbo ("measured, no clean independent
validation") is no longer a data gap; it is an evidenced null on the one powered external
criterion available.
