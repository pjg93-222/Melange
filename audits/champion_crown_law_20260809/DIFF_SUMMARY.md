# Champion crown law — verification summary

**Law (Paul, 2026-08-09): a champion cannot be a threat.** Implementation: crown
supremacy — a Tier-1 crown (overall display Champion; desk-bundle tier == 1) never
appears on any sector's threat board in the champions-v2 artifact, uniformly across
credit_union / bank / crypto / fintech. A crown whose docket would force the threat
board (veto or opposition leadership) demotes to the mixed board when
opposition_att >= 3, else is omitted; both outcomes are receipted per sector under
`crown_threat_exclusions`. Non-crowned routing is untouched — the ratified
2026-08-06 forced-threat routing (Durbin/CCCA) is the negative control.

**Why:** Maxine Waters (crown rank 3/13) sat on the credit_union THREAT board — the
opposition-leadership rule fired on her sponsorship of 118:hr:9303 (Payment Scams
Act; two CU orgs oppose-signed, kim) and overrode her 20-vs-3 supportive profile —
while every main surface crowns her Champion. Tim Scott (also crowned) sat on the
bank threat board the same way.

**Lanes:** Codex (xhigh) authored all four source edits; its managed sandbox denied
python execution, so runtime verification ran in the coordinator lane as visible
PowerShell (glassbox decision event in run
run-20260809T2326505798049Z-41fd9d10c1). Pre-edit state was reconstructed by
stashing the four files. Status: **ALL GATES PASS** (18/18, see diff_receipt.json).
Post-review hardening: the two audit checks gained an exists-guard (missing
boards.json now fails clean instead of crashing the audit mid-run) — applied by
the coordinator lane after both independent reviews flagged it (Codex MCP link
was down); glassbox decision event in the run stream.

| Gate | Result |
|---|---|
| Input purity: baseline (unpatched code, current inputs) == live artifact, generated_utc excluded | PASS — the diff below is exactly the law's effect on deployed data |
| CU threats: exactly Waters removed | PASS |
| CU threats backfill: Lauren Boebert B000825 (threat 0.068, the previously-capped #26) | PASS |
| CU negative controls Durbin/Blumenthal/Sanders/Warren/Booker retained | PASS |
| CU mixed: exactly Waters added (tier 1, opposition_att 3, opp_sponsored 1, threat 2.484746) | PASS |
| Bank threats: exactly Scott removed; Barr + Sessions retained; 6 -> 5, no backfill pool | PASS |
| Bank mixed: exactly Scott added (opposition_att 5 >= 3) | PASS |
| Crypto + fintech: all boards unchanged | PASS |
| Champions boards: unchanged in all four sectors | PASS |
| Zero retained-row drift anywhere | PASS |
| Receipts: crown_threat_exclusions == Waters(CU,mixed) + Scott(bank,mixed); rules.champion_exclusivity present | PASS |
| Audit checks fire on baseline (exactly Waters+Scott), clean on rule artifact | PASS |
| Live shared artifact untouched (sha stable end-to-end) | PASS |

**Board totals:** baseline 134 champions / 31 threats / 108 mixed -> rule
134 / 30 / 110.

**Tests:** lobbying suite direct 232/0 pre -> 237/0 post (5 new crown-law pins);
full harness in worktree: same 6 environmental failures pre and post, zero new
(test_lda_rebuild moved FAIL->OK once `fec\entity_identity.json` scaffolding was
copied in; see isolation.txt).

**Deploy note:** the two new audit_full.py checks read RED on the live machine
until the deploy chain regenerates boards.json (champions_v2 runs before audit in
run_pipeline.py, so a normal chain run lands green). After deploy, Waters also
stops being ADVERSARY-excluded from the CU lobbying-efficiency ranking
(efficiency_layers.py consumes the CU threats board).
