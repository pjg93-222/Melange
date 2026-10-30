'use strict';
// Generated signed payloads and a test-only native boundary; no production
// Python installation, actual model coverage or recipient policy is inferred.
const test=require('node:test'),assert=require('node:assert/strict'),path=require('node:path');
const {WorkspaceDataStartup,workspaceHealthBinding}=require('../workspace-data-startup.cjs');
const {moduleHealthBinding}=require('../module-data-startup.cjs');
const {programFingerprint}=require('../module-data-runtime-boundary.cjs');
const {GitHubModules}=require('../github-modules.cjs'),protocol=require('../github-module-protocol.cjs');
const {isDataStartupFailure,dataStartupFailure}=require('../startup-failure.cjs');
const {environment,signed,sha}=require('./fixtures/github-module-fixture.cjs');
function deferred(){let resolve;const promise=new Promise(done=>{resolve=done;});return {promise,resolve};}
function fixture(t,{appId='mentat',changeBoundary=()=>{}}={}){
 const pub=environment(appId),workspace=environment(appId),events=[];let selected=pub.selected,generation=0,programValid=true;
 const remote=signed(appId,{keys:pub.remote.keys});remote.value.purpose=protocol.configuration(appId,'workspace-v1').purpose;remote.manifest.purpose=remote.value.purpose+'sets';remote.rebind();workspace.remote=remote;
 Object.assign(workspace.options,{channel:'workspace-v1',profile:pub.profile,cacheRoot:path.join(pub.profile,'packs','github-workspace-data'),publicKeys:pub.remote.publicKeys,registry:remote.registry,authorize:pub.options.authorize,
  effectiveConfiguration:({originalSelected,source})=>({...originalSelected,ownerGitHubWorkspaceData:source})});
 const programFiles=[{root:'source',path:'synthetic.py',bytes:0,sha256:sha(Buffer.alloc(0))}],base={schemaVersion:1,appId,programFiles,programFingerprint:programFingerprint(programFiles),startupTimeoutMs:1000,publicReaders:['synthetic-data-reader'],privateBoundaries:['original-data','original-state']};
 const publicContract={...base,contractId:appId+'.public-data.v1',registry:pub.remote.registry,requiredKinds:Object.keys(pub.remote.registry)},workspaceContract={...base,contractId:appId+'.workspace.v1',registry:remote.registry,requiredKinds:Object.keys(remote.registry)};
 const runtime={child:null,origin:null,configuration:null,requestsAllowed:true,async start(){events.push('ordinary');return 'http://127.0.0.1:43212';},async stop(){events.push('stop');this.child=null;this.origin=null;this.configuration=null;this.requestsAllowed=false;}};
 const boundary={programFingerprint:base.programFingerprint,workspaceProgramFingerprint:base.programFingerprint,
  supportsContracts:(left,right)=>programValid&&left===publicContract&&right===workspaceContract,
  async start({runtime,configuration,publicCandidate,workspaceCandidate,claimChild}){events.push('start');runtime.configuration=structuredClone(configuration);runtime.child={pid:1234};runtime.origin='http://127.0.0.1:43212';runtime.requestsAllowed=true;claimChild(runtime.child);
   return {moduleData:moduleHealthBinding(publicCandidate,publicContract),workspaceData:workspaceHealthBinding(workspaceCandidate,workspaceContract),child:runtime.child,origin:runtime.origin};},
  async verifyHealth(){events.push('health');return true;}};
 changeBoundary(boundary);
 for(const [name,data] of [['public',pub],['workspace',workspace]]){const write=data.store.write;data.store.write=async value=>{if(value.active)events.push(name+'-active');return write(value);};}
 const startup=new WorkspaceDataStartup({appId,getSelected:()=>selected,getGeneration:()=>generation,getRuntime:()=>runtime,authorize:pub.options.authorize,
  publicContract,workspaceContract,boundary,canStage:()=>Boolean(runtime.child)&&runtime.requestsAllowed!==false,
  createPublicProvider:()=>{events.push('public-provider');return new GitHubModules(pub.options);},createWorkspaceProvider:()=>{events.push('workspace-provider');return new GitHubModules(workspace.options);},
  setInterval:()=>({unref(){}}),clearInterval:()=>{},onStatus:()=>{}});
 t.after(async()=>{await startup.shutdown();workspace.cleanup();pub.cleanup();});
 return {pub,workspace,events,runtime,startup,boundary,publicContract,workspaceContract,get selected(){return selected;},set selected(value){selected=value;},set generation(value){generation=value;},set programValid(value){programValid=value;}};
}
for(const appId of ['melange','mentat'])test(appId+' commits both signed channels only after the same owned child has bound health',async t=>{
 const f=fixture(t,{appId});assert.equal(await f.startup.start(f.selected,await f.pub.options.authorize()),'http://127.0.0.1:43212');
 assert.deepEqual(f.events,['workspace-provider','public-provider','start','health','public-active','workspace-active']);assert.ok(f.pub.journal.active);assert.ok(f.workspace.journal.active);
 assert.equal(f.runtime.configuration.ownerGitHubModuleData,undefined);assert.equal(f.runtime.configuration.ownerGitHubWorkspaceData,undefined);
});
test('cold workspace network failure starts no child and preserves native retry metadata',async t=>{
 const f=fixture(t);f.workspace.transport.currentPointer=async()=>{throw Object.assign(new Error('proxy'),{reason:'proxy',retryableNetwork:true,retryAfterMs:60000});};
 const error=await f.startup.start(f.selected,await f.pub.options.authorize()).catch(error=>error);
 assert.ok(isDataStartupFailure(error));assert.equal(error.retryable,true);assert.equal(error.retryAfterMs,60000);assert.equal(f.runtime.child,null);assert.equal(f.events.includes('public-provider'),false);assert.equal(f.workspace.journal?.active??null,null);
});
test('a failed second activation write is data-blocked, retains both high-waters and stops only the owned child',async t=>{
 const f=fixture(t),write=f.workspace.store.write;f.workspace.store.write=async value=>{if(value.active)throw new Error('Synthetic protected write failed');return write(value);};
 const error=await f.startup.start(f.selected,await f.pub.options.authorize()).catch(error=>error);assert.ok(isDataStartupFailure(error));assert.equal(error.retryable,false);
 assert.ok(f.pub.journal.active);assert.equal(f.workspace.journal.active,null);assert.equal(f.pub.journal.highwater.catalogSequence,1);assert.equal(f.workspace.journal.highwater.catalogSequence,1);assert.equal(f.runtime.child,null);assert.equal(f.events.at(-1),'stop');
 f.workspace.store.write=write;await f.startup.start(f.selected,await f.pub.options.authorize());assert.ok(f.pub.journal.active);assert.ok(f.workspace.journal.active);
});
test('workspace health digest mismatch never commits either channel',async t=>{
 const f=fixture(t,{changeBoundary:boundary=>{const start=boundary.start;boundary.start=async options=>{const value=await start(options);return {...value,workspaceData:{...value.workspaceData,sourceDigest:'f'.repeat(64)}};};}});
 await assert.rejects(f.startup.start(f.selected,await f.pub.options.authorize()));assert.equal(f.pub.journal.active,null);assert.equal(f.workspace.journal.active,null);assert.equal(f.runtime.child,null);
});
test('a typed native intake rejection after claiming a child does not turn into a binary failure',async t=>{
 const f=fixture(t,{changeBoundary:boundary=>{const start=boundary.start;boundary.start=async options=>{await start(options);throw dataStartupFailure({reason:'integrity'});};}});
 const error=await f.startup.start(f.selected,await f.pub.options.authorize()).catch(error=>error);assert.ok(isDataStartupFailure(error));assert.equal(f.runtime.child,null);assert.equal(f.pub.journal.active,null);assert.equal(f.workspace.journal.active,null);
});
test('program mutation after an external network failure is never classified as retryable data',async t=>{
 const f=fixture(t);f.workspace.transport.currentPointer=async()=>{f.programValid=false;throw Object.assign(new Error('timeout'),{reason:'timeout',retryableNetwork:true});};
 const error=await f.startup.start(f.selected,await f.pub.options.authorize()).catch(error=>error);assert.equal(isDataStartupFailure(error),false);assert.equal(f.runtime.child,null);
});
test('staging both channels while an existing backend is open cannot activate or replace it',async t=>{
 const f=fixture(t),existing={userWork:true};f.runtime.child=existing;await f.startup.stage();assert.equal(f.runtime.child,existing);assert.equal(f.events.includes('start'),false);assert.equal(f.events.includes('stop'),false);assert.equal(f.pub.journal.active,null);assert.equal(f.workspace.journal.active,null);assert.ok(f.pub.journal.staged);assert.ok(f.workspace.journal.staged);
});
test('shutdown drains a cold workspace transfer and cannot spawn after cancellation',async t=>{
 const f=fixture(t),entered=deferred(),release=deferred(),segment=f.workspace.transport.segment;
 f.workspace.transport.segment=async(...args)=>{entered.resolve();await release.promise;return segment(...args);};
 const opening=f.startup.start(f.selected,await f.pub.options.authorize()).catch(error=>error);await entered.promise;let done=false;const shutdown=f.startup.shutdown().then(()=>{done=true;});
 await new Promise(resolve=>setImmediate(resolve));assert.equal(done,false);release.resolve();assert.equal((await opening).code,'cancelled');await shutdown;assert.equal(f.runtime.child,null);assert.equal(f.events.includes('start'),false);
});
