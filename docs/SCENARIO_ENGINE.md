# Scenario & Stress Test Engine

Status: engine avancado implementado em 2026-07-13.

## Objetivo

O `Scenario & Stress Test Engine` simula choques patrimoniais severos para mostrar como a carteira se comportaria em cenarios de crise.

Ele nao tenta prever mercado. Ele aplica choques deterministicos sobre a carteira atual, separando impacto por classe, impacto consolidado e efeito estimado na renda passiva.

## Arquivos

- `backend/app/wealth_os/scenario_engine.py`
- `backend/app/wealth_os/contracts.py`
- `backend/app/routers/wealth_os.py`
- `frontend/src/pages/StressTest.jsx`

## Endpoints

- `GET /api/wealth-os/scenarios`
- `GET /api/wealth-os/stress-test`

`/scenarios` preserva a compatibilidade com o payload antigo.
`/stress-test` entrega o relatorio completo.

## Cenarios simulados

- `black_swan_global`: crise global combinada.
- `b3_crash_30`: bolsa brasileira caindo 30%.
- `usd_brl_650`: dolar alto e real pressionado.
- `selic_15`: Selic alta por mais tempo.
- `crypto_winter_70`: cripto despencando 70%.
- `passive_income_cut_35`: renda passiva caindo 35%.
- `inflation_shock`: inflacao voltando forte.
- `liquidity_freeze`: liquidez seca no mercado.

## Buckets de exposicao

- Acoes Brasil.
- FIIs.
- ETFs.
- Global.
- Cripto.
- Trading.
- Outros.

## Formulas principais

Impacto por bucket:

```text
impacto_bucket = valor_bucket * choque_percentual / 100
```

Patrimonio estressado:

```text
patrimonio_estressado = max(0, patrimonio_base + soma_impactos)
```

Impacto percentual consolidado:

```text
impacto_percentual = soma_impactos / patrimonio_base * 100
```

Renda passiva apos stress:

```text
renda_passiva_pos_stress = max(0, renda_passiva_base * (1 + choque_renda_passiva / 100))
```

Score de resiliencia:

```text
score = 100
  - abs(pior_perda_percentual) * 1.55
  - excesso_cripto_acima_de_10pct * 2.2
  + bonus_exposicao_global
  + bonus_renda_passiva
```

O resultado final e limitado entre 0 e 100.

## Linguagem do produto

O motor pode dizer:

- "A carteira fica sensivel em crise."
- "O pior cenario simulado foi crise global combinada."
- "A renda passiva deve ser simulada com corte menor antes de contar com a meta."
- "A exposicao em cripto precisa ficar separada do nucleo patrimonial."

O motor nao deve dizer:

- "Compre agora."
- "Venda agora."
- "Esse cenario vai acontecer."
- "Nao existe risco."

## Dependencias internas

- `get_dashboard`
- `get_positions`
- `Macro / FX Engine`
- snapshots de mercado disponiveis
- integracoes externas, quando conectadas

## Criterios de aceite

- O endpoint `/api/wealth-os/stress-test` retorna pelo menos oito cenarios.
- O payload antigo de `/api/wealth-os/scenarios` continua funcionando.
- A tela `Stress Test` renderiza os cenarios sem buscar provider externo no frontend.
- O pior cenario e identificado automaticamente.
- O relatorio mostra impacto por classe, impacto em renda passiva e premissas usadas.
