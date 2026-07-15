# Financial Projection Engine

Status: implementado como fonte unica de projecoes em 2026-07-09.

## Objetivo

Centralizar todos os calculos financeiros do Carteira Alpha 360 em um motor de backend:

- Simulador Patrimonial.
- Dashboard.
- Wealth Builder.
- Guardian.
- Alpha Copilot.
- Planejamento de aposentadoria.
- Independencia financeira.

Nenhuma regra financeira deve ficar em componente React.

## Arquivos

- Engine: `backend/app/engines/financial_projection_engine.py`
- Service: `backend/app/services/projections.py`
- Premissas salvas: `backend/app/services/projection_premises.py`
- Schema: `backend/app/schemas.py`
- Rota: `POST /api/projections/simulate`
- Interface: `frontend/src/pages/Projections.jsx`
- Testes: `backend/tests/test_financial_projection_engine.py`

## Conceitos

### Capital gain

Representa apenas valorizacao dos ativos.

Formula:

```text
capital_gain = patrimonio_apos_aporte * rentabilidade_mensal
```

### Renda passiva

Representa apenas dinheiro distribuido: dividendos, JCP, rendimentos de FIIs, REITs, bonds, juros, cupons e outros rendimentos. Na interface essa familia e chamada de `proventos`.

Formula:

```text
renda_passiva = patrimonio_apos_valorizacao * yield_anual_de_proventos / 12
```

### Reinvestimento

```text
proventos_reinvestidos = renda_passiva * percentual_reinvestimento
proventos_sacados = renda_passiva - proventos_reinvestidos
```

### Patrimonio final

```text
patrimonio_final = patrimonio + aportes + valorizacao + proventos_reinvestidos
```

### Patrimonio real

```text
patrimonio_real = patrimonio_nominal / fator_inflacao_acumulado
```

### Independencia financeira

A meta usa exclusivamente renda passiva.

```text
renda_passiva_mensal = patrimonio_final * yield_anual / 12
patrimonio_necessario = meta_mensal * 12 / yield_anual
percentual_da_meta_hoje = renda_passiva_atual / meta_mensal
percentual_da_meta_projetado = renda_passiva_final / meta_mensal
quanto_falta_em_patrimonio = patrimonio_necessario - patrimonio_atual_considerado
```

Capital gain nunca e contado como renda passiva.

A leitura de independencia financeira separa dois conceitos:

- Situacao atual: usa o patrimonio atual consolidado da carteira para calcular quanto falta ate o patrimonio necessario.
- Cenario projetado: usa o patrimonio final da simulacao para mostrar a renda passiva mensal estimada ao fim do prazo.

## Entradas

- `initial_wealth`
- `monthly_contribution`
- `expected_monthly_return`
- `expected_annual_dividend_yield`
- `reinvest_dividends`
- `dividend_reinvestment_rate`
- `annual_contribution_growth`
- `variable_monthly_returns`
- `variable_annual_dividend_yields`
- `variable_annual_inflation`
- `years`
- `annual_inflation`
- `passive_income_goal`

## Persistencia

Premissas podem ser salvas por usuario para evitar que a tela volte ao cenario padrao a cada atualizacao.

Tabela:

- `user_preferences`

Chave:

- `projection_premises`

Rotas:

- `GET /api/projections/premises`
- `PUT /api/projections/premises`
- `DELETE /api/projections/premises`

O frontend usa esse dado salvo para preencher a tela e simular automaticamente o ultimo cenario do usuario.

## Saidas

Compatibilidade mantida:

- `summary.finalValue`
- `summary.totalContributed`
- `summary.totalDividends`
- `summary.totalProceeds`
- `summary.totalInterest`
- `summary.estimatedMonthsToGoal`
- `summary.estimatedYearsToGoal`
- `series`
- `assumptions`

Novas capacidades:

- `breakdown.finalNominal`
- `breakdown.finalReal`
- `breakdown.capitalGain`
- `breakdown.passiveIncomeTotal`
- `breakdown.proceedsTotal`
- `breakdown.reinvestedDividends`
- `breakdown.withdrawnDividends`
- `breakdown.reinvestedProceeds`
- `breakdown.withdrawnProceeds`
- `breakdown.inflationAccumulatedPct`
- `breakdown.realGain`
- `independence`
- `growthSources`
- `intelligentReading`
- `formulas`
- `disclaimer`

Campos principais de `independence`:

- `currentWealthForGoal`: patrimonio atual considerado para a meta.
- `requiredWealth`: patrimonio necessario para gerar a meta mensal com o yield informado.
- `remainingWealthToGoal`: patrimonio que ainda falta hoje.
- `currentGoalProgressPct`: percentual da meta alcancado hoje.
- `projectedGoalProgressPct`: percentual da meta alcancado no fim do prazo simulado.
- `remainingMonthlyIncome`: renda mensal que falta hoje.
- `remainingMonthlyIncomeAtEnd`: renda mensal que faltaria no fim do prazo simulado.

## Regras de compatibilidade

- Payloads antigos continuam aceitos.
- Campos novos sao opcionais e possuem defaults seguros.
- `summary.totalInterest` foi preservado como chave legada e representa capital gain acumulado.
- Chaves com `Dividends` foram preservadas por compatibilidade; a leitura nova deve preferir `Proceeds` quando disponivel.
- `expected_annual_dividend_yield` permanece como nome de payload legado, mas seu significado de produto e yield anual de proventos.
- O frontend atual apenas exibe dados calculados no backend.

## Testes obrigatorios

Cobertos em `backend/tests/test_financial_projection_engine.py`:

- Patrimonio zero.
- Aporte zero.
- Yield zero.
- Rentabilidade negativa.
- Inflacao alta.
- Horizonte de 50 anos.
- Reinvestimento parcial.
- Meta baseada apenas em renda passiva.

## Aviso ao usuario

Toda simulacao depende das premissas informadas e nao promete rentabilidade futura.
