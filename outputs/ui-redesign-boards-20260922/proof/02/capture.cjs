/* Build 02 proof capture (Graph: board M4 and compare modes G1-G5), re-runnable.

   node capture.cjs [port]          (default port 8813; never 8806)

   Needs a READ-ONLY console on that port started from C:\Users\pgoff\Mentat:
     python mentat/app/server.py --port 8813 --read-only
   Writes into this folder:
     shots\<state>_<W>x<H>.png   viewport captures of the build
     measurements_02a.json       default view (M4) checks
     measurements_02b.json       compare-mode checks, Copy-link round trips, timings
   Then run:  python sbs02.py    (pairs each capture with its board)

   Every request leaves only for 127.0.0.1:<port>; every non-GET except the
   sparkline query is aborted. Each changed asset is fetched with
   {cache:'reload'} before the first navigation. The read-only preview's own
   notices (the stale-build banner a read-only instance shows while other
   builders change assets, and its "Read-only preview" status line) are not
   Graph: they are hidden with CSSOM before each capture (the console's CSP
   refuses a <style> tag) and the measurements are taken with them hidden. */
'use strict';
const path = require('path');
const fs = require('fs');
const modules = path.join(process.env.USERPROFILE, '.cache', 'codex-runtimes', 'codex-primary-runtime', 'dependencies', 'node', 'node_modules');
const {chromium} = require(require.resolve('playwright', {paths: [modules]}));

const PORT = Number(process.argv[2] || 8813);
if (PORT === 8806) throw new Error('8806 is Paul\'s console; capture from your own read-only port');
const ORIGIN = `http://127.0.0.1:${PORT}`;
const OUT = __dirname;
const SHOTS = path.join(OUT, 'shots');
fs.mkdirSync(SHOTS, {recursive: true});
const SIZES = [[1440, 900], [1920, 1080]];
const ASSETS = ['graph.js', 'graph.css', 'scope.js', 'theme.js', 'app.js', 'workspace-polish.css', 'acu-theme.css', 'comparison.js'];

const Q = {
  m4: '/?industry=Banking&cycle=2026#graph',
  g1: '/?industry=Banking&industry=Credit%20Union&cycle=2026&compare=industry#graph',
  g2: '/?industry=Banking&cycle=2024&cycle=2026&compare=cycle#graph',
  g3: '/?industry=Banking&company=Goldman%20Sachs%20Bank%20NA&company=JP%20Morgan%20Chase%20Bank%20NA&cycle=2026&compare=company#graph',
  g4: '/?industry=Banking&industry=Credit%20Union&industry=Community%20Banks&cycle=2026&compare=industry#graph'
};
const LOADED = "!document.getElementById('graph-results').hidden && !document.querySelector('#view-graph .graph-metrics.is-stale')";
const READY = "document.getElementById('view-graph').dataset.compareState==='ready' && " + LOADED;
const DRAWER = "!document.getElementById('graph-drawer-panel').hidden && document.getElementById('graph-drawer-rows').children.length>0 && document.getElementById('graph-drawer-status')?.hidden!==false";

// state name -> how to reach it
const STATES = [
  {name: 'M4_overview', board: 'M4_graph_default.webp', url: Q.m4, wait: LOADED, spark: true},
  {name: 'more_menu', board: 'M4_graph_default.webp', url: Q.m4, wait: LOADED, steps: [{click: '#graph-more > summary'}, {pause: 300}], keepFocus: true},
  {name: 'drawer_default', board: 'approved_board5_downstream_drawer.webp', url: Q.m4, wait: LOADED,
    steps: [{click: '#graph-tab-recipients'}, {pause: 500}, {click: '#graph-organizations g.graph-bar-button'}, {until: DRAWER}, {pause: 900}]},
  {name: 'G1_industry', board: 'G1_compare_industry.webp', url: Q.g1, wait: READY, compare: true, spark: true},
  {name: 'G2_cycle', board: 'G2_compare_cycle.webp', url: Q.g2, wait: READY, compare: true, spark: true},
  {name: 'G3_company', board: 'G3_compare_company.webp', url: Q.g3, wait: READY, compare: true, spark: true},
  {name: 'G4_three', board: 'G4_compare_three.webp', url: Q.g4, wait: READY, compare: true},
  {name: 'G5_candidates_table', board: 'G5_candidates_table.webp', url: Q.g1, wait: READY, compare: true,
    steps: [{click: '#graph-tab-candidates'}, {pause: 700}]},
  {name: 'drawer_compare', board: 'approved_board5_downstream_drawer.webp', url: Q.g1, wait: READY, compare: true,
    // Sorted by Credit Union, the top row's Credit Union amount opens scope 2's drawer.
    steps: [{click: '#graph-tab-recipients'}, {pause: 600}, {click: '#graph-compare-grid thead th:nth-child(3) button'}, {pause: 300},
      {click: '#graph-compare-grid tbody tr:first-child td.graph-compare-col--amount:nth-child(3) button'}, {until: DRAWER}, {pause: 900}]}
];

async function until(page, expr, timeout) {
  const end = Date.now() + (timeout || 180000);
  while (!(await page.evaluate(expr))) {
    if (Date.now() > end) throw new Error('timed out waiting for ' + expr);
    await page.waitForTimeout(200);
  }
}
async function hideEnvironment(page) {
  await page.evaluate(() => {
    const banner = document.getElementById('stale-banner');
    if (banner) banner.style.setProperty('display', 'none', 'important');
    const note = document.getElementById('error');
    if (note && !note.classList.contains('error')) note.style.setProperty('display', 'none', 'important');
  });
}

/* ------------------------------------------------ in-page measurements */
function measure() {
  const round = n => Math.round(n * 10) / 10;
  const box = el => { const b = el.getBoundingClientRect(); return {x: round(b.left), y: round(b.top), w: round(b.width), h: round(b.height), right: round(b.right), bottom: round(b.bottom)}; };
  const visible = el => el && !el.closest('[hidden]') && el.getClientRects().length > 0 && getComputedStyle(el).visibility !== 'hidden';
  const css = (el, props) => { const s = getComputedStyle(el); return Object.fromEntries(props.map(p => [p, s.getPropertyValue(p)])); };
  const probe = document.createElement('i'); probe.style.color = 'var(--acu-gold)'; document.body.append(probe);
  const gold = getComputedStyle(probe).color; probe.remove();
  const out = {viewport: [innerWidth, innerHeight], scrollHeight: document.scrollingElement.scrollHeight,
    scrollWidth: document.documentElement.scrollWidth, url: location.search + location.hash};
  // The scope bar: chips, the compare chip or "+ Compare with...", Clear comparison, and the actions.
  const grid = document.querySelector('#view-graph .graph-filter-grid');
  const items = [...grid.children].filter(visible);
  for (const id of ['graph-copy-link', 'graph-reset', 'split-view', 'graph-open-builder']) { const el = document.getElementById(id); if (visible(el)) items.push(el); }
  const more = document.querySelector('#graph-more > summary'); if (visible(more)) items.push(more);
  const named = items.map(el => ({name: el.id || el.getAttribute('for') || el.className.split(' ').slice(-1)[0] || el.tagName, rect: box(el)}));
  const tops = named.map(item => item.rect.y);
  const overlaps = [];
  for (let i = 0; i < named.length; i += 1) for (let j = i + 1; j < named.length; j += 1) {
    const a = named[i].rect, b = named[j].rect;
    if (a.x < b.right - 0.5 && b.x < a.right - 0.5 && a.y < b.bottom - 0.5 && b.y < a.bottom - 0.5) overlaps.push([named[i].name, named[j].name]);
  }
  out.scopeBar = {items: named, topSpread: round(Math.max(...tops) - Math.min(...tops)), oneRow: Math.max(...tops) - Math.min(...tops) <= 1, overlaps,
    pills: [...document.querySelectorAll('#view-graph .chip-compare .scope-pill')].map(p => ({text: p.textContent.replace('×', '').trim(), cut: p.querySelector('.scope-pill-text').scrollWidth > p.querySelector('.scope-pill-text').clientWidth + 1, rect: box(p)}))};
  // Gold-filled elements on screen (computed background equals --acu-gold).
  out.goldFilled = [...document.querySelectorAll('body *')].filter(el => visible(el) && getComputedStyle(el).backgroundColor === gold)
    .map(el => el.id || el.className || el.tagName);
  // Party dots on company rows: Company comparison (whole or in halves) and By company.
  out.companyPartyDots = document.querySelectorAll('#graph-companies circle.graph-party, #view-graph .graph-by-company .graph-party, #graph-compare-table[data-kind=companies] i.graph-compare-party').length;
  // Headline figures and the tab underline.
  const tile = document.querySelector('#view-graph .graph-metrics > div');
  const value = tile.querySelector('.graph-figure-line strong') || tile.querySelector('.graph-figure strong');
  out.headline = {label: css(tile.querySelector(':scope > span'), ['font-size', 'color']), value: css(value, ['font-size', 'font-weight', 'font-variant-numeric', 'color']),
    lines: [...document.querySelectorAll('#view-graph .graph-metrics > div')].map(d => [...d.querySelectorAll('.graph-figure-line')].map(l => l.textContent.trim()))};
  const tab = document.querySelector('#view-graph .analysis-tabs [aria-selected=true]');
  out.tabUnderline = Object.assign({tab: tab.textContent.trim(), gold}, css(tab, ['border-bottom-width', 'border-bottom-color', 'font-size']));
  out.stripWrapped = document.querySelector('#view-graph .analysis-strip').classList.contains('is-wrapped');
  // Cards: rect, and the row pitch inside each drawing (tops of consecutive row plates).
  out.cards = {};
  for (const panel of document.querySelectorAll('#view-graph .graph-panels > .graph-panel')) {
    if (!visible(panel)) continue;
    const entry = {rect: box(panel)};
    const svgs = [...panel.querySelectorAll('svg.graph-bars:not(.graph-stack)')];
    entry.pitch = svgs.map(svg => { const t = [...svg.querySelectorAll('rect.graph-row')].map(r => r.getBoundingClientRect().top); return t.slice(1).map((v, i) => round(v - t[i])); })
      .map(list => list.length ? {min: Math.min(...list), max: Math.max(...list), rows: list.length + 1} : null);
    const halves = [...panel.querySelectorAll('.graph-half')];
    if (halves.length) {
      const rows = halves.map(half => [...half.querySelectorAll('rect.graph-row')].map(r => r.getBoundingClientRect().top));
      const n = Math.min(...rows.map(list => list.length));
      let worst = 0; for (let i = 0; i < n; i += 1) for (const list of rows) worst = Math.max(worst, Math.abs(list[i] - rows[0][i]));
      entry.halves = {count: halves.length, pills: halves.map(h => h.querySelector('.scope-pill').textContent), rowsPerHalf: rows.map(l => l.length), rowTopSpread: round(worst)};
    }
    out.cards[panel.id] = entry;
  }
  const first = ['graph-category-panel', 'graph-candidate-panel'].map(id => out.cards[id]).filter(Boolean);
  out.firstRowBottom = first.length ? Math.max(...first.map(c => c.rect.bottom)) : null;
  // By company (M4, R1b): rows against the level card's Top N and the company card's order.
  const by = [...document.querySelectorAll('#graph-levels > .graph-by-company .graph-by-company-name')].map(n => n.textContent);
  if (by.length) {
    const companies = [...document.querySelectorAll('#graph-companies svg.graph-bars g[aria-label]')].map(g => g.getAttribute('aria-label').replace(/: .*/, ''));
    out.byCompany = {rows: by.length, levelTopN: Number(document.getElementById('graph-top-levels').value), sameOrderAsCompanyCard: by.every((name, i) => companies[i] === name), names: by};
  }
  const split = document.getElementById('split-view');
  out.splitView = {parent: split.parentElement.id || split.parentElement.className, nextSibling: split.nextElementSibling && split.nextElementSibling.id};
  out.compare = window.MentatGraphCompare ? window.MentatGraphCompare.state() : null;
  out.overline = (document.querySelector('.graph-trail-parts') || {}).textContent || '';
  const pill = document.getElementById('graph-drawer-scope');
  out.drawer = visible(document.getElementById('graph-drawer-panel')) ? {title: document.getElementById('graph-drawer-title').textContent, scopePill: pill && !pill.hidden ? pill.textContent : null, rect: box(document.getElementById('graph-drawer-panel'))} : null;
  const table = document.getElementById('graph-compare-table');
  if (visible(table)) out.table = {kind: table.dataset.kind, filters: [...table.querySelectorAll('.graph-compare-filter')].map(b => b.textContent), headers: [...table.querySelectorAll('thead th')].map(th => [th.textContent, th.getAttribute('aria-sort')]), range: document.getElementById('graph-compare-range').textContent, rows: table.querySelectorAll('tbody tr').length};
  return out;
}
function snapshot() {
  return {view: location.hash, pills: [...document.querySelectorAll('#view-graph .chip-compare .scope-pill')].map(p => p.textContent.replace('×', '').trim()),
    compare: window.MentatGraphCompare.state().compare, layout: window.MentatGraphCompare.state().layout,
    overline: (document.querySelector('.graph-trail-parts') || {}).textContent || '',
    selects: ['industry', 'company', 'cycle', 'tier', 'funding'].map(id => document.getElementById('graph-' + id).value)};
}

(async () => {
  const browser = await chromium.launch({headless: true, channel: 'chrome'});
  const results = {port: PORT, taken: new Date().toISOString(), a: {}, b: {states: {}, roundTrips: {}, timings: null}, errors: []};
  try {
    for (const [width, height] of SIZES) {
      const context = await browser.newContext({viewport: {width, height}});
      await context.route('**/*', route => {
        const url = new URL(route.request().url());
        if (url.hostname !== '127.0.0.1' || Number(url.port) !== PORT) return route.abort();
        const method = route.request().method();
        if (method !== 'GET' && !(method === 'POST' && url.pathname === '/api/contributions/query')) return route.abort();
        return route.continue();
      });
      const page = await context.newPage();
      page.on('pageerror', error => results.errors.push(`${width}: ${error.message}`));
      await page.goto(ORIGIN + '/#loading');
      await page.evaluate(async assets => { for (const a of assets) await fetch('/' + a, {cache: 'reload'}); }, ASSETS);
      for (const state of STATES) {
        const key = `${state.name}_${width}x${height}`;
        try {
          await page.goto('about:blank');
          await page.goto(ORIGIN + state.url);
          await until(page, state.wait);
          // Sparklines arrive on their own request, only where a slot was drawn
          // (compare halves under 380px draw none).
          if (state.spark) await until(page, "!document.querySelector('#graph-companies [data-spark]') || document.querySelector('#graph-companies .graph-spark-draw')", 60000).catch(() => {});
          for (const step of state.steps || []) {
            if (step.click) await page.click(step.click, {timeout: 30000});
            if (step.until) await until(page, step.until);
            if (step.pause) await page.waitForTimeout(step.pause);
          }
          await page.waitForTimeout(900);
          if (!state.keepFocus) await page.evaluate(() => document.activeElement && document.activeElement.blur && document.activeElement.blur());
          await hideEnvironment(page);
          await page.screenshot({path: path.join(SHOTS, key + '.png'), animations: 'disabled', caret: 'hide'});
          const measured = await page.evaluate(measure);
          if (state.compare) results.b.states[key] = measured; else results.a[key] = measured;
          // Copy link reopens the state exactly: the URL the button copies, in a fresh page.
          if (state.compare && !state.steps) {
            const before = await page.evaluate(snapshot);
            await page.click('#graph-copy-link');
            await page.waitForTimeout(300);
            const copied = await page.evaluate(() => {
              const field = document.getElementById('graph-copy-url');
              return field && !document.getElementById('graph-copy-fallback').hidden ? field.value : new URL(MentatScope.href('graph', MentatScope.read()), location.href).href;
            });
            const fresh = await context.newPage();
            await fresh.goto(copied);
            await until(fresh, READY);
            const after = await fresh.evaluate(snapshot);
            await fresh.close();
            results.b.roundTrips[key] = {copied, same: JSON.stringify(before) === JSON.stringify(after), before, after};
          }
        } catch (error) {
          results.errors.push(`${key}: ${error.message}`);
        }
      }
      // Time from a pick to every half painted, each mode, from the default view (1440 only).
      if (width === 1440) {
        const timings = [];
        await page.goto('about:blank');
        await page.goto(ORIGIN + Q.m4);
        await until(page, LOADED);
        // Industry, through the menu itself: keyboard only.
        await page.click('#graph-compare-add');
        await page.keyboard.press('Enter');
        await page.waitForTimeout(250);
        await page.keyboard.type('Credit Union');
        await page.keyboard.press('Enter');
        await until(page, READY);
        timings.push(await page.evaluate(() => MentatGraphCompare.state().timings.slice(-1)[0]));
        for (const [kind, value] of [['cycle', '2024'], ['company', 'JP Morgan Chase Bank NA']]) {
          await page.evaluate(() => MentatGraphCompare.clear());
          await until(page, LOADED + " && !document.getElementById('view-graph').dataset.compare");
          await page.evaluate(([k, v]) => MentatGraphCompare.pick(k, v), [kind, value]);
          await until(page, READY);
          timings.push(await page.evaluate(() => MentatGraphCompare.state().timings.slice(-1)[0]));
        }
        results.b.timings = timings;
      }
      await context.close();
    }
    // The default view's R8 check on another tab: #split-view goes home.
    const context = await browser.newContext({viewport: {width: 1440, height: 900}});
    const page = await context.newPage();
    await page.goto(ORIGIN + '/#chart-studio');
    await page.waitForTimeout(1500);
    results.a.splitViewOnChartStudio = await page.evaluate(() => { const s = document.getElementById('split-view'); return {parent: s.parentElement.id || s.parentElement.className, hidden: s.hidden}; });
    await context.close();
  } finally {
    await browser.close();
  }
  fs.writeFileSync(path.join(OUT, 'measurements_02a.json'), JSON.stringify({port: results.port, taken: results.taken, errors: results.errors, states: results.a}, null, 1));
  fs.writeFileSync(path.join(OUT, 'measurements_02b.json'), JSON.stringify({port: results.port, taken: results.taken, errors: results.errors, ...results.b}, null, 1));
  console.log(JSON.stringify({errors: results.errors, shots: fs.readdirSync(SHOTS).length}));
})();
