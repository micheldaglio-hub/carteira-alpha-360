# Premium Entitlements Engine

Status: fundacao tecnica implementada em 2026-07-14.

## Objetivo

Controlar planos, assinaturas, permissoes de acesso e logs de download da vertical Alpha Premium Research.

O motor prepara o Carteira Alpha 360 para area de assinantes, planos pagos, downloads controlados, auditoria de consumo e bloqueio de acesso sem entitlement ativo.

## Arquivos

- `backend/app/premium_research/entitlements.py`
- `backend/app/models.py`
- `backend/app/routers/premium.py`
- `backend/alembic/versions/20260714_0016_premium_entitlements.py`
- `backend/tests/test_premium_entitlements.py`

## Tabelas

Criadas:

- `subscription_plans`
- `user_subscriptions`
- `premium_entitlements`
- `premium_access_logs`

## Planos padrao

O seed tecnico cria:

- `alpha_free`
- `alpha_premium`
- `alpha_institutional`

Entitlements iniciais:

- `premium.research.preview`
- `premium.research.read`
- `premium.pdf.download`
- `premium.publications.archive`
- `premium.pdf.bulk_download`
- `premium.research.admin`

## Fluxo

```text
Plano
-> Assinatura do usuario
-> Entitlements ativos
-> Tentativa de acesso/download
-> Validacao de permissao
-> Log em premium_access_logs
```

## Regra de download

Um PDF premium pode ser baixado quando:

1. O usuario e dono editorial da publicacao; ou
2. O usuario possui entitlement ativo compatvel com `download_pdf`.

Entitlements aceitos para download:

- `premium.pdf.download`
- `premium.pdf.bulk_download`
- `premium.research.admin`

## API

Planos:

```http
POST /api/premium/plans/seed
GET /api/premium/plans
```

Assinatura do usuario atual:

```http
POST /api/premium/subscriptions/grant
GET /api/premium/subscriptions/me
```

Logs:

```http
GET /api/premium/access-logs
```

Download protegido:

```http
GET /api/premium/artifacts/{artifact_id}/download
```

## Auditoria

Cada tentativa de acesso gera `premium_access_logs`, incluindo:

- usuario;
- artefato;
- publicacao;
- snapshot;
- action;
- allowed;
- reason;
- entitlement usado;
- hash do artefato;
- data/hora.

## O que ainda nao faz

- Nao integra gateway de pagamento real.
- RBAC administrativo basico foi implementado em `docs/PREMIUM_RBAC_SUBSCRIBER_AREA.md`.
- Nao possui area visual de assinante.
- Nao envia e-mail.
- Nao emite nota fiscal.
- Nao faz renovacao automatica.

## Criterios de aceite

- Planos padrao sao idempotentes.
- Conceder plano cria assinatura e entitlements.
- Usuario sem entitlement nao baixa PDF premium de terceiros.
- Usuario com entitlement ativo baixa PDF premium.
- Dono editorial baixa o proprio PDF.
- Toda tentativa de download gera log.
- Testes unitarios e de API passam.
