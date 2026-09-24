"""Local observation-vintage journal; event dates never become knowledge dates.

Stores hashes and timestamps, not contributor names or raw source copies. A first
inspection is a lower bound on this application's knowledge, not a filing date.
Transactions are committed only after a complete, stable analysis succeeds.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3

import contribution_data as data

ROOT = data.PROJECT / 'state' / 'insights-history'
VERSION_FIELDS = ('source_id', 'company', 'committee_id', 'date', 'cycle',
                  'funding_source', 'contributor_key', 'recipient', 'party', 'industry',
                  'raw_cents', 'receipt_cents', 'original_cents',
                  'supported_cents', 'pac_cents')
NOTICE = ('First seen means first inspected by this local Insights journal. It is not '
          'the original publication date. Earlier uninspected evidence remains unknown.')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False).encode('utf-8')).hexdigest()


def identity(row):
    return digest(str(row['source_id'])), digest([row.get(key) for key in VERSION_FIELDS])


def _path(dataset):
    return ROOT / (digest(dataset) + '.sqlite')


class Inspection:
    def __init__(self, db, stamp):
        self.db, self.stamp, self.buffer = db, stamp, []
        self.observed = self.new_versions = 0

    def observe(self, rows):
        for row in rows:
            sid, version = identity(row)
            self.buffer.append((sid, version, self.stamp, self.stamp))
            self.observed += 1
            if len(self.buffer) >= 2000:
                self.flush()
            yield row
        self.flush()

    def flush(self):
        if not self.buffer:
            return
        before = self.db.total_changes
        self.db.executemany('INSERT OR IGNORE INTO versions VALUES (?,?,?,?)', self.buffer)
        self.new_versions += self.db.total_changes - before
        self.db.executemany('UPDATE versions SET last_seen=MAX(last_seen,?) WHERE source_id=? AND version=?',
                            ((last, sid, ver) for sid, ver, first, last in self.buffer))
        self.buffer.clear()

    def summary(self):
        return {'inspected_at': self.stamp, 'observations_inspected': self.observed,
                'newly_inspected_versions': self.new_versions, 'notice': NOTICE}


@contextmanager
def inspection(dataset, token, provenance, now=None):
    ROOT.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(_path(dataset), timeout=120)
    try:
        # Hash keys distribute writes throughout the B-tree. Keep a bounded
        # working set instead of repeatedly paging the default 2 MiB cache.
        # A complete industry journal is ~220 MiB. Below that working set,
        # random version-hash updates repeatedly evict dirty pages and turn
        # one inspection into minutes of disk I/O. One Insights worker owns
        # this bounded cache; SQLite allocates only the pages it needs.
        db.execute('PRAGMA cache_size=-262144')
        db.executescript('''CREATE TABLE IF NOT EXISTS versions (
          source_id TEXT, version TEXT, first_seen TEXT, last_seen TEXT,
          PRIMARY KEY(source_id,version));
          CREATE TABLE IF NOT EXISTS snapshots (
          token TEXT PRIMARY KEY, first_seen TEXT, last_seen TEXT, provenance TEXT);''')
        db.execute('BEGIN IMMEDIATE')
        # The inspection clock starts after waiting for another writer. Clock
        # corrections also must not move a recorded last inspection backwards.
        stamp = now or datetime.now(timezone.utc).isoformat()
        db.execute('INSERT INTO snapshots VALUES (?,?,?,?) ON CONFLICT(token) DO UPDATE SET last_seen=MAX(snapshots.last_seen,excluded.last_seen)',
                   (token, stamp, stamp, json.dumps(provenance, sort_keys=True)))
        journal = Inspection(db, stamp)
        yield journal
        journal.flush()
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def annotate(dataset, rows):
    path = _path(dataset)
    if not path.is_file():
        return rows
    db = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
    try:
        for row in rows:
            found = db.execute('SELECT first_seen,last_seen FROM versions WHERE source_id=? AND version=?', identity(row)).fetchone()
            row['first_seen_by_insights'] = found[0] if found else None
            row['last_seen_by_insights'] = found[1] if found else None
        return rows
    finally:
        db.close()


def snapshots(dataset, limit=30):
    path = _path(dataset)
    if not path.is_file():
        return []
    db = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
    try:
        return [{'index_token': token, 'first_seen': first, 'last_seen': last,
                 'provenance': json.loads(provenance)} for token, first, last, provenance in
                db.execute('SELECT * FROM snapshots ORDER BY first_seen DESC LIMIT ?', (limit,))]
    finally:
        db.close()
