'use strict';
// Native-only coordination. This module cannot start/stop a backend, change
// settings, or override a renderer's normal close/unsaved-work protections.
const {canonical}=require('./access-client.cjs');
const {authorized}=require('./github-module-protocol.cjs');
const path=require('node:path');

const REPOSITORIES=Object.freeze({melange:'pjg93-222/melange',mentat:'pjg93-222/mentat'});
const PHASES=new Set(['checking','downloading','verifying','ready','offline','update-ready','error','unsupported']);
const TAG=/^module-data-\d{4}-\d{2}-\d{2}(?:-[a-z0-9][a-z0-9.-]{0,40})?$/;
const HASH=/^[a-f0-9]{64}$/;
const MAX_BYTES=32*1024**3;
const STATUS_EVENT='desktop:module-data-status';
const MESSAGES=Object.freeze({
 checking:'Checking GitHub for reviewed module data.',
 downloading:'Downloading module data to a local cache.',
 verifying:'Verifying the local module data cache.',
 ready:'Verified GitHub data is cached locally.',
 offline:'Using previously activated and verified local data while GitHub is unavailable.',
 'update-ready':'A verified update is staged for the next approved startup.',
 error:'The module data check could not be completed. Existing files were preserved.',
 unsupported:'GitHub preload is not available for this component.'
});
const MENTAT_MESSAGES=Object.freeze({
 ready:'Verified public FEC tables are cached locally. Industry reports and forecasts use separate local files.',
 offline:'Using verified cached public FEC tables while GitHub is unavailable. Industry reports and forecasts use separate local files.'
});
const ERROR_MESSAGES=Object.freeze({
 authorization:'Current existing-owner approval is required.',
 integrity:'Module data verification failed.',
 storage:'Module data storage is unavailable.',
 cancelled:'The module data operation was cancelled.',
 unreachable:'GitHub module data is unavailable.',
 timeout:'The module data check timed out.',
 rate_limited:'GitHub module data is temporarily unavailable.',
 context:'The selected workspace changed.',
 transition:'Module data activation is unavailable.'
});
function failure(code){const error=new Error(ERROR_MESSAGES[code]||ERROR_MESSAGES.integrity);error.code=error.reason=Object.hasOwn(ERROR_MESSAGES,code)?code:'integrity';return error;}
function safeFailure(error){return failure(typeof error?.reason==='string'?error.reason:typeof error?.code==='string'?error.code:'integrity');}
function appRepository(appId){if(!Object.hasOwn(REPOSITORIES,appId))throw new Error('Unsupported module data application.');return REPOSITORIES[appId];}
function timestamp(value){return typeof value==='string'&&value.length===24&&Number.isFinite(Date.parse(value))&&new Date(value).toISOString()===value;}
function freeze(value){if(value&&typeof value==='object'&&!Object.isFrozen(value)){for(const child of Object.values(value))freeze(child);Object.freeze(value);}return value;}

function sanitizeModuleStatus(appId,value,{canRefresh=false}={}){
 const repository=appRepository(appId);
 if(!value||typeof value!=='object'||Array.isArray(value)||
    (value.appId!==undefined&&value.appId!==appId)||
    (value.repository!==undefined&&(typeof value.repository!=='string'||value.repository.toLowerCase()!==repository)))return null;
 const phase=PHASES.has(value.phase)?value.phase:'error';
 const result={provider:'github',appId,repository,phase,cached:value.cached===true,canRefresh:canRefresh===true&&phase!=='unsupported',message:appId==='mentat'&&MENTAT_MESSAGES[phase]||MESSAGES[phase]};
 if(typeof value.releaseTag==='string'&&TAG.test(value.releaseTag))result.releaseTag=value.releaseTag;
 if(Number.isSafeInteger(value.catalogueSequence)&&value.catalogueSequence>0)result.catalogueSequence=value.catalogueSequence;
 for(const key of ['checkedAt','verifiedAt'])if(timestamp(value[key]))result[key]=value[key];
 for(const key of ['receivedBytes','totalBytes'])if(Number.isSafeInteger(value[key])&&value[key]>=0&&value[key]<=MAX_BYTES)result[key]=value[key];
 if(result.receivedBytes!==undefined&&result.totalBytes!==undefined&&result.receivedBytes>result.totalBytes)delete result.receivedBytes;
 if(typeof value.updateAvailable==='boolean')result.updateAvailable=value.updateAvailable;
 return Object.freeze(result);
}

class GitHubModuleController{
 constructor({appId,getSelected,createProvider,authorize,canStage=()=>false,canCommit=()=>false,
              keepAwake=()=>()=>{},onStatus=()=>{},intervalMs=5*60*1000,
              setInterval:setIntervalFn=setInterval,clearInterval:clearIntervalFn=clearInterval}){
  this.appId=appId;this.repository=appRepository(appId);
  for(const callback of [getSelected,createProvider,authorize,canStage,canCommit,keepAwake,onStatus,setIntervalFn,clearIntervalFn])if(typeof callback!=='function')throw new Error('Native module data callbacks are required.');
  if(!Number.isSafeInteger(intervalMs)||intervalMs<1000||intervalMs>24*60*60*1000)throw new Error('Invalid module data check interval.');
  Object.assign(this,{getSelected,createProvider,authorize,canStage,canCommit,keepAwake,onStatus,clearIntervalFn});
  this.provider=null;this.tail=Promise.resolve();this.busy=false;this.closed=false;this.epoch=0;this.invalidating=false;this.draining=null;
  this.cancelled=new AbortController();this.prepared=new WeakMap();this.lastStatus=null;this.statusContext=null;
  this.timer=setIntervalFn(()=>{this.stage({skipIfBusy:true}).catch(()=>{});},intervalMs);
  this.timer?.unref?.();
 }
 selected(){
  let selected;
  try{selected=structuredClone(this.getSelected());}catch{throw failure('authorization');}
  if(!selected||typeof selected!=='object'||Array.isArray(selected)||
     ['ownerGitHubData','ownerGitHubModuleData','githubModuleData','effectiveConfiguration','snapshotRoot'].some(key=>Object.hasOwn(selected,key)))throw failure('authorization');
  let fingerprint;try{fingerprint=canonical(selected);}catch{throw failure('authorization');}
  return {selected:freeze(selected),fingerprint,epoch:this.epoch};
 }
 current(context){try{return !this.closed&&!this.invalidating&&context.epoch===this.epoch&&this.selected().fingerprint===context.fingerprint;}catch{return false;}}
 guard(context,signal){if(this.closed||this.invalidating||context.epoch!==this.epoch||signal?.aborted)throw failure('cancelled');if(!this.current(context))throw failure('context');}
 async approval(context,signal){
  this.guard(context,signal);
  let approval;try{approval=await this.authorize(context.selected);}catch{this.guard(context,signal);throw failure('authorization');}
  this.guard(context,signal);
  if(!authorized(this.appId,context.selected,approval))throw failure('authorization');
  return approval;
 }
 stageAllowed(){try{return !this.closed&&!this.invalidating&&this.canStage()===true;}catch{return false;}}
 commitAllowed(candidate){try{return this.canCommit(candidate)===true;}catch{return false;}}
 status(value,context){
  if(!this.current(context))return;
  const state=sanitizeModuleStatus(this.appId,value,{canRefresh:!this.busy&&this.stageAllowed()});
  if(!state)return;
  this.lastStatus=state;this.statusContext=context.fingerprint;
  try{this.onStatus(state);}catch{/* A renderer observer cannot change the data transaction. */}
 }
 checkedCandidate(candidate){
  if(!candidate||typeof candidate!=='object'||candidate.schemaVersion!==1||candidate.appId!==this.appId||
     typeof candidate.repository!=='string'||candidate.repository.toLowerCase()!==this.repository||
     !Number.isSafeInteger(candidate.catalogueSequence)||candidate.catalogueSequence<1||!TAG.test(candidate.releaseTag)||
     !HASH.test(candidate.pointerDigest)||!HASH.test(candidate.manifestSha256)||
     typeof candidate.snapshotRoot!=='string'||!path.isAbsolute(candidate.snapshotRoot)||
     !candidate.effectiveConfiguration||typeof candidate.effectiveConfiguration!=='object'||Array.isArray(candidate.effectiveConfiguration)||
     !['ready','offline'].includes(candidate.status?.phase)||!sanitizeModuleStatus(this.appId,candidate.status)||
     (candidate.status.catalogueSequence!==undefined&&candidate.status.catalogueSequence!==candidate.catalogueSequence)||
     (candidate.status.releaseTag!==undefined&&candidate.status.releaseTag!==candidate.releaseTag))throw failure('integrity');
  try{return freeze(structuredClone(candidate));}catch{throw failure('integrity');}
 }
 enqueue(kind,options={},candidate){
  if(this.closed||this.invalidating)return Promise.reject(failure('cancelled'));
  if(kind==='stage'&&options.skipIfBusy&&this.busy)return Promise.resolve(null);
  let context;try{context=this.selected();}catch(error){return Promise.reject(safeFailure(error));}
  const result=this.tail.then(()=>this.run(kind,context,options,candidate));
  this.tail=result.catch(()=>{});return result;
 }
 async run(kind,context,options,candidate){
  const signal=options.signal?AbortSignal.any([this.cancelled.signal,options.signal]):this.cancelled.signal;
  this.guard(context,signal);
  if(this.statusContext!==context.fingerprint){this.lastStatus=null;this.statusContext=null;}
  if(kind==='stage'&&!this.stageAllowed())return null;
  this.busy=true;let release;
  try{
   try{await this.approval(context,signal);}catch(error){
    this.lastStatus=null;this.statusContext=null;
    if(error.code==='authorization'&&kind!=='commit')return null;
    throw error;
   }
   if(kind==='info'){
    return this.statusContext===context.fingerprint&&this.lastStatus?
     sanitizeModuleStatus(this.appId,this.lastStatus,{canRefresh:this.stageAllowed()}):null;
   }
   if(kind==='stage'&&!this.stageAllowed())return null;
   if(kind==='commit'){
    const prepared=this.prepared.get(candidate);
    if(!prepared||prepared.fingerprint!==context.fingerprint)throw failure('context');
    if(!this.commitAllowed(candidate))throw failure('transition');
   }
   if(!this.provider){this.provider=await this.createProvider();this.guard(context,signal);}
   if(!this.provider){this.status({phase:'unsupported',cached:false},context);return null;}
   for(const method of ['prepare','stage','commitActive'])if(typeof this.provider[method]!=='function')throw failure('integrity');
   release=this.keepAwake();this.guard(context,signal);
   let lastProgressPhase,lastProgressAt;
   const progress=value=>{
    if(signal.aborted)return;
    const phase=value?.phase,now=Date.now();
    if(lastProgressAt!==undefined&&phase===lastProgressPhase&&now>=lastProgressAt&&now-lastProgressAt<250)return;
    if(!this.current(context))return;
    lastProgressPhase=phase;lastProgressAt=now;this.status(value,context);
   };
   if(kind==='commit'){
    // The native caller holds its normal transition lease and has health-checked
    // this exact prepared backend. Provider commit rechecks owner/hash integrity.
    this.guard(context,signal);if(!this.commitAllowed(candidate))throw failure('transition');
    const beforeCommit=()=>{this.guard(context,signal);if(!this.commitAllowed(candidate))throw failure('transition');return true;};
    const committed=await this.provider.commitActive(candidate,context.selected,{signal,beforeCommit});
    this.guard(context,signal);
    const checked=this.checkedCandidate(committed);this.prepared.delete(candidate);
    this.status(checked.status,context);return checked;
   }
   this.status({phase:'checking',cached:this.lastStatus?.cached===true},context);
   const result=await this.provider[kind](context.selected,{signal,onStatus:progress});
   this.guard(context,signal);await this.approval(context,signal);
   if(kind==='stage'){
    const state=result?.status||result;
    this.status(state||{phase:'unsupported',cached:false},context);
    return this.lastStatus?sanitizeModuleStatus(this.appId,this.lastStatus,{canRefresh:this.stageAllowed()}):null;
   }
   if(result===null){this.status({phase:'unsupported',cached:false},context);return null;}
   const checked=this.checkedCandidate(result);this.prepared.set(checked,context);
   this.status(checked.status,context);return checked;
  }catch(error){
   const safe=safeFailure(error);
   if(safe.code==='authorization'||safe.code==='context'||safe.code==='cancelled'){this.lastStatus=null;this.statusContext=null;}
   else this.status({phase:'error',cached:this.lastStatus?.cached===true},context);
   throw safe;
  }finally{
   try{if(typeof release==='function')release();}catch{/* Sleep-protection cleanup cannot expose private errors. */}finally{
    this.busy=false;
    if(this.lastStatus&&this.statusContext===context.fingerprint&&this.current(context))this.status(this.lastStatus,context);
   }
  }
 }
 prepare(options){return this.enqueue('prepare',options);}
 stage(options){return this.enqueue('stage',options);}
 commitActive(candidate,options){return this.enqueue('commit',options,candidate);}
 info(){return this.enqueue('info');}
 drain(){return this.tail.then(()=>Object.freeze({drained:true}));}
 invalidate(){
  if(this.draining)return this.draining;
  this.invalidating=true;this.epoch++;this.cancelled.abort();this.prepared=new WeakMap();this.lastStatus=null;this.statusContext=null;
  this.draining=this.drain().then(value=>{if(!this.closed){this.cancelled=new AbortController();this.invalidating=false;this.draining=null;}return value;});
  return this.draining;
 }
 shutdown(){if(this.closed)return this.draining;this.closed=true;this.clearIntervalFn(this.timer);return this.invalidate();}
}

function registerModuleDataIPC(ipc,{appId,runtimeOnly,info,refresh,canRefresh}){
 appRepository(appId);
 const trusted=event=>{try{runtimeOnly(event);}catch{throw new Error('Untrusted application request.');}};
 ipc.handle('desktop:module-data',async event=>{
  trusted(event);try{const state=await info();return state?sanitizeModuleStatus(appId,state,{canRefresh:state.canRefresh===true}):null;}
  catch{throw new Error('Module data status is unavailable.');}
 });
 ipc.handle('desktop:module-data-refresh',async event=>{
  trusted(event);
  let available=false;try{available=canRefresh()===true;}catch{/* Native eligibility details stay private. */}
  if(!available)throw new Error('Module data check is unavailable.');
  try{const state=await refresh();return state?sanitizeModuleStatus(appId,state,{canRefresh:state.canRefresh===true}):null;}
  catch{throw new Error('Module data check could not be completed.');}
 });
}
module.exports={GitHubModuleController,registerModuleDataIPC,sanitizeModuleStatus,REPOSITORIES,STATUS_EVENT};
