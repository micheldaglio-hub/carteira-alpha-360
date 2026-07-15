from __future__ import annotations

from datetime import date
from decimal import Decimal
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Asset, Dividend, Transaction, User
from app.wealth_os.tax_engine import build_tax_report


class TaxEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        self.db = self.Session()
        self.user = User(email="tax@carteiraalpha.com", full_name="Tax User", password_hash="hash")
        self.db.add(self.user)
        self.db.flush()
        self.stock = Asset(ticker="BBSE3", name="BB Seguridade", asset_class="Acoes", sector="Seguros", segment="", last_price=Decimal("35"))
        self.fii = Asset(ticker="HGLG11", name="CSHG Logistica", asset_class="FIIs", sector="Fundos imobiliarios", segment="", last_price=Decimal("110"))
        self.db.add_all([self.stock, self.fii])
        self.db.flush()
        self.db.add_all(
            [
                Transaction(user_id=self.user.id, asset_id=self.stock.id, type="buy", date=date(2026, 1, 2), quantity=Decimal("1000"), price=Decimal("10"), fees=Decimal("0"), broker="Alpha"),
                Transaction(user_id=self.user.id, asset_id=self.stock.id, type="sell", date=date(2026, 7, 10), quantity=Decimal("1000"), price=Decimal("35"), fees=Decimal("0"), broker="Alpha"),
                Transaction(user_id=self.user.id, asset_id=self.fii.id, type="buy", date=date(2026, 2, 1), quantity=Decimal("10"), price=Decimal("100"), fees=Decimal("0"), broker="Alpha"),
                Transaction(user_id=self.user.id, asset_id=self.fii.id, type="sell", date=date(2026, 7, 11), quantity=Decimal("10"), price=Decimal("110"), fees=Decimal("0"), broker="Alpha"),
                Dividend(user_id=self.user.id, asset_id=self.stock.id, date=date(2026, 7, 5), amount_per_share=Decimal("1"), total_amount=Decimal("100"), source="jcp"),
                Dividend(user_id=self.user.id, asset_id=self.fii.id, date=date(2026, 7, 8), amount_per_share=Decimal("2"), total_amount=Decimal("20"), source="fii"),
            ]
        )
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_tax_report_estimates_brazilian_rules(self) -> None:
        report = build_tax_report(self.db, self.user.id, year=2026, month=7)

        self.assertEqual(report.status, "estimativa_operacional")
        self.assertEqual(report.estimatedWithheldTax, 15)
        self.assertEqual(report.estimatedTaxDue, 3770)
        self.assertTrue(any(item.id == "income_jcp" for item in report.items))
        self.assertTrue(any(item.id == "gain_stocks_2026-07" for item in report.items))
        self.assertTrue(any(item.id == "gain_fiis_2026-07" for item in report.items))
        self.assertTrue(report.rules)
        self.assertTrue(report.alerts)


if __name__ == "__main__":
    unittest.main()
