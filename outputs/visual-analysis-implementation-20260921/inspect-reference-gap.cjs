const fs=require('fs'),path=require('path'),os=require('os');
const {chromium}=require(require.resolve('playwright',{paths:[path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules')]}));
(async()=>{const browser=await chromium.launch({channel:'chrome',headless:true});const page=await browser.newPage({viewport:{width:1440,height:1000}});let body;
page.on('response',async r=>{if(r.url().includes('/api/graph?'))try{body=await r.json();}catch{}});
await page.goto('http://127.0.0.1:8806/?industry=Credit%20Union#graph');await page.locator('#graph-results').waitFor({state:'visible',timeout:120000});
console.log(JSON.stringify({keys:Object.keys(body||{}),arrays:Object.fromEntries(Object.entries(body||{}).filter(([,v])=>Array.isArray(v)).map(([k,v])=>[k,{count:v.length,first:v[0]}]))},null,2));
console.log(await page.evaluate(()=>Object.fromEntries(['body','.wordmark','.workspace-tabs button','.graph-panel h2','.graph-bars','.analysis-strip'].map(s=>{const e=document.querySelector(s),c=getComputedStyle(e),r=e.getBoundingClientRect();return[s,{font:c.font,width:r.width,height:r.height,y:r.y}]}))));await browser.close();})();
