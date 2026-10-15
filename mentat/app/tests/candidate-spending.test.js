'use strict';
/* candidate-spending.js: how a candidate's campaign spent its money (FEC Schedule B), the hover card and the docked panel.
   The ring's arithmetic (shares that sum to one, segments that span 360 degrees), every state of the card and the panel as
   the markup the page draws, the comparison bar and its fewer-than-five rule, one read per candidate and cycle, the 150 ms
   debounce, and the gestures a candidate's tooltip tells. The campaign's own spending is never this flow's dollars: the card
   and the panel say so. Interaction runs in the browser pass. */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const spend = require('../candidate-spending.js');
const layout = require('../flow-layout.js');
const chart = require('../flow-chart.js');

const PALETTE = ['#327a7a', '#57447b', '#8b6984', '#eca91c', '#de8aab', '#7d4b00', '#3cb0a3', '#83333e', '#99973f',
  '#a09eea', '#d88766', '#509ecd'];
const CTX = {name: 'Garland Barr', cycle: 2024, palette: PALETTE, neutral: '#a39b92'};
const TWO_PI = 2 * Math.PI;
const near = (a, b, why) => assert.ok(Math.abs(a - b) < 1e-9, `${why || ''} ${a} vs ${b}`);

// A server answer. Ten categories, so the ring has to fold the tail into Other.
const LIST = [['contributions_transfers', 40], ['consulting', 25], ['payroll', 9], ['events', 7], ['printing_mail', 5], ['polling_data', 4],
  ['travel', 3], ['legal_compliance', 2.5], ['office', 2], ['fundraising_fees', 1.5], ['other', 1]];
function body(extra) {
  const categories = LIST.map(([key, amount]) => ({key, label: spend.LABELS[key], amount: amount * 1000, share: amount / 100, payments: Math.round(amount)}));
  return Object.assign({status: 'ok', committee_name: 'ANDY BARR FOR CONGRESS, INC.', cycle: 2024, coverage_status: 'complete',
    coverage_reasons: [], total_itemized: 100000, reported_total: 100000, coverage: 1, coverage_unknown: false, positive_total: 100000,
    categories, dropped_negative: []}, extra || {});
}
const detail = extra => Object.assign(body(), {
  payees: {consulting: [{payee: 'THE STANTON GROUP, LLC', amount: 20000, payments: 12}, {payee: 'TARGETED VICTORY', amount: 5000, payments: 3}],
    travel: [{payee: 'DELTA AIRLINES', amount: 3000, payments: 4}], contributions_transfers: [{payee: 'NRCC', amount: 40000, payments: 1}]},
  payments: {
    consulting: {total: 412, rows: Array.from({length: 100}, (_, at) => ({date: `2024-03-${String(1 + at % 28).padStart(2, '0')}`, payee: `PAYEE ${at}`,
      purpose: 'FUNDRAISING CONSULTING', amount: 100 + at, url: 'https://docquery.fec.gov/cgi-bin/fecimg/?202501319748746337'}))},
    travel: {total: 1, rows: [{date: '2024-05-02', payee: 'DELTA <AIRLINES>', purpose: 'TRAVEL EXPENSE', amount: 250.5, url: ''}]}}}, extra || {});
const sum = list => list.reduce((total, value) => total + value, 0);
const style = markup => / style=|<style/.test(markup);

test('the ring: top seven categories and Other, shares sum to one, segments span 360 degrees with no gap', () => {
  const model = spend.ring(body(), {palette: PALETTE});
  assert.equal(model.items.length, 8, 'seven named and Other');
  assert.deepEqual(model.items.map(item => item.key).slice(0, 7), ['contributions_transfers', 'consulting', 'payroll', 'events', 'printing_mail', 'polling_data', 'travel']);
  const rest = model.items[7];
  assert.equal(rest.key, 'other');
  near(rest.amount, 2500 + 2000 + 1500 + 1000, 'the folded tail plus the real Other');
  near(sum(model.items.map(item => item.share)), 1, 'shares');
  assert.equal(model.segments[0].start, 0);
  for (let at = 1; at < model.segments.length; at += 1) near(model.segments[at].start, model.segments[at - 1].end, 'contiguous');
  near(model.segments[model.segments.length - 1].end, TWO_PI, 'spans 360 degrees');
  near(sum(model.segments.map(item => item.end - item.start)), TWO_PI, 'swept angles');
  assert.deepEqual(model.centre, {amount: 100000, words: 'spent'});
  assert.equal(model.partial, false);
});

test('the panel ring names every category and still closes on 360 degrees', () => {
  const model = spend.ring(body(), {top: Infinity});
  assert.equal(model.items.length, 11);
  near(sum(model.items.map(item => item.share)), 1);
  near(model.segments[10].end, TWO_PI);
});

test('low coverage: the ring is drawn over what was reported and what was not itemized is its own hatched segment', () => {
  const low = body({coverage: 0.61, coverage_unknown: false, reported_total: 163934.43});
  const model = spend.ring(low, {palette: PALETTE});
  assert.equal(model.partial, true);
  assert.equal(model.segments.length, 9);
  const last = model.segments[8];
  assert.equal(last.key, 'not_itemized');
  assert.equal(last.label, 'Not itemized');
  near(last.amount, 63934.43, 'the remainder is what was reported less what was itemized');
  near(sum(model.segments.map(item => item.share)), 1, 'shares with the remainder');
  near(last.end, TWO_PI);
  assert.deepEqual(model.centre, {amount: 163934.43, words: 'reported'});
  const svg = spend.donutSvg(low, model, {size: 124, cycle: 2024});
  assert.ok(/<pattern id="spd\d+-hatch"/.test(svg) && svg.includes('fill="url(#spd'), 'the remainder is hatched, not a category colour');
  assert.ok(!style(svg), 'CSP: no inline style');
});

test('full coverage and unknown coverage draw no remainder; coverage text never rounds up to a claim of all', () => {
  assert.equal(spend.ring(body(), {}).remainder, null);
  assert.equal(spend.ring(body({coverage: null, coverage_unknown: true, reported_total: null}), {}).remainder, null);
  assert.equal(spend.coverageText(0.9977), '99.7%');
  assert.equal(spend.coverageText(1), '100%');
  assert.equal(spend.coverageText(1.02), '100%');
  assert.equal(spend.coverageText(0.614), '61%');
});

test('arcPath: a sector, a large arc past half, and a whole ring as two half arcs each way', () => {
  const quarter = spend.arcPath(50, 50, 40, 24, 0, Math.PI / 2);
  assert.ok(quarter.startsWith('M50 10A40 40 0 0 1 90 50L74 50A24 24 0 0 0 50 26Z'), quarter);
  assert.ok(/A40 40 0 1 1/.test(spend.arcPath(50, 50, 40, 24, 0, Math.PI * 1.5)), 'a large arc');
  const whole = spend.arcPath(50, 50, 40, 24, 0, TWO_PI);
  assert.equal((whole.match(/A/g) || []).length, 4);
  assert.equal((whole.match(/Z/g) || []).length, 2);
});

test('the donut is a labelled image: the three largest categories are said, the ring is hand-written SVG', () => {
  const model = spend.ring(body(), {palette: PALETTE});
  const svg = spend.donutSvg(body(), model, {size: 124, cycle: 2024});
  assert.ok(svg.includes('role="img"'));
  assert.ok(svg.includes('aria-label="How the campaign spent its money, ANDY BARR FOR CONGRESS, INC., 2023–24. Largest: Contributions &amp; transfers 40%, Consulting 25%, Payroll &amp; staff 9%."'), svg.slice(0, 400));
  assert.equal((svg.match(/<path class="flow-spend-seg/g) || []).length, 8);
  assert.ok(svg.includes('$100K</text>') && svg.includes('>spent</text>'));
  assert.ok(!style(svg));
});

test('a category keeps its colour from campaign to campaign: one palette slot each, Other is the flow neutral', () => {
  const colours = spend.CATEGORIES.map(([key]) => spend.colourOf(key, PALETTE, '#a39b92'));
  assert.equal(spend.colourOf('other', PALETTE, '#a39b92'), '#a39b92');
  assert.equal(new Set(colours).size, colours.length, 'no two categories share a colour');
  const small = Object.assign(body(), {categories: body().categories.slice(1, 3)});
  assert.equal(spend.ring(small, {palette: PALETTE}).segments[0].colour, spend.colourOf('consulting', PALETTE));
});

/* ------------------------------------------------------------------------------------------------ the card */
test('the card: committee, the sentence under it, a legend of percent and dollars, and the footer that says whose dollars', () => {
  const html = spend.cardHtml({kind: 'ok', body: body()}, CTX);
  assert.ok(html.includes('ANDY BARR FOR CONGRESS, INC.'));
  assert.ok(html.includes('How the campaign spent its money · 2023–24'));
  assert.ok(html.includes('<span class="flow-spend-pct">40%</span><span class="flow-spend-amt">$40K</span>'));
  assert.equal((html.match(/class="flow-spend-row/g) || []).length, 8);
  assert.ok(html.includes("Itemized FEC Schedule B · covers 100% of reported spending · the campaign's own spending, not this flow's dollars"), html.slice(-300));
  assert.ok(!html.includes('flow-spend-chip'), 'no chip at full coverage');
  assert.ok(!style(html));
});

test('the card: under 90% coverage an amber chip says so, with a Not itemized row in the legend', () => {
  const html = spend.cardHtml({kind: 'ok', body: body({coverage: 0.61, reported_total: 163934.43})}, CTX);
  assert.ok(html.includes('Itemized payments cover 61% of reported spending'));
  assert.ok(html.includes('Not itemized'));
  assert.ok(html.includes('covers 61% of reported spending'));
  assert.ok(html.includes('>reported</text>'));
});

test('the card: a partial campaign shows the chip with the reason in its tooltip; with no totals it says coverage is unknown', () => {
  const partial = spend.cardHtml({kind: 'ok', body: body({coverage_status: 'partial', coverage: 0.97, coverage_reasons: ['ZED FOR CONGRESS II: partial (Schedule B pending, totals unsupported)']})}, CTX);
  assert.ok(partial.includes('Itemized payments cover 97% of reported spending'));
  assert.ok(partial.includes('title="ZED FOR CONGRESS II: partial (Schedule B pending, totals unsupported)"'));
  const unknown = spend.cardHtml({kind: 'ok', body: body({coverage_status: 'partial', coverage: null, coverage_unknown: true, reported_total: null,
    coverage_reasons: ['ANDY BARR FOR CONGRESS, INC.: partial (Schedule B pending, totals pending)']})}, CTX);
  assert.ok(unknown.includes('Coverage unknown — itemized sample only'));
  assert.ok(unknown.includes('Itemized FEC Schedule B · coverage unknown'));
  assert.ok(!unknown.includes('covers '), 'no percentage is made up');
  assert.ok(!unknown.includes('Not itemized'), 'and no remainder is drawn');
});

test('the card: loading, not collected and error are drawn as their own states', () => {
  const loading = spend.cardHtml({kind: 'loading'}, CTX);
  assert.ok(loading.includes('data-state="loading"') && loading.includes('Reading FEC payments…') && loading.includes('is-ghost'));
  assert.ok(loading.includes('Garland Barr'), 'named by the node until the committee is known');
  const missing = spend.cardHtml({kind: 'missing'}, CTX);
  assert.ok(missing.includes('data-state="missing"') && missing.includes('Spending not collected for 2023–24') && missing.includes('is-dashed'));
  const words = spend.cardHtml({kind: 'missing', message: 'Campaign committee not identified for 2025–26'}, Object.assign({}, CTX, {cycle: 2026}));
  assert.ok(words.includes('Campaign committee not identified for 2025–26'));
  const unavailable = spend.cardHtml({kind: 'missing', message: 'Spending source not installed'}, CTX);
  assert.ok(unavailable.includes('Spending source not installed'));
  const error = spend.cardHtml({kind: 'error', message: 'Refresh the app before continuing.'}, CTX);
  assert.ok(error.includes('data-state="error"') && error.includes('role="alert"') && error.includes('Refresh the app before continuing.'));
  for (const html of [loading, missing, error]) assert.ok(!style(html));
});

test('the card escapes what it is given', () => {
  const html = spend.cardHtml({kind: 'ok', body: body({committee_name: '<img src=x onerror=alert(1)>'})}, CTX);
  assert.ok(!html.includes('<img') && html.includes('&lt;img src=x onerror=alert(1)&gt;'));
  assert.ok(!spend.cardHtml({kind: 'missing', message: '<b>x</b>'}, CTX).includes('<b>x'));
});

test('a campaign with nothing itemized is not drawn as an empty ring', () => {
  const html = spend.cardHtml({kind: 'ok', body: body({categories: []})}, CTX);
  assert.ok(html.includes('data-state="missing"') && html.includes('No itemized spending on file for this campaign'));
});

/* ------------------------------------------------------------------------------------------ comparison bar */
const peers = (n, extra) => Object.assign({n, office: 'H', cycle: 2024, min: 5, too_few: n < 5, label: `Median of ${n} collected House campaigns, 2023–24`,
  shares: {contributions_transfers: 0.3, consulting: 0.3, payroll: 0.2, events: 0.1, travel: 0.1}}, extra || {});

test('the comparison bar is hidden with fewer than five peers, whatever the flag says, with the reason beside it', () => {
  for (const n of [0, 1, 4]) {
    const mode = spend.compare(body({peers: peers(n, {too_few: false})}));
    assert.equal(mode.hidden, true, `${n} peers`);
    assert.equal(mode.note, 'Too few collected campaigns to compare');
  }
  assert.equal(spend.compare(body({peers: peers(7, {too_few: true})})).hidden, true, 'the server says too few');
  assert.equal(spend.compare(body({peers: peers(5)})).hidden, false);
  assert.equal(spend.compare(body()).hidden, true, 'no peers asked for');
  const html = spend.compareHtml(body({peers: peers(4)}), CTX);
  assert.ok(html.includes('Too few collected campaigns to compare') && !html.includes('flow-spend-stack'));
});

test('the comparison bar: two 100% stacked bars in one category order, labelled with how many campaigns the median is over', () => {
  const html = spend.compareHtml(body({peers: peers(7)}), CTX);
  assert.ok(html.includes('data-compare="shown"'));
  assert.ok(html.includes('Median of 7 collected House campaigns, 2023–24'));
  assert.ok(html.includes('This campaign · 2023–24'));
  const bars = html.split('<svg class="flow-spend-stack"').slice(1);
  assert.equal(bars.length, 2);
  for (const bar of bars) {
    const widths = [...bar.matchAll(/width="([\d.]+)" height="16" fill="(#[0-9a-f]{6})"/g)].map(match => Number(match[1]));
    near(sum(widths), 300, 'a stacked bar spans the whole width');
  }
  const order = bar => [...bar.matchAll(/<title>([^<]+?) \d+%<\/title>/g)].map(match => match[1].replace(/&amp;/g, '&'));
  const labels = spend.CATEGORIES.map(item => item[1]);
  for (const bar of bars) assert.deepEqual(order(bar), order(bar).slice().sort((a, b) => labels.indexOf(a) - labels.indexOf(b)), 'fixed order');
  assert.ok(html.includes('rescaled to 100%'));
  assert.ok(!style(html));
});

/* ------------------------------------------------------------------------------------------------ the panel */
const PANEL = Object.assign({}, CTX, {rows: true, link: url => (/^https:\/\/docquery\.fec\.gov\//.test(url || '') ? url : '')});

test('the panel: the title, a big ring, the largest category chosen, its top payees, and the footer note', () => {
  const html = spend.panelHtml({kind: 'ok', body: detail({peers: peers(3)})}, PANEL, {});
  assert.ok(html.includes('ANDY BARR FOR CONGRESS, INC. · 2023–24 spending'));
  assert.ok(html.includes('class="flow-spend-donut is-big"') && html.includes('width="220"'));
  assert.ok(html.includes('aria-label="Close spending panel"'));
  assert.ok(html.includes('<h4 class="flow-spend-h">Top payees in Contributions &amp; transfers</h4>'), 'the largest is the default');
  assert.ok(html.includes('NRCC') && html.includes('$40,000'));
  assert.ok(html.includes("Categories assigned from each payment&#39;s stated purpose · Refunds and transfers to other committees shown separately · The campaign&#39;s own spending, not a trace of this flow&#39;s dollars"));
  assert.ok(html.includes('data-spend-rows') && html.includes('Open in Rows'));
  assert.ok(html.includes('data-compare="hidden"') && html.includes('Too few collected campaigns to compare'));
  assert.ok(html.includes('data-cat="consulting"') && html.includes('aria-pressed="true"'));
  assert.ok(!style(html));
  const noRows = spend.panelHtml({kind: 'ok', body: detail()}, Object.assign({}, PANEL, {rows: false}), {});
  assert.ok(!noRows.includes('data-spend-rows'));
});

test('the panel: choosing a category changes the payees; at most five are listed; a category with none says so', () => {
  const view = {category: 'travel'};
  const html = spend.panelHtml({kind: 'ok', body: detail()}, PANEL, view);
  assert.ok(html.includes('Top payees in Travel') && html.includes('DELTA AIRLINES'));
  assert.ok(html.includes('data-cat="travel"') && /data-cat="travel"[^>]*aria-pressed="true"/.test(html));
  const many = detail();
  many.payees.consulting = Array.from({length: 9}, (_, at) => ({payee: `P${at}`, amount: 100 - at, payments: 1}));
  const five = spend.payeesHtml(many, 'consulting');
  assert.equal(five.split('<tr><td class="flow-spend-payee">').length - 1, 9, 'the view lists what the server sent (the server caps at five)');
  assert.ok(spend.payeesHtml(body(), 'events').includes('No itemized payees'));
  assert.ok(spend.panelHtml({kind: 'ok', body: detail()}, PANEL, {category: 'nonsense'}).includes('Top payees in Contributions'), 'an unknown choice falls back to the largest');
});

test('the panel: Open payments lists the category\'s payments, each linking to its FEC filing, the first hundred and the count of the rest', () => {
  const closed = spend.panelHtml({kind: 'ok', body: detail()}, PANEL, {category: 'consulting'});
  assert.ok(closed.includes('aria-expanded="false"') && closed.includes('Open payments') && !closed.includes('flow-spend-payments'));
  const open = spend.panelHtml({kind: 'ok', body: detail()}, PANEL, {category: 'consulting', payments: true});
  assert.ok(open.includes('aria-expanded="true"') && open.includes('Hide payments') && open.includes('class="flow-spend-scroll"'));
  assert.equal((open.match(/<tr><td class="flow-spend-date">/g) || []).length, 100);
  assert.equal((open.match(/<a href="https:\/\/docquery\.fec\.gov\/cgi-bin\/fecimg\/\?202501319748746337" target="_blank" rel="noopener noreferrer">/g) || []).length, 100);
  assert.ok(open.includes('Showing the first 100 of 412 payments, newest first.'));
  assert.ok(open.includes('Consulting · 412 payments'));
  const small = spend.panelHtml({kind: 'ok', body: detail()}, PANEL, {category: 'travel', payments: true});
  assert.ok(small.includes('DELTA &lt;AIRLINES&gt;') && small.includes('$250.50'));
  assert.ok(!small.includes('<a href'), 'a payment with no filing link is plain text, never a made-up link');
  assert.ok(!small.includes('Showing the first'));
  const unvetted = spend.paymentsHtml(detail(), 'consulting', () => '');
  assert.ok(!unvetted.includes('<a href'), 'MentatScope.fecLink refuses a link: no link');
});

test('the panel: loading, not collected and error states, with Open in Rows and Close still offered', () => {
  for (const [state, word] of [[{kind: 'loading'}, 'Reading FEC payments…'], [{kind: 'missing'}, 'Spending not collected for 2023–24'],
    [{kind: 'error', message: 'No.'}, 'No.']]) {
    const html = spend.panelHtml(state, PANEL, {});
    assert.ok(html.includes(word), word);
    assert.ok(html.includes('data-spend-close') && html.includes('Open in Rows'), word);
    assert.ok(html.includes("The campaign&#39;s own spending"), 'the footer is there in every state');
  }
});

test('the panel: the same chip and Not itemized segment as the card; the segment is not a button', () => {
  const html = spend.panelHtml({kind: 'ok', body: detail({coverage: 0.5, reported_total: 200000})}, PANEL, {});
  assert.ok(html.includes('Itemized payments cover 50% of reported spending'));
  assert.ok(/<path class="flow-spend-seg is-hatched"[^>]*role="img"/.test(html));
  assert.ok(!/data-cat="not_itemized"[^>]*role="button"/.test(html));
  const unknown = spend.panelHtml({kind: 'ok', body: detail({coverage: null, coverage_status: 'partial', coverage_unknown: true, reported_total: null})}, PANEL, {});
  assert.ok(unknown.includes('Coverage unknown — itemized sample only') && !unknown.includes('is-hatched'));
});

test('the panel marks the chosen segment and gives every segment a readable name and a pull-out offset', () => {
  const html = spend.panelHtml({kind: 'ok', body: detail()}, PANEL, {category: 'consulting'});
  assert.ok(/<path class="flow-spend-seg is-selected"[^>]*data-cat="consulting"/.test(html));
  assert.ok(html.includes('aria-label="Consulting 25%, $25K, 25 payments"'));
  assert.ok(/data-pull="-?[\d.]+ -?[\d.]+"/.test(html));
  assert.ok(html.includes('data-default="Consulting 25% · $25K · 25 payments"'), 'what the readout says until a segment is hovered');
  assert.ok(spend.panelHtml({kind: 'ok', body: detail()}, PANEL, {}).includes('data-default="Contributions &amp; transfers 40% · $40K · 40 payments"'), 'the largest by default');
});

/* ------------------------------------------------------------------------------------- one read per candidate */
const reply = (status, value) => ({ok: status >= 200 && status < 300, status, json: async () => value});

test('one read per candidate and cycle: a second ask shares the first request and a kept answer is not asked for again', async () => {
  const seen = [];
  const client = spend.client(async url => { seen.push(url); await Promise.resolve(); return reply(200, body()); });
  const [a, b] = await Promise.all([client.load('H0KY06104', 2024, {name: 'BARR, GARLAND ANDY'}), client.load('H0KY06104', 2024, {name: 'BARR, GARLAND ANDY'})]);
  assert.equal(seen.length, 1, 'one request in flight per key');
  assert.equal(a, b);
  await client.load('H0KY06104', 2024, {name: 'BARR, GARLAND ANDY'});
  assert.equal(seen.length, 1, 'kept');
  assert.equal(seen[0], '/api/candidate-spending?candidate=H0KY06104&cycle=2024&name=BARR%2C%20GARLAND%20ANDY');
});

test('the detail read carries the peers the chart offers and also serves the light one', async () => {
  const seen = [];
  const client = spend.client(async url => { seen.push(url); return reply(200, detail()); });
  await client.load('H0KY06104', 2026, {detail: true, name: 'BARR, GARLAND ANDY', peers: ['H6TX18232', 'H6GA13070']});
  assert.equal(seen[0], '/api/candidate-spending?candidate=H0KY06104&cycle=2026&name=BARR%2C%20GARLAND%20ANDY&detail=1&peers=H6GA13070%2CH6TX18232');
  assert.ok(client.peek('H0KY06104', 2026, {name: 'BARR, GARLAND ANDY'}), 'the light card reuses the detail answer');
  assert.equal(client.peek('H0KY06104', 2026, {detail: true, peers: ['H1XX00001']}), null, 'a different peer set is a different read');
});

test('what the server says when there is nothing to draw becomes the card\'s words, never an empty ring', async () => {
  const client = spend.client(async url => {
    if (url.includes('H0AA00001')) return reply(404, {status: 'not_collected', error: 'Spending not collected for 2023–24'});
    if (url.includes('H0AA00002')) return reply(404, {status: 'mapping_unknown', error: 'Campaign committee not identified for 2023–24'});
    if (url.includes('H0AA00003')) return reply(503, {status: 'source_unavailable', error: 'Spending source not installed'});
    return reply(403, {error: 'Refresh the app before continuing.'});
  });
  assert.deepEqual(await client.load('H0AA00001', 2024), {kind: 'missing', message: 'Spending not collected for 2023–24', body: {status: 'not_collected', error: 'Spending not collected for 2023–24'}});
  assert.equal((await client.load('H0AA00002', 2024)).message, 'Campaign committee not identified for 2023–24');
  assert.equal((await client.load('H0AA00003', 2024)).message, 'Spending source not installed');
  assert.equal((await client.load('H0AA00004', 2024)).kind, 'error');
});

test('a failure is not kept: the next hover asks again; a refused fetch is an error state', async () => {
  let calls = 0;
  const client = spend.client(async () => { calls += 1; if (calls === 1) throw new Error('offline'); return reply(200, body()); });
  assert.equal((await client.load('H0KY06104', 2024)).kind, 'error');
  assert.equal((await client.load('H0KY06104', 2024)).kind, 'ok');
  assert.equal(calls, 2);
});

test('only an individual candidate in an even cycle has a card: not the industry flow\'s aggregate outcome, not a stub', () => {
  const node = {kind: 'candidate', candidate_id: 'H0KY06104'};
  assert.equal(spend.eligible(node, 2024), true);
  assert.equal(spend.eligible({kind: 'candidate', outcome: true, label: 'Contributions to candidates'}, 2024), false);
  assert.equal(spend.eligible({kind: 'candidate', candidate_id: ''}, 2024), false);
  assert.equal(spend.eligible({kind: 'committee', candidate_id: 'H0KY06104'}, 2024), false);
  assert.equal(spend.eligible({kind: 'candidate', candidate_id: 'H0KY06104', stub: 'onward'}, 2024), false);
  assert.equal(spend.eligible(node, 2023), false);
  assert.equal(spend.eligible(node, undefined), false);
  for (const id of ['H0KY06104', 'S6AL00476', 'P80001571']) assert.equal(spend.eligible({kind: 'candidate', candidate_id: id}, 2026), true, id);
});

/* ------------------------------------------------------------------------------------------- the debounce */
// A stand-in document: enough DOM for controller() to add its section to a tooltip and write its markup.
function fakeDocument() {
  const make = () => ({className: '', innerHTML: '', children: [], classes: new Set(), appendChild(child) { this.children.push(child); },
    classList: {add: name => made.classes.add(name), remove: name => made.classes.delete(name)}});
  const made = make();
  return {tip: Object.assign(make(), {classList: {add(name) { this.set.add(name); }, remove(name) { this.set.delete(name); }, set: new Set()}}),
    doc: {createElement: () => make(), addEventListener() {}, removeEventListener() {}}};
}

test('150 ms on a node before anything is asked: a sweep across the column reads nothing, staying reads once', async t => {
  t.mock.timers.enable({apis: ['setTimeout']});
  const seen = [];
  const {tip, doc} = fakeDocument();
  const control = spend.controller({ownerDocument: doc}, {fetcher: async url => { seen.push(url); return reply(200, body()); }, after() {}});
  const nodes = ['H0AA00001', 'H0AA00002', 'H0AA00003'].map(id => ({id: `candidate:${id}:support`, kind: 'candidate', candidate_id: id, label: id}));
  for (const node of nodes) { control.section(tip, node, 2024); t.mock.timers.tick(100); }        // each one is left within 150 ms
  control.cancel();
  t.mock.timers.tick(500);
  assert.equal(seen.length, 0, 'nothing was asked for');
  control.section(tip, nodes[2], 2024);
  assert.ok(tip.children[tip.children.length - 1].innerHTML.includes('Reading FEC payments…'), 'the skeleton ring shows at once');
  t.mock.timers.tick(149);
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(seen.length, 0, 'not before 150 ms');
  t.mock.timers.tick(1);
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(seen.length, 1, 'once, at 150 ms');
  assert.ok(seen[0].includes('candidate=H0AA00003'));
  await new Promise(resolve => setImmediate(resolve));
  assert.ok(tip.children[tip.children.length - 1].innerHTML.includes('data-state="ok"'), 'the answer replaces the skeleton');
});

/* ------------------------------------------------------------------------------------ the tooltip's hint */
test('a candidate\'s tooltip tells a click opens the spending detail, Shift-click pins; without a panel it still says Rows', () => {
  const contract = JSON.parse(fs.readFileSync(path.resolve(__dirname, '..', '..', '..', 'audits', 'mentat_failings_20260915', 'contracts', 'flow.json'), 'utf8'));
  const flow = contract.examples.find(item => item.name.startsWith('FAIRSHAKE 2023-2024')).body;
  const result = layout.layout(flow, {width: 1100, height: 520});
  const node = result.nodes.find(item => item.kind === 'candidate' && item.candidate_id);
  assert.ok(node, 'the contract flow has an individual candidate');
  const context = {result, format: {short: chart.short, full: chart.full}};
  const hint = hints => chart.describe({node}, context, flow, hints).hint;
  assert.equal(hint({zoom: true, rows: true, spend: true, cycle: 2024}), 'Click for spending detail · Shift-click to pin');
  assert.equal(hint({zoom: true, rows: true, spend: false, cycle: 2024}), 'Click to open in Rows · Shift-click to pin');
  assert.equal(hint({zoom: true, rows: true, spend: true, cycle: 2023}), 'Click to open in Rows · Shift-click to pin', 'an odd cycle has no spending');
  assert.equal(hint(null), '');
});
