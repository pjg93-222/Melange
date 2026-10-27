'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),crypto=require('node:crypto');
const {DirectoryInstaller}=require('../directory-installer.cjs');

function fixture(t,overrides={}){
 const parent=fs.realpathSync(os.tmpdir()),root=fs.mkdtempSync(path.join(parent,'directory-update-review-'));
 t.after(()=>{
  assert.equal(path.dirname(path.resolve(root)),parent);
  assert.ok(path.basename(root).startsWith('directory-update-review-'));
  fs.rmSync(root,{recursive:true,force:true});
 });
 const programs=path.join(root,'programs'),zip=path.join(root,'melange-1.0.21-win32-x64.zip');
 const bytes=Buffer.from('Synthetic archive for adapter-only filesystem tests.');
 fs.mkdirSync(programs);fs.writeFileSync(zip,bytes);
 const manifest={appId:'melange',version:'1.0.21',publisherThumbprints:['A'.repeat(40)],package:{entrypoint:'Melange.exe',size:bytes.length,sha256:crypto.createHash('sha256').update(bytes).digest('hex'),sha512:crypto.createHash('sha512').update(bytes).digest('base64')}};
 const inventory={schemaVersion:1,appId:'melange',version:'1.0.21',entrypoint:'Melange.exe',files:[]};
 const archive={
  inspect:async()=>inventory,
  extract:async(_zip,destination)=>{fs.mkdirSync(destination);fs.writeFileSync(path.join(destination,'Melange.exe'),'program');return inventory;},
  verifyDirectory:async directory=>{assert.equal(fs.readFileSync(path.join(directory,'Melange.exe'),'utf8'),'program');return inventory;},
  ...overrides.archive
 };
 const activated=[];
 const installer=new DirectoryInstaller({root:programs,appId:'melange',archive,verifyProof:()=>{},verifyNativePackage:async()=>{},activate:async(...args)=>activated.push(args),...overrides,archive});
 return {root,programs,zip,manifest,archive,installer,activated,target:path.join(programs,'Melange-1.0.21')};
}

function actualArchive(f){
 const writer=`import hashlib,json,sys,zipfile
files={'Melange.exe':b'MZ fixture program','resources/app.asar':b'approved program bytes'}
inventory={'schemaVersion':1,'appId':'melange','version':'1.0.21','entrypoint':'Melange.exe','files':[{'path':name,'size':len(data),'sha256':hashlib.sha256(data).hexdigest()} for name,data in files.items()]}
with zipfile.ZipFile(sys.argv[1],'w') as archive:
 archive.writestr('directory-package.json',json.dumps(inventory,separators=(',',':')))
 for name,data in files.items():archive.writestr(name,data)
`;
 const result=require('node:child_process').spawnSync('python',['-c',writer,f.zip],{encoding:'utf8'});assert.equal(result.status,0,result.stderr);
 const bytes=fs.readFileSync(f.zip);Object.assign(f.manifest.package,{size:bytes.length,sha256:crypto.createHash('sha256').update(bytes).digest('hex'),sha512:crypto.createHash('sha512').update(bytes).digest('base64')});
 f.installer.archive=require('../directory-package.cjs');
}

async function quarantinedArchive(t){
 const f=fixture(t);actualArchive(f);let calls=0,error;
 f.installer.verifyNativePackage=async()=>{if(++calls===2)throw new Error('Transient policy read failure');};
 await assert.rejects(f.installer.prepare(f.zip,f.manifest),value=>{error=value;return /Transient policy/.test(value.message);});
 f.installer.verifyNativePackage=async()=>{};
 return {...f,failure:{directory:error.stagingDirectory,ownership:error.stagingOwnership,rootOwnership:error.stagingRootOwnership}};
}

test('explicit retry authenticates and clears one quarantine before restaging a transient policy failure',async t=>{
 const f=await quarantinedArchive(t);
 await f.installer.clearFailedStage(f.zip,f.manifest,f.failure);assert.equal(fs.existsSync(f.failure.directory),false);
 await f.installer.prepare(f.zip,f.manifest);assert.deepEqual(fs.readdirSync(f.programs),['Melange-1.0.21']);
});

for(const change of ['extra','modified','replacement'])test('explicit retry preserves quarantine after '+change,async t=>{
 const f=await quarantinedArchive(t),directory=f.failure.directory;
 if(change==='extra')fs.writeFileSync(path.join(directory,'user-note.txt'),'preserve');
 else if(change==='modified')fs.writeFileSync(path.join(directory,'resources','app.asar'),'changed application bytes');
 else{fs.renameSync(directory,directory+'.moved');fs.mkdirSync(directory);fs.writeFileSync(path.join(directory,'user-note.txt'),'preserve');}
 await assert.rejects(f.installer.clearFailedStage(f.zip,f.manifest,f.failure),/preserved at/);
 assert.equal(fs.existsSync(directory),true);assert.equal(fs.existsSync(f.target),false);
});

test('existing version folder is refused without replacing or deleting its files',async t=>{
 const f=fixture(t,{archive:{verifyDirectory:async()=>{throw new Error('Unrecognized existing folder');}}});
 fs.mkdirSync(f.target);const data=path.join(f.target,'user-note.txt');fs.writeFileSync(data,'keep me');
 await assert.rejects(f.installer.prepare(f.zip,f.manifest),/Unrecognized existing folder/);
 assert.equal(fs.readFileSync(data,'utf8'),'keep me');assert.deepEqual(f.activated,[]);
});

test('a target created during signature verification is never replaced',async t=>{
 const f=fixture(t);f.installer.verifyNativePackage=async()=>{fs.mkdirSync(f.target);fs.writeFileSync(path.join(f.target,'concurrent.txt'),'other owner');};
 await assert.rejects(f.installer.prepare(f.zip,f.manifest),/already exists/);
 assert.equal(fs.readFileSync(path.join(f.target,'concurrent.txt'),'utf8'),'other owner');
 assert.deepEqual(fs.readdirSync(f.programs),['Melange-1.0.21']);
});

test('native signature refusal cleans only the invocation staging folder',async t=>{
 const f=fixture(t,{verifyNativePackage:async()=>{throw new Error('Publisher mismatch');}});
 const retained=path.join(f.programs,'Melange-1.0.20');fs.mkdirSync(retained);fs.writeFileSync(path.join(retained,'keep.txt'),'previous');
 await assert.rejects(f.installer.prepare(f.zip,f.manifest),/Publisher mismatch/);
 assert.deepEqual(fs.readdirSync(f.programs),['Melange-1.0.20']);
 assert.equal(fs.readFileSync(path.join(retained,'keep.txt'),'utf8'),'previous');
});

test('cleanup preserves a replacement staging directory it no longer owns',async t=>{
 const f=fixture(t);let replacement;
 f.installer.verifyNativePackage=async executable=>{
  const staging=path.dirname(executable);
  fs.renameSync(staging,staging+'.moved');
  fs.mkdirSync(staging);replacement=path.join(staging,'belongs-to-another-operation.txt');
  fs.writeFileSync(replacement,'preserve');
  throw new Error('Publisher mismatch after directory replacement');
 };
 await assert.rejects(f.installer.prepare(f.zip,f.manifest),/Publisher mismatch/);
 assert.equal(fs.existsSync(replacement),true,'cleanup must not remove a replacement directory');
 assert.equal(fs.readFileSync(replacement,'utf8'),'preserve');
});

test('a replacement staging directory cannot be promoted after signature verification',async t=>{
 const f=fixture(t);let replacement;
 f.installer.verifyNativePackage=async executable=>{
  const staging=path.dirname(executable);fs.renameSync(staging,staging+'.moved');
  fs.mkdirSync(staging);replacement=path.join(staging,'foreign.txt');fs.writeFileSync(replacement,'preserve');
 };
 await assert.rejects(f.installer.prepare(f.zip,f.manifest),/ownership changed/);
 assert.equal(fs.existsSync(f.target),false);assert.equal(fs.readFileSync(replacement,'utf8'),'preserve');
});

test('failed final verification quarantines its owned version and permits a clean retry',async t=>{
 const f=fixture(t),verify=f.archive.verifyDirectory;let failed;
 f.archive.verifyDirectory=async()=>{throw new Error('Final directory verification failed');};
 await assert.rejects(f.installer.prepare(f.zip,f.manifest),error=>{failed=error;return /Final directory/.test(error.message);});
 assert.equal(failed.directoryStageFailed,true);assert.equal(fs.existsSync(f.target),false);
 assert.equal(fs.readFileSync(path.join(failed.stagingDirectory,'Melange.exe'),'utf8'),'program');
 f.archive.verifyDirectory=verify;const prepared=await f.installer.prepare(f.zip,f.manifest);
 assert.equal(prepared.created,true);assert.equal(prepared.directory,f.target);
});

test('failed final verification never quarantines or deletes a replacement final directory',async t=>{
 const f=fixture(t);let foreign;
 f.archive.verifyDirectory=async directory=>{
  fs.renameSync(directory,directory+'.moved');fs.mkdirSync(directory);
  foreign=path.join(directory,'foreign.txt');fs.writeFileSync(foreign,'preserve');throw new Error('Final directory changed');
 };
 await assert.rejects(f.installer.prepare(f.zip,f.manifest),error=>Boolean(error.quarantineError));
 assert.equal(fs.readFileSync(foreign,'utf8'),'preserve');
});

test('cached archive changed after preparation cannot activate the verified directory',async t=>{
 const f=fixture(t);await f.installer.prepare(f.zip,f.manifest);
 const changed=fs.readFileSync(f.zip);changed[0]^=1;fs.writeFileSync(f.zip,changed);
 await assert.rejects(f.installer.launch(f.zip,f.manifest,true),error=>error.code==='PACKAGE_INTEGRITY');
 assert.deepEqual(f.activated,[]);assert.equal(fs.readFileSync(path.join(f.target,'Melange.exe'),'utf8'),'program');
});

test('inventory from a ZIP swapped only during inspection cannot authorize program bytes',async t=>{
 const f=fixture(t),archive=require('../directory-package.cjs'),{spawnSync}=require('node:child_process');
 const writer=`import hashlib,json,sys,zipfile
files={'Melange.exe':b'MZ same signed executable','resources/app.asar':sys.argv[2].encode()}
inventory={'schemaVersion':1,'appId':'melange','version':'1.0.21','entrypoint':'Melange.exe','files':[{'path':name,'size':len(data),'sha256':hashlib.sha256(data).hexdigest()} for name,data in files.items()]}
with zipfile.ZipFile(sys.argv[1],'x',compression=zipfile.ZIP_STORED) as archive:
 archive.writestr('directory-package.json',json.dumps(inventory,separators=(',',':')))
 for name,data in files.items():archive.writestr(name,data)
`;
 const original=path.join(f.root,'original.zip'),substituted=path.join(f.root,'substituted.zip');
 for(const [file,asar] of [[original,'approved code'],[substituted,'attacker code']]){
  const result=spawnSync('python',['-c',writer,file,asar],{encoding:'utf8'});assert.equal(result.status,0,result.stderr);
 }
 const approved=fs.readFileSync(original);
 fs.writeFileSync(f.zip,approved);
 Object.assign(f.manifest.package,{size:approved.length,sha256:crypto.createHash('sha256').update(approved).digest('hex'),sha512:crypto.createHash('sha512').update(approved).digest('base64')});
 const identity={appId:'melange',version:'1.0.21',entrypoint:'Melange.exe'};
 await archive.extract(substituted,f.target,identity);
 f.installer.archive={...archive,inspect:async(filename,options)=>{
  // Model an attacker swapping the path after the outer hash check, then
  // restoring the authentic archive before the final outer check.
  fs.copyFileSync(substituted,filename);
  try{return await archive.inspect(filename,options);}finally{fs.writeFileSync(filename,approved);}
 }};
 await assert.rejects(f.installer.launch(f.zip,f.manifest,true),/hash|integrity|archive changed/i);
 assert.deepEqual(f.activated,[]);
});

