// Read-only probes of the current Chart Studio compiler.
const assert = require('node:assert/strict');
const core = require('../../mentat/app/chart-studio-core.js');
const math = require('../../mentat/app/chart-math.js');
const columns = [
  {index:0,name:'State',type:'category'},
  {index:1,name:'ZIP5',type:'category'},
  {index:2,name:'Total Giving',type:'number'},
  {index:3,name:'Gift Count',type:'number'}
];
const data = {columns,rows:[['MA','02108',100,1],['MA','02109',200,2]],row_numbers:[6,7],row_count:2};
const state = core.createSheet();
state.columns = [{column:0,aggregation:'sum'}];
state.rows = [{column:2,aggregation:'sum'}];
const compile = s => core.compileReport(s,columns);
const baseline = compile(state);
const scenarios = {};
for (const target of ['second_dimension','second_measure','detail','size','label','tooltip']) {
  const s = JSON.parse(JSON.stringify(state));
  if (target === 'second_dimension') s.columns.push({column:1,aggregation:'sum'});
  else if (target === 'second_measure') s.rows.push({column:3,aggregation:'sum'});
  else if (['detail','tooltip'].includes(target)) s.marks[target] = [{column:1,aggregation:'sum'}];
  else s.marks[target] = {column:target === 'size' ? 3 : 1,aggregation:'sum'};
  const r = compile(s);
  assert.deepEqual(r.config,baseline.config);
  assert.equal(r.issues.length,0);
  assert.equal(r.notes.length,0);
  scenarios[target] = {same_config:true,issues:r.issues,notes:r.notes,groups:math.build(data,r.config).groups};
}
const numericZip = core.classifyFields([{index:0,name:'ZIP5',type:'number'}]).fields[0];
const countState = JSON.parse(JSON.stringify(state));
countState.rows = [{column:3,aggregation:'count'}];
const countConfig = compile(countState).config;
const giftCount = math.build(data,countConfig).groups;
console.log(JSON.stringify({baseline:baseline.config,scenarios,numericZip,giftCountCountAggregation:giftCount,expectedGiftCountSum:3},null,2));
