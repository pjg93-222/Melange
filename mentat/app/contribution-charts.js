/* Additional chart families over server aggregates, including source quartiles.
   Every interactive mark retains its exact group for source-record inspection. */
(function(root){
 'use strict';
 const base=typeof module!=='undefined'&&module.exports?require('./contribution-plot.js'):root.MentatContributionPlot;
 const TYPES=['heatmap','highlight','stacked','dot','series-dot','treemap','bubbles','histogram','box','gantt','bullet','combination','dual-line'];
 const palette=root.MentatTheme?.palette||['#57447b','#327a7a','#c68a18','#96628d','#466d9b','#80512d'];
 function validate(rows,spec){
  if(!TYPES.includes(spec.type))throw new Error('Unknown analytical chart.');
  if(!Array.isArray(rows)||!Array.isArray(spec.dimensions)||!spec.measures?.length)throw new Error('Choose fields for this chart.');
  if(['heatmap','highlight','stacked'].includes(spec.type)&&spec.dimensions.length!==2)throw new Error('This chart needs exactly two grouping dimensions. Put other fields on Filters.');
  if(['bullet','combination','dual-line'].includes(spec.type)&&spec.measures.length!==2)throw new Error('Choose exactly two plotted measures.');
  if(['combination','dual-line'].includes(spec.type)&&spec.dimensions.length!==1)throw new Error('Choose one date dimension for the shared time axis.');
  const required=spec.type==='box'?['min_amount','q1_amount','median_amount','q3_amount','max_amount']:spec.type==='gantt'?['first_date','last_date']:spec.measures;
  for(const row of rows)for(const id of required){const v=row[id];if(v!=null&&(id.endsWith('_date')?!/^\d{4}-\d{2}-\d{2}$/.test(v):typeof v!=='number'||!Number.isFinite(v)))throw new Error('A required source statistic is invalid.');}
  const keys=rows.map(r=>JSON.stringify(spec.dimensions.map(d=>r[d]??null)));
  if(new Set(keys).size!==keys.length)throw new Error('Duplicate query groups would distort this chart.');
 }
 const cut=(s,n=34)=>String(s).length>n?String(s).slice(0,n-1)+'…':String(s);
 function partition(items,x,y,w,h,weight){
  if(!items.length)return[];if(items.length===1)return[{row:items[0],x,y,w,h}];
  const total=items.reduce((s,r)=>s+weight(r),0);let at=1,sum=weight(items[0]);
  while(at<items.length-1&&sum<total/2)sum+=weight(items[at++]);
  const ratio=total?sum/total:at/items.length;
  return w>=h?[...partition(items.slice(0,at),x,y,w*ratio,h,weight),...partition(items.slice(at),x+w*ratio,y,w*(1-ratio),h,weight)]:[...partition(items.slice(0,at),x,y,w,h*ratio,weight),...partition(items.slice(at),x,y+h*ratio,w,h*(1-ratio),weight)];
 }
 function render(container,rows,spec,onSelect){
  validate(rows,spec);container.replaceChildren();if(!rows.length){container.textContent='No observations match this selection.';return;}
  const dims=spec.dimensions,ms=spec.measures,m=ms[0],cols=spec.columns||[],fmt=(v,id=m)=>base.format(v,id,cols),label=r=>base.label(r,dims),name=id=>cols.find(c=>c.id===id)?.name||id;
  let H=Math.max(430,rows.length*34+110);if(['treemap','bubbles','combination','dual-line','histogram'].includes(spec.type))H=560;
  const W=1000,svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('class','plot-svg');svg.setAttribute('viewBox',`0 0 ${W} ${H}`);svg.setAttribute('width',W);svg.setAttribute('height',H);svg.setAttribute('role','group');svg.setAttribute('aria-label',spec.type+' chart. Every mark can open its source records.');
  const node=(tag,attrs={},text,parent=svg)=>{const n=document.createElementNS(svg.namespaceURI,tag);for(const[k,v]of Object.entries(attrs))n.setAttribute(k,String(v));if(text!=null)n.textContent=text;parent.append(n);return n;};
  const text=(x,y,s,attrs={})=>node('text',{x,y,'font-size':14,fill:'#342649','font-family':'Arial, sans-serif',...attrs},s);
  node('rect',{width:W,height:H,fill:'#fff'});node('title',{},spec.title||spec.type);text(22,25,spec.title||name(m),{'font-size':17});
  const note=s=>text(22,48,s,{'font-size':12,fill:'#645d6d'});
  const color=(v,max)=>v<0?`rgba(181,91,40,${.18+.8*Math.min(1,Math.abs(v)/(max||1))})`:`rgba(87,68,123,${.18+.8*Math.min(1,Math.abs(v)/(max||1))})`;
  const mark=(tag,attrs,row,detail)=>{const n=node(tag,{...attrs,tabindex:0,role:'button',class:'plot-mark','aria-label':label(row)+'; '+(detail||ms.map(id=>name(id)+': '+fmt(row[id],id)).join('; '))});node('title',{},n.getAttribute('aria-label'),n);n.onclick=()=>onSelect?.(row);n.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();onSelect?.(row);}};return n;};
  const axis=(values,left=265,right=940,y=H-34)=>{const[lo,hi]=base.extent(values),scale=v=>left+(v-lo)/(hi-lo)*(right-left);for(let i=0;i<=5;i++){const v=lo+(hi-lo)*i/5;node('line',{x1:scale(v),x2:scale(v),y1:70,y2:y-18,stroke:'#ece8ef'});text(scale(v),y,base.format(v,m,cols,true),{'text-anchor':'middle'});}return scale;};
  if(['heatmap','highlight'].includes(spec.type)){
   const ys=[...new Set(rows.map(r=>String(r[dims[0]]??'Unknown')))],xs=[...new Set(rows.map(r=>String(r[dims[1]]??'Unknown')))];
   const cw=Math.max(95,680/xs.length),ch=38,width=Math.max(W,270+cw*xs.length),height=Math.max(360,150+ch*ys.length);svg.setAttribute('viewBox',`0 0 ${width} ${height}`);svg.setAttribute('width',width);svg.setAttribute('height',height);svg.firstChild.setAttribute('width',width);svg.firstChild.setAttribute('height',height);
   const max=Math.max(...rows.map(r=>Math.abs(r[m]||0)),1);note('Blank cells mean no returned group. Colour preserves signed values; inspect any cell.');xs.forEach((v,i)=>text(255+i*cw+cw/2,85,cut(v,12),{'text-anchor':'middle'}));ys.forEach((v,i)=>text(240,115+i*ch,cut(v),{'text-anchor':'end'}));
   rows.forEach(r=>{const x=255+xs.indexOf(String(r[dims[1]]??'Unknown'))*cw,y=95+ys.indexOf(String(r[dims[0]]??'Unknown'))*ch;mark('rect',{x,y,width:cw-2,height:ch-2,fill:color(r[m],max)},r);if(spec.type==='highlight'||spec.labels)text(x+cw/2,y+24,base.format(r[m],m,cols,true),{'text-anchor':'middle',fill:Math.abs(r[m]||0)>max*.55?'white':'#342649','pointer-events':'none'});});
  }else if(spec.type==='stacked'){
   const groups=[...new Set(rows.map(r=>String(r[dims[0]]??'Unknown')))],series=[...new Set(rows.map(r=>String(r[dims[1]]??'Unknown')))];
   const spans=groups.map(g=>{const rs=rows.filter(r=>String(r[dims[0]]??'Unknown')===g);return [rs.reduce((s,r)=>s+Math.min(0,r[m]||0),0),rs.reduce((s,r)=>s+Math.max(0,r[m]||0),0)];});const x=axis(spans.flat());note('Positive and negative amounts stack separately from zero.');groups.forEach((g,i)=>{let pos=0,neg=0;const y=80+i*34;text(247,y+18,cut(g),{'text-anchor':'end'});for(const r of rows.filter(r=>String(r[dims[0]]??'Unknown')===g)){const v=r[m]||0,start=v<0?neg:pos,end=start+v;if(v<0)neg=end;else pos=end;mark('rect',{x:Math.min(x(start),x(end)),y,width:Math.max(1,Math.abs(x(end)-x(start))),height:24,fill:palette[series.indexOf(String(r[dims[1]]??'Unknown'))%palette.length]},r);}if(spec.labels)text(Math.max(x(pos),x(neg))+7,y+18,base.format(pos+neg,m,cols,true),{'data-label':'value','pointer-events':'none'});});
   text(22,H-8,series.map((s,i)=>`${i+1}: ${s}`).join(' · ').slice(0,145),{'font-size':11});
  }else if(spec.type==='dot'||spec.type==='series-dot'){
   const x=axis(rows.map(r=>r[m]));note('One circle per selected group on a numeric axis; circles are not joined by lines.');rows.forEach((r,i)=>{const y=85+i*34;text(248,y+5,cut(label(r)),{'text-anchor':'end'});if(r[m]==null)return;mark('circle',{cx:x(r[m]),cy:y,r:7,fill:palette[spec.type==='series-dot'?i%palette.length:0]},r);if(spec.labels)text(Math.min(930,x(r[m])+12),y-10,base.format(r[m],m,cols,true));});
  }else if(spec.type==='treemap'){
   note('Area represents absolute magnitude; orange denotes negative amounts. Values retain their signs.');const total=rows.reduce((s,r)=>s+Math.abs(r[m]||0),0);if(!total){container.textContent='All selected values are zero; use Text to inspect them.';return;}
   for(const box of partition(rows,20,75,960,450,r=>Math.abs(r[m]||0))){if(box.w<.01||box.h<.01)continue;mark('rect',{x:box.x,y:box.y,width:box.w,height:box.h,fill:box.row[m]<0?'#b56b37':'#57447b',stroke:'white','stroke-width':2},box.row);if(box.w>70&&box.h>40){text(box.x+7,box.y+20,cut(label(box.row),Math.floor(box.w/8)-1),{fill:'white','pointer-events':'none'});text(box.x+7,box.y+39,base.format(box.row[m],m,cols,true),{fill:'white','pointer-events':'none'});}}
  }else if(spec.type==='bubbles'){
   note('Circle area represents absolute magnitude. Orange denotes negative values.');const max=Math.max(...rows.map(r=>Math.abs(r[m]||0)),1);let x=25,y=85,rowH=0;for(const r of rows){const radius=Math.max(3,90*Math.sqrt(Math.abs(r[m]||0)/max));if(x+2*radius>975){x=25;y+=rowH+12;rowH=0;}mark('circle',{cx:x+radius,cy:y+radius,r:radius,fill:r[m]<0?'#b56b37':'#57447b','fill-opacity':.85},r);if(radius>28){text(x+radius,y+radius,cut(label(r),Math.floor(radius/4)),{'text-anchor':'middle',fill:'white','pointer-events':'none'});if(spec.labels)text(x+radius,y+radius+17,base.format(r[m],m,cols,true),{'text-anchor':'middle',fill:'white','font-size':12,'data-label':'value','pointer-events':'none'});}x+=2*radius+9;rowH=Math.max(rowH,2*radius);}if(y+rowH+20>H){H=y+rowH+20;svg.setAttribute('height',H);svg.setAttribute('viewBox',`0 0 ${W} ${H}`);svg.querySelector('rect').setAttribute('height',H);}
  }else if(spec.type==='histogram'){
   note('Counts of individual selected observations. Bins include the lower bound and exclude the upper bound.');const width=spec.binWidth||10000,ordered=rows.slice().sort((a,b)=>Number(a.amount_bin)-Number(b.amount_bin)),lo=Number(ordered[0].amount_bin),hi=Number(ordered.at(-1).amount_bin)+width,max=Math.max(...rows.map(r=>r.records||0),1),x=v=>90+(v-lo)/(hi-lo)*850,y=v=>490-v/max*390;
   for(let i=0;i<=5;i++){text(78,y(max*i/5)+4,String(Math.round(max*i/5)),{'text-anchor':'end'});node('line',{x1:90,x2:945,y1:y(max*i/5),y2:y(max*i/5),stroke:'#ece8ef'});text(90+i*170,520,base.format(lo+(hi-lo)*i/5,'amount',cols,true),{'text-anchor':'middle'});}
   for(const r of ordered){const start=Number(r.amount_bin);mark('rect',{x:x(start),y:y(r.records),width:Math.max(.5,x(start+width)-x(start)-1),height:490-y(r.records),fill:'#57447b'},r,`${fmt(start,'amount')} to less than ${fmt(start+width,'amount')}; ${r.records} observations; net ${fmt(r.amount,'amount')}`);if(spec.labels)text((x(start)+x(start+width))/2,y(r.records)-5,String(r.records),{'text-anchor':'middle','font-size':11,'data-label':'value','pointer-events':'none'});}text(480,548,'Individual observation amount (USD)',{'text-anchor':'middle'});
  }else if(spec.type==='box'){
   note('Quartiles of individual observations; whiskers show the full minimum–maximum range.');const x=axis(rows.flatMap(r=>[r.min_amount,r.max_amount]));rows.forEach((r,i)=>{const y=85+i*34;text(248,y+7,cut(label(r)),{'text-anchor':'end'});if(r.min_amount==null)return;node('line',{x1:x(r.min_amount),x2:x(r.max_amount),y1:y,y2:y,stroke:'#57447b','stroke-width':2});for(const id of ['min_amount','max_amount'])node('line',{x1:x(r[id]),x2:x(r[id]),y1:y-8,y2:y+8,stroke:'#57447b'});mark('rect',{x:x(r.q1_amount),y:y-11,width:Math.max(2,x(r.q3_amount)-x(r.q1_amount)),height:22,fill:'#d5c7e7',stroke:'#57447b'},r,['min_amount','q1_amount','median_amount','q3_amount','max_amount'].map(id=>name(id)+': '+fmt(r[id],id)).join('; '));node('line',{x1:x(r.median_amount),x2:x(r.median_amount),y1:y-11,y2:y+11,stroke:'#342649','stroke-width':3,'pointer-events':'none'});});
  }else if(spec.type==='gantt'){
   note('Observed first-to-last receipt dates; the bar is a date span, not continuous giving or a project duration.');const ordinal=s=>Date.parse(s+'T00:00:00Z')/86400000,values=rows.flatMap(r=>[ordinal(r.first_date),ordinal(r.last_date)]).filter(Number.isFinite),lo=Math.min(...values),hi=Math.max(...values,lo+1),x=v=>265+(v-lo)/(hi-lo)*675;
   for(let i=0;i<=4;i++){const v=lo+(hi-lo)*i/4;text(x(v),H-25,new Date(v*86400000).toISOString().slice(0,10),{'text-anchor':'middle'});}
   rows.forEach((r,i)=>{const y=80+i*34;text(248,y+18,cut(label(r)),{'text-anchor':'end'});if(!r.first_date||!r.last_date)return;mark('rect',{x:x(ordinal(r.first_date)),y,width:Math.max(3,x(ordinal(r.last_date))-x(ordinal(r.first_date))),height:23,fill:'#327a7a'},r,`${r.first_date} to ${r.last_date}; observed span ${r.span_days} days`);});
  }else if(spec.type==='bullet'){
   const unit=id=>cols.find(c=>c.id===id)?.unit|| (base.isMoney(id)?'cents':'count');if(unit(ms[0])!==unit(ms[1]))throw new Error('A bullet comparison needs two measures with the same unit.');note(`${name(ms[0])} (bar) compared with ${name(ms[1])} (marker). The second measure is not an inferred target.`);const x=axis(rows.flatMap(r=>ms.map(id=>r[id])));rows.forEach((r,i)=>{const y=85+i*34;text(248,y+13,cut(label(r)),{'text-anchor':'end'});if(r[m]!=null)mark('rect',{x:Math.min(x(0),x(r[m])),y,width:Math.max(1,Math.abs(x(r[m])-x(0))),height:20,fill:'#57447b'},r);if(r[ms[1]]!=null)node('line',{x1:x(r[ms[1]]),x2:x(r[ms[1]]),y1:y-4,y2:y+24,stroke:'#b87516','stroke-width':3});});
  }else{
   note(`${name(ms[0])}: left axis (purple). ${name(ms[1])}: right axis (teal). Independent, labelled scales.`);
   const d=dims[0],ordered=rows.map(r=>({r,t:base.timeValue(r[d],d)})).filter(o=>o.t!=null).sort((a,b)=>a.t-b.t);if(!ordered.length)throw new Error('No valid dates in the selected groups.');const lo=ordered[0].t,hi=ordered.at(-1).t,x=t=>100+(hi===lo?.5:(t-lo)/(hi-lo))*800;
   ms.forEach((id,j)=>{const[a,b]=base.extent(rows.map(r=>r[id])),y=v=>470-(v-a)/(b-a)*370;for(let i=0;i<=5;i++)text(j?925:85,y(a+(b-a)*i/5)+4,base.format(a+(b-a)*i/5,id,cols,true),{'text-anchor':j?'start':'end',fill:palette[j]});let previous=null;for(const o of ordered){if(o.r[id]==null){previous=null;continue;}if(spec.type==='combination'&&!j)mark('rect',{x:x(o.t)-Math.min(16,330/ordered.length),y:Math.min(y(0),y(o.r[id])),width:Math.min(32,660/ordered.length),height:Math.max(1,Math.abs(y(o.r[id])-y(0))),fill:palette[0]},o.r);else {if(previous&&o.t===previous.t+1)node('line',{x1:x(previous.t),x2:x(o.t),y1:y(previous.r[id]),y2:y(o.r[id]),stroke:palette[j],'stroke-width':2});mark('circle',{cx:x(o.t),cy:y(o.r[id]),r:4.5,fill:palette[j]},o.r);}previous=o;}});ordered.forEach((o,i)=>{if(i%Math.max(1,Math.ceil(ordered.length/8))===0)text(x(o.t),505,o.r[d],{'text-anchor':'middle'});});
  }
  container.append(svg);return svg;
 }
 const api={TYPES,render,validate,partition};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.MentatContributionCharts=api;
})(globalThis);
