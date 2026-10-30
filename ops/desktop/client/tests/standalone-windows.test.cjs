'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {createStandaloneGate,checkedWindowsIdentity}=require('../standalone-access.cjs');
const protocol=require('../github-module-protocol.cjs');
const path=require('node:path');
const DEVICE='11111111-1111-4111-8111-111111111111',SID='S-1-5-21-100-200-300-1001';
function store(initial=null){let value=structuredClone(initial);const result={reads:0,writes:0,deletes:0,read:async()=>{result.reads++;return structuredClone(value);},write:async(...args)=>{result.writes++;value=structuredClone(args.at(-1));},delete:async()=>{result.deletes++;value=null;},get value(){return structuredClone(value);}};return result;}
function fixture(appId='melange'){
 const accountStore=store(),passwords=store(),devices=store(),windowsStore=store();let observed={schemaVersion:1,userSid:SID,accountName:'FIXTURE\\Windows User',sessionId:2,locked:false},probes=0;
 return {accountStore,passwords,devices,windowsStore,get probes(){return probes;},get observed(){return structuredClone(observed);},set observed(value){observed=value;},options:{appId,identity:{deviceId:DEVICE},accountStore,passwords,devices,windowsStore,authentication:'windows',windowsSessionProvider:async()=>{probes++;if(observed instanceof Error)throw observed;return structuredClone(observed);},configuration:()=>({district:'co-05'}),now:()=>1800000000000}};
}
for(const appId of ['melange','mentat','terrier'])test(`${appId} opens using a verified Windows session without an app password or managed grant`,async()=>{
 const f=fixture(appId),gate=await createStandaloneGate(f.options),info=await gate.info(),auth=await gate.authorize();
 assert.equal(info.phase,'ready');assert.equal(info.accessMode,'standalone');assert.equal(info.authentication,'windows');assert.equal(info.windowsAccountDisplayName,f.observed.accountName);
 assert.equal(auth.session.method,'windows-session');assert.equal(auth.identity,gate.identity);assert.equal(f.probes,1);assert.equal(await gate.evidence(),null);assert.equal('client' in gate,false);
 assert.deepEqual(Object.keys(auth).sort(),['identity','mode','principal','session']);assert.equal('serverId' in auth.identity,false);assert.equal('accepted' in auth,false);
 assert.deepEqual(auth.principal,appId==='terrier'?{mode:'standalone',districtId:'co-05'}:null);
 assert.equal(f.windowsStore.value.userSid,SID);assert.equal(f.passwords.reads,0);assert.equal(f.passwords.writes,0);assert.equal(f.devices.reads,0);assert.equal(f.devices.writes,0);
 for(const method of ['setPassword','unlock','request','activate','poll'])await assert.rejects(gate.action(method,{password:'unused',userSid:SID}),/does not accept/);
 if(appId!=='terrier')assert.equal(protocol.authorized(appId,{dataDirectory:path.resolve('synthetic-public-root')},auth),true);
});
test('24 account identity, password and remembered-device records remain byte-for-byte unchanged',async()=>{
 const f=fixture(),old=await createStandaloneGate({...f.options,authentication:'password'});
 await f.passwords.write({rollbackOnly:'existing24password'});await f.devices.write({rollbackOnly:'existing24rememberedDevice'});
 const before=[f.accountStore.value,f.passwords.value,f.devices.value],counts=[f.accountStore.writes,f.passwords.writes,f.devices.writes];
 const gate=await createStandaloneGate(f.options);assert.deepEqual(gate.identity,old.identity);await gate.authorize();await gate.action('lock');assert.equal((await gate.info()).phase,'windows_locked');
 await gate.local.resume();await gate.authorize();await gate.local.forget();
 assert.deepEqual([f.accountStore.value,f.passwords.value,f.devices.value],before);assert.deepEqual([f.accountStore.writes,f.passwords.writes,f.devices.writes],counts);assert.equal(f.devices.deletes,0);
});
test('Windows mode requires its explicit trusted provider and distinct protected store',async()=>{
 const f=fixture();await assert.rejects(createStandaloneGate({...f.options,windowsSessionProvider:undefined}),/Protected Windows/);await assert.rejects(createStandaloneGate({...f.options,windowsStore:undefined}),/Protected Windows/);await assert.rejects(createStandaloneGate({...f.options,authentication:'automatic'}),/Protected Windows/);assert.equal(f.accountStore.value,null);
});
test('a locked Windows session cannot be resumed by info, authorization or renderer credentials',async()=>{
 const f=fixture();f.observed={...f.observed,locked:true};const gate=await createStandaloneGate(f.options);
 assert.equal((await gate.info()).phase,'windows_locked');assert.equal(f.windowsStore.value,null);assert.equal(await gate.local.resume(),null);
 f.observed={...f.observed,locked:false};assert.equal((await gate.info()).phase,'windows_locked');await assert.rejects(gate.authorize(),/Unlock Windows/);
 await assert.rejects(gate.action('unlock',{userSid:SID,accountName:f.observed.accountName}),/does not accept/);
 await gate.local.resume();assert.equal((await gate.info()).phase,'ready');
 gate.local.lock();await assert.rejects(gate.authorize(),/Unlock Windows/);assert.equal((await gate.info()).phase,'windows_locked');
});
test('native probe errors fail closed without falling back to an old password/device record',async()=>{
 const f=fixture();await f.devices.write({previouslyRemembered:true});f.observed=new Error('native fixture failure');const gate=await createStandaloneGate(f.options);
 assert.equal((await gate.info()).phase,'windows_unavailable');await assert.rejects(gate.authorize(),/native fixture failure/);assert.equal(f.windowsStore.value,null);assert.equal(f.devices.reads,0);assert.equal(f.passwords.reads,0);
});
test('Windows SID changes are refused while account renames with the same SID are accepted',async()=>{
 const f=fixture(),gate=await createStandaloneGate(f.options);await gate.authorize();const binding=f.windowsStore.value;
 gate.local.lock();f.observed={...f.observed,accountName:'RENAMED\\Same User',sessionId:3};await gate.local.resume();assert.equal((await gate.info()).windowsAccountDisplayName,'RENAMED\\Same User');assert.deepEqual(f.windowsStore.value,binding);
 gate.local.lock();f.observed={...f.observed,userSid:'S-1-5-21-100-200-300-9999'};await assert.rejects(gate.local.resume(),/another Windows user/);await assert.rejects(gate.authorize(),/Unlock Windows/);assert.deepEqual(f.windowsStore.value,binding);
});
test('foreign or malformed protected Windows bindings cannot reset to the current account',async()=>{
 for(const mutate of [value=>({...value,unexpected:true}),value=>({...value,identity:{...value.identity,appId:'mentat'}}),value=>({...value,identity:{...value.identity,deviceId:'22222222-2222-4222-8222-222222222222'}})]){
  const f=fixture(),gate=await createStandaloneGate(f.options);await gate.authorize();await f.windowsStore.write(mutate(f.windowsStore.value));const damaged=f.windowsStore.value;gate.local.lock();await assert.rejects(gate.local.resume(),/another Windows user/);assert.deepEqual(f.windowsStore.value,damaged);
 }
});
test('an in-flight native probe cannot undo a later Windows lock',async()=>{
 const f=fixture();let release;f.options.windowsSessionProvider=()=>new Promise(resolve=>{release=resolve;});const gate=await createStandaloneGate(f.options),pending=gate.info();
 while(!release)await new Promise(resolve=>setImmediate(resolve));gate.local.lock();release(f.observed);
 assert.equal((await pending).phase,'windows_locked');assert.equal(gate.session,null);assert.equal(f.windowsStore.value,null);
});
test('simultaneous initial access checks share one native probe and one session',async()=>{
 const f=fixture(),gate=await createStandaloneGate(f.options);const [first,second]=await Promise.all([gate.authorize(),gate.authorize()]);assert.equal(first.session,second.session);assert.equal(f.probes,1);assert.equal(f.windowsStore.writes,1);
});
test('an explicit OS resume rechecks Windows even if the preceding lock notification was missed',async()=>{
 const f=fixture(),gate=await createStandaloneGate(f.options);await gate.authorize();assert.equal(f.probes,1);
 f.observed={...f.observed,locked:true};assert.equal(await gate.local.resume(),null);assert.equal(f.probes,2);assert.equal(gate.session,null);await assert.rejects(gate.authorize(),/Unlock Windows/);
 f.observed={...f.observed,locked:false};await gate.local.resume();assert.equal(f.probes,3);assert.equal((await gate.authorize()).session.method,'windows-session');
});
test('native identity input must have only validated token/session fields',()=>{
 const f=fixture();for(const changed of [{userSid:'from-environment'},{accountName:'name\nforged'},{locked:'false'},{sessionId:0},{sessionId:-1},{role:'owner'},{schemaVersion:2}])assert.throws(()=>checkedWindowsIdentity({...f.observed,...changed}),/could not be verified/);
});
