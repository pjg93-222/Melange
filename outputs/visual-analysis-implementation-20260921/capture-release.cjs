const fs=require('fs'),path=require('path'),os=require('os'),assert=require('assert/strict');
const{chromium}=require(require.resolve('playwright',{paths:[path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules')]}));
(async()=>{
const phase='reviewfix2',browser=await chromium.launch({channel:'chrome',headless:true}),errors=[],metrics=[];
const page=await browser.newPage({viewport:{width:1440,height:1000},reducedMotion:'reduce'});page.setDefaultTimeout(120000);page.on('pageerror',e=>errors.push(e.message));
const origin='http://127.0.0.1:8806',review=path.resolve(__dirname,'../../.impeccable/review');fs.mkdirSync(review,{recursive:true});
async function capture(view,selected=false){for(const[w,h]of[[1440,1000],[1168,880],[900,844],[390,844]]){
 await page.setViewportSize({width:w,height:h});await page.waitForTimeout(350);await page.evaluate(()=>{document.activeElement?.blur();scrollTo(0,0);});
 const name=`${phase}-${view}${selected?'-selected':''}-${w}`,file=path.join(__dirname,name+'.png');await page.screenshot({path:file});fs.copyFileSync(file,path.join(review,`${view}${selected?'-selected':''}-${w===1440?'desktop':w===390?'mobile':w}.png`));
 if(w===1440||w===390)await page.screenshot({path:path.join(__dirname,name+'-full.png'),fullPage:true});
 const data=await page.evaluate(()=>({scroll:document.documentElement.scrollWidth,viewport:innerWidth,title:document.querySelector('#workspace-title').textContent,stale:document.body.innerText.includes('This console runs an older build')}));assert.equal(data.scroll,data.viewport);assert.equal(data.stale,false);metrics.push({view,selected,...data});}
 await page.setViewportSize({width:1440,height:1000});console.log('CAPTURED',view,selected?'selection':'overview');
}
try{
 await page.goto(origin+'/?industry=Credit%20Union#graph');await page.locator('#graph-results').waitFor({state:'visible'});await capture('graph');
 const scopeBefore=await page.locator('#graph-scope').innerText();await page.locator('#graph-organizations .graph-bar-button').filter({hasText:"AMERICA'S CREDIT UNIONS PAC"}).first().focus();await page.keyboard.press('Enter');await page.waitForFunction(()=>!document.querySelector('#graph-drawer-panel').hidden&&document.querySelector('#graph-drawer-status').hidden);assert.equal(await page.locator('#graph-scope').innerText(),scopeBefore);await capture('graph',true);
 await page.locator('#graph-drawer-detail > summary').click();await page.locator('#graph-drawer-rows svg').waitFor();assert.ok(await page.locator('#graph-drawer-rows .graph-explorer').count());await page.locator('#graph-drawer-close').click();assert.equal(await page.locator('#graph-drawer-panel').isHidden(),true);
 await page.locator('#tab-insights').click();await page.waitForFunction(()=>document.querySelectorAll('#insights-results .insights-card').length===3);await capture('insights');
 await page.goto(origin+'/?a.source=snapshot&a.id=culac-20260921&a.committee=C00007880&a.cycle=2024&a.map=spent#evidence');await page.locator('.map-canvas-host svg.map-canvas').waitFor();await page.selectOption('#evidence-map-layer-select','state');await page.waitForTimeout(800);await capture('evidence');
 await page.locator('.map-row button').first().click();await page.locator('.map-detail').waitFor();await page.waitForTimeout(500);await capture('evidence',true);
 assert.deepEqual(errors,[]);console.log('PASS:20 live view/state captures; no page overflow, stale-build banner or page errors. Keyboard selection kept the Graph scope; expandable PAC explorer and Clear worked.');
}catch(e){await page.screenshot({path:path.join(__dirname,'release-capture-error.png'),fullPage:true});throw e;}finally{fs.writeFileSync(path.join(__dirname,'release-metrics.json'),JSON.stringify({origin,metrics,errors},null,2));await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
