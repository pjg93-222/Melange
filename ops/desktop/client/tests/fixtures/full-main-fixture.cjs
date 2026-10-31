'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path'),vm=require('node:vm');
const {createRequire}=require('node:module'),{EventEmitter}=require('node:events');

// Execute the complete main module and its enclosing lexical blocks. Electron
// host operations are doubles; launch/retry/factory code is never extracted.
function fullMain({client=path.resolve(__dirname,'../..'),appId='terrier',authentication='password',settings={},imports={}}={}){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'desktop-full-main-')),profile=path.join(root,'profile');fs.mkdirSync(profile);
 const cleanup=()=>{assert.equal(path.dirname(root),os.tmpdir());assert.ok(path.basename(root).startsWith('desktop-full-main-'));fs.rmSync(root,{recursive:true,force:true});};
 fs.writeFileSync(path.join(profile,'settings.json'),JSON.stringify(settings));
 const mainFile=path.join(client,'main.cjs'),nativeRequire=createRequire(mainFile),app=new EventEmitter(),paths={home:root,appData:path.join(root,'appdata'),userData:profile};
 let ready,singleInstanceRequests=0;
 Object.assign(app,{isPackaged:false,getVersion:()=> '1.0.42',getPath:name=>paths[name]||path.join(root,name),setPath:(name,value)=>{paths[name]=value;},
  setName(){},setAppUserModelId(){},requestSingleInstanceLock:()=>{singleInstanceRequests++;return true;},whenReady:()=>({then(callback){ready=callback;}}),quit(){},exit(){}});
 const electron={app,powerMonitor:new EventEmitter(),net:{request(){throw new Error('No real network in main fixture');}},dialog:{showErrorBox(){throw new Error('Unexpected native error dialog');}}};
 const context={__dirname:client,Buffer,URL,AbortController,console,setTimeout,clearTimeout,setImmediate,clearImmediate,setInterval,clearInterval,
  process:{env:{...process.env,DESKTOP_APP_ID:appId,DESKTOP_ACCESS_MODE:'standalone',DESKTOP_AUTHENTICATION:authentication,MELANGE_DESKTOP_TEST_PROFILE:profile},
   platform:process.platform,argv:['node',mainFile],pid:process.pid,execPath:process.execPath,versions:process.versions},
  require:name=>name==='electron'?electron:Object.hasOwn(imports,name)?imports[name]:nativeRequire(name)};
 const source=fs.readFileSync(mainFile,'utf8'),anchor="app.on('window-all-closed',finishClose);";
 assert.equal(source.split(anchor).length,2,'One end-of-module hook inside the original lexical scope');
 const powerStart=source.indexOf('  const suspendWindowsAccess='),powerEnd=source.indexOf("  powerMonitor.on('unlock-screen',checkUpdates);",powerStart);
 assert.ok(powerStart>0&&powerEnd>powerStart);
 const powerHandlers=source.slice(powerStart,powerEnd+"  powerMonitor.on('unlock-screen',checkUpdates);".length);
 const hook=`globalThis.fixtureMain={launch,launchAuthorized,startupRetry,createModuleDataStartup,
  registerPowerHandlers(){${powerHandlers}},
  configure(value){Object.assign(applicationConfig,value);},
  install(value){runtime=value.runtime;accessGate=value.gate;accessLifecycle=value.lifecycle;window=value.window;accessWindow=value.accessWindow;
   updater=value.updater;runtimePartition={};
   if(value.checkUpdates)checkUpdates=value.checkUpdates;moduleDataStartup=value.moduleDataStartup||null;
   if(value.showTerrierSignIn)showTerrierSignIn=value.showTerrierSignIn;
   if(value.showSetup)showSetup=value.showSetup;
   if(value.workspaceFactory)createWorkspaceDataStartup=value.workspaceFactory;}};\n`;
 try{vm.runInNewContext(source.replace(anchor,hook+anchor),context,{filename:mainFile});}
 catch(error){cleanup();throw error;}
 return {...context.fixtureMain,electron,profile,root,get singleInstanceRequests(){return singleInstanceRequests;},ready:()=>{assert.equal(typeof ready,'function');return ready();},
  dispose(){context.fixtureMain.startupRetry.cancel();cleanup();}};
}
module.exports={fullMain};
