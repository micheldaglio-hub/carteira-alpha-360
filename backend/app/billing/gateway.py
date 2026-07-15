from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import (
    BillingCheckoutSession,
    BillingTransaction,
    BillingWebhookEvent,
    SubscriptionPlan,
    User,
    UserSubscription,
    new_id,
)
from app.premium_research.entitlements import (
    grant_subscription_to_user,
    list_user_premium_access,
    plan_to_dict,
    seed_default_subscription_plans,
    subscription_to_dict,
)
from app.services.audit import write_audit_event


BILLING_GATEWAY_VERSION = "2026.07.billing1"
PAID_STATUSES = {"paid", "approved", "succeeded", "completed"}
TERMINAL_STATUSES = PAID_STATUSES | {"failed", "canceled", "cancelled", "expired", "refunded"}


class BillingGatewayError(ValueError):
    pass


def create_checkout_session(
    db: Session,
    *,
    user: User,
    plan_code: str,
    billing_cycle: str = "monthly",
    success_url: str = "",
    cancel_url: str = "",
    idempotency_key: str = "",
    commit: bool = True,
) -> dict[str, Any]:
    seed_default_subscription_plans(db, commit=False)
    plan = db.execute(select(SubscriptionPlan).where(SubscriptionPlan.code == plan_code)).scalar_one_or_none()
    if plan is None or plan.status != "active":
        raise BillingGatewayError("Plano nao encontrado ou indisponivel.")

    cycle = _normalize_billing_cycle(billing_cycle)
    amount = _plan_amount(plan, cycle)
    if amount <= 0:
        raise BillingGatewayError("Plano gratuito nao exige checkout de pagamento.")

    key = idempotency_key.strip()[:160] if idempotency_key else new_id()
    existing = db.execute(select(BillingCheckoutSession).where(BillingCheckoutSession.idempotency_key == key)).scalar_one_or_none()
    if existing is not None:
        return {
            "checkout": checkout_session_to_dict(existing),
            "plan": plan_to_dict(existing.plan),
            "providerMode": _provider_mode(existing.provider),
            "reused": True,
        }

    provider = _configured_provider()
    session_id = new_id()
    external_reference = f"ca360:{user.id}:{plan.code}:{cycle}:{session_id}"
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=max(15, get_settings().billing_checkout_expires_minutes))
    provider_payload = _build_provider_payload(
        provider=provider,
        session_id=session_id,
        user=user,
        plan=plan,
        billing_cycle=cycle,
        amount=amount,
        success_url=success_url,
        cancel_url=cancel_url,
        external_reference=external_reference,
    )
    session = BillingCheckoutSession(
        id=session_id,
        user_id=user.id,
        plan_id=plan.id,
        plan_code=plan.code,
        billing_cycle=cycle,
        provider=provider,
        provider_checkout_id=provider_payload["providerCheckoutId"],
        provider_customer_id=provider_payload.get("providerCustomerId", ""),
        external_reference=external_reference,
        idempotency_key=key,
        status="pending",
        currency=plan.currency,
        amount=amount,
        checkout_url=provider_payload["checkoutUrl"],
        success_url=success_url,
        cancel_url=cancel_url,
        provider_payload_json=_json(provider_payload),
        metadata_json=_json({"engineVersion": BILLING_GATEWAY_VERSION, "planCode": plan.code, "billingCycle": cycle}),
        expires_at=expires_at,
    )
    db.add(session)
    db.flush()
    _audit(
        db,
        user_id=user.id,
        action="checkout_created",
        message=f"Checkout {session.id} criado para o plano {plan.code}.",
        resource_id=session.id,
        metadata={"provider": provider, "planCode": plan.code, "billingCycle": cycle, "amount": float(amount)},
    )
    if commit:
        db.commit()
        db.refresh(session)
    return {
        "checkout": checkout_session_to_dict(session),
        "plan": plan_to_dict(plan),
        "providerMode": _provider_mode(provider),
        "reused": False,
    }


def process_mock_checkout_success(
    db: Session,
    *,
    session_id: str,
    user_id: str | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    session = db.get(BillingCheckoutSession, session_id)
    if session is None:
        raise BillingGatewayError("Checkout nao encontrado.")
    if session.provider != "mock":
        raise BillingGatewayError("Este endpoint so confirma pagamentos do provider mock.")
    if user_id and session.user_id != user_id:
        raise BillingGatewayError("Checkout pertence a outro usuario.")
    event_payload = {
        "id": f"mock_event_{session.id}",
        "type": "checkout.session.completed",
        "checkout_session_id": session.id,
        "provider_checkout_id": session.provider_checkout_id,
        "provider_payment_id": f"mock_payment_{session.id}",
        "status": "paid",
        "amount": float(session.amount),
        "currency": session.currency,
    }
    return process_provider_webhook(
        db,
        provider="mock",
        payload=event_payload,
        signature_header="",
        commit=commit,
    )


def process_provider_webhook(
    db: Session,
    *,
    provider: str,
    payload: dict[str, Any],
    signature_header: str = "",
    commit: bool = True,
) -> dict[str, Any]:
    normalized_provider = _normalize_provider(provider)
    event_id = str(payload.get("id") or payload.get("event_id") or _hash_payload(payload))[:160]
    existing = db.execute(
        select(BillingWebhookEvent).where(
            BillingWebhookEvent.provider == normalized_provider,
            BillingWebhookEvent.event_id == event_id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        return {"webhook": webhook_event_to_dict(existing), "duplicate": True, "transaction": None, "subscription": None}

    signature_valid = _verify_signature(normalized_provider, payload, signature_header)
    event = BillingWebhookEvent(
        provider=normalized_provider,
        event_id=event_id,
        event_type=str(payload.get("type") or payload.get("event_type") or payload.get("action") or "payment.updated")[:120],
        status="received",
        signature_valid=signature_valid,
        raw_payload_json=_json(payload),
    )
    db.add(event)
    db.flush()
    if not signature_valid:
        event.status = "failed"
        event.processing_error = "Assinatura do webhook invalida."
        event.processed_at = datetime.now(UTC)
        if commit:
            db.commit()
            db.refresh(event)
        raise BillingGatewayError("Assinatura do webhook invalida.")

    try:
        result = _apply_payment_event(db, provider=normalized_provider, payload=payload, event=event)
        event.status = "processed"
        event.processed_at = datetime.now(UTC)
        if commit:
            db.commit()
            db.refresh(event)
            if result.get("transactionModel") is not None:
                db.refresh(result["transactionModel"])
        transaction = result.get("transactionModel")
        subscription = result.get("subscriptionModel")
        return {
            "webhook": webhook_event_to_dict(event),
            "duplicate": False,
            "transaction": transaction_to_dict(transaction) if transaction else None,
            "subscription": subscription_to_dict(subscription) if subscription else result.get("subscription"),
        }
    except Exception as exc:
        event.status = "failed"
        event.processing_error = str(exc)[:2000]
        event.processed_at = datetime.now(UTC)
        if commit:
            db.commit()
            db.refresh(event)
        raise


def list_user_billing(db: Session, *, user_id: str, limit: int = 20) -> dict[str, Any]:
    checkouts = list(
        db.execute(
            select(BillingCheckoutSession)
            .where(BillingCheckoutSession.user_id == user_id)
            .order_by(desc(BillingCheckoutSession.created_at))
            .limit(limit)
        )
        .scalars()
        .all()
    )
    transactions = list(
        db.execute(
            select(BillingTransaction)
            .where(BillingTransaction.user_id == user_id)
            .order_by(desc(BillingTransaction.created_at))
            .limit(limit)
        )
        .scalars()
        .all()
    )
    access = list_user_premium_access(db, user_id=user_id)
    return {
        "provider": _configured_provider(),
        "providerMode": _provider_mode(_configured_provider()),
        "checkouts": [checkout_session_to_dict(row) for row in checkouts],
        "transactions": [transaction_to_dict(row) for row in transactions],
        "premiumAccess": access,
    }


def checkout_session_to_dict(row: BillingCheckoutSession) -> dict[str, Any]:
    return {
        "id": row.id,
        "userId": row.user_id,
        "planId": row.plan_id,
        "planCode": row.plan_code,
        "billingCycle": row.billing_cycle,
        "provider": row.provider,
        "providerCheckoutId": row.provider_checkout_id,
        "externalReference": row.external_reference,
        "status": row.status,
        "currency": row.currency,
        "amount": _number(row.amount),
        "checkoutUrl": row.checkout_url,
        "successUrl": row.success_url,
        "cancelUrl": row.cancel_url,
        "expiresAt": row.expires_at.isoformat() if row.expires_at else "",
        "completedAt": row.completed_at.isoformat() if row.completed_at else "",
        "metadata": _json_load(row.metadata_json, {}),
        "createdAt": row.created_at.isoformat() if row.created_at else "",
    }


def transaction_to_dict(row: BillingTransaction) -> dict[str, Any]:
    return {
        "id": row.id,
        "userId": row.user_id,
        "checkoutSessionId": row.checkout_session_id or "",
        "subscriptionId": row.subscription_id or "",
        "planId": row.plan_id or "",
        "provider": row.provider,
        "providerPaymentId": row.provider_payment_id,
        "externalReference": row.external_reference,
        "status": row.status,
        "eventType": row.event_type,
        "currency": row.currency,
        "amount": _number(row.amount),
        "paidAt": row.paid_at.isoformat() if row.paid_at else "",
        "metadata": _json_load(row.metadata_json, {}),
        "createdAt": row.created_at.isoformat() if row.created_at else "",
    }


def webhook_event_to_dict(row: BillingWebhookEvent) -> dict[str, Any]:
    return {
        "id": row.id,
        "provider": row.provider,
        "eventId": row.event_id,
        "eventType": row.event_type,
        "status": row.status,
        "signatureValid": row.signature_valid,
        "checkoutSessionId": row.checkout_session_id or "",
        "transactionId": row.transaction_id or "",
        "processingError": row.processing_error,
        "receivedAt": row.received_at.isoformat() if row.received_at else "",
        "processedAt": row.processed_at.isoformat() if row.processed_at else "",
    }


def _apply_payment_event(
    db: Session,
    *,
    provider: str,
    payload: dict[str, Any],
    event: BillingWebhookEvent,
) -> dict[str, Any]:
    checkout_session_id = str(payload.get("checkout_session_id") or payload.get("session_id") or "")[:32]
    provider_checkout_id = str(payload.get("provider_checkout_id") or payload.get("checkout_id") or payload.get("data", {}).get("id") or "")[:160]
    status = _normalize_payment_status(str(payload.get("status") or payload.get("payment_status") or "pending"))
    session = None
    if checkout_session_id:
        session = db.get(BillingCheckoutSession, checkout_session_id)
    if session is None and provider_checkout_id:
        session = db.execute(
            select(BillingCheckoutSession).where(
                BillingCheckoutSession.provider == provider,
                BillingCheckoutSession.provider_checkout_id == provider_checkout_id,
            )
        ).scalar_one_or_none()
    if session is None:
        raise BillingGatewayError("Checkout relacionado ao webhook nao foi encontrado.")

    event.checkout_session_id = session.id
    payment_id = str(payload.get("provider_payment_id") or payload.get("payment_id") or f"{provider}_payment_{session.id}")[:160]
    transaction = db.execute(
        select(BillingTransaction).where(
            BillingTransaction.provider == provider,
            BillingTransaction.provider_payment_id == payment_id,
        )
    ).scalar_one_or_none()
    if transaction is None:
        transaction = BillingTransaction(
            user_id=session.user_id,
            checkout_session_id=session.id,
            plan_id=session.plan_id,
            provider=provider,
            provider_payment_id=payment_id,
            external_reference=session.external_reference,
        )
        db.add(transaction)

    transaction.status = status
    transaction.event_type = event.event_type
    transaction.currency = session.currency
    transaction.amount = _decimal(payload.get("amount"), fallback=session.amount)
    transaction.raw_payload_json = _json(payload)
    transaction.metadata_json = _json({"engineVersion": BILLING_GATEWAY_VERSION, "checkoutSessionId": session.id})
    if status in PAID_STATUSES:
        transaction.paid_at = datetime.now(UTC)
        session.status = "paid"
        session.completed_at = transaction.paid_at
    elif status in TERMINAL_STATUSES:
        session.status = status
    else:
        session.status = "pending"
    db.flush()
    event.transaction_id = transaction.id

    subscription = None
    subscription_payload = None
    if status in PAID_STATUSES:
        period_days = 366 if session.billing_cycle == "annual" else 31
        granted = grant_subscription_to_user(
            db,
            user_id=session.user_id,
            plan_code=session.plan_code,
            status="active",
            period_days=period_days,
            billing_provider=provider,
            metadata={
                "engineVersion": BILLING_GATEWAY_VERSION,
                "checkoutSessionId": session.id,
                "transactionId": transaction.id,
                "providerPaymentId": payment_id,
                "billingCycle": session.billing_cycle,
            },
            commit=False,
        )
        subscription_payload = granted["subscription"]
        subscription = db.get(UserSubscription, subscription_payload["id"])
        transaction.subscription_id = subscription_payload["id"]
        _audit(
            db,
            user_id=session.user_id,
            action="payment_approved",
            message=f"Pagamento confirmado para o plano {session.plan_code}.",
            resource_id=transaction.id,
            metadata={
                "provider": provider,
                "checkoutSessionId": session.id,
                "transactionId": transaction.id,
                "planCode": session.plan_code,
                "amount": float(transaction.amount),
            },
        )
    db.flush()
    return {"transactionModel": transaction, "subscriptionModel": subscription, "subscription": subscription_payload}


def _build_provider_payload(
    *,
    provider: str,
    session_id: str,
    user: User,
    plan: SubscriptionPlan,
    billing_cycle: str,
    amount: Decimal,
    success_url: str,
    cancel_url: str,
    external_reference: str,
) -> dict[str, Any]:
    if provider == "mock":
        return {
            "provider": "mock",
            "providerCheckoutId": f"mock_checkout_{session_id}",
            "providerCustomerId": f"mock_customer_{user.id}",
            "checkoutUrl": success_url or f"/api/billing/mock/checkout/{session_id}/success",
            "externalReference": external_reference,
            "amount": float(amount),
            "currency": plan.currency,
            "planCode": plan.code,
            "billingCycle": billing_cycle,
            "testMode": True,
        }
    raise BillingGatewayError(
        f"Provider de pagamento '{provider}' ainda nao esta ativo. Configure billing_payment_provider=mock ou implemente as credenciais reais."
    )


def _verify_signature(provider: str, payload: dict[str, Any], signature_header: str) -> bool:
    if provider == "mock":
        secret = get_settings().billing_webhook_secret
        if not secret:
            return True
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature_header or "", expected)
    return False


def _configured_provider() -> str:
    return _normalize_provider(get_settings().billing_payment_provider)


def _normalize_provider(value: str) -> str:
    normalized = (value or "mock").strip().lower().replace("-", "_")
    if normalized in {"local", "test"}:
        return "mock"
    if normalized in {"mercado_pago", "mercadopago"}:
        return "mercadopago"
    return normalized or "mock"


def _provider_mode(provider: str) -> str:
    return "test" if provider == "mock" else "external"


def _normalize_billing_cycle(value: str) -> str:
    normalized = (value or "monthly").strip().lower()
    if normalized in {"annual", "yearly", "ano", "anual"}:
        return "annual"
    return "monthly"


def _plan_amount(plan: SubscriptionPlan, billing_cycle: str) -> Decimal:
    return Decimal(plan.annual_price if billing_cycle == "annual" else plan.monthly_price)


def _normalize_payment_status(value: str) -> str:
    normalized = (value or "pending").strip().lower()
    if normalized in {"approved", "succeeded", "completed", "paid"}:
        return "paid"
    if normalized in {"cancelled"}:
        return "canceled"
    return normalized[:32] or "pending"


def _decimal(value: Any, *, fallback: Decimal) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal(fallback)


def _hash_payload(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _audit(
    db: Session,
    *,
    user_id: str,
    action: str,
    message: str,
    resource_id: str,
    metadata: dict[str, Any],
) -> None:
    write_audit_event(
        db,
        event_type="billing_gateway",
        category="billing",
        action=action,
        user_id=user_id,
        severity="info",
        resource_type="billing",
        resource_id=resource_id,
        message=message,
        metadata={"engineVersion": BILLING_GATEWAY_VERSION, **metadata},
    )


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


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
