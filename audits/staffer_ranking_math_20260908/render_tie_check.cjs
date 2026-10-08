const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const text = fs.readFileSync(process.argv[2] || 'fec/surfaces/templates/make_staffer_network_html_00.tpl', 'utf8');
const source = text.match(/function drawTables\(r\)\{[\s\S]*?\n\}/)[0];
const cells = {};
const context = {document: {querySelector: key => cells[key] ||= {}},
  META: {}, esc: x => String(x), num: x => String(x)};
vm.createContext(context);
vm.runInContext(source, context);
function render(people) {
  context.drawTables({top_staff: people});
  const html = cells['#stf-topstaff tbody'].innerHTML;
  return {html, ranks: [...html.matchAll(/<td class=stf-n>(.*?)<\/td>/g)]
    .map(m => m[1]).filter((_, i) => i % 2 === 0)};
}
const person = {pagerank_085: 1, member_connection_strength: 10, rank_tie_size: 2};
assert.deepEqual(render([person, person, {...person, member_connection_strength: 5, rank_tie_size: 1}]).ranks,
  ['1 =', '1 =', '3']);
const cutoff = render([{...person, rank_tie_size: 4}]);
assert.deepEqual(cutoff.ranks, ['1 =']);
assert.ok(cutoff.html.includes('Equal ranking keys for 4 eligible people'));
assert.deepEqual(render([{pagerank_085: 1}, {pagerank_085: 1}]).ranks, ['1', '2']);
assert.ok(cutoff.html.includes('Person-only connectedness'));
console.log('PASS: shared rank, cutoff tie disclosure, legacy unknown ties, persons-only description');
