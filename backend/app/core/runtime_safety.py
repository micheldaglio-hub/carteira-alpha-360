from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings


DEFAULT_SECRET_KEY = "troque-esta-chave-em-producao"
PRODUCTION_NAMES = {"prod", "production"}


@dataclass(frozen=True)
class RuntimeFinding:
    severity: str
    code: str
    message: str

    def as_dict(self) -> dict:
        return {"severity": self.severity, "code": self.code, "message": self.message}


def is_production(settings: Settings) -> bool:
    return settings.environment.strip().lower() in PRODUCTION_NAMES


def runtime_safety_findings(settings: Settings) -> list[RuntimeFinding]:
    findings: list[RuntimeFinding] = []
    production = is_production(settings)
    database_url = settings.database_url.lower()
    cors_regex = settings.backend_cors_origin_regex.lower()

    if settings.secret_key == DEFAULT_SECRET_KEY or len(settings.secret_key.strip()) < 32:
        findings.append(
            RuntimeFinding(
                "critical" if production else "warning",
                "weak_secret_key",
                "SECRET_KEY precisa ser unico, longo e diferente do padrao antes de producao.",
            )
        )

    if database_url.startswith("sqlite"):
        findings.append(
            RuntimeFinding(
                "critical" if production else "warning",
                "sqlite_database",
                "SQLite e aceitavel para preview local; producao precisa PostgreSQL gerenciado com backup.",
            )
        )

    if production and settings.database_auto_create_tables:
        findings.append(
            RuntimeFinding(
                "warning",
                "auto_create_tables_enabled",
                "DATABASE_AUTO_CREATE_TABLES deve ser false em producao; use Alembic para schema controlado.",
            )
        )

    if settings.seed_demo_data:
        findings.append(
            RuntimeFinding(
                "critical" if production else "warning",
                "demo_seed_enabled",
                "SEED_DEMO_DATA deve ser false em producao para evitar dados demonstrativos em ambiente real.",
            )
        )

    if settings.market_data_provider.lower() == "mock":
        findings.append(
            RuntimeFinding(
                "critical" if production else "warning",
                "mock_market_provider",
                "MARKET_DATA_PROVIDER=mock nao pode ser fonte principal em producao.",
            )
        )

    if production and ("127\\.0\\.0\\.1" in cors_regex or "localhost" in cors_regex or "192\\.168" in cors_regex):
        findings.append(
            RuntimeFinding(
                "warning",
                "wide_cors_regex",
                "CORS de producao deve apontar somente para dominios oficiais do produto.",
            )
        )

    if settings.access_token_expire_minutes > 240:
        findings.append(
            RuntimeFinding(
                "warning",
                "long_access_token_ttl",
                "ACCESS_TOKEN_EXPIRE_MINUTES esta alto; producao deve usar expiracao menor com refresh token.",
            )
        )

    if settings.trading_desk_enabled and not settings.trading_desk_integration_key:
        findings.append(
            RuntimeFinding(
                "critical" if production else "warning",
                "trading_desk_key_missing",
                "Trading Desk EV+ habilitado precisa TRADING_DESK_INTEGRATION_KEY configurada.",
            )
        )

    if settings.alpha_copilot_ai_enabled and not (settings.alpha_copilot_api_key or settings.openai_api_key):
        findings.append(
            RuntimeFinding(
                "critical" if production else "warning",
                "alpha_copilot_ai_key_missing",
                "Alpha Copilot com IA habilitada precisa ALPHA_COPILOT_API_KEY ou OPENAI_API_KEY configurada.",
            )
        )

    if production and not settings.audit_enabled:
        findings.append(
            RuntimeFinding(
                "critical",
                "audit_disabled",
                "AUDIT_ENABLED precisa ser true em producao para rastreabilidade operacional.",
            )
        )

    if production and not settings.jobs_enabled:
        findings.append(
            RuntimeFinding(
                "warning",
                "jobs_disabled",
                "JOBS_ENABLED=false desativa automacoes operacionais; use apenas se houver scheduler externo.",
            )
        )

    if production and not settings.observability_json_logs:
        findings.append(
            RuntimeFinding(
                "warning",
                "plain_text_logs",
                "OBSERVABILITY_JSON_LOGS=false dificulta ingestao por ferramentas de monitoramento.",
            )
        )

    return findings


def assert_runtime_safe(settings: Settings) -> None:
    if not is_production(settings):
        return
    blockers = [finding for finding in runtime_safety_findings(settings) if finding.severity == "critical"]
    if blockers:
        details = "; ".join(f"{finding.code}: {finding.message}" for finding in blockers)
        raise RuntimeError(f"Configuracao insegura para producao: {details}")
