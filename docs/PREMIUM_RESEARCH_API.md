# Premium Research Admin API

Status: fundacao tecnica, tela administrativa inicial, Performance Attribution administrativo, Publication Snapshot Engine, Publication Render Engine, Publication PDF Publisher, Premium Entitlements Engine, RBAC e Area Premium do Assinante implementados em 2026-07-14.

## Objetivo

Expor endpoints protegidos para operar a vertical Alpha Premium Research e alimentar a tela administrativa inicial `Research Premium`.

Esses endpoints permitem:

- criar rascunho premium versionado;
- listar publicacoes premium do usuario;
- inspecionar versoes e payload interno;
- sincronizar teses;
- sincronizar ratings;
- executar Research Committee;
- executar Performance Attribution da publicacao;
- consultar rodadas de attribution;
- gerar snapshot imutavel de uma edicao aprovada;
- listar e verificar snapshots;
- gerar HTML premium reproduzivel a partir de snapshot aprovado;
- listar e consultar artefatos renderizados;
- gerar e baixar PDF binario a partir de HTML aprovado;
- controlar planos premium, assinaturas, entitlements e logs de acesso;
- consultar rodadas de comite;
- consultar teses e ratings versionados;
- registrar revisao humana;
- registrar aprovacao ou rejeicao final.

## Protecao

Todas as rotas usam `get_current_user`.

Na fase atual, a area editorial usa RBAC:

- `admin`: controla toda a vertical premium;
- `editor`: cria e prepara publicacoes;
- `reviewer`: registra revisao humana;
- `premium_subscriber`: acessa a area premium conforme assinatura ativa;
- `free_user`: acesso basico.

Rotas administrativas exigem papel operacional. A area de assinante consome endpoints separados e nao recebe payload interno editorial.

## Rotas

Base:

```text
/api/premium
```

### Criar rascunho

```http
POST /api/premium/publications/drafts
```

Body:

```json
{
  "period": "2026-07",
  "publication_type": "monthly_research",
  "title": "Alpha Premium Research - 2026-07",
  "refresh_market": false
}
```

Executa:

```text
AlphaResearchPublisher
-> Thesis Engine
-> Rating Engine
-> Evidence Ledger
-> Readiness Report
-> Research Committee
```

### Listar publicacoes

```http
GET /api/premium/publications
GET /api/premium/publications?status=draft&period=2026-07
```

### Detalhar publicacao

```http
GET /api/premium/publications/{publication_id}
```

Retorna resumo, versoes e rodadas de comite.

### Detalhar versao

```http
GET /api/premium/publications/{publication_id}/versions/{version_id}
```

Retorna resumo da versao, secoes e `payload_json` parseado.

### Sincronizar teses

```http
POST /api/premium/publications/{publication_id}/theses/sync
```

Body:

```json
{
  "publication_version_id": "opcional",
  "force_new_version": false,
  "refresh_market": false,
  "run_committee": true
}
```

Observacao: `run_committee` existe no contrato compartilhado, mas nesta rota apenas teses sao sincronizadas.

### Sincronizar ratings

```http
POST /api/premium/publications/{publication_id}/ratings/sync
```

Body:

```json
{
  "publication_version_id": "opcional",
  "force_new_version": false,
  "run_committee": true
}
```

Quando `run_committee` for `true`, o Research Committee roda novamente apos os ratings.

### Rodar comite

```http
POST /api/premium/publications/{publication_id}/committee/run
```

Body:

```json
{
  "publication_version_id": "opcional"
}
```

### Rodar Performance Attribution

```http
POST /api/premium/publications/{publication_id}/attribution/run
```

Body:

```json
{
  "publication_version_id": "opcional",
  "start_date": "2026-07-01",
  "end_date": "2026-07-31",
  "benchmark_name": "IBOV",
  "benchmark_return_pct": 1.25,
  "refresh_market": false
}
```

Executa o `Performance Attribution Engine` para a versao premium informada.

Retorna:

- retorno estimado da carteira-modelo;
- retorno de preco;
- retorno de renda/proventos estimado;
- benchmark e excesso quando benchmark for informado;
- principais contribuidores;
- principais detratores;
- qualidade dos dados;
- linhas por ativo;
- evidencias gravadas no Data Evidence Ledger.

Por padrao `refresh_market=false`. Assim a rota nao depende de provider externo para funcionar. Quando `refresh_market=true`, o backend tenta buscar historico pelo Market Data Engine v2 e registra fallback quando nao houver dado suficiente.

### Registrar revisao humana

```http
POST /api/premium/publications/{publication_id}/reviews
```

Body:

```json
{
  "publication_version_id": "opcional",
  "decision": "approve",
  "comments": "Revisao humana concluida.",
  "requested_changes": []
}
```

Decisoes aceitas:

- `approve`: marca a publicacao como `reviewed` e aprova as secoes da versao que nao estejam bloqueadas;
- `request_changes`: devolve a publicacao para `draft`;
- `block`: marca a publicacao como `data_pending`.

### Registrar aprovacao final

```http
POST /api/premium/publications/{publication_id}/approvals
```

Body:

```json
{
  "publication_version_id": "opcional",
  "decision": "approve_publication",
  "comments": "Aprovacao editorial final."
}
```

Decisoes aceitas:

- `approve_publication`: marca publicacao e versao como `approved`;
- `reject_publication`: devolve publicacao e versao para `draft`.

### Gerar snapshot imutavel

```http
POST /api/premium/publications/{publication_id}/snapshots
```

Body:

```json
{
  "publication_version_id": "opcional",
  "snapshot_type": "approved_edition",
  "require_approval": true,
  "include_payload": false
}
```

O snapshot final exige publicacao e versao aprovadas, revisao humana `approve` e aprovacao final `approve_publication`.

### Listar snapshots

```http
GET /api/premium/publications/{publication_id}/snapshots
GET /api/premium/snapshots
GET /api/premium/snapshots/{snapshot_id}
```

### Renderizar snapshot em HTML premium

```http
POST /api/premium/snapshots/{snapshot_id}/render
```

Body:

```json
{
  "artifact_type": "html",
  "force": false,
  "include_content": true
}
```

Executa o `Publication Render Engine`.

Regras:

- usa apenas o payload congelado do snapshot;
- exige integridade `ok`;
- gera `artifactHash`;
- grava evidencia `premium_research_artifact.artifact_hash`;
- e idempotente por `snapshot_id + artifact_type + render_version`.

### Listar artefatos renderizados

```http
GET /api/premium/publications/{publication_id}/artifacts
GET /api/premium/snapshots/{snapshot_id}/artifacts
GET /api/premium/artifacts
GET /api/premium/artifacts/{artifact_id}
```

Parametro opcional:

```text
include_content=true
```

Quando `include_content=true`, a resposta inclui `htmlContent` e `plainText`.

### Gerar PDF premium

```http
POST /api/premium/artifacts/{artifact_id}/pdf
```

O `{artifact_id}` precisa ser um artefato HTML gerado pelo Publication Render Engine.

Body:

```json
{
  "force": false
}
```

Retorna o artefato PDF com:

- `artifactType=pdf`;
- `contentType=application/pdf`;
- `sourceArtifactId`;
- `sourceSnapshotHash`;
- `artifactHash`;
- `contentSizeBytes`;
- `pageCount`;
- `downloadUrl`.

### Baixar PDF premium

```http
GET /api/premium/artifacts/{artifact_id}/download
```

Resposta:

```text
Content-Type: application/pdf
X-Artifact-Hash: <hash do PDF>
```

Regras de acesso:

- dono editorial da publicacao pode baixar para revisao e operacao interna;
- assinante precisa possuir entitlement ativo para `premium.pdf.download`, `premium.pdf.bulk_download` ou `premium.research.admin`;
- PDF de publicacao que nao esteja `approved` ou `published` nao e entregue para assinante comum;
- toda tentativa de download, autorizada ou negada, grava `premium_access_logs`.

### Sincronizar planos premium padrao

```http
POST /api/premium/plans/seed
```

Cria ou atualiza os planos internos iniciais:

- `alpha_free`;
- `alpha_premium`;
- `alpha_institutional`.

### Listar planos premium

```http
GET /api/premium/plans
```

Retorna planos, precos, recursos e limites operacionais.

### Conceder assinatura manual

```http
POST /api/premium/subscriptions/grant
```

Body:

```json
{
  "plan_code": "alpha_premium",
  "period_days": 30
}
```

Cria uma assinatura manual para o usuario autenticado e sincroniza os entitlements do plano. Esta rota e fundacao tecnica: ainda nao representa cobranca real por gateway.

### Consultar meus acessos premium

```http
GET /api/premium/subscriptions/me
```

Retorna assinaturas, entitlements totais e entitlements ativos.

### Consultar logs de acesso premium

```http
GET /api/premium/access-logs
GET /api/premium/access-logs?limit=100
```

Retorna tentativas de acesso/download registradas para o usuario autenticado.

### Consultar meu RBAC

```http
GET /api/premium/rbac/me
```

Retorna papeis, permissoes e classificacoes do usuario autenticado.

### Conceder papel RBAC

```http
POST /api/premium/rbac/roles/grant
```

Body:

```json
{
  "user_id": "id-do-usuario",
  "role": "editor",
  "scope_type": "global",
  "scope_id": "*"
}
```

Exige papel `admin`.

### Area Premium do Assinante

```http
GET /api/premium/subscriber/home
```

Retorna plano ativo, RBAC, entitlements, edicoes aprovadas, PDFs disponiveis e logs recentes. Esta rota e propria para UI de assinante.

Regras:

- `approve_publication` exige revisao humana aprovada para a mesma versao.
- `approve_publication` exige rodada do Research Committee.
- `approve_publication` fica bloqueado se o Research Committee tiver decisao `blocked` ou bloqueios ativos.

### Listar rodadas do comite

```http
GET /api/premium/committee/runs
GET /api/premium/committee/runs?decision=blocked
```

### Detalhar rodada do comite

```http
GET /api/premium/committee/runs/{run_id}
```

### Listar rodadas de attribution

```http
GET /api/premium/attribution/runs
GET /api/premium/attribution/runs?period=2026-07
GET /api/premium/attribution/runs?publication_id={publication_id}
```

### Detalhar rodada de attribution

```http
GET /api/premium/attribution/runs/{run_id}
```

### Listar teses

```http
GET /api/premium/theses
GET /api/premium/theses?ticker=BBSE3
```

### Listar ratings

```http
GET /api/premium/ratings
GET /api/premium/ratings?ticker=BBSE3
```

## Auditoria

Rotas `POST` registram eventos de auditoria:

- `premium_research_draft_created`
- `premium_research_theses_synced`
- `premium_research_ratings_synced`
- `premium_research_committee_run`
- `premium_research_attribution_run`
- `premium_research_snapshot_created`
- `premium_research_artifact_rendered`
- `premium_research_pdf_rendered`
- `premium_subscription_plans_seeded`
- `premium_subscription_granted`
- `premium_rbac_role_granted`
- `premium_research_review_recorded`
- `premium_research_approval_recorded`

O middleware HTTP tambem registra mutacoes quando `audit_http_mutations` estiver habilitado.

## Compatibilidade

- Tela nova `Research Premium` foi adicionada sem alterar comportamento das telas existentes.
- Nenhuma rota existente foi alterada.
- Nenhum payload antigo foi removido.
- Migration Alembic aditiva `20260714_0012_performance_attribution` criada para `research_attribution_runs` e `research_attribution_assets`.
- Migration Alembic aditiva `20260714_0013_publication_snapshots` criada para `publication_snapshots`.
- Migration Alembic aditiva `20260714_0014_publication_artifacts` criada para `publication_artifacts`.
- Migration Alembic aditiva `20260714_0015_publication_pdf_artifacts` adiciona PDF binario em `publication_artifacts`.
- Migration Alembic aditiva `20260714_0016_premium_entitlements` cria planos, assinaturas, entitlements e logs de acesso premium.
- Migration Alembic aditiva `20260714_0017_user_roles_rbac` cria `user_roles` e preserva usuarios existentes como `admin`.
- O fluxo continua sem publicacao automatica.

## Testes

- `backend/tests/test_premium_research_api.py`

Cobertura:

- rotas exigem autenticacao;
- cria rascunho premium via API;
- inspeciona publicacao, versao, teses, ratings e comite;
- executa nova rodada do Research Committee por endpoint protegido;
- executa Performance Attribution por endpoint protegido;
- lista e detalha rodadas de attribution;
- impede aprovacao final antes de revisao humana aprovada;
- impede snapshot final antes de aprovacao humana;
- protege download premium por entitlement ativo;
- registra logs de acesso permitidos e negados.
- gera snapshot imutavel apos aprovacao final;
- lista snapshots e valida integridade do hash;
- registra revisao humana;
- registra aprovacao/rejeicao final respeitando bloqueios do comite.

## Tela administrativa inicial

Arquivo:

```text
frontend/src/pages/PremiumResearch.jsx
```

Entrada no menu:

```text
Inteligencia -> Research Premium
```

A tela permite:

- criar rascunho premium;
- selecionar edicoes e versoes;
- consultar readiness, secoes, comite, gates e votos;
- sincronizar teses;
- sincronizar ratings;
- rodar Research Committee;
- registrar revisao humana;
- registrar aprovacao ou rejeicao final.
