# -*- coding: utf-8 -*-
"""measR1d U2: ROW-LEVEL foreign-speaker-tag census over every INTERVIEW row of `speeches`.

Lane B / F2 measured MENTION WINDOWS inside the member->member reference layer. This measures the
ROWS themselves, which is what the member desk and the media blend consume.

WHY THE DETECTOR LOOKS LIKE THIS
  Stored rows contain NO newlines (lane B 02b: has_newline 0/270489) because every writer runs
  re.sub(r'\\s+',' ') before INSERT.  So the production splitter's own `^`-anchored LABEL regex
  (fetch_interviews.py:202) can never be re-applied to the stored text: in the stored text a
  surviving tag is always MID-STRING.  D-U2 therefore anchors on STRING-START or SENTENCE-START.

D-U2  (a row is FLAGGED when it contains >=1 FOREIGN tag)
  TAG   = optional honorific + 1..4 ALL-CAPS name tokens (token class [A-Z] + [A-Z.'`-]*, the
          BACKTICK included on purpose: Fox/CNN write O`DONNELL) + optional ", ROLE/PARTY" tail
          + optional parenthetical, which MAY be lower case ((voice-over) / (on camera))
          + ":" or "::"
  ANCHOR= start of text, or after [.?!] / -- / em-dash / >> / a closing quote-after-terminator,
          followed by at most one space.  (Mid-sentence "told CNN: ..." is NOT an anchor.)
  QUAL  = the name part must not be entirely STOP tokens; and one of
            (a) an honorific is present, or
            (b) >=2 non-STOP name tokens, or
            (c) exactly 1 name token which is in SPEAKER_LEX -- a corpus-derived lexicon of
                surnames seen in multi-token qualifying tags, plus every roster surname.
          (c) is what admits bare 'WALLACE:' / 'O`DONNELL:' / 'BLITZER:' without admitting 'ICE:'.
  ALLCAPS rows (>85% of letters upper) are skipped whole -- they are headings, not turns.
  FOREIGN = QUAL and the tag does not name the row's attributed member (surname match, guarded by
          first-name compatibility when the tag carries >=2 name tokens).

Pass 1 builds SPEAKER_LEX; pass 2 flags.  READ-ONLY: opens social_media.db with mode=ro and
PRAGMA query_only.  Writes only into this packet's receipts dir.
"""
import collections, io, json, os, re, sqlite3, sys, unicodedata, random, csv, hashlib

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
LIVE = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
PK = (r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees'
      r'\unfinished-work-handoff-a3bbad\audits\laundry_list_closeout_20260918\measR1d\receipts')
DB = LIVE + r'\social_media.db'
SEED = 20260918

# ---------------------------------------------------------------- roster
C = {m['member']: m for m in json.load(io.open(LIVE + r'\data\engine\congestion.json', encoding='utf-8'))}


def nrm(s):
    s = unicodedata.normalize('NFD', s or '')
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = s.replace('`', "'")
    return re.sub(r"[^a-z ]", '', s.lower()).strip()


ROSTER_SUR = {nrm(m).split()[-1] for m in C if nrm(m).split()}
NICK_SETS = [
    {'bernard', 'bernie'}, {'charles', 'chuck', 'charlie'}, {'christopher', 'chris'},
    {'richard', 'dick', 'rich', 'rick'}, {'michael', 'mike'}, {'james', 'jim', 'jimmy'},
    {'robert', 'bob', 'rob', 'bobby'}, {'thomas', 'tom', 'tommy'}, {'daniel', 'dan', 'danny'},
    {'joseph', 'joe', 'joey'}, {'timothy', 'tim'}, {'patrick', 'pat'},
    {'william', 'bill', 'will', 'billy'}, {'edward', 'ed', 'ted', 'eddie'}, {'theodore', 'ted'},
    {'elizabeth', 'liz', 'beth', 'betty'}, {'katherine', 'kathryn', 'katie', 'kate', 'kathy'},
    {'margaret', 'maggie', 'meg'}, {'benjamin', 'ben'}, {'alexander', 'alex'}, {'anthony', 'tony'},
    {'andrew', 'andy', 'drew'}, {'matthew', 'matt'}, {'jonathan', 'jon'}, {'nicholas', 'nick'},
    {'gregory', 'greg'}, {'lawrence', 'larry'}, {'gerald', 'jerry'}, {'ronald', 'ron', 'ronny'},
    {'donald', 'don'}, {'kenneth', 'ken'}, {'stephen', 'steven', 'steve'}, {'david', 'dave'},
    {'samuel', 'sam'}, {'frederick', 'fred'}, {'susan', 'sue', 'suzy'}, {'deborah', 'debbie', 'deb'},
    {'cynthia', 'cindy'}, {'jacquelyn', 'jacqueline', 'jackie'}, {'raphael', 'rafael', 'raffi'},
    {'joshua', 'josh'}, {'zachary', 'zach', 'zack'}, {'abigail', 'abby'},
    {'rebecca', 'becca', 'becky'}, {'jefferson', 'jeff'}, {'jeffrey', 'jeff'}, {'mitchell', 'mitch'},
    {'randall', 'randy'}, {'terrence', 'terri', 'terry'}, {'vincent', 'vince'},
]
NICK = {}
for _s in NICK_SETS:
    for _a in _s:
        NICK.setdefault(_a, set()).update(_s)


def fn_compat(a, b):
    if not a or not b:
        return False
    return a == b or a.startswith(b) or b.startswith(a) or bool(
        (NICK.get(a, set()) | {a}) & (NICK.get(b, set()) | {b}))


# ---------------------------------------------------------------- tag grammar
HON = (r"(?:SEN\.|REP\.|PRES\.|GOV\.|DR\.|FMR\.|AMB\.|DEL\.|MR\.|MS\.|MRS\.|SENATOR|"
       r"REPRESENTATIVE|CONGRESSMAN|CONGRESSWOMAN|CHAIRMAN|CHAIRWOMAN|PRESIDENT|GOVERNOR|"
       r"SPEAKER|SECRETARY|GENERAL|JUDGE|MAYOR|ADMIRAL|COLONEL|CAPTAIN)")
NAMETOK = r"[A-Z][A-Z.'`\-]{0,24}"
PAREN = r"(?:\s*\((?:[^)]{1,30})\))?"
TAIL = r"(?:\s*,\s*[A-Z][A-Za-z.'\- ]{1,60}?)?"
ANCHOR = r"(?:^|(?<=[.?!])|(?<=\-\-)|(?<=\u2014)|(?<=>>)|(?<=[.?!][\"\u201d']))"
TAG = re.compile(ANCHOR + r"[ ]{0,2}((?:" + HON + r"\s+)?" + NAMETOK +
                 r"(?:\s+" + NAMETOK + r"){0,3}" + TAIL + PAREN + r")\s*::?(?=\s|$|\u2014|\-\-)")

STOP = set('''USA GAO DOI EPA FBI CIA NSA DOJ DOD HHS IRS FEMA SNAP CNN FOX MSNBC NPR PBS ABC CBS NBC BBC AP
NATO UN EU WHO CDC NIH FDA SEC FCC FTC HUD VA DHS TSA ICE CBP ATF DEA NASA NOAA USDA DOT FAA GDP CEO ACA
WCNSF KUCB URI NPS DACA GAC SAFE RELIEF ACT BANKING COMMITTEE SENATE HOUSE CONGRESS CAUCUS SUBCOMMITTEE
CHAIR RANKING DEMOCRAT REPUBLICAN MAJORITY MINORITY LEADER WHIP HEALTH UNITS NEXT STEPS TITLE SECTION
GOP COVID US DC AI PS NOTE QUESTION ANSWER BACKGROUND SUMMARY CONCLUSION FUND DEPARTMENT DEFENSE MILITARY
RETIREMENT ADMINISTRATION BUREAU OFFICE AGENCY SERVICE SERVICES PROGRAM PROGRAMS ACTION REPORT REPORTS
UPDATE BREAKING LIVE VIDEO AUDIO TAPE CLIP TRANSCRIPT WATCH LISTEN READ MORE ALSO EDITOR NOTE
STATE STATES UNITED AMERICA AMERICAN FEDERAL NATIONAL INTERNATIONAL GLOBAL WORLD NEWS TODAY TONIGHT
MONDAY TUESDAY WEDNESDAY THURSDAY FRIDAY SATURDAY SUNDAY JANUARY FEBRUARY MARCH APRIL MAY JUNE JULY
AUGUST SEPTEMBER OCTOBER NOVEMBER DECEMBER'''.split())
HONRE = re.compile(r'^(?:' + HON + r')$')


def allcaps_row(t):
    letters = [c for c in t if c.isalpha()]
    return bool(letters) and sum(1 for c in letters if c.isupper()) / len(letters) > 0.85


def tag_parts(tag):
    """-> (has_hon, [UPPER name tokens]) with parenthetical + comma tail removed."""
    core = re.sub(r'\([^)]*\)', ' ', tag)
    core = core.split(',')[0]
    toks = [t for t in re.split(r"[^A-Za-z.'`\-]+", core) if t.strip(".'`-")]
    if not toks:
        return False, []
    has_hon = bool(HONRE.match(toks[0].upper()))
    words = [t for t in toks if not HONRE.match(t.upper())]
    up = [w.strip(".'`-").upper() for w in words if w.strip(".'`-")]
    return has_hon, up


def is_upper_tag(tag):
    """the NAME part must actually be ALL CAPS (a lower-case parenthetical is allowed)."""
    core = re.sub(r'\([^)]*\)', ' ', tag)
    letters = [c for c in core if c.isalpha()]
    return bool(letters) and all(c.isupper() for c in letters)


# ---------------------------------------------------------------- pass 1: lexicon
con = sqlite3.connect('file:%s?mode=ro' % DB.replace('\\', '/'), uri=True, timeout=300)
con.execute('PRAGMA query_only=ON')
rows = con.execute("SELECT rowid, member, date, chamber, package, text FROM speeches "
                   "WHERE source='INTERVIEW'").fetchall()
con.close()
print('INTERVIEW rows: %d' % len(rows))

lex = collections.Counter()
for rid, mem, date, cham, pkg, txt in rows:
    if not txt or allcaps_row(txt):
        continue
    for m in TAG.finditer(txt):
        tag = m.group(1)
        if not is_upper_tag(tag):
            continue
        hon, up = tag_parts(tag)
        if len(up) >= 2 and not all(w in STOP for w in up):
            last = nrm(up[-1])
            if len(last) >= 3 and up[-1] not in STOP:
                lex[last] += 1
SPEAKER_LEX = set(ROSTER_SUR) | {k for k, v in lex.items() if v >= 1}
print('SPEAKER_LEX: %d surnames (%d roster + %d corpus-derived multi-token surnames)'
      % (len(SPEAKER_LEX), len(ROSTER_SUR), len(lex)))


def qualifies(tag):
    hon, up = tag_parts(tag)
    if not up:
        return False
    if all(w in STOP for w in up):
        return False
    nonstop = [w for w in up if w not in STOP]
    if hon:
        return True
    if len(nonstop) >= 2:
        return True
    if len(up) == 1 and nrm(up[0]) in SPEAKER_LEX:
        return True
    return False


def is_self(tag, member):
    """does this tag name the row's attributed member?"""
    hon, up = tag_parts(tag)
    if not up:
        return False
    mp = nrm(member).split()
    if not mp:
        return False
    msur, mfirst = mp[-1], mp[0]
    tn = [nrm(w) for w in up if nrm(w)]
    if msur not in tn:
        return False
    if len(tn) >= 2:
        cand = [t for t in tn if t != msur]
        return any(fn_compat(t, mfirst) for t in cand) or len(cand) == 0
    return True


# ---------------------------------------------------------------- pass 2: flag
def host_of(pkg):
    m = re.match(r'https?://([^/]+)/', pkg or '')
    return (m.group(1).lower().replace('www.', '') if m else (pkg or '')[:40])


flag_rows, unflag_rows = [], []
by_show = collections.Counter(); by_show_hit = collections.Counter()
by_host = collections.Counter(); by_host_hit = collections.Counter()
by_year = collections.Counter(); by_year_hit = collections.Counter()
tagfreq = collections.Counter()
skipped_allcaps = 0
chars_total = 0; chars_flagged = 0; chars_after = 0
self_only = 0

for rid, mem, date, cham, pkg, txt in rows:
    yr = (date or '')[:4] or '????'
    host = host_of(pkg)
    by_show[cham] += 1; by_host[host] += 1; by_year[yr] += 1
    t = txt or ''
    chars_total += len(t)
    if not t:
        continue
    if allcaps_row(t):
        skipped_allcaps += 1
        continue
    found = []
    any_self = False
    for m in TAG.finditer(t):
        tag = m.group(1)
        if not is_upper_tag(tag):
            continue
        if not qualifies(tag):
            continue
        if is_self(tag, mem):
            any_self = True
            continue
        found.append((m.start(1), tag, m.end(0)))
    if found:
        b0 = found[0][0]
        chars_flagged += len(t); chars_after += len(t) - b0
        for _, tg, _e in found:
            tagfreq[' '.join(tg.split())] += 1
        by_show_hit[cham] += 1; by_host_hit[host] += 1; by_year_hit[yr] += 1
        flag_rows.append(dict(rowid=rid, member=mem, date=date, show=cham, host=host,
                              package=pkg, ntags=len(found), first_tag=' '.join(found[0][1].split()),
                              first_at=b0, nchars=len(t),
                              chars_after=len(t) - b0, text=t))
    else:
        if any_self:
            self_only += 1
        unflag_rows.append(dict(rowid=rid, member=mem, date=date, show=cham, host=host,
                                package=pkg, nchars=len(t), text=t))

N = len(rows)
F = len(flag_rows)
print()
print('=' * 78)
print('U2 ROW-LEVEL RESULT')
print('=' * 78)
print('INTERVIEW rows                          : %d' % N)
print('rows skipped as ALL-CAPS (not turns)    : %d' % skipped_allcaps)
print('rows FLAGGED (>=1 foreign speaker tag)  : %d  (%.3f%% of all INTERVIEW rows)'
      % (F, 100.0 * F / N))
print('rows carrying ONLY a SELF tag           : %d' % self_only)
print('total foreign tag occurrences           : %d' % sum(tagfreq.values()))
print()
print('characters (INTERVIEW total)            : %d' % chars_total)
print('characters in FLAGGED rows              : %d  (%.3f%% of corpus chars)'
      % (chars_flagged, 100.0 * chars_flagged / chars_total))
print('characters AFTER the first foreign tag  : %d' % chars_after)
print('   as %% of FLAGGED-row characters       : %.2f%%' % (100.0 * chars_after / max(1, chars_flagged)))
print('   as %% of ALL INTERVIEW characters     : %.4f%%' % (100.0 * chars_after / chars_total))
print()
print('--- by show (`chamber`), shows with >=1 hit, sorted by hits ---')
print('%-30s %8s %8s %8s' % ('show', 'rows', 'flagged', 'rate%'))
for sh, h in by_show_hit.most_common():
    print('%-30s %8d %8d %8.3f' % (sh[:30], by_show[sh], h, 100.0 * h / by_show[sh]))
print('  (shows with zero hits: %d of %d distinct shows)'
      % (len(by_show) - len(by_show_hit), len(by_show)))
print()
print('--- by source host (`package` URL host) ---')
print('%-34s %8s %8s %8s' % ('host', 'rows', 'flagged', 'rate%'))
for hs, n in by_host.most_common(24):
    print('%-34s %8d %8d %8.3f' % (hs[:34], n, by_host_hit[hs], 100.0 * by_host_hit[hs] / n))
print()
print('--- by year ---')
print('%-6s %8s %8s %8s' % ('year', 'rows', 'flagged', 'rate%'))
for yr in sorted(by_year):
    print('%-6s %8d %8d %8.3f' % (yr, by_year[yr], by_year_hit[yr],
                                  100.0 * by_year_hit[yr] / by_year[yr]))
print()
print('--- 25 most frequent FOREIGN tags ---')
for i, (tg, n) in enumerate(tagfreq.most_common(25), 1):
    print('%2d. %6d  %s' % (i, n, tg[:70]))
print()
print('distinct foreign tag strings: %d' % len(tagfreq))

# ---------------------------------------------------------------- receipts
with io.open(os.path.join(PK, 'U2_flagged_rows.json'), 'w', encoding='utf-8') as f:
    json.dump([{k: v for k, v in r.items()} for r in flag_rows], f, ensure_ascii=False, indent=1)
print('wrote U2_flagged_rows.json (%d rows)' % F)
with io.open(os.path.join(PK, 'U2_tagfreq.json'), 'w', encoding='utf-8') as f:
    json.dump(tagfreq.most_common(), f, ensure_ascii=False, indent=1)

# seeded graded samples
rnd = random.Random(SEED)
fs = sorted(flag_rows, key=lambda r: r['rowid'])
us = sorted(unflag_rows, key=lambda r: r['rowid'])
samp_f = rnd.sample(fs, 40) if len(fs) >= 40 else fs
samp_u = rnd.sample(us, 40)


def write_sample(name, sample, flagged):
    p = os.path.join(PK, name)
    with io.open(p, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['n', 'rowid', 'member', 'date', 'show', 'first_tag', 'first_at', 'nchars',
                    'GRADE', 'note', 'text'])
        for i, r in enumerate(sample, 1):
            w.writerow([i, r['rowid'], r['member'], r['date'], r['show'],
                        r.get('first_tag', ''), r.get('first_at', ''), r['nchars'], '', '',
                        ' '.join(r['text'].split())])
    print('wrote %s (%d rows)' % (name, len(sample)))


write_sample('U2_flagged_sample40_UNGRADED.csv', samp_f, True)
write_sample('U2_unflagged_sample40_UNGRADED.csv', samp_u, False)
print()
print('seed=%d  sample rowids flagged: %s' % (SEED, [r['rowid'] for r in samp_f]))
print('seed=%d  sample rowids unflagged: %s' % (SEED, [r['rowid'] for r in samp_u]))
print('DONE U2')
