const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(require.resolve('playwright',{paths:['C:/Users/pgoff/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules']}));
const app=path.resolve(__dirname,'../../../mentat/app');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'chrome'});
 try{
  const page=await browser.newPage();page.setDefaultTimeout(10000);
  await page.setContent(fs.readFileSync(path.join(app,'contribution-studio.html'),'utf8').replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi,'').replace(/<link\b[^>]*>/gi,''));
  await page.evaluate(()=>{
   const fields=[...['company','cycle'].map(id=>({id,label:id,name:id,role:'dimension'})),...['amount','records','contributors'].map(id=>({id,label:id,name:id,role:'measure',unit:id==='amount'?'cents':'count'}))];
   const provenance={workbook:'Synthetic.xlsx',workbook_sha256:'a'.repeat(64),database_sha256:'a'.repeat(64),index_token:'old-index',query_engine_sha256:'same-engine'};
   const response=value=>({ok:true,json:async()=>value});
   window.fetch=async(url,options)=>{
    const q=options?.body?JSON.parse(options.body):{};
    if(url.endsWith('/session'))return response({token:'fixture',read_only:true});
    if(url.endsWith('/catalog'))return response({datasets:[{id:'Banking',label:'Synthetic',available:true,fields,bases:[{id:'receipt',label:'Included receipts'}],provenance}],fields});
    if(url.endsWith('/query'))return response({rows:[{company:'Fixture Company',cycle:'2023-2024',amount:10000,records:1,contributors:1}],columns:[...q.dimensions,...q.measures].map(id=>fields.find(f=>f.id===id)),totals:{amount:10000,records:1,contributors:1},basis_label:'Included receipts',group_count:1,offset:0,has_more:false,provenance,reconciliation:{conserved:true,receipt_matches_workbook:true},notices:[]});
    if(url.endsWith('/records'))return response({rows:[{company:'Fixture Company',contributor:'CHANGED SOURCE DONOR',amount_cents:90000,raw_cents:90000,date:'2024-01-01',source_id:'new-record',reasons:[]}],total_records:1,has_more:false,provenance:{...provenance,workbook_sha256:'b'.repeat(64),database_sha256:'b'.repeat(64),index_token:'new-index'}});
    throw new Error(url);
   };
  });
  for(const script of ['contribution-plot.js','contribution-studio.js'])await page.addScriptTag({path:path.join(app,script)});
  await page.waitForFunction(()=>document.querySelector('#visualization svg'));
  await page.locator('#inspect-all').click();await page.waitForFunction(()=>document.querySelector('#record-table').textContent.includes('CHANGED SOURCE DONOR'));
  const evidence=await page.evaluate(()=>({chart_total:document.querySelector('#receipt-values').textContent,inspection:document.querySelector('#record-table').textContent,error:document.querySelector('#error').textContent,inspection_scope:document.querySelector('#inspection-scope').textContent}));
  assert.match(evidence.chart_total,/\$100\.00/);assert.match(evidence.inspection,/\$900\.00/);assert.equal(evidence.error,'');
  fs.writeFileSync(path.join(__dirname,'stale-inspection.json'),JSON.stringify(evidence,null,2)+'\n');console.log(JSON.stringify(evidence));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
