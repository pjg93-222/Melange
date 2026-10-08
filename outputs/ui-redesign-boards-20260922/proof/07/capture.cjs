/* Build 07 proof capture (Loading: boards B20, L1-L4), re-runnable.

   node capture.cjs [port]        (default 8818; never 8806)

   Needs a READ-ONLY console on that port started from C:\Users\pgoff\Mentat:
     python mentat/app/server.py --port 8818 --read-only
   Every write the flow makes is answered here by page.route and never reaches
   the server: /api/session is answered with read_only:false so the page will
   send its roster, and /api/roster, /api/upload, /api/keys and /api/start are
   fulfilled from the fixtures below (their request bodies are recorded in
   measurements.json to show the payload shapes). /api/runs is the console's
   own answer with its coverage replaced by a board-like fixture (L4 draws one
   verified, one stale, several unverifiable and one not-collected cell; this
   computer's saved coverage is all unverifiable, captured separately as
   L4_real). Writes shots\<state>_<W>x<H>.png and measurements.json. */
'use strict';
const path = require('path');
const fs = require('fs');
const modules = path.join(process.env.USERPROFILE, '.cache', 'codex-runtimes', 'codex-primary-runtime', 'dependencies', 'node', 'node_modules');
const {chromium} = require(require.resolve('playwright', {paths: [modules]}));
const PORT = Number(process.argv[2] || 8818);
if ([8806, 8801, 8802, 8841].includes(PORT)) throw new Error('not your port');
const ORIGIN = `http://127.0.0.1:${PORT}`;
const OUT = __dirname, SHOTS = path.join(OUT, 'shots');
fs.mkdirSync(SHOTS, {recursive: true});
const SIZES = [[1440, 900], [1920, 1080]];

const bank = [
  ['Goldman Sachs Bank NA', ['Goldman Sachs & Co', 'GS Bank USA'], []],
  ['Wells Fargo Bank NA', ['Wells Fargo & Co'], []],
  ['Morgan Stanley Bank', ['Morgan Stanley & Co'], []],
  ['JP Morgan Chase Bank NA', ['JPMorgan Chase & Co', 'Chase Bank'], []],
  ['Bank of America NA', ['BofA', 'Merrill Lynch'], ['Merrill Lynch Wealth']],
  ['Citibank', ['Citigroup', 'Citi'], []],
  ['Citizens Bank', ['Citi'], []],
  ['US Bank NA', ['US BANK', 'US BANCORP'], []],
  ['PNC Bank', ['PNC BANK', 'PNC FINANCIAL'], []],
  ['Truist Bank', ['TRUIST', 'TRUIST FINANCIAL'], []],
];
function readiness(clean) {
  const rows = clean ? bank.map(([n, v, x]) => [n, v.filter(a => !(a === 'Citi' && n === 'Citizens Bank')), x]) : bank;
  const companies = rows.map(([name, variants, exclusions]) => ({company: name, variant_count: variants.length + 1,
    variants: [name, ...variants].map(variant => ({variant})), exclusion_count: exclusions.length, exclusions}));
  return {status: clean ? 'succeeded' : 'failed', mode: 'roster', readiness: [{industry: 'Banking', ready: clean,
    company_count: companies.length, variant_count: companies.reduce((n, c) => n + c.variant_count, 0), companies,
    parse_errors: [], duplicate_companies: clean ? [] : ['Wells Fargo Bank NA'],
    cross_company_variants: clean ? [] : [{variant: 'Citi', companies: ['Citibank', 'Citizens Bank']}]}]};
}
const csv = ['canonical_name,alias,sector,exclusion'];
for (const [name, variants, exclusions] of bank) { for (const v of variants) csv.push(`${name},${v},Banking,`); for (const x of exclusions) csv.push(`${name},,Banking,${x}`); }
const coverage = [
  ...['Banking', 'Community Banks', 'Credit Union', 'Crypto', 'Fintech', 'Telecom'].flatMap(industry => [2022, 2024, 2026].map(cycle => ({
    industry, cycle, freshness: 'unverifiable', verified_data_through: null, reason: 'The collection database or its coverage receipt is missing, unreadable or unverifiable.',
    run_name: industry + ' roster.csv', company_count: 10, evidence: [], latest_observed_transaction_date: industry === 'Credit Union' && cycle === 2026 ? '2026-09-08' : null}))),
].filter(r => !(r.industry === 'Telecom' && r.cycle === 2026));
Object.assign(coverage.find(r => r.industry === 'Banking' && r.cycle === 2022), {freshness: 'current', verified_data_through: '2022-12-31', lag_days: 0, target_date: '2022-12-31', reason: 'Verified FEC data-through covers the whole cycle.'});
Object.assign(coverage.find(r => r.industry === 'Community Banks' && r.cycle === 2024), {freshness: 'stale', verified_data_through: '2024-06-30', lag_days: 184, target_date: '2024-12-31', reason: 'The verified cutoff is behind the end of this past cycle.'});

(async () => {
  const browser = await chromium.launch({channel: 'chrome', headless: true});
  const out = {port: PORT, requests: {}, states: {}, errors: []};
  try {
    for (const [W, H] of SIZES) {
      const context = await browser.newContext({viewport: {width: W, height: H}});
      const page = await context.newPage();
      page.on('pageerror', e => out.errors.push(`${W}: ${e.message}`));
      let uploads = 0, realCoverage = false;
      await page.route('**/*', async route => { try {
        const req = route.request(), url = new URL(req.url());
        if (!req.url().startsWith(ORIGIN)) return route.abort();
        if (url.pathname === '/api/session') { const r = await route.fetch(); const body = await r.json(); return route.fulfill({json: {...body, read_only: false}}); }
        if (url.pathname === '/api/runs') { const r = await route.fetch(); const body = await r.json(); return route.fulfill({json: realCoverage ? body : {...body, coverage}}); }
        if (url.pathname === '/api/health') { const r = await route.fetch(); const body = await r.json(); return route.fulfill({json: {...body, on_disk_code_sha256_now: body.code_sha256, on_disk_assets_sha256_now: body.assets_sha256}}); }
        if (req.method() !== 'GET') {
          const body = req.postDataJSON();
          (out.requests[url.pathname] ||= []).push(url.pathname === '/api/upload' ? {filename: body.filename, content_bytes: Buffer.from(body.content, 'base64').length, keys: Object.keys(body)} : body);
          if (url.pathname === '/api/roster') return route.fulfill({json: {id: 'b'.repeat(32), name: 'Community banks roster.csv', state: 'ready', readiness: {status: 'succeeded', readiness: [{industry: body.sector, ready: true, company_count: body.companies.length, variant_count: body.companies.reduce((n, c) => n + 1 + c.aliases.length, 0), companies: body.companies.map(c => ({company: c.name, variant_count: 1 + c.aliases.length, variants: [c.name, ...c.aliases].map(variant => ({variant})), exclusions: []})), parse_errors: [], duplicate_companies: [], cross_company_variants: []}]}}});
          if (url.pathname === '/api/upload') { uploads++; const clean = uploads > 1; return route.fulfill({json: {id: (clean ? 'd' : 'c').repeat(32), name: body.filename, state: clean ? 'ready' : 'needs review', readiness: readiness(clean)}}); }
          if (url.pathname === '/api/keys') return route.fulfill({json: {active_key_count: 16, stored_key_count: 20}});
          if (url.pathname === '/api/start') return route.fulfill({json: {ok: true}});
          return route.abort();
        }
        return await route.continue();
      } catch (error) { await route.abort().catch(() => {}); } });
      await page.goto(ORIGIN + '/#loading');
      for (const asset of ['app.js', 'coverage-view.js', 'style.css']) await page.evaluate(a => fetch('/' + a, {cache: 'reload'}), asset);
      await page.evaluate(() => localStorage.setItem('mentat-roster-draft-v1', JSON.stringify({sector: 'Community banks', companies: [
        {name: 'Harborlight Credit Union', aliases: ['Harborlight CU', 'Harborlight Federal Credit Union']},
        {name: 'First Horizon Bank', aliases: ['First Horizon National Corp']},
        {name: 'Zions Bancorporation', aliases: ['Zions Bank', 'ZB NA']}]})));
      await page.reload();
      await page.waitForFunction(() => document.querySelector('.coverage-cell'));
      const shot = async name => { await page.evaluate(() => { document.activeElement?.blur(); for (const id of ['stale-banner', 'error']) { const el = document.getElementById(id); if (el) el.hidden = true; } }); await page.screenshot({path: path.join(SHOTS, `${name}_${W}x${H}.png`)}); };
      const measure = name => page.evaluate(() => { for (const id of ['stale-banner', 'error']) { const el = document.getElementById(id); if (el) el.hidden = true; }
        const r = s => { const e = document.querySelector(s); if (!e || !e.getClientRects().length) return null; const b = e.getBoundingClientRect(); return [Math.round(b.left * 10) / 10, Math.round(b.top * 10) / 10, Math.round(b.width * 10) / 10, Math.round(b.height * 10) / 10]; };
        const all = s => [...document.querySelectorAll(s)].filter(e => e.getClientRects().length).map(e => { const b = e.getBoundingClientRect(); return [Math.round(b.left), Math.round(b.top), Math.round(b.width), Math.round(b.height)]; });
        const gold = [...document.querySelectorAll('.primary--gold')].filter(e => e.getClientRects().length);
        return {title: r('#workspace-title'), intro: r('#view-loading .view-intro'), steps: all('.loading-step-mark'), labels: all('.loading-step-label'),
          main: r('.loading-main'), setup: r('.loading-setup'), mode: r('.loading-mode'), sector: r('#sector'), table: r('.loading-companies'), rows: all('.company-entry'),
          actions: all('.loading-editor-actions .secondary'), drop: r('#roster-drop'), gold: gold.map(e => { const b = e.getBoundingClientRect(); return {id: e.id, box: [Math.round(b.left), Math.round(b.top), Math.round(b.width), Math.round(b.height)], disabled: e.disabled}; }),
          back: r('#roster-back'), decisions: r('#roster-decisions'), cycles: all('.loading-cycle'), keys: r('.loading-keys'), coverage: r('.loading-coverage'), grid: r('.coverage-grid'), detail: r('.coverage-detail'),
          overflowX: document.documentElement.scrollWidth > innerWidth, scrollHeight: document.documentElement.scrollHeight,
          goldCount: gold.length, summary: document.getElementById('setup-summary').innerText, note: document.getElementById('setup-note').innerText,
          foot: r('#roster-upload:not([hidden]) .loading-upload-foot'), previewRows: all('.loading-preview tbody tr').map(b => b[3]),
          covChips: [...document.querySelectorAll('.coverage-cell:is([data-state=current],[data-state=stale]) .coverage-chip')].map(e => ({t: e.textContent, state: e.closest('.coverage-cell').dataset.state, pressed: e.closest('.coverage-cell').getAttribute('aria-pressed'), sw: e.scrollWidth, cw: e.clientWidth, fits: e.scrollWidth <= e.clientWidth}))};
      });
      // B20: step 1, typing names (the restored draft)
      await shot('B20_typing'); out.states[`B20_${W}`] = await measure();
      // Fix round (R07-3): Enter in #sector or a company name runs the review (implicit form submission)
      const enter = {};
      for (const target of ['#sector', '.company-entry .company-name']) {
        await page.locator(target).first().focus(); await page.keyboard.press('Enter');
        enter[target] = await page.waitForFunction(() => document.getElementById('roster-panel').dataset.step === '2', null, {timeout: 5000}).then(() => '2', () => document.getElementById('roster-panel').dataset.step);
        if (enter[target] === '2') { await page.click('#roster-back'); await page.waitForFunction(() => document.getElementById('roster-panel').dataset.step === '1'); }
      }
      out.states[`enter_${W}`] = enter;
      // L1: step 1 after an upload
      const file = path.join(OUT, 'Banking roster.csv'); fs.writeFileSync(file, csv.join('\r\n') + '\r\n');
      await page.setInputFiles('#file', file);
      await page.waitForFunction(() => !document.getElementById('upload-result').hidden && document.getElementById('upload-file-meta').textContent.includes('companies'));
      fs.rmSync(file); await shot('L1_upload'); out.states[`L1_${W}`] = await measure();
      // L2: step 2 with two open decisions
      await page.click('#review-roster'); await page.waitForSelector('#upload-review:not([hidden])');
      await shot('L2_decisions'); out.states[`L2_${W}`] = await measure();
      out.states[`L2_${W}`].chooseDisabled = await page.locator('#choose-cycles').isDisabled();
      // L2 settled: Keep for Citibank, then Remove the repeated Wells Fargo row -> the edited table is re-sent
      await page.click('button[data-action=keep][data-company="Citibank"]');
      await page.waitForFunction(() => !document.querySelector('#roster-decisions').hidden === false || document.querySelector('#roster-decisions').hidden);
      await page.waitForFunction(() => document.querySelector('#roster-decisions').hidden);
      await shot('L2_settled'); out.states[`L2settled_${W}`] = await measure();
      out.states[`L2settled_${W}`].chooseDisabled = await page.locator('#choose-cycles').isDisabled();
      // L3: step 3
      await page.click('#choose-cycles'); await page.waitForSelector('#loading-step-cycles:not([hidden])');
      await shot('L3_cycles'); out.states[`L3_${W}`] = await measure();
      // L4: the coverage grid with a cell selected
      await page.click('.coverage-cell[data-sector="Banking"][data-cycle="2026"]');
      await page.evaluate(() => document.querySelector('.loading-coverage').scrollIntoView({block: 'end'}));
      await page.evaluate(() => window.scrollBy(0, 0));
      await page.screenshot({path: path.join(SHOTS, `L4_grid_${W}x${H}.png`)}); out.states[`L4_${W}`] = await measure();
      out.states[`L4_${W}`].detailText = await page.locator('.coverage-detail').innerText();
      // Fix round (R07-1): the verified and stale chips while selected (2px border) keep their whole date
      for (const [sector, cycle] of [['Banking', 2022], ['Community Banks', 2024]]) {
        await page.click(`.coverage-cell[data-sector="${sector}"][data-cycle="${cycle}"]`);
        out.states[`L4_${W}`][`selected_${sector}_${cycle}`] = await page.evaluate(([s, c]) => { const e = document.querySelector(`.coverage-cell[data-sector="${s}"][data-cycle="${c}"] .coverage-chip`); return {t: e.textContent, sw: e.scrollWidth, cw: e.clientWidth, fits: e.scrollWidth <= e.clientWidth}; }, [sector, cycle]);
      }
      await page.click('.coverage-cell[data-sector="Banking"][data-cycle="2022"]');
      await page.evaluate(() => document.querySelector('.loading-coverage').scrollIntoView({block: 'end'}));
      await page.screenshot({path: path.join(SHOTS, `L4_verified_${W}x${H}.png`)});
      // L4 with this computer's own saved coverage
      realCoverage = true; await page.evaluate(() => window.scrollTo(0, 0));
      await page.waitForFunction(() => !document.querySelector('.coverage-cell[data-state=current]'), null, {timeout: 10000}).catch(() => {});
      await page.evaluate(() => document.querySelector('.loading-coverage').scrollIntoView({block: 'end'}));
      await page.screenshot({path: path.join(SHOTS, `L4_real_${W}x${H}.png`)});
      // Start collection: payload shape and step 4 (Collection)
      realCoverage = false; await page.evaluate(() => window.scrollTo(0, 0));
      await page.click('#start'); await page.waitForFunction(() => document.body.dataset.view === 'collection');
      out.states[`start_${W}`] = {view: await page.evaluate(() => document.body.dataset.view), stepAfter: await page.evaluate(() => document.getElementById('roster-panel').dataset.step)};
      // Reload restores the typed draft
      await page.evaluate(() => { location.hash = 'loading'; }); await page.reload(); await page.waitForSelector('.company-entry');
      out.states[`reload_${W}`] = await page.evaluate(() => ({sector: document.getElementById('sector').value, rows: [...document.querySelectorAll('.company-entry')].map(r => [r.querySelector('.company-name').value, [...r.querySelectorAll('.loading-alias')].map(c => c.dataset.value)])}));
      await context.close();
    }
  } finally { await browser.close(); }
  fs.writeFileSync(path.join(OUT, 'measurements.json'), JSON.stringify(out, null, 1));
  console.log('errors', out.errors.length, out.errors.slice(0, 5));
})();
