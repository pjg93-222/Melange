'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {ModuleDataTransition}=require('../module-data-transition.cjs');
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function deferred(){let resolve;const promise=new Promise(done=>{resolve=done;});return {promise,resolve};}
function fixture(){
 let selected={dataDirectory:'synthetic-original-root'},generation=1,runtime={child:null,origin:null,configuration:null,requestsAllowed:true};
 const transition=new ModuleDataTransition({getSelected:()=>selected,getGeneration:()=>generation,getRuntime:()=>runtime});
 const candidate=()=>Object.freeze({effectiveConfiguration:Object.freeze({...selected,ownerGitHubModuleData:{fixture:true}})});
 const health=(lease,value)=>{lease.bindCandidate(value);runtime.child={fixtureChild:true};runtime.origin='http://127.0.0.1:12345';runtime.configuration=structuredClone(lease.originalSelected);lease.markHealthy(value);};
 return {transition,candidate,health,get selected(){return selected;},set selected(value){selected=value;},get generation(){return generation;},set generation(value){generation=value;},get runtime(){return runtime;},set runtime(value){runtime=value;}};
}

test('native startup actions are exclusive and retain immutable original selection',async()=>{
 const f=fixture(),hold=deferred(),calls=[];let firstLease;
 const first=f.transition.run(async lease=>{firstLease=lease;calls.push('first');assert.ok(Object.isFrozen(lease.originalSelected));await hold.promise;calls.push('first-done');});
 await tick();const second=f.transition.run(async()=>calls.push('second'));assert.equal(f.transition.busy,true);assert.deepEqual(calls,['first']);
 hold.resolve();await Promise.all([first,second]);assert.deepEqual(calls,['first','first-done','second']);assert.equal(f.transition.busy,false);
 assert.equal(firstLease.signal.aborted,true);assert.throws(()=>firstLease.assertCurrent(),{code:'cancelled'});
});

test('an existing backend refuses a startup lease and the helper never controls that backend',async()=>{
 const f=fixture();let controlled=false;f.runtime.child={stop:()=>{controlled=true;}};
 await assert.rejects(f.transition.run(()=>assert.fail('must not run')),{code:'transition'});
 assert.equal(controlled,false);assert.ok(f.runtime.child);assert.equal(f.transition.busy,false);
});

test('queued selection, access generation and Runtime identity are bound at request time',async()=>{
 for(const kind of ['selection','generation','runtime']){
  const f=fixture(),hold=deferred();const first=f.transition.run(async()=>hold.promise).catch(error=>error);await tick();
  const second=f.transition.run(()=>assert.fail('stale request must not run')).catch(error=>error);
  if(kind==='selection')f.selected={dataDirectory:'another-original-root'};else if(kind==='generation')f.generation++;else f.runtime={...f.runtime};
  hold.resolve();assert.equal((await first).code,kind==='generation'?'authorization':'context');assert.equal((await second).code,kind==='generation'?'authorization':'context');
 }
});

test('health binding requires the exact candidate and matching healthy backend configuration',async()=>{
 const f=fixture();await f.transition.run(async lease=>{
  const prepared=f.candidate();lease.bindCandidate(prepared);
  assert.throws(()=>lease.markHealthy(prepared),{code:'transition'});
  f.runtime.child={};f.runtime.origin='http://127.0.0.1:12345';f.runtime.configuration={different:true};
  assert.throws(()=>lease.markHealthy(prepared),{code:'transition'});
  f.runtime.configuration=structuredClone(lease.originalSelected);f.runtime.requestsAllowed=false;
  assert.throws(()=>lease.markHealthy(prepared),{code:'transition'});f.runtime.requestsAllowed=true;
  assert.throws(()=>lease.markHealthy(structuredClone(prepared)),{code:'transition'});lease.markHealthy(prepared);
  assert.equal(lease.canCommit(prepared),true);assert.equal(lease.canCommit(structuredClone(prepared)),false);
  assert.throws(()=>lease.bindCandidate(f.candidate()),{code:'transition'});
 });
});

test('the health-checked child, origin and configuration must stay identical before commit',async()=>{
 for(const kind of ['child','origin','configuration','generation']){
  const f=fixture();await f.transition.run(async lease=>{
   const prepared=f.candidate();f.health(lease,prepared);assert.equal(lease.canCommit(prepared),true);
   if(kind==='child')f.runtime.child={replacement:true};else if(kind==='origin')f.runtime.origin='http://127.0.0.1:23456';
   else if(kind==='configuration')f.runtime.configuration={changed:true};else f.generation++;
   assert.equal(lease.canCommit(prepared),false);await assert.rejects(lease.commit(prepared,()=>assert.fail('must not commit')));
  }).catch(error=>{assert.equal(kind,'generation');assert.equal(error.code,'authorization');});
 }
});

test('a health-checked exact candidate can commit once and exposes the same cancellation signal',async()=>{
 const f=fixture();let count=0;
 const result=await f.transition.run(async lease=>{
  const prepared=f.candidate();f.health(lease,prepared);
  const value=await lease.commit(prepared,({signal,beforeCommit})=>{assert.equal(signal,lease.signal);assert.equal(beforeCommit(),true);count++;return 'active';});
  assert.equal(lease.canCommit(prepared),false);await assert.rejects(lease.commit(prepared,()=>assert.fail('duplicate')),{code:'transition'});return value;
 });
 assert.equal(result,'active');assert.equal(count,1);assert.ok(f.runtime.child);
});

test('invalidation during a held rehash prevents its pre-write commit guard',async()=>{
 const f=fixture(),hold=deferred(),entered=deferred();let wrote=false;
 const running=f.transition.run(async lease=>{const prepared=f.candidate();f.health(lease,prepared);await lease.commit(prepared,async({beforeCommit})=>{entered.resolve();await hold.promise;beforeCommit();wrote=true;});}).catch(error=>error);
 await entered.promise;const draining=f.transition.invalidate('context');await tick();assert.equal(wrote,false);hold.resolve();
 assert.equal((await running).code,'context');assert.deepEqual(await draining,{drained:true});assert.equal(wrote,false);assert.equal(f.transition.busy,false);
});

test('teardown waits for a protected write already in progress after its pre-write guard',async()=>{
 const f=fixture(),write=deferred(),started=deferred();let durable=false,drained=false;
 const running=f.transition.run(async lease=>{const prepared=f.candidate();f.health(lease,prepared);await lease.commit(prepared,async({beforeCommit})=>{beforeCommit();started.resolve();await write.promise;durable=true;});}).catch(error=>error);
 await started.promise;const invalidating=f.transition.invalidate('authorization').then(value=>{drained=true;return value;});
 await tick();assert.equal(drained,false);assert.equal(durable,false);assert.ok(f.runtime.child);
 await assert.rejects(f.transition.run(()=>assert.fail('draining startup')),{code:'cancelled'});
 write.resolve();assert.equal((await running).code,'authorization');await invalidating;assert.equal(durable,true);assert.equal(drained,true);assert.ok(f.runtime.child);
});

test('a forgotten commit await or caller failure cannot release a protected commit early',async()=>{
 const f=fixture(),write=deferred(),started=deferred();let finished=false;
 const running=f.transition.run(lease=>{const prepared=f.candidate();f.health(lease,prepared);lease.commit(prepared,async()=>{started.resolve();await write.promise;finished=true;});throw new Error('private caller failure');}).catch(error=>error);
 await started.promise;let drained=false;const drain=f.transition.invalidate().then(()=>{drained=true;});await tick();assert.equal(drained,false);
 write.resolve();const error=await running;await drain;assert.equal(error.code,'transition');assert.doesNotMatch(error.message,/private/);assert.equal(finished,true);
});

test('shutdown aborts current work, rejects queued requests and permanently refuses new work',async()=>{
 const f=fixture(),hold=deferred();let signal;
 const first=f.transition.run(async lease=>{signal=lease.signal;await hold.promise;lease.assertCurrent();}).catch(error=>error);await tick();
 const second=f.transition.run(()=>assert.fail('queued callback')).catch(error=>error),shutdown=f.transition.shutdown();
 assert.equal(signal.aborted,true);assert.equal(f.transition.shutdown(),shutdown);hold.resolve();
 assert.equal((await first).code,'cancelled');assert.equal((await second).code,'cancelled');assert.deepEqual(await shutdown,{drained:true});
 await assert.rejects(f.transition.run(()=>assert.fail('closed callback')),{code:'cancelled'});
});

test('a completed invalidation permits a fresh startup while old lease capabilities stay cancelled',async()=>{
 const f=fixture();let old;
 await f.transition.run(lease=>{old=lease;});await f.transition.invalidate('context');f.selected={dataDirectory:'fresh-original-root'};
 assert.equal(await f.transition.run(lease=>lease.originalSelected.dataDirectory),'fresh-original-root');assert.throws(()=>old.assertCurrent(),{code:'cancelled'});
});

test('external cancellation before acquisition or during work is honored without revealing its reason',async()=>{
 const f=fixture(),cancel=new AbortController();cancel.abort(new Error('private cancellation data'));
 await assert.rejects(f.transition.run(()=>assert.fail('cancelled request'),{signal:cancel.signal}),{code:'cancelled'});
 const later=new AbortController();await assert.rejects(f.transition.run(async lease=>{later.abort(new Error('private cancellation data'));lease.assertCurrent();},{signal:later.signal}),error=>error.code==='cancelled'&&!error.message.includes('private'));
});

test('callback and native getter failures are sanitized and a failed startup does not poison the queue',async()=>{
 const f=fixture();await assert.rejects(f.transition.run(()=>{throw new Error('C:/private/account');}),error=>error.code==='transition'&&!error.message.includes('private'));
 assert.equal(await f.transition.run(()=>42),42);
 const bad=new ModuleDataTransition({getSelected:()=>{throw new Error('private settings');},getGeneration:()=>1,getRuntime:()=>({})});
 await assert.rejects(bad.run(()=>assert.fail()),error=>!error.message.includes('private'));
 assert.throws(()=>new ModuleDataTransition({}),/Native module startup callbacks/);
});

test('the actual controller/provider protected write drains under the native startup lease before teardown',async t=>{
 const {GitHubModuleController}=require('../github-module-controller.cjs'),{GitHubModules}=require('../github-modules.cjs');
 const {environment}=require('./fixtures/github-module-fixture.cjs'),env=environment('mentat');
 const runtime={child:null,origin:null,configuration:null,requestsAllowed:true},transition=new ModuleDataTransition({getSelected:()=>env.selected,getGeneration:()=>1,getRuntime:()=>runtime});
 const write=deferred(),entered=deferred(),save=env.store.write;let leaseInMain=null,drained=false;
 env.store.write=async value=>{if(value.active){entered.resolve();await write.promise;}return save(value);};
 const provider=new GitHubModules(env.options),controller=new GitHubModuleController({appId:'mentat',getSelected:()=>env.selected,authorize:env.options.authorize,createProvider:()=>provider,
  canStage:()=>true,canCommit:candidate=>leaseInMain?.canCommit(candidate)===true,setInterval:()=>null,clearInterval:()=>{}});
 t.after(async()=>{controller.shutdown();await transition.shutdown();env.cleanup();});
 const running=transition.run(async lease=>{
  leaseInMain=lease;try{
   const prepared=await controller.prepare({signal:lease.signal});lease.bindCandidate(prepared);
   runtime.child={syntheticHealthCheckedChild:true};runtime.origin='http://127.0.0.1:12345';runtime.configuration=structuredClone(lease.originalSelected);lease.markHealthy(prepared);
   await lease.commit(prepared,()=>controller.commitActive(prepared,{signal:lease.signal}));
  }finally{leaseInMain=null;}
 }).catch(error=>error);
 await entered.promise;const invalidating=transition.invalidate('context').then(()=>{drained=true;});await tick();
 assert.equal(drained,false);assert.equal(env.journal.active,null);assert.ok(runtime.child);
 write.resolve();const error=await running;await invalidating;
 assert.equal(error.code,'cancelled');assert.equal(drained,true);assert.ok(env.journal.active);assert.ok(runtime.child);
 assert.deepEqual(env.selected,{dataDirectory:env.original});
});


test('native health requires original marker-free configuration while tracking candidate mutation separately',async()=>{
 const f=fixture();await f.transition.run(async lease=>{
  const candidate=f.candidate();lease.bindCandidate(candidate);f.runtime.child={};f.runtime.origin='http://127.0.0.1:12345';
  f.runtime.configuration=structuredClone(candidate.effectiveConfiguration);
  assert.throws(()=>lease.markHealthy(candidate),{code:'transition'},'A settings marker cannot substitute for original roots');
  f.runtime.configuration=structuredClone(lease.originalSelected);lease.markHealthy(candidate);assert.equal(lease.canCommit(candidate),true);
  candidate.effectiveConfiguration.ownerGitHubModuleData.fixture=false;
  assert.equal(lease.canCommit(candidate),false,'Exact effective/source identity is independently bound');
  await assert.rejects(lease.commit(candidate,()=>assert.fail('Mutated source must not commit')),{code:'transition'});
 });
});


test('candidate effective identity is captured before awaited native preparation, not first health',async()=>{
 const f=fixture();await f.transition.run(async lease=>{
  const candidate=f.candidate();lease.bindCandidate(candidate);candidate.effectiveConfiguration.ownerGitHubModuleData.fixture=false;
  f.runtime.child={};f.runtime.origin='http://127.0.0.1:12345';f.runtime.configuration=structuredClone(lease.originalSelected);
  assert.throws(()=>lease.markHealthy(candidate),{code:'transition'});assert.equal(lease.canCommit(candidate),false);
 });
});
