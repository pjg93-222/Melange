'use strict';
// Preparation and staging only. Native startup/transition code calls commitActive
// after successful backend health; downloading never activates a dataset.
const fs=require('node:fs'),fsp=fs.promises,path=require('node:path'),crypto=require('node:crypto');
const {canonical}=require('./access-client.cjs');
const {strictJson,exact}=require('./dataset-protocol.cjs');
const protocol=require('./github-module-protocol.cjs');
const {GitHubModuleTransport}=require('./github-module-transport.cjs');
const {physicalPath}=require('./runtime-roots.cjs');
const {fail,requireValue,authorized,hash,integer,TAG,COMMIT}=protocol;
const RECORD=['catalogSequence','pointerDigest','manifestSha256','releaseTag','releaseCommit','identityDigest'];
const OFFLINE=new Set(['unreachable','timeout','rate_limited']);
function canceled(signal){if(signal?.aborted)throw fail('cancelled','Module data operation cancelled');}
function inside(root,target,equal=false){const rel=path.relative(root,target);return (equal||rel!=='')&&rel!=='..'&&!rel.startsWith('..'+path.sep)&&!path.isAbsolute(rel);}
function overlaps(a,b){a=physicalPath(a);b=physicalPath(b);return inside(a,b,true)||inside(b,a,true);}
function digest(bytes){return crypto.createHash('sha256').update(bytes).digest('hex');}
function sameFile(a,b){return a.dev===b.dev&&a.ino===b.ino&&a.mode===b.mode&&a.nlink===b.nlink&&a.size===b.size&&a.mtimeNs===b.mtimeNs&&a.ctimeNs===b.ctimeNs;}
function safeRecord(record){
 if(record===null)return;
 exact(record,RECORD);
 requireValue(integer(record.catalogSequence)&&record.catalogSequence>0&&['pointerDigest','manifestSha256','identityDigest'].every(key=>hash(record[key]))&&typeof record.releaseTag==='string'&&TAG.test(record.releaseTag)&&typeof record.releaseCommit==='string'&&COMMIT.test(record.releaseCommit),'Invalid protected module data record');
}
async function fileDigest(file,{signal,identity}={}){
 const before=await fsp.lstat(file,{bigint:true});requireValue(before.isFile()&&!before.isSymbolicLink()&&before.nlink===1n&&before.size<=BigInt(protocol.MAX_TOTAL),'Unsafe module cache file');
 if(identity)requireValue(sameFile(before,identity),'Module file changed during verification');
 const h=crypto.createHash('sha256');let bytes=0;
 for await(const chunk of fs.createReadStream(file)){canceled(signal);bytes+=chunk.length;requireValue(BigInt(bytes)<=before.size,'Module file grew during verification');h.update(chunk);}
 const after=await fsp.lstat(file,{bigint:true});
 requireValue(after.isFile()&&!after.isSymbolicLink()&&after.nlink===1n&&sameFile(before,after)&&BigInt(bytes)===before.size,'Module file changed during verification');
 return {bytes,sha256:h.digest('hex')};
}
class GitHubModules{
 constructor({appId,publicKeys,profile,cacheRoot,protectedRoots=[],store,registry,requiredKinds=Object.keys(registry||{}),effectiveConfiguration,authorize,transport,now=Date.now,minimumFreeBytes=512*1024**2}){
  this.appId=appId;this.app=protocol.configuration(appId);protocol.checkedRegistry(appId,registry,requiredKinds);
  if(!store?.read||!store?.write||typeof authorize!=='function'||typeof effectiveConfiguration!=='function'||!publicKeys||typeof publicKeys!=='object')throw fail('integrity','Native module data dependencies are required');
  if(typeof profile!=='string'||!path.isAbsolute(profile)||!fs.statSync(profile).isDirectory()||fs.lstatSync(profile).isSymbolicLink())throw fail('integrity','An existing native profile is required');
  if(!Array.isArray(protectedRoots)||protectedRoots.some(root=>typeof root!=='string'||!path.isAbsolute(root))||!integer(minimumFreeBytes))throw fail('integrity','Invalid native module data boundaries');
  this.profile=fs.realpathSync.native(profile);this.publicKeys=structuredClone(publicKeys);this.store=store;this.registry=registry;this.requiredKinds=[...requiredKinds];this.effectiveConfiguration=effectiveConfiguration;this.authorize=authorize;this.transport=transport||new GitHubModuleTransport(appId);this.now=now;this.minimumFreeBytes=minimumFreeBytes;
  const localBase=process.env.LOCALAPPDATA?fs.realpathSync.native(path.resolve(process.env.LOCALAPPDATA)):null;
  const choices=[{base:this.profile,root:path.join(this.profile,'packs','github-module-data')},...(localBase?[{base:localBase,root:path.join(localBase,'MelangeData',appId,'github-module-data')}]:[])];
  const chosen=cacheRoot?choices.find(choice=>physicalPath(choice.root)===physicalPath(cacheRoot)):choices.at(-1);
  if(!chosen)throw fail('integrity','Unapproved native module cache root');
  this.cacheRoot=path.resolve(chosen.root);this.cacheBase=fs.realpathSync.native(chosen.base);this.protectedRoots=[path.join(this.profile,'state'),...protectedRoots];
  for(const root of this.protectedRoots)requireValue(!overlaps(this.cacheRoot,root),'Module cache overlaps protected state');
  this.tail=Promise.resolve();
 }
 operation(selected,options,action){
  const original=structuredClone(selected),copied={...(options||{})};
  const work=this.tail.then(async()=>{canceled(copied.signal);const identity=await this.owner(original);await this.ensureCache(original);return action(original,copied,identity);}).catch(error=>{if(error?.reason)throw error;throw fail('storage','Module data operation failed');});
  this.tail=work.catch(()=>{});return work;
 }
 async owner(selected){
  if(Object.hasOwn(selected||{},'ownerGitHubModuleData')||Object.hasOwn(selected||{},'ownerGitHubData'))throw fail('authorization','Original owner configuration is required');
  let authorization;try{authorization=await this.authorize(structuredClone(selected));}catch{throw fail('authorization','Verified existing-owner approval is required');}
  if(!authorized(this.appId,selected,authorization))throw fail('authorization','Verified existing-owner approval is required');
  const grant=authorization.accepted.grant,owner=authorization.owner;
  return digest(Buffer.from(canonical({appId:this.appId,grantId:grant.grantId,serverId:grant.serverId,deviceId:grant.deviceId,principalId:grant.principalId,accountIdentity:grant.accountIdentity,ownerBindings:owner.dataBindings,selected})));
 }
 async ensureDirectory(target){
  requireValue(inside(this.cacheBase,target,true),'Module cache leaves its native boundary');
  let current=this.cacheBase;
  const baseStat=await fsp.lstat(current);requireValue(baseStat.isDirectory()&&!baseStat.isSymbolicLink(),'Unsafe native module cache base');
  for(const part of path.relative(this.cacheBase,target).split(path.sep).filter(Boolean)){
   current=path.join(current,part);await fsp.mkdir(current).catch(error=>{if(error.code!=='EEXIST')throw fail('storage','Module cache directory is unavailable');});
   const st=await fsp.lstat(current);requireValue(st.isDirectory()&&!st.isSymbolicLink()&&inside(this.cacheBase,await fsp.realpath(current),true),'Unsafe module cache directory');
  }
 }
 async ensureCache(selected){
  requireValue(!overlaps(this.cacheRoot,selected.dataDirectory),'Module cache must remain separate from the owner workspace');
  for(const root of this.protectedRoots)requireValue(!overlaps(this.cacheRoot,root),'Module cache overlaps protected state');
  await this.ensureDirectory(this.cacheRoot);
  for(const part of ['pointers','manifests','segments','snapshots','staging'])await this.ensureDirectory(path.join(this.cacheRoot,part));
 }
 async file(relative,{parent=true}={}){
  requireValue(protocol.relative(relative),'Unsafe module cache path');const file=path.join(this.cacheRoot,...relative.split('/'));
  requireValue(inside(this.cacheRoot,file),'Module cache path leaves its boundary');
  if(parent)await this.ensureDirectory(path.dirname(file));
  try{const st=await fsp.lstat(file);requireValue(st.isFile()&&!st.isSymbolicLink()&&st.nlink===1&&inside(this.cacheRoot,await fsp.realpath(file)),'Unsafe module cache file');}catch(error){if(error.code!=='ENOENT')throw error;}
  return file;
 }
 async read(file,max){const st=await fsp.lstat(file);requireValue(st.isFile()&&!st.isSymbolicLink()&&st.nlink===1&&st.size<=max,'Invalid cached module metadata');return fsp.readFile(file);}
 async openedCacheHandle(handle,file,size){
  // Validate the inode actually opened, not just a path checked before open.
  // In particular, r+ must never write through a swapped account-file hardlink.
  try{
   const opened=await handle.stat({bigint:true}),current=await fsp.lstat(file,{bigint:true});
   requireValue(opened.isFile()&&current.isFile()&&!current.isSymbolicLink()&&opened.nlink===1n&&current.nlink===1n&&opened.ino===current.ino&&opened.dev===current.dev&&opened.size===BigInt(size)&&current.size===opened.size,'Opened module cache identity changed');
   requireValue(inside(physicalPath(this.cacheRoot),physicalPath(await fsp.realpath(file))),'Opened module file leaves cache');
   let parent=path.dirname(file);
   while(inside(this.cacheRoot,parent,true)){const st=await fsp.lstat(parent);requireValue(st.isDirectory()&&!st.isSymbolicLink(),'Opened module directory is unsafe');if(parent===this.cacheRoot)break;parent=path.dirname(parent);}
   return opened;
  }catch(error){if(error.reason)throw error;throw fail('integrity','Opened module cache identity is unavailable');}
 }
 partialIdentity(file,identity){
  // No asynchronous gap between the final path/identity checks and unlink/rename.
  // Callers close the verified handle first for Windows file-sharing semantics.
  try{
   requireValue(path.dirname(file)===path.join(this.cacheRoot,'segments')&&/^[a-f0-9]{64}\.part$/.test(path.basename(file)),'Unsafe module partial path');
   let parent=path.dirname(file);
   while(inside(this.cacheBase,parent,true)){const st=fs.lstatSync(parent);requireValue(st.isDirectory()&&!st.isSymbolicLink(),'Module partial directory changed');if(parent===this.cacheBase)break;parent=path.dirname(parent);}
   requireValue(parent===this.cacheBase&&inside(this.cacheRoot,fs.realpathSync.native(file)),'Module partial leaves its cache');
   const current=fs.lstatSync(file,{bigint:true});
   requireValue(current.isFile()&&!current.isSymbolicLink()&&current.nlink===1n&&sameFile(current,identity),'Module partial identity changed');
  }catch(error){if(error.reason)throw error;throw fail('integrity','Module partial identity is unavailable');}
 }
 async immutable(relative,bytes){
  const file=await this.file(relative);
  if(fs.existsSync(file)){requireValue((await this.read(file,bytes.length)).equals(bytes),'Module metadata cache collision');return file;}
  const temporary=await this.file(relative+'.'+crypto.randomUUID()+'.tmp');let handle;
  try{handle=await fsp.open(temporary,'wx');await this.openedCacheHandle(handle,temporary,0);await handle.writeFile(bytes);await handle.sync();await handle.close();handle=null;requireValue(!fs.existsSync(file),'Concurrent module metadata replacement refused');await fsp.rename(temporary,file);}finally{await handle?.close();await fsp.unlink(temporary).catch(error=>{if(error.code!=='ENOENT')throw error;});}
  return file;
 }
 async state(){
  const value=await this.store.read();
  if(value===null||value===undefined)return {schemaVersion:1,appId:this.appId,repository:this.app.repository,highwater:{catalogSequence:0,pointerDigest:null},accepted:null,staged:null,active:null};
  try{
   requireValue(Buffer.byteLength(JSON.stringify(value))<=16384,'Protected module journal is too large');exact(value,['schemaVersion','appId','repository','highwater','accepted','staged','active']);exact(value.highwater,['catalogSequence','pointerDigest']);
   requireValue(value.schemaVersion===1&&value.appId===this.appId&&value.repository===this.app.repository&&integer(value.highwater.catalogSequence)&&(value.highwater.catalogSequence===0?value.highwater.pointerDigest===null:hash(value.highwater.pointerDigest)),'Invalid protected module journal');
   for(const key of ['accepted','staged','active']){safeRecord(value[key]);if(value[key])requireValue(value[key].catalogSequence<=value.highwater.catalogSequence,'Module journal exceeds accepted high-water');}
   if(value.accepted)requireValue(value.accepted.catalogSequence===value.highwater.catalogSequence&&value.accepted.pointerDigest===value.highwater.pointerDigest,'Module accepted record differs from high-water');
   return structuredClone(value);
  }catch(error){if(error.reason)throw error;throw fail('integrity','Protected module journal is invalid');}
 }
 async save(state){await this.store.write(structuredClone(state));}
 status(phase,record,{onStatus,cached=false,receivedBytes,totalBytes,message}={}){
  const value={provider:'github',appId:this.appId,repository:this.app.repository,phase,cached,canRefresh:!['checking','downloading','verifying'].includes(phase),...(record?{releaseTag:record.releaseTag,catalogueSequence:record.catalogSequence}:{}),checkedAt:new Date(this.now()).toISOString(),...(phase==='ready'||phase==='update-ready'||phase==='offline'?{verifiedAt:new Date(this.now()).toISOString()}:{}),...(integer(receivedBytes)?{receivedBytes}:{}),...(integer(totalBytes)?{totalBytes}:{}),...(phase==='update-ready'?{updateAvailable:true}:{}),...(message?{message}:{})};
  onStatus?.(structuredClone(value));return value;
 }
 record(checked,manifest,identity){return {catalogSequence:checked.value.catalogSequence,pointerDigest:checked.digest,manifestSha256:manifest.sha256,releaseTag:checked.value.releaseTag,releaseCommit:checked.value.releaseCommit,identityDigest:identity};}
 async metadata(record){
  safeRecord(record);
  const envelope=protocol.parseJson(await this.read(await this.file('pointers/'+record.pointerDigest+'.json'),32768));
  const checked=protocol.pointer(this.appId,envelope,this.publicKeys);
  requireValue(checked.digest===record.pointerDigest&&checked.value.catalogSequence===record.catalogSequence&&checked.value.releaseTag===record.releaseTag&&checked.value.releaseCommit===record.releaseCommit&&checked.value.manifest.sha256===record.manifestSha256,'Cached module pointer changed');
  const manifest=protocol.manifest(this.appId,await this.read(await this.file('manifests/'+record.manifestSha256+'.json'),protocol.MAX_MANIFEST),checked,this.registry,this.requiredKinds);
  return {checked,manifest};
 }
 async validateSnapshot(root,manifest,{signal}={}){
  await this.ensureDirectory(path.dirname(root));const st=await fsp.lstat(root);requireValue(st.isDirectory()&&!st.isSymbolicLink()&&inside(this.cacheRoot,await fsp.realpath(root)),'Unsafe module snapshot');
  const expected=new Set(),expectedDirectories=new Set(),datasets=[];
  for(const dataset of manifest.value.datasets){
   const adapter=this.registry[dataset.kind],dataRoot=path.join(root,dataset.datasetId),files={};
   const dataStat=await fsp.lstat(dataRoot);requireValue(dataStat.isDirectory()&&!dataStat.isSymbolicLink(),'Unsafe module dataset directory');
   for(const object of dataset.objects){
    canceled(signal);const relative=dataset.datasetId+'/'+adapter.roles[object.role].path,file=path.join(root,...relative.split('/'));
    let parent=path.dirname(file);
    while(parent!==root){const parentStat=await fsp.lstat(parent);requireValue(parentStat.isDirectory()&&!parentStat.isSymbolicLink(),'Unsafe module snapshot directory');parent=path.dirname(parent);}
    requireValue(inside(root,await fsp.realpath(file)),'Module role leaves snapshot');
    const actual=await fileDigest(file,{signal});requireValue(actual.bytes===object.bytes&&actual.sha256===object.sha256,'Module role cache integrity failed');expected.add(relative);files[object.role]=file;
    let ancestor=path.posix.dirname(relative);while(ancestor!=='.'){expectedDirectories.add(ancestor);ancestor=path.posix.dirname(ancestor);}
   }
   requireValue(await adapter.validateSnapshot({dataset:structuredClone(dataset),root:dataRoot,files:{...files},signal})===true,'Compiled module reader validation failed');
   datasets.push({kind:dataset.kind,datasetId:dataset.datasetId,revisionId:dataset.revisionId,root:dataRoot,files,objects:structuredClone(dataset.objects)});
  }
  const walk=async(directory,prefix='')=>{for(const entry of await fsp.readdir(directory,{withFileTypes:true})){const relative=prefix+entry.name,p=path.join(directory,entry.name);requireValue(!entry.isSymbolicLink(),'Snapshot reparse point refused');if(entry.isDirectory()){requireValue(expectedDirectories.delete(relative),'Unexpected module snapshot directory');await walk(p,relative+'/');}else requireValue(entry.isFile()&&expected.delete(relative),'Unexpected module snapshot file');}};
  await walk(root);requireValue(expected.size===0&&expectedDirectories.size===0,'Module snapshot role is missing');return datasets;
 }
 async candidate(record,selected,identity,{signal,onStatus,phase='ready'}={}){
  requireValue(record.identityDigest===identity,'Module snapshot belongs to another owner configuration');
  const {manifest}=await this.metadata(record),root=path.join(this.cacheRoot,'snapshots',record.manifestSha256),datasets=await this.validateSnapshot(root,manifest,{signal});
  requireValue(await this.owner(selected)===identity,'Owner approval changed during module verification');
  const source={schemaVersion:1,appId:this.appId,repository:this.app.repository,catalogSequence:record.catalogSequence,releaseTag:record.releaseTag,releaseCommit:record.releaseCommit,pointerDigest:record.pointerDigest,manifestSha256:record.manifestSha256,cacheRoot:this.cacheRoot};
  const effective=await this.effectiveConfiguration({originalSelected:structuredClone(selected),snapshotRoot:root,datasets:structuredClone(datasets),source:structuredClone(source)});
  requireValue(effective&&typeof effective==='object'&&!Array.isArray(effective),'Compiled module configuration binding failed');
  const {ownerGitHubModuleData,...original}=effective;
  requireValue(canonical(original)===canonical(selected)&&canonical(ownerGitHubModuleData)===canonical(source),'Module binding must preserve original configuration and exact native source');
  return Object.freeze({schemaVersion:1,appId:this.appId,repository:this.app.repository,catalogueSequence:record.catalogSequence,releaseTag:record.releaseTag,pointerDigest:record.pointerDigest,manifestSha256:record.manifestSha256,snapshotRoot:root,effectiveConfiguration:structuredClone(effective),status:this.status(phase,record,{onStatus,cached:true,totalBytes:manifest.totalBytes,receivedBytes:manifest.totalBytes})});
 }
 async disk(bytes){const stat=await fsp.statfs(this.cacheRoot);if(stat.bavail*stat.bsize<bytes+this.minimumFreeBytes)throw fail('storage','Insufficient module data staging space');}
 async segment(tag,item,{signal,onProgress}={}){
  const complete=await this.file('segments/'+item.sha256+'.bin'),part=await this.file('segments/'+item.sha256+'.part');
  if(fs.existsSync(complete)){const found=await fileDigest(complete,{signal});requireValue(found.bytes===item.bytes&&found.sha256===item.sha256,'Module segment cache integrity failed');onProgress?.(item.bytes);return complete;}
  const initial=fs.existsSync(part)?await fsp.lstat(part,{bigint:true}):null;
  let handle,identity,offset;
  const discard=async message=>{
   const current=await this.openedCacheHandle(handle,part,identity.size);requireValue(sameFile(current,identity),'Module partial identity changed');
   this.partialIdentity(part,identity);await handle.close();handle=null;
   this.partialIdentity(part,identity);fs.unlinkSync(part);throw fail('integrity',message);
  };
  try{
   handle=await fsp.open(part,initial?'r+':'wx');
   identity=await this.openedCacheHandle(handle,part,initial?initial.size:0n);
   if(initial)requireValue(sameFile(initial,identity),'Module partial identity changed');
   if(identity.size>BigInt(item.bytes))await discard('Module partial segment exceeds its bound');
   offset=Number(identity.size);
   if(offset<item.bytes)await this.transport.segment(tag,item,{offset,signal,onChunk:async chunk=>{canceled(signal);requireValue(offset+chunk.length<=item.bytes,'Module segment exceeds its bound');let written=0;while(written<chunk.length){const result=await handle.write(chunk,written,chunk.length-written,offset+written);if(result.bytesWritten<=0)throw fail('storage','Module cache write failed');written+=result.bytesWritten;}offset+=written;onProgress?.(offset);}});
   await handle.sync();identity=await this.openedCacheHandle(handle,part,offset);
   const found=await fileDigest(part,{signal,identity});
   if(found.bytes!==item.bytes||found.sha256!==item.sha256)await discard('Module segment integrity failed');
   await handle.close();handle=null;this.partialIdentity(part,identity);
   requireValue(!fs.existsSync(complete),'Concurrent module segment replacement refused');fs.renameSync(part,complete);return complete;
  }finally{await handle?.sync().catch(()=>{});await handle?.close();}
 }
 async seed(source,destination,object,selected,{signal}={}){
  if(typeof source!=='string'||!path.isAbsolute(source))return false;
  requireValue(inside(physicalPath(selected.dataDirectory),physicalPath(source)),'Legacy module candidate leaves the owner workspace');
  for(const root of this.protectedRoots)requireValue(!inside(physicalPath(root),physicalPath(source),true),'Legacy module candidate overlaps protected state');
  let ancestor=path.dirname(source);const selectedRoot=path.resolve(selected.dataDirectory);
  while(inside(selectedRoot,ancestor,true)){const st=await fsp.lstat(ancestor);requireValue(st.isDirectory()&&!st.isSymbolicLink(),'Legacy module reparse point refused');if(ancestor===selectedRoot)break;ancestor=path.dirname(ancestor);}
  let before;try{before=await fsp.lstat(source,{bigint:true});}catch(error){if(error.code==='ENOENT')return false;throw error;}
  requireValue(before.isFile()&&!before.isSymbolicLink(),'Unsafe legacy module candidate');if(before.size!==BigInt(object.bytes))return false;
  const h=crypto.createHash('sha256');let handle,bytes=0;
  try{handle=await fsp.open(destination,'wx');await this.openedCacheHandle(handle,destination,0);for await(const chunk of fs.createReadStream(source)){canceled(signal);bytes+=chunk.length;if(bytes>object.bytes)break;h.update(chunk);await handle.writeFile(chunk);}await handle.sync();}finally{await handle?.close();}
  const after=await fsp.lstat(source,{bigint:true}),stable=after.isFile()&&!after.isSymbolicLink()&&sameFile(before,after);
  if(!stable||bytes!==object.bytes||h.digest('hex')!==object.sha256){await fsp.unlink(destination);return false;}return true;
 }
 async removeStaging(directory){
  const root=path.join(this.cacheRoot,'staging');requireValue(path.dirname(directory)===root&&/^[a-f0-9-]{36}$/.test(path.basename(directory))&&inside(physicalPath(root),physicalPath(directory)),'Unsafe staging cleanup refused');
  const inspect=async p=>{const st=await fsp.lstat(p);requireValue(!st.isSymbolicLink(),'Staging reparse point refused');if(st.isDirectory())for(const name of await fsp.readdir(p))await inspect(path.join(p,name));};
  if(fs.existsSync(directory)){await inspect(directory);await fsp.rm(directory,{recursive:true});}
 }
 async materialize(manifest,checked,selected,{signal,onStatus}={}){
  const final=path.join(this.cacheRoot,'snapshots',manifest.sha256);
  if(fs.existsSync(final)){await this.validateSnapshot(final,manifest,{signal});return;}
  await this.disk(manifest.totalBytes*2);const staging=path.join(this.cacheRoot,'staging',crypto.randomUUID());await this.ensureDirectory(staging);let completed=0;
  try{
   for(const dataset of manifest.value.datasets){
    const adapter=this.registry[dataset.kind],legacy=typeof adapter.probeLegacy==='function'?await adapter.probeLegacy({originalSelected:structuredClone(selected),dataset:structuredClone(dataset),signal}):null;
    for(const object of dataset.objects){
     canceled(signal);const destination=path.join(staging,dataset.datasetId,...adapter.roles[object.role].path.split('/'));await this.ensureDirectory(path.dirname(destination));
     if(await this.seed(legacy?.[object.role],destination,object,selected,{signal})){completed+=object.bytes;continue;}
     let handle;const h=crypto.createHash('sha256');let bytes=0;
     try{
      handle=await fsp.open(destination,'wx');
      await this.openedCacheHandle(handle,destination,0);
      for(const segment of object.segments){
       const file=await this.segment(checked.value.releaseTag,segment,{signal,onProgress:n=>this.status('downloading',checked.value,{onStatus,totalBytes:manifest.totalBytes,receivedBytes:Math.min(manifest.totalBytes,completed+bytes+n)})});
       for await(const chunk of fs.createReadStream(file)){canceled(signal);bytes+=chunk.length;requireValue(bytes<=object.bytes,'Logical module role exceeds its bound');h.update(chunk);await handle.writeFile(chunk);}
      }
      await handle.sync();
     }finally{await handle?.close();}
     requireValue(bytes===object.bytes&&h.digest('hex')===object.sha256,'Logical module role integrity failed');completed+=bytes;
    }
   }
   this.status('verifying',checked.value,{onStatus,totalBytes:manifest.totalBytes,receivedBytes:completed});await this.validateSnapshot(staging,manifest,{signal});
   requireValue(!fs.existsSync(final),'Concurrent module snapshot replacement refused');await fsp.rename(staging,final);
  }finally{await this.removeStaging(staging);}
 }
 prepare(selected,options={}){return this.operation(selected,options,(original,opts,identity)=>this.check(original,opts,identity,false));}
 stage(selected,options={}){return this.operation(selected,options,(original,opts,identity)=>this.check(original,opts,identity,true));}
 async check(selected,options,identity,background){
  const state=await this.state(),{signal,onStatus}=options;this.status('checking',null,{onStatus});
  try{
   const commit=await this.transport.resolveMain({signal}),envelope=protocol.parseJson(await this.transport.pointer(commit,{signal})),checked=protocol.pointer(this.appId,envelope,this.publicKeys,state.highwater);
   await this.transport.verifyRelease(checked.value,{signal});
   const manifest=protocol.manifest(this.appId,await this.transport.manifest(checked.value,{signal}),checked,this.registry,this.requiredKinds),record=this.record(checked,manifest,identity);
   requireValue(await this.owner(selected)===identity,'Owner approval changed during module check');canceled(signal);
   await this.immutable('pointers/'+checked.digest+'.json',Buffer.from(canonical(envelope)));await this.immutable('manifests/'+manifest.sha256+'.json',manifest.bytes);
   state.highwater={catalogSequence:record.catalogSequence,pointerDigest:record.pointerDigest};state.accepted=record;await this.save(state);
   await this.materialize(manifest,checked,selected,options);requireValue(await this.owner(selected)===identity,'Owner approval changed during module staging');canceled(signal);
   state.staged=record;await this.save(state);
   const unchanged=state.active?.pointerDigest===record.pointerDigest&&state.active?.identityDigest===identity;
   return this.candidate(record,selected,identity,{...options,phase:background&&!unchanged?'update-ready':'ready'});
  }catch(error){
   if(OFFLINE.has(error?.reason)&&state.active)return this.candidate(state.active,selected,identity,{...options,phase:'offline'});
   if(error?.reason)throw error;throw fail('storage','Module data preparation failed');
  }
 }
 active(selected,options={}){return this.operation(selected,options,async(original,opts,identity)=>{const state=await this.state();return state.active?this.candidate(state.active,original,identity,opts):null;});}
 commitActive(candidate,selected,options={}){
  return this.operation(selected,options,async(original,opts,identity)=>{
   requireValue(opts.beforeCommit===undefined||typeof opts.beforeCommit==='function','Invalid native module commit guard');
   const state=await this.state();requireValue(candidate?.schemaVersion===1&&candidate.appId===this.appId&&candidate.repository===this.app.repository,'Invalid native module candidate');
   const matches=record=>record&&record.pointerDigest===candidate.pointerDigest&&record.manifestSha256===candidate.manifestSha256&&record.catalogSequence===candidate.catalogueSequence&&record.releaseTag===candidate.releaseTag&&record.identityDigest===identity;
   const already=matches(state.active),record=already?state.active:matches(state.staged)?state.staged:null;
   requireValue(record&&(already||record.catalogSequence===state.highwater.catalogSequence&&record.pointerDigest===state.highwater.pointerDigest),'Module candidate is no longer the accepted staged revision');
   const fresh=await this.candidate(record,original,identity,opts);requireValue(await this.owner(original)===identity,'Owner approval changed before module activation');canceled(opts.signal);
   if(opts.beforeCommit){const verdict=opts.beforeCommit();requireValue(verdict!==false&&!(verdict&&typeof verdict.then==='function'),'Native module commit guard refused activation');}
   state.active=structuredClone(record);await this.save(state);return fresh;
  });
 }
}
module.exports={GitHubModules,fileDigest,OFFLINE};
