'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const {EventEmitter,once}=require('node:events');
const {spawnSync,spawn}=require('node:child_process');
const activation=require('../installer-activation.cjs');
function fixture(t){
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'activation-observation-'));
  t.after(()=>{assert.equal(path.dirname(directory),path.resolve(os.tmpdir()));fs.rmSync(directory,{recursive:true,force:true});});
  const now=Date.now(),installerPath=path.join(directory,'mentat.exe'),target=path.join(directory,'Mentat-1.0.31');
  fs.writeFileSync(installerPath,'inert');
  const attempt=activation.createAttempt({appId:'mentat',version:'1.0.31',installerPath,target,now});
  const context={appId:'mentat',version:'1.0.31',nativeFiles:[installerPath],target,activatedAt:attempt.startedAt,now};
  const process={pid:1200,startedAt:new Date(now+1).toISOString(),installerPath};
  function receipt(values={}){
    const fields={schema:'1',app:attempt.appId,version:attempt.version,token:attempt.token,target:attempt.target,outcome:'complete',code:'0',...values};
    const text='\ufeff[activation]\r\n'+Object.entries(fields).map(([key,value])=>key+'='+value).join('\r\n')+'\r\n';
    fs.writeFileSync(activation.receiptPath(attempt),Buffer.from(text,'utf16le'));
  }
  return {directory,attempt,context,process,receipt};
}
test('dispatch binds only the verified installer, preserves spawning, and redacts its nonce',async t=>{
  const f=fixture(t),logs=[],calls=[];
  const updater={_logger:{info:value=>logs.push(value)},async spawnLog(command,args,...rest){this._logger.info(command+' '+args.join(' '));calls.push({command,args,rest});return true;}};
  const original=updater.spawnLog,restore=activation.bindDispatch(updater,f.attempt);
  assert.equal(await updater.spawnLog(f.attempt.installerPath,['--updated','/S'],{TEST:'value'},'ignore'),true);
  assert.deepEqual(calls[0].args,['--updated','/S','--desktop-activation='+f.attempt.token]);
  assert.deepEqual(calls[0].rest,[{TEST:'value'},'ignore']);assert.ok(logs.every(value=>!value.includes(f.attempt.token)));
  await updater.spawnLog(path.join(f.directory,'elevate.exe'),[f.attempt.installerPath,'--updated','/S']);
  assert.equal(calls[1].args.at(-1),'--desktop-activation='+f.attempt.token);
  assert.throws(()=>updater.spawnLog(path.join(f.directory,'other.exe'),[]),/differs/);
  assert.throws(()=>updater.spawnLog(f.attempt.installerPath,['--desktop-activation=another']),/Duplicate/);
  restore();assert.equal(updater.spawnLog,original);
});
test('a matched live installer stays running even beyond the ambiguous-attempt deadline',async t=>{
  const f=fixture(t),processes=async()=>[f.process];
  const active=await activation.observeAttempt(f.attempt,{...f.context,processes});assert.equal(active.status,'running');
  f.attempt.process=active.process;
  const long=await activation.observeAttempt(f.attempt,{...f.context,processes,now:f.context.now+activation.MAX_AMBIGUOUS_MS+1});
  assert.equal(long.status,'running');assert.equal(long.longRunning,true);
  const reused=await activation.observeAttempt(f.attempt,{...f.context,processes:async()=>[{...f.process,startedAt:new Date(f.context.now+5000).toISOString()}]});
  assert.equal(reused.status,'unknown','a recycled PID is not the recorded process');
});
test('completed receipt survives process exit and an old pinned app relaunch',async t=>{
  const f=fixture(t);f.receipt();
  const result=await activation.observeAttempt(f.attempt,{...f.context,now:f.context.now+activation.MAX_AMBIGUOUS_MS*2,processes:async()=>assert.fail('completion does not require a live process')});
  assert.deepEqual(result,{status:'complete',code:0});
});
test('completion written during process inspection is read before abandonment',async t=>{
  const f=fixture(t);
  const result=await activation.observeAttempt(f.attempt,{...f.context,now:f.context.now+activation.MAX_AMBIGUOUS_MS+1,processes:async()=>{f.receipt();return [];}});
  assert.equal(result.status,'complete');
});
test('explicit installer failure and genuinely abandoned attempt remain failures',async t=>{
  const f=fixture(t),processes=async()=>[];
  assert.equal((await activation.observeAttempt(f.attempt,{...f.context,processes})).status,'unknown');
  assert.equal((await activation.observeAttempt(f.attempt,{...f.context,processes,now:f.context.now+activation.MAX_AMBIGUOUS_MS+1})).status,'abandoned');
  f.receipt({outcome:'failed',code:'3'});
  assert.deepEqual(await activation.observeAttempt(f.attempt,{...f.context,processes}),{status:'failed',code:3});
});
test('malformed, cross-app, target, token and version receipts cannot prove completion',async t=>{
  const f=fixture(t);
  for(const values of [{app:'org.melange.desktop.terrier'},{version:'1.0.30'},{token:'b'.repeat(64)},{target:path.join(f.directory,'other')},{outcome:'complete',code:'3'},{extra:'field'}]){
    f.receipt(values);assert.throws(()=>activation.readReceipt(f.attempt));
    assert.equal((await activation.observeAttempt(f.attempt,{...f.context,processes:async()=>[]})).status,'unknown');
  }
  fs.writeFileSync(activation.receiptPath(f.attempt),'not an INI');assert.throws(()=>activation.readReceipt(f.attempt));
  assert.equal((await activation.observeAttempt(f.attempt,{...f.context,processes:async()=>[],now:f.context.now+activation.MAX_AMBIGUOUS_MS+1})).status,'abandoned');
  assert.equal((await activation.observeAttempt(null,f.context)).status,'abandoned');
});
test('process inspection uses only the authenticated fixed native observer and projects no arguments',async t=>{
  const f=fixture(t);let request,verified=false;
  const verify=(resources,appId)=>{assert.equal(resources,'resources');assert.equal(appId,'mentat');verified=true;return {binary:'pinned-python',args:['-I','-S','-B','fixed-probe.py']};};
  const probe=async(command,mode,input,options)=>{assert.equal(verified,true);request={command,mode,input,options};return [f.process];};
  assert.deepEqual(await activation.inspectProcesses(f.attempt,{verify,probe,resources:'resources',appId:'mentat',platform:'win32'}),[f.process]);
  assert.deepEqual(request.input,{installerPath:f.attempt.installerPath,token:f.attempt.token});
  assert.equal(request.mode,'--desktop-installer-processes');assert.equal(request.options.timeout,10000);assert.equal(request.options.limit,32768);
  assert.ok(!request.command.args.join(' ').includes(f.attempt.token));
  await assert.rejects(activation.inspectProcesses(f.attempt,{verify,probe:async()=>{throw new Error('WMI unavailable');},resources:'resources',appId:'mentat',platform:'win32'}),/WMI unavailable/);
  await assert.rejects(activation.inspectProcesses(f.attempt,{verify,probe:async()=>[{...f.process,commandLine:'forbidden'}],resources:'resources',appId:'mentat',platform:'win32'}),/Invalid Windows installer observation/);
});

// An inert fixture compiles the actual parser/receipt functions. It never
// extracts an application, writes a registry value, or creates a shortcut.
test('NSIS builtins write an atomic Unicode receipt and reject path-like nonce arguments',t=>{
  const source=fs.readFileSync(path.join(__dirname,'..','plugin-free-installer.nsi'),'utf8');
  const cache=path.join(process.env.LOCALAPPDATA||'','electron-builder','Cache'),candidates=[];
  if(process.env.ELECTRON_BUILDER_NSIS_DIR)candidates.push(path.join(process.env.ELECTRON_BUILDER_NSIS_DIR,'Bin','makensis.exe'));
  try{for(const name of fs.readdirSync(cache).filter(value=>/^nsis-\d/.test(value)))for(const version of fs.readdirSync(path.join(cache,name)))candidates.push(path.join(cache,name,version,'Bin','makensis.exe'));}catch{}
  const compiler=candidates.find(value=>fs.existsSync(value));if(process.platform!=='win32'||!compiler){t.skip('Windows NSIS compiler is unavailable');return;}
  const f=fixture(t),output=path.join(f.directory,'receipt-fixture.exe'),script=path.join(f.directory,'receipt-fixture.nsi');
  const quote=value=>'"'+value.replace(/\$/g,'$$$$').replace(/"/g,'$\\"')+'"';
  const fn=name=>{const match=new RegExp('Function '+name+'\\r?\\n[\\s\\S]*?FunctionEnd').exec(source);assert.ok(match,name);return match[0];};
  const init=fn('\\.onInit').split('  ReadRegStr $0')[0]+'FunctionEnd';
  const target=path.join(f.directory,'Unicode \u00e9 $ target');
  fs.writeFileSync(script,['Unicode true','RequestExecutionLevel user','SilentInstall silent','OutFile '+quote(output),'!define PF_APP_ID "org.melange.desktop.mentat"','!define PF_VERSION "1.0.31"',...source.match(/^Var .+$/gm),fn('pfAcceptActivation'),fn('pfAcceptToken'),fn('pfWriteActivation'),init,'Section','StrCpy $INSTDIR '+quote(target),'StrCpy $pfActivationOutcome "complete"','StrCpy $pfActivationCode "0"','Call pfWriteActivation','SectionEnd'].join('\n'));
  const built=spawnSync(compiler,['/INPUTCHARSET','UTF8','/V2',script],{encoding:'utf8',windowsHide:true,timeout:30000});assert.equal(built.status,0,built.stdout+'\n'+built.stderr);
  const run=spawnSync(output,['/S','--updated','--desktop-activation='+f.attempt.token],{encoding:'utf8',windowsHide:true,timeout:30000});assert.equal(run.status,0,run.stderr);
  const bound={...f.attempt,installerPath:output,target};assert.deepEqual(activation.readReceipt(bound),{status:'complete',code:0});
  assert.equal(fs.existsSync(activation.receiptPath(bound).replace(/\.ini$/,'.tmp')),false);
  const invalid='..\\invalid-'+Date.now(),before=fs.readdirSync(f.directory).sort();
  assert.equal(spawnSync(output,['/S','--desktop-activation='+invalid],{windowsHide:true,timeout:30000}).status,0);
  assert.deepEqual(fs.readdirSync(f.directory).sort(),before,'invalid nonce creates no path');
  assert.doesNotMatch(source,/\b(?:System|UAC|StdUtils|nsis7z)::|WriteUninstaller/);
  assert.ok(source.indexOf('StrCpy $pfActivationOutcome "complete"')>source.lastIndexOf('CreateShortCut'));
});
