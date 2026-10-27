'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os'),crypto=require('node:crypto');
const proof=require('../directory-package-proof.cjs');
const {DesktopUpdater}=require('../updater.cjs');
// Publisher RSA verification has its own cryptographic tests. These tests keep
// real Ed25519 envelopes/hashes and replace only the native/platform boundaries.
function fixture(t){
 t.mock.method(proof,'verifyDirectoryPackageProof',m=>{assert.equal(m.package.format,proof.FORMAT);});
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'directory-lifecycle-'));
 t.after(()=>fs.rmSync(directory,{recursive:true,force:true}));
 const keys=crypto.generateKeyPairSync('ed25519');
 const enrollment={appId:'melange',deviceToken:'fixture',publicKeys:{admin:keys.publicKey.export({format:'der',type:'spki'}).subarray(-32).toString('base64')}};
 const bytes=Buffer.from('ZIP data boundary test fixture');
 const sign=(version,sequence)=>{
  const name='melange-'+version+'-win32-x64.zip';
  const m={schemaVersion:1,appId:'melange',version,sequence,platform:'win32',arch:'x64',minimumUpdaterVersion:'2.0.0',dataSchemaVersion:1,issuedAt:new Date().toISOString(),publisherThumbprints:['0EBC9AD04E929CDD731EDB5D278A4143BC3D3D30'],package:{format:proof.FORMAT,entrypoint:'Melange.exe',name,path:'/v1/packages/melange/'+sequence+'/'+name,size:bytes.length,sha256:crypto.createHash('sha256').update(bytes).digest('hex'),sha512:crypto.createHash('sha512').update(bytes).digest('base64')}};
  const payload=Buffer.from(JSON.stringify(m));return {schemaVersion:1,keyId:'admin',payload:payload.toString('base64'),signature:crypto.sign(null,payload,keys.privateKey).toString('base64')};
 };
 const releases={'1.0.20':sign('1.0.20',1),'1.0.21':sign('1.0.21',2),'1.0.22':sign('1.0.22',3)};
 let state={},version='1.0.20',offered='1.0.21',failLaunch=false,validFolder=true;
 const events=[],queries=[];
 const adapter={
  async prepare(file,m){events.push('prepare:'+m.version);return {executable:path.join(directory,'Melange-'+m.version,'Melange.exe')};},
  async verify(file,m){if(!validFolder)throw new Error('Directory inventory changed');events.push('verify:'+m.version);},
  async launch(file,m,run){assert.ok(state.pending?.phase==='activating'||state.recovery?.phase==='activating'||state.installed?.version===m.version);if(!validFolder)throw new Error('Directory inventory changed');if(failLaunch)throw new Error('relaunch refused');events.push('launch:'+m.version+':'+run);}
 };
 const clients=[];
 function client(extra={}){
  const noNative=()=>{throw new Error('NSIS/native updater must never run');};
  const c=new DesktopUpdater({appId:'melange',version,platform:'win32',arch:'x64',packaged:true,publisherName:'Pinned fixture publisher',directoryInstaller:adapter,userData:directory,
   autoUpdater:{setFeedURL:noNative,checkForUpdates:noNative,downloadUpdate:noNative,quitAndInstall:noNative},makeFeed:noNative,
   loadEnrollment:()=>enrollment,saveEnrollment(){},readState:()=>structuredClone(state),writeState:s=>{state=structuredClone(s);},onStatus(){},
   request:async(p,url)=>{queries.push(url);if(url.endsWith('/trust'))return {transitions:[]};if(url==='/v1/status')return {};if(url.includes('/recovery?'))return releases[version];return offered?releases[offered]:null;},
   download:async(p,token,m,target)=>{fs.mkdirSync(target,{recursive:true});fs.writeFileSync(path.join(target,m.package.name),bytes);},...extra});clients.push(c);return c;
 }
 t.after(()=>clients.forEach(c=>c.close()));
 return {client,events,queries,releases,get state(){return state;},set state(s){state=s;},set version(v){version=v;},set offered(v){offered=v;},set failLaunch(v){failLaunch=v;},set validFolder(v){validFolder=v;}};
}
test('ZIP update stages, activates after close, confirms readiness and performs second update without NSIS',async t=>{
 const f=fixture(t),first=f.client();await first.check();assert.equal(f.state.pending.phase,'prepared');
 assert.ok(f.queries.some(q=>q.includes('/updates?')&&q.includes('distribution=directory-zip')));
 assert.equal(await first.activateAfterClose(false),true);assert.ok(f.events.includes('launch:1.0.21:false'));
 f.version='1.0.21';f.offered=null;const next=f.client();await next.check();assert.equal(f.state.installed.version,'1.0.20');
 next.markApplicationReady();await next.check();assert.equal(f.state.installed.version,'1.0.21');assert.equal(f.state.previous.version,'1.0.20');
 f.offered='1.0.22';await next.check();assert.equal(await next.activateAfterClose(true),true);assert.ok(f.events.includes('launch:1.0.22:true'));
});
test('failed relaunch keeps prepared candidate and old copy usable; OS shutdown never activates',async t=>{
 const f=fixture(t),c=f.client();await c.check();f.failLaunch=true;assert.equal(await c.activateAfterClose(),false);assert.equal(f.state.pending.phase,'prepared');
 f.failLaunch=false;c.suspendInstallation();assert.equal(await c.activateAfterClose(),false);assert.equal(f.events.filter(e=>e.startsWith('launch:')).length,0);
});
test('changed extracted files refuse activation and preserve data/update state',async t=>{
 const f=fixture(t),c=f.client();await c.check();f.validFolder=false;assert.equal(await c.activateAfterClose(),false);
 assert.equal(f.state.pending.phase,'prepared');assert.equal(f.state.sequence,2);assert.equal(f.events.filter(e=>e.startsWith('launch:')).length,0);
});
test('explicit folder rollback preserves antirollback highwater and stages no native installer',async t=>{
 const f=fixture(t),c=f.client();await c.check();await c.activateAfterClose();f.version='1.0.21';f.offered=null;
 const next=f.client();next.markApplicationReady();await next.check();await next.beginRecovery();assert.equal(f.state.recovery.phase,'prepared');
 assert.equal(await next.activateAfterClose(),true);assert.ok(f.events.includes('launch:1.0.20:false'));assert.equal(f.state.sequence,2);assert.equal(f.state.acceptedVersion,'1.0.21');
});
test('retained shortcut redirects only confirmed version and never overrides an active rollback',async t=>{
 const f=fixture(t),first=f.client();await first.check();await first.activateAfterClose();f.version='1.0.21';f.offered=null;
 const next=f.client();assert.equal(await next.redirectInstalled(),false);next.markApplicationReady();await next.check();
 f.version='1.0.20';const stale=f.client();assert.equal(await stale.redirectInstalled(),true);assert.ok(f.events.includes('launch:1.0.21:true'));
 f.version='1.0.21';await next.beginRecovery();assert.equal(await stale.redirectInstalled(),false);
});
test('directory readiness never runs native layout cleanup or adopts EXE baseline',async t=>{
 const f=fixture(t),c=f.client({installLayout:{sweep(){throw new Error('Must preserve existing installed app');}},baselineRoot:'not-used'});
 c.markApplicationReady();assert.equal(c.adoptBaseline({version:'1.0.20'}),null);await c.check();assert.equal(f.state.pending.phase,'prepared');
});
test('background activation survives reboot through old login target without claiming backend readiness',async t=>{
 const f=fixture(t),old=f.client();await old.check();await old.activateAfterClose(false);
 f.version='1.0.21';f.offered=null;const background=f.client();await background.check();
 assert.equal(f.state.pending.phase,'awaiting-ready');assert.equal(f.state.installed.version,'1.0.20');
 f.version='1.0.20';const login=f.client();assert.equal(await login.redirectInstalled(false),true);
 assert.equal(f.state.pending.phase,'activating');assert.equal(f.state.pending.startupAttempts,1);
 f.version='1.0.21';const opened=f.client();opened.markApplicationReady();await opened.check();assert.equal(f.state.installed.version,'1.0.21');
});
test('repeated unacknowledged new-process failure falls back without an endless relaunch loop',async t=>{
 const f=fixture(t),old=f.client();await old.check();await old.activateAfterClose(false);
 assert.equal(await old.redirectInstalled(false),true);assert.equal(await old.redirectInstalled(false),true);
 assert.equal(await old.redirectInstalled(false),false);assert.equal(f.state.pending.phase,'failed');assert.equal(f.state.installed.version,'1.0.20');
});

test('background startup verifies once per process and rechecks on real application readiness',async t=>{
 const f=fixture(t),old=f.client();await old.check();await old.activateAfterClose(false);
 f.version='1.0.21';f.offered=null;const background=f.client();await background.check();
 const count=()=>f.events.filter(value=>value==='verify:1.0.21').length;
 const acknowledged=count();await background.check();await background.check();assert.equal(count(),acknowledged);
 const restart=f.client();await restart.check();assert.equal(count(),acknowledged+1);
 f.validFolder=false;restart.markApplicationReady();await restart.check();
 assert.equal(f.state.installed.version,'1.0.20');assert.equal(f.state.pending.phase,'awaiting-ready');
 f.validFolder=true;await restart.check();assert.equal(f.state.installed.version,'1.0.21');assert.equal(f.state.pending,null);
});

test('rollback background startup routes old login safely and commits only verified readiness',async t=>{
 const f=fixture(t),old=f.client();await old.check();await old.activateAfterClose(false);
 f.version='1.0.21';f.offered=null;const current=f.client();current.markApplicationReady();await current.check();
 await current.beginRecovery();await current.activateAfterClose(false);
 f.version='1.0.20';const restored=f.client();await restored.check();
 assert.equal(f.state.recovery.phase,'awaiting-ready');assert.equal(f.state.installed.version,'1.0.21');
 const verified=f.events.filter(value=>value==='verify:1.0.20').length;await restored.check();
 assert.equal(f.events.filter(value=>value==='verify:1.0.20').length,verified);
 f.version='1.0.21';const login=f.client();assert.equal(await login.redirectInstalled(false),true);
 assert.equal(f.state.recovery.phase,'activating');assert.equal(f.state.recovery.startupAttempts,1);
 f.version='1.0.20';const opened=f.client();opened.markApplicationReady();f.validFolder=false;await opened.check();
 assert.equal(f.state.installed.version,'1.0.21');assert.notEqual(f.state.recovery.phase,'completed');
 f.validFolder=true;await opened.check();assert.equal(f.state.installed.version,'1.0.20');assert.equal(f.state.recovery.phase,'completed');
 assert.equal(f.state.sequence,2);assert.equal(f.state.acceptedVersion,'1.0.21');assert.ok(f.state.suspendedVersions.includes('1.0.21'));
});

test('final staged-directory failure is recorded and does not repeatedly extract the same release',async t=>{
 const f=fixture(t);let preparations=0;
 const c=f.client({directoryInstaller:{prepare:async()=>{preparations++;const error=new Error('Final inventory changed');error.directoryStageFailed=true;error.stagingDirectory='owned-quarantine';throw error;}}});
 await c.check();assert.equal(f.state.pending.phase,'failed');assert.equal(f.state.pending.stageFailure.directory,'owned-quarantine');
 await c.check();await c.check();assert.equal(preparations,1);assert.equal(f.state.sequence,2);
});

test('only an explicit check retries a failed stage, after safe cleanup, preserving highwater',async t=>{
 const f=fixture(t);let preparations=0,cleanups=0,allowCleanup=false;
 const adapter={prepare:async()=>{
  preparations++;if(preparations===1){const error=new Error('Temporary policy failure');error.directoryStageFailed=true;error.stagingDirectory='retained';throw error;}
  return {executable:'verified.exe'};
 },clearFailedStage:async()=>{cleanups++;if(!allowCleanup)throw new Error('Changed quarantine was preserved');}};
 const c=f.client({directoryInstaller:adapter});await c.check();const highwater=f.state.sequence;
 await c.check();assert.equal(preparations,1);assert.equal(cleanups,0);
 await c.check({manual:true});assert.equal(f.state.pending.phase,'failed');assert.equal(preparations,1);
 allowCleanup=true;await c.check({manual:true});assert.equal(preparations,2);assert.equal(cleanups,2);
 assert.equal(f.state.pending.phase,'prepared');assert.equal(f.state.sequence,highwater);assert.equal(f.state.acceptedVersion,'1.0.21');
});

test('isolated update clients cannot clear a failed production staging folder',async t=>{
 const f=fixture(t);let cleanups=0;
 const adapter={prepare:async()=>{const error=new Error('Staged failure');error.directoryStageFailed=true;error.stagingDirectory='retained';throw error;},clearFailedStage:async()=>{cleanups++;}};
 await f.client({directoryInstaller:adapter}).check();const before=f.state;
 const isolated=f.client({directoryInstaller:adapter,nativeInstallation:false});await isolated.check({manual:true});
 assert.equal(cleanups,0);assert.deepEqual(f.state,before);
});

test('retention records only fresh versions and prunes before the old ZIP baseline is removed',async t=>{
 const f=fixture(t),recorded=[],pruned=[];
 const retention={recordCreated:async(m,directory,ownership)=>recorded.push({version:m.version,directory,ownership}),prune:async request=>{
  for(const candidate of request.candidates)if(candidate.manifest.version==='1.0.21')assert.equal(fs.existsSync(candidate.filename),true);
  pruned.push(request);return {removed:[],preserved:[]};
 }};
 const c=f.client({directoryRetention:retention,directoryInstaller:{prepare:async()=>({created:false,executable:'existing.exe'})}});
 await c.check();assert.equal(recorded.length,0);
 const fresh=f.client({directoryRetention:retention,directoryInstaller:{prepare:async()=>({created:true,executable:'fresh.exe',directory:'fresh-directory',ownership:{dev:1n,ino:2n}})}});
 await fresh.check();assert.equal(recorded.length,1);assert.equal(recorded[0].ownership.ino,2n);
 // The next confirmed installation keeps itself, previous, and current process.
 const confirmed=f.state.pending;f.state={...f.state,installed:{...confirmed,phase:'installed'},previous:f.state.installed,pending:null};
 f.version='1.0.21';f.offered='1.0.22';const next=f.client({directoryRetention:retention});await next.check();await next.activateAfterClose(false);
 f.version='1.0.22';f.offered=null;const newest=f.client({directoryRetention:retention});newest.markApplicationReady();await newest.check();
 assert.equal(pruned.length,1);assert.ok(pruned[0].keepVersions.includes('1.0.22'));assert.ok(pruned[0].keepVersions.includes('1.0.21'));
 assert.equal(pruned[0].keepVersions.includes('1.0.20'),false);assert.ok(pruned[0].candidates.some(c=>c.manifest.version==='1.0.20'));
});
