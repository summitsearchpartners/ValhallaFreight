[CmdletBinding()]
param(
    [string]$SourceProject = '',
    [string]$SourceComposeProject = '',
    [string]$OutputDirectory = '',
    [switch]$SkipImages
)
$transferRoot = $PSScriptRoot
if (-not $transferRoot) { $transferRoot = Split-Path -Parent $MyInvocation.MyCommand.Path }
if ([string]::IsNullOrWhiteSpace($SourceProject)) { $SourceProject = $transferRoot }
if ([string]::IsNullOrWhiteSpace($OutputDirectory)) { $OutputDirectory = Join-Path ([Environment]::GetFolderPath('UserProfile')) 'Downloads' }
. (Join-Path $transferRoot 'Demo-Transfer.Common.ps1')
Get-Command docker -ErrorAction Stop | Out-Null
$source = (Resolve-Path -LiteralPath $SourceProject).Path
if (-not (Test-Path -LiteralPath (Join-Path $source 'docker-compose.yml'))) { throw 'Choose the existing working ValhallaFreight folder that contains docker-compose.yml.' }
$compose = @('compose','--project-directory',$source,'--file',(Join-Path $source 'docker-compose.yml'))
if ($SourceComposeProject) { $compose += @('--project-name',$SourceComposeProject) }
Invoke-Docker (@('info','--format','{{.ServerVersion}}')) | Out-Null
$backendId = ((Invoke-Docker ($compose + @('ps','-q','backend'))) -join '').Trim()
$dbId = ((Invoke-Docker ($compose + @('ps','-q','db'))) -join '').Trim()
if (-not $backendId -or -not $dbId) { throw 'The existing backend and database must be running. Copy these scripts into the CURRENT working project folder, then rerun. If you use a custom Compose project, pass -SourceComposeProject NAME.' }
$userName = ((Invoke-Docker ($compose + @('exec','-T','db','printenv','POSTGRES_USER'))) -join '').Trim()
$database = ((Invoke-Docker ($compose + @('exec','-T','db','printenv','POSTGRES_DB'))) -join '').Trim()
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$nonce = [Guid]::NewGuid().ToString('N')
$stage = Join-Path ([IO.Path]::GetTempPath()) ('valhalla-demo-'+$nonce)
$project = Join-Path $stage 'ValhallaFreight'
$backup = Join-Path $project 'demo-backup'
New-Item -ItemType Directory -Path $project -Force | Out-Null
New-Item -ItemType Directory -Path $backup -Force | Out-Null
$paused = $false
try {
    Write-Host 'Copying the current application and local settings...'
    foreach ($name in @('backend','frontend','safe-load-mobile','docs','.env','.env.example','.gitignore','.gitattributes','docker-compose.yml','README.md','start-valhalla-freight.ps1')) {
        $path = Join-Path $source $name
        if (-not (Test-Path -LiteralPath $path)) { continue }
        if ((Get-Item -LiteralPath $path -Force).PSIsContainer) { Copy-DemoTree $path (Join-Path $project $name) }
        else { Copy-Item -LiteralPath $path -Destination $project -Force }
    }
    foreach ($name in @('Export-Demo.ps1','Restore-Demo.ps1','Demo-Transfer.Common.ps1','README-LAPTOP-DEMO.md')) { Copy-Item -LiteralPath (Join-Path $transferRoot $name) -Destination $project -Force }
    Copy-Item -LiteralPath (Join-Path $transferRoot 'docs/demo_restore_documents.py') -Destination (Join-Path $project 'docs/demo_restore_documents.py') -Force
    $runtime = @{}
    foreach ($service in @('backend','frontend')) {
        $cid = ((Invoke-Docker ($compose + @('ps','--all','-q',$service))) -join '').Trim()
        if (-not $cid) { throw "No $service container found. Start the current application before exporting." }
        $envJson = (Invoke-Docker @('inspect','--format','{{json .Config.Env}}',$cid)) -join "`n"
        $envMap = @{}
        foreach ($entry in ($envJson | ConvertFrom-Json)) {
            $parts = $entry -split '=',2
            if ($parts.Count -eq 2 -and ($parts[0] -match '^(JWT_SECRET_KEY|INTEGRATION_SECRET_KEY|DEFAULT_ADMIN_EMAIL|DEFAULT_ADMIN_PASSWORD|DAYTON_.*|SMTP_.*|BROKER_NOTIFICATION_EMAIL|VITE_.*)$')) {
                $envMap[$parts[0]] = $parts[1].Replace('$','$$')
            }
        }
        $runtime[$service] = @{environment=$envMap}
    }
    $runtime['frontend']['environment']['VITE_API_URL']='http://localhost:8000/api/v1'
    $runtime['backend']['environment']['CORS_ORIGINS']='http://localhost:5173'
    Write-Host 'Briefly pausing the backend to snapshot the database and uploaded files together...'
    Invoke-Docker ($compose + @('pause','backend')) | Out-Null
    $paused = $true
    try {
        $dumpPath = '/tmp/valhalla-demo-'+$nonce+'.dump'
        Invoke-Docker ($compose + @('exec','-T','db','pg_dump','--username',$userName,'--dbname',$database,'--format=custom','--no-owner','--no-acl','--file',$dumpPath))
        Invoke-Docker ($compose + @('exec','-T','db','pg_restore','--list',$dumpPath)) | Out-Null
        Invoke-Docker ($compose + @('cp',('db:'+$dumpPath),(Join-Path $backup 'database.dump')))
        $counts = ((Invoke-Docker ($compose + @('exec','-T','db','psql','-U',$userName,'-d',$database,'-At','-v','ON_ERROR_STOP=1','-c',$script:DemoCountSql))) -join '').Trim() | ConvertFrom-Json
        # The backend is paused, so create the document archive in a temporary helper
        # using the exact same volumes. Do not exec into the paused container.
        $archiveCode = @'
import os,tarfile
from pathlib import Path
root=Path('/app/storage')
root.mkdir(parents=True,exist_ok=True)
with tarfile.open('/demo-backup/documents.tar.gz','w:gz') as archive:
    for item in root.iterdir():
        archive.add(item,arcname=item.name)
print('Uploaded document archive complete.')
'@
        $mount = $backup + ':/demo-backup'
        $archiveCode | & docker @compose run --rm -T --no-deps --pull never --entrypoint python --volume $mount backend -
        if ($LASTEXITCODE -ne 0) { throw 'Document archive failed. No demo ZIP was created.' }
        Invoke-Docker ($compose + @('exec','-T','db','rm','-f',$dumpPath))
    } finally {
        if ($paused) { Invoke-Docker ($compose + @('unpause','backend')) | Out-Null; $paused=$false }
    }
    $services = @{backend=$runtime['backend'];frontend=$runtime['frontend']}
    if (-not $SkipImages) {
        Write-Host 'Saving Docker images for laptop use (this can take several minutes)...'
        $tags = @()
        foreach ($service in @('db','backend','frontend')) {
            $cid = ((Invoke-Docker ($compose + @('ps','--all','-q',$service))) -join '').Trim()
            $imageId = ((Invoke-Docker @('inspect','--format','{{.Image}}',$cid)) -join '').Trim()
            $tag = 'valhalla-demo-'+$service+':'+$stamp
            Invoke-Docker @('image','tag',$imageId,$tag)
            $tags += $tag
            if (-not $services.ContainsKey($service)) { $services[$service]=@{} }
            $services[$service]['image']=$tag
            $services[$service]['pull_policy']='never'
        }
        Invoke-Docker (@('image','save','--output',(Join-Path $backup 'images.tar'))+$tags)
    }
    Write-Utf8 (Join-Path $project 'docker-compose.demo.json') (@{services=$services} | ConvertTo-Json -Depth 8)
    $files = @{}
    foreach ($name in @('database.dump','documents.tar.gz','images.tar')) {
        $path=Join-Path $backup $name
        if (Test-Path -LiteralPath $path) { $files[$name]=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash }
    }
    $manifest=@{format=1;created_at=(Get-Date).ToUniversalTime().ToString('o');database_user=$userName;database_name=$database;counts=$counts;files=$files;images_included=(-not $SkipImages)}
    Write-Utf8 (Join-Path $backup 'manifest.json') ($manifest | ConvertTo-Json -Depth 8)
    New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
    $output = Join-Path $OutputDirectory ('ValhallaFreight-Demo-'+$stamp+'.zip')
    if (Test-Path -LiteralPath $output) { throw 'An export with this timestamp already exists. Rerun after one second.' }
    Write-Host 'Creating the complete laptop ZIP...'
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [IO.Compression.ZipFile]::CreateFromDirectory($stage,$output,[IO.Compression.CompressionLevel]::Optimal,$false)
    Write-Host "`nCOMPLETE: $output" -ForegroundColor Green
    Write-Host ('Database rows: users={0}, companies={1}, quotes={2}, shipments={3}' -f $counts.users,$counts.companies,$counts.quotes,$counts.shipments)
    Write-Host 'Copy THAT newly created ZIP to the laptop. It contains actual account data and secrets; keep it private.'
} finally {
    if ($paused) { & docker @compose unpause backend | Out-Null }
    if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage -Recurse -Force }
}
