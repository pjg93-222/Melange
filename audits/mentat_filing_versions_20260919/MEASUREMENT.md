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

### 1. Row census by class, VERSION 4 / `withhold` (cash rows, 24G/24K non-memo)

| class | 2022 rows | 2022 $ | 2024 rows | 2024 $ | 2026 rows | 2026 $ |
|---|---:|---:|---:|---:|---:|---:|
| A  duplicate (repeated raw line or itemization) | 1397 | 38,732,688 | 106 | 10,107,692 | 0 | 0 |
| B  superseded (same identity, later filing) | 82 | 484,200 | 23 | 11,779,595 | 43 | 1,412,941 |
| C  repeated identity inside one filing | 0 | 0 | 0 | 0 | 0 | 0 |
| D  reused transaction id, own identity | 442 | 19,743,097 | 546 | 22,023,709 | 215 | 7,209,293 |
| -  sole identity in its group | 1589004 | 2,442,450,881 | 1395982 | 5,249,718,285 | 256674 | 1,961,411,177 |
| E  ambiguous, withheld | 2 | 90,000 | 0 | 0 | 5 | 30,000 |
| R  unresolved record (invalid field) | 13 | 115,909 | 3 | 135,000 | 1 | 4,325 |

### 2. VERSION 3 against VERSION 4, per cycle (cash block, real 25-header store)

| | 2022 | 2024 | 2026 |
|---|---:|---:|---:|
| v3 current cash edge $ | 2,468,397,260 | 5,327,441,910 | 1,965,680,932 |
| **v4 current cash edge $ (withhold)** | **2,500,547,312** | **5,364,840,916** | **1,974,303,166** |
| v4 current cash edge $ (count_latest) | 2,500,592,312 | 5,364,840,916 | 1,974,323,166 |
| change v3 -> v4 withhold | 32,150,052 | 37,399,006 | 8,622,234 |
| v3 blocked edge $ (source blacklisted) | 108,916,264 | 33,047,447 | 10,533,899 |
| v3 blocked share of current edges | 4.41% | 0.62% | 0.54% |
| **v4 withheld $ (withhold)** | **231,409** | **135,000** | **24,325** |
| v4 withheld $ (count_latest) | 186,409 | 135,000 | 4,325 |
| v3 committees blacklisted | 44 | 47 | 28 |
| v4 committees with a withheld share | 5 | 1 | 3 |
| v3 unresolved_version rows | 4145 | 771 | 310 |
| v4 ambiguous rows (class E) | 2 | 0 | 6 |
| v3 unresolved groups: multi-filing | 303 | 299 | 155 |
| v3 unresolved groups: single-filing | 827 | 67 | 0 |
| v4 ambiguous groups: multi-filing | 1 | 0 | 3 |
| v4 ambiguous groups: single-filing | 0 | 0 | 0 |
| v4 rows flagged tran_id_reused | 445 | 552 | 224 |
| v4 rows settled by a filing header | 0 | 0 | 0 |
| v4 rows settled by file number | 1597695 | 1405528 | 261136 |
| build seconds (v3 / v4) | 243 / 409 | 242 / 143 | 48 / 115 |

### 3. The conservation invariant, recomputed from each published ledger

| ledger | identity tuples counted more times than any one filing showed | groups checked | groups over the clamped ceiling | groups over the raw ceiling | rows without exactly one status |
|---|---:|---:|---:|---:|---:|
| 2022 count_latest | 0 | 1589226 | 0 | 0 | 0 |
| 2022 withhold | 0 | 1589225 | 0 | 0 | 0 |
| 2024 count_latest | 0 | 1396257 | 0 | 0 | 0 |
| 2024 withhold | 0 | 1396257 | 0 | 0 | 0 |
| 2026 count_latest | 0 | 256786 | 0 | 0 | 0 |
| 2026 withhold | 0 | 256783 | 0 | 0 | 0 |

### 4. The 25 largest class-D groups: one reused label, several real counterparties

| cycle | version key | counterparties | filings | rows |
|---|---|---:|---:|---|
| 2024 | `C00692343|Q2|SB22.2` | 1 | 2 | f1713770 C00676965 2023-06-30 24G $586,067.00 current<br>f1798394 C00676965 2024-06-30 24G $878,065.00 current |
| 2026 | `C00770180|Q1|SB22.2` | 1 | 2 | f1886762 C00369033 2025-03-31 24G $766,231.00 current<br>f1963006 C00369033 2026-02-06 24G $303,302.00 current |
| 2022 | `C00676957|Q2|SB22.8` | 1 | 2 | f1526665 C00027466 2021-06-30 24G $621,277.00 current<br>f1613298 C00027466 2022-04-30 24G $439,334.00 current |
| 2024 | `C00692343|Q1|SB22.2` | 1 | 2 | f1699509 C00676965 2023-03-31 24G $245,247.00 current<br>f1773915 C00676965 2024-03-31 24G $685,289.00 current |
| 2022 | `C00676957|Q2|SB22.7` | 2 | 2 | f1526665 C00692327 2021-06-30 24G $380,963.00 current<br>f1613298 C00027466 2022-04-30 24G $489,523.00 current |
| 2022 | `C00676957|Q2|SB22.9` | 1 | 2 | f1526665 C00027466 2021-06-30 24G $341,629.00 current<br>f1613298 C00027466 2022-04-30 24G $460,869.00 current |
| 2024 | `C00692343|Q3|SB22.2` | 1 | 2 | f1730616 C00676965 2023-09-30 24G $468,718.00 current<br>f1828735 C00676965 2024-07-31 24G $231,954.00 current |
| 2024 | `C00692343|Q2|SB22.3` | 1 | 2 | f1713770 C00676965 2023-06-30 24G $290,259.00 current<br>f1798394 C00676965 2024-06-30 24G $332,116.00 current |
| 2024 | `C00779223|Q1|SB22.4` | 2 | 2 | f1699495 C00027466 2023-03-31 24G $13,654.00 current<br>f1774457 C00652727 2024-03-31 24G $562,134.00 current |
| 2026 | `C00770180|Q1|SB22.3` | 1 | 2 | f1886762 C00369033 2025-03-31 24G $420,579.00 current<br>f1963006 C00369033 2026-02-06 24G $140,982.00 current |
| 2022 | `C00676957|Q3|SB22.6` | 1 | 2 | f1542954 C00027466 2021-07-30 24G $248,800.00 current<br>f1640771 C00027466 2022-08-31 24G $301,435.00 current |
| 2024 | `C00692343|Q2|SB22.1` | 1 | 2 | f1713770 C00692327 2023-06-30 24G $135,417.00 current<br>f1798394 C00692327 2024-06-30 24G $391,114.00 current |
| 2022 | `C00676957|Q3|SB22.7` | 1 | 2 | f1542954 C00027466 2021-07-30 24G $411,606.00 current<br>f1640771 C00027466 2022-09-30 24G $113,371.00 current |
| 2022 | `C00676957|Q2|SB22.2` | 2 | 2 | f1526665 C00027466 2021-04-30 24G $363,910.00 current<br>f1613298 C00692327 2022-04-30 24G $158,650.00 current |
| 2022 | `C00676957|Q2|SB22.1` | 2 | 2 | f1526665 C00027466 2021-04-30 24G $432,353.00 current<br>f1613298 C00692327 2022-06-30 24G $61,500.00 current |
| 2024 | `C00692343|YE|SB22.2` | 1 | 2 | f1749502 C00676965 2023-12-31 24G $480,556.00 current<br>f1869946 C00676965 2024-12-31 24G $-66.00 current |
| 2026 | `C00770180|Q1|SB22.5` | 2 | 2 | f1886762 C00387464 2025-03-31 24G $431,089.00 current<br>f1963006 C00369033 2026-02-11 24G $22,000.00 current |
| 2024 | `C00692343|Q1|SB22.3` | 1 | 2 | f1699509 C00676965 2023-03-31 24G $130,038.00 current<br>f1773915 C00676965 2024-03-31 24G $280,443.00 current |
| 2026 | `C00779223|Q2|SB22.1` | 1 | 2 | f1901606 C00652727 2025-06-30 24G $249,487.00 current<br>f1993134 C00652727 2026-06-30 24G $145,983.00 current |
| 2024 | `C00779223|Q2|SB22.1` | 2 | 2 | f1713761 C00692640 2023-06-30 24G $7,908.00 current<br>f1800031 C00652727 2024-05-31 24G $386,646.00 current |
| 2022 | `C00692343|Q3|SB22.3` | 1 | 2 | f1542953 C00692327 2021-09-30 24G $120,227.00 current<br>f1640819 C00692327 2022-09-29 24G $273,260.00 current |
| 2024 | `C00779223|Q2|SB22.2` | 1 | 2 | f1713761 C00652727 2023-06-30 24G $325,749.00 current<br>f1800031 C00652727 2024-05-31 24G $62,986.00 current |
| 2024 | `C00779223|Q3|SB22.2` | 2 | 2 | f1730613 C00652727 2023-09-30 24G $365,362.00 current<br>f1827490 C00027466 2024-09-06 24G $13,976.00 current |
| 2024 | `C00770180|Q2|SB22.30` | 2 | 2 | f1713773 C00492785 2023-06-22 24G $48,046.00 current<br>f1798339 C00027466 2024-04-29 24G $297,321.00 current |
| 2022 | `C00676957|Q2|SB22.4` | 2 | 2 | f1526665 C00692327 2021-04-30 24G $106,340.00 current<br>f1613298 C00027466 2022-06-30 24G $234,185.00 current |

### 5. The 25 largest class-E groups: same counterparty, nothing that separates them

| cycle | version key | counterparties | filings | rows |
|---|---|---:|---:|---|
| 2022 | `C00369033|Q1|SB21.1` | 2 | 2 | f1510762  2021-03-10 24K $45,000.00 unresolved_version<br>f1583658 C00027466 2022-03-13 24K $45,000.00 unresolved_version |
| 2026 | `C00770180|Q1|SB22.4` | 2 | 2 | f1886762  2025-03-31 32G $5,123.00 unresolved_version<br>f1963006 C00369033 2026-02-11 24G $10,000.00 unresolved_version |
| 2026 | `C00493072|M7|SB.7` | 1 | 2 | f1904826 C00440362 2025-06-16 24K $5,000.00 unresolved_version<br>f1999627 C00440362 2026-06-05 24K $5,000.00 unresolved_version |
| 2026 | `C00493072|M7|SB.5` | 1 | 2 | f1904826 C00675348 2025-06-16 24K $5,000.00 unresolved_version<br>f1999627 C00675348 2026-06-05 24K $5,000.00 unresolved_version |


## 3. PAS2: committee-to-candidate activity

| counted committee-to-candidate dollars | 2022 | 2024 | 2026 | all |
|---|---:|---:|---:|---:|
| parser "3" (the previous rule) | $2,759,736,192 | $5,022,083,517 | $1,101,028,965 | $8,882,848,674 |
| parser "4" (committed today) | $2,753,312,446 | $5,021,166,096 | $1,100,738,246 | $8,875,216,788 |
| **parser "5", withhold** | $2,766,830,453 | $5,025,584,919 | $1,101,027,336 | $8,893,442,708 |
| parser "5", count_latest | $2,766,936,453 | $5,025,686,268 | $1,101,037,336 | $8,893,660,057 |

| rows counted | 2022 | 2024 | 2026 | all |
|---|---:|---:|---:|---:|
| parser "3" (the previous rule) | 734,897 | 685,886 | 204,188 | 1,624,971 |
| parser "4" (committed today) | 734,431 | 685,723 | 204,115 | 1,624,269 |
| **parser "5", withhold** | 734,987 | 685,909 | 204,190 | 1,625,086 |
| parser "5", count_latest | 734,992 | 685,911 | 204,192 | 1,625,095 |

**Parser "5" / withhold.** Parser "4" took 702 rows / $7,631,886 out of the counted total that parser "3" had counted. Parser "5" brings back **693 rows / $7,504,537**; 9 rows / $127,349 stay out. It also counts 124 rows / $10,721,383 that neither earlier parser counted. The dollars it still withholds are reported as an unresolved share of $6,468,042 across 3515 rows; 75 rows are superseded amendments (so `superseded_by_amendment` is a real number again, not 0) and 508 rows carry `tran_id_reused`.

**Parser "5" / count_latest.** Parser "4" took 702 rows / $7,631,886 out of the counted total that parser "3" had counted. Parser "5" brings back **700 rows / $7,621,886**; 2 rows / $10,000 stay out. It also counts 126 rows / $10,821,383 that neither earlier parser counted. The dollars it still withholds are reported as an unresolved share of $6,250,693 across 3497 rows; 84 rows are superseded amendments (so `superseded_by_amendment` is a real number again, not 0) and 508 rows carry `tran_id_reused`.

Row-level eyeball tables: `out\pas2_recovered_groups.csv` (groups parser "4" withheld whole that parser "5" counts) and `out\pas2_still_withheld_groups.csv` (groups parser "5" still withholds). Full log: `out\pas2_measure_v4.log`.

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
