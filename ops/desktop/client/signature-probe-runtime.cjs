'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {backendCommand}=require('./backend-command.cjs');
const inventory=require('./module-application-inventory.cjs');
const roster=require('./signature-probe-runtime.json');
const fail=()=>{throw new Error('The bundled Windows signature verifier could not be authenticated.');};
const same=(a,b)=>['dev','ino','mode','nlink','size','mtimeNs','ctimeNs'].every(key=>a[key]===b[key]);
const samePath=(a,b)=>process.platform==='win32'?path.resolve(a).toLowerCase()===path.resolve(b).toLowerCase():path.resolve(a)===path.resolve(b);
function checkedFile(root,row){
 if(!row||Object.keys(row).sort().join(',')!=='bytes,path,sha256'||typeof row.path!=='string'||!row.path.split('/').every(p=>/^[A-Za-z0-9_][A-Za-z0-9_.-]*$/.test(p)&&!p.endsWith('.'))||!Number.isSafeInteger(row.bytes)||row.bytes<0||row.bytes>64*1024**2||!/^[a-f0-9]{64}$/.test(row.sha256))fail();
 let parent=root;
 for(const part of row.path.split('/').slice(0,-1)){parent=path.join(parent,part);const stat=fs.lstatSync(parent);if(!stat.isDirectory()||stat.isSymbolicLink()||!samePath(fs.realpathSync.native(parent),parent))fail();}
 const filename=path.join(root,...row.path.split('/')),before=fs.lstatSync(filename,{bigint:true});
 if(!before.isFile()||before.isSymbolicLink()||before.nlink!==1n||before.size!==BigInt(row.bytes)||!samePath(fs.realpathSync.native(filename),filename))fail();
 const fd=fs.openSync(filename,'r');
 try{
  if(!same(before,fs.fstatSync(fd,{bigint:true})))fail();
  const hash=crypto.createHash('sha256'),buffer=Buffer.alloc(1024*1024);let read,total=0;
  while((read=fs.readSync(fd,buffer,0,buffer.length,null))!==0){total+=read;if(total>row.bytes)fail();hash.update(buffer.subarray(0,read));}
  if(total!==row.bytes||hash.digest('hex')!==row.sha256||!same(before,fs.fstatSync(fd,{bigint:true}))||!same(before,fs.lstatSync(filename,{bigint:true})))fail();
 }finally{fs.closeSync(fd);}
}
function verifyProbeLayout(root,appId){
 if(!['melange','mentat','terrier'].includes(appId)||typeof root!=='string'||!path.isAbsolute(root))fail();
 const python=path.join(root,'python'),bootstrap=path.join(root,'bootstrap');
 for(const directory of [root,python,bootstrap]){const stat=fs.lstatSync(directory);if(!stat.isDirectory()||stat.isSymbolicLink()||!samePath(fs.realpathSync.native(directory),directory))fail();}
 const rows=roster.schemaVersion===1&&roster.applications?.[appId];if(!Array.isArray(rows)||!rows.length||rows.length>2000)fail();
 const expected=new Set(rows.map(row=>row.path));if(expected.size!==rows.length)fail();const directories=new Set();
 for(const row of rows){let parent=path.posix.dirname(row.path);while(parent!=='.'){directories.add(parent);parent=path.posix.dirname(parent);}}
 function walk(directory,prefix=''){
  for(const entry of fs.readdirSync(directory,{withFileTypes:true})){
   const relative=prefix+entry.name,filename=path.join(directory,entry.name),stat=fs.lstatSync(filename);
   if(stat.isSymbolicLink()||!samePath(fs.realpathSync.native(filename),filename))fail();
   if(stat.isDirectory()){if(relative!=='Lib/site-packages'){if(!directories.delete(relative))fail();walk(filename,relative+'/');}}
   else if(!stat.isFile()||!expected.delete(relative))fail();
  }
 }
 walk(python);if(expected.size||directories.size)fail();for(const row of rows)checkedFile(python,row);
 const spec=inventory.APPLICATION_SPECS?.[appId]||inventory.DISTRICT_PROGRAM_SPECS?.[appId];
 const matches=spec?.programFiles?.filter(row=>row.root==='bootstrap'&&row.path==='native_windows_signature.py');
 if(matches?.length!==1)fail();const {root:unused,...probe}=matches[0];checkedFile(bootstrap,probe);
 return {binary:path.join(python,'python.exe'),args:['-I','-S','-B','-u',path.join(bootstrap,'native_windows_signature.py')]};
}
function verifyProbeRuntime(resources,appId){
 if(typeof resources!=='string'||!path.isAbsolute(resources))fail();
 const command=backendCommand(resources,appId),root=path.join(resources,'runtime',appId);
 for(const directory of [resources,path.join(resources,'runtime')]){const stat=fs.lstatSync(directory);if(!stat.isDirectory()||stat.isSymbolicLink()||!samePath(fs.realpathSync.native(directory),directory))fail();}
 const verified=verifyProbeLayout(root,appId);if(command.binary!==verified.binary)fail();return verified;
}
module.exports={verifyProbeRuntime,verifyProbeLayout};
