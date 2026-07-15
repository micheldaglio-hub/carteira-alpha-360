param(
  [string]$OutputDir = "",
  [string]$DatabaseUrl = ""
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path "$PSScriptRoot\.."
if (-not $OutputDir) {
  $OutputDir = Join-Path $ProjectRoot "backups"
}
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

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

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"

if ($DatabaseUrl -like "sqlite*") {
  $dbPath = $DatabaseUrl -replace "^sqlite:///", ""
  if (-not [System.IO.Path]::IsPathRooted($dbPath)) {
    $dbPath = Join-Path $ProjectRoot $dbPath
  }
  if (-not (Test-Path $dbPath)) {
    throw "Banco SQLite nao encontrado: $dbPath"
  }
  $target = Join-Path $OutputDir "carteira-alpha-sqlite-$timestamp.db"
  Copy-Item -LiteralPath $dbPath -Destination $target -Force
  Write-Output "Backup SQLite criado em: $target"
  exit 0
}

$pgDump = Get-Command pg_dump -ErrorAction SilentlyContinue
if (-not $pgDump) {
  throw "pg_dump nao encontrado no PATH. Instale PostgreSQL tools ou use o painel do Supabase para backup gerenciado."
}

$targetSql = Join-Path $OutputDir "carteira-alpha-postgres-$timestamp.dump"
$postgresUrl = $DatabaseUrl -replace "^postgresql\+psycopg://", "postgresql://"
& $pgDump.Source --format=custom --no-owner --no-acl --file $targetSql $postgresUrl
if ($LASTEXITCODE -ne 0) {
  throw "pg_dump falhou com exit code $LASTEXITCODE"
}
Write-Output "Backup PostgreSQL criado em: $targetSql"
