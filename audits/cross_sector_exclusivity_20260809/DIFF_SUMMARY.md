# Cross-sector exclusivity — champion seat yields (Paul 2026-08-09)

**Ruling:** a member on any sector's RETAINED threat board holds no champions
seat in any sector — the threat seat stands (ratified Durbin routing), the
champions seat yields, receipted per sector under `cross_sector_exclusions`.
Crowns resolve the other way first (crown supremacy): never threats, so their
champion seats never yield. With both laws instated, nobody in the artifact is
champion-anywhere and threat-anywhere.

**Implementation:** build_payload split into two phases (stage sectors →
global retained-threat set → champion-class strip before the per-chamber cap),
`_assert_boards` 4th param + champions-seat rejection, CROSS_SECTOR_RULE
receipt text, third audit_full ck, one renderer subtitle sentence, 4 test pins
on a minimal fixture extension (119:hr:7, bank-supportive, M000001-only).
Coordinator-implemented (Codex MCP down all night, documented deviation
precedent); independently reviewed — zero blockers, zero minors, 4 notes.

**Gates (all PASS, see diff_receipt.json):** input purity (baseline == live
artifact minus generated_utc); visible strips exactly Barr+Sessions (CU),
Blumenthal+Durbin+Sanders+Warren (bank), Booker (crypto, no backfill pool);
backfills Finstad+Lucas (CU), Bennet+Ernst+Murray+Wyden (bank); Scott keeps
CU+crypto seats (crown path); threats + mixed boards byte-identical in all
sectors (adversary exclusion unchanged); 16 legitimate below-cap class-level
strips receipt-only (Gooden/Marshall/Welch/Kaptur et al. — never displayed);
totals 134→133 / 30 / 110; audit cross-check fires on baseline exactly 7,
clean on rule; rules.cross_sector present.

**Tests:** lda suite 242/0 (+4 pins). Kernel harness 144/6 — the same six
legislation/primacy environmental failures as every worktree run tonight
(crown-law pack tests_pre/tests_post carry the identical list; none reference
changed modules; first failure is the known worktree bill_directions.csv gap).
Negative control: pre-law producer + post-law tests exit 1 at the
_assert_boards signature boundary (TypeError, lda_negctl.txt); behavioral
fire-on-baseline proven at artifact level (E8a).

**Deploy notes:** the new audit ck reads RED on the live machine until the
chain regenerates boards.json. Next chain also flips efficiency's CU lens
membership fields (Barr/Sessions cu_board_present→false, Finstad/Lucas enter)
— intended consequence, adversary set untouched. Crown-yield fixture test is
belt-and-braces; the structural guarantee is that crowns never enter staged
threats, hence never the strip set.
