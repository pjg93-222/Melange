const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const {chromium}=require(require.resolve('playwright',{paths:[process.env.MENTAT_NODE_MODULES||path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules')]}));
const app=path.join(__dirname,'../app');
test('one through four charts retain independent variants, hidden options and optional linked filters',{timeout:180000},async t=>{
 const browser=await chromium.launch({headless:true,channel:'chrome'});t.after(()=>browser.close());
 const context=await browser.newContext({viewport:{width:1600,height:1100}}),errors=[];
 const scripts=['theme.js','chart-math.js','grouped-chart.js','charts.js','chart-studio-core.js','contribution-plot.js','contribution-charts.js','contribution-map.js','chart-studio-contributions.js','chart-studio.js','chart-comparison.js'];
 const boot=`document.querySelectorAll('[role="tabpanel"][id^="view-"]').forEach(p=>p.hidden=p.id!=='view-chart-studio');window.currentView='chart-studio';window.selectedRun='published-reports';window.escapeHtml=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');window.MentatExport={download:()=>{},image:async()=>{}};`;
 const html=fs.readFileSync(path.join(app,'index.html'),'utf8').replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi,'').replace('</body>','<script>'+boot+'</script>'+scripts.map(f=>'<script src="/'+f+'"></script>').join('')+'</body>');
 const fields=[...['company','year','cycle','party','state','recipient_state','represented_state'].map(id=>({id,label:id,role:'dimension'})),...['amount','records','contributors'].map(id=>({id,label:id,role:'measure',unit:id==='amount'?'cents':'count'}))];
 const provenance={workbook:'Example.xlsx',workbook_sha256:'a'.repeat(64),database_sha256:'b'.repeat(64),index_token:'fixture',destination_schema:1};
 await context.route('http://comparison.fixture/**',async route=>{
  const req=route.request(),url=new URL(req.url()),file=path.basename(url.pathname),json=value=>route.fulfill({contentType:'application/json',body:JSON.stringify(value)});
  if(url.pathname.endsWith('/session'))return json({token:'fixture',read_only:true});
  if(url.pathname.endsWith('/catalog'))return json({datasets:[{id:'Example',label:'Example',available:true,fields,bases:[{id:'receipt',label:'Included receipts'}],provenance}],fields});
  if(url.pathname.endsWith('/query')){const q=req.postDataJSON();const selected=q.filters.find(f=>f.field==='company');const companies=selected?[selected.value]:['Acme','Beta'];const rows=companies.map((company,i)=>Object.fromEntries([...q.dimensions.map(d=>[d,{company,year:'2024',cycle:'2023-2024',party:'D',state:'NY',recipient_state:'DC',represented_state:'VA'}[d]]),...q.measures.map(m=>[m,m==='amount'?10000+i*5000:1])]));return json({rows,columns:[...q.dimensions,...q.measures].map(id=>fields.find(f=>f.id===id)),totals:{amount:rows.reduce((n,r)=>n+r.amount,0),records:rows.length,contributors:rows.length},basis_label:'Included receipts',group_count:rows.length,offset:0,has_more:false,provenance,reconciliation:{receipt_matches_workbook:true},notices:[]});}
  if(file.endsWith('.css')||file.endsWith('.js'))return route.fulfill({contentType:file.endsWith('.css')?'text/css':'text/javascript',body:fs.readFileSync(path.join(app,file),'utf8')});
  if(file.endsWith('.svg'))return route.fulfill({contentType:'image/svg+xml',body:'<svg xmlns="http://www.w3.org/2000/svg"/>'});
  return route.fulfill({contentType:'text/html',body:html});
 });
 const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));await page.goto('http://comparison.fixture/#chart-studio');
 await page.locator('#studio-canvas svg').waitFor();await page.getByRole('button',{name:'4 charts',exact:true}).click();
 const frame=id=>page.frameLocator('iframe[data-pane="'+id+'"]');
 for(const id of ['B','C','D'])await frame(id).locator('#studio-canvas svg').waitFor();
 await page.locator('#studio-mark').selectOption('pie');await frame('B').locator('#studio-mark').selectOption('text');
 assert.equal(await page.locator('#studio-mark').inputValue(),'pie');assert.equal(await frame('C').locator('#studio-mark').inputValue(),'bar');
 await page.getByRole('button',{name:'Canvas only in every chart',exact:true}).click();assert.equal(await page.locator('.studio-side').isVisible(),false);assert.equal(await frame('B').locator('.studio-side').isVisible(),false);
 await page.getByRole('button',{name:'2 charts',exact:true}).click();assert.equal(await page.locator('iframe[data-pane="D"]').isVisible(),false);
 await page.getByRole('button',{name:'4 charts',exact:true}).click();await page.getByRole('button',{name:'Builder in every chart',exact:true}).click();assert.equal(await frame('B').locator('#studio-mark').inputValue(),'text');
 await page.getByRole('button',{name:'3 charts',exact:true}).click();assert.equal(await page.locator('iframe[data-pane="C"]').isVisible(),true);assert.equal(await page.locator('iframe[data-pane="D"]').isVisible(),false);
 await page.getByRole('button',{name:'1 chart',exact:true}).click();assert.equal(await page.locator('iframe[data-pane="B"]').isVisible(),false);await page.getByRole('button',{name:'4 charts',exact:true}).click();
 await page.evaluate(()=>MentatStudioPane.applyFilters([{field:'company',op:'equals',value:'Acme'}],['company']));
 await page.waitForFunction(()=>[...document.querySelectorAll('iframe')].every(f=>f.contentWindow.MentatStudioPane.filters().some(x=>x.field==='company'&&x.value==='Acme')));
 await page.locator('.studio-filter-links summary').click();await page.locator('input[data-field="company"]').uncheck();
 await frame('B').locator('body').evaluate(()=>MentatStudioPane.applyFilters([{field:'company',op:'equals',value:'Beta'}],['company']));
 assert.equal(await page.evaluate(()=>MentatStudioPane.filters().find(f=>f.field==='company').value),'Acme');
 // The destination view lives in the Data source panel, which folds itself
 // away after the first load in the page and in every pane.
 await page.locator('#studio-scope-change').click();
 await page.locator('#studio-destination').selectOption('recipient_state');await page.waitForFunction(()=>document.querySelector('#studio-canvas').textContent.includes('DC'));
 await frame('C').locator('#studio-scope-change').click();
 await frame('C').locator('#studio-destination').selectOption('represented_state');await page.waitForFunction(()=>document.querySelector('iframe[data-pane="C"]').contentDocument.querySelector('#studio-canvas').textContent.includes('VA'));
 await page.getByRole('button',{name:'Canvas only in every chart',exact:true}).click();
 if(process.env.MENTAT_COMPARISON_SCREENSHOT)await page.locator('#view-chart-studio').screenshot({path:process.env.MENTAT_COMPARISON_SCREENSHOT});
 await page.reload();for(const id of ['B','C','D'])await frame(id).locator('#studio-canvas').waitFor();assert.equal(await page.locator('button[data-count="4"]').getAttribute('aria-pressed'),'true');
 await page.getByRole('button',{name:'Builder in every chart',exact:true}).click();assert.equal(await frame('B').locator('#studio-mark').inputValue(),'text');
 await page.getByRole('button',{name:'Canvas only in every chart',exact:true}).click();await page.setViewportSize({width:390,height:900});
 assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Mobile layout should not overflow');
 assert.deepEqual(errors,[]);
});
