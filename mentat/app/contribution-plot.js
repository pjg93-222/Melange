/* Contribution views consume server aggregates. Currency stays in integer cents. */
(function(root){
 'use strict';
 const NS='http://www.w3.org/2000/svg',palette=root.MentatTheme?.palette||['#276749','#477f9b','#aa7942','#805f87','#69783e','#ac6263','#527c77','#6f7499'];
 const moneyKeys=new Set(['amount','gross_amount','refunds','average_amount','median_amount','min_amount','max_amount','q1_amount','q3_amount','stddev_amount']);
 const isMoney=(id,columns=[])=>moneyKeys.has(id)||columns.some(c=>(c.id===id||c.name===id)&&['cents','currency','usd_cents'].includes(c.unit));
 function format(value,id,columns=[],compact=false){if(columns.some(c=>c.id===id&&c.unit==="date"))return value||"—";if(value==null||!Number.isFinite(Number(value)))return '—';return new Intl.NumberFormat('en-US',isMoney(id,columns)?{style:'currency',currency:'USD',maximumFractionDigits:compact?1:2,...(compact?{notation:'compact'}:{})}:{maximumFractionDigits:2,...(compact?{notation:'compact'}:{})}).format(isMoney(id,columns)?Number(value)/100:Number(value));}
 const label=(row,dimensions)=>dimensions.map(d=>row[d]==null||row[d]===''?'Unknown':String(row[d])).join(' / ')||'Selected population';
 const name=(id,columns)=>columns.find(c=>c.id===id)?.name||id.replaceAll('_',' ');
 /* Code review F2 (2026-09-24). A repeated aggregate group - the same value on
    every drawn dimension, which happens when a queried field is not drawn - is
    combined statistic by statistic, never by adding every number. Amounts and
    observation counts add; a mean is weighted by each group's observation
    count (the net amount over the observations when both are present); a
    population standard deviation is pooled from each group's count, mean and
    deviation; the minimum and maximum take the extremes; first and last dates
    widen the span and the span is recomputed from them. A median, a quartile
    or a distinct count cannot be rebuilt from group summaries, so a combined
    mark leaves it blank and the note says so. A field the chart does not draw
    keeps every value it had (a list), so a combined mark's drill-through asks
    for all of its groups' records. A worksheet column names its aggregation. */
 const COMBINE_RULE={amount:'sum',gross_amount:'sum',refunds:'sum',records:'sum',average_amount:'mean',stddev_amount:'stddev',min_amount:'min',max_amount:'max',first_date:'first',last_date:'last',span_days:'span',median_amount:'none',q1_amount:'none',q3_amount:'none',contributors:'distinct',committees:'distinct',companies:'distinct',active_days:'distinct'};
 function combineRule(id,columns=[]){
  if(COMBINE_RULE[id])return COMBINE_RULE[id];
  const column=columns.find(c=>c.id===id),agg=column&&column.aggregation;
  return agg==='sum'||agg==='count'?'sum':agg==='min'||agg==='max'?agg:agg==='countd'?'distinct':'none';
 }
 const finite=v=>typeof v==='number'&&Number.isFinite(v);
 const isDimensionField=(id,values,columns)=>{const column=columns.find(c=>c.id===id);if(column)return column.role==='dimension'||column.type==='category';return !COMBINE_RULE[id]&&!values.every(v=>v==null||finite(v));};
 const RANK={blank:3,weighted:2,pooled:2};
 function combineGroup(list,dims,columns=[]){
  const row={...list[0]},outcome={};
  const ids=[...new Set(list.flatMap(r=>Object.keys(r)))].filter(id=>!dims.includes(id));
  const meanOf=r=>finite(r.amount)&&finite(r.records)&&r.records>0?r.amount/r.records:finite(r.average_amount)?r.average_amount:null;
  const whole=values=>values.every(v=>Number.isInteger(v));
  for(const id of ids){
   const values=list.map(r=>r[id]),present=values.filter(v=>v!=null);
   if(isDimensionField(id,values,columns)){const distinct=[...new Map(present.map(v=>[JSON.stringify(v),v])).values()];row[id]=distinct.length>1?distinct:distinct.length?distinct[0]:values[0];continue;}
   const rule=combineRule(id,columns),numbers=present.filter(finite);
   if(rule==='first'||rule==='last'){const dates=present.map(String).sort();row[id]=dates.length?(rule==='first'?dates[0]:dates.at(-1)):null;outcome[id]='widened';continue;}
   if(rule==='sum'){row[id]=numbers.length?numbers.reduce((a,b)=>a+b,0):null;outcome[id]='added';continue;}
   if(rule==='min'||rule==='max'){row[id]=numbers.length?Math[rule](...numbers):null;outcome[id]=rule==='min'?'lowest':'highest';continue;}
   if(rule==='mean'||rule==='stddev'){
    const used=list.filter(r=>finite(r.records)&&r.records>0),complete=used.length&&list.every(r=>r[id]==null||finite(r.records))&&used.every(r=>finite(meanOf(r))&&(rule==='mean'||finite(r[id])));
    if(!complete){row[id]=null;outcome[id]='blank';continue;}
    const n=used.reduce((a,r)=>a+r.records,0),mean=used.reduce((a,r)=>a+r.records*meanOf(r),0)/n;
    const value=rule==='mean'?mean:Math.sqrt(Math.max(0,used.reduce((a,r)=>a+r.records*(r[id]*r[id]+(meanOf(r)-mean)**2),0)/n));
    row[id]=whole(numbers)?Math.round(value):value;outcome[id]=rule==='mean'?'weighted':'pooled';continue;
   }
   if(rule==='span')continue;
   row[id]=null;outcome[id]='blank';
  }
  if(ids.includes('span_days')){
   const day=s=>Date.parse(String(s)+'T00:00:00Z');
   if(row.first_date&&row.last_date&&Number.isFinite(day(row.first_date))&&Number.isFinite(day(row.last_date))){row.span_days=Math.round((day(row.last_date)-day(row.first_date))/86400000);outcome.span_days='widened';}
   else{row.span_days=null;outcome.span_days='blank';}
  }
  return {row,outcome};
 }
 function combine(rows,dims,columns=[]){
  const groups=new Map();
  for(const row of rows){const key=JSON.stringify(dims.map(d=>row[d]??null));if(!groups.has(key))groups.set(key,[]);groups.get(key).push(row);}
  if(groups.size===rows.length)return {rows,combined:0,outcomes:{}};
  let combined=0;const outcomes={};
  const out=[...groups.values()].map(list=>{if(list.length===1)return list[0];combined+=list.length-1;const merged=combineGroup(list,dims,columns);mergeOutcomes(outcomes,merged.outcome);return merged.row;});
  return {rows:out,combined,outcomes};
 }
 function mergeOutcomes(into,from){for(const[id,kind]of Object.entries(from))if(!into[id]||(RANK[kind]||1)>(RANK[into[id]]||1))into[id]=kind;return into;}
 function combineNote(combined,outcomes,columns=[]){
  if(!combined)return '';
  const of=kind=>Object.keys(outcomes||{}).filter(id=>outcomes[id]===kind).map(id=>name(id,columns));
  const list=a=>a.length<3?a.join(' and '):a.slice(0,-1).join(', ')+' and '+a.at(-1);
  const verb=(a,one,many)=>list(a)+(a.length===1?one:many);
  const parts=[];
  const added=of('added'),weighted=of('weighted'),pooled=of('pooled'),lowest=of('lowest'),highest=of('highest'),widened=of('widened'),blank=of('blank');
  if(added.length)parts.push(verb(added,' is added',' are added'));
  if(weighted.length)parts.push(verb(weighted,' is weighted by observation count',' are weighted by observation count'));
  if(pooled.length)parts.push(verb(pooled,' is pooled from each group’s count, mean and deviation',' are pooled from each group’s count, mean and deviation'));
  if(lowest.length)parts.push(verb(lowest,' takes the lowest value',' take the lowest value'));
  if(highest.length)parts.push(verb(highest,' takes the highest value',' take the highest value'));
  if(widened.length)parts.push(verb(widened,' covers the combined date span',' cover the combined date span'));
  if(blank.length)parts.push(verb(blank,' cannot be rebuilt from group summaries, so a combined mark leaves it blank',' cannot be rebuilt from group summaries, so a combined mark leaves them blank'));
  return combined+' duplicate group'+(combined===1?' was':'s were')+' combined because a queried field is not drawn'+(parts.length?': '+parts.join('; '):'')+'.';
 }
 function validate(rows,spec){
  if(!Array.isArray(rows))throw new Error('Chart data must be a list of aggregate rows.');
  if(!['bar','line','area','scatter','table'].includes(spec.type))throw new Error('Choose a supported chart type.');
  if(!spec.measures?.length)throw new Error('Add a measure to build a chart.');
  if(!Array.isArray(spec.measures)||spec.measures.some(id=>typeof id!=='string')||new Set(spec.measures).size!==spec.measures.length)throw new Error('Choose distinct named measures.');
  if(spec.dimensions!=null&&(!Array.isArray(spec.dimensions)||spec.dimensions.some(id=>typeof id!=='string')||new Set(spec.dimensions).size!==spec.dimensions.length))throw new Error('Choose distinct named dimensions.');
  if(spec.color&&!(spec.dimensions||[]).includes(spec.color))throw new Error('The Colour field must be included in the queried dimensions.');
  // r3 (Paul: "nothing is logically constrained"): a scatter takes two or more
  // measures ([0] x, [1] y, [2] size when spec.size is absent, the rest in the
  // tooltip); Size is drawn on bars, lines and areas too; a line or area whose
  // first dimension is not a time field is drawn on category positions
  // (spec.categorical); Colour may repeat the time axis.
  if(spec.type==='scatter'&&spec.measures.length<2)throw new Error('Scatter needs exactly two measures; each point represents the selected dimensions.');
  if(spec.size&&rows.some(row=>row[spec.size]!=null&&(typeof row[spec.size]!=='number'||!Number.isFinite(row[spec.size]))))throw new Error('Size must use a numeric source measure.');
  if(spec.colorMeasure&&rows.some(row=>row[spec.colorMeasure]!=null&&(typeof row[spec.colorMeasure]!=='number'||!Number.isFinite(row[spec.colorMeasure]))))throw new Error('A Colour measure must be a numeric source measure.');
  if(rows.some(row=>!row||typeof row!=='object'||Array.isArray(row)))throw new Error('Each chart row must be an aggregate record.');
  for(const row of rows)for(const id of spec.measures){if(row[id]!=null&&!(spec.type==='table'&&spec.columns?.some(c=>c.id===id&&c.unit==='date'))&&(typeof row[id]!=='number'||!Number.isFinite(row[id])))throw new Error('The query returned a nonnumeric measure.');}
 }
 function extent(values,zero=true){let lo=Infinity,hi=-Infinity;for(const value of values)if(typeof value==='number'&&Number.isFinite(value)){lo=Math.min(lo,value);hi=Math.max(hi,value);}if(lo===Infinity)return[0,1];if(zero){lo=Math.min(0,lo);hi=Math.max(0,hi);}if(lo===hi){const pad=Math.abs(lo)*.1||1;lo-=zero&&lo===0?0:pad;hi+=pad;}if(!Number.isFinite(hi-lo)||hi<=lo)throw new Error('The numeric range cannot be displayed safely.');return[lo,hi];}
 // Ordinals preserve real elapsed time and distinguish a missing period from zero.
 function timeValue(value,field){
  const text=String(value??'').trim();let match;
  if(field==='year'){if(!/^\d{4}$/.test(text))return null;const year=Number(text);return year>=1800&&year<=2200?year:null;}
  if(field==='cycle'){match=text.match(/^(?:(\d{4})[-–])?(\d{4})$/);if(!match)return null;const end=Number(match[2]);return end>=1800&&end<=2200&&end%2===0&&(!match[1]||Number(match[1])===end-1)?end/2:null;}
  if(field==='month'){match=text.match(/^(\d{4})-(\d{2})$/);if(!match||Number(match[1])<1800||Number(match[1])>2200||Number(match[2])<1||Number(match[2])>12)return null;return Number(match[1])*12+Number(match[2])-1;}
  if(field==='quarter'){match=text.match(/^(\d{4})-Q([1-4])$/);return match&&Number(match[1])>=1800&&Number(match[1])<=2200?Number(match[1])*4+Number(match[2])-1:null;}
  if(field==='date'){if(!/^\d{4}-\d{2}-\d{2}$/.test(text))return null;const date=new Date(text+'T00:00:00Z');return Number.isFinite(date.getTime())&&date.toISOString().slice(0,10)===text?date.getTime()/86400000:null;}
  return null;
 }
 function timeline(rows,spec,measure){
  const time=spec.dimensions[0],other=spec.dimensions.slice(1),groups=new Map(),ticks=new Map();let excluded=0;
  for(const row of rows){const at=timeValue(row[time],time);if(at==null){excluded++;continue;}ticks.set(at,String(row[time]));const key=JSON.stringify(other.map(d=>row[d]??null));if(!groups.has(key))groups.set(key,{key,label:label(row,other),rows:[]});groups.get(key).rows.push({row,at});}
  const series=[...groups.values()].sort((a,b)=>a.key.localeCompare(b.key));
  for(const s of series){s.rows.sort((a,b)=>a.at-b.at);s.segments=[];let segment=[],previous=null;const flush=()=>{if(segment.length)s.segments.push(segment);segment=[];};for(const item of s.rows){if(previous===item.at)throw new Error('The timeline has duplicate aggregate groups. Include every queried dimension before drawing it.');if(previous!=null&&item.at!==previous+1)flush();if(item.row[measure]==null)flush();else segment.push(item);previous=item.at;}flush();}
  return {series,ticks:[...ticks].sort((a,b)=>a[0]-b[0]),excluded};
 }
 const TIME_FIELDS=['cycle','date','year','quarter','month'];
 // The timeline render() draws (V01, V07). timeline() above still refuses a
 // repeated group when called directly; the drawing sums the repeats and says
 // so. A categorical axis places the first dimension's members in row order.
 function drawnTimeline(rows,spec,measure,categorical){
  const time=spec.dimensions?.[0],other=(spec.dimensions||[]).slice(1),groups=new Map(),ticks=new Map(),order=new Map(),repeats=[];let excluded=0,merged=0;
  for(const row of rows){
   let at;
   if(categorical){const text=time==null?'Selected population':row[time]==null||row[time]===''?'Unknown':String(row[time]);if(!order.has(text))order.set(text,order.size);at=order.get(text);ticks.set(at,text);}
   else{at=timeValue(row[time],time);if(at==null){excluded++;continue;}ticks.set(at,String(row[time]));}
   const key=JSON.stringify(other.map(d=>row[d]??null));if(!groups.has(key))groups.set(key,{key,label:label(row,other),rows:[],byAt:new Map()});
   const s=groups.get(key),seen=s.byAt.get(at);
   if(seen){merged++;if(!seen.list){seen.list=[seen.row];repeats.push(seen);}seen.list.push(row);continue;}
   const item={row,at};s.byAt.set(at,item);s.rows.push(item);
  }
  // F2: each repeated group is combined statistic by statistic (combineGroup).
  const outcomes={};for(const item of repeats){const combined=combineGroup(item.list,spec.dimensions||[],spec.columns||[]);item.row=combined.row;mergeOutcomes(outcomes,combined.outcome);delete item.list;}
  const series=[...groups.values()].sort((a,b)=>a.key.localeCompare(b.key));
  for(const s of series){delete s.byAt;s.rows.sort((a,b)=>a.at-b.at);s.segments=[];let segment=[],previous=null;const flush=()=>{if(segment.length)s.segments.push(segment);segment=[];};
   for(const item of s.rows){if(!categorical&&previous!=null&&item.at!==previous+1)flush();if(item.row[measure]==null){if(!categorical)flush();}else segment.push(item);previous=item.at;}flush();}
  return {series,ticks:[...ticks].sort((a,b)=>a[0]-b[0]),excluded,merged,outcomes};
 }
 const scatterPairs=(rows,measures)=>rows.filter(row=>measures.every(id=>typeof row[id]==='number'&&Number.isFinite(row[id])));
 function render(container,rows,spec,onSelect){
  validate(rows,spec);container.replaceChildren();
  const columns=spec.columns||[],dims=spec.dimensions||[],measures=spec.measures;
  if(!rows.length){const p=document.createElement('p');p.className='empty-view';p.textContent='No records match these filters. Try another cycle or accounting basis.';container.append(p);return null;}
  if(spec.type==='table'){const table=document.createElement('table'),head=document.createElement('thead'),tr=document.createElement('tr');for(const id of [...dims,...measures]){const th=document.createElement('th');th.textContent=name(id,columns);tr.append(th);}head.append(tr);table.append(head);const body=document.createElement('tbody');for(const row of rows){const tr=document.createElement('tr');tr.className='selectable';tr.tabIndex=0;tr.setAttribute('aria-label','Inspect '+label(row,dims));for(const id of [...dims,...measures]){const td=document.createElement('td'),shownValue=measures.includes(id)?format(row[id],id,columns):row[id]??'Unknown';if(measures.includes(id)&&spec.labels===false){td.title=String(shownValue);td.dataset.valueHidden='true';}else td.textContent=shownValue;if(measures.includes(id))td.className='numeric';tr.append(td);}tr.onclick=()=>onSelect?.(row);tr.onkeydown=e=>{if(e.key==='Enter')onSelect?.(row);};body.append(tr);}table.append(body);container.append(table);return null;}
  // V01: a line or area whose first dimension is not a time field, or any line
  // with spec.categorical, is drawn on category positions in row order.
  const timed=['line','area'].includes(spec.type),categorical=timed&&(spec.categorical===true||!TIME_FIELDS.includes(dims[0]));
  const timelines=timed?measures.map(m=>drawnTimeline(rows,spec,m,categorical)):[],merged=timelines.reduce((n,t)=>Math.max(n,t.merged),0);
  // A scatter plots [0] against [1]; [2] sizes the points when spec.size is absent (V07).
  const sizeId=spec.size||(spec.type==='scatter'&&measures.length>2?measures[2]:null);
  const plotted=spec.type==='scatter'?scatterPairs(rows,measures.slice(0,2)):timed&&!categorical?rows.filter(row=>timeValue(row[dims[0]],dims[0])!=null):rows;
  if(!plotted.length){const note=document.createElement('p');note.className='empty-view';note.textContent=timed?'No valid dated groups remain. Use Table view to inspect missing or invalid dates.':'No complete measure pairs remain. Use Table view to inspect missing values.';container.append(note);return null;}
  if(plotted.length<rows.length){const note=document.createElement('p');note.className='plot-note';note.textContent=(rows.length-plotted.length)+(timed?' groups have missing or invalid dates.':' groups are missing one or both measures.')+' They remain available in Table view.';container.append(note);}
  if(merged){const note=document.createElement('p');note.className='plot-note';note.textContent=combineNote(merged,timelines.reduce((all,t)=>mergeOutcomes(all,t.outcomes||{}),{}),columns);container.append(note);}
  // V02: bars stacked by Colour, one row per group (labelDimensions, or every
  // dimension except Colour). V03: measures[1..] on a right-hand axis.
  const stacking=spec.type==='bar'&&spec.color&&['stacked','percent'].includes(spec.stack)?spec.stack:null;
  const stackDims=spec.labelDimensions||dims.filter(d=>d!==spec.color),stackKeys=stacking?[...new Set(rows.map(r=>label(r,stackDims)))]:null;
  const dual=spec.dual===true&&['bar','line'].includes(spec.type)&&measures.length>=2;
  const barCount=stackKeys?stackKeys.length:rows.length;
  const svg=document.createElementNS(NS,'svg');svg.setAttribute('class','plot-svg');svg.setAttribute('role','group');svg.setAttribute('aria-label',spec.type+' chart. Select a mark to inspect its source records. The Table view provides all displayed values.');
  // spec.barPitch (Chart Studio, S1): a taller row per bar; 29 otherwise.
  let pitch=spec.type==='bar'&&Number(spec.barPitch)>0?Number(spec.barPitch):29;
  // spec.width (bars only): draw at the container's own width, one unit per
  // CSS pixel; spec.barLeft is then the label column. Otherwise 1000 units.
  const native=spec.type==='bar'&&!dual&&Number(spec.width)>0;let barLeft=native&&Number(spec.barLeft)>0?Number(spec.barLeft):255;
  if(native)svg.setAttribute('data-native','');
  const width=native?Math.max(560,Math.round(Number(spec.width))):1000,panels=spec.type==='scatter'||dual?1:measures.length;let barRight=width-(native?110:125),panelH=spec.type==='bar'&&!dual?Math.max(spec.panelTitles===false?300:350,barCount*pitch+(spec.panelTitles===false?70:105)):dual?500:420;
  svg.setAttribute('viewBox',`0 0 ${width} ${panelH*panels}`);svg.setAttribute('width',width);svg.setAttribute('height',panelH*panels);svg.setAttribute('font-family','Arial, sans-serif');svg.setAttribute('font-size','15');
  const title=document.createElementNS(NS,'title');title.textContent=spec.title||'Contribution analysis';svg.append(title);
  const node=(tag,attrs={},text,parent=svg)=>{const n=document.createElementNS(NS,tag);for(const[k,v]of Object.entries(attrs))n.setAttribute(k,String(v));if(text!=null)n.textContent=text;parent.append(n);return n;};
  const context=document.createElement('canvas').getContext?.('2d');
  const measure=(value,size=15)=>{if(!context)return String(value).length*size;context.font=`${size}px Arial, sans-serif`;return context.measureText(String(value)).width;};
  const fittingLength=(chars,available,size)=>{let lo=0,hi=chars.length;while(lo<hi){const mid=Math.ceil((lo+hi)/2);if(measure(chars.slice(0,mid).join(''),size)<=available)lo=mid;else hi=mid-1;}return lo;};
  const fit=(value,available,size=15)=>{const text=String(value);if(measure(text,size)<=available)return text;const chars=Array.from(text);return chars.slice(0,fittingLength(chars,Math.max(0,available-measure('…',size)),size)).join('')+'…';};
  const wrap=(value,available,size=15)=>{let chars=Array.from(String(value).replace(/\s+/g,' ').trim());const lines=[];while(chars.length){let count=Math.max(1,fittingLength(chars,available,size));if(count<chars.length){const space=chars.slice(0,count).lastIndexOf(' ');if(space>0)count=space;}lines.push(chars.slice(0,count).join(''));chars=Array.from(chars.slice(count).join('').trimStart());}return lines.length?lines:[''];};
  const fittedText=(attrs,value,available,parent)=>{const t=node('text',attrs,fit(value,available,attrs['font-size']||15),parent);node('title',{},value,t);return t;};
  const background=node('rect',{width,height:panelH*panels,fill:'#ffffff'});
  // spec.colorMap (value -> colour) pins a series to a colour and its legend
  // order, as Chart Studio's compared scopes do with --scope-1/2/3; without it
  // series take the palette in alphabetical order, as before.
  const mapped=spec.color&&spec.colorMap?Object.keys(spec.colorMap):null;
  const seen=[...new Set(plotted.map(r=>spec.color?String(r[spec.color]??'Unknown'):'Giving'))];
  const colorValues=mapped?[...mapped.filter(v=>seen.includes(v)),...seen.filter(v=>!mapped.includes(v)).sort((a,b)=>a.localeCompare(b))]:seen.sort((a,b)=>a.localeCompare(b));
  const colorOf=value=>(mapped&&spec.colorMap[value])||palette[Math.max(0,colorValues.indexOf(value))%palette.length];
  const color=row=>colorOf(spec.color?String(row[spec.color]??'Unknown'):'Giving');
  const encodedFields=[...new Set([...measures,...(spec.tooltip||[]),...(spec.labelFields||[]),...(sizeId?[sizeId]:[]),...(spec.colorMeasure?[spec.colorMeasure]:[])])];
  const valueText=(row,id)=>dims.includes(id)||columns.some(c=>c.id===id&&(c.role==='dimension'||c.type==='category'||c.type==='date'))?String(row[id]??'Unknown'):format(row[id],id,columns);
  const labelText=(row,fallback)=>spec.labelFields?.length?spec.labelFields.map(id=>valueText(row,id)).join(' / '):fallback;
  // Money at a bar's end reads in whole dollars (S1: "$10,892,411").
  const barEndValue=(v,id)=>isMoney(id,columns)&&Number.isFinite(Number(v))?new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:0}).format(Number(v)/100):format(v,id,columns,true);
  // The legend's layout, below the panels: one plan draws it and sizes the fit.
  const legendPlan=values=>{let x=24,y=28,rowHeight=28;const items=[];for(const [i,value]of values.entries()){const lines=wrap(value,width-78),itemWidth=30+Math.max(...lines.map(line=>measure(line)));if(x>24&&x+itemWidth>width-24){x=24;y+=rowHeight;rowHeight=28;}items.push({i,value,lines,x,y});rowHeight=Math.max(rowHeight,lines.length*20+8);x+=itemWidth+14;}return {items,height:y+rowHeight};};
  // Chart Studio sizing, native bars only. spec.barLeftMax: the label column
  // fits the longest group label (up to that many px) and the right margin
  // the longest value label plus its 8px gap and 8px pad, so the plot takes
  // the width it is given and keeps its round ticks. spec.fitHeight with
  // spec.barPitchMin: the pitch shrinks toward that minimum until the panels,
  // their axes and the legend fit that height (compared scopes multiply bars).
  // spec.barPitchMax (Chart Studio with a pane put away, ruling c): the pitch
  // may also grow toward that maximum, so the bars fill the height given.
  if(native&&Number(spec.barLeftMax)>0){
   const labelWidth=Math.max(0,...rows.map(r=>measure(label(r,spec.labelDimensions||dims),13.5)));
   barLeft=Math.max(60,Math.min(Number(spec.barLeftMax),Math.ceil(labelWidth)+22));
   const valueWidth=spec.labels?Math.max(0,...measures.flatMap(m=>rows.filter(r=>r[m]!=null&&r[m]>=0).map(r=>measure(labelText(r,barEndValue(r[m],m)),13.5)))):0;
   barRight=width-Math.max(36,Math.ceil(valueWidth)+16);
  }
  if(native&&Number(spec.fitHeight)>0&&(Number(spec.barPitchMin)>0||Number(spec.barPitchMax)>0)&&barCount){
   const chrome=spec.panelTitles===false?70:105,room=(Number(spec.fitHeight)-(spec.color?legendPlan(colorValues).height:0))/panels;
   const least=Number(spec.barPitchMin)>0?Math.min(Number(spec.barPitchMin),pitch):pitch,most=Math.max(pitch,Number(spec.barPitchMax)||0);
   pitch=Math.max(least,Math.min(most,Math.floor((room-chrome)/barCount)));
   panelH=Math.max(Math.min(spec.panelTitles===false?300:350,Math.floor(room)),barCount*pitch+chrome);
   svg.setAttribute('viewBox',`0 0 ${width} ${panelH*panels}`);svg.setAttribute('height',panelH*panels);background.setAttribute('height',panelH*panels);
  }
  const maxSize=sizeId?plotted.reduce((max,row)=>Math.max(max,Math.abs(row[sizeId]||0)),1):1;
  // Size (V04): a bar's thickness and a line's width follow |size| / max too.
  const sizeFactor=row=>sizeId&&typeof row[sizeId]==='number'?.35+.65*Math.sqrt(Math.abs(row[sizeId])/maxSize):1;
  // A Colour measure (V09): one hue, its opacity rising with the value.
  const heatValues=spec.colorMeasure?plotted.map(r=>r[spec.colorMeasure]).filter(v=>typeof v==='number'&&Number.isFinite(v)):[];
  const heat=heatValues.length?[Math.min(...heatValues),Math.max(...heatValues)]:null;
  const shade=row=>heat&&typeof row[spec.colorMeasure]==='number'?{fill:palette[0],'fill-opacity':.25+.75*(heat[1]>heat[0]?(row[spec.colorMeasure]-heat[0])/(heat[1]-heat[0]):1)}:null;
  // Per-panel value axes of the r3 layouts, so reference lines use the drawn scale.
  const axes=[];
  const mark=(tag,attrs,row,parent,keepRadius)=>{if(sizeId&&tag==='circle'&&!keepRadius)attrs={...attrs,r:3+12*Math.sqrt(Math.abs(row[sizeId]||0)/maxSize)};const detail=encodedFields.map(m=>`${name(m,columns)}: ${valueText(row,m)}`).join('\n');const n=node(tag,{...attrs,class:'plot-mark',tabindex:0,role:'button','aria-label':label(row,dims)+'; '+detail},null,parent);node('title',{},label(row,dims)+'\n'+detail,n);n.addEventListener('click',()=>onSelect?.(row));n.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();onSelect?.(row);}});return n;};
  for(let p=0;p<panels;p++){
   const g=node('g',{transform:`translate(0 ${p*panelH})`}),m=measures[p];
   // spec.panelTitles===false (Chart Studio, one measure): the canvas title
   // above the drawing already names the measure, so the panel skips its own.
   if(spec.panelTitles!==false)node('text',{x:20,y:23,fill:'#202522','font-size':18,'font-weight':600},spec.type==='scatter'?`${name(measures[1],columns)} by ${name(measures[0],columns)}`:dual?`${name(measures[0],columns)} (left axis) · ${measures.slice(1).map(id=>name(id,columns)).join(', ')} (right axis)`:name(m,columns),g);
   if(spec.type==='bar'&&!dual){
    // Stacked (V02): each group's segments in Colour order, positives rightward
    // from zero and negatives leftward; 'percent' draws shares of the positive total.
    const stackOf=stacking?stackKeys.map(key=>{const members=rows.filter(r=>label(r,stackDims)===key).sort((a,b)=>colorValues.indexOf(String(a[spec.color]??'Unknown'))-colorValues.indexOf(String(b[spec.color]??'Unknown')));
     const total=members.reduce((sum,r)=>sum+(r[m]>0?r[m]:0),0);let pos=0,neg=0;
     const parts=members.filter(r=>r[m]!=null).map(r=>{const v=stacking==='percent'?(total?r[m]/total*100:0):r[m],start=v<0?neg:pos,end=start+v;if(v<0)neg=end;else pos=end;return {r,v,start,end};});
     return {key,parts,pos,neg,sum:members.reduce((sum,r)=>sum+(r[m]||0),0)};}):null;
    const left=barLeft,right=barRight,top=spec.panelTitles===false?20:55,bottom=panelH-43,[lo,hi]=stackOf?extent(stackOf.flatMap(s=>[s.pos,s.neg])):extent(rows.map(r=>r[m])),x=v=>left+(v-lo)/(hi-lo)*(right-left),zero=x(0);
    if(stackOf)axes[p]={values:stackOf.map(s=>stacking==='percent'?100:s.sum),lo,hi,bar:true};
    // spec.niceTicks (S1): round steps ("$2.0M") and the axis end, instead of
    // five equal fifths of the range. The last round step gives way to the
    // axis end only where their two labels would sit under 8px apart.
    const niceStep=span=>{const raw=span/6,mag=Math.pow(10,Math.floor(Math.log10(raw||1))),n=raw/mag;return (n<=1?1:n<=2?2:n<=2.5?2.5:n<=5?5:10)*mag;};
    let ticks=[0,1,2,3,4,5].map(t=>lo+(hi-lo)*t/5);
    const tickText=v=>stacking==='percent'?Number(v.toFixed(1))+'%':spec.niceTicks&&isMoney(m,columns)?(v===0?'$0':new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',notation:'compact',minimumFractionDigits:1,maximumFractionDigits:1}).format(v/100)):format(v,m,columns,true);
    if(spec.niceTicks&&hi>lo){const step=niceStep(hi-lo);ticks=[];for(let v=Math.ceil(lo/step)*step;v<=hi+step*1e-9;v+=step)ticks.push(v);if(lo<ticks[0])ticks.unshift(lo);const endGap=x(hi)-x(ticks.at(-1));if(endGap>=1){if(ticks.length>1&&endGap<(measure(tickText(ticks.at(-1)),native?13.5:15)+measure(tickText(hi),native?13.5:15))/2+8)ticks.pop();ticks.push(hi);}}
    for(const v of ticks){node('line',{x1:x(v),x2:x(v),y1:top-8,y2:bottom,stroke:spec.niceTicks&&v===0?'#8a8690':'#e8ebe6'},null,g);fittedText({x:x(v),y:panelH-17,'text-anchor':'middle',fill:'#68706b','font-size':native?13.5:15},tickText(v),110,g);}
    // spec.labelDimensions names a group once for a cluster of bars (one bar
    // per compared scope); the value label sits at the end of its own bar.
    const groupLabel=r=>label(r,spec.labelDimensions||dims);
    const barValue=v=>barEndValue(v,m);
    const barH=pitch===29?20:Math.round(pitch*.62),textY=pitch===29?14:Math.round(barH/2+5);
    // spec.seriesColor (Chart Studio, S1's teal): the fill of a single series.
    // Compared scopes (spec.color) keep their colorMap; S1 also draws $0 as a darker axis.
    const barFill=r=>spec.color||!spec.seriesColor?color(r):spec.seriesColor;
    if(stackOf)stackOf.forEach((s,i)=>{const y=top+i*pitch;fittedText({x:left-14,y:y+textY,'text-anchor':'end',fill:'#444c46','font-size':native?13.5:16,'data-label':'category'},s.key,left-(native?22:30),g);
     for(const part of s.parts)mark('rect',{x:Math.min(x(part.start),x(part.end)),y,width:Math.max(1,Math.abs(x(part.end)-x(part.start))),height:barH,fill:color(part.r),stroke:'#ffffff','stroke-width':1},part.r,g);
     if(spec.labels){const end=Math.max(x(s.pos),zero);fittedText({x:end+8,y:y+textY,'text-anchor':'start',fill:'#35483b','font-size':native?13.5:15,'data-label':'value'},stacking==='percent'?'100%':barValue(s.sum),Math.max(60,width-end-16),g);}});
    else rows.forEach((r,i)=>{const y=top+i*pitch,text=groupLabel(r);if(!spec.labelDimensions||!i||text!==groupLabel(rows[i-1]))fittedText({x:left-14,y:y+textY,'text-anchor':'end',fill:'#444c46','font-size':native?13.5:16,'data-label':'category'},text,left-(native?22:30),g);if(r[m]==null)return;const f=sizeFactor(r),h=f===1?barH:barH*f;mark('rect',{x:Math.min(zero,x(r[m])),y:f===1?y:y+(barH-h)/2,width:Math.max(1,Math.abs(x(r[m])-zero)),height:h,rx:2,...(shade(r)||{fill:barFill(r)})},r,g);if(spec.labels&&!native)fittedText({x:right+12,y:y+textY,'text-anchor':'start',fill:'#35483b','font-size':15,'data-label':'value'},labelText(r,format(r[m],m,columns,true)),width-right-28,g);else if(spec.labels){const end=x(r[m]),negative=r[m]<0;fittedText({x:negative?Math.max(left+4,end-8):end+8,y:y+textY,'text-anchor':negative?'end':'start',fill:'#35483b','font-size':native?13.5:15,'data-label':'value'},labelText(r,barValue(r[m])),Math.max(60,negative?end-left:width-end-16),g);}});
   }else if(dual){
    // Dual axis (V03): categories in row order across the panel; measures[0] on
    // the left axis as the chosen mark, measures[1..] on a right axis as
    // spec.dualMark ('line' by default, or 'bar' sharing the category slot).
    const left=110,right=890,top=60,bottom=420,catDims=dims.filter(d=>d!==spec.color),cats=[],catOf=new Map();
    for(const r of rows){const k=label(r,catDims);if(!catOf.has(k)){catOf.set(k,cats.length);cats.push(k);}}
    const n=cats.length,step=(right-left)/Math.max(1,n),cx=i=>left+step*(i+.5);
    const members=spec.color?colorValues:['Giving'],memberOf=r=>spec.color?String(r[spec.color]??'Unknown'):'Giving';
    const rightIds=measures.slice(1),dualMark=spec.dualMark==='bar'?'bar':'line';
    const [la,lb]=extent(rows.map(r=>r[measures[0]])),[ra,rb]=extent(rows.flatMap(r=>rightIds.map(id=>r[id])));
    const ly=v=>bottom-(v-la)/(lb-la)*(bottom-top),ry=v=>bottom-(v-ra)/(rb-ra)*(bottom-top);
    for(let i=0;i<=5;i++){const v=la+(lb-la)*i/5,w=ra+(rb-ra)*i/5;node('line',{x1:left,x2:right,y1:ly(v),y2:ly(v),stroke:'#e8ebe6'},null,g);
     fittedText({x:left-10,y:ly(v)+4,'text-anchor':'end',fill:palette[0],'font-size':14,'data-axis':'left'},format(v,measures[0],columns,true),96,g);
     fittedText({x:right+10,y:ry(w)+4,'text-anchor':'start',fill:palette[1%palette.length],'font-size':14,'data-axis':'right'},format(w,rightIds[0],columns,true),96,g);}
    node('line',{x1:right,x2:right,y1:top,y2:bottom,stroke:'#8a8690'},null,g);
    const every=Math.max(1,Math.ceil(n/Math.max(1,Math.min(12,Math.floor((right-left)/90)))));
    const turnCats=spec.axisLabels==='all'&&every>1;
    cats.forEach((text,i)=>{if(turnCats)fittedText({x:cx(i),y:bottom+16,'text-anchor':'end',fill:'#68706b','font-size':12,transform:`rotate(-35 ${cx(i)} ${bottom+16})`,'data-axis-label':'all'},text,110,g);else if(i%every===0)fittedText({x:cx(i),y:bottom+24,'text-anchor':'middle',fill:'#68706b','font-size':14},text,Math.max(40,step*every-6),g);});
    const barIds=[...(spec.type==='bar'?[measures[0]]:[]),...(dualMark==='bar'?rightIds:[])],slots=Math.max(1,barIds.length*members.length),bw=Math.min(40,step*.8/slots);
    const drawBars=(id,scaleY,fillOf)=>{const k=barIds.indexOf(id);rows.forEach(r=>{if(r[id]==null)return;const i=catOf.get(label(r,catDims)),slot=k*members.length+Math.max(0,members.indexOf(memberOf(r))),x0=cx(i)-bw*slots/2+slot*bw;
      mark('rect',{x:x0,y:Math.min(scaleY(0),scaleY(r[id])),width:Math.max(1,bw-1),height:Math.max(1,Math.abs(scaleY(r[id])-scaleY(0))),fill:fillOf(r)},r,g);
      if(spec.labels)fittedText({x:x0+bw/2,y:Math.min(scaleY(0),scaleY(r[id]))-5,'text-anchor':'middle',fill:'#35483b','font-size':12,'data-label':'value'},labelText(r,format(r[id],id,columns,true)),90,g);});};
    const drawLine=(id,scaleY,strokeOf,dashed)=>{for(const member of members){const points=rows.filter(r=>memberOf(r)===member&&r[id]!=null).map(r=>({r,i:catOf.get(label(r,catDims))})).sort((a,b)=>a.i-b.i);if(!points.length)continue;const stroke=strokeOf(points[0].r);
      node('path',{d:points.map((q,k)=>(k?'L':'M')+cx(q.i)+','+scaleY(q.r[id])).join(' '),fill:'none',stroke,'stroke-width':2.5,...(dashed?{'stroke-dasharray':'6 4'}:{})},null,g);
      points.forEach(q=>{mark('circle',{cx:cx(q.i),cy:scaleY(q.r[id]),r:4.5,fill:stroke,stroke:'white','stroke-width':1.5},q.r,g,true);if(spec.labels)fittedText({x:cx(q.i),y:scaleY(q.r[id])-10,'text-anchor':'middle',fill:stroke,'font-size':12,'data-label':'value'},labelText(q.r,format(q.r[id],id,columns,true)),90,g);});}};
    const leftColour=r=>spec.color?color(r):palette[0];
    if(spec.type==='bar')drawBars(measures[0],ly,leftColour);else drawLine(measures[0],ly,leftColour,false);
    rightIds.forEach((id,k)=>{const colour=r=>spec.color?color(r):palette[(k+1)%palette.length];if(dualMark==='bar')drawBars(id,ry,colour);else drawLine(id,ry,colour,!!spec.color);});
    node('text',{x:left,y:bottom+50,fill:'#59645c','font-size':13},`${name(measures[0],columns)}: left axis. ${rightIds.map(id=>name(id,columns)).join(', ')}: right axis${spec.color?' (dashed lines)':''}. Independent, labelled scales.`,g);
    axes[p]={values:rows.map(r=>r[measures[0]]),lo:la,hi:lb,at:ly,x1:left,x2:right,bar:false};
   }else if(spec.type==='scatter'){
    const [mx,my]=measures,left=100,right=935,top=65,bottom=345,[xl,xh]=extent(plotted.map(r=>r[mx]),false),[yl,yh]=extent(plotted.map(r=>r[my]),false),x=v=>left+(v-xl)/(xh-xl)*(right-left),y=v=>bottom-(v-yl)/(yh-yl)*(bottom-top);
    for(let i=0;i<=5;i++){const vx=xl+(xh-xl)*i/5,vy=yl+(yh-yl)*i/5;node('line',{x1:x(vx),x2:x(vx),y1:top,y2:bottom,stroke:'#e8ebe6'},null,g);node('line',{x1:left,x2:right,y1:y(vy),y2:y(vy),stroke:'#e8ebe6'},null,g);fittedText({x:x(vx),y:bottom+23,'text-anchor':'middle',fill:'#68706b','font-size':15},format(vx,mx,columns,true),110,g);fittedText({x:left-10,y:y(vy)+3,'text-anchor':'end',fill:'#68706b','font-size':15},format(vy,my,columns,true),78,g);}
    node('text',{x:(left+right)/2,y:400,'text-anchor':'middle',fill:'#59645c'},name(mx,columns),g);node('text',{x:18,y:45,fill:'#59645c'},name(my,columns),g);plotted.forEach(r=>{mark('circle',{cx:x(r[mx]),cy:y(r[my]),r:6,...(shade(r)||{fill:color(r),'fill-opacity':.72}),stroke:'white','stroke-width':1.4},r,g);if(spec.labels){const at=x(r[mx]),end=at>(left+right)/2;fittedText({x:at+(end?-8:8),y:y(r[my])-8,'text-anchor':end?'end':'start',fill:'#35483b','font-size':15},labelText(r,label(r,dims)),Math.min(300,end?at-24:width-at-24),g);}});
   }else{
    const prepared=timelines[p],xs=prepared.ticks,left=100,right=940,top=60,bottom=345,[lo,hi]=extent(plotted.map(r=>r[m])),x=at=>left+(xs.length===1?.5:(at-xs[0][0])/(xs.at(-1)[0]-xs[0][0]))*(right-left),y=v=>bottom-(v-lo)/(hi-lo)*(bottom-top);
    for(let i=0;i<=5;i++){const v=lo+(hi-lo)*i/5;node('line',{x1:left,x2:right,y1:y(v),y2:y(v),stroke:'#e8ebe6'},null,g);fittedText({x:left-12,y:y(v)+4,'text-anchor':'end',fill:'#68706b','font-size':15},format(v,m,columns,true),76,g);}
    const tickWidth=xs.reduce((max,[,text])=>Math.max(max,measure(text)),0),tickCount=Math.max(1,Math.min(12,Math.floor((right-left)/(tickWidth+16))));
    // spec.axisLabels 'all' (census B-E21): every tick is labelled, turned when they would collide.
    const allTicks=spec.axisLabels==='all',turnTicks=allTicks&&xs.length>tickCount;
    xs.forEach(([at,text],i)=>{if(turnTicks)fittedText({x:x(at),y:bottom+16,'text-anchor':'end',fill:'#68706b','font-size':12,transform:`rotate(-35 ${x(at)} ${bottom+16})`,'data-axis-label':'all'},text,110,g);else if(allTicks||i%Math.max(1,Math.ceil(xs.length/tickCount))===0)node('text',{x:x(at),y:bottom+25,'text-anchor':'middle',fill:'#68706b','font-size':15},text,g);});
    // Colour on the time axis itself colours each point by its period.
    const perPoint=spec.color&&spec.color===dims[0];
    for(const [seriesIndex,s] of prepared.series.entries()){const stroke=perPoint?'#8a8690':spec.color?color(s.rows[0].row):palette[seriesIndex%palette.length];
     for(const segment of s.segments){const d=segment.map((item,i)=>(i?'L':'M')+x(item.at)+','+y(item.row[m])).join(' ');
      if(spec.type==='area'){const path=`M${x(segment[0].at)},${y(0)} `+segment.map(item=>`L${x(item.at)},${y(item.row[m])}`).join(' ')+` L${x(segment.at(-1).at)},${y(0)} Z`;node('path',{d:path,fill:perPoint?palette[0]:stroke,'fill-opacity':.1,stroke:'none'},null,g);}
      if(sizeId)segment.slice(1).forEach((item,k)=>{const prev=segment[k],share=v=>typeof v==='number'?Math.abs(v)/maxSize:0;node('path',{d:`M${x(prev.at)},${y(prev.row[m])} L${x(item.at)},${y(item.row[m])}`,fill:'none',stroke,'stroke-width':1.5+4.5*(share(prev.row[sizeId])+share(item.row[sizeId]))/2,'stroke-linecap':'round'},null,g);});
      else node('path',{d,fill:'none',stroke,'stroke-width':2.5},null,g);segment.forEach(({row:r,at})=>{mark('circle',{cx:x(at),cy:y(r[m]),r:4.5,fill:perPoint?color(r):stroke,stroke:'white','stroke-width':1.5},r,g,true);if(spec.labels)fittedText({x:x(at),y:y(r[m])-11,'text-anchor':'middle',fill:perPoint?color(r):stroke,'font-size':15},labelText(r,format(r[m],m,columns,true)),110,g);});
     }
    }
   }
  }
  if(spec.references&&(spec.references.average||spec.references.median)&&spec.type!=='scatter'){
   for(let p=0;p<(dual?1:measures.length);p++){
    const ax=axes[p];
    const id=measures[p],values=(ax?ax.values:plotted.map(row=>row[id])).filter(v=>typeof v==='number'&&Number.isFinite(v)).sort((a,b)=>a-b);if(!values.length)continue;
    const average=values.reduce((a,b)=>a+b,0)/values.length,middle=Math.floor(values.length/2),median=values.length%2?values[middle]:(values[middle-1]+values[middle])/2,[lo,hi]=ax?[ax.lo,ax.hi]:extent(values),bar=ax?ax.bar:spec.type==='bar';
    for(const [kind,value]of [['average',average],['median',median]])if(spec.references[kind]){
     const g=node('g',{transform:`translate(0 ${p*panelH})`,'data-reference':kind});const at=ax&&ax.at?ax.at(value):bar?barLeft+(value-lo)/(hi-lo)*(barRight-barLeft):345-(value-lo)/(hi-lo)*285;
     node('line',bar?{x1:at,x2:at,y1:48,y2:panelH-43,stroke:'#745079','stroke-dasharray':'6 4'}:{x1:ax?.x1??100,x2:ax?.x2??940,y1:at,y2:at,stroke:'#745079','stroke-dasharray':'6 4'},null,g);
     node('text',{x:bar?at+3:(ax?.x2??940)-2,y:bar?42:at-5,'text-anchor':bar?'start':'end',fill:'#745079','font-size':12},`${kind==='average'?'Mean':'Median'} of shown marks: ${format(value,id,columns,true)}`,g);
    }
   }
  }
  // Keep legends inside the exported SVG. A sibling HTML legend is absent from
  // PNG/SVG downloads, leaving a coloured series impossible to identify.
  const legends=spec.color?colorValues:timed&&dims.length>1?timelines[0].series.map(s=>s.label):dual?measures.map((id,i)=>name(id,columns)+(i?' (right axis)':' (left axis)')):[];
  if(legends.length){
   const legend=node('g',{'data-legend':'series','aria-label':'Series legend'}),plan=legendPlan(legends),base=panelH*panels;
   for(const {i,value,lines,x,y}of plan.items){
    node('rect',{x,y:base+y-11,width:11,height:11,rx:2,fill:mapped?colorOf(value):palette[i%palette.length]},null,legend);
    lines.forEach((line,j)=>node('text',{x:x+18,y:base+y+j*20,fill:'#59645c','font-size':15},line,legend));
   }
   const height=base+plan.height;svg.setAttribute('viewBox',`0 0 ${width} ${height}`);svg.setAttribute('height',height);
  }
  // A Colour measure's two-stop legend (V09), inside the exported SVG.
  if(heat){
   const box=svg.getAttribute('viewBox').split(' ').map(Number),base=box[3],legend=node('g',{'data-legend':'colour','aria-label':'Colour legend'});
   node('text',{x:24,y:base+24,fill:'#59645c','font-size':14},name(spec.colorMeasure,columns),legend);
   node('rect',{x:24,y:base+34,width:14,height:14,rx:2,fill:palette[0],'fill-opacity':.25},null,legend);node('text',{x:44,y:base+46,fill:'#59645c','font-size':14},format(heat[0],spec.colorMeasure,columns,true),legend);
   node('rect',{x:180,y:base+34,width:14,height:14,rx:2,fill:palette[0],'fill-opacity':1},null,legend);node('text',{x:200,y:base+46,fill:'#59645c','font-size':14},format(heat[1],spec.colorMeasure,columns,true),legend);
   const height=base+60;svg.setAttribute('viewBox',`0 0 ${width} ${height}`);svg.setAttribute('height',height);background.setAttribute('height',height);
  }
  container.append(svg);
  return svg;
 }
 const api={render,format,isMoney,validate,extent,label,timeValue,timeline,drawnTimeline,scatterPairs,combine,combineGroup,combineRule,combineNote,COMBINE_RULE};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.MentatContributionPlot=api;
})(globalThis);
