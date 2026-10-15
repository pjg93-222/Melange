'use strict';
/* Lane Z (2026-10-15): the arrangement a Flow view makes before it draws (small transfers folded, a
   group unfolded in place), the chain behind a pin, the zoom path, one read per query and the unnamed
   committee's FEC ID. None of it may change a dollar: every test below holds the column totals and runs
   the client conservation validator on what would be drawn. */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const layout = require('../flow-layout.js');
const chart = require('../flow-chart.js');

const CONTRACTS = path.resolve(__dirname, '..', '..', '..', 'audits', 'mentat_failings_20260915', 'contracts');
const contract = JSON.parse(fs.readFileSync(path.join(CONTRACTS, 'flow.json'), 'utf8'));
const FIXTURE = contract.examples.find(item => item.name.startsWith('a committee flow')).body;
const FAIRSHAKE = contract.examples.find(item => item.name.startsWith('FAIRSHAKE 2023-2024')).body;
const clone = value => JSON.parse(JSON.stringify(value));
const cents = value => Math.round(value * 100);

// The column totals, in cents, of what a payload draws.
const totals = payload => layout.layout(payload, {width: 1100, height: 520}).columns.map(column => cents(column.total));

// The synthetic committee flow with extra committees in the "Passed to" column: three at a few thousand
// dollars, two at nothing, and one big enough to stay named. ROOT FUND pays each one, out of what it
// would have kept (its balance still balances).
function withSmallTransfers() {
  const body = clone(FIXTURE);
  const root = 'committee:C90000001';
  const paid = {A: 1000, B: 2500, C: 4000, BIG: 60000};
  let total = 0;
  for (const [name, value] of Object.entries(paid)) {
    const id = `committee:C900001${name}`;
    body.nodes.push({id, stage: 2, kind: 'committee', label: `Small ${name}`, committee_id: id.slice(10), value_in: value, value_out: 0});
    body.links.push({source: root, target: id, value, kind: 'transfer', rows: 1, committee: 'C90000001'});
    total += value;
  }
  for (const name of ['ZERO1', 'ZERO2'])
    body.nodes.push({id: `committee:C90000200${name}`, stage: 2, kind: 'committee', label: `Nothing ${name}`, committee_id: `C90000200${name}`,
      value_in: 0, value_out: 0});
  const unspent = body.links.find(link => link.target === 'balance:unspent:2');
  unspent.value -= total;
  body.nodes.find(node => node.id === 'balance:unspent:2').value_in -= total;
  return body;
}

test('small transfers fold into one node per column, and not a dollar moves', () => {
  const body = withSmallTransfers();
  assert.deepEqual(layout.validate(body), [], 'the fixture itself conserves');
  const made = layout.arrange(body, {small: true});
  const small = made.payload.nodes.filter(node => node.bucket === 'small');
  assert.equal(small.length, 1, 'one small-transfers node for the column');
  assert.equal(small[0].stage, 2);
  assert.equal(small[0].member_count, 5, 'three small committees and the two at nothing');
  assert.equal(small[0].label, 'Small transfers (5)');
  assert.equal(small[0].value_in, 7500, 'its total is the members’ total');
  assert.ok(made.payload.nodes.some(node => node.id === 'committee:C900001BIG'), 'a committee above the floor stays named');
  assert.ok(!made.payload.nodes.some(node => /Nothing ZERO/.test(node.label)), 'no node at nothing is left drawn');
  assert.deepEqual(totals(made.payload), totals(body), 'every column keeps its total');
  assert.deepEqual(layout.validate(made.payload), [], 'and the conservation validator still passes');
  // The members are in the node, largest first, for the tooltip.
  assert.deepEqual(small[0].members.map(member => member.value), [4000, 2500, 1000, 0, 0]);
  const said = chart.describe({node: layout.layout(made.payload).nodes.find(node => node.id === small[0].id)},
    {result: layout.layout(made.payload), format: {short: chart.short, full: chart.full}}, made.payload).lines;
  assert.ok(said.includes('5 grouped:') && said.some(line => line.startsWith('Small C ')), said.join(' | '));
});

test('a small bucket unfolds into its top members and a smaller residual, with the same totals', () => {
  const body = withSmallTransfers();
  const made = layout.arrange(body, {small: true, open: {'small:2': 2}});
  const shown = made.payload.nodes.filter(node => node.group === 'small:2' && node.kind === 'committee');
  assert.deepEqual(shown.map(node => node.label).sort(), ['Small B', 'Small C']);
  const residual = made.payload.nodes.find(node => node.bucket === 'small');
  assert.equal(residual.member_count, 3);
  assert.deepEqual(made.groups.map(group => [group.id, group.residual]), [['small:2', true]]);
  assert.deepEqual(totals(made.payload), totals(body));
  assert.deepEqual(layout.validate(made.payload), []);
  // Asking for more than there is shows them all and leaves no bucket behind.
  const all = layout.arrange(body, {small: true, open: {'small:2': 50}});
  assert.ok(!all.payload.nodes.some(node => node.bucket === 'small'));
  assert.deepEqual(totals(all.payload), totals(body));
  assert.deepEqual(layout.validate(all.payload), []);
});

// The grouped answer a server gives at Top N, from the ungrouped one: group() on the same rule.
function grouped(full, top) {
  const made = layout.layout(full, {top, width: 1100, height: 520});
  return Object.assign({}, full, {nodes: made.nodes.map(node => Object.assign({}, node)), links: made.links.map(link => Object.assign({}, link))});
}

test('unfolding an Other keeps every column’s total and its links, from the top=0 answer', () => {
  const full = clone(FIXTURE);
  const answer = grouped(full, 3);
  const other = answer.nodes.find(node => node.id === 'other:0');
  assert.ok(other && other.member_count >= 2, 'the grouped answer has an Other to unfold');
  assert.deepEqual(layout.validate(layout.arrange(answer, {}).payload), []);
  for (const count of [1, 2, 9]) {
    const made = layout.arrange(answer, {open: {'other:0': count}, full});
    assert.deepEqual(made.refused, {}, `unfolded at ${count}`);
    assert.deepEqual(totals(made.payload), totals(answer));
    assert.deepEqual(layout.validate(made.payload), []);
    const doe = made.payload.nodes.find(node => node.id === 'donor:DOE JANE');
    if (doe) assert.equal(made.payload.links.find(link => link.source === doe.id).value, 500000, 'a member’s own link, not a share of the group’s');
  }
  // Nothing to unfold with until the full answer is asked for.
  assert.deepEqual(layout.arrange(answer, {open: {'other:0': 2}}).needs, ['other:0']);
});

test('negative control: members whose links do not add up to the group are refused, not drawn', () => {
  const full = clone(FIXTURE);
  const answer = grouped(full, 3);
  const wrong = clone(full);
  wrong.links.find(link => link.source === 'donor:DOE JANE').value += 1;       // one dollar the group does not have
  const made = layout.arrange(answer, {open: {'other:0': 2}, full: wrong});
  assert.ok(made.refused['other:0'], 'refused');
  assert.ok(!made.payload.nodes.some(node => node.group === 'other:0'), 'and the group stays folded');
  assert.deepEqual(totals(made.payload), totals(answer));
});

test('a real answer: the FAIRSHAKE example folds and validates, and its totals do not move', () => {
  const made = layout.arrange(FAIRSHAKE, {small: true});
  assert.deepEqual(layout.validate(made.payload), []);
  assert.deepEqual(totals(made.payload), totals(FAIRSHAKE));
});

test('an unnamed committee shows its FEC ID as the small line, and the tooltip carries it', () => {
  const body = clone(FIXTURE);
  const node = body.nodes.find(item => item.id === 'committee:C90000002');
  Object.assign(node, {label: 'Unnamed committee', name_as_filed: 'C90000002', unnamed: true});
  const result = layout.layout(body, {width: 1100, height: 520});
  const drawn = result.nodes.find(item => item.id === node.id);
  assert.ok(drawn.sublines.includes('C90000002'));
  assert.equal(drawn.subline, 'C90000002');
  const svg = chart.svgString(body, {width: 1100, height: 520});
  assert.ok(svg.includes('>Unnamed committee</text>') && svg.includes('>C90000002</text>'));
  const said = chart.describe({node: drawn}, {result, format: {short: chart.short, full: chart.full}}, body).lines;
  assert.ok(said.includes('As filed: C90000002'), said.join(' | '));      // the ID is on the drawing and in the tooltip
});

test('a pin’s chain shows each step’s own amount, and never crosses the root’s pool', () => {
  const result = layout.layout(FAIRSHAKE, {width: 1100, height: 520});
  const pool = result.nodes.find(node => node.root && !node.stub);
  const candidate = result.nodes.find(node => node.kind === 'candidate' && result.links.some(link => link.target === node.id));
  const hops = chart.chainOf(result, candidate.id);
  assert.equal(hops[0].node.id, pool.id, 'a candidate’s chain begins at the pool that paid it, not at a donor');
  assert.ok(hops.every(hop => hop.node.kind !== 'donor'), 'no donor is on a candidate’s chain');
  assert.equal(hops[hops.length - 1].node.id, candidate.id);
  hops.forEach((hop, at) => {
    if (!at) return assert.equal(hop.via, null);
    const same = result.links.filter(link => link.source === hops[at - 1].node.id && link.target === hop.node.id);
    assert.ok(same.some(link => link.id === hop.via.id), 'each step is one real link');
  });
  const donor = result.nodes.find(node => node.kind === 'donor' && !node.stub);
  const out = chart.chainOf(result, donor.id);
  assert.equal(out[out.length - 1].node.id, pool.id, 'a donor’s chain ends at the pool it paid');
});

test('the zoom path: a step is a level to return to; going back or jumping drops the levels after it', () => {
  const trail = chart.trail();
  trail.push({label: 'Banking'}); trail.push({label: 'ActBlue'}); trail.push({label: 'DCCC'});
  assert.deepEqual(trail.labels('NRSC'), ['Banking', 'ActBlue', 'DCCC', 'NRSC']);
  assert.equal(trail.back().label, 'DCCC');
  assert.equal(trail.jump(0).label, 'Banking');
  assert.equal(trail.depth(), 0);
});

test('one read per query: concurrent asks share it, a good answer is kept, a failure is not', async () => {
  let calls = 0;
  const fetcher = async url => { calls += 1; return {ok: !url.includes('bad'), status: url.includes('bad') ? 400 : 200, json: async () => ({url})}; };
  const [a, b] = await Promise.all([chart.read('/api/flow?x=1', fetcher), chart.read('/api/flow?x=1', fetcher)]);
  assert.equal(calls, 1);
  assert.equal(a, b);
  await chart.read('/api/flow?x=1', fetcher);
  assert.equal(calls, 1, 'kept');
  await chart.read('/api/flow?bad=1', fetcher);
  await chart.read('/api/flow?bad=1', fetcher);
  assert.equal(calls, 3, 'a refusal is asked again');
});

test('the gestures are in the tooltip, and an onward marker is drawn only for the views that follow it', () => {
  const result = layout.layout(FIXTURE, {width: 1100, height: 520});
  const context = {result, format: {short: chart.short, full: chart.full}};
  const bridge = result.nodes.find(node => node.id === 'committee:C90000002');
  const hints = {zoom: true, rows: true};
  assert.equal(chart.describe({node: bridge}, context, FIXTURE, hints).hint, 'Click to zoom in · Shift-click to pin');
  assert.equal(chart.describe({node: bridge}, context, FIXTURE).hint, '', 'no gestures promised where the view has none');
  const candidate = result.nodes.find(node => node.kind === 'candidate');
  assert.equal(chart.describe({node: candidate}, context, FIXTURE, hints).hint, 'Click to open in Rows · Shift-click to pin');
  const bucket = layout.layout(grouped(clone(FIXTURE), 3), {width: 1100, height: 520}).nodes.find(node => node.id === 'other:0');
  assert.equal(chart.describe({node: bucket}, context, FIXTURE, hints).hint, 'Click to expand · Shift-click to pin');
  const plain = chart.svgString(FIXTURE, {width: 1100, height: 520});
  const explore = chart.svgString(FIXTURE, {width: 1100, height: 520, explore: true});
  assert.ok(!plain.includes('flow-onward'), 'Chart Studio’s flow draws no marker');
  assert.ok(explore.includes('data-onward="committee:C90000002"') && explore.includes('→ 1 onward'));
});
