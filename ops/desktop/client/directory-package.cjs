'use strict';
// The caller authenticates the entire ZIP (release manifest, hash and publisher
// proof) before using it. An inventory read from an installed directory is never
// an authority: activation must pass the inventory from that authenticated ZIP.
const fs=require('node:fs'),fsp=fs.promises,path=require('node:path'),crypto=require('node:crypto');
const {Transform}=require('node:stream');
const {pipeline}=require('node:stream/promises');
const yauzl=require('yauzl');
const INVENTORY='directory-package.json';
const ENTRYPOINTS=Object.freeze({melange:'Melange.exe',mentat:'Mentat.exe',terrier:'Terrier.exe'});
const DEFAULT_LIMITS=Object.freeze({maxArchiveBytes:4*1024**3,maxTotalBytes:8*1024**3,maxFileBytes:2*1024**3,maxFiles:100000,maxInventoryBytes:16*1024**2,maxPathLength:240,maxRatio:1000});
const fail=message=>Object.assign(new Error('Directory package: '+message),{code:'DIRECTORY_PACKAGE_INVALID'});
const requireValue=(value,message)=>{if(!value)throw fail(message);};
const caseKey=value=>value.normalize('NFC').toUpperCase();
function limitsFor(options={}){
 const limits={...DEFAULT_LIMITS,...options.limits};
 for(const [key,value]of Object.entries(limits))requireValue(Object.hasOwn(DEFAULT_LIMITS,key)&&Number.isSafeInteger(value)&&value>0&&value<=DEFAULT_LIMITS[key],'invalid resource limit');
 return limits;
}
function safePath(value,limits=DEFAULT_LIMITS){
 requireValue(typeof value==='string'&&value.length>0&&value.length<=limits.maxPathLength&&value===value.normalize('NFC'),'invalid file path');
 requireValue(!/[\\\x00-\x1f\x7f:<>"|?*]/.test(value)&&!value.startsWith('/')&&!value.endsWith('/'),'unsafe Windows file path');
 for(const component of value.split('/')){
  requireValue(component!==''&&component!=='.'&&component!=='..'&&!/[. ]$/.test(component),'unsafe path component');
  requireValue(!/^(?:CON|PRN|AUX|NUL|CLOCK\$|CONIN\$|CONOUT\$|COM[1-9¹²³]|LPT[1-9¹²³])(?:\.|$)/i.test(component),'reserved Windows filename');
 }
 return value;
}
function identity(options){
 requireValue(options&&ENTRYPOINTS[options.appId]===options.entrypoint,'application entrypoint mismatch');
 requireValue(typeof options.version==='string'&&/^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$/.test(options.version),'invalid application version');
 return options;
}
function keysExactly(object,keys){return object&&typeof object==='object'&&!Array.isArray(object)&&Object.keys(object).sort().join('|')===keys.slice().sort().join('|');}
function validateInventory(value,options,limits){
 identity(options);
 requireValue(keysExactly(value,['schemaVersion','appId','version','entrypoint','files'])&&value.schemaVersion===1&&value.appId===options.appId&&value.version===options.version&&value.entrypoint===options.entrypoint,'inventory identity mismatch');
 requireValue(Array.isArray(value.files)&&value.files.length>0&&value.files.length<=limits.maxFiles,'invalid inventory file count');
 const files=new Map(),directories=new Map();let total=0;
 for(const item of value.files){
  requireValue(keysExactly(item,['path','size','sha256']),'invalid inventory file record');
  safePath(item.path,limits);const key=caseKey(item.path);
  requireValue(key!==caseKey(INVENTORY)&&!files.has(key),'duplicate or reserved inventory path');
  requireValue(Number.isSafeInteger(item.size)&&item.size>=0&&item.size<=limits.maxFileBytes&&typeof item.sha256==='string'&&/^[a-f0-9]{64}$/.test(item.sha256),'invalid inventory size or digest');
  total+=item.size;requireValue(Number.isSafeInteger(total)&&total<=limits.maxTotalBytes,'expanded package is too large');
  files.set(key,item);
  const parts=item.path.split('/');parts.pop();
  while(parts.length){const parent=parts.join('/'),parentKey=caseKey(parent),old=directories.get(parentKey);requireValue(!old||old===parent,'directory case alias');directories.set(parentKey,parent);parts.pop();}
 }
 for(const key of directories.keys())requireValue(!files.has(key)&&key!==caseKey(INVENTORY),'file and directory collision');
 requireValue(files.get(caseKey(options.entrypoint))?.path===options.entrypoint,'entrypoint is missing');
 requireValue(files.get(caseKey('resources/app.asar'))?.path==='resources/app.asar','application archive is missing');
 return {inventory:value,files,directories,total};
}
const samePath=(a,b)=>process.platform==='win32'?path.resolve(a).toLowerCase()===path.resolve(b).toLowerCase():path.resolve(a)===path.resolve(b);
const sameFile=(a,b)=>a.dev===b.dev&&a.ino===b.ino&&a.size===b.size&&a.mtimeNs===b.mtimeNs&&a.ctimeNs===b.ctimeNs;
const sameDirectory=(a,b)=>a.dev===b.dev&&a.ino===b.ino;
async function physicalDirectory(directory){
 const requested=path.resolve(directory),info=await fsp.lstat(requested,{bigint:true});
 requireValue(info.isDirectory()&&!info.isSymbolicLink()&&samePath(requested,await fsp.realpath(requested)),'directory is linked or redirected');
 return info;
}
async function ancestors(directory){
 let current=path.resolve(directory);
 for(;;){await physicalDirectory(current);const parent=path.dirname(current);if(parent===current)break;current=parent;}
}
async function regularFile(file){
 const info=await fsp.lstat(file,{bigint:true});
 requireValue(info.isFile()&&!info.isSymbolicLink()&&info.nlink===1n&&samePath(file,await fsp.realpath(file)),'file is linked, redirected or nonregular');
 return info;
}
async function assertDirectory(directory,expected){
 requireValue(sameDirectory(expected,await physicalDirectory(directory)),'directory identity changed');
}
function stagingDirectories(root,initial){
 const known=new Map([[root,initial]]),creating=new Map();
 async function check(directory){
  const expected=known.get(directory);requireValue(expected,'staging parent was not created by this extraction');
  // realpath resolves the complete ancestor chain. Checking the immediate
  // parent's canonical path plus remembered identity also detects redirection
  // or same-path replacement without repeating every ancestor syscall.
  await assertDirectory(directory,expected);
 }
 async function ensure(directory){
  if(known.has(directory))return check(directory);
  if(creating.has(directory))return creating.get(directory);
  const operation=(async()=>{
   await ensure(path.dirname(directory));await fsp.mkdir(directory,{mode:0o700});
   known.set(directory,await physicalDirectory(directory));
  })();
  creating.set(directory,operation);
  try{await operation;}finally{creating.delete(directory);}
 }
 return {async parent(relative,create=false){
  const target=path.join(root,...relative.split('/')),directory=path.dirname(target);
  await (create?ensure(directory):check(directory));return target;
 },checkRoot:()=>check(root)};
}
async function boundedJobs(items,operation){
 let cursor=0,failed=false,failure;
 await Promise.all(Array.from({length:Math.min(4,items.length)},async()=>{
  while(!failed){const next=cursor++;if(next>=items.length)return;
   try{await operation(items[next]);}catch(error){if(!failed){failed=true;failure=error;}return;}
  }
 }));
 // Every active operation closes its held handles before cleanup or success.
 if(failed)throw failure;
}
function openZip(file){return new Promise((resolve,reject)=>yauzl.open(file,{lazyEntries:true,autoClose:false,strictFileNames:true,validateEntrySizes:true},(error,zip)=>error?reject(error):resolve(zip)));}
function fdStat(fd){return new Promise((resolve,reject)=>fs.fstat(fd,{bigint:true},(error,value)=>error?reject(error):resolve(value)));}
function archiveIdentity(options,limits){
 const expected=options.archive;if(expected===undefined)return null;
 requireValue(expected&&Number.isSafeInteger(expected.size)&&expected.size>0&&expected.size<=limits.maxArchiveBytes,'invalid trusted archive size');
 requireValue(typeof expected.sha256==='string'&&/^[a-f0-9]{64}$/.test(expected.sha256),'invalid trusted archive SHA-256');
 requireValue(typeof expected.sha512==='string'&&Buffer.from(expected.sha512,'base64').length===64&&Buffer.from(expected.sha512,'base64').toString('base64')===expected.sha512,'invalid trusted archive SHA-512');
 return {size:expected.size,sha256:expected.sha256,sha512:expected.sha512};
}
async function verifyHeldArchive(zip,expected,before){
 const fd=zip.reader.fd;requireValue(Number.isInteger(fd)&&fd>=0,'archive handle unavailable');
 requireValue(sameFile(before,await fdStat(fd)),'archive changed before handle verification');
 if(expected){
  requireValue(before.size===BigInt(expected.size),'archive integrity size mismatch');
  const sha256=crypto.createHash('sha256'),sha512=crypto.createHash('sha512');let size=0;
  // Read the descriptor owned by yauzl, so replacing the pathname cannot attach
  // an unauthenticated inventory to independently verified ZIP bytes.
  const stream=fs.createReadStream(null,{fd,autoClose:false,start:0,highWaterMark:1024*1024});
  for await(const chunk of stream){size+=chunk.length;requireValue(size<=expected.size,'archive integrity size mismatch');sha256.update(chunk);sha512.update(chunk);}
  requireValue(size===expected.size&&sha256.digest('hex')===expected.sha256&&sha512.digest('base64')===expected.sha512,'archive hash integrity mismatch');
  requireValue(sameFile(before,await fdStat(fd)),'archive changed during handle verification');
 }
}
function nextEntry(zip){return new Promise((resolve,reject)=>{
 const clean=()=>{zip.removeListener('entry',entry);zip.removeListener('end',end);zip.removeListener('error',error);};
 const entry=value=>{clean();resolve(value);},end=()=>{clean();resolve(null);},error=value=>{clean();reject(value);};
 zip.once('entry',entry);zip.once('end',end);zip.once('error',error);zip.readEntry();
});}
function readStream(zip,entry){return new Promise((resolve,reject)=>zip.openReadStream(entry,(error,stream)=>error?reject(error):resolve(stream)));}
function validateEntry(entry,limits){
 safePath(entry.fileName,limits);
 requireValue(!(entry.generalPurposeBitFlag&1)&&[0,8].includes(entry.compressionMethod),'encrypted or unsupported ZIP member');
 const mode=(entry.externalFileAttributes>>>16)&0xf000;
 requireValue(!(entry.externalFileAttributes&0x10)&&(!mode||mode===0x8000),'ZIP member is a directory, link or special file');
 requireValue(Number.isSafeInteger(entry.uncompressedSize)&&entry.uncompressedSize>=0&&entry.uncompressedSize<=limits.maxFileBytes&&Number.isSafeInteger(entry.compressedSize)&&entry.compressedSize>=0,'invalid ZIP member size');
 requireValue(entry.uncompressedSize<=Math.max(1024*1024,entry.compressedSize*limits.maxRatio),'ZIP member expansion ratio is too large');
}
async function bufferEntry(zip,entry,maxBytes){
 requireValue(entry.uncompressedSize<=maxBytes,'inventory is too large');
 const stream=await readStream(zip,entry),chunks=[];let size=0;
 for await(const chunk of stream){size+=chunk.length;if(size>maxBytes){stream.destroy();throw fail('inventory is too large');}chunks.push(chunk);}
 requireValue(size===entry.uncompressedSize,'inventory size mismatch');return Buffer.concat(chunks);
}
async function readIndex(zip,options,limits){
 requireValue(zip.entryCount>1&&zip.entryCount<=limits.maxFiles+1,'invalid ZIP file count');
 const first=await nextEntry(zip);requireValue(first&&first.fileName===INVENTORY,'inventory must be the first ZIP member');validateEntry(first,limits);
 const bytes=await bufferEntry(zip,first,limits.maxInventoryBytes);let inventory;
 try{inventory=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));}catch{throw fail('invalid inventory JSON');}
 const index=validateInventory(inventory,options,limits),entries=[];const seen=new Set([caseKey(INVENTORY)]);
 for(;;){const entry=await nextEntry(zip);if(!entry)break;validateEntry(entry,limits);const key=caseKey(entry.fileName),expected=index.files.get(key);
  requireValue(!seen.has(key)&&expected&&entry.fileName===expected.path&&entry.uncompressedSize===expected.size,'ZIP contents do not match inventory');seen.add(key);entries.push(entry);
 }
 requireValue(entries.length===index.files.size,'ZIP is missing inventory files');return {...index,bytes,entries};
}
async function withZip(file,options,callback){
 const limits=limitsFor(options);identity(options);const expected=archiveIdentity(options,limits),absolute=path.resolve(file);await ancestors(path.dirname(absolute));
 const before=await regularFile(absolute);requireValue(before.size<=BigInt(limits.maxArchiveBytes),'archive is too large');
 const zip=await openZip(absolute);let zipError;const retainError=error=>{zipError=error;};zip.on('error',retainError);
 try{await verifyHeldArchive(zip,expected,before);const index=await readIndex(zip,options,limits);if(zipError)throw zipError;const result=await callback(zip,index,limits);if(zipError)throw zipError;
  await verifyHeldArchive(zip,expected,before);
  requireValue(sameFile(before,await regularFile(absolute)),'archive changed during inspection');return result;
 }finally{zip.close();}
}
async function inspect(file,options){return withZip(file,options,async(_zip,index)=>structuredClone(index.inventory));}
async function captureStagingOwnership(root){await ancestors(path.dirname(root));return physicalDirectory(root);}
async function assertStagingOwnership(root,initial){
 const current=await captureStagingOwnership(root);requireValue(current.dev===initial.dev&&current.ino===initial.ino,'staging ownership changed; operation refused');
}
async function cleanupStaging(root,initial){
 const owned=()=>assertStagingOwnership(root,initial);
 async function remove(directory){
  await owned();await physicalDirectory(directory);
  for(const entry of await fsp.readdir(directory,{withFileTypes:true})){
   await owned();await physicalDirectory(directory);const target=path.join(directory,entry.name),info=await fsp.lstat(target);
   if(info.isDirectory()&&!info.isSymbolicLink())await remove(target);else await fsp.unlink(target);
  }
  await owned();await physicalDirectory(directory);await fsp.rmdir(directory);
 }
 await remove(root);
}
async function extract(file,destination,options){
 let owned;
 try{return await withZip(file,options,async(zip,index,limits)=>{
  const root=path.resolve(destination);await ancestors(path.dirname(root));await fsp.mkdir(root,{mode:0o700});const initial=await physicalDirectory(root);
  owned={root,initial};const directories=stagingDirectories(root,initial);
  // No existing directory is merged or overwritten. Failed partial staging is
  // removed only while this process still owns the physical directory identity.
  await boundedJobs(index.entries,async entry=>{
   const expected=index.files.get(caseKey(entry.fileName)),target=await directories.parent(expected.path,true),hash=crypto.createHash('sha256');let count=0;
   const handle=await fsp.open(target,fs.constants.O_WRONLY|fs.constants.O_CREAT|fs.constants.O_EXCL|(fs.constants.O_NOFOLLOW||0),0o600);
   try{
    const before=await handle.stat({bigint:true});requireValue(before.isFile()&&before.nlink===1n&&sameFile(before,await regularFile(target)),'extracted file replaced before writing');
    const input=await readStream(zip,entry),output=fs.createWriteStream(target,{fd:handle.fd,autoClose:false});
    const check=new Transform({transform(chunk,_encoding,done){count+=chunk.length;if(count>expected.size)return done(fail('expanded member exceeds declared size'));hash.update(chunk);done(null,chunk);}});
    await pipeline(input,check,output);
    requireValue(count===expected.size&&hash.digest('hex')===expected.sha256,'extracted file hash mismatch');
    const after=await handle.stat({bigint:true});requireValue(sameDirectory(before,after)&&after.nlink===1n&&after.size===BigInt(expected.size)&&sameFile(after,await regularFile(target)),'extracted file changed during writing');
    await directories.parent(expected.path);
   }finally{await handle.close();}
  });
  await directories.checkRoot();
  await fsp.writeFile(path.join(root,INVENTORY),index.bytes,{flag:'wx',mode:0o600});
  await verifyDirectory(root,{...options,inventory:index.inventory,limits});return structuredClone(index.inventory);
 });}catch(error){
  if(owned)try{await cleanupStaging(owned.root,owned.initial);}catch(cleanupError){error.cleanupError=cleanupError.message;}
  throw error;
 }
}
async function verifyDirectory(directory,options){
 const limits=limitsFor(options),index=validateInventory(options?.inventory,options,limits),root=path.resolve(directory);
 await ancestors(root);const initial=await physicalDirectory(root),directories=new Map(),jobs=[];
 async function enumerate(collect){
  const seen=new Set(),seenDirectories=new Set();let count=0;
  async function walk(current,prefix=''){
   const directoryIdentity=await physicalDirectory(current);
   if(collect)directories.set(current,directoryIdentity);else requireValue(directories.has(current)&&sameDirectory(directories.get(current),directoryIdentity),'directory identity changed');
   for(const entry of await fsp.readdir(current,{withFileTypes:true})){
    const relative=prefix?prefix+'/'+entry.name:entry.name;safePath(relative,limits);const key=caseKey(relative),target=path.join(current,entry.name);
    requireValue(!entry.isSymbolicLink(),'installed tree contains a link');
    if(entry.isDirectory()){requireValue(index.directories.get(key)===relative&&!seenDirectories.has(key),'unexpected installed directory');seenDirectories.add(key);await walk(target,relative);continue;}
    requireValue(entry.isFile()&&!seen.has(key),'unexpected installed file type or alias');seen.add(key);count++;requireValue(count<=limits.maxFiles+1,'installed tree has too many files');
    const expected=index.files.get(key);requireValue(relative===INVENTORY||(expected&&expected.path===relative),'unexpected installed file');
    if(collect)jobs.push({relative,target,current,directoryIdentity,expected});
   }
   await assertDirectory(current,directoryIdentity);
  }
  await walk(root);requireValue(seen.size===index.files.size+1&&seen.has(caseKey(INVENTORY))&&seenDirectories.size===index.directories.size,'installed package is incomplete');
 }
 await enumerate(true);
 await boundedJobs(jobs,async({relative,target,current,directoryIdentity,expected})=>{
  const before=await regularFile(target);requireValue(relative===INVENTORY?before.size<=BigInt(limits.maxInventoryBytes):before.size===BigInt(expected.size),relative===INVENTORY?'installed inventory too large':'installed file size mismatch');
  const handle=await fsp.open(target,fs.constants.O_RDONLY|(fs.constants.O_NOFOLLOW||0));
  try{
   requireValue(sameFile(before,await handle.stat({bigint:true})),'installed file replaced before verification');
   if(relative===INVENTORY){
    let value;try{value=JSON.parse(await handle.readFile('utf8'));}catch{throw fail('invalid installed inventory');}
    // Only the authenticated caller inventory authorizes installed bytes.
    requireValue(JSON.stringify(value)===JSON.stringify(index.inventory),'installed inventory changed');
   }else{
    const hash=crypto.createHash('sha256');let size=0;
    for await(const chunk of handle.createReadStream({autoClose:false})){size+=chunk.length;requireValue(size<=expected.size,'installed file grew during verification');hash.update(chunk);}
    requireValue(size===expected.size&&hash.digest('hex')===expected.sha256,'installed file hash mismatch');
   }
   requireValue(sameFile(before,await handle.stat({bigint:true}))&&sameFile(before,await regularFile(target)),'installed file changed during verification');
  }finally{await handle.close();}
  await assertDirectory(current,directoryIdentity);
 });
 // Recheck exact names/types after all readers drain, so files added during
 // parallel hashing cannot escape the final completeness check.
 await enumerate(false);
 const after=await physicalDirectory(root);requireValue(initial.dev===after.dev&&initial.ino===after.ino,'installed root changed');return structuredClone(index.inventory);
}
module.exports={inspect,extract,verifyDirectory,captureStagingOwnership,assertStagingOwnership,cleanupStaging,INVENTORY,DEFAULT_LIMITS,safePath};
