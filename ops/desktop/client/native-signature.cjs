'use strict';
const path=require('node:path'),fs=require('node:fs');
const {desktopProbe}=require('./desktop-probe.cjs');
const {verifyProbeRuntime}=require('./signature-probe-runtime.cjs');
const {THUMBPRINT:PINNED}=require('./publisher-trust.cjs');

const THUMBPRINT=/^[0-9A-F]{40}$/;
const UNTRUSTED_ROOT=0x800B0109;
const FIELDS='certificateError,chainErrors,counterSignerErrors,path,schemaVersion,selfSigned,signerError,thumbprint,validAtVerificationTime,verdict,wintrustStatus';
function validVerdict(result){
 return result&&Object.keys(result).sort().join(',')===FIELDS&&result.schemaVersion===1&&typeof result.path==='string'&&
  ['verified','refused'].includes(result.verdict)&&Number.isInteger(result.wintrustStatus)&&result.wintrustStatus>=0&&result.wintrustStatus<=0xffffffff&&
  (result.thumbprint===null||typeof result.thumbprint==='string'&&THUMBPRINT.test(result.thumbprint.toUpperCase()))&&
  ['selfSigned','validAtVerificationTime','counterSignerErrors'].every(key=>typeof result[key]==='boolean')&&
  ['certificateError','signerError'].every(key=>result[key]===null||Number.isInteger(result[key])&&result[key]>=0&&result[key]<=0xffffffff)&&
  Number.isInteger(result.chainErrors)&&result.chainErrors>=0&&result.chainErrors<=0xffffffff;
}
function acceptedVerdict(result){
 if(result.verdict!=='verified')return false;
 if(result.wintrustStatus===0)return true; // standard Windows trust/timestamp verdict
 if(!result.validAtVerificationTime||result.counterSignerErrors)return false;
 return result.wintrustStatus===UNTRUSTED_ROOT&&result.selfSigned&&result.chainErrors===0x20&&
  [0,UNTRUSTED_ROOT].includes(result.certificateError)&&[0,UNTRUSTED_ROOT].includes(result.signerError)&&result.thumbprint?.toUpperCase()===PINNED;
}
// Get-AuthenticodeSignature hashes the whole file: a 578 MB installer took 32-46 s on a slow host (FAIL-04), past the
// former fixed 20 s. Allow 60 s plus 30 s per started 100 MiB, bounded to 60 s..10 min (578 MB -> 240 s). A timeout
// still refuses the installer (fail closed); it is never treated as a skipped check.
const MIB=1024*1024;
function signatureTimeoutMs(bytes){
  const blocks=Math.ceil(Math.max(0,Number(bytes)||0)/(100*MIB));
  return Math.min(600000,Math.max(60000,60000+30000*blocks));
}
// D-328/T18: the client pin is the publisher; the signed manifest may only confirm it, never widen it. Paul ruling
// 2026-10-26: that NEW pin check is warn-only for 1.0.19 (a mismatch is logged and surfaced through the update status
// and the update proceeds on the manifest allow-list alone); the allow-list itself is always enforced.
// Enforced after the 1.0.19 warning release (Paul ruling 2026-10-26, T18).
const PUBLISHER_PIN_ENFORCE=true;
function allowList(thumbprints){
  if(!Array.isArray(thumbprints)||!thumbprints.length||!thumbprints.every(value=>typeof value==='string'&&THUMBPRINT.test(value)))
    throw new Error('The signed release manifest names no publisher thumbprint; this installer is refused.');
  return thumbprints;
}
function pinnedThumbprints(thumbprints,enforce=PUBLISHER_PIN_ENFORCE){
  const listed=allowList(thumbprints);
  if(!enforce)return listed;
  if(!listed.includes(PINNED))throw new Error('The signed release manifest does not name the pinned publisher thumbprint; this installer is refused.');
  return [PINNED];
}
function pinWarning(listed,thumbprint){
  if(!listed.includes(PINNED))return 'Update publisher warning: the signed release manifest does not name the pinned publisher certificate ('+PINNED+'). This release still installs; the next release will refuse it.';
  if(thumbprint!==PINNED)return 'Update publisher warning: the installer is signed by '+thumbprint+', not the pinned publisher certificate ('+PINNED+'). This release still installs; the next release will refuse it.';
  return null;
}
function verifySignatureResult(result,filename,thumbprints,{enforce=PUBLISHER_PIN_ENFORCE,warn}={}){
  const allowed=pinnedThumbprints(thumbprints,enforce);
  const thumbprint=typeof result?.thumbprint==='string'?result.thumbprint.toUpperCase():'';
  if(!validVerdict(result)||!acceptedVerdict(result)||!THUMBPRINT.test(thumbprint)||!allowed.includes(thumbprint)||
      typeof result.path!=='string'||path.win32.resolve(result.path).toLowerCase()!==path.win32.resolve(filename).toLowerCase())
    throw new Error('Windows package signature or pinned publisher thumbprint could not be verified.');
  const message=enforce?null:pinWarning(thumbprints,thumbprint);
  if(message){console.warn(message);if(typeof warn==='function')warn(message);}
}
async function verifyWindowsPackage(filename,thumbprints,{enforce=PUBLISHER_PIN_ENFORCE,warn,resources,appId}={}){
  if(process.platform!=='win32')throw new Error('Windows package signature verification requires Windows.');
  pinnedThumbprints(thumbprints,enforce);
  const timeout=signatureTimeoutMs(fs.statSync(filename).size),started=Date.now();
  let result;
  try{
    // The command and all importable interpreter bytes come from ASAR-pinned
    // authority, not settings, a mutable runtime manifest, PATH or a shell.
    const command=verifyProbeRuntime(resources,appId);
    result=await desktopProbe(command,'--desktop-windows-signature',{path:path.resolve(filename)},{timeout,limit:32768});
    if(!validVerdict(result))throw new Error('Invalid Windows signature response');
  }catch(error){
    const elapsed=Date.now()-started;
    throw Object.assign(new Error('Windows package signature verification failed after '+(elapsed/1000).toFixed(1)+' s (limit '+(timeout/1000).toFixed(1)+' s).'),{code:'SIGNATURE_CHECK_UNAVAILABLE',elapsedMs:elapsed,timeoutMs:timeout});
  }
  verifySignatureResult(result,filename,thumbprints,{enforce,warn});
}
module.exports={verifyWindowsPackage,verifySignatureResult,validVerdict,signatureTimeoutMs,PUBLISHER_PIN_ENFORCE};
