'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os'),vm=require('node:vm');
const {EventEmitter}=require('node:events'),{createRequire}=require('node:module');
const {AccessLifecycle,authorizationIdentity}=require('../access-lifecycle.cjs');
const {OPTIONS}=require('../local-access.cjs');
function local(appId='melange'){
 const identity={schemaVersion:1,appId,deviceId:'11111111-1111-4111-8111-111111111111',accountId:'22222222-2222-4222-8222-222222222222',accountIdentity:'local_fixture'};
 return {mode:'standalone',identity,session:appId==='terrier'?null:{...identity,sessionId:'33333333-3333-4333-8333-333333333333',authenticatedAt:1800000000000,method:'local-password'},principal:appId==='terrier'?{mode:'standalone',districtId:'co-05'}:null};
}
function launcher(t,appId='melange'){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'standalone-integration-')),profile=path.join(root,'profile'),resources=path.join(root,'resources'),data=path.join(root,'data');for(const folder of [profile,resources,data])fs.mkdirSync(folder);
 const file=path.join(__dirname,'..','runtime.cjs'),native=createRequire(file),module={exports:{}},spawns=[],runtimes=[],children=[];
 const dependencies={
  'node:net':{createServer(){const server=new EventEmitter();server.listen=(_port,_host,ready)=>queueMicrotask(ready);server.address=()=>({port:43210});server.close=ready=>ready();return server;}},
  'node:http':{get(_url,_options,ready){const request=new EventEmitter();request.destroy=()=>{};queueMicrotask(()=>{const response=new EventEmitter();response.statusCode=200;response.destroy=()=>{};ready(response);response.emit('data',JSON.stringify({appId,launchPath:'/'}));response.emit('end');});return request;}},
  'node:child_process':{spawn(binary,args,options){const child=new EventEmitter();child.exitCode=null;child.pid=987654;child.kill=()=>{};spawns.push({binary,args:Array.from(args),options});children.push(child);return child;}},
  './backend-command.cjs':{backendCommand(){return {binary:path.join(resources,'python.exe'),runtime:resources,args:['synthetic-bootstrap']};},backendEnvironment:native('./backend-command.cjs').backendEnvironment},
 };
 vm.runInNewContext(fs.readFileSync(file,'utf8'),{module,require:name=>Object.hasOwn(dependencies,name)?dependencies[name]:native(name),structuredClone,process:{platform:'win32'},URL,setTimeout,clearTimeout},{filename:file});
 t.after(async()=>{for(const child of children){child.exitCode=0;child.emit('exit',0);}for(const runtime of runtimes)await runtime.stop();const resolved=path.resolve(root);if(path.dirname(resolved)!==path.resolve(os.tmpdir())||!path.basename(resolved).startsWith('standalone-integration-'))throw new Error('Unsafe fixture cleanup');fs.rmSync(resolved,{recursive:true,force:true});});
 return {spawns,configuration:{dataDirectory:data,...(appId==='terrier'?{district:'co-05'}:{})},make(options={}){const runtime=new module.exports.Runtime(appId,profile,resources,{authorize:async()=>local(appId),...options});runtimes.push(runtime);return runtime;}};
}
test('runtime requires explicit build opt-in and a matching authenticated local app',async t=>{
 const f=launcher(t);
 for(const options of [{},{allowStandalone:'true'},{allowStandalone:true,authorize:async()=>local('mentat')}])await assert.rejects(f.make(options).start(f.configuration),/Local authorization is unavailable/);
 await assert.rejects(f.make({allowStandalone:true,authorize:async()=>({...local(),session:null})}).start(f.configuration),/Local sign-in/);
 await assert.rejects(f.make({allowStandalone:true,authorize:async()=>({...local(),principal:{mode:'standalone',districtId:'co-05'}})}).start(f.configuration),/Local sign-in/);
 assert.equal(f.spawns.length,0);
});
for(const appId of ['melange','mentat'])test(`${appId} local runtime starts without manufacturing managed approval`,async t=>{
 const f=launcher(t,appId),runtime=f.make({allowStandalone:true});await runtime.start(f.configuration);
 assert.equal(f.spawns.length,1);assert.equal(runtime.authorization.mode,'standalone');assert.equal('accepted' in runtime.authorization,false);
 assert.equal(f.spawns[0].options.env.DESKTOP_ACCESS_PRINCIPAL,undefined);assert.equal(f.spawns[0].args.includes('--standalone'),false);
 assert.equal(typeof f.spawns[0].options.env.DESKTOP_LAUNCH_TOKEN,'string');
});
test('standalone Terrier strips any inherited managed principal and retains the native launch token',async t=>{
 const prior=process.env.DESKTOP_ACCESS_PRINCIPAL;process.env.DESKTOP_ACCESS_PRINCIPAL='synthetic-old-managed-principal';t.after(()=>{if(prior===undefined)delete process.env.DESKTOP_ACCESS_PRINCIPAL;else process.env.DESKTOP_ACCESS_PRINCIPAL=prior;});
 const f=launcher(t,'terrier'),runtime=f.make({allowStandalone:true});await runtime.start(f.configuration);
 assert.equal(f.spawns[0].args.includes('--standalone'),true);assert.equal(f.spawns[0].options.env.DESKTOP_ACCESS_PRINCIPAL,undefined);
 assert.equal(typeof f.spawns[0].options.env.DESKTOP_LAUNCH_TOKEN,'string');assert.deepEqual(runtime.authorization.principal,{mode:'standalone',districtId:'co-05'});
});
test('local lifecycle preserves lock and account binding without remote presence calls',async()=>{
 const approved=local(),runtime={definition:{id:'melange'},child:{pid:1},authorization:approved,requestsAllowed:true};let signedIn=true,hidden=false,shown=false;
 const gate={authorize:async()=>{if(!signedIn)throw new Error('Local sign-in required');return approved;},local:{lock:()=>{signedIn=false;}}};
 const life=new AccessLifecycle({runtime,gate,hide:()=>{hidden=true;},showBoundary:async()=>{shown=true;}});
 assert.equal(await life.authenticated(),true);await life.suspend('locked');assert.equal(runtime.requestsAllowed,false);assert.equal(await life.authenticated(),false);assert.ok(hidden&&shown);
 signedIn=true;await life.resume(approved);assert.equal(await life.canReveal(life.generation,approved),true);
 const other=structuredClone(approved);other.identity.accountId='55555555-5555-4555-8555-555555555555';other.session.accountId=other.identity.accountId;await assert.rejects(life.resume(other),/changing/);
 life.osLocked=true;await assert.rejects(life.resume(approved),/Unlock Windows/);
 assert.equal('serverId' in JSON.parse(authorizationIdentity(approved)),false);
});
test('standalone Terrier lifecycle still requires genuine backend sign-in after locking',async()=>{
 const approved=local('terrier'),runtime={definition:{id:'terrier'},child:{pid:1},authorization:approved,requestsAllowed:true};let backendSignedIn=false,logouts=0;
 const life=new AccessLifecycle({runtime,gate:{authorize:async()=>approved,local:{lock(){}}},hide(){},showBoundary:async()=>{},terrierAuthenticated:async()=>backendSignedIn,terrierLogout:async()=>{backendSignedIn=false;logouts++;return true;}});
 assert.equal(await life.authenticated(),false);backendSignedIn=true;assert.equal(await life.authenticated(),true);
 await life.suspend('locked');assert.equal(logouts,1);await assert.rejects(life.resume(approved),/Fresh Terrier password/);
 backendSignedIn=true;await life.resume(approved,{freshPassword:true});assert.equal(await life.authenticated(),true);assert.equal(approved.session,null);
});

function memory(value=null){let current=structuredClone(value);return {read:async()=>structuredClone(current),write:async(...args)=>{current=structuredClone(args.at(-1));},delete:async()=>{current=null;},get value(){return structuredClone(current);}};}
function bootstrapFixture({existing=false,staleDevice=false}={}){
 const deviceId=local().identity.deviceId,identity={schemaVersion:1,appId:'melange',deviceId,platform:'win32',arch:'x64'};
 const grant={appId:'melange',serverId:'99999999-9999-4999-8999-999999999999',deviceId,principalId:local().identity.accountId,accountIdentity:'legacy_local_fixture',grantId:'44444444-4444-4444-8444-444444444444',role:'local_user',districtIds:[]};
 const binding=Object.fromEntries(['serverId','deviceId','principalId','accountIdentity','appId','role','districtIds'].map(key=>[key,grant[key]]));
 const passwordRecord={schemaVersion:1,binding,algorithm:'scrypt',N:OPTIONS.N,r:OPTIONS.r,p:OPTIONS.p,salt:Buffer.alloc(32,1).toString('base64'),derivedKey:Buffer.alloc(64,2).toString('base64'),failures:2,blockedUntil:0,lastAttempt:1800000000000};
 const deviceBinding=Object.fromEntries(['serverId','deviceId','principalId','accountIdentity','appId','grantId'].map(key=>[key,grant[key]]));if(staleDevice)deviceBinding.grantId='55555555-5555-4555-8555-555555555555';
 const stores={accountStore:memory(existing?{schemaVersion:1,purpose:'desktop-local-account',identity:local().identity}:null),passwords:memory(),devices:memory()},oldIdentity=memory(identity),oldState=memory({grantEnvelope:{synthetic:'verified by injected verifier'}}),calls=[];
 const file=path.join(__dirname,'..','standalone-bootstrap.cjs'),native=createRequire(file),module={exports:{}};
 const dependencies={
  './access-state.cjs':{accessStateStore:({kind})=>{calls.push(kind);if(existing&&kind==='state')assert.fail('Initialized local mode must not reopen old managed state');return kind==='identity'?oldIdentity:oldState;}},
  './access-bootstrap.cjs':{exactIdentity:native('./access-bootstrap.cjs').exactIdentity,bootstrapAccess:async()=>{calls.push('offline-verified-migration');return {evidence:async()=>({grant,revoked:false}),passwords:{read:async()=>structuredClone(passwordRecord)},owner:async()=>null,client:{refresh:()=>assert.fail('No remote refresh'),poll:()=>assert.fail('No remote poll')}};}},
  './access-credentials.cjs':{deviceStore:()=>({read:async()=>({schemaVersion:1,binding:deviceBinding,verifiedAt:1800000000000})})},
  './standalone-state.cjs':{protectedLocalStores:()=>stores},
 };
 vm.runInNewContext(fs.readFileSync(file,'utf8'),{module,require:name=>Object.hasOwn(dependencies,name)?dependencies[name]:native(name),process:{platform:'win32',arch:'x64'}},{filename:file});
 return {run:()=>module.exports.bootstrapStandalone({resources:'synthetic',appId:'melange',profile:'synthetic',configuration:()=>({}),packaged:true,bundledTrust:{},safeStorage:{}}),stores,oldState,calls,passwordRecord};
}
test('bootstrap copies verified old password but discards stale remembered-device authority offline',async()=>{
 const f=bootstrapFixture({staleDevice:true}),old=structuredClone(f.oldState.value),gate=await f.run();
 assert.equal((await gate.info()).phase,'locked');assert.equal(f.stores.devices.value,null);assert.equal(f.stores.passwords.value.derivedKey,f.passwordRecord.derivedKey);assert.equal(f.stores.passwords.value.failures,2);assert.deepEqual(f.oldState.value,old);assert.ok(f.calls.includes('offline-verified-migration'));assert.equal('client' in gate,false);
});
test('initialized standalone bootstrap does not consult prior remote approval state',async()=>{
 const f=bootstrapFixture({existing:true}),gate=await f.run();assert.equal(gate.identity.accountId,local().identity.accountId);assert.deepEqual(f.calls,['identity']);
});
