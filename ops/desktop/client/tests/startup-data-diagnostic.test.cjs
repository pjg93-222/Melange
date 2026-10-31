'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {canonical}=require('../access-client.cjs'),{StartupDataDiagnostic,observeStartupData,PREFIX}=require('../startup-data-diagnostic.cjs');
const {isDataStartupFailure}=require('../startup-failure.cjs');
function fixture({dual=true,guard=()=>{}}={}){
 const context={appId:'melange',launchNonce:'n'.repeat(43),programFingerprint:'a'.repeat(64),sourceDigests:{public:'b'.repeat(64),...(dual?{workspace:'c'.repeat(64)}:{})},guard};
 return {parser:new StartupDataDiagnostic(context),value:{schemaVersion:1,...context,guard:undefined,reason:'integrity'},context};
}
function line(value){const copy={...value};delete copy.guard;return Buffer.from(PREFIX+canonical(copy)+'\n');}
for(const dual of [false,true])test('a complete '+(dual?'dual':'public')+' intake rejection requires stdout drain and a fresh native guard',()=>{
 let guarded=0;const f=fixture({dual,guard:()=>{guarded++;}}),bytes=line(f.value);f.parser.push(bytes.subarray(0,14));f.parser.push(bytes.subarray(14));assert.equal(f.parser.blocked(),null);
 f.parser.end();assert.ok(isDataStartupFailure(f.parser.blocked()));assert.equal(guarded,1);assert.equal(f.parser.blocked().retryable,false);
});
for(const field of ['appId','launchNonce','programFingerprint','sourceDigests','reason','extra'])test('a wrong '+field+' cannot downgrade a child startup failure',()=>{
 const f=fixture(),value={...f.value,[field]:field==='sourceDigests'?{public:'b'.repeat(64)}:field==='reason'?'timeout':'wrong'};
 f.parser.push(line(value));f.parser.end();assert.equal(f.parser.blocked(),null);
});
test('duplicates, malformed/oversized markers and a late marker never grant data-blocked classification',()=>{
 for(const mode of ['duplicate','malformed','oversized','late']){
  const f=fixture();if(mode==='late')f.parser.markHealthy();
  f.parser.push(mode==='malformed'?Buffer.from(PREFIX+'{bad}\n'):mode==='oversized'?Buffer.from(PREFIX+'x'.repeat(9000)+'\n'):line(f.value));
  if(mode==='duplicate')f.parser.push(line(f.value));f.parser.end();assert.equal(f.parser.blocked(),null);
 }
});
test('program/context mutation after child output is fatal, and ordinary log text has no authority',()=>{
 const f=fixture({guard:()=>{throw new Error('Program changed');}});f.parser.push(line(f.value));f.parser.end();assert.throws(()=>f.parser.blocked(),/Program changed/);
 const logs=fixture();logs.parser.push(Buffer.from('ordinary backend data failure\n'+PREFIX+'{not valid}\n'));logs.parser.end();assert.equal(logs.parser.blocked(),null);
});
test('a terminal intake marker cannot be followed by a claimed healthy startup',()=>{
 const f=fixture();f.parser.push(line(f.value));assert.throws(()=>f.parser.markHealthy(),/Conflicting/);assert.equal(f.parser.blocked(),null);
});
test('exit before final stdout data waits for close/drain before accepting the native diagnostic',async()=>{
 const child=new(require('node:events').EventEmitter)();child.stdout=new(require('node:stream').PassThrough)();child.exitCode=1;child.signalCode=null;
 const f=fixture(),observer=observeStartupData(child,f.context);let resolved=false;const result=observer.blockedAfterExit().then(value=>{resolved=true;return value;});
 await new Promise(resolve=>setImmediate(resolve));assert.equal(resolved,false);
 child.stdout.end(line(f.value));await new Promise(resolve=>child.stdout.once('end',resolve));child.emit('close',1);assert.ok(isDataStartupFailure(await result));
});
test('a truncated/never-drained stream or still-running process cannot turn a timeout into data-blocked',async()=>{
 for(const mode of ['running','undrained']){
  const child=new(require('node:events').EventEmitter)();child.stdout=new(require('node:stream').PassThrough)();child.exitCode=mode==='running'?null:1;child.signalCode=null;
  const f=fixture(),observer=observeStartupData(child,f.context);child.stdout.write(line(f.value));assert.equal(await observer.blockedAfterExit({drainMs:5}),null);child.stdout.destroy();child.emit('close');
 }
});
