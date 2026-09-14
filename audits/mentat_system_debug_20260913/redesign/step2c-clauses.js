/* Step 2c: one filter pill can mean more than one server clause. Member lists
   become IN (exclusion becomes a chain of NE, which is AND-compatible) and a
   range becomes its two bounds. An unset filter produces no clause at all,
   instead of the empty-string equality the shelf used to send. */
'use strict';

const clauses = `  function clauses(filter,field){
    const op=filter.op,values=Array.isArray(filter.value)?filter.value:[filter.value];
    if(op==='in'||op==='notin'){
      const chosen=values.filter(v=>v!==''&&v!=null).map(v=>filterValue(v,field));
      if(!chosen.length)return [];
      if(chosen.length>1000)throw new Error('Choose at most 1,000 members, or use Is not one of.');
      return op==='in'?[{field:field.id,op:'in',value:chosen}]:chosen.map(value=>({field:field.id,op:'ne',value}));
    }
    if(op==='between'){
      const out=[];
      if(values[0]!==''&&values[0]!=null)out.push({field:field.id,op:'gte',value:filterValue(values[0],field)});
      if(values[1]!==''&&values[1]!=null)out.push({field:field.id,op:'lte',value:filterValue(values[1],field)});
      return out;
    }
    const simple={equals:'eq',contains:'contains',gte:'gte',lte:'lte'}[op];
    if(!simple)throw new Error('Choose a supported filter operation.');
    if(field.role==='measure'&&simple==='contains')throw new Error('Numeric filters use Equals, At least, At most or Between.');
    if(filter.value===''||filter.value==null)return [];
    return [{field:field.id,op:simple,value:filterValue(filter.value,field)}];
  }
`;

module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\app',
  eol: 'crlf',
  files: [{
    path: 'chart-studio-contributions.js',
    edits: [
      {
        find: `  function compile(state,columns,{dataset,basis='receipt',offset=0}={}){`,
        replace: clauses + `  function compile(state,columns,{dataset,basis='receipt',offset=0}={}){`
      },
      {
        find: `    for(const f of state.filters||[]){const field=byIndex.get(Number(f.column));if(!field)continue;const op={equals:'eq',contains:'contains',gte:'gte',lte:'lte'}[f.op];if(!op)throw new Error('Choose a supported filter operation.');if(field.role==='measure'&&op==='contains')throw new Error('Numeric filters use Equals, At least or At most.');const out={field:field.id,op,value:filterValue(f.value,field)};(f.stage==='aggregate'||field.role==='measure'&&field.id!=='amount'?aggregate_filters:filters).push(out);}`,
        replace: `    for(const f of state.filters||[]){const field=byIndex.get(Number(f.column));if(!field)continue;const target=f.stage==='aggregate'||field.role==='measure'&&field.id!=='amount'?aggregate_filters:filters;for(const clause of clauses(f,field))target.push(clause);}`
      },
      {
        find: `  const api={fields,compile,filterValue,showMeEligibility,showMeApply,markFilters,mapSelection,sameSource,csv,BASIS,MONEY,EXTRA_MARKS};`,
        replace: `  const api={fields,compile,clauses,filterValue,showMeEligibility,showMeApply,markFilters,mapSelection,sameSource,csv,BASIS,MONEY,EXTRA_MARKS};`
      }
    ]
  }]
};
