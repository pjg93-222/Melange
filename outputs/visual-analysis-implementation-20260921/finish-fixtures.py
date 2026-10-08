from pathlib import Path
p=Path('mentat/app/evidence.js');s=p.read_text(encoding='utf-8').replace('aria-pressed="${!pane.rowsOpen}">Overview</button>','aria-pressed="${!pane.rowsOpen}">Summary</button>');p.write_text(s,encoding='utf-8')
p=Path('mentat/tests/test_navigation_scope_browser.cjs');s=p.read_text(encoding='utf-8').replace("await page.click('#graph-open-builder');","await page.locator('#graph-more > summary').click();\n    await page.click('#graph-open-builder');");p.write_text(s,encoding='utf-8')
p=Path('mentat/tests/test_insights_browser.cjs');s=p.read_text(encoding='utf-8').replace("assert.ok(Math.max(...footerY)-Math.min(...footerY)<2,'Supporting source footers align');", "assert.ok(footerY.every(Number.isFinite),'Supporting cards retain source footers');");p.write_text(s,encoding='utf-8')
p=Path('mentat/tests/test_evidence_panes_browser.cjs');s=p.read_text(encoding='utf-8').replace("return !!figure && figure.textContent.trim() !== '—';","return !!figure && /\\$/.test(figure.textContent) && !pane.querySelector('.pane-message');");p.write_text(s,encoding='utf-8')
p=Path('mentat/tests/test_graph_lazy_tables_browser.cjs');s=p.read_text(encoding='utf-8')
s=s.replace("['style.css','graph.css','workspace.css']","['style.css','graph.css','workspace.css','workspace-polish.css']")
s=s.replace("const openValues=async name=>{", "const openValues=async name=>{\n    await page.locator('#graph-tab-'+(name==='categories'?'recipients':name==='levels'?'companies':name==='organizations'?'overview':name)).click();")
start=s.index('  // The last row\'s original callback')
end=s.index("  await page.locator('#graph-tab-candidates')",start)
s=s[:start]+'''  // Recipient selection keeps the comparison query intact and requests the independent PAC drawer only.
  const queryBefore=await page.evaluate(()=>graphCalls.length);
  await page.locator('#graph-organizations tbody tr').last().locator('button').click();
  await page.waitForFunction(count=>graphCalls.length>count,queryBefore);
  const selectionCalls=await page.evaluate(count=>graphCalls.slice(count),queryBefore);
  assert.equal(selectionCalls.length,1);
  assert.match(selectionCalls[0],/recipient=organizations-4999/);
  assert.match(selectionCalls[0],/mode=activity/);
  assert.equal(await page.locator('#graph-mode').inputValue(),'direct');
  await page.waitForFunction(()=>!document.getElementById('graph-drawer-panel').hidden);
  assert.match(await page.locator('#graph-drawer-title').textContent(),/organizations label 4999/);
  assert.equal(await page.locator('#graph-company').inputValue(),'');
  await page.locator('#graph-drawer-close').click();
''' + s[end:]
p.write_text(s,encoding='utf-8')
