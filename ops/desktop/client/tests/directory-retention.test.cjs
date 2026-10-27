'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os'),crypto=require('node:crypto');
const publisher=require('./fixtures/directory-package-fixture.cjs').signingFixture();
require('../publisher-trust.cjs').THUMBPRINT=publisher.thumbprint;
const {publisherProofPayload,FORMAT}=require('../directory-package-proof.cjs');
const {DirectoryRetention,removeVerifiedTree}=require('../directory-retention.cjs');
const archive=require('../directory-package.cjs');
const sha256=value=>crypto.createHash('sha256').update(value).digest('hex');
function crc32(bytes){let crc=0xffffffff;for(const byte of bytes){crc^=byte;for(let bit=0;bit<8;bit++)crc=(crc>>>1)^((crc&1)?0xedb88320:0);}return (crc^0xffffffff)>>>0;}
function zip(members){
 const output=[],directory=[];let offset=0;
 for(const [filename,value]of members){const name=Buffer.from(filename),data=Buffer.from(value),crc=crc32(data),local=Buffer.alloc(30),central=Buffer.alloc(46);
  local.writeUInt32LE(0x04034b50);local.writeUInt16LE(20,4);local.writeUInt32LE(crc,14);local.writeUInt32LE(data.length,18);local.writeUInt32LE(data.length,22);local.writeUInt16LE(name.length,26);
  central.writeUInt32LE(0x02014b50);central.writeUInt16LE(20,6);central.writeUInt32LE(crc,16);central.writeUInt32LE(data.length,20);central.writeUInt32LE(data.length,24);central.writeUInt16LE(name.length,28);central.writeUInt32LE(offset,42);
  output.push(local,name,data);directory.push(central,name);offset+=local.length+name.length+data.length;
 }
 const central=Buffer.concat(directory),end=Buffer.alloc(22);end.writeUInt32LE(0x06054b50);end.writeUInt16LE(members.length,8);end.writeUInt16LE(members.length,10);end.writeUInt32LE(central.length,12);end.writeUInt32LE(offset,16);
 return Buffer.concat([...output,central,end]);
}
function fixture(t){
 const base=fs.realpathSync.native(fs.mkdtempSync(path.join(os.tmpdir(),'directory-retention-'))),root=path.join(base,'programs'),profile=path.join(base,'profile');fs.mkdirSync(root);fs.mkdirSync(profile);
 t.after(()=>fs.rmSync(base,{recursive:true,force:true,maxRetries:5}));
 const recordFile=path.join(profile,'owned.json'),retention=new DirectoryRetention({root,appId:'melange',recordFile});
 async function create(version,{owned=true,appId='melange'}={}){
  const product={melange:'Melange',mentat:'Mentat'}[appId],entrypoint=product+'.exe',identity={appId,version,entrypoint};
  const members=[[entrypoint,'MZ inert test program'],['resources/app.asar','inert application archive'],['resources/runtime/file.bin','runtime bytes']];
  const inventory={schemaVersion:1,...identity,files:members.map(([name,bytes])=>({path:name,size:Buffer.byteLength(bytes),sha256:sha256(bytes)}))};
  const bytes=zip([['directory-package.json',JSON.stringify(inventory)],...members]);
  const manifest={appId,version,platform:'win32',arch:'x64',issuedAt:new Date().toISOString(),publisherThumbprints:[publisher.thumbprint],
   package:{format:FORMAT,entrypoint,name:appId+'-'+version+'-win32-x64.zip',size:bytes.length,sha256:sha256(bytes),sha512:crypto.createHash('sha512').update(bytes).digest('base64')}};
  manifest.package.publisherProof={schemaVersion:1,algorithm:'rsa-sha256',certificateDer:publisher.certificate.toString('base64'),signature:publisher.sign(publisherProofPayload(manifest)).toString('base64')};
  const filename=path.join(profile,manifest.package.name),directory=path.join(root,product+'-'+version);fs.writeFileSync(filename,bytes);await archive.extract(filename,directory,{...identity,archive:manifest.package});
  if(owned)await retention.recordCreated(manifest,directory);
  return {manifest,filename,directory,executable:path.join(directory,entrypoint)};
 }
 return {base,root,recordFile,retention,create};
}
test('retention removes only updater-owned obsolete program while keeping bootstrap,current,previous',async t=>{
 const f=fixture(t),bootstrap=await f.create('1.0.20',{owned:false}),old=await f.create('1.0.21'),previous=await f.create('1.0.22'),current=await f.create('1.0.23');
 fs.writeFileSync(path.join(f.root,'user-notes.txt'),'preserve');
 const result=await f.retention.prune({candidates:[bootstrap,old,previous,current],keepVersions:['1.0.22','1.0.23'],currentExecutable:current.executable});
 assert.deepEqual(result.removed,['1.0.21']);assert.equal(fs.existsSync(old.directory),false);
 for(const item of [bootstrap,previous,current])assert.ok(fs.existsSync(item.executable));
 assert.equal(fs.readFileSync(path.join(f.root,'user-notes.txt'),'utf8'),'preserve');
 assert.equal(JSON.parse(fs.readFileSync(f.recordFile)).created['1.0.21'],undefined);
});
test('actual running executable remains protected after rollback even when caller omits its version',async t=>{
 const f=fixture(t),current=await f.create('1.0.21');
 assert.deepEqual((await f.retention.prune({candidates:[current],keepVersions:['1.0.23'],currentExecutable:current.executable})).removed,[]);assert.ok(fs.existsSync(current.executable));
});
for(const mutation of ['extra-file','extra-directory','changed-program','changed-inventory','hardlink'])test('preserves entire old program when it contains '+mutation,async t=>{
 const f=fixture(t),old=await f.create('1.0.21');
 if(mutation==='extra-file')fs.writeFileSync(path.join(old.directory,'personal.txt'),'user file');
 if(mutation==='extra-directory')fs.mkdirSync(path.join(old.directory,'personal'));
 if(mutation==='changed-program')fs.writeFileSync(old.executable,'modified');
 if(mutation==='changed-inventory')fs.writeFileSync(path.join(old.directory,'directory-package.json'),'{}');
 if(mutation==='hardlink')fs.linkSync(old.executable,path.join(f.base,'other-link'));
 assert.deepEqual((await f.retention.prune({candidates:[old]})).removed,[]);assert.ok(fs.existsSync(old.executable));assert.ok(fs.existsSync(path.join(old.directory,'resources/app.asar')));
});
test('directory replacement and linked parent cannot inherit old physical ownership',async t=>{
 const f=fixture(t),old=await f.create('1.0.21'),moved=old.directory+'-original';fs.renameSync(old.directory,moved);fs.symlinkSync(moved,old.directory,'junction');
 assert.deepEqual((await f.retention.prune({candidates:[old]})).removed,[]);assert.ok(fs.existsSync(path.join(moved,'Melange.exe')));
});
test('same contents in a different physical program directory are preserved',async t=>{
 const f=fixture(t),old=await f.create('1.0.21');fs.renameSync(old.directory,old.directory+'-original');fs.cpSync(old.directory+'-original',old.directory,{recursive:true});
 assert.deepEqual((await f.retention.prune({candidates:[old]})).removed,[]);assert.ok(fs.existsSync(old.executable));
});
test('creation registration refuses a replacement after caller verified ownership',async t=>{
 const f=fixture(t),old=await f.create('1.0.21',{owned:false}),ownership=fs.lstatSync(old.directory,{bigint:true});
 fs.renameSync(old.directory,old.directory+'-original');fs.cpSync(old.directory+'-original',old.directory,{recursive:true});
 await assert.rejects(f.retention.recordCreated(old.manifest,old.directory,ownership),/ownership changed/);
 assert.equal(fs.existsSync(f.recordFile),false);
});
test('publisher proof and retained ZIP are required, regardless of local ownership record',async t=>{
 const f=fixture(t),old=await f.create('1.0.21');const changed=structuredClone(old.manifest);changed.package.sha256='a'.repeat(64);
 assert.deepEqual((await f.retention.prune({candidates:[{...old,manifest:changed}]})).removed,[]);
 fs.appendFileSync(old.filename,'tampered');assert.deepEqual((await f.retention.prune({candidates:[old]})).removed,[]);assert.ok(fs.existsSync(old.executable));
});
test('foreign app and altered ownership root cannot authorize removal',async t=>{
 const f=fixture(t),old=await f.create('1.0.21'),other=await f.create('1.0.21',{owned:false,appId:'mentat'});
 assert.deepEqual((await f.retention.prune({candidates:[other]})).removed,[]);assert.ok(fs.existsSync(other.executable));
 const record=JSON.parse(fs.readFileSync(f.recordFile));record.root=f.base;fs.writeFileSync(f.recordFile,JSON.stringify(record));
 assert.deepEqual((await f.retention.prune({candidates:[old]})).removed,[]);assert.ok(fs.existsSync(old.executable));
});
test('file appearing during verification prevents every deletion',async t=>{
 const f=fixture(t),old=await f.create('1.0.21');
 const raced=new DirectoryRetention({root:f.root,appId:'melange',recordFile:f.recordFile,archive:{...archive,verifyDirectory:async(...args)=>{await archive.verifyDirectory(...args);fs.writeFileSync(path.join(old.directory,'personal.txt'),'preserve');}}});
 assert.deepEqual((await raced.prune({candidates:[old]})).removed,[]);assert.ok(fs.existsSync(old.executable));assert.equal(fs.readFileSync(path.join(old.directory,'personal.txt'),'utf8'),'preserve');
});
test('inventory-bounded cleanup with async ownership guard preserves a late extra file',async t=>{
 const f=fixture(t),old=await f.create('1.0.21'),options={appId:'melange',version:'1.0.21',entrypoint:'Melange.exe',archive:old.manifest.package};
 const inventory=await archive.inspect(old.filename,options),ownership=fs.lstatSync(old.directory,{bigint:true});let verified=false;
 const raced={...archive,verifyDirectory:async(...args)=>{await archive.verifyDirectory(...args);verified=true;}};
 const guard=async()=>{const current=fs.lstatSync(old.directory,{bigint:true});assert.equal(current.ino,ownership.ino);if(verified)fs.writeFileSync(path.join(old.directory,'new-user-file.txt'),'preserve');};
 await assert.rejects(removeVerifiedTree(old.directory,inventory,{archive:raced,options,guard}),/unexpected program file/);
 assert.ok(fs.existsSync(old.executable));assert.equal(fs.readFileSync(path.join(old.directory,'new-user-file.txt'),'utf8'),'preserve');
});
