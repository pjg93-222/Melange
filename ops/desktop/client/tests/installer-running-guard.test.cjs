'use strict';
// An inert fixture compiles the actual running-instance guard and receipt writer
// from the installer template. It extracts only sentinel files into a temporary
// folder and never writes a registry value or shortcut.
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const {once}=require('node:events');
const {spawnSync,spawn}=require('node:child_process');
const activation=require('../installer-activation.cjs');
const source=fs.readFileSync(path.join(__dirname,'..','plugin-free-installer.nsi'),'utf8');
const SENTINELS=['LICENSE.electron.txt','ffmpeg.dll'],BACKEND='resources\\runtime\\mentat\\python\\python.exe';

function compiler(){
  const candidates=[];
  if(process.env.ELECTRON_BUILDER_NSIS_DIR)candidates.push(path.join(process.env.ELECTRON_BUILDER_NSIS_DIR,'Bin','makensis.exe'));
  const cache=path.join(process.env.LOCALAPPDATA||'','electron-builder','Cache');
  try{for(const group of fs.readdirSync(cache).filter(name=>/^nsis-\d/.test(name)))for(const version of fs.readdirSync(path.join(cache,group)))candidates.push(path.join(cache,group,version,'Bin','makensis.exe'));}catch{}
  return candidates.find(file=>fs.existsSync(file));
}
function fixture(t){
  const makensis=compiler(),ping=path.join(process.env.SystemRoot||'C:\\Windows','System32','PING.EXE');
  if(process.platform!=='win32'||!makensis||!fs.existsSync(ping)){t.skip('Windows NSIS compiler or PING.EXE is unavailable');return null;}
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'installer-running-guard-')),target=path.join(directory,'Mentat $ target'),payload=path.join(directory,'payload');
  fs.mkdirSync(target);fs.mkdirSync(payload);
  const live=path.join(target,'Mentat.exe'),old=new Date('2024-01-02T03:04:05Z'),children=[];
  t.after(async()=>{for(const child of children)if(child.exitCode===null&&child.signalCode===null){const exited=once(child,'exit');child.kill();await exited;}fs.rmSync(directory,{recursive:true,force:true});});
  const names=[...SENTINELS,'Mentat.exe'],before={};
  for(const name of SENTINELS){fs.writeFileSync(path.join(target,name),'old '+name);}
  fs.copyFileSync(ping,live);
  for(const name of names){fs.utimesSync(path.join(target,name),old,old);const info=fs.statSync(path.join(target,name));before[name]={bytes:fs.readFileSync(path.join(target,name)),mtimeMs:info.mtimeMs};}
  for(const name of names)fs.writeFileSync(path.join(payload,name),'new '+name);
  const quote=value=>'"'+value.replace(/\$/g,'$$$$').replace(/"/g,'$\\"')+'"';
  const fn=name=>{const match=new RegExp('Function '+name+'\\r?\\n[\\s\\S]*?FunctionEnd').exec(source);assert.ok(match,name);return match[0];};
  const init=fn('\\.onInit').split('  ReadRegStr $0')[0]+'  StrCpy $INSTDIR '+quote(target)+'\n  Call pfRequireNotRunning\nFunctionEnd';
  const output=path.join(directory,'guard-fixture.exe'),script=path.join(directory,'guard-fixture.nsi');
  fs.writeFileSync(script,['Unicode true','RequestExecutionLevel user','SilentInstall silent','OutFile '+quote(output),
    '!define PF_PRODUCT "Mentat"','!define PF_APP_ID "org.melange.desktop.mentat"','!define PF_VERSION "1.0.37"','!define PF_EXE "Mentat.exe"','!define PF_BACKEND_EXE '+quote(BACKEND),
    ...source.match(/^Var .+$/gm),fn('pfAcceptActivation'),fn('pfAcceptToken'),fn('pfWriteActivation'),fn('pfRequireNotRunning'),init,
    'Section','SetOverwrite on','SetOutPath "$INSTDIR"',...names.map(name=>'File /oname='+name+' '+quote(path.join(payload,name))),'SectionEnd'].join('\n'));
  const built=spawnSync(makensis,['/INPUTCHARSET','UTF8','/V2','/WX',script],{encoding:'utf8',windowsHide:true,timeout:60000});assert.equal(built.status,0,built.stdout+'\n'+built.stderr);
  const attempt=activation.createAttempt({appId:'mentat',version:'1.0.37',installerPath:output,target,now:Date.now()});
  const run=()=>spawnSync(output,['/S','--desktop-activation='+attempt.token],{windowsHide:true,timeout:30000});
  const start=async file=>{const child=spawn(file,['-n','30','127.0.0.1'],{windowsHide:true,stdio:'ignore'});children.push(child);await once(child,'spawn');return child;};
  const kill=async child=>{const exited=once(child,'exit');child.kill();await exited;};
  const unchanged=()=>{for(const name of names){const info=fs.statSync(path.join(target,name));assert.deepEqual(fs.readFileSync(path.join(target,name)),before[name].bytes,name);assert.equal(info.mtimeMs,before[name].mtimeMs,name);}};
  const replaced=()=>{for(const name of names)assert.equal(fs.readFileSync(path.join(target,name),'utf8'),'new '+name);};
  return {target,live,attempt,run,start,kill,unchanged,replaced};
}

test('silent install refuses a running target without partial overwrite',async t=>{
  const f=fixture(t);if(!f)return;
  const child=await f.start(f.live);
  const result=f.run();
  assert.equal(result.status,6,String(result.error));
  f.unchanged();
  assert.deepEqual(activation.readReceipt(f.attempt),{status:'failed',code:6});
  assert.ok(child.exitCode===null&&child.signalCode===null,'the running instance is not disturbed');
});

test('silent install refuses a running backend interpreter without partial overwrite',async t=>{
  const f=fixture(t);if(!f)return;
  const backend=path.join(f.target,...BACKEND.split('\\'));fs.mkdirSync(path.dirname(backend),{recursive:true});
  fs.copyFileSync(path.join(process.env.SystemRoot||'C:\\Windows','System32','PING.EXE'),backend);
  await f.start(backend);
  const result=f.run();
  assert.equal(result.status,6,String(result.error));
  f.unchanged();
  assert.deepEqual(activation.readReceipt(f.attempt),{status:'failed',code:6});
});

test('guard passes after the process exits',async t=>{
  const f=fixture(t);if(!f)return;
  const child=await f.start(f.live);
  assert.equal(f.run().status,6);f.unchanged();
  await f.kill(child);
  const result=f.run();
  assert.equal(result.status,0,String(result.error));
  f.replaced();
});
