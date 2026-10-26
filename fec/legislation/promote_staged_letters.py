# -*- coding: utf-8 -*-
from __future__ import annotations
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))); from paths import ROOT as MB_ROOT  # noqa: E402
"""PROMOTER for staged sign-on letters (brain D-263, lane L). Reads data/legislation/letters/letter_staging.jsonl
(written by collect/collect_signon_letters.py) and appends member rows to manual_bill_evidence.csv.

A letter is promoted only when BOTH gates hold:
  Gate E  status EXACT: an exact signatory list from a primary source (the collector's job);
  Gate C  its category and direction come from ONE named authority, never from a model:
    C1  ACU position: the letter's own text names a one-directional ACU subject (CDFI Fund, CU Tax Status) that the ACU
        snapshot also advocates on (issue tag via L1_CATEGORY_MAP + the subject in an ACU letter title); direction +1 by Paul's
        2026-07-29 precedent for the seven hand-ingested letters (authority L2:acu-letter). Direction is NOT read from the text,
        so C1 fails closed: it needs a positive-advocacy cue in the letter, and an adverse cue holds it (possible_adverse_c1).
    C2  inherited: the letter urges passage/opposition of a named bill that already carries a Category and Direction in the CSV's
        hand-entered bill rows (Paul's authority; the sentinel ledger is an LLM's and is never read); direction = the bill's direction
        times the urge verb. Ambiguity (both verbs, a negation, disagreeing hand rows) fails the gate.
    C3  automated classifier: NOT BUILT (and not stubbed): whether to build it is Paul's call. No model is ever called here.
Held, never promoted: no authority, direction -1 (v1 holds every adverse letter for review), off-topic, NOT_EXACT, duplicates.

Writes: rows appended after the existing bytes (EOL preserved) behind a PRE-LETTERS backup; the tag sidecar first, the CSV
second (see legislation/letter_tags.py for why that order is the safe one); staging statuses; promotion_receipt.json, which
reports auto_letter_accounting COUNTED FROM THE CSV (letter_tags.auto_letter_accounting), the same number the audit pins add to their base.
A malformed CSV/staging or an IO error writes nothing further, prints the reason, and exits 0 (PARTIAL): the chain runs on the
unchanged CSV. Usage: python fec/legislation/promote_staged_letters.py [--dry-run] [--root DIR] [--letters-dir DIR]"""
import argparse, collections, csv, datetime as dt, glob, hashlib, io, json, os, pathlib, re, shutil, sys

import bill_rules as BR
from collect import collect_signon_letters as C
from collect.fetch_acu_letters import L1_CATEGORY_MAP
from legislation import letter_tags as LT

C1_CATEGORIES = ('CDFI Fund', 'CU Tax Status')     # the categories of the 244 + 34 hand-ratified L2:acu-letter rows
AUTH_C1, AUTH_C2 = 'L2:acu-letter', 'L2:letter-names-classified-bill'
ROLE_W = {'sponsor': 1.0, 'original-cosponsor': 0.5}
CUES = {category: cue for category, cue, _ in C.CATEGORY_CUES}
BILL_REF = re.compile(r'\b(H\.?\s?R\.?|S\.?)\s*(\d{1,5})\b')
SENTENCE = re.compile(r'(?<=[a-z0-9)"])[.!?]["\')]?\s+(?=[A-Z])')
URGE = re.compile(r'\b(urg(?:e|es|ed|ing)|call(?:s|ed|ing)? on|ask(?:s|ed|ing)?|request(?:s|ed|ing)?|encourag(?:e|es|ed|ing)|implor\w+)\b', re.I)
SUPPORT = re.compile(r'\b(support(?:s|ing)?|pass(?:age)?|advance|enact(?:ment)?|co-?sponsor\w*|bring \w+ to the floor)\b', re.I)
OPPOSE = re.compile(r'\b(oppos(?:e|es|ed|ing|ition)|reject|defeat|vote against)\b', re.I)
STAGING_FIELDS = ('letter_id', 'status', 'signatories', 'leads', 'congress', 'letter_date', 'recipients', 'sha256', 'document_url', 'retrieved_at',
                  'source_kind', 'closing_found', 'unaccounted_lines')   # gate_e() reads the last three


# ---- Gate C -----------------------------------------------------------------------------------------

def load_acu(root):
    """[{id, title, tags}] of the newest ACU letters snapshot (ACU's own letters; they carry no signatories and no position)."""
    found = sorted(p for p in glob.glob(os.path.join(root, 'source_data', 'acu_letters_snapshot_*.json')) if 'partial' not in p)
    if not found:
        return []
    with open(found[-1], encoding='utf-8') as handle:
        letters = json.load(handle).get('letters', [])
    return [{'id': str(l.get('id')), 'title': l.get('title') or l.get('label') or '',
             'tags': {t.get('label') for t in l.get('fieldAdvocacyIssueTypes') or []}} for l in letters]


def acu_backing(category, acu):
    layers = {layer for layer, categories in L1_CATEGORY_MAP.items() if category in categories}
    return [l['id'] for l in acu if l['tags'] & layers and CUES[category].search(l['title'])][:3]


def c1(letter, acu):
    cats = letter.get('subject_categories') or []
    if not cats or any(c not in C1_CATEGORIES for c in cats):
        return None
    backing = {c: acu_backing(c, acu) for c in cats}
    if not all(backing.values()):
        return None
    return {'category': list(cats), 'direction': 1, 'beneficiary_class': 'cu_primary', 'act_weight': 1.0, 'authority': AUTH_C1,
            'confidence': 0.9, 'acu_backing': backing,
            'rationale': 'ACU advocacy letters exist on this subject (%s): signing a sign-on letter on an ACU-advocated subject is direct CU '
                         'advocacy (Paul directive 2026-07-29, L2:acu-letter precedent). Direction +1 by that precedent, not read from '
                         'the letter text; discovered and promoted by rule.' % '; '.join('%s: ACU %s' % (c, ','.join(i)) for c, i in backing.items())}


def bill_index(rows):
    """({(bill display, congress): {category: {directions}}}, rows skipped) from the hand-entered bill rows of manual_bill_evidence.csv
    ONLY (Paul's authority). The sentinel ledger is deliberately not read: its classifications are an LLM's, and an LLM must not pose
    as L2. bill_directions.csv is not used either (64 of its 126 rows have no category; CFPB:Reduce/Expand is a different scale).
    A row counts when it is active (not excluded by the bill rules, not withdrawn) and its Direction is +1/-1; a malformed row is
    skipped on its own and counted, never allowed to void the index."""
    index, skipped = collections.defaultdict(lambda: collections.defaultdict(set)), 0
    for row in rows:
        bill = (row.get('Bill') or '').strip()
        direction = (row.get('Direction') or '').strip()
        if not bill or bill.upper().startswith('LTR-') or direction in ('', '0'):
            continue                                   # a letter row, or no include-equivalent direction: not a bill classification
        try:
            if direction not in ('+1', '-1'):
                raise ValueError('direction %r' % direction)
            category, congress = BR.canonical_category(row.get('Category')), str(int(float(row['Congress'])))
            if not category:
                continue
            if BR.excluded_bill(bill, congress, row.get('Title') or '', row.get('Summary') or '') or \
                    'withdrawn' in ((row.get('Note') or '') + ' ' + (row.get('LastAction') or '')).lower():
                continue
            index[(bill, congress)][category].add(int(direction))
        except (ValueError, KeyError, TypeError):
            skipped += 1
    return index, skipped


NEGATION = re.compile(r"\b(?:not|no|never|nobody|none|neither|nor|cannot|can't|won't|don't|doesn't|without)\b", re.I)


def c2(letter, bills):
    """(classification, None) | (None, 'c2_ambiguous') | (None, None): inherited from the classified bill(s) the letter urges on."""
    signs, categories = {}, collections.defaultdict(set)
    for sentence in SENTENCE.split(letter.get('body') or ''):
        refs = {('H.R.%d' if m.group(1)[0] in 'Hh' else 'S.%d') % int(m.group(2)) for m in BILL_REF.finditer(sentence)}
        classified = [(r, bills[(r, str(letter['congress']))]) for r in sorted(refs) if (r, str(letter['congress'])) in bills]
        if not classified or not URGE.search(sentence):
            continue
        support, oppose = bool(SUPPORT.search(sentence)), bool(OPPOSE.search(sentence))
        if (support and oppose) or ((support or oppose) and NEGATION.search(sentence)):
            return None, 'c2_ambiguous'              # "do not urge you to support", "not to oppose": the verb's sign is not trustworthy
        if support or oppose:
            for bill, cats in classified:
                if signs.setdefault(bill, 1 if support else -1) != (1 if support else -1):
                    return None, 'c2_ambiguous'
                for category, directions in cats.items():
                    if len(directions) != 1:             # the hand rows disagree about this bill's direction
                        return None, 'c2_ambiguous'
                    categories[category].add(next(iter(directions)) * signs[bill])
    if not categories:
        return None, None
    directions = {d for ds in categories.values() for d in ds}
    if len(directions) != 1 or any(len(ds) != 1 for ds in categories.values()):
        return None, 'c2_ambiguous'
    return {'category': sorted(categories), 'direction': directions.pop(), 'beneficiary_class': 'cu_primary', 'act_weight': 1.0,
            'authority': AUTH_C2, 'confidence': 0.85, 'bills': sorted(signs),
            'rationale': 'The letter urges %s on %s, which already carries this Category and Direction in the evidence ledger.' % (
                'passage' if all(s == 1 for s in signs.values()) else 'opposition', ', '.join(sorted(signs)))}, None


# Lead ruling (2026-10-20): C1 assigns +1 by precedent without reading the letter, so a letter whose own text carries one of these
# phrases is held for review. A hold is conservative; it is not a classification, and it is not applied to C2 (which reads the verb).
ADVERSE_C1_CUES = ('repeal', 'eliminate the exemption', 'end the tax exemption', 'tax credit unions', 'subject credit unions to',
                   'level the playing field',
                   # review ruling 3: hostile or sceptical framings of the subject itself, and the scrutiny a GAO study asks for
                   'defund', 'eliminate the cdfi fund', 'eliminate the fund', 'terminate the cdfi fund', 'abolish',
                   'examine whether', 'remains justified', 'still justified', 'no longer justified', 'continued justification')
# C1 fails CLOSED (review ruling 3): +1 by precedent needs positive evidence in the letter's own words ("support" and the like).
POSITIVE_C1_CUES = re.compile(
    r'\bprotect|\bpreserv|\bsafeguard|\bdefend|\bfully fund|\bstrengthen|\bsupport'
    r'|maintain(?:ing)? (?:the |our )?(?:federal )?(?:credit union )?(?:tax )?exempt'
    r'|(?:oppos|reject)\w* (?:any |all )?(?:effort|attempt|proposal|plan)s? to', re.I)


def _text(letter):
    return re.sub(r'\s+', ' ', ' '.join([letter.get('title') or '', letter.get('body') or ''])).lower()


def possible_adverse(letter):
    text = _text(letter)
    return any(cue in text for cue in ADVERSE_C1_CUES) or ('unfair advantage' in text and 'credit union' in text)


def positive_advocacy(letter):
    return bool(POSITIVE_C1_CUES.search(_text(letter)))


def classify(letter, acu, bills):
    """(classification or None, hold reason or None). C1, then C2. There is no C3."""
    cls = c1(letter, acu)
    why = None
    if cls is not None and possible_adverse(letter):
        return None, 'possible_adverse_c1'     # a hold, not a classification: nothing is recorded as the letter's category or direction
    if cls is not None and not positive_advocacy(letter):
        return None, 'c1_direction_unconfirmed'     # no cue that this letter ADVOCATES for the subject: +1 by precedent is not enough
    if cls is None:
        cls, why = c2(letter, bills)
    if cls is None:
        return None, why or 'no_gate_c_authority'
    return cls, ('adverse_direction_held' if cls['direction'] != 1 else None)


# ---- rows ---------------------------------------------------------------------------------------------

def _one_line(text):
    return re.sub(r'\s+', ' ', text or '').strip()


def letter_rows(letter, cls):
    """One CSV row per (roster signatory, category), in the convention of the hand-ingested letters."""
    leads = set(letter['leads'])
    recipient = _one_line((letter['recipients'] or ['the addressee'])[0])
    sponsors = '; '.join(s['member'] for s in letter['signatories'] if s['bioguide'] in leads)
    rows = []
    for category in cls['category']:
        for s in letter['signatories']:
            if s['bioguide']:
                rows.append({'Member': s['member'], 'Role': 'sponsor' if s['bioguide'] in leads else 'original-cosponsor',
                             'Bill': letter['letter_id'], 'Title': _one_line(letter.get('title')) or 'Sign-on letter to ' + recipient,
                             'Sponsor': sponsors, 'Congress': str(letter['congress']), 'Category': category,
                             'Direction': '%+d' % cls['direction'], 'DecayWeight': repr(BR.congress_decay(letter['congress'])),
                             'LastAction': 'Letter sent %s to %s' % (letter['letter_date'], recipient),
                             'DetailLink': letter['document_url'], 'Summary': _one_line(letter.get('subject')),
                             'Note': 'auto-letter %s sha256=%s via %s; staged %s' % (letter['letter_id'], letter['sha256'][:12],
                                                                                    cls['authority'], letter['retrieved_at'])})
    return rows


# ---- the promotion --------------------------------------------------------------------------------------

def promote_dial(env):
    """LETTERS_PROMOTE: unset / '' / 1 = promote (the default), 0 = the revert switch (the promoter only dry-runs: it reports what it
    would add and writes no CSV row), anything else RAISES. Promotion moves ranks (archive_leg, primacy, say-do caps)."""
    value = (env.get('LETTERS_PROMOTE') or '1').strip()
    if value not in ('0', '1'):
        raise ValueError('LETTERS_PROMOTE must be 0 or 1 (or unset), got %r' % value)
    return value == '1'


STATUS_HELD_LIMIT = 20


def write_status(letters_dir, out, now, dry_run, error=None):
    """promoter_status.json: written by EVERY run (PASS, PARTIAL, dry-run, no-op) so the daily runner can say what the promoter did."""
    status = {'schema': 'letters-promoter-status-v1', 'run_at': now.strftime('%Y-%m-%dT%H:%M:%SZ'), 'dry_run': dry_run,
              'status': out.get('status', 'PARTIAL'), 'error': error or out.get('error'), 'rows_added': out.get('rows_added', 0),
              'promotable': out.get('promotable', 0), 'held_count': len(out.get('held', [])), 'held': out.get('held', [])[:STATUS_HELD_LIMIT],
              'c2_rows_skipped': out.get('c2_rows_skipped'), 'auto_letter_accounting': out.get('auto_letter_accounting')}
    C._atomic_write(os.path.join(letters_dir, 'promoter_status.json'), json.dumps(status, indent=1, sort_keys=True).encode('utf-8'))


def promote(*, root, letters_dir, now, env=None, dry_run=False):
    try:
        out = _promote(root=root, letters_dir=letters_dir, now=now, env=env, dry_run=dry_run)
    except Exception as e:
        try:
            write_status(letters_dir, {'status': 'PARTIAL'}, now, dry_run, error='crash:%s: %s' % (type(e).__name__, str(e)[:120]))
        except OSError:
            pass
        raise
    try:
        write_status(letters_dir, out, now, dry_run)
    except OSError as e:
        out.update(status='PARTIAL', status_write_error=repr(e)[:120])
    return out


def _promote(*, root, letters_dir, now, env=None, dry_run=False):
    env = os.environ if env is None else env
    csv_path = os.path.join(root, 'manual_bill_evidence.csv')
    receipt_path = os.path.join(letters_dir, 'promotion_receipt.json')
    out = {'schema': 'letters-promotion-receipt-v1', 'dry_run': dry_run, 'status': 'PASS', 'rows_added': 0, 'promotable': 0, 'held': []}
    try:
        old = pathlib.Path(csv_path).read_bytes()
        rows = list(csv.DictReader(io.StringIO(old.decode('utf-8-sig'), newline='')))
        if list(csv.reader(io.StringIO(old.decode('utf-8-sig'), newline='')))[0] != list(C.CSV_COLUMNS):
            raise ValueError('manual_bill_evidence.csv header is not the expected 13 columns')
        staging = C.load_staging(letters_dir)
        for rec in staging.values():
            if rec['status'] == 'EXACT' and any(f not in rec for f in STAGING_FIELDS):
                raise ValueError('staging record %s lacks required fields' % rec.get('letter_id'))
        acu = load_acu(root)
        bills, out['c2_rows_skipped'] = bill_index(rows)
        _, bio = C.load_roster(root)
        tags_now = {'%s|%s' % (t['bill'], t['congress']): t for t in LT.read_rows(root)}
    except (OSError, ValueError, KeyError, IndexError) as e:
        out.update(status='PARTIAL', error=repr(e)[:200])
        return out
    have = {(r['Member'], r['Bill'], r['Congress'], r['Category']) for r in rows}
    plan, before = [], {k: json.dumps(v, sort_keys=True) for k, v in staging.items()}
    for key in sorted(staging):
        rec = staging[key]
        if rec['status'] != 'EXACT':
            continue
        if (rec.get('extraction_method') or '').split(':')[-1] != C.RULES_VERSION:
            rec['hold_reason'] = 'stale_extraction_rules'
            out['held'].append({'letter_id': key, 'reason': 'stale_extraction_rules'})
            continue
        gate_e = C.gate_e(rec)       # staging is a file and rules change: Gate E is re-checked here, not trusted from the status
        if gate_e != 'EXACT':
            rec['hold_reason'] = 'gate_e_failed:' + gate_e.split(':', 1)[1]
            out['held'].append({'letter_id': key, 'reason': rec['hold_reason']})
            continue
        cls, why = classify(rec, acu, bills)
        rec['classification'] = cls if cls else rec.get('classification')
        if why:
            rec['hold_reason'] = why
            out['held'].append({'letter_id': key, 'reason': why})
            continue
        letter_rows_all = [r for r in letter_rows(rec, cls) if r['Member'] in bio]
        if not letter_rows_all:
            rec['hold_reason'] = 'no_roster_rows'          # every signer has left the current roster: nothing to write, nothing to tag
            out['held'].append({'letter_id': key, 'reason': 'no_roster_rows'})
            continue
        if BR.excluded_bill(rec['letter_id'], rec['congress'], letter_rows_all[0]['Title'], letter_rows_all[0]['Summary']):
            rec['hold_reason'] = 'excluded_by_bill_rules'     # the desk would drop its rows and the tag would be an extra act
            out['held'].append({'letter_id': key, 'reason': 'excluded_by_bill_rules'})
            continue
        new = [r for r in letter_rows_all if (r['Member'], r['Bill'], r['Congress'], r['Category']) not in have]
        plan.append((rec, cls, letter_rows_all, new))
    out['promotable'] = len(plan)
    new_rows = [r for _, _, _, new in plan for r in new]
    out['rows_added'] = len(new_rows)
    out['auto_letter_accounting'] = LT.auto_letter_accounting(rows + new_rows)     # counted from the CSV rows, as the audits count it
    out['example_row'] = new_rows[0] if new_rows else None
    if dry_run:
        return out
    stamp = now.strftime('%Y%m%dT%H%M%SZ')
    new_tags = []
    for rec, cls, all_rows, _ in plan:
        act = '%s|%s' % (rec['letter_id'], rec['congress'])
        if act not in tags_now:
            members = {r['Member']: r['Role'] for r in all_rows}
            new_tags.append(LT.tag_row(rec['letter_id'], rec['congress'], all_rows[0]['Title'], cls, cls['category'],
                                       role_weight=sum(ROLE_W[v] for v in members.values()), member_links=len(members),
                                       tagged=now.date().isoformat(), source_url=rec['document_url'], sha256=rec['sha256']))
    try:
        if new_rows or new_tags:
            if new_rows:
                backup = os.path.join(root, 'manual_bill_evidence.PRE-LETTERS-%s.csv' % stamp)
                n = 2
                while os.path.exists(backup):
                    backup = os.path.join(root, 'manual_bill_evidence.PRE-LETTERS-%s-%d.csv' % (stamp, n))
                    n += 1
                shutil.copyfile(csv_path, backup)
            # Lost-update guard: manual_bill_evidence.csv has no producer and cannot be regenerated. If anyone wrote it since it was
            # read (Paul's hand edit, another lane), write nothing now and let the next run start from the new bytes.
            if pathlib.Path(csv_path).read_bytes() != old:
                out.update(status='PARTIAL', error='csv_changed_during_promotion', rows_added=0)
                return out
            if new_tags:    # sidecar first: a crash before the CSV rename leaves a tag nobody serves, never rows without one
                side = LT.sidecar_path(root)
                existing = pathlib.Path(side).read_bytes() if os.path.exists(side) else b''
                C._atomic_write(side, existing + ''.join(json.dumps(t, sort_keys=True) + '\n' for t in new_tags).encode('utf-8'))
            if new_rows:
                if pathlib.Path(csv_path).read_bytes() != old:      # again, right before the replace (the sidecar write took time)
                    out.update(status='PARTIAL', error='csv_changed_during_promotion', rows_added=0)
                    return out
                eol = '\r\n' if b'\r\n' in old else '\n'
                buf = io.StringIO()
                csv.writer(buf, lineterminator=eol).writerows([[r[c] for c in C.CSV_COLUMNS] for r in new_rows])
                C._atomic_write(csv_path, (old if old.endswith(b'\n') else old + eol.encode()) + buf.getvalue().encode('utf-8'))
        for rec, cls, all_rows, new in plan:
            rec.update(status='PROMOTED', classification=cls, hold_reason=None, promoted_at=now.strftime('%Y-%m-%dT%H:%M:%SZ'),
                       promotion={'rows_added': len(new), 'rows_total': len(all_rows)})
        if any(json.dumps(v, sort_keys=True) != before.get(k) for k, v in staging.items()):
            C.save_staging(letters_dir, staging)
        if new_rows:
            out.update(promoted_at=now.strftime('%Y-%m-%dT%H:%M:%SZ'), backup=backup,
                       csv_sha256_before=hashlib.sha256(old).hexdigest(),
                       csv_sha256_after=hashlib.sha256(pathlib.Path(csv_path).read_bytes()).hexdigest(),
                       csv_rows_before=len(rows), csv_rows_after=len(rows) + len(new_rows),
                       members_touched=sorted({r['Member'] for r in new_rows}),
                       letters=[{'letter_id': rec['letter_id'], 'rows': len(new), 'authority': cls['authority'], 'categories': cls['category'],
                                 'direction': cls['direction'], 'sha256': rec['sha256'], 'document_url': rec['document_url']}
                                for rec, cls, _, new in plan if new],
                       notes=['assemble_approved_legislation_generation sha-binds manual_bill_evidence.csv: the next generation rebinds',
                              'promotion moves ranks through archive_leg, primacy and say-do: enumerate movers against members_touched'])
            C._atomic_write(receipt_path, json.dumps(out, indent=1, sort_keys=True).encode('utf-8'))
    except OSError as e:
        out.update(status='PARTIAL', error=repr(e)[:200], rows_added=0)
    return out


def main(argv=None):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser(description='Promote staged exact sign-on letters (Gate E + Gate C) into manual_bill_evidence.csv.')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--root', default=MB_ROOT)
    ap.add_argument('--letters-dir', default=None)
    a = ap.parse_args(argv)
    dry_run = a.dry_run or not promote_dial(os.environ)      # LETTERS_PROMOTE=0: promotion off, reporting on
    receipt = promote(root=a.root, letters_dir=a.letters_dir or os.path.join(a.root, C.LETTERS_RELATIVE),
                      now=dt.datetime.now(dt.timezone.utc), dry_run=dry_run)
    print('letters promoter %s%s: promotable %d, held %d, rows %d%s' % (
        receipt['status'], ' DRY-RUN' if dry_run else '', receipt['promotable'], len(receipt['held']), receipt['rows_added'],
        (', error ' + receipt['error']) if receipt.get('error') else ''))
    for h in receipt['held']:
        print('  held %s: %s' % (h['letter_id'], h['reason']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
