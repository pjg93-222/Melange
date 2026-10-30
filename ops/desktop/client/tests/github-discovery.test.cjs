'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path'),crypto=require('node:crypto');
const {spawnSync}=require('node:child_process');
const {DiscoveryCache,rateLimit,deadline,TTL,JITTER,MANUAL_INTERVAL,MAX_DELAY}=require('../github-discovery.cjs');
const {GitHubSource,discoveryMetadata}=require('../github-source.cjs');
const repo='owner/releases';
function directory(t){const value=fs.mkdtempSync(path.join(os.tmpdir(),'github-discovery-'));t.after(()=>fs.rmSync(value,{recursive:true,force:true}));return value;}
function release(version='1.0.0'){
 const assets=['melange','mentat','terrier'].flatMap(app=>[app+'-win32-x64.manifest.json',app+'-trust.json',app+'-'+version+'-win32-x64.exe']).map(name=>({name,size:10,browser_download_url:'https://github.com/'+repo+'/releases/download/desktop-v'+version+'/'+name}));
 return {draft:false,prerelease:false,tag_name:'desktop-v'+version,assets};
}
const fixtureKeys=crypto.generateKeyPairSync('ed25519');
function pointer(appId='terrier',version='1.0.0',repository=repo){
 const body={schemaVersion:1,purpose:'melange-desktop-github-release',distribution:'public-installations',repository,appId,version,sequence:Number(version.split('.').at(-1))+1,platform:'win32',arch:'x64',sourceRefs:Object.fromEntries(['melange','mentat','terrier'].map(app=>[app,{repository:'owner/'+app,ref:'main',commit:'a'.repeat(40)}])),package:{name:appId+'-'+version+'-win32-x64.exe',size:10}};
 const bytes=Buffer.from(JSON.stringify(body));return {schemaVersion:1,keyId:'fixture',payload:bytes.toString('base64'),signature:crypto.sign(null,bytes,fixtureKeys.privateKey).toString('base64')};
}
function options(t,extra={}){return {directory:directory(t),repository:repo,validate:values=>discoveryMetadata(values,repo),random:()=>0,...extra};}
test('same-app receivers and restarts share one refresh until the cache expires before the next 15-minute timer',async t=>{
 const root=directory(t);let now=Date.now(),calls=0;
 const create=appId=>new GitHubSource({appId,repository:repo,cacheDirectory:root,cacheOptions:{now:()=>now,random:()=>0.5},readJSON:async()=>{calls++;return [release()];}});
 const sources=['melange','melange','melange'].map(create);
 for(const source of sources)assert.equal((await source.latest()).version,'1.0.0');assert.equal(calls,1);
 assert.match(sources[2].discoverySummary(),/cached release list checked.*Next discovery/);
 assert.equal(TTL,14*60*1000);assert.equal(JITTER,0);
 now+=TTL-1;assert.equal((await create('melange').latest()).version,'1.0.0');assert.equal(calls,1);
 now++;await create('melange').latest();assert.equal(calls,2);
 const independent=new GitHubSource({appId:'melange',repository:'owner/other',cacheDirectory:root,readJSON:async()=>{calls++;return [JSON.parse(JSON.stringify(release()).replaceAll('owner/releases','owner/other'))];}});await independent.latest();assert.equal(calls,3);
});
test('upgraded receivers shorten a valid legacy six-hour cache without deleting its usable metadata',async t=>{
 const root=directory(t);let now=Date.now(),calls=0,version='1.0.25';
 const create=()=>new GitHubSource({appId:'terrier',repository:repo,cacheDirectory:root,cacheOptions:{now:()=>now,random:()=>0},readJSON:async()=>{calls++;return [release(version)];}});
 const initial=create();await initial.latest();const checked=now,legacyNext=checked+6*60*60*1000+20*60*1000;
 const db=initial.cache.cacheDB();db.prepare('UPDATE discovery SET next=? WHERE id=1').run(legacyNext);db.close();
 version='1.0.26';now+=TTL-1;const upgraded=create();assert.equal((await upgraded.latest()).version,'1.0.25');assert.equal(calls,1);
 assert.equal(upgraded.discoveryInfo.nextCheckAt,checked+TTL);
 now++;assert.equal((await upgraded.latest()).version,'1.0.26');assert.equal(calls,2);assert.equal(upgraded.discoveryInfo.cached,false);
 const stored=upgraded.cache.cacheDB();try{const row=stored.prepare('SELECT checked,next FROM discovery WHERE id=1').get();assert.equal(row.checked,now);assert.equal(row.next,now+TTL);}finally{stored.close();}
});
test('long-cache migration retains persisted API cooldown and offline fallback',async t=>{
 const root=directory(t);let now=Date.now(),calls=0,version='1.0.25';
 const create=()=>new GitHubSource({appId:'terrier',repository:repo,cacheDirectory:root,cacheOptions:{now:()=>now,random:()=>0},readJSON:async()=>{calls++;return [release(version)];}});
 const initial=create();await initial.latest();const checked=now;
 const db=initial.cache.cacheDB();db.prepare('UPDATE discovery SET next=? WHERE id=1').run(checked+6*60*60*1000);db.close();
 await initial.cache.note(rateLimit(429,{'retry-after':'3600'}));version='1.0.26';now+=15*60*1000;
 const upgraded=create();assert.equal((await upgraded.latest()).version,'1.0.25');assert.equal(calls,1);assert.equal(upgraded.discoveryInfo.backoffUntil,checked+3600000);
 await assert.rejects(upgraded.refreshDiscovery(),/API retry after/);assert.equal(calls,1);
 now=checked+3600001;assert.equal((await upgraded.latest()).version,'1.0.26');assert.equal(calls,2);
});
test('empty generic discovery caches across restarts, while signed trust/update consumes only one REST release list',async t=>{
 const config=options(t);let emptyCalls=0;assert.deepEqual(await new DiscoveryCache(config).get(async()=>{emptyCalls++;return [];}),[]);assert.deepEqual(await new DiscoveryCache(config).get(async()=>{emptyCalls++;return [];}),[]);assert.equal(emptyCalls,1);
 const root=directory(t);let calls=0;const source=new GitHubSource({appId:'melange',repository:repo,cacheDirectory:root,readJSON:async url=>{if(url.endsWith('/melange-trust.json'))return {transitions:[]};calls++;return [release()];}}),enrollment={source:'github',repository:repo,appId:'melange'};
 assert.deepEqual(await source.request(enrollment,'/v1/apps/melange/trust'),{transitions:[]});assert.equal(await source.request(enrollment,'/v1/apps/melange/updates?platform=win32&arch=x64&version=1.0.0'),null);assert.equal(calls,1);
});

test('manual checks discover 26 from a cached25 list before automatic expiry; repeated clicks share a recent success',async t=>{
 const root=directory(t);let now=Date.now(),calls=0,version='1.0.25';
 const create=()=>new GitHubSource({appId:'terrier',repository:repo,cacheDirectory:root,cacheOptions:{now:()=>now,random:()=>0},readJSON:async()=>{calls++;return [release(version)];}});
 const source=create();assert.equal((await source.latest()).version,'1.0.25');version='1.0.26';now+=MANUAL_INTERVAL;
 assert.equal((await source.latest()).version,'1.0.25');assert.equal(calls,1);
 assert.equal((await source.refreshDiscovery()).version,'1.0.26');assert.equal(calls,2);assert.equal(source.discoveryInfo.cached,false);
 assert.equal((await source.refreshDiscovery()).version,'1.0.26');assert.equal((await create().refreshDiscovery()).version,'1.0.26');assert.equal(calls,2);
 now+=MANUAL_INTERVAL-1;await source.refreshDiscovery();assert.equal(calls,2);
 now++;await source.refreshDiscovery();assert.equal(calls,3);
});
test('manual checks honor a persisted API cooldown and never disguise refresh failures as a current result',async t=>{
 const root=directory(t);let now=Date.now(),calls=0,failure=null;
 const create=()=>new GitHubSource({appId:'terrier',repository:repo,cacheDirectory:root,cacheOptions:{now:()=>now,random:()=>0},readJSON:async()=>{calls++;if(failure)throw failure;return [release('1.0.25')];}});
 const source=create();await source.latest();now+=MANUAL_INTERVAL;
 failure=new Error('offline fixture');await assert.rejects(source.refreshDiscovery(),/refresh deferred/);assert.equal(calls,2);assert.match(source.discoverySummary(),/Refresh deferred/);
 failure=rateLimit(429,{'retry-after':'3600'});await assert.rejects(source.refreshDiscovery(),/API retry after/);assert.equal(calls,3);
 const restarted=create();await assert.rejects(restarted.refreshDiscovery(),/API retry after/);assert.equal(calls,3);
 failure=null;now+=3600001;assert.equal((await restarted.refreshDiscovery()).version,'1.0.25');assert.equal(calls,4);
});
test('concurrent manual refreshes reuse the newly committed list and preserve bounded competing waits',async t=>{
 let now=Date.now(),calls=0,unblock,entered;
 const config=options(t,{now:()=>now,waitMs:100}),first=new DiscoveryCache(config),second=new DiscoveryCache(config);
 await first.get(async()=>[]);now+=MANUAL_INTERVAL;
 const begin=new Promise(resolve=>{entered=resolve;});
 const pending=first.get(async()=>{calls++;entered();await new Promise(resolve=>{unblock=resolve;});return [{version:'1.0.26',assets:release('1.0.26').assets}];},{forceRefresh:true});await begin;
 const competing=second.get(async()=>{calls++;return [];},{forceRefresh:true});unblock();
 const [fresh,shared]=await Promise.all([pending,competing]);assert.equal(fresh[0].version,'1.0.26');assert.deepEqual(shared,fresh);assert.equal(calls,1);
 now+=MANUAL_INTERVAL;const held=first.cacheDB();
 try{held.exec('BEGIN IMMEDIATE');let status;second.onStatus=value=>{status=value;};
  assert.equal((await second.get(async()=>{calls++;return [];},{forceRefresh:true}))[0].version,'1.0.26');
  assert.equal(calls,1);assert.equal(status.refreshDeferred,true);
 }finally{held.exec('ROLLBACK');held.close();}
});
test('API cooldown persists across restart and applies to release list and exact-tag recovery',async t=>{
 const root=directory(t);let now=Date.now(),calls=0,limited=false;
 const create=()=>new GitHubSource({appId:'melange',repository:repo,cacheDirectory:root,cacheOptions:{now:()=>now,random:()=>0},readJSON:async url=>{calls++;if(limited&&url.includes('/releases?'))throw rateLimit(429,{'retry-after':'3600'});if(url.includes('/releases/tags/'))return release();if(url.endsWith('.manifest.json'))return pointer('melange');return [release()];}});
 await create().latest();now+=TTL+1;limited=true;assert.equal((await create().latest()).version,'1.0.0');assert.equal(calls,2);
 const restarted=create();assert.equal((await restarted.latest()).version,'1.0.0');assert.equal(calls,2);assert.match(restarted.discoverySummary(),/API retry after/);
 await assert.rejects(restarted.request({source:'github',repository:repo,appId:'melange'},'/v1/apps/melange/recovery?platform=win32&arch=x64&version=1.0.0'),/API paused/);assert.equal(calls,2,'Recovery respects the same persisted API quota');
 now+=3600001;limited=false;await create().latest();assert.equal(calls,3);
 assert((await restarted.request({source:'github',repository:repo,appId:'melange'},'/v1/apps/melange/recovery?platform=win32&arch=x64&version=1.0.0')).payload);assert.equal(calls,5);
});

test('rate-limit classification distinguishes plain403 and parses bounded reset/date/fallback deadlines',()=>{
 const now=Date.now();assert.equal(rateLimit(403,{},'Repository access denied'),null);
 assert.equal(rateLimit(404),null);assert.equal(rateLimit(403,{},'You have exceeded a secondary rate limit').githubRateLimit,true);
 assert.equal(deadline(rateLimit(429,{'retry-after':'120'}),now,()=>0),now+120000);
 const date=new Date(Math.ceil(now/1000)*1000+120000).toUTCString();assert.equal(deadline(rateLimit(429,{'retry-after':date}),now,()=>0),Date.parse(date));
 const reset=Math.ceil(now/1000)+3600;assert.equal(deadline(rateLimit(403,{'x-ratelimit-remaining':'0','x-ratelimit-reset':String(reset)}),now,()=>0),reset*1000);
 assert.equal(deadline(rateLimit(429),now,()=>0),now+3600000);
 assert.equal(deadline(rateLimit(429,{'retry-after':'999999999999999999'}),now,()=>0),now+MAX_DELAY);
});
test('concurrent app refreshes serialize, wait is bounded, failed refresh releases the writer lock',async t=>{
 const config=options(t,{waitMs:100}),first=new DiscoveryCache(config),second=new DiscoveryCache(config);let unblock,entered,calls=0;
 const started=new Promise(resolve=>{entered=resolve;});const pending=first.get(async()=>{calls++;entered();await new Promise(resolve=>{unblock=resolve;});return [];});await started;
 await assert.rejects(second.get(async()=>{calls++;return [];}),/already refreshing/);assert.equal(calls,1);unblock();await pending;
 assert.deepEqual(await second.get(async()=>{calls++;return [];}),[]);assert.equal(calls,1);
 const failed=new DiscoveryCache(options(t));await assert.rejects(failed.get(async()=>{throw new Error('fixture fetch failed');}),/fixture/);assert.deepEqual(await failed.get(async()=>[]),[]);
});
test('SQLite releases a crashed process refresh lock without deleting another app state',async t=>{
 const config=options(t),cache=new DiscoveryCache(config);const modulePath=path.resolve(__dirname,'../github-discovery.cjs');
 const child=spawnSync(process.execPath,['-e',`const {DiscoveryCache}=require(${JSON.stringify(modulePath)});const c=new DiscoveryCache({directory:${JSON.stringify(config.directory)},repository:${JSON.stringify(repo)},validate:x=>x});const d=c.cacheDB();d.exec('BEGIN IMMEDIATE');process.exit(9);`],{timeout:30000,windowsHide:true,encoding:'utf8'});
 assert.equal(child.status,9,child.stderr);assert.deepEqual(await cache.get(async()=>[]),[]);
});
test('cached metadata and future clock bounds are revalidated before reuse',async t=>{
 let now=Date.now();const config=options(t,{now:()=>now}),cache=new DiscoveryCache(config);await cache.get(async()=>[]);
 let db=cache.cacheDB();db.prepare('UPDATE discovery SET checked=?,next=? WHERE id=1').run(now+86400000,now+86400000+TTL);db.close();let calls=0;await cache.get(async()=>{calls++;return [];});assert.equal(calls,1);
 const item={version:'1.0.0',assets:release().assets};item.assets[0].browser_download_url='https://evil.example/manifest';
 db=cache.cacheDB();db.prepare('UPDATE discovery SET payload=? WHERE id=1').run(JSON.stringify([item]));db.close();await cache.get(async()=>{calls++;return [];});assert.equal(calls,2);
 assert.throws(()=>discoveryMetadata([{version:'1.0.0',assets:[...release().assets,...release().assets]}],repo),/cached/);
 await cache.note(rateLimit(429));now-=86400000;assert.equal(cache.cooldown(),now+3600000);now+=3600001;assert.equal(cache.cooldown(),0);
});
