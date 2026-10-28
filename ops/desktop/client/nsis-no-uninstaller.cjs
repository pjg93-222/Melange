'use strict';
// Adapt only the reviewed electron-builder 26.15.3 templates. A dependency
// change must be reviewed instead of silently restoring an uninstaller.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const PINNED=Object.freeze({
  'installer.nsi':'8811964416d122612c3e7601728af5d3f998d677918df829a4e8b4c739c8b9f8',
  'installSection.nsh':'74c4dbb4163cdd90ca4850b75d304e916235c882d6af7b5cdad63bffbc977072',
  'include/installer.nsh':'0e319437dd01dcbf911f3f48f664fde0cefbaef704f1cdb1739f63d563f5d4a0',
  'include/extractAppPackage.nsh':'e4174388a0f7a1df0b85a0742aa1ea7a4b2b18f9f29dccd6ef10a66212f68148'
});
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const quote=value=>'"'+value.replace(/\$/g,()=> '$$').replace(/"/g,()=> '$\\"')+'"';
const scriptPath=directory=>path.join(directory,'installer.no-uninstaller.nsi');
function replaceOnce(text,from,to){
  if(text.split(from).length!==2)throw new Error('Pinned NSIS adaptation no longer matches its template');
  return text.replace(from,()=>to);
}

// Nsis7z::Extract does not return a result. Never use the stack to restore
// OUTDIR: a blocked plugin can leave its archive argument on that stack.
const EXTRACTION=fs.readFileSync(path.join(__dirname,'nsis-no-uninstaller-extract.nsh'),'utf8');

function prepare({directory,templates=path.join(path.dirname(require.resolve('app-builder-lib/package.json')),'templates','nsis')}){
  directory=path.resolve(directory);templates=path.resolve(templates);
  const originals={};
  for(const [name,expected] of Object.entries(PINNED)){
    const bytes=fs.readFileSync(path.join(templates,name));
    if(sha(bytes)!==expected)throw new Error('Unreviewed NSIS template: '+name);
    originals[name]=bytes.toString('utf8').replace(/\r\n/g,'\n');
  }
  const generated=path.join(directory,'nsis-without-uninstaller');
  const include=path.join(generated,'include');
  let main=replaceOnce(originals['installer.nsi'],'!include "installSection.nsh"','!include '+quote(path.join(generated,'installSection.nsh')));
  main='; Generated from pinned electron-builder 26.15.3; no uninstaller build pass.\n!addincludedir '+quote(templates)+'\n!addincludedir '+quote(path.join(templates,'include'))+'\n'+main;
  let section=replaceOnce(originals['installSection.nsh'],'!include installer.nsh','!include '+quote(path.join(include,'installer.nsh')));
  section=replaceOnce(section,'!insertmacro uninstallOldVersion SHELL_CONTEXT\n!insertmacro handleUninstallResult SHELL_CONTEXT\n\n${if} $installMode == "all"\n  !insertmacro uninstallOldVersion HKEY_CURRENT_USER\n  !insertmacro handleUninstallResult HKEY_CURRENT_USER\n${endIf}','; Previous program folders remain intact; no old uninstaller is invoked.');
  section=replaceOnce(section,'!ifdef UNINSTALLER_ICON\n  File /oname=uninstallerIcon.ico "${UNINSTALLER_ICON}"\n!endif','; No uninstaller icon or executable is installed.');
  let installer=replaceOnce(originals['include/installer.nsh'],'!include "extractAppPackage.nsh"','!include '+quote(path.join(include,'extractAppPackage.nsh')));
  installer=replaceOnce(installer,'  File "/oname=${UNINSTALL_FILENAME}" "${UNINSTALLER_OUT_FILE}"','  ; This installer deliberately creates no uninstaller.');
  installer=replaceOnce(installer,'  StrCpy $2 "$INSTDIR\\${UNINSTALL_FILENAME}"\n  WriteRegStr SHELL_CONTEXT "${UNINSTALL_REGISTRY_KEY}" UninstallString \'"$2" $0\'\n  WriteRegStr SHELL_CONTEXT "${UNINSTALL_REGISTRY_KEY}" QuietUninstallString \'"$2" $0 /S\'',
    '  DeleteRegValue SHELL_CONTEXT "${UNINSTALL_REGISTRY_KEY}" UninstallString\n  DeleteRegValue SHELL_CONTEXT "${UNINSTALL_REGISTRY_KEY}" QuietUninstallString\n  WriteRegDWORD SHELL_CONTEXT "${UNINSTALL_REGISTRY_KEY}" NoRemove 1');
  installer=replaceOnce(installer,'  !ifdef UNINSTALLER_ICON\n    WriteRegStr SHELL_CONTEXT "${UNINSTALL_REGISTRY_KEY}" "DisplayIcon" "$INSTDIR\\uninstallerIcon.ico"\n  !else\n    WriteRegStr SHELL_CONTEXT "${UNINSTALL_REGISTRY_KEY}" "DisplayIcon" "$appExe,0"\n  !endif',
    '  WriteRegStr SHELL_CONTEXT "${UNINSTALL_REGISTRY_KEY}" "DisplayIcon" "$appExe,0"');
  const extraction=originals['include/extractAppPackage.nsh'];
  const start=extraction.indexOf('!macro extractUsing7za FILE\n');
  if(start<0||extraction.indexOf('!macro extractUsing7za FILE\n',start+1)>=0)throw new Error('Pinned extraction macro is missing or duplicated');
  const patchedExtraction=extraction.slice(0,start)+EXTRACTION+'\n';
  const outputs={
    'installer.no-uninstaller.nsi':main,
    'nsis-without-uninstaller/installSection.nsh':section,
    'nsis-without-uninstaller/include/installer.nsh':installer,
    'nsis-without-uninstaller/include/extractAppPackage.nsh':patchedExtraction
  };
  fs.mkdirSync(include,{recursive:true});
  for(const [name,text] of Object.entries(outputs))fs.writeFileSync(path.join(directory,name),text);
  fs.writeFileSync(path.join(directory,'nsis-no-uninstaller.provenance.json'),JSON.stringify({schemaVersion:1,mode:'native-without-uninstaller',electronBuilderVersion:'26.15.3',sourceTemplates:PINNED,generatedFiles:Object.fromEntries(Object.entries(outputs).map(([name,text])=>[name,sha(text)]))},null,2)+'\n');
  return scriptPath(directory);
}
module.exports={prepare,scriptPath,PINNED};
