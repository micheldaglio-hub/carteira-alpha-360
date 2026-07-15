param(
  [switch]$Pause
)

$ErrorActionPreference = "Stop"

function Test-IsAdmin {
  $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
  $principal = New-Object Security.Principal.WindowsPrincipal($identity)
  return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Upsert-FirewallRule {
  param(
    [string]$DisplayName,
    [int]$Port
  )

  $existing = Get-NetFirewallRule -DisplayName $DisplayName -ErrorAction SilentlyContinue

  if (-not $existing) {
    New-NetFirewallRule `
      -DisplayName $DisplayName `
      -Direction Inbound `
      -Action Allow `
      -Protocol TCP `
      -LocalPort $Port `
      -Profile Any `
      -RemoteAddress LocalSubnet `
      -Description "Permite acesso ao Carteira Alpha 360 somente de dispositivos da rede local." | Out-Null
    Write-Host "Criada regra: $DisplayName" -ForegroundColor Green
    return
  }

  $existing | Set-NetFirewallRule -Enabled True -Action Allow -Direction Inbound -Profile Any | Out-Null
  $existing | Get-NetFirewallPortFilter | Set-NetFirewallPortFilter -Protocol TCP -LocalPort $Port | Out-Null
  $existing | Get-NetFirewallAddressFilter | Set-NetFirewallAddressFilter -RemoteAddress LocalSubnet | Out-Null
  Write-Host "Regra atualizada: $DisplayName" -ForegroundColor Green
}

if (-not (Test-IsAdmin)) {
  Write-Host "Abra este script como Administrador para liberar o acesso pela rede local." -ForegroundColor Yellow
  Write-Host "Use o arquivo CONFIGURAR_ACESSO_REDE_ADMIN.bat na raiz do projeto." -ForegroundColor Yellow
  if ($Pause) { Read-Host "Pressione Enter para fechar" | Out-Null }
  exit 2
}

Upsert-FirewallRule -DisplayName "Carteira Alpha 360 - Frontend LAN (5173)" -Port 5173
Upsert-FirewallRule -DisplayName "Carteira Alpha 360 - Backend LAN (8000)" -Port 8000

Write-Host ""
Write-Host "Firewall configurado. O acesso ficou limitado a LocalSubnet nas portas 5173 e 8000." -ForegroundColor Cyan
Write-Host "Se outro roteador da casa estiver criando outra sub-rede, configure esse roteador como Bridge/AP." -ForegroundColor Cyan

if ($Pause) {
  Read-Host "Pressione Enter para fechar" | Out-Null
}
