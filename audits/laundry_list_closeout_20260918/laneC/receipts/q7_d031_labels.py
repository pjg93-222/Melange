# Lane C / Q7 : published-artifact label census vs D-031 + D-034. READ-ONLY. stdlib only.
import json, os, collections, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems"
P = lambda *a: os.path.join(ROOT, *a)

# transcribed from fec/surfaces/dashboard_honors.py:12-15
STANDING_BY_LETTER = {'C':'Champion','F':'Defender','A':'Ally','H':'Highly Persuadable','P':'Persuadable',
 'G':'Lean Persuadable','T':'True Neutral','L':'Lean Skeptic','N':'Neutral','S':'Skeptic',
 'K':'Highly Skeptical','O':'Opponent','-':'Insufficient evidence'}
# transcribed from fec/surfaces/build_dashboard_bundle.py:119 (TC), inverted
TC_INV = {'C':'Champion','F':'Defender','A':'Ally','H':'Highly Persuadable','P':'Persuadable',
 'G':'Lean Persuadable','T':'True Neutral','L':'Lean Skeptic','N':'Neutral','S':'Skeptic',
 'K':'Highly Skeptical','O':'Opponent','-':'—'}
DEFEND_FIELDS = ['Interchange', 'Credit Card Mandates', 'CU Tax Status']   # LADDER_G defensive_fields

with open(P('dashboard_data.json'), encoding='utf-8') as fh:
    dd = json.load(fh)
with open(P('category_stance.json'), encoding='utf-8') as fh:
    cs = json.load(fh)

names = dd['name']; gen = dd['gen']; issues = dd['issues']; cats = dd['engine']['categories']
print("=" * 100)
print("Q7  PUBLISHED LABEL CENSUS  (dashboard_data.json)")
print("=" * 100)
print("members=%d  len(gen)=%d  issues=%d  engine.categories=%d" % (len(names), len(gen), len(issues), len(cats)))

print("\n-- [1] OVERALL label column dd['gen'] decoded by dashboard_honors.STANDING_BY_LETTER --")
overall = [STANDING_BY_LETTER[c] for c in gen]
cnt = collections.Counter(overall)
for lab, n in sorted(cnt.items(), key=lambda kv: -kv[1]):
    print("   %-22s %4d" % (lab, n))
print("   TOTAL %d" % sum(cnt.values()))
print("   D-031 check: overall 'Champion' count == 13 ?  -> %s (count=%d)"
      % (cnt.get('Champion', 0) == 13, cnt.get('Champion', 0)))
print("   overall 'Defender' count = %d  (D-031: Defender is a FIELD label, not an overall band)"
      % cnt.get('Defender', 0))
print("   crowned members (gen=='C'):", sorted(names[i] for i, c in enumerate(gen) if c == 'C'))

print("\n-- [2] dd['overall_honors'][i]['stance'] (the honors projection's overall standing) --")
oh = dd.get('overall_honors')
if not oh:
    print("   ABSENT from bundle")
else:
    st = collections.Counter(c.get('stance') for c in oh)
    for lab, n in sorted(st.items(), key=lambda kv: -kv[1]):
        print("   %-22s %4d" % (lab, n))
    print("   identical to the decoded gen column? %s" % (
        [c.get('stance') for c in oh] == overall))
    print("   stance_reason values:", dict(collections.Counter(c.get('stance_reason') for c in oh)))
    pt = collections.Counter(c.get('priority_tier') for c in oh)
    print("   priority_tier distribution:", dict(sorted(pt.items(), key=lambda kv: str(kv[0]))))
    print("   recognition values:", dict(collections.Counter(c.get('recognition') for c in oh)))

print("\n-- [3] dd['honors'][member][field]['recognition'] : the D-031 FIELD ladder --")
hon = dd.get('honors')
if not hon:
    print("   ABSENT from bundle")
else:
    field_cats = [c for c in cats if c]
    print("   honors rows=%d cols=%d ; field order == engine.categories[:-1]? %s"
          % (len(hon), len(hon[0]), len(hon[0]) == len(field_cats)))
    per_field = {}
    for j, cat in enumerate(field_cats):
        c = collections.Counter(hon[i][j].get('recognition') for i in range(len(hon)))
        per_field[cat] = c
    allvals = collections.Counter()
    for c in per_field.values(): allvals.update(c)
    print("\n   all field-ladder recognition values across %d x %d cells:" % (len(hon), len(field_cats)))
    for lab, n in sorted(allvals.items(), key=lambda kv: -kv[1]):
        print("      %-22s %6d" % (lab, n))
    order = ['Champion','Defender','Ally','Highly Persuadable','Persuadable','Lean Persuadable',
             'True Neutral','Lean Skeptic','Skeptic','Highly Skeptical','Opponent']
    extra = [k for k in allvals if k not in order]
    hdr = order + extra
    lbl = lambda h: ('(none)' if h is None else str(h))[:7]
    print("\n   per-field counts (D=defend field); '(none)' = recognition key absent/null")
    print("   %-28s %s" % ("field", " ".join("%7s" % lbl(h) for h in hdr)))
    for cat in field_cats:
        mark = ' D' if cat in DEFEND_FIELDS else '  '
        print("   %-26s%s %s" % (cat, mark, " ".join("%7d" % per_field[cat].get(h, 0) for h in hdr)))
    print("\n   D-031 check: 'Champion' must NOT appear in the three defend fields; 'Defender' must not appear elsewhere")
    for cat in field_cats:
        ch = per_field[cat].get('Champion', 0); de = per_field[cat].get('Defender', 0)
        ev = collections.Counter(hon[i][j].get('evidence_status')
                                 for j, c2 in enumerate(field_cats) if c2 == cat
                                 for i in range(len(hon)))
        if cat in DEFEND_FIELDS:
            print("      %-28s DEFEND  Champion=%-4d Defender=%-4d  -> %s   evidence_status=%s"
                  % (cat, ch, de, "OK" if ch == 0 else "VIOLATION (Champion present)", dict(ev)))
        elif de:
            print("      %-28s offense Champion=%-4d Defender=%-4d  -> VIOLATION (Defender present)" % (cat, ch, de))
    print("      (fields not listed above are offense fields with Defender=0)")
    print("\n   the %d 'Defender' field cells:" % allvals.get('Defender', 0))
    for i in range(len(hon)):
        for j, cat in enumerate(field_cats):
            if hon[i][j].get('recognition') == 'Defender':
                print("      %-26s %-24s cell=%s" % (names[i], cat,
                      json.dumps({k: v for k, v in hon[i][j].items()
                                  if k in ('recognition','reason','evidence_status','action_count',
                                           'positive_action_count','negative_action_count','raw_field_score',
                                           'rank_start','rank_end','sub_cohort','sub_cohort_size')},
                                 sort_keys=True)))

print("\n-- [4] honors_meta --")
hm = dd.get('honors_meta') or {}
for k in ('schema', 'generation_id', 'as_of', 'overall_board_mode'):
    print("   %-20s %r" % (k, hm.get(k)))
print("   policy      =", json.dumps(hm.get('policy'), sort_keys=True))
print("   overall_policy =", json.dumps(hm.get('overall_policy'), sort_keys=True))
ob = hm.get('overall_board') or {}
print("   overall_board keys =", list(ob))
print("   overall_board.top13 (n=%d) = %s" % (len(ob.get('top13') or []), ob.get('top13')))
print("   evidence_window =", json.dumps(hm.get('evidence_window'), sort_keys=True))

print("\n-- [5] category_stance.json matrix : the per-cell stance ladder (the OTHER label layer) --")
mat = cs['matrix']
allc = collections.Counter(v for d in mat.values() for v in d.values())
for lab, n in sorted(allc.items(), key=lambda kv: -kv[1]):
    print("   %-22s %6d" % (lab, n))
print("   defensive set in artifact:", cs['defensive'])
print("\n   per-field Champion/Defender counts in category_stance.json:")
for cat in cs['cats']:
    c = collections.Counter(d.get(cat) for d in mat.values())
    print("      %-28s%s Champion=%-4d Defender=%-4d Ally=%-4d Opponent=%-4d"
          % (cat, ' D' if cat in set(cs['defensive']) else '  ',
             c.get('Champion', 0), c.get('Defender', 0), c.get('Ally', 0), c.get('Opponent', 0)))

print("\n-- [6] dd['stance'] per-member-per-issue letter strings (what the page renders) --")
stance = dd['stance']
print("   n=%d, each len=%d (issues incl. 'Overall CU stance')" % (len(stance), len(stance[0])))
for j, iss in enumerate(issues):
    c = collections.Counter(TC_INV.get(s[j], '?') for s in stance)
    print("      [%2d] %-46s Champion=%-4d Defender=%-4d Ally=%-4d Opponent=%-4d —=%d"
          % (j, iss[:46], c.get('Champion', 0), c.get('Defender', 0), c.get('Ally', 0),
             c.get('Opponent', 0), c.get('—', 0)))

print("\n-- [7] D-034 cross-post twins (a0c45a709 'Score every social post; cross-post twins noted, not excluded') --")
for key in ('press_policy',):
    print("   category_stance.thresholds.%s = %r" % (key, (cs.get('thresholds') or {}).get(key)))
sc_ = cs.get('source_contract') or {}
print("   category_stance.source_contract =", json.dumps(sc_, sort_keys=True)[:400])
