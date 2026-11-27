# OCD/MDB write bridge (must run under 32-bit PowerShell: ACE OLEDB provider is 32-bit only).
# Reads a JSON batch of operations, applies them to an .mdb via ADODB, writes a JSON result.
#
# Input JSON shape:
#   { "mdb": "<path>",
#     "ops": [
#       { "op": "delete", "table": "tCOMd_Class" },
#       { "op": "delete", "table": "tCOMd_Class", "where": { "com_ClassID": 1 } },
#       { "op": "insert", "table": "tCOMd_Class", "rows": [ { "com_ClassID": 1, ... }, ... ] },
#       { "op": "update", "table": "tCOMd_Package", "set": { ... }, "where": { "com_PackageID": 1 } },
#       { "op": "query",  "sql": "SELECT ..." }
#     ] }
# Inserts may specify "identity": "<autonumber column>". That column contains
# a symbolic token, omitted from SQL; later columns can reference {"$ref": token}.
# The same connection reads @@IDENTITY immediately and returns generated_ids.
# Output JSON: { "ok": true|false, "results": [ { "op": .., "ok": .., "error": .., "rows": [...] } ] }
param(
    [Parameter(Mandatory = $true)][string]$InputPath,
    [Parameter(Mandatory = $true)][string]$OutputPath
)

$ErrorActionPreference = "Stop"

$Inv = [System.Globalization.CultureInfo]::InvariantCulture

function Format-SqlValue($v) {
    if ($null -eq $v) { return "NULL" }
    if ($v -is [bool]) { if ($v) { return "True" } else { return "False" } }
    if ($v -is [int] -or $v -is [long] -or $v -is [int16] -or $v -is [int32] -or $v -is [int64]) {
        return $v.ToString($Inv)
    }
    if ($v -is [double] -or $v -is [decimal] -or $v -is [single]) {
        return $v.ToString($Inv)
    }
    $s = [string]$v
    # An Access date literal (#YYYY-MM-DD HH:MM:SS#) is emitted as-is so it writes
    # to a DateTime column; everything else is a quoted string.
    if ($s -match '^#\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}#$') { return $s }
    $s = $s -replace "'", "''"
    return "'$s'"
}

# Generic lists, not ``@()`` + ``+=``: array ``+=`` copies the whole array on every append, which made
# large result sets and many-op batches quadratic. ``List.Add`` is amortised O(1) and serialises to the
# same JSON arrays (``[]`` / one-element / many).
$result = [ordered]@{ ok = $true; results = [System.Collections.Generic.List[object]]::new() }
$conn = $null
$rs = $null
$identities = @{}
try {
    $payload = Get-Content -Raw -LiteralPath $InputPath | ConvertFrom-Json
    $conn = New-Object -ComObject ADODB.Connection
    if (@($payload.ops | Where-Object { $_.op -ne "query" }).Count -eq 0) {
        $conn.Mode = 1 # adModeRead: previews and verification cannot write.
    }
    $conn.Open("Provider=Microsoft.ACE.OLEDB.16.0;Data Source=$($payload.mdb);")

    $useTx = [bool]$payload.transaction
    if ($useTx) { $conn.BeginTrans() | Out-Null }

    foreach ($op in $payload.ops) {
        $r = [ordered]@{ op = $op.op; table = $op.table; ok = $true; error = $null }
        try {
            switch ($op.op) {
                "delete" {
                    # Optional WHERE (same shape as update); no where = clear table.
                    $whereSql = ""
                    if ($op.where) {
                        $conds = @()
                        foreach ($p in $op.where.PSObject.Properties) {
                            $conds += "[$($p.Name)] = " + (Format-SqlValue $p.Value)
                        }
                        if ($conds.Count -gt 0) { $whereSql = " WHERE " + ($conds -join " AND ") }
                    }
                    $conn.Execute("DELETE FROM [$($op.table)]$whereSql") | Out-Null
                }
                "insert" {
                    if ($op.rows -and @($op.rows).Count -gt 0) {
                        $count = 0
                        $generated = @{}
                        foreach ($row in $op.rows) {
                            $cols = @(); $vals = @()
                            $token = $null
                            foreach ($p in $row.PSObject.Properties) {
                                if ($op.identity -and $p.Name -eq $op.identity) {
                                    $token = [string]$p.Value
                                    if (-not $token -or $identities.ContainsKey($token)) {
                                        throw "Missing or duplicate identity token '$token'"
                                    }
                                    continue
                                }
                                $value = $p.Value
                                if ($null -ne $value -and $value.PSObject.Properties['$ref']) {
                                    $reference = [string]$value.'$ref'
                                    if (-not $identities.ContainsKey($reference)) {
                                        throw "Unresolved identity reference '$reference'"
                                    }
                                    $value = $identities[$reference]
                                }
                                $cols += "[$($p.Name)]"
                                $vals += (Format-SqlValue $value)
                            }
                            if ($op.identity -and -not $token) {
                                throw "Identity column '$($op.identity)' has no token"
                            }
                            $sql = "INSERT INTO [$($op.table)] (" + ($cols -join ",") + ") VALUES (" + ($vals -join ",") + ")"
                            $conn.Execute($sql) | Out-Null
                            if ($op.identity) {
                                $rs = $conn.Execute("SELECT @@IDENTITY")
                                $id = $rs.Fields[0].Value
                                if ($null -eq $id -or $id -is [System.DBNull]) {
                                    throw "MDB returned no identity for '$token'"
                                }
                                $identities[$token] = $id
                                $generated[$token] = $id
                                $rs.Close()
                                [System.Runtime.InteropServices.Marshal]::ReleaseComObject($rs) | Out-Null
                                $rs = $null
                            }
                            $count++
                        }
                        $r.inserted = $count
                        $r.generated_ids = $generated
                    } else {
                        $r.inserted = 0
                    }
                }
                "update" {
                    # A SQL UPDATE (not a recordset) so several updates - dates,
                    # bools, strings - run cleanly in one transaction. Format-
                    # SqlValue emits #..# date literals, True/False and quoted text.
                    $sets = @()
                    foreach ($p in $op.set.PSObject.Properties) {
                        $sets += "[$($p.Name)] = " + (Format-SqlValue $p.Value)
                    }
                    $whereSql = ""
                    if ($op.where) {
                        $conds = @()
                        foreach ($p in $op.where.PSObject.Properties) {
                            $conds += "[$($p.Name)] = " + (Format-SqlValue $p.Value)
                        }
                        if ($conds.Count -gt 0) { $whereSql = " WHERE " + ($conds -join " AND ") }
                    }
                    $sql = "UPDATE [$($op.table)] SET " + ($sets -join ", ") + $whereSql
                    # Report the rows the engine actually changed (0 = no row matched).
                    $affected = 0
                    $conn.Execute($sql, [ref]$affected) | Out-Null
                    $r.updated = [int]$affected
                }
                "query" {
                    $rs = $conn.Execute($op.sql)
                    $rows = [System.Collections.Generic.List[object]]::new()
                    if ($null -ne $rs) {
                        $names = @(); for ($i = 0; $i -lt $rs.Fields.Count; $i++) { $names += $rs.Fields[$i].Name }
                        while (-not $rs.EOF) {
                            $obj = [ordered]@{}
                            for ($i = 0; $i -lt $rs.Fields.Count; $i++) {
                                $v = $rs.Fields[$i].Value
                                if ($v -is [System.DBNull]) { $v = $null }
                                $obj[$names[$i]] = $v
                            }
                            $rows.Add([pscustomobject]$obj)
                            $rs.MoveNext()
                        }
                        $rs.Close()
                        [System.Runtime.InteropServices.Marshal]::ReleaseComObject($rs) | Out-Null
                        $rs = $null
                    }
                    $r.rows = $rows
                }
                default { throw "unknown op '$($op.op)'" }
            }
        }
        catch {
            $r.ok = $false
            $r.error = "$($_.Exception.Message)"
            $result.ok = $false
        }
        $result.results.Add([pscustomobject]$r)
        if ($useTx -and -not $result.ok) { break }
    }

    # Commit only if every op succeeded; otherwise roll the whole batch back so
    # an interrupted/failed run leaves the package unchanged.
    if ($useTx) {
        if ($result.ok) { $conn.CommitTrans() | Out-Null }
        else { $conn.RollbackTrans() | Out-Null }
    }
}
catch {
    $result.ok = $false
    $result.results.Add([pscustomobject]@{ op = "connect"; ok = $false; error = "$($_.Exception.Message)" })
}
finally {
    if ($rs) {
        try { $rs.Close() } catch {}
        try { [System.Runtime.InteropServices.Marshal]::ReleaseComObject($rs) | Out-Null } catch {}
        $rs = $null
    }
    if ($conn) {
        try { if ($conn.State -eq 1) { $conn.Close() } } catch {}
        try { [System.Runtime.InteropServices.Marshal]::ReleaseComObject($conn) | Out-Null } catch {}
        $conn = $null
    }
}

# Stream the response instead of ``$result | ConvertTo-Json``. In this 32-bit PowerShell 5.1 host, one
# ConvertTo-Json over a large aggregate (e.g. ~150k PropValue rows) throws OutOfMemoryException. Each op
# header is serialised on its own and ``rows`` is written one row at a time, so no whole-result JSON string
# exists. The JSON shape is unchanged: {"ok":..,"results":[{op,table,ok,error,..,"rows":[..]}]}.
# Output goes to a temp file that replaces $OutputPath only after a complete, successful write, so a
# failure can never leave a truncated file that the caller would mistake for a valid response.
$tmpOutput = "$OutputPath.partial"
$writer = $null
try {
    if (Test-Path -LiteralPath $tmpOutput) { Remove-Item -LiteralPath $tmpOutput -Force }
    # UTF-8 with BOM, as before ([Text.Encoding]::UTF8); the Python reader uses utf-8-sig.
    $writer = New-Object System.IO.StreamWriter($tmpOutput, $false, (New-Object System.Text.UTF8Encoding($true)))
    $writer.Write('{"ok":' + $(if ($result.ok) { 'true' } else { 'false' }) + ',"results":[')
    $firstItem = $true
    foreach ($item in $result.results) {
        if (-not $firstItem) { $writer.Write(',') }
        $firstItem = $false
        $hasRows = $null -ne $item.PSObject.Properties['rows']
        $head = [ordered]@{}
        foreach ($p in $item.PSObject.Properties) {
            if ($p.Name -ne 'rows') { $head[$p.Name] = $p.Value }
        }
        $headJson = ([pscustomobject]$head) | ConvertTo-Json -Compress -Depth 8
        if (-not $hasRows) {
            $writer.Write($headJson)
            continue
        }
        # headJson is a complete object ("{...}"); reopen it and append the rows array.
        $writer.Write($headJson.Substring(0, $headJson.Length - 1))
        $writer.Write(',"rows":[')
        $firstRow = $true
        foreach ($row in $item.rows) {
            if (-not $firstRow) { $writer.Write(',') }
            $firstRow = $false
            $writer.Write(($row | ConvertTo-Json -Compress -Depth 8))
        }
        $writer.Write(']}')
        $item.rows = $null  # release this table's rows before serialising the next one
    }
    $writer.Write(']}')
    $writer.Flush()
    $writer.Dispose()
    $writer = $null
    if (Test-Path -LiteralPath $OutputPath) { Remove-Item -LiteralPath $OutputPath -Force }
    [System.IO.File]::Move($tmpOutput, $OutputPath)
}
catch {
    if ($writer) { try { $writer.Dispose() } catch {} ; $writer = $null }
    try { if (Test-Path -LiteralPath $tmpOutput) { Remove-Item -LiteralPath $tmpOutput -Force } } catch {}
    # No output file is left behind; the caller reports stderr as the bridge error.
    [Console]::Error.WriteLine("mdb_bridge: failed to write response: $($_.Exception.Message)")
    exit 1
}
