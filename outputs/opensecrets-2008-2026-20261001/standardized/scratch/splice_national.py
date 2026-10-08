from pathlib import Path

root = Path(__file__).resolve().parents[1]
p = root / 'osc' / 'extract.py'
s = p.read_text(encoding='utf-8')
a = s.index('    # ---- national ----')
b = s.index('    def election_cost(self):')
s = s[:a] + (root / 'scratch' / 'national_new.py').read_text(encoding='utf-8') + s[b:]
old1 = "'from_pacs_usd', 'from_individuals_usd', 'candidate_universe', 'display_type'] + PROV,"
new1 = ("'from_pacs_usd', 'from_individuals_usd', 'candidate_universe', 'display_type', 'control_type_value',\n"
        "                                          'control_display_value', 'controls_basis', 'table_caption'] + PROV,")
assert old1 in s
s = s.replace(old1, new1)
old2 = "'offices_expected', 'all_party_amount_usd', 'other_party_residual_signed_usd', 'money_universe'] + PROV,"
new2 = ("'offices_expected', 'all_party_amount_usd', 'other_party_residual_signed_usd', 'candidate_universe',\n"
        "                                       'display_type', 'controls_basis', 'coverage_note', 'money_universe'] + PROV,")
assert old2 in s
s = s.replace(old2, new2)
p.write_text(s, encoding='utf-8')
print('spliced')
