$ErrorActionPreference = "Stop"

# SlikSVN provides a standalone Windows Subversion CLI and explicitly permits
# embedding it in products when the Apache License 2.0 terms are followed.
$version = "1.14.5"
$url = "https://sliksvn.com/pub/Slik-Subversion-$version-x64.zip"
$sha256 = "77D4FE02999DDA3BDC3A20E86243AE6EDE99AAF072B4C12B0CDEDB54D88E954A"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$targetRoot = Join-Path $repoRoot "tools\svn"
$targetBin = Join-Path $targetRoot "bin"
$tempRoot = Join-Path $env:TEMP "mk-workbench-svn-cli-$version"

if (Test-Path (Join-Path $targetBin "svn.exe")) {
    $installedVersion = (& (Join-Path $targetBin "svn.exe") --version --quiet).Trim()
    if ($installedVersion -eq $version) {
        Write-Host "Bundled SVN CLI $version is already prepared."
        exit 0
    }
    Remove-Item $targetRoot -Recurse -Force
}

if (Test-Path $tempRoot) {
    Remove-Item $tempRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null

$archive = Join-Path $tempRoot "Slik-Subversion-$version-x64.zip"
$extract = Join-Path $tempRoot "extract"

Write-Host "Downloading SlikSVN $version x64..."
Invoke-WebRequest -Uri $url -OutFile $archive -UseBasicParsing

$actualHash = (Get-FileHash -Path $archive -Algorithm SHA256).Hash.ToUpperInvariant()
if ($actualHash -ne $sha256) {
    throw "SlikSVN archive checksum mismatch. Expected $sha256 but received $actualHash."
}

Write-Host "Extracting SlikSVN..."
Expand-Archive -Path $archive -DestinationPath $extract -Force

$svnFile = Get-ChildItem -Path $extract -Recurse -Filter "svn.exe" -File | Select-Object -First 1
if (-not $svnFile) {
    throw "The downloaded SlikSVN archive does not contain svn.exe."
}

$sourceBin = $svnFile.Directory.FullName
New-Item -ItemType Directory -Path $targetBin -Force | Out-Null
Copy-Item -Path (Join-Path $sourceBin "*") -Destination $targetBin -Recurse -Force

$license = Get-ChildItem -Path $extract -Recurse -Filter "LICENSE*" -File | Select-Object -First 1
if ($license) {
    Copy-Item $license.FullName (Join-Path $targetRoot "LICENSE.txt") -Force
}

$installedVersion = (& (Join-Path $targetBin "svn.exe") --version --quiet).Trim()
if ($installedVersion -ne $version) {
    throw "Prepared SVN CLI reports version '$installedVersion', expected '$version'."
}

Remove-Item $tempRoot -Recurse -Force

Write-Host "Bundled SVN CLI $version prepared at $targetBin" -ForegroundColor Green
