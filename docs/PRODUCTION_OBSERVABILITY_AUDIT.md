# Production / Observability / Auditoria

Status: fundacao implementada em 2026-07-13.

## Objetivo

Transformar o Carteira Alpha 360 em uma base operavel para ambiente SaaS:

- logs estruturados;
- metricas operacionais;
- auditoria persistente;
- jobs automaticos;
- backup/restore;
- readiness;
- Docker para deploy;
- PostgreSQL/Supabase-ready;
- testes E2E.

## Arquivos principais

- `backend/app/core/observability.py`
- `backend/app/services/audit.py`
- `backend/app/services/job_runner.py`
- `backend/app/routers/ops.py`
- `backend/alembic/versions/20260713_0006_observability_audit_jobs.py`
- `frontend/src/pages/Ops.jsx`
- `scripts/backup-database.ps1`
- `scripts/restore-database.ps1`
- `frontend/tests/e2e/app-smoke.spec.js`
- `backend/Dockerfile`
- `frontend/Dockerfile`
- `docker-compose.prod.yml`

## Banco de dados

Tabelas adicionadas:

### `audit_events`

Registra eventos rastreaveis:

- login;
- cadastro;
- mutacoes HTTP;
- execucao manual de jobs;
- eventos de sistema.

Campos principais:

- `user_id`
- `actor_type`
- `event_type`
- `category`
- `severity`
- `action`
- `resource_type`
- `resource_id`
- `request_id`
- `ip_address`
- `user_agent`
- `message`
- `metadata_json`
- `created_at`

### `job_runs`

Registra cada execucao de job:

- `job_name`
- `status`
- `started_at`
- `finished_at`
- `duration_ms`
- `rows_affected`
- `message`
- `details_json`

## Endpoints operacionais

Todos exigem usuario autenticado.

- `GET /api/ops/observability`
- `GET /api/ops/audit`
- `GET /api/ops/jobs`
- `POST /api/ops/jobs/{job_name}/run`

## Logs estruturados

Cada request gera log JSON com:

- timestamp;
- level;
- request_id;
- method;
- path;
- status_code;
- duration_ms.

Headers continuam sendo retornados:

- `X-Request-ID`
- `X-Process-Time-Ms`

## Auditoria

Eventos automaticos:

- `login_success`
- `login_failed`
- `user_registered`
- `http_mutation`
- `manual_job_run_requested`
- `ops_heartbeat`
- `guardian_snapshot`

Regra:

Falha de auditoria nunca pode derrubar request do usuario.

## Jobs

Jobs registrados:

- `ops.heartbeat`
- `ops.cleanup`
- `guardian.snapshot`

Config:

```env
JOBS_ENABLED=false
JOBS_HEARTBEAT_INTERVAL_SECONDS=300
JOBS_CLEANUP_INTERVAL_SECONDS=3600
JOBS_GUARDIAN_INTERVAL_SECONDS=21600
```

Em desenvolvimento, `JOBS_ENABLED=false` evita trabalho em background durante testes.
Em producao, pode ser `true` ou substituido por scheduler externo.

## Backup

SQLite local:

```powershell
.\scripts\backup-database.ps1
```

PostgreSQL/Supabase:

```powershell
.\scripts\backup-database.ps1 -DatabaseUrl "postgresql+psycopg://usuario:senha@host:5432/banco"
```

Requer `pg_dump` no PATH.

## Restore

Restore exige confirmacao explicita:

```powershell
.\scripts\restore-database.ps1 -BackupPath .\backups\arquivo.dump -DatabaseUrl "postgresql+psycopg://usuario:senha@host:5432/banco" -ConfirmRestore
```

SQLite local tambem exige `-ConfirmRestore` e bloqueia destino fora da pasta `backend`.

## Supabase/PostgreSQL

Formato esperado:

```env
DATABASE_URL=postgresql+psycopg://postgres:SENHA@db.PROJETO.supabase.co:5432/postgres
```

Passos:

1. Criar `.env.production` a partir de `.env.production.example`.
2. Configurar `DATABASE_URL` com senha real.
3. Rodar migracoes:

```powershell
.\scripts\db-migrate.ps1
```

4. Validar readiness:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/ready
```

## Docker

Build local:

```powershell
docker compose -f docker-compose.prod.yml --env-file .env.production up --build
```

Observacao:

O compose de producao espera PostgreSQL externo/gerenciado. Para banco local de desenvolvimento, use `docker-compose.yml`.

## Testes E2E

Arquivos:

- `frontend/playwright.config.js`
- `frontend/tests/e2e/app-smoke.spec.js`

Comando:

```powershell
cd frontend
pnpm run e2e
```

O teste faz:

- login demo;
- valida dashboard;
- abre Stress Test;
- abre Copilot;
- envia pergunta e espera fonte `S1`.

## CI

`.github/workflows/ci.yml` agora possui:

- testes backend;
- build frontend;
- E2E smoke com Playwright.

## Limites atuais

- Auditoria ainda nao possui papeis administrativos.
- Jobs usam scheduler em processo; producao multi-instancia deve usar scheduler unico ou fila externa.
- Monitoramento externo via webhook ainda esta preparado em config, mas sem integracao ativa.
- Backups dependem de `pg_dump`/`pg_restore` ou backup gerenciado do provedor.
