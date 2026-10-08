# BICAM FOLLOW-UPS -- 2026-08-17 (drafts for Paul's gates; nothing applied)

## 1. Per-stratum bar recalibration PROPOSAL (replaces the un-passable >=640/644 composite)

The run-2 decomposition proved the composite bar arithmetically unreachable while 253 of
the 644 universe acts are 119th-Congress and 173 are standalone amendments outside the
downloaded component. Proposed replacement bars, one per honest stratum -- for Paul's
ratification, never self-applied:

| Check | Stratum | Proposed bar | Run-2 measured |
|---|---|---|---|
| act_universe_join | pre-119th BILLS (n=319) | >= 315/319 (98.7%) | 319/319 PASS |
| act_universe_join | 119th bills | REPORT-ONLY until BICAM ships a 119th refresh; auto-arms at >= 95% when congresses.csv shows 119th coverage | 4/145 (sliver) |
| act_universe_join | amendments (n=173) | REPORT-ONLY until the amendments component is downloaded; then >= 95% | structurally 0 |
| act_universe_join | letters (n=7) | excluded by design, count stated | excluded |
| text_presence | pre-119th bills (n=11,474) | >= 0.95 agreement | 0.9865 PASS |
| text_presence | 119th bills + amendments | REPORT-ONLY, same arming conditions as above | structural |
| cosponsor_agreement | joinable universe | unchanged (<= 0.02 aggregate, n >= 100) | 0.0000 on 304 PASS |
| roster_join | 533 roster | unchanged (533/533) -- a currency FAIL is the intended signal | 485/533 FAIL (real) |

Net effect if ratified: the tool's verdict becomes a real data verdict today (pre-119th
strata PASS; roster FAIL stands as the honest currency signal), and the report-only strata
harden automatically when their arming conditions are met. Implementation is a tool change
-> executor lane with tests, after Paul's ratification.

## 2. Maintainer email DRAFT (not sent -- sending is Paul's action)

To: bicam.data@gmail.com
Subject: 119th-Congress refresh timeline + a small members-vintage observation

We are using BICAM (great resource -- thank you) for cross-validation against an internal
congressional dataset. Two questions and one observation from our arrival audit of the
public drop (site copies sha256-matched your package pins, 2026-08-17):

1. The public members component appears effectively early-118th vintage (members_terms has
   17 rows for the 118th vs ~550/congress, none for the 119th; 119th freshmen absent from
   members.csv), while bills.csv carries an early-January 119th sliver (131 bills)
   consistent with "Data Last Updated 1/25/2025". Is a 119th refresh scheduled, and will
   members and bills land together?
2. Is the congress column's mixed encoding in bills.csv intentional ("118" vs "118.0"
   float-strings; 17,693 of the 118th rows are float-encoded)? Downstream integer parsers
   drop those rows silently.
Observation: on our joinable universe (304 acts), bills_cosponsors matched official
BILLSTATUS bulk data 1,288/1,288 entries exactly -- excellent quality signal.

## 3. Residual pre-119th text-gap enumeration

~155 pre-119th bill keys are LEGFIX5_ONLY in run 2 (the true disagreement sample).
Enumeration script queued (shell temporarily unavailable at drafting time); the list will
be appended to this file as section 3a with per-key classification (their gap / our
phantom / id mismatch) when it runs.

## 4. Amendments component

Downloading bicam_amendments.zip (6.5 GB zipped, ~13 GB extracted, README warns ~30 GB
working space) would close the 173-amendment stratum and 3,703 discovery-key stratum.
NOT downloaded -- Paul's call, listed here as the arming action for the amendment bars.

## 3a. Residual gap enumeration (computed 2026-08-17; full list residual_gaps_run2.json)

162 pre-119th bill keys where legfix5 holds accepted text and BICAM bills_texts does not
(receipt-view presence basis, 18,552 keys vs 279,031 BICAM text ids). Composition: 118th
Congress 162/162 (96 hr + 66 s), dominated by the high-number late-session tail (hr10004+):
the coherent reading is that the BICAM text export predates the late-118th publication
backlog clearing, matching the mixed-vintage picture elsewhere. Not a scattered-quality
finding; folds into the same currency question as section 2's email.
## 4a. Amendments component ACQUIRED + schema inventory (2026-08-17, Paul-ordered)

Downloaded 6.41GB, sha256 MATCH vs package pin 2b2660041df3f83a4b9d76758dc4acbba4e97ffe
bdd4fc603773a3f1e35d79e7; extracted to C:\melange-data\bicam_snapshot\extracted\
bicam_amendments (9 CSVs; amendments_texts.csv inflates to 28.6GB -- the README ~30GB
warning was accurate; use the id-projection idiom for any full-file audit pass).
Schema (headers verified): amendments.csv(amendment_id, amendment_type, amendment_number,
congress, chamber, purpose, description, proposed_at, submitted_at, is_* flags);
amendments_sponsors/_cosponsors(amendment_id, bioguide_id); amendments_amended_bills
(amendment_id, bill_id); _amended_amendments, _amended_treaties, _actions,
_actions_recorded_votes; amendments_texts(amendment_id, date, type, raw_text, pdf, html).
INTEGRATION CONTRACT INPUTS (for the new session, executor lane): repo key "S.Amdt.N|C" /
"H.Amdt.N|C" normalizes to bicam amendment_id "samdtN-C" / "hamdtN-C"; the 173-act
amendment stratum joins via amendments.csv; the 3,703 discovery hamdt/samdt keys join
text presence via amendments_texts ids; congress column expect the same int/float-string
mix as bills (the tolerant parser already handles it). Arming the D-011 amendments
stratum = extending the seven-component manifest schema deliberately (a contract change,
Paul-visible), never a silent expansion.
## 2a. Maintainer email -- ADDITIONAL OBSERVATION from run 5 (2026-08-17, unsent; sending stays Paul's action)

Append to the draft in section 2, as item 3:
3. We also pulled bicam_amendments.zip (sha256 matched your pin). Two observations from
   cross-validation: (a) the component appears to contain no 119th-Congress amendments
   at all (our 119th amendment keys go 0-for-874 on texts and 0-for-108 on the
   amendments table, while the staged max amendment numbers stop in the 118th) --
   presumably the same 1/25/2025 vintage; will the amendments component ride the same
   refresh as bills/members? (b) On pre-119th coverage, our text store agrees with
   amendments_texts at 100% for the 116th but only 90.8% (117th) and 86.9% (118th) --
   1,060 amendment texts we hold that the component lacks; if useful we can share the
   id list.

## 5. Amendments arming CLOSED + run-5 outcome (2026-08-17)

The section-4/4a arming action is COMPLETE: component downloaded (pin MATCH), staged
(ids projection), and the D-011 arming condition implemented @4ac4a782f (merged
56f1f84c7; manifest schema bicam-fetch-map-v2; two adversarial review rounds; v1
byte-identity pinned to a pre-change golden). Run 5: the armed act stratum reads
57/173 = 32.9% and the armed text stratum 71.4% -- honest FAILs, vintage/coverage-
driven, zero join defects (decomposition in ARRIVAL_FINDINGS run 5). The 3-receipt
repair landed the same day: AMEND-2 veto cleared, pre-119th text 0.9859 PASSES its
stratum. Remaining external dependency: a BICAM refresh (119th + fuller amendments);
all strata harden automatically when it ships.