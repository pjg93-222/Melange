# -*- coding: utf-8 -*-
import os as _o,sys as _s;_s.path.insert(0,_o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))));from paths import ROOT as MB_ROOT,DRAFT as MB_DRAFT
"""PRESS FULL-TEXT FETCHER (user 2026-07-04 press campaign: "get it to 85"). Headline-only readers
capped press accuracy twice tonight; the long-form research says body text matters. Fetches every
production article URL (member .gov press releases mostly), extracts main text (all <p> blocks,
capped), caches resumable jsonl. Polite: 0.5s spacing, honest UA, per-URL once.
Usage: python fec/collect/fetch_press_text.py   (resumable; press_text_cache.jsonl)"""
import csv, datetime, io, ipaddress, json, os, re, socket, sys, time, urllib.parse, urllib.request
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
B = MB_ROOT
CACHE = B + r'\press_text_cache.jsonl'
UA = {'User-Agent': 'MelangeSystemsResearchCollector/1.0 (public-records research)'}

# Keep IPv6 as a fallback, but avoid the intermittent Windows/Schannel resets observed on
# otherwise reachable public sites by trying their IPv4 route first.
_SYSTEM_GETADDRINFO = socket.getaddrinfo
def _ipv4_first(host, port, family=0, type=0, proto=0, flags=0):
    rows = _SYSTEM_GETADDRINFO(host, port, family, type, proto, flags)
    return sorted(rows, key=lambda row: row[0] != socket.AF_INET)
socket.getaddrinfo = _ipv4_first


from collect.public_fetch_guard import require_public as _require_public, PublicOnlyRedirects as _PublicOnlyRedirects


_opener = urllib.request.build_opener(_PublicOnlyRedirects)

_MAX_NO_BODY_ATTEMPTS = 3    # a fetched-but-bodyless page is terminal fetched_no_body after this many reads
done = set()
no_body_attempts = {}
if os.path.exists(CACHE):
    for ln in open(CACHE, encoding='utf-8'):
        try:
            row = json.loads(ln)
            if (len((row.get('text') or '').split()) >= 20 or
                    row.get('classification') in ('out_of_scope_nonarticle_video', 'fetched_no_body')):
                done.add(row['url'])
            elif row.get('no_body'):
                no_body_attempts[row['url']] = max(no_body_attempts.get(row['url'], 0), int(row.get('attempts') or 1))
        except Exception: pass
arts = list(csv.DictReader(io.open(os.path.join(MB_DRAFT, 'cu_press_stance_tone.csv'), encoding='utf-8-sig', newline='')))
todo = [r for r in arts if (r.get('url') or '').strip() and (r.get('url') or '').strip() not in done]
print('articles: %d | cached %d | to fetch %d' % (len(arts), len(done), len(todo)))

def extract(html):
    html = re.sub(r'<script.*?</script>|<style.*?</style>|<nav.*?</nav>|<footer.*?</footer>', ' ', html, flags=re.S | re.I)
    paras = re.findall(r'<p[^>]*>(.*?)</p>', html, flags=re.S | re.I)
    txt = ' '.join(re.sub(r'<[^>]+>', ' ', p) for p in paras)
    import html as H
    txt = H.unescape(txt)
    return re.sub(r'\s+', ' ', txt).strip()[:6000]


class _NoArticleBody(ValueError):
    """The page was FETCHED successfully but carries no extractable article body.
    Only this failure may be classified terminal; a transport failure must stay retryable."""


if os.path.exists(CACHE) and os.path.getsize(CACHE):
    with open(CACHE, 'rb+') as _f:    # a torn last line must not glue onto the first row appended below
        _f.seek(-1, 2)
        if _f.read(1) != b'\n':
            _f.write(b'\n')
cf = io.open(CACHE, 'a', encoding='utf-8')
ok = fail = 0
_MAX_BODY = 8_000_000
for i, r in enumerate(todo):
    u = (r.get('url') or '').strip()
    try:
        _require_public(u)
        with _opener.open(urllib.request.Request(u, headers=UA), timeout=25) as resp:
            raw = resp.read(_MAX_BODY + 1)
            if len(raw) > _MAX_BODY:
                raise ValueError('response too large')    # stays live_retry_failed, i.e. retryable
            try:
                page = raw.decode(resp.headers.get_content_charset() or 'utf-8', 'replace')
            except LookupError:
                page = raw.decode('utf-8', 'replace')
            body = extract(page)
        if len(body.split()) < 20:
            raise _NoArticleBody('HTTP response contained no extractable article body')
        cf.write(json.dumps({'url': u, 'text': body, 'n': len(body)}, ensure_ascii=True) + '\n')
        ok += 1
    except Exception as e:
        # The terminal classification is what audit_collection.audit_press counts as RESOLVED and
        # what the resume set at the top of this file treats as permanently done, so a DNS/429/
        # timeout failure must never earn it -- only a page we read and found bodyless.
        no_body = isinstance(e, _NoArticleBody)
        attempts = 0
        if no_body:    # only reads that returned a bodyless page count; transport failures never do
            attempts = no_body_attempts.get(u, 0) + 1
            no_body_attempts[u] = attempts
        if no_body and re.search(r'/(?:news/)?videos?/watch/', u, flags=re.I):
            classification = 'out_of_scope_nonarticle_video'
        elif no_body and attempts >= _MAX_NO_BODY_ATTEMPTS:
            classification = 'fetched_no_body'
        else:
            classification = 'live_retry_failed'
        row_out = {
            'url': u,
            'text': '',
            'err': str(e)[:80],
            'classification': classification,
            'attempted_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        if no_body:
            row_out['no_body'] = True
            row_out['attempts'] = attempts
        cf.write(json.dumps(row_out, ensure_ascii=True) + '\n')
        if classification == 'live_retry_failed':    # terminal classifications no longer force exit 2
            fail += 1
    if (i + 1) % 100 == 0:
        cf.flush(); print('  %d/%d (ok %d, fail %d)' % (i + 1, len(todo), ok, fail), flush=True)
    time.sleep(0.5)
cf.close()
print('done: %d fetched, %d failed -> press_text_cache.jsonl' % (ok, fail))
if fail:
    sys.exit(2)
