'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),path=require('node:path');
const {CORE_KINDS,createModuleDataRegistry,withSnapshotValidation}=require('../module-data-adapters.cjs');
const {checkedRegistry}=require('../github-module-protocol.cjs');
function fixture(appId='melange',probe=async request=>({schemaVersion:1,validated:true,appId:request.appId,kind:request.kind,coverage:{completeKind:true,fullApplication:false}}),prepareProbe){
 const registry=createModuleDataRegistry({appId,sourceRoot:path.resolve('trusted-source'),probe,prepareProbe}),kind=CORE_KINDS[appId][0],adapter=registry[kind],root=path.resolve('fixture-cache');
 const dataset={kind,adapterVersion:1,objects:Object.keys(adapter.roles).map(role=>({role,bytes:1,sha256:'a'.repeat(64),segments:[{asset:role+'.bin',bytes:1,sha256:'a'.repeat(64)}]})),counts:{files:Object.keys(adapter.roles).length}};
 const files=Object.fromEntries(Object.entries(adapter.roles).map(([role,spec])=>[role,path.join(root,...spec.path.split('/'))]));
 return{registry,kind,adapter,root,dataset,files};
}
test('core kinds have complete compiled closure and explicit non-full-app probe coverage',async()=>{
 for(const appId of ['melange','mentat']){const f=fixture(appId);assert.equal(checkedRegistry(appId,f.registry),f.registry);assert.equal(f.adapter.validateMetadata(f.dataset),true);assert.equal(await f.adapter.validateSnapshot(f),true);assert.equal(Object.isFrozen(f.registry),true);}
});

for(const appId of ['melange','mentat'])test(`module prewarm ${appId} receives no dataset before hashing and creates a fresh session per validation`,async()=>{
 const events=[],requests=[],controller=new AbortController();let fresh=0;
 const reply=request=>({schemaVersion:1,validated:true,appId:request.appId,kind:request.kind,coverage:{completeKind:true,fullApplication:false}});
 const f=fixture(appId,async request=>{fresh++;return reply(request);},options=>{
  assert.deepEqual(Object.keys(options),['signal']);assert.equal(options.signal,controller.signal);events.push('prewarm');
  return {run:async request=>{events.push('run');requests.push(request);return reply(request);},cancel:async()=>{events.push('drain');}};
 });
 checkedRegistry(appId,f.registry);
 for(let n=0;n<2;n++)await withSnapshotValidation(f.adapter,{signal:controller.signal},async validate=>{events.push('hashes');assert.equal(requests.length,n);return validate({...f,signal:controller.signal});});
 assert.deepEqual(events,['prewarm','hashes','run','drain','prewarm','hashes','run','drain']);assert.equal(fresh,0);assert.equal(requests[0].snapshotRoot,f.root);assert.equal(requests[0].kind,f.kind);
 assert.equal(await f.adapter.validateSnapshot(f),true);assert.equal(fresh,1);
});

test('module prewarm hash failure waits for drain and never sends data',async()=>{
 let release,drainStarted,settled=false,runs=0;const drained=new Promise(resolve=>{release=resolve;}),started=new Promise(resolve=>{drainStarted=resolve;});
 const f=fixture('mentat',undefined,()=>({run:async()=>{runs++;},cancel:async()=>{drainStarted();await drained;}}));
 const result=withSnapshotValidation(f.adapter,{},async()=>{throw new Error('fixture hash failure');});result.then(()=>{settled=true;},()=>{settled=true;});
 await started;assert.equal(settled,false);assert.equal(runs,0);release();await assert.rejects(result,/fixture hash failure/);assert.equal(settled,true);
});

test('module prewarm cannot reuse a consumed session or change its cancellation scope',async()=>{
 let runs=0,drains=0;const signal=new AbortController().signal,f=fixture('mentat',undefined,()=>({run:async request=>{runs++;return {schemaVersion:1,validated:true,appId:request.appId,kind:request.kind,coverage:{completeKind:true,fullApplication:false}};},cancel:async()=>{drains++;}}));
 const session=await f.adapter.prepareSnapshot({signal});assert.throws(()=>session.validateSnapshot(f),/unavailable/);await session.validateSnapshot({...f,signal});assert.throws(()=>session.validateSnapshot({...f,signal}),/unavailable/);await Promise.all([session.cancel(),session.cancel()]);assert.equal(runs,1);assert.equal(drains,1);
});

test('module prewarm cancellation during hashes and invalid paths never send input',async()=>{
 for(const mode of ['cancel','path']){
  let runs=0,drains=0;const controller=new AbortController(),f=fixture('mentat',undefined,()=>({run:async()=>{runs++;},cancel:async()=>{drains++;}}));
  await assert.rejects(withSnapshotValidation(f.adapter,{signal:controller.signal},async validate=>{if(mode==='cancel')controller.abort();else f.files.selection=path.resolve('outside','selection.json');return validate({...f,signal:controller.signal});}));assert.equal(runs,0);assert.equal(drains,1);
 }
});

test('module prewarm rejects invalid reader coverage and malformed runners while draining',async()=>{
 let drains=0;const f=fixture('mentat',undefined,()=>({run:async request=>({schemaVersion:1,validated:true,appId:request.appId,kind:request.kind,coverage:{completeKind:true,fullApplication:true}}),cancel:async()=>{drains++;}}));
 await assert.rejects(withSnapshotValidation(f.adapter,{},validate=>validate(f)),/rejected/);assert.equal(drains,1);
 const g=fixture('mentat',undefined,()=>({cancel:async()=>{drains++;}}));await assert.rejects(g.adapter.prepareSnapshot(),/unavailable/);assert.equal(drains,2);
});
test('missing, unknown, duplicate, oversized and miscounted roles cannot enable a core kind',()=>{
 for(const change of [d=>d.objects.pop(),d=>d.objects[0].role='accounts',d=>d.objects[0].role=d.objects[1].role,d=>d.objects[0].bytes=Number.MAX_SAFE_INTEGER,d=>d.counts.files--]){const f=fixture();change(f.dataset);assert.equal(f.adapter.validateMetadata(f.dataset),false);}
});
test('fixed cache role locations are mandatory before a probe runs',async()=>{
 let calls=0;const f=fixture('mentat',async()=>{calls++;});f.files.selection=path.resolve('outside','selection.json');await assert.rejects(f.adapter.validateSnapshot(f));assert.equal(calls,0);
});
test('probe request carries native-derived roots and signal only through the agreed options contract',async()=>{
 let captured;const f=fixture('mentat',async(request,options)=>{captured={request,options};return{schemaVersion:1,validated:true,appId:request.appId,kind:request.kind,coverage:{completeKind:true,fullApplication:false}};});
 const controller=new AbortController();await f.adapter.validateSnapshot({...f,signal:controller.signal});assert.equal(captured.options.signal,controller.signal);assert.equal(captured.request.snapshotRoot,f.root);assert.equal(captured.request.objects,f.dataset.objects);assert.equal(Object.hasOwn(captured.request,'configuration'),false);
});
test('wrong app/kind, false or inflated coverage, and unknown response fields fail closed',async()=>{
 for(const mutate of [r=>r.appId='terrier',r=>r.kind='other',r=>r.validated=false,r=>r.coverage.fullApplication=true,r=>r.extra='private-path']){const f=fixture('melange',async request=>{const result={schemaVersion:1,validated:true,appId:request.appId,kind:request.kind,coverage:{completeKind:true,fullApplication:false}};mutate(result);return result;});await assert.rejects(f.adapter.validateSnapshot(f));}
});
test('cancellation before or during a probe never reports verification success',async()=>{
 let calls=0;const first=new AbortController();first.abort();const f=fixture('melange',async()=>{calls++;});await assert.rejects(f.adapter.validateSnapshot({...f,signal:first.signal}));assert.equal(calls,0);
 const later=new AbortController(),g=fixture('melange',async request=>{later.abort();return{schemaVersion:1,validated:true,appId:request.appId,kind:request.kind,coverage:{completeKind:true,fullApplication:false}};});await assert.rejects(g.adapter.validateSnapshot({...g,signal:later.signal}));
});


for(const appId of ['melange','mentat'])test(`${appId} passive public registry has exact fixed roles without any mixed core defaults`,async()=>{
 const {PUBLIC_KINDS,PUBLIC_ROLES,createPublicModuleDataRegistry}=require('../module-data-adapters.cjs');
 const calls=[],registry=createPublicModuleDataRegistry({appId,sourceRoot:path.resolve('trusted-source'),probe:async request=>{calls.push(request);return {schemaVersion:1,validated:true,appId:request.appId,kind:request.kind,coverage:{completeKind:true,fullApplication:false}};}});
 assert.deepEqual(Object.keys(registry),PUBLIC_KINDS[appId]);assert.ok(CORE_KINDS[appId].every(kind=>!Object.hasOwn(registry,kind)));
 checkedRegistry(appId,registry,PUBLIC_KINDS[appId]);const kind=PUBLIC_KINDS[appId][0],adapter=registry[kind],root=path.resolve('public-fixture-cache');
 const dataset={kind,adapterVersion:1,objects:Object.keys(PUBLIC_ROLES[kind]).map(role=>({role,bytes:1,sha256:'a'.repeat(64)})),counts:{files:Object.keys(PUBLIC_ROLES[kind]).length}};
 const files=Object.fromEntries(Object.entries(adapter.roles).map(([role,spec])=>[role,path.join(root,...spec.path.split('/'))]));
 assert.equal(await adapter.validateSnapshot({dataset,root,files}),true);assert.equal(calls.length,1);
 if(appId==='melange'){assert.deepEqual(Object.keys(adapter.roles),['observations','receipt']);assert.equal(adapter.roles.observations.maxBytes,8*1024**3);}
 else{assert.equal(Object.keys(adapter.roles).length,13);assert.equal(adapter.maxTotalBytes,512*1024**2);
  assert.equal(adapter.roles['mentat.fec.cm.2022'].path,'fec/2022/cm.psv');dataset.objects.forEach(object=>{object.bytes=object.role==='mentat.fec.provenance'?1:160*1024**2;});
  assert.equal(adapter.validateMetadata(dataset),false,'Combined public payload cannot exceed512MiB even under per-file limits');}
});
