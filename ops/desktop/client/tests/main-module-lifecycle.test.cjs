'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {startupFixture}=require('./fixtures/module-startup-fixture.cjs');
const mainFile=path.join(__dirname,'..','main.cjs'),source=fs.readFileSync(mainFile,'utf8');
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function deferred(){let resolve;const promise=new Promise(done=>{resolve=done;});return {promise,resolve};}
function actual(startText,endText,context){const start=source.indexOf(startText),end=source.indexOf(endText,start);assert.ok(start>=0&&end>start);vm.runInNewContext(source.slice(start,end),context,{filename:mainFile});return context;}

for(const appId of ['terrier','melange','mentat']){
 test(`actual ${appId} factory requires the exact installed program before activation`,async t=>{
  const context={definition:{id:appId},require:name=>{assert.equal(name,'./module-data-startup.cjs');return require('../module-data-startup.cjs');},
   read:()=>({dataDirectory:'original'}),refuseModuleDataSettings:require('../runtime.cjs').refuseModuleDataSettings,
   resources:path.join(__dirname,'absent-runtime'),runtime:{child:null},accessLifecycle:null};
  actual('function createModuleDataStartup()','\napp.on(\'second-instance\'',context);const startup=context.createModuleDataStartup();
  if(appId==='terrier'){assert.equal(startup,null);return;}t.after(()=>startup.shutdown());assert.equal(startup.supported,false);assert.equal(startup.boundary,null);assert.equal(startup.contract,null);
  assert.equal((await startup.info()).phase,'unsupported');assert.equal(startup.canRefresh(),false);
 });
}

for(const marker of [null,false,undefined,{schemaVersion:1}]){
 test(`actual native factory refuses an own marker ${String(marker)} before installed program lookup`,async t=>{
  let lookups=0,reads=0;const original={dataDirectory:'original',ownerGitHubModuleData:marker};
  const context={definition:{id:'melange'},read:()=>{reads++;return original;},refuseModuleDataSettings:require('../runtime.cjs').refuseModuleDataSettings,
   require:name=>{assert.equal(name,'./module-data-startup.cjs');return {...require('../module-data-startup.cjs'),compiledApplicationContract:()=>{lookups++;assert.fail('No program or provider lookup');}};},
   runtime:{child:null},accessLifecycle:null};
  actual('function createModuleDataStartup()','\napp.on(\'second-instance\'',context);const startup=context.createModuleDataStartup();t.after(()=>startup.shutdown());
  assert.equal(startup.supported,false);assert.equal(startup.contract,null);assert.equal(lookups,0);assert.equal(reads,1);
  await assert.rejects(startup.start(original,null),/GitHub module data startup is unavailable/);
 });
}

test('actual native factory never reads a marker accessor before unsupported launch handling',async t=>{
 let values=0;const selected={};Object.defineProperty(selected,'ownerGitHubModuleData',{get(){values++;assert.fail('No marker value read');}});
 const context={definition:{id:'mentat'},read:()=>selected,refuseModuleDataSettings:require('../runtime.cjs').refuseModuleDataSettings,
  require:name=>{assert.equal(name,'./module-data-startup.cjs');return {...require('../module-data-startup.cjs'),compiledApplicationContract:()=>assert.fail('No installed program lookup')};},runtime:{child:null}};
 actual('function createModuleDataStartup()','\napp.on(\'second-instance\'',context);const startup=context.createModuleDataStartup();t.after(()=>startup.shutdown());
 assert.equal(startup.supported,false);assert.equal(values,0);
});

test('actual approved close drains held signed staging before stopping runtime or activating an update',async t=>{
 const f=startupFixture(t),entered=deferred(),release=deferred(),events=[],segment=f.data.transport.segment;
 f.runtime.child={existing:true};f.data.transport.segment=async(...args)=>{entered.resolve();await release.promise;return segment(...args);};
 const staging=f.startup.stage().catch(error=>error);await entered.promise;const stop=f.runtime.stop;f.runtime.stop=async()=>{events.push('stop');return stop.call(f.runtime);};
 const context={closing:false,moduleDataStartup:f.startup,downloads:{abort:()=>events.push('abort')},clearInterval:()=>{},interval:null,presenceInterval:null,districtDataInterval:null,
  networkWatcher:{close:()=>events.push('network-close')},districtSwitch:null,runtime:f.runtime,portable:false,
  updater:{activateAfterClose:async()=>{events.push('activate');return false;},close:()=>events.push('updater-close')},app:{quit:()=>events.push('quit')}};
 actual('async function finishClose()','\nfunction createModuleDataStartup()',context);
 const closing=context.finishClose();await tick();assert.deepEqual(events,['abort','network-close']);assert.ok(f.runtime.child);
 release.resolve();assert.equal((await staging).code,'cancelled');await closing;assert.deepEqual(events,['abort','network-close','stop','activate','updater-close','quit']);
});

test('actual access lifecycle callback cancels staging synchronously and awaits drain while retaining an open user backend',async t=>{
 const f=startupFixture(t),entered=deferred(),release=deferred(),segment=f.data.transport.segment,existing={userWork:true};f.runtime.child=existing;f.runtime.definition={id:'mentat'};
 f.data.transport.segment=async(...args)=>{entered.resolve();await release.promise;return segment(...args);};const staging=f.startup.stage().catch(error=>error);await entered.promise;
 const gate={local:{lock(){}},client:{presence:async()=>{}}};const context={accessTransition:{mutating:false,begin:()=>()=>{}},accessGate:null,accessInitializing:null,activityOutbox:null,accessLifecycle:null,
  resources:'synthetic-resources',userData:'synthetic-profile',definition:{id:'mentat'},applicationConfig:{},app:{isPackaged:false,getVersion:()=> '1.0.0'},read:()=>({}),runtime:f.runtime,moduleDataStartup:f.startup,
  window:{hide(){}},showAccess:async()=>{},districtSwitch:null,runtimePartition:null,
  require:name=>{
   if(name==='./access-bootstrap.cjs')return {bootstrapAccess:async()=>gate};
   if(name==='./activity-outbox.cjs')return {ActivityOutbox:class{}};
   if(name==='./access-state.cjs')return {accessStateStore:()=>({})};
   if(name==='./access-lifecycle.cjs')return require('../access-lifecycle.cjs');throw new Error('Unexpected access dependency');}};
 actual('async function ensureAccess()','\nasync function drainActivity()',context);await context.ensureAccess();
 let drained=false;const locking=context.accessLifecycle.suspend('locked').then(()=>{drained=true;});assert.equal(f.runtime.requestsAllowed,false);assert.equal(context.accessLifecycle.generation,1);
 await tick();assert.equal(drained,false);assert.equal(f.runtime.child,existing);release.resolve();assert.equal((await staging).code,'cancelled');await locking;
 assert.equal(f.runtime.child,existing);assert.equal(f.events.includes('stop'),false);assert.equal(f.data.journal.active,null);
});

test('actual close confirmation retains calculation and user cancellation guards before teardown',async()=>{
 for(const active of [true,false]){
  const calls=[],context={districtSwitch:null,runtime:{activity:async()=>active},dialog:{showMessageBox:async()=>{calls.push('dialog');return {response:0};}},
   definition:{name:'Synthetic app'},window:{close:()=>assert.fail('No approved close')},askingClose:true,closeApproved:false,updateStatus:()=>{}};
  actual('async function confirmClose()','\nasync function finishClose()',context);await context.confirmClose();assert.equal(context.askingClose,false);assert.equal(context.closeApproved,false);assert.deepEqual(calls,['dialog']);
 }
});

test('actual preload exposes only argument-free module status/stage and removable status subscription',async()=>{
 const calls=[],listeners=new Map();let exposed;
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'..','preload.cjs'),'utf8'),{require:name=>{
  assert.equal(name,'electron');return {contextBridge:{exposeInMainWorld:(name,value)=>{if(name==='desktop')exposed=value;}},ipcRenderer:{sendSync:()=>({enabled:false}),
   invoke:(...args)=>{calls.push(args);return Promise.resolve(null);},on:(event,callback)=>listeners.set(event,callback),removeListener:(event,callback)=>{assert.equal(listeners.get(event),callback);listeners.delete(event);}}};}});
 await exposed.moduleData({configuration:'ignored'});await exposed.refreshModuleData({url:'ignored',path:'ignored'});assert.deepEqual(calls,[['desktop:module-data'],['desktop:module-data-refresh']]);
 let seen;const remove=exposed.onModuleData(value=>{seen=value;}),state={phase:'unsupported'};listeners.get('desktop:module-data-status')({},state);assert.equal(seen,state);remove();assert.equal(listeners.size,0);
 assert.equal(exposed.prepareModuleData,undefined);assert.equal(exposed.commitModuleData,undefined);
});

test('actual main IPC wiring guards sender/frame/origin and stages only native-selected signed data',async t=>{
 const f=startupFixture(t),handlers=new Map(),frame={url:'http://127.0.0.1:43212/'},contents={mainFrame:frame};
 f.runtime.child={existing:true};f.runtime.origin='http://127.0.0.1:43212';
 const context={URL,definition:{id:'mentat'},moduleDataStartup:f.startup,runtime:f.runtime,accessLifecycle:{suspended:false},window:{webContents:contents},
  ipcMain:{handle:(name,callback)=>handlers.set(name,callback)},require:name=>{assert.equal(name,'./github-module-controller.cjs');return require('../github-module-controller.cjs');}};
 actual('function runtimeOnly(event)','\nasync function showSetup()',context);
 actual("  if(moduleDataStartup)require('./github-module-controller.cjs').registerModuleDataIPC", "\n  ipcMain.handle('desktop:districts'",context);
 const trusted={sender:contents,senderFrame:frame},info=handlers.get('desktop:module-data'),refresh=handlers.get('desktop:module-data-refresh');
 for(const event of [{},{sender:{},senderFrame:frame},{sender:contents,senderFrame:{url:frame.url}}])await assert.rejects(refresh(event),/Untrusted application request/);
 frame.url='https://untrusted.invalid/';await assert.rejects(info(trusted),/Untrusted application request/);frame.url=f.runtime.origin+'/';
 assert.deepEqual(f.data.requests,[]);const original=structuredClone(f.selected);
 const status=await refresh(trusted,{appId:'melange',snapshotRoot:'injected',configuration:{dataDirectory:'injected'}});
 assert.equal(status.phase,'update-ready');assert.equal(status.appId,'mentat');assert.equal(status.snapshotRoot,undefined);assert.deepEqual(f.selected,original);assert.equal(f.data.journal.active,null);
 assert.deepEqual([...handlers.keys()],['desktop:module-data','desktop:module-data-refresh']);
 context.accessLifecycle.suspended=true;await assert.rejects(info(trusted),/Untrusted application request/);
});


test('actual native Public data navigation uses only compiled paths after fresh access reveal checks',async()=>{
 for(const [appId,target]of [['melange','/public-data/'],['mentat','/#public-data'],['terrier',null]]){
  let launches=0,allow=true;const loaded=[],runtime={child:{},authorization:{fixture:true},origin:'http://127.0.0.1:43212'},context={definition:{id:appId},closing:false,runtime,
   accessLifecycle:{generation:3,canReveal:async(generation,approval)=>{assert.equal(generation,3);assert.equal(approval,runtime.authorization);return allow;}},launch:async()=>{launches++;},window:{loadURL:async url=>loaded.push(url)}};
  actual('async function openPublicData()','\napp.on(\'second-instance\'',context);await context.openPublicData();
  assert.equal(launches,target?1:0);assert.deepEqual(loaded,target?[runtime.origin+target]:[]);
  if(!target)continue;allow=false;await context.openPublicData();assert.equal(loaded.length,1);
  allow=true;context.accessLifecycle.canReveal=async()=>{context.accessLifecycle.generation++;return true;};await context.openPublicData();assert.equal(loaded.length,1,'Changed access generation prevents navigation');
 }
});
