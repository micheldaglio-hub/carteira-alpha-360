from __future__ import annotations

import os
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.database import Base
from app.models import User
from app.services.external_integrations import (
    TRADING_DESK_INTEGRATION_KEY,
    get_latest_external_integration_snapshot,
    save_external_integration_snapshot,
    trading_desk_summary_from_snapshot,
)
from app.services.trading_desk_integration import get_trading_desk_summary


class ExternalIntegrationSnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        self.db = self.Session()
        self.user = User(email="michel@example.com", full_name="Michel", password_hash="hash")
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)
        self.old_enabled = os.environ.get("TRADING_DESK_ENABLED")
        os.environ["TRADING_DESK_ENABLED"] = "false"
        get_settings.cache_clear()

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        if self.old_enabled is None:
            os.environ.pop("TRADING_DESK_ENABLED", None)
        else:
            os.environ["TRADING_DESK_ENABLED"] = self.old_enabled
        get_settings.cache_clear()

    def test_save_and_read_latest_trading_desk_snapshot(self) -> None:
        snapshot = save_external_integration_snapshot(
            self.db,
            integration_key=TRADING_DESK_INTEGRATION_KEY,
            user_id=self.user.id,
            payload={
                "source": "trading_desk_ev_plus",
                "name": "Trading Desk EV+",
                "currency": "BRL",
                "currentBalance": 120.5,
                "initialCapital": 100,
                "realizedPnl": 20.5,
                "openPnl": 0,
                "totalPnl": 20.5,
                "totalPnlPct": 20.5,
                "updatedAt": "2026-07-15T12:00:00+00:00",
            },
        )
        self.db.commit()

        latest = get_latest_external_integration_snapshot(
            self.db,
            integration_key=TRADING_DESK_INTEGRATION_KEY,
            user_id=self.user.id,
        )
        self.assertEqual(latest.id, snapshot.id)

        summary = trading_desk_summary_from_snapshot(latest)
        self.assertTrue(summary["connected"])
        self.assertEqual(summary["status"], "snapshot")
        self.assertEqual(summary["currentBalance"], 120.5)
        self.assertEqual(summary["totalPnl"], 20.5)

    def test_trading_desk_summary_uses_snapshot_when_live_integration_is_disabled(self) -> None:
        save_external_integration_snapshot(
            self.db,
            integration_key=TRADING_DESK_INTEGRATION_KEY,
            user_id=self.user.id,
            payload={
                "currentBalance": 86.87,
                "initialCapital": 100,
                "realizedPnl": -13.13,
                "openPnl": 0,
                "totalPnl": -13.13,
            },
        )
        self.db.commit()

        summary = get_trading_desk_summary(db=self.db, user_id=self.user.id)

        self.assertEqual(summary["status"], "snapshot")
        self.assertEqual(summary["currentBalance"], 86.87)
        self.assertEqual(summary["totalPnl"], -13.13)


if __name__ == "__main__":
    unittest.main()
