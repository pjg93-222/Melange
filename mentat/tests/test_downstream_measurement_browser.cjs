'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const os=require('node:os');
const modules=process.env.MENTAT_NODE_MODULES||path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules');
const {chromium}=require(require.resolve('playwright',{paths:[modules]}));
const app=path.join(__dirname,'../app');

test('downstream drawer distinguishes observed activity, signed amounts, source differences and coverage',{timeout:60000},async t=>{
  const browser=await chromium.launch({headless:true,channel:process.env.MENTAT_BROWSER_CHANNEL||'chrome'});
  t.after(()=>browser.close());
  const page=await browser.newPage({viewport:{width:1500,height:1100}});
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.route('**/*',route=>route.abort());
  await page.setContent(fs.readFileSync(path.join(app,'index.html'),'utf8').replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi,'').replace(/<link\b[^>]*>/gi,''));
  for(const sheet of ['style.css','graph.css','workspace.css'])await page.addStyleTag({path:path.join(app,sheet)});
  await page.addScriptTag({path:path.join(app,'theme.js')});
  await page.evaluate(()=>{
    window.currentView='graph';window.splitView=false;window.selectedRun='fixture';
    document.querySelector('#view-loading').hidden=true;document.querySelector('#view-graph').hidden=false;
    const body={options:{companies:['Fixture Company'],cycles:['2024'],categories:['Super PAC'],recipients:[{id:'C00000001',label:'Fixture PAC'}]},
      filters:{company:'',cycle:'2024',tier:'',funding:'all',mode:'direct',direction:'Support'},
      totals:{giving:100,direct:0,organizations:100,unresolved_candidate_links:0,recipients:1,receipt_groups:1},
      organizations:[{id:'C00000001',label:'Fixture PAC',amount:100}],
      categories:[{id:'Super PAC',label:'Super PAC',amount:100}],companies:[{id:'Fixture Company',label:'Fixture Company',amount:100}],
      levels:[{id:'Employees',label:'Employees',amount:100}],candidates:[{id:'H00000001',label:'Fixture Candidate',amount:-20}],
      candidate_available:true,candidate_note:'Saved network activity, not dollars attributed to the selected donor. Different sources are not reconciled.',
      note:'Synthetic test data only. Included does not mean verified.',reports:[{name:'Fixture workbook.xlsx',sha256:'a'.repeat(64)}],
      direction_totals:[{direction:'Contribution / Other',candidates:0,amount:0},{direction:'Support',candidates:1,amount:-20},{direction:'Oppose',candidates:0,amount:0},{direction:'Unknown',candidates:0,amount:5,unidentified_amount:5}],
      pac_candidate_relationships:[{candidate:'Fixture Candidate',candidate_id:'H00000001',committee:'C00000002',committee_name:'Downstream Fixture PAC',cycle:'2024',direction:'Support',amount:-20,share_of_pac_direction:null,route:['C00000001','C00000002']}],
      measurement_comparisons:[{committee:'C00000002',cycle:'2024',schedule:'independent_expenditures',workbook_amount:100,snapshot_amount:-20,basis:'Coverage/filing changes are not reconciled.'},
        {committee:'C00000002',cycle:'2024',schedule:'contributions',workbook_amount:null,snapshot_amount:25}],
      downstream_sources:[{committee:'C00000002',cycle:'2024',coverage_start:'2023-01-01',coverage_end:'2024-06-30',sha256:'b'.repeat(64)}]};
    window.api=async url=>url.startsWith('/api/report-sources')?{runs:[{id:'fixture',name:'Offline fixture',state:'completed'}]}:{industries:[{name:'Synthetic'}]};
    body.candidates_by_direction={Support:body.candidates,Oppose:[],Unknown:[{id:'unidentified-candidate',label:'Unidentified candidate',amount:5}], 'Contribution / Other':[]};
    body.downstream_edges=[{source:'C00000001',destination:'C00000002',cycle:'2024',amount:100}];
    window.graphRequests=0;
    window.fetch=async()=>{window.graphRequests++;return {ok:true,json:async()=>body};};
  });
  await page.addScriptTag({path:path.join(app,'graph-explorer.js')});
  await page.addScriptTag({path:path.join(app,'graph.js')});
  await page.waitForSelector('#graph-organizations .graph-bar-button',{state:'attached'});
  await page.locator('#graph-tab-recipients').click();
  await page.locator('#graph-organizations .graph-bar-button').first().click();
  // Paul, 2026-09-23 (board 5): the explorer and its table are attached but
  // collapsed; under the rows only "Expand explorer" shows until it is pressed.
  await page.waitForSelector('#graph-drawer-rows table',{state:'attached'});
  const drawer=page.locator('#graph-drawer-panel');
  assert.equal(await drawer.locator('#graph-drawer-rows table').isVisible(),false,'the explorer starts collapsed');
  assert.equal(await drawer.getByText('Saved snapshot coverage',{exact:true}).isVisible(),false,'its disclosures wait with it');
  assert.equal(await drawer.getByRole('button',{name:'Expand explorer',exact:true}).isVisible(),true);
  // Board 5's note, kept truthful, ends the drawer above Open in PAC evidence.
  assert.match(await page.locator('#graph-drawer-note').textContent(),/^Reported activity of this committee and the PACs it funds, not money attributed to the companies\.$/);
  assert.equal(await drawer.getByRole('button',{name:/Open in PAC evidence/}).isVisible(),true);
  // Board 5's title (build 02 fix round 1, R02-M6; was "Saved downstream PAC activity").
  assert.match(await drawer.textContent(),/Where this PAC’s money went next/);
  assert.match(await drawer.textContent(),/Unavailable/);
  assert.match(await drawer.textContent(),/-\$20/);
  assert.match(await drawer.textContent(),/workbook \$100\.00; selected snapshot -\$20\.00/);
  assert.match(await drawer.textContent(),/not present in saved activity/);
  assert.match(await drawer.textContent(),/Backing is assumed from recorded transfers/);
  assert.match(await drawer.textContent(),/not dollars attributed/);
  assert.match(await drawer.textContent(),/Contributions \/ Other/);
  const unknown=drawer.locator('.graph-drawer-side').filter({hasText:'Unknown'});
  assert.match(await unknown.textContent(),/0 \+ \?/);
  assert.match(await unknown.getAttribute('title'),/\$5\.00 has no candidate identity/);
  const requests=await page.evaluate(()=>window.graphRequests);
  await unknown.click();
  await drawer.locator('.graph-drawer-side').filter({hasText:'Support'}).click();
  assert.equal(await page.evaluate(()=>window.graphRequests),requests,'direction toggles use one saved payload');
  assert.equal(await drawer.locator('tbody tr').count(),1);
  const narrow=(await drawer.boundingBox()).width;
  await drawer.getByRole('button',{name:'Expand explorer',exact:true}).click();
  await page.waitForFunction(()=>document.getElementById('graph-drawer-panel').getBoundingClientRect().width>700);
  assert.ok((await drawer.boundingBox()).width>narrow*1.5);
  assert.match(await drawer.textContent(),/-\$20/);
  // Expanded, the explorer's table and the drawer's disclosures show, and the
  // coverage disclosure opens here (it was pressed before the explorer was
  // collapsed by default).
  assert.equal(await drawer.locator('#graph-drawer-rows table').isVisible(),true);
  await drawer.getByText('Saved snapshot coverage',{exact:true}).click();
  assert.match(await drawer.textContent(),/2023-01-01 to 2024-06-30/);
  assert.equal(await drawer.getByRole('button',{name:'Collapse explorer',exact:true}).getAttribute('aria-expanded'),'true');
  assert.deepEqual(errors,[]);
  if(process.env.MENTAT_MEASUREMENT_SCREENSHOT){
    fs.mkdirSync(path.dirname(process.env.MENTAT_MEASUREMENT_SCREENSHOT),{recursive:true});
    await drawer.screenshot({path:process.env.MENTAT_MEASUREMENT_SCREENSHOT});
  }
});
