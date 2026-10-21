"""Narrow Melange graph/payroll closure; closed aliases keep local state untouched."""
import gzip
import io
import json
from pathlib import PureWindowsPath
import types
from module_data_snapshot import MiB, ReadAliases, LimitedGzip, Snapshot, digest, load_source, parse, require

GENERATION='staffer_social_network_20260908_v8_math_primary'
VERIFICATION='staffer_social_network_20260908_v8_math_verification'
GRAPH_FILES={'staffer_social_edges':('edges','staffer_social_edges.ndjson.gz'),
 'staffer_social_node_scores':('node-scores','staffer_social_node_scores.ndjson.gz'),
 'staffer_trajectories':('trajectories','staffer_trajectories.ndjson.gz'),
 'staffer_office_moves':('office-moves','staffer_office_moves.ndjson.gz'),
 'membership_layer':('membership','staffer_social_membership_layer.ndjson.gz'),
 'revolving_layer':('revolving','staffer_social_revolving_layer.ndjson.gz'),
 'policy_layer':('policy','staffer_social_policy_layer.ndjson.gz'),
 'groups':('groups','staffer_social_groups.ndjson.gz'),
 'staffer_social_politico_review_layers':('review','staffer_social_politico_review_layers.ndjson.gz')}
UPSTREAM={'hill_person_spine':('spine','hill_personnel_spine_20260908_v8_primary/hill_person_spine.ndjson.gz'),
 'hill_member_office_index':('office-index','hill_personnel_spine_20260908_v8_primary/member_office_index.ndjson.gz')}
PAYROLL_SOURCES={
 'spine-receipt':'audits/staffer_network/hill_personnel_spine_20260908_v8_primary/hill_personnel_spine_receipt.json',
 'hill-spans':'audits/staffer_network/hill_personnel_spine_20260908_v8_primary/hill_person_office_spans.ndjson.gz',
 'house-observations':'audits/staffer_network/house_personnel_ledger_20260903_v5_primary/house_personnel_observations.ndjson.gz',
 'senate-employment':'audits/staffer_network/official_senate_payroll_2011_2026_employment_scope_v1/senate_payroll_employment_candidates_2011_2026.ndjson.gz',
 'senate-committee':'audits/staffer_network/senate_committee_payroll_20260903_v3_primary/senate_committee_payroll_candidates_2011_2026.ndjson.gz'}
PAYROLL_EVIDENCE='audits/staffer_network/payroll_identity_20260908_v8_primary/payroll_identity_evidence.json.gz'

def reference(value,allowed):
    """Compare only a compiled suffix; never open or resolve a receipt path."""
    require(isinstance(value,str) and 0<len(value)<2048 and '\x00' not in value)
    parts=PureWindowsPath(value).parts
    require('..' not in parts and '.' not in parts)
    matches=[key for key in allowed if tuple(parts[-len(key.split('/')):])==tuple(key.split('/'))]
    require(len(matches)==1)
    return matches[0]

def bounded_rows(path,*,max_records=2_000_000,max_bytes=2*1024*MiB,budget=None):
    total=records=0
    with gzip.open(path,'rb') as stream:
        while True:
            line=stream.readline(2*MiB+1)
            if not line:break
            total+=len(line);require(len(line)<=2*MiB and total<=max_bytes,'Compressed graph data exceeds its limit')
            if budget is not None:
                budget['bytes']+=len(line);require(budget['bytes']<=32*1024*MiB,'Compressed graph snapshot exceeds its aggregate limit')
            if line.strip():
                records+=1;require(records<=max_records,'Compressed graph data exceeds its record limit')
                value=parse(line);require(isinstance(value,dict));yield value

def validate_graph(snapshot):
    receipt,verification=snapshot.json('graph-receipt'),snapshot.json('graph-verification')
    require(receipt.get('schema_id')=='staffer-network-social-receipt-v1' and receipt.get('status')=='PASS')
    require(verification.get('schema_id')=='staffer-network-social-verification-receipt-v1' and verification.get('status')=='PASS' and not verification.get('failures'))
    require(not receipt.get('canonical_employment_promotions') and not receipt.get('canonical_identity_promotions'))
    rows=receipt.get('files');require(isinstance(rows,list) and len(rows)==len(GRAPH_FILES))
    mapping={};seen=set();base='audits/staffer_network/'
    for spec in rows:
        require(isinstance(spec,dict) and spec.get('role') in GRAPH_FILES and spec['role'] not in seen);seen.add(spec['role'])
        role,leaf=GRAPH_FILES[spec['role']];require(spec.get('path')==leaf);snapshot.matches(role,spec)
        mapping[base+GENERATION+'/'+leaf]=snapshot.files[role]
    inputs=receipt.get('inputs');require(isinstance(inputs,list))
    for name,(role,tail) in UPSTREAM.items():
        found=[item for item in inputs if isinstance(item,dict) and item.get('role')==name];require(len(found)==1)
        spec=found[0];reference(spec.get('path'),[tail]);snapshot.matches(role,spec)
        mapping[base+tail]=snapshot.files[role]
    mapping[base+GENERATION+'/staffer_social_network_receipt.json']=snapshot.files['graph-receipt']
    mapping[base+VERIFICATION+'/staffer_social_network_verification_receipt.json']=snapshot.files['graph-verification']
    twins=verification.get('twin_byte_identity');require(isinstance(twins,list))
    found=[row for row in twins if isinstance(row,dict) and row.get('path')=='staffer_social_network_receipt.json'];require(len(found)==1)
    row=found[0];require(row.get('identical') is True and row.get('primary_sha256')==row.get('twin_sha256')==snapshot.objects['graph-receipt']['sha256'])
    source=load_source(snapshot.source_file('fec/surfaces/staffer_graph_snapshot.py'))
    require(source.GENERATION==GENERATION and source.VERIFICATION==VERIFICATION)
    aliases=ReadAliases(mapping,snapshot.root)
    graph=source.StaticGraph(str(snapshot.root));graph.root=aliases.path(base.rstrip('/'))
    budget={'bytes':0}
    # The reviewed receipt emits 5,312,984 edge rows. Keep an explicit growth
    # allowance without applying the much smaller ancillary-file limit to it.
    source.rows=lambda path:bounded_rows(path,max_records=8_000_000 if path.name=='staffer_social_edges.ndjson.gz' else 2_000_000,
        max_bytes=(16 if path.name=='staffer_social_edges.ndjson.gz' else 2)*1024*MiB,budget=budget)
    graph.load();require(not graph.errors,'Compiled graph reader rejected the snapshot')
    return graph

def validate_payroll(snapshot):
    config=snapshot.json('config');require(isinstance(config,dict))
    require(reference(config.get('path'),[PAYROLL_EVIDENCE])==PAYROLL_EVIDENCE);snapshot.matches('evidence',config)
    mapping={**{relative:snapshot.files[role] for role,relative in PAYROLL_SOURCES.items()},PAYROLL_EVIDENCE:snapshot.files['evidence'],'config.json':snapshot.files['config']}
    aliases=ReadAliases(mapping,snapshot.root)
    source=load_source(snapshot.source_file('fec/surfaces/staffer_payroll_identity.py'))
    def checked_load(stream):
        bundle=parse(stream.read())
        require(isinstance(bundle,dict) and bundle.get('version')=='payroll-identity-rows-v1')
        bindings=bundle.get('sources');require(isinstance(bindings,list) and len(bindings)==len(PAYROLL_SOURCES));seen=set()
        for binding in bindings:
            require(isinstance(binding,dict));relative=reference(binding.get('path'),PAYROLL_SOURCES.values())
            role=next(role for role,key in PAYROLL_SOURCES.items() if key==relative)
            require(role not in seen);seen.add(role);snapshot.matches(role,binding)
            aliases.alias(binding['path'],relative)
        return bundle
    source.Path=aliases.path
    source.json=types.SimpleNamespace(load=checked_load,loads=parse)
    source.gzip=types.SimpleNamespace(open=lambda path,*args,**kwargs:LimitedGzip(path,256*MiB))
    def loader(_original_root=None,*,config_path=None):
        # Original paths are caller context only; all inputs are compiled roles.
        return source.load_payroll_identity(aliases.path(''),config_path=aliases.path('config.json'))
    result=loader()
    require(isinstance(result,dict) and isinstance(result.get('counts'),dict),'Compiled payroll reader rejected the snapshot')
    return loader

def validate(snapshot):
    if snapshot.kind=='melange.staffer-graph-core.v1':validate_graph(snapshot)
    elif snapshot.kind=='melange.payroll-identity-core.v1':validate_payroll(snapshot)
    else:require(False)

def configure_readers(request):
    """Native component binding; never redirects the app's writable root.

    The backend may replace only its StaticGraph factory or its imported
    load_payroll_identity callable. LiveService/source_root and global Path
    remain unchanged, preserving local assertions, captures, account/state DBs.
    """
    snapshot=Snapshot(request)
    if snapshot.kind=='melange.staffer-graph-core.v1':
        graph=validate_graph(snapshot)
        readers={'graph':graph,'graph_factory':lambda _original_root=None:graph}
    elif snapshot.kind=='melange.payroll-identity-core.v1':
        readers={'payroll_loader':validate_payroll(snapshot)}
    else:require(False)
    for role,path in snapshot.files.items():require(digest(path)==snapshot.objects[role]['sha256'])
    return {**readers,'appId':snapshot.app,'kind':snapshot.kind,
        'coverage':{'completeKind':True,'fullApplication':False}}
