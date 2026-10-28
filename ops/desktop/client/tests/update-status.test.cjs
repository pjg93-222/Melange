'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {createUpdateStatus}=require('../update-status.cjs');
const {mount}=require('../update-status-ui.js');
const names={melange:'Melange',mentat:'Mentat',terrier:'Terrier'};
const clock='2026-10-28T20:00:00.000Z';
const make=(appId='melange')=>createUpdateStatus({appId,appName:names[appId],installedVersion:'1.0.24',provider:'github',accessMode:'standalone',now:()=>new Date(clock)});
for(const appId of Object.keys(names))test(appId+' status identifies the installed app and starts without claiming a check',()=>{
  const state=make(appId).current();assert.equal(state.appName,names[appId]);assert.equal(state.installedVersion,'1.0.24');
  assert.equal(state.accessMode,'standalone');assert.equal(state.state,'waiting');assert.equal(state.checkedAt,null);assert.ok(Object.isFrozen(state));
});
test('real updater events distinguish check, current, download, prepared and network failure',()=>{
  const status=make();assert.equal(status.record('Checking for updates…').state,'checking');
  assert.equal(status.record('No newer signed update.').state,'current');assert.equal(status.current().checkedAt,clock);
  assert.equal(status.record('Downloading verified update 1.0.25…').state,'downloading');
  assert.equal(status.record('Update 1.0.25 verified. Installs after you close this app.').state,'ready');
  assert.match(status.current().message,/1\.0\.25/);
  assert.equal(status.record('Update check deferred. Verified update remains staged; local app remains available.').state,'unavailable');
  assert.match(status.current().message,/still staged/);
});
test('pending startup or failed preparation never becomes a healthy up-to-date claim',()=>{
  const status=make();assert.equal(status.record('No newer signed update. Updated app awaits a successful local startup.').state,'waiting');
  assert.match(status.current().message,/not yet confirmed/);
  assert.equal(status.record('No newer signed update. Staged update 1.0.25 was not prepared: Native signature refused').state,'unavailable');
  assert.equal(status.record('Update deferred: request failed').state,'unavailable');
});
test('cached discovery uses its real timestamp and a deferred refresh cannot claim current',()=>{
  const status=make(),older='2026-10-28T18:00:00.000Z';
  status.record('Already current. Using cached release list checked '+older+'. Next discovery after '+clock+'.');
  assert.equal(status.current().checkedAt,older);assert.match(status.current().message,/last checked release list/);
  assert.equal(status.record('Already current. GitHub API retry after '+clock+'.').state,'unavailable');
  assert.equal(status.current().checkedAt,older);
  assert.equal(status.record('Already current. Using cached release list checked '+older+'. Refresh deferred.').state,'unavailable');
});
test('invalid metadata and unknown events cannot claim update success',()=>{
  assert.throws(()=>createUpdateStatus({appId:'melange',appName:'Terrier',installedVersion:'1.0.24'}));
  assert.throws(()=>createUpdateStatus({appId:'melange',appName:'Melange',installedVersion:'latest'}));
  for(const message of ['',null,'some new message','Downloading verified update unknown'])assert.equal(make().record(message).state,'unavailable');
});
function documentFixture(){
  const nodes=Object.fromEntries(['desktop-update-status','desktop-installed-version','desktop-update-message'].map(id=>[id,{dataset:{},textContent:''}]));
  return {nodes,document:{getElementById:id=>nodes[id]}};
}
test('renderer ignores a stale initial reply after a newer status event and unsubscribes',async()=>{
  const {nodes,document}=documentFixture();let listener,resolve,removed=false;
  const status=make(),initial=status.current();const dispose=mount(document,{getUpdateInfo:()=>new Promise(done=>{resolve=done;}),onUpdateStatus:fn=>{listener=fn;return()=>{removed=true;};}});
  listener(status.record('Update deferred: network unavailable'));resolve(initial);await Promise.resolve();
  assert.equal(nodes['desktop-update-status'].dataset.state,'unavailable');assert.match(nodes['desktop-installed-version'].textContent,/1\.0\.24/);
  assert.match(nodes['desktop-update-message'].textContent,/GitHub updates:/);dispose();assert.equal(removed,true);
});
test('renderer rejects cross-app events and IPC failures rather than leaving stale current text',async()=>{
  const {nodes,document}=documentFixture();let listener;
  mount(document,{getUpdateInfo:async()=>make().record('Already current.'),onUpdateStatus:fn=>{listener=fn;}});await Promise.resolve();
  assert.equal(nodes['desktop-update-status'].dataset.state,'current');listener(make('terrier').current());
  assert.equal(nodes['desktop-update-status'].dataset.state,'unavailable');assert.doesNotMatch(nodes['desktop-update-message'].textContent,/Up to date/);
  const failed=documentFixture();mount(failed.document,{getUpdateInfo:async()=>{throw new Error('unavailable');},onUpdateStatus:()=>{}});await Promise.resolve();
  assert.equal(failed.nodes['desktop-update-status'].dataset.state,'unavailable');
});
for(const filename of ['preload.cjs','access-preload.cjs'])test(filename+' exposes isolated update IPC without leaking Electron events',async()=>{
  let api,channel,listener,removed=false;
  const ipcRenderer={sendSync:()=>null,invoke:async name=>{channel=name;return make().current();},on:(name,fn)=>{channel=name;listener=fn;},removeListener:(name,fn)=>{assert.equal(name,'desktop:update-status');assert.equal(fn,listener);removed=true;}};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'..',filename),'utf8'),{require:name=>{assert.equal(name,'electron');return {contextBridge:{exposeInMainWorld:(_name,value)=>{api=value;}},ipcRenderer};}});
  await api.getUpdateInfo();assert.equal(channel,'desktop:update-info');assert.throws(()=>api.onUpdateStatus(null));
  let received;const unsubscribe=api.onUpdateStatus(value=>{received=value;});const snapshot=make().current();listener({secret:'event'},snapshot);
  assert.equal(received,snapshot);unsubscribe();assert.equal(removed,true);
});
for(const appId of Object.keys(names))test('loading branding uses '+appId+' and keeps its update line separate',()=>{
  const status=make(appId).current(),nodes={detail:{},'loading-name':{},'loading-icon':{},'loading-video':{dataset:{},play:()=>Promise.resolve()}};
  const document={title:'',body:{dataset:{},classList:{toggle(){}}},getElementById:id=>nodes[id]};
  const window={desktop:{onStatus:fn=>fn('Local startup progress')},desktopUpdateStatus:{mount:(_document,_api,{onInfo})=>{onInfo(status);return()=>{};}},addEventListener(){},matchMedia:()=>({matches:false})};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'..','loading.js'),'utf8'),{document,window});
  assert.equal(document.title,names[appId]);assert.equal(nodes['loading-name'].textContent,names[appId]);
  assert.equal(document.body.dataset.app,appId);assert.equal(nodes.detail.textContent,'Local startup progress');
  assert.equal(nodes['loading-video'].hidden,appId!=='terrier');assert.equal(nodes['loading-icon'].hidden,false);
});
