# Market Data Engine

Status: Market Data Engine v2 implementado de forma aditiva em 2026-07-09 e expandido para arquitetura multi-provider em 2026-07-11.

## Objetivo

Criar uma camada unica para dados de mercado. Providers nao devem ser isolados por tela. O sistema deve pedir dados ao `Market Data Engine`, e o engine decide provider, cache, fallback, normalizacao e retorno padronizado.

## Responsabilidades

- Buscar cotacoes.
- Buscar fundamentos.
- Buscar dividendos e proventos.
- Buscar historico de precos.
- Buscar cambio.
- Buscar cripto.
- Buscar ETFs, acoes internacionais, FIIs, REITs e commodities.
- Normalizar unidades, moedas, datas e simbolos.
- Registrar fonte e data de atualizacao.
- Usar cache para reduzir custo e lentidao.
- Preparar fallback quando um provider falhar.

## Providers implementados ou preparados

- BRAPI.
- CVM.
- B3.
- CoinGecko.
- CoinMarketCap.
- Twelve Data.
- Banco Central.
- Financial Modeling Prep.
- Dados de Mercado.
- Fundamentus.
- Yahoo Finance Chart como fallback auxiliar de historico.
- Fintz preparado por configuracao, aguardando token/contrato de endpoints.

Providers futuros candidatos:

- Alpha Vantage.
- Finnhub.
- AwesomeAPI ou outro provider de cambio.

## Contratos conceituais

Implementacao inicial:

- Contratos: `backend/app/services/market_data/v2/contracts.py`.
- Engine: `backend/app/services/market_data/v2/engine.py`.
- Provider Manager: `backend/app/services/market_data/v2/provider_manager.py`.
- Normalizacao: `backend/app/services/market_data/v2/normalization.py`.
- Cache: `backend/app/services/market_data/v2/cache.py`.
- Providers v2: `backend/app/services/market_data/v2/providers`.
- Migration de cache: `backend/alembic/versions/20260709_0003_market_data_engine_v2_cache.py`.
- Migration de fatos/eventos: `backend/alembic/versions/20260709_0004_knowledge_facts_and_provider_events.py`.
- Testes: `backend/tests/test_market_data_engine_v2.py`.

### `MarketDataProviderV2`

Interface por provider.

Contrato implementado:

- `supports(data_type, request)`
- `fetch(data_type, request)`

Tipos de dados suportados conceitualmente:

- `quote`
- `fundamentals`
- `dividends`
- `price_history`
- `fx_rate`
- `asset_search`

### `MarketDataEngine`

Orquestrador.

Responsabilidades:

- Selecionar provider primario.
- Aplicar fallback.
- Normalizar resposta.
- Persistir cache.
- Expor dados tratados para o Knowledge Engine.

Status atual:

- Disponibiliza metodos `get_quote`, `get_fundamentals`, `get_dividends`, `get_price_history`, `get_fx_rate` e `search_assets`.
- Usa cache em memoria quando nao recebe sessao de banco.
- Usa cache em banco via `market_data_cache` quando recebe `Session`.
- Tenta provider primario e cai para fallback mock quando aplicavel.
- Registra eventos de falha em `market_data_provider_events` quando ha sessao de banco.
- Encaminha dados normalizados com `asset_id` para o Knowledge Engine persistir como `asset_facts`.
- Possui metodo `collect(data_type, request)` para consultar todos os providers disponiveis com cache separado por provider.
- O `collect` e usado por motores de validacao que precisam confirmar dados antes de declarar insuficiencia.

### `NormalizedMarketPayload`

Formato interno padrao.

Campos:

- `asset_id`
- `data_type`
- `provider`
- `source_symbol`
- `currency`
- `as_of`
- `payload`
- `quality_score`
- `warnings`

Implementacao: `NormalizedMarketData`.

## Tabelas propostas

### `market_providers`

- `id`
- `name`
- `status`
- `priority`
- `supported_asset_classes`
- `supported_markets`
- `rate_limit_per_minute`
- `created_at`
- `updated_at`

### `market_data_cache`

- `id`
- `provider`
- `data_type`
- `cache_key`
- `payload_json`
- `quality_score`
- `expires_at`
- `created_at`
- `updated_at`

### `market_data_observations`

- `id`
- `asset_id`
- `provider`
- `data_type`
- `value_date`
- `currency`
- `payload_json`
- `source_quality`
- `created_at`

### `fx_rates`

- `id`
- `base_currency`
- `quote_currency`
- `rate`
- `provider`
- `as_of`
- `created_at`

## Regras de fallback

- Se provider primario falhar, registrar evento tecnico e tentar provider secundario configurado.
- Se todos falharem, retornar ultimo cache valido com aviso de dado defasado.
- Se nao houver cache, retornar erro controlado, sem quebrar dashboard.
- Tela nunca deve chamar provider diretamente.

Status atual:

- Provider Manager captura falha do primario e tenta o proximo provider.
- Fallback mock permanece disponivel.
- O sync de mercado usa o engine v2 em modo multi-provider e nao usa dado mock para sobrescrever preco real quando fontes reais falham.
- Se Fundamentus estiver habilitado e falhar por `403`, timeout, bloqueio, rate limit ou indisponibilidade, o erro e registrado e o fluxo segue para fallback.
- Providers antigos continuam no projeto para compatibilidade.

## Providers v2 atuais

Arquivos:

- `providers/brapi.py`: provider operacional para B3 quando `BRAPI_TOKEN` esta configurado.
- `providers/dados_mercado.py`: provider opcional para dados brasileiros, habilitado por `DADOS_MERCADO_API_TOKEN`.
- `providers/fmp.py`: Financial Modeling Prep para stocks internacionais, fundamentos, dividendos, historico e busca quando `FMP_API_KEY` esta configurada.
- `providers/twelvedata.py`: Twelve Data para cotacoes, historico, dividendos, busca e suporte internacional quando `TWELVE_DATA_API_KEY` esta configurada.
- `providers/coinmarketcap.py`: fonte primaria de cripto quando `COINMARKETCAP_API_KEY` esta configurada.
- `providers/coingecko.py`: fallback de cripto por CoinGecko, usando `COINGECKO_API_KEY` quando disponivel; tambem suporta `price_history` via `market_chart/range`.
- `providers/bcb.py`: Banco Central do Brasil para cambio via SGS.
- `providers/fundamentus.py`: fonte secundaria de validacao fundamentalista.
- `providers/yahoo.py`: fallback auxiliar para `price_history` de acoes, usado quando fontes principais nao entregam historico longo.
- `providers/mock.py`: fallback de desenvolvimento, nunca deve sobrescrever dado real em sincronizacao de mercado.

Regra de consenso:

- Cada provider escreve cache proprio por `provider + data_type + symbol + mercado + moeda`.
- Quando o sistema precisa validar uma carteira, deve usar `collect`.
- `sync_asset_market_data` consolida os campos de fundamentos por prioridade de fonte.
- O Knowledge Engine salva fatos por fonte e pode marcar divergencias.
- Se nenhuma fonte real trouxer determinado campo, o campo permanece ausente/parcial.
- A ausencia so deve ser comunicada depois de tentar os providers reais disponiveis.

## Provider Fundamentus

Status: implementado como provider secundario e opcional.

Arquivo:

- `backend/app/services/market_data/v2/providers/fundamentus.py`

Regras:

- Nunca e fonte principal.
- Nao e chamado pelo frontend.
- Desativado por padrao via `FUNDAMENTUS_ENABLED=false`.
- So participa de `fundamentals`.
- Usa o cache do Market Data Engine; novas chamadas externas so acontecem em cache miss.
- Verifica `robots.txt` antes de acessar `detalhes.php`.
- Aplica rate limit baixo por `FUNDAMENTUS_RATE_LIMIT_SECONDS`.
- Em bloqueio ou indisponibilidade, retorna fallback por meio do Provider Manager.
- Salva dados como fonte `fundamentus` no Knowledge Engine quando houver `asset_id`.
- Nunca sobrescreve BRAPI, CVM ou B3.

Campos normalizados:

- P/L -> `pe_ratio`
- P/VP -> `pvp`
- EV/EBITDA -> `ev_ebitda`
- ROE -> `roe`
- ROIC -> `roic`
- Margem liquida -> `net_margin`
- Divida liquida/EBITDA -> `debt_to_ebitda`
- Dividend yield -> `dividend_yield`
- Payout -> `payout`
- Receita -> `revenue`
- Lucro -> `profit`
- Valor de mercado -> `market_value`

## Impacto sobre codigo atual

- `backend/app/services/market_data/providers`: deve virar implementacao de providers do engine, nao dependencia direta de tela.
- `portfolio/sync-market`: deve chamar `MarketDataEngine`.
- `crypto`: deve usar o mesmo engine, com provider CoinMarketCap ou CoinGecko.
- `radar`: deve consumir Knowledge Engine, nao provider cru.

## Criterios de aceite

- Existe um contrato unico para providers.
- Dados de acoes, ETFs, cripto e cambio entram pelo mesmo fluxo.
- Falha de provider nao derruba a interface.
- Todas as respostas guardam origem e data.
