from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Carteira Alpha 360"
    environment: str = "development"
    secret_key: str = "troque-esta-chave-em-producao"
    access_token_expire_minutes: int = 720
    database_url: str = "sqlite:///./carteira_alpha.db"
    database_auto_create_tables: bool = True
    backend_cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    backend_cors_origin_regex: str = r"^https?://(localhost|127\.0\.0\.1|[A-Za-z0-9-]+(?:\.local)?|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+)(:\d+)?$"
    seed_demo_data: bool = True
    market_data_provider: str = "mock"
    brapi_token: str = ""
    coinmarketcap_api_key: str = ""
    cvm_base_url: str = "https://dados.cvm.gov.br"
    b3_base_url: str = "https://sistemaswebb3-listados.b3.com.br"
    dados_mercado_base_url: str = "https://api.dadosdemercado.com.br/v1"
    dados_mercado_api_token: str = ""
    fmp_base_url: str = "https://financialmodelingprep.com/stable"
    fmp_api_key: str = ""
    twelve_data_base_url: str = "https://api.twelvedata.com"
    twelve_data_api_key: str = ""
    fundamentus_enabled: bool = False
    fundamentus_base_url: str = "https://www.fundamentus.com.br"
    fundamentus_rate_limit_seconds: int = 45
    fundamentus_timeout_seconds: float = 6.0
    coingecko_base_url: str = "https://api.coingecko.com/api/v3"
    coingecko_api_key: str = ""
    bcb_sgs_base_url: str = "https://api.bcb.gov.br/dados/serie"
    fintz_base_url: str = "https://api.fintz.com.br"
    fintz_api_key: str = ""
    trading_desk_enabled: bool = False
    trading_desk_api_url: str = "http://127.0.0.1:8510"
    trading_desk_integration_key: str = ""
    trading_desk_timeout_seconds: float = 4.0
    trading_desk_local_path: str = ""
    alpha_copilot_ai_enabled: bool = False
    alpha_copilot_provider: str = "openai"
    alpha_copilot_model: str = "gpt-4o-mini"
    alpha_copilot_timeout_seconds: float = 20.0
    alpha_copilot_max_context_chars: int = 18000
    alpha_copilot_api_key: str = ""
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    observability_json_logs: bool = True
    observability_log_request_body: bool = False
    audit_enabled: bool = True
    audit_http_mutations: bool = True
    audit_retention_days: int = 365
    jobs_enabled: bool = False
    jobs_heartbeat_interval_seconds: int = 300
    jobs_cleanup_interval_seconds: int = 3600
    jobs_guardian_interval_seconds: int = 21600
    jobs_market_data_interval_seconds: int = 3600
    jobs_model_portfolios_interval_seconds: int = 21600
    jobs_macro_fx_interval_seconds: int = 3600
    jobs_formula_audit_interval_seconds: int = 86400
    backup_directory: str = "backups"
    monitoring_webhook_url: str = ""
    billing_payment_provider: str = "mock"
    billing_checkout_expires_minutes: int = 60
    billing_webhook_secret: str = ""
    billing_public_base_url: str = "http://127.0.0.1:5173"
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    mercadopago_access_token: str = ""
    mercadopago_webhook_secret: str = ""
    distribution_provider: str = "mock"
    distribution_from_email: str = "research@carteiraalpha.local"
    distribution_reply_to: str = ""
    distribution_webhook_secret: str = ""
    distribution_public_base_url: str = ""
    distribution_resend_api_key: str = ""
    distribution_resend_base_url: str = "https://api.resend.com"
    distribution_smtp_host: str = ""
    distribution_smtp_port: int = 587
    distribution_smtp_username: str = ""
    distribution_smtp_password: str = ""
    distribution_smtp_use_tls: bool = True

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
