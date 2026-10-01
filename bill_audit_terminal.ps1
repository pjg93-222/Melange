$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $Root
$Host.UI.RawUI.WindowTitle = 'Moneyball Bill and Stance Audit Console'
python -u .\fec\legislation\bill_audit_console.py
