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
async function parents(root,relative,create=false){
 await physicalDirectory(root);let current=root;
 for(const component of relative.split('/').slice(0,-1)){
  current=path.join(current,component);
  if(create)try{await fsp.mkdir(current,{mode:0o700});}catch(error){if(error.code!=='EEXIST')throw error;}
  await physicalDirectory(current);
 }
 return path.join(root,...relative.split('/'));
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
  owned={root,initial};
  // No existing directory is merged or overwritten. Failed partial staging is
  // removed only while this process still owns the physical directory identity.
  for(const entry of index.entries){
   const expected=index.files.get(caseKey(entry.fileName)),target=await parents(root,expected.path,true),hash=crypto.createHash('sha256');let count=0;
   const input=await readStream(zip,entry),output=fs.createWriteStream(target,{flags:'wx',mode:0o600});
   const check=new Transform({transform(chunk,_encoding,done){count+=chunk.length;if(count>expected.size)return done(fail('expanded member exceeds declared size'));hash.update(chunk);done(null,chunk);}});
   await pipeline(input,check,output);
   requireValue(count===expected.size&&hash.digest('hex')===expected.sha256,'extracted file hash mismatch');
   await parents(root,expected.path);await regularFile(target);
  }
  requireValue((await physicalDirectory(root)).ino===initial.ino,'staging directory changed');
  await fsp.writeFile(path.join(root,INVENTORY),index.bytes,{flag:'wx',mode:0o600});
  await verifyDirectory(root,{...options,inventory:index.inventory,limits});return structuredClone(index.inventory);
 });}catch(error){
  if(owned)try{await cleanupStaging(owned.root,owned.initial);}catch(cleanupError){error.cleanupError=cleanupError.message;}
  throw error;
 }
}
async function verifyDirectory(directory,options){
 const limits=limitsFor(options),index=validateInventory(options?.inventory,options,limits),root=path.resolve(directory);
 await ancestors(root);const initial=await physicalDirectory(root),seen=new Set(),seenDirectories=new Set();let count=0;
 async function walk(current,prefix=''){
  await physicalDirectory(current);
  for(const entry of await fsp.readdir(current,{withFileTypes:true})){
   const relative=prefix?prefix+'/'+entry.name:entry.name;safePath(relative,limits);const key=caseKey(relative),target=path.join(current,entry.name);
   requireValue(!entry.isSymbolicLink(),'installed tree contains a link');
   if(entry.isDirectory()){requireValue(index.directories.get(key)===relative&&!seenDirectories.has(key),'unexpected installed directory');seenDirectories.add(key);await walk(target,relative);continue;}
   requireValue(entry.isFile()&&!seen.has(key),'unexpected installed file type or alias');seen.add(key);count++;requireValue(count<=limits.maxFiles+1,'installed tree has too many files');
   if(relative===INVENTORY){const info=await regularFile(target);requireValue(info.size<=BigInt(limits.maxInventoryBytes),'installed inventory too large');
    let value;try{value=JSON.parse(await fsp.readFile(target,'utf8'));}catch{throw fail('invalid installed inventory');}
    // Comparison uses the caller's authenticated inventory, never local authority.
    requireValue(JSON.stringify(value)===JSON.stringify(index.inventory),'installed inventory changed');continue;}
   const expected=index.files.get(key);requireValue(expected&&expected.path===relative,'unexpected installed file');
   const before=await regularFile(target);requireValue(before.size===BigInt(expected.size),'installed file size mismatch');
   const handle=await fsp.open(target,fs.constants.O_RDONLY|(fs.constants.O_NOFOLLOW||0));
   try{requireValue(sameFile(before,await handle.stat({bigint:true})),'installed file replaced before verification');const hash=crypto.createHash('sha256');let size=0;
    for await(const chunk of handle.createReadStream({autoClose:false})){size+=chunk.length;requireValue(size<=expected.size,'installed file grew during verification');hash.update(chunk);}
    requireValue(size===expected.size&&hash.digest('hex')===expected.sha256,'installed file hash mismatch');
    requireValue(sameFile(before,await handle.stat({bigint:true}))&&sameFile(before,await regularFile(target)),'installed file changed during verification');
   }finally{await handle.close();}
   await parents(root,relative);
  }
 }
 await walk(root);requireValue(seen.size===index.files.size+1&&seen.has(caseKey(INVENTORY))&&seenDirectories.size===index.directories.size,'installed package is incomplete');
 const after=await physicalDirectory(root);requireValue(initial.dev===after.dev&&initial.ino===after.ino,'installed root changed');return structuredClone(index.inventory);
}
module.exports={inspect,extract,verifyDirectory,captureStagingOwnership,assertStagingOwnership,cleanupStaging,INVENTORY,DEFAULT_LIMITS,safePath};
