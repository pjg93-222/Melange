'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os'),crypto=require('node:crypto');
const {spawnSync}=require('node:child_process');
const archive=require('../directory-package.cjs');
const identity={appId:'melange',version:'1.0.20',entrypoint:'Melange.exe'};
const nested='resources/runtime/melange/python/Lib/site-packages/shared/deep';
function fixture(t){
 const parent=fs.realpathSync.native(os.tmpdir()),root=fs.mkdtempSync(path.join(parent,'directory-cache-review-'));
 t.after(()=>{assert.equal(path.dirname(path.resolve(root)),parent);assert.ok(path.basename(root).startsWith('directory-cache-review-'));fs.rmSync(root,{recursive:true,force:true,maxRetries:5});});
 const files={'Melange.exe':'MZ fixture','resources/app.asar':'ASAR fixture',[nested+'/one.py']:'first module',[nested+'/two.py']:'second module'};
 const writer=`import hashlib,json,sys,zipfile
files={name:value.encode() for name,value in json.load(sys.stdin).items()}
inventory={'schemaVersion':1,'appId':'melange','version':'1.0.20','entrypoint':'Melange.exe','files':[{'path':name,'size':len(data),'sha256':hashlib.sha256(data).hexdigest()} for name,data in files.items()]}
with zipfile.ZipFile(sys.argv[1],'x') as archive:
 archive.writestr('directory-package.json',json.dumps(inventory,separators=(',',':')))
 for name,data in files.items():archive.writestr(name,data)
`;
 const zip=path.join(root,'package.zip'),result=spawnSync('python',['-B','-c',writer,zip],{input:JSON.stringify(files),encoding:'utf8'});
 assert.equal(result.status,0,result.stderr);
 const bytes=fs.readFileSync(zip),options={...identity,archive:{size:bytes.length,sha256:crypto.createHash('sha256').update(bytes).digest('hex'),sha512:crypto.createHash('sha512').update(bytes).digest('base64')}};
 return {root,zip,options,files,destination:path.join(root,'staging')};
}

function beforeFirstOpen(t,directory,action){
 const original=fs.promises.open;let replaced=false;
 t.mock.method(fs.promises,'open',async(...args)=>{
  if(path.dirname(String(args[0]))===directory&&!replaced){replaced=true;action();}
  return original(...args);
 });
 return ()=>replaced;
}

test('cached extraction directory replacement is refused before accepting written files',async t=>{
 const f=fixture(t),directory=path.join(f.destination,nested),first=path.join(directory,'one.py');
 const replaced=beforeFirstOpen(t,directory,()=>{
   fs.renameSync(directory,path.join(f.root,'saved-parent'));fs.mkdirSync(directory);
 });
 await assert.rejects(archive.extract(f.zip,f.destination,f.options),/changed|ownership/);
 assert.equal(replaced(),true);
 assert.equal(fs.existsSync(path.join(directory,'two.py')),false);
});

test('an ancestor replaced by a junction cannot redirect cached writes to a foreign tree',async t=>{
 const f=fixture(t),ancestor=path.join(f.destination,'resources','runtime'),foreign=path.join(f.root,'foreign');
 const suffix=path.join('melange','python','Lib','site-packages','shared','deep'),target=path.join(ancestor,suffix,'one.py');
 fs.mkdirSync(path.join(foreign,suffix),{recursive:true});fs.writeFileSync(path.join(foreign,'sentinel'),'preserve');
 fs.writeFileSync(path.join(foreign,suffix,'one.py'),'foreign one');
 fs.writeFileSync(path.join(foreign,suffix,'two.py'),'foreign two');
 const replaced=beforeFirstOpen(t,path.dirname(target),()=>{
  fs.renameSync(ancestor,path.join(f.root,'saved-ancestor'));fs.symlinkSync(foreign,ancestor,'junction');
 });
 await assert.rejects(archive.extract(f.zip,f.destination,f.options),/linked|redirected|changed|EEXIST/);
 assert.equal(replaced(),true);assert.equal(fs.readFileSync(path.join(foreign,'sentinel'),'utf8'),'preserve');
 assert.equal(fs.readFileSync(path.join(foreign,suffix,'one.py'),'utf8'),'foreign one');
 assert.equal(fs.readFileSync(path.join(foreign,suffix,'two.py'),'utf8'),'foreign two');
});

test('directory verification rejects a same-byte parent substitution before its files open',async t=>{
 const f=fixture(t),inventory=await archive.extract(f.zip,f.destination,f.options),directory=path.join(f.destination,nested),first=path.join(directory,'one.py');
 const replaced=beforeFirstOpen(t,directory,()=>{
  const saved=path.join(f.root,'saved-verified-parent');fs.renameSync(directory,saved);fs.cpSync(saved,directory,{recursive:true});
 });
 await assert.rejects(archive.verifyDirectory(f.destination,{...f.options,inventory}),/changed|replaced|ownership/);
 assert.equal(replaced(),true);
});

test('failed extraction drains held writers before any staging cleanup',async t=>{
 const f=fixture(t),originalOpen=fs.promises.open,originalUnlink=fs.promises.unlink,originalRmdir=fs.promises.rmdir;
 let releaseClose,signalHeld,signalFailure,active=0,maxActive=0,cleaned=false,settled=false;
 const closeGate=new Promise(resolve=>{releaseClose=resolve;}),held=new Promise(resolve=>{signalHeld=resolve;}),failed=new Promise(resolve=>{signalFailure=resolve;});
 t.mock.method(fs.promises,'open',async(file,flags,...args)=>{
  const writing=typeof flags==='number'&&Boolean(flags&fs.constants.O_WRONLY);
  if(writing&&String(file)===path.join(f.destination,'resources','app.asar')){await held;signalFailure();throw new Error('forced sibling write failure');}
  const handle=await originalOpen(file,flags,...args);
  if(writing){
   active++;maxActive=Math.max(maxActive,active);const close=handle.close.bind(handle);
   if(String(file)===path.join(f.destination,'Melange.exe'))signalHeld();
   handle.close=async()=>{if(String(file)===path.join(f.destination,'Melange.exe'))await closeGate;try{await close();}finally{active--;}};
  }
  return handle;
 });
 for(const [name,original]of [['unlink',originalUnlink],['rmdir',originalRmdir]])t.mock.method(fs.promises,name,async(...args)=>{assert.equal(active,0,'cleanup cannot race an output handle');cleaned=true;return original(...args);});
 const pending=archive.extract(f.zip,f.destination,f.options).then(()=>{settled=true;return null;},error=>{settled=true;return error;});
 let timeout;
 try{
  await Promise.race([failed,new Promise((_resolve,reject)=>{timeout=setTimeout(()=>reject(new Error('parallel sibling never ran')),5000);})]);
  await new Promise(resolve=>setTimeout(resolve,30));assert.equal(settled,false);assert.equal(cleaned,false);
 }finally{clearTimeout(timeout);releaseClose();}
 const error=await pending;assert.match(error?.message||'',/forced sibling write failure/);
 assert.equal(active,0);assert.ok(maxActive>0&&maxActive<=4);assert.equal(cleaned,true);assert.equal(fs.existsSync(f.destination),false);
});

test('parallel verification rejects an extra file added after enumeration',async t=>{
 const f=fixture(t),inventory=await archive.extract(f.zip,f.destination,f.options),original=fs.promises.open;
 let added=false;
 t.mock.method(fs.promises,'open',async(...args)=>{
  const handle=await original(...args);
  if(!added){
   const close=handle.close.bind(handle);
   handle.close=async()=>{await close();if(!added){added=true;fs.writeFileSync(path.join(f.destination,'unexpected.txt'),'preserve');}};
  }
  return handle;
 });
 await assert.rejects(archive.verifyDirectory(f.destination,{...f.options,inventory}),/unexpected installed file/);
 assert.equal(added,true);assert.equal(fs.readFileSync(path.join(f.destination,'unexpected.txt'),'utf8'),'preserve');
});

test('failed verification drains held readers before rejecting',async t=>{
 const f=fixture(t),inventory=await archive.extract(f.zip,f.destination,f.options),original=fs.promises.open;
 let releaseClose,signalHeld,signalFailure,active=0,maxActive=0,settled=false;
 const closeGate=new Promise(resolve=>{releaseClose=resolve;}),held=new Promise(resolve=>{signalHeld=resolve;}),failed=new Promise(resolve=>{signalFailure=resolve;});
 t.mock.method(fs.promises,'open',async(file,...args)=>{
  if(String(file)===path.join(f.destination,'resources','app.asar')){await held;signalFailure();throw new Error('forced sibling read failure');}
  const handle=await original(file,...args);active++;maxActive=Math.max(maxActive,active);const close=handle.close.bind(handle);let countedClosed=false;
  if(String(file)===path.join(f.destination,'Melange.exe'))signalHeld();
  handle.close=async()=>{if(String(file)===path.join(f.destination,'Melange.exe'))await closeGate;try{await close();}finally{if(!countedClosed){countedClosed=true;active--;}}};
  return handle;
 });
 const pending=archive.verifyDirectory(f.destination,{...f.options,inventory}).then(()=>{settled=true;return null;},error=>{settled=true;return error;});
 let timeout;
 try{
  await Promise.race([failed,new Promise((_resolve,reject)=>{timeout=setTimeout(()=>reject(new Error('parallel sibling never ran')),5000);})]);
  await new Promise(resolve=>setTimeout(resolve,30));assert.equal(settled,false);
 }finally{clearTimeout(timeout);releaseClose();}
 const error=await pending;assert.match(error?.message||'',/forced sibling read failure/);
 assert.equal(active,0);assert.ok(maxActive>0&&maxActive<=4);assert.equal(fs.existsSync(f.destination),true);
});
