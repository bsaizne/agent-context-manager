param(
  [string]$Python = "python",
  [switch]$GuiOnly
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonCommand = Get-Command $Python -ErrorAction SilentlyContinue
if (-not $pythonCommand -and -not (Test-Path -LiteralPath $Python)) {
  throw "Python was not found. Install Python or pass -Python C:\\path\\to\\python.exe."
}

& $Python -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
  throw "PyInstaller is not installed for this Python. Run: $Python -m pip install -e `"${projectRoot}[gui,package]`""
}

$specs = if ($GuiOnly) {
  @("agent-context-gui.spec")
} else {
  @("agent-context.spec", "agent-context-gui.spec")
}

foreach ($spec in $specs) {
  $specPath = Join-Path $projectRoot $spec
  if (-not (Test-Path -LiteralPath $specPath)) {
    throw "Build spec not found: $specPath"
  }
}

Push-Location $projectRoot
try {
  foreach ($spec in $specs) {
    $currentSpec = Join-Path $projectRoot $spec
    if (-not (Test-Path -LiteralPath $currentSpec)) {
      throw "Build spec not found: $currentSpec"
    }
    & $Python -m PyInstaller $currentSpec --clean --noconfirm
    if ($LASTEXITCODE -ne 0) {
      throw "PyInstaller failed with exit code $LASTEXITCODE for $spec."
    }
  }
}
finally {
  Pop-Location
}

# Read the executable name from each spec instead of hardcoding it. The GUI spec
# carries the release in its name ("Agent Context Manager v0.5"), so a hardcoded
# list fails this check as soon as the version changes, even though the build
# itself succeeded.
foreach ($spec in $specs) {
  $specPath = Join-Path $projectRoot $spec
  $content = Get-Content -LiteralPath $specPath -Raw
  $match = [regex]::Match($content, 'name\s*=\s*"([^"]+)"')
  if (-not $match.Success) {
    throw "Cannot read the output executable name from: $specPath"
  }
  $name = $match.Groups[1].Value
  # onedir specs produce dist\<name>\<name>.exe, onefile specs dist\<name>.exe.
  $oneFile = Join-Path $projectRoot ("dist\" + $name + ".exe")
  $oneDir = Join-Path $projectRoot ("dist\" + $name + "\" + $name + ".exe")
  if (Test-Path -LiteralPath $oneDir) {
    Write-Host "Built $oneDir"
  } elseif (Test-Path -LiteralPath $oneFile) {
    Write-Host "Built $oneFile"
  } else {
    throw "Build completed without creating: $oneFile or $oneDir"
  }
}
