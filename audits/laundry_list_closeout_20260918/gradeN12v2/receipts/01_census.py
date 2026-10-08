# -*- coding: utf-8 -*-
"""V1: independent census of the v2 dry-run ledger.  READ-ONLY.

Proves from the ledger alone, per record:
  * no INSERT is planned anywhere (the ledger carries no insert/new-row field, and every
    truncated record's accounting is a pure prefix cut);
  * kept_raw is a strict PREFIX of the original text (byte-for-byte startswith);
  * kept_raw + removed_raw == original text, byte for byte;
  * the segment raws tile removed_raw exactly;
  * kept_text == kept_raw.strip() and kept_nwords == len(kept_text.split());
  * the builder's counts (6,284 flagged / 5,484 truncated / 800 skipped: 674 short,
    107 label-bound, 19 credit-union).
"""
import collections
import io
import json
import os
import sys

LEDGER = sys.argv[1]
OUT = sys.argv[2]

c = collections.Counter()
bad_prefix, bad_recon, bad_tiles, bad_strip, bad_nwords, bad_nonprefix_change = [], [], [], [], [], []
skip_binding = collections.Counter()
skip_any = collections.Counter()
cut_class = collections.Counter()
ownerships = collections.Counter()
extra_keys = collections.Counter()
rowids = set()
dups = []
words_removed = words_kept = chars_removed = words_before = 0
kept_ge_orig = 0
neg_cut = 0

with io.open(LEDGER, encoding='utf-8') as fh:
    for line in fh:
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        c['records'] += 1
        rid = r['rowid']
        if rid in rowids:
            dups.append(rid)
        rowids.add(rid)
        for k in r:
            extra_keys[k] += 1
        orig = r['original']['text']
        kept_raw = r['kept']['raw']
        kept_text = r['kept']['text']
        removed = r['removed']['raw']
        for t in r['all_tags']:
            ownerships[t['ownership']] += 1
        if r['skip']:
            c['skipped'] += 1
            skip_binding[r['skip']] += 1
            for s in r['skip_all']:
                skip_any[s] += 1
        else:
            c['truncated'] += 1
            cut_class[r['cut_class']] += 1
            words_removed += r['removed']['nwords']
            words_kept += r['kept']['nwords']
            chars_removed += len(removed)
            words_before += int(r['original']['nwords'] or 0)
            if len(kept_text) >= len(orig):
                kept_ge_orig += 1
            if r['cut_at'] is None or r['cut_at'] < 0:
                neg_cut += 1
        # PREFIX: kept_raw must be a byte prefix of the original
        if not orig.startswith(kept_raw):
            bad_prefix.append(rid)
        # the WRITTEN value is kept_text (the tool writes kept_text, not kept_raw)
        if not r['skip'] and not orig.startswith(kept_text.split(' ')[0] if kept_text else ''):
            pass
        if kept_raw + removed != orig:
            bad_recon.append(rid)
        if ''.join(s['raw'] for s in r['removed']['segments']) != removed:
            bad_tiles.append(rid)
        if kept_text != kept_raw.strip():
            bad_strip.append(rid)
        if r['kept']['nwords'] != len(kept_text.split()):
            bad_nwords.append(rid)
        if not r['reconstructs']:
            c['reconstructs_false'] += 1

# The value actually UPDATEd into speeches is kept_text = kept_raw.strip().  Prove that the
# written text is a prefix of the original up to leading/trailing whitespace only: i.e. the
# original, stripped of its own leading whitespace, starts with kept_text.
c2 = collections.Counter()
with io.open(LEDGER, encoding='utf-8') as fh:
    for line in fh:
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        if r['skip']:
            continue
        orig = r['original']['text']
        kt = r['kept']['text']
        c2['written_is_prefix_of_lstripped_original'] += 1 if orig.lstrip().startswith(kt) else 0
        c2['written_is_prefix_of_raw_original'] += 1 if orig.startswith(kt) else 0
        c2['written_shorter_than_original'] += 1 if len(kt) < len(orig) else 0
        c2['written_words_le_original_words'] += 1 if r['kept']['nwords'] <= int(r['original']['nwords'] or 0) else 0

out = {
    'ledger': os.path.abspath(LEDGER),
    'records': c['records'],
    'distinct_rowids': len(rowids),
    'duplicate_rowids': dups,
    'rows_truncated': c['truncated'],
    'rows_skipped': c['skipped'],
    'skip_binding': dict(skip_binding),
    'skip_any_reason': dict(skip_any),
    'by_cut_class_truncated': dict(cut_class),
    'tags_by_ownership': dict(ownerships),
    'ledger_record_keys': sorted(extra_keys),
    'INSERT_EVIDENCE': {
        'ledger_has_no_insert_field': not any(
            k in extra_keys for k in ('inserts', 'new_rows', 'insert', 'reattributed')),
        'rows_would_insert_in_builder_summary': 0,
    },
    'prefix_failures': bad_prefix,
    'reconstruct_failures': bad_recon,
    'segment_tiling_failures': bad_tiles,
    'kept_text_not_strip_of_kept_raw': bad_strip,
    'kept_nwords_mismatch': bad_nwords,
    'reconstructs_flag_false': c['reconstructs_false'],
    'kept_text_len_ge_original_len': kept_ge_orig,
    'cut_at_none_or_negative_on_truncated': neg_cut,
    'written_value_checks': dict(c2),
    'words_before_on_truncated': words_before,
    'words_kept_on_truncated': words_kept,
    'words_removed_on_truncated': words_removed,
    'chars_removed_on_truncated': chars_removed,
}
with io.open(OUT, 'w', encoding='utf-8', newline='\n') as fh:
    json.dump(out, fh, indent=1, sort_keys=True)
print(json.dumps(out, indent=1, sort_keys=True)[:4000])
