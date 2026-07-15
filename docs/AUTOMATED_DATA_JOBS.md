# Automated Data Jobs

Status: implementado em 2026-07-13.

## Objetivo

Executar rotinas automaticas de dados, governanca e auditoria sem depender da interface React.

## Scheduler

Arquivo principal:

- `backend/app/services/job_runner.py`

Os jobs rodam apenas quando `JOBS_ENABLED=true`.

## Jobs registrados

- `ops.heartbeat`: registra batimento operacional em auditoria.
- `ops.cleanup`: remove auditoria expirada e cache vencido.
- `guardian.snapshot`: recalcula monitoramento Guardian para os usuarios.
- `market_data.user_assets`: sincroniza dados de mercado dos ativos presentes nas carteiras.
- `market_data.model_portfolios`: recalcula carteiras recomendadas, score institucional e governanca.
- `macro_fx.refresh`: atualiza Macro / FX Engine com Selic, IPCA e cambio.
- `financial.formula_audit`: executa auditoria real das formulas financeiras.

## Intervalos

Configurados por variaveis:

- `JOBS_HEARTBEAT_INTERVAL_SECONDS`
- `JOBS_CLEANUP_INTERVAL_SECONDS`
- `JOBS_GUARDIAN_INTERVAL_SECONDS`
- `JOBS_MARKET_DATA_INTERVAL_SECONDS`
- `JOBS_MODEL_PORTFOLIOS_INTERVAL_SECONDS`
- `JOBS_MACRO_FX_INTERVAL_SECONDS`
- `JOBS_FORMULA_AUDIT_INTERVAL_SECONDS`

## Auditoria

Cada job cria registro em `job_runs`.

Os jobs tambem escrevem eventos em `audit_events` quando executam operacoes relevantes, como sincronizacao de mercado, revisao de carteira recomendada, refresh macro/cambio e auditoria de formulas.

## Operacao manual

Endpoints autenticados:

- `GET /api/ops/jobs`
- `POST /api/ops/jobs/{job_name}/run`

Esses endpoints existem para inspecao e acionamento manual de rotinas em ambiente controlado.

