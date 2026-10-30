'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {createRequire}=require('node:module');
function store(initial=null){let value=structuredClone(initial);return {read:async()=>structuredClone(value),write:async(...args)=>{value=structuredClone(args.at(-1));},delete:async()=>{value=null;},get value(){return structuredClone(value);}};}
function fixture({failure=false}={}){
 const identity={schemaVersion:1,appId:'melange',deviceId:'11111111-1111-4111-8111-111111111111',accountId:'22222222-2222-4222-8222-222222222222',accountIdentity:'existing24account'};
 const stores={accountStore:store({schemaVersion:1,purpose:'desktop-local-account',identity}),passwords:store(),devices:store(),windowsStore:store()},calls=[];
 const file=path.join(__dirname,'..','standalone-bootstrap.cjs'),native=createRequire(file),module={exports:{}};
 const dependencies={
  './access-state.cjs':{accessStateStore:({kind})=>{calls.push('store:'+kind);assert.equal(kind,'identity','existing24 account must not consult remote approval');return store({schemaVersion:1,appId:'melange',deviceId:identity.deviceId,platform:'win32',arch:'x64'});}},
  './access-bootstrap.cjs':{exactIdentity:native('./access-bootstrap.cjs').exactIdentity,bootstrapAccess:async()=>assert.fail('remote bootstrap was consulted')},
  './standalone-state.cjs':{protectedLocalStores:()=>stores},
  './windows-session.cjs':{windowsSession:async(resources,appId)=>{calls.push('native-windows');assert.equal(resources,'private-runtime');assert.equal(appId,'melange');if(failure)throw new Error('Native Windows identity unavailable');return {schemaVersion:1,userSid:'S-1-5-21-100-200-300-1001',accountName:'FIXTURE\\Current Windows User',sessionId:2,locked:false};}},
 };
 vm.runInNewContext(fs.readFileSync(file,'utf8'),{module,require:name=>Object.hasOwn(dependencies,name)?dependencies[name]:native(name),process:{platform:'win32',arch:'x64'}},{filename:file});
 return {calls,stores,identity,run:authentication=>module.exports.bootstrapStandalone({resources:'private-runtime',appId:'melange',profile:'private-profile',configuration:()=>({}),packaged:true,safeStorage:{},authentication})};
}
test('explicit Windows build bootstraps actual native sign-in without modifying existing24 account',async()=>{
 const f=fixture(),before=f.stores.accountStore.value,gate=await f.run('windows');assert.equal((await gate.info()).phase,'ready');assert.equal((await gate.authorize()).session.method,'windows-session');assert.deepEqual(gate.identity,f.identity);assert.deepEqual(f.stores.accountStore.value,before);assert.deepEqual(f.calls,['store:identity','native-windows']);
});
test('default and explicit password bootstrap do not consult Windows authentication',async()=>{
 for(const mode of [undefined,'password']){const f=fixture(),gate=await f.run(mode);assert.equal((await gate.info()).phase,'needs_password');assert.equal((await gate.info()).authentication,'local-password');assert.deepEqual(f.calls,['store:identity']);assert.equal(f.stores.windowsStore.value,null);}
});
test('Windows helper failure remains unavailable without falling back to password/approval bootstrap',async()=>{
 const f=fixture({failure:true}),gate=await f.run('windows');const info=await gate.info();assert.equal(info.phase,'windows_unavailable');assert.equal(info.authentication,'windows');assert.equal('windowsAccountDisplayName' in info,false);await assert.rejects(gate.authorize(),/Native Windows identity unavailable/);assert.equal(f.stores.windowsStore.value,null);assert.deepEqual(f.calls,['store:identity','native-windows','native-windows']);
});
test('unknown authentication build mode is refused before state or identity lookup',async()=>{
 const f=fixture();await assert.rejects(f.run('environment-user'),/Unsupported local authentication/);assert.deepEqual(f.calls,[]);
});
