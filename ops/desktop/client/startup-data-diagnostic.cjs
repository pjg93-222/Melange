'use strict';
// A child log is not health. Only one context-bound native intake diagnostic
// can distinguish rejected external data from an otherwise unknown process exit.
const {StringDecoder}=require('node:string_decoder');
const {canonical}=require('./access-client.cjs');
const {dataStartupFailure}=require('./startup-failure.cjs');
const PREFIX='DESKTOP_DATA_BLOCKED ',MAX_LINE=8192;
function exact(value,keys){return value&&typeof value==='object'&&!Array.isArray(value)&&Object.keys(value).sort().join('|')===[...keys].sort().join('|');}
class StartupDataDiagnostic{
 constructor({appId,launchNonce,programFingerprint,sourceDigests,guard}){
  if(!['melange','mentat','terrier'].includes(appId)||typeof launchNonce!=='string'||!/^[A-Za-z0-9_-]{43}$/.test(launchNonce)||
     !/^[a-f0-9]{64}$/.test(programFingerprint)||!exact(sourceDigests,appId==='terrier'?['district']:Object.hasOwn(sourceDigests||{},'workspace')?['public','workspace']:['public'])||
     Object.values(sourceDigests).some(value=>!/^[a-f0-9]{64}$/.test(value))||typeof guard!=='function')throw new Error('Native startup diagnostic context is required.');
  this.expected={appId,launchNonce,programFingerprint,sourceDigests:structuredClone(sourceDigests)};this.guard=guard;this.decoder=new StringDecoder('utf8');
  this.pending='';this.discarding=false;this.markers=0;this.value=null;this.invalid=false;this.drained=false;this.healthy=false;
 }
 line(line){
  if(!line.startsWith(PREFIX))return;
  this.markers++;
  if(this.healthy||this.markers!==1||line.length>MAX_LINE){this.invalid=true;return;}
  try{
   const raw=line.slice(PREFIX.length),value=JSON.parse(raw);
   if(!exact(value,['schemaVersion','appId','launchNonce','programFingerprint','sourceDigests','reason'])||value.schemaVersion!==1||
      !['integrity','storage'].includes(value.reason)||canonical(value)!==raw||
      ['appId','launchNonce','programFingerprint'].some(key=>value[key]!==this.expected[key])||canonical(value.sourceDigests)!==canonical(this.expected.sourceDigests))throw new Error();
   this.value=value;
  }catch{this.invalid=true;}
 }
 push(bytes){
  if(this.drained)return;let text=this.decoder.write(bytes);
  while(text.length){
   const newline=text.indexOf('\n'),part=newline<0?text:text.slice(0,newline);
   if(!this.discarding){this.pending+=part;if(this.pending.length>MAX_LINE){if(this.pending.startsWith(PREFIX)){this.markers++;this.invalid=true;}this.pending='';this.discarding=true;}}
   if(newline<0)break;
   if(!this.discarding)this.line(this.pending.endsWith('\r')?this.pending.slice(0,-1):this.pending);
   this.pending='';this.discarding=false;text=text.slice(newline+1);
  }
 }
 end(){if(this.drained)return;this.push(Buffer.from(this.decoder.end()));if(!this.discarding&&this.pending)this.line(this.pending);this.pending='';this.drained=true;}
 markHealthy(){if(this.markers)throw new Error('Conflicting native startup diagnostic and health.');this.healthy=true;this.value=null;}
 blocked(){
  if(!this.drained||this.healthy||this.invalid||this.markers!==1||!this.value)return null;
  this.guard();return dataStartupFailure({reason:this.value.reason});
 }
}
function observeStartupData(child,context){
 const parser=new StartupDataDiagnostic(context);let close,end;const closed=new Promise(resolve=>{close=resolve;}),ended=new Promise(resolve=>{end=resolve;});
 child.once('close',close);
 if(child.stdout){child.stdout.on('data',bytes=>parser.push(bytes));child.stdout.once('end',()=>{parser.end();end(true);});child.stdout.once('error',()=>{parser.invalid=true;end(false);});child.stdout.once('close',()=>{if(!parser.drained)end(false);});}else end(false);
 return Object.freeze({markHealthy:()=>parser.markHealthy(),
  async blockedAfterExit({drainMs=2000,waitForExit=false}={}){
   if(!waitForExit&&child.exitCode==null&&child.signalCode==null)return null;
   let timer;try{const drained=await Promise.race([Promise.all([closed,ended]).then(([,ended])=>ended),new Promise(resolve=>{timer=setTimeout(()=>resolve(false),drainMs);})]);return drained?parser.blocked():null;}finally{clearTimeout(timer);}
  }
 });
}
module.exports={StartupDataDiagnostic,observeStartupData,PREFIX};
