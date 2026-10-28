'use strict';
// Local installation authority is deliberately not an administrator grant. It
// must never be sent to a private server, or used as a bearer credential.
const crypto=require('node:crypto');
const {promisify}=require('node:util');
const {OPTIONS,checkedRecord:checkedLegacyPassword}=require('./local-access.cjs');
const scrypt=promisify(crypto.scrypt);
const NAMES={melange:'Melange',mentat:'Mentat',terrier:'Terrier'};
const DISTRICTS=Object.freeze(['co-05','ct-01','or-05']);
const ID_FIELDS=['schemaVersion','appId','deviceId','accountId','accountIdentity'];
const PASSWORD_FIELDS=['algorithm','N','r','p','salt','derivedKey','failures','blockedUntil','lastAttempt'];
const UUID=/^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/;
const SID=/^S-1-(?:\d{1,15}-){1,15}\d{1,15}$/;
function uuid(value){return typeof value==='string'&&UUID.test(value)&&value!=='00000000-0000-0000-0000-000000000000';}
function exact(value,fields){return Boolean(value&&typeof value==='object'&&!Array.isArray(value)&&Object.keys(value).sort().join('|')===[...fields].sort().join('|'));}
function validIdentity(value){
 if(!exact(value,ID_FIELDS)||value.schemaVersion!==1||!Object.hasOwn(NAMES,value.appId)||!uuid(value.deviceId)||!uuid(value.accountId)||typeof value.accountIdentity!=='string'||!/^[A-Za-z0-9_@.+-]{1,150}$/.test(value.accountIdentity))throw new Error('Invalid protected local account');
 return value;
}
function sameIdentity(a,b){return Boolean(a&&b&&ID_FIELDS.every(key=>a[key]===b[key]));}
function checkedWindowsIdentity(value){
 if(!exact(value,['schemaVersion','userSid','accountName','sessionId','locked'])||value.schemaVersion!==1||typeof value.userSid!=='string'||value.userSid.length>184||!SID.test(value.userSid)||typeof value.accountName!=='string'||!value.accountName.trim()||value.accountName.length>256||/[\x00-\x1f\x7f]/.test(value.accountName)||!Number.isSafeInteger(value.sessionId)||value.sessionId<0||value.sessionId>0xffffffff||typeof value.locked!=='boolean'||(!value.locked&&value.sessionId===0))throw new Error('Windows sign-in could not be verified');
 return Object.freeze(clone(value));
}
function checkedWindowsBinding(record,identity,userSid){
 if(!exact(record,['schemaVersion','purpose','identity','userSid'])||record.schemaVersion!==1||record.purpose!=='desktop-windows-account'||!sameIdentity(validIdentity(record.identity),identity)||record.userSid!==userSid)throw new Error('Protected app account belongs to another Windows user');
 return record;
}
function clone(value){return structuredClone(value);}
function bytes(value,length){if(typeof value!=='string')throw new Error('Invalid protected local password');const result=Buffer.from(value,'base64');if(result.length!==length||result.toString('base64')!==value)throw new Error('Invalid protected local password');return result;}
function passwordBytes(value){if(typeof value!=='string'||Array.from(value).length<12||Buffer.byteLength(value)>1024||value.includes('\0'))throw new Error('Use a password of at least 12 characters and at most 1024 UTF-8 bytes.');return Buffer.from(value,'utf8');}
function checkedPassword(record,identity){
 if(!exact(record,['schemaVersion','purpose','identity',...PASSWORD_FIELDS])||record.schemaVersion!==1||record.purpose!=='desktop-local-password'||!sameIdentity(validIdentity(record.identity),identity)||record.algorithm!=='scrypt'||record.N!==OPTIONS.N||record.r!==OPTIONS.r||record.p!==OPTIONS.p)throw new Error('Invalid protected local password');
 bytes(record.salt,32).fill(0);bytes(record.derivedKey,64).fill(0);
 if(!Number.isSafeInteger(record.failures)||record.failures<0||record.failures>1000000||!Number.isSafeInteger(record.blockedUntil)||record.blockedUntil<0||!Number.isSafeInteger(record.lastAttempt)||record.lastAttempt<0)throw new Error('Invalid protected local password');
 return record;
}
function checkedDevice(record,identity){
 if(!exact(record,['schemaVersion','purpose','identity','verifiedAt'])||record.schemaVersion!==1||record.purpose!=='desktop-local-device'||!sameIdentity(validIdentity(record.identity),identity)||!Number.isSafeInteger(record.verifiedAt)||record.verifiedAt<0)throw new Error('Invalid protected local device');
 return record;
}
function legacyDevice(record,grant){
 if(!record)return false;
 const fields=['serverId','deviceId','principalId','accountIdentity','appId','grantId'];
 if(!exact(record,['schemaVersion','binding','verifiedAt'])||record.schemaVersion!==1||!exact(record.binding,fields)||fields.some(key=>record.binding[key]!==grant[key])||!Number.isSafeInteger(record.verifiedAt)||record.verifiedAt<0)throw new Error('Legacy device verification belongs to another account');
 return true;
}
function payloadPassword(value){if(!exact(value,['password']))throw new Error('Invalid local sign-in action');return value.password;}
function deviceRecord(identity,now){return {schemaVersion:1,purpose:'desktop-local-device',identity:clone(identity),verifiedAt:now};}

class StandaloneAccessGate{
 constructor({identity,passwords,devices,configuration,now=Date.now}){
  this.identity=Object.freeze(clone(validIdentity(identity)));this.appId=identity.appId;this.passwords=passwords;this.devices=devices;this.configuration=configuration;this.now=now;this.session=null;this.busy=false;this.epoch=0;this.forgetting=0;
  this.local={lock:()=>this.lock(),forget:()=>this.forget(),resume:()=>this.resume()};
 }
 lock(){this.epoch++;this.session=null;}
 async forget(){this.lock();this.forgetting++;try{await this.devices.delete(this.identity);}finally{this.forgetting--;}}
 async resume(){
  if(this.appId==='terrier'||this.forgetting)return null;
  if(this.session)return this.session;
  const epoch=this.epoch;let record;
  try{record=await this.devices.read(this.identity);if(!record)return null;checkedDevice(record,this.identity);}catch{return null;}
  if(epoch!==this.epoch||this.forgetting)return null;
  return this.session=Object.freeze({...this.identity,sessionId:crypto.randomUUID(),authenticatedAt:this.now(),method:'device-trust'});
 }
 async info(){
  const base={appId:this.appId,appName:NAMES[this.appId],accountIdentity:this.identity.accountIdentity,accessMode:'standalone',authentication:'local-password'};
  if(this.appId==='terrier')return {...base,phase:'terrier_signin'};
  if(await this.resume())return {...base,phase:'ready'};
  const record=await this.passwords.read(this.identity);if(record)checkedPassword(record,this.identity);
  return {...base,phase:record?'locked':'needs_password'};
 }
 async action(method,payload){
  if(this.busy)throw new Error('Local sign-in is already in progress');this.busy=true;
  try{
   if(method==='lock'){if(payload!==undefined)throw new Error('Invalid local sign-in action');await this.forget();return this.info();}
   if(this.appId==='terrier'||!['setPassword','unlock'].includes(method))throw new Error('Unsupported local sign-in action');
   const password=payloadPassword(payload),raw=passwordBytes(password);raw.fill(0);
   const state=await this.info(),epoch=this.epoch;
   if(method==='setPassword'){
    if(state.phase!=='needs_password')throw new Error('A local password already exists; sign in to that account');
    const salt=crypto.randomBytes(32);let key;
    try{const input=passwordBytes(password);try{key=await scrypt(input,salt,64,OPTIONS);}finally{input.fill(0);}
     await this.passwords.write(this.identity,{schemaVersion:1,purpose:'desktop-local-password',identity:clone(this.identity),algorithm:'scrypt',N:OPTIONS.N,r:OPTIONS.r,p:OPTIONS.p,salt:salt.toString('base64'),derivedKey:key.toString('base64'),failures:0,blockedUntil:0,lastAttempt:0});
    }finally{salt.fill(0);key?.fill(0);}
   }else{
    if(state.phase!=='locked')throw new Error('Local password sign-in is unavailable');
    this.session=null;const record=checkedPassword(await this.passwords.read(this.identity),this.identity),now=this.now();
    if(!Number.isSafeInteger(now)||now<record.lastAttempt-60000)throw new Error('Local clock changed; password check refused');
    if(now<record.blockedUntil)throw new Error('Too many attempts. Try again later.');
    const failures=Math.min(record.failures+1,1000000),delay=failures<5?0:Math.min(900000,5000*2**Math.min(failures-5,8));
    await this.passwords.write(this.identity,{...record,failures,blockedUntil:now+delay,lastAttempt:now});
    const expected=bytes(record.derivedKey,64),salt=bytes(record.salt,32),input=passwordBytes(password);let key;
    try{key=await scrypt(input,salt,64,OPTIONS);if(!crypto.timingSafeEqual(key,expected))throw new Error('Incorrect password');}finally{expected.fill(0);salt.fill(0);input.fill(0);key?.fill(0);}
    await this.passwords.write(this.identity,{...record,failures:0,blockedUntil:0,lastAttempt:now});
    if(epoch!==this.epoch)throw new Error('Local sign-in was interrupted');
    this.session=Object.freeze({...this.identity,sessionId:crypto.randomUUID(),authenticatedAt:now,method:'local-password'});
    let remembered=false;try{await this.devices.write(this.identity,deviceRecord(this.identity,now));remembered=true;}catch{/* This sign-in works; next launch asks again if remembering failed. */}
    if(epoch!==this.epoch){this.session=null;if(remembered)try{await this.devices.delete(this.identity);}catch{/* The workspace remains locked for this interrupted action. */}throw new Error('Local sign-in was interrupted');}
   }
   return this.info();
  }finally{this.busy=false;}
 }
 async authorize(configuration=this.configuration()){
  const session=await this.resume();if(this.appId!=='terrier'&&!session)throw new Error('Local sign-in required');
  let principal=null;
  if(this.appId==='terrier'){if(!DISTRICTS.includes(configuration?.district))throw new Error('Choose a supported local district');principal=Object.freeze({mode:'standalone',districtId:configuration.district});}
  return Object.freeze({mode:'standalone',identity:this.identity,session,principal});
 }
 async evidence(){return null;}
 async refresh(){return this.info();}
 districts(){return this.appId==='terrier'?[...DISTRICTS]:[];}
}

class WindowsStandaloneAccessGate extends StandaloneAccessGate{
 constructor({windowsSessionProvider,windowsStore,...options}){
  super(options);this.windowsSessionProvider=windowsSessionProvider;this.windowsStore=windowsStore;this.windowsIdentity=null;this.suspended=false;this.pendingWindows=null;
  this.local={lock:()=>this.lock(),forget:()=>this.forget(),resume:()=>this.resume(true)};
 }
 lock(){super.lock();this.suspended=true;}
 async forget(){this.lock();}
 async resume(afterWindowsUnlock=false){
  // A trusted OS-resume notification always starts a new native observation,
  // even if a preceding lock notification was missed or is still in flight.
  if(afterWindowsUnlock){this.epoch++;this.session=null;}
  if(this.session&&!this.suspended)return this.session;
  if(this.suspended&&!afterWindowsUnlock)return null;
  const epoch=this.epoch;
  if(this.pendingWindows?.epoch===epoch)return this.pendingWindows.promise;
  const pending={epoch};
  pending.promise=(async()=>{
   try{
    const observed=checkedWindowsIdentity(await this.windowsSessionProvider());
    if(epoch!==this.epoch)return null;
    this.windowsIdentity=observed;
    if(observed.locked){this.suspended=true;return null;}
    const binding=await this.windowsStore.read();
    if(epoch!==this.epoch)return null;
    if(binding)checkedWindowsBinding(binding,this.identity,observed.userSid);
    else await this.windowsStore.write({schemaVersion:1,purpose:'desktop-windows-account',identity:clone(this.identity),userSid:observed.userSid});
    if(epoch!==this.epoch)return null;
    const now=this.now();if(!Number.isSafeInteger(now)||now<0)throw new Error('Windows sign-in could not be verified');
    this.suspended=false;
    return this.session=Object.freeze({...this.identity,sessionId:crypto.randomUUID(),authenticatedAt:now,method:'windows-session'});
   }finally{if(this.pendingWindows===pending)this.pendingWindows=null;}
  })();
  this.pendingWindows=pending;return pending.promise;
 }
 async info(){
  const epoch=this.epoch;let session,unavailable=false;
  try{session=await this.resume();}catch{if(epoch===this.epoch){this.session=null;unavailable=true;}else session=this.session;}
  return {appId:this.appId,appName:NAMES[this.appId],accountIdentity:this.identity.accountIdentity,accessMode:'standalone',authentication:'windows',...(this.windowsIdentity?{windowsAccountDisplayName:this.windowsIdentity.accountName}:{}),phase:unavailable?'windows_unavailable':session?'ready':'windows_locked'};
 }
 async action(method,payload){
  if(method!=='lock'||payload!==undefined)throw new Error('Windows sign-in does not accept app passwords or account input');
  await this.forget();return this.info();
 }
 async authorize(configuration=this.configuration()){
  const session=await this.resume();if(!session)throw new Error('Unlock Windows to open this application');
  let principal=null;
  if(this.appId==='terrier'){if(!DISTRICTS.includes(configuration?.district))throw new Error('Choose a supported local district');principal=Object.freeze({mode:'standalone',districtId:configuration.district});}
  return Object.freeze({mode:'standalone',identity:this.identity,session,principal});
 }
}

// legacy is supplied only after the native caller verifies the old grant/owner
// attestation. Old protected records are never overwritten or deleted here.
async function createStandaloneGate({appId,identity,accountStore,passwords,devices,configuration=()=>({}),legacy=null,now=Date.now,authentication='password',windowsSessionProvider,windowsStore}){
 if(!Object.hasOwn(NAMES,appId)||!uuid(identity?.deviceId)||(identity.appId!==undefined&&identity.appId!==appId)||!accountStore?.read||!accountStore?.write||!passwords?.read||!passwords?.write||!devices?.read||!devices?.write||!devices?.delete||typeof configuration!=='function')throw new Error('Protected local account stores are required');
 if(!['password','windows'].includes(authentication)||authentication==='windows'&&(typeof windowsSessionProvider!=='function'||!windowsStore?.read||!windowsStore?.write))throw new Error('Protected Windows sign-in is required');
 let account=await accountStore.read();
 if(account){
  if(!exact(account,['schemaVersion','purpose','identity'])||account.schemaVersion!==1||account.purpose!=='desktop-local-account')throw new Error('Invalid protected local account');
  validIdentity(account.identity);if(account.identity.appId!==appId||account.identity.deviceId!==identity.deviceId)throw new Error('Protected local account belongs to another installation');
 }else{
  const grant=legacy?.grant;
  if(legacy&&(!grant||grant.appId!==appId||grant.deviceId!==identity.deviceId||!uuid(grant.principalId)||typeof grant.accountIdentity!=='string'))throw new Error('Legacy account belongs to another installation');
  const localIdentity=validIdentity({schemaVersion:1,appId,deviceId:identity.deviceId,accountId:grant?.principalId||identity.deviceId,accountIdentity:grant?.accountIdentity||'local_'+identity.deviceId.replaceAll('-','')});
  const oldPassword=legacy?.passwordRecord;
  if(oldPassword){checkedLegacyPassword(oldPassword,grant);const migrated={schemaVersion:1,purpose:'desktop-local-password',identity:clone(localIdentity),...Object.fromEntries(PASSWORD_FIELDS.map(key=>[key,oldPassword[key]]))};const prior=await passwords.read(localIdentity);if(prior)checkedPassword(prior,localIdentity);else await passwords.write(localIdentity,migrated);}
  const verifiedDevice=legacyDevice(legacy?.deviceRecord,grant);
  if(appId!=='terrier'&&(verifiedDevice||legacy?.ownerVerified===true)){const prior=await devices.read(localIdentity);if(prior)checkedDevice(prior,localIdentity);else await devices.write(localIdentity,deviceRecord(localIdentity,now()));}
  account={schemaVersion:1,purpose:'desktop-local-account',identity:clone(localIdentity)};await accountStore.write(account);
 }
 const options={identity:account.identity,passwords,devices,configuration,now};
 return authentication==='windows'?new WindowsStandaloneAccessGate({...options,windowsSessionProvider,windowsStore}):new StandaloneAccessGate(options);
}
module.exports={createStandaloneGate,StandaloneAccessGate,WindowsStandaloneAccessGate,validIdentity,checkedPassword,checkedDevice,checkedWindowsIdentity,DISTRICTS};
