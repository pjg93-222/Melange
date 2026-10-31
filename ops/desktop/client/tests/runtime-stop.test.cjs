'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {createRequire}=require('node:module'),{EventEmitter}=require('node:events');
const runtimeFile=path.join(__dirname,'..','runtime.cjs'),source=fs.readFileSync(runtimeFile,'utf8'),localRequire=createRequire(runtimeFile);
const turn=()=>new Promise(resolve=>setImmediate(resolve));
function fixture({commandHangs=false,commandThrows=false}={}){
  const timers=new Map(),commands=[],signals=[];let nextTimer=0;
  const child=Object.assign(new EventEmitter(),{pid:12345,exitCode:null,signalCode:null,kill(signal){signals.push(signal);return true;}});
  const context={module:{exports:{}},process:{platform:'win32'},setTimeout(callback,ms){const id=++nextTimer;timers.set(id,{callback,ms});return id;},clearTimeout(id){timers.delete(id);},
    require(name){if(name!=='node:child_process')return localRequire(name);return {spawn(binary,args,options){
      commands.push({binary,args:[...args],options});if(commandThrows)throw new Error('taskkill unavailable');
      const killer=Object.assign(new EventEmitter(),{exitCode:commandHangs?null:0,signalCode:null,kill(signal){this.signalCode=signal;this.emit('exit',null,signal);return true;}});
      commands.at(-1).child=killer;return killer;
    }};}};
  vm.runInNewContext(source,context,{filename:runtimeFile});
  const runtime=new context.module.exports.Runtime('terrier','unused-profile','unused-resources');runtime.child=child;runtime.requestsAllowed=true;
  runtime.origin='http://127.0.0.1:12345';runtime.token='fixture';runtime.configuration={district:'co-05'};
  return {runtime,child,commands,signals,timers,exit(signal=null){child.exitCode=signal?null:0;child.signalCode=signal;child.emit('exit',child.exitCode,signal);},
    async expire(){await turn();const first=timers.entries().next().value;assert.ok(first,'expected a bounded shutdown timer');const [id,item]=first;assert.equal(item.ms,5000);timers.delete(id);item.callback();await turn();}};
}

test('an already signal-exited backend needs no kill and releases its handle',async()=>{
  const f=fixture();f.child.signalCode='SIGTERM';await f.runtime.stop();
  assert.equal(f.commands.length,0);assert.equal(f.signals.length,0);assert.equal(f.runtime.child,null);assert.equal(f.runtime.stoppingChild,null);
  assert.equal(f.runtime.requestsAllowed,false);assert.equal(f.runtime.origin,null);assert.equal(f.timers.size,0);
});

test('SIGKILL dispatch does not resolve shutdown before the backend actually exits',async()=>{
  const f=fixture();let resolved=false;const stopping=f.runtime.stop();stopping.then(()=>{resolved=true;});
  await f.expire();assert.deepEqual(f.signals,['SIGKILL']);assert.equal(resolved,false);
  assert.equal(f.runtime.child,f.child);assert.equal(f.runtime.stoppingChild,f.child);
  await assert.rejects(f.runtime.start({}),/shutdown is still pending/);
  f.exit('SIGKILL');await stopping;assert.equal(resolved,true);assert.equal(f.runtime.child,null);assert.equal(f.timers.size,0);
});

test('failed termination retains a retryable child and cannot authorize cache retirement',async()=>{
  const f=fixture();f.child.kill=()=>{throw new Error('termination refused');};
  const stopping=f.runtime.stop(),rejected=assert.rejects(stopping,{code:'BACKEND_STOP_TIMEOUT'});
  await f.expire();await f.expire();await rejected;
  assert.equal(f.runtime.child,f.child);assert.equal(f.runtime.stoppingChild,f.child);assert.equal(f.runtime.stopPromise,null);
  assert.equal(f.runtime.requestsAllowed,false);await assert.rejects(f.runtime.start({}),/shutdown is still pending/);
  f.exit();await f.runtime.stop();assert.equal(f.runtime.child,null);assert.equal(f.runtime.stoppingChild,null);assert.equal(f.commands.length,1);
});

test('concurrent stops share one termination and close services once',async()=>{
  const f=fixture();let rendererCloses=0,scrapeCloses=0;f.runtime.generation=7;
  f.runtime.renderer={async close(){rendererCloses++;}};f.runtime.scrape={async close(){scrapeCloses++;}};
  const first=f.runtime.stop(),second=f.runtime.stop();assert.equal(first,second);assert.equal(f.runtime.generation,8);assert.equal(f.runtime.requestsAllowed,false);
  await turn();assert.equal(f.commands.length,1);assert.equal(rendererCloses,1);assert.equal(scrapeCloses,1);
  f.exit();await Promise.all([first,second]);assert.equal(f.runtime.stopPromise,null);assert.equal(f.timers.size,0);
});

test('a hung taskkill command is bounded and still requires the real backend exit',async()=>{
  const f=fixture({commandHangs:true});let resolved=false;const stopping=f.runtime.stop();stopping.then(()=>{resolved=true;});
  await f.expire();assert.equal(f.commands[0].child.signalCode,'SIGKILL');assert.equal(resolved,false);
  f.exit();await stopping;assert.equal(f.runtime.child,null);assert.equal(f.timers.size,0);
});

test('taskkill startup failure falls back without claiming the backend has exited',async()=>{
  const f=fixture({commandThrows:true});let resolved=false;const stopping=f.runtime.stop();stopping.then(()=>{resolved=true;});
  await turn();assert.deepEqual(f.signals,[undefined]);assert.equal(resolved,false);assert.equal(f.runtime.child,f.child);
  f.exit();await stopping;assert.equal(f.runtime.child,null);assert.equal(f.timers.size,0);
});
