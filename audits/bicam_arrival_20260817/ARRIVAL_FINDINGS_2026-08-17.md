# BICAM ARRIVAL AUDIT 2026-08-17 -- first-run record (tool verdict FAIL, decomposed)

Frozen dated record. Run: fec/tools/b0_bicam_arrival_audit.py --audit (D-009 item 2; download
chat-approved by Paul 2026-08-17). Outputs in this directory: bicam_arrival_audit.json (full
miss lists), bicam_arrival_manifest.json (per-input sha256 + row counts), source_manifest.json.

## Provenance chain

- Six zips pulled from downloads.bicam.net; sha256 6/6 MATCH vs the pip package's pinned
  hashes (site and package distribute identical bits -- retires that recon blocker).
- Stage transforms (all deterministic, recorded): bills_sponsored derived from
  bills_sponsors.csv (361,979 rows) + bills_cosponsors.csv (3,915,543 rows) with an explicit
  relationship column; members_staged adds member_id = bioguide_id (2,555 rows);
  bills_texts (371,806 rows) and committeereports (106,498 rows) projected to their id
  columns because the tool's csv reader lacks field_size_limit (defect 1 below).
- BILLSTATUS comparison source built from the legfix5 enrichment lane's
  member_measure_edges.ndjson (14,854 acts, 204,021 current-cosponsor edges; withdrawn-role
  edges excluded by role label). NOTE: that file's current sha256
  FAF0DD0B9A0C563F897EEA88FA8ACEE756DF8DBE65BE98E67491118B08727FB0 differs from its 07-26
  smoke-manifest pin 772fb736905295acddc296110324e5adf17302206a0b28bf7e2b6ac4ab296b6f --
  file is newer than the manifest; recorded, not adjudicated here.
- legfix5 presence view: 18,552 of 18,555 receipts; THREE receipts are 1,330 bytes of
  binary garbage each (119:hr:2393, 119:hr:2397, 119:hr:2401) -- adjacent bills, one
  OneDrive write window; a store finding for the legfix5 lane to adjudicate (not repaired).
- Tool patch in the same commit: receipt body-field fallback + "html_file" (the real
  receipts' field name); their 19-test suite re-run green post-patch.

## The four verdicts, decomposed

1. roster_join FAIL 485/533. The 48 missing bioguides are the 119TH FRESHMAN CLASS
   (spot-verified: Ansari, Alsobrooks, Armstrong, Baumgartner, Bell, Bynum, Conaway,
   Dexter, Elfreth, Figures, Friedman, Fine...). REAL BICAM FINDING: the members component
   ends at the 118th Congress (matches the pip package's congress_range 1-118; the site's
   "81st-present" label overstates; "Data Last Updated 1/25/2025"). Consequence: B2
   rollover use is blocked for freshmen until BICAM updates; the melange roster remains
   authoritative. Question for maintainers (bicam.data@gmail.com): 119th update timeline.
2. act_universe_join FAIL 38/644. Dominated by a TOOL DEFECT: bill-type key normalization
   between repo keys ("H.R.1919|119") and BICAM bill_ids ("hr1919-119") fails for most
   types -- only 38 joined when several hundred pre-119th acts should. Compounded by real
   119th absence (253/644 acts are 119th; bills.csv rows 414,376 vs the paper's 421,764 --
   delta consistent with a missing 119th tranche). Non-bill LTR-* acts appear in the miss
   list as expected. NOT a data verdict until defect 6 is fixed and the audit re-run.
3. text_presence FAIL, overlap 0/18,557 (LEGFIX5_ONLY=18,552). TOOL DEFECT: the check
   never aligns BICAM bill_id format with legfix5 canonical keys ("117:hr:2434") -- the
   two key spaces are disjoint by construction, so the matrix is an artifact, not a
   coverage measurement.
4. cosponsor_agreement FAIL on the n>=100 sample floor only (37 joinable acts available).
   Where keys DID align, agreement was PERFECT: 420/420 cosponsor entries, aggregate
   ratio 0.0000 vs official BILLSTATUS. The strongest early quality signal for BICAM --
   worth restating once defect 6 raises the joinable sample past the floor.

## Tool defect ledger (assigned to the deferred Codex second-review round)

1. csv.field_size_limit never raised -- crashes on >128KB fields (bills_texts raw_text,
   committeereports); worked around this run via id-projections.
2. iter_json_records crashes on non-record JSON instead of skipping/ledgering (events/*.json).
3. --legfix5-run / --legfix5-fulltext DEFAULTS are miswired vs the code's own consumption
   (presence loader wants the httr store root; discovery reader wants the records ndjson).
4. Receipt body-field name mismatch: real receipts use "html_file" -- PATCHED (this commit).
5. A single unreadable receipt aborts the whole audit rather than entering the error ledger.
6. Repo-to-BICAM bill-type normalization broken for most bill types (38/644 join).
7. BICAM-to-legfix5 canonical-key alignment absent in the text-presence check.

Fixtures never exercised GB-scale files, real receipt schemas, or real key formats -- the
arrival-world gap this audit exists to close. Defects 6-7 gate any re-run whose act/text
bars can be read as DATA verdicts.

## Standing disposition

BICAM holdings stay in C:\melange-data\bicam_snapshot (off-OneDrive, non-repo), consumed
by NOTHING. The roster-currency finding and the 420/420 cosponsor signal are logged in the
effectiveness sheet. Re-audit follows the defect-6/7 fixes in the review round.

## RUN 2 (same day, post-normalization fixes) + CORRECTION OF RECORD

TOOL FIXES APPLIED (this commit; suite 22/22 after adding 3 regression tests): tolerant
congress parsing (_parse_congress -- BICAM's congress column mixes "118" with "118.0"
float-strings, 17,693 of the 118th rows float-encoded; the old int() parse silently dropped
them all -- defect 6's dominant cause) and canonical-to-BICAM key conversion in the
text-presence check (defect 7). Reports: *_run2.json beside the run-1 files.

RUN-2 VERDICTS (tool status still FAIL -- every remaining failure is now a REAL data fact):
- roster_join 485/533 unchanged: the 48 freshmen are genuinely absent (see correction below).
- act_universe_join 323/644, now FULLY DECOMPOSED with zero unexplained: pre-119th bills
  join 319/319 (100%); +4 via the 119th early-January sliver; 141 misses = 119th bills
  beyond the sliver (real currency gap); 173 = STANDALONE AMENDMENTS (S.Amdt./H.Amdt.) in
  our act universe -- structurally outside bills.csv (they live in the un-downloaded
  amendments component) and outside bill_type_key's grammar; 7 = non-bill letters (by
  design). The >=640/644 bar cannot pass while 253 universe acts are 119th and 173 are
  amendments -- BAR RECALIBRATION (per-stratum) assigned to the review round, Paul-visible,
  never silently weakened.
- text_presence overall 0.610 -- but stratified: PRE-119TH BILLS AGREE 98.65% (n=11,474),
  ABOVE the 0.95 bar on the honest stratum. The 7,238 LEGFIX5_ONLY = 3,703 amendments
  (component not downloaded) + ~3,380 119th bills (BICAM texts end at the 1/25/2025
  sliver) + ~155 residual pre-119th gaps (the true disagreement sample, enumerable).
- cosponsor_agreement PASS: 304 both-source acts, 1,288 vs 1,288 entries, aggregate ratio
  0.0000, per-act differences NONE. BICAM cosponsorship is byte-perfect against official
  BILLSTATUS on our joinable universe.

CORRECTION OF RECORD (supersedes run-1 wording, Paul's challenge sustained in part):
Run 1 said "the members component ends at the 118th." Sharpened by direct raw-file
verification: (a) bills.csv DOES carry the 119th -- a 131-bill early-January sliver
(hr239-119 range), consistent with "Data Last Updated 1/25/2025"; (b) members is STALER
than stated -- members_terms has only 17 rows for the 118th (vs ~550/congress) and zero
119th: effectively EARLY-118TH vintage; the five probed freshmen are absent from
members.csv and bills_sponsors.csv by exact bioguide. The public drop is a mixed-vintage
export; the paper's "6th-119th" describes the internal database. Practical verdict
unchanged: unusable for 119th freshmen or current-Congress work until BICAM refreshes.
Propagation: this block supersedes the run-1 sections above; the effectiveness-sheet and
brain entries carry the corrected wording from this date.
## RUN 3 (2026-08-17, on the FIXED DEFAULTS post fix-round @0fc190cd1)

FIRST RUN WITH NO HAND-PINNED LEGFIX5 PATHS: the D3-corrected defaults resolved correctly
(run -> text_relevance_httr_full_20260727z, 18,552 receipt keys; fulltext -> the discovery
ndjson, 18,557) and the real store walked clean (skipped_nonrecord 0 everywhere; the three
damaged receipts became LEDGER ENTRIES exactly matching the manual scan: 119:hr:2393/2397/
2401). Verdicts:
- roster_join FAIL 485/533 (unchanged real currency signal).
- act_universe_join FAIL on the unchanged aggregate bar, now with NATIVE strata:
  {116: 0/21, 117: 153/173, 118: 169/197, 119: 1/253} (n per congress includes non-bills);
  NON_BILL natively separated = 180 (173 amendments + 7 letters), MALFORMED = 0, canonical
  duplicates = 0. CORRECTION OF RUN-2 ARITHMETIC: pre-119th BILLS join 153/153 + 169/169
  = 322/322 (100%) and the 119th sliver contributes 1 join -- run 2's sidecar decomposition
  said "319/319 + 4 sliver" for the same 323 total; the native split supersedes it. The
  100% pre-119th conclusion is UNCHANGED.
- text_presence FAIL: agreement 0.610 byte-consistent with run 2, and the AMEND-2
  fail-closed veto FIRED AS DESIGNED on the three ledgered receipts -- the honest verdict
  about a store carrying damage, versus run 2's view-based route-around.
- cosponsor_agreement PASS, UPGRADED CLAIM: the new identity-set metric shows
  symmetric_difference_total = 0 and identity_mismatch_ratio = 0.0000 across 304 acts /
  1,288 entries -- BICAM cosponsors are IDENTITY-perfect against official BILLSTATUS,
  closing run 2's count-only caveat.
Reports: *_run3.json beside runs 1-2. The per-stratum BAR RECALIBRATION proposal
(FOLLOWUPS section 1) remains Paul-gated; under it, run 3 would read: pre-119th strata
PASS, roster FAIL (real), text pre-119th PASS with 3 receipt-damage entries flagged.
## RUN 4 (2026-08-17, under the D-011 RATIFIED per-stratum bars @a42674d56)

bars_schema d011-stratum-v1. The verdict regime now says what it means:
- act_universe_join: **PASS -- the first act-bar pass of the arc**, earned on the honest
  stratum (pre-119th bills 100% >= the ratified 98.7%); the 119 stratum reports unarmed
  (congress_119_snapshot_rows = 131 < 5000; hit rate 0.007 report-only), amendments
  placeholder unarmed pending the future component contract.
- roster_join: FAIL 485/533 -- the intended BICAM-currency signal, unchanged.
- text_presence: FAIL via the RETAINED AMEND-2 veto (3 damaged legfix5 receipts) -- the
  pre-119th stratified agreement (0.9865) clears the ratified 0.95 and the bar will PASS
  the moment the legfix5 lane repairs or adjudicates those three receipts.
- cosponsor_agreement: PASS, identity-perfect (symdiff 0 across 304 acts / 1,288 entries).
Overall FAIL = roster currency + receipt damage, both real, both intended signals. The
D-011 implementation carried two adversarial review rounds (empty-stratum fail-open
defects caught and closed fail-closed; causal boundary tests at exactly 0.987 and 0.95).
## RUN 5 (2026-08-17, receipts REPAIRED + amendments stratum ARMED @4ac4a782f)

Two arming events between runs 4 and 5: (1) the legfix5 lane's httr cookie-replay
re-fetch repaired 119:hr:2393/2397/2401 (damaged pair quarantined with sha256 damage
record; fresh receipts HTTP 200, bodies 365-388K chars, title-matched; store presence
18,552 -> 18,555); (2) the amendments component (6.41GB, sha256 pin MATCH) was staged
(28.1MB amendments.csv; 111,977-row amendments_texts id projection from the 28.6GB raw)
and the D-011 amendments arming condition -- "component is present" -- was implemented
under manifest schema bicam-fetch-map-v2 (executor lane, two review rounds, v1
byte-identity golden-pinned). Verdict decomposition, bars_schema d011-stratum-v1:
- act_universe_join: FAIL, and solely on the NEWLY ARMED amendments stratum. Pre-119th
  bills stay 322/322 (100%); 119 stays report-only (131 rows < 5000). The armed
  amendments stratum reads 57/173 = 32.9% (bar 95%): ZERO JOIN DEFECTS (no missed id
  exists in the staged csv; per-congress decomposition: 119th 0/108 -- BICAM's
  amendments component contains NO 119th amendments at all (max staged numbers stop in
  the 118th) -- vs pre-119th 57/65 = 87.7% (116th 21/21, 118th 23/26, 117th 13/18).
  The dominant cause is the same Jan-2025 vintage already established for bills/members;
  the 8 pre-119th misses are real BICAM amendment-coverage gaps (window: the 65
  pre-119th amendment acts of the 644-act universe).
- roster_join: FAIL 485/533 -- the intended currency signal, unchanged.
- text_presence: **the run-4 blocker is CLEARED** -- legfix5_errors = 0 (AMEND-2 veto
  no longer fires) and pre-119th bill agreement 0.9859 (n=11,474) clears the 0.95 bar.
  FAIL persists solely on the newly armed amendments stratum: agreement 2,643/3,703 =
  71.4%; per-congress (denominator = legfix5-present amendment keys): 116th 1,139/1,139
  = 100%, 117th 812/894 = 90.8%, 118th 692/796 = 86.9%, 119th 0/874 = 0% (zero 119th
  amendment texts in BICAM). Pre-119th pooled 2,643/2,829 = 93.4% -- genuinely below
  the 0.95 bar even excluding the 119th: unlike bills (98.6%), BICAM's pre-119th
  amendment TEXT coverage carries real 117th/118th gaps.
- cosponsor_agreement: PASS, identity-perfect, unchanged (bills-only universe by design).
Overall FAIL = roster currency + amendments-component vintage/coverage, all real data
verdicts; zero tool defects found in decomposition (the arming's join was spot-audited
against the staged csv directly). Reports: *_run5.json beside runs 1-4. The receipt
repair achieved exactly its predicted effect: the text bar's run-4 blocker is gone and
the pre-119th text stratum PASSES; the armed amendments strata add honest currency
failures that harden automatically when BICAM ships a refresh with 119th + fuller
amendment coverage.