const fs=require('fs'),path=require('path'),os=require('os');
const {chromium}=require(require.resolve('playwright',{paths:[path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules')]}));
(async()=>{const phase=process.argv[2]||'rebuild',browser=await chromium.launch({channel:'chrome',headless:true}),errors=[],metrics=[];
const page=await browser.newPage({viewport:{width:1440,height:1000},reducedMotion:'reduce'});page.setDefaultTimeout(90000);page.on('pageerror',e=>errors.push(e.message));page.on('console',e=>{if(e.type()==='error')errors.push(e.text());});
async function capture(view){for(const[w,h]of[[1440,1000],[1168,880],[900,844],[390,844],[2048,1360]]){
await page.setViewportSize({width:w,height:h});await page.waitForTimeout(450);await page.evaluate(()=>{document.activeElement?.blur();scrollTo(0,0)});
await page.mouse.move(0,0);await page.screenshot({path:path.join(__dirname,`${phase}-${view}-${w}.png`)});if(w===1440||w===390)await page.screenshot({path:path.join(__dirname,`${phase}-${view}-${w}-full.png`),fullPage:true});
metrics.push(await page.evaluate(({view})=>({view,width:innerWidth,overflow:document.documentElement.scrollWidth-innerWidth,stale:document.body.innerText.includes('This console runs an older build'),regions:[...document.querySelectorAll('#graph-organization-panel,#graph-company-panel,#graph-drawer-panel,#insights-panel-trends,#insights-panel-favorites,#insights-panel-changes,.map-figure,.map-detail,.map-ranked-chart')].filter(e=>e.getBoundingClientRect().width).map(e=>({id:e.id||e.className,x:e.getBoundingClientRect().x,y:e.getBoundingClientRect().y,width:e.getBoundingClientRect().width,height:e.getBoundingClientRect().height}))}),{view}));
}await page.setViewportSize({width:1440,height:1000});console.log('CAPTURED',view);}
try{
await page.goto('http://127.0.0.1:8806/?industry=Credit%20Union#graph');await page.locator('#graph-results').waitFor({state:'visible'});await capture('graph');
await page.locator('#graph-organizations .graph-bar-button').filter({hasText:"AMERICA'S CREDIT UNIONS PAC"}).first().click();await page.waitForFunction(()=>!document.querySelector('#graph-drawer-panel').hidden&&document.querySelector('#graph-drawer-status').hidden);await capture('graph-selected');
await page.locator('#tab-insights').click();await page.waitForFunction(()=>document.querySelectorAll('#insights-results .insights-card').length===3);await capture('insights');
await page.goto('http://127.0.0.1:8806/?a.source=snapshot&a.id=culac-20260921&a.committee=C00007880&a.cycle=2024&a.map=spent#evidence');await page.locator('.map-canvas-host svg.map-canvas').waitFor();await page.selectOption('#evidence-map-layer-select','state');await page.waitForTimeout(600);await capture('evidence');
await page.locator('.map-comparison-row').filter({hasText:'California'}).click();await page.locator('.map-detail').waitFor();await page.waitForTimeout(500);await capture('evidence-selected');
console.log(JSON.stringify({errors,failures:metrics.filter(m=>m.overflow||m.stale),desktop:metrics.filter(m=>m.width===1440)},null,2));
}finally{fs.writeFileSync(path.join(__dirname,phase+'-metrics.json'),JSON.stringify({metrics,errors},null,2));await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1});
