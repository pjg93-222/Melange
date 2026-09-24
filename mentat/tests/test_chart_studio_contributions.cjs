'use strict';
const {test}=require('node:test');const assert=require('node:assert/strict');
const studio=require('../app/chart-studio-contributions.js'),core=require('../app/chart-studio-core.js');
const catalog=[...['company','cycle','date','year','zip5','state','recipient'].map(id=>({id,label:id,role:'dimension'})),...['amount','records','contributors','average_amount','gross_amount'].map(id=>({id,label:id,role:'measure',unit:id==='records'||id==='contributors'?'count':'cents'}))];
const columns=studio.fields(catalog),index=id=>columns.find(f=>f.id===id).index,pill=(id,aggregation='sum')=>({column:index(id),aggregation});
function sheet(){const s=core.createSheet('A');s.columns=[pill('company')];s.rows=[pill('amount')];s.marks.type='bar';return s;}
const compile=s=>studio.compile(s,columns,{dataset:'Banking',basis:'receipt'});
test('original shelves query source observations once and preserve independent dimensions',()=>{const s=sheet();s.rows.push(pill('state'));s.marks.detail=[pill('recipient')];s.marks.color=pill('cycle');const r=compile(s);assert.deepEqual(r.query.dimensions,['company','state','cycle','recipient']);assert.deepEqual(r.query.measures,['amount']);assert.equal(r.query.basis,'receipt');assert.equal(r.query.limit,60);});
test('measure aggregation requests actual source statistics, without summing group means or distincts',()=>{const s=sheet();s.rows=[pill('amount','mean'),pill('contributors')];assert.deepEqual(compile(s).query.measures,['average_amount','contributors']);s.rows=[pill('contributors','mean')];assert.throws(()=>compile(s),/computed directly/);});
test('ZIP map queries state eligibility and forbids allocating through unrelated grain',()=>{const s=sheet();s.marks.type='map';s.columns=[pill('zip5')];const r=compile(s);assert.deepEqual(r.query.dimensions,['zip5','state']);assert.equal(r.query.limit,100000);s.columns.push(pill('company'));assert.throws(()=>compile(s),/Put other fields on Filters/);});
test('money filters are cents; measure filters can run after grouping',()=>{const s=sheet();s.filters=[{column:index('amount'),op:'gte',value:'12.50'},{column:index('contributors'),op:'gte',value:'2',stage:'aggregate'},{column:index('zip5'),op:'equals',value:'01234'}];const r=compile(s);assert.deepEqual(r.query.filters,[{field:'amount',op:'gte',value:1250},{field:'zip5',op:'eq',value:'01234'}]);assert.deepEqual(r.query.aggregate_filters,[{field:'contributors',op:'gte',value:2}]);assert.throws(()=>studio.filterValue('1.001',columns[index('amount')]),/two decimal/);});
test('Pages limits source observations and Size/Label/Tooltip request truthful encodings',()=>{const s=sheet();s.pages=pill('cycle');s.pageMember='2023-2024';s.rows.push(pill('contributors'));s.marks.type='circle';s.marks.size=pill('records');s.marks.label=pill('state');s.marks.tooltip=[pill('gross_amount')];const r=compile(s);assert.equal(r.spec.type,'scatter');assert.equal(r.spec.size,'records');assert.deepEqual(r.spec.labelFields,['state']);assert.deepEqual(r.query.dimensions,['company','state']);assert.deepEqual(r.query.measures,['amount','contributors','gross_amount','records']);assert.deepEqual(r.query.filters,[{field:'cycle',op:'eq',value:'2023-2024'}]);});
test('style-only changes do not change query identity and temporal queries preserve complete periods',()=>{const s=sheet(),before=compile(s).query;s.fit='width';s.showLabels=true;s.analytics.average=true;assert.deepEqual(compile(s).query,before);s.columns=[pill('date')];s.analytics.transform='annual';s.analytics.period='cycle';assert.deepEqual(compile(s).query.dimensions,['cycle']);assert.equal(compile(s).query.limit,100000);});
test('distributions query individual source statistics and monetary splitting stays prohibited',()=>{const s=sheet();s.marks.type='histogram';assert.deepEqual(compile(s).query.dimensions,['amount_bin']);assert.deepEqual(compile(s).query.measures,['records','amount']);s.marks.type='box';assert.deepEqual(compile(s).query.measures,['min_amount','q1_amount','median_amount','q3_amount','max_amount']);s.marks.type='bar';s.params.splitMulti=true;assert.throws(()=>compile(s),/repeats money/);});
test('verified Show Me separates categorical circles from two-measure scatter and enables source distributions',()=>{
 const one=core.showMeSelection(sheet(),columns,[]),verified=studio.showMeEligibility(one),worksheet=core.showMeEligibility(one);
 assert.equal(verified.find(t=>t.id==='circle-views').enabled,true);assert.equal(verified.find(t=>t.id==='side-by-side-circles').enabled,false);assert.equal(verified.find(t=>t.id==='scatter-plot').enabled,false);assert.match(verified.find(t=>t.id==='scatter-plot').reason,/2 measures/);
 for(const id of ['histogram','box-and-whisker']){assert.equal(verified.find(t=>t.id===id).enabled,true);assert.match(verified.find(t=>t.id===id).note,/individual/);assert.equal(worksheet.find(t=>t.id===id).enabled,true);}
 assert.equal(worksheet.find(t=>t.id==='circle-views').enabled,true);
});
test('circle tiles create categorical circles while scatter keeps both measures and exact dimensions',()=>{
 const s=sheet();s.rows.push(pill('contributors'));s.columns.push(pill('state'));
 for(const [id,type] of [['circle-views','dot'],['side-by-side-circles','series-dot'],['scatter-plot','scatter']]){const next=studio.showMeApply(id,s,columns,[]),result=compile(next);assert.equal(result.spec.type,type);assert.deepEqual(result.query.measures,['amount','contributors']);assert.deepEqual(result.query.dimensions,['company','state']);assert.deepEqual(next.columns,s.columns);assert.deepEqual(next.rows,s.rows);}
});
test('Show Me preserves existing shelves, mean and filters for treemaps and horizontal bars',()=>{
 const s=sheet();s.rows=[pill('amount','mean')];s.columns.push(pill('state'));s.filters=[{column:index('cycle'),op:'equals',value:'2023-2024'}];
 for(const id of ['treemap','horizontal-bars']){const next=studio.showMeApply(id,s,columns,[]);assert.deepEqual(next.columns,s.columns);assert.deepEqual(next.rows,s.rows);assert.deepEqual(next.filters,s.filters);assert.deepEqual(compile(next).query.measures,['average_amount']);}
});
test('reconcile names why Graph and Studio differ, and says so plainly when they do not',()=>{
 const base={totals:{amount:1209041200},comparison:{receipt:1209041200},provenance:{workbook_sha256:'w'.repeat(64)},reconciliation:{aggregate_filters_applied:false}};
 const graph={totals:{giving:12090412},reports:[{name:'Banking.xlsx',sha256:'w'.repeat(64)}]};
 const clean={tier:'',funding:'all'},wider=amount=>({...base,totals:{amount}});
 const agree=studio.reconcile(base,'receipt',graph,clean);
 assert.equal(agree.agree,true);assert.equal(agree.graphCents,1209041200);assert.equal(agree.studioCents,1209041200);
 assert.equal(agree.differenceCents,0);assert.equal(agree.reason,'');
 // A different basis is a different question, so the strip must not call it agreement.
 const basis=studio.reconcile(wider(990000000),'original_observed',graph,clean);
 assert.equal(basis.agree,false);assert.equal(basis.reasonId,'basis');assert.match(basis.reason,/uses a different basis than Graph/);
 // A Graph employee-level or giving-type filter has no verified field, so the Studio total is the wider one.
 assert.equal(studio.reconcile(wider(1300000000),'receipt',graph,{tier:'Chief',funding:'all'}).reasonId,'graph_filter');
 assert.equal(studio.reconcile(wider(1300000000),'receipt',graph,{tier:'',funding:'personal'}).reasonId,'graph_filter');
 // Two different workbooks are not reconcilable by arithmetic.
 assert.equal(studio.reconcile(wider(1300000000),'receipt',{...graph,reports:[{sha256:'z'.repeat(64)}]},clean).reasonId,'workbook');
 assert.equal(studio.reconcile({...wider(1300000000),reconciliation:{aggregate_filters_applied:true}},'receipt',graph,clean).reasonId,'aggregate');
 const unexplained=studio.reconcile(wider(1300000000),'receipt',graph,clean);
 assert.equal(unexplained.reasonId,'unexplained');assert.equal(unexplained.differenceCents,90958800);
 // No Graph total is an absence, never a difference to explain.
 assert.equal(studio.reconcile(base,'receipt',null,clean).reasonId,'unavailable');
 assert.equal(studio.reconcile(base,'receipt',{totals:{}},clean).reasonId,'unavailable');
 assert.equal(studio.reconcile({totals:{}},'receipt',graph,clean).reasonId,'unavailable');
});
test('drill-through keeps exact ZIP and all selected raw state variants',()=>{const query={dimensions:['zip5','state'],filters:[{field:'company',op:'eq',value:'A'}]};assert.deepEqual(studio.markFilters(query,{zip5:'01234',state:['MA',' ma ']}),[...query.filters,{field:'zip5',op:'eq',value:'01234'},{field:'state',op:'in',value:['MA',' ma ']}]);});
test('state-only map marks retain exact state filters and unidentified marks never select every record',()=>{const selection=studio.mapSelection({kind:'state',state:'MA',states:['MA',' ma '],amount_cents:125});assert.deepEqual(studio.markFilters({dimensions:['state'],filters:[]},selection),[{field:'state',op:'in',value:['MA',' ma ']}]);assert.deepEqual(studio.mapSelection({state:'MA'}),{state:['MA']});assert.throws(()=>studio.mapSelection({amount_cents:100}),/no geographical/);});
test('CSV exports cents as USD and preserves source, query and filtering provenance',()=>{const result={columns:[{id:'zip5'},{id:'amount',unit:'cents'}],rows:[{zip5:'01234',amount:-1250}],provenance:{workbook_sha256:'workbook',database_sha256:'source',index_token:'index',query_engine_sha256:'engine'}};const value=studio.csv(result,{basis:'receipt',filters:[],aggregate_filters:[]});assert.match(value,/"01234","-12.5"/);assert.match(value,/database_sha256/);assert.match(value,/query_engine_sha256/);assert.match(value,/"receipt","workbook","source","index","engine"/);assert.equal(studio.sameSource(result.provenance,{...result.provenance,index_token:'changed'}),false);});
