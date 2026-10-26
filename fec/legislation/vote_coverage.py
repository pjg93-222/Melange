"""Vote-source coverage gate: is the Voteview snapshot behind the bills the archive cites?

Ruling (Paul 2026-10-25): vote data is stale only if the archive's bills carry recorded floor votes newer than the
latest roll call on file for that chamber. Floor evidence comes from each cited bill's local GovInfo BILLSTATUS
<recordedVotes>; never file mtime. Voice votes have no recordedVote, so they are excluded by construction.
Offline. One shared function for the builder (raises) and the audit mirror (returns a string).

ponytail: the BILLSTATUS reader repeats the zip layout of build_cu_member_lane.read_bills (CR lane, not on main;
its parser also drops recordedVotes). Fold into it once that lane lands.
"""
from __future__ import annotations

import csv
import os
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

CONGRESSES = (117, 118, 119)
CHAMBERS = ('House', 'Senate')


def default_raw_root():
    return os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Melange', 'lda_rebuild', 'raw')


def archive_bill_keys(frame, measure, congresses=CONGRESSES):
    """Unique 'congress:type:number' keys (build_vote_category.measure form) of an archive frame, covered congresses only."""
    keys = {measure(n, c) for n, c in zip(frame['Name'], frame['Congress'])}
    keys.discard(None)
    return sorted(k for k in keys if int(k.split(':')[0]) in congresses)


def snapshot_coverage(source_dir, congresses=CONGRESSES):
    """-> (latest date per chamber from the newest congress file, max clerk roll per (chamber, congress, session))."""
    latest, max_roll = {}, {}
    for congress in congresses:
        path = Path(source_dir) / f'HS{congress}_rollcalls.csv'
        if not path.is_file():
            continue
        with path.open(encoding='utf-8-sig', newline='') as handle:
            for row in csv.DictReader(handle):
                chamber = row.get('chamber')
                if chamber not in CHAMBERS:
                    continue
                if congress == max(congresses) and row.get('date'):
                    latest[chamber] = max(latest.get(chamber, ''), row['date'])
                roll, session = (row.get('clerk_rollnumber') or ''), (row.get('session') or '')
                if roll.isdigit() and session.isdigit():
                    k = (chamber, congress, int(session))
                    max_roll[k] = max(max_roll.get(k, 0), int(roll))
    return latest, max_roll


def _local_date(stamp):
    """BILLSTATUS recordedVote dates are UTC instants; Voteview dates are Eastern calendar days."""
    text = (stamp or '').strip()
    if len(text) <= 10:
        return text
    moment = datetime.fromisoformat(text.replace('Z', '+00:00'))
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    try:
        from zoneinfo import ZoneInfo
        return moment.astimezone(ZoneInfo('America/New_York')).date().isoformat()
    except Exception:
        return (moment - timedelta(hours=5)).date().isoformat()


def billstatus_loader(raw_root):
    """key 'c:type:n' -> list of {chamber, congress, session, roll, date} recorded votes; None when BILLSTATUS is unavailable."""
    zips = {}

    def load(key):
        congress, btype, number = key.split(':')
        zp = os.path.join(raw_root, f'billstatus{congress}', f'BILLSTATUS-{congress}-{btype}.zip')
        if zp not in zips:
            zips[zp] = zipfile.ZipFile(zp) if os.path.exists(zp) else None
        z = zips[zp]
        member = f'BILLSTATUS-{congress}{btype}{number}.xml'
        if z is None or member not in z.namelist():
            return None
        raw = z.read(member)
        if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
            return None
        try:
            bill = ET.fromstring(raw).find('bill')
        except ET.ParseError:
            return None
        if bill is None:
            return None
        out = []
        for rv in bill.iter('recordedVote'):
            g = lambda tag: (rv.findtext(tag) or '').strip()
            out.append({'chamber': g('chamber'), 'congress': int(g('congress') or congress),
                        'session': g('sessionNumber'), 'roll': g('rollNumber'), 'date': _local_date(g('date'))})
        return out
    return load


def uncovered_recorded_votes(bill_keys, loader, latest_by_chamber, max_roll=None, congresses=CONGRESSES):
    """-> (uncovered [dict, oldest..newest], unverifiable [bill key]). Deduped per bill, chamber, congress, session, roll."""
    max_roll, seen, uncovered, unverifiable = max_roll or {}, set(), [], []
    for key in bill_keys:
        votes = loader(key)
        if votes is None:
            unverifiable.append(key)
            continue
        for v in votes:
            chamber = v['chamber']
            if chamber not in CHAMBERS or v['congress'] not in congresses:
                continue
            ident = (key, chamber, v['congress'], v['session'], v['roll'])
            if ident in seen:
                continue
            seen.add(ident)
            later = bool(v['date']) and v['date'] > latest_by_chamber.get(chamber, '')
            ceiling = max_roll.get((chamber, v['congress'], int(v['session']))) if v['session'].isdigit() else None
            over = ceiling is not None and v['roll'].isdigit() and int(v['roll']) > ceiling
            if later or over:
                uncovered.append({'bill': key, **v})
    uncovered.sort(key=lambda u: (u['date'], u['congress'], u['roll'].zfill(6), u['bill']))
    return uncovered, unverifiable


def stale_message(uncovered, latest_by_chamber):
    if not uncovered:
        return None
    n = uncovered[-1]
    return (f'Vote source is stale relative to archive: {len(uncovered)} recorded floor vote(s) newer than the snapshot '
            f'(latest on file {dict(latest_by_chamber)}); newest uncovered: {n["bill"]} {n["chamber"]} roll {n["roll"]} {n["date"]}')


def evaluate(source_dir, bill_keys, raw_root=None, loader=None):
    """Shared by builder and audit -> (message or None, uncovered, unverifiable)."""
    latest, max_roll = snapshot_coverage(source_dir)
    loader = loader or billstatus_loader(raw_root or default_raw_root())
    uncovered, unverifiable = uncovered_recorded_votes(bill_keys, loader, latest, max_roll)
    return stale_message(uncovered, latest), uncovered, unverifiable
