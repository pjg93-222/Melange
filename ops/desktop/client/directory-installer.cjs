'use strict';
// Program-only updates. Neither profile/data directories nor existing program
// folders are removed. Every activation rechecks the authenticated ZIP inventory.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {appDefinition}=require('./apps.cjs');
const {verifyPackageFile}=require('./trust.cjs');
const {verifyWindowsPackage}=require('./native-signature.cjs');
const {verifyDirectoryPackageProof}=require('./directory-package-proof.cjs');
const {captureStagingOwnership,assertStagingOwnership,cleanupStaging}=require('./directory-package.cjs');
const {removeVerifiedTree}=require('./directory-retention.cjs');
class DirectoryInstaller{
 constructor({root,appId,activate,archive,verifyNativePackage=verifyWindowsPackage,verifyProof=verifyDirectoryPackageProof}){
  if(!path.isAbsolute(root))throw new Error('Application update root must be absolute.');
  this.root=path.resolve(root);this.appId=appId;this.product=appDefinition(appId).name;
  this.activate=activate;this.archive=archive||require('./directory-package.cjs');
  this.verifyNativePackage=verifyNativePackage;this.verifyProof=verifyProof;
 }
 options(manifest){
  this.verifyProof(manifest);
  if(manifest.appId!==this.appId||manifest.package.entrypoint!==this.product+'.exe')throw new Error('Directory update application mismatch.');
  return {appId:this.appId,version:manifest.version,entrypoint:manifest.package.entrypoint,archive:manifest.package};
 }
 destination(manifest){
  this.options(manifest);
  if(!/^[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?$/.test(manifest.version))throw new Error('Invalid directory update version.');
  return path.join(this.root,this.product+'-'+manifest.version);
 }
 async verify(filename,manifest){
  const options=this.options(manifest),directory=this.destination(manifest);
  await verifyPackageFile(filename,manifest);
  const inventory=await this.archive.inspect(filename,options);
  await this.archive.verifyDirectory(directory,{...options,inventory});
  const executable=path.join(directory,options.entrypoint);
  await this.verifyNativePackage(executable,manifest.publisherThumbprints,{enforce:true});
  // A signature check can be slow. Recheck files immediately before returning a
  // runnable path, with inventory recovered from the authenticated archive.
  await this.archive.verifyDirectory(directory,{...options,inventory});
  await verifyPackageFile(filename,manifest);
  return {directory,executable};
 }
 async prepare(filename,manifest){
  const options=this.options(manifest),directory=this.destination(manifest);
  await verifyPackageFile(filename,manifest);
  if(fs.existsSync(directory))return this.verify(filename,manifest);
  fs.mkdirSync(this.root,{recursive:true});
  const staging=path.join(this.root,'.'+this.appId+'-'+crypto.randomUUID()+'.staging');
  let owned=null,rootOwner=null;
  try{
   // extract exclusively creates staging and rejects link/redirected parents.
   await this.archive.extract(filename,staging,options);
   owned=await captureStagingOwnership(staging);
   rootOwner=await captureStagingOwnership(this.root);
   await this.verifyNativePackage(path.join(staging,options.entrypoint),manifest.publisherThumbprints,{enforce:true});
   await verifyPackageFile(filename,manifest);
   // Never replace a folder that appeared while verification was running.
   if(fs.existsSync(directory))throw new Error('The target version folder already exists.');
   await assertStagingOwnership(this.root,rootOwner);await assertStagingOwnership(staging,owned);
   fs.renameSync(staging,directory);
   const promotedOwner=owned;owned=null;
   try{return {...await this.verify(filename,manifest),created:true,ownership:promotedOwner};}
   catch(error){
    // A failed final check must not strand a corrupt final version or remove a
    // replacement directory. Quarantine only the exact tree we just promoted.
    error.directoryStageFailed=true;
    try{
     await assertStagingOwnership(this.root,rootOwner);await assertStagingOwnership(directory,promotedOwner);
     if(fs.existsSync(staging))throw new Error('The original staging path is occupied.');
     fs.renameSync(directory,staging);error.stagingDirectory=staging;
     error.stagingOwnership={dev:String(promotedOwner.dev),ino:String(promotedOwner.ino)};
     error.stagingRootOwnership={dev:String(rootOwner.dev),ino:String(rootOwner.ino)};
    }catch(quarantineError){error.quarantineError=quarantineError.message;}
    throw error;
   }
  }finally{
   // The random path alone is insufficient: another process can replace it.
   if(owned)try{await cleanupStaging(staging,owned);}catch{}
  }
 }
 async clearFailedStage(filename,manifest,failure){
  const options=this.options(manifest),directory=failure?.directory;
  const asIdentity=value=>{
   if(!value||typeof value.dev!=='string'||typeof value.ino!=='string'||!/^\d+$/.test(value.dev)||!/^\d+$/.test(value.ino))throw new Error('Failed staging ownership is unavailable.');
   return {dev:BigInt(value.dev),ino:BigInt(value.ino)};
  };
  const same=(a,b)=>process.platform==='win32'?a.toLowerCase()===b.toLowerCase():a===b;
  if(typeof directory!=='string'||!path.isAbsolute(directory)||!same(path.dirname(path.resolve(directory)),this.root)||
     !new RegExp('^\\.'+this.appId+'-[0-9a-f-]{36}\\.staging$').test(path.basename(directory)))throw new Error('Failed staging path is unavailable or outside the application root.');
  const owned=asIdentity(failure.ownership),rootOwner=asIdentity(failure.rootOwnership);
  try{
   await assertStagingOwnership(this.root,rootOwner);await assertStagingOwnership(directory,owned);
   await verifyPackageFile(filename,manifest);
   const inventory=await this.archive.inspect(filename,options);
   await removeVerifiedTree(directory,inventory,{archive:this.archive,options,guard:async()=>{
    await assertStagingOwnership(this.root,rootOwner);await assertStagingOwnership(directory,owned);
   }});
  }catch(error){throw new Error('The failed update folder was preserved at '+directory+': '+error.message);}
 }
 async launch(filename,manifest,run){
  const target=await this.verify(filename,manifest);
  if(typeof this.activate!=='function')throw new Error('Directory update activation is unavailable.');
  await this.activate(target.executable,Boolean(run));
  return target;
 }
}
module.exports={DirectoryInstaller};
