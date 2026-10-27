'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os'),crypto=require('node:crypto');
const {spawnSync}=require('node:child_process');
const {verifyNativeFiles,asarMember,extractVerifiedDirectory}=require('../../packaging/verify_directory_release.cjs');
const {signPool,THUMBPRINT}=require('../release-signing.cjs');
function fixture(){const files=Array.from({length:9},(_,n)=>({item:{path:n?'native'+n+'.dll':'Melange.exe',sha256:String(n).repeat(64)},file:'/private/native'+n})),built=new Map(files.map(({item},n)=>[item.path,{sha256:item.sha256,thumbprint:n?'vendor':THUMBPRINT}]));return {files,built};}
test('final verifier checks every PE with at most four workers and preserves exact evidence',async()=>{
 const {files,built}=fixture();let active=0,maximum=0;const visited=[];
 const signing={signPool,THUMBPRINT,signFile:async(file,root,options)=>{assert.equal(root,'/private');assert.equal(options.verify,true);const n=files.findIndex(item=>item.file===file);assert.equal(options.owned,n===0);active++;maximum=Math.max(maximum,active);await new Promise(resolve=>setTimeout(resolve,5));visited.push(n);active--;return {sha256:files[n].item.sha256,thumbprint:n?'vendor':THUMBPRINT,timestamped:n===0,status:'Valid'};}};
 const result=await verifyNativeFiles(files,signing,'/private','Melange.exe',built);assert.equal(result.length,files.length);assert.equal(new Set(visited).size,files.length);assert.equal(maximum,4);assert.equal(active,0);
});
test('final verifier drains pending workers and propagates failure before returning evidence',async()=>{
 const {files,built}=fixture();let active=0;const visited=[];
 const signing={signPool,THUMBPRINT,signFile:async file=>{const n=files.findIndex(item=>item.file===file);active++;visited.push(n);try{await new Promise(resolve=>setTimeout(resolve,n?15:1));if(!n)throw new Error('signature failure');return {sha256:files[n].item.sha256,thumbprint:'vendor',timestamped:false,status:'Valid'};}finally{active--;}}};
 await assert.rejects(verifyNativeFiles(files,signing,'/private','Melange.exe',built),/signature failure/);assert.equal(active,0);assert.ok(visited.length<=4);
});

function temporary(t){const parent=fs.realpathSync.native(os.tmpdir()),root=fs.mkdtempSync(path.join(parent,'directory-verifier-test-'));t.after(()=>{assert.equal(path.dirname(root),parent);assert.ok(path.basename(root).startsWith('directory-verifier-test-'));fs.rmSync(root,{recursive:true,force:true,maxRetries:5});});return root;}
const digest=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
function packageFixture(t){
 const root=temporary(t),source=path.join(root,'source'),output=path.join(root,'output');fs.mkdirSync(output);
 for(const [name,bytes] of Object.entries({'Melange.exe':'MZ fixture','resources/app.asar':'ASAR fixture','resources/runtime/melange/module.py':'runtime fixture'})){const file=path.join(source,...name.split('/'));fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,bytes);}
 const archive=path.join(output,'fixture.zip'),created=spawnSync('python',['-B',path.resolve(__dirname,'../../packaging/directory_zip.py'),'--source',source,'--output',archive,'--app','melange','--version','1.0.20'],{encoding:'utf8'});assert.equal(created.status,0,created.stderr);
 const descriptor=JSON.parse(created.stdout),options={appId:'melange',version:'1.0.20',entrypoint:'Melange.exe',archive:descriptor};fs.writeFileSync(path.join(output,'package.json'),JSON.stringify(descriptor));
 return {root,output,descriptor,options,client:path.resolve(__dirname,'..'),directory:require('../directory-package.cjs')};
}

test('nested ASAR dependency lookup uses the native Windows member separator',async t=>{
 const root=temporary(t),source=path.join(root,'app'),dependency=path.join(source,'node_modules','yauzl');fs.mkdirSync(dependency,{recursive:true});
 fs.writeFileSync(path.join(dependency,'package.json'),JSON.stringify({name:'yauzl',version:'3.4.0'}));fs.writeFileSync(path.join(dependency,'index.js'),'module.exports={fixture:true};');
 const asar=require('@electron/asar'),archive=path.join(root,'app.asar');await asar.createPackage(source,archive);
 assert.equal(JSON.parse(asarMember(asar,archive,'node_modules','yauzl','package.json')).version,'3.4.0');assert.equal(asarMember(asar,archive,'node_modules','yauzl','index.js').toString(),'module.exports={fixture:true};');
});

test('existing extraction continuation uses fresh ZIP authority and refuses a locally rewritten inventory',async t=>{
 const f=packageFixture(t),destination=path.join(f.root,'retained'),inventory=await f.directory.extract(f.descriptor.path,destination,f.options);
 const continued=await extractVerifiedDirectory({...f,destination,reuse:true});assert.deepEqual(continued.inventory,inventory);
 const app=path.join(destination,'Melange.exe'),changed=Buffer.alloc(fs.statSync(app).size,120);fs.writeFileSync(app,changed);
 const local=structuredClone(inventory);local.files.find(row=>row.path==='Melange.exe').sha256=digest(changed);fs.writeFileSync(path.join(destination,'directory-package.json'),JSON.stringify(local));
 await assert.rejects(extractVerifiedDirectory({...f,destination,reuse:true}),/hash mismatch|inventory changed/);
});

test('fresh native verifier extraction records helper and tool hashes and retains the original inventory',{skip:!process.env.NATIVE_EXTRACT_7ZA},async t=>{
 const f=packageFixture(t),tool=fs.realpathSync.native(process.env.NATIVE_EXTRACT_7ZA),sha256=digest(fs.readFileSync(tool));
 fs.writeFileSync(path.join(f.output,'packager-implementation.json'),JSON.stringify({source:'native-controller',nativeTool:{path:tool,sha256}}));
 const result=await extractVerifiedDirectory({...f,destination:path.join(f.root,'native')});
 assert.equal(result.inventory.appId,'melange');assert.equal(result.evidence.nativeToolSha256,sha256);assert.equal(result.evidence.helperImplementationSha256,digest(fs.readFileSync(path.resolve(__dirname,'../../packaging/native_extract_directory.py'))));
});
