# COMPET_MULT candidate run: allocation delta (dial OFF -> COMPET_MULT=1)

Facts only. Constants AMPLITUDE=1.0, SCALE=5.0 are Paul's judgment, uncalibrated; the reciprocity (dollars buy more where a seat is competitive) is NOT validated.
Artifact: `competitiveness_c.json.candidate` (roster sha256 `e0e76c7ab4992fac`). Boundaries UNVERIFIED-HERE; mid-decade-redistricted states flagged, never altered.

## Conservation, certificate, ranks

| quantity | before (dial off) | after (c on) |
|---|---|---|
| pot (budget) | $2,500,000 | $2,500,000 |
| spent | $2,500,000 | $2,500,000 |
| sum of alloc | $2,500,000 | $2,500,000 |
| funded members | 380 | 383 |
| per-member cap respected (max alloc, cap $10,000) | $10,000 | $10,000 |
| certificate_valid | True | True |
| conversion_reachable | False | False |
| base / final winnability | 54.335 / 63.031 | 52.670 / 62.084 |
| recorded dials COMPET_MULT / sha | (absent: dial off) | 1 / 4e109597546e2c5d |

ROI = the member desk expected weighted flips from the next $10k (desk_roi, lifted from make_member_desk.py), before = the shipped engine block, after = the same block with engine.cmult = c; the helper reproduces the shipped desk bundle roi for 533/533 members. gap = opt_alloc (the plan increment).

Pot unchanged: True. Total allocated conserved: True.

## Member allocation: top 25 gainers and losers (opt_alloc, real dollars; gap = the plan increment = opt_alloc)

### Top 25 gainers

| member | party | lean | c | opt_alloc before | after | delta | gap before | gap after | ROI before | ROI after |
|---|---|---|---|---|---|---|---|---|---|---|
| Robert Wittman | R | 3 | 1.5488 | 1,500 | 5,500 | +4000 | 1500 | 5500 | 0.0089 | 0.0111 |
| Don Bacon | R | -3 | 2.0000 | 6,500 | 9,500 | +3000 | 6500 | 9500 | 0.0137 | 0.0225 |
| David McCormick | R | 1 | 1.8187 | 500 | 3,000 | +2500 | 500 | 3000 | 0.0084 | 0.0098 |
| Greg Landsman | D | -1 | 2.0000 | 1,500 | 4,000 | +2500 | 1500 | 4000 | 0.0074 | 0.0105 |
| Jennifer Kiggans | R | 0 | 2.0000 | 3,000 | 5,500 | +2500 | 3000 | 5500 | 0.0089 | 0.0120 |
| Jon Ossoff | D | -1 | 2.0000 | 2,000 | 4,500 | +2500 | 2000 | 4500 | 0.0079 | 0.0113 |
| Kathy Castor | D | -4 | 2.0000 | 6,500 | 9,000 | +2500 | 6500 | 9000 | 0.0122 | 0.0168 |
| Darrell Issa | R | -2 | 2.0000 | 7,000 | 9,000 | +2000 | 7000 | 9000 | 0.0143 | 0.0189 |
| Marie Gluesenkamp Perez | D | -2 | 2.0000 | 5,000 | 7,000 | +2000 | 5000 | 7000 | 0.0104 | 0.0132 |
| Ryan Mackenzie | R | 1 | 1.8187 | 6,500 | 8,500 | +2000 | 6500 | 8500 | 0.0138 | 0.0202 |
| Steve Cohen | D | -9 | 2.0000 | 8,000 | 10,000 | +2000 | 8000 | 10000 | 0.0168 | 0.0280 |
| Ashley Hinson | R | 4 | 1.4493 | 0 | 1,500 | +1500 | 0 | 1500 | 0.0078 | 0.0089 |
| Derrick Van Orden | R | 3 | 1.5488 | 5,000 | 6,500 | +1500 | 5000 | 6500 | 0.0108 | 0.0128 |
| Donald Davis | D | -5 | 2.0000 | 5,500 | 7,000 | +1500 | 5500 | 7000 | 0.0106 | 0.0121 |
| Jared Moskowitz | D | -3 | 2.0000 | 7,500 | 9,000 | +1500 | 7500 | 9000 | 0.0130 | 0.0172 |
| Jefferson Van Drew | R | 5 | 1.3679 | 2,000 | 3,500 | +1500 | 2000 | 3500 | 0.0087 | 0.0104 |
| Michael Lawler | R | -1 | 2.0000 | 8,500 | 10,000 | +1500 | 8500 | 10000 | 0.0108 | 0.0158 |
| Patrick Ryan | D | 2 | 1.6703 | 2,500 | 4,000 | +1500 | 2500 | 4000 | 0.0083 | 0.0102 |
| Sharice Davids | D | 2 | 1.6703 | 1,000 | 2,500 | +1500 | 1000 | 2500 | 0.0074 | 0.0088 |
| Thomas Suozzi | D | 0 | 2.0000 | 1,500 | 3,000 | +1500 | 1500 | 3000 | 0.0090 | 0.0100 |
| Bernie Moreno | R | 5 | 1.3679 | 8,500 | 9,500 | +1000 | 8500 | 9500 | 0.0150 | 0.0176 |
| Chris Pappas | D | 2 | 1.6703 | 1,000 | 2,000 | +1000 | 1000 | 2000 | 0.0074 | 0.0083 |
| Earl Carter | R | 8 | 1.2019 | 5,500 | 6,500 | +1000 | 5500 | 6500 | 0.0137 | 0.0155 |
| Gabe Evans | R | 0 | 2.0000 | 2,500 | 3,500 | +1000 | 2500 | 3500 | 0.0077 | 0.0099 |
| Hillary Scholten | D | 4 | 1.4493 | 1,500 | 2,500 | +1000 | 1500 | 2500 | 0.0080 | 0.0091 |

### Top 25 losers

| member | party | lean | c | opt_alloc before | after | delta | gap before | gap after | ROI before | ROI after |
|---|---|---|---|---|---|---|---|---|---|---|
| Adrian Smith | R | 27 | 1.0045 | 9,500 | 8,000 | -1500 | 9500 | 8000 | 0.0128 | 0.0128 |
| Mike Rogers | R | 23 | 1.0101 | 2,500 | 1,000 | -1500 | 2500 | 1000 | 0.0092 | 0.0092 |
| Adriano Espaillat | D | 32 | 1.0017 | 5,000 | 4,000 | -1000 | 5000 | 4000 | 0.0106 | 0.0106 |
| Burgess Owens | R | -12 | 2.0000 | 5,500 | 4,500 | -1000 | 5500 | 4500 | 0.0111 | 0.0107 |
| Frank Lucas | R | 23 | 1.0101 | 1,500 | 500 | -1000 | 1500 | 500 | 0.0087 | 0.0087 |
| James Clyburn | D | 13 | 1.0743 | 4,500 | 3,500 | -1000 | 4500 | 3500 | 0.0101 | 0.0101 |
| James Himes | D | 13 | 1.0743 | 9,000 | 8,000 | -1000 | 9000 | 8000 | 0.0119 | 0.0121 |
| Jay Obernolte | R | 9 | 1.1653 | 7,000 | 6,000 | -1000 | 7000 | 6000 | 0.0118 | 0.0119 |
| John Larson | D | 12 | 1.0907 | 9,000 | 8,000 | -1000 | 9000 | 8000 | 0.0130 | 0.0131 |
| Lloyd Smucker | R | 11 | 1.1108 | 4,000 | 3,000 | -1000 | 4000 | 3000 | 0.0095 | 0.0096 |
| Max Miller | R | 5 | 1.3679 | 4,000 | 3,000 | -1000 | 4000 | 3000 | 0.0096 | 0.0097 |
| Michelle Fischbach | R | 18 | 1.0273 | 9,500 | 8,500 | -1000 | 9500 | 8500 | 0.0141 | 0.0142 |
| Mike Bost | R | 22 | 1.0123 | 10,000 | 9,000 | -1000 | 10000 | 9000 | 0.0160 | 0.0160 |
| Mike Kennedy | R | 17 | 1.0334 | 3,000 | 2,000 | -1000 | 3000 | 2000 | 0.0090 | 0.0090 |
| Mike Quigley | D | 19 | 1.0224 | 8,000 | 7,000 | -1000 | 8000 | 7000 | 0.0128 | 0.0128 |
| Steve Womack | R | 13 | 1.0743 | 10,000 | 9,000 | -1000 | 10000 | 9000 | 0.0133 | 0.0134 |
| Terri Sewell | D | 10 | 1.1353 | 2,500 | 1,500 | -1000 | 2500 | 1500 | 0.0094 | 0.0095 |
| Tom Cole | R | 17 | 1.0334 | 3,000 | 2,000 | -1000 | 3000 | 2000 | 0.0094 | 0.0094 |
| Tom McClintock | R | 10 | 1.1353 | 10,000 | 9,000 | -1000 | 10000 | 9000 | 0.0210 | 0.0210 |
| Troy Carter | D | 25 | 1.0067 | 9,500 | 8,500 | -1000 | 9500 | 8500 | 0.0138 | 0.0138 |
| Adam Smith | D | 22 | 1.0123 | 2,000 | 1,500 | -500 | 2000 | 1500 | 0.0080 | 0.0081 |
| Andy Biggs | R | 10 | 1.1353 | 7,000 | 6,500 | -500 | 7000 | 6500 | 0.0463 | 0.0471 |
| Angus King | D | 4 | 1.4493 | 5,000 | 4,500 | -500 | 5000 | 4500 | 0.0191 | 0.0206 |
| April McClain Delaney | D | 3 | 1.5488 | 7,500 | 7,000 | -500 | 7500 | 7000 | 0.0150 | 0.0153 |
| Austin Scott | R | 15 | 1.0498 | 1,500 | 1,000 | -500 | 1500 | 1000 | 0.0076 | 0.0077 |

Members whose opt_alloc changed: 134 (gainers 42, losers 92); sum of gains $57,000 = sum of losses $57,000.

## By c bucket (all 533)

| c bucket | members | funded before | funded after | $ before | $ after | delta |
|---|---|---|---|---|---|---|
| <1.1 | 225 | 153 | 152 | $995,500 | $958,500 | -37000 |
| 1.1-1.5 | 221 | 158 | 160 | $1,065,500 | $1,062,500 | -3000 |
| 1.5-1.99 | 43 | 34 | 35 | $201,000 | $213,500 | +12500 |
| 2.0 | 44 | 35 | 36 | $238,000 | $265,500 | +27500 |

## per_topic_alloc (flip engine, per-topic $2.0M each): totals by topic

| topic | funded before | funded after | $ before | $ after | members changed |
|---|---|---|---|---|---|
| Examination & Supervision | 148 | 151 | $2,000,000 | $2,000,000 | 88 |
| Credit Union Capital Requirements | 156 | 160 | $2,000,000 | $2,000,000 | 98 |
| NCUA Budget & Share Insurance Fund | 168 | 168 | $2,000,000 | $2,000,000 | 120 |
| Interchange | 167 | 172 | $2,000,000 | $2,000,000 | 43 |
| Payments | 116 | 120 | $2,000,000 | $2,000,000 | 72 |
| Technology & Emerging Issues | 173 | 179 | $2,000,000 | $2,000,000 | 92 |
| Fraud Prevention | 154 | 164 | $2,000,000 | $2,000,000 | 96 |
| Data Privacy & Cybersecurity | 151 | 160 | $2,000,000 | $2,000,000 | 93 |
| Charter Modernization & Governance | 158 | 165 | $2,000,000 | $2,000,000 | 112 |
| Defense Credit Union Issues | 124 | 129 | $2,000,000 | $2,000,000 | 60 |
| Field of Membership | 127 | 127 | $2,000,000 | $2,000,000 | 73 |
| CDFI Fund | 173 | 179 | $2,000,000 | $2,000,000 | 106 |
| CFPB Restrain | 152 | 156 | $2,000,000 | $2,000,000 | 72 |
| CFPB Reach (-) | 135 | 143 | $2,000,000 | $2,000,000 | 54 |
| Telephone Consumer Protection Act Issues | 168 | 170 | $2,000,000 | $2,000,000 | 76 |
| Credit Card & Consumer-Fee Mandates | 147 | 154 | $2,000,000 | $2,000,000 | 71 |
| Member Business Lending | 197 | 202 | $2,000,000 | $2,000,000 | 128 |
| Mortgage Lending & Housing | 183 | 196 | $2,000,000 | $2,000,000 | 120 |
| Credit Union Tax Status | 185 | 185 | $2,000,000 | $2,000,000 | 32 |

Per-topic pots conserved: True.

## Budget frontier (coalition mode) (lev -> c)

| topic | base spread before/after | seeds before/after | final spread before/after | knee before/after | first seeds after |
|---|---|---|---|---|---|
| Examination & Supervision | 221.0 / 221.0 | 45 / 45 | 242.8 / 242.8 | $2050k / $2200k | Gonzalez, Perez, Fitzpatrick |
| Credit Union Capital Requirements | 265.1 / 265.1 | 45 / 45 | 283.7 / 283.7 | $1950k / $1950k | Gottheimer, Cuellar, Issa |
| NCUA Budget & Share Insurance Fund | 303.1 / 303.1 | 45 / 45 | 321.5 / 321.5 | $1950k / $1900k | Green, Hill, Bynum |
| Interchange | 7.2 / 7.2 | 45 / 45 | 64.2 / 64.2 | $700k / $650k | Gonzalez, Williams, Vargas |
| Payments | 70.2 / 70.2 | 45 / 45 | 101.0 / 101.0 | $800k / $900k | Cramer, Masto, Vargas |
| Technology & Emerging Issues | 246.5 / 246.5 | 45 / 45 | 271.6 / 271.6 | $2250k / $2200k | Cuellar, Smith, Horsford |
| Fraud Prevention | 390.7 / 390.7 | 45 / 45 | 408.6 / 408.6 | $2200k / $2200k | LaLota, Budd, Tillis |
| Data Privacy & Cybersecurity | 368.1 / 368.1 | 44 / 44 | 390.4 / 390.4 | $2050k / $2050k | Cuellar, Courtney, Hayes |
| Charter Modernization & Governance | 207.7 / 207.7 | 45 / 45 | 230.1 / 230.1 | $2100k / $2100k | Davis, Gallego, Soto |
| Defense Credit Union Issues | 208.9 / 208.9 | 45 / 45 | 242.4 / 242.4 | $150k / $300k | Tillis, Cramer, Peters |
| Field of Membership | 84.8 / 84.8 | 45 / 45 | 111.2 / 111.2 | $900k / $1100k | Barr, Williams, Gottheimer |
| CDFI Fund | 276.9 / 276.9 | 45 / 45 | 297.2 / 297.2 | $2100k / $2100k | Cuellar, Mace, Issa |
| CFPB Restrain | 156.7 / 156.7 | 45 / 45 | 184.2 / 184.2 | $2100k / $2100k | Masto, Horsford, Warner |
| Telephone Consumer Protection Act Issues | 126.2 / 126.2 | 45 / 45 | 157.8 / 157.8 | $800k / $800k | Gonzalez, Lawler, Meuser |
| Credit Card & Consumer-Fee Mandates | 72.4 / 72.4 | 45 / 45 | 99.2 / 99.2 | $1450k / $1250k | Gonzalez, Masto, Emmer |
| Member Business Lending | 349.4 / 349.4 | 44 / 44 | 372.0 / 372.0 | $2200k / $2200k | Hayes, Soto, Bynum |
| Mortgage Lending & Housing | 299.7 / 299.7 | 45 / 45 | 320.2 / 320.2 | $2100k / $2100k | Cuellar, Issa, Ciscomani |
| Credit Union Tax Status | 62.3 / 62.3 | 45 / 45 | 107.6 / 107.6 | $500k / $650k | Tillis, Gonzalez, Sullivan |

Seed picks that changed: 0 of 808 before-picks are no longer picked; 0 new. Pot per seed fixed at $50k (CAP): unchanged.

## Budget frontier (electoral mode) (lev -> c)

| topic | base spread before/after | seeds before/after | final spread before/after | knee before/after | first seeds after |
|---|---|---|---|---|---|
| Examination & Supervision | 206.7 / 206.7 | 60 / 60 | 240.2 / 240.2 | $3000k / $3000k | Gonzalez, Perez, Issa |
| Credit Union Capital Requirements | 248.8 / 248.8 | 60 / 60 | 280.6 / 280.8 | $3000k / $3000k | Cuellar, Gottheimer, Budd |
| NCUA Budget & Share Insurance Fund | 280.4 / 280.4 | 60 / 60 | 315.5 / 315.8 | $3000k / $3000k | Hill, Green, Subramanyam |
| Interchange | 4.5 / 4.5 | 49 / 49 | 64.9 / 64.9 | $750k / $850k | Gonzalez, Williams, Cramer |
| Payments | 59.4 / 59.4 | 53 / 53 | 101.7 / 101.7 | $600k / $1250k | Tillis, Fitzpatrick, Cramer |
| Technology & Emerging Issues | 220.8 / 220.8 | 60 / 60 | 261.4 / 261.8 | $3000k / $3000k | Klobuchar, Sullivan, Smith |
| Fraud Prevention | 366.9 / 366.9 | 60 / 60 | 399.5 / 399.6 | $3000k / $3000k | Budd, Murkowski, Tillis |
| Data Privacy & Cybersecurity | 341.2 / 341.2 | 60 / 60 | 378.5 / 378.6 | $3000k / $3000k | Gonzalez, Cuellar, Budd |
| Charter Modernization & Governance | 186.1 / 186.1 | 60 / 60 | 223.7 / 223.9 | $3000k / $3000k | Hill, Davis, Cuellar |
| Defense Credit Union Issues | 194.8 / 194.8 | 60 / 60 | 240.8 / 240.9 | $200k / $750k | Tillis, Sullivan, Hyde-Smith |
| Field of Membership | 80.0 / 80.0 | 50 / 50 | 111.2 / 111.2 | $1200k / $1250k | Barr, Williams, Gottheimer |
| CDFI Fund | 248.7 / 248.7 | 60 / 60 | 289.1 / 289.4 | $2950k / $3000k | Cuellar, Mace, Sullivan |
| CFPB Restrain | 134.4 / 134.4 | 60 / 60 | 177.6 / 177.8 | $2200k / $2850k | Fitzpatrick, Cuellar, Masto |
| Telephone Consumer Protection Act Issues | 117.2 / 117.2 | 54 / 54 | 157.8 / 157.8 | $1300k / $1200k | Gonzalez, Meuser, Lawler |
| Credit Card & Consumer-Fee Mandates | 64.3 / 64.3 | 60 / 60 | 99.2 / 99.2 | $1450k / $1450k | Gonzalez, Masto, Emmer |
| Member Business Lending | 317.2 / 317.2 | 60 / 60 | 355.6 / 356.1 | $3000k / $3000k | Hayes, Soto, Hurd |
| Mortgage Lending & Housing | 275.0 / 275.0 | 60 / 60 | 311.5 / 311.6 | $3000k / $3000k | Cuellar, Ciscomani, Budd |
| Credit Union Tax Status | 52.1 / 52.1 | 56 / 56 | 107.6 / 107.6 | $500k / $800k | Tillis, Gonzalez, Sullivan |

Seed picks that changed: 35 of 1042 before-picks are no longer picked; 35 new. Pot per seed fixed at $50k (CAP): unchanged.

compet_mult flag recorded in the after files: coalition True, electoral True.

## lt_priming (Mortgage & Housing, default topic)

primeable targets before/after: 67 / 67; total cost sum before/after: $42,127,254 / $33,838,632.
Largest cost cuts (member: before -> after): Jon Ossoff $4,250,448 -> $2,143,861; April McClain Delaney $2,176,217 -> $1,405,088; Beth Van Duyne $4,494,386 -> $3,744,356; Mariannette Miller-Meeks $1,660,612 -> $1,148,363; Ann Wagner $1,958,291 -> $1,506,924; Gabe Evans $854,304 -> $427,152; Tom Barrett $718,112 -> $359,056; Kristen McDonald Rivet $386,234 -> $193,117; Ryan Zinke $686,685 -> $502,007; Joe Courtney $584,942 -> $403,595.

