# MK OBX Generator plugin for pCon.planner

A pCon.planner Plugin SDK 8.15 plugin that lets **MK Product Workbench → QA →
Article OBX Generator (pCon SDK)** configure catalogue articles inside
pCon.planner and export them as OBX. The SDK findings and the API mapping are in
[`docs/04_Reference/pCon/SDK_Article_OBX_Generator.md`](../../docs/04_Reference/pCon/SDK_Article_OBX_Generator.md).

## What it does

After `EventType.ApplicationReady` the plugin polls a job folder every 500 ms
(default `%LOCALAPPDATA%\MKProductWorkbench\pcon_obx_jobs`, override with the
`MK_PCON_OBX_JOBS` environment variable) and answers JSON requests:

| kind | SDK calls |
|---|---|
| `ping` | `GetEffectiveArticleLanguages`, `Document.Modified` |
| `catalog` | `Articles.Package.GetAll()` |
| `articles` | `Articles.Catalog.Get(package).GetAllItems()` |
| `properties` | `InsertArticle`/`InsertArticleByPackage`, `InstantiateArticle`, `IPropertyProvider.GetProperties`, `IProperty.SetValue`, `getArticleInformation`, `DbEntity.Delete` |
| `generate` | `Document.NewPlanning`, then automatic depth-first enumeration of every configurable choice property using the live `ValueSet` after each `SetValue` (dependent and nested properties discovered at every node, duplicates by final article number dropped, `<id>.cancel` honoured), `ExportBasketToObx`, `GenerateBasket` |

It also writes `plugin.heartbeat.json` every 2 s so the Workbench can tell
whether pCon.planner and the plugin are alive. A ribbon tab *MK Workbench*
offers "Run Workbench jobs" and "Job folder".

## Build

```powershell
.\build.ps1                      # dotnet build, Release, net481
# or
dotnet build .\MKObxGenerator.csproj -c Release
```

Requirements: .NET SDK, NuGet access for `Microsoft.NETFramework.ReferenceAssemblies.net481`,
and an installed pCon.planner PRO (the project references
`C:\Program Files\EasternGraphics\pCon.planner PRO\bin\X3gPlugin.dll`; pass
`-p:X3gPluginDir=<dir>` to use another copy, e.g. the SDK's `SamplePlugin\X3gPlugin`).

## Install

Copy `MKObxGenerator.dll`, `MKObxGenerator.xml` and `MKObxGenerator.ui` from
`bin\Release\net481` to

```
%APPDATA%\EasternGraphics\pCon.planner Pro\plugins\MKObxGenerator\
```

(or `%ProgramData%\EasternGraphics\pCon.planner Pro\plugins\MKObxGenerator\`)
and restart pCon.planner. The Workbench page's **Install Plugin** button does the copy.

## Licensing (blocking)

pCon.planner only loads plugins whose manifest `hash` was issued by
EasternGraphics, or any plugin with `hash="0"` on a machine holding a
**Plugin SDK developer licence** (Getting Started, section 3). The manifest
ships with `hash="0"`. To distribute the plugin, register vendor
`MillerKnoll` / plugin `MKObxGenerator` with `request@easterngraphics.com`,
then put the issued hash in `res/MKObxGenerator.xml` **and** in
`X3gGetGlobalIdentifier()` in `PluginMain.cs`.

## Safety

* A `generate` request refuses to run while the current planning has unsaved
  changes unless the request sets `discardUnsavedPlanning`; it then starts a
  new planning (`Document.NewPlanning()`).
* Inspection (`properties`) removes the probe article again.
* Values are only ever set when they are offered by the live `ValueSet`; a
  configuration whose earlier values were changed by a relation cascade is
  skipped, never exported.
