'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os'),{spawnSync}=require('node:child_process');
test('all three directory builds select the ZIP updater and skip NSIS includes, while native builds retain NSIS',t=>{
 const root=fs.realpathSync.native(fs.mkdtempSync(path.join(os.tmpdir(),'directory-build-config-')));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
 for(const app of ['melange','mentat','terrier']){
  const runtime=path.join(root,'runtime',app);fs.mkdirSync(path.join(runtime,'python','bin'),{recursive:true});fs.mkdirSync(path.join(runtime,'bootstrap'));
  fs.writeFileSync(path.join(runtime,'python',process.platform==='win32'?'python.exe':'bin/python3'),'');fs.writeFileSync(path.join(runtime,'bootstrap','desktop_backend.py'),'');
  for(const distribution of ['directory-zip','native']){
   const env={...process.env,DESKTOP_APP_ID:app,DESKTOP_RUNTIME_ROOT:path.join(root,'runtime'),DESKTOP_DIST_ROOT:path.join(root,distribution),DESKTOP_DISTRIBUTION:distribution,DESKTOP_ACCESS_TRUST:''};
   for(const name of ['DESKTOP_SIGNING_CERT_SHA1','WINDOWS_PUBLISHER_NAME','DESKTOP_PUBLIC_DATA_MODE','DESKTOP_SHARED_SCRAPE','DESKTOP_GITHUB_REPOSITORY','DESKTOP_UPDATE_PROVIDER'])delete env[name];
   const script="(async()=>{const fs=require('fs'),path=require('path'),c=require('./builder.cjs'),out=path.join(c.directories.output,'win-unpacked');fs.mkdirSync(out,{recursive:true});console.log=()=>{};await require('./after-pack.cjs')({appOutDir:out,packager:{config:c,appInfo:{version:'1.0.20'}}});process.stdout.write(JSON.stringify({target:c.win.target,metadata:c.extraMetadata.desktopAppConfig,include:fs.existsSync(path.join(c.directories.output,'installer.generated.nsh'))}));})().catch(e=>{console.error(e);process.exit(1)});";
   const child=spawnSync(process.execPath,['-e',script],{cwd:path.resolve(__dirname,'..'),env,encoding:'utf8',windowsHide:true});assert.equal(child.status,0,child.stderr);
   const result=JSON.parse(child.stdout);assert.deepEqual(result.target,[distribution==='directory-zip'?'dir':'nsis']);assert.equal(result.include,distribution==='native');assert.equal(result.metadata.desktopDistribution,distribution==='directory-zip'?distribution:undefined);assert.equal(result.metadata.desktopUpdateSource.distribution,distribution==='directory-zip'?distribution:undefined);
  }
 }
});

test('ZIP proof signer accepts the public code-signing EKU through the X509 extension without key access',{skip:process.platform!=='win32'},()=>{
 const source=fs.readFileSync(path.resolve(__dirname,'../../packaging/sign_directory_package.ps1'),'utf8'),helper=source.match(/^function Test-CodeSigningEku[^\n]*\{\r?\n[\s\S]*?^\}/m);assert.ok(helper);
 const certificate=fs.readFileSync(path.resolve(__dirname,'../melange-systems-desktop-release.cer')).toString('base64');
 const script=helper[0]+"\n$certificate=[Security.Cryptography.X509Certificates.X509Certificate2]::new([Convert]::FromBase64String('"+certificate+"')); if(-not(Test-CodeSigningEku $certificate)){throw 'EKU mismatch'}; if($certificate.HasPrivateKey){throw 'Public fixture contains a key'}; 'public-certificate-eku-valid'";
 const child=spawnSync(String.raw`C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe`,['-NoProfile','-NonInteractive','-EncodedCommand',Buffer.from(script,'utf16le').toString('base64')],{encoding:'utf8',windowsHide:true,timeout:15000});assert.equal(child.status,0,child.stderr);assert.equal(child.stdout.trim(),'public-certificate-eku-valid');
});

test('native census recognizes PE headers in unconventional extensions and refuses fake headers',t=>{
 const root=fs.realpathSync.native(fs.mkdtempSync(path.join(os.tmpdir(),'directory-pe-header-')));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
 const bytes=Buffer.alloc(132);bytes.write('MZ');bytes.writeUInt32LE(128,60);bytes.write('PE\0\0',128);
 const file=path.join(root,'soffice.bin');fs.writeFileSync(file,bytes);
 const {hasPEHeader}=require('../release-signing.cjs');assert.equal(hasPEHeader(file),true);assert.equal(require('../../packaging/verify_directory_release.cjs').isPE(file),true);
 bytes.writeUInt32LE(50000,60);fs.writeFileSync(file,bytes);assert.equal(hasPEHeader(file),false);
 if(process.platform==='win32'){
  bytes.writeUInt32LE(128,60);fs.writeFileSync(file,bytes);
  const source=fs.readFileSync(path.resolve(__dirname,'../sign-staged-binary.ps1'),'utf8'),helper=source.match(/^function Test-PortableExecutableFile[^\n]*\{\r?\n[\s\S]*?^\}/m);assert.ok(helper);
  const script=helper[0]+"\nif(-not(Test-PortableExecutableFile '"+file.replace(/'/g,"''")+"')){throw 'Valid header refused'}; 'pe-header-valid'";
  const child=spawnSync(String.raw`C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe`,['-NoProfile','-NonInteractive','-EncodedCommand',Buffer.from(script,'utf16le').toString('base64')],{encoding:'utf8',windowsHide:true,timeout:15000});assert.equal(child.status,0,child.stderr);assert.equal(child.stdout.trim(),'pe-header-valid');
 }
});
