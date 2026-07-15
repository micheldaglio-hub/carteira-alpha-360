# Publication PDF Publisher

Status: fundacao tecnica implementada em 2026-07-14.

## Objetivo

Gerar um PDF binario, versionado e auditavel a partir de um artefato HTML premium ja renderizado pelo `Publication Render Engine`.

O PDF e o primeiro artefato pronto para download controlado, envio futuro por e-mail, historico de assinantes e publicacao premium.

Desde o Premium Entitlements Engine, o download binario usa gate de permissao no backend: dono editorial ou entitlement ativo.

## Regra principal

O PDF nunca consulta dados vivos.

Fluxo oficial:

```text
publication_snapshots
-> publication_artifacts artifact_type=html
-> publication_artifacts artifact_type=pdf
```

O PDF guarda o `source_artifact_id` do HTML e o hash do HTML usado como origem.

## Arquivos

- `backend/app/premium_research/pdf_publisher.py`
- `backend/app/models.py`
- `backend/app/routers/premium.py`
- `backend/alembic/versions/20260714_0015_publication_pdf_artifacts.py`
- `backend/tests/test_publication_pdf_publisher.py`
- `backend/tests/test_premium_research_api.py`

## Dependencias

Adicionadas em `backend/requirements.txt`:

- `reportlab`
- `pypdf`

Uso:

- `reportlab`: cria o PDF binario com layout estruturado.
- `pypdf`: valida leitura e contagem de paginas nos testes.

## Banco de dados

A migration `20260714_0015_publication_pdf_artifacts.py` adiciona campos a `publication_artifacts`:

- `source_artifact_id`
- `binary_content`
- `content_size_bytes`
- `page_count`

Rollback:

```text
alembic downgrade 20260714_0014
```

## Hash

O PDF gera `artifact_hash` por SHA-256 usando:

```text
pdf_version + html_artifact_hash + snapshot_hash + pdf_bytes
```

## Data Lineage

Cada PDF registra evidencia:

```text
domain: premium_research_pdf
field_name: pdf_hash
provider: publication_pdf_publisher
source_type: formula
formula_name: publication_pdf_binary_hash
formula_version: 2026.07.pdf1
```

## API

Gerar PDF:

```http
POST /api/premium/artifacts/{artifact_id}/pdf
```

Body:

```json
{
  "force": false
}
```

Baixar PDF:

```http
GET /api/premium/artifacts/{artifact_id}/download
```

Resposta:

```text
Content-Type: application/pdf
X-Artifact-Hash: <hash do PDF>
```

Regra de acesso:

- dono editorial pode baixar para revisao;
- assinante precisa de entitlement ativo para `premium.pdf.download`, `premium.pdf.bulk_download` ou `premium.research.admin`;
- toda tentativa grava `premium_access_logs`.

## Idempotencia

Uma chamada repetida para o mesmo HTML e a mesma versao do PDF retorna o mesmo artefato.

Chave:

```text
snapshot_id + artifact_type=pdf + render_version + source_artifact_id
```

## O que nao faz ainda

- Nao publica o PDF em area de assinantes.
- Nao envia e-mail.
- Nao cobra assinatura em gateway real.
- Nao assina digitalmente o PDF.

## Criterios de aceite

- PDF so nasce de artefato HTML.
- Snapshot de origem precisa ter integridade `ok`.
- PDF possui bytes iniciando com `%PDF`.
- `page_count` e validado com `pypdf`.
- `content_size_bytes` e persistido.
- Download retorna `application/pdf`.
- Download de assinante exige entitlement ativo.
- Tentativas de download sao auditadas em `premium_access_logs`.
- Hash e evidencia ficam registrados.
