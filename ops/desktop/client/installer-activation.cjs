'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {desktopProbe}=require('./desktop-probe.cjs');
const {verifyProbeRuntime}=require('./signature-probe-runtime.cjs');
const {appDefinition}=require('./apps.cjs');
const MAX_AMBIGUOUS_MS=30*60*1000,MAX_RECEIPT_BYTES=8192;
const TOKEN=/^[0-9a-f]{64}$/;
const samePath=(a,b)=>typeof a==='string'&&typeof b==='string'&&path.win32.resolve(a).toLowerCase()===path.win32.resolve(b).toLowerCase();
const flag=token=>'--desktop-activation='+token;
const receiptPath=attempt=>path.join(path.dirname(attempt.installerPath),'.desktop-activation-'+attempt.token+'.ini');

// These observations only describe progress. Neither a process nor an unsigned
// receipt authorizes a package, launches it, or confirms a healthy installation.
function createAttempt({appId,version,installerPath,target,now=Date.now()}){
  if(!path.isAbsolute(installerPath)||!path.isAbsolute(target)||!/^\d+\.\d+\.\d+$/.test(version)||!Number.isSafeInteger(now))throw new Error('Invalid installer activation identity');
  return {schemaVersion:1,token:crypto.randomBytes(32).toString('hex'),appId:appDefinition(appId).applicationId,version,
    installerPath:path.resolve(installerPath),target:path.resolve(target),startedAt:new Date(now).toISOString()};
}
function validAttempt(attempt,{appId,version,nativeFiles,target,activatedAt}){
  return attempt?.schemaVersion===1&&TOKEN.test(attempt.token)&&attempt.appId===appDefinition(appId).applicationId&&attempt.version===version&&
    Array.isArray(nativeFiles)&&nativeFiles.length===1&&samePath(attempt.installerPath,nativeFiles[0])&&samePath(attempt.target,target)&&
    attempt.startedAt===activatedAt&&Number.isFinite(Date.parse(attempt.startedAt));
}
function bindDispatch(updater,attempt){
  const original=updater.spawnLog;
  if(typeof original!=='function')throw new Error('The native updater cannot identify its installer attempt.');
  const argument=flag(attempt.token);
  function wrapped(command,args=[],...rest){
    const own=samePath(command,attempt.installerPath)||(path.win32.basename(command).toLowerCase()==='elevate.exe'&&samePath(args[0],attempt.installerPath));
    if(!own)throw new Error('Native installer dispatch differs from the verified attempt.');
    if(args.some(value=>typeof value==='string'&&value.startsWith('--desktop-activation=')))throw new Error('Duplicate installer activation argument');
    // electron-updater logs arguments synchronously on entry. Keep the random
    // correlation token out of those logs while retaining its original spawner.
    const logger=this._logger;
    if(logger)this._logger=new Proxy(logger,{get(object,key){return key==='info'?(...values)=>object.info(...values.map(value=>typeof value==='string'?value.replaceAll(argument,'--desktop-activation=[redacted]'):value)):Reflect.get(object,key);}});
    try{return original.call(this,command,[...args,argument],...rest);}finally{if(logger)this._logger=logger;}
  }
  updater.spawnLog=wrapped;
  return()=>{if(updater.spawnLog===wrapped)updater.spawnLog=original;};
}

// Only the authenticated, fixed native observer sees process command lines;
// it returns matching path/token/creation-time identities, never raw arguments.
async function inspectProcesses(attempt,{resources,appId,probe=desktopProbe,verify=verifyProbeRuntime,platform=process.platform}={}){
  if(platform!=='win32'||!TOKEN.test(attempt?.token)||!path.isAbsolute(attempt?.installerPath||''))throw new Error('Windows installer observation unavailable');
  const command=verify(resources,appId);
  const rows=await probe(command,'--desktop-installer-processes',{installerPath:attempt.installerPath,token:attempt.token},{timeout:10000,limit:32768});
  if(!Array.isArray(rows)||rows.length>8||rows.some(row=>!row||Object.keys(row).sort().join('|')!=='installerPath|pid|startedAt'||
      !Number.isSafeInteger(row.pid)||row.pid<=0||typeof row.startedAt!=='string'||!Number.isFinite(Date.parse(row.startedAt))||!samePath(row.installerPath,attempt.installerPath)))
    throw new Error('Invalid Windows installer observation');
  return rows;
}
function readReceipt(attempt,{readFile=fs.readFileSync,lstat=fs.lstatSync,realpath=fs.realpathSync.native}={}){
  const filename=receiptPath(attempt);let stat;
  try{stat=lstat(filename);}catch(error){if(error.code==='ENOENT')return null;throw error;}
  if(!stat.isFile()||stat.isSymbolicLink()||stat.size>MAX_RECEIPT_BYTES||stat.size<4||!samePath(realpath(filename),filename)||stat.mtimeMs<Date.parse(attempt.startedAt)-1000)throw new Error('Invalid installer progress receipt');
  const bytes=readFile(filename);
  if(bytes[0]!==255||bytes[1]!==254||bytes.length%2)throw new Error('Invalid installer progress encoding');
  const lines=bytes.subarray(2).toString('utf16le').split(/\r?\n/).filter(Boolean),values={};
  if(lines.shift()!=='[activation]')throw new Error('Invalid installer progress section');
  for(const line of lines){const at=line.indexOf('=');if(at<1)throw new Error('Invalid installer progress field');const key=line.slice(0,at),value=line.slice(at+1);if(Object.hasOwn(values,key)||/[\x00-\x1f]/.test(value))throw new Error('Invalid installer progress field');values[key]=value;}
  if(Object.keys(values).sort().join('|')!=='app|code|outcome|schema|target|token|version'||values.schema!=='1'||values.app!==attempt.appId||values.version!==attempt.version||values.token!==attempt.token||!samePath(values.target,attempt.target)||
    !((values.outcome==='complete'&&values.code==='0')||(values.outcome==='failed'&&['2','3','4','5','6'].includes(values.code))))throw new Error('Installer progress identity mismatch');
  return {status:values.outcome,code:Number(values.code)};
}
function matchingProcess(value,attempt){
  const created=Date.parse(value?.startedAt),began=Date.parse(attempt.startedAt);
  return Number.isSafeInteger(value?.pid)&&value.pid>0&&typeof value.startedAt==='string'&&Number.isFinite(created)&&created>=began&&samePath(value.installerPath,attempt.installerPath)&&
    (!attempt.process||(value.pid===attempt.process.pid&&created===Date.parse(attempt.process.startedAt)));
}
async function observeAttempt(attempt,{appId,version,nativeFiles,target,activatedAt,now=Date.now(),processes=inspectProcesses,receipt=readReceipt}={}){
  if(!validAttempt(attempt,{appId,version,nativeFiles,target,activatedAt}))return {status:'abandoned'};
  const age=now-Date.parse(attempt.startedAt),bounded=Number.isFinite(age)&&age>=0&&age<=MAX_AMBIGUOUS_MS;
  let result,receiptError=false;
  try{result=receipt(attempt);}catch{receiptError=true;}
  // Completion is written before optional new-app launch, and outlives the
  // process. Absence of a live process therefore never overrules completion.
  if(result?.status==='complete')return result;
  if(result?.status==='failed')return result;
  try{
    const rows=await processes(attempt),matches=rows.filter(value=>matchingProcess(value,attempt));
    if(matches.length===1&&rows.length===1)return {status:'running',process:{pid:matches[0].pid,startedAt:matches[0].startedAt},longRunning:age>MAX_AMBIGUOUS_MS};
    if(rows.length||receiptError)return {status:bounded?'unknown':'abandoned'};
    // The installer may have committed its receipt and exited during the
    // process query. Re-read before concluding that it disappeared.
    try{result=receipt(attempt);}catch{return {status:bounded?'unknown':'abandoned'};}
    if(result?.status==='complete'||result?.status==='failed')return result;
    return {status:bounded?'unknown':'abandoned'};
  }catch{return {status:bounded?'unknown':'abandoned'};}
}
module.exports={createAttempt,bindDispatch,observeAttempt,inspectProcesses,readReceipt,receiptPath,MAX_AMBIGUOUS_MS};
