'use strict';
const crypto=require('node:crypto');
const {accessStateStore}=require('./access-state.cjs');
const {bootstrapAccess,exactIdentity}=require('./access-bootstrap.cjs');
const {deviceStore}=require('./access-credentials.cjs');
const {protectedLocalStores}=require('./standalone-state.cjs');
const {createStandaloneGate}=require('./standalone-access.cjs');
async function bootstrapStandalone({resources,appId,profile,configuration,packaged,bundledTrust,safeStorage,authentication='password'}){
 if(process.platform!=='win32'||process.arch!=='x64')throw new Error('Local desktop access supports Windows x64 only');
 if(!['password','windows'].includes(authentication))throw new Error('Unsupported local authentication mode');
 const identityStore=accessStateStore({resources,appId,profile,kind:'identity'});
 let saved=await identityStore.read();
 if(!saved){saved={schemaVersion:1,appId,deviceId:crypto.randomUUID(),platform:'win32',arch:'x64'};await identityStore.write(saved);}
 const identity=exactIdentity(saved,appId),stores=protectedLocalStores({profile,appId,deviceId:identity.deviceId,safeStorage});
 let legacy;
 if(!await stores.accountStore.read()){
  // Pending fresh installs have no grant to migrate. Existing signed accounts
  // are checked offline; no approval request, poll, refresh or bearer call occurs.
  const previous=await accessStateStore({resources,appId,profile,kind:'state'}).read();
  if(previous?.grantEnvelope){
   const old=await bootstrapAccess({resources,appId,profile,configuration,packaged,bundledTrust});
   const accepted=await old.evidence();
   if(accepted&&!accepted.revoked){
    const grant=accepted.grant;
    const passwordRecord=appId==='terrier'?null:await old.passwords.read(grant);
    let deviceRecord=appId==='terrier'?null:await deviceStore(resources).read(grant);
    const deviceFields=['serverId','deviceId','principalId','accountIdentity','appId','grantId'];
    // An old remembered-device record can refer to a replaced approval. Like
    // the previous sign-in flow, that case asks for the preserved password.
    if(deviceRecord&&(deviceRecord.schemaVersion!==1||!deviceRecord.binding||Object.keys(deviceRecord.binding).length!==deviceFields.length||deviceFields.some(key=>deviceRecord.binding[key]!==grant[key])||!Number.isSafeInteger(deviceRecord.verifiedAt)||deviceRecord.verifiedAt<0))deviceRecord=null;
    let ownerVerified=false;
    try{ownerVerified=Boolean(await old.owner(accepted,configuration()));}catch{/* Unverified owner status cannot confer remembered local sign-in. */}
    legacy={grant,passwordRecord,deviceRecord,ownerVerified};
   }
  }
 }
 const windowsSessionProvider=authentication==='windows'?()=>require('./windows-session.cjs').windowsSession(resources,appId):undefined;
 return createStandaloneGate({appId,identity,configuration,...stores,legacy,authentication,windowsSessionProvider});
}
module.exports={bootstrapStandalone};
