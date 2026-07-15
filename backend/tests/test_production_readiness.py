from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.rate_limit import InMemoryRateLimiter
from app.core.runtime_safety import DEFAULT_SECRET_KEY, assert_runtime_safe, runtime_safety_findings
from app.main import app


class ProductionReadinessTests(unittest.TestCase):
    def test_production_with_insecure_defaults_is_blocked(self) -> None:
        settings = Settings(
            environment="production",
            secret_key=DEFAULT_SECRET_KEY,
            database_url="sqlite:///./carteira_alpha.db",
            seed_demo_data=True,
            market_data_provider="mock",
        )

        with self.assertRaises(RuntimeError):
            assert_runtime_safe(settings)

    def test_development_reports_warnings_without_blocking(self) -> None:
        settings = Settings(
            environment="development",
            secret_key=DEFAULT_SECRET_KEY,
            database_url="sqlite:///./carteira_alpha.db",
            seed_demo_data=True,
            market_data_provider="mock",
        )

        findings = runtime_safety_findings(settings)

        self.assertTrue(findings)
        self.assertTrue(all(finding.severity == "warning" for finding in findings))
        assert_runtime_safe(settings)

    def test_auth_rate_limiter_blocks_after_limit(self) -> None:
        now = [1000.0]
        limiter = InMemoryRateLimiter(clock=lambda: now[0])

        self.assertTrue(limiter.allow("auth:login:ip:127.0.0.1", limit=2, window_seconds=60))
        self.assertTrue(limiter.allow("auth:login:ip:127.0.0.1", limit=2, window_seconds=60))
        self.assertFalse(limiter.allow("auth:login:ip:127.0.0.1", limit=2, window_seconds=60))

        now[0] += 61
        self.assertTrue(limiter.allow("auth:login:ip:127.0.0.1", limit=2, window_seconds=60))

    def test_security_headers_are_present(self) -> None:
        with TestClient(app) as client:
            response = client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertIn("camera=()", response.headers["Permissions-Policy"])
        self.assertTrue(response.headers["X-Request-ID"])
        self.assertTrue(float(response.headers["X-Process-Time-Ms"]) >= 0)

    def test_readiness_exposes_sanitized_runtime_status(self) -> None:
        with TestClient(app) as client:
            response = client.get("/api/ready")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn(payload["status"], {"ready", "not_ready"})
        self.assertIn("database", payload)
        self.assertNotIn("SECRET_KEY", str(payload))
        self.assertNotIn("BRAPI_TOKEN", str(payload))


if __name__ == "__main__":
    unittest.main()
