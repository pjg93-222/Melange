"use strict";
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {EventEmitter}=require('node:events'),{Writable}=require('node:stream'),{createRequire}=require('node:module');
const {canonical}=require('../access-client.cjs'),native=require('../module-data-runtime-boundary.cjs');
const {ModuleDataStartup,compiledApplicationContract}=require('../module-data-startup.cjs');
const {GitHubModules}=require('../github-modules.cjs');
const {environment,signed,sha}=require('./fixtures/github-module-fixture.cjs');
const mainFile=path.join(__dirname,'..','main.cjs'),main=fs.readFileSync(mainFile,'utf8');

test('paired program verification scans the shared program once per phase and rechecks after a yield',async t=>{
 const f=fixture(t,{workspace:true}),files=[path.join(f.sources,'app.py'),path.join(f.bootstrap,'desktop_backend.py')],reads=[];
 const open=fs.openSync;t.mock.method(fs,'openSync',function(file,...args){if(files.includes(file))reads.push(file);return open.call(this,file,...args);});
 assert.equal(f.startup.boundary.supportsContracts(f.contract,f.workspaceContract),true);assert.deepEqual(reads.sort(),[...files].sort());
 await Promise.resolve();fs.appendFileSync(files[0],'# changed after the first verification');
 assert.equal(f.startup.boundary.supportsContracts(f.contract,f.workspaceContract),false);
});

test('paired program verification refuses a changed workspace table despite a reused fingerprint',t=>{
 const f=fixture(t,{workspace:true}),workspaceContract={...f.workspaceContract,programFiles:structuredClone(f.workspaceContract.programFiles)};
 const boundary=native.createRuntimeWorkspaceBoundary({appId:'mentat',profile:f.data.profile,publicKeys:f.data.remote.publicKeys,publicContract:f.contract,workspaceContract,
  getRuntime:()=>f.runtime,getSelected:()=>f.selected,authorize:f.data.options.authorize});
 assert.equal(boundary.supportsContracts(f.contract,workspaceContract),true);workspaceContract.programFiles[0].sha256='0'.repeat(64);
 assert.equal(boundary.supportsContracts(f.contract,workspaceContract),false);
});

for(const appId of ['melange','mentat'])test(appId+' actual main workspace factory sends only the opaque paired frame and confirms both native digests',async t=>{
 const f=fixture(t,{appId,workspace:true});const origin=await f.startup.start(f.selected,await f.data.options.authorize());
 assert.equal(origin,f.runtime.origin);assert.deepEqual(Object.keys(f.frame).sort(),['publicInput','schemaVersion','workspaceInput']);
 assert.equal(f.frame.schemaVersion,1);assert.equal(f.frame.publicInput.launchNonce,f.frame.workspaceInput.launchNonce);
 assert.equal(f.frame.publicInput.programFingerprint,f.frame.workspaceInput.programFingerprint);
 assert.equal(f.frame.workspaceInput.contractId,appId+'.workspace.v1');assert.notEqual(f.frame.publicInput.source.cacheRoot,f.frame.workspaceInput.source.cacheRoot);
 assert.ok(f.spawned[0].args.includes('--desktop-workspace-input'));assert.ok(!f.spawned[0].args.includes('--desktop-module-input'));
 assert.ok(f.data.journal.active);assert.ok(f.workspaceData.journal.active);assert.deepEqual(f.runtime.originalConfiguration(),f.selected);
 assert.equal(f.runtime.originalConfiguration().ownerGitHubWorkspaceData,undefined);
});

test('actual dual Runtime refuses mismatched workspace health before either active journal is committed',async t=>{
 const f=fixture(t,{workspace:true,healthChange:value=>{value.workspaceData.sourceDigest='0'.repeat(64);}});
 await assert.rejects(f.startup.start(f.selected,await f.data.options.authorize()));assert.equal(f.data.journal.active,null);assert.equal(f.workspaceData.journal.active,null);assert.equal(f.runtime.child,null);
});

test('actual dual native intake rejects data with both source digests without accepting either journal',async t=>{
 const {PassThrough}=require('node:stream'),{isDataStartupFailure}=require('../startup-failure.cjs');let child;
 const f=fixture(t,{workspace:true,onSpawn:({child:value})=>{child=value;child.stdout=new PassThrough();},onPipe:({frame})=>queueMicrotask(()=>{
  const input=frame.publicInput;child.stdout.end('DESKTOP_DATA_BLOCKED '+canonical({schemaVersion:1,appId:'mentat',launchNonce:input.launchNonce,programFingerprint:input.programFingerprint,sourceDigests:{public:input.binding.sourceDigest,workspace:frame.workspaceInput.binding.sourceDigest},reason:'integrity'})+'\n');
  child.exitCode=1;child.emit('exit',1);child.emit('close',1);
 })});
 await assert.rejects(f.startup.start(f.selected,await f.data.options.authorize()),error=>isDataStartupFailure(error)&&error.dataReason==='integrity');
 assert.equal(f.data.journal.active,null);assert.equal(f.workspaceData.journal.active,null);
});
for(const absent of [false,true])test(`Mentat with ${absent?'no workspace key':'an empty workspace config (builder output)'} starts after only the public prepare, with no workspace binding`,async t=>{
 const f=fixture(t,{appId:'mentat',noWorkspaceKey:absent}),original=structuredClone(f.selected);
 assert.equal(f.context.applicationConfig.desktopWorkspaceData?.mentat,undefined);
 assert.equal(f.startup.constructor.name,'ModuleDataStartup');assert.equal(f.startup.supported,true);
 const origin=await f.startup.start(f.selected,await f.data.options.authorize());assert.equal(origin,f.runtime.origin);
 assert.equal(f.requested.some(name=>/workspace/.test(name)),false,'No workspace startup, contract or provider is ever loaded');
 assert.equal(f.data.journal.active.catalogSequence,1,'The public channel prepared and committed');
 assert.equal(f.spawned.length,1);const args=f.spawned[0].args;assert.ok(args.includes('--desktop-module-input'));assert.equal(args.includes('--desktop-workspace-input'),false);
 assert.equal(Object.hasOwn(f.frame,'workspaceInput')||Object.hasOwn(f.frame,'publicInput'),false,'The backend input is the plain public frame');
 assert.equal(Object.hasOwn(f.frame,'workspaceBinding'),false);assert.ok(f.frame.binding&&f.frame.launchNonce);
 assert.ok(f.calls.indexOf('preparing')<f.calls.indexOf('spawn'));assert.ok(f.calls.indexOf('pipe')<f.calls.indexOf('health'));
 assert.equal(await f.runtime.verifyModuleHealth(f.frame.binding),true);assert.deepEqual(f.selected,original);
 assert.equal(f.runtime.child!==null,true);
});
function fixture(t,{appId='mentat',healthChange=null,onPipe=null,onSpawn=null,rendererFactory=null,beforeConstruct=null,workspace=false,noWorkspaceKey=false}={}){
 const data=environment(appId),resources=path.join(data.temporary,'installed'),sources=path.join(resources,'sources'),bootstrap=path.join(resources,'bootstrap');
 fs.mkdirSync(sources,{recursive:true});fs.mkdirSync(bootstrap);fs.writeFileSync(path.join(sources,'app.py'),'# Generated fixture consumer\n');fs.writeFileSync(path.join(bootstrap,'desktop_backend.py'),'# Generated fixture bootstrap\n');
 const programFiles=[['source','app.py',sources],['bootstrap','desktop_backend.py',bootstrap]].map(([root,name,base])=>{const raw=fs.readFileSync(path.join(base,name));return{root,path:name,bytes:raw.length,sha256:sha(raw)};});
 const contract={schemaVersion:1,appId,contractId:appId+'.native-fixture.v1',programFiles,programFingerprint:native.programFingerprint(programFiles),startupTimeoutMs:1000,
  requiredKinds:Object.keys(data.remote.registry),registry:data.remote.registry,publicReaders:['fixture.public-reader'],privateBoundaries:['original.workspace','original.state']};
 const workspaceData=workspace?environment(appId):null;
 if(workspaceData){const remote=signed(appId,{keys:data.remote.keys});remote.value.purpose=appId+'-full-workspace-data';remote.manifest.purpose=remote.value.purpose+'sets';remote.rebind();workspaceData.remote=remote;}
 const workspaceContract=workspace?{...contract,contractId:appId+'.workspace.v1',registry:workspaceData.remote.registry,publicReaders:['fixture.workspace-reader']}:null;
 const calls=[],spawned=[],messages=[],requested=[];let selected=data.selected,frame,child,runtime;
 const runtimeFile=path.join(__dirname,'..','runtime.cjs'),realRequire=createRequire(runtimeFile),module={exports:{}};
 const dependencies={
  './backend-command.cjs':{backendCommand:()=>({binary:path.join(resources,'python.exe'),runtime:resources,args:['synthetic-bootstrap']}),backendEnvironment:()=>({})},
  'node:net':{createServer(){const server=new EventEmitter();server.listen=(_p,_h,ready)=>queueMicrotask(ready);server.address=()=>({port:43212});server.close=ready=>ready();return server;}},
  'node:http':{get(url,options,ready){const request=new EventEmitter();request.destroy=()=>request.emit('error',new Error('closed'));
   queueMicrotask(()=>{calls.push('health');assert.equal(options.headers['X-Desktop-Token'],runtime.token);assert.equal(url,runtime.origin+'/__desktop/health');
    const response=new EventEmitter();response.statusCode=200;response.destroy=()=>{};ready(response);
    const publicFrame=frame?.publicInput||frame,workspaceFrame=frame?.workspaceInput;
    const installed=(input,spec)=>({schemaVersion:1,...input.binding,launchNonce:input.launchNonce,coverageDigest:sha(Buffer.from(canonical({publicReaders:[...spec.publicReaders].sort(),privateBoundaries:[...spec.privateBoundaries].sort()})))});
    const value={appId,pid:child.pid,launchPath:'/',moduleData:publicFrame?installed(publicFrame,contract):undefined,...(workspaceFrame?{workspaceData:installed(workspaceFrame,workspaceContract)}:{})};
    if(healthChange)healthChange(value,{child,calls,runtime,frame});response.emit('data',JSON.stringify(value));response.emit('end');});return request;}},
  'node:child_process':{spawn(binary,args,options){calls.push(binary==='taskkill.exe'?'kill':'spawn');const proc=new EventEmitter();proc.pid=543210;proc.exitCode=null;proc.kill=()=>{};
   if(binary==='taskkill.exe'){queueMicrotask(()=>{child.exitCode=0;child.emit('exit',0);proc.emit('exit',0);});return proc;}
   child=proc;spawned.push({binary,args,options,child});if(onSpawn)onSpawn({data,child:proc,setSelected:value=>{selected=value;}});
   const chunks=[];proc.stdin=new Writable({write(chunk,_encoding,done){chunks.push(Buffer.from(chunk));done();},final(done){const raw=Buffer.concat(chunks);assert.equal(raw.readUInt32BE(),raw.length-4);frame=JSON.parse(raw.subarray(4).toString('utf8'));calls.push('pipe');if(onPipe)onPipe({data,runtime,frame,setSelected:value=>{selected=value;}});done();}});return proc;}}
 };
 vm.runInNewContext(fs.readFileSync(runtimeFile,'utf8'),{module,require:name=>Object.hasOwn(dependencies,name)?dependencies[name]:realRequire(name),structuredClone,process:{platform:'win32'},URL,setTimeout,clearTimeout},{filename:runtimeFile});
 runtime=new module.exports.Runtime(appId,data.profile,resources,{authorize:data.options.authorize,rendererFactory});
 const context={standaloneMode:false,definition:{id:appId},userData:data.profile,runtime,resources,refuseModuleDataSettings:module.exports.refuseModuleDataSettings,applicationConfig:{...(noWorkspaceKey?{}:{desktopWorkspaceData:workspace?{[appId]:'workspace-v1'}:{}}),desktopAccessTrust:{updatePublicKeysByApp:{[appId]:data.remote.publicKeys}}},app:{getAppPath:()=>resources},path,process:{execPath:path.join(resources,'desktop.exe')},
  updateStatus:message=>{assert.equal(message,workspace?'Opening your workspace from verified GitHub data.':'Preparing reviewed public data. Larger sources can take several minutes.');calls.push('preparing');},loadingStatus:async()=>{},readerDiagnostic:()=>{},read:()=>selected,ensureAccess:async()=>({authorize:data.options.authorize}),accessLifecycle:{generation:0,suspended:false},askingClose:false,closing:false,
  window:{isDestroyed:()=>false,webContents:{send:(_name,state)=>messages.push(state)}},powerSaveBlocker:{start:()=>1,stop(){}},
  require:name=>{requested.push(name);
   if(name==='./module-data-startup.cjs')return{ModuleDataStartup,withCompiledApplicationContract:(_appId,_context,construct)=>native.withVerifiedProgramConstruction(runtime,contract,proof=>construct(proof?contract:null,proof||undefined)),withCompiledWorkspaceApplicationContract:(_appId,_context,construct)=>native.withVerifiedProgramConstruction(runtime,workspaceContract,proof=>construct(proof?workspaceContract:null,proof||undefined))};
   if(name==='./workspace-data-startup.cjs')return require('../workspace-data-startup.cjs');
   if(name==='./workspace-data-contract.cjs')return require('../workspace-data-contract.cjs');
   if(name==='./github-module-transport.cjs')return require('../github-module-transport.cjs');
   if(name==='./module-data-runtime-boundary.cjs')return native;
   if(name==='./github-modules.cjs')return{GitHubModules:class extends GitHubModules{constructor(options){const item=options.channel==='workspace-v1'?workspaceData:data;super({...options,cacheRoot:options.channel==='workspace-v1'?path.join(data.profile,'packs','github-workspace-data'):data.options.cacheRoot,transport:item.transport,store:item.store,minimumFreeBytes:0});}}};
   if(name==='./access-state.cjs')return{accessStateStore:()=>data.store};throw new Error('Unexpected factory dependency '+name);
  }};
 const start=main.indexOf('function createModuleDataStartup()'),end=main.indexOf("\napp.on('second-instance'",start);assert.ok(start>=0&&end>start);vm.runInNewContext(main.slice(start,end),context,{filename:mainFile});
 const constructionReads=[],open=fs.openSync;let startup;
 fs.openSync=function(file,...args){if(file===path.join(sources,'app.py')||file===path.join(bootstrap,'desktop_backend.py'))constructionReads.push(file);return open.call(this,file,...args);};
 try{beforeConstruct?.({sources,bootstrap});startup=context.createModuleDataStartup();}finally{fs.openSync=open;}
 t.after(async()=>{await startup.shutdown();await runtime.stop();workspaceData?.cleanup();data.cleanup();});
 return{data,workspaceData,contract,workspaceContract,runtime,startup,calls,spawned,messages,requested,context,sources,bootstrap,constructionReads,get frame(){return frame;},get selected(){return selected;},set selected(value){selected=value;}};
}
function constructionBoundary(f,proof,overrides={}){return native.createRuntimeModuleBoundary({appId:f.contract.appId,profile:f.data.profile,publicKeys:f.data.remote.publicKeys,
 contract:f.contract,getRuntime:()=>f.runtime,getSelected:()=>f.selected,authorize:f.data.options.authorize,constructionProof:proof,...overrides});}

for(const mutateProgram of [false,true])test('actual Runtime drains a typed intake diagnostic '+(mutateProgram?'but refuses it after program mutation':'before reporting external data blocked'),async t=>{
 const f=fixture(t,{onSpawn:({child})=>{child.stdout=new(require('node:stream').PassThrough)();},onPipe:({runtime,frame})=>{
  const child=runtime.child,value={schemaVersion:1,appId:frame.appId,launchNonce:frame.launchNonce,programFingerprint:frame.programFingerprint,sourceDigests:{public:frame.binding.sourceDigest},reason:'integrity'};
  if(mutateProgram)fs.appendFileSync(path.join(f.sources,'app.py'),'# changed during intake');
  child.exitCode=1;child.emit('exit',1);child.stdout.end(require('../startup-data-diagnostic.cjs').PREFIX+canonical(value)+'\n');
  queueMicrotask(()=>child.emit('close',1));
 }});
 const error=await f.startup.start(f.selected,await f.data.options.authorize()).catch(error=>error);
 assert.equal(require('../startup-failure.cjs').isDataStartupFailure(error),!mutateProgram,String(error?.stack));assert.equal(f.runtime.child,null);assert.equal(f.data.journal.active,null);
 if(!mutateProgram)assert.equal(error.retryable,false);
});

test('construction proof cannot be forged, cloned, replayed or used for another exact contract/runtime',t=>{
 const f=fixture(t);
 for(const proof of [{},Object.freeze({runtime:f.runtime,contract:f.contract})])assert.equal(constructionBoundary(f,proof).supportsContract(f.contract),false);
 let escaped;
 native.withVerifiedProgramConstruction(f.runtime,f.contract,proof=>{
  escaped=proof;
  assert.equal(constructionBoundary(f,structuredClone(proof)).supportsContract(f.contract),false);
  const other={};native.initializeModuleRuntime(other,()=>({source:f.sources,bootstrap:f.bootstrap}));
  assert.equal(constructionBoundary(f,proof,{getRuntime:()=>other}).supportsContract(f.contract),false);
  const copy={...f.contract};assert.equal(constructionBoundary(f,proof,{contract:copy}).supportsContract(copy),false);
  assert.equal(constructionBoundary(f,proof).supportsContract(f.contract),true);
  assert.equal(constructionBoundary(f,proof).supportsContract(f.contract),false);
 });
 assert.equal(constructionBoundary(f,escaped).supportsContract(f.contract),false);
});

test('construction proof expires on throw, thenable return and a queued microtask',async t=>{
 const f=fixture(t);let escaped,queued;
 let called=false;assert.throws(()=>native.withVerifiedProgramConstruction(f.runtime,f.contract,async()=>{called=true;}),/Native module/);assert.equal(called,false);
 assert.throws(()=>require('../module-data-startup.cjs').withCompiledApplicationContract('mentat',undefined,async()=>{called=true;}),/Module data/);assert.equal(called,false);
 assert.throws(()=>native.withVerifiedProgramConstruction(f.runtime,f.contract,proof=>{escaped=proof;throw new Error('fixture throw');}),/fixture throw/);
 assert.equal(constructionBoundary(f,escaped).supportsContract(f.contract),false);
 assert.throws(()=>native.withVerifiedProgramConstruction(f.runtime,f.contract,proof=>{escaped=proof;return Promise.resolve();}),/Native module/);
 assert.equal(constructionBoundary(f,escaped).supportsContract(f.contract),false);
 native.withVerifiedProgramConstruction(f.runtime,f.contract,proof=>{queued=new Promise(resolve=>queueMicrotask(()=>resolve(constructionBoundary(f,proof).supportsContract(f.contract))));});
 assert.equal(await queued,false);
});

test('construction proofs do not cross nested scopes or mutable program-root mappings',t=>{
 const f=fixture(t),other=fixture(t,{appId:'melange'});
 native.withVerifiedProgramConstruction(f.runtime,f.contract,first=>{
  native.withVerifiedProgramConstruction(other.runtime,other.contract,second=>{
   assert.equal(constructionBoundary(other,first).supportsContract(other.contract),false);
   assert.equal(constructionBoundary(f,second).supportsContract(f.contract),false);
   assert.equal(constructionBoundary(other,second).supportsContract(other.contract),true);
  });
  assert.equal(constructionBoundary(f,first).supportsContract(f.contract),true);
 });
 const changing={},roots={source:f.sources,bootstrap:f.bootstrap};native.initializeModuleRuntime(changing,()=>roots);
 native.withVerifiedProgramConstruction(changing,f.contract,proof=>{
  roots.source=other.sources;
  assert.equal(constructionBoundary(f,proof,{getRuntime:()=>changing}).supportsContract(f.contract),false);
 });
});

test('initial program corruption still leaves the main factory unsupported before provider work',t=>{
 const f=fixture(t,{beforeConstruct:({sources})=>fs.appendFileSync(path.join(sources,'app.py'),'# changed')});
 assert.equal(f.startup.supported,false);assert.deepEqual(f.data.requests,[]);assert.equal(f.data.journal,null);assert.equal(f.spawned.length,0);
});

test('same-size program tamper with restored mtime after construction is freshly refused before preparation',async t=>{
 const f=fixture(t),file=path.join(f.sources,'app.py'),before=fs.statSync(file),raw=fs.readFileSync(file);raw[2]^=1;
 fs.writeFileSync(file,raw);fs.utimesSync(file,before.atime,before.mtime);
 await assert.rejects(f.startup.start(f.selected,await f.data.options.authorize()));
 assert.equal(f.spawned.length,0);assert.equal(f.data.journal,null);assert.deepEqual(f.data.requests,[]);
});

test('program mutation after later runtime authorization is not covered by construction proof',async t=>{
 const f=fixture(t),authorize=f.runtime.authorize;
 f.runtime.authorize=async configuration=>{const approved=await authorize(configuration);fs.appendFileSync(path.join(f.sources,'app.py'),'# changed after authorization');return approved;};
 await assert.rejects(f.startup.start(f.selected,await f.data.options.authorize()));
 assert.equal(f.spawned.length,0);assert.equal(f.data.journal?.active,null);
});
for(const appId of ['melange','mentat'])test(`actual ${appId} main factory reaches native Runtime framing and only commits exact owned health`,async t=>{
 const f=fixture(t,{appId}),original=structuredClone(f.selected);assert.equal(f.startup.supported,true);
 assert.deepEqual(f.constructionReads.sort(),[path.join(f.sources,'app.py'),path.join(f.bootstrap,'desktop_backend.py')].sort(),'Construction hashes each program file once');
 const origin=await f.startup.start(f.selected,await f.data.options.authorize());assert.equal(origin,'http://127.0.0.1:43212');
 assert.equal(f.data.journal.active.catalogSequence,1);assert.equal(f.spawned.length,1);assert.equal(f.spawned[0].options.stdio[0],'pipe');
 const args=f.spawned[0].args;assert.equal(args[args.indexOf('--profile-root')+1],f.data.profile);assert.ok(args.includes('--desktop-module-input'));
 assert.equal(f.frame.profileRoot,f.data.profile);assert.equal(f.frame.originalDataRoot,f.data.original);assert.equal(f.frame.stateRoot,path.join(f.data.profile,'state'));
 assert.deepEqual(f.runtime.originalConfiguration(),original);assert.deepEqual(f.selected,original);assert.equal(Object.hasOwn(f.runtime.configuration,'ownerGitHubModuleData'),false);
 assert.ok(f.calls.indexOf('preparing')<f.calls.indexOf('spawn'));assert.ok(f.calls.indexOf('pipe')<f.calls.indexOf('health'));assert.equal(await f.runtime.verifyModuleHealth(f.frame.binding),true);
 const requests=f.data.requests.length,child=f.runtime.child;await f.startup.start(f.selected,await f.data.options.authorize());assert.equal(f.runtime.child,child);assert.equal(f.spawned.length,1);assert.equal(f.data.requests.length,requests,'Warm resume does not reacquire or commit an epoch');
 assert.equal(compiledApplicationContract(appId),null,'Generated native fixture never enables production registry');
});
for(const field of ['pid','launchNonce','coverageDigest','sourceDigest','sourceFingerprint','contractId','programFingerprint'])test(`native Runtime refuses ${field} from a healthy-looking unrelated response`,async t=>{
 const f=fixture(t,{healthChange(value,{child}){if(field==='pid')value.pid++;else value.moduleData[field]='0'.repeat(64);queueMicrotask(()=>{child.exitCode=1;child.emit('exit',1);});}});
 await assert.rejects(f.startup.start(f.selected,await f.data.options.authorize()));assert.equal(f.data.journal.active,null);assert.equal(f.runtime.child,null);
});
test('ordinary Runtime cannot consume a JSON-shaped capability before auth, mkdir or spawn',async t=>{
 const f=fixture(t);let auth=0;f.runtime.authorize=()=>{auth++;throw new Error('Not reached');};
 await assert.rejects(f.runtime.start(f.selected,{approved:true,contract:f.contract}));assert.equal(auth,0);assert.equal(f.spawned.length,0);assert.equal(fs.existsSync(path.join(f.data.profile,'state')),false);
});
test('compiled source mutation disables the actual main boundary before any provider or root preparation',async t=>{
 const f=fixture(t);fs.appendFileSync(path.join(f.sources,'app.py'),'# changed');
 await assert.rejects(f.startup.start(f.selected,await f.data.options.authorize()));assert.equal(f.spawned.length,0);assert.equal(f.data.journal,null);assert.deepEqual(f.data.requests,[]);assert.equal(fs.existsSync(path.join(f.data.profile,'state')),false);
});
test('selection change while pipe completes aborts the lease and tears down only its claimed child',async t=>{
 const f=fixture(t,{onPipe({data,setSelected}){setSelected({...data.selected,changed:true});}});
 await assert.rejects(f.startup.start(f.selected,await f.data.options.authorize()));assert.equal(f.data.journal.active,null);assert.equal(f.runtime.child,null);assert.ok(f.calls.includes('kill'));
});
test('pipe EOF rejects truncated or oversized native encoding and cancellation drains owned process',async()=>{
 assert.throws(()=>native.encodeModuleFrame({value:'x'.repeat(65536)}));
 const child=new EventEmitter();child.stdin=new Writable({write(_chunk,_encoding,done){setImmediate(done);}});const abort=new AbortController();
 const running=native.writeModuleFrame(child,native.encodeModuleFrame({fixture:true}),abort.signal);abort.abort();await assert.rejects(running);
});
test('program source table rejects alias paths, unknown fields and mismatched bytes/digest',()=>{
 const file={root:'source',path:'a.py',bytes:0,sha256:sha(Buffer.alloc(0))};
 for(const files of [[file,{...file,path:'A.py'}],[{...file,path:'../a.py'}],[{...file,path:'a.py.'}],[{...file,extra:true}],[{...file,bytes:16*1024**2+1}]])assert.throws(()=>native.programTable(files));
 assert.equal(native.programFingerprint([file]).length,64);
});


test('selection invalidation at spawn still claims and stops exactly the newly spawned child',async t=>{
 const f=fixture(t,{onSpawn({data,setSelected}){setSelected({...data.selected,changedDuringSpawn:true});}});
 await assert.rejects(f.startup.start(f.selected,await f.data.options.authorize()));assert.equal(f.runtime.child,null);assert.equal(f.data.journal.active,null);assert.equal(f.calls.filter(v=>v==='kill').length,1);
});


test('compiled native contract requires exact program table fingerprint and an explicit bounded startup budget',async t=>{
 const f=fixture(t),base={appId:'mentat',getSelected:()=>f.selected,getRuntime:()=>f.runtime,getGeneration:()=>0,authorize:f.data.options.authorize,createProvider:()=>assert.fail('No provider work')};
 for(const changes of [{startupTimeoutMs:undefined},{startupTimeoutMs:0},{startupTimeoutMs:600001},{startupTimeoutMs:NaN},{programFiles:[]},{programFingerprint:'0'.repeat(64)},{programFiles:[{...f.contract.programFiles[0],path:'../outside.py'}]}]){
  assert.throws(()=>new ModuleDataStartup({...base,contract:{...f.contract,...changes}}));
  assert.equal(native.createRuntimeModuleBoundary({appId:'mentat',profile:f.data.profile,contract:{...f.contract,...changes},getRuntime:()=>f.runtime,getSelected:()=>f.selected,authorize:f.data.options.authorize}),null);
 }
});
