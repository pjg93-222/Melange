'use strict';
// Preparation and staging only. Native startup/transition code calls commitActive
// after successful backend health; downloading never activates a dataset.
const fs=require('node:fs'),fsp=fs.promises,path=require('node:path'),crypto=require('node:crypto');
const {canonical}=require('./access-client.cjs');
const {strictJson,exact}=require('./dataset-protocol.cjs');
const protocol=require('./github-module-protocol.cjs');
const {GitHubModuleTransport}=require('./github-module-transport.cjs');
const {physicalPath}=require('./runtime-roots.cjs');
const {checkedNativeCacheRoot}=require('./module-data-binding.cjs');
const {withSnapshotValidation}=require('./module-data-adapters.cjs');
const {CHANNEL:WORKSPACE_CHANNEL}=require('./workspace-data-contract.cjs');
const {fail,requireValue,authorized,hash,integer,TAG,COMMIT}=protocol;
const RECORD=['catalogSequence','pointerDigest','manifestSha256','releaseTag','releaseCommit','identityDigest'];
const OFFLINE=new Set(['unreachable','timeout','rate_limited','proxy']);
// Large public tables are streamed sequentially. Bounded 4 MiB reads avoid
// thousands of Windows I/O round trips while retaining every integrity check.
const READ_BYTES=4*1024*1024;
const stagingOwners=new WeakMap();
function canceled(signal){if(signal?.aborted)throw fail('cancelled','Module data operation cancelled');}
function inside(root,target,equal=false){const rel=path.relative(root,target);return (equal||rel!=='')&&rel!=='..'&&!rel.startsWith('..'+path.sep)&&!path.isAbsolute(rel);}
function overlaps(a,b){a=physicalPath(a);b=physicalPath(b);return inside(a,b,true)||inside(b,a,true);}
function digest(bytes){return crypto.createHash('sha256').update(bytes).digest('hex');}
function sameFile(a,b){return a.dev===b.dev&&a.ino===b.ino&&a.mode===b.mode&&a.nlink===b.nlink&&a.size===b.size&&a.mtimeNs===b.mtimeNs&&a.ctimeNs===b.ctimeNs;}
function sameIdentity(a,b){return a.dev===b.dev&&a.ino===b.ino&&a.mode===b.mode;}
function safeRecord(record){
 if(record===null)return;
 exact(record,RECORD);
 requireValue(integer(record.catalogSequence)&&record.catalogSequence>0&&['pointerDigest','manifestSha256','identityDigest'].every(key=>hash(record[key]))&&typeof record.releaseTag==='string'&&TAG.test(record.releaseTag)&&typeof record.releaseCommit==='string'&&COMMIT.test(record.releaseCommit),'Invalid protected module data record');
}
async function fileDigest(file,{signal,identity}={}){
 const before=await fsp.lstat(file,{bigint:true});requireValue(before.isFile()&&!before.isSymbolicLink()&&before.nlink===1n&&before.size<=BigInt(protocol.MAX_TOTAL),'Unsafe module cache file');
 if(identity)requireValue(sameFile(before,identity),'Module file changed during verification');
 const h=crypto.createHash('sha256');let bytes=0;
 for await(const chunk of fs.createReadStream(file,{highWaterMark:READ_BYTES})){canceled(signal);bytes+=chunk.length;requireValue(BigInt(bytes)<=before.size,'Module file grew during verification');h.update(chunk);}
 const after=await fsp.lstat(file,{bigint:true});
 requireValue(after.isFile()&&!after.isSymbolicLink()&&after.nlink===1n&&sameFile(before,after)&&BigInt(bytes)===before.size,'Module file changed during verification');
 return {bytes,sha256:h.digest('hex')};
}
class GitHubModules{
 constructor({appId,publicKeys,profile,cacheRoot,protectedRoots=[],store,previousStore=null,registry,requiredKinds=Object.keys(registry||{}),effectiveConfiguration,authorize,transport,now=Date.now,minimumFreeBytes=512*1024**2,channel='public-v1'}){
  requireValue(['public-v1',WORKSPACE_CHANNEL.id].includes(channel),'Unsupported compiled module channel');
  this.channel=channel;this.cacheName=channel===WORKSPACE_CHANNEL.id?WORKSPACE_CHANNEL.cacheName:'github-module-data';this.sourceField=channel===WORKSPACE_CHANNEL.id?WORKSPACE_CHANNEL.sourceField:'ownerGitHubModuleData';
  this.appId=appId;this.app=protocol.configuration(appId,channel);protocol.checkedRegistry(appId,registry,requiredKinds,channel);
  if(!store?.read||!store?.write||typeof authorize!=='function'||typeof effectiveConfiguration!=='function'||!publicKeys||typeof publicKeys!=='object')throw fail('integrity','Native module data dependencies are required');
  if(previousStore!==null&&(typeof previousStore?.read!=='function'||previousStore===store))throw fail('integrity','A separate previous public data journal is required');
  requireValue(channel==='public-v1'||previousStore===null,'Workspace state cannot import public-channel journals');
  if(typeof profile!=='string'||!path.isAbsolute(profile)||!fs.statSync(profile).isDirectory()||fs.lstatSync(profile).isSymbolicLink())throw fail('integrity','An existing native profile is required');
  if(!Array.isArray(protectedRoots)||protectedRoots.some(root=>typeof root!=='string'||!path.isAbsolute(root))||!integer(minimumFreeBytes))throw fail('integrity','Invalid native module data boundaries');
  this.profile=fs.realpathSync.native(profile);this.publicKeys=structuredClone(publicKeys);this.store=store;this.previousStore=previousStore;this.registry=registry;this.requiredKinds=[...requiredKinds];this.effectiveConfiguration=effectiveConfiguration;this.authorize=authorize;this.transport=transport||new GitHubModuleTransport(appId,{channel});this.now=now;this.minimumFreeBytes=minimumFreeBytes;
  const localBase=process.env.LOCALAPPDATA?fs.realpathSync.native(path.resolve(process.env.LOCALAPPDATA)):null;
  const choices=[{base:this.profile,root:path.join(this.profile,'packs',this.cacheName)},...(localBase?[{base:localBase,root:path.join(localBase,'MelangeData',appId,this.cacheName)}]:[])];
  const chosen=cacheRoot?choices.find(choice=>physicalPath(choice.root)===physicalPath(cacheRoot)):choices.at(-1);
  if(!chosen)throw fail('integrity','Unapproved native module cache root');
  this.cacheRoot=path.resolve(chosen.root);this.cacheBase=fs.realpathSync.native(chosen.base);this.protectedRoots=[path.join(this.profile,'state'),...protectedRoots];
  for(const root of this.protectedRoots)requireValue(!overlaps(this.cacheRoot,root),'Module cache overlaps protected state');
  this.tail=Promise.resolve();
  stagingOwners.set(this,new Map());
 }
 operation(selected,options,action){
  const original=structuredClone(selected),copied={...(options||{})};
  const work=this.tail.then(async()=>{canceled(copied.signal);const identity=await this.owner(original);await this.ensureCache(original);return action(original,copied,identity);}).catch(error=>{if(error?.reason)throw error;throw fail('storage','Module data operation failed');});
  this.tail=work.catch(()=>{});return work;
 }
 async owner(selected){
  if(['ownerGitHubModuleData','ownerGitHubWorkspaceData','ownerGitHubData'].some(key=>Object.hasOwn(selected||{},key)))throw fail('authorization','Original owner configuration is required');
  let authorization;try{authorization=await this.authorize(structuredClone(selected));}catch{throw fail('authorization','Verified local access is required for public data');}
  if(!authorized(this.appId,selected,authorization))throw fail('authorization','Verified local access is required for public data');
  if(authorization.mode==='standalone')return digest(Buffer.from(canonical({mode:'standalone',identity:authorization.identity,selectedRoot:physicalPath(selected.dataDirectory),selected})));
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
  const resolved=checkedNativeCacheRoot(this.cacheBase,this.cacheRoot);
  requireValue(!overlaps(resolved,selected.dataDirectory),'Module cache must remain separate from the owner workspace');
  for(const root of this.protectedRoots)requireValue(!overlaps(resolved,root),'Module cache overlaps protected state');
  this.cacheRoot=resolved;
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
 cacheAncestors(file){
  requireValue(inside(this.cacheRoot,file),'Owned module file leaves cache');
  let parent=path.dirname(file);
  while(inside(this.cacheBase,parent,true)){const st=fs.lstatSync(parent);requireValue(st.isDirectory()&&!st.isSymbolicLink(),'Owned module directory changed');if(parent===this.cacheBase)break;parent=path.dirname(parent);}
  requireValue(parent===this.cacheBase&&inside(this.cacheRoot,fs.realpathSync.native(file)),'Owned module file leaves its native boundary');
 }
 ownedFile(file,receipt,{links=1n,linkTransition=false}={}){
  // This read-only, bounded verification is synchronous through the final action.
  // A receipt always retains the originally opened inode and writer digest.
  requireValue(receipt&&integer(receipt.bytes,protocol.MAX_TOTAL)&&hash(receipt.sha256)&&receipt.stamp,'Invalid owned module receipt');
  this.cacheAncestors(file);const before=fs.lstatSync(file,{bigint:true}),original=receipt.stamp;
  requireValue(before.isFile()&&!before.isSymbolicLink()&&before.nlink===links&&sameIdentity(before,original)&&before.size===BigInt(receipt.bytes),'Owned module file identity changed');
  requireValue(linkTransition?before.mtimeNs===original.mtimeNs:sameFile(before,original),'Owned module file stamp changed');
  let descriptor;const h=crypto.createHash('sha256');let bytes=0;
  try{
   descriptor=fs.openSync(file,fs.constants.O_RDONLY|(fs.constants.O_NOFOLLOW||0));requireValue(sameFile(fs.fstatSync(descriptor,{bigint:true}),before),'Owned module handle changed');
   const buffer=Buffer.alloc(Math.min(1024*1024,Math.max(1,receipt.bytes)));
   for(;;){const n=fs.readSync(descriptor,buffer,0,buffer.length,null);if(n===0)break;bytes+=n;requireValue(bytes<=receipt.bytes,'Owned module file exceeds its bound');h.update(buffer.subarray(0,n));}
   requireValue(bytes===receipt.bytes&&h.digest('hex')===receipt.sha256,'Owned module file integrity failed');
   requireValue(sameFile(before,fs.fstatSync(descriptor,{bigint:true}))&&sameFile(before,fs.lstatSync(file,{bigint:true})),'Owned module file changed during verification');this.cacheAncestors(file);
   return before;
  }finally{if(descriptor!==undefined)fs.closeSync(descriptor);}
 }
 removeOwnedFile(file,receipt){
  if(!receipt)return false;
  try{this.ownedFile(file,receipt);fs.unlinkSync(file);return true;}catch{return false;}
 }
 rememberStagedFile(file,receipt){
  for(const [root,owner] of stagingOwners.get(this))if(inside(root,file)){const relative=path.relative(root,file);requireValue(!owner.files.has(relative),'Staged module file already recorded');owner.files.set(relative,receipt);return;}
 }
 stageDirectory(root,target,owner){
  requireValue(inside(root,target,true),'Staged module directory leaves its root');let current=root;
  requireValue(sameIdentity(fs.lstatSync(root,{bigint:true}),owner.root),'Staging root identity changed');
  for(const part of path.relative(root,target).split(path.sep).filter(Boolean)){
   current=path.join(current,part);const relative=path.relative(root,current),known=owner.directories.get(relative);
   if(!known){fs.mkdirSync(current);const created=fs.lstatSync(current,{bigint:true});requireValue(created.isDirectory()&&!created.isSymbolicLink(),'Unsafe staged module directory');owner.directories.set(relative,created);}
   const st=fs.lstatSync(current,{bigint:true});requireValue(st.isDirectory()&&!st.isSymbolicLink()&&sameIdentity(st,owner.directories.get(relative)),'Staging directory identity changed');
  }
 }
 ownedStaging(root,owner){
  this.cacheAncestors(root);const st=fs.lstatSync(root,{bigint:true});requireValue(st.isDirectory()&&!st.isSymbolicLink()&&sameIdentity(st,owner.root),'Staging root identity changed');
  const files=new Set(owner.files.keys()),directories=new Set(owner.directories.keys());
  const walk=directory=>{for(const name of fs.readdirSync(directory)){
   const file=path.join(directory,name),relative=path.relative(root,file),item=fs.lstatSync(file,{bigint:true});requireValue(!item.isSymbolicLink(),'Staging reparse point refused');
   if(item.isDirectory()){requireValue(directories.delete(relative)&&sameIdentity(item,owner.directories.get(relative)),'Unowned staging directory refused');walk(file);}
   else{requireValue(item.isFile()&&files.delete(relative),'Unowned staging file refused');this.ownedFile(file,owner.files.get(relative));}
  }};
  walk(root);requireValue(files.size===0&&directories.size===0,'Owned staging member is missing');
 }
 async immutable(relative,bytes){
  const expected=Buffer.from(bytes),entry={bytes:expected.length,sha256:digest(expected)};
  const file=await this.file(relative);
  if(fs.existsSync(file)){const stamp=fs.lstatSync(file,{bigint:true});this.ownedFile(file,{...entry,stamp});return file;}
  const temporary=await this.file(relative+'.'+crypto.randomUUID()+'.tmp');let handle,receipt;
  try{
   handle=await fsp.open(temporary,'wx');const initial=await this.openedCacheHandle(handle,temporary,0);await handle.writeFile(expected);await handle.sync();
   const stamp=await this.openedCacheHandle(handle,temporary,entry.bytes);requireValue(sameIdentity(initial,stamp),'Owned module writer identity changed');receipt={...entry,stamp};
   await handle.close();handle=null;this.ownedFile(temporary,receipt);
   // link is exclusive even if another process creates the destination now.
   fs.linkSync(temporary,file);
   const linked=this.ownedFile(temporary,receipt,{links:2n,linkTransition:true});receipt={...entry,stamp:linked};this.ownedFile(file,receipt,{links:2n});
   this.ownedFile(temporary,receipt,{links:2n});fs.unlinkSync(temporary);this.ownedFile(file,receipt,{linkTransition:true});return file;
  }finally{await handle?.close().catch(()=>{});this.removeOwnedFile(temporary,receipt);}
 }
 checkedState(value){
  if(value===null||value===undefined)return {schemaVersion:1,appId:this.appId,repository:this.app.repository,highwater:{catalogSequence:0,pointerDigest:null},accepted:null,staged:null,active:null};
  try{
   requireValue(Buffer.byteLength(JSON.stringify(value))<=16384,'Protected module journal is too large');exact(value,['schemaVersion','appId','repository','highwater','accepted','staged','active']);exact(value.highwater,['catalogSequence','pointerDigest']);
   requireValue(value.schemaVersion===1&&value.appId===this.appId&&value.repository===this.app.repository&&integer(value.highwater.catalogSequence)&&(value.highwater.catalogSequence===0?value.highwater.pointerDigest===null:hash(value.highwater.pointerDigest)),'Invalid protected module journal');
   for(const key of ['accepted','staged','active']){safeRecord(value[key]);if(value[key])requireValue(value[key].catalogSequence<=value.highwater.catalogSequence,'Module journal exceeds accepted high-water');}
   if(value.accepted)requireValue(value.accepted.catalogSequence===value.highwater.catalogSequence&&value.accepted.pointerDigest===value.highwater.pointerDigest,'Module accepted record differs from high-water');
   return structuredClone(value);
  }catch(error){if(error.reason)throw error;throw fail('integrity','Protected module journal is invalid');}
 }
 async state(){
  const value=await this.store.read();
  if(value!==null&&value!==undefined||!this.previousStore)return this.checkedState(value);
  // A mode change must not reset the highest signed public revision observed.
  // Only its watermark crosses authorities; prior active/staged bindings do not.
  const previous=this.checkedState(await this.previousStore.read()),next=this.checkedState(null);
  if(previous.highwater.catalogSequence){
   try{
    const envelope=protocol.parseJson(await this.read(await this.file('pointers/'+previous.highwater.pointerDigest+'.json'),32768));
    const checked=protocol.pointer(this.appId,envelope,this.publicKeys,previous.highwater,this.channel);
    requireValue(checked.digest===previous.highwater.pointerDigest&&checked.value.catalogSequence===previous.highwater.catalogSequence,'Previous public data high-water does not match its signed pointer');
    next.highwater=structuredClone(previous.highwater);
   }catch{throw fail('integrity','Previous public data high-water could not be verified; existing data was preserved');}
  }
  // A completed local journal always wins over migration, including after a retry.
  const current=await this.store.read();if(current!==null&&current!==undefined)return this.checkedState(current);
  await this.save(next);return next;
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
  const checked=protocol.pointer(this.appId,envelope,this.publicKeys,{},this.channel);
  requireValue(checked.digest===record.pointerDigest&&checked.value.catalogSequence===record.catalogSequence&&checked.value.releaseTag===record.releaseTag&&checked.value.releaseCommit===record.releaseCommit&&checked.value.manifest.sha256===record.manifestSha256,'Cached module pointer changed');
  const manifest=protocol.manifest(this.appId,await this.read(await this.file('manifests/'+record.manifestSha256+'.json'),protocol.MAX_MANIFEST),checked,this.registry,this.requiredKinds,this.channel);
  return {checked,manifest};
 }
 async validateSnapshot(root,manifest,{signal}={}){
  await this.ensureDirectory(path.dirname(root));const st=await fsp.lstat(root);requireValue(st.isDirectory()&&!st.isSymbolicLink()&&inside(this.cacheRoot,await fsp.realpath(root)),'Unsafe module snapshot');
  const expected=new Set(),expectedDirectories=new Set(),datasets=[],verified=[];
  for(const dataset of manifest.value.datasets){
   const adapter=this.registry[dataset.kind],dataRoot=path.join(root,dataset.datasetId),files={};
   const dataStat=await fsp.lstat(dataRoot);requireValue(dataStat.isDirectory()&&!dataStat.isSymbolicLink(),'Unsafe module dataset directory');
   await withSnapshotValidation(adapter,{signal},async validate=>{
   for(const object of dataset.objects){
    canceled(signal);const relative=dataset.datasetId+'/'+adapter.roles[object.role].path,file=path.join(root,...relative.split('/'));
    let parent=path.dirname(file);
    while(parent!==root){const parentStat=await fsp.lstat(parent);requireValue(parentStat.isDirectory()&&!parentStat.isSymbolicLink(),'Unsafe module snapshot directory');parent=path.dirname(parent);}
    requireValue(inside(root,await fsp.realpath(file)),'Module role leaves snapshot');
    const stamp=await fsp.lstat(file,{bigint:true}),actual=await fileDigest(file,{signal,identity:stamp});requireValue(actual.bytes===object.bytes&&actual.sha256===object.sha256,'Module role cache integrity failed');verified.push({file,receipt:{stamp,bytes:object.bytes,sha256:object.sha256}});expected.add(relative);files[object.role]=file;
    let ancestor=path.posix.dirname(relative);while(ancestor!=='.'){expectedDirectories.add(ancestor);ancestor=path.posix.dirname(ancestor);}
   }
   requireValue(await validate({dataset:structuredClone(dataset),root:dataRoot,files:{...files},signal})===true,'Compiled module reader validation failed');
   });
   datasets.push({kind:dataset.kind,datasetId:dataset.datasetId,revisionId:dataset.revisionId,root:dataRoot,files,objects:structuredClone(dataset.objects)});
  }
  const walk=async(directory,prefix='')=>{for(const entry of await fsp.readdir(directory,{withFileTypes:true})){const relative=prefix+entry.name,p=path.join(directory,entry.name);requireValue(!entry.isSymbolicLink(),'Snapshot reparse point refused');if(entry.isDirectory()){requireValue(expectedDirectories.delete(relative),'Unexpected module snapshot directory');await walk(p,relative+'/');}else requireValue(entry.isFile()&&expected.delete(relative),'Unexpected module snapshot file');}};
  await walk(root);requireValue(expected.size===0&&expectedDirectories.size===0,'Module snapshot role is missing');canceled(signal);for(const {file,receipt} of verified)this.ownedFile(file,receipt);return datasets;
 }
 async candidate(record,selected,identity,{signal,onStatus,phase='ready'}={}){
  requireValue(record.identityDigest===identity,'Module snapshot belongs to another owner configuration');
  const {manifest}=await this.metadata(record),root=path.join(this.cacheRoot,'snapshots',record.manifestSha256),datasets=await this.validateSnapshot(root,manifest,{signal});
  requireValue(await this.owner(selected)===identity,'Owner approval changed during module verification');
  const source={schemaVersion:1,appId:this.appId,repository:this.app.repository,catalogSequence:record.catalogSequence,releaseTag:record.releaseTag,releaseCommit:record.releaseCommit,pointerDigest:record.pointerDigest,manifestSha256:record.manifestSha256,cacheRoot:this.cacheRoot};
  const effective=await this.effectiveConfiguration({originalSelected:structuredClone(selected),snapshotRoot:root,datasets:structuredClone(datasets),source:structuredClone(source)});
  requireValue(effective&&typeof effective==='object'&&!Array.isArray(effective),'Compiled module configuration binding failed');
  const original={...effective},boundSource=original[this.sourceField];delete original[this.sourceField];
  requireValue(canonical(original)===canonical(selected)&&canonical(boundSource)===canonical(source),'Module binding must preserve original configuration and exact native source');
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
  requireValue(before.isFile()&&!before.isSymbolicLink()&&before.nlink===1n,'Unsafe legacy module candidate');if(before.size!==BigInt(object.bytes))return false;
  const h=crypto.createHash('sha256');let handle,bytes=0,receipt;
  try{handle=await fsp.open(destination,'wx');const initial=await this.openedCacheHandle(handle,destination,0);for await(const chunk of fs.createReadStream(source,{highWaterMark:READ_BYTES})){canceled(signal);bytes+=chunk.length;if(bytes>object.bytes)break;h.update(chunk);await handle.writeFile(chunk);}await handle.sync();
   const stamp=await this.openedCacheHandle(handle,destination,bytes);requireValue(sameIdentity(initial,stamp),'Legacy module writer identity changed');receipt={stamp,bytes,sha256:h.digest('hex')};
  }finally{await handle?.close();}
  const after=await fsp.lstat(source,{bigint:true}),stable=after.isFile()&&!after.isSymbolicLink()&&sameFile(before,after);
  if(!stable||bytes!==object.bytes||receipt.sha256!==object.sha256){this.removeOwnedFile(destination,receipt);return false;}
  this.ownedFile(destination,receipt);this.rememberStagedFile(destination,receipt);return true;
 }
 async removeStaging(directory){
  const root=path.join(this.cacheRoot,'staging'),owners=stagingOwners.get(this),owner=owners.get(directory);
  requireValue(path.dirname(directory)===root&&/^[a-f0-9-]{36}$/.test(path.basename(directory)),'Unsafe staging cleanup refused');
  if(!owner)return false;
  try{
   if(!fs.existsSync(directory)){owners.delete(directory);return true;}
   this.ownedStaging(directory,owner);
   // Never recursively remove a tree: every member must have an original receipt.
   for(const [relative,receipt] of owner.files){const file=path.join(directory,relative);requireValue(sameIdentity(fs.lstatSync(directory,{bigint:true}),owner.root),'Staging root identity changed');this.ownedFile(file,receipt);fs.unlinkSync(file);}
   for(const relative of [...owner.directories.keys()].sort((a,b)=>b.split(path.sep).length-a.split(path.sep).length)){
    const file=path.join(directory,relative),st=fs.lstatSync(file,{bigint:true});requireValue(st.isDirectory()&&!st.isSymbolicLink()&&sameIdentity(st,owner.directories.get(relative)),'Staging directory identity changed');fs.rmdirSync(file);
   }
   const st=fs.lstatSync(directory,{bigint:true});requireValue(st.isDirectory()&&!st.isSymbolicLink()&&sameIdentity(st,owner.root),'Staging root identity changed');fs.rmdirSync(directory);owners.delete(directory);return true;
  }catch{return false;}
 }
 async materialize(manifest,checked,selected,{signal,onStatus}={}){
  const final=path.join(this.cacheRoot,'snapshots',manifest.sha256);
  if(fs.existsSync(final)){await this.validateSnapshot(final,manifest,{signal});return;}
  await this.disk(manifest.totalBytes*2);const staging=path.join(this.cacheRoot,'staging',crypto.randomUUID());await this.ensureDirectory(path.dirname(staging));fs.mkdirSync(staging);
  const root=fs.lstatSync(staging,{bigint:true});requireValue(root.isDirectory()&&!root.isSymbolicLink(),'Unsafe new staging root');
  const owner={root,directories:new Map(),files:new Map()};stagingOwners.get(this).set(staging,owner);let completed=0;
  try{
   for(const dataset of manifest.value.datasets){
    const adapter=this.registry[dataset.kind],legacy=typeof adapter.probeLegacy==='function'?await adapter.probeLegacy({originalSelected:structuredClone(selected),dataset:structuredClone(dataset),signal}):null;
    for(const object of dataset.objects){
     canceled(signal);const destination=path.join(staging,dataset.datasetId,...adapter.roles[object.role].path.split('/'));this.stageDirectory(staging,path.dirname(destination),owner);
     if(await this.seed(legacy?.[object.role],destination,object,selected,{signal})){completed+=object.bytes;continue;}
     let handle,receipt;const h=crypto.createHash('sha256');let bytes=0;
     try{
      handle=await fsp.open(destination,'wx');
      const initial=await this.openedCacheHandle(handle,destination,0);
      for(const segment of object.segments){
       const file=await this.segment(checked.value.releaseTag,segment,{signal,onProgress:n=>this.status('downloading',checked.value,{onStatus,totalBytes:manifest.totalBytes,receivedBytes:Math.min(manifest.totalBytes,completed+bytes+n)})});
       for await(const chunk of fs.createReadStream(file,{highWaterMark:READ_BYTES})){canceled(signal);bytes+=chunk.length;requireValue(bytes<=object.bytes,'Logical module role exceeds its bound');h.update(chunk);await handle.writeFile(chunk);}
      }
      await handle.sync();const stamp=await this.openedCacheHandle(handle,destination,bytes);requireValue(sameIdentity(initial,stamp),'Staged module writer identity changed');receipt={stamp,bytes,sha256:h.digest('hex')};
     }finally{await handle?.close();}
     requireValue(bytes===object.bytes&&receipt.sha256===object.sha256,'Logical module role integrity failed');this.ownedFile(destination,receipt);this.rememberStagedFile(destination,receipt);completed+=bytes;
    }
   }
   this.status('verifying',checked.value,{onStatus,totalBytes:manifest.totalBytes,receivedBytes:completed});await this.validateSnapshot(staging,manifest,{signal});
   canceled(signal);this.ownedStaging(staging,owner);requireValue(!fs.existsSync(final),'Concurrent module snapshot replacement refused');fs.renameSync(staging,final);this.ownedStaging(final,owner);
  }finally{await this.removeStaging(staging);}
 }
 prepare(selected,options={}){return this.operation(selected,options,(original,opts,identity)=>this.check(original,opts,identity,false));}
 stage(selected,options={}){return this.operation(selected,options,(original,opts,identity)=>this.check(original,opts,identity,true));}
 async check(selected,options,identity,background){
  const state=await this.state(),{signal,onStatus}=options;this.status('checking',null,{onStatus});
  try{
   const envelope=protocol.parseJson(await this.transport.currentPointer({signal})),checked=protocol.pointer(this.appId,envelope,this.publicKeys,state.highwater,this.channel);
   const prior=state.accepted,value=checked.value;
   let manifest;
   if(prior&&prior.identityDigest===identity&&prior.pointerDigest===checked.digest&&prior.catalogSequence===value.catalogSequence&&prior.releaseTag===value.releaseTag&&prior.releaseCommit===value.releaseCommit&&prior.manifestSha256===value.manifest.sha256){
    // Only the protected accepted journal attests a prior successful public/tag
    // REST check. A loose cache file or high-water alone cannot create one.
    // Reverify both signed envelopes with CURRENT keys: exact envelope equality
    // binds the key ID/epoch as well as repo, tag, commit and manifest bytes.
    const cached=await this.metadata(prior);
    if(canonical(cached.checked.envelope)===canonical(checked.envelope))manifest=protocol.manifest(this.appId,cached.manifest.bytes,checked,this.registry,this.requiredKinds,this.channel);
   }
   if(!manifest){await this.transport.verifyRelease(value,{signal});manifest=protocol.manifest(this.appId,await this.transport.manifest(value,{signal}),checked,this.registry,this.requiredKinds,this.channel);}
   const record=this.record(checked,manifest,identity);
   requireValue(await this.owner(selected)===identity,'Owner approval changed during module check');canceled(signal);
   await this.immutable('pointers/'+checked.digest+'.json',Buffer.from(canonical(envelope)));await this.immutable('manifests/'+manifest.sha256+'.json',manifest.bytes);
   state.highwater={catalogSequence:record.catalogSequence,pointerDigest:record.pointerDigest};state.accepted=record;await this.save(state);
   // An exact staged record needs no restaging, but candidate still freshly
   // verifies every byte, compiled reader and owner before this check returns.
   const alreadyStaged=state.staged&&RECORD.every(key=>state.staged[key]===record[key])&&fs.existsSync(path.join(this.cacheRoot,'snapshots',record.manifestSha256));
   if(!alreadyStaged){
    await this.materialize(manifest,checked,selected,options);requireValue(await this.owner(selected)===identity,'Owner approval changed during module staging');canceled(signal);
    state.staged=record;await this.save(state);
   }
   const unchanged=state.active?.pointerDigest===record.pointerDigest&&state.active?.identityDigest===identity;
   return this.candidate(record,selected,identity,{...options,phase:background&&!unchanged?'update-ready':'ready'});
  }catch(error){
   if(error?.retryableNetwork===true&&OFFLINE.has(error.reason)&&state.active)return this.candidate(state.active,selected,identity,{...options,phase:'offline'});
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
