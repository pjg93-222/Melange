'use strict';
// Complete, narrow immutable-data kinds. None is a full application workspace.
const path=require('node:path');
const GiB=1024**3,MiB=1024**2;
const CORE_KINDS=Object.freeze({melange:Object.freeze(['melange.staffer-graph-core.v1','melange.payroll-identity-core.v1']),mentat:Object.freeze(['mentat.aggregate-forecast-core.v1'])});
const role=(path,maxBytes)=>Object.freeze({path,maxBytes});
const GRAPH=Object.freeze({
 'graph-receipt':role('graph/receipt.json',MiB),'graph-verification':role('graph/verification.json',MiB),
 edges:role('graph/edges.bin',GiB),'node-scores':role('graph/node-scores.bin',128*MiB),trajectories:role('graph/trajectories.bin',128*MiB),
 'office-moves':role('graph/office-moves.bin',32*MiB),membership:role('graph/membership.bin',128*MiB),revolving:role('graph/revolving.bin',32*MiB),
 policy:role('graph/policy.bin',32*MiB),groups:role('graph/groups.bin',32*MiB),review:role('graph/review.bin',128*MiB),
 spine:role('graph/spine.bin',128*MiB),'office-index':role('graph/office-index.bin',32*MiB)
});
const PAYROLL=Object.freeze({config:role('payroll/config.json',65536),evidence:role('payroll/evidence.bin',128*MiB),
 'spine-receipt':role('payroll/spine-receipt.json',MiB),'hill-spans':role('payroll/hill-spans.bin',256*MiB),
 'house-observations':role('payroll/house-observations.bin',512*MiB),'senate-employment':role('payroll/senate-employment.bin',128*MiB),'senate-committee':role('payroll/senate-committee.bin',128*MiB)});
const FORECAST=Object.freeze({selection:role('models/selection.json',4096),'giving-pointer':role('models/giving-models-current.json',4096),'pac-pointer':role('models/pac-giving-current.json',4096),
 'giving-model':role('models/giving-model.json',16*MiB),'pac-model':role('models/pac-model.json',16*MiB),anchors:role('anchors/snapshot.json',16*MiB),'anchor-receipt':role('anchors/receipt.json',MiB),
 'workbook-commercial-banks':role('reports/commercial-banks.xlsx',512*MiB),'workbook-credit-unions':role('reports/credit-unions.xlsx',512*MiB),
 'workbook-property-casualty':role('reports/property-casualty.xlsx',512*MiB),'workbook-telecom':role('reports/telecom.xlsx',512*MiB),'workbook-community-banks':role('reports/community-banks.xlsx',512*MiB)});
const ROLE_MAPS=Object.freeze({'melange.staffer-graph-core.v1':GRAPH,'melange.payroll-identity-core.v1':PAYROLL,'mentat.aggregate-forecast-core.v1':FORECAST});
function exact(value,keys){return value&&typeof value==='object'&&!Array.isArray(value)&&Object.keys(value).sort().join('|')===[...keys].sort().join('|');}
function createModuleDataRegistry({appId,sourceRoot,probe}){
 if(!Object.hasOwn(CORE_KINDS,appId)||typeof sourceRoot!=='string'||!path.isAbsolute(sourceRoot)||typeof probe!=='function')throw new Error('Compiled module validator is unavailable');
 const registry={};
 for(const kind of CORE_KINDS[appId]){
  const roles=ROLE_MAPS[kind],maxTotalBytes=Object.values(roles).reduce((n,r)=>n+r.maxBytes,0);
  function validateMetadata(dataset){
   if(!dataset||dataset.kind!==kind||dataset.adapterVersion!==1||!Array.isArray(dataset.objects)||dataset.objects.length!==Object.keys(roles).length||!exact(dataset.counts,['files'])||dataset.counts.files!==dataset.objects.length)return false;
   const seen=new Set();let total=0;
   for(const object of dataset.objects){if(!object||!Object.hasOwn(roles,object.role)||seen.has(object.role)||!Number.isSafeInteger(object.bytes)||object.bytes<=0||object.bytes>roles[object.role].maxBytes||typeof object.sha256!=='string'||!/^[a-f0-9]{64}$/.test(object.sha256))return false;seen.add(object.role);total+=object.bytes;}
   return total<=maxTotalBytes;
  }
  registry[kind]=Object.freeze({appId,version:1,roles,maxTotalBytes,validateMetadata,
   async validateSnapshot({dataset,root,files,signal}){
    if(signal?.aborted)throw new Error('Module data verification canceled');
    if(!validateMetadata(dataset)||typeof root!=='string'||!path.isAbsolute(root)||!exact(files,Object.keys(roles)))throw new Error('Module data snapshot is incomplete');
    for(const [name,spec] of Object.entries(roles))if(typeof files[name]!=='string'||path.resolve(files[name])!==path.resolve(root,...spec.path.split('/')))throw new Error('Module data role escaped its compiled location');
    const result=await probe({appId,kind,sourceRoot,snapshotRoot:root,files,objects:dataset.objects},{signal});
    if(signal?.aborted)throw new Error('Module data verification canceled');
    if(!exact(result,['schemaVersion','validated','appId','kind','coverage'])||result.schemaVersion!==1||result.validated!==true||result.appId!==appId||result.kind!==kind||!exact(result.coverage,['completeKind','fullApplication'])||result.coverage.completeKind!==true||result.coverage.fullApplication!==false)throw new Error('Compiled module reader rejected this snapshot');
    return true;
   }});
 }
 return Object.freeze(registry);
}
module.exports={CORE_KINDS,ROLE_MAPS,createModuleDataRegistry};
