# Bill Archive Congress.gov Query Provenance

## Provenance statement

- Producer: **manual Congress.gov API-browser**.
- Statement: Paul, 2026-07-25.
- There is not and never was a producer script.
- Recovery scope: query specification only. No data row was invented, re-fetched, or modified.
- API-browser signature: **one hand-built query per category, pasted across its result rows**.

Source scratch copy: `congress_bills_archive_20260624_115822.xlsx`  
SHA-256: `4ca1c81af641a2e255ab54cd78dc4c8eb43aa7d2c156893c753cdbe4faa05a73`  
Bytes: `1832697`

## Recovery method and count definitions

Every nonblank `DetailLink` is inspected for an `hl=` parameter. The parameter is validated, URL-decoded, and lexed into quoted phrases, bare terms, and operators. Repeated full queries across rows are provenance, not duplication errors.

- **Distinct full queries:** unique complete decoded `hl` strings.
- **Query atoms:** each quoted phrase, bare term, or operator counts once.
- **Whitespace tokens:** `len(decoded_query.split())`; this is the audit’s historical 17–72 measure.

Quoted phrases are checked only against `Title + bill_summary` rows in their own sheet. `SUSPECT-ZERO-YIELD` means zero yield in this artifact, not a claim about current Congress.gov results.

## 8,520 reconciliation

| View | Rows | Non-empty hl | Decodable hl | Missing/empty | Malformed | Delta vs 8,520 |
|---|---:|---:|---:|---:|---:|---:|
| All Bills | 10986 | 8520 | 8520 | 2466 | 0 | +0 |
| Numbered sheets | 10986 | 8520 | 8520 | 2466 | 0 | +0 |

The two rows above are duplicate workbook views of the same archive records. Their physical-cell sum is not the audit denominator.

## Per-sheet summary

| Sheet | Category | Rows | Decodable | Missing/empty | Malformed | Distinct full queries | Atom counts | Whitespace-token counts | Suspects |
|---|---|---:|---:|---:|---:|---:|---|---|---:|
| All Bills | mixed / none | 10986 | 8520 | 2466 | 0 | 16 | deduplicated set [1, 15, 17, 19, 20, 22, 24, 25, 26, 27, 30, 34, 37, 44] | deduplicated set [4, 17, 19, 21, 24, 31, 32, 37, 39, 42, 43, 45, 52, 66, 72] | 37 |
| 01 Examination & Supervision | Examination & Supervision | 674 | 436 | 238 | 0 | 1 | [44] | [66] | 6 |
| 02 Credit Union Capital Require | CU Capital Requirements | 618 | 387 | 231 | 0 | 1 | [17] | [17] | 0 |
| 03 NCUA Budget & Share Insuranc | NCUA Budget & Insurance | 713 | 473 | 240 | 0 | 1 | [25] | [32] | 0 |
| 04 Interchange | Interchange | 36 | 20 | 16 | 0 | 1 | [1] | [4] | 0 |
| 05 Payments | Payments | 34 | 10 | 24 | 0 | 1 | [22] | [37] | 11 |
| 06 Technology & Emerging Issues | Technology & Emerging | 877 | 678 | 199 | 0 | 1 | [30] | [45] | 4 |
| 07 Fraud Prevention | Fraud Prevention | 1123 | 896 | 227 | 0 | 1 | [26] | [42] | 5 |
| 08 Data Privacy & Cybersecurity | Data Privacy & Cyber | 966 | 681 | 285 | 0 | 1 | [24] | [31] | 1 |
| 09 Charter Modernization & Gove | Charter Modernization | 639 | 456 | 183 | 0 | 1 | [19] | [31] | 0 |
| 10 Defense Credit Union Issues | Defense CU Issues | 49 | 6 | 43 | 0 | 1 | [15] | [19] | 2 |
| 11 Field of Membership | Field of Membership | 41 | 13 | 28 | 0 | 1 | [17] | [21] | 2 |
| 12 CDFI Fund | CDFI Fund | 0 | 0 | 0 | 0 | 0 | [] | [] | 0 |
| 13 CFPB Issues & Structural Ref | CFPB | 635 | 503 | 132 | 0 | 1 | [37] | [72] | 2 |
| 14 Credit Card & Consumer-Fee M | Credit Card Mandates | 146 | 54 | 92 | 0 | 1 | [24] | [39] | 1 |
| 15 Telephone Consumer Protectio | TCPA | 165 | 88 | 77 | 0 | 1 | [20] | [24] | 1 |
| 16 Member Business Lending | Member Business Lending | 2665 | 2452 | 213 | 0 | 1 | [27] | [52] | 1 |
| 17 Mortgage Lending & Housing | Mortgage & Housing | 1605 | 1367 | 238 | 0 | 1 | [34] | [43] | 2 |

## Never-configured category evidence

- Numbered archive sheets are `contiguous 01..17`.
- `12 CDFI Fund` has zero data rows and no query set.
- No `CU Tax Status` numbered sheet or query set exists.
- Documented-known missing query sets: CDFI Fund, CU Tax Status.

## Per-sheet query catalog

### All Bills

Rows: 10986; distinct full queries cataloged: 16; missing/empty hl rows: 2466; malformed hl rows: 0; decoded-hl truncations: 0; query-catalog status: COMPLETE; overflow rows: 0.

**Query 1** — 20 rows; Excel rows 2007-2008, 2010-2011, 2015-2016, 2018-2019, 2021-2022, 2028-2029, 2034-2035, 2037-2042

```text
"Credit\ Card\ Competition\ Act"
```

- Query atoms: 1
- Whitespace tokens: 4
- Catalog status: COMPLETE
- Quoted phrases: `Credit Card Competition Act`
- Bare terms: none
- Operators: none

**Query 2** — 10 rows; Excel rows 2045-2046, 2050-2051, 2054-2055, 2064-2065, 2067-2068

```text
"FedNow" "real\-time\ payments" "install\ payment\ fund" ACH payment faster payments credit union "same\-day\ ACH" "automated\ clearing\ house" "faster\ payments" "open\ banking" earned wage access "payment\ system\ access" "instant\ payment" master account "buy\ now\ pay\ later" "Regulation\ E"
```

- Query atoms: 22
- Whitespace tokens: 37
- Catalog status: COMPLETE
- Quoted phrases: `FedNow`, `real-time payments`, `install payment fund`, `same-day ACH`, `automated clearing house`, `faster payments`, `open banking`, `payment system access`, `instant payment`, `buy now pay later`, `Regulation E`
- Bare terms: `ACH`, `payment`, `faster`, `payments`, `credit`, `union`, `earned`, `wage`, `access`, `master`, `account`
- Operators: none

**Query 3** — 88 rows; Excel rows 6554-6556, 6558-6559, 6563-6564, 6566-6567, 6569-6575, 6577-6578, 6585-6586, 6593-6595, 6597-6604, 6608-6609, 6612-6615, 6617-6620, 6622-6625, 6627-6629, 6632-6634, 6640-6641, 6643-6645, 6649-6650, 6652-6655, 6658-6659, 6665-6666, 6668-6669, 6674-6680, 6682-6683, 6685-6686, 6691-6694, 6696-6698, 6712-6713

```text
"Telephone\ Consumer\ Protection\ Act" TCPA FCC credit union Federal Communications Communication Commission robocall financial institution "autodialer\ consent" Prior express consent Telephone Consumer Protection Act
```

- Query atoms: 20
- Whitespace tokens: 24
- Catalog status: COMPLETE
- Quoted phrases: `Telephone Consumer Protection Act`, `autodialer consent`
- Bare terms: `TCPA`, `FCC`, `credit`, `union`, `Federal`, `Communications`, `Communication`, `Commission`, `robocall`, `financial`, `institution`, `Prior`, `express`, `consent`, `Telephone`, `Consumer`, `Protection`, `Act`
- Operators: none

**Query 4** — 2452 rows; Excel rows 6719-6729, 6731-6732, 6734-6737, 6740-6745, 6750-6758, 6760-6768, 6771-6773, 6776-6778, 6781-6786, 6789-6795, 6797-6798, 6801-6807, 6809-6814, 6816-6819, 6821-6847, 6849-6850, 6852-6860, 6864-6869, 6871-6880, 6882-6888, 6890-6899, 6901-6902, 6904-6906, 6911-6921, 6923-6924, 6926-6927, 6929-6934, 6937-6939, 6941-6945, 6947-6960, 6962-7000, 7004-7009, 7012-7020, 7022-7041, 7043-7044, 7046-7051, 7053-7060, 7063-7068, 7070-7079, 7082-7083, 7086-7096, 7098-7099, 7101-7117, 7119-7126, 7128-7130, 7134-7135, 7137-7146, 7149-7150, 7153-7156, 7158-7176, 7178-7179, 7182-7190, 7192-7198, 7200-7209, 7213-7214, 7216-7223, 7227-7230, 7232-7250, 7252-7253, 7255-7258, 7261-7264, 7266-7276, 7278-7281, 7283-7285, 7287-7299, 7302-7309, 7311-7316, 7321-7324, 7326-7328, 7330-7331, 7335-7338, 7342-7359, 7361-7371, 7373-7386, 7389-7422, 7429-7438, 7443-7446, 7449-7461, 7464-7470, 7472-7485, 7487-7493, 7495-7505, 7508-7510, 7512-7517, 7519-7521, 7523-7531, 7533-7560, 7563-7585, 7587-7650, 7652-7670, 7672-7680, 7682-7704, 7706-7794, 7797-7809, 7812-7852, 7854-7855, 7857-7864, 7866-7976, 7978-7997, 7999-8031, 8033-8057, 8059-8124, 8126-8148, 8150-8172, 8174-8209, 8211-8226, 8228-8234, 8236-8292, 8294-8305, 8307-8313, 8316-8317, 8319-8371, 8374-8406, 8408-8441, 8443-8473, 8475-8505, 8507-8530, 8533-8573, 8577-8584, 8586-8592, 8594-8615, 8618-8622, 8624-8630, 8632-8649, 8651-8706, 8709-8717, 8719-8789, 8792-8793, 8795-8830, 8832-8856, 8858-8946, 8949-8961, 8963-9045, 9047-9063, 9065-9075, 9077-9113, 9115-9126, 9128-9142, 9144-9165, 9168-9189, 9191-9230, 9232-9258, 9260-9261, 9263-9266, 9269-9315, 9318-9320, 9322-9382

```text
"de\ minimis\ threshold" credit union lending member business loan exempt MBL veteran increase maximum maturity cap 12.25% asset 12.25 percent threshold commercial SBA 7(a) limit "Veterans\ Member\ Business\ Loan\ Act" "Increasing\ Credit\ Union\ Lending\ for\ Business\ Growth\ Act" "Expanding Access to Lending Options Act" "Protecting Access to Credit for Small Businesses Act"
```

- Query atoms: 27
- Whitespace tokens: 52
- Catalog status: COMPLETE
- Quoted phrases: `de minimis threshold`, `Veterans Member Business Loan Act`, `Increasing Credit Union Lending for Business Growth Act`, `Expanding Access to Lending Options Act`, `Protecting Access to Credit for Small Businesses Act`
- Bare terms: `credit`, `union`, `lending`, `member`, `business`, `loan`, `exempt`, `MBL`, `veteran`, `increase`, `maximum`, `maturity`, `cap`, `12.25%`, `asset`, `12.25`, `percent`, `threshold`, `commercial`, `SBA`, `7(a)`, `limit`
- Operators: none

**Query 5** — 503 rows; Excel rows 5772-5773, 5775-5782, 5785-5786, 5790-5799, 5805-5806, 5809-5810, 5812-5834, 5838-5850, 5854-5864, 5866-5883, 5887-5895, 5903-5907, 5909-5914, 5916-5917, 5919-5923, 5929-5931, 5934-5938, 5940-5948, 5954-5965, 5968-5972, 5975-5976, 5978-5982, 5984-5985, 5987-5993, 5995-6000, 6002-6028, 6031-6038, 6040-6047, 6049-6060, 6062-6070, 6072-6073, 6075-6091, 6094-6112, 6116-6120, 6123-6140, 6142-6143, 6151-6163, 6165-6166, 6168-6169, 6176-6179, 6182-6183, 6185-6189, 6193-6201, 6204-6205, 6207-6209, 6211-6215, 6219-6222, 6227-6232, 6234-6235, 6237-6247, 6249-6251, 6253-6258, 6261-6282, 6290-6304, 6308-6309, 6312-6321, 6324-6325, 6327-6328, 6330-6338, 6340-6349, 6353-6359, 6362-6384, 6386-6406

```text
CFPB reform Consumer Financial Protection Bureau governance structure funding "Consumer\ Financial\ Protection\ Bureau\ funding\ structure" council commission congressional approrpriation cost-benefit analysis analysi CFBP appropriation abusive standard Dodd-Frank Section 1071 small business data "UDAAP" "unfair\ deceptive\ abusive\ acts\ practice" "Transparency\ in\ CFPB\ Cost\-Benefit\ Analysis\ Act" "Bureau\ of\ Consumer\ Financial\ Protection\ Commission\ Act" "Rectifying\ UDAAP\ Act" "TABS\ Act" "1071 Repeal to Protect Small Business Lending Act" "Business\ of\ Insurance\ Regulatory\ Reform\ Act" overdraft rule
```

- Query atoms: 37
- Whitespace tokens: 72
- Catalog status: COMPLETE
- Quoted phrases: `Consumer Financial Protection Bureau funding structure`, `UDAAP`, `unfair deceptive abusive acts practice`, `Transparency in CFPB Cost-Benefit Analysis Act`, `Bureau of Consumer Financial Protection Commission Act`, `Rectifying UDAAP Act`, `TABS Act`, `1071 Repeal to Protect Small Business Lending Act`, `Business of Insurance Regulatory Reform Act`
- Bare terms: `CFPB`, `reform`, `Consumer`, `Financial`, `Protection`, `Bureau`, `governance`, `structure`, `funding`, `council`, `commission`, `congressional`, `approrpriation`, `cost-benefit`, `analysis`, `analysi`, `CFBP`, `appropriation`, `abusive`, `standard`, `Dodd-Frank`, `Section`, `1071`, `small`, `business`, `data`, `overdraft`, `rule`
- Operators: none

**Query 6** — 678 rows; Excel rows 2077-2080, 2082-2084, 2087-2089, 2091-2092, 2094-2095, 2097-2098, 2101-2104, 2106-2117, 2122-2132, 2135-2138, 2142-2144, 2147-2148, 2152-2155, 2157-2162, 2166-2167, 2173-2175, 2177-2179, 2183-2184, 2186-2187, 2191-2192, 2195-2197, 2201-2202, 2204-2213, 2217-2223, 2229-2230, 2237-2238, 2241-2246, 2252-2253, 2255-2263, 2271-2276, 2279-2280, 2283-2287, 2290-2291, 2293-2294, 2296-2297, 2299-2313, 2316-2322, 2326-2327, 2333-2338, 2340-2341, 2343-2348, 2352-2360, 2363-2364, 2367-2380, 2382-2383, 2386-2402, 2404-2428, 2430-2445, 2447-2450, 2455-2471, 2475-2478, 2480-2481, 2483-2490, 2492-2493, 2496-2497, 2499-2502, 2504-2522, 2524-2526, 2528-2530, 2532-2541, 2543-2557, 2559-2560, 2562-2580, 2582-2594, 2596-2598, 2601-2602, 2604-2610, 2612-2613, 2618-2620, 2623-2625, 2629-2631, 2633-2636, 2640-2648, 2650-2651, 2653-2659, 2661-2667, 2669-2670, 2672-2674, 2676-2683, 2685-2688, 2690-2694, 2696-2697, 2702-2703, 2706-2707, 2711-2714, 2717-2718, 2720-2722, 2725-2739, 2742-2759, 2761-2776, 2778-2782, 2784-2794, 2796-2802, 2804-2813, 2815-2819, 2821-2826, 2828-2833, 2835-2841, 2843-2845, 2847-2853, 2856-2859, 2863-2873, 2875-2878, 2880-2892, 2895-2897, 2899-2913, 2916-2928, 2931-2937, 2939-2953

```text
central bank digital currency remote online notarization "CDBC" fintech partnership credit union NCUA overhead transfer rate "open\ banking" "AI\ lending\ model" "digital\ commodity" asset machine learning underwriting algorithmic decision "Anti\-CBDC\ Surveillance\ State\ Act" "Digital\ Asset\ Market\ Clarity\ Acy" "Secure\ Notarization\ Act" "Genius\ Act" "Stable\ Act"
```

- Query atoms: 30
- Whitespace tokens: 45
- Catalog status: COMPLETE
- Quoted phrases: `CDBC`, `open banking`, `AI lending model`, `digital commodity`, `Anti-CBDC Surveillance State Act`, `Digital Asset Market Clarity Acy`, `Secure Notarization Act`, `Genius Act`, `Stable Act`
- Bare terms: `central`, `bank`, `digital`, `currency`, `remote`, `online`, `notarization`, `fintech`, `partnership`, `credit`, `union`, `NCUA`, `overhead`, `transfer`, `rate`, `asset`, `machine`, `learning`, `underwriting`, `algorithmic`, `decision`
- Operators: none

**Query 7** — 54 rows; Excel rows 6411-6412, 6416-6417, 6425-6426, 6428-6430, 6434-6437, 6450-6451, 6453-6461, 6469-6470, 6477-6478, 6483-6492, 6500-6504, 6525-6528, 6534-6537, 6547-6549

```text
credit card rate cap car interest interchange limit overdraft fee lending rule late usury Truth in Lending Act junk financial institution "10\ Percent\ Credit\ Card\ Interest\ Rate\ Cap\ Act" "Credit\ Card\ Fairness\ Act" "Overdraft Lending: Very Large Financial Institutions"
```

- Query atoms: 24
- Whitespace tokens: 39
- Catalog status: COMPLETE
- Quoted phrases: `10 Percent Credit Card Interest Rate Cap Act`, `Credit Card Fairness Act`, `Overdraft Lending: Very Large Financial Institutions`
- Bare terms: `credit`, `card`, `rate`, `cap`, `car`, `interest`, `interchange`, `limit`, `overdraft`, `fee`, `lending`, `rule`, `late`, `usury`, `Truth`, `in`, `Lending`, `Act`, `junk`, `financial`, `institution`
- Operators: none

**Query 8** — 473 rows; Excel rows 1295-1303, 1306-1308, 1312-1320, 1323-1327, 1329-1330, 1338-1341, 1344-1345, 1347-1353, 1363-1365, 1369-1370, 1384-1385, 1405-1407, 1409-1414, 1425-1427, 1447-1448, 1451-1453, 1457-1458, 1461-1463, 1467-1473, 1475-1478, 1482-1490, 1492-1498, 1502-1503, 1506-1507, 1509-1519, 1521-1531, 1534-1540, 1543-1545, 1549-1555, 1557-1558, 1562-1566, 1569-1574, 1576-1578, 1581-1587, 1589-1590, 1592-1600, 1605-1608, 1610-1619, 1625-1626, 1633-1636, 1641-1644, 1647-1648, 1650-1653, 1655-1658, 1662-1663, 1667-1675, 1677-1680, 1683-1684, 1686-1691, 1693-1695, 1698-1700, 1702-1708, 1710-1712, 1714-1715, 1718-1723, 1726-1733, 1736-1737, 1739-1749, 1751-1777, 1781-1782, 1785-1787, 1789-1793, 1797-1798, 1800-1801, 1804-1806, 1808-1813, 1816-1819, 1823-1828, 1830-1831, 1833-1841, 1844-1846, 1849-1861, 1863-1864, 1866-1867, 1870-1872, 1874-1875, 1879-1880, 1882-1886, 1889-1897, 1899-1917, 1919-1927, 1929-1933, 1935-1939, 1941-1946, 1949-1955, 1958-1961, 1963-1969, 1973-1978, 1980-1982, 1984-1986, 1992-1995, 1997-2003

```text
credit union budget process National Credit Union Share Insurance Fund "Federal\ Credit\ Union\ Act" NCUA transparency overhead transfer rate equity ratio board "NCUA\ Central\ Liquidity\ Facility\ Enhancements" Central liquidity facility CLF SIF
```

- Query atoms: 25
- Whitespace tokens: 32
- Catalog status: COMPLETE
- Quoted phrases: `Federal Credit Union Act`, `NCUA Central Liquidity Facility Enhancements`
- Bare terms: `credit`, `union`, `budget`, `process`, `National`, `Credit`, `Union`, `Share`, `Insurance`, `Fund`, `NCUA`, `transparency`, `overhead`, `transfer`, `rate`, `equity`, `ratio`, `board`, `Central`, `liquidity`, `facility`, `CLF`, `SIF`
- Operators: none

**Query 9** — 13 rows; Excel rows 5733-5735, 5738-5739, 5741-5742, 5745-5748, 5769-5770

```text
credit union dual charter federal membership "field\ of\ membership" common bond multiple community underserved area state chartered "dual\ charter\ system" preemption
```

- Query atoms: 17
- Whitespace tokens: 21
- Catalog status: COMPLETE
- Quoted phrases: `field of membership`, `dual charter system`
- Bare terms: `credit`, `union`, `dual`, `charter`, `federal`, `membership`, `common`, `bond`, `multiple`, `community`, `underserved`, `area`, `state`, `chartered`, `preemption`
- Operators: none

**Query 10** — 1367 rows; Excel rows 9383-9391, 9394-9398, 9402-9408, 9410-9421, 9423-9428, 9431-9434, 9440-9441, 9446-9447, 9451-9452, 9455-9456, 9460-9461, 9463-9464, 9468-9469, 9473-9475, 9477-9479, 9481-9484, 9487-9488, 9490-9491, 9493-9494, 9498-9512, 9514-9526, 9530-9533, 9535-9537, 9539-9543, 9548-9563, 9565-9569, 9571-9573, 9577-9580, 9582-9583, 9585-9588, 9590-9608, 9610-9611, 9614-9619, 9622-9626, 9628-9632, 9637-9647, 9649-9655, 9657-9659, 9663-9673, 9678-9679, 9681-9684, 9687-9688, 9691-9692, 9697-9698, 9701-9702, 9708-9709, 9713-9714, 9716-9717, 9719-9722, 9725-9726, 9731-9741, 9743-9744, 9746-9753, 9756-9757, 9759-9760, 9762-9766, 9768-9769, 9771-9772, 9774-9781, 9788-9793, 9795-9796, 9798-9799, 9801-9802, 9805-9808, 9811-9821, 9824-9840, 9842-9857, 9859-9865, 9867-9870, 9872-9880, 9883-9890, 9893-9896, 9898-9938, 9940-9951, 9954-9959, 9961-9969, 9971-9990, 9994-10018, 10021-10078, 10080-10091, 10095-10113, 10116-10130, 10132-10139, 10141-10148, 10150-10153, 10155-10195, 10197-10216, 10218-10229, 10231-10234, 10236-10244, 10246-10260, 10262-10276, 10278-10305, 10307-10309, 10313-10317, 10319-10330, 10332-10342, 10344-10345, 10347-10351, 10356-10383, 10385-10409, 10412-10418, 10420-10421, 10423-10471, 10474-10482, 10484-10501, 10503-10509, 10511-10512, 10514-10518, 10521-10525, 10527-10554, 10556-10564, 10566-10576, 10578-10590, 10592-10597, 10600-10608, 10611-10623, 10625-10626, 10629-10633, 10635-10643, 10645-10656, 10658-10666, 10670-10688, 10690-10700, 10702-10715, 10719-10739, 10741-10757, 10759-10784, 10786-10792, 10795-10811, 10813-10826, 10831-10841, 10843-10861, 10863-10895, 10898-10914, 10917-10922, 10924-10926, 10928-10929, 10933-10934, 10936-10948, 10950-10965, 10967-10987

```text
credit union mortgage flood insurance affordable National Flood Insurance Program reauthorization NFIP predictable homebuyer regulatory exception secondary market liquidity product first-time down payment assistance accessory dwelling unit financing ADU FHA "Home\ Mortgage\ Disclosure\ Act" "HELPER\ Act" "Home\ of\ Your\ Own\ Act" "SUPPLY\ Act"
```

- Query atoms: 34
- Whitespace tokens: 43
- Catalog status: COMPLETE
- Quoted phrases: `Home Mortgage Disclosure Act`, `HELPER Act`, `Home of Your Own Act`, `SUPPLY Act`
- Bare terms: `credit`, `union`, `mortgage`, `flood`, `insurance`, `affordable`, `National`, `Flood`, `Insurance`, `Program`, `reauthorization`, `NFIP`, `predictable`, `homebuyer`, `regulatory`, `exception`, `secondary`, `market`, `liquidity`, `product`, `first-time`, `down`, `payment`, `assistance`, `accessory`, `dwelling`, `unit`, `financing`, `ADU`, `FHA`
- Operators: none

**Query 11** — 6 rows; Excel rows 5682-5683, 5700-5701, 5721-5722

```text
credit union servicemembers servicemember military nominal lease installation "on\-base\ financial\ services" "on\-site\ financial\ services" Military lending act defense land
```

- Query atoms: 15
- Whitespace tokens: 19
- Catalog status: COMPLETE
- Quoted phrases: `on-base financial services`, `on-site financial services`
- Bare terms: `credit`, `union`, `servicemembers`, `servicemember`, `military`, `nominal`, `lease`, `installation`, `Military`, `lending`, `act`, `defense`, `land`
- Operators: none

**Query 12** — 387 rows; Excel rows 676-678, 684-686, 692-693, 695-696, 698-702, 706-707, 710-713, 717-718, 721-722, 724-725, 729-730, 732-740, 749-750, 753-754, 757-758, 762-763, 767-769, 772-773, 787-788, 796-802, 804-805, 808-809, 818-823, 830-833, 836-837, 840-841, 843-847, 850-852, 857-859, 864-865, 868-869, 873-874, 878-879, 883-885, 887-891, 894-902, 905-907, 911-916, 918-924, 926-929, 931-933, 937-939, 941-944, 946-948, 950-958, 960-961, 963-971, 973-980, 984-987, 991-996, 1001-1015, 1018-1019, 1023-1025, 1029-1030, 1033-1037, 1039-1040, 1044-1048, 1052-1055, 1058-1059, 1063-1064, 1069-1070, 1074-1075, 1077-1080, 1083-1089, 1091-1092, 1094-1095, 1103-1107, 1109-1111, 1113-1119, 1121-1122, 1126-1127, 1129-1130, 1132-1133, 1135-1139, 1141-1147, 1150-1155, 1158-1161, 1165-1166, 1170-1171, 1177-1178, 1181-1182, 1184-1188, 1191-1199, 1201-1208, 1210-1212, 1215-1220, 1222-1225, 1229-1230, 1236-1249, 1251-1270, 1272-1275, 1277-1278, 1282-1288, 1290-1293

```text
credit union supplement capital additional requirements requirement net worth ratio risk-based subordinated debt secondary prompt corrective action
```

- Query atoms: 17
- Whitespace tokens: 17
- Catalog status: COMPLETE
- Quoted phrases: none
- Bare terms: `credit`, `union`, `supplement`, `capital`, `additional`, `requirements`, `requirement`, `net`, `worth`, `ratio`, `risk-based`, `subordinated`, `debt`, `secondary`, `prompt`, `corrective`, `action`
- Operators: none

**Query 13** — 436 rows; Excel rows 3-7, 10-20, 23-27, 31-33, 39-41, 48-49, 52-55, 59-60, 66-68, 70-76, 80-89, 93-94, 96-103, 106-109, 114-122, 124-129, 133-137, 139-141, 145-148, 154-155, 158-159, 162-163, 166-169, 172-173, 175-176, 178-179, 183-190, 200-201, 203-204, 208-209, 213-214, 217-221, 224-228, 231-234, 237-242, 245-246, 254-267, 269-280, 283-289, 292-304, 307-316, 318-319, 321-325, 327-335, 337-338, 343-345, 347-351, 353-354, 363-373, 375-386, 390-391, 398-406, 408-414, 420-423, 428-429, 432-433, 438-440, 445-448, 450-451, 453-456, 458-461, 463-465, 470-471, 474-475, 477-480, 483-486, 491-497, 499-502, 509-510, 518-519, 523-527, 529-530, 534-535, 537-550, 555-556, 564-570, 573-576, 579-581, 584-585, 587-588, 590-594, 598-603, 606-607, 609-613, 617-618, 620-621, 626-627, 629-632, 635-636, 639-646, 648-652, 654-656, 658-659, 661-675

```text
examination credit union supervision notice-and-comment rulemaking filing threshold suspicious suspiciou activity currency transaction "CAMELS\ rating" reputational risk safety and soundness cycle off-site appeal rights right tailoring regulatory burden asset relief "FFIEC" "Federal\ Financial\ Institutions\ Examination\ Council" "CTR\ threshold" "currency\ transaction\ report\ threshold" "SAR\ threshold" report "FIRM\ Act" "HUMPS\ Act" "SMART\ Act" "STREAMLINE\ Act" "Financial\ Reporting\ Threshold\ Modernization\ Act" "Community\ Bank\ Regulatory\ Tailoring\ Act" Bank Secrecy Act
```

- Query atoms: 44
- Whitespace tokens: 66
- Catalog status: COMPLETE
- Quoted phrases: `CAMELS rating`, `FFIEC`, `Federal Financial Institutions Examination Council`, `CTR threshold`, `currency transaction report threshold`, `SAR threshold`, `FIRM Act`, `HUMPS Act`, `SMART Act`, `STREAMLINE Act`, `Financial Reporting Threshold Modernization Act`, `Community Bank Regulatory Tailoring Act`
- Bare terms: `examination`, `credit`, `union`, `supervision`, `notice-and-comment`, `rulemaking`, `filing`, `threshold`, `suspicious`, `suspiciou`, `activity`, `currency`, `transaction`, `reputational`, `risk`, `safety`, `soundness`, `cycle`, `off-site`, `appeal`, `rights`, `right`, `tailoring`, `regulatory`, `burden`, `asset`, `relief`, `report`, `Bank`, `Secrecy`, `Act`
- Operators: `and`

**Query 14** — 456 rows; Excel rows 5043-5044, 5046-5055, 5059-5061, 5063-5067, 5069-5070, 5072-5075, 5077-5078, 5085-5088, 5091-5093, 5097-5098, 5101-5102, 5104-5108, 5110-5118, 5120-5121, 5124-5125, 5129-5133, 5140-5145, 5151-5152, 5155-5157, 5164-5165, 5170-5171, 5181-5182, 5186-5190, 5192-5195, 5198-5219, 5221-5223, 5225-5230, 5232-5233, 5235-5241, 5248-5259, 5261-5263, 5265-5272, 5274-5281, 5284-5290, 5293-5296, 5300-5302, 5304-5314, 5316-5322, 5325-5328, 5330-5331, 5334-5336, 5339-5342, 5344-5345, 5350-5354, 5357-5359, 5364-5368, 5372-5377, 5380-5381, 5384-5389, 5391-5392, 5394-5397, 5399-5401, 5403-5404, 5406-5412, 5415-5421, 5423-5424, 5426-5427, 5430-5436, 5439-5440, 5442-5447, 5449-5467, 5470-5471, 5473-5477, 5482-5483, 5485-5486, 5489-5490, 5496-5509, 5512-5526, 5531-5538, 5542-5552, 5555-5556, 5561-5562, 5564-5566, 5568-5572, 5575-5577, 5580-5587, 5589-5590, 5592-5598, 5600-5603, 5605-5609, 5611-5621, 5624-5626, 5628-5632, 5634-5639, 5643-5646, 5648-5653, 5658-5678, 5680-5681

```text
federal credit union modernization board governance diversify de novo chartering FHLB membership Federal Home Loan Bank "Credit\ Union\ Board\ Modernization\ Act" "American Access to Banking Act" "MORE\ Opportunities\ for\ Homeownership\ Act"
```

- Query atoms: 19
- Whitespace tokens: 31
- Catalog status: COMPLETE
- Quoted phrases: `Credit Union Board Modernization Act`, `American Access to Banking Act`, `MORE Opportunities for Homeownership Act`
- Bare terms: `federal`, `credit`, `union`, `modernization`, `board`, `governance`, `diversify`, `de`, `novo`, `chartering`, `FHLB`, `membership`, `Federal`, `Home`, `Loan`, `Bank`
- Operators: none

**Query 15** — 681 rows; Excel rows 4077-4084, 4087-4095, 4098-4100, 4105-4109, 4111-4112, 4117-4118, 4120-4123, 4128-4129, 4131-4133, 4137-4139, 4141-4144, 4151-4153, 4155-4157, 4161-4162, 4168-4173, 4176-4178, 4180-4181, 4187-4189, 4200-4201, 4207-4217, 4220-4230, 4232-4237, 4239-4242, 4245-4246, 4252-4255, 4262-4265, 4268-4272, 4278-4279, 4285-4289, 4293-4294, 4300-4305, 4308-4309, 4313-4316, 4322-4323, 4326-4327, 4330-4333, 4340-4341, 4343-4344, 4347-4351, 4355-4362, 4367-4368, 4370-4373, 4377-4382, 4385-4386, 4388-4391, 4394-4395, 4398-4401, 4407-4412, 4415-4416, 4418-4419, 4421-4423, 4426-4428, 4431-4434, 4438-4439, 4441-4442, 4449-4450, 4452-4467, 4470-4481, 4485-4491, 4496-4505, 4507-4518, 4520-4526, 4528-4538, 4540-4541, 4543-4546, 4550-4552, 4558-4559, 4561-4563, 4565-4566, 4569-4570, 4573-4574, 4576-4580, 4582-4583, 4586-4589, 4591-4597, 4599-4601, 4604-4623, 4625-4639, 4641-4661, 4664-4666, 4668-4670, 4677-4680, 4682-4689, 4692-4693, 4696-4698, 4700-4702, 4704-4715, 4717-4718, 4723-4737, 4740-4741, 4743-4744, 4746-4756, 4759-4762, 4765-4772, 4775-4784, 4788-4791, 4795-4800, 4802-4803, 4805-4808, 4810-4812, 4814-4815, 4818-4820, 4823-4834, 4836-4837, 4839-4840, 4842-4851, 4853-4854, 4857-4868, 4871-4872, 4874-4882, 4884-4886, 4889-4892, 4894-4900, 4905-4914, 4916-4923, 4925-4931, 4934-4936, 4938-4939, 4941-4945, 4947-4964, 4967-4976, 4978-4990, 4993-4998, 5001-5010, 5012-5015, 5019-5025, 5027-5028, 5030-5031, 5033-5035, 5037-5042

```text
federal data privacy standard national preemption state law GLBA exemption Gramm-Leach-Bliley Act breach notification "data\ security\ standard" mortgage trigger leads lead "trigger\ lead" "data\ broker" permissible sharing "Homebuyers\ Privacy\ Protection\ Act"
```

- Query atoms: 24
- Whitespace tokens: 31
- Catalog status: COMPLETE
- Quoted phrases: `data security standard`, `trigger lead`, `data broker`, `Homebuyers Privacy Protection Act`
- Bare terms: `federal`, `data`, `privacy`, `standard`, `national`, `preemption`, `state`, `law`, `GLBA`, `exemption`, `Gramm-Leach-Bliley`, `Act`, `breach`, `notification`, `mortgage`, `trigger`, `leads`, `lead`, `permissible`, `sharing`
- Operators: none

**Query 16** — 896 rows; Excel rows 2958-2962, 2972-2974, 2983-2984, 2987-2988, 2990-2992, 3000-3001, 3003-3016, 3018-3019, 3022-3025, 3028-3031, 3037-3039, 3042-3046, 3050-3053, 3055-3057, 3059-3067, 3070-3073, 3076-3077, 3080-3082, 3085-3088, 3092-3095, 3099-3100, 3104-3107, 3109-3113, 3116-3117, 3125-3126, 3128-3131, 3133-3134, 3139-3141, 3143-3146, 3150-3153, 3155-3156, 3159-3162, 3164-3167, 3170-3175, 3177-3179, 3184-3187, 3189-3191, 3194-3197, 3200-3201, 3203-3209, 3212-3215, 3218-3225, 3228-3234, 3236-3237, 3239-3241, 3243-3248, 3252-3255, 3257-3261, 3267-3268, 3274-3275, 3280-3282, 3284-3288, 3291-3297, 3299-3328, 3330-3334, 3336-3342, 3344-3349, 3352-3371, 3374-3376, 3378-3381, 3383-3387, 3389-3398, 3400-3402, 3404-3407, 3409-3414, 3416-3426, 3429-3431, 3433-3456, 3458-3462, 3464-3469, 3472-3487, 3489-3522, 3526-3533, 3535-3536, 3538-3542, 3544-3546, 3548-3553, 3555-3567, 3569-3570, 3573-3586, 3588-3595, 3597-3603, 3605-3607, 3609-3611, 3613-3614, 3621-3624, 3626-3645, 3648-3665, 3668-3677, 3679-3680, 3682-3689, 3691-3700, 3702-3711, 3713-3725, 3727-3731, 3733-3739, 3741-3750, 3752-3756, 3758-3785, 3788-3793, 3795-3796, 3798-3816, 3820-3822, 3824-3829, 3832-3835, 3837-3841, 3843-3848, 3850-3884, 3886-3887, 3889-3927, 3930-3949, 3952-3962, 3964-3965, 3967-3970, 3972-3973, 3975-3978, 3980-3983, 3985-4003, 4005-4033, 4035-4042, 4044-4047, 4051-4052, 4055-4070, 4072-4076

```text
financial fraud credit union "payment\ fraud" "Task Force for Recognizing and Averting Payment Scams" "check\ fraud" "check\ processing\ vulnerabilities" "permissible\ information\ sharing" "payment\ scam" authorized push payment elder financ exploit information sharing safe harbor mail theft check "imposter\ scam" "romance\ scam" identity
```

- Query atoms: 26
- Whitespace tokens: 42
- Catalog status: COMPLETE
- Quoted phrases: `payment fraud`, `Task Force for Recognizing and Averting Payment Scams`, `check fraud`, `check processing vulnerabilities`, `permissible information sharing`, `payment scam`, `imposter scam`, `romance scam`
- Bare terms: `financial`, `fraud`, `credit`, `union`, `authorized`, `push`, `payment`, `elder`, `financ`, `exploit`, `information`, `sharing`, `safe`, `harbor`, `mail`, `theft`, `check`, `identity`
- Operators: none

### 01 Examination & Supervision

Rows: 674; distinct full queries cataloged: 1; missing/empty hl rows: 238; malformed hl rows: 0; decoded-hl truncations: 0; query-catalog status: COMPLETE; overflow rows: 0.

**Query 1** — 436 rows; Excel rows 3-7, 10-20, 23-27, 31-33, 39-41, 48-49, 52-55, 59-60, 66-68, 70-76, 80-89, 93-94, 96-103, 106-109, 114-122, 124-129, 133-137, 139-141, 145-148, 154-155, 158-159, 162-163, 166-169, 172-173, 175-176, 178-179, 183-190, 200-201, 203-204, 208-209, 213-214, 217-221, 224-228, 231-234, 237-242, 245-246, 254-267, 269-280, 283-289, 292-304, 307-316, 318-319, 321-325, 327-335, 337-338, 343-345, 347-351, 353-354, 363-373, 375-386, 390-391, 398-406, 408-414, 420-423, 428-429, 432-433, 438-440, 445-448, 450-451, 453-456, 458-461, 463-465, 470-471, 474-475, 477-480, 483-486, 491-497, 499-502, 509-510, 518-519, 523-527, 529-530, 534-535, 537-550, 555-556, 564-570, 573-576, 579-581, 584-585, 587-588, 590-594, 598-603, 606-607, 609-613, 617-618, 620-621, 626-627, 629-632, 635-636, 639-646, 648-652, 654-656, 658-659, 661-675

```text
examination credit union supervision notice-and-comment rulemaking filing threshold suspicious suspiciou activity currency transaction "CAMELS\ rating" reputational risk safety and soundness cycle off-site appeal rights right tailoring regulatory burden asset relief "FFIEC" "Federal\ Financial\ Institutions\ Examination\ Council" "CTR\ threshold" "currency\ transaction\ report\ threshold" "SAR\ threshold" report "FIRM\ Act" "HUMPS\ Act" "SMART\ Act" "STREAMLINE\ Act" "Financial\ Reporting\ Threshold\ Modernization\ Act" "Community\ Bank\ Regulatory\ Tailoring\ Act" Bank Secrecy Act
```

- Query atoms: 44
- Whitespace tokens: 66
- Catalog status: COMPLETE
- Quoted phrases: `CAMELS rating`, `FFIEC`, `Federal Financial Institutions Examination Council`, `CTR threshold`, `currency transaction report threshold`, `SAR threshold`, `FIRM Act`, `HUMPS Act`, `SMART Act`, `STREAMLINE Act`, `Financial Reporting Threshold Modernization Act`, `Community Bank Regulatory Tailoring Act`
- Bare terms: `examination`, `credit`, `union`, `supervision`, `notice-and-comment`, `rulemaking`, `filing`, `threshold`, `suspicious`, `suspiciou`, `activity`, `currency`, `transaction`, `reputational`, `risk`, `safety`, `soundness`, `cycle`, `off-site`, `appeal`, `rights`, `right`, `tailoring`, `regulatory`, `burden`, `asset`, `relief`, `report`, `Bank`, `Secrecy`, `Act`
- Operators: `and`

### 02 Credit Union Capital Require

Rows: 618; distinct full queries cataloged: 1; missing/empty hl rows: 231; malformed hl rows: 0; decoded-hl truncations: 0; query-catalog status: COMPLETE; overflow rows: 0.

**Query 1** — 387 rows; Excel rows 2-4, 10-12, 18-19, 21-22, 24-28, 32-33, 36-39, 43-44, 47-48, 50-51, 55-56, 58-66, 75-76, 79-80, 83-84, 88-89, 93-95, 98-99, 113-114, 122-128, 130-131, 134-135, 144-149, 156-159, 162-163, 166-167, 169-173, 176-178, 183-185, 190-191, 194-195, 199-200, 204-205, 209-211, 213-217, 220-228, 231-233, 237-242, 244-250, 252-255, 257-259, 263-265, 267-270, 272-274, 276-284, 286-287, 289-297, 299-306, 310-313, 317-322, 327-341, 344-345, 349-351, 355-356, 359-363, 365-366, 370-374, 378-381, 384-385, 389-390, 395-396, 400-401, 403-406, 409-415, 417-418, 420-421, 429-433, 435-437, 439-445, 447-448, 452-453, 455-456, 458-459, 461-465, 467-473, 476-481, 484-487, 491-492, 496-497, 503-504, 507-508, 510-514, 517-525, 527-534, 536-538, 541-546, 548-551, 555-556, 562-575, 577-596, 598-601, 603-604, 608-614, 616-619

```text
credit union supplement capital additional requirements requirement net worth ratio risk-based subordinated debt secondary prompt corrective action
```

- Query atoms: 17
- Whitespace tokens: 17
- Catalog status: COMPLETE
- Quoted phrases: none
- Bare terms: `credit`, `union`, `supplement`, `capital`, `additional`, `requirements`, `requirement`, `net`, `worth`, `ratio`, `risk-based`, `subordinated`, `debt`, `secondary`, `prompt`, `corrective`, `action`
- Operators: none

### 03 NCUA Budget & Share Insuranc

Rows: 713; distinct full queries cataloged: 1; missing/empty hl rows: 240; malformed hl rows: 0; decoded-hl truncations: 0; query-catalog status: COMPLETE; overflow rows: 0.

**Query 1** — 473 rows; Excel rows 3-11, 14-16, 20-28, 31-35, 37-38, 46-49, 52-53, 55-61, 71-73, 77-78, 92-93, 113-115, 117-122, 133-135, 155-156, 159-161, 165-166, 169-171, 175-181, 183-186, 190-198, 200-206, 210-211, 214-215, 217-227, 229-239, 242-248, 251-253, 257-263, 265-266, 270-274, 277-282, 284-286, 289-295, 297-298, 300-308, 313-316, 318-327, 333-334, 341-344, 349-352, 355-356, 358-361, 363-366, 370-371, 375-383, 385-388, 391-392, 394-399, 401-403, 406-408, 410-416, 418-420, 422-423, 426-431, 434-441, 444-445, 447-457, 459-485, 489-490, 493-495, 497-501, 505-506, 508-509, 512-514, 516-521, 524-527, 531-536, 538-539, 541-549, 552-554, 557-569, 571-572, 574-575, 578-580, 582-583, 587-588, 590-594, 597-605, 607-625, 627-635, 637-641, 643-647, 649-654, 657-663, 666-669, 671-677, 681-686, 688-690, 692-694, 700-703, 705-711

```text
credit union budget process National Credit Union Share Insurance Fund "Federal\ Credit\ Union\ Act" NCUA transparency overhead transfer rate equity ratio board "NCUA\ Central\ Liquidity\ Facility\ Enhancements" Central liquidity facility CLF SIF
```

- Query atoms: 25
- Whitespace tokens: 32
- Catalog status: COMPLETE
- Quoted phrases: `Federal Credit Union Act`, `NCUA Central Liquidity Facility Enhancements`
- Bare terms: `credit`, `union`, `budget`, `process`, `National`, `Credit`, `Union`, `Share`, `Insurance`, `Fund`, `NCUA`, `transparency`, `overhead`, `transfer`, `rate`, `equity`, `ratio`, `board`, `Central`, `liquidity`, `facility`, `CLF`, `SIF`
- Operators: none

### 04 Interchange

Rows: 36; distinct full queries cataloged: 1; missing/empty hl rows: 16; malformed hl rows: 0; decoded-hl truncations: 0; query-catalog status: COMPLETE; overflow rows: 0.

**Query 1** — 20 rows; Excel rows 2-3, 5-6, 10-11, 13-14, 16-17, 23-24, 29-30, 32-37

```text
"Credit\ Card\ Competition\ Act"
```

- Query atoms: 1
- Whitespace tokens: 4
- Catalog status: COMPLETE
- Quoted phrases: `Credit Card Competition Act`
- Bare terms: none
- Operators: none

### 05 Payments

Rows: 34; distinct full queries cataloged: 1; missing/empty hl rows: 24; malformed hl rows: 0; decoded-hl truncations: 0; query-catalog status: COMPLETE; overflow rows: 0.

**Query 1** — 10 rows; Excel rows 4-5, 9-10, 13-14, 23-24, 26-27

```text
"FedNow" "real\-time\ payments" "install\ payment\ fund" ACH payment faster payments credit union "same\-day\ ACH" "automated\ clearing\ house" "faster\ payments" "open\ banking" earned wage access "payment\ system\ access" "instant\ payment" master account "buy\ now\ pay\ later" "Regulation\ E"
```

- Query atoms: 22
- Whitespace tokens: 37
- Catalog status: COMPLETE
- Quoted phrases: `FedNow`, `real-time payments`, `install payment fund`, `same-day ACH`, `automated clearing house`, `faster payments`, `open banking`, `payment system access`, `instant payment`, `buy now pay later`, `Regulation E`
- Bare terms: `ACH`, `payment`, `faster`, `payments`, `credit`, `union`, `earned`, `wage`, `access`, `master`, `account`
- Operators: none

### 06 Technology & Emerging Issues

Rows: 877; distinct full queries cataloged: 1; missing/empty hl rows: 199; malformed hl rows: 0; decoded-hl truncations: 0; query-catalog status: COMPLETE; overflow rows: 0.

**Query 1** — 678 rows; Excel rows 2-5, 7-9, 12-14, 16-17, 19-20, 22-23, 26-29, 31-42, 47-57, 60-63, 67-69, 72-73, 77-80, 82-87, 91-92, 98-100, 102-104, 108-109, 111-112, 116-117, 120-122, 126-127, 129-138, 142-148, 154-155, 162-163, 166-171, 177-178, 180-188, 196-201, 204-205, 208-212, 215-216, 218-219, 221-222, 224-238, 241-247, 251-252, 258-263, 265-266, 268-273, 277-285, 288-289, 292-305, 307-308, 311-327, 329-353, 355-370, 372-375, 380-396, 400-403, 405-406, 408-415, 417-418, 421-422, 424-427, 429-447, 449-451, 453-455, 457-466, 468-482, 484-485, 487-505, 507-519, 521-523, 526-527, 529-535, 537-538, 543-545, 548-550, 554-556, 558-561, 565-573, 575-576, 578-584, 586-592, 594-595, 597-599, 601-608, 610-613, 615-619, 621-622, 627-628, 631-632, 636-639, 642-643, 645-647, 650-664, 667-684, 686-701, 703-707, 709-719, 721-727, 729-738, 740-744, 746-751, 753-758, 760-766, 768-770, 772-778, 781-784, 788-798, 800-803, 805-817, 820-822, 824-838, 841-853, 856-862, 864-878

```text
central bank digital currency remote online notarization "CDBC" fintech partnership credit union NCUA overhead transfer rate "open\ banking" "AI\ lending\ model" "digital\ commodity" asset machine learning underwriting algorithmic decision "Anti\-CBDC\ Surveillance\ State\ Act" "Digital\ Asset\ Market\ Clarity\ Acy" "Secure\ Notarization\ Act" "Genius\ Act" "Stable\ Act"
```

- Query atoms: 30
- Whitespace tokens: 45
- Catalog status: COMPLETE
- Quoted phrases: `CDBC`, `open banking`, `AI lending model`, `digital commodity`, `Anti-CBDC Surveillance State Act`, `Digital Asset Market Clarity Acy`, `Secure Notarization Act`, `Genius Act`, `Stable Act`
- Bare terms: `central`, `bank`, `digital`, `currency`, `remote`, `online`, `notarization`, `fintech`, `partnership`, `credit`, `union`, `NCUA`, `overhead`, `transfer`, `rate`, `asset`, `machine`, `learning`, `underwriting`, `algorithmic`, `decision`
- Operators: none

### 07 Fraud Prevention

Rows: 1123; distinct full queries cataloged: 1; missing/empty hl rows: 227; malformed hl rows: 0; decoded-hl truncations: 0; query-catalog status: COMPLETE; overflow rows: 0.

**Query 1** — 896 rows; Excel rows 6-10, 20-22, 31-32, 35-36, 38-40, 48-49, 51-64, 66-67, 70-73, 76-79, 85-87, 90-94, 98-101, 103-105, 107-115, 118-121, 124-125, 128-130, 133-136, 140-143, 147-148, 152-155, 157-161, 164-165, 173-174, 176-179, 181-182, 187-189, 191-194, 198-201, 203-204, 207-210, 212-215, 218-223, 225-227, 232-235, 237-239, 242-245, 248-249, 251-257, 260-263, 266-273, 276-282, 284-285, 287-289, 291-296, 300-303, 305-309, 315-316, 322-323, 328-330, 332-336, 339-345, 347-376, 378-382, 384-390, 392-397, 400-419, 422-424, 426-429, 431-435, 437-446, 448-450, 452-455, 457-462, 464-474, 477-479, 481-504, 506-510, 512-517, 520-535, 537-570, 574-581, 583-584, 586-590, 592-594, 596-601, 603-615, 617-618, 621-634, 636-643, 645-651, 653-655, 657-659, 661-662, 669-672, 674-693, 696-713, 716-725, 727-728, 730-737, 739-748, 750-759, 761-773, 775-779, 781-787, 789-798, 800-804, 806-833, 836-841, 843-844, 846-864, 868-870, 872-877, 880-883, 885-889, 891-896, 898-932, 934-935, 937-975, 978-997, 1000-1010, 1012-1013, 1015-1018, 1020-1021, 1023-1026, 1028-1031, 1033-1051, 1053-1081, 1083-1090, 1092-1095, 1099-1100, 1103-1118, 1120-1124

```text
financial fraud credit union "payment\ fraud" "Task Force for Recognizing and Averting Payment Scams" "check\ fraud" "check\ processing\ vulnerabilities" "permissible\ information\ sharing" "payment\ scam" authorized push payment elder financ exploit information sharing safe harbor mail theft check "imposter\ scam" "romance\ scam" identity
```

- Query atoms: 26
- Whitespace tokens: 42
- Catalog status: COMPLETE
- Quoted phrases: `payment fraud`, `Task Force for Recognizing and Averting Payment Scams`, `check fraud`, `check processing vulnerabilities`, `permissible information sharing`, `payment scam`, `imposter scam`, `romance scam`
- Bare terms: `financial`, `fraud`, `credit`, `union`, `authorized`, `push`, `payment`, `elder`, `financ`, `exploit`, `information`, `sharing`, `safe`, `harbor`, `mail`, `theft`, `check`, `identity`
- Operators: none

### 08 Data Privacy & Cybersecurity

Rows: 966; distinct full queries cataloged: 1; missing/empty hl rows: 285; malformed hl rows: 0; decoded-hl truncations: 0; query-catalog status: COMPLETE; overflow rows: 0.

**Query 1** — 681 rows; Excel rows 2-9, 12-20, 23-25, 30-34, 36-37, 42-43, 45-48, 53-54, 56-58, 62-64, 66-69, 76-78, 80-82, 86-87, 93-98, 101-103, 105-106, 112-114, 125-126, 132-142, 145-155, 157-162, 164-167, 170-171, 177-180, 187-190, 193-197, 203-204, 210-214, 218-219, 225-230, 233-234, 238-241, 247-248, 251-252, 255-258, 265-266, 268-269, 272-276, 280-287, 292-293, 295-298, 302-307, 310-311, 313-316, 319-320, 323-326, 332-337, 340-341, 343-344, 346-348, 351-353, 356-359, 363-364, 366-367, 374-375, 377-392, 395-406, 410-416, 421-430, 432-443, 445-451, 453-463, 465-466, 468-471, 475-477, 483-484, 486-488, 490-491, 494-495, 498-499, 501-505, 507-508, 511-514, 516-522, 524-526, 529-548, 550-564, 566-586, 589-591, 593-595, 602-605, 607-614, 617-618, 621-623, 625-627, 629-640, 642-643, 648-662, 665-666, 668-669, 671-681, 684-687, 690-697, 700-709, 713-716, 720-725, 727-728, 730-733, 735-737, 739-740, 743-745, 748-759, 761-762, 764-765, 767-776, 778-779, 782-793, 796-797, 799-807, 809-811, 814-817, 819-825, 830-839, 841-848, 850-856, 859-861, 863-864, 866-870, 872-889, 892-901, 903-915, 918-923, 926-935, 937-940, 944-950, 952-953, 955-956, 958-960, 962-967

```text
federal data privacy standard national preemption state law GLBA exemption Gramm-Leach-Bliley Act breach notification "data\ security\ standard" mortgage trigger leads lead "trigger\ lead" "data\ broker" permissible sharing "Homebuyers\ Privacy\ Protection\ Act"
```

- Query atoms: 24
- Whitespace tokens: 31
- Catalog status: COMPLETE
- Quoted phrases: `data security standard`, `trigger lead`, `data broker`, `Homebuyers Privacy Protection Act`
- Bare terms: `federal`, `data`, `privacy`, `standard`, `national`, `preemption`, `state`, `law`, `GLBA`, `exemption`, `Gramm-Leach-Bliley`, `Act`, `breach`, `notification`, `mortgage`, `trigger`, `leads`, `lead`, `permissible`, `sharing`
- Operators: none

### 09 Charter Modernization & Gove

Rows: 639; distinct full queries cataloged: 1; missing/empty hl rows: 183; malformed hl rows: 0; decoded-hl truncations: 0; query-catalog status: COMPLETE; overflow rows: 0.

**Query 1** — 456 rows; Excel rows 2-3, 5-14, 18-20, 22-26, 28-29, 31-34, 36-37, 44-47, 50-52, 56-57, 60-61, 63-67, 69-77, 79-80, 83-84, 88-92, 99-104, 110-111, 114-116, 123-124, 129-130, 140-141, 145-149, 151-154, 157-178, 180-182, 184-189, 191-192, 194-200, 207-218, 220-222, 224-231, 233-240, 243-249, 252-255, 259-261, 263-273, 275-281, 284-287, 289-290, 293-295, 298-301, 303-304, 309-313, 316-318, 323-327, 331-336, 339-340, 343-348, 350-351, 353-356, 358-360, 362-363, 365-371, 374-380, 382-383, 385-386, 389-395, 398-399, 401-406, 408-426, 429-430, 432-436, 441-442, 444-445, 448-449, 455-468, 471-485, 490-497, 501-511, 514-515, 520-521, 523-525, 527-531, 534-536, 539-546, 548-549, 551-557, 559-562, 564-568, 570-580, 583-585, 587-591, 593-598, 602-605, 607-612, 617-637, 639-640

```text
federal credit union modernization board governance diversify de novo chartering FHLB membership Federal Home Loan Bank "Credit\ Union\ Board\ Modernization\ Act" "American Access to Banking Act" "MORE\ Opportunities\ for\ Homeownership\ Act"
```

- Query atoms: 19
- Whitespace tokens: 31
- Catalog status: COMPLETE
- Quoted phrases: `Credit Union Board Modernization Act`, `American Access to Banking Act`, `MORE Opportunities for Homeownership Act`
- Bare terms: `federal`, `credit`, `union`, `modernization`, `board`, `governance`, `diversify`, `de`, `novo`, `chartering`, `FHLB`, `membership`, `Federal`, `Home`, `Loan`, `Bank`
- Operators: none

### 10 Defense Credit Union Issues

Rows: 49; distinct full queries cataloged: 1; missing/empty hl rows: 43; malformed hl rows: 0; decoded-hl truncations: 0; query-catalog status: COMPLETE; overflow rows: 0.

**Query 1** — 6 rows; Excel rows 2-3, 20-21, 41-42

```text
credit union servicemembers servicemember military nominal lease installation "on\-base\ financial\ services" "on\-site\ financial\ services" Military lending act defense land
```

- Query atoms: 15
- Whitespace tokens: 19
- Catalog status: COMPLETE
- Quoted phrases: `on-base financial services`, `on-site financial services`
- Bare terms: `credit`, `union`, `servicemembers`, `servicemember`, `military`, `nominal`, `lease`, `installation`, `Military`, `lending`, `act`, `defense`, `land`
- Operators: none

### 11 Field of Membership

Rows: 41; distinct full queries cataloged: 1; missing/empty hl rows: 28; malformed hl rows: 0; decoded-hl truncations: 0; query-catalog status: COMPLETE; overflow rows: 0.

**Query 1** — 13 rows; Excel rows 4-6, 9-10, 12-13, 16-19, 40-41

```text
credit union dual charter federal membership "field\ of\ membership" common bond multiple community underserved area state chartered "dual\ charter\ system" preemption
```

- Query atoms: 17
- Whitespace tokens: 21
- Catalog status: COMPLETE
- Quoted phrases: `field of membership`, `dual charter system`
- Bare terms: `credit`, `union`, `dual`, `charter`, `federal`, `membership`, `common`, `bond`, `multiple`, `community`, `underserved`, `area`, `state`, `chartered`, `preemption`
- Operators: none

### 12 CDFI Fund

Rows: 0; distinct full queries cataloged: 0; missing/empty hl rows: 0; malformed hl rows: 0; decoded-hl truncations: 0; query-catalog status: COMPLETE; overflow rows: 0.

No recovered query set.

### 13 CFPB Issues & Structural Ref

Rows: 635; distinct full queries cataloged: 1; missing/empty hl rows: 132; malformed hl rows: 0; decoded-hl truncations: 0; query-catalog status: COMPLETE; overflow rows: 0.

**Query 1** — 503 rows; Excel rows 2-3, 5-12, 15-16, 20-29, 35-36, 39-40, 42-64, 68-80, 84-94, 96-113, 117-125, 133-137, 139-144, 146-147, 149-153, 159-161, 164-168, 170-178, 184-195, 198-202, 205-206, 208-212, 214-215, 217-223, 225-230, 232-258, 261-268, 270-277, 279-290, 292-300, 302-303, 305-321, 324-342, 346-350, 353-370, 372-373, 381-393, 395-396, 398-399, 406-409, 412-413, 415-419, 423-431, 434-435, 437-439, 441-445, 449-452, 457-462, 464-465, 467-477, 479-481, 483-488, 491-512, 520-534, 538-539, 542-551, 554-555, 557-558, 560-568, 570-579, 583-589, 592-614, 616-636

```text
CFPB reform Consumer Financial Protection Bureau governance structure funding "Consumer\ Financial\ Protection\ Bureau\ funding\ structure" council commission congressional approrpriation cost-benefit analysis analysi CFBP appropriation abusive standard Dodd-Frank Section 1071 small business data "UDAAP" "unfair\ deceptive\ abusive\ acts\ practice" "Transparency\ in\ CFPB\ Cost\-Benefit\ Analysis\ Act" "Bureau\ of\ Consumer\ Financial\ Protection\ Commission\ Act" "Rectifying\ UDAAP\ Act" "TABS\ Act" "1071 Repeal to Protect Small Business Lending Act" "Business\ of\ Insurance\ Regulatory\ Reform\ Act" overdraft rule
```

- Query atoms: 37
- Whitespace tokens: 72
- Catalog status: COMPLETE
- Quoted phrases: `Consumer Financial Protection Bureau funding structure`, `UDAAP`, `unfair deceptive abusive acts practice`, `Transparency in CFPB Cost-Benefit Analysis Act`, `Bureau of Consumer Financial Protection Commission Act`, `Rectifying UDAAP Act`, `TABS Act`, `1071 Repeal to Protect Small Business Lending Act`, `Business of Insurance Regulatory Reform Act`
- Bare terms: `CFPB`, `reform`, `Consumer`, `Financial`, `Protection`, `Bureau`, `governance`, `structure`, `funding`, `council`, `commission`, `congressional`, `approrpriation`, `cost-benefit`, `analysis`, `analysi`, `CFBP`, `appropriation`, `abusive`, `standard`, `Dodd-Frank`, `Section`, `1071`, `small`, `business`, `data`, `overdraft`, `rule`
- Operators: none

### 14 Credit Card & Consumer-Fee M

Rows: 146; distinct full queries cataloged: 1; missing/empty hl rows: 92; malformed hl rows: 0; decoded-hl truncations: 0; query-catalog status: COMPLETE; overflow rows: 0.

**Query 1** — 54 rows; Excel rows 6-7, 11-12, 20-21, 23-25, 29-32, 45-46, 48-56, 64-65, 72-73, 78-87, 95-99, 120-123, 129-132, 142-144

```text
credit card rate cap car interest interchange limit overdraft fee lending rule late usury Truth in Lending Act junk financial institution "10\ Percent\ Credit\ Card\ Interest\ Rate\ Cap\ Act" "Credit\ Card\ Fairness\ Act" "Overdraft Lending: Very Large Financial Institutions"
```

- Query atoms: 24
- Whitespace tokens: 39
- Catalog status: COMPLETE
- Quoted phrases: `10 Percent Credit Card Interest Rate Cap Act`, `Credit Card Fairness Act`, `Overdraft Lending: Very Large Financial Institutions`
- Bare terms: `credit`, `card`, `rate`, `cap`, `car`, `interest`, `interchange`, `limit`, `overdraft`, `fee`, `lending`, `rule`, `late`, `usury`, `Truth`, `in`, `Lending`, `Act`, `junk`, `financial`, `institution`
- Operators: none

### 15 Telephone Consumer Protectio

Rows: 165; distinct full queries cataloged: 1; missing/empty hl rows: 77; malformed hl rows: 0; decoded-hl truncations: 0; query-catalog status: COMPLETE; overflow rows: 0.

**Query 1** — 88 rows; Excel rows 3-5, 7-8, 12-13, 15-16, 18-24, 26-27, 34-35, 42-44, 46-53, 57-58, 61-64, 66-69, 71-74, 76-78, 81-83, 89-90, 92-94, 98-99, 101-104, 107-108, 114-115, 117-118, 123-129, 131-132, 134-135, 140-143, 145-147, 161-162

```text
"Telephone\ Consumer\ Protection\ Act" TCPA FCC credit union Federal Communications Communication Commission robocall financial institution "autodialer\ consent" Prior express consent Telephone Consumer Protection Act
```

- Query atoms: 20
- Whitespace tokens: 24
- Catalog status: COMPLETE
- Quoted phrases: `Telephone Consumer Protection Act`, `autodialer consent`
- Bare terms: `TCPA`, `FCC`, `credit`, `union`, `Federal`, `Communications`, `Communication`, `Commission`, `robocall`, `financial`, `institution`, `Prior`, `express`, `consent`, `Telephone`, `Consumer`, `Protection`, `Act`
- Operators: none

### 16 Member Business Lending

Rows: 2665; distinct full queries cataloged: 1; missing/empty hl rows: 213; malformed hl rows: 0; decoded-hl truncations: 0; query-catalog status: COMPLETE; overflow rows: 0.

**Query 1** — 2452 rows; Excel rows 3-13, 15-16, 18-21, 24-29, 34-42, 44-52, 55-57, 60-62, 65-70, 73-79, 81-82, 85-91, 93-98, 100-103, 105-131, 133-134, 136-144, 148-153, 155-164, 166-172, 174-183, 185-186, 188-190, 195-205, 207-208, 210-211, 213-218, 221-223, 225-229, 231-244, 246-284, 288-293, 296-304, 306-325, 327-328, 330-335, 337-344, 347-352, 354-363, 366-367, 370-380, 382-383, 385-401, 403-410, 412-414, 418-419, 421-430, 433-434, 437-440, 442-460, 462-463, 466-474, 476-482, 484-493, 497-498, 500-507, 511-514, 516-534, 536-537, 539-542, 545-548, 550-560, 562-565, 567-569, 571-583, 586-593, 595-600, 605-608, 610-612, 614-615, 619-622, 626-643, 645-655, 657-670, 673-706, 713-722, 727-730, 733-745, 748-754, 756-769, 771-777, 779-789, 792-794, 796-801, 803-805, 807-815, 817-844, 847-869, 871-934, 936-954, 956-964, 966-988, 990-1078, 1081-1093, 1096-1136, 1138-1139, 1141-1148, 1150-1260, 1262-1281, 1283-1315, 1317-1341, 1343-1408, 1410-1432, 1434-1456, 1458-1493, 1495-1510, 1512-1518, 1520-1576, 1578-1589, 1591-1597, 1600-1601, 1603-1655, 1658-1690, 1692-1725, 1727-1757, 1759-1789, 1791-1814, 1817-1857, 1861-1868, 1870-1876, 1878-1899, 1902-1906, 1908-1914, 1916-1933, 1935-1990, 1993-2001, 2003-2073, 2076-2077, 2079-2114, 2116-2140, 2142-2230, 2233-2245, 2247-2329, 2331-2347, 2349-2359, 2361-2397, 2399-2410, 2412-2426, 2428-2449, 2452-2473, 2475-2514, 2516-2542, 2544-2545, 2547-2550, 2553-2599, 2602-2604, 2606-2666

```text
"de\ minimis\ threshold" credit union lending member business loan exempt MBL veteran increase maximum maturity cap 12.25% asset 12.25 percent threshold commercial SBA 7(a) limit "Veterans\ Member\ Business\ Loan\ Act" "Increasing\ Credit\ Union\ Lending\ for\ Business\ Growth\ Act" "Expanding Access to Lending Options Act" "Protecting Access to Credit for Small Businesses Act"
```

- Query atoms: 27
- Whitespace tokens: 52
- Catalog status: COMPLETE
- Quoted phrases: `de minimis threshold`, `Veterans Member Business Loan Act`, `Increasing Credit Union Lending for Business Growth Act`, `Expanding Access to Lending Options Act`, `Protecting Access to Credit for Small Businesses Act`
- Bare terms: `credit`, `union`, `lending`, `member`, `business`, `loan`, `exempt`, `MBL`, `veteran`, `increase`, `maximum`, `maturity`, `cap`, `12.25%`, `asset`, `12.25`, `percent`, `threshold`, `commercial`, `SBA`, `7(a)`, `limit`
- Operators: none

### 17 Mortgage Lending & Housing

Rows: 1605; distinct full queries cataloged: 1; missing/empty hl rows: 238; malformed hl rows: 0; decoded-hl truncations: 0; query-catalog status: COMPLETE; overflow rows: 0.

**Query 1** — 1367 rows; Excel rows 2-10, 13-17, 21-27, 29-40, 42-47, 50-53, 59-60, 65-66, 70-71, 74-75, 79-80, 82-83, 87-88, 92-94, 96-98, 100-103, 106-107, 109-110, 112-113, 117-131, 133-145, 149-152, 154-156, 158-162, 167-182, 184-188, 190-192, 196-199, 201-202, 204-207, 209-227, 229-230, 233-238, 241-245, 247-251, 256-266, 268-274, 276-278, 282-292, 297-298, 300-303, 306-307, 310-311, 316-317, 320-321, 327-328, 332-333, 335-336, 338-341, 344-345, 350-360, 362-363, 365-372, 375-376, 378-379, 381-385, 387-388, 390-391, 393-400, 407-412, 414-415, 417-418, 420-421, 424-427, 430-440, 443-459, 461-476, 478-484, 486-489, 491-499, 502-509, 512-515, 517-557, 559-570, 573-578, 580-588, 590-609, 613-637, 640-697, 699-710, 714-732, 735-749, 751-758, 760-767, 769-772, 774-814, 816-835, 837-848, 850-853, 855-863, 865-879, 881-895, 897-924, 926-928, 932-936, 938-949, 951-961, 963-964, 966-970, 975-1002, 1004-1028, 1031-1037, 1039-1040, 1042-1090, 1093-1101, 1103-1120, 1122-1128, 1130-1131, 1133-1137, 1140-1144, 1146-1173, 1175-1183, 1185-1195, 1197-1209, 1211-1216, 1219-1227, 1230-1242, 1244-1245, 1248-1252, 1254-1262, 1264-1275, 1277-1285, 1289-1307, 1309-1319, 1321-1334, 1338-1358, 1360-1376, 1378-1403, 1405-1411, 1414-1430, 1432-1445, 1450-1460, 1462-1480, 1482-1514, 1517-1533, 1536-1541, 1543-1545, 1547-1548, 1552-1553, 1555-1567, 1569-1584, 1586-1606

```text
credit union mortgage flood insurance affordable National Flood Insurance Program reauthorization NFIP predictable homebuyer regulatory exception secondary market liquidity product first-time down payment assistance accessory dwelling unit financing ADU FHA "Home\ Mortgage\ Disclosure\ Act" "HELPER\ Act" "Home\ of\ Your\ Own\ Act" "SUPPLY\ Act"
```

- Query atoms: 34
- Whitespace tokens: 43
- Catalog status: COMPLETE
- Quoted phrases: `Home Mortgage Disclosure Act`, `HELPER Act`, `Home of Your Own Act`, `SUPPLY Act`
- Bare terms: `credit`, `union`, `mortgage`, `flood`, `insurance`, `affordable`, `National`, `Flood`, `Insurance`, `Program`, `reauthorization`, `NFIP`, `predictable`, `homebuyer`, `regulatory`, `exception`, `secondary`, `market`, `liquidity`, `product`, `first-time`, `down`, `payment`, `assistance`, `accessory`, `dwelling`, `unit`, `financing`, `ADU`, `FHA`
- Operators: none

## SUSPECT-ZERO-YIELD quoted phrases

Counts are per query-occurrence: 37 occurrences / 36 distinct phrases.

| Sheet | Query identifier | Phrase | Artifact hits | Scope |
|---|---|---|---:|---|
| All Bills | Query 6 | `AI lending model` | 0 | Title + bill_summary within this sheet |
| All Bills | Query 3 | `autodialer consent` | 0 | Title + bill_summary within this sheet |
| All Bills | Query 2 | `automated clearing house` | 0 | Title + bill_summary within this sheet |
| All Bills | Query 2 | `buy now pay later` | 0 | Title + bill_summary within this sheet |
| All Bills | Query 13 | `CAMELS rating` | 0 | Title + bill_summary within this sheet |
| All Bills | Query 6 | `CDBC` | 0 | Title + bill_summary within this sheet |
| All Bills | Query 16 | `check fraud` | 0 | Title + bill_summary within this sheet |
| All Bills | Query 16 | `check processing vulnerabilities` | 0 | Title + bill_summary within this sheet |
| All Bills | Query 5 | `Consumer Financial Protection Bureau funding structure` | 0 | Title + bill_summary within this sheet |
| All Bills | Query 13 | `CTR threshold` | 0 | Title + bill_summary within this sheet |
| All Bills | Query 13 | `currency transaction report threshold` | 0 | Title + bill_summary within this sheet |
| All Bills | Query 15 | `data security standard` | 0 | Title + bill_summary within this sheet |
| All Bills | Query 4 | `de minimis threshold` | 0 | Title + bill_summary within this sheet |
| All Bills | Query 6 | `Digital Asset Market Clarity Acy` | 0 | Title + bill_summary within this sheet |
| All Bills | Query 9 | `dual charter system` | 0 | Title + bill_summary within this sheet |
| All Bills | Query 2 | `faster payments` | 0 | Title + bill_summary within this sheet |
| All Bills | Query 13 | `Federal Financial Institutions Examination Council` | 0 | Title + bill_summary within this sheet |
| All Bills | Query 2 | `FedNow` | 0 | Title + bill_summary within this sheet |
| All Bills | Query 13 | `FFIEC` | 0 | Title + bill_summary within this sheet |
| All Bills | Query 9 | `field of membership` | 0 | Title + bill_summary within this sheet |
| All Bills | Query 10 | `Home Mortgage Disclosure Act` | 0 | Title + bill_summary within this sheet |
| All Bills | Query 2 | `install payment fund` | 0 | Title + bill_summary within this sheet |
| All Bills | Query 2 | `instant payment` | 0 | Title + bill_summary within this sheet |
| All Bills | Query 11 | `on-base financial services` | 0 | Title + bill_summary within this sheet |
| All Bills | Query 11 | `on-site financial services` | 0 | Title + bill_summary within this sheet |
| All Bills | Query 2 | `open banking` | 0 | Title + bill_summary within this sheet |
| All Bills | Query 6 | `open banking` | 0 | Title + bill_summary within this sheet |
| All Bills | Query 16 | `payment fraud` | 0 | Title + bill_summary within this sheet |
| All Bills | Query 2 | `payment system access` | 0 | Title + bill_summary within this sheet |
| All Bills | Query 16 | `permissible information sharing` | 0 | Title + bill_summary within this sheet |
| All Bills | Query 2 | `real-time payments` | 0 | Title + bill_summary within this sheet |
| All Bills | Query 2 | `Regulation E` | 0 | Title + bill_summary within this sheet |
| All Bills | Query 2 | `same-day ACH` | 0 | Title + bill_summary within this sheet |
| All Bills | Query 13 | `SAR threshold` | 0 | Title + bill_summary within this sheet |
| All Bills | Query 10 | `SUPPLY Act` | 0 | Title + bill_summary within this sheet |
| All Bills | Query 16 | `Task Force for Recognizing and Averting Payment Scams` | 0 | Title + bill_summary within this sheet |
| All Bills | Query 5 | `unfair deceptive abusive acts practice` | 0 | Title + bill_summary within this sheet |

No network claim is made by this list.

## Dictionary check

**OMITTED.** No deterministic dictionary or approved known-vocabulary source exists in the offline input set.

## C13 decision summary

| Status | Check | Detail |
|---|---|---|
| WARN | C13 hl coverage: All Bills | 8520/10986 decodable; missing=2466 empty=0 malformed=0 |
| WARN | C13 hl coverage: 01 Examination & Supervision | 436/674 decodable; missing=238 empty=0 malformed=0 |
| WARN | C13 hl coverage: 02 Credit Union Capital Require | 387/618 decodable; missing=231 empty=0 malformed=0 |
| WARN | C13 hl coverage: 03 NCUA Budget & Share Insuranc | 473/713 decodable; missing=240 empty=0 malformed=0 |
| WARN | C13 hl coverage: 04 Interchange | 20/36 decodable; missing=16 empty=0 malformed=0 |
| WARN | C13 hl coverage: 05 Payments | 10/34 decodable; missing=24 empty=0 malformed=0 |
| WARN | C13 hl coverage: 06 Technology & Emerging Issues | 678/877 decodable; missing=199 empty=0 malformed=0 |
| WARN | C13 hl coverage: 07 Fraud Prevention | 896/1123 decodable; missing=227 empty=0 malformed=0 |
| WARN | C13 hl coverage: 08 Data Privacy & Cybersecurity | 681/966 decodable; missing=285 empty=0 malformed=0 |
| WARN | C13 hl coverage: 09 Charter Modernization & Gove | 456/639 decodable; missing=183 empty=0 malformed=0 |
| WARN | C13 hl coverage: 10 Defense Credit Union Issues | 6/49 decodable; missing=43 empty=0 malformed=0 |
| WARN | C13 hl coverage: 11 Field of Membership | 13/41 decodable; missing=28 empty=0 malformed=0 |
| WARN | C13 hl coverage: 12 CDFI Fund | 0 data rows; hl coverage unavailable |
| WARN | C13 hl coverage: 13 CFPB Issues & Structural Ref | 503/635 decodable; missing=132 empty=0 malformed=0 |
| WARN | C13 hl coverage: 14 Credit Card & Consumer-Fee M | 54/146 decodable; missing=92 empty=0 malformed=0 |
| WARN | C13 hl coverage: 15 Telephone Consumer Protectio | 88/165 decodable; missing=77 empty=0 malformed=0 |
| WARN | C13 hl coverage: 16 Member Business Lending | 2452/2665 decodable; missing=213 empty=0 malformed=0 |
| WARN | C13 hl coverage: 17 Mortgage Lending & Housing | 1367/1605 decodable; missing=238 empty=0 malformed=0 |
| PASS | C13 numbered archive sheets are contiguous 01..17 | 17 unique numbered sheets |
| WARN | C13 single-atom API-browser query sets | 04 Interchange (20 rows) |
| WARN | C13 documented canonical categories with no query set | CDFI Fund, CU Tax Status |
| PASS | C13 no undocumented canonical query-set gaps | documented known: CDFI Fund, CU Tax Status |

## Method citations

- `AUDIT_SP/sections.py:14-32 (All Bills and per-sheet traversal semantics)`
- `fec/bill_rules.py:16-58,110-122 (canonical category semantics)`
- `fec/leg_evidence_recompute.py:300-327,415-450 (atomic output and manifest-verification house style)`
