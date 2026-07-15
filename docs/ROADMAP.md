# Roadmap - Carteira Alpha 360

Status: plano mestre vivo.

## Diretriz maxima

O Roadmap deve seguir `docs/CONSTITUICAO_DO_PROJETO.md`. Cada fase precisa entregar valor real para a construcao de patrimonio de longo prazo, sem prometer rentabilidade, sem recomendacao direta de compra ou venda e sem criar atalhos que prejudiquem escalabilidade futura.

## Plano Mestre atualizado

Pilares oficiais:

1. Asset Engine Universal.
2. Market Data Engine.
3. Knowledge Engine.
4. Strategy Engine.
5. Global Portfolio Engine.
6. FX/Money Engine.
7. Alpha Score Mundial.
8. Wealth Builder.
9. Guardian.
10. Copilot.

## Production Readiness

Status: fundacao tecnica iniciada em 2026-07-13.

Entregue:

- Runtime Safety Gate para bloquear producao insegura.
- Endpoint `GET /api/ready`.
- Headers basicos de seguranca.
- Rate limit de login/cadastro em memoria.
- Template `.env.production.example`.
- Workflow CI para backend e frontend.
- Documento `docs/PRODUCTION_READINESS.md`.
- Logs estruturados JSON por request.
- Auditoria persistente em `audit_events`.
- Jobs operacionais com `job_runs`.
- Tela `Operacoes`.
- Scripts de backup/restore para SQLite e PostgreSQL/Supabase.
- Scripts de migracao SQLite -> PostgreSQL/Supabase, com backup, Alembic, dry-run e auditoria financeira pos-migracao.
- Dockerfiles backend/frontend e `docker-compose.prod.yml`.
- E2E smoke com Playwright.
- Documento `docs/PRODUCTION_OBSERVABILITY_AUDIT.md`.
- Jobs automaticos de Market Data, Carteira Recomendada, Macro/FX e Formula Audit.
- Auditoria matematica operacional das formulas financeiras centrais.
- Data Lineage & Evidence Ledger, com tabela `data_evidence_ledger`, endpoint operacional e evidencias para Market Data, Backtest, Financial Formula Auditor, Dashboard, CDI/RDB, Projecoes, Impostos, Stress Test, Strategy Engine, Recommended Portfolio Engine, Macro/FX e Copilot.

Proximas etapas obrigatorias:

- Rate limit distribuido com Redis.
- Refresh token, rotacao e revogacao de sessao.
- Monitoramento externo gerenciado, alertas e metricas historicas.
- Backup automatico agendado fora do processo da API e restore testado em ambiente separado.
- Testes de carga.
- Validacao externa independente de fontes de mercado e governanca de recomendacao.
- Expandir o Evidence Ledger para tabelas, graficos, linhas de ativo, secoes editoriais futuras e PDFs publicados.

## Alpha Premium Research

Status: Fase A/B/C/F/G tecnica em andamento desde 2026-07-14. Contratos, migrations aditivas, Publisher sem UI, Thesis Engine versionado, Rating Engine, Research Committee, Performance Attribution Engine, Publication Snapshot Engine, Publication Render Engine, Publication PDF Publisher, Premium Entitlements Engine, RBAC, Area Premium do Assinante, Payment Gateway, Distribution Engine com providers e Notification Center implementados.

Objetivo:

- Evoluir o Carteira Alpha 360 de Wealth OS patrimonial para tambem ser uma plataforma premium de research, carteira-modelo, publicacao editorial, newsletter, PDF/web e area de assinantes.
- Reutilizar engines existentes em vez de duplicar calculos.
- Garantir que nenhuma edicao premium seja publicada sem aprovacao humana explicita.
- Exigir Data Lineage para todo numero publicado.
- Criar historico auditavel do que foi publicado, quando, com quais dados, evidencias, decisoes e versao.

Entregue na Fase A:

- Contratos internos do Alpha Research Publisher em `backend/app/premium_research/contracts.py`.
- Modelos SQLAlchemy aditivos para publicacoes, versoes, secoes, ativos citados, fontes, evidencias, revisoes, aprovacoes e correcoes.
- Migration Alembic `20260714_0008_alpha_research_publisher`.
- Testes de fundacao e compatibilidade em `backend/tests/test_alpha_research_publisher_foundation.py`.
- Servico `AlphaResearchPublisher` sem UI em `backend/app/premium_research/publisher.py`.
- Testes do Publisher em `backend/tests/test_alpha_research_publisher_service.py`.
- Geracao de rascunho premium versionado com secoes, fontes, ativos citados, evidencias e readiness report.
- Thesis Engine versionado em `backend/app/premium_research/thesis_engine.py`.
- Migration Alembic `20260714_0009_asset_thesis_engine`.
- Testes do Thesis Engine em `backend/tests/test_asset_thesis_engine.py`.
- Integracao Publisher -> Thesis Engine para congelar teses dos ativos do relatorio premium.
- Rating Engine em `backend/app/premium_research/rating_engine.py`, calculado a partir de `asset_thesis_versions`.
- Migration Alembic `20260714_0010_asset_rating_engine`.
- Testes do Rating Engine em `backend/tests/test_asset_rating_engine.py`.
- Integracao Publisher -> Rating Engine para gerar rating versionado dos ativos do rascunho premium.
- Research Committee em `backend/app/premium_research/research_committee.py`, usando Thesis Engine, Rating Engine, Data Confidence, Guardian e Evidence Ledger como gates.
- Migration Alembic `20260714_0011_research_committee`.
- Testes do Research Committee em `backend/tests/test_research_committee.py`.
- Integracao Publisher -> Research Committee para registrar `researchCommittee` no payload interno da versao.
- API administrativa protegida `/api/premium` em `backend/app/routers/premium.py`.
- Testes da API premium em `backend/tests/test_premium_research_api.py`.
- Performance Attribution Engine em `backend/app/premium_research/performance_attribution.py`, com atribuicao por ativo, contribuidores, detratores, benchmark opcional, qualidade de dado e evidencias.
- Migration Alembic `20260714_0012_performance_attribution`.
- Rotas protegidas `POST /api/premium/publications/{publication_id}/attribution/run`, `GET /api/premium/attribution/runs` e `GET /api/premium/attribution/runs/{run_id}`.
- Publication Snapshot Engine em `backend/app/premium_research/snapshot_engine.py`, congelando edicoes aprovadas com payload canonico, manifest, hashes e evidencia no Data Evidence Ledger.
- Migration Alembic `20260714_0013_publication_snapshots`.
- Rotas protegidas `POST /api/premium/publications/{publication_id}/snapshots`, `GET /api/premium/publications/{publication_id}/snapshots`, `GET /api/premium/snapshots` e `GET /api/premium/snapshots/{snapshot_id}`.
- Publication Render Engine em `backend/app/premium_research/renderer.py`, gerando HTML premium reproduzivel a partir de snapshot aprovado.
- Migration Alembic `20260714_0014_publication_artifacts`.
- Rotas protegidas `POST /api/premium/snapshots/{snapshot_id}/render`, `GET /api/premium/publications/{publication_id}/artifacts`, `GET /api/premium/snapshots/{snapshot_id}/artifacts`, `GET /api/premium/artifacts` e `GET /api/premium/artifacts/{artifact_id}`.
- Publication PDF Publisher em `backend/app/premium_research/pdf_publisher.py`, gerando PDF binario a partir do HTML aprovado.
- Migration Alembic `20260714_0015_publication_pdf_artifacts`.
- Rotas protegidas `POST /api/premium/artifacts/{artifact_id}/pdf` e `GET /api/premium/artifacts/{artifact_id}/download`.
- Premium Entitlements Engine em `backend/app/premium_research/entitlements.py`, com planos, assinatura manual, entitlements e logs de acesso.
- Migration Alembic `20260714_0016_premium_entitlements`.
- Rotas protegidas `POST /api/premium/plans/seed`, `GET /api/premium/plans`, `POST /api/premium/subscriptions/grant`, `GET /api/premium/subscriptions/me` e `GET /api/premium/access-logs`.
- Download de PDF premium protegido por dono editorial ou entitlement ativo.
- Premium RBAC em `backend/app/services/rbac.py`, com papeis `admin`, `editor`, `reviewer`, `premium_subscriber` e `free_user`.
- Migration Alembic `20260714_0017_user_roles_rbac`, com backfill de usuarios existentes como `admin`.
- Rotas protegidas `GET /api/premium/rbac/me`, `POST /api/premium/rbac/roles/grant` e `GET /api/premium/subscriber/home`.
- Tela `Area Premium` para assinante consultar plano, permissoes, edicoes, PDFs e logs.
- Menu `Research Premium` filtrado por papel editorial.
- Payment Gateway em `backend/app/billing/gateway.py`, com checkout, transacoes, webhooks idempotentes, provider `mock` e ativacao de assinatura via Entitlements Engine.
- Migration Alembic `20260714_0018_billing_payment_gateway`.
- Rotas `POST /api/billing/checkout/sessions`, `POST /api/billing/mock/checkout/{session_id}/success`, `POST /api/billing/webhooks/{provider}`, `GET /api/billing/me` e `GET /api/billing/admin/webhook-events`.
- Area Premium passou a exibir planos pagos e botoes de assinatura mensal/anual.
- Distribution Engine em `backend/app/distribution/engine.py`, com campanhas, destinatarios, eventos, provider `mock` e selecao de assinantes por entitlement ativo.
- Migration Alembic `20260714_0019_distribution_engine`.
- Rotas `POST /api/distribution/campaigns`, `POST /api/distribution/campaigns/{campaign_id}/dispatch`, `GET /api/distribution/campaigns`, `GET /api/distribution/campaigns/{campaign_id}` e `POST /api/distribution/webhooks/{provider}`.
- Camada de providers em `backend/app/distribution/providers.py`, com `mock`, `resend`, `smtp` e fallback automatico para mock quando credenciais externas estiverem ausentes.
- Template institucional de email premium em `backend/app/distribution/templates.py`, gerando HTML, texto simples, preview, disclaimer e controle de integridade.
- Tela `Research Premium` passou a exibir campanhas e permitir disparo mock de edicoes aprovadas.
- Notification Center / Subscriber Delivery Inbox em `backend/app/distribution/inbox.py`, consolidando entregas, aberturas, cliques e downloads do assinante.
- Rota `GET /api/premium/subscriber/delivery-inbox` e campo `deliveryInbox` em `GET /api/premium/subscriber/home`.
- Tela `Area Premium` passou a exibir edicoes recebidas, pendentes, abertas, clicadas, baixadas e falhas.

Fases:

1. Arquitetura Editorial. Em andamento, base tecnica criada.
2. Thesis, Rating e Committee. Fundacao tecnica entregue sem UI.
3. Attribution e Fechamento.
4. Publisher.
5. PDF e Web.
6. Assinantes. Fundacao tecnica de entitlements, RBAC e area visual inicial entregue.
7. Distribuicao. Fundacao, providers e inbox do assinante entregues.
8. Compliance e Lancamento.

Proximas etapas:

- Criar tela administrativa futura de Committee Center.
- Criar tela administrativa futura para Performance Attribution e fechamento mensal.
- Criar tela administrativa futura para snapshots, artefatos renderizados e verificacao de integridade.
- Criar tela administrativa futura para baixar/validar PDF premium.
- Integrar gateway de pagamento real.
- Revisar juridicamente a linguagem de pesquisa, carteira-modelo e assinatura antes de venda real.
- Definir quais dados serao visiveis em cada plano: Free, Premium e Institutional.

## Alpha Wealth OS

Status: fundacao implementada em 2026-07-13.

Entregue:

- `Goal Engine` para metas patrimoniais.
- `Wealth Progress Score` para medir progresso de construcao de patrimonio.
- `Data Confidence Engine` para declarar qualidade dos dados usados.
- `Scenario & Stress Test Engine` para crise global, queda de bolsa, dolar alto, Selic alta, cripto despencando, corte de renda passiva, inflacao e liquidez seca.
- `Opportunity Engine` para estudos de oportunidade.
- `Economic Engine` como base para juros, inflacao e cambio.
- `Alpha Copilot` conversacional, com chat livre, citacoes de dados internos, provider de IA opcional e fallback deterministico seguro.
- `GET /api/wealth-os/*`.
- Bloco `Centro de Comando Patrimonial` na Visao Geral.
- `Event Engine 2.0` e `Guardian 2.0`, com fila unica de monitoramento em `/api/alerts`.
- `Research & News Engine` e `Evidence Center`, com endpoints `/api/wealth-os/research` e painel visual na Carteira Recomendada Alpha.
- `Macro / FX Engine` real via Banco Central SGS, com Selic, IPCA, USD/BRL, EUR/BRL, cache obrigatorio e fallback.
- `Tax Engine` inicial, com estimativa operacional de IRRF/JCP, ganho de capital em acoes, ganho de capital em FIIs, isencoes condicionais e lacunas fiscais controladas.
- `Strategy Engine 2.0`, com perfis de dividendos, crescimento, global, cripto controlado, aposentadoria, Barsi, Buffett, Bogle, Dalio e Lynch.
- Aba `Estrategias`, exibindo perfil dominante, aderencia, atual versus alvo, fatores, proximos estudos e encaixe de ativos.
- `Recommended Portfolio Engine` institucional, com relatorio mensal da Carteira Recomendada Alpha, score, tese, risco, evidencias, matriz de risco e checklist de revisao.
- `Total Return Engine`, separando valorizacao, aportes, dividendos, JCP e rendimentos cadastrados no livro interno.
- `Data Confidence Engine V2`, auditando fonte e qualidade dos dados por campo e reduzindo conviccao quando houver fallback.
- `Recommendation Governance Engine`, com reviewId, snapshot mensal, tese, risco, evidencias, gatilhos de revisao e persistencia em `user_preferences`.
- Aba `Stress Test`, exibindo score de resiliencia, pior cenario, impacto por classe, renda passiva antes/depois, premissas e acoes de acompanhamento.

Proximas etapas:

- Persistir metas personalizadas por usuario.
- Persistir perfil estrategico escolhido pelo usuario e historico mensal de aderencia.
- Persistir rodadas historicas de stress test por usuario e comparar resiliencia mes a mes.
- Tornar Event Engine 2.0 persistente para ciclos diarios.
- Integrar CVM fatos relevantes, B3 eventos corporativos e calendarios de resultados ao Research Engine.
- Expandir macro para Fintz, curvas de juros, indicadores globais e provedores alternativos de cambio.
- Evoluir Tax Engine com compensacao de prejuizos, day trade, cripto, EUA, withholding tax, IOF, DARF paga e relatorio anual.
- Expandir auditoria matematica para taxas internacionais, tributacao completa, cambio e total return com eventos corporativos.
- Tornar obrigatorio que todo card financeiro critico tenha link visual "ver origem do calculo".
- Persistir historico de conversas do Copilot por usuario, com trilha de dados e auditoria de respostas.

## Fase 1 - Refinamento Arquitetural antes da Taxonomia Global

Status: Etapa 1 tecnica iniciada e migration aditiva do Asset Engine implementada.

### Objetivo

Preparar a arquitetura para tratar qualquer investimento mundial como `Asset`, sem implementar telas e sem quebrar funcionalidades atuais.

### Arquivos afetados nesta etapa documental

- `docs/DOCUMENTACAO_TECNICA.md`
- `docs/CONSTITUICAO_DO_PROJETO.md`
- `docs/ARQUITETO_CHEFE.md`
- `docs/PRODUCT.md`
- `docs/MAPA_DO_SISTEMA.md`
- `docs/DIAGRAMA_ARQUITETURA.md`
- `docs/ROADMAP.md`
- `docs/ASSET_ENGINE.md`
- `docs/MARKET_DATA_ENGINE.md`
- `docs/KNOWLEDGE_ENGINE.md`
- `docs/STRATEGY_ENGINE.md`
- `docs/VISION_2035.md`
- `docs/MODEL_PORTFOLIOS.md`
- `CHANGELOG.md`

## Modulo Carteira Recomendada

Status: primeira versao implementada com Screener Alpha B3 e Carteira Recomendada Alpha oficial.

Objetivo:

- Trazer para dentro do Carteira Alpha 360 a experiencia de analise patrimonial que antes era feita em relatorios externos.
- Substituir a carteira principal importada por uma carteira oficial gerada pelo Screener Alpha B3.
- Separar carteira principal, ativos pimenta, backtest e cripto especulativa.
- Manter linguagem responsavel, sem recomendacao direta, sem promessa de rentabilidade e com alertas de risco.
- Validar ativos com criterios Alpha antes de tratar uma carteira importada como carteira validada.
- Exibir dados insuficientes quando os providers atuais nao entregarem fundamentos bastantes para uma conclusao independente.

Entregue em 2026-07-11:

- `backend/app/services/alpha_b3_screener.py`.
- Rotas `GET /api/model-portfolios/screener` e `POST /api/model-portfolios/screener/run`.
- `docs/SCREENER_ALPHA_B3.md`.
- Carteira Recomendada Alpha oficial inicial: BBSE3, TAEE11, ITSA4, BBAS3, EGIE3, CPFE3, SAPR11, PSSA3, VIVT3 e CSMG3.

Entregue em 2026-07-12:

- `backend/app/services/income.py`.
- `backend/app/services/alpha_fii_screener.py`.
- `backend/app/services/alpha_global_equity_screener.py`.
- `docs/PROVENTOS_ENGINE.md`.
- `docs/SCREENER_ALPHA_FIIS.md`.
- `docs/SCREENER_ALPHA_GLOBAL.md`.
- `backend/app/services/global_backtest.py`.
- `docs/GLOBAL_BACKTEST_ENGINE.md`.
- Fundacao de Proventos Engine: dividendos, JCP, rendimentos de FIIs e outras distribuicoes entram como renda passiva distribuida.
- Screener Alpha FIIs separado do Screener Alpha B3 de acoes, com carteira de estudo inicial e metodologia propria de renda imobiliaria.
- Screener Alpha Global separado do Screener Alpha B3, com watchlist internacional inicial por pais, regiao, moeda, setor, qualidade, liquidez e risco.
- Backtest internacional com cambio, dividendos internacionais e comparacao entre stock direto, BDR proxy e ETF global.
- `backend/app/services/crypto_research_engine.py`.
- `backend/app/services/alpha_confidence_engine.py`.
- `backend/app/services/recommended_portfolio_engine.py`.
- `docs/CRYPTO_RESEARCH_ENGINE.md`.
- `docs/ALPHA_CONFIDENCE_ENGINE.md`.
- `docs/RECOMMENDED_PORTFOLIO_ENGINE.md`.
- Camada de research apos o Screener Alpha Crypto, com tese, catalisadores, riscos, tokenomics, due diligence e cenarios para a cripto do mes.
- Aba `Alertas` conectada ao Alpha Intelligence: eventos importantes, insights e Guardian agora aparecem no monitoramento operacional.
- Alpha Confidence Engine conectado a `GET /api/model-portfolios`, gerando `confidenceReport` com nota geral, gates de confianca, leitura humana, regras nao negociaveis e confianca por ativo.
- Recommended Portfolio Engine conectado a `GET /api/model-portfolios`, gerando `recommendedPortfolioReport` e endpoint proprio `/api/model-portfolios/recommended-report`.

Evolucao futura:

- Evoluir `Screener Alpha B3` para persistir rodadas, historico de pesos e auditoria de fontes.
- Ampliar integracao Market Data Engine e Knowledge Engine para mais fontes de fundamentos, dividendos, historico e liquidez. Base multi-provider inicial entregue com BRAPI, FMP, Twelve Data, CoinMarketCap, CoinGecko, Banco Central, Dados de Mercado preparado e Fundamentus secundario.
- Criar backtest real por ativo.
- Evoluir backtest global com cambio historico real, imposto individual, spreads, taxas, IOF e comparacao por ativo especifico.
- Comparar carteira real do usuario contra carteiras modelo por perfil.
- Comparar execucao por stocks, BDRs, ETFs globais e corretoras internacionais.
- Persistir historico mensal da carteira recomendada e da cripto do mes.
- Evoluir o Crypto Research Engine com dados on-chain, unlocks, holders, auditoria de contrato e historico de teses.
- Persistir jobs do Guardian para varredura automatica agendada, historico de alertas e trilha de decisao por ativo.
- Persistir historico mensal de `confidenceReport`, com trilha de decisao por ativo e reducao automatica de confianca quando fontes ou dados ficarem fracos.

### Componentes novos propostos

- `AssetEngine`
- `MarketDataEngine`
- `KnowledgeEngine`
- `StrategyEngine`
- `GlobalPortfolioEngine`
- `FxMoneyEngine`
- `AlphaScoreWorldEngine`
- `WealthBuilder`
- `GuardianEngine`
- `CopilotService`

### Banco de dados proposto

Tabelas candidatas:

- `assets`
- `asset_identifiers`
- `asset_classifications`
- `asset_exposures`
- `market_providers`
- `market_data_cache`
- `market_data_observations`
- `fx_rates`
- `asset_facts`
- `asset_metrics`
- `asset_price_history`
- `asset_income_events`
- `corporate_events`
- `sector_datasets`
- `strategies`
- `strategy_rules`
- `strategy_assessments`
- `user_strategy_profiles`

### APIs necessarias futuramente

- `GET /api/assets/search`
- `GET /api/assets/{asset_id}`
- `POST /api/assets/resolve`
- `POST /api/market-data/sync`
- `GET /api/market-data/status`
- `GET /api/knowledge/assets/{asset_id}/metrics`
- `GET /api/wealth-os/strategies` entregue para Strategy Engine 2.0.
- Rotas futuras versionadas para persistir historico de estrategia e perfil do usuario.
- `GET /api/fx/rates`

As rotas atuais devem continuar funcionando durante a transicao.

### Migracoes

Toda implementacao posterior deve usar Alembic. A primeira fase tecnica deve ser aditiva:

- Adicionar colunas novas nullable ou com defaults seguros.
- Criar tabelas auxiliares.
- Backfill dos ativos atuais.
- So depois endurecer constraints.

### Dependencias

Nenhuma dependencia nova obrigatoria nesta etapa documental.

Dependencias possiveis futuras:

- Cliente HTTP ja existe via `httpx`.
- Jobs/agendamento podem exigir APScheduler, Celery, RQ ou servico equivalente.
- Cache pode comecar no banco e depois evoluir para Redis.

### Riscos

- Confundir tela especifica com modelo de dominio.
- Usar ticker como identificador universal.
- Quebrar carteira local existente ao migrar `Asset`.
- Criar acoplamento entre provider e score.
- Duplicar conceitos entre cripto e ativos tradicionais.
- Dificultar PostgreSQL futuro por atalhos do SQLite.
- Exibir dado parcial como se fosse dado completo.

### Criterios de aceite da Fase 1 documental

- Documentos arquiteturais criados.
- Plano Mestre atualizado com os 10 pilares.
- Modelo conceitual de dados definido.
- Tabelas propostas listadas.
- Riscos e impactos descritos.
- Ordem de implementacao definida.
- Nenhum arquivo de backend funcional, frontend ou banco alterado.

## Ordem exata de implementacao apos aprovacao

1. Concluido: criar migration Alembic aditiva para expandir `assets` e criar tabelas auxiliares minimas: `asset_identifiers`, `asset_classifications`, `asset_exposures`.
2. Concluido parcialmente: criar camada backend `app/engines` com helper inicial do Asset Engine.
3. Concluido: criar backfill dos ativos atuais para preencher subclasse, pais, mercado, bolsa, moedas e `universal_symbol`.
4. Concluido para criacao de ativos: adaptar services atuais para preencher Asset Engine sem alterar payload publico das rotas.
5. Concluido: criar `MarketDataEngine` com interface provider, normalizacao, cache em memoria e cache em banco.
6. Concluido parcialmente: adaptar BRAPI e mock ao contrato v2 sem remover providers antigos. CVM, B3 e CoinMarketCap seguem como proximas adaptacoes.
7. Concluido parcialmente: criar tabelas de Knowledge Engine para fatos, divergencias de metricas e eventos tecnicos de providers.
8. Concluido parcialmente: criar `FinancialProjectionEngine` como fonte unica de projecoes financeiras.
9. Fazer radares consumirem metricas tratadas do Knowledge Engine mantendo respostas atuais.
10. Criar Strategy Engine com estrategias iniciais e assessments sem alterar recomendacoes visuais.
11. Criar Centro Fundamentalista para auditoria de fundamentos e divergencias entre fontes.
12. Criar testes de migracao, carteira, resolucao de ativos e compatibilidade das rotas atuais.
13. Atualizar documentacao tecnica e changelog em cada etapa.

## Fases futuras

### Fase 2 - Taxonomia Global

Implementar modelo universal de ativos, identificadores e classificacoes globais.

### Fase 3 - Market Data Engine

Unificar providers, cache, fallback, normalizacao e observabilidade.

### Fase 4 - Knowledge Engine

Persistir fatos, metricas, eventos, historico e qualidade de dados.

### Fase 5 - Strategy Engine

Adicionar estrategias, regras, assessments e explicacoes.

### Fase 6 - Global Portfolio Engine

Consolidar carteira multi-moeda, multi-classe e multi-mercado.

### Fase 7 - FX/Money Engine

Implementar cambio, moeda base do usuario e conversoes historicas.

### Fase 8 - Alpha Score Mundial

Criar score comparavel globalmente por classe, estrategia e risco.

### Fase 9 - Wealth Builder e Guardian

Evoluir projecoes, metas, alertas e protecao patrimonial.

Base tecnica iniciada:

- `FinancialProjectionEngine` centraliza capital gain, renda passiva, retorno total, inflacao, independencia financeira e leitura inteligente.
- Proximas fases devem consumir este motor em vez de criar calculos novos no frontend.

### Fase 10 - Copilot

Status: primeira versao conversacional entregue em 2026-07-13.

Entregue:

- `GET /api/wealth-os/copilot/status`.
- `POST /api/wealth-os/copilot/chat`.
- Tela `Copilot`.
- Contexto interno com fontes numeradas.
- Provider de IA opcional no backend.
- Fallback deterministico seguro.

Proximas evolucoes:

- Persistir historico de conversas por usuario.
- Criar auditoria de respostas.
- Permitir follow-ups com memoria curta controlada.
- Expandir citacoes para Research & News, Knowledge Engine e dados historicos.

### Alpha Premium Research

Status: fundacao editorial tecnica em evolucao desde 2026-07-14.

Entregue:

- Alpha Research Publisher sem UI.
- Thesis Engine versionado.
- Rating Engine baseado em teses versionadas.
- Research Committee com gates, votos e bloqueios.
- API administrativa protegida `/api/premium`.
- Fluxo humano inicial de revisao e aprovacao final.
- Tela administrativa inicial `Research Premium`.
- Performance Attribution Engine mensal sem UI.
- Publication Snapshot Engine sem UI.
- Publication Render Engine sem UI.
- Publication PDF Publisher sem UI.
- Premium Entitlements Engine sem UI, com planos, assinatura manual, entitlements, logs de acesso e download de PDF protegido.

Proximas evolucoes:

- Area visual de assinantes.
- Gateway de pagamento real.
- RBAC editorial separado para admin, editor, revisor, assinante e leitor.
- Entrega por e-mail/newsletter e publicacao web controlada.
