'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const {GitHubModules,fileDigest}=require('../github-modules.cjs');
const {validateModuleBinding}=require('../module-data-binding.cjs');
const {environment,signed,sha}=require('./fixtures/github-module-fixture.cjs');

function largeFixture(t){
 const f=environment();t.after(()=>f.cleanup());
 const bytes=Buffer.from(JSON.stringify({aggregate:42,padding:'x'.repeat(8*1024*1024+173)}));
 const kind='mentat.fixture.v1',registry={[kind]:{appId:'mentat',version:1,roles:{aggregate:{path:'models/aggregate.json',maxBytes:16*1024*1024}},maxTotalBytes:16*1024*1024,
  validateMetadata:()=>true,validateSnapshot:async({files})=>JSON.parse(fs.readFileSync(files.aggregate,'utf8')).aggregate===42}};
 f.remote=signed('mentat',{keys:f.remote.keys,registry,bytes});f.options.registry=registry;
 f.transport.segment=async(_tag,item,{offset,onChunk})=>{const content=f.remote.objects.get(item.asset);for(let n=offset;n<content.length;n+=1024*1024)await onChunk(content.subarray(n,n+1024*1024));};
 return {f,bytes};
}

test('large streamed digest includes the non-aligned final bytes',async t=>{
 const {f,bytes}=largeFixture(t),file=path.join(f.temporary,'large-public-fixture.bin');fs.writeFileSync(file,bytes);
 assert.deepEqual(await fileDigest(file),{bytes:bytes.length,sha256:sha(bytes)});
});

test('large streamed digest still stops on cancellation during reading',async t=>{
 const {f,bytes}=largeFixture(t),file=path.join(f.temporary,'large-public-fixture.bin'),controller=new AbortController();fs.writeFileSync(file,bytes);
 const create=fs.createReadStream;let observed=false;
 t.mock.method(fs,'createReadStream',function(...args){const stream=create.apply(this,args);stream.once('data',()=>{observed=true;controller.abort();});return stream;});
 await assert.rejects(fileDigest(file,{signal:controller.signal}),error=>error.reason==='cancelled');assert.equal(observed,true);
 assert.deepEqual(fs.readFileSync(file),bytes);
});

test('large segmented roles retain exact bytes and binding rejects a changed tail',async t=>{
 const {f,bytes}=largeFixture(t),candidate=await new GitHubModules(f.options).prepare(f.selected);
 const file=path.join(candidate.snapshotRoot,f.remote.manifest.datasets[0].datasetId,'models','aggregate.json');assert.deepEqual(fs.readFileSync(file),bytes);
 const options={appId:'mentat',profile:f.profile,configuration:candidate.effectiveConfiguration,publicKeys:f.options.publicKeys,registry:f.options.registry};
 const before=await f.store.read(),checked=await validateModuleBinding(options);assert.equal(checked.snapshotRoot,candidate.snapshotRoot);assert.deepEqual(await f.store.read(),before);
 const descriptor=fs.openSync(file,'r+');try{fs.writeSync(descriptor,Buffer.from('y'),0,1,bytes.length-3);}finally{fs.closeSync(descriptor);}
 await assert.rejects(validateModuleBinding(options),error=>error.reason==='integrity');assert.deepEqual(await f.store.read(),before);
});

test('large native binding stops after cancellation without changing the journal',async t=>{
 const {f}=largeFixture(t),candidate=await new GitHubModules(f.options).prepare(f.selected),controller=new AbortController();
 const file=path.join(candidate.snapshotRoot,f.remote.manifest.datasets[0].datasetId,'models','aggregate.json'),open=fs.promises.open;
 let observed=false;t.mock.method(fs.promises,'open',async function(target,...args){const handle=await open.call(this,target,...args);if(target===file){const read=handle.read.bind(handle);handle.read=async(...values)=>{const result=await read(...values);if(result.bytesRead){observed=true;controller.abort();}return result;};}return handle;});
 const before=await f.store.read();await assert.rejects(validateModuleBinding({appId:'mentat',profile:f.profile,configuration:candidate.effectiveConfiguration,publicKeys:f.options.publicKeys,registry:f.options.registry,signal:controller.signal}),error=>error.reason==='cancelled');
 assert.equal(observed,true);assert.deepEqual(await f.store.read(),before);
});
