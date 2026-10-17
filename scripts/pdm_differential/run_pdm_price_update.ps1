# Runs the REAL, compiled PDM price update (UpdatePriceThread.execThread - what the PDM "Update pCon Prices"
# buttons start) against an ISOLATED MDB copy. Must run under 32-bit PowerShell (Jet 4.0 OLEDB + x86 PDM).
#
# Safety: PDMMaintenance.exe is loaded as a library from a COPY; PDM.bat / the UI are never started.
# CADMaintenance.pConPath is redirected so the only database PDM can write is the MDB copy under -PconRoot.
# PDM only SELECTs from SQL Server in these code paths (verified in the source: every INSERT/UPDATE it issues
# targets tCOMd_* Jet tables). SQL access uses PDM's own connection logic with the current Windows identity.
#
# Job JSON: { "pconRoot": "...\\", "workspace": "...", "mode": "article|global|placeholders",
#   "items": [...], "itemFilter": "", "programCode": "layout_studio", "siteId": 1, "catalogueId": 1,
#   "mydate": "16-Oct-2026", "prevdate": "15-Oct-2026", "currency": "GBP", "priceListId": 22,
#   "pricelist": "GBP_2026_2", "variableincs": true, "packageId": 375, "resetToZero": false }
param(
    [Parameter(Mandatory = $true)][string]$JobPath,
    [Parameter(Mandatory = $true)][string]$OutPath,
    [Parameter(Mandatory = $true)][string]$PdmDir
)
$ErrorActionPreference = "Stop"
$job = Get-Content -Raw -LiteralPath $JobPath | ConvertFrom-Json
Add-Type -AssemblyName System.Windows.Forms
$asm = [Reflection.Assembly]::LoadFrom((Join-Path $PdmDir "PDMMaintenance.exe"))
$any = [Reflection.BindingFlags]"Static,Instance,Public,NonPublic"
function T($name) { $asm.GetTypes() | Where-Object { $_.Name -eq $name } | Select-Object -First 1 }

(T "CADMaintenance").GetField("pConPath").SetValue($null, [string]$job.pconRoot)
if ($job.server) { (T "Global").GetField("connectedServer", $any).SetValue($null, [string]$job.server) }
if ($job.database) { (T "Global").GetField("connectedDB", $any).SetValue($null, [string]$job.database) }

$ppu = [Activator]::CreateInstance((T "PConPriceUpdate"))
$th = [Activator]::CreateInstance((T "UpdatePriceThread"))
$thType = T "UpdatePriceThread"
$thType.GetField("packageId", $any).SetValue($th, [int]$job.packageId)

# variableincs exactly as PConPriceUpdate.button_global_Click computes it.
$variableincs = [bool]$job.variableincs
if ($job.variableincsFromProgram -and $job.mode -eq "global") {
    $variableincs = [bool]((T "PriceMaintenance").GetMethod("programCodeHasVariableIncs", $any).Invoke($null, @([string]$job.programCode)))
}
$items = New-Object System.Collections.ArrayList
foreach ($i in $job.items) { [void]$items.Add([string]$i) }
$article = ($job.mode -eq "article" -or $job.mode -eq "placeholders")
$placeholders = ($job.mode -eq "placeholders")
$init = $thType.GetMethod("initThread", $any)
# initThread(ppu, itemList, itemFilter, workspace, programCode, actualProgramCode, siteId, catalogueId, mydate,
#            prevdate, currency, priceListId, pricelist, articlepricing, hybridpricing, addGlobalPricePlaceHolders,
#            variableincs, testItem, verbose, resetToZero)
$initArgs = @($ppu, $items, [string]$job.itemFilter, [string]$job.workspace, [string]$job.programCode,
    [string]$job.programCode, [int]$job.siteId, [int]$job.catalogueId, [string]$job.mydate, [string]$job.prevdate,
    [string]$job.currency, [int]$job.priceListId, [string]$job.pricelist, [bool]$article, $false, [bool]$placeholders,
    $variableincs, "", $false, [bool]$job.resetToZero)
for ($k = 0; $k -lt $initArgs.Count; $k++) {
    if ($initArgs[$k] -is [System.Management.Automation.PSObject]) { $initArgs[$k] = $initArgs[$k].PSObject.BaseObject }
}
if ($init.GetParameters().Count -ne $initArgs.Count) { throw "initThread signature changed: $($init.GetParameters().Count) params" }
[void]$init.Invoke($th, $initArgs)

$log = New-Object System.Collections.ArrayList
$handler = [PDMMaintenance.UpdatePriceThread+UpdateStatusEventHandler]{ param($s, $st) [void]$log.Add([string]$st) }
$th.add_UpdateStatus($handler)

# Runs synchronously on this STA thread; the caller enforces the timeout (a stray modal dialog would
# otherwise block) by killing the process.
$exec = $thType.GetMethod("execThread", $any)
$finished = $true
try { [void]$exec.Invoke($th, $null) } catch { $finished = $false; [void]$log.Add("EXCEPTION: " + $_.Exception.ToString()) }
$result = [ordered]@{
    finished = $finished
    pdmVersion = [string]$asm.GetName().Version
    mode = $job.mode
    variableincs = $variableincs
    status = @($log)
    noPDMprice = @($ppu.GetType().GetField("noPDMprice", $any).GetValue($ppu))
    notfound = @($ppu.GetType().GetField("notfound", $any).GetValue($ppu))
}
[IO.File]::WriteAllText($OutPath, ($result | ConvertTo-Json -Depth 5), [Text.Encoding]::UTF8)
