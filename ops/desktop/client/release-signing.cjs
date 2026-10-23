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
async function signPool(files,task){
 const identities=files.map(file=>path.resolve(file).toLowerCase());
 if(new Set(identities).size!==files.length)throw new Error('Signing pool requires distinct private files');
 let next=0,failed=false,failure;
 await Promise.all(Array.from({length:Math.min(4,files.length)},async()=>{
  while(!failed){const index=next++;if(index>=files.length)return;
   try{await task(files[index]);}catch(error){if(!failed)failure=error;failed=true;}
  }
 }));
 // Drain every in-flight operation before returning failure or releasing a phase.
 if(failed)throw failure;
}
async function signFile(file,root,{verify=false,owned=false,execute=run}={}){
 file=path.resolve(file);root=path.resolve(root);if(!within(root,file)||!PE.test(file))throw new Error('Refusing binary outside private build root');ancestors(root,true);ancestors(file);
 const args=['-NoProfile','-NonInteractive','-File',path.join(__dirname,'sign-staged-binary.ps1'),'-File',file,'-Root',root,'-Mode',verify?'Verify':'Sign',...(owned?['-RequirePublisher']:[])];
 const {stdout}=await execute(String.raw`C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe`,args,{windowsHide:true,timeout:300000,maxBuffer:1024*1024});
 const result=JSON.parse(stdout.replace(/^\uFEFF/,''));
 const failure=result.path.toLowerCase()!==file.toLowerCase()?'path':result.status!=='Valid'?'status':result.sha256!==hash(file)?'sha256':owned&&result.thumbprint!==THUMBPRINT?'thumbprint':owned&&result.timestamped!==true?'timestamped':null;
 if(failure)throw new Error('Staged signature verification failed ('+failure+')');
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
 const identity=file=>path.resolve(file).toLowerCase();
 const owned=file=>path.basename(file)===app.name+'.exe'||/__uninstaller\.exe$/i.test(file)||new RegExp('^'+app.name+'-[0-9]+\\.[0-9]+\\.[0-9]+.*\\.exe$').test(path.basename(file))||(appDirectory&&identity(file)===identity(path.join(appDirectory,'resources','elevate.exe')));
 const record=async(file,verify=false,forceOwned=owned(file))=>{const result=await sign(file,root,{verify,owned:forceOwned});records.push(result);return result;};
 const verifyToolCopies=()=>{
  for(const directory of ['nsis','nsis-resources'])for(const file of tree(path.join(root,directory)).filter(file=>PE.test(file)))
   if(!records.some(row=>row.path.toLowerCase()===file.toLowerCase()&&row.sha256===hash(file)&&row.status==='Valid'))throw new Error('Private NSIS binary changed after signing');
 };
 return {
  forceCodeSigning:true,
  win:{signtoolOptions:{publisherName:SUBJECT,signingHashAlgorithms:['sha256'],sign:async configuration=>{if(!ready)throw new Error('Private signing tools were not prepared');await record(configuration.path);}}},
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
   await signPool(copies.flatMap(copy=>tree(copy.destination).filter(file=>PE.test(file))),file=>record(file,false,false));
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
   await signPool(tree(appDirectory).filter(file=>PE.test(file)),file=>record(file,false,owned(file)));
   await record(path.join(context.appOutDir,app.name+'.exe'),true,true);verifyToolCopies();
  },
  artifactBuildCompleted:async event=>{
   if(!event.file?.toLowerCase().endsWith('.exe'))return;
   if(!appDirectory)throw new Error('Application signing has not completed');
   const current=new Map();
   const verifyCurrent=async(file,forceOwned=owned(file))=>{const result=await record(file,true,forceOwned);current.set(identity(file),result);};
   await signPool(tree(appDirectory).filter(file=>PE.test(file)),file=>verifyCurrent(file));
   await verifyCurrent(event.file,true);verifyToolCopies();
   for(const file of [path.join(appDirectory,app.name+'.exe'),path.join(appDirectory,'resources','elevate.exe'),path.resolve(event.file)]){
    const result=current.get(identity(file));
    if(!result||identity(result.path)!==identity(file)||result.status!=='Valid'||result.thumbprint!==THUMBPRINT||result.timestamped!==true)throw new Error('Current application, elevation helper or installer signature evidence is missing');
    ancestors(file);if(result.sha256!==hash(file))throw new Error('Current application, elevation helper or installer changed after verification');
   }
   if(!records.some(row=>/__uninstaller\.exe$/i.test(row.path)&&row.status==='Valid'&&row.thumbprint===THUMBPRINT&&row.timestamped===true))throw new Error('Staged uninstaller signature evidence is missing');
   const receipt={schemaVersion:1,appId:app.id,certificateThumbprint:THUMBPRINT,installer:path.resolve(event.file),files:records,currentFiles:[...current.values()],uninstallerEvidence:'staged-history-only'};
   fs.writeFileSync(event.file+'.signatures.json',JSON.stringify(receipt,null,2)+'\n',{flag:'wx'});
  }
 };
}
module.exports={THUMBPRINT,SUBJECT,within,tree,signFile,signPool,options};
