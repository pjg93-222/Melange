'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {fullMain}=require('./fixtures/full-main-fixture.cjs');
const {dataStartupFailure}=require('../startup-failure.cjs');
const {networkFailure}=require('../network-transport.cjs');

test('whole main owns its real retry coordinator across deferred startup and retry',async t=>{
 const main=fullMain({appId:'mentat',imports:{'./access-gate.cjs':{authorizeAvailable:gate=>gate.authorize()}}});t.after(()=>main.dispose());
 const counts={attempts:0,deferred:0,ready:0,failed:0,shown:0},approved={};let url='file:///loading.html';
 const runtime={child:null,configuration:{},origin:'http://127.0.0.1:43210',launchPath:'/'};
 const lifecycle={generation:0,suspended:false,resume:async()=>{},canReveal:async()=>true,heartbeat:async()=>{}};
 main.install({runtime,lifecycle,gate:{authorize:async()=>approved},
  moduleDataStartup:{supported:true,start:async()=>{counts.attempts++;if(counts.attempts===1)throw dataStartupFailure(networkFailure('unreachable','Fixture network outage'));runtime.child={};return runtime.origin;}},
  updater:{markApplicationDeferred(){counts.deferred++;},markApplicationReady(){counts.ready++;},markApplicationFailed(){counts.failed++;}},
  window:{isDestroyed:()=>false,isVisible:()=>true,hide(){},show(){counts.shown++;},loadURL:async value=>{url=value;},webContents:{getURL:()=>url,send(){}}}});
 assert.equal(main.startupRetry.constructor.name,'StartupRetry');await main.launch();
 assert.equal(counts.deferred,1);assert.equal(counts.failed,0);assert.ok(main.startupRetry.waiting);
 assert.equal(await main.startupRetry.retryNow(),false,'The real coordinator preserves the minimum network retry delay');
 await new Promise(resolve=>setTimeout(resolve,1050));
 assert.equal(await main.startupRetry.retryNow(),true);assert.equal(counts.attempts,2);assert.equal(counts.ready,1);assert.equal(counts.failed,0);assert.equal(main.startupRetry.waiting,null);
});

test('whole main configures Electron net only from the ready callback before startup',async t=>{
 const calls=[],stop=new Error('Stop after actual transport wiring');
 const main=fullMain({appId:'mentat',imports:{'./network-transport.cjs':{
  configureElectronTransport(net){calls.push(net);throw stop;},configureNodeTransport(){assert.fail('Desktop must use native proxy transport');}}}});t.after(()=>main.dispose());
 assert.equal(calls.length,0);await assert.rejects(main.ready(),error=>error===stop);assert.deepEqual(calls,[main.electron.net]);
});

for(const appId of ['melange','mentat'])test('whole main honors '+appId+' workspace feed before a used local directory',t=>{
 const main=fullMain({appId});t.after(()=>main.dispose());const selected=path.join(main.root,'selected-original');fs.mkdirSync(selected);
 if(appId==='melange'){fs.writeFileSync(path.join(selected,'Moneyball.html'),'x'.repeat(5000));fs.writeFileSync(path.join(selected,'ranks_python.json'),'{}');}
 else fs.mkdirSync(path.join(selected,'.cache','industry-report','existing'),{recursive:true});
 const marker=path.join(selected,'original-user-record.json');fs.writeFileSync(marker,'{"preserved":true}');
 fs.writeFileSync(path.join(main.profile,'settings.json'),JSON.stringify({dataDirectory:selected}));
 const started={channel:'workspace-v1'};let calls=0;main.install({workspaceFactory:()=>{calls++;return started;}});
 main.configure({desktopWorkspaceData:{[appId]:'workspace-v1'}});assert.equal(main.createModuleDataStartup(),started);assert.equal(calls,1);
 assert.equal(JSON.parse(fs.readFileSync(path.join(main.profile,'settings.json'))).dataDirectory,selected);assert.equal(fs.readFileSync(marker,'utf8'),'{"preserved":true}');
 main.configure({desktopWorkspaceData:{}});assert.equal(main.createModuleDataStartup(),null);assert.equal(calls,1);
});
