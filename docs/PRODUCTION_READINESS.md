# Production Readiness - Carteira Alpha 360

Status: fundacao ampliada em 2026-07-13.

## Objetivo

Este documento define a regua minima para o Carteira Alpha 360 sair de preview local e entrar em uma avaliacao profissional de produto SaaS financeiro.

O objetivo nao e declarar que o sistema e perfeito. O objetivo e impedir que o sistema suba em producao com configuracoes inseguras, dados demonstrativos ou falsa confianca operacional.

## Controles implementados

### Runtime Safety Gate

Arquivo:

- `backend/app/core/runtime_safety.py`

Comportamento:

- Em `development`, configuracoes fracas viram warnings.
- Em `production`, configuracoes criticas bloqueiam o startup do backend.

Bloqueios criticos em producao:

- `SECRET_KEY` padrao ou curta.
- `DATABASE_URL` usando SQLite.
- `SEED_DEMO_DATA=true`.
- `MARKET_DATA_PROVIDER=mock`.
- Trading Desk habilitado sem chave de integracao.

Warnings em producao:

- CORS ainda aberto para localhost/rede privada.
- Token de acesso com expiracao longa.

### Readiness Endpoint

Endpoint:

- `GET /api/ready`

Retorna:

- Status do banco.
- Ambiente atual.
- Se esta em modo producao.
- Quantidade de findings criticos.
- Quantidade de warnings.
- Findings sanitizados, sem secrets.

### Security Headers

Aplicados em todas as respostas do backend:

- `X-Request-ID`
- `X-Process-Time-Ms`
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`
- `X-Permitted-Cross-Domain-Policies: none`
- `Cross-Origin-Opener-Policy: same-origin`
- `Strict-Transport-Security` em producao HTTPS.

### Auth Rate Limit

Arquivo:

- `backend/app/core/rate_limit.py`

Aplicado em:

- `POST /api/auth/login`
- `POST /api/auth/register`

Objetivo:

- Reduzir brute force local e ataques simples de repeticao.

Limite:

- Implementacao atual e em memoria por processo.
- Producao multi-worker deve trocar para Redis ou outro storage compartilhado.

### CI

Arquivo:

- `.github/workflows/ci.yml`

Executa:

- Testes backend com `python -m unittest discover -s tests`.
- Build frontend com `pnpm run build`.
- E2E smoke com Playwright.

### Template de producao

Arquivo:

- `.env.production.example`

Regras:

- `ENVIRONMENT=production`
- `SEED_DEMO_DATA=false`
- PostgreSQL obrigatorio.
- CORS restrito ao dominio oficial.
- Provider mock proibido como fonte principal.
- Chaves externas ficam somente no backend.

### Observability / Auditoria / Jobs

Arquivos:

- `backend/app/core/observability.py`
- `backend/app/services/audit.py`
- `backend/app/services/job_runner.py`
- `backend/app/routers/ops.py`

Endpoints:

- `GET /api/ops/observability`
- `GET /api/ops/audit`
- `GET /api/ops/jobs`
- `POST /api/ops/jobs/{job_name}/run`

Entregue:

- Logs estruturados JSON.
- Metricas de requests em memoria.
- Auditoria persistente em `audit_events`.
- Registro de jobs em `job_runs`.
- Jobs `ops.heartbeat`, `ops.cleanup`, `guardian.snapshot`, `market_data.user_assets`, `market_data.model_portfolios`, `macro_fx.refresh` e `financial.formula_audit`.
- Tela `Operacoes`.
- Scripts `backup-database.ps1` e `restore-database.ps1`.
- Scripts `migrate-to-supabase.ps1` e `migrate_sqlite_to_postgres.py` para migracao controlada SQLite -> PostgreSQL/Supabase.
- Dockerfiles para backend/frontend e `docker-compose.prod.yml`.
- Teste E2E Playwright.
- Data Evidence Ledger em `data_evidence_ledger`, com endpoint `GET /api/ops/evidence` para rastrear origem de dados e formulas.

### PostgreSQL / Supabase

Arquivos:

- `.env.supabase.example`
- `scripts/migrate-to-supabase.ps1`
- `scripts/migrate_sqlite_to_postgres.py`

Controles:

- `DATABASE_AUTO_CREATE_TABLES=false` em producao.
- Schema por Alembic.
- Backup local antes de migrar.
- Dry-run por padrao.
- Copia de dados somente com `-Apply`.
- Auditoria matematica executada ao final do fluxo.

### Auditoria real das formulas financeiras

Arquivo:

- `backend/app/services/financial_formula_auditor.py`

Job:

- `financial.formula_audit`

Casos auditados:

- Patrimonio necessario para renda passiva.
- Aporte sem retorno.
- Separacao entre capital gain e renda passiva.
- CDI diario composto.
- Backtest time-weighted sem aporte virar lucro.
- Valor real descontando inflacao.

### Data Lineage

Arquivos:

- `backend/app/services/data_lineage.py`
- `backend/alembic/versions/20260713_0007_data_evidence_ledger.py`

Endpoint:

- `GET /api/ops/evidence`

O ledger registra fonte, provider, formula, versao, hash dos insumos, confianca, qualidade e status de dados criticos. A primeira integracao cobre Market Data, Portfolio Backtest e Financial Formula Auditor.

## Pontos ainda nao resolvidos para nivel institucional

Estes itens continuam obrigatorios antes de apresentar como produto financeiro institucional:

- Autenticacao com refresh token, rotacao e revogacao de sessao.
- Rate limit distribuido com Redis.
- Monitoramento externo gerenciado, alertas e metricas de longo prazo.
- Backups automaticos agendados fora do processo da API e restore testado em ambiente separado.
- Deploy HTTPS real com dominio e HSTS.
- Auditoria independente das formulas financeiras.
- Historico real de precos/proventos com fontes persistidas.
- Politica de divergencia entre provedores.
- Termos de uso, politica de privacidade e disclaimer juridico revisados.
- Testes de carga.
- Revisao de acessibilidade.
- Pipeline de deploy separado de CI.
- Secrets gerenciados por plataforma, nunca por arquivo local.

## Comando de validacao local

```powershell
$env:PYTHONPATH='C:\Users\miche\OneDrive\Documentos\CarteiraAlpha\backend'
& 'C:\Users\miche\OneDrive\Documentos\CarteiraAlpha\backend\.venv\Scripts\python.exe' -m unittest discover -s backend\tests
```

Frontend:

```powershell
cd frontend
pnpm run build
```

Readiness:

```powershell
Invoke-WebRequest -UseBasicParsing -Uri http://127.0.0.1:8000/api/ready
```
