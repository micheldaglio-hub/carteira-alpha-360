from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import httpx

from app.core.config import get_settings


def _number(value: Any) -> float:
    try:
        return round(float(value or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def empty_trading_desk_summary(*, status: str = "disabled", message: str = "") -> dict:
    return {
        "enabled": status != "disabled",
        "connected": False,
        "status": status,
        "message": message,
        "source": "trading_desk_ev_plus",
        "name": "Trading Desk EV+",
        "currency": "BRL",
        "currentBalance": 0.0,
        "initialCapital": 0.0,
        "realizedPnl": 0.0,
        "openPnl": 0.0,
        "totalPnl": 0.0,
        "totalPnlPct": 0.0,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }


def _normalize_payload(payload: dict[str, Any], *, status: str = "connected", message: str = "") -> dict:
    initial_capital = _number(payload.get("initialCapital"))
    realized_pnl = _number(payload.get("realizedPnl"))
    open_pnl = _number(payload.get("openPnl"))
    total_pnl = _number(payload.get("totalPnl"))
    if total_pnl == 0 and (realized_pnl or open_pnl):
        total_pnl = _number(realized_pnl + open_pnl)

    current_balance = _number(payload.get("currentBalance"))
    if current_balance == 0 and (initial_capital or total_pnl):
        current_balance = _number(initial_capital + total_pnl)

    total_pnl_pct = _number(payload.get("totalPnlPct"))
    if total_pnl_pct == 0 and initial_capital > 0:
        total_pnl_pct = round(total_pnl / initial_capital * 100, 2)

    return {
        "enabled": True,
        "connected": True,
        "status": status,
        "message": message,
        "source": payload.get("source") or "trading_desk_ev_plus",
        "name": payload.get("name") or "Trading Desk EV+",
        "currency": payload.get("currency") or "BRL",
        "currentBalance": current_balance,
        "initialCapital": initial_capital,
        "realizedPnl": realized_pnl,
        "openPnl": open_pnl,
        "totalPnl": total_pnl,
        "totalPnlPct": total_pnl_pct,
        "updatedAt": payload.get("updatedAt") or datetime.now(timezone.utc).isoformat(),
    }


def _latest_mtime_iso(paths: list[Path]) -> str:
    existing = [path for path in paths if path.exists()]
    if not existing:
        return datetime.now(timezone.utc).isoformat()
    latest = max(path.stat().st_mtime for path in existing)
    return datetime.fromtimestamp(latest, tz=timezone.utc).isoformat()


def _read_local_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_trading_desk_local_summary() -> dict | None:
    settings = get_settings()
    if not settings.trading_desk_local_path:
        return None

    base_path = Path(settings.trading_desk_local_path).expanduser()
    config_path = base_path / "config_banca.json"
    history_path = base_path / "historico_financeiro.json"
    if not base_path.exists():
        return None

    try:
        config = _read_local_json(config_path, {})
        history = _read_local_json(history_path, [])
    except (OSError, json.JSONDecodeError):
        return None

    initial_capital = _number(config.get("banca_inicial") or config.get("initialCapital"))
    realized_pnl = 0.0
    if isinstance(history, list):
        for item in history:
            if not isinstance(item, dict):
                continue
            realized_pnl += _number(item.get("lucro"))
    realized_pnl = round(realized_pnl, 2)
    current_balance = round(initial_capital + realized_pnl, 2)
    total_pnl_pct = round(realized_pnl / initial_capital * 100, 2) if initial_capital > 0 else 0.0

    return _normalize_payload(
        {
            "source": "trading_desk_ev_plus",
            "name": "Trading Desk EV+",
            "currency": "BRL",
            "currentBalance": current_balance,
            "initialCapital": initial_capital,
            "realizedPnl": realized_pnl,
            "openPnl": 0,
            "totalPnl": realized_pnl,
            "totalPnlPct": total_pnl_pct,
            "updatedAt": _latest_mtime_iso([config_path, history_path]),
        },
        status="local_files",
        message="Dados lidos dos arquivos locais do Trading Desk EV+.",
    )


def get_trading_desk_summary(client: httpx.Client | None = None) -> dict:
    settings = get_settings()
    if not settings.trading_desk_enabled:
        return empty_trading_desk_summary(status="disabled")
    if not settings.trading_desk_integration_key:
        local_summary = get_trading_desk_local_summary()
        if local_summary is not None:
            return local_summary
        return empty_trading_desk_summary(status="missing_key", message="TRADING_DESK_INTEGRATION_KEY nao configurada.")

    base_url = settings.trading_desk_api_url.rstrip("/")
    url = f"{base_url}/api/integrations/carteira-alpha/summary"
    headers = {"X-Integration-Key": settings.trading_desk_integration_key}

    owns_client = client is None
    client = client or httpx.Client(timeout=settings.trading_desk_timeout_seconds)
    try:
        response = client.get(url, headers=headers)
        if response.status_code == 401:
            local_summary = get_trading_desk_local_summary()
            if local_summary is not None:
                return local_summary
            return empty_trading_desk_summary(status="unauthorized", message="Chave de integracao recusada pelo Trading Desk.")
        response.raise_for_status()
        payload = response.json()
    except httpx.TimeoutException:
        local_summary = get_trading_desk_local_summary()
        if local_summary is not None:
            return local_summary
        return empty_trading_desk_summary(status="timeout", message="Trading Desk nao respondeu dentro do tempo limite.")
    except httpx.HTTPError as exc:
        local_summary = get_trading_desk_local_summary()
        if local_summary is not None:
            return local_summary
        return empty_trading_desk_summary(status="unavailable", message=str(exc)[:240])
    except ValueError:
        local_summary = get_trading_desk_local_summary()
        if local_summary is not None:
            return local_summary
        return empty_trading_desk_summary(status="invalid_payload", message="Trading Desk retornou JSON invalido.")
    finally:
        if owns_client:
            client.close()

    return _normalize_payload(payload)
