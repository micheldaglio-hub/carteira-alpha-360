from __future__ import annotations

import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import httpx

from app.services.trading_desk_integration import get_trading_desk_summary


def _settings(**overrides):
    values = {
        "trading_desk_enabled": True,
        "trading_desk_api_url": "http://trading.local",
        "trading_desk_integration_key": "secret",
        "trading_desk_timeout_seconds": 1,
        "trading_desk_local_path": "",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class TradingDeskIntegrationTests(unittest.TestCase):
    def test_disabled_integration_returns_zero_fallback(self) -> None:
        with patch("app.services.trading_desk_integration.get_settings", return_value=_settings(trading_desk_enabled=False)):
            summary = get_trading_desk_summary()

        self.assertFalse(summary["enabled"])
        self.assertFalse(summary["connected"])
        self.assertEqual(summary["currentBalance"], 0)

    def test_connected_integration_normalizes_summary(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.headers["X-Integration-Key"], "secret")
            return httpx.Response(
                200,
                json={
                    "source": "trading_desk_ev_plus",
                    "name": "Trading Desk EV+",
                    "currency": "BRL",
                    "currentBalance": 8300,
                    "initialCapital": 5000,
                    "realizedPnl": 3300,
                    "openPnl": 0,
                    "totalPnl": 3300,
                    "totalPnlPct": 66,
                    "updatedAt": "2026-07-10T08:30:00",
                },
            )

        client = httpx.Client(transport=httpx.MockTransport(handler))
        with patch("app.services.trading_desk_integration.get_settings", return_value=_settings()):
            summary = get_trading_desk_summary(client)
        client.close()

        self.assertTrue(summary["connected"])
        self.assertEqual(summary["currentBalance"], 8300)
        self.assertEqual(summary["initialCapital"], 5000)
        self.assertEqual(summary["totalPnl"], 3300)
        self.assertEqual(summary["totalPnlPct"], 66)

    def test_unauthorized_integration_does_not_raise(self) -> None:
        client = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(401, json={"detail": "unauthorized"})))
        with patch("app.services.trading_desk_integration.get_settings", return_value=_settings()):
            summary = get_trading_desk_summary(client)
        client.close()

        self.assertTrue(summary["enabled"])
        self.assertFalse(summary["connected"])
        self.assertEqual(summary["status"], "unauthorized")

    def test_api_unavailable_falls_back_to_local_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            (base_path / "config_banca.json").write_text(json.dumps({"banca_inicial": 100}), encoding="utf-8")
            (base_path / "historico_financeiro.json").write_text(
                json.dumps(
                    [
                        {"resultado": "GREEN", "lucro": 5.25},
                        {"resultado": "RED", "lucro": -2},
                        {"resultado": "PENDENTE", "lucro": 0},
                    ]
                ),
                encoding="utf-8",
            )
            client = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(503, json={"error": "offline"})))

            with patch(
                "app.services.trading_desk_integration.get_settings",
                return_value=_settings(trading_desk_local_path=str(base_path)),
            ):
                summary = get_trading_desk_summary(client)
            client.close()

        self.assertTrue(summary["connected"])
        self.assertEqual(summary["status"], "local_files")
        self.assertEqual(summary["initialCapital"], 100)
        self.assertEqual(summary["realizedPnl"], 3.25)
        self.assertEqual(summary["currentBalance"], 103.25)


if __name__ == "__main__":
    unittest.main()
