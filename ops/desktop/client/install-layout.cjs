'use strict';
// ONE config point for the Downloads layout (D-300/D-303). Change names here only; NSIS reads a generated include.
const path=require('node:path');
const semver=require('semver');
const win=path.win32;
const LAYOUT=Object.freeze({
  rootName:'MelangeApplications',            // <Downloads>\MelangeApplications
  appFolder:'{product}-{version}',           // <root>\Melange-1.0.19 (folder name carries 1.x)
  updatesName:'updates',                      // <root>\updates
  updaterCacheFolder:'{app}',                // <root>\updates\melange\pending\melange-1.0.20-win32-x64.exe
  setupFolder:'{app}-setup',                 // <root>\updates\melange-setup\nsXXXX.tmp (NSIS $TEMP). No version: 7 more characters of
                                              // user name fit under DL_MAX_SETUP (LAUNCH F2); only one setup folder is ever live
  legacySetupFolder:'{app}-{version}-setup', // the 1.0.19 name; the sweep removes these leftovers
  keepVersions:2,                             // D-7: current + one previous
  rollbackFloor:'1.0.19',                     // D-5: first Downloads release
  downloadsKnownFolder:'{374DE290-123F-4565-9164-39C4925E467B}',
  maxPath:259,                                // MAX_PATH 260 minus NUL
  deepestRelativeBudget:150,                  // after-pack fails the build above this (measured 145/135/131)
  pluginsDirOverhead:20,                      // '\nsXXXX.tmp' + '\7z-out\'
  legacyProgramFolders:['documents','programs'] // D-4 cleanup targets (exact paths, see legacyCandidates)
});
const VERSION='\\d+\\.\\d+\\.\\d+';
const escape=text=>String(text).replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
const fill=(template,values)=>template.replace(/\{(product|app|version)\}/g,(match,key)=>{if(values[key]===undefined)throw new Error('Layout value missing: '+key);return values[key];});
const root=downloads=>win.join(downloads,LAYOUT.rootName);
const updatesDirectory=downloads=>win.join(root(downloads),LAYOUT.updatesName);
const appDirectory=(downloads,product,version)=>win.join(root(downloads),fill(LAYOUT.appFolder,{product,version}));
const updaterCacheDirectory=(downloads,app)=>win.join(updatesDirectory(downloads),fill(LAYOUT.updaterCacheFolder,{app}));
const setupTempDirectory=(downloads,app,version)=>win.join(updatesDirectory(downloads),fill(LAYOUT.setupFolder,{app,version}));
// Relative-based and case-insensitive (path.win32). Never a string-prefix test: MelangeApplications2 is not under MelangeApplications.
function isUnder(child,parent){
  if(typeof child!=='string'||typeof parent!=='string'||!child||!parent)return false;
  const relative=win.relative(parent,child);
  return relative!==''&&relative!=='..'&&!relative.startsWith('..\\')&&!win.isAbsolute(relative);
}
const overlaps=(a,b)=>win.relative(a,b)===''||isUnder(a,b)||isUnder(b,a);
// The single switch: false means legacy behaviour everywhere (an app that runs from Documents or Programs).
const downloadsMode=({execPath,downloads})=>Boolean(downloads&&execPath&&isUnder(execPath,root(downloads)));
const maxDirectory=()=>LAYOUT.maxPath-LAYOUT.deepestRelativeBudget-1;
const maxSetup=()=>LAYOUT.maxPath-LAYOUT.deepestRelativeBudget-LAYOUT.pluginsDirOverhead-1;
const fitsPath=directory=>String(directory).length+LAYOUT.deepestRelativeBudget+1<=LAYOUT.maxPath;
// Longest relative path (characters) of any file under dir. Links are not followed.
function deepestRelative(directory,fs=require('node:fs')){
  let deepest=0;
  const walk=(current,prefix)=>{
    let entries;try{entries=fs.readdirSync(current,{withFileTypes:true});}catch{return;}
    for(const entry of entries){
      const relative=prefix?prefix+'\\'+entry.name:entry.name;
      if(relative.length>deepest)deepest=relative.length;
      if(entry.isDirectory()&&!entry.isSymbolicLink())walk(win.join(current,entry.name),relative);
    }
  };
  walk(directory,'');return deepest;
}
// Version folders to delete. entries: names (or Dirents) from readdir(root). Keeps the current version, every protected version,
// then fills up to `keep` with the newest remaining. With a root (and fs), links and junctions are never listed.
function pruneTargets({entries,product,current,protect=[],keep=LAYOUT.keepVersions,root:directory,fs}){
  const pattern=new RegExp('^'+escape(product)+'-('+VERSION+')$');
  const versions=[];
  for(const entry of entries){
    const name=typeof entry==='string'?entry:entry.name,match=pattern.exec(name);
    if(!match)continue;
    if(typeof entry!=='string'&&(entry.isDirectory?.()===false||entry.isSymbolicLink?.()))continue;
    if(directory&&fs){try{const info=fs.lstatSync(win.join(directory,name));if(info.isSymbolicLink()||!info.isDirectory())continue;}catch{continue;}}
    versions.push({name,version:match[1]});
  }
  const kept=new Set([current,...protect.filter(Boolean)]);
  const rest=versions.filter(item=>!kept.has(item.version)).sort((a,b)=>semver.rcompare(a.version,b.version));
  const slots=Math.max(0,keep-new Set([...kept].filter(version=>versions.some(item=>item.version===version))).size);
  for(const item of rest.slice(0,slots))kept.add(item.version);
  return versions.filter(item=>!kept.has(item.version)).map(item=>item.name);
}
// Exactly these program folders (D-4); nothing else is ever enumerated, so Melange.bak-* siblings are unreachable.
function legacyCandidates({product,home,documents,localAppData}){
  const list=[];
  if(documents)list.push(win.join(documents,LAYOUT.rootName,product));
  if(home)list.push(win.join(home,'Documents',LAYOUT.rootName,product));
  if(localAppData)list.push(win.join(localAppData,'Programs',product));
  const seen=new Set();return list.filter(item=>{const key=item.toLowerCase();if(seen.has(key))return false;seen.add(key);return true;});
}
const number=value=>{const n=typeof value==='string'?Number(value.trim()):value;return Number.isFinite(n)?n:NaN;};
function downloadsWarnings({downloads,home,env={},storagePolicy={},storagePolicyGpo={}}){
  const warnings=[],base=root(downloads);
  if(home&&downloads.toLowerCase()!==win.join(home,'Downloads').toLowerCase())warnings.push('Downloads is redirected to '+downloads+'. Tell IT this path if the app is blocked.');
  const cloud=['OneDrive','OneDriveCommercial','OneDriveConsumer'].map(name=>env[name]).filter(Boolean);
  if(cloud.some(folder=>downloads.toLowerCase()===folder.toLowerCase()||isUnder(downloads,folder)))warnings.push('Downloads is inside OneDrive ('+downloads+'); files may be moved to the cloud or locked while syncing.');
  const days=number(storagePolicy['512']);
  if(number(storagePolicy['01'])===1&&number(storagePolicy['32'])===1&&days>0)warnings.push('Storage Sense deletes Downloads files not opened for '+days+' days; this app lives in '+base+'.');
  const threshold=number(storagePolicyGpo.ConfigStorageSenseDownloadsCleanupThreshold);
  if(threshold>0&&number(storagePolicyGpo.AllowStorageSenseGlobal)!==0)warnings.push('Storage Sense deletes Downloads files not opened for '+threshold+' days (set by policy); this app lives in '+base+'.');
  return warnings;
}
// reg.exe query output -> {name:value}
function parseRegQuery(text){
  const values={};
  for(const line of String(text||'').split(/\r?\n/)){const match=/^\s+(\S+)\s+REG_\w+\s+(.*?)\s*$/.exec(line);if(match)values[match[1]]=match[2];}
  return values;
}
async function registryValues(execFile,key,env=process.env){
  try{const {stdout}=await execFile(win.join(env.SystemRoot||'C:\\Windows','System32','reg.exe'),['query',key]);return parseRegQuery(stdout);}catch{return {};}
}
async function layoutWarnings({downloads,home,env=process.env,execFile}){
  const [storagePolicy,storagePolicyGpo]=await Promise.all([
    registryValues(execFile,'HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\StorageSense\\Parameters\\StoragePolicy',env),
    registryValues(execFile,'HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\StorageSense',env)]);
  return downloadsWarnings({downloads,home,env,storagePolicy,storagePolicyGpo});
}
function nsisInclude({product,app,version,installerNsh}){
  const values={product,app,version};
  return [
    '!define DL_VERSION "'+version+'"','!define DL_ROOT_NAME "'+LAYOUT.rootName+'"','!define DL_UPDATES_NAME "'+LAYOUT.updatesName+'"',
    '!define DL_APP_FOLDER "'+fill(LAYOUT.appFolder,values)+'"','!define DL_SETUP_FOLDER "'+fill(LAYOUT.setupFolder,values)+'"',
    '!define DL_CACHE_FOLDER "'+fill(LAYOUT.updaterCacheFolder,values)+'"','!define DL_KNOWN_FOLDER "'+LAYOUT.downloadsKnownFolder+'"',
    '!define DL_MAX_DIR '+maxDirectory(),'!define DL_MAX_SETUP '+maxSetup(),
    '!include "'+installerNsh+'"',''].join('\n');
}
// ---- sweep: keep-2 pruning (2.5) and legacy program-folder cleanup (2.6), run once after a successful launch ----
async function realDirectory(fs,target){
  try{const info=await fs.promises.lstat(target);return info.isDirectory()&&!info.isSymbolicLink();}catch{return false;}
}
async function sweepLayout({fs=require('node:fs'),downloads,documents,home,localAppData,product,app,applicationId,current,execPath,userData,state={},log=()=>{}}){
  const result={pruned:[],setupRemoved:[],legacyRemoved:[],installersRemoved:[]};
  if(!downloadsMode({execPath,downloads}))return result;
  const base=root(downloads),executable=win.dirname(execPath);
  if(!await realDirectory(fs,base))return result; // a junctioned root (or none) is never swept
  const remove=async(target,options)=>{try{await fs.promises.rm(target,options);log('[layout] removed '+target);return true;}catch(error){log('[layout] could not remove '+target+': '+(error.code||error.message));return false;}};
  // 2.5 version folders
  try{
    const live=state.recovery&&!['completed','failed'].includes(state.recovery.phase)?state.recovery.target?.version:null;
    // installed too: this sweep runs at readiness, before recover() promotes installed to previous, so installed is still the version updated from.
    const protect=[state.installed?.version,state.pending?.version,live,state.previous?.version].filter(Boolean);
    const names=await fs.promises.readdir(base);
    for(const name of pruneTargets({entries:names,product,current,protect,keep:LAYOUT.keepVersions})){
      const target=win.join(base,name);
      if(!await realDirectory(fs,target)||overlaps(target,executable))continue;
      if(await remove(target,{recursive:true,force:false}))result.pruned.push(target);
    }
  }catch(error){if(error.code!=='ENOENT')log('[layout] version sweep skipped: '+error.message);}
  // stale setup folders: the NSIS run is over and they are empty
  try{
    const updates=updatesDirectory(downloads),keepSetup=new Set([current,state.pending?.version].filter(Boolean).map(version=>fill(LAYOUT.setupFolder,{app,version})));
    const pattern=new RegExp('^(?:'+[LAYOUT.setupFolder,LAYOUT.legacySetupFolder].map(template=>escape(fill(template,{app,version:'@@'})).replace('@@',VERSION)).join('|')+')$');
    for(const name of await fs.promises.readdir(updates)){
      if(!pattern.test(name)||keepSetup.has(name))continue;
      const target=win.join(updates,name);
      if(!await realDirectory(fs,target)||overlaps(target,executable))continue;
      if(await remove(target,{recursive:true,force:false}))result.setupRemoved.push(target);
    }
  }catch(error){if(error.code!=='ENOENT')log('[layout] setup sweep skipped: '+error.message);}
  // downloaded installers: keep only this version's exact file; older versions and (1)-style duplicates go
  try{
    const installer=new RegExp('^'+escape(app)+'-('+VERSION+')-win32-x64(?: \\(\\d+\\))?\\.exe$','i'),keep=(app+'-'+current+'-win32-x64.exe').toLowerCase();
    for(const name of await fs.promises.readdir(downloads)){
      if(!installer.test(name)||name.toLowerCase()===keep)continue;
      const target=win.join(downloads,name);
      try{if(!(await fs.promises.lstat(target)).isFile())continue;}catch{continue;}
      if(await remove(target,{force:false}))result.installersRemoved.push(target);
    }
  }catch(error){if(error.code!=='ENOENT')log('[layout] installer sweep skipped: '+error.message);}
  // 2.6 legacy program folders
  const guarded=[executable,userData,documents&&win.join(documents,'MelangeApplicationState'),home&&win.join(home,'Documents','MelangeApplicationState'),
    localAppData&&win.join(localAppData,'MelangeData'),localAppData&&applicationId&&win.join(localAppData,applicationId),base].filter(Boolean);
  for(const candidate of legacyCandidates({product,home,documents,localAppData})){
    try{
      if(win.basename(candidate)!==product||candidate.toLowerCase().includes('.bak'))continue;
      if(guarded.some(item=>overlaps(candidate,item)))continue;
      if(!await realDirectory(fs,candidate)||!await realDirectory(fs,win.dirname(candidate)))continue;
      const regular=async file=>{try{return (await fs.promises.lstat(file)).isFile();}catch{return false;}};
      if(!await regular(win.join(candidate,product+'.exe'))||!await regular(win.join(candidate,'resources','app.asar')))continue;
      if(await remove(candidate,{recursive:true}))result.legacyRemoved.push(candidate);
    }catch(error){log('[layout] legacy cleanup skipped '+candidate+': '+error.message);}
  }
  return result;
}
module.exports={LAYOUT,fill,root,appDirectory,updaterCacheDirectory,setupTempDirectory,updatesDirectory,isUnder,overlaps,downloadsMode,fitsPath,pruneTargets,legacyCandidates,
  downloadsWarnings,parseRegQuery,registryValues,layoutWarnings,nsisInclude,deepestRelative,sweepLayout,maxDirectory,maxSetup};
