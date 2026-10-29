'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const read=name=>fs.readFileSync(path.join(__dirname,'..',name),'utf8');
// Owner decision: updates are always on. The Ed25519-signed manifest and sha256/sha512 checks (trust.cjs, github-source.cjs)
// gate every install; the Windows certificate store and Authenticode chain are not consulted.
test('updates are checked unconditionally and the Authenticode chain checks are skipped',()=>{
 const main=read('main.cjs');
 assert.match(main,/catch\{enrollmentDeferred=true;\}\r?\n\s*if\(manual&&githubSource\)await githubSource\.refreshDiscovery\(\);\r?\n\s*await updater\.check\(\);/);
 assert.doesNotMatch(main,/publisher-trust|publisherTrusted|trustPublisher|trustUpdates|trust-updates|offerUpdateTrust|UPDATES_UNTRUSTED|updatesTrusted|Turn on updates/);
 // The installer publisher check is not disabled: updater.cjs uses its default, native-signature.cjs, which pins the
 // signer thumbprint to the signed manifest's publisherThumbprints (tests/publisher-thumbprint.test.cjs).
 assert.match(main,/autoUpdater:require\('electron-updater'\)\.autoUpdater,packaged:/);
 assert.doesNotMatch(main,/verifyNativePackage:/);
 assert.match(main,/^\s*require\('electron-updater'\)\.autoUpdater\.verifyUpdateCodeSignature=async\(\)=>null;/m);
 // updater.cjs nativeTrust refuses every update when electron-updater has no publisherName, which verifyUpdateCodeSignature:true provides.
 assert.match(read('builder.cjs'),/verifyUpdateCodeSignature:true/);
});

function checkerFixture(refresh=async()=>{}){
 const calls=[],context={portable:false,checkingUpdates:false,closing:false,githubConfig:null,accessGate:null,background:false,
  updater:{osShutdown:false,check:async()=>calls.push('check')},githubSource:{refreshDiscovery:async()=>{calls.push('refresh');await refresh();},discoverySummary:()=> 'Refresh deferred.'},
  updateGitHubStatus:value=>calls.push(value),updateStatus:value=>calls.push(value),drainActivity:async()=>{},accessOperation:async()=>{},enrollApproved:async()=>{}};
 const main=read('main.cjs'),body=main.slice(main.indexOf('async function checkUpdates('),main.indexOf('async function recoverPrevious('));
 vm.runInNewContext(body+'\nthis.check=checkUpdates;',context);return {context,calls};
}
test('manual menu check refreshes discovery before updater while automatic checks reuse normal cache policy',async()=>{
 const {context,calls}=checkerFixture();await context.check();assert.equal(calls.includes('refresh'),false);assert.ok(calls.includes('check'));
 calls.length=0;await context.check({manual:true});assert.ok(calls.indexOf('refresh')<calls.indexOf('check'));
 assert.match(read('main.cjs'),/label:'Check for updates',click:\(\)=>checkUpdates\(\{manual:true\}\)/);
});
test('failed manual refresh reports deferral and cannot be overwritten by cached no-update result',async()=>{
 const {context,calls}=checkerFixture(async()=>{throw new Error('network unavailable');});await context.check({manual:true});
 assert.equal(calls.includes('check'),false);assert.ok(calls.some(value=>/Update deferred.*Refresh deferred/.test(value)));
 assert.equal(context.checkingUpdates,false);
});
test('repeated manual clicks share the active check and do not start concurrent refreshes',async()=>{
 let release,entered;const started=new Promise(resolve=>{entered=resolve;});
 const {context,calls}=checkerFixture(async()=>{entered();await new Promise(resolve=>{release=resolve;});});
 const first=context.check({manual:true});await started;await context.check({manual:true});assert.equal(calls.filter(value=>value==='refresh').length,1);
 release();await first;assert.equal(calls.filter(value=>value==='check').length,1);
});
// Owner decision: the app never asks for a workspace folder or a district before launch. District switching lives inside the opened app.
test('the settings page has no folder, district or certificate-trust control and every script id exists',()=>{
 const html=read('setup.html'),script=read('setup.js'),preload=read('preload.cjs'),main=read('main.cjs');
 assert.doesNotMatch(html+script,/choose|district|directory|workspace|trustUpdates|Turn on updates/i);
 assert.doesNotMatch(preload,/chooseDirectory|trustUpdates|district:value|desktop:directory|desktop:trust-updates|desktop:district'/);
 assert.doesNotMatch(main,/desktop:directory|desktop:trust-updates|desktop:district'|openDirectory|createDirectory|Choose your local data directory/);
 for(const [, id] of script.matchAll(/byId\('([^']+)'\)/g))assert.ok(html.includes('id="'+id+'"'),'setup.html lacks #'+id);
 for(const id of ['launch','status'])assert.ok(html.includes('id="'+id+'"'),id);
 // The in-app district switcher (Terrier web UI) keeps its two runtime-only entry points.
 assert.match(preload,/districts:\(\)=>ipcRenderer\.invoke\('desktop:districts'\)/);assert.match(preload,/switchDistrict:value=>ipcRenderer\.invoke\('desktop:switch-district',value\)/);
 assert.match(main,/ipcMain\.handle\('desktop:switch-district',selectDistrict\)/);assert.match(main,/async function selectDistrict\(event,district\)\{\r?\n\s*runtimeOnly\(event\);/);
});
