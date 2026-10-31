"use strict";
const assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path'),vm=require('node:vm');
const {EventEmitter}=require('node:events'),{Writable,PassThrough}=require('node:stream'),{createRequire}=require('node:module');
const client=process.env.LIFECYCLE_BASELINE_ROOT||path.resolve(__dirname,'../..');
const realRequire=createRequire(path.join(client,'runtime.cjs'));
const {createStandaloneGate}=realRequire('./standalone-access.cjs');
function store(){let value=null;return {read:async()=>structuredClone(value),write:async(...args)=>{value=structuredClone(args.at(-1));},delete:async()=>{value=null;}};}
async function districtRuntime(t){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'district-warm-')),profile=path.join(root,'profile'),resources=path.join(root,'resources'),data=path.join(root,'data'),cacheRoot=path.join(profile,'packs'),sha='a'.repeat(64);
 const directory=path.join(cacheRoot,'github-districts','datasets-v2',sha,'co-05');
 for(const folder of [directory,path.join(resources,'sources'),data])fs.mkdirSync(folder,{recursive:true});
 const configuration={dataDirectory:data,district:'co-05',standaloneGitHubData:{schemaVersion:2,cacheRoot,district:'co-05',catalogueSha256:sha}};
 const observed={schemaVersion:1,userSid:'S-1-5-21-100-200-300-1001',accountName:'TEST\\Windows User',sessionId:2,locked:false};
 const gate=await createStandaloneGate({appId:'terrier',identity:{deviceId:'11111111-1111-4111-8111-111111111111'},accountStore:store(),passwords:store(),devices:store(),windowsStore:store(),authentication:'windows',windowsSessionProvider:async()=>structuredClone(observed),configuration:()=>configuration});
 const state={spawns:0,commits:0,closes:0,checks:0,phase:'prepared',fingerprint:'f'.repeat(64),requests:[],hold:false,mutate:value=>value};
 let child,frame,runtime;
 const response=(ready,value,status=200)=>{const incoming=new EventEmitter();incoming.statusCode=status;incoming.resume=()=>{};incoming.destroy=()=>{};ready(incoming);incoming.emit('data',JSON.stringify(value));incoming.emit('end');};
 const transport={get(_url,_options,ready){const req=new EventEmitter();req.destroy=()=>req.emit('error',new Error('closed'));
   const complete=()=>{const {files,commitToken,profileRoot,sourceRoot,dataRoot,stateRoot,...context}=frame;response(ready,state.mutate({appId:'terrier',launchPath:'/',pid:child.pid,districtData:{...context,phase:state.phase,snapshot:'co-cd005-aaaaaaaaaaaa'}}));};
   if(state.hold)state.requests.push(complete);else queueMicrotask(complete);return req;},
  request(_url,_options,ready){const req=new EventEmitter();req.setTimeout=()=>{};req.destroy=()=>{};req.end=()=>queueMicrotask(()=>{state.phase='active';response(ready,{},204);});return req;}};
 const probe={...realRequire('./district-data-probe.cjs'),verifyDistrictProgram(){state.checks++;return {programFingerprint:state.fingerprint};}};
 function load(name,dependencies){const filename=path.join(client,name),module={exports:{}};vm.runInNewContext(fs.readFileSync(filename,'utf8'),{module,require:key=>Object.hasOwn(dependencies,key)?dependencies[key]:realRequire(key),structuredClone,Buffer,URL,setTimeout,clearTimeout,process:{platform:'win32'}},{filename});return module.exports;}
 const input=load('district-runtime-input.cjs',{'./district-data-probe.cjs':probe,'node:http':transport,'./backend-command.cjs':{backendCommand:()=>({runtime:resources})}});
 const dependencies={'./district-runtime-input.cjs':input,'./district-data-probe.cjs':probe,'node:http':transport,
  'node:net':{createServer(){const server=new EventEmitter();server.listen=(_port,_host,ready)=>queueMicrotask(ready);server.address=()=>({port:43210});server.close=ready=>ready();return server;}},
  './backend-command.cjs':{backendCommand:()=>({binary:path.join(resources,'python.exe'),runtime:resources,args:[]}),backendEnvironment:()=>({})},
  './startup-data-diagnostic.cjs':{observeStartupData:()=>({markHealthy(){},blockedAfterExit:async()=>null})},
  'node:child_process':{spawn(binary){const process=new EventEmitter();process.exitCode=null;process.signalCode=null;process.pid=987650+state.spawns;
    if(binary==='taskkill.exe'){queueMicrotask(()=>{child.exitCode=0;child.emit('exit',0);process.emit('exit',0);});return process;}
    state.spawns++;child=process;state.phase='prepared';let bytes=Buffer.alloc(0);process.stdin=new Writable({write(chunk,_encoding,done){bytes=Buffer.concat([bytes,chunk]);done();},final(done){frame=JSON.parse(bytes.subarray(4).toString());done();}});process.stdout=new PassThrough();process.kill=()=>{};return process;}}};
 const Runtime=load('runtime.cjs',dependencies).Runtime;
 runtime=new Runtime('terrier',profile,resources,{allowStandalone:true,authentication:'windows',districtInputRequired:true,authorize:()=>gate.authorize()});
 const roles=[...realRequire('./github-district-protocol.cjs').ROLES,'snapshots/co-cd005-aaaaaaaaaaaa/manifest.json'];
 const bind=()=>input.bindDistrictConfiguration(structuredClone(configuration),{profile,directory,district:'co-05',files:roles.map(role=>({role,path:'co-05/data/'+role,bytes:1,sha256:sha})),verify:async()=>{},commit:async()=>{state.commits++;},close:async()=>{state.closes++;}});
 t.after(async()=>{await runtime.stop();assert.equal(path.dirname(root),os.tmpdir());assert.ok(path.basename(root).startsWith('district-warm-'));fs.rmSync(root,{recursive:true,force:true});});
 return {runtime,configuration,gate,state,observed,bind,async start(){return runtime.start(bind());},exit(){child.exitCode=1;child.emit('exit',1);},release(){state.requests.splice(0).forEach(fn=>fn());}};
}
module.exports={districtRuntime};
