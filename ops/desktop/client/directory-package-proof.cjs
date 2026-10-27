'use strict';
// ZIP has no Authenticode container. This independent publisher signature binds
// every archived byte in addition to the existing Ed25519 release authorization.
const crypto=require('node:crypto');
const {appDefinition}=require('./apps.cjs');
const {THUMBPRINT}=require('./publisher-trust.cjs');
const FORMAT='windows-directory-zip-v1',DISTRIBUTION='directory-zip',UPDATER_VERSION='2.0.0';
const DOMAIN='MELANGE-DESKTOP-DIRECTORY-ZIP-V1\n';
function canonicalBase64(value,maximum,label){
 if(typeof value!=='string'||value.length===0||value.length>maximum*2)throw new Error('Invalid '+label);
 const bytes=Buffer.from(value,'base64');
 if(bytes.length===0||bytes.length>maximum||bytes.toString('base64')!==value)throw new Error('Invalid '+label);
 return bytes;
}
function directoryPackageIdentity(manifest){
 const p=manifest?.package,name=appDefinition(manifest?.appId).name;
 if(manifest.platform!=='win32'||manifest.arch!=='x64'||typeof manifest.version!=='string'||!/^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/.test(manifest.version)||
    p?.format!==FORMAT||p.entrypoint!==name+'.exe'||p.name!==manifest.appId+'-'+manifest.version+'-win32-x64.zip'||
    !Number.isSafeInteger(p.size)||p.size<1||p.size>20*1024**3||typeof p.sha256!=='string'||! /^[a-f0-9]{64}$/.test(p.sha256)||canonicalBase64(p.sha512,64,'ZIP SHA-512').length!==64)
  throw new Error('Invalid directory ZIP package identity');
 return {appId:manifest.appId,version:manifest.version,platform:manifest.platform,arch:manifest.arch,format:p.format,entrypoint:p.entrypoint,name:p.name,size:p.size,sha256:p.sha256,sha512:p.sha512};
}
function publisherProofPayload(manifest){return Buffer.from(DOMAIN+JSON.stringify(directoryPackageIdentity(manifest)),'utf8');}
function verifyDirectoryPackageProof(manifest){
 const payload=publisherProofPayload(manifest),proof=manifest.package.publisherProof;
 if(!proof||typeof proof!=='object'||Array.isArray(proof)||Object.keys(proof).sort().join('|')!=='algorithm|certificateDer|schemaVersion|signature'||proof.schemaVersion!==1||proof.algorithm!=='rsa-sha256')
  throw new Error('Invalid directory ZIP publisher proof');
 const der=canonicalBase64(proof.certificateDer,16384,'publisher certificate'),signature=canonicalBase64(proof.signature,1024,'publisher signature');
 let certificate;try{certificate=new crypto.X509Certificate(der);}catch{throw new Error('Invalid publisher certificate');}
 const thumbprint=crypto.createHash('sha1').update(der).digest('hex').toUpperCase();
 if(!certificate.raw.equals(der)||thumbprint!==THUMBPRINT||!Array.isArray(manifest.publisherThumbprints)||!manifest.publisherThumbprints.includes(THUMBPRINT))throw new Error('Directory ZIP publisher certificate does not match the pinned publisher');
 const key=certificate.publicKey;
 if(key.asymmetricKeyType!=='rsa'||key.asymmetricKeyDetails?.modulusLength<2048||!certificate.keyUsage?.includes('1.3.6.1.5.5.7.3.3'))throw new Error('Unsupported directory ZIP signing certificate');
 const issued=Date.parse(manifest.issuedAt);
 if(!Number.isFinite(issued)||issued<Date.parse(certificate.validFrom)||issued>Date.parse(certificate.validTo))throw new Error('Directory ZIP release is outside publisher certificate validity');
 if(!crypto.verify('sha256',payload,{key,padding:crypto.constants.RSA_PKCS1_PADDING},signature))throw new Error('Invalid directory ZIP publisher signature');
 return {thumbprint,entrypoint:manifest.package.entrypoint};
}
module.exports={FORMAT,DISTRIBUTION,UPDATER_VERSION,directoryPackageIdentity,publisherProofPayload,verifyDirectoryPackageProof};
