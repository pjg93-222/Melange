'use strict';
// Keep electron-builder and the final installer in one process: the signing
// hooks retain the private-tool and native-program evidence between phases.
const fs=require('node:fs'),path=require('node:path');
const {appDefinition}=require('./apps.cjs');

function argumentsFor(argv,{platform=process.platform,arch=process.arch}={}){
  let target=null,architecture=null,publish='never',directoryOnly=false;
  for(let index=0;index<argv.length;index++){
    const item=argv[index];
    const platforms={'--win':'win32','--windows':'win32','--mac':'darwin','--macos':'darwin','--linux':'linux'};
    if(platforms[item]){if(target&&target!==platforms[item])throw new Error('Build one platform per invocation');target=platforms[item];continue;}
    if(['--x64','--arm64','--ia32','--armv7l','--universal'].includes(item)){
      if(architecture&&architecture!==item.slice(2))throw new Error('Build one architecture per invocation');
      architecture=item.slice(2);continue;
    }
    if(item==='--dir'){directoryOnly=true;continue;}
    if(item==='--publish'){publish=argv[++index];continue;}
    if(item.startsWith('--publish=')){publish=item.slice('--publish='.length);continue;}
    throw new Error('Unsupported desktop build argument: '+item);
  }
  if(!['never','always','onTag','onTagOrDraft'].includes(publish))throw new Error('Invalid publish mode');
  target=target||platform;
  if(!['win32','darwin','linux'].includes(target))throw new Error('Unsupported desktop build platform');
  return {platform:target,arch:architecture||(target==='win32'?'x64':arch),publish,directoryOnly};
}

async function buildNative(argv=process.argv.slice(2),{
  env=process.env,platform=process.platform,arch=process.arch,projectDir=__dirname,
  electronBuilder,loadConfig=()=>require('./builder.cjs'),compile
}={}){
  const request=argumentsFor(argv,{platform,arch});
  const api=electronBuilder||require('electron-builder'),config=loadConfig();
  const selectedPlatform=request.platform==='win32'?api.Platform.WINDOWS:request.platform==='darwin'?api.Platform.MAC:api.Platform.LINUX;
  if(request.platform!=='win32'){
    return api.build({projectDir,config,targets:api.createTargets([selectedPlatform],request.directoryOnly?'dir':null,request.arch),publish:request.publish});
  }
  if(platform!=='win32'||request.arch!=='x64')throw new Error('Signed Windows releases require Windows and x64');
  if(request.publish!=='never')throw new Error('Publish signed Windows releases through the signed-feed release pipeline');
  if(config.forceCodeSigning!==true||typeof config.beforePack!=='function'||typeof config.afterSign!=='function'||
      typeof config.win?.signtoolOptions?.sign!=='function'||typeof config.artifactBuildCompleted!=='function'){
    throw new Error('Production Windows builds require the approved private signing configuration; no unsigned fallback');
  }
  if(config.extraMetadata?.desktopAppConfig?.desktopUninstaller!==false||
      JSON.stringify(config.win.target)!==JSON.stringify(['dir'])||config.nsis){
    throw new Error('Production Windows builds require the built-in no-uninstaller directory configuration');
  }
  let signedContext;
  const afterSign=config.afterSign;
  const buildConfig={...config,afterSign:async context=>{
    if(signedContext)throw new Error('One signed Windows application is required per build');
    await afterSign(context);signedContext=context;
  }};
  const artifacts=await api.build({projectDir,config:buildConfig,targets:api.createTargets([selectedPlatform],'dir',request.arch),publish:'never'});
  if(!signedContext||signedContext.electronPlatformName!=='win32')throw new Error('The native program signing phase did not complete');
  if(request.directoryOnly)return artifacts;
  const selected=appDefinition(config.extraMetadata.desktopAppConfig.appId);
  const version=signedContext.packager.appInfo.version;
  const program=path.resolve(signedContext.appOutDir);
  fs.accessSync(path.join(program,'resources','app-update.yml'),fs.constants.R_OK);
  if(!env.ELECTRON_BUILDER_NSIS_DIR)throw new Error('Private compiler staging did not complete');
  const output=path.join(path.resolve(projectDir,config.directories.output),selected.name+'-'+version+'-win-x64.exe');
  const compiler=compile||require('./build-plugin-free.cjs').build;
  const built=await compiler({appId:selected.id,version,program,output,makensis:env.ELECTRON_BUILDER_NSIS_DIR,compression:'zlib'});
  if(built.installer!==output||built.format!=='builtin-nsis-v1')throw new Error('Unexpected built-in installer result');
  await config.win.signtoolOptions.sign({path:output});
  await config.artifactBuildCompleted({file:output});
  const receipt=JSON.parse(fs.readFileSync(output+'.signatures.json','utf8'));
  if(receipt.installer!==output||receipt.appId!==selected.id||receipt.installerFormat!=='builtin-nsis-v1'||
      receipt.desktopUninstaller!==false||!Array.isArray(receipt.installerPlugins)||receipt.installerPlugins.length!==0){
    throw new Error('Final built-in installer signature receipt is missing or mismatched');
  }
  return [...artifacts,output];
}
module.exports={argumentsFor,buildNative};
if(require.main===module)buildNative().then(artifacts=>console.log(JSON.stringify({artifacts}))).catch(error=>{console.error(error);process.exitCode=1;});
