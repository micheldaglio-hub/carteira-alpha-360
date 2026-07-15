# Mapa do Sistema - Carteira Alpha 360

Status: mapa arquitetural vivo.

## Estado atual

O sistema possui backend FastAPI, banco SQLAlchemy/Alembic, frontend React e modulos funcionais de carteira, cripto, dashboard, radares, projecoes, rebalanceamento, alertas e inteligencia.

Hoje ainda existem conceitos herdados de uma carteira brasileira:

- `Asset` ja existe, mas ainda nao possui identidade global completa.
- `MarketSnapshot` concentra fundamentos e mercado de forma simples.
- Cripto possui fluxo de tela especifico, mas deve ser integrado ao conceito universal de Asset.
- Providers existem, mas ainda nao formam um Market Data Engine completo.

## Mapa alvo

```text
Usuario
  -> Carteira
    -> Posicoes
    -> Transacoes
    -> Proventos
    -> Metas

Asset Engine Universal
  -> Asset
  -> Identificadores
  -> Classificacoes
  -> Exposicoes
  -> Asset Taxonomy unica

Portfolio Aggregation Engine
  -> Snapshot patrimonial unico
  -> Alocacao por classe, pais, regiao, moeda, setor e ativo
  -> Exposicoes global, cripto, trading e renda fixa
  -> Fonte comum para Dashboard, Strategy, Stress e Copilot

Total Return Engine
  -> Retorno de preco
  -> Dividendos
  -> JCP
  -> Rendimentos de FIIs
  -> Aportes fora do lucro
  -> Retorno total acumulado auditavel

Market Data Engine
  -> Providers
  -> Cache
  -> Fallback
  -> Normalizacao

Crypto Research Engine
  -> Screener mensal
  -> Tese
  -> Tokenomics
  -> Catalisadores
  -> Riscos
  -> Cenarios

Alpha Confidence Engine
  -> Gates de confianca
  -> Nota geral
  -> Confianca por ativo
  -> Regras nao negociaveis
  -> Linguagem humana

Recommended Portfolio Engine
  -> Relatorio institucional mensal
  -> Tese por ativo
  -> Risco e evidencias
  -> Score institucional
  -> Revisao mensal

Recommendation Governance Engine
  -> ReviewId
  -> Snapshot mensal
  -> Tese, risco e evidencias
  -> Gatilhos extraordinarios
  -> Persistencia em user_preferences

Alpha Wealth OS
  -> Command Center
  -> Event Engine 2.0
  -> Guardian 2.0
  -> Research & News Engine
  -> Evidence Center
  -> Goal Engine
  -> Wealth Progress Score
  -> Scenario & Stress Test Engine
  -> Opportunity Engine
  -> Data Confidence Engine V2
  -> Economic Engine
  -> Macro / FX Engine
  -> Tax Engine
  -> Strategy Engine 2.0
  -> Alpha Copilot conversacional

Alpha Premium Research
  -> Alpha Research Publisher
  -> Contratos de publicacao
  -> Rascunho premium versionado
  -> Publicacoes versionadas
  -> Secoes editoriais
  -> Fontes e evidencias
  -> Revisoes, aprovacoes e correcoes
  -> Thesis Engine
  -> Teses versionadas por ativo
  -> Historico de tese e evidencias
  -> Rating Engine
  -> Ratings versionados por tese
  -> Research Committee
  -> Gates de tese, rating, confianca, Guardian e evidencias
  -> Premium Research Admin API
  -> Rotas protegidas em /api/premium
  -> Revision Engine
  -> Portfolio Constructor
  -> Performance Attribution Engine
  -> Publication Snapshot Engine
  -> Publication Render Engine
  -> Publication PDF Publisher
  -> Premium Entitlements Engine
  -> Planos, assinaturas, permissoes e logs de acesso
  -> Premium RBAC
  -> Area Premium do Assinante
  -> Payment Gateway
  -> Checkout, transacoes, webhooks e ativacao de assinatura
  -> Distribution Engine
  -> Campanhas, destinatarios, eventos de entrega, templates premium e providers mock/resend/smtp
  -> Notification Center / Subscriber Delivery Inbox
  -> Editorial AI Engine
  -> PDF / Web Publisher
  -> Subscription & Entitlements
  -> Compliance & Disclosure
  -> Publication Quality Gates
  -> Historico auditavel de publicacoes

Production / Observability / Auditoria
  -> Logs estruturados
  -> Audit Events
  -> Job Runner
  -> Ops Center
  -> Backup / Restore
  -> E2E

Proventos Engine
  -> Dividendos
  -> JCP
  -> Rendimentos de FIIs
  -> Rendimentos futuros

Screener Alpha Global
  -> Acoes internacionais
  -> Paises
  -> Moedas
  -> Bolsas
  -> Diversificacao geografica

Global Backtest Engine
  -> Stock direto
  -> BDR proxy
  -> ETF global
  -> Cambio
  -> Dividendos internacionais

Knowledge Engine
  -> Fatos
  -> Metricas
  -> Historico
  -> Eventos corporativos

Strategy Engine 2.0
  -> Perfis patrimoniais
  -> Alocacao alvo
  -> Aderencia por fatores
  -> Encaixe dos ativos
  -> Proximos estudos

Global Portfolio Engine
  -> Consolidacao
  -> Alocacao
  -> Rentabilidade
  -> Concentracao

FX/Money Engine
  -> Cambio
  -> Conversao
  -> Moeda base do usuario

Guardian
  -> Alertas
  -> Eventos
  -> Risco
  -> Fila de acompanhamento

Copilot
  -> Perguntas
  -> Respostas explicaveis

Production Readiness
  -> Runtime Safety Gate
  -> Readiness
  -> Security Headers
  -> Auth Rate Limit
  -> CI
  -> Secrets por ambiente
```

## Dependencias desejadas

Telas dependem de rotas.
Rotas dependem de services.
Services dependem de engines.
Engines dependem de repositorios e providers.
Providers nunca dependem de telas.

## Modulos atuais e destino

| Modulo atual | Destino arquitetural |
| --- | --- |
| Minha Carteira | Global Portfolio Engine |
| Cripto | Asset Engine + Market Data Engine |
| Cripto do mes | Market Data Engine + Crypto Research Engine |
| Carteira Recomendada | Recommended Portfolio Engine + Alpha Confidence + Screeners Alpha + Strategy Engine |
| Confiabilidade Alpha | Alpha Confidence Engine + Knowledge Engine futuro |
| Proventos | Proventos Engine + Knowledge Engine + Strategy Engine |
| Carteira Alpha FIIs | Screener Alpha FIIs + Strategy Engine |
| Carteira Alpha Global | Screener Alpha Global + Market Data Engine + FX/Money Engine |
| Backtest internacional | Global Backtest Engine + Market Data Engine + FX/Money Engine |
| Estrategias | Strategy Engine 2.0 + Global Portfolio Engine |
| Crescimento | Knowledge Engine + Strategy Engine |
| Radar de Ativos | Strategy Engine + Alpha Score Mundial |
| Projecoes | Wealth Builder |
| Rebalanceamento | Global Portfolio Engine + Strategy Engine |
| Alertas | Guardian + Event Engine + Insight Engine |
| Alpha Intelligence | Knowledge + Strategy + Guardian + Copilot |
| Alpha Premium Research | Wealth OS + Recommended Portfolio + Data Lineage + Publisher + Thesis Engine versionado + Rating Engine + Research Committee + Performance Attribution Engine + Publication Snapshot Engine + Publication Render Engine + Publication PDF Publisher + Premium Entitlements + RBAC + Payment Gateway + Distribution Engine + Distribution Providers + Premium Email Templates + Notification Center + Premium Admin API + Area Premium |

## Regra de acoplamento

Uma tela pode ter nome especifico para facilitar uso. O backend nao deve duplicar regra de negocio por nome da tela.
