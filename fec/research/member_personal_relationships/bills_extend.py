"""Extend the member-relationships lane's dated bill history to the 115th Congress.

STATUS: EXPLORATORY. Writes only under
outputs/member_personal_relationships/20260911_full_history_115_119. Never edits or
re-derives an existing artifact: the 116-119 rows in the output file are byte-identical
lines copied verbatim from 20260910_full_history/bills.ndjson, never re-parsed.

Two layers are mirrored, both checked against the real production code first rather than
assumed:

  Layer 1 (BILLSTATUS XML -> raw bill dict) mirrors
  fec/research/cosponsor_challengers/audit_data.py's date()/text()/parse_bill(),
  REIMPLEMENTED line-by-line rather than imported. audit_data.py does have an
  `if __name__ == "__main__": run()` guard, and its module-level code (ROOT/OUT/RAW/
  FINANCE) is plain Path/env/set construction with no I/O, so importing it would not by
  itself run anything. It was still not imported: fec/research/cosponsor_challengers has
  no __init__.py, so a package-relative import of a sibling research lane from here is
  untested territory, and the task that produced this file explicitly sanctioned mirroring
  as the fallback. The self-check this module runs against real 116-119 data (see
  self_check()) is what actually proves the mirror is faithful, not this paragraph.

  Layer 2 (raw bill dict -> the lane's actual final row schema: key, congress, chamber,
  sponsor, introduced, end, title, area, joins, withdrawals, original, size, updated, url)
  mirrors the per-bill body of history_work.read_history() -- discovered by reading
  prepare_history.py (which builds 20260910_full_history/bills.ndjson from
  outputs/cosponsor_challengers_20260905/bills.jsonl via read_history()) and confirmed
  against real rows. It is REIMPLEMENTED here (as reshape(), below) because
  read_history() hardcodes `116 <= congress <= 119` and congress 115 must pass; the two
  congress-agnostic helpers it calls, congress_end() and served_on(), are IMPORTED
  unmodified from .history_work (its docstring says "Import-safe"; it has no __main__ and
  performs no I/O at import time) so the 115th rows use exactly the same end-date formula
  and dated-service check as production, rather than a hand-copied approximation of them.

Run: `python -m fec.research.member_personal_relationships.bills_extend` with
PYTHONPATH set to the repo root.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
import sys
import time
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from .data import ROOT, read_json, write_json, digest
from .history_work import congress_end, served_on

OUTPUTS = ROOT / 'outputs/member_personal_relationships'
HISTORY = OUTPUTS / '20260910_full_history'
OUT = OUTPUTS / '20260911_full_history_115_119'
RAW = Path(os.environ['LOCALAPPDATA']) / 'Melange/lda_rebuild/raw'
CUTOFF = '2026-09-10'  # matches the cutoff frozen into the copied 116-119 rows

FINAL_ROW_FIELDS = ('key', 'congress', 'chamber', 'sponsor', 'introduced', 'end', 'title',
                     'area', 'joins', 'withdrawals', 'original', 'size', 'updated', 'url')


def _emitter():
    try:
        from fec.surfaces.glassbox_emit import emit, new_run_id
        return emit, new_run_id
    except ImportError:
        import importlib.util
        spec = importlib.util.spec_from_file_location('glassbox_emit', ROOT / 'fec/surfaces/glassbox_emit.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.emit, module.new_run_id


EMIT, NEW_RUN_ID = _emitter()


def event(kind, status, summary, run_id, stage='', detail='', duration_ms=-1, metadata=None):
    EMIT(kind, status, summary, run_id=run_id, lane='claude',
         source='member-personal-relationships-bills-extend', stage=stage, detail=detail,
         duration_ms=int(duration_ms), metadata=metadata)


# ---------------------------------------------------------------- layer 1: raw XML parse
# Mirrors audit_data.date()/text()/parse_bill() line-by-line. See module docstring.

def _date(value):
    value = str(value or '').strip()
    for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%Y/%m/%d'):
        try:
            return dt.datetime.strptime(value[:10] if fmt == '%Y-%m-%d' else value, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def _text(node, path, default=''):
    return node.findtext(path, default=default).strip()


_FINANCE = {'HSBA', 'SSBK', 'HSAG', 'SSAF'}


def _parse_bill(payload):
    root = ET.fromstring(payload)
    b = root if root.tag == 'bill' else root.find('bill')
    if b is None:
        raise ValueError('missing bill root')
    introduced = _date(_text(b, 'introducedDate'))
    committees = []
    for c in b.findall('committees/item'):
        for a in c.findall('activities/item'):
            committees.append({'code': _text(c, 'systemCode').upper().removesuffix('00'),
                               'date': _date(_text(a, 'date')), 'activity': _text(a, 'name')})
    titles = [{'text': _text(t, 'title'), 'kind': _text(t, 'titleType'),
               'updated': _date(_text(t, 'updateDate'))} for t in b.findall('titles/item')
              if 'as introduced' in _text(t, 'titleType').lower()]
    cosponsors = [{'member': _text(c, 'bioguideId'), 'date': _date(_text(c, 'sponsorshipDate')),
                   'original': _text(c, 'isOriginalCosponsor').lower() == 'true',
                   'withdrawn': _date(_text(c, 'sponsorshipWithdrawnDate'))}
                  for c in b.findall('cosponsors/item')]
    actions = [{'date': _date(_text(a, 'actionDate')), 'code': _text(a, 'actionCode'),
                'type': _text(a, 'type'), 'text': _text(a, 'text')}
               for a in b.findall('actions/item')]
    congress = int(_text(b, 'congress'))
    kind = (_text(b, 'type') or _text(b, 'billType')).lower()
    number_value = _text(b, 'number') or _text(b, 'billNumber')
    if not number_value:
        raise ValueError(f"Missing number; root children: {[(x.tag, (x.text or '')[:60]) for x in b]}")
    number = int(number_value)
    return {'key': f'{congress}:{kind}:{number}', 'congress': congress, 'type': kind,
            'number': number, 'introduced': introduced, 'chamber': _text(b, 'originChamber'),
            'sponsor': _text(b, 'sponsors/item/bioguideId'), 'cosponsors': cosponsors,
            'committees': committees, 'titles': titles, 'policy_area': _text(b, 'policyArea/name'),
            'actions': actions, 'updated': _date(_text(b, 'updateDate')),
            'finance_at_introduction': any(c['code'] in _FINANCE and c['date'] == introduced
                                            and c['activity'].lower() == 'referred to' for c in committees)}


def parse_zip_bills(path, expected_congress, expected_kind):
    """Parse every bill XML in one BILLSTATUS zip into layer-1 raw dicts.

    Mirrors audit_data.run()'s per-zip loop, including its pre/post digest equality guard
    (the zip must not change while being read) and its per-bill congress/kind assertion.
    """
    before = digest(path)
    rows = []
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if not name.lower().endswith('.xml'):
                continue
            b = _parse_bill(archive.read(name))
            if not (b['congress'] == expected_congress and b['type'] == expected_kind):
                raise AssertionError(f'{path}:{name} parsed as {b["congress"]}:{b["type"]}, '
                                      f'expected {expected_congress}:{expected_kind}')
            rows.append(b)
    if digest(path) != before:
        raise RuntimeError(f'Input changed during extraction: {path}')
    return rows


# ------------------------------------------------------------ layer 2: reshape to lane row
# Mirrors the body of history_work.read_history() (per-bill reshape + duplicate-key dedup),
# generalized to accept an explicit congress range instead of the hardcoded 116..119.
# congress_end() and served_on() are the unmodified functions imported from .history_work.

def reshape(raw_rows, members, cutoff, congress_low, congress_high):
    seen = {}
    audit = collections.Counter()
    for b in raw_rows:
        audit['source_records'] += 1
        if not congress_low <= b['congress'] <= congress_high or b['introduced'] > cutoff:
            audit['outside_congress_or_cutoff'] += 1
            continue
        key = b['key']
        if key in seen:
            audit['duplicate_bill_records'] += 1
            if (seen[key].get('updated') or '') > (b.get('updated') or ''):
                continue
        seen[key] = b
    bills = []
    for key, b in sorted(seen.items()):
        # Exclusive service end, inclusive data cutoff -- identical to read_history().
        end = min(congress_end(b['congress']),
                  dt.date.fromordinal(dt.date.fromisoformat(cutoff).toordinal() + 1).isoformat())
        valid = {}
        withdrawal = {}
        original = set()
        for c in b['cosponsors']:
            who, joined = c['member'], c.get('date')
            if not joined or not b['introduced'] <= joined < end:
                audit['invalid_or_post_cutoff_join'] += 1
                continue
            if who == b['sponsor']:
                audit['self_signature'] += 1
                continue
            if who in members and not served_on(members[who], joined, b['chamber']):
                audit['join_outside_dated_service'] += 1
                continue
            valid[who] = min(joined, valid.get(who, joined))
            if c.get('original'):
                original.add(who)
            withdrawn = c.get('withdrawn')
            if withdrawn and joined <= withdrawn < end:
                withdrawal[who] = withdrawn
        title = next((t['text'] for t in b['titles'] if t['kind'].startswith('Short Title')), None)
        title = title or next((t['text'] for t in b['titles'] if t['kind'] == 'Official Title as Introduced'), '')
        bills.append(dict(key=key, congress=b['congress'], chamber=b['chamber'],
            sponsor=b['sponsor'], introduced=b['introduced'], end=end, title=title,
            area=b.get('policy_area') or 'Unknown', joins=valid, withdrawals=withdrawal,
            original=sorted(original), size=len(valid), updated=b.get('updated'),
            url=f"https://www.congress.gov/bill/{b['congress']}th-congress/"
                f"{'house' if b['type'] == 'hr' else 'senate'}-bill/{b['number']}"))
        audit['joins_after_day_30'] += sum(
            (dt.date.fromisoformat(d) - dt.date.fromisoformat(b['introduced'])).days > 30 for d in valid.values())
        audit['withdrawal_records'] += len(withdrawal)
    audit['included_bills'] = len(bills)
    audit['distinct_title_reintroductions_retained'] = len(bills) - len({(b['sponsor'], b['title'].casefold()) for b in bills})
    audit['bills_by_congress'] = dict(collections.Counter(b['congress'] for b in bills))
    return bills, dict(audit)


# --------------------------------------------------------------------- output composition

def write_output_ndjson(out_path, new_rows, source_bytes):
    """New rows are serialized fresh; the existing 116-119 bytes are copied verbatim
    (never re-parsed or re-serialized) so they stay byte-identical to
    20260910_full_history/bills.ndjson, per the task's hard rule.

    Opened in binary mode deliberately: a text-mode 'w' open defaults to
    newline=None, which on Windows silently rewrites every '\\n' the new rows write as
    '\\r\\n' while the appended source bytes keep their original '\\n' -- a real bug this
    module's own tests caught (see VerbatimCopyTests). The source file on disk uses plain
    '\\n', so binary mode keeps both halves of the file in that same, single convention.
    """
    with out_path.open('wb') as f:
        for row in new_rows:
            f.write((json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8'))
        f.write(source_bytes)


def count_by_congress_and_type(new_rows, existing_lines):
    """{"115": {"hr": N, "s": M}, "116": {...}, ...} across new_rows plus the raw copied
    ndjson lines. Only needs each row's `key` (congress:type:number), so it works
    uniformly over freshly built dicts and untouched source-file lines."""
    counts = collections.defaultdict(collections.Counter)
    for row in new_rows:
        congress, kind, _number = row['key'].split(':')
        counts[congress][kind] += 1
    for line in existing_lines:
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        congress, kind, _number = row['key'].split(':')
        counts[congress][kind] += 1
    return {c: dict(v) for c, v in sorted(counts.items())}


# -------------------------------------------------------------------------- self-check

def rows_equal(a, b):
    diffs = [f for f in FINAL_ROW_FIELDS if a.get(f) != b.get(f)]
    return not diffs, diffs


def load_existing_rows(source_path, congress, kind):
    prefix = f'{congress}:{kind}:'
    rows = {}
    with Path(source_path).open(encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row['key'].startswith(prefix):
                rows[row['key']] = row
    return rows


def self_check(members, cutoff, congress=116, kind='s'):
    """Re-parses one already-shipped BILLSTATUS zip independently of the pipeline that
    produced 20260910_full_history/bills.ndjson, and diffs the result row-for-row against
    the rows actually shipped there. Proves (or disproves) that layers 1+2 above are a
    faithful mirror of production, rather than merely asserting it."""
    zip_path = RAW / f'billstatus{congress}/BILLSTATUS-{congress}-{kind}.zip'
    raw_rows = parse_zip_bills(zip_path, congress, kind)
    mine, _audit = reshape(raw_rows, members, cutoff, congress, congress)
    mine_by_key = {b['key']: b for b in mine}
    theirs_by_key = load_existing_rows(HISTORY / 'bills.ndjson', congress, kind)
    all_keys = sorted(set(mine_by_key) | set(theirs_by_key))
    matching = differing = 0
    only_mine, only_theirs, examples = [], [], []
    for key in all_keys:
        if key not in theirs_by_key:
            only_mine.append(key)
            continue
        if key not in mine_by_key:
            only_theirs.append(key)
            continue
        ok, diffs = rows_equal(mine_by_key[key], theirs_by_key[key])
        if ok:
            matching += 1
        else:
            differing += 1
            if len(examples) < 10:
                examples.append(dict(key=key, diffs=diffs))
    return dict(zip=str(zip_path), congress=congress, kind=kind, compared=len(all_keys),
                matching=matching, differing=differing, only_in_mine_count=len(only_mine),
                only_in_theirs_count=len(only_theirs), only_in_mine=only_mine[:10],
                only_in_theirs=only_theirs[:10], examples=examples)


# ------------------------------------------------------------------------------- main

def main():
    parser = argparse.ArgumentParser(description='Extend the dated bill history to the 115th Congress')
    parser.add_argument('--self-check-congress', type=int, default=116)
    parser.add_argument('--self-check-kind', default='s')
    args = parser.parse_args()

    run_id = NEW_RUN_ID('bills-extend')
    started = time.time()
    event('bills_extend', 'started', 'bills_extend run started', run_id, stage='start',
          metadata=dict(cutoff=CUTOFF))
    try:
        OUT.mkdir(parents=True, exist_ok=True)
        members = read_json(HISTORY / 'members.json')

        hr_zip = RAW / 'billstatus115/BILLSTATUS-115-hr.zip'
        s_zip = RAW / 'billstatus115/BILLSTATUS-115-s.zip'
        hr_raw = parse_zip_bills(hr_zip, 115, 'hr')
        s_raw = parse_zip_bills(s_zip, 115, 's')
        rows_115, audit_115 = reshape(hr_raw + s_raw, members, CUTOFF, 115, 115)
        print(f'Parsed 115th Congress: {len(hr_raw)} hr + {len(s_raw)} s raw bills; '
              f'{len(rows_115)} rows after reshape', flush=True)

        source_path = HISTORY / 'bills.ndjson'
        source_sha_before = digest(source_path)
        source_bytes = source_path.read_bytes()
        if digest(source_path) != source_sha_before:
            raise RuntimeError(f'Input changed during read: {source_path}')
        source_lines = [ln for ln in source_bytes.decode('utf-8').splitlines() if ln.strip()]

        out_path = OUT / 'bills.ndjson'
        write_output_ndjson(out_path, rows_115, source_bytes)

        self_check_result = self_check(members, CUTOFF, args.self_check_congress, args.self_check_kind)
        print(f"Self-check {self_check_result['zip']}: "
              f"{self_check_result['matching']}/{self_check_result['compared']} rows match", flush=True)

        manifest = dict(
            created_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
            run_id=run_id,
            cutoff=CUTOFF,
            counts_by_congress_and_type=count_by_congress_and_type(rows_115, source_lines),
            rows_115_new=len(rows_115),
            rows_116_119_copied=len(source_lines),
            reshape_audit_115=audit_115,
            inputs=dict(
                billstatus115_hr=dict(path=str(hr_zip), sha256=digest(hr_zip), bytes=hr_zip.stat().st_size),
                billstatus115_s=dict(path=str(s_zip), sha256=digest(s_zip), bytes=s_zip.stat().st_size),
                source_ndjson=dict(path=str(source_path), sha256=source_sha_before,
                                    bytes=source_path.stat().st_size)),
            self_check=self_check_result)
        write_json(OUT / 'manifest.json', manifest)

        artifacts = {p.name: digest(p) for p in sorted(OUT.iterdir())
                     if p.is_file() and p.name != 'run_receipt.json'}
        write_json(OUT / 'run_receipt.json', dict(
            finished_utc=dt.datetime.now(dt.timezone.utc).isoformat(), run_id=run_id,
            wall_seconds=time.time() - started, code_sha256=digest(__file__), python=sys.version,
            cutoff=CUTOFF,
            input_sha256=dict(billstatus115_hr=manifest['inputs']['billstatus115_hr']['sha256'],
                               billstatus115_s=manifest['inputs']['billstatus115_s']['sha256'],
                               source_ndjson=source_sha_before),
            rows_115_new=len(rows_115), rows_116_119_copied=len(source_lines),
            self_check_congress=args.self_check_congress, self_check_kind=args.self_check_kind,
            self_check_matching=self_check_result['matching'],
            self_check_differing=self_check_result['differing'],
            self_check_compared=self_check_result['compared'],
            development_only=True, held_out_split_touched=False, artifacts=artifacts))
    except Exception as exc:
        event('bills_extend', 'failed', f'bills_extend run failed: {exc}', run_id, stage='error',
              duration_ms=(time.time() - started) * 1000)
        raise
    event('bills_extend', 'ok',
          f'bills_extend complete; {len(rows_115)} new 115th rows, '
          f"self-check {self_check_result['matching']}/{self_check_result['compared']}",
          run_id, stage='finish', duration_ms=(time.time() - started) * 1000,
          metadata=dict(rows_115=len(rows_115), self_check=self_check_result['matching']))
    print(f'Wrote {out_path}', flush=True)


if __name__ == '__main__':
    main()
