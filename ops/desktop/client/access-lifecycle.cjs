'use strict';
const http=require('node:http');
function authorizationIdentity(value){
 if(value?.mode==='standalone'){
  const identity=require('./standalone-access.cjs').validIdentity(value.identity);
  const windows=value.session?.method==='windows-session';
  if(windows&&['schemaVersion','appId','deviceId','accountId','accountIdentity'].some(key=>value.session[key]!==identity[key]))throw new Error('Windows sign-in is required');
  if(identity.appId==='terrier'){
   if(value.principal?.mode!=='standalone'||!require('./standalone-access.cjs').DISTRICTS.includes(value.principal.districtId))throw new Error('Local district sign-in is required');
  }else if(value.principal!==null||!value.session||['schemaVersion','appId','deviceId','accountId','accountIdentity'].some(key=>value.session[key]!==identity[key])||!['local-password','device-trust','windows-session'].includes(value.session.method))throw new Error('Local sign-in is required');
  return JSON.stringify({mode:'standalone',authentication:windows?'windows':'password',identity,principal:value.principal});
 }
 const grant=value?.accepted?.grant;if(!grant||value.accepted.revoked)throw new Error('Current approval is required');
 return JSON.stringify({serverId:grant.serverId,deviceId:grant.deviceId,principalId:grant.principalId,
  accountIdentity:grant.accountIdentity,appId:grant.appId,role:grant.role,districtIds:grant.districtIds,
  owner:Boolean(value.owner),principal:value.principal||null});
}
async function terrierSession(runtime,partition,{logout=false,passwordLockDisabled=false}={}){
 if(runtime.definition.id!=='terrier'||!runtime.origin||!runtime.token||!runtime.authorization?.principal)return false;
 const origin=new URL(runtime.origin);
 if(origin.protocol!=='http:'||origin.hostname!=='127.0.0.1'||!origin.port||origin.pathname!=='/')return false;
 const cookies=await partition.cookies.get({url:runtime.origin});
 const cookie=cookies.map(item=>item.name+'='+item.value).join('; ');
 const request=(relative,method='GET',csrf)=>new Promise(resolve=>{
  const body=method==='POST'?'{}':undefined;
  const req=http.request(new URL(relative,origin),{method,headers:{'X-Desktop-Token':runtime.token,Cookie:cookie,Accept:'application/json',...(body?{'Content-Type':'application/json','Content-Length':2,'X-CSRFToken':csrf,Origin:runtime.origin}:{})},timeout:2000},response=>{
   let bytes=0;const chunks=[];response.on('data',part=>{bytes+=part.length;if(bytes>8192)response.destroy();else chunks.push(part);});response.on('error',()=>resolve(null));response.on('close',()=>resolve(null));response.on('end',()=>{try{resolve(response.statusCode===200?JSON.parse(Buffer.concat(chunks).toString('utf8')):null);}catch{resolve(null);}});
  });req.on('error',()=>resolve(null));req.on('timeout',()=>req.destroy());req.end(body);
 });
 const value=await request('/api/auth/session');
 const local=runtime.authorization.mode==='standalone'&&runtime.authorization.principal.mode==='standalone';
 const windows=local&&runtime.authorization.session?.method==='windows-session';
 const authenticated=Boolean(value?.authenticated===true&&value.administrator===true&&(!windows||value.authentication==='windows')&&(local?typeof value.username==='string'&&value.username.length>0:value.username===runtime.authorization.principal.localAccountIdentity));
 if(logout){if(!value||typeof value.csrf!=='string')return false;const result=await request('/api/auth/logout','POST',value.csrf);return result?.ok===true;}
 return authenticated&&(!passwordLockDisabled||value.password_lock_disabled===true);
}
class AccessLifecycle{
 constructor({runtime,gate,hide,showBoundary,presence=async()=>{},terrierAuthenticated=async()=>false,terrierLogout=async()=>false,terrierPasswordLockDisabled=async()=>false,onSuspend=async()=>{}}){Object.assign(this,{runtime,gate,hide,showBoundary,presence,terrierAuthenticated,terrierLogout,terrierPasswordLockDisabled,onSuspend});this.suspended=false;this.generation=0;this.sessionId=require('node:crypto').randomUUID();this.osLocked=false;this.requiresFreshPassword=false;}
 async authenticated(){
  if(this.suspended||!this.runtime.child||this.runtime.requestsAllowed===false)return false;
  try{const approved=await this.gate.authorize();if(authorizationIdentity(approved)!==authorizationIdentity(this.runtime.authorization))return false;
   return this.runtime.definition.id==='terrier'?await this.terrierAuthenticated():Boolean(approved.owner||approved.session);
  }catch{return false;}
 }
 async suspend(reason){
  // Stop new network activity first. Existing requests/compute and the DOM remain intact.
  const generation=++this.generation;this.runtime.requestsAllowed=false;this.suspended=true;this.gate.local?.lock();this.hide();
  // onSuspend cancels in-flight district switches synchronously; its backend stops never gate or skip the lock.
  const stopped=(async()=>this.onSuspend())().catch(()=>{});
  const windows=this.runtime.allowStandalone===true&&this.runtime.authentication==='windows';
  if(['locked','signed_out'].includes(reason)&&this.runtime.definition.id==='terrier'&&!windows){
   // Fail closed while the password-lock preference is read; the final value is set below.
   this.requiresFreshPassword=true;let passwordless=false;try{passwordless=await this.terrierPasswordLockDisabled();}catch{}
   this.requiresFreshPassword=!passwordless;if(!passwordless)await this.terrierLogout();
  }
  await stopped;
  try{await this.presence(reason==='signed_out'?'signed_out':'locked',this.sessionId);}catch{}
  if(generation===this.generation&&this.suspended)await this.showBoundary();
 }
 async resume(approved,{freshPassword=false,expectedGeneration=this.generation}={}){
  if(this.osLocked)throw new Error('Unlock Windows before opening the workspace');
  if(expectedGeneration!==this.generation)throw new Error('Access changed while sign-in was pending');
  if(this.requiresFreshPassword&&!freshPassword)throw new Error('Fresh Terrier password authentication required');
  if(this.runtime.child&&this.runtime.authorization&&authorizationIdentity(approved)!==authorizationIdentity(this.runtime.authorization))throw new Error('Close the workspace before changing its approved account');
  this.runtime.requestsAllowed=true;this.suspended=false;this.requiresFreshPassword=false;
 }
 async resumeWindows({expectedGeneration=this.generation}={}){
  const current=()=>this.runtime.allowStandalone===true&&this.runtime.authentication==='windows'&&!this.osLocked&&expectedGeneration===this.generation;
  if(!current())throw new Error('Unlock Windows before opening the workspace');
  await this.gate.local.resume();
  if(!current())throw new Error('Windows access changed while resuming');
  const approved=await this.gate.authorize();
  if(!current()||approved?.mode!=='standalone'||approved.session?.method!=='windows-session')throw new Error('Windows sign-in is required');
  authorizationIdentity(approved);
  if(this.runtime.child&&this.runtime.authorization&&authorizationIdentity(approved)!==authorizationIdentity(this.runtime.authorization))throw new Error('Close the workspace before changing its Windows account');
  return approved; // Normal launch still checks the backend, generation and reveal boundary.
 }
 async refreshPasswordlessOwner({expectedGeneration=this.generation}={}){
  if(this.runtime.definition.id!=='terrier'||!this.suspended)return false;
  const authorization=this.runtime.authorization;
  const owner=value=>value?.owner?.mode==='existing-owner'&&value?.principal?.mode==='existing-owner';
  if(!owner(authorization))return false; // Recipients still need the existing password flow.
  try{
   const identity=authorizationIdentity(authorization),child=this.runtime.child,origin=this.runtime.origin,token=this.runtime.token;
   const current=()=>this.runtime.definition.id==='terrier'&&!this.osLocked&&this.suspended&&this.runtime.requestsAllowed===false
    &&expectedGeneration===this.generation&&Boolean(child)&&this.runtime.child===child
    &&Boolean(origin)&&this.runtime.origin===origin&&Boolean(token)&&this.runtime.token===token
    &&this.runtime.authorization===authorization&&owner(this.runtime.authorization)&&authorizationIdentity(this.runtime.authorization)===identity;
   const approved=value=>current()&&owner(value)&&authorizationIdentity(value)===identity;
   if(!current())throw new Error();
   if(!approved(await this.gate.authorize()))throw new Error();
   // A lock-time timeout is not a permanent password requirement for a verified owner.
   // This existing callback proves the bound account, administrator session and owner preference.
   if(await this.terrierPasswordLockDisabled()!==true||!current())throw new Error();
   if(!approved(await this.gate.authorize()))throw new Error();
   this.requiresFreshPassword=false;
   return true; // The caller must still use normal resume, runtime and reveal checks.
  }catch{throw new Error('Terrier owner sign-in could not be verified. Try opening the app again.');}
 }
 authenticationTicket(){return Object.freeze({generation:this.generation});}
 authenticationCurrent(ticket){return Boolean(ticket)&&ticket.generation===this.generation;}
 async prepareAuthentication(){
  const ticket=this.authenticationTicket();
  if(this.requiresFreshPassword&&await this.terrierAuthenticated()){
   await this.terrierLogout();if(await this.terrierAuthenticated())throw new Error('The previous sign-in could not be cleared');
  }
  return this.authenticationCurrent(ticket)?ticket:null;
 }
 async canReveal(generation,approved){
  const current=()=>!this.osLocked&&generation===this.generation&&!this.suspended&&this.runtime.requestsAllowed!==false&&Boolean(this.runtime.child);
  if(!current())return false;
  try{const latest=await this.gate.authorize();if(!current())return false;if(authorizationIdentity(latest)===authorizationIdentity(approved)&&authorizationIdentity(latest)===authorizationIdentity(this.runtime.authorization))return true;}catch{}
  if(current())await this.suspend('locked');return false;
 }
 async heartbeat(){const active=await this.authenticated();const state=this.osLocked?'locked':active?'active':'signed_out';try{await this.presence(state,this.sessionId);}catch{}return state;}
}
module.exports={authorizationIdentity,terrierSession,AccessLifecycle};
