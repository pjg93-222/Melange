'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const {GitHubModules,fileDigest}=require('../github-modules.cjs');
const {fail}=require('../github-module-protocol.cjs');
const {environment,signed,sha,redirectedLocalCache}=require('./fixtures/github-module-fixture.cjs');
function fixture(t){const f=environment();t.after(()=>f.cleanup());return f;}
function roleFile(candidate,f){return path.join(candidate.snapshotRoot,f.remote.manifest.datasets[0].datasetId,'models','aggregate.json');}
function next(f,sequence=2,bytes=Buffer.from('{"aggregate":42,"revision":2}')){f.remote=signed('mentat',{keys:f.remote.keys,sequence,bytes});}

for(const mode of ['success','hash failure','cancel','drain mutation'])test(`module prewarm provider ${mode} preserves the hash and final mutation barriers`,async t=>{
 const f=fixture(t),p=new GitHubModules(f.options),candidate=await p.prepare(f.selected),file=roleFile(candidate,f),adapter=f.options.registry['mentat.fixture.v1'],read=adapter.validateSnapshot,controller=new AbortController(),events=[],before=structuredClone(f.journal);
 const stream=fs.createReadStream;t.mock.method(fs,'createReadStream',function(target,...options){const result=stream.call(this,target,...options);if(target===file){events.push('hash');result.once('end',()=>events.push('hashed'));}return result;});
 adapter.prepareSnapshot=async options=>{assert.deepEqual(Object.keys(options),['signal']);assert.equal(options.signal,controller.signal);events.push('prewarm');if(mode==='cancel')controller.abort();return {
  validateSnapshot:async input=>{assert.equal(events.at(-1),'hashed');events.push('reader');return read(input);},
  cancel:async()=>{events.push('drain');if(mode==='drain mutation')fs.writeFileSync(file,Buffer.alloc(f.remote.bytes.length,120));}
 };};
 if(mode==='hash failure')fs.writeFileSync(file,Buffer.alloc(f.remote.bytes.length,120));
 const result=p.stage(f.selected,{signal:controller.signal});if(mode==='success'){await result;assert.deepEqual(events,['prewarm','hash','hashed','reader','drain']);}else{await assert.rejects(result);assert.equal(events.at(-1),'drain');assert.equal(events.includes('reader'),mode==='drain mutation');}
 assert.equal(events[0],'prewarm');assert.deepEqual(f.journal,before);
});

test('a fixed transparently redirected native cache adopts one physical root before metadata, segments and snapshot checks',async t=>{
 const f=fixture(t),local=path.join(fs.realpathSync.native(f.temporary),'local');fs.mkdirSync(local);const redirect=redirectedLocalCache(t,local);
 const previous=process.env.LOCALAPPDATA;t.after(()=>{if(previous===undefined)delete process.env.LOCALAPPDATA;else process.env.LOCALAPPDATA=previous;});process.env.LOCALAPPDATA=local;
 const p=new GitHubModules({...f.options,cacheRoot:path.join(local,'MelangeData','mentat','github-module-data')}),selected=structuredClone(f.selected),candidate=await p.prepare(f.selected);
 const physical=path.join(redirect.physicalRoot,'mentat','github-module-data');assert.equal(p.cacheRoot,physical);assert.equal(candidate.effectiveConfiguration.ownerGitHubModuleData.cacheRoot,physical);
 assert.equal(candidate.snapshotRoot,path.join(physical,'snapshots',candidate.manifestSha256));assert.deepEqual(fs.readFileSync(roleFile(candidate,f)),f.remote.bytes);
 assert.equal(fs.readdirSync(path.join(physical,'pointers')).length,1);assert.ok(fs.readdirSync(path.join(physical,'pointers'))[0].endsWith('.json'));assert.deepEqual(f.selected,selected);
 await p.commitActive(candidate,f.selected);assert.equal(f.journal.active.manifestSha256,candidate.manifestSha256);
});

function onMetadataClose(t,action){
 const open=fs.promises.open;let reached=false;
 t.mock.method(fs.promises,'open',async function(file,...args){const handle=await open.call(this,file,...args);if(!file.endsWith('.tmp'))return handle;
  const close=handle.close.bind(handle);handle.close=async()=>{await close();if(!reached){reached=true;action(file);}};return handle;
 });
 return ()=>reached;
}

function equalObservedTimes(t,{onClose,onLstat}={}){
 // Model a timestamp collision without weakening identity/size/link observations.
 const stamp=stat=>typeof stat.ino==='bigint'&&stat.isFile()?new Proxy(stat,{get(object,key){if(key==='mtimeNs'||key==='ctimeNs')return 1234567890000000000n;return Reflect.get(object,key,object);}}):stat;
 for(const key of ['lstatSync','fstatSync']){const original=fs[key];t.mock.method(fs,key,function(...args){return stamp(original.apply(this,args));});}
 const lstat=fs.promises.lstat;t.mock.method(fs.promises,'lstat',async function(...args){onLstat?.(args[0]);return stamp(await lstat.apply(this,args));});
 const open=fs.promises.open;let reached=false;t.mock.method(fs.promises,'open',async function(...args){const handle=await open.apply(this,args),stat=handle.stat.bind(handle);handle.stat=async(...options)=>stamp(await stat(...options));
  if(onClose&&args[0].endsWith('.tmp')){const close=handle.close.bind(handle);handle.close=async()=>{await close();if(!reached){reached=true;onClose(args[0]);}};}return handle;
 });return ()=>reached;
}

test('immutable metadata pins caller bytes before its first asynchronous operation',async t=>{
 const f=fixture(t),p=new GitHubModules(f.options);await p.ensureCache(f.selected);const raw=Buffer.from('original'),expected=Buffer.from(raw),file=p.file.bind(p);let changed=false;
 p.file=async(...args)=>{if(!changed){changed=true;raw.fill(120);}return file(...args);};
 const published=await p.immutable('pointers/'+('1'.repeat(64))+'.json',raw);assert.equal(changed,true);assert.deepEqual(fs.readFileSync(published),expected);assert.equal(fs.statSync(published).nlink,1);
});

test('immutable metadata rejects and preserves completed bytes changed when its writer closes',async t=>{
 const f=fixture(t),p=new GitHubModules(f.options);await p.ensureCache(f.selected);const raw=Buffer.from('original');let staged;
 const reached=onMetadataClose(t,file=>{staged=file;fs.writeFileSync(file,Buffer.alloc(raw.length,120));});
 await assert.rejects(p.immutable('pointers/'+('2'.repeat(64))+'.json',raw),error=>error.reason==='integrity');assert.equal(reached(),true);assert.deepEqual(fs.readFileSync(staged),Buffer.alloc(raw.length,120));assert.equal(fs.existsSync(path.join(p.cacheRoot,'pointers','2'.repeat(64)+'.json')),false);
});

test('immutable final verification rejects different bytes even when all observed timestamps collide',async t=>{
 const f=fixture(t),p=new GitHubModules(f.options);await p.ensureCache(f.selected);const raw=Buffer.from('original');let staged;
 const reached=equalObservedTimes(t,{onClose:file=>{staged=file;fs.writeFileSync(file,Buffer.alloc(raw.length,120));}});
 await assert.rejects(p.immutable('pointers/'+('6'.repeat(64))+'.json',raw),/Owned module file integrity/);assert.equal(reached(),true);assert.deepEqual(fs.readFileSync(staged),Buffer.alloc(raw.length,120));
});

for(const replacement of ['regular','hardlink','junction'])test(`immutable cleanup preserves a ${replacement} replacement instead of rebasing ownership`,async t=>{
 const f=fixture(t),p=new GitHubModules(f.options);await p.ensureCache(f.selected);const raw=Buffer.from('original'),foreign=path.join(f.original,'foreign');let staged,backup;
 if(replacement==='junction'){fs.mkdirSync(foreign);fs.writeFileSync(path.join(foreign,'sentinel'),'foreign');}else fs.writeFileSync(foreign,'foreign');
 const reached=onMetadataClose(t,file=>{staged=file;backup=file+'.owned';fs.renameSync(file,backup);if(replacement==='regular')fs.writeFileSync(file,'foreign');else if(replacement==='hardlink')fs.linkSync(foreign,file);else fs.symlinkSync(foreign,file,process.platform==='win32'?'junction':'dir');});
 await assert.rejects(p.immutable('pointers/'+('3'.repeat(64))+'.json',raw));assert.equal(reached(),true);assert.deepEqual(fs.readFileSync(backup),raw);
 if(replacement==='junction'){assert.equal(fs.lstatSync(staged).isSymbolicLink(),true);assert.equal(fs.readFileSync(path.join(foreign,'sentinel'),'utf8'),'foreign');}else assert.equal(fs.readFileSync(staged,'utf8'),'foreign');
 if(replacement==='hardlink')assert.equal(fs.statSync(foreign).nlink,2);
});

test('immutable exclusive publication never replaces a concurrently created destination',async t=>{
 const f=fixture(t),p=new GitHubModules(f.options);await p.ensureCache(f.selected);const link=fs.linkSync;let staged,published,reached=false;
 t.mock.method(fs,'linkSync',function(from,to){if(from.endsWith('.tmp')){staged=from;published=to;reached=true;fs.writeFileSync(to,'foreign');}return link.call(this,from,to);});
 await assert.rejects(p.immutable('pointers/'+('4'.repeat(64))+'.json',Buffer.from('original')),error=>error.code==='EEXIST');assert.equal(reached,true);assert.equal(fs.readFileSync(published,'utf8'),'foreign');assert.equal(fs.existsSync(staged),false);
});

test('immutable publication verifies linked bytes and preserves a changed linked pair on refusal',async t=>{
 const f=fixture(t),p=new GitHubModules(f.options);await p.ensureCache(f.selected);const link=fs.linkSync,raw=Buffer.from('original');let staged,published;
 t.mock.method(fs,'linkSync',function(from,to){const result=link.call(this,from,to);if(from.endsWith('.tmp')){staged=from;published=to;fs.writeFileSync(to,Buffer.alloc(raw.length,120));}return result;});
 await assert.rejects(p.immutable('pointers/'+('5'.repeat(64))+'.json',raw),error=>error.reason==='integrity');assert.deepEqual(fs.readFileSync(published),Buffer.alloc(raw.length,120));assert.equal(fs.statSync(staged).nlink,2);
});

test('failed seed cleanup retains its original writer receipt across asynchronous source verification',async t=>{
 const f=fixture(t),p=new GitHubModules(f.options);await p.ensureCache(f.selected);const source=path.join(f.original,'source'),destination=await p.file('staging/seed.fixture'),raw=Buffer.from('original');fs.writeFileSync(source,raw);
 const lstat=fs.promises.lstat;let count=0,backup;
 t.mock.method(fs.promises,'lstat',async function(file,...args){if(file===source&&++count===2){backup=destination+'.owned';fs.renameSync(destination,backup);fs.writeFileSync(destination,'foreign');}return lstat.call(this,file,...args);});
 assert.equal(await p.seed(source,destination,{bytes:raw.length,sha256:'0'.repeat(64)},f.selected),false);assert.equal(count,2);assert.equal(fs.readFileSync(destination,'utf8'),'foreign');assert.deepEqual(fs.readFileSync(backup),raw);assert.deepEqual(fs.readFileSync(source),raw);
});

test('successful seed refuses destination mutation during asynchronous source verification',async t=>{
 const f=fixture(t),p=new GitHubModules(f.options);await p.ensureCache(f.selected);const source=path.join(f.original,'source'),destination=await p.file('staging/seed.fixture'),raw=Buffer.from('original');fs.writeFileSync(source,raw);
 const lstat=fs.promises.lstat;let count=0;
 t.mock.method(fs.promises,'lstat',async function(file,...args){if(file===source&&++count===2)fs.writeFileSync(destination,Buffer.alloc(raw.length,120));return lstat.call(this,file,...args);});
 await assert.rejects(p.seed(source,destination,{bytes:raw.length,sha256:sha(raw)},f.selected),error=>error.reason==='integrity');assert.equal(count,2);assert.deepEqual(fs.readFileSync(destination),Buffer.alloc(raw.length,120));assert.deepEqual(fs.readFileSync(source),raw);
});

test('seed cleanup preserves different completed bytes with an identical observed full stamp',async t=>{
 const f=fixture(t),p=new GitHubModules(f.options);await p.ensureCache(f.selected);const source=path.join(f.original,'source'),destination=await p.file('staging/seed.fixture'),raw=Buffer.from('original');fs.writeFileSync(source,raw);let count=0;
 equalObservedTimes(t,{onLstat:file=>{if(file===source&&++count===2)fs.writeFileSync(destination,Buffer.alloc(raw.length,120));}});
 assert.equal(await p.seed(source,destination,{bytes:raw.length,sha256:'0'.repeat(64)},f.selected),false);assert.equal(count,2);assert.deepEqual(fs.readFileSync(destination),Buffer.alloc(raw.length,120));assert.deepEqual(fs.readFileSync(source),raw);
});

test('staging cleanup cannot remove an unknown directory, even with a valid UUID path',async t=>{
 const f=fixture(t),p=new GitHubModules(f.options);await p.ensureCache(f.selected);const directory=path.join(p.cacheRoot,'staging',require('node:crypto').randomUUID());fs.mkdirSync(directory);fs.writeFileSync(path.join(directory,'foreign'),'foreign');
 assert.equal(await p.removeStaging(directory),false);assert.equal(fs.readFileSync(path.join(directory,'foreign'),'utf8'),'foreign');
});

for(const mutation of ['bytes','extra','root','hardlink','junction'])test(`materialize preserves a ${mutation} mutation after the compiled validator and does not publish it`,async t=>{
 const f=fixture(t),adapter=f.options.registry['mentat.fixture.v1'];let file,staging,backup,reached=false;const foreign=path.join(f.original,'foreign');
 fs.mkdirSync(foreign);fs.writeFileSync(path.join(foreign,'sentinel'),'foreign');
 adapter.validateSnapshot=async({files,root})=>{reached=true;file=files.aggregate;staging=path.dirname(root);
  if(mutation==='bytes')fs.writeFileSync(file,Buffer.alloc(f.remote.bytes.length,120));
  if(mutation==='extra')fs.writeFileSync(path.join(staging,'foreign'),'foreign');
  if(mutation==='root'){backup=staging+'.owned';fs.renameSync(staging,backup);fs.mkdirSync(staging);fs.writeFileSync(path.join(staging,'foreign'),'foreign');}
  if(mutation==='hardlink'){backup=file+'.owned';fs.renameSync(file,backup);fs.writeFileSync(path.join(foreign,'linked'),'foreign');fs.linkSync(path.join(foreign,'linked'),file);}
  if(mutation==='junction'){const models=path.dirname(file);backup=models+'.owned';fs.renameSync(models,backup);fs.symlinkSync(foreign,models,process.platform==='win32'?'junction':'dir');}
  return true;
 };
 const p=new GitHubModules(f.options);await assert.rejects(p.prepare(f.selected));assert.equal(reached,true);assert.equal(fs.existsSync(path.join(p.cacheRoot,'snapshots',sha(f.remote.manifestBytes))),false);assert.equal(f.journal.active,null);assert.equal(f.journal.staged,null);
 assert.equal(fs.existsSync(staging),true);assert.equal(fs.readFileSync(path.join(foreign,'sentinel'),'utf8'),'foreign');
 if(mutation==='bytes')assert.deepEqual(fs.readFileSync(file),Buffer.alloc(f.remote.bytes.length,120));if(mutation==='extra'||mutation==='root')assert.equal(fs.readFileSync(path.join(staging,'foreign'),'utf8'),'foreign');
 if(mutation==='hardlink'){assert.equal(fs.readFileSync(file,'utf8'),'foreign');assert.equal(fs.statSync(file).nlink,2);}if(mutation==='junction')assert.equal(fs.lstatSync(path.dirname(file)).isSymbolicLink(),true);
});

test('a cancelled partial role is preserved rather than recursively cleaned as a completed member',async t=>{
 const f=fixture(t),controller=new AbortController(),send=f.transport.segment;let reached=false;
 f.transport.segment=async(...args)=>{if(!reached){reached=true;controller.abort();}return send(...args);};
 const p=new GitHubModules(f.options);await assert.rejects(p.prepare(f.selected,{signal:controller.signal}),error=>error.reason==='cancelled');assert.equal(reached,true);const stages=fs.readdirSync(path.join(p.cacheRoot,'staging'));assert.equal(stages.length,1);assert.equal(fs.existsSync(path.join(p.cacheRoot,'staging',stages[0],f.remote.manifest.datasets[0].datasetId,'models','aggregate.json')),true);assert.equal(f.journal.staged,null);
});

test('materialize refuses post-validator byte changes despite an identical observed full stamp',async t=>{
 const f=fixture(t);equalObservedTimes(t);let file,reached=false;f.options.registry['mentat.fixture.v1'].validateSnapshot=async({files})=>{reached=true;file=files.aggregate;fs.writeFileSync(file,Buffer.alloc(f.remote.bytes.length,120));return true;};const p=new GitHubModules(f.options);
 await assert.rejects(p.prepare(f.selected),/Owned module file integrity/);assert.equal(reached,true);assert.deepEqual(fs.readFileSync(file),Buffer.alloc(f.remote.bytes.length,120));assert.equal(f.journal.staged,null);
});

test('materialize rechecks the published tree before reporting success and preserves a changed result',async t=>{
 const f=fixture(t),p=new GitHubModules(f.options),rename=fs.renameSync;let reached=false,published,rejection;
 t.mock.method(fs,'renameSync',function(from,to){const result=rename.call(this,from,to);if(path.dirname(from)===path.join(p.cacheRoot,'staging')){reached=true;published=path.join(to,f.remote.manifest.datasets[0].datasetId,'models','aggregate.json');fs.writeFileSync(published,Buffer.alloc(f.remote.bytes.length,120));}return result;});
 try{await p.prepare(f.selected);}catch(error){rejection=error;}
 assert.equal(reached,true);assert.equal(rejection?.reason,'integrity');assert.deepEqual(fs.readFileSync(published),Buffer.alloc(f.remote.bytes.length,120));assert.equal(f.journal.staged,null);
});

test('a wholly owned completed staging tree is cleaned after a validator refusal',async t=>{
 const f=fixture(t);let reached=false;f.options.registry['mentat.fixture.v1'].validateSnapshot=async()=>{reached=true;return false;};const p=new GitHubModules(f.options);
 await assert.rejects(p.prepare(f.selected),/Compiled module reader/);assert.equal(reached,true);assert.deepEqual(fs.readdirSync(path.join(p.cacheRoot,'staging')),[]);assert.equal(f.journal.staged,null);
});

function changedStamp(t,file,field){
 const original=fs.promises.lstat;let calls=0;
 t.mock.method(fs.promises,'lstat',async function(target,options){
  const stat=await original.call(this,target,options);if(target!==file)return stat;
  const changed=calls++>0,big=options?.bigint===true;
  return new Proxy(stat,{get(object,key){if(key!==field)return Reflect.get(object,key,object);if(field==='ino')return big?9007199254740992n+BigInt(changed):Number(9007199254740992n+BigInt(changed));if(field==='dev')return big?BigInt(changed)+1n:Number(changed)+1;return big?1234567890000000000n+BigInt(changed):undefined;}});
 });
 return ()=>calls;
}

for(const field of ['ino','dev','mtimeNs','ctimeNs']){
 test(`file digests reject exact ${field} changes without Number precision loss`,async t=>{
  const f=fixture(t),file=path.join(f.original,'digest.fixture');fs.writeFileSync(file,'synthetic bytes');
  const calls=changedStamp(t,file,field);await assert.rejects(fileDigest(file),/changed during verification/);assert.equal(calls(),2);
 });
 test(`legacy seeding rejects exact ${field} changes without Number precision loss`,async t=>{
  const f=fixture(t),p=new GitHubModules(f.options);await p.ensureCache(f.selected);
  const source=path.join(f.original,'seed.fixture'),destination=await p.file('staging/seed.fixture');fs.writeFileSync(source,f.remote.bytes);
  const calls=changedStamp(t,source,field);assert.equal(await p.seed(source,destination,f.remote.manifest.datasets[0].objects[0],f.selected),false);
  assert.equal(calls(),2);assert.equal(fs.existsSync(destination),false);assert.deepEqual(fs.readFileSync(source),f.remote.bytes);
 });
}

for(const invalid of ['wrong-hash','oversized','prefix'])test(`${invalid} owned partial segments fail once and permit a later clean retry`,async t=>{
 const f=fixture(t),p=new GitHubModules(f.options);await p.ensureCache(f.selected);
 const item=f.remote.manifest.datasets[0].objects[0].segments[0],part=path.join(p.cacheRoot,'segments',item.sha256+'.part');
 fs.writeFileSync(part,Buffer.alloc(item.bytes+(invalid==='oversized'?1:invalid==='prefix'?-1:0),120));
 await assert.rejects(p.prepare(f.selected),error=>error.reason==='integrity');
 assert.equal(fs.existsSync(part),false);assert.equal(f.journal.active,null);assert.equal(f.requests.filter(x=>x===item.asset).length,invalid==='prefix'?1:0);
 const offsetCount=f.offsets.length,candidate=await p.prepare(f.selected);assert.equal(f.offsets[offsetCount],0);assert.deepEqual(fs.readFileSync(roleFile(candidate,f)),f.remote.bytes);assert.equal(f.journal.active,null);
});

for(const replacement of ['regular','hardlink','junction'])test(`partial cleanup preserves a ${replacement} replacement made while the verified handle closes`,async t=>{
 const f=fixture(t),p=new GitHubModules(f.options);await p.ensureCache(f.selected);
 const item=f.remote.manifest.datasets[0].objects[0].segments[0],part=path.join(p.cacheRoot,'segments',item.sha256+'.part'),foreign=path.join(f.original,'foreign.fixture');
 fs.writeFileSync(part,Buffer.alloc(item.bytes,120));if(replacement==='junction'){fs.mkdirSync(foreign);fs.writeFileSync(path.join(foreign,'sentinel.fixture'),'foreign synthetic bytes');}else fs.writeFileSync(foreign,'foreign synthetic bytes');
 const open=fs.promises.open;let swapped=false;
 t.mock.method(fs.promises,'open',async function(file,...args){
  const handle=await open.call(this,file,...args);if(file!==part)return handle;
  const close=handle.close.bind(handle);handle.close=async()=>{await close();if(!swapped){swapped=true;fs.unlinkSync(part);if(replacement==='hardlink')fs.linkSync(foreign,part);else if(replacement==='junction')fs.symlinkSync(foreign,part,process.platform==='win32'?'junction':'dir');else fs.renameSync(foreign,part);}};return handle;
 });
 await assert.rejects(p.prepare(f.selected),error=>error.reason==='integrity');assert.equal(swapped,true);
 if(replacement==='junction'){assert.equal(fs.lstatSync(part).isSymbolicLink(),true);assert.equal(fs.readFileSync(path.join(foreign,'sentinel.fixture'),'utf8'),'foreign synthetic bytes');}else assert.equal(fs.readFileSync(part,'utf8'),'foreign synthetic bytes');
 if(replacement==='hardlink')assert.equal(fs.readFileSync(foreign,'utf8'),'foreign synthetic bytes');assert.equal(f.journal.active,null);
});

test('an aliased approved LOCALAPPDATA ancestor yields the canonical fixed provider cache',async t=>{
 const f=fixture(t),local=path.join(f.temporary,'local-real'),alias=path.join(f.temporary,'local-alias');fs.mkdirSync(local);fs.symlinkSync(local,alias,process.platform==='win32'?'junction':'dir');
 const prior=process.env.LOCALAPPDATA;process.env.LOCALAPPDATA=alias;t.after(()=>{if(prior===undefined)delete process.env.LOCALAPPDATA;else process.env.LOCALAPPDATA=prior;});
 const p=new GitHubModules({...f.options,cacheRoot:path.join(alias,'MelangeData','mentat','github-module-data')}),canonical=path.join(fs.realpathSync.native(local),'MelangeData','mentat','github-module-data');
 const candidate=await p.prepare(f.selected);assert.equal(p.cacheRoot,canonical);assert.equal(candidate.effectiveConfiguration.ownerGitHubModuleData.cacheRoot,canonical);
 assert.throws(()=>new GitHubModules({...f.options,cacheRoot:path.join(f.temporary,'outside')}),/Unapproved/);
 assert.throws(()=>new GitHubModules({...f.options,cacheRoot:canonical,protectedRoots:[local]}),/overlaps/);
});

test('canonicalizing LOCALAPPDATA never blesses a reparse point below its fixed cache suffix',async t=>{
 const f=fixture(t),local=path.join(f.temporary,'local-real'),outside=path.join(f.temporary,'outside');fs.mkdirSync(local);fs.mkdirSync(outside);fs.writeFileSync(path.join(outside,'sentinel.fixture'),'unchanged');fs.symlinkSync(outside,path.join(local,'MelangeData'),process.platform==='win32'?'junction':'dir');
 const prior=process.env.LOCALAPPDATA;process.env.LOCALAPPDATA=local;t.after(()=>{if(prior===undefined)delete process.env.LOCALAPPDATA;else process.env.LOCALAPPDATA=prior;});
 const p=new GitHubModules({...f.options,cacheRoot:path.join(local,'MelangeData','mentat','github-module-data')});await assert.rejects(p.prepare(f.selected),error=>error.reason==='integrity');
 assert.deepEqual(fs.readdirSync(outside),['sentinel.fixture']);assert.equal(fs.readFileSync(path.join(outside,'sentinel.fixture'),'utf8'),'unchanged');assert.equal(f.journal,null);
});
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
for(const appId of ['melange','mentat'])test(`${appId} unchanged staged checks validate once while startup activation still verifies independently`,async t=>{
 const f=environment(appId);t.after(()=>f.cleanup());const p=new GitHubModules(f.options),first=await p.prepare(f.selected);await p.commitActive(first,f.selected);
 const before=structuredClone(f.journal),selected=structuredClone(f.selected),account=path.join(f.original,'account.fixture');fs.writeFileSync(account,'owner state');
 const validate=t.mock.method(p,'validateSnapshot'),adapter=t.mock.method(f.options.registry[appId+'.fixture.v1'],'validateSnapshot'),write=t.mock.method(f.store,'write');
 f.requests.length=0;const unchanged=await p.stage(f.selected);
 assert.equal(unchanged.status.phase,'ready');assert.equal(unchanged.status.updateAvailable,undefined);assert.equal(validate.mock.callCount(),1);assert.equal(adapter.mock.callCount(),1);assert.equal(write.mock.callCount(),1);
 assert.deepEqual(f.requests,['main','pointer','release','manifest']);assert.deepEqual(f.journal,before);assert.deepEqual(f.selected,selected);assert.equal(fs.readFileSync(account,'utf8'),'owner state');
 const prepared=await p.prepare(f.selected);assert.equal(validate.mock.callCount(),2);assert.equal(adapter.mock.callCount(),2);const requests=f.requests.length;
 await p.commitActive(prepared,f.selected);assert.equal(validate.mock.callCount(),3);assert.equal(adapter.mock.callCount(),3);assert.equal(f.requests.length,requests);assert.deepEqual(f.journal,before);
});
test('a restarted provider revalidates a staged newer snapshot once without activating or downloading it again',async t=>{
 const f=fixture(t),p=new GitHubModules(f.options);await p.commitActive(await p.prepare(f.selected),f.selected);next(f);await p.stage(f.selected);
 const before=structuredClone(f.journal),restarted=new GitHubModules(f.options),validate=t.mock.method(restarted,'validateSnapshot'),write=t.mock.method(f.store,'write');f.requests.length=0;
 const repeated=await restarted.stage(f.selected);assert.equal(repeated.status.phase,'update-ready');assert.equal(repeated.status.updateAvailable,true);assert.equal(validate.mock.callCount(),1);assert.equal(write.mock.callCount(),1);
 assert.deepEqual(f.requests,['main','pointer','release','manifest']);assert.deepEqual(f.journal,before);assert.equal(f.journal.active.catalogSequence,1);assert.equal(f.journal.staged.catalogSequence,2);
});
for(const [field,value] of Object.entries({catalogSequence:1,pointerDigest:'1'.repeat(64),manifestSha256:'2'.repeat(64),releaseTag:'module-data-2026-10-21-other',releaseCommit:'b'.repeat(40),identityDigest:'3'.repeat(64)}))test(`a different staged ${field} cannot skip materialization`,async t=>{
 const f=fixture(t);next(f);const p=new GitHubModules(f.options);await p.prepare(f.selected);const expected=structuredClone(f.journal.staged),state=structuredClone(f.journal);state.staged={...state.staged,[field]:value};await f.store.write(state);
 const materialize=t.mock.method(p,'materialize'),validate=t.mock.method(p,'validateSnapshot');await p.stage(f.selected);
 assert.equal(materialize.mock.callCount(),1);assert.equal(validate.mock.callCount(),2);assert.deepEqual(f.journal.staged,expected);assert.equal(f.journal.active,null);
});
test('an exact staged record with a missing snapshot rematerializes from verified segments',async t=>{
 const f=fixture(t),p=new GitHubModules(f.options),first=await p.prepare(f.selected),before=structuredClone(f.journal);fs.renameSync(first.snapshotRoot,path.join(f.temporary,'removed-snapshot'));
 const materialize=t.mock.method(p,'materialize');f.requests.length=0;const recovered=await p.prepare(f.selected);
 assert.equal(materialize.mock.callCount(),1);assert.deepEqual(fs.readFileSync(roleFile(recovered,f)),f.remote.bytes);assert.deepEqual(f.requests,['main','pointer','release','manifest']);assert.deepEqual(f.journal,before);
});
for(const mutation of ['bytes','extra','junction','hardlink','missing-role','reader'])test(`an exact staged record still refuses ${mutation} snapshot corruption`,async t=>{
 const f=fixture(t),p=new GitHubModules(f.options),first=await p.prepare(f.selected);await p.commitActive(first,f.selected);const before=structuredClone(f.journal),file=roleFile(first,f),backup=path.join(f.temporary,'original-snapshot');
 if(mutation==='bytes')fs.writeFileSync(file,Buffer.alloc(f.remote.bytes.length,120));
 if(mutation==='extra')fs.writeFileSync(path.join(first.snapshotRoot,'foreign'),'preserve');
 if(mutation==='junction'){fs.renameSync(first.snapshotRoot,backup);fs.symlinkSync(backup,first.snapshotRoot,process.platform==='win32'?'junction':'dir');}
 if(mutation==='hardlink'){const original=path.join(f.original,'original-role');fs.renameSync(file,original);fs.linkSync(original,file);}
 if(mutation==='missing-role')fs.renameSync(file,path.join(f.temporary,'missing-role'));
 if(mutation==='reader')f.options.registry['mentat.fixture.v1'].validateSnapshot=async()=>false;
 const materialize=t.mock.method(p,'materialize');await assert.rejects(p.stage(f.selected),error=>error.reason===(mutation==='missing-role'?'storage':'integrity'));
 assert.equal(materialize.mock.callCount(),0);assert.deepEqual(f.journal,before);if(mutation==='extra')assert.equal(fs.readFileSync(path.join(first.snapshotRoot,'foreign'),'utf8'),'preserve');
 if(mutation==='junction')assert.equal(fs.lstatSync(first.snapshotRoot).isSymbolicLink(),true);if(mutation==='hardlink')assert.equal(fs.statSync(file).nlink,2);
});
test('an exact staged record retains the final byte check after a reader mutation with identical observed timestamps',async t=>{
 const f=fixture(t),p=new GitHubModules(f.options),first=await p.prepare(f.selected);await p.commitActive(first,f.selected);const before=structuredClone(f.journal);equalObservedTimes(t);let reached=false;
 f.options.registry['mentat.fixture.v1'].validateSnapshot=async({files})=>{reached=true;fs.writeFileSync(files.aggregate,Buffer.alloc(f.remote.bytes.length,120));return true;};
 await assert.rejects(p.stage(f.selected),/Owned module file integrity/);assert.equal(reached,true);assert.deepEqual(f.journal,before);
});
for(const mutation of ['bytes','revoked','cancelled'])test(`an exact staged record refuses ${mutation} after accepted-state persistence`,async t=>{
 const f=fixture(t),p=new GitHubModules(f.options),first=await p.prepare(f.selected);await p.commitActive(first,f.selected);const before=structuredClone(f.journal),controller=new AbortController(),write=f.store.write;let reached=false;
 f.store.write=async value=>{await write(value);reached=true;if(mutation==='bytes')fs.writeFileSync(roleFile(first,f),Buffer.alloc(f.remote.bytes.length,120));if(mutation==='revoked')f.revoked=true;if(mutation==='cancelled')controller.abort();};
 await assert.rejects(p.stage(f.selected,{signal:controller.signal}),error=>error.reason===({bytes:'integrity',revoked:'authorization',cancelled:'cancelled'})[mutation]);assert.equal(reached,true);assert.deepEqual(f.journal,before);
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
 await assert.rejects(p.prepare(f.selected),error=>error.reason==='integrity');assert.equal(swapped,true);assert.equal(fs.readFileSync(account,'utf8'),'own');assert.equal(fs.statSync(account).nlink,2);assert.equal(f.journal.active,null);
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

test('paged mode with on-demand-current.json absent fails closed and never reads the legacy pointer',async t=>{
 const {EventEmitter}=require('node:events'),{Readable}=require('node:stream'),{GitHubModuleTransport}=require('../github-module-transport.cjs');
 const f=environment('melange');t.after(()=>f.cleanup());
 const legacy=new GitHubModules(f.options);await legacy.commitActive(await legacy.prepare(f.selected),f.selected);
 const before=structuredClone(f.journal),urls=[];
 // GitHub answers main normally; the paged pointer file does not exist (404).
 const request=(url,_options,callback)=>{const req=new EventEmitter();req.destroy=()=>{};urls.push(String(url));req.end=()=>queueMicrotask(()=>{
  const main=new URL(url).hostname==='api.github.com',bytes=Buffer.from(main?JSON.stringify({ref:'refs/heads/main',object:{type:'commit',sha:'b'.repeat(40)}}):'404: Not Found');
  const incoming=Readable.from([bytes]);incoming.statusCode=main?200:404;incoming.headers={'content-length':String(bytes.length)};callback(incoming);});return req;};
 const paged=new GitHubModules({...f.options,transport:new GitHubModuleTransport('melange',{request,paged:true})});
 // Refused as an integrity failure, so the offline fallback to the active (legacy) snapshot is not taken.
 await assert.rejects(paged.prepare(f.selected),error=>error.reason==='integrity');
 assert.ok(urls.some(url=>url.endsWith('/docs/desktop-data/on-demand-current.json')));
 assert.ok(!urls.some(url=>url.endsWith('/docs/desktop-data/current.json')));
 assert.deepEqual(f.journal,before);
});
