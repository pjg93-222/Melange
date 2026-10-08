# -*- coding: utf-8 -*-
"""V2 adversarial scans + V3 segment tails.  READ-ONLY, ledger only.

A. CENSUS of every DISTINCT cut tag over all 5,484 truncated rows, with frequency and one
   example rowid.  This is the shape that finds a non-speaker cut trigger without my having to
   guess which shape it would take.
B. S4 bucketing: why does the kept text end without terminal punctuation?
C. Extra risk shapes not in the brief:
     X1 cut tag is a bare single token with no honorific and no parenthetical
     X2 removed text carries NO further tag beyond the cut tag AND is >=40 words (a long
        untagged run is where a member's return would hide)
     X3 kept share <= 10% of the original words (biggest blast radius)
     X4 cut tag looks like a place / organisation / heading (no broadcast marker, no honorific,
        and every token is a non-person word by an independent list)
     X5 class E tag whose removed run is >=25 words (colon-less = weakest evidence)
D. V3: for the 90 sampled rows, every removed segment's tag + its last 260 characters, plus a
   first-person marker count, so a member's untagged return can be read rather than assumed.
"""
import collections
import io
import json
import os
import random
import re
import sys
import unicodedata

LEDGER, OUTDIR = sys.argv[1], sys.argv[2]
SEED, PER_CLASS = 20260920, 15
_AP = "'`’‘ʼ"


def norm(s):
    s = unicodedata.normalize('NFD', s or '')
    s = ''.join(c for c in s if not unicodedata.combining(c))
    for ch in _AP:
        s = s.replace(ch, "'")
    return re.sub(r"[^a-z ]", '', s.lower()).strip()


TS = re.compile(r'\[\d{1,2}:\d{2}(?::\d{2})?\]\s*$')
PAREN_END = re.compile(r'\([^)]*\)\s*$')
TERMINAL = '.?!…'
CLOSERS = '"”’\')]»'
DASH_END = re.compile(r'(?:--|—|-)\s*$')
HON = re.compile(r'\b(?:SEN|REP|PRES|GOV|DR|FMR|AMB|DEL|MR|MS|MRS|SENATOR|REPRESENTATIVE|'
                 r'CONGRESSMAN|CONGRESSWOMAN|CHAIRMAN|CHAIRWOMAN|PRESIDENT|GOVERNOR|SPEAKER|'
                 r'SECRETARY|GENERAL|JUDGE|MAYOR|ADMIRAL|COLONEL|CAPTAIN)\b\.?', re.I)
BCAST = re.compile(r'\((?:voice[\s\-]?over|on\s?camera|through|voiceover|on\s?the\s?phone|'
                   r'via|audio|recorded|taped|interpreter|translator)', re.I)
ROLE = re.compile(r'\b(?:UNIDENTIFIED|UNKNOWN|ANNOUNCER|NARRATOR|MODERATOR|INTERPRETER|'
                  r'AUTOMATED)\b')
# An independent (not the tool's) list of words that are not a person's name.
NONPERSON = set('''COMMITTEE SUBCOMMITTEE SENATE HOUSE CONGRESS CAUCUS DEPARTMENT BUREAU OFFICE
AGENCY ADMINISTRATION UNIVERSITY COLLEGE SCHOOL INSTITUTE FOUNDATION CENTER CENTRE COUNCIL
ASSOCIATION SOCIETY UNION COMPANY CORPORATION GROUP NETWORK CHANNEL NEWS TIMES POST JOURNAL
HOSPITAL CHURCH COUNTY CITY TOWN STATE STATES COUNTRY NATION AMERICA AMERICAN UNITED FEDERAL
NATIONAL INTERNATIONAL GLOBAL WORLD PARK PARKS DISTRICT STREET AVENUE ROAD BUILDING HALL
BACKGROUND SUMMARY CONCLUSION QUESTION ANSWER NOTE UPDATE BREAKING TRANSCRIPT HEADLINE HEADLINES
SECTION TITLE CHAPTER APPENDIX EXHIBIT TABLE FIGURE PART ITEM TOPIC AGENDA MINUTES RECORD
NEW YORK LOS ANGELES WASHINGTON CHICAGO TEXAS FLORIDA CALIFORNIA GEORGIA VIRGINIA CAROLINA
OHIO MICHIGAN ARIZONA NEVADA COLORADO OREGON ALASKA HAWAII IOWA UTAH MAINE IDAHO KANSAS'''.split())

records = []
with io.open(LEDGER, encoding='utf-8') as fh:
    for line in fh:
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        if not r['skip']:
            records.append(r)

# ---------------------------------------------------------------- A. distinct cut-tag census
tagc = collections.Counter()
tag_example = {}
tag_classes = collections.defaultdict(set)
for r in records:
    t = r['cut_tag'] or ''
    tagc[t] += 1
    tag_classes[t].add(r['cut_class'])
    tag_example.setdefault(t, r['rowid'])

census = [{'tag': t, 'n': n, 'classes': sorted(tag_classes[t]), 'example_rowid': tag_example[t]}
          for t, n in tagc.most_common()]

# ------------------------------------------------------------------------- B. S4 bucketing
s4_buckets = collections.Counter()
s4_rows = collections.defaultdict(list)
for r in records:
    k = (r['kept']['text'] or '').rstrip()
    kk = k
    while kk and kk[-1] in CLOSERS:
        kk = kk[:-1].rstrip()
    if kk and kk[-1] in TERMINAL:
        continue                                  # ends on a terminal: not an S4 hit
    if TS.search(k):
        core = TS.sub('', k).rstrip()
        while core and core[-1] in CLOSERS:
            core = core[:-1].rstrip()
        b = 'ends_cnn_timestamp_after_terminal' if (core and core[-1] in TERMINAL) \
            else 'ends_cnn_timestamp_after_nonterminal'
    elif DASH_END.search(k):
        b = 'ends_dash_interrupted_speech'
    elif PAREN_END.search(k):
        b = 'ends_parenthetical'
    elif k.endswith(','):
        b = 'ends_comma'
    elif k.endswith(':') or k.endswith(';'):
        b = 'ends_colon_or_semicolon'
    else:
        b = 'ends_bare_word'
    s4_buckets[b] += 1
    s4_rows[b].append({'rowid': r['rowid'], 'member': r['member'], 'cut_class': r['cut_class'],
                       'cut_tag': r['cut_tag'], 'kept_tail': r['kept']['text'][-200:],
                       'removed_head': r['removed']['raw'][:200],
                       'kept_nwords': r['kept']['nwords']})

# ------------------------------------------------------------------------- C. extra shapes
x1, x2, x3, x4, x5 = [], [], [], [], []
for r in records:
    tag = r['cut_tag'] or ''
    up = [w for w in re.split(r"[^A-Za-zÀ-ɏ'’\-]+", tag) if w]
    core_tokens = [w.upper() for w in up if not HON.fullmatch(w) and not HON.fullmatch(w + '.')]
    has_hon = bool(HON.search(tag))
    has_paren = '(' in tag
    if len(core_tokens) == 1 and not has_hon and not has_paren:
        x1.append({'rowid': r['rowid'], 'member': r['member'], 'cut_tag': tag,
                   'cut_class': r['cut_class'], 'kept_tail': r['kept']['text'][-200:],
                   'removed_head': r['removed']['raw'][:250]})
    if len(r['removed']['segments']) <= 1 and r['removed']['nwords'] >= 40:
        x2.append(r['rowid'])
    before = int(r['original']['nwords'] or 0)
    if before and r['kept']['nwords'] / float(before) <= 0.10:
        x3.append({'rowid': r['rowid'], 'member': r['member'], 'cut_tag': tag,
                   'cut_class': r['cut_class'], 'kept_nwords': r['kept']['nwords'],
                   'orig_nwords': before, 'kept_text': r['kept']['text'][:220],
                   'removed_head': r['removed']['raw'][:250]})
    if (core_tokens and not has_hon and not BCAST.search(tag) and not ROLE.search(tag)
            and all(t in NONPERSON for t in core_tokens)):
        x4.append({'rowid': r['rowid'], 'member': r['member'], 'cut_tag': tag,
                   'cut_class': r['cut_class'], 'kept_tail': r['kept']['text'][-200:],
                   'removed_head': r['removed']['raw'][:250]})
    if r['cut_class'] == 'E_colonless_honorific' and r['removed']['nwords'] >= 25:
        x5.append({'rowid': r['rowid'], 'member': r['member'], 'cut_tag': tag,
                   'removed_nwords': r['removed']['nwords'],
                   'kept_tail': r['kept']['text'][-200:],
                   'removed_head': r['removed']['raw'][:320]})

# ------------------------------------------------------------------------ D. V3 segment tails
by_class = collections.defaultdict(list)
for r in records:
    by_class[r['cut_class']].append(r)
for k in by_class:
    by_class[k].sort(key=lambda r: r['rowid'])
rnd = random.Random(SEED)
sample = []
for cls in sorted(by_class):
    sample.extend(rnd.sample(by_class[cls], min(PER_CLASS, len(by_class[cls]))))
sample.sort(key=lambda r: (r['cut_class'], r['rowid']))

FP = re.compile(r'(?:(?<=^)|(?<=[.?!]\s))\s*(I|I\'m|I\'ve|My|We|We\'re|Our)\b')
os.makedirs(OUTDIR, exist_ok=True)
with io.open(os.path.join(OUTDIR, 'V3_segment_tails_sample90.txt'), 'w', encoding='utf-8',
             newline='\n') as fh:
    for i, r in enumerate(sample, 1):
        fh.write('=' * 96 + '\n')
        fh.write('#%02d rowid=%s class=%s member=%r  removed_nwords=%s  segs=%d\n'
                 % (i, r['rowid'], r['cut_class'], r['member'], r['removed']['nwords'],
                    len(r['removed']['segments'])))
        for j, s in enumerate(r['removed']['segments'], 1):
            body = s['text'] or ''
            fh.write('   seg%d tag=%r cls=%s nwords=%d firstperson_starts=%d\n'
                     % (j, s['tag'], s['class'], s['nwords'], len(FP.findall(body))))
            fh.write('      HEAD: %s\n' % body[:200].replace('\n', ' '))
            if len(body) > 260:
                fh.write('      TAIL: ...%s\n' % body[-260:].replace('\n', ' '))
        fh.write('\n')


def dump(name, obj):
    with io.open(os.path.join(OUTDIR, name), 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(obj, fh, indent=1, ensure_ascii=False, sort_keys=True)


dump('V2_cut_tag_census.json', census)
dump('V2_scan_S4_buckets.json', {'buckets': dict(s4_buckets),
                                 'rows': {k: v for k, v in s4_rows.items()}})
dump('V2_scan_X1_bare_single_token_tag.json', x1)
dump('V2_scan_X3_kept_share_le_10pct.json', x3)
dump('V2_scan_X4_place_or_org_tag.json', x4)
dump('V2_scan_X5_classE_long_removal.json', x5)
dump('V2_scan_X2_single_segment_ge40w_rowids.json', x2)

print(json.dumps({
    'distinct_cut_tags': len(census),
    'top20': [(c['tag'], c['n']) for c in census[:20]],
    'S4_buckets': dict(s4_buckets),
    'X1_bare_single_token_tag': len(x1),
    'X2_single_segment_ge40w': len(x2),
    'X3_kept_share_le_10pct': len(x3),
    'X4_place_or_org_tag': len(x4),
    'X5_classE_removal_ge25w': len(x5),
}, indent=1, ensure_ascii=False))
