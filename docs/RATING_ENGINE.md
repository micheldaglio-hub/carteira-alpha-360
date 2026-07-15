# Rating Engine

Status: fundacao tecnica implementada em 2026-07-14.

## Objetivo

O Rating Engine transforma uma tese versionada em uma leitura institucional estruturada.

Ele nao le texto solto da interface. A origem obrigatoria e `asset_thesis_versions`.

O rating responde:

- qual e a qualidade institucional da tese atual;
- quais componentes sustentam a nota;
- quais riscos e limitacoes ainda existem;
- qual versao de tese originou o rating;
- qual formula e versao metodologica foram usadas;
- quais evidencias sustentam cada nota.

O motor nao compra, nao vende, nao altera carteira e nao publica relatorio sozinho.

## Arquivos

- `backend/app/premium_research/rating_engine.py`
- `backend/app/premium_research/thesis_engine.py`
- `backend/app/premium_research/publisher.py`
- `backend/app/premium_research/contracts.py`
- `backend/app/models.py`
- `backend/alembic/versions/20260714_0010_asset_rating_engine.py`
- `backend/tests/test_asset_rating_engine.py`

## Tabelas

### `asset_ratings`

Tabela mae do rating atual por ativo.

Campos principais:

- `asset_id`
- `thesis_id`
- `ticker`
- `asset_name`
- `asset_class`
- `rating_type`
- `status`
- `current_version`
- `current_version_id`
- `current_version_hash`
- `current_rating`
- `current_classification`
- `current_score`
- `confidence`
- `risk_level`
- `source_engine`
- `last_reviewed_at`
- `next_review_at`

Restricao:

- `ticker + asset_class + rating_type` deve ser unico.

### `asset_rating_versions`

Historico de cada versao do rating.

Campos principais:

- `rating_id`
- `asset_id`
- `thesis_id`
- `thesis_version_id`
- `publication_id`
- `publication_version_id`
- `version`
- `version_hash`
- `rating`
- `classification`
- `rating_status`
- `score_final`
- `thesis_score`
- `evidence_score`
- `risk_score`
- `conviction_score`
- `confidence_score`
- `data_quality_score`
- `governance_score`
- `suitability_score`
- `risk_level`
- `data_quality`
- `summary`
- `strengths_json`
- `watchpoints_json`
- `limits_json`
- `evidence_ids_json`
- `methodology_version`
- `source_thesis_hash`
- `effective_from`
- `effective_to`

### `asset_rating_evidence`

Ponte entre rating versionado e `Data Evidence Ledger`.

## Formula

Versao: `2026.07.rating1`.

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

Componentes:

- `thesis_score`: mede completude da tese, evidencias, riscos e plano de monitoramento.
- `evidence_score`: mede evidencias declaradas e links ao ledger.
- `risk_score`: penaliza risco alto, extremo ou arrojado.
- `conviction_score`: herdado da tese versionada.
- `confidence_score`: herdado da tese versionada.
- `data_quality_score`: mede qualidade dos dados declarada na tese.
- `governance_score`: considera se a tese esta ativa, fortalecida, em revisao, enfraquecida ou arquivada.
- `suitability_score`: considera papel e peso-alvo do ativo.

## Labels

```text
>= 85  -> alpha_core       -> Nucleo Alpha
>= 75  -> alpha_positive   -> Forte para acompanhamento
>= 62  -> alpha_neutral    -> Neutro qualificado
>= 50  -> alpha_watch      -> Em observacao
<  50  -> alpha_restricted -> Fora dos criterios atuais
```

## Fluxo

```text
Recommended Portfolio Engine
-> Alpha Research Publisher
-> Thesis Engine
-> asset_thesis_versions
-> Rating Engine
-> asset_rating_versions
-> Data Evidence Ledger
-> Research Committee
```

## Integracao com Publisher

`create_premium_research_draft` chama:

1. `sync_theses_from_recommended_report`
2. `sync_ratings_for_publication`
3. `run_research_committee_for_publication`

Assim, uma edicao premium ja guarda:

- tese versionada por ativo;
- rating versionado por tese;
- evidencias do rating no ledger;
- `ratingSync` no payload interno da versao da publicacao.
- `researchCommittee` no payload interno da versao da publicacao.

## Compatibilidade

- Nenhuma tela foi alterada.
- Nenhuma rota publica foi alterada.
- Nenhuma regra financeira foi alterada.
- Nenhum campo antigo foi removido.
- Rollback seguro: `alembic downgrade 20260714_0009`.

## Testes

- `backend/tests/test_asset_rating_engine.py`
- `backend/tests/test_alpha_research_publisher_service.py`

Cobertura:

- cria rating a partir de tese versionada;
- cria evidencias do rating;
- nao duplica versao quando a tese nao mudou;
- cria nova versao quando a tese muda;
- encerra a versao anterior com `effective_to`;
- sincroniza multiplas teses;
- confirma que o Publisher gera rating ao criar rascunho premium.

## Proximas evolucoes

1. Rating Center administrativo.
2. Rating por estrategia: dividendos, crescimento, global, cripto e aposentadoria.
3. Integracao com eventos extraordinarios do Guardian.
4. Publicacao premium somente apos revisao humana e aprovacao.
