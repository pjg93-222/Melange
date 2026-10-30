'use strict';
// Native orchestration only. Compiled application contracts require the exact
// installed program closure; component probes remain fullApplication:false.
const crypto=require('node:crypto');
const path=require('node:path');
const {canonical}=require('./access-client.cjs');
const {authorized,checkedRegistry}=require('./github-module-protocol.cjs');
const {GitHubModuleController,sanitizeModuleStatus}=require('./github-module-controller.cjs');
const {ModuleDataTransition}=require('./module-data-transition.cjs');
const {refuseModuleDataSettings}=require('./runtime.cjs');
const {programTable,programFingerprint,verifyProgram,withVerifiedProgramConstruction}=require('./module-data-runtime-boundary.cjs');
const {APPLICATION_SPECS,WORKSPACE_APPLICATION_SPECS}=require('./module-application-inventory.cjs');
const {createPublicModuleDataRegistry,createPagedModuleDataRegistry,createWorkspaceModuleDataRegistry,PUBLIC_KINDS,PAGED_KINDS}=require('./module-data-adapters.cjs');
const {WORKSPACE_KINDS}=require('./workspace-data-contract.cjs');
const {backendCommand}=require('./backend-command.cjs');
const {desktopProbe,prepareDesktopProbe}=require('./desktop-probe.cjs');
const {dataStartupFailure,programFailure}=require('./startup-failure.cjs');
function applicationContract(appId,context){
 if(!['melange','mentat'].includes(appId)||!context?.runtime||typeof context.resources!=='string'||!path.isAbsolute(context.resources))return null;
 try{
  const workspace=context.workspaceContract===true,paged=!workspace&&appId==='melange'&&context.publicDataMode==='paged-v1';
  const base=workspace?WORKSPACE_APPLICATION_SPECS?.[appId]:APPLICATION_SPECS[appId],spec=paged?{...base,contractId:'melange.public-data.pages.v1',requiredKinds:PAGED_KINDS.melange}:base;
  if(!spec||spec.contractId!==(workspace?appId+'.workspace.v1':paged?'melange.public-data.pages.v1':appId+'.public-data.v1')||spec.requiredKinds.join('|')!==(workspace?WORKSPACE_KINDS[appId]:paged?PAGED_KINDS[appId]:PUBLIC_KINDS[appId]).join('|')||
     spec.startupTimeoutMs!==(appId==='melange'?600000:300000))return null;
  const command=backendCommand(context.resources,appId),sourceRoot=path.join(command.runtime,'sources'),bootstrapRoot=path.join(command.runtime,'bootstrap');
  const current=()=>{try{const roots=verifyProgram(context.runtime,spec);if(roots.source!==sourceRoot||roots.bootstrap!==bootstrapRoot)throw failure();}catch{throw programFailure();}};
  // Native read-only validation dispatches by dataset kind for both channels.
  const probeMode='--desktop-github-module-check';
  const registry=(workspace?createWorkspaceModuleDataRegistry:paged?createPagedModuleDataRegistry:createPublicModuleDataRegistry)({appId,sourceRoot,prepareProbe:({signal}={})=>{
   if(signal?.aborted)throw failure();
   const reader=prepareDesktopProbe(command,probeMode,{signal,timeout:spec.startupTimeoutMs,onDiagnostic:context.onProbeDiagnostic,beforeSpawn:current});
   return {async run(request){if(signal?.aborted)throw failure();current();let result;try{result=await reader.run(request);}catch(error){
    if(!signal?.aborted&&reader.diagnostics().some(value=>value.phase==='prewarm'&&['spawn-failed','process-error','early-exit','input-error'].includes(value.reason)))throw programFailure();
    throw error;
   }if(signal?.aborted)throw failure();current();return result;},cancel:()=>reader.cancel()};
  },probe:async(request,{signal}={})=>{
   if(signal?.aborted)throw failure();current();
   const result=await desktopProbe(command,probeMode,request,{signal,timeout:spec.startupTimeoutMs});
   if(signal?.aborted)throw failure();current();return result;
  }});
  return {contract:checkedContract(appId,{...spec,registry},workspace?'workspace-v1':'public-v1'),roots:Object.freeze({source:sourceRoot,bootstrap:bootstrapRoot})};
 }catch{return null;}
}
function withCompiledApplicationContract(appId,context,construct){
 if(typeof construct!=='function'||require('node:util').types.isAsyncFunction(construct))throw failure();
 const application=applicationContract(appId,context);
 if(!application)return construct(null);
 const {contract,roots}=application;
 return withVerifiedProgramConstruction(context.runtime,contract,proof=>construct(proof?contract:null,proof||undefined),roots);
}
function compiledApplicationContract(appId,context){return withCompiledApplicationContract(appId,context,contract=>contract);}
function withCompiledWorkspaceApplicationContract(appId,context,construct){return withCompiledApplicationContract(appId,{...context,workspaceContract:true},construct);}
function failure(){const error=new Error('Module data activation is unavailable.');error.code=error.reason='transition';return error;}
function fingerprint(value){try{return crypto.createHash('sha256').update(canonical(value)).digest('hex');}catch{throw failure();}}
function freeze(value){if(value&&typeof value==='object'&&!Object.isFrozen(value)){for(const child of Object.values(value))freeze(child);Object.freeze(value);}return value;}
function names(value){return Array.isArray(value)&&value.length>0&&value.every(name=>typeof name==='string'&&/^[a-z0-9][a-z0-9._-]{0,127}$/.test(name))&&new Set(value).size===value.length;}
function checkedContract(appId,contract,channel='public-v1'){
 if(contract===null)return null;
 if(!contract||Object.keys(contract).sort().join('|')!=='appId|contractId|privateBoundaries|programFiles|programFingerprint|publicReaders|registry|requiredKinds|schemaVersion|startupTimeoutMs'||
    contract.schemaVersion!==1||contract.appId!==appId||typeof contract.contractId!=='string'||!/^[a-z0-9][a-z0-9._-]{0,127}$/.test(contract.contractId)||
    typeof contract.programFingerprint!=='string'||!/^[a-f0-9]{64}$/.test(contract.programFingerprint)||
    !names(contract.requiredKinds)||!names(contract.publicReaders)||!names(contract.privateBoundaries)||
    !Number.isSafeInteger(contract.startupTimeoutMs)||contract.startupTimeoutMs<1000||contract.startupTimeoutMs>600000)throw failure();
 try{programTable(contract.programFiles);if(programFingerprint(contract.programFiles)!==contract.programFingerprint)throw failure();checkedRegistry(appId,contract.registry,contract.requiredKinds,channel);}catch{throw failure();}
 return freeze(contract);
}
function moduleHealthBinding(candidate,contract){
 const source=candidate?.effectiveConfiguration?.ownerGitHubModuleData;
 if(!source||source.appId!==contract.appId||source.manifestSha256!==candidate.manifestSha256||source.pointerDigest!==candidate.pointerDigest)throw failure();
 return Object.freeze({contractId:contract.contractId,programFingerprint:contract.programFingerprint,
  sourceDigest:candidate.manifestSha256,sourceFingerprint:fingerprint(source)});
}

class ModuleDataStartup{
 constructor({appId,getSelected,getGeneration,getRuntime,authorize,createProvider,canStage=()=>false,keepAwake,onStatus=()=>{},requireInstalledContract=false,
              contract=compiledApplicationContract(appId),boundary=null,...controllerOptions}){
  if([getSelected,getGeneration,getRuntime,authorize,createProvider,canStage,onStatus].some(value=>typeof value!=='function'))throw failure();
  this.appId=appId;this.getRuntime=getRuntime;this.getSelected=getSelected;this.onStatus=onStatus;this.stageEligible=canStage;this.contract=checkedContract(appId,contract);
  if(typeof requireInstalledContract!=='boolean')throw failure();
  this.closed=false;this.liveLease=null;this.requireInstalledContract=requireInstalledContract;
  // The native boundary must independently support the exact compiled source
  // closure. A contract flag or ordinary HTTP health cannot grant activation.
  this.supported=Boolean(this.contract&&boundary&&boundary.programFingerprint===this.contract.programFingerprint&&
   typeof boundary.supportsContract==='function'&&boundary.supportsContract(this.contract)===true&&
   typeof boundary.start==='function'&&typeof boundary.verifyHealth==='function');
  this.boundary=this.supported?Object.freeze({programFingerprint:boundary.programFingerprint,supportsContract:boundary.supportsContract.bind(boundary),start:boundary.start.bind(boundary),verifyHealth:boundary.verifyHealth.bind(boundary)}):null;
  this.transition=new ModuleDataTransition({getSelected,getGeneration,getRuntime});
  this.controller=new GitHubModuleController({...controllerOptions,appId,getSelected,authorize,keepAwake,onStatus,
   createProvider:()=>this.supported?createProvider(this.contract):null,
   canStage:()=>this.canRefresh(),
   canCommit:candidate=>Boolean(this.supported&&this.liveLease?.canCommit(candidate))});
 }
 canRefresh(){try{return !this.closed&&this.supported&&!this.transition.busy&&!this.controller?.invalidating&&this.stageEligible()===true;}catch{return false;}}
 unsupported(){return sanitizeModuleStatus(this.appId,{phase:'unsupported',cached:false});}
 info(){return this.supported?this.controller.info():Promise.resolve(this.unsupported());}
 stage(options){if(this.supported&&this.boundary.supportsContract(this.contract)!==true)return Promise.reject(failure());return this.supported?this.controller.stage(options):Promise.resolve(this.unsupported());}
 async start(configuration,approval){
  refuseModuleDataSettings(configuration);
  const runtime=this.getRuntime();
  if(this.closed||this.transition.busy)throw failure();
  if(this.requireInstalledContract&&!this.supported)throw programFailure();
  if(runtime.child||!this.supported||!authorized(this.appId,configuration,approval))return runtime.start(configuration);
  if(this.boundary.supportsContract(this.contract)!==true)throw failure();
  return this.transition.run(async lease=>{
   let ownedChild=null;this.liveLease=lease;
   try{
    if(fingerprint(configuration)!==fingerprint(lease.originalSelected))throw failure();
    let candidate;
    try{candidate=await this.controller.prepare({signal:lease.signal});}
    catch(error){
     lease.assertCurrent();
     // External data cannot establish a broken binary. Recheck installed code
     // before preserving a blocked/deferred outcome; health is still ungranted.
     if(this.boundary.supportsContract(this.contract)!==true)throw programFailure();
     throw dataStartupFailure(error)||error;
    }
    lease.assertCurrent();
    if(!candidate){const error=new Error('Existing-owner access is no longer available.');error.code=error.reason='authorization';throw error;}lease.bindCandidate(candidate);
    const expected=moduleHealthBinding(candidate,this.contract);
    const binding=await this.boundary.start({runtime,configuration,candidate,lease,contract:this.contract,
     claimChild:child=>{if(ownedChild||!child||runtime.child!==child)throw failure();ownedChild=child;lease.assertCurrent();}});
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
module.exports={ModuleDataStartup,compiledApplicationContract,withCompiledApplicationContract,withCompiledWorkspaceApplicationContract,moduleHealthBinding,checkedContract};
