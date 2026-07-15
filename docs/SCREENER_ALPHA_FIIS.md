# Screener Alpha FIIs

Status: fundacao implementada em 2026-07-12.

## Objetivo

Criar um motor separado para avaliar FIIs sem misturar a metodologia com acoes.

FIIs devem ser tratados como ativos de renda imobiliaria, com foco em:

- Recorrencia de rendimentos.
- Qualidade dos imoveis ou CRIs.
- Vacancia.
- Liquidez.
- Qualidade da gestao.
- Diversificacao de inquilinos, setores e regioes.
- P/VP e disciplina de valuation.
- Risco de credito, quando for fundo de recebiveis.
- Risco de emissao, alavancagem e diluicao.

## Arquivos

- Motor: `backend/app/services/alpha_fii_screener.py`
- Rota: `GET /api/model-portfolios/fii-screener`
- Rota: `POST /api/model-portfolios/fii-screener/run`
- Agregacao em Carteira Recomendada: `backend/app/services/model_portfolios.py`
- Interface: `frontend/src/pages/ModelPortfolios.jsx`
- Testes: `backend/tests/test_model_portfolios.py`

## Portfolio inicial do motor

O motor inicial trabalha com uma carteira de estudo de FIIs:

- HGLG11
- KNRI11
- BTLG11
- XPML11
- VISC11
- KNCR11
- MXRF11
- CPTS11

Pesos somam 100%.

## Diferenca entre acao e FII

Acoes:

- ROE.
- ROIC.
- Margem.
- Lucro.
- Payout.
- Crescimento de receita.
- Divida liquida/EBITDA.

FIIs:

- Rendimentos recorrentes.
- Vacancia.
- Qualidade do portfolio.
- Segmento imobiliario.
- P/VP.
- Liquidez das cotas.
- Gestao.
- Risco dos contratos ou CRIs.

Por isso FIIs nao devem entrar diretamente no `Screener Alpha B3` de acoes.

## Score Alpha FIIs

Pontuacao inicial:

```text
score =
  recorrencia_de_renda * 0.24 +
  liquidez * 0.16 +
  qualidade_do_portfolio * 0.22 +
  gestao * 0.16 +
  disciplina_de_valuation * 0.12 +
  risco_invertido * 0.10
```

## Dados reais futuros

O motor esta preparado para receber dados de:

- B3.
- CVM.
- Fintz.
- Dados de Mercado.
- BRAPI, se entregar fundos.
- Outras fontes que tragam P/VP, DY, vacancia e historico.

## Regra de linguagem

O sistema pode dizer:

- FII compoe estudo de renda imobiliaria.
- FII exige acompanhamento de vacancia, P/VP e qualidade de renda.
- FII tem perfil de renda mensal.

O sistema nao deve prometer:

- Rendimento garantido.
- Isencao fiscal permanente.
- Valorizacao da cota.

## Proximas evolucoes

- Integrar dados reais de FIIs por provider.
- Criar historico de rendimentos por FII.
- Incluir FIIs no calendario de proventos.
- Criar comparacao FII x Tesouro IPCA x renda fixa.
- Criar painel de vacancia, P/VP, segmentos e qualidade da gestao.
