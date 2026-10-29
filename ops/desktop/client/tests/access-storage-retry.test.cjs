'use strict';
// M21: protected storage (access records and credentials) retries a timed-out call with backoff, a bounded number of
// times, then fails with the original timeout error. No hang, no endless loop, every timed-out child killed.
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const {EventEmitter}=require('node:events');
const childProcess=require('node:child_process');
// Replace spawn before the modules under test destructure it: each fake child either hangs or answers.
let plan=[],spawned=[];
childProcess.spawn=()=>{
  const child=new EventEmitter(),answer=plan.shift();child.killed=false;
  child.stdout=new EventEmitter();child.stderr={resume(){}};
  child.stdin={on(){},end(){if(answer)setImmediate(()=>{child.stdout.emit('data',Buffer.from(JSON.stringify(answer)));child.emit('close',0);});}};
  child.kill=()=>{child.killed=true;};spawned.push(child);return child;
};
const {protectedAccess,storageRetry,STORAGE_RETRY}=require('../access-state.cjs');
const {accessCredential}=require('../access-credentials.cjs');

test('shipped bound: three attempts of 15 s with 1 s and 2 s backoff stay under 60 s in total',()=>{
  assert.deepEqual(STORAGE_RETRY,{timeouts:[15000,15000,15000],backoff:[1000,2000]});
  assert.ok(STORAGE_RETRY.timeouts.reduce((a,b)=>a+b)+STORAGE_RETRY.backoff.reduce((a,b)=>a+b)<60000);
});

function fast(t){
  const saved={...STORAGE_RETRY};Object.assign(STORAGE_RETRY,{timeouts:[30,30,30],backoff:[5,5]});
  const resources=fs.mkdtempSync(path.join(os.tmpdir(),'access-retry-'));
  fs.mkdirSync(path.join(resources,'runtime','melange'),{recursive:true});
  fs.writeFileSync(path.join(resources,'runtime','melange',process.platform==='win32'?'desktop-backend.exe':'desktop-backend'),'');
  plan=[];spawned=[];
  t.after(()=>{Object.assign(STORAGE_RETRY,saved);fs.rmSync(resources,{recursive:true,force:true});});
  return resources;
}

test('storageRetry retries only a timeout, with the per-attempt timeout, and stops at the bound',async t=>{
  fast(t);const timeout=new Error('Protected access storage timed out');
  let seen=[];assert.equal(await storageRetry(async ms=>{seen.push(ms);if(seen.length<3)throw timeout;return 'ok';}),'ok');assert.deepEqual(seen,[30,30,30]);
  seen=[];await assert.rejects(storageRetry(async ms=>{seen.push(ms);throw timeout;}),/storage timed out/);assert.equal(seen.length,3,'bounded: no fourth attempt');
  seen=[];await assert.rejects(storageRetry(async()=>{seen.push(1);throw new Error('Protected access storage unavailable');}),/unavailable/);assert.equal(seen.length,1,'other failures are not retried');
});

test('protected access record: a slow first start succeeds on a later attempt; the hung child is killed',async t=>{
  const resources=fast(t);plan=[null,{value:{ok:1}}];
  assert.deepEqual(await protectedAccess({resources,appId:'melange',profile:'p',action:'read',kind:'state'}),{value:{ok:1}});
  assert.equal(spawned.length,2);assert.equal(spawned[0].killed,true);
});

test('protected access record: storage that never answers fails cleanly after the bounded attempts',async t=>{
  const resources=fast(t);plan=[null,null,null,null];const started=Date.now();
  await assert.rejects(protectedAccess({resources,appId:'melange',profile:'p',action:'write',kind:'state',value:{}}),/Protected access storage timed out/);
  assert.equal(spawned.length,3);assert.ok(spawned.every(child=>child.killed));assert.ok(Date.now()-started<2000);
});

test('access credential: retried on timeout, then fails cleanly when storage stays hung',async t=>{
  const resources=fast(t);plan=[null,{token:null}];
  assert.deepEqual(await accessCredential({resources,appId:'melange',deviceId:'d',scope:'access-token',action:'read'}),{token:null});
  assert.equal(spawned.length,2);assert.equal(spawned[0].killed,true);
  plan=[null,null,null];spawned=[];
  await assert.rejects(accessCredential({resources,appId:'melange',deviceId:'d',scope:'access-token',action:'delete'}),/Protected access storage timed out/);
  assert.equal(spawned.length,3);assert.ok(spawned.every(child=>child.killed));
});
