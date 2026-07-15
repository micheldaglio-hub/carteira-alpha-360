# Payment Gateway

Status: fundacao tecnica implementada em 2026-07-14.

## Objetivo

Criar a camada de pagamento do Carteira Alpha 360 sem acoplar o frontend ao provedor financeiro.

O frontend nunca chama Stripe, Mercado Pago ou qualquer outro gateway diretamente. Ele solicita um checkout ao backend. O backend cria a sessao, registra auditoria, recebe webhooks e ativa a assinatura somente depois de um evento de pagamento aprovado.

## Principios

- Nenhuma chave de pagamento fica no frontend.
- Toda ativacao premium nasce de checkout ou concessao administrativa.
- Webhook e idempotente por `provider + event_id`.
- Pagamento e assinatura sao conceitos separados.
- O Entitlements Engine continua sendo a fonte de verdade para permissao premium.
- RBAC continua sendo a fonte de verdade para permissao operacional.

## Arquivos

- `backend/app/billing/gateway.py`
- `backend/app/billing/__init__.py`
- `backend/app/routers/billing.py`
- `backend/alembic/versions/20260714_0018_billing_payment_gateway.py`
- `backend/tests/test_billing_gateway.py`
- `frontend/src/pages/PremiumSubscriber.jsx`

## Tabelas

### `billing_checkout_sessions`

Registra uma tentativa de compra.

Campos principais:

- `user_id`
- `plan_id`
- `plan_code`
- `billing_cycle`
- `provider`
- `provider_checkout_id`
- `external_reference`
- `idempotency_key`
- `status`
- `amount`
- `currency`
- `checkout_url`
- `expires_at`
- `completed_at`

### `billing_transactions`

Registra pagamentos confirmados, pendentes, cancelados ou falhos.

Campos principais:

- `user_id`
- `checkout_session_id`
- `subscription_id`
- `provider`
- `provider_payment_id`
- `status`
- `amount`
- `currency`
- `paid_at`
- `raw_payload_json`

### `billing_webhook_events`

Registra os eventos recebidos dos gateways.

Campos principais:

- `provider`
- `event_id`
- `event_type`
- `status`
- `signature_valid`
- `checkout_session_id`
- `transaction_id`
- `raw_payload_json`
- `processing_error`
- `received_at`
- `processed_at`

## Fluxo

1. Usuario acessa `Area Premium`.
2. Frontend chama `POST /api/billing/checkout/sessions`.
3. Backend cria `billing_checkout_sessions`.
4. Provider retorna URL de checkout.
5. Em ambiente `mock`, o frontend confirma com `POST /api/billing/mock/checkout/{session_id}/success`.
6. Em ambiente real, o gateway chama `POST /api/billing/webhooks/{provider}`.
7. Backend valida assinatura do webhook.
8. Backend registra `billing_webhook_events`.
9. Backend registra ou atualiza `billing_transactions`.
10. Se o pagamento foi aprovado, backend ativa assinatura via `grant_subscription_to_user`.
11. Entitlements e papel `premium_subscriber` sao sincronizados.

## Rotas

```text
POST /api/billing/checkout/sessions
POST /api/billing/mock/checkout/{session_id}/success
POST /api/billing/webhooks/{provider}
GET  /api/billing/me
GET  /api/billing/checkout/sessions/{session_id}
GET  /api/billing/admin/webhook-events
```

`GET /api/billing/admin/webhook-events` exige papel `admin`.

## Providers

Provider ativo por padrao:

- `mock`

Providers preparados conceitualmente:

- `stripe`
- `mercadopago`

A primeira versao nao faz chamada externa real. Ela cria o contrato, a persistencia, a seguranca, o fluxo de ativacao e a UI. A conexao real deve ser feita adicionando adaptadores no backend, mantendo o mesmo contrato.

## Variaveis

```text
BILLING_PAYMENT_PROVIDER=mock
BILLING_CHECKOUT_EXPIRES_MINUTES=60
BILLING_WEBHOOK_SECRET=
BILLING_PUBLIC_BASE_URL=http://127.0.0.1:5173
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
MERCADOPAGO_ACCESS_TOKEN=
MERCADOPAGO_WEBHOOK_SECRET=
```

## Seguranca

- Webhook com assinatura invalida nao ativa assinatura.
- Em `mock`, a assinatura e opcional; se `BILLING_WEBHOOK_SECRET` estiver vazio, o ambiente local aceita o evento de teste.
- Checkout pertence ao usuario autenticado.
- Pagamento aprovado nao libera acesso direto: ele chama o Entitlements Engine.
- Downloads premium continuam protegidos por entitlement ativo.

## Rollback

Migration:

```text
20260714_0018_billing_payment_gateway
```

Rollback remove apenas as tabelas de billing:

- `billing_webhook_events`
- `billing_transactions`
- `billing_checkout_sessions`

Nao remove usuarios, assinaturas, planos, entitlements ou RBAC.

## Testes

Cobertura:

- Criacao de checkout mock.
- Confirmacao de pagamento.
- Ativacao de assinatura premium.
- Criacao de entitlements.
- Historico de billing.
- Idempotencia de webhook.

Arquivo:

- `backend/tests/test_billing_gateway.py`
