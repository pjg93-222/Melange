'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const crypto=require('node:crypto');
const p=require('../github-module-protocol.cjs');
const {canonical}=require('../access-client.cjs');
const {signed,environment,sha}=require('./fixtures/github-module-fixture.cjs');
function check(f){const pointer=p.pointer(f.appId,f.envelope,f.publicKeys);return p.manifest(f.appId,f.manifestBytes,pointer,f.registry);}
test('app-specific signatures, fixed repository and independent high-water domains',()=>{
 for(const appId of ['melange','mentat']){const f=signed(appId);assert.equal(check(f).segmentCount,2);assert.equal(check(f).totalBytes,f.bytes.length);assert.throws(()=>p.pointer(appId==='melange'?'mentat':'melange',f.envelope,f.publicKeys),/Unsupported/);}
 const f=signed(),ok=p.pointer('mentat',f.envelope,f.publicKeys);assert.equal(p.pointer('mentat',f.envelope,f.publicKeys,{catalogSequence:1,pointerDigest:ok.digest}).digest,ok.digest);
 assert.throws(()=>p.pointer('mentat',f.envelope,f.publicKeys,{catalogSequence:2,pointerDigest:ok.digest}),/rollback/);
 assert.throws(()=>p.pointer('mentat',f.envelope,f.publicKeys,{catalogSequence:1,pointerDigest:'f'.repeat(64)}),/equivocation/);
});
test('rejects signature, scope, noncanonical/duplicate signed fields and binary tags',()=>{
 for(const mutate of [f=>{f.value.repository='pjg93-222/other';},f=>{f.value.purpose='melange-public-module-data';},f=>{f.value.releaseTag='desktop-v1.0.11';},f=>{f.value.extra=true;},f=>{f.value.releaseCommit='0'.repeat(40);},f=>{f.value.manifest.bytes=p.MAX_MANIFEST+1;}]){const f=signed();mutate(f);f.envelope=f.sign(f.value);assert.throws(()=>p.pointer('mentat',f.envelope,f.publicKeys));}
 const f=signed(),bad={...f.envelope,signature:Buffer.alloc(64).toString('base64')};assert.throws(()=>p.pointer('mentat',bad,f.publicKeys),/signature/);
 for(const raw of [JSON.stringify(f.value,null,2),canonical(f.value).replace('"schemaVersion":1','"schemaVersion":1,"schemaVersion":1')]){const bytes=Buffer.from(raw);const envelope={...f.envelope,payload:bytes.toString('base64'),signature:crypto.sign(null,bytes,f.keys.privateKey).toString('base64')};assert.throws(()=>p.pointer('mentat',envelope,f.publicKeys));}
});
test('typed logical roles support large files only through ordered bounded raw segments',()=>{
 const f=signed(),role=f.manifest.datasets[0].objects[0];f.registry[Object.keys(f.registry)[0]].roles.aggregate.maxBytes=4*p.MAX_SEGMENT;f.registry[Object.keys(f.registry)[0]].maxTotalBytes=4*p.MAX_SEGMENT;
 role.bytes=3351265280;role.sha256='d'.repeat(64);role.segments=[0,1,2,3].map((n)=>({asset:'lda-'+n+'.bin',bytes:n<3?p.MAX_SEGMENT:role.bytes-3*p.MAX_SEGMENT,sha256:'e'.repeat(64)}));f.rebind();assert.equal(check(f).totalBytes,3351265280);
 role.segments[0].bytes++;f.rebind();assert.throws(()=>check(f),/segment/);
});
test('rejects missing/unknown roles, segment sums/counts, case aliases and unsafe names',()=>{
 const mutations=[f=>f.manifest.datasets[0].objects[0].segments[0].bytes++,f=>{f.manifest.datasets[0].objects[0].segments[0].asset='../outside';},f=>{f.manifest.datasets[0].objects[0].segments[0].asset='CON.txt';},f=>{f.manifest.datasets[0].objects[0].segments[0].asset='file:stream';},f=>{f.manifest.datasets[0].objects[0].segments[0].asset='trailing.';},f=>{f.manifest.datasets[0].objects[0].segments[1].asset=f.manifest.datasets[0].objects[0].segments[0].asset.toUpperCase();},f=>{f.manifest.datasets[0].objects[0].role='credentials';},f=>{f.manifest.datasets[0].objects=[];f.manifest.datasets[0].counts.files=0;},f=>{f.manifest.datasets[0].objects[0].segments=Array.from({length:33},(_,n)=>({asset:'segment-'+n,bytes:1,sha256:'a'.repeat(64)}));}];
 for(const mutate of mutations){const f=signed();mutate(f);f.rebind();assert.throws(()=>check(f));}
});
test('compiled paths, required kinds and total budgets cannot be expanded by a manifest',()=>{
 for(const value of ['../outside','root/CON.txt','root/file.','root/file:stream','script.js','data.zip']){const f=signed();f.registry[Object.keys(f.registry)[0]].roles.aggregate.path=value;assert.throws(()=>check(f));}
 const f=signed(),kind=Object.keys(f.registry)[0];f.registry[kind].maxTotalBytes=p.MAX_TOTAL+1;assert.throws(()=>check(f));
 const g=signed();assert.throws(()=>p.manifest('mentat',g.manifestBytes,p.pointer('mentat',g.envelope,g.publicKeys),g.registry,['mentat.not-compiled.v1']));
 g.manifest.datasets[0].kind='mentat.not-compiled.v1';g.rebind();assert.throws(()=>check(g));
});
test('whole-role and segment hashes are independently required and metadata hash-bound',()=>{
 const f=signed(),pointer=p.pointer('mentat',f.envelope,f.publicKeys);assert.throws(()=>p.manifest('mentat',Buffer.from('{}'),pointer,f.registry),/integrity/);
 for(const key of ['sha256']){f.manifest.datasets[0].objects[0][key]='not-a-hash';f.rebind();assert.throws(()=>check(f));}
 const g=signed();g.manifest.datasets[0].objects[0].segments[0].sha256='not-a-hash';g.rebind();assert.throws(()=>check(g));
 assert.notEqual(sha(Buffer.from('firstsecond')),sha(Buffer.from('secondfirst')));
});
test('only verified existing-owner bindings qualify; remembered recipients and revocation do not',async()=>{
 const f=environment();try{const auth=await f.options.authorize();assert.equal(p.authorized('mentat',f.selected,auth),true);assert.equal(p.authorized('melange',f.selected,auth),false);assert.equal(p.authorized('mentat',f.selected,{...auth,owner:null,session:{unlocked:true}}),false);auth.accepted.revoked=true;assert.equal(p.authorized('mentat',f.selected,auth),false);auth.accepted.revoked=false;auth.owner.dataBindings[0].districtId='co-05';assert.equal(p.authorized('mentat',f.selected,auth),false);}finally{f.cleanup();}
});
test('the complete catalogue caps segments at256 and compiled/actual totals at32GiB',()=>{
 const f=signed(),dataset=f.manifest.datasets[0],kind=dataset.kind,roles={};dataset.objects=[];
 for(let role=0;role<9;role++){const name='role'+role;roles[name]={path:name+'.json',maxBytes:32};dataset.objects.push({role:name,bytes:32,sha256:'a'.repeat(64),segments:Array.from({length:32},(_,n)=>({asset:name+'-'+n+'.bin',bytes:1,sha256:'b'.repeat(64)}))});}
 dataset.counts.files=9;f.registry[kind].roles=roles;f.registry[kind].maxTotalBytes=288;f.rebind();assert.throws(()=>check(f),/total budget/);
 dataset.objects.pop();delete roles.role8;dataset.counts.files=8;f.rebind();assert.equal(check(f).segmentCount,256);
 const g=signed(),other='mentat.extra.v1';g.registry[Object.keys(g.registry)[0]].maxTotalBytes=p.MAX_TOTAL;g.registry[other]={...g.registry[Object.keys(g.registry)[0]],roles:{extra:{path:'extra.json',maxBytes:1}},maxTotalBytes:1};assert.throws(()=>p.checkedRegistry('mentat',g.registry),/budget/);
});
