# Alpha Confidence Engine

Status: implementado em 2026-07-13.

## Objetivo

O `Alpha Confidence Engine` e a camada de confiabilidade da Carteira Recomendada.

Ele responde uma pergunta simples:

> "Esta indicacao esta bem sustentada por dados, metodologia, risco, diversificacao, fontes e historico?"

Ele nao responde:

> "Posso comprar sem medo?"

Essa segunda pergunta nao tem resposta honesta no mercado financeiro. O motor existe para aumentar a confianca analitica e deixar os criterios visiveis, nao para eliminar risco.

## Arquivo

- `backend/app/services/alpha_confidence_engine.py`

## Integracao

Agregador:

- `backend/app/services/model_portfolios.py`

Interface:

- `frontend/src/pages/ModelPortfolios.jsx`

Testes:

- `backend/tests/test_model_portfolios.py`

Payload aditivo:

- `confidenceReport`

Nenhuma rota antiga foi alterada. Nenhum payload antigo foi removido.

## Entradas

O motor recebe:

- `screener`: resultado do Screener Alpha B3.
- `validation`: validacao Alpha da carteira de acoes.
- `fii_screener`: resultado do Screener Alpha FIIs.
- `global_screener`: resultado do Screener Alpha Global.
- `crypto_study`: resultado do Screener Alpha Crypto + Crypto Research Engine.
- `global_backtest`: backtest internacional.
- `imported_backtest`: backtest historico importado de referencia.

## Saida

O motor gera:

- `overallScore`: nota geral de confianca de 0 a 100.
- `classification`: leitura geral.
- `headline`: resumo humano.
- `plainLanguage`: frases curtas para o usuario final.
- `gates`: criterios auditaveis.
- `assetRows`: leitura de confianca por ativo.
- `nonNegotiables`: regras que o Alpha nao negocia.
- `howToRead`: explicacao curta da nota.

## Gates de confianca

### Cobertura de dados

Avalia se o sistema tem dados suficientes de universo, fundamentos, cripto, FIIs e global.

### Metodologia

Avalia se existem filtros objetivos e research antes da exibicao da carteira.

### Fundamentos

Avalia a qualidade media dos ativos do nucleo patrimonial.

### Controle de risco

Penaliza risco politico, risco alto, cripto extrema, baixa liquidez e outros pontos criticos.

### Diversificacao

Avalia quantidade de ativos, concentracao setorial e presenca de FIIs/global.

### Historico e cenarios

Avalia existencia de backtests, historico e avisos de fallback.

### Fontes e rastreabilidade

Avalia se o sistema consegue apontar de onde vieram universo, preco, fundamentos e research.

## Nota por ativo

A nota por ativo combina:

- Score Alpha do ativo.
- Qualidade/cobertura de dados.
- Controle de risco.
- Peso-alvo ou disciplina de alocacao.

Formula base:

```text
score_ativo =
  alpha_score * 0.50
  + data_score * 0.20
  + risk_score * 0.18
  + allocation_score * 0.12
```

Para cripto, a nota e ajustada por risco extremo:

```text
score_cripto =
  research_score * 0.36
  + data_score * 0.22
  + exchange_access_score * 0.22
  + extreme_risk_score * 0.20
```

## Nota geral

Formula:

```text
overall_score =
  core_score * 0.42
  + gate_score * 0.40
  + asset_score * 0.18
```

Onde:

- `core_score`: media dos ativos da carteira principal de acoes Brasil.
- `gate_score`: media dos gates de confianca.
- `asset_score`: media de todos os ativos avaliados.

## Classificacoes

| Faixa | Classificacao |
| --- | --- |
| >= 84 | Alta confianca Alpha |
| >= 74 | Boa confianca Alpha |
| >= 62 | Confianca em construcao |
| < 62 | Exige validacao adicional |

## Regras nao negociaveis

- Nenhum ativo e tratado como compra sem medo.
- Sem dados suficientes, o ativo nao sobe para alta confianca Alpha.
- Cripto fica fora do nucleo patrimonial e sempre recebe leitura de risco extremo.
- Concentracao individual, setorial ou geografica reduz a confianca mesmo quando o ativo e bom.
- Backtest ajuda a entender o passado, mas nunca vira promessa de rentabilidade futura.

## Evolucao futura

- Persistir historico mensal de `confidenceReport`.
- Criar trilha de decisao por ativo.
- Mostrar divergencias entre fontes no Centro Fundamentalista.
- Bloquear aumento de confianca quando dados essenciais estiverem vencidos.
- Usar Knowledge Engine como fonte principal dos fatos tratados.
- Integrar Guardian para reduzir a nota quando houver evento relevante.
