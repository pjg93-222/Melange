'use strict';
const fs=require('node:fs');
const path=require('node:path');
const crypto=require('node:crypto');
const KINDS=new Set(['account','password','device','windows']);
// These files are separate from the previous administrator grants and Windows
// Credential Manager records, so upgrading does not destroy rollback data.
function protectedLocalStores({profile,appId,deviceId,safeStorage,platform=process.platform}){
 if(platform!=='win32'||!['melange','mentat','terrier'].includes(appId)||!/^\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/.test(deviceId)||!path.isAbsolute(profile))throw new Error('Invalid local account storage');
 const root=path.resolve(profile),binding=root.toLowerCase();
 const available=()=>{if(!safeStorage?.isEncryptionAvailable())throw new Error('Windows credential protection is unavailable');};
 const directory=()=>{fs.mkdirSync(root,{recursive:true,mode:0o700});if(fs.lstatSync(root).isSymbolicLink())throw new Error('Local account storage cannot be a link');};
 const location=kind=>{if(!KINDS.has(kind))throw new Error('Invalid local account scope');return path.join(root,'standalone-'+kind+'.enc');};
 const checkedFile=target=>{try{const st=fs.lstatSync(target);if(st.isSymbolicLink()||!st.isFile()||st.size>65536)throw new Error('Invalid protected local account file');return true;}catch(error){if(error.code==='ENOENT')return false;throw error;}};
 function store(kind){const target=location(kind);return {
  async read(){
   available();directory();if(!checkedFile(target))return null;
   const value=JSON.parse(safeStorage.decryptString(fs.readFileSync(target)));
   if(!value||Object.keys(value).sort().join('|')!=='appId|deviceId|kind|profile|purpose|schemaVersion|value'||value.schemaVersion!==1||value.purpose!=='desktop-local-protected'||value.appId!==appId||value.deviceId!==deviceId||value.kind!==kind||value.profile!==binding)throw new Error('Local account storage belongs to another installation');
   return value.value;
  },
  async write(first,second){
   const value=second===undefined?first:second;
   available();directory();checkedFile(target);
   const serialized=JSON.stringify({schemaVersion:1,purpose:'desktop-local-protected',appId,deviceId,kind,profile:binding,value});
   if(Buffer.byteLength(serialized)>32768)throw new Error('Protected local account is too large');
   const temporary=target+'.'+crypto.randomUUID()+'.tmp';let fd;
   try{fd=fs.openSync(temporary,'wx',0o600);fs.writeFileSync(fd,safeStorage.encryptString(serialized));fs.fsyncSync(fd);fs.closeSync(fd);fd=undefined;checkedFile(target);fs.renameSync(temporary,target);}
   finally{if(fd!==undefined)fs.closeSync(fd);try{fs.unlinkSync(temporary);}catch(error){if(error.code!=='ENOENT')throw error;}}
  },
  async delete(){available();directory();if(checkedFile(target))fs.unlinkSync(target);}
 };}
 return {accountStore:store('account'),passwords:store('password'),devices:store('device'),windowsStore:store('windows')};
}
module.exports={protectedLocalStores};
