'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const {spawnSync}=require('node:child_process');
const generator=require('../nsis-no-uninstaller.cjs');
const templates=path.join(path.dirname(require.resolve('app-builder-lib/package.json')),'templates','nsis');
function workspace(t){const directory=fs.mkdtempSync(path.join(os.tmpdir(),'native-no-uninstaller-'));t.after(()=>fs.rmSync(directory,{recursive:true,force:true}));return directory;}
function generated(t){const directory=workspace(t),script=generator.prepare({directory});return {directory,script,read:name=>fs.readFileSync(path.join(directory,name),'utf8')};}

test('actual pinned templates preserve installation but contain no uninstaller write, execution or registry command',t=>{
  const g=generated(t),section=g.read('nsis-without-uninstaller/installSection.nsh'),installer=g.read('nsis-without-uninstaller/include/installer.nsh');
  assert.match(fs.readFileSync(g.script,'utf8'),/!include "[^\n]*nsis-without-uninstaller[\\/]installSection\.nsh"/);
  assert.doesNotMatch(section,/!insertmacro (uninstallOldVersion|handleUninstallResult)/i);
  assert.doesNotMatch(installer,/File [^\n]*(UNINSTALL_FILENAME|UNINSTALLER_OUT_FILE)/);
  assert.doesNotMatch(installer,/WriteRegStr [^\n]*(?:Quiet)?UninstallString/);
  for(const key of ['UninstallString','QuietUninstallString'])assert.match(installer,new RegExp('DeleteRegValue [^\\n]* '+key+'\\n'));
  assert.match(installer,/WriteRegDWORD [^\n]* NoRemove 1/);
  assert.match(installer,/WriteRegStr [^\n]* InstallLocation "\$INSTDIR"/);
  for(const operation of ['CHECK_APP_RUNNING','installApplicationFiles','registryAddInstallInfo','addStartMenuLink','addDesktopLink','customInstall'])assert.ok(section.includes(operation),operation);
  assert.ok(section.indexOf('!insertmacro installApplicationFiles')<section.indexOf('!insertmacro customInstall'),'startup registration follows successful extraction');
  assert.doesNotMatch(installer,/RMDir\s+\/r|Delete "\$INSTDIR/,'old program folders are retained');
});

test('electron-builder custom-script branch never generates or signs an uninstaller',async t=>{
  require('app-builder-lib'); // Initialize the public entrypoint before the internal target's circular imports.
  const g=generated(t),{NsisTarget}=require('app-builder-lib/out/targets/nsis/NsisTarget');
  let selected;
  const fake={options:{script:g.script},packager:{getResource:async value=>(selected=value),signIf:()=>{throw new Error('uninstaller signing must not run');}},executeMakensis:()=>{throw new Error('uninstaller compiler pass must not run');}};
  const result=await NsisTarget.prototype.computeScriptAndSignUninstaller.call(fake,{}, {},'unused.exe','',[]);
  assert.equal(selected,g.script);assert.equal(result.isCustomScript,true);assert.equal(result.script,fs.readFileSync(g.script,'utf8'));
});

test('changed upstream template fails before producing a script',t=>{
  const directory=workspace(t),copy=path.join(directory,'templates');
  for(const name of Object.keys(generator.PINNED)){const file=path.join(copy,name);fs.mkdirSync(path.dirname(file),{recursive:true});fs.copyFileSync(path.join(templates,name),file);}
  fs.appendFileSync(path.join(copy,'include/installer.nsh'),'\n; upstream changed\n');
  const output=path.join(directory,'out');assert.throws(()=>generator.prepare({directory:output,templates:copy}),/Unreviewed NSIS template/);assert.equal(fs.existsSync(output),false);
});

function compiler(){
  const candidates=[];
  if(process.env.ELECTRON_BUILDER_NSIS_DIR)candidates.push(path.join(process.env.ELECTRON_BUILDER_NSIS_DIR,'Bin','makensis.exe'));
  const cache=path.join(process.env.LOCALAPPDATA||'','electron-builder','Cache');
  try{for(const group of fs.readdirSync(cache).filter(name=>/^nsis-\d/.test(name)))for(const version of fs.readdirSync(path.join(cache,group)))candidates.push(path.join(cache,group,version,'Bin','makensis.exe'));}catch{}
  return candidates.find(file=>fs.existsSync(file));
}
for(const mode of ['success','blocked-plugin','empty-extraction'])test('compiled extraction '+mode+' preserves destination and fails closed',t=>{
  const makensis=compiler();if(process.platform!=='win32'||!makensis){t.skip('pinned NSIS compiler unavailable');return;}
  const g=generated(t),target=path.join(g.directory,'program'),exe=path.join(g.directory,'fixture.exe');
  fs.mkdirSync(target);fs.writeFileSync(path.join(target,'keep-user-data.txt'),'untouched');
  const source=g.read('nsis-without-uninstaller/include/extractAppPackage.nsh');
  let macro=source.slice(source.indexOf('!macro extractUsing7za FILE'));
  const call='Nsis7z::Extract "${FILE}"';assert.equal(macro.split(call).length,2);
  const stub=mode==='success'?[
    'FileOpen $0 "$PLUGINSDIR\\7z-out\\Melange.exe" w','FileWrite $0 "fixture"','FileClose $0',
    'CreateDirectory "$PLUGINSDIR\\7z-out\\resources"','FileOpen $0 "$PLUGINSDIR\\7z-out\\resources\\app.asar" w','FileWrite $0 "asar"','FileClose $0'
  ].join('\n'):mode==='blocked-plugin'?'Push "archive-argument-left-on-stack"\nSetErrors':'ClearErrors';
  macro=macro.replace(call,()=>stub);
  const text=['Unicode true','!include LogicLib.nsh','!define APP_EXECUTABLE_FILENAME "Melange.exe"','Name "Extraction fixture"','OutFile "'+exe+'"','RequestExecutionLevel user','SilentInstall silent',macro,'Section','InitPluginsDir','StrCpy $INSTDIR "'+target+'"','SetOutPath $INSTDIR','!insertmacro extractUsing7za "unused.7z"','SectionEnd'].join('\n');
  const script=path.join(g.directory,'fixture.nsi');fs.writeFileSync(script,text);
  const build=spawnSync(makensis,['/V2',script],{encoding:'utf8',windowsHide:true});assert.equal(build.status,0,build.stdout+build.stderr);
  const run=spawnSync(exe,['/S'],{windowsHide:true,timeout:30000});assert.equal(run.status,mode==='success'?0:2,String(run.error));
  assert.equal(fs.readFileSync(path.join(target,'keep-user-data.txt'),'utf8'),'untouched');
  assert.equal(fs.existsSync(path.join(target,'Melange.exe')),mode==='success');assert.equal(fs.existsSync(path.join(target,'resources','app.asar')),mode==='success');
  assert.equal(fs.readdirSync(target).some(name=>/^uninstall/i.test(name)),false);
});
