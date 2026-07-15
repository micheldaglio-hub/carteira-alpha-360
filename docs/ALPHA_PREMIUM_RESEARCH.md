# Alpha Premium Research

Status: Fase A/B/C/F/G tecnica em andamento. Contratos, migrations aditivas, AlphaResearchPublisher sem UI, Thesis Engine versionado, Rating Engine, Research Committee, Performance Attribution Engine, Publication Snapshot Engine, Publication Render Engine, Publication PDF Publisher, Premium Entitlements Engine, RBAC, Area Premium do Assinante, Payment Gateway, Distribution Engine com providers e Notification Center implementados.

Data: 2026-07-14

## Objetivo

O Alpha Premium Research e a nova vertical futura do Carteira Alpha 360.

Ele transforma o Wealth OS em uma plataforma tambem capaz de produzir pesquisa financeira premium, portflios-modelo, edicoes mensais, newsletter, publicacao web, PDF, historico auditavel e distribuicao para assinantes.

Esta fase deixou de ser apenas documental em 2026-07-14. A Fase A/B/C/F/G tecnica criou contratos internos, modelos SQLAlchemy, migrations Alembic aditivas, o primeiro servico `AlphaResearchPublisher` sem UI, a fundacao do `Thesis Engine` versionado, o `Rating Engine` baseado em teses versionadas, o `Research Committee` como gate institucional antes de revisao humana, o `Performance Attribution Engine` para explicar retorno de edicoes premium por ativo, fonte e qualidade dos dados, o `Publication Snapshot Engine` para congelar edicoes aprovadas com hash canonico, o `Publication Render Engine` para gerar HTML premium reproduzivel a partir do snapshot, o `Publication PDF Publisher` para gerar PDF binario auditavel, o `Premium Entitlements Engine` para controlar planos, assinaturas, permissoes e downloads, a fundacao de RBAC + Area Premium do Assinante, o `Payment Gateway` para checkout, webhook e ativacao de assinatura, o `Distribution Engine` para campanhas, destinatarios, eventos de entrega, templates e providers `mock`, `resend` e `smtp`, e o `Notification Center` para o assinante acompanhar entregas e downloads.

Ainda nao implementa cobranca real em Stripe/Mercado Pago, entrega por e-mail ou publicacao automatica. O gateway existe com provider `mock` e contrato backend pronto para adaptadores externos.

Em 2026-07-14, endpoints administrativos protegidos foram adicionados em `/api/premium` para operar rascunhos, teses, ratings e Research Committee sem UI publica.

## Diagnostico da arquitetura atual

O sistema ja possui fundacao forte para reutilizar:

- Asset Engine Universal.
- Market Data Engine.
- Knowledge Engine.
- Global Portfolio Engine.
- Fixed Income Engine.
- Proventos Engine.
- Total Return Engine.
- Financial Projection Engine.
- Goal Engine.
- Strategy Engine 2.0.
- Recommended Portfolio Engine.
- Alpha Confidence Engine.
- Recommendation Governance Engine.
- Research & News Engine.
- Scenario & Stress Test Engine.
- Guardian.
- Event Engine 2.0.
- Macro / FX Engine.
- Tax Engine.
- Alpha Copilot.
- Data Confidence Engine V2.
- Data Lineage & Evidence Ledger.
- Financial Formula Auditor.
- Observabilidade, auditoria, jobs e preparo PostgreSQL/Supabase.

Conclusao: a nova vertical nao deve duplicar calculos. Ela deve organizar, versionar, revisar, aprovar e publicar dados e analises ja produzidos pelos motores existentes.

## Visao de produto

O Alpha Premium Research sera composto por duas experiencias:

1. Plataforma viva.
2. Edicao periodica.

A plataforma viva mostra atualizacoes continuas durante o mes:

- fundamentos;
- eventos corporativos;
- noticias relevantes;
- alteracoes de score;
- mudancas de risco;
- revisao de teses;
- proventos;
- valuation;
- alteracoes da carteira-modelo;
- alertas extraordinarios.

A edicao periodica consolida o mes:

- carta editorial;
- resumo executivo;
- carteira-modelo;
- entradas, saidas e mudancas de peso;
- performance;
- atribuicao de retorno;
- proventos;
- renda passiva;
- macro;
- stress test;
- teses;
- riscos;
- metodologia;
- fontes;
- evidencias;
- limitacoes;
- avisos legais.

## Principio obrigatorio

Nenhuma edicao premium podera ser publicada automaticamente.

Fluxo oficial:

```text
Dados
-> Normalizacao
-> Analise
-> Evidencias
-> Comite
-> Rascunho
-> Revisao humana
-> Aprovacao
-> Publicacao
```

A IA pode escrever rascunhos e explicar dados, mas nao pode aprovar, alterar decisoes, esconder lacunas ou publicar.

## Arquitetura proposta

```text
Alpha Premium Research
  -> Alpha Research Publisher
  -> Thesis Engine
  -> Revision Engine
  -> Rating Engine
  -> Alpha Research Committee
  -> Portfolio Constructor
  -> Performance Attribution Engine
  -> Editorial AI Engine
  -> Publication Workflow
  -> Publication Render Engine
  -> Publication PDF Publisher
  -> Web Publisher
  -> Premium Entitlements Engine
  -> Premium RBAC
  -> Area Premium do Assinante
  -> Subscription & Entitlements
  -> Compliance & Disclosure
```

## Modulos reutilizaveis

| Modulo atual | Uso na nova vertical |
| --- | --- |
| Asset Engine | Identidade universal dos ativos publicados. |
| Market Data Engine | Dados de mercado, historico, fundamentos, proventos e cambio. |
| Knowledge Engine | Dados tratados e organizados antes da analise editorial. |
| Research & News Engine | Centro de research, fatos, noticias, riscos e lacunas. |
| Recommended Portfolio Engine | Base da carteira-modelo Alpha. |
| Recommendation Governance Engine | Revisao mensal, snapshots, gatilhos e governanca. |
| Alpha Confidence Engine | Confianca da carteira e dos ativos. |
| Data Confidence Engine V2 | Qualidade dos dados por campo. |
| Data Lineage & Evidence Ledger | Rastreabilidade obrigatoria dos numeros publicados. |
| Total Return Engine | Retorno total, separando preco, proventos e aportes. |
| Macro / FX Engine | Macro, juros, inflacao e cambio. |
| Scenario & Stress Test Engine | Choques e resiliencia da carteira-modelo. |
| Tax Engine | Impostos estimados e lacunas tributarias. |
| Alpha Copilot | Explicacao baseada em dados internos e citacoes. |
| Ops / Jobs / Audit | Execucao, logs, auditoria e trilha operacional. |

## Modulos novos propostos

### Alpha Research Publisher

Gerencia edicoes editoriais.

Estados:

- criada;
- coletando_dados;
- processando;
- rascunho;
- dados_pendentes;
- em_revisao;
- revisada;
- aprovada;
- publicada;
- corrigida;
- arquivada;
- cancelada.

### Thesis Engine

Mantem tese versionada por ativo.

Status tecnico em 2026-07-14: fundacao implementada sem UI em `backend/app/premium_research/thesis_engine.py`.

O motor grava uma tese mae por ativo e cria uma nova versao quando a leitura muda. Cada versao guarda hash, texto da tese, papel na carteira, resumo de evidencias, riscos, plano de monitoramento, gatilhos de invalidacao, confianca, conviccao, peso-alvo e links para o `Data Evidence Ledger`.

O `AlphaResearchPublisher` ja chama o Thesis Engine ao gerar um rascunho premium, para preservar a tese historica dos ativos do `recommendedPortfolioReport`.

Cada tese deve responder:

- por que o ativo entrou;
- qual papel cumpre;
- quais fundamentos sustentam;
- quais riscos existem;
- o que faria manter, reduzir ou sair;
- quais evidencias sustentam;
- quem revisou;
- quando mudou.

### Revision Engine

Executa revisoes periodicas e extraordinarias.

Saidas possiveis:

- tese mantida;
- tese fortalecida;
- tese enfraquecida;
- ativo em observacao;
- ativo em revisao;
- proposta de reducao;
- proposta de saida;
- dados adicionais necessarios.

### Rating Engine

Cria rating institucional por ativo.

Status tecnico em 2026-07-14: fundacao implementada sem UI em `backend/app/premium_research/rating_engine.py`.

O Rating Engine nao calcula em cima de texto solto. Ele usa `asset_thesis_versions` como origem obrigatoria, calcula componentes auditaveis e grava `asset_ratings`, `asset_rating_versions` e `asset_rating_evidence`.

Dimensoes:

- qualidade;
- perenidade;
- dividendos;
- crescimento;
- previsibilidade;
- governanca;
- moat;
- geracao de caixa;
- estrutura de capital;
- valuation;
- liquidez;
- risco;
- assimetria;
- confianca dos dados.

### Alpha Research Committee

Consolida votos dos motores.

Status tecnico em 2026-07-14: fundacao implementada sem UI em `backend/app/premium_research/research_committee.py`.

Participantes internos:

- Quality Engine;
- Dividend Engine;
- Growth Engine;
- Valuation Engine;
- Risk Engine;
- Guardian;
- Strategy Engine;
- Research Engine;
- Macro Engine;
- Confidence Engine;
- Data Confidence Engine;
- Recommendation Governance;
- Portfolio Constructor;
- Human Reviewer.

Nao usar media simples. Aplicar gates:

- risco critico bloqueia entrada;
- dado essencial incompleto impede alta conviccao;
- governanca fraca impede nucleo;
- baixa liquidez limita peso;
- concentracao limita entrada;
- score alto nao apaga risco extremo.

Gates tecnicos iniciais implementados:

- `thesis_coverage`: exige tese versionada;
- `rating_coverage`: exige rating calculado a partir da tese historica;
- `evidence_ledger`: exige evidencias rastreaveis;
- `data_confidence`: verifica qualidade dos dados usada pelo rating;
- `guardian_risk`: bloqueia rating restrito, risco extremo ou ativo fora dos criterios;
- `publication_readiness`: usa o readiness editorial da versao;
- `legal_safety`: confirma aviso legal e revisao humana obrigatoria.

Decisoes tecnicas:

- `approved_for_review`: pode ir para revisao humana;
- `needs_review`: pode ser revisado com pontos de atencao;
- `request_changes`: precisa de ajuste antes de revisao final;
- `blocked`: nao deve avancar como publicacao premium.

O comite nunca publica automaticamente.

### Portfolio Constructor

Monta carteira-modelo como estrutura coerente, nao como lista de melhores scores.

Controla:

- peso maximo por ativo;
- peso maximo por setor;
- peso maximo por classe;
- peso maximo por pais;
- peso maximo por moeda;
- peso maximo por tese;
- nucleo e satelites;
- especulativo;
- liquidez;
- qualidade;
- confianca;
- correlacao;
- diversificacao;
- aderencia estrategica.

### Performance Attribution Engine

Explica a performance por fonte.

Status tecnico em 2026-07-14: fundacao implementada sem UI em `backend/app/premium_research/performance_attribution.py`.

Separar:

- dinheiro novo;
- retorno de preco;
- proventos;
- efeito cambial;
- imposto;
- custos;
- alocacao;
- selecao;
- rebalanceamento.

Aporte nunca pode ser tratado como lucro.

A primeira entrega grava `research_attribution_runs` e `research_attribution_assets`, registra evidencias em `premium_research_attribution`, separa retorno de preco e renda estimada por yield, aceita benchmark opcional e marca fallback quando nao existe historico suficiente.

### Publication Snapshot Engine

Status tecnico em 2026-07-14: fundacao implementada sem UI em `backend/app/premium_research/snapshot_engine.py`.

O motor cria um pacote imutavel da edicao aprovada. Ele captura publicacao, versao, secoes, ativos, fontes, evidencias, Research Committee, Performance Attribution, revisao humana, aprovacao final e aviso legal, gerando hashes SHA-256 para conteudo, fontes, evidencias, aprovacao e payload canonico completo.

Regra principal:

- snapshot final exige revisao humana aprovada e aprovacao final;
- um snapshot por `publication_version_id + snapshot_type`;
- chamada repetida e idempotente;
- o hash do snapshot e registrado no Data Evidence Ledger;
- o snapshot nao publica, nao envia e-mail e nao gera PDF.

### Publication Render Engine

Status tecnico em 2026-07-14: fundacao implementada sem UI em `backend/app/premium_research/renderer.py`.

O motor transforma um `PublicationSnapshot` travado em um artefato HTML premium, pronto para impressao e para uma etapa futura de PDF. Ele nunca busca dado vivo de mercado, carteira, noticia ou score. A fonte unica e o `payload_json` do snapshot aprovado.

Regra principal:

- renderizacao exige snapshot com integridade `ok`;
- um artefato por `snapshot_id + artifact_type + render_version`;
- chamada repetida e idempotente;
- o HTML guarda hashes do snapshot, conteudo, fontes, evidencias e aprovacao;
- o hash do artefato e registrado no Data Evidence Ledger;
- o motor nao envia, nao cobra, nao libera acesso e nao publica automaticamente.

### Publication PDF Publisher

Status tecnico em 2026-07-14: fundacao implementada sem UI em `backend/app/premium_research/pdf_publisher.py`.

O motor gera um PDF binario a partir do artefato HTML premium ja renderizado. O PDF herda o snapshot de origem, registra `source_artifact_id`, guarda bytes em `publication_artifacts.binary_content`, calcula hash proprio e registra evidencia `premium_research_pdf.pdf_hash`.

Regra principal:

- PDF nasce apenas de artefato `html` ou `html_print`;
- snapshot de origem precisa ter integridade `ok`;
- chamada repetida e idempotente para o mesmo HTML e versao do PDF;
- download binario protegido por autenticacao e, para assinantes, entitlement ativo;
- o motor nao envia e-mail, nao cobra e nao publica automaticamente.

### Premium Entitlements Engine

Status tecnico em 2026-07-14: fundacao implementada sem UI em `backend/app/premium_research/entitlements.py`.

O motor controla planos, assinaturas, permissoes de acesso e logs de download da vertical premium. Ele prepara a area de assinantes sem expor gateway de pagamento real e sem alterar a UI atual.

Regra principal:

- planos padrao sao sincronizados de forma idempotente;
- assinatura manual cria entitlements ativos por periodo;
- download de PDF exige dono editorial ou entitlement ativo;
- tentativas permitidas e negadas sao gravadas em `premium_access_logs`;
- a camada ainda nao cobra, nao envia e-mail e nao cria area visual de assinantes.

### Premium RBAC e Area do Assinante

Status tecnico em 2026-07-14: fundacao implementada em `backend/app/services/rbac.py` e `frontend/src/pages/PremiumSubscriber.jsx`.

O RBAC separa operador editorial de assinante. A area do assinante consome apenas dados prontos para usuario final: plano, permissoes, edicoes aprovadas, PDFs liberados e logs de acesso.

Papeis iniciais:

- `admin`;
- `editor`;
- `reviewer`;
- `premium_subscriber`;
- `free_user`.

Regra principal:

- `Research Premium` exige papel editorial;
- `Area Premium` fica disponivel ao usuario autenticado;
- rotas de criacao, revisao, aprovacao, snapshot, HTML e PDF exigem papel operacional;
- concessao manual de assinatura exige `admin`;
- download segue protegido por entitlement ativo ou acesso editorial/admin.

### Editorial AI Engine

Gera rascunhos a partir de dados preparados pelo backend.

Pode:

- escrever primeiro rascunho;
- resumir mudancas;
- explicar metricas em texto humano;
- sugerir titulos;
- revisar tom;
- regenerar secao;
- preparar carta editorial.

Nao pode:

- inventar numero;
- consultar fonte sem registro;
- alterar decisao do comite;
- publicar;
- esconder limitacoes;
- afirmar certeza;
- usar dado sem Data Lineage.

## Modelo conceitual

```text
ResearchPublication
  -> PublicationVersion
    -> PublicationSection
    -> PublicationAsset
    -> PublicationSource
    -> PublicationEvidence
    -> PublicationReview
    -> PublicationApproval
    -> PublicationCorrection

AssetThesis
  -> AssetThesisVersion

ResearchCommitteeRun
  -> ResearchCommitteeVote

AssetRating

PortfolioModelVersion
  -> PortfolioModelPosition
  -> PortfolioChange

PerformanceAttribution

SubscriptionPlan
  -> Subscription
  -> Entitlement

PublicationDelivery
PublicationDownload
ComplianceDisclosure
```

## Tabelas propostas

Fase A tecnica criou as tabelas base do Alpha Research Publisher:

- `research_publications`
- `publication_versions`
- `publication_sections`
- `publication_assets`
- `publication_sources`
- `publication_evidence`
- `publication_reviews`
- `publication_approvals`
- `publication_corrections`

Fase B tecnica iniciou o Thesis Engine versionado com:

- `asset_theses`
- `asset_thesis_versions`
- `asset_thesis_evidence`

Fase B tecnica tambem iniciou o Rating Engine com:

- `asset_ratings`
- `asset_rating_versions`
- `asset_rating_evidence`

Fase B tecnica tambem iniciou o Research Committee com:

- `research_committee_runs`
- `research_committee_gate_results`
- `research_committee_votes`

Fase C tecnica iniciou o Performance Attribution Engine com:

- `research_attribution_runs`
- `research_attribution_assets`

Fase C tecnica tambem iniciou o Publication Snapshot Engine com:

- `publication_snapshots`

Fase C tecnica tambem iniciou o Publication Render Engine com:

- `publication_artifacts`

Fase C tecnica tambem iniciou o Publication PDF Publisher adicionando em `publication_artifacts`:

- `source_artifact_id`
- `binary_content`
- `content_size_bytes`
- `page_count`

Fase C tecnica tambem iniciou o Premium Entitlements Engine com:

- `subscription_plans`
- `user_subscriptions`
- `premium_entitlements`
- `premium_access_logs`

Fase F tecnica iniciou RBAC e Area do Assinante com:

- `user_roles`

Tabelas candidatas para fases posteriores:

- `portfolio_model_versions`
- `portfolio_model_positions`
- `portfolio_changes`
- `publication_deliveries`
- `compliance_disclosures`

## APIs propostas

Todas as rotas futuras devem ser autenticadas e versionadas.

Publisher:

- `GET /api/premium/publications`
- `POST /api/premium/publications`
- `GET /api/premium/publications/{id}`
- `POST /api/premium/publications/{id}/collect-data`
- `POST /api/premium/publications/{id}/generate-draft`
- `POST /api/premium/publications/{id}/submit-review`
- `POST /api/premium/publications/{id}/approve`
- `POST /api/premium/publications/{id}/publish`
- `POST /api/premium/publications/{id}/correct`
- `POST /api/premium/publications/{id}/archive`

Teses:

- `GET /api/premium/theses`
- `GET /api/premium/theses/{asset_id}`
- `POST /api/premium/theses/{asset_id}/versions`
- `POST /api/premium/theses/{asset_id}/review`

Comite:

- `POST /api/premium/committee/run`
- `GET /api/premium/committee/runs/{id}`
- `POST /api/premium/committee/runs/{id}/vote`

Attribution:

- `POST /api/premium/publications/{publication_id}/attribution/run`
- `GET /api/premium/attribution/runs`
- `GET /api/premium/attribution/runs/{run_id}`

Snapshots:

- `POST /api/premium/publications/{publication_id}/snapshots`
- `GET /api/premium/publications/{publication_id}/snapshots`
- `GET /api/premium/snapshots`
- `GET /api/premium/snapshots/{snapshot_id}`

Ratings:

- `GET /api/premium/ratings`
- `GET /api/premium/ratings/{asset_id}`
- `POST /api/premium/ratings/refresh`

Assinaturas:

- `POST /api/premium/plans/seed`
- `GET /api/premium/plans`
- `POST /api/premium/subscriptions/grant`
- `GET /api/premium/subscriptions/me`
- `GET /api/premium/access-logs`
- `GET /api/premium/rbac/me`
- `POST /api/premium/rbac/roles/grant`
- `GET /api/premium/subscriber/home`

Distribuicao:

- `POST /api/premium/publications/{id}/render/pdf`
- `POST /api/premium/publications/{id}/render/email`
- `POST /api/premium/publications/{id}/deliver`
- `GET /api/premium/publications/{id}/download`

## Paginas propostas

Area administrativa:

- Alpha Research Publisher.
- Edicoes.
- Editor de secao.
- Thesis Center.
- Rating Center.
- Committee Run.
- Publication Readiness.
- Evidencias da edicao.
- Correcoes e versoes.
- Distribuicao.
- Assinantes e planos.

Area do assinante:

- Home Premium.
- Edicao mais recente.
- Carteira Alpha atual.
- Historico de edicoes.
- Pagina de research por ativo.
- Mudancas do mes.
- Alertas premium.
- Download do PDF.

## Jobs propostos

- `premium.data_readiness`
- `premium.monthly_close`
- `premium.asset_revision`
- `premium.thesis_revision`
- `premium.rating_refresh`
- `premium.portfolio_proposal`
- `premium.committee_run`
- `premium.performance_attribution`
- `premium.newsletter_draft`
- `premium.pdf_render`
- `premium.publish`
- `premium.delivery`
- `premium.extraordinary_review`
- `premium.compliance_check`
- `premium.archival`
- `premium.link_validation`

Cada job deve ter:

- idempotencia;
- status;
- periodo;
- inicio;
- fim;
- erro;
- retry;
- log;
- evidencia;
- usuario responsavel quando aplicavel.

## Fluxo mensal proposto

D-5:

- verificar dados;
- atualizar precos;
- fundamentos;
- proventos;
- eventos;
- macro;
- noticias;
- lacunas.

D-3:

- recalcular ratings;
- revisar teses;
- riscos;
- confianca;
- stress test;
- attribution;
- proposta de carteira.

D-2:

- executar comite;
- registrar votos;
- analisar divergencias;
- gerar proposta de entradas, saidas e pesos;
- bloquear itens insuficientes.

D-1:

- gerar edicao;
- rascunho editorial;
- graficos;
- tabelas;
- revisar evidencias;
- revisar metodologia;
- revisao humana.

Dia 0:

- aprovacao final;
- gerar PDF;
- publicar web;
- enviar e-mail;
- registrar versao;
- snapshot imutavel;
- atualizar area premium.

Durante o mes:

- monitorar fatos materiais;
- emitir atualizacao extraordinaria;
- preservar historico.

## Quality gates de publicacao

Uma edicao nao pode ser publicada se:

- pesos nao somarem 100%;
- houver ativo duplicado;
- houver erro de formula;
- Financial Formula Auditor falhar;
- dado critico nao tiver fonte;
- secao critica tiver confianca abaixo do minimo;
- provider obrigatorio estiver indisponivel sem fallback controlado;
- tese nao tiver revisao;
- rating minimo estiver ausente;
- divergencia nao estiver analisada;
- aviso legal estiver ausente;
- aprovacao humana estiver ausente.

Criar `Publication Readiness Score`:

- `bloqueado`
- `incompleto`
- `pronto_para_revisao`
- `pronto_para_aprovacao`
- `pronto_para_publicacao`

## Fluxo de assinatura

Planos conceituais:

### Alpha Free

- conteudo limitado;
- amostra da carteira;
- resumo atrasado;
- educacao financeira.

### Alpha Premium

- carteira completa;
- teses;
- relatorio mensal;
- mudancas de peso;
- research;
- alertas;
- historico;
- stress test;
- proventos;
- evidencias resumidas.

### Alpha Institutional

- tudo do Premium;
- Data Lineage;
- Evidence Ledger;
- Attribution;
- exportacoes;
- API futura;
- historico integral;
- governanca detalhada.

Nao implementar cobranca antes de permissao, compliance e contratos.

## Controle de acesso futuro

Papeis:

- subscriber;
- premium_subscriber;
- institutional_subscriber;
- editor;
- analyst;
- reviewer;
- approver;
- administrator.

Permissoes:

- visualizar edicao;
- baixar PDF;
- visualizar carteira;
- visualizar teses;
- visualizar evidencias;
- editar edicao;
- aprovar;
- publicar;
- corrigir;
- administrar assinantes.

## Compliance

Antes de venda real, criar fase juridica especifica.

Preparar:

- termos de uso;
- politica de privacidade;
- metodologia publica;
- conflitos de interesse;
- posicao dos responsaveis;
- conteudo patrocinado;
- correcoes;
- registro de aprovacao;
- trilha editorial;
- retencao de registros.

Linguagem proibida:

- compre agora;
- venda agora;
- retorno garantido;
- vai subir;
- fique rico;
- sem risco;
- compra sem medo.

Usar enquanto nao houver validacao juridica:

- carteira-modelo;
- pesquisa;
- estudo;
- analise;
- conteudo informativo.

## Riscos

- Transformar newsletter em captura de tela em vez de produto editorial estruturado.
- Duplicar calculos ja existentes.
- Publicar textos de IA sem evidencia.
- Criar cobranca antes de compliance.
- Criar tese sem versionamento.
- Permitir alteracao silenciosa de publicacao passada.
- Misturar performance passada com promessa futura.
- Nao separar aporte, performance, renda, cambio, imposto e custo.
- Expor Data Lineage detalhado para plano errado.
- Publicar dado com fallback sem sinalizar.

## Dependencias

- PostgreSQL/Supabase para historico robusto e multiusuario.
- Jobs automaticos confiaveis.
- Data Lineage expandido para todos os campos publicados.
- Permission/Entitlement Engine.
- Template de PDF estruturado.
- Revisao juridica antes de comercializacao.
- Rotina de backup e snapshot imutavel.

## Criterios de aceite da Fase A

- Documento mestre criado.
- Roadmap atualizado.
- Produto atualizado.
- Visao 2035 atualizada.
- Mapa do sistema atualizado.
- Diagrama conceitual atualizado.
- Documentacao tecnica atualizada.
- Changelog atualizado.
- Contratos internos criados em `backend/app/premium_research/contracts.py`.
- Migration Alembic aditiva criada em `backend/alembic/versions/20260714_0008_alpha_research_publisher.py`.
- Migration Alembic aditiva do Thesis Engine criada em `backend/alembic/versions/20260714_0009_asset_thesis_engine.py`.
- Migration Alembic aditiva do Rating Engine criada em `backend/alembic/versions/20260714_0010_asset_rating_engine.py`.
- Migration Alembic aditiva do Research Committee criada em `backend/alembic/versions/20260714_0011_research_committee.py`.
- Migration Alembic aditiva do Performance Attribution Engine criada em `backend/alembic/versions/20260714_0012_performance_attribution.py`.
- Migration Alembic aditiva do Publication Snapshot Engine criada em `backend/alembic/versions/20260714_0013_publication_snapshots.py`.
- Migration Alembic aditiva do Publication Render Engine criada em `backend/alembic/versions/20260714_0014_publication_artifacts.py`.
- Migration Alembic aditiva do Publication PDF Publisher criada em `backend/alembic/versions/20260714_0015_publication_pdf_artifacts.py`.
- Migration Alembic aditiva do Premium Entitlements Engine criada em `backend/alembic/versions/20260714_0016_premium_entitlements.py`.
- Migration Alembic aditiva do Premium RBAC criada em `backend/alembic/versions/20260714_0017_user_roles_rbac.py`.
- Modelos SQLAlchemy aditivos criados em `backend/app/models.py`.
- Banco local preparado para revision `20260714_0017`, com rollback `0017 -> 0016` previsto pela migration.
- Nenhuma rota, tela ou regra financeira alterada.
- Plano dividido em fases pequenas, reversiveis e testaveis.

## Roadmap de implementacao

### Fase A - Arquitetura Editorial

Objetivo: documentar dominio, contratos, fluxos, quality gates e modelo conceitual.

Status: fundacao tecnica aditiva em andamento desde 2026-07-14.

Entregue:

- Contratos dataclass do Alpha Research Publisher.
- Maquina de estados de publicacao e transicoes explicitas.
- Classificacao de readiness da publicacao.
- Tabelas base para publicacao, versoes, secoes, ativos citados, fontes, evidencias, revisoes, aprovacoes e correcoes.
- Rollback Alembic seguro.
- Testes de compatibilidade da fundacao.
- Servico `AlphaResearchPublisher` sem UI em `backend/app/premium_research/publisher.py`.
- Geracao de rascunho premium com secoes editoriais, fontes internas, ativos citados, evidencias vinculadas ao Data Evidence Ledger e readiness report.
- Persistencia versionada sem sobrescrever rascunhos anteriores do mesmo periodo.
- Integracao aditiva com `Thesis Engine`: cada rascunho premium tambem versiona as teses dos ativos analisados.
- Integracao aditiva com `Rating Engine`: cada tese versionada do rascunho tambem gera rating institucional versionado.
- Integracao aditiva com `Research Committee`: cada rascunho premium roda gates de tese, rating, evidencia, data confidence, Guardian, readiness e aviso legal antes de seguir para revisao humana.
- API administrativa protegida `/api/premium` para criar rascunho, listar publicacoes, consultar versoes, sincronizar teses/ratings e executar o Research Committee.
- Fluxo humano inicial entregue: endpoints protegidos registram revisao, aprovacao e rejeicao final, respeitando bloqueios do Research Committee.
- Tela administrativa inicial `Research Premium` entregue no frontend para operar rascunhos, versoes, readiness, comite, revisao e aprovacao.
- Bloqueio conceitual: rascunho nao publica automaticamente e continua exigindo revisao humana.
- Performance Attribution mensal entregue sem UI: API protegida gera rodadas de atribuicao por publicacao premium, com retorno por ativo, contribuidores, detratores, benchmark opcional, avisos de fallback e evidencias no Data Evidence Ledger.
- Snapshot imutavel de edicao entregue sem UI: API protegida congela uma versao aprovada com payload canonico, manifest, hashes e evidencia no Data Evidence Ledger.
- Publication Render Engine entregue sem UI: API protegida gera HTML premium reproduzivel a partir do snapshot aprovado, grava `publication_artifacts` e evidencia `premium_research_artifact.artifact_hash`.
- Publication PDF Publisher entregue sem UI: API protegida gera PDF binario a partir do HTML aprovado, grava bytes, tamanho, paginas e evidencia `premium_research_pdf.pdf_hash`.
- Premium Entitlements Engine entregue sem UI: API protegida sincroniza planos, concede assinatura manual, lista permissoes, registra logs de acesso e protege download de PDF por entitlement.
- Premium RBAC e Area do Assinante entregues: papeis operacionais, backfill admin para usuarios existentes, menu filtrado por papel, endpoint do assinante e tela `Area Premium`.

### Fase B - Thesis, Rating e Committee

Objetivo: criar tese versionada, rating institucional e comite de motores.

Status: iniciada em 2026-07-14 com a entrega da fundacao do Thesis Engine, Rating Engine e Research Committee.

Entrega minima:

- modelos aditivos de tese;
- servico interno de versionamento;
- evidencias vinculadas ao Data Evidence Ledger;
- modelos aditivos de rating;
- rating institucional calculado a partir da tese versionada;
- modelos aditivos do comite;
- gates e votos institucionais antes da publicacao premium;
- sem tela nova, sem rota publica e sem publicacao automatica.

### Fase C - Attribution e Fechamento

Objetivo: criar fechamento mensal, snapshot e attribution.

Status: iniciada em 2026-07-14 com a fundacao do Performance Attribution Engine.

Entregue:

- performance attribution;
- snapshot imutavel de edicao;

Entrega restante:

- comparacao com benchmark.

### Fase D - Publisher

Objetivo: criar fluxo editorial com revisao e aprovacao humana.

Entrega minima:

- edicao;
- secoes;
- status;
- aprovacao;
- correcoes.

### Fase E - PDF e Web

Objetivo: renderizar edicao a partir de dados estruturados.

Entrega minima:

- HTML;
- PDF reproduzivel;
- versionamento;
- hash da edicao.

### Fase F - Assinantes

Objetivo: planos, permissoes e area premium.

Entrega minima:

- planos conceituais. Entregue como fundacao tecnica em 2026-07-14;
- entitlements. Entregue como fundacao tecnica em 2026-07-14;
- controle de acesso por recurso. Download de PDF protegido entregue em 2026-07-14;
- area visual do assinante. Entregue em 2026-07-14 como fundacao inicial e ampliada em 2026-07-15 com Notification Center.

### Fase G - Distribuicao

Objetivo: e-mail, download, notificacoes e metricas.

Entrega minima:

- entrega de edicao;
- historico;
- logs de download.

### Fase H - Compliance e Lancamento

Objetivo: preparar venda real com revisao juridica e piloto.

Entrega minima:

- termos;
- metodologia;
- disclosures;
- auditoria;
- piloto controlado.

## Ordem exata de implementacao apos aprovacao

1. Definir contratos pydantic/dataclasses da vertical premium. Entregue em 2026-07-14.
2. Criar migrations aditivas para publicacoes, versoes, secoes e evidencias. Entregue em 2026-07-14.
3. Criar `AlphaResearchPublisher` sem UI. Entregue em 2026-07-14.
4. Criar `Thesis Engine` versionado. Entregue em 2026-07-14 como fundacao sem UI.
5. Criar `Rating Engine` com formulas documentadas. Entregue em 2026-07-14 como fundacao sem UI.
6. Criar `Research Committee` com gates entre Thesis, Rating, Data Confidence, Guardian e Evidence Ledger. Entregue em 2026-07-14 como fundacao sem UI.
7. Criar endpoints administrativos protegidos. Entregue em 2026-07-14 como fundacao sem UI.
8. Criar tela administrativa inicial. Entregue em 2026-07-14.
9. Criar Performance Attribution mensal. Entregue em 2026-07-14 como fundacao sem UI.
10. Criar snapshot imutavel de edicao. Entregue em 2026-07-14 como fundacao sem UI.
11. Criar HTML estruturado a partir do snapshot. Entregue em 2026-07-14 como fundacao sem UI.
12. Criar PDF binario estruturado. Entregue em 2026-07-14 como fundacao sem UI.
13. Criar entitlements e planos. Entregue em 2026-07-14 como fundacao sem UI.
14. Criar Editorial AI Engine apenas para rascunho.
15. Criar area premium visual do assinante. Entregue em 2026-07-14 como fundacao inicial.
16. Criar distribuicao e metricas. Fundacao entregue em 2026-07-14 com provider `mock`, templates e providers `resend`/`smtp` preparados. Inbox do assinante entregue em 2026-07-15.
17. Integrar gateway de pagamento real. Fundacao entregue em 2026-07-14 com provider `mock`; Stripe/Mercado Pago seguem como ativacao por credenciais.
18. Executar fase juridica/compliance antes de lancamento comercial.

## Decisao desta fase

Alpha Premium Research passa a ser uma vertical futura oficial do Carteira Alpha 360.

Ela nao substitui o Wealth OS. Ela reutiliza o Wealth OS como base analitica e cria uma camada editorial, auditavel, versionada e eventualmente monetizavel.
