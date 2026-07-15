from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import User
from app.schemas import DashboardProjectionPremises, ProjectionRequest
from app.services.projection_premises import (
    delete_dashboard_projection_premises,
    delete_projection_premises,
    get_dashboard_projection_premises,
    get_projection_premises,
    save_dashboard_projection_premises,
    save_projection_premises,
)


class ProjectionPremisesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        self.db = self.Session()
        self.user = User(email="premises@carteiraalpha.com", full_name="Premises User", password_hash="hash")
        self.db.add(self.user)
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_save_load_and_delete_projection_premises(self) -> None:
        payload = ProjectionRequest(
            initial_wealth=1000,
            monthly_contribution=100,
            expected_monthly_return=1.5,
            expected_annual_dividend_yield=7.5,
            reinvest_dividends=True,
            dividend_reinvestment_rate=100,
            years=25,
            annual_inflation=4,
            passive_income_goal=5000,
        )

        save_projection_premises(self.db, self.user.id, payload)
        loaded = get_projection_premises(self.db, self.user.id)
        delete_projection_premises(self.db, self.user.id)

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["expected_monthly_return"], 1.5)
        self.assertEqual(loaded["passive_income_goal"], 5000)
        self.assertIsNone(get_projection_premises(self.db, self.user.id))

    def test_save_load_and_delete_dashboard_projection_premises(self) -> None:
        payload = DashboardProjectionPremises(monthly_contribution=350, monthly_return=1.25)

        save_dashboard_projection_premises(self.db, self.user.id, payload)
        loaded = get_dashboard_projection_premises(self.db, self.user.id)
        delete_dashboard_projection_premises(self.db, self.user.id)

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["monthly_contribution"], 350)
        self.assertEqual(loaded["monthly_return"], 1.25)
        self.assertIsNone(get_dashboard_projection_premises(self.db, self.user.id))


if __name__ == "__main__":
    unittest.main()
