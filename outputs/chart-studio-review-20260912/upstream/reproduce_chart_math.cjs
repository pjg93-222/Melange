const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const enginePath = 'C:/Users/pgoff/Mentat/mentat/app/chart-math.js';
const math = require(enginePath);
const employee = JSON.parse(fs.readFileSync(path.join(__dirname,'banking_employee_chart_data.json')));
const overview = JSON.parse(fs.readFileSync(path.join(__dirname,'banking_overview_chart_data.json')));
const config = {type:'bar',x:0,y:1,aggregation:'sum',maxGroups:60};
function run(data,cfg){
  const model=math.build(data,cfg);
  return {config:cfg,selected:model.selected,excluded:model.excluded,mark_count:model.groups.length,mark_value_sum:model.groups.reduce((s,g)=>s+g.value,0),notes:model.notes,note:model.note,split:model.split};
}
const result={engine:enginePath,engine_sha256:crypto.createHash('sha256').update(fs.readFileSync(enginePath)).digest('hex'),source_sha256:employee.sha256,scope:employee.scope,
  zip_split_off:run(employee,{...config,splitMulti:false}),
  zip_split_on:run(employee,{...config,splitMulti:true}),
  overview_all_rows:run(overview,config),
  overview_totals_only:run(overview,{...config,filters:[{column:2,op:'equals',value:'Total Giving'}]}),
  overview_cycle2024_all:run(overview,{...config,filters:[{column:0,op:'equals',value:'2023-2024'}]}),
  overview_cycle2024_totals_only:run(overview,{...config,filters:[{column:0,op:'equals',value:'2023-2024'},{column:2,op:'equals',value:'Total Giving'}]})};
fs.writeFileSync(path.join(__dirname,'chart_math_reproduction.json'),JSON.stringify(result,null,2));
console.log(JSON.stringify(result,null,2));
