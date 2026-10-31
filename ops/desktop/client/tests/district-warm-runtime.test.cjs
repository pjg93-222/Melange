"use strict";
const test=require('node:test'),assert=require('node:assert/strict');
const {districtRuntime}=require('./fixtures/district-runtime-fixture.cjs');
// Actual Runtime and one-use signed-input lifecycle; only OS process, program
// census and loopback transport are synthetic. No installed app is launched.
test('accepted native district survives a new Windows session without replaying its consumed capability',async t=>{
 const f=await districtRuntime(t);await f.start();const child=f.runtime.child,session=(await f.gate.authorize()).session.sessionId;
 assert.equal(f.state.commits,1);assert.equal(f.state.closes,1);
 f.gate.local.lock();await f.gate.local.resume();assert.notEqual((await f.gate.authorize()).session.sessionId,session);
 await f.runtime.start(f.runtime.originalConfiguration());assert.equal(f.runtime.child,child);assert.equal(f.state.spawns,1);assert.equal(f.state.commits,1);assert.ok(f.state.checks>=4);
});
test('changed settings cannot borrow accepted district authority',async t=>{
 const f=await districtRuntime(t);await f.start();await assert.rejects(f.runtime.start({...f.runtime.originalConfiguration(),extra:'changed'}),{code:'program'});assert.equal(f.state.spawns,1);
});
for(const mode of ['stop','exit'])test(mode+' clears retained authority; restart requires a fresh capability',async t=>{
 const f=await districtRuntime(t);await f.start();const configuration=f.runtime.originalConfiguration();if(mode==='stop')await f.runtime.stop();else f.exit();
 await assert.rejects(f.runtime.start(configuration),{code:'program'});await f.start();assert.equal(f.state.spawns,2);assert.equal(f.state.commits,2);assert.equal(f.state.closes,2);
});
for(const field of ['pid','launchNonce','sourceDigest','rootsDigest','snapshot'])test('warm native health refuses changed '+field,async t=>{
 const f=await districtRuntime(t);await f.start();f.state.mutate=value=>{if(field==='pid')value.pid++;else value.districtData[field]='changed';return value;};
 await assert.rejects(f.runtime.start(f.runtime.originalConfiguration()),{code:'program'});assert.equal(f.state.spawns,1);
});
test('changed installed program is refused before warm native health',async t=>{
 const f=await districtRuntime(t);await f.start();f.state.fingerprint='e'.repeat(64);await assert.rejects(f.runtime.start(f.runtime.originalConfiguration()),{code:'program'});
});
test('a replacement child cannot inherit a previous child authority',async t=>{
 const f=await districtRuntime(t);await f.start();const original=f.runtime.child;f.runtime.child={...original};try{await assert.rejects(f.runtime.start(f.runtime.originalConfiguration()),{code:'program'});}finally{f.runtime.child=original;}
});
test('shutdown during pending warm health cannot restore a stopped instance',async t=>{
 const f=await districtRuntime(t);await f.start();f.state.hold=true;const pending=f.runtime.start(f.runtime.originalConfiguration()),rejected=assert.rejects(pending,/cancelled/);
 for(let n=0;n<20&&!f.state.requests.length;n++)await new Promise(setImmediate);assert.equal(f.state.requests.length,1);await f.runtime.stop();f.release();await rejected;assert.equal(f.runtime.configuration,null);
});
