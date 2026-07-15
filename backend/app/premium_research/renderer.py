from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from html import escape
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PublicationArtifact, PublicationSnapshot
from app.premium_research.snapshot_engine import verify_snapshot_integrity
from app.services.data_lineage import record_data_evidence


PUBLICATION_RENDER_VERSION = "2026.07.render1"
PUBLICATION_RENDER_ENGINE = "publication_render_engine"
SUPPORTED_ARTIFACT_TYPES = {"html", "html_print"}


class PublicationRenderError(ValueError):
    """Raised when a premium snapshot cannot be rendered safely."""


def render_publication_snapshot(
    db: Session,
    *,
    snapshot: PublicationSnapshot,
    user_id: str | None = None,
    artifact_type: str = "html",
    force: bool = False,
    commit: bool = True,
) -> dict[str, Any]:
    """Render a locked snapshot into a deterministic premium HTML artifact.

    Rendering always reads from the snapshot payload, not live market data. This
    keeps the approved publication reproducible even when prices, scores or
    sources change later.
    """

    artifact_type = (artifact_type or "html").strip().lower()[:80] or "html"
    if artifact_type not in SUPPORTED_ARTIFACT_TYPES:
        raise PublicationRenderError("Tipo de artefato premium nao suportado.")

    integrity = verify_snapshot_integrity(snapshot)
    if integrity.get("status") != "ok":
        raise PublicationRenderError("Snapshot premium nao passou na verificacao de integridade.")

    existing = db.execute(
        select(PublicationArtifact).where(
            PublicationArtifact.snapshot_id == snapshot.id,
            PublicationArtifact.artifact_type == artifact_type,
            PublicationArtifact.render_version == PUBLICATION_RENDER_VERSION,
        )
    ).scalar_one_or_none()
    if existing is not None and not force:
        payload = artifact_to_dict(existing, include_content=False)
        payload["alreadyExists"] = True
        return payload

    snapshot_payload = _json_load(snapshot.payload_json, {})
    rendered = _build_html(snapshot, snapshot_payload, artifact_type=artifact_type)
    artifact_hash = _hash_text(
        "|".join(
            [
                PUBLICATION_RENDER_VERSION,
                artifact_type,
                snapshot.snapshot_hash,
                rendered["htmlContent"],
            ]
        )
    )
    manifest = {
        "renderEngine": PUBLICATION_RENDER_ENGINE,
        "renderVersion": PUBLICATION_RENDER_VERSION,
        "artifactType": artifact_type,
        "contentType": "text/html; charset=utf-8",
        "fileExtension": "html",
        "publicationId": snapshot.publication_id,
        "publicationVersionId": snapshot.publication_version_id,
        "snapshotId": snapshot.id,
        "sourceSnapshotHash": snapshot.snapshot_hash,
        "artifactHash": artifact_hash,
        "period": snapshot.period,
        "sectionCount": snapshot.section_count,
        "assetCount": snapshot.asset_count,
        "sourceCount": snapshot.source_count,
        "evidenceCount": snapshot.evidence_count,
        "generatedAt": datetime.now(UTC).isoformat(),
    }

    artifact = existing or PublicationArtifact(
        publication_id=snapshot.publication_id,
        publication_version_id=snapshot.publication_version_id,
        snapshot_id=snapshot.id,
        period=snapshot.period,
        artifact_type=artifact_type,
    )
    artifact.status = "rendered"
    artifact.title = rendered["title"][:220]
    artifact.content_type = "text/html; charset=utf-8"
    artifact.file_extension = "html"
    artifact.render_engine = PUBLICATION_RENDER_ENGINE
    artifact.render_version = PUBLICATION_RENDER_VERSION
    artifact.source_snapshot_hash = snapshot.snapshot_hash
    artifact.artifact_hash = artifact_hash
    artifact.html_content = rendered["htmlContent"]
    artifact.plain_text = rendered["plainText"]
    artifact.manifest_json = _json(manifest)
    artifact.metadata_json = _json(
        {
            "snapshotIntegrity": integrity,
            "artifactPurpose": "premium_research_print_ready_html",
            "renderedFromImmutableSnapshot": True,
            "sourceContentHash": snapshot.content_hash,
            "sourceEvidenceHash": snapshot.evidence_hash,
            "sourceApprovalHash": snapshot.approval_hash,
        }
    )
    artifact.created_by_user_id = user_id
    if existing is None:
        db.add(artifact)
    db.flush()

    evidence_row = record_data_evidence(
        db,
        user_id=user_id,
        domain="premium_research_artifact",
        field_name="artifact_hash",
        value_text=artifact_hash,
        unit="sha256",
        provider=PUBLICATION_RENDER_ENGINE,
        source_type="formula",
        source_ref=f"publicationSnapshot:{snapshot.id}:artifact:{artifact.id}",
        formula_name="publication_artifact_html_hash",
        formula_version=PUBLICATION_RENDER_VERSION,
        input_payload=manifest,
        confidence=96,
        quality_score=96,
        status="ok",
        metadata={
            "snapshotId": snapshot.id,
            "artifactId": artifact.id,
            "sourceSnapshotHash": snapshot.snapshot_hash,
        },
    )
    evidence_ids = _json_load(artifact.evidence_ids_json, [])
    evidence_ids.append(evidence_row.id)
    artifact.evidence_ids_json = _json(evidence_ids)

    if commit:
        db.commit()
        db.refresh(artifact)

    payload = artifact_to_dict(artifact, include_content=False)
    payload["alreadyExists"] = False
    return payload


def artifact_to_dict(artifact: PublicationArtifact, *, include_content: bool = False) -> dict[str, Any]:
    payload = {
        "id": artifact.id,
        "publicationId": artifact.publication_id,
        "publicationVersionId": artifact.publication_version_id,
        "snapshotId": artifact.snapshot_id,
        "period": artifact.period,
        "artifactType": artifact.artifact_type,
        "status": artifact.status,
        "title": artifact.title,
        "contentType": artifact.content_type,
        "fileExtension": artifact.file_extension,
        "renderEngine": artifact.render_engine,
        "renderVersion": artifact.render_version,
        "sourceArtifactId": artifact.source_artifact_id or "",
        "sourceSnapshotHash": artifact.source_snapshot_hash,
        "artifactHash": artifact.artifact_hash,
        "contentSizeBytes": artifact.content_size_bytes,
        "pageCount": artifact.page_count,
        "hasBinaryContent": bool(artifact.binary_content),
        "manifest": _json_load(artifact.manifest_json, {}),
        "metadata": _json_load(artifact.metadata_json, {}),
        "evidenceIds": _json_load(artifact.evidence_ids_json, []),
        "createdByUserId": artifact.created_by_user_id,
        "createdAt": artifact.created_at.isoformat() if artifact.created_at else "",
    }
    if include_content:
        payload["htmlContent"] = artifact.html_content
        payload["plainText"] = artifact.plain_text
    return payload


def _build_html(snapshot: PublicationSnapshot, payload: dict[str, Any], *, artifact_type: str) -> dict[str, str]:
    publication = payload.get("publication") or {}
    version = payload.get("version") or {}
    title = str(publication.get("title") or "Carteira Alpha 360 Premium Research")
    subtitle = str(publication.get("subtitle") or "Edicao premium aprovada")
    period = str(publication.get("period") or snapshot.period or "")
    sections = list(payload.get("sections") or [])
    assets = list(payload.get("assets") or [])
    sources = list(payload.get("sources") or [])
    evidence = list(payload.get("evidence") or [])
    committee = payload.get("committee") or {}
    attribution = payload.get("attribution") or {}
    review = payload.get("review") or {}
    approval = payload.get("approval") or {}
    disclaimer = str(payload.get("legalDisclaimer") or "")
    generated_at = datetime.now(UTC).isoformat()

    html_sections = "\n".join(_section_html(section) for section in sections)
    asset_rows = "\n".join(_asset_row_html(asset) for asset in assets) or _empty_row_html(5, "Nenhum ativo no snapshot.")
    source_rows = "\n".join(_source_row_html(source) for source in sources[:40]) or _empty_row_html(4, "Nenhuma fonte registrada.")
    evidence_rows = "\n".join(_evidence_row_html(item) for item in evidence[:40]) or _empty_row_html(4, "Nenhuma evidencia registrada.")
    committee_summary = str(committee.get("summary") or "Comite sem resumo registrado no snapshot.")
    attribution_summary = _attribution_summary(attribution)
    plain = _plain_text(title, subtitle, period, sections, assets, sources, evidence, disclaimer)

    html = f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(title)}</title>
  <style>
    :root {{
      --ink: #111827;
      --muted: #4b5563;
      --line: #d8dee8;
      --gold: #c7971a;
      --gold-soft: #fff8dc;
      --surface: #f7f4ec;
      --panel: #ffffff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--surface);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.48;
    }}
    .page {{
      max-width: 980px;
      margin: 0 auto;
      padding: 42px;
      background: var(--panel);
      min-height: 100vh;
    }}
    .eyebrow {{
      color: var(--gold);
      font-size: 11px;
      font-weight: 800;
      letter-spacing: .14em;
      text-transform: uppercase;
    }}
    h1 {{ margin: 10px 0 8px; font-size: 34px; line-height: 1.1; }}
    h2 {{ margin: 30px 0 10px; font-size: 19px; border-bottom: 1px solid var(--line); padding-bottom: 8px; }}
    h3 {{ margin: 18px 0 8px; font-size: 15px; }}
    p {{ margin: 0 0 10px; }}
    .subtitle {{ color: var(--muted); font-size: 15px; max-width: 720px; }}
    .meta-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin: 24px 0;
    }}
    .meta {{
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 12px;
      background: linear-gradient(180deg, #fff, #fbfaf6);
    }}
    .meta span {{ display: block; color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .08em; }}
    .meta strong {{ display: block; margin-top: 4px; font-size: 13px; word-break: break-word; }}
    .callout {{
      border: 1px solid #ead28a;
      background: var(--gold-soft);
      border-radius: 10px;
      padding: 14px;
      margin: 18px 0;
    }}
    table {{ width: 100%; border-collapse: collapse; margin: 14px 0 24px; font-size: 12px; }}
    th {{
      text-align: left;
      color: #374151;
      background: #f2f4f7;
      border-bottom: 1px solid var(--line);
      padding: 9px 8px;
      text-transform: uppercase;
      font-size: 10px;
      letter-spacing: .08em;
    }}
    td {{ border-bottom: 1px solid #e7ebf0; padding: 9px 8px; vertical-align: top; }}
    .hash {{ font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 10px; word-break: break-all; color: var(--muted); }}
    .footer {{ margin-top: 36px; padding-top: 18px; border-top: 2px solid var(--gold); color: var(--muted); font-size: 11px; }}
    @media print {{
      body {{ background: #fff; }}
      .page {{ max-width: none; padding: 24px; }}
    }}
  </style>
</head>
<body>
  <main class="page" data-artifact-type="{escape(artifact_type)}">
    <div class="eyebrow">Carteira Alpha 360 Premium Research</div>
    <h1>{escape(title)}</h1>
    <p class="subtitle">{escape(subtitle)}</p>
    <section class="meta-grid" aria-label="Metadados da publicacao">
      {_meta_html("Periodo", period)}
      {_meta_html("Versao", str(version.get("version") or snapshot.version_label or ""))}
      {_meta_html("Snapshot", snapshot.snapshot_hash[:14])}
      {_meta_html("Gerado em", generated_at[:19])}
    </section>
    <section class="callout">
      <strong>Pacote renderizado a partir de snapshot imutavel.</strong>
      <p>Este HTML usa apenas dados aprovados e travados no snapshot. Dados de mercado ao vivo nao alteram esta edicao.</p>
    </section>
    {html_sections}
    <h2>Ativos e papeis no relatorio</h2>
    <table>
      <thead><tr><th>Ativo</th><th>Nome</th><th>Papel</th><th>Peso</th><th>Leitura</th></tr></thead>
      <tbody>{asset_rows}</tbody>
    </table>
    <h2>Comite e aprovacao</h2>
    <p>{escape(committee_summary)}</p>
    <table>
      <thead><tr><th>Etapa</th><th>Decisao</th><th>Responsavel</th><th>Comentario</th></tr></thead>
      <tbody>
        <tr><td>Revisao</td><td>{escape(str(review.get("decision") or ""))}</td><td>{escape(str(review.get("reviewerUserId") or ""))}</td><td>{escape(str(review.get("comments") or ""))}</td></tr>
        <tr><td>Aprovacao</td><td>{escape(str(approval.get("decision") or ""))}</td><td>{escape(str(approval.get("approverUserId") or ""))}</td><td>{escape(str(approval.get("comments") or ""))}</td></tr>
      </tbody>
    </table>
    <h2>Atribuicao de performance</h2>
    <p>{escape(attribution_summary)}</p>
    <h2>Fontes</h2>
    <table>
      <thead><tr><th>Fonte</th><th>Tipo</th><th>Provedor</th><th>Referencia</th></tr></thead>
      <tbody>{source_rows}</tbody>
    </table>
    <h2>Evidencias</h2>
    <table>
      <thead><tr><th>Dominio</th><th>Campo</th><th>Fonte</th><th>Qualidade</th></tr></thead>
      <tbody>{evidence_rows}</tbody>
    </table>
    <footer class="footer">
      <p>{escape(disclaimer or "Material educacional e analitico. Nao representa promessa de rentabilidade, garantia de resultado ou ordem de compra/venda.")}</p>
      <p class="hash">snapshotHash={escape(snapshot.snapshot_hash)} contentHash={escape(snapshot.content_hash)} sourceHash={escape(snapshot.source_hash)} evidenceHash={escape(snapshot.evidence_hash)} approvalHash={escape(snapshot.approval_hash)}</p>
    </footer>
  </main>
</body>
</html>"""

    return {"title": title, "htmlContent": html, "plainText": plain}


def _section_html(section: dict[str, Any]) -> str:
    title = str(section.get("title") or section.get("key") or "Secao")
    content = str(section.get("contentMarkdown") or section.get("content") or "")
    confidence = _number(section.get("confidence"))
    body = _markdown_to_html(content)
    gaps = section.get("dataGaps") or []
    gaps_html = ""
    if gaps:
        gaps_html = "<ul>" + "".join(f"<li>{escape(str(item))}</li>" for item in gaps[:8]) + "</ul>"
    return f"<section><h2>{escape(title)} <small style=\"color:#6b7280;font-size:11px;\">{confidence:.0f}/100</small></h2>{body}{gaps_html}</section>"


def _markdown_to_html(markdown: str) -> str:
    lines = [line.rstrip() for line in markdown.splitlines()]
    blocks: list[str] = []
    list_items: list[str] = []

    def flush_list() -> None:
        if list_items:
            blocks.append("<ul>" + "".join(list_items) + "</ul>")
            list_items.clear()

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush_list()
            continue
        if stripped.startswith("### "):
            flush_list()
            blocks.append(f"<h3>{escape(stripped[4:])}</h3>")
        elif stripped.startswith("## "):
            flush_list()
            blocks.append(f"<h2>{escape(stripped[3:])}</h2>")
        elif stripped.startswith("# "):
            flush_list()
            blocks.append(f"<h3>{escape(stripped[2:])}</h3>")
        elif stripped.startswith("- "):
            list_items.append(f"<li>{escape(stripped[2:])}</li>")
        else:
            flush_list()
            blocks.append(f"<p>{escape(stripped)}</p>")
    flush_list()
    return "\n".join(blocks)


def _asset_row_html(asset: dict[str, Any]) -> str:
    ticker = str(asset.get("ticker") or "")
    name = str(asset.get("name") or asset.get("assetName") or "")
    role = str(asset.get("role") or "")
    target = _number(asset.get("targetWeight"))
    classification = str(asset.get("classification") or asset.get("ratingClassification") or "")
    return (
        "<tr>"
        f"<td><strong>{escape(ticker)}</strong></td>"
        f"<td>{escape(name)}</td>"
        f"<td>{escape(role)}</td>"
        f"<td>{target:.2f}%</td>"
        f"<td>{escape(classification)}</td>"
        "</tr>"
    )


def _source_row_html(source: dict[str, Any]) -> str:
    return (
        "<tr>"
        f"<td>{escape(str(source.get('title') or source.get('name') or source.get('sourceName') or 'Fonte'))}</td>"
        f"<td>{escape(str(source.get('sourceType') or source.get('type') or ''))}</td>"
        f"<td>{escape(str(source.get('provider') or ''))}</td>"
        f"<td class=\"hash\">{escape(str(source.get('url') or source.get('sourceRef') or source.get('reference') or ''))}</td>"
        "</tr>"
    )


def _evidence_row_html(item: dict[str, Any]) -> str:
    return (
        "<tr>"
        f"<td>{escape(str(item.get('domain') or item.get('evidenceDomain') or ''))}</td>"
        f"<td>{escape(str(item.get('fieldName') or item.get('field') or item.get('id') or ''))}</td>"
        f"<td>{escape(str(item.get('provider') or item.get('sourceType') or ''))}</td>"
        f"<td>{_number(item.get('qualityScore') or item.get('confidence')):.0f}/100</td>"
        "</tr>"
    )


def _attribution_summary(attribution: dict[str, Any]) -> str:
    if not attribution:
        return "Atribuicao de performance nao registrada no snapshot."
    return (
        f"Retorno da carteira: {_number(attribution.get('portfolioReturnPct')):.2f}%. "
        f"Benchmark: {attribution.get('benchmarkName') or 'nao informado'} "
        f"({_number(attribution.get('benchmarkReturnPct')):.2f}%). "
        f"Qualidade media dos dados: {_number(attribution.get('dataQualityScore')):.0f}/100."
    )


def _plain_text(
    title: str,
    subtitle: str,
    period: str,
    sections: list[dict[str, Any]],
    assets: list[dict[str, Any]],
    sources: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    disclaimer: str,
) -> str:
    lines = [
        "Carteira Alpha 360 Premium Research",
        title,
        subtitle,
        f"Periodo: {period}",
        "",
        "Secoes:",
    ]
    lines.extend(f"- {section.get('title') or section.get('key')}" for section in sections)
    lines.append("")
    lines.append("Ativos:")
    lines.extend(f"- {asset.get('ticker')}: {asset.get('role') or ''}" for asset in assets)
    lines.append("")
    lines.append(f"Fontes: {len(sources)} | Evidencias: {len(evidence)}")
    lines.append(disclaimer)
    return "\n".join(str(line) for line in lines)


def _meta_html(label: str, value: str) -> str:
    return f"<div class=\"meta\"><span>{escape(label)}</span><strong>{escape(value or '-')}</strong></div>"


def _empty_row_html(colspan: int, text: str) -> str:
    return f"<tr><td colspan=\"{colspan}\">{escape(text)}</td></tr>"


def _number(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, default=_json_default)


def _json_load(raw: str | None, default: Any) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)
