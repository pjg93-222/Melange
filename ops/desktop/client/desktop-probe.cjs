'use strict';
const {spawn}=require('node:child_process');
const {performance}=require('node:perf_hooks');
const {backendEnvironment}=require('./backend-command.cjs');
const canceled=()=>new Error('Local data verification canceled.');
// Bootstrap imports may warm while trusted callers hash. No input is sent until
// run(), and every failure waits for the owned process/streams to close.
function prepareDesktopProbe(command,mode,{timeout=30000,limit=32768,signal,prewarmTimeout=30000,onDiagnostic=()=>{},beforeSpawn=()=>{}}={}){
 let used=false,cancelled=false,attempt;const diagnostics=[];
 const record=(phase,reason,started)=>{const value=Object.freeze({phase,reason,elapsedMs:Math.round(performance.now()-started)});diagnostics.push(value);try{onDiagnostic(value);}catch{}};
 function begin(warming){
  const started=performance.now();let child,timer,sent=false,closed=false,error=null,expired=false,size=0;const chunks=[];
  let complete;const done=new Promise(resolve=>{complete=resolve;});
  let reported=false;
  const report=reason=>{if(reported)return;reported=true;record(sent?'reader':'prewarm',reason,started);};
  const close=code=>{
   if(closed)return;closed=true;clearTimeout(timer);signal?.removeEventListener('abort',abort);
   let value;if(!error){if(!sent||code!==0)error=new Error('Local data verification failed.');else try{value=JSON.parse(Buffer.concat(chunks).toString('utf8'));}catch{error=new Error('Invalid local verification response.');}}
   if(error&&!reported)report(!sent?'early-exit':'invalid-result');complete({error,value,expired});
  };
  const stop=(failure,reason,{expire=false}={})=>{
   if(closed)return done;if(!error){error=failure;expired=expire;report(reason);}clearTimeout(timer);
   // stdin is never ended with a dataset on a failed/expired warm attempt.
   try{child?.stdin.destroy();}catch{}try{child?.kill();}catch{}
   if(!child)close(null);return done;
  };
  const abort=()=>stop(canceled(),'cancelled');
  if(signal?.aborted){stop(canceled(),'cancelled');}
  else{
   beforeSpawn();
   try{child=spawn(command.binary,[...command.args,mode],{env:backendEnvironment(),windowsHide:true,stdio:['pipe','pipe','pipe']});}
   catch{stop(new Error('Local data verification unavailable.'),'spawn-failed');}
   if(child){
    child.on('error',()=>stop(signal?.aborted?canceled():new Error('Local data verification unavailable.'),signal?.aborted?'cancelled':'process-error'));
    child.stdin.on('error',()=>stop(signal?.aborted?canceled():new Error('Local data verification unavailable.'),signal?.aborted?'cancelled':'input-error'));child.stderr.resume();
    child.stdout.on('data',chunk=>{size+=chunk.length;if(size>limit)stop(new Error('Invalid local verification response.'),'output-limit');else chunks.push(chunk);});
    child.on('close',close);signal?.addEventListener('abort',abort,{once:true});
    if(signal?.aborted)abort();
    else if(warming)timer=setTimeout(()=>stop(new Error('Optional native reader warmup expired.'),'expired',{expire:true}),Math.min(120000,Math.max(1,Number(prewarmTimeout)||30000)));
   }
  }
  return {done,stop,send(payload){
   if(sent)throw new Error('Local data verification input was already sent.');
   if(closed||error)return done;sent=true;clearTimeout(timer);
   timer=setTimeout(()=>stop(new Error('Local data verification timed out.'),'timeout'),timeout);
   try{child.stdin.end(JSON.stringify(payload));}catch{stop(new Error('Local data verification unavailable.'),'input-error');}
   return done;
  }};
 }
 attempt=begin(true);
 return Object.freeze({
  async run(payload){
   if(used)throw new Error('Local data verification input was already sent.');used=true;
   if(cancelled||signal?.aborted){await attempt.stop(canceled(),'cancelled');throw canceled();}
   let result=await attempt.send(payload);
   if(result.expired&&!cancelled&&!signal?.aborted){
    // An optional warmup can expire during a long valid hash. Its child has
    // already exited; exactly one ordinary fresh probe gets the verified input.
    attempt=begin(false);result=await attempt.send(payload);
   }
   if(cancelled||signal?.aborted)throw canceled();if(result.error)throw result.error;return result.value;
  },
  async cancel(){cancelled=true;await attempt.stop(canceled(),'cancelled');},
  diagnostics:()=>diagnostics.map(value=>({...value}))
 });
}
function desktopProbe(command,mode,payload,options){return prepareDesktopProbe(command,mode,options).run(payload);}
module.exports={desktopProbe,prepareDesktopProbe};
