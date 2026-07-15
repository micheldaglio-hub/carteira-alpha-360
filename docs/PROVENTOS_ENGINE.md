# Proventos Engine

Status: fundacao implementada em 2026-07-12.

## Objetivo

Padronizar a renda distribuida da carteira como `proventos`, evitando que o sistema trate apenas dividendos como renda passiva.

Proventos incluem:

- Dividendos.
- Juros sobre capital proprio (JCP).
- Rendimentos de FIIs.
- Rendimentos de REITs.
- Juros, cupons e outras distribuicoes futuras.

## Arquivos

- Classificacao: `backend/app/services/income.py`
- Carteira e dashboard: `backend/app/services/portfolio.py`
- Registro de proventos: `backend/app/routers/portfolio.py`
- Eventos Alpha: `backend/app/alpha/event_engine.py`
- Insights: `backend/app/alpha/insight_engine.py`
- Resumo inteligente: `backend/app/alpha/intelligence_service.py`
- Simulador: `backend/app/engines/financial_projection_engine.py`
- Interface: `frontend/src/pages/Dashboard.jsx`, `frontend/src/pages/Projections.jsx`, `frontend/src/pages/Portfolio.jsx`, `frontend/src/pages/Radar.jsx`
- Testes: `backend/tests/test_income_classification.py`, `backend/tests/test_financial_projection_engine.py`

## Compatibilidade

A tabela existente `dividends` foi preservada para nao quebrar payloads, rotas ou dados antigos.

O campo `source` passa a aceitar semanticamente:

- `dividend`
- `jcp`
- `fii_income`
- `manual`
- fontes externas como `brapi`, `cvm`, `b3`

As chaves legadas continuam existindo:

- `dividendsMonth`
- `dividendsYear`
- `dividendHistory`
- `totalDividends`
- `reinvestedDividends`
- `withdrawnDividends`

Campos aditivos novos:

- `proceedsMonth`
- `proceedsYear`
- `incomeBreakdownMonth`
- `incomeBreakdownYear`
- `totalProceeds`
- `proceedsTotal`
- `reinvestedProceeds`
- `withdrawnProceeds`

## Regra de calculo

Todo provento registrado soma no fluxo de renda passiva:

```text
proventos_totais = dividendos + jcp + rendimentos_fii + outros_proventos
```

Yield de proventos:

```text
yield_proventos_pm = proventos_12m / valor_investido * 100
```

Renda passiva projetada:

```text
renda_passiva_mensal = patrimonio * yield_anual_de_proventos / 12
```

## JCP

JCP nao deve ser escondido como dividendo comum na leitura de produto.

Quando `source = jcp`, o sistema classifica como `JCP`.

Observacao tributaria:

- JCP normalmente sofre IR retido na fonte.
- A projecao atual trabalha com yield informado pelo usuario.
- Se o usuario usar yield liquido, a simulacao fica liquida.
- Se usar yield bruto, a simulacao fica bruta.
- Uma etapa futura deve criar motor tributario para separar bruto, imposto e liquido.

## FIIs

Rendimentos de FIIs entram como proventos imobiliarios.

Quando `asset_class = FIIs`, o sistema classifica automaticamente proventos manuais como `Rendimento de FII`, salvo se a fonte informar outro tipo.

Observacao tributaria:

- Rendimentos de FIIs podem ser isentos para pessoa fisica quando atendem aos requisitos legais.
- Ganho de capital na venda de cotas nao segue a mesma regra.
- O sistema nao deve prometer isencao; deve indicar que a regra precisa ser validada.

## Proximas evolucoes

- Criar tabela propria `income_events` ou `proceeds` em migracao aditiva futura.
- Separar valor bruto, imposto retido, valor liquido e moeda.
- Importar eventos oficiais de proventos via B3/CVM/providers.
- Incluir JCP e rendimentos de FII no backtest historico.
- Criar painel de calendario de proventos.
