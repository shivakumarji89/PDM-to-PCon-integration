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

$result = [ordered]@{ ok = $true; results = @() }
$conn = $null
try {
    $payload = Get-Content -Raw -LiteralPath $InputPath | ConvertFrom-Json
    $conn = New-Object -ComObject ADODB.Connection
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
                        foreach ($row in $op.rows) {
                            $cols = @(); $vals = @()
                            foreach ($p in $row.PSObject.Properties) {
                                $cols += "[$($p.Name)]"
                                $vals += (Format-SqlValue $p.Value)
                            }
                            $sql = "INSERT INTO [$($op.table)] (" + ($cols -join ",") + ") VALUES (" + ($vals -join ",") + ")"
                            $conn.Execute($sql) | Out-Null
                            $count++
                        }
                        $r.inserted = $count
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
                    $conn.Execute($sql) | Out-Null
                    $r.updated = 1
                }
                "query" {
                    $rs = $conn.Execute($op.sql)
                    $rows = @()
                    if ($null -ne $rs) {
                        $names = @(); for ($i = 0; $i -lt $rs.Fields.Count; $i++) { $names += $rs.Fields[$i].Name }
                        while (-not $rs.EOF) {
                            $obj = [ordered]@{}
                            for ($i = 0; $i -lt $rs.Fields.Count; $i++) {
                                $v = $rs.Fields[$i].Value
                                if ($v -is [System.DBNull]) { $v = $null }
                                $obj[$names[$i]] = $v
                            }
                            $rows += [pscustomobject]$obj
                            $rs.MoveNext()
                        }
                        $rs.Close()
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
        $result.results += [pscustomobject]$r
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
    $result.results += [pscustomobject]@{ op = "connect"; ok = $false; error = "$($_.Exception.Message)" }
}
finally {
    if ($conn -and $conn.State -eq 1) { $conn.Close() }
}

$json = $result | ConvertTo-Json -Depth 8
[System.IO.File]::WriteAllText($OutputPath, $json, [System.Text.Encoding]::UTF8)
