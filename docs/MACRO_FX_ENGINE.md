# Macro / FX Engine

Status: implementado em 2026-07-13.

## Objetivo

O `Macro / FX Engine` e a fonte unica do Wealth OS para juros, inflacao e cambio.

Ele existe para impedir que telas, scores ou futuras IAs chamem APIs externas diretamente.

## Responsabilidades

- Buscar indicadores macroeconomicos.
- Buscar cambio.
- Normalizar respostas.
- Salvar cache obrigatorio.
- Entregar fallback com cache quando o provider falhar.
- Gerar leituras de impacto para carteira.
- Registrar falhas de provider sem derrubar o app.

## Implementacao

Arquivo principal:

- `backend/app/wealth_os/macro_fx_engine.py`

Contratos:

- `MacroIndicator`
- `FxRateSnapshot`
- `MacroPortfolioReading`
- `MacroFxSnapshot`

Todos ficam em:

- `backend/app/wealth_os/contracts.py`

## Fontes atuais

Fonte oficial usada agora:

- Banco Central SGS.

Series:

- Selic meta: SGS `432`.
- IPCA mensal: SGS `433`.
- IPCA acumulado 12m: calculado por composicao dos ultimos 12 valores da SGS `433`.
- USD/BRL: SGS `10813`.
- EUR/BRL: SGS `21619`.

## Cache

Tabela:

- `market_data_cache`

Chaves:

- `wealth-os:macro-fx:v1:macro:{indicador}`
- `wealth-os:macro-fx:v1:fx:{base}:{quote}`

TTL:

- Macro: 6 horas.
- FX: 15 minutos.

Quando a fonte falha:

1. O engine registra evento em `market_data_provider_events`.
2. Tenta usar cache mesmo expirado.
3. Se nao houver cache, retorna item indisponivel com `qualityScore = 0`.

## Endpoints

- `GET /api/wealth-os/macro-fx`
- `GET /api/wealth-os/macro-fx?refresh=true`
- `GET /api/wealth-os/fx`
- `GET /api/wealth-os/fx?refresh=true`

## Consumidores atuais

- `Economic Engine`.
- `GET /api/wealth-os/economic`.

## Consumidores futuros

- Guardian.
- Alpha Score Mundial.
- Wealth Builder.
- Backtests globais.
- Alpha Copilot.
- Strategy Engine.

## Regra de seguranca

Tokens e chamadas externas ficam somente no backend. O frontend nunca acessa Banco Central, FMP, CoinGecko, CoinMarketCap, Twelve Data ou qualquer provider diretamente.
