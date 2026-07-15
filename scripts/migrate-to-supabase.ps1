param(
  [Parameter(Mandatory = $true)]
  [string]$SupabaseDatabaseUrl,

  [string]$SqliteDatabaseUrl = "",

  [switch]$Apply,

  [switch]$Truncate
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path "$PSScriptRoot\.."
$BackendPath = Join-Path $ProjectRoot "backend"
$PythonPath = Join-Path $BackendPath ".venv\Scripts\python.exe"

if (-not (Test-Path $PythonPath)) {
  throw "Ambiente Python nao encontrado em backend\.venv."
}

if ($SupabaseDatabaseUrl -match "\[YOUR-PASSWORD\]|SUA_SENHA|senha") {
  throw "A connection string ainda contem placeholder de senha. Cole a senha real do banco Supabase para migrar."
}

$NormalizedUrl = $SupabaseDatabaseUrl -replace "^postgresql://", "postgresql+psycopg://"
if (-not $SqliteDatabaseUrl) {
  $SqliteDatabaseUrl = "sqlite:///$((Join-Path $BackendPath 'carteira_alpha.db') -replace '\\','/')"
}

Write-Output "1/4 Backup local antes da migracao..."
& (Join-Path $PSScriptRoot "backup-database.ps1") -DatabaseUrl $SqliteDatabaseUrl | Write-Output

Write-Output "2/4 Aplicando migrations Alembic no Supabase/PostgreSQL..."
$env:DATABASE_URL = $NormalizedUrl
$env:DATABASE_AUTO_CREATE_TABLES = "false"
$env:SEED_DEMO_DATA = "false"
Push-Location $BackendPath
try {
  & $PythonPath -m alembic upgrade head
} finally {
  Pop-Location
}
if ($LASTEXITCODE -ne 0) {
  throw "Alembic falhou com exit code $LASTEXITCODE"
}

Write-Output "3/4 Copiando dados SQLite -> Supabase/PostgreSQL..."
$argsList = @(
  (Join-Path $PSScriptRoot "migrate_sqlite_to_postgres.py"),
  "--sqlite-url", $SqliteDatabaseUrl,
  "--postgres-url", $NormalizedUrl
)
if ($Apply) {
  $argsList += "--apply"
}
if ($Truncate) {
  $argsList += "--truncate"
}
& $PythonPath @argsList
if ($LASTEXITCODE -ne 0) {
  throw "Migracao de dados falhou com exit code $LASTEXITCODE"
}

Write-Output "4/4 Rodando auditoria real das formulas financeiras no ambiente configurado..."
$env:PYTHONPATH = $BackendPath
@'
from app.database import SessionLocal
from app.services.financial_formula_auditor import run_financial_formula_audit

db = SessionLocal()
try:
    report = run_financial_formula_audit(db)
    print(f"financial_formula_audit={report['status']} score={report['score']}")
    if report["status"] != "pass":
        raise SystemExit(1)
finally:
    db.close()
'@ | & $PythonPath -
if ($LASTEXITCODE -ne 0) {
  throw "Auditoria financeira falhou depois da migracao."
}

if (-not $Apply) {
  Write-Output "Dry-run concluido. Nada foi gravado nas tabelas, exceto migrations Alembic e auditoria operacional."
  Write-Output "Para copiar dados, rode novamente com -Apply. Use -Truncate somente se tiver certeza que quer limpar o destino antes."
} else {
  Write-Output "Migracao concluida com sucesso."
}
