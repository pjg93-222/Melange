from pathlib import Path
root=Path(__file__).resolve().parents[2]
source=root/'outputs/mentat-full-audit-2026-09-13/frontend'
tests=root/'mentat/tests'
text=(source/'repro-period-analysis.cjs').read_text()
text=text.replace("path.resolve(__dirname,'../../../mentat/app')","path.resolve(__dirname,'../app')")
text=text.replace("try{\n  const page", "try{\n for (const transform of ['yoy','change','forecast']) {\n  const page")
text=text.replace("await page.evaluate(()=>{const state=", "await page.evaluate(transform=>{const state=")
text=text.replace("state.analytics.transform='forecast'", "state.analytics.transform=transform")
text=text.replace("sheets:[state],active:0}}));});", "sheets:[state],active:0}}));},transform);")
start=text.index("await page.waitForFunction(()=>document.querySelector('#studio-error')")
end=text.index(" }finally{await browser.close();}",start)
text=text[:start]+'''await page.waitForFunction(()=>document.querySelector('#studio-canvas svg'));
  assert.equal(await page.locator('#studio-error').textContent(),'');
  const labels=await page.locator('#studio-canvas svg title').allTextContents();
  assert.ok(labels.length>=7,transform+' needs period marks');
  if(transform==='forecast'){
    assert.ok(await page.locator('#studio-canvas [stroke-dasharray="7 5"]').count(),'Projection must be distinguished from observed money');
    assert.ok(labels.some(x=>x.includes('Same-phase baseline')));
    assert.ok(labels.some(x=>x.includes('100')),'Cents are converted to dollars');
  }else if(transform==='change')assert.ok(labels.some(x=>x.includes('10')),'Annual change is $10');
  console.log(transform+': rendered successfully');await page.close();
 }
'''+text[end:]
(tests/'test_studio_temporal_regression_browser.cjs').write_text(text)
text=(source/'repro-stale-inspection.cjs').read_text().replace("path.resolve(__dirname,'../../../mentat/app')","path.resolve(__dirname,'../app')")
text=text.replace("const response=value=>", "window.stale=false;const response=value=>")
text=text.replace("provenance:{...provenance,workbook_sha256:","provenance:window.stale?{...provenance,workbook_sha256:")
text=text.replace("index_token:'new-index'}})","index_token:'new-index'}:provenance})")
text=text.replace("contributor:'CHANGED SOURCE DONOR',amount_cents:90000,raw_cents:90000", "contributor:window.stale?'CHANGED SOURCE DONOR':'ORIGINAL DONOR',amount_cents:window.stale?90000:10000,raw_cents:window.stale?90000:10000")
start=text.index("await page.locator('#inspect-all').click();")
end=text.index(" }finally{await browser.close();}",start)
text=text[:start]+'''await page.locator('#inspect-all').click();
  await page.waitForFunction(()=>document.querySelector('#record-table').textContent.includes('ORIGINAL DONOR'));
  assert.match(await page.locator('#record-table').textContent(),/\\$100\\.00/);
  await page.evaluate(()=>window.stale=true);
  await page.locator('#inspect-all').click();
  await page.waitForFunction(()=>document.querySelector('#error').textContent.includes('Source changed'));
  assert.doesNotMatch(await page.locator('#record-table').textContent(),/CHANGED SOURCE DONOR/);
  assert.match(await page.locator('#receipt-values').textContent(),/\\$100\\.00/);
  console.log('Matching source accepted; stale inspection rejected.');
'''+text[end:]
(tests/'test_studio_inspection_regression_browser.cjs').write_text(text)
