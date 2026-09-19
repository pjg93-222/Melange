const assert = require('node:assert/strict');
const view = require('../app/coverage-view.js');
const browserContext = {window:{}};
require('node:vm').runInNewContext(require('node:fs').readFileSync(require.resolve('../app/coverage-view.js'),'utf8'),browserContext);
assert.equal(typeof browserContext.window.MentatCoverage?.html,'function');
assert.equal(typeof browserContext.window.MentatCoverage?.select,'function');
const rows = [
  {industry:'Fintech',cycle:2026,freshness:'stale',verified_data_through:'2026-06-30',latest_observed_transaction_date:'2026-09-01',lag_days:72,target_date:'2026-09-10',reason:'Old evidence'},
  {industry:'Fintech',cycle:2024,freshness:'current',verified_data_through:'2024-12-31',lag_days:0,target_date:'2024-12-31'},
  {industry:'Other',cycle:2026,freshness:'unverifiable',reason:'Missing receipt'},
];
assert.equal(view.select(rows,[' fintech '],[2026]).length,1);
assert.equal(view.select(rows,['New sector'],[2022,2026]).length,2);
assert.equal(view.select(rows,['New sector'],[2026])[0].freshness,'unverifiable');
assert.match(view.html(rows),/Stale coverage/);
assert.match(view.html(rows),/Current within policy/);
assert.match(view.html(rows),/Unverifiable coverage/);
assert.match(view.html(rows),/Observed only; does not establish coverage/);
assert.match(view.html(rows),/2026-06-30/);
assert.match(view.html([]),/Unverifiable/);
const unsafe = view.html([{...rows[0],industry:'<img src=x onerror=alert(1)>',reason:'<script>oops</script>',receipt:'<b>bad</b>'}]);
assert.doesNotMatch(unsafe,/<img|<script>|<b>bad/);
assert.match(unsafe,/&lt;img/);
assert.match(view.html([{...rows[0],freshness:'unverifiable'}]),/<td>Unknown<\/td>/);
console.log('Coverage view checks passed.');
