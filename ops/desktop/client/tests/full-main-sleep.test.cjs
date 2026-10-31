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
async function fixture(t,{recoverProvider=false}={}){
 const f=await districtRuntime(t);await f.start();const counts={shown:0,failed:0,ready:0,setup:0,updates:0,prepared:0};let drainResolve;
 const drain=new Promise(resolve=>{drainResolve=resolve;});
 const lifecycle=new AccessLifecycle({runtime:f.runtime,gate:f.gate,hide(){},showBoundary:async()=>{},terrierAuthenticated:async()=>true,onSuspend:()=>drain});
 const imports={'./access-gate.cjs':{authorizeAvailable:gate=>gate.authorize()},'./access-lifecycle.cjs':{terrierSession:async()=>true}};
 if(recoverProvider){
  // Keep the real controller authorization/queue and one-use runtime input;
  // replace network/catalogue preparation with an isolated fresh-input provider.
  const {GitHubDistrictController}=require(path.join(client,'github-district-controller.cjs'));
  const provider={info:()=>null,ensure:async(_configuration,authorization)=>{assert.equal(authorization.mode,'standalone');assert.equal(f.runtime.child,null);counts.prepared++;return f.bind();},retireInactive:async()=>{}};
  imports['./backend-command.cjs']={backendCommand:()=>({runtime:f.runtime.resources})};
  imports['./github-district-controller.cjs']={ownerGitHubSource:()=>true,GitHubDistrictController:class extends GitHubDistrictController{constructor(options){super({...options,createProvider:()=>provider,keepAwake:()=>()=>{}});}}};
 }
 const main=fullMain({client,authentication:'windows',settings:f.configuration,imports});
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
test('an observed backend exit during sleep obtains fresh district authority before the main resume restarts it',async t=>{
 const f=await fixture(t,{recoverProvider:true}),oldChild=f.runtime.child,spent=f.runtime.originalConfiguration();
 f.main.electron.powerMonitor.emit('suspend');f.exit();assert.equal(f.runtime.child,null);assert.equal(f.runtime.configuration,null);
 f.main.electron.powerMonitor.emit('resume');f.drainResolve();await until(()=>f.counts.ready+f.counts.failed>0);await f.main.launch.whenIdle();
 assert.equal(f.counts.failed,0);assert.equal(f.counts.setup,0);assert.equal(f.counts.prepared,1);assert.equal(f.counts.ready,1);
 assert.notEqual(f.runtime.child,oldChild);assert.notEqual(f.runtime.originalConfiguration(),spent);assert.equal(f.state.spawns,2);assert.equal(f.state.commits,2);assert.equal(f.state.closes,2);
 assert.equal(f.runtime.requestsAllowed,true);assert.equal(f.lifecycle.suspended,false);assert.equal(f.main.singleInstanceRequests,1);
});
