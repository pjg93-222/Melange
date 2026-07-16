# -*- coding: utf-8 -*-
import os as _o,sys as _s;_s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__)));from paths import ROOT as MB_ROOT  # centralized root
"""EXTRACT — API-FREE foundation for the broadcast/podcast INTERVIEW CU-stance channel (2026-07-15).

Reads attributed interview transcripts out of social_media.db (READ-ONLY) and emits
interviews_cu.csv: the subset where the attributed speaker (the member's OWN words) mentions a
CU / CFPB / interchange topic, keyed to a bioguide and routed to the shared media categories.
This is an INPUT-ONLY artifact — nothing here is wired into the pipeline, no network, no API, no spend.

Mirrors extract_cu_speeches.py exactly (same helpers, same fixes, same routing); only the source
filter and output name differ.  Resolution and routing reuse the project's shared modules so this
channel speaks the same member + category vocabulary as every other producer:
  * member -> bioguide via member_identity.Resolver (fail-closed: unresolved rows are dropped)
  * text   -> category via media_rules.route_raw_categories(text, declared=[])  (drop if none)
"""
import sys, os, sqlite3, csv, json, collections, re, hashlib
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import media_rules as MR
from member_identity import Resolver

DB      = os.path.join(MB_ROOT, 'social_media.db')
ROSTER  = os.path.join(MB_ROOT, 'congestion.json')
OUT     = os.path.join(MB_ROOT, 'interviews_cu.csv')
TEXTCAP = 4000
# The CU-relevant INTERVIEW subset is tiny (<250 rows across the whole corpus). Unlike the CREC
# floor channel — whose 104k rows justify a 2023 recency gate — this channel LABELS THE FULL modern-era
# set, so MINDATE is a permissive floor (earliest CU interview is 2011-11-10) kept only for structure
# and to guard against any null/blank date. It admits every CU-relevant interview row (task: no down-sampling).
MINDATE = '2009-01-01'

# Topic keywords (full-text substring match, case-insensitive) — the CU/CFPB relevance gate.
# C1 (2026-07-15, Paul-directed): the INTERVIEW gate is BROADENED beyond the shared speech list to
# lift coverage (agency-name variants, CFPB director 'chopra', bare 'durbin', payday/medical-debt/
# consumer-bureau) — accepting more noise that hand labeling + the narrator/interchange/keyword-in-
# stored guards trim.
KEYWORDS = ['cfpb', 'consumer financial protection', 'financial protection', 'consumer bureau',
            'credit union', 'interchange', 'swipe fee', 'credit card competition', 'ncua',
            'durbin', 'durbin amendment', 'field of membership', 'member business lending',
            'overdraft', 'junk fee', 'chopra', 'payday', 'medical debt']

# ---- roster: canonical member names + name->bioguide, from congestion.json ----
_roster = json.load(open(ROSTER, encoding='utf-8'))
NAME2BIO = {x['member']: x.get('bioguide') for x in _roster}
resolver = Resolver([x['member'] for x in _roster], NAME2BIO)

# ---- pull the topic subset, READ-ONLY ----
con = sqlite3.connect('file:' + DB + '?mode=ro', uri=True)
cur = con.cursor()
where = ' OR '.join(['lower(text) LIKE ?'] * len(KEYWORDS))
params = ['%' + k + '%' for k in KEYWORDS]
# BUG-B fix: this channel is INTERVIEW ONLY. CREC (floor speeches) and CHRG (hearings) are SEPARATE
# channels (extract_cu_speeches.py handles CREC; CHRG stays under its speaker-verified quarantine);
# the source filter pins to INTERVIEW so the streams never cross-contaminate. The stored 'member' is
# the collector's attributed speaker (nickname/rank-scoped surname pools) — resolved fail-closed anyway.
# BUG-D fix: deterministic ORDER BY (never rely on SQLite scan order).
q = ('select member,date,source,chamber,package,nwords,text from speeches '
     'where date >= ? and source = ? and (' + where + ') '
     'order by date, member, package, nwords, substr(text,1,120)')
rows = cur.execute(q, [MINDATE, 'INTERVIEW'] + params).fetchall()
con.close()

total = len(rows)
kept = drop_unresolved = drop_nocat = drop_dup = drop_insert = drop_offtopic = drop_durbin = 0
members = set()
catdist = collections.Counter()
out_rows = []
seen = set()
# BUG-E: non-spoken "printed in the Record" insertions are not the member's own stance -> drop.
# (A CREC-inherited guard; it effectively never fires on interview transcripts but is retained for
# structural parity and to keep the drop accounting identical across channels.)
INSERT_RX = re.compile(r'unanimous consent.{0,80}(printed in the (record|congressional record)|inserted?)', re.I)
# F3 interchange precision: bare 'interchange' also matches HIGHWAY interchanges / 'interchangeable' /
# 'interchanges between staff'. If a row's ONLY CU keyword is 'interchange' and no occurrence sits near
# a payment-interchange context, it is off-topic -> drop (audit MED: ~7/41 interview FPs, a few hearing).
_FINCTX_RX = re.compile(r'swipe|debit|credit card|merchant|durbin|payment|transaction fee|visa|mastercard|interchange fee|network fee')
_OTHER_KWS = [k for k in KEYWORDS if k != 'interchange']
def _interchange_only_offtopic(tl):
    if any(k in tl for k in _OTHER_KWS):
        return False                      # a non-interchange CU keyword is present -> genuinely relevant
    idxs = [m.start() for m in re.finditer('interchange', tl)]
    if not idxs:
        return False                      # not an interchange-driven match at all
    return not any(_FINCTX_RX.search(tl[max(0, i - 60):i + 70]) for i in idxs)
# Durbin precision (Paul 2026-07-15): the broadened interview gate added bare 'durbin', which matches
# Senator Durbin in ANY context. Keep a durbin-driven row ONLY when it is the Durbin AMENDMENT or Durbin
# speaking in a credit-union / interchange context; drop bare Senator-Durbin mentions unrelated to CUs.
_DURBIN_CTX_RX = re.compile(r'interchange|swipe|debit|credit union|credit card|merchant|dodd.?frank|routing number|card fee|transaction fee|network fee|cfpb|consumer financial protection|financial protection|overdraft')
_OTHER_KWS_ND = [k for k in KEYWORDS if k not in ('durbin', 'durbin amendment')]
def _durbin_only_offtopic(tl):
    if 'durbin amendment' in tl:
        return False                       # explicit amendment -> keep
    if any(k in tl for k in _OTHER_KWS_ND):
        return False                       # another real CU keyword present -> relevant regardless of durbin
    idxs = [m.start() for m in re.finditer('durbin', tl)]
    if not idxs:
        return False                       # not a durbin-driven match
    return not any(_DURBIN_CTX_RX.search(tl[max(0, i - 100):i + 100]) for i in idxs)
for member, date, source, chamber, package, nwords, text in rows:
    text = str(text or '')
    if _interchange_only_offtopic(text.lower()):   # F3: drop off-topic bare-'interchange' rows
        drop_offtopic += 1
        continue
    if _durbin_only_offtopic(text.lower()):        # keep durbin only as the amendment or in a CU context
        drop_durbin += 1
        continue
    canon = resolver.resolve(name=member)          # fail-closed: None if not uniquely resolved
    bio = NAME2BIO.get(canon) if canon else None
    if not canon or not bio:
        drop_unresolved += 1
        continue
    if INSERT_RX.search(text[:220]):               # BUG-E: pure insert-into-the-Record request, not speech
        drop_insert += 1
        continue
    h = (bio, hashlib.md5(text[:TEXTCAP].encode('utf-8', 'replace')).hexdigest())   # BUG-E + B1: dedup on the STORED (truncated) text
    if h in seen:
        drop_dup += 1
        continue
    seen.add(h)
    # route on the full untruncated text (same text the keyword gate matched on)
    cats = MR.route_raw_categories(text, [])
    if not cats:
        drop_nocat += 1
        continue
    kept += 1
    members.add(bio)
    for c in cats:
        catdist[c] += 1
    out_rows.append([bio, canon, date, source, chamber, ';'.join(cats),
                     nwords if nwords is not None else '', text[:TEXTCAP]])

# ---- write interviews_cu.csv (atomic replace) ----
tmp = OUT + '.tmp'
with open(tmp, 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f)
    w.writerow(['bioguide', 'member', 'date', 'source', 'chamber', 'categories', 'nwords', 'text'])
    w.writerows(out_rows)
os.replace(tmp, OUT)

# ---- report ----
print('=== extract_cu_interviews ===')
print('total matched (date>=%s + keyword) : %d' % (MINDATE, total))
print('kept                               : %d' % kept)
print('dropped - member unresolved        : %d' % drop_unresolved)
print('dropped - insert-into-Record        : %d' % drop_insert)
print('dropped - exact duplicate          : %d' % drop_dup)
print('dropped - no routed category       : %d' % drop_nocat)
print('dropped - interchange off-topic    : %d' % drop_offtopic)
print('dropped - durbin non-CU            : %d' % drop_durbin)
print('distinct members (bioguide)        : %d' % len(members))
print('wrote                              : %s' % OUT)
print('--- category distribution (kept rows, multi-cat counted per category) ---')
for cat, n in catdist.most_common():
    print('  %-40s %d' % (cat, n))
