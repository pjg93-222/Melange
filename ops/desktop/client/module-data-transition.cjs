'use strict';
// A native startup lease, not a backend controller or a hot-update mechanism.
const {canonical}=require('./access-client.cjs');
const {isDataStartupFailure}=require('./startup-failure.cjs');
const MESSAGES=Object.freeze({cancelled:'Module startup was cancelled.',context:'The selected workspace changed.',authorization:'Application access changed during startup.',transition:'Module startup is unavailable.'});
function failure(code='transition'){const error=new Error(MESSAGES[code]||MESSAGES.transition);error.code=error.reason=Object.hasOwn(MESSAGES,code)?code:'transition';return error;}
function safe(error){return isDataStartupFailure(error)?error:failure(Object.hasOwn(MESSAGES,error?.reason)?error.reason:error?.code);}
function freeze(value){if(value&&typeof value==='object'&&!Object.isFrozen(value)){for(const child of Object.values(value))freeze(child);Object.freeze(value);}return value;}
function fingerprint(value){try{return canonical(structuredClone(value));}catch{throw failure('context');}}

class ModuleDataTransition{
 constructor({getSelected,getGeneration,getRuntime}){
  if([getSelected,getGeneration,getRuntime].some(value=>typeof value!=='function'))throw new Error('Native module startup callbacks are required.');
  Object.assign(this,{getSelected,getGeneration,getRuntime});this.tail=Promise.resolve();this.active=null;this.pending=0;this.epoch=0;this.closed=false;this.invalidating=false;this.draining=null;
 }
 get busy(){return Boolean(this.pending||this.active||this.invalidating);}
 capture(){
  try{
   const selected=structuredClone(this.getSelected()),generation=this.getGeneration(),runtime=this.getRuntime();
   if(!selected||typeof selected!=='object'||Array.isArray(selected)||!Number.isSafeInteger(generation)||generation<0||!runtime||typeof runtime!=='object')throw failure();
   return {selected:freeze(selected),fingerprint:fingerprint(selected),generation,runtime,epoch:this.epoch};
  }catch(error){throw safe(error);}
 }
 assert(record){
  if(record.finished)throw failure('cancelled');
  if(record.signal.aborted){const reason=record.signal.reason;throw safe(reason?.code?reason:failure('cancelled'));}
  if(this.closed||record.epoch!==this.epoch)throw failure('cancelled');
  let current;try{current=this.capture();}catch{throw failure('context');}
  if(current.generation!==record.generation)throw failure('authorization');
  if(current.runtime!==record.runtime||current.fingerprint!==record.fingerprint)throw failure('context');
 }
 assertCommit(record,candidate){
  this.assert(record);const runtime=record.runtime,health=record.health;
  if(candidate!==record.candidate||!candidate||!health||record.committed||
     runtime.child!==health.child||!runtime.child||runtime.origin!==health.origin||runtime.requestsAllowed===false||
     fingerprint(runtime.configuration)!==health.configuration||fingerprint(candidate.effectiveConfiguration)!==health.candidateConfiguration)throw failure();
  return true;
 }
 lease(record){
  return Object.freeze({signal:record.signal,originalSelected:record.selected,
   assertCurrent:()=>{this.assert(record);return true;},
   bindCandidate:candidate=>{
    this.assert(record);
    if(record.candidate||!candidate||typeof candidate!=='object'||!candidate.effectiveConfiguration||typeof candidate.effectiveConfiguration!=='object')throw failure();
    record.candidate=candidate;record.candidateConfiguration=fingerprint(candidate.effectiveConfiguration);return candidate;
   },
   markHealthy:candidate=>{
    this.assert(record);const runtime=record.runtime;
    if(candidate!==record.candidate||!candidate||!runtime.child||typeof runtime.origin!=='string'||!runtime.origin||runtime.requestsAllowed===false||
       fingerprint(runtime.configuration)!==record.fingerprint||fingerprint(candidate.effectiveConfiguration)!==record.candidateConfiguration)throw failure();
    record.health={child:runtime.child,origin:runtime.origin,configuration:fingerprint(runtime.configuration),candidateConfiguration:record.candidateConfiguration};return true;
   },
   canCommit:candidate=>{try{return this.assertCommit(record,candidate);}catch{return false;}},
   assertCommit:candidate=>this.assertCommit(record,candidate),
   commit:(candidate,action)=>{
    try{this.assertCommit(record,candidate);if(record.attempted||typeof action!=='function')throw failure();}catch(error){return Promise.reject(safe(error));}
    record.attempted=true;
    // Keep this promise even if the native caller forgets to await it or throws.
    // Teardown never outruns a protected journal write that has already begun.
    const critical=Promise.resolve().then(()=>{this.assertCommit(record,candidate);return action({signal:record.signal,beforeCommit:()=>this.assertCommit(record,candidate)});});
    record.commitPromise=critical.then(value=>{this.assertCommit(record,candidate);record.committed=true;return value;},error=>{throw safe(error);});
    record.commitPromise.catch(()=>{});return record.commitPromise;
   }
  });
 }
 run(action,{signal}={}){
  if(this.closed||this.invalidating)return Promise.reject(failure('cancelled'));
  if(typeof action!=='function')return Promise.reject(failure());
  if(signal?.aborted)return Promise.reject(failure('cancelled'));
  let context;try{context=this.capture();}catch(error){return Promise.reject(safe(error));}
  this.pending++;
  const result=this.tail.then(()=>this.execute(action,context,signal)).finally(()=>{this.pending--;});
  this.tail=result.catch(()=>{});return result;
 }
 async execute(action,context,externalSignal){
  const abort=new AbortController(),signal=externalSignal?AbortSignal.any([abort.signal,externalSignal]):abort.signal;
  const record={...context,abort,signal,finished:false,candidate:null,health:null,attempted:false,committed:false,commitPromise:null};
  this.assert(record);
  if(record.runtime.child)throw failure(); // Starting a second data root under an open backend is forbidden.
  this.active=record;let value,error;
  try{
   value=await action(this.lease(record));
   if(record.commitPromise)await record.commitPromise;
   this.assert(record);
  }catch(problem){error=safe(problem);}
  finally{
   if(record.commitPromise)try{await record.commitPromise;}catch(problem){error=error||safe(problem);}
   record.finished=true;record.abort.abort(failure('cancelled'));if(this.active===record)this.active=null;
  }
  if(error)throw error;return value;
 }
 invalidate(reason='cancelled'){
  if(this.draining)return this.draining;
  this.invalidating=true;this.epoch++;
  this.active?.abort.abort(failure(reason));
  const pending=this.tail;
  this.draining=pending.then(()=>{
   if(!this.closed){this.invalidating=false;this.draining=null;}
   return Object.freeze({drained:true});
  });
  return this.draining;
 }
 shutdown(){this.closed=true;return this.invalidate('cancelled');}
}
module.exports={ModuleDataTransition};
