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
  IntOp $pfTokenIndex $pfTokenIndex + 1
  StrCpy $pfToken ""
  done:
FunctionEnd

Function .onInit
  SetShellVarContext current
  StrCpy $pfUpdated "0"
  StrCpy $pfForceRun "0"
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
  ; Update existing shortcuts, retaining the user's choice to delete a link.
  DetailPrint "Updating application shortcuts..."
  StrCmp $pfUpdated "1" update_start start_link
  update_start:
    IfFileExists "$SMPROGRAMS\${PF_PRODUCT}.lnk" start_link desktop
  start_link:
    CreateShortCut "$SMPROGRAMS\${PF_PRODUCT}.lnk" "$INSTDIR\${PF_EXE}" "" "$INSTDIR\${PF_EXE}" 0
  desktop:
    StrCmp $pfUpdated "1" update_desktop desktop_link
  update_desktop:
    IfFileExists "$DESKTOP\${PF_PRODUCT}.lnk" desktop_link baseline
  desktop_link:
    CreateShortCut "$DESKTOP\${PF_PRODUCT}.lnk" "$INSTDIR\${PF_EXE}" "" "$INSTDIR\${PF_EXE}" 0
  baseline:
    ; Best effort only. Silent/update installs do not copy their own installer.
    IfSilent launch
    StrCmp $pfUpdated "1" launch
    DetailPrint "Preparing recovery..."
    ClearErrors
    CreateDirectory "$LOCALAPPDATA\${PF_APP_ID}\baseline\${PF_VERSION}"
    CopyFiles /SILENT "$EXEPATH" "$LOCALAPPDATA\${PF_APP_ID}\baseline\${PF_VERSION}\$EXEFILE"
  launch:
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
    SetDetailsPrint both
    DetailPrint "Installation stopped while writing program files."
    MessageBox MB_OK|MB_ICONSTOP "${PF_PRODUCT} could not write its program files. No new login receiver has been registered. Close this installer and ask IT to check the blocked file or folder." /SD IDOK
    SetErrorLevel 3
    Abort
  registration_failed:
    MessageBox MB_OK|MB_ICONSTOP "${PF_PRODUCT} was extracted, but Windows could not register its per-user login receiver." /SD IDOK
    SetErrorLevel 4
    Abort
  launch_failed:
    MessageBox MB_OK|MB_ICONSTOP "${PF_PRODUCT} was installed, but Windows could not start it." /SD IDOK
    SetErrorLevel 5
    Abort
  done:
SectionEnd
