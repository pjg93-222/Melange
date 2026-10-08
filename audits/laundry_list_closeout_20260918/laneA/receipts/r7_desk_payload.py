# -*- coding: utf-8 -*-
"""LANE A / R7 -- the PUBLISHED desk payload: its own media census + D-034 evidence (read-only).

member_desk_bundle.json carries bundle['integrity']['source_display'] == the media_audit dict
built by make_member_desk.load_press_and_bills.  That is the producer's OWN census of the
published surface, so it is the authority for what is displayed, and the cross-check for R4.

Also counts, in the shipped bytes: 'also posted on' notes (D-034), scored/unscored article rows
by source, and exclusion reasons -- from the deferred profile script that actually carries them.
"""
import os, sys, io, json, re, collections, datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
BUNDLE = os.path.join(ROOT, 'member_desk_bundle.json')
HTML = os.path.join(ROOT, 'cu-member-desk.html')
PROF = os.path.join(ROOT, 'cu-member-desk-profiles.js')
print('=' * 100)
print('R7  PUBLISHED DESK PAYLOAD   run', datetime.datetime.now().isoformat(timespec='seconds'))
print('=' * 100)
for lbl, p in (('member_desk_bundle.json', BUNDLE), ('cu-member-desk.html', HTML),
               ('cu-member-desk-profiles.js', PROF)):
    print('   %-30s %14d bytes  mtime %s' % (lbl, os.path.getsize(p),
          datetime.datetime.fromtimestamp(os.path.getmtime(p)).isoformat(sep=' ')))

# ---- A. the desk's own media_audit ------------------------------------------------------------
print('\n-- A. bundle["integrity"]["source_display"] == media_audit (the producer census) --')
with io.open(BUNDLE, encoding='utf-8') as fh:
    bundle = json.load(fh)
sd = (bundle.get('integrity') or {}).get('source_display') or {}
skip = {'exclusion_samples', 'social_exclusions_by_member'}
for k in sorted(sd):
    if k in skip:
        continue
    print('   %-52s %s' % (k, sd[k]))
xs = sd.get('exclusion_samples') or {}
print('\n   exclusion_samples sizes: %s' % {k: len(v) for k, v in xs.items()})
sebm = sd.get('social_exclusions_by_member') or {}
print('   social_exclusions_by_member: %d members;  unrelated total=%d  offtopic total=%d'
      % (len(sebm), sum(v.get('unrelated', 0) for v in sebm.values()),
         sum(v.get('offtopic', 0) for v in sebm.values())))

print('\n-- social accounting stated by the published bundle --')
si = sd.get('social_source_rows', 0)
parts = [('social_unverified_handle_excluded', sd.get('social_unverified_handle_excluded', 0)),
         ('social_unknown_member_excluded', sd.get('social_unknown_member_excluded', 0)),
         ('social_unrelated_excluded', sd.get('social_unrelated_excluded', 0)),
         ('social_offtopic_excluded', sd.get('social_offtopic_excluded', 0)),
         ('social_displayed', sd.get('social_displayed', 0))]
tot = sum(v for _, v in parts)
print('   social_source_rows = %d' % si)
for k, v in parts:
    print('      %-40s %6d' % (k, v))
print('   sum of the five = %d   -> %s' % (tot, 'CLOSES' if tot == si else 'DOES NOT CLOSE (delta %d)' % (si - tot)))

print('\n-- press accounting stated by the published bundle --')
pi = sd.get('press_source_rows', 0)
pparts = [('press_unknown_member_excluded', sd.get('press_unknown_member_excluded', 0)),
          ('press_billstatus_rows_routed_to_legislation',
           sd.get('press_billstatus_rows_routed_to_legislation', 0)),
          ('press_displayed', sd.get('press_displayed', 0))]
ptot = sum(v for _, v in pparts)
print('   press_source_rows = %d   (sheet "Press Release Articles")' % pi)
for k, v in pparts:
    print('      %-46s %6d' % (k, v))
print('   sum = %d   -> %s' % (ptot, 'CLOSES' if ptot == pi else 'DOES NOT CLOSE (delta %d)' % (pi - ptot)))

print('\n-- footprint accounting stated by the published bundle --')
for tag, src, subs in (
        ('interview', 'interview_episode_rows',
         ['interview_unknown_member_excluded', 'interview_appearances_displayed',
          'interview_beyond_display_cap']),
        ('hearing', 'hearing_appearance_rows',
         ['hearing_unknown_member_excluded', 'hearing_appearances_displayed',
          'hearing_beyond_display_cap']),
        ('bluesky', 'bluesky_post_rows',
         ['bluesky_unverified_handle_posts_excluded', 'bluesky_unknown_member_excluded',
          'bluesky_empty_text_excluded', 'bluesky_scored_rows_routed_to_social',
          'bluesky_footprint_displayed', 'bluesky_beyond_display_cap'])):
    base = sd.get(src, 0)
    extra = sd.get('hearing_graded_rows_added', 0) if tag == 'hearing' else 0
    print('   %s: %s = %d %s' % (tag, src, base,
                                 '+ hearing_graded_rows_added %d' % extra if extra else ''))
    s = 0
    for k in subs:
        v = sd.get(k, 0)
        s += v
        print('      %-48s %6d' % (k, v))
    print('      sum = %d vs %d -> %s' % (s, base + extra,
                                          'CLOSES' if s == base + extra else 'DELTA %d' % (base + extra - s)))

# ---- B. article rows actually in the payload --------------------------------------------------
print('\n-- B. article rows in the FULL bundle (bundle["members"][*]["articles"]) --')
by_source = collections.Counter()
scored_by_source = collections.Counter()
excl = collections.Counter()
also = 0
also_by_platform = collections.Counter()
cats_seen = collections.Counter()
n_arts = 0
members_with = 0
for m in bundle.get('members') or []:
    arts = m.get('articles') or []
    if arts:
        members_with += 1
    for a in arts:
        n_arts += 1
        s = a.get('source') or '?'
        by_source[s] += 1
        if a.get('scored'):
            scored_by_source[s] += 1
        if a.get('exclusion'):
            excl[(s, a['exclusion'])] += 1
        if a.get('also'):
            also += 1
            mm = re.match(r'also posted on (\S+)', a['also'])
            also_by_platform[mm.group(1) if mm else '?'] += 1
        for c in (a.get('cats') or []):
            cats_seen[c] += 1
print('   total article rows: %d across %d members' % (n_arts, members_with))
print('   by source:')
for s, v in by_source.most_common():
    print('      %-12s displayed %6d   scored=True %6d' % (s, v, scored_by_source.get(s, 0)))
print('   exclusion reasons (source, reason) -> rows:')
for (s, r), v in excl.most_common():
    print('      %-10s %-48s %6d' % (s, r, v))
print('\n   D-034 EVIDENCE: article rows carrying an "also posted on ..." note: %d' % also)
print('      by named first platform: %s' % dict(also_by_platform.most_common()))
print('   categories present on displayed article rows (norm_cats output):')
for c, v in cats_seen.most_common():
    print('      %-34s %6d' % (c, v))

# ---- C. shipped-bytes check in the deferred profile script ------------------------------------
print('\n-- C. shipped bytes: literal "also posted on" occurrences --')
for lbl, p in (('cu-member-desk.html', HTML), ('cu-member-desk-profiles.js', PROF)):
    n = 0
    with io.open(p, encoding='utf-8', errors='replace') as fh:
        while True:
            chunk = fh.read(1 << 22)
            if not chunk:
                break
            n += chunk.count('also posted on')
    print('   %-30s "also posted on" x %d' % (lbl, n))

# ---- D. is the media/press census surfaced to the reader? -------------------------------------
print('\n-- D. does the page expose the media census to a reader? --')
needles = ['social_unrelated_excluded', 'social_offtopic_excluded', 'source_display',
           'media_exclusions', 'nothing hidden', 'exact cross-post']
with io.open(HTML, encoding='utf-8', errors='replace') as fh:
    html = fh.read()
for nd in needles:
    print('   %-28s in cu-member-desk.html: %s' % (nd, html.count(nd)))
print('\nDONE R7')
