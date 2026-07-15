param(
  [Parameter(Mandatory = $true)]
  [string]$BackupPath,
  [string]$DatabaseUrl = "",
  [switch]$ConfirmRestore
)

$ErrorActionPreference = "Stop"

if (-not $ConfirmRestore) {
  throw "Restore bloqueado. Rode novamente com -ConfirmRestore depois de conferir o arquivo de backup e o banco de destino."
}

$ProjectRoot = Resolve-Path "$PSScriptRoot\.."
$resolvedBackup = Resolve-Path $BackupPath

if (-not $DatabaseUrl) {
  $envFile = Join-Path $ProjectRoot ".env"
  if (Test-Path $envFile) {
    $line = Get-Content $envFile | Where-Object { $_ -match "^DATABASE_URL=" } | Select-Object -First 1
    if ($line) {
      $DatabaseUrl = $line.Substring("DATABASE_URL=".Length)
    }
  }
}

if (-not $DatabaseUrl) {
  $DatabaseUrl = "sqlite:///./backend/carteira_alpha.db"
}

if ($DatabaseUrl -like "sqlite*") {
  $dbPath = $DatabaseUrl -replace "^sqlite:///", ""
  if (-not [System.IO.Path]::IsPathRooted($dbPath)) {
    $dbPath = Join-Path $ProjectRoot $dbPath
  }
  $targetResolved = [System.IO.Path]::GetFullPath($dbPath)
  $backendRoot = [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot "backend"))
  if (-not $targetResolved.StartsWith($backendRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Restore SQLite bloqueado: destino fora da pasta backend ($targetResolved)."
  }
  Copy-Item -LiteralPath $resolvedBackup -Destination $targetResolved -Force
  Write-Output "Banco SQLite restaurado em: $targetResolved"
  exit 0
}

$pgRestore = Get-Command pg_restore -ErrorAction SilentlyContinue
if (-not $pgRestore) {
  throw "pg_restore nao encontrado no PATH. Instale PostgreSQL tools ou restaure pelo painel do provedor."
}

$postgresUrl = $DatabaseUrl -replace "^postgresql\+psycopg://", "postgresql://"
& $pgRestore.Source --clean --if-exists --no-owner --no-acl --dbname $postgresUrl $resolvedBackup
if ($LASTEXITCODE -ne 0) {
  throw "pg_restore falhou com exit code $LASTEXITCODE"
}
Write-Output "Banco PostgreSQL restaurado a partir de: $resolvedBackup"
