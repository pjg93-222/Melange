'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {GitHubModules}=require('../github-modules.cjs');
const {canonical}=require('../access-client.cjs');
const {environment,signed}=require('./fixtures/github-module-fixture.cjs');
function local(appId){const identity={schemaVersion:1,appId,deviceId:'11111111-1111-4111-8111-111111111111',accountId:'22222222-2222-4222-8222-222222222222',accountIdentity:'local_fixture'};return {mode:'standalone',identity,session:{...identity,sessionId:'33333333-3333-4333-8333-333333333333',authenticatedAt:1800000000000,method:'device-trust'},principal:null};}
function journal(initial=null){let value=structuredClone(initial),writes=0;return {read:async()=>structuredClone(value),write:async next=>{value=structuredClone(next);writes++;},get value(){return structuredClone(value);},get writes(){return writes;}};}
for(const appId of ['melange','mentat']){
 test(`${appId} local migration verifies and preserves the highest signed watermark without adopting old activations`,async()=>{
  const f=environment(appId);try{
   const old=new GitHubModules(f.options),first=f.remote,candidate=await old.prepare(f.selected);await old.commitActive(candidate,f.selected);
   f.remote=signed(appId,{sequence:2,keys:first.keys});await old.stage(f.selected);
   const before=structuredClone(f.journal),next=journal();f.requests.length=0;
   const options={...f.options,store:next,previousStore:f.store,authorize:async()=>local(appId)},provider=new GitHubModules(options);
   assert.equal(await provider.active(f.selected),null);assert.deepEqual(f.requests,[]);
   assert.deepEqual(next.value.highwater,before.highwater);assert.equal(next.value.highwater.catalogSequence,2);
   for(const key of ['accepted','staged','active'])assert.equal(next.value[key],null);
   assert.deepEqual(f.journal,before);
   f.remote=first;await assert.rejects(provider.prepare(f.selected),/rollback/);assert.deepEqual(next.value.highwater,before.highwater);
   const restarted=new GitHubModules({...options,previousStore:{read:async()=>assert.fail('Existing local journal must not be remigrated')}});
   assert.equal(await restarted.active(f.selected),null);assert.equal(next.writes,1);assert.deepEqual(f.journal,before);
  }finally{f.cleanup();}
 });
 test(`${appId} invalid or missing cached signed history cannot reset the watermark`,async()=>{
  const f=environment(appId);try{
   await new GitHubModules(f.options).prepare(f.selected);const before=structuredClone(f.journal),next=journal(),file=path.join(f.options.cacheRoot,'pointers',before.highwater.pointerDigest+'.json');
   const envelope=JSON.parse(fs.readFileSync(file,'utf8'));envelope.signature=Buffer.alloc(64).toString('base64');fs.writeFileSync(file,canonical(envelope));f.requests.length=0;
   const provider=new GitHubModules({...f.options,store:next,previousStore:f.store,authorize:async()=>local(appId)});
   await assert.rejects(provider.active(f.selected),/high-water could not be verified/);assert.equal(next.value,null);assert.equal(next.writes,0);
   fs.unlinkSync(file);await assert.rejects(provider.active(f.selected),/high-water could not be verified/);
   assert.deepEqual(f.journal,before);assert.deepEqual(f.requests,[]);
  }finally{f.cleanup();}
 });
 test(`${appId} malformed prior journal cannot be imported and failed persistence retries safely`,async()=>{
  const f=environment(appId);try{
   await new GitHubModules(f.options).prepare(f.selected);const before=structuredClone(f.journal),next=journal();
   const options={...f.options,store:next,authorize:async()=>local(appId)};
   await assert.rejects(new GitHubModules({...options,previousStore:{read:async()=>({...before,appId:'terrier'})}}).active(f.selected),/journal/);assert.equal(next.value,null);
   const realWrite=next.write;let fail=true;next.write=async value=>{if(fail){fail=false;throw new Error('Synthetic write interruption');}return realWrite(value);};
   const provider=new GitHubModules({...options,previousStore:f.store});await assert.rejects(provider.active(f.selected));assert.equal(next.value,null);
   assert.equal(await provider.active(f.selected),null);assert.deepEqual(next.value.highwater,before.highwater);assert.deepEqual(f.journal,before);
  }finally{f.cleanup();}
 });
}
