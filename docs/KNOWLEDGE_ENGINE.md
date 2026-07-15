# Knowledge Engine

Status: primeira implementacao tecnica aditiva em 2026-07-09.

## Objetivo

Criar o motor central de conhecimento dos ativos. Providers entregam dados crus ou semi-normalizados; o `Knowledge Engine` transforma isso em informacao confiavel, historica e consumivel por dashboard, scores, alertas, radares e Copilot.

## Regra central

Telas e scores nao devem buscar dados crus diretamente dos providers. Eles devem consumir dados tratados pelo `Knowledge Engine` ou por servicos derivados dele.

Implementacao atual:

- Engine: `backend/app/engines/knowledge_engine.py`.
- Modelos: `AssetFact`, `AssetMetricDivergence` e `MarketDataProviderEvent` em `backend/app/models.py`.
- Migration: `backend/alembic/versions/20260709_0004_knowledge_facts_and_provider_events.py`.
- Testes: `backend/tests/test_fundamentus_knowledge_engine.py`.

## Responsabilidades

- Armazenar fundamentos.
- Armazenar indicadores.
- Armazenar dividendos.
- Armazenar eventos corporativos.
- Armazenar historico de precos.
- Armazenar splits e bonificacoes.
- Armazenar resultados.
- Calcular metricas de qualidade.
- Calcular metricas de risco.
- Organizar dados setoriais.
- Organizar metadados globais.
- Controlar qualidade, data e origem dos dados.

## Entidades conceituais

### `AssetFact`

Fato bruto ou normalizado sobre um ativo.

Exemplos:

- Receita anual.
- Lucro liquido.
- ROE.
- Dividend yield.
- Divida liquida/EBITDA.
- Patrimonio liquido.

Implementado como fato tratado por fonte, metrica e periodo. O mesmo indicador pode existir em BRAPI, CVM, B3, Fundamentus ou fonte futura sem um sobrescrever o outro.

Fontes primarias/preferenciais iniciais:

- `brapi`
- `cvm`
- `b3`

Fonte secundaria de comparacao inicial:

- `fundamentus`

### `AssetMetric`

Metrica derivada e pronta para consumo.

Exemplos:

- Crescimento medio de receita em 5 anos.
- Consistencia de dividendos.
- Volatilidade de 12 meses.
- Score de qualidade.

### `CorporateEvent`

Evento societario.

Exemplos:

- Split.
- Grupamento.
- Bonificacao.
- Reducao de dividendos.
- Resultado trimestral.
- Mudanca de ticker.

## Tabelas propostas

### `asset_facts` implementada

- `id`
- `asset_id`
- `source`
- `metric_key`
- `value_numeric`
- `value_text`
- `currency`
- `unit`
- `period`
- `confidence`
- `raw_payload_json`
- `as_of`
- `created_at`
- `updated_at`

Escopo unico:

- `asset_id`
- `source`
- `metric_key`
- `period`

### `asset_metric_divergences` implementada

- `id`
- `asset_id`
- `metric_key`
- `primary_source`
- `comparison_source`
- `primary_value`
- `comparison_value`
- `divergence_pct`
- `status`
- `created_at`

Regra:

- Divergencias sao registradas quando a diferenca relativa entre fonte primaria e fonte de comparacao for maior ou igual a 15%.
- A divergencia nao altera automaticamente snapshots, scores ou recomendacoes.
- O objetivo e auditoria e futura tela "Centro Fundamentalista".

### `market_data_provider_events` implementada

- `id`
- `provider`
- `event_type`
- `severity`
- `message`
- `status_code`
- `created_at`

Uso:

- Registrar bloqueio, timeout, rate limit e indisponibilidade de providers.
- Diferenciar falha tecnica externa de regra de negocio.

### `asset_metrics`

- `id`
- `asset_id`
- `metric_key`
- `metric_value`
- `metric_unit`
- `period`
- `methodology_version`
- `confidence`
- `as_of`
- `created_at`

### `asset_price_history`

- `id`
- `asset_id`
- `date`
- `open`
- `high`
- `low`
- `close`
- `adjusted_close`
- `volume`
- `currency`
- `provider`

### `asset_income_events`

- `id`
- `asset_id`
- `event_type`
- `ex_date`
- `payment_date`
- `amount`
- `currency`
- `tax_notes`
- `provider`

### `corporate_events`

- `id`
- `asset_id`
- `event_type`
- `title`
- `description`
- `effective_date`
- `payload_json`
- `provider`

### `sector_datasets`

- `id`
- `taxonomy`
- `country_code`
- `sector`
- `industry`
- `metric_key`
- `metric_value`
- `as_of`
- `provider`

## Impacto sobre scores atuais

- Radar de Dividendos deve usar metricas tratadas, como consistencia, frequencia, payout, recorrencia e risco de corte.
- Radar de Crescimento deve usar metricas tratadas, como crescimento de receita, lucro, ROE, ROIC e margem.
- Alpha Score 2.0 deve consumir `asset_metrics`, nao snapshots soltos.
- Dados parciais devem continuar aparecendo como dados parciais.

## Criterios de aceite

- Scores conseguem explicar origem das metricas.
- Provider pode mudar sem alterar tela.
- Historico de precos, dividendos e fundamentos ficam separados por natureza de dado.
- O sistema sabe diferenciar dado ausente, dado zero e dado desatualizado.
