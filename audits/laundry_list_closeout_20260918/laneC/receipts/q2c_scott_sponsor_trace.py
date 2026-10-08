# Lane C / Q2c : per-row trace of the five workbook Tim Scott MBL sponsor rows. READ-ONLY.
import openpyxl, os, json, re, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
R = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems"
norm = lambda b: re.sub(r'\s+', '', str(b or '')).upper()
def xl(p, s):
    wb = openpyxl.load_workbook(os.path.join(R, p), read_only=True, data_only=True)
    ws = wb[s]; it = ws.iter_rows(values_only=True)
    h = [str(x) if x is not None else '' for x in next(it)]
    o = [dict(zip(h, r)) for r in it]; wb.close(); return o

A = xl('congress_bills_archive_20260825_115305.xlsx', 'All Bills')
SENT = [r for r in xl('Sentinel Bill Ledger.xlsx', 'Sentinel Bill Ledger')
        if str(r.get('Scoring Eligible') or '').strip().lower() in {'true', '1', 'yes'}
        and str(r.get('Review Status') or '').strip().lower() == 'verified'
        and str(r.get('Record Type') or '').strip().lower() == 'membership']
WB = {sn: xl('Moneyball Main Version - Blended.xlsx', sn)
      for sn in ('Sponsor Interactions', 'Original Co-Sponsor Interaction', 'Co-Sponsor Interactions')}
RA = json.load(open(os.path.join(R, 'legislation_routing_audit.json'), encoding='utf-8'))
LEG = json.load(open(os.path.join(R, 'archive_leg.json'), encoding='utf-8'))

print("=" * 100)
print("Q2c  the FIVE workbook 'Sponsor Interactions' Tim Scott x Member Business Lending rows, traced")
print("=" * 100)
FIVE = [('S.2486', '119', 1.0), ('S.3382', '117', 0.64), ('S.3992', '118', 0.8),
        ('S.762', '117', 0.64), ('S.J.Res.18', '119', 1.0)]
total = 0.0
for bill, cong, dw in FIVE:
    w = 3.0 * dw
    total += w
    print("\n-- %s (%sth)  sponsor role_weight 3.0 x decay %.2f = %.2f signed weight" % (bill, cong, dw, w))
    print("   workbook['Sponsor Interactions'] sections for Tim Scott: %s"
          % sorted(r['Section'] for r in WB['Sponsor Interactions']
                   if norm(r['Name']) == norm(bill) and str(r['Member']).strip() == 'Tim Scott'))
    ab = [r for r in A if norm(r['Name']) == norm(bill)]
    ats = [r for r in ab if str(r['Member']).strip() == 'Tim Scott']
    print("   selected archive: rows for this bill = %d ; roles present = %s ; sections = %s"
          % (len(ab), sorted({r['Role'] for r in ab}), sorted({r['Section'] for r in ab})))
    print("   selected archive: Tim Scott rows = %s"
          % [(r['Section'], r['Role']) for r in ats])
    print("   sentinel verified: Tim Scott rows = %s"
          % [(r['Section'], r['Role']) for r in SENT
             if norm(r['Bill']) == norm(bill) and str(r['Member']).strip() == 'Tim Scott'])
    rr = [r for r in RA['rows'] if norm(r.get('bill')) == norm(bill)
          and (r.get('member') == 'Tim Scott' or str(r.get('member_source')).strip() == 'Tim Scott')]
    print("   routing audit: %s" % [(r.get('source_section'), r.get('source_role'),
                                     r.get('effective_category'), r['disposition'],
                                     r.get('contribution')) for r in rr])
print("\n   workbook sponsor-row total signed weight = %.2f   (July finding: 12.24)" % total)
print("\n-- what the stance matrix actually holds --")
print("   archive_leg.json['Tim Scott']['Member Business Lending'] = %.4f" % LEG['Tim Scott']['Member Business Lending'])
sel = [r for r in RA['rows'] if r['disposition'] == 'selected' and r.get('member') == 'Tim Scott'
       and r.get('effective_category') == 'Member Business Lending']
print("   sum of Tim Scott MBL 'selected' routing contributions = %.4f across %d rows"
      % (sum(r['contribution'] for r in sel), len(sel)))
for r in sorted(sel, key=lambda r: str(r['bill'])):
    print("      %-14s C=%-4s %-20s %+.3f" % (r['bill'], r['congress'], r['effective_role'], r['contribution']))
print("   archive_leg.json['Tim Scott']['CFPB'] = %.4f  (S.J.Res.18's +3.00 lands here via bill_overrides.csv)"
      % LEG['Tim Scott']['CFPB'])
