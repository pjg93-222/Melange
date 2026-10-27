'use strict';
const path=require('node:path'),fs=require('node:fs');
const {execFile}=require('node:child_process');
const {THUMBPRINT:PINNED}=require('./publisher-trust.cjs');

// Fixed source; the file path is JSON data on stdin, never executable shell text.
const SCRIPT="$ProgressPreference='SilentlyContinue'; $ErrorActionPreference='Stop'; $inputData=[Console]::In.ReadToEnd() | ConvertFrom-Json; $signature=Get-AuthenticodeSignature -LiteralPath $inputData.path; [ordered]@{status=[int]$signature.Status; path=$signature.Path; thumbprint=$signature.SignerCertificate.Thumbprint} | ConvertTo-Json -Compress";
const THUMBPRINT=/^[0-9A-F]{40}$/;
// System.Management.Automation.SignatureStatus: 2 NotSigned, 3 HashMismatch. Any other status still names the signer
// (a self-signed release root that is not in the user's store reports UnknownError or NotTrusted), so the publisher
// decision is the signer thumbprint alone, checked against the Ed25519-signed manifest's allow-list. No trust store is
// consulted. The installer bytes are authenticated separately by the manifest's sha256/sha512 gates (trust.cjs).
const REFUSED_STATUS=new Set([2,3]);
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
// Enforced starting with 1.0.20 (Paul ruling 2026-10-26, T18).
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
  if(!Number.isInteger(result?.status)||REFUSED_STATUS.has(result.status)||!THUMBPRINT.test(thumbprint)||!allowed.includes(thumbprint)||
      typeof result.path!=='string'||path.win32.resolve(result.path).toLowerCase()!==path.win32.resolve(filename).toLowerCase())
    throw new Error('Windows package signature or pinned publisher thumbprint could not be verified.');
  const message=enforce?null:pinWarning(thumbprints,thumbprint);
  if(message){console.warn(message);if(typeof warn==='function')warn(message);}
}
async function verifyWindowsPackage(filename,thumbprints,{enforce=PUBLISHER_PIN_ENFORCE,warn}={}){
  if(process.platform!=='win32')throw new Error('Windows package signature verification requires Windows.');
  pinnedThumbprints(thumbprints,enforce);
  const executable=path.join(process.env.SystemRoot||'C:\\Windows','System32','WindowsPowerShell','v1.0','powershell.exe');
  const encoded=Buffer.from(SCRIPT,'utf16le').toString('base64');
  const timeout=signatureTimeoutMs(fs.statSync(filename).size),started=Date.now();
  const result=await new Promise((resolve,reject)=>{
    const environment={...process.env,PSModulePath:path.join(process.env.SystemRoot||'C:\\Windows','System32','WindowsPowerShell','v1.0','Modules')};
    const child=execFile(executable,['-NoProfile','-NonInteractive','-EncodedCommand',encoded],{env:environment,windowsHide:true,timeout,maxBuffer:32768},(error,stdout,stderr)=>{
      // No verdict (spawn error, timeout, exit code or stderr) is distinguishable from a refused signature.
      if(error||stderr){
        const seconds=ms=>(ms/1000).toFixed(1)+' s',elapsed=Date.now()-started;
        reject(Object.assign(new Error('Windows package signature verification failed after '+seconds(elapsed)+' (limit '+seconds(timeout)+(error?.killed?', timed out':'')+').'),{code:'SIGNATURE_CHECK_UNAVAILABLE',elapsedMs:elapsed,timeoutMs:timeout}));return;
      }
      try{resolve(JSON.parse(stdout));}catch{reject(Object.assign(new Error('Invalid Windows signature verification result.'),{code:'SIGNATURE_CHECK_UNAVAILABLE'}));}
    });
    child.stdin.on('error',()=>{});child.stdin.end(JSON.stringify({path:path.resolve(filename)}));
  });
  verifySignatureResult(result,filename,thumbprints,{enforce,warn});
}
module.exports={verifyWindowsPackage,verifySignatureResult,signatureTimeoutMs,PUBLISHER_PIN_ENFORCE};
