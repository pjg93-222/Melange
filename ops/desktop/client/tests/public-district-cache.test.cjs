'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const {retirePublicDistrictCaches}=require('../public-district-cache.cjs');
function fixture(t){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'public-district-retirement-'));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
 const sha='a'.repeat(64),ids=['co-05','or-05','ct-01'];
 const manifest={sha256:sha,dataFiles:Object.fromEntries(ids.map(id=>[id,[{role:'scores.sqlite3',bytes:4},{role:'snapshots/example/rows.json',bytes:2}]])),assets:new Map(ids.map((id,index)=>[id,{sha256:String(index+1).repeat(64),bytes:3}]))};
 const cache=(namespace,id)=>path.join(root,'github-districts',namespace,sha,id);
 const put=(name,text)=>{fs.mkdirSync(path.dirname(name),{recursive:true});fs.writeFileSync(name,text);};
 for(const namespace of ['datasets','datasets-v2'])for(const id of ids){put(path.join(cache(namespace,id),'scores.sqlite3'),'data');if(namespace==='datasets-v2')put(path.join(cache(namespace,id),'snapshots/example/rows.json'),'[]');}
 for(const asset of manifest.assets.values())put(path.join(root,'github-districts/downloads',asset.sha256+'.zip'),'zip');
 const configuration={district:'or-05',standaloneGitHubData:{schemaVersion:2,district:'or-05',cacheRoot:root,catalogueSha256:sha}};
 return {root,cache,put,manifest,configuration,run:()=>retirePublicDistrictCaches({root,configuration,manifests:[manifest]})};
}
test('retires known inactive public cache and archives while preserving active data and private state',async t=>{
 const f=fixture(t),state=path.join(f.root,'state/accounts.sqlite3'),journal=path.join(f.root,'protected-journal.json'),saved=path.join(f.root,'state/snapshots/example/rows.json');
 for(const file of [state,journal,saved])f.put(file,'user state');
 const result=await f.run();assert.equal(result.skipped.length,0);assert.equal(result.retired.length,7);
 assert.ok(fs.existsSync(f.cache('datasets-v2','or-05')));assert.ok(!fs.existsSync(f.cache('datasets','or-05')));assert.ok(!fs.existsSync(f.cache('datasets-v2','co-05')));
 assert.ok(fs.existsSync(path.join(f.root,'github-districts/downloads','2'.repeat(64)+'.zip')));
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
test('missing active cache or mismatched roots cannot trigger retirement',async t=>{
 const f=fixture(t);f.configuration.standaloneGitHubData.cacheRoot=path.join(f.root,'other');await assert.rejects(f.run(),/unsafe/);
 f.configuration.standaloneGitHubData.cacheRoot=f.root;fs.rmSync(f.cache('datasets-v2','or-05'),{recursive:true});await assert.rejects(f.run(),/unsafe/);
 assert.ok(fs.existsSync(f.cache('datasets-v2','co-05')));
});
