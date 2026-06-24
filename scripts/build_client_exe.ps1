$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$python = Join-Path $root ".venv\Scripts\python.exe"
$client = Join-Path $root "scripts\extractor_pdf_client.py"
$icon = $null

Set-Location $root

& $python -m PyInstaller `
    --onefile `
    --name ExtractorPDFClient `
    --clean `
    --distpath "$root\dist" `
    --workpath "$root\build\pyinstaller" `
    --specpath "$root\build\pyinstaller" `
    $client

Write-Host ""
Write-Host "Ejecutable generado en:" -ForegroundColor Green
Write-Host "  $root\dist\ExtractorPDFClient.exe"
