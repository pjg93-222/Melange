; All runtime instructions below are NSIS builtins. No MUI, plugin, elevation,
; uninstaller, external extraction helper or temporary plugin directory is used.
Unicode true
RequestExecutionLevel user
Name "${PF_PRODUCT} ${PF_VERSION}"
OutFile "${PF_OUTPUT}"
Icon "${PF_ICON}"
LoadLanguageFile "${PF_LANGUAGE}"
VIProductVersion "${PF_VERSION}.0"
VIAddVersionKey /LANG=1033 "ProductName" "${PF_PRODUCT}"
VIAddVersionKey /LANG=1033 "FileDescription" "${PF_PRODUCT} installer"
VIAddVersionKey /LANG=1033 "FileVersion" "${PF_VERSION}"
VIAddVersionKey /LANG=1033 "ProductVersion" "${PF_VERSION}"
VIAddVersionKey /LANG=1033 "LegalCopyright" "Melange Systems"
; Compress each file before adding it to the compiler datablock. A solid build
; accumulates the raw program and exceeds this compiler's 2 GiB mapping limit.
SetCompressor ${PF_COMPRESSION}
!if "${PF_COMPRESSION}" == "lzma"
  SetCompressorDictSize 8
!endif
SetDatablockOptimize on
ShowInstDetails show
AutoCloseWindow false
Page instfiles

Var pfUpdated
Var pfForceRun
Var pfToken
Var pfTokenIndex
Var pfPosition
Var pfQuoted
Var pfActivation
Var pfActivationOutcome
Var pfActivationCode

; The nonce is a correlation value, never authorization. Only an exact 64-hex
; token can name a receipt beside this installer; no caller-supplied path is used.
Function pfAcceptActivation
  StrCpy $0 $pfToken 21
  StrCmp $0 "--desktop-activation=" 0 done
  StrCpy $0 $pfToken "" 21
  StrLen $1 $0
  StrCmp $1 "64" 0 done
  StrCpy $2 0
  character:
    StrCpy $3 $0 1 $2
    StrCmp $3 "" valid
    StrCpy $4 0
  digit:
    StrCpy $5 "0123456789abcdef" 1 $4
    StrCmp $5 "" done
    StrCmp $3 $5 next_character
    IntOp $4 $4 + 1
    Goto digit
  next_character:
    IntOp $2 $2 + 1
    Goto character
  valid:
    StrCpy $pfActivation $0
  done:
FunctionEnd

; Builtins only. A fresh UTF-16LE INI is completed under a temporary name, then
; renamed atomically. Readers reject partial/mismatched receipts. The receipt
; reports progress only; the application still verifies its signed installer and
; requires healthy startup before confirming an update.
Function pfWriteActivation
  StrCmp $pfActivation "" done
  IfFileExists "$EXEDIR\.desktop-activation-$pfActivation.tmp" done
  ClearErrors
  FileOpen $0 "$EXEDIR\.desktop-activation-$pfActivation.tmp" w
  IfErrors done
  FileWriteByte $0 255
  FileWriteByte $0 254
  FileClose $0
  IfErrors done
  WriteINIStr "$EXEDIR\.desktop-activation-$pfActivation.tmp" "activation" "schema" "1"
  WriteINIStr "$EXEDIR\.desktop-activation-$pfActivation.tmp" "activation" "app" "${PF_APP_ID}"
  WriteINIStr "$EXEDIR\.desktop-activation-$pfActivation.tmp" "activation" "version" "${PF_VERSION}"
  WriteINIStr "$EXEDIR\.desktop-activation-$pfActivation.tmp" "activation" "token" "$pfActivation"
  WriteINIStr "$EXEDIR\.desktop-activation-$pfActivation.tmp" "activation" "target" "$INSTDIR"
  WriteINIStr "$EXEDIR\.desktop-activation-$pfActivation.tmp" "activation" "outcome" "$pfActivationOutcome"
  WriteINIStr "$EXEDIR\.desktop-activation-$pfActivation.tmp" "activation" "code" "$pfActivationCode"
  IfErrors done
  ; A launch error may replace this same attempt's completed-progress receipt.
  Delete "$EXEDIR\.desktop-activation-$pfActivation.ini"
  Rename "$EXEDIR\.desktop-activation-$pfActivation.tmp" "$EXEDIR\.desktop-activation-$pfActivation.ini"
  done:
FunctionEnd

; Parse complete command-line tokens with builtin string operations. Skip the
; executable token and accept quoted flags, without matching flag prefixes.
Function pfAcceptToken
  StrCmp $pfToken "" done
  StrCmp $pfTokenIndex "0" next
  StrCmp $pfToken "--updated" 0 force
    StrCpy $pfUpdated "1"
  force:
  StrCmp $pfToken "--force-run" 0 next
    StrCpy $pfForceRun "1"
  next:
  Call pfAcceptActivation
  IntOp $pfTokenIndex $pfTokenIndex + 1
  StrCpy $pfToken ""
  done:
FunctionEnd

Function .onInit
  SetShellVarContext current
  StrCpy $pfUpdated "0"
  StrCpy $pfForceRun "0"
  StrCpy $pfActivation ""
  StrCpy $pfToken ""
  StrCpy $pfTokenIndex "0"
  StrCpy $pfPosition "0"
  StrCpy $pfQuoted "0"
  parse:
    StrCpy $0 $CMDLINE 1 $pfPosition
    StrCmp $0 "" parsed
    IntOp $pfPosition $pfPosition + 1
    StrCmp $0 '$\"' quote
    StrCmp $pfQuoted "1" append
    StrCmp $0 " " separator
    StrCmp $0 "$\t" separator append
  quote:
    IntOp $pfQuoted $pfQuoted ^ 1
    Goto parse
  separator:
    Call pfAcceptToken
    Goto parse
  append:
    StrCpy $pfToken "$pfToken$0"
    Goto parse
  parsed:
    Call pfAcceptToken
  ReadRegStr $0 HKCU "Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders" "${PF_DOWNLOADS_GUID}"
  ExpandEnvStrings $0 $0
  StrCmp $0 "" 0 downloads
    StrCpy $0 "$PROFILE\Downloads"
  downloads:
  StrCpy $INSTDIR "$0\${PF_ROOT}\${PF_FOLDER}"
  StrLen $1 $INSTDIR
  IntCmp $1 ${PF_MAX_DIRECTORY} ready ready too_long
  too_long:
    StrCpy $pfActivationOutcome "failed"
    StrCpy $pfActivationCode "2"
    Call pfWriteActivation
    MessageBox MB_OK|MB_ICONSTOP "The install folder path is too long for Windows:$\r$\n$INSTDIR$\r$\nUse a shorter Downloads location or tell IT this path." /SD IDOK
    SetErrorLevel 2
    Quit
  ready:
FunctionEnd

Section "${PF_PRODUCT}"
  SetShellVarContext current
  SetOverwrite on
  SetDetailsPrint both
  DetailPrint "Installing ${PF_PRODUCT} program files..."
  ; Keep current-file status and progress without inserting tens of thousands
  ; of rows into the details list. NSIS recommends textonly for many small files.
  SetDetailsPrint textonly
  ClearErrors
  SetOutPath "$INSTDIR"
  IfErrors extraction_failed
  ; Overlay exclusions are checked for ambiguous nested names by the packager.
  File /r /x "${PF_EXE}" /x "app.asar" "${PF_PROGRAM}\*"
  IfErrors extraction_failed
  SetOutPath "$INSTDIR"
  IfErrors extraction_failed
  File /oname=${PF_EXE} "${PF_EXECUTABLE_SOURCE}"
  IfErrors extraction_failed
  SetOutPath "$INSTDIR\resources"
  IfErrors extraction_failed
  File /oname=app.asar "${PF_ASAR_SOURCE}"
  IfErrors extraction_failed
  SetOutPath "$INSTDIR"
  ; Only a fully extracted version can become the next-login update receiver.
  SetDetailsPrint both
  DetailPrint "Preparing automatic updates..."
  ClearErrors
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "${PF_APP_ID}" '$\"$INSTDIR\${PF_EXE}$\" --desktop-updater'
  IfErrors registration_failed
  WriteRegStr HKCU "Software\${PF_APP_ID}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "Software\${PF_APP_ID}" "Version" "${PF_VERSION}"
  IfErrors registration_failed
  ; Update existing shortcuts, retaining the user's choice to delete a link.
  DetailPrint "Updating application shortcuts..."
  StrCmp $pfUpdated "1" update_start start_link
  update_start:
    IfFileExists "$SMPROGRAMS\${PF_PRODUCT}.lnk" start_link desktop
  start_link:
    ClearErrors
    CreateShortCut "$SMPROGRAMS\${PF_PRODUCT}.lnk" "$INSTDIR\${PF_EXE}" "" "$INSTDIR\${PF_EXE}" 0
    IfErrors registration_failed
  desktop:
    StrCmp $pfUpdated "1" update_desktop desktop_link
  update_desktop:
    IfFileExists "$DESKTOP\${PF_PRODUCT}.lnk" desktop_link baseline
  desktop_link:
    ClearErrors
    CreateShortCut "$DESKTOP\${PF_PRODUCT}.lnk" "$INSTDIR\${PF_EXE}" "" "$INSTDIR\${PF_EXE}" 0
    IfErrors registration_failed
  baseline:
    ; Best effort only. Silent/update installs do not copy their own installer.
    IfSilent launch
    StrCmp $pfUpdated "1" launch
    DetailPrint "Preparing recovery..."
    ClearErrors
    CreateDirectory "$LOCALAPPDATA\${PF_APP_ID}\baseline\${PF_VERSION}"
    CopyFiles /SILENT "$EXEPATH" "$LOCALAPPDATA\${PF_APP_ID}\baseline\${PF_VERSION}\$EXEFILE"
  launch:
    StrCpy $pfActivationOutcome "complete"
    StrCpy $pfActivationCode "0"
    Call pfWriteActivation
    ClearErrors
    StrCmp $pfForceRun "1" 0 complete
    DetailPrint "Starting ${PF_PRODUCT}..."
    Exec '$\"$INSTDIR\${PF_EXE}$\" --updated'
    IfErrors launch_failed
  complete:
    DetailPrint "${PF_PRODUCT} installation is complete."
    SetErrorLevel 0
    Goto done
  extraction_failed:
    StrCpy $pfActivationOutcome "failed"
    StrCpy $pfActivationCode "3"
    Call pfWriteActivation
    SetDetailsPrint both
    DetailPrint "Installation stopped while writing program files."
    MessageBox MB_OK|MB_ICONSTOP "${PF_PRODUCT} could not write its program files. No new login receiver has been registered. Close this installer and ask IT to check the blocked file or folder." /SD IDOK
    SetErrorLevel 3
    Abort
  registration_failed:
    StrCpy $pfActivationOutcome "failed"
    StrCpy $pfActivationCode "4"
    Call pfWriteActivation
    MessageBox MB_OK|MB_ICONSTOP "${PF_PRODUCT} was extracted, but Windows could not register its per-user login receiver." /SD IDOK
    SetErrorLevel 4
    Abort
  launch_failed:
    StrCpy $pfActivationOutcome "failed"
    StrCpy $pfActivationCode "5"
    Call pfWriteActivation
    MessageBox MB_OK|MB_ICONSTOP "${PF_PRODUCT} was installed, but Windows could not start it." /SD IDOK
    SetErrorLevel 5
    Abort
  done:
SectionEnd
