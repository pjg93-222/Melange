'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {validateState,mount}=require('../access-ui.js');
const names={melange:'Melange',mentat:'Mentat',terrier:'Terrier'},tick=()=>new Promise(resolve=>setImmediate(resolve));
const state=(appId='melange',phase='ready',extra={})=>({appId,appName:names[appId],phase,accessMode:'standalone',authentication:'windows',accountIdentity:'retained_internal_account',windowsAccountDisplayName:'WORKGROUP\\Fixture User',...extra});
function documentFixture(file='access.html'){
 const html=fs.readFileSync(path.join(__dirname,'..',file),'utf8'),nodes=Object.fromEntries([...html.matchAll(/id="([^"]+)"/g)].map(([,id])=>[id,{hidden:false,disabled:false,value:'',textContent:'',dataset:{},events:{},addEventListener(name,fn){this.events[name]=fn;},fire(name){this.events[name]?.({preventDefault(){}});}}]));
 for(const node of Object.values(nodes))Object.defineProperty(node,'innerHTML',{set(){throw new Error('Unsafe HTML insertion');}});
 const document={title:'',body:{dataset:{}},getElementById:id=>nodes[id],querySelectorAll:()=>Object.values(nodes)};
 return {nodes,document};
}
function fixture(initial=state()){
 const view=documentFixture(),calls=[];let value=initial,listener;
 const api=Object.fromEntries(['info','request','poll','activate','setPassword','unlock','open','lock'].map(method=>[method,async args=>{calls.push({method,args});return value;}]));
 api.onStatus=fn=>{listener=fn;return()=>{listener=null;};};
 const window={setTimeout,clearTimeout,addEventListener(){}};
 return {...view,api,calls,window,push:next=>listener?.(next),set:next=>{value=next;}};
}
for(const appId of Object.keys(names))test(`${appId} Windows mode displays only the verified OS name and no separate sign-in form`,async()=>{
 const f=fixture(state(appId));f.nodes['desktop-update-message'].textContent='GitHub updates: Checking for updates…';
 const ui=mount(f.document,f.api,f.window);await ui.ready;
 for(const id of ['request-form','pending-panel','activation-form','password-form','confirm-panel','lock'])assert.equal(f.nodes[id].hidden,true,id);
 assert.match(f.nodes.description.textContent,/Windows sign-in is verified/);assert.match(f.nodes.description.textContent,/opens automatically/);
 assert.doesNotMatch(f.nodes.description.textContent,/installation is approved|administrator/);
 assert.equal(f.nodes.account.textContent,'Windows account: WORKGROUP\\Fixture User');assert.doesNotMatch(f.nodes.account.textContent,/retained_internal_account/);
 assert.equal(f.nodes['desktop-update-message'].textContent,'GitHub updates: Checking for updates…');
 for(const id of ['request-form','activation-form','password-form'])f.nodes[id].fire('submit');f.nodes.lock.fire('click');await tick();
 assert.deepEqual(f.calls,[{method:'info',args:undefined}]);
 f.nodes.open.fire('click');await tick();assert.deepEqual(f.calls.at(-1),{method:'open',args:undefined});ui.dispose();
});
test('Windows lock has no password, approval, open or renderer unlock action',async()=>{
 const f=fixture(state('terrier','windows_locked')),ui=mount(f.document,f.api,f.window);await ui.ready;
 assert.match(f.nodes.description.textContent,/Unlock Windows/);assert.equal(f.nodes['ready-panel'].hidden,true);assert.equal(f.nodes.retry.hidden,true);
 for(const id of ['password-form','request-form','activation-form']){assert.equal(f.nodes[id].hidden,true);f.nodes[id].fire('submit');}
 f.nodes.open.fire('click');f.nodes.lock.fire('click');await tick();assert.deepEqual(f.calls.map(row=>row.method),['info']);ui.dispose();
});
test('Windows unavailable retries a native status read without credentials or remote approval messages',async()=>{
 const f=fixture(state('mentat','windows_unavailable')),ui=mount(f.document,f.api,f.window);await ui.ready;
 assert.equal(f.nodes.retry.hidden,false);f.api.info=async()=>{f.calls.push({method:'info'});throw new Error('access:unreachable secret-token /private/path');};
 f.nodes.retry.fire('click');await tick();assert.match(f.nodes.status.textContent,/Windows sign-in/);assert.doesNotMatch(f.nodes.status.textContent,/administrator|secret-token|private/);
 assert.deepEqual(f.calls.map(row=>row.method),['info','info']);ui.dispose();
});
test('Windows UI never guesses an account name from the retained application identity',async()=>{
 const value=state();delete value.windowsAccountDisplayName;const f=fixture(value),ui=mount(f.document,f.api,f.window);await ui.ready;
 assert.equal(f.nodes.account.hidden,true);assert.equal(f.nodes.account.textContent,'');ui.dispose();
});
test('Windows snapshots refuse password/approval phases and malformed identity display data',()=>{
 for(const phase of ['needs_request','pending','needs_password','locked','revoked','terrier_signin','error'])assert.throws(()=>validateState(state('melange',phase)));
 for(const extra of [{accessMode:'managed'},{authentication:'sso'},{canRequestAgain:false},{windowsAccountDisplayName:' bad'},{windowsAccountDisplayName:'user\nname'},{windowsAccountDisplayName:'x'.repeat(257)},{windowsAccountDisplayName:{name:'user'}}])assert.throws(()=>validateState(state('melange','ready',extra)));
 assert.throws(()=>validateState({appId:'melange',appName:'Melange',phase:'windows_locked'}));
 assert.equal(validateState(state('terrier','windows_locked')).phase,'windows_locked');
});
test('a stale initial reply cannot replace newer Windows lock status with a password prompt',async()=>{
 const f=fixture();let resolve;f.api.info=()=>new Promise(done=>{resolve=done;});
 const ui=mount(f.document,f.api,f.window);f.push(state('melange','windows_locked'));
 resolve({appId:'melange',appName:'Melange',phase:'needs_password'});await ui.ready;
 assert.match(f.nodes.description.textContent,/Unlock Windows/);assert.equal(f.nodes['password-form'].hidden,true);ui.dispose();
});
test('Windows mode cannot fall back to password UI after an invalid status or downgrade',async()=>{
 const f=fixture(),ui=mount(f.document,f.api,f.window);await ui.ready;
 f.push({...state(),windowsAccountDisplayName:'bad\nname'});
 f.push({appId:'melange',appName:'Melange',phase:'needs_password',authentication:'local-password',accessMode:'standalone'});
 assert.equal(f.nodes['password-form'].hidden,true);assert.equal(f.nodes['ready-panel'].hidden,true);assert.match(f.nodes.description.textContent,/Windows sign-in could not be verified/);ui.dispose();
});
test('a stale initial failure cannot overwrite a newer verified Windows session',async()=>{
 const f=fixture();let reject;f.api.info=()=>new Promise((_,fail)=>{reject=fail;});
 const ui=mount(f.document,f.api,f.window);f.push(state());reject(new Error('access:timeout'));await ui.ready;
 assert.match(f.nodes.description.textContent,/Windows sign-in is verified/);assert.equal(f.nodes.status.textContent,'');assert.equal(f.nodes['password-form'].hidden,true);ui.dispose();
});
test('explicit local-password mode keeps password setup and removes approval wording',async()=>{
 const f=fixture({appId:'melange',appName:'Melange',phase:'needs_password',accessMode:'standalone',authentication:'local-password'}),ui=mount(f.document,f.api,f.window);await ui.ready;
 assert.equal(f.nodes['password-form'].hidden,false);assert.match(f.nodes.description.textContent,/Choose a password for your local/);assert.doesNotMatch(f.nodes.description.textContent,/approved|administrator/);ui.dispose();
});
for(const appId of Object.keys(names))test(`${appId} settings explain Windows sign-in while preserving the independent GitHub update line`,async()=>{
 const {nodes,document}=documentFixture('setup.html');nodes['desktop-update-message'].textContent='GitHub updates: Up to date.';
 const info={appId,name:names[appId],status:'Ready',paired:true,updateProvider:'github',authentication:'windows',windowsAccountDisplayName:'ORG\\Analyst & Research'};
 const window={desktop:{info:async()=>info,onStatus(){},launch:async()=>{},pair:async()=>{}},desktopUpdateStatus:{mount:(_document,_api,{onInfo})=>{onInfo({provider:'github',accessMode:'standalone'});return()=>{};}},addEventListener(){}};
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../setup.js'),'utf8'),{window,document});await tick();
 assert.equal(nodes.authentication.hidden,false);assert.match(nodes.authentication.textContent,/current Windows sign-in/);assert.equal(nodes['windows-account'].textContent,'Windows account: ORG\\Analyst & Research');
 assert.equal(nodes['desktop-update-message'].textContent,'GitHub updates: Up to date.');assert.equal(nodes.pairing.hidden,true);assert.equal(nodes.pair.hidden,true);
});
