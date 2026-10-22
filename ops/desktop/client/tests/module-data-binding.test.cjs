'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const {spawnSync}=require('node:child_process');
const {canonical}=require('../access-client.cjs');
const {GitHubModules}=require('../github-modules.cjs');
const {validateModuleBinding}=require('../module-data-binding.cjs');
const {environment,signed,sha}=require('./fixtures/github-module-fixture.cjs');
async function fixture(t,appId='mentat'){
 const f=environment(appId);t.after(()=>f.cleanup());
 f.selected.connection={schemaVersion:1,console:'original-console',reports:'original-report-output'};
 const candidate=await new GitHubModules(f.options).prepare(f.selected);
 const options={appId,profile:f.profile,configuration:structuredClone(candidate.effectiveConfiguration),publicKeys:f.options.publicKeys,registry:f.options.registry};
 return {...f,candidate,options,role:path.join(candidate.snapshotRoot,f.remote.manifest.datasets[0].datasetId,'models','aggregate.json'),cache:f.options.cacheRoot};
}
function metadataFiles(f){return {pointer:path.join(f.cache,'pointers',f.candidate.pointerDigest+'.json'),manifest:path.join(f.cache,'manifests',f.candidate.manifestSha256+'.json')};}
function inventory(root){
 const result=[];
 function walk(directory){for(const entry of fs.readdirSync(directory,{withFileTypes:true})){const file=path.join(directory,entry.name),st=fs.lstatSync(file,{bigint:true});result.push([path.relative(root,file),String(st.ino),String(st.size),String(st.mtimeNs),String(st.ctimeNs),entry.isFile()?sha(fs.readFileSync(file)):null]);if(entry.isDirectory())walk(file);}}
 walk(root);return result;
}
function windowsShortPath(directory){
 const script=[
  "Add-Type -TypeDefinition 'using System; using System.Text; using System.Runtime.InteropServices; public static class ModuleBindingShortPath { [DllImport(\"kernel32.dll\", CharSet=CharSet.Unicode, SetLastError=true)] public static extern uint GetShortPathName(string path, StringBuilder buffer, uint capacity); }'",
  '$pathBuffer = New-Object System.Text.StringBuilder 32768',
  '$pathLength = [ModuleBindingShortPath]::GetShortPathName($env:MODULE_BINDING_FIXTURE_DIRECTORY, $pathBuffer, 32768)',
  "if ($pathLength -eq 0 -or $pathLength -ge 32768) { throw 'Fixture short path could not be resolved' }",
  '[Console]::Out.Write($pathBuffer.ToString())'
 ].join('\n');
 const result=spawnSync('powershell.exe',['-NoProfile','-NonInteractive','-Command','-'],{input:script,encoding:'utf8',windowsHide:true,timeout:30000,env:{...process.env,MODULE_BINDING_FIXTURE_DIRECTORY:directory}});
 assert.ifError(result.error);assert.equal(result.status,0,result.stderr);
 const short=result.stdout.trim();assert.ok(short);return short;
}
async function localAliasFixture(t,{shortPath=false}={}){
 const f=environment('mentat');t.after(()=>f.cleanup());
 const local=path.join(f.temporary,'Native Local Application Data Binding');fs.mkdirSync(local);
 let configuredLocal;
 if(shortPath){
  configuredLocal=windowsShortPath(local);
  if(path.resolve(configuredLocal).toLowerCase()===path.resolve(local).toLowerCase()){t.skip('The isolated filesystem does not provide a distinct Windows short path');return null;}
 }else{
  configuredLocal=path.join(f.temporary,'local-app-data-alias');fs.symlinkSync(local,configuredLocal,process.platform==='win32'?'junction':'dir');
 }
 const previous=process.env.LOCALAPPDATA;t.after(()=>{if(previous===undefined)delete process.env.LOCALAPPDATA;else process.env.LOCALAPPDATA=previous;});
 process.env.LOCALAPPDATA=configuredLocal;
 const localBase=fs.realpathSync.native(local),cacheRoot=path.join(localBase,'MelangeData','mentat','github-module-data');
 const candidate=await new GitHubModules({...f.options,cacheRoot:path.join(configuredLocal,'MelangeData','mentat','github-module-data')}).prepare(f.selected);
 const options={appId:'mentat',profile:f.profile,configuration:candidate.effectiveConfiguration,publicKeys:f.options.publicKeys,registry:f.options.registry};
 return {...f,local:localBase,configuredLocal,cacheRoot,candidate,options};
}
test('both app bindings independently derive signed roles while preserving configuration, account and journal bytes',async t=>{
 for(const appId of ['melange','mentat']){
  const f=await fixture(t,appId),account=path.join(f.original,'account.fixture');fs.writeFileSync(account,'original account');
  const before=inventory(f.temporary),configuration=structuredClone(f.options.configuration),requests=f.requests.length,journal=await f.store.read();
  const actual=await validateModuleBinding(f.options);
  assert.deepEqual(actual.source,configuration.ownerGitHubModuleData);assert.equal(actual.snapshotRoot,f.candidate.snapshotRoot);
  assert.deepEqual(actual.datasets[0].objects,f.remote.manifest.datasets[0].objects);assert.equal(actual.datasets[0].files.aggregate,f.role);
  assert.deepEqual(f.options.configuration,configuration);assert.deepEqual(await f.store.read(),journal);assert.equal(f.requests.length,requests);assert.deepEqual(inventory(f.temporary),before);
 }
});
test('the binding requires no segment cache, network, journal or owner side effect',async t=>{
 const f=await fixture(t);fs.rmSync(path.join(f.cache,'segments'),{recursive:true});
 const actual=await validateModuleBinding(f.options);assert.equal(actual.datasets.length,1);assert.equal(fs.existsSync(path.join(f.cache,'segments')),false);
});
test('a missing cache or role fails without creating directories or changing original state',async t=>{
 const f=await fixture(t);fs.unlinkSync(f.role);const before=inventory(f.temporary);await assert.rejects(validateModuleBinding(f.options));assert.deepEqual(inventory(f.temporary),before);
 fs.rmSync(f.cache,{recursive:true});const missing=inventory(f.temporary);await assert.rejects(validateModuleBinding(f.options));assert.deepEqual(inventory(f.temporary),missing);
});
test('all nine source fields must equal authenticated pointer and native cache derivation',async t=>{
 const f=await fixture(t);
 const changes=[s=>s.schemaVersion=2,s=>s.appId='melange',s=>s.repository='other/repo',s=>s.catalogSequence++,s=>s.releaseTag='module-data-2026-10-22',s=>s.releaseCommit='b'.repeat(40),s=>s.pointerDigest='b'.repeat(64),s=>s.manifestSha256='c'.repeat(64),s=>s.cacheRoot=f.original,s=>s.extra='untrusted',s=>delete s.releaseCommit];
 for(const change of changes){const configuration=structuredClone(f.options.configuration);change(configuration.ownerGitHubModuleData);await assert.rejects(validateModuleBinding({...f.options,configuration}),error=>error.reason==='integrity');}
});
test('a settings-like absent marker or other workspace override is not a binding',async t=>{
 const f=await fixture(t);const configuration=structuredClone(f.selected);
 await assert.rejects(validateModuleBinding({...f.options,configuration}));
 await assert.rejects(validateModuleBinding({...f.options,configuration:{...f.options.configuration,ownerGitHubData:{cacheRoot:f.cache}}}));
});
test('untrusted signatures, cross-app public keys and changed signed manifest bytes are rejected before readers',async t=>{
 const f=await fixture(t),files=metadataFiles(f);let calls=0;f.options.registry['mentat.fixture.v1'].validateSnapshot=async()=>{calls++;return true;};
 const pointer=fs.readFileSync(files.pointer),manifest=fs.readFileSync(files.manifest),bad=JSON.parse(pointer);bad.signature=Buffer.alloc(64).toString('base64');fs.writeFileSync(files.pointer,canonical(bad));
 await assert.rejects(validateModuleBinding(f.options));fs.writeFileSync(files.pointer,pointer);
 await assert.rejects(validateModuleBinding({...f.options,publicKeys:signed('melange').publicKeys}));
 fs.writeFileSync(files.manifest,Buffer.concat([manifest,Buffer.from(' ')]));await assert.rejects(validateModuleBinding(f.options));assert.equal(calls,0);
});
test('compiled required kinds and exact file bytes are enforced before reader acceptance',async t=>{
 const f=await fixture(t);await assert.rejects(validateModuleBinding({...f.options,requiredKinds:['mentat.missing.v1']}));
 const bytes=fs.readFileSync(f.role);fs.writeFileSync(f.role,Buffer.alloc(bytes.length,120));await assert.rejects(validateModuleBinding(f.options),/integrity/);
});
test('unexpected snapshot files and empty directories fail exact closure',async t=>{
 const f=await fixture(t),extra=path.join(f.candidate.snapshotRoot,'unexpected');fs.mkdirSync(extra);await assert.rejects(validateModuleBinding(f.options),/Unexpected/);fs.rmdirSync(extra);
 fs.writeFileSync(extra,'unlisted');await assert.rejects(validateModuleBinding(f.options),/Unexpected/);
});
test('protected/account workspace overlap is refused even for otherwise signed data',async t=>{
 const f=await fixture(t);await assert.rejects(validateModuleBinding({...f.options,protectedRoots:[f.cache]}),/overlaps/);
 await assert.rejects(validateModuleBinding({...f.options,configuration:{...f.options.configuration,dataDirectory:f.profile}}),/overlaps/);
});
test('snapshot hardlinks cannot read an original account as a logical role',async t=>{
 const f=await fixture(t),account=path.join(f.original,'account.fixture');fs.writeFileSync(account,f.remote.bytes);fs.unlinkSync(f.role);fs.linkSync(account,f.role);
 await assert.rejects(validateModuleBinding(f.options),/unsafe/);assert.deepEqual(fs.readFileSync(account),f.remote.bytes);
});
test('metadata hardlinks and parent directory junctions are rejected',async t=>{
 const f=await fixture(t),files=metadataFiles(f),original=path.join(f.original,'metadata.fixture');fs.writeFileSync(original,fs.readFileSync(files.pointer));fs.unlinkSync(files.pointer);fs.linkSync(original,files.pointer);
 await assert.rejects(validateModuleBinding(f.options),/unsafe/);fs.unlinkSync(files.pointer);fs.writeFileSync(files.pointer,fs.readFileSync(original));
 const dataset=path.dirname(path.dirname(f.role)),outside=path.join(f.original,'models');fs.renameSync(path.join(dataset,'models'),outside);fs.symlinkSync(outside,path.join(dataset,'models'),process.platform==='win32'?'junction':'dir');
 await assert.rejects(validateModuleBinding(f.options),/unsafe|reparse/);
});
test('a role swapped to a hardlink during open is refused by the opened handle identity',async t=>{
 const f=await fixture(t),account=path.join(f.original,'account.fixture');fs.writeFileSync(account,f.remote.bytes);
 const open=fs.promises.open.bind(fs.promises);let swapped=false;
 t.mock.method(fs.promises,'open',async(file,...args)=>{if(file===f.role&&!swapped){swapped=true;fs.unlinkSync(f.role);fs.linkSync(account,f.role);}return open(file,...args);});
 await assert.rejects(validateModuleBinding(f.options),/unsafe/);assert.equal(swapped,true);assert.deepEqual(fs.readFileSync(account),f.remote.bytes);
});
test('typed probes cannot turn corrupt, changed or canceled snapshots into a successful binding',async t=>{
 const f=await fixture(t),adapter=f.options.registry['mentat.fixture.v1'];adapter.validateSnapshot=async()=>false;await assert.rejects(validateModuleBinding(f.options),/reader/);
 adapter.validateSnapshot=async()=>{fs.writeFileSync(f.role,Buffer.alloc(f.remote.bytes.length,120));return true;};await assert.rejects(validateModuleBinding(f.options),/changed/);
 fs.writeFileSync(f.role,f.remote.bytes);const controller=new AbortController();adapter.validateSnapshot=async()=>{controller.abort();return true;};await assert.rejects(validateModuleBinding({...f.options,signal:controller.signal}),error=>error.reason==='cancelled');
 const before=inventory(f.temporary);await assert.rejects(validateModuleBinding({...f.options,signal:controller.signal}),error=>error.reason==='cancelled');assert.deepEqual(inventory(f.temporary),before);
});
test('configuration and cached metadata mutations during reader awaits fail closed',async t=>{
 const f=await fixture(t),files=metadataFiles(f),adapter=f.options.registry['mentat.fixture.v1'];
 adapter.validateSnapshot=async()=>{f.options.configuration.connection.console='different';return true;};await assert.rejects(validateModuleBinding(f.options),/configuration changed/);
 adapter.validateSnapshot=async()=>{fs.appendFileSync(files.pointer,' ');return true;};await assert.rejects(validateModuleBinding(f.options),/changed/);
});
test('the second allowed cache is app-scoped LOCALAPPDATA, with no arbitrary sibling selection',async t=>{
 const f=environment('mentat');t.after(()=>f.cleanup());const previous=process.env.LOCALAPPDATA;
 const local=path.join(f.temporary,'local-app-data');fs.mkdirSync(local);process.env.LOCALAPPDATA=local;
 try{
  const cacheRoot=path.join(local,'MelangeData','mentat','github-module-data'),candidate=await new GitHubModules({...f.options,cacheRoot}).prepare(f.selected);
  const options={appId:'mentat',profile:f.profile,configuration:candidate.effectiveConfiguration,publicKeys:f.options.publicKeys,registry:f.options.registry};
  assert.equal((await validateModuleBinding(options)).source.cacheRoot,cacheRoot);
  const configuration=structuredClone(candidate.effectiveConfiguration);configuration.ownerGitHubModuleData.cacheRoot=path.join(local,'MelangeData','melange','github-module-data');
  await assert.rejects(validateModuleBinding({...options,configuration}),/Unapproved/);
 }finally{if(previous===undefined)delete process.env.LOCALAPPDATA;else process.env.LOCALAPPDATA=previous;}
});
test('unrelated native profile activity does not replace the checked cache identity',async t=>{
 const f=await fixture(t);f.options.registry['mentat.fixture.v1'].validateSnapshot=async()=>{fs.writeFileSync(path.join(f.profile,'unrelated-native.fixture'),'separate local state');return true;};
 assert.equal((await validateModuleBinding(f.options)).snapshotRoot,f.candidate.snapshotRoot);
});

test('a real LOCALAPPDATA alias derives the exact canonical descriptor without approving source aliases, outside roots or original state',async t=>{
 const f=await localAliasFixture(t),account=path.join(f.original,'account.fixture');fs.writeFileSync(account,'original account bytes');
 const before=inventory(f.temporary),configuration=structuredClone(f.options.configuration),requests=f.requests.length;
 const actual=await validateModuleBinding(f.options);
 assert.equal(actual.source.cacheRoot,f.cacheRoot);assert.deepEqual(actual.source,configuration.ownerGitHubModuleData);assert.equal(actual.snapshotRoot,f.candidate.snapshotRoot);
 const aliasRoot=path.join(f.configuredLocal,'MelangeData','mentat','github-module-data');assert.notEqual(aliasRoot,f.cacheRoot);
 for(const cacheRoot of [aliasRoot,path.join(f.local,'MelangeData','mentat','outside-cache'),path.join(f.local,'MelangeData','melange','github-module-data')]){
  const changed=structuredClone(configuration);changed.ownerGitHubModuleData.cacheRoot=cacheRoot;
  await assert.rejects(validateModuleBinding({...f.options,configuration:changed}),/Unapproved/);
 }
 await assert.rejects(validateModuleBinding({...f.options,configuration:{...configuration,dataDirectory:f.local}}),/overlaps/);
 await assert.rejects(validateModuleBinding({...f.options,protectedRoots:[f.configuredLocal]}),/overlaps/);
 assert.deepEqual(f.options.configuration,configuration);assert.equal(f.requests.length,requests);assert.deepEqual(inventory(f.temporary),before);assert.equal(fs.readFileSync(account,'utf8'),'original account bytes');
});

test('canonical LOCALAPPDATA handling does not resolve away a cache-descendant directory junction',async t=>{
 const f=await localAliasFixture(t),managed=path.join(f.local,'MelangeData'),outside=path.join(f.temporary,'outside-cache-branch');
 fs.renameSync(managed,outside);fs.symlinkSync(outside,managed,process.platform==='win32'?'junction':'dir');
 const before=inventory(f.temporary),requests=f.requests.length;
 await assert.rejects(validateModuleBinding(f.options),/unsafe|boundary|overlaps/);
 assert.deepEqual(inventory(f.temporary),before);assert.equal(f.requests.length,requests);
});

test('a real Windows short LOCALAPPDATA path binds to the provider canonical cache identity',async t=>{
 if(process.platform!=='win32'){t.skip('Windows native short paths are platform-specific');return;}
 const f=await localAliasFixture(t,{shortPath:true});if(!f)return;
 assert.equal(fs.realpathSync.native(f.configuredLocal),f.local);
 const before=inventory(f.temporary),actual=await validateModuleBinding(f.options);
 assert.equal(actual.source.cacheRoot,f.cacheRoot);assert.deepEqual(actual.source,f.candidate.effectiveConfiguration.ownerGitHubModuleData);
 assert.deepEqual(inventory(f.temporary),before);
});
