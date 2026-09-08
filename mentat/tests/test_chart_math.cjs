const {test} = require('node:test');
const assert = require('node:assert/strict');
const math = require('../app/chart-math.js');
const data = {
  columns:[{index:0,name:'Company',type:'category',distinct:2},{index:1,name:'Amount',type:'number',distinct:4},{index:2,name:'Date',type:'date',distinct:3}],
  rows:[['A',10,'2026-01-02'],['A',30,'2026-01-01'],['B',60,'2026-01-03'],['B',null,'2026-01-01']], row_numbers:[6,7,8,9]
};
const config = {type:'bar',x:0,y:1,aggregation:'sum',filters:[]};
test('missing, signed, currency, percent and finite numeric values',()=>{
  assert.equal(math.numeric(null),null); assert.equal(math.numeric(''),null); assert.equal(math.numeric(true),null);
  assert.equal(math.numeric('NaN'),null); assert.equal(math.numeric(Infinity),null); assert.equal(math.numeric('1,2'),null);
  assert.equal(math.numeric('$1,250.25'),1250.25); assert.equal(math.numeric('($20.50)'),-20.5); assert.equal(math.numeric('25%'),.25);
  assert.equal(math.numeric(1e-9),1e-9); assert.equal(math.numeric(0),0);
});
test('known quartiles, Tukey whiskers and outlier',()=>{
  assert.deepEqual(math.box([1,2,3,4,100]),{n:5,q1:2,median:3,q3:4,low:1,high:4,outliers:[100]});
  assert.deepEqual(math.box([8]),{n:1,q1:8,median:8,q3:8,low:8,high:8,outliers:[]});
  assert.equal(math.quantile([1,2,3,4],.25),1.75);
});
test('grouped sum, mean and count retain missing distinction',()=>{
  const sum=math.build(data,config);
  assert.deepEqual(sum.groups,[{label:'A',value:40,n:2},{label:'B',value:60,n:1}]);
  assert.equal(sum.excluded,1);
  assert.equal(math.build(data,{...config,aggregation:'mean'}).groups[0].value,20);
  const count=math.build(data,{...config,aggregation:'count'});
  assert.equal(count.groups[1].value,2); assert.equal(count.excluded,0);
});
test('AND filters and worksheet row ranges drive subsection totals',()=>{
  const filtered=math.build(data,{...config,start:7,end:9,filters:[{column:0,op:'equals',value:'a'},{column:1,op:'gte',value:20}]});
  assert.equal(filtered.selected,1); assert.equal(filtered.groups[0].value,30);
  assert.throws(()=>math.build(data,{...config,filters:[{column:1,op:'gte',value:'oops'}]}),/number/);
  assert.throws(()=>math.build(data,{...config,start:9,end:6}),/precede/);
  assert.throws(()=>math.build(data,{...config,filters:[{column:0,op:'equals',value:'absent'}]}),/No rows/);
});
test('pie rejects negative values and all-zero totals',()=>{
  assert.throws(()=>math.build({...data,rows:[['A',-1],['A',10]],row_numbers:[6,7]},{...config,type:'pie'}),/nonnegative/);
  assert.throws(()=>math.build({...data,rows:[['A',0]],row_numbers:[6]},{...config,type:'pie'}),/positive total/);
});
test('line orders dates and histogram counts each observation once',()=>{
  assert.deepEqual(math.build(data,{...config,type:'line',x:2}).groups.map(g=>g.label),['2026-01-01','2026-01-02','2026-01-03']);
  const histogram=math.build(data,{...config,type:'histogram'});
  assert.equal(histogram.groups.reduce((s,g)=>s+g.value,0),3);
  const constant=math.build({...data,rows:[['A',2],['B',2]],row_numbers:[6,7]},{...config,type:'histogram'});
  assert.equal(constant.groups.length,1); assert.equal(constant.groups[0].value,2);
});
test('scatter excludes incomplete pairs; boxes use individual observations',()=>{
  const scatter=math.build(data,{...config,type:'scatter',x:1});
  assert.deepEqual(scatter.points,[{x:10,y:10},{x:30,y:30},{x:60,y:60}]); assert.equal(scatter.excluded,1);
  assert.equal(math.build(data,{...config,type:'box'}).groups[0].median,20);
  assert.throws(()=>math.build(data,{...config,type:'scatter',x:0}),/No numeric/);
});
test('recommendations use detected types and grouping cardinality',()=>{
  const suggested=math.recommend(data.columns);
  assert.equal(suggested[0].type,'bar'); assert(suggested.some(s=>s.type==='box')); assert(suggested.some(s=>s.type==='line'));
  assert.equal(suggested.find(s=>s.type==='pie').aggregation,'count');
  assert(!suggested.some(s=>s.type==='scatter'));
});
test('all missing and oversized groups refuse misleading charts',()=>{
  assert.throws(()=>math.build({...data,rows:[['A',null]],row_numbers:[6]},config),/No numeric/);
  const rows=Array.from({length:61},(_,i)=>['Group '+i,i]);
  assert.throws(()=>math.build({...data,rows,row_numbers:rows.map((_,i)=>i+6)},config),/60 groups/);
});
test('category labels remain literal and input rows stay unchanged',()=>{
  const evil={...data,rows:[['<script>alert(1)</script>',3],['__proto__',4]],row_numbers:[6,7]};
  const before=JSON.stringify(evil);
  assert.equal(math.build(evil,config).groups[0].label,'<script>alert(1)</script>');
  assert.equal(JSON.stringify(evil),before);
});
