/* Integration proof capture (all views, builds 01-08 together), re-runnable.

   node capture.cjs [port]      (default 8812; never 8806)

   Needs a READ-ONLY console on that port started from C:\Users\pgoff\Mentat:
     python mentat/app/server.py --port 8812 --read-only
   Writes shots\<state>_<W>x<H>.png and measurements.json (shell geometry, gold
   count, scroll, console errors, page errors, failed and off-origin requests
   per view). Then: python sbs.py (board left, build right).

   Every request is kept to 127.0.0.1:<port>; non-GET requests other than the
   read-only query endpoints are aborted. Changed assets are fetched with
   {cache:'reload'} first. The read-only preview's own notices (#stale-banner
   and the "Read-only preview" line) are hidden with CSSOM before each capture. */
'use strict';
const path = require('path');
const fs = require('fs');
const modules = path.join(process.env.USERPROFILE, '.cache', 'codex-runtimes', 'codex-primary-runtime', 'dependencies', 'node', 'node_modules');
const {chromium} = require(require.resolve('playwright', {paths: [modules]}));

const PORT = Number(process.argv[2] || 8812);
if ([8806, 8801, 8802, 8841].includes(PORT)) throw new Error('not this port');
const ORIGIN = `http://127.0.0.1:${PORT}`;
const OUT = __dirname;
const SHOTS = path.join(OUT, 'shots');
fs.mkdirSync(SHOTS, {recursive: true});
const SIZES = [[1440, 900], [1920, 1080]];
const ASSETS = ['app.js', 'scope.js', 'theme.js', 'graph.js', 'graph.css', 'comparison.js', 'chart-studio.js', 'chart-studio-core.js',
  'contribution-plot.js', 'ui-state.js', 'chart-studio.css', 'insights.js', 'insights.css', 'cross-reference.js', 'cross-reference.css',
  'evidence.js', 'evidence-map.js', 'workspace.css', 'coverage-view.js', 'style.css', 'acu-theme.css', 'workspace-polish.css'];
const SRC = 'csv-bbe7ee6a0f03957cddc3d14eddfb0f1c';
const PANES = `?a.source=csv&a.id=${SRC}&a.committee=C00004275&b.source=csv&b.id=${SRC}&b.committee=C00196444`;

const GRAPH = "!document.getElementById('graph-results').hidden && !document.querySelector('#view-graph .graph-metrics.is-stale')";
const STATES = [
  {name: 'graph_M4', view: 'graph', board: 'M4_graph_default.webp', url: '/?industry=Banking&cycle=2026#graph', wait: GRAPH},
  {name: 'graph_G1', view: 'graph', board: 'G1_compare_industry.webp', url: '/?industry=Banking&industry=Credit%20Union&cycle=2026&compare=industry#graph',
    wait: "document.getElementById('view-graph').dataset.compareState==='ready' && " + GRAPH},
  {name: 'chart-studio_S1', view: 'chart-studio', board: 'S1_chart_studio.webp', url: '/?industry=Banking#chart-studio',
    wait: "!!document.querySelector('#studio-canvas svg') && document.getElementById('studio-canvas').getAttribute('aria-busy')!=='true'"},
  {name: 'insights_I1', view: 'insights', board: 'I1_insights.webp', url: '/?industry=Banking#insights',
    wait: "document.querySelectorAll('#insights-results article[data-state=\"ready\"],#insights-results article[data-state=\"empty\"]').length>=3"},
  {name: 'cross-reference_B16', view: 'cross-reference', board: 'B16_cross_reference.webp', url: '/#cross-reference',
    wait: "!!document.querySelector('#xref-results .xref-tab') || !!document.querySelector('#xref-results .xref-empty')"},
  {name: 'evidence_B19', view: 'evidence', board: 'B19_pac_evidence_panes.webp', url: '/' + PANES + '#evidence',
    wait: "document.querySelectorAll('#evidence-panes [data-pane]').length===2 && !document.querySelector('#evidence-panes .pane-message')"},
  {name: 'loading_B20', view: 'loading', board: 'B20_loading_step1_typing.webp', url: '/#loading',
    wait: "!!document.querySelector('#loading-steps') && !document.getElementById('view-loading').hidden"},
  {name: 'collection_B22', view: 'collection', board: 'B22_collection_run_card.webp', url: '/#collection',
    wait: "document.body.dataset.view==='collection' && (!document.getElementById('monitor').hidden || !document.getElementById('empty').hidden || !document.getElementById('run-setup-actions').hidden)"},
];

function measure(view) {
  const rect = el => { if (!el) return null; const r = el.getBoundingClientRect(); return {x: +r.x.toFixed(1), y: +r.y.toFixed(1), w: +r.width.toFixed(1), h: +r.height.toFixed(1)}; };
  const vis = el => { if (!el) return false; const r = el.getBoundingClientRect(); const cs = getComputedStyle(el); return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none'; };
  const font = el => { if (!el) return null; const cs = getComputedStyle(el); return `${cs.fontWeight} ${cs.fontSize}/${cs.lineHeight} ${cs.fontFamily.split(',')[0]}`; };
  const root = getComputedStyle(document.documentElement);
  const probe = document.createElement('div'); probe.style.color = root.getPropertyValue('--acu-gold').trim(); document.body.appendChild(probe);
  const gold = getComputedStyle(probe).color; probe.remove();
  const section = document.getElementById('view-' + view);
  const all = [...document.querySelectorAll('button, a, [role=button], .primary, summary, label')].filter(vis);
  const golds = all.filter(el => getComputedStyle(el).backgroundColor === gold)
    .map(el => ({id: el.id || null, cls: String(el.className || '').slice(0, 60), text: (el.textContent || '').trim().slice(0, 40),
      inPaneSegment: !!el.closest('#evidence-panes .pane-view, #evidence-panes .seg, .pane-thumb .seg')}));
  const nav = document.querySelector('.app-navigation');
  const active = document.querySelector('.workspace-tabs button[aria-selected=true]');
  const title = document.getElementById('workspace-title');
  const firstCard = section ? [...section.querySelectorAll('.card')].filter(vis).sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top)[0] : null;
  const overline = [...document.querySelectorAll('.page-overline')].filter(vis)[0] || null;
  const chips = section ? [...section.querySelectorAll('.chip-select')].filter(vis).map(el => +el.getBoundingClientRect().height.toFixed(1)) : [];
  const pills = section ? [...section.querySelectorAll('.scope-pill')].filter(vis).map(el => +el.getBoundingClientRect().height.toFixed(1)) : [];
  const partyDots = section ? [...section.querySelectorAll('*')].filter(el => vis(el) && /party-(dem|rep)/.test(String(el.className || ''))).length : 0;
  return {
    gold, goldCount: golds.filter(g => !g.inPaneSegment).length, golds,
    nav: rect(nav), navBg: nav && getComputedStyle(nav).backgroundColor,
    wordmark: {rect: rect(document.querySelector('.wordmark')), font: font(document.querySelector('.wordmark'))},
    tagline: {visible: vis(document.querySelector('.brand-caption')), text: document.querySelector('.brand-caption')?.textContent},
    activeTab: {id: active?.id, rect: rect(active), bg: active && getComputedStyle(active).backgroundColor, color: active && getComputedStyle(active).color, font: font(active)},
    groupLabel: font(document.querySelector('.nav-group')),
    title: {text: title?.textContent, rect: rect(title), font: font(title), color: title && getComputedStyle(title).color, visible: vis(title)},
    heading: rect(document.querySelector('.workspace-heading')),
    stage: {visible: vis(document.getElementById('stage')), text: document.getElementById('stage')?.textContent?.trim(), rect: rect(document.getElementById('stage'))},
    overline: overline ? {text: overline.textContent.trim().slice(0, 80), rect: rect(overline), font: font(overline)} : null,
    firstCard: firstCard ? {cls: String(firstCard.className).slice(0, 60), rect: rect(firstCard), radius: getComputedStyle(firstCard).borderRadius, bg: getComputedStyle(firstCard).backgroundColor} : null,
    chipHeights: chips, pillHeights: pills, partyDotsInView: partyDots,
    bodyBg: getComputedStyle(document.body).backgroundColor, mainBg: getComputedStyle(document.getElementById('workspace-main')).backgroundColor,
    scroll: {h: document.documentElement.scrollHeight, vh: innerHeight, w: document.documentElement.scrollWidth, vw: innerWidth},
    footer: rect(document.querySelector('footer, .app-footer, #console-footer')),
  };
}

(async () => {
  const browser = await chromium.launch({headless: true, channel: 'chrome'});
  const report = {port: PORT, when: new Date().toISOString(), states: {}};
  try {
    for (const [W, H] of SIZES) {
      for (const state of STATES.filter(s => !process.env.ONLY || process.env.ONLY.split(',').includes(s.name))) {
        const context = await browser.newContext({viewport: {width: W, height: H}});
        const offOrigin = [], failed = [], consoleErrors = [], pageErrors = [];
        await context.route('**/*', route => {
          const url = new URL(route.request().url());
          if (url.hostname !== '127.0.0.1' || Number(url.port) !== PORT) { offOrigin.push(url.href); return route.abort(); }
          const method = route.request().method();
          if (method !== 'GET' && !(method === 'POST' && /^\/api\/(contributions\/(query|records|geography)|insights\/(query|records)|analysis|graph|comparison)/.test(url.pathname))) return route.abort();
          return route.continue();
        });
        const page = await context.newPage();
        page.on('pageerror', e => pageErrors.push(e.message));
        page.on('console', m => { if (m.type() === 'error') consoleErrors.push(m.text().slice(0, 300)); });
        page.on('response', r => { if (r.status() >= 400) failed.push(`${r.status()} ${r.request().method()} ${new URL(r.url()).pathname}`); });
        const key = `${state.name}_${W}x${H}`;
        try {
          await page.goto(ORIGIN + '/', {waitUntil: 'domcontentloaded'});
          await page.evaluate(async files => { for (const f of files) await fetch('/' + f, {cache: 'reload'}).catch(() => {}); }, ASSETS);
          await page.goto(ORIGIN + state.url, {waitUntil: 'domcontentloaded'});
          // The console's CSP refuses eval, so poll with page.evaluate (CDP), not waitForFunction(string).
          for (const end = Date.now() + 240000; !(await page.evaluate(state.wait).catch(() => false));) {
            if (Date.now() > end) throw new Error('timed out waiting for ' + state.wait);
            await page.waitForTimeout(300);
          }
          await page.waitForTimeout(1500);
          await page.evaluate(() => {
            const banner = document.getElementById('stale-banner'); if (banner) banner.style.setProperty('display', 'none', 'important');
            const note = document.getElementById('error'); if (note && /Read-only preview/.test(note.textContent || '')) note.style.setProperty('display', 'none', 'important');
          });
          await page.evaluate(() => window.scrollTo(0, 0));
          await page.waitForTimeout(300);
          await page.screenshot({path: path.join(SHOTS, `${key}.png`)});
          report.states[key] = {view: state.view, board: state.board, url: state.url, ok: true, measure: await page.evaluate(measure, state.view),
            consoleErrors, pageErrors, failed, offOrigin};
          console.log('captured', key, 'gold', report.states[key].measure.goldCount, 'errors', consoleErrors.length + pageErrors.length);
        } catch (error) {
          await page.screenshot({path: path.join(SHOTS, `${key}_FAILED.png`)}).catch(() => {});
          report.states[key] = {view: state.view, board: state.board, url: state.url, ok: false, error: String(error.message).slice(0, 400), consoleErrors, pageErrors, failed, offOrigin};
          console.log('FAILED', key, String(error.message).slice(0, 200));
        }
        await context.close();
      }
    }
  } finally {
    const file = path.join(OUT, 'measurements.json');
    const prev = process.env.ONLY && fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, 'utf8')).states : {};
    report.states = Object.assign(prev, report.states);
    fs.writeFileSync(file, JSON.stringify(report, null, 1));
    await browser.close();
  }
})();
