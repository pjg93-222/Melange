# User-ratified primacy diagnostic, 2026-09-20

Paul selected the diagnostic twice ("I am rocking with the diagnostic"), then
authorized "Lets commit it, regenerate, and keep going." The adopted arm is
`CLASS_DOCK_PRESS_GRADE_ALL` with within-chamber seating. This promotes that
specific mechanism, not an instruction to pin selected members to desired seats.

The additional uncertainty dock defaults to zero. Ordinary shrinkage toward the
roster baseline with anchor 15 remains. Legislative grade contributions retain
their existing routed sign, role weight and tensor multiplier, multiplied by
beneficiary magnitude: CU-primary 1, shared .5, bank/crypto/fintech .15, off-topic
0, oppose 1. Oppose is a magnitude because routed actions already carry a sign.
Unclassified acts contribute zero and are counted in the grade receipt. Votes,
annualization, the 80/20 legislative/press split, chamber normalization, evidence
floors, conduct cap and adjudicated credits retain their existing rules.

Press is signed CU-weighted intensity divided by ALL admitted statement intensity.
Media class weights are CU-direct 1, shared .5, other-industry 0 and off-topic 0.
Both numerator and denominator are rounded to nine decimals before division,
matching the reviewed diagnostic. The five-observed-item gate remains. Repeated
source IDs retain separate occurrence IDs so admitted crossposts are preserved.

## Classified media input

`fec/config/primacy_press_v1.ndjson` is the complete adopted 7,413-item classified
historical vintage covering 483 members. Its adjacent JSON receipt binds its
bytes, source hashes, counts and policies. The loader validates the receipt,
identities, occurrence uniqueness, classes, directions and positive finite mass;
missing or invalid evidence fails loudly. `.gitattributes` preserves ledger LF
bytes across Windows checkouts. The grade hashes both files in its own receipt.

This is not a continuously refreshed press corpus. Association articles and
crossposts are included, time decay is absent, and neutral/unclassified new items
are absent. These limitations are retained from the selected diagnostic and
embedded in the generated policy. A future corpus refresh needs a complete
classified generation and review; it must not silently relabel new speech or
turn missing labels into neutral evidence. Full text remains in the original
audit corpus; the committed ledger retains source URLs and text hashes.
`fec/tools/import_primacy_press.py --packet <audit packet> --output-root <staging>`
rebuilds this vintage and refuses to write unless every approved aggregate matches.

ACU champion annotations are an external comparison, not an input to scoring.
Paul's judgment that Barr and Daines are not champions remains distinct from
ACU's published characterizations. No new member override was introduced.

## Verification and rollback

On the frozen 2026-09-19 input vintage, the actual producers and `tier_util`
reproduce all 533 approved seats, tiers and grade percentiles exactly. The media
ledger independently reproduces all 483 amended member aggregates exactly.
`PRIMACY_METHOD=legacy` reproduces both pre-change producer artifacts
byte-for-byte and all 533 old seats. To roll back, set this variable and regenerate
the full chain; changing only `PRIMACY_BOARD` is not this paired-method rollback.
Explicit existing environment overrides still apply and should be cleared when
comparing default methods.

The approved Tier 1 order is Padilla, Gonzalez, Waters, Fitzpatrick, Sherman,
Vargas, Tim Scott, Timmons, Fitzgerald, Huizenga, Young Kim, Cramer, Ciscomani.
Barr ranks 15 before the existing conduct rule and 38 after it; Daines ranks 29.
The diagnostic changes 511 board ranks and 29 tiers versus the prior live board.
Exact before/after rows and full-chain receipts accompany this adoption.

## Remaining audit work

The immediate next methodological questions are neutral/unclassified media
coverage, association-article attribution, signed vote semantics and amendment
treatment in the grade. These are explicit follow-up questions, not components
silently added to this promotion. Seating alternatives were compared in the
original audit; within-chamber seating is the adopted baseline.
