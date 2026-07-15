# Event Engine 2.0

Status: fundacao implementada em 2026-07-13.

## Objetivo

O Event Engine 2.0 transforma eventos, insights, alertas manuais e Guardian em uma fila unica de acompanhamento.

## Fontes

- Alertas manuais da tabela `alerts`.
- Eventos do Alpha Intelligence Engine.
- Insights do Alpha Insight Engine.
- Itens do Guardian 2.0.

## Contrato

Cada evento possui:

- `id`
- `eventType`
- `category`
- `severity`
- `priority`
- `asset`
- `title`
- `message`
- `impact`
- `recommendedAction`
- `status`
- `source`
- `triggeredAt`
- `lifecycleStage`
- `confidence`
- `readOnly`
- `dataUsed`

## Endpoints

- `GET /api/wealth-os/events`
- `GET /api/alerts`

`GET /api/alerts` continua existindo para compatibilidade, mas agora consome o Event Engine 2.0.

## Regra

Eventos explicam situacoes relevantes. Eles nao executam ordem de compra ou venda.

