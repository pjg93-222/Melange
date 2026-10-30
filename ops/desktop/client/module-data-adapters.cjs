'use strict';
// Complete, narrow immutable-data kinds. Old mixed cores are component-only;
// passive public contracts explicitly select the separate reviewed public map.
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
const PUBLIC_KINDS=Object.freeze({melange:Object.freeze(['melange.official-payroll-observations.v1']),mentat:Object.freeze(['mentat.public-fec-tables.v1'])});
const PAGED_KINDS=Object.freeze({melange:Object.freeze(['melange.official-payroll-pages.v1'])});
const PAGED_ROLES=Object.freeze({'melange.official-payroll-pages.v1':Object.freeze({index:role('public-data/index.json',2*MiB),receipt:role('public-data/receipt.json',MiB)})});
const FEC=Object.freeze(Object.fromEntries([...['2022','2024','2026'].flatMap(cycle=>['cm','cn','ccl','pas2'].map(table=>['mentat.fec.'+table+'.'+cycle,role('fec/'+cycle+'/'+table+'.psv',160*MiB)])),['mentat.fec.provenance',role('fec/provenance.json',65536)]]));
const PUBLIC_ROLES=Object.freeze({'melange.official-payroll-observations.v1':Object.freeze({observations:role('public-data/observations.ndjson',8*GiB),receipt:role('public-data/receipt.json',MiB)}),'mentat.public-fec-tables.v1':FEC});
const ROLE_MAPS=Object.freeze({'melange.staffer-graph-core.v1':GRAPH,'melange.payroll-identity-core.v1':PAYROLL,'mentat.aggregate-forecast-core.v1':FORECAST});
function exact(value,keys){return value&&typeof value==='object'&&!Array.isArray(value)&&Object.keys(value).sort().join('|')===[...keys].sort().join('|');}
function registryFor({appId,sourceRoot,probe,prepareProbe},kinds,maps){
 if(!Object.hasOwn(kinds,appId)||typeof sourceRoot!=='string'||!path.isAbsolute(sourceRoot)||typeof probe!=='function'||prepareProbe!==undefined&&typeof prepareProbe!=='function')throw new Error('Compiled module validator is unavailable');
 const registry={};
 for(const kind of kinds[appId]){
  const roles=maps[kind],maxTotalBytes=kind==='mentat.public-fec-tables.v1'?512*MiB:Object.values(roles).reduce((n,r)=>n+r.maxBytes,0);
  function validateMetadata(dataset){
   if(!dataset||dataset.kind!==kind||dataset.adapterVersion!==1||!Array.isArray(dataset.objects)||dataset.objects.length!==Object.keys(roles).length||!exact(dataset.counts,['files'])||dataset.counts.files!==dataset.objects.length)return false;
   const seen=new Set();let total=0;
   for(const object of dataset.objects){if(!object||!Object.hasOwn(roles,object.role)||seen.has(object.role)||!Number.isSafeInteger(object.bytes)||object.bytes<=0||object.bytes>roles[object.role].maxBytes||typeof object.sha256!=='string'||!/^[a-f0-9]{64}$/.test(object.sha256))return false;seen.add(object.role);total+=object.bytes;}
   return total<=maxTotalBytes;
  }
  async function validateSnapshot({dataset,root,files,signal},read){
    if(signal?.aborted)throw new Error('Module data verification canceled');
    if(!validateMetadata(dataset)||typeof root!=='string'||!path.isAbsolute(root)||!exact(files,Object.keys(roles)))throw new Error('Module data snapshot is incomplete');
    for(const [name,spec] of Object.entries(roles))if(typeof files[name]!=='string'||path.resolve(files[name])!==path.resolve(root,...spec.path.split('/')))throw new Error('Module data role escaped its compiled location');
    const result=await read({appId,kind,sourceRoot,snapshotRoot:root,files,objects:dataset.objects},{signal});
    if(signal?.aborted)throw new Error('Module data verification canceled');
    if(!exact(result,['schemaVersion','validated','appId','kind','coverage'])||result.schemaVersion!==1||result.validated!==true||result.appId!==appId||result.kind!==kind||!exact(result.coverage,['completeKind','fullApplication'])||result.coverage.completeKind!==true||result.coverage.fullApplication!==false)throw new Error('Compiled module reader rejected this snapshot');
    return true;
  }
  const adapter={appId,version:1,roles,maxTotalBytes,validateMetadata,validateSnapshot:input=>validateSnapshot(input,probe)};
  if(prepareProbe)adapter.prepareSnapshot=async({signal}={})=>{
   if(signal?.aborted)throw new Error('Module data verification canceled');
   // Only the native command/options reach prewarm. Dataset paths and bytes are
   // passed to run after the caller's ordinary role hashes have all succeeded.
   const runner=await prepareProbe({signal});
   if(!runner||typeof runner.run!=='function'||typeof runner.cancel!=='function'){
    if(typeof runner?.cancel==='function')await runner.cancel();throw new Error('Compiled module validator is unavailable');
   }
   let used=false,closed=false,drain;
   return Object.freeze({
    validateSnapshot(input){
     if(used||closed||input.signal!==signal)throw new Error('Module data verification session is unavailable');used=true;
     return validateSnapshot(input,request=>runner.run(request));
    },
    cancel(){closed=true;return drain??=Promise.resolve().then(()=>runner.cancel());}
   });
  };
  registry[kind]=Object.freeze(adapter);
 }
 return Object.freeze(registry);
}
function createModuleDataRegistry(options){return registryFor(options,CORE_KINDS,ROLE_MAPS);}
function createPublicModuleDataRegistry(options){return registryFor(options,PUBLIC_KINDS,PUBLIC_ROLES);}
function createPagedModuleDataRegistry(options){return registryFor(options,PAGED_KINDS,PAGED_ROLES);}
function createWorkspaceModuleDataRegistry(options){const workspace=require('./workspace-data-contract.cjs');return registryFor(options,workspace.WORKSPACE_KINDS,workspace.roleMaps());}
async function withSnapshotValidation(adapter,options,work){
 if(adapter.prepareSnapshot!==undefined&&typeof adapter.prepareSnapshot!=='function')throw new Error('Compiled module validator is unavailable');
 const session=adapter.prepareSnapshot?await adapter.prepareSnapshot(options):null;
 try{
  if(session&&(!exact(session,['validateSnapshot','cancel'])||typeof session.validateSnapshot!=='function'||typeof session.cancel!=='function'))throw new Error('Compiled module validator is unavailable');
  if(adapter.prepareSnapshot&&!session)throw new Error('Compiled module validator is unavailable');
  return await work((session||adapter).validateSnapshot.bind(session||adapter));
 }finally{if(session&&typeof session.cancel==='function')await session.cancel();}
}
module.exports={CORE_KINDS,ROLE_MAPS,PUBLIC_KINDS,PUBLIC_ROLES,PAGED_KINDS,PAGED_ROLES,createModuleDataRegistry,createPublicModuleDataRegistry,createPagedModuleDataRegistry,createWorkspaceModuleDataRegistry,withSnapshotValidation};
