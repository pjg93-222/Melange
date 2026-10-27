'use strict';
// Remove only program trees created by this updater, while the original signed
// ZIP is still available. Local inventory/ownership files never authorize bytes.
const fs=require('node:fs'),fsp=fs.promises,path=require('node:path'),crypto=require('node:crypto');
const {appDefinition}=require('./apps.cjs');
const {verifyPackageFile}=require('./trust.cjs');
const {verifyDirectoryPackageProof}=require('./directory-package-proof.cjs');
const fail=message=>new Error('Directory retention: '+message);
const check=(value,message)=>{if(!value)throw fail(message);};
const key=value=>process.platform==='win32'?path.resolve(value).toLowerCase():path.resolve(value);
const within=(parent,child)=>key(child)===key(parent)||key(child).startsWith(key(parent)+path.sep);
const identity=info=>({dev:String(info.dev),ino:String(info.ino)});
const same=(a,b)=>a.dev===b.dev&&a.ino===b.ino;
const unchanged=(a,b)=>same(a,b)&&a.size===b.size&&a.mtimeNs===b.mtimeNs&&a.ctimeNs===b.ctimeNs;
function physical(directory){
 const info=fs.lstatSync(directory,{bigint:true});
 check(info.isDirectory()&&!info.isSymbolicLink()&&key(fs.realpathSync.native(directory))===key(directory),'directory is linked or redirected');
 return info;
}
function ancestors(directory){for(let current=path.resolve(directory);;){physical(current);const parent=path.dirname(current);if(parent===current)return;current=parent;}}
function regular(filename){
 const info=fs.lstatSync(filename,{bigint:true});
 check(info.isFile()&&!info.isSymbolicLink()&&info.nlink===1n&&key(fs.realpathSync.native(filename))===key(filename),'file is linked or nonregular');return info;
}
function treeSnapshot(directory,inventory){
 const files=new Set(['directory-package.json',...inventory.files.map(item=>item.path)]),directories=new Set();
 for(const filename of files){const components=filename.split('/');components.pop();while(components.length){directories.add(components.join('/'));components.pop();}}
 const result=new Map();
 function walk(current,prefix=''){
  result.set(prefix,physical(current));
  for(const entry of fs.readdirSync(current,{withFileTypes:true})){
   const relative=prefix?prefix+'/'+entry.name:entry.name,target=path.join(current,entry.name);
   check(!entry.isSymbolicLink(),'linked program entry');
   if(entry.isDirectory()){check(directories.has(relative),'unexpected program directory');walk(target,relative);}
   else{check(files.has(relative),'unexpected program file');result.set(relative,regular(target));}
  }
 }
 walk(directory);check(result.size===files.size+directories.size+1,'program tree is incomplete');return result;
}
async function removeVerifiedTree(directory,inventory,{archive,options,guard}){
 check(path.isAbsolute(directory)&&typeof guard==='function','owned directory guard required');
 await guard();const before=treeSnapshot(directory,inventory);
 await archive.verifyDirectory(directory,{...options,inventory});await guard();
 const after=treeSnapshot(directory,inventory);check(before.size===after.size,'program tree changed');
 for(const [relative,info]of before)check(after.has(relative)&&unchanged(info,after.get(relative)),'program entry changed');
 const parentGuard=async relative=>{await guard();let current=directory,prefix='';for(const component of relative.split('/').slice(0,-1)){
  current=path.join(current,component);prefix=prefix?prefix+'/'+component:component;check(same(before.get(prefix)||{},physical(current)),'program parent changed');
 }};
 // Delete only the authenticated plan. Never re-enumerate a tree for deletion:
 // an unexpected file added after verification must never become a target.
 for(const [relative,info]of before){
  if(!relative||info.isDirectory())continue;await parentGuard(relative);const filename=path.join(directory,...relative.split('/'));
  ancestors(path.dirname(filename));check(unchanged(info,regular(filename)),'program file changed');fs.unlinkSync(filename);
 }
 const directories=[...before].filter(([,info])=>info.isDirectory()).sort((a,b)=>b[0].split('/').length-a[0].split('/').length||b[0].length-a[0].length);
 for(const [relative,info]of directories){await parentGuard(relative);const target=relative?path.join(directory,...relative.split('/')):directory;
  ancestors(path.dirname(target));check(same(info,physical(target)),'program directory changed');fs.rmdirSync(target);
 }
}
class DirectoryRetention{
 constructor({root,appId,recordFile,archive,verifyProof=verifyDirectoryPackageProof}){
  check(path.isAbsolute(root)&&path.isAbsolute(recordFile),'absolute paths required');
  this.root=path.resolve(root);this.appId=appId;this.product=appDefinition(appId).name;this.recordFile=path.resolve(recordFile);
  check(!within(this.root,this.recordFile),'ownership record must be outside program folders');
  this.archive=archive||require('./directory-package.cjs');this.verifyProof=verifyProof;
 }
 target(manifest){
  this.verifyProof(manifest);
  check(manifest.appId===this.appId&&manifest.package.entrypoint===this.product+'.exe','application mismatch');
  check(/^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/.test(manifest.version),'invalid version');
  return path.join(this.root,this.product+'-'+manifest.version);
 }
 read(){
  ancestors(this.root);const rootIdentity=identity(physical(this.root));
  ancestors(path.dirname(this.recordFile));
  if(!fs.existsSync(this.recordFile))return {schemaVersion:1,appId:this.appId,root:this.root,rootIdentity,created:{}};
  check(regular(this.recordFile).size<=1024n*1024n,'ownership record is too large');
  const value=JSON.parse(fs.readFileSync(this.recordFile,'utf8'));
  check(value?.schemaVersion===1&&value.appId===this.appId&&value.root===this.root&&same(value.rootIdentity||{},rootIdentity),'ownership root changed');
  check(value.created&&typeof value.created==='object'&&!Array.isArray(value.created)&&Object.keys(value.created).length<=4096,'invalid ownership records');
  for(const [version,item]of Object.entries(value.created))check(/^\d+\.\d+\.\d+$/.test(version)&&item&&/^[0-9]+$/.test(item.dev)&&/^[0-9]+$/.test(item.ino),'invalid program ownership');
  return value;
 }
 async write(value){
  ancestors(path.dirname(this.recordFile));check(same(identity(physical(this.root)),value.rootIdentity),'ownership root changed');
  if(fs.existsSync(this.recordFile))regular(this.recordFile);
  const bytes=JSON.stringify(value);check(Buffer.byteLength(bytes)<=1024*1024,'ownership record is too large');
  const temporary=this.recordFile+'.'+crypto.randomUUID()+'.tmp';
  try{await fsp.writeFile(temporary,bytes,{flag:'wx',mode:0o600});ancestors(path.dirname(this.recordFile));
   if(fs.existsSync(this.recordFile))regular(this.recordFile);await fsp.rename(temporary,this.recordFile);
  }finally{try{regular(temporary);await fsp.unlink(temporary);}catch{}}
 }
 async recordCreated(manifest,directory,expectedIdentity){
  const expected=this.target(manifest);check(key(expected)===key(directory),'created program path mismatch');
  const value=this.read(),owned=identity(physical(expected));
  if(expectedIdentity)check(same(owned,identity(expectedIdentity)),'created program ownership changed');
  if(value.created[manifest.version])check(same(value.created[manifest.version],owned),'program ownership changed');
  else{check(Object.keys(value.created).length<4096,'ownership record limit reached');value.created[manifest.version]=owned;}
  await this.write(value);
 }
 async prune({candidates,keepVersions=[],currentExecutable=process.execPath}){
  const result={removed:[],preserved:[]};
  check(Array.isArray(candidates)&&candidates.length<=32&&Array.isArray(keepVersions),'invalid retention request');
  check(typeof currentExecutable==='string'&&path.isAbsolute(currentExecutable),'running executable required');
  const keep=new Set(keepVersions),seen=new Set();let value;
  try{value=this.read();}catch{return {removed:[],preserved:candidates.map(item=>item.manifest?.version).filter(Boolean)};}
  for(const candidate of candidates){
   const manifest=candidate?.manifest,version=manifest?.version;if(seen.has(version))continue;seen.add(version);
   try{
    const directory=this.target(manifest),owned=value.created[version];
    check(owned&&!keep.has(version)&&!within(directory,currentExecutable),'program is retained or not updater-owned');
    const guard=()=>{ancestors(this.root);check(same(identity(physical(this.root)),value.rootIdentity)&&same(identity(physical(directory)),owned),'program ownership changed');};
    guard();await verifyPackageFile(candidate.filename,manifest);
    const options={appId:this.appId,version,entrypoint:manifest.package.entrypoint,archive:manifest.package};
    const inventory=await this.archive.inspect(candidate.filename,options);
    await removeVerifiedTree(directory,inventory,{archive:this.archive,options,guard});
    delete value.created[version];await this.write(value);result.removed.push(version);
   }catch{result.preserved.push(version);}
  }
  return result;
 }
}
module.exports={DirectoryRetention,removeVerifiedTree};
