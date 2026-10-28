'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const {spawnSync}=require('node:child_process');
const layout=require('../install-layout.cjs');
const source=fs.readFileSync(path.join(__dirname,'..','installer.nsh'),'utf8');

function macro(name){
  const match=new RegExp('^!macro '+name+'\\b[^\\n]*\\n([\\s\\S]*?)^!macroend','m').exec(source);
  assert.ok(match,'macro '+name+' exists');return match[1];
}
const code=text=>text.split('\n').map(line=>line.replace(/;.*$/,'').trimEnd()).filter(Boolean).join('\n');

test('preInit is skipped in the build-time uninstaller pass and uses no plugin before the temp folder moves',()=>{
  const body=code(macro('preInit'));
  assert.match(body,/^\s*!ifndef BUILD_UNINSTALLER\n[\s\S]*\n\s*!endif$/,'wrapped in !ifndef BUILD_UNINSTALLER');
  const copy=body.indexOf('UnsafeStrCpy $TEMP'),init=body.indexOf('InitPluginsDir'),firstPlugin=body.indexOf('::');
  assert.ok(copy>=0&&init>copy,'UnsafeStrCpy $TEMP precedes InitPluginsDir');
  assert.ok(firstPlugin>init,'the first plugin call follows InitPluginsDir');
  const before=body.slice(0,init);
  for(const forbidden of ['${isUpdated}','GetDParameter','System::','StdUtils','nsExec::','UAC::'])assert.ok(!before.includes(forbidden),forbidden+' before InitPluginsDir');
  assert.match(body,/SetEnvironmentVariable\(t "TEMP", t "\$TEMP"\)/);assert.match(body,/SetEnvironmentVariable\(t "TMP", t "\$TEMP"\)/);
  assert.ok(!body.includes('--updated'),'all installs use the same guarded setup directory');
  assert.match(body,/\$R7 > \$\{DL_MAX_SETUP\}/);assert.match(body,/SetErrorLevel 2\n\s*Quit/,'over-long setup paths fail closed');
});

test('the Downloads root is resolved without a plugin, from the User Shell Folders value',()=>{
  const body=code(macro('dlRoot'));
  assert.match(body,/ReadRegStr \$R0 HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\User Shell Folders" "\$\{DL_KNOWN_FOLDER\}"/);
  assert.match(body,/ExpandEnvStrings \$R0 \$R0/);assert.match(body,/\$PROFILE\\Downloads/);assert.ok(!body.includes('::'));
});

test('every install/update/rollback chooses its own version folder and refuses an over-long path',()=>{
  const body=code(macro('dlDecideInstdir'));
  assert.ok(body.includes('StrCpy $INSTDIR "$R0\\${DL_APP_FOLDER}"'));
  assert.ok(!body.includes('isUpdated')&&!body.includes('$R9'),'legacy and Downloads updates use the same fresh-version choice');
  assert.match(body,/\$R2 > \$\{DL_MAX_DIR\}/);assert.match(body,/SetErrorLevel 2\n\s*Quit/);
  assert.match(code(macro('customInit')),/^\s*!insertmacro dlDecideInstdir$/m);
});

test('B1: the install-mode page is forced per-user and the folder choice is re-applied after the pages',()=>{
  assert.match(code(macro('customInstallMode')),/^\s*StrCpy \$isForceCurrentInstall "1"$/m);
  const after=code(macro('customPageAfterChangeDir'));
  assert.match(after,/Function dlReforceInstdir\n\s*!insertmacro dlDecideInstdir\n\s*Abort\n\s*FunctionEnd\n\s*Page custom dlReforceInstdir/);
});

test('L2: a stale or missing generated include fails the compile',()=>{
  assert.match(source,/!ifndef DL_VERSION\n\s*!error/);assert.match(source,/!if "\$\{DL_VERSION\}" != "\$\{VERSION\}"\n\s*!error/);
});

test('successful per-user installation registers the new background receiver without any uninstaller command',()=>{
  const body=macro('customInstall');
  assert.ok(body.includes('WriteRegStr HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Run" "${APP_ID}" \'"$INSTDIR\\${APP_EXECUTABLE_FILENAME}" --desktop-updater\''));
  assert.ok(body.indexOf('WriteRegStr HKCU')>body.indexOf('${If} $installMode == "CurrentUser"'));
  assert.ok(!body.includes('UninstallString'));
  assert.ok(!source.includes('!macro customUnInstall'));
  assert.doesNotMatch(code(source),/RMDir\s+\/r/,'no legacy program/profile/cache is recursively removed');
  assert.ok(body.includes('${IfNot} ${isUpdated}'),'the interactive baseline copy remains');
});

test('installer.nsh keeps its original line endings and no unexpected CR',()=>{assert.ok(!source.includes('\r'));});

function findMakensis(){
  const candidates=[];
  if(process.env.ELECTRON_BUILDER_NSIS_DIR)candidates.push(path.join(process.env.ELECTRON_BUILDER_NSIS_DIR,'Bin','makensis.exe'));
  const cache=path.join(process.env.LOCALAPPDATA||'','electron-builder','Cache');
  try{for(const group of fs.readdirSync(cache).filter(name=>/^nsis-\d/.test(name)))for(const version of fs.readdirSync(path.join(cache,group)))candidates.push(path.join(cache,group,version,'Bin','makensis.exe'));}catch{}
  return candidates.find(file=>fs.existsSync(file));
}

function harness(t){
  const makensis=findMakensis();
  if(process.platform!=='win32'||!makensis){t.skip('makensis is not installed');return null;}
  const work=fs.mkdtempSync(path.join(os.tmpdir(),'dl-nsis-'));t.after(()=>fs.rmSync(work,{recursive:true,force:true}));
  const header=(fake,max,extra={})=>['Unicode true','!define VERSION "1.0.19"','!define DL_VERSION "'+(extra.dlVersion||'1.0.19')+'"','!define DL_TEST_ROOT "'+fake+'"','!define DL_ROOT_NAME "MelangeApplications"','!define DL_UPDATES_NAME "updates"',
    '!define DL_APP_FOLDER "Melange-1.0.19"','!define DL_SETUP_FOLDER "melange-setup"','!define DL_CACHE_FOLDER "melange"','!define DL_KNOWN_FOLDER "'+layout.LAYOUT.downloadsKnownFolder+'"',
    '!define DL_MAX_DIR '+(max.dir??layout.maxDirectory()),'!define DL_MAX_SETUP '+(max.setup??layout.maxSetup()),'!define APP_ID "org.melange.test.dlharness"','!define APP_EXECUTABLE_FILENAME "Melange.exe"','!include LogicLib.nsh',
    // stand-in for electron-builder's StdUtils-based ${isUpdated}: same --updated switch, script-only
    '!include FileFunc.nsh','!macro _isUpdated _a _b _t _f','  ${GetParameters} $8','  ClearErrors','  ${GetOptions} $8 "--updated" $7','  IfErrors `${_f}` `${_t}`','!macroend','!define isUpdated `"" isUpdated ""`',
    'Var isForceCurrentInstall','Var installMode','!include "'+path.join(__dirname,'..','installer.nsh')+'"'];
  const compile=(name,lines)=>{
    const script=path.join(work,name+'.nsi');fs.writeFileSync(script,lines.join('\r\n')+'\r\n');
    return spawnSync(makensis,['/V2',script],{encoding:'utf8',windowsHide:true});
  };
  return {work,makensis,header,compile};
}
const read=log=>Object.fromEntries(fs.readFileSync(log,'utf8').split(/\r?\n/).filter(Boolean).map(line=>[line.slice(0,line.indexOf('=')),line.slice(line.indexOf('=')+1)]));

test('compiled installer logic: TEMP move, folder choice (including a Downloads path with a space), and the over-long cases',t=>{
  const h=harness(t);if(!h)return;
  const {work}=h,fake=path.join(work,'Down loads'),rootDir=path.join(fake,'MelangeApplications'),pending=path.join(rootDir,'updates','melange','pending');
  const old=path.join(work,'old Programs','Melange');
  const build=(name,max)=>{
    const log=path.join(work,name+'.log'),exe=path.join(work,name+'.exe');
    const compiled=h.compile(name,[...h.header(fake,max),'Name "dl-harness"','OutFile "'+exe+'"','RequestExecutionLevel user','SilentInstall silent','InstallDir "$LOCALAPPDATA\\dl-harness-unused"',
      '!insertmacro customPageAfterChangeDir', // compiles the hidden re-force page and its function
      'Function .onInit','  !insertmacro preInit','  StrCpy $0 $PLUGINSDIR','  StrCpy $INSTDIR "'+old+'"','  !insertmacro customInit','  StrCpy $1 $INSTDIR',
      '  StrCpy $INSTDIR "$LOCALAPPDATA\\Programs\\Melange"  ; what setInstallModePerUser does on leaving the mode page','  !insertmacro dlDecideInstdir',
      '  !insertmacro customInstallMode','  FileOpen $9 "'+log+'" w','  FileWrite $9 "PLUGINSDIR=$0$\\r$\\nTEMP=$TEMP$\\r$\\nFIRST=$1$\\r$\\nAFTERPAGE=$INSTDIR$\\r$\\nFORCE=$isForceCurrentInstall$\\r$\\n"','  FileClose $9','  Quit','FunctionEnd','Section','SectionEnd']);
    assert.equal(compiled.status,0,compiled.stdout+compiled.stderr);
    return (args,exeDir)=>{
      const env={...process.env,TEMP:path.join(work,'realtemp'),TMP:path.join(work,'realtemp')};fs.mkdirSync(env.TEMP,{recursive:true});fs.rmSync(log,{force:true});
      let target=exe;if(exeDir){fs.mkdirSync(exeDir,{recursive:true});target=path.join(exeDir,name+'.exe');fs.copyFileSync(exe,target);}
      const run=spawnSync(target,args,{env,windowsHide:true});
      assert.equal(run.status,2,'Quit in .onInit exits 2; got '+run.status+' '+run.error);
      return fs.existsSync(log)?{...read(log),realTemp:env.TEMP}:null;
    };
  };
  const setup=path.join(rootDir,'updates','melange-setup').toLowerCase(),want=path.join(rootDir,'Melange-1.0.19');
  const run=build('normal',{setup:250,dir:250}); // the temp dir here is longer than a real user's budget; the comparisons are what is under test
  const first=run(['/S']);
  assert.ok(first.PLUGINSDIR.toLowerCase().startsWith(setup+'\\'),'manual install: plugins load under the Downloads setup folder (path has a space): '+first.PLUGINSDIR);
  assert.equal(first.TEMP.toLowerCase(),setup);assert.equal(first.FIRST,want,'manual install is forced into the per-version folder');
  assert.equal(first.AFTERPAGE,want,'and re-forced after the mode page reset it');assert.equal(first.FORCE,'1');
  const inPlace=run(['--updated','/S']);
  assert.ok(inPlace.PLUGINSDIR.toLowerCase().startsWith(setup+'\\'),'legacy update uses the guarded setup directory');
  assert.equal(inPlace.FIRST,want,'legacy update chooses the new version folder');
  const fromLayout=run(['--updated','/S'],pending);
  assert.ok(fromLayout.PLUGINSDIR.toLowerCase().startsWith(setup+'\\'),'an update installer running from <root>\\updates\\<app>\\pending moves TEMP without any /D');
  assert.equal(fromLayout.FIRST,want,'and chooses <App>-<its version> itself, spaces included');
  assert.equal(fromLayout.AFTERPAGE,want,'the post-page re-force repeats the choice for updates');
  const elsewhereInRoot=run(['--updated','/S'],path.join(rootDir,'Melange-1.0.18'));
  assert.ok(elsewhereInRoot.PLUGINSDIR.toLowerCase().startsWith(setup+'\\'),'an update launched from an older folder still uses the guarded setup directory');
  assert.equal(elsewhereInRoot.FIRST,want,'and chooses the new version folder');
  const manual=run(['/S','/D='+path.join(work,'elsewhere')]);
  assert.ok(manual.PLUGINSDIR.toLowerCase().startsWith(setup+'\\'),'a non-updated run always moves TEMP');
  // Both updates and manual installs refuse an over-long new folder.
  const tiny=build('tinydir',{setup:250,dir:10});
  assert.equal(tiny(['--updated','/S'],pending),null,'update with an over-long target is refused');
  assert.equal(tiny(['/S']),null,'manual install with an over-long target is refused');
  // A too-long setup folder is refused before plugin loading.
  const noMove=build('toolong',{setup:10,dir:250})(['/S']);
  assert.equal(noMove,null);
  assert.equal(fs.existsSync(path.join(rootDir,'updates','melange-setup')),true,'NSIS removes its ns*.tmp, leaving the empty setup folder for the sweep');
});

test('a stale generated include (different version) fails the compile',t=>{
  const h=harness(t);if(!h)return;
  const stale=h.compile('stale',[...h.header(path.join(h.work,'x'),{},{dlVersion:'1.0.18'}),'Name "s"','OutFile "'+path.join(h.work,'s.exe')+'"','Section','SectionEnd']);
  assert.notEqual(stale.status,0);assert.match(stale.stdout+stale.stderr,/stale/);
});

test('compiled silent update registers its new receiver even without launching the app',t=>{
  const h=harness(t);if(!h)return;
  const fake=path.join(h.work,'receiver'),rootDir=path.join(fake,'MelangeApplications'),target=path.join(rootDir,'Melange-1.0.19'),log=path.join(h.work,'receiver.log'),exe=path.join(h.work,'receiver.exe');
  fs.mkdirSync(target,{recursive:true});
  const lines=[...h.header(fake,{dir:250,setup:250}),'Name "receiver fixture"','OutFile "'+exe+'"','RequestExecutionLevel user','SilentInstall silent',
    'Section','StrCpy $installMode "CurrentUser"','StrCpy $INSTDIR "'+target+'"','!insertmacro customInstall',
    'ReadRegStr $R5 HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Run" "${APP_ID}"',
    'DeleteRegValue HKCU "Software\\Microsoft\\Windows\\CurrentVersion\\Run" "${APP_ID}"',
    'FileOpen $9 "'+log+'" w','FileWrite $9 "$R5"','FileClose $9','SectionEnd'];
  const compiled=h.compile('receiver',lines);assert.equal(compiled.status,0,compiled.stdout+compiled.stderr);
  try {
    const run=spawnSync(exe,['--updated','/S'],{windowsHide:true,timeout:30000});assert.equal(run.status,0,String(run.error));
    assert.equal(fs.readFileSync(log,'utf8'),'"'+path.join(target,'Melange.exe')+'" --desktop-updater');
    assert.equal(fs.existsSync(path.join(target,'Melange.exe')),false,'fixture registered the receiver without launching an application');
  } finally {
    spawnSync('reg.exe',['delete','HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run','/v','org.melange.test.dlharness','/f'],{windowsHide:true,stdio:'ignore'});
  }
});
