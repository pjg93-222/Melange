// The cycle view of Forecast giving (board F2): the models behind the chart, the candidate-mix cards, the lobbying card and the footer line, the
// historical-example message, and the request the scenario panel builds. Real responses of the console's own calculator go through the real
// giving-forecast.js in a vm sandbox against a DOM stub; the file on disk is not touched. The DOM itself is covered by test_giving_forecast_f2_browser.cjs.
//
// Two data paths, both pinned here (the model fix P1 is live, but a console that has not been updated yet still answers without it, so the view is right with and without it):
//   * tests/fixtures/giving_forecast_f2_live.json     the calculator as it was published before the model fix (no P1): intervals, remainders and remaining amounts are the
//                                                     unconditioned ones, a remainder can be negative and a share row can be budget_inconsistent;
//   * tests/fixtures/giving_forecast_f2_live_p1.json  the same requests answered with P1 applied: new fields condition the open cycle on the giving already
//                                                     observed. The legacy fields keep the unconditioned values, so the view has to read the new ones.
//
// What these tests pin (spec F2 section 3c and 6): one dollar basis on the chart, intervals drawn exactly as the model returned them (never clipped),
// no account ever added to another, a blank input staying unknown, every flag the model raises showing up as a chip (looked up by name), and the corrected
// historical-example message.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const SOURCE = path.join(__dirname, '..', 'app', 'giving-forecast.js');
const LEGACY = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'giving_forecast_f2_live.json'), 'utf8'));
const WITH_P1 = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'giving_forecast_f2_live_p1.json'), 'utf8'));
const LANDED = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'giving_forecast_f2_live_landed.json'), 'utf8'));
const FIXTURE = LEGACY;                 // the catalog (identical for both paths apart from the P1 `waivers` key) and the runs of the calculator without the fix
const RUN = LEGACY.runs, P1 = WITH_P1.runs;
const AMBER = 'warn', NEUTRAL = 'info';
const RANGE_TEXT = 'An input is outside the range this model was fitted on.';
const INTERVAL_TEXT = 'Mentat\'s own last change for this series was far outside this band; treat the band as too narrow.';
const BUDGET_TEXT = 'Budget inconsistent — revise scenario';

function el(tag) {
  const classes = new Set();
  return {tag, textContent: '', className: '', children: [], dataset: {}, style: {}, value: '', hidden: false, scope: '', disabled: false,
    classList: {toggle(name, on) { (on === undefined ? !classes.has(name) : on) ? classes.add(name) : classes.delete(name); }, contains: name => classes.has(name)},
    append(...c) { this.children.push(...c); }, replaceChildren(...c) { this.children = c; }, setAttribute() {}, addEventListener() {}, after() {}, dispatchEvent() {}, focus() {}, firstChild: {}};
}

function load() {
  const els = {};
  const create = tag => { const e = el(tag); let id = ''; Object.defineProperty(e, 'id', {get: () => id, set: v => { id = v; els[v] = e; }}); return e; };
  const document = {getElementById: id => els[id] || (els[id] = el('div')), createElement: create};
  let src = fs.readFileSync(SOURCE, 'utf8');
  assert.match(src, /\}\)\(\);\s*$/, 'unexpected file ending');
  src = src.replace(/\}\)\(\);\s*$/, `globalThis.__t={niceScale,axisLabel,chartModel,mixModel,lobbyModel,footerFacts,referenceRequest,getRequest,buildInputs,historicalExample,industry,anchorExample,
    refreshControls,parseNumber,formatNumber,exampleText,exampleParts,exampleTip,conditioning,refreshExample,waiverChips,waiverEntries,conditionedTables,givenOf,allocationOf,hasFlag,generalName,getControls:()=>controls,getPills:()=>pills,clearSaved,
    setCatalog:c=>{catalog=c;},setRuns:(r,b)=>{result=r;refRun=b;}};\n})();\n`);
  const ctx = vm.createContext({document, Intl, Number, Math, String, console, URL: {}, Blob: function () {}, setTimeout, fetch: () => {}, AbortController, Object, JSON, Array, Date, Map, Set, Event: function Event(type, init) { this.type = type; Object.assign(this, init); }});
  vm.runInContext(src, ctx, {filename: SOURCE});
  return {t: ctx.__t, els};
}
const clone = value => JSON.parse(JSON.stringify(value));
const plain = clone;    // a value built inside the vm has the sandbox's Object and Array: compare it as plain data
function session({sector = 'commercial_banks', outlook = true, waivers = undefined, source = FIXTURE} = {}) {
  const s = load();
  const catalog = clone(source.catalog);
  if (!outlook) delete catalog.saved_outlook;
  if (waivers) catalog.waivers = clone(waivers);
  s.els['gf-industry'] = Object.assign(el('select'), {value: sector});
  s.els['gf-date'] = Object.assign(el('input'), {value: source === FIXTURE ? '2026-09-30' : source.catalog.as_of});
  s.t.setCatalog(catalog);
  return s;
}
const measure = (run, horizon, id) => run.horizons[horizon].pac.measures.find(m => m.id === id);
const basis = (run, horizon, chamber, id) => run.horizons[horizon].shares[chamber].bases.find(b => b.id === id);
const texts = lines => lines.map(line => line.head || (line.row ? line.row.join(': ') : line.note)).join('\n');
const row = (lines, label) => (lines.find(line => line.row && line.row[0] === label) || {}).row;
const chipTexts = chips => plain(chips.map(c => c.text));
// The three owner waivers of the House share the registry (mentat/forecast/refit/registry/gate_waivers.json) lists with show_warning true, and the lobbying one with false.
const REGISTRY_WAIVERS = [
  {gate: 'G6', cell: 'lobby / commercial_banks', term: 'lobby', industry: 'commercial_banks', reason: 'owner ruling: keep log refit', owner: 'Paul Goff', date: '2026-09-30', show_warning: false},
  {gate: 'G6', cell: 'control_House / commercial_banks', term: 'control_House', industry: 'commercial_banks', reason: 'Owner explicitly authorized the three House-share LOEO degradations measured by pod-final-20260930: "Waive these three cells and publish".', owner: 'Paul Goff', date: '2026-09-30', show_warning: true, new_MAE: 1.9, published_MAE: 1.6},
  {gate: 'G6', cell: 'control_House / credit_unions', term: 'control_House', industry: 'credit_unions', reason: 'Owner explicitly authorized the three House-share LOEO degradations measured by pod-final-20260930: "Waive these three cells and publish".', owner: 'Paul Goff', date: '2026-09-30', show_warning: true},
  {gate: 'G6', cell: 'control_House / auto_light_duty_manufacturing', term: 'control_House', industry: 'auto_light_duty_manufacturing', reason: 'Owner explicitly authorized the three House-share LOEO degradations measured by pod-final-20260930: "Waive these three cells and publish".', owner: 'Paul Goff', date: '2026-09-30', show_warning: true}];

test('the fixtures are the two calculators\' own answers to the same requests', () => {
  assert.equal(P1.banks.model_version, RUN.banks.model_version);
  assert.deepEqual(Object.keys(P1).sort(), Object.keys(RUN).sort());
  assert.deepEqual(plain(WITH_P1.catalog_waivers), [], 'the recording of the fix alone carries no waivers (they come with the refit registry)');
  // the model fix adds fields; it changes none of the legacy ones
  assert.equal(measure(P1.banks, 0, 'pac_to_candidates').cycle_prediction_low, measure(RUN.banks, 0, 'pac_to_candidates').cycle_prediction_low);
  assert.equal(measure(RUN.banks, 0, 'pac_to_candidates').cycle_given_observed_median, undefined, 'the calculator without the fix has no conditioned fields');
  assert.ok(measure(P1.banks, 0, 'pac_to_candidates').cycle_given_observed_median > 0, 'the one with the fix does');
});

test('the axis is a nice scale with at most eleven intervals, and its labels are compact dollars', () => {
  const {t} = session();
  assert.deepEqual(plain(t.niceScale(52197936.48)), {step: 5e6, top: 55e6, ticks: [0, 5e6, 10e6, 15e6, 20e6, 25e6, 30e6, 35e6, 40e6, 45e6, 50e6, 55e6]});   // the board's $0-$55M in $5M steps
  assert.equal(t.niceScale(11381408.4).step, 2e6);
  assert.equal(t.niceScale(11381408.4).top, 12e6);
  assert.equal(t.niceScale(811090).step, 1e5);
  assert.equal(t.niceScale(0).top, 1);
  for (const max of [1234, 0.9e6, 3.3e6, 27.2e6, 52.2e6, 99.99e6, 123e6]) assert.ok(t.niceScale(max).ticks.length <= 12, 'at most eleven intervals for ' + max);
  assert.deepEqual([0, 2.5e6, 55e6, 5e5, 1.2e6].map(v => t.axisLabel(v)), ['$0', '$2.5M', '$55M', '$500K', '$1.2M']);
});

test('one dollar basis: the Mentat level is the 2025-dollar anchor; the nominal amount lives in the tooltip', () => {
  for (const [name, runs] of [['without the model fix', RUN], ['with the model fix P1', P1]]) {
    const {t} = session();
    const general = measure(runs.banks, 0, 'general_giving');
    const model = t.chartModel(runs.banks, null, 'general');
    const anchor = model.columns[0];
    assert.equal(anchor.value, general.anchor_cycle_real_2025, name);
    assert.notEqual(anchor.value, general.anchor_cycle_nominal, name);
    assert.equal(model.basis, '2025 dollars');
    assert.deepEqual(plain(row(anchor.tip, 'In 2025 USD (this chart)')), ['In 2025 USD (this chart)', '$27.18M']);
    assert.deepEqual(plain(row(anchor.tip, 'Nominal')), ['Nominal', '$26.11M']);
    assert.match(anchor.aria, /\$27\.18M in 2025 dollars, \$26\.11M nominal/);
    // every dollar the chart scales to is a 2025-dollar amount from the response: the anchor, observed at face value, the totals and the intervals
    const cur = model.columns[1], next = model.columns[2];
    assert.equal(model.axisMax, Math.max(anchor.value, cur.observed, cur.total, cur.high, next.total, next.high));
    assert.equal(next.total, measure(runs.banks, 1, 'general_giving').projected_cycle_real_2025);
  }
});

test('without the model fix: the open cycle is observed at face value plus the model\'s own remainder, with the date the remainder starts', () => {
  const {t} = session();
  const general = measure(RUN.banks, 0, 'general_giving');
  const model = t.chartModel(RUN.banks, null, 'general'), cur = model.columns[1];
  assert.equal(cur.state, 'stacked');
  assert.equal(cur.conditioned, false);
  assert.equal(cur.observed, general.observed.amount_real_2025);
  assert.equal(cur.remainder, general.projected_remaining);
  assert.equal(cur.total, general.projected_cycle_real_2025);
  assert.ok(Math.abs(cur.observed + cur.remainder - cur.total) < 1e-6);
  assert.equal(cur.through, '2026-06-30');
  assert.deepEqual(plain(row(cur.observedTip, 'Basis')), ['Basis', 'Face value: no 2026 CPI yet']);
  assert.match(texts(cur.observedTip), /remainder starts the next day, 2026-07-01/);
  assert.match(texts(cur.remainderTip), /Full cycle: \$27\.18M = \$11\.57M observed \+ \$15\.61M remainder/);
  assert.ok(row(cur.remainderTip, 'Remainder prediction interval'));
});

test('without the model fix: an interval is drawn exactly as returned and never clipped; one that starts below observed giving is flagged amber', () => {
  const {t} = session();
  const general = measure(RUN.banks, 0, 'general_giving'), pac = measure(RUN.banks, 0, 'pac_to_candidates');
  const generalModel = t.chartModel(RUN.banks, null, 'general'), pacModel = t.chartModel(RUN.banks, null, 'pac');
  assert.equal(generalModel.columns[1].low, general.cycle_prediction_low);
  assert.equal(generalModel.columns[1].high, general.cycle_prediction_high);
  assert.equal(generalModel.columns[2].low, measure(RUN.banks, 1, 'general_giving').cycle_prediction_low);
  assert.equal(generalModel.columns[2].high, measure(RUN.banks, 1, 'general_giving').cycle_prediction_high);
  assert.deepEqual(plain(generalModel.flags), [], 'general giving: the interval stays above what is observed, so no flag');
  // roster PACs: the returned full-cycle interval starts under the $4.67M already observed
  assert.ok(pac.cycle_prediction_low < pac.observed.amount_real_2025);
  assert.equal(pacModel.columns[1].low, pac.cycle_prediction_low, 'not raised to the observed amount');
  assert.equal(pacModel.columns[1].high, pac.cycle_prediction_high);
  assert.equal(pacModel.columns[1].remainderLow, pac.remaining_prediction_low);
  assert.ok(pacModel.columns[1].remainderLow < 0, 'the negative remainder low end is kept');
  const flag = pacModel.flags.find(f => f.text === 'Prediction interval starts below giving already observed');
  assert.equal(flag.kind, AMBER);
  assert.match(texts(flag.tip), /drawn exactly as returned, not clipped/);
  assert.match(texts(flag.tip), new RegExp(BUDGET_TEXT));
  assert.match(texts(pacModel.columns[1].remainderTip), /reaches below zero; it is shown as the model returned it/);
});

test('model fix P1: the whisker is the conditioned full-cycle interval, the remainder segment the conditioned remainder, and nothing is clipped', () => {
  const {t} = session();
  const pac = measure(P1.banks, 0, 'pac_to_candidates'), general = measure(P1.banks, 0, 'general_giving');
  const pacModel = t.chartModel(P1.banks, null, 'pac'), generalModel = t.chartModel(P1.banks, null, 'general');
  for (const [model, m] of [[pacModel, pac], [generalModel, general]]) {
    const cur = model.columns[1];
    assert.equal(model.conditioned, true);
    assert.equal(cur.conditioned, true);
    assert.equal(cur.state, 'stacked');
    assert.equal(cur.low, m.cycle_given_observed_low, 'the whisker starts at the conditioned low end, exactly');
    assert.equal(cur.high, m.cycle_given_observed_high);
    assert.equal(cur.total, m.cycle_given_observed_median);
    assert.equal(cur.remainder, m.remaining_given_observed_median, 'the remainder segment is the conditioned remainder');
    assert.equal(cur.remainderLow, m.remaining_given_observed_low);
    assert.equal(cur.remainderHigh, m.remaining_given_observed_high);
    assert.ok(Math.abs(cur.observed + cur.remainder - cur.total) < 1e-6, 'observed + remainder is the drawn total');
    assert.ok(cur.low >= cur.observed - 1e-6, 'the conditioned interval cannot start below what is observed');
    assert.ok(cur.remainder > 0 && cur.remainderLow >= 0, 'no negative remainder');
  }
  // the legacy fields of the same response still hold the unconditioned values (negative low end): the view must not draw them
  assert.ok(pac.remaining_prediction_low < 0);
  assert.notEqual(pacModel.columns[1].low, pac.cycle_prediction_low);
  assert.deepEqual(chipTexts(pacModel.flags.filter(f => f.kind === AMBER)), [], 'nothing amber: the drawn figures are consistent with the giving observed');
  assert.match(texts(pacModel.columns[1].intervalTip), /conditioned on the giving already observed/);
  assert.ok(row(pacModel.columns[1].intervalTip, 'Unconditioned model'));
  assert.ok(Math.abs(Number(row(pacModel.columns[1].intervalTip, 'Unconditioned chance below observed')[1].replace('%', '')) - 12.15) < 0.01, 'the 12.1% of the unconditioned mass below observed is said');
  // the next cycle has nothing observed: it is the model's own interval in both paths
  assert.equal(pacModel.columns[2].low, measure(P1.banks, 1, 'pac_to_candidates').cycle_prediction_low);
});

test('with and without P1 the same inputs give the same observed amount, the same anchor and the same next-cycle column', () => {
  const a = session().t.chartModel(RUN.banks, null, 'pac'), b = session().t.chartModel(P1.banks, null, 'pac');
  assert.equal(a.columns[0].value, b.columns[0].value);
  assert.equal(a.columns[1].observed, b.columns[1].observed);
  assert.deepEqual(plain(a.columns[2]).total, plain(b.columns[2]).total);
  assert.equal(a.columns[1].conditioned, false);
  assert.equal(b.columns[1].conditioned, true);
});

test('model fix P1: giving observed above the unconditioned projection is drawn from the conditioned figures and said in a neutral chip', () => {
  const {t} = session();
  const run = clone(P1.banks), m = measure(run, 0, 'pac_to_candidates');
  m.projected_cycle_real_2025 = m.observed.amount_real_2025 * 0.8;                // the synthetic case the flag exists for: projection below observed
  m.flags.push('observed_exceeds_unconditional_projection');
  const model = t.chartModel(run, null, 'pac');
  assert.equal(model.columns[1].state, 'stacked');
  assert.equal(model.columns[1].total, m.cycle_given_observed_median);
  const flag = model.flags.find(f => f.text === 'Observed giving exceeds the unconditioned projection');
  assert.equal(flag.kind, NEUTRAL);
  assert.match(texts(flag.tip), /conditioned on what is observed/);
});

test('zero input change is said, not drawn: the coefficient interval is zero-width by construction', () => {
  const {t} = session();
  const cur = t.chartModel(RUN.banks, null, 'general').columns[1];
  assert.equal(row(cur.intervalTip, 'Coefficient interval')[1], '$27.18M to $27.18M (no input change)');
  const moved = t.chartModel(RUN.banks_growth_down, null, 'general').columns[1];
  const [, text] = row(moved.intervalTip, 'Coefficient interval');
  assert.doesNotMatch(text, /no input change/);
});

test('D4(b): the name of the general-giving account, and the note about the receipts left out, come from the own label of the calculator - nothing claims an exclusion the model does not state', () => {
  const NEW_LABEL = 'Mentat general giving (all channels), excluding receipts Mentat marks non-giving (FEC interest, refunds, insurance claims, loans)';
  const {t} = session();
  // before the change: the old label, no exclusion claimed anywhere
  const old = t.chartModel(RUN.banks, null, 'general');
  assert.equal(old.accountLabel, 'Mentat general giving (all channels)');
  assert.doesNotMatch(texts(old.columns[0].tip), /non-giving/);
  assert.equal(t.generalName(RUN.banks), 'Mentat general giving (all channels)');
  // after it: the new label is the account name, the anchor tooltip says what is left out, and the PAC account has no such note
  for (const runs of [RUN, P1]) {
    const run = clone(runs.banks);
    for (const h of run.horizons) for (const m of h.pac.measures) if (m.id === 'general_giving') m.label = NEW_LABEL;
    const model = t.chartModel(run, null, 'general');
    assert.equal(model.accountLabel, NEW_LABEL);
    assert.match(NEW_LABEL, /^Mentat general giving \(all channels\)/, 'the prefix the existing tests match is kept');
    assert.match(texts(model.columns[0].tip), /Receipts the accounting engine marks non-giving \(interest, refunds, insurance claims, loans\) are left out; the amounts are in Sources and notes\./);
    assert.doesNotMatch(texts(t.chartModel(run, null, 'pac').columns[0].tip), /non-giving/, 'the roster PAC account has no such exclusion');
    assert.equal(t.generalName(run), NEW_LABEL);
  }
  assert.equal(t.generalName(null), 'Mentat general giving');
});

test('PAC giving and general giving are separate accounts: nothing is stacked, added or blended (either data path)', () => {
  for (const runs of [RUN, P1]) {
    const {t} = session();
    const general = t.chartModel(runs.banks, null, 'general'), pac = t.chartModel(runs.banks, null, 'pac');
    assert.notEqual(general.columns[0].value, pac.columns[0].value);
    assert.equal(pac.columns[0].value, measure(runs.banks, 0, 'pac_to_candidates').anchor_cycle_real_2025);
    const sums = [general.columns[0].value + pac.columns[0].value, general.columns[1].total + pac.columns[1].total, general.columns[2].total + pac.columns[2].total];
    for (const model of [general, pac]) {
      const values = [model.columns[0].value, model.columns[1].observed, model.columns[1].total, model.columns[1].high, model.columns[2].total, model.columns[2].high];
      for (const sum of sums) assert.ok(values.every(v => Math.abs(v - sum) > 1), 'a column equals the sum of the two accounts');
    }
    assert.ok(pac.axisMax < general.axisMax / 3, 'each account has its own scale');
    assert.match(pac.accountLabel, /Roster companies' PACs/);
    assert.equal(general.accountLabel, measure(runs.banks, 0, 'general_giving').label, 'the name of the account is the one the model gives it');
  }
});

test('no pooled figure of the two candidate-share bases is ever read or drawn: no model, row, tip or chip mentions one', () => {
  for (const runs of [RUN, P1]) {
    const {t} = session();
    const everything = JSON.stringify([t.chartModel(runs.banks, null, 'pac'), t.chartModel(runs.banks, null, 'general'), t.mixModel(runs.banks, null, 'House'), t.mixModel(runs.banks, null, 'Senate'), t.lobbyModel(runs.banks_lobby, 2026, 2028)]);
    assert.doesNotMatch(everything, /combined|pooled reference/i);
    const house = t.mixModel(runs.banks, null, 'House');
    assert.equal(house.rows.length, 2);
    assert.deepEqual(plain(house.rows.map(r => r.id)), ['employee_candidate', 'pac_candidate']);
  }
});

test('before a calculation the chart holds real data only: the Mentat level and the observed segment', () => {
  const {t} = session();
  const model = t.chartModel(null, RUN.banks, 'general');
  const [anchor, cur, next] = model.columns;
  assert.equal(anchor.value, measure(RUN.banks, 0, 'general_giving').anchor_cycle_real_2025);
  assert.equal(cur.state, 'pending');
  assert.equal(cur.observed, measure(RUN.banks, 0, 'general_giving').observed.amount_real_2025);
  for (const column of [cur, next]) { assert.equal(column.total, undefined); assert.equal(column.low, undefined); assert.equal(column.high, undefined); }
  assert.equal(next.state, 'pending');
  assert.equal(model.axisMax, anchor.value, 'the scale follows the data on the chart, not a projection that is not there');
  assert.match(cur.aria, /observed through 2026-06-30; Set a scenario and calculate/);
});

test('a missing input shows a dash with the reason in its tooltip; the observed segment stays', () => {
  const {t} = session();
  const model = t.chartModel(RUN.banks_blank, RUN.banks, 'general');
  const [, cur, next] = model.columns;
  assert.equal(cur.state, 'pending'); assert.equal(next.state, 'pending');
  assert.equal(cur.reason, 'Enter expected two-year cycle revenue growth.');
  assert.match(texts(cur.pendingTip), /Enter expected two-year cycle revenue growth\./);
  assert.equal(cur.observed, measure(RUN.banks, 0, 'general_giving').observed.amount_real_2025);
  assert.match(next.aria, /Enter expected two-year cycle revenue growth\./);
});

test('an account the industry does not have is said, not drawn as a zero', () => {
  const {t} = session({sector: 'property_casualty'});
  const pac = t.chartModel(RUN.property_casualty, null, 'pac');
  assert.equal(pac.empty, true);
  assert.equal(pac.message, 'No roster PAC committees are resolved for this industry');
  assert.deepEqual(plain(pac.flags.map(f => f.text)), ['No roster PAC committees are resolved for this industry']);
  const general = t.chartModel(RUN.property_casualty, null, 'general');
  assert.equal(general.empty, false);
  assert.equal(general.columns[0].value, measure(RUN.property_casualty, 0, 'general_giving').anchor_cycle_real_2025);
});

test('credit unions: the single-PAC thin base is a neutral chip and the June cut-back too; the model\'s own flag text is used', () => {
  for (const runs of [RUN, P1]) {
    const {t} = session({sector: 'credit_unions'});
    const pac = t.chartModel(runs.credit_unions, null, 'pac');
    const thin = pac.flags.find(f => /^One PAC \(SchoolsFirst Federal Credit Union\)/.test(f.text));
    assert.equal(thin.kind, NEUTRAL);
    assert.equal(thin.text, measure(runs.credit_unions, 0, 'pac_to_candidates').flag_text);
    const cut = pac.flags.find(f => f.text === 'Coverage cut back to 2026-05-31');
    assert.equal(cut.kind, NEUTRAL);
    assert.match(texts(cut.tip), /June incomplete/);
    assert.equal(pac.columns[1].through, '2026-05-31');
  }
});

test('flags are looked up by NAME, never by position: the model fix inserts a new first flag on the credit-union PAC', () => {
  const {t} = session({sector: 'credit_unions'});
  const baseline = measure(P1.credit_unions, 0, 'pac_to_candidates').flags;
  assert.deepEqual(plain(baseline), ['interval_not_supported_by_own_history', 'single_pac_thin_base']);
  for (const order of [baseline, [...baseline].reverse(), ['some_future_flag', ...baseline], [...baseline, 'another_future_flag'], ['some_future_flag', ...[...baseline].reverse()]]) {
    const run = clone(P1.credit_unions);
    for (const h of run.horizons) h.pac.measures.find(m => m.id === 'pac_to_candidates').flags = [...order];
    const flags = t.chartModel(run, null, 'pac').flags;
    assert.equal(flags.filter(f => f.kind === AMBER && f.text === INTERVAL_TEXT).length, 1, 'amber chip for ' + order.join(','));
    assert.equal(flags.filter(f => /^One PAC \(/.test(f.text)).length, 1, 'thin-base chip for ' + order.join(','));
  }
  const without = clone(P1.credit_unions);
  for (const h of without.horizons) h.pac.measures.find(m => m.id === 'pac_to_candidates').flags = ['some_future_flag'];
  assert.deepEqual(chipTexts(t.chartModel(without, null, 'pac').flags).filter(text => text === INTERVAL_TEXT || /^One PAC/.test(text)), [], 'a flag that is not there raises no chip');
  const model = t.hasFlag({flags: ['a', 'b']}, 'b');
  assert.equal(model, true);
  assert.equal(t.hasFlag({flags: ['a', 'b']}, 'c'), false);
  assert.equal(t.hasFlag({}, 'c'), false);
});

test('an interval Mentat\'s own history contradicts is an amber chip with the owner\'s wording, for the account it concerns', () => {
  const {t} = session({sector: 'credit_unions'});
  for (const account of ['pac', 'general']) {
    const model = t.chartModel(P1.credit_unions, null, account);
    const flag = model.flags.find(f => f.kind === AMBER);
    assert.equal(flag.text, INTERVAL_TEXT, account);
    assert.match(texts(flag.tip), /standard deviations of the step the band is built on/);
    assert.match(texts(flag.tip), /Own last step, Mentat 2021–2022 to 2023–2024/);
  }
  const banks = session().t;
  assert.deepEqual(chipTexts(banks.chartModel(P1.banks, null, 'pac').flags).filter(text => text === INTERVAL_TEXT), [], 'banks is not flagged');
  assert.deepEqual(chipTexts(banks.chartModel(P1.banks, null, 'general').flags).filter(text => text === INTERVAL_TEXT), []);
  // a calculator without the fix never raises it: nothing to show
  assert.deepEqual(chipTexts(t.chartModel(RUN.credit_unions, null, 'pac').flags).filter(text => text === INTERVAL_TEXT), []);
});

test('the scope caveats of an industry are one neutral chip on the chart (both accounts), listing every caveat in its tooltip', () => {
  const {t} = session({sector: 'property_casualty'});
  const caveats = FIXTURE.catalog.industries.find(i => i.id === 'property_casualty').caveats;
  assert.equal(caveats.length, 2);
  for (const run of [RUN, P1]) {
    const model = t.chartModel(run.property_casualty, null, 'general');
    const chip = model.flags.find(f => f.text === caveats[0]);
    assert.equal(chip.kind, NEUTRAL);
    assert.match(texts(chip.tip), /F09 = all insurance/);
    assert.match(texts(chip.tip), /IBISWorld's current-year estimate/);
  }
  assert.deepEqual(chipTexts(session().t.chartModel(RUN.banks, null, 'general').flags).filter(text => /F09/.test(text)), [], 'banks has none');
});

test('candidate mix, without the model fix: the bar is the projected FULL-cycle Republican share, never the share of what remains', () => {
  const {t} = session();
  const house = t.mixModel(RUN.banks, null, 'House');
  const bases = RUN.banks.horizons[0].shares.House.bases;
  assert.deepEqual(plain(house.rows.map(r => r.label)), ['Employees', 'Roster PACs']);
  assert.equal(house.rows[0].share, bases[0].projected_cycle_R_share);
  assert.equal(house.rows[0].conditioned, false);
  assert.notEqual(house.rows[0].share, bases[0].projected_remaining_R_share, 'the remaining share (42.16%) is a different denominator');
  assert.equal(house.rows[1].share, bases[1].projected_cycle_R_share);
  assert.deepEqual(plain(row(house.rows[0].tip, 'Share of the remaining giving')), ['Share of the remaining giving', '42.16% (from 2026-07-01)']);
  assert.equal(house.rows[0].next, RUN.banks.horizons[1].shares.House.bases[0].projected_cycle_R_share, 'the teal tick is the next cycle\'s full-cycle share');
  assert.equal(house.caption, '2023–2024: 34.35% and 54.36%');
  assert.deepEqual(plain(house.rows.map(r => r.id)), ['employee_candidate', 'pac_candidate'], 'two bases, never a pooled third');
});

test('candidate mix, without the model fix: budget_inconsistent outlines the affected bar and raises one amber chip, no clipping', () => {
  const {t} = session();
  const senate = t.mixModel(RUN.banks, null, 'Senate');
  assert.equal(senate.rows[0].flagged, false);
  assert.equal(senate.rows[1].flagged, true);
  assert.equal(senate.rows[1].share, RUN.banks.horizons[0].shares.Senate.bases[1].projected_cycle_R_share, 'the bar still shows the full-cycle share');
  const amber = senate.chips.filter(c => c.kind === AMBER);
  assert.equal(amber.length, 1);
  assert.equal(amber[0].text, BUDGET_TEXT);
  assert.match(texts(amber[0].tip), /budget_inconsistent: The projected total and share are incompatible/);
  assert.match(texts(amber[0].tip), /R -\$135\.67K · D \$32\.16K/);
  assert.equal(senate.chips[0].kind, AMBER, 'amber first');
  assert.equal(senate.conditioned, false);
});

test('candidate mix, model fix P1: the bar is the implied full-cycle share (observed + the projected share on the money still to come); no amber', () => {
  const {t} = session();
  const house = t.mixModel(P1.banks, null, 'House'), senate = t.mixModel(P1.banks, null, 'Senate');
  for (const [model, chamber] of [[house, 'House'], [senate, 'Senate']]) {
    assert.equal(model.conditioned, true);
    model.rows.forEach((r, i) => {
      const b = P1.banks.horizons[0].shares[chamber].bases[i], a = b.remaining_allocation;
      assert.equal(r.conditioned, true);
      assert.equal(r.share, a.implied_cycle_R_share, 'the bar is the P1 implied share');
      assert.notEqual(r.share, b.projected_cycle_R_share);
      assert.equal(r.projectedShare, b.projected_cycle_R_share);
      assert.equal(r.low, a.implied_cycle_R_share_prediction_low);
      assert.equal(r.high, a.implied_cycle_R_share_prediction_high);
      assert.equal(r.flagged, false, 'no amber outline: the remaining amounts are not negative');
      assert.ok(a.remaining_R_real_2025 >= 0 && a.remaining_D_real_2025 >= 0);
      // the share is exactly what the amounts imply
      const seen = b.observed;
      assert.ok(Math.abs((seen.R_real_2025 + a.remaining_R_real_2025) / (seen.R_real_2025 + seen.D_real_2025 + a.remaining_total_real_2025) - r.share) < 1e-9);
    });
    assert.deepEqual(chipTexts(model.chips.filter(c => c.kind === AMBER)), []);
  }
  // the Senate roster PACs were budget_inconsistent before conditioning: neutral chip and a tooltip note instead of the amber state
  assert.equal(P1.banks.horizons[0].shares.Senate.bases[1].remainder_status, 'budget_inconsistent', 'the legacy field still says so');
  assert.deepEqual(chipTexts(senate.chips), [RANGE_TEXT], 'no chip of its own: the bar tooltip and the notes say what was conditioned');
  assert.match(texts(senate.rows[1].tip), /Before conditioning, the model's projected two-party total \(\$886\.99K\) was below the giving already observed/);
  assert.match(texts(senate.rows[1].tip), /Remaining from 2026-07-01 \(median\): R \$150\.68K · D \$62\.88K of \$213\.56K/);
  assert.match(texts(senate.rows[1].tip), /Projected share, applied to the remaining giving: 70\.56%/);
  // the teal tick (next cycle) and the caption are the same in both paths
  assert.equal(house.rows[0].next, RUN.banks.horizons[1].shares.House.bases[0].projected_cycle_R_share);
  assert.equal(house.caption, '2023–2024: 34.35% and 54.36%');
});

test('out-of-range input: a neutral chip with the model\'s own sentence; the model fix names the input, how far and which input moved the share', () => {
  const {t} = session();
  for (const [name, runs] of [['published', RUN], ['P1', P1]]) {
    const house = t.mixModel(runs.banks, null, 'House');
    const chip = house.chips.find(c => c.text === RANGE_TEXT);
    assert.equal(chip.kind, NEUTRAL, name);
    assert.match(texts(chip.tip), new RegExp(RANGE_TEXT.replace(/\./g, '\\.')));
  }
  const p1 = t.mixModel(P1.banks, null, 'House').chips.find(c => c.text === RANGE_TEXT).tip;
  assert.match(texts(p1), /prior-cycle growth: 48\.89% \(fitted 2012–2022: -9\.87% to 14\.1%\)/);
  assert.match(texts(p1), /Model change by input, before conditioning on the giving already observed: .*presidential or midterm cycle -1\.88 pp/);
  assert.match(texts(p1), /Shares the model was fitted on: 42\.85% to 72\.81%/);
  // a calculator without the fix knows only yes or no
  assert.doesNotMatch(texts(t.mixModel(RUN.banks, null, 'House').chips.find(c => c.text === RANGE_TEXT).tip), /fitted 2012/);
});

test('candidate mix: thin bases and out-of-range inputs are neutral; a share outside 0-100% is not drawn and not clipped', () => {
  const {t} = session({sector: 'credit_unions'});
  const house = t.mixModel(RUN.credit_unions, null, 'House');
  assert.deepEqual(plain(house.chips.filter(c => c.kind === NEUTRAL).map(c => c.text).sort()), ['An input is outside the range this model was fitted on.', 'Thin base: Employees and Roster PACs'], 'one chip per kind of flag; the tooltip names each base');
  assert.equal(house.chips.filter(c => c.kind === AMBER).length, 1, 'the House employee basis is budget_inconsistent');
  const senate = t.mixModel(RUN.credit_unions_growth_down, null, 'Senate');
  const pacRow = senate.rows[1];
  assert.equal(RUN.credit_unions_growth_down.horizons[1].shares.Senate.bases[1].status, 'outside_share_range');
  assert.equal(pacRow.next, null, 'no tick is drawn for a share the model put outside 0-100%');
  assert.ok(pacRow.share != null, 'the current-cycle bar is still real');
  // with P1 the same House card has no amber state: the budget_inconsistent row is conditioned
  const withFix = session({sector: 'credit_unions'}).t.mixModel(P1.credit_unions, null, 'House');
  assert.equal(withFix.chips.filter(c => c.kind === AMBER).length, 0);
  assert.equal(withFix.rows.filter(r => r.flagged).length, 0);
});

test('candidate mix: a blank scenario draws no bar and says which input is missing; the anchor shares still caption the card', () => {
  const {t} = session();
  const house = t.mixModel(RUN.banks_blank, RUN.banks, 'House');
  assert.deepEqual(plain(house.rows.map(r => r.state)), ['missing', 'missing']);
  assert.equal(house.rows[0].reason, 'Enter House current-control assumption, House control score.');
  assert.match(texts(house.rows[0].tip), /Enter House current-control assumption/);
  assert.equal(house.caption, '2023–2024: 34.35% and 54.36%');
  const before = t.mixModel(null, RUN.banks, 'House');
  assert.deepEqual(plain(before.rows.map(r => r.state)), ['pending', 'pending']);
  assert.equal(before.caption, '2023–2024: 34.35% and 54.36%');
});

test('candidate mix: an industry with one basis captions that basis by name and shows a dash for the other', () => {
  const {t} = session({sector: 'property_casualty'});
  const house = t.mixModel(RUN.property_casualty, null, 'House');
  assert.deepEqual(plain(house.rows.map(r => r.state)), ['ready', 'missing']);
  assert.match(house.rows[1].reason, /No roster PAC committees are resolved/);
  assert.match(house.caption, /^2023–2024: 43\.37% \(employees\)$/);
});

test('owner waivers: a neutral chip on the card of the term the waiver concerns, for the selected industry only', () => {
  const {t} = session({waivers: REGISTRY_WAIVERS});
  for (const [name, runs] of [['published', RUN], ['P1', P1]]) {
    const house = t.mixModel(runs.banks, null, 'House');
    const waiver = house.chips.filter(c => /^Gate waived by owner/.test(c.text));
    assert.deepEqual(plain(waiver.map(c => c.text)), ['Gate waived by owner: House share'], name);
    assert.equal(waiver[0].kind, NEUTRAL);
    assert.match(texts(waiver[0].tip), /Cell: control_House \/ commercial_banks/);
    assert.match(texts(waiver[0].tip), /Gate: G6/);
    assert.match(texts(waiver[0].tip), /Measured: refit 1\.900 · earlier published calculator 1\.600/);
    assert.match(texts(waiver[0].tip), /Owner: Paul Goff, 2026-09-30/);
    assert.match(texts(waiver[0].tip), /Waive these three cells and publish/);
    assert.deepEqual(chipTexts(t.mixModel(runs.banks, null, 'Senate').chips).filter(text => /Gate waived/.test(text)), [], 'the Senate share has no waiver');
  }
  // show_warning false (the lobbying waiver): listed in the notes, no chip on the card
  assert.deepEqual(plain(t.lobbyModel(RUN.banks_lobby, 2026, 2028).chips.map(c => c.text).filter(text => /Gate waived/.test(text))), []);
  assert.equal(t.waiverEntries().length, 4, 'all four stay listed in "Sources and notes"');
  // another industry's waiver is not shown on this one's card
  const credit = session({sector: 'credit_unions', waivers: REGISTRY_WAIVERS}).t.mixModel(RUN.credit_unions, null, 'House');
  assert.equal(credit.chips.filter(c => /^Gate waived by owner/.test(c.text)).length, 1);
  // a waiver the response itself carries counts too, and the chart takes the PAC one
  const run = clone(P1.banks); run.waivers = [{gate: 'G6', cell: 'pac / commercial_banks', term: 'pac', industry: 'commercial_banks', reason: 'test', owner: 'Paul Goff', date: '2026-09-30', show_warning: true}];
  assert.deepEqual(chipTexts(session().t.chartModel(run, null, 'pac').flags).filter(text => /Gate waived/.test(text)), ['Gate waived by owner: PAC giving']);
  // none carried: none shown
  assert.deepEqual(chipTexts(session().t.mixModel(RUN.banks, null, 'House').chips).filter(text => /Gate waived/.test(text)), []);
});

test('owner waivers: the entry shape is read generically - the display text becomes the chip, the chamber finds the card, every figure goes in the tooltip', () => {
  const entry = {industry: 'commercial_banks', chamber: 'House', term: 'control', metric: 'leave-one-election-out error (pp)', published: 1.9, comparator: 1.6, date: '2026-09-30',
    display_text: 'House share: published under an owner waiver (leave-one-election-out error 1.9 pp against 1.6 pp)', show_warning: true};
  const {t} = session({waivers: [entry]});
  const house = t.mixModel(RUN.banks, null, 'House');
  const chip = house.chips.find(c => /owner waiver/.test(c.text));
  assert.equal(chip.text, entry.display_text, 'the display text of the entry is the chip');
  assert.equal(chip.kind, NEUTRAL);
  assert.match(texts(chip.tip), /Metric: leave-one-election-out error \(pp\)/);
  assert.match(texts(chip.tip), /Measured: published 1\.900 · comparator 1\.600/);
  assert.match(texts(chip.tip), /Owner: 2026-09-30/);
  assert.deepEqual(chipTexts(t.mixModel(RUN.banks, null, 'Senate').chips).filter(text => /owner waiver|Gate waived/.test(text)), [], 'a House waiver is not shown on the Senate card');
  // without display text the generic wording names the card
  const bare = session({waivers: [{industry: 'commercial_banks', chamber: 'Senate', term: 'control', date: '2026-09-30'}]}).t;
  assert.deepEqual(chipTexts(bare.mixModel(RUN.banks, null, 'Senate').chips).filter(text => /Gate waived/.test(text)), ['Gate waived by owner: Senate share']);
  // an entry that names no card is listed in the notes and drawn nowhere
  const stray = session({waivers: [{industry: 'commercial_banks', cell: 'something / else', date: '2026-09-30'}]}).t;
  assert.equal(stray.waiverEntries().length, 1);
  for (const chamber of ['House', 'Senate']) assert.deepEqual(chipTexts(stray.mixModel(RUN.banks, null, chamber).chips).filter(text => /waive/i.test(text)), []);
});

/// The entries the live calculator puts in its catalog (recorded: fixtures/giving_forecast_f2_live_landed.json): the House-share cells the owner waived, shown for the industries they name.
const CATALOG_WAIVERS = LANDED.catalog.waivers;
const pp3 = value => value.toFixed(3);

test('owner waivers: the entries the calculator catalog carries - the display text is the chip, the figures and the comparator are in the tooltip, one chip per offered industry', () => {
  assert.ok(CATALOG_WAIVERS.length >= 2, 'the landed catalog carries the owner waivers');
  const landed = sector => session({sector, source: LANDED});
  const entryOf = sector => CATALOG_WAIVERS.find(w => w.industry === sector && w.chamber === 'House');
  const banks = landed('commercial_banks').t.mixModel(LANDED.runs.banks, null, 'House');
  const entry = entryOf('commercial_banks');
  const chip = banks.chips.find(c => c.text === entry.display_text);
  assert.ok(chip, 'the display text of the entry is a chip of the House card');
  assert.equal(chip.kind, NEUTRAL);
  const tip = texts(chip.tip);
  assert.ok(tip.includes('Cell: ' + entry.cell), 'the cell is in the tooltip');
  assert.ok(tip.includes('Metric: ' + entry.metric), 'the metric is in the tooltip');
  assert.ok(tip.includes(`Measured: published ${pp3(entry.published_value)} ${entry.unit === 'percentage points' ? 'pp' : entry.unit} · comparator ${pp3(entry.comparator_value)} ${entry.unit === 'percentage points' ? 'pp' : entry.unit}`), tip);
  assert.ok(tip.includes('Comparator: ' + entry.comparator_label), 'the comparator is named');
  assert.ok(tip.includes(`Owner: ${entry.owner}, ${entry.date}`), 'the owner and the date are in the tooltip');
  assert.deepEqual(chipTexts(landed('commercial_banks').t.mixModel(LANDED.runs.banks, null, 'Senate').chips).filter(text => /waive/i.test(text)), [], 'a House waiver is not shown on the Senate card');
  // every industry the entries name shows its own entry; one the entries do not name shows none
  for (const sector of new Set(CATALOG_WAIVERS.filter(w => w.show_warning === true).map(w => w.industry))) {
    const run = sector === 'credit_unions' ? LANDED.runs.credit_unions : LANDED.runs.banks;
    const shown = chipTexts(landed(sector).t.mixModel(run, null, 'House').chips).filter(text => /waived/i.test(text));
    assert.deepEqual(shown, CATALOG_WAIVERS.filter(w => w.industry === sector && w.chamber === 'House' && w.show_warning === true).map(w => w.display_text), sector);
  }
  assert.deepEqual(chipTexts(landed('property_casualty').t.mixModel(LANDED.runs.property_casualty, null, 'House').chips).filter(text => /waive/i.test(text)), [], 'not named, not shown');
  assert.equal(landed('commercial_banks').t.waiverEntries().length, CATALOG_WAIVERS.length, 'every entry stays listed in "Sources and notes"');
});

test('the live calculator: the general-giving name and its exclusion come from its own label, and nothing pooled or invented is in its responses', () => {
  for (const [name, run] of Object.entries(LANDED.runs)) {
    if (run.status !== 'ready') continue;
    const {t} = session({source: LANDED});
    const general = run.horizons[0].pac.measures.find(m => m.id === 'general_giving');
    if (!general) continue;
    assert.equal(t.generalName(run), general.label, name + ': the account is named by the response label');
    assert.match(general.label, /^Mentat general giving \(all channels\), excluding receipts Mentat marks non-giving/, name + ': the label states what the measure leaves out');
  }
  assert.doesNotMatch(JSON.stringify(LANDED), /combined|pooled_reference/i, 'the landed responses carry no pooled reference');
  const {t} = session({source: LANDED});
  const model = t.chartModel(LANDED.runs.banks, null, 'general');
  assert.equal(model.accountLabel, LANDED.runs.banks.horizons[0].pac.measures.find(m => m.id === 'general_giving').label);
  assert.match(texts(model.columns[0].tip), /Receipts the accounting engine marks non-giving \(interest, refunds, insurance claims, loans\) are left out; the amounts are in Sources and notes\./, 'the Mentat-level tooltip says what the level leaves out');
  assert.doesNotMatch(texts(t.chartModel(LANDED.runs.banks, null, 'pac').columns[0].tip), /non-giving/, 'the roster PAC account has no such exclusion');
});

test('lobbying: two series on one chart, never summed; empty and closed states say so', () => {
  const {t} = session();
  const lobby = t.lobbyModel(RUN.banks_lobby, 2026, 2028);
  assert.equal(lobby.state, 'ready');
  assert.deepEqual(plain(lobby.series.map(s => s.label)), ['Outside-firm fees', 'In-house expenses']);
  assert.deepEqual(plain(lobby.years), [2025, 2026, 2027, 2028]);
  const [fees, inhouse] = lobby.series;
  assert.equal(fees.points[0].value, 23824000);
  assert.equal(inhouse.points[0].value, 65696931);
  assert.equal(fees.points.length, 4); assert.equal(inhouse.points.length, 4);
  for (let i = 0; i < 4; i++) assert.ok(lobby.series.every(s => Math.abs(s.points[i].value - (fees.points[i].value + inhouse.points[i].value)) > 1), 'a point equals the two series added');
  assert.match(fees.points[1].tip.map(l => l.note || '').join(' '), /never added/);
  assert.ok(lobby.axisMax >= Math.max(...inhouse.points.map(p => p.high || p.value)));
  assert.deepEqual(plain(t.lobbyModel(RUN.banks, 2026, 2028)), {state: 'empty', text: 'Enter yearly growth to project 2026–2028'});
  assert.deepEqual(plain(t.lobbyModel(null, 2026, 2028)), {state: 'empty', text: 'Enter yearly growth to project 2026–2028'});
  assert.match(t.lobbyModel(RUN.property_casualty, 2026, 2028).text, /^Not shown: No Melange-LDA sector for this industry/);
  assert.equal(lobby.dollars, 'nominal dollars');
});

test('lobbying, model fix P1: the open year is drawn from the interval conditioned on the observed quarters, in the base year\'s dollars', () => {
  const {t} = session();
  const lobby = t.lobbyModel(P1.banks_lobby, 2026, 2028);
  const s = P1.banks_lobby.horizons[0].lobbying.rows[0].series[0];
  const point = lobby.series[0].points[1];
  assert.equal(point.conditioned, true);
  assert.equal(point.value, s.cycle_given_observed_median);
  assert.equal(point.low, s.cycle_given_observed_low);
  assert.equal(point.high, s.cycle_given_observed_high);
  assert.equal(point.remaining, s.remaining_given_observed_median);
  assert.equal(lobby.dollars, '2025 dollars');
  assert.match(texts(point.tip), /given the observed quarters/);
  assert.match(texts(point.tip), /Observed Q1\+Q2: \$13\.37M \(face value\)/);
  assert.equal(lobby.series[0].points[2].conditioned, false, 'a year with no observed quarters is the model\'s own interval');
  assert.deepEqual(plain(lobby.chips), []);
});

test('lobbying, without the model fix: an interval that starts below the observed quarters is an amber chip (synthetic case)', () => {
  const {t} = session();
  const run = clone(RUN.banks_lobby), s = run.horizons[0].lobbying.rows[0].series[0];
  s.prediction_low = s.observed.amount_nominal * 0.9;
  const chips = t.lobbyModel(run, 2026, 2028).chips;
  assert.equal(chips.length, 1);
  assert.equal(chips[0].kind, AMBER);
  assert.match(chips[0].text, /interval starts below the amount already observed/);
});

test('the notes carry the conditioned figures only when the model fix is present, and every waiver', () => {
  const {t} = session({waivers: REGISTRY_WAIVERS});
  const fix = t.conditionedTables(P1.banks_lobby);
  assert.equal(fix.amounts.length, 2);
  assert.equal(fix.mixes.length, 4);
  assert.equal(fix.lobby.length, 2);
  assert.match(fix.mixes[3][5], /negative before conditioning/);
  assert.match(fix.amounts[0][0], /Roster companies' PACs/);
  assert.deepEqual(plain(t.conditionedTables(RUN.banks_lobby)), {amounts: [], mixes: [], lobby: []});
});

test('logical validity across every scenario of the fixtures: with the model fix nothing drawn contradicts the giving already observed; without it every contradiction carries an amber chip', () => {
  const industries = {banks: 'commercial_banks', banks_lobby: 'commercial_banks', banks_growth_up: 'commercial_banks', banks_growth_down: 'commercial_banks', credit_unions: 'credit_unions',
    credit_unions_lobby: 'credit_unions', credit_unions_growth_down: 'credit_unions', property_casualty: 'property_casualty'};
  let checked = 0, contradictions = 0;
  for (const [name, sector] of Object.entries(industries)) {
    for (const [pathName, runs, source] of [['P1', P1, FIXTURE], ['landed', LANDED.runs, LANDED], ['published', RUN, FIXTURE]]) {
      const {t} = session({sector, source});
      const run = runs[name];
      for (const account of ['pac', 'general']) {
        const model = t.chartModel(run, null, account);
        if (model.empty) continue;
        const cur = model.columns[1];
        if (cur.state !== 'stacked' && cur.state !== 'conflict') continue;
        checked++;
        const amber = model.flags.filter(f => f.kind === AMBER);
        if (pathName !== 'published') {
          assert.ok(cur.low >= cur.observed - 1e-6, `${name}/${account}: the whisker starts at ${cur.low}, under the ${cur.observed} observed`);
          assert.equal(cur.state, 'stacked', `${name}/${account}`);
          assert.ok(cur.remainder > 0 && cur.remainderLow >= 0, `${name}/${account}: negative remainder`);
          assert.ok(Math.abs(cur.observed + cur.remainder - cur.total) < 1e-6, `${name}/${account}: observed + remainder is not the total`);
          assert.ok(cur.low <= cur.total && cur.total <= cur.high, `${name}/${account}: the median is outside its own interval`);
          assert.ok(!amber.some(f => /starts below|exceeds the projected/.test(f.text)), `${name}/${account}: an inconsistency chip with conditioned figures`);
        } else if (cur.low < cur.observed - 0.5 || cur.state === 'conflict' || (cur.remainderLow != null && cur.remainderLow < 0)) {
          contradictions++;
          assert.ok(amber.some(f => /starts below giving already observed|exceeds the projected cycle total/.test(f.text)), `${name}/${account}: a contradiction drawn as returned without the amber chip`);
        }
      }
      for (const chamber of ['House', 'Senate']) {
        const mix = t.mixModel(run, null, chamber);
        mix.rows.forEach((row, i) => {
          if (row.state !== 'ready') return;
          checked++;
          const b = run.horizons[0].shares[chamber].bases[i];
          assert.ok(row.share >= 0 && row.share <= 1, `${name}/${chamber}/${row.label}: share ${row.share} outside 0-100%`);
          if (pathName !== 'published') {
            assert.equal(row.conditioned, true, `${name}/${chamber}/${row.label}`);
            assert.ok(row.low <= row.share + 1e-12 && row.share <= row.high + 1e-12, `${name}/${chamber}/${row.label}: the implied share is outside its own interval`);
            assert.ok(b.remaining_allocation.remaining_R_real_2025 >= 0 && b.remaining_allocation.remaining_D_real_2025 >= 0, `${name}/${chamber}/${row.label}: negative remaining amount`);
            assert.equal(row.flagged, false);
            assert.ok(!mix.chips.some(c => c.kind === AMBER && c.text === BUDGET_TEXT), `${name}/${chamber}: an amber budget chip next to conditioned amounts`);
          } else if (b.remainder_status === 'budget_inconsistent' || (b.projected_remaining_R_real_2025 != null && b.projected_remaining_R_real_2025 < 0)) {
            contradictions++;
            assert.equal(row.flagged, true, `${name}/${chamber}/${row.label}: a negative remaining amount drawn without the amber outline`);
            assert.ok(mix.chips.some(c => c.kind === AMBER && c.text === BUDGET_TEXT), `${name}/${chamber}: no amber budget chip`);
          }
        });
      }
    }
  }
  assert.ok(checked > 90, 'the sweep covered ' + checked + ' drawn marks');
  assert.ok(contradictions >= 4, 'the calculator without the fix contradicts itself in ' + contradictions + ' places the sweep must have flagged');
});

test('the footer line states only what the response says: coverage end, work units, CPI', () => {
  const {t} = session();
  assert.deepEqual(plain(t.footerFacts(RUN.banks.anchors)), ['Observed through 2026-06-30', '41 of 67 work units complete', 'No 2026 CPI yet']);
  assert.deepEqual(plain(t.footerFacts(P1.banks.anchors)), ['Observed through 2026-06-30', '41 of 67 work units complete', 'No 2026 CPI yet']);
  assert.deepEqual(plain(t.footerFacts(RUN.credit_unions.anchors)), ['Observed through 2026-05-31 (cut back from 2026-06-30)', 'No 2026 CPI yet']);
  assert.deepEqual(plain(t.footerFacts(FIXTURE.catalog.anchors.industries.commercial_banks)), ['Observed through 2026-06-30', '41 of 67 work units complete', 'No 2026 CPI yet'], 'before a calculation the same facts come from the catalog');
  assert.deepEqual(plain(t.footerFacts(null)), []);
});

test('unset inputs send no value: nothing defaults a slider to a number', () => {
  const {t} = session({outlook: false});
  t.buildInputs();
  const controls = t.getControls();
  assert.equal(controls.length, 6, 'growth and two control scores for each of the two horizons');
  assert.ok(controls.every(c => c.holder.value === ''), 'every holder starts blank');
  const request = t.getRequest();
  for (const end of [2026, 2028]) {
    const a = request.horizons[end];
    assert.equal(a.growth_pct, ''); assert.equal(a.prior_growth_pct, '');
    assert.deepEqual({...a.control_scores}, {House: '', Senate: ''});
    assert.deepEqual({...a.current_control}, {House: '', Senate: ''});
  }
  assert.deepEqual({...request.horizons[2026].annual_forecast_changes}, {2026: ''});
  assert.deepEqual({...request.horizons[2028].annual_forecast_changes}, {2027: '', 2028: ''});
  t.refreshControls();
  assert.ok(controls.every(c => c.slider.classList.contains('is-unset')), 'every slider is in its unset state');
});

test('the saved outlook stays an editable prefill of the 2026 control scores; growth and the 2027-2028 inputs stay blank', () => {
  const {t} = session();
  t.buildInputs();
  const request = t.getRequest();
  assert.equal(Number(request.horizons[2026].control_scores.House), FIXTURE.catalog.saved_outlook.control.House.value);
  assert.equal(request.horizons[2026].growth_pct, '');
  assert.equal(request.horizons[2028].control_scores.House, '');
  t.refreshControls();
  const [growth2026, house2026] = t.getControls();
  assert.equal(growth2026.slider.classList.contains('is-unset'), true);
  assert.equal(house2026.slider.classList.contains('is-unset'), false);
});

test('the reference request reads Mentat\'s levels with the anchor cycle\'s own growth and control, never what the user typed', () => {
  const {t, els} = session();
  t.buildInputs();
  const typed = t.getControls()[0].holder; typed.value = '99';
  els['gf-industry'].value = 'commercial_banks';
  const body = t.referenceRequest();
  assert.equal(body.industry, 'commercial_banks');
  assert.equal(body.as_of, '2026-09-30');
  assert.match(body.assumption_source, /^Reference levels only: the 2023–2024 growth and control, no scenario/);
  const anchorInputs = FIXTURE.catalog.political_inputs.anchor_cycles['2024'];
  const history = FIXTURE.catalog.industries.find(i => i.id === 'commercial_banks').history.find(r => r.cycle === 2024);
  for (const end of [2026, 2028]) {
    const a = body.horizons[end];
    assert.equal(a.growth_pct, history.growth_pct);
    assert.equal(a.control_scores.House, anchorInputs.House.p_rep * 100);
    assert.equal(a.current_control.Senate, anchorInputs.current_control.Senate);
    assert.deepEqual({...a.annual_forecast_changes}, {}, 'no lobbying value is invented');
  }
  assert.notEqual(body.horizons[2026].growth_pct, '99');
});

test('the historical example fills the controls and the request with the anchor cycle', () => {
  const {t} = session();
  t.buildInputs(); t.historicalExample();
  const request = t.getRequest();
  const history = FIXTURE.catalog.industries.find(i => i.id === 'commercial_banks').history.find(r => r.cycle === 2024);
  assert.equal(Number(request.horizons[2026].growth_pct), history.growth_pct);
  assert.equal(Number(request.horizons[2028].control_scores.Senate), FIXTURE.catalog.political_inputs.anchor_cycles['2024'].Senate.p_rep * 100);
  assert.equal(request.horizons[2026].current_control.House, 1);
  assert.equal(request.horizons[2026].current_control.Senate, 0);
  assert.equal(request.horizons[2026].prior_growth_pct, '', 'the prior-cycle growth stays blank: the server fills it');
  assert.doesNotMatch(request.assumption_source, /no change from the Mentat previous cycle/);
});

// The example sentence and the texts beside the marks follow what is DRAWN (owner review 2026-10-01): the model's own change is the unconditioned one, so
// where the model fix conditions the open cycle on the giving already observed, every text that quotes a change either says it is the model's change before
// conditioning or prints the change actually drawn. These helpers format like the page does (number() / signed() / percent()).
const num = value => (Math.abs(value) < 0.005 ? 0 : value).toLocaleString('en-US', {maximumFractionDigits: 2});
const sgn = value => (value >= 0.005 ? '+' : '') + num(value);
const pctTxt = value => num(value * 100) + '%';
// the change between two shares in points, from the shares as displayed (two decimals): 51.44% to 48.17% is -3.27 pp, as the numbers beside it read
const shownPp = (from, to) => Number(num(to * 100)) - Number(num(from * 100));
const EXAMPLE_HEAD = "The model's change in the amounts is zero (growth and control as in 2023–2024).";
const EXAMPLE_MIXES = "Party mixes also move: 2026 is a midterm, and the blank prior-cycle growth uses 2024's growth, which is outside the range the share models were fitted on.";
const EXAMPLE_UNKNOWN = `${EXAMPLE_HEAD} The model's projected amounts equal the 2023–2024 Mentat level before any conditioning on the giving already observed. ${EXAMPLE_MIXES}`;
const EXAMPLE_PLAIN = `${EXAMPLE_HEAD} The 2025–2026 amounts equal the 2023–2024 Mentat level. ${EXAMPLE_MIXES}`;
const EXAMPLE_CONDITIONED = `${EXAMPLE_HEAD} The 2025–2026 amounts differ from the 2023–2024 Mentat level only because they are conditioned on the giving already observed. ${EXAMPLE_MIXES}`;
const THREE_PATHS = [['without the model fix', RUN, FIXTURE], ['with the model fix P1', P1, FIXTURE], ['the live calculator', LANDED.runs, LANDED]];
const SECTORS = {banks: 'commercial_banks', credit_unions: 'credit_unions', property_casualty: 'property_casualty'};

test('the historical-example message says only what is true: the model\'s change is zero, and the drawn amounts equal the Mentat level only where nothing conditions them', () => {
  const {t, els} = session();
  assert.equal(t.conditioning(), null);
  assert.equal(t.exampleText(), EXAMPLE_UNKNOWN, 'no run yet: only the model\'s own amounts are claimed to equal the level, before any conditioning (true on both paths)');
  t.buildInputs(); t.historicalExample();
  assert.equal(els['gf-status'].textContent, 'Anchor-cycle values loaded as an example: growth and control as in 2023–2024. ' + EXAMPLE_UNKNOWN + ' Change them to explore.');
  assert.doesNotMatch(els['gf-status'].textContent, /so the projection equals/);
  assert.equal(els['gf-example-note'].textContent, EXAMPLE_UNKNOWN);
  assert.equal(els['gf-example-pill'].textContent, 'Historical example: 2023–2024 growth and control');
  // the run the message describes arrives after the example was loaded: the texts that carry it follow (the status line only while it still shows the example message)
  t.setRuns(null, P1.banks); t.refreshExample();
  assert.equal(els['gf-example-note'].textContent, EXAMPLE_CONDITIONED);
  assert.equal(els['gf-example-pill'].dataset.note, EXAMPLE_CONDITIONED);
  assert.equal(els['gf-status'].textContent, 'Anchor-cycle values loaded as an example: growth and control as in 2023–2024. ' + EXAMPLE_CONDITIONED + ' Change them to explore.');
  els['gf-status'].textContent = 'Something else the page said meanwhile.';
  t.setRuns(null, RUN.banks); t.refreshExample();
  assert.equal(els['gf-example-note'].textContent, EXAMPLE_PLAIN);
  assert.equal(els['gf-status'].textContent, 'Something else the page said meanwhile.', 'a status line that no longer shows the example message is left alone');
  // each state, from the run that is known
  assert.equal(t.conditioning(), false); assert.equal(t.exampleText(), EXAMPLE_PLAIN);
  t.setRuns(null, P1.banks);
  assert.equal(t.conditioning(), true); assert.equal(t.exampleText(), EXAMPLE_CONDITIONED);
  t.setRuns(P1.banks, null);
  assert.equal(t.exampleText(), EXAMPLE_CONDITIONED, 'the calculation counts as much as the reference levels');
});

test('the example message agrees with the amounts drawn beside it: the Mentat level only where the drawn total equals it, "conditioned" where it differs (all three calculators)', () => {
  let checked = 0;
  for (const [pathName, runs, source] of THREE_PATHS) {
    for (const name of Object.keys(SECTORS)) {
      const run = runs[name], {t} = session({sector: SECTORS[name], source});
      t.setRuns(run, run);
      const sentence = t.exampleText();
      assert.doesNotMatch(sentence, /so the projection equals/, 'the false sentence is gone');
      for (const account of ['pac', 'general']) {
        const model = t.chartModel(run, run, account);
        if (model.empty) continue;
        const cur = model.columns[1];
        if (cur.state !== 'stacked' && cur.state !== 'conflict') continue;
        const level = model.columns[0].value, equal = Math.abs(cur.total - level) < 0.5;     // the total drawn for 2025-2026 against the 2023-2024 Mentat level, to the cent
        checked++;
        if (pathName === 'without the model fix') {
          assert.ok(equal, `${pathName}/${name}/${account}: the model's projection equals the level (${cur.total} vs ${level})`);
          assert.match(sentence, /The 2025–2026 amounts equal the 2023–2024 Mentat level\./);
        } else {
          assert.ok(!equal, `${pathName}/${name}/${account}: the conditioned total differs from the level (${cur.total} vs ${level}); the message must not say it equals it`);
          assert.match(sentence, /The 2025–2026 amounts differ from the 2023–2024 Mentat level only because they are conditioned on the giving already observed\./);
          assert.doesNotMatch(sentence, /amounts equal/);
        }
      }
    }
  }
  assert.ok(checked >= 15, 'the comparison covered ' + checked + ' drawn totals');
  // the review's numbers (live calculator, banks): the PAC column draws about +2.9% over the level and the general-giving column about +0.06%
  const live = session({source: LANDED}).t;
  const pac = live.chartModel(LANDED.runs.banks, null, 'pac').columns, general = live.chartModel(LANDED.runs.banks, null, 'general').columns;
  assert.ok(pac[1].total > pac[0].value * 1.02, 'PAC: ' + pac[1].total + ' against ' + pac[0].value);
  assert.ok(general[1].total > general[0].value && general[1].total < general[0].value * 1.01, 'general giving: ' + general[1].total + ' against ' + general[0].value);
});

test('the example message says only what is true of the industry: each clause follows the catalog', () => {
  // growth inside the fitted range: the clause stays but no longer says "outside"
  const inside = session();
  const catalog = clone(FIXTURE.catalog);
  for (const m of Object.values(catalog.share_models)) m.history.filter(r => r.industry === 'commercial_banks').forEach((r, i) => { r.prior_growth_pct = i % 2 ? 60 : 0; });
  inside.t.setCatalog(catalog);
  assert.match(inside.t.exampleText(), /the blank prior-cycle growth uses 2024's growth\.$/);
  assert.doesNotMatch(inside.t.exampleText(), /outside the range/);
  // a chamber anchored on the same phase: the midterm effect is zero for it, and the sentence names the chamber's own anchor
  const same = session();
  const c2 = clone(FIXTURE.catalog);
  for (const m of Object.values(c2.share_models)) m.anchors.commercial_banks.anchor = 'same_phase';
  same.t.setCatalog(c2);
  assert.doesNotMatch(same.t.exampleText(), /midterm/);
  assert.match(same.t.exampleText(), /The 2026 House and Senate candidate mix is anchored on Mentat 2021–2022, the cycle of the same phase\.$/);
  // only the House model carries the presidential/midterm term (the Senate model has none): a same-phase House anchor removes the clause, a same-phase Senate anchor does not
  assert.equal(FIXTURE.catalog.share_models.control_House.terms.includes('Pres'), true);
  assert.equal(FIXTURE.catalog.share_models.control_Senate.terms.includes('Pres'), false);
  const onlyHouse = session(), c3 = clone(FIXTURE.catalog);
  c3.share_models.control_House.anchors.commercial_banks.anchor = 'same_phase';
  onlyHouse.t.setCatalog(c3);
  assert.doesNotMatch(onlyHouse.t.exampleText(), /midterm/, 'the House model, the only one with the term, is anchored on the same phase');
  assert.match(onlyHouse.t.exampleText(), /The 2026 House candidate mix is anchored on Mentat 2021–2022/);
  const onlySenate = session(), c4 = clone(FIXTURE.catalog);
  c4.share_models.control_Senate.anchors.commercial_banks.anchor = 'same_phase';
  onlySenate.t.setCatalog(c4);
  assert.match(onlySenate.t.exampleText(), /2026 is a midterm/, 'the House model still carries the cycle');
});

test('the projection tooltip agrees with the column it sits on: the change against the Mentat level is the one drawn, and the model\'s own change says what it is (all three calculators)', () => {
  let checked = 0;
  for (const [pathName, runs, source] of THREE_PATHS) for (const name of Object.keys(SECTORS)) for (const account of ['pac', 'general']) {
    const run = runs[name], {t} = session({sector: SECTORS[name], source}), model = t.chartModel(run, null, account);
    if (model.empty) continue;
    const cur = model.columns[1];
    if (cur.state !== 'stacked' && cur.state !== 'conflict') continue;
    const level = model.columns[0].value, drawn = (cur.total / level - 1) * 100, where = `${pathName}/${name}/${account}`;
    checked++;
    if (cur.conditioned) {
      assert.deepEqual(plain(row(cur.tip, 'Change vs Mentat 2023–2024, drawn (conditioned)')), ['Change vs Mentat 2023–2024, drawn (conditioned)', sgn(drawn) + '%'], where);
      const own = row(cur.tip, 'Model change before conditioning on the giving already observed');
      assert.ok(own && /^[+-]?[\d.,]+% \(previous cycle\)$/.test(own[1]), where + ': ' + JSON.stringify(own));
      assert.equal(row(cur.tip, 'Change vs Mentat 2023–2024'), undefined, where + ': the unlabelled model change is not printed beside a conditioned total');
      assert.ok(row(cur.tip, 'Coefficient interval (before conditioning)'), where);
    } else {
      const same = row(cur.tip, 'Change vs Mentat 2023–2024');
      assert.ok(same, where);
      assert.ok(Math.abs(parseFloat(same[1].replace(/,/g, '')) - drawn) < 0.01, `${where}: the change printed (${same[1]}) is the change drawn (${drawn})`);
    }
  }
  assert.ok(checked >= 15, 'the comparison covered ' + checked + ' drawn columns');
  // the review's case: the PAC column of banks on the live calculator draws about +2.9% over the Mentat level while the model's own change is 0%
  const pac = session({source: LANDED}).t.chartModel(LANDED.runs.banks, null, 'pac').columns[1];
  assert.match(row(pac.tip, 'Change vs Mentat 2023–2024, drawn (conditioned)')[1], /^\+2\.9\d?%$/);
  assert.equal(row(pac.tip, 'Model change before conditioning on the giving already observed')[1], '0% (previous cycle)');
});

test('the candidate-mix bar tooltip agrees with the bar: the change in share is the one drawn, and the model\'s own change says what it is (all three calculators)', () => {
  let checked = 0;
  for (const [pathName, runs, source] of THREE_PATHS) for (const name of Object.keys(SECTORS)) for (const chamber of ['House', 'Senate']) {
    const run = runs[name], {t} = session({sector: SECTORS[name], source}), mix = t.mixModel(run, null, chamber), s0 = run.horizons[0].shares[chamber];
    for (const r of mix.rows) {
      if (r.state !== 'ready' || r.anchorShare == null) continue;
      const drawn = shownPp(r.anchorShare, r.share), where = `${pathName}/${name}/${chamber}/${r.label}`;
      checked++;
      if (r.conditioned) {
        assert.deepEqual(plain(row(r.tip, 'Change in Republican share, drawn (conditioned)')), ['Change in Republican share, drawn (conditioned)', sgn(drawn) + ' pp'], where);
        assert.deepEqual(plain(row(r.tip, 'Model change before conditioning on the giving already observed')), ['Model change before conditioning on the giving already observed', sgn(s0.change_pp) + ' pp on each basis'], where);
        assert.equal(row(r.tip, 'Change in Republican share'), undefined, where + ': the unlabelled model change is not printed beside a conditioned bar');
        if (s0.change_by_term_pp) assert.ok(row(r.tip, 'Model change by input, before conditioning on the giving already observed'), where);
      } else {
        const own = row(r.tip, 'Change in Republican share');
        assert.ok(own && Math.abs(parseFloat(own[1]) - drawn) < 0.011, `${where}: the change printed (${own && own[1]}) is the change drawn (${drawn.toFixed(3)})`);
      }
    }
  }
  assert.ok(checked >= 20, 'the comparison covered ' + checked + ' drawn bars');
  // the review's cases on the live calculator: banks House employees draw 29.56% against 34.35% (-4.79 pp, where the model says -1.63 pp); the Senate bars move
  // 51.44% -> 48.17% and 64.5% -> 75.76% (the model says +6.06 pp)
  const live = session({source: LANDED}).t;
  const house = live.mixModel(LANDED.runs.banks, null, 'House').rows[0], senate = live.mixModel(LANDED.runs.banks, null, 'Senate').rows;
  assert.equal(row(house.tip, 'Change in Republican share, drawn (conditioned)')[1], '-4.79 pp');
  assert.equal(row(house.tip, 'Model change before conditioning on the giving already observed')[1], '-1.63 pp on each basis');
  assert.deepEqual(plain(senate.map(r => [pctTxt(r.anchorShare), pctTxt(r.share)])), [['51.44%', '48.17%'], ['64.5%', '75.76%']]);
  assert.equal(row(senate[0].tip, 'Model change before conditioning on the giving already observed')[1], '+6.06 pp on each basis');
});

test('the scope pill tooltip agrees with the bars: the model\'s change is labelled before conditioning, and once calculated the change drawn per basis is printed beside it', () => {
  const rowsOf = lines => lines.filter(line => line.row).map(line => line.row);
  for (const [pathName, runs, source] of THREE_PATHS.slice(1)) {
    const run = runs.banks, {t} = session({source});
    t.setRuns(null, run);                                          // before Calculate: the reference levels only, nothing is drawn yet
    const before = rowsOf(t.exampleTip());
    for (const chamber of ['House', 'Senate']) {
      const model = before.find(r => r[0] === `${chamber} change in R share, model, before conditioning on the giving already observed`);
      assert.ok(model, `${pathName}/${chamber}`);
      assert.equal(model[1].split(' · ')[0], sgn(run.horizons[0].shares[chamber].change_pp) + ' pp');
    }
    assert.equal(before.some(r => /drawn/.test(r[0])), false, pathName + ': nothing is drawn before Calculate, so nothing claims to be');
    t.setRuns(run, run);                                           // calculated
    const after = rowsOf(t.exampleTip());
    for (const chamber of ['House', 'Senate']) {
      const drawn = after.find(r => r[0] === `${chamber} change in R share, drawn (conditioned)`), bars = t.mixModel(run, run, chamber).rows.filter(r => r.state === 'ready');
      assert.ok(drawn, `${pathName}/${chamber}`);
      assert.equal(drawn[1], bars.map(r => `${r.label} ${pctTxt(r.anchorShare)} to ${pctTxt(r.share)} (${sgn(shownPp(r.anchorShare, r.share))} pp)`).join(' · '), pathName + '/' + chamber + ': the bars drawn');
    }
  }
  // the review's case on the live calculator
  const live = session({source: LANDED}).t;
  live.setRuns(LANDED.runs.banks, LANDED.runs.banks);
  const senate = rowsOf(live.exampleTip()).find(r => r[0] === 'Senate change in R share, drawn (conditioned)');
  assert.equal(senate[1], 'Employees 51.44% to 48.17% (-3.27 pp) · Roster PACs 64.5% to 75.76% (+11.26 pp)');
  assert.match(rowsOf(live.exampleTip()).find(r => r[0] === 'Senate change in R share, model, before conditioning on the giving already observed')[1], /^\+6\.06 pp · prior-cycle growth \+6\.06 pp$/);
  // a calculator without the fix names no input and conditions nothing: no change rows at all
  const plainTip = session().t; plainTip.setRuns(RUN.banks, RUN.banks);
  assert.deepEqual(plain(rowsOf(plainTip.exampleTip())), []);
});

test('the lobbying tooltip agrees with the point it sits on: the change against the base level is the one drawn, and the model\'s own change says what it is', () => {
  let checked = 0;
  for (const [pathName, runs, source] of THREE_PATHS) {
    const {t} = session({sector: 'commercial_banks', source}), model = t.lobbyModel(runs.banks_lobby, 2026, 2028);
    for (const item of model.series) {
      const base = item.points[0].value;
      for (const p of item.points.slice(1)) {
        const drawn = (p.value / base - 1) * 100, where = `${pathName}/${item.label}/${p.year}`;
        checked++;
        if (p.conditioned) {
          assert.deepEqual(plain(row(p.tip, 'Change vs the 2025 level, drawn (conditioned)')), ['Change vs the 2025 level, drawn (conditioned)', sgn(drawn) + '%'], where);
          assert.ok(row(p.tip, 'Model change before conditioning on the observed quarters'), where);
          assert.equal(row(p.tip, 'Change vs the 2025 level'), undefined, where);
        } else {
          const own = row(p.tip, 'Change vs the 2025 level');
          assert.ok(own && Math.abs(parseFloat(own[1].replace(/,/g, '')) - drawn) < 0.01, `${where}: ${own && own[1]} against ${drawn}`);
        }
      }
    }
  }
  assert.ok(checked >= 6, 'the comparison covered ' + checked + ' drawn points');
});

const WIDE_TEXT = 'Share interval extends outside 0-100% (linear share model on a thin base); treat it as unreliable.';
test('a mix row whose drawn share interval leaves 0-100% gets an amber chip and an amber outline and is not clipped (credit unions on the live calculator and on the others)', () => {
  for (const [pathName, runs, source] of THREE_PATHS) {
    const {t} = session({sector: 'credit_unions', source}), senate = t.mixModel(runs.credit_unions, null, 'Senate');
    const wide = senate.rows.filter(r => r.state === 'ready' && (r.low < 0 || r.high > 1));
    assert.ok(wide.length >= 1, `${pathName}: a Senate row of the credit-union card has an interval outside 0-100%`);
    const chips = senate.chips.filter(c => c.text === WIDE_TEXT);
    assert.equal(chips.length, 1, pathName + ': one amber chip however many rows');
    assert.equal(chips[0].kind, AMBER);
    assert.equal(senate.chips[0].text, WIDE_TEXT, pathName + ': amber chips come first');
    assert.deepEqual(plain(senate.rows.filter(r => r.wide).map(r => r.label)), plain(wide.map(r => r.label)));
    for (const r of wide) {
      assert.match(texts(chips[0].tip), new RegExp(r.label + ': .*' + (r.conditioned ? 'implied full-cycle share, 95% interval' : '95% prediction interval')));
      assert.ok(texts(chips[0].tip).includes(`${pctTxt(r.low)} to ${pctTxt(r.high)}`), pathName + ': the interval is printed as returned (' + pctTxt(r.low) + ' to ' + pctTxt(r.high) + ')');
      assert.match(r.aria, /Share interval extends outside 0-100%/);
      if (r.conditioned) assert.equal(r.flagged, false, 'the budget state is a different flag');
    }
    // not clipped: the interval is the model's own
    const base = runs.credit_unions.horizons[0].shares.Senate.bases.find(b => b.id === 'pac_candidate'), alloc = base.remaining_allocation;
    const own = senate.rows.find(r => r.id === 'pac_candidate');
    assert.equal(own.low, alloc ? alloc.implied_cycle_R_share_prediction_low : base.cycle_prediction_low);
  }
  // the live calculator's numbers (the review): -1.89% to 4.69%
  const live = session({sector: 'credit_unions', source: LANDED}).t.mixModel(LANDED.runs.credit_unions, null, 'Senate').rows.find(r => r.id === 'pac_candidate');
  assert.equal(`${pctTxt(live.low)} to ${pctTxt(live.high)}`, '-1.89% to 4.69%');
  // banks: no row leaves the range, so no chip; a synthetic row above 100% gets one
  for (const [pathName, runs, source] of THREE_PATHS) for (const chamber of ['House', 'Senate']) {
    assert.deepEqual(plain(session({source}).t.mixModel(runs.banks, null, chamber).chips.filter(c => c.text === WIDE_TEXT)), [], `${pathName}/banks/${chamber}`);
  }
  const run = clone(P1.banks), alloc = run.horizons[0].shares.House.bases[0].remaining_allocation;
  alloc.implied_cycle_R_share_prediction_high = 1.2;
  const synthetic = session().t.mixModel(run, null, 'House');
  assert.equal(synthetic.chips.filter(c => c.text === WIDE_TEXT).length, 1);
  assert.deepEqual(plain(synthetic.rows.map(r => r.wide)), [true, false]);
});

test('the 2026 control rows open filled from the saved outlook and say where the numbers come from; every other input opens blank', () => {
  for (const [name, source] of [['the published catalog', FIXTURE], ['the live catalog', LANDED]]) {
    const {t} = session({source}), snapshot = source.catalog.saved_outlook;
    t.buildInputs();
    const [g26, h26, s26, g28, h28, s28] = t.getControls(), [ph26, ps26, ph28, ps28] = t.getPills();
    assert.equal(Number(h26.holder.value), snapshot.control.House.value, name);
    assert.equal(Number(s26.holder.value), snapshot.control.Senate.value, name);
    assert.deepEqual([ph26.value, ps26.value].map(String), [String(snapshot.control.House.current_control), String(snapshot.control.Senate.current_control)]);
    for (const c of [g26, g28, h28, s28]) { assert.equal(c.holder.value, '', name + ': blank'); assert.equal(c.saved, undefined, name + ': no saved outlook behind it'); }
    assert.deepEqual([ph28.value, ps28.value].map(String), ['', ''], name + ': the 2027-2028 pills are unset');
    // the source is said beside each row, from the catalog
    const text = `Saved outlook · Polymarket Jan–Jun · as of ${snapshot.control.House.as_of}`;
    for (const c of [h26, s26]) {
      assert.equal(c.saved.source.children[0].textContent, text, name);
      assert.equal(c.saved.source.title, c.saved.title);
      assert.ok(c.saved.title.startsWith(`Saved ${snapshot.cycle} outlook, as of ${snapshot.control.House.as_of}: Polymarket mean of the daily probability of Republican control from ${snapshot.control.House.window.start} to ${snapshot.control.House.window.end}.`), name);
    }
    t.refreshControls();
    assert.deepEqual([h26, s26].map(c => c.saved.source.classList.contains('is-quiet')), [false, false], 'shown while the rows hold the saved values');
    assert.deepEqual([h26, s26].map(c => c.slider.classList.contains('is-unset')), [false, false]);
    // the request on open: the saved scores and pills for 2026 only
    const request = t.getRequest();
    assert.equal(Number(request.horizons[2026].control_scores.House), snapshot.control.House.value);
    assert.equal(String(request.horizons[2026].current_control.Senate), String(snapshot.control.Senate.current_control));
    assert.deepEqual({...request.horizons[2028].control_scores}, {House: '', Senate: ''});
    assert.equal(request.horizons[2026].growth_pct, '');
    // typing another score, or changing the pill, ends the claim for that row only; typing the saved score back restores it
    h26.holder.value = '30'; t.refreshControls();
    assert.deepEqual([h26, s26].map(c => c.saved.source.classList.contains('is-quiet')), [true, false]);
    assert.equal(h26.saved.clear.classList.contains('is-quiet'), true);
    h26.holder.value = String(snapshot.control.House.value); t.refreshControls();
    assert.equal(h26.saved.source.classList.contains('is-quiet'), false);
    ps26.value = 0; t.refreshControls();
    assert.deepEqual([h26, s26].map(c => c.saved.source.classList.contains('is-quiet')), [false, true]);
    ps26.value = snapshot.control.Senate.current_control; t.refreshControls();
    // clearing the House row puts the score and the pill back to the real unset state: nothing is sent for them, the Senate row is untouched
    t.clearSaved(h26);
    assert.equal(h26.holder.value, ''); assert.equal(ph26.value, '');
    assert.equal(h26.slider.classList.contains('is-unset'), true); assert.equal(h26.saved.source.classList.contains('is-quiet'), true); assert.equal(h26.saved.clear.classList.contains('is-quiet'), true);
    const cleared = t.getRequest();
    assert.equal(cleared.horizons[2026].control_scores.House, ''); assert.equal(cleared.horizons[2026].current_control.House, '');
    assert.equal(Number(cleared.horizons[2026].control_scores.Senate), snapshot.control.Senate.value, 'the other row is untouched');
    assert.equal(s26.saved.source.classList.contains('is-quiet'), false);
    t.clearSaved(s26);
    const none = t.getRequest();
    assert.deepEqual({...none.horizons[2026].control_scores}, {House: '', Senate: ''}); assert.deepEqual({...none.horizons[2026].current_control}, {House: '', Senate: ''});
  }
  // a catalog without a saved outlook, or one for another cycle: every row opens blank and no caption exists
  for (const strip of [catalog => { delete catalog.saved_outlook; }, catalog => { catalog.saved_outlook.cycle = 2024; }]) {
    const {t} = session(), catalog = clone(FIXTURE.catalog);
    strip(catalog); t.setCatalog(catalog); t.buildInputs();
    assert.ok(t.getControls().every(c => c.holder.value === '' && c.saved === undefined));
  }
});

test('a refusal or a missing run draws nothing and invents nothing', () => {
  const {t} = session();
  assert.deepEqual(plain(t.chartModel({status: 'anchor_stale', reason: 'old'}, null, 'general')), {empty: true, account: 'general', message: ''});
  assert.deepEqual(plain(t.mixModel({status: 'anchor_stale'}, null, 'House').rows), []);
  assert.equal(t.lobbyModel({status: 'anchor_stale'}, 2026, 2028).state, 'empty');
});
