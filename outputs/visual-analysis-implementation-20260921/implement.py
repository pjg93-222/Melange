from pathlib import Path
import re, shutil
ROOT=Path(__file__).resolve().parents[2]
APP=ROOT/'mentat/app'
BACK=Path(__file__).parent/'pre-edit'
def edit(name, fn):
 p=APP/name
 b=BACK/name;b.parent.mkdir(parents=True,exist_ok=True)
 if not b.exists():shutil.copy2(p,b)
 s=p.read_text(encoding='utf-8');p.write_text(fn(s),encoding='utf-8')

# The existing shared stylesheet owns shell and reusable frame geometry.
def shared(s):
 s='\n'.join(line for line in s.splitlines() if not line.startswith(('#view-graph ', '#view-insights ')))
 s=s.replace('#view-loading .loading-grid,#view-collection .collection-work-grid,#view-graph .graph-panels[data-analysis=overview],#view-insights .insights-results','#view-loading .loading-grid,#view-collection .collection-work-grid')
 s += '''
/* Approved visual analysis system: Graph, PAC evidence and Insights. */
:root{--analysis-teal:#327A7A;--analysis-purple:#57447B;--analysis-plum:#342649;--analysis-paper:#FAF8F6}
body[data-view] .workspace{background:var(--analysis-paper)}
.analysis-intro{display:flex;align-items:center;justify-content:space-between;gap:16px;margin:0 0 16px}
.analysis-intro p{margin:0;font-size:15px;color:var(--muted)}
.analysis-page-actions,.analysis-chart-actions{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.analysis-page-actions{flex:none}
.analysis-page-actions :is(button,summary),.analysis-chart-actions :is(button,summary){min-height:40px;border:1px solid #c6bab0;border-radius:5px;background:white;color:var(--acu-plum);padding:8px 12px;font:400 12px var(--font-sans);cursor:pointer}
.analysis-segment{display:inline-flex;border:1px solid #c6bab0;border-radius:5px;overflow:hidden;flex:none}
.analysis-segment button{border:0!important;border-radius:0!important;margin:0;min-height:40px;padding:8px 12px;font:400 12px var(--font-sans);background:white;color:var(--acu-plum);cursor:pointer}
.analysis-segment button[aria-pressed=true]{background:var(--acu-plum);color:white}
.analysis-nav{display:flex;gap:8px;overflow-x:auto;border-bottom:1px solid var(--line);margin:12px 0 16px}
.analysis-nav :is(button,a){font:500 13px var(--font-sans);color:var(--acu-plum);background:none;border:0;border-bottom:3px solid transparent;padding:12px;text-decoration:none;white-space:nowrap;min-height:40px}
.analysis-nav [aria-current],.analysis-nav [aria-selected=true]{border-bottom-color:var(--acu-purple);font-weight:600}
.analysis-scope-line{font-size:12px;line-height:1.6;color:var(--muted);margin:8px 0}
.analysis-detail{padding:16px;background:white;border:1px solid var(--line);border-radius:7px;min-width:0}
.analysis-detail h3{font:700 22px var(--font-serif);margin:0 0 12px}
.analysis-detail p{font-size:13px;line-height:1.6;overflow-wrap:anywhere}
.analysis-detail-amount{font:400 26px var(--font-serif);font-variant-numeric:tabular-nums}
.analysis-selection{outline:2px solid var(--acu-purple);outline-offset:2px}
@media(max-width:760px){.analysis-intro{align-items:start;flex-direction:column;gap:12px}.analysis-page-actions :is(button,summary),.analysis-segment button,.analysis-chart-actions :is(button,summary){min-height:44px}.analysis-nav{gap:0}.analysis-nav :is(button,a){padding:12px 8px;min-height:44px}}
'''
 return s
edit('workspace-polish.css',shared)

def graph_template(s):
 s=s.replace('<section class="panel graph-controls"','<div class="analysis-intro"><p>Compare giving, then open the evidence behind it.</p><div id="graph-page-actions" class="analysis-page-actions"></div></div>\n<section class="panel graph-controls"',1)
 s=s.replace('<div class="analysis-strip">','<p id="graph-scope" class="analysis-scope-line" role="status"></p>\n<div class="analysis-strip">',1)
 s=s.replace('<p id="graph-scope" class="chart-note" role="status" hidden></p>','')
 s=s.replace('<h2>Top organizations</h2>','<h2>Where the giving went</h2>')
 s=s.replace('<h2>Company comparison</h2>','<h2>Giving by company</h2>')
 s=s.replace('<div id="graph-drawer-directions"','<div id="graph-selection-summary"></div><div id="graph-drawer-directions"')
 return s
edit('templates/view_graph.html',graph_template)

def graph_js(s):
 s=s.replace("organizations:id=>{remember();recipient=id;closeDrawer(false);pendingDrawer={id,direction:''};refresh();}","organizations:id=>{openDrawer(id,'');drawPanel('organizations',false);}")
 s=s.replace("get('scope').textContent=scope;","get('scope').textContent=scope+' · Net included workbook receipts · Saved coverage; completeness unverified';")
 s=s.replace("get('category-panel').hidden=!['overview','recipients'].includes(analysis);","get('category-panel').hidden=analysis!=='recipients';")
 s=s.replace("get('organization-panel').hidden=analysis!=='recipients';","get('organization-panel').hidden=!['overview','recipients'].includes(analysis);")
 s=s.replace("get('candidate-panel').hidden=!['overview','candidates'].includes(analysis);","get('candidate-panel').hidden=analysis!=='candidates';")
 s=s.replace("get('level-panel').hidden=!['overview','companies'].includes(analysis);","get('level-panel').hidden=analysis!=='companies';")
 s=s.replace("Boolean(drawer)&&analysis==='recipients'","Boolean(drawer)&&['overview','recipients'].includes(analysis)")
 s=s.replace("get('drawer-title').textContent=`Saved downstream PAC activity \\u00b7 ${drawerCycle()}`;","get('drawer-title').textContent=drawer.label;\n    const chosen=view?.organizations.find(row=>row.id===drawer.id),summary=get('selection-summary');\n    summary.replaceChildren();\n    if(chosen){const amount=document.createElement('p');amount.className='analysis-detail-amount';amount.textContent=dollars(chosen.amount);summary.append(amount);}\n    const context=document.createElement('p');context.textContent='Industry-associated net receipts · '+drawerCycle()+'. The saved PAC activity below has its own accounting scope; it is not traced company giving.';summary.append(context);")
 s=s.replace("overview:'categories'","overview:'organizations'")
 s=s.replace("const open=Boolean(details&&details.open);","const open=Boolean(details&&details.open);\n    const svg=host?.querySelector('svg');if(svg)svg.hidden=open;\n    const chartButton=document.querySelector('[data-chart-view=\"'+name+'\"]');if(chartButton)chartButton.setAttribute('aria-pressed',String(!open));\n    button.setAttribute('aria-pressed',String(open));")
 s=re.sub(r"button.textContent=open\?`Show top \$\{top.toLocaleString\(\)\}`\s*:'View all \\u2192';","button.textContent='Table';",s)
 # Upgrade the existing bar renderer, preserving callbacks, exports and tables.
 start=s.index('  function draw(name,rows,onClick,options) {')
 end=s.index('  // Item 11:',start)
 s=s[:start]+(Path(__file__).parent/'graph-draw.txt').read_text()+s[end:]
 s=s.replace("const panelWidth=container=>Math.max(420,Math.min(920,Math.round(container.clientWidth||520)));","const panelWidth=container=>Math.max(240,Math.round(container.clientWidth||520));")
 marker="  document.querySelectorAll('[data-values]').forEach(b=>b.onclick=()=>showValues(b.dataset.values));"
 s=s.replace(marker,marker+'''
  // One shared chart/table pattern; exports stay beside it in each frame.
  for(const name of PANELS){
    const host=get(name),panel=host?.closest('.graph-panel'),tools=panel?.querySelector('.graph-panel-tools'),table=panel?.querySelector('[data-values]');if(!tools||!table)continue;
    const segment=document.createElement('div');segment.className='analysis-segment';segment.setAttribute('role','group');segment.setAttribute('aria-label',titleFor[name]+' presentation');
    const chart=document.createElement('button');chart.type='button';chart.textContent='Chart';chart.dataset.chartView=name;chart.setAttribute('aria-pressed','true');chart.onclick=()=>{const detail=host.querySelector('details');if(detail)detail.open=false;labelValues(name);};
    segment.append(chart,table);tools.append(segment);const menu=get('menu-'+name);if(menu)tools.append(menu);
  }
  const pageActions=get('page-actions');
  if(pageActions){pageActions.append(get('export-menu'),get('open-sources'));get('open-sources').textContent='Sources';}
''')
 s=s.replace("if(analysis!=='recipients')selectAnalysis('recipients');","if(!['overview','recipients'].includes(analysis))selectAnalysis('recipients');")
 return s
edit('graph.js',graph_js)

def graph_css(s):
 s += '''
/* Comparison-led composition. Specialized drawer/collection behavior stays intact. */
#view-graph .graph-controls{padding:12px 16px;margin:0}
#view-graph .graph-header{display:flex;flex-wrap:wrap;gap:8px;align-items:end}
#view-graph .graph-filter-grid{flex:1 1 100%;grid-template-columns:1.3fr 1.3fr 1fr 1fr 1fr;gap:12px}
#view-graph .graph-actions{margin-left:auto}
#view-graph .graph-chips:empty{display:none}
#view-graph .analysis-strip{margin:8px 0 16px}
#view-graph .analysis-tabs{margin:0;gap:8px}
#view-graph .analysis-tabs button{border-radius:0;background:transparent;color:var(--acu-plum);border-bottom:3px solid transparent;min-height:40px;font-size:13px;padding:10px 12px}
#view-graph .analysis-tabs button[aria-selected=true]{border-bottom-color:var(--acu-purple)}
#view-graph .graph-panels{display:grid;grid-template-columns:minmax(0,1fr);gap:16px}
#view-graph .graph-panels>.panel{padding:16px;border-radius:7px;min-height:0}
#view-graph .graph-panels[data-analysis=overview],#view-graph .graph-panels[data-analysis=recipients],#view-graph .graph-panels[data-analysis=companies]{grid-template-columns:minmax(0,1fr)}
#view-graph #graph-organization-panel{order:0}
#view-graph #graph-drawer-panel{order:1}
#view-graph #graph-company-panel,#view-graph #graph-category-panel{order:2}
#view-graph .graph-panel>.panel-heading{display:flex;flex-wrap:wrap;gap:12px;margin-bottom:12px}
#view-graph .graph-panel-tools{margin-left:auto;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
#view-graph .graph-panel-tools :is(button,select,summary){min-height:40px;font-size:12px}
#view-graph .graph-panel-tools .graph-text-button{padding:8px 12px}
#view-graph .graph-bars{width:100%;height:auto;display:block;overflow:visible}
#view-graph .graph-bars[hidden]{display:none}
#view-graph .graph-bar-button:focus-visible{outline:2px solid var(--acu-purple);outline-offset:2px}
#view-graph .graph-bar-button.is-selected .graph-row{fill:#e8f3f1}
#view-graph .graph-panel-foot{margin-top:12px;font-size:12px}
#view-graph .graph-values>summary{font-size:12px}
#view-graph .graph-metrics{display:flex;flex-wrap:wrap;gap:24px;padding:12px 0;margin:16px 0;background:transparent;border:0;border-top:1px solid var(--line);border-radius:0}
#view-graph .graph-metrics>div{padding:0;flex:1;min-width:190px;border:0}
#view-graph .graph-metrics strong,#view-graph .graph-metrics>div:first-child strong{font-size:20px}
#view-graph .graph-share-track{display:none}
#view-graph .graph-metrics small{font-size:12px}
#graph-results{display:flex;flex-direction:column}#graph-results[hidden]{display:none}
#graph-analysis-panel{order:0}.graph-metrics{order:1}.graph-details-tools{order:2}
#view-graph .graph-drawer{animation:none;max-height:none}
#graph-selection-summary p{font-size:13px;line-height:1.6}
#graph-selection-summary .analysis-detail-amount{font-size:26px}
#view-graph .graph-drawer-close{font-size:12px}
@media(min-width:1250px){#view-graph .graph-panels[data-drawer=open]{grid-template-columns:minmax(0,2fr) minmax(300px,1fr)}#view-graph .graph-panels[data-drawer=open] :is(#graph-company-panel,#graph-category-panel){grid-column:1/-1}}
@media(max-width:760px){#view-graph .graph-filter-grid{grid-template-columns:repeat(2,minmax(0,1fr))}#view-graph .graph-panel-tools{margin-left:0}#view-graph .graph-panel-tools :is(button,select,summary){min-height:44px}#view-graph .graph-panels>.panel{padding:12px}#view-graph .analysis-tabs button{padding:10px 8px;min-height:44px}#view-graph .analysis-caption{display:none}}
'''
 return s
edit('graph.css',graph_css)
edit('app.js',lambda s:s.replace("evidence:'Follow PAC spending'","evidence:'PAC evidence'"))

def insights_template(s):
 s=s.replace('class="insights-heading"','class="insights-heading analysis-intro"')
 s=s.replace('Explore giving, trends, and the records behind them.','Compare periods and explain observed changes.')
 s=s.replace('<div class="insights-export"><button','<div class="insights-export analysis-page-actions"><details class="graph-menu"><summary>Export</summary><div><button',1)
 s=s.replace('>Export JSON</button></div>','>Export JSON</button></div></details><button id="insights-page-sources" type="button" class="secondary">Sources</button></div>',1)
 s=s.replace('  <section id="insights-sources"','  <nav class="analysis-nav" aria-label="Insights analysis"><button type="button" id="insights-analysis-overview" aria-current="page">Overview</button><button type="button" id="insights-analysis-choose">Choose analyses</button><button type="button" id="insights-analysis-sources">Source records</button></nav>\n  <section id="insights-sources"')
 s=s.replace('<p class="section-label">Underlying evidence</p>','')
 s=s.replace('>Close records</button>','>Clear selection</button>')
 return s
edit('templates/view_insights.html',insights_template)

def insights_js(s):
 start=s.index('  function makeChart(');end=s.index('  function closeSources(',start)
 s=s[:start]+(Path(__file__).parent/'insights-charts.txt').read_text()+s[end:]
 s=s.replace("el('results').replaceChildren();\n    for (const key of enabled)","plotObserver?.disconnect();el('results').replaceChildren();\n    for (const key of [...enabled].sort((a,b)=>(a==='trends'?-1:b==='trends'?1:0)))")
 s=s.replace("key==='trends'?'Giving trends':panel.title", "key==='trends'?'Giving through the same point in each cycle':key==='favorites'?'Favorite recipients':key==='changes'?'What changed':panel.title")
 s=s.replace("const chart = makeChart(key,panel);", "const chart = makeChart(key,panel);")
 start=s.index("      const tools=node('div',undefined,'insights-card-tools')")
 end=s.index('      if (panel.truncated',start)
 s=s[:start]+'''      const tools=node('div',undefined,'insights-card-tools analysis-chart-actions'), segment=node('div',undefined,'analysis-segment'), chartButton=node('button','Chart','secondary'),tableButton=node('button','Table','secondary'),exportButton=node('button','Export','secondary');
      tableHost.id='insights-table-'+key;tableButton.setAttribute('aria-controls',tableHost.id);
      const toggle=show=>{tableHost.hidden=!show;tablesShown[key]=show;tableButton.setAttribute('aria-expanded',String(show));tableButton.setAttribute('aria-pressed',String(show));chartButton.setAttribute('aria-pressed',String(!show));if(chart)chart.parentElement.hidden=show;};
      chartButton.type=tableButton.type=exportButton.type='button';chartButton.disabled=!chart;chartButton.onclick=()=>toggle(false);tableButton.onclick=()=>toggle(tableHost.hidden);toggle(!chart||Boolean(tablesShown[key]));
      segment.setAttribute('role','group');segment.setAttribute('aria-label',title.textContent+' presentation');segment.append(chartButton,tableButton);
      exportButton.setAttribute('aria-label','Export '+title.textContent+' as CSV');exportButton.onclick=()=>download('csv',key);tools.append(segment,exportButton);heading.append(tools);
''' +s[end:]
 # Source provenance is accessible from the page action, not a second control wall.
 s=s.replace("const details = node('details'), summary = node('summary','Source and accounting provenance')", "const details = node('details'), summary = node('summary','Source and accounting provenance')")
 s=s.replace("'Giving selection: ' + ","")
 s=s.replace("parts.join(' · ')","parts.join(' · ')+' · Saved coverage; completeness unverified'")
 marker="  el('controls').addEventListener('submit'"
 i=s.index(marker)
 s=s[:i]+'''  el('page-sources')?.addEventListener('click',()=>{const details=el('scope').querySelector('details');if(details){details.open=!details.open;if(details.open)details.scrollIntoView({block:'nearest'});}});
  el('analysis-choose')?.addEventListener('click',()=>{el('panel-picker').open=!el('panel-picker').open;el('panel-picker').scrollIntoView({block:'nearest'});});
  el('analysis-overview')?.addEventListener('click',()=>el('results').scrollIntoView({block:'start'}));
  el('analysis-sources')?.addEventListener('click',()=>{const first=el('results').querySelector('.insights-mark[role=button]');if(first)first.focus();else el('page-sources')?.click();});
''' +s[i:]
 return s
edit('insights.js',insights_js)

def insights_css(s):
 s=s.replace('grid-template-columns:repeat(3,minmax(0,1fr))','grid-template-columns:repeat(2,minmax(0,1fr))')
 s=s.replace('font-size:20px','font-size:12px')
 s += '''
/* A full-width comparison followed by generous supporting analyses. */
#view-insights .insights-results{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}
#insights-panel-trends{grid-column:1/-1}
#view-insights .insights-card{padding:16px;border-radius:7px;min-width:0}
#view-insights .insights-card h3{font:700 22px/1.2 var(--font-serif);margin:0}
#view-insights .insights-panel-heading{align-items:start;gap:12px}
#view-insights .insights-card-tools{margin-left:auto}
#view-insights .insights-panel-badge{font-size:12px;background:none;padding:0;order:3}
#view-insights .insights-card-summary{font-size:13px;line-height:1.6;min-height:0;margin:8px 0;color:var(--muted)}
#view-insights .insights-chart-area{min-height:0;margin:12px 0}
#view-insights .insights-chart{margin:0;min-width:0}
#view-insights .insights-chart svg{width:100%;height:auto;display:block}
#view-insights .insights-chart text{font:400 12px var(--font-sans);fill:var(--acu-plum)}
#view-insights .insights-chart .insights-channel-label{font-size:12px;fill:var(--muted)}
#view-insights .insights-chart-filter{font-size:12px;justify-content:start;gap:12px;margin-bottom:12px}
#view-insights .insights-chart-filter select{min-height:40px;max-width:75%}
#view-insights .insights-chart :is(figcaption,.insights-chart-legend){font-size:12px;line-height:1.6}
#view-insights .insights-chart-legend i{height:10px;width:18px}
#view-insights .insights-mark[role=button]{cursor:pointer}
#view-insights .insights-mark:is(:focus-visible,[aria-pressed=true]) rect{stroke:var(--acu-plum);stroke-width:2}
#view-insights .insights-scope{border:0;background:none;padding:0;margin:8px 0;font-size:12px;line-height:1.6}
#view-insights .insights-scope strong{display:inline;font-size:12px;font-weight:500}
#view-insights .insights-scope>div{display:inline;margin-left:8px}
#view-insights .insights-scope>details{display:none}
#view-insights .insights-scope>details[open]{display:block;background:white;padding:12px;border:1px solid var(--line);border-radius:7px}
#view-insights .insights-status:not([data-state=error]):not([data-state=loading]){display:none}
#view-insights .insights-controls{padding:12px 16px;margin-bottom:8px}
#view-insights .insights-filter-grid{gap:12px}
#view-insights .insights-card-source{font-size:12px!important;margin-top:12px!important;line-height:1.6}
#view-insights .insights-sources{border:1px solid var(--line);border-radius:7px}
@media(max-width:1100px){#view-insights .insights-results{grid-template-columns:minmax(0,1fr)}}
@media(max-width:760px){#view-insights .insights-filter-grid{grid-template-columns:repeat(2,minmax(0,1fr))}#view-insights .insights-card{padding:12px}#view-insights .insights-chart-filter select{min-height:44px}#view-insights .insights-card-tools{margin-left:0}#view-insights .insights-card-tools button{min-height:44px}}
'''
 return s
edit('insights.css',insights_css)

def evidence_template(s):
 s=s.replace('<p class="view-intro">Follow the reported money for one PAC, or several side by side, from any industry file or saved snapshot.</p>','<div class="analysis-intro"><p>Inspect reported PAC activity and the records behind it.</p><div class="analysis-page-actions"><button type="button" class="secondary" id="evidence-page-export">Export</button><button type="button" class="secondary" id="evidence-page-sources">Sources</button></div></div>')
 s=s.replace('<label for="evidence-type">','<label class="evidence-extra-scope" for="evidence-type">').replace('<label for="evidence-find">','<label class="evidence-extra-scope" for="evidence-find">')
 return s
edit('templates/view_evidence.html',evidence_template)

def evidence_js(s):
 s=s.replace('>Summary</button>','>Overview</button>').replace('aria-pressed="false">Map</button>','aria-pressed="false">Geography</button>')
 s=s.replace('  const MAP_SKELETON = `<nav class="map-trail" aria-label="Where you are"></nav>','  const MAP_SKELETON = `')
 s=s.replace('    <div class="map-note-host"></div>\n    <div class="map-grid">','''    <div class="map-note-host"></div>
    <nav class="analysis-nav" aria-label="PAC analysis"><button type="button" data-map-overview>Overview</button><button type="button" aria-current="page" data-map-geography>Geography</button><button type="button" data-map-records>PAC routes &amp; records</button></nav>
    <nav class="map-trail" aria-label="Where you are"></nav>
    <div class="map-grid">''',1)
 s=s.replace('      <section class="map-figure" aria-label="Map">\n        <div class="map-canvas-host">','''      <section class="map-figure" aria-label="Map">
        <div class="panel-heading"><h2>Where reported money moved</h2><div class="analysis-chart-actions"><div class="analysis-segment" role="group" aria-label="Geography presentation"><button type="button" data-map-presentation="chart" aria-pressed="true">Chart</button><button type="button" data-map-presentation="table" aria-pressed="false">Table</button></div><button type="button" data-map-export>Export</button></div></div>
        <div class="map-canvas-host">''',1)
 s=s.replace('      <section class="map-ranking" aria-label="Explore places">','      <section class="map-detail analysis-detail" aria-label="Selected place evidence" hidden></section>\n      <section class="map-ranking" aria-label="Explore places">',1)
 s=s.replace("    if (state.focus) return mapFocusHtml(pane, state, reconciliation);",'')
 s=s.replace('<tr class="map-row" data-focus-kind=', '<tr class="map-row${state.focus?.key===row.key ? \' is-selected\' : \'\'}" aria-selected="${state.focus?.key===row.key}" data-focus-kind=')
 s=s.replace('class="link-button map-clear-focus">Clear</button>','class="link-button map-clear-focus">Clear selection</button>')
 # Equality is a claim: only show it when the response reconciles.
 start=s.index('    const reconciliation =',s.index('  function mapRankedHtml'))
 end=s.index('    const allRows',start)
 s=s[:start]+'''    const reconciliation = mapReconciliation(body, raised);
''' +s[end:]
 insert=s.index('  function mapRankedHtml')
 s=s[:insert]+'''  function mapReconciliation(body,raised){
    const basis=raised?'reported receipts':body.spend_basis==='consolidated_saved_network'?'saved network disbursements, excluding internal transfers':'reported disbursements';
    return body.reconciles ? `${money(body.located_total)} located + ${money(body.unlocated_total)} unlocated = ${money(body.reported_total)} ${basis}` : `${money(body.located_total)} located · ${money(body.unlocated_total)} unlocated · ${money(body.reported_total)} ${basis}. Unresolved source gap: ${money(body.reconciliation_residual)}; no verified equality.`;
  }
  function renderMapSelection(host,pane,state){
    const detail=host.querySelector('.map-detail');if(!detail)return;detail.hidden=!state.focus||!state.body;host.classList.toggle('has-selection',!detail.hidden);if(detail.hidden){detail.replaceChildren();return;}
    const rows=rankedRows(state).filter(r=>r.key===state.focus.key),known=rows.length>0,amount=rows.reduce((n,r)=>n+r.amount,0);
    render(detail,`<p class="analysis-detail-amount">${known?money(amount):'Amount unavailable on this layer'}</p><p>${escapeHtml(cycleLabel(state.cycle))} · ${state.direction==='raised'?'Reported receipts':'Reported PAC spending'} · selected geography</p>`+mapFocusHtml(pane,state,mapReconciliation(state.body,state.direction==='raised')));
  }
  function exportMap(){
    const state=mapStates.get(mapPane),pane=panes.get(mapPane);if(!state?.body||!pane)return;
    const payload={committee:pane.committee,source:pane.id,cycle:state.cycle,direction:state.direction,layer:state.layer,excluded_kinds:[...(state.off||[])],selection:state.focus,rows:rankedRows(state),reconciliation:mapReconciliation(state.body,state.direction==='raised'),basis:state.body.spend_basis,coverage:'Saved observations; completeness unverified'};
    const url=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='mentat-pac-geography-'+pane.committee+'-'+state.cycle+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
''' +s[insert:]
 s=s.replace("render(host.querySelector('.map-ranked'), mapRankedHtml(pane, state));","render(host.querySelector('.map-ranked'), mapRankedHtml(pane, state));\n    renderMapSelection(host,pane,state);")
 s=s.replace("render(host.querySelector('.map-ranked'),mapRankedHtml(panes.get(mapPane),state));applyBars(host);","render(host.querySelector('.map-ranked'),mapRankedHtml(panes.get(mapPane),state));renderMapSelection(host,panes.get(mapPane),state);applyBars(host);")
 marker="  $('evidence-map').addEventListener('click', event => {"
 s=s.replace(marker,marker+'''
    if(event.target.closest('[data-map-export]')){exportMap();return;}
    if(event.target.closest('[data-map-overview]')){closeMap();return;}
    if(event.target.closest('[data-map-geography]')){const host=$('evidence-map');host.classList.remove('map-table-view');return;}
    if(event.target.closest('[data-map-records]')){const pane=panes.get(mapPane);closeMap();if(pane){pane.rowsOpen=true;renderPanes();}return;}
    const presentation=event.target.closest('[data-map-presentation]');if(presentation){const host=$('evidence-map'),table=presentation.dataset.mapPresentation==='table';host.classList.toggle('map-table-view',table);host.querySelectorAll('[data-map-presentation]').forEach(b=>b.setAttribute('aria-pressed',String(b===presentation)));if(table)host.querySelector('.map-ranking').scrollIntoView({block:'nearest'});return;}
''')
 marker='  function start() {'
 s=s.replace(marker,'''  $('evidence-page-export')?.addEventListener('click',()=>{if(mapPane)exportMap();else{const pane=panes.values().next().value;if(pane)openMap(pane.key);}});
  $('evidence-page-sources')?.addEventListener('click',()=>{if(mapPane){const details=$('evidence-map').querySelector('.map-source-details');if(details){details.open=!details.open;details.scrollIntoView({block:'nearest'});}}else $('evidence-import-open').click();});
''' +marker)
 return s
edit('evidence.js',evidence_js)

def workspace_css(s):
 s=s.replace('.workspace:has(#view-evidence.map-open:not([hidden])) > .workspace-heading { display: none; }','')
 s=s.replace('grid-template-columns: minmax(0, 1.45fr) minmax(0, 1fr);','grid-template-columns: minmax(0, 1fr);')
 s += '''
/* Geography uses the shared analysis frame; ranking and selection coexist. */
#view-evidence .evidence-scope{padding:12px 16px}
#view-evidence .evidence-scope-grid{grid-template-columns:1.3fr 1fr 1.1fr 1.4fr .8fr auto;gap:12px}
#evidence-map{border:0;background:none;padding:0;display:flex;flex-direction:column;gap:8px}
#evidence-map[hidden]{display:none}
#evidence-map .map-head{align-items:center;margin:0}
#evidence-map .map-head h2{font:600 15px var(--font-sans);line-height:1.5}
#evidence-map .map-source-heading{font-size:12px;margin:4px 0}
#evidence-map .map-toolbar-card{border-radius:7px;padding:12px 16px}
#evidence-map .map-controls-help{display:none}
#evidence-map .map-toolbar :is(button,select,input){min-height:40px;font-size:12px}
#evidence-map .map-toolbar .seg button{min-height:40px;font-size:12px}
#evidence-map .map-grid{gap:16px;grid-template-columns:minmax(0,1fr)}
#evidence-map .map-figure{padding:16px;background:white;border:1px solid var(--line);border-radius:7px}
#evidence-map .map-figure>.panel-heading{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin:0 0 12px}
#evidence-map .map-figure>.panel-heading h2{font:700 22px var(--font-serif);margin:0}
#evidence-map .analysis-chart-actions{margin-left:auto}
#evidence-map .map-canvas-host{background:white}
#evidence-map svg.map-canvas{height:420px;min-height:340px}
#evidence-map .map-ranking{grid-column:1;min-width:0;border:1px solid var(--line);border-radius:7px;background:white;padding:16px}
#evidence-map .map-ranked{border:0;padding:0;border-radius:0}
#evidence-map .map-detail{grid-column:1;min-width:0}
#evidence-map .map-detail .panel-heading{display:flex;gap:12px;flex-wrap:wrap}
#evidence-map .map-detail h2{font:700 22px var(--font-serif)}
#evidence-map .map-detail .table-scroll{max-height:420px;overflow:auto}
#evidence-map .map-detail .analysis-detail-amount{font:400 26px var(--font-serif);margin:0 0 8px}
#evidence-map .map-detail .map-reconcile{font-size:12px}
#evidence-map .map-row.is-selected{background:#e8f3f1;outline:1px solid var(--acu-purple);outline-offset:-1px}
#evidence-map .map-list :is(td,th,button){font-size:12px}
#evidence-map .map-list .bartrack{height:12px}
#evidence-map .map-legend-card{padding:12px 0}
#evidence-map .map-legend-card .map-ramp{background:#7cbfb7}
#evidence-map .map-legend-key,#evidence-map .map-legend-low,#evidence-map .map-legend-high,#evidence-map .map-legend-scope{font-size:12px}
#evidence-map .map-legend-key{line-height:1.6}
#evidence-map .map-trail{font-size:12px;margin:0}
#evidence-map .analysis-nav{margin:0}
#evidence-map .map-note-host{font-size:12px}
#evidence-map.map-table-view .map-canvas-host{display:none}
@media(min-width:1250px){#evidence-map.has-selection:not(.enlarged) .map-grid{grid-template-columns:minmax(0,2fr) minmax(300px,1fr)}#evidence-map.has-selection .map-detail{grid-column:2;grid-row:1/3}}
@media(max-width:1249px){#view-evidence .evidence-scope-grid{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:760px){#view-evidence .evidence-scope-grid{grid-template-columns:repeat(2,minmax(0,1fr))}#evidence-map .map-figure,#evidence-map .map-ranking{padding:12px}#evidence-map .analysis-chart-actions{margin-left:0}#evidence-map svg.map-canvas{height:300px;min-height:0}#evidence-map .map-toolbar :is(button,select,input){min-height:44px}#evidence-map .map-toolbar .seg button{min-height:44px}#evidence-map .map-detail{grid-row:2}#evidence-map .map-ranking{grid-row:3}}
'''
 return s
edit('workspace.css',workspace_css)
