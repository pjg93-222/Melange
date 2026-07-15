# -*- coding: utf-8 -*-
"""Fail-closed identity/category checks for generated dashboard artifacts."""
import hashlib, json, os
import openpyxl
from paths import ROOT, WORKBOOK, p
import moneyball_core as MC
import stance_rules as SR


class IntegrityError(RuntimeError):
    pass


def _sha(obj):
    raw=json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def _file_sha(path):
    """Hash file contents, not mtimes, so OneDrive/Excel touches are not data changes."""
    if not os.path.exists(path):
        return None
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()


def _check(condition, message, errors):
    if not condition: errors.append(message)


def preflight(member_names, category_stance, dashboard_data, archive_leg):
    """Validate the identity and category joins before any desk artifact is written."""
    errors=[]; warnings=[]; roster=MC.members(); rset=set(roster); cats=category_stance.get('cats') or []
    _check(len(roster)==len(rset), 'canonical roster contains duplicate names', errors)
    _check(len(member_names)==len(set(member_names)), 'member desk source contains duplicate names', errors)
    _check(set(member_names)==rset, 'member desk source roster differs from canonical roster', errors)
    snames=dashboard_data.get('name') or []
    _check(len(snames)==len(set(snames)), 'dashboard_data contains duplicate names', errors)
    _check(set(snames)==rset, 'dashboard_data roster differs from canonical roster', errors)
    _check(set(category_stance.get('matrix') or {})==rset, 'stance matrix roster differs from canonical roster', errors)
    _check(set(category_stance.get('scores') or {})==rset, 'stance score roster differs from canonical roster', errors)
    _check(set(archive_leg).issubset(rset), 'legislation archive contains unknown/current-roster-mismatched names', errors)
    for name in roster:
        _check(set((category_stance.get('matrix') or {}).get(name,{}) or {})==set(cats),
               'stance categories missing/misaligned for '+name, errors)
        _check(set((category_stance.get('scores') or {}).get(name,{}) or {})==set(cats),
               'stance score categories missing/misaligned for '+name, errors)
    issues=dashboard_data.get('issues') or []
    stance_rows=dashboard_data.get('stance') or []
    _check(len(stance_rows)==len(snames), 'dashboard stance row count does not match dashboard names', errors)
    _check(all(len(s)==len(issues) for s in stance_rows), 'dashboard stance strings do not align to issue count', errors)

    wb=openpyxl.load_workbook(WORKBOOK,read_only=True,data_only=True)
    ra=wb['Rank & Allocation']; wn=[ra.cell(r,1).value for r in range(3,536) if ra.cell(r,1).value]
    # Rows 2:534 are the 533-member roster; row 535 is the literal "Weights" footer.
    rw=wb['Press Release - Raw']; mn=[rw.cell(r,1).value for r in range(2,535) if rw.cell(r,1).value]
    wb.close()
    _check(len(wn)==len(set(wn)) and set(wn)==rset, 'Rank & Allocation roster is duplicated or misaligned', errors)
    _check(len(mn)==len(set(mn)) and set(mn)==rset, 'Press Release - Raw roster is duplicated or misaligned', errors)

    # General CU must be conserved exactly when distributed.
    alloc=((category_stance.get('media') or {}).get('general_credit_union') or {})
    bad_conservation=[]
    for name,a in alloc.items():
        if name not in rset or abs(float(a.get('general',0))-sum(float(x) for x in (a.get('to') or {}).values()))>1e-8:
            bad_conservation.append(name)
    _check(not bad_conservation, 'General CU allocation is not identity-safe/conserved: '+', '.join(bad_conservation[:5]), errors)
    if not alloc: warnings.append('no nonzero General Credit Union values were available to disperse')

    report={'status':'pass' if not errors else 'fail','errors':errors,'warnings':warnings,
            'counts':{'roster':len(roster),'categories':len(cats),'general_cu_members':len(alloc)},
            'roster_order_sha256':_sha(roster),'category_order_sha256':_sha(cats)}
    if errors: raise IntegrityError('; '.join(errors[:8]))
    return report


def postflight(bundle, preflight_report):
    """Validate the completed desk bundle and enforce deterministic regeneration."""
    errors=[]; warnings=[]; roster=MC.members(); rset=set(roster); cats=bundle.get('cats') or []
    members=bundle.get('members') or []; names=[m.get('name') for m in members]
    _check(len(names)==len(set(names)) and set(names)==rset, 'desk bundle roster is duplicated or misaligned', errors)
    allowed=set(cats)|set(bundle.get('art_extra_cats') or [])
    n2b=MC.name2bio(); social_members=set(); article_total=bill_total=0; missing_bio=[]
    for m in members:
        name=m.get('name'); article_total+=len(m.get('articles') or []); bill_total+=len(m.get('bills') or [])
        _check(len(m.get('stances') or '')==len(cats), 'desk stance string misaligned for '+str(name), errors)
        expected=n2b.get(name); actual=(m.get('bio') or {}).get('bioguide')
        if expected and actual: _check(actual==expected, 'bioguide mismatch for '+str(name), errors)
        elif expected and not actual: missing_bio.append(name)
        for a in m.get('articles') or []:
            _check(set(a.get('cats') or []).issubset(allowed), 'unknown media category for '+str(name), errors)
            if a.get('source')=='social': social_members.add(name)
        for b in m.get('bills') or []:
            _check(set(b.get('areas') or []).issubset(allowed), 'unknown bill category for '+str(name), errors)
    source_display=((bundle.get('integrity') or {}).get('source_display') or {})
    _check(source_display.get('social_displayed',0)>0, 'social source loaded zero visible items', errors)
    def _recon(source,parts):
        accounted=sum(int(source_display.get(k,0) or 0) for k in parts)
        return {'source_rows':int(source),'accounted_rows':accounted,
                'difference':int(source)-accounted,'components':{k:int(source_display.get(k,0) or 0) for k in parts},
                'status':'pass' if int(source)==accounted else 'fail'}
    reconciliation={
        'press':_recon(source_display.get('press_source_rows',0),(
            'press_displayed','press_unknown_member_excluded','press_billstatus_rows_routed_to_legislation')),
        'social':_recon(source_display.get('social_source_rows',0),(
            'social_displayed','social_unverified_handle_excluded','social_unknown_member_excluded',
            'social_unrelated_excluded','social_offtopic_excluded')),
        'legislation':_recon((source_display.get('bill_source_rows',0) or 0)+
                              (source_display.get('bill_manual_rows',0) or 0),(
            'bills_displayed_unique','bill_duplicate_rows_collapsed','bill_unknown_member_excluded',
            'bill_rules_excluded','bill_override_excluded','bill_manual_excluded')),
    }
    for source,row in reconciliation.items():
        _check(row['status']=='pass','%s source rows are not fully reconciled (%+d)'%(source,row['difference']),errors)
    _check(article_total==(source_display.get('press_displayed',0) or 0)+(source_display.get('social_displayed',0) or 0),
           'desk article total does not match reconciled press + social display rows',errors)
    _check(bill_total==(source_display.get('bills_displayed_unique',0) or 0),
           'desk bill total does not match reconciled unique legislation rows',errors)
    MC.dump_atomic({'status':'pass' if all(v['status']=='pass' for v in reconciliation.values()) else 'fail',
                    'rule':'Every source row must be displayed or assigned one explicit exclusion/routing reason.',
                    'sources':reconciliation,'exclusion_samples':source_display.get('exclusion_samples') or {}},
                   p('dashboard_exclusion_reconciliation.json'),indent=2,ensure_ascii=False)
    if missing_bio: warnings.append('%d members lack desk bioguide enrichment (identity not guessed)'%len(missing_bio))

    # Strip self-referential validation and volatile freshness metadata before hashing the semantic
    # product.  ``generated_at`` and source mtimes are provenance/display metadata, not member data;
    # including them makes every same-input rebuild fail merely because it ran in a later second.
    projection={k:v for k,v in bundle.items() if k not in ('integrity','freshness')}
    output_hash=_sha(projection)
    # Fingerprint every source consumed by make_member_desk plus its routing code
    # and templates.  Content hashes prevent timestamp-only Excel/OneDrive touches
    # from defeating the same-input/same-output corruption check.
    source_files=[
        'Moneyball Main Version - Blended.xlsx','Social Master.xlsx','tweet_stance_final.csv',
        'manual_bill_evidence.csv','bill_overrides.csv','archive_leg.json',
        'behavioral_dispositions.json','behavioral_roles_v2_candidate.json',
        'big5_blue_emb.json','big5_blue_validated.json','big5_llm_opus.json',
        'big5_senate_expert_gold.json','big5_external_gold_validation.json','big5_e_gold_anchored.json',
        'big5_gold_anchored.json',
        'big5_traits.json','big5_v2.json','category_stance.json','communication_style.json',
        'coop_v2_candidate.json','dashboard_data.json','electoral_history.json',
        'electoral_plays.json','interview_antagonism.json','kb_benchmark.json',
        'lep_criterion.json','member_desk_manual.json','member_desk_src.json',
        'member_narratives_v2.json','member_personal_texture.json','member_receptivity.json',
        'member_references.json','model_bio.json','optimize_result.json',
        'pillar_inputs_snapshot.json','press_date_overrides.json','press_stance_overrides.json',
        'profile_basis_v2.json','ranks_python.json','signed_coalitions.json',
        'staff_directory.json','staff_interactions.json','staff_state.json','formal_visibility_roles.json',
        os.path.join('fec','legislators.csv'),os.path.join('fec','make_member_desk.py'),
        os.path.join('fec','media_rules.py'),os.path.join('fec','bill_rules.py'),
        os.path.join('fec','member_identity.py'),os.path.join('fec','dashboard_integrity.py'),
        os.path.join('fec','moneyball_core.py'),os.path.join('fec','stance_rules.py'),
        os.path.join('fec','per_category_stance.py'),os.path.join('fec','compute_pillars.py'),
        os.path.join('fec','influence_roles.py'),
        os.path.join('fec','templates','make_member_desk_00.tpl'),
    ]
    source_state={rel:_file_sha(p(rel)) for rel in source_files}
    input_hash=_sha(source_state); state_path=p('dashboard_integrity_state.json')
    prior=json.load(open(state_path,encoding='utf-8')) if os.path.exists(state_path) else None
    if prior and prior.get('input_fingerprint')==input_hash:
        _check(prior.get('output_semantic_sha256')==output_hash,
               'same dashboard inputs produced a different semantic bundle', errors)
    report={'status':'pass' if not errors else 'fail','errors':errors,'warnings':warnings,
            'preflight':preflight_report,'counts':{'members':len(members),'articles':article_total,
                'bills':bill_total,'members_with_social':len(social_members)},
            'input_fingerprint':input_hash,'output_semantic_sha256':output_hash,
            'regeneration_match': None if not prior or prior.get('input_fingerprint')!=input_hash else not errors,
            'missing_bioguide_enrichment':missing_bio,'exclusion_reconciliation':reconciliation}
    if errors: raise IntegrityError('; '.join(errors[:8]))
    MC.dump_atomic(report,p('dashboard_integrity_report.json'),indent=2,ensure_ascii=False)
    MC.dump_atomic({'input_fingerprint':input_hash,'output_semantic_sha256':output_hash},state_path,indent=2)
    return report
