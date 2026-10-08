# moneyball_acu_search_urls.R
# All 18 advanced-search query templates from Moneyball_ACU_Search_Outline.docx,
# in outline order. Each has the member switch slot set to the literal
# placeholder %22__MEMBER__%22 (decoded "__MEMBER__") for build_member_url().
#
# Verified programmatically for every template:
#   - exactly one __MEMBER__ slot
#   - decoded query is valid JSON
#   - placeholder sits in the sponsor field, except cdfi_fund and
#     cu_bank_competitive, whose switch is the search/contains field
#   - reconstructs byte-for-byte to the outline's hyperlink aside from the swap

# === 1. Examination & Supervision ===
examination_supervision_url_parts <- c(
  "https://www.congress.gov/advanced-search?raw=",
  # --- Block 1: congresses 119 / 118 / 117 ---
  "%5B%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22congress%22%2C%22operator%22%3A%22multi%22%2C%22value%22%3A%5B%22119%22%2C%22118%22%2C%22117%22%5D%7D%7D%5D%7D",
  # --- Block 2: subject-matter terms (one AND + many OR) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B",
  "%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22examination+credit+union%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22supervision+credit+union%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22notice-and-comment+rulemaking+credit+union%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22filing+threshold+suspicious+activity%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22filing+threshold+currency+transaction%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata_case%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22CAMELS+rating%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22reputational+risk+supervision%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22safety+and+soundness+examination%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22examination+cycle+credit+union%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22off-site+examination+credit+union%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22examination+appeal+rights+credit+union%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22tailoring+regulatory+burden+credit+union%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22asset+threshold+regulatory+relief%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata_case%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22FFIEC%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22Federal+Financial+Institutions+Examination+Council%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22CTR+threshold%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22currency+transaction+report+threshold%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22SAR+threshold%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22suspicious+activity+report+threshold%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22search%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22Bank+Secrecy+Act+credit+union%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata_case%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22FIRM+Act%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata_case%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22HUMPS+Act%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata_case%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22SMART+Act%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata_case%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22STREAMLINE+Act%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata_case%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22Financial+Reporting+Threshold+Modernization+Act%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata_case%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22Community+Bank+Regulatory+Tailoring+Act%22%7D%7D",
  "%5D%7D",
  # --- Block 3: sponsor == SWITCH VARIABLE (the member) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22sponsor%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22__MEMBER__%22%7D%7D%5D%7D",
  # --- Block 4: subject areas (Commerce / Finance / Government Operations) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22subject%22%2C%22operator%22%3A%22multi%22%2C%22value%22%3A%5B%22Commerce%22%2C%22Finance+and+Financial+Sector%22%2C%22Government+Operations+and+Politics%22%5D%7D%7D%5D%7D",
  "%5D"
)

# === 2. Credit Union Capital Requirements ===
cu_capital_requirements_url_parts <- c(
  "https://www.congress.gov/advanced-search?raw=",
  # --- Block 1: congresses 119 / 118 / 117 ---
  "%5B%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22congress%22%2C%22operator%22%3A%22multi%22%2C%22value%22%3A%5B%22119%22%2C%22118%22%2C%22117%22%5D%7D%7D%5D%7D",
  # --- Block 2: subject-matter terms (one AND + many OR) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B",
  "%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22credit+union+supplement+capital%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22credit+union+additional+capital%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22credit+union+capital+requirements%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22credit+union+net+worth+ratio%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22risk-based+capital+credit+union%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22subordinated+debt+credit+union%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22secondary+capital+credit+union%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22prompt+corrective+action+credit+union%22%7D%7D",
  "%5D%7D",
  # --- Block 3: subject areas (Commerce / Finance / Government Operations / Housing) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22subject%22%2C%22operator%22%3A%22multi%22%2C%22value%22%3A%5B%22Commerce%22%2C%22Finance+and+Financial+Sector%22%2C%22Government+Operations+and+Politics%22%2C%22Housing+and+Community+Development%22%5D%7D%7D%5D%7D",
  # --- Block 4: sponsor == SWITCH VARIABLE (the member) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22sponsor%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22__MEMBER__%22%7D%7D%5D%7D",
  "%5D"
)

# === 3. NCUA Budget & Share Insurance Fund ===
ncua_budget_share_insurance_url_parts <- c(
  "https://www.congress.gov/advanced-search?raw=",
  # --- Block 1: congresses 119 / 118 / 117 ---
  "%5B%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22congress%22%2C%22operator%22%3A%22multi%22%2C%22value%22%3A%5B%22119%22%2C%22118%22%2C%22117%22%5D%7D%7D%5D%7D",
  # --- Block 2: subject-matter terms (one AND + many OR) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B",
  "%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22credit+union+budget+process%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22National+Credit+Union+Share+Insurance+Fund%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22Federal+Credit+Union+Act%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22NCUA+budget+transparency%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22NCUA+overhead+transfer+rate%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22Share+Insurance+Fund+equity+ratio%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata_case%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22NCUA+board%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22NCUA+Central+Liquidity+Facility+Enhancements%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22Central+liquidity+facility+credit+union%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22CLF+credit+union%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22SIF+equity+ratio%22%7D%7D",
  "%5D%7D",
  # --- Block 3: sponsor == SWITCH VARIABLE (the member) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22sponsor%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22__MEMBER__%22%7D%7D%5D%7D",
  # --- Block 4: subject areas (Commerce / Finance / Government Operations) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22subject%22%2C%22operator%22%3A%22multi%22%2C%22value%22%3A%5B%22Commerce%22%2C%22Finance+and+Financial+Sector%22%2C%22Government+Operations+and+Politics%22%5D%7D%7D%5D%7D",
  "%5D"
)

# === 4. Interchange (Status Quo) (-) ===
interchange_status_quo_url_parts <- c(
  "https://www.congress.gov/advanced-search?raw=",
  # --- Block 1: congresses 119 / 118 / 117 ---
  "%5B%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22congress%22%2C%22operator%22%3A%22multi%22%2C%22value%22%3A%5B%22119%22%2C%22118%22%2C%22117%22%5D%7D%7D%5D%7D",
  # --- Block 2: subject-matter terms (all OR) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22Credit+Card+Competition+Act%22%7D%7D%5D%7D",
  # --- Block 3: sponsor == SWITCH VARIABLE (the member) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22sponsor%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22__MEMBER__%22%7D%7D%5D%7D",
  "%5D"
)

# === 5. Payments ===
payments_url_parts <- c(
  "https://www.congress.gov/advanced-search?raw=",
  # --- Block 1: congresses 119 / 118 / 117 ---
  "%5B%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22congress%22%2C%22operator%22%3A%22multi%22%2C%22value%22%3A%5B%22119%22%2C%22118%22%2C%22117%22%5D%7D%7D%5D%7D",
  # --- Block 2: subject-matter terms (all OR) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B",
  "%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22FedNow%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22real-time+payments%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22install+payment+fund%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22ACH+payment%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22faster+payments+credit+union%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22same-day+ACH%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22automated+clearing+house%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22faster+payments%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22open+banking%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22earned+wage+access%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22payment+system+access%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22instant+payment%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22master+account%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22buy+now+pay+later%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata_nostem%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22Regulation+E%22%7D%7D",
  "%5D%7D",
  # --- Block 3: sponsor == SWITCH VARIABLE (the member) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22sponsor%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22__MEMBER__%22%7D%7D%5D%7D",
  # --- Block 4: subject areas (Agriculture / Commerce / Finance) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22subject%22%2C%22operator%22%3A%22multi%22%2C%22value%22%3A%5B%22Agriculture+and+Food%22%2C%22Commerce%22%2C%22Finance+and+Financial+Sector%22%5D%7D%7D%5D%7D",
  "%5D"
)

# === 6. Technology & Emerging Issues ===
technology_emerging_url_parts <- c(
  "https://www.congress.gov/advanced-search?raw=",
  # --- Block 1: congresses 119 / 118 / 117 ---
  "%5B%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22congress%22%2C%22operator%22%3A%22multi%22%2C%22value%22%3A%5B%22119%22%2C%22118%22%2C%22117%22%5D%7D%7D%5D%7D",
  # --- Block 2: subject-matter terms (one AND + many OR) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B",
  "%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22central+bank+digital+currency%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22remote+online+notarization%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22CDBC%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22fintech+partnership+credit+union%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22NCUA+overhead+transfer+rate%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22open+banking%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata_case%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22AI+lending+model%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22digital+commodity%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22digital+asset+credit+union%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22machine+learning+underwriting%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22algorithmic+credit+decision%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22Anti-CBDC+Surveillance+State+Act%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22Digital+Asset+Market+Clarity+Acy%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22Secure+Notarization+Act%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22Genius+Act%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22Stable+Act%22%7D%7D",
  "%5D%7D",
  # --- Block 3: sponsor == SWITCH VARIABLE (the member) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22sponsor%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22__MEMBER__%22%7D%7D%5D%7D",
  # --- Block 4: subject areas (Commerce / Crime / Finance / Labor / Law / Science) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22subject%22%2C%22operator%22%3A%22multi%22%2C%22value%22%3A%5B%22Commerce%22%2C%22Crime+and+Law+Enforcement%22%2C%22Finance+and+Financial+Sector%22%2C%22Labor+and+Employment%22%2C%22Law%22%2C%22Science%2C+Technology%2C+Communications%22%5D%7D%7D%5D%7D",
  "%5D"
)

# === 7. Fraud Prevention ===
fraud_prevention_url_parts <- c(
  "https://www.congress.gov/advanced-search?raw=",
  # --- Block 1: congresses 119 / 118 / 117 ---
  "%5B%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22congress%22%2C%22operator%22%3A%22multi%22%2C%22value%22%3A%5B%22119%22%2C%22118%22%2C%22117%22%5D%7D%7D%5D%7D",
  # --- Block 2: subject-matter terms (one AND + many OR) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B",
  "%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22financial+fraud+credit+union%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22payment+fraud%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22Task+Force+for+Recognizing+and+Averting+Payment+Scams%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22check+fraud%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22check+processing+vulnerabilities%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22permissible+information+sharing%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22payment+scam%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22authorized+push+payment+fraud%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22elder+financ+exploit+credit%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22fraud+information+sharing+safe+harbor%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22mail+theft+check+fraud%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22imposter+scam%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22romance+scam%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22identity+theft+credit%22%7D%7D",
  "%5D%7D",
  # --- Block 3: sponsor == SWITCH VARIABLE (the member) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22sponsor%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22__MEMBER__%22%7D%7D%5D%7D",
  # --- Block 4: subject areas (Commerce / Crime / Finance / Law / Science) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22subject%22%2C%22operator%22%3A%22multi%22%2C%22value%22%3A%5B%22Commerce%22%2C%22Crime+and+Law+Enforcement%22%2C%22Finance+and+Financial+Sector%22%2C%22Law%22%2C%22Science%2C+Technology%2C+Communications%22%5D%7D%7D%5D%7D",
  "%5D"
)

# === 8. Data Privacy & Cybersecurity ===
data_privacy_cybersecurity_url_parts <- c(
  "https://www.congress.gov/advanced-search?raw=",
  # --- Block 1: congresses 119 / 118 / 117 ---
  "%5B%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22congress%22%2C%22operator%22%3A%22multi%22%2C%22value%22%3A%5B%22119%22%2C%22118%22%2C%22117%22%5D%7D%7D%5D%7D",
  # --- Block 2: subject-matter terms (one AND + many OR) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B",
  "%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22federal+data+privacy+standard%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22national+data+privacy+standard%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22federal+preemption+privacy%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22state+privacy+law+preemption%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22GLBA+exemption+state+privacy+law%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22GLBA+exemption%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22Gramm-Leach-Bliley+Act+exemption%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22data+breach+notification%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22data+security+standard%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22mortgage+trigger+leads%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22trigger+lead%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22data+broker%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22permissible+data+sharing%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22Homebuyers+Privacy+Protection+Act%22%7D%7D",
  "%5D%7D",
  # --- Block 3: sponsor == SWITCH VARIABLE (the member) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22sponsor%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22__MEMBER__%22%7D%7D%5D%7D",
  # --- Block 4: subject areas (Armed Forces / Commerce / Crime / Finance / Law / Science) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22subject%22%2C%22operator%22%3A%22multi%22%2C%22value%22%3A%5B%22Armed+Forces+and+National+Security%22%2C%22Commerce%22%2C%22Crime+and+Law+Enforcement%22%2C%22Finance+and+Financial+Sector%22%2C%22Law%22%2C%22Science%2C+Technology%2C+Communications%22%5D%7D%7D%5D%7D",
  "%5D"
)

# === 9. Charter Modernization & Governance ===
charter_modernization_url_parts <- c(
  "https://www.congress.gov/advanced-search?raw=",
  # --- Block 1: congresses 119 / 118 / 117 ---
  "%5B%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22congress%22%2C%22operator%22%3A%22multi%22%2C%22value%22%3A%5B%22119%22%2C%22118%22%2C%22117%22%5D%7D%7D%5D%7D",
  # --- Block 2: subject-matter terms (one AND + many OR) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B",
  "%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22federal+credit+union+modernization%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22credit+union+board%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22credit+union+governance%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22credit+union+diversify%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22de+novo+credit+union%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22credit+union+chartering%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22FHLB+membership+credit+union%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22Federal+Home+Loan+Bank+credit+union%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22Credit+Union+Board+Modernization+Act%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22American+Access+to+Banking+Act%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22MORE+Opportunities+for+Homeownership+Act%22%7D%7D",
  "%5D%7D",
  # --- Block 3: sponsor == SWITCH VARIABLE (the member) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22sponsor%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22__MEMBER__%22%7D%7D%5D%7D",
  # --- Block 4: subject areas (Commerce / Families / Finance) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22subject%22%2C%22operator%22%3A%22multi%22%2C%22value%22%3A%5B%22Commerce%22%2C%22Families%22%2C%22Finance+and+Financial+Sector%22%5D%7D%7D%5D%7D",
  "%5D"
)

# === 10. Defense Credit Union Issues ===
defense_credit_union_url_parts <- c(
  "https://www.congress.gov/advanced-search?raw=",
  # --- Block 1: congresses 119 / 118 / 117 ---
  "%5B%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22congress%22%2C%22operator%22%3A%22multi%22%2C%22value%22%3A%5B%22119%22%2C%22118%22%2C%22117%22%5D%7D%7D%5D%7D",
  # --- Block 2: subject-matter terms (one AND + many OR) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B",
  "%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22credit+union+servicemembers%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22credit+union+military%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22credit+union+nominal+lease%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22military+installation+credit+union%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22on-base+financial+services%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22on-site+financial+services%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22Military+lending+act+credit+union%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22defense+credit+union+land+lease%22%7D%7D",
  "%5D%7D",
  # --- Block 3: subject areas (Armed Forces / Commerce / Finance) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22subject%22%2C%22operator%22%3A%22multi%22%2C%22value%22%3A%5B%22Armed+Forces+and+National+Security%22%2C%22Commerce%22%2C%22Finance+and+Financial+Sector%22%5D%7D%7D%5D%7D",
  # --- Block 4: sponsor == SWITCH VARIABLE (the member) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22sponsor%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22__MEMBER__%22%7D%7D%5D%7D",
  "%5D"
)

# === 11. Field of Membership ===
field_of_membership_url_parts <- c(
  "https://www.congress.gov/advanced-search?raw=",
  # --- Block 1: congresses 119 / 118 / 117 ---
  "%5B%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22congress%22%2C%22operator%22%3A%22multi%22%2C%22value%22%3A%5B%22119%22%2C%22118%22%2C%22117%22%5D%7D%7D%5D%7D",
  # --- Block 2: subject-matter terms (all OR) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B",
  "%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22credit+union+dual+charter%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22credit+union+federal+charter%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22credit+union+membership%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22field+of+membership%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22common+bond+credit+union%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22multiple+common+bond%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22community+charter+credit+union%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22underserved+area+credit+union%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22state+chartered+credit+union%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22dual+charter+system%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22federal+preemption+state+credit+union%22%7D%7D",
  "%5D%7D",
  # --- Block 3: sponsor == SWITCH VARIABLE (the member) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22sponsor%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22__MEMBER__%22%7D%7D%5D%7D",
  # --- Block 4: subject areas (Commerce / Finance) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22subject%22%2C%22operator%22%3A%22multi%22%2C%22value%22%3A%5B%22Commerce%22%2C%22Finance+and+Financial+Sector%22%5D%7D%7D%5D%7D",
  "%5D"
)

# === 12. CDFI Fund ===
cdfi_fund_url_parts <- c(
  "https://www.congress.gov/advanced-search?raw=",
  # --- Block 1: congresses 119 / 118 / 117 ---
  "%5B%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22congress%22%2C%22operator%22%3A%22multi%22%2C%22value%22%3A%5B%22119%22%2C%22118%22%2C%22117%22%5D%7D%7D%5D%7D",
  # --- Block 2: subject-matter terms (all OR) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B",
  "%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22CDFI%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22Community+Development+Financial+Institution%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22Community+Development+Financial+Institution+Fund%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22CDFI+Fund%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22CDFI+Fund+appropriations%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22CDFI+certification%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22Community+Development+Financial+Institution+Fund+appropriations%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22Community+Development+Financial+Institution+certification%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22CDFI+bond+guarantee%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22minority+depository+institution%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22Community+Development+Financial+Institution+bond+guarantee%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata_case%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22MDI%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22CDFI+Fund+Transparency+Act%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata_case%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22AFFORD+Act%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22CDFI+Bond+Guarantee+Program+Improvement+Act%22%7D%7D",
  "%5D%7D",
  # --- Block 3: subject areas (Agriculture / Commerce / Finance / Housing) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22subject%22%2C%22operator%22%3A%22multi%22%2C%22value%22%3A%5B%22Agriculture+and+Food%22%2C%22Commerce%22%2C%22Finance+and+Financial+Sector%22%2C%22Housing+and+Community+Development%22%5D%7D%7D%5D%7D",
  # --- Block 4: search == SWITCH VARIABLE (the member) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22sponsor%22%2C%22operator%22%3A%22contains%22%2C%22value%22%3A%22__MEMBER__%22%7D%7D%5D%7D"
)

# === 14. CFPB Issues & Structural Reform ===
cfpb_reform_url_parts <- c(
  "https://www.congress.gov/advanced-search?raw=",
  # --- Block 1: congresses 119 / 118 / 117 ---
  "%5B%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22congress%22%2C%22operator%22%3A%22multi%22%2C%22value%22%3A%5B%22119%22%2C%22118%22%2C%22117%22%5D%7D%7D%5D%7D",
  # --- Block 2: subject-matter terms (all OR) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B",
  "%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22CFPB+reform%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22Consumer+Financial+Protection+Bureau+reform%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22CFPB+governance+structure%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22Consumer+Financial+Protection+Bureau+governance+structure%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22CFPB+funding+structure%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22Consumer+Financial+Protection+Bureau+funding+structure%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22CFPB+council%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22Consumer+Financial+Protection+Bureau+council%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22CFPB+commission+structure%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22Consumer+Financial+Protection+Bureau+structure%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22Consumer+Financial+Protection+Bureau+congressional+approrpriation%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22Consumer+Financial+Protection+Bureau+cost-benefit+analysis%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22CFBP+congressional+appropriation%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22CFPB+cost-benefit+analysis%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22abusive+standard+Dodd-Frank%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22Section+1071+small+business+data%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22UDAAP%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22unfair+deceptive+abusive+acts+practice%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22Transparency+in+CFPB+Cost-Benefit+Analysis+Act%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22Bureau+of+Consumer+Financial+Protection+Commission+Act%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22Rectifying+UDAAP+Act%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22TABS+Act%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%221071+Repeal+to+Protect+Small+Business+Lending+Act%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22Business+of+Insurance+Regulatory+Reform+Act%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22overdraft+rule+CFPB%22%7D%7D",
  "%5D%7D",
  # --- Block 3: subject areas (Commerce / Finance) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22subject%22%2C%22operator%22%3A%22multi%22%2C%22value%22%3A%5B%22Commerce%22%2C%22Finance+and+Financial+Sector%22%5D%7D%7D%5D%7D",
  # --- Block 4: sponsor == SWITCH VARIABLE (the member) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22sponsor%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22__MEMBER__%22%7D%7D%5D%7D",
  "%5D"
)

# === 15. Credit Card & Consumer-Fee Mandates (Status Quo) (-) ===
credit_card_consumer_fee_url_parts <- c(
  "https://www.congress.gov/advanced-search?raw=",
  # --- Block 1: congresses 119 / 118 / 117 ---
  "%5B%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22congress%22%2C%22operator%22%3A%22multi%22%2C%22value%22%3A%5B%22119%22%2C%22118%22%2C%22117%22%5D%7D%7D%5D%7D",
  # --- Block 2: subject-matter terms (all OR) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B",
  "%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22credit+card+rate+cap%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22credit+car+interest+rate+cap%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22interchange+limit%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22overdraft+fee+cap%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22overdraft+lending+rule%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22credit+card+late+fee%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22usury+limit+credit+card%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata_case%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22Truth+in+Lending+Act+interest+rate%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22junk+fee+financial+institution%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%2210+Percent+Credit+Card+Interest+Rate+Cap+Act%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22Credit+Card+Fairness+Act%22%7D%7D",
  "%5D%7D",
  # --- Block 3: subject areas (Commerce / Finance) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22subject%22%2C%22operator%22%3A%22multi%22%2C%22value%22%3A%5B%22Commerce%22%2C%22Finance+and+Financial+Sector%22%5D%7D%7D%5D%7D",
  # --- Block 4: sponsor == SWITCH VARIABLE (the member) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22sponsor%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22__MEMBER__%22%7D%7D%5D%7D",
  # --- Block 5: NOT — exclusion filter ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22notContains%22%2C%22value%22%3A%22Disapproving+the+rule+submitted+by+the+Bureau+of+Consumer+Financial+Protection+relating+to+%5C%22Overdraft+Lending%3A+Very+Large+Financial+Institutions%5C%22.%22%7D%7D%5D%7D",
  "%5D"
)

# === 16. Telephone Consumer Protection Act Issues ===
tcpa_url_parts <- c(
  "https://www.congress.gov/advanced-search?raw=",
  # --- Block 1: congresses 119 / 118 / 117 ---
  "%5B%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22congress%22%2C%22operator%22%3A%22multi%22%2C%22value%22%3A%5B%22119%22%2C%22118%22%2C%22117%22%5D%7D%7D%5D%7D",
  # --- Block 2: subject-matter terms (all OR) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B",
  "%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22Telephone+Consumer+Protection+Act%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22TCPA%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22FCC+credit+union%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22Federal+Communications+Commission+credit+union%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22robocall+financial+institution%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22autodialer+consent%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22Prior+express+consent+TCPA%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22Prior+express+consent+Telephone+Consumer+Protection+Act%22%7D%7D",
  "%5D%7D",
  # --- Block 3: sponsor == SWITCH VARIABLE (the member) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22sponsor%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22__MEMBER__%22%7D%7D%5D%7D",
  # --- Block 4: subject areas (Commerce / Crime / Energy / Law / Science) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22subject%22%2C%22operator%22%3A%22multi%22%2C%22value%22%3A%5B%22Commerce%22%2C%22Crime+and+Law+Enforcement%22%2C%22Energy%22%2C%22Law%22%2C%22Science%2C+Technology%2C+Communications%22%5D%7D%7D%5D%7D",
  "%5D"
)

# === 17. Member Business Lending ===
member_business_lending_url_parts <- c(
  "https://www.congress.gov/advanced-search?raw=",
  # --- Block 1: congresses 119 / 118 / 117 ---
  "%5B%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22congress%22%2C%22operator%22%3A%22multi%22%2C%22value%22%3A%5B%22119%22%2C%22118%22%2C%22117%22%5D%7D%7D%5D%7D",
  # --- Block 2: subject-matter terms (all OR) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B",
  "%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22de+minimis+threshold%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22credit+union+lending%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22credit+union+member+business+loan%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22exempt+loan+MBL%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22member+business+loan+exempt%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22MBL+veteran%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22member+business+loan+veteran%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22increase+maximum+loan+maturity%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22member+business+lending+cap%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%2212.25%25+asset+credit+union%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%2212.25+percent+asset+credit+union%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22business+loan+threshold+credit+union%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22commercial+lending+credit+union%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22SBA+7%28a%29+credit+union%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22loan+maturity+limit+credit+union%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22credit+union+loan+limit+increase%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22exempt+loan+credit+union+veteran%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22Veterans+Member+Business+Loan+Act%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22Increasing+Credit+Union+Lending+for+Business+Growth+Act%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22Expanding+Access+to+Lending+Options+Act%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22Protecting+Access+to+Credit+for+Small+Businesses+Act%22%7D%7D",
  "%5D%7D",
  # --- Block 3: subject areas (Commerce / Finance) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22subject%22%2C%22operator%22%3A%22multi%22%2C%22value%22%3A%5B%22Commerce%22%2C%22Finance+and+Financial+Sector%22%5D%7D%7D%5D%7D",
  # --- Block 4: sponsor == SWITCH VARIABLE (the member) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22sponsor%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22__MEMBER__%22%7D%7D%5D%7D",
  "%5D"
)

# === 18. Mortgage Lending & Housing ===
mortgage_lending_housing_url_parts <- c(
  "https://www.congress.gov/advanced-search?raw=",
  # --- Block 1: congresses 119 / 118 / 117 ---
  "%5B%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22congress%22%2C%22operator%22%3A%22multi%22%2C%22value%22%3A%5B%22119%22%2C%22118%22%2C%22117%22%5D%7D%7D%5D%7D",
  # --- Block 2: subject-matter terms (all OR) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B",
  "%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22credit+union+mortgage%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22flood+insurance+affordable%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22National+Flood+Insurance+Program+reauthorization%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22NFIP+reauthorization%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22predictable+mortgage+homebuyer%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22regulatory+exception+credit+union+mortgage%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22secondary+market+liquidity%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22credit+union+affordable+mortgage+product%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22affordable+mortgage+credit+union%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22first-time+homebuyer+credit+union%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22down+payment+assistance%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22accessory+dwelling+unit+financing%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22ADU+financing%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22title%22%2C%22operator%22%3A%22containsAll%22%2C%22value%22%3A%22FHA+mortgage+insurance%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22Home+Mortgage+Disclosure+Act%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata_case%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22HELPER+Act%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22Home+of+Your+Own+Act%22%7D%7D",
  "%2C%7B%22op%22%3A%22OR%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22metadata_case%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22SUPPLY+Act%22%7D%7D",
  "%5D%7D",
  # --- Block 3: subject areas (Commerce / Emergency Management / Finance / Housing) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22subject%22%2C%22operator%22%3A%22multi%22%2C%22value%22%3A%5B%22Commerce%22%2C%22Emergency+Management%22%2C%22Finance+and+Financial+Sector%22%2C%22Housing+and+Community+Development%22%5D%7D%7D%5D%7D",
  # --- Block 4: sponsor == SWITCH VARIABLE (the member) ---
  "%2C%7B%22op%22%3A%22AND%22%2C%22conditions%22%3A%5B%7B%22op%22%3A%22AND%22%2C%22inputs%22%3A%7B%22source%22%3A%22legislation%22%2C%22field%22%3A%22sponsor%22%2C%22operator%22%3A%22phrase%22%2C%22value%22%3A%22__MEMBER__%22%7D%7D%5D%7D",
  "%5D"
)

