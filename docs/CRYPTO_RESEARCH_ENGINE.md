# Crypto Research Engine

Status: implementado como camada de validacao apos o Screener Alpha Crypto.

## Objetivo

O `Crypto Research Engine` transforma uma lista de candidatas quantitativas em um estudo mensal mais profundo.

O Screener Alpha Crypto responde: "quais ativos apareceram na varredura?".

O Crypto Research Engine responde: "qual candidata merece virar estudo do mes, com tese, riscos, tokenomics, catalisadores e cenarios?".

## Arquivo principal

- `backend/app/services/crypto_research_engine.py`

## Fluxo

1. `alpha_crypto_screener.py` busca oportunidades externas em Binance, CoinMarketCap e CoinGecko.
2. O screener monta um ranking quantitativo por acesso, preco, market cap, liquidez, momento, narrativa e contexto da carteira.
3. O `CryptoResearchEngine` recebe as melhores candidatas.
4. O motor enriquece cada candidata com dados detalhados do CoinGecko quando disponivel.
5. O motor recalcula o `researchScore`.
6. A tela `Carteira Recomendada` exibe a candidata selecionada junto com o relatorio de research.

## Metricas

O `researchScore` combina:

- `screener`: nota quantitativa original.
- `narrativa`: forca da tese setorial ou narrativa cripto.
- `tokenomics`: supply, relacao FDV/market cap e risco de diluicao.
- `liquidez`: volume e relacao volume/market cap.
- `assimetria`: preco unitario e faixa de market cap.
- `momento`: variacao de 7 e 30 dias, penalizando pumps extremos.
- `risco`: qualidade da tese, FDV excessivo e movimento esticado.
- `carteira`: se o usuario ja possui o ativo e se a exposicao ainda e pequena.

## Saida do relatorio

Cada candidata pesquisada retorna:

- ticker e nome.
- `researchScore`.
- status de research.
- decisao: nova oportunidade ou reforco de tese existente.
- conviccao.
- breakdown de notas.
- tese.
- catalisadores.
- fatores de risco.
- due diligence.
- cenarios defensivo, base e agressivo.
- tokenomics.
- leitura de mercado.
- veredito final.
- disclaimer de risco.

## Regras de seguranca

- O motor nao promete rentabilidade.
- O motor nao trata preco baixo como oportunidade por si so.
- O motor nao compara preco unitario com XRP, ADA ou outro ativo sem considerar supply e market cap.
- Se CoinGecko, CoinMarketCap ou Binance falharem, o sistema preserva fallback e nao quebra a tela.
- A candidata mensal pode ser uma moeda nova ou uma tese ja existente, mas precisa passar pelo research antes de ser destacada.

## Integracao com a tela

A tela `frontend/src/pages/ModelPortfolios.jsx` consome:

- `cryptoStudy.researchReport`.
- `cryptoStudy.researchScore`.
- `cryptoStudy.conviction`.
- `cryptoStudy.researchRanking`.

Ela exibe:

- decisao Alpha.
- conviccao.
- score de research.
- tese.
- catalisadores.
- riscos.
- due diligence.
- cenarios.
- top oportunidades do screener.

## Testes

Cobertura principal:

- `backend/tests/test_model_portfolios.py`

Testes verificam que:

- o payload de cripto passa a usar `selecionada_por_research_engine`;
- existe `researchReport`;
- o relatorio possui cenarios;
- uma candidata como FET precisa gerar tese, riscos, catalisadores e score antes de ser considerada elegivel.

## Evolucao futura

- Persistir historico mensal dos relatorios.
- Adicionar fontes on-chain.
- Avaliar unlocks e vesting.
- Avaliar holders, concentracao e exchanges.
- Adicionar auditoria de contrato quando aplicavel.
- Criar aba propria "Research Cripto".
- Conectar ao Alpha Copilot para explicar por que a candidata mudou de um mes para outro.
