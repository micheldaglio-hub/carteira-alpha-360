$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path "$PSScriptRoot\.."
$BackendPath = Join-Path $ProjectRoot "backend"
$PythonPath = Join-Path $BackendPath ".venv\Scripts\python.exe"

if (-not (Test-Path $PythonPath)) {
  throw "Ambiente Python nao encontrado em backend\.venv. Rode .\scripts\run-backend.ps1 uma vez para criar e instalar dependencias."
}

Push-Location $BackendPath
try {
  & $PythonPath -m alembic stamp head
} finally {
  Pop-Location
}
