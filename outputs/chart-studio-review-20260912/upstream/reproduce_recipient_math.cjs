const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const enginePath='C:/Users/pgoff/Mentat/mentat/app/chart-math.js',math=require(enginePath);
const data=JSON.parse(fs.readFileSync(path.join(__dirname,'banking_recipient_chart_data.json')));
const config={type:'bar',x:0,y:1,aggregation:'sum',maxGroups:60};
function run(cfg){const result=math.build(data,cfg);return {config:cfg,selected:result.selected,excluded:result.excluded,groups:result.groups,total:result.groups.reduce((a,g)=>a+g.value,0)};}
const result={source_file:data.source_file,source_sha256:data.sha256,sheet:data.sheet,engine:enginePath,engine_sha256:crypto.createHash('sha256').update(fs.readFileSync(enginePath)).digest('hex'),unrestricted:run(config),industry_only:run({...config,filters:[{column:2,op:'equals',value:'Industry'}]}),company_only:run({...config,filters:[{column:2,op:'equals',value:'Company'}]})};
fs.writeFileSync(path.join(__dirname,'recipient_math_reproduction.json'),JSON.stringify(result,null,2));
console.log(JSON.stringify(result,null,2));
