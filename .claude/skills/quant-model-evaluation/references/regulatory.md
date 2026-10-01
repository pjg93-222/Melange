# Regulatory and standards — quant-model-evaluation reference

> **Load when:** a system's inputs, outputs or methods may fall under law, supervisory guidance, a voluntary standard, platform terms or research-ethics norms; a document cites a regulation or standard; you need model-risk practice (inventory, tiering, validation, monitoring, effective challenge) as evaluation steps; or you must pick a reporting guideline for a model study. **Not for:** whether a legal citation is well formed or current *as a citation* (`citation.md`, flag C); simulation V&V mechanics (`engineering-simulation.md`); run records, hashing and lineage (`automation.md`).
> Statuses were verified on 2026-09-29 (rows marked as re-read, on 2026-09-30) and are stated as of 2026-09-30. They change: re-verify on the use date (§2.8).
> **Not legal advice.** This module organizes evidence for review; it cannot decide applicability or compliance. Route every deliverable that touches individual contributors, voter files, personal data or platform content, and every open DIRECT (conditional) blocker, to counsel before release. Title such outputs "Draft evidence review for owner and counsel assessment", never "compliant", "certified" or "audit pass".

## 1. Assumption map

| Assumption (class) | Where it usually hides | What breaks if it is false | Tests |
|---|---|---|---|
| The framework the documents cite is current (LEGAL) | Methods sections, validation reports, model policies | "Current requirements" rest on superseded text (e.g. SR 11-7) | §2.8; REG-07; `citation.md` flag C |
| An instrument does, or does not, apply (LEGAL) | Scope statements, disclaimers, "research only" labels | Missed duties, or controls built for the wrong regime | §2.2; REG-48, REG-64..66 |
| Public records may be used for any purpose (LEGAL) | Ingestion code, exports, UI, client deliverables | FEC sale-or-use breach; terms-of-service breach; privacy duties on inferences | §2.4; REG-51..58 |
| The component is not a "model", so needs no validation (DECISION) | Inventory exclusions, "just a spreadsheet" composites | Fitted or theory-weighted scores escape testing | §2.3; REG-01..03 |
| Aggregates reconcile to their sources (DATA) | Roll-ups, joins, de-duplication | Silent double counts or gaps in money totals | REG-14..17, REG-21 |
| Disclosed amounts are exact (DATA) | Lobbying income and expense fields | False precision in efficiency ratios | REG-19, REG-22 |
| Lobbying of individual legislators is observed (MEASUREMENT) | Member-level lobbying features | Circular validation of an inferred link | REG-20 |
| Expert-set weights and dials need no outcome evidence (DECISION) | Config constants, "calibrated" dials | Untested judgment drives T1 decisions | REG-26; `scripts/global_sensitivity.py` |
| A calendar review cycle catches drift (STATISTICAL) | Validation schedules | A regime change (new session, redistricting, rule change) goes unseen | REG-28, REG-29 |
| Score explanations reflect the model's drivers (PRESENTATION) | Reason codes, "why ranked high" text | Unfaithful explanations reach decision-makers | REG-49 |
| The objective serves the client (DECISION) | Objective functions, allocation rules | Recommendations that favour the operator | REG-50 |
| LLM-written text and labels are faithful (MEASUREMENT) | Briefs, narratives, classifier labels | Confabulated facts reach readers | REG-44..47 |
| Simulation output is credible for this decision (COMPUTATIONAL) | Monte-Carlo, agent-based and cascade engines | Decisions rest on noise or unvalidated logic | REG-33..42; `engineering-simulation.md` |
| The report is complete enough to appraise (PRESENTATION) | Papers, model cards, briefs | Readers cannot judge validity | §2.7 |

## 2. Procedures

### 2.1 Status register (as of 2026-09-30)

Tags: **[P]** primary or official source read 2026-09-29, or re-read 2026-09-30 where the row says so; **[S]** reputable secondary source (law firm, standards distributor, trade press) used because the primary was unreachable or silent; **[K]** established background, not re-fetched; **STATUS-UNVERIFIED** means current status could not be confirmed. IDs are the source tags used in §3. Links go to the issuer's page. Re-verify before relying on any row (§2.8).

| ID | Instrument | Issuer | Date | Status as of 2026-09-30 | Tag | Applicability pattern |
|---|---|---|---|---|---|---|
| A1 | [SR 26-2](https://www.federalreserve.gov/supervisionreg/srletters/SR2602.htm) / [OCC 2026-13](https://www.occ.gov/news-issuances/bulletins/2026/bulletin-2026-13.html) / [FDIC FIL-15-2026](https://www.fdic.gov/news/financial-institution-letters/2026/agencies-revise-interagency-model-risk-management-guidance), Revised Guidance on Model Risk Management | FRB, OCC, FDIC | 2026-04-17 | In force as non-binding supervisory guidance; most relevant to banks above $30B; generative and agentic AI out of scope; the promised AI/model-risk RFI is STATUS-UNVERIFIED | [P] | DIRECT for in-scope US banks; reaches a vendor through the bank's vendor-model duties (Section VII); BY-ANALOGY otherwise |
| A1 (old) | SR 11-7 and SR 21-8; OCC 2011-12, 1997-24, 2021-19 and the MRM Handbook booklet | FRB, OCC | 2011-04-04 (SR 11-7) | SUPERSEDED or rescinded 2026-04-17; the SR 11-7 page returns HTTP 404 | [P] | History only: cite "(superseded by SR 26-2)" |
| A1b | [OCC Bulletin 2025-26](https://www.occ.gov/news-issuances/bulletins/2025/bulletin-2025-26.html), MRM clarification for community banks | OCC | 2025-10-06 | In force (not on the 2026-13 rescission list); no annual-validation requirement for banks up to $30B | [P] | BY-ANALOGY: proportionality template for small teams |
| A2 | FDIC FIL-22-2017 (applied SR 11-7 to FDIC banks of $1B or more) and FIL-27-2021 | FDIC | 2017-06-07 | SUPERSEDED 2026-04-17 by FIL-15-2026; the FIL-22-2017 page is marked inactive (re-read 2026-09-30) | [P] | History only |
| A3 | [NCUA model-risk expectations](https://publishedguides.ncua.gov/examiner/content/examinersguide/SensitivityMarketRisk/EvaluatingIRR/Measurement/ModelRisk.htm) (IRR examiner guidance; 12 CFR 741.3(b)(5)) | NCUA | guide pages 2024-12-06; 26-CU-01 2026-01 | No stand-alone MRM rule; no adoption of SR 11-7 or SR 26-2 found (STATUS-UNVERIFIED); GAO-25-107197's call to update MRM guidance is open | [P]/[S] | DIRECT for credit-union IRR models; a credit-union client carries vendor-review duties; BY-ANALOGY otherwise |
| A4 | [PRA SS1/23](https://www.bankofengland.co.uk/prudential-regulation/publication/2023/may/model-risk-management-principles-for-banks-ss) (five principles) | Bank of England PRA | 2023-05-17; effective 2024-05-17; amended 2026-04-23 | In force as amended; internal-model firms' stress-test models now in scope (amendment details [S]) | [P]/[S] | DIRECT for UK banks with internal-model approval; BY-ANALOGY otherwise |
| A5 | [OSFI Guideline E-23](https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/guideline-e-23-model-risk-management-2027) | OSFI (Canada) | final 2025-09-11 | Final, effective 2027-05-01; its model definition includes AI/ML and judgment-based assumptions | [P] | DIRECT for Canadian federally regulated institutions from 2027-05-01; BY-ANALOGY otherwise |
| A6 | [ECB guide to internal models](https://www.bankingsupervision.europa.eu/ecb/pub/pdf/ssm.supervisory_guide_egim_202606.en.pdf) | ECB Banking Supervision | revised 2025-07-28; updated 2026-06 | In force (June 2026 version); ML models must be explainable and their performance must justify their complexity | [P] | DIRECT for SSM banks' internal models; BY-ANALOGY otherwise |
| A7 | [BCBS 239](https://www.bis.org/publ/bcbs239.htm), risk data aggregation and reporting (14 principles); ECB RDARR guide (2024-05) | BCBS; ECB | 2013-01-09 | In force, unrevised; RDARR revision planned for Q4 2026 | [P] (principles 1-2, 7-14 [S]) | DIRECT for supervised banks; BY-ANALOGY as the data-lineage template |
| A8 | [Community Reinvestment Act](https://www.federalreserve.gov/consumerscommunities/community-reinvestment-act-2025-notice-of-proposed-rulemaking.htm), 12 U.S.C. §2901 et seq. [K]; rules: OCC 12 CFR 25, FDIC 12 CFR 345, Fed Regulation BB | Congress (1977); OCC, FRB, FDIC | 2023 final rule 89 FR 6574 (2024-02-01); rescission proposal 90 FR 34086 (2025-07-18); OCC-FDIC proposal 91 FR 52114 (2026-08-12) | The 2023 final rule never applied: on 2024-03-29 a federal district court preliminarily enjoined its enforcement and extended its dates for as long as the injunction lasts. All three agencies still apply the pre-2024 rules, based on the 1995 framework. OCC and FDIC chose not to finalize the 2025 rescission and proposed new rules instead (comments to 2026-10-13). The Board's rescission proposal is pending, with no final Board action in the Federal Register as of 2026-09-30. 2026 thresholds (Fed and FDIC): small bank below $1.649B, intermediate small bank from $412M (read 2026-09-30) | [P] | DIRECT for insured depository institutions (banks, savings associations); federal CRA does not cover credit unions; a model using CRA ratings, assessment areas or tract lists must name the framework behind them (REG-67); BY-ANALOGY otherwise |
| B1 | [NIST AI RMF 1.0](https://www.nist.gov/itl/ai-risk-management-framework) (AI 100-1) and Playbook | NIST | 2023-01-26 | Voluntary; NIST says it is under revision; no successor released; critical-infrastructure profile concept note 2026-04-07 | [P] | DIRECT (voluntary) for ML and LLM components |
| B2 | NIST AI 600-1, Generative AI Profile (same page) | NIST | 2024-07-26 | Voluntary; no revision found | [P] | DIRECT (voluntary) for LLM text and labels; fills the SR 26-2 gap |
| B3 | [ISO/IEC 42001:2023](https://www.iso.org/standard/42001), AI management system | ISO/IEC JTC 1/SC 42 | 2023-12 [K] | In force per a distributor listing (EN ISO/IEC 42001:2026, CEN approval 2026-03-13, text unchanged); iso.org returned 403 | [S] | BY-ANALOGY unless certification is sought |
| B4 | [ISO/IEC 23894:2023](https://www.iso.org/standard/77304.html), AI risk-management guidance | ISO/IEC JTC 1/SC 42 | 2023-02 | STATUS-UNVERIFIED (iso.org 403; no revision found) | [S] | BY-ANALOGY: the ISO 31000 cycle applied to AI |
| B5 | [EU AI Act, Reg. (EU) 2024/1689](https://eur-lex.europa.eu/eli/reg/2024/1689/oj) | EU Parliament and Council | in force 2024-08-01 [K] | Phased: prohibitions and AI literacy from 2025-02-02, general-purpose AI from 2025-08-02 [K]; Art. 50 transparency 2026-08-02 [S], with systems on the market before 2026-08-02 given until 2026-12-02 to meet Art. 50(2) [P] | [K]/[S]/[P] | DIRECT only if a system is placed on the EU market or its output is used in the Union |
| B5 | [Digital Omnibus on AI, Reg. (EU) 2026/1744](https://eur-lex.europa.eu/eli/reg/2026/1744/oj/eng) | EU Parliament and Council | adopted 2026-07-08 | Published in OJ L on 2026-07-24; in force 2026-07-27; Annex III high-risk duties from 2027-12-02, Annex I from 2028-08-02 (EUR-Lex, re-read 2026-09-30) | [P] | As above; re-classify whenever an output is offered or used in the EU |
| B6 | [Colorado SB 26-189](https://leg.colorado.gov/bills/sb26-189) (repeals and re-enacts SB 24-205, which never took effect) | Colorado | signed 2026-05-14 | Effective 2027-01-01; ADMT notices and adverse-outcome explanations; AG rules due by 2027-01-01 | [P] | DIRECT only if an output makes, or is a substantial factor in, a consequential decision about a Colorado consumer |
| B7 | US federal AI policy: EO 14179; OMB M-25-21; EO 14281 (disparate-impact enforcement deprioritized); AI Action Plan; EO 14365 (targets state AI laws); National Policy Framework | White House; OMB | 2025-01-23 to 2026-03-20 | Executive policy in force; no federal preemption statute enacted as of Sept 2026 | [K]/[S] | BY-ANALOGY context; binds federal agencies, not private analysts |
| B8 | [SEC predictive data analytics proposal, S7-12-23](https://www.sec.gov/rules-regulations/2025/06/s7-12-23) | SEC | proposed 2023-07-26 | WITHDRAWN 2025-06-12 (effective 2025-06-17); no final rule intended | [P] | NOT-APPLICABLE as law; the operator-conflict test transfers BY-ANALOGY |
| B9 | [CFPB Circulars 2022-03, 2023-03 and 2024-06](https://www.consumerfinance.gov/compliance/guidance/withdrawn-guidance/) (adverse action, complex algorithms, worker scores) | CFPB | withdrawn 2025-05-12 | WITHDRAWN | [P] | NOT-APPLICABLE; the specific-reasons fidelity idea transfers BY-ANALOGY |
| B9 | [Reg B (ECOA) final rule](https://www.consumerfinance.gov/rules-policy/regulations/1002/) | CFPB | published 2026-04-22 | In force 2026-07-21; removes the effects test; the 12 CFR 1002.9 specific-reasons duty is unchanged [K] | [S] | DIRECT for creditors only |
| C1 | [52 U.S.C. §30111(a)(4)](https://www.law.cornell.edu/uscode/text/52/30111); [11 CFR §104.15](https://www.law.cornell.edu/cfr/text/11/104.15); [FEC guidance](https://www.fec.gov/updates/sale-or-use-contributor-information/) and advisory opinions (§2.4) | Congress; FEC | rule 1980, amended 1996; guidance 2018-11-02 | In force | [P] | DIRECT for anyone using individual contributor information copied from FEC reports |
| C2 | [Lobbying Disclosure Act, 2 U.S.C. §1601 et seq.](https://www.law.cornell.edu/uscode/text/2/1604); [lda.gov API terms](https://lda.gov/api/tos/) | Congress; Secretary of the Senate; Clerk of the House | 1995, amended 2007 [K] | In force; lda.senate.gov 301-redirects to lda.gov (observed 2026-09-29); filing quality measured in GAO-26-108486 (2026-06-30) | [P] | DIRECT for any system using LD-1, LD-2 or LD-203 data |
| C3 | [Foreign Agents Registration Act](https://www.justice.gov/nsd-fara); [22 U.S.C. §613(h)](https://www.law.cornell.edu/uscode/text/22/613) | DOJ NSD FARA Unit | 1938 | In force; eFile requires DOJ Login with MFA from 2026-02-06 | [P] | BY-ANALOGY unless foreign-principal lobbying is in scope, then DIRECT as a data source |
| C4 | [State voter-file use restrictions](https://www.ncsl.org/elections-and-campaigns/access-to-and-use-of-voter-registration-lists) (NCSL survey) | State legislatures | survey 2026-06-10 | Current; most states restrict use to non-commercial, election or political purposes | [P] | DIRECT (conditional) on any input derived from a voter file |
| C5 | [X Developer Agreement](https://docs.x.com/developer-terms/agreement) | X Corp. | updated 2026-04-27 | In force | [P] | DIRECT for X content collected or licensed |
| C5 | [Bluesky Developer Guidelines](https://bsky.network/docs/developer-guidelines/) | Bluesky Social PBC | undated | In force | [P] | DIRECT for Bluesky data collected |
| C6 | Scraping case law: *Van Buren v. United States*, 593 U.S. 374 (2021); *hiQ Labs v. LinkedIn*, 31 F.4th 1180 (9th Cir. 2022) and the 2022 consent judgment; *Meta Platforms v. Bright Data* (N.D. Cal. 2024) | US courts | 2021-2024 | As summarized: public, logged-out collection carries low CFAA risk; contract and trespass claims remain | [S] | DIRECT for any scraper |
| D1 | [Common Rule, 45 CFR 46](https://www.hhs.gov/ohrp/regulations-and-policy/regulations/common-rule/index.html) | HHS OHRP and Common Rule agencies | 2018 Requirements; compliance 2019-01-21 [K] | In force; an exemption-widening proposed rule was on the HHS agenda, unpublished when checked [S] | [P] | DIRECT for federally conducted or supported research; BY-ANALOGY otherwise |
| D2 | [APSA Principles and Guidance for Human Subjects Research](https://apsanet.org/resources/ethics/) | APSA | approved 2020-04-04 [S]; in the ethics guide 2022-02, updated 2023-05 | In force as a professional norm | [P] | BY-ANALOGY; a norm for APSA members |
| D3 | [AoIR Internet Research Ethical Guidelines 3.0](https://aoir.org/reports/ethics3.pdf) | AoIR | 2019 (document dated 2020) | Current as far as found; no successor found, none ruled out | [S] | BY-ANALOGY for social-media text |
| D4 | [DA-RT and the Journal Editors' Transparency Statement (JETS)](https://www.dartstatement.org/2014-journal-editors-statement-jets) | APSA; journal editors | 2014; implemented by 2016-01-15 | In force at signatory journals (27 at first); contested | [P] | DIRECT when publishing there; BY-ANALOGY otherwise |
| D5 | [TOP Guidelines and TOP 2025](https://www.cos.io/initiatives/top-guidelines) | Center for Open Science | 2015; TOP 2025 published 2026 | TOP 2025 is current | [P] | BY-ANALOGY unless a journal or funder adopts it |
| D6 | [AEA Data and Code Availability Policy](https://www.aeaweb.org/journals/data/data-code-policy); [SSDE README template v1.1](https://social-science-data-editors.github.io/template_README/) | AEA; Social Science Data Editors | policy 2026-02; template 2022 | In force | [P] | DIRECT for AEA submissions; BY-ANALOGY as the replication-package standard |
| D7 | Preregistration: [OSF Registries](https://osf.io/registries) (now hosts EGAP) and the [AEA RCT Registry](https://www.socialscienceregistry.org) | COS; EGAP; AEA | — | Operating | [S] | BY-ANALOGY for confirmatory tests |
| E1 | [ASME V&V 10-2019 (reaffirmed 2025), V&V 20-2009 (reaffirmed 2021), V&V 40-2018, VVUQ 1-2022](https://www.asme.org/codes-standards/publications-information/verification-validation-uncertainty) | ASME | editions 2009-2022; reaffirmations to 2025 | Voluntary consensus standards; V&V 40 reaffirmation STATUS-UNVERIFIED | [P]/[S] | BY-ANALOGY for simulation engines |
| E2 | [NASA-STD-7009B](https://standards.nasa.gov/standard/NASA/NASA-STD-7009), Standard for Models and Simulations | NASA Office of the Chief Engineer | approved 2024-03-05 | In force; a later revision is not ruled out (standards page unreachable) | [P] | BY-ANALOGY |
| E3 | ODD protocol (2006, 2010, 2020) and TRACE (2010, 2014, 2021 notebooks) | Grimm and co-authors (§5) | 2006-2021 | Voluntary; ODD 2020 is current | [K] | DIRECT (voluntary) for agent-based and diffusion simulations |
| E4 | Sargent, verification and validation of simulation models (§5) | Methodological literature | 2013 | Canonical method reference | [K] | DIRECT (voluntary) for simulation engines |
| F1 | [GDPR, Reg. (EU) 2016/679](https://eur-lex.europa.eu/eli/reg/2016/679/oj); [EDPB Guidelines 3/2018](https://www.edpb.europa.eu/documents/guideline/guidelines-32018-on-the-territorial-scope-of-the-gdpr-article-3-version-adopted_en) | EU; EDPB | applies 2018-05-25 [K]; guidelines 2019-11-12 | In force; a data omnibus narrowing "personal data" was still under negotiation in Sept 2026 [S] | [K]/[S] | NOT-APPLICABLE without an EU establishment, EU offering or EU monitoring (Art. 3); check EU-address records |
| F2 | [CCPA/CPRA](https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=CIV&sectionNum=1798.140); CPPA regulations; Delete Act (SB 362, [DROP](https://privacy.ca.gov/drop-for-data-brokers/)) | California; CPPA; Attorney General | thresholds 2025-01-01; regulations 2026-01-01 | In force; revenue threshold $26,625,000; inferences are personal information even when drawn from public data (AG Op. 20-303) [S]; ADMT duties from 2027-01-01 [S]; DROP deletions every 45 days from 2026-08-01 [P] | [P]/[S] | DIRECT (conditional) on meeting a "business" threshold or selling personal information |
| F3 | [Other state comprehensive privacy laws](https://fpf.org/wp-content/uploads/2025/12/FPF-Anatomy-of-a-State-Comprehensive-Privacy-Law-Report.pdf) (FPF survey) | 19 states | survey 2025-12 | 19 laws; 9 amended in 2025; 12 of 19 broadly exempt nonprofits | [P] | BY-ANALOGY unless a state's thresholds are met |

### 2.2 Assign an applicability label

- **Tests:** does each register row bind, cover, inform or not touch the system under audit?
- **Labels.** `DIRECT`: the requirements bind the operator, or the data it uses, as written. `DIRECT (voluntary)`: a voluntary standard whose scope squarely covers an artifact of the system; it binds once the owner adopts or claims it. `DIRECT (conditional)`: applies only if a stated fact is true; name the fact and who can confirm it, and carry it as an open blocker until confirmed. `BY-ANALOGY`: neither binds nor covers, but its checks transfer; word them as retained good practice, never "required by". `NOT-APPLICABLE`: neither binds nor fits; record the reason and the trigger that would change it, and keep any useful checks tagged BY-ANALOGY.
- **Assumptions of the procedure:** the row is current on the use date (§2.8); facts about the operator, data and territory come from the owner, and are recorded as `[OWNER]` evidence.
- **Run it.** For each row, answer five scope questions and write the answers into the assumption register (class LEGAL, evidence tag `[REG]` with the status date):
  1. *Entity:* is the operator, or whoever relies on the outputs, a covered entity (a bank above a threshold, a creditor, a credit union, a "business" under a privacy law, a journal author)?
  2. *Data and activity:* does the system use covered data (FEC contributor fields, LDA filings, voter files, platform content, personal data), or do covered things (consequential decisions about consumers, credit scoring, content shown to voters)?
  3. *Territory:* where are outputs offered or used (EU market, a US state)?
  4. *Time:* is the instrument in force on the use date? Watch 2027-01-01, 2027-05-01 and 2027-12-02.
  5. *Function over label:* judge by what outputs do and who relies on them; a "research only" label, a disclaimer or "human in the loop" does not by itself change status.
- **Flip triggers to record:** a bank client relies on outputs (vendor-model documentation under A1); an output is offered or used in the EU (re-run B5); a voter-file input appears (C4); a revenue or consumer-count threshold is crossed (F2); an output feeds a credit, housing, employment or insurance decision (B6, B9).
- **Pass criterion:** every row has a label, a one-line reason and a flip trigger; only DIRECT (conditional) rows rest on unconfirmed facts, and they are listed as blockers.
- **Failure signature:** blanket "not applicable" with no reason; an unknown fact defaulted to NOT-APPLICABLE ("not assessed" is not "not applicable"); voluntary frameworks called mandatory, or binding law called optional; one checklist blending regimes that answer different questions.
- **Verdicts:** a LEGAL assumption SURVIVES only when both the applicability reasoning and the compliance evidence were checked; UNVERIFIED-HERE when either cannot be; KILLED for a material breach, after a second reader, routed to counsel.

### 2.3 Model-risk practice as evaluation steps

- **Tests:** is each model governed, tested and monitored in proportion to what rides on it?
- **Assumptions of the procedure:** SR 26-2 is principles-based and non-binding. It no longer lists the SR 11-7-era techniques (sensitivity analysis, benchmarking, process verification of code, override analysis, early-warning metrics); keep them as retained good practice (2011 lineage) and never cite them as current requirements [S]. The skill's materiality tiers T1-T3 stand in for the guidance's materiality axis.
1. **Inventory and tiering** (REG-01..06). A model is a complex quantitative method that applies statistical, economic or financial theory to turn inputs into estimates; simple arithmetic and deterministic rules with no such theory are excluded (the 2026 text dropped the word "mathematical" [P]). A composite score with fitted or theory-derived weights is a model; OSFI E-23 also counts AI/ML methods and judgment-based assumptions. Record ID, name, purpose, owner, developer, origin, inherent risk (assumptions, complexity, input quality, data limits), materiality (exposure × purpose), tier and re-tier triggers. Watch immaterial models for conditions that would make them material. List shared data, assumptions and code, and test what a shared-component failure does (aggregate risk; `scripts/mutation_check.py` for vacuous checks).
2. **Conceptual soundness** (REG-08..13). Document design choices, assumptions, judgments and data selection; test at least one alternative specification or method; where theory review is impractical, use interpretability measures or benchmarking. Keep a simpler benchmark and show the gain justifies the complexity (A6). Check omitted drivers and borrowed parameters. For money-to-outcome efficiency claims, state the causal assumptions (`social-science.md`, `scripts/confounding_sensitivity.py`).
3. **Data quality and lineage** (REG-14..24). Use BCBS 239's aggregation principles as tests: accuracy and integrity (reconcile to source totals, log breaks), completeness (coverage by period, entity and source), timeliness (freshness per input), adaptability (ad hoc questions answered without one-off manual joins). Keep one data dictionary and lineage map with owners (`automation.md`). Screen training data for relevance, representativeness, errors, completeness and bias.
4. **Outcomes analysis and backtesting** (REG-25..27). Compare outputs with realized outcomes against thresholds fixed before looking, out of sample and out of time; a random split of one source is not external validation. Judgment-based models need quantitative outcome evidence of that judgment. Back-test behavioural assumptions, not only outputs. Never move a threshold after seeing performance. Run `scripts/backtest_eval.py` (against naive and seasonal-naive benchmarks) and `scripts/calibration_report.py` (probabilities).
5. **Ongoing monitoring and drift triggers** (REG-28, REG-29). Set frequency by risk and rate of change: SR 26-2 has no fixed annual cycle and OCC 2025-26 drops annual validation for community banks, but every model keeps a floor of an inventory entry plus performance monitoring. Write triggers for regime change (a new legislative session, redistricting, rule or source changes, new data vintages) and a response ladder: overlay, then recalibration, then redevelopment. Revalidate on material change in code, data source or parameter regime.
6. **Limitations and overlays** (REG-27, REG-31, REG-40). Give every limitation a mitigant: a use restriction, an overlay with rationale and expiry, or closer monitoring. Use beyond the intended purpose needs new analysis; use before validation needs restriction, close monitoring and disclosure. Warn decision-makers explicitly when acceptance criteria fail or limits are breached.
7. **Effective challenge and findings log** (REG-30). The reviewer needs expertise, independence from the developer and the standing to force change; manage developer-validator conflicts; log findings, responses, exceptions and remediation; internal audit evaluates the process rather than redoing it. This is the skill's second-reader rule for KILLED. Give every release gate or human-review checkpoint a traceability row (source, rationale, owner, status) with positive, negative, boundary and missing-input tests, and check the gate set for orphans, conflicts, cycles and paths that bypass human review.
8. **Vendor and third-party inputs** (REG-11). Validate vendor data, parameter values and models; understand their design, development data and performance; monitor their outcomes; justify any customization. Send generative and agentic components to the AI 600-1 control set (§2.5).
9. **Decommissioning** (REG-32). Retire models formally: date, reason, successor, the outputs that stop, and the prior version kept.
- **Pass criterion (default; the owner may set another before testing):** T1 has evidence for every step or an owner-signed exception; T2 has steps 1, 3, 4 and 5; T3 has the floor (inventory entry and performance monitoring).
- **Failure signature:** composite scores missing from the inventory; validation by calendar only; limitations without mitigants; the developer as the only reviewer; SR 11-7 cited as current.

### 2.4 Data-use screen for political-finance inputs

- **Tests:** may the system use each input the way it does, and do its deliverables stay inside that use?
- **Run it:** trace each person-level field from source to every feature, table, export and screen (REG-51); apply the rules below; write a use statement (purpose, aggregation level, recipients) for counsel.
- **FEC sale-or-use (C1).** Information copied from FEC reports may not be sold or used to solicit contributions of any kind, charitable included, or for commercial purposes; the one exception lets a committee's name and address be used to solicit that committee. News, books and similar works are allowed unless their principal purpose is passing on contributor information. The Commission asks whether a use touches the privacy concerns behind the ban, above all list-making and enabling solicitation of individual contributors; being for-profit is not, alone, what makes a use commercial. Committees may salt each report with up to 10 pseudonyms.

| Advisory opinion (requester), date | Holding (paraphrase) |
|---|---|
| 2021-05 (Tally Up), 2021-05-17 [P] | Prohibited: segment scores built from aggregated FEC data, delivered with segment members' names and contacts, despite a 100-person floor |
| 2017-08 (Point Bridge Capital), 2017-08-17 [P] | Permitted: company indexes built from aggregated, non-personally-identifiable contribution data |
| 2015-12 (Ethiq); 2013-16 (PoliticalRefund.org) | Permitted: aggregated matching of users to candidates and firms; aggregate counts |
| 2014-07 (Crowdpac), 2014-08-14 [P] | Permitted: contributor data feeding position-inference algorithms, with totals displayed and no contact information disclosed; contributors' names, cities and states could also be shown to explain the algorithm |
| 2009-19 (Club for Growth PAC) | Permitted: telling contributors about their refund rights |
| 2022-10 (Sprinkle / Platform Venture Studio), 2022-07-28 [P] | Permitted: aggregated candidate-level data that does not identify contributors |
| 2022-03 (Democracy Engine), 2022-06-27 [P] | The restriction does not reach contribution data from non-FEC sources |
| 2004-24 (NGP Software), 2004-08-12 [P]; 1985-16 (Weiss), 1985-05-24 [P]; 1995-05 (TRIM) | Prohibited: merging contribution histories into donor databases; screening a list vendor's names against contributors; copying names to mail solicitations |
| 1986-25 (Public Data Access), 1986-08-15 [P] | Prohibited: selling compilations mainly of contributor names, even without street addresses; academic use may be permissible without solicitation or commercial use |
| AOR 2021-01 (Aluminate) | No opinion (no four votes) on fundraising services for universities and nonprofits |

Rows marked [P] were read as final opinions on fec.gov (all eight re-read 2026-09-30). Rows without [P] were verified as described in AO 2021-05 or on fec.gov landing pages. Courts cited in the AOs: *FEC v. Legi-Tech*, 967 F. Supp. 523 (D.D.C. 1997); *FEC v. Political Contributions Data*, 943 F.2d 190 (2d Cir. 1991); *FEC v. American International Demographic Services*, 629 F. Supp. 317 (E.D. Va. 1986).

- **LDA (C2).** LD-2 is due 20 days after each quarter, LD-203 30 days after each half-year. LD-2 names issues, bills, and the chambers and agencies contacted, never individual members. Income and expenses above $5,000 are rounded to the nearest $10,000; smaller amounts appear only as "less than $5,000". API terms: 120 requests/min with a key, 15/min anonymous; cite the access date; carry the Senate Office of Public Records disclaimer that it cannot vouch for the data or analyses derived from them; never present altered data as LDA.gov data. GAO-26-108486 (re-read 2026-09-30): 94% of filers could document income and expenses; an estimated 22% of LD-2 reports may not have properly disclosed lobbyists' covered positions (an estimate, with a maximum margin of error of 9 percentage points); 93% of LD-203 reports listed all contributions; 12,391 non-filing referrals in 2016-2025, about 46% closed in compliance by December 2025.
- **FARA (C3).** §613(h) exempts LDA registrants for some non-government foreign principals, so commercial foreign interests tend to appear in LDA data and foreign governments and parties in FARA data. Confirm any FARA collection path survived the 2026-02-06 DOJ Login change.
- **Voter files (C4).** Access and permitted use vary by state; most allow only non-commercial, election or political use; some add confidentiality terms or felony penalties; address-confidentiality participants are shielded almost everywhere.
- **Platforms (C5).** X: no targeting, segmenting or profiling of individuals by sensitive characteristics, explicitly including political affiliation or beliefs, without X's written approval; no surveillance or user tracking; no redistribution beyond the agreement; delete or modify content within 24 hours of a written request; no training or fine-tuning of foundation or frontier models. Bluesky: honor user deletions, secure stored data, and make no automated or bulk interactions that notify users.
- **Scraping (C6).** Collect only public, logged-out content; never circumvent blocks, rate limits or CAPTCHAs; stop on revoked access or a cease-and-desist; snapshot the site's terms with the data.
- **Human subjects (D1).** A human subject is a living person about whom a researcher obtains information through interaction, or obtains identifiable private information. Scholarly and journalistic work focused on specific individuals is excluded from "research". Exemption (d)(4) covers secondary use of identifiable private information that is public, or that is recorded so subjects are not readily identifiable, with no contact and no re-identification.
- **Privacy (F1-F3).** GDPR reaches a non-EU controller that offers goods or services to people in the Union or monitors their behaviour (Art. 3(2)); political opinions are special-category data (Art. 9); Art. 14 notices and Art. 35 impact assessments follow if it applies. A CCPA "business" has revenue above $26,625,000 (from 2025-01-01), or buys, sells or shares the data of 100,000 or more California consumers or households, or earns at least half its revenue from selling or sharing; public records and deidentified or aggregate data are excluded, but inferences about a person are not. Most state laws exempt publicly available data; only 12 of 19 broadly exempt nonprofits; California also covers employment-context data.
- **Pass criterion:** every person-level path has a documented use that fits each applicable rule, and no deliverable links identity or contact data to contribution-derived scores. This default is stricter than AO 2014-07, which let names, cities and states be shown to explain an algorithm; counsel decides whether a deliverable may rely on that opinion.
- **Failure signature:** contributor names in client exports; "it is public data" as the whole justification; lobbying amounts treated as exact; a scraper holding login credentials.

### 2.5 AI and LLM component screen

- SR 26-2 keeps traditional statistical models and non-generative, non-agentic AI in scope and excludes generative and agentic AI (its footnote 3). Route LLM components to NIST AI 600-1 and the AI RMF (REG-43..47).
- **AI RMF:** four functions (Govern, Map, Measure, Manage) and seven trustworthiness characteristics (valid and reliable; safe; secure and resilient; accountable and transparent; explainable and interpretable; privacy-enhanced; fair with harmful bias managed). Map each characteristic to at least one test.
- **AI 600-1** lists 12 generative-AI risks. A model audit tests at least confabulation, harmful bias and homogenization, data privacy, human-AI configuration, information integrity, and value chain and component integration.
- **EU AI Act Annex III.** Point 5(b) covers AI that evaluates natural persons' creditworthiness or sets their credit score; fraud detection is excepted. Point 8(b) covers AI intended to influence the outcome of an election or referendum, or how people vote in them. It excludes systems whose output people are not directly exposed to, such as tools that organize or optimize campaigns administratively or logistically. An Annex III system that profiles natural persons is always high-risk (Art. 6(3)) [K]. A model of legislators' votes is not a model of voters: record that reasoning (REG-48), and re-run it when outputs reach voters or the EU. The Omnibus also adds an Art. 5 ban on generating non-consensual intimate imagery or child sexual abuse material (from 2026-12-02) and an Art. 4a basis for processing special-category data to detect bias [P]; it also softens the AI-literacy duty [S].
- **Colorado SB 26-189** (from 2027-01-01). Developers give deployers intended-use documentation and notice of material updates. Deployers give clear and conspicuous notice, and within 30 days of an adverse outcome a plain-language account of the ADMT's role. Consumers can obtain and correct their data and get meaningful human review. Both sides keep records for 3 years. Covered decisions: education, employment, housing, financial or lending services, insurance, health care and essential government services. The AG enforces, with a 60-day cure period before 2030-01-01.
- **Withdrawn guidance** (B8, B9) is not evidence that a practice is sound. Keep the fidelity test (reasons are specific and match the drivers, REG-49) and the conflict test (the objective does not favour the operator, REG-50).

### 2.6 Simulation credibility and research transparency

- **V&V standards (E1-E4).** Keep code verification, solution verification and validation apart, using VVUQ 1 terms. V&V 20 judges validation by comparing the simulation-minus-data error with a combined validation uncertainty (numerical, input and data). V&V 40 sets credibility goals from model influence times decision consequence. NASA-STD-7009B keeps 43 record requirements, including intended use, criticality, acceptance criteria, assumptions, limits, permissible uses, data pedigree, domains of verification and validation, uncertainty, sensitivity, use and results assessments, explicit warnings to decision-makers (M&S 32) and assessed risk of reliance (M&S 49). ODD describes a model by overview, design concepts and details; TRACE documents it from problem formulation to output corroboration. Sargent separates data validity, conceptual model validity, computerized model verification and operational validity. Mechanics: `engineering-simulation.md`, `scripts/mc_error.py`, `scripts/global_sensitivity.py`.
- **Transparency (D4-D7).** TOP 2025 has seven practices (study registration, protocol, analysis plan, materials, data, code, reporting transparency) at three levels (Disclosed; Shared and Cited; Certified); two verification practices (results transparency; computational reproducibility); and four verification study types (replication, registered report, multiverse, many-analyst). The AEA policy (Feb 2026) requires data, code and computational details in a trusted repository; a README (data availability, computational requirements, instructions, program-to-output map); citation of all data; and a Data Editor reproducibility check. Restricted data are preserved for 5 years, with the code published. JETS asks for data deposit at publication, clear analytic procedures and data citation (author, title, date, version, persistent identifier). Registries time-stamp hypotheses, outcomes and analysis plans before outcomes are seen.
- **Ethics norms (D2, D3).** APSA 2020 groups its principles under power, consent, deception, harm and trauma, confidentiality, impact, laws and prospective review, and shared responsibility; the impact principle asks what outputs do to political processes beyond their users. AoIR 3.0 asks for ethics across the whole lifecycle, attention to context and user expectations, and protection of researchers.

### 2.7 Reporting-guideline map for model studies

- **Tests:** is the study reported fully enough for a reader to appraise it?
- **Rule:** a reporting guideline lists what to report. It is not a quality score, a risk-of-bias tool or a design method. Mark each item reported, partly reported, not reported, not applicable (with the reason) or not assessed. Appraise methods separately. If no guideline fits, say so instead of forcing the nearest one. Outside their home fields (clinical, health-economic, operational research) all rows are BY-ANALOGY.

| Study type | Guideline | Items that transfer | Pair with |
|---|---|---|---|
| Prediction or classification model (default risk, vote or flip probability, stance classifier) | TRIPOD+AI (Collins et al. 2024); replaces TRIPOD 2015; CrossRef lists a correction | Intended use and population; predictor and outcome timing; missing data; sample-size rationale; full specification; internal and external validation; discrimination and calibration with uncertainty; subgroup performance | `machine-learning.md`; `scripts/calibration_report.py`; `scripts/leakage_audit.py` |
| Observational study of administrative or routinely collected records (disclosure filings, votes, registries) | STROBE (von Elm et al. 2007) plus RECORD (Benchimol et al. 2015) | Selection, confounding, missing data, sensitivity analyses; RECORD adds code lists and algorithms, linkage, cleaning and data access | `social-science.md`; `scripts/regression_report.R` |
| Spending-efficiency, cost-effectiveness or budget-allocation evaluation | CHEERS 2022 (Husereau et al. 2022), 28 items | Perspective, comparators, time horizon, discounting, cost and outcome measurement, model assumptions, heterogeneity, distributional effects, uncertainty | `finance.md`; `scripts/dea_frontier.py`; `scripts/global_sensitivity.py` |
| Simulation study (Monte Carlo, discrete-event, agent-based) | STRESS-DES (Monks et al. 2019); ODD for agent-based models | Objectives, model logic, data, experimentation, implementation, code access | `engineering-simulation.md`; `scripts/mc_error.py` |
| Survey evidence | AAPOR Code of Professional Ethics and Practices and Disclosure Standards | Sponsor, population, frame, mode, field dates, exact wording, weighting, unweighted bases, response-rate definitions, precision and its assumptions | `social-science.md` |
| Systematic review behind a parameter | PRISMA 2020 | Search, selection flow; risk of bias reported separately | `citation.md` |
| Forecast or backtest | No dedicated guideline found: say so | Benchmarks, windows, power | `finance.md`; `scripts/backtest_eval.py` |

- **Failure signature:** "scored 18 of 30" language; adherence claimed when only some items were reviewed; an outdated parent statement; a missing method written in as if it happened.

### 2.8 Re-verify statuses on the use date

- **Rule.** Every register row is a dated read. Before a row supports a T1 deliverable, re-check the issuer's official page on the use date and record the instrument, URL, date checked, status and what changed. For T2 and T3 work, re-check when the row is older than the review interval the owner set.
- **Superseded.** Mark the row SUPERSEDED (by what, on what date) and set flag C in `citation.md`. Claims about current law cite the successor; historical claims keep "(superseded by ...)".
- **Unconfirmable.** Tag [S] when only a secondary source confirms the status, and STATUS-UNVERIFIED when none does. A LEGAL assumption resting on a STATUS-UNVERIFIED row is UNVERIFIED-HERE, never SURVIVES.
- **Sources.** Take legal text from the issuer (uscode or govinfo, eCFR or the Federal Register, fec.gov, lda.gov, federalreserve.gov, ncua.gov), never from search snippets or model memory; law-firm alerts are [S]. Do not silently swap in a newer edition of an incorporated standard, and never reproduce ISO/IEC clause text (cite the designation and describe your own process).
- **Watch list (as of 2026-09-30):** the banking agencies' AI/model-risk RFI; the NIST AI RMF revision; federal AI preemption bills; Colorado AG rules and SB 26-189 (2027-01-01); CPPA ADMT duties (2027-01-01); OSFI E-23 (2027-05-01); EU Annex III (2027-12-02) and Annex I (2028-08-02); the ECB RDARR revision (Q4 2026); the HHS Common Rule exemption proposal; the GDPR data omnibus; the OCC-FDIC CRA proposal (comments to 2026-10-13) and any Board action on the 2025 CRA rescission proposal.
- **Open items from the source research (re-verify these first):**
  1. The interagency AI/model-risk RFI promised with SR 26-2: issuance STATUS-UNVERIFIED; one tracker called it unpublished on 2026-08-26.
  2. ISO/IEC 23894:2023: STATUS-UNVERIFIED (iso.org 403; no revision found).
  3. ISO/IEC 42001:2023: current only per a secondary source (the 2026 CEN adoption); the ISO page returned 403.
  4. Reg. (EU) 2026/1744 OJ date: CLOSED on 2026-09-30. It was published in OJ L on 2026-07-24 and entered into force on 2026-07-27 (EUR-Lex) [P].
  5. NASA-STD-7009B: approval on 2024-03-05 is confirmed from the PDF; the absence of a later revision is not.
  6. ASME V&V 40-2018: reaffirmation or revision status unverified.
  7. NCUA's non-adoption of SR 11-7 or SR 26-2 rests on a secondary source and on absence from the pages checked.
  8. The legacy SR 11-7 text (Fed page 404). The $1B threshold and the dropped word "mathematical" were confirmed on issuer pages on 2026-09-30 [P]. The annual-review and itemized-technique differences still rely on a 2026 law-firm comparison.
  9. The CFPB Reg B final rule (2026-04-22, effective 2026-07-21): the Federal Register page blocked automated fetch; it rests on several 2026 law-firm alerts.
  10. "No federal AI preemption statute enacted": secondary sources only, as of Sept 2026.
  11. Colorado SB 25B-004's signing date (2025-08-28) and APSA's approval date (2020-04-04) come from secondary sources.
  12. The Bluesky Developer Guidelines are undated.
  13. AoIR IRE 3.0: no successor found, but none ruled out.
  14. OSFI E-23's principle count: sources disagree, so none is given.
  15. PRA LIAF01/26 amendment details: the BoE confirms a 2026-04-23 version; the details come from search summaries.

## 3. Checklist

Each item gives its assumption class, its source tags (§2.1 IDs) with the applicability label the source research assigned, and the procedure or script that runs it. Those labels were set for a US political-finance analytics operator that is not a bank, creditor or EU-facing provider: re-assign them with §2.2 for your system. DIRECT items bind only when the named data or activity is in scope. "(v)" = DIRECT (voluntary); "(c)" = DIRECT (conditional).

**3.1 Governance and inventory**
- **REG-01** (DECISION) Inventory every component that meets the 2026 US model definition or OSFI's AI-inclusive one; write the rationale for each exclusion. [A1, A5 · BY-ANALOGY] → §2.3 step 1
- **REG-02** (DECISION) Give each model a documented purpose and intended use, owner, developer, origin (internal or vendor) and a tier from inherent risk × materiality. [A1, A4, A5 · BY-ANALOGY] → §2.3 step 1
- **REG-03** (DECISION) Record the triggers that would move a low-tier model up, and re-tier on every change. [A1, A1b · BY-ANALOGY] → §2.3 step 1
- **REG-04** (DECISION) Keep an owner-approved model policy covering approval, version control, exceptions, escalation, modification and decommissioning. [A3, A5 · BY-ANALOGY]
- **REG-05** (COMPUTATIONAL) List the data, assumptions and code that models share, and test what happens when a shared component fails. [A1 · BY-ANALOGY] → `scripts/mutation_check.py`
- **REG-06** (DECISION) Name one accountable owner of model risk, and report aggregate model risk to decision-makers at a set interval. [A4 · BY-ANALOGY]
- **REG-07** (LEGAL) Label every cited framework as binding law, supervisory guidance or voluntary, with a status date, and refresh the label on change; SR 11-7 is superseded. [B7, A2 · BY-ANALOGY] → §2.8; `citation.md` flag C

**3.2 Conceptual soundness and assumptions**
- **REG-08** (FUNCTIONAL-FORM) Document key modeling choices, assumptions, judgments and data selection, and test at least one alternative specification or method. [A1 · BY-ANALOGY] → `core-statistics.md`; `scripts/regression_report.R`
- **REG-09** (CAUSAL) For any claim about the effect or efficiency of money on votes or outcomes, state the causal assumptions and test reverse causality (money following expected votes), selection and confounding (party, committee). [A1, E4 · BY-ANALOGY] → `social-science.md`; `scripts/confounding_sensitivity.py`
- **REG-10** (STATISTICAL) Back-test every behavioural assumption the model relies on, not only its final outputs. [A3 · BY-ANALOGY] → `scripts/backtest_eval.py`
- **REG-11** (DATA) Check borrowed or vendor parameters for reasonableness against the local population before use. [A3, A1 · BY-ANALOGY] → §2.3 step 8
- **REG-12** (FUNCTIONAL-FORM) Keep a simpler benchmark for every ML or complex component and justify the added complexity with measured performance. [A6 · BY-ANALOGY] → `machine-learning.md`; `scripts/backtest_eval.py`
- **REG-13** (FUNCTIONAL-FORM) Check for omitted drivers: confirm the model captures every material driver of the quantity it estimates. [A3 · BY-ANALOGY]

**3.3 Data quality and lineage**
- **REG-14** (DATA) Reconcile every aggregate to its source totals (e.g. FEC committee totals, LDA filing counts) and log every break. [A7 · BY-ANALOGY] → `finance.md`
- **REG-15** (DATA) Measure completeness by period, entity type and source, and name the gaps. [A7 · BY-ANALOGY]
- **REG-16** (DATA) Record freshness for each input and alert when it goes stale. [A7 · BY-ANALOGY] → `automation.md`
- **REG-17** (DATA) Keep one data dictionary and lineage map, with an owner for each critical data element. [A7, B3 · BY-ANALOGY] → `automation.md`
- **REG-18** (DATA) Before training or validation, test data for relevance, representativeness, errors, completeness and bias. [B5, A5 · BY-ANALOGY] → `machine-learning.md`; `scripts/leakage_audit.py`
- **REG-19** (MEASUREMENT) Treat LD-2 amounts as interval-censored (above $5,000 rounded to the nearest $10,000; a "less than $5,000" bucket) and carry that into any efficiency estimate. [C2 · DIRECT] → `finance.md`
- **REG-20** (MEASUREMENT) Treat attribution of lobbying to individual legislators as a model inference (LD-2 names no members) and validate it against evidence the inference did not produce. [C2 · DIRECT]
- **REG-21** (DATA) De-duplicate LD-203 contributions against FEC receipts before summing money flows. [C2 · DIRECT]
- **REG-22** (DATA) Feed GAO-measured filing error rates (GAO-26-108486) into uncertainty or sensitivity analysis. [C2 · DIRECT] → `scripts/global_sensitivity.py`
- **REG-23** (DATA) Account for FEC salted pseudonyms (up to 10 per report) in entity resolution, and never contact contributors. [C1 · DIRECT]
- **REG-24** (DATA) For foreign-principal lobbying, document how coverage splits between LDA and FARA and keep the two apart in features. [C3 · BY-ANALOGY]

**3.4 Validation, backtesting and monitoring**
- **REG-25** (STATISTICAL) Include out-of-sample and out-of-time tests in development. [A1 · BY-ANALOGY] → `scripts/backtest_eval.py`; `scripts/leakage_audit.py`
- **REG-26** (DECISION) Run outcomes analysis against realized outcomes with thresholds fixed in advance; expert-set dials and weights need quantitative outcome evidence too. [A1 · BY-ANALOGY] → `scripts/calibration_report.py`; `scripts/backtest_eval.py`
- **REG-27** (DECISION) Validate before first use; if a model is used earlier, restrict its use, monitor it closely and disclose its limitations. [A1 · BY-ANALOGY]
- **REG-28** (STATISTICAL) Set validation frequency by risk and rate of change, not by calendar, and revalidate on material change. [A1b, A4 · BY-ANALOGY]
- **REG-29** (STATISTICAL) Keep a monitoring plan with drift triggers (a new legislative session, redistricting, rule or source changes) and a response ladder: overlay, recalibrate, redevelop. [A1, A5 · BY-ANALOGY]
- **REG-30** (DECISION) Require effective challenge by an independent reviewer with authority to force change, and keep a log of findings, responses and exceptions. [A1, A4 · BY-ANALOGY] → §2.3 step 7
- **REG-31** (PRESENTATION) Track each limitation with a mitigant: a use restriction, or an overlay with a rationale and an expiry date. [A4, A1 · BY-ANALOGY]
- **REG-32** (DECISION) Decommission models formally and keep the record. [A5, A3 · BY-ANALOGY]

**3.5 Simulation credibility**
- **REG-33** (COMPUTATIONAL) Keep code verification, solution verification and validation separate, in VVUQ 1 terms. [E1 · BY-ANALOGY] → `engineering-simulation.md`
- **REG-34** (COMPUTATIONAL) Code-verify simulation engines (e.g. network cascade or diffusion engines) against analytically known cases: edge probabilities of 0 and 1, a single seed on a path or star, an empty graph. [E1, E4 · BY-ANALOGY]
- **REG-35** (COMPUTATIONAL) Quantify Monte-Carlo error and convergence as runs grow, and compare it with the differences that drive decisions (rank gaps, frontier points). [E1, E4 · BY-ANALOGY] → `scripts/mc_error.py`
- **REG-36** (COMPUTATIONAL) Compare simulated with observed outcomes, reporting the error against the validation uncertainty. [E1 · BY-ANALOGY]
- **REG-37** (DECISION) Set credibility goals from model influence × decision consequence. [E1, E2 · BY-ANALOGY]
- **REG-38** (PRESENTATION) Record intended use, criticality, acceptance criteria, assumptions, limits, permissible uses, data pedigree, and the domains of verification and validation. [E2 · BY-ANALOGY]
- **REG-39** (COMPUTATIONAL) Record how uncertainty was characterized and what the sensitivity analyses covered and found (edge probabilities, thresholds, shock sizes, budget-response curves). [E2, E4 · BY-ANALOGY] → `scripts/global_sensitivity.py`
- **REG-40** (PRESENTATION) Warn decision-makers explicitly when acceptance criteria are unmet, assumptions or limits are violated, or a run produced warnings. [E2 · BY-ANALOGY]
- **REG-41** (PRESENTATION) Document each agent-based or diffusion simulation in ODD, keep a TRACE file, and test whether it can be re-implemented from the ODD alone. [E3 · DIRECT (v)]
- **REG-42** (COMPUTATIONAL) Apply Sargent's operational-validity techniques: historical comparison with a holdout, extreme-condition and degenerate tests, sensitivity analysis, face validity, model-to-model comparison, replication variability. [E4 · DIRECT (v)]

**3.6 AI and LLM components**
- **REG-43** (MEASUREMENT) Apply the AI RMF functions (Govern, Map, Measure, Manage) and map each trustworthiness characteristic to a test. [B1 · DIRECT (v)] → §2.5
- **REG-44** (MEASUREMENT) Test LLM outputs for confabulation against source records and report the error rate from a sample. [B2 · DIRECT (v)] → `citation.md` axis S
- **REG-45** (COMPUTATIONAL) Pin model versions and prompts for LLM calls that feed scores or published text, and re-validate on any change. [B2 · DIRECT (v)] → `automation.md`
- **REG-46** (MEASUREMENT) Test LLM labels for systematic bias across party, chamber and gender, and keep human review on text that decision-makers see. [B2, B1 · DIRECT (v)] → `social-science.md`
- **REG-47** (LEGAL) Minimize the personal data sent to third-party AI and log every transfer. [B2, F2 · DIRECT (v)]
- **REG-48** (LEGAL) Keep individual-level profiling of private persons out of client products, and record the EU AI Act Annex III reasoning for points 5(b) and 8(b). [B5 · BY-ANALOGY] → §2.5
- **REG-49** (PRESENTATION) Check that reasons given for scores are specific and faithful to the model's drivers, using perturbation or drop-feature tests. [B9 · BY-ANALOGY] → `machine-learning.md`
- **REG-50** (DECISION) Document the objective function and any operator-client conflict (e.g. a term that rewards more spending), and report whether recommendations change without it. [B8 · BY-ANALOGY]

**3.7 Legal constraints on data use**
- **REG-51** (LEGAL) Map every path by which FEC individual-contributor fields (name, street, city, ZIP, employer, occupation, amount) reach features, tables, exports and the UI. [C1 · DIRECT] → §2.4
- **REG-52** (LEGAL) Never link identities or contact information to contribution-derived scores; deliver only aggregated, non-personally-identifiable contribution analytics (AOs 2021-05, 2017-08, 2022-10; AO 2014-07 allowed more, see §2.4). [C1 · DIRECT]
- **REG-53** (LEGAL) Do not distribute compilations made up mainly of contributor names (AO 1986-25) or build or clean lists (AOs 1985-16, 2004-24); tag each row FEC or non-FEC (AO 2022-03). [C1 · DIRECT]
- **REG-54** (LEGAL) Use the lda.gov API with a key and within the rate limits, record the access date, and attach the Senate Office of Public Records disclaimer. [C2 · DIRECT] → `citation.md` §2.7
- **REG-55** (LEGAL) Record each social source's access path and terms version; do not profile individuals' political affiliation from X content without X's approval, redistribute raw content, or train foundation models on it. [C5 · DIRECT]
- **REG-56** (LEGAL) Honor platform deletions: X content within 24 hours of a request, and Bluesky delete events. [C5 · DIRECT]
- **REG-57** (LEGAL) Do not scrape behind logins or technical barriers, and snapshot the site's terms at collection time. [C6 · DIRECT]
- **REG-58** (LEGAL) If any voter-file data is used, confirm each state's permitted uses, and never join voter files to FEC contributor rows. [C4 · DIRECT (c)]

**3.8 Research transparency and ethics**
- **REG-59** (STATISTICAL) Preregister confirmatory tests with timestamps, report deviations, and keep a ledger of every look. [D7, D5 · BY-ANALOGY]
- **REG-60** (COMPUTATIONAL) Ship a replication package and README for each claim, and have someone other than the author reproduce it. [D6, D4, D5 · BY-ANALOGY] → `automation.md`
- **REG-61** (PRESENTATION) Cite data with persistent identifiers and versions. [D4 · BY-ANALOGY] → `citation.md`
- **REG-62** (LEGAL) Assess and document the potential impact on political processes; separate public figures from private individuals, and minimize the private individuals' data. [D2, D3 · BY-ANALOGY]
- **REG-63** (LEGAL) Classify person-level datasets as public, identifiable-private or de-identified, and never re-identify data or contact subjects. [D1 · BY-ANALOGY]

**3.9 Privacy**
- **REG-64** (LEGAL) Record the GDPR Article 3 analysis, and aggregate or exclude EU-address contributor rows from individual profiling. [F1 · BY-ANALOGY]
- **REG-65** (LEGAL) Decide CCPA "business" status each year, treat inferences about individuals as personal information, and assess the Delete Act and DROP if personal information is sold. [F2 · DIRECT (c)]
- **REG-66** (LEGAL) Map individual-level data elements to each state's "publicly available" definition, do not assume derived data stays exempt, and note that California covers employment-context data. [F3 · BY-ANALOGY]

**3.10 Bank community-lending law** (added 2026-09-30; no source-research counterpart)
- **REG-67** (DATA) If any input comes from CRA evaluations, ratings, assessment areas or LMI tract designations, record the framework that produced it (the pre-2024 rules; the 2023 rule never applied), re-check the status on the use date, and do not extend CRA coverage to credit unions. [A8 · DIRECT for banks; BY-ANALOGY otherwise] → §2.1 A8; `finance.md`

**3.11 The ten checks that matter most for a political-spending-efficiency model**
1. REG-09: state the causal assumptions behind money-to-vote efficiency and test reverse causality, selection and confounding.
2. REG-26 with REG-25: outcomes analysis and out-of-time backtests against thresholds fixed in advance; test flip or outcome predictions against realized votes.
3. REG-39: sensitivity and uncertainty analysis on the key parameters (edge probabilities and thresholds, shock sizes, spend-response curves), with the validated domain stated.
4. REG-35 with REG-34: Monte-Carlo error and convergence against rank gaps and frontier differences, plus code verification.
5. REG-40: explicit warnings when outputs fall outside the validated domain or break assumptions.
6. REG-02: a documented intended use, owner and materiality tier for every model.
7. REG-30: effective challenge by an independent reviewer with authority, and a findings log.
8. REG-14: reconciliation to source totals (FEC committee totals, LDA filing counts).
9. REG-52: FEC sale-or-use; keep contribution analytics aggregated and never linked to contributor identity or contact data.
10. REG-20 with REG-19: member-level lobbying attribution is a model inference; avoid circular validation and carry the LD-2 rounding.

## 4. Pitfalls and anti-patterns

- Citing SR 11-7, OCC 2011-12 or FDIC FIL-22-2017 as current authority. All were superseded on 2026-04-17.
- Presenting SR 11-7-era techniques as current regulatory requirements. They are retained good practice.
- Reading a withdrawal (CFPB circulars, the SEC proposal) or deprioritized enforcement as proof that a practice is sound. Re-derive the check from statute or first principles.
- Treating "publicly available" as "usable for anything". FEC reports carry a statutory use restriction, and California treats inferences drawn from public data as personal information.
- Letting a label change status. "Research only", a disclaimer or "human in the loop" does not change what an output does or who relies on it.
- Treating a checklist, crosswalk or script result as a conformity assessment, or titling an output "compliant", "certified" or "audit pass".
- Blending regimes into one protocol. Bank guidance, AI law and data-use law answer different questions, and a blended checklist satisfies none of them. Keep each check tied to its source ID.
- Defaulting an undetermined fact to NOT-APPLICABLE. Leave it as a DIRECT (conditional) blocker.
- Taking legal text or status from search snippets, model memory or a law-firm summary when the issuer's page is reachable.
- Hard-coding the old LDA host (lda.senate.gov) without recording the 301 redirect to lda.gov in provenance.
- Assuming either extreme on validation cadence. No fixed annual cycle is required, but every model keeps a floor of an inventory entry and performance monitoring.
- Reading Annex III point 8(b) as covering models of legislators' votes. It concerns voters and excludes tools voters are not directly exposed to. Conversely, profiling natural persons makes an Annex III system high-risk.
- Treating generative components as covered by bank model-risk guidance. SR 26-2 excludes them; use NIST AI 600-1.
- Using a reporting-guideline tally as a quality score, or writing an unperformed method into a report to fill a checklist item.

## 5. References

The skill-wide bibliography, with a dated status tag on every entry, is `references/sources.md`; re-check it with `python scripts/cite_check.py --text references/sources.md` (`citation.md` §2.4).

Scholarly and standards sources. DOIs were checked against CrossRef or DataCite in the source research on 2026-09-29, and every DOI and title below was re-checked against its registry record on 2026-09-30.
- Ayllón, D., et al. (2021). Keeping modelling notebooks with TRACE. *Environmental Modelling & Software* 136:104932. DOI 10.1016/j.envsoft.2020.104932
- Benchimol, E. I., et al. (2015). The REporting of studies Conducted using Observational Routinely-collected health Data (RECORD) statement. *PLOS Medicine* 12(10):e1001885. DOI 10.1371/journal.pmed.1001885
- Collins, G. S., et al. (2024). TRIPOD+AI statement: updated guidance for reporting clinical prediction models that use regression or machine learning methods. *BMJ* 385:e078378. DOI 10.1136/bmj-2023-078378 (CrossRef lists a correction)
- Grant, S., Corker, K. S., Mellor, D. T., et al. (2026). TOP 2025: an update to the Transparency and Openness Promotion Guidelines. *Research Integrity and Peer Review* 11(1). DOI 10.1186/s41073-026-00223-0
- Grimm, V., et al. (2006). A standard protocol for describing individual-based and agent-based models. *Ecological Modelling* 198(1-2):115-126. DOI 10.1016/j.ecolmodel.2006.04.023
- Grimm, V., et al. (2010). The ODD protocol: a review and first update. *Ecological Modelling* 221(23):2760-2768. DOI 10.1016/j.ecolmodel.2010.08.019
- Grimm, V., et al. (2014). Towards better modelling and decision support: documenting model development, testing, and analysis using TRACE. *Ecological Modelling* 280:129-139. DOI 10.1016/j.ecolmodel.2014.01.018
- Grimm, V., et al. (2020). The ODD protocol for describing agent-based and other simulation models: a second update. *JASSS* 23(2). DOI 10.18564/jasss.4259
- Husereau, D., et al. (2022). Consolidated Health Economic Evaluation Reporting Standards 2022 (CHEERS 2022) statement. *BMJ* 376:e067975. DOI 10.1136/bmj-2021-067975
- Lupia, A., & Elman, C. (2014; online 2013). Openness in political science: data access and research transparency. *PS: Political Science & Politics* 47(1):19-42. DOI 10.1017/S1049096513001716
- Monks, T., et al. (2019; online 2018). Strengthening the reporting of empirical simulation studies: introducing the STRESS guidelines. *Journal of Simulation* 13(1):55-67. DOI 10.1080/17477778.2018.1442155
- Nosek, B. A., et al. (2015). Promoting an open research culture. *Science* 348(6242):1422-1425. DOI 10.1126/science.aab2374
- Sargent, R. G. (2013). Verification and validation of simulation models. *Journal of Simulation* 7(1):12-24. DOI 10.1057/jos.2012.20
- Sargent, R. G., & Balci, O. (2017). History of verification and validation of simulation models. WSC 2017. DOI 10.1109/wsc.2017.8247794
- Schmolke, A., et al. (2010). Ecological models supporting environmental decision making: a strategy for the future. *Trends in Ecology & Evolution* 25(8):479-486. DOI 10.1016/j.tree.2010.05.001
- Tabassi, E. (2023). Artificial Intelligence Risk Management Framework (AI RMF 1.0), NIST AI 100-1. NIST. DOI 10.6028/NIST.AI.100-1
- NIST (2024). Artificial Intelligence Risk Management Framework: Generative Artificial Intelligence Profile, NIST AI 600-1. DOI 10.6028/NIST.AI.600-1
- Vilhuber, L., Connolly, M., Koren, M., Llull, J., & Morrow, P. (2022). A template README for social science replication packages (v1.1). Zenodo. DOI 10.5281/zenodo.7293838
- von Elm, E., et al. (2007). The Strengthening the Reporting of Observational Studies in Epidemiology (STROBE) statement: guidelines for reporting observational studies. *PLoS Medicine* 4(10):e296. DOI 10.1371/journal.pmed.0040296

Official pages not linked in §2.1 (read 2026-09-29; CRA pages 2026-09-30):
- CRA (A8), Federal Register: https://www.federalregister.gov/documents/2024/02/01/2023-25797/community-reinvestment-act, https://www.federalregister.gov/documents/2025/07/18/2025-13559/community-reinvestment-act-regulations, https://www.federalregister.gov/documents/2026/08/12/2026-16454/community-reinvestment-act-regulations (status, litigation history and "current rules" baseline) and https://www.federalregister.gov/documents/2026/01/07/2026-00042/community-reinvestment-act-regulations-asset-size-thresholds; Fed CRA pages https://www.federalreserve.gov/consumerscommunities/cra_about.htm
- FEC advisory-opinion texts: https://www.fec.gov/files/legal/aos/2021-05/2021-05.pdf, https://www.fec.gov/files/legal/aos/2022-10/2022-10.pdf, https://www.fec.gov/files/legal/aos/1986-25/1986-25.pdf, https://www.fec.gov/updates/ao-2022-03/; bulk-data notice: https://www.fec.gov/data/browse-data/?tab=bulk-data
- GAO-26-108486: https://www.gao.gov/products/gao-26-108486; GAO-25-107197: https://www.gao.gov/products/gao-25-107197; LDA API: https://lda.gov/api/
- PRA LIAF01/26: https://www.bankofengland.co.uk/prudential-regulation/publication/2026/april/low-impact-amendments-finalisation-april-2026; ECB internal-models revision release: https://www.bankingsupervision.europa.eu/press/pr/date/2025/html/ssm.pr250728~2b36305822.en.html
- [S] Annex III text: https://artificialintelligenceact.eu/annex/3/; Omnibus summary: https://artificialintelligenceact.eu/ai-act-explorer/digital-omnibus/; SR 11-7 versus SR 26-2 comparison (Orrick, 2026): https://www.orrick.com/en/Insights/2026/04/Agencies-Overhaul-Model-Risk-Management-Guidance-for-Banks-Heres-What-Changed
- CPPA thresholds: https://cppa.ca.gov/regulations/cpi_adjustment.html; California AG Opinion 20-303: https://oag.ca.gov/system/files/opinions/pdfs/20-303.pdf; 45 CFR 46.102: https://www.law.cornell.edu/cfr/text/45/46.102; NASA-STD-7009B PDF: https://standards.nasa.gov/sites/default/files/standards/NASA/B/1/NASA-STD-7009B-Final-3-5-2024.pdf
- Reporting-guideline homes (URLs from the K-Dense source ledgers, checked there 2026-07-23; not re-read here): https://www.equator-network.org/; AAPOR Code https://aapor.org/standards-and-ethics/ and Disclosure Standards https://aapor.org/standards-and-ethics/disclosure-standards/ (Code revision of 2026-06 per that ledger, UNVERIFIED here); PRISMA 2020 https://www.prisma-statement.org/prisma-2020; RECORD https://www.record-statement.org/

Adapted from (K-Dense scientific-agent-skills, MIT; ideas paraphrased, no text or code copied; paths are inside the K-Dense repository, not this skill): `clinical-decision-support/SKILL.md`, `clinical-decision-support/references/regulatory_and_governance.md`, `clinical-decision-support/references/model_biomarker_evaluation.md`, `clinical-decision-support/references/decision_logic_traceability.md`, `clinical-decision-support/references/study_reporting.md`; `iso-standards-readiness/SKILL.md`, `iso-standards-readiness/references/assurance-lanes.md`, `iso-standards-readiness/references/source-ledger.md`; `analytical-method-validation/SKILL.md`; `peer-review/references/reporting_standards.md`; `scientific-writing/references/reporting_guidelines.md`; `market-research-reports/references/methods_and_ethics.md`; `simpy/references/simulation-methodology.md`.
