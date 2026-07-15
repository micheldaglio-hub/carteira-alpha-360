# Data Lineage & Evidence Ledger

Status: fundacao implementada em 2026-07-13.

## Objetivo

Transformar o Carteira Alpha 360 em um sistema que nao apenas calcula, mas prova de onde cada numero importante veio.

O Data Lineage & Evidence Ledger responde:

- De onde veio o dado?
- Qual provider trouxe?
- Foi dado real, cache, fallback, manual ou formula?
- Quando foi observado?
- Qual formula usou?
- Qual versao da formula?
- Qual foi a confianca?
- Qual hash dos insumos gerou aquele resultado?

## Tabela

Tabela:

- `data_evidence_ledger`

Modelo:

- `backend/app/models.py::DataEvidenceLedger`

Migration:

- `backend/alembic/versions/20260713_0007_data_evidence_ledger.py`

## Campos principais

- `user_id`: usuario dono do dado, quando aplicavel.
- `asset_id`: ativo relacionado, quando aplicavel.
- `trace_id`: identificador para agrupar evidencias do mesmo calculo.
- `evidence_key`: chave logica da evidencia.
- `domain`: dominio do dado, como `market_data`, `portfolio_backtest`, `financial_formula_audit`.
- `field_name`: campo calculado ou coletado.
- `value_numeric` / `value_text`: valor registrado.
- `provider`: fonte ou motor responsavel.
- `source_type`: `provider`, `cache`, `fallback`, `manual`, `formula`, `system` ou `user_ledger`.
- `source_ref`: referencia operacional do dado.
- `formula_name`: formula usada, se aplicavel.
- `formula_version`: versao da formula.
- `input_hash`: hash dos insumos relevantes.
- `confidence`: confianca analitica.
- `quality_score`: qualidade operacional da fonte.
- `status`: `ok`, `fallback`, `partial`, `fail` etc.
- `metadata_json`: contexto adicional.
- `observed_at`: data/hora em que o dado foi observado.

## Servico

Arquivo:

- `backend/app/services/data_lineage.py`

Funcoes:

- `record_data_evidence`
- `record_evidence_batch`
- `list_data_evidence`
- `data_lineage_summary`
- `evidence_to_dict`

## Endpoints

Endpoint operacional:

- `GET /api/ops/evidence`

Filtros:

- `domain`
- `field_name`
- `asset_id`
- `limit`

O endpoint `GET /api/ops/observability` tambem passa a retornar `dataLineage`.

## Integracoes iniciais

### Market Data Engine

Arquivo:

- `backend/app/services/market_data/sync.py`

Registra evidencias de preco e fundamentos tratados.

### Portfolio Backtest

Arquivo:

- `backend/app/services/portfolio_backtest.py`

Registra evidencias de valor inicial, valor final, retornos, renda fixa, cripto, acoes, proventos e total return.

### Financial Formula Auditor

Arquivo:

- `backend/app/services/financial_formula_auditor.py`

Registra evidencia para cada caso matematico auditado e para o score geral da auditoria.

## Integracoes expandidas

Arquivo de integracao:

- `backend/app/services/data_lineage_integrations.py`

Esse servico registra evidencias de saida dos motores principais sem alterar as regras de negocio internas. Ele e chamado pelas rotas depois que cada motor calcula o payload, grava as evidencias e retorna um resumo `dataLineage`.

Dominios cobertos nesta fase:

- `dashboard`: patrimonio total, valor investido, P/L, P/L %, proventos no ano, renda passiva projetada e projecoes de 10/20/30 anos.
- `fixed_income`: valor atual, P/L, retorno, dias aplicados e CDI diario usado em RDB/CDB/Tesouro/renda fixa atrelada ao CDI.
- `financial_projection`: valor final, total aportado, proventos acumulados, capital gain, retorno total, patrimonio real, renda passiva mensal, patrimonio necessario e tempo ate a meta.
- `tax`: proventos brutos, ganho realizado, IRRF estimado, DARF estimado e liquido estimado.
- `stress_test`: patrimonio base, renda passiva base, pior impacto e score de resiliencia.
- `strategy`: score de aderencia, exposicao global, peso de cripto, maior ativo e yield de renda.
- `recommendation`: score institucional, score de confianca e breakdown do Recommended Portfolio Engine.
- `macro_fx`: indicadores macroeconomicos e taxas de cambio vindas do Macro / FX Engine.
- `copilot`: resposta, modo, fontes internas usadas e quantidade de citacoes.

## Interface

O componente `frontend/src/components/StatCard.jsx` aceita os parametros opcionais:

- `token`
- `evidenceDomain`
- `evidenceField`

Quando informados, o card exibe um botao discreto de origem do calculo. Esse botao consulta `GET /api/ops/evidence` e mostra as ultimas evidencias do campo: provider, source type, formula, confianca e valor registrado.

Paginas com origem do calculo visivel nesta fase:

- Visao Geral
- Projecoes
- Carteira Recomendada
- Impostos
- Estrategias
- Stress Test

## Regra daqui para frente

Todo numero financeiro critico novo deve registrar evidencia no ledger.

Exemplos obrigatorios:

- renda passiva projetada;
- independencia financeira;
- score Alpha;
- score institucional;
- recomendacao Alpha;
- CDI/RDB;
- cambio;
- impostos;
- stress test;
- Copilot quando citar conclusao numerica.

Nenhuma tese institucional deve usar dado sem rastreabilidade minima.
