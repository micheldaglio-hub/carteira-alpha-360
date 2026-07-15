# Carteira Alpha 360 - Documentacao Tecnica

Ultima atualizacao: 2026-07-13  
Status: documentacao viva do sistema

## Hierarquia documental

O documento `docs/CONSTITUICAO_DO_PROJETO.md` e a diretriz maxima do Carteira Alpha 360. Toda decisao tecnica, matematica, visual, funcional, de produto ou arquitetura deve ser compativel com ele.

Esta documentacao tecnica detalha a implementacao, mas nao substitui a Constituicao do Projeto.

## Regra obrigatoria de manutencao

Toda alteracao relevante no sistema deve atualizar este documento no mesmo ciclo de trabalho.

Atualize este arquivo sempre que houver mudanca em:

- Modelos de dados, tabelas, relacionamentos ou campos.
- Endpoints REST, payloads, autenticacao ou permissoes.
- Calculos de carteira, proventos, dividendos, JCP, rentabilidade, projecoes, rebalanceamento, scores, saude ou insights.
- Origem de dados, providers externos, mock de mercado, CVM, B3 ou Brapi.
- Regras de negocio, classificacoes, limites, pesos ou formulas.
- Estrutura visual, navegacao, tema, layout ou comportamento importante do frontend.
- Scripts de execucao, variaveis de ambiente, build, deploy ou banco de dados.

Ao alterar uma regra de calculo, documente:

1. O que mudou.
2. Qual arquivo foi alterado.
3. Qual dado de entrada a regra usa.
4. Qual dado de saida ela gera.
5. Qual impacto esperado para o usuario.

## Visao geral

O Carteira Alpha 360 e uma plataforma SaaS web para acompanhamento e analise de carteira de investimentos. O sistema cobre:

- Acoes, FIIs e ETFs.
- Renda fixa local, incluindo posicoes cadastradas como RDB, CDB, Tesouro ou classe `Renda fixa`.
- Compras, vendas, aportes e proventos.
- Dashboard financeiro.
- Radar de proventos.
- Radar de crescimento.
- Score proprietario de ativos.
- Backtest retroativo da carteira atual.
- Total Return Engine, separando retorno de preco, aportes e proventos/JCP/rendimentos cadastrados.
- Data Confidence Engine V2, auditando fonte e qualidade dos dados por campo: preco, historico, fundamentos, proventos, movimentacoes e divergencias.
- Data Lineage & Evidence Ledger, registrando fonte, provider, formula, versao, hash de insumos, confianca e status para numeros financeiros criticos.
- Recommendation Governance Engine, registrando review mensal, tese, risco, evidencia, status, proxima revisao e gatilhos extraordinarios da Carteira Recomendada Alpha.
- Backtest internacional com cambio, dividendos internacionais e comparacao entre stock direto, BDR proxy e ETF global.
- Projecao financeira.
- Rebalanceamento.
- Alertas.
- Carteira Recomendada, agora alimentada pelo Screener Alpha B3 para gerar a Carteira Recomendada Alpha oficial, pelo Screener Alpha FIIs para renda imobiliaria, pelo Screener Alpha Global para acoes internacionais e pelo Screener Alpha Crypto para cripto do mes.
- Recommended Portfolio Engine, com relatorio institucional mensal da Carteira Recomendada Alpha, tese, risco, score, evidencias e governanca de revisao.
- Proventos agora sao tratados como conceito central de renda passiva: dividendos, JCP, rendimentos de FIIs, REITs, juros, cupons e outras distribuicoes.
- Cripto do mes agora e alimentada pelo Screener Alpha Crypto com regra Binance-first, priorizando ativos de compra simples em exchange grande antes de considerar assimetria especulativa.
- Alpha Intelligence Engine, com eventos, timeline, saude da carteira, insights, Alpha Score 2.0 e camada Alpha Copilot preparada para IA.
- Alpha Wealth OS, com centro de comando patrimonial, metas, Wealth Progress Score, Scenario & Stress Test avancado, oportunidade em estudo, confiabilidade de dados, leitura economica e Alpha Copilot conversacional com IA opcional, contexto interno e citacoes.
- Research & News Engine, com centro de evidencias por ativo, fundamentos tratados, eventos, noticias via backend/cache, riscos, oportunidades e lacunas de dados.
- Macro / FX Engine real, com Selic, IPCA, USD/BRL e EUR/BRL via Banco Central SGS, cache obrigatorio e fallback para cache.
- Tax Engine, com estimativa operacional de IRRF, DARF, JCP, FIIs, ganho de capital e lacunas tributarias controladas.
- Strategy Engine 2.0, com perfis patrimoniais de dividendos, crescimento, global, cripto controlado, aposentadoria, Barsi, Buffett, Bogle, Dalio e Lynch.
- Production / Observability / Auditoria, com logs estruturados, auditoria persistente, jobs, tela operacional, backup/restore, Docker e E2E.
- PostgreSQL/Supabase migration, com Alembic controlado, `DATABASE_AUTO_CREATE_TABLES=false` em producao, backup local, dry-run, copia de dados por script e auditoria matematica apos migracao.
- Jobs automaticos de dados, com sincronizacao de ativos do usuario, revisao das carteiras recomendadas, refresh Macro/FX e auditoria financeira recorrente.
- Alpha Premium Research como vertical futura de research, carteira-modelo, edicao mensal, newsletter, PDF/web, assinatura, historico auditavel e publicacao com aprovacao humana.

## Atualizacao 2026-07-15 - Acesso LAN definitivo

Arquivos principais:

- `backend/app/core/config.py`
- `.env`
- `.env.example`
- `scripts/start-carteira-alpha.ps1`
- `scripts/check-lan-access.ps1`
- `scripts/ensure-lan-firewall.ps1`
- `CONFIGURAR_ACESSO_REDE_ADMIN.bat`
- `INICIAR_CARTEIRA_ALPHA_REDE.bat`
- `DIAGNOSTICAR_ACESSO_REDE.bat`
- `docs/ACESSO_REDE_LOCAL.md`

Decisao:

- O sistema ja subia backend e frontend em `0.0.0.0`, mas ainda havia tres pontos frageis para acesso por outro computador: firewall do Windows, CORS por nome da maquina e diagnostico insuficiente quando ha dois roteadores.
- O backend passou a aceitar, em desenvolvimento, origens por hostname local simples, `.local`, localhost e faixas privadas IPv4.
- O Vite ja estava configurado com `allowedHosts: true` e `host: 0.0.0.0`.
- O frontend continua sem `VITE_API_URL` por padrao, resolvendo automaticamente a API como `http://HOST_ATUAL:8000/api`.

Regras:

- `CONFIGURAR_ACESSO_REDE_ADMIN.bat` abre UAC e cria regras no Firewall para `5173` e `8000`.
- As regras usam `RemoteAddress LocalSubnet`, limitando o acesso a dispositivos da rede local.
- `INICIAR_CARTEIRA_ALPHA_REDE.bat` sobe o sistema e mostra as URLs atuais.
- `DIAGNOSTICAR_ACESSO_REDE.bat` grava `logs/carteira-alpha-lan-diagnostic.txt`.
- `scripts/start-carteira-alpha.ps1` chama o diagnostico em modo silencioso e atualiza `logs/carteira-alpha-urls.txt`.

Limite externo:

- Se outro Wi-Fi da casa estiver atras de um segundo roteador em sub-rede diferente ou com isolamento de clientes, o PC pode estar correto e ainda assim o outro dispositivo nao acessa. Nesse caso, a solucao e configurar o segundo roteador como Bridge/AP ou liberar comunicacao entre sub-redes.

## Atualização 2026-07-15 - Integração online Vercel -> Render

Arquivos principais:

- `frontend/src/lib/api.js`
- `frontend/.env.example`

Decisão:

- O frontend aceita `VITE_API_URL` como origem do backend, por exemplo `https://carteira-alpha-360.onrender.com`.
- O prefixo `/api` é adicionado automaticamente por `buildApiUrl`.
- Se algum endpoint for chamado já com `/api`, o helper remove o prefixo duplicado antes de montar a URL final.
- A regra preserva o funcionamento local e corrige produção, onde a chamada antiga para `/auth/register` retornava `404`.

Critério técnico:

- `buildApiUrl("/auth/register", "https://carteira-alpha-360.onrender.com")` gera `https://carteira-alpha-360.onrender.com/api/auth/register`.
- `buildApiUrl("/api/auth/me", "https://carteira-alpha-360.onrender.com")` gera `https://carteira-alpha-360.onrender.com/api/auth/me`.

## Atualizacao 2026-07-15 - Login sem scroll inicial

Arquivos principais:

- `frontend/src/pages/Login.jsx`
- `frontend/src/styles/index.css`
- `frontend/tests/e2e/app-smoke.spec.js`

Decisao:

- A landing institucional de login foi compactada para caber na primeira dobra em notebooks e desktops com altura reduzida.
- O ajuste usa media queries por altura (`max-height`) e largura, preservando a identidade visual preta/dourada e a imagem de fundo.
- Em telas baixas, metricas demonstrativas e texto secundario sao ocultados para priorizar headline, formulario e acesso.
- Inputs, tabs, botao, card e margens passam a usar dimensoes menores apenas nesses viewports compactos.
- Em mobile, o hero tambem e reduzido para evitar scroll inicial excessivo.
- Autenticacao, rotas, payloads, token, seguranca e backend nao foram alterados.

Validacao visual:

- `1366x768`: `scrollHeight` igual ao `innerHeight`.
- `1366x720`: `scrollHeight` igual ao `innerHeight`.
- `1280x720`: `scrollHeight` igual ao `innerHeight`.
- `390x844`: `scrollHeight` igual ao `innerHeight`.

## Atualizacao 2026-07-15 - Revisao ortografica da UI

Arquivos principais:

- `frontend/src/pages/Login.jsx`
- `frontend/src/components/Sidebar.jsx`
- `frontend/src/components/StatCard.jsx`
- `frontend/src/pages/Dashboard.jsx`
- `frontend/src/pages/Portfolio.jsx`
- `frontend/src/pages/Projections.jsx`
- `frontend/src/pages/Crypto.jsx`
- `frontend/src/pages/Radar.jsx`
- `frontend/src/pages/StressTest.jsx`
- `frontend/src/pages/ModelPortfolios.jsx`
- `frontend/src/pages/PremiumResearch.jsx`
- `frontend/src/pages/PremiumSubscriber.jsx`
- `frontend/src/pages/Copilot.jsx`
- `frontend/src/pages/Alerts.jsx`

Decisao:

- Textos visiveis do frontend foram revisados para uso correto de acentos em portugues.
- Exemplos corrigidos: `patrimônio`, `decisões`, `evidências`, `confiança`, `projeções`, `ações`, `segurança`, `usuário`, `relatório`, `comitê`, `edição` e `não`.
- Chaves internas como `patrimonio` e valores tecnicos de payload como `asset_class: "Acoes"` foram preservados para nao quebrar compatibilidade de dados.
- Build e E2E passaram apos a revisao.

## Atualização 2026-07-15 - Fórmula única de rentabilidade mensal de ações

Arquivos principais:

- `backend/app/services/portfolio.py`
- `backend/app/services/portfolio_backtest.py`
- `backend/tests/test_portfolio_summary.py`
- `frontend/src/pages/Portfolio.jsx`

Decisão:

- O card superior `Rent. ações no mês` e o gráfico `Retorno mês a mês` do backtest passam a usar a mesma janela de cálculo.
- A base mensal é o primeiro preço disponível a partir do fechamento/marcação do último dia do mês anterior.
- O preço final é o preço atual do ativo no sistema.
- Fórmula: `(valor atual das ações / valor base das ações - 1) * 100`.
- A regra evita divergências visuais entre o card superior e a barra do mês atual no backtest.

Impacto esperado:

- Quando o backtest estiver filtrado até a data atual e a visão selecionada for `Ações`, o retorno do mês exibido no tooltip deve bater com o card superior de rentabilidade mensal das ações.
- Se o usuário selecionar uma data final antiga no backtest, o gráfico mostrará o retorno até aquela data histórica, enquanto o card superior continua mostrando o mês corrente até hoje.

## Atualizacao 2026-07-15 - Polimento final da landing institucional de login

Arquivos principais:

- `frontend/src/pages/Login.jsx`
- `frontend/src/styles/index.css`
- `frontend/tests/e2e/app-smoke.spec.js`
- `docs/DESIGN_SYSTEM.md`

Decisao:

- A imagem de fundo institucional foi preservada sem troca.
- A evolucao desta fase focou em hierarquia, proporcao, tipografia, glassmorphism, movimento e legibilidade.
- A autenticacao continua intacta: nao houve alteracao de backend, rotas, APIs, payloads, validacoes, token ou seguranca.

Mudancas:

- Card de login reduzido no desktop por meio de novo grid `minmax(21rem, 25rem)`, menor padding e reposicionamento controlado.
- Marca principal ampliada e assinatura `Institutional Wealth Intelligence` adicionada apenas no hero para evitar repeticao excessiva.
- Headline final: `Construa patrimonio. Tome decisoes melhores.`
- Pseudo-botoes decorativos foram removidos e substituidos por indicadores demonstrativos leves:
  - `32` teses versionadas;
  - `493` evidencias rastreaveis;
  - `74/100` confianca dos dados.
- Overlays foram refinados para revelar mais mapa, linhas douradas e grafico no centro/direita, mantendo contraste atras do texto e formulario.
- Card recebeu vidro institucional mais sutil: fundo escuro translucido, blur mais forte, borda fina, highlight superior e brilho interno leve.
- Botao principal recebeu gradiente dourado, brilho discreto, hover, focus, active e animacao leve por background-position.
- CSS respeita `prefers-reduced-motion` e desativa animacoes de hero/card/botao.
- `frontend/index.html` recebeu meta description para SEO.
- Validacao Lighthouse em build de producao via `vite preview`: Performance 95, Accessibility 100, Best Practices 96, SEO 91.

Responsividade:

- Desktop: hero e card lado a lado, card menor e fundo com mais presenca.
- Tablet: layout em coluna, card com largura controlada e imagem preservada.
- Mobile: indicadores e textos secundarios sao ocultos para foco em headline curta e formulario completo.

## Atualizacao 2026-07-15 - Nova landing institucional de login

Arquivos principais:

- `frontend/src/pages/Login.jsx`
- `frontend/src/styles/index.css`
- `frontend/index.html`
- `frontend/public/assets/alpha-login-background.png`
- `frontend/public/assets/alpha-login-background.webp`
- `frontend/tests/e2e/app-smoke.spec.js`

Decisao:

- A tela de login deixou de ser um painel demonstrativo e passou a ser uma landing institucional full-screen.
- A imagem aprovada do Alpha 360 e usada como fundo principal via `picture`, com WebP prioritario e PNG como fallback.
- `frontend/index.html` faz preload de `/assets/alpha-login-background.webp`.
- A autenticacao continua intacta: `onLogin({ email, password })` e `onRegister({ email, full_name, password })` continuam sendo os unicos pontos de chamada para as rotas existentes.
- Nenhuma API, rota, payload, validacao de senha, token, hash ou regra de seguranca foi alterada.

Composicao visual:

- Fundo full-screen com `object-fit: cover`, overlays escuros, gradiente lateral e vinheta para legibilidade.
- Card de login translucido com `backdrop-filter`, borda sutil, sombra profunda e foco visual no formulario.
- Hero institucional com marca, promessa principal e beneficio de produto.
- O fundo preserva mapa mundial, graficos, linhas douradas e leitura de inteligencia patrimonial.
- Dados visuais do fundo sao identificados como demonstrativos.

Acessibilidade e responsividade:

- Tabs de Login/Cadastro usam `role="tablist"` e `role="tab"`.
- Inputs possuem labels reais, `autocomplete`, `aria-invalid`, `aria-describedby` em erro e foco visivel.
- Botao de mostrar/ocultar senha usa `aria-label`.
- Mensagens de erro/sucesso usam `role="alert"` ou `role="status"`.
- CSS respeita `prefers-reduced-motion`.
- Layout cobre desktop, tablet e mobile sem scroll horizontal.

## Atualizacao 2026-07-15 - Login premium institucional

Arquivo principal:

- `frontend/src/pages/Login.jsx`

Testes:

- `frontend/tests/e2e/app-smoke.spec.js`

Decisao:

- A tela de login/cadastro foi refinada para o mesmo padrao premium institucional do restante do Carteira Alpha 360.
- A autenticacao nao foi alterada: os callbacks `onLogin({ email, password })` e `onRegister({ email, full_name, password })` continuam chamando as mesmas rotas configuradas em `frontend/src/App.jsx`.
- Nao houve mudanca em backend, rotas, payloads, token, hash de senha, permissoes ou regra de seguranca.

Mudancas visuais e de experiencia:

- Conjunto central ampliado e layout aproximando card de autenticacao e painel demonstrativo.
- Promessa de produto substituida por texto claro de valor: organizar, acompanhar e interpretar patrimonio em uma unica plataforma.
- Painel direito exibe dados demonstrativos identificados como demonstracao: patrimonio consolidado, renda anual, Score Alpha, risco, grafico e progresso de meta patrimonial.
- Adicionados controles visuais de `Esqueci minha senha`, mostrar/ocultar senha e `Manter conectado`.
- Estados locais de loading, sucesso e erro foram adicionados no frontend sem alterar logica de negocio.
- Inputs receberam labels, autocomplete, `aria-invalid`, foco visivel e botoes com `aria-label`.
- Aviso legal foi compactado e a indicacao de seguranca foi adicionada: acesso protegido, dados isolados por usuario e trilha de auditoria.
- O layout preserva tokens CSS de tema escuro/claro definidos em `frontend/src/styles/index.css`.

## Atualizacao 2026-07-14 - Alpha Research Publisher Fase A

Documento principal: `docs/ALPHA_PREMIUM_RESEARCH.md`.

Arquivos criados:

- `backend/app/premium_research/__init__.py`
- `backend/app/premium_research/contracts.py`
- `backend/alembic/versions/20260714_0008_alpha_research_publisher.py`
- `backend/tests/test_alpha_research_publisher_foundation.py`

Arquivos alterados:

- `backend/app/models.py`
- `docs/ALPHA_PREMIUM_RESEARCH.md`
- `docs/DOCUMENTACAO_TECNICA.md`
- `docs/ROADMAP.md`
- `docs/MAPA_DO_SISTEMA.md`
- `docs/DIAGRAMA_ARQUITETURA.md`
- `CHANGELOG.md`

Decisao:

- A Fase A tecnica do Alpha Premium Research foi iniciada com contratos e banco aditivos.
- Nenhuma tela, rota publica, payload existente, regra financeira, calculo ou recomendacao foi alterado.
- A base criada serve para versionar futuras edicoes premium, fontes, evidencias, secoes, revisoes, aprovacoes e correcoes.

Contratos:

- `PublicationSourceContract`
- `PublicationEvidenceContract`
- `PublicationSectionContract`
- `PublicationVersionContract`
- `ResearchPublicationContract`
- `PublicationQualityGate`
- `PublicationReadinessReport`

Regras de contrato:

- Estados de publicacao sao explicitos: `created`, `collecting_data`, `processing`, `draft`, `data_pending`, `in_review`, `reviewed`, `approved`, `published`, `corrected`, `archived` e `cancelled`.
- Transicoes sao validadas por `can_transition_publication`.
- Estados terminais sao reconhecidos por `is_terminal_publication_status`.
- Readiness e classificado por `classify_publication_readiness`.

Tabelas criadas pela migration `20260714_0008`:

- `research_publications`
- `publication_versions`
- `publication_sections`
- `publication_assets`
- `publication_sources`
- `publication_evidence`
- `publication_reviews`
- `publication_approvals`
- `publication_corrections`

Rollback:

- O downgrade remove indices e tabelas em ordem reversa, preservando as tabelas antigas do sistema.

Compatibilidade:

- A migration e aditiva.
- As tabelas antigas nao foram removidas nem alteradas.
- Rotas atuais continuam com os mesmos payloads.
- O app permanece no head Alembic `20260714_0008`.

## Atualizacao 2026-07-14 - AlphaResearchPublisher sem UI

Arquivo principal:

- `backend/app/premium_research/publisher.py`

Testes:

- `backend/tests/test_alpha_research_publisher_service.py`

Objetivo:

- Criar o primeiro servico operacional da vertical premium sem alterar interface, rotas publicas, calculos financeiros ou payloads existentes.
- Transformar dados internos ja produzidos pelo sistema em um rascunho editorial versionado.
- Persistir secoes, fontes, ativos citados, evidencias e readiness report usando as tabelas criadas na migration `20260714_0008`.

Fluxo:

```text
get_model_portfolios
-> recommendedPortfolioReport
-> recommendationGovernance
-> Data Evidence Ledger
-> AlphaResearchPublisher
-> research_publications
-> publication_versions
-> publication_sections
-> publication_sources
-> publication_assets
-> publication_evidence
```

Regras:

- O Publisher nao recalcula carteira recomendada, score, risco, governanca ou confianca. Ele consome os motores internos existentes.
- Cada rascunho recebe uma versao propria. Se ja existir `v0.1` para o mesmo periodo, o proximo rascunho vira `v0.2`, preservando historico.
- O readiness report mede secoes, fontes, evidencias, ativos citados, confianca, score institucional, Data Confidence e pendencia de revisao humana.
- Mesmo com readiness alto, o rascunho nao pode ser publicado automaticamente.
- A revisao humana continua obrigatoria antes de qualquer PDF, web, newsletter ou distribuicao premium.

Saidas persistidas:

- Publicacao em `research_publications`.
- Versao em `publication_versions`.
- Secoes editoriais em `publication_sections`.
- Fontes internas em `publication_sources`.
- Ativos citados em `publication_assets`.
- Evidencias vinculadas ao `data_evidence_ledger` em `publication_evidence`.

Compatibilidade:

- Nenhuma rota publica nova foi criada nesta etapa.
- Nenhuma tela foi alterada.
- Nenhum payload atual foi alterado.
- Nenhuma regra financeira foi alterada.

## Atualizacao 2026-07-13 - Alpha Premium Research

Documento principal: `docs/ALPHA_PREMIUM_RESEARCH.md`.

Decisao:

- Alpha Premium Research passa a ser uma vertical futura oficial do Carteira Alpha 360.
- A vertical reutiliza os engines existentes: Wealth OS, Recommended Portfolio Engine, Research & News Engine, Data Confidence, Data Lineage, Total Return, Macro/FX, Tax, Stress Test, Strategy e Copilot.
- Ela nao deve duplicar calculos no frontend nem gerar newsletter a partir de captura de tela.
- Nenhuma publicacao premium pode ser publicada automaticamente sem aprovacao humana explicita.
- Todo numero publicado deve ter Data Lineage minimo.
- Toda tese deve ser versionada, nunca sobrescrita silenciosamente.
- Toda edicao publicada deve preservar versao, hash, evidencias, fontes, status, revisoes, aprovacao e changelog.
- A fase atual e documental e arquitetural. Nao cria tabelas, rotas, telas, PDF, cobranca ou publicacao.

Modulos futuros:

- Alpha Research Publisher.
- Thesis Engine.
- Revision Engine.
- Rating Engine.
- Alpha Research Committee.
- Portfolio Constructor.
- Performance Attribution Engine.
- Editorial AI Engine.
- PDF / Web Publisher.
- Subscription & Entitlements.
- Compliance & Disclosure.

Ordem de implementacao futura:

1. Contratos e migrations aditivas.
2. Publisher sem UI.
3. Thesis Engine versionado.
4. Rating Engine com formulas documentadas.
5. Research Committee com gates.
6. Publication Readiness Score.
7. Endpoints administrativos protegidos.
8. Tela administrativa.
9. Attribution e snapshot mensal.
10. Editorial AI apenas para rascunho.
11. PDF/HTML estruturado.
12. Entitlements e area premium.
13. Distribuicao.
14. Compliance e piloto antes de venda real.

## Atualizacao 2026-07-13 - Total Return, Data Confidence e Governanca

### Total Return Engine

Arquivo principal: `backend/app/services/total_return_engine.py`.

O backtest da carteira atual continua calculando retorno de preco por classe, mas agora recebe uma camada adicional de `Total Return`. Essa camada soma dividendos, JCP e rendimentos de FIIs cadastrados na tabela interna `dividends`.

Regra:

```text
retorno_total_mes = retorno_preco_mes + (proventos_do_mes / base_de_performance_do_mes)
retorno_total_acumulado = produto(1 + retorno_total_mes) - 1
```

Aporte mensal nao entra como lucro. Aporte aumenta patrimonio, mas a performance percentual e calculada por retorno encadeado.

### Data Confidence Engine V2

Arquivo principal: `backend/app/services/data_confidence_engine.py`.

Cada ativo da carteira recebe auditoria de:

- preco atual;
- historico de precos;
- fundamentos;
- proventos/JCP;
- movimentacoes;
- divergencias entre fontes.

O payload do backtest passou a incluir `dataConfidence`, com `overallScore`, classificacao, quantidade de ativos auditados, quantidade com fallback e auditoria campo a campo.

### Recommendation Governance Engine

Arquivo principal: `backend/app/services/recommendation_governance_engine.py`.

A Carteira Recomendada Alpha passou a gerar `recommendationGovernance`, contendo:

- `reviewId`;
- mes do relatorio;
- proxima revisao;
- score institucional;
- confianca Alpha;
- confianca dos dados do usuario;
- revisao por ativo;
- tese, risco, evidencias e monitoramento;
- gatilhos extraordinarios de revisao.

Quando existe usuario autenticado, o snapshot e gravado em `user_preferences` com as chaves `recommendation_governance:latest` e `recommendation_governance:YYYY-MM`.

### Backtest mensal

O calculo mensal do backtest foi corrigido para usar o checkpoint anterior como base de comparacao. Isso evita distorcoes em meses intermediarios e alinha o grafico de retorno mensal com os cards superiores.

O sistema nao promete rentabilidade e nao emite recomendacao direta de compra ou venda. A linguagem correta e analitica: ativo atrativo, ativo caro, ativo descontado, atencao ao risco, bom para dividendos, bom para crescimento ou fora dos criterios.

## Atualizacao 2026-07-13 - PostgreSQL, Jobs e Auditoria Financeira

### Migração PostgreSQL/Supabase

Arquivos:

- `scripts/migrate-to-supabase.ps1`
- `scripts/migrate_sqlite_to_postgres.py`
- `.env.supabase.example`

O sistema passa a ter um caminho operacional para migrar dados do SQLite local para PostgreSQL/Supabase. O schema e criado por Alembic, e em producao `DATABASE_AUTO_CREATE_TABLES` deve ser `false`.

O fluxo padrao faz backup do SQLite antes da migracao, bloqueia connection string com senha placeholder e roda dry-run antes de copiar dados. A copia real exige `-Apply`; limpeza do destino exige `-Truncate`.

### Jobs automaticos de dados

Arquivo principal:

- `backend/app/services/job_runner.py`

Novos jobs:

- `market_data.user_assets`: sincroniza fundamentos e precos dos ativos da carteira.
- `market_data.model_portfolios`: recalcula Screener Alpha, Carteira Recomendada e governanca.
- `macro_fx.refresh`: atualiza Selic, IPCA e cambio.
- `financial.formula_audit`: roda auditoria matematica das formulas centrais.

Todos os jobs registram execucao em `job_runs` e eventos relevantes em `audit_events`.

### Auditoria real das formulas financeiras

Arquivo:

- `backend/app/services/financial_formula_auditor.py`

A auditoria valida cenarios deterministicos de renda passiva, aportes, CDI diario, backtest sem distorcao por aporte e valor real com inflacao.

Se o job `financial.formula_audit` falhar, a execucao fica registrada como erro e deve bloquear deploy ate correcao.

## Atualizacao 2026-07-13 - Data Lineage & Evidence Ledger

Arquivo principal:

- `backend/app/services/data_lineage.py`

Tabela:

- `data_evidence_ledger`

Migration:

- `backend/alembic/versions/20260713_0007_data_evidence_ledger.py`

Endpoint:

- `GET /api/ops/evidence`

Objetivo:

Registrar evidencias de dados e formulas para permitir auditoria por campo. Cada evidencia pode guardar usuario, ativo, dominio, campo, valor, provider, tipo de fonte, formula, versao, hash dos insumos, confianca, qualidade, status e metadados.

Integracoes iniciais:

- `Market Data Engine`: registra evidencias de preco e fundamentos quando sincroniza ativos.
- `Portfolio Backtest`: registra evidencias dos principais campos de retorno e patrimonio.
- `Financial Formula Auditor`: registra evidencia do score e de cada caso matematico auditado.

Regra:

Todo numero financeiro critico novo deve registrar evidencia no ledger. Fallback nao e proibido, mas precisa aparecer como `source_type=fallback` e reduzir confianca.

## Auditoria de Confiabilidade Financeira

Implementada em 2026-07-13 para corrigir divergencias entre Dashboard, Strategy Engine, Stress Test, Guardian e Copilot.

Arquivos principais:

- `backend/app/services/asset_taxonomy.py`
- `backend/app/services/portfolio_aggregation.py`
- `backend/tests/test_financial_reliability_invariants.py`

Regras implementadas:

- Todo ativo passa pela taxonomia unica antes de ser usado em alocacao, strategy, stress ou Copilot.
- Classes canonicas suportadas: `Acoes Brasil`, `FIIs`, `ETFs Brasil`, `Renda Fixa Brasil`, `Caixa`, `Acoes Internacionais`, `ETFs Internacionais`, `REITs`, `Cripto`, `Trading`, `Commodities` e `Outros`.
- RDB, CDB, Tesouro e ativos com CDI sao sempre `Renda Fixa Brasil`, nunca `Acoes Brasil`, `Global` ou proventos de dividendos.
- Cripto nao entra como renda passiva tradicional.
- Trading Desk EV+ entra como `Trading` e nao deve ser contado duas vezes.
- O `Portfolio Aggregation Engine` gera a fotografia unica da carteira com totais, P/L, alocacao por classe, bucket estrategico, pais, regiao, moeda, setor e ativo.
- Dashboard, Strategy Engine, Stress Test e Copilot passam a consumir ou citar essa fotografia unica.
- Confidence Gates agora aplicam tetos: cobertura de dados abaixo de 80 limita confianca a 69; controle de risco abaixo de 60 impede leitura institucional forte; uso relevante de fallback deixa o relatorio provisional.

Invariantes testadas:

- Soma de classes deve fechar no patrimonio atual.
- Pesos por classe devem somar aproximadamente 100%.
- `P/L = valor atual - valor investido`, incluindo integracoes externas sem dupla contagem.
- RDB/CDI nao pode virar acao, global ou dividend yield.
- Stress Test aplica choque conforme classe canonica.
- Strategy Engine usa bucket estrategico derivado da taxonomia unica.

## Alpha Wealth OS

Implementado em 2026-07-13 como camada de orquestracao patrimonial.

Arquivos principais:

- `backend/app/wealth_os/contracts.py`
- `backend/app/wealth_os/service.py`
- `backend/app/wealth_os/goal_engine.py`
- `backend/app/wealth_os/wealth_progress_engine.py`
- `backend/app/wealth_os/data_confidence_engine.py`
- `backend/app/wealth_os/scenario_engine.py`
- `backend/app/wealth_os/opportunity_engine.py`
- `backend/app/wealth_os/economic_engine.py`
- `backend/app/wealth_os/macro_fx_engine.py`
- `backend/app/wealth_os/tax_engine.py`
- `backend/app/wealth_os/strategy_engine.py`
- `backend/app/wealth_os/copilot_service.py`
- `backend/app/wealth_os/research_news_engine.py`
- `backend/app/routers/wealth_os.py`
- `frontend/src/pages/Dashboard.jsx`
- `frontend/src/pages/Tax.jsx`
- `frontend/src/pages/Strategies.jsx`
- `frontend/src/pages/StressTest.jsx`
- `frontend/src/pages/Copilot.jsx`
- `frontend/src/pages/ModelPortfolios.jsx`

Endpoints aditivos:

- `GET /api/wealth-os`
- `GET /api/wealth-os/command-center`
- `GET /api/wealth-os/goals`
- `GET /api/wealth-os/score`
- `GET /api/wealth-os/scenarios`
- `GET /api/wealth-os/stress-test`
- `GET /api/wealth-os/opportunities`
- `GET /api/wealth-os/economic`
- `GET /api/wealth-os/macro-fx`
- `GET /api/wealth-os/fx`
- `GET /api/wealth-os/tax`
- `GET /api/wealth-os/strategies`
- `GET /api/wealth-os/data-confidence`
- `GET /api/wealth-os/copilot/questions`
- `GET /api/wealth-os/copilot/answer/{question_id}`
- `GET /api/wealth-os/copilot/status`
- `POST /api/wealth-os/copilot/chat`
- `GET /api/wealth-os/research`
- `GET /api/wealth-os/research/{ticker}`

Motores:

- Goal Engine: calcula metas patrimoniais e tempo estimado usando patrimonio atual, premissas salvas e formulas financeiras documentadas.
- Wealth Progress Score: mede progresso patrimonial por meta, diversificacao, concentracao, renda passiva, Saude Alpha e momento da carteira.
- Data Confidence Engine: declara confianca dos dados de posicoes, precos, setores, proventos e macro/fiscal.
- Scenario & Stress Test Engine: simula crise global, queda de bolsa, dolar alto, Selic alta, cripto despencando, corte de renda passiva, inflacao e liquidez seca, calculando impacto por classe, impacto em renda passiva, pior cenario e score de resiliencia.
- Opportunity Engine: gera estudos de oportunidade e pontos de acompanhamento sem ordem automatica de compra ou venda.
- Economic Engine: interpreta juros, inflacao e cambio usando o Macro / FX Engine.
- Macro / FX Engine: busca Selic, IPCA e cambio no Banco Central SGS, normaliza, grava cache e retorna fallback quando a fonte falha.
- Tax Engine: estima eventos tributarios de acoes, FIIs, JCP e proventos, separando IRRF, DARF, renda liquida e lacunas de apuracao.
- Strategy Engine 2.0: compara a carteira com perfis patrimoniais, calcula aderencia, desalinhamentos, fatores e encaixe de ativos sem emitir ordem de compra ou venda.
- Alpha Copilot: responde perguntas estruturadas e chat livre com dados internos, citacoes, nivel de confianca, fallback seguro e provider de IA opcional no backend.
- Event Engine 2.0: unifica alertas manuais, eventos Alpha, insights e Guardian em uma fila unica.
- Guardian 2.0: monitora saude, concentracao, metas, ativos em revisao, confianca dos dados e Wealth Score.
- Research & News Engine: consolida evidencias internas, fundamentos tratados e noticias externas quando provider estiver configurado.

Documentacao especifica:

- `docs/WEALTH_OS.md`
- `docs/GOAL_ENGINE.md`
- `docs/WEALTH_PROGRESS_SCORE.md`
- `docs/SCENARIO_ENGINE.md`
- `docs/OPPORTUNITY_ENGINE.md`
- `docs/ECONOMIC_ENGINE.md`
- `docs/MACRO_FX_ENGINE.md`
- `docs/TAX_ENGINE.md`
- `docs/STRATEGY_ENGINE.md`
- `docs/DATA_CONFIDENCE.md`
- `docs/ALPHA_COPILOT.md`
- `docs/EVENT_ENGINE_V2.md`
- `docs/GUARDIAN_2.md`
- `docs/RESEARCH_NEWS_ENGINE.md`
- `docs/EVIDENCE_CENTER.md`

Regra: nenhuma regra financeira ou estrategica nova fica no React. A interface consome payloads prontos do backend.

## Renda fixa e CDI

Desde 2026-07-13, posicoes cadastradas como `Renda fixa`, `RDB`, `CDB`, `Tesouro` ou com setor/segmento indicando CDI passam a ser calculadas por uma camada propria no backend.

Arquivo principal:

- `backend/app/services/fixed_income.py`

Integracoes:

- `backend/app/services/portfolio.py`
- `backend/app/engines/asset_engine.py`
- `backend/app/wealth_os/strategy_engine.py`
- `backend/app/routers/radar.py`
- `frontend/src/pages/Portfolio.jsx`

Entrada esperada:

- Classe do ativo: `Renda fixa`, `Fixed Income`, `RDB`, `CDB` ou equivalente.
- Setor ou segmento com percentual do indexador, por exemplo `100% CDI` ou `110,5% do CDI`.
- Movimentacoes de compra e venda ja existentes no modulo de carteira.

Regra de calculo:

1. O portfolio monta lotes de renda fixa a partir das compras.
2. Vendas reduzem lotes em FIFO, sem apagar historico.
3. O sistema busca CDI diario no Banco Central SGS, serie `12`.
4. A consulta de CDI usa cache em memoria por intervalo de datas por 5 minutos, para evitar chamadas repetidas ao Banco Central quando dashboard, carteira, estrategia e backtest carregam juntos.
5. Para cada dia util com taxa disponivel, aplica:

```text
valor_do_dia = valor_do_dia_anterior * (1 + taxa_cdi_diaria * percentual_do_cdi / 100)
```

6. O valor atual da posicao e a soma dos lotes atualizados.
7. P/L = valor atual - valor aplicado.
8. Rentabilidade = P/L / valor aplicado.

Fallback:

- Se o Banco Central estiver indisponivel, o sistema usa uma taxa diaria estimada apenas para manter a tela funcional.
- O fallback diario atual e `0,047%`, equivalente a uma aproximacao operacional de 100% CDI perto de 1% ao mes antes de impostos.
- O payload marca a origem em `fixedIncome.source`.
- O usuario deve ver a fonte/observacao na tabela de renda fixa.

Impacto visual:

- `Minha Carteira` nao mistura renda fixa com a tabela de acoes.
- Renda fixa aparece em bloco proprio, com indexador, valor aplicado, valor atual, ganho, rentabilidade e fonte.
- Renda fixa nao entra no radar de dividendos, crescimento ou ativos de bolsa.
- `Strategy Engine 2.0` classifica renda fixa como `Caixa/Renda Fixa`, nao como `Global`.
- A `Renda passiva projetada` do dashboard soma `projectedProceedsIncome` e `projectedFixedIncome`. Assim, RDB/CDI entra como rendimento mensal estimado, enquanto acoes/FIIs entram por yield de proventos quando houver dado disponivel.

Limites conhecidos:

- A simulacao local estima rendimento bruto. Tributacao regressiva, IOF e liquidez diaria detalhada devem evoluir no Tax Engine.
- O sistema ainda nao importa extrato real do Nubank; o cadastro manual continua sendo a origem da posicao.

## Proventos, JCP e FIIs

Desde 2026-07-12, o conceito de produto para renda distribuida passa a ser `proventos`.

Proventos incluem:

- Dividendos.
- Juros sobre capital proprio (JCP).
- Rendimentos de FIIs.
- Rendimentos de REITs.
- Juros, cupons e outras distribuicoes futuras.

Compatibilidade:

- A tabela historica continua chamada `dividends`.
- As rotas e chaves antigas continuam funcionando para nao quebrar o frontend e dados atuais.
- O backend adiciona classificacao semantica em `backend/app/services/income.py`.
- O dashboard adiciona `proceedsMonth`, `proceedsYear`, `incomeBreakdownMonth` e `incomeBreakdownYear`.
- O Financial Projection Engine adiciona `totalProceeds`, `proceedsTotal`, `reinvestedProceeds` e `withdrawnProceeds`, preservando as chaves antigas.

Regra:

- Renda passiva projetada usa yield anual de proventos.
- Capital gain nunca entra como renda passiva.
- JCP deve ser acompanhado separado de dividendos porque pode ter IR retido na fonte.
- Rendimentos de FIIs devem ser tratados como proventos imobiliarios e podem ter regra tributaria propria.

FIIs agora possuem motor separado em `backend/app/services/alpha_fii_screener.py`, documentado em `docs/SCREENER_ALPHA_FIIS.md`.

Acoes internacionais agora possuem fundacao separada em `backend/app/services/alpha_global_equity_screener.py`, documentada em `docs/SCREENER_ALPHA_GLOBAL.md`. O modulo entrega `Carteira Alpha Global - watchlist inicial`, com diversificacao por pais, regiao, moeda, bolsa e setor. A comunicacao deve deixar claro que ainda e uma base em validacao, nao uma varredura completa de todas as bolsas do mundo.

O backtest internacional usa `backend/app/services/global_backtest.py`, documentado em `docs/GLOBAL_BACKTEST_ENGINE.md`. Ele compara stock direto, BDR proxy e ETF global em BRL, considerando cambio, dividendos internacionais, retencao simulada e fontes/fallbacks.

## Refinamento arquitetural Fase 1

Status: proposta arquitetural documentada, aguardando aprovacao para implementacao.

A partir da Fase 1, o norte do sistema passa a ser uma plataforma patrimonial global. O nucleo nao deve pensar em "acoes", "FIIs", "ETFs" e "criptomoedas" como estruturas separadas. O nucleo deve pensar em `Asset`.

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

Regra de arquitetura:

- Todo investimento deve ser representado por um `Asset` universal.
- Telas podem ter nomes especificos para facilitar uso, mas regras internas nao devem ser duplicadas por tela.
- Providers externos nao devem ser chamados diretamente por telas ou scores.
- Dados crus devem ser normalizados pelo Market Data Engine e tratados pelo Knowledge Engine.
- Estrategias devem explicar compatibilidade e desalinhamento sem recomendar compra ou venda.
- Alteracoes futuras em banco devem ser aditivas, migradas por Alembic e documentadas.

Documentos da Fase 1:

- `docs/CONSTITUICAO_DO_PROJETO.md`
- `docs/ARQUITETO_CHEFE.md`
- `docs/PRODUCT.md`
- `docs/MAPA_DO_SISTEMA.md`
- `docs/DIAGRAMA_ARQUITETURA.md`
- `docs/ROADMAP.md`
- `docs/ASSET_ENGINE.md`
- `docs/PROVENTOS_ENGINE.md`
- `docs/SCREENER_ALPHA_FIIS.md`
- `docs/SCREENER_ALPHA_GLOBAL.md`
- `docs/GLOBAL_BACKTEST_ENGINE.md`
- `docs/PRODUCTION_READINESS.md`
- `docs/MARKET_DATA_ENGINE.md`
- `docs/KNOWLEDGE_ENGINE.md`
- `docs/STRATEGY_ENGINE.md`
- `docs/MODEL_PORTFOLIOS.md`
- `docs/RECOMMENDED_PORTFOLIO_ENGINE.md`
- `docs/SCREENER_ALPHA_B3.md`
- `docs/VISION_2035.md`

## Stack tecnica

Backend:

- Python.
- FastAPI.
- SQLAlchemy 2.
- Alembic.
- Pydantic.
- JWT para sessao.
- PostgreSQL planejado via Docker Compose.
- SQLite como fallback local para preview e desenvolvimento rapido.

Frontend:

- React.
- Vite.
- TailwindCSS.
- Recharts.
- Lucide React.

Dados externos:

- Camada de providers em `backend/app/services/market_data/providers`.
- Provider mock para demonstracao.
- Provider Brapi preparado para cotacoes e fundamentos.
- Provider CVM preparado para dados publicos da CVM.
- Provider B3 preparado para dados publicos da B3.
- Market Data Engine v2 orquestra BRAPI, Dados de Mercado, FMP, Twelve Data, CoinMarketCap, CoinGecko, Banco Central, Fundamentus, Yahoo Finance Chart e mock, com cache, fallback e normalizacao.

## Estrutura de pastas

```text
CarteiraAlpha/
  backend/
    alembic/
      versions/
    app/
      alpha/
      core/
      engines/
      routers/
      services/
      services/market_data/providers/
      database.py
      dependencies.py
      main.py
      models.py
      schemas.py
      seed.py
    carteira_alpha.db
    alembic.ini
    requirements.txt
  frontend/
    src/
      components/
      lib/
      pages/
      styles/
      App.jsx
      main.jsx
    package.json
  scripts/
    start-carteira-alpha.ps1
    stop-carteira-alpha.ps1
    install-windows-shortcuts.ps1
    db-migrate.ps1
    db-stamp-head.ps1
    run-backend.ps1
    run-frontend.ps1
  docker-compose.yml
  .env.production.example
  .github/workflows/ci.yml
  README.md
  docs/
    ARQUITETO_CHEFE.md
    PRODUCT.md
    MAPA_DO_SISTEMA.md
    DIAGRAMA_ARQUITETURA.md
    ROADMAP.md
    ASSET_ENGINE.md
    FINANCIAL_PROJECTION_ENGINE.md
    PROVENTOS_ENGINE.md
    SCREENER_ALPHA_B3.md
    SCREENER_ALPHA_FIIS.md
    SCREENER_ALPHA_GLOBAL.md
    CRYPTO_RESEARCH_ENGINE.md
    GLOBAL_BACKTEST_ENGINE.md
    PORTFOLIO_BACKTEST.md
    PRODUCTION_READINESS.md
    MARKET_DATA_ENGINE.md
    KNOWLEDGE_ENGINE.md
    STRATEGY_ENGINE.md
    VISION_2035.md
```

## Execucao local

Modo desenvolvimento manual - backend:

```powershell
.\scripts\run-backend.ps1
```

Inicializador recomendado:

```powershell
.\scripts\start-carteira-alpha.ps1
```

Esse script:

- Sobe backend na porta `8000`, se ainda nao estiver rodando.
- Sobe frontend na porta `5173`, se ainda nao estiver rodando.
- Procura `npm` no PATH e, quando nao existir, usa o `pnpm` do runtime local do Codex, inclusive no diretorio `dependencies/bin/fallback`.
- Usa `0.0.0.0` para permitir acesso local e pela rede.
- Descobre o IPv4 atual da maquina.
- Salva URLs em `logs/carteira-alpha-urls.txt`.
- Gera diagnostico de rede local em `logs/carteira-alpha-lan-diagnostic.txt`.
- Abre `http://127.0.0.1:5173`, salvo quando chamado com `-NoBrowser`.

Atalhos Windows:

- `scripts/install-windows-shortcuts.ps1` cria atalhos na Area de Trabalho e outro na inicializacao do Windows.
- Atalho da Area de Trabalho: inicia servidores e abre navegador.
- Atalho `Carteira Alpha 360 Rede`: inicia servidores e mostra URLs para celular/outro computador.
- Atalho `Carteira Alpha 360 Liberar Rede`: abre UAC e libera Firewall para a rede local.
- Atalho `Carteira Alpha 360 Diagnostico Rede`: gera e abre diagnostico de LAN.
- Atalho de inicializacao: inicia servidores em segundo plano ao entrar no Windows.

Parar servidores:

```powershell
.\scripts\stop-carteira-alpha.ps1
```

Modo desenvolvimento manual:

```powershell
.\scripts\run-frontend.ps1
```

URLs:

- Frontend local: `http://127.0.0.1:5173`
- Backend local: `http://127.0.0.1:8000/api/health`
- Frontend na rede: `http://SEU_IP_LOCAL:5173`
- Backend na rede: `http://SEU_IP_LOCAL:8000/api/health`
- Hostname local: `http://NOME_DO_COMPUTADOR:5173`
- Hostname `.local`: `http://NOME_DO_COMPUTADOR.local:5173`

Readiness operacional:

- `GET /api/ready`

Retorna status do banco, ambiente, modo producao e findings sanitizados de seguranca/configuracao.

## Production Readiness

Documento especifico:

- `docs/PRODUCTION_READINESS.md`

Arquivos implementados:

- `backend/app/core/runtime_safety.py`
- `backend/app/core/rate_limit.py`
- `backend/app/core/observability.py`
- `backend/app/services/audit.py`
- `backend/app/services/job_runner.py`
- `backend/app/routers/ops.py`
- `.env.production.example`
- `.github/workflows/ci.yml`
- `backend/tests/test_production_readiness.py`
- `backend/tests/test_ops_observability.py`

Controles atuais:

- Em `ENVIRONMENT=production`, o backend bloqueia startup com `SECRET_KEY` padrao/curto, SQLite, seed demo ativo, provider mock como fonte principal ou Trading Desk habilitado sem chave.
- `GET /api/ready` permite checar readiness sem expor secrets.
- Todas as respostas recebem headers basicos de seguranca, `X-Request-ID` e `X-Process-Time-Ms`.
- `POST /api/auth/login` e `POST /api/auth/register` possuem rate limit em memoria.
- CI executa testes backend, build frontend e E2E smoke em push/pull request.
- Logs estruturados JSON sao gerados por request.
- Auditoria persistente usa `audit_events`.
- Jobs operacionais usam `job_runs`.
- Endpoints operacionais autenticados:
  - `GET /api/ops/observability`
  - `GET /api/ops/audit`
  - `GET /api/ops/jobs`
  - `POST /api/ops/jobs/{job_name}/run`
- Scripts operacionais:
  - `scripts/backup-database.ps1`
  - `scripts/restore-database.ps1`
- Docker:
  - `backend/Dockerfile`
  - `frontend/Dockerfile`
  - `docker-compose.prod.yml`

Limites conhecidos:

- Rate limit em memoria nao e suficiente para producao multi-worker; usar Redis ou storage compartilhado.
- A autenticacao ainda nao possui refresh token, rotacao e revogacao de sessao.
- Deploy HTTPS real com dominio, monitoramento externo gerenciado, testes de carga e auditoria independente ainda sao proximas etapas obrigatorias para ambiente institucional.

## Migracoes de banco

Ferramenta oficial: Alembic.

Arquivos:

- `backend/alembic.ini`: configuracao do Alembic.
- `backend/alembic/env.py`: carrega `DATABASE_URL` pelo mesmo `Settings` usado pela aplicacao e registra `Base.metadata`.
- `backend/alembic/versions/20260709_0001_baseline_current_schema.py`: baseline do schema atual.
- `backend/alembic/versions/20260709_0002_asset_engine_universal.py`: expansao aditiva do Asset Engine Universal.
- `backend/alembic/versions/20260709_0003_market_data_engine_v2_cache.py`: cache persistente do Market Data Engine v2.
- `backend/alembic/versions/20260709_0004_knowledge_facts_and_provider_events.py`: fatos tratados do Knowledge Engine, divergencias de metricas e eventos tecnicos de providers.
- `backend/alembic/versions/20260709_0005_user_preferences.py`: preferencias salvas por usuario.
- `scripts/db-migrate.ps1`: executa `alembic upgrade head`.
- `scripts/db-stamp-head.ps1`: marca um banco local ja existente como estando no baseline atual.

Regra:

- Banco novo deve usar `.\scripts\db-migrate.ps1`.
- Banco local existente, criado antes do Alembic, deve usar `.\scripts\db-stamp-head.ps1` uma unica vez.
- Toda mudanca futura em `backend/app/models.py` deve gerar uma nova revision Alembic no mesmo ciclo de trabalho.
- O `Base.metadata.create_all` ainda permanece no startup como compatibilidade local temporaria. A evolucao oficial do schema passa a ser Alembic.
- O banco SQLite local `backend/carteira_alpha.db` foi marcado como `20260709_0001` em 2026-07-09.
- O banco SQLite local foi migrado para `20260709_0002` em 2026-07-09 com backfill do Asset Engine Universal.
- O banco SQLite local foi migrado para `20260709_0003` em 2026-07-09 com `market_data_cache`.
- O banco SQLite local foi migrado para `20260709_0004` em 2026-07-09 com `asset_facts`, `asset_metric_divergences` e `market_data_provider_events`.
- O banco SQLite local foi migrado para `20260709_0005` em 2026-07-09 com `user_preferences`.

Comandos:

```powershell
.\scripts\db-migrate.ps1
```

```powershell
.\scripts\db-stamp-head.ps1
```

Login demo:

- Email: `demo@carteiraalpha.com`
- Senha: `Carteira@123`

## Variaveis de ambiente

Arquivo local: `.env`

Template de producao: `.env.production.example`

Variaveis principais:

- `ENVIRONMENT`: `development` ou `production`. Em `production`, configuracoes inseguras bloqueiam o startup.
- `DATABASE_URL`: conexao do banco. Exemplo local: `sqlite:///./carteira_alpha.db`.
- `SEED_DEMO_DATA`: carrega dados demonstrativos quando `true`.
- `SECRET_KEY`: chave usada para JWT.
- `ACCESS_TOKEN_EXPIRE_MINUTES`: tempo de expiracao do token.
- `BACKEND_CORS_ORIGINS`: origens permitidas.
- `BACKEND_CORS_ORIGIN_REGEX`: regex para permitir rede local.
- `MARKET_DATA_PROVIDER`: provider ativo, como `mock` ou `brapi`.
- `BRAPI_TOKEN`: chave de API externa. Nunca versionar, nunca expor no frontend.
- `COINMARKETCAP_API_KEY`: chave para cotacoes de criptomoedas via CoinMarketCap. Nunca versionar, nunca expor no frontend.
- `COINGECKO_API_KEY`: chave CoinGecko para fallback de cripto. Nunca versionar, nunca expor no frontend.
- `FMP_API_KEY`: chave Financial Modeling Prep para stocks internacionais, fundamentos, dividendos, splits, perfis e historico. Nunca versionar, nunca expor no frontend.
- `TWELVE_DATA_API_KEY`: chave Twelve Data para cotacoes, historico, dividendos e ativos globais. Nunca versionar, nunca expor no frontend.
- `DADOS_MERCADO_API_TOKEN`: token Dados de Mercado, enviado como `Authorization: Bearer`. Nunca versionar, nunca expor no frontend.
- `FINTZ_API_KEY`: chave futura para Fintz, preparada mas sem provider ativo ate definicao do contrato final.
- `CVM_BASE_URL`: base publica CVM.
- `B3_BASE_URL`: base publica B3.
- `BCB_SGS_BASE_URL`: base SGS do Banco Central para series macro e cambio.
- `FUNDAMENTUS_ENABLED`: habilita o provider Fundamentus secundario, desativado por padrao.
- `FUNDAMENTUS_BASE_URL`: URL base do Fundamentus.
- `FUNDAMENTUS_RATE_LIMIT_SECONDS`: intervalo minimo conservador entre requisicoes.
- `FUNDAMENTUS_TIMEOUT_SECONDS`: timeout maximo das chamadas do provider.
- `TRADING_DESK_ENABLED`: habilita a integracao opcional com Trading Desk EV+.
- `TRADING_DESK_API_URL`: URL base do Trading Desk EV+, exemplo `http://127.0.0.1:8510`.
- `TRADING_DESK_INTEGRATION_KEY`: chave enviada no header `X-Integration-Key`. Nunca versionar, nunca expor no frontend.
- `TRADING_DESK_TIMEOUT_SECONDS`: timeout da chamada de integracao.
- `TRADING_DESK_LOCAL_PATH`: caminho local opcional para ler `config_banca.json` e `historico_financeiro.json` quando o Trading Desk EV+ estiver fechado.

## Banco de dados e modelos

Arquivo principal: `backend/app/models.py`

### User

Representa um usuario SaaS.

Campos principais:

- `id`
- `email`
- `full_name`
- `password_hash`
- `created_at`

Relacionamentos:

- `transactions`
- `dividends`
- `targets`
- `alerts`
- `alpha_events`

Regra multiusuario:

Cada endpoint protegido usa `get_current_user` e filtra dados por `user.id`. Um usuario nao deve acessar carteira de outro usuario.

### Asset

Representa um ativo negociavel.

Direcao arquitetural Fase 1:

- A entidade `Asset` deve evoluir para identidade universal de qualquer investimento.
- `ticker` continua existindo, mas nao deve ser usado como identificador global.
- Campos futuros planejados incluem classe, subclasse, pais, regiao, mercado, bolsa, moeda base, moeda de negociacao, setor, industria, ISIN, CUSIP e simbolo universal interno.

Campos principais:

- `universal_symbol`
- `ticker`
- `name`
- `asset_class`
- `asset_subclass`
- `sector`
- `industry`
- `segment`
- `currency`
- `base_currency`
- `trading_currency`
- `country_code`
- `region`
- `market`
- `exchange`
- `isin`
- `cusip`
- `provider_symbol`
- `last_price`
- `status`
- `updated_at`

Relacionamentos:

- `transactions`
- `dividends`
- `snapshot`
- `identifiers`
- `classifications`
- `exposures`

Compatibilidade:

- `asset_class`, `ticker`, `currency`, `sector`, `segment` e demais campos antigos nao foram removidos.
- Payloads atuais das rotas continuam usando os campos antigos, por exemplo `class`, `sector` e `segment`.
- `universal_symbol` e metadados globais foram adicionados para uso interno futuro.

Backfill local em 2026-07-09:

- 18 ativos existentes receberam `universal_symbol`.
- 18 ativos ficaram com identidade global preenchida.
- 36 identificadores foram criados em `asset_identifiers`.
- 54 classificacoes foram criadas em `asset_classifications`.
- 46 exposicoes foram criadas em `asset_exposures`.
- Exemplos: `TAEE11 -> BR:B3:TAEE11`, `BBDC4 -> BR:B3:BBDC4`, `BTC -> CRYPTO:BTC`.

### AssetIdentifier

Mapeia multiplos identificadores para o mesmo ativo.

Campos principais:

- `asset_id`
- `identifier_type`
- `identifier_value`
- `provider`
- `market`
- `is_primary`
- `created_at`

Uso inicial:

- `universal_symbol`
- `ticker`
- `provider_symbol`, quando diferente do ticker.

### AssetClassification

Armazena classificacoes flexiveis de um ativo sem engessar o modelo principal.

Campos principais:

- `asset_id`
- `taxonomy`
- `level`
- `code`
- `label`
- `weight`
- `source`
- `created_at`

Uso inicial:

- Classe legada.
- Subclasse inferida.
- Setor atual.

### AssetExposure

Armazena exposicoes economicas de ativos, ETFs, cripto e futuros fundos globais.

Campos principais:

- `asset_id`
- `exposure_type`
- `exposure_key`
- `percentage`
- `source`
- `as_of_date`
- `created_at`

Uso inicial:

- Acoes, FIIs e ETFs brasileiros recebem exposicao de pais/regiao/moeda.
- IVVB11 fica listado como ativo brasileiro, mas recebe exposicao economica `US`.
- Criptos recebem exposicao de classe `Crypto` e moeda base do proprio ativo.

### MarketSnapshot

Snapshot de mercado e fundamentos do ativo.

Campos usados nos scores:

- `price`
- `dividend_yield`
- `payout`
- `revenue_growth`
- `profit_growth`
- `net_margin`
- `roe`
- `roic`
- `debt_to_ebitda`
- `historical_appreciation`
- `dividend_consistency`
- `payment_frequency`
- `recurring_profit`
- `sector_stability`
- `pe_ratio`
- `pvp`

Origem atual:

- Dados mockados em `backend/app/seed.py`.
- Futuramente podem vir de Brapi, CVM, B3 ou outro provider.

### Transaction

Registra compras e vendas.

Campos:

- `user_id`
- `asset_id`
- `type`: `buy` ou `sell`
- `date`
- `quantity`
- `price`
- `fees`
- `broker`
- `notes`
- `created_at`

Campos recebidos no payload para cadastro/atualizacao manual do ativo:

- `asset_name`
- `asset_class`
- `sector`
- `segment`

Impacto:

- Alimenta quantidade atual.
- Alimenta preco medio.
- Alimenta valor investido.
- Alimenta lucro/prejuizo.
- Gera evento no Alpha Event Engine.
- Pode preencher manualmente classe, setor, segmento e nome do ativo.

### Dividend

Registra dividendos/proventos.

Campos:

- `user_id`
- `asset_id`
- `date`
- `amount_per_share`
- `total_amount`
- `source`
- `created_at`

Impacto:

- Alimenta dividendos do mes.
- Alimenta dividendos do ano.
- Alimenta historico mensal.
- Alimenta dividend yield sobre preco medio.
- Gera evento no Alpha Event Engine.

### TargetAllocation

Define carteira ideal para rebalanceamento.

Campos:

- `user_id`
- `level`: `asset`, `class` ou outro nivel futuro.
- `target_key`: ticker, classe ou setor.
- `percentage`
- `profile`: dividendos, crescimento ou equilibrado.

### Alert

Armazena alertas.

Campos:

- `user_id`
- `asset_id`
- `type`
- `severity`
- `title`
- `message`
- `is_read`
- `triggered_at`

### AlphaEventModel

Tabela persistida do Alpha Intelligence Engine.

Campos:

- `id`
- `user_id`
- `asset_id`
- `type`
- `category`
- `severity`
- `title`
- `description`
- `impact`
- `occurred_at`
- `status`
- `origin`

Uso:

- Registrar eventos reais, como compra, venda e dividendo.
- Complementar eventos sinteticos gerados pelos engines.
- Servir como base para timeline, resumo inteligente e futuros recursos de IA.

## Autenticacao e seguranca

Arquivos:

- `backend/app/routers/auth.py`
- `backend/app/core/security.py`
- `backend/app/dependencies.py`

Fluxo:

1. Cadastro cria `User` com senha criptografada.
2. Login valida senha com hash.
3. Backend retorna JWT.
4. Frontend envia `Authorization: Bearer TOKEN`.
5. Endpoints protegidos usam `get_current_user`.

Pontos importantes:

- Senhas nunca devem ser salvas em texto puro.
- Token externo, como Brapi, deve ficar apenas no `.env`.
- O frontend nao deve receber secrets.
- Toda consulta de carteira deve filtrar por `user_id`.

## Endpoints REST

Base: `/api`

### Auth

- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`

### Dashboard

- `GET /dashboard`
- `GET /dashboard/projection-premises`
- `PUT /dashboard/projection-premises`
- `DELETE /dashboard/projection-premises`

Retorna:

- `metrics`
- `history`
- `dividendHistory`
- `allocations`
- `positions`
- `externalIntegrations`

As premissas do bloco "Premissas das projecoes" da Visao Geral ficam salvas em `user_preferences` com a chave `dashboard_projection_premises`. Elas persistem `monthly_contribution` e `monthly_return` por usuario e tambem possuem fallback em `localStorage`.

Integracao Trading Desk EV+:

- Arquivo: `backend/app/services/trading_desk_integration.py`.
- Chama `GET {TRADING_DESK_API_URL}/api/integrations/carteira-alpha/summary`.
- Envia header `X-Integration-Key` com `TRADING_DESK_INTEGRATION_KEY`.
- Se a API estiver fechada, indisponivel, com timeout ou chave ausente, tenta ler diretamente `TRADING_DESK_LOCAL_PATH/config_banca.json` e `TRADING_DESK_LOCAL_PATH/historico_financeiro.json`.
- No fallback local, calcula `initialCapital` a partir de `banca_inicial`, `realizedPnl` pela soma de `lucro` do historico financeiro e `currentBalance = initialCapital + realizedPnl`.
- Quando conectado, soma `currentBalance` em `metrics.totalEquity`, soma `initialCapital` em `metrics.investedValue` e soma `totalPnl` no P/L consolidado.
- A alocacao por classe passa a incluir `Trading`.
- Se o Trading Desk estiver fechado, sem chave, com 401 ou timeout, o dashboard segue funcionando e retorna a integracao como desconectada.

### Portfolio

- `GET /portfolio`
- `POST /portfolio/transactions`
- `POST /portfolio/dividends`
- `DELETE /portfolio/positions/{asset_id}`
- `POST /portfolio/sync-market`

`POST /portfolio/transactions` aceita tambem metadados manuais do ativo:

- `asset_name`
- `asset_class`
- `sector`
- `segment`

Uso:

- Permitir que o usuario cadastre a propria classificacao quando a origem externa ainda nao preencheu classe, setor ou segmento.
- Atualizar os dados basicos do ativo quando o ticker ja existe e o usuario informou metadados no formulario.

`DELETE /portfolio/positions/{asset_id}` remove a posicao do usuario logado.

Importante:

- Nao representa venda.
- Nao cria realizacao de lucro/prejuizo.
- Nao remove o ativo global da base.
- Remove apenas dados do usuario atual para aquele ativo.

Dados removidos:

- Compras e vendas (`Transaction`).
- Dividendos (`Dividend`).
- Alertas daquele ativo (`Alert`).
- Eventos Alpha persistidos daquele ativo (`AlphaEventModel`).
- Meta de rebalanceamento por ativo (`TargetAllocation` com `level = asset`).

`POST /portfolio/sync-market` tenta atualizar os ativos da carteira do usuario usando o Market Data Engine.

Comportamento:

- Atualiza preco quando a fonte externa retorna cotacao.
- Atualiza fundamentos disponiveis, como dividend yield, payout, P/L, P/VP, crescimento, margem e ROE quando retornados.
- Consulta providers reais disponiveis via `MarketDataEngine.collect` antes de declarar dado insuficiente.
- Consolida campos por prioridade de fonte em `backend/app/services/market_data/sync.py`.
- Se a fonte externa falhar ou retornar dados parciais, o sistema preserva os dados existentes.
- A chave da API nunca deve ir para o frontend.

### Radar

- `GET /radar/assets`
- `GET /radar/dividends`
- `GET /radar/growth`

Escopo atual:

- As tres rotas retornam apenas ativos que estao na carteira do usuario logado.
- Cripto fica fora do radar tradicional de dividendos/crescimento; deve ter Crypto Score separado.
- O Radar de Ativos nao e lista de compra e nao e recomendacao.
- Ativos com fundamentos incompletos retornam `dataStatus = parcial` e classificacao `Dados parciais`.
- O frontend permite remover uma posicao diretamente dessas telas usando a mesma rota `DELETE /portfolio/positions/{asset_id}`.

### Cripto

- `GET /crypto`
- `POST /crypto/transactions`
- `POST /crypto/sync-market`

Uso:

- Cripto tem aba propria e usa `asset_class = Cripto`.
- A categoria da cripto fica em `Asset.segment`.
- A moeda de referencia fica em `Asset.currency`.
- Exchange/corretora fica em `Transaction.broker`.
- Wallet opcional fica em `Transaction.notes`.
- Cripto entra no patrimonio total e na alocacao por classe.
- Cripto nao entra na renda passiva projetada.
- Cripto nao entra no Radar de Dividendos nem no Score Alpha tradicional de dividendos/crescimento.

Atualizacao de mercado:

- O provider legado CoinMarketCap fica em `backend/app/services/market_data/providers/coinmarketcap.py`.
- A sincronizacao atual usa preferencialmente o Market Data Engine v2, com `CoinMarketCapProviderV2` e fallback `CoinGeckoProviderV2`.
- CoinMarketCap usa quotes latest quando `COINMARKETCAP_API_KEY` esta configurada.
- CoinGecko usa `simple/price` como fallback de cripto quando aplicavel.
- A chave e enviada apenas no backend pelo header `X-CMC_PRO_API_KEY`.
- O parser aceita resposta `data`/`quote` tanto em formato de objeto quanto em lista, pois o endpoint v3 pode retornar arrays para symbol/convert.
- Se a chave nao existir ou a API falhar, o sistema preserva o preco manual informado pelo usuario.

Crypto Score:

- Separado do Alpha Score tradicional.
- Componentes iniciais do MVP: categoria, concentracao na carteira cripto e peso na carteira total.
- Classificacoes: Nucleo, Moderado, Alto risco, Especulativo, Stable e Evitar.
- BTC e ETH recebem leitura estrutural maior.
- Stablecoins recebem leitura separada.
- Meme coins entram como especulativas por padrao.

### Projections

- `POST /projections/simulate`
- `GET /projections/premises`
- `PUT /projections/premises`
- `DELETE /projections/premises`

### Rebalance

- `GET /rebalance?next_contribution=2500`

### Alerts

- `GET /alerts`
- `POST /alerts/{alert_id}/read`

### Intelligence

- `GET /intelligence/summary`
- `GET /intelligence/timeline`
- `GET /intelligence/health`
- `GET /intelligence/insights`
- `GET /intelligence/alpha-score`
- `GET /intelligence/copilot`

## Frontend

Arquivos principais:

- `frontend/src/App.jsx`: shell principal, tema claro/escuro, menu lateral recolhivel, roteamento interno.
- `frontend/src/components/Sidebar.jsx`: navegacao lateral.
- `frontend/src/pages/Login.jsx`: login e cadastro.
- `frontend/src/pages/Dashboard.jsx`: visao geral e Resumo Inteligente.
- `frontend/src/pages/Portfolio.jsx`: carteira e lancamentos.
- `frontend/src/pages/Radar.jsx`: radar de ativos, dividendos e crescimento.
- `frontend/src/pages/Projections.jsx`: simulador financeiro.
- `frontend/src/pages/Rebalance.jsx`: rebalanceamento.
- `frontend/src/pages/Alerts.jsx`: alertas.
- `frontend/src/pages/Settings.jsx`: configuracoes.
- `frontend/src/lib/api.js`: cliente REST.
- `frontend/src/lib/format.js`: formatacao de moeda, percentual e numeros.
- `frontend/src/styles/index.css`: tema visual premium, modo claro/escuro e tokens CSS.
- `frontend/src/components/StatCard.jsx`: cards financeiros compactos usados em dashboards e simuladores.

### Navegacao

A navegacao atual e client-side dentro do React. Isso deixa a troca de abas rapida, sem recarregar o sistema inteiro. O estado de tema e o estado de menu recolhido ficam no `localStorage`.

### Tema visual

Identidade:

- Fundo preto/chumbo no modo escuro.
- Dourado como destaque principal.
- Cards escuros com bordas discretas.
- Tipografia moderna.
- Modo claro opcional.
- Tema claro UI 2.0 com identidade propria, fundo platina, superficies em camadas, acentos dourado+cobalto e profundidade premium.

Tokens principais ficam em `frontend/src/styles/index.css`:

- `--bg`
- `--surface-0`
- `--surface-1`
- `--surface-2`
- `--surface-3`
- `--surface-4`
- `--surface-5`
- `--surface`
- `--border`
- `--border-soft`
- `--border-strong`
- `--border-focus`
- `--text`
- `--text-soft`
- `--muted`
- `--primary`
- `--primary-strong`
- `--primary-soft`
- `--accent`
- `--success`
- `--danger`
- `--warning`
- `--info`
- `--shadow-1`
- `--shadow-2`
- `--shadow-3`
- `--shadow-4`
- `--shadow-5`
- `--radius-xs`
- `--radius-sm`
- `--radius-md`
- `--radius-lg`
- `--radius-xl`

### Design System UI 2.0

Arquivo:

- `frontend/src/styles/index.css`

Objetivo:

- Reconstruir o tema claro sem tratar ele como inversao do tema escuro.
- Criar sensacao de produto SaaS premium.
- Manter todas as funcionalidades, rotas e regras de negocio intactas.

Tema claro:

- Fundo principal: `--bg`, em tom platina/azulado suave. Nao usa branco puro como fundo principal.
- Superficies: cinco niveis de profundidade de `--surface-1` a `--surface-5`.
- Acentos: dourado institucional em `--primary` e cobalto em `--accent`.
- Estados positivos, negativos, alerta e informativos usam `--success`, `--danger`, `--warning` e `--info`.
- Cards usam gradientes extremamente sutis e sombras em camadas.
- Inputs usam fundo proprio, borda suave, hover e foco com halo cobalto.
- Tabelas usam header premium, linhas com hover discreto e separadores suaves.

Escalas:

- Sombras: `--shadow-1` a `--shadow-5`.
- Bordas: `--radius-xs` a `--radius-xl`.
- Espacamento: `--space-1` a `--space-6`.
- Tipografia: `--type-xs` a `--type-2xl`.

Classes base:

- `.app-shell`: fundo geral da aplicacao.
- `.app-header`: header fixo.
- `.app-sidebar`: menu lateral.
- `.surface`: cards e paineis elevados.
- `.field`: inputs, selects e campos premium.
- `.btn-primary`: acao principal.
- `.btn-secondary`: acao secundaria.
- `.icon-button`: botoes compactos de icone.
- `.brand-badge`: selo/acento visual.

Densidade visual:

- O produto usa densidade compacta por padrao para reduzir scroll em desktop.
- A compactacao global fica no final de `frontend/src/styles/index.css`.
- O ajuste reduz `font-size` base, espacamentos `gap-*`/`space-y-*`, paddings de superficies, altura de inputs, botoes, graficos e linhas de tabela.
- A sidebar e uma excecao visual: `frontend/src/components/Sidebar.jsx` usa alturas e espacamentos proprios para ocupar melhor a lateral e manter a navegacao confortavel.
- `StatCard` foi reduzido para cards financeiros mais baixos, preservando icone, label, valor e hint.
- No desktop 1366x768, as telas Minha Carteira, Cripto e Projecoes devem ficar sem scroll vertical ou muito proximas disso. O Dashboard ainda pode ter scroll por conter mais secoes, mas o primeiro viewport deve mostrar resumo, KPIs e graficos principais.
- Em mobile, a prioridade e nao gerar overflow horizontal; o scroll vertical e esperado porque os blocos empilham.

Regra de manutencao visual:

- Preferir alterar tokens no Design System antes de editar pagina por pagina.
- Evitar branco puro como fundo principal no tema claro.
- Nao criar identidade clara apenas invertendo preto/branco.
- Qualquer novo componente deve usar `.surface`, `.field`, `.btn-primary`, `.btn-secondary` ou tokens equivalentes.
- Estados de hover, focus e ativo devem permanecer visiveis nos dois temas.
- Novas telas devem respeitar a densidade compacta: evitar cards altos, graficos acima de 13rem em desktop e tabelas com excesso de padding vertical.

## Origem de cada informacao

### Patrimonio total

Fonte:

- `Transaction`
- `Asset`
- `MarketSnapshot.price` ou `Asset.last_price`

Calculo:

- Para cada ativo: `quantidade atual * preco atual`.
- Soma de todos os ativos em carteira.

Arquivo:

- `backend/app/services/portfolio.py`

### Valor investido

Fonte:

- Compras, vendas, taxas.

Calculo:

- Compra soma `quantity * price + fees`.
- Venda reduz o custo pelo preco medio proporcional da quantidade vendida.

Arquivo:

- `backend/app/services/portfolio.py`

### Quantidade atual

Fonte:

- `Transaction`

Calculo:

- Compras aumentam quantidade.
- Vendas reduzem quantidade ate o limite da posicao existente.

### Preco medio

Fonte:

- Custo acumulado e quantidade atual.

Calculo:

- `valor investido atual / quantidade atual`.

### Valor atual

Fonte:

- Quantidade atual.
- Snapshot de preco.

Calculo:

- `quantidade atual * preco atual`.

### Lucro/prejuizo em reais

Calculo:

- `valor atual - valor investido`.

### Lucro/prejuizo percentual

Calculo:

- `(lucro/prejuizo / valor investido) * 100`.

### Dividendos recebidos no mes

Fonte:

- `Dividend`

Calculo:

- Soma de `total_amount` com `date` no mes e ano atuais.

### Dividendos recebidos no ano

Fonte:

- `Dividend`

Calculo:

- Soma de `total_amount` com `date.year` igual ao ano atual.

### Renda passiva mensal projetada

Fonte:

- Posicoes atuais.
- `MarketSnapshot.dividend_yield`.

Calculo:

- Para cada ativo: `currentValue * dividend_yield / 100 / 12`.
- Soma dos ativos.

Observacao:

- E uma estimativa baseada no yield atual. Nao e promessa de recebimento futuro.

### Evolucao patrimonial

Fonte:

- Posicoes atuais.
- Valor investido atual.
- Valor atual.

Calculo atual:

- Serie sintetica estimada para visualizacao, baseada no progresso mensal ate o patrimonio atual.
- Ultimo ponto sempre reflete os totais atuais.

Arquivo:

- `get_portfolio_history` em `backend/app/services/portfolio.py`.

### Historico de dividendos

Fonte:

- `Dividend`

Calculo:

- Agrupamento mensal dos ultimos 12 meses.

### Alocacao por classe, setor e ativo

Fonte:

- Posicoes atuais.
- Campos `asset_class`, `sector`, `ticker`.

Calculo:

- Soma do valor atual por grupo.
- Peso = `valor do grupo / patrimonio total * 100`.

## Scoring original

Arquivo:

- `backend/app/services/scoring.py`

Funcoes auxiliares:

- `clamp(value, 0, 100)`: limita nota.
- `band(value, low, high)`: transforma uma faixa em nota de 0 a 100.
- `inverse_band(value, low, high)`: quanto menor o valor, maior a nota.
- `classification(score)`: Excelente, Bom, Neutro, Atencao, Evitar.
- `market_term(...)`: gera termo analitico sem recomendacao direta.

### Score de Dividendos

Fonte:

- `dividend_yield`
- `payment_frequency`
- `dividend_consistency`
- `payout`
- `recurring_profit`
- `debt_to_ebitda`
- `sector_stability`

Peso atual:

- Dividend yield: 25%
- Frequencia de pagamento: 15%
- Consistencia historica: 18%
- Payout: 14%
- Lucro recorrente: 12%
- Divida liquida/EBITDA: 9%
- Estabilidade setorial: 7%

Saida:

- `scoreDividendos`
- justificativas textuais.

### Score de Crescimento

Fonte:

- `revenue_growth`
- `profit_growth`
- `net_margin`
- `roe`
- `roic`
- `debt_to_ebitda`
- `historical_appreciation`
- `recurring_profit`

Peso atual:

- Crescimento de receita: 17%
- Crescimento de lucro: 19%
- Margem liquida: 13%
- ROE: 15%
- ROIC: 14%
- Divida: 10%
- Valorizacao historica: 7%
- Consistencia operacional: 5%

### Score de Seguranca

Fonte:

- `debt_to_ebitda`
- `recurring_profit`
- `sector_stability`
- `dividend_consistency`

Peso atual:

- Divida: 35%
- Lucro recorrente: 25%
- Estabilidade setorial: 25%
- Consistencia de dividendos: 15%

### Score de Valuation

Fonte:

- `pe_ratio`
- `pvp`

Regra:

- P/L recebe faixa favoravel aproximada entre 6 e 14.
- P/VP recebe faixa favoravel aproximada entre 0,7 e 1,4.

Peso:

- P/L: 58%
- P/VP: 42%

### Score de Risco

Fonte:

- `debt_to_ebitda`
- `recurring_profit`
- `sector_stability`
- `dividend_consistency`

Quanto maior o score de risco, pior. Em composicoes finais o sistema usa `100 - scoreRisco`.

### Score Final original

Formula:

```text
final =
  dividendos * 0.24 +
  crescimento * 0.24 +
  seguranca * 0.22 +
  valuation * 0.18 +
  (100 - risco) * 0.12
```

Uso:

- Radar geral.
- Radar de dividendos.
- Radar de crescimento.

## Alpha Intelligence Engine

Pasta:

- `backend/app/alpha`

Objetivo:

Ser o cerebro analitico da plataforma, usando dados internos da carteira. Ele interpreta a situacao, gera eventos, timeline, saude, insights, score expandido e interface futura para IA.

Regra:

- Nunca emitir "compre" ou "venda".
- Nunca prometer rentabilidade.
- Nunca depender diretamente da interface.

### Contracts

Arquivo:

- `backend/app/alpha/contracts.py`

Define estruturas:

- `AlphaEvent`
- `HealthScore`
- `HealthReport`
- `Insight`
- `ScoreBreakdown`
- `AlphaScoreV2`
- `CopilotQuestion`

### Event Engine

Arquivo:

- `backend/app/alpha/event_engine.py`

Tipos de eventos cobertos:

- Compra realizada.
- Venda realizada.
- Novo dividendo recebido.
- Concentracao elevada.
- Setor acima do limite.
- Novo maior patrimonio.
- Novo maior dividendo.
- Score em faixa forte.
- Score pedindo acompanhamento.
- Alertas convertidos para timeline.

Campos do evento:

- `id`
- `tipo`
- `categoria`
- `gravidade`
- `ativo`
- `titulo`
- `descricao`
- `impacto`
- `data`
- `status`
- `origem`

Eventos persistidos:

- Compras.
- Vendas.
- Dividendos.

Eventos sinteticos:

- Concentracao.
- Recordes.
- Alertas.
- Leitura de score.

### Timeline Engine

Arquivo:

- `backend/app/alpha/timeline_engine.py`

Funcao:

- Ordena eventos em ordem cronologica decrescente.

### Health Engine

Arquivo:

- `backend/app/alpha/health_engine.py`

Gera notas de 0 a 100 para:

- Diversificacao.
- Concentracao.
- Liquidez.
- Dividendos.
- Crescimento.
- Seguranca.
- Valuation.
- Volatilidade.
- Renda Passiva.
- Qualidade Geral.

Tambem gera:

- `notaGeral`
- `status`
- justificativas.

#### Diversificacao

Fonte:

- Quantidade de ativos.
- Quantidade de classes.
- Quantidade de setores.

Peso:

- Ativos: 45%
- Classes: 25%
- Setores: 30%

#### Concentracao

Fonte:

- Maior peso por ativo.
- Maior peso por setor.

Regra:

- Penaliza ativo acima de 15%.
- Penaliza setor acima de 30%.

#### Liquidez

Fonte:

- Classe do ativo.
- Valor atual da posicao.

Notas base:

- Acoes: 84
- ETFs: 88
- FIIs: 72
- Renda fixa: 80
- Cripto: 62

Calculo:

- Media ponderada pelo valor atual das posicoes.

#### Dividendos

Fonte:

- Dividend yield sobre preco medio.
- Renda anual projetada sobre patrimonio.

Peso:

- DY sobre preco medio: 55%
- Renda anual projetada: 45%

#### Crescimento, Seguranca e Valuation

Fonte:

- Media dos scores dos ativos em carteira.

#### Volatilidade

Fonte:

- Score de risco dos ativos.

Calculo:

- `100 - media(scoreRisco)`.

#### Renda Passiva

Fonte:

- Renda mensal projetada.
- Dividendos recebidos no ano.

#### Qualidade Geral

Fonte:

- Dividendos.
- Crescimento.
- Seguranca.
- Valuation.
- Volatilidade.

### Insight Engine

Arquivo:

- `backend/app/alpha/insight_engine.py`

Gera insights com:

- `titulo`
- `descricao`
- `prioridade`
- `tipo`
- `impacto`
- `data`

Exemplos atuais:

- Maior ativo com peso elevado.
- Setor concentrado.
- Renda passiva recebida no mes.
- Renda passiva mensal projetada.
- Score Alpha em faixa saudavel ou pedindo acompanhamento.
- Ativo lider no Score Alpha 2.0.
- Ativo fora da faixa saudavel.
- Patrimonio em novo recorde interno.

### Alpha Score 2.0

Arquivo:

- `backend/app/alpha/alpha_score_engine.py`

Componentes:

- Dividendos.
- Crescimento.
- Seguranca.
- Valuation.
- Liquidez.
- Concentracao.
- Diversificacao.
- Volatilidade.
- Governanca.
- Resultado.
- Score Final.

Formula atual:

```text
final =
  dividendos * 0.16 +
  crescimento * 0.16 +
  seguranca * 0.13 +
  valuation * 0.11 +
  liquidez * 0.08 +
  concentracao * 0.10 +
  diversificacao * 0.08 +
  volatilidade * 0.07 +
  governanca * 0.05 +
  resultado * 0.06
```

#### Liquidez

Fonte:

- Classe do ativo.

Notas base iguais ao Health Engine.

#### Concentracao

Fonte:

- Peso do ativo na carteira.

Regra:

- Quanto maior o peso acima da faixa definida, menor a nota.

#### Diversificacao

Fonte:

- Peso do setor.
- Peso do ativo.

Regra:

- Penaliza setor acima de 30%.
- Penaliza ativo acima de 15%.

#### Volatilidade

Fonte:

- Score de risco original.

Calculo:

- `100 - scoreRisco`.

#### Governanca

Fonte:

- Lucro recorrente.
- Estabilidade setorial.
- Divida liquida/EBITDA.
- Consistencia de dividendos.

Peso:

- Recorrencia: 32%
- Estabilidade: 25%
- Divida: 25%
- Consistencia: 18%

#### Resultado

Fonte:

- Crescimento de receita.
- Crescimento de lucro.
- Margem liquida.
- ROE.
- ROIC.

Peso:

- Receita: 22%
- Lucro: 26%
- Margem: 18%
- ROE: 17%
- ROIC: 17%

### Intelligence Service

Arquivo:

- `backend/app/alpha/intelligence_service.py`

Agrega:

- Summary.
- Timeline.
- Health.
- Insights.
- Alpha Score.
- Copilot.

E o ponto recomendado para criar novas respostas de inteligencia antes de expor por rota.

### Alpha Copilot

Arquivo:

- `backend/app/alpha/copilot.py`
- `backend/app/wealth_os/copilot_service.py`
- `frontend/src/pages/Copilot.jsx`

Status:

- Alpha Copilot conversacional implementado no Wealth OS.
- Provider de IA opcional no backend.
- Fallback deterministico seguro quando a IA externa nao estiver configurada.

Perguntas estruturadas preservadas:

- Quanto falta para minha liberdade financeira?
- Meu risco aumentou?
- Por que meu score caiu?
- Quanto preciso aportar?
- Explique minha carteira.
- Qual ativo pesa mais?

Dados de contexto:

- Patrimonio total.
- Proventos e renda passiva.
- Renda passiva projetada.
- Quantidade de ativos.
- Maior ativo.
- Maior peso.
- Nota geral.
- Goal Engine.
- Guardian.
- Strategy Engine.
- Scenario & Stress Test.
- Economic Engine.
- Data Confidence Engine.

Regras:

- Nao chamar LLM diretamente a partir do frontend.
- Enviar para o provider apenas contexto interno consolidado.
- Citar as fontes internas em cada resposta.
- Declarar lacunas quando os dados forem insuficientes.
- Nao emitir promessa de rentabilidade nem ordem direta de compra ou venda.

## Projecao financeira

Arquivo:

- `backend/app/engines/financial_projection_engine.py`
- `backend/app/services/projections.py`

Regra de arquitetura:

- O `FinancialProjectionEngine` e a unica fonte de verdade para projecoes financeiras.
- Componentes React nao fazem calculo financeiro; eles apenas enviam premissas e exibem o resultado da API.
- Dashboard, Simulador Patrimonial, Wealth Builder, Guardian e Copilot devem reutilizar este motor.
- Premissas salvas ficam em `user_preferences` com chave `projection_premises`, isoladas por usuario.

Entrada:

- Patrimonio inicial.
- Aporte mensal.
- Rentabilidade mensal esperada.
- Dividend yield anual esperado.
- Reinvestimento de dividendos.
- Percentual de reinvestimento dos dividendos.
- Aumento anual dos aportes.
- Series variaveis opcionais para rentabilidade mensal, yield anual e inflacao anual.
- Prazo em anos.
- Inflacao anual.
- Meta de renda passiva mensal.

Calculo mensal:

1. Soma aporte mensal.
2. Calcula capital gain: `patrimonio_apos_aporte * rentabilidade_mensal`.
3. Soma capital gain ao patrimonio.
4. Calcula renda passiva distribuida: `patrimonio_apos_valorizacao * yield_anual / 12`.
5. Reinveste a parcela definida dos dividendos/JCP ou trata o restante como saque.
6. Atualiza fator de inflacao acumulado e patrimonio real.
7. Calcula renda passiva mensal final: `patrimonio_final * yield_anual / 12`.
8. Identifica quando a meta de independencia financeira e atingida usando apenas renda passiva.

Interpretacao importante:

- `expected_monthly_return` e tratado como rentabilidade mensal sem dividendos/JCP.
- `expected_annual_dividend_yield` e tratado como dividendos/JCP anual esperado.
- Se o usuario informar uma rentabilidade mensal que ja inclui dividendos, deve usar DY 0 para evitar contagem dupla.
- Capital gain representa apenas valorizacao dos ativos.
- Renda passiva representa apenas dinheiro distribuido: dividendos, JCP, FIIs, REITs, cupons, juros e rendimentos.
- Quando `dividend_reinvestment_rate > 0`, a parte reinvestida entra no patrimonio e tambem passa a render nos meses seguintes.
- Meta financeira e baseada exclusivamente em renda passiva: `patrimonio * yield_anual / 12`.

Saida:

- Valor final projetado.
- Total aportado.
- Total recebido em dividendos.
- Capital gain acumulado.
- Dividendos/JCP reinvestidos.
- Dividendos/JCP sacados.
- Patrimonio final nominal.
- Patrimonio final real.
- Inflacao acumulada.
- Ganho real.
- Bloco de independencia financeira com renda passiva mensal, meta, percentual da meta, quanto falta, patrimonio necessario e tempo estimado.
- Grafico "Como o patrimonio cresceu" com capital aportado, valorizacao, dividendos reinvestidos, dividendos sacados, inflacao e ganho real.
- Meses/anos estimados ate meta.
- Serie anual/mensal reduzida para grafico.
- Premissas calculadas em `assumptions`, incluindo retorno mensal efetivo e DY mensal aproximado.

Persistencia das premissas:

- `GET /api/projections/premises`: carrega o ultimo cenario salvo do usuario.
- `PUT /api/projections/premises`: salva as premissas atuais do usuario.
- `DELETE /api/projections/premises`: remove o cenario salvo e volta ao padrao da tela.
- Frontend tambem mantem fallback em `localStorage` para a tela carregar rapido, mas a fonte persistente para SaaS e o backend.

Formulas:

- Capital gain: `patrimonio_apos_aporte * rentabilidade_mensal`.
- Renda passiva: `patrimonio_apos_valorizacao * yield_anual / 12`.
- Dividendos reinvestidos: `renda_passiva * percentual_reinvestimento`.
- Dividendos sacados: `renda_passiva - dividendos_reinvestidos`.
- Patrimonio final: `patrimonio + aportes + valorizacao + dividendos_reinvestidos`.
- Patrimonio real: `patrimonio_nominal / fator_inflacao_acumulado`.
- Patrimonio necessario para meta: `meta_mensal * 12 / yield_anual`.
- Percentual da meta: `renda_passiva_mensal / meta_mensal`.

Aviso:

- Simulacao baseada em premissas. Nao promete rentabilidade futura.

## Rebalanceamento

Arquivo:

- `backend/app/services/rebalance.py`

Entrada:

- Posicoes atuais.
- Alocacoes alvo por ativo.
- Proximo aporte.

Regra:

- Se o usuario tem alvos definidos, usa `TargetAllocation`.
- Se nao tem alvos, distribui igualmente entre ativos atuais.

Status por ativo:

- `abaixo_do_peso`: diferenca maior que 1 ponto percentual.
- `acima_do_peso`: diferenca menor que -1 ponto percentual.
- `alinhado`: dentro da faixa.

Sugestao de proximo aporte:

- Distribui o aporte proporcionalmente entre ativos abaixo do peso.

Risco de concentracao:

- `alto` se algum ativo pesa 20% ou mais.
- `controlado` caso contrario.

## Providers de dados de mercado

Direcao arquitetural Fase 1:

- Providers devem ser adaptadores do Market Data Engine.
- Radares, scores e telas nao devem consumir provider cru.
- Falhas de provider devem ter fallback ou cache quando possivel.
- Toda resposta de mercado deve preservar provider, data, moeda, unidade e qualidade do dado.

Market Data Engine v2:

- Contrato unico `MarketDataProviderV2` em `backend/app/services/market_data/v2/contracts.py`.
- Orquestrador `MarketDataEngine` em `backend/app/services/market_data/v2/engine.py`.
- `ProviderManager` em `backend/app/services/market_data/v2/provider_manager.py`.
- Normalizacao em `backend/app/services/market_data/v2/normalization.py`.
- Cache em memoria e cache em banco em `backend/app/services/market_data/v2/cache.py`.
- Provider mock v2 em `backend/app/services/market_data/v2/providers/mock.py`.
- Provider BRAPI v2 em `backend/app/services/market_data/v2/providers/brapi.py`.
- Provider Dados de Mercado v2 em `backend/app/services/market_data/v2/providers/dados_mercado.py`.
- Provider Financial Modeling Prep v2 em `backend/app/services/market_data/v2/providers/fmp.py`.
- Provider Twelve Data v2 em `backend/app/services/market_data/v2/providers/twelvedata.py`.
- Provider CoinMarketCap v2 em `backend/app/services/market_data/v2/providers/coinmarketcap.py`.
- Provider CoinGecko v2 em `backend/app/services/market_data/v2/providers/coingecko.py`.
- Provider Banco Central v2 em `backend/app/services/market_data/v2/providers/bcb.py`.
- Provider Fundamentus v2 em `backend/app/services/market_data/v2/providers/fundamentus.py`, secundario e opcional.
- Provider Yahoo Finance Chart v2 em `backend/app/services/market_data/v2/providers/yahoo.py`, fallback auxiliar para historico de acoes.
- Providers antigos permanecem para compatibilidade.
- O frontend continua sem consultar APIs externas diretamente.
- Tokens continuam apenas em variaveis de ambiente do backend.
- Falhas de provider podem ser registradas em `market_data_provider_events`.
- Quando o engine recebe `asset_id` e sessao de banco, dados normalizados sao enviados ao Knowledge Engine como fatos tratados.
- O metodo `collect(data_type, request)` consulta todos os providers reais disponiveis com cache separado por provider.
- O mock continua disponivel para desenvolvimento, mas nao deve sobrescrever dados reais nas sincronizacoes de mercado.

Tipos de dados preparados:

- Cotacoes.
- Fundamentos.
- Dividendos.
- Historico de precos.
- Cambio.
- Cripto via contrato/fallback.
- Busca de ativos.

### MarketDataCacheEntry

Tabela: `market_data_cache`

Campos principais:

- `cache_key`
- `provider`
- `data_type`
- `payload_json`
- `quality_score`
- `expires_at`
- `created_at`
- `updated_at`

Uso:

- Cache persistente opcional do Market Data Engine v2.
- Quando o engine recebe uma sessao SQLAlchemy, usa cache em banco.
- Quando nao recebe sessao, usa cache em memoria.
- Payloads normalizados preservam provider, data, moeda, qualidade e avisos.

### FundamentusProviderV2

Status: provider secundario e opcional para validacao/comparacao fundamentalista.

Regras:

- Nao e fonte principal.
- Nao e chamado pelo frontend.
- Fica desativado por padrao via `FUNDAMENTUS_ENABLED=false`.
- So atende dados de fundamentos no backend.
- Usa cache obrigatorio do Market Data Engine antes de nova coleta.
- Verifica `robots.txt` em tempo de execucao antes de acessar `detalhes.php`.
- Aplica rate limit conservador por `FUNDAMENTUS_RATE_LIMIT_SECONDS`.
- Em `403`, timeout, bloqueio ou indisponibilidade, registra evento tecnico e cai para fallback.
- Dados salvos como fonte `fundamentus` no Knowledge Engine nunca sobrescrevem BRAPI, CVM ou B3.

Campos tratados quando disponiveis:

- `pe_ratio`
- `pvp`
- `ev_ebitda`
- `roe`
- `roic`
- `net_margin`
- `debt_to_ebitda`
- `dividend_yield`
- `payout`
- `revenue`
- `profit`
- `market_value`

### AssetFact

Tabela: `asset_facts`

Uso:

- Armazena fatos tratados por ativo, fonte, metrica e periodo.
- Preserva origem e payload bruto normalizado para auditoria.
- Permite comparar BRAPI, CVM, B3, Fundamentus e fontes futuras sem sobrescrever dados oficiais.

Campos principais:

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

### AssetMetricDivergence

Tabela: `asset_metric_divergences`

Uso:

- Registra divergencias relevantes entre uma fonte primaria/oficial e uma fonte de comparacao.
- O limiar inicial e 15% de divergencia relativa.
- A divergencia nao altera snapshots nem scores automaticamente; ela alimenta auditoria e o futuro Centro Fundamentalista.

### MarketDataProviderEvent

Tabela: `market_data_provider_events`

Uso:

- Registra falhas tecnicas de providers, como bloqueio, timeout, rate limit e indisponibilidade.
- Ajuda o Guardian e a observabilidade futura a diferenciar erro de dado externo de erro de negocio.

Pasta:

- `backend/app/services/market_data/providers`

Objetivo:

Permitir trocar a origem dos dados sem alterar dashboard, carteira, scores ou frontend.

Providers atuais:

- `mock.py`: dados demonstrativos.
- `brapi.py`: estrutura para API Brapi.
- `cvm.py`: estrutura para dados publicos CVM.
- `b3.py`: estrutura para dados publicos B3.
- `factory.py`: escolhe provider com base em configuracao.
- `base.py`: contrato comum.

Regra de arquitetura:

- Novos providers devem implementar o contrato base.
- Rotas e servicos de negocio nao devem depender de detalhes especificos de uma API externa.
- Secrets ficam no `.env`.

## Dados mockados

Arquivo:

- `backend/app/seed.py`

Inclui:

- Ativos demonstrativos.
- Snapshots de fundamentos.
- Usuario demo.
- Transacoes demo.
- Dividendos demo.
- Alvos de rebalanceamento.
- Alertas demo.

Ativos demo atuais:

- TAEE11
- ITSA4
- PETR4
- HGLG11
- KNRI11
- IVVB11
- BOVA11
- WEGE3

Uso:

- Desenvolvimento local.
- Demonstracao.
- Validacao visual.

## Cuidados ao evoluir o sistema

### Ao criar nova metrica

1. Definir fonte do dado.
2. Implementar no backend, preferencialmente em `services` ou `alpha`.
3. Expor por rota apenas se necessario.
4. Atualizar frontend.
5. Atualizar esta documentacao.
6. Validar com usuario demo.

### Ao alterar Minha Carteira

1. Lembrar que posicoes sao calculadas a partir de transacoes e dividendos.
2. Venda deve continuar sendo evento financeiro real.
3. Exclusao de posicao deve continuar sendo limpeza de cadastro, nao venda.
4. Toda exclusao deve filtrar por `user_id`.
5. Nao apagar o registro global de `Asset` ao remover uma posicao do usuario.
6. Atualizar esta documentacao quando campos de cadastro manual mudarem.

### Ao alterar Radar, Dividendos ou Crescimento

1. Manter escopo padrao como carteira do usuario, nao universo global de ativos.
2. Nao transformar ranking em recomendacao de compra.
3. Mostrar dados parciais quando fundamentos externos estiverem incompletos.
4. Permitir remocao apenas por `user_id`.
5. Cripto deve ficar fora do Score Alpha tradicional de dividendos/crescimento.

### Ao alterar formula de score

1. Atualizar o arquivo de score.
2. Atualizar justificativas textuais.
3. Verificar se a classificacao continua coerente.
4. Garantir que nao existe recomendacao direta.
5. Atualizar a secao de metricas deste documento.

### Ao adicionar IA

1. Manter LLM fora do frontend.
2. Criar servico backend especifico.
3. Enviar para o LLM apenas contexto consolidado e permitido.
4. Registrar eventos importantes, se a resposta gerar mudanca no estado.
5. Manter respostas sem promessa de rentabilidade e sem ordem de compra/venda.

### Ao conectar dados reais

1. Criar ou ajustar provider.
2. Mapear resposta externa para modelos internos.
3. Validar unidades: percentual, moeda, data, ticker, classe, setor.
4. Tratar falhas de API.
5. Preservar fallback mock.
6. Nunca expor token.

## Checklist de validacao tecnica

Backend:

```powershell
cd C:\Users\miche\OneDrive\Documentos\CarteiraAlpha\backend
.\.venv\Scripts\python.exe -m compileall app
.\.venv\Scripts\python.exe -m alembic heads
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Frontend:

```powershell
cd C:\Users\miche\OneDrive\Documentos\CarteiraAlpha\frontend
pnpm run build
```

Rotas principais:

```text
GET  /api/health
POST /api/auth/login
GET  /api/dashboard
GET  /api/portfolio
GET  /api/portfolio/backtest
GET  /api/radar/assets
GET  /api/intelligence/summary
GET  /api/intelligence/timeline
GET  /api/intelligence/health
GET  /api/intelligence/insights
GET  /api/intelligence/alpha-score
GET  /api/intelligence/copilot
GET  /api/model-portfolios
POST /api/model-portfolios/validate
GET  /api/model-portfolios/recommended-report
POST /api/model-portfolios/recommended-report/run
GET  /api/model-portfolios/screener
POST /api/model-portfolios/screener/run
```

## Historico de decisoes

### Decisao: navegacao React client-side

Motivo:

- Troca de abas muito rapida.
- Evita recarregar a aplicacao a cada clique.
- Melhora a sensacao de plataforma profissional.

### Decisao: menu lateral compacto e menos redundante

Motivo:

- O menu lateral precisa caber inteiro em telas menores sem esconder itens importantes.
- O bloco visual `Plataforma segura` foi removido da lateral porque ocupava espaco permanente sem ajudar a operacao diaria.
- As telas `Proventos`, `Crescimento` e `Radar de Ativos` eram variacoes do mesmo componente analitico e geravam sensacao de repeticao para o usuario.
- A navegacao visivel passou a consolidar essas leituras em `Analise da Carteira`.
- As rotas antigas continuam registradas internamente para compatibilidade, mas a experiencia principal fica mais simples.

Regra:

- Novas abas so devem entrar no menu quando tiverem funcao clara e diferente para um usuario leigo.
- Nomes de menu devem evitar termos tecnicos quando existir uma opcao mais humana.

### Decisao: engines no backend

Motivo:

- Inteligencia nao deve depender da interface.
- Facilita adicionar IA no futuro.
- Evita duplicar regra de negocio no frontend.

### Decisao: independencia financeira mede patrimonio faltante hoje

Motivo:

- A renda passiva projetada no fim do prazo nao deve ser confundida com a situacao atual do investidor.
- O bloco `Independencia financeira` da aba `Projecoes` agora mostra patrimonio atual considerado, patrimonio necessario, quanto falta em patrimonio, progresso hoje e progresso projetado no fim do prazo.
- Formula: `quanto_falta = max(patrimonio_necessario - patrimonio_atual_considerado, 0)`.
- `currentGoalProgressPct` mostra o percentual da meta hoje.
- `projectedGoalProgressPct` mostra o percentual da meta no fim da simulacao.
- A rota `POST /api/projections/simulate` passa o patrimonio consolidado atual da carteira para o motor financeiro quando o usuario esta autenticado.

### Decisao: resumo consolidado da Minha Carteira no backend

Motivo:

- O backend precisa manter quantidade de acoes, quantidade de cripto, P/L por classe e P/L consolidado para reutilizacao em outras telas.
- O endpoint `GET /api/portfolio` passou a devolver o campo aditivo `summary`.
- `summary.stocks`, `summary.crypto` e `summary.total` trazem quantidade, numero de ativos, valor investido, valor atual, P/L em reais e P/L percentual.
- O calculo atual usa `valor atual versus preco medio/custo investido`; P/L mensal real deve evoluir futuramente com historico de snapshots de mercado.

Decisao visual de 2026-07-13:

- A tela `Minha Carteira` nao deve misturar cripto nos cards e na tabela principal de acoes.
- O topo da tela fica focado em acoes/ativos de bolsa: valor atual, quantidade de ativos, P/L de acoes e peso em acoes.
- Criptomoedas ficam em bloco proprio abaixo, com cards e tabela dedicados.
- O P/L consolidado total deixa de aparecer na aba `Minha Carteira` e passa a ser leitura da `Visao Geral`, no card `P/L total`.
- O campo `summary.total` continua no payload por compatibilidade e para consumo de outras telas.

### Decisao: backtest retroativo da carteira atual

Motivo:

- O usuario precisa analisar como os ativos atuais teriam se comportado em um periodo historico escolhido.
- O endpoint `GET /api/portfolio/backtest` calcula no backend a evolucao mensal de acoes, cripto e consolidado.
- A primeira versao usa as quantidades atuais como base retroativa.
- Historico de preco deve vir do Market Data Engine v2; FMP, Twelve Data, CoinGecko e Yahoo Finance Chart sao fontes preparadas para esta primeira versao.
- Quando alguma fonte falha, o sistema usa fallback de preco atual apenas para manter a tela funcional e informa a cobertura de dados.
- Dividendos, JCP, splits, impostos, taxas e movimentacoes reais historicas ficam para a evolucao futura do motor.

Atualizacao de 2026-07-13:

- Renda fixa deixou de ser somada em `stocksValue`.
- O backtest agora devolve `fixedIncomeValue` separado de `stocksValue` e `cryptoValue`.
- Renda fixa usa o valor atual como ancora no backtest retroativo inicial, pois a curva historica diaria de CDI por lote pertence ao modulo de carteira atual.
- A interface mostra linha separada de `Renda fixa` para evitar que RDB/CDI pareca acao no grafico.

### Decisao: providers de mercado substituiveis

Motivo:

- Permite trocar Brapi, CVM, B3 ou outros provedores.

### Decisao: validacao honesta da Carteira Recomendada

Motivo:

- A carteira recomendada pode nascer de relatorios ou estudos externos, mas nao deve ser tratada como validada sem checagem propria.
- O endpoint `POST /api/model-portfolios/validate` tenta atualizar dados via Market Data Engine e recalcula scores de dados, dividendos, seguranca, valuation, risco, setor e concentracao.
- Quando o provider devolve somente preco, P/L ou dados parciais, o sistema deve exibir `dados_insuficientes` ou `em_validacao`, em vez de criar uma falsa certeza.
- Fontes secundarias, como Fundamentus, podem enriquecer a validacao via Knowledge Engine, mas nao sobrescrevem fontes oficiais sem comparacao e divergencia documentada.
- Reduz acoplamento.
- Mantem fallback mock para desenvolvimento.

### Decisao: Screener Alpha B3 como origem da carteira oficial

Motivo:

- A carteira principal da tela `Carteira Recomendada` nao deve depender da carteira antiga importada de relatorios externos.
- O backend passa a gerar a `Carteira Recomendada Alpha oficial` em `backend/app/services/alpha_b3_screener.py`.
- O Screener le universo B3 via BRAPI quando disponivel, filtra instrumentos fora da tese, avalia setores perenes e combina leitura estrategica com fundamentos vindos do Market Data Engine.
- Os pesos oficiais atuais sao documentados em `docs/SCREENER_ALPHA_B3.md`.
- A carteira antiga permanece como historico/importacao e compatibilidade, mas nao e mais a fonte principal exibida ao usuario.

### Decisao: Screener Alpha Crypto com regra Binance-first

Motivo:

- A primeira candidata cripto importada, PEPETO, tinha assimetria especulativa, mas falhou no criterio operacional de compra simples.
- O bloco `Cripto do mes` passa a ser gerado por `backend/app/services/alpha_crypto_screener.py`.
- A primeira regra do motor e acesso: a cripto precisa estar disponivel na Binance ou exchange grande equivalente, com liquidez real e processo simples para o usuario.
- JASMY foi definida como candidata atual por estar disponivel via JASMY/USDT na Binance Spot, ter preco unitario baixo e tese especulativa ligada a IoT/soberania de dados.
- O motor deve continuar exibindo risco extremo, limite simbolico de alocacao, alerta sobre market cap/supply e revisao mensal.
- Preco unitario baixo nao pode ser usado isoladamente como sinal de oportunidade; supply, market cap, volume, desbloqueios, holders, narrativa e execucao precisam compor a leitura.
- A busca de oportunidade e externa primeiro. A carteira atual entra depois para classificar a decisao como `nova_oportunidade` ou `reforcar_tese_existente`.
- O resultado mensal e cacheado em `user_preferences` com chave `alpha_crypto_screener:YYYY-MM`; `POST /api/model-portfolios/crypto-screener/run` forca nova varredura.

### Decisao: Crypto Research Engine apos o Screener Alpha Crypto

Motivo:

- O ranking quantitativo nao deve virar candidata final sozinho.
- A cripto do mes precisa de tese, catalisadores, riscos, tokenomics, supply, liquidez, FDV, red flags e cenarios antes de aparecer como destaque.
- O novo arquivo `backend/app/services/crypto_research_engine.py` recebe as melhores candidatas do screener e retorna `researchReport`, `researchScore`, `conviction`, `dueDiligence` e `scenarios`.
- A tela `Carteira Recomendada` continua consumindo o payload antigo, mas agora tambem exibe a camada de research.
- A regra de arquitetura fica: Screener encontra oportunidades; Research valida a tese; interface apenas apresenta a leitura.
- O motor continua sem prometer valorizacao e sem transformar estudo especulativo em garantia de resultado.

### Decisao: Alpha Confidence Engine para auditabilidade das indicacoes

Motivo:

- A Carteira Recomendada precisa transmitir confianca sem fingir certeza absoluta.
- O usuario final precisa bater o olho e entender por que o Alpha confia ou limita a confianca em uma indicacao.
- A confianca nao deve ficar espalhada na interface React nem depender de texto manual.
- O novo arquivo `backend/app/services/alpha_confidence_engine.py` recebe Screener Alpha B3, FIIs, Global, Crypto Research, validacao e backtests.
- A saida e o payload aditivo `confidenceReport`, consumido pela tela `frontend/src/pages/ModelPortfolios.jsx`.
- O motor gera nota geral, gates de confianca, nota por ativo, leitura humana e regras nao negociaveis.
- Gates atuais: cobertura de dados, metodologia, fundamentos, controle de risco, diversificacao, historico/cenarios e fontes/rastreabilidade.
- Regra central: nenhum ativo pode ser tratado como `compra sem medo`; a linguagem correta e confianca analitica, risco controlado, tese especulativa ou validacao adicional.
- O motor prepara a futura integracao com Knowledge Engine, Guardian e Centro Fundamentalista para reduzir automaticamente a confianca quando dados, eventos ou fundamentos piorarem.

### Decisao: Recommended Portfolio Engine institucional

Motivo:

- A Carteira Recomendada Alpha precisa parecer e funcionar como relatorio institucional mensal, nao apenas como tabela de ativos.
- O novo arquivo `backend/app/services/recommended_portfolio_engine.py` consolida Screener Alpha B3, FIIs, Global, Crypto Research, Alpha Confidence, Global Backtest e Strategy Engine 2.0.
- A saida e o payload aditivo `recommendedPortfolioReport`, consumido pela tela `frontend/src/pages/ModelPortfolios.jsx`.
- Rotas novas: `GET /api/model-portfolios/recommended-report` e `POST /api/model-portfolios/recommended-report/run`.
- O relatorio contem score institucional, classificacao, risco agregado, resumo executivo, blocos de carteira, relatorio por ativo, evidencias, matriz de risco e checklist de revisao mensal.
- A revisao mensal deve recalcular precos, fundamentos, proventos, eventos corporativos, FIIs, global, cripto, concentracao e mudanca de tese.
- Linguagem continua protegida: o motor explica tese, risco e evidencia, mas nao emite ordem automatica nem promete rentabilidade.

### Decisao: Alertas como centro operacional do Alpha Intelligence

Motivo:

- O Resumo Inteligente exibe contagem de eventos importantes; esses eventos precisam ser rastreaveis em uma tela operacional.
- A rota `GET /api/alerts` passou a consolidar alertas persistidos, eventos importantes do Event Engine, insights acionaveis e itens do Guardian.
- A aba `Alertas` agora exibe `Monitoramento Alpha`, com eventos, impacto, acao sugerida, origem e severidade.
- Itens sinteticos do Alpha sao `readOnly` e recalculados ao abrir/atualizar a tela; alertas manuais continuam podendo ser marcados como lidos.
- Alertas precisam falar com investidor final, nao com desenvolvedor. Evitar jargoes como `motor`, `Score Alpha 2.0` sem contexto, ou justificativas internas longas.
- Ativos com classificacao neutra ou nota proxima da faixa media nao devem aparecer como `fora da faixa saudavel`.
- O Guardian so deve levantar revisao forte por ativo quando a nota estiver realmente abaixo do limite minimo operacional. Caso contrario, o correto e tratar como acompanhamento normal ou carteira em construcao.
- Quando um ativo fica abaixo dos criterios, o sistema deve usar linguagem de monitoramento: `entrou em revisao`, `revisar tese`, `avaliar reducao/substituicao em estudo`, nunca ordem automatica de compra ou venda.

### Decisao: Data Lineage expandido para os calculos visiveis

Motivo:

- Um produto patrimonial institucional precisa explicar a origem dos numeros antes de pedir confianca do usuario.
- A tabela `data_evidence_ledger` passa a cobrir tambem os resultados finais exibidos em tela, nao apenas dados brutos de provider.
- O novo arquivo `backend/app/services/data_lineage_integrations.py` registra evidencias para Dashboard, RDB/CDI, Projecoes, Impostos, Stress Test, Strategy Engine, Recommended Portfolio, Macro/FX e Alpha Copilot.
- As rotas continuam entregando os mesmos payloads principais, apenas com campo aditivo `dataLineage` quando a evidencia e gravada.
- `StatCard` ganhou parametros opcionais `evidenceDomain` e `evidenceField`, permitindo que cards financeiros exibam um botao discreto de origem do calculo.
- Regra daqui para frente: todo card financeiro critico deve informar dominio e campo do ledger, ou justificar tecnicamente por que ainda nao possui rastreabilidade.
- A rastreabilidade deve registrar formula, provider, source type, confidence, quality score, source ref e hash dos insumos; nunca gravar tokens ou secrets.

### Decisao: SQLite local e PostgreSQL planejado

Motivo:

- SQLite acelera preview local.
- PostgreSQL e o alvo correto para SaaS multiusuario em producao.

### Decisao: Alembic como fonte oficial do schema

Motivo:

- Permite evoluir o banco de forma rastreavel e reversivel.
- Evita depender de criacao automatica de tabelas em producao.
- Prepara o projeto para PostgreSQL, multiusuario real e novas fases globais.

### Decisao: Thesis Engine versionado no Alpha Premium Research

Motivo:

- Antes de criar Rating Engine e Research Committee, o sistema precisa guardar a tese historica de cada ativo.
- Uma carteira recomendada institucional nao pode apenas mostrar a tese atual; ela precisa provar o que era sabido, quais evidencias existiam, quais riscos estavam monitorados e quando a leitura mudou.
- O novo arquivo `backend/app/premium_research/thesis_engine.py` cria e atualiza teses por ativo sem depender da interface.
- A migration `backend/alembic/versions/20260714_0009_asset_thesis_engine.py` adiciona `asset_theses`, `asset_thesis_versions` e `asset_thesis_evidence`.
- `asset_theses` guarda a tese corrente por ativo, classe e tipo.
- `asset_thesis_versions` guarda cada versao com hash, texto da tese, papel na carteira, evidencias, riscos, gatilhos de invalidacao, confianca, conviccao, peso-alvo e periodo de vigencia.
- `asset_thesis_evidence` liga cada versao ao `Data Evidence Ledger`, mantendo rastreabilidade de fonte, provider, formula, confidence e status.
- O `AlphaResearchPublisher` passou a chamar o Thesis Engine ao gerar um rascunho premium, criando `thesisSync` no payload interno da versao da publicacao.
- Regra de compatibilidade: nenhuma tela, rota publica, payload antigo, calculo financeiro ou carteira do usuario foi alterada.
- Rollback seguro: `alembic downgrade 20260714_0008`.
- Documentacao especifica: `docs/THESIS_ENGINE.md`.

Regra:

- Rating Engine e Research Committee devem consumir teses versionadas, nao textos soltos da interface.
- Toda mudanca de tese deve gerar nova versao com motivo, hash e evidencias.
- Nenhuma tese versionada deve ser tratada como publicacao aprovada sem fluxo posterior de revisao humana.

### Decisao: Rating Engine baseado em teses versionadas

Motivo:

- Antes do Research Committee, o sistema precisa transformar cada tese versionada em rating institucional auditavel.
- Rating nao deve nascer de texto solto da interface, nem de payload temporario.
- O novo arquivo `backend/app/premium_research/rating_engine.py` consome `asset_thesis_versions` como origem obrigatoria.
- A migration `backend/alembic/versions/20260714_0010_asset_rating_engine.py` adiciona `asset_ratings`, `asset_rating_versions` e `asset_rating_evidence`.
- `asset_ratings` guarda o rating atual por ativo, classe e tipo.
- `asset_rating_versions` guarda cada versao do rating, com `source_thesis_hash`, `thesis_version_id`, componentes, rating, classificacao, resumo, limites, pontos de atencao e periodo de vigencia.
- `asset_rating_evidence` liga cada componente do rating ao `Data Evidence Ledger`.
- O `AlphaResearchPublisher` passou a chamar o Rating Engine depois do Thesis Engine, gerando `ratingSync` no payload interno da versao da publicacao.
- Regra de compatibilidade: nenhuma tela, rota publica, payload antigo, calculo financeiro ou carteira do usuario foi alterada.
- Rollback seguro: `alembic downgrade 20260714_0009`.
- Documentacao especifica: `docs/RATING_ENGINE.md`.

Formula:

```text
score_final =
  thesis_score       * 0.18 +
  evidence_score     * 0.16 +
  risk_score         * 0.16 +
  conviction_score   * 0.15 +
  confidence_score   * 0.15 +
  data_quality_score * 0.10 +
  governance_score   * 0.06 +
  suitability_score  * 0.04
```

Regra:

- Rating Engine deve usar a tese versionada vigente ou a tese criada pela publicacao premium.
- Rating Engine deve registrar evidencia por componente.
- Research Committee deve consumir ratings versionados, nao recalcular notas diretamente a partir da interface.
- Rating analitico nao e ordem automatica de compra ou venda.

### Decisao: Research Committee como gate institucional

Motivo:

- Antes de qualquer tese virar publicacao premium aprovada, o sistema precisa de um gate formal entre Thesis Engine, Rating Engine, Data Confidence, Guardian e Evidence Ledger.
- O novo arquivo `backend/app/premium_research/research_committee.py` consome `asset_thesis_versions`, `asset_rating_versions`, evidencias ligadas e readiness editorial.
- A migration `backend/alembic/versions/20260714_0011_research_committee.py` adiciona `research_committee_runs`, `research_committee_gate_results` e `research_committee_votes`.
- `research_committee_runs` guarda decisao, score, bloqueios, avisos e resumo humano.
- `research_committee_gate_results` guarda o resultado dos gates `thesis_coverage`, `rating_coverage`, `evidence_ledger`, `data_confidence`, `guardian_risk`, `publication_readiness` e `legal_safety`.
- `research_committee_votes` guarda votos dos motores `thesis_engine`, `rating_engine`, `data_confidence`, `guardian` e `evidence_ledger`.
- O `AlphaResearchPublisher` passou a chamar o Research Committee depois do Thesis Engine, Rating Engine, evidencias do publisher e readiness report, gravando `researchCommittee` no payload interno da versao da publicacao.
- O comite tambem grava uma evidencia `research_committee.approval_score` no Data Evidence Ledger.
- Regra de compatibilidade: nenhuma tela, rota publica, payload antigo, calculo financeiro ou carteira do usuario foi alterada.
- Rollback seguro: `alembic downgrade 20260714_0010`.
- Documentacao especifica: `docs/RESEARCH_COMMITTEE.md`.

Decisoes:

```text
approved_for_review -> pode ir para revisao humana
needs_review        -> pode ser revisado com pontos de atencao
request_changes     -> precisa de ajuste antes da revisao final
blocked             -> nao deve avancar como publicacao premium
```

Regra:

- Qualquer gate ou voto `block` bloqueia a publicacao premium.
- Avisos e baixa confianca podem solicitar ajustes.
- O comite nunca publica automaticamente.
- Aprovacao final continua sendo humana via fluxo de revisao/aprovacao.

### Decisao: API administrativa protegida do Alpha Premium Research

Motivo:

- Depois de Publisher, Thesis Engine, Rating Engine e Research Committee, era necessario expor uma camada operacional protegida para desenvolvedores e futuras telas administrativas.
- O novo arquivo `backend/app/routers/premium.py` registra rotas sob `/api/premium`.
- Todas as rotas usam `get_current_user`.
- A partir da fase `Premium RBAC e Area do Assinante`, rotas administrativas da vertical premium exigem papeis operacionais (`admin`, `editor` ou `reviewer`), enquanto a area do assinante consome endpoints separados.
- A API permite criar rascunho premium, listar/detalhar publicacoes, consultar versoes, sincronizar teses, sincronizar ratings, rodar Research Committee e consultar teses/ratings/rodadas.
- `app/main.py` passou a incluir `premium.router`.
- Mutacoes registram eventos de auditoria especificos e tambem sao cobertas pelo middleware de auditoria HTTP quando habilitado.
- Regra de compatibilidade: nenhuma tela existente, rota existente, payload antigo, calculo financeiro ou carteira do usuario foi alterada.
- Documentacao especifica: `docs/PREMIUM_RESEARCH_API.md`.

Rotas principais:

```text
POST /api/premium/publications/drafts
GET  /api/premium/publications
GET  /api/premium/publications/{publication_id}
GET  /api/premium/publications/{publication_id}/versions/{version_id}
POST /api/premium/publications/{publication_id}/theses/sync
POST /api/premium/publications/{publication_id}/ratings/sync
POST /api/premium/publications/{publication_id}/committee/run
POST /api/premium/publications/{publication_id}/reviews
POST /api/premium/publications/{publication_id}/approvals
GET  /api/premium/committee/runs
GET  /api/premium/committee/runs/{run_id}
POST /api/premium/publications/{publication_id}/attribution/run
GET  /api/premium/attribution/runs
GET  /api/premium/attribution/runs/{run_id}
GET  /api/premium/theses
GET  /api/premium/ratings
```

### Decisao: Performance Attribution Engine para Research Premium

Motivo:

- A edicao premium precisa explicar performance sem confundir aporte, preco e renda.
- A atribuicao deve ser versionada por publicacao e por versao, nao calculada de forma solta na interface.
- Cada numero central deve ter evidencia no Data Evidence Ledger.
- O motor deve funcionar mesmo quando provider externo falha, marcando fallback e reduzindo qualidade do dado.

Arquivos:

- `backend/app/premium_research/performance_attribution.py`
- `backend/alembic/versions/20260714_0012_performance_attribution.py`
- `docs/PERFORMANCE_ATTRIBUTION_ENGINE.md`

Tabelas:

- `research_attribution_runs`
- `research_attribution_assets`

Formula resumida:

```text
retorno_preco_% = ((preco_final / preco_inicial) - 1) * 100
retorno_renda_% = dividend_yield_anual * dias / 365
retorno_total_% = retorno_preco_% + retorno_renda_%
contribuicao_% = peso_normalizado * retorno_total_% / 100
retorno_carteira_% = soma(contribuicao_%)
```

Compatibilidade:

- Nenhuma tela existente foi alterada.
- Nenhum payload antigo foi removido.
- A rota nova e protegida por autenticacao.
- Rollback Alembic `20260714_0012 -> 20260714_0011` validado.

### Decisao: fluxo humano inicial do Premium Research

Motivo:

- A vertical premium nao pode permitir aprovacao automatica de tese ou publicacao.
- Foram adicionados endpoints protegidos para registrar revisao humana e aprovacao/rejeicao final usando as tabelas existentes `publication_reviews` e `publication_approvals`.
- `approve_publication` exige revisao humana aprovada para a mesma versao.
- `approve_publication` exige rodada do Research Committee.
- `approve_publication` e bloqueado quando o Research Committee retorna `blocked` ou possui bloqueios ativos.
- A tela `frontend/src/pages/PremiumResearch.jsx` opera o fluxo inicial sem alterar telas existentes.
- O menu lateral recebeu a entrada `Research Premium` no grupo `Inteligencia`.
- Mutacoes registram auditoria em `premium_research_review_recorded` e `premium_research_approval_recorded`.
- Regra de compatibilidade: nenhuma rota existente, payload antigo, calculo financeiro ou carteira do usuario foi alterada.

Fluxo:

```text
Criar rascunho
-> sincronizar teses
-> sincronizar ratings
-> rodar Research Committee
-> revisao humana
-> aprovacao ou rejeicao final
```

### Decisao: Publication Snapshot Engine para edicoes premium

Motivo:

- Depois de uma edicao premium ser aprovada, o sistema precisa congelar exatamente o que foi aprovado.
- PDF, web, entrega por e-mail, correcoes e auditoria futura nao podem depender de dados vivos que mudam com o tempo.
- O snapshot preserva payload canonico, manifest, secoes, ativos, fontes, evidencias, Research Committee, Performance Attribution, revisao, aprovacao e aviso legal.
- A edicao final ganha hash SHA-256 e evidencia no Data Evidence Ledger.

Arquivos:

- `backend/app/premium_research/snapshot_engine.py`
- `backend/alembic/versions/20260714_0013_publication_snapshots.py`
- `docs/PUBLICATION_SNAPSHOT_ENGINE.md`

Tabela:

- `publication_snapshots`

Regra:

```text
snapshot final = publicacao approved + versao approved + revisao humana approve + aprovacao final approve_publication
```

Hashes:

```text
content_hash  = publicacao + versao + secoes + ativos
source_hash   = fontes + evidencias
evidence_hash = evidencias
approval_hash = revisao + aprovacao + comite
snapshot_hash = payload canonico completo
```

APIs:

```text
POST /api/premium/publications/{publication_id}/snapshots
GET  /api/premium/publications/{publication_id}/snapshots
GET  /api/premium/snapshots
GET  /api/premium/snapshots/{snapshot_id}
```

Compatibilidade:

- Nenhuma tela foi alterada.
- Nenhum payload legado foi removido.
- Nenhum calculo financeiro foi alterado.
- Rollback Alembic: `20260714_0013 -> 20260714_0012`.

### Decisao: Publication Render Engine para HTML premium reproduzivel

Motivo:

- Depois do snapshot aprovado, o sistema precisa gerar um artefato visual que possa virar PDF/web sem depender dos dados vivos.
- O HTML premium deve representar exatamente a edicao congelada, incluindo fontes, evidencias, comite, revisao, aprovacao e aviso legal.
- O artefato precisa ter hash proprio, manifest e evidencia no Data Evidence Ledger.
- Renderizacao repetida do mesmo snapshot, tipo e versao deve ser idempotente.

Arquivos:

- `backend/app/premium_research/renderer.py`
- `backend/alembic/versions/20260714_0014_publication_artifacts.py`
- `docs/PUBLICATION_RENDER_ENGINE.md`

Tabela:

- `publication_artifacts`

Regra:

```text
artifact HTML = snapshot com integridade ok + artifact_type + render_version
```

Hash:

```text
artifact_hash = sha256(render_version + artifact_type + snapshot_hash + html_content)
```

APIs:

```text
POST /api/premium/snapshots/{snapshot_id}/render
GET  /api/premium/publications/{publication_id}/artifacts
GET  /api/premium/snapshots/{snapshot_id}/artifacts
GET  /api/premium/artifacts
GET  /api/premium/artifacts/{artifact_id}
```

Compatibilidade:

- Nenhuma tela foi alterada.
- Nenhum payload legado foi removido.
- Nenhum calculo financeiro foi alterado.
- Rollback Alembic: `20260714_0014 -> 20260714_0013`.

### Decisao: Publication PDF Publisher para PDF binario premium

Motivo:

- O produto premium precisa gerar um PDF baixavel e auditavel a partir da edicao aprovada.
- O PDF deve nascer do HTML premium ja renderizado, preservando `source_artifact_id`, hash do HTML e hash do snapshot.
- O PDF precisa guardar bytes, tamanho, paginas, hash proprio e evidencia no Data Evidence Ledger.
- A rota de download deve devolver `application/pdf` e nao embutir binario em JSON.

Arquivos:

- `backend/app/premium_research/pdf_publisher.py`
- `backend/alembic/versions/20260714_0015_publication_pdf_artifacts.py`
- `docs/PUBLICATION_PDF_PUBLISHER.md`

Tabela:

- `publication_artifacts`

Campos adicionados:

- `source_artifact_id`
- `binary_content`
- `content_size_bytes`
- `page_count`

Regra:

```text
artifact PDF = artifact HTML aprovado + snapshot com integridade ok + pdf_version
```

Hash:

```text
artifact_hash = sha256(pdf_version + html_artifact_hash + snapshot_hash + pdf_bytes)
```

APIs:

```text
POST /api/premium/artifacts/{artifact_id}/pdf
GET  /api/premium/artifacts/{artifact_id}/download
```

Compatibilidade:

- Nenhuma tela foi alterada.
- Nenhum payload legado foi removido.
- Nenhum calculo financeiro foi alterado.
- Rollback Alembic: `20260714_0015 -> 20260714_0014`.

### Decisao: Premium Entitlements Engine para acesso premium auditavel

Motivo:

- A vertical premium precisa controlar quem pode acessar e baixar publicacoes pagas.
- O controle deve ficar no backend, nunca no frontend.
- O PDF premium precisa ter gate de permissao, logs de tentativas e caminho futuro para pagamento real.
- A implementacao deve ser aditiva e nao alterar layout, calculos financeiros ou payloads existentes.

Arquivos:

- `backend/app/premium_research/entitlements.py`
- `backend/alembic/versions/20260714_0016_premium_entitlements.py`
- `backend/tests/test_premium_entitlements.py`
- `docs/PREMIUM_ENTITLEMENTS_ENGINE.md`

Tabelas:

- `subscription_plans`
- `user_subscriptions`
- `premium_entitlements`
- `premium_access_logs`

Regra:

```text
download PDF = usuario autenticado + (dono editorial ou entitlement ativo)
```

Entitlements aceitos para download:

- `premium.pdf.download`
- `premium.pdf.bulk_download`
- `premium.research.admin`

APIs:

```text
POST /api/premium/plans/seed
GET  /api/premium/plans
POST /api/premium/subscriptions/grant
GET  /api/premium/subscriptions/me
GET  /api/premium/access-logs
GET  /api/premium/artifacts/{artifact_id}/download
```

Compatibilidade:

- Nenhuma tela foi alterada.
- Nenhum payload legado foi removido.
- Nenhum calculo financeiro foi alterado.
- A geracao de PDF continua separada da permissao de download.
- Rollback Alembic: `20260714_0016 -> 20260714_0015`.

### Decisao: Premium RBAC e Area do Assinante

Motivo:

- O produto premium precisa separar operador editorial de assinante.
- A tela administrativa nao deve ser a experiencia do assinante final.
- O backend precisa decidir permissao por papel, nao por botao escondido no frontend.
- Usuarios antigos precisam continuar com acesso para evitar bloqueio no ambiente local.

Arquivos:

- `backend/app/services/rbac.py`
- `backend/alembic/versions/20260714_0017_user_roles_rbac.py`
- `backend/app/routers/premium.py`
- `backend/app/routers/auth.py`
- `frontend/src/pages/PremiumSubscriber.jsx`
- `docs/PREMIUM_RBAC_SUBSCRIBER_AREA.md`

Tabela:

- `user_roles`

Papeis:

- `admin`
- `editor`
- `reviewer`
- `premium_subscriber`
- `free_user`

APIs:

```text
GET  /api/premium/rbac/me
POST /api/premium/rbac/roles/grant
GET  /api/premium/subscriber/home
```

Regras:

- Usuarios existentes recebem `admin` via migration aditiva.
- Novos usuarios recebem `free_user` quando ainda nao possuem papel.
- Rotas editoriais premium exigem papel operacional.
- `Research Premium` fica oculto no menu para usuario sem papel editorial.
- `Area Premium` mostra plano, permissoes, edicoes aprovadas, PDFs e logs.
- Concessao manual de assinatura agora exige `admin`.

Compatibilidade:

- Nenhum calculo financeiro foi alterado.
- Nenhum payload financeiro legado foi removido.
- Download de PDF continua protegido por entitlement.
- Rollback Alembic: `20260714_0017 -> 20260714_0016`.

### Decisao: Payment Gateway desacoplado

Motivo:

- O sistema precisa vender assinatura premium sem expor credenciais de pagamento no frontend.
- Pagamento, assinatura, RBAC e entitlement devem continuar separados.
- O gateway precisa aceitar Stripe/Mercado Pago no futuro sem reescrever a Area Premium.
- Webhooks precisam ser idempotentes e auditaveis.

Arquivos:

- `backend/app/billing/gateway.py`
- `backend/app/routers/billing.py`
- `backend/alembic/versions/20260714_0018_billing_payment_gateway.py`
- `frontend/src/pages/PremiumSubscriber.jsx`
- `docs/PAYMENT_GATEWAY.md`

Tabelas:

- `billing_checkout_sessions`
- `billing_transactions`
- `billing_webhook_events`

APIs:

```text
POST /api/billing/checkout/sessions
POST /api/billing/mock/checkout/{session_id}/success
POST /api/billing/webhooks/{provider}
GET  /api/billing/me
GET  /api/billing/admin/webhook-events
```

Regras:

- O provider padrao local e `mock`.
- Webhook com assinatura invalida nao ativa assinatura.
- Pagamento aprovado chama `grant_subscription_to_user`, que sincroniza entitlements e papel `premium_subscriber`.
- `GET /api/billing/admin/webhook-events` exige `admin`.
- Rollback Alembic: `20260714_0018 -> 20260714_0017`.

### Decisao: Distribution Engine auditavel

Motivo:

- Edicoes premium precisam ser entregues a assinantes sem misturar envio com publicacao, pagamento ou entitlement.
- Cada envio precisa ser auditavel: campanha, destinatario, status e evento.
- O sistema precisa testar localmente sem disparar email real.

Arquivos:

- `backend/app/distribution/engine.py`
- `backend/app/distribution/providers.py`
- `backend/app/distribution/templates.py`
- `backend/app/routers/distribution.py`
- `backend/alembic/versions/20260714_0019_distribution_engine.py`
- `frontend/src/pages/PremiumResearch.jsx`
- `docs/DISTRIBUTION_ENGINE.md`

Tabelas:

- `distribution_campaigns`
- `distribution_recipients`
- `distribution_event_logs`

APIs:

```text
POST /api/distribution/campaigns
POST /api/distribution/campaigns/{campaign_id}/dispatch
GET  /api/distribution/campaigns
GET  /api/distribution/campaigns/{campaign_id}
POST /api/distribution/webhooks/{provider}
```

Regras:

- Criacao e disparo exigem papel editorial.
- Audiencia `premium_subscribers` usa `premium_entitlements` ativos.
- Provider local e `mock`.
- Providers preparados: `resend` e `smtp`.
- Se provider externo estiver configurado sem credenciais, a engine usa `mock` e registra `fallbackReason`.
- O template de envio gera HTML, texto simples, preview, disclaimer e controle de integridade do artefato.
- Webhook com assinatura invalida e rejeitado quando segredo estiver configurado.
- Rollback Alembic: `20260714_0019 -> 20260714_0018`.

### Decisao: Notification Center / Subscriber Delivery Inbox

Motivo:

- O assinante precisa ver dentro da Area Premium quais edicoes recebeu, abriu, clicou, baixou ou ainda estao pendentes.
- A tela deve reutilizar dados auditaveis do Distribution Engine e do Premium Entitlements Engine, sem criar uma segunda fonte de verdade.

Arquivos:

- `backend/app/distribution/inbox.py`
- `backend/app/routers/premium.py`
- `frontend/src/pages/PremiumSubscriber.jsx`
- `docs/NOTIFICATION_CENTER.md`

APIs:

```text
GET /api/premium/subscriber/delivery-inbox
GET /api/premium/subscriber/home
```

Regras:

- O inbox filtra entregas por `user_id` ou e-mail do assinante autenticado.
- Status de envio vem de `distribution_recipients`.
- Downloads confirmados vêm de `premium_access_logs`.
- O botao de download continua usando a rota protegida por entitlement.
- Nenhuma permissao premium e concedida pelo inbox; ele apenas mostra o estado consolidado.

### Decisao: Asset Engine aditivo

Motivo:

- Expande o modelo para ativos globais sem quebrar o sistema atual.
- Preserva campos antigos e payloads atuais.
- Permite que cripto, ETFs, acoes brasileiras e ativos internacionais futuros usem a mesma base conceitual.
- Cria rollback seguro para voltar ao schema `20260709_0001` se necessario.

## Roadmap tecnico sugerido

Prioridade alta:

- Criar testes automatizados para migracoes, calculos de carteira, scoring e projections.
- Persistir historico diario de patrimonio e score.
- Criar tela especifica de timeline.
- Criar tela especifica de saude da carteira.

Prioridade media:

- Integrar provider Brapi com atualizacao real de cotacoes.
- Criar jobs de sincronizacao de mercado.
- Adicionar importacao de notas ou planilhas.
- Criar controle de assinatura/planos SaaS.
- Adicionar auditoria de eventos.

Prioridade futura:

- Integrar Alpha Copilot com LLM.
- Criar explainability completa por pergunta.
- Criar alertas automaticos com base em jobs.
- Criar multi-carteiras por usuario.
