# Financial Formula Audit

Status: implementado em 2026-07-13.

## Objetivo

Criar uma auditoria operacional das formulas financeiras centrais do Carteira Alpha 360.

Ela nao substitui testes unitarios, mas funciona como uma rotina de producao para detectar quebra matematica antes de deploy, migracao ou revisao institucional.

## Arquivo principal

- `backend/app/services/financial_formula_auditor.py`

## Job

- `financial.formula_audit`

## Casos auditados

### Patrimonio necessario para renda passiva

```text
patrimonio_necessario = meta_mensal * 12 / yield_anual
```

Exemplo auditado:

```text
15000 * 12 / 0,075 = 2.400.000
```

### Aporte sem retorno

```text
patrimonio_final = patrimonio_inicial + soma_aportes
```

Com rentabilidade zero e yield zero, nao pode existir lucro.

### Renda passiva separada de valorizacao

```text
renda_passiva_mensal = patrimonio * yield_anual / 12
```

Capital gain nao pode ser tratado como renda distribuida.

### CDI diario composto

```text
valor_final = valor_inicial * produto(1 + taxa_diaria * percentual_cdi)
```

Usado para validar RDB/CDB/Tesouro atrelados ao CDI.

### Backtest com aporte sem distorcao

```text
retorno_acumulado = produto(1 + retorno_mensal) - 1
```

Aporte aumenta patrimonio, mas nao entra como lucro percentual.

### Valor real descontando inflacao

```text
patrimonio_real = patrimonio_nominal / fator_inflacao
```

## Resultado

O auditor retorna:

- `status`
- `score`
- `passed`
- `failed`
- `cases`
- `plainLanguage`

Quando executado com banco, grava evento em `audit_events` com categoria `financial_audit`.

Se o job detectar falha, ele registra erro em `job_runs` e deve bloquear deploy ate correcao.

