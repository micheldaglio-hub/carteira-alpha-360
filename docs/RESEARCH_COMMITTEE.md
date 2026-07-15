# Research Committee

Status: fundacao tecnica implementada em 2026-07-14.

## Objetivo

O Research Committee e o gate institucional entre tese, rating, confianca dos dados, Guardian, Evidence Ledger e publicacao premium.

Ele nao cria recomendacao sozinho, nao altera carteira, nao publica relatorio e nao substitui aprovacao humana. A funcao dele e responder:

- a tese existe e esta versionada?
- o rating foi calculado a partir dessa tese historica?
- as evidencias sao rastreaveis no Data Evidence Ledger?
- a confianca dos dados sustenta a leitura?
- o Guardian encontrou risco impeditivo?
- a edicao pode ir para revisao humana, precisa de ajustes ou deve ficar bloqueada?

## Arquivos

- `backend/app/premium_research/research_committee.py`
- `backend/app/premium_research/publisher.py`
- `backend/app/premium_research/contracts.py`
- `backend/app/models.py`
- `backend/alembic/versions/20260714_0011_research_committee.py`
- `backend/tests/test_research_committee.py`
- `backend/tests/test_alpha_research_publisher_service.py`

## Tabelas

### `research_committee_runs`

Guarda cada rodada do comite.

Campos principais:

- `publication_id`
- `publication_version_id`
- `period`
- `committee_type`
- `status`
- `decision`
- `readiness_score`
- `approval_score`
- `blocker_count`
- `warning_count`
- `gate_count`
- `vote_count`
- `summary`
- `blockers_json`
- `warnings_json`
- `metadata_json`
- `methodology_version`

### `research_committee_gate_results`

Guarda o resultado de cada gate.

Gates iniciais:

- `thesis_coverage`
- `rating_coverage`
- `evidence_ledger`
- `data_confidence`
- `guardian_risk`
- `publication_readiness`
- `legal_safety`

Status possiveis:

- `pass`
- `warn`
- `block`

### `research_committee_votes`

Guarda votos dos motores internos.

Votantes iniciais:

- `thesis_engine`
- `rating_engine`
- `data_confidence`
- `guardian`
- `evidence_ledger`

Decisoes possiveis:

- `approve`
- `request_changes`
- `block`

## Decisoes do comite

```text
approved_for_review -> pode seguir para revisao humana
needs_review        -> pode ser revisado, mas com pontos de atencao
request_changes     -> precisa de ajuste antes da revisao final
blocked             -> nao deve avancar como publicacao premium
```

Nenhuma decisao equivale a publicacao automatica.

## Formula

Versao: `2026.07.committee1`.

O score de aprovacao e uma media ponderada dos gates, com penalizacao por bloqueios e avisos.

Pesos:

```text
thesis_coverage       18
rating_coverage       18
evidence_ledger       16
data_confidence       14
guardian_risk         14
publication_readiness 10
legal_safety          10
```

Regra:

```text
approval_score = media_ponderada(gates) - penalidade_bloqueios - penalidade_avisos
```

Penalidades:

- cada gate `block`: -18 pontos
- cada gate `warn`: -4 pontos

Politica de decisao:

- qualquer gate/voto `block` gera `blocked`;
- score abaixo de 68 ou muitos votos `request_changes` gera `request_changes`;
- avisos leves geram `needs_review`;
- sem bloqueios nem avisos gera `approved_for_review`.

## Integracao com Publisher

`create_premium_research_draft` agora executa:

```text
Alpha Research Publisher
-> Thesis Engine
-> Rating Engine
-> Publisher Evidence
-> Readiness Report
-> Research Committee
-> payload interno com researchCommittee
```

O payload interno de `publication_versions.payload_json` recebe:

- `thesisSync`
- `ratingSync`
- `researchCommittee`

O `version_hash` tambem considera:

- id da rodada do comite;
- decisao;
- score de aprovacao.

## Evidence Ledger

Cada rodada cria uma evidencia no `Data Evidence Ledger`:

- `domain`: `research_committee`
- `field_name`: `approval_score`
- `provider`: `research_committee`
- `source_type`: `formula`
- `formula_version`: `2026.07.committee1`

Assim, a decisao do comite tambem fica auditavel.

## Compatibilidade

- Nenhuma tela foi alterada.
- Nenhuma rota publica foi alterada.
- Nenhum payload legado foi removido.
- Nenhum calculo financeiro foi alterado.
- Nenhuma publicacao automatica foi criada.
- Rollback seguro: `alembic downgrade 20260714_0010`.

## Testes

- `backend/tests/test_research_committee.py`
- `backend/tests/test_alpha_research_publisher_service.py`

Cobertura:

- comite aprova research forte apenas para revisao humana;
- comite bloqueia publicacao sem rating;
- comite bloqueia rating restrito/risco extremo;
- Publisher gera comite automaticamente no rascunho premium;
- payload interno da versao guarda a decisao do comite.

## Proximas evolucoes

1. Endpoints administrativos protegidos para listar e executar rodadas.
2. Workflow formal de revisao humana usando `publication_reviews` e `publication_approvals`.
3. Committee Center administrativo.
4. Votos especializados por estrategia: dividendos, crescimento, global, FII e cripto.
5. Eventos extraordinarios do Guardian reabrindo teses ja aprovadas.
