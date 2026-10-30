'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os'),crypto=require('node:crypto');
const {DesktopUpdater}=require('../updater.cjs');
const {watchNetwork}=require('../lifecycle.cjs');
const {verifyEnvelope}=require('../trust.cjs');
const {activity}=require('../runtime.cjs');
const http=require('node:http');
const {dataStartupFailure}=require('../startup-failure.cjs');

function fixture(t){
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'desktop-lifecycle-'));
  t.after(()=>fs.rmSync(directory,{recursive:true,force:true}));
  const keys=crypto.generateKeyPairSync('ed25519');
  const enrollment={appId:'terrier',deviceToken:'fixture-only',publicKeys:{admin:keys.publicKey.export({format:'der',type:'spki'}).subarray(-32).toString('base64')}};
  const bytes=Buffer.from('Non-installable signed test fixture');
  let state={},offline=false,version='1.0.0',downloads=0,installs=0,nativeChecks=0,envelope,status=[],nativeValid=true;
  const sign=(release='1.1.0',sequence=1)=>{
    sequence+=1; // Sequence one is the already approved initial installer.
    const manifest={schemaVersion:1,appId:'terrier',version:release,sequence,platform:'win32',arch:'x64',minimumUpdaterVersion:'1.0.0',dataSchemaVersion:1,issuedAt:new Date().toISOString(),package:{name:'Terrier.exe',path:'/v1/packages/terrier/'+sequence+'/Terrier.exe',size:bytes.length,sha256:crypto.createHash('sha256').update(bytes).digest('hex'),sha512:crypto.createHash('sha512').update(bytes).digest('base64')}};
    const payload=Buffer.from(JSON.stringify(manifest));return {schemaVersion:1,keyId:'admin',payload:payload.toString('base64'),signature:crypto.sign(null,payload,keys.privateKey).toString('base64')};
  };
  envelope=sign();
  let seed=sign('1.0.0',0);
  fs.mkdirSync(path.join(directory,'updates','1'),{recursive:true});fs.writeFileSync(path.join(directory,'updates','1','Terrier.exe'),bytes);
  state={installed:{envelope:seed,version:'1.0.0',phase:'installed'},sequence:1,manifestHash:crypto.createHash('sha256').update(Buffer.from(seed.payload,'base64')).digest('hex'),acceptedVersion:'1.0.0'};
  const clients=[];
  function client(publisherName='Fixture Publisher',extra={}){
    let staged,feedManifest;
    const native={configOnDisk:{value:Promise.resolve({publisherName:'Fixture Publisher'})},setFeedURL(){},async checkForUpdates(){nativeChecks++;const active=state.recovery&&['staged','prepared'].includes(state.recovery.phase)?state.recovery.target.envelope:state.pending?.envelope||envelope;const m=feedManifest||JSON.parse(Buffer.from(active.payload,'base64'));return {updateInfo:{version:m.version,files:[m.package]}};},async downloadUpdate(){staged=path.join(directory,'native.exe');fs.writeFileSync(staged,bytes);return [staged];},quitAndInstall(){assert.ok(state.pending?.phase==='activating'||state.recovery?.phase==='activating','Transaction must be durable before native activation');this.quitAndInstallCalled=true;installs++;}};
    const updater=new DesktopUpdater({appId:'terrier',version,userData:directory,platform:'win32',arch:'x64',publisherName,packaged:true,autoUpdater:native,loadEnrollment:()=>enrollment,saveEnrollment(){},readState:()=>structuredClone(state),writeState:value=>{state=structuredClone(value);},onStatus:message=>status.push(message),verifyNativePackage:async()=>{if(!nativeValid)throw new Error('Native signature refused');},makeFeed:async manifest=>{feedManifest=manifest;return {url:'http://127.0.0.1/fixture/',close(){}};},request:async(p,url,options)=>{if(offline)throw new Error('offline');if(url.endsWith('/trust'))return {transitions:[]};if(url.includes('/recovery?'))return seed;if(url==='/v1/status'){assert.match(options.body.errorCode||'',/^[A-Z0-9_]*$/);return {};}return envelope;},download:async(p,token,m,target)=>{downloads++;fs.mkdirSync(target,{recursive:true});const destination=path.join(target,m.package.name);fs.writeFileSync(destination,bytes);return destination;},...extra});
    clients.push(updater);return updater;
  }
  t.after(()=>clients.forEach(c=>c.close()));
  return {client,sign,enrollment,get state(){return state;},set state(v){state=v;},set seed(v){seed=v;},set nativeValid(v){nativeValid=v;},set offline(v){offline=v;},set version(v){version=v;},set envelope(v){envelope=v;},get envelope(){return envelope;},get downloads(){return downloads;},get installs(){return installs;},get nativeChecks(){return nativeChecks;},get status(){return status;},directory};
}

function pending33Fixture(t,{legacy=false}={}){
 const f=fixture(t),old=f.sign('1.0.31',21),pending=f.sign('1.0.33',23);
 f.version='1.0.33';f.envelope=pending;f.seed=pending;
 const hash=envelope=>crypto.createHash('sha256').update(Buffer.from(envelope.payload,'base64')).digest('hex');
 f.state={installed:{envelope:old,version:'1.0.31',phase:'installed'},pending:{envelope:pending,version:'1.0.33',phase:'activating'},sequence:24,acceptedVersion:'1.0.33',manifestHash:hash(pending)};
 fs.mkdirSync(path.join(f.directory,'updates','24'),{recursive:true});fs.copyFileSync(path.join(f.directory,'updates','1','Terrier.exe'),path.join(f.directory,'updates','24','Terrier.exe'));
 const client=f.client('Fixture Publisher',legacy?{userData:path.join(f.directory,'moved'),legacyUserData:f.directory}:{});
 return {f,client,old,pending};
}
function deferredRecovery33Fixture(t){
 const {f}=pending33Fixture(t),target={version:'1.0.33',phase:'installed',envelope:f.sign('1.0.33',23)},from={version:'1.0.34',phase:'installed',envelope:f.sign('1.0.34',24)};
 const hash=envelope=>crypto.createHash('sha256').update(Buffer.from(envelope.payload,'base64')).digest('hex');
 f.state={installed:from,previous:target,pending:null,sequence:25,manifestHash:hash(from.envelope),acceptedVersion:'1.0.34',
  recovery:{target,manifestHash:hash(target.envelope),fromVersion:'1.0.34',phase:'prepared',requestedAt:new Date().toISOString()}};
 f.envelope=f.sign('1.0.35',25);const client=f.client();client.markApplicationDeferred(dataStartupFailure({reason:'timeout',retryableNetwork:true}));
 return {f,client,target,from};
}
test('forward and recovery downloads receive the actual verified signed manifest hash',async t=>{
 const f=fixture(t),first=f.client(),download=first.download,seen=[];
 first.download=(...args)=>{seen.push(args[4]);return download(...args);};await first.check();
 assert.equal(seen.length,1);assert.equal(seen[0].manifestHash,crypto.createHash('sha256').update(Buffer.from(f.envelope.payload,'base64')).digest('hex'));assert.equal(typeof seen[0].onProgress,'function');
 await first.activateAfterClose();f.version='1.1.0';const ready=f.client();ready.markApplicationReady();await ready.check();
 const recovery=f.client('Fixture Publisher',{userData:path.join(f.directory,'missing-new-cache')}),fallback=recovery.download;let received;
 recovery.download=(...args)=>{received=args[4];return fallback(...args);};await recovery.beginRecovery();
 assert.equal(received.manifestHash,crypto.createHash('sha256').update(Buffer.from(f.state.recovery.target.envelope.payload,'base64')).digest('hex'));assert.equal(typeof received.onProgress,'function');
});

test('native prefetch reports resumed signed bytes then hash/signature phases without progress changing state',async t=>{
 const f=fixture(t),client=f.client(),original=client.download;let late;
 client.download=async(...args)=>{
  const total=args[2].package.size,callback=args[4].onProgress,before=structuredClone(f.state);late=callback;
  callback({received:5,total,resumed:true});const count=f.status.length;
  callback({received:6,total,resumed:true});assert.equal(f.status.length,count,'rapid chunks are throttled');
  callback({received:7,total:total+1,resumed:true});callback({received:7,total,resumed:5});assert.equal(f.status.length,count,'untrusted counters are ignored');
  callback({received:total,total,resumed:true});assert.deepEqual(f.state,before);return original(...args);
 };
 await client.check();assert.ok(client.ready);assert.ok(f.status.some(message=>/resuming saved download/.test(message)));
 const hash=f.status.findIndex(message=>message==='Download complete. Checking update 1.1.0 hashes…'),native=f.status.findIndex(message=>message==='Verifying update 1.1.0 hashes and Windows signature…');
 assert.ok(hash>=0&&native>hash);const count=f.status.length;late({received:0,total:34,resumed:false});assert.equal(f.status.length,count,'settled transfer cannot overwrite final status');
});
test('a data-deferred current recovery33 stages35, survives35 restart, and confirms only real35 health',async t=>{
 const {f,client,target}=deferredRecovery33Fixture(t);await client.check();
 assert.equal(f.state.pending.version,'1.0.35');assert.equal(f.state.pending.phase,'prepared');assert.equal(f.state.sequence,26);assert.equal(f.state.recovery.phase,'prepared');
 assert.equal(client.lastConfirmedBaseline(f.enrollment,f.state).version,'1.0.33');assert.equal(await client.activateAfterClose(),true);
 f.version='1.0.35';const restarted=f.client();restarted.prepareRecovery=()=>assert.fail('Do not re-enter old recovery33');await restarted.check();
 assert.equal(f.state.pending.phase,'activating');assert.equal(f.state.recovery.phase,'prepared');assert.equal(restarted.applicationReady,undefined);assert.equal(f.state.installed.version,'1.0.34');
 restarted.markApplicationReady();await new Promise(queueMicrotask);await restarted.checkPromise;
 assert.equal(f.state.installed.version,'1.0.35');assert.deepEqual(f.state.previous,target);assert.equal(f.state.pending,null);assert.equal(f.state.recovery,null);
 assert.equal(f.state.supersededRecovery.phase,'superseded');assert.equal(f.state.supersededRecovery.previousPhase,'prepared');assert.equal(f.state.supersededRecovery.supersededBy.version,'1.0.35');assert.equal(f.state.sequence,26);assert.equal(f.state.suspendedVersions,undefined);
});
test('failed35 discovered from a data-deferred33 recovery can stage36 while retaining verified33',async t=>{
 const {f,client}=deferredRecovery33Fixture(t);await client.check();await client.activateAfterClose();f.version='1.0.35';
 const failed=f.client();await failed.markApplicationFailed();f.envelope=f.sign('1.0.36',26);await failed.check();
 assert.equal(f.state.pending.version,'1.0.36');assert.equal(f.state.pending.phase,'prepared');assert.equal(f.state.sequence,27);assert.deepEqual(f.state.suspendedVersions,['1.0.35']);
 assert.equal(f.state.recovery.phase,'prepared');assert.equal(failed.lastConfirmedBaseline(f.enrollment,f.state).version,'1.0.33');assert.equal(await failed.activateAfterClose(),true);
});
test('a second data outage in corrective35 cannot erase the original33 recovery binding or block36',async t=>{
 const {f,client,target}=deferredRecovery33Fixture(t);await client.check();await client.activateAfterClose();f.version='1.0.35';
 const current=f.client();current.markApplicationDeferred(dataStartupFailure({reason:'rate_limited',retryableNetwork:true,retryAfterMs:60000}));
 assert.equal(f.state.startupPendingVersion,'1.0.35');assert.equal(f.state.recovery.dataDeferredVersion,'1.0.33');
 assert.equal(f.state.recovery.dataDeferredManifestHash,f.state.recovery.manifestHash);
 f.envelope=f.sign('1.0.36',26);current.prepareRecovery=()=>assert.fail('Do not reenter original33 recovery');await current.check();
 assert.equal(f.state.pending.version,'1.0.36');assert.equal(f.state.pending.phase,'prepared');assert.equal(current.lastConfirmedBaseline(f.enrollment,f.state).version,'1.0.33');assert.equal(await current.activateAfterClose(),true);
 f.version='1.0.36';const ready=f.client();ready.prepareRecovery=()=>assert.fail('No old recovery during36 startup');await ready.check();assert.equal(f.state.installed.version,'1.0.34');
 ready.markApplicationReady();await new Promise(queueMicrotask);await ready.checkPromise;
 assert.equal(f.state.installed.version,'1.0.36');assert.deepEqual(f.state.previous,target);assert.equal(f.state.recovery,null);assert.equal(f.state.supersededRecovery.supersededBy.version,'1.0.36');assert.equal(f.state.sequence,27);assert.equal(f.state.suspendedVersions,undefined);
});
test('real33 recovery health can complete while preserving an already staged35 correction',async t=>{
 const {f,client}=deferredRecovery33Fixture(t);await client.check();client.markApplicationReady();await new Promise(queueMicrotask);await client.checkPromise;
 assert.equal(f.state.installed.version,'1.0.33');assert.equal(f.state.recovery.phase,'completed');assert.equal(f.state.pending.version,'1.0.35');assert.equal(f.state.pending.phase,'prepared');assert.equal(await client.activateAfterClose(),true);
});
test('deferred recovery rejects the original34 even without a suspended-version entry',async t=>{
 const {f,client,from}=deferredRecovery33Fixture(t);f.envelope=from.envelope;await client.check();
 assert.equal(f.state.pending,null);assert.equal(f.state.sequence,25);assert.equal(f.state.suspendedVersions,undefined);assert.equal(f.downloads,0);assert.equal(await client.activateAfterClose(),false);assert.match(f.status.at(-1),/newer than 1\.0\.34/);
});
for(const kind of ['unmarked','wrong-version','wrong-hash','tampered-target','failed'])test('recovery correction refuses '+kind+' data-deferral authorization',async t=>{
 const {f,client}=deferredRecovery33Fixture(t),state=f.state;
 if(kind==='unmarked')delete state.recovery.dataDeferredVersion;
 if(kind==='wrong-version')state.recovery.dataDeferredVersion='1.0.99';
 if(kind==='wrong-hash')state.recovery.dataDeferredManifestHash='f'.repeat(64);
 if(kind==='tampered-target')state.recovery.target.envelope.signature=Buffer.alloc(64).toString('base64');
 if(kind==='failed')state.recovery.phase='failed';f.state=state;
 await client.check();assert.equal(f.downloads,0);assert.equal(f.state.pending,null);assert.equal(f.state.sequence,25);
});
test('a forged superseding pending35 cannot bypass or complete the retained recovery33',async t=>{
 const {f,client}=deferredRecovery33Fixture(t);await client.check();const state=f.state;state.pending.envelope.signature=Buffer.alloc(64).toString('base64');f.state=state;f.version='1.0.35';
 const restarted=f.client();restarted.markApplicationReady();await new Promise(queueMicrotask);await restarted.checkPromise;
 assert.equal(f.state.installed.version,'1.0.34');assert.equal(f.state.recovery.phase,'prepared');assert.equal(f.state.supersededRecovery,undefined);assert.equal(await restarted.activateAfterClose(),false);
});
for(const reason of ['timeout','rate_limited','proxy','unreachable','integrity'])test('real updater pending33 survives '+reason+' data deferral and confirms only successful retry',async t=>{
 const {f,client}=pending33Fixture(t),before=structuredClone(f.state);
 const error=dataStartupFailure({reason,retryableNetwork:reason!=='integrity',retryAfterMs:60000});
 client.markApplicationDeferred(error);await client.check();
 assert.equal(client.applicationReady,false);assert.equal(f.state.pending.phase,'activating');assert.equal(f.state.startupPendingVersion,'1.0.33');
 assert.deepEqual(f.state.installed,before.installed);assert.equal(f.state.sequence,24);assert.equal(f.state.manifestHash,before.manifestHash);assert.equal(f.state.suspendedVersions,undefined);
 const restarted=f.client();await restarted.check();assert.equal(f.state.pending.phase,'activating');assert.equal(f.state.installed.version,'1.0.31');
 restarted.markApplicationReady();await new Promise(queueMicrotask);await restarted.checkPromise;
 assert.equal(f.state.pending,null);assert.equal(f.state.installed.version,'1.0.33');assert.equal(f.state.previous.version,'1.0.31');assert.equal(f.state.startupPendingVersion,null);assert.equal(f.state.suspendedVersions,undefined);
});
test('a data-deferred33 still discovers and stages a newer signed correction without losing its confirmed baseline',async t=>{
 const {f,client}=pending33Fixture(t),error=dataStartupFailure({reason:'timeout',retryableNetwork:true});client.markApplicationDeferred(error);
 f.envelope=f.sign('1.0.34',24);await client.check();
 assert.equal(f.state.pending.version,'1.0.34');assert.equal(f.state.pending.phase,'prepared');assert.equal(f.state.sequence,25);assert.equal(f.state.installed.version,'1.0.31');assert.equal(client.applicationReady,false);
 const ready=client.ready;assert.ok(ready);client.markApplicationDeferred(error);
 assert.equal(client.ready,ready);assert.equal(f.state.pending.version,'1.0.34');assert.equal(f.state.suspendedVersions,undefined);
});
test('legacy installer location cannot confirm a deferred pending33, even after restarting the updater',async t=>{
 const {f,client}=pending33Fixture(t,{legacy:true});client.markApplicationDeferred(dataStartupFailure({reason:'proxy',retryableNetwork:true}));
 const restarted=f.client('Fixture Publisher',{userData:path.join(f.directory,'moved'),legacyUserData:f.directory});await restarted.check();
 assert.equal(f.state.pending.phase,'activating');assert.equal(f.state.installed.version,'1.0.31');
 restarted.markApplicationReady();await new Promise(queueMicrotask);await restarted.checkPromise;assert.equal(f.state.installed.version,'1.0.33');assert.equal(f.state.pending,null);
});
test('a deferred outcome during installer verification cannot overwrite newer waiting state with stale readiness',async t=>{
 const {f}=pending33Fixture(t);let entered,release;const waiting=new Promise(resolve=>{entered=resolve;}),resume=new Promise(resolve=>{release=resolve;});
 const client=f.client('Fixture Publisher',{verifyNativePackage:async()=>{entered();await resume;}});client.markApplicationReady();await waiting;
 client.markApplicationDeferred(dataStartupFailure({reason:'rate_limited',retryableNetwork:true,retryAfterMs:60000}));release();await client.checkPromise;
 assert.equal(f.state.pending.phase,'activating');assert.equal(f.state.installed.version,'1.0.31');assert.equal(client.applicationReady,false);assert.equal(f.state.suspendedVersions,undefined);
});
test('an unbranded deferral cannot suppress an actual program failure',async t=>{
 const {f,client}=pending33Fixture(t);assert.throws(()=>client.markApplicationDeferred({code:'startup_deferred',retryable:true}),/native data-startup/);
 await client.markApplicationFailed();await client.check();assert.equal(f.state.pending.phase,'failed');assert.deepEqual(f.state.suspendedVersions,['1.0.33']);assert.equal(f.state.installed.version,'1.0.31');
});

test('download never arms quit hooks; explicit close persists transaction before native install',async t=>{
  const f=fixture(t),client=f.client();await client.check();
  assert.equal(client.autoUpdater.autoInstallOnAppQuit,false);assert.equal(f.installs,0);assert.equal(f.state.pending.phase,'prepared');
  assert.equal(await client.activateAfterClose(),true);assert.equal(f.installs,1);
});

test('first update records the running version from its signed manifest without downloading its installer, and enables first rollback',async t=>{
  const f=fixture(t);f.state={};fs.rmSync(path.join(f.directory,'updates','1'),{recursive:true});const first=f.client();await first.check();
  assert.equal(f.state.installed.version,'1.0.0');assert.equal(f.downloads,1);assert.equal(f.state.sequence,2);
  assert.equal(fs.existsSync(path.join(f.directory,'updates','1','Terrier.exe')),false,'the running version is never downloaded again');
  await first.activateAfterClose();f.version='1.1.0';const upgraded=f.client();upgraded.markApplicationReady();await upgraded.check();
  assert.equal(upgraded.recoveryCandidate().version,'1.0.0');assert.equal(f.state.previous.version,'1.0.0');assert.equal(f.downloads,1);
  // Only an actual rollback request fetches the older installer, then verifies it like any activation.
  assert.equal(await upgraded.beginRecovery(),'1.0.0');assert.equal(f.downloads,2);assert.equal(f.state.recovery.phase,'prepared');
  assert.equal(f.state.sequence,2);assert.equal(f.state.acceptedVersion,'1.1.0');
  assert.equal(await upgraded.activateAfterClose(),true);assert.equal(f.installs,2);assert.equal(f.state.recovery.phase,'activating');
});

test('an on-demand rollback installer failing its hash or publisher check is refused and never activates',async t=>{
  const f=fixture(t);f.state={};fs.rmSync(path.join(f.directory,'updates','1'),{recursive:true});const first=f.client();await first.check();await first.activateAfterClose();
  f.version='1.1.0';const tampered=f.client('Fixture Publisher',{download:async(p,token,m,target)=>{fs.mkdirSync(target,{recursive:true});fs.writeFileSync(path.join(target,m.package.name),'tampered');}});
  tampered.markApplicationReady();await tampered.check();
  await assert.rejects(()=>tampered.beginRecovery(),/Cached package/);assert.equal(f.state.recovery.phase,'failed');assert.equal(await tampered.activateAfterClose(),false);
  fs.rmSync(path.join(f.directory,'updates','1'),{recursive:true});f.nativeValid=false;const refused=f.client();refused.markApplicationReady();
  await assert.rejects(()=>refused.beginRecovery(),/Native signature refused/);assert.equal(await refused.activateAfterClose(),false);
  assert.equal(f.installs,1);assert.equal(f.state.sequence,2);assert.equal(f.state.acceptedVersion,'1.1.0');
});

test('missing initial recovery approval defers first update without activation',async t=>{
  const f=fixture(t);f.state={};f.seed=null;const first=f.client();await first.check();
  assert.equal(f.downloads,0);assert.equal(f.state.installed,undefined);assert.equal(await first.activateAfterClose(),false);
  assert.match(f.status.at(-1),/recovery installer/);
});

test('forged or wrong-version recovery seed cannot establish first-update trust',async t=>{
  const f=fixture(t);f.state={};f.seed={...f.sign('1.0.0',0),signature:Buffer.alloc(64).toString('base64')};const first=f.client();await first.check();
  assert.equal(f.state.installed,undefined);assert.equal(f.downloads,0);assert.equal(await first.activateAfterClose(),false);
  f.seed=f.sign('1.1.0',1);await first.check();assert.equal(f.state.installed,undefined);assert.equal(f.downloads,0);
});

test('native signature failure prevents package activation even though the signed baseline is recorded',async t=>{
  const f=fixture(t);f.state={};f.nativeValid=false;const first=f.client();await first.check();
  // The baseline is only the running version's signed manifest; no unsigned bytes can be staged from it.
  assert.equal(f.state.installed.version,'1.0.0');assert.equal(f.state.pending,null);assert.ok(f.state.verifyFailure);assert.equal(await first.activateAfterClose(),false);
  f.nativeValid=true;await first.check();f.nativeValid=false;assert.equal(await first.activateAfterClose(),false);assert.equal(f.installs,0);
});

test('older current-version recovery seed never lowers accepted release high-water',async t=>{
  const f=fixture(t);f.state={sequence:9,acceptedVersion:'9.0.0',manifestHash:'retained-high-water'};const first=f.client();await first.check();
  assert.equal(f.state.installed.version,'1.0.0');assert.equal(f.state.sequence,9);assert.equal(f.state.acceptedVersion,'9.0.0');assert.equal(f.state.manifestHash,'retained-high-water');assert.equal(await first.activateAfterClose(),false);
});

test('OS shutdown leaves staged update uninstalled and restores offline after next login',async t=>{
  const f=fixture(t),first=f.client();await first.check();first.suspendInstallation();
  assert.equal(await first.activateAfterClose(),false);assert.equal(f.installs,0);
  f.offline=true;const next=f.client();await next.check();
  assert.equal(f.downloads,1);assert.equal(next.ready.manifest.version,'1.1.0');
  assert.equal(await next.activateAfterClose(),true);assert.equal(f.installs,1);
});

test('altered staged bytes cannot be restored or installed offline',async t=>{
  const f=fixture(t),client=f.client();await client.check();
  fs.writeFileSync(path.join(f.directory,'updates','2','Terrier.exe'),'tampered');
  assert.equal(await client.activateAfterClose(),false);assert.equal(f.installs,0);
  f.offline=true;const next=f.client();await next.check();assert.equal(next.ready,null);assert.equal(await next.activateAfterClose(),false);
});

test('missing pinned native publisher fails before downloading or arming updates',async t=>{
  const f=fixture(t),client=f.client(null);await client.check();assert.equal(f.downloads,0);assert.equal(f.installs,0);assert.match(f.status.at(-1),/publisher/);
});

test('interrupted activation suspends repeated installation and retains recoverable metadata',async t=>{
  const f=fixture(t),client=f.client();await client.check();await client.activateAfterClose();
  const next=f.client();await next.check();assert.equal(f.state.pending.phase,'failed');assert.equal(f.installs,1);assert.equal(await next.activateAfterClose(),false);
  assert.ok(f.state.pending.envelope);assert.ok(fs.existsSync(path.join(f.directory,'updates','2','Terrier.exe')));
  f.envelope=f.sign('1.1.1',2);await next.check();assert.equal(f.state.pending.version,'1.1.1');assert.equal(f.state.pending.phase,'prepared');
});

function activationClient(f,extra={}){
  const client=f.client('Fixture Publisher',{activationTarget:version=>path.join(f.directory,'Terrier-'+version),...extra});
  client.autoUpdater.spawnLog=async()=>true;return client;
}
function activationReceipt(transaction,outcome='complete',code=0){
  const {receiptPath}=require('../installer-activation.cjs'),a=transaction.activation;
  const fields={schema:'1',app:a.appId,version:a.version,token:a.token,target:a.target,outcome,code:String(code)};
  fs.writeFileSync(receiptPath(a),Buffer.from('\ufeff[activation]\r\n'+Object.entries(fields).map(([key,value])=>key+'='+value).join('\r\n')+'\r\n','utf16le'));
}
test('old client relaunch while its exact installer runs does not fail or reinstall the update',async t=>{
  const f=fixture(t),first=activationClient(f);await first.check();await first.activateAfterClose();
  const {observeAttempt,MAX_AMBIGUOUS_MS}=require('../installer-activation.cjs'),started=Date.parse(f.state.pending.activatedAt);
  const nativeBefore=f.nativeChecks,downloads=f.downloads;
  const old=activationClient(f,{observeActivation:(attempt,context)=>observeAttempt(attempt,{...context,now:started+MAX_AMBIGUOUS_MS+1,
    processes:async()=>[{pid:4321,startedAt:new Date(started+1).toISOString(),installerPath:attempt.installerPath}]})});
  await old.check();assert.equal(f.state.pending.phase,'activating');assert.equal(f.state.pending.activation.process.pid,4321);
  assert.equal(f.state.installed.version,'1.0.0');assert.equal(f.state.sequence,2);assert.equal(f.downloads,downloads);
  assert.equal(f.nativeChecks,nativeBefore);assert.equal(f.installs,1);assert.match(f.status.at(-1),/still running.*longer than expected/);
});
test('completed installer followed by old-pin launch waits for verified healthy target startup',async t=>{
  const f=fixture(t),first=activationClient(f);await first.check();await first.activateAfterClose();activationReceipt(f.state.pending);
  let verified=0;
  const old=activationClient(f,{verifyNativePackage:async()=>{verified++;}});await old.check();
  assert.equal(verified,1,'unsigned completion is not used until the cached native installer is reverified');
  assert.equal(f.state.pending.phase,'activating');assert.equal(f.state.installed.version,'1.0.0');assert.match(f.status.at(-1),/finished; close this old copy/);
  await old.check();assert.equal(f.installs,1);assert.equal(f.state.pending.phase,'activating','repeated old-pin launches never classify completed installation as failure');
  f.version='1.1.0';const next=activationClient(f);await next.check();
  assert.equal(f.state.pending.phase,'activating');assert.match(f.status.at(-1),/awaits a successful local startup/);
  f.nativeValid=false;next.markApplicationReady();await next.check();
  assert.equal(f.state.pending.phase,'activating');assert.equal(f.state.installed.version,'1.0.0','receipt and healthy backend cannot bypass native verification');
  f.nativeValid=true;await next.check();assert.equal(f.state.pending,null);assert.equal(f.state.installed.version,'1.1.0');
});
test('abandoned or explicitly failed new attempts retain the original failed-release guard',async t=>{
  for(const outcome of ['abandoned','failed']){
    const f=fixture(t),first=activationClient(f);await first.check();await first.activateAfterClose();
    if(outcome==='failed')activationReceipt(f.state.pending,'failed',3);
    const {observeAttempt,MAX_AMBIGUOUS_MS}=require('../installer-activation.cjs');
    const old=activationClient(f,{observeActivation:(attempt,context)=>observeAttempt(attempt,{...context,now:Date.parse(attempt.startedAt)+MAX_AMBIGUOUS_MS+1,processes:async()=>[]})});
    await old.check();assert.equal(f.state.pending.phase,'failed');assert.equal(f.installs,1);assert.match(f.status.at(-1),/Failed release remains suspended/);
    assert.equal(await old.activateAfterClose(),false);assert.equal(f.state.installed.version,'1.0.0');
  }
});
test('a receipt never clears an existing failed target transaction',async t=>{
  const f=fixture(t),first=activationClient(f);await first.check();await first.activateAfterClose();activationReceipt(f.state.pending);
  f.state={...f.state,pending:{...f.state.pending,phase:'failed'}};f.version='1.1.0';
  const next=activationClient(f,{observeActivation:()=>assert.fail('failed state cannot consult a progress receipt')});next.markApplicationReady();await next.check();
  assert.equal(f.state.pending.phase,'failed');assert.equal(f.state.installed.version,'1.0.0');assert.ok(f.state.suspendedVersions.includes('1.1.0'));
});
test('stale observation cannot overwrite a failure recorded during its await',async t=>{
  const f=fixture(t),first=activationClient(f);await first.check();await first.activateAfterClose();
  const old=activationClient(f,{observeActivation:async()=>{f.state={...f.state,pending:{...f.state.pending,phase:'failed'}};return {status:'running',process:{pid:1,startedAt:new Date().toISOString()}};},
    verifyNativePackage:()=>assert.fail('changed transaction must not use stale liveness')});
  await old.check();assert.equal(f.state.pending.phase,'failed');assert.equal(f.state.pending.activation.process,undefined);
});

for(const offline of [false,true])test('healthy startup confirms its signed local installer automatically'+(offline?' without GitHub availability':''),async t=>{
  const f=fixture(t),first=f.client();await first.check();await first.activateAfterClose();
  f.version='1.1.0';f.offline=offline;let verified=0;
  const next=f.client('Fixture Publisher',{verifyNativePackage:async()=>{verified++;}});
  next.markApplicationReady();
  // Observe the automatically scheduled check; do not invoke a manual check.
  await new Promise(queueMicrotask);assert.ok(next.checkPromise);await next.checkPromise;
  assert.equal(verified,1);assert.equal(f.state.pending,null);assert.equal(f.state.installed.version,'1.1.0');
  assert.equal(f.state.installedVersion,'1.1.0');assert.equal(f.state.previous.version,'1.0.0');assert.equal(f.downloads,1);
  assert.match(f.status.at(-1),offline?/Update deferred: offline/:/Already current/);
});

test('readiness during a check queues confirmation behind that same serialized operation',async t=>{
  const f=fixture(t),first=f.client();await first.check();await first.activateAfterClose();f.version='1.1.0';
  let entered,release,held=false,verifications=0;
  const waiting=new Promise(resolve=>{entered=resolve;}),resume=new Promise(resolve=>{release=resolve;});
  const next=f.client('Fixture Publisher',{verifyNativePackage:async()=>{verifications++;}}),request=next.request;
  next.request=async(...args)=>{if(args[1].includes('/updates?')&&!held){held=true;entered();await resume;}return request(...args);};
  const checking=next.check();await waiting;next.markApplicationReady();next.markApplicationReady();
  assert.equal(next.check(),checking,'Concurrent checks must join the running operation');
  assert.equal(f.state.pending.phase,'activating');assert.equal(verifications,0);
  release();await checking;
  assert.equal(verifications,1);assert.equal(f.state.pending,null);assert.equal(f.state.installed.version,'1.1.0');
  assert.equal(f.state.previous.version,'1.0.0');assert.equal(next.busy,false);
});

test('startup failure during automatic native verification cannot confirm stale readiness',async t=>{
  const f=fixture(t),first=f.client();await first.check();await first.activateAfterClose();f.version='1.1.0';f.seed=f.envelope;
  let entered,release;const waiting=new Promise(resolve=>{entered=resolve;}),resume=new Promise(resolve=>{release=resolve;});
  const next=f.client('Fixture Publisher',{verifyNativePackage:async()=>{entered();await resume;}});
  next.markApplicationReady();await waiting;const checking=next.checkPromise;
  await next.markApplicationFailed();release();await checking;
  assert.equal(next.applicationReady,false);assert.equal(f.state.pending.phase,'failed');assert.equal(f.state.installed.version,'1.0.0');
  assert.notEqual(f.state.installedVersion,'1.1.0');assert.equal(f.downloads,1);
});

test('installed status requires backend readiness and preserves previous authorization without its installer',async t=>{
  const f=fixture(t),client=f.client();await client.check();await client.activateAfterClose();
  f.version='1.1.0';const next=f.client();await next.check();assert.equal(f.state.pending.version,'1.1.0');assert.equal(f.state.installed.version,'1.0.0');
  next.markApplicationReady();await next.check();assert.equal(f.state.pending,null);assert.equal(f.state.installed.version,'1.1.0');
  f.envelope=f.sign('1.2.0',2);await next.check();await next.activateAfterClose();
  f.version='1.2.0';const latest=f.client();latest.markApplicationReady();await latest.check();
  assert.equal(f.state.installed.version,'1.2.0');assert.equal(f.state.previous.version,'1.1.0');assert.ok(f.state.previous.envelope);assert.equal(fs.existsSync(path.join(f.directory,'updates','2','Terrier.exe')),false);
});

test('unconfirmed running update can discover and activate a corrective release without promoting its baseline',async t=>{
  const f=fixture(t),first=f.client();await first.check();await first.activateAfterClose();
  f.version='1.1.0';f.envelope=f.sign('1.2.0',2);const waiting=f.client();await waiting.check();
  assert.notEqual(waiting.applicationReady,true);assert.equal(f.state.installed.version,'1.0.0');
  assert.equal(f.state.startupPendingVersion,'1.1.0');assert.equal(f.state.pending.version,'1.2.0');
  assert.equal(f.state.pending.phase,'prepared');assert.equal(f.state.acceptedVersion,'1.2.0');
  assert.equal(waiting.recoveryCandidate().version,'1.0.0');
  assert.equal(await waiting.activateAfterClose(),true);assert.equal(f.installs,2);
  assert.equal(f.state.installed.version,'1.0.0');assert.equal(f.state.sequence,3);
});

test('corrective download failure and restart preserve the unconfirmed version and last confirmed baseline',async t=>{
  const f=fixture(t),first=f.client();await first.check();await first.activateAfterClose();
  f.version='1.1.0';f.envelope=f.sign('1.2.0',2);
  const failed=f.client('Fixture Publisher',{download:async()=>{throw new Error('transfer interrupted');}});await failed.check();
  assert.equal(f.state.pending,null);assert.equal(f.state.startupPendingVersion,'1.1.0');
  assert.equal(f.state.installed.version,'1.0.0');assert.equal(f.state.sequence,3);
  assert.match(f.status.at(-1),/Update deferred: transfer interrupted/);
  const restarted=f.client();await restarted.check();
  assert.equal(f.state.pending.phase,'prepared');assert.equal(f.state.pending.version,'1.2.0');
  assert.equal(f.state.installed.version,'1.0.0');assert.equal(f.state.startupPendingVersion,'1.1.0');
});

for(const invalid of ['missing','forged','mismatched'])test('corrective release requires the real last confirmed baseline: '+invalid,async t=>{
  const f=fixture(t),first=f.client();await first.check();await first.activateAfterClose();f.version='1.1.0';
  const old=f.state.installed;
  const baseline=invalid==='missing'?null:invalid==='forged'?{...old,envelope:{...old.envelope,signature:Buffer.alloc(64).toString('base64')}}:
    {...old,envelope:f.sign('1.0.1',0)};
  f.state={...f.state,installed:baseline};f.envelope=f.sign('1.2.0',2);const before=f.downloads;
  const waiting=f.client();await waiting.check();
  assert.equal(f.downloads,before);assert.equal(f.state.pending.version,'1.1.0');assert.equal(f.state.sequence,2);
  assert.equal(waiting.ready,null);assert.equal(await waiting.activateAfterClose(),false);assert.equal(f.installs,1);
});

test('corrective release still requires native signature verification',async t=>{
  const f=fixture(t),first=f.client();await first.check();await first.activateAfterClose();
  f.version='1.1.0';f.envelope=f.sign('1.2.0',2);f.nativeValid=false;const waiting=f.client();await waiting.check();
  assert.equal(waiting.ready,null);assert.equal(await waiting.activateAfterClose(),false);assert.equal(f.installs,1);
  assert.equal(f.state.installed.version,'1.0.0');assert.equal(f.state.startupPendingVersion,'1.1.0');
  assert.match(f.status.at(-1),/Native signature refused/);
});

test('genuine readiness promotes an unconfirmed version after a failed corrective download',async t=>{
  const f=fixture(t),first=f.client();await first.check();await first.activateAfterClose();
  f.version='1.1.0';f.envelope=f.sign('1.2.0',2);
  await f.client('Fixture Publisher',{download:async()=>{throw new Error('transfer interrupted');}}).check();
  f.seed=f.sign('1.1.0',1);const ready=f.client();ready.markApplicationReady();await ready.check();
  assert.equal(f.state.startupPendingVersion,null);assert.equal(f.state.installed.version,'1.1.0');
  assert.equal(f.state.previous.version,'1.0.0');assert.equal(f.state.pending.version,'1.2.0');
  assert.equal(f.state.pending.phase,'prepared');assert.equal(f.state.sequence,3);
});

test('a later ready corrective version clears the earlier unconfirmed marker and retains the good baseline',async t=>{
  const f=fixture(t),first=f.client();await first.check();await first.activateAfterClose();
  f.version='1.1.0';f.envelope=f.sign('1.2.0',2);const waiting=f.client();await waiting.check();await waiting.activateAfterClose();
  f.version='1.2.0';const corrected=f.client();corrected.markApplicationReady();await corrected.check();
  assert.equal(f.state.startupPendingVersion,null);assert.equal(f.state.pending,null);
  assert.equal(f.state.installed.version,'1.2.0');assert.equal(f.state.previous.version,'1.0.0');
});

test('readiness arriving during discovery preserves the pending identity until real baseline promotion',async t=>{
  const f=fixture(t),first=f.client();await first.check();await first.activateAfterClose();
  f.version='1.1.0';f.envelope=f.sign('1.2.0',2);const waiting=f.client(),request=waiting.request;
  waiting.request=async(...args)=>{if(args[1].includes('/updates?'))waiting.markApplicationReady();return request(...args);};
  await waiting.check();assert.equal(f.state.pending.phase,'prepared');assert.equal(f.state.startupPendingVersion,'1.1.0');
  assert.equal(f.state.installed.version,'1.0.0');f.seed=f.sign('1.1.0',1);await waiting.check();
  assert.equal(f.state.startupPendingVersion,null);assert.equal(f.state.installed.version,'1.1.0');assert.equal(f.state.previous.version,'1.0.0');
});

for(const during of ['recovery fetch','native trust'])test('readiness lost during '+during+' cannot promote the unconfirmed baseline',async t=>{
  const f=fixture(t),first=f.client();await first.check();await first.activateAfterClose();f.version='1.1.0';f.envelope=f.sign('1.2.0',2);
  await f.client('Fixture Publisher',{download:async()=>{throw new Error('transfer interrupted');}}).check();
  f.seed=f.sign('1.1.0',1);const ready=f.client();ready.markApplicationReady();
  if(during==='recovery fetch'){
    const request=ready.request;ready.request=async(...args)=>{if(args[1].includes('/recovery?'))await ready.markApplicationFailed();return request(...args);};
  }else{
    const nativeTrust=ready.nativeTrust.bind(ready);let once=true;
    ready.nativeTrust=async()=>{if(once){once=false;await ready.markApplicationFailed();}return nativeTrust();};
  }
  await ready.check();assert.equal(ready.applicationReady,false);assert.equal(f.state.installed.version,'1.0.0');
  assert.equal(f.state.startupPendingVersion,'1.1.0');assert.equal(f.state.pending.version,'1.2.0');
  assert.equal(f.state.pending.phase,'prepared');assert.equal(ready.recoveryCandidate().version,'1.0.0');
});

test('update status starts with a real check and replaces prior current status when the network fails',async t=>{
  const f=fixture(t);f.envelope=null;const client=f.client();await client.check();
  assert.equal(f.status[0],'Checking for updates…');assert.match(f.status.at(-1),/No newer signed update/);
  f.offline=true;await client.check();assert.equal(f.status.at(-2),'Checking for updates…');
  assert.match(f.status.at(-1),/^Update deferred: offline/);
});

test('higher release sequence cannot downgrade an already accepted version',t=>{
  const f=fixture(t);
  assert.throws(()=>verifyEnvelope(f.sign('1.1.0',3),f.enrollment,{appId:'terrier',platform:'win32',arch:'x64',version:'1.0.0'},{sequence:2,acceptedVersion:'1.2.0'}),/approved version downgrade/);
});

test('failed backend startup records a bounded failure and preserves previous recovery package',async t=>{
  const f=fixture(t),first=f.client();await first.check();await first.activateAfterClose();
  f.version='1.1.0';const installed=f.client();installed.markApplicationReady();await installed.check();
  f.envelope=f.sign('1.2.0',2);await installed.check();await installed.activateAfterClose();
  f.version='1.2.0';f.offline=true;const failed=f.client();await failed.markApplicationFailed();
  assert.equal(f.state.pending.phase,'failed');assert.equal(f.state.installed.version,'1.1.0');
  assert.equal(f.state.outbox.errorCode,'APP_STARTUP_FAILED');assert.equal(f.state.outbox.status,'failed');
  await failed.check();assert.equal(f.state.pending.phase,'failed');assert.equal(failed.ready,null);
  assert.equal(failed.recoveryCandidate().version,'1.1.0');
});

test('local recovery restores only retained authorized package and preserves anti-rollback high-water',async t=>{
  const f=fixture(t),first=f.client();await first.check();await first.activateAfterClose();
  f.version='1.1.0';const second=f.client();second.markApplicationReady();await second.check();
  f.envelope=f.sign('1.2.0',2);await second.check();await second.activateAfterClose();
  f.version='1.2.0';const third=f.client();third.markApplicationReady();await third.check();
  assert.equal(third.recoveryCandidate().version,'1.1.0');f.offline=true;
  assert.equal(await third.beginRecovery(),'1.1.0');assert.equal(f.state.sequence,3);assert.equal(f.state.acceptedVersion,'1.2.0');
  assert.equal(await third.activateAfterClose(),true);assert.equal(f.state.recovery.phase,'activating');
  f.version='1.1.0';const recovered=f.client();recovered.markApplicationReady();await recovered.check();
  assert.equal(f.state.recovery.phase,'completed');assert.equal(f.state.installed.version,'1.1.0');assert.equal(f.state.sequence,3);assert.equal(f.state.acceptedVersion,'1.2.0');assert.deepEqual(f.state.suspendedVersions,['1.2.0']);
  f.offline=false;await recovered.check();assert.equal(recovered.ready,null);assert.match(f.status.at(-1),/suspended/);
  f.envelope=f.sign('1.2.1',3);await recovered.check();assert.equal(f.state.pending.version,'1.2.1');
});

test('local recovery refuses tampered retained packages and installs nothing',async t=>{
  const f=fixture(t),first=f.client();await first.check();await first.activateAfterClose();
  f.version='1.1.0';const second=f.client();second.markApplicationReady();await second.check();
  f.envelope=f.sign('1.2.0',2);await second.check();await second.activateAfterClose();
  f.version='1.2.0';const third=f.client();third.markApplicationReady();await third.check();
  fs.mkdirSync(path.join(f.directory,'updates','2'),{recursive:true});
  fs.writeFileSync(path.join(f.directory,'updates','2','Terrier.exe'),'corrupt');
  // Offline, the corrupt copy is deleted and nothing can replace it: refused, nothing installs.
  const offline=f.client('Fixture Publisher',{download:async()=>{throw new Error('offline');}});
  await assert.rejects(()=>offline.beginRecovery(),/offline/);assert.equal(fs.existsSync(path.join(f.directory,'updates','2','Terrier.exe')),false);
  assert.equal(await offline.activateAfterClose(),false);assert.equal(f.installs,2);
  // Online, the fallback download is hash-checked against the signed manifest like any other.
  assert.equal(await third.beginRecovery(),'1.1.0');assert.equal(f.state.recovery.phase,'prepared');assert.equal(await third.activateAfterClose(),true);assert.equal(f.installs,3);
});

test('isolated test profile never downloads, stages or activates native installers',async t=>{
  const fresh=fixture(t);fresh.state={};const isolated=fresh.client('Fixture Publisher',{nativeInstallation:false});
  await assert.rejects(()=>isolated.nativeTrust(),/isolated test profile/);
  await isolated.check();
  assert.equal(fresh.downloads,0);assert.equal(fresh.nativeChecks,0);assert.equal(fresh.installs,0);assert.equal(fresh.state.sequence,undefined);assert.equal(fresh.state.pending,undefined);
  assert.match(fresh.status.at(-1),/isolated test profile/);assert.equal(await isolated.activateAfterClose(),false);
  // A previously prepared production transaction found in the same state cannot be activated or recovered either.
  const f=fixture(t);await f.client().check();assert.equal(f.state.pending.phase,'prepared');const checks=f.nativeChecks;
  const confined=f.client('Fixture Publisher',{nativeInstallation:false});await confined.check();
  assert.equal(confined.ready,null);assert.equal(await confined.activateAfterClose(),false);assert.equal(f.installs,0);assert.equal(f.nativeChecks,checks);
  await assert.rejects(()=>confined.beginRecovery());assert.equal(f.installs,0);
  // Production behavior is unchanged when the option is absent or true.
  const production=f.client('Fixture Publisher',{nativeInstallation:true});await production.check();assert.equal(await production.activateAfterClose(),true);assert.equal(f.installs,1);
});

test('network reconnect triggers one check without disclosing device data to discovery services',()=>{
  let online=false,calls=0,address='192.168.1.5';
  const watcher=watchNetwork({isOnline:()=>online,interfaces:()=>({WiFi:[{internal:false,family:'IPv4',address}]}),onReconnect:()=>calls++});
  try{watcher.poll();online=true;watcher.poll();watcher.poll();assert.equal(calls,1);address='192.168.2.5';watcher.poll();assert.equal(calls,2);online=false;watcher.poll();assert.equal(calls,2);}finally{watcher.close();}
});

test('activity signal requires matching app and typed boolean; unavailable is unknown',async()=>{
  let response={appId:'mentat',busy:true},code=200;
  const server=http.createServer((request,res)=>{assert.equal(request.headers['x-desktop-token'],'launch-secret');assert.equal(request.url,'/__desktop/activity');res.writeHead(code,{'Content-Type':'application/json'});res.end(JSON.stringify(response));});
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));const origin='http://127.0.0.1:'+server.address().port;
  try{assert.equal(await activity(origin,'launch-secret','mentat'),true);response={appId:'mentat',busy:false};assert.equal(await activity(origin,'launch-secret','mentat'),false);response={appId:'terrier',busy:false};assert.equal(await activity(origin,'launch-secret','mentat'),null);response={appId:'mentat',busy:'false'};assert.equal(await activity(origin,'launch-secret','mentat'),null);code=404;assert.equal(await activity(origin,'launch-secret','mentat'),null);}finally{await new Promise(resolve=>server.close(resolve));}
});

test('release failing native verification backs off, cannot wedge a corrected release, and keeps the high-water',async t=>{
  const f=fixture(t),bad=path.join(f.directory,'updates','2')+path.sep,failing=f.envelope,codes=[];
  const client=f.client('Fixture Publisher',{verifyNativePackage:async file=>{if(path.resolve(file).startsWith(bad))throw new Error('Native signature refused');}});
  const report=client.report.bind(client);client.report=(e,s,c)=>{codes.push(s+':'+c);return report(e,s,c);};
  await client.check();
  assert.equal(f.downloads,1);assert.equal(f.state.pending,null);assert.equal(client.ready,null);assert.match(f.status.at(-1),/Native signature refused/);assert.deepEqual(codes,['failed:VERIFY_FAILED']);
  assert.equal(f.state.verifyFailure.manifestHash,crypto.createHash('sha256').update(Buffer.from(failing.payload,'base64')).digest('hex'));
  // The signed high-water is recorded before download by design; a failed candidate keeps it.
  assert.equal(f.state.sequence,2);assert.equal(f.state.acceptedVersion,'1.1.0');assert.equal(await client.activateAfterClose(),false);
  // Inside the backoff window the same manifest is neither downloaded nor verified again.
  await client.check();await client.check();assert.equal(f.downloads,1);assert.match(f.status.at(-1),/retry after/);assert.equal(codes.length,1);
  // Older, equivocating or downgrading manifests stay refused.
  for(const [offer,reason] of [[f.sign('1.1.0',0),/Rollback/],[f.sign('1.1.1',1),/Rollback|equivocation/],[f.sign('1.0.9',3),/downgrade/]]){
    f.envelope=offer;await client.check();
    assert.match(f.status.at(-1),reason);assert.equal(f.state.sequence,2);assert.equal(f.state.acceptedVersion,'1.1.0');assert.equal(f.downloads,1);assert.equal(client.ready,null);
  }
  // After the window the same manifest is retried once (fresh download), fails again and backs off again.
  f.envelope=failing;f.state={...f.state,verifyFailure:{...f.state.verifyFailure,failedAt:Date.now()-6*60*60*1000-1}};
  await client.check();assert.equal(f.downloads,2);assert.equal(f.state.pending,null);assert.ok(Date.now()-f.state.verifyFailure.failedAt<60000);
  await client.check();assert.equal(f.downloads,2);
  // A corrected release with a higher sequence bypasses the backoff immediately.
  f.envelope=f.sign('1.1.1',2);await client.check();
  assert.equal(f.downloads,3);assert.equal(f.state.sequence,3);assert.equal(f.state.pending.version,'1.1.1');assert.equal(f.state.pending.phase,'prepared');
  assert.equal(await client.activateAfterClose(),true);assert.equal(f.installs,1);
});

test('restart reverification failure is reported and not overwritten by an empty update reply',async t=>{
  const f=fixture(t);let refuse=false;const bad=path.join(f.directory,'updates','2')+path.sep;
  const verifyNativePackage=async file=>{if(refuse&&path.resolve(file).startsWith(bad))throw new Error('Native signature refused');};
  await f.client('Fixture Publisher',{verifyNativePackage}).check();assert.equal(f.state.pending.phase,'prepared');
  refuse=true;f.envelope=null;const restarted=f.client('Fixture Publisher',{verifyNativePackage}),codes=[];
  const report=restarted.report.bind(restarted);restarted.report=(e,s,c)=>{codes.push(s+':'+c);return report(e,s,c);};
  await restarted.check();
  assert.match(f.status.at(-1),/Staged update 1.1.0 .*Native signature refused/);assert.deepEqual(codes,['failed:VERIFY_FAILED']);
  assert.equal(f.state.pending,null);assert.equal(restarted.ready,null);assert.equal(await restarted.activateAfterClose(),false);
});

test('download integrity failure records the high-water but a corrected release still installs',async t=>{
  const f=fixture(t);let fail=true;
  const client=f.client('Fixture Publisher',{download:async(p,token,m,target)=>{if(fail){fail=false;throw new Error('Downloaded package integrity failed');}fs.mkdirSync(target,{recursive:true});const destination=path.join(target,m.package.name);fs.writeFileSync(destination,Buffer.from('Non-installable signed test fixture'));return destination;}});
  await client.check();
  assert.equal(f.state.sequence,2);assert.equal(f.state.pending,null);assert.match(f.status.at(-1),/integrity failed/);
  f.envelope=f.sign('1.1.0',0);await client.check();assert.match(f.status.at(-1),/Rollback/);assert.equal(f.state.sequence,2);
  f.envelope=f.sign('1.1.1',2);await client.check();
  assert.equal(f.state.sequence,3);assert.equal(f.state.pending.phase,'prepared');assert.equal(await client.activateAfterClose(),true);
});

test('failed rollback preparation is marked failed, never activates, and stops blocking updates',async t=>{
  const f=fixture(t),first=f.client();await first.check();await first.activateAfterClose();
  f.version='1.1.0';const second=f.client();second.markApplicationReady();await second.check();
  f.envelope=f.sign('1.2.0',2);await second.check();await second.activateAfterClose();
  f.version='1.2.0';const third=f.client();third.markApplicationReady();await third.check();
  // Rollback staged, then its retained installer fails reverification after a restart.
  assert.equal(await third.beginRecovery(),'1.1.0');fs.writeFileSync(path.join(f.directory,'updates','2','Terrier.exe'),'corrupt');
  const restarted=f.client();restarted.markApplicationReady();f.offline=true;await restarted.check();
  assert.equal(f.state.recovery.phase,'failed');assert.equal(restarted.ready,null);assert.equal(await restarted.activateAfterClose(),false);
  // The failed installer was deleted, so the next attempt fetches a fresh one (no manual cleanup).
  assert.equal(fs.existsSync(path.join(f.directory,'updates','2','Terrier.exe')),false);const original=restarted.download;
  // A manual retry whose fresh download still fails verification is refused, deleted again and marked failed.
  restarted.download=async(p,token,m,target)=>{fs.mkdirSync(target,{recursive:true});fs.writeFileSync(path.join(target,m.package.name),'corrupt');};
  await assert.rejects(()=>restarted.beginRecovery(),/Cached package/);assert.equal(f.state.recovery.phase,'failed');assert.equal(fs.existsSync(path.join(f.directory,'updates','2','Terrier.exe')),false);
  restarted.download=original;
  // Normal updates resume; the newer valid release becomes ready and the failed rollback never activates.
  f.offline=false;f.envelope=f.sign('1.2.1',3);await restarted.check();
  assert.equal(f.state.pending.version,'1.2.1');assert.equal(f.state.pending.phase,'prepared');assert.equal(restarted.ready.recovery,false);
  assert.equal(await restarted.activateAfterClose(),true);assert.equal(f.state.pending.phase,'activating');assert.equal(f.state.recovery.phase,'failed');assert.equal(f.installs,3);
});

test('broken current-version baseline is not blamed on the staged release and starts no backoff',async t=>{
  const f=fixture(t);await f.client().check();assert.equal(f.state.pending.phase,'prepared');
  const baseline=f.state.installed;f.state={...f.state,installed:{...baseline,envelope:{...baseline.envelope,signature:Buffer.alloc(64).toString('base64')}}};
  const restarted=f.client();await restarted.check();
  assert.equal(f.state.verifyFailure,undefined);assert.equal(f.state.pending.version,'1.1.0');assert.equal(restarted.ready,null);assert.equal(await restarted.activateAfterClose(),false);
  f.state={...f.state,installed:baseline};await restarted.check();
  assert.equal(f.downloads,1);assert.equal(f.state.verifyFailure,undefined);assert.equal(await restarted.activateAfterClose(),true);
});

test('signature tool failure without a verdict keeps the staged release and retries locally without backoff',async t=>{
  const f=fixture(t),bad=path.join(f.directory,'updates','2')+path.sep,codes=[];let unavailable=true;
  const client=f.client('Fixture Publisher',{verifyNativePackage:async file=>{if(unavailable&&path.resolve(file).startsWith(bad))throw Object.assign(new Error('Windows package signature verification failed.'),{code:'SIGNATURE_CHECK_UNAVAILABLE'});}});
  const report=client.report.bind(client);client.report=(e,s,c)=>{codes.push(s+':'+c);return report(e,s,c);};
  await client.check();
  assert.equal(f.state.verifyFailure,undefined);assert.equal(f.state.pending.phase,'staged');assert.equal(f.downloads,1);assert.deepEqual(codes,['deferred:SIGNATURE_CHECK_UNAVAILABLE']);
  await client.check();assert.equal(f.downloads,1);assert.equal(f.state.verifyFailure,undefined);assert.match(f.status.at(-1),/not prepared/);
  assert.deepEqual(codes,['deferred:SIGNATURE_CHECK_UNAVAILABLE']); // Reported once per staged manifest.
  unavailable=false;await client.check();assert.equal(f.downloads,1);assert.equal(await client.activateAfterClose(),true);assert.deepEqual(codes,['deferred:SIGNATURE_CHECK_UNAVAILABLE']);
});

test('malformed backoff timestamp is ignored without throwing',async t=>{
  for(const failedAt of [String(Date.now()),[Date.now()]]){
    const f=fixture(t),client=f.client();
    f.state={...f.state,verifyFailure:{manifestHash:crypto.createHash('sha256').update(Buffer.from(f.envelope.payload,'base64')).digest('hex'),failedAt}};
    await client.check();
    assert.equal(f.downloads,1);assert.equal(f.state.pending.phase,'prepared');assert.doesNotMatch(f.status.join(' '),/Invalid time|retry after/);
  }
});

test('install-on-close refuses activation when the current-version baseline fails at close time',async t=>{
  const f=fixture(t),client=f.client();await client.check();assert.equal(f.state.pending.phase,'prepared');
  f.state={...f.state,installed:{...f.state.installed,envelope:f.sign('1.0.1',0)}};
  assert.equal(await client.activateAfterClose(),false);assert.equal(f.installs,0);assert.equal(f.state.pending.phase,'prepared');assert.match(f.status.at(-1),/activation refused/);
});

test('a verified update pending from an earlier session installs silently at the next start, before anything else',async t=>{
  const f=fixture(t),calls=[];
  const watch=client=>{const original=client.autoUpdater.quitAndInstall;client.autoUpdater.quitAndInstall=function(silent,run){calls.push([silent,run,this.autoRunAppAfterInstall]);return original.call(this);};return client;};
  const first=f.client();await first.check();first.suspendInstallation();assert.equal(await first.activateAfterClose(),false);
  // Nothing to install, or an OS shutdown in progress: a normal start continues.
  const shutdown=watch(f.client());shutdown.suspendInstallation();assert.equal(await shutdown.activateAtLaunch(true),false);
  f.offline=true;const next=watch(f.client());
  assert.equal(await next.activateAtLaunch(true),true);assert.deepEqual(calls,[[true,true,true]]);assert.equal(f.installs,1);assert.equal(f.state.pending.phase,'activating');
  // The interrupted install is never retried at launch; a version awaiting startup is not reinstalled.
  assert.equal(await watch(f.client()).activateAtLaunch(true),false);f.version='1.1.0';
  f.state={...f.state,pending:{...f.state.pending,phase:'prepared'}};assert.equal(await watch(f.client()).activateAtLaunch(true),false);assert.equal(f.installs,1);
  // A normal close installs silently without relaunching.
  const g=fixture(t),closing=watch(g.client());await closing.check();assert.equal(await closing.activateAfterClose(),true);assert.deepEqual(calls.at(-1),[true,false,false]);
});

test('launch install keeps every check: tampered, isolated, unpinned or unstartable installs never activate',async t=>{
  const f=fixture(t);await f.client().check();assert.equal(f.state.pending.phase,'prepared');
  assert.equal(await f.client('Fixture Publisher',{nativeInstallation:false}).activateAtLaunch(true),false);
  assert.equal(await f.client(null).activateAtLaunch(true),false);
  const failed=f.client();failed.autoUpdater.quitAndInstall=function(){this.quitAndInstallCalled=false;};
  assert.equal(await failed.activateAtLaunch(true),false,'an installer that could not start lets the app start normally');
  const g=fixture(t);await g.client().check();fs.writeFileSync(path.join(g.directory,'updates','2','Terrier.exe'),'tampered');
  assert.equal(await g.client().activateAtLaunch(false),false);assert.equal(g.installs,0);assert.equal(g.state.pending,null);assert.equal(f.installs,0);
});

test('a requested rollback beats a pending update at launch, and starts by parking that update',async t=>{
  const f=fixture(t),first=f.client();await first.check();await first.activateAfterClose();
  f.version='1.1.0';const second=f.client();second.markApplicationReady();await second.check();
  f.envelope=f.sign('1.2.0',2);await second.check();assert.equal(f.state.pending.version,'1.2.0');assert.equal(f.state.pending.phase,'prepared');
  const staged=f.state.pending,installs=f.installs;
  assert.equal(await second.beginRecovery(),'1.0.0');assert.equal(f.state.pending,null,'the rolled-back-over update must not resurface');assert.equal(f.state.recovery.phase,'prepared');
  // Even if a pending update is somehow still recorded, a prepared rollback wins at launch.
  for(const phase of ['staged','prepared','activating']){
    f.state={...f.state,pending:staged,recovery:{...f.state.recovery,phase}};
    assert.equal(await f.client().activateAtLaunch(true),false);assert.equal(f.installs,installs);
  }
});

test('an unconfirmed update can roll back offline from the retained first installer',async t=>{
  const f=fixture(t),bytes=fs.readFileSync(path.join(f.directory,'updates','1','Terrier.exe'));
  f.state={};fs.rmSync(path.join(f.directory,'updates','1'),{recursive:true});
  const baselineRoot=path.join(f.directory,'baseline'),offline=async()=>{throw new Error('offline');};
  // installer.nsh put the running installer here under whatever name it had.
  fs.mkdirSync(path.join(baselineRoot,'1.0.0'),{recursive:true});fs.writeFileSync(path.join(baselineRoot,'1.0.0','Terrier Setup (1).exe'),bytes);
  const first=f.client('Fixture Publisher',{baselineRoot});await first.check();await first.activateAfterClose();
  f.version='1.1.0';const second=f.client('Fixture Publisher',{baselineRoot});await second.check();
  assert.equal(f.state.installed.version,'1.0.0');assert.ok(f.state.installed.envelope,'the signed manifest of the baseline is kept locally');
  const downloads=f.downloads;f.offline=true;second.download=offline;
  assert.equal(await second.beginRecovery(),'1.0.0');assert.equal(f.downloads,downloads);assert.equal(f.state.recovery.phase,'prepared');
  assert.equal(fs.readdirSync(path.join(baselineRoot,'1.0.0')).length,1,'the baseline is copied, not moved: it stays until the rollback completed');
  assert.equal(await second.activateAfterClose(),true);
  f.version='1.0.0';const restored=f.client('Fixture Publisher',{baselineRoot});restored.markApplicationReady();await restored.check();
  assert.equal(f.state.recovery.phase,'completed');assert.equal(fs.existsSync(path.join(baselineRoot,'1.0.0')),false,'removed once the target version is confirmed running');
  // A corrupt baseline copy fails the hash check, is deleted, and only then is the installer fetched.
  const g=fixture(t);g.state={};fs.rmSync(path.join(g.directory,'updates','1'),{recursive:true});
  const root=path.join(g.directory,'baseline');fs.mkdirSync(path.join(root,'1.0.0'),{recursive:true});fs.writeFileSync(path.join(root,'1.0.0','Terrier.exe'),'corrupt');
  const a=g.client('Fixture Publisher',{baselineRoot:root});await a.check();await a.activateAfterClose();
  g.version='1.1.0';const b=g.client('Fixture Publisher',{baselineRoot:root});b.markApplicationReady();await b.check();const before=g.downloads;
  assert.equal(await b.beginRecovery(),'1.0.0');assert.equal(g.downloads,before+1);assert.equal(fs.existsSync(path.join(root,'1.0.0','Terrier.exe')),false);
});

test('a healthy update removes previous installers, retains recovery metadata, and downloads rollback on demand',async t=>{
  const f=fixture(t),baselineRoot=path.join(f.directory,'baseline'),mk=()=>f.client('Fixture Publisher',{baselineRoot});
  fs.mkdirSync(path.join(baselineRoot,'1.0.0'),{recursive:true});fs.writeFileSync(path.join(baselineRoot,'1.0.0','Terrier.exe'),'old');
  const has=n=>fs.existsSync(path.join(f.directory,'updates',String(n)));
  const first=mk();await first.check();await first.activateAfterClose();
  f.version='1.1.0';const second=mk();second.markApplicationReady();await second.check();
  assert.deepEqual([has(1),has(2)],[false,true]);assert.equal(fs.existsSync(path.join(baselineRoot,'1.0.0')),false);
  assert.equal(f.state.previous.version,'1.0.0');assert.ok(f.state.previous.envelope);
  f.envelope=f.sign('1.2.0',2);await second.check();await second.activateAfterClose();
  assert.deepEqual([has(1),has(2),has(3)],[false,true,true],'the installed version is kept until its replacement starts successfully');
  f.version='1.2.0';const third=mk();third.markApplicationReady();await third.check();
  assert.deepEqual([has(1),has(2),has(3)],[false,false,true]);assert.equal(fs.existsSync(path.join(baselineRoot,'1.0.0')),false);
  const before=f.downloads;assert.equal(await third.beginRecovery(),'1.1.0');assert.equal(f.downloads,before+1);
  assert.equal(has(2),true);third.pruneBaselines();assert.equal(has(2),true,'an active recovery download remains protected');
});

test('launch install stops waiting after repeated "no verdict" and reads the relaunch choice after preparation',async t=>{
  const f=fixture(t);await f.client().check();let unavailable=true;
  const mk=()=>f.client('Fixture Publisher',{verifyNativePackage:async()=>{if(unavailable)throw Object.assign(new Error('x'),{code:'SIGNATURE_CHECK_UNAVAILABLE'});}});
  for(let i=0;i<3;i++)assert.equal(await mk().activateAtLaunch(true),false);
  assert.equal(f.state.launchUnavailable.count,3);unavailable=false;
  assert.equal(await mk().activateAtLaunch(true),false,'launch install is skipped; install-on-close remains');assert.equal(f.installs,0);
  // Strikes are not reset by a background check; the update still installs when the app closes.
  const checker=mk();await checker.check();assert.equal(f.state.launchUnavailable.count,3);assert.equal(await checker.activateAfterClose(),true);assert.equal(f.installs,1);
  // A launch requested while the update is being prepared makes the app relaunch even after a background start.
  const g=fixture(t);await g.client().check();let requested=false;
  const late=g.client('Fixture Publisher',{verifyNativePackage:async()=>{requested=true;}});
  assert.equal(await late.activateAtLaunch(()=>requested),true);assert.equal(late.autoUpdater.autoRunAppAfterInstall,true);
});

test('an installer spawn failure after quitAndInstall returned is recorded as failed and never retried at launch',async t=>{
  // electron-updater 6.8.9: doInstall returns true right after the async spawn, so activation reports success and the app quits.
  const f=fixture(t);await f.client().check();const c=f.client();
  assert.equal(await c.activateAtLaunch(true),true);assert.equal(c.autoUpdater.quitAndInstallCalled,true);
  await c.nativeFailure();assert.equal(f.state.pending.phase,'failed');assert.equal(f.client().launchCandidate(),null);
  // The process exited before the error event: the next start marks the interrupted transaction failed.
  const g=fixture(t);await g.client().check();assert.equal(await g.client().activateAtLaunch(true),true);assert.equal(g.state.pending.phase,'activating');
  assert.equal(g.client().launchCandidate(),null);await g.client().check();assert.equal(g.state.pending.phase,'failed');
});

test('a rollback copy is deleted only when its own bytes fail the hash check; an untrusted signature or tool error keeps it',async t=>{
  const f=fixture(t),bytes=fs.readFileSync(path.join(f.directory,'updates','1','Terrier.exe'));
  f.state={};fs.rmSync(path.join(f.directory,'updates','1'),{recursive:true});
  const baselineRoot=path.join(f.directory,'baseline'),baseline=path.join(baselineRoot,'1.0.0','Terrier.exe'),retained=path.join(f.directory,'updates','1','Terrier.exe');
  fs.mkdirSync(path.dirname(baseline),{recursive:true});fs.writeFileSync(baseline,bytes);
  const mk=extra=>f.client('Fixture Publisher',{baselineRoot,...extra});
  const first=mk();await first.check();await first.activateAfterClose();f.version='1.1.0';const second=mk();await second.check(); // Unconfirmed startup retains offline recovery copies.
  // Authenticode refusal (untrusted certificate): the verified copy and the baseline both stay.
  f.nativeValid=false;await assert.rejects(()=>mk().beginRecovery(),/Native signature refused/);
  assert.ok(fs.existsSync(retained),'cached copy kept');assert.ok(fs.existsSync(baseline),'baseline kept');assert.equal(f.state.recovery.phase,'failed');
  // No verdict from the signature tool: also kept.
  await assert.rejects(()=>mk({verifyNativePackage:async()=>{throw Object.assign(new Error('x'),{code:'SIGNATURE_CHECK_UNAVAILABLE'});}}).beginRecovery(),/x/);
  assert.ok(fs.existsSync(retained));assert.ok(fs.existsSync(baseline));
  // A native-updater/feed error: kept.
  const broken=mk();broken.autoUpdater.checkForUpdates=async()=>{throw new Error('feed down');};f.nativeValid=true;
  await assert.rejects(()=>broken.beginRecovery(),/feed down/);assert.ok(fs.existsSync(retained));
  // A trust configuration error (no pinned publisher) is not the installer's fault either.
  await assert.rejects(()=>f.client(null,{baselineRoot}).beginRecovery());assert.ok(fs.existsSync(retained));
  // Once it verifies, the rollback works from that same copy without any download.
  const downloads=f.downloads;assert.equal(await mk().beginRecovery(),'1.0.0');assert.equal(f.downloads,downloads);
  // Corrupt bytes: now it is deleted, together with its baseline source.
  fs.writeFileSync(retained,'corrupt');fs.writeFileSync(baseline,'corrupt');
  assert.equal(await mk().beginRecovery(),'1.0.0');assert.equal(f.downloads,downloads+1,'fetched fresh after the corrupt copy was removed');assert.equal(fs.existsSync(baseline),false);
});

test('a transient read error (EBUSY) on a rollback copy is not an integrity failure: neither the copy nor its baseline source is deleted',async t=>{
  const f=fixture(t),bytes=fs.readFileSync(path.join(f.directory,'updates','1','Terrier.exe'));
  f.state={};fs.rmSync(path.join(f.directory,'updates','1'),{recursive:true});
  const baselineRoot=path.join(f.directory,'baseline'),baseline=path.join(baselineRoot,'1.0.0','Terrier.exe'),retained=path.join(f.directory,'updates','1','Terrier.exe');
  fs.mkdirSync(path.dirname(baseline),{recursive:true});fs.writeFileSync(baseline,bytes);
  const mk=extra=>f.client('Fixture Publisher',{baselineRoot,...extra});
  const first=mk();await first.check();await first.activateAfterClose();f.version='1.1.0';const second=mk();await second.check(); // Unconfirmed startup retains offline recovery copies.
  // Antivirus holds the freshly copied installer open: reading it fails with EBUSY, which says nothing about its bytes.
  const read=fs.createReadStream;fs.createReadStream=(file,...rest)=>{if(String(file).endsWith('Terrier.exe'))throw Object.assign(new Error('EBUSY: resource busy or locked'),{code:'EBUSY'});return read.call(fs,file,...rest);};
  try{await assert.rejects(()=>mk({download:async()=>{throw new Error('offline');}}).beginRecovery(),/offline/);}finally{fs.createReadStream=read;}
  assert.ok(fs.existsSync(retained),'the adopted rollback copy is kept');assert.ok(fs.existsSync(baseline),'the baseline source is kept');
  // The lock is gone: the rollback now works offline from those same copies.
  const downloads=f.downloads;assert.equal(await mk().beginRecovery(),'1.0.0');assert.equal(f.downloads,downloads);
});

test('a corrupt copy locked against delete and replace stops recovery before any download; once unlocked, recovery downloads',async t=>{
  const f=fixture(t),bytes=fs.readFileSync(path.join(f.directory,'updates','1','Terrier.exe'));
  f.state={};fs.rmSync(path.join(f.directory,'updates','1'),{recursive:true});
  const baselineRoot=path.join(f.directory,'baseline'),baseline=path.join(baselineRoot,'1.0.0','Terrier.exe'),retained=path.join(f.directory,'updates','1','Terrier.exe');
  fs.mkdirSync(path.dirname(baseline),{recursive:true});fs.writeFileSync(baseline,bytes);
  const mk=extra=>f.client('Fixture Publisher',{baselineRoot,...extra});
  const first=mk();await first.check();await first.activateAfterClose();f.version='1.1.0';const second=mk();await second.check(); // Unconfirmed startup retains offline recovery copies.
  fs.mkdirSync(path.dirname(retained),{recursive:true});fs.writeFileSync(retained,'corrupt');fs.writeFileSync(baseline,'corrupt');
  // Another program holds the corrupt retained copy open with read sharing only (as Windows does for a running .exe):
  // it reads fine, but deleting it, renaming onto it or overwriting it fails with EPERM.
  const original={rmSync:fs.rmSync,rm:fs.promises.rm,renameSync:fs.renameSync,writeFileSync:fs.writeFileSync},locked=file=>path.resolve(String(file))===retained;
  const refuse=()=>Object.assign(new Error('EPERM: operation not permitted'),{code:'EPERM'});
  fs.rmSync=(file,...rest)=>{if(locked(file))throw refuse();return original.rmSync.call(fs,file,...rest);};
  fs.promises.rm=async(file,...rest)=>{if(locked(file))throw refuse();return original.rm.call(fs.promises,file,...rest);};
  fs.renameSync=(from,to)=>{if(locked(to))throw refuse();return original.renameSync.call(fs,from,to);};
  fs.writeFileSync=(file,...rest)=>{if(locked(file))throw refuse();return original.writeFileSync.call(fs,file,...rest);};
  const downloads=f.downloads;
  try{await assert.rejects(()=>mk().beginRecovery(),/in use by another program/);}finally{Object.assign(fs,{rmSync:original.rmSync,renameSync:original.renameSync,writeFileSync:original.writeFileSync});fs.promises.rm=original.rm;}
  assert.equal(f.downloads,downloads,'no download was spent on a path that could not be replaced');assert.ok(fs.existsSync(retained));
  // The lock is gone: the corrupt copies are removed and recovery downloads a fresh installer.
  assert.equal(await mk().beginRecovery(),'1.0.0');assert.equal(f.downloads,downloads+1);assert.equal(fs.existsSync(baseline),false);
});

test('launch strikes count every failure, including activation-time no-verdict and pre-try failures, and reset only after dispatch',async t=>{
  // Failure before the try in preparePending (no pinned publisher): three strikes, then no more offers.
  const f=fixture(t);await f.client().check();
  for(let i=0;i<3;i++){assert.ok(f.client(null).launchCandidate()!==null||i===3);assert.equal(await f.client(null).activateAtLaunch(true),false);}
  assert.equal(f.state.launchUnavailable.count,3);assert.equal(f.client().launchCandidate(),null,'no more installing window at launch');
  // No verdict only at activation time (preparation passes, the activation re-check does not).
  const g=fixture(t);await g.client().check();
  const flaky=()=>{let calls=0;return g.client('Fixture Publisher',{verifyNativePackage:async()=>{if(++calls>2)throw Object.assign(new Error('x'),{code:'SIGNATURE_CHECK_UNAVAILABLE'});}});};
  for(let i=0;i<3;i++){assert.notEqual(g.client().launchCandidate(),null);assert.equal(await flaky().activateAtLaunch(true),false);}
  assert.equal(g.state.launchUnavailable.count,3);assert.equal(g.client().launchCandidate(),null);assert.equal(g.installs,0);
  // A dispatched install resets the strikes.
  const h=fixture(t);await h.client().check();await h.client(null).activateAtLaunch(true);assert.equal(h.state.launchUnavailable.count,1);
  assert.equal(await h.client().activateAtLaunch(true),true);assert.equal(h.state.launchUnavailable,null);
});

test('moving the updater file root keeps the anti-rollback high-water and installed record; an uncached staged installer is fetched again once',async t=>{
  const f=fixture(t);await f.client().check();assert.equal(f.state.pending.phase,'prepared');assert.equal(f.downloads,1);
  const before=structuredClone(f.state),moved=path.join(f.directory,'moved-root');
  const client=f.client('Fixture Publisher',{userData:moved});await client.check();
  // The old location's installers are ignored: one re-download, no failure, no backoff.
  assert.equal(f.downloads,2);assert.equal(f.state.verifyFailure,undefined);assert.equal(f.state.pending.phase,'prepared');
  assert.ok(fs.existsSync(path.join(moved,'updates','2','Terrier.exe')));
  // Nothing reset: same high-water, same accepted version, same installed record.
  assert.equal(f.state.sequence,before.sequence);assert.equal(f.state.acceptedVersion,before.acceptedVersion);assert.equal(f.state.manifestHash,before.manifestHash);assert.deepEqual(f.state.installed,before.installed);
  // And it cannot go backwards from the moved root either: an older signed release is refused.
  f.state={...f.state,pending:null};f.envelope=f.sign('1.0.5',0);const downloads=f.downloads;
  await f.client('Fixture Publisher',{userData:moved}).check();
  assert.equal(f.state.sequence,before.sequence);assert.equal(f.state.acceptedVersion,before.acceptedVersion);assert.equal(f.downloads,downloads);assert.equal(f.state.pending,null);
});

// An update installed by a version that cached its installer in the old updater file root leaves a pending record for
// the running version whose installer is not at the current path.
for(const [name,ready,legacy] of [['ready, installer only at the legacy path',true,true],['ready, installer nowhere',true,false],['background-only, installer only at the legacy path',false,true]])
  test('an activated update whose installer cache moved is confirmed by the running version, then discovery proceeds: '+name,async t=>{
    const f=fixture(t);const first=f.client();await first.check();await first.activateAfterClose();
    assert.equal(f.state.pending.phase,'activating');f.version='1.1.0';
    if(!legacy)fs.rmSync(path.join(f.directory,'updates','2'),{recursive:true});
    const client=f.client('Fixture Publisher',{userData:path.join(f.directory,'moved-root'),legacyUserData:f.directory});
    if(ready)client.markApplicationReady();
    await client.check();
    assert.equal(f.state.pending,null);assert.equal(f.state.installed.version,'1.1.0');assert.equal(f.state.installedVersion,'1.1.0');assert.equal(f.state.previous.version,'1.0.0');
    assert.match(f.status.at(-1),/^Already current\./,'the check went on to ask for newer releases');
    // The verified legacy copy is kept at the current path, where a later offline rollback looks for it.
    if(legacy)assert.deepEqual(fs.readFileSync(path.join(f.directory,'moved-root','updates','2','Terrier.exe')),fs.readFileSync(path.join(f.directory,'updates','2','Terrier.exe')));
  });

test('an installer gone from both paths does not prove the old cache was used: a background-only run waits for a successful startup',async t=>{
  const f=fixture(t);const first=f.client();await first.check();await first.activateAfterClose();f.version='1.1.0';
  fs.rmSync(path.join(f.directory,'updates','2'),{recursive:true});
  const options={userData:path.join(f.directory,'moved-root'),legacyUserData:f.directory};
  await f.client('Fixture Publisher',options).check();
  assert.equal(f.state.pending.phase,'activating');assert.equal(f.state.installed.version,'1.0.0');assert.match(f.status.at(-1),/awaits a successful local startup/);
  const ready=f.client('Fixture Publisher',options);ready.markApplicationReady();await ready.check();
  assert.equal(f.state.pending,null);assert.equal(f.state.installed.version,'1.1.0');
});

test('a legacy-path installer is still verified: one failing the native check does not confirm the update',async t=>{
  const f=fixture(t);const first=f.client();await first.check();await first.activateAfterClose();f.version='1.1.0';f.nativeValid=false;
  const client=f.client('Fixture Publisher',{userData:path.join(f.directory,'moved-root'),legacyUserData:f.directory});client.markApplicationReady();await client.check();
  assert.equal(f.state.pending.phase,'activating');assert.equal(f.state.installed.version,'1.0.0');assert.match(f.status.at(-1),/Native signature refused/);
});

test('an installer at the current path keeps the readiness gate: a background-only run does not confirm it',async t=>{
  const f=fixture(t);const first=f.client();await first.check();await first.activateAfterClose();f.version='1.1.0';
  await f.client().check();assert.equal(f.state.pending.phase,'activating');assert.equal(f.state.installed.version,'1.0.0');assert.match(f.status.at(-1),/awaits a successful local startup/);
});

test('main.cjs moves only the updater file root to %LOCALAPPDATA%, leaving the update state in the profile',()=>{
  const main=fs.readFileSync(path.join(__dirname,'..','main.cjs'),'utf8');
  assert.match(main,/const updaterRoot=localRoot\?path\.join\(localRoot,'updater'\):githubConfig\?path\.join\(userData,'github-updates'\):userData;/);
  assert.match(main,/baselineRoot:localRoot\?path\.join\(localRoot,'baseline'\):null/);assert.match(main,/userData:updaterRoot,loadEnrollment/);
  assert.match(main,/legacyUserData:localRoot&&githubConfig\?path\.join\(userData,'github-updates'\):null/,'the pre-move cache stays known to the updater');
  assert.match(main,/readState:\(\)=>read\(githubConfig\?'github-update-state\.json':'update-state\.json'\),writeState:value=>write\(/,'state stays in the profile');
});

// ---- Downloads install layout (DL-spec 2.3 / 3.2) ----
const layoutModule=require('../install-layout.cjs');
function layoutOptions(root,over={}){const cache=path.join(root,'updates','terrier');return {installLayout:{cacheDirectory:cache,sweep:async()=>{},...over}};}

test('electron-updater is pinned to the audited 6.8.9 and still reuses a preset download helper',async()=>{
  assert.equal(require('electron-updater/package.json').version,'6.8.9','the downloadedUpdateHelper preset relies on 6.8.9 internals; re-audit AppUpdater.getOrCreateDownloadHelper before bumping');
  assert.equal(require('../package.json').dependencies['electron-updater'],'6.8.9');
  const {DownloadedUpdateHelper}=require('electron-updater/out/DownloadedUpdateHelper'),{AppUpdater}=require('electron-updater');
  const helper=new DownloadedUpdateHelper(path.join(os.tmpdir(),'dl-helper-probe'));
  assert.equal(await AppUpdater.prototype.getOrCreateDownloadHelper.call({downloadedUpdateHelper:helper}),helper);
  assert.equal(helper.cacheDirForPendingUpdate,path.join(os.tmpdir(),'dl-helper-probe','pending'));
});

test('with an install layout the update cache moves under Downloads; without one the auto-updater is untouched',t=>{
  const f=fixture(t),root=path.join(f.directory,'Downloads','MelangeApplications');
  const legacy=f.client();assert.equal('downloadedUpdateHelper' in legacy.autoUpdater,false);assert.equal('installDirectory' in legacy.autoUpdater,false);
  const moved=f.client('Fixture Publisher',layoutOptions(root));
  assert.equal(moved.autoUpdater.downloadedUpdateHelper.cacheDirForPendingUpdate,path.join(root,'updates','terrier','pending'));
});

test('B2: activation never passes /D (a spaced path would be quoted and ignored by NSIS); the installer chooses its own folder',async t=>{
  const f=fixture(t),root=path.join(f.directory,'Down loads','MelangeApplications');
  const spaced=f.client('Fixture Publisher',layoutOptions(root));await spaced.check();
  assert.equal(await spaced.activateAfterClose(),true);assert.equal('installDirectory' in spaced.autoUpdater,false);
  const h=fixture(t),plain=h.client();await plain.check();await plain.activateAfterClose();assert.equal('installDirectory' in plain.autoUpdater,false,'no layout: never touched');
});

test('a rollback below the Downloads floor is refused with a layout and allowed without one',t=>{
  const f=fixture(t),root=path.join(f.directory,'Downloads','MelangeApplications');
  const target=version=>{const envelope=f.sign(version,0);return {phase:'prepared',target:{envelope,version},manifestHash:crypto.createHash('sha256').update(Buffer.from(envelope.payload,'base64')).digest('hex')}};
  const withLayout=f.client('Fixture Publisher',layoutOptions(root)),without=f.client();
  assert.throws(()=>withLayout.verifyRecovery(f.enrollment,target('1.0.18')),/Rollback below 1\.0\.19 would leave the Downloads layout/);
  assert.equal(without.verifyRecovery(f.enrollment,target('1.0.18')).manifest.version,'1.0.18');
  assert.equal(withLayout.verifyRecovery(f.enrollment,target('1.0.19')).manifest.version,'1.0.19');
});

test('readiness sweeps the layout exactly once and a failing sweep never throws',async t=>{
  const f=fixture(t),root=path.join(f.directory,'Downloads','MelangeApplications');
  let calls=0,seen;
  const ok=f.client('Fixture Publisher',layoutOptions(root,{sweep:async s=>{calls++;seen=s;}}));
  ok.markApplicationReady();ok.markApplicationReady();assert.equal(calls,1);assert.equal(ok.applicationReady,true);assert.equal(seen.installed.version,'1.0.0');
  const rejecting=f.client('Fixture Publisher',layoutOptions(root,{sweep:()=>Promise.reject(new Error('boom'))}));
  assert.doesNotThrow(()=>rejecting.markApplicationReady());await new Promise(resolve=>setImmediate(resolve));
  const throwing=f.client('Fixture Publisher',layoutOptions(root,{sweep(){throw new Error('sync boom');}}));
  assert.doesNotThrow(()=>throwing.markApplicationReady());
  const legacy=f.client();legacy.markApplicationReady();assert.equal(legacy.applicationReady,true);
});
