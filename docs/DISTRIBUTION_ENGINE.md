# Distribution Engine

Status: fundacao tecnica implementada em 2026-07-14. Camada de providers e templates implementada na mesma data.

## Objetivo

Controlar a distribuicao de edicoes premium do Carteira Alpha 360 para assinantes, sem misturar publicacao, pagamento e envio.

O Distribution Engine entra depois que:

1. a edicao premium foi aprovada;
2. o snapshot foi congelado;
3. o HTML/PDF foi renderizado;
4. o assinante possui entitlement ativo.

## Principios

- Nao cria tese.
- Nao altera rating.
- Nao aprova publicacao.
- Nao cobra pagamento.
- Nao entrega conteudo para usuario sem permissao.
- Todo envio gera campanha, destinatarios e eventos auditaveis.
- O provider `mock` permite testar localmente sem disparar email real.

## Arquivos

- `backend/app/distribution/engine.py`
- `backend/app/distribution/inbox.py`
- `backend/app/distribution/providers.py`
- `backend/app/distribution/templates.py`
- `backend/app/distribution/__init__.py`
- `backend/app/routers/distribution.py`
- `backend/alembic/versions/20260714_0019_distribution_engine.py`
- `backend/tests/test_distribution_engine.py`
- `frontend/src/pages/PremiumResearch.jsx`

## Tabelas

### `distribution_campaigns`

Registra a campanha de envio.

Campos principais:

- `publication_id`
- `artifact_id`
- `created_by_user_id`
- `channel`
- `audience_type`
- `provider`
- `status`
- `subject`
- `recipient_count`
- `delivered_count`
- `failed_count`
- `open_count`
- `click_count`

### `distribution_recipients`

Registra cada destinatario da campanha.

Campos principais:

- `campaign_id`
- `user_id`
- `email`
- `full_name`
- `status`
- `provider_message_id`
- `entitlement_status`
- `sent_at`
- `delivered_at`
- `opened_at`
- `clicked_at`

### `distribution_event_logs`

Registra eventos do provider.

Campos principais:

- `campaign_id`
- `recipient_id`
- `provider`
- `provider_event_id`
- `provider_message_id`
- `event_type`
- `status`
- `payload_json`

## Fluxo

1. Editor acessa `Research Premium`.
2. Edicao precisa estar aprovada.
3. PDF precisa existir.
4. Editor cria campanha para `premium_subscribers`.
5. Engine seleciona usuarios com entitlement premium ativo.
6. Campanha fica `ready`.
7. Editor dispara campanha.
8. Provider `mock` marca destinatarios como `delivered`.
9. Eventos sao registrados em `distribution_event_logs`.

## APIs

```text
POST /api/distribution/campaigns
POST /api/distribution/campaigns/{campaign_id}/dispatch
GET  /api/distribution/campaigns
GET  /api/distribution/campaigns/{campaign_id}
POST /api/distribution/webhooks/{provider}
GET  /api/premium/subscriber/delivery-inbox
```

Rotas administrativas exigem papel editorial (`admin` ou `editor`).

## Providers

Providers implementados:

- `mock`
- `resend`
- `smtp`

Regra de seguranca:

- Se `DISTRIBUTION_PROVIDER=resend` e `DISTRIBUTION_RESEND_API_KEY` estiver ausente, a engine usa `mock` automaticamente e grava `fallbackReason` na campanha.
- Se `DISTRIBUTION_PROVIDER=smtp` e `DISTRIBUTION_SMTP_HOST` estiver ausente, a engine usa `mock` automaticamente e grava `fallbackReason` na campanha.
- Provider desconhecido tambem cai para `mock`.
- O provider efetivo fica salvo em `distribution_campaigns.provider`; o provider configurado fica em `metadata.configuredProvider`.

Providers futuros opcionais:

- SendGrid
- Amazon SES
- Mailgun
- Brevo
- Postmark

## Variaveis

```text
DISTRIBUTION_PROVIDER=mock
DISTRIBUTION_FROM_EMAIL=research@carteiraalpha.local
DISTRIBUTION_REPLY_TO=
DISTRIBUTION_WEBHOOK_SECRET=
DISTRIBUTION_PUBLIC_BASE_URL=http://127.0.0.1:5173
DISTRIBUTION_RESEND_API_KEY=
DISTRIBUTION_RESEND_BASE_URL=https://api.resend.com
DISTRIBUTION_SMTP_HOST=
DISTRIBUTION_SMTP_PORT=587
DISTRIBUTION_SMTP_USERNAME=
DISTRIBUTION_SMTP_PASSWORD=
DISTRIBUTION_SMTP_USE_TLS=true
```

## Templates

O template padrao e gerado em `backend/app/distribution/templates.py`.

Ele produz:

- assunto;
- HTML premium responsivo;
- texto simples;
- preview text;
- disclaimer;
- controle de integridade do artefato.

O template usa o `payload_json` congelado da campanha. Assim, o conteudo enviado fica vinculado a uma publicacao, artefato e hash especificos.

## Inbox do assinante

O `Subscriber Delivery Inbox` consolida o estado das entregas para a Area Premium.

Ele cruza:

- destinatarios de campanha;
- campanha e publicacao;
- artefato PDF;
- logs de download premium.

Status possiveis:

- `pending`
- `sent`
- `received`
- `opened`
- `clicked`
- `downloaded`
- `failed`
- `skipped`

O inbox nao concede acesso. Ele apenas informa o que aconteceu. Download continua protegido por entitlement.

## Seguranca

- Webhook com assinatura invalida e rejeitado quando `DISTRIBUTION_WEBHOOK_SECRET` estiver configurado.
- Campanhas so podem ser criadas por papel editorial.
- Audiencia premium e calculada por `premium_entitlements` ativos.
- A campanha armazena `artifactHash`, status da publicacao e versao do engine.

## Rollback

Migration:

```text
20260714_0019_distribution_engine
```

Rollback remove apenas:

- `distribution_event_logs`
- `distribution_recipients`
- `distribution_campaigns`

Nao remove publicacoes, PDFs, assinaturas, entitlements, billing ou RBAC.

## Testes

Cobertura:

- Criacao de campanha para assinante premium ativo.
- Disparo mock.
- Renderizacao do conteudo de email no evento mock.
- Fallback automatico de `resend` sem chave para `mock`.
- Inbox do assinante com entrega recebida e mudanca para `downloaded` apos baixar PDF.
- Registro de destinatario.
- Registro de evento.
- API de criacao, disparo, listagem e detalhe.

Arquivo:

- `backend/tests/test_distribution_engine.py`
