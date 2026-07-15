from __future__ import annotations

import html
from dataclasses import dataclass
from typing import Any

from app.core.config import get_settings
from app.models import DistributionCampaign, DistributionRecipient


@dataclass(frozen=True)
class DistributionEmailContent:
    subject: str
    html_body: str
    text_body: str
    preview_text: str


def render_distribution_email(
    *,
    campaign: DistributionCampaign,
    recipient: DistributionRecipient,
) -> DistributionEmailContent:
    payload = _payload(campaign)
    publication = payload.get("publication") or {}
    artifact = payload.get("artifact") or {}
    settings = get_settings()
    base_url = (settings.distribution_public_base_url or settings.billing_public_base_url or "").rstrip("/")
    publication_url = f"{base_url}/premium" if base_url else ""
    title = str(publication.get("title") or campaign.subject or "Carteira Alpha Premium")
    period = str(publication.get("period") or "")
    subtitle = str(publication.get("subtitle") or campaign.preview_text or "")
    artifact_hash = str(artifact.get("artifactHash") or artifact.get("artifact_hash") or "")
    recipient_name = recipient.full_name or recipient.email.split("@")[0]
    preview = campaign.preview_text or subtitle or "Nova edicao premium disponivel."
    html_body = _html_document(
        recipient_name=recipient_name,
        title=title,
        subtitle=subtitle,
        period=period,
        preview=preview,
        publication_url=publication_url,
        artifact_hash=artifact_hash,
    )
    text_body = _text_document(
        recipient_name=recipient_name,
        title=title,
        subtitle=subtitle,
        period=period,
        publication_url=publication_url,
        artifact_hash=artifact_hash,
    )
    return DistributionEmailContent(
        subject=campaign.subject or title,
        html_body=html_body,
        text_body=text_body,
        preview_text=preview,
    )


def _html_document(
    *,
    recipient_name: str,
    title: str,
    subtitle: str,
    period: str,
    preview: str,
    publication_url: str,
    artifact_hash: str,
) -> str:
    safe_title = html.escape(title)
    safe_subtitle = html.escape(subtitle)
    safe_period = html.escape(period)
    safe_name = html.escape(recipient_name)
    safe_preview = html.escape(preview)
    safe_hash = html.escape(artifact_hash[:16]) if artifact_hash else "registrado"
    button = ""
    if publication_url:
        safe_url = html.escape(publication_url, quote=True)
        button = (
            f'<a href="{safe_url}" '
            'style="display:inline-block;background:#facc15;color:#111827;'
            'font-weight:700;text-decoration:none;padding:12px 18px;border-radius:8px;">'
            "Abrir area premium</a>"
        )
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title}</title>
</head>
<body style="margin:0;background:#07090d;color:#f8fafc;font-family:Arial,Helvetica,sans-serif;">
  <span style="display:none!important;opacity:0;overflow:hidden;height:0;width:0;">{safe_preview}</span>
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#07090d;padding:24px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:680px;background:#11151d;border:1px solid #2b303b;border-radius:12px;overflow:hidden;">
          <tr>
            <td style="padding:22px 24px;border-bottom:1px solid #2b303b;">
              <div style="font-size:12px;letter-spacing:3px;color:#facc15;font-weight:700;text-transform:uppercase;">Carteira Alpha 360</div>
              <h1 style="margin:8px 0 0;font-size:24px;line-height:1.25;color:#ffffff;">{safe_title}</h1>
              <p style="margin:8px 0 0;color:#cbd5e1;font-size:14px;line-height:1.6;">{safe_subtitle}</p>
            </td>
          </tr>
          <tr>
            <td style="padding:24px;">
              <p style="margin:0 0 16px;color:#e5e7eb;font-size:15px;line-height:1.65;">Olá, {safe_name}.</p>
              <p style="margin:0 0 18px;color:#e5e7eb;font-size:15px;line-height:1.65;">
                A edição premium do período <strong>{safe_period}</strong> está pronta para leitura.
                O conteúdo foi gerado pelo Alpha Research Publisher e passou pelos controles internos de evidências, rating, comitê e distribuição.
              </p>
              <div style="margin:18px 0;padding:14px 16px;background:#171b24;border:1px solid #2b303b;border-radius:10px;">
                <div style="font-size:12px;color:#94a3b8;text-transform:uppercase;letter-spacing:2px;">Controle de integridade</div>
                <div style="margin-top:6px;color:#f8fafc;font-weight:700;">Artefato: {safe_hash}</div>
              </div>
              {button}
              <p style="margin:22px 0 0;color:#94a3b8;font-size:12px;line-height:1.6;">
                Conteúdo informativo. Não representa promessa de rentabilidade nem ordem automática de compra ou venda.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _text_document(
    *,
    recipient_name: str,
    title: str,
    subtitle: str,
    period: str,
    publication_url: str,
    artifact_hash: str,
) -> str:
    lines = [
        f"Olá, {recipient_name}.",
        "",
        f"{title}",
        subtitle,
        f"Periodo: {period}",
        "",
        "A edição premium está pronta para leitura.",
        "O conteúdo passou pelos controles internos de evidências, rating, comitê e distribuição.",
    ]
    if publication_url:
        lines.extend(["", f"Acesse: {publication_url}"])
    if artifact_hash:
        lines.extend(["", f"Controle de integridade: {artifact_hash[:16]}"])
    lines.extend(["", "Conteúdo informativo. Não representa promessa de rentabilidade nem ordem automática de compra ou venda."])
    return "\n".join(line for line in lines if line is not None)


def _payload(campaign: DistributionCampaign) -> dict[str, Any]:
    if not campaign.payload_json:
        return {}
    try:
        import json

        return json.loads(campaign.payload_json)
    except Exception:
        return {}
