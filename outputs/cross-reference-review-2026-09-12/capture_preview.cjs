'use strict';

// Run after the saved reconciliation finishes. This only reads the preview.
const assert = require('node:assert/strict');
const path = require('node:path');
const os = require('node:os');
const fs = require('node:fs/promises');
const moduleRoot = process.env.MENTAT_NODE_MODULES || path.join(
  os.homedir(), '.cache', 'codex-runtimes', 'codex-primary-runtime',
  'dependencies', 'node', 'node_modules'
);
const {chromium, request} = require(require.resolve('playwright', {paths:[moduleRoot]}));
const origin = process.env.MENTAT_PREVIEW_ORIGIN || 'http://127.0.0.1:56312';
const outputDirectory = __dirname;

function assertCompleted(snapshot) {
  assert.equal(snapshot.available, true, 'Saved cross-reference evidence must be available.');
  assert.equal(snapshot.status, 'completed', 'Run the capture after the reconciliation completes.');
  assert.equal(snapshot.report?.status, 'completed');
  const summary = snapshot.report.summary;
  for (const key of ['input_records', 'automatic_decisions', 'unresolved_records',
    'source_verified_records', 'classified_from_stored_records', 'coverage_records',
    'coverage_only_records']) {
    assert.ok(Object.hasOwn(summary, key), `Updated adapter must expose ${key}.`);
    assert.ok(Number.isInteger(summary[key]) && summary[key] >= 0, `${key} must be a nonnegative count.`);
  }
  assert.ok(Object.hasOwn(summary, 'coverage_amount'));
  assert.ok(typeof summary.coverage_amount === 'number' && Number.isFinite(summary.coverage_amount));
  assert.ok(Array.isArray(snapshot.report.coverage_reasons), 'Updated adapter must expose grouped coverage reasons.');
  return summary;
}

async function assertNoOverflow(page, size) {
  const dimensions = await page.evaluate(() => {
    const pane = document.getElementById('view-cross-reference');
    return {
      documentWidth: document.documentElement.scrollWidth,
      viewportWidth: document.documentElement.clientWidth,
      paneWidth: pane.clientWidth,
      paneScrollWidth: pane.scrollWidth,
    };
  });
  assert.ok(dimensions.documentWidth <= dimensions.viewportWidth,
    `${size}: page overflows horizontally: ${JSON.stringify(dimensions)}`);
  assert.ok(dimensions.paneScrollWidth <= dimensions.paneWidth,
    `${size}: cross-reference pane overflows horizontally: ${JSON.stringify(dimensions)}`);
  return dimensions;
}

(async () => {
  const api = await request.newContext({baseURL:origin, timeout:30000});
  let browser;
  try {
    const healthResponse = await api.get('/api/health');
    assert.ok(healthResponse.ok(), 'Read-only preview must be running on port 8813.');
    assert.equal((await healthResponse.json()).read_only, true, 'Capture is restricted to the read-only preview.');
    const response = await api.get('/api/cross-reference');
    assert.ok(response.ok());
    const snapshot = await response.json();
    const summary = assertCompleted(snapshot);

    browser = await chromium.launch({headless:true, channel:process.env.MENTAT_BROWSER_CHANNEL || 'chrome'});
    const page = await browser.newPage({viewport:{width:1440,height:1100}, deviceScaleFactor:1});
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(origin + '/#cross-reference', {waitUntil:'domcontentloaded'});
    await page.getByText('Source-verified receipts', {exact:true}).waitFor();
    await page.getByRole('heading', {name:'Collection coverage follow-up',exact:true}).waitFor();
    await page.getByText('Classified from stored evidence', {exact:true}).waitFor();
    assert.equal(await page.locator('#tab-cross-reference').getAttribute('aria-selected'), 'true');
    assert.match(await page.locator('#xref-results').innerText(), new RegExp(snapshot.run_id));
    await page.evaluate(() => document.fonts.ready);

    const desktopDimensions = await assertNoOverflow(page, 'Desktop');
    const desktop = path.join(outputDirectory, 'cross-reference-desktop.png');
    await page.screenshot({path:desktop, fullPage:true});
    await page.setViewportSize({width:390,height:844});
    const mobileDimensions = await assertNoOverflow(page, 'Mobile');
    const mobile = path.join(outputDirectory, 'cross-reference-mobile.png');
    await page.screenshot({path:mobile, fullPage:true});

    const finalResponse = await api.get('/api/cross-reference');
    assert.ok(finalResponse.ok());
    const finalSnapshot = await finalResponse.json();
    assertCompleted(finalSnapshot);
    assert.equal(finalSnapshot.run_id, snapshot.run_id, 'Saved report changed during capture; rerun for one consistent snapshot.');
    assert.deepEqual(errors, [], 'The preview must not produce uncaught JavaScript errors.');
    const receipt = {
      captured_at:new Date().toISOString(), url:origin + '/#cross-reference',
      run_id:snapshot.run_id, summary, desktop, mobile,
      desktop_dimensions:desktopDimensions, mobile_dimensions:mobileDimensions, javascript_errors:errors,
    };
    await fs.writeFile(path.join(outputDirectory, 'preview-qa.json'), JSON.stringify(receipt,null,2) + '\n');
    console.log(JSON.stringify(receipt,null,2));
  } finally {
    if (browser) await browser.close();
    await api.dispose();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
