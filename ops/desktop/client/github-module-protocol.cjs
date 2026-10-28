'use strict';
// Public data uses its own signature purpose and high-water; binary updates and
// recipient-pinned dataset transport remain separate.
const crypto=require('node:crypto');
const path=require('node:path');
const {canonical}=require('./access-client.cjs');
const {exact,strictJson}=require('./dataset-protocol.cjs');
const MAX_MANIFEST=2*1024**2,MAX_SEGMENT=1024**3,MAX_TOTAL=32*1024**3;
const MAX_SEGMENTS=256,POINTER_PATH='docs/desktop-data/current.json';
const HASH=/^[a-f0-9]{64}$/,COMMIT=/^[a-f0-9]{40}$/;
const UUID=/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/;
const TAG=/^module-data-\d{4}-\d{2}-\d{2}(?:-[a-z0-9][a-z0-9.-]{0,40})?$/;
const APPS=Object.freeze({melange:Object.freeze({repository:'pjg93-222/melange',purpose:'melange-public-module-data'}),mentat:Object.freeze({repository:'pjg93-222/mentat',purpose:'mentat-public-module-data'})});
function fail(reason='integrity',message='GitHub module data verification failed'){const error=new Error(message);error.reason=reason;return error;}
function requireValue(value,message){if(!value)throw fail('integrity',message);}
function configuration(appId){if(!Object.hasOwn(APPS,appId))throw fail('integrity','Unsupported GitHub module');return APPS[appId];}
function integer(value,max=Number.MAX_SAFE_INTEGER){return Number.isSafeInteger(value)&&value>=0&&value<=max;}
function hash(value){return typeof value==='string'&&HASH.test(value);}
function parseJson(bytes){try{return strictJson(bytes);}catch{throw fail('integrity','Invalid GitHub module JSON');}}
function uuid(value){return typeof value==='string'&&UUID.test(value)&&value!=='00000000-0000-0000-0000-000000000000';}
function assetName(value){return typeof value==='string'&&/^[A-Za-z0-9][A-Za-z0-9._-]{0,150}$/.test(value)&&!value.endsWith('.')&&!/^(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i.test(value);}
function relative(value){return typeof value==='string'&&value.length>0&&value.length<=400&&value.split('/').every(part=>assetName(part)&&part!=='.'&&part!=='..');}
function authorized(appId,selected,authorization){
 if(!Object.hasOwn(APPS,appId)||!selected||typeof selected.dataDirectory!=='string'||!path.isAbsolute(selected.dataDirectory))return false;
 if(authorization?.mode==='standalone'){
  // This proves local sign-in for PUBLIC GitHub datasets only. Private data
  // transports still require their real server grants and bearer credentials.
  try{
   exact(authorization,['mode','identity','session','principal']);
   const identity=require('./standalone-access.cjs').validIdentity(authorization.identity),session=authorization.session;
   exact(session,[...Object.keys(identity),'sessionId','authenticatedAt','method']);
   return identity.appId===appId&&authorization.principal===null&&Object.keys(identity).every(key=>session[key]===identity[key])&&uuid(session.sessionId)&&integer(session.authenticatedAt)&&['local-password','device-trust','windows-session'].includes(session.method);
  }catch{return false;}
 }
 const {accepted,owner}=authorization||{},grant=accepted?.grant,bindings=owner?.dataBindings;
 return Boolean(accepted?.revoked===false&&grant?.appId===appId&&owner?.mode==='existing-owner'&&owner.appId===appId&&owner.grantId===grant.grantId&&owner.accountIdentity===grant.accountIdentity&&typeof grant.grantId==='string'&&typeof grant.accountIdentity==='string'&&Array.isArray(bindings)&&bindings.length===1&&bindings[0]?.districtId===null&&bindings[0]?.localUserId===null&&bindings[0]?.localUsername===null&&hash(bindings[0]?.dataRootHash));
}
function checkedRegistry(appId,registry,requiredKinds=Object.keys(registry||{})){
 configuration(appId);requireValue(registry&&typeof registry==='object'&&!Array.isArray(registry),'Compiled module adapters are required');
 requireValue(Array.isArray(requiredKinds)&&requiredKinds.length>0&&requiredKinds.length<=32&&new Set(requiredKinds).size===requiredKinds.length,'Compiled required datasets are unavailable');
 let budget=0;
 for(const [kind,adapter] of Object.entries(registry)){
  requireValue(kind.startsWith(appId+'.')&&/^[a-z0-9.-]{1,100}$/.test(kind)&&adapter?.appId===appId&&adapter.version===1&&typeof adapter.validateMetadata==='function'&&typeof adapter.validateSnapshot==='function','Invalid compiled module adapter');
  requireValue(adapter.roles&&typeof adapter.roles==='object'&&!Array.isArray(adapter.roles)&&Object.keys(adapter.roles).length>0&&Object.keys(adapter.roles).length<=128&&integer(adapter.maxTotalBytes,MAX_TOTAL)&&adapter.maxTotalBytes>0,'Invalid compiled module budget');
  const paths=new Set();
  for(const [role,spec] of Object.entries(adapter.roles)){
   requireValue(/^[a-z][a-z0-9_.-]{0,63}$/.test(role)&&spec&&relative(spec.path)&&integer(spec.maxBytes,MAX_TOTAL)&&spec.maxBytes>0&&!paths.has(spec.path.toLowerCase()),'Invalid compiled module role');
   requireValue(!/\.(?:html?|[cm]?js|exe|dll|cmd|bat|ps1|sh|py|r|zip|gz|br|7z|tar)$/i.test(spec.path),'Executable or archived module data is unsupported');
   paths.add(spec.path.toLowerCase());
  }
  budget+=adapter.maxTotalBytes;
 }
 requireValue(budget<=MAX_TOTAL&&requiredKinds.every(kind=>Object.hasOwn(registry,kind)),'Compiled module budget or required kind is invalid');
 return registry;
}
function pointer(appId,envelope,publicKeys,previous={}){
 const app=configuration(appId);
 try{
  exact(envelope,['schemaVersion','keyId','payload','signature']);
  requireValue(envelope.schemaVersion===1&&typeof envelope.keyId==='string'&&Object.hasOwn(publicKeys||{},envelope.keyId)&&typeof envelope.payload==='string'&&envelope.payload.length<16384&&typeof envelope.signature==='string','Untrusted GitHub module pointer');
  const raw=publicKeys[envelope.keyId],bytes=Buffer.from(envelope.payload,'base64'),signature=Buffer.from(envelope.signature,'base64');
  requireValue(typeof raw==='string'&&Buffer.from(raw,'base64').length===32&&Buffer.from(raw,'base64').toString('base64')===raw&&bytes.toString('base64')===envelope.payload&&signature.length===64&&signature.toString('base64')===envelope.signature,'Invalid GitHub module signature encoding');
  const key=crypto.createPublicKey({key:Buffer.concat([Buffer.from('302a300506032b6570032100','hex'),Buffer.from(raw,'base64')]),format:'der',type:'spki'});
  requireValue(crypto.verify(null,bytes,key,signature),'Invalid GitHub module signature');
  const value=strictJson(bytes),digest=crypto.createHash('sha256').update(bytes).digest('hex');
  exact(value,['schemaVersion','purpose','appId','repository','catalogSequence','releaseTag','releaseCommit','manifest']);
  requireValue(canonical(value)===bytes.toString('utf8')&&value.schemaVersion===1&&value.purpose===app.purpose&&value.appId===appId&&value.repository===app.repository&&integer(value.catalogSequence)&&value.catalogSequence>0&&typeof value.releaseTag==='string'&&TAG.test(value.releaseTag)&&COMMIT.test(value.releaseCommit)&&value.releaseCommit!=='0'.repeat(40),'Unsupported GitHub module pointer');
  exact(value.manifest,['asset','bytes','sha256']);
  requireValue(value.manifest.asset==='manifest.json'&&integer(value.manifest.bytes,MAX_MANIFEST)&&value.manifest.bytes>0&&hash(value.manifest.sha256),'Invalid GitHub module manifest binding');
  requireValue(value.catalogSequence>=(previous.catalogSequence||0)&&(value.catalogSequence!==previous.catalogSequence||digest===previous.pointerDigest),'GitHub module rollback or equivocation refused');
  return {value,digest,envelope:structuredClone(envelope)};
 }catch(error){if(error?.reason)throw error;throw fail();}
}
function manifest(appId,bytes,checked,registry,requiredKinds=Object.keys(registry||{})){
 try{
  const app=configuration(appId);checkedRegistry(appId,registry,requiredKinds);
  requireValue(Buffer.isBuffer(bytes)&&bytes.length===checked.value.manifest.bytes&&crypto.createHash('sha256').update(bytes).digest('hex')===checked.value.manifest.sha256,'GitHub module manifest integrity failed');
  const value=strictJson(bytes);exact(value,['schemaVersion','purpose','appId','repository','releaseTag','datasets']);
  requireValue(value.schemaVersion===1&&value.purpose===app.purpose+'sets'&&value.appId===appId&&value.repository===app.repository&&value.releaseTag===checked.value.releaseTag&&Array.isArray(value.datasets)&&value.datasets.length>0&&value.datasets.length<=32,'Unsupported GitHub module manifest');
  const ids=new Set(),revisions=new Set(),kinds=new Set(),assets=new Set();let totalBytes=0,segmentCount=0;
  for(const dataset of value.datasets){
   exact(dataset,['datasetId','revisionId','kind','adapterVersion','objects','counts']);
   requireValue(uuid(dataset.datasetId)&&uuid(dataset.revisionId)&&!ids.has(dataset.datasetId)&&!revisions.has(dataset.revisionId)&&!kinds.has(dataset.kind)&&Object.hasOwn(registry,dataset.kind)&&dataset.adapterVersion===1,'Invalid GitHub module dataset identity');
   ids.add(dataset.datasetId);revisions.add(dataset.revisionId);kinds.add(dataset.kind);
   const adapter=registry[dataset.kind];
   requireValue(Array.isArray(dataset.objects)&&dataset.objects.length===Object.keys(adapter.roles).length,'Module role set is incomplete');
   exact(dataset.counts,['files']);requireValue(dataset.counts.files===dataset.objects.length,'Invalid GitHub module file count');
   const roles=new Set();let datasetBytes=0;
   for(const object of dataset.objects){
    exact(object,['role','bytes','sha256','segments']);
    requireValue(typeof object.role==='string'&&Object.hasOwn(adapter.roles,object.role)&&!roles.has(object.role)&&integer(object.bytes,adapter.roles[object.role].maxBytes)&&object.bytes>0&&hash(object.sha256)&&Array.isArray(object.segments)&&object.segments.length>0&&object.segments.length<=32,'Invalid GitHub module logical role');
    roles.add(object.role);let raw=0;
    for(const segment of object.segments){
     exact(segment,['asset','bytes','sha256']);
     requireValue(assetName(segment.asset)&&!assets.has(segment.asset.toLowerCase())&&integer(segment.bytes,MAX_SEGMENT)&&segment.bytes>0&&hash(segment.sha256),'Invalid GitHub module segment');
     assets.add(segment.asset.toLowerCase());raw+=segment.bytes;segmentCount++;
    }
    requireValue(raw===object.bytes,'GitHub module segment sum differs from logical role');datasetBytes+=object.bytes;
   }
   requireValue(datasetBytes<=adapter.maxTotalBytes&&adapter.validateMetadata(structuredClone(dataset))===true,'Compiled module adapter rejected metadata');totalBytes+=datasetBytes;
  }
  requireValue(requiredKinds.every(kind=>kinds.has(kind))&&segmentCount<=MAX_SEGMENTS&&totalBytes<=MAX_TOTAL,'GitHub module total budget or required datasets exceeded');
  return {value,bytes:Buffer.from(bytes),sha256:checked.value.manifest.sha256,totalBytes,segmentCount};
 }catch(error){if(error?.reason)throw error;throw fail();}
}
module.exports={configuration,authorized,checkedRegistry,pointer,manifest,parseJson,fail,requireValue,integer,hash,uuid,assetName,relative,HASH,COMMIT,TAG,POINTER_PATH,MAX_MANIFEST,MAX_SEGMENT,MAX_TOTAL,MAX_SEGMENTS};
