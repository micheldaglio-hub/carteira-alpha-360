# Global Backtest Engine

Status: fundacao implementada em 2026-07-12.

## Objetivo

Comparar formas de exposicao internacional dentro do Carteira Alpha 360:

- Stock direto no exterior.
- BDR proxy negociado na B3.
- ETF global negociado no Brasil.

O motor trabalha em BRL como moeda-base do usuario e considera:

- Historico de precos.
- Cambio.
- Dividendos internacionais.
- Retencao tributaria simulada.
- Custos/arrasto estrutural de BDR e ETF.
- Fallback identificado quando providers reais nao entregam historico suficiente.

## Arquivo principal

- `backend/app/services/global_backtest.py`

## Rotas

- `GET /api/model-portfolios/global-backtest`
- `POST /api/model-portfolios/global-backtest/run`

Parametros:

- `start_date`
- `end_date`
- `initial_value`

O `GET` calcula com a base disponivel e fallback seguro.  
O `POST` tenta enriquecer com providers reais via Market Data Engine.

## Fontes previstas

Precos e dividendos:

- Financial Modeling Prep.
- Twelve Data.
- Yahoo Finance como fallback auxiliar de historico.
- BRAPI/Yahoo para BDRs e ETFs brasileiros quando suportado.

Cambio:

- Banco Central para taxa atual quando disponivel.
- FX/Money Engine futuro para serie historica completa.
- Fallback Alpha identificado enquanto a serie historica nao existir.

## Veiculos comparados

### Stock direto

Simula compra direta das acoes internacionais em moeda original.

Regras:

- Valor inicial em BRL e convertido economicamente por exposicao cambial.
- Preco do ativo varia em moeda original.
- Valor e convertido de volta para BRL por cambio.
- Dividendos sao tratados como liquidos e reinvestidos.
- Retencao padrao simulada: 30% quando nao houver regra especifica.

### BDR proxy

Simula exposicao via BDR na B3.

Regras:

- Usa o mesmo ativo economico do stock.
- Cambio continua impactando a exposicao.
- Aplica arrasto anual estimado de estrutura/custos quando nao houver historico real.
- Dividendos sao tratados como repasse liquido simulado.

### ETF global

Simula exposicao via cesta de ETFs negociados no Brasil:

- IVVB11.
- WRLD11.
- NASD11.

Regras:

- Quando houver historico real, usa a cota do ETF.
- Quando nao houver, usa proxy da carteira global com taxa anual estimada.
- Proventos tendem a ficar embutidos ou reinvestidos na cota, portanto nao sao tratados como renda distribuida para o usuario nessa primeira versao.

## Payload

O motor retorna:

- `rows`: serie mensal com `stockDirectValue`, `bdrValue`, `globalEtfValue`, retornos e cambio.
- `vehicles`: resumo por veiculo.
- `summary`: melhor veiculo no periodo, USD/BRL inicial/final, impacto cambial e cobertura de fontes.
- `comparison`: tabela operacional stock x BDR x ETF.
- `assumptions`: premissas explicitas.
- `warnings`: avisos de fallback.
- `dataSources`: fontes usadas para preco, dividendos e cambio.

## Regras de comunicacao

Permitido:

- "No periodo simulado, stock direto performou melhor."
- "O ETF foi o caminho mais simples."
- "BDR manteve exposicao cambial com execucao em BRL."
- "Historico foi calculado com fallback identificado."

Nao permitido:

- "Esse caminho e garantidamente melhor."
- "Invista sem medo."
- "Vai performar mais."
- "Essa simulacao garante resultado futuro."

## Limitacoes atuais

- Cambio historico ainda usa fallback quando nao houver provider temporal.
- Dividendos internacionais podem ser estimados por yield anual quando o provider nao entregar eventos.
- Impostos sao simulados por regra generica, nao por situacao fiscal individual.
- ETF global usa cesta inicial e nao substitui uma analise tributaria/operacional completa.

## Proximas evolucoes

- Criar FX/Money Engine com serie historica real USD/BRL, EUR/BRL, CHF/BRL e outras moedas.
- Persistir rodadas de backtest global.
- Comparar stock direto, BDR e ETF por ativo especifico.
- Incluir spread cambial, IOF, corretagem, taxas de custodia e imposto sobre ganho de capital.
- Separar dividendos brutos, imposto retido, dividendos liquidos e reinvestimento.
