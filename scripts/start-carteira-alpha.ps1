param(
  [switch]$NoBrowser,
  [switch]$NoInstall
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path "$PSScriptRoot\.."
$BackendPath = Join-Path $ProjectRoot "backend"
$FrontendPath = Join-Path $ProjectRoot "frontend"
$LogsPath = Join-Path $ProjectRoot "logs"
$UrlsFile = Join-Path $LogsPath "carteira-alpha-urls.txt"
$DiagnosticsScript = Join-Path $PSScriptRoot "check-lan-access.ps1"

New-Item -ItemType Directory -Force -Path $LogsPath | Out-Null

function Test-PortListening {
  param([int]$Port)
  $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
  return $null -ne $connection
}

function Get-PrimaryIPv4 {
  $addresses = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object {
      $_.IPAddress -notlike "127.*" -and
      $_.IPAddress -notlike "169.254.*" -and
      $_.PrefixOrigin -ne "WellKnown"
    } |
    Sort-Object {
      if ($_.InterfaceAlias -match "Ethernet|Wi-Fi|Wireless") { 0 } else { 1 }
    }, InterfaceMetric

  return ($addresses | Select-Object -First 1).IPAddress
}

function Wait-HttpOk {
  param(
    [string]$Url,
    [int]$Seconds = 45
  )

  $deadline = (Get-Date).AddSeconds($Seconds)
  do {
    try {
      $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 3
      if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
        return $true
      }
    } catch {
      Start-Sleep -Milliseconds 800
    }
  } while ((Get-Date) -lt $deadline)

  return $false
}

function Ensure-Backend {
  if (-not (Test-Path (Join-Path $BackendPath ".venv\Scripts\python.exe"))) {
    if ($NoInstall) { throw "Ambiente Python nao encontrado em backend\.venv." }
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    $pythonExe = if ($pythonCmd) { $pythonCmd.Source } else { "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" }
    if (-not (Test-Path $pythonExe)) { throw "Python nao encontrado." }
    Push-Location $BackendPath
    & $pythonExe -m venv .venv
    & .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    Pop-Location
  }

  if (-not (Test-PortListening 8000)) {
    $log = Join-Path $LogsPath "backend.log"
    $err = Join-Path $LogsPath "backend.err.log"
    $command = "Set-Location '$BackendPath'; .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
    Start-Process -FilePath powershell.exe -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $command) -WorkingDirectory $BackendPath -WindowStyle Hidden -RedirectStandardOutput $log -RedirectStandardError $err | Out-Null
  }

  if (-not (Wait-HttpOk "http://127.0.0.1:8000/api/health" 45)) {
    throw "Backend nao respondeu em http://127.0.0.1:8000/api/health. Veja logs\backend.err.log."
  }
}

function Ensure-Frontend {
  $nodeDir = "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin"
  $binDir = "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\bin"
  $fallbackBinDir = Join-Path $binDir "fallback"
  $pnpmCandidates = @(
    (Join-Path $binDir "pnpm.cmd"),
    (Join-Path $fallbackBinDir "pnpm.cmd")
  )
  $pnpm = $pnpmCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
  $npmCmd = Get-Command npm -ErrorAction SilentlyContinue

  if (-not (Test-Path (Join-Path $FrontendPath "node_modules"))) {
    if ($NoInstall) { throw "Dependencias do frontend nao encontradas em frontend\node_modules." }
    Push-Location $FrontendPath
    if ($npmCmd) {
      & npm install
    } elseif ($pnpm) {
      $env:PATH = "$nodeDir;$fallbackBinDir;$binDir;$env:PATH"
      & $pnpm install
    } else {
      throw "npm/pnpm nao encontrado."
    }
    Pop-Location
  }

  if (-not (Test-PortListening 5173)) {
    $log = Join-Path $LogsPath "frontend.log"
    $err = Join-Path $LogsPath "frontend.err.log"
    if ($npmCmd) {
      $command = "Set-Location '$FrontendPath'; npm run dev -- --host 0.0.0.0 --port 5173"
    } elseif ($pnpm) {
      $command = "`$env:PATH = '$nodeDir;$fallbackBinDir;$binDir;' + `$env:PATH; Set-Location '$FrontendPath'; & '$pnpm' run dev -- --host 0.0.0.0 --port 5173"
    } else {
      throw "npm/pnpm nao encontrado."
    }
    Start-Process -FilePath powershell.exe -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $command) -WorkingDirectory $FrontendPath -WindowStyle Hidden -RedirectStandardOutput $log -RedirectStandardError $err | Out-Null
  }

  if (-not (Wait-HttpOk "http://127.0.0.1:5173" 45)) {
    throw "Frontend nao respondeu em http://127.0.0.1:5173. Veja logs\frontend.err.log."
  }
}

Ensure-Backend
Ensure-Frontend

$ip = Get-PrimaryIPv4
$computerUrl = "http://$env:COMPUTERNAME`:5173"
$localUrl = "http://127.0.0.1:5173"
$networkUrl = if ($ip) { "http://$ip`:5173" } else { "IP de rede nao encontrado" }

@"
Carteira Alpha 360
Atualizado em: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

Neste computador:
$localUrl
http://localhost:5173

Outros computadores da mesma rede:
$computerUrl
$networkUrl

Backend:
http://127.0.0.1:8000/api/health
"@ | Set-Content -Path $UrlsFile -Encoding UTF8

if (Test-Path $DiagnosticsScript) {
  try {
    & $DiagnosticsScript -Quiet
  } catch {
    Write-Warning "Nao foi possivel gerar diagnostico de rede: $($_.Exception.Message)"
  }
}

if (-not $NoBrowser) {
  Start-Process $localUrl | Out-Null
}

Write-Host "Carteira Alpha 360 iniciado."
Write-Host "Local: $localUrl"
Write-Host "Rede:  $networkUrl"
Write-Host "Nome:  $computerUrl"
Write-Host "URLs salvas em: $UrlsFile"
