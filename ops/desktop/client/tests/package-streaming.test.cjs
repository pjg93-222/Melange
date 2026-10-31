'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const crypto=require('node:crypto');
const fs=require('node:fs');
const http=require('node:http');
const os=require('node:os');
const path=require('node:path');
const {verifyPackageFile}=require('../trust.cjs');
const {verifiedFeed}=require('../updater.cjs');

function fixture(t){
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'desktop-package-stream-'));
  t.after(()=>fs.rmSync(directory,{recursive:true,force:true}));
  const bytes=Buffer.alloc(8*1024*1024+37,0x35);
  // Distinct bytes straddle the enlarged read boundaries and cover the partial final read.
  for(const offset of [0,4*1024*1024-1,4*1024*1024,8*1024*1024,bytes.length-1])bytes[offset]=offset%251;
  const filename=path.join(directory,'Terrier.exe');fs.writeFileSync(filename,bytes);
  const manifest={version:'1.0.26',issuedAt:'2026-10-28T00:00:00Z',package:{name:'Terrier.exe',size:bytes.length,
    sha256:crypto.createHash('sha256').update(bytes).digest('hex'),sha512:crypto.createHash('sha512').update(bytes).digest('base64')}};
  return {filename,manifest};
}

test('large cached packages retain exact signed size and both digest checks across read boundaries',async t=>{
  const {filename,manifest}=fixture(t);
  assert.equal(await verifyPackageFile(filename,manifest),filename);
  for(const change of [{size:manifest.package.size-1},{sha256:'0'.repeat(64)},{sha512:Buffer.alloc(64).toString('base64')}]){
    await assert.rejects(verifyPackageFile(filename,{...manifest,package:{...manifest.package,...change}}),{code:'PACKAGE_INTEGRITY'});
  }
  const fd=fs.openSync(filename,'r+');
  try{fs.writeSync(fd,Buffer.from([0xff]),0,1,4*1024*1024);}finally{fs.closeSync(fd);}
  await assert.rejects(verifyPackageFile(filename,manifest),{code:'PACKAGE_INTEGRITY'});
});

test('local update feed streams the complete large package and its partial final chunk',async t=>{
  const {filename,manifest}=fixture(t),feed=await verifiedFeed(manifest,filename);
  t.after(()=>feed.close());
  const result=await new Promise((resolve,reject)=>{
    const request=http.get(feed.url+manifest.package.name,{agent:false},response=>{
      const hash=crypto.createHash('sha512');let size=0;
      response.on('data',chunk=>{size+=chunk.length;hash.update(chunk);});
      response.on('error',reject);
      response.on('end',()=>resolve({status:response.statusCode,length:response.headers['content-length'],size,sha512:hash.digest('base64')}));
    });
    request.setTimeout(15000,()=>request.destroy(new Error('Local package stream timed out')));
    request.on('error',reject);
  });
  assert.equal(result.status,200);assert.equal(result.length,String(manifest.package.size));
  assert.equal(result.size,manifest.package.size);assert.equal(result.sha512,manifest.package.sha512);
});
