from __future__ import annotations

import smtplib
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.models import DistributionCampaign, DistributionRecipient

from .templates import render_distribution_email


@dataclass(frozen=True)
class DistributionProviderChoice:
    name: str
    configured_name: str
    fallback_reason: str = ""


@dataclass(frozen=True)
class DistributionSendResult:
    provider: str
    message_id: str
    event_type: str
    metadata: dict[str, Any] = field(default_factory=dict)


class DistributionProvider:
    name = "base"

    def send(self, *, campaign: DistributionCampaign, recipient: DistributionRecipient) -> DistributionSendResult:
        raise NotImplementedError


class MockDistributionProvider(DistributionProvider):
    name = "mock"

    def send(self, *, campaign: DistributionCampaign, recipient: DistributionRecipient) -> DistributionSendResult:
        content = render_distribution_email(campaign=campaign, recipient=recipient)
        return DistributionSendResult(
            provider=self.name,
            message_id=f"mock_msg_{campaign.id}_{recipient.id}",
            event_type="delivered",
            metadata={
                "mode": "mock",
                "subject": content.subject,
                "htmlPreviewLength": len(content.html_body),
                "textPreviewLength": len(content.text_body),
            },
        )


class ResendDistributionProvider(DistributionProvider):
    name = "resend"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def send(self, *, campaign: DistributionCampaign, recipient: DistributionRecipient) -> DistributionSendResult:
        content = render_distribution_email(campaign=campaign, recipient=recipient)
        payload = {
            "from": self.settings.distribution_from_email,
            "to": [recipient.email],
            "subject": content.subject,
            "html": content.html_body,
            "text": content.text_body,
        }
        if self.settings.distribution_reply_to:
            payload["reply_to"] = self.settings.distribution_reply_to
        response = httpx.post(
            f"{self.settings.distribution_resend_base_url.rstrip('/')}/emails",
            json=payload,
            headers={"Authorization": f"Bearer {self.settings.distribution_resend_api_key}"},
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        return DistributionSendResult(
            provider=self.name,
            message_id=str(data.get("id") or f"resend_msg_{campaign.id}_{recipient.id}"),
            event_type="sent",
            metadata={"providerResponse": data},
        )


class SmtpDistributionProvider(DistributionProvider):
    name = "smtp"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def send(self, *, campaign: DistributionCampaign, recipient: DistributionRecipient) -> DistributionSendResult:
        content = render_distribution_email(campaign=campaign, recipient=recipient)
        message = EmailMessage()
        message["Subject"] = content.subject
        message["From"] = self.settings.distribution_from_email
        message["To"] = recipient.email
        if self.settings.distribution_reply_to:
            message["Reply-To"] = self.settings.distribution_reply_to
        message.set_content(content.text_body)
        message.add_alternative(content.html_body, subtype="html")
        with smtplib.SMTP(self.settings.distribution_smtp_host, self.settings.distribution_smtp_port, timeout=15) as smtp:
            if self.settings.distribution_smtp_use_tls:
                smtp.starttls()
            if self.settings.distribution_smtp_username:
                smtp.login(self.settings.distribution_smtp_username, self.settings.distribution_smtp_password)
            smtp.send_message(message)
        return DistributionSendResult(
            provider=self.name,
            message_id=f"smtp_msg_{campaign.id}_{recipient.id}",
            event_type="sent",
            metadata={"smtpHost": self.settings.distribution_smtp_host, "smtpPort": self.settings.distribution_smtp_port},
        )


def resolve_distribution_provider(settings: Settings | None = None) -> DistributionProviderChoice:
    settings = settings or get_settings()
    configured = _normalize_provider(settings.distribution_provider)
    if configured == "mock":
        return DistributionProviderChoice(name="mock", configured_name=configured)
    if configured == "resend":
        if not settings.distribution_resend_api_key:
            return DistributionProviderChoice(
                name="mock",
                configured_name=configured,
                fallback_reason="DISTRIBUTION_RESEND_API_KEY ausente; usando mock para nao bloquear distribuicao.",
            )
        return DistributionProviderChoice(name="resend", configured_name=configured)
    if configured == "smtp":
        if not settings.distribution_smtp_host:
            return DistributionProviderChoice(
                name="mock",
                configured_name=configured,
                fallback_reason="DISTRIBUTION_SMTP_HOST ausente; usando mock para nao bloquear distribuicao.",
            )
        return DistributionProviderChoice(name="smtp", configured_name=configured)
    return DistributionProviderChoice(
        name="mock",
        configured_name=configured,
        fallback_reason=f"Provider '{configured}' nao suportado; usando mock.",
    )


def get_distribution_provider(provider_name: str | None = None, settings: Settings | None = None) -> DistributionProvider:
    settings = settings or get_settings()
    normalized = _normalize_provider(provider_name or resolve_distribution_provider(settings).name)
    if normalized == "resend":
        return ResendDistributionProvider(settings)
    if normalized == "smtp":
        return SmtpDistributionProvider(settings)
    return MockDistributionProvider()


def _normalize_provider(value: str | None) -> str:
    return (value or "mock").strip().lower().replace("-", "_") or "mock"
