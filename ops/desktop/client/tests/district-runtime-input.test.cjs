'use strict';
// Generated programme table and payloads; actual byte verification, no real app.
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path'),crypto=require('node:crypto'),vm=require('node:vm'),{createRequire}=require('node:module');
const native=require('../module-data-runtime-boundary.cjs'),failures=require('../startup-failure.cjs'),{ROLES}=require('../github-district-protocol.cjs');
function fixture(t){
 const root=fs.realpathSync.native(fs.mkdtempSync(path.join(os.tmpdir(),'district-runtime-capability-'))),profile=path.join(root,'profile'),source=path.join(root,'source'),bootstrap=path.join(root,'bootstrap'),directory=path.join(root,'data'),state=path.join(root,'state');
 for(const value of [profile,source,bootstrap,directory,state])fs.mkdirSync(value);
 fs.writeFileSync(path.join(source,'app.py'),'# generated source');fs.writeFileSync(path.join(bootstrap,'desktop_backend.py'),'# generated bootstrap');
 const hash=bytes=>crypto.createHash('sha256').update(bytes).digest('hex'),programFiles=[['source',source,'app.py'],['bootstrap',bootstrap,'desktop_backend.py']].map(([area,base,name])=>{const raw=fs.readFileSync(path.join(base,name));return{root:area,path:name,bytes:raw.length,sha256:hash(raw)};});
 const contract={programFiles,programFingerprint:native.programFingerprint(programFiles)},runtime={definition:{id:'terrier'},userData:profile,resources:root,child:{pid:71}};
 native.initializeModuleRuntime(runtime,()=>({source,bootstrap}));
 const verify=runtime=>{try{native.verifyProgram(runtime,contract);return contract;}catch{throw failures.programFailure();}};
 const file=path.resolve(__dirname,'../district-runtime-input.cjs'),real=createRequire(file),module={exports:{}};
 vm.runInNewContext(fs.readFileSync(file,'utf8'),{module,require:name=>name==='./district-data-probe.cjs'?{...real(name),verifyDistrictProgram:verify}:name==='./backend-command.cjs'?{backendCommand:()=>({runtime:root})}:real(name),Buffer,URL,setTimeout,clearTimeout,structuredClone},{filename:file});
 const api=module.exports,snapshotId='co-cd005-123456abcdef',roles=[...ROLES,'snapshots/'+snapshotId+'/manifest.json'],files=roles.map(role=>{const raw=Buffer.from('{}'),file=path.join(directory,role);fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,raw);return{role,path:'co-05/data/'+role,bytes:raw.length,sha256:hash(raw)};});
 const configuration={dataDirectory:directory,district:'co-05',standaloneGitHubData:{schemaVersion:2}},calls=[];let input;
 api.bindDistrictConfiguration(configuration,{profile,directory,district:'co-05',files,verify:async()=>calls.push('verify'),commit:async()=>calls.push('commit'),close:async()=>calls.push('close')});
 t.after(async()=>{await input?.close();await api.discardDistrictConfiguration(configuration);fs.rmSync(root,{recursive:true,force:true});});
 return {api,runtime,configuration,calls,source,snapshotId,roots:{data:directory,state,district:'co-05'},consume(){input=api.consumeDistrictConfiguration(runtime,configuration);return input;}};
}
test('copied settings cannot mint a district capability; original is consumed once and secret stays only in stdin',async t=>{
 const f=fixture(t);assert.equal(f.api.consumeDistrictConfiguration(f.runtime,structuredClone(f.configuration)),null);
 const input=f.consume();assert.ok(input);assert.equal(f.api.consumeDistrictConfiguration(f.runtime,f.configuration),null);await input.validate();
 const bytes=input.frame(f.roots,f.source),frame=JSON.parse(bytes.subarray(4));assert.equal(bytes.readUInt32BE(),bytes.length-4);
 assert.equal(frame.commitToken.length,43);assert.equal(JSON.stringify(f.configuration).includes(frame.commitToken),false);
 assert.equal(JSON.stringify(input.diagnostic()).includes(frame.commitToken),false);
 const context=Object.fromEntries(['schemaVersion','appId','launchNonce','programFingerprint','sourceDigest','district','rootsDigest'].map(key=>[key,frame[key]]));
 const health={pid:71,districtData:{...context,phase:'prepared',snapshot:f.snapshotId}};
 assert.equal(input.matches(health,'prepared'),true);assert.equal(input.matches(health,'active'),false);
 for(const [name,value]of [['launchNonce','x'.repeat(43)],['sourceDigest','0'.repeat(64)],['programFingerprint','1'.repeat(64)]])assert.equal(input.matches({...health,districtData:{...health.districtData,[name]:value}},'prepared'),false);
 assert.equal(input.matches({...health,pid:72},'prepared'),false);
 await input.close();await input.close();assert.equal(f.calls.filter(value=>value==='close').length,1);
});
test('changed exact configuration or installed programme refuses startup and releases owned handles',async t=>{
 const changed=fixture(t);changed.configuration.district='ct-01';assert.throws(()=>changed.consume(),{code:'context'});
 const programme=fixture(t);fs.appendFileSync(path.join(programme.source,'app.py'),'# modified');assert.throws(()=>programme.consume(),{code:'program'});
 await new Promise(resolve=>setImmediate(resolve));assert.ok(changed.calls.includes('close'));assert.ok(programme.calls.includes('close'));
});
test('native frame uses the canonical roster order used by its source digest',async t=>{
 const f=fixture(t),input=f.consume(),frame=JSON.parse(input.frame(f.roots,f.source).subarray(4));
 // The fixture appends snapshots after walk.sqlite3, like the signed provider;
 // Python requires the same lexicographic order that districtSourceDigest uses.
 assert.deepEqual(frame.files.map(row=>row.role),frame.files.map(row=>row.role).sort());
 const expected=crypto.createHash('sha256').update(require('../access-client.cjs').canonical({district:frame.district,files:frame.files})).digest('hex');
 assert.equal(frame.sourceDigest,expected);
});
test('canceling an issued configuration closes it without activation; a clone cannot cancel its owner',async t=>{
 const f=fixture(t);assert.equal(await f.api.discardDistrictConfiguration(structuredClone(f.configuration)),false);assert.equal(await f.api.discardDistrictConfiguration(f.configuration),true);
 assert.equal(f.api.consumeDistrictConfiguration(f.runtime,f.configuration),null);assert.deepEqual(f.calls,['close']);
});
