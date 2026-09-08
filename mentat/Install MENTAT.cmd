@echo off
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-MENTAT.ps1"
if errorlevel 1 pause
