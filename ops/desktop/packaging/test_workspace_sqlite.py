from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
import zlib

from workspace_publication import PublicationProjection
import workspace_sqlite as target


class SQLiteProjectionTests(unittest.TestCase):
    def test_older_changed_timestamp_database_uses_separate_path_and_held_handle_snapshots(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'old.sqlite'
            with closing(sqlite3.connect(path)) as db:db.executescript(target.SCHEMAS['source'])
            os.utime(path,(946684800,946684800))
            with path.open('rb') as stream:expected=hashlib.file_digest(stream,'sha256').hexdigest()
            with target.readonly(path,'source',expected_sha256=expected,expected_bytes=path.stat().st_size,final_hash=True) as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM entities').fetchone(),(0,))

    def test_all_compiled_families_rebuild_deterministically_from_live_rows_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for family, ddl in target.SCHEMAS.items():
                source = root/(family+'.sqlite')
                with closing(sqlite3.connect(source)) as db:
                    db.executescript(ddl)
                    if family in ('source','lda'):
                        data = [{'id':'fixture-id','url':'https://example.org/source?id=1&api_key=fixture-private'}]
                        db.execute('INSERT INTO chunks VALUES (?,?)',(1,zlib.compress(json.dumps(data).encode())))
                        db.execute('INSERT INTO entities VALUES (?,?,?,?,?,?,?)',('fixture-id','Fixture','person','public','summary',1,0))
                    db.commit()
                receipts = []
                for attempt in (1,2):
                    projection = PublicationProjection()
                    published = root/(family+str(attempt)+'.sqlite')
                    receipts.append(target.rebuild(source,published,family,projection))
                    with target.readonly(published,family,expected_sha256=receipts[-1]['sha256'],expected_bytes=receipts[-1]['bytes']) as db:
                        self.assertEqual(db.execute('PRAGMA freelist_count').fetchone(),(0,))
                        with self.assertRaises(sqlite3.OperationalError):
                            db.execute('CREATE TABLE forbidden(value)')
                        if family in ('source','lda'):
                            rows=json.loads(zlib.decompress(db.execute('SELECT payload FROM chunks').fetchone()[0]))
                            self.assertEqual(rows[0]['url'],'https://example.org/source?id=1')
                self.assertEqual(receipts[0],receipts[1])
                self.assertEqual((root/(family+'1.sqlite')).read_bytes(),(root/(family+'2.sqlite')).read_bytes())

    def test_triggers_views_foreign_tables_sidecars_and_hash_changes_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name, extra in (('trigger','CREATE TRIGGER malicious AFTER INSERT ON metadata BEGIN DELETE FROM metadata; END'),
                                ('view','CREATE VIEW malicious AS SELECT * FROM metadata'),
                                ('table','CREATE TABLE malicious(value)')):
                path=root/(name+'.sqlite')
                with closing(sqlite3.connect(path)) as db:
                    db.executescript(target.SCHEMAS['source']+extra)
                with self.assertRaises(ValueError):
                    with target.readonly(path,'source'):pass
            clean=root/'clean.sqlite'
            with closing(sqlite3.connect(clean)) as db:db.executescript(target.SCHEMAS['source'])
            with self.assertRaises(ValueError):
                with target.readonly(clean,'source',expected_sha256='0'*64,expected_bytes=clean.stat().st_size):pass
            Path(str(clean)+'-wal').write_bytes(b'')
            with self.assertRaises(ValueError):
                with target.readonly(clean,'source'):pass

    def test_donor_precision_changes_do_not_reassign_person_or_financial_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'source.sqlite';output=root/'output.sqlite'
            with closing(sqlite3.connect(source)) as db:
                db.executescript(target.SCHEMAS['facts'])
                columns=[row[1] for row in db.execute('PRAGMA table_info(facts)')]
                row={name:'' for name in columns}
                row.update(source_id='fixture-source',contributor_key='existing-preassigned-person-key',street_1='fixture home street',
                           street_2='fixture apartment',zip5='01234',raw_zip='01234-5678',raw_cents=-100,receipt_cents=-100,
                           original_cents=-100,supported_cents=0,pac_cents=0,unresolved=0,reasons='[]',evidence_ids='[]')
                db.execute('INSERT INTO facts VALUES ('+','.join('?' for _ in columns)+')',[row[name] for name in columns]);db.commit()
            target.rebuild(source,output,'facts',PublicationProjection())
            with target.readonly(output,'facts') as db:
                db.row_factory=sqlite3.Row
                result=dict(db.execute('SELECT * FROM facts').fetchone())
                self.assertEqual(result,{**row,'street_1':'','street_2':'','raw_zip':'01234'})
            self.assertEqual([target.postal(value) for value in ('01234','012345678','01234-5678','foreign-postal','')],['01234','01234','01234','',''])


if __name__ == '__main__':unittest.main()
