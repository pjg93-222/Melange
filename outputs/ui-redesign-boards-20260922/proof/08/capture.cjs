/* Build 08 proof capture (Collection, board B22), re-runnable.

   node capture.cjs [port]        (default 8819; never 8806)

   Needs a READ-ONLY console on that port started from C:\Users\pgoff\Mentat:
     python mentat/app/server.py --port 8819 --read-only
   No collection is started: /api/runs and /api/run are answered by page.route
   with the fixtures below (the approach of test_console_browser.cjs), and
   /api/session is the console's own answer with read_only:false so Archive
   shows as it does on Paul's console. Writes shots\<state>_<W>x<H>.png and
   measurements.json. */
'use strict';
const path = require('path');
const fs = require('fs');
const modules = path.join(process.env.USERPROFILE, '.cache', 'codex-runtimes', 'codex-primary-runtime', 'dependencies', 'node', 'node_modules');
const {chromium} = require(require.resolve('playwright', {paths: [modules]}));
const PORT = Number(process.argv[2] || 8819);
if ([8806, 8801, 8802, 8841].includes(PORT) || (PORT >= 8820 && PORT <= 8829)) throw new Error('not your port');
const ORIGIN = `http://127.0.0.1:${PORT}`;
const OUT = __dirname, SHOTS = path.join(OUT, 'shots');
fs.mkdirSync(SHOTS, {recursive: true});
const SIZES = [[1440, 900], [1920, 1080], [1600, 900]];

const companies = ['Goldman Sachs Bank NA', 'Wells Fargo Bank NA', 'Morgan Stanley Bank', 'JP Morgan Chase Bank NA', 'Bank of America NA', 'PNC Bank NA', 'Capital One Bank NA'];
const cycles = [2022, 2024, 2026];
const today = new Date(); today.setSeconds(0, 0);
const at = (h, m) => { const d = new Date(today); d.setHours(h, m, 0, 0); return d; };
const rOffset = d => { const o = -d.getTimezoneOffset(), s = o >= 0 ? '+' : '-', a = Math.abs(o); return s + String(Math.floor(a / 60)).padStart(2, '0') + String(a % 60).padStart(2, '0'); };
const rTime = d => { const p = n => String(n).padStart(2, '0'); return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}.000${rOffset(d)}`; };
// Finished company/cycle tasks: [company index, cycle, rows, ended h:m]
const finished = [[0, 2022, 4102, [15, 12]], [0, 2024, 4390, [15, 21]], [0, 2026, 3926, [15, 31]], [1, 2022, 3311, [15, 14]], [1, 2024, 3420, [15, 20]], [1, 2026, 3171, [15, 27]],
  [2, 2022, 2980, [15, 25]], [2, 2024, 3024, [15, 33]], [3, 2022, 2804, [15, 29]], [3, 2024, 2813, [15, 34]], [4, 2022, 1450, [15, 34]]];
function runningRun(state = 'collecting') {
  const terminal = state !== 'collecting';
  const tasks = finished.map(([c, cycle, rows, [h, m]], i) => ({task_id: `t${i}`, company: companies[c], cycle, status: 'succeeded', rows, ended_at: rTime(at(h, m)), wall_clock_seconds: 140}));
  const progress = [
    {company: companies[2], cycle: 2026, kind: 'employer', rows_seen: 612, records_total: 1480, fetched_complete: 0, stored_complete: 0, updated_at: rTime(at(15, 33))},
    {company: companies[3], cycle: 2026, kind: 'employer', rows_seen: 344, records_total: 1302, fetched_complete: 0, stored_complete: 0, updated_at: rTime(at(15, 34))},
    {company: companies[4], cycle: 2024, kind: 'employer', rows_seen: 760, records_total: 1510, fetched_complete: 0, stored_complete: 0, updated_at: rTime(at(15, 34))},
    {company: companies[0], cycle: 2026, kind: 'corporate', rows_seen: 212, records_total: 212, fetched_complete: 1, stored_complete: 1, updated_at: rTime(at(15, 31))},
  ];
  const records = Array.from({length: 6}, (_, i) => ({sub_id: `SUB${1000 + i}`, contributor_name: ['A. Rivera', 'J. Chen', 'M. Okafor', 'S. Patel', 'L. Novak', 'R. Haines'][i], company: companies[i % 5], contribution_receipt_date: '2026-03-0' + (i + 1), contribution_receipt_amount: 250 * (i + 1), contributor_occupation: ['VICE PRESIDENT', 'ANALYST', 'CEO', 'DIRECTOR', 'ENGINEER', 'MANAGER'][i], committee_name: 'Example PAC'}));
  const run = {
    id: 'run-banking', name: 'Banking roster.csv', state,
    readiness: {status: 'succeeded', readiness: [{industry: 'Banking', ready: true, company_count: companies.length, companies: companies.map(company => ({company, variant_count: 2, exclusion_count: 0}))}]},
    resumable: state === 'stopped', resumed_from: null, elapsed_seconds: 1800, age_seconds: terminal ? 400 : 5,
    status: {stage: state === 'stopped' ? 'collecting' : 'collecting', current_industry: 'Banking', cycles, estimated_remaining_seconds: 2300,
      updated_at: rTime(at(15, 34)), fanout: {total: companies.length * cycles.length, completed: finished.length, running: 4, failed: 0},
      industries: [{industry: 'Banking', stage: 'collecting', started_at: at(15, 4).toISOString(), workers: {active_workers: 4, requested_workers: 4, scheduling: 'company_work_sharing', pending_companies: 2, company_handoffs: 3}}]},
    control: {}, lanes: [{id: 'industries/banking/fanout/lane-01', industry: 'Banking', label: 'lane-01', state: {status: terminal ? 'stopped' : 'running', lane: 1, completed: finished.length, total: 21, current_company: terminal ? null : companies[3], current_cycle: 2026, tasks}}],
    selected_lane: 'industries/banking/fanout/lane-01', preview: {available: true, progress, records},
    events: [{event: 'industry_started', industry: 'Banking', timestamp: at(15, 4).toISOString()}], reports: [], assurance: [], fec_coverage: [], source_snapshots: [],
  };
  return run;
}
function completedRun() {
  const run = runningRun('completed');
  const all = [];
  companies.forEach((company, c) => cycles.forEach((cycle, k) => all.push({task_id: `c${c}-${cycle}`, company, cycle, status: 'succeeded', rows: 1200 + 311 * c + 97 * k, ended_at: rTime(at(15, 10 + c * 6 + k * 2)), wall_clock_seconds: 150})));
  run.id = 'run-banking-sep19'; run.name = 'Banking roster.csv'; run.age_seconds = 9000; run.elapsed_seconds = 3480;
  run.status = {...run.status, stage: 'completed', estimated_remaining_seconds: null, fanout: {total: 21, completed: 21, running: 0, failed: 0}, industries: [{...run.status.industries[0], stage: 'completed'}]};
  run.lanes[0].state = {status: 'succeeded', lane: 1, completed: 21, total: 21, current_company: null, current_cycle: null, tasks: all};
  run.preview.progress = [];
  run.reports = [{name: 'Banking 2022-2026.xlsx', index: 0, quality: {direction_columns: true}, freshness: {sources: [], verified_source_count: 0, note: 'Fixture.'}}];
  return run;
}
const day = n => Math.floor(at(15, 4).getTime() / 1000) - n * 86400;
const historyRuns = [
  {id: 'run-banking-sep19', name: 'Banking roster.csv', state: 'completed', created_at: day(4), archived: false, can_archive: true, resumable: false},
  {id: 'run-credit-sep16', name: 'Credit unions roster.csv', state: 'stopped', created_at: day(7), archived: false, can_archive: true, resumable: true},
  {id: 'run-insurers-sep12', name: 'Insurers roster.xlsx', state: 'completed', created_at: day(11), archived: false, can_archive: true, resumable: false},
  {id: 'run-fintech-sep08', name: 'Fintech roster.csv', state: 'failed', created_at: day(15), archived: false, can_archive: true, resumable: false},
];
const scenarios = {
  running: {runs: [{id: 'run-banking', name: 'Banking roster.csv', state: 'collecting', created_at: day(0), archived: false, can_archive: false, resumable: false}, ...historyRuns], run: () => runningRun('collecting')},
  stopped: {runs: [{id: 'run-banking', name: 'Banking roster.csv', state: 'stopped', created_at: day(0), archived: false, can_archive: true, resumable: true}, ...historyRuns], run: () => runningRun('stopped')},
  completed: {runs: historyRuns, run: completedRun},
  empty: {runs: [], run: () => null},
  history: {runs: historyRuns, run: completedRun},
  folder: {runs: [{id: 'run-banking', name: 'Banking roster.csv', state: 'collecting', created_at: day(0), archived: false, can_archive: false, resumable: false}, ...historyRuns], run: () => runningRun('collecting')},
  mobile: {runs: [{id: 'run-banking', name: 'Banking roster.csv', state: 'collecting', created_at: day(0), archived: false, can_archive: false, resumable: false}, ...historyRuns], run: () => runningRun('collecting')},
};

(async () => {
  const browser = await chromium.launch({headless: true, channel: 'chrome'});
  const out = {port: PORT, captured_at: new Date().toISOString(), states: {}};
  try {
    for (const [W, H] of SIZES) {
      for (const [name, scenario] of Object.entries(scenarios)) {
        if (name === 'mobile' && W !== 1440) continue;
        const context = await browser.newContext({viewport: name === 'mobile' ? {width: 390, height: 844} : {width: W, height: H}});
        const page = await context.newPage();
        page.setDefaultTimeout(15000);
        const errors = [];
        page.on('pageerror', e => errors.push(e.message));
        await page.route('**/*', async route => {
          const url = new URL(route.request().url());
          if (url.origin !== ORIGIN) return route.abort();
          if (url.pathname === '/api/session') { const r = await route.fetch(); const body = await r.json(); return route.fulfill({json: {...body, read_only: false}}); }
          if (url.pathname === '/api/runs') { const r = await route.fetch(); const body = await r.json(); return route.fulfill({json: {...body, runs: scenario.runs, archived_count: 0, total_run_count: scenario.runs.length, read_only: false}}); }
          if (url.pathname === '/api/run') {
            const run = scenario.run(); const id = url.searchParams.get('id');
            if (!run) return route.fulfill({status: 404, json: {error: 'Run not found.'}});
            if (id && id !== run.id) { const other = historyRuns.find(item => item.id === id); if (other) return route.fulfill({json: {...completedRun(), id: other.id, name: other.name, state: other.state}}); }
            return route.fulfill({json: run});
          }
          return route.continue();
        });
        await page.goto(ORIGIN + '/#collection');
        for (const asset of ['app.js', 'style.css', 'ui-state.js']) await page.evaluate(a => fetch('/' + a, {cache: 'reload'}), asset);
        await page.reload();
        await page.waitForFunction(() => document.body.dataset.view === 'collection');
        if (name === 'completed') {
          await page.waitForSelector('#run-history-more:not([hidden])');
        }
        if (name === 'stopped') {
          await page.locator('[data-run-group=history]').click();
        }
        if (name === 'history') {
          await page.waitForSelector('#run-history-more:not([hidden])');
          await page.locator('.run-history-open[data-run-id="run-insurers-sep12"]').click();
          await page.waitForFunction(() => document.querySelector('#run-title').textContent === 'Insurers roster.xlsx');
        }
        if (name === 'empty') await page.waitForSelector('#empty:not([hidden])');
        else await page.waitForFunction(() => !document.querySelector('#monitor').hidden && document.querySelectorAll('#run-companies tr').length > 0);
        await page.waitForTimeout(700);
        if (name === 'folder') { await page.locator('#open-working-folder').click(); await page.waitForSelector('#working-folders:not([hidden])'); await page.waitForTimeout(400); }
        await page.evaluate(() => { if (document.activeElement?.id !== 'open-working-folder') document.activeElement?.blur(); for (const id of ['stale-banner', 'error']) { const el = document.getElementById(id); if (el) el.hidden = true; } window.scrollTo(0, 0); });
        const file = path.join(SHOTS, name === 'mobile' ? 'mobile_390x844.png' : `${name}_${W}x${H}.png`);
        await page.screenshot({path: file, fullPage: name === 'mobile'});
        if (name === 'history') await page.screenshot({path: path.join(SHOTS, `history_full_${W}x${H}.png`), fullPage: true});
        const measure = await page.evaluate(() => {
          const box = sel => { const el = document.querySelector(sel); if (!el || !el.getClientRects().length) return null; const r = el.getBoundingClientRect(); return {x: +r.x.toFixed(1), y: +r.y.toFixed(1), w: +r.width.toFixed(1), h: +r.height.toFixed(1), right: +r.right.toFixed(1), bottom: +r.bottom.toFixed(1)}; };
          const visible = el => !!el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden';
          const golds = [...document.querySelectorAll('#view-collection .primary--gold, .workspace .primary--gold')].filter(visible).map(el => el.id);
          const rows = [...document.querySelectorAll('#run-companies tr')].map(tr => [...tr.cells].map(td => td.innerText.trim()));
          const overlaps = [];
          const actions = [...document.querySelectorAll('#run-controls > :not([hidden]), #run-controls .run-folder > button')].filter(visible);
          for (let i = 0; i < actions.length; i++) for (let j = i + 1; j < actions.length; j++) { const a = actions[i].getBoundingClientRect(), b = actions[j].getBoundingClientRect(); if (a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom && !actions[i].contains(actions[j]) && !actions[j].contains(actions[i])) overlaps.push([actions[i].id, actions[j].id]); }
          return {
            title: box('#workspace-title'), pill: box('#stage'), pillText: document.querySelector('#stage').innerText, pillState: document.querySelector('#stage').dataset.runState,
            tabs: box('.run-collections'), tabActive: box('.run-collections [aria-pressed=true]'), toolbar: box('#run-toolbar'), history: box('#run-history'),
            card: box('#run-card'), runTitle: box('#run-title'), subtitle: box('#run-subtitle'), subtitleText: document.querySelector('#run-subtitle').innerText,
            track: box('.run-progress .progress-track'), label: box('.run-progress-label'), labelText: document.querySelector('.run-progress-label').innerText,
            steps: [...document.querySelectorAll('.run-step')].map(li => ({state: li.className.replace('run-step run-step--', ''), mark: (r => ({x: +r.x.toFixed(1), y: +r.y.toFixed(1), w: +r.width.toFixed(1)}))(li.querySelector('.run-step-mark').getBoundingClientRect())})),
            thead: box('.run-companies thead tr'), rowsBox: box('#run-companies'), rows,
            stop: box('#stop'), stopText: document.querySelector('#stop').innerText, resume: box('#resume-run'), folder: box('#open-working-folder'), gold: box('#view-partial-results'), goldText: document.querySelector('#view-partial-results').innerText, goldDisabled: document.querySelector('#view-partial-results').disabled,
            note: box('#run-card-note'), details: box('#run-details'), empty: box('#empty'), goldButtons: golds, actionOverlaps: overlaps,
            scrollOverflow: document.documentElement.scrollWidth > innerWidth, popover: box('#working-folders'),
            historyItems: [...document.querySelectorAll('.run-history-item')].map(li => li.innerText.replace(/\s+/g, ' ').trim()),
          };
        });
        out.states[`${name}_${W}`] = {...measure, errors};
        await page.unrouteAll({behavior: 'ignoreErrors'});
        await context.close();
        console.log('captured', name, W, errors.length ? errors : '');
      }
    }
  } finally {
    await browser.close();
    fs.writeFileSync(path.join(OUT, 'measurements.json'), JSON.stringify(out, null, 1));
  }
})().catch(error => { console.error(error); process.exit(1); });
