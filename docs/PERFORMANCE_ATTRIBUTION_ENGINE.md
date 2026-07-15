# Performance Attribution Engine

Status: fundacao tecnica implementada em 2026-07-14.

## Objetivo

O `Performance Attribution Engine` explica a performance de uma edicao premium da Carteira Recomendada Alpha por ativo, fonte de retorno e qualidade de dado.

Ele nao cria recomendacao nova e nao promete resultado. Ele responde:

- quanto a carteira-modelo estimou de retorno no periodo;
- quais ativos mais contribuiram;
- quais ativos puxaram a performance para baixo;
- quanto veio de preco;
- quanto veio de renda estimada por yield/proventos;
- qual benchmark foi usado, se informado;
- qual foi a qualidade dos dados usados;
- quais evidencias foram gravadas no Data Evidence Ledger.

## Arquivos

- `backend/app/premium_research/performance_attribution.py`
- `backend/app/routers/premium.py`
- `backend/app/models.py`
- `backend/alembic/versions/20260714_0012_performance_attribution.py`
- `backend/tests/test_premium_research_api.py`

## Tabelas

### research_attribution_runs

Guarda uma rodada de atribuicao de performance para uma publicacao premium.

Campos centrais:

- `publication_id`
- `publication_version_id`
- `period`
- `start_date`
- `end_date`
- `benchmark_name`
- `portfolio_return_pct`
- `benchmark_return_pct`
- `excess_return_pct`
- `price_return_pct`
- `income_return_pct`
- `data_quality_score`
- `top_contributors_json`
- `detractors_json`
- `warnings_json`
- `metadata_json`

### research_attribution_assets

Guarda a contribuicao por ativo dentro de uma rodada.

Campos centrais:

- `run_id`
- `asset_id`
- `ticker`
- `target_weight`
- `start_price`
- `end_price`
- `price_return_pct`
- `income_return_pct`
- `total_return_pct`
- `contribution_pct`
- `data_quality_score`
- `provider`
- `source_type`
- `evidence_ids_json`

## Formula

Para cada ativo:

```text
retorno_preco_% = ((preco_final / preco_inicial) - 1) * 100
retorno_renda_% = dividend_yield_anual * dias_no_periodo / 365
retorno_total_% = retorno_preco_% + retorno_renda_%
contribuicao_% = peso_normalizado * retorno_total_% / 100
```

Para a carteira-modelo:

```text
retorno_carteira_% = soma(contribuicao_% por ativo)
retorno_preco_carteira_% = soma(peso_normalizado * retorno_preco_% / 100)
retorno_renda_carteira_% = soma(peso_normalizado * retorno_renda_% / 100)
excesso_% = retorno_carteira_% - retorno_benchmark_%
```

Se nao houver benchmark configurado, o excesso fica em `0` e o motor registra aviso para evitar leitura enganosa.

## Fontes

O engine usa:

- `PublicationAsset` para ativos e pesos da edicao premium.
- `Asset` e `MarketSnapshot` para preco atual e yield.
- `MarketDataEngine v2` para historico de precos quando `refresh_market=true`.
- `Data Evidence Ledger` para registrar as conclusoes publicadas.

Por padrao, `refresh_market=false`, entao o motor nao depende de provider externo para criar uma rodada. Quando faltar historico, ele usa snapshot/fallback, marca menor qualidade e registra aviso.

## APIs

```http
POST /api/premium/publications/{publication_id}/attribution/run
GET /api/premium/attribution/runs
GET /api/premium/attribution/runs/{run_id}
```

Payload de criacao:

```json
{
  "publication_version_id": "opcional",
  "start_date": "2026-07-01",
  "end_date": "2026-07-31",
  "benchmark_name": "IBOV",
  "benchmark_return_pct": 1.25,
  "refresh_market": false
}
```

## Evidencias

Cada ativo gera evidencia:

```text
domain = premium_research_attribution
field_name = asset_total_return_pct
formula_name = asset_total_return_attribution
formula_version = 2026.07.attrib1
```

Cada rodada gera evidencia:

```text
domain = premium_research_attribution
field_name = portfolio_return_pct
formula_name = portfolio_total_return_attribution
formula_version = 2026.07.attrib1
```

## Regras

- Aporte nunca entra como lucro.
- Benchmark ausente nao deve gerar excesso de retorno automatico.
- Historico insuficiente deve aparecer como `fallback`.
- O motor nunca publica sozinho.
- Toda rodada fica vinculada a uma publicacao e versao premium.
- Toda conclusao numerica central deve ter evidencia.

## Testes

Validado por:

```text
python -m unittest tests.test_premium_research_api
```

O teste cria rascunho premium, executa Research Committee, executa Performance Attribution, lista rodadas e consulta detalhes com linhas por ativo.
