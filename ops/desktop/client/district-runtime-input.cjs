'use strict';
// Only the native verified provider can attach this ephemeral launch binding.
// Settings copies and renderer messages never carry it or the commit secret.
const crypto=require('node:crypto'),fs=require('node:fs');
const {canonical}=require('./access-client.cjs');
const {districtSourceDigest,verifyDistrictProgram}=require('./district-data-probe.cjs');
const {dataStartupFailure,programFailure}=require('./startup-failure.cjs');
const INPUTS=new WeakMap(),MAX_FRAME=2*1024**2;
const hash=value=>crypto.createHash('sha256').update(canonical(value)).digest('hex');
function changed(){const error=new Error('The selected district changed before startup.');error.code=error.reason='context';return error;}
function bindDistrictConfiguration(configuration,{profile,directory,district,files,verify,commit,close}){
 if(!configuration||INPUTS.has(configuration)||[verify,commit,close].some(value=>typeof value!=='function'))throw programFailure();
 const sourceDigest=districtSourceDigest(district,files),record={configuration:canonical(configuration),profile,directory,district,files:structuredClone(files),sourceDigest,verify,commit,close,closed:false,consumed:false};
 const release=async()=>{if(record.closed)return;record.closed=true;clearTimeout(record.timer);await close();};record.release=release;
 // A canceled caller that never reaches Runtime cannot hold verified handles.
 record.timer=setTimeout(()=>{release().catch(()=>{});},120000);record.timer.unref?.();
 INPUTS.set(configuration,record);return configuration;
}
function consumeDistrictConfiguration(runtime,configuration){
 const record=INPUTS.get(configuration);if(!record)return null;INPUTS.delete(configuration);
 if(record.closed||record.consumed||record.configuration!==canonical(configuration)||record.profile!==runtime.userData||runtime.definition.id!=='terrier'){record.release().catch(()=>{});throw changed();}
 let contract;try{contract=verifyDistrictProgram(runtime);}catch(error){record.release().catch(()=>{});throw error;}
 record.consumed=true;clearTimeout(record.timer);
 const nonce=crypto.randomBytes(32).toString('base64url'),commitToken=crypto.randomBytes(32).toString('base64url');
 let context=null;
 const guard=async()=>{if(record.closed)throw changed();verifyDistrictProgram(runtime);await record.verify();};
 return Object.freeze({sourceDigest:record.sourceDigest,district:record.district,programFingerprint:contract.programFingerprint,
  async validate(){await guard();},
  frame(roots,sourceRoot){
   if(context||roots.district!==record.district||fs.realpathSync.native(roots.data)!==fs.realpathSync.native(record.directory))throw changed();
   const paths={profileRoot:fs.realpathSync.native(runtime.userData),sourceRoot:fs.realpathSync.native(sourceRoot),dataRoot:fs.realpathSync.native(roots.data),stateRoot:fs.realpathSync.native(roots.state)};
   context=Object.freeze({schemaVersion:1,appId:'terrier',launchNonce:nonce,programFingerprint:contract.programFingerprint,sourceDigest:record.sourceDigest,district:record.district,rootsDigest:hash(paths)});
   const raw=Buffer.from(canonical({...context,...paths,files:record.files,commitToken}));if(raw.length>MAX_FRAME)throw programFailure();
   const framed=Buffer.alloc(raw.length+4);framed.writeUInt32BE(raw.length);raw.copy(framed,4);return framed;
  },
  diagnostic(){if(!context)throw changed();return {appId:'terrier',launchNonce:nonce,programFingerprint:contract.programFingerprint,sourceDigests:{district:record.sourceDigest},guard:()=>verifyDistrictProgram(runtime)};},
  matches(value,phase){
   const actual=value?.districtData;if(value?.pid!==runtime.child?.pid||!context||!actual||actual.phase!==phase||Object.keys(actual).sort().join('|')!==[...Object.keys(context),'phase','snapshot'].sort().join('|')||Object.entries(context).some(([key,item])=>actual[key]!==item))return false;
   return typeof actual.snapshot==='string'&&record.files.some(item=>item.role==='snapshots/'+actual.snapshot+'/manifest.json');
  },
  matchesWarm(value,roots){
   const actual=value?.districtData;if(value?.pid!==runtime.child?.pid||!actual||actual.schemaVersion!==1||actual.appId!=='terrier'||actual.phase!=='active'||actual.sourceDigest!==record.sourceDigest||actual.programFingerprint!==contract.programFingerprint||actual.district!==record.district||!/^[A-Za-z0-9_-]{43}$/.test(actual.launchNonce))return false;
   const sourceRoot=require('node:path').join(require('./backend-command.cjs').backendCommand(runtime.resources,'terrier').runtime,'sources');
   const paths={profileRoot:fs.realpathSync.native(runtime.userData),sourceRoot:fs.realpathSync.native(sourceRoot),dataRoot:fs.realpathSync.native(roots.data),stateRoot:fs.realpathSync.native(roots.state)};
   return actual.rootsDigest===hash(paths)&&record.files.some(item=>item.role==='snapshots/'+actual.snapshot+'/manifest.json');
  },
  async commitNative(origin,token){
   await guard();
   await new Promise((resolve,reject)=>{
    const target=new URL('/__desktop/district-commit',origin),request=require('node:http').request(target,{method:'POST',headers:{'X-Desktop-Token':token,'X-Desktop-District-Commit':commitToken,'Content-Length':'0'},agent:false},response=>{response.resume();response.once('end',()=>response.statusCode===204?resolve():reject(new Error('The selected district could not be activated.')));response.once('error',reject);});
    request.setTimeout(30000,()=>request.destroy(new Error('District activation timed out.')));request.once('error',reject);request.end();
   });
   await guard();
  },
  async commit(){await guard();await record.commit();},
  close:record.release,maximum:MAX_FRAME
 });
}
async function discardDistrictConfiguration(configuration){const record=INPUTS.get(configuration);if(!record)return false;INPUTS.delete(configuration);await record.release();return true;}
module.exports={bindDistrictConfiguration,consumeDistrictConfiguration,discardDistrictConfiguration,MAX_FRAME};
