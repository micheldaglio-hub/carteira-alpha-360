# Tax Engine

Status: implementado em 2026-07-13 como estimativa operacional.

## Objetivo

O `Tax Engine` separa eventos tributarios da carteira para o usuario entender impacto de IRRF, DARF, isencoes condicionais e lacunas de apuracao.

Ele nao substitui contador, declaracao oficial ou apuracao fiscal completa.

## Arquivos

- `backend/app/wealth_os/tax_engine.py`
- `backend/app/wealth_os/contracts.py`
- `backend/app/routers/wealth_os.py`
- `frontend/src/pages/Tax.jsx`

## Endpoint

- `GET /api/wealth-os/tax`
- `GET /api/wealth-os/tax?year=2026&month=7`

## Regras Brasil implementadas

### Acoes

- Calcula ganho realizado por vendas usando preco medio historico.
- Se vendas mensais de acoes ficarem ate R$ 20 mil, marca potencial isencao de ganho liquido.
- Se vendas mensais passarem de R$ 20 mil, estima 15% sobre ganho positivo.

### FIIs

- Rendimentos de FIIs entram como isencao condicional.
- Ganho positivo na venda de cotas de FIIs recebe estimativa de 20%.

### JCP

- JCP e separado de dividendo comum.
- Estima IRRF de 15% sobre JCP.

### Dividendos

- Dividendos sao separados de JCP.
- O motor alerta quando dividendos mensais passam de R$ 50 mil para revisao das regras vigentes de IRRF sobre dividendos elevados.

## Lacunas controladas

- Day trade.
- Aluguel de acoes.
- Compensacao de prejuizos.
- DARFs ja pagos.
- Dedo-duro/IRRF de renda variavel.
- Cripto.
- Dividendos internacionais, withholding tax, acordo fiscal, IOF e cambio.

## Interface

A aba `Impostos` mostra:

- Proventos brutos.
- Ganho realizado.
- IRRF estimado.
- DARF estimado.
- Liquido estimado.
- Eventos tributarios.
- Regras usadas.
- Lacunas controladas.

## Fontes

Fontes usadas como base documental:

- Receita Federal: renda variavel / bolsa de valores / isencoes.
- Receita Federal: IRRF / JCP.
- Receita Federal: fundos de investimento no Brasil.

## Regra de produto

O sistema deve falar em `estimativa`, `revisao` e `lacuna controlada`. Ele nao deve afirmar que o imposto final esta oficialmente apurado.
