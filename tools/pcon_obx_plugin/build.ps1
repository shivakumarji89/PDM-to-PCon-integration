# Build the MK OBX Generator plugin for pCon.planner.
#
# Requires: .NET SDK (dotnet) and the NuGet access for the .NET Framework 4.8.1
# reference assemblies (both verified on the Workbench build machine). X3gPlugin.dll is taken from
# the installed pCon.planner PRO unless -X3gPluginDir is given.
param(
    [string]$Configuration = "Release",
    [string]$X3gPluginDir = ""
)
$ErrorActionPreference = "Stop"
$project = Join-Path $PSScriptRoot "MKObxGenerator.csproj"
$args = @("build", $project, "-c", $Configuration, "-nologo")
if ($X3gPluginDir) { $args += "-p:X3gPluginDir=$X3gPluginDir" }
& dotnet @args
if ($LASTEXITCODE -ne 0) { throw "dotnet build failed with exit code $LASTEXITCODE" }
$out = Join-Path $PSScriptRoot "bin\$Configuration\net481"
Write-Host "Plugin built to $out"
Write-Host "Install: copy MKObxGenerator.dll, .xml and .ui to %APPDATA%\EasternGraphics\pCon.planner Pro\plugins\MKObxGenerator\"
