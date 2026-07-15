from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Asset, MarketSnapshot
from app.services.alpha_b3_screener import run_alpha_b3_screener
from app.services.alpha_confidence_engine import build_alpha_confidence_report
from app.services.alpha_crypto_screener import MarketCandidate, _rank_candidates, run_alpha_crypto_screener
from app.services.alpha_fii_screener import run_alpha_fii_screener
from app.services.alpha_global_equity_screener import run_alpha_global_equity_screener
from app.services.crypto_research_engine import CryptoResearchEngine
from app.services.global_backtest import run_global_backtest
from app.services.model_portfolios import DIVIDEND_MODEL_ASSETS, get_model_portfolios, validate_dividend_portfolio


class ModelPortfolioTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        self.db = self.Session()

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_dividend_model_weights_sum_to_100(self) -> None:
        payload = get_model_portfolios()
        weights = [asset["targetWeight"] for asset in payload["dividendPortfolio"]["assets"]]

        self.assertEqual(sum(weights), 100)
        self.assertEqual(len(weights), 10)

    def test_payload_has_guardrails_against_direct_recommendation(self) -> None:
        payload = get_model_portfolios()

        self.assertEqual(payload["status"], "educational_model")
        self.assertEqual(payload["validation"]["status"], "carteira_alpha_oficial")
        self.assertEqual(payload["screener"]["title"], "Screener Alpha B3")
        self.assertIn("Nao representa recomendacao individual", payload["disclaimer"])
        self.assertIn("sem promessa de rentabilidade", payload["dividendPortfolio"]["targetReturnLanguage"])
        self.assertEqual(payload["cryptoStudy"]["riskLevel"], "extremo")
        self.assertEqual(payload["cryptoStudy"]["ticker"], "JASMY")
        self.assertIn("fiiPortfolio", payload)
        self.assertIn("isencao tributaria", payload["fiiPortfolio"]["targetReturnLanguage"])
        self.assertIn("estudo inicial", payload["fiiPortfolio"]["title"].lower())
        self.assertIn("globalPortfolio", payload)
        self.assertIn("globalBacktest", payload)
        self.assertIn("confidenceReport", payload)
        self.assertIn("recommendedPortfolioReport", payload)
        self.assertTrue(any("compra sem medo" in item.lower() for item in payload["confidenceReport"]["nonNegotiables"]))

    def test_alpha_fii_screener_has_dedicated_fii_metrics(self) -> None:
        screener = run_alpha_fii_screener()
        weights = [asset["targetWeight"] for asset in screener["portfolio"]]

        self.assertEqual(screener["title"], "Screener Alpha FIIs")
        self.assertEqual(sum(weights), 100)
        self.assertTrue(all(asset["class"] == "FIIs" for asset in screener["portfolio"]))
        self.assertIn("vacancia", " ".join(screener["filters"]).lower())
        self.assertIn("segmentAllocation", screener)

    def test_alpha_global_screener_diversifies_country_and_currency(self) -> None:
        screener = run_alpha_global_equity_screener()
        weights = [asset["targetWeight"] for asset in screener["portfolio"]]
        countries = {asset["country"] for asset in screener["portfolio"]}
        currencies = {asset["currency"] for asset in screener["portfolio"]}

        self.assertEqual(screener["title"], "Screener Alpha Global")
        self.assertEqual(sum(weights), 100)
        self.assertGreaterEqual(len(countries), 5)
        self.assertGreaterEqual(len(currencies), 2)
        self.assertIn("FMP", " ".join(screener["filters"]))

    def test_global_backtest_compares_stock_bdr_and_etf_in_brl(self) -> None:
        backtest = run_global_backtest(initial_value_brl=1000)
        vehicle_ids = {vehicle["id"] for vehicle in backtest["vehicles"]}

        self.assertEqual(backtest["currency"], "BRL")
        self.assertEqual(vehicle_ids, {"stock_direct", "bdr_proxy", "global_etf"})
        self.assertGreater(len(backtest["rows"]), 3)
        self.assertIn("stockDirectValue", backtest["rows"][0])
        self.assertIn("bdrValue", backtest["rows"][0])
        self.assertIn("globalEtfValue", backtest["rows"][0])
        self.assertGreater(backtest["summary"]["endUsdBrl"], 0)
        self.assertTrue(any(vehicle["dividendsBrl"] >= 0 for vehicle in backtest["vehicles"]))

    def test_official_alpha_portfolio_is_generated_by_screener(self) -> None:
        payload = get_model_portfolios()
        tickers = [asset["ticker"] for asset in payload["dividendPortfolio"]["assets"]]

        self.assertEqual(payload["dividendPortfolio"]["title"], "Carteira Recomendada Alpha oficial")
        self.assertIn("ITSA4", tickers)
        self.assertIn("CPFE3", tickers)
        self.assertIn("PSSA3", tickers)
        self.assertIn("VIVT3", tickers)
        self.assertNotIn("BBDC4", tickers)

    def test_alpha_confidence_report_has_gates_and_asset_scores(self) -> None:
        payload = get_model_portfolios()
        report = payload["confidenceReport"]

        self.assertEqual(report["status"], "confidence_layer")
        self.assertGreater(report["overallScore"], 0)
        self.assertGreaterEqual(len(report["gates"]), 6)
        self.assertTrue(report["assetRows"])
        self.assertTrue(all("score" in row for row in report["assetRows"]))
        self.assertTrue(any(row["ticker"] == "BBSE3" for row in report["assetRows"]))
        self.assertNotIn("comprar sem medo", report["headline"].lower())

    def test_recommended_portfolio_engine_builds_institutional_report(self) -> None:
        payload = get_model_portfolios()
        report = payload["recommendedPortfolioReport"]

        self.assertEqual(report["status"], "institutional_report")
        self.assertEqual(report["title"], "Recommended Portfolio Engine institucional")
        self.assertGreater(report["institutionalScore"], 0)
        self.assertTrue(report["executiveSummary"])
        self.assertTrue(report["assetReports"])
        self.assertTrue(report["riskMatrix"])
        self.assertTrue(report["evidenceLedger"])
        self.assertIn("nextReviewDate", report)
        self.assertIn("monthlyReview", report)
        self.assertTrue(any(item["ticker"] == "BBSE3" for item in report["assetReports"]))
        self.assertTrue(any("compra" in item.lower() for item in report["blockedLanguage"]))
        self.assertIn("Nucleo Brasil", report["portfolios"][0]["title"])

    def test_recommended_asset_report_has_thesis_risk_score_and_evidence(self) -> None:
        payload = get_model_portfolios()
        report = payload["recommendedPortfolioReport"]
        bbse = next(item for item in report["assetReports"] if item["ticker"] == "BBSE3")

        self.assertGreater(bbse["institutionalScore"], 0)
        self.assertTrue(bbse["thesis"])
        self.assertTrue(bbse["risks"])
        self.assertTrue(bbse["evidence"])
        self.assertIn("scoreBreakdown", bbse)
        self.assertIn("reviewAction", bbse)

    def test_alpha_confidence_engine_can_run_standalone(self) -> None:
        screener = run_alpha_b3_screener()
        validation = {
            "rows": [
                {
                    "ticker": asset["ticker"],
                    "validationScore": asset["alphaScore"],
                    "dataFields": asset.get("dataFields", 0),
                }
                for asset in screener["portfolio"]
            ]
        }

        report = build_alpha_confidence_report(screener=screener, validation=validation)

        self.assertEqual(report["title"], "Confiabilidade Alpha")
        self.assertGreater(report["overallScore"], 0)
        self.assertTrue(report["nonNegotiables"])

    def test_screener_alpha_b3_generates_official_weights(self) -> None:
        screener = run_alpha_b3_screener()
        weights = {asset["ticker"]: asset["targetWeight"] for asset in screener["portfolio"]}

        self.assertEqual(screener["title"], "Screener Alpha B3")
        self.assertEqual(sum(weights.values()), 100)
        self.assertEqual(weights["BBSE3"], 13)
        self.assertEqual(weights["TAEE11"], 12)
        self.assertEqual(weights["CSMG3"], 10)
        self.assertNotIn("BRSR6", weights)

    def test_crypto_screener_is_binance_first(self) -> None:
        study = run_alpha_crypto_screener()

        self.assertEqual(study["ticker"], "JASMY")
        self.assertEqual(study["selectionStatus"], "selecionada_por_research_engine")
        self.assertIn("JASMY/USDT", study["binancePairs"])
        self.assertIn("researchReport", study)
        self.assertIn("scenarios", study["researchReport"])
        self.assertEqual(study["previousCandidate"]["ticker"], "PEPETO")
        self.assertEqual(study["decisionType"], "nova_oportunidade")

    def test_crypto_research_engine_validates_candidate_before_selection(self) -> None:
        engine = CryptoResearchEngine()
        engine._fetch_external_detail = lambda ticker, name: {
            "name": "Fetch.ai",
            "source": "test",
            "categories": ["Artificial Intelligence", "Infrastructure"],
            "priceUsd": 0.5,
            "marketCapUsd": 1_500_000_000,
            "fullyDilutedValuationUsd": 1_700_000_000,
            "volumeUsd": 70_000_000,
            "priceChange24hPct": 2,
            "priceChange7dPct": 8,
            "priceChange30dPct": 18,
            "circulatingSupply": 2_500_000_000,
            "totalSupply": 2_700_000_000,
            "maxSupply": 2_700_000_000,
        }
        candidate = {
            "ticker": "FET",
            "name": "Fetch.ai",
            "priceUsd": 0.5,
            "marketCapUsd": 1_500_000_000,
            "volumeUsd": 70_000_000,
            "priceChange24hPct": 2,
            "priceChange7dPct": 8,
            "priceChange30dPct": 18,
            "binancePairs": ["FET/USDT"],
            "alphaScore": 90,
            "decisionType": "nova_oportunidade",
            "selectionReason": "Passou no screener quantitativo.",
        }

        report = engine.research_candidate(candidate, {})

        self.assertEqual(report["ticker"], "FET")
        self.assertGreater(report["researchScore"], 70)
        self.assertEqual(report["decisionType"], "nova_oportunidade")
        self.assertTrue(report["catalysts"])
        self.assertTrue(report["riskFactors"])
        self.assertEqual(len(report["scenarios"]), 3)
        self.assertIn("disclaimer", report)

    def test_crypto_screener_ranks_external_opportunity_before_portfolio_context(self) -> None:
        candidates = [
            MarketCandidate("AAA", "Alpha A", 0.02, 300_000_000, 12_000_000, 2, 4, 10, ["AAA/USDT"], "test"),
            MarketCandidate("ADA", "Cardano", 0.8, 25_000_000_000, 100_000_000, 1, 2, 4, ["ADA/USDT"], "test"),
        ]
        holdings = {"ADA": {"currentValue": 20, "returnPct": -20}}

        ranking = _rank_candidates(candidates, holdings)

        self.assertEqual(ranking[0]["ticker"], "AAA")
        self.assertEqual(ranking[0]["decisionType"], "nova_oportunidade")
        self.assertTrue(any(item["ticker"] == "ADA" and item["decisionType"] == "reforcar_tese_existente" for item in ranking))

    def test_backtest_summary_matches_imported_report(self) -> None:
        payload = get_model_portfolios()
        summary = payload["backtest"]["summary"]

        self.assertEqual(summary["stockFinalValue"], 1313.93)
        self.assertEqual(summary["fixedIncomeFinalValue"], 1208.11)
        self.assertEqual(summary["stockTotalReturn"], 31.39)
        self.assertEqual(len(payload["backtest"]["rows"]), 19)

    def test_alpha_validation_uses_database_snapshots(self) -> None:
        for item in DIVIDEND_MODEL_ASSETS:
            asset = Asset(
                ticker=item["ticker"],
                name=item["name"],
                asset_class="Acoes",
                sector=item["sector"],
                segment="Carteira recomendada",
                currency="BRL",
                provider_symbol=item["ticker"],
            )
            self.db.add(asset)
            self.db.flush()
            self.db.add(
                MarketSnapshot(
                    asset_id=asset.id,
                    price=30,
                    dividend_yield=8,
                    payout=65,
                    revenue_growth=6,
                    profit_growth=8,
                    net_margin=22,
                    roe=18,
                    roic=13,
                    debt_to_ebitda=1.5,
                    historical_appreciation=30,
                    dividend_consistency=85,
                    payment_frequency=6,
                    recurring_profit=82,
                    sector_stability=84,
                    pe_ratio=9,
                    pvp=1.1,
                )
            )
        self.db.commit()

        validation = validate_dividend_portfolio(self.db)

        self.assertEqual(len(validation["rows"]), 10)
        self.assertGreater(validation["overallScore"], 60)
        self.assertEqual(validation["insufficientCount"], 0)
        self.assertTrue(any(row["status"] in {"validado_alpha", "em_observacao"} for row in validation["rows"]))


if __name__ == "__main__":
    unittest.main()
