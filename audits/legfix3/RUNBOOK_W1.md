# W1 — ACU letters snapshot collector runbook

Run these commands in order from PowerShell. The collector uses only the
standard library and writes the durable snapshot under this worktree's
`source_data` directory.

## Commands

1. Enter the W1 worktree.

   ```powershell
   Set-Location -LiteralPath 'C:\Users\pgoff\AppData\Local\Temp\claude\cxwt-legfix3'
   ```

2. Compile-check without creating `__pycache__`.

   ```powershell
   python -W error -c "from pathlib import Path; p=Path(r'fec/fetch_acu_letters.py'); compile(p.read_text(encoding='utf-8'), str(p), 'exec'); print('compile ok:', p)"
   ```

3. Run the collector against the live routing audit. The ACU request spacing
   is at least one second and each request has a 30-second timeout.

   ```powershell
   python fec\fetch_acu_letters.py --routing-audit 'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\legislation_routing_audit.json' --timeout 30
   ```

4. Validate the durable artifact, its encoding, count agreement, and required
   date-then-URL-or-ID ordering.

   ```powershell
   @'
   import json
   from pathlib import Path

   p = Path(r'source_data/acu_letters_snapshot_20260725.json')
   raw = p.read_bytes()
   assert not raw.startswith(b'\xef\xbb\xbf'), 'snapshot has a UTF-8 BOM'
   doc = json.loads(raw.decode('utf-8'))
   letters = doc['letters']
   assert doc['collected_count'] == doc['reported_count'] == len(letters)

   def date_of(value):
       if isinstance(value, list):
           return next((date_of(item) for item in value if date_of(item)), '')
       if isinstance(value, dict):
           return str(value.get('formatted') or '')
       return ''

   key = lambda row: (
       date_of(row.get('fieldPublishDate')),
       str(row.get('url') or row.get('id') or ''),
   )
   assert letters == sorted(letters, key=key), 'snapshot ordering failed'
   print(
       'snapshot ok:',
       p.resolve(),
       'letters=', len(letters),
       'fetched_at=', doc['fetched_at'],
   )
   '@ | python -
   ```

## Predicted output

- The compile command prints
  `compile ok: fec\fetch_acu_letters.py`.
- With the observed live count of 533 and accepted page size 50, collection
  uses 11 search pages plus 11 `AdvocacyQuery` batches: 22 requests. If the
  server rejects or silently caps 50, the collector reports the rejection,
  restarts at the captured browser page size of 12, and uses 45 search/detail
  page pairs after the rejected attempt.
- Success reports `collected=533 reported=533`, the request count and selected
  page size, followed by the durable path:
  `source_data\acu_letters_snapshot_20260725.json`.
- Layer-1 counts are printed inline against the 2026-07-24 cache:
  Examination and Supervision 176; Payments & Technology 92; Consumer
  Protection 87; Lending 85; Tax, Budget & Bank Attacks 82; Credit Union
  Powers & Charter 74; Regulatory Relief 23; Information Security 21; and
  Diversity, Equity & Inclusion 2. A live change appears as a nonzero delta.
- If those tag counts remain unchanged, the supplied routing audit produces
  old=fresh reverse-gap multipliers of approximately: Information Security
  4.04x; Lending 2.77x; Consumer Protection 0.64x; Payments & Technology
  0.62x; Examination and Supervision 0.60x; Credit Union Powers & Charter
  0.58x; and Tax, Budget & Bank Attacks 0.44x. The mapping citation printed by
  the collector is
  `audits/legfix2/audit_sp_reference/gapb.py:11-19`.
- The final section prints every full label evidence line matching H.R.8398 or
  H.R.8413, tolerating `H.R. 8398`, `H.R.8398`, or `HR 8398` forms. It prints
  an explicit no-match line for either bill with no matching letter label.
- The validation command should print `snapshot ok`, the absolute worktree
  path, `letters= 533`, and the snapshot timestamp.

## Abort conditions

- Exit code 2 means an HTTP, WAF, timeout, request-cap, GraphQL, pagination, or
  response-integrity failure. The collector prints status plus progress and
  writes collected records only to
  `source_data\acu_letters_snapshot_20260725.json.partial`; it never writes a
  partial result to the durable name.
- Stop downstream use if the reported count differs from the intercepted
  533, even if collection is internally complete. Confirm whether ACU changed
  the live corpus or request behavior before accepting the new universe.
- Stop if the durable validation command fails, mapped tag counts collapse to
  zero, the output is non-UTF-8/BOM-prefixed, or ordering/count assertions
  fail.
- Stop if the collector reaches 200 requests. Do not increase the cap without
  a new collection decision.
- A routing-audit validation error exits 1 before any network request. Correct
  the supplied path or audit structure and rerun.
- Do not use a failed run's `.partial` file as evidence.

## Tracker omission

There is no `--tracker` mode. The 2026-07-25 capture recovered the `search` and
`AdvocacyQuery` letter operations but no tracker-position request shape.
Per W1, no tracker endpoint or request was invented.
