from __future__ import annotations

import unittest

from app.services.income import add_income_to_breakdown, empty_income_breakdown, normalize_income_type


class IncomeClassificationTests(unittest.TestCase):
    def test_jcp_source_is_classified_as_jcp(self) -> None:
        classification = normalize_income_type("jcp", "Acoes")

        self.assertEqual(classification.key, "jcp")
        self.assertEqual(classification.label, "JCP")

    def test_fii_asset_class_defaults_to_fii_income(self) -> None:
        classification = normalize_income_type("manual", "FIIs")

        self.assertEqual(classification.key, "fii_income")
        self.assertEqual(classification.label, "Rendimento de FII")

    def test_breakdown_keeps_total_proceeds(self) -> None:
        breakdown = empty_income_breakdown()

        add_income_to_breakdown(breakdown, 10, "dividend", "Acoes")
        add_income_to_breakdown(breakdown, 5, "jcp", "Acoes")
        add_income_to_breakdown(breakdown, 3, "manual", "FIIs")

        self.assertEqual(breakdown["dividend"], 10)
        self.assertEqual(breakdown["jcp"], 5)
        self.assertEqual(breakdown["fii_income"], 3)
        self.assertEqual(breakdown["total_proceeds"], 18)


if __name__ == "__main__":
    unittest.main()
