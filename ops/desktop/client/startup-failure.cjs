'use strict';
// Native startup outcomes: data availability never grants program health.
const NETWORK=new Set(['timeout','unreachable','proxy','rate_limited']);
const BLOCKED=new Set(['integrity','storage']);
const branded=new WeakSet();
const {performance}=require('node:perf_hooks');
const MESSAGES=Object.freeze({
 timeout:'The data download paused because the connection timed out. Retrying automatically; your app update is retained.',
 unreachable:'Waiting for a connection to GitHub data. Retrying automatically; your app update is retained.',
 proxy:'Waiting for the Windows network proxy. Retrying automatically; your app update is retained.',
 rate_limited:'GitHub temporarily limited data requests. Retrying after its waiting period; your app update is retained.',
 integrity:'Data or server-certificate verification did not pass. Automatic retry is paused. Check the reviewed source, then choose Open app to retry. Your app update is retained.',
 storage:'The local data cache is unavailable. Check free space and the selected data folder, then choose Open app to retry. Your app update is retained.'
});
function reason(error){return typeof error?.reason==='string'?error.reason:error?.code;}
function networkFailure(error){return error?.retryableNetwork===true&&NETWORK.has(reason(error));}
function programFailure(){const error=new Error('The installed application could not be verified or started.');error.reason=error.code='program';return error;}
function dataStartupFailure(error){
 const code=reason(error),retryable=networkFailure(error);
 if(!retryable&&!BLOCKED.has(code))return null;
 const result=new Error(MESSAGES[code]);
 result.code=result.reason='startup_deferred';result.dataReason=code;result.retryable=retryable;
 if(retryable&&Number.isSafeInteger(error.retryAfterMs)&&error.retryAfterMs>=1000&&error.retryAfterMs<=3600000)result.retryAfterMs=error.retryAfterMs;
 branded.add(result);return Object.freeze(result);
}
function isDataStartupFailure(error){return Boolean(error&&branded.has(error));}

class StartupRetry{
 constructor({retry,getContext,canRetry,now=()=>performance.now(),setTimeout:setTimer=setTimeout,clearTimeout:clearTimer=clearTimeout}){
  if([retry,getContext,canRetry,now,setTimer,clearTimer].some(value=>typeof value!=='function'))throw new Error('Native startup retry callbacks required.');
  Object.assign(this,{retry,getContext,canRetry,now,setTimer,clearTimer});this.waiting=null;this.timer=null;this.attempts=0;this.lastContext=null;
 }
 context(){const value=this.getContext();if(!value?.runtime||typeof value.key!=='string'||!value.key||value.key.length>256)throw new Error('Startup context unavailable.');return {runtime:value.runtime,key:value.key};}
 same(left,right){return Boolean(left&&right&&left.runtime===right.runtime&&left.key===right.key);}
 eligible(context){try{return this.canRetry()===true&&this.same(context,this.context());}catch{return false;}}
 begin(){if(this.timer!==null)this.clearTimer(this.timer);this.timer=null;this.waiting=null;}
 cancel(){this.begin();this.attempts=0;this.lastContext=null;}
 defer(error){
  if(!isDataStartupFailure(error))throw new Error('A native data startup outcome is required.');
  this.begin();if(!error.retryable){this.cancel();return false;}
  let context;try{context=this.context();}catch{this.cancel();return false;}
  if(!this.eligible(context)){this.cancel();return false;}
  if(!this.same(context,this.lastContext))this.attempts=0;
  this.lastContext=context;this.attempts=Math.min(16,this.attempts+1);
  const time=this.now(),retryAfter=error.retryAfterMs||0,delay=Math.max(retryAfter,Math.min(120000,5000*2**(this.attempts-1)));
  const waiting={context,notBefore:time+retryAfter,dueAt:time+delay};this.waiting=waiting;
  this.timer=this.setTimer(()=>{this.run(waiting).catch(()=>{});},delay);this.timer?.unref?.();return true;
 }
 async run(waiting){
  if(this.waiting!==waiting)return false;
  if(!this.eligible(waiting.context)){this.cancel();return false;}
  if(this.now()<waiting.notBefore)return false;
  this.begin();await this.retry();return true;
 }
 retryNow(){const waiting=this.waiting;return waiting?this.run(waiting):Promise.resolve(false);}
}
module.exports={StartupRetry,isDataStartupFailure,dataStartupFailure,networkFailure,programFailure};
