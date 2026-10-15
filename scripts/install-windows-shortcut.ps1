param(
  [string]$ShortcutName = "Agent Context Manager",
  [string]$TargetPath,
  [string]$IconPath,
  [string]$AppId = "AgentContextManager.Desktop"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot

if (-not $TargetPath) {
  $TargetPath = Join-Path $projectRoot "dist\Agent Context Manager.exe"
}
if (-not $IconPath) {
  $IconPath = Join-Path $projectRoot "assets\branding.ico"
}

if (-not (Test-Path -LiteralPath $TargetPath)) {
  throw "Target executable was not found: $TargetPath"
}
if (-not (Test-Path -LiteralPath $IconPath)) {
  throw "Icon file was not found: $IconPath"
}

$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "$ShortcutName.lnk"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = (Resolve-Path -LiteralPath $TargetPath).Path
$shortcut.WorkingDirectory = Split-Path -Parent $shortcut.TargetPath
$shortcut.IconLocation = "$((Resolve-Path -LiteralPath $IconPath).Path),0"
$shortcut.Description = "Agent Context Manager"
$shortcut.Save()

Write-Host "Shortcut updated: $shortcutPath"
Write-Host "Target: $($shortcut.TargetPath)"
Write-Host "Icon: $($shortcut.IconLocation)"
Write-Host "AppUserModelID used by the app process: $AppId"
