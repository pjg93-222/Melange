'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os'),crypto=require('node:crypto'),vm=require('node:vm');
const {createRequire}=require('node:module');
const native=require('../module-data-runtime-boundary.cjs'),{PUBLIC_KINDS,PUBLIC_ROLES}=require('../module-data-adapters.cjs');
const startupFile=path.join(__dirname,'..','module-data-startup.cjs'),startupRequire=createRequire(startupFile);
const {APPLICATION_SPECS}=require('../module-application-inventory.cjs');
function fixture(t,appId='melange',changeSpec=()=>{}){
 const base=fs.mkdtempSync(path.join(os.tmpdir(),'module-program-')),resources=path.join(base,'resources'),runtimeRoot=path.join(resources,'runtime',appId);
 const roots={source:path.join(runtimeRoot,'sources'),bootstrap:path.join(runtimeRoot,'bootstrap')};
 for(const root of Object.values(roots))fs.mkdirSync(root,{recursive:true});
 const files=[['source','reader.py','compiled reader'],['bootstrap','desktop_backend.py','compiled backend']].map(([root,file,value])=>{fs.writeFileSync(path.join(roots[root],file),value);return {root,path:file,bytes:Buffer.byteLength(value),sha256:crypto.createHash('sha256').update(value).digest('hex')};});
 const spec={...APPLICATION_SPECS[appId],programFiles:files,programFingerprint:native.programFingerprint(files)};changeSpec(spec);
 const runtime={};native.initializeModuleRuntime(runtime,()=>roots);
 const calls=[];let behavior=async()=>({schemaVersion:1,validated:true,appId,kind:PUBLIC_KINDS[appId][0],coverage:{completeKind:true,fullApplication:false}});
 const command={binary:path.join(runtimeRoot,'python','python.exe'),args:['-E','-s','-u',path.join(roots.bootstrap,'desktop_backend.py')],runtime:runtimeRoot};
 const module={exports:{}};
 vm.runInNewContext(fs.readFileSync(startupFile,'utf8'),{module,require:name=>{
  if(name==='./module-application-inventory.cjs')return {APPLICATION_SPECS:{[appId]:spec}};
  if(name==='./backend-command.cjs')return {backendCommand:(selected,id)=>{assert.equal(selected,resources);assert.equal(id,appId);return command;}};
  if(name==='./desktop-probe.cjs')return {desktopProbe:async(...args)=>{calls.push(args);return behavior(...args);}};
  return startupRequire(name);
 }},{filename:startupFile});
 t.after(()=>fs.rmSync(base,{recursive:true,force:true}));
 const lookup=module.exports.compiledApplicationContract;
 return {appId,base,resources,roots,runtime,spec,calls,command,lookup,set behavior(value){behavior=value;},get contract(){return lookup(appId,{runtime,resources});}};
}
function snapshot(f){const kind=PUBLIC_KINDS[f.appId][0],root=path.join(f.base,'snapshot'),roles=PUBLIC_ROLES[kind];
 return {dataset:{kind,adapterVersion:1,objects:Object.keys(roles).map(role=>({role,bytes:1,sha256:'a'.repeat(64)})),counts:{files:Object.keys(roles).length}},root,files:Object.fromEntries(Object.entries(roles).map(([role,spec])=>[role,path.join(root,...spec.path.split('/'))]))};}
test('paged Melange selection is explicit and legacy default remains compatible',t=>{
 const f=fixture(t),paged=f.lookup('melange',{runtime:f.runtime,resources:f.resources,publicDataMode:'paged-v1'});
 assert.equal(f.contract.contractId,'melange.public-data.v1');assert.equal(paged.contractId,'melange.public-data.pages.v1');
 assert.equal(paged.requiredKinds.join('|'),'melange.official-payroll-pages.v1');
 assert.deepEqual(Object.keys(paged.registry[paged.requiredKinds[0]].roles),['index','receipt']);
 assert.equal(paged.programFingerprint,f.contract.programFingerprint);
});
test('paged mode is ignored for other apps and unknown modes keep the legacy contract',t=>{
 const f=fixture(t),odd=f.lookup('melange',{runtime:f.runtime,resources:f.resources,publicDataMode:'paged-v2'}),none=f.lookup('melange',{runtime:f.runtime,resources:f.resources});
 assert.equal(odd.contractId,'melange.public-data.v1');assert.equal(none.contractId,'melange.public-data.v1');
 assert.equal(odd.requiredKinds.join('|'),'melange.official-payroll-observations.v1');
});
for(const appId of ['melange','mentat']){
 test(`${appId} compiled inventory has fixed public coverage, budget and closed source table`,()=>{
  const spec=APPLICATION_SPECS[appId];assert.equal(spec.contractId,appId+'.public-data.v1');assert.equal(spec.appId,appId);
  assert.deepEqual(spec.requiredKinds,PUBLIC_KINDS[appId]);assert.equal(spec.startupTimeoutMs,appId==='melange'?600000:300000);
  assert.equal(native.programFingerprint(spec.programFiles),spec.programFingerprint);assert.ok(Object.isFrozen(spec)&&Object.isFrozen(spec.programFiles));
  assert.ok(spec.programFiles.some(item=>item.root==='bootstrap'&&item.path==='module_application_contracts.py'));
  assert.ok(spec.programFiles.some(item=>item.root==='bootstrap'&&item.path==='module_public_input_installers.py'));
  assert.ok(spec.programFiles.some(item=>item.root==='source'&&item.path===(appId==='melange'?'fec/surfaces/public_data/public-data.js':'mentat/app/public_data.js')));
  assert.equal(spec.programFiles.some(item=>/fixture_|module_application_inventory\.py$/.test(item.path)),false);
  assert.equal(require('../module-data-startup.cjs').compiledApplicationContract(appId),null);
 });
 test(`${appId} production lookup needs the actual registered matching program and supplies the compiled probe deadline`,async t=>{
  const f=fixture(t,appId),contract=f.contract;assert.ok(contract);assert.equal(contract.appId,appId);assert.ok(Object.isFrozen(contract));
  assert.equal(f.lookup(appId,{runtime:{},resources:f.resources}),null);assert.equal(f.lookup(appId,{runtime:f.runtime,resources:'relative'}),null);assert.equal(f.lookup('terrier',{runtime:f.runtime,resources:f.resources}),null);
  const controller=new AbortController();assert.equal(await contract.registry[PUBLIC_KINDS[appId][0]].validateSnapshot({...snapshot(f),signal:controller.signal}),true);
  assert.equal(f.calls.length,1);const [command,mode,payload,options]=f.calls[0];assert.equal(command,f.command);assert.equal(mode,'--desktop-github-module-check');
  assert.equal(payload.sourceRoot,f.roots.source);assert.equal(payload.appId,appId);assert.equal(options.timeout,appId==='melange'?600000:300000);assert.equal(options.signal,controller.signal);
 });
}
for(const field of ['programFingerprint','contractId','startupTimeoutMs','requiredKinds']){
 test(`compiled lookup refuses a changed ${field} rather than creating a provider`,t=>{
  const f=fixture(t,'melange',spec=>{spec[field]=field==='startupTimeoutMs'?30000:field==='requiredKinds'?['melange.staffer-graph-core.v1']:'changed';});
  assert.equal(f.contract,null);assert.equal(f.calls.length,0);
 });
}
test('changed installed bytes fail closed initially and after a successful component response',async t=>{
 const f=fixture(t),contract=f.contract;assert.ok(contract);const reader=path.join(f.roots.source,'reader.py');
 f.behavior=async()=>{fs.writeFileSync(reader,'foreign mutation');return {schemaVersion:1,validated:true,appId:f.appId,kind:PUBLIC_KINDS[f.appId][0],coverage:{completeKind:true,fullApplication:false}};};
 await assert.rejects(contract.registry[PUBLIC_KINDS[f.appId][0]].validateSnapshot(snapshot(f)));assert.equal(f.calls.length,1);assert.equal(f.contract,null);
});
for(const appId of ['melange','mentat'])for(const root of ['source','bootstrap']){
 test(`${appId} replaced registered ${root} root cannot borrow another installed selection`,t=>{
  const f=fixture(t,appId);f.roots[root]=path.join(f.base,'other');fs.mkdirSync(f.roots[root]);
  const [file,value]=root==='source'?['reader.py','compiled reader']:['desktop_backend.py','compiled backend'];
  fs.writeFileSync(path.join(f.roots[root],file),value);
  assert.equal(f.contract,null);assert.equal(f.calls.length,0);
 });
}
test('component cancellation refuses before probe and after response while ordinary metadata cannot grant health',async t=>{
 const f=fixture(t),contract=f.contract,controller=new AbortController();controller.abort();
 await assert.rejects(contract.registry[PUBLIC_KINDS[f.appId][0]].validateSnapshot({...snapshot(f),signal:controller.signal}));assert.equal(f.calls.length,0);
 const during=new AbortController();f.behavior=async()=>{during.abort();return {schemaVersion:1,validated:true,appId:f.appId,kind:PUBLIC_KINDS[f.appId][0],coverage:{completeKind:true,fullApplication:false}};};
 await assert.rejects(contract.registry[PUBLIC_KINDS[f.appId][0]].validateSnapshot({...snapshot(f),signal:during.signal}));assert.equal(f.calls.length,1);
});
