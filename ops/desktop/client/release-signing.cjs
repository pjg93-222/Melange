'use strict';
// Signing runs only on private build copies. The certificate stays in CurrentUser\My.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {execFile}=require('node:child_process'),{promisify}=require('node:util');
const run=promisify(execFile);
const THUMBPRINT='0EBC9AD04E929CDD731EDB5D278A4143BC3D3D30';
const SUBJECT='CN=Melange Systems Desktop Release (self-signed)';
const PE=/\.(exe|dll|pyd|node|ocx)$/i;
function within(root,file){const relative=path.relative(root,file);return relative!==''&&!relative.startsWith('..'+path.sep)&&relative!=='..'&&!path.isAbsolute(relative);}
function regular(file,directory=false){const stat=fs.lstatSync(file);if(stat.isSymbolicLink()||!(directory?stat.isDirectory():stat.isFile())||(!directory&&stat.nlink!==1))throw new Error('Build path must be a private regular '+(directory?'directory':'file'));return stat;}
function ancestors(file,directory=false){regular(file,directory);for(let parent=path.dirname(file);;parent=path.dirname(parent)){regular(parent,true);if(parent===path.dirname(parent))break;}}
function tree(root){regular(root,true);const files=[];for(const item of fs.readdirSync(root,{withFileTypes:true})){const file=path.join(root,item.name);if(item.isDirectory())files.push(...tree(file));else{regular(file);files.push(file);}}return files;}
function hash(file){return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');}
async function signFile(file,root,{verify=false,owned=false,execute=run}={}){
 file=path.resolve(file);root=path.resolve(root);if(!within(root,file)||!PE.test(file))throw new Error('Refusing binary outside private build root');ancestors(root,true);ancestors(file);
 const args=['-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',path.join(__dirname,'sign-staged-binary.ps1'),'-File',file,'-Root',root,'-Mode',verify?'Verify':'Sign',...(owned?['-RequirePublisher']:[])];
 const {stdout}=await execute('C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe',args,{windowsHide:true,timeout:300000,maxBuffer:1024*1024,env:{...process.env,PSModulePath:'C:\Windows\System32\WindowsPowerShell\v1.0\Modules;C:\Program Files\WindowsPowerShell\Modules'}});
 const result=JSON.parse(stdout.replace(/^\uFEFF/,''));
 if(result.path.toLowerCase()!==file.toLowerCase()||result.status!=='Valid'||result.sha256!==hash(file)||(owned&&(result.thumbprint!==THUMBPRINT||result.timestamped!==true)))throw new Error('Staged signature verification failed');
 return result;
}
function options(app,{env=process.env,platform=process.platform,sign=signFile,toolset}={}){
 const configured=env.DESKTOP_SIGNING_CERT_SHA1;
 if(!configured)return {};
 if(platform!=='win32'||configured!==THUMBPRINT||env.WINDOWS_PUBLISHER_NAME!==SUBJECT||!env.DESKTOP_SIGNING_ROOT||!path.isAbsolute(env.DESKTOP_SIGNING_ROOT)||!env.DESKTOP_DIST_ROOT||!within(path.resolve(env.DESKTOP_SIGNING_ROOT),path.resolve(env.DESKTOP_DIST_ROOT)))throw new Error('Release signing requires the approved certificate and a private build/dist root');
 if(env.CSC_LINK||env.WIN_CSC_LINK||env.CSC_KEY_PASSWORD||env.WIN_CSC_KEY_PASSWORD||env.ELECTRON_BUILDER_OFFLINE==='true')throw new Error('Release signing uses only the existing CurrentUser certificate and online timestamps');
 // A cached executable can bypass the sign hook and omits fuses from its key.
 env.ELECTRON_BUILDER_DISABLE_BUILD_CACHE='true';
 const root=path.resolve(env.DESKTOP_SIGNING_ROOT),records=[];let ready=false,appDirectory;
 ancestors(root,true);
 const owned=file=>path.basename(file)===app.name+'.exe'||/__uninstaller\.exe$/i.test(file)||new RegExp('^'+app.name+'-[0-9]+\\.[0-9]+\\.[0-9]+.*\\.exe$').test(path.basename(file));
 const record=async(file,verify=false,forceOwned=owned(file))=>{const result=await sign(file,root,{verify,owned:forceOwned});records.push(result);return result;};
 const verifyToolCopies=()=>{
  for(const directory of ['nsis','nsis-resources'])for(const file of tree(path.join(root,directory)).filter(file=>PE.test(file)))
   if(!records.some(row=>row.path.toLowerCase()===file.toLowerCase()&&row.sha256===hash(file)&&row.status==='Valid'))throw new Error('Private NSIS binary changed after signing');
 };
 return {
  forceCodeSigning:true,
  win:{signExts:['.dll','.pyd','.node','.ocx'],signtoolOptions:{publisherName:SUBJECT,signingHashAlgorithms:['sha256'],sign:async configuration=>{if(!ready)throw new Error('Private signing tools were not prepared');await record(configuration.path);}}},
  beforePack:async context=>{
   if(context.electronPlatformName!=='win32'||ready||!within(root,path.resolve(context.appOutDir)))throw new Error('Release signing supports one fresh private Windows package per build');
   if(env.ELECTRON_BUILDER_NSIS_DIR||env.ELECTRON_BUILDER_NSIS_RESOURCES_DIR)throw new Error('Release signing refuses inherited NSIS tool overrides');
   const tools=toolset||require('app-builder-lib/out/toolsets/windows.js');
   const compiler=await tools.getMakeNsisPath(),plugins=await tools.getNsisPluginsPath();
   const source=compiler.env?.NSISDIR;
   if(!source||!fs.existsSync(path.join(source,'Bin','makensis.exe')))throw new Error('Expected pinned legacy NSIS layout');
   const copies=[{source,destination:path.join(root,'nsis')},{source:path.dirname(plugins),destination:path.join(root,'nsis-resources')}];
   const originals=[];
   for(const copy of copies){if(fs.existsSync(copy.destination))throw new Error('Private NSIS staging already exists');for(const file of tree(copy.source))originals.push({file,sha256:hash(file)});fs.cpSync(copy.source,copy.destination,{recursive:true,errorOnExist:true,force:false});}
   for(const copy of copies)for(const file of tree(copy.destination).filter(file=>PE.test(file)))await record(file,false,false);
   for(const original of originals)if(hash(original.file)!==original.sha256)throw new Error('Shared NSIS tool cache changed');
   const userPlugins=path.join(context.packager.info.buildResourcesDir,'x86-unicode');
   if(fs.existsSync(userPlugins))throw new Error('Unreviewed custom NSIS plugins override the signed private toolset');
   env.ELECTRON_BUILDER_NSIS_DIR=copies[0].destination;env.ELECTRON_BUILDER_NSIS_RESOURCES_DIR=copies[1].destination;
   ready=true;verifyToolCopies();
  },
  afterSign:async context=>{
   if(!ready||!within(root,path.resolve(context.appOutDir)))throw new Error('Unexpected release signing root');
   // Fuses and resource editing have already completed. Sign remaining DLL/PYD
   // dependencies; valid third-party signatures are checked and left unchanged.
   appDirectory=path.resolve(context.appOutDir);
   for(const file of tree(appDirectory).filter(file=>PE.test(file)))await record(file,false,owned(file));
   await record(path.join(context.appOutDir,app.name+'.exe'),true,true);verifyToolCopies();
  },
  artifactBuildCompleted:async event=>{
   if(!event.file?.toLowerCase().endsWith('.exe'))return;
   if(!appDirectory)throw new Error('Application signing has not completed');
   for(const file of tree(appDirectory).filter(file=>PE.test(file)))await record(file,true,owned(file));
   await record(event.file,true,true);verifyToolCopies();
   if(!records.some(row=>path.basename(row.path)===app.name+'.exe'&&row.thumbprint===THUMBPRINT)||!records.some(row=>/__uninstaller\.exe$/i.test(row.path)&&row.thumbprint===THUMBPRINT)||!records.some(row=>path.basename(row.path)==='elevate.exe'&&row.thumbprint===THUMBPRINT))throw new Error('Application, elevation helper or uninstaller signature evidence is missing');
   const receipt={schemaVersion:1,appId:app.id,certificateThumbprint:THUMBPRINT,installer:path.resolve(event.file),files:records};
   fs.writeFileSync(event.file+'.signatures.json',JSON.stringify(receipt,null,2)+'\n',{flag:'wx'});
  }
 };
}
module.exports={THUMBPRINT,SUBJECT,within,tree,signFile,options};
