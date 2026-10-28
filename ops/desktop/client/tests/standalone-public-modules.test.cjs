'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {authorized}=require('../github-module-protocol.cjs');
const {GitHubModules}=require('../github-modules.cjs');
const {environment}=require('./fixtures/github-module-fixture.cjs');
function local(appId){
 const identity={schemaVersion:1,appId,deviceId:'11111111-1111-4111-8111-111111111111',accountId:'22222222-2222-4222-8222-222222222222',accountIdentity:'local_fixture'};
 return {mode:'standalone',identity,session:{...identity,sessionId:'33333333-3333-4333-8333-333333333333',authenticatedAt:1800000000000,method:'local-password'},principal:null};
}
for(const appId of ['melange','mentat']){
 test(`${appId} public module authority requires matching local sign-in and cannot carry a private grant`,()=>{
  const f=environment(appId);try{
   const auth=local(appId);assert.equal(authorized(appId,f.selected,auth),true);
   for(const candidate of [{...auth,session:null},{...auth,accepted:{grant:{}}},{...auth,principal:{role:'admin'}},{...auth,session:{...auth.session,accountId:auth.identity.deviceId}},{...auth,session:{...auth.session,method:'remote-approval'}}])assert.equal(authorized(appId,f.selected,candidate),false);
   assert.equal(authorized(appId,{dataDirectory:'relative'},auth),false);
   assert.equal(authorized(appId,f.selected,local(appId==='melange'?'mentat':'melange')),false);
  }finally{f.cleanup();}
 });
 test(`${appId} signed public download works locally while preserving private files and signature checks`,async()=>{
  const f=environment(appId);try{
   const account=path.join(f.original,'private-account.fixture');fs.writeFileSync(account,'private local fixture');
   f.options.authorize=async()=>local(appId);const provider=new GitHubModules(f.options);
   const candidate=await provider.prepare(f.selected);assert.ok(candidate);assert.equal(f.journal.active,null);
   assert.deepEqual(f.requests.slice(0,4),['main','pointer','release','manifest']);
   assert.equal(fs.readFileSync(account,'utf8'),'private local fixture');
   f.remote.envelope.signature=Buffer.alloc(64).toString('base64');
   await assert.rejects(provider.prepare(f.selected),/signature/);
   assert.equal(fs.readFileSync(account,'utf8'),'private local fixture');assert.equal(f.journal.active,null);
  }finally{f.cleanup();}
 });
 test(`${appId} cache authority changes with the account or selected physical root, not a new login session`,async()=>{
  const f=environment(appId);try{
   let auth=local(appId);f.options.authorize=async()=>auth;const provider=new GitHubModules(f.options);
   const first=await provider.owner(f.selected);auth.session.sessionId='44444444-4444-4444-8444-444444444444';assert.equal(await provider.owner(f.selected),first);
   const other=path.join(f.temporary,'other-workspace');fs.mkdirSync(other);assert.notEqual(await provider.owner({dataDirectory:other}),first);
   auth.identity.accountId='55555555-5555-4555-8555-555555555555';auth.session.accountId=auth.identity.accountId;assert.notEqual(await provider.owner(f.selected),first);
   auth.session=null;await assert.rejects(provider.owner(f.selected),/local access/);assert.deepEqual(f.requests,[]);
  }finally{f.cleanup();}
 });
}
