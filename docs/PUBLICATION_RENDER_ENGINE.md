# Publication Render Engine

Status: fundacao tecnica implementada em 2026-07-14.

## Objetivo

Transformar uma edicao premium aprovada e congelada pelo `Publication Snapshot Engine` em um artefato HTML premium, reproduzivel, versionado e auditavel.

O motor existe para preparar a futura geracao de PDF, pagina web premium, download, entrega por e-mail e historico de assinantes sem depender dos dados vivos da carteira ou dos provedores de mercado.

## Regra principal

O `Publication Render Engine` nunca consulta dado vivo.

Fonte unica:

```text
publication_snapshots.payload_json
```

Isso garante que a edicao aprovada continue igual mesmo que precos, noticias, scores, fontes ou recomendacoes mudem depois.

## Arquivos

- `backend/app/premium_research/renderer.py`
- `backend/app/models.py`
- `backend/app/routers/premium.py`
- `backend/alembic/versions/20260714_0014_publication_artifacts.py`
- `backend/tests/test_publication_renderer.py`
- `backend/tests/test_premium_research_api.py`

## Tabela

Tabela criada:

```text
publication_artifacts
```

Campos principais:

- `publication_id`
- `publication_version_id`
- `snapshot_id`
- `period`
- `artifact_type`
- `status`
- `title`
- `content_type`
- `file_extension`
- `render_engine`
- `render_version`
- `source_snapshot_hash`
- `artifact_hash`
- `html_content`
- `plain_text`
- `manifest_json`
- `metadata_json`
- `evidence_ids_json`
- `created_by_user_id`
- `created_at`

Unicidade:

```text
snapshot_id + artifact_type + render_version
```

Rollback:

```text
alembic downgrade 20260714_0013
```

## Fluxo

```text
Research Publication aprovada
-> Publication Snapshot Engine
-> Snapshot com integridade ok
-> Publication Render Engine
-> publication_artifacts
-> Data Evidence Ledger
-> futuro PDF/Web/Delivery
```

## Saida

O motor gera:

- HTML premium com estilo print-ready;
- texto simples para busca, auditoria e previews;
- manifest do artefato;
- `artifact_hash`;
- evidencia em `Data Evidence Ledger`.

## Hashes

O `artifact_hash` e SHA-256 calculado a partir de:

```text
render_version + artifact_type + snapshot_hash + html_content
```

O HTML inclui:

- `snapshotHash`
- `contentHash`
- `sourceHash`
- `evidenceHash`
- `approvalHash`

## Data Lineage

Cada renderizacao grava:

```text
domain: premium_research_artifact
field_name: artifact_hash
provider: publication_render_engine
source_type: formula
formula_name: publication_artifact_html_hash
formula_version: 2026.07.render1
```

## API

Renderizar:

```http
POST /api/premium/snapshots/{snapshot_id}/render
```

Body:

```json
{
  "artifact_type": "html",
  "force": false,
  "include_content": true
}
```

Consultar:

```http
GET /api/premium/artifacts
GET /api/premium/artifacts/{artifact_id}
GET /api/premium/publications/{publication_id}/artifacts
GET /api/premium/snapshots/{snapshot_id}/artifacts
```

## O que nao faz ainda

- Nao gera PDF binario.
- Nao publica site publico.
- Nao envia e-mail.
- Nao controla assinatura.
- Nao libera download por plano.
- Nao substitui revisao humana.

## Riscos

- HTML ainda e artefato tecnico, nao layout comercial final.
- PDF binario exigira renderer dedicado e validacao visual.
- Downloads em PDF agora sao protegidos pelo Premium Entitlements Engine; o HTML continua sendo artefato operacional protegido por autenticacao.
- Revisao juridica ainda e obrigatoria antes de venda real.

## Criterios de aceite

- Snapshot com integridade ruim nao renderiza.
- Render repetido retorna o mesmo artefato sem duplicar.
- Artefato guarda hash e origem do snapshot.
- HTML contem disclaimer e hashes da edicao.
- API exige autenticacao.
- Evidencia e registrada no Data Evidence Ledger.
- Testes unitarios e de API passam.
