'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const client=process.env.LIFECYCLE_BASELINE_ROOT||path.resolve(__dirname,'..');
const {AccessLifecycle}=require(path.join(client,'access-lifecycle.cjs'));

function fixture({owner=true}={}){
 const approved={accepted:{grant:{appId:'terrier',serverId:'server',deviceId:'device',principalId:'principal',accountIdentity:'approved-account',role:'local_administrator',districtIds:['or-05']},revoked:false},
  owner:owner?{mode:'existing-owner'}:null,principal:{mode:owner?'existing-owner':'recipient',localAccountIdentity:'local-owner',localUserId:'7',districtId:'or-05'}};
 const runtime={definition:{id:'terrier'},child:{pid:123},origin:'http://127.0.0.1:12345',token:'fixture-token',authorization:approved,requestsAllowed:false,configuration:{district:'or-05'},launchPath:'/'};
 const counts={proof:0,logout:0,gate:0,session:0,signin:0,show:0,closeAccess:0,start:0};
 let authenticated=true;
 const gate={authorize:async()=>{counts.gate++;return structuredClone(approved);},local:{lock(){}}};
 const lifecycle=new AccessLifecycle({runtime,gate,hide(){},showBoundary:async()=>{},
  terrierAuthenticated:async()=>authenticated,
  terrierLogout:async()=>{counts.logout++;if(!owner)authenticated=false;return true;},
  terrierPasswordLockDisabled:async()=>{counts.proof++;return true;}});
 lifecycle.suspended=true;lifecycle.requiresFreshPassword=true;
 runtime.start=async()=>{counts.start++;return runtime.origin;};
 return {approved,runtime,counts,gate,lifecycle};
}

function mainLaunch(f){
 const source=fs.readFileSync(path.join(client,'main.cjs'),'utf8');
 const start=source.indexOf('async function launchAuthorized(fromAccess){');
 const end=source.indexOf('// Terrier: the chosen district',start);
 assert.ok(start>=0&&end>start,'Use the actual published/candidate main launch function');
 const context={URL,background:false,closing:false,openingAccess:false,portable:true,packs:null,definition:{id:'terrier'},
  accessLifecycle:f.lifecycle,accessGate:f.gate,runtime:f.runtime,runtimePartition:{},districtSwitch:null,
  refuseModuleDataSettings(){},moduleDataStartup:null,loadingStatus:async()=>{},updater:{markApplicationReady(){},markApplicationFailed:async()=>{}},ensureAccess:async()=>f.gate,settleDistrict:async()=>{},read:()=>f.runtime.configuration,bundleNotice(){},
  window:{hide(){},show(){f.counts.show++;},webContents:{getURL:()=>f.runtime.origin+'/',}},
  accessWindow:{close(){f.counts.closeAccess++;}},showAccess:async()=>{},showSetup:async()=>{},updateStatus(){},
  showTerrierSignIn:async()=>{f.counts.signin++;await f.lifecycle.prepareAuthentication();},
  require(name){
   if(name==='./access-gate.cjs')return {authorizeAvailable:gate=>gate.authorize()};
   if(name==='./access-lifecycle.cjs')return {terrierSession:async()=>{f.counts.session++;return true;}};
   throw new Error('Unexpected fixture import: '+name);
  }};
 return vm.runInNewContext('('+source.slice(start,end)+')',context)(true);
}

test('warm main recovers the stale owner latch without logout or a sign-in window',async()=>{
 const f=fixture(),child=f.runtime.child;
 await mainLaunch(f);
 assert.equal(f.counts.signin,0);assert.equal(f.counts.logout,0);
 assert.equal(f.counts.session,0,'No second short authentication probe after verified owner proof');
 assert.equal(f.counts.proof,1);assert.equal(f.counts.start,1);assert.equal(f.counts.show,1);assert.equal(f.counts.closeAccess,1);
 assert.equal(f.runtime.child,child);assert.equal(f.lifecycle.requiresFreshPassword,false);assert.equal(f.lifecycle.suspended,false);assert.equal(f.runtime.requestsAllowed,true);
 assert.ok(f.counts.gate>=5,'Fresh owner authorization, ordinary resume authorization and reveal gates all run');
});

test('a failed lock-time owner probe is recoverable even though logout auto-rebinds that owner',async()=>{
 const f=fixture();f.lifecycle.suspended=false;f.runtime.requestsAllowed=true;
 f.lifecycle.terrierPasswordLockDisabled=async()=>false;
 await f.lifecycle.suspend('locked');
 assert.equal(f.lifecycle.requiresFreshPassword,true);assert.equal(f.counts.logout,1);assert.equal(await f.lifecycle.terrierAuthenticated(),true);
 f.lifecycle.terrierPasswordLockDisabled=async()=>true;
 assert.equal(await f.lifecycle.refreshPasswordlessOwner(),true);
 assert.equal(f.counts.logout,1,'Recovery does not attempt the impossible owner logout');
 assert.equal(f.lifecycle.requiresFreshPassword,false);
 assert.equal(f.lifecycle.suspended,true);assert.equal(f.runtime.requestsAllowed,false,'Proof alone does not restore access');
});

for(const kind of ['false','throws'])test('failed owner proof stays hidden and does not log out: '+kind,async()=>{
 const f=fixture();f.lifecycle.terrierPasswordLockDisabled=async()=>{if(kind==='throws')throw new Error('unavailable');return false;};
 await assert.rejects(mainLaunch(f),/owner sign-in could not be verified/);
 assert.equal(f.lifecycle.requiresFreshPassword,true);assert.equal(f.lifecycle.suspended,true);assert.equal(f.runtime.requestsAllowed,false);
 assert.equal(f.counts.signin,0);assert.equal(f.counts.logout,0);assert.equal(f.counts.start,0);assert.equal(f.counts.show,0);
});

test('recipient cannot use an injected true owner predicate and still needs fresh password authentication',async()=>{
 const f=fixture({owner:false});
 assert.equal(await f.lifecycle.refreshPasswordlessOwner(),false);assert.equal(f.counts.proof,0);
 await assert.rejects(f.lifecycle.resume(f.approved),/Fresh/);
 await mainLaunch(f);
 assert.equal(f.counts.signin,1);assert.equal(f.counts.logout,1);assert.equal(f.counts.proof,0);assert.equal(f.counts.show,0);assert.equal(f.counts.start,0);
 assert.equal(f.lifecycle.requiresFreshPassword,true);assert.equal(f.runtime.requestsAllowed,false);
 await f.lifecycle.resume(f.approved,{freshPassword:true});assert.equal(f.runtime.requestsAllowed,true);
});

test('both verified owner modes are required and other apps do not enter owner recovery',async()=>{
 for(const mutate of [f=>{f.approved.owner=null;},f=>{f.approved.owner.mode='recipient';},f=>{f.approved.principal.mode='recipient';},f=>{f.runtime.definition.id='mentat';}]){
  const f=fixture();mutate(f);assert.equal(await f.lifecycle.refreshPasswordlessOwner(),false);assert.equal(f.counts.proof,0);assert.equal(f.lifecycle.requiresFreshPassword,true);assert.equal(f.runtime.requestsAllowed,false);
 }
});

for(const phase of ['before','after'])test('fresh authorization rejects revoked, narrowed and changed approval '+phase+' owner proof',async()=>{
 for(const change of [a=>{a.accepted.revoked=true;},a=>{a.accepted.grant.districtIds=[];},a=>{a.accepted.grant.principalId='other';},a=>{a.principal.localAccountIdentity='other';},a=>{a.principal.mode='recipient';a.owner=null;}]){
  const f=fixture();let calls=0;
  f.gate.authorize=async()=>{const value=structuredClone(f.approved);if(++calls===(phase==='before'?1:2))change(value);return value;};
  await assert.rejects(f.lifecycle.refreshPasswordlessOwner(),/could not be verified/);
  assert.equal(f.lifecycle.requiresFreshPassword,true);assert.equal(f.runtime.requestsAllowed,false);assert.equal(f.counts.logout,0);
 }
});

const mutations={
 generation:f=>{f.lifecycle.generation++;},
 lock:f=>{f.lifecycle.osLocked=true;},
 child:f=>{f.runtime.child={pid:456};},
 origin:f=>{f.runtime.origin='http://127.0.0.1:23456';},
 token:f=>{f.runtime.token='replacement';},
 authorization:f=>{f.runtime.authorization=structuredClone(f.approved);},
 identity:f=>{f.approved.principal.localAccountIdentity='changed';},
 ownerMode:f=>{f.approved.owner.mode='recipient';},
 application:f=>{f.runtime.definition.id='mentat';},
};
for(const phase of ['first approval','owner session','final approval'])test('no stale owner proof survives '+phase+' races',async()=>{
 for(const [name,mutate]of Object.entries(mutations)){
  const f=fixture();let calls=0;
  f.gate.authorize=async()=>{if(++calls===(phase==='first approval'?1:phase==='final approval'?2:-1))mutate(f);return structuredClone(f.approved);};
  f.lifecycle.terrierPasswordLockDisabled=async()=>{if(phase==='owner session')mutate(f);return true;};
  await assert.rejects(f.lifecycle.refreshPasswordlessOwner(),/could not be verified/,phase+': '+name);
  assert.equal(f.lifecycle.requiresFreshPassword,true,name);assert.equal(f.runtime.requestsAllowed,false,name);assert.equal(f.counts.logout,0,name);
 }
});

test('initial OS lock and stale generation prevent the owner probe entirely',async()=>{
 const locked=fixture();locked.lifecycle.osLocked=true;
 await assert.rejects(locked.lifecycle.refreshPasswordlessOwner(),/could not be verified/);assert.equal(locked.counts.gate,0);assert.equal(locked.counts.proof,0);
 const stale=fixture();await assert.rejects(stale.lifecycle.refreshPasswordlessOwner({expectedGeneration:-1}),/could not be verified/);assert.equal(stale.counts.gate,0);
});

test('OS lock prevents ordinary resume even after a successful owner proof',async()=>{
 const f=fixture();await f.lifecycle.refreshPasswordlessOwner();f.lifecycle.osLocked=true;
 await assert.rejects(f.lifecycle.resume(f.approved),/Unlock Windows/);assert.equal(f.runtime.requestsAllowed,false);assert.equal(f.lifecycle.suspended,true);
});

test('OS lock before or during reveal authorization prevents revealing an active window',async()=>{
 for(const during of [false,true]){
  const f=fixture();f.lifecycle.requiresFreshPassword=false;await f.lifecycle.resume(f.approved);
  if(during)f.gate.authorize=async()=>{f.lifecycle.osLocked=true;return f.approved;};else f.lifecycle.osLocked=true;
  assert.equal(await f.lifecycle.canReveal(f.lifecycle.generation,f.approved),false);
 }
});

test('warm main does not resume or reveal when Windows locks after the owner proof',async()=>{
 const f=fixture(),original=f.lifecycle.refreshPasswordlessOwner.bind(f.lifecycle);
 f.lifecycle.refreshPasswordlessOwner=async options=>{const result=await original(options);f.lifecycle.osLocked=true;return result;};
 await mainLaunch(f);assert.equal(f.counts.show,0);assert.equal(f.counts.start,0);assert.equal(f.runtime.requestsAllowed,false);
});
