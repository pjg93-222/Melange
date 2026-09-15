'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const modules=process.env.MENTAT_NODE_MODULES||path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules');
const {chromium}=require(require.resolve('playwright',{paths:[modules]}));const app=path.join(__dirname,'../app');
test('Chart Studio startup only handshakes; saved evidence loads on its visible source and keeps Graph context',{timeout:120000},async t=>{
 const browser=await chromium.launch({headless:true,channel:process.env.MENTAT_BROWSER_CHANNEL||'chrome'});t.after(()=>browser.close());const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const html=fs.readFileSync(path.join(app,'index.html'),'utf8').replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi,'').replace(/<link\b[^>]*>/gi,'');await page.route('http://app.fixture/**',route=>route.fulfill({contentType:'text/html',body:html}));await page.goto('http://app.fixture/#chart-studio');
 await page.evaluate(()=>{window.calls=[];window.fetch=async url=>{calls.push(String(url));let body;if(String(url).startsWith('/api/session?light=1'))body={token:'token',read_only:true,evidence_collection_available:true};else if(url==='/api/evidence')body={snapshots:[]};else throw Error('Unexpected background request '+url);return {ok:true,json:async()=>body};};});
 for(const file of ['ui-state.js','coverage-view.js','app.js'])await page.addScriptTag({path:path.join(app,file)});
 await page.waitForFunction(()=>document.querySelector('#connection').textContent.includes('Local connection'));
 assert.deepEqual(await page.evaluate(()=>calls),['/api/session?light=1']);
 await page.locator('#tab-evidence').click();assert.equal(await page.evaluate(()=>calls.includes('/api/evidence')),false,'CSV mode needs no saved catalog');
 await page.locator('#evidence-source').selectOption('snapshot');await page.waitForFunction(()=>calls.filter(v=>v==='/api/evidence').length===1);
 await page.locator('#tab-chart-studio').click();await page.evaluate(()=>{document.querySelector('#evidence-mode').value='graph';window.dispatchEvent(new CustomEvent('mentat:graph',{detail:{filters:{company:'Example',cycle:'2024'},options:{companies:['Example']},companies:[{id:'Example'}]}}));});
 assert.equal(await page.evaluate(()=>calls.filter(v=>v==='/api/evidence').length),1,'hidden Graph context changes must not load financial evidence');
 await page.locator('#tab-evidence').click();await page.waitForFunction(()=>calls.filter(v=>v==='/api/evidence').length===2);
 assert.equal(await page.locator('#evidence-mode').inputValue(),'graph');assert.equal(await page.locator('#evidence-source').inputValue(),'snapshot');assert.deepEqual(errors,[]);
});
test('An older build on disk raises the restart banner, and the stamp names the console answering',{timeout:120000},async t=>{
 const browser=await chromium.launch({headless:true,channel:process.env.MENTAT_BROWSER_CHANNEL||'chrome'});t.after(()=>browser.close());const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const html=fs.readFileSync(path.join(app,'index.html'),'utf8').replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi,'').replace(/<link\b[^>]*>/gi,'');await page.route('http://app.fixture/**',route=>route.fulfill({contentType:'text/html',body:html}));await page.goto('http://app.fixture/#chart-studio');
 await page.evaluate(()=>{window.calls=[];const build={git_sha:'2906980d1',code_sha256:'a'.repeat(64),assets_sha256:'b'.repeat(64),on_disk_code_sha256_now:'c'.repeat(64),on_disk_assets_sha256_now:'b'.repeat(64),started_at:1757809380,port:8803,pid:79412,busy:false};window.fetch=async url=>{calls.push(String(url));let body;if(String(url).startsWith('/api/session?light=1'))body={token:'token',read_only:false,evidence_collection_available:true,api_version:2,build,...build};else if(url==='/api/evidence')body={snapshots:[]};else throw Error('Unexpected background request '+url);return {ok:true,json:async()=>body};};});
 for(const file of ['ui-state.js','coverage-view.js','app.js'])await page.addScriptTag({path:path.join(app,file)});
 await page.waitForFunction(()=>document.querySelector('#stale-banner')&&document.querySelector('#stale-banner').hidden===false);
 assert.equal(await page.locator('#stale-banner-message').textContent(),'This console runs an older build. Press Restart, or close this tab and open http://app.fixture.');
 assert.equal(await page.locator('#stale-restart').textContent(),'Restart');
 assert.match(await page.locator('#build-stamp').textContent(),/^build 2906980 · port 8803 · up since .+$/);
 assert.deepEqual(await page.evaluate(()=>calls),['/api/session?light=1'],'the stamp must not cost an extra startup request');
 assert.deepEqual(errors,[]);
});
test('Changed interface files ask for a restart, and a current build shows no banner',{timeout:120000},async t=>{
 const browser=await chromium.launch({headless:true,channel:process.env.MENTAT_BROWSER_CHANNEL||'chrome'});t.after(()=>browser.close());
 const html=fs.readFileSync(path.join(app,'index.html'),'utf8').replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi,'').replace(/<link\b[^>]*>/gi,'');
 for(const scenario of [{name:'assets',on_disk_assets_sha256_now:'d'.repeat(64),banner:true,action:'Restart'},{name:'current',banner:false}]){
  const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('http://app.fixture/**',route=>route.fulfill({contentType:'text/html',body:html}));await page.goto('http://app.fixture/#chart-studio');
  await page.evaluate(scenario=>{window.calls=[];const build={git_sha:'unknown',code_sha256:'a'.repeat(64),assets_sha256:'b'.repeat(64),on_disk_code_sha256_now:'a'.repeat(64),on_disk_assets_sha256_now:scenario.on_disk_assets_sha256_now||'b'.repeat(64),started_at:1757809380,port:8802,pid:41288,busy:false};window.fetch=async url=>{calls.push(String(url));let body;if(String(url).startsWith('/api/session?light=1'))body={token:'token',read_only:false,evidence_collection_available:true,api_version:2,build,...build};else if(url==='/api/evidence')body={snapshots:[]};else throw Error('Unexpected background request '+url);return {ok:true,json:async()=>body};};},scenario);
  for(const file of ['ui-state.js','coverage-view.js','app.js'])await page.addScriptTag({path:path.join(app,file)});
  await page.waitForFunction(()=>document.querySelector('#build-stamp')!==null);
  assert.equal(await page.locator('#stale-banner').isVisible(),scenario.banner,scenario.name);
  if(scenario.banner){
   assert.equal(await page.locator('#stale-banner-message').textContent(),'This console runs an older build. Press Restart, or close this tab and open http://app.fixture.');
   assert.equal(await page.locator('#stale-restart').textContent(),scenario.action);
  }
  // Git unavailable falls back to the code tree hash, never to a blank stamp.
  assert.match(await page.locator('#build-stamp').textContent(),/^build aaaaaaa · port 8802 · up since .+$/);
  assert.deepEqual(errors,[],scenario.name);
  await page.close();
 }
});
