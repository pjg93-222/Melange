const fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const {chromium}=require(require.resolve('playwright',{paths:[path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules')]}));
(async()=>{
 const out=__dirname,phase=process.argv[2]||'before';
 const browser=await chromium.launch({channel:'chrome',headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1000},reducedMotion:'reduce'});page.setDefaultTimeout(60000);
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:8806/?industry=Credit%20Union#graph');
 await page.locator('#graph-results').waitFor({state:'visible'});
 console.log('GRAPH',await page.locator('#graph-industry').inputValue(),await page.locator('#graph-run').inputValue());
 const sizes=[[1440,1000],[1168,880],[900,844],[390,844]];
 const metrics=[];
 async function captures(view){for(const [width,height]of sizes){await page.setViewportSize({width,height});await page.waitForTimeout(350);await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:path.join(out,`${phase}-${view}-${width}.png`),fullPage:false});if(width===1440||width===390)await page.screenshot({path:path.join(out,`${phase}-${view}-${width}-full.png`),fullPage:true});metrics.push({view,width,height,...await page.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth,head:document.querySelector('#workspace-title').textContent}))});}await page.setViewportSize({width:1440,height:1000});}
 await captures('graph');
 await page.locator('#tab-insights').click();await page.waitForFunction(()=>document.querySelector('.insights-card')||document.querySelector('#insights-status').dataset.state==='error',{},{timeout:60000}).catch(()=>{});console.log('INSIGHTS STATUS',await page.locator('#insights-status').innerText());
 console.log('INSIGHTS',await page.locator('#insights-dataset').inputValue());await captures('insights');
 await page.locator('#tab-evidence').click();await page.waitForFunction(()=>document.querySelector('#evidence-source').options.length>1);
 console.log('SOURCES',await page.locator('#evidence-source option').evaluateAll(x=>x.map(o=>({value:o.value,label:o.textContent}))));
 const sources=await page.locator('#evidence-source option').evaluateAll(x=>x.map(o=>({value:o.value,label:o.textContent})));
 const source=sources.find(s=>/snapshot/.test(s.value)&&/credit|union|CUNA/i.test(s.label))||sources.find(s=>/snapshot/.test(s.value))||sources.find(s=>s.value);
 await page.selectOption('#evidence-source',source.value);await page.waitForFunction(()=>!document.querySelector('#evidence-add').disabled);
 await page.locator('#evidence-add').click();await page.waitForFunction(()=>{const p=document.querySelector('.evidence-pane');return p && !p.querySelector('.pane-message') && p.querySelector('.pane-map');},null,{timeout:120000});
 console.log('PANE',await page.locator('.evidence-pane').first().innerText());
 const map=page.locator('.pane-map').first();if(await map.count()){await map.click();await page.locator('.map-canvas-host svg.map-canvas').waitFor();}
 await page.selectOption('#evidence-map-cycle','2024');await page.waitForFunction(()=>document.querySelector('.map-row'));
 await page.selectOption('#evidence-map-layer-select','state');await page.waitForTimeout(1000);
 await captures('evidence');
 await page.locator('.map-row button').first().click();await page.locator('.map-detail').waitFor();await page.waitForTimeout(1000);await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:path.join(out,`${phase}-evidence-selected.png`),fullPage:true});
 await page.locator('#tab-graph').click();await page.locator('#graph-organizations .graph-bar-button').filter({hasText:"AMERICA'S CREDIT UNIONS PAC"}).first().focus();await page.keyboard.press('Enter');await page.locator('#graph-drawer-panel').waitFor();await page.waitForFunction(()=>document.querySelector('#graph-drawer-status').hidden,null,{timeout:120000});
 for(const [width,height]of sizes){await page.setViewportSize({width,height});await page.waitForTimeout(350);await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:path.join(out,`${phase}-graph-selected-${width}.png`),fullPage:true});}
 fs.writeFileSync(path.join(out,`${phase}-metrics.json`),JSON.stringify({origin:'http://127.0.0.1:8806',metrics,errors},null,2));await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
