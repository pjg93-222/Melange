'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {verifyNativeFiles}=require('../../packaging/verify_directory_release.cjs');
const {signPool,THUMBPRINT}=require('../release-signing.cjs');
function fixture(){const files=Array.from({length:9},(_,n)=>({item:{path:n?'native'+n+'.dll':'Melange.exe',sha256:String(n).repeat(64)},file:'/private/native'+n})),built=new Map(files.map(({item},n)=>[item.path,{sha256:item.sha256,thumbprint:n?'vendor':THUMBPRINT}]));return {files,built};}
test('final verifier checks every PE with at most four workers and preserves exact evidence',async()=>{
 const {files,built}=fixture();let active=0,maximum=0;const visited=[];
 const signing={signPool,THUMBPRINT,signFile:async(file,root,options)=>{assert.equal(root,'/private');assert.equal(options.verify,true);const n=files.findIndex(item=>item.file===file);assert.equal(options.owned,n===0);active++;maximum=Math.max(maximum,active);await new Promise(resolve=>setTimeout(resolve,5));visited.push(n);active--;return {sha256:files[n].item.sha256,thumbprint:n?'vendor':THUMBPRINT,timestamped:n===0,status:'Valid'};}};
 const result=await verifyNativeFiles(files,signing,'/private','Melange.exe',built);assert.equal(result.length,files.length);assert.equal(new Set(visited).size,files.length);assert.equal(maximum,4);assert.equal(active,0);
});
test('final verifier drains pending workers and propagates failure before returning evidence',async()=>{
 const {files,built}=fixture();let active=0;const visited=[];
 const signing={signPool,THUMBPRINT,signFile:async file=>{const n=files.findIndex(item=>item.file===file);active++;visited.push(n);try{await new Promise(resolve=>setTimeout(resolve,n?15:1));if(!n)throw new Error('signature failure');return {sha256:files[n].item.sha256,thumbprint:'vendor',timestamped:false,status:'Valid'};}finally{active--;}}};
 await assert.rejects(verifyNativeFiles(files,signing,'/private','Melange.exe',built),/signature failure/);assert.equal(active,0);assert.ok(visited.length<=4);
});
