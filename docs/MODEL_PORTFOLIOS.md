# Carteira Recomendada - Estudos Patrimoniais

Status: modulo implementado com Screener Alpha B3, Screener Alpha FIIs, Screener Alpha Global, Screener Alpha Crypto e validacao Alpha propria.

Desde 2026-07-13, o modulo tambem possui o `Alpha Confidence Engine`, responsavel por transformar a carteira recomendada em uma leitura auditavel de confianca. Ele mostra nota geral, criterios que passaram, limitacoes, leitura humana e confianca por ativo. A camada nao promete resultado e nao transforma nenhum ativo em "compra sem medo".

## Procedencia da carteira atual

A primeira carteira nasceu dos relatorios enviados pelo usuario e foi normalizada para dentro do Carteira Alpha 360 como historico de estudo.

A partir de 2026-07-11, ela tambem passa por uma validacao Alpha propria. Essa validacao nao copia o texto dos relatorios: ela cruza os ativos com os dados internos, tenta atualizar fundamentos via Market Data Engine, calcula scores e classifica cada ativo por status.

Regra essencial: se as fontes atuais nao entregarem fundamentos suficientes, o sistema deve mostrar `dados_insuficientes` ou `em_validacao`. O Alpha nao deve marcar uma carteira como validada apenas porque ela foi importada de um relatorio.

A partir da implementacao do `Screener Alpha B3`, a carteira principal exibida na tela deixou de ser a carteira importada da Manus. Ela passa a ser gerada pelo backend em `backend/app/services/alpha_b3_screener.py`, usando universo B3, filtros de setores perenes, leitura proprietaria, scoring e pesos oficiais Alpha.

Desde 2026-07-12, FIIs deixam de ser tratados como extensao da carteira de acoes. Eles passam a ter motor separado em `backend/app/services/alpha_fii_screener.py`, porque fundos imobiliarios exigem indicadores proprios como vacancia, P/VP, qualidade do portfolio, gestao, liquidez, risco de credito e recorrencia de rendimentos.

Tambem em 2026-07-12, a plataforma ganhou a fundacao do `Screener Alpha Global`, em `backend/app/services/alpha_global_equity_screener.py`. Ele cria uma watchlist inicial de acoes internacionais para diversificacao geografica, cambial e setorial. A lista global ainda nao representa varredura completa de todas as bolsas do mundo; ela e a base para conectar FMP, Twelve Data, cambio, backtest internacional e rodadas mensais futuras.

## Screener Alpha B3

Arquivo:

- `backend/app/services/alpha_b3_screener.py`

Rotas:

- `GET /api/model-portfolios/screener`
- `POST /api/model-portfolios/screener/run`

Responsabilidades:

- Ler universo B3 via BRAPI `available`, quando disponivel.
- Remover tickers que parecem FIIs, ETFs, BDRs, recibos, fracionarios ou instrumentos fora da tese de acoes brasileiras.
- Avaliar candidatas de setores perenes.
- Usar Market Data Engine para enriquecer fundamentos quando solicitado.
- Combinar score estrategico, qualidade, liquidez, governanca, risco e dados quantitativos.
- Gerar a `Carteira Recomendada Alpha oficial`.

Carteira oficial atual:

- BBSE3: 13%.
- TAEE11: 12%.
- ITSA4: 11%.
- BBAS3: 10%.
- EGIE3: 10%.
- CPFE3: 9%.
- SAPR11: 9%.
- PSSA3: 8%.
- VIVT3: 8%.
- CSMG3: 10%.

Ativos da carteira antiga que ficaram fora do nucleo atual:

- BBDC4: banco grande, mas ainda depende de recuperacao clara de rentabilidade.
- BRSR6: banco regional com maior risco politico e concentracao geografica.
- AURE3: boa candidata, mas com menor previsibilidade de dividendos que as selecionadas.
- CPLE6: boa empresa de energia, mas perdeu vaga para o conjunto TAEE11, EGIE3 e CPFE3.

## Screener Alpha FIIs

Arquivo:

- `backend/app/services/alpha_fii_screener.py`

Rotas:

- `GET /api/model-portfolios/fii-screener`
- `POST /api/model-portfolios/fii-screener/run`

Responsabilidades:

- Avaliar FIIs separados de acoes.
- Pontuar recorrencia de renda, liquidez, qualidade do portfolio, gestao, valuation e risco.
- Separar segmentos como logistica, hibrido, shoppings e recebiveis.
- Exibir a `Carteira Alpha FIIs - estudo inicial` dentro da tela Carteira Recomendada.

Carteira de estudo inicial:

- HGLG11: 16%.
- KNRI11: 15%.
- BTLG11: 14%.
- XPML11: 13%.
- VISC11: 11%.
- KNCR11: 12%.
- MXRF11: 10%.
- CPTS11: 9%.

Observacao: rendimentos de FIIs entram como proventos imobiliarios. A isencao de IR nao deve ser prometida; o sistema deve tratar como regra tributaria sujeita a requisitos legais.

Observacao de produto: a lista atual de FIIs e uma fundacao em validacao. Ela nao deve ser comunicada como "melhores FIIs do mercado" ate que o motor tenha historico real de vacancia, P/VP, rendimentos, liquidez, gestao, concentracao de imoveis e backtest por provider.

## Screener Alpha Global

Arquivo:

- `backend/app/services/alpha_global_equity_screener.py`

Rotas:

- `GET /api/model-portfolios/global-screener`
- `POST /api/model-portfolios/global-screener/run`

Responsabilidades:

- Criar base de acoes internacionais dentro do conceito universal de `Asset`.
- Diversificar por pais, regiao, moeda, bolsa e setor.
- Usar criterios estruturais de qualidade, moat, liquidez, governanca, diversificacao geografica e risco.
- Enriquecer fundamentos via Market Data Engine quando FMP/Twelve Data estiverem disponiveis.
- Exibir a `Carteira Alpha Global - watchlist inicial` na tela Carteira Recomendada.

Universo inicial:

- MSFT, AAPL, GOOGL, NVDA, V, JNJ, PG, KO, ASML, NVO, NESN.SW, TSM e BHP.

Observacao de produto: a lista global reduz a dependencia do Brasil, mas ainda nao e uma auditoria completa de todos os mercados internacionais. As proximas evolucoes devem incluir backtest com cambio, dividendos internacionais, imposto retido na fonte, comparacao com BDRs/ETFs e historico mensal de decisoes.

## Backtest internacional com cambio

Arquivo:

- `backend/app/services/global_backtest.py`

Rotas:

- `GET /api/model-portfolios/global-backtest`
- `POST /api/model-portfolios/global-backtest/run`

Responsabilidades:

- Comparar `stock direto`, `BDR proxy` e `ETF global`.
- Manter BRL como moeda-base do usuario.
- Considerar cambio, dividendos internacionais, retencao simulada e custos estruturais.
- Mostrar fonte/fallback para precos, dividendos e cambio.
- Exibir a comparacao na tela Carteira Recomendada, abaixo da Carteira Alpha Global.

Regras importantes:

- O estudo historico nao promete resultado futuro.
- Quando providers reais nao entregarem historico, o motor usa fallback identificado e mostra aviso.
- ETF global trata proventos como embutidos/reinvestidos na cota nesta primeira versao.
- Dividendos internacionais usam retencao padrao simulada quando nao houver regra tributaria especifica.

## Objetivo

O modulo Carteira Recomendada transforma relatorios analiticos enviados pelo usuario em uma leitura estruturada dentro do Carteira Alpha 360.

Ele foi criado para reproduzir a utilidade pratica das analises antigas da Manus, mas dentro das regras oficiais do projeto:

- Nao emitir ordem direta de compra ou venda.
- Nao prometer rentabilidade.
- Separar carteira principal, ativos de maior risco e cripto especulativa.
- Explicar tese, risco, papel do ativo e pontos de monitoramento.
- Tratar backtest como estudo historico, nao como garantia futura.

## Arquitetura

Backend:

- `backend/app/services/model_portfolios.py`
- `backend/app/services/alpha_confidence_engine.py`
- `backend/app/routers/model_portfolios.py`
- Rota: `GET /api/model-portfolios`
- Rota: `POST /api/model-portfolios/validate`

Frontend:

- `frontend/src/pages/ModelPortfolios.jsx`
- Menu: `Carteira Recomendada`

Testes:

- `backend/tests/test_model_portfolios.py`

Documentacao especifica:

- `docs/ALPHA_CONFIDENCE_ENGINE.md`

## Validacao Alpha

A Carteira Recomendada agora possui uma camada inicial de validacao propria.

O motor avalia cada ativo por:

- Qualidade dos dados disponiveis.
- Score de dividendos.
- Score de seguranca.
- Score de valuation.
- Score de risco.
- Perenidade do setor.
- Risco qualitativo importado do estudo.
- Peso individual e concentracao setorial.

Status possiveis por ativo:

- `validado_alpha`: passou nos criterios atuais.
- `em_observacao`: possui tese, mas exige acompanhamento ou ajuste.
- `reprovado_alpha`: nao passou nos criterios atuais.
- `dados_insuficientes`: faltam dados para validacao independente.

Status possiveis da carteira:

- `validada_alpha`.
- `em_observacao`.
- `requer_ajustes`.
- `em_validacao`.

A rota `POST /api/model-portfolios/validate` tenta atualizar os dados de mercado quando providers estao configurados e recalcula a validacao. A sincronizacao usa `MarketDataEngine.collect` para consultar as fontes reais disponiveis antes de sinalizar insuficiencia.

Em 2026-07-11, o BRAPI retornou preco, P/L e valor de mercado para a maioria dos ativos testados, mas nao retornou todos os campos necessarios para uma validacao completa de dividendos, como dividend yield, payout, consistencia, ROE, ROIC, margem e divida liquida/EBITDA. O sistema passou a tentar BRAPI, FMP, Twelve Data, Fundamentus e outras fontes configuradas antes de concluir insuficiencia. Ainda assim, se os dados reais permanecerem parciais, o status correto continua sendo `Validacao parcial`.

O FundamentusProviderV2 existe como fonte secundaria e opcional para validacao/comparacao. Ele deve permanecer fora do frontend, com cache, verificacao de robots, rate limit conservador e fallback. Dados de Fundamentus devem ser salvos como fonte `fundamentus` no Knowledge Engine e nunca sobrescrever dados oficiais sem validacao.

## Alpha Confidence Engine

O `Alpha Confidence Engine` consolida a confianca da carteira recomendada.

Ele recebe Screener Alpha B3, FIIs, Global, Crypto Research, validacao e backtests. A partir disso, gera o payload aditivo `confidenceReport`.

O `confidenceReport` contem:

- Nota geral de confianca.
- Classificacao humana.
- Resumo em linguagem simples.
- Gates de confianca: dados, metodologia, fundamentos, risco, diversificacao, historico e fontes.
- Nota por ativo.
- Regras nao negociaveis.

Regra de produto:

- A tela pode mostrar `Alta confianca Alpha`.
- A tela nao pode mostrar `compre sem medo`, `garantia`, `certeza` ou promessa equivalente.
- A nota de confianca reduz quando faltam fontes, historico, dados ou quando o risco sobe.

## Experiencia de interface

A tela principal da Carteira Recomendada deve mostrar a decisao de produto, nao a auditoria tecnica.

Regra de UX:

- Exibir `Carteira Recomendada Alpha`.
- Exibir ativo, setor, peso, papel na carteira, leitura Alpha, tese e pontos de acompanhamento.
- Nao exibir na visao principal termos internos como `dados parciais`, `bloqueios`, `dados insuficientes` ou tabelas de auditoria.
- A validacao tecnica continua existindo no backend para alimentar a leitura, mas nao deve dominar a experiencia visual do usuario.
- Detalhes tecnicos podem virar uma area futura de auditoria ou Centro Fundamentalista, separada da carteira recomendada.

## Dados historicos importados

A primeira versao do modulo foi normalizada a partir dos PDFs enviados pelo usuario em 2026-07-11:

- Avaliacao e recomendacoes da carteira de dividendos - julho de 2026.
- Sugestoes de pimenta para a carteira de dividendos - julho de 2026.
- Relatorio de backtest carteira de acoes versus renda fixa.
- Recomendacao de criptomoeda para investimento de alto potencial.

Os dados foram incorporados como modelo educacional estatico, backtest de referencia e insumo historico. Eles nao sao mais a origem da carteira principal exibida na tela.

## Carteira importada anterior

Carteira de dividendos perenes importada dos relatorios antigos:

- BBSE3: 15%.
- BBAS3: 15%.
- TAEE11: 10%.
- EGIE3: 10%.
- AURE3: 10%.
- CMIG4: 8%.
- CSMG3: 8%.
- BRSR6: 8%.
- CPLE6: 8%.
- BBDC4: 8%.

O total dos pesos permanece em 100% por compatibilidade historica, mas a carteira oficial atual e a `Carteira Recomendada Alpha oficial` gerada pelo Screener Alpha B3.

## Ativos pimenta

Ativos de maior risco cadastrados para estudo:

- PRNR3.
- TTEN3.

Regra de leitura: esses ativos sao classificados como "pimenta", nao como nucleo patrimonial.

## Backtest

O backtest importado compara:

- Carteira de acoes com dividendos reinvestidos.
- Renda fixa simulada a 1% ao mes.
- Periodo: 2025-01 a 2026-07.

Resultado importado:

- Carteira modelo: R$ 1.313,93.
- Renda fixa: R$ 1.208,11.
- Retorno da carteira modelo: 31,39%.
- Retorno da renda fixa: 20,81%.

Regra: resultado historico nunca deve ser exibido como promessa de resultado futuro.

## Cripto do mes

O bloco `Cripto do mes` passou a usar o `Screener Alpha Crypto`, com regra Binance-first e varredura mensal de oportunidades assimetricas.

Em julho de 2026, a candidata ativa e JASMY (JasmyCoin), substituindo PEPETO porque PEPETO falhou no criterio operacional de compra simples para o usuario.

A partir de 2026-07-12, o bloco ganhou o `Crypto Research Engine`.

Regra nova: o Screener Alpha Crypto encontra oportunidades, mas nao escolhe sozinho a candidata final. As melhores candidatas passam pelo `CryptoResearchEngine`, que valida narrativa, tokenomics, liquidez, supply, FDV, catalisadores, red flags e cenarios antes de marcar a cripto do mes.

Arquivo:

- `backend/app/services/crypto_research_engine.py`

Documento tecnico:

- `docs/CRYPTO_RESEARCH_ENGINE.md`

Regra principal:

- A candidata mensal precisa estar disponivel na Binance ou exchange grande equivalente.
- Preferir ativos com compra simples, liquidez real e sem necessidade de carteira externa, pre-venda ou fluxo operacional complexo.
- JASMY entra como estudo especulativo por estar disponivel via JASMY/USDT na Binance Spot, possuir preco unitario baixo e narrativa de IoT/soberania de dados.
- Quando nao houver par BRL direto no spot, o sistema deve deixar claro que a compra pode depender de conversao para USDT ou recurso equivalente da corretora.
- O motor procura oportunidade externa primeiro. A carteira atual do usuario entra depois, apenas para decidir se a melhor oportunidade do ranking e `nova_oportunidade` ou `reforcar_tese_existente`.
- O resultado e cacheado por mes e pode ser recalculado via rota de execucao manual.

Rotas:

- `GET /api/model-portfolios/crypto-screener`
- `POST /api/model-portfolios/crypto-screener/run`

O sistema deve sempre exibir:

- Risco extremo.
- Alocacao apenas simbolica e suportavel de perder.
- Alerta de que preco unitario baixo nao significa ativo barato.
- Alerta de que market cap e oferta total importam mais do que preco por token.

Criterios previstos para a varredura mensal:

- Disponibilidade em Binance ou exchange grande equivalente.
- Preco unitario baixo combinado com market cap compativel com assimetria.
- Liquidez minima para entrada e saida sem mercado travado.
- Tokenomics compreensivel.
- Utilidade, narrativa ou comunidade capazes de gerar demanda.
- Contrato, auditoria, rede, exchanges, holders e risco de golpe avaliados.
- Research qualitativo obrigatorio antes do destaque final.
- Cenarios defensivo, base e agressivo para deixar claro o intervalo de risco.

Fontes preparadas:

- Binance Spot: pares, status de negociacao e volume.
- CoinMarketCap: market cap, volume, preco e variacao quando houver API key.
- CoinGecko: fallback para market cap, volume, preco e variacao.

## Recommended Portfolio Engine institucional

Implementado em 2026-07-13.

Objetivo:

- Transformar a Carteira Recomendada Alpha em relatorio institucional mensal.
- Consolidar tese, risco, score, evidencias, governanca e revisao mensal.
- Separar nucleo Brasil, FIIs, global e cripto controlado.
- Exibir score institucional por ativo e da carteira consolidada.

Arquivos:

- `backend/app/services/recommended_portfolio_engine.py`
- `frontend/src/pages/ModelPortfolios.jsx`
- `docs/RECOMMENDED_PORTFOLIO_ENGINE.md`

Endpoints:

- `GET /api/model-portfolios/recommended-report`
- `POST /api/model-portfolios/recommended-report/run`

O payload principal `GET /api/model-portfolios` ganhou o campo aditivo `recommendedPortfolioReport`.

O relatorio contem:

- `institutionalScore`
- `classification`
- `riskLevel`
- `scoreBreakdown`
- `executiveSummary`
- `portfolios`
- `assetReports`
- `evidenceLedger`
- `riskMatrix`
- `monthlyReview`
- `governanceRules`
- `allowedLanguage`
- `blockedLanguage`

Regra de produto:

- A carteira pode ter tese forte e alta confianca analitica.
- Ela nunca pode ser comunicada como compra sem medo, retorno garantido ou ordem automatica.

## Evolucao futura

Proximas fases previstas:

- Integrar com Market Data Engine para atualizar preco, DY, fundamentals e liquidez.
- Criar status de validacao: importada, em analise, validada pelo Alpha, reprovada ou substituida.
- Persistir historico mensal de validacoes.
- Permitir substituicao automatica de ativos reprovados por candidatos melhores.
- Criar versionamento de carteiras modelo.
- Permitir comparacao contra a carteira real do usuario.
- Criar backtest real com dados historicos por ativo.
- Conectar ao Alpha Copilot para explicar diferencas entre modelo e carteira real.
- Adicionar filtros por perfil: dividendos, crescimento, equilibrado, conservador e cripto controlado.
