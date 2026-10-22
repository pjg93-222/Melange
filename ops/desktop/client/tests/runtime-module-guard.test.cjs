'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os'),vm=require('node:vm');
const {EventEmitter}=require('node:events'),{createRequire}=require('node:module');

// Real Runtime/root preparation, with synthetic files and isolated process/health
// doubles. No backend, installed application, or production profile is touched.
function fixture(t,appId){
 const temporaryRoot=path.resolve(os.tmpdir()),root=fs.mkdtempSync(path.join(temporaryRoot,'desktop-module-guard-'));
 const user=path.join(root,'profile'),resources=path.join(root,'resources'),data=path.join(root,'original-data');
 fs.mkdirSync(resources);fs.mkdirSync(data);fs.writeFileSync(path.join(data,'owner-state.txt'),'synthetic original state');
 const configuration={dataDirectory:data,connection:{workspace:'original-workspace',reports:'original-reports'}};
 const calls={authorize:0,spawn:[]};let child;
 const runtimeFile=path.join(__dirname,'..','runtime.cjs'),nativeRequire=createRequire(runtimeFile),module={exports:{}};
 const dependencies={
  'node:net':{createServer(){const server=new EventEmitter();server.listen=(_port,_host,ready)=>queueMicrotask(ready);server.address=()=>({port:43211});server.close=ready=>ready();return server;}},
  'node:http':{get(_url,_options,ready){const request=new EventEmitter();request.destroy=()=>request.emit('error',new Error('synthetic transport closed'));
   queueMicrotask(()=>{const response=new EventEmitter();response.statusCode=200;response.destroy=()=>{};ready(response);response.emit('data',JSON.stringify({appId,launchPath:'/'}));response.emit('end');});return request;}},
  'node:child_process':{spawn(binary,args,options){const process=new EventEmitter();process.exitCode=null;process.pid=987653;process.kill=()=>{};
   if(binary==='taskkill.exe'){queueMicrotask(()=>{child.exitCode=0;child.emit('exit',0);process.emit('exit',0);});return process;}
   child=process;calls.spawn.push({binary,args:Array.from(args),options});return process;}},
  './backend-command.cjs':{backendCommand(){return {binary:path.join(resources,'python','python.exe'),runtime:resources,args:['synthetic-bootstrap']};},backendEnvironment:()=>({})},
 };
 vm.runInNewContext(fs.readFileSync(runtimeFile,'utf8'),{module,require:name=>Object.hasOwn(dependencies,name)?dependencies[name]:nativeRequire(name),structuredClone,process:{platform:'win32'},URL,setTimeout,clearTimeout},{filename:runtimeFile});
 const runtime=new module.exports.Runtime(appId,user,resources,{authorize:async()=>{calls.authorize++;return {accepted:{grant:{},revoked:false},owner:true};}});
 t.after(async()=>{
  await runtime.stop();
  // Only remove the exact synthetic directory this fixture created.
  assert.equal(path.dirname(path.resolve(root)),temporaryRoot);assert.match(path.basename(root),/^desktop-module-guard-/);
  fs.rmSync(root,{recursive:true,force:true});
 });
 return {runtime,configuration,calls,root,user,data};
}

for(const appId of ['melange','mentat']){
 for(const [label,value] of [['undefined',undefined],['null',null],['false',false],['true',true],['descriptor',{schemaVersion:1,cacheRoot:'untrusted-cache'}]]){
  test(`${appId} refuses an own ${label} module marker before authorization or storage/process side effects`,async t=>{
   const f=fixture(t,appId),before=fs.readdirSync(f.root);
   await assert.rejects(f.runtime.start({...f.configuration,ownerGitHubModuleData:value}),/GitHub module data startup is unavailable in this build/);
   assert.equal(f.calls.authorize,0);assert.equal(f.calls.spawn.length,0);
   assert.equal(f.runtime.child,null);assert.equal(f.runtime.configuration,null);assert.equal(f.runtime.roots,null);
   assert.equal(fs.existsSync(f.user),false);assert.deepEqual(fs.readdirSync(f.root),before);
   assert.equal(fs.readFileSync(path.join(f.data,'owner-state.txt'),'utf8'),'synthetic original state');
  });
 }
 test(`${appId} refuses an own module accessor without reading its value`,async t=>{
  const f=fixture(t,appId),configuration={...f.configuration};let reads=0;
  Object.defineProperty(configuration,'ownerGitHubModuleData',{enumerable:true,get(){reads++;throw new Error('untrusted accessor');}});
  await assert.rejects(f.runtime.start(configuration),/GitHub module data startup is unavailable in this build/);
  assert.equal(reads,0);assert.equal(f.calls.authorize,0);assert.equal(f.calls.spawn.length,0);assert.equal(fs.existsSync(f.user),false);
 });
 for(const inherited of [false,true]){
  test(`${appId} preserves original roots for ${inherited?'inherited-marker':'ordinary'} configuration without enabling module startup`,async t=>{
   const f=fixture(t,appId),configuration=inherited?Object.assign(Object.create({ownerGitHubModuleData:{schemaVersion:1,cacheRoot:'untrusted-cache'}}),f.configuration):f.configuration;
   await f.runtime.start(configuration);
   assert.equal(f.calls.authorize,1);assert.equal(f.calls.spawn.length,1);
   assert.equal(f.runtime.roots.data,f.data);assert.equal(f.runtime.roots.state,path.join(f.user,'state'));
   assert.deepEqual(f.runtime.configuration,f.configuration);assert.equal(Object.hasOwn(f.runtime.configuration,'ownerGitHubModuleData'),false);
   const args=f.calls.spawn[0].args,value=name=>args[args.indexOf(name)+1];
   assert.equal(value('--data-root'),f.data);assert.equal(value('--state-root'),path.join(f.user,'state'));
   assert.equal(args.some(arg=>arg.includes('github-module')),false);
   assert.equal(fs.readFileSync(path.join(f.data,'owner-state.txt'),'utf8'),'synthetic original state');
  });
 }
}
