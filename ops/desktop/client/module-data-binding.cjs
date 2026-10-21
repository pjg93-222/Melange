'use strict';
// Read-only revalidation for a native-prepared runtime configuration. This is
// not owner authorization, a high-water journal, or a renderer/settings API.
const fs=require('node:fs'),fsp=fs.promises,path=require('node:path'),crypto=require('node:crypto');
const {canonical}=require('./access-client.cjs');
const {exact}=require('./dataset-protocol.cjs');
const protocol=require('./github-module-protocol.cjs');
const {physicalPath}=require('./runtime-roots.cjs');
const SOURCE_FIELDS=['schemaVersion','appId','repository','catalogSequence','releaseTag','releaseCommit','pointerDigest','manifestSha256','cacheRoot'];
const {requireValue,fail}=protocol;
function canceled(signal){if(signal?.aborted)throw fail('cancelled','Module binding verification cancelled');}
function inside(root,target,equal=false){const rel=path.relative(root,target);return (equal||rel!=='')&&rel!=='..'&&!rel.startsWith('..'+path.sep)&&!path.isAbsolute(rel);}
function overlaps(a,b){a=physicalPath(a);b=physicalPath(b);return inside(a,b,true)||inside(b,a,true);}
function same(a,b){return a.dev===b.dev&&a.ino===b.ino&&a.mode===b.mode&&a.nlink===b.nlink&&a.size===b.size&&a.mtimeNs===b.mtimeNs&&a.ctimeNs===b.ctimeNs;}
function sameDirectory(a,b,strict){return strict?same(a,b):a.dev===b.dev&&a.ino===b.ino&&a.mode===b.mode;}
class ReadView{
 constructor(base,root,signal){this.base=base;this.root=root;this.signal=signal;this.directories=new Map();this.files=new Map();}
 async directory(target){
  canceled(this.signal);requireValue(inside(this.base,target,true),'Module binding leaves its native cache boundary');
  let current=this.base;
  for(const part of ['',...path.relative(this.base,target).split(path.sep).filter(Boolean)]){
   if(part)current=path.join(current,part);
   const stat=await fsp.lstat(current,{bigint:true});
   requireValue(stat.isDirectory()&&!stat.isSymbolicLink(),'Module binding directory is unsafe');
   requireValue(inside(this.base,await fsp.realpath(current),true),'Module binding directory leaves its cache boundary');
   // Native profile/LOCALAPPDATA ancestors can receive unrelated application
   // writes. Their identity must stay fixed; cache directories stay byte/stamp
   // stable as well while the caller holds the native transition lease.
   const prior=this.directories.get(current);requireValue(!prior||sameDirectory(prior,stat,inside(this.root,current,true)),'Module binding directory changed');this.directories.set(current,stat);
  }
 }
 async read(file,maxBytes,{bytes,sha256,retain=false}={}){
  canceled(this.signal);requireValue(inside(this.root,file),'Module binding file leaves its cache');
  await this.directory(path.dirname(file));
  let handle;
  try{
   handle=await fsp.open(file,fs.constants.O_RDONLY|(fs.constants.O_NOFOLLOW||0));
   const before=await handle.stat({bigint:true}),named=await fsp.lstat(file,{bigint:true});
   requireValue(before.isFile()&&named.isFile()&&!named.isSymbolicLink()&&before.nlink===1n&&named.nlink===1n&&same(before,named)&&before.size<=BigInt(maxBytes),'Module binding file is unsafe');
   requireValue(inside(this.root,await fsp.realpath(file)),'Module binding file leaves its cache');
   if(bytes!==undefined)requireValue(before.size===BigInt(bytes),'Module binding file size differs');
   const hash=crypto.createHash('sha256'),chunks=[];let received=0;
   const buffer=Buffer.alloc(64*1024);
   while(true){
    canceled(this.signal);const result=await handle.read(buffer,0,buffer.length,null);if(result.bytesRead===0)break;
    received+=result.bytesRead;requireValue(BigInt(received)<=before.size,'Module binding file grew during verification');
    const chunk=buffer.subarray(0,result.bytesRead);hash.update(chunk);if(retain)chunks.push(Buffer.from(chunk));
   }
   const digest=hash.digest('hex'),after=await handle.stat({bigint:true}),current=await fsp.lstat(file,{bigint:true});
   requireValue(after.isFile()&&current.isFile()&&!current.isSymbolicLink()&&after.nlink===1n&&current.nlink===1n&&same(before,after)&&same(after,current)&&BigInt(received)===before.size,'Module binding file changed during verification');
   if(sha256!==undefined)requireValue(digest===sha256,'Module binding file integrity failed');
   const prior=this.files.get(file);requireValue(!prior||same(prior,current),'Module binding file changed');this.files.set(file,current);
   return retain?Buffer.concat(chunks):{bytes:received,sha256:digest};
  }finally{await handle?.close();}
 }
 async unchanged(){
  for(const [directory,before] of this.directories){canceled(this.signal);const stat=await fsp.lstat(directory,{bigint:true});requireValue(stat.isDirectory()&&!stat.isSymbolicLink()&&sameDirectory(before,stat,inside(this.root,directory,true))&&inside(this.base,await fsp.realpath(directory),true),'Module binding directory changed during verification');}
  for(const [file,before] of this.files){canceled(this.signal);const stat=await fsp.lstat(file,{bigint:true});requireValue(stat.isFile()&&!stat.isSymbolicLink()&&stat.nlink===1n&&same(before,stat),'Module binding file changed during reader verification');}
 }
 async closure(root,expectedFiles,expectedDirectories){
  const walk=async(directory,prefix='')=>{
   await this.directory(directory);
   for(const entry of await fsp.readdir(directory,{withFileTypes:true})){
    canceled(this.signal);const relative=prefix+entry.name,file=path.join(directory,entry.name);
    requireValue(!entry.isSymbolicLink(),'Module binding snapshot reparse point refused');
    if(entry.isDirectory()){requireValue(expectedDirectories.delete(relative),'Unexpected module binding directory');await walk(file,relative+'/');}
    else requireValue(entry.isFile()&&expectedFiles.delete(relative),'Unexpected module binding file');
   }
  };
  await walk(root);requireValue(expectedFiles.size===0&&expectedDirectories.size===0,'Module binding snapshot is incomplete');
 }
}
async function validateModuleBinding({appId,profile,configuration,publicKeys,registry,requiredKinds=Object.keys(registry||{}),signal,protectedRoots=[]}){
 try{
  canceled(signal);const app=protocol.configuration(appId);protocol.checkedRegistry(appId,registry,requiredKinds);
  requireValue(configuration&&typeof configuration==='object'&&!Array.isArray(configuration)&&typeof configuration.dataDirectory==='string'&&path.isAbsolute(configuration.dataDirectory),'Original module workspace is required');
  requireValue(!Object.hasOwn(configuration,'ownerGitHubData'),'Unexpected module workspace override');
  requireValue(typeof profile==='string'&&path.isAbsolute(profile)&&Array.isArray(protectedRoots)&&protectedRoots.every(root=>typeof root==='string'&&path.isAbsolute(root)),'Native module boundaries are required');
  const original=structuredClone(configuration),source=original.ownerGitHubModuleData;exact(source,SOURCE_FIELDS);
  requireValue(source.schemaVersion===1&&source.appId===appId&&source.repository===app.repository&&protocol.integer(source.catalogSequence)&&source.catalogSequence>0&&protocol.hash(source.pointerDigest)&&protocol.hash(source.manifestSha256)&&typeof source.cacheRoot==='string'&&path.isAbsolute(source.cacheRoot),'Invalid native module source binding');
  const profileStat=await fsp.lstat(profile);requireValue(profileStat.isDirectory()&&!profileStat.isSymbolicLink(),'Native module profile is unsafe');
  const nativeProfile=await fsp.realpath(profile);
  const choices=[{base:nativeProfile,root:path.join(nativeProfile,'packs','github-module-data')},...(process.env.LOCALAPPDATA?[{base:path.resolve(process.env.LOCALAPPDATA),root:path.resolve(process.env.LOCALAPPDATA,'MelangeData',appId,'github-module-data')}]:[])];
  const selected=choices.find(choice=>path.resolve(source.cacheRoot)===path.resolve(choice.root));
  requireValue(selected&&source.cacheRoot===path.resolve(selected.root),'Unapproved native module cache root');
  const cacheRoot=path.resolve(selected.root),base=path.resolve(selected.base);
  for(const protectedRoot of [original.dataDirectory,path.join(nativeProfile,'state'),...protectedRoots])requireValue(!overlaps(cacheRoot,protectedRoot),'Module binding cache overlaps original or protected state');
  const view=new ReadView(base,cacheRoot,signal);await view.directory(cacheRoot);
  const envelope=protocol.parseJson(await view.read(path.join(cacheRoot,'pointers',source.pointerDigest+'.json'),32768,{retain:true}));
  const checked=protocol.pointer(appId,envelope,publicKeys);
  const expected={schemaVersion:1,appId,repository:app.repository,catalogSequence:checked.value.catalogSequence,releaseTag:checked.value.releaseTag,releaseCommit:checked.value.releaseCommit,pointerDigest:checked.digest,manifestSha256:checked.value.manifest.sha256,cacheRoot};
  requireValue(canonical(source)===canonical(expected),'Native module source differs from signed metadata');
  const manifest=protocol.manifest(appId,await view.read(path.join(cacheRoot,'manifests',source.manifestSha256+'.json'),protocol.MAX_MANIFEST,{bytes:checked.value.manifest.bytes,sha256:source.manifestSha256,retain:true}),checked,registry,requiredKinds);
  const snapshotRoot=path.join(cacheRoot,'snapshots',manifest.sha256),datasets=[],expectedFiles=new Set(),expectedDirectories=new Set();await view.directory(snapshotRoot);
  for(const dataset of manifest.value.datasets){
   canceled(signal);const adapter=registry[dataset.kind],root=path.join(snapshotRoot,dataset.datasetId),files={};await view.directory(root);
   for(const object of dataset.objects){
    const relative=dataset.datasetId+'/'+adapter.roles[object.role].path,file=path.join(snapshotRoot,...relative.split('/'));
    await view.read(file,object.bytes,{bytes:object.bytes,sha256:object.sha256});files[object.role]=file;expectedFiles.add(relative);
    let parent=path.posix.dirname(relative);while(parent!=='.'){expectedDirectories.add(parent);parent=path.posix.dirname(parent);}
   }
   requireValue(await adapter.validateSnapshot({dataset:structuredClone(dataset),root,files:{...files},signal})===true,'Compiled module reader rejected binding');
   datasets.push({kind:dataset.kind,datasetId:dataset.datasetId,revisionId:dataset.revisionId,root,files,objects:structuredClone(dataset.objects)});
  }
  await view.closure(snapshotRoot,expectedFiles,expectedDirectories);await view.unchanged();canceled(signal);
  requireValue(canonical(configuration)===canonical(original),'Original module configuration changed during verification');
  return {source:structuredClone(expected),snapshotRoot,datasets};
 }catch(error){if(error?.reason)throw error;throw fail('integrity','Module binding verification failed');}
}
module.exports={validateModuleBinding};
