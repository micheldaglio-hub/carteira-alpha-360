$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\..\backend"

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
$pythonExe = if ($pythonCmd) { $pythonCmd.Source } else { "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" }
if (-not (Test-Path $pythonExe)) {
  throw "Python nao encontrado. Instale Python 3.12+ ou rode dentro do Codex com o runtime empacotado."
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
  & $pythonExe -m venv .venv
}
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
