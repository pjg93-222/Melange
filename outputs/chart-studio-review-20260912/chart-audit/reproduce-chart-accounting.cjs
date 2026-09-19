'use strict';
// Read-only execution of shipped pure calculation modules. All rows are synthetic.
const assert = require('node:assert/strict');
const math = require('../../../mentat/app/chart-math.js');
const core = require('../../../mentat/app/chart-studio-core.js');
const dataset = (columns, rows) => ({columns: columns.map((c,index)=>({index,...c})), rows, row_numbers:rows.map((_,i)=>i+2), row_count:rows.length});
const base = {type:'bar',x:0,y:1,series:-1,aggregation:'sum',transform:'none',filters:[],splitMulti:false,maxGroups:40};
const money = dataset([{name:'ZIPs',type:'category'},{name:'Amount',type:'number'}], [['10001; 10002; 10003',100],['10001',50]]);
const unsplit = math.build(money, base);
const splitConfig = {...base,splitMulti:true};
const split = math.build(money, splitConfig);
assert.equal(core.grandTotal(unsplit,base),150);
assert.equal(core.grandTotal(split,splitConfig),350);
console.log(JSON.stringify({case:'ZIP split duplicates money and produces a money grand total',sourceMoney:150,plotted:split.groups,grandTotal:core.grandTotal(split,splitConfig),status:core.rowsToMarksSummary(split,splitConfig,money.columns),note:split.note}));

const multi = dataset([{name:'ZIPs',type:'category'},{name:'Amount',type:'number'},{name:'Districts',type:'category'}], [['10001; 10002; 10003',100,'NY-10; NY-12']]);
const multiConfig = {...base,type:'grouped',series:2,splitMulti:true};
const crossed = math.build(multi,multiConfig);
const crossedMoney = core.markValues(crossed).reduce((a,b)=>a+b,0);
assert.equal(crossedMoney,600);
console.log(JSON.stringify({case:'ZIP and district splitting creates every pair',sourceMoney:100,plottedMoney:crossedMoney,selected:crossed.selected,groups:crossed.groups,grandTotal:core.grandTotal(crossed,multiConfig),note:crossed.note}));

const repeated = dataset(money.columns,[['10001; 10001',100]]);
const repeatedResult = math.build(repeated,splitConfig);
assert.equal(repeatedResult.groups[0].value,200);
console.log(JSON.stringify({case:'Repeated identical ZIP token repeats same money in the same mark',sourceMoney:100,plotted:repeatedResult.groups,grandTotal:core.grandTotal(repeatedResult,splitConfig)}));

const time = dataset([{name:'Year',type:'category'},{name:'Amount',type:'number'}], [[2022,100],[2023,200],[2024,400]]);
const yoyConfig = {...base,type:'line',transform:'yoy',period:'year'};
const yoy = math.build(time,yoyConfig);
assert.equal(core.grandTotal(yoy,yoyConfig),200);
console.log(JSON.stringify({case:'YoY percentages summed into SUM(Amount) status',plotted:yoy.groups,status:core.rowsToMarksSummary(yoy,yoyConfig,time.columns),refusal:core.totalNote(yoy,yoyConfig)}));

const history = dataset([{name:'Year',type:'category'},{name:'Amount',type:'number'}],Array.from({length:8},(_,i)=>[2016+i,(i+1)*100]));
const forecastConfig = {...base,type:'line',transform:'forecast',period:'year',horizon:2,as_of:'2025-01-01'};
const forecast = math.build(history,forecastConfig);
assert.equal(core.grandTotal(forecast,forecastConfig),4700);
console.log(JSON.stringify({case:'Grand total includes forecast repeats as money',actualMoney:3600,forecastMoney:1100,grandTotal:core.grandTotal(forecast,forecastConfig),status:core.rowsToMarksSummary(forecast,forecastConfig,history.columns),plotted:forecast.groups.map(g=>({year:g.year,value:g.value,forecast:!!g.forecast}))}));

const countData = dataset([{name:'Company',type:'category'},{name:'Amount',type:'number'}],[['A',100],['A',null],['B',50]]);
const countConfig = {...base,aggregation:'count'};
const countResult = math.build(countData,countConfig);
assert.equal(core.grandTotal(countResult,countConfig),3);
console.log(JSON.stringify({case:'Count(Amount) counts a missing Amount',nonNullAmounts:2,status:core.rowsToMarksSummary(countResult,countConfig,countData.columns),groups:countResult.groups,excluded:countResult.excluded}));

const filterData = dataset([{name:'Company',type:'category'},{name:'Amount',type:'number'}],[['A',60],['A',60],['B',150]]);
const filtered = math.build(filterData,{...base,filters:[{column:1,op:'gte',value:'100'}]});
assert.deepEqual(filtered.groups.map(g=>g.label),['B']);
console.log(JSON.stringify({case:'Measure filter is row-level only (Tableau aggregate SUM filter would keep A too)',unfilteredGroups:math.build(filterData,base).groups,amountGte100:filtered.groups}));
