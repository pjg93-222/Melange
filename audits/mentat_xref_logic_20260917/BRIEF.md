# Brief: re-examine the Mentat cross-verification logic (contradictions, not ambiguity)

Written 2026-09-17 by the S3 (PAC evidence) session on Paul's instruction: "You need to start a new session and go over the logic of the cross verification. If you can improve the process to reduce this, then do it." This file is self-contained; the session that picks it up needs nothing from the S3 transcript.

## Paul's words (verbatim, 2026-09-17)

> Ok, I think we really need to reconsider the whole idea of the Cross-Verification, it is way too strict
>
> * Donor not matched to a listed company · counted at $0 — 36,241 — $37,940,955. = This is an inevitability and is why we filter based on name, giving amount and all the other steps
> * Memo entry without a proven parent receipt — 19,529 — $8,522,419.98 = This is also an inevitability
>
> Just because it is missing info does not mean it should be excluded; we are focusing on contradictions, not ambiguity.
>
> You need to start a new session and go over the logic of the cross verification. If you can improve the process to reduce this, than do it

Second ruling, same day, when told to start the session:

> Start the session, and its ok if they work at another company if the money is going to something JP Morgan affiliated or if they are an advisor or in an a adjacent position

## The rule to apply

A cross-verification step may remove or zero a row only when evidence CONTRADICTS it: a proven duplicate of a counted parent (same filing, same amount, same date, memo leg of a counted conduit receipt), a proven refund, a proven wrong committee, a name that provably belongs to another listed company. Missing or ambiguous information is never grounds for exclusion: an employer that does not match the register, a memo leg whose parent is simply absent from the corpus, an attribution that is "unsettled". Those rows stay counted and flagged as unverified. The name, amount and date filters that admitted the row are the intended defence against noise.

**Employer mismatch is not a contradiction (second ruling).** A donor whose stated employer is another company still counts for the listed company when either holds:

- **Recipient route:** the money goes to something affiliated with the listed company (JP Morgan is Paul's example): its PAC, a connected or affiliated committee, a committee whose connected-organization name resolves to the listed company. Use the PAC register, `verified_company_affiliations.json` and the FEC connected-organization field; the recipient side proves the affiliation, the employer field does not have to.
- **Role route:** the donor is an advisor or holds an adjacent position for the listed company (advisor, adviser, consultant, board member, director, trustee, counsel, and similar) where the occupation or employer text names the listed company or its affiliate. Propose the marker vocabulary to Paul with row and dollar counts per marker before applying it; the list is his.

Only when neither route applies does the row stay counted-but-unverified (never zeroed). A row is attributed to a DIFFERENT listed company only on the same evidence, never on a guess.

Paul's "then do it" is the go for the code change once the reason-code table below has been shown to him (standing rule: present, then act; APPLY of anything beyond this lane's files is his).

## Where the logic lives (all under C:\Users\pgoff\Mentat\mentat, branch codex/mentat-crypto)

- `tools/cross_reference_engine.py` — the engine. Anchors from the 2026-09-17 council review (verify against the file; other lanes have committed since): register match by exact string `:146`; transfers retained `:283-289`; memo legs with no proven same-filing parent `:424-451`; earmark legs `:456-500`.
- `tools/cross_reference_store.py` — run storage.
- `app/cross_reference_data.py` — console data layer for the tab (also exports `_source_url`, imported by `evidence_csv.py`; keep that name).
- `app/cross-reference.js:33-36` — the reason labels Paul sees: `company_attribution_unresolved` → "Donor not matched to a listed company · counted at $0"; `attribution_unresolved` → "Attribution unsettled · counted at $0"; `memo_parent_not_established` → "Memo entry without a proven parent receipt". `tests/test_studio_wording.cjs:103-106` pins those labels.
- Runs: `state/cross-reference/<runId>/` with a `rules/tools/` snapshot of the engine that produced the run (use it to confirm which code made the numbers Paul is looking at). Latest Banking run `20260913T074303-bca0ac2b9cd3`; Fintech runs are the `20260911T01…` ones. Only Banking and Fintech runs exist.
- Prior read-only review: `C:\Users\pgoff\Mentat\audits\mentat_xref_workbook_review_20260917\REVIEW.md` (+ `workbook_totals.py`, `workbook_facts.py`, `sheet_summary.py`, `workbook_census.py`, `banking_workbook_totals.txt`, `workbook_census.txt`). Memory files: `mentat-xref-workbook-review-2026-09-17.md`, `mentat-system-debug-lane-2026-09-13.md` (the $37.9M diagnosis), `xref-contradictions-not-ambiguity-2026-09-17.md` (this rule).

## Numbers already established (Banking run 20260913T074303, cycles 2022/2024/2026)

- Baseline $133,516,227.27 (accepted, non-excluded, non-duplicate-memo DB rows at face value); observed original giving $72,103,655.70 (employee $70,446,487.57, unverified $1,657,168.13, corporate $0.00); PAC outgoing $22,774,438.00 separate; change −$61,412,571.57.
- Review queue 76,197 rows / $49.9M gross. `company_attribution_unresolved` 36,241 / $37,940,955.71 — zeroed in every total. `memo_parent_not_established` 19,529 / $8,522,419.98. Transfers 18,696 / $5,789,063.20. Earmark legs ~$0.7M. FEC-verified rows 13,853 of 849,399 (1.6%).
- Published workbook total for the same cycles $54,762,844.05. The review found the engine counts $17.3M MORE than the workbook on retained memo/transfer/earmark legs while zeroing $37.9M on unmatched employers: both directions are ambiguity treated as fact.
- Fintech run 20260911: baseline $9,803,891.31 (equals the Fintech workbook exactly); observed $9,089,743.52; unresolved exposure $17.9M; PAC $0; corporate $0.
- Structural under-counts the review named, all ambiguity-type: corporate treasury $0 (`verified_company_affiliations.json` has 12 records, zero treasury_entity); PAC outgoing $0 for every non-Banking industry; exact-string register match; cycle from receipt date instead of FEC two_year_transaction_period.

## What to do

1. Read the engine's decision points and build the reason-code table: reason code → where it is decided (file:line) → current effect (zeroed / excluded / retained-with-flag) → evidence class (CONTRADICTION or AMBIGUITY, with the one-line test that distinguishes them) → proposed effect. Include every reason the engine emits, not only the two Paul named; `attribution_unresolved` is the third visible bucket. For `company_attribution_unresolved`, split the 36,241 rows by which route would rescue them (recipient route, role route, neither) with row and dollar counts from the Banking run.
2. Present the table to Paul in the chat, with the dollar and row count per reason from the Banking run, and the proposed advisor/adjacent marker vocabulary with counts. Then proceed (his "then do it").
3. Change every AMBIGUITY reason from zero/exclude to count-with-flag: the row stays inside the observed totals, carries its reason as a flag, and the tab shows an "unverified" slice beside "FEC-verified" instead of a $0 line. Apply the recipient and role routes before flagging. CONTRADICTION reasons keep their effect. Do not touch the name/amount/date filters upstream; they are the intended screen.
4. Re-run Fintech first (smaller; measure the run time), then Banking. Report per reason: rows and dollars before and after; observed original giving before and after; the workbook total for comparison ($54.76M Banking). If observed giving now exceeds the workbook by a wide margin, say so and name the reason codes responsible; that is Paul's call, not a reason to re-zero.
5. Tests red before, green after: engine unit tests for one contradiction case (proven duplicate memo leg stays out), one ambiguity case (unmatched employer stays in, flagged), one recipient-route case (other employer, listed company's PAC as recipient, attributed) and one role-route case; `tests/test_studio_wording.cjs` for any relabel (labels must stop saying "counted at $0" if that is no longer true).
6. Packet: `C:\Users\pgoff\Mentat\audits\mentat_xref_logic_20260917\` with REVIEW.md (the table and the before/after), `patches/<slug>.patch` cut as bytes (`git diff -- <files> > file` via bash redirect; the text=True patch cutter mangles non-ASCII), receipts with the test output and run summaries. Append a HANDOFF section if the packet has one. Commit only if Paul says so; never `git stash`, `git add -A` or `commit -a`; stage by explicit path and check `git diff` hunk by hunk (other lanes have uncommitted hunks in shared files).

## Constraints that bit earlier sessions

- From a Melange worktree session the Write/Edit tools REFUSE `C:\Users\pgoff\Mentat`. Write patch scripts to the scratchpad with the Write tool and run them with Python; pass Windows paths (`C:\...`) to Python, `/c/...` paths fail in `python -c`. Never unquoted heredocs (they mangle backslashes and apostrophes). Preserve each file's line endings (most `mentat/app` and `tests` files are CRLF).
- The collector-slowdown session is committing `mentat/app/server.py`, `app.js`, `index.html`, `tools/api_company_cycle_fanout.py`, `tools/merge_company_shards.py`, `tools/collect_api_lane.R`, `tools/parallel/*.ps1`, `R/fec_api.R` on 2026-09-17; do not edit those until its commits land (check `git log` for a resume-route commit).
- Never bind ports 8802, 8806, 8808, 8841. Consoles 8806 and 8802 are Paul's; a rebuilt tab needs a console restart to show.
- Reasoning and code in Fable (or an Opus architect); never Sonnet/Haiku for code; Haiku scouts gather facts only and their "not found" claims must be re-checked with your own grep. Verify every agent claim against output; an earlier agent reported "33 passed" for a run that never happened.
- Long runs: never poll-supervise; start the run, do other work, read the output file when notified.
- A Banking cross-reference run reads ~850k rows; measure Fintech first and estimate before starting Banking.
