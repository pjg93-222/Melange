'use strict';
// One cold backend, two independently authenticated data channels. Journal
// activation writes are sequential, never described or treated as atomic.
const crypto=require('node:crypto');
const {canonical}=require('./access-client.cjs');
const {authorized}=require('./github-module-protocol.cjs');
const {GitHubModuleController,sanitizeModuleStatus}=require('./github-module-controller.cjs');
const {ModuleDataTransition}=require('./module-data-transition.cjs');
const {checkedContract,moduleHealthBinding}=require('./module-data-startup.cjs');
const {refuseModuleDataSettings}=require('./runtime.cjs');
const {dataStartupFailure,programFailure,isDataStartupFailure}=require('./startup-failure.cjs');
function failure(){const error=new Error('Workspace data activation is unavailable.');error.code=error.reason='transition';return error;}
function digest(value){return crypto.createHash('sha256').update(canonical(value)).digest('hex');}
function freeze(value){if(value&&typeof value==='object'&&!Object.isFrozen(value)){for(const child of Object.values(value))freeze(child);Object.freeze(value);}return value;}
function workspaceHealthBinding(candidate,contract){
 const source=candidate?.effectiveConfiguration?.ownerGitHubWorkspaceData;
 if(!source||source.appId!==contract.appId||source.manifestSha256!==candidate.manifestSha256||source.pointerDigest!==candidate.pointerDigest)throw failure();
 return Object.freeze({contractId:contract.contractId,programFingerprint:contract.programFingerprint,sourceDigest:source.manifestSha256,sourceFingerprint:digest(source)});
}
const STATUS_MESSAGES=Object.freeze({checking:'Checking GitHub for reviewed workspace data.',downloading:'Downloading workspace data to a local cache.',
 verifying:'Verifying cached workspace data.',ready:'Verified workspace data is cached locally.',offline:'Using previously activated and verified workspace data while GitHub is unavailable.',
 'update-ready':'A verified workspace data update is staged for the next startup.',error:'The workspace data check could not be completed. Existing files were preserved.',unsupported:'Workspace data is unavailable for this component.'});
class WorkspaceDataStartup{
 constructor({appId,getSelected,getGeneration,getRuntime,authorize,createPublicProvider,createWorkspaceProvider,publicContract,workspaceContract,boundary,
              canStage=()=>false,keepAwake,onStatus=()=>{},requireInstalledContract=true,...controllerOptions}){
  if([getSelected,getGeneration,getRuntime,authorize,createPublicProvider,createWorkspaceProvider,canStage,onStatus].some(value=>typeof value!=='function'))throw failure();
  this.appId=appId;this.getRuntime=getRuntime;this.stageEligible=canStage;this.publicContract=checkedContract(appId,publicContract);this.workspaceContract=checkedContract(appId,workspaceContract,'workspace-v1');
  this.closed=false;this.liveLease=null;this.pair=null;this.requireInstalledContract=requireInstalledContract;
  try{this.supported=Boolean(this.publicContract&&this.workspaceContract&&boundary&&boundary.programFingerprint===this.publicContract.programFingerprint&&
   boundary.workspaceProgramFingerprint===this.workspaceContract.programFingerprint&&typeof boundary.supportsContracts==='function'&&
   boundary.supportsContracts(this.publicContract,this.workspaceContract)===true&&typeof boundary.start==='function'&&typeof boundary.verifyHealth==='function');}catch{this.supported=false;}
  this.boundary=this.supported?Object.freeze({supportsContracts:boundary.supportsContracts.bind(boundary),start:boundary.start.bind(boundary),verifyHealth:boundary.verifyHealth.bind(boundary)}):null;
  this.transition=new ModuleDataTransition({getSelected,getGeneration,getRuntime});
  const options={...controllerOptions,appId,getSelected,authorize,keepAwake,canStage:()=>this.canRefresh()};
  const canCommit=(candidate,field)=>Boolean(this.supported&&this.pair?.[field]===candidate&&this.liveLease?.canCommit(this.pair));
  this.controller=new GitHubModuleController({...options,onStatus,createProvider:()=>this.supported?createPublicProvider(this.publicContract):null,canCommit:candidate=>canCommit(candidate,'publicCandidate')});
  this.workspaceController=new GitHubModuleController({...options,onStatus:state=>onStatus(Object.freeze({...state,message:STATUS_MESSAGES[state.phase]||STATUS_MESSAGES.error})),createProvider:()=>this.supported?createWorkspaceProvider(this.workspaceContract):null,canCommit:candidate=>canCommit(candidate,'workspaceCandidate')});
 }
 canRefresh(){try{return !this.closed&&this.supported&&!this.transition.busy&&!this.controller.invalidating&&!this.workspaceController.invalidating&&this.stageEligible()===true;}catch{return false;}}
 currentProgram(){return this.supported&&this.boundary.supportsContracts(this.publicContract,this.workspaceContract)===true;}
 unsupported(){return sanitizeModuleStatus(this.appId,{phase:'unsupported',cached:false});}
 info(){return this.supported?this.controller.info():Promise.resolve(this.unsupported());}
 workspaceInfo(){return this.supported?this.workspaceController.info():Promise.resolve(this.unsupported());}
 async stage(options){
  if(!this.supported)return this.unsupported();if(!this.currentProgram())throw programFailure();
  await this.workspaceController.stage(options);return this.controller.stage(options);
 }
 async start(configuration,approval){
  refuseModuleDataSettings(configuration);const runtime=this.getRuntime();
  if(this.closed||this.transition.busy)throw failure();
  if(this.requireInstalledContract&&!this.supported)throw programFailure();
  if(runtime.child||!this.supported||!authorized(this.appId,configuration,approval))return runtime.start(configuration);
  if(!this.currentProgram())throw programFailure();
  return this.transition.run(async lease=>{
   let ownedChild=null,phase='preparing';this.liveLease=lease;
   const dataOutcome=error=>{
    lease.assertCurrent();if(!this.currentProgram())throw programFailure();return dataStartupFailure(error)||error;
   };
   try{
    if(digest(configuration)!==digest(lease.originalSelected))throw failure();
    // Resolve the new channel first: repeated offline retries do not repeatedly
    // walk the unchanged large legacy public snapshot before contacting GitHub.
    let workspaceCandidate,publicCandidate;
    try{workspaceCandidate=await this.workspaceController.prepare({signal:lease.signal});lease.assertCurrent();publicCandidate=await this.controller.prepare({signal:lease.signal});lease.assertCurrent();}
    catch(error){throw dataOutcome(error);}
    if(!publicCandidate||!workspaceCandidate){const error=new Error('Existing-owner access is no longer available.');error.code=error.reason='authorization';throw error;}
    const pair=freeze({schemaVersion:1,appId:this.appId,publicCandidate,workspaceCandidate,effectiveConfiguration:{...structuredClone(configuration),
      ownerGitHubModuleData:structuredClone(publicCandidate.effectiveConfiguration.ownerGitHubModuleData),ownerGitHubWorkspaceData:structuredClone(workspaceCandidate.effectiveConfiguration.ownerGitHubWorkspaceData)}});
    this.pair=pair;lease.bindCandidate(pair);
    const expected=Object.freeze({moduleData:moduleHealthBinding(publicCandidate,this.publicContract),workspaceData:workspaceHealthBinding(workspaceCandidate,this.workspaceContract)});
    phase='starting';
    const binding=await this.boundary.start({runtime,configuration,publicCandidate,workspaceCandidate,lease,
     claimChild:child=>{if(ownedChild||!child||runtime.child!==child)throw failure();ownedChild=child;lease.assertCurrent();}});
    lease.assertCurrent();if(!ownedChild||runtime.child!==ownedChild||binding?.child!==ownedChild||binding.origin!==runtime.origin||
      digest(binding.moduleData)!==digest(expected.moduleData)||digest(binding.workspaceData)!==digest(expected.workspaceData))throw failure();
    const origin=new URL(binding.origin);if(origin.protocol!=='http:'||origin.hostname!=='127.0.0.1'||!origin.port||origin.origin!==binding.origin||origin.pathname!=='/'||origin.search||origin.hash)throw failure();
    phase='health';if(await this.boundary.verifyHealth({runtime,lease,binding:expected})!==true)throw failure();
    lease.assertCurrent();if(runtime.child!==ownedChild||runtime.origin!==binding.origin)throw failure();lease.markHealthy(pair);
    phase='committing';await lease.commit(pair,async()=>{
     try{await this.controller.commitActive(publicCandidate,{signal:lease.signal});lease.assertCurrent();await this.workspaceController.commitActive(workspaceCandidate,{signal:lease.signal});}
     catch(error){throw dataOutcome(error);}
    });lease.assertCurrent();return binding.origin;
   }catch(error){
    await Promise.all([this.controller.drain(),this.workspaceController.drain()]);
    // Only pre-child external-data errors, or typed native intake/commit data
    // errors, may be blocked without blaming a binary. Unknown health stays fatal.
    let problem=error;
    if(!ownedChild&&phase==='starting')problem=dataOutcome(error);
    if(ownedChild&&runtime.child===ownedChild)await runtime.stop().catch(()=>{});
    throw isDataStartupFailure(problem)||problem?.code?problem:failure();
   }finally{if(this.liveLease===lease){this.liveLease=null;this.pair=null;}}
  });
 }
 invalidate(reason='authorization'){return Promise.all([this.transition.invalidate(reason),this.controller.invalidate(),this.workspaceController.invalidate()]).then(()=>Object.freeze({drained:true}));}
 shutdown(){this.closed=true;return Promise.all([this.transition.shutdown(),this.controller.shutdown(),this.workspaceController.shutdown()]).then(()=>Object.freeze({drained:true}));}
}
module.exports={WorkspaceDataStartup,workspaceHealthBinding};
