# Screener Alpha Global

Status: fundacao implementada em 2026-07-12.

## Objetivo

Criar a base inicial para o Carteira Alpha 360 analisar acoes internacionais dentro da arquitetura de patrimonio global.

O objetivo nao e afirmar que a lista atual representa as melhores empresas do mundo ou que um especialista externo concordaria com cada ativo. A lista atual e uma `watchlist inicial` para diversificacao internacional, preparada para ser enriquecida por providers globais, backtest com cambio e rodadas mensais persistidas.

## Arquivos

- Backend: `backend/app/services/alpha_global_equity_screener.py`
- Rotas: `backend/app/routers/model_portfolios.py`
- Agregacao: `backend/app/services/model_portfolios.py`
- Interface: `frontend/src/pages/ModelPortfolios.jsx`
- Testes: `backend/tests/test_model_portfolios.py`

## Rotas

- `GET /api/model-portfolios/global-screener`
- `POST /api/model-portfolios/global-screener/run`

O `GET` entrega a watchlist estrutural sem forcar chamadas externas.

O `POST` executa tentativa de enriquecimento via Market Data Engine, usando providers globais configurados, especialmente Financial Modeling Prep e Twelve Data. Se providers falharem ou nao estiverem configurados, o sistema deve manter fallback seguro e nao quebrar a tela.

## Universo inicial

A primeira fundacao inclui empresas globais de alta liquidez e vantagem competitiva:

- MSFT
- AAPL
- GOOGL
- NVDA
- V
- JNJ
- PG
- KO
- ASML
- NVO
- NESN.SW
- TSM
- BHP

Essa lista existe para montar a camada tecnica e visual de diversificacao internacional. Ela nao substitui uma varredura completa de todas as bolsas do mundo.

## Criterios iniciais

O score inicial combina:

- Qualidade do negocio.
- Vantagem competitiva.
- Liquidez.
- Governanca.
- Diversificacao geografica.
- Risco qualitativo.
- Fundamentos coletados por provider quando disponiveis.

Quando os providers retornam dados suficientes, o score combina fundamentos e avaliacao estrutural. Quando nao retornam, o motor marca `foundation` ou `partial_provider_data`.

## Providers previstos

- Financial Modeling Prep.
- Twelve Data.
- Yahoo Finance, se viavel como fallback auxiliar.
- FX/Money Engine futuro para cambio USD/BRL, CHF/BRL e outras moedas.

As telas nunca devem chamar provider diretamente. Tudo deve passar pelo Market Data Engine.

## Payload principal

`run_alpha_global_equity_screener` retorna:

- `portfolio`
- `ranking`
- `regionAllocation`
- `currencyAllocation`
- `sectorAllocation`
- `validationNote`
- `nextSteps`
- `dataMode`

Cada ativo contem:

- `ticker`
- `name`
- `country`
- `region`
- `exchange`
- `currency`
- `sector`
- `role`
- `alphaScore`
- `conviction`
- `riskLevel`
- `thesis`
- `watchpoints`

## Regra de comunicacao

Permitido:

- "Watchlist global em validacao."
- "Ativo de alta qualidade global."
- "Compoe diversificacao internacional."
- "Ajuda a reduzir dependencia estrutural do Brasil."

Nao permitido:

- "Melhor acao do mundo."
- "Pode investir sem medo."
- "Garantia de retorno."
- "Vai subir."

## Proximas evolucoes

- Persistir rodadas mensais do screener global.
- Evoluir o backtest internacional ja criado em `docs/GLOBAL_BACKTEST_ENGINE.md` com cambio historico real, impostos e taxas operacionais.
- Comparar stocks, BDRs e ETFs globais por ativo especifico.
- Criar mapa por pais, moeda, bolsa e setor.
- Incluir dividendos internacionais, impostos, withholding tax e conversao cambial.
- Integrar com Knowledge Engine para historico de fundamentos e eventos corporativos.
