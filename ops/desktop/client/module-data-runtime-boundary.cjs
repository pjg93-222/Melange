'use strict';
// Only trusted native code can issue a one-use launch reference. Serialized
// settings, source metadata and ordinary HTTP health never create one.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {canonical}=require('./access-client.cjs');
const {authorizationIdentity}=require('./access-lifecycle.cjs');
const {authorized}=require('./github-module-protocol.cjs');
const {validateModuleBinding}=require('./module-data-binding.cjs');
const RUNTIMES=new WeakMap(),CAPABILITIES=new WeakMap();
const MAX_FRAME=65536,HASH=/^[a-f0-9]{64}$/;
function failure(){const error=new Error('Native module input is unavailable.');error.code=error.reason='transition';return error;}
function requireValue(value){if(!value)throw failure();}
function digest(value){return crypto.createHash('sha256').update(canonical(value)).digest('hex');}
function exact(value,fields){return value&&typeof value==='object'&&!Array.isArray(value)&&Object.keys(value).sort().join('|')===[...fields].sort().join('|');}
function same(a,b){return a.dev===b.dev&&a.ino===b.ino&&a.mode===b.mode&&a.nlink===b.nlink&&a.size===b.size&&a.mtimeNs===b.mtimeNs&&a.ctimeNs===b.ctimeNs;}
function inside(root,file){const rel=path.relative(root,file);return rel!==''&&rel!=='..'&&!rel.startsWith('..'+path.sep)&&!path.isAbsolute(rel);}
function programTable(files){
 requireValue(Array.isArray(files)&&files.length>0&&files.length<=512);
 const seen=new Set();let total=0;
 const result=files.map(item=>{
  requireValue(exact(item,['root','path','bytes','sha256'])&&['source','bootstrap'].includes(item.root)&&typeof item.path==='string'&&item.path.length>0&&item.path.length<=400&&
   item.path.split('/').every(part=>/^[A-Za-z0-9_-][A-Za-z0-9._-]{0,127}$/.test(part)&&!part.endsWith('.'))&&
   Number.isSafeInteger(item.bytes)&&item.bytes>=0&&item.bytes<=16*1024**2&&typeof item.sha256==='string'&&HASH.test(item.sha256));
  const key=item.root+'/'+item.path.toLowerCase();requireValue(!seen.has(key));seen.add(key);total+=item.bytes;
  return {root:item.root,path:item.path,bytes:item.bytes,sha256:item.sha256};
 });
 requireValue(total<=64*1024**2);
 return result.sort((a,b)=>a.root===b.root?(a.path<b.path?-1:a.path>b.path?1:0):(a.root<b.root?-1:1));
}
function programFingerprint(files){return digest(programTable(files));}
function initializeModuleRuntime(runtime,programRoots){requireValue(runtime&&typeof programRoots==='function'&&!RUNTIMES.has(runtime));RUNTIMES.set(runtime,{programRoots,active:null});}
function verifyProgram(runtime,contract){
 const support=RUNTIMES.get(runtime);requireValue(support&&programFingerprint(contract.programFiles)===contract.programFingerprint);
 const roots=support.programRoots();requireValue(exact(roots,['source','bootstrap']));
 for(const item of programTable(contract.programFiles)){
  const root=roots[item.root];requireValue(typeof root==='string'&&path.isAbsolute(root));
  const base=fs.realpathSync.native(root),rootInfo=fs.lstatSync(root,{bigint:true});requireValue(rootInfo.isDirectory()&&!rootInfo.isSymbolicLink());
  const file=path.join(base,...item.path.split('/'));requireValue(inside(base,file));
  let current=base;
  for(const part of item.path.split('/').slice(0,-1)){current=path.join(current,part);const info=fs.lstatSync(current,{bigint:true});requireValue(info.isDirectory()&&!info.isSymbolicLink()&&fs.realpathSync.native(current)===current);}
  const before=fs.lstatSync(file,{bigint:true});requireValue(before.isFile()&&!before.isSymbolicLink()&&before.nlink===1n&&before.size===BigInt(item.bytes)&&fs.realpathSync.native(file)===file);
  const descriptor=fs.openSync(file,fs.constants.O_RDONLY|(fs.constants.O_NOFOLLOW||0));
  try{
   requireValue(same(before,fs.fstatSync(descriptor,{bigint:true})));
   const h=crypto.createHash('sha256'),buffer=Buffer.alloc(65536);let bytes=0,read;
   while((read=fs.readSync(descriptor,buffer,0,buffer.length,null))!==0){bytes+=read;requireValue(bytes<=item.bytes);h.update(buffer.subarray(0,read));}
   requireValue(bytes===item.bytes&&h.digest('hex')===item.sha256&&same(before,fs.fstatSync(descriptor,{bigint:true}))&&same(before,fs.lstatSync(file,{bigint:true})));
  }finally{fs.closeSync(descriptor);}
 }
 return roots;
}
function encodeModuleFrame(value){
 const bytes=Buffer.from(canonical(value),'utf8');requireValue(bytes.length>=2&&bytes.length<=MAX_FRAME);
 const header=Buffer.alloc(4);header.writeUInt32BE(bytes.length);return Buffer.concat([header,bytes]);
}
function writeModuleFrame(child,frame,signal){
 return new Promise((resolve,reject)=>{
  const input=child.stdin;let done=false,timer=null;
  const finish=error=>{if(done)return;done=true;clearTimeout(timer);child.removeListener('exit',exited);signal?.removeEventListener('abort',aborted);error?reject(failure()):resolve();};
  const failed=()=>finish(failure()),exited=()=>finish(failure()),aborted=()=>{input?.destroy();finish(failure());};
  if(!input||signal?.aborted||!Buffer.isBuffer(frame)||frame.length>MAX_FRAME+4){finish(failure());return;}
  input.on('error',failed);input.once('close',()=>input.removeListener('error',failed));child.once('exit',exited);signal?.addEventListener('abort',aborted,{once:true});
  timer=setTimeout(()=>{input.destroy();finish(failure());},5000);timer.unref?.();
  try{input.end(frame,error=>finish(error));}catch{finish(failure());}
 });
}
function consumeModuleCapability(runtime,capability,configuration){
 const record=CAPABILITIES.get(capability);requireValue(record&&record.runtime===runtime&&!record.consumed&&!runtime.child&&record.selectedFingerprint===digest(configuration));
 record.guard();verifyProgram(runtime,record.contract);record.consumed=true;return record;
}
function activeModule(runtime){return RUNTIMES.get(runtime)?.active||null;}
function setActiveModule(runtime,record,child){const support=RUNTIMES.get(runtime);requireValue(support&&record.runtime===runtime&&record.consumed&&runtime.child===child);support.active={record,child};}
function clearActiveModule(runtime,child){const support=RUNTIMES.get(runtime);if(support&&(!child||support.active?.child===child))support.active=null;}
function matchesModuleHealth(runtime,value,binding){
 const active=activeModule(runtime);if(!active||runtime.child!==active.child||!value||value.pid!==active.child.pid||value.appId!==runtime.definition.id)return false;
 const record=active.record,data=value.moduleData;
 return exact(data,['schemaVersion','contractId','programFingerprint','sourceDigest','sourceFingerprint','launchNonce','coverageDigest'])&&
  data.schemaVersion===1&&data.launchNonce===record.launchNonce&&data.coverageDigest===record.coverageDigest&&
  Object.entries(record.binding).every(([key,expected])=>data[key]===expected)&&
  (!binding||exact(binding,Object.keys(record.binding))&&Object.entries(record.binding).every(([key,expected])=>binding[key]===expected));
}
function checkWarmModule(runtime,configuration,approval){
 const active=activeModule(runtime);if(!active)return;
 const record=active.record;requireValue(runtime.child===active.child&&digest(configuration)===record.selectedFingerprint&&digest(record.getSelected())===record.selectedFingerprint&&
  authorized(record.appId,configuration,approval)&&authorizationIdentity(approval)===record.authorizationIdentity);
 verifyProgram(runtime,record.contract);
}
function createRuntimeModuleBoundary({appId,profile,publicKeys,contract,getRuntime,getSelected,authorize,protectedRoots=[],onPreparing=()=>{}}){
 if(!contract||!['melange','mentat'].includes(appId)||typeof getRuntime!=='function'||typeof getSelected!=='function'||typeof authorize!=='function'||typeof onPreparing!=='function')return null;
 let files;
 try{
  files=programTable(contract.programFiles);
  requireValue(contract.appId===appId&&programFingerprint(files)===contract.programFingerprint&&Number.isSafeInteger(contract.startupTimeoutMs)&&contract.startupTimeoutMs>=1000&&contract.startupTimeoutMs<=600000);
 }catch{return null;}
 const supported=selected=>{try{requireValue(selected===contract);verifyProgram(getRuntime(),contract);return true;}catch{return false;}};
 return Object.freeze({programFingerprint:contract.programFingerprint,supportsContract:supported,
  async start({runtime,configuration,candidate,lease,contract:requested,claimChild}){
   requireValue(runtime===getRuntime()&&requested===contract&&supported(requested)&&!runtime.child&&typeof claimChild==='function');
   const selected=structuredClone(configuration),selectedFingerprint=digest(selected),generation=runtime.generation||0;
   const guard=()=>{lease.assertCurrent();requireValue(!lease.signal.aborted&&runtime===getRuntime()&&(runtime.generation||0)===generation&&digest(getSelected())===selectedFingerprint);};
   guard();requireValue(digest(lease.originalSelected)===selectedFingerprint);
   const effective=structuredClone(candidate.effectiveConfiguration),source=effective.ownerGitHubModuleData;delete effective.ownerGitHubModuleData;
   requireValue(digest(effective)===selectedFingerprint&&source?.appId===appId&&source.manifestSha256===candidate.manifestSha256&&source.pointerDigest===candidate.pointerDigest);
   const binding=Object.freeze({contractId:contract.contractId,programFingerprint:contract.programFingerprint,sourceDigest:source.manifestSha256,sourceFingerprint:digest(source)});
   const approval=await authorize(selected);guard();requireValue(authorized(appId,selected,approval));
   const roots=verifyProgram(runtime,contract),launchNonce=crypto.randomBytes(32).toString('base64url');
   const record={runtime,appId,contract,generation,selectedFingerprint,getSelected,guard,source:structuredClone(source),binding,launchNonce,signal:lease.signal,consumed:false,
    authorizationIdentity:authorizationIdentity(approval),startupTimeoutMs:contract.startupTimeoutMs,claimChild,
    coverageDigest:digest({publicReaders:[...contract.publicReaders].sort(),privateBoundaries:[...contract.privateBoundaries].sort()}),
    validate:async()=>{guard();verifyProgram(runtime,contract);const checked=await validateModuleBinding({appId,profile,configuration:candidate.effectiveConfiguration,publicKeys,registry:contract.registry,requiredKinds:contract.requiredKinds,signal:lease.signal,protectedRoots});
     guard();requireValue(checked.snapshotRoot===candidate.snapshotRoot&&digest(checked.source)===binding.sourceFingerprint);},
    checkAuthorization:current=>{guard();requireValue(authorized(appId,selected,current)&&authorizationIdentity(current)===authorizationIdentity(approval));verifyProgram(runtime,contract);},
    frame:runtimeRoots=>encodeModuleFrame({schemaVersion:1,appId,contractId:contract.contractId,programFingerprint:contract.programFingerprint,
     profileRoot:profile,sourceRoot:roots.source,originalDataRoot:runtimeRoots.data,stateRoot:runtimeRoots.state,
     source:structuredClone(source),launchNonce,binding})};
   const capability=Object.freeze({});CAPABILITIES.set(capability,record);
   onPreparing();guard();
   const origin=await runtime.start(selected,capability);guard();
   requireValue(activeModule(runtime)?.record===record);
   return Object.freeze({...binding,origin,child:runtime.child});
  },
  async verifyHealth({runtime,lease,contract:requested,binding}){
   lease.assertCurrent();if(runtime!==getRuntime()||requested!==contract||!supported(requested))return false;
   const active=activeModule(runtime);if(!active)return false;active.record.guard();
   const value=await runtime.verifyModuleHealth(binding);lease.assertCurrent();active.record.guard();
   return value===true&&activeModule(runtime)===active;
  }
 });
}
module.exports={programTable,programFingerprint,verifyProgram,encodeModuleFrame,writeModuleFrame,initializeModuleRuntime,
 consumeModuleCapability,activeModule,setActiveModule,clearActiveModule,matchesModuleHealth,checkWarmModule,createRuntimeModuleBoundary};
