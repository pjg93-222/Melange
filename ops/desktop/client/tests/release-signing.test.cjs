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
 await assert.rejects(signFile(f.main,f.root,{owned:true,execute:async(command,args,settings)=>{called={command,args,settings};return {stdout:JSON.stringify({path:f.main,status:'Valid',sha256:f.digest(f.main),thumbprint:'vendor',timestamped:true})};}}),/verification failed/);
 assert.equal(called.command,String.raw`C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe`);assert.equal(path.win32.isAbsolute(called.command),true);assert.equal(/[\x00-\x1f]/.test(called.command),false);assert.equal(/[\x00-\x1f]/.test(called.settings.env.PSModulePath),false);
 if(process.platform==='win32')assert.equal(fs.statSync(called.command).isFile(),true);
 assert.ok(called.args.includes('-RequirePublisher'));assert.equal(called.settings.windowsHide,true);assert.equal(called.args.includes('/p'),false);
});
test('a junction parent cannot redirect signing outside the private staging directory',async t=>{
 const f=fixture(t),link=path.join(f.root,'junction');fs.symlinkSync(path.join(f.vendor,'nsis'),link,'junction');
 let called=false;await assert.rejects(signFile(path.join(link,'elevate.exe'),f.root,{execute:async()=>{called=true;}}),/private regular/);assert.equal(called,false);fs.unlinkSync(link);
});
test('actual Windows subprocess verifies a copied vendor binary without signing or changing it',{skip:process.platform!=='win32'},async t=>{
 const f=fixture(t),file=path.join(f.root,'vendor-powershell.exe');
 fs.copyFileSync(String.raw`C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe`,file);
 const before=f.digest(file),result=await signFile(file,f.root,{verify:true});
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
