$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
  $Python = "python"
}

$env:PYTHONPATH = Join-Path $ProjectRoot "src"

& $Python -m pytest -m "not ocr and not llm and not diagnostico" -q
