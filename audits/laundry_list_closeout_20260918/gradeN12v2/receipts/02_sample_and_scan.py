# -*- coding: utf-8 -*-
"""V2/V3 evidence extraction.  READ-ONLY, ledger only, no production import.

(1) Seeded sample (seed 20260920) of 90 TRUNCATED rows stratified by cut_class, 15 per class.
(2) Mechanical scan of ALL truncated rows for the four high-risk shapes:
      S1 tag surname == the row member's surname (several independent equality tests)
      S2 the cut tag sits inside quotation marks
      S3 the cut tag is preceded by said / told / asked / according to
      S4 the kept text ends without terminal punctuation (mid-sentence)
(3) V3 signal: does the REMOVED text carry an explicit OWN-member tag after the cut?

Nothing here imports fec/*: normalisation is reimplemented so the grade is independent.
"""
import collections
import io
import json
import os
import random
import re
import sys
import unicodedata

LEDGER = sys.argv[1]
OUTDIR = sys.argv[2]
SEED = 20260920
PER_CLASS = 15

_AP = "'`’‘ʼ"


def norm(s):
    s = unicodedata.normalize('NFD', s or '')
    s = ''.join(c for c in s if not unicodedata.combining(c))
    for ch in _AP:
        s = s.replace(ch, "'")
    return re.sub(r"[^a-z ]", '', s.lower()).strip()


def tag_tokens(tag):
    """Every normalised word-ish token in a tag, plus hyphen/space components.  Independent
    reimplementation (over-inclusive, like the tool's name_tokens)."""
    out = set()
    for w in re.split(r"[^A-Za-zÀ-ɏ.'`’‘ʼ\-]+", tag or ''):
        n = norm(w)
        if n:
            out.add(n)
        for part in re.split(r"[-\s]+", w):
            p = norm(part)
            if p:
                out.add(p)
    return out


SAID = re.compile(r"\b(said|says|saying|told|tells|asked|asks|asking|"
                  r"according\s+to|quote|quoting|quoted|wrote|writes|tweeted|posted)\b"
                  r"[^.?!]{0,40}$", re.I)
TERMINAL = '.?!…'
CLOSERS = '"”’\')]»'
OPEN_Q = '"“„«'
CLOSE_Q = '"”»'


def ends_midsentence(kept):
    k = (kept or '').rstrip()
    while k and k[-1] in CLOSERS:
        k = k[:-1].rstrip()
    if not k:
        return True
    return k[-1] not in TERMINAL


def quote_state(head):
    """Is the cut point inside an open quotation?  Counts straight quotes parity and curly
    open/close balance over the whole kept prefix."""
    straight = head.count('"') % 2 == 1
    curly = head.count('“') - head.count('”')
    return bool(straight or curly > 0)


records = []
with io.open(LEDGER, encoding='utf-8') as fh:
    for line in fh:
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        if r['skip']:
            continue
        records.append(r)

by_class = collections.defaultdict(list)
for r in records:
    by_class[r['cut_class']].append(r)
for k in by_class:
    by_class[k].sort(key=lambda r: r['rowid'])

# ---------------------------------------------------------------- stratified seeded sample
rnd = random.Random(SEED)
sample = []
for cls in sorted(by_class):
    pool = by_class[cls]
    n = min(PER_CLASS, len(pool))
    sample.extend(rnd.sample(pool, n))
sample.sort(key=lambda r: (r['cut_class'], r['rowid']))
sample_ids = [r['rowid'] for r in sample]

# ---------------------------------------------------------------- mechanical scans, ALL rows
s1, s2, s3, s4 = [], [], [], []
own_tag_after_cut = []
scan_rows = collections.Counter()
for r in records:
    tag = r['cut_tag'] or ''
    orig = r['original']['text']
    cut = r['cut_at']
    head = orig[:cut]
    member = r['member']
    mp = norm(member).split()
    msur = mp[-1] if mp else ''
    mfirst = mp[0] if mp else ''
    toks = tag_tokens(tag)

    # S1 -- surname equality, four independent tests
    hit1 = []
    if msur and msur in toks:
        hit1.append('exact_token')
    if msur and len(msur) >= 4:
        for t in toks:
            if len(t) >= 4 and t != msur and (t.startswith(msur) or msur.startswith(t)):
                hit1.append('prefix_relation:%s' % t)
    if msur and len(msur) >= 4 and re.search(re.escape(msur), norm(tag).replace(' ', '')):
        hit1.append('substring_in_joined_tag')
    if mfirst and mfirst in toks and len(mfirst) >= 4:
        hit1.append('member_firstname_in_tag')
    if hit1:
        s1.append({'rowid': r['rowid'], 'member': member, 'cut_tag': tag,
                   'cut_class': r['cut_class'], 'tests': sorted(set(hit1))})

    # S2 -- tag inside quotation marks
    prev = head[-1:] if head else ''
    if quote_state(head) or prev in OPEN_Q:
        s2.append({'rowid': r['rowid'], 'member': member, 'cut_tag': tag,
                   'cut_class': r['cut_class'],
                   'open_straight': head.count('"') % 2 == 1,
                   'open_curly': head.count('“') - head.count('”'),
                   'char_before': prev,
                   'head_tail': head[-160:], 'removed_head': r['removed']['raw'][:160]})

    # S3 -- attribution verb immediately before the tag
    m = SAID.search(head[-200:])
    if m:
        s3.append({'rowid': r['rowid'], 'member': member, 'cut_tag': tag,
                   'cut_class': r['cut_class'], 'verb': m.group(1),
                   'head_tail': head[-200:], 'removed_head': r['removed']['raw'][:160]})

    # S4 -- kept text ends mid-sentence
    if ends_midsentence(r['kept']['text']):
        s4.append({'rowid': r['rowid'], 'member': member, 'cut_tag': tag,
                   'cut_class': r['cut_class'],
                   'kept_tail': r['kept']['text'][-160:],
                   'removed_head': r['removed']['raw'][:160]})

    # V3 signal -- an explicit OWN-member tag AFTER the cut
    own_after = [t for t in r['all_tags']
                 if t['at'] >= cut and (t['ownership'] == 'own'
                                        or (msur and msur in tag_tokens(t['tag'])))]
    if own_after:
        own_tag_after_cut.append({'rowid': r['rowid'], 'member': member,
                                  'cut_class': r['cut_class'],
                                  'own_tags': [t['tag'] for t in own_after],
                                  'removed_nwords': r['removed']['nwords']})

os.makedirs(OUTDIR, exist_ok=True)


def dump(name, obj):
    with io.open(os.path.join(OUTDIR, name), 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(obj, fh, indent=1, ensure_ascii=False, sort_keys=True)


dump('V2_sample90_ids.json', {'seed': SEED, 'per_class': PER_CLASS,
                              'class_pool_sizes': {k: len(v) for k, v in sorted(by_class.items())},
                              'ids': sample_ids,
                              'ids_by_class': {cls: [r['rowid'] for r in sample
                                                     if r['cut_class'] == cls]
                                               for cls in sorted(by_class)}})
dump('V2_scan_S1_surname_equals_member.json', s1)
dump('V2_scan_S2_tag_inside_quotes.json', s2)
dump('V2_scan_S3_attribution_verb_before_tag.json', s3)
dump('V2_scan_S4_kept_ends_midsentence.json', s4)
dump('V3_own_member_tag_after_cut.json', own_tag_after_cut)

# ------------------------------------------------------------------- readable sample dossier
with io.open(os.path.join(OUTDIR, 'V2_sample90_text.txt'), 'w', encoding='utf-8',
             newline='\n') as fh:
    for i, r in enumerate(sample, 1):
        orig = r['original']['text']
        cut = r['cut_at']
        fh.write('=' * 100 + '\n')
        fh.write('#%02d  rowid=%s  class=%s  member=%r  date=%s  show=%s  pkg=%s\n'
                 % (i, r['rowid'], r['cut_class'], r['member'], r['date'], r['chamber'],
                    r['package']))
        fh.write('    CUT_TAG=%r   cut_at=%s   orig_nwords=%s  kept=%s  removed=%s\n'
                 % (r['cut_tag'], cut, r['original']['nwords'], r['kept']['nwords'],
                    r['removed']['nwords']))
        fh.write('    ALL_TAGS=%s\n' % json.dumps(r['all_tags'], ensure_ascii=False))
        fh.write('    --- KEPT HEAD  : %s\n' % orig[:200].replace('\n', ' '))
        fh.write('    --- KEPT TAIL  : ...%s\n' % orig[max(0, cut - 420):cut].replace('\n', ' '))
        fh.write('    >>> CUT HERE <<<\n')
        fh.write('    --- REMOVED    : %s\n' % r['removed']['raw'][:700].replace('\n', ' '))
        fh.write('    --- REM TAIL   : ...%s\n' % r['removed']['raw'][-300:].replace('\n', ' '))
        fh.write('    --- SEGMENT TAGS: %s\n'
                 % json.dumps([(s['tag'], s['class'], s['nwords']) for s in
                               r['removed']['segments']], ensure_ascii=False))
        fh.write('\n')

print(json.dumps({
    'truncated_records': len(records),
    'class_pool_sizes': {k: len(v) for k, v in sorted(by_class.items())},
    'sample_n': len(sample),
    'S1_surname_equals_member': len(s1),
    'S2_tag_inside_quotes': len(s2),
    'S3_attribution_verb_before_tag': len(s3),
    'S4_kept_ends_midsentence': len(s4),
    'V3_own_member_tag_after_cut': len(own_tag_after_cut),
}, indent=1, sort_keys=True))
