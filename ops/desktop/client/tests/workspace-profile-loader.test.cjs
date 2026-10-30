'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const packaging=path.resolve(__dirname,'../../packaging');
const source=fs.readFileSync(path.join(packaging,'module_workspace_render.py'),'utf8');
const loader=/PROFILE_LOADER = r"""([\s\S]*?)"""/.exec(source)[1];
const template=fs.readFileSync(path.resolve(__dirname,'../../../../fec/surfaces/templates/make_member_desk_00.tpl'),'utf8');
const start=template.indexOf('window.__melangeProfileMerge=function(D2){'),end=template.indexOf('\n};',start)+3,stockMerge=template.slice(start,end);
const fields=['articles','bills','bio','community','cook_pvi','district_brief','electoral','employers','financial','industry','partners','personal','psy','refs','staffdir'];
const settle=async()=>{for(let i=0;i<8;i++)await new Promise(resolve=>setImmediate(resolve));};
function fixture(fetch){
 const payload={bill_lobbying:{bill:'fixture'},members_heavy:[{bio:{text:'<img src=x onerror=UNTRUSTED>'}},{staffdir:[{name:'fixture'}]}]},bytes=Buffer.byteLength(JSON.stringify(payload)),nodes=new Map();
 class Element{constructor(){this.children=[];this.listeners={};this.style={};}set id(value){this._id=value;nodes.set(value,this);}get id(){return this._id;}replaceChildren(...children){this.children=children;}append(...children){this.children.push(...children);}after(node){nodes.set(node.id,node);}addEventListener(name,callback){this.listeners[name]=callback;}remove(){nodes.delete(this.id);}}
 const bar=new Element();bar.id='desktop-workspace-provenance';const note=new Element();note.id='mel-profiles-note';
 const document={getElementById:id=>nodes.get(id)||null,createElement:()=>new Element(),createTextNode:text=>({text}),body:{prepend:node=>nodes.set(node.id,node)}};
 const base={members:[{name:'Alpha',state:'AA',district:'1'},{name:'Beta',state:'BB',district:'2'}]},window={__profilesReady:false,__pendingOpen:1,dispatchEvent:event=>events.push(event.type)},events=[],opened=[],rebuild=[];
 const expected={sha256:'a'.repeat(64),bytes,members:2,sourceDigest:'b'.repeat(64)},calls=[];
 const response={ok:true,headers:{get:name=>({'content-type':'application/json','content-length':String(bytes),'x-melange-role-sha256':expected.sha256}[name.toLowerCase()]??null)},json:async()=>structuredClone(payload)};
 const context=vm.createContext({window,document,Event:class{constructor(type){this.type=type;}},D:base,rebuildBillRepository:()=>rebuild.push('bills'),rebuildStaffIndex:()=>rebuild.push('staff'),openMember:index=>opened.push(index),fetch:async(url,options)=>{calls.push({url,options});return fetch?fetch({response,payload,calls}):response;}});
 vm.runInContext(stockMerge,context);
 const code=loader.replace('__PROFILE_CONTEXT__',JSON.stringify(expected)).replace('__PROFILE_FIELDS__',JSON.stringify(fields)).replace(/^<script>\s*/,'').replace(/\s*<\/script>$/,'');
 vm.runInContext(code,context);return {base,payload,window,nodes,calls,events,opened,rebuild,response};
}

test('lazy profile loader uses fixed authenticated same-origin JSON and exact stock positional merge',async()=>{
 const f=fixture();await settle();assert.equal(f.window.__profilesReady,true);assert.equal(f.calls.length,1);assert.equal(f.calls[0].url,'/__desktop/workspace/member-profiles.json');assert.equal(f.calls[0].options.credentials,'same-origin');assert.equal(f.calls[0].options.cache,'no-store');assert.equal(f.calls[0].options.redirect,'error');assert.equal(f.calls[0].options.headers['X-Melange-Workspace'],'b'.repeat(64));
 assert.deepEqual(f.base.members,[{name:'Alpha',state:'AA',district:'1',...f.payload.members_heavy[0]},{name:'Beta',state:'BB',district:'2',...f.payload.members_heavy[1]}]);assert.deepEqual(f.base.bill_lobbying,f.payload.bill_lobbying);assert.deepEqual(f.rebuild,['bills','staff']);assert.deepEqual(f.opened,[1]);assert.equal(f.nodes.has('mel-profiles-note'),false);assert.equal(f.events[0],'melange-workspace-profiles-ready');
});

test('failed profile fetch remains visibly unready and explicit retry completes without losing queued member action',async()=>{
 let fail=true;const f=fixture(({response})=>{if(fail)throw new Error('private failure details must stay private');return response;});await settle();assert.equal(f.window.__profilesReady,false);const status=f.nodes.get('desktop-workspace-profile-status');assert.match(status.children[0].text,/not ready/);assert.doesNotMatch(status.children[0].text,/private failure/);const button=f.nodes.get('desktop-workspace-profile-retry');assert(button);fail=false;await button.listeners.click();await settle();assert.equal(f.window.__profilesReady,true);assert.deepEqual(f.opened,[1]);assert.equal(f.calls.length,2);
});

test('in-flight loads coalesce and wrong workspace/roster/prototype fields never signal full readiness',async()=>{
 let release;const f=fixture(({response})=>new Promise(resolve=>{release=()=>resolve(response);}));f.window.__melangeLoadWorkspaceProfiles();f.window.__melangeLoadWorkspaceProfiles();assert.equal(f.calls.length,1);assert.equal(f.window.__profilesReady,false);release();await settle();assert.equal(f.window.__profilesReady,true);
 for(const kind of ['workspace','roster','field']){const g=fixture(({response,payload})=>{if(kind==='workspace')response.headers.get=name=>name.toLowerCase()==='x-melange-role-sha256'?'c'.repeat(64):name==='content-type'?'application/json':null;else response.json=async()=>kind==='roster'?{...payload,members_heavy:[]}:{...payload,members_heavy:[JSON.parse('{"__proto__":{"polluted":true}}'),{}]};return response;});await settle();assert.equal(g.window.__profilesReady,false);assert.deepEqual(g.events,[]);assert(g.nodes.has('desktop-workspace-profile-retry'));assert.equal({}.polluted,undefined);}
});
