'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {verifySignatureResult}=require('../native-signature.cjs');
const PIN='0EBC9AD04E929CDD731EDB5D278A4143BC3D3D30',OTHER='1111111111111111111111111111111111111111';
test('native signature requires a pinned signer thumbprint and the exact installer path, not Windows trust',()=>{
  const filename='C:\Test\Package.exe',pins=[OTHER,PIN];
  const valid={status:0,thumbprint:PIN,path:filename};
  verifySignatureResult(valid,filename,pins);
  // UnknownError / NotTrusted: a self-signed release root absent from the user's store still names its signer.
  for(const status of [1,4])verifySignatureResult({...valid,status},filename,pins);
  verifySignatureResult({...valid,thumbprint:PIN.toLowerCase()},filename,pins);
  for(const result of [{},{...valid,status:2},{...valid,status:3},{...valid,status:'0'},{...valid,thumbprint:null},{...valid,thumbprint:'2222222222222222222222222222222222222222'},
    {...valid,thumbprint:PIN+'00'},{...valid,path:'C:\Other\Package.exe'},{...valid,path:undefined}])
    assert.throws(()=>verifySignatureResult(result,filename,pins),/could not be verified/);
  for(const pins of [undefined,null,[],'0EBC',[PIN.toLowerCase()]])assert.throws(()=>verifySignatureResult(valid,filename,pins),/names no publisher thumbprint/);
});
test('signature tool failures without a verdict are tagged; a parsed refusal is not',async()=>{
  const childProcess=require('node:child_process'),realExecFile=childProcess.execFile,platform=Object.getOwnPropertyDescriptor(process,'platform');
  const filename='C:\Test\Package.exe',pins=[PIN],modulePath=require.resolve('../native-signature.cjs');
  let reply,calls=0;
  childProcess.execFile=(file,args,options,callback)=>{calls++;process.nextTick(()=>callback(...reply()));return {stdin:{on(){},end(){}}};};
  Object.defineProperty(process,'platform',{...platform,value:'win32'});delete require.cache[modulePath];
  try{
    const {verifyWindowsPackage}=require('../native-signature.cjs');
    const verdict=(status,thumbprint=PIN)=>JSON.stringify({status,path:filename,thumbprint});
    for(const [name,result] of [
      ['timeout',()=>[Object.assign(new Error('timed out'),{killed:true,signal:'SIGTERM'}),'','']],
      ['spawn error',()=>[Object.assign(new Error('spawn powershell.exe ENOENT'),{code:'ENOENT'}),'','']],
      ['non-zero exit',()=>[Object.assign(new Error('Command failed'),{code:1}),'','']],
      ['stderr',()=>[null,verdict(0),'Get-AuthenticodeSignature : access denied']],
      ['unparseable output',()=>[null,'not json','']]]){
      reply=result;await assert.rejects(verifyWindowsPackage(filename,pins),error=>error.code==='SIGNATURE_CHECK_UNAVAILABLE',name);
    }
    reply=()=>[null,verdict(2,null),''];
    await assert.rejects(verifyWindowsPackage(filename,pins),error=>/could not be verified/.test(error.message)&&error.code===undefined);
    reply=()=>[null,verdict(0,OTHER),''];
    await assert.rejects(verifyWindowsPackage(filename,pins),error=>/could not be verified/.test(error.message)&&error.code===undefined);
    reply=()=>[null,verdict(0),''];await verifyWindowsPackage(filename,pins);
    // A legacy manifest (no allow-list) is a refusal, decided before the signature tool runs.
    calls=0;await assert.rejects(verifyWindowsPackage(filename,undefined),error=>/names no publisher thumbprint/.test(error.message)&&error.code===undefined);assert.equal(calls,0);
  }finally{childProcess.execFile=realExecFile;Object.defineProperty(process,'platform',platform);delete require.cache[modulePath];}
});
