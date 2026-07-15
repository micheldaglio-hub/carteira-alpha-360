# Total Return Engine

## Objetivo

O `Total Return Engine` separa retorno de preco de retorno total. Ele existe para impedir uma leitura enganosa do tipo "a acao subiu X%" quando o investidor tambem recebeu dividendos, JCP ou rendimentos de FIIs.

## Fonte dos dados

- Preco e historico: `Market Data Engine` via backtest da carteira.
- Proventos/JCP/rendimentos: tabela interna `dividends`, vinculada ao usuario e ao ativo.
- Classificacao do rendimento: `backend/app/services/income.py`.

## Regra de calculo

Retorno de preco:

```text
retorno_preco = variacao_do_ativo_no_periodo
```

Retorno total mensal:

```text
retorno_total_mes = retorno_preco_mes + (proventos_do_mes / base_de_performance_do_mes)
```

Retorno total acumulado:

```text
retorno_total_acumulado = produto(1 + retorno_total_mes) - 1
```

Aporte mensal nao entra como lucro. Aporte aumenta patrimonio, mas o percentual de performance continua sendo calculado por retorno encadeado.

## Limite atual

O motor usa apenas rendimentos cadastrados internamente pelo usuario. Historico externo de dividendos/JCP ainda precisa passar pelo `Knowledge Engine` antes de entrar no backtest para evitar dupla contagem ou fonte sem auditoria.

## Arquivo principal

- `backend/app/services/total_return_engine.py`

