"""Read-only query planning over the validated contribution index.

The accounting index remains authoritative. This layer computes one grouped
selection and one population summary without rebuilding monetary decisions.
"""
from contextlib import closing, contextmanager
import json
from pathlib import Path
import threading

import contribution_data as data
import contribution_query_store as store
import contribution_semantics as semantics

LOADED_STAMP=data._stamp(__file__)
LOADED_SHA256=data._hash(__file__)
_metadata_memory_slot=threading.Semaphore(1)


@contextmanager
def _metadata_workspace(db,source,refs):
    # Avoid disk-backed automatic-index churn on narrow metadata views. Only
    # one such workspace runs at a time; wider/larger sources retain SQLite's
    # disk-backed temporary storage. This does not modify either source DB.
    keys=set(refs)&set(semantics.RAW)
    source_path=source.get('database')
    eligible=bool(keys and len(keys)<=4 and source_path and Path(source_path).stat().st_size<=1024**3)
    if not eligible:
        yield
        return
    with _metadata_memory_slot:
        db.execute('PRAGMA temp_store=MEMORY')
        db.execute('PRAGMA main.cache_size=-32768')
        yield


def _check_loaded():
    semantics.check()
    if data._stamp(__file__)!=LOADED_STAMP:
        raise ValueError('Contribution query code changed. Restart the app to load the current query rules.')


def _scan_table(filters,table='facts'):
    # GROUP BY ZIP otherwise encourages ~N random lookups through a noncovering
    # index into wide facts. Preserve useful selective equality/range indexes.
    selective=any(isinstance(f,dict) and f.get('field') in ('company','zip5','state','committee_id')
                  and f.get('op') in ('eq','equals','in') for f in filters)
    if table!='facts':return table
    return 'facts' if selective else 'facts NOT INDEXED'


def _plan(request,basis,dims,measures,limit,offset,group_table='facts',summary_table='facts',raw_relation=None):
    column=data.BASES[basis][1]
    filters=request.get('filters',[])
    row_where,params=semantics.row_filter(filters,column)
    include=column+' != 0' if basis!='raw' else '1'
    where=row_where+' AND '+include
    aggregate_filters=request.get('aggregate_filters',[])
    if not isinstance(aggregate_filters,list):raise ValueError('Aggregate filters must be a list.')
    filter_measures=[f.get('field') for f in aggregate_filters if isinstance(f,dict) and f.get('field') in semantics.MEASURES]
    all_measures=list(dict.fromkeys(measures+['amount','records','contributors']+filter_measures))
    having,having_params=data._filter(aggregate_filters,set(all_measures))
    sort=request.get('sort') or [{'field':'amount','direction':'desc'}]
    if not isinstance(sort,list) or len(sort)>8:raise ValueError('Choose a valid sort order.')
    order=[];sort_measures=[]
    for item in sort:
        if not isinstance(item,dict) or item.get('field') not in dims+all_measures or item.get('direction','asc') not in ('asc','desc'):
            raise ValueError('Choose valid sort fields and directions.')
        field='CAST(amount_bin AS INTEGER)' if item['field']=='amount_bin' else '"'+item['field']+'"'
        order.append(field+' '+item.get('direction','asc').upper())
        if item['field'] in semantics.MEASURES:sort_measures.append(item['field'])
    order+=['"'+d+'" ASC' for d in dims]
    group_measures=list(dict.fromkeys(measures+['amount']+filter_measures+sort_measures))
    expressions=semantics.expressions(column)
    select=['"'+d+'"' for d in dims]+[expressions[m]+' AS "'+m+'"' for m in group_measures]
    refs=dims+all_measures+[f.get('field') for f in filters if isinstance(f,dict)]
    group_table=semantics.table(group_table,refs,request,raw_relation=raw_relation)
    summary_table=semantics.table(summary_table,all_measures+[f.get('field') for f in filters if isinstance(f,dict)],request,raw_relation=raw_relation)
    grouped='SELECT '+','.join(select)+' FROM '+_scan_table(filters,group_table)+' WHERE '+where+(' GROUP BY '+','.join('"'+d+'"' for d in dims) if dims else '')
    fields=dims+measures
    # A materialized CTE is shared by the summary and sorted page. Rank fixes
    # output order explicitly while permitting summary results on empty pages.
    grouped_sql='''WITH grouped AS MATERIALIZED ('''+grouped+'''),
        selected AS MATERIALIZED (SELECT * FROM grouped WHERE '''+having+'''),
        summary AS (SELECT COUNT(*) AS group_count,COALESCE(SUM(amount),0) AS grouped_amount FROM selected),
        page AS (SELECT *,ROW_NUMBER() OVER(ORDER BY '''+','.join(order)+''') AS _page_rank FROM selected
                 ORDER BY '''+','.join(order)+''' LIMIT ? OFFSET ?)
        SELECT 0 AS _page_rank,group_count AS _group_count,grouped_amount AS _grouped_amount,'''+','.join('NULL AS "'+f+'"' for f in fields)+''' FROM summary
        UNION ALL SELECT _page_rank,NULL,NULL,'''+','.join('"'+f+'"' for f in fields)+''' FROM page ORDER BY _page_rank'''
    selected_amount=column if basis=='raw' else 'CASE WHEN '+include+' THEN '+column+' END'
    totals_expr=semantics.expressions(selected_amount)
    totals_expr['records']='COUNT(*)' if basis=='raw' else 'COUNT(CASE WHEN '+include+' THEN 1 END)'
    totals_expr['contributors']='COUNT(DISTINCT contributor_key)' if basis=='raw' else 'COUNT(DISTINCT CASE WHEN '+include+' THEN contributor_key END)'
    summary_select=[totals_expr[m]+' AS "total__'+m+'"' for m in all_measures]
    comparison_expr={'receipt':'COALESCE(SUM(receipt_cents),0)',
        'original_observed':'COALESCE(SUM(original_cents),0)',
        'original_supported':'COALESCE(SUM(supported_cents),0)',
        'unresolved_gross_exposure':'COALESCE(SUM(CASE WHEN unresolved=1 THEN ABS(raw_cents) ELSE 0 END),0)',
        'unresolved_records':'COUNT(CASE WHEN unresolved=1 THEN 1 END)'}
    summary_select += [expr+' AS "comparison__'+key+'"' for key,expr in comparison_expr.items()]
    summary_select += ['COUNT(CASE WHEN ('+include+') AND zip5!=\'\' THEN 1 END) AS geo__valid',
                      'COALESCE(SUM(CASE WHEN ('+include+') AND zip5=\'\' THEN '+column+' ELSE 0 END),0) AS geo__unmapped']
    summary_sql='SELECT '+','.join(summary_select)+' FROM '+_scan_table(filters,summary_table)+' WHERE '+row_where
    return {'grouped_sql':grouped_sql,'grouped_params':params+having_params+[limit,offset],
            'summary_sql':summary_sql,'summary_params':params,'all_measures':all_measures,
            'comparison_fields':list(comparison_expr),'group_measures':group_measures}


def query(report_directory,request):
    _check_loaded()
    basis,dims,measures,limit,offset=semantics.validate(request)
    source=data._source(report_directory,request)
    path,pending=data._ready(source,retry=request.get('retry') is True)
    if pending:return pending
    token=data._token(source)
    result=_query_ready(path,request,source,basis,dims,measures,limit,offset)
    if data._token(source)!=token:raise ValueError('Contribution source changed while querying. Retry against the current source.')
    return result


def _query_ready(path,request,source,basis,dims,measures,limit,offset):
    _check_loaded()
    _plan(request,basis,dims,measures,limit,offset) # validate before any cache hit
    stamp=data._stamp(path)
    uses_raw=bool((set(dims)|{f.get('field') for f in request.get('filters',[]) if isinstance(f,dict)})&set(semantics.RAW))
    raw_path=Path(source['database']) if uses_raw and source.get('database') else None
    raw_stamp=data._stamp(raw_path) if raw_path else None
    def stable():
        _check_loaded();store._loaded()
        return store.source_stable(path,stamp) and (not raw_path or store.source_stable(raw_path,raw_stamp))
    if not stable():raise ValueError('A contribution or reported-metadata source has active writes. Retry after it is stable.')
    identity={'index':stamp,'raw_source':raw_stamp,'query_code':LOADED_SHA256,'semantics':semantics.SHA,'dataset':source['id'],'request':request}
    return store.cached('results',identity,
        lambda:_query_uncached(path,request,source,basis,dims,measures,limit,offset,stamp,stable),stable)


def _query_uncached(path,request,source,basis,dims,measures,limit,offset,stamp,stable):
    projected=store.view(path)
    projection_stamp=data._stamp(projected);proof_stamp=data._stamp(projected.with_suffix('.json'))
    def query_stable():
        return (stable() and store.source_stable(projected,projection_stamp)
            and data._stamp(projected.with_suffix('.json'))==proof_stamp)
    if not query_stable():raise ValueError('Query projection changed before its query started.')
    filters=request.get('filters',[])
    filter_refs=[f.get('field') for f in filters if isinstance(f,dict)]
    extra_measures=[f.get('field') for f in request.get('aggregate_filters',[]) if isinstance(f,dict)]
    group_deps=semantics.dependencies(dims+measures+extra_measures)
    filter_deps=semantics.dependencies(filter_refs+measures+extra_measures)
    group_table,summary_table=store.tables(group_deps,[{'field':f} for f in filter_deps])
    with closing(store._readonly(projected)) as db, _metadata_workspace(db,source,dims+filter_refs):
        if set(dims+filter_refs)&(set(semantics.AUDIT)|set(semantics.RAW)):
            db.execute('ATTACH DATABASE ? AS original',(Path(path).resolve().as_uri()+'?mode=ro',))
        relation=semantics.raw_relation(db,source,set(dims+filter_refs))
        plan=_plan(request,basis,dims,measures,limit,offset,group_table,summary_table,relation)
        semantics.register(db)
        db.create_aggregate('median_cent',1,data._Median)
        metadata=json.loads(db.execute("SELECT value FROM metadata WHERE key='manifest'").fetchone()[0])
        summary_key={'index':stamp,'query_code':LOADED_SHA256,'semantics':semantics.SHA,'basis':basis,
            'raw_source':data._stamp(source['database']) if set(filter_refs)&set(semantics.RAW) and source.get('database') else None,
            'filters':request.get('filters',[]),'bin_width_cents':request.get('bin_width_cents',10000),'measures':plan['all_measures']}
        summary=store.cached('summaries',summary_key,
            lambda:dict(db.execute(plan['summary_sql'],plan['summary_params']).fetchone()),query_stable)
        totals={m:summary['total__'+m] for m in plan['all_measures']}
        comparison={m:summary['comparison__'+m] for m in plan['comparison_fields']}
        geography={'observations':totals['records'],'valid_zip_observations':summary['geo__valid'],'unmapped_amount':summary['geo__unmapped']}
        groups=iter(db.execute(plan['grouped_sql'],plan['grouped_params']))
        first=next(groups);count=first['_group_count'];group_amount=first['_grouped_amount']
        result=[{key:row[key] for key in dims+measures} for row in groups]
    if not query_stable():raise ValueError('Query projection changed while computing its query.')
    notices=['Observed original giving remains provisional; supported giving is a subset, not a complete total.',metadata['identity_basis']]
    if basis=='raw':notices.append('Raw observations can repeat gifts, include excluded receipts and contain money stages that must not be added as giving.')
    if basis=='pac_activity':notices.append('PAC activity here is recipient-reported, not a complete outgoing Schedule B census.')
    if count>offset+len(result):notices.append('More groups are available. Totals cover all matching observations, not just this page.')
    if request.get('aggregate_filters'):notices.append('Totals and accounting comparisons describe row-filtered observations before the aggregate filter; grouped_amount_cents describes the retained groups.')
    return {'schema_version':data.VERSION,'status':'ready','dataset':source['id'],'basis':basis,'basis_label':'Supported original giving (gross subset)' if basis=='original_supported' else data.BASES[basis][0],
        'columns':[{**field,'name':'Supported gross amount' if basis=='original_supported' and field['id']=='amount' else field['label']} for key in dims+measures for field in semantics.fields() if field['id']==key],
        'rows':result,'totals':totals,'group_count':count,'offset':offset,'limit':limit,'has_more':offset+len(result)<count,
        'comparison':comparison,'geography':geography,'reconciliation':{'source_receipt_cents':metadata['totals']['receipt'],'expected_receipt_cents':metadata['expected_receipt_cents'],'receipt_matches_workbook':metadata['totals']['receipt']==metadata['expected_receipt_cents'],'filtered_amount_cents':totals['amount'],'grouped_amount_cents':group_amount,'aggregate_filters_applied':bool(request.get('aggregate_filters')),'conserved':group_amount==totals['amount'] if not request.get('aggregate_filters') else None},
        'provenance':{**metadata['provenance'],'ledger_run_id':metadata['ledger_run_id'],'query_engine_sha256':LOADED_SHA256,'field_semantics_sha256':semantics.SHA,'query_projection_sha256':store.LOADED_SHA},'notices':notices,'verified_unique':False}


def records(report_directory,request):
    _check_loaded()
    basis,_,_,limit,offset=semantics.validate(request)
    if limit>5000:raise ValueError('Drill-through page size must be at most 5,000.')
    if request.get('aggregate_filters'):raise ValueError('Drill through a selected group using its dimension filters.')
    source=data._source(report_directory,request);path,pending=data._ready(source,retry=request.get('retry') is True)
    if pending:return pending
    token=data._token(source);stamp=data._stamp(path);column=data.BASES[basis][1]
    raw_path=Path(source['database']) if source.get('database') else None;raw_stamp=data._stamp(raw_path) if raw_path else None
    if raw_path and not store.source_stable(raw_path,raw_stamp):raise ValueError('Reported-metadata source has active writes.')
    filters=request.get('filters',[]);where,params=semantics.row_filter(filters,column)
    if not request.get('include_excluded',False) and basis!='raw':where+=' AND '+column+' != 0'
    refs=request.get('dimensions',[])+[f.get('field') for f in filters if isinstance(f,dict)]
    with closing(data._ro(path)) as db, _metadata_workspace(db,source,refs):
        relation=semantics.raw_relation(db,source,refs)
        table=semantics.table('facts',refs,request,original=True,raw_relation=relation)
        count=db.execute('SELECT COUNT(*) FROM '+table+' WHERE '+where,params).fetchone()[0]
        rows=[dict(r) for r in db.execute('SELECT *,'+column+' AS amount_cents FROM '+table+' WHERE '+where+' ORDER BY date DESC,source_id LIMIT ? OFFSET ?',params+[limit,offset])]
    if not store.source_stable(path,stamp) or (raw_path and not store.source_stable(raw_path,raw_stamp)) or data._token(source)!=token:raise ValueError('Contribution source changed during record inspection.')
    for row in rows:
        row['reasons']=json.loads(row['reasons']);row['evidence_ids']=json.loads(row['evidence_ids']);row.pop('contributor_key',None)
    return {'schema_version':data.VERSION,'status':'ready','dataset':source['id'],'basis':basis,'rows':rows,'total_records':count,'offset':offset,'limit':limit,'has_more':offset+len(rows)<count,
        'provenance':{**data._provenance(source),'index_token':token,'query_engine_sha256':LOADED_SHA256,'field_semantics_sha256':semantics.SHA},'amount_unit':'cents'}
