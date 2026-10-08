# Lane C / Q2 Q3 Q4 Q5 Q6 : bill-universe fork, placement facts, bill_key collisions,
# registry-direction literals, original-cosponsor twins.  READ-ONLY.  stdlib + openpyxl.
# NOTHING under fec/ is imported.  bill_key / bill_type_key / _congress / role_weight /
# canonical_role / canonical_category / congress_decay below are TRANSCRIBED VERBATIM from
# the LIVE producer's rule module fec/bill_rules.py (quoted with file:line in REPORT.md).
import os, csv, json, re, collections, sys
import openpyxl
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems"
P = lambda *a: os.path.join(ROOT, *a)
ARCHIVE_SELECTED = "congress_bills_archive_20260825_115305.xlsx"
ARCHIVE_PRIOR    = "congress_bills_archive_20260624_115822.xlsx"

# ---- transcribed from fec/bill_rules.py ----
def bill_key(value):                                       # :135-138
    m = re.match(r'\s*([HS])\.?\s*([RJ]?\.?\s*(?:Res\.?)?)\s*(\d+)', str(value or ''), re.I)
    return (m.group(1).upper(), int(m.group(3))) if m else None

def bill_type_key(value):                                  # :141-154
    m = re.match(r'\s*([HS])\.?\s*(?:(R|J\.?\s*Res|Con\.?\s*Res|Res)\.?\s*)?(\d+)', str(value or ''), re.I)
    if not m:
        return None
    tok = re.sub(r'[^A-Za-z]', '', m.group(2) or 'R').upper()
    return (m.group(1).upper(), tok, int(m.group(3)))

def _congress(value):                                      # :240-244
    try:
        return str(int(float(value)))
    except (TypeError, ValueError):
        return str(value or '').strip()

def canonical_role(role):                                  # :222-230
    v = str(role or '').strip().lower()
    if 'original' in v: return 'original-cosponsor'
    if 'cosponsor' in v or 'co-spons' in v: return 'cosponsor'
    if 'sponsor' in v: return 'sponsor'
    return v or 'other'

def role_weight(role):                                     # :211-219
    v = canonical_role(role)
    return {'original-cosponsor': 2.0, 'cosponsor': 1.0, 'sponsor': 3.0}.get(v, 1.0)

CATEGORIES = ('Examination & Supervision','CU Capital Requirements','NCUA Budget & Insurance','Interchange',
 'Payments','Technology & Emerging','Fraud Prevention','Data Privacy & Cyber','Charter Modernization',
 'Defense CU Issues','Field of Membership','CU Tax Status','CDFI Fund','CFPB','Credit Card Mandates','TCPA',
 'Member Business Lending','Mortgage & Housing')
LABEL_TO_CANONICAL = {'CFPB Issues & Structural Reform':'CFPB','Charter Modernization & Governance':'Charter Modernization',
 'Credit Union Capital Requirements':'CU Capital Requirements','Credit Card & Consumer-Fee Mandates':'Credit Card Mandates',
 'Credit Union Tax Status':'CU Tax Status','Data Privacy & Cybersecurity':'Data Privacy & Cyber',
 'Defense Credit Union Issues':'Defense CU Issues','Mortgage Lending & Housing':'Mortgage & Housing',
 'NCUA Budget & Share Insurance Fund':'NCUA Budget & Insurance','Technology & Emerging Issues':'Technology & Emerging',
 'Telephone Consumer Protection Act Issues':'TCPA'}
SECTION_KEYWORDS = (('Examination & Supervision','examination'),('CU Capital Requirements','capital'),
 ('NCUA Budget & Insurance','ncua'),('Interchange','interchange'),('Payments','payments'),
 ('Technology & Emerging','technology'),('Fraud Prevention','fraud'),('Data Privacy & Cyber','data privacy'),
 ('Charter Modernization','charter'),('Defense CU Issues','defense'),('Field of Membership','field of membership'),
 ('CU Tax Status','tax status'),('CDFI Fund','cdfi'),('CFPB','cfpb'),('Credit Card Mandates','credit card'),
 ('TCPA','telephone'),('Member Business Lending','member business'),('Mortgage & Housing','mortgage'))

def canonical_category(value):                             # :110-122
    raw = str(value or '').strip()
    if not raw: return None
    if raw in CATEGORIES: return raw
    if raw in LABEL_TO_CANONICAL: return LABEL_TO_CANONICAL[raw]
    low = raw.lower()
    for cat, kw in SECTION_KEYWORDS:
        if kw in low: return cat
    return None

def congress_decay(c, current=119):                        # :190-198
    return round(0.8 ** max(0, current - int(float(c))), 12)

# --------------------------------------------------------------------------- loaders
def xl_rows(path, sheet):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[sheet]
    it = ws.iter_rows(values_only=True)
    hdr = [str(h) if h is not None else '' for h in next(it)]
    out = [dict(zip(hdr, r)) for r in it]
    wb.close()
    return out

ARCH = xl_rows(P(ARCHIVE_SELECTED), 'All Bills')
PRIOR = xl_rows(P(ARCHIVE_PRIOR), 'All Bills')
ROLE_SHEETS = {}
wbm = openpyxl.load_workbook(P('Moneyball Main Version - Blended.xlsx'), read_only=True, data_only=True)
for sn in ('Sponsor Interactions','Original Co-Sponsor Interaction','Co-Sponsor Interactions',
           'Success Sponsor','Success Original Co-Sponsor'):
    ws = wbm[sn]; it = ws.iter_rows(values_only=True)
    hdr = [str(h) if h is not None else '' for h in next(it)]
    ROLE_SHEETS[sn] = [dict(zip(hdr, r)) for r in it]
wbm.close()
SENT = xl_rows(P('Sentinel Bill Ledger.xlsx'), 'Sentinel Bill Ledger')
def sent_eligible(r):
    t = lambda k: str(r.get(k) or '').strip().lower()
    return t('Scoring Eligible') in {'true','1','yes'} and t('Review Status') == 'verified' and t('Record Type') == 'membership'
SENT_OK = [r for r in SENT if sent_eligible(r)]
with open(P('manual_bill_evidence.csv'), encoding='utf-8-sig', newline='') as fh:
    MANUAL = list(csv.DictReader(fh))
with open(P('data','legislation','bill_directions.csv'), encoding='utf-8-sig', newline='') as fh:
    DIRS = list(csv.DictReader(fh))
with open(P('data','legislation','bill_overrides.csv'), encoding='utf-8-sig', newline='') as fh:
    OVR = list(csv.DictReader(fh))
with open(P('legislation_routing_audit.json'), encoding='utf-8') as fh:
    RA = json.load(fh)
with open(P('archive_leg.json'), encoding='utf-8') as fh:
    LEG = json.load(fh)

print("LOADED: archive(selected) %d  archive(prior) %d  sentinel %d (verified-eligible %d)  manual %d  "
      "bill_directions %d  bill_overrides %d  routing rows %d  archive_leg members %d"
      % (len(ARCH), len(PRIOR), len(SENT), len(SENT_OK), len(MANUAL), len(DIRS), len(OVR),
         len(RA['rows']), len(LEG)))
print("routing audit 'source' field: %r ; source_rows=%s" % (RA.get('source'), RA.get('source_rows')))
print("reconstruction check: archive %d + sentinel_verified %d + manual %d = %d  (== source_rows? %s)"
      % (len(ARCH), len(SENT_OK), len(MANUAL), len(ARCH)+len(SENT_OK)+len(MANUAL),
         len(ARCH)+len(SENT_OK)+len(MANUAL) == RA.get('source_rows')))

# =========================================================================== Q2
print("\n" + "=" * 100)
print("Q2  BILL-UNIVERSE FORK -- Tim Scott, Member Business Lending, sponsor rows")
print("=" * 100)
print("\nArchive SELECTION code, live producer fec/legislation/build_archive_legislative.py:50")
print(r"  A=pd.read_excel(sorted(glob.glob(MB_ROOT+r'\congress_bills_archive_*.xlsx'))[-1],sheet_name='All Bills')")
print("  -> %s" % ARCHIVE_SELECTED)

def mbl(sec):  return canonical_category(sec) == 'Member Business Lending'
def is_scott(m): return str(m or '').strip().lower() in ('tim scott', 'timothy scott', 'scott, tim')

def show(rows, label, keymap):
    sel = [r for r in rows if is_scott(r.get(keymap['member'])) and mbl(r.get(keymap['section']))]
    spon = [r for r in sel if canonical_role(r.get(keymap['role'])) == 'sponsor']
    tot = 0.0
    print("\n  %s : Tim Scott x MBL rows=%d  (sponsor-role rows=%d)" % (label, len(sel), len(spon)))
    for r in sorted(sel, key=lambda r: str(r.get(keymap['bill']))):
        cg = _congress(r.get(keymap['congress']))
        role = canonical_role(r.get(keymap['role']))
        dwraw = r.get(keymap['decay'])
        try: dw = float(dwraw)
        except (TypeError, ValueError): dw = congress_decay(cg) if cg.isdigit() else 1.0
        w = role_weight(role) * dw
        if role == 'sponsor': tot += w
        print("     %-14s C=%-4s role=%-18s dw=%-20s w=%6.3f  action=%-22s title=%s"
              % (r.get(keymap['bill']), cg, role, dwraw, w,
                 str(r.get(keymap.get('action')) or '')[:22], str(r.get(keymap['title']) or '')[:44]))
    print("     -> signed sponsor-role weight (sign=+1 assumed for MBL section default) = %.2f" % tot)
    return sel, spon, tot

KM_ARCH = {'member':'Member','section':'Section','role':'Role','bill':'Name','congress':'Congress',
           'decay':'DecayWeight','title':'Title','action':'LastAction'}
KM_SENT = {'member':'Member','section':'Section','role':'Role','bill':'Bill','congress':'Congress',
           'decay':'DecayWeight','title':'Title','action':'Latest Action'}
KM_MAN  = {'member':'Member','section':'Category','role':'Role','bill':'Bill','congress':'Congress',
           'decay':'DecayWeight','title':'Title','action':'LastAction'}

print("\n(a) WORKBOOK ROLE SHEETS  (Moneyball Main Version - Blended.xlsx)")
wb_all = []
for sn, rows in ROLE_SHEETS.items():
    s, sp, t = show(rows, "workbook['%s']" % sn, KM_ARCH)
    wb_all += s
print("\n(b) SELECTED ARCHIVE  (%s, sheet 'All Bills')" % ARCHIVE_SELECTED)
a_sel, a_spon, a_tot = show(ARCH, "archive SELECTED", KM_ARCH)
print("\n(b') PRIOR ARCHIVE  (%s, sheet 'All Bills') -- context only" % ARCHIVE_PRIOR)
p_sel, p_spon, p_tot = show(PRIOR, "archive PRIOR", KM_ARCH)
print("\n(b'') SENTINEL BILL LEDGER verified+eligible rows")
s_sel, s_spon, s_tot = show(SENT_OK, "sentinel verified", KM_SENT)
print("\n(b''') manual_bill_evidence.csv")
m_sel, m_spon, m_tot = show(MANUAL, "manual csv", KM_MAN)

print("\n(c) archive_leg.json + legislation_routing_audit.json for Tim Scott")
print("    archive_leg.json['Tim Scott'] =")
for c, v in sorted((LEG.get('Tim Scott') or {}).items(), key=lambda kv: -abs(kv[1])):
    print("       %-30s %+.4f" % (c, v))
scott_rows = [r for r in RA['rows'] if r.get('member') == 'Tim Scott' or is_scott(r.get('member_source'))]
scott_mbl = [r for r in scott_rows if (r.get('effective_category') == 'Member Business Lending'
                                      or mbl(r.get('source_section')))]
print("    routing-audit rows for Tim Scott: total=%d ; MBL-related=%d" % (len(scott_rows), len(scott_mbl)))
print("    MBL rows by disposition:", dict(collections.Counter(r['disposition'] for r in scott_mbl)))
print("    MBL SELECTED rows:")
for r in sorted([r for r in scott_mbl if r['disposition'] == 'selected'], key=lambda r: str(r.get('bill'))):
    print("       %-14s C=%-4s role=%-18s sign=%+d dw=%-6s contrib=%+7.3f mech=%s" % (
        r.get('bill'), _congress(r.get('congress')), r.get('effective_role'), r.get('sign'),
        r.get('decay_weight'), r.get('contribution'), r.get('direction_mechanism')))
print("    MBL NON-selected rows:")
for r in sorted([r for r in scott_mbl if r['disposition'] != 'selected'], key=lambda r: str(r.get('bill'))):
    print("       %-14s C=%-4s src_role=%-18s disp=%-52s reason=%s" % (
        r.get('bill'), _congress(r.get('congress')), r.get('source_role'), r.get('disposition'),
        r.get('reason') or r.get('override_reason') or ''))

print("\n(d) manual_bill_evidence.csv PATH IN CODE (live build_archive_legislative.py:91):")
print(r"      _manual_path=MB_ROOT+r'\manual_bill_evidence.csv'")
print("    exists at that path? %s   rows=%d" % (os.path.exists(P('manual_bill_evidence.csv')), len(MANUAL)))
print("    other manual_bill_evidence.csv copies under the live root (non-recursive + data/legislation):")
for cand in (P('manual_bill_evidence.csv'), P('data','legislation','manual_bill_evidence.csv'),
             P('data','manual_bill_evidence.csv'), P('backups','manual_bill_evidence.csv')):
    print("       %-72s %s" % (cand.replace(ROOT, '<ROOT>'), 'PRESENT' if os.path.exists(cand) else 'absent'))
print("    manual rows by Category:")
for k, v in sorted(collections.Counter(r['Category'] for r in MANUAL).items(), key=lambda kv: -kv[1]):
    print("       %-34s %d" % (k, v))
print("    manual rows by Role:", dict(collections.Counter(canonical_role(r['Role']) for r in MANUAL)))
_ltr = [r for r in MANUAL if str(r['Bill']).upper().startswith('LTR-')]
print("    LTR- rows=%d  distinct letters=%d  distinct members=%d   (gate floor 296/7/251, live code:285)"
      % (len(_ltr), len({r['Bill'] for r in _ltr}), len({r['Member'] for r in _ltr})))
print("    non-LTR manual rows (%d):" % (len(MANUAL) - len(_ltr)))
for r in [r for r in MANUAL if not str(r['Bill']).upper().startswith('LTR-')]:
    print("       %-14s C=%-4s %-26s role=%-18s dir=%-4s member=%s" % (
        r['Bill'], r['Congress'], r['Category'], canonical_role(r['Role']), r['Direction'], r['Member']))

# =========================================================================== Q3
print("\n" + "=" * 100)
print("Q3  PLACEMENT FACTS")
print("=" * 100)
TARGETS = [('S.869', '118'), ('H.R.7733', '117'), ('H.J.Res.59', '119'), ('S.J.Res.18', '119'),
           ('H.R.3009', '117')]
def norm(b): return re.sub(r'\s+', '', str(b or '')).upper()
for bill, cong in TARGETS:
    print("\n---- %s (%sth) ----" % (bill, cong))
    print("   bill_key=%s   bill_type_key=%s" % (bill_key(bill), bill_type_key(bill)))
    for label, rows, km in (("archive SELECTED", ARCH, KM_ARCH), ("archive PRIOR", PRIOR, KM_ARCH),
                            ("sentinel verified", SENT_OK, KM_SENT), ("manual csv", MANUAL, KM_MAN)):
        hit = [r for r in rows if norm(r.get(km['bill'])) == norm(bill) and _congress(r.get(km['congress'])) == cong]
        secs = collections.Counter(str(r.get(km['section'])) for r in hit)
        roles = collections.Counter(canonical_role(r.get(km['role'])) for r in hit)
        print("   %-18s rows=%-5d sections=%s roles=%s" % (label, len(hit), dict(secs), dict(roles)))
        if hit:
            print("        title=%r  latest_action=%r" % (str(hit[0].get(km['title']))[:70],
                                                          str(hit[0].get(km.get('action')))[:50]))
    for sn, rows in ROLE_SHEETS.items():
        hit = [r for r in rows if norm(r.get('Name')) == norm(bill) and _congress(r.get('Congress')) == cong]
        if hit:
            print("   workbook[%-32s] rows=%-5d sections=%s roles=%s" % (
                sn, len(hit), dict(collections.Counter(str(r.get('Section')) for r in hit)),
                dict(collections.Counter(canonical_role(r.get('Role')) for r in hit))))
    d = [r for r in DIRS if norm(r['Bill']) == norm(bill)]
    print("   bill_directions.csv rows: %s" % (d or 'NONE'))
    o = [r for r in OVR if norm(r['Bill']) == norm(bill)]
    print("   bill_overrides.csv rows : %s" % (o or 'NONE'))
    rr = [r for r in RA['rows'] if norm(r.get('bill')) == norm(bill) and _congress(r.get('congress')) == cong]
    print("   routing-audit rows=%d" % len(rr))
    print("      dispositions      :", dict(collections.Counter(r['disposition'] for r in rr)))
    print("      effective_category:", dict(collections.Counter(str(r.get('effective_category')) for r in rr)))
    print("      category_mechanism:", dict(collections.Counter(str(r.get('category_mechanism')) for r in rr)))
    print("      direction sign    :", dict(collections.Counter(str(r.get('sign')) for r in rr)))
    print("      direction_mech    :", dict(collections.Counter(str(r.get('direction_mechanism')) for r in rr)))
    print("      source_section    :", dict(collections.Counter(str(r.get('source_section')) for r in rr)))
    sel = [r for r in rr if r['disposition'] == 'selected']
    print("      SELECTED rows=%d  signed contribution total=%+.3f  distinct members=%d"
          % (len(sel), sum(r['contribution'] for r in sel), len({r['member'] for r in sel})))

print("\n---- 'CDFI Fund' legislative evidence today ----")
cdfi_sel = [r for r in RA['rows'] if r.get('effective_category') == 'CDFI Fund' and r['disposition'] == 'selected']
print("   routing-audit SELECTED rows with effective_category='CDFI Fund': %d" % len(cdfi_sel))
print("   distinct members: %d   distinct bills/measures: %d" % (
    len({r['member'] for r in cdfi_sel}), len({norm(r['bill']) for r in cdfi_sel})))
print("   signed contribution total: %+.2f" % sum(r['contribution'] for r in cdfi_sel))
print("   archive_leg.json members carrying a 'CDFI Fund' entry: %d ; signed sum %+.2f" % (
    sum(1 for d in LEG.values() if 'CDFI Fund' in d), sum(d.get('CDFI Fund', 0) for d in LEG.values())))
print("   CDFI evidence by measure identifier (top 20 by row count):")
for b, n in collections.Counter(norm(r['bill']) for r in cdfi_sel).most_common(20):
    print("      %-30s rows=%-5d LTR? %s" % (b, n, b.startswith('LTR-')))
print("   CDFI rows whose identifier is a LTR- letter: %d ; formal bills: %d" % (
    sum(1 for r in cdfi_sel if norm(r['bill']).startswith('LTR-')),
    sum(1 for r in cdfi_sel if not norm(r['bill']).startswith('LTR-'))))
print("   CDFI rows by category_mechanism:", dict(collections.Counter(str(r.get('category_mechanism')) for r in cdfi_sel)))
print("   'CDFI Fund' sheet row count in PRIOR archive workbook (July baseline): see q0_schema_probe.txt")

# =========================================================================== Q4
print("\n" + "=" * 100)
print("Q4  bill_key() TYPE-BLINDNESS -- collision census")
print("=" * 100)
def universe(rows, bill_field, cong_field, tag):
    out = []
    for r in rows:
        b = r.get(bill_field)
        if b is None or str(b).strip() == '':
            continue
        out.append((str(b).strip(), _congress(r.get(cong_field)), tag))
    return out

UNI_ARCH = universe(ARCH, 'Name', 'Congress', 'archive')
UNI_DIRS = universe(DIRS, 'Bill', 'Congress', 'bill_directions')
UNI_SENT = universe(SENT_OK, 'Bill', 'Congress', 'sentinel')
UNI_MAN  = universe(MANUAL, 'Bill', 'Congress', 'manual')
UNI_OVR  = universe(OVR, 'Bill', 'Congress', 'bill_overrides')

DIR_TYPEKEYS = {(bill_type_key(r['Bill']), _congress(r['Congress'])) for r in DIRS if bill_type_key(r['Bill'])}
DIR_LEGACYKEYS = {bill_key(r['Bill']) for r in DIRS if bill_key(r['Bill'])}
OVR_LEGACYKEYS = {(bill_key(r['Bill']), _congress(r['Congress'])) for r in OVR if bill_key(r['Bill'])}
BUILTIN = {(('H',7733),'117'), (('S',869),'118'), (('H',7036),'118'), (('H',7022),'117'), (('S',4698),'117')}
EXCLUDED_PINS = {(('H',3664),'117'), (('H',1707),'118')}

def collisions(pairs, within_congress):
    """pairs: [(identifier, congress, tag)] -> {group_key: {type_token: {(ident,congress,tag)}}}"""
    groups = collections.defaultdict(lambda: collections.defaultdict(set))
    for ident, cong, tag in pairs:
        lk = bill_key(ident)
        tk = bill_type_key(ident)
        if lk is None:
            continue
        gk = (lk, cong) if within_congress else lk
        groups[gk][tk[1] if tk else '?'].add((ident, cong, tag))
    return {g: t for g, t in groups.items() if len(t) > 1}

for scope_name, pairs in (("archive(selected) + bill_directions.csv", UNI_ARCH + UNI_DIRS),
                          ("archive + sentinel + manual + bill_directions + bill_overrides  (full producer frame)",
                           UNI_ARCH + UNI_SENT + UNI_MAN + UNI_DIRS + UNI_OVR)):
    print("\n-- scope: %s" % scope_name)
    print("   identifiers considered = %d ; distinct bill_key groups = %d"
          % (len(pairs), len({bill_key(i) for i, c, t in pairs if bill_key(i)})))
    for within, lbl in ((True, "WITHIN the same Congress"), (False, "ACROSS Congresses (Congress ignored)")):
        col = collisions(pairs, within)
        print("\n   [%s] collision groups = %d" % (lbl, len(col)))
        n_with_dir = 0
        listing = []
        for gk, types in sorted(col.items(), key=lambda kv: str(kv[0])):
            members_ = sorted({(i, c) for s in types.values() for i, c, t in s})
            tags = sorted({t for s in types.values() for i, c, t in s})
            has_dir = any(bill_key(i) in DIR_LEGACYKEYS and
                          (bill_type_key(i), c) in DIR_TYPEKEYS or
                          any(norm(i) == norm(d['Bill']) for d in DIRS)
                          for i, c in members_)
            # a direction row exists for AT LEAST ONE member of the group (legacy key match)
            dir_members = [(i, c) for i, c in members_ if any(norm(i) == norm(d['Bill']) for d in DIRS)]
            ovr_members = [(i, c) for i, c in members_ if any(norm(i) == norm(o['Bill']) for o in OVR)]
            builtin_members = [(i, c) for i, c in members_ if (bill_key(i), c) in BUILTIN]
            excl_members = [(i, c) for i, c in members_ if (bill_key(i), c) in EXCLUDED_PINS]
            if dir_members: n_with_dir += 1
            listing.append((gk, types, members_, tags, dir_members, ovr_members, builtin_members, excl_members))
        print("   groups containing >=1 bill that HAS a bill_directions.csv row = %d" % n_with_dir)
        if within:
            print("   full listing (within-Congress groups):")
            for gk, types, members_, tags, dm, om, bm, em in listing:
                print("      key=%s  types=%s" % (gk, sorted(types)))
                for i, c in members_:
                    src = sorted({t for s in types.values() for ii, cc, t in s if ii == i and cc == c})
                    print("         %-16s C=%-5s type=%-4s sources=%s%s%s%s%s" % (
                        i, c, (bill_type_key(i) or ('?','?','?'))[1], src,
                        "  [bill_directions row]" if (i, c) in dm else "",
                        "  [bill_overrides row]" if (i, c) in om else "",
                        "  [BUILTIN_OVERRIDES]" if (i, c) in bm else "",
                        "  [EXCLUDED_BILL_CONGRESSES]" if (i, c) in em else ""))
        else:
            print("   groups (across-Congress) whose members carry a directions/overrides/builtin/excluded key:")
            for gk, types, members_, tags, dm, om, bm, em in listing:
                if dm or om or bm or em:
                    print("      key=%s types=%s members=%s dir=%s ovr=%s builtin=%s excl=%s"
                          % (gk, sorted(types), members_, dm, om, bm, em))

print("\n-- does bill_directions.csv ITSELF hold type-colliding rows? --")
dc = collisions(UNI_DIRS, True)
print("   within-Congress collisions inside bill_directions.csv: %d %s" % (len(dc), sorted(dc) if dc else ''))
dc2 = collisions(UNI_DIRS, False)
print("   across-Congress collisions inside bill_directions.csv: %d %s" % (len(dc2), sorted(dc2) if dc2 else ''))
print("\n-- does bill_overrides.csv / BUILTIN / EXCLUDED collide with a real archive bill? --")
arch_legacy = collections.defaultdict(set)
for i, c, t in UNI_ARCH + UNI_SENT + UNI_MAN:
    lk = bill_key(i)
    if lk: arch_legacy[(lk, c)].add((i, (bill_type_key(i) or ('?','?','?'))[1]))
for lbl, keys in (('bill_overrides.csv', OVR_LEGACYKEYS), ('BUILTIN_OVERRIDES', BUILTIN),
                  ('EXCLUDED_BILL_CONGRESSES', EXCLUDED_PINS)):
    print("   %s -- %d keys" % (lbl, len(keys)))
    for k in sorted(keys, key=str):
        hits = arch_legacy.get(k, set())
        types = sorted({t for _, t in hits})
        flag = 'MULTI-TYPE MATCH' if len(types) > 1 else ('single type' if types else 'no archive match')
        print("      key=%-22s matches %d archive identifiers, types=%s  -> %s" % (str(k), len(hits), types, flag))
        if len(types) > 1:
            for i, t in sorted(hits):
                print("            %-16s type=%s" % (i, t))

# =========================================================================== Q5
print("\n" + "=" * 100)
print("Q5  REGISTRY-DIRECTION PARSE")
print("=" * 100)
print("source: data\\legislation\\bill_directions.csv , column 'Direction'")
print("  loaded by live build_archive_legislative.py:118-124 ->")
print("     direction=(row.get('Direction') or '').strip()")
print("  consumed at live build_archive_legislative.py:233 ->")
print("     sign={'1':1,'-1':-1}.get(registry_direction,0)")
lit = collections.Counter((r.get('Direction') or '') for r in DIRS)
print("\n  literal Direction values present (n=%d rows):" % len(DIRS))
for v, n in sorted(lit.items(), key=lambda kv: -kv[1]):
    mapped = {'1': 1, '-1': -1}.get(v.strip(), 0)
    print("     %-8r rows=%-5d -> sign=%+d %s" % (v, n, mapped,
          "" if v.strip() in ('1', '-1') else "  <-- NOT '1'/'-1' : silently neutralised"))
bad = [r for r in DIRS if (r.get('Direction') or '').strip() not in ('1', '-1')]
print("\n  rows whose literal is NOT '1'/'-1' (would be forced to sign=0): %d" % len(bad))
for r in bad:
    print("     %s" % r)
plus = [r for r in DIRS if (r.get('Direction') or '').strip() == '+1']
print("  rows carrying literal '+1': %d" % len(plus))
print("\n  ALSO: which of these registry rows actually reach a live row? (routing audit mechanism counts)")
mech = collections.Counter(str(r.get('direction_mechanism')) for r in RA['rows'])
print("     direction_mechanism over all %d routing rows: %s" % (len(RA['rows']), dict(mech)))
print("     rows disposed 'neutral-registry': %d" % sum(1 for r in RA['rows'] if r['disposition'] == 'neutral-registry'))
nr = [r for r in RA['rows'] if r['disposition'] == 'neutral-registry']
print("     their bills:", sorted({(norm(r['bill']), _congress(r['congress'])) for r in nr}))
print("\n  CROSS-CHECK: manual_bill_evidence.csv 'Direction' literals (a DIFFERENT parser, parse_direction float()):")
mlit = collections.Counter((r.get('Direction') or '') for r in MANUAL)
for v, n in sorted(mlit.items(), key=lambda kv: -kv[1]):
    try: f = float(v.strip()); m = int(f) if f in (-1.0, 0.0, 1.0) else 0
    except ValueError: m = 0
    print("     %-8r rows=%-5d -> parse_direction=%+d" % (v, n, m))
print("  CROSS-CHECK: bill_overrides.csv 'Direction' literals (parse_direction too):")
olit = collections.Counter((r.get('Direction') or '') for r in OVR)
for v, n in sorted(olit.items(), key=lambda kv: -kv[1]):
    print("     %-8r rows=%d" % (v, n))

# =========================================================================== Q6
print("\n" + "=" * 100)
print("Q6  ORIGINAL-COSPONSOR TWINS")
print("=" * 100)
sel = [r for r in RA['rows'] if r['disposition'] == 'selected']
print("selected rows = %d ; routing-audit selected_events = %s" % (len(sel), RA.get('selected_events')))
print("dedup key in producer (live build_archive_legislative.py:251):")
print("   event_key=(mm,str(r.get('Name') or '').strip().lower(),BR._congress(r.get('Congress')),cat)")
by_mbc = collections.Counter((r['member'], norm(r['bill']), _congress(r['congress'])) for r in sel)
dupe_mbc = {k: v for k, v in by_mbc.items() if v > 1}
print("\n(member, bill, Congress) combinations contributing MORE THAN ONCE : %d" % len(dupe_mbc))
print("   total extra contributions from them: %d" % sum(v - 1 for v in dupe_mbc.values()))
by_mbcc = collections.Counter((r['member'], norm(r['bill']), _congress(r['congress']), r['effective_category'])
                              for r in sel)
dupe_mbcc = {k: v for k, v in by_mbcc.items() if v > 1}
print("(member, bill, Congress, effective_category) combinations contributing more than once : %d" % len(dupe_mbcc))
print("   (this is the producer's own event key -- >0 would mean the collapse FAILED)")
if dupe_mbcc:
    for k, v in list(dupe_mbcc.items())[:20]:
        print("      %s  x%d" % (k, v))
print("\nrole mix inside multi-category (member,bill,Congress) groups (first 25):")
groups = collections.defaultdict(list)
for r in sel:
    groups[(r['member'], norm(r['bill']), _congress(r['congress']))].append(r)
multi = [(k, v) for k, v in groups.items() if len(v) > 1]
print("   distinct such groups = %d" % len(multi))
catpairs = collections.Counter(tuple(sorted({x['effective_category'] for x in v})) for k, v in multi)
print("   category sets involved:")
for cp, n in catpairs.most_common():
    print("      %-70s groups=%d" % (str(cp), n))
rolesets = collections.Counter(tuple(sorted({x['effective_role'] for x in v})) for k, v in multi)
print("   role sets involved:", dict(rolesets))
for k, v in multi[:25]:
    print("      %-26s %-14s C=%-4s -> %s" % (k[0][:26], k[1], k[2],
          [(x['effective_category'], x['effective_role'], x['contribution']) for x in v]))
print("\nduplicate dispositions recorded by the producer: %s" % RA['summary']['duplicates'])
oc = [r for r in RA['rows'] if r['disposition'] in ('duplicate-lower-role', 'duplicate-same-role')]
print("   rows suppressed as duplicates: %d ; their source roles: %s" % (
    len(oc), dict(collections.Counter(canonical_role(r.get('source_role')) for r in oc))))

print("\nCONSISTENCY CHECK: sum(selected contributions) per (member,category) == archive_leg.json?")
rebuilt = collections.defaultdict(float)
for r in sel:
    rebuilt[(r['member'], r['effective_category'])] += r['contribution']
mismatch = []
for (m, c), v in rebuilt.items():
    lv = (LEG.get(m) or {}).get(c)
    if lv is None or abs(lv - v) > 1e-9:
        mismatch.append((m, c, v, lv))
print("   rebuilt cells=%d ; archive_leg cells=%d ; mismatches=%d"
      % (len(rebuilt), sum(len(d) for d in LEG.values()), len(mismatch)))
for row in mismatch[:15]:
    print("      MISMATCH", row)
