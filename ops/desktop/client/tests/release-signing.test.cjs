'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os'),crypto=require('node:crypto');
const {options,THUMBPRINT,SUBJECT,signFile,signPool}=require('../release-signing.cjs');
const app={id:'terrier',name:'Terrier'};
function fixture(t){
 const outer=fs.mkdtempSync(path.join(os.tmpdir(),'desktop-signing-')),root=path.join(outer,'private'),vendor=path.join(outer,'cache'),build=path.join(outer,'build-resources');fs.mkdirSync(root);fs.mkdirSync(build);
 const put=(name,body='unsigned')=>{const file=path.join(outer,name);fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,body);return file;};
 put('cache/nsis/Bin/makensis.exe');put('cache/nsis/elevate.exe');put('cache/nsis/Plugins/x86-unicode/System.dll');put('cache/nsis/Plugins/x86-unicode/nsDialogs.dll');put('cache/resources/plugins/x86-unicode/StdUtils.dll');put('cache/resources/plugins/x86-unicode/nsis7z.dll');
 const appOutDir=path.join(root,'dist','terrier','win-unpacked'),main=put('private/dist/terrier/win-unpacked/Terrier.exe'),dll=put('private/dist/terrier/win-unpacked/ffmpeg.dll'),third=put('private/dist/terrier/win-unpacked/resources/runtime/vendor.dll','valid-vendor');
 const env={DESKTOP_SIGNING_CERT_SHA1:THUMBPRINT,WINDOWS_PUBLISHER_NAME:SUBJECT,DESKTOP_SIGNING_ROOT:root,DESKTOP_DIST_ROOT:path.join(root,'dist')};
 const digest=file=>crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'),calls=[];
 const sign=async(file,_root,{verify,owned})=>{let content=fs.readFileSync(file,'utf8');const valid=content.startsWith('valid-');if(verify&&!valid)throw new Error('NotSigned');if(owned&&content==='valid-vendor')throw new Error('Wrong publisher');if(!verify&&!valid){content='valid-release:'+content;fs.writeFileSync(file,content);}calls.push({file,verify,owned});return {path:file,sha256:digest(file),status:'Valid',thumbprint:content==='valid-vendor'?'vendor':THUMBPRINT,timestamped:content!=='valid-vendor',preserved:valid};};
 const toolset={getMakeNsisPath:async()=>({path:path.join(vendor,'nsis','Bin','makensis.exe'),env:{NSISDIR:path.join(vendor,'nsis')}}),getNsisPluginsPath:async()=>path.join(vendor,'resources','plugins')};
 const context={electronPlatformName:'win32',appOutDir,packager:{info:{buildResourcesDir:build}}};
 t.after(()=>{assert.equal(path.dirname(outer),fs.realpathSync(os.tmpdir()));fs.rmSync(outer,{recursive:true,force:true});});
 return {root,put,env,sign,toolset,context,main,dll,third,calls,vendor,build,digest};
}
test('release signing is explicit, approved identity only and no credential or timestamp fallback',t=>{
 const f=fixture(t);assert.deepEqual(options(app,{env:{}}),{});
 for(const change of [{DESKTOP_SIGNING_CERT_SHA1:'a'.repeat(40)},{WINDOWS_PUBLISHER_NAME:'CN=Other'},{DESKTOP_DIST_ROOT:f.vendor},{CSC_LINK:'key.pfx'},{ELECTRON_BUILDER_OFFLINE:'true'}])assert.throws(()=>options(app,{env:{...f.env,...change},platform:'win32'}));
 const selected=options(app,{env:f.env,platform:'win32',sign:f.sign,toolset:f.toolset});assert.equal(selected.forceCodeSigning,true);assert.equal(f.env.ELECTRON_BUILDER_DISABLE_BUILD_CACHE,'true');assert.deepEqual(selected.win.signtoolOptions.signingHashAlgorithms,['sha256']);assert.equal(selected.win.signExts,undefined);
});
test('private NSIS copies, inner application, generated uninstaller and outer installer share approved signer',async t=>{
 const f=fixture(t),sourceHash=f.digest(path.join(f.vendor,'nsis','Plugins','x86-unicode','System.dll')),vendorHash=f.digest(f.third),config=options(app,{env:f.env,platform:'win32',sign:f.sign,toolset:f.toolset});
 await assert.rejects(config.win.signtoolOptions.sign({path:f.main}),/not prepared/);
 await config.beforePack(f.context);assert.ok(f.env.ELECTRON_BUILDER_NSIS_DIR.startsWith(f.root));assert.equal(f.digest(path.join(f.vendor,'nsis','Plugins','x86-unicode','System.dll')),sourceHash);
 assert.ok(fs.readFileSync(path.join(f.root,'nsis','Plugins','x86-unicode','System.dll'),'utf8').startsWith('valid-release:'));
 // electron-builder completes fuse/resource editing, then calls the sign hook.
 const deferred=['pyd','node','ocx','exe'].map(ext=>f.put('private/dist/terrier/win-unpacked/resources/runtime/native.'+ext));
 fs.appendFileSync(f.main,'+fuses');await config.win.signtoolOptions.sign({path:f.main});await config.afterSign(f.context);assert.equal(f.digest(f.third),vendorHash);for(const file of [f.dll,...deferred])assert.ok(f.calls.some(item=>item.file===file));
 const elevate=f.put('private/dist/terrier/win-unpacked/resources/elevate.exe'),uninstaller=f.put('private/dist/terrier/Terrier-1.0.15-win-x64.__uninstaller.exe'),installer=f.put('private/dist/terrier/Terrier-1.0.15-win-x64.exe');
 for(const file of [elevate,uninstaller,installer])await config.win.signtoolOptions.sign({path:file});
 fs.unlinkSync(uninstaller);await config.artifactBuildCompleted({file:installer});
 const proof=JSON.parse(fs.readFileSync(installer+'.signatures.json'));for(const target of [f.main,uninstaller,installer])assert.ok(proof.files.some(row=>row.path===target&&row.status==='Valid'&&row.thumbprint===THUMBPRINT&&row.timestamped));
 assert.equal(f.digest(f.third),vendorHash);
});
test('missing inner signature or changed private NSIS plugin cannot yield a release receipt',async t=>{
 const f=fixture(t),config=options(app,{env:f.env,platform:'win32',sign:f.sign,toolset:f.toolset});await config.beforePack(f.context);
 fs.writeFileSync(path.join(f.root,'nsis','Plugins','x86-unicode','System.dll'),'changed');await assert.rejects(config.afterSign(f.context),/changed after signing/);
});
test('private staging refuses reuse, external files and custom plugin shadowing',async t=>{
 const f=fixture(t);f.put('build-resources/x86-unicode/System.dll');const config=options(app,{env:f.env,platform:'win32',sign:f.sign,toolset:f.toolset});await assert.rejects(config.beforePack(f.context),/custom NSIS plugins/);
 await assert.rejects(signFile(path.join(f.vendor,'nsis','elevate.exe'),f.root),/outside private/);
 await assert.rejects(config.beforePack(f.context),/staging already exists/);
});
test('signature command uses CurrentUser script and refuses an invalid verification result',async t=>{
 const f=fixture(t);let called;
 await assert.rejects(signFile(f.main,f.root,{owned:true,execute:async(command,args,settings)=>{called={command,args,settings};return {stdout:JSON.stringify({path:fs.realpathSync.native(f.main),status:'Valid',sha256:f.digest(f.main),thumbprint:'vendor',timestamped:true})};}}),/verification failed/);
 assert.equal(called.command,String.raw`C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe`);assert.equal(path.win32.isAbsolute(called.command),true);assert.equal(/[\x00-\x1f]/.test(called.command),false);assert.equal(Object.hasOwn(called.settings,'env'),false);
 if(process.platform==='win32')assert.equal(fs.statSync(called.command).isFile(),true);
 assert.ok(called.args.includes('-RequirePublisher'));assert.equal(called.settings.windowsHide,true);assert.equal(called.args.includes('/p'),false);
});
test('signature invocation uses only a process-scoped policy bypass and no environment overrides',async t=>{
 const f=fixture(t),calls=[];
 for(const request of [{verify:true,owned:false},{verify:false,owned:true}]){
  const nativeFile=fs.realpathSync.native(f.main),nativeRoot=fs.realpathSync.native(f.root);
  const result=await signFile(f.main,f.root,{...request,execute:async(command,args,settings)=>{
   calls.push({command,args,settings});
   return {stdout:JSON.stringify({path:nativeFile,status:'Valid',sha256:f.digest(f.main),thumbprint:THUMBPRINT,timestamped:true})};
  }});
  assert.equal(result.path,path.resolve(f.main));assert.equal(result.verifiedPath,nativeFile);
  const called=calls.at(-1);
  assert.equal(called.command,String.raw`C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe`);
  assert.deepEqual(called.args,['-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',path.join(__dirname,'..','sign-staged-binary.ps1'),'-File',nativeFile,'-Root',nativeRoot,'-Mode',request.verify?'Verify':'Sign',...(request.owned?['-RequirePublisher']:[])]);
  assert.deepEqual(called.settings,{windowsHide:true,timeout:300000,maxBuffer:1024*1024});
  assert.equal(Object.hasOwn(called.settings,'env'),false);
  assert.equal(called.args.filter(value=>/^(?:-ExecutionPolicy|-EP|Bypass)$/i.test(value)).join(' '),'-ExecutionPolicy Bypass');
 }
 assert.equal(calls.length,2);
});
test('signature evidence refuses a same-byte replacement after fake execution',async t=>{
 const f=fixture(t);let reached=false;
 await assert.rejects(signFile(f.main,f.root,{verify:true,execute:async(command,args)=>{
  const file=args[args.indexOf('-File',args.indexOf('-File')+1)+1],before=fs.lstatSync(file,{bigint:true});
  fs.renameSync(file,file+'.original-fixture');fs.copyFileSync(file+'.original-fixture',file);
  assert.notEqual(fs.lstatSync(file,{bigint:true}).ino,before.ino);reached=true;
  return {stdout:JSON.stringify({path:file,status:'Valid',sha256:f.digest(file),thumbprint:THUMBPRINT,timestamped:true})};
 }}),/identity changed/);
 assert.equal(reached,true);
});
test('a junction parent cannot redirect signing outside the private staging directory',async t=>{
 const f=fixture(t),link=path.join(f.root,'junction');fs.symlinkSync(path.join(f.vendor,'nsis'),link,'junction');
 let called=false;await assert.rejects(signFile(path.join(link,'elevate.exe'),f.root,{execute:async()=>{called=true;}}),/private regular/);assert.equal(called,false);fs.unlinkSync(link);
});
function vendorPathDiagnostic(file,root,reported,baseline){
 const value=reported.path,isString=typeof value==='string',equal=(a,b)=>a.toLowerCase()===b.toLowerCase();
 const short=value=>/(?:^|[\\/])[^\\/]*~[0-9]+(?:[.][^\\/]*)?(?:[\\/]|$)/i.test(value);
 const facts={kind:'copied-vendor-path-diagnostic',requestedAbsolute:path.win32.isAbsolute(file),returnedPathString:isString,
  returnedAbsolute:isString&&path.win32.isAbsolute(value),lexicalPathEqual:isString&&equal(file,value),
  slashNormalizedEqual:isString&&equal(file.replace(/\//g,'\\'),value.replace(/\//g,'\\')),
  requestedShortComponent:short(file),returnedShortComponent:isString&&short(value),
  returnedProviderPrefix:isString&&/^(?:Microsoft[.]PowerShell[.]Core\\)?FileSystem::/i.test(value),
  requestedExtendedPrefix:/^\\\\[?.]\\/.test(file),returnedExtendedPrefix:isString&&/^\\\\[?.]\\/.test(value),
  basenameEqual:isString&&equal(path.win32.basename(file),path.win32.basename(value)),returnedEqualsRoot:isString&&equal(root,value),
  statusValid:reported.status==='Valid',reportedHashMatchesBefore:reported.sha256===baseline.sha256,returnedLocalFixtureDrive:false,refusedPathScope:false,
  expectedWithinNativeRoot:null,returnedWithinNativeRoot:null,sameNativeRealpath:null,sameDevIno:null,sameSize:null,
  regularSingleLink:null,expectedIdentityPreserved:null,diagnosticSizeBound:null,
  expectedHashPreserved:null,sameCurrentSHA256:null,returnedHashMatchesReported:null,diagnosticError:null};
 const drive=value=>{
  if(typeof value!=='string'||/[\x00-\x1f]/.test(value))return null;
  if(value.startsWith('\\\\?\\')){const plain=value.slice(4);return /^[a-z]:\\/i.test(plain)?plain[0].toUpperCase():null;}
  return /^[a-z]:[\\/]/i.test(value)?value[0].toUpperCase():null;
 };
 const requestedDrive=drive(file),returnedDrive=drive(value);
 facts.returnedLocalFixtureDrive=requestedDrive!==null&&returnedDrive===requestedDrive;
 if(!facts.returnedLocalFixtureDrive){facts.refusedPathScope=true;return facts;}
 try{
  if(!facts.returnedAbsolute)return facts;
  const nativeRoot=fs.realpathSync.native(root),nativeExpected=fs.realpathSync.native(file),nativeReturned=fs.realpathSync.native(value);
  const contained=p=>{const r=path.win32.relative(nativeRoot,p);return r!==''&&r!=='..'&&!r.startsWith('..'+path.win32.sep)&&!path.win32.isAbsolute(r);};
  facts.expectedWithinNativeRoot=contained(nativeExpected);facts.returnedWithinNativeRoot=contained(nativeReturned);
  if(!facts.expectedWithinNativeRoot||!facts.returnedWithinNativeRoot)return facts;
  const expected=fs.lstatSync(nativeExpected,{bigint:true}),returned=fs.lstatSync(nativeReturned,{bigint:true});
  facts.sameNativeRealpath=equal(nativeExpected,nativeReturned);facts.sameDevIno=expected.dev===returned.dev&&expected.ino===returned.ino;
  facts.sameSize=expected.size===returned.size;
  facts.regularSingleLink=expected.isFile()&&!expected.isSymbolicLink()&&expected.nlink===1n&&returned.isFile()&&!returned.isSymbolicLink()&&returned.nlink===1n;
  facts.expectedIdentityPreserved=expected.dev===baseline.stat.dev&&expected.ino===baseline.stat.ino&&expected.size===baseline.stat.size;
  facts.diagnosticSizeBound=baseline.stat.size>0n&&baseline.stat.size<=16n*1024n*1024n;
  if(facts.regularSingleLink&&facts.sameSize&&facts.expectedIdentityPreserved&&facts.diagnosticSizeBound){
   const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
   const current=hash(nativeExpected),returnedHash=hash(nativeReturned);
   facts.expectedHashPreserved=current===baseline.sha256;facts.sameCurrentSHA256=current===returnedHash;facts.returnedHashMatchesReported=returnedHash===reported.sha256;
  }
 }catch(error){facts.diagnosticError=typeof error.code==='string'&&/^[A-Z_]{1,32}$/.test(error.code)?error.code:'diagnostic-read-error';}
 return facts;
}

test('actual Windows subprocess verifies a copied vendor binary without signing or changing it',{skip:process.platform!=='win32'},async t=>{
 const f=fixture(t),file=path.join(f.root,'vendor-powershell.exe');
 fs.copyFileSync(String.raw`C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe`,file);
 const before=f.digest(file),baseline={stat:fs.lstatSync(file,{bigint:true}),sha256:before};
 const execute=async(command,args,settings)=>{
  const response=await require('node:util').promisify(require('node:child_process').execFile)(command,args,settings);
  let facts;
  try{facts=vendorPathDiagnostic(file,f.root,JSON.parse(response.stdout.replace(/^\uFEFF/,'')),baseline);}
  catch(error){facts={kind:'copied-vendor-path-diagnostic',diagnosticError:'response-json-unavailable'};}
  t.diagnostic(JSON.stringify(facts));return response;
 };
 const result=await signFile(file,f.root,{verify:true,execute});
 assert.equal(result.status,'Valid');assert.equal(result.signed,false);assert.equal(result.preserved,true);assert.equal(result.sha256,before);assert.equal(f.digest(file),before);
});

test('signing pool bounds concurrency to four, visits every unique file and refuses duplicates',async()=>{
 let active=0,peak=0;const visited=[];
 await signPool(Array.from({length:13},(_,i)=>String(i)+'.dll'),async file=>{active++;peak=Math.max(peak,active);await new Promise(resolve=>setTimeout(resolve,10));visited.push(file);active--;});
 assert.equal(peak,4);assert.equal(active,0);assert.equal(new Set(visited).size,13);
 await assert.rejects(signPool(['same.dll','SAME.dll'],async()=>assert.fail('Duplicate task started')),/distinct private files/);
});

test('signing pool stops admission on failure and drains all in-flight operations before rejecting',async()=>{
 let active=0;const started=[],finished=[];const failure=new Error('signature rejected');
 await assert.rejects(signPool(Array.from({length:20},(_,i)=>String(i)+'.dll'),async file=>{started.push(file);active++;try{if(file==='0.dll')throw failure;await new Promise(resolve=>setTimeout(resolve,20));finished.push(file);}finally{active--;}}),error=>error===failure);
 assert.equal(active,0);assert.equal(started.length,4);assert.equal(finished.length,3);
});

async function preparedRelease(t,decorate=sign=>sign){
 const f=fixture(t),elevate=f.put('private/dist/terrier/win-unpacked/resources/elevate.exe');
 const sign=decorate(f.sign,f),config=options(app,{env:f.env,platform:'win32',sign,toolset:f.toolset});
 await config.beforePack(f.context);await config.win.signtoolOptions.sign({path:f.main});await config.afterSign(f.context);
 const uninstaller=f.put('private/dist/terrier/Terrier-1.0.15-win-x64.__uninstaller.exe'),installer=f.put('private/dist/terrier/Terrier-1.0.15-win-x64.exe');
 for(const file of [uninstaller,installer])await config.win.signtoolOptions.sign({path:file});
 fs.unlinkSync(uninstaller);
 return {...f,elevate,config,installer,uninstaller};
}
test('current owned helper rejects a changed vendor signer despite approved historical evidence',async t=>{
 const attempts=[],f=await preparedRelease(t,(sign,_f)=>async(file,root,request)=>{attempts.push({file,...request});return sign(file,root,request);});
 const original=f.digest(f.elevate);fs.writeFileSync(f.elevate,'valid-vendor');
 assert.notEqual(f.digest(f.elevate),original);
 await assert.rejects(f.config.artifactBuildCompleted({file:f.installer}),/Wrong publisher/);
 const current=attempts.filter(row=>row.file===f.elevate&&row.verify).at(-1);
 assert.equal(current.owned,true);assert.equal(fs.readFileSync(f.elevate,'utf8'),'valid-vendor');assert.equal(fs.existsSync(f.installer+'.signatures.json'),false);
});
test('current helper requires a timestamp even when its reported signer is approved',async t=>{
 let final=false;
 const f=await preparedRelease(t,(sign,base)=>async(file,root,request)=>{const result=await sign(file,root,request);return final&&file===path.join(base.context.appOutDir,'resources','elevate.exe')&&request.verify?{...result,timestamped:false}:result;});
 final=true;
 await assert.rejects(f.config.artifactBuildCompleted({file:f.installer}),/Current application, elevation helper or installer signature/);
 assert.equal(fs.existsSync(f.installer+'.signatures.json'),false);
});
test('another same-named vendor helper cannot replace the exact current application helper',async t=>{
 const f=await preparedRelease(t),decoy=f.put('private/dist/terrier/win-unpacked/resources/vendor/elevate.exe','valid-vendor');
 fs.unlinkSync(f.elevate);
 await assert.rejects(f.config.artifactBuildCompleted({file:f.installer}),/Current application, elevation helper or installer signature/);
 assert.equal(f.calls.filter(row=>row.file===decoy).at(-1).owned,false);assert.equal(fs.readFileSync(decoy,'utf8'),'valid-vendor');assert.equal(fs.existsSync(f.installer+'.signatures.json'),false);
});
test('helper bytes changed after its current verification cannot yield a receipt',async t=>{
 let final=false;
 const f=await preparedRelease(t,(sign,base)=>async(file,root,request)=>{const result=await sign(file,root,request);if(final&&request.verify&&file.endsWith('Terrier-1.0.15-win-x64.exe'))fs.writeFileSync(path.join(base.context.appOutDir,'resources','elevate.exe'),'valid-release:changed-after-verification');return result;});
 final=true;
 await assert.rejects(f.config.artifactBuildCompleted({file:f.installer}),/changed after verification/);
 assert.equal(fs.readFileSync(f.elevate,'utf8'),'valid-release:changed-after-verification');assert.equal(fs.existsSync(f.installer+'.signatures.json'),false);
});
test('fresh exact current rows are distinct from staged uninstaller history and preserve vendors',async t=>{
 const f=await preparedRelease(t),vendor=f.digest(f.third);
 await f.config.artifactBuildCompleted({file:f.installer});
 const proof=JSON.parse(fs.readFileSync(f.installer+'.signatures.json'));
 for(const file of [f.main,f.elevate,f.installer]){
  const rows=proof.currentFiles.filter(row=>row.path===file);assert.equal(rows.length,1);assert.equal(rows[0].sha256,f.digest(file));assert.equal(rows[0].thumbprint,THUMBPRINT);assert.equal(rows[0].timestamped,true);
 }
 assert.equal(proof.currentFiles.some(row=>row.path===f.uninstaller),false);assert.ok(proof.files.some(row=>row.path===f.uninstaller));assert.equal(proof.uninstallerEvidence,'staged-history-only');
 assert.equal(f.digest(f.third),vendor);assert.equal(proof.currentFiles.find(row=>row.path===f.third).thumbprint,'vendor');
});
test('fixed builtin signing imports and command-origin guards fail closed without signing',{skip:process.platform!=='win32'},async()=>{
 const source=fs.readFileSync(path.join(__dirname,'..','sign-staged-binary.ps1'),'utf8');
 for(const module of ['Utility','Security'])assert.ok(source.includes("Import-Module -Name ($PSHOME + '\\Modules\\Microsoft.PowerShell."+module+"\\Microsoft.PowerShell."+module+".psd1') -ErrorAction Stop"));
 assert.ok(source.includes("$PSVersionTable.PSEdition -ne 'Desktop'"));assert.ok(source.includes('$PSVersionTable.PSVersion.Minor -ne 1'));
 assert.ok(source.includes('Microsoft.PowerShell.Utility\\Get-FileHash -LiteralPath'));assert.ok(source.includes('Microsoft.PowerShell.Security\\Get-AuthenticodeSignature -LiteralPath'));
 assert.equal(/\$env:PSModulePath\s*=/i.test(source),false);
 const guard=source.match(/^function Assert-ReleaseBuiltinCommand[^\n]*\{\r?\n[\s\S]*?^\}/m);assert.ok(guard);
 const script=`$ErrorActionPreference='Stop'
function Get-Command([string]$Name,[string]$ErrorAction) {
 if($script:scenario -eq 'missing'){throw 'Unresolved builtin'}
 $module='Microsoft.PowerShell.Utility';$file=[IO.Path]::Combine($PSHOME,'Modules',$module,'Microsoft.PowerShell.Utility.psm1');$type='Function'
 if($script:scenario -eq 'wrong-module'){$module='Unreviewed.Module'}
 if($script:scenario -eq 'wrong-path'){$file='C:\\Unreviewed\\Utility.psm1'}
 if($script:scenario -eq 'wrong-type'){$type='Alias'}
 [pscustomobject]@{ModuleName=$module;CommandType=$type;Module=[pscustomobject]@{Path=$file}}
}
${guard[0]}
$script:scenario='good';Assert-ReleaseBuiltinCommand 'Get-FileHash' 'Microsoft.PowerShell.Utility' 'Microsoft.PowerShell.Utility.psm1' 'Function'
foreach($scenario in @('missing','wrong-module','wrong-path','wrong-type')){
 $script:scenario=$scenario;$refused=$false
 try{Assert-ReleaseBuiltinCommand 'Get-FileHash' 'Microsoft.PowerShell.Utility' 'Microsoft.PowerShell.Utility.psm1' 'Function'}catch{$refused=$true}
 if(-not $refused){throw ('Invalid command origin accepted: '+$scenario)}
}
'four-invalid-origins-refused'`;
 const {stdout}=await require('node:util').promisify(require('node:child_process').execFile)(String.raw`C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe`,['-NoProfile','-NonInteractive','-EncodedCommand',Buffer.from(script,'utf16le').toString('base64')],{windowsHide:true,timeout:15000,maxBuffer:1024*1024});
 assert.equal(stdout.trim(),'four-invalid-origins-refused');
});


async function preparedWithoutUninstaller(t){
 const f=fixture(t);f.context.packager.config={extraMetadata:{desktopAppConfig:{desktopUninstaller:false}}};
 const config=options(app,{env:f.env,platform:'win32',sign:f.sign,toolset:f.toolset,withoutUninstaller:true});
 await config.beforePack(f.context);await config.afterSign(f.context);
 const elevate=f.put('private/dist/terrier/win-unpacked/resources/elevate.exe'),installer=f.put('private/dist/terrier/Terrier-1.0.21-win-x64.exe');
 for(const file of [elevate,installer])await config.win.signtoolOptions.sign({path:file});
 return {...f,config,elevate,installer};
}
test('explicit no-uninstaller release retains installer application helper and vendor signature evidence',async t=>{
 const f=await preparedWithoutUninstaller(t),vendor=f.digest(f.third);
 await f.config.artifactBuildCompleted({file:f.installer});
 const receipt=JSON.parse(fs.readFileSync(f.installer+'.signatures.json'));
 assert.equal(receipt.desktopUninstaller,false);assert.equal(receipt.uninstallerEvidence,'intentionally-absent');
 for(const file of [f.main,f.elevate,f.installer]){
  const row=receipt.currentFiles.find(row=>row.path===file);assert.ok(row);assert.equal(row.sha256,f.digest(file));assert.equal(row.thumbprint,THUMBPRINT);assert.equal(row.timestamped,true);
 }
 assert.equal(f.digest(f.third),vendor);assert.equal(receipt.currentFiles.find(row=>row.path===f.third).thumbprint,'vendor');
});
test('no-uninstaller signing requires explicit matching packaged metadata',async t=>{
 const f=fixture(t),config=options(app,{env:f.env,platform:'win32',sign:f.sign,toolset:f.toolset,withoutUninstaller:true});
 await assert.rejects(config.beforePack(f.context),/matching application metadata/);
});
test('no-uninstaller release rejects even removed staged uninstaller history',async t=>{
 const f=await preparedWithoutUninstaller(t),uninstaller=f.put('private/dist/terrier/Terrier-1.0.21-win-x64.__uninstaller.exe');
 await f.config.win.signtoolOptions.sign({path:uninstaller});fs.unlinkSync(uninstaller);
 await assert.rejects(f.config.artifactBuildCompleted({file:f.installer}),/contains uninstaller/);
 assert.equal(fs.existsSync(f.installer+'.signatures.json'),false);
});
test('no-uninstaller release still refuses a missing elevation helper',async t=>{
 const f=await preparedWithoutUninstaller(t);fs.unlinkSync(f.elevate);
 await assert.rejects(f.config.artifactBuildCompleted({file:f.installer}),/Current application, elevation helper or installer signature/);
 assert.equal(fs.existsSync(f.installer+'.signatures.json'),false);
});


test('no-uninstaller receipt rejects each recognized legacy or generated executable name',async t=>{
 for(const name of ['old-uninstaller.exe','unins000.exe','candidate__uninstaller.exe'])await t.test(name,async t=>{
  const f=await preparedWithoutUninstaller(t),file=f.put('private/dist/terrier/'+name);
  await f.config.win.signtoolOptions.sign({path:file});fs.unlinkSync(file);
  await assert.rejects(f.config.artifactBuildCompleted({file:f.installer}),/contains uninstaller/);
  assert.equal(fs.existsSync(f.installer+'.signatures.json'),false);
 });
});

async function preparedBuiltin(t){
 const f=fixture(t);f.context.packager.config={extraMetadata:{desktopAppConfig:{desktopUninstaller:false}}};
 f.toolset.getNsisPluginsPath=async()=>{throw new Error('Built-in packaging must not request installer plug-ins');};
 const config=options(app,{env:f.env,platform:'win32',sign:f.sign,toolset:f.toolset,withoutUninstaller:true,builtinInstaller:true});
 await config.beforePack(f.context);await config.afterSign(f.context);
 const installer=f.put('private/dist/terrier/Terrier-1.0.23-win-x64.exe');await config.win.signtoolOptions.sign({path:installer});
 return {...f,config,installer};
}

test('built-in installer signs the program and installer without adding plug-ins or an elevation helper',async t=>{
 const f=await preparedBuiltin(t),vendor=f.digest(f.third);
 assert.equal(fs.existsSync(path.join(f.root,'nsis-resources')),false);
 assert.equal(fs.existsSync(path.join(f.root,'nsis','Plugins')),false);
 assert.equal(f.env.ELECTRON_BUILDER_NSIS_RESOURCES_DIR,undefined);
 assert.equal(f.calls.some(row=>withinTool(row.file)),false);
 function withinTool(file){return file.startsWith(path.join(f.root,'nsis')+path.sep);}
 const compiler=path.join(f.root,'nsis','Bin','makensis.exe');
 assert.equal(f.digest(compiler),f.digest(path.join(f.vendor,'nsis','Bin','makensis.exe')));
 await f.config.artifactBuildCompleted({file:f.installer});
 const receipt=JSON.parse(fs.readFileSync(f.installer+'.signatures.json'));
 assert.equal(receipt.installerFormat,'builtin-nsis-v1');assert.deepEqual(receipt.installerPlugins,[]);
 assert.equal(receipt.desktopUninstaller,false);assert.equal(receipt.uninstallerEvidence,'intentionally-absent');
 assert.ok(receipt.compilerFiles.some(row=>row.path===compiler&&row.sha256===f.digest(compiler)));
 assert.deepEqual(new Set(receipt.currentFiles.map(row=>row.path)),new Set([f.main,f.dll,f.third,f.installer]));
 assert.equal(f.digest(f.third),vendor);assert.equal(receipt.currentFiles.find(row=>row.path===f.third).thumbprint,'vendor');
});

test('built-in installer refuses a compiler changed after staging',async t=>{
 const f=await preparedBuiltin(t);fs.appendFileSync(path.join(f.root,'nsis','Bin','makensis.exe'),'changed');
 await assert.rejects(f.config.artifactBuildCompleted({file:f.installer}),/compiler changed after staging/);
 assert.equal(fs.existsSync(f.installer+'.signatures.json'),false);
});

test('built-in installer refuses a changed compiler file set',async t=>{
 const f=await preparedBuiltin(t);f.put('private/nsis/extra.nsh');
 await assert.rejects(f.config.artifactBuildCompleted({file:f.installer}),/compiler file set changed/);
 assert.equal(fs.existsSync(f.installer+'.signatures.json'),false);
});
