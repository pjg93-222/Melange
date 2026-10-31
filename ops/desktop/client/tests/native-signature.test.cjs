"use strict";
const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {verdict,PIN}=require('./fixtures/native-signature-verdict.cjs');
const OTHER='1111111111111111111111111111111111111111';
let probeResult,probeFailure,integrityFailure,calls=[];
require('../signature-probe-runtime.cjs').verifyProbeRuntime=(resources,appId)=>{
 if(integrityFailure)throw integrityFailure;
 assert.equal(resources,'fixture-resources');assert.equal(appId,'mentat');
 return {binary:'trusted-python',args:['-I','-S','-B','fixed-probe.py']};
};
require('../desktop-probe.cjs').desktopProbe=async(command,mode,payload,options)=>{
 calls.push({command,mode,payload,options});if(probeFailure)throw probeFailure;return probeResult;
};
const {verifyWindowsPackage,verifySignatureResult,signatureTimeoutMs,PUBLISHER_PIN_ENFORCE}=require('../native-signature.cjs');
const filename='C:/Test/Package.exe';
test('native Windows success and only pinned self-signed root policy are accepted',()=>{
 verifySignatureResult(verdict(filename),filename,[PIN]);
 verifySignatureResult(verdict(filename,4),filename,[PIN]);
 for(const status of [1,2,3])assert.throws(()=>verifySignatureResult(verdict(filename,status),filename,[PIN]),/could not be verified/);
 for(const result of [verdict(filename,0,OTHER),{...verdict(filename),path:'C:/Other.exe'},
  {...verdict(filename),wintrustStatus:0x800B0101},{...verdict(filename,4),chainErrors:0x40},
  {...verdict(filename,4),counterSignerErrors:true},{...verdict(filename,4),validAtVerificationTime:false},
  {...verdict(filename,4),selfSigned:false},{...verdict(filename,4),certificateError:0x800B010C},
  {...verdict(filename),verdict:'refused'},{...verdict(filename),extra:true},{}])
  assert.throws(()=>verifySignatureResult(result,filename,[PIN]),/could not be verified/);
 verifySignatureResult({...verdict(filename),chainErrors:0x01000040},filename,[PIN]);
});
test('manifest and client pin both remain mandatory; the manifest cannot widen authority',()=>{
 assert.equal(PUBLISHER_PIN_ENFORCE,true);
 for(const list of [null,[],[PIN.toLowerCase()]])assert.throws(()=>verifySignatureResult(verdict(filename),filename,list),/names no publisher thumbprint/);
 assert.throws(()=>verifySignatureResult(verdict(filename),filename,[OTHER]),/does not name the pinned publisher/);
 assert.throws(()=>verifySignatureResult(verdict(filename,0,OTHER),filename,[PIN,OTHER]),/could not be verified/);
});
test('missing verdict and interpreter integrity failures differ from valid signature refusals',async t=>{
 const temporary=fs.mkdtempSync(path.join(os.tmpdir(),'native-signature-js-'));
 t.after(()=>fs.rmSync(temporary,{recursive:true,force:true}));
 const file=path.join(temporary,'Package.exe');fs.writeFileSync(file,'fixture');
 const options={resources:'fixture-resources',appId:'mentat'};
 const platform=Object.getOwnPropertyDescriptor(process,'platform');Object.defineProperty(process,'platform',{...platform,value:'win32'});
 try{
  probeResult=verdict(file);await verifyWindowsPackage(file,[PIN],options);
  assert.deepEqual(calls.at(-1).command.args,['-I','-S','-B','fixed-probe.py']);
  assert.equal(calls.at(-1).mode,'--desktop-windows-signature');
  assert.deepEqual(calls.at(-1).payload,{path:path.resolve(file)});
  for(const failure of [new Error('spawn refused'),new Error('timeout'),new Error('invalid response')]){
   probeFailure=failure;await assert.rejects(verifyWindowsPackage(file,[PIN],options),e=>e.code==='SIGNATURE_CHECK_UNAVAILABLE');
  }
  probeFailure=null;probeResult={};await assert.rejects(verifyWindowsPackage(file,[PIN],options),e=>e.code==='SIGNATURE_CHECK_UNAVAILABLE');
  const count=calls.length;integrityFailure=new Error('interpreter changed');
  await assert.rejects(verifyWindowsPackage(file,[PIN],options),e=>e.code==='SIGNATURE_CHECK_UNAVAILABLE');assert.equal(calls.length,count);
  integrityFailure=null;probeResult=verdict(file,3);
  await assert.rejects(verifyWindowsPackage(file,[PIN],options),e=>e.code===undefined&&/could not be verified/.test(e.message));
  const before=calls.length;await assert.rejects(verifyWindowsPackage(file,[],options));assert.equal(calls.length,before);
 }finally{Object.defineProperty(process,'platform',platform);probeFailure=null;integrityFailure=null;}
});
test('size-scaled timeout remains bounded',()=>{
 const MiB=1024**2;
 for(const [bytes,ms] of [[0,60000],[1,90000],[100*MiB,90000],[100*MiB+1,120000],[578e6,240000],[1e12,600000]])assert.equal(signatureTimeoutMs(bytes),ms);
});
