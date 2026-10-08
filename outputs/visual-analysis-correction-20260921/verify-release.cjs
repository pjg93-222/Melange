const assert=require('node:assert/strict'),fs=require('fs'),path=require('path'),os=require('os'),crypto=require('crypto');
const {chromium}=require(require.resolve('playwright',{paths:[path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules')]}));
(async()=>{
const watchdog=setTimeout(()=>{console.error('Release check exceeded 120s');process.exit(1)},120000);
const base='http://127.0.0.1:8806',health=await(await fetch(base+'/api/health')).json(),assets=[];
assert.equal(health.assets_sha256,health.on_disk_assets_sha256_now);
for(const name of ['index.html','acu-theme.css','workspace.css','workspace-polish.css','graph.css','graph.js','insights.css','insights.js','evidence.js','evidence-map.js']){
 const response=await fetch(base+(name==='index.html'?'/':'/'+name));assert.equal(response.status,200,name);
 const served=Buffer.from(await response.arrayBuffer()),local=fs.readFileSync(path.resolve(__dirname,'../../mentat/app',name));
 assert.ok(served.equals(local),name+' served bytes must match disk');assets.push({name,sha256:crypto.createHash('sha256').update(served).digest('hex')});
}
const browser=await chromium.launch({channel:'chrome',headless:true});
console.log('Asset hashes verified; browser ready');
try{
 const page=await browser.newPage({viewport:{width:1440,height:1000},reducedMotion:'reduce'}),errors=[];page.setDefaultTimeout(30000);
 page.on('pageerror',e=>errors.push(e.message));page.on('console',e=>{if(e.type()==='error')errors.push(e.text())});
 await page.goto(base+'/?a.source=snapshot&a.id=culac-20260921&a.committee=C00007880&a.cycle=2024&a.map=spent#evidence');
 await page.locator('.map-canvas-host svg.map-canvas').waitFor();await page.selectOption('#evidence-map-layer-select','state');console.log('Map loaded');
 await page.locator('.map-comparison-row').filter({hasText:'California'}).click();await page.locator('.map-place-title').waitFor();
 const ranked=await page.locator('.map-ranked-chart').boundingBox();assert.ok(ranked.y+ranked.height<1000,'five ranked states fit in first viewport');
 assert.match(await page.locator('.map-legend-high').innerText(),/1,042,416/,'selection keeps the national color scale');
 const sources=page.locator('.map-record-list > li').first().locator('details');
 const linksBefore=await sources.locator('a').evaluateAll(nodes=>nodes.map(n=>n.href));assert.equal(linksBefore.length,4);
 await sources.locator('summary').click();assert.equal(await sources.locator('a:visible').count(),4);
 await sources.locator('summary').click();assert.deepEqual(await sources.locator('a').evaluateAll(nodes=>nodes.map(n=>n.href)),linksBefore);
 console.log('Desktop ranking and filing disclosures passed');await page.setViewportSize({width:390,height:844});
 const scope=page.locator('.map-scope-disclosure > summary');assert.equal(await scope.isVisible(),true);assert.match(await scope.innerText(),/C00007880/);
 await scope.click();assert.match(await page.locator('.map-head h2').innerText(),/CULAC/);await scope.click();
 assert.match(await page.locator('.map-selection-summary').innerText(),/California.*374,000/s);
 await page.locator('[data-map-selected-records]').click();assert.equal(await page.evaluate(()=>document.activeElement.id),'map-selected-evidence');
 await page.locator('[data-map-clear-summary]').click();await page.waitForFunction(()=>!document.querySelector('#evidence-map').classList.contains('has-selection'));
 assert.equal(await page.locator('.map-selection-summary').isVisible(),false);
 assert.deepEqual(errors,[]);
 fs.writeFileSync(path.join(__dirname,'live-build-receipt.json'),JSON.stringify({health,assets,checks:['served bytes match disk','five states in desktop first viewport','national scale retained on comparison selection','four first-recipient filing links preserved and operable','collapsed mobile committee identity','expanded mobile source identity','adjacent mobile selection context','records handoff scrolls and focuses evidence','clear removes linked selection'],errors},null,2));
 console.log('PASS release: current live assets, selected ranking, preserved filings, mobile identity and selection handoff; zero browser errors');
}finally{await Promise.race([browser.close(),new Promise(resolve=>setTimeout(resolve,5000))]);clearTimeout(watchdog)}
})().catch(e=>{console.error(e);process.exitCode=1});
