# -*- coding: utf-8 -*-
import os as _o,sys as _s;_s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__)));from paths import ROOT as MB_ROOT  # centralized root
"""SIGNED MEMBER-REFERENCE LAYER (user-directed 2026-07-04: "see who they are referencing... in press
articles and transcripts or re-tweet their colleagues... either negatively or positively" + "not
formalities, like actual substantive mentions").

Extraction: every reference to ANOTHER roster member inside a member's OWN words — floor speech,
hearings, interviews (speeches table), press headlines, and X mentions/RTs. Attribution uses the
QA2-hardened rules (accent transliteration, first-name compatibility, no unique-surname guessing
without a title). SELF-references excluded.

FORMALITY DISCIPLINE (the user's explicit rule): chamber courtesy is NOISE. Two stages:
  1. Free regex prefilter drops pure ritual ("I yield to...", "I thank the gentleman from...",
     recognition/colloquy boilerplate) when the window carries no evaluative content.
  2. Fable classifies every surviving mention: positive / negative / neutral-substantive / FORMALITY
     — and formality is DISCARDED. Only substantive references enter the layer.
Cost control: per-dyad-per-source cap (newest first) for the scored pass; raw counts kept for all.
Modes:
  python member_reference_layer.py --probe          # free: extraction + prefilter volume + cost estimate
  python member_reference_layer.py --score [--go]   # Fable valence pass (cost-gated), writes member_references.json
Output: member_references.json {edges:[{a,b,n_raw,n_scored,pos,neg,neu,net,sources{},examples[]}]}"""
import csv, hashlib, io, json, os, re, sqlite3, sys, time, collections, unicodedata
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
B = MB_ROOT
DYAD_CAP = int(os.environ.get('REF_DYAD_CAP', '4'))     # scored contexts per (a->b, source)
MODEL = 'claude-fable-5'
CACHE = B + r'\member_reference_cache_fable.jsonl'

C = {m['member']: m for m in json.load(open(B + r'\congestion.json'))}

def norm(s):
    s = unicodedata.normalize('NFD', s); s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z ]", '', s.lower()).strip()

# reference patterns: title+surname (any roster surname, resolved only if unique) OR full first+last
SUR = collections.defaultdict(list)
for m in C: SUR[norm(m).split()[-1]].append(m)
FULLSET = {}
for m in C:
    p = norm(m).split()
    if len(p) >= 2: FULLSET[(p[0], p[-1])] = m
TITLE_RE = r'(?:senator|sen\.|representative|rep\.|congressman|congresswoman|speaker|leader|chairman|chairwoman|ranking member)'
SURNAMES = sorted({norm(m).split()[-1] for m in C}, key=len, reverse=True)
REF_RE = re.compile(r'\b(' + TITLE_RE + r')\s+([a-z]+(?:\s[a-z]+)?)|\b([a-z]+)\s([a-z\'\-]+)\b', re.I)

# stage-1 ritual prefilter: window is PURE formality if it matches ritual AND has no evaluative token
RITUAL = re.compile(r'\b(i yield|yield(s|ing)? (to|back)|i thank (the|my|senator|rep)|thank the (gentleman|gentlewoman|gentlelady|chair)|'
                    r'(gentleman|gentlewoman|gentlelady) from|i recognize|is recognized|i join .{0,40} in (recogniz|celebrat|honor|wish)|'
                    r'colloquy|unanimous consent|i ask .{0,30} to join|pursuant to|the clerk|quorum|i reserve)\b', re.I)
EVALUATIVE = re.compile(r'\b(wrong|right|great|dangerous|disastrous|brilliant|leadership|fail|failed|courage|proud|disgrace|'
                        r'attack|defend|oppose|support|fight|betray|hero|corrupt|honest|lie|lying|truth|gut|destroy|save|'
                        r'protect|reckless|smart|effective|partner|friend|mentor|extremis|radical|principled|bipartisan)\b', re.I)

def resolve_ref(text_l, speaker):
    """Yield (member, char_pos) references found in lowercase text. Conservative: title+unique-surname
    or full first+last (first-name-compatible)."""
    out = []
    # title + name form
    for m in re.finditer(r'\b' + TITLE_RE + r'\s+([a-zÀ-ɏ\'\-]+(?:\s[a-zÀ-ɏ\'\-]+)?)', text_l):
        cand = norm(m.group(1))
        parts = cand.split()
        if not parts: continue   # accent/punctuation-only capture normalizes to empty
        hit = None
        if len(parts) == 1:
            cs = SUR.get(parts[0], [])
            if len(cs) == 1: hit = cs[0]
        else:
            hit = FULLSET.get((parts[0], parts[-1]))
            if not hit:
                cs = SUR.get(parts[-1], [])
                if len(cs) == 1 and (norm(cs[0]).split()[0].startswith(parts[0]) or parts[0].startswith(norm(cs[0]).split()[0])):
                    hit = cs[0]
        if hit and hit != speaker: out.append((hit, m.start()))
    # bare full-name form (First Last exact)
    for (fn, ln), mem in FULLSET.items():
        if mem == speaker: continue
        for m in re.finditer(r'\b' + re.escape(fn) + r'\s+' + re.escape(ln) + r'\b', text_l):
            out.append((mem, m.start()))
    # dedupe by (member, pos//80)
    seen = set(); res = []
    for mem, pos in out:
        k = (mem, pos // 80)
        if k not in seen: seen.add(k); res.append((mem, pos))
    return res

def extract():
    """All (speaker -> referenced, source, date, window) mentions passing the ritual prefilter."""
    refs = []
    con = sqlite3.connect(B + r'\social_media.db', timeout=120)
    for spk, date, src, text in con.execute("SELECT member, date, source, text FROM speeches"):
        if spk not in C or not text: continue
        tl = ' ' + text.lower() + ' '
        for mem, pos in resolve_ref(tl, spk):
            w = text[max(0, pos - 170):pos + 200]
            if RITUAL.search(w) and not EVALUATIVE.search(w): continue   # pure formality -> drop free
            refs.append({'a': spk, 'b': mem, 'src': src, 'date': date or '', 'w': re.sub(r'\s+', ' ', w).strip()})
    con.close()
    # press headlines: member A's article naming member B
    src = os.path.join(os.path.dirname(B), 'Draft Systems', 'cu_press_stance_tone.csv')
    if os.path.exists(src):
        for r in csv.DictReader(io.open(src, encoding='utf-8-sig', newline='')):
            spk = r.get('member'); t = (r.get('title') or '')
            if spk not in C or not t: continue
            tl = ' ' + t.lower() + ' '
            for mem, pos in resolve_ref(tl, spk):
                refs.append({'a': spk, 'b': mem, 'src': 'PRESS', 'date': r.get('date') or '', 'w': t[:300]})
    # X original-post mentions (framed text; plain RTs counted separately as endorsement events)
    try:
        import openpyxl
        con2 = sqlite3.connect(B + r'\social_media.db', timeout=120)
        h2m = {}
        bio2name = {C[m]['bioguide']: m for m in C if C[m].get('bioguide')}
        for bio, tw in con2.execute("SELECT bioguide,twitter FROM members WHERE twitter IS NOT NULL AND twitter!=''"):
            if bio in bio2name: h2m[tw.lower().lstrip('@')] = bio2name[bio]
        con2.close()
        ws = openpyxl.load_workbook(B + r'\Quorum Processed.xlsx', read_only=True)['Members']
        hdr = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
        im, ic, irt, idt = hdr.index('member'), hdr.index('Content'), hdr.index('is_rt'), hdr.index('dt') if 'dt' in hdr else None
        for row in ws.iter_rows(min_row=2, values_only=True):
            spk = row[im]; t = str(row[ic] or '')
            if spk not in C or not t or str(row[irt]).lower() in ('1', 'true'): continue
            for h in re.findall(r'@(\w+)', t):
                mem = h2m.get(h.lower())
                if mem and mem != spk:
                    refs.append({'a': spk, 'b': mem, 'src': 'X', 'date': str(row[idt] or '') if idt is not None else '', 'w': t[:300]})
    except Exception as e:
        print('  (X mention pass skipped: %s)' % str(e)[:80])
    return refs

SYSTEM = """You judge how a member of Congress references a COLLEAGUE in their own words. Given a text window
where SPEAKER mentions TARGET, classify the reference:
  * positive  — praise, endorsement, credit, alliance, defending the target ("Senator X's leadership on this
    bill", "I'm proud to partner with...", co-authorship framed with approval)
  * negative  — criticism, attack, blame, mockery, opposing the target's position or character
  * neutral-substantive — a real policy interaction without clear valence ("Senator X's amendment changes
    the threshold to 3%") — substantive but neither praise nor attack
  * formality — chamber courtesy/procedure only: yields, thanks-the-gentleman, recognition, colloquy setup,
    ceremonial co-mentions with NO evaluative or substantive content. When in doubt between formality and
    neutral-substantive, choose formality.
Judge only the SPEAKER's expressed attitude toward the TARGET in this window."""
SCHEMA = {"type": "object",
          "properties": {"cls": {"type": "string", "enum": ["positive", "negative", "neutral-substantive", "formality"]},
                         "reason": {"type": "string"}},
          "required": ["cls", "reason"], "additionalProperties": False}

if '--probe' in sys.argv:
    t0 = time.time()
    refs = extract()
    by_src = collections.Counter(r['src'] for r in refs)
    dyads = collections.Counter((r['a'], r['b']) for r in refs)
    # scored set under the dyad cap
    bykey = collections.defaultdict(list)
    for r in refs: bykey[(r['a'], r['b'], r['src'])].append(r)
    n_scored = sum(min(DYAD_CAP, len(v)) for v in bykey.values())
    print('substantive-candidate references: %d (post ritual-prefilter) in %.0fs' % (len(refs), time.time() - t0))
    print('  by source: %s' % dict(by_src))
    print('  directed dyads: %d | dyads with 3+ refs: %d' % (len(dyads), sum(1 for v in dyads.values() if v >= 3)))
    print('  to score under DYAD_CAP=%d: %d contexts | est Fable cost ~$%.2f' % (DYAD_CAP, n_scored, n_scored * 0.006))
    for r in refs[:6]:
        print('  eg [%s] %s -> %s | %s...' % (r['src'], r['a'].split()[-1], r['b'].split()[-1], r['w'][:90]))
    sys.exit(0)

if '--score' in sys.argv:
    if not os.environ.get('ANTHROPIC_API_KEY'):
        _kf = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'anthropic_key.txt')
        if os.path.exists(_kf): os.environ['ANTHROPIC_API_KEY'] = open(_kf).read().strip()
    import anthropic, threading
    from concurrent.futures import ThreadPoolExecutor, as_completed
    client = anthropic.Anthropic(); lock = threading.Lock()
    refs = extract()
    bykey = collections.defaultdict(list)
    for r in refs: bykey[(r['a'], r['b'], r['src'])].append(r)
    todo_all = []
    for k, v in bykey.items():
        v.sort(key=lambda r: r['date'], reverse=True)
        todo_all.extend(v[:DYAD_CAP])
    cache = {}
    if os.path.exists(CACHE):
        for ln in open(CACHE, encoding='utf-8'):
            try: d = json.loads(ln); cache[d['k']] = d['out']
            except Exception: pass
    def key(r): return hashlib.md5((r['a'] + '|' + r['b'] + '|' + r['w'][:200]).encode('utf-8', 'replace')).hexdigest()
    todo = [r for r in todo_all if key(r) not in cache]
    print('scored set: %d | cached %d | to classify %d | est ~$%.2f' % (len(todo_all), len(todo_all) - len(todo), len(todo), len(todo) * 0.006))
    if todo and '--go' not in sys.argv: print('COST GATE: add --go to spend.'); sys.exit(0)
    def work(r):
        try:
            resp = client.messages.create(model=MODEL, max_tokens=400,
                output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
                system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": "SPEAKER: %s\nTARGET: %s\nWindow: %s\n(reason under 10 words)" % (r['a'], r['b'], r['w'][:400])}])
            return r, json.loads(next(b.text for b in resp.content if b.type == 'text')), None
        except Exception as e:
            return r, None, (str(e)[:100] or type(e).__name__)
    done = errs = 0
    if todo:
        cf = io.open(CACHE, 'a', encoding='utf-8')
        with ThreadPoolExecutor(max_workers=int(os.environ.get('REF_WORKERS', '8'))) as ex:
            for f in as_completed([ex.submit(work, r) for r in todo]):
                r, out, err = f.result()
                with lock:
                    done += 1
                    if err or not out: errs += 1
                    else: cache[key(r)] = out; cf.write(json.dumps({'k': key(r), 'out': out}, ensure_ascii=True) + '\n')
                    if done % 500 == 0 or done == len(todo): print('  %d/%d (%d errors)' % (done, len(todo), errs), flush=True)
        cf.close()
    edges = collections.defaultdict(lambda: {'n_raw': 0, 'n_scored': 0, 'pos': 0, 'neg': 0, 'neu': 0, 'form': 0,
                                             'sources': collections.Counter(), 'examples': []})
    for r in refs: edges[(r['a'], r['b'])]['n_raw'] += 1; edges[(r['a'], r['b'])]['sources'][r['src']] += 1
    for r in todo_all:
        o = cache.get(key(r))
        if not o: continue
        e = edges[(r['a'], r['b'])]; e['n_scored'] += 1
        c = o['cls']
        if c == 'positive': e['pos'] += 1
        elif c == 'negative': e['neg'] += 1
        elif c == 'neutral-substantive': e['neu'] += 1
        else: e['form'] += 1
        if c in ('positive', 'negative') and len(e['examples']) < 2:
            e['examples'].append({'cls': c, 'w': r['w'][:200], 'src': r['src']})
    out_edges = []
    for (a, b), e in edges.items():
        sub = e['pos'] + e['neg'] + e['neu']
        if sub == 0: continue                      # formality-only dyads never enter the layer
        out_edges.append({'a': a, 'b': b, 'n_raw': e['n_raw'], 'n_scored': e['n_scored'],
                          'pos': e['pos'], 'neg': e['neg'], 'neu': e['neu'], 'formality_dropped': e['form'],
                          'net': round((e['pos'] - e['neg']) / max(1, sub), 3),
                          'sources': dict(e['sources']), 'examples': e['examples']})
    out_edges.sort(key=lambda x: -(x['pos'] + x['neg'] + x['neu']))
    from moneyball_core import dump_atomic
    dump_atomic({'edges': out_edges, 'dyad_cap': DYAD_CAP, 'model': MODEL,
                 'provenance': 'substantive member references (formality discarded per user 2026-07-04); speeches+press+X; Fable-valenced'},
                B + r'\member_references.json')
    npos = sum(1 for e in out_edges if e['net'] > 0.2); nneg = sum(1 for e in out_edges if e['net'] < -0.2)
    print('member_references.json: %d substantive directed edges | positive %d | negative %d' % (len(out_edges), npos, nneg))
    sys.exit(0)

print('usage: member_reference_layer.py [--probe | --score [--go]]')
