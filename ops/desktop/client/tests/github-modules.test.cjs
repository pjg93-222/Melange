'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const {GitHubModules}=require('../github-modules.cjs');
const {fail}=require('../github-module-protocol.cjs');
const {environment,signed,sha}=require('./fixtures/github-module-fixture.cjs');
function fixture(t){const f=environment();t.after(()=>f.cleanup());return f;}
function roleFile(candidate,f){return path.join(candidate.snapshotRoot,f.remote.manifest.datasets[0].datasetId,'models','aggregate.json');}
function next(f,sequence=2,bytes=Buffer.from('{"aggregate":42,"revision":2}')){f.remote=signed('mentat',{keys:f.remote.keys,sequence,bytes});}
test('prepare verifies complete segmented roles but activation is a separate native commit',async t=>{
 const f=fixture(t),provider=new GitHubModules(f.options),settings=structuredClone(f.selected);
 fs.mkdirSync(path.join(f.profile,'state'));const account=path.join(f.profile,'state','accounts.fixture');fs.writeFileSync(account,'unchanged-account-state');const before=sha(fs.readFileSync(account));
 const candidate=await provider.prepare(f.selected);
 assert.equal(f.journal.active,null);assert.equal(f.journal.staged.catalogSequence,1);assert.deepEqual(fs.readFileSync(roleFile(candidate,f)),f.remote.bytes);assert.equal(candidate.status.phase,'ready');assert.deepEqual(f.selected,settings);
 const active=await provider.commitActive(candidate,f.selected,{beforeCommit:()=>true});assert.equal(f.journal.active.catalogSequence,1);assert.equal(active.pointerDigest,candidate.pointerDigest);assert.equal(sha(fs.readFileSync(account)),before);assert.ok(!JSON.stringify(f.journal).includes(f.original));
});
test('background checks stage newer data while preserving active and do not invent an unchanged update',async t=>{
 const f=fixture(t),p=new GitHubModules(f.options),first=await p.prepare(f.selected);await p.commitActive(first,f.selected);
 assert.equal((await p.stage(f.selected)).status.phase,'ready');next(f);const second=await p.stage(f.selected);
 assert.equal(second.status.phase,'update-ready');assert.equal(second.status.updateAvailable,true);assert.equal(f.journal.active.catalogSequence,1);assert.equal(f.journal.staged.catalogSequence,2);
 await p.commitActive(second,f.selected);assert.equal(f.journal.active.catalogSequence,2);
});
test('interrupted transfers retain bounded partial bytes and resume with the exact offset',async t=>{
 const f=fixture(t),original=f.transport.segment;let interrupted=false;
 f.transport.segment=async(tag,item,options)=>{if(!interrupted){interrupted=true;await options.onChunk(f.remote.objects.get(item.asset).subarray(0,3));throw fail('unreachable','Synthetic interruption');}return original(tag,item,options);};
 const p=new GitHubModules(f.options);await assert.rejects(p.prepare(f.selected),error=>error.reason==='unreachable');assert.equal(f.journal.active,null);
 const prepared=await p.prepare(f.selected);assert.ok(f.offsets.includes(3));assert.deepEqual(fs.readFileSync(roleFile(prepared,f)),f.remote.bytes);assert.equal(f.journal.active,null);
});
test('offline fallback requires a previously active fully reverified snapshot',async t=>{
 const f=fixture(t),p=new GitHubModules(f.options),prepared=await p.prepare(f.selected);f.network='unreachable';await assert.rejects(p.prepare(f.selected),error=>error.reason==='unreachable');
 f.network=null;await p.commitActive(prepared,f.selected);f.network='timeout';const offline=await p.prepare(f.selected);assert.equal(offline.status.phase,'offline');assert.equal(offline.status.cached,true);
 fs.writeFileSync(roleFile(offline,f),'corrupt');await assert.rejects(p.prepare(f.selected),error=>error.reason==='integrity');assert.equal(f.journal.active.catalogSequence,1);
});
test('bad signatures, lower sequences and equivocation never become an offline success',async t=>{
 const f=fixture(t),p=new GitHubModules(f.options);await p.commitActive(await p.prepare(f.selected),f.selected);
 const valid=f.remote.envelope;f.remote.envelope={...valid,signature:Buffer.alloc(64).toString('base64')};await assert.rejects(p.prepare(f.selected),error=>error.reason==='integrity');
 f.remote.envelope=valid;next(f,2);await p.stage(f.selected);next(f,1);await assert.rejects(p.prepare(f.selected),/rollback/);next(f,2,Buffer.from('{"aggregate":42,"changed":true}'));await assert.rejects(p.prepare(f.selected),/equivocation/);assert.equal(f.journal.active.catalogSequence,1);
});
test('a failed higher revision keeps active usable without lowering the accepted high-water',async t=>{
 const f=fixture(t),p=new GitHubModules(f.options);await p.commitActive(await p.prepare(f.selected),f.selected);next(f);
 f.transport.segment=async()=>{throw fail('unreachable','Synthetic segment unavailable');};const old=await p.prepare(f.selected);
 assert.equal(old.status.phase,'offline');assert.equal(old.catalogueSequence,1);assert.equal(f.journal.highwater.catalogSequence,2);assert.equal(f.journal.active.catalogSequence,1);
 next(f,1);await assert.rejects(p.prepare(f.selected),/rollback/);
});
test('revocation is checked when queued work actually begins and again after network work',async t=>{
 const f=fixture(t),p=new GitHubModules(f.options);let release,entered;
 const waiting=new Promise(resolve=>{entered=resolve;});f.transport.resolveMain=async()=>{f.requests.push('held-main');entered();await new Promise(resolve=>{release=resolve;});return 'b'.repeat(40);};
 const first=p.prepare(f.selected);await waiting;const queued=p.stage(f.selected);f.revoked=true;release();
 await assert.rejects(first,error=>error.reason==='authorization');await assert.rejects(queued,error=>error.reason==='authorization');assert.equal(f.journal,null);assert.equal(f.requests.filter(x=>x==='held-main').length,1);
});
test('native commit rechecks owner and cannot trust a caller-supplied effective configuration',async t=>{
 const f=fixture(t),p=new GitHubModules(f.options),candidate=await p.prepare(f.selected);f.revoked=true;await assert.rejects(p.commitActive(candidate,f.selected),error=>error.reason==='authorization');assert.equal(f.journal.active,null);
 f.revoked=false;const active=await p.commitActive({...candidate,effectiveConfiguration:{dataDirectory:'untrusted'},snapshotRoot:'untrusted'},f.selected);assert.equal(active.effectiveConfiguration.dataDirectory,f.original);assert.equal(active.snapshotRoot,candidate.snapshotRoot);
});
test('native beforeCommit guard is synchronous and runs after verification, before any active write',async t=>{
 const f=fixture(t),p=new GitHubModules(f.options),candidate=await p.prepare(f.selected);let calls=0;
 await assert.rejects(p.commitActive(candidate,f.selected,{beforeCommit:()=>{calls++;return false;}}),/guard/);assert.equal(calls,1);assert.equal(f.journal.active,null);
 await assert.rejects(p.commitActive(candidate,f.selected,{beforeCommit:async()=>true}),/guard/);assert.equal(f.journal.active,null);
 await assert.rejects(p.commitActive(candidate,f.selected,{beforeCommit:true}),/guard/);assert.equal(f.journal.active,null);
});
test('logical concatenation hash rejects valid segments supplied in the wrong order',async t=>{
 const f=fixture(t),p=new GitHubModules(f.options);f.remote.manifest.datasets[0].objects[0].segments.reverse();f.remote.rebind();
 await assert.rejects(p.prepare(f.selected),/Logical module role integrity/);assert.equal(f.journal.active,null);assert.equal(f.journal.staged,null);assert.equal(f.journal.highwater.catalogSequence,1);
});
test('stable matching legacy bytes seed a separate snapshot without network downloads or hardlinks',async t=>{
 const f=fixture(t),source=path.join(f.original,'aggregate.json');fs.writeFileSync(source,f.remote.bytes);f.options.registry['mentat.fixture.v1'].probeLegacy=async()=>({aggregate:source});
 const p=new GitHubModules(f.options),candidate=await p.prepare(f.selected),copy=roleFile(candidate,f);assert.equal(f.offsets.length,0);assert.deepEqual(fs.readFileSync(copy),f.remote.bytes);assert.notEqual(fs.statSync(copy,{bigint:true}).ino,fs.statSync(source,{bigint:true}).ino);
 fs.writeFileSync(source,'local-change');assert.deepEqual(fs.readFileSync(copy),f.remote.bytes);await p.commitActive(candidate,f.selected);
});
test('a nonmatching legacy candidate is preserved and the signed data is downloaded instead',async t=>{
 const f=fixture(t),source=path.join(f.original,'aggregate.json'),local=Buffer.from('different-local-data');fs.writeFileSync(source,local);f.options.registry['mentat.fixture.v1'].probeLegacy=async()=>({aggregate:source});
 const p=new GitHubModules(f.options);await p.prepare(f.selected);assert.ok(f.offsets.length>0);assert.deepEqual(fs.readFileSync(source),local);
});
test('legacy seed paths cannot escape the original workspace or read protected state',async t=>{
 const f=fixture(t),outside=path.join(f.profile,'account.fixture');fs.writeFileSync(outside,f.remote.bytes);f.options.registry['mentat.fixture.v1'].probeLegacy=async()=>({aggregate:outside});
 await assert.rejects(new GitHubModules(f.options).prepare(f.selected),/leaves the owner workspace/);assert.deepEqual(fs.readFileSync(outside),f.remote.bytes);
});
test('native cache roots are allowlisted and cannot overlap owner or protected roots',async t=>{
 const f=fixture(t);assert.throws(()=>new GitHubModules({...f.options,cacheRoot:path.join(f.temporary,'arbitrary')}),/Unapproved/);
 assert.throws(()=>new GitHubModules({...f.options,protectedRoots:[f.options.cacheRoot]}),/overlaps/);
 const p=new GitHubModules(f.options);await assert.rejects(p.prepare({...f.selected,dataDirectory:f.profile}),/separate/);assert.equal(f.requests.length,0);
});
test('cache directory junctions/reparse points are refused before network or account changes',async t=>{
 const f=fixture(t);fs.mkdirSync(f.options.cacheRoot,{recursive:true});fs.symlinkSync(f.original,path.join(f.options.cacheRoot,'segments'),process.platform==='win32'?'junction':'dir');
 const sentinel=path.join(f.original,'account.fixture');fs.writeFileSync(sentinel,'preserve');await assert.rejects(new GitHubModules(f.options).prepare(f.selected),/Unsafe module cache directory/);assert.equal(f.requests.length,0);assert.equal(fs.readFileSync(sentinel,'utf8'),'preserve');
});
test('extra snapshot directories and corrupt complete segment objects are not silently overwritten',async t=>{
 const f=fixture(t),p=new GitHubModules(f.options),candidate=await p.prepare(f.selected);fs.mkdirSync(path.join(candidate.snapshotRoot,'unexpected'));await assert.rejects(p.commitActive(candidate,f.selected),/Unexpected module snapshot directory/);assert.equal(f.journal.active,null);
 fs.rmdirSync(path.join(candidate.snapshotRoot,'unexpected'));await p.commitActive(candidate,f.selected);const segment=f.remote.manifest.datasets[0].objects[0].segments[0];fs.writeFileSync(path.join(f.options.cacheRoot,'segments',segment.sha256+'.bin'),'bad');next(f,2,f.remote.bytes);await assert.rejects(p.stage(f.selected),/segment cache integrity/);assert.equal(f.journal.active.catalogSequence,1);
});
test('insufficient staging space never activates and protected journal corruption never resets high-water',async t=>{
 const f=fixture(t),p=new GitHubModules({...f.options,minimumFreeBytes:Number.MAX_SAFE_INTEGER});await assert.rejects(p.prepare(f.selected),error=>error.reason==='storage');assert.equal(f.journal.active,null);
 await f.store.write({...f.journal,extra:true});const count=f.requests.length;await assert.rejects(new GitHubModules(f.options).prepare(f.selected),error=>error.reason==='integrity');assert.equal(f.requests.length,count);
});
test('per-app journals cannot be substituted and active reads perform no public requests',async t=>{
 const f=fixture(t),p=new GitHubModules(f.options);assert.equal(await p.active(f.selected),null);await p.commitActive(await p.prepare(f.selected),f.selected);const count=f.requests.length;await p.active(f.selected);assert.equal(f.requests.length,count);
 const other=environment('melange');t.after(()=>other.cleanup());await assert.rejects(new GitHubModules({...other.options,store:f.store}).active(other.selected),error=>error.reason==='integrity');assert.equal(f.journal.appId,'mentat');assert.equal(f.journal.highwater.catalogSequence,1);
});
test('a pre-existing partial cache hardlink cannot mutate an owner account file',async t=>{
 const f=fixture(t),segment=f.remote.manifest.datasets[0].objects[0].segments[0],account=path.join(f.original,'account.fixture');fs.writeFileSync(account,'own');
 fs.mkdirSync(path.join(f.options.cacheRoot,'segments'),{recursive:true});fs.linkSync(account,path.join(f.options.cacheRoot,'segments',segment.sha256+'.part'));
 await assert.rejects(new GitHubModules(f.options).prepare(f.selected),/Unsafe module cache file/);assert.equal(fs.readFileSync(account,'utf8'),'own');assert.equal(f.journal.active,null);
});
test('legacy bytes changed during the copy are discarded instead of treated as immutable',async t=>{
 const f=fixture(t),bytes=Buffer.from('{"aggregate":42,"padding":"'+('x'.repeat(128))+'"}');next(f,1,bytes);const source=path.join(f.original,'aggregate.json');fs.writeFileSync(source,bytes);f.options.registry['mentat.fixture.v1'].probeLegacy=async()=>({aggregate:source});
 const original=fs.createReadStream;let changed=false;
 const mock=t.mock.method(fs,'createReadStream',function(file,...args){const stream=original.call(this,file,...(file===source?[{highWaterMark:16}]:args));if(file===source&&!changed)stream.once('data',()=>{changed=true;fs.writeFileSync(source,Buffer.alloc(bytes.length,120));});return stream;});
 const candidate=await new GitHubModules(f.options).prepare(f.selected);mock.mock.restore();assert.equal(changed,true);assert.ok(f.offsets.length>0);assert.deepEqual(fs.readFileSync(roleFile(candidate,f)),bytes);assert.deepEqual(fs.readFileSync(source),Buffer.alloc(bytes.length,120));
});
test('a partial swapped to an account hardlink after path validation is refused before the first write',async t=>{
 const f=fixture(t),p=new GitHubModules(f.options),account=path.join(f.original,'account.fixture');fs.writeFileSync(account,'own');
 const file=p.file.bind(p);let swapped=false;
 p.file=async function(relative,options){const result=await file(relative,options);if(relative.endsWith('.part')&&!swapped){swapped=true;fs.linkSync(account,result);}return result;};
 await assert.rejects(p.prepare(f.selected),/Opened module cache identity changed/);assert.equal(swapped,true);assert.equal(fs.readFileSync(account,'utf8'),'own');assert.equal(f.journal.active,null);
});
test('writes retain the validated handle if the partial path is replaced after open',async t=>{
 const f=fixture(t),p=new GitHubModules(f.options),account=path.join(f.original,'account.fixture');fs.writeFileSync(account,'own');const send=f.transport.segment;let swapped=false;
 f.transport.segment=async(tag,item,options)=>{if(!swapped){const part=path.join(f.options.cacheRoot,'segments',item.sha256+'.part');fs.unlinkSync(part);fs.linkSync(account,part);swapped=true;}return send(tag,item,options);};
 await assert.rejects(p.prepare(f.selected),/Unsafe module cache file/);assert.equal(swapped,true);assert.equal(fs.readFileSync(account,'utf8'),'own');assert.equal(f.journal.active,null);
});
test('trusted binder receives authenticated source and exact objects while original roots remain intact',async t=>{
 const f=fixture(t);f.selected.connection={appDataRoot:path.join(f.original,'app','data'),console:'original-console'};const original=structuredClone(f.selected);let context;
 f.options.effectiveConfiguration=value=>{context=value;return {...value.originalSelected,ownerGitHubModuleData:value.source};};
 const p=new GitHubModules(f.options),candidate=await p.prepare(f.selected),source=candidate.effectiveConfiguration.ownerGitHubModuleData;
 assert.deepEqual(context.datasets[0].objects,f.remote.manifest.datasets[0].objects);assert.equal(source.manifestSha256,candidate.manifestSha256);assert.equal(source.pointerDigest,candidate.pointerDigest);assert.equal(source.releaseCommit,f.remote.value.releaseCommit);assert.equal(source.catalogSequence,1);assert.equal(source.cacheRoot,p.cacheRoot);assert.equal(source.repository,'pjg93-222/mentat');
 assert.equal(path.join(source.cacheRoot,'snapshots',source.manifestSha256),candidate.snapshotRoot);assert.deepEqual(candidate.effectiveConfiguration.connection,original.connection);assert.deepEqual(f.selected,original);
 const requests=f.requests.length;await assert.rejects(p.prepare(candidate.effectiveConfiguration),error=>error.reason==='authorization');assert.equal(f.requests.length,requests);
});
test('a compiled binder cannot alter original paths/connections or inject another source descriptor',async t=>{
 const f=fixture(t);f.selected.connection={appDataRoot:path.join(f.original,'app','data')};
 for(const mutate of [value=>({...value.originalSelected,dataDirectory:path.join(f.original,'other'),ownerGitHubModuleData:value.source}),value=>({...value.originalSelected,connection:{appDataRoot:'changed'},ownerGitHubModuleData:value.source}),value=>({...value.originalSelected,ownerGitHubModuleData:{...value.source,appId:'melange'}})]){
  await assert.rejects(new GitHubModules({...f.options,effectiveConfiguration:mutate}).prepare(f.selected),/preserve original configuration/);assert.equal(f.journal.active,null);
 }
});
