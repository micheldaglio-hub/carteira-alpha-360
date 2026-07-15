param()

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path "$PSScriptRoot\..").Path
$StartScript = Join-Path $ProjectRoot "scripts\start-carteira-alpha.ps1"
$NetworkBat = Join-Path $ProjectRoot "INICIAR_CARTEIRA_ALPHA_REDE.bat"
$FirewallBat = Join-Path $ProjectRoot "CONFIGURAR_ACESSO_REDE_ADMIN.bat"
$DiagnosticBat = Join-Path $ProjectRoot "DIAGNOSTICAR_ACESSO_REDE.bat"
$Shell = New-Object -ComObject WScript.Shell

function New-Shortcut {
  param(
    [string]$Path,
    [string]$TargetPath,
    [string]$Arguments,
    [string]$Description
  )

  $shortcut = $Shell.CreateShortcut($Path)
  $shortcut.TargetPath = $TargetPath
  $shortcut.Arguments = $Arguments
  $shortcut.WorkingDirectory = $ProjectRoot
  $shortcut.Description = $Description
  $shortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,220"
  $shortcut.Save()
}

$Desktop = [Environment]::GetFolderPath("Desktop")
$Startup = [Environment]::GetFolderPath("Startup")

$DesktopShortcut = Join-Path $Desktop "Carteira Alpha 360.lnk"
$DesktopNetworkShortcut = Join-Path $Desktop "Carteira Alpha 360 Rede.lnk"
$DesktopFirewallShortcut = Join-Path $Desktop "Carteira Alpha 360 Liberar Rede.lnk"
$DesktopDiagnosticShortcut = Join-Path $Desktop "Carteira Alpha 360 Diagnostico Rede.lnk"
$StartupShortcut = Join-Path $Startup "Carteira Alpha 360 Servidor.lnk"

New-Shortcut `
  -Path $DesktopShortcut `
  -TargetPath "powershell.exe" `
  -Arguments "-NoProfile -ExecutionPolicy Bypass -File `"$StartScript`"" `
  -Description "Inicia o Carteira Alpha 360 e abre no navegador."

New-Shortcut `
  -Path $DesktopNetworkShortcut `
  -TargetPath $NetworkBat `
  -Arguments "" `
  -Description "Inicia o Carteira Alpha 360 e mostra URLs para celular/outro computador."

New-Shortcut `
  -Path $DesktopFirewallShortcut `
  -TargetPath $FirewallBat `
  -Arguments "" `
  -Description "Libera o Firewall do Windows para acesso do Carteira Alpha 360 na rede local."

New-Shortcut `
  -Path $DesktopDiagnosticShortcut `
  -TargetPath $DiagnosticBat `
  -Arguments "" `
  -Description "Diagnostica acesso ao Carteira Alpha 360 por outros computadores da rede."

New-Shortcut `
  -Path $StartupShortcut `
  -TargetPath "powershell.exe" `
  -Arguments "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$StartScript`" -NoBrowser -NoInstall" `
  -Description "Inicia o servidor do Carteira Alpha 360 ao entrar no Windows."

Write-Host "Atalhos criados:"
Write-Host "- $DesktopShortcut"
Write-Host "- $DesktopNetworkShortcut"
Write-Host "- $DesktopFirewallShortcut"
Write-Host "- $DesktopDiagnosticShortcut"
Write-Host "- $StartupShortcut"
