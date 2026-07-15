$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\..\frontend"

$npmCmd = Get-Command npm -ErrorAction SilentlyContinue
if ($npmCmd) {
  npm install
  npm run dev -- --host 0.0.0.0 --port 5173
  exit
}

$nodeDir = "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin"
$binDir = "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\bin"
$pnpm = Join-Path $binDir "pnpm.cmd"
if (-not (Test-Path $pnpm)) {
  throw "npm/pnpm nao encontrado. Instale Node.js 20+ ou rode dentro do Codex com o runtime empacotado."
}

$env:PATH = "$nodeDir;$binDir;$env:PATH"
& $pnpm install
& $pnpm run dev -- --host 0.0.0.0 --port 5173
