'use strict';
// Actual Runtime and private binding; generated programme/data and fake child.
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os'),crypto=require('node:crypto'),vm=require('node:vm'),{createRequire}=require('node:module'),{EventEmitter}=require('node:events'),{Writable,PassThrough}=require('node:stream');
const native=require('../module-data-runtime-boundary.cjs'),failure=require('../startup-failure.cjs'),{canonical}=require('../access-client.cjs'),{ROLES}=require('../github-district-protocol.cjs');
function fixture(t,mode='success'){
 const temporary=fs.realpathSync.native(fs.mkdtempSync(path.join(os.tmpdir(),'district-runtime-wiring-'))),resources=path.join(temporary,'installed'),profile=path.join(temporary,'profile'),workspace=path.join(temporary,'workspace'),cache=path.join(profile,'packs'),data=path.join(cache,'github-districts','datasets-v2','a'.repeat(64),'co-05'),source=path.join(resources,'sources'),bootstrap=path.join(resources,'bootstrap');
 for(const directory of [source,bootstrap,profile,workspace,data])fs.mkdirSync(directory,{recursive:true});
 fs.writeFileSync(path.join(source,'app.py'),'# generated programme');fs.writeFileSync(path.join(bootstrap,'desktop_backend.py'),'# generated bootstrap');
 const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex'),programFiles=[['source',source,'app.py'],['bootstrap',bootstrap,'desktop_backend.py']].map(([root,base,name])=>{const raw=fs.readFileSync(path.join(base,name));return{root,path:name,bytes:raw.length,sha256:sha(raw)};}),contract={programFiles,programFingerprint:native.programFingerprint(programFiles)};
 const verify=runtime=>{try{native.verifyProgram(runtime,contract);return contract;}catch{throw failure.programFailure();}};
 const command={binary:path.join(resources,'python.exe'),runtime:resources,args:['generated-bootstrap']},moduleFile=path.resolve(__dirname,'../district-runtime-input.cjs'),real=createRequire(moduleFile),privateModule={exports:{}};
 const probe={...real('./district-data-probe.cjs'),verifyDistrictProgram:verify},backend={backendCommand:()=>command,backendEnvironment:()=>({})};
 vm.runInNewContext(fs.readFileSync(moduleFile,'utf8'),{module:privateModule,require:name=>name==='./district-data-probe.cjs'?probe:name==='./backend-command.cjs'?backend:name==='node:http'?http:real(name),Buffer,URL,structuredClone,setTimeout,clearTimeout},{filename:moduleFile});const input=privateModule.exports;
 let runtime,child,frame,phase='prepared',nativeCommits=0,journalCommits=0,closed=0,authorization=true,journalFailure=mode==='journal-storage';
 const snapshotId='co-cd005-123456abcdef',files=[...ROLES,'snapshots/'+snapshotId+'/manifest.json'].sort().map(role=>{const file=path.join(data,role);fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,'{}');return{role,path:'co-05/data/'+role,bytes:2,sha256:sha(Buffer.from('{}'))};}),before=fs.statSync(path.join(data,'density.json')).mtimeMs;
 const http={get(url,options,ready){const request=new EventEmitter();request.destroy=()=>request.emit('error',new Error('closed'));queueMicrotask(()=>{const response=new EventEmitter();response.statusCode=200;response.destroy=()=>{};ready(response);const fields=Object.fromEntries(['schemaVersion','appId','launchNonce','programFingerprint','sourceDigest','district','rootsDigest'].map(name=>[name,frame[name]]));if(mode==='mutation'&&phase==='prepared')fs.writeFileSync(path.join(data,'density.json'),'changed');response.emit('data',JSON.stringify({appId:'terrier',pid:child.pid,districtData:{...fields,phase,snapshot:snapshotId}}));response.emit('end');});return request;},
  request(url,options,ready){assert.equal(new URL(url).pathname,'/__desktop/district-commit');assert.equal(options.headers['X-Desktop-District-Commit'],frame.commitToken);const request=new EventEmitter();request.setTimeout=()=>{};request.destroy=error=>request.emit('error',error);request.end=()=>queueMicrotask(()=>{
   if(mode==='native-storage'){const value={schemaVersion:1,appId:'terrier',launchNonce:frame.launchNonce,programFingerprint:frame.programFingerprint,sourceDigests:{district:frame.sourceDigest},reason:'storage'};child.stdout.end('DESKTOP_DATA_BLOCKED '+canonical(value)+'\n');child.exitCode=1;child.emit('exit',1);child.emit('close',1);request.emit('error',new Error('socket closed'));return;}
   if(mode==='locked')authorization=false;else{nativeCommits++;phase='active';}const response=new EventEmitter();response.resume=()=>{};response.statusCode=mode==='locked'?403:204;ready(response);response.emit('end');});return request;}};
 const runtimeFile=path.resolve(__dirname,'../runtime.cjs'),runtimeReal=createRequire(runtimeFile),runtimeModule={exports:{}},dependencies={
  './backend-command.cjs':backend,'./district-runtime-input.cjs':input,'./district-data-probe.cjs':probe,'node:http':http,
  'node:net':{createServer(){const server=new EventEmitter();server.listen=(_p,_h,ready)=>queueMicrotask(ready);server.address=()=>({port:43218});server.close=ready=>ready();return server;}},
  'node:child_process':{spawn(binary){const process=new EventEmitter();process.pid=binary==='taskkill.exe'?81:72;process.exitCode=null;process.kill=()=>{};
   if(binary==='taskkill.exe'){queueMicrotask(()=>{child.exitCode=0;child.stdout.end();child.emit('exit',0);child.emit('close',0);process.emit('exit',0);});return process;}
   child=process;child.stdout=new PassThrough();child.stdin=new Writable({write(bytes,_encoding,done){const raw=Buffer.from(bytes);frame=JSON.parse(raw.subarray(4));done();}});return child;}}
 };
 vm.runInNewContext(fs.readFileSync(runtimeFile,'utf8'),{module:runtimeModule,require:name=>dependencies[name]||runtimeReal(name),process:{platform:'win32'},structuredClone,URL,setTimeout,clearTimeout},{filename:runtimeFile});
 const identity={schemaVersion:1,appId:'terrier',deviceId:crypto.randomUUID(),accountId:crypto.randomUUID(),accountIdentity:'synthetic_owner'};
 runtime=new runtimeModule.exports.Runtime('terrier',profile,resources,{allowStandalone:true,districtInputRequired:true,authorize:async()=>{if(!authorization)throw new Error('synthetic locked session');return{mode:'standalone',identity,session:null,principal:{mode:'standalone',districtId:'co-05'}};}});
 const configuration={dataDirectory:workspace,district:'co-05',standaloneGitHubData:{schemaVersion:2,district:'co-05',cacheRoot:cache,catalogueSha256:'a'.repeat(64)}};
 const bind=()=>input.bindDistrictConfiguration(configuration,{profile,directory:data,district:'co-05',files,verify:async()=>{if(fs.statSync(path.join(data,'density.json')).mtimeMs!==before||fs.statSync(path.join(data,'density.json')).size!==2)throw failure.dataStartupFailure({reason:'integrity'});},commit:async()=>{if(journalFailure)throw failure.dataStartupFailure({reason:'storage'});journalCommits++;},close:async()=>{closed++;}});bind();
 t.after(async()=>{await runtime.stop();await input.discardDistrictConfiguration(configuration);await new Promise(resolve=>setImmediate(resolve));await fs.promises.rm(temporary,{recursive:true,force:true,maxRetries:5,retryDelay:20});});
 return {runtime,configuration,retry(){journalFailure=false;phase='prepared';bind();},get frame(){return frame;},get nativeCommits(){return nativeCommits;},get journalCommits(){return journalCommits;},get closed(){return closed;}};
}
test('real Runtime requires prepared candidate health, private native commit and actual active health before its journal',async t=>{
 const f=fixture(t);assert.equal(await f.runtime.start(f.configuration),'http://127.0.0.1:43218');assert.equal(f.nativeCommits,1);assert.equal(f.journalCommits,1);assert.equal(f.closed,1);assert.equal(f.runtime.originalConfiguration().commitToken,undefined);assert.equal(f.frame.appId,'terrier');
});
for(const mode of ['mutation','native-storage','journal-storage'])test('real Runtime '+mode+' defers dataset failure, stops only its child and never confirms protected activation',async t=>{
 const f=fixture(t,mode);await assert.rejects(f.runtime.start(f.configuration),error=>failure.isDataStartupFailure(error));assert.equal(f.journalCommits,0);assert.equal(f.runtime.child,null);assert.equal(f.closed,1);if(mode==='mutation')assert.equal(f.nativeCommits,0);if(mode==='journal-storage')assert.equal(f.nativeCommits,1,'Native/JS partial commit remains truthful');
});
test('lock during private native commit pauses access and preserves unconfirmed state',async t=>{
 const f=fixture(t,'locked');await assert.rejects(f.runtime.start(f.configuration),{code:'authorization'});assert.equal(f.journalCommits,0);assert.equal(f.runtime.child,null);assert.equal(f.closed,1);
});
test('native partial commit is freshly prepared and reconciled after protected journal storage recovers',async t=>{
 const f=fixture(t,'journal-storage');await assert.rejects(f.runtime.start(f.configuration),error=>failure.isDataStartupFailure(error));
 const previous={...f.frame};assert.equal(f.nativeCommits,1);assert.equal(f.journalCommits,0);assert.equal(f.runtime.originalConfiguration(),null);assert.equal(f.runtime.child,null);
 f.retry();assert.equal(await f.runtime.start(f.configuration),'http://127.0.0.1:43218');assert.equal(f.nativeCommits,2);assert.equal(f.journalCommits,1);assert.equal(f.closed,2);
 assert.notEqual(f.frame.launchNonce,previous.launchNonce);assert.notEqual(f.frame.commitToken,previous.commitToken);assert.equal(f.frame.sourceDigest,previous.sourceDigest);assert.equal(f.frame.programFingerprint,previous.programFingerprint);
});
