'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const path=require('node:path');
const os=require('node:os');
const {authorized}=require('../github-module-protocol.cjs');
const {GitHubModuleController,registerModuleDataIPC,sanitizeModuleStatus,STATUS_EVENT}=require('../github-module-controller.cjs');

const tick=()=>new Promise(resolve=>setImmediate(resolve));
function deferred(){let resolve;const promise=new Promise(done=>{resolve=done;});return {promise,resolve};}
function approval(appId='melange'){
 const grant={appId,grantId:'fixture-grant',accountIdentity:'fixture-owner'};
 return {accepted:{revoked:false,grant},owner:{mode:'existing-owner',appId,grantId:grant.grantId,accountIdentity:grant.accountIdentity,
  dataBindings:[{districtId:null,localUserId:null,localUsername:null,dataRootHash:'a'.repeat(64)}]}};
}
function candidate(appId,selected,phase='ready'){
 return {schemaVersion:1,appId,repository:'pjg93-222/'+appId,catalogueSequence:2,releaseTag:'module-data-2026-10-21',
  pointerDigest:'b'.repeat(64),manifestSha256:'c'.repeat(64),snapshotRoot:path.join(os.tmpdir(),'private-fixture-cache'),
  effectiveConfiguration:{...selected,ownerGitHubModuleData:{fixture:true}},
  status:{phase,cached:true,catalogueSequence:2,releaseTag:'module-data-2026-10-21',verifiedAt:'2026-10-21T23:00:00.000Z'}};
}
function fixture(options={}){
 const appId=options.appId||'melange',calls=[],states=[],timer={unref(){calls.push('timer-unref');}};
 let selected={dataDirectory:path.join(os.tmpdir(),'module-original-fixture')},authorization=approval(appId),healthy=false,canStage=true,timerCallback;
 let active='previous-active';
 const provider={
  async prepare(value,{signal,onStatus}){calls.push(['prepare',value,signal]);onStatus({phase:'verifying',cached:true});return candidate(appId,value);},
  async stage(value,{signal,onStatus}){calls.push(['stage',value,signal]);onStatus({phase:'downloading',cached:true,totalBytes:100,receivedBytes:100});return candidate(appId,value,'update-ready');},
  async commitActive(value,original,{signal,beforeCommit}){calls.push(['commit',value,original,signal]);beforeCommit();active=value.manifestSha256;return candidate(appId,original);}
 };
 const controller=new GitHubModuleController({appId,getSelected:()=>selected,
  createProvider:()=>{calls.push('create');return provider;},
  authorize:async value=>{calls.push(['authorize',value]);return authorization;},
  canStage:()=>canStage,canCommit:()=>healthy,
  keepAwake:()=>{calls.push('awake');return()=>calls.push('release');},onStatus:value=>states.push(value),
  setInterval:(callback,ms)=>{timerCallback=callback;calls.push(['interval',ms]);return timer;},
  clearInterval:value=>{assert.equal(value,timer);calls.push('timer-clear');},...options.controller});
 assert.equal(authorized(appId,selected,authorization),true);
 return {controller,provider,calls,states,get selected(){return selected;},set selected(value){selected=value;},
  get authorization(){return authorization;},set authorization(value){authorization=value;},
  get active(){return active;},set healthy(value){healthy=value;},set canStage(value){canStage=value;},timer:()=>timerCallback()};
}

test('startup prepares an immutable native candidate and activates only after the health guard',async()=>{
 const f=fixture(),original=structuredClone(f.selected);
 const prepared=await f.controller.prepare({configuration:{dataDirectory:'ignored renderer value'}});
 assert.deepEqual(f.selected,original);assert.equal(f.active,'previous-active');
 assert.ok(Object.isFrozen(prepared)&&Object.isFrozen(prepared.effectiveConfiguration));
 assert.throws(()=>{prepared.snapshotRoot='altered';},TypeError);
 assert.equal(f.calls.find(item=>Array.isArray(item)&&item[0]==='prepare')[1].dataDirectory,original.dataDirectory);
 await assert.rejects(f.controller.commitActive(prepared),{code:'transition'});assert.equal(f.active,'previous-active');
 f.healthy=true;const committed=await f.controller.commitActive(prepared);
 assert.equal(f.active,committed.manifestSha256);assert.deepEqual(f.selected,original);
 await assert.rejects(f.controller.commitActive(prepared),{code:'context'});f.controller.shutdown();
});

test('background staging returns only public status and cannot activate a snapshot',async()=>{
 const f=fixture();f.healthy=true;
 const state=await f.controller.stage();
 assert.equal(state.phase,'update-ready');assert.equal(state.catalogueSequence,2);assert.equal(state.canRefresh,true);
 assert.equal(f.active,'previous-active');assert.equal(state.effectiveConfiguration,undefined);assert.equal(state.snapshotRoot,undefined);
 await assert.rejects(f.controller.commitActive(state),{code:'context'});
 assert.equal(f.calls.some(item=>Array.isArray(item)&&item[0]==='commit'),false);f.controller.shutdown();
});

test('missing compiled adapters report unsupported without claiming that data was prepared',async()=>{
 const f=fixture({controller:{createProvider:()=>null}});
 assert.equal(await f.controller.prepare(),null);
 const state=await f.controller.info();assert.equal(state.phase,'unsupported');assert.equal(state.cached,false);assert.equal(state.canRefresh,false);
 assert.equal(f.active,'previous-active');f.controller.shutdown();
});

test('queued work obtains current owner approval after an earlier download and refuses revocation',async()=>{
 const f=fixture(),hold=deferred();
 f.provider.prepare=async value=>{f.calls.push('held-prepare');await hold.promise;return candidate('melange',value);};
 const opening=f.controller.prepare();const openingResult=opening.catch(error=>error);await tick();
 assert.equal(await f.controller.stage({skipIfBusy:true}),null);
 const queued=f.controller.stage();f.authorization={...f.authorization,accepted:{...f.authorization.accepted,revoked:true}};
 hold.resolve();assert.equal((await openingResult).code,'authorization');assert.equal(await queued,null);
 assert.equal(f.calls.some(item=>Array.isArray(item)&&item[0]==='stage'),false);assert.equal(f.active,'previous-active');
 assert.ok(f.calls.filter(item=>Array.isArray(item)&&item[0]==='authorize').length>=3);f.controller.shutdown();
});

test('queued and in-flight work cannot follow a changed selected workspace',async()=>{
 const f=fixture(),hold=deferred();f.provider.prepare=async value=>{await hold.promise;return candidate('melange',value);};
 const opening=f.controller.prepare().catch(error=>error);await tick();const queued=f.controller.stage().catch(error=>error);
 f.selected={dataDirectory:path.join(os.tmpdir(),'different-original-fixture')};hold.resolve();
 assert.equal((await opening).code,'context');assert.equal((await queued).code,'context');assert.equal(f.active,'previous-active');
 assert.equal(f.calls.some(item=>Array.isArray(item)&&item[0]==='stage'),false);f.controller.shutdown();
});

test('a workspace change during asynchronous authorization never constructs the provider',async()=>{
 const gate=deferred();let f;
 f=fixture({controller:{authorize:async()=>{await gate.promise;return approval();}}});
 const preparing=f.controller.prepare().catch(error=>error);await tick();f.selected={dataDirectory:path.join(os.tmpdir(),'changed-at-gate')};gate.resolve();
 assert.equal((await preparing).code,'context');assert.equal(f.calls.includes('create'),false);f.controller.shutdown();
});

test('recipients, revoked or mismatched approvals and non-null district bindings never create a provider',async()=>{
 const alterations=[value=>({...value,owner:null}),value=>({...value,accepted:{...value.accepted,revoked:true}}),
  value=>({...value,owner:{...value.owner,appId:'mentat'}}),value=>({...value,owner:{...value.owner,grantId:'other'}}),
  value=>({...value,owner:{...value.owner,accountIdentity:'other'}}),
  value=>({...value,owner:{...value.owner,dataBindings:[{...value.owner.dataBindings[0],districtId:'co-05'}]}})];
 for(const alter of alterations){const f=fixture();f.authorization=alter(f.authorization);assert.equal(await f.controller.prepare(),null);assert.equal(await f.controller.stage(),null);assert.equal(f.calls.includes('create'),false);f.controller.shutdown();}
});

test('native settings cannot inject an effective cache configuration into original-root authorization',async()=>{
 for(const field of ['ownerGitHubData','ownerGitHubModuleData','githubModuleData','effectiveConfiguration','snapshotRoot']){
  const f=fixture();f.selected={...f.selected,[field]:{path:'injected'}};
  await assert.rejects(f.controller.prepare(),{code:'authorization'});assert.equal(f.calls.includes('create'),false);f.controller.shutdown();
 }
 const f=fixture();f.selected={dataDirectory:'relative'};assert.equal(await f.controller.prepare(),null);assert.equal(f.calls.includes('create'),false);f.controller.shutdown();
});

test('provider failure preserves active data, releases sleep protection and permits a later retry',async()=>{
 const f=fixture();f.provider.prepare=async()=>{const error=new Error('C:/private/account and raw response');error.reason='storage';throw error;};
 await assert.rejects(f.controller.prepare(),error=>error.code==='storage'&&!/private|account|response/.test(error.message));
 assert.equal(f.active,'previous-active');assert.equal(f.controller.busy,false);assert.equal(f.calls.at(-1),'release');
 f.provider.prepare=async value=>candidate('melange',value);assert.ok(await f.controller.prepare());f.controller.shutdown();
});

test('failed activation preserves prior active data and the native caller can retry the same prepared snapshot',async()=>{
 const f=fixture(),prepared=await f.controller.prepare();f.healthy=true;
 f.provider.commitActive=async()=>{throw new Error('private activation detail');};
 await assert.rejects(f.controller.commitActive(prepared),{code:'integrity'});assert.equal(f.active,'previous-active');
 let committed=false;f.provider.commitActive=async value=>{committed=true;return value;};
 await f.controller.commitActive(prepared);assert.equal(committed,true);f.controller.shutdown();
});

test('only this controller prepared object identity can be committed in its original context',async()=>{
 const f=fixture(),prepared=await f.controller.prepare();f.healthy=true;
 await assert.rejects(f.controller.commitActive(structuredClone(prepared)),{code:'context'});
 f.selected={dataDirectory:path.join(os.tmpdir(),'changed-before-commit')};
 await assert.rejects(f.controller.commitActive(prepared),{code:'context'});assert.equal(f.active,'previous-active');f.controller.shutdown();
});

test('wrong-app and malformed provider candidates cannot become startup capabilities',async()=>{
 for(const alter of [value=>({...value,appId:'mentat'}),value=>({...value,repository:'other/repository'}),value=>({...value,manifestSha256:'bad'}),value=>({...value,status:{phase:'ready',appId:'mentat'}}),
  value=>({...value,snapshotRoot:'relative'}),value=>({...value,status:{phase:'unsupported'}}),value=>({...value,status:{...value.status,catalogueSequence:99}})]){
  const f=fixture();f.provider.prepare=async selected=>alter(candidate('melange',selected));
  await assert.rejects(f.controller.prepare(),{code:'integrity'});assert.equal(f.active,'previous-active');f.controller.shutdown();
 }
});

test('a lost native activation lease is checked again before the provider can commit',async()=>{
 let checks=0;const f=fixture({controller:{canCommit:()=>++checks===1}}),prepared=await f.controller.prepare();
 await assert.rejects(f.controller.commitActive(prepared),{code:'transition'});
 assert.equal(checks,2);assert.equal(f.calls.some(value=>Array.isArray(value)&&value[0]==='commit'),false);assert.equal(f.active,'previous-active');f.controller.shutdown();
});

test('a context or health-lease change during the provider rehash is refused before its active write',async()=>{
 for(const change of ['context','transition']){
  const f=fixture(),hold=deferred(),prepared=await f.controller.prepare();f.healthy=true;let entered=false,written=false;
  f.provider.commitActive=async(value,_original,{beforeCommit})=>{entered=true;await hold.promise;beforeCommit();written=true;return value;};
  const committing=f.controller.commitActive(prepared).catch(error=>error);await tick();assert.equal(entered,true);
  if(change==='context')f.selected={dataDirectory:path.join(os.tmpdir(),'changed-during-rehash')};else f.healthy=false;
  hold.resolve();assert.equal((await committing).code,change);assert.equal(written,false);assert.equal(f.active,'previous-active');f.controller.shutdown();
 }
});

test('cancellation while the native gate awaits is reported as cancellation and never constructs a provider',async()=>{
 const gate=deferred(),cancel=new AbortController();
 const f=fixture({controller:{authorize:async()=>{await gate.promise;throw new Error('private cancelled gate');}}});
 const preparing=f.controller.prepare({signal:cancel.signal}).catch(error=>error);await tick();cancel.abort();gate.resolve();
 assert.equal((await preparing).code,'cancelled');assert.equal(f.calls.includes('create'),false);f.controller.shutdown();
});

test('cancellation after download and cancellation while queued cannot activate or stage data',async()=>{
 const f=fixture(),hold=deferred(),cancel=new AbortController();
 f.provider.prepare=async selected=>{await hold.promise;return candidate('melange',selected);};
 const opening=f.controller.prepare({signal:cancel.signal}).catch(error=>error);await tick();cancel.abort();hold.resolve();
 assert.equal((await opening).code,'cancelled');assert.equal(f.active,'previous-active');f.controller.shutdown();
 const g=fixture(),later=deferred(),queuedCancel=new AbortController();g.provider.prepare=async selected=>{await later.promise;return candidate('melange',selected);};
 const preparing=g.controller.prepare();await tick();const queued=g.controller.stage({signal:queuedCancel.signal}).catch(error=>error);queuedCancel.abort();later.resolve();await preparing;
 assert.equal((await queued).code,'cancelled');assert.equal(g.calls.some(item=>Array.isArray(item)&&item[0]==='stage'),false);g.controller.shutdown();
});

test('shutdown cancels current and queued work, clears its timer and stops status publication',async()=>{
 const f=fixture(),hold=deferred();let signal;
 f.provider.prepare=async(selected,options)=>{signal=options.signal;await hold.promise;options.onStatus({phase:'ready',snapshotRoot:'private'});return candidate('melange',selected);};
 const opening=f.controller.prepare().catch(error=>error);await tick();const queued=f.controller.stage().catch(error=>error);
 f.controller.shutdown();const count=f.states.length;assert.equal(signal.aborted,true);hold.resolve();
 assert.equal((await opening).code,'cancelled');assert.equal((await queued).code,'cancelled');assert.equal(f.states.length,count);
 assert.equal(f.calls.filter(value=>value==='timer-clear').length,1);f.controller.shutdown();
 await assert.rejects(f.controller.prepare(),{code:'cancelled'});assert.equal(f.active,'previous-active');
});

test('the five-minute timer can stage only, honors the native busy guard and never commits',async()=>{
 const f=fixture();assert.deepEqual(f.calls[0],['interval',300000]);assert.ok(f.calls.includes('timer-unref'));
 f.timer();await f.controller.tail;assert.equal(f.active,'previous-active');assert.equal(f.calls.filter(value=>Array.isArray(value)&&value[0]==='stage').length,1);
 f.canStage=false;f.timer();await f.controller.tail;assert.equal(f.calls.filter(value=>Array.isArray(value)&&value[0]==='stage').length,1);
 assert.equal(f.calls.some(value=>Array.isArray(value)&&value[0]==='commit'),false);f.controller.shutdown();
});

test('status reads reauthorize and never expose another context or a revoked owner status',async()=>{
 const f=fixture();await f.controller.prepare();assert.equal((await f.controller.info()).phase,'ready');
 f.authorization={...f.authorization,accepted:{...f.authorization.accepted,revoked:true}};
 assert.equal(await f.controller.info(),null);assert.equal(f.active,'previous-active');f.controller.shutdown();
});

test('public status uses fixed app/repository and bounded scalar fields without private details',()=>{
 const state=sanitizeModuleStatus('mentat',{phase:'ready',appId:'mentat',repository:'pjg93-222/Mentat',catalogueSequence:3,releaseTag:'module-data-2026-10-21',
  message:'C:/private/path account-id raw error',snapshotRoot:'secret',owner:{grantId:'secret'},effectiveConfiguration:{secret:true},
  checkedAt:'not a timestamp',verifiedAt:'2026-10-21T23:00:00.000Z',receivedBytes:101,totalBytes:100,updateAvailable:true},{canRefresh:true});
 assert.equal(state.repository,'pjg93-222/mentat');assert.equal(state.catalogueSequence,3);assert.equal(state.canRefresh,true);
 assert.equal(state.checkedAt,undefined);assert.equal(state.receivedBytes,undefined);assert.equal(state.verifiedAt,'2026-10-21T23:00:00.000Z');
 assert.doesNotMatch(JSON.stringify(state),/secret|private|grant|effectiveConfiguration|snapshotRoot|account-id|raw error/);
 assert.equal(sanitizeModuleStatus('mentat',{phase:'ready',appId:'melange'}),null);
 assert.equal(sanitizeModuleStatus('mentat',{phase:'ready',repository:'other/repository'}),null);
 assert.equal(sanitizeModuleStatus('melange',{phase:'ready',totalBytes:Infinity,catalogueSequence:-1}).totalBytes,undefined);
 assert.throws(()=>sanitizeModuleStatus('terrier',{}),/Unsupported/);
});

test('fixed IPC denies untrusted frames before reads, ignores injected arguments and strips status details',async()=>{
 const handlers=new Map(),trusted={},calls=[];
 registerModuleDataIPC({handle:(key,callback)=>handlers.set(key,callback)},{appId:'melange',runtimeOnly:event=>{if(event!==trusted)throw new Error('private profile path');},
  info:()=>{calls.push('info');return {phase:'ready',snapshotRoot:'private',message:'private',canRefresh:true};},
  refresh:(...args)=>{assert.deepEqual(args,[]);calls.push('stage');return {phase:'update-ready',effectiveConfiguration:{private:true}};},canRefresh:()=>true});
 await assert.rejects(handlers.get('desktop:module-data')({}),/^Error: Untrusted application request\.$/);
 await assert.rejects(handlers.get('desktop:module-data-refresh')({}),/^Error: Untrusted application request\.$/);assert.deepEqual(calls,[]);
 const info=await handlers.get('desktop:module-data')(trusted,{appId:'mentat',configuration:{dataDirectory:'injected'}});
 assert.equal(info.appId,'melange');assert.equal(info.snapshotRoot,undefined);assert.doesNotMatch(info.message,/private/);
 const refreshed=await handlers.get('desktop:module-data-refresh')(trusted,{url:'https://injected.invalid',path:'injected'});
 assert.equal(refreshed.phase,'update-ready');assert.equal(refreshed.effectiveConfiguration,undefined);assert.deepEqual(calls,['info','stage']);
 assert.equal(handlers.has('desktop:module-data-commit'),false);assert.equal(STATUS_EVENT,'desktop:module-data-status');
});

test('IPC masks provider and refresh-eligibility errors and does not run blocked staging',async()=>{
 for(const eligible of [()=>false,()=>{throw new Error('private lease detail');}]){
  const handlers=new Map();registerModuleDataIPC({handle:(key,value)=>handlers.set(key,value)},{appId:'mentat',runtimeOnly:()=>{},info:()=>null,refresh:()=>assert.fail('blocked refresh'),canRefresh:eligible});
  await assert.rejects(handlers.get('desktop:module-data-refresh')({}),error=>!error.message.includes('private')&&/unavailable/.test(error.message));
 }
 const handlers=new Map();registerModuleDataIPC({handle:(key,value)=>handlers.set(key,value)},{appId:'mentat',runtimeOnly:()=>{},info:()=>{throw new Error('private info');},refresh:()=>{throw new Error('private transfer');},canRefresh:()=>true});
 await assert.rejects(handlers.get('desktop:module-data')({}),/^Error: Module data status is unavailable\.$/);
 await assert.rejects(handlers.get('desktop:module-data-refresh')({}),/^Error: Module data check could not be completed\.$/);
});

test('observer and sleep-protection cleanup failures cannot leak private errors or change the transaction',async()=>{
 const f=fixture({controller:{onStatus:()=>{throw new Error('private renderer');},keepAwake:()=>()=>{throw new Error('private power blocker');}}});
 assert.ok(await f.controller.prepare());assert.equal(f.controller.busy,false);assert.equal(f.active,'previous-active');f.controller.shutdown();
});

test('unsupported applications and invalid scheduling are refused before a controller can run',()=>{
 assert.throws(()=>new GitHubModuleController({appId:'terrier'}),/Unsupported/);
 assert.throws(()=>fixture({controller:{intervalMs:0}}),/Invalid module data check interval/);
});

test('actual signed provider preparation/staging/activation preserves original settings for both applications',async t=>{
 const {GitHubModules}=require('../github-modules.cjs'),{environment}=require('./fixtures/github-module-fixture.cjs');
 for(const appId of ['melange','mentat']){
  const env=environment(appId),original=structuredClone(env.selected),provider=new GitHubModules(env.options);let healthy=false;
  const controller=new GitHubModuleController({appId,getSelected:()=>env.selected,authorize:env.options.authorize,createProvider:()=>provider,
   canStage:()=>true,canCommit:()=>healthy,setInterval:()=>null,clearInterval:()=>{}});
  t.after(()=>{controller.shutdown();env.cleanup();});
  const prepared=await controller.prepare();assert.equal(env.journal.active,null);assert.equal(prepared.status.phase,'ready');
  const staged=await controller.stage();assert.equal(staged.phase,'update-ready');assert.equal(env.journal.active,null);
  assert.doesNotMatch(JSON.stringify(staged),/snapshotRoot|effectiveConfiguration|grantId|accountIdentity/);
  healthy=true;await controller.commitActive(prepared);assert.equal(env.journal.active.manifestSha256,prepared.manifestSha256);
  assert.deepEqual(env.selected,original);assert.equal(Object.hasOwn(env.selected,'ownerGitHubModuleData'),false);
  const unchanged=await controller.stage();assert.equal(unchanged.phase,'ready');assert.equal(unchanged.updateAvailable,undefined);
  env.network='unreachable';const offline=await controller.prepare();assert.equal(offline.status.phase,'offline');
  assert.equal(env.journal.active.manifestSha256,prepared.manifestSha256);
 }
});

test('actual provider pre-write guard prevents activation when the native health lease changes during rehash',async t=>{
 const {GitHubModules}=require('../github-modules.cjs'),{environment}=require('./fixtures/github-module-fixture.cjs');
 const env=environment('mentat'),provider=new GitHubModules(env.options);let healthy=true;
 const controller=new GitHubModuleController({appId:'mentat',getSelected:()=>env.selected,authorize:env.options.authorize,createProvider:()=>provider,
  canStage:()=>true,canCommit:()=>healthy,setInterval:()=>null,clearInterval:()=>{}});
 t.after(()=>{controller.shutdown();env.cleanup();});
 const prepared=await controller.prepare(),hold=deferred(),entered=deferred(),validate=provider.validateSnapshot.bind(provider);
 provider.validateSnapshot=async(...args)=>{entered.resolve();await hold.promise;return validate(...args);};
 const committing=controller.commitActive(prepared).catch(error=>error);await entered.promise;healthy=false;hold.resolve();
 const error=await committing;assert.equal(error.code,'transition');assert.equal(env.journal.active,null);
 assert.equal(env.journal.staged.manifestSha256,prepared.manifestSha256);assert.equal(env.journal.highwater.catalogSequence,1);
});
