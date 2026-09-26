'use strict';
/* flow-chart.js (lane F): the SVG the Flow views draw, read as markup. Gradient ribbons
   (userSpaceOnUse, source colour into target colour), the other ribbon modes, the 40%
   default opacity, board #44's sublines, party rings, escaping, no inline style (CSP),
   unique ids per chart, and the pooled-money tooltip. Interaction runs in the browser pass. */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const layout = require('../flow-layout.js');
const chart = require('../flow-chart.js');

const CONTRACTS = path.resolve(__dirname, '..', '..', '..', 'audits', 'mentat_failings_20260915', 'contracts');
const contract = JSON.parse(fs.readFileSync(path.join(CONTRACTS, 'flow.json'), 'utf8'));
const FAIRSHAKE = contract.examples.find(item => item.name.startsWith('FAIRSHAKE 2023-2024')).body;
const FIXTURE = contract.examples.find(item => item.name.startsWith('a committee flow')).body;
const PALETTE = ['#327a7a', '#57447b', '#8b6984', '#eca91c', '#de8aab', '#7d4b00', '#3cb0a3', '#83333e', '#99973f',
  '#a09eea', '#d88766', '#509ecd'];
const all = (text, pattern) => [...text.matchAll(pattern)];

test('gradient ribbons: one userSpaceOnUse gradient per ribbon, source colour into target colour', () => {
  const svg = chart.svgString(FAIRSHAKE, {width: 1200, height: 560, palette: PALETTE});
  const result = layout.layout(FAIRSHAKE, {width: 1200, height: 560});
  const colours = layout.colours(result, PALETTE, '#a39b92');
  const gradients = all(svg, /<linearGradient id="flow-g-(\d+)" gradientUnits="userSpaceOnUse" x1="([\d.]+)" y1="0" x2="([\d.]+)" y2="0"><stop offset="0" stop-color="(#[0-9a-f]{6})" stop-opacity="([01])"\/><stop offset="1" stop-color="(#[0-9a-f]{6})" stop-opacity="([01])"\/>/g);
  assert.equal(gradients.length, result.links.length);
  for (const match of gradients) {
    const link = result.links[Number(match[1])];
    const source = result.nodes.find(node => node.id === link.source);
    const target = result.nodes.find(node => node.id === link.target);
    assert.equal(Number(match[2]), Math.round(link.gradient.x1 * 100) / 100);
    assert.equal(Number(match[3]), Math.round(link.gradient.x2 * 100) / 100);
    if (!source.stub && !target.stub) {
      assert.equal(match[4], colours.get(source.id));
      assert.equal(match[6], colours.get(target.id));
      assert.deepEqual([match[5], match[7]], ['1', '1']);
    }
  }
  assert.equal(all(svg, /class="flow-link[^"]*"[^>]*fill-opacity="0.4"/g).length, result.links.length);
});

test('Source, Target and Outcome colour ribbons by a node, never by an original donor', () => {
  const result = layout.layout(FAIRSHAKE);
  const colours = layout.colours(result, PALETTE, '#a39b92');
  for (const mode of ['source', 'target', 'outcome']) {
    const svg = chart.svgString(FAIRSHAKE, {ribbons: mode, palette: PALETTE});
    const moreno = all(svg, /<path class="flow-link" data-link="committee:C00836221&#8594;candidate:S4OH00192:support/g);
    assert.equal(moreno.length, 0, 'data-link ids are raw arrows, escaped only when needed');
    const fill = svg.match(/data-link="committee:C00836221→candidate:S4OH00192:support→ie_support" d="[^"]+" fill="([^"]+)"/)[1];
    if (mode === 'source') assert.equal(fill, colours.get('committee:C00836221'));   // the pooling committee's colour
    if (mode === 'target') assert.equal(fill, colours.get('candidate:S4OH00192:support'));
    if (mode === 'outcome') assert.equal(fill, colours.get('candidate:S4OH00192:support'));
    assert.notEqual(fill, colours.get('donor:COINBASE'));
  }
});

test("board #44's words under the bars, party rings and short money", () => {
  const svg = chart.svgString(FAIRSHAKE, {palette: PALETTE});
  assert.ok(svg.includes('>Coinbase</text>'));
  assert.ok(svg.includes('>$68.5M</text>'));
  assert.ok(svg.includes('>incl. $23.0M bitcoin still held</text>'));
  assert.ok(svg.includes('>cash $64.2M + bitcoin $23.0M</text>'));
  assert.ok(svg.includes('>Other donors $5.8M</text>'));
  assert.ok(svg.includes('>Other donors $6.3M</text>'));
  assert.ok(svg.includes('>Bernie Moreno · support</text>'));
  assert.ok(svg.includes('>Katherine Porter · oppose</text>'));
  assert.ok(svg.includes('>Other candidates</text>'));
  assert.ok(svg.includes('>$55.8M</text>'));
  assert.ok(svg.includes('>Kept by DAJ and PP</text>'));
  assert.equal(all(svg, /class="flow-party"[^>]*stroke="#83333e"/g).length, 2);   // Moreno and Justice (R)
  assert.equal(all(svg, /class="flow-party"[^>]*stroke="#509ecd"/g).length, 4);   // Slotkin, Porter, Gallego, Helmer (D)
  assert.ok(svg.includes('>RECEIVED FROM</text>') && svg.includes('>LANDED ON</text>'));
  assert.ok(svg.includes('fill="url(#flow-hatch)"'), 'not yet spent and kept are hatched');
});

test('no inline style, labels escaped, one tab stop, unique ids per chart', () => {
  const hostile = JSON.parse(JSON.stringify(FIXTURE));
  hostile.nodes.find(node => node.id === 'donor:ACME CORP').label = '<img src=x onerror=alert(1)>';
  const svg = chart.svgString(hostile, {palette: PALETTE, idPrefix: 'chartA'});
  assert.ok(!/ style=/.test(svg) && !svg.includes('<style'), 'CSP: no inline style');
  assert.ok(!svg.includes('<img'), 'labels are escaped');
  assert.ok(svg.includes('&lt;img src=x onerror=alert(1)&gt;'));
  assert.equal(all(svg, /tabindex="0"/g).length, 1);
  assert.ok(svg.includes('id="chartA-g-0"') && !svg.includes('id="flow-g-0"'));
});

test('the pooled-money tooltip names the route, the spender and the share', () => {
  const result = layout.layout(FAIRSHAKE);
  const context = {result, colours: layout.colours(result, PALETTE, '#a39b92')};
  context.outcomes = layout.outcomes(result, context.colours);
  const link = result.links.find(item => item.source === 'committee:C00836221' && item.target === 'candidate:S4OH00192:support');
  const text = chart.describe({link}, context, FAIRSHAKE);
  assert.equal(text.title, 'FAIRSHAKE → Defend American Jobs → Bernie Moreno (R-OH), support');
  assert.equal(text.lines[0], '$40,134,929.71 spent by Defend American Jobs');
  assert.equal(text.lines[1], '90.4% of its 2023–2024 receipts came from FAIRSHAKE · pooled, not traced dollars');
  assert.ok(text.lines[2].includes('% of Landed on') && text.lines[2].includes('filings'));
  const own = result.links.find(item => item.source === 'bucket:own-ads' && item.target === 'candidate:S4CA00522:oppose');
  const direct = chart.describe({link: own}, context, FAIRSHAKE);
  assert.equal(direct.title, 'FAIRSHAKE → Katherine Porter (D-CA), oppose');
  assert.ok(!direct.lines.some(line => line.includes('pooled')), "the root's own ads are not pooled by another committee");
  const node = result.nodes.find(item => item.id === 'balance:unspent:2');
  assert.ok(chart.describe({node}, context, FAIRSHAKE).lines.includes(
    'cash on hand $64,244,197.94 at the end of the window + bitcoin $23,000,000.00 still held'));
});

test('carryover (b): a carried-over committee\u2019s tooltip says where its gate came from, in the payload\u2019s words', () => {
  const body = JSON.parse(JSON.stringify(FIXTURE));
  const bridge = body.nodes.find(node => node.kind === 'committee' && !node.root && !node.stub);
  bridge.gate_source = 'carryover';
  bridge.carryover = {label: 'gate opened by 2023-2024 transfers', gate: '2025-01-01',
    opened_by: [{source: body.root.id, label: 'Root Fund', first_date: '2024-03-02', amount: 800000}]};
  const cash = body.nodes.find(node => node.stub === 'prior_cash');
  if (cash) cash.carryover = bridge.carryover.label;
  const context = {result: layout.layout(body, {width: 1200, height: 560}), format: {short: chart.short, full: chart.full}};
  const said = chart.describe({node: context.result.nodes.find(node => node.id === bridge.id)}, context, body).lines;
  assert.ok(said.includes('Counted from the start of the cycle: gate opened by 2023-2024 transfers'), said.join(' | '));
  assert.ok(said.some(line => line.startsWith('Opened by Root Fund $800K from 2024-03-02')), said.join(' | '));
  const before = chart.describe({node: layout.layout(FIXTURE, {width: 1200, height: 560}).nodes.find(node => node.id === bridge.id)},
    {result: layout.layout(FIXTURE, {width: 1200, height: 560}), format: {short: chart.short, full: chart.full}}, FIXTURE).lines;
  assert.ok(!before.some(line => /start of the cycle/.test(line)), 'a committee reached in the cycle says nothing of it');
});
