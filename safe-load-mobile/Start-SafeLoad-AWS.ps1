[CmdletBinding()]
param(
    [ValidateSet('lan','tunnel')][string]$Connection = 'tunnel'
)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
    throw 'Node.js/npm is required. Install Node.js LTS and reopen PowerShell.'
}
$env:EXPO_PUBLIC_SAFELOAD_SERVER_URL = 'https://valhallatms.com'
Write-Host '=== SAFE LOAD - AWS CONNECTED MOBILE TEST ==='
Write-Host 'Backend: https://valhallatms.com'
Write-Host 'Use a test warehouse account and a test shipment first.'
Write-Host 'The Expo development server runs on this PC; the TMS backend runs on AWS.'
& npm.cmd ci
if ($LASTEXITCODE -ne 0) { throw 'npm ci failed.' }
& npm.cmd run check
if ($LASTEXITCODE -ne 0) { throw 'TypeScript check failed.' }
& npm.cmd test
if ($LASTEXITCODE -ne 0) { throw 'Mobile tests failed.' }
Write-Host 'Scan the Expo QR code with Expo Go (SDK-compatible version).'
if ($Connection -eq 'tunnel') {
    & npx.cmd expo start --go --tunnel --clear
} else {
    & npx.cmd expo start --go --lan --clear
}
if ($LASTEXITCODE -ne 0) { throw 'Expo failed. Review output above.' }
