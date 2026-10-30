'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),path=require('node:path'),{EventEmitter}=require('node:events');
const protocol=require('../github-module-protocol.cjs'),{GitHubModules}=require('../github-modules.cjs');
const {validateModuleBinding}=require('../module-data-binding.cjs');
const {GitHubModuleTransport}=require('../github-module-transport.cjs');
const {CHANNEL}=require('../workspace-data-contract.cjs');
const {environment,signed}=require('./fixtures/github-module-fixture.cjs');
function fixture(t,appId){
 const pub=environment(appId),workspace=environment(appId);t.after(()=>{workspace.cleanup();pub.cleanup();});
 const remote=signed(appId,{keys:pub.remote.keys});remote.value.purpose=protocol.configuration(appId,CHANNEL.id).purpose;remote.manifest.purpose=remote.value.purpose+'sets';remote.rebind();workspace.remote=remote;
 Object.assign(workspace.options,{channel:CHANNEL.id,profile:pub.profile,cacheRoot:path.join(pub.profile,'packs',CHANNEL.cacheName),publicKeys:pub.remote.publicKeys,registry:remote.registry,
  authorize:pub.options.authorize,effectiveConfiguration:({originalSelected,source})=>({...originalSelected,[CHANNEL.sourceField]:source})});
 return {pub,workspace,remote};
}
for(const appId of ['melange','mentat']){
 test(appId+' workspace signatures cannot cross the legacy public purpose even with the same signing key',t=>{
  const {pub,remote}=fixture(t,appId);
  assert.throws(()=>protocol.pointer(appId,remote.envelope,pub.remote.publicKeys),{reason:'integrity'});
  assert.throws(()=>protocol.pointer(appId,pub.remote.envelope,pub.remote.publicKeys,{},CHANNEL.id),{reason:'integrity'});
  assert.equal(protocol.pointer(appId,remote.envelope,pub.remote.publicKeys,{},CHANNEL.id).value.purpose,appId+'-full-workspace-data');
 });
 test(appId+' public and workspace preparations keep independent caches, high-waters and immutable source bindings',async t=>{
  const {pub,workspace}=fixture(t,appId),publicProvider=new GitHubModules(pub.options),workspaceProvider=new GitHubModules(workspace.options);
  const first=await publicProvider.prepare(pub.selected),before=structuredClone(pub.journal),next=await workspaceProvider.prepare(pub.selected);
  assert.deepEqual(pub.journal,before);assert.equal(first.effectiveConfiguration.ownerGitHubWorkspaceData,undefined);assert.equal(next.effectiveConfiguration.ownerGitHubModuleData,undefined);
  assert.notEqual(first.snapshotRoot,next.snapshotRoot);assert.equal(workspace.journal.highwater.catalogSequence,1);assert.equal(pub.journal.highwater.catalogSequence,1);
  const checked=await validateModuleBinding({appId,profile:pub.profile,configuration:next.effectiveConfiguration,publicKeys:pub.remote.publicKeys,registry:workspace.options.registry,channel:CHANNEL.id});
  assert.equal(checked.snapshotRoot,next.snapshotRoot);
  await assert.rejects(validateModuleBinding({appId,profile:pub.profile,configuration:next.effectiveConfiguration,publicKeys:pub.remote.publicKeys,registry:workspace.options.registry}),{reason:'integrity'});
  const spoof=structuredClone(next.effectiveConfiguration);spoof.ownerGitHubWorkspaceData.cacheRoot=first.effectiveConfiguration.ownerGitHubModuleData.cacheRoot;
  await assert.rejects(validateModuleBinding({appId,profile:pub.profile,configuration:spoof,publicKeys:pub.remote.publicKeys,registry:workspace.options.registry,channel:CHANNEL.id}),{reason:'integrity'});
 });
 test(appId+' workspace provider cannot import an old public journal or use a public cache root',t=>{
  const {pub,workspace}=fixture(t,appId);
  assert.throws(()=>new GitHubModules({...workspace.options,previousStore:pub.store}),/cannot import public/);
  assert.throws(()=>new GitHubModules({...workspace.options,cacheRoot:pub.options.cacheRoot}),/Unapproved/);
 });
}
test('workspace transport permits only its compiled branch/path and keeps legacy raw main route unchanged',async()=>{
 const urls=[],bytes=Buffer.from('{}');
 const request=(url,options,callback)=>{assert.equal(options.rejectUnauthorized,true);urls.push(url.href);const req=new EventEmitter();req.destroy=()=>{};req.end=()=>queueMicrotask(()=>{
  const res=new(require('node:stream').PassThrough)();res.statusCode=200;res.headers={'content-length':String(bytes.length)};callback(res);res.end(bytes);
 });return req;};
 const workspace=new GitHubModuleTransport('melange',{channel:CHANNEL.id,request});await workspace.currentPointer();
 assert.deepEqual(urls,['https://raw.githubusercontent.com/pjg93-222/melange/desktop-workspace-data/docs/desktop-workspace/current.json']);
 await assert.rejects(workspace.fetch('https://raw.githubusercontent.com/pjg93-222/melange/main/docs/desktop-workspace/current.json',{limit:32768}),{reason:'integrity'});
 assert.equal(urls.length,1);const legacy=new GitHubModuleTransport('melange',{request});await legacy.currentPointer();assert.equal(urls.at(-1),'https://raw.githubusercontent.com/pjg93-222/melange/main/docs/desktop-data/current.json');
 assert.throws(()=>new GitHubModuleTransport('melange',{channel:'renderer-chosen'}),{reason:'integrity'});
});
