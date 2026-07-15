# Research & News Engine

Status: fundacao implementada em 2026-07-13.

## Objetivo

O Research & News Engine cria o centro de evidencias do Carteira Alpha 360.

Ele consolida, por ativo:

- Fundamentos tratados pelo Knowledge Engine.
- Snapshot de mercado.
- Eventos internos do Alpha.
- Alertas e Guardian.
- Noticias externas quando provider estiver configurado.
- Lacunas de dados.
- Riscos.
- Oportunidades.
- Score de research.

## Arquivo principal

- `backend/app/wealth_os/research_news_engine.py`

## Endpoints

- `GET /api/wealth-os/research`
- `GET /api/wealth-os/research/{ticker}`

Parametros:

- `limit`: quantidade maxima de ativos no centro consolidado.
- `refresh_news`: quando `true`, tenta atualizar noticias externas pelo backend.

## Fonte de noticias

Primeira fonte implementada:

- Financial Modeling Prep Stock News API.

Endpoint documentado pelo provider:

```text
https://financialmodelingprep.com/stable/news/stock?symbols=AAPL
```

O frontend nunca chama FMP diretamente. A chamada externa fica no backend e usa cache.

## Cache

Noticias sao armazenadas em `market_data_cache` com:

- `provider = fmp`
- `data_type = news`
- TTL inicial de 6 horas

## Contratos

### ResearchEvidence

- `id`
- `type`
- `source`
- `title`
- `reading`
- `confidenceScore`
- `asOf`
- `url`

### ResearchNewsItem

- `id`
- `ticker`
- `title`
- `summary`
- `source`
- `publishedAt`
- `url`
- `sentiment`
- `relevanceScore`

### AssetResearchReport

- `ticker`
- `name`
- `assetClass`
- `sector`
- `researchScore`
- `status`
- `headline`
- `thesis`
- `evidence`
- `news`
- `risks`
- `opportunities`
- `dataGaps`
- `confidence`
- `updatedAt`

## Regra de produto

O Research & News Engine explica evidencias. Ele nao emite ordem automatica de compra ou venda.

Quando nao houver noticias, o motor deve dizer isso claramente e continuar usando evidencias internas.

## Proximas evolucoes

- CVM fatos relevantes.
- B3 eventos corporativos.
- Earnings calendar.
- Press releases.
- Transcripts.
- Classificacao de impacto por LLM com citacao das fontes.
- Auditoria de fontes por ativo.

