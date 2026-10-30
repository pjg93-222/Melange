'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const test=require('node:test');
const vm=require('node:vm');
const reply=()=>({schemaVersion:1,userSid:'S-1-5-21-100-200-300-1001',accountName:'FIXTURE\\User',sessionId:1,locked:false});
function fixture(value=reply(),platform='win32'){
 const module={exports:{}},calls=[],command={binary:'fixture-python',args:['fixture-bootstrap']};
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'..','windows-session.cjs'),'utf8'),{module,process:{platform},Object,
  require(name){if(name==='./backend-command.cjs')return {backendCommand:(resources,appId)=>{calls.push({resources,appId});return command;}};if(name==='./desktop-probe.cjs')return {desktopProbe:async(...args)=>{calls.push(args);return value;}};throw new Error(name);}});
 return {...module.exports,calls,command};
}
test('Windows bridge requests only native current-session identity without renderer claims',async()=>{
 const f=fixture(),value=await f.windowsSession('resources','terrier');
 assert.equal(value.userSid,reply().userSid);assert.equal(Object.isFrozen(value),true);
 assert.equal(f.calls[1][0],f.command);assert.equal(f.calls[1][1],'--desktop-windows-session');
 assert.equal(JSON.stringify(f.calls[1][2]),'{}');assert.equal(f.calls[1][3].timeout,15000);
});
test('lock status is preserved while malformed or service-session identities are refused',async()=>{
 assert.equal((await fixture({...reply(),locked:true}).windowsSession('r','melange')).locked,true);
 for(const value of [{...reply(),userSid:'claimed-user'},{...reply(),userSid:'S-1-5-18'},{...reply(),sessionId:0},{...reply(),locked:'false'},{...reply(),username:'claimed'},null]){
  await assert.rejects(fixture(value).windowsSession('r','mentat'),/could not be verified/);
 }
 for(const [app,platform] of [['unknown','win32'],['terrier','darwin']]){
  const f=fixture(reply(),platform);await assert.rejects(f.windowsSession('r',app),/unavailable/);assert.equal(f.calls.length,0);
 }
});
