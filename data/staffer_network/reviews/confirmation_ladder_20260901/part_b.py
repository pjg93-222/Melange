# -*- coding: utf-8 -*-
"""
PART B -- A6 prose extraction near-candidates measurement (read-only).
Source: lda_conservative_bounded_episode_candidates_20260901_b (byte-identical to _a; treated
as a deterministic twin-verify pair, same sha256 for candidates/blockers files in both receipts).
"""
import sys, io, gzip, json, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

RECEIPT_PATH = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems\audits\staffer_network\lda_conservative_bounded_episode_candidates_20260901_b\lda_conservative_bounded_episode_receipt.json"
BLOCKERS_PATH = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems\audits\staffer_network\lda_conservative_bounded_episode_candidates_20260901_b\lda_conservative_bounded_episode_blockers.ndjson.gz"
OUT_JSON = r"C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-employment-tenure-adjudication-e27de8\b4908000-b7b6-4df6-92e9-96e07c3b29bc\scratchpad\ladder_cp_a6.json"

# entity classes on office_employer_mention that we count as "names a resolvable member or
# committee" for step-3(i). Determined empirically below (printed) before being hard-coded here.
RESOLVABLE_ENTITY_CLASSES = {'MEMBER_OFFICE_CANDIDATE', 'COMMITTEE_CANDIDATE'}


def main():
    with open(RECEIPT_PATH, 'r', encoding='utf-8') as f:
        receipt = json.load(f)

    print("=== A6 receipt (verbatim fields) ===")
    print("status:", receipt['status'])
    print("promotion_policy:", receipt['promotion_policy'])
    print("near_candidate_blocker_rows:", receipt['near_candidate_blocker_rows'])
    print("candidate_rows (promoted episodes):", receipt['candidate_rows'])
    print("filter_funnel:", json.dumps(receipt['filter_funnel']))
    print("blocker_counts:", json.dumps(receipt['blocker_counts'], indent=2))
    print("risk_notes:", receipt['risk_notes'])

    rows = []
    with gzip.open(BLOCKERS_PATH, 'rt', encoding='utf-8') as f:
        for line in f:
            rows.append(json.loads(line))

    assert len(rows) == receipt['near_candidate_blocker_rows'], (len(rows), receipt['near_candidate_blocker_rows'])

    # recompute blocker/rejection-reason distribution directly from the rows, as a check
    reason_counter = collections.Counter()
    for r in rows:
        for reason in r.get('rejection_reasons', []):
            reason_counter[reason] += 1
    print("\n=== rejection_reasons distribution, recomputed from the 3090 rows (should match blocker_counts) ===")
    for k, v in sorted(reason_counter.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")

    # entity_class distribution on office_employer_mention
    entity_class_counter = collections.Counter()
    office_mention_present = 0
    for r in rows:
        om = r.get('office_employer_mention')
        if om is None:
            entity_class_counter['<NONE>'] += 1
        else:
            office_mention_present += 1
            entity_class_counter[om.get('entity_class', '<MISSING>')] += 1
    print("\n=== office_employer_mention entity_class distribution (3090 rows) ===")
    for k, v in sorted(entity_class_counter.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")
    print("office_employer_mention present (non-null) on:", office_mention_present, "/", len(rows))

    # date_range_mention completeness
    both_years = start_only = end_only = neither = 0
    pattern_id_counter = collections.Counter()
    for r in rows:
        dr = r.get('date_range_mention')
        if dr is None:
            neither += 1
            continue
        pattern_id_counter[dr.get('pattern_id')] += 1
        sy, ey = dr.get('explicit_start_year'), dr.get('explicit_end_year')
        if sy is not None and ey is not None:
            both_years += 1
        elif sy is not None:
            start_only += 1
        elif ey is not None:
            end_only += 1
        else:
            neither += 1
    print("\n=== date_range_mention year completeness (3090 rows) ===")
    print("  both explicit_start_year and explicit_end_year present:", both_years)
    print("  start year only:", start_only)
    print("  end year only:", end_only)
    print("  neither (or date_range_mention null):", neither)
    print("  date_range_mention.pattern_id distribution:", dict(pattern_id_counter))

    # role_title_mention presence (for context, not one of the 3 required metrics but useful)
    role_present = sum(1 for r in rows if r.get('role_title_mention') is not None)
    print("\nrole_title_mention present (non-null) on:", role_present, "/", len(rows))

    # ---- 10 example near-candidate rows ----
    print("\n=== 10 example near-candidate rows (truncated) ===")
    examples = []
    step = max(1, len(rows) // 10)
    for i in range(0, len(rows), step):
        if len(examples) >= 10:
            break
        r = rows[i]
        om = r.get('office_employer_mention') or {}
        dr = r.get('date_range_mention') or {}
        rt = r.get('role_title_mention') or {}
        ex = {
            'claim_text_truncated': r['claim_text'][:140],
            'role_title_text': rt.get('text'),
            'office_employer_text': om.get('text'),
            'office_employer_entity_class': om.get('entity_class'),
            'date_range_text': dr.get('text'),
            'explicit_start_year': dr.get('explicit_start_year'),
            'explicit_end_year': dr.get('explicit_end_year'),
            'rejection_reasons': r.get('rejection_reasons'),
        }
        examples.append(ex)
        print(json.dumps(ex, indent=2))

    # ---- the 3 headline metrics ----
    print("\n=== STEP 3 metrics: stricter same-string binding rule ===")
    n_i = 0    # resolvable member/committee entity present
    n_ii = 0   # date span with both start and end year
    n_iii = 0  # both (i) and (ii)
    for r in rows:
        om = r.get('office_employer_mention')
        dr = r.get('date_range_mention')
        has_resolvable_entity = bool(om) and om.get('entity_class') in RESOLVABLE_ENTITY_CLASSES
        has_full_date_span = bool(dr) and dr.get('explicit_start_year') is not None and dr.get('explicit_end_year') is not None
        if has_resolvable_entity:
            n_i += 1
        if has_full_date_span:
            n_ii += 1
        if has_resolvable_entity and has_full_date_span:
            n_iii += 1

    print(f"(i)  resolvable member/committee entity_class in {sorted(RESOLVABLE_ENTITY_CLASSES)}: {n_i} / {len(rows)}")
    print(f"(ii) date span with BOTH explicit_start_year and explicit_end_year: {n_ii} / {len(rows)}")
    print(f"(iii) both (i) AND (ii) -- partial episodes extractable with a stricter same-string binding rule: {n_iii} / {len(rows)}")

    result = {
        'part_b': {
            'source_dir': 'lda_conservative_bounded_episode_candidates_20260901_b (byte-identical to _20260901_a)',
            'receipt_status': receipt['status'],
            'near_candidate_blocker_rows': receipt['near_candidate_blocker_rows'],
            'blocker_counts_from_receipt': receipt['blocker_counts'],
            'blocker_counts_recomputed_from_rows': dict(reason_counter),
            'entity_class_distribution': dict(entity_class_counter),
            'date_year_completeness': {
                'both_years': both_years, 'start_only': start_only, 'end_only': end_only, 'neither': neither,
            },
            'date_pattern_id_distribution': dict(pattern_id_counter),
            'role_title_mention_present': role_present,
            'examples': examples,
            'step3_metrics': {
                'resolvable_entity_in_string': n_i,
                'full_date_span': n_ii,
                'both': n_iii,
                'resolvable_entity_classes_used': sorted(RESOLVABLE_ENTITY_CLASSES),
            },
        }
    }

    # merge with existing part_a output if present
    try:
        with open(OUT_JSON, 'r', encoding='utf-8') as f:
            existing = json.load(f)
    except FileNotFoundError:
        existing = {}
    existing.update(result)
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(existing, f, indent=2, default=str)
    print("\nWrote/merged:", OUT_JSON)


if __name__ == '__main__':
    main()
