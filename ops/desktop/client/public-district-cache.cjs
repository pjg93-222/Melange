'use strict';
// Retire only downloaded public files described by verified catalogues. Local
// accounts, saved views, snapshot history and rollback journals live elsewhere.
const nativeFs=require('node:fs'),fs=nativeFs.promises,path=require('node:path'),crypto=require('node:crypto');
const IDS=['co-05','or-05','ct-01'],SHA=/^[a-f0-9]{64}$/;
const within=(root,target)=>{const relative=path.relative(root,target);return relative!==''&&relative!=='..'&&!relative.startsWith('..'+path.sep)&&!path.isAbsolute(relative);};
const stamp=stat=>[stat.dev,stat.ino,stat.size,stat.mtimeNs,stat.ctimeNs].map(String).join('|');
function requireValue(value){if(!value)throw new Error('Public district cache retirement refused an unsafe path or changed file.');}
async function signedFile(file,expected,stat){
 requireValue(SHA.test(expected.sha256));const hash=crypto.createHash('sha256');let bytes=0;
 for await(const chunk of nativeFs.createReadStream(file,{highWaterMark:4*1024*1024})){bytes+=chunk.length;requireValue(bytes<=expected.bytes);hash.update(chunk);}
 requireValue(bytes===expected.bytes&&hash.digest('hex')===expected.sha256&&stamp(await fs.lstat(file,{bigint:true}))===stamp(stat));
}
async function existing(filename){try{return await fs.lstat(filename,{bigint:true});}catch(error){if(error.code==='ENOENT')return null;throw error;}}
async function directory(root,target){
 requireValue(target===root||within(root,target));
 for(const current of [root,...path.relative(root,target).split(path.sep).filter(Boolean).map((_,index,parts)=>path.join(root,...parts.slice(0,index+1)))]){
  const stat=await existing(current);if(!stat)return false;
  requireValue(stat.isDirectory()&&!stat.isSymbolicLink()&&path.resolve(await fs.realpath(current))===current);
 }
 return true;
}
function rolePath(role){
 requireValue(typeof role==='string'&&!role.includes('\\')&&!role.includes(':')&&role.split('/').every(part=>part&&part!=='.'&&part!=='..'));
 return role.split('/').join(path.sep);
}
async function inventory(root,target,files){
 const expected=new Map(files.map(row=>[rolePath(row.role),row])),allowedDirectories=new Set(['']);
 for(const name of expected.keys()){let parent=path.dirname(name);while(parent!=='.'){allowedDirectories.add(parent);parent=path.dirname(parent);}}
 const rows=[],directories=[];let visited=0;
 async function visit(current){
  requireValue(++visited<=10000&&within(root,current));
  const relative=path.relative(target,current),stat=await existing(current);requireValue(stat&&!stat.isSymbolicLink());
  if(stat.isDirectory()){
   requireValue(allowedDirectories.has(relative)&&await directory(root,current));
   for(const name of await fs.readdir(current))await visit(path.join(current,name));
   directories.push(current);
  }else{
   requireValue(stat.isFile()&&expected.has(relative)&&BigInt(expected.get(relative).bytes)===stat.size);
   await signedFile(current,expected.get(relative),stat);
   rows.push({file:current,stamp:stamp(stat)});
  }
 }
 await visit(target);return {rows,directories};
}
async function retirePublicDistrictCaches({root,configuration,manifests}){
 const descriptor=configuration?.standaloneGitHubData;
 requireValue(descriptor&&[1,2].includes(descriptor.schemaVersion)&&IDS.includes(configuration.district)&&descriptor.district===configuration.district&&SHA.test(descriptor.catalogueSha256));
 requireValue(typeof root==='string'&&path.isAbsolute(root)&&path.resolve(descriptor.cacheRoot)===path.resolve(root)&&Array.isArray(manifests)&&manifests.length<=16);
 root=path.resolve(root);const base=path.join(root,'github-districts');
 const active=path.join(base,descriptor.schemaVersion===2?'datasets-v2':'datasets',descriptor.catalogueSha256,configuration.district);
 requireValue(await directory(root,active));
 const activeManifest=manifests.find(item=>item.sha256===descriptor.catalogueSha256);requireValue(activeManifest);
 const activeArchive=activeManifest.assets.get(configuration.district)?.sha256;requireValue(SHA.test(activeArchive));
 const result={retired:[],skipped:[]},seen=new Set();
 for(const manifest of manifests){
  requireValue(SHA.test(manifest.sha256)&&manifest.assets instanceof Map);
  for(const namespace of ['datasets','datasets-v2'])for(const district of IDS){
   const target=path.join(base,namespace,manifest.sha256,district);if(target===active||seen.has(target))continue;seen.add(target);
   try{
    if(!await directory(root,target))continue;
    const plan=await inventory(root,target,manifest.dataFiles[district]);
    for(const row of plan.rows){requireValue(await directory(root,path.dirname(row.file)));const current=await existing(row.file);requireValue(current?.isFile()&&!current.isSymbolicLink()&&stamp(current)===row.stamp);await fs.unlink(row.file);}
    for(const folder of plan.directories){requireValue(await directory(root,folder));await fs.rmdir(folder);}
    result.retired.push(target);
   }catch{result.skipped.push(target);}
  }
  for(const asset of manifest.assets.values()){
   requireValue(SHA.test(asset.sha256));if(asset.sha256===activeArchive)continue;
   const target=path.join(base,'downloads',asset.sha256+'.zip');if(seen.has(target))continue;seen.add(target);
   try{
    if(!await directory(root,path.dirname(target)))continue;
    const stat=await existing(target);if(!stat)continue;
    requireValue(stat.isFile()&&!stat.isSymbolicLink()&&stat.size===BigInt(asset.bytes));
    await signedFile(target,asset,stat);
    requireValue(await directory(root,path.dirname(target))&&stamp(await fs.lstat(target,{bigint:true}))===stamp(stat));await fs.unlink(target);result.retired.push(target);
   }catch{result.skipped.push(target);}
  }
 }
 return result;
}
module.exports={retirePublicDistrictCaches};
