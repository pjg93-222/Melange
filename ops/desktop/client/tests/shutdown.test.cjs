'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const mainFile=path.join(__dirname,'..','main.cjs'),source=fs.readFileSync(mainFile,'utf8');
const turn=()=>new Promise(resolve=>setImmediate(resolve));
function fixture({stop=async()=>{},districtStop=null,activate=false,noticeThrows=false}={}){
 const calls=[],handlers=new Map(),child={fixture:true};
 const context={closing:false,closeApproved:true,background:true,portable:false,interval:1,presenceInterval:2,districtDataInterval:3,
  startupRetry:{cancel(){calls.push('startup-cancel');}},downloads:{abort(){calls.push('abort');}},clearInterval(){},networkWatcher:{close(){calls.push('network-close');}},moduleDataStartup:{async shutdown(){calls.push('drain');}},
  runtime:{child,async stop(){calls.push('stop');await stop();this.child=null;}},districtSwitch:districtStop?{async stopAll(){calls.push('stop-all');await districtStop();}}:null,
  updater:{async activateAfterClose(){calls.push('activate');return activate;},close(){calls.push('updater-close');}},
  updateStatus(){calls.push('notice');if(noticeThrows)throw new Error('notification unavailable');},updateGitHubStatus(){calls.push('update-notice');},
  dialog:{showErrorBox(){calls.push('dialog');}},definition:{name:'Terrier'},
  app:{on(name,handler){handlers.set(name,handler);},quit(){calls.push('quit');}},
  window:{isDestroyed:()=>true,close(){calls.push('window-close');}},accessLifecycle:{suspended:false},
  launchInstall:{installing:false,closeWindow(){calls.push('install-window-close');},defer:()=>false,showWindow(){calls.push('install-window-show');}},
  async showAccess(){calls.push('access');},async launch(){calls.push('launch');}};
 vm.createContext(context);
 const start=source.indexOf('async function finishClose(){'),end=source.indexOf('\nfunction createModuleDataStartup()',start);
 assert.ok(start>0&&end>start);vm.runInContext(source.slice(start,end),context,{filename:mainFile});
 for(const event of ['second-instance','before-quit']){
  const line=source.split('\n').find(value=>value.startsWith("app.on('"+event+"'"));assert.ok(line);vm.runInContext(line,context,{filename:mainFile});
 }
 return {context,calls,handlers,child,close:()=>context.finishClose()};
}

test('failed backend shutdown defers activation and quit, reports failure and preserves retryability',async()=>{
 let attempts=0;const f=fixture({stop:async()=>{if(++attempts===1)throw new Error('still alive');},noticeThrows:true});
 assert.equal(await f.close(),false);assert.equal(f.calls[0],'startup-cancel');assert.ok(f.calls.indexOf('startup-cancel')<f.calls.indexOf('drain'));assert.equal(f.context.closing,false);assert.equal(f.context.closeApproved,false);
 assert.equal(f.context.finishClose.deferred,true);assert.equal(f.context.finishClose.inProgress,false);assert.equal(f.context.runtime.child,f.child);
 assert.equal(f.calls.includes('activate'),false);assert.equal(f.calls.includes('quit'),false);assert.ok(f.calls.includes('dialog'));
 assert.equal(await f.close(),true);assert.equal(attempts,2);assert.equal(f.context.runtime.child,null);
 assert.equal(f.context.finishClose.deferred,false);assert.equal(f.context.finishClose.stopped,true);assert.equal(f.calls.filter(value=>value==='activate').length,1);assert.equal(f.calls.filter(value=>value==='quit').length,1);
});

test('failure to stop any retained district prevents an installer or quit',async()=>{
 const f=fixture({districtStop:async()=>{throw new Error('retained backend still alive');}});
 assert.equal(await f.close(),false);assert.ok(f.calls.includes('stop-all'));assert.equal(f.calls.includes('stop'),false);
 assert.equal(f.calls.includes('activate'),false);assert.equal(f.calls.includes('quit'),false);assert.equal(f.context.finishClose.deferred,true);
});

test('Quit cannot bypass an in-progress shutdown before real backend termination',async()=>{
 let release;const f=fixture({stop:()=>new Promise(resolve=>{release=resolve;}),activate:true});
 const closing=f.close();await turn();let prevented=false;
 f.handlers.get('before-quit')({preventDefault(){prevented=true;}});
 assert.equal(prevented,true);assert.equal(f.calls.includes('activate'),false);assert.equal(await f.close(),false);
 f.handlers.get('second-instance')();assert.equal(f.calls.includes('launch'),false);
 release();assert.equal(await closing,true);assert.equal(f.context.finishClose.stopped,true);assert.equal(f.calls.filter(value=>value==='activate').length,1);
 let preventedAfter=false;f.handlers.get('before-quit')({preventDefault(){preventedAfter=true;}});assert.equal(preventedAfter,false);
});

for(const event of ['second-instance','before-quit'])test(event+' retries deferred shutdown after the original window is destroyed',async()=>{
 let attempts=0;const f=fixture({stop:async()=>{if(++attempts===1)throw new Error('try again');},activate:true});
 await f.close();let prevented=false;f.handlers.get(event)({preventDefault(){prevented=true;}});await turn();
 assert.equal(attempts,2);assert.equal(f.context.finishClose.deferred,false);assert.equal(f.context.runtime.child,null);
 assert.equal(f.calls.includes('launch'),false);assert.equal(f.calls.includes('access'),false);assert.equal(f.calls.filter(value=>value==='activate').length,1);
 if(event==='before-quit')assert.equal(prevented,true);
});

test('ordinary second-instance routing remains unchanged outside shutdown',async()=>{
 const f=fixture();f.handlers.get('second-instance')();await turn();assert.ok(f.calls.includes('launch'));assert.equal(f.calls.includes('stop'),false);
});
