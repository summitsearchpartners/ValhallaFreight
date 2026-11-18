Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
function Invoke-Docker {
    param([string[]]$Arguments)
    & docker @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Docker command failed (exit $LASTEXITCODE). Read the Docker error above." }
}
function Write-Utf8 { param([string]$Path,[string]$Text)
    [IO.File]::WriteAllText($Path,$Text,(New-Object Text.UTF8Encoding($false)))
}
function Copy-DemoTree { param([string]$From,[string]$To)
    New-Item -ItemType Directory -Path $To -Force | Out-Null
    foreach ($item in Get-ChildItem -LiteralPath $From -Force) {
        if ($item.Name -in @('node_modules','__pycache__','.pytest_cache','.git','dist','.venv','venv','demo-backup','storage')) { continue }
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { continue }
        if ($item.PSIsContainer) { Copy-DemoTree $item.FullName (Join-Path $To $item.Name) }
        elseif ($item.Extension -notin @('.pyc','.tsbuildinfo','.log','.db','.sqlite')) { Copy-Item -LiteralPath $item.FullName -Destination $To -Force }
    }
}
function Wait-DemoDatabase { param([string[]]$Compose,[string]$User,[string]$Database)
    for ($i=0;$i -lt 60;$i++) {
        & docker @Compose exec -T db pg_isready -U $User -d $Database *> $null
        if ($LASTEXITCODE -eq 0) { return }
        Start-Sleep -Seconds 1
    }
    throw 'PostgreSQL did not become ready. Check Docker Desktop and compose logs.'
}
$script:DemoCountSql = "SELECT json_build_object('users',(SELECT count(*) FROM users),'companies',(SELECT count(*) FROM customers),'quotes',(SELECT count(*) FROM quotes),'shipments',(SELECT count(*) FROM shipments));"
