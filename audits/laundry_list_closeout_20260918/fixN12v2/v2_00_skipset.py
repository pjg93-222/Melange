# -*- coding: utf-8 -*-
"""N12-v2 SKIP-SET BUILDER.  READ-ONLY.

Builds the two rowid sets the v2 migration must never touch, INDEPENDENTLY of which rows the
detector flags (v1's inventory was intersected with v1's flagged set; v2 needs the whole set):

  (b) LABEL-BOUND rows -- any hand label, gold item, identity contract or reviewed record points
      at the row.  Families, exactly the ones v1's inventory found
      (audits/laundry_list_closeout_20260918/fixN12/label_safety_rowid_collisions.json):
        data/speech/source_media_*.jsonl                 (text_sha256 / identity_contract /
                                                          speaker_identity_status records)
        data/speech/speech_descriptive_clip_cache.jsonl
        outputs/member_personal_relationships/**/*.ndjson|*.json
        C:\\melange-data\\member_clips\\clips_manifest*.jsonl   (clip manifests)
        data/stance/*gold*                                (read for rowid refs; the CU gold queue
                                                           is keyed by content hash, so it is
                                                           covered by (c) as well)
  (c) CU-EXTRACT rows -- every row the LIVE interview CU stance channel currently reads.
      fec/stance/extract_cu_interviews.py (read as TEXT, never imported: it WRITES two files at
      import time) selects with
          date >= '2009-01-01' AND source = 'INTERVIEW' AND (lower(text) LIKE '%<kw>%' OR ...)
          ORDER BY date, member, package, nwords, substr(text,1,120), rowid
      and emits one CSV row per surviving CU passage.  Truncation can only REMOVE text, so a row
      outside that gate can never gain a passage and can never enter the ordered set; a row inside
      it can lose one.  Skipping every row inside the gate therefore makes interviews_cu.csv --
      and everything downstream of it: interview_gold_queue.csv, interview_stance_final.csv, the
      desk's <=37 displayed CU snips -- byte-identical after the migration.  That is a SUPERSET of
      "the row yields a CU passage today" and is provable without importing the producer.

Writes only into this packet directory.
"""
import collections
import csv
import glob
import io
import json
import os
import re
import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
LIVE = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
DB = os.path.join(LIVE, 'social_media.db')
CLIPS_DIR = r'C:\melange-data\member_clips'

# extract_cu_interviews.py:32 and :39-42, copied character for character from the live file.
CU_MINDATE = '2009-01-01'
CU_KEYWORDS = ['cfpb', 'consumer financial protection', 'financial protection', 'consumer bureau',
               'credit union', 'interchange', 'swipe fee', 'credit card competition', 'ncua',
               'durbin', 'durbin amendment', 'field of membership', 'member business lending',
               'overdraft', 'junk fee', 'chopra', 'payday', 'medical debt']


def open_ro(path):
    con = sqlite3.connect('file:%s?mode=ro' % path.replace('\\', '/'), uri=True, timeout=300)
    con.execute('PRAGMA query_only=ON')
    return con


def verify_keywords_against_live():
    """The gate is only sound if it is the LIVE producer's gate.  Read it as text and compare."""
    src = io.open(os.path.join(LIVE, 'fec', 'stance', 'extract_cu_interviews.py'),
                  encoding='utf-8').read()
    m = re.search(r'^KEYWORDS = (\[.*?\])\n\n', src, re.S | re.M)
    kw = eval(m.group(1)) if m else None
    md = re.search(r"^MINDATE = '([^']+)'", src, re.M)
    return kw == CU_KEYWORDS, (md.group(1) if md else None) == CU_MINDATE, kw


ROWID_KEYS = ('source_rowid', 'speech_rowid', 'rowid', 'speeches_rowid', 'row_id')
LOCATOR_KEYS = ('source_locator', 'turn_id', 'transcript_path', 'locator', 'source_ref',
                'source_id', 'provenance')
LOC_RX = re.compile(r'(?:rowid=|speeches:|speeches/|speeches#)(\d{1,9})')

# The contract's qualifier for rule (b): "ANY hand label, gold item, identity contract or REVIEWED
# record points at the row ... member_personal_relationships records with a review_status or
# excerpt offsets".  A record that carries one of these is a HAND artefact; a bare mined candidate
# is not.  Both sets are emitted: STRICT is the operative rule, WIDE is the superset Paul can pick
# instead (it costs repair coverage, it cannot cost safety).
LABEL_FIELDS = ('review_status', 'reviewer', 'reviewed_at', 'reviewed_by', 'decision', 'grade',
                'gold_stance', 'gold', 'label', 'hand_label', 'use_as_relationship_label',
                'identity_contract', 'speaker_identity_status', 'text_sha256',
                'excerpt_start', 'excerpt_end', 'adjudication', 'verdict', 'clip_id',
                'clip_path', 'speaker_verified')


def is_labelled(rec):
    return isinstance(rec, dict) and any(
        rec.get(k) not in (None, '', [], {}) for k in LABEL_FIELDS)


def rowids_from_record(rec):
    out = set()
    if not isinstance(rec, dict):
        return out
    for k in ROWID_KEYS:
        v = rec.get(k)
        if isinstance(v, int):
            out.add(v)
        elif isinstance(v, str) and v.strip().isdigit():
            out.add(int(v))
        elif isinstance(v, list):
            for x in v:
                if isinstance(x, int):
                    out.add(x)
                elif isinstance(x, str) and x.strip().isdigit():
                    out.add(int(x))
    for k in LOCATOR_KEYS:
        v = rec.get(k)
        if isinstance(v, str):
            out.update(int(g) for g in LOC_RX.findall(v))
        elif isinstance(v, dict):
            out.update(rowids_from_record(v))
    return out


def _take(rec, wide, strict):
    ids = rowids_from_record(rec)
    wide |= ids
    if ids and is_labelled(rec):
        strict |= ids


def scan_jsonish(path):
    """(wide, strict, n_records) rowids referenced by one .jsonl/.ndjson/.json artifact."""
    wide, strict = set(), set()
    n = 0
    try:
        head = io.open(path, encoding='utf-8', errors='replace').read(4096).lstrip()
    except OSError:
        return wide, strict, 0
    if head.startswith('['):
        try:
            data = json.load(io.open(path, encoding='utf-8', errors='replace'))
        except ValueError:
            return wide, strict, 0
        for rec in (data if isinstance(data, list) else [data]):
            n += 1
            _take(rec, wide, strict)
        return wide, strict, n
    if head.startswith('{') and '\n{' not in head[:2000] and path.endswith('.json'):
        try:
            data = json.load(io.open(path, encoding='utf-8', errors='replace'))
        except ValueError:
            data = None
        if isinstance(data, dict):
            n += 1
            _take(data, wide, strict)
            for v in data.values():
                if isinstance(v, list):
                    for rec in v:
                        n += 1
                        _take(rec, wide, strict)
            return wide, strict, n
    with io.open(path, encoding='utf-8', errors='replace') as fh:
        for line in fh:
            line = line.strip()
            if not line.startswith('{'):
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            n += 1
            _take(rec, wide, strict)
    return wide, strict, n


def main():
    kw_ok, date_ok, live_kw = verify_keywords_against_live()
    families = collections.OrderedDict()
    families['data/speech/source_media_*.jsonl'] = sorted(
        glob.glob(os.path.join(LIVE, 'data', 'speech', 'source_media_*.jsonl')))
    families['data/speech/speech_descriptive_clip_cache.jsonl'] = [
        p for p in [os.path.join(LIVE, 'data', 'speech', 'speech_descriptive_clip_cache.jsonl')]
        if os.path.exists(p)]
    families['data/speech/member_interview_*.jsonl'] = sorted(
        glob.glob(os.path.join(LIVE, 'data', 'speech', 'member_interview_*.jsonl')))
    mpr = []
    for ext in ('*.ndjson', '*.json', '*.jsonl'):
        mpr += glob.glob(os.path.join(LIVE, 'outputs', 'member_personal_relationships', '**', ext),
                         recursive=True)
    families['outputs/member_personal_relationships/**'] = sorted(set(mpr))
    families['member_clips/clips_manifest*'] = sorted(
        glob.glob(os.path.join(CLIPS_DIR, 'clips_manifest*.jsonl'))
        + glob.glob(os.path.join(CLIPS_DIR, 'clips_conflicts.jsonl'))
        + glob.glob(os.path.join(CLIPS_DIR, 'clips_rejections.jsonl')))
    families['data/stance gold'] = sorted(
        p for p in glob.glob(os.path.join(LIVE, 'data', 'stance', '*'))
        if os.path.isfile(p) and ('gold' in os.path.basename(p).lower()
                                  or 'interview' in os.path.basename(p).lower())
        and os.path.splitext(p)[1] in ('.json', '.jsonl', '.ndjson', '.csv'))

    wide_rowids, strict_rowids = set(), set()
    per_artifact = []
    for fam, paths in families.items():
        for p in paths:
            if os.path.splitext(p)[1] == '.csv':
                wide, strict, n = set(), set(), 0
                with io.open(p, encoding='utf-8-sig', newline='', errors='replace') as fh:
                    try:
                        rdr = csv.DictReader(fh)
                        cols = [c for c in (rdr.fieldnames or []) if c and 'rowid' in c.lower()]
                        for rec in rdr:
                            n += 1
                            for c in cols:
                                v = (rec.get(c) or '').strip()
                                if v.isdigit():
                                    wide.add(int(v))
                                    strict.add(int(v))   # a hand-label sheet is a hand label
                    except csv.Error:
                        pass
            else:
                wide, strict, n = scan_jsonish(p)
            if wide:
                per_artifact.append({'family': fam,
                                     'artifact': os.path.relpath(p, LIVE)
                                     if p.startswith(LIVE) else p,
                                     'records': n, 'rowids': len(wide),
                                     'labelled_rowids': len(strict)})
            wide_rowids |= wide
            strict_rowids |= strict
    label_rowids = strict_rowids

    con = open_ro(DB)
    iv = {r[0] for r in con.execute("SELECT rowid FROM speeches WHERE source='INTERVIEW'")}
    where = ' OR '.join(['lower(text) LIKE ?'] * len(CU_KEYWORDS))
    params = ['%' + k + '%' for k in CU_KEYWORDS]
    cu = {r[0] for r in con.execute(
        'SELECT rowid FROM speeches WHERE date >= ? AND source = ? AND (' + where + ')',
        [CU_MINDATE, 'INTERVIEW'] + params)}
    n_iv = len(iv)
    n_all = con.execute('SELECT COUNT(*) FROM speeches').fetchone()[0]
    con.close()

    label_iv = label_rowids & iv
    wide_iv = wide_rowids & iv
    out = {
        'live_db': DB, 'db_bytes': os.path.getsize(DB),
        'speeches_rows': n_all, 'interview_rows': n_iv,
        'cu_gate_matches_live_producer': bool(kw_ok and date_ok),
        'cu_keywords': CU_KEYWORDS, 'cu_mindate': CU_MINDATE,
        'cu_rowids': sorted(cu), 'n_cu_rowids': len(cu),
        'label_rowids_interview': sorted(label_iv), 'n_label_rowids_interview': len(label_iv),
        'wide_rowids_interview': sorted(wide_iv), 'n_wide_rowids_interview': len(wide_iv),
        'protected_union_interview': sorted(label_iv | cu),
        'n_protected_union_interview': len(label_iv | cu),
        'protected_union_wide_interview': sorted(wide_iv | cu),
        'n_protected_union_wide_interview': len(wide_iv | cu),
        'per_artifact': sorted(per_artifact, key=lambda d: -d['rowids']),
    }
    p = os.path.join(HERE, 'v2_skipset.json')
    with io.open(p, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1, sort_keys=True)
    print('CU gate reproduces the live producer: keywords=%s mindate=%s' % (kw_ok, date_ok))
    if not kw_ok:
        print('  LIVE KEYWORDS: %r' % (live_kw,))
    print('speeches rows %d ; INTERVIEW rows %d' % (n_all, n_iv))
    print('CU-gate rows (skip rule c)                    : %d' % len(cu))
    print('label-bound INTERVIEW rowids  STRICT (rule b) : %d' % len(label_iv))
    print('label-bound INTERVIEW rowids  WIDE  (superset): %d' % len(wide_iv))
    print('protected union (b|c) STRICT                  : %d' % len(label_iv | cu))
    print('protected union (b|c) WIDE                    : %d' % len(wide_iv | cu))
    print('245771 in CU set: %s ; in strict label set: %s'
          % (245771 in cu, 245771 in label_rowids))
    print()
    print('%-52s %9s %8s %9s' % ('artifact', 'records', 'rowids', 'labelled'))
    for d in out['per_artifact'][:40]:
        print('%-52s %9d %8d %9d'
              % (d['artifact'][-52:], d['records'], d['rowids'], d['labelled_rowids']))
    print('\nwrote %s' % p)


if __name__ == '__main__':
    main()
