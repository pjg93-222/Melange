; Nsis7z::Extract returns no stack value. A blocked plugin may leave its
; archive argument on the stack, so restore the destination explicitly.
!macro extractUsing7za FILE
  CreateDirectory "$PLUGINSDIR\7z-out"
  SetOutPath "$PLUGINSDIR\7z-out"
  ClearErrors
  Nsis7z::Extract "${FILE}"
  ${If} ${Errors}
    Goto ApplicationExtractionFailed
  ${EndIf}
  IfFileExists "$PLUGINSDIR\7z-out\${APP_EXECUTABLE_FILENAME}" 0 ApplicationExtractionFailed
  IfFileExists "$PLUGINSDIR\7z-out\resources\app.asar" 0 ApplicationExtractionFailed
  SetOutPath $INSTDIR
  StrCpy $R1 0
  CopyApplicationFiles:
    ClearErrors
    CopyFiles /SILENT "$PLUGINSDIR\7z-out\*" "$INSTDIR"
    IfErrors RetryApplicationCopy
    IfFileExists "$INSTDIR\${APP_EXECUTABLE_FILENAME}" 0 ApplicationExtractionFailed
    IfFileExists "$INSTDIR\resources\app.asar" 0 ApplicationExtractionFailed
    Goto ApplicationExtractionComplete
  RetryApplicationCopy:
    IntOp $R1 $R1 + 1
    ${If} $R1 < 5
      Sleep 1000
      Goto CopyApplicationFiles
    ${EndIf}
    MessageBox MB_RETRYCANCEL|MB_ICONEXCLAMATION "The application files could not be written. Close the application and try again." /SD IDCANCEL IDRETRY CopyApplicationFiles
  ApplicationExtractionFailed:
    SetErrorLevel 2
    MessageBox MB_OK|MB_ICONSTOP "The application files could not be extracted or written. Installation has stopped. Give IT the installer Details if security software blocked a file." /SD IDOK
    Quit
  ApplicationExtractionComplete:
!macroend
