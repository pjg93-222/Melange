'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path'),crypto=require('node:crypto');
const producer=require('../build-plugin-free.cjs');
const hash=raw=>crypto.createHash('sha256').update(raw).digest('hex');
function fixture(t,app='terrier',version='1.0.31'){
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'desktop-source-overlay-'));
  t.after(()=>{assert.equal(fs.realpathSync.native(root),root);fs.rmSync(root,{recursive:true,force:true});});
  const program=path.join(root,'base'),overlay=path.join(root,'overlay'),manifest=path.join(overlay,'manifest.json');
  const prefix='resources/runtime/'+app+'/',name=prefix+'bootstrap/terrier_standalone.py';
  const write=(folder,relative,raw)=>{const file=path.join(folder,relative);fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,raw);return file;};
  const base=write(program,name,'old reviewed bootstrap\n');
  write(program,'vendor.dll','retained vendor fixture');
  const value={schemaVersion:1,appId:app,version,clientCommit:'a'.repeat(40),sourceCommit:'b'.repeat(40),files:[]};
  function replace(relative,raw){write(path.join(overlay,'files'),relative,raw);value.files.push({path:relative,bytes:Buffer.byteLength(raw),sha256:hash(raw)});}
  replace(name,'new reviewed bootstrap\n');
  const save=()=>fs.writeFileSync(manifest,JSON.stringify(value));save();
  return {root,program,overlay,manifest,prefix,name,base,value,write,replace,save,
    run:()=>producer.sourceOverlay(producer.payloadFiles(program,'Terrier.exe'),app,version,manifest)};
}

test('release33 adds only its explicitly reviewed workspace helpers and preserves every vendor/base byte',t=>{
  for(const app of ['melange','mentat','terrier']){
    const f=fixture(t,app,'1.0.33'),added=['desktop_workspace.py','terrier_runtime_handoff.py','module_workspace_handoff.py',
      'workspace_data_contract.py','module_workspace_installers.py','module_workspace_inputs.py','workspace_melange.py',
      'workspace_mentat.py','workspace_archive.py','workspace_sqlite.py','workspace_cache.py','workspace_graph.py',
      'module_workspace_render.py','module_workspace_combined_ui.py','module_workspace_industry_ui.py','module_workspace_ui_templates.py'];
    for(const name of added)f.replace(f.prefix+'bootstrap/'+name,'reviewed new helper '+name);
    f.write(f.program,f.prefix+'bootstrap/desktop_backend.py','retained native boundary');
    f.replace(f.prefix+'bootstrap/desktop_backend.py','reviewed paired native boundary');f.save();
    const before=producer.payloadFiles(f.program,'unused.exe'),out=f.run();assert.equal(out.files.size,before.size+added.length);
    assert.equal(out.files.get('vendor.dll'),before.get('vendor.dll'));assert.equal(fs.readFileSync(f.base,'utf8'),'old reviewed bootstrap\n');
    const row=f.value.files[1],name=row.path;row.path=f.prefix+'bootstrap/native_credentials.py';f.save();assert.throws(f.run,/Invalid source overlay member/);
    row.path=f.prefix+'bootstrap/unreviewed.py';f.save();assert.throws(f.run,/Invalid source overlay member/);row.path=name;f.save();
  }
});

test('release33 permits only the two Melange sources; old reader and Terrier route are strictly inherited',t=>{
  for(const app of ['melange','mentat','terrier']){
    const f=fixture(t,app,'1.0.33');
    const graph=f.prefix+'sources/fec/surfaces/staffer_graph_snapshot.py';f.write(f.program,graph,'old graph');f.replace(graph,'exact Git graph');f.save();
    if(app==='melange')assert.ok(f.run().files.has(graph));else assert.throws(f.run,/Invalid source overlay member/);
    for(const source of ['fec/surfaces/melange_public_data.py','server/research/street_views.py']){
      f.value.files[1].path=f.prefix+'sources/'+source;f.write(f.program,f.value.files[1].path,'retained source');f.save();assert.throws(f.run,/Invalid source overlay member/);
    }
  }
});

test('release33 exact native activity service is permitted only under Melange source closure',t=>{
  for(const app of ['melange','mentat','terrier']){
    const f=fixture(t,app,'1.0.33'),name=f.prefix+'sources/fec/surfaces/staffer_live_service.py';
    f.write(f.program,name,'retained activity service');f.replace(name,'exact reviewed native activity slot');f.save();
    if(app==='melange')assert.ok(f.run().files.has(name));else assert.throws(f.run,/Invalid source overlay member/);
  }
});
test('source overlay replaces only exact approved bytes and leaves immutable base unchanged',t=>{
  const f=fixture(t),before=fs.readFileSync(f.base),out=f.run();
  assert.equal(out.files.size,2);assert.equal(out.files.get('vendor.dll'),path.join(f.program,'vendor.dll'));
  assert.equal(out.files.get(f.name),path.join(f.overlay,'files',f.name));assert.deepEqual(fs.readFileSync(f.base),before);
  assert.equal(out.inputs.length,2);assert.equal(out.sha256,hash(fs.readFileSync(f.manifest)));
});
test('all three apps accept their own bootstrap and metadata replacements',t=>{
  for(const app of ['melange','mentat','terrier']){
    const f=fixture(t,app);
    for(const name of ['bootstrap/module_application_inventory.py','source-inventory.json','source-provenance.json']){
      f.write(f.program,f.prefix+name,'old');f.replace(f.prefix+name,'new');
    }
    f.save();assert.equal(f.run().replacements.length,4);
  }
});
test('reviewed eight and nine member overlays add only the fixed helper and emit a closed payload',t=>{
  for(const app of ['melange','mentat','terrier']){
    const f=fixture(t,app),helper=f.prefix+'bootstrap/module_catalogue_cache.py';
    const changes=['bootstrap/module_application_inventory.py','bootstrap/module_application_contracts.py',
      'bootstrap/module_public_input_installers.py','bootstrap/native_access_state.py',
      'source-inventory.json','source-provenance.json',
      ...(app==='melange'?['sources/fec/surfaces/melange_public_data.py']:[]),
      ...(app==='terrier'?['sources/server/research/street_views.py']:[])];
    for(const name of changes){f.write(f.program,f.prefix+name,'retained '+name);f.replace(f.prefix+name,'reviewed '+name);}
    f.replace(helper,'reviewed fixed cache helper');f.save();
    const before=producer.payloadFiles(f.program,'unused.exe');
    const oldBytes=new Map([...before].map(([name,file])=>[name,fs.readFileSync(file)]));
    const out=f.run(),expected=app==='mentat'?8:9;
    assert.equal(out.replacements.length,expected);assert.equal(out.inputs.length,expected+1);
    assert.equal(out.files.size,expected+1);assert.equal(out.files.get(helper),path.join(f.overlay,'files',helper));
    assert.equal(fs.existsSync(path.join(f.program,helper)),false);
    const include=producer.payloadInclude(out.files);
    assert.equal((include.match(/^  File /gm)||[]).length,out.files.size);
    assert.equal((include.match(/\/oname=module_catalogue_cache\.py/g)||[]).length,1);
    for(const [name,raw] of oldBytes)assert.deepEqual(fs.readFileSync(before.get(name)),raw);
    assert.equal(out.files.get('vendor.dll'),before.get('vendor.dll'));
  }
});
test('new helper exception cannot add other bootstrap, cross-app, or native members',t=>{
  for(const app of ['melange','mentat','terrier']){
    const f=fixture(t,app),helper=f.prefix+'bootstrap/module_catalogue_cache.py';
    f.replace(helper,'reviewed fixed cache helper');f.save();assert.ok(f.run().files.has(helper));
    const row=f.value.files[1];
    for(const name of [f.prefix+'bootstrap/module_application_contracts.py',f.prefix+'bootstrap/arbitrary.py',
      'resources/runtime/other/bootstrap/module_catalogue_cache.py',helper.toUpperCase()]){
      row.path=name;f.save();assert.throws(f.run,/Invalid source overlay member/);
    }
    row.path=helper;
    const raw=Buffer.from('MZ native content in added helper');
    fs.writeFileSync(path.join(f.overlay,'files',helper),raw);
    Object.assign(row,{bytes:raw.length,sha256:hash(raw)});f.save();assert.throws(f.run,/native images/);
  }
});
test('overlay member budget follows each exact application allowlist',t=>{
  for(const app of ['melange','mentat','terrier']){
    const f=fixture(t,app),limit=app==='mentat'?8:9;
    while(f.value.files.length<=limit)f.value.files.push({...f.value.files[0]});
    f.save();assert.throws(f.run,/Invalid source overlay identity/);
  }
});
test('Terrier committed route replacement is permitted without vendor or native overrides',t=>{
  const f=fixture(t),name=f.prefix+'sources/server/research/street_views.py';
  f.write(f.program,name,'old guard');f.replace(name,'new guard');f.save();assert.ok(f.run().files.has(name));
  f.value.files[1].path='vendor.dll';f.save();assert.throws(f.run,/Invalid source overlay member/);
});
test('cross-app, traversal, absolute, backslash, case aliases and unreviewed sources are refused',t=>{
  const f=fixture(t);
  for(const name of ['resources/runtime/mentat/bootstrap/terrier_standalone.py','../escape.py','C:/escape.py',f.name.replaceAll('/','\\'),f.name.toUpperCase(),f.prefix+'sources/other.py']){
    f.value.files[0].path=name;f.save();assert.throws(f.run,/Invalid source overlay member/);
  }
});
test('missing existing path, duplicate entries and extra manifest fields are refused',t=>{
  const f=fixture(t);fs.unlinkSync(f.base);assert.throws(f.run,/Invalid source overlay member/);
  f.write(f.program,f.name,'old');f.value.files.push({...f.value.files[0]});f.save();assert.throws(f.run,/Invalid source overlay member/);
  f.value.files.pop();f.value.authority='ignored';f.save();assert.throws(f.run,/Invalid source overlay identity/);
});
test('wrong version or source identity and modified hash or size are refused',t=>{
  const f=fixture(t);
  for(const [key,value] of [['version','1.0.30'],['appId','melange'],['clientCommit','bad'],['sourceCommit','bad']]){
    const old=f.value[key];f.value[key]=value;f.save();assert.throws(f.run,/identity/);f.value[key]=old;
  }
  f.save();fs.appendFileSync(path.join(f.overlay,'files',f.name),'tamper');assert.throws(f.run,/bytes differ/);
});
test('unexpected overlay files and PE content under a Python name are refused',t=>{
  const f=fixture(t);const extra=f.write(path.join(f.overlay,'files'),'extra.txt','unexpected');
  assert.throws(f.run,/inventory is not closed/);fs.unlinkSync(extra);
  const raw=Buffer.from('MZ disguised native fixture');fs.writeFileSync(path.join(f.overlay,'files',f.name),raw);
  Object.assign(f.value.files[0],{bytes:raw.length,sha256:hash(raw)});f.save();assert.throws(f.run,/native images/);
});
test('hard links and redirected overlay directories are refused',t=>{
  const f=fixture(t),file=path.join(f.overlay,'files',f.name),alias=path.join(f.root,'alias.py');
  fs.linkSync(file,alias);assert.throws(f.run,/physical/);fs.unlinkSync(alias);
  const real=path.join(f.overlay,'actual-files');fs.renameSync(path.join(f.overlay,'files'),real);
  fs.symlinkSync(real,path.join(f.overlay,'files'),process.platform==='win32'?'junction':'dir');
  assert.throws(f.run,/physical/);
});
test('exact NSIS include emits every effective input once with safe dollar and quote escaping',t=>{
  const f=fixture(t),out=f.run();
  out.files.set('folder $/name " x.txt',path.join(f.root,'source $ " x.txt'));
  const include=producer.payloadInclude(out.files);
  assert.equal((include.match(/^  File /gm)||[]).length,out.files.size);
  for(const line of include.split('\n').filter(value=>/^  File /.test(value)))assert.match(line,/^  File "\/oname=/,'NSIS requires the whole oname argument quoted');
  assert.equal((include.match(/terrier_standalone\.py"/g)||[]).length,2,'one destination and one new source');
  assert.ok(!include.includes(f.base));assert.ok(!include.includes('File /r'));
  assert.ok(include.includes('folder $$'));assert.ok(include.includes('$\\"'));
  for(const line of include.split('\n').filter(value=>/^  (File |SetOutPath )/.test(value)))assert.ok(include.includes(line+'\n  IfErrors extraction_failed'));
});
test('source overlay argument is explicit and duplicate flags are refused',()=>{
  const args=['--app','terrier','--version','1.0.31','--program','base','--output','out.exe','--makensis','compiler','--source-overlay','manifest.json'];
  assert.equal(producer.argumentsFor(args).sourceOverlay,'manifest.json');
  assert.throws(()=>producer.argumentsFor([...args,'--source-overlay','other.json']),/repeated/);
});
test('duplicate JSON properties cannot acquire a producer receipt',t=>{
  const f=fixture(t);fs.writeFileSync(f.manifest,'{"schemaVersion":1,'+JSON.stringify(f.value).slice(1));
  assert.throws(f.run,/canonical JSON/);
});
// Minimal PE carrying only the Electron ASAR integrity resource for the given archive.
function integrityExe(archive,file='resources\\app.asar'){
  const asar=require('@electron/asar'),{NtExecutable,NtExecutableResource}=require('resedit'),pe=NtExecutable.createEmpty(),resources=NtExecutableResource.from(pe);
  resources.entries.push({type:'INTEGRITY',id:'ELECTRONASAR',lang:1033,codepage:0,bin:Buffer.from(JSON.stringify([{file,alg:'SHA256',value:hash(asar.getRawHeader(archive).headerString)}]))});
  resources.outputResource(pe);return Buffer.from(pe.generate());
}
async function compilerFixture(t,mutation,integrityFile){
  const f=fixture(t),asar=require('@electron/asar'),vm=require('node:vm'),{createRequire}=require('node:module');
  f.write(f.program,'resources/runtime/terrier/python/python.exe','inert backend interpreter fixture');
  const client=path.join(f.root,'client');fs.mkdirSync(client);
  fs.writeFileSync(path.join(client,'package.json'),JSON.stringify({name:'terrier-desktop',version:'1.0.31',desktopAppConfig:{appId:'terrier',desktopUninstaller:false}}));
  await asar.createPackage(client,path.join(f.program,'resources/app.asar'));
  f.write(f.program,'Terrier.exe',integrityExe(path.join(f.program,'resources/app.asar'),integrityFile));
  const compiler=f.write(f.root,'nsis/Bin/makensis.exe','never executed');
  f.write(f.root,'nsis/Contrib/Language files/English.nlf','fixture');
  const output=path.join(f.root,'release/fixture.exe'),filename=require.resolve('../build-plugin-free.cjs'),localRequire=createRequire(filename);
  let calls=0;
  const fakeRequire=name=>name==='node:child_process'?{spawnSync:()=>{
    calls++;if(mutation)mutation(f,output);fs.writeFileSync(output,'inert fixture compiler output');return{status:0};
  }}:localRequire(name);
  const module={exports:{}};
  vm.runInNewContext(fs.readFileSync(filename,'utf8'),{require:fakeRequire,module,exports:module.exports,__dirname:path.dirname(filename),process,Buffer},{filename});
  return {f,output,run:()=>module.exports.build({appId:'terrier',version:'1.0.31',program:f.program,output,makensis:compiler,sourceOverlay:f.manifest,compression:'zlib'}),calls:()=>calls};
}
test('producer rechecks its closed overlay and exact generated include after compiler exit',async t=>{
  const mutations={extra:(f)=>f.write(path.join(f.overlay,'files'),'unexpected.py','extra'),
    bytes:(f)=>fs.appendFileSync(path.join(f.overlay,'files',f.name),'changed'),
    manifest:(f)=>fs.appendFileSync(f.manifest,'\n'),
    identity:(f)=>{const file=path.join(f.overlay,'files',f.name),raw=fs.readFileSync(file);fs.renameSync(file,file+'.previous');fs.writeFileSync(file,raw);fs.unlinkSync(file+'.previous');},
    include:(_f,out)=>fs.appendFileSync(out+'.work/payload.nsh','changed')};
  for(const [name,mutation] of Object.entries(mutations)){
    const c=await compilerFixture(t,mutation);assert.throws(c.run,/overlay|include|canonical/,name);assert.equal(c.calls(),1);
    assert.equal(fs.existsSync(c.output+'.build.json'),false,'failed compiler input proof cannot create receipt');
  }
  const c=await compilerFixture(t),before=fs.readFileSync(c.f.base),result=c.run();
  assert.equal(c.calls(),1);assert.ok(result.sourceOverlay);assert.equal(result.inputFileCount,5);
  assert.deepEqual(fs.readFileSync(c.f.base),before);assert.equal(result.payloadIncludeSha256,hash(fs.readFileSync(result.payloadInclude)));
});
test('producer refuses a main EXE whose ASAR integrity key or hash differs, before compiling',async t=>{
  // 1.0.37 attempt 1: 'resources\app.asar' in a JS literal became 'resourcesapp.asar'; Electron's fuse then refuses to start.
  const lost=await compilerFixture(t,undefined,'resourcesapp.asar');assert.throws(lost.run,/ASAR integrity differs.*resourcesapp\.asar/);assert.equal(lost.calls(),0);
  const slash=await compilerFixture(t,undefined,'resources/app.asar');assert.throws(slash.run,/ASAR integrity differs/);assert.equal(slash.calls(),0);
  // A re-packed app.asar after the EXE was patched (stale header hash) is refused the same way.
  const stale=await compilerFixture(t),client=path.join(stale.f.root,'client');fs.writeFileSync(path.join(client,'extra.js'),'changed header');
  await require('@electron/asar').createPackage(client,path.join(stale.f.program,'resources/app.asar'));
  assert.throws(stale.run,/ASAR integrity differs/);assert.equal(stale.calls(),0);
});
test('producer refuses a payload without the backend interpreter the installer guard probes',async t=>{
  const c=await compilerFixture(t);fs.rmSync(path.join(c.f.program,'resources/runtime/terrier/python/python.exe'));
  assert.throws(c.run,/backend interpreter/);assert.equal(c.calls(),0);
});
