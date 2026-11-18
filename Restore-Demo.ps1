[CmdletBinding()]
param([ValidatePattern('^[a-z0-9][a-z0-9_-]+$')][string]$ProjectName='valhalla-laptop-demo')
. (Join-Path $PSScriptRoot 'Demo-Transfer.Common.ps1')
Get-Command docker -ErrorAction Stop | Out-Null
$project=$PSScriptRoot
$backup=Join-Path $project 'demo-backup'
$manifestPath=Join-Path $backup 'manifest.json'
if (-not (Test-Path -LiteralPath $manifestPath)) { throw 'This ZIP has no exported database. Run Export-Demo.ps1 on the original desktop FIRST, then transfer the NEW ValhallaFreight-Demo-TIMESTAMP.zip.' }
$manifest=Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ($manifest.format -ne 1) { throw 'Unsupported backup format.' }
Write-Host 'Verifying the database, document and image checksums...'
foreach ($entry in $manifest.files.PSObject.Properties) {
    if ($entry.Name -notin @('database.dump','documents.tar.gz','images.tar')) { throw 'Unexpected backup filename.' }
    $file=Join-Path $backup $entry.Name
    if (-not (Test-Path -LiteralPath $file)) { throw ('Backup file missing: '+$entry.Name) }
    if ((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash -ne $entry.Value) { throw ('Backup checksum failed: '+$entry.Name) }
}
foreach ($name in @('database.dump','documents.tar.gz')) {
    if (-not ($manifest.files.PSObject.Properties.Name -contains $name)) { throw "Missing required archive: $name" }
}
$compose=@('compose','--project-directory',$project,'--file',(Join-Path $project 'docker-compose.yml'),'--file',(Join-Path $project 'docker-compose.demo.json'),'--project-name',$ProjectName)
Invoke-Docker @('info','--format','{{.ServerVersion}}') | Out-Null
Invoke-Docker ($compose + @('config','--quiet'))
if ($manifest.images_included) {
    Write-Host 'Loading the exported Docker images...'
    Invoke-Docker @('image','load','--input',(Join-Path $backup 'images.tar'))
} else {
    Write-Host 'Images were omitted: internet access is required to download and build them.'
    Invoke-Docker ($compose + @('build','backend','frontend'))
}
# Database-only startup prevents application startup from seeding tables before restore.
Invoke-Docker ($compose + @('up','-d','db'))
$userName=[string]$manifest.database_user
$database=[string]$manifest.database_name
Wait-DemoDatabase $compose $userName $database
$tables=((Invoke-Docker ($compose + @('exec','-T','db','psql','-U',$userName,'-d',$database,'-At','-v','ON_ERROR_STOP=1','-c',"SELECT count(*) FROM pg_tables WHERE schemaname='public';"))) -join '').Trim()
if ($tables -ne '0') { throw "Restore refused: project '$ProjectName' already contains database tables. Your existing data was NOT overwritten. If already restored, run the Start command in README-LAPTOP-DEMO.md. For a separate copy use -ProjectName valhalla-demo2 (stop conflicting app ports first)." }
# Refuse a nonempty target document volume before modifying the database.
$checkCode=@'
from pathlib import Path
p=Path('/app/storage')
if p.exists() and any(p.iterdir()):
    raise SystemExit('Restore refused: the target document volume is not empty.')
'@
$checkCode | & docker @compose run --rm -T --no-deps --entrypoint python backend -
if ($LASTEXITCODE -ne 0) { throw 'Document-volume check failed. No database import was performed.' }
Write-Host 'Restoring the database into the separate demo project...'
Invoke-Docker ($compose + @('cp',(Join-Path $backup 'database.dump'),'db:/tmp/valhalla-demo-restore.dump'))
try {
    Invoke-Docker ($compose + @('exec','-T','db','pg_restore','--username',$userName,'--dbname',$database,'--no-owner','--no-privileges','--exit-on-error','--single-transaction','/tmp/valhalla-demo-restore.dump'))
} finally { & docker @compose exec -T db rm -f /tmp/valhalla-demo-restore.dump | Out-Null }
$actual=((Invoke-Docker ($compose + @('exec','-T','db','psql','-U',$userName,'-d',$database,'-At','-v','ON_ERROR_STOP=1','-c',$script:DemoCountSql))) -join '').Trim() | ConvertFrom-Json
foreach ($key in @('users','companies','quotes','shipments')) {
    if ($actual.$key -ne $manifest.counts.$key) { throw "Restored row count differs for $key. The app remains stopped; inspect the backup before continuing." }
}
Write-Host 'Restoring uploaded documents...'
$mount=$backup+':/demo-backup:ro'
$restoreCode=Get-Content -LiteralPath (Join-Path $project 'docs/demo_restore_documents.py') -Raw
$restoreCode | & docker @compose run --rm -T --no-deps --entrypoint python --volume $mount backend -
if ($LASTEXITCODE -ne 0) { throw 'Database restored, but document restore failed. The app remains stopped. See README-LAPTOP-DEMO.md recovery instructions; do not overwrite the database.' }
Write-Host 'Starting the demo application...'
Invoke-Docker ($compose + @('up','-d','--no-build'))
$ready=$false
for ($i=0;$i -lt 60;$i++) {
    try {
        $health=Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:8000/health' -TimeoutSec 2
        $front=Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:5173/' -TimeoutSec 2
        if ($health.StatusCode -eq 200 -and $front.StatusCode -eq 200) { $ready=$true; break }
    } catch { }
    Start-Sleep -Seconds 1
}
if (-not $ready) { throw 'Data restored, but the application is not responding yet. Check the compose logs using the same files/project shown in README-LAPTOP-DEMO.md.' }
Write-Host "`nDEMO READY: http://localhost:5173" -ForegroundColor Green
Write-Host ('Verified rows: users={0}, companies={1}, quotes={2}, shipments={3}' -f $actual.users,$actual.companies,$actual.quotes,$actual.shipments)
Write-Host 'Use the same account logins and passwords as your desktop. Data will remain in the laptop demo volumes after restart.'
