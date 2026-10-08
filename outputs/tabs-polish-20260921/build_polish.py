from pathlib import Path

root = Path('mentat/app')
def edit(name, old, new):
    p=root/name
    s=p.read_text(encoding='utf-8')
    assert old in s, (name, old[:100])
    p.write_text(s.replace(old,new,1),encoding='utf-8')

edit('app.js', "  for (const name of ['loading', 'collection', 'cross-reference', 'evidence', 'graph', 'chart-studio', 'insights']) {", "  document.body.dataset.view = currentView;\n  for (const name of ['loading', 'collection', 'cross-reference', 'evidence', 'graph', 'chart-studio', 'insights']) {")
edit('templates/page_head.html','</head>', '<link rel="stylesheet" href="/workspace-polish.css">\n</head>')
edit('server.py', '    "/workspace.css": ("workspace.css", "text/css; charset=utf-8"),', '    "/workspace.css": ("workspace.css", "text/css; charset=utf-8"),\n    "/workspace-polish.css": ("workspace-polish.css", "text/css; charset=utf-8"),')
edit('templates/view_loading.html','<h2>Sector & companies</h2>','<h2>Roster</h2>')

p=root/'templates/view_collection.html'
s=p.read_text(encoding='utf-8')
start=s.index('<section class="panel coverage-panel"')
end=s.index('<div id="worker-panel"')
coverage=s[start:end]
s=s[:start]+s[end:]
coverage=coverage.replace('<section class="panel coverage-panel" aria-labelledby="collection-coverage-title">','<details class="panel coverage-panel collection-disclosure" id="collection-coverage-details"><summary id="collection-coverage-title">FEC data-through by sector and cycle</summary>')
coverage=coverage.replace('<h2 id="collection-coverage-title">FEC data-through by sector and cycle</h2>','').replace('</section>','</details>')
s=s.replace('<div id="worker-panel"','<div class="collection-work-grid"><div class="collection-work-main"><div id="worker-panel"',1)
s=s.replace('<div class="bottom-grid">','</div><div class="bottom-grid">',1)
s=s.replace('<section class="panel" aria-labelledby="report-freshness-title">','</div>'+coverage+'<details class="panel collection-disclosure" id="collection-freshness-details"><summary id="report-freshness-title">Report freshness</summary>',1)
s=s.replace('<h3 id="report-freshness-title">Report freshness</h3>','')
s=s.replace('<div id="report-freshness"></div></section>','<div id="report-freshness"></div></details>')
# Place the compact progress strip before the caveat and working details.
start=s.index('<div class="metrics">');end=s.index('<span id="stopping-banner"',start)
metrics=s[start:end];s=s[:start]+s[end:]
s=s.replace('<div class="quality-panel"', metrics+'<div class="quality-panel"',1)
p.write_text(s,encoding='utf-8')

edit('templates/view_chart_studio.html','<h2 class="studio-heading">Chart Studio</h2>','<button id="studio-data-toggle" class="secondary studio-data-toggle" type="button" aria-expanded="false" aria-controls="studio-data-panel">Data &amp; fields</button>')
edit('templates/view_chart_studio.html','<aside class="studio-side" aria-label="Data">','<aside class="studio-side" id="studio-data-panel" aria-label="Data">')
edit('chart-studio.js',"  el('scope-change').onclick = () => {", "  const setDataPanel = open => {\n    document.querySelector('#view-chart-studio .studio').classList.toggle('studio-data-open', open);\n    el('data-toggle').setAttribute('aria-expanded', String(open));\n  };\n  el('data-toggle').onclick = () => setDataPanel(el('data-toggle').getAttribute('aria-expanded') !== 'true');\n  el('scope-change').onclick = () => {\n    setDataPanel(true);")
edit('chart-studio.js', "window.matchMedia('(max-width: 1200px)')", "window.matchMedia('(max-width: 1099px)')")

edit('coverage-view.js','<div class="table-scroll"><table>', '<div class="table-scroll coverage-table"><table>')
edit('coverage-view.js','<tr><td>${escape(row.industry)}', '<tr><td data-label="Sector / cycle">${escape(row.industry)}')
edit('coverage-view.js','</small></td><td>${escape(verified', '</small></td><td data-label="Verified FEC data-through">${escape(verified')
edit('coverage-view.js','<td class="coverage-${state}">','<td data-label="Coverage status" class="coverage-${state}">')
edit('coverage-view.js','<td>${escape(row.latest_observed', '<td data-label="Latest observed transaction">${escape(row.latest_observed')
edit('coverage-view.js','<td>${escape(row.reason)}', '<td data-label="Evidence">${escape(row.reason)}')

edit('cross-reference.js', 'headings.map(title => `<th>${title}</th>`)', 'headings.map(title => `<th${/amount/i.test(title) ? \' class="number"\' : \'\'}>${title}</th>`)')
edit('cross-reference.js', 'cells(row).map(value => `<td>${value}</td>`)', 'cells(row).map((value, index) => `<td${/amount/i.test(headings[index]) ? \' class="number"\' : \'\'}>${value}</td>`)')
edit('cross-reference.js', "content += '<h3>Negative adjustments without a matched original</h3>';", "content += '<details class=\"xref-adjustments\"><summary><h3>Negative adjustments without a matched original</h3></summary>';")
edit('cross-reference.js', 'before anyone calls them refunds.</p></section>', 'before anyone calls them refunds.</p></details></section>')
edit('cross-reference.js', "content += '<h3>Unusually large receipts retained for inspection</h3>", "content += '</section><section class=\"panel\"><h3>Unusually large receipts retained for inspection</h3>")

# The disclosure is now intentional; existing assertions still inspect the complete evidence.
p=Path('mentat/tests/test_console_browser.cjs')
s=p.read_text(encoding='utf-8')
s=s.replace("    assert.match(await page.locator('#collection-coverage').innerText(),/Stale coverage/);", "    await page.locator('#collection-coverage-details > summary').click();\n    assert.match(await page.locator('#collection-coverage').innerText(),/Stale coverage/);",1)
p.write_text(s,encoding='utf-8')
