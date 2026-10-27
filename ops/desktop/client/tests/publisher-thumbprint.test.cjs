'use strict';
// Installer publisher pinning end to end: the real updater with the real native-signature.cjs default, only the
// PowerShell Get-AuthenticodeSignature answer is simulated. Owner decision (Task 4, 2026-10-23): the signer thumbprint
// must be in the Ed25519-signed manifest's publisherThumbprints; Status Valid is not required and no trust store is
// consulted; the sha256/sha512 gates still authenticate the bytes; a manifest without the field is refused.
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os'),crypto=require('node:crypto');
const childProcess=require('node:child_process');
const PIN='0EBC9AD04E929CDD731EDB5D278A4143BC3D3D30',OTHER='1111111111111111111111111111111111111111';
let signer={status:0,thumbprint:PIN},signatureCalls=0;
// Installed before updater.cjs loads, so native-signature.cjs binds this double. Each test file runs in its own process.
childProcess.execFile=(file,args,options,callback)=>{
  signatureCalls++;
  return {stdin:{on(){},end(input){const {path:target}=JSON.parse(input);process.nextTick(()=>callback(null,JSON.stringify({status:signer.status,path:target,thumbprint:signer.thumbprint}),''));}}};
};
const platform=Object.getOwnPropertyDescriptor(process,'platform');
Object.defineProperty(process,'platform',{...platform,value:'win32'});
const {DesktopUpdater}=require('../updater.cjs');
const {verifyEnvelope}=require('../trust.cjs');

function fixture(t,{thumbprints=[PIN]}={}){
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'desktop-thumbprint-'));
  t.after(()=>fs.rmSync(directory,{recursive:true,force:true}));
  signer={status:0,thumbprint:PIN};signatureCalls=0;
  const keys=crypto.generateKeyPairSync('ed25519');
  const enrollment={appId:'terrier',deviceToken:'TEST-TOKEN-0000',publicKeys:{admin:keys.publicKey.export({format:'der',type:'spki'}).subarray(-32).toString('base64')}};
  const bytes=Buffer.from('Non-installable signed test fixture');
  const sign=(release,sequence,extra={})=>{
    const manifest={schemaVersion:1,appId:'terrier',version:release,sequence,platform:'win32',arch:'x64',minimumUpdaterVersion:'1.0.0',dataSchemaVersion:1,issuedAt:new Date().toISOString(),
      ...(thumbprints?{publisherThumbprints:thumbprints}:{}),...extra,
      package:{name:'Terrier.exe',path:'/v1/packages/terrier/'+sequence+'/Terrier.exe',size:bytes.length,sha256:crypto.createHash('sha256').update(bytes).digest('hex'),sha512:crypto.createHash('sha512').update(bytes).digest('base64')}};
    const payload=Buffer.from(JSON.stringify(manifest));
    return {schemaVersion:1,keyId:'admin',payload:payload.toString('base64'),signature:crypto.sign(null,payload,keys.privateKey).toString('base64')};
  };
  const seed=sign('1.0.0',1);
  const f={directory,enrollment,sign,status:[],installs:0,downloads:0,envelope:sign('1.1.0',2),payload:bytes,version:'1.0.0',
    state:{installed:{envelope:seed,version:'1.0.0',phase:'installed'},sequence:1,manifestHash:crypto.createHash('sha256').update(Buffer.from(seed.payload,'base64')).digest('hex'),acceptedVersion:'1.0.0'}};
  f.client=()=>{
    const native={configOnDisk:{value:Promise.resolve({publisherName:'Fixture Publisher'})},setFeedURL(){},
      async checkForUpdates(){const m=JSON.parse(Buffer.from(f.state.pending.envelope.payload,'base64'));return {updateInfo:{version:m.version,files:[m.package]}};},
      async downloadUpdate(){const staged=path.join(directory,'native.exe');fs.writeFileSync(staged,bytes);return [staged];},
      quitAndInstall(){this.quitAndInstallCalled=true;f.installs++;}};
    const updater=new DesktopUpdater({appId:'terrier',version:f.version,userData:directory,platform:'win32',arch:'x64',publisherName:'Fixture Publisher',packaged:true,autoUpdater:native,
      loadEnrollment:()=>enrollment,saveEnrollment(){},readState:()=>structuredClone(f.state),writeState:value=>{f.state=structuredClone(value);},onStatus:message=>f.status.push(message),
      makeFeed:async()=>({url:'http://127.0.0.1/fixture/',close(){}}),
      request:async(p,url)=>{if(url.endsWith('/trust'))return {transitions:[]};if(url.includes('/recovery?'))return seed;if(url==='/v1/status')return {};return f.envelope;},
      download:async(p,token,m,target)=>{f.downloads++;fs.mkdirSync(target,{recursive:true});const destination=path.join(target,m.package.name);fs.writeFileSync(destination,f.payload);return destination;}});
    t.after(()=>updater.close());return updater;
  };
  return f;
}
// "The current version keeps launching": a refused update never throws out of check() or the launch-time install,
// never reaches quitAndInstall, and leaves the running version's installed record untouched.
async function refusedAndStillRunning(f,client,pattern){
  await client.check();
  assert.equal(f.installs,0);assert.equal(await client.activateAfterClose(),false);assert.equal(f.installs,0);
  assert.equal(f.state.installed.version,'1.0.0');assert.notEqual(f.state.pending?.phase,'prepared');
  assert.match(f.status.at(-1),pattern);
}

test('a signer thumbprint in the manifest allow-list installs, even when Windows does not trust the self-signed root',async t=>{
  const f=fixture(t);signer={status:4,thumbprint:PIN.toLowerCase()};// NotTrusted: the root is not in the user's store
  const client=f.client();await client.check();
  assert.equal(f.state.pending.phase,'prepared');assert.ok(signatureCalls>=2,'the staged file and the native cache are both checked');
  assert.equal(await client.activateAfterClose(),true);assert.equal(f.installs,1);
});

test('an unsigned installer is refused',async t=>{
  const f=fixture(t);signer={status:2,thumbprint:null};
  await refusedAndStillRunning(f,f.client(),/Update deferred: Windows package signature or pinned publisher thumbprint could not be verified/);
  assert.equal(f.state.verifyFailure.manifestHash.length,64);
});

test('an installer signed by a different publisher is refused, whatever its Windows status',async t=>{
  for(const status of [0,1]){
    const f=fixture(t);signer={status,thumbprint:OTHER};
    await refusedAndStillRunning(f,f.client(),/pinned publisher thumbprint could not be verified/);
  }
});

test('a HashMismatch Authenticode status is refused even with the pinned thumbprint',async t=>{
  const f=fixture(t);signer={status:3,thumbprint:PIN};
  await refusedAndStillRunning(f,f.client(),/pinned publisher thumbprint could not be verified/);
});

test('an installer tampered with after signing is refused by the signed hash gate before any signature check',async t=>{
  const f=fixture(t);f.payload=Buffer.from('Non-installable signed test fixturX');// same size, different bytes
  await refusedAndStillRunning(f,f.client(),/Cached package integrity failed/);
  assert.equal(signatureCalls,0,'the hash gate runs first; the pinned thumbprint cannot rescue changed bytes');
});

test('a replayed older signed build is refused (version and sequence high-water)',async t=>{
  const f=fixture(t);f.version='1.2.0';const current=f.sign('1.2.0',3);
  f.state={installed:{envelope:current,version:'1.2.0',phase:'installed'},sequence:3,manifestHash:crypto.createHash('sha256').update(Buffer.from(current.payload,'base64')).digest('hex'),acceptedVersion:'1.2.0'};
  f.envelope=f.sign('1.1.0',2);const client=f.client();await client.check();
  assert.equal(f.downloads,0);assert.equal(f.installs,0);assert.equal(f.state.installed.version,'1.2.0');
  assert.match(f.status.at(-1),/downgrade refused/);
  f.envelope=f.sign('1.3.0',2);await client.check();// a newer version replaying an old sequence
  assert.equal(f.downloads,0);assert.match(f.status.at(-1),/Rollback or equivocation refused/);
});

test('a legacy manifest without publisherThumbprints is refused at activation (fail closed)',async t=>{
  const f=fixture(t,{thumbprints:null});
  await refusedAndStillRunning(f,f.client(),/names no publisher thumbprint/);
  assert.equal(signatureCalls,0,'refused before the signature tool runs');
});

test('a staged update whose signer no longer verifies is refused at launch and the current version starts normally',async t=>{
  const f=fixture(t);await f.client().check();assert.equal(f.state.pending.phase,'prepared');
  signer={status:2,thumbprint:null};const restarted=f.client();
  assert.ok(restarted.launchCandidate());assert.equal(await restarted.activateAtLaunch(()=>true),false);
  assert.equal(f.installs,0);assert.equal(f.state.installed.version,'1.0.0');
});

test('publisherThumbprints must be a non-empty list of 40 uppercase hex digits when present',t=>{
  const f=fixture(t),identity={appId:'terrier',version:'1.0.0',platform:'win32',arch:'x64'};
  assert.equal(verifyEnvelope(f.sign('1.1.0',2),f.enrollment,identity).manifest.publisherThumbprints[0],PIN);
  for(const bad of [[],[PIN.toLowerCase()],[PIN+'0'],'0EBC',[1],Array(9).fill(PIN)])
    assert.throws(()=>verifyEnvelope(f.sign('1.1.0',2,{publisherThumbprints:bad}),f.enrollment,identity),/Invalid publisher thumbprints/);
});

test('T18 enforcement after 1.0.19 refuses a manifest that omits the pinned publisher',async t=>{
  const f=fixture(t,{thumbprints:[OTHER]});signer={status:4,thumbprint:OTHER};
  await refusedAndStillRunning(f,f.client(),/does not name the pinned publisher thumbprint/);
  assert.equal(signatureCalls,0,'manifest cannot widen the client publisher pin');
});
