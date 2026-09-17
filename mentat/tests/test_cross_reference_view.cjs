/* The dwarfed cross-reference tab: clear refunds, obvious outliers, no totals. */
const assert = require('node:assert/strict');
const view = require('../app/cross-reference.js');

const DIGEST = {
  basis: 'A receipt is listed as large at $1,000,000.00 or more, or at $100,000.00 or more when an individual sent it; both thresholds are a proposed default and await the owner’s ratification.',
  refunds: {
    linked: [{refund_record_id:'R1', original_record_id:'O1', company:'A Bank', cycle:'2024',
      refund_amount:-2000, original_amount:50000,
      refund_source_url:'https://docquery.fec.gov/pdf/333/three.pdf',
      original_source_url:'https://docquery.fec.gov/pdf/000/orig.pdf'}],
    linked_count: 1, linked_amount: -2000,
    unlinked: [{record_id:'U1', company:'A Bank', cycle:'2024', amount:-7500,
      description:'RETURN OF ERRONEOUS DEBIT', source_url:'https://docquery.fec.gov/pdf/222/two.pdf'}],
    unlinked_count: 1, unlinked_amount: -7500,
  },
  outliers: {
    non_giving: [{record_id:'N1', company:'A Bank', cycle:'2024', amount:15000, role:'other_receipt',
      description:'LOAN', source_url:'https://docquery.fec.gov/pdf/111/one.pdf'}],
    non_giving_count: 1, non_giving_amount: 15000,
    large: [{record_id:'L1', company:'A Bank', cycle:'2024', amount:120000, entity:'IND', role:'contribution',
      source_url:'https://docquery.fec.gov/pdf/444/four.pdf'}],
    large_count: 1, large_amount: 120000,
  },
};
const fixture = {available:true, status:'completed', run_id:'20260910-safe', selected_by:'pointer', report:{
  run_id:'20260910-safe', status:'completed', generated_at:'2026-09-10T12:00:00Z',
  scope:{industries:['Banking'], companies:['A Bank'], cycles:[2024], company_count:1},
  digest_available:true, digest:DIGEST, digest_message:'',
  limitations:['Collection coverage remains unverified.'],
}};
const rendered = view.html(fixture);

// The tab says what it is, and no total can be read off it.
assert.match(rendered,/The published report workbook is the accounting of record\. This view lists only obvious outliers and clear refunds found while cross-referencing; it publishes no totals\./);
assert.doesNotMatch(rendered,/Observed original giving/);
assert.doesNotMatch(rendered,/PAC outgoing|Previous receipt total|Partisan composition|Records needing review|Collection coverage follow-up|Provisional totals/);
assert.doesNotMatch(rendered,/xref-step/);

// Both sections, both tables in each.
assert.match(rendered,/<h2>Clear refunds<\/h2>/);
assert.match(rendered,/<h2>Obvious outliers<\/h2>/);
assert.match(rendered,/<h3>Negative adjustments without a matched original<\/h3>/);
assert.match(rendered,/<h3>Counted as giving, but not giving<\/h3>/);
assert.match(rendered,/<h3>Large receipts to eyeball<\/h3>/);
assert.match(rendered,/Banking · Cycles 2024/);
assert.match(rendered,/Run 20260910-safe/);
assert.match(rendered,/Generated 2026-09-10T12:00:00Z/);

// A refund pair carries a link to each side of the pair.
assert.match(rendered,/href="https:\/\/docquery.fec.gov\/pdf\/333\/three.pdf"[^>]*>R1 ↗<\/a>/);
assert.match(rendered,/href="https:\/\/docquery.fec.gov\/pdf\/000\/orig.pdf"[^>]*>O1 ↗<\/a>/);
assert.match(rendered,/rel="noopener noreferrer"/);
assert.match(rendered,/-\$2,000\.00/);
assert.match(rendered,/\$50,000\.00/);

// Outlier rows print the receipt text, the role in plain words and the size.
assert.match(rendered,/LOAN/);
assert.match(rendered,/Other receipt/);
assert.doesNotMatch(rendered,/other_receipt/);
assert.match(rendered,/\$15,000\.00/);
assert.match(rendered,/Individual/);
assert.doesNotMatch(rendered,/>IND</);
assert.match(rendered,/\$120,000\.00/);
assert.match(rendered,/both thresholds are a proposed default and await the owner’s ratification/);
assert.match(rendered,/1 linked refund in this run\./);
assert.match(rendered,/1 unmatched negative adjustment in this run\./);
assert.match(rendered,/1 reclassified receipt in this run\./);
assert.match(rendered,/1 large receipt in this run\./);

// A capped list says how many rows the saved digest holds.
const many = structuredClone(fixture);
many.report.digest.outliers.non_giving = Array.from({length:200}, (_, i) => ({record_id:'N'+i, company:'A Bank', cycle:'2024', amount:100 - i/1000, role:'other_receipt'}));
many.report.digest.outliers.non_giving_count = 4778;
const manyHtml = view.html(many);
assert.match(manyHtml,/4,778 reclassified receipts in this run\. The 200 largest are listed here; the saved digest holds the rest\./);
assert.match(manyHtml,/N199/);

// Empty tables say what was not found rather than printing nothing.
const bare = structuredClone(fixture);
bare.report.digest = {basis:'', refunds:{linked:[], linked_count:0, unlinked:[], unlinked_count:0},
  outliers:{non_giving:[], non_giving_count:0, large:[], large_count:0}};
const bareHtml = view.html(bare);
assert.match(bareHtml,/No refund in this run is matched to the gift it reverses/);
assert.match(bareHtml,/Every negative adjustment in this run is matched to an original gift/);
assert.match(bareHtml,/No receipt the accepted report counted was reclassified as non-giving/);
assert.match(bareHtml,/No counted receipt in this run reached the size stated below/);
assert.match(bareHtml,/The size that selects these rows is unavailable/);

// A run with no digest says how to build one, and shows no tables.
const noDigest = structuredClone(fixture);
noDigest.report.digest = null;
noDigest.report.digest_available = false;
noDigest.report.digest_message = 'This run has no outlier/refund digest. Build it with tools/cross_reference_digest.py <run_dir>.';
const noDigestHtml = view.html(noDigest);
assert.match(noDigestHtml,/This run has no outlier\/refund digest\. Build it with tools\/cross_reference_digest\.py &lt;run_dir&gt;\./);
assert.doesNotMatch(noDigestHtml,/<h2>Clear refunds<\/h2>|<h2>Obvious outliers<\/h2>/);
assert.match(noDigestHtml,/Run 20260910-safe/);

// The envelopes this view already had.
assert.match(view.html({status:'empty'}),/No run has been saved yet/);
assert.match(view.html({status:'empty'}),/it publishes no totals/);
assert.match(view.html({status:'error',message:'Mismatch'}),/No totals are shown/);
assert.doesNotMatch(view.html({status:'error',message:'Mismatch'}),/\$/);
assert.match(view.html({available:true,status:'running',run_id:'active',progress:{updated_at:'2026-09-10T12:00:00Z'}}),/Evidence is being cross-referenced/);
const failed = {available:true,status:'failed',run_id:'bad',notices:[],progress:{message:'Failure'}};
assert.equal(view.html(failed),view.html(failed)); // Rendering does not mutate saved notices.
assert.match(view.html(failed),/Run failed/);

// Every value reaching the page is escaped, whichever table it lands in.
const injected = structuredClone(fixture), bad = '<img src=x onerror="alert(1)">';
injected.run_id = bad;
injected.report.scope.companies = [bad];
injected.report.digest.outliers.non_giving[0].description = '<script>alert(1)</script> RETURN OF ERRONEOUS DEBIT';
injected.report.digest.outliers.non_giving[0].role = bad;
injected.report.digest.refunds.linked[0].refund_record_id = bad;
injected.report.digest.basis = bad;
const injectedHtml = view.html(injected);
assert.doesNotMatch(injectedHtml,/<img|<script|onerror="/);
assert.match(injectedHtml,/&lt;img/);
assert.match(injectedHtml,/&lt;script&gt;alert\(1\)&lt;\/script&gt; RETURN OF ERRONEOUS DEBIT/);

// Only public FEC filings become links.
for (const url of ['javascript:alert(1)','https://evil.test/file','https://www.fec.gov/file?api_key=secret']) {
  const unsafe = structuredClone(fixture);
  unsafe.report.digest = {basis:'', refunds:{linked:[], linked_count:0, unlinked:[{record_id:'U1', company:'A Bank', cycle:'2024', amount:-1, source_url:url}], unlinked_count:1},
    outliers:{non_giving:[], non_giving_count:0, large:[], large_count:0}};
  assert.doesNotMatch(view.html(unsafe),/href=/);
}

assert.equal(view.money(null),'Unavailable');
assert.equal(view.money('60'),'Unavailable');
assert.equal(view.money(Infinity),'Unavailable');
assert.equal(view.money(0),'$0.00');
console.log('Cross-reference view checks passed.');

// Opt-in browser integration verifies tab activation, rendering and refresh.
if (process.env.MENTAT_CROSS_REFERENCE_BROWSER === '1') (async () => {
  const {spawn} = require('node:child_process'), {once} = require('node:events'), path = require('node:path'), os = require('node:os');
  const modules = process.env.MENTAT_NODE_MODULES || path.join(os.homedir(), '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules');
  const {chromium} = require(require.resolve('playwright', {paths:[modules]}));
  const server = spawn(process.env.MENTAT_PYTHON || 'python', [path.join(__dirname,'console_browser_fixture.py')], {stdio:['pipe','pipe','pipe'],windowsHide:true});
  let browser;
  const stderr = []; server.stderr.on('data', chunk => stderr.push(chunk.toString()));
  try {
    const origin = await new Promise((resolve,reject) => {
      let output = '';
      server.stdout.on('data', chunk => { output += chunk; if (output.includes('\n')) resolve(output.trim().split('\n')[0]); });
      server.on('exit', code => reject(new Error(`Fixture exited ${code}: ${stderr.join('')}`)));
      server.on('error', reject);
    });
    browser = await chromium.launch({headless:true, channel:process.env.MENTAT_BROWSER_CHANNEL || 'chrome'});
    const page = await browser.newPage({viewport:{width:1440,height:1100}});
    const errors = []; page.on('pageerror', error => errors.push(error.message));
    let data = fixture, calls = 0;
    await page.route('**/api/cross-reference', route => { calls++; return route.fulfill({json:data}); });
    await page.goto(origin + '/#cross-reference');
    await page.getByRole('heading',{name:'Clear refunds'}).waitFor();
    assert.equal(await page.locator('#tab-cross-reference').getAttribute('aria-selected'),'true');
    assert.equal(await page.locator('#view-collection').isVisible(),false);
    assert.equal(await page.locator('#view-graph').isVisible(),false);
    assert.equal(await page.getByRole('heading',{name:'Obvious outliers'}).count(),1);
    assert.equal(await page.getByText('Observed original giving',{exact:true}).count(),0);
    assert.match(await page.locator('#xref-results').innerText(),/it publishes no totals/);
    if (process.env.MENTAT_CROSS_REFERENCE_SCREENSHOT) await page.screenshot({path:process.env.MENTAT_CROSS_REFERENCE_SCREENSHOT,fullPage:true});
    await page.setViewportSize({width:390,height:844});
    assert.equal(await page.locator('#view-cross-reference').evaluate(element => element.scrollWidth <= element.clientWidth),true);
    const tabIds = await page.locator('.workspace-tabs [role=tab]').evaluateAll(tabs => tabs.map(tab => tab.id));
    const previousTab = tabIds[(tabIds.indexOf('tab-cross-reference') + tabIds.length - 1) % tabIds.length];
    await page.locator('#' + previousTab).click();
    await page.locator('#' + previousTab).focus();
    await page.keyboard.press('ArrowRight');
    assert.equal(await page.locator('#tab-cross-reference').getAttribute('aria-selected'),'true');
    data = {status:'error',message:'Saved report fingerprint mismatch.'};
    await page.locator('#xref-refresh').click();
    await page.getByRole('heading',{name:'Saved evidence unavailable'}).waitFor();
    assert.equal(await page.getByRole('heading',{name:'Clear refunds'}).count(),0);
    assert.ok(calls >= 2);
    assert.deepEqual(errors,[]);
    console.log('Cross-reference browser checks passed.');
  } finally {
    if (browser) await browser.close();
    const exited = once(server,'exit'); server.stdin.end('\n'); await exited;
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
