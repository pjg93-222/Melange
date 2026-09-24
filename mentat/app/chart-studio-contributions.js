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
  // Board S1's Data pane, by catalog id and in the board's order: Industry, Election cycle,
  // Contribution year, Company, Contribution date, Recipient, Recipient category, Party, State, ZIP;
  // Selected amount, Gift count (an observation is not always one gift, so it keeps its name
  // Observation count) and Contributors (distinct reported donor identities). S1's Candidate and
  // Net receipts have no field of their own: the catalog carries no candidate name, and the net
  // amount of the chosen basis is the field shown as Selected amount.
  const PANE_FIELDS={dimensions:['industry','cycle','year','company','date','recipient','recipient_category','party','state','zip5'],measures:['amount','records','contributors']};
  function fields(catalog,basis='receipt'){
    return catalog.map((f,index)=>({...f,index,name:f.id==='amount'?(basis==='original_supported'?'Supported gross amount':'Selected amount'):f.label||f.name||f.id,type:f.type||(f.role==='measure'?'number':f.id==='date'?'date':'category'),is_time:TIME.includes(f.id),visible:true,unit:f.unit}));
  }
  const RULES={'heat-map':['heatmap',2,1],'highlight-table':['highlight',2,1],'stacked-bars':['stacked',2,1],'circle-views':['dot',1,1],'side-by-side-circles':['series-dot',2,1],'treemap':['treemap',1,1],'packed-bubbles':['bubbles',1,1],'histogram':['histogram',0,1],'box-and-whisker':['box',0,1],'gantt':['gantt',1,0],'bullet-graph':['bullet',0,2],'dual-combination':['combination',1,2,true],'dual-lines':['dual-line',1,2,true]};
  // Paul, 2026-09-23: "...all graph types properly register and nothing is logically constrained".
  // Every tile is enabled on verified data as on a worksheet: a rule is what a tile prefers, `fits`
  // says whether the shelves hold it, and a click draws with what is there.
  const fill=missing=>missing.length?'Draws with the fields on the shelves and picks '+missing.join(' and ')+' from the source':'';
  function showMeEligibility(selection){
    return core.showMeEligibility(selection).map(tile=>{
      if(RULES[tile.id]){const[type,d,m,time]=RULES[tile.id],missing=[];if(selection.dimensions<d)missing.push((d-selection.dimensions)+' dimension'+(d-selection.dimensions===1?'':'s'));if(selection.measures<m)missing.push((m-selection.measures)+' measure'+(m-selection.measures===1?'':'s'));if(time&&!selection.times)missing.push('a date dimension');return {...tile,mark:type,enabled:true,reason:'',fits:!missing.length,missing,fill:fill(missing),requirement:`${d} or more Dimensions, ${m} or more Measures`,note:['histogram','box'].includes(type)?'Computed from individual selected observation amounts on the server.':type==='gantt'?'First-to-last observed receipt dates, not continuous giving.':type==='bullet'?'Two measures with the same unit; the second is a comparison, not an inferred target.':type==='dot'?'One circle per group at its value.':type==='series-dot'?'One circle series per Colour member.':'Uses the selected source groups; no repeated aggregation of subtotals.'};}
      if(tile.id==='scatter-plot'){const missing=selection.measures<2?[(2-selection.measures)+' measure'+(2-selection.measures===1?'':'s')]:[];return {...tile,enabled:true,reason:'',fits:!missing.length,missing,fill:fill(missing),requirement:'0 or more Dimensions, 2 plotted Measures',note:'Compares the first two selected measures as circles; one measure draws one circle per group.'};}
      if(['symbol-map','filled-map'].includes(tile.id))return {...tile,enabled:true,reason:'',fits:true,missing:[],fill:'',requirement:'Contributor ZIP or State, summed Selected amount',note:'Creates verified ZIP/state marks with optional state and congressional boundaries.'};
      return tile;
    });
  }
  // A tile changes the mark and keeps every pill, filter, aggregate, encoding and analysis (census
  // B-S28). Empty shelves are seeded from the fields in use, then from the source.
  function showMeApply(tileId,state,columns,selected){
    if(['symbol-map','filled-map'].includes(tileId)){
      const next=structuredClone(state);next.marks={...next.marks,type:tileId==='filled-map'?'filled-map':'map'};return next;
    }
    const rule=RULES[tileId];
    if(!rule)return core.showMeApply(tileId,state,columns,selected);
    const next=structuredClone(state);next.marks={...next.marks,type:rule[0]};if(next.marks.orientation)delete next.marks.orientation;
    if(core.shelf(state.columns).length||core.shelf(state.rows).length)return next;
    const selection=core.showMeSelection(state,columns,selected),meta=core.classifyFields(columns,state.types),p=f=>({column:f.index,aggregation:'sum'});
    const inUse=selection.fields,dims=[...inUse.filter(f=>f.role==='dimension'),...meta.dimensions.filter(f=>!inUse.includes(f))],measures=[...inUse.filter(f=>f.role==='measure'),...meta.measures.filter(f=>!inUse.includes(f))];
    const times=dims.filter(f=>f.isTime),plain=dims.filter(f=>!f.isTime);
    next.columns=(rule[3]?(times.length?times:plain).slice(0,1):rule[0]==='histogram'?[]:[...plain,...times].slice(0,rule[1])).map(p);
    next.rows=(['histogram','box','gantt'].includes(rule[0])?[columns.find(f=>f.id==='amount')]:measures.slice(0,Math.max(1,rule[2]))).filter(Boolean).map(p);
    if(rule[0]==='histogram'&&columns.some(f=>f.id==='amount_bin')){next.columns=[p(columns.find(f=>f.id==='amount_bin'))];next.rows=[p(columns.find(f=>f.id==='records'))];}
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
  // `notes`, when given, turns the two composition refusals into notes (census B-S35, B-S36): a list
  // over 1,000 members sends its first 1,000, and text matching on a number is dropped.
  function clauses(filter,field,notes){
    const op=filter.op,values=Array.isArray(filter.value)?filter.value:[filter.value];
    if(op==='in'||op==='notin'){
      let chosen=values.filter(v=>v!==''&&v!=null).map(v=>filterValue(v,field));
      if(!chosen.length)return [];
      if(chosen.length>1000){if(!notes)throw new Error('Choose at most 1,000 members, or use Is not one of.');notes.push(field.name+' filter sends its first 1,000 of '+chosen.length+' members; use Is not one of to keep every member.');chosen=chosen.slice(0,1000);}
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
    if(field.role==='measure'&&simple==='contains'){if(!notes)throw new Error('Numeric filters use Equals, At least, At most or Between.');notes.push(field.name+' cannot be matched as text, so its Contains filter is left out; use Equals, At least, At most or Between.');return [];}
    if(filter.value===''||filter.value==null)return [];
    return [{field:field.id,op:simple,value:filterValue(filter.value,field)}];
  }
  /* ------------------------------------------- what the sort controls do
     One account, read by compile() below and by the toolbar, so a button can
     never claim something the query does not do.

     sheet().sort is none | asc | desc | az | za and opens at 'none'
     (chart-studio-core.js createSheet). Paul, 2026-09-23: "nothing is logically
     constrained" - so every mark sorts (census B-S16). 'none' is the view's own
     order: chronological when the first dimension is a time axis (or the
     histogram's bins), otherwise largest first, which is why this path has
     always read 'none' as descending there. asc and desc order the groups by
     the first measure on every mark; az and za by the first dimension's label. */
  const effectiveSort=state=>(state&&state.sort)==='asc'?'asc':'desc';
  const SORT_LOCK_TIME='Time views keep chronological order';
  const SORT_LOCK_BINS='A histogram keeps its bins in numeric order';
  const CHRONOLOGICAL=['line','area','combination','dual-line'];
  const ORDERED=['date','year','cycle','quarter','month','amount_bin'];
  const orderedAxis=dimensions=>ORDERED.includes((dimensions||[])[0]);
  function querySort(state,dimensions,measures){
    const stored=(state&&state.sort)||'none',first=(dimensions||[])[0];
    if((stored==='az'||stored==='za')&&first)return [{field:first,direction:stored==='az'?'asc':'desc'}];
    if(stored==='asc'||stored==='desc')return [{field:measures[0],direction:stored}];
    return orderedAxis(dimensions)?[{field:first,direction:'asc'}]:[{field:measures[0],direction:'desc'}];
  }
  // Retired (census B-S16): no mark refuses to be sorted. Kept for older callers, answering "no lock".
  function sortLock(){return '';}
  /* Paul, 2026-09-23: "nothing is logically constrained". The None button used to be disabled
     wherever 'none' asked the server the same question as Descending (a category axis, largest
     first). A stored 'none' keeps that meaning - it is every new sheet's and every saved view's
     order - and None now stores 'source': the same query (the page holds the largest groups),
     listed client-side in the groups' own order, A to Z with numbers ascending. On a time axis or
     a histogram's bins 'source' is the chronological/bin order 'none' already is. */
  const naturalOrder=(state,dimensions)=>(state&&state.sort)==='source'&&(dimensions||[]).length>0&&!orderedAxis(dimensions);
  function naturalRows(rows,dimensions){
    const dims=dimensions||[];
    return (rows||[]).map((row,at)=>({row,at})).sort((a,b)=>{for(const d of dims){const c=String(a.row[d]??'').localeCompare(String(b.row[d]??''),undefined,{numeric:true});if(c)return c;}return a.at-b.at;}).map(item=>item.row);
  }

  /* -------------------------------------------- which marks can be labelled
     Every mark type this path accepts or produces. Paul's words above: every
     renderer draws value labels (engine contract V05, W8), so every entry is
     `true`. A table's marks are its value cells, so its Labels button shows or
     hides the printed values (hidden values stay on hover and in the CSV), the
     way a text table reads with mark labels off; it is never disabled.
     app/tests/chart-studio-contributions-sort.test.js fails if a producible
     type is missing from the table or a stale one is left in it. */
  const LABEL_SUPPORT={
    automatic:true,bar:true,line:true,area:true,circle:true,scatter:true,
    heatmap:true,dot:true,'series-dot':true,stacked:true,histogram:true,bubbles:true,
    highlight:true,treemap:true,box:true,gantt:true,bullet:true,combination:true,'dual-line':true,
    pie:true,doughnut:true,waterfall:true,pareto:true,radar:true,map:true,'filled-map':true,
    text:true,table:true
  };
  // Period analysis keeps its labels too (contract W8: charts.js draws them).
  const LABELLED_TRANSFORMS=['none','annual','yoy','change','forecast'];
  const LABEL_LOCK_TRANSFORM='Period analysis is drawn on the report canvas, which has no mark labels';
  function labelLock(type){
    const support=LABEL_SUPPORT[type];
    if(support===true)return '';
    return support||'This mark type does not draw labels';
  }

  // Paul, 2026-09-23: "Additionally, within the Chart Studio make sure everything is freely
  // flexible, that all graph types properly register and nothing is logically constrained, it
  // needs to be utterly maluable." compile() throws only when no field at all is placed (and for a
  // mark id no menu offers); every other refusal became a note, and the query asks for what the
  // server can answer (engine contract, section G-V).
  const TIMELINE=['line','area','combination','dual-line'];
  function compile(state,columns,{dataset,industry,basis='receipt',offset=0}={}){
    const byIndex=new Map(columns.map(f=>[f.index,f])),attach=list=>core.shelf(list).map(p=>({...p,field:byIndex.get(p.column)})).filter(p=>p.field);
    const axes=attach([...(state.columns||[]),...(state.rows||[])]),dimensions=[],measures=[],allMeasures=[],notes=[],computed=new Set();
    const addDim=f=>{if(!dimensions.includes(f.id))dimensions.push(f.id);};
    const addTo=(list,id)=>{if(id&&!list.includes(id))list.push(id);};
    const nameOf=id=>(columns.find(f=>f.id===id)||{}).name||id;
    const measure=p=>{const id=p.field.id;if(id==='amount')return AGG[p.aggregation]||'amount';if(p.aggregation!=='sum'&&!computed.has(id)){computed.add(id);notes.push(p.field.name+' is computed directly from source observations, so it keeps its source statistic.');}return id;};
    const mark=state.marks||{},color=attach(mark.color==null?[]:[mark.color])[0],size=attach(mark.size==null?[]:[mark.size])[0];
    const labels=attach(mark.label==null?[]:[mark.label]),tooltip=attach(mark.tooltip),detail=attach(mark.detail);
    if(!axes.length&&!color&&!size&&!labels.length&&!tooltip.length&&!detail.length)throw new Error('Add a dollar or count measure to Rows or Columns.');
    axes.filter(p=>p.field.role==='dimension').forEach(p=>addDim(p.field));
    axes.filter(p=>p.field.role==='measure').forEach(p=>addTo(measures,measure(p)));
    for(const p of [...(color?[color]:[]),...detail,...labels,...tooltip,...(size?[size]:[])])if(p.field.role==='dimension')addDim(p.field);
    const count=columns.some(f=>f.id==='records')?'records':'amount';
    if(!measures.length){measures.push(count);notes.push('No measure is placed, so each mark counts '+(count==='records'?'source observations':'the selected amount')+'.');}
    allMeasures.push(...measures);
    const encoded=p=>p.field.role==='measure'?measure(p):p.field.id;
    const colorMeasure=color&&color.field.role==='measure'?encoded(color):'';
    const sizeMeasure=size&&size.field.role==='measure'?encoded(size):'';
    if(size&&!sizeMeasure)notes.push('Size follows a measure; '+size.field.name+' joins the grouping instead.');
    const tipMeasures=[...tooltip,...detail].filter(p=>p.field.role==='measure').map(encoded);
    for(const id of [...labels.filter(p=>p.field.role==='measure').map(encoded),...tipMeasures,sizeMeasure,colorMeasure])addTo(allMeasures,id);
    let type=mark.type||'automatic';
    if(!types.has(type))throw new Error('Not available for verified data. Use Bar, Line, Circle, Text or Map, or switch to Report worksheet.');
    if(type==='automatic')type=dimensions.some(d=>TIME.includes(d))?'line':'bar';
    // Circle with two or more measures is a scatter ([0] x, [1] y, the rest in the tooltip); with one
    // it is one circle per group at its value.
    if(type==='circle')type=measures.length>=2?'scatter':'dot';
    if(type==='text')type='table';
    const filled=type==='filled-map';if(filled)type='map';
    let transform=state.analytics?.transform||'none';
    // Distributions, spans, maps and scatters have no period axis: the analysis is left off and said so.
    if(transform!=='none'&&['histogram','box','gantt','map','scatter'].includes(type)){notes.push('Period analysis draws marks along a time axis, so this '+(type==='scatter'?'circle':type==='map'?'map':type)+' view is drawn without it.');transform='none';}
    if(transform!=='none'){
      const time=dimensions.findIndex(d=>['date','year','cycle'].includes(d));
      if(time<0){notes.push('Period analysis needs Contribution date, Year or Election cycle on a shelf, so the chart is drawn without it.');transform='none';}
      else{
        dimensions[time]=state.analytics.period==='year'?'year':state.analytics.period==='cycle'?'cycle':dimensions[time]==='date'?'year':dimensions[time];
        if(time)dimensions.unshift(dimensions.splice(time,1)[0]);
        // Contract V11/W5: the chosen mark is kept, and every measure and every other dimension is
        // its own series over the periods.
      }
    }
    let categorical=false;
    if(TIMELINE.includes(type)&&transform==='none'){
      const time=dimensions.findIndex(d=>TIME.includes(d));
      if(time>0){dimensions.unshift(dimensions.splice(time,1)[0]);notes.push(nameOf(dimensions[0])+' leads the axis, so every other group is its own line.');}
      else if(time<0)categorical=true;
    }
    const needsSecond=['bullet','combination','dual-line'].includes(type)&&measures.length<2&&!(color&&color.field.role==='dimension');
    if(needsSecond){const second=['amount','records','contributors'].find(id=>id!==measures[0]&&columns.some(f=>f.id===id));if(second){measures.push(second);addTo(allMeasures,second);notes.push(nameOf(second)+' is the second measure; put another measure on the shelves to choose it.');}}
    if(sizeMeasure)notes.push('Mark size follows the absolute magnitude of '+size.field.name+'; signed values remain in the tooltip.');
    if(state.params?.splitMulti)notes.push('Split multi-value cells applies to report worksheets; verified source records are never multi-valued, so it is not used here.');
    const filters=[],aggregate_filters=[];
    for(const f of state.filters||[]){const field=byIndex.get(Number(f.column));if(!field)continue;const target=f.stage==='aggregate'||field.role==='measure'&&field.id!=='amount'?aggregate_filters:filters;try{for(const clause of clauses(f,field,notes))target.push(clause);}catch(error){notes.push(field.name+' filter is left out: '+error.message);}}
    const page=attach(state.pages==null?[]:[state.pages])[0];
    if(page){if(page.field.role!=='dimension')notes.push('Pages steps through a dimension; '+page.field.name+' is a measure, so Pages is not applied.');else if(state.pageMember!=='')filters.push({field:page.field.id,op:'eq',value:state.pageMember});}
    let binWidth=Math.round(Number(state.params?.binWidth||100)*100);
    if(!Number.isSafeInteger(binWidth)||binWidth<1){notes.push('The histogram bin width must be a positive amount in dollars and cents, so $100 bins are used.');binWidth=10000;}
    if(type==='histogram'){
      const keep=color&&color.field.role==='dimension'?[color.field.id]:[],dropped=dimensions.filter(d=>!keep.includes(d)&&d!=='amount_bin');
      dimensions.splice(0,dimensions.length,'amount_bin',...keep);measures.splice(0,measures.length,'records');allMeasures.splice(0,allMeasures.length,'records','amount');
      notes.push('Bins count individual observations; no group means or subtotals are used.'+(dropped.length?' '+dropped.map(nameOf).join(', ')+(dropped.length===1?' is':' are')+' not binned; put a field on Colour to stack the bins by it.':''));
    }
    if(type==='box'){measures.splice(0,measures.length,'median_amount');allMeasures.splice(0,allMeasures.length,'min_amount','q1_amount','median_amount','q3_amount','max_amount');notes.push('Quartiles use selected individual amounts. Whiskers show minimum and maximum, including outliers.');}
    if(type==='gantt'){measures.splice(0,measures.length,'span_days');allMeasures.splice(0,allMeasures.length,'first_date','last_date','span_days');notes.push('Shows the observed receipt date span, not a project duration or continuous giving.');}
    if(type==='map'){
      if(!dimensions.includes('zip5')&&!dimensions.includes('state')){type='bar';notes.push('A map groups by Contributor ZIP or State; neither is on a shelf, so this view is drawn as bars.');}
      else{
      if(dimensions.includes('zip5')&&!dimensions.includes('state'))dimensions.push('state');
        const others=dimensions.filter(d=>!['zip5','state'].includes(d));
        if(others.length)notes.push('Each map mark combines every '+others.map(nameOf).join(' / ')+' group at its place; put '+(others.length===1?'it':'them')+' on Filters to map one.');
        if(measures[0]!=='amount')notes.push('The map shades by '+nameOf(measures[0])+'.');
        addTo(allMeasures,'amount');
        if(color||size||labels.length||tooltip.length)notes.push('Map marks show ZIP, recorded states and selected amount.');
      }
    }
    const wanted=state.params?.maxGroups;
    const limit=type==='map'?100000:type==='histogram'?10000:wanted==='all'?100000:Math.min(100000,Math.max(1,Number(wanted)||60));
    if(wanted==='all'&&type!=='map'&&type!=='histogram')notes.push('All groups: the server returns up to 100,000 groups per page.');
    const queryDimensions=[...new Set(dimensions)];
    const sort=querySort(state,queryDimensions,measures);
    // A time axis ordered by a measure is read in that order, not as elapsed time (contract V01).
    if(TIMELINE.includes(type)&&transform==='none'&&sort[0].field!==queryDimensions[0])categorical=true;
    let dual=false;
    // Contract V03: dual axes over a category axis are one panel of bars or a line with the second
    // measure on a right axis; over a time axis contribution-charts draws them.
    if(['combination','dual-line'].includes(type)&&categorical){dual=true;type=type==='combination'?'bar':'line';}
    const query={dataset,basis,dimensions:queryDimensions,measures:allMeasures,filters,aggregate_filters,sort,limit,offset:type==='map'||transform!=='none'?0:offset};
    if(industry)query.industry=industry;
    if(transform!=='none')query.limit=100000;
    if(type==='histogram'||query.dimensions.includes('amount_bin')||filters.some(f=>f.field==='amount_bin'))query.bin_width_cents=binWidth;
    const spec={type,filled,binWidth,dimensions:query.dimensions,measures,color:color&&color.field.role==='dimension'?color.field.id:'',size:sizeMeasure,labelFields:labels.map(encoded),tooltip:[...tooltip.map(encoded),...detail.filter(p=>p.field.role==='measure').map(encoded)],labels:!!state.showLabels,references:{average:!!state.analytics?.average,median:!!state.analytics?.median}};
    if(colorMeasure)spec.colorMeasure=colorMeasure;
    if(categorical)spec.categorical=true;
    if(dual){spec.dual=true;spec.dualMark='line';}
    if(naturalOrder(state,queryDimensions)&&transform==='none'&&type!=='map')spec.naturalOrder=true;
    if(type==='stacked'&&spec.color)spec.stack='stacked';
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
    basis:'this sheet uses a different basis than Graph',
    graph_filter:'a Graph filter (employee level or giving type) is not carried',
    workbook:'the workbook version differs',
    aggregate:'grouped filters apply after aggregation',
    cycle:'the Graph view shows one election cycle and this sheet shows all of them',
    unavailable:'the Graph view has no total for this scope',
    unexplained:'the cause is unknown; report it'
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
  const api={fields,PANE_FIELDS,compile,clauses,filterValue,showMeEligibility,showMeApply,markFilters,mapSelection,sameSource,csv,reconcile,effectiveSort,querySort,orderedAxis,naturalOrder,naturalRows,sortLock,labelLock,BASIS,MONEY,EXTRA_MARKS,RECONCILE_REASONS,LABEL_SUPPORT,MARK_TYPES:types,SORT_LOCK_TIME,SORT_LOCK_BINS,LABEL_LOCK_TRANSFORM,LABELLED_TRANSFORMS,CHRONOLOGICAL,TIMELINE};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.MentatStudioContributions=api;
})(globalThis);
