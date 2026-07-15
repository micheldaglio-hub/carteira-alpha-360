# Goal Engine

Status: fundacao implementada em 2026-07-13.

## Objetivo

O Goal Engine transforma a carteira atual em metas patrimoniais mensuraveis.

Metas iniciais:

- Primeiros R$ 100 mil.
- Primeiro R$ 1 milhao.
- Renda passiva mensal.
- Diversificacao global.
- Cripto sob controle.

## Fontes internas

- `get_dashboard`
- `get_positions`
- `get_projection_premises`
- `get_dashboard_projection_premises`

## Formulas

Progresso da meta:

```text
progresso = valor_atual / valor_meta * 100
```

Patrimonio necessario para renda passiva:

```text
patrimonio_necessario = renda_mensal_meta * 12 / yield_anual
```

Tempo estimado com aporte e retorno:

```text
n = log((meta + aporte / r) / (patrimonio_atual + aporte / r)) / log(1 + r)
```

Onde `r` e a rentabilidade mensal em decimal.

## Guardrails

- A meta de renda passiva usa apenas renda distribuida.
- Valorizacao patrimonial nao e tratada como renda.
- Quando faltam premissas, o motor retorna confianca menor em vez de inventar dado.

