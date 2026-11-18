[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$ComputerIP)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$parsedAddress = $null
if (-not [System.Net.IPAddress]::TryParse($ComputerIP, [ref]$parsedAddress) -or $parsedAddress.AddressFamily -ne [System.Net.Sockets.AddressFamily]::InterNetwork) {
    throw 'ComputerIP must be your PC IPv4 address, for example 192.168.1.195.'
}
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
    throw 'Node.js with npm is required. Install a supported Node.js LTS version, then reopen PowerShell.'
}
& node.exe -e "const [major,minor]=process.versions.node.split('.').map(Number);if(!((major===22&&minor>=13)||(major===24&&minor>=3)||major>=26)){console.error('Use Node 22.13+ or Node 24.3+ LTS for this Expo SDK.');process.exit(1)}"
if ($LASTEXITCODE -ne 0) { throw 'Update Node.js, then reopen PowerShell and retry.' }
$mobileManifest = Get-Content (Join-Path $PSScriptRoot 'package.json') -Raw | ConvertFrom-Json
Write-Host "Starting Safe Load mobile v$($mobileManifest.version) from $PSScriptRoot"
Write-Host 'Installing the pinned Safe Load SDK 58 dependencies...'
& npm.cmd ci
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Keep the output above for troubleshooting.' }
& npm.cmd run check
if ($LASTEXITCODE -ne 0) { throw 'Safe Load code check failed. Keep the output above for troubleshooting.' }
$env:REACT_NATIVE_PACKAGER_HOSTNAME = $ComputerIP
Write-Host "Keep Docker running. In Safe Load use TMS server URL http://${ComputerIP}:8000"
Write-Host 'Open Expo Go SDK 58 on Android and scan the QR code below. Leave this window running.'
& npx.cmd expo start --go --lan --clear --port 8081
if ($LASTEXITCODE -ne 0) { throw 'Mobile server stopped with an error. Keep the output above for troubleshooting.' }
