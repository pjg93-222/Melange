# -*- coding: utf-8 -*-
import io, sqlite3, sys
DB = r'C:/Users/pgoff/OneDrive/Desktop/Melange Systems/social_media.db'
con = sqlite3.connect('file:%s?mode=ro' % DB, uri=True, timeout=300)
con.execute('PRAGMA query_only=ON')
out = io.open(sys.argv[1], 'w', encoding='utf-8', newline='\n')
def w(s=''):
    out.write(s + '\n')
w('V1  the qmb package rowid 245558 belongs to (5 of the 64 inserts come from this one row)')
for r in con.execute("SELECT rowid,member,nwords,substr(text,1,140) FROM speeches "
                     "WHERE package LIKE '%/qmb/date/2023-08-17/segment/01' ORDER BY rowid"):
    w('    rowid=%-7s %-22s nw=%-5s %s' % r)
w()
w('V2  Mike Johnson INTERVIEW rows by show (top 12):')
for r in con.execute("SELECT chamber,COUNT(*) FROM speeches WHERE member='Mike Johnson' "
                     "AND source='INTERVIEW' GROUP BY chamber ORDER BY 2 DESC LIMIT 12"):
    w('    show=%-16s rows=%s' % r)
w()
w('V3  every Daniel Webster INTERVIEW row:')
for r in con.execute("SELECT rowid,date,chamber,nwords,substr(text,1,160) FROM speeches "
                     "WHERE member='Daniel Webster' AND source='INTERVIEW' ORDER BY rowid"):
    w('    rowid=%-7s %s %-10s nw=%-5s %s' % r)
w()
w('V4  rowid 83061 (Maxine Dexter) full stored text; the removed segment holds her own words:')
w('    %s' % con.execute('SELECT text FROM speeches WHERE rowid=83061').fetchone()[0])
w()
w('V5  two of the four untouched rows are a duplicate ingest of one CNN package:')
for r in con.execute("SELECT rowid,member,date,package,nwords FROM speeches "
                     "WHERE rowid IN (69544,244993)"):
    w('    rowid=%-7s %-14s date=%s nw=%s' % (r[0], r[1], r[2], r[4]))
    w('            package=%s' % r[3])
n = con.execute("SELECT COUNT(*) FROM (SELECT member,text,COUNT(*) c FROM speeches "
                "WHERE source='INTERVIEW' GROUP BY member,text HAVING c>1)").fetchone()[0]
w('    (member,text) INTERVIEW duplicate groups in the corpus TODAY: %d' % n)
con.close()
out.close()
print(io.open(sys.argv[1], encoding='utf-8').read()[:5000])
