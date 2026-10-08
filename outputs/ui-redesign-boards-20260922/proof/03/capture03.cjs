/* Build 03 proof capture (Chart Studio, board S1), re-runnable.

   node capture03.cjs [port]          (default 8817; never 8806)

   Needs a READ-ONLY console on that port started from C:\Users\pgoff\Mentat:
     python mentat/app/server.py --port 8817 --read-only
   Writes shots\<state>_<W>x<H>.png and measurements.json here; then
   python sbs03.py pairs each capture with S1. Every request stays on
   127.0.0.1:<port>; only GETs and POST /api/contributions/query|records pass.
   Each changed asset is fetched with {cache:'reload'} first. The read-only
   preview's own notices are hidden with CSSOM before each capture. */
'use strict';
const path = require('path'), fs = require('fs');
const modules = path.join(process.env.USERPROFILE, '.cache', 'codex-runtimes', 'codex-primary-runtime', 'dependencies', 'node', 'node_modules');
const {chromium} = require(require.resolve('playwright', {paths: [modules]}));
const PORT = Number(process.argv[2] || 8817);
if (PORT === 8806) throw new Error('8806 is Paul\'s console');
const ORIGIN = `http://127.0.0.1:${PORT}`;
const SHOTS = path.join(__dirname, 'shots'); fs.mkdirSync(SHOTS, {recursive: true});
const SIZES = [[1440, 900], [1920, 1080]];
const ASSETS = ['chart-studio.js', 'chart-studio-core.js', 'chart-studio-contributions.js', 'contribution-plot.js', 'ui-state.js', 'chart-studio.css', 'workspace-polish.css', 'graph.js', 'graph.css', 'scope.js'];
const CANVAS_READY = () => !!document.querySelector('#studio-canvas svg') && document.getElementById('studio-canvas').getAttribute('aria-busy') !== 'true';
const STATES = [
  {name: 'builder_default', steps: []},
  {name: 'source_popover', steps: [{click: '#studio-scope-change'}, {pause: 400}]},
  {name: 'compare_cycle', steps: [{click: '#studio-compare-add'}, {pause: 300},
    {run: () => document.querySelectorAll('.compare-menu-kind')[1].click()},
    {until: () => document.querySelectorAll('.compare-menu-option').length > 1},
    {run: () => [...document.querySelectorAll('.compare-menu-option')].find(n => /2023/.test(n.textContent)).click()},
    {until: () => !document.getElementById('studio-compare-pills').hidden && document.getElementById('studio-canvas').getAttribute('aria-busy') !== 'true' && /compared/.test(document.getElementById('studio-subtitle').textContent)},
    {pause: 1500}]},
  {name: 'note_before_match', steps: [{until: () => !document.getElementById('studio-match-graph').hidden}]},
  {name: 'note_after_match', steps: [{until: () => !document.getElementById('studio-match-graph').hidden}, {click: '#studio-match-graph'},
    {until: () => document.querySelectorAll('#studio-filters .studio-pill').length > 0 && document.getElementById('studio-canvas').getAttribute('aria-busy') !== 'true'},
    {until: () => /Agree\.|differ/.test(document.getElementById('studio-reconcile-detail').textContent) && /2025/.test(document.getElementById('studio-reconcile-detail').textContent)}, {pause: 800}]},
  {name: 'why_open', steps: [{until: () => !document.getElementById('studio-match-graph').hidden}, {click: '#studio-reconcile-why'}, {pause: 300}]},
  {name: 'inspector_collapsed', steps: [{click: '#studio-inspector-collapse'}, {pause: 600}]},
  {name: 'canvas_mode', steps: [{click: '#studio-view-canvas'}, {pause: 1200}]},
  // Final fix round: the company comparison (R03-1 header, R03-4 menu, R03-5 labels) and a new empty sheet (R03-10).
  {name: 'compare_company', steps: [{click: '#studio-compare-add'}, {pause: 300},
    {run: () => document.querySelectorAll('.compare-menu-kind')[2].click()},
    {until: () => document.querySelectorAll('.compare-menu-option').length > 1},
    {run: () => document.querySelectorAll('.compare-menu-option')[0].click()},
    {until: () => !document.getElementById('studio-compare-pills').hidden && document.getElementById('studio-canvas').getAttribute('aria-busy') !== 'true' && /compared/.test(document.getElementById('studio-subtitle').textContent)},
    {pause: 1500}]},
  // The new-sheet click can leave the 962px page scrolled to its footer (I4); the capture reads it from the top.
  {name: 'new_sheet', steps: [{click: '#studio-new-sheet'}, {until: () => document.getElementById('studio-canvas').getAttribute('aria-busy') !== 'true'}, {pause: 1200}, {run: () => window.scrollTo(0, 0)}, {pause: 200}]}
];

function measure() {
  const box = sel => { const n = typeof sel === 'string' ? document.querySelector(sel) : sel; if (!n || n.hidden) return null; const r = n.getBoundingClientRect(); if (!r.width && !r.height) return null; return [Math.round(r.left * 10) / 10, Math.round(r.top * 10) / 10, Math.round(r.right * 10) / 10, Math.round(r.bottom * 10) / 10]; };
  const out = {};
  for (const s of ['#workspace-title', '#view-chart-studio .studio-header', '#studio-scope-change', '#studio-compare-add', '#studio-compare-pills', '#studio-ready', '#studio-view-mode',
    '#view-chart-studio .studio-toolbar', '#studio-showme-toggle', '#studio-grid', '#studio-data-panel', '#studio-search', '#studio-shelves', '#studio-canvas-wrap',
    '#studio-title', '#studio-subtitle', '#studio-verified-summary', '#studio-canvas', '#studio-note-line', '#studio-reconcile', '#studio-match-graph', '#studio-reconcile-why',
    '#studio-reconcile-detail', '#studio-result-controls', '#studio-inspector', '#studio-inspector-rail', '#studio-inspector-collapse', '#view-chart-studio .studio-sheets', '#studio-status',
    '#studio-source-popover', '#studio-mark', '#studio-board-tiles', 'body > footer']) out[s] = box(s);
  // Chrome rows above the chart: every visible control between the page top
  // and the grid, grouped by vertical overlap.
  const grid = document.getElementById('studio-grid').getBoundingClientRect();
  const controls = [...document.querySelectorAll('#view-chart-studio .studio-header *, #view-chart-studio .studio-toolbar *')].filter(n => {
    const r = n.getBoundingClientRect(); return r.width > 0 && r.height > 0 && r.bottom <= grid.top && !n.closest('[hidden]') && ['BUTTON', 'SELECT', 'SUMMARY', 'LABEL', 'SPAN'].includes(n.tagName) && !n.closest('#studio-source-popover');
  }).map(n => n.getBoundingClientRect());
  const rows = [];
  for (const r of controls.sort((a, b) => a.top - b.top)) { const row = rows.find(x => r.top < x.bottom && r.bottom > x.top); if (row) { row.top = Math.min(row.top, r.top); row.bottom = Math.max(row.bottom, r.bottom); } else rows.push({top: r.top, bottom: r.bottom}); }
  out.chromeRows = rows.map(r => [Math.round(r.top), Math.round(r.bottom)]);
  const visible = n => { const r = n.getBoundingClientRect(); return r.width > 0 && r.height > 0 && !n.closest('[hidden]'); };
  out.gold = [...document.querySelectorAll('#view-chart-studio *')].filter(n => visible(n) && /rgb\((236, 169, 28|242, 187, 75)\)/.test(getComputedStyle(n).backgroundColor)).map(n => n.id || n.className);
  out.redText = [...document.querySelectorAll('#view-chart-studio *')].filter(n => { if (!visible(n) || ![...n.childNodes].some(c => c.nodeType === 3 && c.textContent.trim())) return false; const m = getComputedStyle(n).color.match(/\d+/g).map(Number); return m[0] > 150 && m[1] < 100 && m[2] < 100; }).map(n => (n.id || n.className) + ': ' + n.textContent.trim().slice(0, 50));
  out.reconcileDifferClass = document.querySelectorAll('#studio-reconcile .studio-reconcile-differ').length;
  out.noteText = (document.getElementById('studio-reconcile-text') || {}).textContent || '';
  out.noteHidden = document.getElementById('studio-reconcile').hidden;
  out.groupCount = (document.getElementById('studio-group-count') || {}).textContent;
  out.status = (document.getElementById('studio-status') || {}).textContent;
  out.chip = (document.getElementById('studio-scope-change') || {}).textContent;
  out.ready = (document.getElementById('studio-ready') || {}).textContent;
  out.filters = (window.MentatStudioPane && window.MentatStudioPane.filters()) || [];
  out.pills = [...document.querySelectorAll('#studio-compare-pills .scope-pill')].map(n => [n.textContent.replace('×', ''), getComputedStyle(n).backgroundColor]);
  out.barColours = [...new Set([...document.querySelectorAll('#studio-canvas rect.plot-mark')].map(n => n.getAttribute('fill')))];
  out.inspectorWidth = Math.round(document.getElementById('studio-inspector').getBoundingClientRect().width);
  out.collapsedStored = (() => { try { return localStorage.getItem('mentat-chart-studio-inspector-collapsed'); } catch { return 'n/a'; } })();
  out.boardButtonsVisible = ['studio-board-1', 'studio-board-2', 'studio-board-4'].map(id => visible(document.getElementById(id)));
  out.scroll = [document.documentElement.scrollWidth, document.documentElement.scrollHeight];
  out.url = location.search;
  // Final fix round measurements: chip fit, what sits on Clear, the chart region, axis end, labels.
  const chipNode = document.getElementById('studio-scope-change');
  out.chipFit = {scrollWidth: chipNode.scrollWidth, clientWidth: chipNode.clientWidth};
  const clear = document.getElementById('studio-compare-clear');
  if (!clear.hidden) { const c = clear.getBoundingClientRect(); const hit = document.elementFromPoint(c.left + c.width / 2, c.top + c.height / 2); out.hitAtClear = hit && (hit.id || hit.className); }
  const canvas = document.getElementById('studio-canvas');
  out.canvasScroll = {scrollH: canvas.scrollHeight, clientH: canvas.clientHeight};
  out.axisTicks = [...document.querySelectorAll('#studio-canvas svg > g > text')].filter(t => t.getAttribute('text-anchor') === 'middle').map(t => t.firstChild ? t.firstChild.textContent : t.textContent);
  out.categoryLabels = [...document.querySelectorAll('#studio-canvas text[data-label=category]')].map(t => t.firstChild ? t.firstChild.textContent : t.textContent);
  out.title = (document.getElementById('studio-title') || {}).textContent;
  out.subtitle = (document.getElementById('studio-subtitle') || {}).textContent;
  out.figures = [...document.querySelectorAll('#studio-verified-summary > span')].map(n => n.textContent);
  out.noteLineHeight = Math.round(document.getElementById('studio-note-line').getBoundingClientRect().height);
  return out;
}

(async () => {
  const browser = await chromium.launch({headless: true, channel: 'chrome'});
  // ONLY=<state,...> re-captures those states and keeps the others' measurements.
  const previous = process.env.ONLY && fs.existsSync(path.join(__dirname, 'measurements.json')) ? JSON.parse(fs.readFileSync(path.join(__dirname, 'measurements.json'), 'utf8')).states : {};
  const report = {port: PORT, when: new Date().toISOString(), states: Object.assign({}, previous)};
  try {
    for (const [W, H] of SIZES) {
      for (const state of STATES.filter(s => !process.env.ONLY || process.env.ONLY.split(',').includes(s.name))) {
        const context = await browser.newContext({viewport: {width: W, height: H}});
        await context.route('**/*', route => {
          const url = new URL(route.request().url());
          if (url.hostname !== '127.0.0.1' || Number(url.port) !== PORT) return route.abort();
          const method = route.request().method();
          if (method !== 'GET' && !(method === 'POST' && /^\/api\/contributions\/(query|records)$/.test(url.pathname))) return route.abort();
          return route.continue();
        });
        const page = await context.newPage();
        const errors = []; page.on('pageerror', e => errors.push(e.message));
        try {
          await page.goto(ORIGIN + '/', {waitUntil: 'domcontentloaded'});
          await page.evaluate(async files => { for (const f of files) await fetch('/' + f, {cache: 'reload'}).catch(() => {}); }, ASSETS);
          await page.goto(ORIGIN + '/?industry=Banking#chart-studio', {waitUntil: 'domcontentloaded'});
          await page.waitForFunction(CANVAS_READY, null, {timeout: 120000, polling: 250});
          await page.waitForFunction(() => !document.getElementById('studio-reconcile').hidden || /Agree/.test(document.getElementById('studio-reconcile-detail').textContent), null, {timeout: 30000, polling: 250}).catch(() => {});
          await page.waitForTimeout(800);
          for (const s of state.steps) {
            if (s.click) await page.click(s.click);
            if (s.run) await page.evaluate(s.run);
            if (s.until) await page.waitForFunction(s.until, null, {timeout: 60000, polling: 250});
            if (s.pause) await page.waitForTimeout(s.pause);
          }
          await page.evaluate(() => {
            const banner = document.getElementById('stale-banner'); if (banner) banner.style.setProperty('display', 'none', 'important');
            const note = document.getElementById('error'); if (note && !note.classList.contains('error')) note.style.setProperty('display', 'none', 'important');
          });
          await page.waitForTimeout(250);
          await page.screenshot({path: path.join(SHOTS, `${state.name}_${W}x${H}.png`)});
          report.states[`${state.name}_${W}x${H}`] = Object.assign(await page.evaluate(measure), {errors});
          console.log('shot', state.name, W, H, errors.length ? errors : 'ok');
        } catch (error) {
          report.states[`${state.name}_${W}x${H}`] = {failed: error.message, errors};
          console.log('FAILED', state.name, W, H, error.message);
        } finally { await context.close(); }
      }
    }
  } finally { await browser.close(); }
  fs.writeFileSync(path.join(__dirname, 'measurements.json'), JSON.stringify(report, null, 1));
})().catch(e => { console.error(e); process.exit(1); });
