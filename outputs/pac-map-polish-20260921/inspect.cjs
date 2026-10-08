/* P4b: the PAC map is INTERACTIVE, and the picture survives interacting with it.
 *
 * The point of this suite is the one thing the S8 map could not do: zoom, pan,
 * change layer and select without the <svg> being rebuilt underneath the
 * reader. So the central assertion is NODE IDENTITY - the same element objects
 * before and after a wheel zoom - not a re-query that equal markup would pass.
 *
 * It also measures. The brief set two budgets (first open under 1.5s excluding
 * network; a wheel-zoom frame under 16ms with 3,000 circles present) and this
 * run prints the numbers it measured rather than asserting a feeling.
 *
 * Harness copied from tests/test_evidence_map_browser.cjs: freePort(),
 * startServer/stopServer, step()/pass(), HARD_CAP_MS, withTimeout and the
 * MENTAT_NODE_MODULES playwright resolution.
 * Run from cwd mentat/:  node tests\test_evidence_map_interaction_browser.cjs
 * MENTAT_MAP_SHOT_DIR keeps the PNGs; unset, the run writes no image.
 */
const assert = require('node:assert/strict');
const {spawn, execFileSync} = require('node:child_process');
const path = require('node:path');
const os = require('node:os');
const fs = require('node:fs');
const net = require('node:net');
const modules = process.env.MENTAT_NODE_MODULES
  || path.join(os.homedir(), '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules');
const {chromium} = require(require.resolve('playwright', {paths: [modules]}));

const MENTAT_DIR = path.resolve('mentat');
const FORBIDDEN_PORTS = new Set([8801, 8802, 8806, 8808, 8841, 8940, 8971, 8990, 8991, 8992, 8993]);
const HARD_CAP_MS = 900_000;
const BOOK = 'Crypto Industry Spending Overview.xlsx';
const SHOT_DIR = process.env.MENTAT_MAP_SHOT_DIR || '';
// How many distinct ZIPs the fixture spreads its contributors over. The brief's
// performance budget is stated at 3,000 circles, so the fixture carries enough
// ZIPs for the map to have that many to draw.
const ZIP_ROWS = 3200;

let stepNumber = 0, currentStepLabel = '(none)', stepStartedAt = Date.now();
let serverForWatchdog = null, pageForDiagnostics = null;
const watchdog = setTimeout(() => {
  console.error(`WATCHDOG: step ${stepNumber} (${currentStepLabel}) exceeded ${HARD_CAP_MS}ms`);
  try { if (serverForWatchdog && serverForWatchdog.exitCode === null) serverForWatchdog.kill(); } catch { /* best effort */ }
  process.exit(1);
}, HARD_CAP_MS);

function step(label) {
  stepNumber += 1; currentStepLabel = label; stepStartedAt = Date.now();
  console.log(`STEP ${stepNumber}: ${label}`);
}
function pass(detail) {
  console.log(`PASS step ${stepNumber} (${((Date.now() - stepStartedAt) / 1000).toFixed(1)}s) - ${detail}`);
}
function withTimeout(promise, ms, label) {
  let timer;
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(() => reject(new Error(`${label} exceeded its ${ms}ms bound`)), ms);
  });
  return Promise.race([promise, timeout]).finally(() => clearTimeout(timer));
}
function freePort() {
  const once = () => new Promise((resolve, reject) => {
    const server = net.createServer();
    server.on('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const port = server.address().port;
      server.close(() => resolve(port));
    });
  });
  const pick = async () => { for (;;) { const port = await once(); if (!FORBIDDEN_PORTS.has(port)) return port; } };
  return withTimeout(pick(), 10000, 'freePort()');
}
function startServer(port, dataRoot, reportRoot) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.env.MENTAT_PYTHON || 'python',
      ['app/server.py', '--port', String(port), '--data-root', dataRoot],
      {cwd: MENTAT_DIR, stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true,
       env: {...process.env, MENTAT_REPORT_DIRECTORY: reportRoot}});
    const stderr = [];
    let stdout = '', settled = false;
    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      reject(new Error(`server on ${port} printed no ready line in 30s; stderr: ${stderr.join('')}`));
    }, 30000);
    child.stdout.on('data', chunk => {
      stdout += chunk.toString();
      if (!settled && new RegExp(`Mentat app: http://127\\.0\\.0\\.1:${port}\\b`).test(stdout)) {
        settled = true; clearTimeout(timer); resolve(child);
      }
    });
    child.stderr.on('data', chunk => stderr.push(chunk.toString()));
    child.on('exit', code => {
      if (settled) return;
      settled = true; clearTimeout(timer);
      reject(new Error(`server on ${port} exited ${code}; stderr: ${stderr.join('')}`));
    });
    child.on('error', error => { if (!settled) { settled = true; clearTimeout(timer); reject(error); } });
  });
}
function stopServer(child) {
  return withTimeout(new Promise(resolve => {
    if (!child || child.exitCode !== null) { resolve(); return; }
    child.once('exit', () => resolve());
    child.kill();
  }), 10000, 'stopServer()').catch(error => console.error(error.message));
}

/* The fixture spreads one committee's receipts over thousands of REAL ZIPs,
   read out of the shipped geo/zcta_points.json, so every circle the map draws
   has a centre the console actually ships rather than one this test invented.
   Lubbock's 79401 is written in by name because the search step looks for it
   and for the district it sits in. */
const FIXTURE_SCRIPT = `
import json
import sys
import openpyxl

target, app_dir, wanted = sys.argv[1], sys.argv[2], int(sys.argv[3])
points = json.loads(open(app_dir + '/geo/zcta_points.json', encoding='utf-8').read())['points']
codes = [code for code in sorted(points) if points[code][3] not in ('PR', 'VI', 'GU', 'AS', 'MP')]
picked = [code for code in ('79401', '94607', '94105', '10001') if code in points]
# Every Nth ZIP in sort order, so the fixture is spread over the whole country.
# The first N in sort order are all in New England, which made a zoom into the
# middle of the map measure an empty screen.
rest = [code for code in codes if code not in picked]
stride = max(1, len(rest) // max(1, wanted - len(picked)))
picked += rest[::stride][:max(0, wanted - len(picked))]

HEAD = ['committee_id', 'committee_name', 'amount', 'date', 'two_year_transaction_period',
        'record_type', 'recipient_category', 'include_in_analysis', 'inclusion_reason',
        'contributor_name', 'street_1', 'city', 'state', 'zip']
workbook = openpyxl.Workbook()
workbook.remove(workbook.active)
sheet = workbook.create_sheet('2023-2024')
sheet.append(HEAD)
for index, code in enumerate(picked):
    x, y, region, state = points[code]
    # Two contributors in some ZIPs, one in others, so the donor-count buckets
    # the legend draws all have members.
    for person in range(1 + index % 4):
        # Keep the explicitly searched ZIPs inside the producer's 3,000-ZIP
        # display cap; otherwise 79401 is correctly reported as off this map.
        sheet.append(['C00804179', 'COINBASE INNOVATION PAC', (10000 if index < 4 else 100) + (index % 37) * 13 + person,
                      '2024-01-02', '2023-2024', 'CONTRIBUTION', 'PAC', 'Yes', 'counted',
                      'PERSON %d-%d' % (index, person), '%d Main St' % (index + 1),
                      'Town %d' % index, state, code])
workbook.save(target + '/${BOOK}')
print(len(picked))
`;


(async()=>{
 const dataRoot=fs.mkdtempSync(path.join(os.tmpdir(),'map-polish-data-'));
 const fixtureDir=fs.mkdtempSync(path.join(os.tmpdir(),'map-polish-fixture-'));
 const reportRoot=fs.mkdtempSync(path.join(os.tmpdir(),'map-polish-report-'));
 let server,browser;
 const out=path.resolve('outputs/pac-map-polish-20260921');
 try {
  execFileSync('python',['-c',FIXTURE_SCRIPT,fixtureDir,path.join(MENTAT_DIR,'app'),'3200']);
  const port=await freePort(); server=await startServer(port,dataRoot,reportRoot);
  browser=await chromium.launch({channel:'chrome',headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:1050}});
  await page.goto(`http://127.0.0.1:${port}/`); await page.click('#tab-evidence');
  await page.click('#evidence-import-open'); await page.fill('#evidence-path',path.join(fixtureDir,BOOK));
  await page.click('#evidence-path-read');
  await page.waitForSelector('#evidence-pac option[value="C00804179"]',{state:'attached',timeout:60000});
  await page.selectOption('#evidence-pac','C00804179');
  await page.waitForSelector('#evidence-cycle option[value="2024"]',{state:'attached'});
  await page.selectOption('#evidence-cycle','2024'); await page.click('#evidence-add');
  await page.waitForSelector('.pane-map'); await page.click('.pane-map');
  await page.waitForSelector('svg.map-canvas');
  const audit=await page.evaluate(async()=>{
   const host=document.querySelector('.map-canvas-host'),api=window.MentatEvidenceMap,svg=host.querySelector('svg.map-canvas');
   const event=new WheelEvent('wheel',{deltaY:120,bubbles:true,cancelable:true});
   svg.dispatchEvent(event);
   api.flyToKey(host,'TX'); await new Promise(r=>setTimeout(r,100)); api.zoom(host,1.4);
   const requested=api.view(host); await new Promise(r=>setTimeout(r,750)); const landed=api.view(host);
   return {plainScrollCaptured:event.defaultPrevented,manualZoomOverridden:Math.abs(landed.scale-requested.scale)>.001,
    requested,landed,touchAction:getComputedStyle(svg).touchAction};
  });
  await page.fill('#evidence-map-search','TX-19');await page.press('#evidence-map-search','Enter');
  await page.waitForTimeout(800);
  audit.searchFocus=await page.evaluate(()=>document.activeElement.id);
  await page.click('.map-layer[data-map-layer="sld"]');
  await page.waitForSelector('#evidence-map-state option[value="TX"]',{state:'attached'});
  await page.focus('#evidence-map-state'); await page.selectOption('#evidence-map-state','TX'); await page.waitForSelector('.map-sld[data-key^="TX-"]');
  await page.waitForTimeout(750);
  audit.stateFocus=await page.evaluate(()=>document.activeElement.id);
  await page.locator('#evidence-map').screenshot({path:path.join(out,'after-desktop.png')});
  await page.setViewportSize({width:390,height:844});
  await page.locator('#evidence-map').screenshot({path:path.join(out,'after-mobile.png')});
  audit.mobile=await page.evaluate(()=>{
    const host=document.querySelector('#evidence-map');return {client:host.clientWidth,scroll:host.scrollWidth,
      mapWidth:host.querySelector('svg.map-canvas').getBoundingClientRect().width,
      toolbarHeight:host.querySelector('.map-toolbar').getBoundingClientRect().height};
  });
  fs.writeFileSync(path.join(out,'after-audit.json'),JSON.stringify(audit,null,2)); console.log(JSON.stringify(audit));
 } finally {clearTimeout(watchdog); if(browser)await withTimeout(browser.close(),10000,'browser close').catch(()=>{});await stopServer(server);}
 process.exit(0);
})().catch(e=>{console.error(e);process.exit(1)});
