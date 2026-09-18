/* S8 PAC evidence district map, real-client pass: a pane's Map button opens
 * the district heatmap, Raised vs Spent, the ranked list, the reconciliation
 * line, a layer chip, a district tooltip, clicking a district to filter that
 * pane's rows, Back to panes, and the URL round trip that reopens the same
 * map from a permalink.
 *
 * Spawns the actual `python app/server.py` console under a temp data root, so
 * the import really lands on disk and the permalink really restores from it.
 * Run with MENTAT_NODE_MODULES pointing at a local Playwright installation,
 * from cwd mentat/:  node tests\test_evidence_map_browser.cjs
 *
 * Every wait is bounded and a top-level watchdog names the step it was on.
 * Harness copied from tests/test_evidence_panes_browser.cjs (S6): freePort(),
 * startServer/stopServer, step()/pass(), HARD_CAP_MS, withTimeout, the
 * MENTAT_NODE_MODULES playwright resolution and a temp data root.
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

const MENTAT_DIR = path.resolve(__dirname, '..');
// Paul's consoles and the ports other lanes reserve. A scratch console never
// lands on one of these.
const FORBIDDEN_PORTS = new Set([8802, 8806, 8808, 8841, 8940, 8971, 8990, 8991, 8992, 8993]);
const HARD_CAP_MS = 900_000;
const CRYPTO_BOOK = 'Crypto Industry Spending Overview.xlsx';
const RECEIPTS_DIR = path.resolve(MENTAT_DIR, '..', 'audits', 'mentat_failings_20260915', 'receipts');
const SCREENSHOT_PATH = path.join(RECEIPTS_DIR, 'S8_after_screenshot.png');

let stepNumber = 0, currentStepLabel = '(none)', stepStartedAt = Date.now();
let serverForWatchdog = null;
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

function startServer(port, dataRoot) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.env.MENTAT_PYTHON || 'python',
      ['app/server.py', '--port', String(port), '--data-root', dataRoot],
      {cwd: MENTAT_DIR, stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true});
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

// One industry-workbook fixture, built the same way the S6 fixture is
// (openpyxl, HEAD row, two_year_transaction_period decides the sheet), plus a
// State and a ZIP column so evidence_geo.py's STATE_FIELDS/ZIP_FIELDS lookup
// has contributor geography to place on the map. Real 2023-2024 (118th) ZIP
// crosswalk facts used below (checked against app/geo/zcta_cd118.json):
// 94607 (Oakland) -> CA-12 at 100% share, 94105 (SF) -> CA-11 at 100% share.
const FIXTURE_SCRIPT = `
import sys
import openpyxl

target = sys.argv[1]
HEAD = ['committee_id', 'committee_name', 'amount', 'date', 'two_year_transaction_period',
        'record_type', 'recipient_category', 'include_in_analysis', 'inclusion_reason',
        'contributor_name', 'state', 'zip']

def book(rows, name, sheets=('2023-2024', '2025-2026')):
    workbook = openpyxl.Workbook()
    workbook.remove(workbook.active)
    for sheet_name in sheets:
        sheet = workbook.create_sheet(sheet_name)
        sheet.append(HEAD)
        for row in rows:
            if row[4] in sheet_name:
                sheet.append(list(row))
    workbook.save(target + '/' + name)

CRYPTO = [
    ('C00804179', 'COINBASE INNOVATION PAC', 383197, '2024-05-05', '2024', 'CONTRIBUTION', 'Company PAC', 'Yes', '', 'CHOI, EMILIE', 'CA', '94607'),
    ('C00804179', 'COINBASE INNOVATION PAC', 18884, '2024-05-06', '2024', 'CONTRIBUTION', 'Company PAC', 'Yes', '', 'POLLAK, JESSE', 'CA', '94105'),
    ('C00804179', 'COINBASE INNOVATION PAC', 5000, '2024-05-07', '2024', 'CONTRIBUTION', 'Company PAC', 'Yes', '', 'NO ZIP PERSON', 'NY', ''),
    ('C00804179', 'COINBASE INNOVATION PAC', 1000, '2026-01-05', '2026', 'CONTRIBUTION', 'Company PAC', 'Yes', '', 'LATER PERSON', 'CA', '94607'),
]
book(CRYPTO, '${CRYPTO_BOOK}')
`;

(async () => {
  let browser = null, server = null, failed = false;
  const dataRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'mentat-s8-data-'));
  const fixtureDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mentat-s8-fixtures-'));
  try {
    step('build one industry workbook fixture with contributor ZIP and state');
    execFileSync(process.env.MENTAT_PYTHON || 'python', ['-c', FIXTURE_SCRIPT, fixtureDir],
      {cwd: MENTAT_DIR, stdio: 'pipe'});
    assert.ok(fs.existsSync(path.join(fixtureDir, CRYPTO_BOOK)));
    pass(`fixture written under ${fixtureDir}`);

    step('launch a scratch console on a free port with a temp data root');
    const port = await freePort();
    server = await startServer(port, dataRoot);
    serverForWatchdog = server;
    const origin = `http://127.0.0.1:${port}`;
    pass(`console ready on ${port}, data root ${dataRoot}`);

    step('launch headless Chrome and open the PAC evidence tab');
    browser = await withTimeout(chromium.launch({headless: true,
      channel: process.env.MENTAT_BROWSER_CHANNEL || 'chrome', timeout: 30000}), 35000, 'chromium.launch()');
    const page = await browser.newPage({viewport: {width: 1600, height: 1200}});
    page.setDefaultTimeout(20000);
    const errors = [], consoleErrors = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => { if (message.type() === 'error') consoleErrors.push(message.text()); });
    const status = async () => (await page.textContent('#evidence-status')).trim();
    // Polled with evaluate() rather than waitForFunction(), matching S6: a
    // raf-polled predicate did not resolve reliably on this host.
    const until = async (predicate, timeout, what) => {
      const deadline = Date.now() + timeout;
      for (;;) {
        if (await page.evaluate(predicate.fn, predicate.arg)) return;
        if (Date.now() > deadline) {
          const seen = await page.textContent('#evidence-status').catch(() => '<unreadable>');
          throw new Error(`${what} did not happen within ${timeout}ms; `
            + `#evidence-status was ${JSON.stringify((seen || '').trim())}`);
        }
        await new Promise(resolve => setTimeout(resolve, 200));
      }
    };
    const waitStatus = (pattern, timeout = 60000) => until(
      {fn: source => new RegExp(source).test(((document.getElementById('evidence-status') || {}).textContent || '').trim()),
       arg: pattern.source}, timeout, `status matching ${pattern}`);
    const waitPanes = (count, timeout = 60000) => until(
      {fn: wanted => document.querySelectorAll('#evidence-panes [data-pane]').length === wanted
        && document.querySelectorAll('#evidence-panes .pane-message').length === 0,
       arg: count}, timeout, `${count} loaded pane(s)`);
    const waitFor = (fn, arg, timeout, what) => until({fn, arg}, timeout, what);
    const openDrawer = async id => {
      const drawer = id === 'evidence-import-open' ? 'evidence-import-drawer' : 'evidence-snapshot-drawer';
      if (await page.isVisible('#' + drawer)) return;
      await page.click('#' + id);
      await page.waitForSelector('#' + drawer + ':not([hidden])');
    };

    await page.goto(origin + '/');
    await page.click('#tab-evidence');
    await waitStatus(/Nothing imported yet|snapshot/);
    pass('evidence tab open');

    step('import the Crypto fixture through the path box');
    await openDrawer('evidence-import-open');
    await page.fill('#evidence-path', path.join(fixtureDir, CRYPTO_BOOK));
    await page.click('#evidence-path-read');
    await waitStatus(/Crypto|PACs in file/, 180000);
    pass(`imported: ${JSON.stringify(await status())}`);

    step('choose the PAC and cycle 2024 in the scope bar, and add the pane');
    await waitFor(() => document.querySelectorAll('#evidence-pac option').length >= 1, null, 20000, 'a page condition');
    await page.selectOption('#evidence-pac', 'C00804179');
    await waitFor(() => [...document.querySelectorAll('#evidence-cycle option')].some(option => option.value === '2024'),
      null, 20000, 'a page condition');
    await page.selectOption('#evidence-cycle', '2024');
    await waitFor(() => !document.getElementById('evidence-add').disabled, null, 20000, 'a page condition');
    await page.click('#evidence-add');
    await waitPanes(1);
    const paneSel = '#evidence-panes [data-pane=a]';
    assert.equal((await page.textContent(`${paneSel} h2`)).trim(), 'COINBASE INNOVATION PAC');
    pass('pane A open for COINBASE INNOVATION PAC, cycle 2024');

    step('the pane header carries a visible .pane-map button labelled Map');
    assert.equal(await page.locator(`${paneSel} .pane-map`).count(), 1);
    assert.equal(await page.isVisible(`${paneSel} .pane-map`), true);
    assert.equal((await page.textContent(`${paneSel} .pane-map`)).trim(), 'Map');
    pass('.pane-map exists, is visible, and reads "Map"');

    step('clicking Map hides the pane grid and shows the map view');
    await page.click(`${paneSel} .pane-map`);
    await page.waitForSelector('#evidence-map:not([hidden])');
    assert.equal(await page.isVisible('#evidence-panes'), false, '#evidence-panes should hide once the map opens');
    assert.equal(await page.isVisible('#evidence-map'), true, '#evidence-map should show once opened');
    pass('#evidence-panes hidden, #evidence-map shown');

    step('the map header carries the two direction buttons, the cycle select and Back');
    assert.equal(await page.locator('#evidence-map .map-direction').count(), 2);
    const directionTexts = await page.locator('#evidence-map .map-direction').allTextContents();
    assert.ok(directionTexts.some(text => /Raised/.test(text) && /where it came from/.test(text)), JSON.stringify(directionTexts));
    assert.ok(directionTexts.some(text => /Spent/.test(text) && /where it went/.test(text)), JSON.stringify(directionTexts));
    assert.equal(await page.locator('#evidence-map-cycle').count(), 1);
    assert.equal(await page.locator('#evidence-map-back').count(), 1);
    pass(`direction buttons ${JSON.stringify(directionTexts)}`);

    step('click Raised: the heatmap paints and the ranked list carries CA-12');
    await page.click('#evidence-map .map-direction[data-direction="raised"]');
    await page.waitForSelector('#evidence-map .map-canvas svg, #evidence-map svg.map-canvas', {timeout: 30000});
    await page.waitForSelector('#evidence-map .map-list', {timeout: 30000});
    await waitFor(() => document.querySelectorAll('#evidence-map path.map-district').length > 0,
      null, 20000, 'district paths to render');
    const painted = await page.evaluate(() => [...document.querySelectorAll('#evidence-map path.map-district')]
      .some(node => {
        const fill = getComputedStyle(node).fill;
        return !!fill && fill !== 'none' && fill !== 'transparent' && fill !== 'rgba(0, 0, 0, 0)';
      }));
    assert.ok(painted, 'no path.map-district has a painted computed fill');
    const listText = await page.textContent('#evidence-map .map-list');
    assert.ok(/CA-12/.test(listText), listText);
    pass('at least one district is painted; CA-12 is present in the ranked list');

    step('the reconciliation line names the located and reported totals');
    const reconcileText = (await page.textContent('#evidence-map .map-reconcile')).trim();
    assert.ok(reconcileText.length > 0, 'empty .map-reconcile');
    assert.ok(/located/.test(reconcileText), reconcileText);
    assert.ok(/reported/.test(reconcileText), reconcileText);
    pass(`reconcile: ${JSON.stringify(reconcileText)}`);

    step('toggling a layer chip flips aria-pressed and the off class, both ways');
    const layerSel = '#evidence-map .layer';
    assert.equal(await page.locator(layerSel).count(), 1, 'expected exactly one layer chip (kind=contributors)');
    const layerClasses = async () => ((await page.getAttribute(layerSel, 'class')) || '').split(/\s+/).filter(Boolean);
    const pressedBefore = await page.getAttribute(layerSel, 'aria-pressed');
    assert.equal(pressedBefore, 'true', `expected the layer chip to start pressed(on): ${pressedBefore}`);
    assert.equal((await layerClasses()).includes('off'), false, 'expected the layer chip to start without the off class');
    await page.click(layerSel);
    await waitFor(previous => document.querySelector('#evidence-map .layer').getAttribute('aria-pressed') !== previous,
      pressedBefore, 20000, 'the layer chip aria-pressed to flip off');
    const pressedAfter = await page.getAttribute(layerSel, 'aria-pressed');
    assert.equal(pressedAfter, 'false', `aria-pressed did not flip to false: ${pressedAfter}`);
    assert.equal((await layerClasses()).includes('off'), true, 'off class was not added');
    pass(`layer toggled off: aria-pressed ${pressedBefore} -> ${pressedAfter}`);
    // Restore it before reading the tooltip and clicking a district: toggling
    // the only kind off drops it from the heat entirely (heatFrom skips
    // kinds that are off), which would blank CA-12's tooltip below.
    await page.click(layerSel);
    await waitFor(previous => document.querySelector('#evidence-map .layer').getAttribute('aria-pressed') !== previous,
      pressedAfter, 20000, 'the layer chip aria-pressed to flip back on');
    const pressedRestored = await page.getAttribute(layerSel, 'aria-pressed');
    assert.equal(pressedRestored, 'true', `aria-pressed did not flip back to true: ${pressedRestored}`);
    assert.equal((await layerClasses()).includes('off'), false, 'off class was not removed on restore');
    pass('layer chip restored to on');

    step('a CA-12 tooltip names the district and a dollar amount');
    const title = await page.evaluate(() => {
      const node = document.querySelector('#evidence-map path.map-district[data-key="CA-12"]');
      const titleNode = node ? node.querySelector('title') : null;
      return titleNode ? titleNode.textContent : null;
    });
    assert.ok(title, 'no <title> child on path.map-district[data-key="CA-12"]');
    assert.ok(/CA-12/.test(title), title);
    assert.ok(/\$[\d,]+/.test(title), title);
    pass(`tooltip: ${JSON.stringify(title)}`);

    step('click the CA-12 district path: it gains class "chosen"');
    // Dispatched rather than Playwright's geometric click: the app reads the
    // event only through delegation (`event.target.closest('[data-district]')`
    // on #evidence-map), so a real bubbling click on the exact node exercises
    // the same handler without depending on where an irregular polygon's
    // bounding-box centre happens to fall.
    await page.evaluate(() => {
      const node = document.querySelector('#evidence-map path.map-district[data-key="CA-12"]');
      if (!node) throw new Error('no path.map-district[data-key="CA-12"] found to click');
      node.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}));
    });
    await waitFor(() => {
      const node = document.querySelector('#evidence-map .map-canvas [data-district="CA-12"]');
      return !!node && node.classList.contains('chosen');
    }, null, 20000, 'the CA-12 district path to gain class "chosen"');
    pass('CA-12 district path carries class "chosen"');

    step('Back to panes: the map closes and the pane shows the CA-12 district filter');
    await page.click('#evidence-map-back');
    await page.waitForSelector('#evidence-panes:not([hidden])', {timeout: 20000});
    assert.equal(await page.isVisible('#evidence-map'), false, '#evidence-map should be hidden after Back to panes');
    assert.equal(await page.isVisible('#evidence-panes'), true, '#evidence-panes should be visible after Back to panes');
    await page.waitForSelector(`${paneSel} .pane-district-filter`, {timeout: 20000});
    const filterText = (await page.textContent(`${paneSel} .pane-district-filter`)).trim();
    assert.ok(/CA-12/.test(filterText), filterText);
    pass(`district filter reads ${JSON.stringify(filterText)}`);

    step('URL round trip: a.map=raised restores the map after a fresh navigation');
    await page.click(`${paneSel} .pane-map`);
    await page.waitForSelector('#evidence-map:not([hidden])', {timeout: 20000});
    const mapUrl = page.url();
    // a.map is written last among the pane's own keys, so in practice it is
    // followed by the #hash, not another &pair; accept either terminator (and
    // end-of-string, in case a future key is ever appended after it).
    assert.ok(/[?&]a\.map=raised(&|#|$)/.test(mapUrl), mapUrl);
    await page.goto(mapUrl);
    await page.waitForSelector('#evidence-map:not([hidden])', {timeout: 60000});
    assert.equal(await page.isVisible('#evidence-map'), true, '#evidence-map should be visible after reload from the permalink');
    assert.equal(await page.isVisible('#evidence-panes'), false, '#evidence-panes should stay hidden while the map view is restored');
    const raisedPressedAfterReload = await page.getAttribute(
      '#evidence-map .map-direction[data-direction="raised"]', 'aria-pressed');
    assert.equal(raisedPressedAfterReload, 'true', `direction was not restored as raised: ${raisedPressedAfterReload}`);
    pass(`permalink ${mapUrl} restored the map in the raised direction`);

    step('screenshot the map at 1440x900');
    fs.mkdirSync(RECEIPTS_DIR, {recursive: true});
    await page.setViewportSize({width: 1440, height: 900});
    await page.waitForSelector('#evidence-map svg.map-canvas', {timeout: 20000});
    await page.screenshot({path: SCREENSHOT_PATH});
    assert.ok(fs.existsSync(SCREENSHOT_PATH), SCREENSHOT_PATH);
    pass(`screenshot saved to ${SCREENSHOT_PATH} (${fs.statSync(SCREENSHOT_PATH).size} bytes)`);

    step('final check: zero pageerror entries and zero console error entries');
    assert.deepEqual(errors, [], `page errors: ${JSON.stringify(errors)}`);
    assert.deepEqual(consoleErrors, [], `console errors: ${JSON.stringify(consoleErrors)}`);
    pass('no page errors, no console errors across every step');

    console.log(`ALL ${stepNumber} STEPS PASSED`);
  } catch (error) {
    failed = true;
    console.error(`FAILED at step ${stepNumber} (${currentStepLabel}): ${error.stack || error.message}`);
  } finally {
    clearTimeout(watchdog);
    if (browser) await browser.close().catch(() => {});
    await stopServer(server);
    for (const target of [dataRoot, fixtureDir]) {
      try { fs.rmSync(target, {recursive: true, force: true, maxRetries: 10, retryDelay: 200}); }
      catch (error) { console.error(`cleanup failed for ${target}: ${error.message}`); }
    }
    process.exit(failed ? 1 : 0);
  }
})();
