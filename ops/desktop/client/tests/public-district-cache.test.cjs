'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const {retirePublicDistrictCaches}=require('../public-district-cache.cjs');
const hash=value=>require('node:crypto').createHash('sha256').update(value).digest('hex');
function fixture(t){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'public-district-retirement-'));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
 const sha='a'.repeat(64),ids=['co-05','or-05','ct-01'];
 const manifest={sha256:sha,dataFiles:Object.fromEntries(ids.map(id=>[id,[{role:'scores.sqlite3',bytes:4,sha256:hash('data')},{role:'snapshots/example/rows.json',bytes:2,sha256:hash('[]')}]])),assets:new Map(ids.map((id,index)=>[id,{sha256:hash('zip'+index),bytes:4}]))};
 const cache=(namespace,id)=>path.join(root,'github-districts',namespace,sha,id);
 const put=(name,text)=>{fs.mkdirSync(path.dirname(name),{recursive:true});fs.writeFileSync(name,text);};
 for(const namespace of ['datasets','datasets-v2'])for(const id of ids){put(path.join(cache(namespace,id),'scores.sqlite3'),'data');if(namespace==='datasets-v2')put(path.join(cache(namespace,id),'snapshots/example/rows.json'),'[]');}
 for(const [index,asset]of [...manifest.assets.values()].entries())put(path.join(root,'github-districts/downloads',asset.sha256+'.zip'),'zip'+index);
 const configuration={district:'or-05',standaloneGitHubData:{schemaVersion:2,district:'or-05',cacheRoot:root,catalogueSha256:sha}};
 return {root,cache,put,manifest,configuration,run:()=>retirePublicDistrictCaches({root,configuration,manifests:[manifest]})};
}
test('retires known inactive public cache and archives while preserving active data and private state',async t=>{
 const f=fixture(t),state=path.join(f.root,'state/accounts.sqlite3'),journal=path.join(f.root,'protected-journal.json'),saved=path.join(f.root,'state/snapshots/example/rows.json');
 for(const file of [state,journal,saved])f.put(file,'user state');
 const result=await f.run();assert.equal(result.skipped.length,0);assert.equal(result.retired.length,6);
 assert.ok(fs.existsSync(f.cache('datasets-v2','or-05')));assert.ok(!fs.existsSync(f.cache('datasets','or-05')));assert.ok(!fs.existsSync(f.cache('datasets-v2','co-05')));
 assert.ok(fs.existsSync(path.join(f.root,'github-districts/downloads',f.manifest.assets.get('or-05').sha256+'.zip')));
 for(const file of [state,journal,saved])assert.equal(fs.readFileSync(file,'utf8'),'user state');
 assert.deepEqual(await f.run(),{retired:[],skipped:[]});
});
test('unknown files and changed downloaded files preserve their entire cache directories',async t=>{
 const f=fixture(t),custom=path.join(f.cache('datasets-v2','co-05'),'personal.txt');f.put(custom,'keep');
 const modified=path.join(f.cache('datasets-v2','ct-01'),'scores.sqlite3');f.put(modified,'edited data');
 const result=await f.run();assert.ok(result.skipped.includes(f.cache('datasets-v2','co-05')));assert.ok(result.skipped.includes(f.cache('datasets-v2','ct-01')));
 assert.equal(fs.readFileSync(custom,'utf8'),'keep');assert.equal(fs.readFileSync(modified,'utf8'),'edited data');assert.ok(fs.existsSync(path.join(f.cache('datasets-v2','co-05'),'scores.sqlite3')));
});
test('cache junctions cannot reach files outside their managed dataset',async t=>{
 const f=fixture(t),outside=path.join(f.root,'outside');f.put(path.join(outside,'scores.sqlite3'),'safe');
 const target=f.cache('datasets-v2','co-05');fs.rmSync(target,{recursive:true});fs.symlinkSync(outside,target,'junction');
 const result=await f.run();assert.ok(result.skipped.includes(target));assert.equal(fs.readFileSync(path.join(outside,'scores.sqlite3'),'utf8'),'safe');
});
test('same-size local modifications preserve the whole cache leaf and changed archives',async t=>{
 const f=fixture(t),target=f.cache('datasets-v2','co-05'),archive=path.join(f.root,'github-districts/downloads',f.manifest.assets.get('co-05').sha256+'.zip');
 f.put(path.join(target,'scores.sqlite3'),'edit');f.put(archive,'keep');const result=await f.run();
 assert.ok(result.skipped.includes(target));assert.ok(result.skipped.includes(archive));assert.equal(fs.readFileSync(archive,'utf8'),'keep');assert.equal(fs.readFileSync(path.join(target,'snapshots/example/rows.json'),'utf8'),'[]');
});
test('missing active cache or mismatched roots cannot trigger retirement',async t=>{
 const f=fixture(t);f.configuration.standaloneGitHubData.cacheRoot=path.join(f.root,'other');await assert.rejects(f.run(),/unsafe/);
 f.configuration.standaloneGitHubData.cacheRoot=f.root;fs.rmSync(f.cache('datasets-v2','or-05'),{recursive:true});await assert.rejects(f.run(),/unsafe/);
 assert.ok(fs.existsSync(f.cache('datasets-v2','co-05')));
});

function stagedFixture(f,{populate=true}={}){
 const manifest=structuredClone(f.manifest);manifest.sha256='b'.repeat(64);
 manifest.assets=new Map([...manifest.assets.keys()].map((id,index)=>[id,{sha256:hash('new'+index),bytes:4}]));
 const cache=(namespace,id)=>path.join(f.root,'github-districts',namespace,manifest.sha256,id),archive=id=>path.join(f.root,'github-districts/downloads',manifest.assets.get(id).sha256+'.zip');
 for(const [index,id]of [...manifest.assets.keys()].entries()){
  if(populate)for(const namespace of ['datasets','datasets-v2']){f.put(path.join(cache(namespace,id),'scores.sqlite3'),'data');if(namespace==='datasets-v2')f.put(path.join(cache(namespace,id),'snapshots/example/rows.json'),'[]');}
  f.put(archive(id),'new'+index);
 }
 const stagedGeneration={schemaVersion:2,district:'or-05',catalogueSha256:manifest.sha256};
 return {manifest,cache,archive,stagedGeneration,run:(value=stagedGeneration)=>retirePublicDistrictCaches({root:f.root,configuration:f.configuration,manifests:[f.manifest,manifest],stagedGeneration:value})};
}

test('retirement preserves the current active and staged generations and both archives, not other districts or namespaces',async t=>{
 const f=fixture(t),s=stagedFixture(f),result=await s.run();assert.deepEqual(result.skipped,[]);
 for(const target of [f.cache('datasets-v2','or-05'),s.cache('datasets-v2','or-05'),path.join(f.root,'github-districts/downloads',f.manifest.assets.get('or-05').sha256+'.zip'),s.archive('or-05')])assert.ok(fs.existsSync(target),target);
 for(const target of [f.cache('datasets','or-05'),s.cache('datasets','or-05'),s.cache('datasets-v2','co-05'),s.archive('co-05')])assert.ok(result.retired.includes(target),target);
 assert.deepEqual(await s.run(),{retired:[],skipped:[]});
});

test('archive hashes needed by a staged generation survive references from another catalogue and district',async t=>{
 const f=fixture(t),s=stagedFixture(f);f.manifest.assets.set('co-05',s.manifest.assets.get('or-05'));
 const result=await s.run();assert.ok(!result.retired.includes(s.archive('or-05')));assert.equal(fs.readFileSync(s.archive('or-05'),'utf8'),'new1');
});

test('a completed district switch retires prior unpacked generations while retaining a recent compressed download',async t=>{
 const f=fixture(t),s=stagedFixture(f);f.configuration.district='co-05';f.configuration.standaloneGitHubData.district='co-05';
 for(const asset of [...f.manifest.assets.values(),...s.manifest.assets.values()])fs.utimesSync(path.join(f.root,'github-districts/downloads',asset.sha256+'.zip'),1,1);fs.utimesSync(s.archive('or-05'),2,2);
 const result=await s.run(null);for(const target of [f.cache('datasets-v2','or-05'),s.cache('datasets-v2','or-05')])assert.ok(result.retired.includes(target),target);assert.ok(fs.existsSync(s.archive('or-05')));
 assert.ok(fs.existsSync(f.cache('datasets-v2','co-05')));
});

for(const [name,change]of [
 ['schema',value=>({...value,schemaVersion:1})],['district',value=>({...value,district:'co-05'})],['hash',value=>({...value,catalogueSha256:'../state'})],
 ['unknown catalogue',value=>({...value,catalogueSha256:'c'.repeat(64)})],['renderer path',value=>({...value,path:'C:\\private'})],['array',value=>[value]],['false',()=>false]
])test(`invalid staged protection (${name}) defers all retirement`,async t=>{
 const f=fixture(t),s=stagedFixture(f);await assert.rejects(s.run(change(s.stagedGeneration)),/unsafe/);
 for(const target of [f.cache('datasets-v2','co-05'),s.cache('datasets-v2','or-05'),s.archive('co-05')])assert.ok(fs.existsSync(target),target);
});

test('an unsafe staged directory defers all retirement without following its junction',async t=>{
 const f=fixture(t),s=stagedFixture(f,{populate:false}),outside=path.join(f.root,'outside'),target=s.cache('datasets-v2','or-05');
 f.put(path.join(outside,'private.txt'),'preserved');fs.mkdirSync(path.dirname(target),{recursive:true});fs.symlinkSync(outside,target,process.platform==='win32'?'junction':'dir');
 await assert.rejects(s.run(),/unsafe/);assert.equal(fs.readFileSync(path.join(outside,'private.txt'),'utf8'),'preserved');assert.ok(fs.existsSync(f.cache('datasets-v2','co-05')));assert.ok(fs.existsSync(s.archive('co-05')));
});

test('a missing staged directory still retains its signed archive for later reconstruction',async t=>{
 const f=fixture(t),s=stagedFixture(f,{populate:false});await s.run();assert.equal(fs.existsSync(s.cache('datasets-v2','or-05')),false);assert.equal(fs.readFileSync(s.archive('or-05'),'utf8'),'new1');
});

test('changed staged bytes are preserved for the next ordinary verification to reject',async t=>{
 const f=fixture(t),s=stagedFixture(f),file=path.join(s.cache('datasets-v2','or-05'),'scores.sqlite3');f.put(file,'edit');await s.run();assert.equal(fs.readFileSync(file,'utf8'),'edit');assert.ok(fs.existsSync(s.archive('or-05')));
});

test('staged protection is captured before asynchronous directory inspection',async t=>{
 const f=fixture(t),s=stagedFixture(f),lstat=fs.promises.lstat;let changed=false;
 t.mock.method(fs.promises,'lstat',async function(...args){if(!changed){changed=true;s.stagedGeneration.catalogueSha256='c'.repeat(64);s.stagedGeneration.district='ct-01';}return lstat.apply(this,args);});
 await s.run();assert.equal(changed,true);assert.ok(fs.existsSync(s.cache('datasets-v2','or-05')));assert.ok(fs.existsSync(s.archive('or-05')));
});

test('only the newest verified optional archive remains beside the required current archive',async t=>{
 const f=fixture(t),archive=id=>path.join(f.root,'github-districts/downloads',f.manifest.assets.get(id).sha256+'.zip');fs.utimesSync(archive('co-05'),1,1);fs.utimesSync(archive('ct-01'),2,2);
 const result=await f.run();assert.ok(result.retired.includes(archive('co-05')));assert.ok(fs.existsSync(archive('ct-01')));assert.ok(fs.existsSync(archive('or-05')));assert.equal(fs.readdirSync(path.dirname(archive('or-05'))).length,2);
});

test('future required archive overflow defers all cleanup with an explicit budget condition',async t=>{
 const f=fixture(t);f.manifest.assets.get('or-05').bytes=4*1024**3+1;
 await assert.rejects(f.run(),error=>error.code==='PUBLIC_ARCHIVE_BUDGET');assert.ok(fs.existsSync(f.cache('datasets-v2','co-05')));assert.equal(fs.readdirSync(path.join(f.root,'github-districts/downloads')).length,3);
});

for(const mutation of ['changed','link'])test(`a ${mutation} archive and unknown files survive outside the verified retention quota`,async t=>{
 const f=fixture(t),archive=id=>path.join(f.root,'github-districts/downloads',f.manifest.assets.get(id).sha256+'.zip'),unknown=path.join(f.root,'github-districts/downloads','f'.repeat(64)+'.zip'),outside=path.join(f.root,'private.fixture');f.put(unknown,'private unknown');f.put(outside,'safe');
 if(mutation==='changed')f.put(archive('ct-01'),'edit');else{const directory=path.join(f.root,'private-directory');f.put(path.join(directory,'keep'),'safe');fs.unlinkSync(archive('ct-01'));fs.symlinkSync(directory,archive('ct-01'),process.platform==='win32'?'junction':'dir');}
 const result=await f.run();assert.ok(result.skipped.includes(archive('ct-01')));assert.ok(fs.existsSync(archive('co-05')));assert.equal(fs.readFileSync(unknown,'utf8'),'private unknown');assert.equal(fs.readFileSync(outside,'utf8'),'safe');if(mutation==='changed')assert.equal(fs.readFileSync(archive('ct-01'),'utf8'),'edit');else assert.equal(fs.readFileSync(path.join(archive('ct-01'),'keep'),'utf8'),'safe');
});

test('an archive changed after hash verification is preserved by the final eviction identity guard',async t=>{
 const f=fixture(t),archive=id=>path.join(f.root,'github-districts/downloads',f.manifest.assets.get(id).sha256+'.zip'),target=archive('co-05');fs.utimesSync(target,1,1);fs.utimesSync(archive('ct-01'),2,2);
 const lstat=fs.promises.lstat;let calls=0;t.mock.method(fs.promises,'lstat',async function(file,...args){const value=await lstat.call(this,file,...args);if(file===target&&++calls===2)fs.writeFileSync(target,'edit');return value;});
 const result=await f.run();assert.ok(result.skipped.includes(target));assert.equal(fs.readFileSync(target,'utf8'),'edit');assert.ok(calls>=3);
});
