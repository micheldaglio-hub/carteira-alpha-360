# Notification Center / Subscriber Delivery Inbox

Status: implementado em 2026-07-15.

## Objetivo

Permitir que o assinante premium veja, dentro da Area Premium, quais edicoes foram entregues para ele, quais estao pendentes, quais foram recebidas, abertas, clicadas e baixadas.

## Principio arquitetural

O Notification Center nao cria uma nova fonte de verdade.

Ele consolida dados ja auditaveis:

- `distribution_recipients`: destinatario, status de envio, abertura e clique.
- `distribution_campaigns`: campanha, publicacao, artefato e provider.
- `distribution_event_logs`: eventos recebidos do provider.
- `premium_access_logs`: downloads e acessos a PDFs premium.
- `publication_artifacts`: PDF/HTML publicado.
- `research_publications`: edicao premium.

## Arquivos

- `backend/app/distribution/inbox.py`
- `backend/app/routers/premium.py`
- `frontend/src/pages/PremiumSubscriber.jsx`
- `backend/tests/test_distribution_engine.py`

## API

```text
GET /api/premium/subscriber/delivery-inbox
```

Parametros:

- `limit`: limite de entregas retornadas. Padrao `80`, maximo `200`.

Tambem foi incluido no payload:

```text
GET /api/premium/subscriber/home
```

Campo novo:

```json
{
  "deliveryInbox": {
    "items": [],
    "summary": {},
    "count": 0,
    "limit": 80,
    "engineVersion": "2026.07.delivery_inbox1"
  }
}
```

## Status exibidos

- `pending`: entrega ainda pendente.
- `sent`: enviada ao provider.
- `received`: entregue/recebida.
- `opened`: aberta.
- `clicked`: link clicado.
- `downloaded`: PDF baixado pelo assinante.
- `failed`: falha de envio.
- `skipped`: ignorada por regra operacional.

## Regras

- O assinante so ve entregas vinculadas ao proprio `user_id` ou ao proprio e-mail.
- Download continua passando pelo `Premium Entitlements Engine`.
- O inbox nao concede acesso e nao altera permissao.
- Uma entrega so aparece como `downloaded` quando existe `premium_access_logs` permitido para o artefato ou publicacao.
- O botao de download usa a mesma rota protegida: `GET /api/premium/artifacts/{artifact_id}/download`.

## Testes

Cobertura adicionada:

- campanha entregue aparece no inbox do assinante;
- `subscriber/home` inclui `deliveryInbox`;
- apos baixar o PDF, o inbox muda a entrega para `downloaded`.

Arquivo:

- `backend/tests/test_distribution_engine.py`
