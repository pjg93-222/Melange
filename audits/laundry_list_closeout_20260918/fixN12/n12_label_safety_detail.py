# -*- coding: utf-8 -*-
"""N12 LABEL SAFETY, record by record.  READ-ONLY.

For every record that points at one of the flagged speeches rows, say exactly what happens to it
after the split: does its verbatim excerpt survive in the kept text, do its character offsets still
address the same text, does its text_sha256 still match?  Nothing is changed anywhere.
"""
import collections
import hashlib
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
WT = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(WT, 'fec'))
from members import turn_tags as TT                      # noqa: E402
from members import migrate_interview_turn_bleed as MIG   # noqa: E402

LIVE = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
CLIPS = r'C:\melange-data\member_clips\clips_manifest.jsonl'

ROSTER = [m['member'] for m in json.load(io.open(LIVE + r'\data\engine\congestion.json',
                                                 encoding='utf-8'))]
index = TT.build_roster_index(ROSTER)
con = MIG.open_ro(LIVE + r'\social_media.db')
lexicon = MIG.build_lexicon(con, ROSTER)
plans = MIG.plan_all(con, index, lexicon)
TXT = {rid: (t or '') for rid, t in con.execute(
    "SELECT rowid, text FROM speeches WHERE source='INTERVIEW'")}
AXE = con.execute("SELECT COUNT(*) FROM speeches WHERE source='INTERVIEW' "
                  "AND chamber='axefiles'").fetchone()[0]
con.close()
P = {p['rowid']: p for p in plans}
FLAG = set(P)

coll = json.load(io.open(os.path.join(HERE, 'label_safety_rowid_collisions.json'),
                         encoding='utf-8'))
print('flagged rows: %d ; artifacts touching one: %d' % (len(FLAG), len(coll)))
print('INTERVIEW rows with chamber=axefiles (the axe clip block): %d' % AXE)
print('axe clips_manifest.jsonl in the collision list: %s'
      % any('clips_manifest' in c['artifact'] for c in coll))
print()

FIELDS_TEXT = ('text', 'context_650', 'excerpt', 'evidence', 'snippet', 'turn_text')
verdicts = collections.Counter()
per_artifact = collections.Counter()
examples = []
for c in coll:
    path = os.path.join(LIVE, c['artifact']) if not os.path.isabs(c['artifact']) else c['artifact']
    if not os.path.exists(path):
        path = CLIPS if 'clips_manifest' in c['artifact'] else path
    if not os.path.exists(path):
        print('MISSING %s' % c['artifact'])
        continue
    want = set(c['flagged'])
    with io.open(path, encoding='utf-8', errors='replace') as fh:
        for line in fh:
            if '"' not in line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if not isinstance(rec, dict):
                continue
            rid = rec.get('source_rowid')
            if rid is None:
                loc = str(rec.get('source_locator') or rec.get('turn_id')
                          or rec.get('transcript_path') or '')
                for key in ('rowid=', 'speeches:'):
                    if key in loc:
                        try:
                            rid = int(loc.rsplit(key, 1)[1].split('&')[0].split('#')[0])
                        except ValueError:
                            rid = None
            if rid is None or int(rid) not in want:
                continue
            rid = int(rid)
            plan = P[rid]
            kept = plan['kept_text'] if not plan['skip'] else plan['text']
            orig = TXT.get(rid, '')
            excerpt = None
            for f in FIELDS_TEXT:
                if isinstance(rec.get(f), str) and len(rec[f]) > 20:
                    excerpt = rec[f]
                    break
            lo, hi = rec.get('excerpt_start'), rec.get('excerpt_end')
            sha = rec.get('text_sha256')
            v = []
            if plan['skip']:
                v.append('ROW UNCHANGED (migration skips it)')
            else:
                if excerpt is not None:
                    v.append('EXCERPT SURVIVES' if ' '.join(excerpt.split()) in
                             ' '.join(kept.split()) else 'EXCERPT LOST (it is the other speaker)')
                if isinstance(lo, int) and isinstance(hi, int):
                    v.append('OFFSETS STILL VALID' if hi <= len(kept)
                             else 'OFFSETS PAST THE NEW END')
                if sha:
                    v.append('SHA MATCHES' if sha == hashlib.sha256(
                        kept.encode('utf-8')).hexdigest() else 'SHA BREAKS')
            label = [k for k in ('review_status', 'reviewer', 'decision', 'grade',
                                 'use_as_relationship_label', 'gold_stance',
                                 'speaker_identity_status', 'identity_contract')
                     if k in rec]
            key = (os.path.basename(c['artifact']), ' + '.join(v) or 'NO TEXT/OFFSET/SHA FIELD',
                   ','.join(label) or '(no label field)')
            per_artifact[key] += 1
            verdicts[' + '.join(v) or 'NO TEXT/OFFSET/SHA FIELD'] += 1
            if len(examples) < 14 and label:
                examples.append((os.path.basename(c['artifact']), rid, key[1], label,
                                 (excerpt or '')[:120]))

print('%-52s %-46s %-34s %5s' % ('artifact', 'what happens to the record', 'label field', 'n'))
for (art, v, lab), n in sorted(per_artifact.items(), key=lambda x: -x[1]):
    print('%-52s %-46s %-34s %5d' % (art[:52], v[:46], lab[:34], n))
print()
print('roll-up:')
for v, n in verdicts.most_common():
    print('  %-58s %5d' % (v, n))
print()
print('examples of records that carry a review/label field:')
for art, rid, v, lab, ex in examples:
    print('  %-44s rowid=%-7s %s  fields=%s' % (art[:44], rid, v, lab))
    print('      %s' % ' '.join(ex.split())[:120])
print('DONE')
