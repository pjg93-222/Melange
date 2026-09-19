/* Read-only live launch check. Browser storage exists only in this test context. */
const assert = require('node:assert/strict');
const path = require('node:path');
const os = require('node:os');
const modules = path.join(os.homedir(), '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules');
const {chromium} = require(require.resolve('playwright', {paths:[modules]}));
(async () => {
  const browser = await chromium.launch({headless:true,channel:'chrome'});
  try {
    const origin=process.env.MENTAT_SMOKE_ORIGIN || 'http://127.0.0.1:8805';
    const context=await browser.newContext();
    const page=await context.newPage();
    const errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    await page.route('**/*',route => route.request().method()==='GET' && route.request().url().startsWith(origin+'/')
      ? route.continue() : route.abort());
    const response=await page.goto(origin+'/#loading');
    assert.equal(response.status(),200);
    await page.waitForFunction(()=>typeof window.MentatCoverage?.html==='function' &&
      document.querySelector('#loading-coverage').textContent.trim().length>0,{},{timeout:30000});
    await page.locator('#sector').fill('Launch smoke test');
    await page.locator('.company-name').first().fill('Fixture company');
    assert.match(await page.locator('#loading-coverage').innerText(),/Unverifiable|No saved collection evidence/);
    assert.deepEqual(errors,[]);
    const health=await (await context.request.get(origin+'/api/health')).json();
    const asset=await context.request.get(origin+'/coverage-view.js');
    assert.equal(asset.status(),200);
    assert.equal(health.read_only,false);
    assert.match(health.server_code_sha256,/^[a-f0-9]{64}$/);
    const expectedHash=require('node:crypto').createHash('sha256').update(require('node:fs').readFileSync(path.join(__dirname,'../mentat/app/server.py'))).digest('hex');
    assert.equal(health.server_code_sha256,expectedHash);
    console.log(JSON.stringify({origin,coverageScript:asset.status(),coverageGlobal:'defined',pageErrors:errors,readOnly:health.read_only,currentCode:true}));
    await context.close();
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
