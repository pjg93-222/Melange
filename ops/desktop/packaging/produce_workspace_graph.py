"""Local publisher projection/parity gate. No network or signing operation.

The candidate evaluator supplies a fixed program-owned layout to the actual
graph algorithm. It is explicitly not a native installation test. After real
comparisons pass, the final separate evaluation uses the ordinary strict
VerifiedDisplayInput constructor with its completed new parity receipt.
"""
import argparse
import gc
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import shutil
import types

from module_data_snapshot import GRAPH, Snapshot, digest, load_source, parse, require
from melange_module_data import GRAPH_FILES, UPSTREAM
from workspace_data_contract import DISPLAY_GRAPH_KIND
from workspace_graph import VerifiedDisplayInput, canonical_sha
from workspace_publication import PublicationProjection, assert_public_record


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def snapshot_request(root, source):
    files, objects = {}, []
    for role,(leaf,_limit) in GRAPH.items():
        path=root/leaf;files[role]=str(path.resolve());size=path.stat().st_size;sha=digest(path)
        objects.append({'role':role,'bytes':size,'sha256':sha,
                        'segments':[{'asset':role+'.bin','bytes':size,'sha256':sha}]})
    return {'appId':'melange','kind':DISPLAY_GRAPH_KIND,'sourceRoot':str(source.resolve()),
            'snapshotRoot':str(root.resolve()),'files':files,'objects':objects}


def build(root, parents, selected):
    root.mkdir(exist_ok=False);(root/'graph').mkdir()
    projection=PublicationProjection();counts={};files={}
    for name,(role,_leaf) in {**GRAPH_FILES,**UPSTREAM}.items():
        item=selected['graph.'+name];source=Path(item['source'])
        require(digest(source)==item['recordedSha256'],'Pinned graph source changed')
        before=source.stat();target=root/GRAPH[role][0];count=0;decoded=0
        with gzip.open(source,'rb') as incoming,target.open('xb') as handle:
            with gzip.GzipFile(fileobj=handle,mode='wb',filename='',mtime=0,compresslevel=6) as output:
                for line in itertools.islice(incoming,10000) if role=='edges' else incoming:
                    if not line.strip():
                        raise ValueError('Unexpected blank row in the selected graph generation')
                    decoded+=len(line)
                    require(len(line)<=2*1024**2 and decoded<=4*1024**3,'Graph producer decoded budget exceeded')
                    value=projection.record(parse(line),'graph/'+role+'/[]')
                    assert_public_record(value)
                    output.write(encoded(value)+b'\n');count+=1
                    require(count<=2_000_000,'Graph projection row budget exceeded')
        after=source.stat()
        require((before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)==
                (after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns),'Graph source changed during projection')
        files[role]={'bytes':target.stat().st_size,'sha256':digest(target),'records':count};counts[role]=count
        print(json.dumps({'phase':'projected','role':role,**files[role]}),flush=True)
    parent_receipt=projection.record(parents['receipt']['document'],'graph/parent-receipt')
    parent_verification=projection.record(parents['verification']['document'],'graph/parent-verification')
    source_edge=next(row for row in parents['receipt']['document']['files'] if row['role']=='staffer_social_edges')
    receipt={'schemaVersion':1,'kind':DISPLAY_GRAPH_KIND,
        'parent':{name:{'originalSha256':parents[name]['sha256'],'projectedSha256':canonical_sha(document),'document':document}
                  for name,document in (('receipt',parent_receipt),('verification',parent_verification))},
        'projection':{'method':'first-10000-emitted-co-tenure-rows','sourceRecords':source_edge['records'],
                      'roleLocationProjection':{'/nodes/*/label_provenance/path':'hill_member_office_index'},
                      'displayRecords':counts['edges'],'sourceEdgesSha256':source_edge['sha256']},'files':files}
    (root/GRAPH['graph-receipt'][0]).write_bytes(encoded(receipt))
    # PENDING is honest and cannot pass the production constructor.
    (root/GRAPH['graph-verification'][0]).write_bytes(encoded({'status':'PENDING','kind':DISPLAY_GRAPH_KIND}))
    return receipt,projection.receipt()


def candidate_graph(source, original_root, root, receipt):
    graph=source.StaticGraph(original_root)
    def layout(_graph):
        _graph.receipt=receipt['parent']['receipt']['document']
        _graph.verification=receipt['parent']['verification']['document']
        def artifact(name):
            require(name in GRAPH_FILES)
            role,_leaf=GRAPH_FILES[name]
            return _graph._verified(root/GRAPH[role][0],receipt['files'][role],name)
        def upstream(name):
            require(name in UPSTREAM)
            role,_leaf=UPSTREAM[name]
            return _graph._verified(root/GRAPH[role][0],receipt['files'][role],name)
        return artifact,upstream
    graph._input_layout=types.MethodType(layout,graph)
    graph.load();require(not graph.errors,'Projected graph algorithm refused candidate input')
    return graph


def compare(before, after):
    queries=['','a','s','john','washington',*sorted(before.nodes)[:3]]
    comparisons={
        'nodeIds':set(before.nodes)==set(after.nodes),
        'edgeIds':[row['id'] for row in before.edges]==[row['id'] for row in after.edges],
        'searchRanks':before._rank == after._rank and before._search_words == after._search_words
                      and all(before.search_ids(query,limit)==after.search_ids(query,limit)
                              for query in queries for limit in (0,1,25,700)),
        'pageBoundaries':True,
        'layerCounts':before.layer_counts==after.layer_counts,
        'sourceBounds':before.source_node_count==after.source_node_count and before.receipt['edge_counts']==after.receipt['edge_counts'],
    }
    # Compare every numerical/categorical value returned by actual graph views;
    # only physical provenance paths/hashes and explicit projection annotation
    # differ intentionally across original and new immutable roots.
    def factual(value, locations, context=''):
        if isinstance(value,dict):
            return {key:factual(child,locations,context+'/'+key) for key,child in value.items() if key not in ('sources','display_projection')}
        if isinstance(value,list):return [factual(child,locations,context+'/*') for child in value]
        if isinstance(value,str) and value in locations:
            # Only actual byte-verified source locations can become logical
            # role citations. Unknown path/string fields remain unchanged.
            require(context.endswith(('/provenance/path','/provenance/identity_path','/artifact_path','/label_provenance/path')),
                    'An undeclared graph source-location representation changed')
            return 'verified-graph-source:'+locations[value]
        return value
    receipts=[]
    projection=PublicationProjection()
    for query in queries:
        for limit in (1,25,700):
            left,right=before.view(query,limit),after.view(query,limit)
            for value,graph in ((left,before),(right,after)):
                require(value['sources']==graph.sources and all(item.get('verified') is True for item in graph.sources),
                        'Graph source bindings changed')
            left=factual(left,{item['path']:item['role'] for item in before.sources})
            right=factual(right,{item['path']:item['role'] for item in after.sources})
            left,right=projection.record(left),projection.record(right)
            same=left==right
            comparisons['pageBoundaries'] &= same
            receipts.append({'querySha256':canonical_sha(query),'limit':limit,
                             'originalSha256':canonical_sha(left),'projectedSha256':canonical_sha(right),
                             'equal':same})
    return comparisons,receipts


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-manifest',type=Path,required=True)
    parser.add_argument('--source-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--reuse-projections',action='store_true',help='Recheck both fixed existing artifact trees; never reuse a PASS/status marker')
    options=parser.parse_args()
    require(shutil.disk_usage(options.output.parent).free>=17*1024**3,'Release disk reserve is unavailable')
    if not options.reuse_projections:options.output.mkdir(exist_ok=False)
    selected={item['role']:item for item in json.loads(options.source_manifest.read_text(encoding='utf-8'))['melange']}
    parents={}
    for name in ('receipt','verification'):
        path=Path(selected['graph.'+name]['source']);raw=path.read_bytes()
        parents[name]={'sha256':hashlib.sha256(raw).hexdigest(),'document':parse(raw)}
    original_root=Path(selected['graph.receipt']['source']).parents[3]
    code=options.source_root/'fec/surfaces/staffer_graph_snapshot.py';code_sha=digest(code)
    source=load_source(code)
    baseline=source.StaticGraph(original_root);baseline.load()
    require(not baseline.errors,'Original pinned graph is not ready')
    print(json.dumps({'phase':'original-ready','nodes':len(baseline.nodes),'edges':len(baseline.edges)}),flush=True)
    if options.reuse_projections:
        first=parse((options.output/'first'/GRAPH['graph-receipt'][0]).read_bytes())
        second=parse((options.output/'second'/GRAPH['graph-receipt'][0]).read_bytes())
        require(all(first['parent'][name]['originalSha256']==parents[name]['sha256'] for name in parents),'Projection parent changed')
        for role,spec in first['files'].items():
            require(digest(options.output/'first'/GRAPH[role][0])==digest(options.output/'second'/GRAPH[role][0])==spec['sha256'],'Existing projection bytes changed')
        for document,tree in ((first,'first'),(second,'second')):
            document['projection']['roleLocationProjection']={'/nodes/*/label_provenance/path':'hill_member_office_index'}
            (options.output/tree/GRAPH['graph-receipt'][0]).write_bytes(encoded(document))
        transformations={'scope':'Original two-build data remains unchanged; final API comparison applies the same approved metadata projection to both sides.'}
    else:
        first,transformations=build(options.output/'first',parents,selected)
        second,_other=build(options.output/'second',parents,selected)
    deterministic=first==second
    require(deterministic,'Graph projection was not byte deterministic')
    candidate=candidate_graph(source,original_root,options.output/'first',first)
    comparisons,api_receipts=compare(baseline,candidate)
    (options.output/'private-comparison-progress.json').write_bytes(encoded({'comparisons':comparisons,'actualApiReceipts':api_receipts}))
    require(all(comparisons.values()),'Graph display projection changed actual endpoint results')
    del candidate
    gc.collect()
    proof={'schemaVersion':1,'kind':DISPLAY_GRAPH_KIND,'status':'PASS','failures':[],
           'receiptSha256':digest(options.output/'first'/GRAPH['graph-receipt'][0]),
           'comparisons':comparisons,'deterministicBuild':{role:spec['sha256'] for role,spec in first['files'].items()}}
    (options.output/'first'/GRAPH['graph-verification'][0]).write_bytes(encoded(proof))
    snapshot=Snapshot(snapshot_request(options.output/'first',options.source_root))
    display=VerifiedDisplayInput(snapshot)
    empty_root=options.output/'empty-private-root'
    if not empty_root.exists():empty_root.mkdir()
    final=source.StaticGraph(empty_root,display_input=display);final.load()
    require(not final.errors,'Final strict display reader refused projection')
    native_comparisons,native_api=compare(baseline,final)
    require(all(native_comparisons.values()),'Final strict display reader changed actual endpoint results')
    require(digest(code)==code_sha,'Graph program changed during the producer gate')
    result={'schemaVersion':1,'privateEvidence':True,'publicationReady':False,'codeSha256':code_sha,
            'originalRoot':str(original_root),'sourceManifestSha256':digest(options.source_manifest),
            'candidateEvaluation':'Publisher-only fixed-role layout; final ordinary VerifiedDisplayInput constructor checked separately.',
            'twoBuildsByteIdentical':True,'originalDataRootUnavailableToFinalConstructor':True,
            'comparisonNormalization':'Exact approved local-source/authentication metadata projection on both sides; all node ranks/search words remain exactly equal before normalization.',
            'comparisons':comparisons,'actualApiReceipts':api_receipts,
            'strictNativeComparisons':native_comparisons,'strictNativeApiReceipts':native_api,
            'privateTransformations':transformations,'objects':snapshot.request if hasattr(snapshot,'request') else snapshot.objects,
            'projectedCompressedBytes':sum(spec['bytes'] for spec in first['files'].values())}
    target=options.output/'private-graph-projection-receipt.json';target.write_bytes(encoded(result))
    print(json.dumps({'receipt':str(target),'sha256':digest(target),'status':'PASS','bytes':result['projectedCompressedBytes']}),flush=True)


if __name__=='__main__':main()
