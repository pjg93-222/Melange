import collections
import json
import os
import sqlite3
import sys


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def inspect_database(path):
    print(f"\nDB|{os.path.basename(path)}|mtime={os.path.getmtime(path):.0f}")
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    tables = [r[0] for r in con.execute(
        "select name from sqlite_master where type='table' order by name"
    )]
    for table in tables:
        cols = [r[1] for r in con.execute(f'pragma table_info("{table}")')]
        if "member" not in cols:
            continue
        where = 'member = ?'
        n = con.execute(f'select count(*) from "{table}" where {where}', ("Daniel Meuser",)).fetchone()[0]
        if not n:
            continue
        print(f"TABLE|{table}|rows={n}|cols={','.join(cols)}")
        source_col = next((c for c in ("source", "type", "platform") if c in cols), None)
        if source_col:
            groups = con.execute(
                f'select "{source_col}", count(*) from "{table}" where {where} group by 1 order by 2 desc',
                ("Daniel Meuser",),
            ).fetchall()
            print("SOURCES|" + json.dumps(groups))
        text_col = next((c for c in ("text", "content", "body", "title") if c in cols), None)
        if text_col:
            stats = con.execute(
                f'select min(length("{text_col}")), avg(length("{text_col}")), max(length("{text_col}")) '
                f'from "{table}" where {where}',
                ("Daniel Meuser",),
            ).fetchone()
            print(f"TEXTLEN|min={stats[0]}|avg={stats[1]:.1f}|max={stats[2]}")
    con.close()


def inspect_desk(path):
    data = json.load(open(path, encoding="utf-8"))
    members = data if isinstance(data, list) else data.get("members", [])
    member = next(m for m in members if m.get("name") == "Daniel Meuser")
    articles = member.get("articles", [])
    print(f"\nDESK|{os.path.basename(path)}|rank={member.get('rank')}|score={member.get('score')}|articles={len(articles)}")
    by_source = collections.Counter(a.get("source") for a in articles)
    print("ARTICLE_SOURCES|" + json.dumps(by_source))
    lengths = sorted(((len(a.get("title") or ""), a) for a in articles), reverse=True, key=lambda x: x[0])
    for n, article in lengths[:15]:
        print("LONG|%d|%s|%s|%s|%s" % (
            n,
            article.get("date"),
            article.get("source"),
            ";".join(article.get("cats") or []),
            (article.get("url") or "")[:120],
        ))
    exact = collections.Counter(" ".join((a.get("title") or "").lower().split()) for a in articles)
    print("EXACT_DUPLICATE_GROUPS|" + str(sum(1 for n in exact.values() if n > 1)))


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        path = os.path.abspath(arg)
        if path.lower().endswith(".db"):
            inspect_database(path)
        else:
            inspect_desk(path)
