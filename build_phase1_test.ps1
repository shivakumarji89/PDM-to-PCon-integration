$ErrorActionPreference = "Stop"

Write-Host "=== MK Product Workbench - Phase 1 Test EXE Build ===" -ForegroundColor Cyan

$python = "C:\Users\siaoca\AppData\Local\Programs\Python\Python312\python.exe"
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Supported Python interpreter was not found: $python"
}

if (-not (Test-Path ".\main.py")) {
    throw "Run this script from the repository root (main.py was not found)."
}
if (-not (Test-Path ".\MK_Workbench_Phase1_Test.spec" -PathType Leaf)) {
    throw "Build spec was not found: .\MK_Workbench_Phase1_Test.spec"
}

$environmentCheck = @'
import importlib.util
import struct
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from packaging.requirements import Requirement

if sys.version_info[:2] != (3, 12):
    raise SystemExit(f"Expected Python 3.12, found {sys.version.split()[0]}")
if struct.calcsize("P") * 8 != 64:
    raise SystemExit("Expected a 64-bit Python interpreter")
print(f"Using {sys.executable} ({sys.version.split()[0]}, 64-bit)")

module_names = {
    "pyside6": "PySide6",
    "openpyxl": "openpyxl",
    "pyodbc": "pyodbc",
    "pyinstaller": "PyInstaller",
}
missing = []
for requirements_file in ("requirements.txt", "requirements-build.txt"):
    path = Path(requirements_file)
    if not path.is_file():
        missing.append(f"requirements file {path} is missing")
        continue
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        requirement = Requirement(line)
        if requirement.marker and not requirement.marker.evaluate():
            continue
        try:
            installed_version = version(requirement.name)
        except PackageNotFoundError:
            missing.append(f"{requirement.name} is not installed (required by {path})")
            continue
        if requirement.specifier and installed_version not in requirement.specifier:
            missing.append(
                f"{requirement.name} {installed_version} does not satisfy "
                f"{requirement.specifier} (required by {path})"
            )
            continue
        module_name = module_names.get(requirement.name.lower().replace("_", "-"))
        if module_name and importlib.util.find_spec(module_name) is None:
            missing.append(f"{requirement.name} is installed but cannot be imported")
        else:
            print(f"{requirement.name} {installed_version}: available")

if missing:
    raise SystemExit("Build prerequisites are not satisfied:\n- " + "\n- ".join(missing))
'@
Write-Host "Checking the supported interpreter and installed dependencies..." -ForegroundColor Yellow
& $python -c $environmentCheck
if ($LASTEXITCODE -ne 0) { throw "Python environment validation failed; no packages were installed." }

$scratchRoot = [System.IO.Path]::GetTempPath()
$scratchDirectory = Join-Path $scratchRoot ("MK_Workbench_Phase1_Test-" + [Guid]::NewGuid().ToString("N"))
$workPath = Join-Path $scratchDirectory "work"
$distPath = Join-Path $scratchDirectory "dist"
New-Item -ItemType Directory -Path $workPath, $distPath -Force | Out-Null

Write-Host "Building single-file Windows executable in scratch storage..." -ForegroundColor Yellow
$pyinstallerArgs = @(
    "--noconfirm",
    "--workpath", $workPath,
    "--distpath", $distPath,
    ".\MK_Workbench_Phase1_Test.spec"
)
& $python -m PyInstaller @pyinstallerArgs

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed."
}

$exe = Join-Path $distPath "MK_Workbench_Phase1_Test.exe"
if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) {
    throw "Build completed without producing the expected executable: $exe"
}
if ((Get-Item -LiteralPath $exe).Length -le 0) {
    throw "Build produced an empty executable: $exe"
}

Write-Host ""
Write-Host "BUILD COMPLETE" -ForegroundColor Green
Write-Host "EXE: $((Resolve-Path -LiteralPath $exe).Path)" -ForegroundColor Green
Write-Host "Scratch output retained for verification: $scratchDirectory" -ForegroundColor Cyan
Write-Host ""
Write-Host "Double-click the EXE to launch MK Product Workbench." -ForegroundColor Cyan
