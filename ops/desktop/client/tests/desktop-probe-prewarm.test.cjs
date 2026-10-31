'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {EventEmitter,getEventListeners}=require('node:events');
const source=fs.readFileSync(path.join(__dirname,'..','desktop-probe.cjs'),'utf8');
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const command={binary:'trusted-native-fixture',args:['trusted-bootstrap']};
function harness({imports=null}={}){
 let clock=0,id=0;const timers=new Map(),children=[],diagnostics=[];
 const timer=(fn,ms)=>{const key=++id;timers.set(key,{fn,at:clock+ms});return key;};
 const spawn=(binary,args,options)=>{
  assert.equal(binary,command.binary);assert.deepEqual([...args.slice(0,1)],command.args);assert.equal(options.windowsHide,true);assert.deepEqual({...options.env},{fixtureEnvironment:true});
  const child=new EventEmitter();child.stdout=new EventEmitter();child.stderr={resume(){}};child.stdin=new EventEmitter();
  Object.assign(child,{inputs:[],kills:0,inputDestroyed:0,closed:false,spawnedAt:clock});
  child.finish=(value={validated:true},code=0)=>{if(child.closed)return;child.closed=true;if(value!==null)child.stdout.emit('data',Buffer.from(JSON.stringify(value)));child.emit('close',code);};
  child.kill=()=>{child.kills++;return true;};child.stdin.destroy=()=>{child.inputDestroyed++;};
  child.stdin.end=raw=>{child.inputs.push(JSON.parse(raw));if(imports!==null)timer(()=>child.finish(),Math.max(0,child.spawnedAt+imports-clock)+10);};
  children.push(child);return child;
 };
 const module={exports:{}};
 vm.runInNewContext(source,{module,Buffer,setTimeout:timer,clearTimeout:key=>timers.delete(key),require:name=>{
  if(name==='node:child_process')return {spawn};if(name==='node:perf_hooks')return {performance:{now:()=>clock}};
  if(name==='./backend-command.cjs')return {backendEnvironment:()=>({fixtureEnvironment:true})};throw new Error(name);
 }});
 return {children,diagnostics,get now(){return clock;},get timers(){return [...timers.values()].map(item=>item.at);},
  prepare:options=>module.exports.prepareDesktopProbe(command,'fixture-check',{onDiagnostic:value=>diagnostics.push(value),...options}),
  advance(to){assert.ok(to>=clock);while(true){const due=[...timers].filter(([,value])=>value.at<=to).sort((a,b)=>a[1].at-b[1].at)[0];if(!due)break;clock=due[1].at;timers.delete(due[0]);due[1].fn();}clock=to;}
 };
}

test('prewarm keeps stdin unsent until verified input, is one-use, and does not cross operations',async()=>{
 const h=harness(),a=h.prepare(),b=h.prepare();assert.equal(h.children.length,2);assert.deepEqual(h.children.map(child=>child.inputs),[[],[]]);
 const first=a.run({root:'snapshot-a',manifest:'a'});assert.deepEqual(h.children[0].inputs,[{root:'snapshot-a',manifest:'a'}]);assert.deepEqual(h.children[1].inputs,[]);
 await assert.rejects(a.run({root:'snapshot-b'}),/already sent/);
 h.children[0].finish();await first;const second=b.run({root:'snapshot-b',manifest:'b'});assert.deepEqual(h.children[1].inputs,[{root:'snapshot-b',manifest:'b'}]);h.children[1].finish();await second;
 await a.cancel();await b.cancel();assert.deepEqual(h.children.map(child=>child.kills),[0,0]);
});

test('hash failure cancellation withholds input and awaits owned child close',async()=>{
 const h=harness(),p=h.prepare();let drained=false;const done=p.cancel().then(()=>{drained=true;});await tick();
 assert.equal(drained,false);assert.equal(h.children[0].kills,1);assert.deepEqual(h.children[0].inputs,[]);
 h.children[0].finish(null,1);await done;await assert.rejects(p.run({private:'not sent'}),/canceled/);assert.equal(h.children.length,1);
});

test('signal cancellation drains unsent warm process and removes its listener',async()=>{
 const h=harness(),controller=new AbortController(),p=h.prepare({signal:controller.signal});controller.abort(new Error('private cancellation detail'));
 let settled=false;const result=p.run({root:'not sent'}).then(()=>{settled=true;},error=>{settled=true;assert.equal(error.message,'Local data verification canceled.');});
 await tick();assert.equal(settled,false);assert.deepEqual(h.children[0].inputs,[]);h.children[0].finish(null,1);await result;
 assert.equal(getEventListeners(controller.signal,'abort').length,0);assert.equal(JSON.stringify(h.diagnostics).includes('private'),false);
});

test('optional expiry drains before exactly one fresh probe receives verified input',async()=>{
 let programChecks=0;const h=harness(),p=h.prepare({prewarmTimeout:30,timeout:100,beforeSpawn:()=>{programChecks++;}});h.advance(30);assert.equal(h.children[0].kills,1);
 const result=p.run({root:'verified'});await tick();assert.equal(h.children.length,1);assert.deepEqual(h.children[0].inputs,[]);
 h.children[0].finish(null,1);await tick();assert.equal(h.children.length,2);assert.deepEqual(h.children[1].inputs,[{root:'verified'}]);assert.deepEqual(h.timers,[130]);
 h.children[1].finish();await result;assert.deepEqual(h.diagnostics.map(value=>[value.phase,value.reason]),[['prewarm','expired']]);
 assert.equal(programChecks,2);
 await assert.rejects(p.run({root:'replay'}),/already sent/);assert.equal(h.children.length,2);
});

test('fallback rechecks trusted program immediately before spawning a fresh reader',async()=>{
 const h=harness();let checks=0;const p=h.prepare({prewarmTimeout:10,beforeSpawn:()=>{if(++checks===2)throw new Error('Program changed');}});
 h.advance(10);const result=p.run({root:'verified'}),rejected=assert.rejects(result,/Program changed/);h.children[0].finish(null,1);await rejected;
 assert.equal(checks,2);assert.equal(h.children.length,1);assert.deepEqual(h.children[0].inputs,[]);await p.cancel();
});

test('native timeout starts at send and a fresh fallback never loops',async()=>{
 const h=harness(),p=h.prepare({prewarmTimeout:200,timeout:100});h.advance(150);assert.equal(h.children[0].kills,0);
 const result=p.run({root:'verified'});assert.deepEqual(h.timers,[250]);const rejected=assert.rejects(result,/timed out/);h.advance(250);h.children[0].finish(null,1);await rejected;
 assert.deepEqual(h.diagnostics.map(value=>[value.phase,value.reason]),[['reader','timeout']]);
 const g=harness(),q=g.prepare({prewarmTimeout:10,timeout:20});g.advance(10);const fallback=q.run({root:'verified'}),failed=assert.rejects(fallback,/timed out/);g.children[0].finish(null,1);await tick();g.advance(30);g.children[1].finish(null,1);await failed;assert.equal(g.children.length,2);
});

for(const sent of [false,true])test(`output bounds refuse and drain ${sent?'running':'unsent'} probe without fallback`,async()=>{
 const h=harness(),p=h.prepare({limit:4});const result=sent?p.run({root:'verified'}):null;
 h.children[0].stdout.emit('data',Buffer.from('private overflowing output'));const rejected=assert.rejects(result||p.run({root:'verified'}),/Invalid local verification response/);
 assert.equal(h.children[0].kills,1);h.children[0].finish(null,1);await rejected;assert.equal(h.children.length,1);assert.equal(JSON.stringify(h.diagnostics).includes('private'),false);
});

test('early exit captures prewarm failure and never sends data to the closed child',async()=>{
 const h=harness(),p=h.prepare();h.children[0].finish(null,2);await assert.rejects(p.run({root:'verified'}),/verification failed/);
 assert.deepEqual(h.children[0].inputs,[]);assert.deepEqual(h.diagnostics.map(value=>[value.phase,value.reason]),[['prewarm','early-exit']]);
});

test('controlled synthetic schedule overlaps bootstrap only and never advances dataset reading',async()=>{
 const warm=harness({imports:40}),reader=warm.prepare();warm.advance(60);assert.deepEqual(warm.children[0].inputs,[]);
 const result=reader.run({hashesPassed:true});warm.advance(70);await result;
 const serial=harness({imports:40});serial.advance(60);const ordinary=serial.prepare().run({hashesPassed:true});serial.advance(110);await ordinary;
 assert.equal(warm.now,70);assert.equal(serial.now,110); // modelled waits, not measured native startup speed
});
