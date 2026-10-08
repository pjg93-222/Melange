/* Run with MENTAT_NODE_MODULES pointing to a local Playwright installation. */
const assert = require('node:assert/strict');
const {spawn} = require('node:child_process');
const path = require('node:path');
const os = require('node:os');
const fs = require('node:fs');
const {once} = require('node:events');
const modules = process.env.MENTAT_NODE_MODULES || path.join(os.homedir(), '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules');
const {chromium} = require(require.resolve('playwright', {paths:[modules]}));
(async () => {
  const trace=message=>{if(process.env.MENTAT_BROWSER_TRACE)console.log(`[browser] ${message}`);};
  const fixture = spawn(process.env.MENTAT_PYTHON || 'python', [path.resolve('mentat/tests/console_browser_fixture.py')], {stdio:['pipe','pipe','pipe'],windowsHide:true});
  trace(`Starting test ${process.pid}; temporary fixture ${fixture.pid}.`);
  let browser;
  const stderr=[]; fixture.stderr.on('data', chunk=>stderr.push(chunk.toString()));
  try {
    const origin = await new Promise((resolve,reject)=>{
      let output='';
      fixture.stdout.on('data',chunk=>{output+=chunk; if(output.includes('\n'))resolve(output.trim().split('\n')[0]);});
      fixture.on('exit',code=>reject(new Error(`Fixture exited ${code}: ${stderr.join('')}`)));
      fixture.on('error',reject);
    });
    browser = await chromium.launch({headless:true,channel:process.env.MENTAT_BROWSER_CHANNEL || 'chrome'});
    const page = await browser.newPage({viewport:{width:1440,height:1050}});
    page.setDefaultTimeout(15000);
    async function captureScreenshot(file,fullPage=true) {
      if(!file)return;
      await page.evaluate(()=>{document.activeElement?.blur();window.scrollTo(0,0);});
      await page.screenshot({path:file,fullPage});
    }
    const errors=[],remote=[];
    page.on('pageerror',e=>errors.push(e.message));
    page.on('request',request=>{if(!request.url().startsWith(origin) && !request.url().startsWith('blob:'))remote.push(request.url());});
    const savedEvidence={version:1,company:'Harborlight Credit Union',aliases:['HARBORLIGHT CU'],retrieved_at:'2026-09-10T00:00:00Z',scope:'Fixture evidence',
      committee_finances:[{cycle:2024,committee_id:'C00000001',committee_name:'First PAC'},{cycle:2026,committee_id:'C00000002',committee_name:'Second PAC'}],
      receipts:[],transfers:[],candidate_activity:[],temporal_routes:[]};
    const crossReference={available:true,status:'completed',run_id:'fictional-browser-fixture',report:{
      generated_at:'2026-09-10T00:00:00Z',scope:{industries:['Fictional credit union sample'],companies:[savedEvidence.company],cycles:[2024],source_count:1},
      summary:{input_records:5,automatic_decisions:2,unresolved_records:1,unresolved_amount:40,observed_original_giving:100,
        employee_giving:100,pac_outgoing:60,baseline_amount:160,amount_change:-60,verified_unique:false},
      steps:[{id:'collect',status:'completed'},{id:'connect',status:'review',detail:'Missing counterpart'}],
      unresolved_reasons:[{reason:'Reference missing',records:1,amount:40}],
      review_queue:[{company:savedEvidence.company,reason:'Reference missing',cycle:2024,amount:40,record_id:'fixture-123'}],
      changes:[{company:savedEvidence.company,reason:'Linked outgoing stage',cycle:2024,before:160,after:100,delta:-60,record_id:'fixture-456'}],
      limitations:['Fictional fixture only. Collection coverage remains unverified.'],
    }};
    let extraSnapshot=false;
    await page.route('**/api/evidence?*',route=>route.fulfill({json:savedEvidence}));
    await page.route('**/api/evidence',route=>route.fulfill({json:{snapshots:[{id:'fixture-evidence',company:savedEvidence.company,cycles:[2024,2026],retrieved_at:savedEvidence.retrieved_at},...(extraSnapshot?[{id:'new-evidence',company:'Another Company',cycles:[2026]}]:[])]}}));
    await page.route('**/api/cross-reference?*',route=>route.fulfill({json:crossReference}));
    await page.route('**/api/cross-reference',route=>route.fulfill({json:crossReference}));

    const phase=process.env.UI_PHASE||'before',out=path.resolve('outputs/tabs-polish-20260921');
    fs.mkdirSync(out,{recursive:true});
    await page.route('**/api/insights/catalog',route=>route.fulfill({json:{datasets:[{id:'Synthetic',label:'Fictional credit union sample',available:true}],panels:[]}}));
    await page.route('**/api/insights/query',route=>{
      const q=route.request().postDataJSON(),panels={};
      for(const id of q.panels||[]) panels[id]={status:'ready',title:({favorites:'Favorite recipients',trends:'Giving over time',changes:'Changes in giving'})[id]||id,summary:'Synthetic records for interface testing.',columns:[{key:'recipient',label:'Recipient',type:'text'},{key:'amount_cents',label:'Amount',type:'money'}],rows:[{recipient:'Harborlight PAC',amount_cents:125000,filters:[{field:'committee_id',op:'eq',value:'C00000001'}]},{recipient:'Civic Horizon PAC',amount_cents:50000}],notices:[]};
      return route.fulfill({json:{status:'ready',scope:{...q,basis_label:'Reported receipts',as_of:'2026-09-01',baseline_cycle:'2023-2024',current_cycle:'2025-2026'},panels,options:{companies:['Harborlight Credit Union'],funding_sources:['employee_original'],cycles:['2023-2024','2025-2026']},provenance:{workbook:'Synthetic UI workbook.xlsx',index_token:'ui-fixture'},notices:['Synthetic fixture. Coverage is incomplete.']}});
    });
    await page.goto(origin+'/');
    const audit=[];
    async function capture(tab){
      for(const width of [1440,390]){
        await page.setViewportSize({width,height:width===1440?1050:844});
        await page.evaluate(()=>{document.activeElement?.blur();window.scrollTo(0,0)});
        await page.screenshot({path:path.join(out,`${phase}-${tab}-${width}.png`),fullPage:true});
        audit.push(await page.evaluate(({tab,width})=>{
          const visible=el=>el.getBoundingClientRect().width>0&&el.getBoundingClientRect().height>0;
          return {tab,width,scroll:document.documentElement.scrollWidth,controls:[...document.querySelectorAll(`#view-${tab} button,#view-${tab} select,#view-${tab} input, #view-${tab} summary`)].filter(visible).map(el=>({id:el.id,label:(el.getAttribute('aria-label')||el.textContent||el.placeholder||'').slice(0,65),height:Math.round(el.getBoundingClientRect().height)}))};
        },{tab,width}));
      }
      await page.setViewportSize({width:1440,height:1050});
    }
    await page.waitForFunction(()=>document.querySelector('#loading-coverage').textContent.includes('Stale coverage'));
    if(!process.env.REMAINING_ONLY)await capture('loading');
    await page.click('#tab-collection'); await page.click('[data-run-group=history]'); await page.waitForSelector('#monitor:not([hidden])');
    if(!process.env.REMAINING_ONLY)await capture('collection');
    await page.click('#tab-graph');await page.waitForSelector('#graph-results:not([hidden])');if(!process.env.REMAINING_ONLY)await capture('graph');
    await page.click('#tab-chart-studio');
    await page.selectOption('#studio-source-mode','worksheet');
    await page.waitForFunction(()=>document.querySelectorAll('#studio-dimensions .studio-pill').length>0);
    await capture('chart-studio');
    await page.click('#tab-insights'); await page.waitForSelector('#insights-results article');await capture('insights');
    await page.click('#tab-cross-reference');await page.waitForSelector('#xref-results h2');await capture('cross-reference');
    fs.writeFileSync(path.join(out,`${phase}-audit.json`),JSON.stringify({audit,errors},null,2));
    console.log(JSON.stringify({phase,views:audit.map(({tab,width,scroll})=>({tab,width,scroll})),errors}));
  } finally {
    if(browser)await Promise.race([browser.close(),new Promise(resolve=>setTimeout(resolve,10000))]);
    fixture.stdin.end('\n');
    setTimeout(()=>fixture.kill(),3000).unref();
  }
  process.exit(0);
})().catch(e=>{console.error(e);process.exit(1)});
