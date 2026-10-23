'use strict';
const path=require('node:path');
const {execFile}=require('node:child_process');

// Fixed source; the file path is JSON data on stdin, never executable shell text.
const SCRIPT="$ProgressPreference='SilentlyContinue'; $ErrorActionPreference='Stop'; $inputData=[Console]::In.ReadToEnd() | ConvertFrom-Json; $signature=Get-AuthenticodeSignature -LiteralPath $inputData.path; [ordered]@{status=[int]$signature.Status; path=$signature.Path; thumbprint=$signature.SignerCertificate.Thumbprint} | ConvertTo-Json -Compress";
const THUMBPRINT=/^[0-9A-F]{40}$/;
// System.Management.Automation.SignatureStatus: 2 NotSigned, 3 HashMismatch. Any other status still names the signer
// (a self-signed release root that is not in the user's store reports UnknownError or NotTrusted), so the publisher
// decision is the signer thumbprint alone, checked against the Ed25519-signed manifest's allow-list. No trust store is
// consulted. The installer bytes are authenticated separately by the manifest's sha256/sha512 gates (trust.cjs).
const REFUSED_STATUS=new Set([2,3]);
function pinnedThumbprints(thumbprints){
  if(!Array.isArray(thumbprints)||!thumbprints.length||!thumbprints.every(value=>typeof value==='string'&&THUMBPRINT.test(value)))
    throw new Error('The signed release manifest names no publisher thumbprint; this installer is refused.');
  return thumbprints;
}
function verifySignatureResult(result,filename,thumbprints){
  const allowed=pinnedThumbprints(thumbprints);
  const thumbprint=typeof result?.thumbprint==='string'?result.thumbprint.toUpperCase():'';
  if(!Number.isInteger(result?.status)||REFUSED_STATUS.has(result.status)||!THUMBPRINT.test(thumbprint)||!allowed.includes(thumbprint)||
      typeof result.path!=='string'||path.win32.resolve(result.path).toLowerCase()!==path.win32.resolve(filename).toLowerCase())
    throw new Error('Windows package signature or pinned publisher thumbprint could not be verified.');
}
async function verifyWindowsPackage(filename,thumbprints){
  if(process.platform!=='win32')throw new Error('Windows package signature verification requires Windows.');
  pinnedThumbprints(thumbprints);
  const executable=path.join(process.env.SystemRoot||'C:\\Windows','System32','WindowsPowerShell','v1.0','powershell.exe');
  const encoded=Buffer.from(SCRIPT,'utf16le').toString('base64');
  const result=await new Promise((resolve,reject)=>{
    const environment={...process.env,PSModulePath:path.join(process.env.SystemRoot||'C:\\Windows','System32','WindowsPowerShell','v1.0','Modules')};
    const child=execFile(executable,['-NoProfile','-NonInteractive','-EncodedCommand',encoded],{env:environment,windowsHide:true,timeout:20000,maxBuffer:32768},(error,stdout,stderr)=>{
      // No verdict (spawn error, timeout, exit code or stderr) is distinguishable from a refused signature.
      if(error||stderr){reject(Object.assign(new Error('Windows package signature verification failed.'),{code:'SIGNATURE_CHECK_UNAVAILABLE'}));return;}
      try{resolve(JSON.parse(stdout));}catch{reject(Object.assign(new Error('Invalid Windows signature verification result.'),{code:'SIGNATURE_CHECK_UNAVAILABLE'}));}
    });
    child.stdin.on('error',()=>{});child.stdin.end(JSON.stringify({path:path.resolve(filename)}));
  });
  verifySignatureResult(result,filename,thumbprints);
}
module.exports={verifyWindowsPackage,verifySignatureResult};
