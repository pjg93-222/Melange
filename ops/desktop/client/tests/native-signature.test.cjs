'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {verifySignatureResult,PUBLISHER_PIN_ENFORCE}=require('../native-signature.cjs');
const fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const tempPackage=bytes=>{const filename=path.join(fs.mkdtempSync(path.join(os.tmpdir(),'native-signature-')),'Package.exe');fs.writeFileSync(filename,Buffer.alloc(bytes));return filename;};
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
test('T18 (D-328): with enforcement on, the signer must equal the client-pinned thumbprint AND be on the manifest allow-list',()=>{
  const filename='C:\Test\Package.exe',signed=thumbprint=>({status:0,thumbprint,path:filename}),on={enforce:true};
  verifySignatureResult(signed(PIN),filename,[PIN],on);
  verifySignatureResult(signed(PIN.toLowerCase()),filename,[PIN],on);
  // A manifest that names another publisher (even alone, even as the signer) cannot widen the client pin.
  for(const [signer,pins] of [[OTHER,[OTHER]],[OTHER,[PIN,OTHER]],[PIN,[OTHER]]])
    assert.throws(()=>verifySignatureResult(signed(signer),filename,pins,on),/could not be verified|does not name the pinned publisher thumbprint/);
  for(const status of [2,3])assert.throws(()=>verifySignatureResult({...signed(PIN),status},filename,[PIN],on),/could not be verified/);
  assert.throws(()=>verifySignatureResult({...signed(PIN),path:'C:\Other\Package.exe'},filename,[PIN],on),/could not be verified/);
});
test('T18 (Paul 2026-10-26): the shipped default is warn-only for 1.0.19 (flip PUBLISHER_PIN_ENFORCE in the next release)',()=>{
  assert.equal(PUBLISHER_PIN_ENFORCE,false);
});
test('T18 warn-only: a pin mismatch warns and proceeds while enforcement is off; the allow-list and release-signing checks still refuse',()=>{
  const filename='C:\Test\Package.exe',signed=thumbprint=>({status:0,thumbprint,path:filename}),off={enforce:false};
  const run=(result,pins)=>{const warnings=[];verifySignatureResult(result,filename,pins,{...off,warn:message=>warnings.push(message)});return warnings;};
  // The pin matches: no warning.
  assert.deepEqual(run(signed(PIN),[PIN]),[]);
  assert.deepEqual(run(signed(PIN),[OTHER,PIN]),[]);
  // Manifest does not name the pin (signer is on the manifest list): proceeds with a warning.
  assert.match(run(signed(OTHER),[OTHER])[0],/does not name the pinned publisher certificate.*next release will refuse/);
  // Manifest names the pin but the installer is signed by another listed publisher: proceeds with a warning.
  assert.match(run(signed(OTHER),[PIN,OTHER])[0],/signed by 1111.*not the pinned publisher certificate/);
  // Not warn-only for the existing checks: a signer outside the manifest list, a refused status, a path mismatch, or no list still throws.
  assert.throws(()=>run(signed(OTHER),[PIN]),/could not be verified/);
  for(const status of [2,3])assert.throws(()=>run({...signed(PIN),status},[PIN]),/could not be verified/);
  assert.throws(()=>run({...signed(PIN),path:'C:\Other\Package.exe'},[PIN]),/could not be verified/);
  assert.throws(()=>run(signed(PIN),[]),/names no publisher thumbprint/);
  // The module default (off) behaves the same without options, and console.warn is the log.
  const logged=[],realWarn=console.warn;console.warn=message=>logged.push(message);
  try{verifySignatureResult(signed(OTHER),filename,[OTHER]);}finally{console.warn=realWarn;}
  assert.equal(logged.length,1);
});
test('T18 flip: the same mismatches that warn while off block once enforcement is on',()=>{
  const filename='C:\Test\Package.exe',signed=thumbprint=>({status:0,thumbprint,path:filename});
  for(const [signer,pins] of [[OTHER,[OTHER]],[OTHER,[PIN,OTHER]]]){
    verifySignatureResult(signed(signer),filename,pins,{enforce:false});
    assert.throws(()=>verifySignatureResult(signed(signer),filename,pins,{enforce:true}),/could not be verified|does not name the pinned publisher thumbprint/);
  }
});
test('signature tool failures without a verdict are tagged; a parsed refusal is not',async()=>{
  const childProcess=require('node:child_process'),realExecFile=childProcess.execFile,platform=Object.getOwnPropertyDescriptor(process,'platform');
  const filename=tempPackage(1),pins=[PIN],modulePath=require.resolve('../native-signature.cjs');
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
test('the Authenticode timeout scales with installer size: 60 s + 30 s per started 100 MiB, bounded to 60 s..10 min',()=>{
  const {signatureTimeoutMs}=require('../native-signature.cjs'),MIB=1024*1024;
  for(const [bytes,ms] of [[0,60000],[-1,60000],[NaN,60000],[undefined,60000],[1,90000],[100*MIB,90000],[100*MIB+1,120000],
    [578e6,240000],[1700*MIB,570000],[1700*MIB+1,600000],[1e12,600000],[Infinity,600000]])
    assert.equal(signatureTimeoutMs(bytes),ms,String(bytes));
});
test('a slow signature probe within the size-scaled limit is accepted; one past it is refused with the elapsed time',async t=>{
  const childProcess=require('node:child_process'),realExecFile=childProcess.execFile,platform=Object.getOwnPropertyDescriptor(process,'platform');
  const filename=tempPackage(1),pins=[PIN],modulePath=require.resolve('../native-signature.cjs');
  // Simulated powershell taking probeMs; past options.timeout it is killed exactly as execFile does (killed, SIGTERM).
  let probeMs,limits=[];
  childProcess.execFile=(file,args,options,callback)=>{
    limits.push(options.timeout);
    if(probeMs<options.timeout)setTimeout(()=>callback(null,JSON.stringify({status:0,path:filename,thumbprint:PIN}),''),probeMs);
    else setTimeout(()=>callback(Object.assign(new Error('timed out'),{killed:true,signal:'SIGTERM'}),'',''),options.timeout);
    return {stdin:{on(){},end(){}}};
  };
  Object.defineProperty(process,'platform',{...platform,value:'win32'});delete require.cache[modulePath];
  t.mock.timers.enable({apis:['setTimeout','Date']});
  try{
    const {verifyWindowsPackage}=require('../native-signature.cjs');
    probeMs=46000;let pending=verifyWindowsPackage(filename,pins);t.mock.timers.tick(46000);await pending;
    probeMs=95000;pending=verifyWindowsPackage(filename,pins);t.mock.timers.tick(90000);
    await assert.rejects(pending,error=>error.code==='SIGNATURE_CHECK_UNAVAILABLE'&&error.elapsedMs===90000&&
      /failed after 90\.0 s \(limit 90\.0 s, timed out\)/.test(error.message));
    assert.deepEqual(limits,[90000,90000]);
  }finally{childProcess.execFile=realExecFile;Object.defineProperty(process,'platform',platform);delete require.cache[modulePath];}
});
test('flip guard (T18, Paul 2026-10-26): PUBLISHER_PIN_ENFORCE must be true once the client version is past 1.0.19',()=>{
  const parts=version=>version.split('-')[0].split('.').map(Number),[a,b,c]=parts(require('../package.json').version),[x,y,z]=parts('1.0.19');
  const pastWarnOnlyRelease=a>x||(a===x&&(b>y||(b===y&&c>z)));
  if(pastWarnOnlyRelease)assert.equal(PUBLISHER_PIN_ENFORCE,true,'flip PUBLISHER_PIN_ENFORCE to true: the warn-only release (1.0.19) has shipped');
});
