/* Original Chart Studio shelves -> verified server query. No worksheet sums. */
(function(root){
  'use strict';
  const core=typeof module!=='undefined'&&module.exports?require('./chart-studio-core.js'):root.MentatStudioCore;
  const MONEY=new Set(['amount','gross_amount','refunds','average_amount','median_amount','min_amount','max_amount','q1_amount','q3_amount','stddev_amount']);
  const BASIS={receipt:['Published included receipts','Matches the workbook’s included receipts. Economic uniqueness remains unresolved; intermediary stages may overlap.'],original_observed:['Observed original giving (provisional)','Evidence-aware original giving. Ambiguous observations remain provisional.'],original_supported:['Supported original giving (gross subset)','Positive amounts supported by the current evidence rules. Refunds are excluded; this is a partial gross subset.'],raw:['Raw source observations','Includes excluded and repeated source representations. This is not a giving total.'],pac_activity:['PAC activity on recipient receipts','Recipient-reported activity is separate from original giving and is not a complete spending ledger.']};
  const AGG={sum:'amount',mean:'average_amount',count:'records',median:'median_amount',min:'min_amount',max:'max_amount'};
  const EXTRA_MARKS=[['heatmap','Heat map'],['highlight','Highlight table'],['stacked','Stacked bars'],['dot','Circle view'],['series-dot','Side-by-side circles'],['treemap','Treemap'],['bubbles','Packed bubbles'],['gantt','Observed date span'],['bullet','Bullet comparison'],['combination','Dual combination'],['dual-line','Dual lines'],['filled-map','Filled state map']];
  const types=new Set(['automatic','bar','line','area','circle','text','map','pie','doughnut','waterfall','pareto','radar','histogram','box',...EXTRA_MARKS.map(m=>m[0])]);
  const TIME=['date','year','cycle','quarter','month'];
  function fields(catalog,basis='receipt'){
    return catalog.map((f,index)=>({...f,index,name:f.id==='amount'?(basis==='original_supported'?'Supported gross amount':'Selected amount'):f.label||f.name||f.id,type:f.type||(f.role==='measure'?'number':f.id==='date'?'date':'category'),is_time:TIME.includes(f.id),visible:true,unit:f.unit}));
  }
  const RULES={'heat-map':['heatmap',2,1],'highlight-table':['highlight',2,1],'stacked-bars':['stacked',2,1],'circle-views':['dot',1,1],'side-by-side-circles':['series-dot',2,1],'treemap':['treemap',1,1],'packed-bubbles':['bubbles',1,1],'histogram':['histogram',0,1],'box-and-whisker':['box',0,1],'gantt':['gantt',1,0],'bullet-graph':['bullet',0,2],'dual-combination':['combination',1,2,true],'dual-lines':['dual-line',1,2,true]};
  function showMeEligibility(selection){
    return core.showMeEligibility(selection).map(tile=>{
      if(RULES[tile.id]){const[type,d,m,time]=RULES[tile.id],missing=[];if(selection.dimensions<d)missing.push(d+' dimension'+(d===1?'':'s'));if(selection.measures<m)missing.push(m+' measure'+(m===1?'':'s'));if(time&&!selection.times)missing.push('a date dimension');return {...tile,enabled:!missing.length,requirement:`${d} or more Dimensions, ${m} or more Measures`,reason:missing.length?'Needs '+missing.join(' and '):'',note:['histogram','box'].includes(type)?'Computed from individual selected observation amounts on the server.':type==='gantt'?'First-to-last observed receipt dates, not continuous giving.':type==='bullet'?'Two measures with the same unit; the second is a comparison, not an inferred target.':'Uses the selected source groups; no repeated aggregation of subtotals.'};}
      if(['circle-views','side-by-side-circles','scatter-plot'].includes(tile.id)){
        const dimensions=tile.id==='circle-views'?1:tile.id==='side-by-side-circles'?2:0;
        const missing=[];if(selection.measures<2)missing.push('2 measures');if(selection.dimensions<dimensions)missing.push(dimensions+' dimension'+(dimensions===1?'':'s'));
        return {...tile,enabled:!missing.length,requirement:(dimensions?dimensions+' or more Dimensions, ':'0 or more Dimensions, ')+'2 plotted Measures',reason:missing.length?'Needs '+missing.join(' and '):'',note:'Compares the first two selected measures as circles. Dimensions define each group'+(tile.id==='side-by-side-circles'?'; the second dimension supplies Colour.':'.')};
      }
      if(['symbol-map','filled-map'].includes(tile.id))return {...tile,enabled:true,requirement:'Contributor ZIP or State, summed Selected amount',note:'Creates verified ZIP/state marks with optional state and congressional boundaries.',reason:''};
      return tile;
    });
  }
  function showMeApply(tileId,state,columns,selected){
    if(RULES[tileId]){
      const selection=core.showMeSelection(state,columns,selected),rule=RULES[tileId];if(!showMeEligibility(selection).find(t=>t.id===tileId)?.enabled)return structuredClone(state);
      const next=structuredClone(state),dims=selection.fields.filter(f=>f.role==='dimension'),measures=selection.fields.filter(f=>f.role==='measure'),p=f=>({column:f.index,aggregation:'sum'});
      next.columns=(rule[3]?dims.filter(f=>f.isTime).slice(0,1):rule[0]==='histogram'?[]:dims.slice(0,rule[1]||8)).map(p);
      next.rows=(['histogram','box','gantt'].includes(rule[0])?[columns.find(f=>f.id==='amount')]:measures.slice(0,rule[2])).filter(Boolean).map(p);
      if(rule[0]==='histogram'&&columns.some(f=>f.id==='amount_bin')){next.columns=[p(columns.find(f=>f.id==='amount_bin'))];next.rows=[p(columns.find(f=>f.id==='records'))];}
      next.marks={type:rule[0],color:null,size:null,label:null,detail:[],tooltip:[]};next.analytics={...next.analytics,transform:'none'};return next;
    }
    if(!['circle-views','side-by-side-circles','scatter-plot'].includes(tileId))return core.showMeApply(tileId,state,columns,selected);
    const selection=core.showMeSelection(state,columns,selected),tile=showMeEligibility(selection).find(t=>t.id===tileId);if(!tile?.enabled)return structuredClone(state);
    const next=core.showMeApply('scatter-plot',state,columns,selected),dimensions=selection.fields.filter(f=>f.role==='dimension');
    next.marks.detail=dimensions.map(f=>({column:f.index,aggregation:'sum'}));
    if(tileId==='side-by-side-circles')next.marks.color={column:dimensions[1].index,aggregation:'sum'};
    return next;
  }
  function filterValue(value,field){
    if(field.unit==='date'){if(!/^\d{4}-\d{2}-\d{2}$/.test(String(value)))throw new Error('Enter an ISO date, YYYY-MM-DD.');return String(value);}
    if(field.role!=='measure')return String(value??'');
    if(!/^-?(?:\d+(?:\.\d*)?|\.\d+)$/.test(String(value).trim()))throw new Error('Enter a number without currency symbols or commas.');
    const number=Number(value),converted=MONEY.has(field.id)?number*100:number,result=Math.round(converted);
    if(!Number.isSafeInteger(result)||Math.abs(converted-result)>0.00001)throw new Error(MONEY.has(field.id)?'Use at most two decimal places for money.':'Use a whole observation count.');
    return result;
  }
  function clauses(filter,field){
    const op=filter.op,values=Array.isArray(filter.value)?filter.value:[filter.value];
    if(op==='in'||op==='notin'){
      const chosen=values.filter(v=>v!==''&&v!=null).map(v=>filterValue(v,field));
      if(!chosen.length)return [];
      if(chosen.length>1000)throw new Error('Choose at most 1,000 members, or use Is not one of.');
      return op==='in'?[{field:field.id,op:'in',value:chosen}]:chosen.map(value=>({field:field.id,op:'ne',value}));
    }
    if(op==='between'){
      const out=[];
      if(values[0]!==''&&values[0]!=null)out.push({field:field.id,op:'gte',value:filterValue(values[0],field)});
      if(values[1]!==''&&values[1]!=null)out.push({field:field.id,op:'lte',value:filterValue(values[1],field)});
      return out;
    }
    const simple={equals:'eq',contains:'contains',gte:'gte',lte:'lte'}[op];
    if(!simple)throw new Error('Choose a supported filter operation.');
    if(field.role==='measure'&&simple==='contains')throw new Error('Numeric filters use Equals, At least, At most or Between.');
    if(filter.value===''||filter.value==null)return [];
    return [{field:field.id,op:simple,value:filterValue(filter.value,field)}];
  }
  function compile(state,columns,{dataset,basis='receipt',offset=0}={}){
    const byIndex=new Map(columns.map(f=>[f.index,f])),attach=list=>core.shelf(list).map(p=>({...p,field:byIndex.get(p.column)})).filter(p=>p.field);
    const axes=attach([...(state.columns||[]),...(state.rows||[])]),dimensions=[],measures=[],allMeasures=[],notes=[];
    const addDim=f=>{if(!dimensions.includes(f.id))dimensions.push(f.id);};
    const measure=p=>{const id=p.field.id;if(id==='amount')return AGG[p.aggregation]||'amount';if(p.aggregation!=='sum')throw new Error(p.field.name+' is computed directly from source observations. Use its default aggregation.');return id;};
    axes.filter(p=>p.field.role==='dimension').forEach(p=>addDim(p.field));
    axes.filter(p=>p.field.role==='measure').forEach(p=>{const id=measure(p);if(!measures.includes(id))measures.push(id);});
    const mark=state.marks||{},color=attach(mark.color==null?[]:[mark.color])[0],size=attach(mark.size==null?[]:[mark.size])[0];
    const labels=attach(mark.label==null?[]:[mark.label]),tooltip=attach(mark.tooltip),detail=attach(mark.detail);
    for(const p of [...(color?[color]:[]),...detail,...labels,...tooltip])if(p.field.role==='dimension')addDim(p.field);
    if(color&&color.field.role!=='dimension')throw new Error('Colour uses a dimension to separate series.');
    if(detail.some(p=>p.field.role==='measure'))throw new Error('Detail uses dimensions to define one mark per group.');
    if(!measures.length)throw new Error('Add a dollar or count measure to Rows or Columns.');
    allMeasures.push(...measures);
    const encoded=p=>p.field.role==='measure'?measure(p):p.field.id;
    for(const p of [...labels,...tooltip,...(size?[size]:[])])if(p.field.role==='measure'&&!allMeasures.includes(encoded(p)))allMeasures.push(encoded(p));
    let type=mark.type||'automatic';
    if(type==='automatic')type=dimensions.some(d=>TIME.includes(d))?'line':'bar';
    if(type==='circle'){if(measures.length!==2)throw new Error('Circle compares two measures. Place two measures on the shelves, or choose Bar.');type='scatter';}
    if(type==='text')type='table';
    const filled=type==='filled-map';if(filled)type='map';
    if(!types.has(mark.type||'automatic'))throw new Error('This chart type needs individual receipts. Switch Data source to Report worksheet, or select Bar, Line, Circle, Text or Map.');
    const transform=state.analytics?.transform||'none';
    if(transform!=='none'){
      const time=dimensions.findIndex(d=>['date','year','cycle'].includes(d));
      if(time<0)throw new Error('Period analysis needs Contribution date, Year or Election cycle on a shelf.');
      dimensions[time]=state.analytics.period==='year'?'year':state.analytics.period==='cycle'?'cycle':dimensions[time]==='date'?'year':dimensions[time];
      if(time)dimensions.unshift(dimensions.splice(time,1)[0]);
      if(measures.length!==1||measures[0]!=='amount')throw new Error('Period analysis requires one summed Selected amount measure.');
      if(transform!=='annual'&&dimensions.length!==1)throw new Error('Change and forecast analysis need one time dimension; filter a subject instead of splitting it into series.');
      type='line';
    }
    if(['line','area','combination','dual-line'].includes(type)&&!TIME.includes(dimensions[0]))throw new Error('Place a date, year, quarter, month or election cycle first on the shelves for a timeline.');
    if(size&&(size.field.role!=='measure'||type!=='scatter'))throw new Error('Size requires a measure and a Circle view with two measures.');
    if(size)notes.push('Circle size follows the absolute magnitude of '+size.field.name+'; signed values remain in the tooltip.');
    if(state.params?.splitMulti)throw new Error('Splitting source records across labels repeats money. Clear Split before charting contributions.');
    const filters=[],aggregate_filters=[];
    for(const f of state.filters||[]){const field=byIndex.get(Number(f.column));if(!field)continue;const target=f.stage==='aggregate'||field.role==='measure'&&field.id!=='amount'?aggregate_filters:filters;for(const clause of clauses(f,field))target.push(clause);}
    const page=attach(state.pages==null?[]:[state.pages])[0];
    if(page){if(page.field.role!=='dimension')throw new Error('Pages requires a dimension.');if(state.pageMember!=='')filters.push({field:page.field.id,op:'eq',value:state.pageMember});}
    const binWidth=Math.round(Number(state.params?.binWidth||100)*100);
    if(!Number.isSafeInteger(binWidth)||binWidth<1)throw new Error('Enter a positive bin width in dollars and cents.');
    if(type==='histogram'){dimensions.splice(0,dimensions.length,'amount_bin');measures.splice(0,measures.length,'records');allMeasures.splice(0,allMeasures.length,'records','amount');notes.push('Bins count individual observations; no group means or subtotals are used.');}
    if(type==='box'){measures.splice(0,measures.length,'median_amount');allMeasures.splice(0,allMeasures.length,'min_amount','q1_amount','median_amount','q3_amount','max_amount');notes.push('Quartiles use selected individual amounts. Whiskers show minimum and maximum, including outliers.');}
    if(type==='gantt'){measures.splice(0,measures.length,'span_days');allMeasures.splice(0,allMeasures.length,'first_date','last_date','span_days');notes.push('Shows the observed receipt date span, not a project duration or continuous giving.');}
    if(['heatmap','highlight','stacked'].includes(type)&&dimensions.length!==2)throw new Error('Choose exactly two grouping dimensions for this chart; put other fields on Filters.');
    if(['bullet','combination','dual-line'].includes(type)&&measures.length!==2)throw new Error('Choose exactly two plotted measures.');
    if(type==='map'){
      if(measures.length!==1||measures[0]!=='amount')throw new Error('A map uses summed Selected amount.');
      if(!dimensions.includes('zip5')&&!dimensions.includes('state'))throw new Error('Place Contributor ZIP or State on a shelf for a map.');
      if(dimensions.some(d=>!['zip5','state'].includes(d)))throw new Error('Maps group by ZIP and recorded State. Put other fields on Filters.');
      if(dimensions.includes('zip5')&&!dimensions.includes('state'))dimensions.push('state');
      if(color||size||labels.length||tooltip.length)notes.push('Map marks show ZIP, recorded states and selected amount.');
    }
    const limit=type==='map'?100000:type==='histogram'?10000:Math.min(1000,Math.max(1,Number(state.params?.maxGroups)||40));
    const chronological=['line','area','combination','dual-line','histogram'].includes(type),sort=chronological?[{field:dimensions[0],direction:'asc'}]:[{field:measures[0],direction:state.sort==='asc'?'asc':'desc'}];
    const query={dataset,basis,dimensions:[...new Set(dimensions)],measures:allMeasures,filters,aggregate_filters,sort,limit,offset:type==='map'||transform!=='none'?0:offset};
    if(transform!=='none')query.limit=100000;
    if(type==='histogram'||query.dimensions.includes('amount_bin')||filters.some(f=>f.field==='amount_bin'))query.bin_width_cents=binWidth;
    const spec={type,filled,binWidth,dimensions:query.dimensions,measures,color:color?.field.id||'',size:size?encoded(size):'',labelFields:labels.map(encoded),tooltip:tooltip.map(encoded),labels:!!state.showLabels,references:{average:!!state.analytics?.average,median:!!state.analytics?.median}};
    if(detail.length||labels.some(p=>p.field.role==='dimension')||tooltip.some(p=>p.field.role==='dimension'))notes.push('Detail, Label and Tooltip dimensions define the grouping behind each mark.');
    return {query,spec,notes,transform};
  }
  /* Graph and Chart Studio read the same workbook, so a difference between
     them is a fact about the question each one was asked, not about the
     money. reconcile() names that difference instead of leaving a reader to
     decide which of two numbers on two screens is the wrong one. Pure: it is
     handed the studio result, the basis it was drawn on, the Graph view for
     the same company and cycle, and the Graph controls that were set. */
  const RECONCILE_REASONS={
    basis:'the basis is not Published included receipts',
    graph_filter:'a Graph filter (employee level, giving type) has no verified field',
    workbook:'the workbook version differs',
    aggregate:'grouped filters apply after aggregation',
    cycle:'the Graph view is pinned to one election cycle and this sheet covers every cycle',
    unavailable:'the Graph total for this scope is not available',
    unexplained:'this is unexplained — report it'
  };
  function reconcile(result,basis,graphView,filters){
    const dollarsToCents=value=>Number.isFinite(Number(value))?Math.round(Number(value)*100):null;
    const wholeCents=value=>Number.isFinite(Number(value))?Math.round(Number(value)):null;
    const graphCents=graphView&&graphView.totals?dollarsToCents(graphView.totals.giving):null;
    const studioCents=result&&result.totals?wholeCents(result.totals.amount):null;
    const receiptCents=result&&result.comparison?wholeCents(result.comparison.receipt):null;
    const out={graphCents,studioCents,receiptCents,differenceCents:null,agree:false,reasonId:'',reason:''};
    if(graphCents===null||studioCents===null){out.reasonId='unavailable';out.reason=RECONCILE_REASONS.unavailable;return out;}
    out.differenceCents=studioCents-graphCents;
    if(basis==='receipt'&&out.differenceCents===0){out.agree=true;return out;}
    const scope=filters||{};
    const workbook=String((result.provenance||{}).workbook_sha256||'');
    const books=((graphView||{}).reports||[]).map(report=>String(report.sha256||'')).filter(Boolean);
    out.reasonId=basis!=='receipt'?'basis'
      :!scope.studioCycle&&scope.graphCycle?'cycle'
      :scope.tier||(scope.funding&&scope.funding!=='all')?'graph_filter'
      :workbook&&books.length&&!books.includes(workbook)?'workbook'
      :(result.reconciliation||{}).aggregate_filters_applied?'aggregate'
      :'unexplained';
    out.reason=RECONCILE_REASONS[out.reasonId];
    return out;
  }
  function markFilters(request,row){const filters=[...request.filters];if(row)for(const field of request.dimensions){const value=row[field];if(value!==undefined)filters.push({field,op:Array.isArray(value)?'in':'eq',value});}return filters;}
  function mapSelection(row){if(row.zip5&&Array.isArray(row.states)&&row.states.length)return {zip5:row.zip5,state:row.states};if(!row.zip5&&row.state)return {state:row.states||[row.state]};throw new Error('This map mark has no geographical source identity.');}
  const sameSource=(a,b)=>['workbook_sha256','database_sha256','index_token','query_engine_sha256','field_semantics_sha256'].every(k=>a?.[k]===b?.[k]);
  const quote=value=>'"'+String(typeof value==='string'&&/^\s*[=+@-]/.test(value)?"'"+value:value??'').replaceAll('"','""')+'"';
  function csv(result,request){const cols=result.columns;return '\uFEFF'+[cols.map(c=>c.id+(c.unit==='cents'?'_usd':'')).concat(['accounting_basis','source_workbook_sha256','database_sha256','analytical_index','query_engine_sha256','field_semantics_sha256','query_filters']).map(quote).join(','),...result.rows.map(row=>cols.map(c=>c.unit==='cents'&&row[c.id]!=null?row[c.id]/100:row[c.id]).concat([request.basis,result.provenance.workbook_sha256,result.provenance.database_sha256,result.provenance.index_token,result.provenance.query_engine_sha256,result.provenance.field_semantics_sha256,JSON.stringify({filters:request.filters,aggregate_filters:request.aggregate_filters,bin_width_cents:request.bin_width_cents})]).map(quote).join(','))].join('\r\n');}
  const api={fields,compile,clauses,filterValue,showMeEligibility,showMeApply,markFilters,mapSelection,sameSource,csv,reconcile,BASIS,MONEY,EXTRA_MARKS,RECONCILE_REASONS};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.MentatStudioContributions=api;
})(globalThis);
