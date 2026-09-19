# VERSION 4 / parser "5": what the identity rule changes, measured

Everything here was produced in a scratch copy of the committed project
(`git archive` of `C:\Users\pgoff\Mentat` HEAD `236a420581298abd096d8549ec4bdb53f1328629`).
Nothing was written under `C:\Users\pgoff\Mentat`; the FEC source files were read
through hard links, and their bytes and mtimes are unchanged.

## 0. What is being compared

- **VERSION 3 / parser "4"** is the committed rule: every set of rows sharing
  `committee | report_type | transaction_id` is treated as competing versions of
  one transaction and withheld unless a verified filing header settles the
  family. Its numbers come from the earlier measurement kit
  (`...\v3_measure\out\block*-headers.json`) over the same cash blocks and the
  same real 25-header store.
- **VERSION 4 / parser "5"** is the candidate. Inside the same group, a row's
  identity is its counterparty, amount in cents, transaction date and
  transaction type. `AMBIGUOUS_VERSION_POLICY` selects the treatment of the
  ambiguous remainder: `withhold` (today's) or `count_latest`.
- The OTH figures are measured on the **cash blocks** (`block22/24/26`): the
  contiguous tail of each real `itoth.txt` that holds every 24G/24K row in the
  file. The PAS2 figures are measured on the **whole** real `itpas2.txt` files,
  reparsed by the patched `fec_build_pas2_index()`.

## 1. One deviation from the rule as specified, and why

The rule as handed to me said class C -- the same identity several times inside
ONE filing -- is several itemized transactions, and all of them count. **That is
wrong on this data and I did not build it.**

`class_c_census.py` takes every identity that appears more than once inside a
single filing, strips the SUB_ID field from each raw line and compares the rest.
Run against the published v4 ledgers for all three cash blocks:

| | 2022 | 2024 | 2026 | all |
|---|---:|---:|---:|---:|
| groups byte-identical apart from SUB_ID | **826** | **66** | 0 | **892** |
| rows beyond the first in those groups | 2,710 | 104 | 0 | 2,814 |
| cash dollars those extra rows carry | **$38,731,688** | **$10,105,692** | $0 | **$48,837,380** |
| groups that differ anywhere else | 1 | 1 | 0 | 2 |
| cash dollars in those | $1,000 | $2,000 | $0 | $3,000 |

The two exceptions differ only in `amendment_indicator` (`N` vs `A`) inside the
same filing number, so they are the same itemization too. A worked case:

    C00010603|A|M11|G2021|202203149493887866|24G|PTY|DEMOCRATIC PARTY OF VIRGINIA|...|10182021|1480000|C00155952|500129245|1573863|||4031920221461876813
    C00010603|A|M11|G2021|202203149493887866|24G|PTY|DEMOCRATIC PARTY OF VIRGINIA|...|10182021|1480000|C00155952|500129245|1573863|||4031920221461899900
    ... three more, identical, SUB_ID 4031920221461899901/902/903

Same filing, same image number, same transaction id, same $1,480,000. Counting
all five books $7.4M for one transfer.

So v4 keeps ONE row per identity per filing and marks the rest `duplicate` /
"Repeated itemization in one filing". **Two genuine equal gifts are unaffected**:
the group is keyed by the filer's own transaction id, so two real gifts carry two
transaction ids, land in two different groups, and are both counted. A test pins
exactly that (`test_two_genuine_equal_gifts_on_one_day_are_both_counted`).

Class E was also read slightly wider than the letter of the spec. The spec said
the ambiguous remainder is "same counterparty and type, different amount or
date". Taken literally, a cross-filing *type* change (24K restated as 24Z) or a
destination blanked by an amendment would become two separate transactions and
be counted twice. v4 instead treats two surviving identities in different filings
as ambiguous unless two *valid, different* committee ids tell them apart. That
keeps the committed behaviour that a reclassification requires filing evidence
(`test_reclassification_and_new_year_amendment_require_filing_evidence`, and
`test_a_cross_filing_type_change_is_not_counted_as_a_second_transaction`).

## 2. Tables

<!--TABLES-->

## 3. PAS2: committee-to-candidate activity

<!--PAS2-->

## 4. How to reproduce

```powershell
$s = '<scratch>\v4_rule'
$hd = 'C:\Users\pgoff\Mentat\mentat\state\cross-reference\filing-headers'
$env:PYTHONDONTWRITEBYTECODE = '1'
python "$s\measure_transfer_v4.py" --cycle 2022 --policy withhold `
    --itoth "$s\block22\itoth.txt" --header-dir $hd --out "$s\out\v4-2022-withhold.json"
python "$s\invariant_check.py"  $s          # the sign-safe invariant, off the ledgers
python "$s\class_c_census.py"   "$s\block22" "$s\block24" "$s\block26"
& "C:\Program Files\R\R-4.6.0\bin\Rscript.exe" "$s\pas2_measure_v4.R"
python "$s\assemble_measurement.py" $s      # rebuilds the tables above
```

A built index is cached, so re-reading a result costs a few seconds. The cache
key is source content + header set + VERSION + policy, **not** the code: after
changing the rule, delete `<scratch>\block2*\transfer-index-v4*` before
re-measuring.
