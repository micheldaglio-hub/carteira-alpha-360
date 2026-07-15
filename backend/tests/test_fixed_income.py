from datetime import date
from decimal import Decimal
import unittest

from app.services.fixed_income import accrue_cdi_lots, parse_cdi_percent


class FixedIncomeTests(unittest.TestCase):
    def test_parse_cdi_percent(self):
        self.assertEqual(parse_cdi_percent("100% CDI"), Decimal("100"))
        self.assertEqual(parse_cdi_percent("110,5% do CDI"), Decimal("110.5"))
        self.assertEqual(parse_cdi_percent("RDB CDI"), Decimal("100"))

    def test_accrue_cdi_lots_with_daily_rates(self):
        result = accrue_cdi_lots(
            [{"date": date(2026, 1, 1), "amount": Decimal("1000")}],
            cdi_percent=Decimal("100"),
            end_date=date(2026, 1, 3),
            rates=[
                {"date": date(2026, 1, 2), "dailyPct": Decimal("0.10")},
                {"date": date(2026, 1, 3), "dailyPct": Decimal("0.10")},
            ],
        )

        self.assertEqual(result["source"], "Banco Central SGS 12")
        self.assertEqual(result["appliedDays"], 2)
        self.assertAlmostEqual(result["currentValue"], 1002.0, places=2)
        self.assertAlmostEqual(result["returnPct"], 0.2, places=2)


if __name__ == "__main__":
    unittest.main()
