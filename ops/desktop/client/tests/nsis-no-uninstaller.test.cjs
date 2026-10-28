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
  const utilities=g.read('nsis-without-uninstaller/include/installUtil.nsh');
  assert.doesNotMatch(utilities,/^(?:Function|!macro) (?:GetInQuotes|GetFileParent|handleUninstallResult|uninstallOldVersion)\b/m);
  for(const name of ['moveFile','copyFile','setIsTryToKeepShortcuts'])assert.match(utilities,new RegExp('!macro '+name+'\\b'));
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

test('complete generated assisted installer compiles with warnings as errors; original unused closure fails',async t=>{
  const makensis=compiler(),cache=path.join(process.env.LOCALAPPDATA||'','electron-builder','Cache','nsis-resources-3.4.1');
  const resource=fs.existsSync(cache)&&fs.readdirSync(cache).map(name=>path.join(cache,name,'plugins','x86-unicode')).find(file=>fs.existsSync(file));
  if(process.platform!=='win32'||!makensis||!resource){t.skip('pinned NSIS compiler/resources unavailable');return;}
  require('app-builder-lib');
  const {NsisScriptGenerator}=require('app-builder-lib/out/targets/nsis/nsisScriptGenerator');
  const {LangConfigurator,createAddLangsMacro,addCustomMessageFileInclude}=require('app-builder-lib/out/targets/nsis/nsisLang');
  const g=generated(t),header=new NsisScriptGenerator(),languages=new LangConfigurator({multiLanguageInstaller:false});
  header.include(path.join(templates,'include','StdUtils.nsh'));
  header.addIncludeDir(path.join(templates,'include'));header.addPluginDir('x86-unicode',resource);
  header.flags(['updated','force-run','keep-shortcuts','no-desktop-shortcut','delete-app-data','allusers','currentuser']);
  createAddLangsMacro(header,languages);
  let index=0;const packager={getTempFile:async()=>path.join(g.directory,'messages-'+index++ + '.nsh')};
  await addCustomMessageFileInclude('messages.yml',packager,header,languages);
  await addCustomMessageFileInclude('assistedMessages.yml',packager,header,languages);
  const layout=path.join(g.directory,'installer.generated.nsh');
  fs.writeFileSync(layout,require('../install-layout.cjs').nsisInclude({product:'Melange',app:'melange',version:'1.0.21',installerNsh:path.join(__dirname,'..','installer.nsh')}));
  header.include(layout);
  const archive=path.join(g.directory,'fixture.7z');fs.writeFileSync(archive,'compile-only payload; never extracted or executed');
  const definitions={APP_ID:'org.melange.desktop.compile-fixture',APP_GUID:'00000000-0000-4000-8000-000000000001',UNINSTALL_APP_KEY:'00000000-0000-4000-8000-000000000001',
    PRODUCT_NAME:'Melange',PRODUCT_FILENAME:'Melange',APP_FILENAME:'Melange',APP_DESCRIPTION:'Compile fixture',VERSION:'1.0.21',PROJECT_DIR:g.directory,
    BUILD_RESOURCES_DIR:g.directory,APP_PACKAGE_NAME:'melange-desktop',APP_64:archive,APP_64_NAME:'fixture.7z',APP_64_UNPACKED_SIZE:'1',
    APP_INSTALLER_STORE_FILE:'melange-desktop-updater\\installer.exe',COMPRESSION_METHOD:'7z',HIDE_RUN_AFTER_FINISH:null,
    MULTIUSER_INSTALLMODE_ALLOW_ELEVATION:null,INSTALL_MODE_PER_ALL_USERS_REQUIRED:null,SHORTCUT_NAME:'Melange',UNINSTALL_DISPLAY_NAME:'Melange 1.0.21',ESTIMATED_SIZE:'1',COMPRESS:'auto',UNINSTALLER_OUT_FILE:null};
  const script=path.join(g.directory,'complete.nsi'),exe=path.join(g.directory,'compile-only.exe');
  const prelude=['Unicode true','OutFile "'+exe+'"','VIProductVersion 1.0.21.0',
    ...['ProductName','ProductVersion','LegalCopyright','FileDescription','FileVersion'].map(name=>'VIAddVersionKey /LANG=1033 '+name+' "'+(name.endsWith('Version')?'1.0.21':'Compile fixture')+'"'),
    ...Object.entries(definitions).map(([name,value])=>'!define '+name+(value===null?'':' "'+value+'"'))].join('\n');
  fs.writeFileSync(script,prelude+'\n'+header.build()+fs.readFileSync(g.script,'utf8'));
  // Match electron-builder's stdin/cwd invocation so its multiUser.nsh wins over
  // NSIS's unrelated, case-insensitively named standard MultiUser.nsh.
  const compile=()=>spawnSync(makensis,['-WX','-V2','-INPUTCHARSET','UTF8','-'],{cwd:templates,input:fs.readFileSync(script,'utf8'),encoding:'utf8',windowsHide:true,timeout:60000});
  const success=compile();assert.equal(success.status,0,success.stdout+success.stderr);assert.doesNotMatch(success.stdout+success.stderr,/warning\s+\d+:/i);
  assert.ok(fs.statSync(exe).size>0); // Never execute the compiled installer.
  fs.copyFileSync(path.join(templates,'include','installUtil.nsh'),path.join(g.directory,'nsis-without-uninstaller','include','installUtil.nsh'));
  const regression=compile();assert.notEqual(regression.status,0);assert.match(regression.stdout+regression.stderr,/warning\s+6010/);
});
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
