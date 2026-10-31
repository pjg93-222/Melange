'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {StartupRetry,dataStartupFailure,isDataStartupFailure,programFailure}=require('../startup-failure.cjs');
function network(reason,retryAfterMs){return Object.assign(new Error('unsafe provider details'),{reason,retryableNetwork:true,retryAfterMs});}
function fixture(){
 let now=0,context={runtime:{},key:'generation-and-selection-a'},allowed=true,calls=0;const timers=[];
 const retry=new StartupRetry({retry:async()=>{calls++;},getContext:()=>context,canRetry:()=>allowed,now:()=>now,
  setTimeout:(callback,delay)=>{const entry={callback,delay,cleared:false,unref(){}};timers.push(entry);return entry;},clearTimeout:timer=>{timer.cleared=true;}});
 return {retry,timers,get calls(){return calls;},set now(value){now=value;},set context(value){context=value;},set allowed(value){allowed=value;}};
}
test('only native marked transport errors can request automatic retry; data-integrity refusal is terminal',()=>{
 for(const reason of ['timeout','unreachable','proxy','rate_limited']){
  const outcome=dataStartupFailure(network(reason,30000));assert.ok(isDataStartupFailure(outcome));assert.equal(outcome.retryable,true);assert.equal(outcome.retryAfterMs,30000);assert.doesNotMatch(outcome.message,/unsafe provider/);
  assert.equal(dataStartupFailure({reason}),null);
 }
 for(const reason of ['integrity','storage'])assert.equal(dataStartupFailure({reason,retryableNetwork:true}).retryable,false);
 for(const reason of ['program','transition','authorization','context','cancelled','CERT_HAS_EXPIRED'])assert.equal(dataStartupFailure({reason,retryableNetwork:true}),null);
 assert.equal(isDataStartupFailure({code:'startup_deferred',retryable:true}),false);
 assert.equal(dataStartupFailure(programFailure()),null);
});
test('a reconnect honors server retry-after and resumes through the native launch callback once',async()=>{
 const f=fixture();f.retry.defer(dataStartupFailure(network('rate_limited',60000)));assert.equal(f.timers[0].delay,60000);
 f.now=59999;assert.equal(await f.retry.retryNow(),false);assert.equal(f.calls,0);
 f.now=60000;assert.equal(await f.retry.retryNow(),true);assert.equal(f.calls,1);assert.equal(f.timers[0].cleared,true);
 await f.timers[0].callback();assert.equal(f.calls,1);
});
test('successive cold failures back off, while a new selected context starts a fresh bounded retry',()=>{
 const f=fixture(),error=dataStartupFailure(network('timeout'));
 f.retry.defer(error);assert.equal(f.timers.at(-1).delay,5000);f.retry.begin();f.retry.defer(error);assert.equal(f.timers.at(-1).delay,10000);
 f.context={runtime:{},key:'new-selection'};f.retry.defer(error);assert.equal(f.timers.at(-1).delay,5000);
});
for(const change of ['authorization','runtime','selection','close','cancel'])test('queued cold retry cannot survive '+change,async()=>{
 const f=fixture();f.retry.defer(dataStartupFailure(network('timeout')));
 if(change==='authorization'||change==='close')f.allowed=false;
 if(change==='runtime'||change==='selection')f.context={runtime:{},key:'changed'};
 if(change==='cancel')f.retry.cancel();
 f.now=5000;await f.timers[0].callback();await new Promise(resolve=>setImmediate(resolve));assert.equal(f.calls,0);
});
test('data signature/TLS integrity refusal schedules no automatic request or health callback',()=>{
 const f=fixture();assert.equal(f.retry.defer(dataStartupFailure({reason:'integrity'})),false);assert.equal(f.timers.length,0);assert.equal(f.calls,0);
 assert.throws(()=>f.retry.defer({reason:'startup_deferred',retryable:true}),/native data startup/);
});
