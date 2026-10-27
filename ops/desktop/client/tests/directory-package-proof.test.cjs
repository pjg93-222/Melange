'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const {signingFixture}=require('./fixtures/directory-package-fixture.cjs');
const publisher=signingFixture();
// Replace only this test process's pinned public certificate before loading the
// verifier. Production APIs expose no configurable publisher pin.
require('../publisher-trust.cjs').THUMBPRINT=publisher.thumbprint;
const {publisherProofPayload,verifyDirectoryPackageProof,FORMAT}=require('../directory-package-proof.cjs');
const {verifyEnvelope}=require('../trust.cjs');
const {GitHubSource,githubPolicy,discoveryMetadata}=require('../github-source.cjs');
const repo='owner/desktop-updates',keys=crypto.generateKeyPairSync('ed25519');
const enrollment={source:'github',appId:'melange',repository:repo,publicKeys:{root:keys.publicKey.export({format:'der',type:'spki'}).subarray(-32).toString('base64')}};
const identity={appId:'melange',platform:'win32',arch:'x64',version:'1.0.20',distribution:'directory-zip'};
function manifest(){
 const bytes=Buffer.from('Synthetic ZIP bytes; never execute');
 const m={schemaVersion:1,purpose:'melange-desktop-github-release',distribution:'public-installations',repository:repo,sourceRefs:Object.fromEntries(['melange','mentat','terrier'].map(app=>[app,{repository:'owner/'+app,ref:'main',commit:'a'.repeat(40)}])),appId:'melange',version:'1.0.21',sequence:21,platform:'win32',arch:'x64',minimumUpdaterVersion:'2.0.0',dataSchemaVersion:1,issuedAt:new Date().toISOString(),publisherThumbprints:[publisher.thumbprint],package:{format:FORMAT,entrypoint:'Melange.exe',name:'melange-1.0.21-win32-x64.zip',path:'/v1/packages/melange/21/melange-1.0.21-win32-x64.zip',size:bytes.length,sha256:crypto.createHash('sha256').update(bytes).digest('hex'),sha512:crypto.createHash('sha512').update(bytes).digest('base64')}};
 m.package.publisherProof={schemaVersion:1,algorithm:'rsa-sha256',certificateDer:publisher.certificate.toString('base64'),signature:publisher.sign(publisherProofPayload(m)).toString('base64')};return m;
}
function envelope(m){const payload=Buffer.from(JSON.stringify(m));return {schemaVersion:1,keyId:'root',payload:payload.toString('base64'),signature:crypto.sign(null,payload,keys.privateKey).toString('base64')};}
test('directory ZIP requires both real publisher and Ed25519 signatures',()=>{
 const m=manifest();assert.equal(verifyDirectoryPackageProof(m).thumbprint,publisher.thumbprint);assert.equal(verifyEnvelope(envelope(m),enrollment,identity).manifest.package.format,FORMAT);
 const forged=envelope(m);forged.signature=Buffer.alloc(64).toString('base64');assert.throws(()=>verifyEnvelope(forged,enrollment,identity),/signature/);
 m.package.publisherProof.signature=Buffer.alloc(256).toString('base64');assert.throws(()=>verifyEnvelope(envelope(m),enrollment,identity),/publisher signature/);
});
test('publisher proof binds full package identity and archive hashes even after Ed25519 re-signing',()=>{
 for(const key of ['appId','version','platform','arch']){const m=manifest();m[key]={appId:'mentat',version:'1.0.22',platform:'darwin',arch:'arm64'}[key];assert.throws(()=>verifyDirectoryPackageProof(m),key);}
 for(const [key,value] of Object.entries({format:'nsis',entrypoint:'Other.exe',name:'other.zip',size:77,sha256:'b'.repeat(64),sha512:Buffer.alloc(64,3).toString('base64')})){const m=manifest();m.package[key]=value;assert.throws(()=>verifyDirectoryPackageProof(m),key);}
 const m=manifest();m.package.sha256='b'.repeat(64);assert.throws(()=>verifyEnvelope(envelope(m),enrollment,identity),/publisher signature/);
});
test('untrusted certificate, invalid proof shape, noncanonical encodings and invalid validity fail closed',()=>{
 const foreign=signingFixture(),m=manifest();m.package.publisherProof.certificateDer=foreign.certificate.toString('base64');m.package.publisherProof.signature=foreign.sign(publisherProofPayload(m)).toString('base64');assert.throws(()=>verifyDirectoryPackageProof(m),/pinned/);
 for(const mutate of [m=>delete m.package.publisherProof,m=>m.package.publisherProof.extra=true,m=>m.package.publisherProof.algorithm='none',m=>m.package.publisherProof.signature+='\n',m=>m.package.publisherProof.certificateDer+='\n',m=>m.publisherThumbprints=['A'.repeat(40)],m=>m.issuedAt='2000-01-01T00:00:00.000Z']){const m=manifest();mutate(m);assert.throws(()=>verifyDirectoryPackageProof(m));}
});
test('ZIP identity cannot accept native packages and native identity cannot accept ZIP packages',()=>{
 const m=manifest();assert.throws(()=>verifyEnvelope(envelope(m),enrollment,{...identity,distribution:'native'}));assert.throws(()=>verifyEnvelope(envelope(m),enrollment,{...identity,distribution:undefined}));assert.throws(()=>verifyEnvelope(envelope(m),enrollment,{...identity,distribution:'typo'}));
 const native={...m,minimumUpdaterVersion:'1.0.0',package:{...m.package,format:undefined,name:'melange-1.0.21-win32-x64.exe',path:'/v1/packages/melange/21/melange-1.0.21-win32-x64.exe'}};assert.throws(()=>verifyEnvelope(envelope(native),enrollment,identity));
 assert.throws(()=>verifyEnvelope(envelope(m),enrollment,identity,{sequence:22}),/Rollback/);assert.throws(()=>verifyEnvelope(envelope(m),enrollment,identity,{sequence:21,manifestHash:'changed'}),/equivocation/);
});
test('GitHub discovers separate ZIP manifest and refuses native recovery/download in ZIP mode',async()=>{
 const m=manifest(),e=envelope(m),asset=name=>({name,size:name.endsWith('.zip')?m.package.size:100,browser_download_url:'https://github.com/'+repo+'/releases/download/desktop-v1.0.21/'+name});
 const value={draft:false,prerelease:false,tag_name:'desktop-v1.0.21',assets:[asset(m.package.name),asset('melange-win32-x64-directory-zip.manifest.json'),asset('melange-trust.json')]};
 const calls=[],readJSON=async url=>{calls.push(url);return url.includes('?per_page=')?[value]:url.includes('/tags/')?value:e;};
 const native=new GitHubSource({repository:repo,appId:'melange',readJSON});assert.equal(await native.latest(),null);
 const zipped=new GitHubSource({repository:repo,appId:'melange',distribution:'directory-zip',readJSON});const item=await zipped.latest();assert.equal(item.version,'1.0.21');assert.deepEqual(await zipped.manifest(item),e);assert.match(calls.at(-1),/directory-zip\.manifest\.json$/);
 assert.deepEqual(await zipped.request(enrollment,'/v1/apps/melange/recovery?platform=win32&arch=x64&version=1.0.21'),e);
 assert.throws(()=>githubPolicy(m,repo),/policy/);assert.throws(()=>discoveryMetadata([item],repo),/asset/);
 await assert.rejects(native.download(enrollment,null,m,'unused'),/policy/);
 const wrong={...m,package:{...m.package,name:'melange-1.0.21-win32-x64.exe'}};await assert.rejects(zipped.download(enrollment,null,wrong,'unused'),/policy/);
});
