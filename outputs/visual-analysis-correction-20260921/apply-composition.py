from pathlib import Path
root=Path(__file__).resolve().parents[2]/'mentat'/'app'
def edit(name, old, new):
 p=root/name;s=p.read_text(encoding='utf-8');assert old in s,(name,old[:90]);p.write_text(s.replace(old,new),encoding='utf-8')
edit('acu-theme.css','--muted:#716a64;','--muted:#62596e;')
edit('acu-theme.css','--line:#e4d9d0;','--line:#d9d4de;')
edit('acu-theme.css','--chart-grid:#e8e0da;','--chart-grid:#e5e1e8;')
edit('workspace.css','.app-navigation{background:white;','.app-navigation{background:var(--analysis-paper,#FAF8F6);')
edit('workspace.css','.app-navigation .wordmark{color:var(--acu-plum);font-size:22px;letter-spacing:2px}', '.app-navigation .wordmark{color:var(--acu-plum);font:700 28px/1.2 var(--font-serif);letter-spacing:-.3px}')
edit('workspace.css','.app-navigation .workspace-tabs button{color:var(--muted);font-size:14px;font-weight:500}', '.app-navigation .workspace-tabs button{color:var(--acu-plum);font-size:16px;font-weight:500}')
edit('workspace-polish.css','--workspace-panel-border:#e7e0dc','--workspace-panel-border:#d9d4de')
edit('workspace-polish.css','body[data-view] .app-navigation .workspace-tabs{margin-top:30px}', 'body[data-view] .app-navigation .workspace-tabs{margin-top:16px;padding-top:8px;border-top:1px solid var(--line)}')
edit('workspace-polish.css','body[data-view] .app-navigation{width:180px;padding:28px 12px 20px}', 'body[data-view] .app-navigation{width:180px;padding:24px 12px 20px}')
edit('workspace-polish.css','font-size:12px;color:var(--muted)}\n.workspace :is(.graph-filter-grid', 'font-size:13px;font-weight:600;color:var(--acu-plum)}\n.workspace :is(.graph-filter-grid')
edit('workspace-polish.css','font:400 13px/1.3 var(--font-sans);border:1px solid #c6bab0','font:400 14px/1.3 var(--font-sans);border:1px solid #c8c0d1')
edit('workspace-polish.css','border:1px solid #c6bab0;border-radius:5px;background:white;color:var(--acu-plum);padding:8px 12px;font:400 12px', 'border:1px solid #b7a9c5;border-radius:5px;background:white;color:var(--acu-plum);padding:8px 12px;font:500 13px')
edit('workspace-polish.css','.analysis-segment{display:inline-flex;border:1px solid #c6bab0', '.analysis-segment{display:inline-flex;border:1px solid #b7a9c5')
edit('workspace-polish.css','padding:8px 12px;font:400 12px var(--font-sans);background:white','padding:8px 12px;font:500 13px var(--font-sans);background:white')
edit('workspace-polish.css','font:500 13px var(--font-sans);color:var(--acu-plum);background:none','font:500 14px var(--font-sans);color:var(--acu-plum);background:none')
edit('workspace-polish.css','.analysis-scope-line{font-size:12px;', '.analysis-scope-line{font-size:13px;')
edit('workspace-polish.css','body[data-view] .app-navigation .workspace-tabs{margin-top:16px;padding-top:8px;border-top:1px solid var(--line)}','body[data-view] .app-navigation .workspace-tabs{margin-top:16px;padding-top:8px;border-top:1px solid var(--line)}\n  body[data-view] .app-navigation .wordmark{padding:0 4px}')
# Six preview rows preserve the entire table and existing Top N choices.
p=root/'templates/view_graph.html';s=p.read_text(encoding='utf-8')
for name in ['organizations','companies']:
 start=s.index('id="graph-top-'+name+'"');end=s.index('</select>',start)
 s=s[:start]+s[start:end].replace('<option value="10" selected>','<option value="6" selected>Top 6</option><option value="10">')+s[end:]
p.write_text(s,encoding='utf-8')
edit('graph.css','#view-graph .graph-panel>.panel-heading{display:flex;flex-wrap:wrap;gap:12px;margin-bottom:12px}', '#view-graph .graph-panel>.panel-heading{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:8px}')
edit('graph.css','#view-graph .graph-panel-foot{margin-top:12px;font-size:12px}', '#view-graph .graph-panel-foot{margin-top:6px;font-size:12px}')
edit('graph.css','#view-graph #graph-trail{margin:8px 0}', '#view-graph #graph-trail{margin:0 0 4px;flex:none}\n#view-graph #graph-trail[hidden]{display:none}\n#view-graph #graph-status{display:none}\n#view-graph .analysis-strip{align-items:center}\n#view-graph #graph-drawer-panel>.panel-heading{position:relative;padding-right:0}\n#view-graph #graph-drawer-title{font-size:20px;text-wrap:initial;line-height:1.25}\n#view-graph #graph-drawer-close{margin-left:auto;min-height:32px;padding:4px 0}\n#graph-selection-summary .analysis-detail-amount{margin:12px 0 4px;color:var(--acu-plum);font-weight:700}\n#graph-selection-summary .graph-selection-basis{margin:0 0 16px}\n.graph-selection-facts{display:grid;grid-template-columns:76px minmax(0,1fr);gap:10px;font-size:13px;line-height:1.45;margin:0 0 16px}\n.graph-selection-facts dt{color:var(--muted)}\n.graph-selection-facts dd{margin:0;overflow-wrap:anywhere}\n#view-graph #graph-drawer-panel .graph-panel-foot{display:flex;flex-direction:column-reverse;align-items:stretch;padding:0;gap:12px}\n#view-graph #graph-drawer-evidence{background:var(--acu-plum);color:white;border:0;border-radius:5px;padding:10px 12px;text-align:center;width:100%;font-size:14px}\n#view-graph #graph-drawer-committee{font-size:12px;line-height:1.5;display:block}\n#view-graph #graph-drawer-detail{margin-top:8px}')
edit('graph.css','min-height:40px;font-size:13px;padding:10px 12px','min-height:40px;font-size:14px;padding:10px 12px')
# Scope controls occupy one row. Comparison fields remain in an explicit disclosure.
p=root/'templates/view_insights.html';s=p.read_text(encoding='utf-8')
start=s.index('    <div class="insights-filter-grid">');end=s.index('    <div class="insights-scope-actions">',start)
s=s[:start]+'''    <div class="insights-filter-grid">
      <label>Industry<select id="insights-dataset" aria-label="Insights industry"><option value="">Loading industries…</option></select></label>
      <label>Company<select id="insights-company"><option value="">All covered companies</option></select></label>
      <label>Basis<select id="insights-basis"><option value="receipt">Reported receipts</option><option value="original_observed">Observed original giving</option><option value="original_supported">Supported original giving</option><option value="pac_activity">PAC activity</option></select></label>
      <label>Funding<select id="insights-funding-source"><option value="">All reported sources</option></select></label>
      <label>Compare<button id="insights-compare-open" type="button" class="secondary">Compare periods</button></label>
    </div>
    <details class="insights-comparison-options"><summary>Comparison options</summary><div class="insights-filter-grid">
      <label>Contributions through<input id="insights-as-of" type="date" title="Include contribution dates up to this day. Blank uses today."></label>
      <label>Compare industry<select id="insights-comparison-dataset"><option value="">No industry comparison</option></select></label>
      <label>Baseline cycle<select id="insights-baseline-cycle"><option value="">Automatic</option></select></label>
      <label>Comparison cycle<select id="insights-current-cycle"><option value="">Automatic</option></select></label>
    </div></details>
''' +s[end:];p.write_text(s,encoding='utf-8')
# Consolidate the old repeated Insight composition overrides at their owning section.
p=root/'insights.css';s=p.read_text(encoding='utf-8');s=s[:s.index('/* A full-width comparison')]+'''
/* Approved composition: one compact scope, one contained plot, then two analyses. */
#view-insights .insights-results{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;align-items:start;margin-top:12px}
#insights-panel-trends{grid-column:1/-1}
#view-insights .insights-card{padding:16px;border-radius:7px;min-width:0}
#view-insights .insights-card h3{font:700 22px/1.2 var(--font-serif);margin:0}
#view-insights .insights-panel-heading{align-items:center;flex-wrap:wrap;gap:8px;margin:0 0 8px}
#view-insights .insights-card-tools{margin-left:auto;display:flex;gap:8px;flex-wrap:wrap}
#view-insights .insights-card-tools button{min-height:40px;padding:8px 12px}
#view-insights .insights-panel-badge{display:none}
#view-insights .insights-panel-badge[data-status=unavailable],#view-insights .insights-panel-badge[data-status=insufficient_history]{display:inline;font-size:12px;background:none;padding:0}
#view-insights .insights-chart-area{min-height:0;margin:0 0 8px}
#view-insights .insights-chart{margin:0;min-width:0}
#view-insights .insights-chart svg{width:100%;height:auto;display:block;max-width:none}
#view-insights .insights-chart text{font:400 13px var(--font-sans);fill:var(--acu-plum)}
#view-insights .insights-chart .insights-channel-label{font-size:12px;fill:var(--muted)}
#view-insights .insights-chart-filter{font-size:12px;justify-content:start;gap:8px;margin:0}
#view-insights .insights-panel-heading>.insights-chart-filter{font-size:0;flex:none}
#view-insights .insights-chart-filter select{min-height:40px;max-width:none;font-size:13px;min-width:140px}
#view-insights .insights-chart :is(figcaption,.insights-chart-legend){font-size:12px;line-height:1.5}
#view-insights .insights-chart-legend i{height:10px;width:16px}
#view-insights .insights-mark[role=button]{cursor:pointer}
#view-insights .insights-mark:is(:focus-visible,[aria-pressed=true]) rect{stroke:var(--acu-plum);stroke-width:2}
#view-insights .insights-controls{display:block;padding:12px 16px;margin:0 0 8px}
#view-insights .insights-filter-grid{grid-template-columns:1.1fr 1.1fr 1fr 1fr 1.2fr;gap:12px}
#view-insights #insights-compare-open{margin:6px 0 0;min-height:40px;width:100%;text-align:left;font-size:13px;font-weight:400;white-space:nowrap}
#view-insights .insights-comparison-options:not([open]){display:none}
#view-insights .insights-comparison-options[open]{margin:12px 0 0;border-top:1px solid var(--line);padding-top:8px}
#view-insights .insights-comparison-options .insights-filter-grid{grid-template-columns:repeat(4,minmax(0,1fr));margin-top:8px}
#view-insights .insights-scope-actions:empty{display:none}
#view-insights #insights-panel-picker:not([open]){display:none}
#view-insights #insights-panel-picker[open]{padding:16px;margin-bottom:16px;background:white;border:1px solid var(--line);border-radius:7px}
#view-insights .insights-scope{border:0;background:none;padding:0;margin:8px 0;font-size:12px;line-height:1.6}
#view-insights .insights-scope strong{display:inline;font-size:12px;font-weight:500}
#view-insights .insights-scope>div{display:inline;margin-left:8px}
#view-insights .insights-scope>details{display:none}
#view-insights .insights-scope>details[open]{display:block;background:white;padding:12px;border:1px solid var(--line);border-radius:7px}
#view-insights .insights-status:not([data-state=error]):not([data-state=loading]){display:none}
#view-insights .insights-evidence-footer{display:flex;gap:12px;align-items:start;justify-content:space-between;border-top:1px solid var(--line);padding-top:8px;margin-top:4px;font-size:12px}
#view-insights .insights-analysis-details{min-width:0;flex:1}
#view-insights .insights-analysis-details>summary{cursor:pointer;min-height:32px;align-content:center}
#view-insights .insights-analysis-details[open]{flex-basis:100%}
#view-insights .insights-evidence-footer:has(details[open]){flex-wrap:wrap}
#view-insights .insights-evidence-footer>.insights-source-button{min-height:32px;margin:0;align-content:center}
#view-insights .insights-card-summary{font-size:14px;line-height:1.5;min-height:0;margin:8px 0;color:var(--muted)}
#view-insights .insights-card-source{font-size:12px!important;margin-top:8px!important;line-height:1.5}
#view-insights .insights-sources{border:1px solid var(--line);border-radius:7px}
#view-insights .analysis-page-actions #insights-refresh{width:auto;flex:0 0 auto;margin:0;min-height:40px;grid-area:auto;align-self:center}
@media(max-width:1100px){#view-insights .insights-results{grid-template-columns:minmax(0,1fr)}}
@media(max-width:760px){#view-insights .insights-filter-grid,#view-insights .insights-comparison-options .insights-filter-grid{grid-template-columns:repeat(2,minmax(0,1fr))}#view-insights .insights-card{padding:12px}#view-insights .insights-chart-filter select{min-height:44px}#view-insights .insights-card-tools{margin-left:0}#view-insights .insights-card-tools button{min-height:44px}#view-insights .insights-evidence-footer{flex-wrap:wrap}#view-insights .insights-evidence-footer>.insights-source-button{min-height:44px}}
''';p.write_text(s,encoding='utf-8')
edit('evidence.js',"const detail=host.querySelector('.map-detail');if(!detail)return;", "renderRankedChart(host,state);const detail=host.querySelector('.map-detail');if(!detail)return;")
edit('evidence.js',"    renderRankedChart(host,state);\n    renderMapSelection", "    renderMapSelection")
