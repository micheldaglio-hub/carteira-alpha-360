# Arquiteto Chefe - Carteira Alpha 360

Status: guia arquitetural vivo.

## Constituicao arquitetural

O documento `docs/CONSTITUICAO_DO_PROJETO.md` e o nivel mais alto da documentacao do projeto. Este guia de arquitetura existe para transformar essa Constituicao em decisoes tecnicas concretas.

Nenhuma decisao arquitetural deve contrariar a missao permanente de construir uma plataforma global de inteligencia patrimonial, confiavel, escalavel, documentada e baseada em dados.

## Mandato

Toda evolucao do Carteira Alpha 360 deve preservar a visao de plataforma patrimonial global. O sistema deve ser modular, auditavel, escalavel e preparado para multiplos ativos, mercados, moedas, providers e estrategias.

## Principios

- Todo investimento e um `Asset`.
- Ticker nao e identificador global.
- Provider externo nao deve mandar na modelagem interna.
- Tela nao deve consumir dado cru de provider.
- Score nao deve ser recomendacao financeira.
- Mudanca de modelo exige migracao Alembic.
- Documentacao deve ser atualizada no mesmo ciclo da alteracao.
- O sistema deve permanecer funcional ao final de cada fase.

## Pilares de arquitetura

1. `Asset Engine Universal`: identidade e taxonomia global de ativos.
2. `Market Data Engine`: orquestracao de providers, cache, fallback e normalizacao.
3. `Knowledge Engine`: fatos, metricas, eventos e historico tratados.
4. `Strategy Engine 2.0`: interpretacao de estilos patrimoniais, alocacao alvo, aderencia e proximos estudos sem ordem automatica.
5. `Global Portfolio Engine`: consolidacao global da carteira por ativo, moeda, classe e mercado.
6. `FX/Money Engine`: cambio, conversao, moeda base do usuario e valores multi-moeda.
7. `Alpha Score Mundial`: scores comparaveis por classe, regiao, setor e estrategia.
8. `Wealth Builder`: metas, projecoes, aportes, renda passiva e cenarios.
9. `Guardian`: alertas, risco, concentracao, anomalias e eventos importantes.
10. `Copilot`: camada conversacional futura baseada em dados tratados.

## Alpha Wealth OS

O Alpha Wealth OS passa a ser a camada de orquestracao acima dos pilares.

Ele nao substitui os engines. Ele coordena:

- Goal Engine.
- Wealth Progress Score.
- Scenario Engine.
- Opportunity Engine.
- Data Confidence Engine.
- Economic Engine.
- Strategy Engine 2.0.
- Alpha Copilot estruturado.

Regra arquitetural: React nao calcula score patrimonial, meta, oportunidade ou cenario. A interface apenas renderiza payloads do backend.

Rotas novas devem ser aditivas e versionaveis. Rotas antigas nao podem ser quebradas.

## Decisao da Fase 1

Antes de implementar taxonomia global definitiva, a Fase 1 deve refinar a arquitetura e documentar a transicao do modelo atual para o modelo universal.

Escopo permitido nesta etapa:

- Revisar arquitetura.
- Atualizar documentacao.
- Propor modelagem.
- Listar tabelas.
- Listar riscos.
- Listar impacto no codigo atual.
- Definir criterios de aceite.

Escopo proibido nesta etapa:

- Alterar layout.
- Criar telas.
- Alterar regras de negocio em codigo.
- Mudar rotas existentes.
- Migrar dados reais sem aprovacao.

## Impacto previsto sobre o codigo atual

- `backend/app/models.py`: evoluir `Asset` e criar tabelas auxiliares.
- `backend/alembic/versions`: criar migrations aditivas.
- `backend/app/services/market_data`: virar Market Data Engine.
- `backend/app/alpha`: consumir Knowledge/Strategy Engine em vez de snapshots diretos.
- `backend/app/routers`: manter contratos atuais enquanto novos services entram por baixo.
- `frontend`: sem mudanca inicial; telas continuam consumindo as mesmas rotas.

## Criterio de arquitetura saudavel

Se um novo ativo como `AAPL`, `VNQ`, `BTC`, `ouro` ou `caixa em USD` exigir nova tela ou regra isolada no backend para existir, a arquitetura ainda nao esta boa o suficiente.
