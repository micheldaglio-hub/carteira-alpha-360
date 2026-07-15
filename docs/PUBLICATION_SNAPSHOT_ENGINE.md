# Publication Snapshot Engine

Status: fundacao tecnica implementada em 2026-07-14.

## Objetivo

O `Publication Snapshot Engine` cria o pacote imutavel de uma edicao premium do Alpha Premium Research.

Ele existe para impedir que uma edicao aprovada mude silenciosamente depois da aprovacao humana. Cada snapshot guarda:

- publicacao;
- versao editorial;
- secoes;
- ativos citados;
- fontes;
- evidencias;
- Research Committee;
- Performance Attribution, quando existir;
- revisao humana;
- aprovacao final;
- aviso legal;
- manifest;
- hash canonico da edicao.

O snapshot nao publica, nao envia e-mail, nao gera PDF e nao muda carteira. Ele apenas congela o estado aprovado da edicao para as proximas fases: HTML/PDF, distribuicao, correcoes, auditoria e assinantes.

## Arquivos

- `backend/app/premium_research/snapshot_engine.py`
- `backend/app/routers/premium.py`
- `backend/app/models.py`
- `backend/alembic/versions/20260714_0013_publication_snapshots.py`
- `backend/tests/test_publication_snapshots.py`
- `backend/tests/test_premium_research_api.py`

## Tabela

### `publication_snapshots`

Campos principais:

- `publication_id`
- `publication_version_id`
- `period`
- `snapshot_type`
- `status`
- `version_label`
- `publication_status`
- `version_status`
- `snapshot_hash`
- `content_hash`
- `source_hash`
- `evidence_hash`
- `approval_hash`
- `committee_run_id`
- `attribution_run_id`
- `review_id`
- `approval_id`
- `section_count`
- `asset_count`
- `source_count`
- `evidence_count`
- `is_immutable`
- `payload_json`
- `manifest_json`
- `evidence_ids_json`
- `created_by_user_id`
- `locked_at`

Restricao:

- `publication_version_id + snapshot_type` e unico.

Isso torna a operacao idempotente: se o snapshot da mesma versao ja existe, o motor devolve o snapshot existente em vez de criar outro.

## Fluxo

```text
Rascunho premium
-> Thesis Engine
-> Rating Engine
-> Research Committee
-> Performance Attribution opcional
-> Revisao humana
-> Aprovacao final
-> Publication Snapshot Engine
-> HTML/PDF/Distribuicao futura
```

## Regra de aprovacao

Por padrao, o snapshot final exige:

- `research_publications.status = approved`;
- `publication_versions.status = approved`;
- revisao humana com `decision = approve`;
- aprovacao final com `decision = approve_publication`.

Se qualquer item faltar, o endpoint retorna conflito e nao cria snapshot.

## Hashes

O motor gera hashes SHA-256:

```text
content_hash  = hash(publicacao + versao + secoes + ativos)
source_hash   = hash(fontes + evidencias)
evidence_hash = hash(evidencias)
approval_hash = hash(revisao + aprovacao + comite)
snapshot_hash = hash(payload canonico completo)
```

O `snapshot_hash` e gravado tambem no Data Evidence Ledger:

```text
domain = premium_research_snapshot
field_name = snapshot_hash
provider = publication_snapshot_engine
source_type = formula
formula_version = 2026.07.snapshot1
```

## APIs

```http
POST /api/premium/publications/{publication_id}/snapshots
GET /api/premium/publications/{publication_id}/snapshots
GET /api/premium/snapshots
GET /api/premium/snapshots/{snapshot_id}
```

Payload de criacao:

```json
{
  "publication_version_id": "opcional",
  "snapshot_type": "approved_edition",
  "require_approval": true,
  "include_payload": false
}
```

## Integridade

`snapshot_to_dict` retorna:

- `integrity.status = ok` quando o hash recalculado do payload bate com o hash armazenado;
- `integrity.status = tampered` se o payload foi alterado depois de gravado.

## Compatibilidade

- Nenhuma rota existente foi removida.
- Nenhum payload legado foi alterado.
- Nenhuma tela foi alterada.
- Nenhum calculo financeiro foi alterado.
- Rollback seguro: `alembic downgrade 20260714_0012`.

## Testes

Validado por:

```text
python -m unittest tests.test_publication_snapshots tests.test_premium_research_api
```

Cobertura:

- rascunho sem aprovacao nao pode gerar snapshot final;
- edicao aprovada gera snapshot imutavel;
- chamada repetida devolve o mesmo snapshot;
- hash de integridade fica `ok`;
- endpoint protegido cria, lista e consulta snapshots.
