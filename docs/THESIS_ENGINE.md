# Thesis Engine

Status: fundacao tecnica implementada em 2026-07-14.

## Objetivo

O Thesis Engine guarda a tese historica de cada ativo analisado pelo Alpha Premium Research.

Ele existe para responder:

- por que um ativo entrou em uma carteira ou relatorio;
- qual papel ele cumpre na construcao patrimonial;
- quais evidencias sustentavam a tese naquela data;
- quais riscos estavam monitorados;
- quais gatilhos poderiam enfraquecer ou invalidar a tese;
- quando a tese mudou e qual versao estava vigente.

O motor nao publica relatorio, nao aprova recomendacao, nao altera carteira do usuario e nao muda regra financeira. Ele apenas versiona a leitura analitica que ja veio dos motores internos.

## Arquivos

- `backend/app/premium_research/thesis_engine.py`
- `backend/app/premium_research/contracts.py`
- `backend/app/premium_research/publisher.py`
- `backend/app/models.py`
- `backend/alembic/versions/20260714_0009_asset_thesis_engine.py`
- `backend/tests/test_asset_thesis_engine.py`

## Tabelas

### `asset_theses`

Tabela mae da tese atual por ativo.

Campos principais:

- `asset_id`
- `ticker`
- `universal_symbol`
- `asset_name`
- `asset_class`
- `thesis_type`
- `strategy_profile`
- `status`
- `current_version`
- `current_version_id`
- `current_version_hash`
- `confidence`
- `risk_level`
- `source_engine`
- `last_reviewed_at`
- `next_review_at`

Restricao:

- `ticker + asset_class + thesis_type` deve ser unico.

### `asset_thesis_versions`

Historico imutavel de cada versao da tese.

Campos principais:

- `thesis_id`
- `asset_id`
- `publication_id`
- `publication_version_id`
- `version`
- `version_hash`
- `thesis_status`
- `role`
- `thesis_text`
- `evidence_summary`
- `risk_summary`
- `monitoring_plan`
- `invalidation_triggers_json`
- `evidence_ids_json`
- `source_report_id`
- `source_engine`
- `confidence`
- `conviction`
- `target_weight`
- `risk_level`
- `data_quality`
- `change_reason`
- `effective_from`
- `effective_to`

Restricao:

- `thesis_id + version` deve ser unico.

### `asset_thesis_evidence`

Ponte entre a tese versionada e o `Data Evidence Ledger`.

Campos principais:

- `thesis_id`
- `thesis_version_id`
- `evidence_id`
- `evidence_key`
- `domain`
- `field_name`
- `provider`
- `source_type`
- `confidence`
- `status`

## Fluxo

```text
Recommended Portfolio Engine
-> recommendedPortfolioReport.assetReports
-> Alpha Research Publisher
-> Thesis Engine
-> asset_theses
-> asset_thesis_versions
-> asset_thesis_evidence
-> Data Evidence Ledger
```

## Regras de versionamento

1. O motor normaliza o relatorio do ativo.
2. Ele busca a tese por `ticker`, `asset_class` e `thesis_type`.
3. Calcula `version_hash` com ticker, classe, tipo, papel, tese, evidencias, riscos, monitoramento, confianca, conviccao, nivel de risco, origem e id do relatorio.
4. Se o hash for igual e `force_new_version=False`, nao cria duplicata.
5. Se o hash mudou ou `force_new_version=True`, encerra a versao anterior com `effective_to` e cria a proxima versao (`v1`, `v2`, `v3`...).
6. Atualiza a tese mae com a versao corrente.
7. Registra evidencias de tese, risco, confianca, conviccao e peso-alvo no `Data Evidence Ledger`.

## Integracao com Publisher

`create_premium_research_draft` chama `sync_theses_from_recommended_report` sem alterar tela, rota ou payload antigo.

O payload interno da `publication_versions.payload_json` ganhou `thesisSync`, contendo:

- status da sincronizacao;
- versao do motor;
- quantidade de ativos;
- quantidade de versoes criadas;
- teses unchanged;
- ids das versoes geradas.

## Compatibilidade

- Nenhuma tabela antiga foi removida.
- Nenhum campo antigo foi removido.
- Nenhuma rota publica foi alterada.
- Nenhuma tela foi alterada.
- Nenhuma regra financeira foi alterada.
- Rollback seguro: `alembic downgrade 20260714_0008`.

## Testes

- `backend/tests/test_asset_thesis_engine.py`
- `backend/tests/test_alpha_research_publisher_service.py`

Cobertura:

- cria tese e versao inicial;
- cria evidencias vinculadas;
- evita duplicata quando nada muda;
- cria nova versao quando a tese muda;
- encerra versao anterior com `effective_to`;
- sincroniza multiplos ativos a partir de um relatorio;
- confirma que o Publisher gera teses ao criar rascunho premium.

## Proximas evolucoes

1. Rating Engine: transformar tese, score, risco e evidencias em rating institucional versionado.
2. Research Committee: exigir gates entre motores antes de elevar conviccao editorial.
3. Thesis Center: tela administrativa para comparar versoes historicas.
4. Eventos extraordinarios: criar nova tese quando Guardian, Research & News ou Market Data detectarem mudanca relevante.
5. Disclosures: ligar tese publicada a aviso legal, assinatura e aprovacao humana.
