#!/usr/bin/env python3
"""The adjudication itself: Opus 5's ruling on every amendment, and the rule behind it.

Nothing here is automated judgement. Each PER_KEY entry is a ruling made after
reading that amendment's own operative text (or its official purpose line) in
the review cards under ./cards/. Each FAMILY entry is one ruling that covers a
set of amendments carrying the SAME operative text refiled across vehicles, and
names the signature that identifies the family. Each structural default names
the rule and the evidence state it rests on.

Direction is grounded in ACU's own recorded positions in
acu_category_registry.json wherever the category has one, so a +1/-1 is a
finding about the amendment's ultimate effect on a position ACU actually holds,
not a guess about what ACU would think.

DIRECTION CONVENTION: +1 = the amendment's ultimate policy effect ADVANCES the
credit-union interest the category names; -1 = it SETS BACK that interest.
"""

# --- direction anchors actually recorded in acu_category_registry.json --------
# interchange                        OPPOSE Credit Card Competition Act
# credit_card_consumer_fee_mandates  OPPOSE 10 Percent Credit Card Interest Rate Cap Act
#                                    OPPOSE Credit Card Fairness Act
#                                    SUPPORT resolution disapproving the CRA overdraft rule
# technology_emerging_issues         SUPPORT Anti-CBDC Surveillance State Act; SUPPORT GENIUS/STABLE
# fraud_prevention                   SUPPORT TRAPS Act (payment-scam task force)
# data_privacy_cybersecurity         SUPPORT Homebuyers Privacy Protection Act (trigger leads)
# ncua_budget_share_insurance        SUPPORT NCUA Central Liquidity Facility Enhancements Act
# member_business_lending            SUPPORT Veterans Member Business Loan Act
# cdfi_fund                          SUPPORT CDFI Bond Guarantee Program Improvement Act
# cfpb_issues_structural_reform      SUPPORT TABS Act (CFPB into appropriations);
#                                    SUPPORT Bureau Commission Act; SUPPORT 1071 Repeal
# examination_supervision            SUPPORT STREAMLINE Act (CTR/SAR thresholds); SUPPORT TAILOR
# mortgage_lending_housing           SUPPORT HELPER Act (FHA insurance for first responders)
# charter_modernization_governance   SUPPORT CU Board Modernization; American Access to Banking

INC = "include"
EXC = "exclude_false_positive"
FLG = "flagged"

# (disposition, [category_ids], direction, confidence, rule_id, reason)
PER_KEY: dict[str, tuple] = {}


def _add(keys, disp, cats, direction, conf, rule, reason):
    for k in keys.split():
        PER_KEY[k] = (disp, cats, direction, conf, rule, reason)


# ============================ INCLUDE, direction -1 ==========================
_add("117:samdt:6201 118:samdt:1695 118:samdt:1936 118:samdt:862 119:samdt:4305",
     INC, ["interchange"], -1, "high", "R-CCCA",
     "operative text is the Credit Card Competition Act verbatim (routing mandates on "
     "covered card issuers via EFTA sec.921); ACU records OPPOSE on that measure")
_add("119:samdt:2229 119:samdt:2230 119:samdt:2345",
     INC, ["interchange"], -1, "high", "R-CCCA-PRESS",
     "Credit Card Competition Act text offered to S.1582; ACU articles name Sen. Marshall's "
     "interchange amendment by sponsor and substance and state 'we urge Senators to oppose it'")
_add("119:samdt:2239",
     INC, ["credit_card_consumer_fee_mandates"], -1, "high", "R-RATECAP-PRESS",
     "operative text caps credit-card APR at 10 percent via TILA sec.107; ACU articles name "
     "Sen. Hawley's 10 percent rate-cap amendment and record ACU joining a letter opposing it")
_add("118:hamdt:658",
     INC, ["cdfi_fund"], -1, "high", "R-CDFI-DEFUND",
     "operative text strikes the Community Development Financial Institutions Fund program "
     "account from the appropriation; direct defunding of the CDFI Fund")
_add("116:hamdt:247",
     INC, ["mortgage_lending_housing", "cfpb_issues_structural_reform"], -1, "medium", "R-HMDA-EXEMPT",
     "operative text rewrites the HMDA sec.304(i) small-volume reporting exemption and bars the "
     "CFPB from granting HMDA exemptions; removes reporting relief credit unions rely on")
_add("116:hamdt:263",
     INC, ["cfpb_issues_structural_reform"], -1, "medium", "R-ARBITRATION",
     "operative text repeals the CRA joint resolution and orders the CFPB to reissue the "
     "forced-arbitration ban; restores a rule the insured-depository sector opposed")
_add("119:samdt:1071",
     INC, ["credit_card_consumer_fee_mandates"], -1, "medium", "R-FEEPOINT",
     "operative text creates a Senate point of order against legislation easing overdraft and "
     "credit-card late-fee restrictions; ACU records SUPPORT for disapproving the overdraft rule")
_add("119:samdt:1159",
     INC, ["cfpb_issues_structural_reform", "credit_card_consumer_fee_mandates"], -1, "medium", "R-CFPBRESTORE",
     "reserve fund to restore CFPB staff specifically to continue reducing overdraft and "
     "credit-card late fees; runs against ACU's recorded CFPB-reform and fee-mandate positions")

# ============================ INCLUDE, direction +1 ==========================
_add("119:samdt:1637",
     INC, ["credit_union_tax_status"], 1, "high", "R-TAXPOINT",
     "operative text creates a Senate point of order against legislation eliminating the "
     "credit-union tax exemption; directly protective of the category's core interest")
_add("119:samdt:3722 119:samdt:3834 119:samdt:5882 119:samdt:6180",
     INC, ["ncua_budget_share_insurance", "field_of_membership"], 1, "high", "R-CLF-AGENT",
     "operative text amends FCU Act sec.304(b)(2) to broaden Agent membership in the NCUA "
     "Central Liquidity Facility; ACU records SUPPORT for CLF enhancements")
_add("119:samdt:3776",
     INC, ["member_business_lending", "ncua_budget_share_insurance"], 1, "high", "R-MBL-DEF",
     "operative text amends the FCU Act sec.107A(c) member-business-loan definition; ACU records "
     "SUPPORT for the Veterans Member Business Loan Act and MBL-cap relief generally")
_add("119:samdt:3257",
     INC, ["fraud_prevention"], 1, "high", "R-TRAPS",
     "operative text establishes the Task Force for Recognizing and Averting Payment Scams; "
     "ACU records SUPPORT for the TRAPS Act by name")
_add("119:samdt:2280",
     INC, ["cfpb_issues_structural_reform"], 1, "high", "R-1071",
     "operative text repeals ECOA sec.704B, the CFPB small-business (1071) data collection "
     "rule; ACU records SUPPORT for 1071 repeal")
_add("119:samdt:6241",
     INC, ["examination_supervision"], 1, "high", "R-CTRSAR",
     "operative text raises and indexes the Currency Transaction Report and Suspicious Activity "
     "Report thresholds; ACU records SUPPORT for the STREAMLINE Act threshold update")
_add("116:hamdt:253 117:samdt:4704",
     INC, ["cfpb_issues_structural_reform"], 1, "high", "R-CFPB-APPROP",
     "operative text amends CFPA sec.1017 to fund the CFPB through regular appropriations; "
     "ACU records SUPPORT for the TABS Act")
_add("118:samdt:1776",
     INC, ["cfpb_issues_structural_reform", "examination_supervision"], 1, "medium", "R-CFPB-CHAIR",
     "operative text amends CFPA sec.1017 funding and converts the single Director to a Chair "
     "across the FFIEC and related statutes; ACU records SUPPORT for the Commission Act and TABS")
_add("118:samdt:3339",
     INC, ["data_privacy_cybersecurity", "mortgage_lending_housing"], 1, "high", "R-TRIGGERLEADS",
     "operative text is the Homebuyers Privacy Protection Act, amending FCRA sec.604(c) to curb "
     "mortgage trigger leads, and it defines credit union; ACU records SUPPORT/PASSED")
_add("118:samdt:3048 119:samdt:4320",
     INC, ["mortgage_lending_housing"], 1, "high", "R-HELPER",
     "operative text adds National Housing Act sec.203(z), FHA mortgage insurance for first "
     "responders; this is the HELPER Act, which ACU records as SUPPORT")
_add("118:hamdt:662 118:hamdt:696 119:samdt:2272 119:samdt:4249 119:samdt:4391",
     INC, ["technology_emerging_issues"], 1, "high", "R-ANTICBDC",
     "operative text prohibits Federal Reserve issuance or Treasury development of a central "
     "bank digital currency; ACU records SUPPORT for the Anti-CBDC Surveillance State Act")
_add("117:samdt:6312 118:samdt:479 119:samdt:6101",
     INC, ["cdfi_fund"], 1, "high", "R-CDFI-BOND",
     "operative text is the CDFI Bond Guarantee Program Improvement Act; ACU records SUPPORT")
_add("118:samdt:2907 119:samdt:3326",
     INC, ["cdfi_fund"], 1, "medium", "R-CDFI-RELEND",
     "operative text creates a Native CDFI relending set-aside under Housing Act sec.502; "
     "expands the CDFI channel ACU records SUPPORT for")
_add("117:samdt:4811",
     INC, ["examination_supervision", "data_privacy_cybersecurity"], 1, "medium", "R-IRSREPORT",
     "operative text bars the IRS from requiring financial institutions to report customer "
     "transaction flows, with a Bank Secrecy Act savings clause; removes a reporting mandate "
     "on insured depositories, consistent with ACU's recorded reporting-threshold relief position")
_add("119:samdt:2247",
     INC, ["examination_supervision"], 1, "medium", "R-BSAREFORM",
     "operative text amends the Right to Financial Privacy Act as Bank Secrecy Act reform; "
     "burden relief of the kind ACU records SUPPORT for in the STREAMLINE Act")
_add("116:samdt:2542",
     INC, ["ncua_budget_share_insurance"], 1, "medium", "R-CLF-CARES",
     "operative text extends the temporary credit-union provisions of FCU Act sec.307(a)(4)(A) "
     "(Central Liquidity Facility) alongside CARES Act 13(3) clarification")
_add("116:samdt:1580",
     INC, ["cdfi_fund", "member_business_lending"], 1, "medium", "R-PPP-CU",
     "operative text defines credit unions and community financial institutions and reserves a "
     "share of Paycheck Protection Program lending for them; direct credit-union lending access")
_add("117:hamdt:97",
     INC, ["charter_modernization_governance", "examination_supervision"], 1, "medium", "R-SAFEBANKING",
     "operative text is the SAFE Banking title, defining Federal and State credit unions and "
     "barring regulators from penalising depositories serving lawful cannabis businesses")
_add("116:samdt:2170 117:samdt:3989 118:samdt:206",
     INC, ["defense_credit_union_issues"], 1, "medium", "R-MILCU-COUNSEL",
     "operative text amends 10 U.S.C. 992 to let qualified representatives of credit unions "
     "operating on military installations deliver financial counselling to members and spouses")
_add("119:samdt:2299 119:samdt:2305 119:samdt:2315",
     INC, ["payments"], 1, "medium", "R-STABLE-NOYIELD",
     "operative text bars any person from paying interest or yield on a payment stablecoin; "
     "the provision insured depositories sought to prevent share/deposit disintermediation")
_add("119:samdt:2329",
     INC, ["payments"], 1, "medium", "R-STABLE-FEDACCESS",
     "operative text limits access to Federal Reserve services to permitted stablecoin issuers "
     "that are insured depository institutions, preserving the depository access distinction")
_add("116:samdt:2713 116:samdt:1049 119:samdt:3673 119:samdt:4167",
     INC, ["fraud_prevention"], 1, "medium", "R-SCAMBODY",
     "operative text stands up a federal scam/elder-fraud prevention office, task force or "
     "notification duty; the same instrument ACU records SUPPORT for in the TRAPS Act")
_add("119:samdt:4348 119:samdt:4736",
     INC, ["fraud_prevention", "technology_emerging_issues"], 1, "medium", "R-CRYPTOATM",
     "operative text registers crypto ATM operators, mandates fraud disclosures stating virtual "
     "currency carries no NCUA or FDIC protection, and provides refunds for scam victims")
_add("116:hamdt:260",
     INC, ["cfpb_issues_structural_reform"], 1, "medium", "R-CFPB-CUSEAT",
     "operative text directs the CFPB to seek advisory appointees representing credit unions "
     "and community banks; secures credit-union representation in Bureau process")
_add("116:hamdt:248",
     INC, ["cfpb_issues_structural_reform"], 1, "medium", "R-CFPB-GAO",
     "operative text orders a GAO study of CFPB effectiveness and efficiency; oversight of the "
     "kind ACU records SUPPORT for in the CFPB cost-benefit transparency measure")
_add("118:samdt:2910",
     INC, ["mortgage_lending_housing"], 1, "medium", "R-ADU-TITLEI",
     "operative text modernises FHA Title I property-improvement and manufactured-housing loan "
     "limits and adds accessory dwelling unit financing; expands the lending channel")

# ================================= FLAGGED ===================================
_add("119:samdt:2241",
     FLG, ["charter_modernization_governance", "field_of_membership", "payments"], None, "low", "F-OMNIBUS-SUB",
     "large substitute carrying a State credit-union chartering savings clause; the clause is "
     "protective but the ultimate effect of a 21k-character omnibus substitute on the category "
     "cannot be reduced to it")
_add("117:samdt:5788",
     FLG, ["ncua_budget_share_insurance", "charter_modernization_governance"], None, "low", "F-FDTA",
     "operative text amends Title I of the FCU Act to impose Financial Data Transparency Act "
     "reporting standards on the NCUA; in-domain, but whether machine-readable reporting "
     "standards help or burden credit unions is not resolvable from amendment-specific evidence")
_add("117:samdt:216",
     FLG, ["payments"], None, "low", "F-FEDNOW",
     "budget reserve fund on maximum private-sector participation in the FedNow Service; FedNow "
     "is a named payments identifier but the reserve fund is non-operative and its direction "
     "for credit unions is not determinable")
_add("117:samdt:518 117:samdt:675 119:samdt:5097 119:samdt:835",
     FLG, [], None, "low", "F-RESERVEFUND",
     "deficit-neutral reserve fund touching a category subject (financial-innovation/CBDC "
     "grants, CFPB leadership structure, credit-card affordability, homeownership barriers); "
     "non-operative budget mechanics, so no ultimate policy effect can be read from the text")
_add("119:samdt:5869",
     FLG, ["examination_supervision"], None, "low", "F-BOI-ACCESS",
     "Ownership Clarity Act, financial-institution access to FinCEN beneficial ownership "
     "information; the short-act sidecar correctly kills the CLARITY Act collision, and the "
     "remaining BSA-burden reading is real but fires no category identifier")
_add("119:samdt:2335",
     FLG, ["examination_supervision"], None, "low", "F-BSA-SENSE",
     "sense of Congress that any entity functioning as a financial institution must comply with "
     "the Bank Secrecy Act; parity-relevant but non-operative")
_add("119:samdt:2340 119:samdt:2244 119:samdt:2342 119:samdt:2304",
     FLG, ["payments", "cfpb_issues_structural_reform"], None, "low", "F-STABLE-CFPB",
     "operative stablecoin provisions that preserve State law or federal consumer financial law "
     "authority over payment stablecoins; in-domain, direction for credit unions unresolved")
_add("116:samdt:1499",
     FLG, ["mortgage_lending_housing"], None, "low", "F-ENERGYUW",
     "enhanced energy-efficiency mortgage underwriting criteria developed in consultation with "
     "the FFIEC; touches underwriting but the operative actor is an energy agency")
_add("116:hamdt:840 116:hamdt:843 117:hamdt:48 117:hamdt:98 116:samdt:2116 119:samdt:6256",
     FLG, ["credit_card_consumer_fee_mandates"], None, "low", "F-TILA-CONSUMER",
     "operative amendments to the Truth in Lending Act or FDCPA affecting private education "
     "loans, confessions of judgement, cosigner discharge or servicemember-style forbearance; "
     "consumer-credit domain is real, effect on credit-union lending not resolvable")
_add("116:hamdt:251 116:hamdt:262 116:hamdt:249 116:hamdt:250 116:hamdt:255 116:hamdt:258 116:hamdt:259",
     FLG, ["cfpb_issues_structural_reform"], None, "low", "F-CFPB-REPORTING",
     "operative amendments to CFPA sec.1016/1022 adding Bureau reporting duties or MOUs on debt "
     "collection, payday lending, student borrowers, seniors or fair lending; in-domain but the "
     "reporting duty alone does not resolve to a positive or negative effect on credit unions")
_add("116:hamdt:252",
     FLG, ["cfpb_issues_structural_reform"], None, "low", "F-POINTER",
     "entire operative text is a positional strike inside H.R.1500 with no recoverable subject; "
     "text is present but uninformative, so it cannot be resolved either way")
_add("116:hamdt:491 116:hamdt:500 118:hamdt:211",
     FLG, [], None, "low", "F-POINTER-APPROP",
     "entire operative text is a dollar-figure or publication edit at a page-and-line pointer; "
     "the floor remarks assert a category subject but remarks cannot substitute for operative "
     "text, and a pointer edit cannot be resolved without the underlying page")
_add("119:samdt:3931",
     FLG, ["examination_supervision"], None, "low", "F-DEPOSITACCT",
     "requirements for deposit accounts naming the NCUA as the credit-union regulator; the "
     "operative subject reaches insured credit unions but its direction is not determinable")
_add("119:samdt:4323 119:samdt:4786 119:samdt:4324 119:samdt:4357",
     FLG, ["mortgage_lending_housing"], None, "low", "F-MORTGAGE-OPEN",
     "operative housing-finance amendments (downpayment assistance through CDFIs and MDIs, a "
     "public appraisal database with reconsideration of value, private mortgage insurance "
     "reform); in-domain, direction for credit-union lending unresolved")
_add("118:samdt:2372 119:samdt:3125 117:hamdt:101",
     FLG, ["defense_credit_union_issues"], None, "low", "F-SCRA-TRAINING",
     "operative amendments to the Servicemembers Civil Relief Act or to the financial literacy "
     "training that carries its protections; military-lending adjacent and it reaches credit "
     "unions as creditors, but no resolvable direction")
_add("119:samdt:4330",
     FLG, ["mortgage_lending_housing", "credit_card_consumer_fee_mandates"], None, "low", "F-HEI-TILA",
     "extends TILA sec.137 to home equity contracts; reaches a product credit unions do not "
     "offer, so the parity effect is second-order and not resolvable")
_add("119:samdt:6240",
     FLG, ["data_privacy_cybersecurity"], None, "low", "F-MEDDEBT",
     "amends FCRA and CFPB Regulation V on medical debt reporting; credit-reporting domain is "
     "real, effect on credit-union underwriting not resolvable from amendment-specific evidence")
_add("116:hamdt:254 116:hamdt:755 116:hamdt:756 116:hamdt:758 116:hamdt:761 116:hamdt:764 "
     "116:hamdt:765 117:hamdt:102 119:samdt:1056",
     FLG, ["data_privacy_cybersecurity"], None, "low", "F-FCRA-OPEN",
     "operative amendments to the Fair Credit Reporting Act (free score disclosure, positive "
     "reporting, scoring-model review, arrest information, CRA cybersecurity supervision, "
     "servicemember and medical-debt protections); credit unions furnish to these systems, but "
     "the direction of each change for credit unions is not resolvable here")
_add("119:samdt:3901",
     FLG, ["mortgage_lending_housing"], None, "low", "F-HOUSINGSUPPLY",
     "no amendment text; the official purpose is to increase the supply of affordable housing, "
     "which lands inside the mortgage and housing category ACU records SUPPORT positions in, but "
     "a purpose line alone cannot say what the amendment operatively does")
_add("117:samdt:2219 117:samdt:2614 117:samdt:2647 117:samdt:2649 118:samdt:1299 119:samdt:3932",
     FLG, [], None, "low", "F-NFIP-BOUNDARY",
     "operative subject is the National Flood Insurance Program itself (premium caps, coverage "
     "restriction, reauthorisation); the NFIP is not one of the 19 ACU categories, but NFIP "
     "lapse and pricing bear on mortgage closings, so the boundary is referred up rather than "
     "resolved by exclusion")

# ============================== EXCLUDE ======================================
_add("116:samdt:2185 116:samdt:2207 116:samdt:2281 117:samdt:4168 117:samdt:4645 118:samdt:1062 "
     "118:samdt:1072 118:samdt:1078 118:samdt:269 118:samdt:996 118:samdt:1986 118:samdt:2240 "
     "119:samdt:3120",
     EXC, [], None, "high", "X-NAHASDA",
     "operative text is the Native American Housing Assistance and Self-Determination "
     "reauthorisation; the credit_union_tax_status hit is the words appropriations/financial "
     "services inside a committee-referral list and the cdfi_fund hit is a definitional "
     "eligible-lender cross-reference, neither an operative change to either category")
_add("117:samdt:2595 117:samdt:5862",
     EXC, [], None, "high", "X-URBANWATERS",
     "Urban Waters Federal Partnership; the CDFI Fund appears only as one entry in a list of "
     "participating federal agencies")
_add("117:hamdt:103 117:samdt:3957",
     EXC, [], None, "high", "X-REGE-ARTIFACT",
     "the Regulation E hit is the token sequence regulation followed by subparagraph letter (E) "
     "in unrelated drinking-water and federal-personnel text; a tokenizer artifact, not a "
     "reference to Regulation E")
_add("118:samdt:135",
     EXC, [], None, "high", "X-DURBIN-NAME",
     "the Durbin amendment hit is the Congressional Record header naming Mr. DURBIN as the "
     "proposing senator, not the Durbin interchange amendment")
_add("117:samdt:5975 117:samdt:6425",
     EXC, [], None, "medium", "X-CASHACCEPT",
     "retail cash-acceptance mandate; the NCUA and Share Insurance Fund appear only in the "
     "definition of insured institutions, and the operative duty falls on retailers")
_add("118:samdt:1411 118:samdt:1466 118:samdt:682 118:samdt:829 119:samdt:3136 118:samdt:2262 "
     "118:samdt:481 116:samdt:1866 117:samdt:1495 117:samdt:5917 118:samdt:1903 118:samdt:2054 "
     "118:samdt:561 119:samdt:3257x",
     EXC, [], None, "high", "X-AGENCYLIST",
     "the credit union board or CFPB hit is the NCUA or Bureau appearing as one entry in a list "
     "of consulted agencies (Ukraine asset provisions, AI regulation reports, cross-border "
     "financial crime working groups, personal-data export controls); no operative change to a "
     "credit-union or Bureau authority")
_add("116:samdt:1456 117:samdt:2045 117:samdt:5297 119:samdt:4368",
     EXC, [], None, "high", "X-CDFI-DEFN",
     "community development financial institution appears only in a definition or an eligible-"
     "entity list of an energy, development-finance, housing-fund or tenant-screening program; "
     "no operative change to the CDFI Fund")
_add("116:samdt:2105",
     EXC, [], None, "medium", "X-UDAAP-PHRASE",
     "the unfair/deceptive/abusive phrase appears inside a Higher Education Act complaint-system "
     "description; no operative change to CFPA UDAAP authority")
_add("117:samdt:6275 118:samdt:218 119:samdt:3270 119:samdt:3751 119:samdt:3916",
     EXC, [], None, "medium", "X-OFFICIAL-PII",
     "protecting covered information of judges, legislators and at-risk officials in public "
     "records; the data broker definition is borrowed, but the subject is official personal "
     "safety, not consumer financial data privacy")
_add("116:samdt:2208 117:samdt:2367",
     EXC, [], None, "high", "X-HOMONYM",
     "groundwater overdraft and intermodal freight interchange; both hits are ordinary-English "
     "homonyms of category identifiers")
_add("117:samdt:2389 119:samdt:6645",
     EXC, [], None, "high", "X-CU-MENTION",
     "a credit union is named only as an example (an NCUA diversity training anecdote; "
     "courthouse tenant amenities), with no operative credit-union provision")
_add("118:samdt:591",
     EXC, [], None, "high", "X-FI-DEFLIST",
     "credit union appears only inside a definition of covered financial institutions in a "
     "fentanyl sanctions subtitle")
_add("119:samdt:2789 119:samdt:3384",
     EXC, [], None, "high", "X-PBM",
     "pharmacy benefit manager transparency and drug pricing; no credit-union category content")
_add("118:samdt:1412 118:samdt:1861 118:samdt:2069",
     EXC, [], None, "high", "X-ASYLUM",
     "asylum eligibility clarification; no credit-union category content")
_add("119:samdt:6505 119:samdt:6507",
     EXC, [], None, "high", "X-LEBANON",
     "Lebanon security assistance and sanctions; the bank secrecy reference is to Lebanon's own "
     "banking law, not the U.S. Bank Secrecy Act")
_add("117:samdt:4452 119:samdt:1868 119:samdt:2021 119:samdt:2446 119:samdt:3845 119:samdt:4681 "
     "119:samdt:4349 119:samdt:4352 119:samdt:4740",
     EXC, [], None, "medium", "X-CRYPTO-ETHICS",
     "digital-asset provisions whose operative subject is official conduct or federal investment "
     "(presidential and officeholder crypto holdings, El Salvador reporting, Social Security "
     "trust fund investment, bailout bans on trading protocols), not payments or technology "
     "policy bearing on credit unions")
_add("119:samdt:5814",
     EXC, [], None, "high", "X-TOC",
     "the central bank digital currency hit is a line in an intelligence authorisation table of "
     "contents, not an operative provision of this amendment")
_add("116:samdt:275",
     EXC, [], None, "medium", "X-CALLBLOCK",
     "free call-blocking technology for servicemembers imposes duties on communications "
     "providers; it does not change Telephone Consumer Protection Act liability for callers")
_add("119:samdt:5645",
     EXC, [], None, "medium", "X-SURVEILLPRICE",
     "surveillance-based price setting for air carriers; the CFPA cross-reference is definitional")
_add("119:samdt:2447",
     EXC, [], None, "medium", "X-RENTERFEES",
     "junk fees for renters; the operative duty falls on landlords and the CFPB rulemaking "
     "concerns rental housing, not credit-union products")
_add("116:hamdt:633 116:hamdt:634 116:samdt:1702 116:samdt:378 117:samdt:6377",
     EXC, [], None, "medium", "X-BENEFICIAL-OWNER",
     "beneficial ownership reporting for shell companies, Burma extractive industries, or "
     "AML duties on lawyers and accountants; none of the 19 categories covers corporate "
     "beneficial-ownership registration and no credit-union duty is changed")
_add("119:samdt:4618 119:samdt:4620 119:samdt:1991",
     EXC, [], None, "medium", "X-DATABROKER-CIVIC",
     "data broker provisions about polling places, DOGE record handling, and Social Security "
     "privatisation; civic-data subjects outside the consumer-financial-data category")
_add("117:samdt:1530 117:samdt:4029 118:samdt:296 119:samdt:4611",
     EXC, [], None, "medium", "X-AI-GOV",
     "artificial-intelligence governance task forces and supply-chain risk classification; no "
     "credit-union category content")
_add("117:samdt:4784 117:samdt:4798 117:samdt:6164 118:samdt:116 118:samdt:1829 118:samdt:256 "
     "119:samdt:4343 118:samdt:1835 116:samdt:2697 116:samdt:166 117:samdt:6163 118:samdt:1306 "
     "118:samdt:1307 118:samdt:1308 118:samdt:1313 118:samdt:1334 118:samdt:1335 119:samdt:4306 "
     "119:samdt:4340 119:samdt:6595 116:hamdt:475 117:samdt:2018",
     EXC, [], None, "medium", "X-OFFDOMAIN-TEXT",
     "operative subject is infrastructure defence, postsecondary data, savings-bond matching, "
     "Fourth Amendment records, corporate home purchases, coastal and flood mitigation, "
     "continuing-appropriations flood clauses, disaster housing and intake, FHA single-family "
     "eligibility riders, or vehicle technology; the flood, credit-reporting or SCRA phrase hits "
     "are incidental to those subjects and no category identifier operates")
_add("116:samdt:2267",
     EXC, [], None, "medium", "X-TAXCREDIT",
     "veteran small business start-up tax credit under the Internal Revenue Code; the credit-"
     "union tax status category concerns the credit-union federal tax exemption, not general "
     "business tax credits")


# --- family signatures over operative text, for rows not individually keyed ---
# (regex, disposition, categories, direction, confidence, rule_id, reason)
FAMILY_SIGNATURES = [
    (r"Native American Housing Assistance and Self-Determination", EXC, [], None, "high",
     "X-NAHASDA", "operative text is the NAHASDA reauthorisation; category hits are a "
     "committee-referral list and a definitional eligible-lender cross-reference"),
    (r"Mapping America'?s Pharmaceutical Supply|PHARMACEUTICAL SUPPLY CHAIN", EXC, [], None, "high",
     "X-SIDECAR-SUPPLY", "short-act collision: the sidecar's SUPPLY Act alias matched "
     "pharmaceutical supply-chain mapping text, not the housing SUPPLY Act"),
    (r"TRANSNATIONAL REPRESSION ACCOUNTABILITY AND PREVENTION|Transnational Repression Accountability",
     EXC, [], None, "high", "X-SIDECAR-TRAPS",
     "short-act collision: the sidecar's TRAPS Act alias matched Transnational Repression "
     "Accountability and Prevention, not the payment-scams task force"),
    (r"COUNTERING WEAPONS OF MASS DESTRUCTION", EXC, [], None, "high", "X-SIDECAR-STREAMLINE",
     "short-act collision: the sidecar's STREAMLINE Act alias matched a WMD and health-security "
     "division, not the CTR/SAR threshold measure"),
    (r"Clean Water for Rural Communities|Water Supply Infrastructure", EXC, [], None, "high",
     "X-SIDECAR-WATER", "short-act collision: the SUPPLY Act alias matched water-supply text"),
    (r"FEDERAL EMERGENCY MANAGEMENT|Robert T\. Stafford Disaster Relief", EXC, [], None, "medium",
     "X-DISASTER", "operative subject is federal disaster assistance; the flood-insurance "
     "phrase is an incidental cross-reference"),
]
