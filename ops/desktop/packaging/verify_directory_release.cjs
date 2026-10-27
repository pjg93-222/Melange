'use strict';
// Independent final-ZIP inspection. Never starts the packaged program.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const IMPLEMENTATION_SHA256=crypto.createHash('sha256').update(fs.readFileSync(__filename)).digest('hex');
function isPE(file){const fd=fs.openSync(file,'r');try{const header=Buffer.alloc(64);if(fs.readSync(fd,header,0,64,0)!==64||header.toString('ascii',0,2)!=='MZ')return false;const offset=header.readUInt32LE(60),signature=Buffer.alloc(4);return offset<=fs.fstatSync(fd).size-4&&fs.readSync(fd,signature,0,4,offset)===4&&signature.equals(Buffer.from([80,69,0,0]));}finally{fs.closeSync(fd);}}
async function verifyNativeFiles(files,signing,root,entrypoint,builtByPath){
 const native=[],entries=new Map(files.map(value=>[value.file,value.item]));
 // The same tested pool drains every in-flight check on failure and admits at
 // most four Windows signature processes. Every header-detected PE is checked.
 await signing.signPool(files.map(value=>value.file),async file=>{
  const item=entries.get(file);
  const old=builtByPath.get(item.path);if(!old||old.sha256!==item.sha256)throw new Error('Complete PE census is not bound to build signing evidence: '+item.path);
  const result=await signing.signFile(file,root,{verify:true,owned:item.path===entrypoint});
  if(result.sha256!==item.sha256||result.thumbprint!==old.thumbprint)throw new Error('Final ZIP native signature differs from build evidence');
  if(result.thumbprint===signing.THUMBPRINT&&!result.timestamped)throw new Error('Publisher native binary lacks timestamp');
  native.push({...result,path:item.path});
 });
 return native.sort((a,b)=>a.path.localeCompare(b.path));
}
async function main(){
 const [clientArg,outputArg,rootArg,version]=process.argv.slice(2),client=path.resolve(clientArg),output=path.resolve(outputArg),root=path.resolve(rootArg);
 const directory=require(path.join(client,'directory-package.cjs')),signing=require(path.join(client,'release-signing.cjs')),proof=require(path.join(client,'directory-package-proof.cjs'));
 const descriptor=JSON.parse(fs.readFileSync(path.join(output,'package.json'))),publisherProof=JSON.parse(fs.readFileSync(path.join(output,'publisher-proof.json'))),app=descriptor.appId;
 if(descriptor.version!==version)throw new Error('Candidate version mismatch');
 const manifest={appId:app,version,platform:'win32',arch:'x64',issuedAt:new Date().toISOString(),publisherThumbprints:[signing.THUMBPRINT],package:{...descriptor,publisherProof}};
 proof.verifyDirectoryPackageProof(manifest);
 const destination=path.join(root,'verify',app),options={appId:app,version,entrypoint:descriptor.entrypoint,archive:descriptor};
 const inventory=await directory.extract(descriptor.path,destination,options);
 const built=JSON.parse(fs.readFileSync(path.join(output,'build-signatures.json'))),builtByPath=new Map(built.currentFiles.map(row=>[path.relative(built.appDirectory,row.path).replace(/\\/g,'/'),row]));
 const files=inventory.files.map(item=>({item,file:path.join(destination,...item.path.split('/'))}));
 const native=await verifyNativeFiles(files.filter(({file})=>isPE(file)),signing,root,descriptor.entrypoint,builtByPath);
 if(!native.some(row=>row.path===descriptor.entrypoint))throw new Error('Main application is not a verified PE');
 const asar=require(path.join(client,'node_modules','@electron','asar'));
 const packaged=JSON.parse(asar.extractFile(path.join(destination,'resources','app.asar'),'package.json'));
 if(packaged.version!==version||packaged.desktopAppConfig?.appId!==app||packaged.desktopAppConfig?.desktopDistribution!=='directory-zip'||packaged.desktopAppConfig?.desktopUpdateSource?.distribution!=='directory-zip')throw new Error('Packaged application configuration is not the frozen directory release');
 if(inventory.files.some(row=>/portable\.marker$|(?:^|\/)Uninstall [^/]+\.exe$/i.test(row.path)))throw new Error('Installer/legacy portable artifact present');
 const runtimeModules=['main.cjs','updater.cjs','trust.cjs','github-source.cjs','native-signature.cjs','publisher-trust.cjs','profile.cjs','directory-installer.cjs','directory-package.cjs','directory-package-proof.cjs','directory-retention.cjs'];
 for(const member of runtimeModules)if(!asar.extractFile(path.join(destination,'resources','app.asar'),member).equals(fs.readFileSync(path.join(client,member))))throw new Error('Packaged updater module differs from frozen source: '+member);
 const yauzl=JSON.parse(asar.extractFile(path.join(destination,'resources','app.asar'),'node_modules/yauzl/package.json'));
 if(yauzl.version!=='3.4.0'||!asar.extractFile(path.join(destination,'resources','app.asar'),'node_modules/yauzl/index.js').length)throw new Error('Pinned ZIP reader missing');
 const deepest=inventory.files.reduce((value,row)=>Math.max(value,row.path.length),0),exampleRoot='C:\\Users\\pgoff.contractor\\Downloads\\MelangeApplications\\'+descriptor.entrypoint.replace(/\.exe$/,'')+'-'+version;
 if(exampleRoot.length+1+deepest>=260)throw new Error('Work-PC program path exceeds Windows legacy path limit');
 await directory.verifyDirectory(destination,{...options,inventory});
 fs.writeFileSync(path.join(output,'native-verification.json'),JSON.stringify({schemaVersion:1,appId:app,version,verifierImplementationSha256:IMPLEMENTATION_SHA256,packageSha256:descriptor.sha256,completeNativeCensus:true,files:native,packagedAppConfig:packaged.desktopAppConfig,updaterModulesMatchFrozenSource:true,longestRelativeProgramPath:deepest,exampleWorkPCPathLength:exampleRoot.length+1+deepest,applicationExecuted:false},null,2)+'\n',{flag:'wx'});
 process.stdout.write(JSON.stringify({appId:app,verifiedNativeFiles:native.length,applicationExecuted:false})+'\n');
}
if(require.main===module)main().catch(error=>{console.error(error);process.exitCode=1;});
module.exports={isPE,verifyNativeFiles};
