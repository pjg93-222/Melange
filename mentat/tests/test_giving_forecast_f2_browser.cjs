/* The cycle view of Forecast giving (board F2) in a real browser: the real console page and CSS (served by console_browser_fixture.py), the real
   giving-forecast.js, and the calculator's real responses (tests/fixtures/giving_forecast_f2_live*.json) answered by route stubs, so the data is
   exact and the run is deterministic. Every scenario runs on BOTH data paths:
     * the calculator as it was published before the model fix (no P1; a console that has not been updated still answers like this): unconditioned
       intervals and remainders, a budget_inconsistent Senate row;
     * the calculator with the model fix P1 (live): the same requests answered with the open cycle conditioned on the giving already observed.
   What is pinned here, beyond giving-forecast.js's own models (test_giving_forecast_f2.cjs): the header switch and the secondary Export button, the scope
   pill and its corrected sentence, the unset slider state and the request it sends, the drawn chart (one dollar basis, whisker and remainder from the right
   fields, nothing added across accounts), the candidate-mix bars and chips, the lobbying empty state, the footer line, "Sources and notes", the waiver chip,
   the loading and error states, reduced motion, and the one-column layout with no horizontal scroll at 390 px.
   Run: node tests/test_giving_forecast_f2_browser.cjs   (cwd: the checkout root; MENTAT_PYTHON = a python with the console's requirements;
   MENTAT_NODE_MODULES = a Playwright install, or the default ~/.cache/codex-runtimes/... path used by every other .cjs test here) */
'use strict';
const {test, before, after} = require('node:test');
const assert = require('node:assert/strict');
const {spawn} = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const modules = process.env.MENTAT_NODE_MODULES || path.join(os.homedir(), '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules');
const {chromium} = require(require.resolve('playwright', {paths: [modules]}));

const LEGACY = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'giving_forecast_f2_live.json'), 'utf8'));
const WITH_P1 = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'giving_forecast_f2_live_p1.json'), 'utf8'));
const LANDED = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'giving_forecast_f2_live_landed.json'), 'utf8'));   // the live calculator's whole catalog and answers
const PATHS = {legacy: LEGACY.runs, p1: WITH_P1.runs, landed: LANDED.runs};
const BUDGET_TEXT = 'Budget inconsistent — revise scenario';
const RANGE_TEXT = 'An input is outside the range this model was fitted on.';
const INTERVAL_TEXT = "Mentat's own last change for this series was far outside this band; treat the band as too narrow.";
const WIDE_TEXT = 'Share interval extends outside 0-100% (linear share model on a thin base); treat it as unreliable.';
// What the pill's tooltip, its aria-label, the status line and the notes say follows the run they describe (owner review 2026-10-01): where the calculator conditions the open
// cycle on the giving already observed the drawn amounts differ from the Mentat level, and the sentence says why instead of claiming they are equal.
const EXAMPLE_HEAD = "The model's change in the amounts is zero (growth and control as in 2023–2024).";
const EXAMPLE_MIXES = "Party mixes also move: 2026 is a midterm, and the blank prior-cycle growth uses 2024's growth, which is outside the range the share models were fitted on.";
const EXAMPLE_PLAIN = `${EXAMPLE_HEAD} The 2025–2026 amounts equal the 2023–2024 Mentat level. ${EXAMPLE_MIXES}`;
const EXAMPLE_CONDITIONED = `${EXAMPLE_HEAD} The 2025–2026 amounts differ from the 2023–2024 Mentat level only because they are conditioned on the giving already observed. ${EXAMPLE_MIXES}`;
// The saved 2026 outlook behind the two control rows, as the catalog describes it.
const SAVED_TEXT = 'Saved outlook · Polymarket Jan–Jun · as of 2026-09-24';
const money = value => new Intl.NumberFormat('en-US', {style: 'currency', currency: 'USD', notation: 'compact', maximumFractionDigits: 2}).format(Math.abs(value) < 0.005 ? 0 : value);
const num = value => (Math.abs(value) < 0.005 ? 0 : value).toLocaleString('en-US', {maximumFractionDigits: 2});
const sgn = value => (value >= 0.005 ? '+' : '') + num(value);
const REGISTRY_WAIVERS = [
  {gate: 'G6', cell: 'lobby / commercial_banks', term: 'lobby', industry: 'commercial_banks', reason: 'owner ruling: keep log refit', owner: 'Paul Goff', date: '2026-09-30', show_warning: false},
  {gate: 'G6', cell: 'control_House / commercial_banks', term: 'control_House', industry: 'commercial_banks', reason: 'Owner explicitly authorized the three House-share LOEO degradations: "Waive these three cells and publish".', owner: 'Paul Goff', date: '2026-09-30', show_warning: true},
  {gate: 'G6', cell: 'control_House / credit_unions', term: 'control_House', industry: 'credit_unions', reason: 'Owner explicitly authorized the three House-share LOEO degradations: "Waive these three cells and publish".', owner: 'Paul Goff', date: '2026-09-30', show_warning: true},
  {gate: 'G6', cell: 'control_House / auto_light_duty_manufacturing', term: 'control_House', industry: 'auto_light_duty_manufacturing', reason: 'Owner explicitly authorized the three House-share LOEO degradations: "Waive these three cells and publish".', owner: 'Paul Goff', date: '2026-09-30', show_warning: true}];

// The entry the live calculator carries in its catalog for the House share of commercial banks (display text, published and comparator values with their unit).
const DISPLAY_WAIVER = JSON.parse(JSON.stringify(LANDED.catalog.waivers.find(w => w.industry === 'commercial_banks' && w.chamber === 'House' && w.show_warning === true)));
const measuredText = w => `Measured.*published ${w.published_value.toFixed(3)} pp . comparator ${w.comparator_value.toFixed(3)} pp`;

let fixture, origin, browser;
const stderr = [];
before(async () => {
  fixture = spawn(process.env.MENTAT_PYTHON || 'python', [path.join(__dirname, 'console_browser_fixture.py')], {stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true});
  fixture.stderr.on('data', chunk => stderr.push(chunk.toString()));
  origin = await new Promise((resolve, reject) => {
    let output = '';
    fixture.stdout.on('data', chunk => { output += chunk; if (output.includes('\n')) resolve(output.trim().split('\n')[0]); });
    fixture.on('exit', code => reject(new Error(`Fixture exited ${code}: ${stderr.join('')}`)));
    fixture.on('error', reject);
  });
  browser = await chromium.launch({headless: true, channel: process.env.MENTAT_BROWSER_CHANNEL || 'chrome'});
});
after(async () => {
  if (browser) await browser.close();
  if (fixture) { fixture.stdin.write('\n'); fixture.stdin.end(); setTimeout(() => fixture.kill(), 3000).unref(); }
});

// The run the calculator would answer to a request: the same selection the console's own examples use (blank growth -> nothing entered, lobbying entered -> the lobbying run).
function answerFor(runs, body) {
  const horizons = Object.values(body.horizons);
  const blank = horizons.every(h => h.growth_pct === '' || h.growth_pct == null);
  const lobbying = horizons.some(h => Object.values(h.annual_forecast_changes || {}).some(v => v !== '' && v != null));
  if (body.industry === 'property_casualty') return runs.property_casualty;
  if (body.industry === 'credit_unions') return lobbying ? runs.credit_unions_lobby : runs.credit_unions;
  if (blank) return runs.banks_blank;
  return lobbying ? runs.banks_lobby : runs.banks;
}

/* A page on the real console with the forecast calls stubbed. options: path ('legacy' | 'p1'), width, height, waivers, reducedMotion, delay (ms), failure (status). */
async function open(options = {}) {
  const {path: dataPath = 'legacy', width = 1600, height = 900, waivers = null, reducedMotion = 'no-preference', delay = 0, failure = 0, malformed = false} = options;
  const context = await browser.newContext({viewport: {width, height}, deviceScaleFactor: 1, reducedMotion, acceptDownloads: true});
  const page = await context.newPage();
  page.errors = []; page.requests = []; page.setDefaultTimeout(20000);
  page.on('pageerror', error => page.errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error' && !/Failed to load resource/.test(message.text())) page.errors.push(message.text()); });
  const catalog = JSON.parse(JSON.stringify(dataPath === 'landed' ? LANDED.catalog : LEGACY.catalog));
  if (dataPath === 'p1') catalog.waivers = WITH_P1.catalog_waivers;       // the one key the model fix adds to the catalog
  if (waivers) catalog.waivers = waivers;
  page.stub = {catalog, runs: PATHS[dataPath], delay, failure, malformed};
  await page.route('**/api/forecast/catalog', route => route.fulfill({json: page.stub.catalog}));
  await page.route('**/api/forecast/project', async route => {
    const body = route.request().postDataJSON();
    page.requests.push(body);
    if (page.stub.delay) await new Promise(resolve => setTimeout(resolve, page.stub.delay));
    if (page.stub.failure) return route.fulfill({status: page.stub.failure, json: {error: 'The forecast service could not finish this calculation.'}});
    if (page.stub.malformed) return route.fulfill({json: {status: 'ready', industry_label: 'Commercial banks', horizons: [{}, {}], anchors: {}, notices: []}});
    return route.fulfill({json: answerFor(page.stub.runs, body)});
  });
  await page.route('**/api/insights/catalog', route => route.fulfill({json: {datasets: [{id: 'Credit Union Sample', label: 'Credit Union Sample', available: true}], panels: []}}));
  await page.route('**/api/insights/query', route => route.fulfill({json: {status: 'ready', scope: {}, panels: {}, options: {}, provenance: {}, notices: []}}));
  await page.goto(origin + '/#insights');
  await page.waitForSelector('#giving-forecast-open', {state: 'visible'});
  await page.click('#giving-forecast-open');
  await page.waitForSelector('#gf-form:not([hidden])');
  await settled(page);
  return page;
}
// The chart has drawn (an svg or an empty message) and no calculation is running.
const settled = page => page.waitForFunction(() => {
  const chart = document.getElementById('gf-chart');
  return chart && chart.getAttribute('aria-busy') === 'false' && (chart.querySelector('svg') || (chart.querySelector('.gf-chart-empty') && !/Loading/.test(chart.textContent)));
});
async function calculate(page) {
  await page.click('#gf-calculate');
  await page.waitForFunction(() => document.getElementById('gf-chart').getAttribute('aria-busy') === 'false' && !document.getElementById('gf-calculate').disabled);
  await page.waitForTimeout(250);
}
const example = async page => { await page.click('#gf-reference'); await page.waitForTimeout(120); };
const chartText = page => page.$eval('#gf-chart svg', el => el.textContent);
const closePage = page => page.context().close();
const lastRequest = page => page.requests[page.requests.length - 1];
const noHorizontalScroll = page => page.evaluate(() => ({scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth}));
async function hoverTip(page, selector, options = {}) {
  // Scroll first and let the scroll settle: a scroll hides the tooltip (by design), and Playwright scrolls an element into view before it hovers.
  const target = page.locator(selector).first();
  await target.scrollIntoViewIfNeeded();
  await page.waitForTimeout(80);
  await target.hover(options);
  await page.waitForSelector('#gf-tip:not([hidden])');
  return page.$eval('#gf-tip', el => el.textContent);
}

for (const dataPath of ['legacy', 'p1']) {
  const withFix = dataPath === 'p1';
  const label = withFix ? 'with the model fix P1' : 'without the model fix';

  test(`[${label}] header: Observed insights | Forecast giving, and Export scenario as a secondary button that waits for a calculation`, async () => {
    const page = await open({path: dataPath});
    try {
      assert.equal(await page.getAttribute('#giving-forecast-open', 'aria-pressed'), 'true');
      assert.equal(await page.getAttribute('#gf-view-insights', 'aria-pressed'), 'false');
      assert.equal(await page.$eval('#giving-forecast', el => el.hidden), false);
      const style = await page.$eval('#gf-export', el => { const s = getComputedStyle(el); return {background: s.backgroundColor, color: s.color, border: s.borderTopWidth + ' ' + s.borderTopStyle, height: s.height, primary: el.classList.contains('primary'), secondary: el.classList.contains('secondary'), hidden: el.hidden, disabled: el.disabled}; });
      assert.equal(style.primary, false, 'not a second plum primary next to Calculate');
      assert.equal(style.secondary, true);
      assert.equal(style.background, 'rgb(255, 255, 255)');
      assert.equal(style.color, 'rgb(52, 38, 73)', 'plum text');
      assert.match(style.border, /^1px solid/, 'hairline');
      assert.equal(style.height, '34px', 'as tall as the segmented control');
      assert.equal(style.hidden, false); assert.equal(style.disabled, true, 'no scenario yet');
      const switchHeight = await page.$eval('#gf-view-switch', el => getComputedStyle(el).height);
      assert.equal(switchHeight, '34px');
      const calc = await page.$eval('#gf-calculate', el => getComputedStyle(el).backgroundColor);
      assert.equal(calc, 'rgb(52, 38, 73)', 'Calculate is the one plum primary');
      await example(page); await calculate(page);
      assert.equal(await page.$eval('#gf-export', el => el.disabled), false, 'a calculated scenario can be exported');
      // the two segments switch the Insights sub-view exactly as before
      await page.click('#gf-view-insights');
      assert.equal(await page.$eval('#giving-forecast', el => el.hidden), true);
      assert.equal(await page.$eval('#gf-export', el => el.hidden), true, 'Export scenario belongs to the forecast view');
      assert.equal(await page.$eval('#insights-controls', el => getComputedStyle(el).display !== 'none'), true, 'the observed-insights scope is back');
      await page.click('#giving-forecast-open');
      assert.equal(await page.$eval('#giving-forecast', el => el.hidden), false);
      assert.deepEqual(page.errors, []);
    } finally { await closePage(page); }
  });

  test(`[${label}] the unset slider state: a blank input shows "-", a hollow thumb and a muted track, and the request sends no value for it`, async () => {
    const page = await open({path: dataPath});
    try {
      const growth = await page.$eval('#gf-2026-growth-view', el => ({value: el.value, placeholder: el.placeholder}));
      assert.equal(growth.value, '');
      assert.equal(growth.placeholder, '-');
      const sliders = await page.$$eval('#gf-panel-current .gf-slider', all => all.map(el => ({unset: el.classList.contains('is-unset'), text: el.getAttribute('aria-valuetext'), fill: getComputedStyle(el.querySelector('.gf-fill')).width, thumb: getComputedStyle(el.querySelector('.gf-thumb')).borderTopStyle})));
      assert.equal(sliders[0].unset, true, 'revenue growth is unset');
      assert.equal(sliders[0].text, 'Not set');
      assert.equal(sliders[0].fill, '0px', 'no plum fill');
      assert.equal(sliders[0].thumb, 'dashed', 'a hollow thumb');
      await page.click('#gf-tab-next');
      assert.deepEqual(await page.$$eval('#gf-panel-next .gf-slider', all => all.map(el => el.classList.contains('is-unset'))), [true, true, true], '2027-2028: growth and both control scores are unset');
      await page.click('#gf-calculate');
      await page.waitForFunction(() => document.getElementById('gf-chart').getAttribute('aria-busy') === 'false');
      await page.click('#gf-tab-current');
      const body = lastRequest(page);
      for (const end of ['2026', '2028']) {
        assert.equal(body.horizons[end].growth_pct, '', 'no growth is invented for ' + end);
        assert.equal(body.horizons[end].prior_growth_pct, '');
      }
      assert.equal(body.horizons['2028'].control_scores.House, '');
      assert.equal(body.horizons['2028'].control_scores.Senate, '');
      assert.equal(body.horizons['2028'].current_control.House, '');
      assert.match(await page.$eval('#gf-status', el => el.textContent), /Both horizons calculated/);
      // typing a number sets it; clearing it returns to the unset state and to the empty value in the request
      await page.fill('#gf-2026-growth-view', '10');
      assert.equal(await page.$eval('#gf-2026-growth', el => el.value), '10');
      assert.equal(await page.$eval('#gf-panel-current .gf-slider', el => el.classList.contains('is-unset')), false);
      await page.fill('#gf-2026-growth-view', '');
      assert.equal(await page.$eval('#gf-2026-growth', el => el.value), '');
      assert.equal(await page.$eval('#gf-panel-current .gf-slider', el => el.classList.contains('is-unset')), true);
      // the keyboard works the slider: an arrow key on an unset slider starts at its minimum span step, Delete clears it
      await page.focus('#gf-panel-current .gf-slider');
      await page.keyboard.press('ArrowRight');
      assert.notEqual(await page.$eval('#gf-2026-growth', el => el.value), '');
      await page.keyboard.press('Delete');
      assert.equal(await page.$eval('#gf-2026-growth', el => el.value), '');
      assert.deepEqual(page.errors, []);
    } finally { await closePage(page); }
  });

  test(`[${label}] the saved outlook: the two 2026 control rows open filled with their source beside them and clear back to the unset state; every other input opens blank`, async () => {
    const page = await open({path: dataPath});
    try {
      const snapshot = (dataPath === 'landed' ? LANDED : LEGACY).catalog.saved_outlook;
      const rowState = chamber => page.evaluate(chamber => {
        const view = document.getElementById(`gf-2026-${chamber}-political-view`), pill = document.getElementById(`gf-2026-${chamber}-majority`), source = document.getElementById(`gf-2026-${chamber}-source`);
        const slider = view.closest('.gf-row').querySelector('.gf-slider'), clear = view.closest('.gf-row').querySelector('.gf-source-clear');
        const visible = el => { const s = getComputedStyle(el), r = el.getBoundingClientRect(); return s.visibility !== 'hidden' && r.width > 0 && r.height > 0; };
        return {shown: view.value, held: document.getElementById(`gf-2026-${chamber}-political`).value, pill: pill.value, pillText: pill.options[pill.selectedIndex].text, caption: source.textContent, captionVisible: visible(source), clearVisible: visible(clear),
          unset: slider.classList.contains('is-unset'), valuetext: slider.getAttribute('aria-valuetext'), focused: document.activeElement === view, title: source.title};
      }, chamber);
      // the open state: filled from the saved outlook, with the source and the date from the catalog beside each row; growth, prior-cycle growth and the whole 2027-2028 tab blank
      for (const chamber of ['House', 'Senate']) {
        const s = await rowState(chamber), saved = snapshot.control[chamber];
        assert.equal(Number(s.held), saved.value, chamber); assert.equal(s.shown, num(saved.value), chamber + ': the visible number is the saved one');
        assert.equal(s.pill, String(saved.current_control)); assert.equal(s.pillText, 'Republican');
        assert.equal(s.caption, SAVED_TEXT); assert.equal(s.captionVisible, true); assert.equal(s.clearVisible, true); assert.equal(s.unset, false);
        assert.match(s.title, /^Saved 2026 outlook, as of 2026-09-24: Polymarket mean of the daily probability of Republican control from 2026-01-01 to 2026-06-30\./);
      }
      assert.equal(await page.$eval('#gf-2026-growth-view', el => el.value), ''); assert.equal(await page.$eval('#gf-2026-prior', el => el.value), '');
      await page.click('#gf-tab-next');
      assert.deepEqual(await page.$$eval('#gf-panel-next .gf-numbox input', all => all.map(el => el.value)), ['', '', ''], '2027-2028: growth and both control scores are blank');
      assert.deepEqual(await page.$$eval('#gf-panel-next .gf-pill-select', all => all.map(el => el.value)), ['', ''], '... and both pills read Choose');
      assert.equal(await page.$$eval('#gf-panel-next .gf-source', all => all.length), 0, 'no saved outlook is claimed for 2027-2028');
      await page.click('#gf-tab-current');
      // Calculate sends the saved scores and pills for 2026 and nothing for the rest
      const place = () => page.$eval('#gf-calculate', el => Math.round(el.getBoundingClientRect().top * 10) / 10);
      const calcAt = await place();
      await calculate(page);
      const first = lastRequest(page);
      assert.equal(Number(first.horizons['2026'].control_scores.House), snapshot.control.House.value); assert.equal(first.horizons['2026'].current_control.House, String(snapshot.control.House.current_control));
      assert.equal(Number(first.horizons['2026'].control_scores.Senate), snapshot.control.Senate.value);
      assert.equal(first.horizons['2026'].growth_pct, ''); assert.deepEqual({...first.horizons['2028'].control_scores}, {House: '', Senate: ''}); assert.deepEqual({...first.horizons['2028'].current_control}, {House: '', Senate: ''});
      // clear the House row: the score and the pill go back to the real unset state ("-", a hollow thumb, Choose); the Senate row is untouched; nothing below moves
      await page.click('[aria-label="Clear the saved House control score and its control before the election: leave both unset"]');
      const house = await rowState('House'), senate = await rowState('Senate');
      assert.deepEqual({shown: house.shown, held: house.held, pill: house.pill, pillText: house.pillText, unset: house.unset, valuetext: house.valuetext, focused: house.focused}, {shown: '', held: '', pill: '', pillText: 'Choose', unset: true, valuetext: 'Not set', focused: true});
      assert.equal(await page.$eval('#gf-2026-House-political-view', el => el.placeholder), '-');
      assert.equal(house.captionVisible, false, 'the caption goes quiet with the value it described'); assert.equal(house.clearVisible, false);
      assert.deepEqual({held: Number(senate.held), pill: senate.pill, captionVisible: senate.captionVisible, unset: senate.unset}, {held: snapshot.control.Senate.value, pill: String(snapshot.control.Senate.current_control), captionVisible: true, unset: false});
      assert.equal(await place(), calcAt, 'the panel keeps its height: Calculate does not move');
      await calculate(page);
      const cleared = lastRequest(page);
      assert.equal(cleared.horizons['2026'].control_scores.House, ''); assert.equal(cleared.horizons['2026'].current_control.House, '', 'clearing sends no value');
      assert.equal(Number(cleared.horizons['2026'].control_scores.Senate), snapshot.control.Senate.value);
      // typing in the cleared row does not bring the claim back; editing the Senate score ends its claim; neither moves the panel
      await page.fill('#gf-2026-House-political-view', '40');
      assert.equal((await rowState('House')).captionVisible, false);
      await page.fill('#gf-2026-Senate-political-view', '60');
      const edited = await rowState('Senate');
      assert.deepEqual({captionVisible: edited.captionVisible, clearVisible: edited.clearVisible, held: edited.held}, {captionVisible: false, clearVisible: false, held: '60'});
      assert.equal(await place(), calcAt);
      // the other horizon's tab does not move Calculate either (both tab panels share one cell)
      await page.click('#gf-tab-next'); assert.equal(await place(), calcAt, 'switching the horizon keeps Calculate where it is');
      await page.click('#gf-tab-current');
      // the historical example puts the anchor cycle's values in both rows: they are not the saved outlook, so the captions stay quiet
      await example(page);
      for (const chamber of ['House', 'Senate']) { const s = await rowState(chamber); assert.equal(s.captionVisible, false, chamber); assert.equal(s.clearVisible, false, chamber); }
      assert.equal(await page.$eval('#gf-2026-House-political-view', el => el.value), '44.92');
      assert.deepEqual(page.errors, []);
    } finally { await closePage(page); }
  });

  test(`[${label}] the historical example: the scope pill and its sentence follow the run (the model's change is zero; the drawn amounts equal the Mentat level only where nothing conditions them; the party mixes still move)`, async () => {
    const page = await open({path: dataPath});
    try {
      assert.equal(await page.$eval('#gf-example-pill', el => el.hidden), true, 'the pill is shown only while the example is loaded');
      await example(page);
      assert.equal(await page.$eval('#gf-example-pill', el => el.hidden), false);
      assert.equal(await page.textContent('#gf-example-pill'), 'Historical example: 2023–2024 growth and control');
      const sentence = withFix ? EXAMPLE_CONDITIONED : EXAMPLE_PLAIN;
      const tip = await hoverTip(page, '#gf-example-pill');
      assert.ok(tip.includes(sentence), 'the tooltip carries the sentence of this calculator: ' + tip);
      assert.doesNotMatch(tip, /so the projection equals/);
      if (withFix) {
        assert.match(tip, /House change in R share, model, before conditioning on the giving already observed-1\.63 pp .*presidential or midterm cycle -1\.88 pp/);
        assert.match(tip, /Senate change in R share, model, before conditioning on the giving already observed\+6\.06 pp .*prior-cycle growth \+6\.06 pp/);
        assert.doesNotMatch(tip, /drawn/, 'nothing is drawn before Calculate, so the tooltip claims no drawn change yet');
      } else assert.doesNotMatch(tip, /change in R share/, 'a calculator without the fix names no input and conditions nothing');
      assert.equal(await page.$eval('#gf-status', el => el.textContent), 'Anchor-cycle values loaded as an example: growth and control as in 2023–2024. ' + sentence + ' Change them to explore.');
      assert.match(await page.$eval('#gf-example-pill', el => el.getAttribute('aria-label')), new RegExp(sentence.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')), 'the aria-label carries it too');
      await page.click('#gf-notes-toggle');
      assert.equal(await page.textContent('#gf-example-note'), sentence, 'also in Sources and notes');
      assert.doesNotMatch(await page.textContent('#giving-forecast'), /so the projection equals the Mentat level/);
      await page.click('#gf-notes-toggle');
      // calculated: the sentence agrees with the amounts DRAWN beside it (the total of 2025-2026 against the Mentat level), and the tooltip prints the change drawn per basis
      await calculate(page);
      const measure = answerFor(page.stub.runs, lastRequest(page)).horizons[0].pac.measures.find(m => m.id === 'general_giving');
      const total = withFix ? measure.cycle_given_observed_median : measure.projected_cycle_real_2025, level = measure.anchor_cycle_real_2025;
      assert.ok(await chartText(page).then(text => text.includes(money(total)) && text.includes(money(level))), 'the chart draws the total and the level compared here: ' + money(total) + ' and ' + money(level));
      const equal = Math.abs(total - level) < 0.5;
      assert.equal(equal, !withFix, 'with the fix the drawn total differs from the level, without it it equals it');
      const note = await page.$eval('#gf-example-note', el => el.textContent);
      if (equal) assert.match(note, /The 2025–2026 amounts equal the 2023–2024 Mentat level\./); else assert.match(note, /differ from the 2023–2024 Mentat level only because they are conditioned on the giving already observed\./);
      if (withFix) {
        const bars = await page.$$eval('#gf-senate-body .gf-bar-label', all => all.map(el => parseFloat(el.textContent))), caption = await page.textContent('#gf-senate-foot .gf-mix-caption');
        const anchors = caption.match(/-?[\d.]+(?=%)/g).map(Number), names = ['Employees', 'Roster PACs'];
        const expected = names.map((name, i) => `${name} ${num(anchors[i])}% to ${num(bars[i])}% (${sgn(Number(num(bars[i])) - Number(num(anchors[i])))} pp)`).join(' · ');
        const after = await hoverTip(page, '#gf-example-pill');
        assert.ok(after.includes('Senate change in R share, drawn (conditioned)' + expected), 'the bars drawn say ' + expected + ': ' + after);
        assert.ok(after.includes('Senate change in R share, model, before conditioning on the giving already observed'));
      }
      // changing an input ends the example: the pill goes
      await page.fill('#gf-2026-growth-view', '12');
      assert.equal(await page.$eval('#gf-example-pill', el => el.hidden), true);
      assert.deepEqual(page.errors, []);
    } finally { await closePage(page); }
  });

  test(`[${label}] the chart: one dollar basis, the whisker and the remainder from the right fields, observed at face value`, async () => {
    const page = await open({path: dataPath});
    try {
      await example(page); await calculate(page);
      const text = await chartText(page);
      assert.match(await page.textContent('#gf-basis'), /2025 dollars/);
      // the three columns, each with its x label; the 2023-2024 column is the Mentat level in 2025 dollars ($27.18M), not the nominal $26.11M
      assert.match(text, /2023–2024Mentat level/);
      assert.match(text, /2025–2026/); assert.match(text, /2027–2028/);
      assert.ok(text.includes('$27.18M'));
      assert.ok(!text.includes('$26.11M'), 'the nominal amount is in the tooltip, not on the chart');
      assert.ok(text.includes('$11.57M') && /observed to Jun 30/.test(text));
      if (withFix) {
        assert.ok(text.includes('$15.63M') && /remainder/.test(text), 'conditioned remainder');
        assert.ok(text.includes('$17.37M') && text.includes('$43.13M'), 'conditioned whisker: $17.37M to $43.13M');
        assert.ok(!text.includes('$17.13M'), 'the unconditioned low end is not drawn');
      } else {
        assert.ok(text.includes('$15.61M') && /remainder/.test(text));
        assert.ok(text.includes('$17.13M') && text.includes('$43.12M'), 'the returned interval, as returned');
      }
      assert.ok(text.includes('$52.2M') && text.includes('$14.15M'), '2027-2028: interval top and bottom');
      assert.equal(await page.$$eval('#gf-chart .gf-col-observed', all => all.length), 1);
      assert.equal(await page.$$eval('#gf-chart .gf-col-remainder', all => all.length), 1);
      assert.equal(await page.$$eval('#gf-chart .gf-col-projection', all => all.length), 1);
      assert.equal(await page.$$eval('#gf-chart .gf-whisker', all => all.length), 2, 'one whisker beside the open cycle and one through the next');
      // hover: the observed segment, the remainder, the whisker and the anchor column each carry a tooltip
      assert.match(await hoverTip(page, '#gf-chart .gf-mark-current .gf-col-observed'), /Observed through2026-06-30/);
      assert.match(await hoverTip(page, '#gf-chart .gf-mark-current .gf-col-remainder'), withFix ? /Remainder, median \(given the giving already observed\)\$15\.63M/ : /Projected remainder\$15\.61M/);
      assert.match(await hoverTip(page, '#gf-chart .gf-mark-current .gf-whisker .gf-hit'), /95% prediction interval/);
      const anchorTip = await hoverTip(page, '#gf-chart .gf-mark-anchor .gf-col-anchor');
      assert.match(anchorTip, /In 2025 USD \(this chart\)\$27\.18M/);
      assert.match(anchorTip, /Nominal\$26\.11M/);
      await page.mouse.move(5, 5);
      await page.waitForSelector('#gf-tip', {state: 'hidden'});
      assert.deepEqual(page.errors, []);
    } finally { await closePage(page); }
  });

  test(`[${label}] PAC giving and general giving are switched, never stacked or added; the amber state exists only without the model fix`, async () => {
    const page = await open({path: dataPath});
    try {
      await example(page); await calculate(page);
      assert.equal(await page.getAttribute('#gf-account-general', 'aria-pressed'), 'true');
      const general = await chartText(page);
      await page.click('#gf-account-pac');
      assert.equal(await page.getAttribute('#gf-account-pac', 'aria-pressed'), 'true');
      assert.equal(await page.getAttribute('#gf-account-general', 'aria-pressed'), 'false');
      await page.waitForTimeout(900);
      const pac = await chartText(page);
      assert.notEqual(pac, general);
      assert.equal(await page.$$eval('#gf-chart .gf-col-anchor', all => all.length), 1, 'one set of columns, not two stacked accounts');
      // the PAC account: the roster PACs' own giving; its anchor level is not the general-giving level and not their sum
      assert.ok(!pac.includes('$27.18M'));
      assert.ok(pac.includes('$5.93M'), 'the anchor level of the roster PACs own giving, in 2025 dollars');
      assert.ok(!pac.includes('$55M') && !pac.includes('$33.1'), 'no sum of the two accounts and no shared scale');
      const flags = await page.$$eval('#gf-chart-flags .gf-chip', all => all.map(el => ({text: el.textContent, amber: el.classList.contains('gf-chip-warn')})));
      if (withFix) {
        assert.deepEqual(flags.filter(f => f.amber), [], 'nothing amber: the interval is conditioned on the giving already observed');
        assert.ok(pac.includes('$4.78M') && pac.includes('$9.58M'), 'conditioned interval of the roster PACs: $4.78M to $9.58M');
        assert.ok(!pac.includes('$3.74M'));
      } else {
        const amber = flags.filter(f => f.amber);
        assert.equal(amber.length, 1);
        assert.match(amber[0].text, /Prediction interval starts below giving already observed/);
        assert.ok(pac.includes('$3.74M') && pac.includes('$9.4M'), 'the unconditioned interval, drawn as returned: $3.74M to $9.4M (below the $4.67M observed)');
        assert.match(await hoverTip(page, '#gf-chart-flags .gf-chip-warn'), /not clipped/);
      }
      assert.deepEqual(page.errors, []);
    } finally { await closePage(page); }
  });

  test(`[${label}] the candidate-mix cards: the bar is a full-cycle share; the amber budget state belongs to the calculator without the fix, the conditioned figures to the fix`, async () => {
    const page = await open({path: dataPath});
    try {
      await example(page); await calculate(page);
      const bars = async chamber => page.$$eval(`#gf-${chamber}-body .gf-bar`, all => all.map(el => ({label: el.textContent.trim(), flagged: el.classList.contains('is-flagged')})));
      const house = await bars('house'), senate = await bars('senate');
      assert.deepEqual(house.map(b => b.label), withFix ? ['29.56% R', '52.7% R'] : ['32.72% R', '52.73% R']);
      assert.deepEqual(senate.map(b => b.label), withFix ? ['48.17% R', '75.76% R'] : ['57.5% R', '70.56% R']);
      assert.deepEqual(house.map(b => b.flagged), [false, false]);
      const senateChips = await page.$$eval('#gf-senate-foot .gf-chip', all => all.map(el => ({text: el.textContent.trim(), amber: el.classList.contains('gf-chip-warn')})));
      const houseChips = await page.$$eval('#gf-house-foot .gf-chip', all => all.map(el => ({text: el.textContent.trim(), amber: el.classList.contains('gf-chip-warn')})));
      assert.ok(houseChips.some(c => c.text === RANGE_TEXT && !c.amber), 'out-of-range input: neutral, the model\'s sentence');
      if (withFix) {
        assert.deepEqual(senate.map(b => b.flagged), [false, false], 'no amber outline: the remaining amounts are not negative');
        assert.deepEqual(senateChips.filter(c => c.amber), []);
        assert.deepEqual(senateChips.map(c => c.text), [RANGE_TEXT], 'the conditioned row has no chip of its own: its tooltip says what was conditioned');
        assert.match(await hoverTip(page, '#gf-senate-body .gf-bar >> nth=1'), /Remaining from 2026-07-01 \(median\)R \$150\.68K · D \$62\.88K of \$213\.56K/);
      } else {
        assert.deepEqual(senate.map(b => b.flagged), [false, true], 'the budget_inconsistent row is outlined');
        assert.deepEqual(senateChips.filter(c => c.amber).map(c => c.text), [BUDGET_TEXT]);
        assert.match(await hoverTip(page, '#gf-senate-foot .gf-chip-warn'), /budget_inconsistent: The projected total and share are incompatible/);
        assert.match(await hoverTip(page, '#gf-senate-body .gf-bar >> nth=1'), /R -\$135\.67K · D \$32\.16K/);
      }
      // the 2027-2028 full-cycle share is the teal tick with its label; the caption is the anchor cycle's share
      assert.equal(await page.$$eval('#gf-house-body .gf-tick', all => all.length), 2);
      assert.deepEqual(await page.$$eval('#gf-house-body .gf-tick-label', all => all.map(el => el.textContent)), ['34.59%', '54.61%']);
      assert.equal(await page.textContent('#gf-house-foot .gf-mix-caption'), '2023–2024: 34.35% and 54.36%');
      assert.equal(await page.$$eval('#gf-house-body .gf-bar', all => all.length), 2, 'two bases, never a pooled third');
      assert.doesNotMatch(await page.textContent('#gf-house'), /combined|pooled/i);
      // the tooltip of a bar agrees with the bar: the change printed is the one between the caption's share and the bar's label as displayed; with the fix the model's own change
      // (before conditioning) is labelled as such next to it
      for (const chamber of ['house', 'senate']) {
        const bars = await page.$$eval(`#gf-${chamber}-body .gf-bar-label`, all => all.map(el => parseFloat(el.textContent)));
        const anchors = (await page.textContent(`#gf-${chamber}-foot .gf-mix-caption`)).match(/-?[\d.]+(?=%)/g).map(Number);
        for (let i = 0; i < bars.length; i++) {
          const drawn = sgn(Number(num(bars[i])) - Number(num(anchors[i]))) + ' pp', tipText = await hoverTip(page, `#gf-${chamber}-body .gf-bar >> nth=${i}`);
          if (withFix) {
            assert.ok(tipText.includes('Change in Republican share, drawn (conditioned)' + drawn), `${chamber} bar ${i}: the tooltip says ${drawn}: ${tipText}`);
            assert.match(tipText, /Model change before conditioning on the giving already observed[+-]?[\d.]+ pp on each basis/);
          } else {
            assert.match(tipText, new RegExp('Change in Republican share' + drawn.replace(/[+.]/g, '\\$&').replace(' pp', ' pp on each basis')), `${chamber} bar ${i}: the printed change is the drawn one (${drawn}): ${tipText}`);
            assert.doesNotMatch(tipText, /before conditioning/);
          }
        }
      }
      assert.deepEqual(page.errors, []);
    } finally { await closePage(page); }
  });

  test(`[${label}] the lobbying card: an empty state with no line drawn, then two series that are never summed`, async () => {
    const page = await open({path: dataPath});
    try {
      assert.match(await page.textContent('#gf-lobby-chart'), /Enter yearly growth to project 2026–2028/);
      assert.equal(await page.$$eval('#gf-lobby-chart .gf-line', all => all.length), 0, 'no line without data');
      await example(page); await calculate(page);
      assert.match(await page.textContent('#gf-lobby-chart'), /Enter yearly growth to project 2026–2028/, 'the example enters no lobbying growth, so there is still nothing to draw');
      // enter yearly lobbying growth in the popovers of both horizons
      await page.click('#gf-panel-current .gf-lobby-link');
      assert.equal(await page.$eval('#gf-lobby-pop-current', el => el.hidden), false);
      await page.fill('#gf-2026-lobby', '0');
      await page.click('#gf-panel-current .gf-pop-done');
      await page.click('#gf-tab-next'); await page.click('#gf-panel-next .gf-lobby-link');
      await page.fill('#gf-2027-lobby', '0'); await page.fill('#gf-2028-lobby', '0');
      await page.click('#gf-panel-next .gf-pop-done');
      await calculate(page);
      assert.equal(await page.$$eval('#gf-lobby-chart .gf-line', all => all.length), 2, 'two lines, one per series');
      assert.deepEqual(await page.$$eval('#gf-lobby-chart .gf-series', all => all.map(el => el.getAttribute('aria-label').split(',')[0])), ['Outside-firm fees', 'In-house expenses']);
      const colours = await page.$$eval('#gf-lobby-chart .gf-line', all => all.map(el => getComputedStyle(el).stroke));
      assert.deepEqual(colours, ['rgb(43, 155, 153)', 'rgb(139, 105, 132)'], 'teal and mauve: not the party colours of the candidate bars');
      assert.match(await hoverTip(page, '#gf-lobby-chart .gf-series-fees .gf-hit >> nth=1'), /never added/);
      assert.deepEqual(page.errors, []);
    } finally { await closePage(page); }
  });

  test(`[${label}] the footer line and "Sources and notes": everything the old panel printed is still reachable`, async () => {
    const page = await open({path: dataPath});
    try {
      assert.match(await page.textContent('#gf-footnote'), /Mentat levels; OpenSecrets data only estimates the relationships\. Observed through 2026-06-30 · 41 of 67 work units complete · No 2026 CPI yet · Sources and notes/);
      assert.equal(await page.$eval('#gf-notes', el => el.hidden), true);
      await example(page); await calculate(page);
      await page.click('#gf-notes-toggle');
      assert.equal(await page.getAttribute('#gf-notes-toggle', 'aria-expanded'), 'true');
      const notes = await page.textContent('#gf-notes');
      for (const needle of ['Mentat levels for the industry\'s tracked companies', 'Mentat anchors: Banking Industry Spending Overview.xlsx', 'Included receipts the accounting engine buckets as non_giving',
        'Full numbers by outcome', 'Model evidence and ordinary p-values', 'Revenue growth: 100 ×', 'Lobbying by year: change in forecast annual industry growth', 'must not be added', 'Observed through 2026-06-30']) {
        assert.ok(notes.includes(needle) || notes.replace(/\s+/g, ' ').includes(needle), 'Sources and notes keeps: ' + needle);
      }
      assert.match(notes, /Remainder prediction interval: -\$937\.21K to \$4\.73M/, 'the model\'s own unconditioned numbers are in the table behind the notes');
      assert.match(notes, /budget_inconsistent: The projected total and share are incompatible/);
      assert.match(notes, /Ordinary p = |ordinary p = /);
      if (withFix) {
        assert.match(notes, /Conditioned on the giving already observed/);
        assert.match(notes, /Remainder, median/);
        assert.match(notes, /negative before conditioning/);
        assert.match(notes, /The table below is the model's own unconditioned arithmetic/);
      } else {
        assert.doesNotMatch(notes, /Conditioned on the giving already observed/);
      }
      // the evidence drawer opens and holds the ordinary p-values
      await page.click('#gf-evidence summary');
      assert.match(await page.textContent('#gf-evidence-content'), /PAC amount · Commercial banks/);
      assert.match(await page.textContent('#gf-evidence-content'), /Ordinary p/);
      await page.click('#gf-notes-toggle');
      assert.equal(await page.$eval('#gf-notes', el => el.hidden), true);
      assert.deepEqual(page.errors, []);
    } finally { await closePage(page); }
  });

  test(`[${label}] owner waivers: a neutral chip on the House card and the full list in the notes (registry-shaped fixture entries, then the shape the calculator catalog carries)`, async () => {
    const none = await open({path: dataPath});
    try {
      await example(none); await calculate(none);
      assert.equal((await none.$$eval('#gf-house-foot .gf-chip', all => all.map(el => el.textContent))).filter(text => /Gate waived/.test(text)).length, 0);
    } finally { await closePage(none); }
    const page = await open({path: dataPath, waivers: REGISTRY_WAIVERS});
    try {
      await example(page); await calculate(page);
      const chips = await page.$$eval('#gf-house-foot .gf-chip', all => all.map(el => ({text: el.textContent.trim(), amber: el.classList.contains('gf-chip-warn')})));
      assert.deepEqual(chips.filter(c => /Gate waived/.test(c.text)), [{text: 'Gate waived by owner: House share', amber: false}]);
      assert.equal((await page.$$eval('#gf-senate-foot .gf-chip', all => all.map(el => el.textContent))).filter(text => /Gate waived/.test(text)).length, 0);
      assert.match(await hoverTip(page, '#gf-house-foot .gf-chip >> text=Gate waived by owner'), /Cellcontrol_House \/ commercial_banksGateG6.*OwnerPaul Goff, 2026-09-30/);
      await page.click('#gf-notes-toggle');
      const waivers = await page.textContent('#gf-waivers');
      assert.match(waivers, /Owner waivers of the refit gates/);
      for (const cell of REGISTRY_WAIVERS.map(w => w.cell)) assert.ok(waivers.includes(cell), cell + ' is listed');
      assert.match(waivers, /listed here only/);
      assert.deepEqual(page.errors, []);
    } finally { await closePage(page); }
    // the entry as the calculator will carry it: its own display text is the chip, wrapped inside the House card
    const shaped = await open({path: dataPath, waivers: [DISPLAY_WAIVER], width: 1440});
    try {
      await example(shaped); await calculate(shaped);
      const chip = shaped.locator('#gf-house-foot .gf-chip', {hasText: 'gate waived by owner'});
      assert.equal(await chip.textContent(), DISPLAY_WAIVER.display_text);
      const inside = await shaped.evaluate(() => { const c = [...document.querySelectorAll('#gf-house-foot .gf-chip')].find(e => /waived/.test(e.textContent)).getBoundingClientRect(), k = document.getElementById('gf-house').getBoundingClientRect(); return {chipRight: c.right, cardRight: k.right}; });
      assert.ok(inside.chipRight <= inside.cardRight, 'the chip stays inside the card: ' + JSON.stringify(inside));
      assert.match(await hoverTip(shaped, '#gf-house-foot .gf-chip >> text=gate waived by owner'), new RegExp(measuredText(DISPLAY_WAIVER)));
      assert.deepEqual(shaped.errors, []);
    } finally { await closePage(shaped); }
  });

  test(`[${label}] credit unions: the single-PAC thin base, the own-history band warning and the thin-base mix rows are chips`, async () => {
    const page = await open({path: dataPath});
    try {
      await page.selectOption('#gf-industry', 'credit_unions');
      await page.waitForTimeout(400);
      await example(page); await calculate(page);
      await page.click('#gf-account-pac');
      await page.waitForTimeout(900);
      const chips = await page.$$eval('#gf-chart-flags .gf-chip', all => all.map(el => ({text: el.textContent.trim(), amber: el.classList.contains('gf-chip-warn')})));
      assert.ok(chips.some(c => /^One PAC \(SchoolsFirst Federal Credit Union\): a thin base/.test(c.text) && !c.amber), 'single_pac_thin_base is neutral');
      assert.ok(chips.some(c => c.text === 'Coverage cut back to 2026-05-31' && !c.amber));
      const band = chips.filter(c => c.text === 'Mentat\'s own last change for this series was far outside this band; treat the band as too narrow.');
      assert.equal(band.length, withFix ? 1 : 0, 'the own-history warning is the model fix\'s flag');
      if (withFix) assert.equal(band[0].amber, true);
      const houseChips = await page.$$eval('#gf-house-foot .gf-chip', all => all.map(el => ({text: el.textContent.trim(), amber: el.classList.contains('gf-chip-warn')})));
      assert.deepEqual(houseChips.filter(c => /^Thin base/.test(c.text)).map(c => c.text), ['Thin base: Employees and Roster PACs']);
      assert.equal(houseChips.filter(c => c.amber && c.text !== WIDE_TEXT).length, withFix ? 0 : 1, 'the House employee basis is budget_inconsistent without the fix');
      // a row whose drawn share interval leaves 0-100% is not clipped: an amber chip says so and the bar is outlined (the credit-union roster-PAC basis on a thin base)
      for (const chamber of ['House', 'Senate']) {
        const response = answerFor(page.stub.runs, lastRequest(page)).horizons[0].shares[chamber].bases;
        const wide = response.filter(b => b.status === 'ready').map(b => { const a = b.remaining_allocation; const low = a ? a.implied_cycle_R_share_prediction_low : b.cycle_prediction_low, high = a ? a.implied_cycle_R_share_prediction_high : b.cycle_prediction_high; return low < 0 || high > 1; });
        const chips = await page.$$eval(`#gf-${chamber.toLowerCase()}-foot .gf-chip`, all => all.map(el => ({text: el.textContent.trim(), amber: el.classList.contains('gf-chip-warn')})));
        assert.equal(chips.some(c => c.text === WIDE_TEXT && c.amber), wide.some(Boolean), `${chamber}: the amber chip follows the interval of the response`);
        assert.equal(await page.$$eval(`#gf-${chamber.toLowerCase()}-body .gf-bar.is-flagged`, all => all.length) >= wide.filter(Boolean).length, true, chamber + ': the affected bar is outlined');
        if (wide.some(Boolean)) assert.match(await hoverTip(page, `#gf-${chamber.toLowerCase()}-foot .gf-chip-warn >> text=Share interval`), /not clipped to 0–100%/);
      }
      assert.deepEqual(page.errors, []);
    } finally { await closePage(page); }
  });

  test(`[${label}] states: a calculation in flight keeps the columns and shows progress; a failure is said in the card; a blank scenario draws dashes, not zeros`, async () => {
    const page = await open({path: dataPath});
    try {
      await example(page); await calculate(page);
      const before = await chartText(page);
      page.stub.delay = 900;
      await page.click('#gf-calculate');
      await page.waitForFunction(() => document.getElementById('gf-chart').getAttribute('aria-busy') === 'true');
      assert.equal(await page.$eval('#gf-progress', el => el.hidden), false, 'a thin progress bar under the hero title');
      assert.equal(await chartText(page), before, 'the columns keep their last values while it runs');
      await page.waitForFunction(() => document.getElementById('gf-chart').getAttribute('aria-busy') === 'false');
      assert.equal(await page.$eval('#gf-progress', el => el.hidden), true);
      // failure: an inline message that names what failed and what to change
      page.stub.delay = 0; page.stub.failure = 500;
      await page.click('#gf-calculate');
      await page.waitForFunction(() => !document.getElementById('gf-alert').hidden);
      const alert = await page.textContent('#gf-alert');
      assert.match(alert, /Not calculated\./);
      assert.match(alert, /The forecast service could not finish this calculation\./);
      assert.match(alert, /Change the input it names, or reload the page, and calculate again\./);
      assert.equal(await page.$eval('#gf-export', el => el.disabled), true);
      page.stub.failure = 0;
      // a blank scenario: the open cycle keeps its observed segment and the missing input is a dash with the reason in its tooltip
      await page.fill('#gf-2026-growth-view', '');
      await page.click('#gf-tab-next'); await page.fill('#gf-2028-growth-view', ''); await page.click('#gf-tab-current');
      await page.click('#gf-calculate');
      await page.waitForFunction(() => document.getElementById('gf-chart').getAttribute('aria-busy') === 'false' && document.getElementById('gf-alert').hidden);
      const text = await chartText(page);
      assert.ok(text.includes('$11.57M'), 'the observed segment is real data and stays');
      assert.ok(!/\$15\.6/.test(text), 'no remainder is drawn without growth');
      assert.equal((await page.$$eval('#gf-chart .gf-dash', all => all.map(el => el.textContent))).join(''), '--', 'a dash in each open slot');
      assert.match(await hoverTip(page, '#gf-chart .gf-mark-current'), /Enter expected two-year cycle revenue growth\./);
      assert.deepEqual(await page.$$eval('#gf-house-body .gf-bar-dash', all => all.map(el => el.textContent)), ['-', '-']);
      assert.deepEqual(page.errors, []);
    } finally { await closePage(page); }
  });

  test(`[${label}] layout: two columns with three equal cards at 1600 and 1440, one column and no horizontal scroll at 390`, async () => {
    for (const [width, height] of [[1600, 900], [1440, 900], [390, 844]]) {
      const page = await open({path: dataPath, width, height});
      try {
        await example(page); await calculate(page);
        const sizes = await page.evaluate(() => {
          const box = id => { const r = document.getElementById(id).getBoundingClientRect(); return {x: r.x, y: r.y, w: r.width, h: r.height}; };
          const hero = document.querySelector('.gf-hero').getBoundingClientRect(), scenario = document.querySelector('.gf-scenario').getBoundingClientRect(), chart = document.querySelector('.gf-chart-col').getBoundingClientRect();
          return {house: box('gf-house'), senate: box('gf-senate'), lobby: box('gf-lobby'), hero: {w: hero.width, h: hero.height}, scenario: {x: scenario.x, y: scenario.y, w: scenario.width, h: scenario.height, content: document.getElementById('gf-reference').getBoundingClientRect().bottom - scenario.top}, chart: {x: chart.x, y: chart.y, w: chart.width, h: chart.height},
            scope: box('gf-example-pill'), scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth};
        });
        assert.ok(sizes.scrollWidth <= sizes.clientWidth, `no horizontal scroll at ${width}: ${sizes.scrollWidth} > ${sizes.clientWidth}`);
        if (width >= 1180) {
          assert.ok(sizes.scenario.x > sizes.chart.x + sizes.chart.w - 2, 'the Scenario panel sits beside the chart');
          assert.ok(Math.abs(sizes.scenario.w - 342) <= 2, 'the Scenario panel is 342 px wide: ' + sizes.scenario.w);
          assert.ok(sizes.scenario.content <= 396, 'the Scenario content (down to "Use historical example") fits the board height of the hero card (408) with its saved-outlook captions: ' + sizes.scenario.content);
          assert.ok(Math.abs(sizes.house.w - sizes.senate.w) <= 1 && Math.abs(sizes.senate.w - sizes.lobby.w) <= 1, 'three equal cards');
          assert.ok(Math.abs(sizes.house.y - sizes.lobby.y) <= 1 && Math.abs(sizes.senate.y - sizes.lobby.y) <= 1, 'one row');
          assert.ok(Math.abs(sizes.house.h - sizes.senate.h) <= 1 && Math.abs(sizes.senate.h - sizes.lobby.h) <= 1, 'one height');
          const gaps = [sizes.senate.x - (sizes.house.x + sizes.house.w), sizes.lobby.x - (sizes.senate.x + sizes.senate.w)];
          assert.ok(gaps.every(g => Math.abs(g - 18) <= 1), '18 px gaps: ' + gaps);
        } else {
          assert.ok(sizes.scenario.y >= sizes.chart.y + sizes.chart.h - 2, 'one column: the Scenario panel is under the chart ' + JSON.stringify({scenario: sizes.scenario, chart: sizes.chart, hero: sizes.hero}));
          assert.ok(sizes.senate.y > sizes.house.y + sizes.house.h - 2 && sizes.lobby.y > sizes.senate.y + sizes.senate.h - 2, 'the three cards stack');
          assert.ok(sizes.house.w > width - 60, 'full width cards');
        }
        // the lobbying dialog of either horizon opens over the sliders, inside the Scenario panel: never over its heading or the horizon switch
        for (const which of ['current', 'next']) {
          if (which === 'next') await page.click('#gf-tab-next');
          await page.click(`#gf-panel-${which} .gf-lobby-link`);
          const geometry = await page.evaluate(which => {
            const rect = el => el.getBoundingClientRect();
            const pop = rect(document.getElementById('gf-lobby-pop-' + which)), scenario = rect(document.querySelector('.gf-scenario'));
            const meets = el => { const r = rect(el); return pop.left < r.right && r.left < pop.right && pop.top < r.bottom && r.top < pop.bottom; };
            return {open: !document.getElementById('gf-lobby-pop-' + which).hidden, coversHeading: meets(document.getElementById('gf-scenario-title')), coversSwitch: meets(document.querySelector('.gf-tabs')),
              insideColumn: pop.left >= scenario.left - 1 && pop.right <= scenario.right + 1 && pop.left >= 0 && pop.right <= innerWidth, belowPanelTop: pop.top >= scenario.top};
          }, which);
          assert.deepEqual(geometry, {open: true, coversHeading: false, coversSwitch: false, insideColumn: true, belowPanelTop: true}, `the ${which} lobbying dialog at ${width} px`);
          await page.keyboard.press('Escape');
          assert.equal(await page.$eval('#gf-lobby-pop-' + which, el => el.hidden), true, 'Escape closes it');
        }
        assert.deepEqual(page.errors, []);
      } finally { await closePage(page); }
    }
  });
}

test('the live calculator as recorded now (model fix P1, owner waivers, no pooled reference, general giving without the non-giving receipts): the page draws its own answers', async () => {
  const general = run => run.horizons[0].pac.measures.find(m => m.id === 'general_giving');
  const page = await open({path: 'landed'});
  try {
    // the saved 2026 outlook of the live catalog opens in both control rows with its source beside them
    assert.deepEqual(await page.$$eval('#gf-panel-current .gf-source-text', all => all.map(el => el.textContent)), [SAVED_TEXT, SAVED_TEXT]);
    await example(page); await calculate(page);
    // banks: the conditioned open cycle leaves nothing to flag amber; the owner waiver of the House share is the entry's own display text, a neutral chip
    assert.equal(await page.$$eval('#gf-form .gf-chip-warn', all => all.length), 0, 'nothing contradicts the giving already observed');
    const house = await page.$$eval('#gf-house-foot .gf-chip', all => all.map(el => ({text: el.textContent.trim(), amber: el.classList.contains('gf-chip-warn')})));
    assert.deepEqual(house.filter(c => /waived/i.test(c.text)), [{text: DISPLAY_WAIVER.display_text, amber: false}]);
    assert.equal((await page.$$eval('#gf-senate-foot .gf-chip', all => all.map(el => el.textContent))).filter(text => /waived/i.test(text)).length, 0);
    assert.match(await hoverTip(page, '#gf-house-foot .gf-chip >> text=gate waived by owner'), new RegExp(measuredText(DISPLAY_WAIVER)));
    // the Mentat level says what the general-giving measure leaves out; the roster-PAC account says nothing of the kind
    assert.match(await hoverTip(page, '#gf-chart .gf-mark-anchor .gf-col-anchor'), /Receipts the accounting engine marks non-giving \(interest, refunds, insurance claims, loans\) are left out/);
    await page.click('#gf-account-pac'); await page.waitForTimeout(500);
    assert.doesNotMatch(await hoverTip(page, '#gf-chart .gf-mark-anchor .gf-col-anchor'), /non-giving/);
    assert.match(general(LANDED.runs.banks).label, /^Mentat general giving \(all channels\), excluding receipts Mentat marks non-giving/);
    // the notes name the measure by that label and list every waiver the catalog carries
    await page.click('#gf-notes-toggle');
    assert.ok((await page.textContent('#gf-notes')).includes(general(LANDED.runs.banks).label), 'the comparison table names the measure by the response label');
    const waivers = await page.textContent('#gf-waivers');
    for (const entry of LANDED.catalog.waivers) assert.ok(waivers.includes(entry.cell), entry.cell + ' is listed');
    await page.click('#gf-notes-toggle');
    // credit unions: the flags the response raises (looked up by name) are the chips; its House waiver is its own entry
    await page.selectOption('#gf-industry', 'credit_unions'); await page.waitForTimeout(400);
    await example(page); await calculate(page);
    const flags = general(LANDED.runs.credit_unions).flags || [];
    const chart = await page.$$eval('#gf-chart-flags .gf-chip', all => all.map(el => ({text: el.textContent.trim(), amber: el.classList.contains('gf-chip-warn')})));
    assert.equal(chart.some(c => c.amber && c.text === INTERVAL_TEXT), flags.includes('interval_not_supported_by_own_history'), 'the own-history band warning follows the flag of the response');
    const cuWaiver = LANDED.catalog.waivers.find(w => w.industry === 'credit_unions' && w.chamber === 'House' && w.show_warning === true);
    const credit = await page.$$eval('#gf-house-foot .gf-chip', all => all.map(el => el.textContent.trim()));
    assert.equal(credit.filter(text => /waived/i.test(text)).length, cuWaiver ? 1 : 0);
    if (cuWaiver) assert.ok(credit.includes(cuWaiver.display_text));
    // the credit-union Senate roster-PAC share interval of the live calculator leaves 0-100% (-1.89% to 4.69%): not clipped, said so in amber, the bar outlined
    const senateChips = await page.$$eval('#gf-senate-foot .gf-chip', all => all.map(el => ({text: el.textContent.trim(), amber: el.classList.contains('gf-chip-warn')})));
    assert.ok(senateChips.some(c => c.text === WIDE_TEXT && c.amber), 'the amber chip: ' + JSON.stringify(senateChips));
    assert.equal(await page.$$eval('#gf-senate-body .gf-bar.is-flagged', all => all.length), 1);
    assert.match(await hoverTip(page, '#gf-senate-body .gf-bar >> nth=1'), /95% prediction interval-1\.89% to 4\.69%/);
    assert.deepEqual(page.errors, []);
  } finally { await closePage(page); }
});

test('reduced motion: nothing animates; with motion on, the columns grow from the baseline and the mix bars sweep', async () => {
  const still = await open({path: 'p1', reducedMotion: 'reduce'});
  try {
    await example(still); await calculate(still);
    const names = await still.$$eval('#gf-chart .gf-grow, #gf-house-body .gf-bar-d, #gf-chart .gf-fade', all => all.map(el => getComputedStyle(el).animationName));
    assert.ok(names.length > 5);
    assert.deepEqual([...new Set(names)], ['none'], 'prefers-reduced-motion disables every animation');
    assert.equal(await still.$eval('.gf-col-observed', el => getComputedStyle(el).opacity), '1', 'everything is visible at rest');
  } finally { await closePage(still); }
  const moving = await open({path: 'p1'});
  try {
    await example(moving); await calculate(moving);
    await moving.click('#gf-account-pac');
    const grow = await moving.$eval('#gf-chart .gf-grow', el => getComputedStyle(el).animationName);
    assert.equal(grow, 'gf-grow');
    const sweep = await moving.$eval('#gf-house-body .gf-bar-d', el => getComputedStyle(el).animationName);
    assert.equal(sweep, 'gf-sweep');
    await moving.waitForTimeout(1500);
    assert.equal(await moving.$eval('.gf-col-observed', el => getComputedStyle(el).opacity), '1', 'everything is visible once the entrance is over');
  } finally { await closePage(moving); }
});

test('the Scenario tabs hold each horizon\'s own inputs, a pill sets the control before the election, and Calculate always asks for both horizons', async () => {
  const page = await open({path: 'legacy'});
  try {
    assert.equal(await page.textContent('#gf-tab-current'), 'Rest of 2026');
    assert.equal(await page.textContent('#gf-tab-next'), '2027–2028');
    assert.equal(await page.getAttribute('#gf-tab-current', 'aria-selected'), 'true');
    await page.fill('#gf-2026-growth-view', '8');
    await page.click('#gf-tab-next');
    assert.equal(await page.getAttribute('#gf-tab-next', 'aria-selected'), 'true');
    assert.deepEqual(await page.$eval('#gf-panel-current', el => ({off: el.classList.contains('is-off'), ariaHidden: el.getAttribute('aria-hidden'), inert: el.inert, visibility: getComputedStyle(el).visibility})), {off: true, ariaHidden: 'true', inert: true, visibility: 'hidden'},
      'the horizon that is not shown is invisible and inert');
    assert.equal(await page.isVisible('#gf-2026-growth-view'), false);
    await page.fill('#gf-2028-growth-view', '-3');
    await page.selectOption('#gf-2028-House-majority', '0');
    assert.equal(await page.$eval('#gf-2028-House-majority', el => el.dataset.value), '0');
    await page.click('#gf-tab-current');
    assert.equal(await page.inputValue('#gf-2026-growth-view'), '8', 'both horizons keep their values');
    await page.click('#gf-calculate');
    await page.waitForFunction(() => document.getElementById('gf-chart').getAttribute('aria-busy') === 'false');
    const body = lastRequest(page);
    assert.deepEqual(Object.keys(body.horizons).sort(), ['2026', '2028'], 'both horizons');
    assert.equal(body.horizons['2026'].growth_pct, '8');
    assert.equal(body.horizons['2028'].growth_pct, '-3');
    assert.equal(body.horizons['2028'].current_control.House, '0');
    assert.equal(body.horizons['2028'].current_control.Senate, '');
    assert.equal(body.industry, 'commercial_banks');
    assert.deepEqual(page.errors, []);
  } finally { await closePage(page); }
});

test('a response the cycle view cannot read says so in the card and never blanks the page; the notes stay reachable', async () => {
  const page = await open({path: 'p1', malformed: true});
  try {
    await page.waitForFunction(() => !document.getElementById('gf-alert').hidden);
    const alert = await page.textContent('#gf-alert');
    assert.match(alert, /The cycle view could not be drawn\./);
    assert.match(alert, /The full numbers are under Sources and notes\./);
    assert.equal(await page.$eval('#gf-form', el => el.hidden), false, 'the form is still there');
    await page.click('#gf-notes-toggle');
    assert.equal(await page.$eval('#gf-notes', el => el.hidden), false);
    assert.ok(page.errors.every(text => /could not be drawn/.test(text)), 'only the logged, caught error: ' + page.errors.join(' | '));
  } finally { await closePage(page); }
});

test('Export scenario downloads the calculated scenario and the model evidence', async () => {
  const page = await open({path: 'p1'});
  try {
    await example(page); await calculate(page);
    const [download] = await Promise.all([page.waitForEvent('download'), page.click('#gf-export')]);
    assert.match(download.suggestedFilename(), /^Mentat-commercial_banks-\d{4}-\d{2}-\d{2}-scenario\.json$/);
    const saved = JSON.parse(fs.readFileSync(await download.path(), 'utf8'));
    assert.equal(saved.industry, 'commercial_banks');
    assert.ok(saved.model_evidence && saved.model_evidence.model_version);
    assert.ok(saved.exported_at);
    assert.deepEqual(page.errors, []);
  } finally { await closePage(page); }
});
