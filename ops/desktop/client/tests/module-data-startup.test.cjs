'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {compiledApplicationContract}=require('../module-data-startup.cjs');
const {startupFixture}=require('./fixtures/module-startup-fixture.cjs');
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function deferred(){let resolve;const promise=new Promise(done=>{resolve=done;});return {promise,resolve};}
test('a packaged required installed contract cannot fall back to unverified ordinary startup',async t=>{
 const f=startupFixture(t,{production:true,changeOptions:options=>{options.requireInstalledContract=true;}});
 await assert.rejects(f.startup.start(f.selected,null),{code:'program'});assert.deepEqual(f.events,[]);assert.equal(f.runtime.child,null);
});

for(const appId of ['melange','mentat']){
 test(`${appId} production gate preserves ordinary startup and reports unsupported without data/auth/provider work`,async t=>{
  const f=startupFixture(t,{appId,production:true,changeOptions:options=>{options.authorize=()=>assert.fail('No module owner lookup');options.createProvider=()=>assert.fail('No module provider');}}),original=structuredClone(f.selected);
  assert.equal(compiledApplicationContract(appId),null);assert.equal(f.startup.supported,false);
  assert.equal((await f.startup.info()).phase,'unsupported');assert.equal((await f.startup.stage()).canRefresh,false);
  assert.equal(await f.startup.start(f.selected,null),'http://127.0.0.1:43212');
  assert.deepEqual(f.events,['ordinary-start']);assert.deepEqual(f.selected,original);assert.equal(f.data.journal,null);assert.deepEqual(f.data.requests,[]);
 });
 test(`${appId} generated signed fixture commits only after exact native test-bound health`,async t=>{
  const f=startupFixture(t,{appId}),account=path.join(f.data.original,'account.fixture');fs.writeFileSync(account,'private original fixture');
  const configuration=structuredClone(f.selected),approved=await f.data.options.authorize();
  assert.equal(await f.startup.start(configuration,approved),'http://127.0.0.1:43212');
  assert.deepEqual(f.events,['provider','module-start','module-health']);assert.equal(f.data.journal.active.catalogSequence,1);
  assert.deepEqual(f.selected,configuration);assert.equal(fs.readFileSync(account,'utf8'),'private original fixture');
  assert.ok(f.states.every(state=>!('snapshotRoot' in state)&&!('effectiveConfiguration' in state)));
 });
}

for(const kind of ['missing-boundary','wrong-program','unsupported-program']){
 test(`a complete-looking contract cannot enable activation with ${kind}`,async t=>{
  const f=startupFixture(t,{changeOptions:options=>{if(kind==='missing-boundary')options.boundary=null;
   if(kind==='wrong-program')options.boundary.programFingerprint='b'.repeat(64);
   if(kind==='unsupported-program')options.boundary.supportsContract=()=>false;}});
  assert.equal(f.startup.supported,false);await f.startup.start(f.selected,await f.data.options.authorize());
  assert.deepEqual(f.events,['ordinary-start']);assert.equal(f.data.journal,null);assert.deepEqual(f.data.requests,[]);
 });
}

test('a saved settings marker still refuses before any module or ordinary launch action',async t=>{
 const f=startupFixture(t);let reads=0;const selected={...f.selected};Object.defineProperty(selected,'ownerGitHubModuleData',{get(){reads++;throw new Error('untrusted getter');}});
 await assert.rejects(f.startup.start(selected,await f.data.options.authorize()),/GitHub module data startup is unavailable/);
 assert.equal(reads,0);assert.deepEqual(f.events,[]);assert.equal(f.data.journal,null);
});

test('a recipient keeps the ordinary path without preparing owner data',async t=>{
 const f=startupFixture(t);f.data.owner=false;await f.startup.start(f.selected,await f.data.options.authorize());
 assert.deepEqual(f.events,['ordinary-start']);assert.deepEqual(f.data.requests,[]);assert.equal(f.data.journal,null);
});

for(const field of ['sourceDigest','sourceFingerprint','contractId','programFingerprint','child','origin']){
 test(`module health refuses a mismatched ${field} and retains the previous active journal`,async t=>{
  const f=startupFixture(t,{changeBoundary:boundary=>{const start=boundary.start;boundary.start=async options=>{
   const result=await start(options);return {...result,[field]:field==='child'?{}:'mismatched'};};}});
  await assert.rejects(f.startup.start(f.selected,await f.data.options.authorize()),{code:'transition'});
  assert.equal(f.data.journal.active,null);assert.equal(f.runtime.child,null);assert.equal(f.events.filter(value=>value==='stop').length,1);
  assert.equal(f.events.includes('module-health'),false);
 });
}

test('ordinary healthy HTTP is insufficient when the trusted installer cannot verify module health',async t=>{
 const f=startupFixture(t,{changeBoundary:boundary=>{boundary.verifyHealth=async()=>false;}});
 await assert.rejects(f.startup.start(f.selected,await f.data.options.authorize()),{code:'transition'});
 assert.equal(f.data.journal.active,null);assert.equal(f.runtime.child,null);
});

test('staging while an existing backend is open never starts, stops or activates it',async t=>{
 const f=startupFixture(t),existing={userWork:true};f.runtime.child=existing;f.runtime.configuration=f.selected;f.runtime.origin='http://127.0.0.1:43212';
 const result=await f.startup.stage();assert.equal(result.phase,'update-ready');assert.equal(f.runtime.child,existing);
 assert.deepEqual(f.events,['provider']);assert.equal(f.data.journal.active,null);assert.equal(f.data.journal.staged.catalogSequence,1);
 f.stageEligible=false;assert.equal(f.startup.canRefresh(),false);assert.equal(await f.startup.stage(),null);
});

test('shutdown aborts and drains preparation before any caller may tear down the runtime',async t=>{
 const entered=deferred(),release=deferred(),f=startupFixture(t),segment=f.data.transport.segment;
 f.data.transport.segment=async(...args)=>{entered.resolve();await release.promise;return segment(...args);};
 const running=f.startup.start(f.selected,await f.data.options.authorize()).catch(error=>error);await entered.promise;
 let drained=false;const closing=f.startup.shutdown().then(()=>{drained=true;});await tick();assert.equal(drained,false);assert.equal(f.startup.canRefresh(),false);
 release.resolve();assert.equal((await running).code,'cancelled');await closing;assert.equal(drained,true);
 assert.equal(f.runtime.child,null);assert.equal(f.data.journal.active,null);assert.equal(f.events.includes('module-start'),false);
});

test('access invalidation during health aborts the lease, drains it and allows a later fresh cold launch',async t=>{
 const entered=deferred(),release=deferred(),f=startupFixture(t,{changeBoundary:boundary=>{
  const health=boundary.verifyHealth;boundary.verifyHealth=async options=>{entered.resolve();await release.promise;return health(options);};}});
 const running=f.startup.start(f.selected,await f.data.options.authorize()).catch(error=>error);await entered.promise;f.generation++;
 let drained=false;const locked=f.startup.invalidate().then(()=>{drained=true;});await tick();assert.equal(drained,false);assert.ok(f.runtime.child);
 release.resolve();assert.equal((await running).code,'authorization');await locked;assert.equal(f.data.journal.active,null);assert.equal(f.runtime.child,null);
 await f.startup.start(f.selected,await f.data.options.authorize());assert.equal(f.data.journal.active.catalogSequence,1);
});

test('a runtime replacement during failed health is never stopped by the old lease',async t=>{
 const replacement={unrelated:true},f=startupFixture(t,{changeBoundary:boundary=>{boundary.verifyHealth=async({runtime})=>{runtime.child=replacement;return false;};}});
 await assert.rejects(f.startup.start(f.selected,await f.data.options.authorize()),{code:'transition'});
 assert.equal(f.runtime.child,replacement);assert.equal(f.events.includes('stop'),false);assert.equal(f.data.journal.active,null);
});

test('a second startup cannot resume through the ordinary path while a cold module lease is awaiting health',async t=>{
 const entered=deferred(),release=deferred(),f=startupFixture(t,{changeBoundary:boundary=>{const health=boundary.verifyHealth;
  boundary.verifyHealth=async options=>{entered.resolve();await release.promise;return health(options);};}});
 const approval=await f.data.options.authorize(),opening=f.startup.start(f.selected,approval);await entered.promise;
 await assert.rejects(f.startup.start(f.selected,approval),{code:'transition'});assert.equal(f.events.includes('ordinary-start'),false);
 release.resolve();await opening;assert.equal(f.data.journal.active.catalogSequence,1);
});

test('shutdown drains a protected active write already begun before stopping its owned candidate',async t=>{
 const f=startupFixture(t),entered=deferred(),release=deferred(),write=f.data.store.write;
 f.data.store.write=async value=>{if(value.active){entered.resolve();await release.promise;}return write(value);};
 const opening=f.startup.start(f.selected,await f.data.options.authorize()).catch(error=>error);await entered.promise;
 let drained=false;const closing=f.startup.shutdown().then(()=>{drained=true;});await tick();assert.equal(drained,false);assert.ok(f.runtime.child);assert.equal(f.events.includes('stop'),false);
 release.resolve();assert.equal((await opening).code,'cancelled');await closing;assert.equal(drained,true);assert.equal(f.runtime.child,null);
 assert.equal(f.data.journal.active.catalogSequence,1,'An already-started durable write is drained, not rewritten');
});
