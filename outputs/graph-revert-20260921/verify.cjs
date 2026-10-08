const fs=require('fs'),path=require('path'),os=require('os'),assert=require('node:assert/strict');
const {chromium}=require(require.resolve('playwright',{paths:[path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules')]}));
(async()=>{const browser=await chromium.launch({channel:'chrome',headless:true});try{
const page=await browser.newPage({viewport:{width:1440,height:1000},reducedMotion:'reduce'}),errors=[];page.setDefaultTimeout(30000);page.on('pageerror',e=>errors.push(e.message));
await page.goto('http://127.0.0.1:8806/?industry=Credit%20Union#graph');await page.locator('#graph-results').waitFor({state:'visible'});
assert.equal(await page.locator('#graph-category-panel').isVisible(),true);assert.equal(await page.locator('#graph-candidate-panel').isVisible(),true);
assert.equal(await page.locator('#graph-organization-panel').isVisible(),false);
const metrics=await page.locator('.graph-metrics').boundingBox(),categories=await page.locator('#graph-category-panel').boundingBox(),candidates=await page.locator('#graph-candidate-panel').boundingBox();
assert.ok(metrics.y<categories.y);assert.equal(categories.y,candidates.y);assert.ok(candidates.x>categories.x);
await page.screenshot({path:path.join(__dirname,'restored-graph-1440.png')});
await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(__dirname,'restored-graph-390.png')});
await page.setViewportSize({width:1440,height:1000});await page.locator('#graph-tab-recipients').click();await page.locator('#graph-organization-panel').waitFor({state:'visible'});await page.locator('#graph-tab-overview').click();
await page.locator('#tab-insights').click();await page.waitForFunction(()=>document.querySelectorAll('#insights-results .insights-card').length===3);
assert.equal(await page.locator('#insights-panel-trends').isVisible(),true);await page.locator('#tab-graph').click();await page.locator('#graph-results').waitFor({state:'visible'});
assert.deepEqual(errors,[]);assert.equal(await page.evaluate(()=>document.body.innerText.includes('This console runs an older build')),false);
fs.writeFileSync(path.join(__dirname,'verification.json'),JSON.stringify({metrics,categories,candidates,errors,checks:['original summary above charts','recipient types and candidates side by side','recipient navigation','Insights remains available','no stale banner']},null,2));console.log('PASS: original Graph composition and navigation restored; Insights intact; no browser errors');
}finally{await Promise.race([browser.close(),new Promise(r=>setTimeout(r,5000))])}})().catch(e=>{console.error(e);process.exitCode=1});
