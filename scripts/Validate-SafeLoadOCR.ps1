# Windows PowerShell 5.1; local-only. No deployment, database, or uploads modified.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv-warehouse-test\Scripts\python.exe'
if (-not (Test-Path $python)) { throw 'Missing .venv-warehouse-test Python environment.' }
$paths = @(
    $env:SAFE_LOAD_TESSERACT_PATH,
    (Join-Path $env:ProgramFiles 'Tesseract-OCR\tesseract.exe'),
    (Join-Path ${env:ProgramFiles(x86)} 'Tesseract-OCR\tesseract.exe'),
    (Join-Path $env:LOCALAPPDATA 'Programs\Tesseract-OCR\tesseract.exe')
) | Where-Object { $_ -and (Test-Path $_) }
$command = Get-Command tesseract -ErrorAction SilentlyContinue
if ($command) { $paths = @($command.Source) + $paths }
if (-not $paths) {
    Write-Host 'Tesseract OCR is NOT installed or cannot be found.' -ForegroundColor Red
    Write-Host 'Install Tesseract OCR for Windows with English (eng) language data.'
    Write-Host 'Then rerun this script. Do NOT deploy or override the Safe Load rejection.'
    exit 2
}
$tesseract = $paths | Select-Object -First 1
Write-Host "Using OCR: $tesseract"
& $tesseract --version
$langs = (& $tesseract --list-langs 2>&1 | Out-String)
if ($langs -notmatch '(?m)^eng\s*$') { throw 'Tesseract English language data (eng) is missing.' }
$env:SAFE_LOAD_TESSERACT_PATH = $tesseract
Push-Location (Join-Path $root 'backend')
try {
    & $python -m pytest tests/test_safe_load_automation.py tests/test_safe_load_numbered_reader.py tests/test_safe_load_photos.py tests/test_safe_load_qa_progress.py tests/test_safe_load_vin_reader.py -q --tb=short --disable-warnings
    $result = $LASTEXITCODE
} finally { Pop-Location }
if ($result -ne 0) { throw "OCR tests failed with exit code $result. Do NOT deploy." }
Write-Host 'Targeted OCR tests passed. Run full backend tests before deploying.' -ForegroundColor Green
