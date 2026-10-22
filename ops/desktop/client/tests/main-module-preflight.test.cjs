'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {refuseModuleDataSettings}=require('../runtime.cjs');

// Evaluate the actual native launch function with isolated dependencies. This
// covers launch-entry ordering, not app.whenReady/profile/default/migration boot.
const mainFile=path.join(__dirname,'..','main.cjs'),source=fs.readFileSync(mainFile,'utf8');
const start=source.indexOf('async function launchAuthorized('),end=source.indexOf('\n// Terrier: the chosen district stays',start);
assert.ok(start>=0&&end>start,'The actual launch function must be present');
const launchSource=source.slice(start,end)+'\nmodule.exports=launchAuthorized;';
function fixture(appId,{settings,role='owner',portable=false,suspended=false,accessError=false,startupError=false,readError=false,afterSettle=null}={}){
 let selected=settings||{dataDirectory:'synthetic-original-workspace',district:'co-05'},url='about:blank';
 const events=[],authorized=[],started=[],resumed=[],revealed=[];
 const approved={accepted:{grant:{appId,role}},owner:role==='owner'?{mode:'existing-owner'}:null,session:role==='recipient'?{mode:'local-session'}:null};
 const context={module:{exports:{}},URL,background:true,openingAccess:false,closing:false,portable,packs:appId==='terrier'?{}:null,definition:{id:appId},refuseModuleDataSettings,
  read:name=>{assert.equal(name,'settings.json');events.push('read');if(readError)throw new Error('Synthetic settings read failure');return selected;},
  updateStatus:message=>{events.push('status');assert.equal(message,'Application startup failed. Check local logs.');},
  showSetup:async()=>{events.push('setup');},showAccess:async()=>{events.push('accessUI');},showTerrierSignIn:async()=>{events.push('signIn');},
  onRevoked:async()=>{events.push('revoked');},dropDistrictData:async()=>{events.push('dropDistrictData');},bundleNotice:()=>events.push('bundleNotice'),
  accessWindow:{close:()=>events.push('closeAccess')},districtSwitch:{remember:()=>events.push('remember')},
  updater:{markApplicationFailed:async()=>events.push('failed'),markApplicationReady:()=>events.push('ready')},
  window:{hide:()=>events.push('hide'),show:()=>events.push('show'),loadURL:async value=>{events.push('loadURL');url=value;},webContents:{getURL:()=>url}},
  require:name=>{
   if(name==='./access-gate.cjs')return {authorizeAvailable:async gate=>{assert.equal(gate,context.accessGate);events.push('authorizeAvailable');if(accessError)throw new Error('Synthetic unavailable access');}};
   if(name==='./access-lifecycle.cjs')return {terrierSession:async()=>true};
   throw new Error('Unexpected native launch dependency');
  },
 };
 context.accessGate={accepted:{revoked:false},authorize:async configuration=>{events.push('authorize');authorized.push(configuration);return approved;}};
 context.accessLifecycle={generation:0,suspended,requiresFreshPassword:false,
  resume:async(value,options)=>{events.push('resume');resumed.push(value);assert.equal(options.expectedGeneration,0);context.accessLifecycle.suspended=false;},
  canReveal:async(generation,value)=>{events.push('canReveal');assert.equal(generation,0);revealed.push(value);return true;},
  heartbeat:async()=>events.push('heartbeat'),suspend:async()=>{events.push('suspend');context.accessLifecycle.suspended=true;}};
 context.ensureAccess=async()=>{events.push('ensureAccess');return context.accessGate;};
 context.settleDistrict=async()=>{events.push('settleDistrict');if(afterSettle)selected=afterSettle(selected);};
 context.prepareDistrictData=async()=>{events.push('prepareDistrictData');return selected;};
 context.runtime={child:null,configuration:null,launchPath:'/',start:async configuration=>{
  events.push('runtime.start');started.push(configuration);refuseModuleDataSettings(configuration);
  if(startupError)throw new Error('Synthetic backend startup failure');context.runtime.child={};return 'http://127.0.0.1:43212';
 }};
 vm.runInNewContext(launchSource,context,{filename:mainFile});
 return {launch:context.module.exports,context,events,authorized,started,resumed,revealed,approved,get selected(){return selected;}};
}
function assertPreflightFailure(f){
 assert.deepEqual(f.events,['read','failed','status','setup']);
 assert.equal(f.authorized.length,0);assert.equal(f.started.length,0);assert.equal(f.context.openingAccess,false);
}

for(const appId of ['terrier','melange','mentat']){
 for(const [label,value] of [['undefined',undefined],['null',null],['false',false],['true',true],['descriptor',{schemaVersion:1,cacheRoot:'untrusted-cache'}]]){
  test(`${appId} rejects an own ${label} module marker before launch authorization/district/cache preparation`,async()=>{
   const settings={dataDirectory:'synthetic-original-workspace',ownerGitHubModuleData:value},f=fixture(appId,{settings});
   await assert.rejects(f.launch(false),/GitHub module data startup is unavailable in this build/);
   assertPreflightFailure(f);assert.equal(f.selected,settings);
  });
 }
 for(const role of ['owner','recipient']){
  test(`${appId} ordinary ${role} startup still authorizes, prepares and reveals through the existing lifecycle`,async()=>{
   const f=fixture(appId,{role});await f.launch(false);
   assert.deepEqual(f.events.slice(0,5),['read','ensureAccess','settleDistrict','authorizeAvailable','read']);
   assert.equal(f.events.includes('prepareDistrictData'),appId==='terrier');
   assert.equal(f.authorized.length,1);assert.equal(f.started.length,1);assert.equal(f.authorized[0],f.selected);assert.equal(f.started[0],f.selected);
   assert.equal(f.resumed[0],f.approved);assert.equal(f.revealed.length,2);assert.ok(f.revealed.every(value=>value===f.approved));
   assert.equal(f.events.includes('setup'),false);assert.equal(f.events.includes('accessUI'),false);assert.equal(f.events.at(-1),'heartbeat');assert.equal(f.context.openingAccess,false);
  });
 }
}

test('the launch preflight refuses an own marker accessor without evaluating it',async()=>{
 const settings={dataDirectory:'synthetic-original-workspace'};let reads=0;
 Object.defineProperty(settings,'ownerGitHubModuleData',{enumerable:true,get(){reads++;throw new Error('Untrusted accessor');}});
 const f=fixture('mentat',{settings});await assert.rejects(f.launch(true),/GitHub module data startup is unavailable/);
 assert.equal(reads,0);assertPreflightFailure(f);
});

test('Terrier rereads configuration after district settlement instead of launching the early preflight snapshot',async()=>{
 const f=fixture('terrier',{afterSettle:previous=>({...previous,district:'or-05',settled:true})});await f.launch(false);
 assert.equal(f.authorized[0].district,'or-05');assert.equal(f.started[0].district,'or-05');assert.equal(f.started[0],f.selected);
 assert.equal(f.events.filter(value=>value==='read').length,2);assert.ok(f.events.indexOf('prepareDistrictData')>f.events.indexOf('settleDistrict'));
});

test('the fresh configuration is checked again before district preparation if it changes during access work',async()=>{
 const f=fixture('terrier',{afterSettle:previous=>({...previous,ownerGitHubModuleData:false})});
 await assert.rejects(f.launch(false),/GitHub module data startup is unavailable/);
 assert.deepEqual(f.events,['read','ensureAccess','settleDistrict','authorizeAvailable','read','failed','status','setup']);
 assert.equal(f.authorized.length,0);assert.equal(f.started.length,0);assert.equal(f.context.openingAccess,false);
});

for(const fromAccess of [false,true]){
 test(`ordinary unavailable recipient access preserves its existing ${fromAccess?'access-window':'normal-open'} handler`,async()=>{
  const f=fixture('mentat',{role:'recipient',accessError:true});
  if(fromAccess)await assert.rejects(f.launch(true),/Access is not ready/);else await f.launch(false);
  assert.equal(f.events.includes('setup'),false);assert.equal(f.events.includes('failed'),false);assert.equal(f.events.includes('accessUI'),!fromAccess);assert.equal(f.started.length,0);
 });
}

test('backend startup errors still use the same failure UI and clear openingAccess',async()=>{
 const f=fixture('melange',{startupError:true});await assert.rejects(f.launch(false),/Synthetic backend startup failure/);
 assert.deepEqual(f.events.slice(-3),['failed','status','setup']);assert.equal(f.events.includes('accessUI'),false);assert.equal(f.context.openingAccess,false);
});

test('portable preflight failure preserves startup UI without marking an update failed',async()=>{
 const f=fixture('melange',{portable:true,settings:{dataDirectory:'synthetic-original-workspace',ownerGitHubModuleData:null}});
 await assert.rejects(f.launch(false),/GitHub module data startup is unavailable/);assert.deepEqual(f.events,['read','status','setup']);
});

test('an already suspended lifecycle keeps the existing startup-failure suppression',async()=>{
 const f=fixture('terrier',{suspended:true,settings:{dataDirectory:'synthetic-original-workspace',ownerGitHubModuleData:false}});
 await f.launch(false);assert.deepEqual(f.events,['read']);assert.equal(f.context.openingAccess,false);
});

test('settings read failures use startup UI before any launch-dependent access preparation',async()=>{
 const f=fixture('mentat',{readError:true});await assert.rejects(f.launch(false),/Synthetic settings read failure/);assertPreflightFailure(f);
});
