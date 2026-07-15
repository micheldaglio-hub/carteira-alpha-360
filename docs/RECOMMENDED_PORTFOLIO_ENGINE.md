# Recommended Portfolio Engine

Status: implementado em 2026-07-13.

## Objetivo

O Recommended Portfolio Engine transforma a Carteira Recomendada Alpha em um relatorio institucional mensal.

Ele consolida:

- Screener Alpha B3.
- Screener Alpha FIIs.
- Screener Alpha Global.
- Crypto Research Engine.
- Alpha Confidence Engine.
- Global Backtest Engine.
- Strategy Engine 2.0, quando houver usuario autenticado.

## Arquivos

- `backend/app/services/recommended_portfolio_engine.py`
- `backend/app/services/model_portfolios.py`
- `backend/app/routers/model_portfolios.py`
- `frontend/src/pages/ModelPortfolios.jsx`
- `backend/tests/test_model_portfolios.py`

## Endpoints

- `GET /api/model-portfolios`
- `GET /api/model-portfolios/recommended-report`
- `POST /api/model-portfolios/recommended-report/run`

O payload principal recebeu o campo aditivo `recommendedPortfolioReport`.

## Contrato do relatorio

Campos principais:

- `institutionalScore`
- `classification`
- `riskLevel`
- `confidenceScore`
- `scoreBreakdown`
- `executiveSummary`
- `portfolios`
- `assetReports`
- `evidenceLedger`
- `riskMatrix`
- `monthlyReview`
- `governanceRules`
- `allowedLanguage`
- `blockedLanguage`
- `nextReviewDate`

## Asset report

Cada ativo recebe:

- ticker
- nome
- classe
- setor
- peso alvo
- papel na carteira
- tese
- risco
- Alpha Score
- Confidence Score
- Institutional Score
- evidencias
- riscos
- pontos de monitoramento
- qualidade dos dados
- acao de revisao

## Formula do Institutional Score por ativo

Para ativos de carteira:

```text
Institutional Score =
  Alpha Score       * 42%
+ Confidence Score  * 22%
+ Data Score        * 14%
+ Risk Score        * 12%
+ Evidence Score    * 10%
```

Para cripto:

```text
Institutional Score =
  Research Score    * 38%
+ Confidence Score  * 18%
+ Data Score        * 16%
+ Access Score      * 16%
+ Risk Score        * 12%
```

Cripto sempre recebe risco extremo e fica fora do nucleo patrimonial.

## Formula do Institutional Score da carteira

```text
Portfolio Institutional Score =
  Core Portfolio     * 34%
+ Confidence         * 22%
+ Methodology        * 16%
+ Diversification    * 12%
+ Evidence           * 10%
+ Monthly Governance * 6%
```

## Revisao mensal

A revisao mensal deve verificar:

- Precos.
- Fundamentos.
- Dividendos, JCP e rendimentos.
- Eventos corporativos.
- Resultados trimestrais.
- FIIs: vacancia, P/VP, rendimento, liquidez e gestao.
- Global: cambio, dividendos internacionais, stock x BDR x ETF.
- Cripto: Binance, CoinMarketCap, CoinGecko, tokenomics, liquidez e narrativa.
- Risco de concentracao.
- Mudanca de tese.

## Linguagem permitida

- Ativo compativel com a tese.
- Ativo em revisao.
- Ativo com risco elevado.
- Peso-alvo de estudo.
- Ponto de acompanhamento mensal.

## Linguagem bloqueada

- Compre agora.
- Venda agora.
- Sem risco.
- Retorno garantido.
- Pode comprar sem medo.

## Criterios de aceite

- Nenhum payload antigo foi removido.
- A tela Carteira Recomendada exibe o relatorio institucional.
- O endpoint proprio retorna somente o relatorio.
- O motor funciona sem depender de React.
- O relatorio possui tese, risco, score, evidencias e revisao mensal.
- Testes validam presenca de asset reports, risk matrix, evidence ledger e monthly review.
