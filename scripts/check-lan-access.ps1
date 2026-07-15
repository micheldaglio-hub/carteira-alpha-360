param(
  [switch]$Quiet,
  [switch]$OpenReport
)

$ErrorActionPreference = "Continue"

$ProjectRoot = (Resolve-Path "$PSScriptRoot\..").Path
$LogsPath = Join-Path $ProjectRoot "logs"
$UrlsFile = Join-Path $LogsPath "carteira-alpha-urls.txt"
$ReportFile = Join-Path $LogsPath "carteira-alpha-lan-diagnostic.txt"

New-Item -ItemType Directory -Force -Path $LogsPath | Out-Null

function Get-LanIPv4 {
  Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object {
      $_.AddressState -eq "Preferred" -and
      $_.IPAddress -notlike "127.*" -and
      $_.IPAddress -notlike "169.254.*" -and
      $_.InterfaceAlias -notmatch "Loopback|vEthernet|Docker|WSL|Bluetooth"
    } |
    Sort-Object {
      if ($_.InterfaceAlias -match "Ethernet|Wi-Fi|Wireless") { 0 } else { 1 }
    }, InterfaceMetric
}

function Test-HttpEndpoint {
  param([string]$Url)
  try {
    $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 4
    return "OK $($response.StatusCode)"
  } catch {
    return "FALHOU: $($_.Exception.Message)"
  }
}

function Get-RuleStatus {
  param([string]$Name)
  $rule = Get-NetFirewallRule -DisplayName $Name -ErrorAction SilentlyContinue | Select-Object -First 1
  if (-not $rule) { return "NAO ENCONTRADA" }

  $ports = ($rule | Get-NetFirewallPortFilter -ErrorAction SilentlyContinue)
  $address = ($rule | Get-NetFirewallAddressFilter -ErrorAction SilentlyContinue)
  return "$($rule.Enabled) / $($rule.Action) / Perfil $($rule.Profile) / Porta $($ports.LocalPort) / Remoto $($address.RemoteAddress)"
}

$ips = @(Get-LanIPv4)
$profiles = @(Get-NetConnectionProfile -ErrorAction SilentlyContinue)
$listeners = @(Get-NetTCPConnection -LocalPort 5173,8000 -State Listen -ErrorAction SilentlyContinue)
$frontendListening = $listeners | Where-Object { $_.LocalPort -eq 5173 -and ($_.LocalAddress -eq "0.0.0.0" -or $_.LocalAddress -eq "::" -or ($ips.IPAddress -contains $_.LocalAddress)) }
$backendListening = $listeners | Where-Object { $_.LocalPort -eq 8000 -and ($_.LocalAddress -eq "0.0.0.0" -or $_.LocalAddress -eq "::" -or ($ips.IPAddress -contains $_.LocalAddress)) }

$computerUrl = "http://$($env:COMPUTERNAME):5173"
$computerLocalUrl = "http://$($env:COMPUTERNAME).local:5173"
$lanUrls = $ips | ForEach-Object { "http://$($_.IPAddress):5173" }
$backendUrls = $ips | ForEach-Object { "http://$($_.IPAddress):8000/api/health" }

$urlLines = @(
  "Carteira Alpha 360",
  "Atualizado em: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")",
  "",
  "Neste computador:",
  "http://127.0.0.1:5173",
  "http://localhost:5173",
  "",
  "Outros computadores/celulares da mesma rede:",
  $computerUrl,
  $computerLocalUrl
) + $lanUrls + @(
  "",
  "Backend:",
  "http://127.0.0.1:8000/api/health"
) + $backendUrls + @(
  "",
  "Se outro dispositivo nao abrir:",
  "1. Execute CONFIGURAR_ACESSO_REDE_ADMIN.bat uma vez para liberar o Firewall do Windows.",
  "2. Confirme que o outro dispositivo esta na mesma faixa de IP deste PC. Este PC hoje esta em: $($ips.IPAddress -join ", ").",
  "3. Se o outro Wi-Fi usar outra faixa, configure o segundo roteador em modo Bridge/AP ou desative isolamento de clientes."
)

$urlLines | Set-Content -Path $UrlsFile -Encoding UTF8

$report = New-Object System.Collections.Generic.List[string]
$report.Add("Carteira Alpha 360 - Diagnostico de acesso pela rede local")
$report.Add("Gerado em: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")")
$report.Add("")
$report.Add("URLs para testar em outro computador/celular:")
foreach ($line in $urlLines) { $report.Add($line) }
$report.Add("")
$report.Add("Interfaces de rede:")
foreach ($ip in $ips) {
  $report.Add("- $($ip.InterfaceAlias): $($ip.IPAddress)/$($ip.PrefixLength)")
}
if (-not $ips) { $report.Add("- Nenhum IPv4 de LAN encontrado.") }
$report.Add("")
$report.Add("Perfis do Windows:")
foreach ($profile in $profiles) {
  $report.Add("- $($profile.InterfaceAlias): $($profile.Name) / $($profile.NetworkCategory) / IPv4 $($profile.IPv4Connectivity)")
}
$report.Add("")
$report.Add("Portas ouvindo:")
$report.Add("- Frontend 5173: $(if ($frontendListening) { "OK em rede" } else { "NAO esta ouvindo em rede" })")
$report.Add("- Backend 8000: $(if ($backendListening) { "OK em rede" } else { "NAO esta ouvindo em rede" })")
foreach ($listener in $listeners | Sort-Object LocalPort,LocalAddress) {
  $report.Add("  - $($listener.LocalAddress):$($listener.LocalPort) PID $($listener.OwningProcess)")
}
$report.Add("")
$report.Add("Firewall:")
$report.Add("- Carteira Alpha 360 - Frontend LAN (5173): $(Get-RuleStatus "Carteira Alpha 360 - Frontend LAN (5173)")")
$report.Add("- Carteira Alpha 360 - Backend LAN (8000): $(Get-RuleStatus "Carteira Alpha 360 - Backend LAN (8000)")")
$report.Add("")
$report.Add("Teste HTTP local:")
$report.Add("- http://127.0.0.1:5173 => $(Test-HttpEndpoint "http://127.0.0.1:5173")")
$report.Add("- http://127.0.0.1:8000/api/health => $(Test-HttpEndpoint "http://127.0.0.1:8000/api/health")")
foreach ($ip in $ips) {
  $report.Add("- http://$($ip.IPAddress):5173 => $(Test-HttpEndpoint "http://$($ip.IPAddress):5173")")
  $report.Add("- http://$($ip.IPAddress):8000/api/health => $(Test-HttpEndpoint "http://$($ip.IPAddress):8000/api/health")")
}
$report.Add("")
$report.Add("Leitura:")
if (-not $frontendListening -or -not $backendListening) {
  $report.Add("- O app nao esta ouvindo corretamente na rede. Inicie com INICIAR_CARTEIRA_ALPHA_REDE.bat.")
} elseif ((Get-RuleStatus "Carteira Alpha 360 - Frontend LAN (5173)") -eq "NAO ENCONTRADA" -or (Get-RuleStatus "Carteira Alpha 360 - Backend LAN (8000)") -eq "NAO ENCONTRADA") {
  $report.Add("- O app esta ouvindo, mas as regras do firewall nao existem. Execute CONFIGURAR_ACESSO_REDE_ADMIN.bat uma vez.")
} else {
  $report.Add("- Este PC esta pronto para acesso LAN. Se outro dispositivo falhar, o bloqueio provavelmente esta no segundo roteador, sub-rede diferente ou isolamento de clientes.")
}

$report | Set-Content -Path $ReportFile -Encoding UTF8

if (-not $Quiet) {
  $report | ForEach-Object { Write-Host $_ }
}

if ($OpenReport) {
  Start-Process notepad.exe $ReportFile | Out-Null
}
