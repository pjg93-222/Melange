# Primacy → Efficiency → Substance → Volume

The corrected candidate is implemented and replayed against the frozen 118th- and 119th-Congress evidence. **Institutional power adds no tier points.** Sponsor/original/later-cosponsor roles and joining-time discounts are included in legislative credit.

Open the [interactive comparison](generation_03/review.html) or the [readable run report](generation_03/report.md). The [scoring contract](SCORING_CONTRACT.md) gives the exact formulas and missing-data rules.

| Final comparison | 118th | 119th |
|---|---:|---:|
| Displayed members | 533 | 533 |
| Available progressive efficiency | 428 | 459 |
| Unavailable efficiency | 105 | 74 |
| Available mean substance | 426 | 458 |
| Changed ranks | 149 | 138 |
| Changed tier memberships | 0 | 0 |

All 13 existing Tier-1 members remain in Tier 1. Strict primacy precedence means that later criteria only resolve exact ties in preceding criteria; they cannot compensate for lower primacy. Existing evidence, conduct and seat rules still apply.

What changed from the earlier P/E/V run:

- Restored the original five-stage progressive efficiency specification. The previous fixed-window conversion rate no longer determines E.
- Added Substance before Volume, using average importance so activity quantity does not masquerade as more substantive work.
- Applied role weights and the introduction-to-first-join discount once to each credited engagement or milestone. Withdrawal blocks later stage credit; rejoining does not reset timing.
- Retained the full chamber universe and recomputed tensor E percentiles. No standard-channel success percentile is reused.
- Excluded the five documented 119th House reserved-number placeholders in a receipted derived view. Preserved actual official pre-introduction hearings and a valid closing-day 118th bill.
- Verified the consumed bill, impact, role, roster and signal files against their frozen generation manifest before scoring.

**Substance remains provisional:** every selected measure currently has recorded weight 5. Observed mean substance is therefore exactly 5 and cannot distinguish members. No significance classification is invented from incomplete publication coverage. The 180-day cosponsor half-life is the source's illustrative setting, not an empirically optimized estimate.

Validation: **69 tests passed**; the 533-member baseline reproduced exactly; all final gates passed; source hashes were unchanged. Generations 03 and 04 have byte-identical board data, contribution ledgers, HTML and reports. See the [validation receipt](VALIDATION_RECEIPT.json), [test log](validation_tests.log), and [independent review](INDEPENDENT_REVIEW.md).

The HTML's embedded data, control IDs, injection handling and JavaScript syntax were checked. Automatic interactive browser verification was blocked by the browser's local-URL policy; no workaround was used.

**Production remains unchanged.** This package delivers the executable candidate and its comparison. It does not claim live consumer integration or a full production pipeline verification.

## Reproduce

```powershell
$pesvPython = 'C:\Users\pgoff\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $pesvPython -I -B -m unittest discover -s 'C:\Users\pgoff\Mentat\outputs\pesv_implementation_20260913\tests' -v
& $pesvPython -I -B 'C:\Users\pgoff\Mentat\outputs\pesv_implementation_20260913\src\replay_pesv.py' --source-root 'C:\Users\pgoff\OneDrive\Desktop\Melange Systems' --shadow-root 'C:\Users\pgoff\AppData\Local\Melange\legislative_effectiveness\shadow_20260912' --output-root 'C:\Users\pgoff\Mentat\outputs\pesv_implementation_20260913\generation_new' --congress 118 119 --as-of 2026-09-06
```

Use a new output directory for every replay. The default half-life can be explicitly supplied with `--cosponsor-half-life-days 180`. Generations 01 and 02 are retained intermediate runs; use 03 or its identical repeat 04 for the final corrected comparison.

Files: [pure engine](src/pesv.py), [replay runner](src/replay_pesv.py), [report builder](src/reporting.py), [core tests](tests/test_pesv.py), [adapter tests](tests/test_replay.py), and [contribution ledger](generation_03/contributions.ndjson).
