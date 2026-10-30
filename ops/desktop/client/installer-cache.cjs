'use strict';
const fs=require('node:fs');
const path=require('node:path');
const semver=require('semver');

// These roots contain downloaded installers, never installed applications or data.
// Delete individual regular files only: an unexpected file or nested folder survives.
function realDirectory(directory){
  if(!path.isAbsolute(directory))return false;
  for(let current=directory;;current=path.dirname(current)){
    const info=fs.lstatSync(current);
    if(!info.isDirectory()||info.isSymbolicLink())return false;
    if(current===path.dirname(current))return true;
  }
}
function pruneInstallerCache({appId,currentVersion,currentSequence,updatesRoots=[],baselineRoot,nativeCacheDirectory,keepSequences=[],keepVersions=[]}){
  const removed=[];
  if(!['melange','mentat','terrier'].includes(appId)||!semver.valid(currentVersion)||!Number.isSafeInteger(currentSequence)||currentSequence<1)return removed;
  const sequences=new Set([String(currentSequence),...keepSequences.map(String)]),versions=new Set([currentVersion,...keepVersions]);
  const removeFiles=(directory,installerName)=>{
    if(!realDirectory(directory))return;
    for(const filename of fs.readdirSync(directory)){
      if(!installerName(filename))continue;
      const target=path.join(directory,filename);
      try{
        const info=fs.lstatSync(target);
        if(!info.isFile()||info.isSymbolicLink()||info.nlink!==1||!realDirectory(directory))continue;
        fs.unlinkSync(target);removed.push(target);
      }catch{} // A locked installer is retried after the next successful launch.
    }
  };
  const sweep=(root,eligible,installerName)=>{
    if(!root)return;
    try{
      const resolved=path.resolve(root);
      if(!path.isAbsolute(root)||!realDirectory(resolved))return;
      for(const name of fs.readdirSync(resolved)){
        if(!eligible(name))continue;
        const directory=path.join(resolved,name);
        try{
          if(path.dirname(directory)!==resolved||!realDirectory(directory))continue;
          removeFiles(directory,installerName);
          try{fs.rmdirSync(directory);}catch{} // Only empty directories; never recursive.
        }catch{}
      }
    }catch{}
  };
  const packageName=new RegExp('^'+appId+'(?:-\\d+\\.\\d+\\.\\d+-win(?:32)?-x64)?\\.exe$','i');
  for(const root of new Set(updatesRoots))sweep(root,name=>/^[1-9]\d*$/.test(name)&&Number.isSafeInteger(Number(name))&&Number(name)<currentSequence&&!sequences.has(name),name=>packageName.test(name));
  // NSIS preserves the browser's original filename in this app's private baseline folder.
  sweep(baselineRoot,name=>semver.valid(name)===name&&semver.lt(name,currentVersion)&&!versions.has(name),name=>/\.exe$/i.test(name));
  // The native updater uses a flat pending cache. A manual upgrade can leave its
  // old installer here; filenames without an exact app/version binding are kept.
  if(nativeCacheDirectory&&path.isAbsolute(nativeCacheDirectory))try{
    const versioned=new RegExp('^'+appId+'-(\\d+\\.\\d+\\.\\d+)-win(?:32)?-x64\\.exe$','i');
    removeFiles(path.join(nativeCacheDirectory,'pending'),name=>{const match=versioned.exec(name);return Boolean(match&&semver.valid(match[1])&&semver.lt(match[1],currentVersion)&&!versions.has(match[1]));});
  }catch{}
  return removed;
}
module.exports={pruneInstallerCache};
