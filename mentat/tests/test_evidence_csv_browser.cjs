/* Streaming CSV evidence import (S3), real-client pass. Spawns the actual
 * `python app/server.py` console (not console_browser_fixture.py) so imports
 * really land on disk and survive a same-port restart. Run with
 * MENTAT_NODE_MODULES pointing to a local Playwright installation, from cwd
 * mentat/: `node tests\test_evidence_csv_browser.cjs`.
 *
 * Every wait below is bounded, and a top-level watchdog forces the process to
 * exit and name the step it was on if something outside those bounds still
 * hangs (a prior run hung silently for 10+ minutes with zero output; this is
 * the fix -- see HANDOFF.md S3 section).
 */
const assert = require('node:assert/strict');
const {spawn} = require('node:child_process');
const {execFileSync} = require('node:child_process');
const path = require('node:path');
const os = require('node:os');
const fs = require('node:fs');
const net = require('node:net');
const modules = process.env.MENTAT_NODE_MODULES || path.join(os.homedir(), '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules');
const {chromium} = require(require.resolve('playwright', {paths: [modules]}));

const MENTAT_DIR = path.resolve(__dirname, '..');
const FORBIDDEN_PORTS = new Set([8802, 8806, 8808]);
// Waits are sized for a loaded host, not a quiet one. The same 6 MB ingest
// measured between 0.8s and 34.7s on this machine depending on what else was
// running (1.6-3.5 GB free of 31.5 GB), and step 5 failed twice at 60s purely
// under that load while passing in ~5s on a quiet host. The caps below have to
// clear the slow end, and this one has to clear the sum of them.
const HARD_CAP_MS = 1_200_000; // raised for S3b: 14 more steps, each with its own bounded (mostly 15s) wait, added atop the original 19-step sum.
const trace = message => { if (process.env.MENTAT_BROWSER_TRACE) console.log(`[browser] ${message}`); };

// Rows are the width of a real Schedule A export, ~155 bytes, which is what
// makes a 40 MB fixture a legitimate import. At the original ~77 bytes a row,
// 40 MB came to 516,377 rows and the server refused the whole file with
// "Choose a CSV containing no more than 500,000 rows." - correctly, since
// MAX_ROWS binds alongside the 50 MB ceiling. The fixture, not the server, was
// what made step 6 unpassable.
const HEADER = 'committee_id,committee_name,contribution_receipt_amount,contribution_receipt_date,'
  + 'two_year_transaction_period,contributor_name,contributor_city,contributor_state,contributor_zip,'
  + 'contributor_employer,contributor_occupation,memo_text,sub_id\r\n';

function csvRow(index) {
  return `C00000001,Example PAC,${(index % 1000) + 1}.00,2026-01-01,2026,"Contributor, ${index}",`
    + `Washington,DC,20002,"Example Employer ${index}",Analyst,`
    + `"Memo for row ${index}, padded to a realistic filing width",SA-${index}\r\n`;
}

function buildCsvOfSize(targetBytes) {
  // Track the running byte count instead of re-measuring the whole
  // accumulated string every iteration (Buffer.byteLength(text) on a
  // multi-hundred-thousand-line string, called once per line, is O(n^2) and
  // was the actual cause of a 4+ minute hang building forty.csv -- nothing
  // to do with the server or Playwright).
  const parts = [HEADER];
  let bytes = Buffer.byteLength(HEADER, 'utf8');
  let index = 1;
  while (bytes < targetBytes) {
    const row = csvRow(index);
    parts.push(row);
    bytes += Buffer.byteLength(row, 'utf8');
    index += 1;
  }
  return parts.join('');
}

function wide201Csv() {
  const headers = ['committee_id', ...Array.from({length: 200}, (_, i) => `col${i}`)];
  const row = ['C00000001', ...Array.from({length: 200}, () => 'x')];
  return headers.join(',') + '\r\n' + row.join(',') + '\r\n';
}

function truncatedCsv() {
  return HEADER + csvRow(1) + 'C00000002,Example PAC,10.00,2026-01-02,2026,"Doe, Jane';
}

function latin1Buffer() {
  return Buffer.concat([
    Buffer.from(HEADER, 'utf8'),
    Buffer.from('C00000001,Example PAC,10.00,2026-01-01,2026,', 'utf8'),
    Buffer.from([0xff, 0xfe, 0x00]),
    Buffer.from(',SA-1\r\n', 'utf8'),
  ]);
}

function nocommitteeCsv() {
  return 'name,amount\r\nExample,10\r\n';
}

function writeFixtures(dir) {
  fs.writeFileSync(path.join(dir, 'six.csv'), buildCsvOfSize(6_000_000));
  fs.writeFileSync(path.join(dir, 'forty.csv'), buildCsvOfSize(40_000_000));
  // A sparse file: open + ftruncate to 500,000,001 bytes writes no actual
  // data (NTFS allocates nothing until written), and the client pre-flight
  // for an oversize file reads only file.size and sends no request, so the
  // fixture can exceed the 500 MB cap without a 500 MB write.
  {
    const fd = fs.openSync(path.join(dir, 'big.csv'), 'w');
    fs.ftruncateSync(fd, 500_000_001);
    fs.closeSync(fd);
  }
  fs.writeFileSync(path.join(dir, 'wide201.csv'), wide201Csv());
  fs.writeFileSync(path.join(dir, 'truncated.csv'), truncatedCsv());
  fs.writeFileSync(path.join(dir, 'empty.csv'), '');
  fs.writeFileSync(path.join(dir, 'latin1.csv'), latin1Buffer());
  fs.writeFileSync(path.join(dir, 'nocommittee.csv'), nocommitteeCsv());
  fs.writeFileSync(path.join(dir, 'notes.txt'), 'just some notes, not a CSV\n');
  fs.writeFileSync(path.join(dir, 'abort.csv'), HEADER + csvRow(1));
  fs.writeFileSync(path.join(dir, 'html.csv'), HEADER + csvRow(1));
}

function withTimeout(promise, ms, label) {
  let timer;
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(() => reject(new Error(`${label} exceeded its ${ms}ms bound`)), ms);
  });
  return Promise.race([promise, timeout]).finally(() => clearTimeout(timer));
}

function freePort() {
  const attemptOnce = () => new Promise((resolve, reject) => {
    const server = net.createServer();
    server.on('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const port = server.address().port;
      server.close(() => resolve(port));
    });
  });
  const pick = async () => {
    for (;;) {
      const port = await attemptOnce();
      if (!FORBIDDEN_PORTS.has(port)) return port;
    }
  };
  return withTimeout(pick(), 10000, 'freePort()');
}

function startServer(port, dataRoot) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.env.MENTAT_PYTHON || 'python',
      ['app/server.py', '--port', String(port), '--data-root', dataRoot],
      {cwd: MENTAT_DIR, stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true});
    const stderrLines = [];
    let stdout = '';
    let settled = false;
    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      reject(new Error(`server on port ${port} did not print a ready line within 30s; stderr: ${stderrLines.join('')}`));
    }, 30000);
    child.stdout.on('data', chunk => {
      stdout += chunk.toString();
      trace(`server ${port} stdout: ${chunk.toString().trim()}`);
      if (!settled && new RegExp(`Mentat app: http://127\\.0\\.0\\.1:${port}\\b`).test(stdout)) {
        settled = true;
        clearTimeout(timer);
        resolve(child);
      }
    });
    child.stderr.on('data', chunk => { stderrLines.push(chunk.toString()); trace(`server ${port} stderr: ${chunk.toString().trim()}`); });
    child.on('exit', code => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      reject(new Error(`server on port ${port} exited ${code} before reporting ready; stderr: ${stderrLines.join('')}`));
    });
    child.on('error', error => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      reject(error);
    });
  });
}

function stopServer(child) {
  return withTimeout(new Promise(resolve => {
    if (!child || child.exitCode !== null) { resolve(); return; }
    child.once('exit', () => resolve());
    child.kill();
  }), 10000, 'stopServer()').catch(error => { console.error(error.message); });
}

function cleanupPath(target) {
  try { fs.rmSync(target, {recursive: true, force: true, maxRetries: 10, retryDelay: 200}); }
  catch (error) { console.error(`cleanup failed for ${target}: ${error.message}`); }
}

// ---------------------------------------------------------------------------
// S3b additions: any file type, any path, xlsx sheets, browse(). Fixtures below
// land in the SAME scratch fixtureDir step 1 already created. sheets.xlsx and
// indiv-bulk.zip need a real xlsx/zip container; this repo already builds those
// from Python (openpyxl / the zipfile stdlib) rather than a Node dependency, so
// a short Python script is spawned once here, the same way startServer() already
// spawns `python app/server.py`.
// ---------------------------------------------------------------------------
const PYTHON_S3B_FIXTURE_SCRIPT = `
import sys, zipfile
import openpyxl

target = sys.argv[1]

wb = openpyxl.Workbook()
sheet1 = wb.active
sheet1.title = 'Sheet1'
sheet1.append(['committee_id', 'committee_name', 'contribution_receipt_amount', 'contribution_receipt_date',
               'two_year_transaction_period'])
sheet1.append(['C00000001', 'Example PAC', 10.0, '2026-01-05', '2026'])
sheet1.append(['C00000001', 'Example PAC', 20.0, '2026-01-06', '2026'])
detail = wb.create_sheet('Detail')
detail.append(['committee_id', 'committee_name', 'contribution_receipt_amount', 'contribution_receipt_date',
               'two_year_transaction_period'])
detail.append(['C00000002', 'Detail PAC', 30.0, '2026-02-05', '2026'])
wb.save(target + '/sheets.xlsx')

import datetime
book = openpyxl.Workbook()
overview = book.active
overview.title = 'Master Overview'
overview.append(['Credit Union Master Overview'])
overview.append(['Mentat master-workbook layout'])
overview.append([])
overview.append(['Company', 'Rank', 'Total Giving'])
overview.append(['Alpha CU', 1, 100.0])
columns = ['Source ID', 'Cycle', 'FEC Filing Cycle', 'Cycle Alignment', 'Company', 'Contributor', 'Employee Tier',
           'Amount', 'Analysis Amount', 'Party', 'Recipient Category', 'Category Source', 'Party Source', 'Recipient',
           'Committee ID', 'Recipient Key', 'Date', 'City', 'State', 'ZIP', 'Employer', 'Occupation', 'Record Type']
cycles = {
    '2023-2024': [('C00007880', 'AMERICAS CREDIT UNIONS PAC', 10.0, datetime.datetime(2024, 12, 31)),
                  ('C00007880', 'AMERICAS CREDIT UNIONS PAC', 15.5, datetime.datetime(2024, 6, 1)),
                  ('C00919084', 'TALARICO FOR TEXAS', 25.0, datetime.datetime(2024, 1, 2))],
    '2025-2026': [('C00919084', 'TALARICO FOR TEXAS', 30.77, datetime.datetime(2026, 3, 3))],
}
for cycle_name, rows in cycles.items():
    sheet = book.create_sheet(cycle_name)
    sheet.append([cycle_name + ' Credit Union Contributions'])
    sheet.append(['Contribution-date cycle.'])
    sheet.append(['Source DB SHA-256: fixture'])
    sheet.append(columns)
    for index, (committee, recipient, amount, when) in enumerate(rows, 1):
        sheet.append(['40%d' % index, cycle_name, cycle_name[-4:], 'OK', 'Alpha CU', 'DOE, JANE', 'Employee', amount, amount,
                      'D', 'Candidate', 'fec', '', recipient, committee, 'FEC:' + committee, when, 'CITY', 'ST', '00000',
                      'ALPHA CU', 'ANALYST', 'CONTRIBUTION'])
downstream = book.create_sheet('Downstream Activity')
downstream.append(['Downstream Committee-to-Candidate Activity'])
downstream.append(['Same-cycle activity.'])
downstream.append(['885,132 exact source rows'])
downstream.append([])
downstream.append(['Cycle', 'Source Committee', 'Source Committee ID', 'Candidate / Officeholder', 'Support / Oppose',
                   'Transaction Type', 'Net Included Amount'])
downstream.append(['2021-2022', 'ABRAHAM LINCOLN PAC', 'C00631051', 'ARENHOLZ, ASHLEY', 'Contribution / Other', '24K', 10000])
book.save(target + '/overview.xlsx')

header = ['CMTE_ID', 'AMNDT_IND', 'RPT_TP', 'TRANSACTION_PGI', 'IMAGE_NUM', 'TRANSACTION_TP', 'ENTITY_TP', 'NAME',
          'CITY', 'STATE', 'ZIP_CODE', 'EMPLOYER', 'OCCUPATION', 'TRANSACTION_DT', 'TRANSACTION_AMT', 'OTHER_ID',
          'TRAN_ID', 'FILE_NUM', 'MEMO_CD', 'MEMO_TEXT', 'SUB_ID']


def bulk_row(index):
    values = {name: '' for name in header}
    values.update({
        'CMTE_ID': 'C00000001', 'AMNDT_IND': 'N', 'RPT_TP': 'Q1', 'TRANSACTION_PGI': 'P2026',
        'IMAGE_NUM': '2026030100000%d' % index, 'TRANSACTION_TP': '15', 'ENTITY_TP': 'IND',
        'NAME': 'DOE JANE %d' % index, 'CITY': 'WASHINGTON', 'STATE': 'DC', 'ZIP_CODE': '20002',
        'EMPLOYER': 'EXAMPLE EMPLOYER', 'OCCUPATION': 'ANALYST',
        'TRANSACTION_DT': '0%d152026' % (1 + index % 9), 'TRANSACTION_AMT': '%d00.00' % index,
        'TRAN_ID': 'SA-%d' % index, 'FILE_NUM': '1234567', 'SUB_ID': '400000000000%d' % index,
    })
    return '|'.join(values[name] for name in header)


body = '\\r\\n'.join(bulk_row(index) for index in range(1, 4)) + '\\r\\n'
with zipfile.ZipFile(target + '/indiv-bulk.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
    archive.writestr('indiv.txt', body)
print('S3B_FIXTURES_OK')
`;

function buildXlsxAndZipFixtures(dir) {
  const scriptPath = path.join(dir, 'build_s3b_fixtures.py');
  fs.writeFileSync(scriptPath, PYTHON_S3B_FIXTURE_SCRIPT);
  const output = execFileSync(process.env.MENTAT_PYTHON || 'python', [scriptPath, dir], {cwd: MENTAT_DIR}).toString();
  if (!output.includes('S3B_FIXTURES_OK')) throw new Error(`fixture-building python script did not report success: ${output}`);
}

function writeS3bFixtures(dir) {
  buildXlsxAndZipFixtures(dir);
  fs.writeFileSync(path.join(dir, 'evidence.tsv'),
    'committee_id\tcommittee_name\tcontribution_receipt_amount\tcontribution_receipt_date\ttwo_year_transaction_period\r\n'
    + 'C00000001\tExample PAC\t10.00\t2026-01-05\t2026\r\n');
  fs.writeFileSync(path.join(dir, 'evidence.json'), JSON.stringify({results: [
    {committee_id: 'C00000001', committee_name: 'Example PAC', contribution_receipt_amount: 10.0,
     contribution_receipt_date: '2026-01-05', two_year_transaction_period: '2026'},
  ]}));
  // Windows-1252: 'Caf\xe9 PAC' -- 0xE9 is invalid standalone UTF-8, valid cp1252.
  fs.writeFileSync(path.join(dir, 'cp1252.csv'), Buffer.concat([
    Buffer.from('committee_id,committee_name,contribution_receipt_amount,contribution_receipt_date,'
      + 'two_year_transaction_period\r\nC00000001,Caf', 'utf8'),
    Buffer.from([0xe9]),
    Buffer.from(' PAC,10.00,2026-01-05,2026\r\n', 'utf8'),
  ]));
  fs.writeFileSync(path.join(dir, 'notes.pdf'), Buffer.from('%PDF-1.4 not really a pdf', 'utf8'));
}

let stepNumber = 0;
let currentStepLabel = 'startup (fixtures, port selection, server launch)';
let serverAForWatchdog = null;
let serverBForWatchdog = null;

// Belt-and-braces: even if some await above is never bounded by its own
// timeout, this forces the process to end and say which step it died on,
// rather than hang silently. Cleared implicitly by process.exit() on the
// normal path, since exit cancels all pending timers.
const watchdog = setTimeout(() => {
  console.error(`RED: hung >${HARD_CAP_MS / 1000}s at step ${stepNumber} (${currentStepLabel})`);
  try { if (serverAForWatchdog && serverAForWatchdog.exitCode === null) serverAForWatchdog.kill(); } catch { /* best effort */ }
  try { if (serverBForWatchdog && serverBForWatchdog.exitCode === null) serverBForWatchdog.kill(); } catch { /* best effort */ }
  process.exit(1);
}, HARD_CAP_MS);

let stepStartedAt = Date.now();

function step(label) {
  stepNumber += 1;
  currentStepLabel = label;
  stepStartedAt = Date.now();
  console.log(`STEP ${stepNumber}: ${label}`);
}

function pass(detail) {
  console.log(`PASS step ${stepNumber} (${((Date.now() - stepStartedAt) / 1000).toFixed(1)}s) - ${detail}`);
}

(async () => {
  let browser = null;
  let serverA = null;
  let serverB = null;
  let secondPage = null;
  const dataRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'mentat-evidence-data-'));
  const fixtureDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mentat-evidence-fixtures-'));
  let failed = false;

  try {
    step('write fixture CSVs to a scratch directory');
    writeFixtures(fixtureDir);
    pass(`fixtures written under ${fixtureDir}`);

    step('pick a free port and launch the first console server');
    const portA = await freePort();
    serverA = await startServer(portA, dataRoot);
    serverAForWatchdog = serverA;
    const origin = `http://127.0.0.1:${portA}`;
    pass(`server A ready on port ${portA}, data root ${dataRoot}`);

    step('launch headless Chrome and open a page');
    browser = await withTimeout(
      chromium.launch({headless: true, channel: process.env.MENTAT_BROWSER_CHANNEL || 'chrome', timeout: 30000}),
      35000, 'chromium.launch()',
    );
    const page = await browser.newPage({viewport: {width: 1440, height: 1050}});
    page.setDefaultTimeout(15000);
    const errors = [];
    const remote = [];
    const consoleLines = [];
    const apiCalls = [];
    page.on('pageerror', e => errors.push(e.message));
    page.on('request', request => {
      if (!request.url().startsWith(origin) && !request.url().startsWith('blob:')) remote.push(request.url());
    });
    // Diagnostics only. A status-wait that times out has to say what the status
    // actually was and what the page had just been told, otherwise a slow host
    // and a stuck client look identical in the failure output.
    page.on('console', message => consoleLines.push(`${message.type()}: ${message.text()}`));
    page.on('response', response => {
      const url = response.url();
      if (!url.includes('/api/evidence-csv')) return;
      const entry = {line: `${new Date().toISOString().slice(11, 23)} ${response.request().method()} `
        + `${response.status()} ${url.replace(origin, '')}`};
      apiCalls.push(entry);
      if (url.includes('job=') || response.status() >= 400) {
        response.text().then(body => { entry.line += ` body=${body.slice(0, 240)}`; }, () => {});
      }
    });
    pass('browser launched, page opened, pageerror/request listeners attached');

    const statusText = async targetPage => (await targetPage.textContent('#evidence-csv-status')).trim();
    const assertStatusNotEmpty = async targetPage => assert.notStrictEqual(await statusText(targetPage), '');

    async function explainWait(what, error) {
      let current = '<unreadable>';
      try { current = await statusText(page); } catch (readError) { current = `<${readError.message}>`; }
      const enriched = [
        `${error.message}`,
        `  waiting for: ${what}`,
        `  #evidence-csv-status was: ${JSON.stringify(current)}`,
        `  last ${Math.min(14, apiCalls.length)} of ${apiCalls.length} /api/evidence-csv responses:`,
        ...apiCalls.slice(-14).map(entry => `    ${entry.line}`),
        `  page console (last 20 of ${consoleLines.length}):`,
        ...consoleLines.slice(-20).map(line => `    ${line}`),
        `  pageerrors: ${JSON.stringify(errors)}`,
      ].join('\n');
      throw Object.assign(new Error(enriched), {cause: error});
    }

    async function waitForStatusExact(expected, timeout = 15000) {
      try {
        await page.waitForFunction(
          ({selector, text}) => (document.querySelector(selector)?.textContent || '').trim() === text,
          {selector: '#evidence-csv-status', text: expected},
          {timeout},
        );
      } catch (error) { await explainWait(`status exactly ${JSON.stringify(expected)}`, error); }
      await assertStatusNotEmpty(page);
    }

    async function waitForStatusMatching(pattern, timeout = 15000) {
      try {
        await page.waitForFunction(
          ({selector, source}) => new RegExp(source).test((document.querySelector(selector)?.textContent || '').trim()),
          {selector: '#evidence-csv-status', source: pattern.source},
          {timeout},
        );
      } catch (error) { await explainWait(`status matching ${pattern}`, error); }
      await assertStatusNotEmpty(page);
    }

    step('open the evidence tab, select CSV source, expect the empty-catalog status');
    await page.goto(origin + '/');
    await page.click('#tab-evidence');
    await page.selectOption('#evidence-source', 'csv');
    await waitForStatusExact('No CSV imported yet. Choose a file.');
    pass('evidence tab open, CSV source selected, empty-catalog status shown');

    step('import six.csv (~6 MB) and check the first page of rows');
    await page.setInputFiles('#evidence-csv-file', path.join(fixtureDir, 'six.csv'));
    // ~5s on a quiet host; 60s was not enough twice under load. See HARD_CAP_MS.
    await waitForStatusMatching(/rows in file$/, 180000);
    assert.equal(await page.isVisible('#evidence-csv-results'), true);
    const rowCountSix = await page.locator('#evidence-csv-rows tr').count();
    assert.equal(rowCountSix, 100);
    const committeeOptionsSix = await page.locator('#evidence-csv-committee option').count();
    assert.ok(committeeOptionsSix >= 1, 'expected at least one PAC option after importing six.csv');
    pass(`six.csv imported (~6 MB), ${rowCountSix} rows rendered on the first page`);

    step('import forty.csv (~40 MB) and watch for a progress sample');
    const samples = [];
    await page.setInputFiles('#evidence-csv-file', path.join(fixtureDir, 'forty.csv'));
    const pollDeadline = Date.now() + 480000;
    let readyForty = false;
    while (Date.now() < pollDeadline) {
      const text = await statusText(page);
      samples.push(text);
      if (/rows in file$/.test(text)) { readyForty = true; break; }
      await page.waitForTimeout(100);
    }
    assert.ok(readyForty, `forty.csv never reached a ready state within 480s; last samples: ${JSON.stringify(samples.slice(-5))}`);
    await assertStatusNotEmpty(page);
    assert.ok(samples.some(sample => /^Reading forty\.csv · [\d,]+ rows · [\d.]+ of 40\.0 MB$/.test(sample)),
      `no progress sample matched the expected pattern; first samples: ${JSON.stringify(samples.slice(0, 20))}`);
    assert.ok(await page.locator('#evidence-csv-rows tr').count() > 0);
    pass(`forty.csv imported (~40 MB) after ${samples.length} polled progress samples`);

    step('kill and relaunch the console on the same port/data root; reuse prior imports');
    await stopServer(serverA);
    serverA = await startServer(portA, dataRoot);
    serverAForWatchdog = serverA;
    await page.reload();
    await page.click('#tab-evidence');
    await page.selectOption('#evidence-source', 'csv');
    await page.waitForSelector('#evidence-csv-source', {timeout: 15000});
    const sourceOptionTexts = await page.locator('#evidence-csv-source option').allTextContents();
    assert.equal(sourceOptionTexts.filter(text => text.includes('six.csv') || text.includes('forty.csv')).length, 2,
      `expected exactly the 2 previously imported sources, got: ${JSON.stringify(sourceOptionTexts)}`);
    const sixLabel = sourceOptionTexts.find(text => text.includes('six.csv'));
    const [selectResponse] = await Promise.all([
      page.waitForResponse(response => response.url().includes('/api/evidence-csv?id=') && response.request().method() === 'GET'),
      page.selectOption('#evidence-csv-source', {label: sixLabel}),
    ]);
    assert.equal(selectResponse.status(), 200, 'GET /api/evidence-csv?id= for the previously imported six.csv must succeed after a restart');
    assert.ok(await page.locator('#evidence-csv-rows tr').count() > 0);
    await assertStatusNotEmpty(page);
    pass('server restarted on the same port and data root; both prior imports reachable without re-upload');

    step('launch a second console on the same data root, a different port');
    const portB = await freePort();
    serverB = await startServer(portB, dataRoot);
    serverBForWatchdog = serverB;
    const originB = `http://127.0.0.1:${portB}`;
    secondPage = await browser.newPage();
    secondPage.setDefaultTimeout(15000);
    await secondPage.goto(originB + '/');
    await secondPage.click('#tab-evidence');
    await secondPage.selectOption('#evidence-source', 'csv');
    await secondPage.waitForSelector('#evidence-csv-source', {timeout: 15000});
    const sourceOptionTextsB = await secondPage.locator('#evidence-csv-source option').allTextContents();
    assert.ok(sourceOptionTextsB.some(text => text.includes('six.csv')));
    assert.ok(sourceOptionTextsB.some(text => text.includes('forty.csv')));
    await secondPage.close();
    secondPage = null;
    await stopServer(serverB);
    serverB = null;
    serverBForWatchdog = null;
    pass('a second console on the same data root and a different port lists both imports');

    step('error case: big.csv rejected client-side, no upload issued');
    const evidencePosts = [];
    const trackPosts = request => {
      if (request.method() === 'POST' && request.url().includes('/api/evidence-csv')) evidencePosts.push(request.url());
    };
    page.on('request', trackPosts);
    await page.setInputFiles('#evidence-csv-file', path.join(fixtureDir, 'big.csv'));
    await waitForStatusMatching(/^big\.csv \(500\.0 MB\): Choose a CSV no larger than 500 MB\.$/);
    page.off('request', trackPosts);
    assert.equal(evidencePosts.length, 0, 'big.csv must be rejected client-side before any upload is attempted');
    pass('big.csv rejected by the client pre-flight size check; no POST issued');

    step('error case: notes.txt is read as delimited text and refused for its header');
    await page.setInputFiles('#evidence-csv-file', path.join(fixtureDir, 'notes.txt'));
    await waitForStatusExact('notes.txt: The CSV needs a Committee ID, CMTE_ID, or Source Committee ID column.');
    pass('notes.txt read as delimited text and refused for its header');

    step('error case: wide201.csv rejected for exceeding the column cap');
    await page.setInputFiles('#evidence-csv-file', path.join(fixtureDir, 'wide201.csv'));
    await waitForStatusExact('wide201.csv: The CSV needs unique nonempty column names, with no more than 200 columns.');
    pass('wide201.csv rejected for exceeding the column cap');

    step('error case: truncated.csv rejected for an unterminated quoted field');
    await page.setInputFiles('#evidence-csv-file', path.join(fixtureDir, 'truncated.csv'));
    await waitForStatusMatching(/^truncated\.csv: The CSV could not be read at row [\d,]+\. Check its quoted fields and delimiter\.$/);
    pass('truncated.csv rejected for an unterminated quoted field');

    step('error case: empty.csv rejected as empty');
    await page.setInputFiles('#evidence-csv-file', path.join(fixtureDir, 'empty.csv'));
    await waitForStatusExact('empty.csv: The CSV file is empty.');
    pass('empty.csv rejected as empty');

    step('error case: latin1.csv holds control bytes and is refused as binary');
    await page.setInputFiles('#evidence-csv-file', path.join(fixtureDir, 'latin1.csv'));
    await waitForStatusExact('latin1.csv: This file contains binary data and could not be read as text.');
    pass('latin1.csv holds control bytes and is refused as binary');

    step('error case: nocommittee.csv rejected for missing a committee-id column');
    await page.setInputFiles('#evidence-csv-file', path.join(fixtureDir, 'nocommittee.csv'));
    await waitForStatusExact('nocommittee.csv: The CSV needs a Committee ID, CMTE_ID, or Source Committee ID column.');
    pass('nocommittee.csv rejected for missing a committee-id column');

    step('error case: abort.csv reports a transport failure when the upload is aborted');
    await page.route('**/api/evidence-csv', route => route.abort());
    await page.setInputFiles('#evidence-csv-file', path.join(fixtureDir, 'abort.csv'));
    await waitForStatusMatching(/^abort\.csv: upload to \/api\/evidence-csv failed: /);
    await page.unroute('**/api/evidence-csv');
    pass('abort.csv reports a transport failure when the upload request is aborted');

    step('error case: html.csv reports an unparseable HTTP 500 response');
    await page.route('**/api/evidence-csv', route => route.fulfill({status: 500, contentType: 'text/html', body: '<html>oops</html>'}));
    await page.setInputFiles('#evidence-csv-file', path.join(fixtureDir, 'html.csv'));
    await waitForStatusExact('html.csv: /api/evidence-csv answered HTTP 500 with no error message.');
    await page.unroute('**/api/evidence-csv');
    pass('html.csv reports an unparseable HTTP 500 response');

    step('error case: a bad ?offset= value returns 400 with the exact M_PAGE message');
    const sixSourceId = await page.evaluate(async () => {
      const response = await fetch('/api/evidence-csv');
      const body = await response.json();
      const match = (body.sources || []).find(source => source.name === 'six.csv');
      return match ? match.id : null;
    });
    assert.ok(sixSourceId, 'expected to find six.csv in the sources listing to probe the page-argument validator');
    const pageProbe = await page.evaluate(async id => {
      const response = await fetch(`/api/evidence-csv?id=${id}&offset=abc`);
      const body = await response.json();
      return {status: response.status, error: body.error};
    }, sixSourceId);
    assert.equal(pageProbe.status, 400);
    assert.equal(pageProbe.error, 'Choose a valid CSV row page (1–1,000 rows).');
    pass('a bad ?offset= value returns 400 with the exact M_PAGE message, not a leaked exception');

    step('final check: zero pageerror entries and zero remote requests');
    assert.equal(errors.length, 0, `expected zero pageerror entries, got: ${JSON.stringify(errors)}`);
    assert.equal(remote.length, 0, `expected zero remote requests, got: ${JSON.stringify(remote)}`);
    pass('zero pageerror entries and zero remote requests across the whole run');

    step('write additional S3b fixtures (xlsx, tsv, json, cp1252 csv, fec bulk zip, pdf)');
    writeS3bFixtures(fixtureDir);
    pass(`S3b fixtures written under ${fixtureDir}`);

    step('picker input has no accept attribute; its label is unchanged');
    const fileInputAccept = await page.getAttribute('#evidence-csv-file', 'accept');
    assert.equal(fileInputAccept, null, `expected no accept attribute on #evidence-csv-file, got ${JSON.stringify(fileInputAccept)}`);
    const fileLabelText = (await page.textContent('label[for="evidence-csv-file"]')).trim();
    assert.equal(fileLabelText, 'Choose CSV');
    await assertStatusNotEmpty(page);
    pass('picker input has no accept attribute; label text unchanged ("Choose CSV")');

    step('upload a 2-sheet xlsx whose sheets share one header: both sheets read as one table, no picker UI');
    await page.setInputFiles('#evidence-csv-file', path.join(fixtureDir, 'sheets.xlsx'));
    await waitForStatusMatching(/rows in file$/);
    assert.equal(await page.locator('#evidence-sheet-label').count(), 0, 'no worksheet picker markup may exist (UI unchanged)');
    // The page renders one committee at a time; the file-level count and the two
    // committees (one per sheet) prove both sheets were read as one table.
    const sheetsStatus = (await page.textContent('#evidence-csv-status')).trim();
    assert.ok(/ · 3 rows in file$/.test(sheetsStatus), `expected '… · 3 rows in file', got ${JSON.stringify(sheetsStatus)}`);
    const sheetsCommittees = await page.locator('#evidence-csv-committee option').allTextContents();
    assert.equal(sheetsCommittees.length, 2, `expected two committees (one per sheet), got ${JSON.stringify(sheetsCommittees)}`);
    const sheetsRowCount = await page.locator('#evidence-csv-rows tr').count();
    assert.ok(sheetsRowCount > 0, 'expected rows rendered for the first committee');
    const sheetsWarnings = await page.textContent('#evidence-csv-warnings');
    assert.ok(sheetsWarnings.includes('Read 2 worksheets with the same columns: Sheet1, Detail.'),
      `expected the combined-sheets warning, got: ${JSON.stringify(sheetsWarnings)}`);
    await assertStatusNotEmpty(page);
    pass('sheets.xlsx read Sheet1 + Detail as one 3-row, 2-committee table; combined-sheets warning shown; no picker UI');

    step('upload a tab-delimited tsv: ready');
    await page.setInputFiles('#evidence-csv-file', path.join(fixtureDir, 'evidence.tsv'));
    await waitForStatusMatching(/rows in file$/);
    assert.ok(await page.locator('#evidence-csv-rows tr').count() > 0);
    await assertStatusNotEmpty(page);
    pass('evidence.tsv (tab-delimited) imported and ready');

    step('upload an openFEC-shaped json file: ready');
    await page.setInputFiles('#evidence-csv-file', path.join(fixtureDir, 'evidence.json'));
    await waitForStatusMatching(/rows in file$/);
    assert.ok(await page.locator('#evidence-csv-rows tr').count() > 0);
    await assertStatusNotEmpty(page);
    pass('evidence.json ({"results": [...]}) imported and ready');

    step('upload a Windows-1252 csv: ready, with the decode warning visible');
    await page.setInputFiles('#evidence-csv-file', path.join(fixtureDir, 'cp1252.csv'));
    await waitForStatusMatching(/rows in file$/);
    const warningsText = await page.textContent('#evidence-csv-warnings');
    assert.ok(warningsText.includes('Decoded as Windows-1252 because the file is not valid UTF-8.'),
      `expected the Windows-1252 warning in #evidence-csv-warnings, got: ${JSON.stringify(warningsText)}`);
    await assertStatusNotEmpty(page);
    pass('cp1252.csv imported and ready; Windows-1252 decode warning visible in #evidence-csv-warnings');

    step('upload an FEC bulk zip (recognised "indiv" stem): ready');
    await page.setInputFiles('#evidence-csv-file', path.join(fixtureDir, 'indiv-bulk.zip'));
    await waitForStatusMatching(/rows in file$/);
    assert.ok(await page.locator('#evidence-csv-rows tr').count() > 0);
    await assertStatusNotEmpty(page);
    pass('indiv-bulk.zip (FEC bulk) imported and ready');

    step('error case: notes.pdf rejected for its file type, no upload issued');
    const evidencePostsPdf = [];
    const trackPostsPdf = request => {
      if (request.method() === 'POST' && request.url().includes('/api/evidence-csv')) evidencePostsPdf.push(request.url());
    };
    page.on('request', trackPostsPdf);
    await page.setInputFiles('#evidence-csv-file', path.join(fixtureDir, 'notes.pdf'));
    await waitForStatusExact('notes.pdf: This file type (.pdf) is not supported. Choose CSV, TSV, TXT, XLSX, JSON or an FEC bulk ZIP.');
    page.off('request', trackPostsPdf);
    assert.equal(evidencePostsPdf.length, 0, 'notes.pdf must be rejected client-side before any upload is attempted');
    pass('notes.pdf rejected by the client pre-flight file-type check; no POST issued');

    step('upload a Mentat industry workbook: title rows, header on row 4, two cycle sheets read as one table, receipts totalled');
    await page.setInputFiles('#evidence-csv-file', path.join(fixtureDir, 'overview.xlsx'));
    await waitForStatusMatching(/rows in file$/);
    const overviewRows = await page.locator('#evidence-csv-rows tr').count();
    assert.ok(overviewRows > 0, 'expected contribution rows rendered from the cycle sheets');
    const overviewWarnings = await page.textContent('#evidence-csv-warnings');
    assert.ok(overviewWarnings.includes('Read 2 worksheets with the same columns: 2023-2024, 2025-2026.'),
      `expected the combined cycle-sheets warning, got: ${JSON.stringify(overviewWarnings)}`);
    const overviewTotals = await page.textContent('#evidence-csv-totals');
    assert.ok(overviewTotals.includes('Receipts'), `expected a Receipts channel total, got: ${JSON.stringify(overviewTotals)}`);
    const overviewCommittees = await page.locator('#evidence-csv-committee option').allTextContents();
    assert.ok(overviewCommittees.some(text => text.includes('TALARICO FOR TEXAS')),
      `expected the recipient name in the committee picker, got: ${JSON.stringify(overviewCommittees)}`);
    await assertStatusNotEmpty(page);
    pass(`overview.xlsx: ${overviewRows} rows rendered from the cycle sheets, Receipts totalled, recipient names shown`);

    step('no path box, no browse panel, no sheet picker exist in the page (UI unchanged)');
    for (const id of ['evidence-path', 'evidence-header-path', 'evidence-path-read', 'evidence-browse', 'evidence-browser', 'evidence-sheet']) {
      assert.equal(await page.locator('#' + id).count(), 0, `#${id} must not exist`);
    }
    await assertStatusNotEmpty(page);
    pass('none of the S3b path/browse/sheet controls exist in the page');

    step('final check (again, across every S3b step too): zero pageerror entries and zero remote requests');
    assert.equal(errors.length, 0, `expected zero pageerror entries, got: ${JSON.stringify(errors)}`);
    assert.equal(remote.length, 0, `expected zero remote requests, got: ${JSON.stringify(remote)}`);
    pass('zero pageerror entries and zero remote requests across the whole run, including every S3b step');

    console.log(`ALL ${stepNumber} STEPS PASSED`);
  } catch (error) {
    failed = true;
    console.error(`FAIL step ${stepNumber} (${currentStepLabel}): ${error && error.stack ? error.stack : error}`);
  } finally {
    if (secondPage) { try { await withTimeout(secondPage.close(), 10000, 'secondPage.close()'); } catch (error) { console.error(error.message); } }
    if (browser) { try { await withTimeout(browser.close(), 10000, 'browser.close()'); } catch (error) { console.error(error.message); } }
    await stopServer(serverA);
    await stopServer(serverB);
    cleanupPath(fixtureDir);
    cleanupPath(dataRoot);
  }
  process.exit(failed ? 1 : 0);
})();
