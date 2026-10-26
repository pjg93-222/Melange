# -*- coding: utf-8 -*-
"""Beneficiary-tag sidecar for auto-promoted sign-on letters (brain D-263, lane L).

A promoted LTR- row with no tag makes engine/primacy_factors.py raise KeyError, and a tag whose letter is not in the
member-desk bundle breaks its "act universe and beneficiary tags are closed" check. The tracked
bill_beneficiary_tags.ndjson is a ratified, hash-bound artifact and is never edited (law 6), so the promoter writes
data/legislation/letters/letter_tags.ndjson instead and sentinel_admissions.effective_tags merges it with the same
rule as sentinel decisions: an existing (ratified) classification wins.

load() therefore serves a tag only while its letter has rows in manual_bill_evidence.csv. The promoter renames the
sidecar BEFORE the CSV, so a crash between the two leaves a tag nobody serves, never rows without a tag."""
import csv
import json
import os

SIDECAR = os.path.join('data', 'legislation', 'letters', 'letter_tags.ndjson')
REQUIRED = ('bill', 'congress', 'class', 'areas')


def sidecar_path(root):
    return os.path.join(root, SIDECAR)


def tag_row(letter_id, congress, title, classification, areas, *, role_weight, member_links, tagged, source_url, sha256):
    """One tag in the shape of the hand-ratified letter tags (bill_beneficiary_tags.ndjson), plus its source."""
    return {'bill': letter_id, 'congress': str(congress), 'title': title, 'class': classification['beneficiary_class'],
            'act_weight': classification['act_weight'], 'authority': classification['authority'],
            'rationale': classification['rationale'], 'acu_position': '', 'confidence': classification['confidence'],
            'areas': list(areas), 'roster_role_weight': role_weight, 'member_links': member_links, 'tagged': tagged,
            'source_url': source_url, 'source_sha256': sha256}


def read_rows(root):
    """Every sidecar row (validated, duplicates refused), in file order; [] when there is no sidecar."""
    path = sidecar_path(root)
    if not os.path.exists(path):
        return []
    rows, seen = [], set()
    with open(path, encoding='utf-8') as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            for key in REQUIRED:
                if key not in row:
                    raise ValueError('letter tag %r lacks %s' % (row.get('bill'), key))
            act = '%s|%s' % (str(row['bill']).strip(), str(row['congress']).strip())
            if act in seen:
                raise ValueError('duplicate letter tag: %s' % act)
            seen.add(act)
            rows.append(row)
    return rows


def csv_letter_ids(root):
    path = os.path.join(root, 'manual_bill_evidence.csv')
    if not os.path.exists(path):
        return set()
    with open(path, encoding='utf-8-sig', newline='') as handle:
        return {(r.get('Bill') or '').strip() for r in csv.DictReader(handle)}


def load(root):
    """{'<letter id>|<congress>': tag} for the sidecar tags whose letters are in the CSV (same key primacy_factors.load_tags uses)."""
    rows = read_rows(root)
    if not rows:
        return {}
    live = csv_letter_ids(root)
    return {'%s|%s' % (str(r['bill']).strip(), str(r['congress']).strip()): r for r in rows if str(r['bill']).strip() in live}


AUTO_NOTE = 'auto-letter'     # the promoter starts every Note it writes with this; hand-ingested rows never do


def auto_letter_accounting(rows):
    """What promote_staged_letters.py has put in the CSV, counted FROM THE ROWS (never from a receipt that could disagree with the file):
    {'rows': auto-letter LTR rows, 'sponsor' / 'original': distinct member x letter pairs by role (what the member-desk bundle holds
    once a letter's categories collapse), 'letters': distinct letter ids}. The audit pins and the legacy evidence recompute add this
    to their fixed base counts, exactly."""
    pairs, letters, count = {}, set(), 0
    for row in rows:
        bill = (row.get('Bill') or '').strip()
        if bill.upper().startswith('LTR-') and (row.get('Note') or '').strip().startswith(AUTO_NOTE):
            count += 1
            letters.add(bill)
            pairs[(row.get('Member'), bill)] = (row.get('Role') or '').strip().lower()
    return {'rows': count, 'sponsor': sum(r == 'sponsor' for r in pairs.values()),
            'original': sum(r in ('original-cosponsor', 'original') for r in pairs.values()), 'letters': len(letters)}


def auto_letter_accounting_from_csv(path):
    if not os.path.exists(path):
        return auto_letter_accounting([])
    with open(path, encoding='utf-8-sig', newline='') as handle:
        return auto_letter_accounting(csv.DictReader(handle))
