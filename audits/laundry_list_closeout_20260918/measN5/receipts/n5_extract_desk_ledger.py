# -*- coding: utf-8 -*-
"""N5 step 0 (READ-ONLY): extract the SHIPPED desk bill ledger from member_desk_bundle.json.

Nothing under fec/ is imported (import == execution).  This reads the artifact the
producer already wrote, so every filter, sidecar merge and collapse that
make_member_desk.load_press_and_bills applies is already baked in -- this is what the
desk DISPLAYS today, not a re-simulation of it.

Writes a compact sidecar to SCRATCH so the later scripts never re-parse 77 MB.
"""
import json, os, sys, hashlib, collections
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems"
SCRATCH = (r"C:\Users\pgoff\AppData\Local\Temp\claude"
           r"\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-unfinished-work-handoff-a3bbad"
           r"\5b7f7c28-909b-48f8-a495-2da7aebcc0fe\scratchpad\measN5")
os.makedirs(SCRATCH, exist_ok=True)
BUNDLE = os.path.join(ROOT, 'member_desk_bundle.json')

st = os.stat(BUNDLE)
print('bundle: %s  %d bytes  mtime=%s' % (BUNDLE, st.st_size, st.st_mtime))
with open(BUNDLE, 'rb') as fh:
    raw = fh.read()
print('sha256 = %s' % hashlib.sha256(raw).hexdigest())
D = json.loads(raw.decode('utf-8'))
del raw

print('top-level keys: %d' % len(D))
print('members: %d' % len(D.get('members') or []))
for k in ('generated', 'generated_at', 'as_of', 'desk_membership_source',
          'legislation_culling', 'source_freshness'):
    if k in D:
        v = D[k]
        print('  %-26s %s' % (k, (json.dumps(v)[:300] if not isinstance(v, str) else v)))

# the load audit the producer prints / stores
for key in ('load_audit', 'media_audit', 'desk_audit'):
    if key in D:
        a = D[key]
        if isinstance(a, dict):
            print('\n--- %s (bill_* keys) ---' % key)
            for k in sorted(a):
                if k.startswith('bill'):
                    v = a[k]
                    print('   %-46s %s' % (k, json.dumps(v)[:200] if isinstance(v, (dict, list)) else v))

out = {}
nrows = 0
for m in D.get('members') or []:
    nm = m.get('name')
    rows = m.get('bills') or []
    nrows += len(rows)
    out[nm] = [{'bill': r.get('bill') or '', 'congress': str(r.get('congress') or ''),
                'role': r.get('role') or '', 'areas': r.get('areas') or [],
                'title': r.get('title') or '', 'sponsor': r.get('sponsor') or '',
                'ncos': r.get('ncos') or 0, 'action': r.get('action') or '',
                'summary': r.get('summary') or '', 'url': r.get('url') or ''}
               for r in rows]
print('\nmembers in bundle = %d ; displayed bill rows (post-collapse) = %d ; members with >=1 = %d'
      % (len(out), nrows, sum(1 for v in out.values() if v)))
print('role histogram of displayed rows:',
      dict(collections.Counter(r['role'] for v in out.values() for r in v)))
print('congress histogram:',
      dict(sorted(collections.Counter(r['congress'] for v in out.values() for r in v).items())))

dest = os.path.join(SCRATCH, 'desk_ledger_shipped.json')
with open(dest, 'w', encoding='utf-8') as fh:
    json.dump(out, fh, ensure_ascii=False, separators=(',', ':'))
print('\nwrote %s (%.1f MB)' % (dest, os.path.getsize(dest) / 1048576.0))
