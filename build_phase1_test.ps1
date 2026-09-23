$ErrorActionPreference = "Stop"

Write-Host "=== MK Product Workbench - Phase 1 Test EXE Build ===" -ForegroundColor Cyan

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw "Python was not found on PATH. Install Python 3.10+ and run this script again."
}

$version = & python --version
Write-Host "Using $version"

if (-not (Test-Path ".\main.py")) {
    throw "Run this script from the repository root (main.py was not found)."
}

Write-Host "Installing runtime and build dependencies..." -ForegroundColor Yellow
& python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Runtime dependency installation failed." }

& python -m pip install -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw "Build dependency installation failed." }

Write-Host "Cleaning previous build output..." -ForegroundColor Yellow
if (Test-Path ".\build") { Remove-Item ".\build" -Recurse -Force }
if (Test-Path ".\dist") { Remove-Item ".\dist" -Recurse -Force }

Write-Host "Preparing bundled SVN command-line runtime..." -ForegroundColor Yellow
& powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\prepare_svn_cli.ps1"
if ($LASTEXITCODE -ne 0) { throw "Bundled SVN CLI preparation failed." }

$svnBin = (Resolve-Path ".\tools\svn\bin").Path
$svnExe = Join-Path $svnBin "svn.exe"
if (-not (Test-Path $svnExe)) {
    throw "Bundled SVN CLI was not prepared at $svnExe"
}

Write-Host "Building single-file Windows executable..." -ForegroundColor Yellow
$pyinstallerArgs = @(
    "--noconfirm",
    "--clean",
    "--onefile",
    "--windowed",
    "--name", "MK_Workbench_Phase1_Test",
    "--additional-hooks-dir", "build_hooks",
    "--add-data", "resources;resources",
    "--add-binary", "$svnBin\*;svn\bin",
    "main.py"
)
& python -m PyInstaller @pyinstallerArgs

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed."
}

$exe = ".\dist\MK_Workbench_Phase1_Test.exe"
if (-not (Test-Path $exe)) {
    throw "Build completed without producing $exe"
}

Write-Host ""
Write-Host "BUILD COMPLETE" -ForegroundColor Green
Write-Host "EXE: $((Resolve-Path $exe).Path)" -ForegroundColor Green
Write-Host ""
Write-Host "Double-click the EXE to launch MK Product Workbench." -ForegroundColor Cyan
