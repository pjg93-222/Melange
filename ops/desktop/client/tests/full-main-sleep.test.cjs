"use strict";
const test=require('node:test'),assert=require('node:assert/strict'),path=require('node:path');
const client=process.env.LIFECYCLE_BASELINE_ROOT||path.resolve(__dirname,'..');
const {AccessLifecycle}=require(path.join(client,'access-lifecycle.cjs'));
const {districtRuntime}=require('./fixtures/district-runtime-fixture.cjs');
const {fullMain}=require('./fixtures/full-main-fixture.cjs');
async function until(predicate){for(let n=0;n<100&&!predicate();n++)await new Promise(resolve=>setTimeout(resolve,5));assert.ok(predicate(),'lifecycle reached its expected boundary');}
// Complete main module with real Runtime, Windows gate and access lifecycle.
// Replay its exact host-registration block in its original lexical scope; OS,
// native process/HTTP, window and updater are isolated doubles, never the PC.
async function fixture(t){
 const f=await districtRuntime(t);await f.start();const counts={shown:0,failed:0,ready:0,setup:0,updates:0};let drainResolve;
 const drain=new Promise(resolve=>{drainResolve=resolve;});
 const lifecycle=new AccessLifecycle({runtime:f.runtime,gate:f.gate,hide(){},showBoundary:async()=>{},terrierAuthenticated:async()=>true,onSuspend:()=>drain});
 const main=fullMain({client,authentication:'windows',settings:f.configuration,imports:{'./access-gate.cjs':{authorizeAvailable:gate=>gate.authorize()},'./access-lifecycle.cjs':{terrierSession:async()=>true}}});
 let url=f.runtime.origin+'/';
 main.install({runtime:f.runtime,gate:f.gate,lifecycle,updater:{markApplicationReady(){counts.ready++;},markApplicationFailed:async()=>{counts.failed++;}},
  checkUpdates:()=>{counts.updates++;},showSetup:async()=>{counts.setup++;},
  window:{hide(){},show(){counts.shown++;},loadURL:async value=>{url=value;},isDestroyed:()=>false,isVisible:()=>true,webContents:{getURL:()=>url,send(){}}}});
 main.registerPowerHandlers();t.after(()=>main.dispose());return {...f,main,lifecycle,counts,drainResolve};
}
test('sleep/wake waits for inactive teardown then reuses the verified active Terrier child',async t=>{
 const f=await fixture(t),child=f.runtime.child;f.main.electron.powerMonitor.emit('suspend');assert.equal(f.runtime.requestsAllowed,false);
 f.main.electron.powerMonitor.emit('resume');await new Promise(resolve=>setTimeout(resolve,20));assert.equal(f.counts.ready,0,'wake waits for suspended teardown');
 f.drainResolve();await until(()=>f.counts.ready+f.counts.failed>0);await f.main.launch.whenIdle();
 assert.equal(f.counts.failed,0);assert.equal(f.counts.setup,0);assert.equal(f.counts.ready,1);assert.equal(f.runtime.child,child);assert.equal(f.state.spawns,1);assert.equal(f.runtime.requestsAllowed,true);assert.equal(f.main.singleInstanceRequests,1);
});
test('rapid sleep, lock, resume and unlock do not revive stale or duplicate startup',async t=>{
 const f=await fixture(t),power=f.main.electron.powerMonitor;power.emit('suspend');power.emit('lock-screen');power.emit('resume');power.emit('unlock-screen');power.emit('suspend');power.emit('resume');
 assert.equal(f.runtime.requestsAllowed,false);f.drainResolve();await until(()=>f.counts.ready+f.counts.failed>0);await f.main.launch.whenIdle();
 assert.equal(f.counts.failed,0);assert.equal(f.state.spawns,1);assert.equal(f.runtime.requestsAllowed,true);assert.equal(f.lifecycle.suspended,false);assert.equal(f.main.singleInstanceRequests,1);
});
test('a different Windows account on wake remains hidden with no new backend',async t=>{
 const f=await fixture(t),power=f.main.electron.powerMonitor;power.emit('suspend');f.observed.userSid='S-1-5-21-100-200-300-9999';power.emit('resume');f.drainResolve();await new Promise(resolve=>setTimeout(resolve,30));
 assert.equal(f.counts.ready,0);assert.equal(f.counts.shown,0);assert.equal(f.runtime.requestsAllowed,false);assert.equal(f.state.spawns,1);
});
