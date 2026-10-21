'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),path=require('node:path');
const {CORE_KINDS,createModuleDataRegistry}=require('../module-data-adapters.cjs');
const {checkedRegistry}=require('../github-module-protocol.cjs');
function fixture(appId='melange',probe=async request=>({schemaVersion:1,validated:true,appId:request.appId,kind:request.kind,coverage:{completeKind:true,fullApplication:false}})){
 const registry=createModuleDataRegistry({appId,sourceRoot:path.resolve('trusted-source'),probe}),kind=CORE_KINDS[appId][0],adapter=registry[kind],root=path.resolve('fixture-cache');
 const dataset={kind,adapterVersion:1,objects:Object.keys(adapter.roles).map(role=>({role,bytes:1,sha256:'a'.repeat(64),segments:[{asset:role+'.bin',bytes:1,sha256:'a'.repeat(64)}]})),counts:{files:Object.keys(adapter.roles).length}};
 const files=Object.fromEntries(Object.entries(adapter.roles).map(([role,spec])=>[role,path.join(root,...spec.path.split('/'))]));
 return{registry,kind,adapter,root,dataset,files};
}
test('core kinds have complete compiled closure and explicit non-full-app probe coverage',async()=>{
 for(const appId of ['melange','mentat']){const f=fixture(appId);assert.equal(checkedRegistry(appId,f.registry),f.registry);assert.equal(f.adapter.validateMetadata(f.dataset),true);assert.equal(await f.adapter.validateSnapshot(f),true);assert.equal(Object.isFrozen(f.registry),true);}
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
