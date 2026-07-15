from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from html import escape
from io import BytesIO
from typing import Any

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PublicationArtifact
from app.premium_research.renderer import artifact_to_dict
from app.premium_research.snapshot_engine import verify_snapshot_integrity
from app.services.data_lineage import record_data_evidence


PDF_PUBLISHER_VERSION = "2026.07.pdf1"
PDF_PUBLISHER_ENGINE = "publication_pdf_publisher"
SUPPORTED_SOURCE_TYPES = {"html", "html_print"}


class PublicationPdfError(ValueError):
    """Raised when a premium HTML artifact cannot be converted to PDF safely."""


def render_pdf_from_html_artifact(
    db: Session,
    *,
    html_artifact: PublicationArtifact,
    user_id: str | None = None,
    force: bool = False,
    commit: bool = True,
) -> dict[str, Any]:
    """Create a binary PDF artifact from a locked HTML artifact.

    The PDF is generated from the same immutable snapshot used by the source
    HTML. The HTML artifact hash is stored as the direct source artifact hash,
    so future delivery/download records can prove the PDF came from the exact
    approved HTML package.
    """

    if html_artifact.artifact_type not in SUPPORTED_SOURCE_TYPES:
        raise PublicationPdfError("PDF premium exige um artefato HTML como origem.")
    if not html_artifact.snapshot:
        raise PublicationPdfError("Artefato HTML sem snapshot de origem.")

    integrity = verify_snapshot_integrity(html_artifact.snapshot)
    if integrity.get("status") != "ok":
        raise PublicationPdfError("Snapshot de origem nao passou na verificacao de integridade.")

    existing = db.execute(
        select(PublicationArtifact).where(
            PublicationArtifact.snapshot_id == html_artifact.snapshot_id,
            PublicationArtifact.artifact_type == "pdf",
            PublicationArtifact.render_version == PDF_PUBLISHER_VERSION,
            PublicationArtifact.source_artifact_id == html_artifact.id,
        )
    ).scalar_one_or_none()
    if existing is not None and not force:
        payload = artifact_to_dict(existing, include_content=False)
        payload["alreadyExists"] = True
        return payload

    snapshot_payload = _json_load(html_artifact.snapshot.payload_json, {})
    pdf_bytes = _build_pdf_bytes(html_artifact.snapshot, snapshot_payload, html_artifact=html_artifact)
    page_count = _page_count(pdf_bytes)
    pdf_hash = _hash_bytes(
        b"|".join(
            [
                PDF_PUBLISHER_VERSION.encode("utf-8"),
                html_artifact.artifact_hash.encode("utf-8"),
                html_artifact.source_snapshot_hash.encode("utf-8"),
                pdf_bytes,
            ]
        )
    )
    plain_text = _plain_text(snapshot_payload, page_count=page_count)
    manifest = {
        "renderEngine": PDF_PUBLISHER_ENGINE,
        "renderVersion": PDF_PUBLISHER_VERSION,
        "artifactType": "pdf",
        "contentType": "application/pdf",
        "fileExtension": "pdf",
        "publicationId": html_artifact.publication_id,
        "publicationVersionId": html_artifact.publication_version_id,
        "snapshotId": html_artifact.snapshot_id,
        "sourceArtifactId": html_artifact.id,
        "sourceHtmlArtifactHash": html_artifact.artifact_hash,
        "sourceSnapshotHash": html_artifact.source_snapshot_hash,
        "artifactHash": pdf_hash,
        "contentSizeBytes": len(pdf_bytes),
        "pageCount": page_count,
        "period": html_artifact.period,
        "generatedAt": datetime.now(UTC).isoformat(),
    }

    artifact = existing or PublicationArtifact(
        publication_id=html_artifact.publication_id,
        publication_version_id=html_artifact.publication_version_id,
        snapshot_id=html_artifact.snapshot_id,
        period=html_artifact.period,
        artifact_type="pdf",
    )
    artifact.status = "rendered"
    artifact.title = f"{html_artifact.title} - PDF"[:220]
    artifact.content_type = "application/pdf"
    artifact.file_extension = "pdf"
    artifact.render_engine = PDF_PUBLISHER_ENGINE
    artifact.render_version = PDF_PUBLISHER_VERSION
    artifact.source_artifact_id = html_artifact.id
    artifact.source_snapshot_hash = html_artifact.source_snapshot_hash
    artifact.artifact_hash = pdf_hash
    artifact.html_content = ""
    artifact.binary_content = pdf_bytes
    artifact.plain_text = plain_text
    artifact.content_size_bytes = len(pdf_bytes)
    artifact.page_count = page_count
    artifact.manifest_json = _json(manifest)
    artifact.metadata_json = _json(
        {
            "snapshotIntegrity": integrity,
            "artifactPurpose": "premium_research_pdf_binary",
            "renderedFromHtmlArtifact": html_artifact.id,
            "sourceHtmlArtifactHash": html_artifact.artifact_hash,
            "sourceSnapshotHash": html_artifact.source_snapshot_hash,
        }
    )
    artifact.created_by_user_id = user_id
    if existing is None:
        db.add(artifact)
    db.flush()

    evidence_row = record_data_evidence(
        db,
        user_id=user_id,
        domain="premium_research_pdf",
        field_name="pdf_hash",
        value_text=pdf_hash,
        unit="sha256",
        provider=PDF_PUBLISHER_ENGINE,
        source_type="formula",
        source_ref=f"publicationArtifact:{html_artifact.id}:pdf:{artifact.id}",
        formula_name="publication_pdf_binary_hash",
        formula_version=PDF_PUBLISHER_VERSION,
        input_payload=manifest,
        confidence=96,
        quality_score=96,
        status="ok",
        metadata={
            "sourceArtifactId": html_artifact.id,
            "artifactId": artifact.id,
            "pageCount": page_count,
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


def _build_pdf_bytes(snapshot, payload: dict[str, Any], *, html_artifact: PublicationArtifact) -> bytes:
    publication = payload.get("publication") or {}
    version = payload.get("version") or {}
    sections = list(payload.get("sections") or [])
    assets = list(payload.get("assets") or [])
    sources = list(payload.get("sources") or [])
    evidence = list(payload.get("evidence") or [])
    committee = payload.get("committee") or {}
    attribution = payload.get("attribution") or {}
    disclaimer = str(payload.get("legalDisclaimer") or "Material analitico. Nao representa promessa de rentabilidade ou ordem de compra/venda.")
    title = str(publication.get("title") or html_artifact.title or "Carteira Alpha 360 Premium Research")
    subtitle = str(publication.get("subtitle") or "Edicao premium aprovada")
    period = str(publication.get("period") or snapshot.period or "")

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.45 * cm,
        leftMargin=1.45 * cm,
        topMargin=1.45 * cm,
        bottomMargin=1.25 * cm,
        title=title,
        author="Carteira Alpha 360",
    )
    styles = _styles()
    story: list[Any] = []
    story.append(Paragraph("CARTEIRA ALPHA 360 PREMIUM RESEARCH", styles["Eyebrow"]))
    story.append(Paragraph(_safe(title), styles["Title"]))
    story.append(Paragraph(_safe(subtitle), styles["Subtitle"]))
    story.append(Spacer(1, 10))
    story.append(
        _meta_table(
            [
                ("Periodo", period),
                ("Versao", str(version.get("version") or snapshot.version_label or "")),
                ("Snapshot", snapshot.snapshot_hash[:14]),
                ("HTML", html_artifact.artifact_hash[:14]),
            ]
        )
    )
    story.append(Spacer(1, 10))
    story.append(Paragraph("Artefato PDF gerado a partir de snapshot imutavel e HTML aprovado. Dados vivos nao alteram esta edicao.", styles["Callout"]))

    for section in sections:
        story.extend(_section_flowables(section, styles))

    story.append(Paragraph("Ativos e papeis no relatorio", styles["H2"]))
    story.append(_asset_table(assets, styles))
    story.append(Paragraph("Comite e aprovacao", styles["H2"]))
    story.append(Paragraph(_safe(str(committee.get("summary") or "Comite sem resumo registrado no snapshot.")), styles["Body"]))
    story.append(Paragraph("Atribuicao de performance", styles["H2"]))
    story.append(Paragraph(_safe(_attribution_summary(attribution)), styles["Body"]))
    story.append(PageBreak())
    story.append(Paragraph("Fontes", styles["H2"]))
    story.append(_source_table(sources[:40], styles))
    story.append(Paragraph("Evidencias", styles["H2"]))
    story.append(_evidence_table(evidence[:40], styles))
    story.append(Spacer(1, 10))
    story.append(Paragraph(_safe(disclaimer), styles["Disclaimer"]))
    story.append(Paragraph(_safe(f"snapshotHash={snapshot.snapshot_hash}"), styles["Hash"]))
    story.append(Paragraph(_safe(f"htmlArtifactHash={html_artifact.artifact_hash}"), styles["Hash"]))
    story.append(Paragraph(_safe(f"generatedAt={datetime.now(UTC).isoformat()}"), styles["Hash"]))

    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "Eyebrow": ParagraphStyle("Eyebrow", parent=base["Normal"], fontSize=8, leading=10, textColor=colors.HexColor("#b8860b"), spaceAfter=6, alignment=TA_CENTER),
        "Title": ParagraphStyle("Title", parent=base["Title"], fontSize=22, leading=26, textColor=colors.HexColor("#111827"), spaceAfter=8),
        "Subtitle": ParagraphStyle("Subtitle", parent=base["Normal"], fontSize=10, leading=14, textColor=colors.HexColor("#4b5563"), spaceAfter=8),
        "H2": ParagraphStyle("H2", parent=base["Heading2"], fontSize=13, leading=16, textColor=colors.HexColor("#111827"), spaceBefore=14, spaceAfter=6),
        "H3": ParagraphStyle("H3", parent=base["Heading3"], fontSize=10.5, leading=13, textColor=colors.HexColor("#111827"), spaceBefore=8, spaceAfter=4),
        "Body": ParagraphStyle("Body", parent=base["BodyText"], fontSize=8.5, leading=12, textColor=colors.HexColor("#1f2937"), spaceAfter=5),
        "Bullet": ParagraphStyle("Bullet", parent=base["BodyText"], fontSize=8.3, leading=11.5, leftIndent=12, bulletIndent=4, textColor=colors.HexColor("#1f2937"), spaceAfter=3),
        "Callout": ParagraphStyle("Callout", parent=base["BodyText"], fontSize=8.5, leading=12, textColor=colors.HexColor("#5c4400"), backColor=colors.HexColor("#fff6d6"), borderColor=colors.HexColor("#e2bf4f"), borderWidth=0.6, borderPadding=6, spaceAfter=8),
        "Small": ParagraphStyle("Small", parent=base["BodyText"], fontSize=7.2, leading=9, textColor=colors.HexColor("#4b5563")),
        "Hash": ParagraphStyle("Hash", parent=base["BodyText"], fontName="Courier", fontSize=6.5, leading=8, textColor=colors.HexColor("#4b5563")),
        "Disclaimer": ParagraphStyle("Disclaimer", parent=base["BodyText"], fontSize=7.5, leading=10, textColor=colors.HexColor("#374151"), borderColor=colors.HexColor("#c7971a"), borderWidth=0.6, borderPadding=6),
    }


def _section_flowables(section: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list[Any]:
    flowables: list[Any] = []
    title = str(section.get("title") or section.get("key") or "Secao")
    confidence = _number(section.get("confidence"))
    flowables.append(Paragraph(_safe(f"{title} ({confidence:.0f}/100)"), styles["H2"]))
    content = str(section.get("contentMarkdown") or section.get("content") or "")
    flowables.extend(_markdown_flowables(content, styles))
    gaps = section.get("dataGaps") or []
    for gap in gaps[:6]:
        flowables.append(Paragraph(_safe(str(gap)), styles["Bullet"], bulletText="-"))
    return flowables


def _markdown_flowables(markdown: str, styles: dict[str, ParagraphStyle]) -> list[Any]:
    flowables: list[Any] = []
    for raw in markdown.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("# "):
            flowables.append(Paragraph(_safe(line[2:]), styles["H3"]))
        elif line.startswith("## "):
            flowables.append(Paragraph(_safe(line[3:]), styles["H3"]))
        elif line.startswith("- "):
            flowables.append(Paragraph(_safe(line[2:]), styles["Bullet"], bulletText="-"))
        else:
            flowables.append(Paragraph(_safe(line), styles["Body"]))
    return flowables


def _meta_table(items: list[tuple[str, str]]) -> Table:
    data = [[Paragraph(_safe(label), _styles()["Small"]), Paragraph(_safe(value or "-"), _styles()["Body"])] for label, value in items]
    table = Table(data, colWidths=[3.0 * cm, 12.8 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f7f4ec")),
                ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#d8dee8")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e7ebf0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _asset_table(assets: list[dict[str, Any]], styles: dict[str, ParagraphStyle]) -> Table:
    rows = [[_p("Ativo", styles), _p("Nome", styles), _p("Papel", styles), _p("Peso", styles), _p("Leitura", styles)]]
    for asset in assets[:45]:
        rows.append(
            [
                _p(str(asset.get("ticker") or ""), styles),
                _p(str(asset.get("name") or asset.get("assetName") or ""), styles),
                _p(str(asset.get("role") or ""), styles),
                _p(f"{_number(asset.get('targetWeight')):.2f}%", styles),
                _p(str(asset.get("classification") or asset.get("ratingClassification") or ""), styles),
            ]
        )
    return _table(rows, [2.2 * cm, 3.5 * cm, 4.2 * cm, 1.5 * cm, 4.8 * cm])


def _source_table(sources: list[dict[str, Any]], styles: dict[str, ParagraphStyle]) -> Table:
    rows = [[_p("Fonte", styles), _p("Tipo", styles), _p("Provedor", styles), _p("Referencia", styles)]]
    for source in sources:
        rows.append(
            [
                _p(str(source.get("title") or source.get("name") or source.get("sourceName") or "Fonte"), styles),
                _p(str(source.get("sourceType") or source.get("type") or ""), styles),
                _p(str(source.get("provider") or ""), styles),
                _p(str(source.get("url") or source.get("sourceRef") or source.get("reference") or ""), styles),
            ]
        )
    return _table(rows, [3.5 * cm, 2.4 * cm, 3.0 * cm, 7.3 * cm])


def _evidence_table(evidence: list[dict[str, Any]], styles: dict[str, ParagraphStyle]) -> Table:
    rows = [[_p("Dominio", styles), _p("Campo", styles), _p("Fonte", styles), _p("Qualidade", styles)]]
    for item in evidence:
        rows.append(
            [
                _p(str(item.get("domain") or item.get("evidenceDomain") or ""), styles),
                _p(str(item.get("fieldName") or item.get("field") or item.get("id") or ""), styles),
                _p(str(item.get("provider") or item.get("sourceType") or ""), styles),
                _p(f"{_number(item.get('qualityScore') or item.get('confidence')):.0f}/100", styles),
            ]
        )
    return _table(rows, [4.0 * cm, 4.7 * cm, 4.0 * cm, 3.5 * cm])


def _table(rows: list[list[Any]], widths: list[float]) -> Table:
    table = Table(rows, colWidths=widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f2f4f7")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#374151")),
                ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#d8dee8")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e7ebf0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _p(value: str, styles: dict[str, ParagraphStyle]) -> Paragraph:
    return Paragraph(_safe(value), styles["Small"])


def _footer(canvas, document) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#6b7280"))
    canvas.drawString(1.45 * cm, 0.65 * cm, "Carteira Alpha 360 - Premium Research")
    canvas.drawRightString(A4[0] - 1.45 * cm, 0.65 * cm, f"Pagina {document.page}")
    canvas.restoreState()


def _attribution_summary(attribution: dict[str, Any]) -> str:
    if not attribution:
        return "Atribuicao de performance nao registrada no snapshot."
    return (
        f"Retorno da carteira: {_number(attribution.get('portfolioReturnPct')):.2f}%. "
        f"Benchmark: {attribution.get('benchmarkName') or 'nao informado'} "
        f"({_number(attribution.get('benchmarkReturnPct')):.2f}%). "
        f"Qualidade media dos dados: {_number(attribution.get('dataQualityScore')):.0f}/100."
    )


def _plain_text(payload: dict[str, Any], *, page_count: int) -> str:
    publication = payload.get("publication") or {}
    assets = payload.get("assets") or []
    return "\n".join(
        [
            "Carteira Alpha 360 Premium Research PDF",
            str(publication.get("title") or ""),
            f"Periodo: {publication.get('period') or ''}",
            f"Paginas: {page_count}",
            f"Ativos: {len(assets)}",
        ]
    )


def _page_count(pdf_bytes: bytes) -> int:
    reader = PdfReader(BytesIO(pdf_bytes))
    return len(reader.pages)


def _safe(value: str) -> str:
    return escape(str(value or "")).replace("\n", "<br/>")


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _hash_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


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
