<#
.SYNOPSIS
  Runs the pure static helper methods of a COPY of the real legacy PDMMaintenance.exe over a vector file.

.DESCRIPTION
  No database access: only parseAttributeNameAsPConProperty, ParsePConPropertyName, SIFImport.camelCase and
  CADMaintenance.isInteger are called (all pure string functions). Run from 32-bit PowerShell
  (%WINDIR%\SysWOW64\WindowsPowerShell\v1.0\powershell.exe) because the assembly is x86.
  Pass a copy of the PDM bin directory, never the installed directory.

.EXAMPLE
  & "$env:WINDIR\SysWOW64\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -File run_legacy_helpers.ps1 `
      -PdmDir C:\scratch\pdm_copy -Vectors fixtures\helper_vectors.json -Out fixtures\helper_legacy_results.json
#>
param(
    [Parameter(Mandatory)] [string] $PdmDir,
    [Parameter(Mandatory)] [string] $Vectors,
    [Parameter(Mandatory)] [string] $Out
)
$ErrorActionPreference = 'Stop'
$exe = Join-Path $PdmDir 'PDMMaintenance.exe'
$expr = Join-Path $PdmDir 'ExprEvaluator.dll'
if (-not (Test-Path $exe)) { throw "PDMMaintenance.exe not found in $PdmDir" }
if (Test-Path $expr) { [System.Reflection.Assembly]::LoadFrom((Resolve-Path $expr)) | Out-Null }
$asm = [System.Reflection.Assembly]::LoadFrom((Resolve-Path $exe))
$flags = [System.Reflection.BindingFlags]'Static,Public,NonPublic'
$cad = $asm.GetType('PDMMaintenance.CADMaintenance', $true)
$sif = $asm.GetType('PDMMaintenance.SIFImport', $true)
$vec = Get-Content $Vectors -Raw | ConvertFrom-Json

$parse = $cad.GetMethod('parseAttributeNameAsPConProperty', $flags)
$ppn = $cad.GetMethod('ParsePConPropertyName', $flags)
$isInt = $cad.GetMethod('isInteger', $flags)
$camel = $sif.GetMethod('camelCase', $flags)

$result = [ordered]@{
    assemblyVersion = $asm.GetName().Version.ToString()
    assemblySha256  = ([System.BitConverter]::ToString(([System.Security.Cryptography.SHA256]::Create()).ComputeHash([System.IO.File]::ReadAllBytes((Resolve-Path $exe)))) -replace '-', '')
    parseAttributeNameAsPConProperty = @()
    camelCase = @()
    ParsePConPropertyName = @()
    isInteger = @()
}
foreach ($ctx in $vec.parseAttributeNameAsPConProperty.contexts) {
    foreach ($n in $vec.parseAttributeNameAsPConProperty.names) {
        $result.parseAttributeNameAsPConProperty += [ordered]@{ name = $n; context = $ctx; result = [string]$parse.Invoke($null, @($n, $ctx)) }
    }
}
foreach ($v in $vec.camelCase) { $result.camelCase += [ordered]@{ input = $v; result = [string]$camel.Invoke($null, @($v, $false, $false, $false)) } }
foreach ($v in $vec.ParsePConPropertyName) { $result.ParsePConPropertyName += [ordered]@{ input = $v; result = [string]$ppn.Invoke($null, @($v)) } }
foreach ($v in $vec.isInteger) {
    $result.isInteger += [ordered]@{ input = $v; allowNegative = $false; result = [bool]$isInt.Invoke($null, @($v, $false)) }
    $result.isInteger += [ordered]@{ input = $v; allowNegative = $true;  result = [bool]$isInt.Invoke($null, @($v, $true)) }
}
$result | ConvertTo-Json -Depth 6 | Set-Content -Path $Out -Encoding UTF8
"wrote $Out"
