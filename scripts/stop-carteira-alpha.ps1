$ErrorActionPreference = "Stop"

$ports = @(5173, 8000)
$connections = Get-NetTCPConnection -LocalPort $ports -State Listen -ErrorAction SilentlyContinue

if (-not $connections) {
  Write-Host "Nenhum processo do Carteira Alpha 360 encontrado nas portas 5173/8000."
  exit 0
}

$connections |
  Select-Object -ExpandProperty OwningProcess -Unique |
  ForEach-Object {
    Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
    Write-Host "Processo finalizado: $_"
  }

Write-Host "Carteira Alpha 360 parado."
