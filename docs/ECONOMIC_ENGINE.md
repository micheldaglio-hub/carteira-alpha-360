# Economic Engine

Status: leitura real implementada em 2026-07-13.

## Objetivo

O Economic Engine interpreta o impacto macroeconomico da carteira.

Ele nao busca dados crus na interface. A leitura economica consome o `Macro / FX Engine`, que normaliza, cacheia e trata fallback de dados do Banco Central.

## Leituras atuais

- Sensibilidade a juros.
- Sensibilidade a inflacao.
- Exposicao cambial.

## Fonte real atual

- Banco Central SGS.

Series usadas:

- `432`: Selic meta.
- `433`: IPCA mensal e IPCA acumulado em 12 meses.
- `10813`: USD/BRL.
- `21619`: EUR/BRL.

## Arquivos

- `backend/app/wealth_os/economic_engine.py`
- `backend/app/wealth_os/macro_fx_engine.py`
- `backend/app/wealth_os/contracts.py`
- `backend/app/routers/wealth_os.py`

## Endpoints

- `GET /api/wealth-os/economic`
- `GET /api/wealth-os/macro-fx`
- `GET /api/wealth-os/fx`

## Cache e fallback

O engine grava dados em `market_data_cache` com provider `bcb_sgs`.

TTLs:

- Macro: 6 horas.
- Cambio: 15 minutos.

Se a API do Banco Central falhar, o engine tenta usar cache antigo e registra evento em `market_data_provider_events`. A tela nunca deve chamar provider externo diretamente.

## Regra de produto

A leitura macro explica contexto e risco. Ela nao promete resultado e nao emite ordem automatica de compra ou venda.
