# Asset Engine Universal

Status: Etapa 1 tecnica implementada de forma aditiva em 2026-07-09.

## Objetivo

O Carteira Alpha 360 deve tratar todo investimento como um `Asset` universal. A plataforma nao deve ser organizada internamente por telas como acoes, FIIs, ETFs ou cripto. Essas categorias sao visoes de produto; o nucleo deve pensar em patrimonio global.

Exemplos:

- WEGE3: `Asset` de classe `Equity`, pais `BR`, mercado `B3`, moeda de negociacao `BRL`.
- AAPL: `Asset` de classe `Equity`, pais `US`, mercado `NASDAQ`, moeda de negociacao `USD`.
- BTC: `Asset` de classe `Crypto`, mercado `Crypto`, moeda base `BTC`, moeda de precificacao variavel.
- IVVB11: `Asset` de classe `ETF`, pais `BR`, exposicao principal `US`, moeda de negociacao `BRL`.
- VNQ: `Asset` de classe `ETF/REIT`, pais `US`, moeda de negociacao `USD`.
- Ouro: `Asset` de classe `Commodity`.
- Caixa: `Asset` de classe `Cash`.

## Principio central

Todo ativo tem uma identidade global unica, metadados padronizados e classificacoes flexiveis. Classe e subclasse nao devem virar tabelas isoladas por produto. O sistema deve permitir novas classes sem reescrever dashboard, carteira, score ou providers.

## Campos conceituais do Asset

- `id`: identificador interno universal.
- `asset_class`: classe principal, como Equity, ETF, REIT, Crypto, Commodity, Cash, Fixed Income, Fund, Alternative.
- `asset_subclass`: subclasse, como Common Stock, Preferred Stock, FII, ETF Equity, ETF Bond, Stablecoin, Gold.
- `country`: pais legal ou principal do ativo.
- `region`: regiao economica, como Latin America, North America, Europe, Global.
- `market`: mercado de negociacao, como B3, NASDAQ, NYSE, Crypto, OTC.
- `exchange`: bolsa especifica, quando aplicavel.
- `base_currency`: moeda economica do ativo.
- `trading_currency`: moeda em que o usuario negocia.
- `sector`: setor padronizado.
- `industry`: industria padronizada.
- `ticker`: ticker exibido ao usuario.
- `provider_symbol`: simbolo usado por provider externo.
- `isin`: identificador global ISIN, quando existir.
- `cusip`: identificador CUSIP, quando existir.
- `universal_symbol`: chave interna canonica para desambiguacao.

## Tabelas propostas

Implementacao inicial:

- Migration: `backend/alembic/versions/20260709_0002_asset_engine_universal.py`.
- Modelo ORM: `backend/app/models.py`.
- Helper de compatibilidade: `backend/app/engines/asset_engine.py`.
- Testes: `backend/tests/test_asset_engine_compatibility.py`.

### `assets`

Tabela canonica de ativos. Pode evoluir da tabela atual.

Campos propostos:

- `id`
- `universal_symbol`
- `ticker`
- `name`
- `asset_class`
- `asset_subclass`
- `country_code`
- `region`
- `market`
- `exchange`
- `base_currency`
- `trading_currency`
- `sector`
- `industry`
- `isin`
- `cusip`
- `provider_symbol`
- `status`
- `created_at`
- `updated_at`

Observacao de compatibilidade:

- `asset_class` continua preservando valores atuais como `Acoes`, `FIIs`, `ETFs` e `Cripto`.
- `universal_symbol` foi criado como identificador canonico interno.
- Os campos novos foram adicionados sem remover campos antigos.

### `asset_identifiers`

Mapeia multiplos identificadores do mesmo ativo.

Campos propostos:

- `id`
- `asset_id`
- `identifier_type`: ticker, isin, cusip, figi, provider_symbol, coingecko_id, coinmarketcap_id.
- `identifier_value`
- `provider`
- `market`
- `is_primary`

### `asset_classifications`

Permite classificacoes multiplas sem engessar o modelo.

Campos propostos:

- `id`
- `asset_id`
- `taxonomy`
- `level`
- `code`
- `label`
- `weight`
- `source`

### `asset_exposures`

Representa exposicao economica de ETFs, fundos, REITs, commodities e cripto.

Campos propostos:

- `id`
- `asset_id`
- `exposure_type`: country, region, sector, currency, asset_class, factor.
- `exposure_key`
- `percentage`
- `source`
- `as_of_date`

## Impacto sobre o codigo atual

- `backend/app/models.py`: a tabela `Asset` atual deve ser expandida de forma aditiva, nao substituida de uma vez.
- `portfolio`: deve continuar calculando posicoes por transacoes, mas passar a depender da identidade universal do ativo.
- `crypto`: deve deixar de ser um silo conceitual; a tela pode continuar existindo, mas cripto deve ser `Asset`.
- `radar`: deve consumir ativos filtrados por classe/estrategia, nao listas manuais por tela.
- `dashboard`: alocacao por classe deve usar `asset_class`, e nao pressupor apenas acoes/FIIs/ETFs/cripto.

## Regras de implementacao

- Nao quebrar tickers existentes.
- Nao apagar campos atuais sem migracao.
- Criar migracoes Alembic aditivas.
- Manter compatibilidade com dados locais do Michel.
- Criar adaptadores para transformar dados antigos no modelo universal.

## Criterios de aceite

- Um unico `Asset` consegue representar acao brasileira, acao americana, ETF, FII, REIT, cripto, ouro e caixa.
- Nenhuma tela atual perde funcionalidade.
- Os dados antigos continuam abrindo e calculando carteira.
- O modelo permite adicionar provider internacional sem alterar telas.

## Backfill executado

Banco local `backend/carteira_alpha.db` migrado para `20260709_0002`.

Resumo:

- 18 ativos preenchidos com `universal_symbol`.
- 36 identificadores criados.
- 54 classificacoes criadas.
- 46 exposicoes criadas.

Exemplos:

- `BBDC4 -> BR:B3:BBDC4`
- `TAEE11 -> BR:B3:TAEE11`
- `BTC -> CRYPTO:BTC`
- `ADA -> CRYPTO:ADA`
