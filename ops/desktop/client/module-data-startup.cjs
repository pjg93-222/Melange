'use strict';
// Native orchestration only. Production has neither a complete application
// contract nor a supported Runtime installer yet. Downloaded metadata and saved
// settings cannot fill either gate; component probes remain fullApplication:false.
const crypto=require('node:crypto');
const {canonical}=require('./access-client.cjs');
const {authorized,checkedRegistry}=require('./github-module-protocol.cjs');
const {GitHubModuleController,sanitizeModuleStatus}=require('./github-module-controller.cjs');
const {ModuleDataTransition}=require('./module-data-transition.cjs');
const {refuseModuleDataSettings}=require('./runtime.cjs');
const APPLICATION_CONTRACTS=Object.freeze({});
function compiledApplicationContract(appId){return Object.hasOwn(APPLICATION_CONTRACTS,appId)?APPLICATION_CONTRACTS[appId]:null;}
function failure(){const error=new Error('Module data activation is unavailable.');error.code=error.reason='transition';return error;}
function fingerprint(value){try{return crypto.createHash('sha256').update(canonical(value)).digest('hex');}catch{throw failure();}}
function freeze(value){if(value&&typeof value==='object'&&!Object.isFrozen(value)){for(const child of Object.values(value))freeze(child);Object.freeze(value);}return value;}
function names(value){return Array.isArray(value)&&value.length>0&&value.every(name=>typeof name==='string'&&/^[a-z0-9][a-z0-9._-]{0,127}$/.test(name))&&new Set(value).size===value.length;}
function checkedContract(appId,contract){
 if(contract===null)return null;
 if(!contract||Object.keys(contract).sort().join('|')!=='appId|contractId|privateBoundaries|programFingerprint|publicReaders|registry|requiredKinds|schemaVersion'||
    contract.schemaVersion!==1||contract.appId!==appId||typeof contract.contractId!=='string'||!/^[a-z0-9][a-z0-9._-]{0,127}$/.test(contract.contractId)||
    typeof contract.programFingerprint!=='string'||!/^[a-f0-9]{64}$/.test(contract.programFingerprint)||
    !names(contract.requiredKinds)||!names(contract.publicReaders)||!names(contract.privateBoundaries))throw failure();
 try{checkedRegistry(appId,contract.registry,contract.requiredKinds);}catch{throw failure();}
 return freeze(contract);
}
function moduleHealthBinding(candidate,contract){
 const source=candidate?.effectiveConfiguration?.ownerGitHubModuleData;
 if(!source||source.appId!==contract.appId||source.manifestSha256!==candidate.manifestSha256||source.pointerDigest!==candidate.pointerDigest)throw failure();
 return Object.freeze({contractId:contract.contractId,programFingerprint:contract.programFingerprint,
  sourceDigest:candidate.manifestSha256,sourceFingerprint:fingerprint(source)});
}

class ModuleDataStartup{
 constructor({appId,getSelected,getGeneration,getRuntime,authorize,createProvider,canStage=()=>false,keepAwake,onStatus=()=>{},
              contract=compiledApplicationContract(appId),boundary=null,...controllerOptions}){
  if([getSelected,getGeneration,getRuntime,authorize,createProvider,canStage,onStatus].some(value=>typeof value!=='function'))throw failure();
  this.appId=appId;this.getRuntime=getRuntime;this.getSelected=getSelected;this.onStatus=onStatus;this.stageEligible=canStage;this.contract=checkedContract(appId,contract);
  this.closed=false;this.liveLease=null;
  // The native boundary must independently support the exact compiled source
  // closure. A contract flag or ordinary HTTP health cannot grant activation.
  this.supported=Boolean(this.contract&&boundary&&boundary.programFingerprint===this.contract.programFingerprint&&
   typeof boundary.supportsContract==='function'&&boundary.supportsContract(this.contract)===true&&
   typeof boundary.start==='function'&&typeof boundary.verifyHealth==='function');
  this.boundary=this.supported?Object.freeze({programFingerprint:boundary.programFingerprint,start:boundary.start.bind(boundary),verifyHealth:boundary.verifyHealth.bind(boundary)}):null;
  this.transition=new ModuleDataTransition({getSelected,getGeneration,getRuntime});
  this.controller=new GitHubModuleController({...controllerOptions,appId,getSelected,authorize,keepAwake,onStatus,
   createProvider:()=>this.supported?createProvider(this.contract):null,
   canStage:()=>this.canRefresh(),
   canCommit:candidate=>Boolean(this.supported&&this.liveLease?.canCommit(candidate))});
 }
 canRefresh(){try{return !this.closed&&this.supported&&!this.transition.busy&&!this.controller?.invalidating&&this.stageEligible()===true;}catch{return false;}}
 unsupported(){return sanitizeModuleStatus(this.appId,{phase:'unsupported',cached:false});}
 info(){return this.supported?this.controller.info():Promise.resolve(this.unsupported());}
 stage(options){return this.supported?this.controller.stage(options):Promise.resolve(this.unsupported());}
 async start(configuration,approval){
  refuseModuleDataSettings(configuration);
  const runtime=this.getRuntime();
  if(this.closed||this.transition.busy)throw failure();
  if(runtime.child||!this.supported||!authorized(this.appId,configuration,approval))return runtime.start(configuration);
  return this.transition.run(async lease=>{
   let ownedChild=null;this.liveLease=lease;
   try{
    if(fingerprint(configuration)!==fingerprint(lease.originalSelected))throw failure();
    const candidate=await this.controller.prepare({signal:lease.signal});lease.assertCurrent();
    if(!candidate)throw failure();lease.bindCandidate(candidate);
    const expected=moduleHealthBinding(candidate,this.contract);
    const binding=await this.boundary.start({runtime,configuration,candidate,lease,contract:this.contract,
     claimChild:child=>{lease.assertCurrent();if(ownedChild||!child||runtime.child!==child)throw failure();ownedChild=child;}});
    lease.assertCurrent();
    if(!binding||binding.child!==ownedChild||!ownedChild||runtime.child!==ownedChild||binding.origin!==runtime.origin||
       Object.entries(expected).some(([key,value])=>binding[key]!==value))throw failure();
    const origin=new URL(binding.origin);if(origin.protocol!=='http:'||origin.hostname!=='127.0.0.1'||!origin.port||origin.origin!==binding.origin||origin.pathname!=='/'||origin.search||origin.hash)throw failure();
    if(await this.boundary.verifyHealth({runtime,candidate,lease,contract:this.contract,binding:expected})!==true)throw failure();
    lease.assertCurrent();if(runtime.child!==ownedChild||runtime.origin!==binding.origin)throw failure();
    lease.markHealthy(candidate);
    await lease.commit(candidate,()=>this.controller.commitActive(candidate,{signal:lease.signal}));lease.assertCurrent();
    return binding.origin;
   }catch(error){
    // Only the child claimed by this cold lease is ours to stop. Wait for any
    // provider operation before teardown; an unrelated open backend is retained.
    await this.controller.drain();
    if(ownedChild&&runtime.child===ownedChild)await runtime.stop().catch(()=>{});
    throw error?.code?error:failure();
   }finally{if(this.liveLease===lease)this.liveLease=null;}
  });
 }
 invalidate(reason='authorization'){
  const startup=this.transition.invalidate(reason),staging=this.controller.invalidate();
  return Promise.all([startup,staging]).then(()=>Object.freeze({drained:true}));
 }
 shutdown(){
  this.closed=true;
  const startup=this.transition.shutdown(),staging=this.controller.shutdown();
  return Promise.all([startup,staging]).then(()=>Object.freeze({drained:true}));
 }
}
module.exports={ModuleDataStartup,compiledApplicationContract,moduleHealthBinding};
