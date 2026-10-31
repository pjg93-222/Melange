'use strict';
// One signed binary transfer. The SQLite transaction is a crash-released
// cross-process writer lock, not a trust receipt. Only final size/hash checks
// can publish a package; existing partial bytes never grant execution authority.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),{DatabaseSync}=require('node:sqlite');
const network=require('./network-transport.cjs');
const same=(a,b)=>a.dev===b.dev&&a.ino===b.ino;
const linkStable=(a,b)=>same(a,b)&&a.size===b.size&&a.mtimeNs===b.mtimeNs;
const stable=(a,b)=>same(a,b)&&a.size===b.size&&a.mtimeNs===b.mtimeNs&&a.ctimeNs===b.ctimeNs;
const fail=message=>Object.assign(new Error(message),{code:'BINARY_CACHE_INTEGRITY'});
function canceled(signal){if(signal?.aborted)throw Object.assign(new Error('Binary transfer cancelled'),{reason:'cancelled'});}
function directoryBoundary(directory){
 if(typeof directory!=='string'||!path.isAbsolute(directory)||process.platform==='win32'&&!/^[A-Za-z]:[\\/]/.test(directory))throw fail('A local absolute binary cache directory is required');
 const selected=path.resolve(directory),parents=[];let current=path.parse(selected).root;
 for(const part of ['',...path.relative(current,selected).split(path.sep).filter(Boolean)]){
  if(part)current=path.join(current,part);
  try{fs.lstatSync(current);}catch(error){if(error.code!=='ENOENT')throw error;try{fs.mkdirSync(current,{mode:0o700});}catch(created){if(created.code!=='EEXIST')throw created;}}
  const stat=fs.lstatSync(current,{bigint:true});if(!stat.isDirectory()||stat.isSymbolicLink())throw fail('A binary cache ancestor is unsafe');parents.push({path:current,stat});
 }
 const check=()=>{for(const row of parents){const now=fs.lstatSync(row.path,{bigint:true});if(!now.isDirectory()||now.isSymbolicLink()||!same(now,row.stat))throw fail('Binary cache ancestry changed');}};
 check();return {directory:selected,check};
}
function regular(file,{links=1n}={}){const stat=fs.lstatSync(file,{bigint:true});if(!stat.isFile()||stat.isSymbolicLink()||stat.nlink!==links)throw fail('A binary cache member is unsafe');return stat;}
function owned(file,identity,boundary,{links=1n,linkTransition=false}={}){boundary.check();const now=regular(file,{links});if(!(linkTransition?linkStable(now,identity):stable(now,identity)))throw fail('Binary cache member changed');return now;}
function removeOwned(file,identity,boundary,options){if(!identity)return false;try{owned(file,identity,boundary,options);fs.unlinkSync(file);return true;}catch{return false;}}
async function digestHandle(handle,pkg,signal){
 const before=await handle.stat({bigint:true});if(before.nlink!==1n)throw fail('Binary package link count differs');if(before.size!==BigInt(pkg.size))return {identity:before,valid:false};
 const sha256=crypto.createHash('sha256'),sha512=crypto.createHash('sha512'),buffer=Buffer.alloc(Math.min(4*1024*1024,pkg.size));let bytes=0;
 for(;;){canceled(signal);const {bytesRead}=await handle.read(buffer,0,buffer.length,bytes);if(!bytesRead)break;bytes+=bytesRead;if(bytes>pkg.size)throw fail('Binary package exceeds signed size');sha256.update(buffer.subarray(0,bytesRead));sha512.update(buffer.subarray(0,bytesRead));}
 if(!stable(before,await handle.stat({bigint:true})))throw fail('Binary package changed during verification');
 return {identity:before,valid:bytes===pkg.size&&sha256.digest('hex')===pkg.sha256&&sha512.digest('base64')===pkg.sha512};
}
async function downloadBinary({directory,manifest,manifestHash,url,open,signal,onProgress}){
 const pkg=manifest?.package;
 if(!/^[a-f0-9]{64}$/.test(manifestHash||'')||!pkg||!['melange','mentat','terrier'].includes(manifest.appId)||typeof manifest.version!=='string'||!/^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/.test(manifest.version)||pkg.name!==manifest.appId+'-'+manifest.version+'-win32-x64.exe'||!Number.isSafeInteger(pkg.size)||pkg.size<1||pkg.size>20*1024**3||!/^[a-f0-9]{64}$/.test(pkg.sha256||'')||typeof pkg.sha512!=='string'||Buffer.from(pkg.sha512,'base64').length!==64||Buffer.from(pkg.sha512,'base64').toString('base64')!==pkg.sha512||typeof open!=='function')throw fail('A complete signed binary identity is required');
 if(onProgress!==undefined&&typeof onProgress!=='function')throw fail('Invalid binary progress callback');
 let progressAt=-Infinity,progressBytes=-1;
 const progress=(received,resumed,{force=false}={})=>{const now=performance.now();if(!onProgress||received===progressBytes||!force&&now-progressAt<1000)return;progressBytes=received;progressAt=now;try{onProgress({received,total:pkg.size,resumed});}catch{}};
 canceled(signal);const boundary=directoryBoundary(directory),destination=path.join(boundary.directory,pkg.name),part=path.join(boundary.directory,'.'+manifestHash+'.part'),lockPath=path.join(boundary.directory,'.binary-transfer.sqlite');
 let db,locked=false,handle,identity,stream,linked=false,published=false;
 try{
  let lockBefore;for(const suffix of ['','-wal','-shm','-journal']){const file=lockPath+suffix;if(fs.existsSync(file)){const lock=regular(file);if(lock.size>3n*1024n*1024n)throw fail('Binary writer-lock metadata is too large');if(!suffix)lockBefore=lock;}}
  db=new DatabaseSync(lockPath);boundary.check();const lockNow=regular(lockPath);if(lockBefore&&!same(lockBefore,lockNow))throw fail('Binary writer lock changed');db.exec('PRAGMA trusted_schema=OFF; PRAGMA busy_timeout=0;');
  try{db.exec('BEGIN IMMEDIATE');locked=true;}catch{throw new Error('Another process owns the binary download cache. Retry later.');}
  if(fs.existsSync(destination)){
   const before=regular(destination);handle=await fs.promises.open(destination,'r');if(!same(before,await handle.stat({bigint:true})))throw fail('Cached binary changed before verification');
   const checked=await digestHandle(handle,pkg,signal);owned(destination,checked.identity,boundary);await handle.close();handle=null;owned(destination,checked.identity,boundary);
   if(checked.valid){progress(pkg.size,true,{force:true});return destination;}
   // Only byte mismatch authorizes removal of this exact derived cache member.
   owned(destination,checked.identity,boundary);fs.unlinkSync(destination);
  }
  const before=fs.existsSync(part)?regular(part):null;handle=await fs.promises.open(part,before?'r+':'wx+',0o600);identity=await handle.stat({bigint:true});
  if(identity.nlink!==1n||!identity.isFile()||before&&!stable(before,identity))throw fail('Binary partial identity changed');owned(part,identity,boundary);
  if(identity.size>BigInt(pkg.size))throw fail('Binary partial exceeds signed size');let offset=Number(identity.size);const resumed=offset>0;progress(offset,resumed,{force:true});
  if(offset<pkg.size){
   const remaining=pkg.size-offset,totalMs=Math.min(30*60*1000,Math.max(120000,60000+Math.ceil(remaining/(64*1024))*1000));
   stream=await open(url,{asset:true,signal,deadlineMs:totalMs,range:{offset,totalBytes:pkg.size}});owned(part,identity,boundary);
   for await(const chunk of stream){canceled(signal);if(offset+chunk.length>pkg.size)throw fail('Binary download exceeds signed size');let written=0;while(written<chunk.length){const result=await handle.write(chunk,written,chunk.length-written,offset+written);if(result.bytesWritten<=0)throw new Error('Binary cache write failed');written+=result.bytesWritten;}offset+=written;progress(offset,resumed);}
   await handle.sync();
  }
  const complete=await handle.stat({bigint:true});if(!same(complete,identity))throw fail('Binary writer identity changed');identity=complete;owned(part,identity,boundary);
  if(offset===pkg.size)progress(offset,resumed,{force:true});
  const checked=await digestHandle(handle,pkg,signal);if(!checked.valid)throw fail('Binary package integrity/hash differs from signed identity');owned(part,checked.identity,boundary);canceled(signal);
  // Exclusive publication never replaces an unrelated destination. Both links
  // are verified before removing our partial name; originals are never linked.
  fs.linkSync(part,destination);linked=true;const paired=owned(part,checked.identity,boundary,{links:2n,linkTransition:true});owned(destination,paired,boundary,{links:2n,linkTransition:true});fs.unlinkSync(part);
  const final=owned(destination,paired,boundary,{linkTransition:true});if(final.size!==BigInt(pkg.size))throw fail('Published binary size changed');published=true;return destination;
 }catch(error){
  stream?.destroy();const classified=network.classifyNetworkError(error);let last;
  if(handle){await handle.sync().catch(()=>{});last=await handle.stat({bigint:true}).catch(()=>null);await handle.close().catch(()=>{});handle=null;}
  if(linked&&!published&&last&&identity&&same(last,identity))removeOwned(destination,last,boundary,{links:last.nlink,linkTransition:true});
  const resumable=classified?.retryableNetwork===true||classified?.reason==='cancelled'||classified?.code==='ABORT_ERR';
  if(!resumable&&last&&identity&&same(last,identity))removeOwned(part,last,boundary,linked?{linkTransition:true}:undefined);
  throw classified;
 }finally{stream?.destroy();await handle?.close().catch(()=>{});if(locked)try{db.exec('ROLLBACK');}catch{}try{db?.close();}catch{}}
}
module.exports={downloadBinary};
