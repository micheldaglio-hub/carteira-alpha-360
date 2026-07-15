# Backtest da Carteira Atual

Status: primeira versao implementada em 2026-07-11.

## Objetivo

Permitir que o usuario escolha um periodo e veja como a carteira atual teria se comportado mes a mes, usando as quantidades atuais de acoes e criptomoedas.

Exemplo: simular de 2025-01-01 ate a data atual para entender quanto o conjunto atual de ativos teria oscilado no periodo.

## Arquivos principais

- `backend/app/services/portfolio_backtest.py`
- `backend/app/routers/portfolio.py`
- `frontend/src/pages/Portfolio.jsx`
- `frontend/src/styles/index.css`

## Rota

- `GET /api/portfolio/backtest?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`

## Metodo de calculo

1. O backend le as posicoes atuais do usuario.
2. Para cada ativo, busca historico de preco pelo Market Data Engine v2.
3. A simulacao usa o valor atual real de cada ativo como ponto de partida.
4. O aporte mensal salvo nas premissas da Visao Geral e aplicado a cada novo mes simulado.
5. O aporte mensal e distribuido proporcionalmente entre os ativos existentes no momento do aporte.
6. O aporte entra antes da variacao historica daquele periodo, simulando dinheiro novo investido no comeco do mes.
7. O primeiro ponto do grafico e exatamente a data inicial escolhida; os pontos seguintes usam fechamentos mensais.
8. O sistema calcula o valor de acoes, cripto e consolidado em cada ponto.
9. O retorno mensal e calculado sem contar aporte como lucro:

```text
base_do_mes = valor_mes_anterior + aporte_do_mes
retorno_mensal_% = (valor_mes_atual / base_do_mes - 1) * 100
```

10. O retorno acumulado mede a performance encadeada dos ativos, independente do tamanho dos aportes:

```text
retorno_acumulado_% = (produto(1 + retorno_mensal_% / 100) - 1) * 100
```

11. O ganho sobre capital aplicado fica separado:

```text
capital_aplicado = valor_inicial + aportes_acumulados
ganho_sobre_capital_aplicado_% = (valor_mes_atual / capital_aplicado - 1) * 100
```

Regra de leitura do valor inicial:

```text
valor_base_do_ativo = valor_atual_real_do_ativo
variacao_historica_do_ativo = preco_historico_do_mes / preco_historico_na_data_inicial
valor_simulado_do_ativo_no_mes = valor_base_do_ativo * variacao_historica_do_ativo
valor_simulado_da_classe = soma(valor_simulado_dos_ativos_da_classe)
```

O grafico responde a pergunta: "se eu tivesse comecado na data inicial com o valor que tenho hoje em cada ativo, quanto esse conjunto teria virado?". Assim, acoes e cripto partem dos mesmos totais da alocacao atual. Integracoes externas, como Trading Desk EV+, nao entram neste backtest de ativos.

Quando existe aporte mensal salvo na Visao Geral, o grafico tambem responde: "e se eu tivesse colocado esse mesmo aporte todos os meses desde a data inicial?". O aporte aumenta patrimonio e capital aplicado, mas nao e tratado como rentabilidade.

## Campos retornados

- `summary.initialValue`
- `summary.finalValue`
- `summary.totalReturnPct`
- `summary.averageMonthlyReturnPct`
- `summary.monthlyContribution`
- `summary.totalContributed`
- `summary.capitalBaseValue`
- `summary.performancePnl`
- `summary.appliedCapitalReturnPct`
- `summary.bestMonth`
- `summary.worstMonth`
- `summary.realDataAssets`
- `summary.fallbackAssets`
- `rows[].periodLabel`
- `rows[].stocksValue`
- `rows[].cryptoValue`
- `rows[].totalValue`
- `rows[].monthlyContribution`
- `rows[].totalContributed`
- `rows[].capitalBaseValue`
- `rows[].performancePnl`
- `rows[].appliedCapitalReturnPct`
- `rows[].monthlyReturnPct`
- `rows[].stocksReturnPct`
- `rows[].cryptoReturnPct`
- `rows[].cumulativeReturnPct`

## Fontes de dados

O modulo usa o Market Data Engine v2.

Fontes principais preparadas:

- FMP para historico de acoes.
- Twelve Data para historico de acoes, ETFs e cripto quando disponivel.
- CoinGecko para historico de criptomoedas.
- Yahoo Finance Chart como fallback auxiliar de historico de acoes quando BRAPI/FMP/Twelve nao entregarem o periodo necessario.
- Mock/fallback apenas para manter a tela funcional quando providers falharem.

## Limitacoes da versao inicial

- Nao inclui dividendos, JCP, splits, bonificacoes, impostos ou taxas historicas.
- Usa o aporte mensal planejado salvo na Visao Geral, mas ainda nao reconstrui aportes reais historicos por data.
- Nao considera compras reais na data em que aconteceram.
- Usa as quantidades atuais de cada ativo.
- Se um provider nao entregar historico, o ativo fica com preco atual como fallback e o sistema informa a cobertura de dados.

## Evolucao futura

- Modo "movimentacoes reais", usando cada compra/venda na data correta.
- Inclusao de dividendos e JCP reinvestidos.
- Inclusao de splits e bonificacoes.
- Comparacao com CDI, Ibovespa, IPCA, S&P 500 e Bitcoin.
- Persistencia de snapshots mensais para P/L mensal real da carteira.
