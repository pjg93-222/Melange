'use strict';
// electron-builder afterPack: strip Mentat user state and runtime databases out of the packed Mentat/app sources.
// Only resources/runtime/<app>/sources/** is touched; third-party files elsewhere (proj.db, R's KEYWORDS.db and
// license.db, RSQLite's datasets.sqlite, ...) are legitimate and survive. Each removal is logged; this never fails
// the build. The extraResources glob filter in builder.cjs is case-sensitive and shallow, so this is the real guard.
const fs=require('node:fs'),path=require('node:path');
const layout=require('./install-layout.cjs'),{appDefinition}=require('./apps.cjs');
const DATABASE_SUFFIXES=['.sqlite','.sqlite3','.db','-wal','-shm','-journal'];
function stripState(runtimeRoot,log=()=>{}){
  const removed=[];
  const remove=full=>{try{fs.rmSync(full,{recursive:true,force:true});removed.push(full);log('[after-pack] removed '+full);}catch(error){log('[after-pack] could not remove '+full+': '+error.message);}};
  const walk=directory=>{
    let entries;
    try{entries=fs.readdirSync(directory,{withFileTypes:true});}catch(error){log('[after-pack] could not read '+directory+': '+error.message);return;}
    for(const entry of entries){
      const lower=entry.name.toLowerCase(),full=path.join(directory,entry.name);
      if(lower==='state'||DATABASE_SUFFIXES.some(suffix=>lower.endsWith(suffix)))remove(full);
      else if(entry.isDirectory())walk(full);
    }
  };
  if(!fs.existsSync(runtimeRoot))return removed;
  for(const application of fs.readdirSync(runtimeRoot,{withFileTypes:true}))if(application.isDirectory())
    for(const child of fs.readdirSync(path.join(runtimeRoot,application.name),{withFileTypes:true}))
      if(child.isDirectory()&&child.name.toLowerCase()==='sources')walk(path.join(runtimeRoot,application.name,child.name));
  return removed;
}
// N20 (Paul: the public installer ships a no-data dashboard shell only). The shell is the first-run page that
// melange_bootstrap.py writes into the user's data folder; the real Moneyball*.html and any dataset never ship.
// Dashboards are banned anywhere in the runtime; datasets only in Melange's own sources (Terrier and Mentat name reviewed schema/geo files in the manifest).
const DASHBOARD_PATTERN=/^moneyball.*\.html$/i,DATASET_PATTERN=/\.(xlsx|xlsm|xls|csv|parquet|feather|ndjson|joblib|pkl|pickle|npz)$/i;
function findShippedData(runtimeRoot){
  // One walk over the whole runtime, so files at any depth (including directly under runtime/<app>) are checked.
  const found=[],melangeSources=path.join(runtimeRoot,'melange','sources',path.sep).toLowerCase();
  const walk=directory=>{
    // Fail closed: an unreadable directory could hide a dashboard or dataset (stripState stays best-effort).
    for(const entry of fs.readdirSync(directory,{withFileTypes:true})){
      const full=path.join(directory,entry.name);
      if(entry.isDirectory())walk(full);
      else if(DASHBOARD_PATTERN.test(entry.name)||(full.toLowerCase().startsWith(melangeSources)&&DATASET_PATTERN.test(entry.name)))found.push(full);
    }
  };
  if(fs.existsSync(runtimeRoot))walk(runtimeRoot);
  return found;
}
async function afterPack(context){
  const removed=stripState(path.join(context.appOutDir,'resources','runtime'),message=>console.log(message));
  console.log('[after-pack] runtime packing report: removed '+removed.length+' state/database path(s) under runtime/*/sources');
  const shipped=findShippedData(path.join(context.appOutDir,'resources','runtime'));
  if(shipped.length)throw new Error('A public installer ships only the no-data dashboard shell (N20), but the package holds a dashboard or dataset: '+shipped.join(', '));
  // Downloads layout (DL-spec 1.3, 2.8): the long-path gate, then the one writer of the generated NSIS include (builder.cjs nsis.include).
  const depth=layout.deepestRelative(context.appOutDir),budget=layout.LAYOUT.deepestRelativeBudget;
  console.log('[after-pack] deepest packaged path: '+depth+' characters (limit '+budget+')');
  if(depth>budget)throw new Error('The deepest packaged path is '+depth+' characters, over the limit of '+budget+'. The Downloads install path (MAX_PATH) would be exceeded; shorten the packaged paths.');
  const version=context.packager?.appInfo?.version;
  const config=context.packager?.config;
  const windows=context.electronPlatformName===undefined||context.electronPlatformName==='win32';
  const targets=[config?.win?.target??[]].flat().map(target=>typeof target==='string'?target:target.target);
  if(version&&windows&&targets.includes('dir')&&!targets.some(target=>target.startsWith('nsis'))){
    // electron-builder writes app-update.yml only for its NSIS targets. Our
    // built-in installer still requires the same publisher pin and cache name.
    const definition=appDefinition(config?.extraMetadata?.desktopAppConfig?.appId||process.env.DESKTOP_APP_ID||'melange');
    const publisher=config?.extraMetadata?.desktopAppConfig?.windowsPublisherName;
    const publish=config?.publish;
    if(publish?.provider!=='generic'||typeof publish.url!=='string')throw new Error('The native directory build requires its configured update endpoint');
    const resources=path.join(context.appOutDir,'resources');
    fs.mkdirSync(resources,{recursive:true});
    if(fs.lstatSync(resources).isSymbolicLink())throw new Error('Updater configuration requires physical packaged resources');
    const updateConfig={provider:publish.provider,url:publish.url,updaterCacheDirName:context.packager.appInfo.updaterCacheDirName||definition.id+'-desktop-updater',...(publisher?{publisherName:[publisher]}:{})};
    // JSON is valid YAML and preserves literal publisher names without a YAML
    // serialization dependency. This file is consumed by electron-updater.
    const target=path.join(resources,'app-update.yml');
    fs.writeFileSync(target,JSON.stringify(updateConfig,null,2)+'\n',{flag:'wx'});
    console.log('[after-pack] wrote '+target+' for the built-in installer');
  }else if(version&&windows){
    const definition=appDefinition(context.packager.config?.extraMetadata?.desktopAppConfig?.appId||process.env.DESKTOP_APP_ID||'melange');
    const target=path.join(path.dirname(context.appOutDir),'installer.generated.nsh');
    fs.writeFileSync(target,layout.nsisInclude({product:definition.name,app:definition.id,version,installerNsh:path.join(__dirname,'installer.nsh')}));
    console.log('[after-pack] wrote '+target);
    if(context.packager.config?.extraMetadata?.desktopAppConfig?.desktopUninstaller===false){
      const script=require('./nsis-no-uninstaller.cjs').prepare({directory:path.dirname(context.appOutDir)});
      console.log('[after-pack] wrote '+script);
    }
  }
}
module.exports=afterPack;module.exports.stripState=stripState;module.exports.findShippedData=findShippedData;
